#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import random
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
FATAL_CODES = {"insufficient_user_quota", "model_not_found", "invalid_api_key", "unauthorized"}

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
    if status in RETRYABLE_STATUS and code not in FATAL_CODES:
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

def png_info(data: bytes) -> tuple[int, int]:
    if len(data) < 24 or not data.startswith(PNG_SIGNATURE) or data[12:16] != b"IHDR":
        raise InvalidImageError("response is not a valid PNG")
    width, height = struct.unpack(">II", data[16:24])
    if width < 1 or height < 1 or b"IEND" not in data[-32:]:
        raise InvalidImageError("PNG is incomplete")
    return width, height

def _extract_image(payload: dict) -> bytes:
    data = payload.get("data") or []
    if not data or not data[0].get("b64_json"):
        raise InvalidImageError("response does not contain data[0].b64_json")
    try:
        return base64.b64decode(data[0]["b64_json"], validate=True)
    except Exception as exc:
        raise InvalidImageError("invalid base64 image") from exc

def _atomic_save(data: bytes, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_name(out.name + ".part")
    temp.write_bytes(data)
    temp.replace(out)

def verified_image(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        width, height = png_info(path.read_bytes())
        return {"width": width, "height": height, "bytes": path.stat().st_size}
    except InvalidImageError:
        return None

def generate_one(cfg: dict, prompt: str, out: Path, *, max_attempts: int = 10, timeout: int = 300, size: str = "1024x1024", quality: str = "standard", style: str = "vivid", transport=http_transport, sleeper=time.sleep) -> dict:
    request = {
        "url": f"{cfg['base_url'].rstrip('/')}/images/generations",
        "api_key": cfg["api_key"],
        "timeout": timeout,
        "payload": {"model": cfg["model"], "prompt": prompt, "size": size, "quality": quality, "style": style, "n": 1, "response_format": "b64_json"},
    }
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            image = _extract_image(transport(request))
            width, height = png_info(image)
            _atomic_save(image, out)
            return {"status": "succeeded", "attempts": attempt, "out": str(out), "width": width, "height": height, "bytes": len(image)}
        except FatalApiError:
            raise
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

def run_batch(cfg: dict, manifest: Path, output_dir: Path, *, max_attempts: int = 10, resume: bool = True, timeout: int = 300, transport=http_transport, sleeper=time.sleep) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger = output_dir / "image-generation-ledger.jsonl"
    summary = {"total": 0, "succeeded": 0, "failed": 0, "skipped": 0, "items": []}
    for task in _read_manifest(manifest):
        summary["total"] += 1
        out = output_dir / task["out"]
        existing = verified_image(out) if resume else None
        if existing:
            item = {"id": task["id"], "status": "skipped", "out": str(out), **existing}
            summary["skipped"] += 1
        else:
            try:
                item = {"id": task["id"], **generate_one(cfg, task["prompt"], out, max_attempts=max_attempts, timeout=timeout, size=task.get("size", "1024x1024"), quality=task.get("quality", "standard"), style=task.get("style", "vivid"), transport=transport, sleeper=sleeper)}
                summary["succeeded"] += 1
            except ApiError as exc:
                item = {"id": task["id"], "status": "failed", "out": str(out), "error": str(exc), "http_status": exc.status}
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
    parser = argparse.ArgumentParser(description="Reliable gpt-image-2 generator with retries and resume")
    parser.add_argument("--config")
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("generate")
    one.add_argument("--prompt", required=True)
    one.add_argument("--out", required=True)
    one.add_argument("--size", default="1024x1024")
    one.add_argument("--quality", default="standard")
    one.add_argument("--style", default="vivid")
    one.add_argument("--max-attempts", type=int, default=10)
    one.add_argument("--timeout", type=int, default=300)
    batch = sub.add_parser("batch")
    batch.add_argument("--manifest", required=True)
    batch.add_argument("--output-dir", required=True)
    batch.add_argument("--max-attempts", type=int, default=10)
    batch.add_argument("--timeout", type=int, default=300)
    batch.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.command == "generate":
            result = generate_one(cfg, args.prompt, Path(args.out), max_attempts=args.max_attempts, timeout=args.timeout, size=args.size, quality=args.quality, style=args.style)
        else:
            result = run_batch(cfg, Path(args.manifest), Path(args.output_dir), max_attempts=args.max_attempts, timeout=args.timeout, resume=not args.no_resume)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("failed", 0) == 0 else 2
    except (ApiError, InvalidImageError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[reliable-image] failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
