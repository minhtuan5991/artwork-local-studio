import json
import subprocess
from .engine import NO_WINDOW

def hardware_summary():
    gpu = "Chưa nhận GPU NVIDIA"
    ram = ""
    try:
        result = subprocess.run(["nvidia-smi","--query-gpu=name,memory.total","--format=csv,noheader"],
            capture_output=True,text=True,creationflags=NO_WINDOW,timeout=5)
        if result.returncode == 0:
            gpu = result.stdout.strip().splitlines()[0]
    except (OSError,subprocess.TimeoutExpired):
        pass
    try:
        import ctypes
        class Memory(ctypes.Structure):
            _fields_=[("length",ctypes.c_ulong),("load",ctypes.c_ulong)]+[(name,ctypes.c_ulonglong) for name in
                ["total","available","page","available_page","virtual","available_virtual","extended"]]
        memory=Memory()
        memory.length=ctypes.sizeof(memory)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(memory))
        ram=f"RAM {memory.total / 2**30:.1f} GB"
    except Exception:
        pass
    return " · ".join(filter(None,[gpu,ram]))
