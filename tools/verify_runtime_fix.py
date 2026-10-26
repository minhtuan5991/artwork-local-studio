"""Run one explicitly selected existing source through the real local backend."""
import argparse,json,sys,threading,time,sqlite3
from dataclasses import replace
from pathlib import Path
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
from artwork_local.core import JobOptions,validate_rgba
from artwork_local.engine import CliEngine
parser=argparse.ArgumentParser()
parser.add_argument("--data-dir",type=Path,required=True)
parser.add_argument("--job-id",required=True)
parser.add_argument("--output-dir",type=Path,required=True)
args=parser.parse_args(); args.output_dir.mkdir(parents=True,exist_ok=True)
with sqlite3.connect((args.data_dir/"studio.sqlite3").resolve().as_uri()+"?mode=ro",uri=True) as con:
    con.row_factory=sqlite3.Row
    job=dict(con.execute("SELECT * FROM jobs WHERE id=?",(args.job_id,)).fetchone())
config=json.loads((args.data_dir/"settings.json").read_text(encoding="utf-8"))
config.update(model_dir=str(root/"models"),runtime_exe=str(root/"runtime/sd-cli.exe"),
              profile="low",max_vram=4.5,cache_type="q8_0",timeout=1200)
options=replace(JobOptions.from_dict(json.loads(job["options"])),size=1024)
started=time.monotonic(); result={"source_job":args.job_id,"source":job["source_path"],"output":str(args.output_dir/"qwen.png")}
def report(stage,progress,message,line=""):
    with (args.output_dir/"runtime.log").open("a",encoding="utf-8") as file:
        file.write((line or message or "")+"\n")
try:
    result.update(CliEngine(config,json.loads((root/"model-manifest.json").read_text())).generate(
        Path(job["source_path"]),args.output_dir/"qwen.png",options,threading.Event(),report))
    result["validation"]=validate_rgba(args.output_dir/"qwen.png",1024)
    result["success"]=True
except Exception as exc:
    result.update(success=False,error=str(exc))
finally:
    result["wall_seconds"]=round(time.monotonic()-started,3)
    (args.output_dir/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:result.get(k) for k in ["success","error","wall_seconds","output"]},ensure_ascii=True),flush=True)
sys.exit(0 if result["success"] else 1)
