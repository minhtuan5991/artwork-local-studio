from pathlib import Path
import sys
from artwork_local.native_host import serve, register_host, unregister_host
from artwork_local.paths import default_data_dir
if __name__=="__main__":
    root=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent
    if len(sys.argv)==2 and sys.argv[1] in {"--register","--unregister"}:
        operation=register_host if sys.argv[1]=="--register" else unregister_host
        operation(root,default_data_dir(root))
    else:
        serve(root)
