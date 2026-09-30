"""Workspace-local build tools fetched from official, checksum-pinned releases."""
import hashlib
import subprocess
import urllib.request
import zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
folder=root/".tools"
folder.mkdir(exist_ok=True)
specs=[
 ("gh.zip","https://github.com/cli/cli/releases/download/v2.102.0/gh_2.102.0_windows_amd64.zip","ae64e556ecc240b200f7eba60d550e4bb60d78e860e69dd88c449405b86067f4"),
 ("inno-setup.exe","https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe","9c73c3bae7ed48d44112a0f48e66742c00090bdb5bef71d9d3c056c66e97b732")]
for name,url,digest in specs:
    target=folder/name
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest()!=digest:
        temp=target.with_suffix(".part")
        with urllib.request.urlopen(url,timeout=45) as response,temp.open("wb") as stream:
            while block:=response.read(1024*1024): stream.write(block)
        if hashlib.sha256(temp.read_bytes()).hexdigest()!=digest: raise ValueError("Checksum mismatch: "+name)
        temp.replace(target)
    print("Verified "+name,flush=True)
with zipfile.ZipFile(folder/"gh.zip") as bundle:
    destination=folder/"gh"
    for info in bundle.infolist():
        if not (destination/info.filename).resolve().is_relative_to(destination.resolve()): raise ValueError("Invalid ZIP path")
    bundle.extractall(destination)
compiler=folder/"inno"/"ISCC.exe"
if not compiler.exists():
    subprocess.run([str(folder/"inno-setup.exe"),"/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART","/CURRENTUSER","/NOICONS",
        "/DIR="+str(folder/"inno")],check=True,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
print("Build tools ready",flush=True)
