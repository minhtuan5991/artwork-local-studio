import base64,io,json,tempfile,unittest
from dataclasses import replace
from pathlib import Path
from PIL import Image,ImageDraw,PngImagePlugin
from artwork_local.core import Settings,Store,JobOptions,export_png,validate_rgba,sha256_file,safe_name
from artwork_local.engine import QueueRunner,build_command
from artwork_local.native_host import accept_payload,read_message,write_message,serve,allowed_origin
ROOT=Path(__file__).resolve().parents[1]

class FakeEngine:
    """Synthetic test fixture only; never used as the application's AI engine."""
    def __init__(self,opaque=False,cancel=False): self.calls=0; self.opaque=opaque; self.cancel=cancel
    def generate(self,source,output,options,cancel,report):
        self.calls+=1
        if self.cancel: raise InterruptedError("Test cancellation")
        output.parent.mkdir(parents=True,exist_ok=True)
        im=Image.new("RGBA",(options.size,options.size),(0,0,0,255 if self.opaque else 0))
        ImageDraw.Draw(im).rectangle((200,200,800,800),fill=(255,0,0,255)); im.save(output)
        return {"test_only":True}

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.store=Store(self.root/"data"); self.source=self.root/"input.png"
        im=Image.new("RGBA",(256,256),"white"); ImageDraw.Draw(im).ellipse((40,40,190,190),fill="red"); im.save(self.source)
        self.prepared=self.store.prepare(self.source); self.options=JobOptions()
    def tearDown(self): self.temp.cleanup()
    def enqueue(self,options=None,output=None,force=False):
        return self.store.enqueue(self.prepared,options or self.options,str(output or self.root/"output"),force=force)["job_id"]
    def run_job(self,engine,ids=None):
        runner=QueueRunner(self.store,{}, {},lambda *args:None,ids=ids,engine=engine)
        runner.start(); runner.join(10); self.assertFalse(runner.is_alive())
    def test_duplicate_survives_hide_restart(self):
        jid=self.enqueue(); self.store.hide([jid]); store=Store(self.store.data)
        result=store.enqueue(store.prepare(self.source),self.options,str(self.root/"other"))
        self.assertEqual(result["duplicate"],"exact"); self.assertEqual(result["job"]["id"],jid)
    def test_metadata_only_change_is_duplicate(self):
        with Image.open(self.source) as im:
            meta=PngImagePlugin.PngInfo(); meta.add_text("note","different metadata")
            other=self.root/"meta.png"; im.save(other,pnginfo=meta)
        self.enqueue(); self.assertEqual(self.store.enqueue(self.store.prepare(other),self.options,str(self.root/"output"))["duplicate"],"exact")
    def test_different_seed_is_new(self):
        self.enqueue(); self.assertIn("job_id",self.store.enqueue(self.prepared,replace(self.options,seed=43),str(self.root/"output")))
    def test_force_duplicate(self):
        self.assertNotEqual(self.enqueue(),self.enqueue(force=True))
    def test_similar_is_warning(self):
        self.enqueue()
        with Image.open(self.source) as im:
            im.putpixel((0,0),(240,240,240,255)); other=self.root/"near.png"; im.save(other)
        prepared=self.store.prepare(other)
        self.assertEqual(self.store.enqueue(prepared,self.options,str(self.root/"output"))["duplicate"],"similar")
        self.assertIn("job_id",self.store.enqueue(prepared,self.options,str(self.root/"output"),accept_similar=True))
    def test_recover_active_jobs(self):
        jid=self.enqueue(); self.store.update(jid,status="generating"); self.store.recover()
        self.assertEqual(self.store.get(jid)["status"],"interrupted")
    def test_persistent_order_and_selection(self):
        a=self.enqueue(); b=self.enqueue(replace(self.options,seed=43)); self.store.move(b,-1)
        self.assertEqual(self.store.next_job()["id"],b); self.run_job(FakeEngine(),[a])
        self.assertEqual(self.store.get(a)["status"],"completed"); self.assertEqual(self.store.get(b)["status"],"queued")
    def test_real_alpha_gate_and_composites(self):
        jid=self.enqueue(); self.run_job(FakeEngine()); job=self.store.get(jid); self.assertEqual(job["status"],"completed")
        master=Path(job["master_path"]); self.assertEqual(validate_rgba(master,1024)["alpha_min"],0)
        for background,color in [("white",(255,255,255)),("chroma",(0,255,0))]:
            path,_=export_png(master,replace(self.options,background=background),self.root/"exports","test")
            with Image.open(path) as im: self.assertEqual(im.mode,"RGB"); self.assertEqual(im.getpixel((0,0)),color)
    def test_rgb_and_opaque_rgba_rejected(self):
        p=self.root/"invalid.png"
        for mode in ["RGB","RGBA"]:
            Image.new(mode,(1024,1024),"white").save(p)
            with self.assertRaises(ValueError): validate_rgba(p,1024)
    def test_wrong_resolution_rejected(self):
        with self.assertRaises(ValueError): validate_rgba(self.source,1024)
    def test_clipped_foreground_rejected(self):
        path=self.root/"clipped.png"
        im=Image.new("RGBA",(1024,1024),(0,0,0,0))
        ImageDraw.Draw(im).rectangle((0,400,600,600),fill="red"); im.save(path)
        with self.assertRaisesRegex(ValueError,"chạm mép"): validate_rgba(path,1024)
    def test_quality_candidate_retained(self):
        jid=self.enqueue(); self.run_job(FakeEngine(opaque=True))
        job=self.store.get(jid); self.assertEqual(job["status"],"needs_review"); self.assertTrue(Path(job["master_path"]).is_file())
        self.store.retry(jid); self.assertEqual(self.store.get(jid)["master_path"],"")
    def test_save_failure_retry_does_not_regenerate(self):
        blocker=self.root/"not-a-directory"; blocker.write_text("keep")
        jid=self.enqueue(output=blocker); engine=FakeEngine(); self.run_job(engine)
        self.assertEqual(self.store.get(jid)["status"],"save_failed")
        self.store.update(jid,output_dir=str(self.root/"fixed")); self.store.retry(jid); self.run_job(engine)
        self.assertEqual(engine.calls,1); self.assertEqual(self.store.get(jid)["status"],"completed"); self.assertEqual(blocker.read_text(),"keep")
    def test_cancel_keeps_source(self):
        jid=self.enqueue(); self.run_job(FakeEngine(cancel=True))
        self.assertEqual(self.store.get(jid)["status"],"canceled"); self.assertTrue(Path(self.prepared["source_path"]).is_file())
    def test_reuse_rgba_for_background_job(self):
        jid=self.enqueue(); engine=FakeEngine(); self.run_job(engine)
        other=self.enqueue(replace(self.options,background="white")); self.run_job(engine)
        self.assertEqual(engine.calls,1); self.assertEqual(self.store.get(jid)["master_path"],self.store.get(other)["master_path"])
    def test_no_overwrite_and_idempotent_receipt(self):
        jid=self.enqueue(); self.run_job(FakeEngine()); job=self.store.get(jid)
        original=Path(job["output_path"]); checksum=sha256_file(original)
        new,_=export_png(Path(job["master_path"]),self.options,original.parent,"input.png")
        self.assertNotEqual(original,new); self.assertEqual(checksum,sha256_file(original))
        reused,receipt=export_png(Path(job["master_path"]),self.options,original.parent,"input.png",previous=str(original))
        self.assertEqual(reused,original); self.assertTrue(receipt["reused"])
    def test_invalid_options_and_windows_name(self):
        for value in [{"size":512},{"background":"fake"},{"chroma":"red"},{"seed":-1},{"steps":0}]:
            with self.assertRaises(ValueError): JobOptions.from_dict(value)
        self.assertEqual(safe_name("CON.png"),"artwork_CON"); self.assertNotIn(":",safe_name("bad:name?.png"))
    def test_command_paths_and_unicode_no_shell(self):
        manifest=json.loads((ROOT/"model-manifest.json").read_text()); config=Settings(self.root).values
        command=build_command(config,manifest,self.source,self.root/"ảnh mới.png",replace(self.options,exact_text='$(bad) "'+chr(96)+'x"'))
        for arg in ["--fa","--llm_vision","--mmap"]: self.assertIn(arg,command)
        self.assertEqual(command[command.index("-o")+1],str((self.root/"ảnh mới.png").resolve()))
    def test_native_protocol_roundtrip_and_origin(self):
        stream=io.BytesIO(); write_message(stream,{"action":"enqueue","x":"ảnh"}); stream.seek(0); self.assertEqual(read_message(stream)["x"],"ảnh")
        self.assertEqual(allowed_origin(ROOT),"chrome-extension://nimddfjhgiebfhfpgecahpgllikefljc/")
        output=io.BytesIO(); serve(ROOT,io.BytesIO(),output,origin="chrome-extension://attacker/",launch=False); output.seek(0)
        self.assertFalse(read_message(output)["ok"])
    def test_native_spool_and_untrusted_fields(self):
        payload={"action":"enqueue","image":base64.b64encode(self.source.read_bytes()).decode(),
            "name":"test.png","source_url":"$(not a shell)","output_dir":"C:/wrong","options":{"background":"white","command":"bad"}}
        result=accept_payload(payload,ROOT,self.root/"native")
        data=json.loads((self.root/"native"/"inbox"/(result["receipt"]+".json")).read_text(encoding="utf-8"))
        self.assertNotIn("output_dir",data); self.assertNotIn("command",data["options"]); self.assertEqual(data["options"]["background"],"white")
    def test_native_rejects_bad_image_and_size(self):
        for payload in [{"action":"shell","image":""},{"action":"enqueue","image":"!!"},
                {"action":"enqueue","image":base64.b64encode(b"not an image").decode()}]:
            with self.assertRaises(Exception): accept_payload(payload,ROOT,self.root/"native")
        import struct
        with self.assertRaises(ValueError): read_message(io.BytesIO(struct.pack("<I",100*1024*1024)))

if __name__=="__main__": unittest.main()
