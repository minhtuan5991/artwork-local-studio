"""Strict, local Native Messaging transport. No shell commands or output paths from websites."""
import base64
import io
import json
import os
import struct
import subprocess
import sys
import uuid
from pathlib import Path
from PIL import Image, ImageOps
from .paths import default_data_dir

HOST_NAME="com.artworklocal.studio"
MAX_MESSAGE=36*1024*1024
MAX_IMAGE=25*1024*1024

def read_exact(stream,length):
    chunks=bytearray()
    while len(chunks)<length:
        block=stream.read(length-len(chunks))
        if not block: raise EOFError("Thông điệp bị cắt.")
        chunks.extend(block)
    return bytes(chunks)

def read_message(stream):
    header=stream.read(4)
    if not header: return None
    if len(header)!=4: raise ValueError("Header không hợp lệ.")
    size=struct.unpack("<I",header)[0]
    if not 0<size<=MAX_MESSAGE: raise ValueError("Thông điệp vượt giới hạn.")
    return json.loads(read_exact(stream,size).decode("utf-8"))

def write_message(stream,value):
    content=json.dumps(value,ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I",len(content))); stream.write(content); stream.flush()

def allowed_origin(root):
    manifest=json.loads((root/"browser-extension"/"manifest.json").read_text(encoding="utf-8"))
    import hashlib
    digest=hashlib.sha256(base64.b64decode(manifest["key"],validate=True)).hexdigest()[:32]
    return "chrome-extension://"+"".join(chr(97+int(c,16)) for c in digest)+"/"

def accept_payload(message,root,data):
    if not isinstance(message,dict) or message.get("action")!="enqueue":
        raise ValueError("Chỉ hỗ trợ gửi ảnh vào Queue.")
    encoded=message.get("image")
    if not isinstance(encoded,str) or len(encoded)>MAX_MESSAGE: raise ValueError("Ảnh không hợp lệ.")
    raw=base64.b64decode(encoded,validate=True)
    if len(raw)>MAX_IMAGE: raise ValueError("Ảnh vượt 25 MB.")
    with Image.open(io.BytesIO(raw)) as image:
        if image.format not in {"PNG","JPEG","WEBP"}: raise ValueError("Chỉ nhận PNG/JPEG/WebP.")
        if image.width*image.height>40_000_000 or min(image.size)<16: raise ValueError("Kích thước ảnh không hợp lệ.")
        image.load(); image=ImageOps.exif_transpose(image).convert("RGBA")
    options=message.get("options",{})
    if not isinstance(options,dict): raise ValueError("Thiết lập không hợp lệ.")
    allowed={"size":{1024,2048},"background":{"transparent","white","chroma"},"detail":{"preserve","restore"}}
    clean={}
    for key,values in allowed.items():
        if key in options:
            if options[key] not in values: raise ValueError("Thiết lập không hợp lệ: "+key)
            clean[key]=options[key]
    if "chroma" in options:
        import re
        if not isinstance(options["chroma"],str) or not re.fullmatch(r"#[0-9a-fA-F]{6}",options["chroma"]): raise ValueError("Màu chroma không hợp lệ.")
        clean["chroma"]=options["chroma"]
    inbox=data/"inbox"; inbox.mkdir(parents=True,exist_ok=True)
    receipt=uuid.uuid4().hex
    path=inbox/(receipt+".png"); image.save(path,"PNG")
    payload={"image":path.name,"name":str(message.get("name","web-artwork.png"))[:150],
        "source_url":str(message.get("source_url",""))[:2048],"source_page":str(message.get("source_page",""))[:2048],"options":clean}
    angle=message.get("source_rotation_degrees",0)
    import math
    if not isinstance(angle,(float,int)) or not math.isfinite(angle) or not -180<=angle<=180:
        path.unlink(missing_ok=True); raise ValueError("Góc xoay nguồn không hợp lệ.")
    payload["source_rotation_degrees"]=angle
    temp=inbox/(receipt+".tmp"); temp.write_text(json.dumps(payload,ensure_ascii=False),encoding="utf-8")
    os.replace(temp,inbox/(receipt+".json"))
    return {"ok":True,"receipt":receipt,"message":"Đã nhận ảnh vào inbox local. Xem Queue trong app."}

def register_host(root,data):
    import winreg
    exe=root/"ArtworkNativeHost.exe"
    if not exe.is_file(): raise ValueError("Cần bản app đã đóng gói có ArtworkNativeHost.exe.")
    host_dir=data/"native"; host_dir.mkdir(parents=True,exist_ok=True)
    manifest_path=host_dir/(HOST_NAME+".json")
    manifest_path.write_text(json.dumps(dict(name=HOST_NAME,description="Artwork Local Studio local image receiver",
        path=str(exe.resolve()),type="stdio",allowed_origins=[allowed_origin(root)]),indent=2),encoding="utf-8")
    # Installed app roots are read-only. Their default data directory is stable across updates.
    if data.resolve()!=default_data_dir(root).resolve():
        (root/"native-config.json").write_text(json.dumps({"data_dir":str(data.resolve())}),encoding="utf-8")
    for browser in ["Google\\Chrome","Microsoft\\Edge"]:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER,"Software\\"+browser+"\\NativeMessagingHosts\\"+HOST_NAME) as key:
            winreg.SetValueEx(key,"",0,winreg.REG_SZ,str(manifest_path.resolve()))

def unregister_host(root,data):
    import winreg
    expected=data/"native"/(HOST_NAME+".json")
    if not expected.is_file(): return
    try:
        content=json.loads(expected.read_text(encoding="utf-8"))
        if Path(content["path"]).resolve()!=(root/"ArtworkNativeHost.exe").resolve(): return
    except (OSError,ValueError,KeyError): return
    for browser in ["Google\\Chrome","Microsoft\\Edge"]:
        key_name="Software\\"+browser+"\\NativeMessagingHosts\\"+HOST_NAME
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_name) as key: value=winreg.QueryValue(key,None)
            if Path(value).resolve()==expected.resolve(): winreg.DeleteKey(winreg.HKEY_CURRENT_USER,key_name)
        except FileNotFoundError: pass
    expected.unlink(missing_ok=True)

def serve(root,stdin=None,stdout=None,origin=None,launch=True):
    stdin=stdin or sys.stdin.buffer; stdout=stdout or sys.stdout.buffer
    origin=origin or (sys.argv[1] if len(sys.argv)>1 else "")
    try:
        if origin!=allowed_origin(root): raise ValueError("Extension chưa được cho phép.")
        config=root/"native-config.json"
        data=Path(json.loads(config.read_text())["data_dir"]) if config.exists() else default_data_dir(root)
        message=read_message(stdin)
        if message is None: return
        result=accept_payload(message,root,data)
        if launch:
            # A named local event indicates the GUI is already running; it still consumes the inbox.
            import ctypes
            from ctypes import wintypes
            ctypes.windll.kernel32.OpenEventW.restype=wintypes.HANDLE
            ctypes.windll.kernel32.CloseHandle.argtypes=[wintypes.HANDLE]
            handle=ctypes.windll.kernel32.OpenEventW(0x00100000,False,"Local\\ArtworkLocalStudio-"+str(data.resolve()).replace("\\","_"))
            if handle: ctypes.windll.kernel32.CloseHandle(handle)
            else:
                subprocess.Popen([str(root/"ArtworkLocalStudio.exe"),"--data-dir",str(data)],cwd=root,
                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        write_message(stdout,result)
    except Exception as exc: write_message(stdout,{"ok":False,"error":str(exc)[:1000]})
