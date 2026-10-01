import json,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from artwork_local import __version__
source=root/"browser-extension";folder=root/"release"/__version__;folder.mkdir(parents=True,exist_ok=True)
target=folder/("ArtworkLocalStudio-Extension-"+__version__+".zip")
with zipfile.ZipFile(target,"w",zipfile.ZIP_DEFLATED) as bundle:
    for path in sorted(source.rglob("*")):
        if path.is_file(): bundle.write(path,Path("browser-extension")/path.relative_to(source))
with zipfile.ZipFile(target) as bundle:
    assert bundle.testzip() is None
    assert json.loads(bundle.read("browser-extension/manifest.json"))["version"]==__version__
print(str(target))
