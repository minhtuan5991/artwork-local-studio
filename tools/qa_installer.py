"""Silent install/uninstall in an isolated workspace; preserve browser registration."""
import json,os,subprocess,sys,uuid,winreg
from pathlib import Path
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
from artwork_local import __version__
from artwork_local.native_host import HOST_NAME
base=root/"test-output"/("installer-"+__version__+"-"+uuid.uuid4().hex[:8])
base.mkdir(parents=True)
installed=base/"app"; local=base/"local"
assert installed.resolve().is_relative_to((root/"test-output").resolve())
uninstall_key=r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{C69ADC52-8C70-4C13-A2A3-EC59B32D79C8}_is1"
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,uninstall_key) as key:
        previous=Path(winreg.QueryValueEx(key,"InstallLocation")[0]).resolve()
    if not previous.is_relative_to((root/"test-output").resolve()) or not previous.parent.name.startswith("installer-"+__version__+"-"):
        raise RuntimeError("An installed user copy already exists; refusing to replace its uninstall registration during QA.")
    # Only recover a prior test-owned install; never move/delete an installed user copy.
    subprocess.run([str(previous/"unins000.exe"),"/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART"],check=True,timeout=60)
except FileNotFoundError: pass
def registered_hosts():
    values={}
    for browser in [r"Google\Chrome",r"Microsoft\Edge"]:
        key_name="Software\\"+browser+"\\NativeMessagingHosts\\"+HOST_NAME
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_name) as key: values[browser]=winreg.QueryValue(key,None)
        except FileNotFoundError: values[browser]=None
    return values
before=registered_hosts()
environment=dict(os.environ,LOCALAPPDATA=str(local),QT_QPA_PLATFORM="offscreen")
setup=root/"release"/__version__/("ArtworkLocalStudio-Setup-"+__version__+".exe")
subprocess.run([str(setup),"/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART","/NOCLOSEAPPLICATIONS","/NORESTARTAPPLICATIONS",
    "/NOICONS","/TESTMODE=1","/DIR="+str(installed),"/LOG="+str(base/"install.log")],env=environment,check=True,timeout=120)
assert registered_hosts()==before
assert (installed/"installation.json").is_file()
assert (installed/"assets"/"app.ico").is_file()
assert not (installed/"models").exists()
assert json.loads((installed/"browser-extension"/"manifest.json").read_text(encoding="utf-8"))["version"]==__version__
screenshot=base/"installed-ui.png"
subprocess.run([str(installed/"ArtworkLocalStudio.exe"),"--screenshot",str(screenshot)],env=environment,check=True,timeout=30,
    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
data=local/"ArtworkLocalStudio"
assert (data/"studio.sqlite3").is_file() and screenshot.is_file()
assert not (installed/"data").exists()
preserved=data/"models"/"preserve.txt"; preserved.parent.mkdir(exist_ok=True); preserved.write_text("Model data must survive uninstall.")
subprocess.run([str(installed/"unins000.exe"),"/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART","/LOG="+str(base/"uninstall.log")],
    env=environment,check=True,timeout=60)
assert preserved.is_file() and (data/"studio.sqlite3").is_file()
assert not (installed/"ArtworkLocalStudio.exe").exists()
assert registered_hosts()==before
result={"installer":True,"installed_gui":True,"uninstall":True,"userdata_retained":True,"existing_browser_registration_unchanged":True}
(base/"result.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result))
