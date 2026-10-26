import json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from artwork_local.core import JobOptions,sha256_file
from artwork_local.engine import check_job_resources,prepare_reference,runtime_error,CliEngine

class MemoryTests(unittest.TestCase):
    def test_native_2k_rejected_before_loading_on_6gb(self):
        with tempfile.TemporaryDirectory() as folder:
            exe=Path(folder)/"runtime.exe"; exe.write_bytes(b"")
            engine=CliEngine({"runtime_exe":str(exe),"model_dir":folder,"device":"cuda0","max_vram":4.5},{"files":[]})
            with patch("artwork_local.engine.subprocess.run",return_value=SimpleNamespace(returncode=0,stdout="0, 6144\n")), patch("artwork_local.engine.subprocess.Popen") as process:
                with self.assertRaisesRegex(ValueError,"1K"):
                    engine.generate(Path(folder)/"input.png",Path(folder)/"out.png",JobOptions(size=2048),None,lambda *args:None)
                process.assert_not_called()
    def test_1k_and_cpu_do_not_query_gpu(self):
        with patch("artwork_local.engine.subprocess.run") as query:
            check_job_resources({"device":"cuda0","max_vram":3.5},JobOptions())
            check_job_resources({"device":"cpu"},JobOptions(size=2048))
            query.assert_not_called()
    def test_2k_budget_is_checked_on_larger_gpu(self):
        with patch("artwork_local.engine.subprocess.run",return_value=SimpleNamespace(returncode=0,stdout="0, 24576\n")):
            with self.assertRaisesRegex(ValueError,"Giới hạn VRAM"):
                check_job_resources({"device":"cuda0","max_vram":3.5},JobOptions(size=2048))
            check_job_resources({"device":"cuda0","max_vram":12},JobOptions(size=2048))
    def test_large_reference_resized_without_touching_original(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/"source.png"; output=Path(folder)/"result"/"output.png"
            image=Image.new("RGBA",(4096,2048),(0,0,0,0)); image.paste((255,0,0,255),(512,256,3584,1792)); image.save(source)
            checksum=sha256_file(source)
            path,metadata=prepare_reference(source,output,JobOptions(),{"profile":"low"})
            self.assertEqual(sha256_file(source),checksum)
            self.assertTrue(metadata["reference_resized"])
            self.assertEqual(metadata["reference_size"],[1024,512])
            with Image.open(path) as im:
                self.assertEqual(im.mode,"RGBA"); self.assertEqual(im.getpixel((0,0))[3],0)
    def test_small_reference_uses_original_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"input.png"; Image.new("RGBA",(200,300),"red").save(path)
            actual,metadata=prepare_reference(path,Path(folder)/"output.png",JobOptions(),{})
            self.assertEqual(actual,path); self.assertFalse(metadata["reference_resized"])
    def test_memory_error_is_actionable_and_preserves_diagnostics(self):
        message=str(runtime_error(1,["cannot make enough memory available on CUDA0","sampling failed"],JobOptions(size=2048)))
        self.assertIn("Thiếu bộ nhớ",message); self.assertIn("1K",message); self.assertIn("sampling failed",message)
        self.assertIn("mã 7",str(runtime_error(7,["invalid model"],JobOptions())))

if __name__=="__main__": unittest.main()
