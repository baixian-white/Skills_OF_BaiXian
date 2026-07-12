#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError


FORMAT_SUFFIXES = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}


def extract_error(body: str) -> str:
    try:
        payload = json.loads(body)
        error = payload.get("error") or {}
        return str(error.get("message") or body[:1000])
    except json.JSONDecodeError:
        return body[:1000]


def extract_image(payload: dict) -> tuple[bytes, str | None]:
    for candidate in payload.get("candidates") or []:
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            inline = part.get("inlineData") or part.get("inline_data") or {}
            encoded = inline.get("data")
            if encoded:
                return base64.b64decode(encoded, validate=True), inline.get("mimeType") or inline.get("mime_type")
    raise RuntimeError("response contains no inline image")


def validate_image(data: bytes) -> dict:
    try:
        with Image.open(BytesIO(data)) as image:
            image.load()
            image_format = (image.format or "").lower()
            if image_format == "jpg":
                image_format = "jpeg"
            if image_format not in FORMAT_SUFFIXES:
                raise RuntimeError(f"unsupported returned image format: {image_format or 'unknown'}")
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise RuntimeError(f"response image cannot be decoded: {exc}") from exc
    return {"format": image_format, "width": width, "height": height}


def atomic_save(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(data)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe a Gemini native image model without logging the API key")
    parser.add_argument("--config", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--aspect-ratio", default="1:1")
    parser.add_argument("--image-size", default="1K")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    api_key = str(config.get("api_key") or "")
    if not api_key:
        raise RuntimeError("missing api_key")
    parsed_base = urllib.parse.urlsplit(str(config.get("base_url") or "https://mianyunai.com/v1"))
    origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
    model_path = urllib.parse.quote(args.model, safe="")
    encoded_key = urllib.parse.quote(api_key, safe="")
    url = f"{origin}/v1beta/models/{model_path}:generateContent?key={encoded_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": args.prompt}]}],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
            "imageConfig": {
                "aspectRatio": args.aspect_ratio,
                "imageSize": args.image_size,
            },
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "reliable-image-native-probe/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        print(json.dumps({"status": "failed", "http_status": exc.code, "error": extract_error(body)}, ensure_ascii=False, indent=2))
        return 1
    except (urllib.error.URLError, TimeoutError) as exc:
        reason = exc.reason if hasattr(exc, "reason") else exc
        print(json.dumps({"status": "failed", "http_status": 0, "error": str(reason)}, ensure_ascii=False, indent=2))
        return 1

    image_data, declared_mime = extract_image(response_payload)
    info = validate_image(image_data)
    requested_out = Path(args.out)
    actual_out = requested_out.with_suffix(FORMAT_SUFFIXES[info["format"]])
    atomic_save(image_data, actual_out)
    print(json.dumps({
        "status": "succeeded",
        "model": args.model,
        "requested_aspect_ratio": args.aspect_ratio,
        "requested_image_size": args.image_size,
        "declared_mime": declared_mime,
        **info,
        "bytes": len(image_data),
        "out": str(actual_out),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
