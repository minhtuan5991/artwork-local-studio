"""Copy and verify portable data into a stable workspace; never delete sources."""
import argparse,json,hashlib,shutil,sqlite3,sys,time
from contextlib import closing
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from artwork_local.core import Store,ACTIVE

def digest(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def consolidate(workspace,primary,others):
    workspace=workspace.resolve(); target=workspace/'data'
    if (target/'studio.sqlite3').exists(): raise ValueError('Destination database already exists; refusing to overwrite')
    sources=[primary.resolve(),*[p.resolve() for p in others]]
    if len(set(sources))!=len(sources): raise ValueError('Duplicate source database')
    for source in sources:
        if not source.is_relative_to(workspace) or not (source/'studio.sqlite3').is_file():
            raise ValueError('Invalid source data directory: '+str(source))
    store=Store(target); mapping={}; copied=[]
    def copy_file(path,destination):
        if path.is_symlink() or path.is_junction(): raise ValueError('Reparse file: '+str(path))
        checksum=digest(path)
        if destination.exists() and digest(destination)!=checksum:
            destination=destination.with_name(destination.stem+'-'+checksum[:12]+destination.suffix)
        destination.parent.mkdir(parents=True,exist_ok=True)
        if not destination.exists(): shutil.copy2(path,destination)
        if digest(destination)!=checksum: raise ValueError('Copy checksum mismatch: '+str(path))
        mapping[str(path.resolve()).casefold()]=str(destination.resolve())
        copied.append({'source':str(path),'destination':str(destination),'sha256':checksum})
    for source in sources:
        for name in ['sources','results']:
            folder=source/name
            if not folder.exists(): continue
            for path in folder.rglob('*'):
                if path.is_symlink() or path.is_junction(): raise ValueError('Reparse path')
                if path.is_file(): copy_file(path,target/name/path.relative_to(folder))
        inbox=source/'inbox'
        if list(inbox.glob('*.json')) or list(inbox.glob('*.processing')):
            raise ValueError('Pending browser imports must finish before consolidation')
        old_output=source.parent/'output'
        if old_output.is_dir():
            for path in old_output.rglob('*'):
                if path.is_file(): copy_file(path,workspace/'output'/path.relative_to(old_output))
    def rewrite(value):
        if isinstance(value,dict): return {k:rewrite(v) for k,v in value.items()}
        if isinstance(value,list): return [rewrite(v) for v in value]
        if isinstance(value,str):
            if value.casefold() in mapping: return mapping[value.casefold()]
            for source in sources:
                output=source.parent/'output'
                if value.casefold().startswith(str(output).casefold()):
                    return str(workspace/'output')+value[len(str(output)):]
                if value.casefold().startswith(str(source).casefold()):
                    return str(target)+value[len(str(source)):]
        return value
    totals=[]
    with store.connection() as dest:
        for index,source in enumerate(sources):
            with closing(sqlite3.connect((source/'studio.sqlite3').as_uri()+'?mode=ro',uri=True)) as con:
                con.row_factory=sqlite3.Row
                jobs=[dict(row) for row in con.execute('SELECT * FROM jobs ORDER BY position,created')]
                for job in jobs:
                    if job['status'] in ACTIVE: raise ValueError('Active processing job; close the app before consolidation')
                    for key in ['source_path','master_path','output_path','output_dir']:
                        job[key]=rewrite(job[key])
                    job['metadata']=json.dumps(rewrite(json.loads(job['metadata'])),ensure_ascii=False)
                    if index: job['visible']=0
                    columns=list(job)
                    dest.execute('INSERT OR IGNORE INTO jobs('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',[job[k] for k in columns])
                for row in con.execute('SELECT job_key,job_id FROM ledger'):
                    dest.execute('INSERT OR IGNORE INTO ledger(job_key,job_id) VALUES(?,?)',tuple(row))
                for row in con.execute('SELECT job_id,at,message FROM logs'):
                    dest.execute('INSERT INTO logs(job_id,at,message) VALUES(?,?,?)',tuple(row))
                totals.append({'data':str(source),'jobs':len(jobs)})
    settings=json.loads((primary/'settings.json').read_text(encoding='utf-8'))
    settings.update(model_dir=str(workspace/'models'),runtime_exe=str(workspace/'runtime/sd-cli.exe'),
        profile='low',cache_type='q8_0',max_vram=4.5)
    settings['defaults']['size']=1024
    settings['output_dir']=rewrite(settings['output_dir'])
    (target/'settings.json').write_text(json.dumps(settings,ensure_ascii=False,indent=2),encoding='utf-8')
    with store.connection() as con:
        assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
        for row in con.execute('SELECT source_path,master_path,output_path FROM jobs'):
            for path in row:
                if path and not Path(path).is_file(): raise ValueError('Missing preserved image: '+path)
        count=con.execute('SELECT count(*) FROM jobs').fetchone()[0]
    report={'sources':totals,'jobs_retained':count,'verified_files':len(copied),'copies':copied}
    (target/'consolidation-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--primary',type=Path,required=True);parser.add_argument('--older',type=Path,action='append',default=[])
    args=parser.parse_args(); result=consolidate(root,args.primary,args.older)
    print(json.dumps({key:result[key] for key in ['sources','jobs_retained','verified_files']}))
