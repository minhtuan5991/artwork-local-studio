import hashlib,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
from artwork_local import __version__
folder=root/"release"/__version__
lines=[]
for path in sorted(folder.iterdir()):
    if path.suffix not in {".zip",".exe"}: continue
    digest=hashlib.file_digest(path.open("rb"),"sha256").hexdigest()
    lines.append(digest+"  "+path.name)
(folder/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n",encoding="utf-8")
print("\n".join(lines))
