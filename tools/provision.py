import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from artwork_local.downloads import provision

parser = argparse.ArgumentParser()
parser.add_argument("--runtime-only", action="store_true")
parser.add_argument("--models-only", action="store_true")
parser.add_argument("--destination", type=Path, default=ROOT)
args = parser.parse_args()

def report(message, done, total):
    print(message, flush=True)

provision(ROOT / "model-manifest.json", args.destination, report,
          models=not args.runtime_only, runtime=not args.models_only)
