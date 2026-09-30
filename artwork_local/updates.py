"""Public release metadata only. No image, model or user data is uploaded."""
import json
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError

REPOSITORY="minhtuan5991/artwork-local-studio"
RELEASES_URL="https://github.com/"+REPOSITORY+"/releases"
API_URL="https://api.github.com/repos/"+REPOSITORY+"/releases/latest"


def version_tuple(value):
    match=re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)",value)
    if not match: raise ValueError("Phiên bản release không hợp lệ.")
    return tuple(map(int,match.groups()))


def parse_release(payload,current):
    if not isinstance(payload,dict): raise ValueError("Dữ liệu release không hợp lệ.")
    if payload.get("draft") or payload.get("prerelease"): return {"state":"current"}
    tag=payload.get("tag_name","")
    latest=version_tuple(tag); installed=version_tuple(current)
    if latest<=installed: return {"state":"current","version":tag.lstrip("v")}
    # Construct our own URL rather than trusting arbitrary links in remote metadata.
    return {"state":"available","version":tag.lstrip("v"),"url":RELEASES_URL+"/tag/"+tag,
            "notes":str(payload.get("body",""))[:6000]}


def check_latest(current,opener=urlopen):
    request=Request(API_URL,headers={"Accept":"application/vnd.github+json","User-Agent":"ArtworkLocalStudio/"+current})
    try:
        with opener(request,timeout=10) as response:
            raw=response.read(256_001)
        if len(raw)>256_000: raise ValueError("Dữ liệu cập nhật vượt giới hạn.")
        return parse_release(json.loads(raw),current)
    except HTTPError as exc:
        if exc.code==404: return {"state":"unpublished"}
        return {"state":"error","message":"GitHub chưa phản hồi ("+str(exc.code)+")."}
    except Exception:
        return {"state":"error","message":"Không kiểm tra được cập nhật. Kiểm tra kết nối mạng rồi thử lại."}
