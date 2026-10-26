from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps
from .paths import default_data_dir, resource_base, is_installed

Image.MAX_IMAGE_PIXELS = 40_000_000
ACTIVE = {"preparing", "encoding", "generating", "decoding", "validating", "saving"}
STATUS_LABELS = {
    "queued": "Đang chờ", "preparing": "Chuẩn bị", "encoding": "Mã hóa nguồn",
    "generating": "Đang tạo ảnh", "decoding": "Giải mã", "validating": "Kiểm tra PNG",
    "saving": "Đang lưu", "completed": "Đã lưu", "failed": "Lỗi xử lý",
    "save_failed": "Lỗi lưu", "needs_review": "Cần kiểm tra", "canceled": "Đã hủy",
    "interrupted": "Bị gián đoạn",
}


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True)
class JobOptions:
    size: int = 1024
    background: str = "transparent"
    chroma: str = "#00FF00"
    detail: str = "preserve"
    steps: int = 20
    seed: int = 42
    exact_text: str = ""
    manual_prompt: str = ""

    @classmethod
    def from_dict(cls, data):
        fields = cls.__dataclass_fields__
        value = cls(**{key: data[key] for key in fields if key in data})
        if value.size not in {1024, 2048}:
            raise ValueError("Kích thước phải là 1K hoặc 2K.")
        if value.background not in {"transparent", "white", "chroma"}:
            raise ValueError("Chế độ nền không hợp lệ.")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value.chroma):
            raise ValueError("Màu chroma phải có dạng #00FF00.")
        if value.detail not in {"preserve", "restore"}:
            raise ValueError("Chế độ chi tiết không hợp lệ.")
        if not isinstance(value.steps, int) or not 5 <= value.steps <= 80:
            raise ValueError("Số bước phải từ 5 đến 80.")
        if not isinstance(value.seed, int) or not 0 <= value.seed < 2**32:
            raise ValueError("Seed phải từ 0 đến 4294967295.")
        if len(value.exact_text) > 3000 or len(value.manual_prompt) > 6000:
            raise ValueError("Nội dung prompt hoặc chữ xác nhận quá dài.")
        return value


class Settings:
    def __init__(self, root: Path, data_dir: Path | None = None):
        self.root = root
        self.data = data_dir or default_data_dir(root)
        self.data.mkdir(parents=True, exist_ok=True)
        self.path = self.data / "settings.json"
        resources=resource_base(root)
        output=Path.home()/"Pictures"/"Artwork Local Studio" if is_installed(root) else root/"output"/"Artwork Local Studio"
        self.values = {
            "output_dir": str(output),
            "model_dir": str(resources / "models"), "runtime_exe": str(resources / "runtime" / "sd-cli.exe"),
            "device": "cuda0", "max_vram": 3.5, "cache_type": "q8_0",
            "profile": "low", "timeout": 1800, "defaults": asdict(JobOptions()), "check_updates": True,
        }
        if self.path.exists():
            try:
                self.values.update(json.loads(self.path.read_text(encoding="utf-8")))
            except (ValueError, OSError) as exc:
                raise ValueError("Không đọc được cài đặt. File vẫn được giữ tại " + str(self.path)) from exc

    def save(self):
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(self.values, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, self.path)


def normalized_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        if source.format not in {"PNG", "JPEG", "WEBP"}:
            raise ValueError("Chỉ nhận PNG, JPEG và WebP.")
        if source.width * source.height > 40_000_000:
            raise ValueError("Ảnh vượt giới hạn 40 megapixel.")
        source.load()
        image = ImageOps.exif_transpose(source)
        icc = image.info.get("icc_profile")
        image = image.convert("RGBA")
        if icc:
            import io
            try:
                alpha = image.getchannel("A")
                rgb = ImageCms.profileToProfile(image.convert("RGB"),
                    ImageCms.ImageCmsProfile(io.BytesIO(icc)), ImageCms.createProfile("sRGB"), outputMode="RGB")
                image = rgb.convert("RGBA")
                image.putalpha(alpha)
            except (ValueError, OSError, ImageCms.PyCMSError):
                pass
        if min(image.size) < 16:
            raise ValueError("Ảnh quá nhỏ; cần ít nhất 16 pixel mỗi chiều.")
        # RGB in fully transparent pixels is invisible and must not evade duplicate detection.
        arr = np.array(image)
        arr[arr[:, :, 3] == 0, :3] = 0
        return Image.fromarray(arr)


def perceptual_hash(image: Image.Image) -> str:
    gray = np.asarray(image.convert("RGB").resize((32, 32), Image.Resampling.LANCZOS).convert("L"), dtype=float)
    n = np.arange(32)
    matrix = np.cos(np.pi * (2 * n[None, :] + 1) * n[:, None] / 64)
    low = (matrix @ gray @ matrix.T)[:8, :8].ravel()
    bits = low > np.median(low[1:])
    return f"{sum(int(bit) << i for i, bit in enumerate(bits)):016x}"


class Store:
    def __init__(self, data: Path):
        self.data = data
        self.blobs = data / "sources"
        self.results = data / "results"
        self.inbox = data / "inbox"
        for folder in (data, self.blobs, self.results, self.inbox):
            folder.mkdir(parents=True, exist_ok=True)
        self.db = data / "studio.sqlite3"
        with self.connection() as con:
            con.executescript("""
              CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, source_path TEXT NOT NULL,
                source_hash TEXT NOT NULL, pixel_hash TEXT NOT NULL, phash TEXT NOT NULL,
                job_key TEXT NOT NULL, options TEXT NOT NULL, output_dir TEXT NOT NULL,
                source_url TEXT DEFAULT '', source_page TEXT DEFAULT '',
                status TEXT NOT NULL, message TEXT DEFAULT '', progress INTEGER DEFAULT 0,
                created REAL NOT NULL, updated REAL NOT NULL, elapsed REAL DEFAULT 0,
                master_path TEXT DEFAULT '', output_path TEXT DEFAULT '', error TEXT DEFAULT '',
                metadata TEXT DEFAULT '{}', position INTEGER DEFAULT 0, visible INTEGER DEFAULT 1);
              CREATE INDEX IF NOT EXISTS queue_order ON jobs(status,position,created);
              CREATE TABLE IF NOT EXISTS ledger (job_key TEXT PRIMARY KEY,job_id TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, job_id TEXT,at REAL,message TEXT);
            """)

    @contextmanager
    def connection(self):
        con = sqlite3.connect(self.db, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=15000")
        try:
            with con:
                yield con
        finally:
            con.close()

    def recover(self):
        with self.connection() as con:
            placeholders = ",".join("?" for _ in ACTIVE)
            con.execute(f"UPDATE jobs SET status='interrupted',message=?,updated=? WHERE status IN ({placeholders})",
                        ("Ứng dụng đã đóng khi job chưa hoàn tất. Có thể tiếp tục.", time.time(), *ACTIVE))

    def prepare(self, path: Path):
        if path.stat().st_size > 25 * 1024 * 1024:
            raise ValueError("Ảnh vượt giới hạn 25 MB.")
        image = normalized_image(path)
        pixels = hashlib.sha256(str(image.size).encode() + image.tobytes()).hexdigest()
        source = self.blobs / (pixels + ".png")
        if not source.exists():
            tmp = source.with_name(source.stem + "." + uuid.uuid4().hex + ".tmp")
            image.save(tmp, "PNG")
            os.replace(tmp, source)
        return {"source_path": str(source), "source_hash": sha256_file(path),
                "pixel_hash": pixels, "phash": perceptual_hash(image), "name": path.name}

    def enqueue(self, prepared: dict, options: JobOptions, output_dir: str,
                metadata=None, force=False, accept_similar=False):
        metadata = metadata or {}
        option_data = asdict(options)
        # Background is export-only. A new job may reuse an earlier valid master.
        inference = {k: v for k, v in option_data.items() if k not in {"background", "chroma"}}
        inference_key = hashlib.sha256(canonical_json({"source": prepared["pixel_hash"],
                        "inference": inference, "prompt_revision": 4, "reference_preprocess_revision": 1, "cfg_scale": 1.0, "model": "Qwen-Image-2.1"}).encode()).hexdigest()
        job_key = hashlib.sha256(canonical_json({"inference": inference_key, "options": option_data}).encode()).hexdigest()
        if force:
            job_key += ":" + uuid.uuid4().hex
        now = time.time()
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            duplicate = con.execute("SELECT j.* FROM ledger l JOIN jobs j ON l.job_id=j.id WHERE l.job_key=?", (job_key,)).fetchone()
            if duplicate:
                return {"duplicate": "exact", "job": dict(duplicate)}
            similar = con.execute("SELECT * FROM jobs WHERE visible=1 ORDER BY created DESC LIMIT 500").fetchall()
            if not accept_similar:
                for row in similar:
                    if row["pixel_hash"] == prepared["pixel_hash"]:
                        continue
                    if (int(row["phash"], 16) ^ int(prepared["phash"], 16)).bit_count() <= 6:
                        return {"duplicate": "similar", "job": dict(row)}
            job_id = uuid.uuid4().hex
            position = con.execute("SELECT COALESCE(MAX(position),0)+1 FROM jobs").fetchone()[0]
            master = ""
            for row in similar:
                saved_metadata = json.loads(row["metadata"])
                if saved_metadata.get("inference_key") == inference_key and row["status"] == "completed" and Path(row["master_path"]).is_file():
                    master = row["master_path"]
                    break
            metadata = {**metadata, "inference_key": inference_key}
            con.execute("""INSERT INTO jobs(id,name,source_path,source_hash,pixel_hash,phash,job_key,options,output_dir,
                source_url,source_page,status,created,updated,metadata,position,master_path) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, prepared["name"], prepared["source_path"], prepared["source_hash"], prepared["pixel_hash"],
                 prepared["phash"], job_key, canonical_json(option_data), str(Path(output_dir).resolve()),
                 str(metadata.get("source_url", ""))[:2048], str(metadata.get("source_page", ""))[:2048],
                 "queued", now, now, canonical_json(metadata), position, master))
            con.execute("INSERT INTO ledger(job_key,job_id) VALUES(?,?)", (job_key, job_id))
            return {"job_id": job_id}

    def all(self, limit=200):
        with self.connection() as con:
            return [dict(r) for r in con.execute("SELECT * FROM jobs WHERE visible=1 ORDER BY position,created LIMIT ?", (limit,))]

    def get(self, job_id):
        with self.connection() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
            return dict(row) if row else None

    def next_job(self, ids=None):
        with self.connection() as con:
            if ids is not None:
                if not ids:
                    return None
                row = con.execute("SELECT * FROM jobs WHERE status='queued' AND visible=1 AND id IN (" +
                                  ",".join("?" for _ in ids) + ") ORDER BY position,created LIMIT 1", list(ids)).fetchone()
            else:
                row = con.execute("SELECT * FROM jobs WHERE status='queued' AND visible=1 ORDER BY position,created LIMIT 1").fetchone()
            return dict(row) if row else None

    def claim_next_job(self, ids=None):
        """Claim a visible job atomically so removal cannot race queue startup."""
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            if ids is not None and not ids:
                return None
            query = "SELECT * FROM jobs WHERE status='queued' AND visible=1"
            parameters = []
            if ids is not None:
                query += " AND id IN (" + ",".join("?" for _ in ids) + ")"
                parameters = list(ids)
            row = con.execute(query + " ORDER BY position,created LIMIT 1", parameters).fetchone()
            if not row:
                return None
            con.execute("UPDATE jobs SET status='preparing',message=?,updated=? WHERE id=?",
                        ("Chuẩn bị xử lý…", time.time(), row["id"]))
            return dict(row)

    def update(self, job_id, **values):
        allowed = {"status", "message", "progress", "elapsed", "master_path", "output_path", "error", "metadata", "position", "visible", "output_dir"}
        if not set(values).issubset(allowed):
            raise ValueError("Trường dữ liệu job không hợp lệ.")
        values["updated"] = time.time()
        with self.connection() as con:
            con.execute("UPDATE jobs SET " + ",".join(k + "=?" for k in values) + " WHERE id=?", (*values.values(), job_id))

    def log(self, job_id, message):
        with self.connection() as con:
            con.execute("INSERT INTO logs(job_id,at,message) VALUES(?,?,?)", (job_id, time.time(), message[-4000:]))
            con.execute("DELETE FROM logs WHERE job_id=? AND id NOT IN (SELECT id FROM logs WHERE job_id=? ORDER BY id DESC LIMIT 1000)", (job_id, job_id))

    def logs(self, job_id):
        with self.connection() as con:
            return [dict(r) for r in con.execute("SELECT * FROM logs WHERE job_id=? ORDER BY id DESC LIMIT 150", (job_id,))][::-1]

    def retry(self, job_id, rerun=False):
        job = self.get(job_id)
        if not job or job["status"] in ACTIVE or job["status"] == "queued":
            return
        # Candidates failing alpha must be regenerated, never silently converted to RGBA.
        clear_master = rerun or job["status"] == "needs_review"
        self.update(job_id, status="queued", error="", progress=0,
                    master_path="" if clear_master else job["master_path"], message="Đã đưa về Queue.")

    def hide(self, ids):
        removed, active = [], []
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            for job_id in dict.fromkeys(ids):
                job = con.execute("SELECT status,visible FROM jobs WHERE id=?", (job_id,)).fetchone()
                if not job or not job["visible"]:
                    continue
                if job["status"] in ACTIVE:
                    active.append(job_id)
                    continue
                con.execute("UPDATE jobs SET visible=0,updated=? WHERE id=?", (time.time(), job_id))
                removed.append(job_id)
        return {"removed": removed, "active": active}

    def restore(self, ids):
        restored = []
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            for job_id in dict.fromkeys(ids):
                # Restoring a removed pending job must not restart inference
                # automatically if a runner is still consuming the queue.
                cursor = con.execute("""UPDATE jobs SET visible=1,updated=?,
                    status=CASE WHEN status='queued' THEN 'canceled' ELSE status END,
                    message=CASE WHEN status='queued' THEN ? ELSE message END
                    WHERE id=? AND visible=0""",
                    (time.time(), "Đã khôi phục. Chọn Thử lại / lưu tiếp để đưa về Queue.", job_id))
                if cursor.rowcount:
                    restored.append(job_id)
        return restored

    def move(self, job_id, direction):
        rows = self.all(10000)
        for index, job in enumerate(rows):
            if job["id"] == job_id:
                other_index = index + direction
                if 0 <= other_index < len(rows):
                    other = rows[other_index]
                    self.update(job_id, position=other["position"])
                    self.update(other["id"], position=job["position"])
                return


def validate_rgba(path: Path, size: int):
    with Image.open(path) as image:
        image.load()
        if image.format != "PNG" or image.mode != "RGBA":
            raise ValueError("Model chưa xuất PNG RGBA. Không chuyển RGB thành alpha giả.")
        if image.size != (size, size):
            raise ValueError(f"Kết quả {image.width}×{image.height}, khác kích thước {size}×{size} đã chọn.")
        alpha = np.asarray(image.getchannel("A"))
        transparent = int(np.count_nonzero(alpha < 16))
        foreground = int(np.count_nonzero(alpha > 127))
        if transparent < 16 or foreground < 16:
            raise ValueError("Kênh alpha toàn đục hoặc ảnh trống; cần kiểm tra và tạo lại.")
        edge = int(np.count_nonzero(alpha[:2, :] > 127) + np.count_nonzero(alpha[-2:, :] > 127)
                   + np.count_nonzero(alpha[2:-2, :2] > 127) + np.count_nonzero(alpha[2:-2, -2:] > 127))
        if edge > 32:
            raise ValueError("Artwork chạm mép canvas; có nguy cơ bị cắt chữ/chi tiết. Cần kiểm tra và tạo lại với đủ vùng nguồn.")
        return {"width": size, "height": size, "transparent_pixels": transparent,
                "foreground_pixels": foreground, "edge_foreground_pixels": edge,
                "alpha_min": int(alpha.min()), "alpha_max": int(alpha.max())}


def safe_name(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", Path(name).stem).strip(" .")[:110] or "artwork"
    if re.match(r"^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\.|$)", name, re.I):
        name = "artwork_" + name
    return name


def export_png(master: Path, options: JobOptions, directory: Path, name: str,
               previous: str = "", metadata=None):
    validation = validate_rgba(master, options.size)
    directory.mkdir(parents=True, exist_ok=True)
    with Image.open(master) as source:
        source.load()
        if options.background == "transparent":
            output = source.copy()
        else:
            bg = "#FFFFFF" if options.background == "white" else options.chroma
            output = Image.new("RGBA", source.size, bg)
            output = Image.alpha_composite(output, source).convert("RGB")
    stem = f"{safe_name(name)}_{options.size // 1024}k_{options.background}"
    temp = directory / (".artwork-" + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("wb") as file:
            output.save(file, "PNG", compress_level=4)
            file.flush()
            os.fsync(file.fileno())
        expected = sha256_file(temp)
        with Image.open(temp) as check:
            check.load()
            if check.size != output.size or check.mode != output.mode:
                raise OSError("File ghi không đúng kích thước/kênh màu.")
            if options.background == "transparent":
                validate_rgba(temp, options.size)
        if previous:
            old = Path(previous)
            if old.is_file() and old.parent.resolve() == directory.resolve() and sha256_file(old) == expected:
                temp.unlink()
                return old, {**validation, "sha256": expected, "reused": True}
        number = 0
        while True:
            target = directory / (stem + (f" ({number})" if number else "") + ".png")
            try:
                # Exclusive reservation prevents a concurrent export overwriting a file.
                with target.open("xb"):
                    pass
                break
            except FileExistsError:
                number += 1
        try:
            os.replace(temp, target)
        except BaseException:
            if target.exists() and target.stat().st_size == 0:
                target.unlink()
            raise
        if sha256_file(target) != expected:
            raise OSError("Checksum sau ghi không khớp. Kết quả AI vẫn được giữ.")
        receipt = {**validation, "sha256": expected, "saved_at": time.time(), "background": options.background}
        # The DB receipt is authoritative; this sidecar is optional for portability.
        if metadata:
            try:
                target.with_suffix(".json").write_text(json.dumps({**metadata, "export": receipt}, ensure_ascii=False, indent=2), encoding="utf-8")
            except OSError:
                receipt["metadata_warning"] = "PNG đã lưu; chưa ghi được metadata JSON."
        return target, receipt
    finally:
        if temp.exists():
            temp.unlink()
