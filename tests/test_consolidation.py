import json,tempfile,unittest
from pathlib import Path
from PIL import Image
from artwork_local.core import Settings,Store,JobOptions,sha256_file
from tools.consolidate_data import consolidate

class ConsolidationTests(unittest.TestCase):
    def test_merge_keeps_current_queue_and_archives_older_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); current=root/'v2'/'data'; old=root/'v1'/'data'
            image=root/'source.png';Image.new('RGBA',(32,48),'red').save(image)
            ids=[]
            for data in [current,old]:
                settings=Settings(data.parent,data);settings.save();store=Store(data)
                jid=store.enqueue(store.prepare(image),JobOptions(),str(root/'output'))['job_id'];ids.append(jid)
            original=Store(old).get(ids[1])['source_path'];checksum=sha256_file(Path(original))
            result=consolidate(root,current,[old]); merged=Store(root/'data')
            self.assertEqual(result['jobs_retained'],2)
            self.assertEqual([job['id'] for job in merged.all()],[ids[0]])
            self.assertEqual(sha256_file(Path(merged.get(ids[1])['source_path'])),checksum)
            self.assertTrue(Path(original).is_file())
            settings=json.loads((root/'data/settings.json').read_text(encoding='utf-8'))
            self.assertEqual(settings['defaults']['size'],1024)
            self.assertEqual(settings['model_dir'],str(root/'models'))
            with self.assertRaisesRegex(ValueError,'Destination database'):
                consolidate(root,current,[old])

if __name__=='__main__':unittest.main()
