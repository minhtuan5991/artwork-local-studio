import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from artwork_local.core import export_png,JobOptions
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]
folder=root/"test-output"/(sys.argv[1] if len(sys.argv)>1 else "benchmark-flash")
master=folder/"qwen.png"
for background in ["white","chroma"]:
    export_png(master,JobOptions(background=background),folder,"qwen")
with Image.open(master) as result:
    checker=Image.new("RGBA",result.size,"#E0E6E0"); draw=ImageDraw.Draw(checker)
    for y in range(0,1024,24):
        for x in range(0,1024,24):
            if (x//24+y//24)%2: draw.rectangle((x,y,x+23,y+23),fill="#F0F3F0")
    Image.alpha_composite(checker,result).convert("RGB").save(folder/"checker-preview.png")
