import sys
from pathlib import Path
release=Path(sys.argv[1])
# Supported Windows versions provide the ICU API Qt needs. A bundled Python ICU
# with versioned symbols must not shadow that Windows DLL.
for name in ["icuuc.dll","icudt78.dll","icuuc-unused.dll"]:
    generated=release/"_internal"/name
    if generated.is_file(): generated.unlink()
print("Release configured without machine-specific paths.")
