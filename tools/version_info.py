from pathlib import Path
import sys
root=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(root))
from artwork_local import __version__
version=tuple(map(int,__version__.split(".")))+(0,)
source="""VSVersionInfo(
  ffi=FixedFileInfo(filevers=%r, prodvers=%r, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)),
  kids=[StringFileInfo([StringTable('040904B0', [
    StringStruct('CompanyName','Artwork Local Studio'),
    StringStruct('FileDescription','Artwork Local Studio - Local Qwen artwork editor'),
    StringStruct('FileVersion','%s'),
    StringStruct('ProductName','Artwork Local Studio'),
    StringStruct('ProductVersion','%s')])]), VarFileInfo([VarStruct('Translation',[1033,1200])])])
"""%(version,version,__version__,__version__)
(root/"build").mkdir(exist_ok=True)
(root/"build"/"version-info.txt").write_text(source,encoding="utf-8")
