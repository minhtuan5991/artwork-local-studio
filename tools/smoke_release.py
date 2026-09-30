import base64,json,os,subprocess,sys,time,sqlite3,struct
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from artwork_local.native_host import allowed_origin,write_message,read_message
from artwork_local import __version__
import io
release=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else root/"release"/__version__/"ArtworkLocalStudio"
folder=root/"test-output"/("release-smoke-"+__version__)
folder.mkdir(parents=True,exist_ok=True)
data=folder/"data"; screenshot=folder/"screenshot.png"
configuration=release/"native-config.json"
previous=configuration.read_bytes() if configuration.exists() else None
configuration.write_text(json.dumps({"data_dir":str(data)}),encoding="utf-8")
environment=dict(os.environ,QT_QPA_PLATFORM="offscreen")
gui=None
try:
    gui=subprocess.Popen([str(release/"ArtworkLocalStudio.exe"),"--data-dir",str(data),"--screenshot",str(screenshot)],env=environment,
        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    # The native host must correctly reject an untrusted extension without starting a GUI.
    bad=subprocess.run([str(release/"ArtworkNativeHost.exe"),"chrome-extension://attacker/"],input=b"",capture_output=True,timeout=20,env=environment)
    reply=read_message(io.BytesIO(bad.stdout))
    assert reply and not reply["ok"],repr(bad.stdout)
    source=folder/"fixture.png"
    from PIL import Image,ImageDraw
    fixture=Image.new("RGBA",(200,400),"#AAAAAA"); ImageDraw.Draw(fixture).rectangle((30,50,170,350),fill="#FFE500"); fixture.save(source)
    payload={"action":"enqueue","image":base64.b64encode(source.read_bytes()).decode(),"name":"native-smoke.png",
        "source_url":"https://example.invalid/fixture.png","options":{"size":1024,"background":"transparent"}}
    stream=io.BytesIO(); write_message(stream,payload)
    host=subprocess.run([str(release/"ArtworkNativeHost.exe"),allowed_origin(release)],input=stream.getvalue(),capture_output=True,timeout=20,env=environment)
    reply=read_message(io.BytesIO(host.stdout)); assert reply and reply["ok"],repr(host.stdout)
    # A screenshot-only GUI may exit before its next inbox tick; launch again to
    # verify persistence and intake without running inference.
    gui.wait(timeout=20)
    assert gui.returncode==0,gui.returncode
    process=subprocess.run([str(release/"ArtworkLocalStudio.exe"),"--data-dir",str(data),"--screenshot",str(screenshot)],env=environment,timeout=20,
        creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
    assert process.returncode==0,process.returncode
    # Main screenshot timer runs at 1.2s; native inbox timer is at 1.5s. Run a
    # non-visual GUI until its inbox is consumed, then terminate test-owned process.
    con=sqlite3.connect(data/"studio.sqlite3")
    count=con.execute("SELECT count(*) FROM jobs").fetchone()[0]; con.close()
    if count==0:
        gui=subprocess.Popen([str(release/"ArtworkLocalStudio.exe"),"--data-dir",str(data)],env=environment,
            creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            time.sleep(.25)
            con=sqlite3.connect(data/"studio.sqlite3")
            row=con.execute("SELECT status,name FROM jobs LIMIT 1").fetchone(); con.close()
            if row: break
        assert row and row[0]=="queued" and row[1]=="native-smoke.png",row
        gui.terminate(); gui.wait(timeout=10)
    assert screenshot.is_file(),"No GUI screenshot"
    result={"compiled_gui":True,"compiled_host":True,"origin_rejected":True,"native_intake_queued":True}
    (folder/"result.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result))
finally:
    if gui and gui.poll() is None: gui.terminate(); gui.wait(timeout=10)
    if previous is not None: configuration.write_bytes(previous)
    elif configuration.exists(): configuration.unlink()
