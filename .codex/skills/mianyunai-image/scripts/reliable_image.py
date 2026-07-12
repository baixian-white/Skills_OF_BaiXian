#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import random
import struct
import sys
import time
import urllib.error
import urllib.request
import uuid
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    Image = None
    UnidentifiedImageError = OSError

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
FATAL_CODES = {"insufficient_user_quota", "model_not_found", "invalid_api_key", "unauthorized"}
FATAL_MESSAGE_FRAGMENTS = {
    "not supported model",
    "only imagen models are supported",
    "fixed 4k sku",
}
OUTPUT_FORMATS = {"png", "jpeg", "webp"}
MODERATION_LEVELS = {"auto", "low"}

class ApiError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status

class RetryableApiError(ApiError):
    pass

class FatalApiError(ApiError):
    pass

class InvalidImageError(RuntimeError):
    pass

class FormatMismatchError(InvalidImageError):
    pass

def load_config(path: str | None) -> dict:
    config_path = Path(path) if path else None
    if config_path is None and os.environ.get("RELIABLE_IMAGE_CONFIG"):
        config_path = Path(os.environ["RELIABLE_IMAGE_CONFIG"])
    cfg = json.loads(config_path.read_text(encoding="utf-8")) if config_path else {}
    cfg.setdefault("api_key", os.environ.get("IMAGE_API_KEY", ""))
    cfg.setdefault("base_url", os.environ.get("IMAGE_API_BASE_URL", "https://mianyunai.com/v1"))
    cfg.setdefault("model", os.environ.get("IMAGE_API_MODEL", "gpt-image-2"))
    if not cfg["api_key"]:
        raise FatalApiError(0, "missing api_key")
    return cfg

def _error_from_http(status: int, body: str) -> ApiError:
    message = body[:1000]
    code = ""
    try:
        payload = json.loads(body)
        error = payload.get("error") or {}
        message = str(error.get("message") or message)
        code = str(error.get("code") or "")
    except json.JSONDecodeError:
        pass
    deterministic = any(fragment in message.lower() for fragment in FATAL_MESSAGE_FRAGMENTS)
    if status in RETRYABLE_STATUS and code not in FATAL_CODES and not deterministic:
        return RetryableApiError(status, message)
    return FatalApiError(status, message)

def http_transport(request: dict) -> dict:
    body = json.dumps(request["payload"], ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        request["url"], data=body, method="POST",
        headers={"Authorization": f"Bearer {request['api_key']}", "Content-Type": "application/json", "User-Agent": "reliable-image/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=request["timeout"]) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise _error_from_http(exc.code, exc.read().decode("utf-8", "replace")) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RetryableApiError(0, f"network timeout: {exc}") from exc

def http_download(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "reliable-image/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise _error_from_http(exc.code, exc.read().decode("utf-8", "replace")) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RetryableApiError(0, f"image download timeout: {exc}") from exc

def _multipart_value(value: object) -> str:
    return str(value).replace("\r", "").replace("\n", "")

def _multipart_token(value: object) -> str:
    return _multipart_value(value).replace("\\", "\\\\").replace('"', '\\"')

def _encode_multipart(fields: dict, files: list[dict], *, boundary: str | None = None) -> tuple[bytes, str]:
    boundary = boundary or f"reliable-image-{uuid.uuid4().hex}"
    body = bytearray()
    for name, value in fields.items():
        if value is None:
            continue
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(f'Content-Disposition: form-data; name="{_multipart_token(name)}"\r\n\r\n'.encode("utf-8"))
        body.extend(_multipart_value(value).encode("utf-8"))
        body.extend(b"\r\n")
    for item in files:
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{_multipart_token(item["field"])}"; '
                f'filename="{_multipart_token(item["filename"])}"\r\n'
            ).encode("utf-8")
        )
        body.extend(f'Content-Type: {item["content_type"]}\r\n\r\n'.encode("ascii"))
        body.extend(item["data"])
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("ascii"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"

def http_edit_transport(request: dict) -> dict:
    body, content_type = _encode_multipart(request["fields"], request["files"])
    req = urllib.request.Request(
        request["url"], data=body, method="POST",
        headers={"Authorization": f"Bearer {request['api_key']}", "Content-Type": content_type, "User-Agent": "reliable-image/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=request["timeout"]) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise _error_from_http(exc.code, exc.read().decode("utf-8", "replace")) from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RetryableApiError(0, f"network timeout: {exc}") from exc

def png_info(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise InvalidImageError("response is not a valid PNG")
    width, height = struct.unpack(">II", data[16:24])
    if width < 1 or height < 1 or b"IEND" not in data[-32:]:
        raise InvalidImageError("PNG is incomplete")
    return width, height

def image_info(data: bytes, expected_format: str | None = None) -> dict:
    expected = expected_format.lower() if expected_format else None
    if expected == "jpg":
        expected = "jpeg"
    if expected and expected not in OUTPUT_FORMATS:
        raise ValueError(f"unsupported output_format: {expected_format}")
    if Image is None:
        if expected not in (None, "png"):
            raise InvalidImageError("Pillow is required to validate JPEG and WebP images")
        width, height = png_info(data)
        return {"format": "png", "width": width, "height": height, "has_alpha": False, "transparent_pixels": 0}
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            actual = (image.format or "").lower()
            if actual == "jpg":
                actual = "jpeg"
            if actual not in OUTPUT_FORMATS:
                raise InvalidImageError(f"unsupported returned image format: {actual or 'unknown'}")
            if expected and actual != expected:
                raise FormatMismatchError(f"expected {expected}, received {actual}")
            width, height = image.size
            has_alpha = "A" in image.getbands() or "transparency" in image.info
            transparent_pixels = 0
            alpha_min = alpha_max = 255
            if has_alpha:
                alpha = image.convert("RGBA").getchannel("A")
                alpha_min, alpha_max = alpha.getextrema()
                transparent_pixels = sum(alpha.histogram()[:255])
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        if isinstance(exc, InvalidImageError):
            raise
        raise InvalidImageError(f"response is not a valid {expected or 'supported'} image: {exc}") from exc
    if width < 1 or height < 1:
        raise InvalidImageError("image dimensions are invalid")
    return {
        "format": actual,
        "width": width,
        "height": height,
        "has_alpha": has_alpha,
        "alpha_min": alpha_min,
        "alpha_max": alpha_max,
        "transparent_pixels": transparent_pixels,
    }

def _extract_image(payload: dict, *, timeout: int = 300, downloader=http_download) -> bytes:
    data = payload.get("data") or []
    if not data:
        raise InvalidImageError("response does not contain image data")
    if data[0].get("b64_json"):
        try:
            return base64.b64decode(data[0]["b64_json"], validate=True)
        except Exception as exc:
            raise InvalidImageError("invalid base64 image") from exc
    if data[0].get("url"):
        return downloader(str(data[0]["url"]), timeout)
    raise InvalidImageError("response does not contain data[0].b64_json or data[0].url")

def _atomic_save(data: bytes, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_name(out.name + ".part")
    temp.write_bytes(data)
    temp.replace(out)

def verified_image(path: Path, expected_format: str | None = None) -> dict | None:
    if not path.exists():
        return None
    try:
        info = image_info(path.read_bytes(), expected_format)
        return {**info, "bytes": path.stat().st_size}
    except (InvalidImageError, ValueError):
        return None

def generate_one(cfg: dict, prompt: str, out: Path, *, max_attempts: int = 10, timeout: int = 300, size: str = "1024x1024", quality: str = "standard", style: str = "vivid", output_format: str = "png", moderation: str = "auto", model: str | None = None, transport=http_transport, downloader=http_download, sleeper=time.sleep) -> dict:
    output_format = output_format.lower()
    if output_format == "jpg":
        output_format = "jpeg"
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"unsupported output_format: {output_format}")
    if moderation not in MODERATION_LEVELS:
        raise ValueError(f"unsupported moderation: {moderation}")
    model_name = model or cfg["model"]
    request = {
        "url": f"{cfg['base_url'].rstrip('/')}/images/generations",
        "api_key": cfg["api_key"],
        "timeout": timeout,
        "payload": {
            "model": model_name, "prompt": prompt, "size": size,
            "quality": quality, "style": style, "output_format": output_format,
            "moderation": moderation, "n": 1, "response_format": "b64_json",
        },
    }
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            image = _extract_image(transport(request), timeout=timeout, downloader=downloader)
            info = image_info(image, output_format)
            _atomic_save(image, out)
            return {
                "status": "succeeded", "attempts": attempt, "out": str(out),
                "model": model_name, "requested_size": size, **info, "bytes": len(image),
            }
        except FatalApiError:
            raise
        except FormatMismatchError as exc:
            raise FatalApiError(0, str(exc)) from exc
        except (RetryableApiError, InvalidImageError) as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            delay = min(60.0, 2 ** min(attempt - 1, 5)) + random.random()
            sleeper(delay)
    raise RetryableApiError(getattr(last_error, "status", 0), f"failed after {max_attempts} attempts: {last_error}")

def _upload_file(path: Path, field: str) -> tuple[dict, dict]:
    if not path.is_file():
        raise ValueError(f"input image does not exist: {path}")
    data = path.read_bytes()
    info = image_info(data)
    content_type = {
        "png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp",
    }.get(info["format"], mimetypes.guess_type(path.name)[0] or "application/octet-stream")
    return {
        "field": field,
        "path": str(path),
        "filename": path.name,
        "content_type": content_type,
        "data": data,
    }, info

def edit_one(cfg: dict, prompt: str, images: list[Path], out: Path, *, mask: Path | None = None, max_attempts: int = 10, timeout: int = 300, size: str = "1024x1024", quality: str = "standard", style: str = "vivid", output_format: str = "png", moderation: str = "auto", model: str | None = None, transport=http_edit_transport, downloader=http_download, sleeper=time.sleep) -> dict:
    if not images:
        raise ValueError("at least one input image is required")
    output_format = output_format.lower()
    if output_format == "jpg":
        output_format = "jpeg"
    if output_format not in OUTPUT_FORMATS:
        raise ValueError(f"unsupported output_format: {output_format}")
    if moderation not in MODERATION_LEVELS:
        raise ValueError(f"unsupported moderation: {moderation}")

    upload_files = []
    input_info = []
    for image_path in images:
        upload, info = _upload_file(Path(image_path), "image[]")
        upload_files.append(upload)
        input_info.append(info)
    if mask is not None:
        mask_upload, mask_info = _upload_file(Path(mask), "mask")
        first_size = (input_info[0]["width"], input_info[0]["height"])
        mask_size = (mask_info["width"], mask_info["height"])
        if mask_size != first_size:
            raise ValueError(f"mask dimensions {mask_size[0]}x{mask_size[1]} do not match first image {first_size[0]}x{first_size[1]}")
        upload_files.append(mask_upload)

    model_name = model or cfg["model"]
    request = {
        "url": f"{cfg['base_url'].rstrip('/')}/images/edits",
        "api_key": cfg["api_key"],
        "timeout": timeout,
        "fields": {
            "model": model_name, "prompt": prompt, "size": size,
            "quality": quality, "style": style, "output_format": output_format,
            "moderation": moderation, "n": 1, "response_format": "b64_json",
        },
        "files": upload_files,
    }
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            image = _extract_image(transport(request), timeout=timeout, downloader=downloader)
            info = image_info(image, output_format)
            _atomic_save(image, out)
            return {
                "status": "succeeded", "attempts": attempt, "out": str(out),
                "model": model_name, "requested_size": size,
                "input_image_count": len(images), "mask": str(mask) if mask else None,
                **info, "bytes": len(image),
            }
        except FatalApiError:
            raise
        except FormatMismatchError as exc:
            raise FatalApiError(0, str(exc)) from exc
        except (RetryableApiError, InvalidImageError) as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            delay = min(60.0, 2 ** min(attempt - 1, 5)) + random.random()
            sleeper(delay)
    raise RetryableApiError(getattr(last_error, "status", 0), f"failed after {max_attempts} attempts: {last_error}")

def _read_manifest(path: Path) -> list[dict]:
    tasks = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        task = json.loads(line)
        if not task.get("prompt") or not task.get("out"):
            raise ValueError(f"manifest line {line_number} requires prompt and out")
        task.setdefault("id", str(line_number))
        tasks.append(task)
    return tasks

def _append_jsonl(path: Path, record: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")

def _manifest_input_path(manifest: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else manifest.parent / path

def _task_images(task: dict, manifest: Path) -> list[Path]:
    values = task.get("images")
    if values is None and task.get("image") is not None:
        values = [task["image"]]
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    if not isinstance(values, list) or not values:
        raise ValueError("manifest images must be a non-empty string or list")
    return [_manifest_input_path(manifest, str(value)) for value in values]

def run_batch(cfg: dict, manifest: Path, output_dir: Path, *, max_attempts: int = 10, resume: bool = True, timeout: int = 300, model: str | None = None, transport=http_transport, edit_transport=http_edit_transport, downloader=http_download, sleeper=time.sleep) -> dict:
    manifest = Path(manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = output_dir / "image-generation-ledger.jsonl"
    summary = {"total": 0, "succeeded": 0, "failed": 0, "skipped": 0, "items": []}
    for task in _read_manifest(manifest):
        summary["total"] += 1
        out = output_dir / task["out"]
        output_format = task.get("output_format", "png")
        existing = verified_image(out, output_format) if resume else None
        if existing:
            item = {"id": task["id"], "status": "skipped", "out": str(out), **existing}
            summary["skipped"] += 1
        else:
            try:
                images = _task_images(task, manifest)
                common = {
                    "max_attempts": max_attempts,
                    "timeout": timeout,
                    "size": task.get("size", "1024x1024"),
                    "quality": task.get("quality", "standard"),
                    "style": task.get("style", "vivid"),
                    "output_format": output_format,
                    "moderation": task.get("moderation", "auto"),
                    "model": task.get("model", model),
                    "downloader": downloader,
                    "sleeper": sleeper,
                }
                if images:
                    mask = task.get("mask")
                    mask_path = _manifest_input_path(manifest, str(mask)) if mask else None
                    result = edit_one(
                        cfg, task["prompt"], images, out,
                        mask=mask_path, transport=edit_transport, **common,
                    )
                else:
                    result = generate_one(
                        cfg, task["prompt"], out,
                        transport=transport, **common,
                    )
                item = {"id": task["id"], **result}
                summary["succeeded"] += 1
            except (ApiError, InvalidImageError, ValueError, OSError) as exc:
                item = {
                    "id": task["id"], "status": "failed", "out": str(out),
                    "error": str(exc), "http_status": getattr(exc, "status", 0),
                }
                summary["failed"] += 1
                _append_jsonl(ledger, item)
                summary["items"].append(item)
                if isinstance(exc, FatalApiError):
                    break
                continue
        _append_jsonl(ledger, item)
        summary["items"].append(item)
    (output_dir / "image-generation-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reliable image generator and editor with retries and resume")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("generate")
    one.add_argument("--prompt", required=True)
    one.add_argument("--out", required=True)
    one.add_argument("--model")
    one.add_argument("--size", default="1024x1024")
    one.add_argument("--quality", default="standard")
    one.add_argument("--style", default="vivid")
    one.add_argument("--output-format", choices=sorted(OUTPUT_FORMATS), default="png")
    one.add_argument("--moderation", choices=sorted(MODERATION_LEVELS), default="auto")
    one.add_argument("--max-attempts", type=int, default=10)
    one.add_argument("--timeout", type=int, default=300)
    edit = sub.add_parser("edit")
    edit.add_argument("--prompt", required=True)
    edit.add_argument("--image", action="append", required=True)
    edit.add_argument("--mask")
    edit.add_argument("--out", required=True)
    edit.add_argument("--model")
    edit.add_argument("--size", default="1024x1024")
    edit.add_argument("--quality", default="standard")
    edit.add_argument("--style", default="vivid")
    edit.add_argument("--output-format", choices=sorted(OUTPUT_FORMATS), default="png")
    edit.add_argument("--moderation", choices=sorted(MODERATION_LEVELS), default="auto")
    edit.add_argument("--max-attempts", type=int, default=10)
    edit.add_argument("--timeout", type=int, default=300)
    batch = sub.add_parser("batch")
    batch.add_argument("--manifest", required=True)
    batch.add_argument("--output-dir", required=True)
    batch.add_argument("--model")
    batch.add_argument("--max-attempts", type=int, default=10)
    batch.add_argument("--timeout", type=int, default=300)
    batch.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.command == "generate":
            result = generate_one(
                cfg, args.prompt, Path(args.out),
                max_attempts=args.max_attempts, timeout=args.timeout,
                size=args.size, quality=args.quality, style=args.style,
                output_format=args.output_format, moderation=args.moderation,
                model=args.model,
            )
        elif args.command == "edit":
            result = edit_one(
                cfg, args.prompt, [Path(path) for path in args.image], Path(args.out),
                mask=Path(args.mask) if args.mask else None,
                max_attempts=args.max_attempts, timeout=args.timeout,
                size=args.size, quality=args.quality, style=args.style,
                output_format=args.output_format, moderation=args.moderation,
                model=args.model,
            )
        else:
            result = run_batch(
                cfg, Path(args.manifest), Path(args.output_dir),
                max_attempts=args.max_attempts, timeout=args.timeout,
                resume=not args.no_resume, model=args.model,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("failed", 0) == 0 else 2
    except (ApiError, InvalidImageError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[reliable-image] failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
