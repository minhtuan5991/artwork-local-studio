"""Deterministic input rotation; image-generation never receives an unrotated substitute."""
import math
from PIL import Image

def drag_rotation(initial_angle,initial_bearing,current_bearing,snap=False):
    delta=(current_bearing-initial_bearing+180)%360-180
    angle=initial_angle+delta
    if snap: angle=math.floor(angle/15+.5)*15
    return round((angle+180)%360-180,1)

def rotated_size(size,clockwise_degrees):
    width,height=size
    angle=float(clockwise_degrees)%360
    if angle in {0,180}: return width,height
    if angle in {90,270}: return height,width
    radians=math.radians(angle)
    a,b=round(math.cos(radians),15),round(math.sin(radians),15)
    cx,cy=width/2,height/2
    corners=[(a*(x-cx)+b*(y-cy)+cx,-b*(x-cx)+a*(y-cy)+cy) for x,y in [(0,0),(width,0),(width,height),(0,height)]]
    return math.ceil(max(x for x,y in corners))-math.floor(min(x for x,y in corners)),math.ceil(max(y for x,y in corners))-math.floor(min(y for x,y in corners))

def rotate_input(image,clockwise_degrees):
    angle=float(clockwise_degrees)
    if not math.isfinite(angle) or abs(angle)>360: raise ValueError("Góc xoay không hợp lệ.")
    if angle%360==0: return image.copy()
    if rotated_size(image.size,angle)[0]*rotated_size(image.size,angle)[1]>80_000_000:
        raise ValueError("Ảnh sau xoay quá lớn. Giảm kích thước nguồn trước.")
    return image.convert("RGBA").rotate(-angle,resample=Image.Resampling.BICUBIC,expand=True,fillcolor=(0,0,0,0))
