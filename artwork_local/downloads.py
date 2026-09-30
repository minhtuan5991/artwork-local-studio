from __future__ import annotations

import hashlib
import json
import os
import shutil
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(4 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def download_file(spec: dict, target: Path, report: Callable[[str, int, int], None], cancel=None):
    """Pinned, resumable download; success always verifies the published SHA-256."""
    target.parent.mkdir(parents=True, exist_ok=True)
    expected = int(spec["size"])
    if target.exists() and target.stat().st_size == expected:
        report("Kiểm tra " + target.name, expected, expected)
        if file_sha256(target) == spec["sha256"]:
            return target
        raise ValueError(f"Checksum không khớp: {target}. Chọn lại thư mục model hoặc đổi tên file lỗi.")
    partial = target.with_name(target.name + ".part")
    for attempt in range(4):
        if cancel and cancel.is_set():
            raise InterruptedError("Đã dừng tải; phần đã tải được giữ để tiếp tục.")
        offset = partial.stat().st_size if partial.exists() else 0
        if offset == expected:
            break
        if offset > expected:
            raise ValueError("File tải dở lớn hơn dung lượng dự kiến: " + str(partial))
        headers = {"User-Agent": "ArtworkLocalStudio/0.1.0"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(spec["url"], headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                if offset and response.status != 206:
                    offset = 0
                if response.status == 206:
                    content_range = response.headers.get("Content-Range", "")
                    if not content_range.startswith(f"bytes {offset}-"):
                        raise ValueError("Máy chủ trả vùng tải không đúng.")
                with partial.open("ab" if offset else "wb") as stream:
                    last_report = 0.0
                    while block := response.read(2 * 1024 * 1024):
                        if cancel and cancel.is_set():
                            raise InterruptedError("Đã dừng tải; phần đã tải được giữ để tiếp tục.")
                        stream.write(block)
                        offset += len(block)
                        if offset > expected:
                            raise ValueError("Dung lượng tải vượt manifest.")
                        if time.monotonic() - last_report > 0.5:
                            report(target.name, offset, expected)
                            last_report = time.monotonic()
                if offset != expected:
                    raise OSError(f"Tải chưa đủ: {offset}/{expected} byte")
            break
        except (OSError, urllib.error.URLError):
            if attempt == 3:
                raise
            if cancel:
                cancel.wait(2 * (attempt + 1))
            else:
                time.sleep(2 * (attempt + 1))
    report("Kiểm tra SHA-256: " + target.name, expected, expected)
    if file_sha256(partial) != spec["sha256"]:
        partial.rename(partial.with_name(partial.name + f".invalid-{int(time.time())}"))
        raise ValueError("Checksum không khớp; file đã được giữ riêng. Hãy tải lại.")
    os.replace(partial, target)
    report("Đã sẵn sàng: " + target.name, expected, expected)
    return target


def provision(manifest: Path, destination: Path, report=print, cancel=None,
              models=True, runtime=True):
    specs = json.loads(manifest.read_text(encoding="utf-8"))
    def progress(name, done, total):
        report(f"{name} · {done / 1e9:.2f}/{total / 1e9:.2f} GB", done, total)
    if runtime:
        runtime_dir = destination / "runtime"
        for spec in specs["runtime"]:
            archive = download_file(spec, destination / "downloads" / spec["name"], progress, cancel)
            runtime_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(archive) as bundle:
                for entry in bundle.infolist():
                    out = (runtime_dir / entry.filename).resolve()
                    if not out.is_relative_to(runtime_dir.resolve()):
                        raise ValueError("Archive runtime chứa đường dẫn không hợp lệ.")
                bundle.extractall(runtime_dir)
        # Release archives may contain nested folders. Keep executables beside DLLs.
        for source in list(runtime_dir.rglob("*")):
            if source.is_file() and source.suffix.lower() in {".dll", ".exe"} and source.parent != runtime_dir:
                target = runtime_dir / source.name
                if target.exists() and file_sha256(target) != file_sha256(source):
                    raise ValueError("Hai file runtime trùng tên nhưng khác nội dung: " + source.name)
                if not target.exists():
                    shutil.copy2(source, target)
    if models:
        for spec in specs["files"]:
            download_file(spec, destination / "models" / spec["name"], progress, cancel)
        license_spec = urllib.request.Request(
            "https://huggingface.co/Qwen/Qwen-Image-2.1/raw/main/LICENSE",
            headers={"User-Agent": "ArtworkLocalStudio/0.1.0"})
        with urllib.request.urlopen(license_spec, timeout=30) as response:
            (destination / "models" / "QWEN-LICENSE.txt").write_bytes(response.read(1024 * 1024))

