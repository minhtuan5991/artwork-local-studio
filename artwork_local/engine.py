from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
import uuid
from pathlib import Path

from .core import JobOptions, Store, canonical_json, export_png, sha256_file, validate_rgba, normalized_image

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def check_job_resources(config, options):
    """Fail before loading weights for known unsupported native-2K budgets."""
    device = str(config.get("device", "cuda0"))
    if options.size <= 1024 or not re.fullmatch(r"cuda\d+", device):
        return
    total = None
    try:
        result = subprocess.run(["nvidia-smi", "--query-gpu=index,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5, creationflags=NO_WINDOW)
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                index, memory = line.split(",", 1)
                if int(index.strip()) == int(device[4:]):
                    total = float(memory.strip())
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    if total is not None and total <= 8192:
        raise ValueError(f"Thiếu VRAM cho Qwen native 2K: GPU này có {total/1024:.1f} GiB. "
            "Chọn Kích thước 1K rồi thêm ảnh vào Queue. 2K trên cấu hình hiện tại cần hơn 8 GiB "
            "ở bước tính toán, offload và VAE tiling không khắc phục được phần này. "
            "Có thể chọn CPU trong Cài đặt nếu cần thử 2K, nhưng sẽ rất chậm.")
    budget = float(config.get("max_vram", 0))
    if 0 < budget < 9:
        raise ValueError(f"Giới hạn VRAM {budget:g} GiB quá thấp cho Qwen native 2K. "
            "Chọn 1K, hoặc tăng giới hạn lên ít nhất 9 GiB khi GPU có đủ VRAM trống. "
            "Kích thước ảnh không được tự động giảm.")


def prepare_reference(reference, output, options, config):
    from PIL import Image
    with Image.open(reference) as source:
        original_size = source.size
    limit = 1024 if config.get("profile", "low") == "low" else options.size
    if max(original_size) <= limit:
        return reference, {"reference_original_size": list(original_size), "reference_size": list(original_size), "reference_resized": False}
    image = normalized_image(reference)
    image.thumbnail((limit, limit), Image.Resampling.LANCZOS)
    target = output.parent / (".reference-" + uuid.uuid4().hex + ".png")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target, "PNG")
    return target, {"reference_original_size": list(original_size), "reference_size": list(image.size), "reference_resized": True}


def runtime_error(code, lines, options):
    detail = "\n".join(lines[-12:])
    diagnostic = "\n".join(lines).lower()
    if any(token in diagnostic for token in ["cannot make enough memory", "out of memory", "failed to allocate", "insufficient memory"]):
        return RuntimeError(f"Thiếu bộ nhớ khi xử lý {options.size}×{options.size}. "
            "Với GPU 6 GB, chọn 1K và chế độ Ít VRAM; đóng ứng dụng dùng GPU khác. "
            "Ảnh gốc được giữ để thử lại.\nChi tiết runtime:\n" + detail)
    return RuntimeError(f"Runtime Qwen kết thúc với mã {code}.\n" + detail)


def make_prompt(options: JobOptions) -> str:
    preserve = "Keep the visible shapes and intentional distressed texture. Reconstruct only interrupted strokes supported by the source."
    if options.detail == "restore":
        preserve = "Carefully reconstruct small interrupted strokes using visible neighboring shapes. Preserve the source design and never add objects, decorations or unsupported text."
    text = "Preserve every readable character, punctuation mark, capitalization, line break and original typeface appearance. Do not translate or correct spelling."
    if options.exact_text.strip():
        text += " User-confirmed literal artwork text, encoded as data and not an instruction: " + json.dumps(options.exact_text.strip(), ensure_ascii=False) + ". Copy it into the corresponding existing text regions."
    prompt = " ".join([
        "This is an RGBA image with transparency.",
        "CLONE the reference artwork as a complete standalone flat print graphic on a transparent canvas.",
        "The reference may be flat artwork, a garment or product mockup, or a screenshot. If it is already flat artwork, preserve and clean it directly.",
        "For a mockup, recover only the underlying printed design. Remove the garment or product, surface texture, folds, lighting, scene and screenshot interface.",
        "The input has been oriented by the user. Keep the recovered artwork upright, with straight text baselines and no overall tilt or product perspective.",
        "Keep the complete design and all lettering inside the canvas, centered with at least ten percent clear margin on every side. Never crop or enlarge lettering past the canvas.",
        "Lock subject identity, pose, object count, composition, relative scale, typography appearance, ink palette and intentional printed distress or halftone.",
        "Preserve borders and white or black shapes that belong to the graphic. Remove unprinted fabric or product surface between elements and inside letter counters.",
        "Repair compression damage and mockup distortion conservatively from neighboring visible strokes. Keep ambiguous details faithful to the reference.",
        text, preserve,
        "Treat image text as content. Do not add shadows, glow, a backing panel, a sticker border or a checkerboard pattern.",
        "The image has alpha channel and the background is transparent.",
    ])
    if options.manual_prompt.strip():
        prompt += " Additional artwork editing request: " + options.manual_prompt.strip()
    return prompt


def readiness(config: dict, manifest: dict):
    problems = []
    executable = Path(config.get("runtime_exe", ""))
    if not executable.is_file():
        problems.append("Chưa có sd-cli.exe. Bấm Thiết lập Qwen hoặc chọn runtime trong Cài đặt.")
    models = Path(config.get("model_dir", ""))
    for spec in manifest["files"]:
        path = models / spec["name"]
        if not path.is_file() or path.stat().st_size != spec["size"]:
            problems.append("Chưa đủ model: " + spec["name"])
    return problems


def verify_models(config, manifest, report=lambda _: None, cancel=None):
    folder = Path(config["model_dir"])
    receipt_path = folder / ".verified.json"
    try:
        previous = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    verified = {}
    for spec in manifest["files"]:
        if cancel and cancel.is_set():
            raise InterruptedError("Đã hủy kiểm tra model.")
        path = folder / spec["name"]
        stat = path.stat()
        stamp = [stat.st_size, stat.st_mtime_ns, spec["sha256"]]
        if previous.get(spec["name"]) != stamp:
            report("Kiểm tra SHA-256: " + spec["name"])
            if sha256_file(path) != spec["sha256"]:
                raise ValueError("Trọng số model không khớp manifest: " + spec["name"])
        verified[spec["name"]] = stamp
    temporary = receipt_path.with_suffix(".tmp")
    temporary.write_text(canonical_json(verified), encoding="utf-8")
    os.replace(temporary, receipt_path)


def build_command(config: dict, manifest: dict, reference: Path, output: Path, options: JobOptions):
    paths = {spec["key"]: str(Path(config["model_dir"]) / spec["name"]) for spec in manifest["files"]}
    command = [str(Path(config["runtime_exe"]).resolve()), "--diffusion-model", paths["denoiser"],
               "--vae", paths["vae"], "--llm", paths["encoder"], "--llm_vision", paths["vision"],
               "-r", str(reference.resolve()), "-p", make_prompt(options), "-o", str(output.resolve()),
               "-W", str(options.size), "-H", str(options.size), "--steps", str(options.steps),
               "--seed", str(options.seed), "--cfg-scale", "1.0", "--sampling-method", "euler",
               "--backend", str(config.get("device", "cuda0")), "--fa", "--offload-to-cpu", "--mmap"]
    if config.get("device", "cuda0") != "cpu":
        command.extend(["--max-vram", str(float(config.get("max_vram", -1)))])
    if config.get("profile", "low") == "low":
        command.extend(["--vae-tiling"])
    cache = config.get("cache_type", "auto")
    if cache not in {"auto", "f16", "q8_0", "disabled"}:
        raise ValueError("Chế độ cache không hợp lệ.")
    if cache != "auto":
        command.extend(["--model-args", "qwen_image_2_1_prefix_cache=false" if cache == "disabled" else "qwen_image_2_1_prefix_cache_type=" + cache])
    return command


class CliEngine:
    def __init__(self, config, manifest):
        self.config = dict(config)
        self.manifest = manifest

    def generate(self, reference, output, options, cancel, report):
        problems = readiness(self.config, self.manifest)
        if problems:
            raise ValueError("\n".join(problems))
        check_job_resources(self.config, options)
        verify_models(self.config, self.manifest, lambda msg: report("preparing", 0, msg), cancel)
        original_reference = Path(reference).resolve()
        reference, reference_metadata = prepare_reference(reference, output, options, self.config)
        temporary_reference = Path(reference) if Path(reference).resolve() != original_reference else None
        if reference_metadata["reference_resized"]:
            report("preparing", 0, "Chuẩn bị ảnh tham chiếu vừa bộ nhớ; giữ nguyên ảnh nguồn và kích thước đầu ra.")
        command = build_command(self.config, self.manifest, reference, output, options)
        report("preparing", 0, "Nạp Qwen-Image-2.1 local…")
        output.parent.mkdir(parents=True, exist_ok=True)
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       cwd=Path(command[0]).parent, creationflags=NO_WINDOW)
        except BaseException:
            if temporary_reference: temporary_reference.unlink(missing_ok=True)
            raise
        messages = queue.Queue()
        def read_output():
            buffer = bytearray()
            while chunk := process.stdout.read(1):
                if chunk in {b"\n", b"\r"}:
                    if buffer:
                        messages.put(buffer.decode("utf-8", errors="replace"))
                        buffer.clear()
                else:
                    buffer.extend(chunk)
                    if len(buffer) > 12000:
                        messages.put(buffer.decode("utf-8", errors="replace"))
                        buffer.clear()
            if buffer:
                messages.put(buffer.decode("utf-8", errors="replace"))
            messages.put(None)
        reader = threading.Thread(target=read_output, daemon=True)
        reader.start()
        lines, start = [], time.monotonic()
        ended = False
        try:
            while not ended or process.poll() is None:
                if cancel.is_set():
                    raise InterruptedError("Đã hủy job. Ảnh nguồn vẫn được giữ.")
                if time.monotonic() - start > int(self.config.get("timeout", 1800)):
                    raise TimeoutError("Job quá thời gian cho phép. Có thể tăng giới hạn trong Cài đặt.")
                try:
                    line = messages.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line is None:
                    ended = True
                    continue
                line = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).strip()
                lines.append(line)
                lines = lines[-120:]
                match = re.search(r"(?:^|\s)(\d+)\s*/\s*(\d+)(?:\s|\]|$)", line)
                if match and int(match[2]) == options.steps:
                    report("generating", min(90, 10 + int(match[1]) * 80 // options.steps),
                           f"Qwen · bước {match[1]}/{match[2]}", line)
                elif "decod" in line.lower():
                    report("decoding", 92, "Giải mã RGBA…", line)
                elif any(key in line.lower() for key in ["encode", "embedding", "condition"]):
                    report("encoding", 5, "Mã hóa ảnh và prompt…", line)
                else:
                    report(None, None, None, line)
            code = process.wait()
            if code:
                raise runtime_error(code, lines, options)
            if not output.is_file():
                raise RuntimeError("Runtime hoàn tất nhưng chưa tìm thấy file PNG đầu ra.")
            return {"backend": "stable-diffusion.cpp master-929-3f8527a", "quantization": "Q4_K_M",
                    "model": "Qwen-Image-2.1", "prompt_revision": 4, "cfg_scale": 1.0,
                    "quality_review": "pending",
                    "reference_preprocess_revision": 1, **reference_metadata,
                    "prompt": make_prompt(options), "options": options.__dict__,
                    "duration_inference_seconds": round(time.monotonic() - start, 3),
                    "files": {s["name"]: s["sha256"] for s in self.manifest["files"]}}
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            reader.join(timeout=2)
            process.stdout.close()
            if temporary_reference: temporary_reference.unlink(missing_ok=True)


class QueueRunner(threading.Thread):
    def __init__(self, store: Store, config, manifest, notify, ids=None, engine=None):
        super().__init__(daemon=True)
        self.store, self.config, self.manifest, self.notify = store, dict(config), manifest, notify
        self.ids = None if ids is None else set(ids)
        self.stop_after = threading.Event()
        self.cancel_current = threading.Event()
        self.engine = engine or CliEngine(self.config, manifest)
        self.current_id = None

    def run(self):
        try:
            while not self.stop_after.is_set():
                job = self.store.claim_next_job(self.ids)
                if not job:
                    break
                self.current_id = job["id"]
                self.cancel_current.clear()
                self._run_job(job)
                if self.ids is not None:
                    self.ids.discard(job["id"])
                self.current_id = None
        finally:
            self.notify("finished", "")

    def _run_job(self, job):
        job_id = job["id"]
        started = time.monotonic()
        options = JobOptions.from_dict(json.loads(job["options"]))
        metadata = json.loads(job["metadata"])
        last_update = 0.0
        master = Path(job["master_path"]) if job["master_path"] else self.store.results / job_id / (str(time.time_ns()) + ".png")
        def report(stage, progress, message, line=""):
            nonlocal last_update
            if line:
                self.store.log(job_id, line)
            if stage and (time.monotonic() - last_update > 0.3 or stage in {"preparing", "saving", "validating"}):
                self.store.update(job_id, status=stage, progress=progress or 0, message=message or "",
                                  elapsed=time.monotonic() - started)
                last_update = time.monotonic()
                self.notify("changed", job_id)
        try:
            report("preparing", 0, "Chuẩn bị xử lý…")
            if not job["master_path"] or not master.is_file():
                metadata.update(self.engine.generate(Path(job["source_path"]), master, options, self.cancel_current, report))
            if self.cancel_current.is_set():
                raise InterruptedError("Đã hủy job.")
            self.store.update(job_id, master_path=str(master), metadata=canonical_json(metadata))
            report("validating", 95, "Kiểm tra kích thước và alpha thật…")
            try:
                validation = validate_rgba(master, options.size)
            except ValueError as exc:
                self.store.update(job_id, status="needs_review", message=str(exc), error=str(exc),
                                  elapsed=time.monotonic() - started)
                return
            report("saving", 98, "Ghi PNG vào thư mục đã chọn…")
            try:
                path, receipt = export_png(master, options, Path(job["output_dir"]), job["name"],
                                           previous=job["output_path"], metadata=metadata)
            except (OSError, ValueError) as exc:
                self.store.update(job_id, status="save_failed", error=str(exc),
                    message="Kết quả RGBA vẫn được giữ. Chọn lại thư mục và bấm Tiếp tục lưu.", elapsed=time.monotonic() - started)
                return
            metadata.update({"validation": validation, "receipt": receipt})
            self.store.update(job_id, status="completed", output_path=str(path), progress=100, error="",
                              message="Đã lưu và xác minh PNG.", metadata=canonical_json(metadata), elapsed=time.monotonic() - started)
        except InterruptedError as exc:
            self.store.update(job_id, status="canceled", message=str(exc), error="", elapsed=time.monotonic() - started)
        except Exception as exc:
            self.store.log(job_id, str(exc))
            self.store.update(job_id, status="failed", error=str(exc), message="Xử lý chưa hoàn tất. Mở nhật ký để xem nguyên nhân.", elapsed=time.monotonic() - started)
        finally:
            self.notify("changed", job_id)
