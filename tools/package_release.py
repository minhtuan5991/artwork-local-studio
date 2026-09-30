import json,zipfile,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from artwork_local import __version__
app=root/"release"/__version__/"ArtworkLocalStudio"
archive=app.parent/("ArtworkLocalStudio-"+__version__+"-Windows.zip")
with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED,compresslevel=5) as bundle:
    for path in app.rglob("*"):
        relative=path.relative_to(app)
        if relative.parts[0] in {"data","output","models","runtime","downloads"} or path.name in {"native-config.json","installation.json"}:
            continue
        if path.is_file(): bundle.write(path,Path("ArtworkLocalStudio")/relative)
with zipfile.ZipFile(archive) as bundle:
    assert bundle.testzip() is None
    assert any(name.endswith("ArtworkLocalStudio.exe") for name in bundle.namelist())
    assert not any(name.startswith("ArtworkLocalStudio/data/") for name in bundle.namelist())
print(json.dumps({"archive":str(archive),"size":archive.stat().st_size,"files":len(bundle.namelist())}))
