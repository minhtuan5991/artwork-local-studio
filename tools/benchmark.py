import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json, threading, time
import argparse
from PIL import Image, ImageDraw, ImageFont
from artwork_local.core import Settings, JobOptions, validate_rgba
from artwork_local.engine import CliEngine
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
root = Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument("--variant",default="benchmark")
parser.add_argument("--cache",default="disabled")
parser.add_argument("--vram",type=float,default=2.5)
parser.add_argument("--crop",action="store_true")
args=parser.parse_args()
folder = root / "test-output" / args.variant
folder.mkdir(parents=True, exist_ok=True)
image = Image.new("RGB", (1024, 1024), "#d5d5d0")
draw = ImageDraw.Draw(image)
draw.polygon([(250,130),(380,80),(644,80),(774,130),(900,330),(750,420),(730,940),(294,940),(274,420),(124,330)], fill="#253942")
draw.ellipse((400,280,624,504), fill="#f7bb43", outline="#f5e8d0", width=12)
draw.polygon([(512,310),(532,370),(596,370),(546,408),(566,470),(512,432),(458,470),(478,408),(428,370),(492,370)], fill="#253942")
font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 56)
draw.text((512,565), "ARTWORK 42", anchor="mm", font=font, fill="#f5e8d0")
image.save(folder / "mockup.png")
if args.crop:
    image.crop((290,230,735,650)).save(folder / "mockup.png")
config = Settings(root).values
config["timeout"] = 600
config["cache_type"] = args.cache
config["max_vram"] = args.vram
manifest = json.loads((root/"model-manifest.json").read_text())
started=time.monotonic()
def report(stage, progress, message, line=""):
    print(line or message or "", flush=True)
    with (folder/"runtime.log").open("a", encoding="utf-8") as file:
        file.write((line or message or "")+"\n")
options=JobOptions(exact_text="ARTWORK 42")
result={"options":options.__dict__, "config":config}
try:
    result.update(CliEngine(config,manifest).generate(folder/"mockup.png",folder/"qwen.png",options,threading.Event(),report))
    result["validation"]=validate_rgba(folder/"qwen.png",1024)
    result["success"]=True
except Exception as exc:
    result.update(success=False,error=str(exc))
finally:
    result["wall_seconds"]=round(time.monotonic()-started,3)
    (folder/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False),flush=True)
