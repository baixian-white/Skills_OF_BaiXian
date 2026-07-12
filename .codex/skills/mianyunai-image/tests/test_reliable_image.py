import base64
import importlib.util
import json
import struct
import tempfile
import unittest
import zlib
from io import BytesIO
from pathlib import Path
from unittest import mock

from PIL import Image

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "reliable_image.py"

def load_module():
    spec = importlib.util.spec_from_file_location("reliable_image", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def png_bytes(width=2, height=3):
    signature = b"\x89PNG\r\n\x1a\n"
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + (b"\x00\x00\x00" * width) for _ in range(height))
    return signature + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")

def encoded_image(format_name, width=4, height=3):
    image = Image.new("RGB", (width, height), (200, 20, 30))
    output = BytesIO()
    image.save(output, format=format_name)
    return output.getvalue()

def encoded_mask(width=4, height=3):
    image = Image.new("L", (width, height), 255)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()

class SequenceTransport:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
    def __call__(self, request):
        outcome = self.outcomes[self.calls]
        self.calls += 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

class ReliableImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()
    def config(self):
        return {"api_key": "sk-secret-value", "base_url": "https://example.invalid/v1", "model": "gpt-image-2"}
    def test_retries_four_524_errors_then_saves_valid_png(self):
        retry = self.mod.RetryableApiError
        payload = {"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
        transport = SequenceTransport([retry(524, "timeout")] * 4 + [payload])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "image.png"
            result = self.mod.generate_one(self.config(), "prompt", out, max_attempts=5, transport=transport, sleeper=lambda _: None)
            self.assertEqual(transport.calls, 5)
            self.assertTrue(out.exists())
            self.assertEqual(result["width"], 2)
            self.assertEqual(result["height"], 3)
    def test_invalid_png_is_retried(self):
        bad = {"data": [{"b64_json": base64.b64encode(b"not png").decode()}]}
        good = {"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
        transport = SequenceTransport([bad, good])
        with tempfile.TemporaryDirectory() as tmp:
            self.mod.generate_one(self.config(), "prompt", Path(tmp) / "image.png", max_attempts=2, transport=transport, sleeper=lambda _: None)
            self.assertEqual(transport.calls, 2)
    def test_sends_configurable_format_quality_and_moderation(self):
        payload = {"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
        requests = []
        def transport(request):
            requests.append(request)
            return payload
        with tempfile.TemporaryDirectory() as tmp:
            result = self.mod.generate_one(
                self.config(), "prompt", Path(tmp) / "image.png",
                output_format="png", quality="high", moderation="low",
                transport=transport, sleeper=lambda _: None,
            )
        sent = requests[0]["payload"]
        self.assertEqual(sent["output_format"], "png")
        self.assertEqual(sent["quality"], "high")
        self.assertEqual(sent["moderation"], "low")
        self.assertEqual(sent["response_format"], "b64_json")
        self.assertEqual(result["format"], "png")
    def test_validates_and_saves_jpeg_and_webp(self):
        for output_format, pillow_format, suffix in (("jpeg", "JPEG", ".jpg"), ("webp", "WEBP", ".webp")):
            with self.subTest(output_format=output_format), tempfile.TemporaryDirectory() as tmp:
                raw = encoded_image(pillow_format)
                payload = {"data": [{"b64_json": base64.b64encode(raw).decode()}]}
                result = self.mod.generate_one(
                    self.config(), "prompt", Path(tmp) / f"image{suffix}",
                    output_format=output_format,
                    transport=SequenceTransport([payload]), sleeper=lambda _: None,
                )
                self.assertEqual(result["format"], output_format)
                self.assertEqual((result["width"], result["height"]), (4, 3))
    def test_multipart_encoder_preserves_fields_and_file_bytes(self):
        file_bytes = b"\x00binary\r\ncontent\xff"
        body, content_type = self.mod._encode_multipart(
            {"prompt": "turn it blue", "n": 1},
            [{
                "field": "image[]", "filename": "input.png",
                "content_type": "image/png", "data": file_bytes,
            }],
            boundary="test-boundary",
        )
        self.assertEqual(content_type, "multipart/form-data; boundary=test-boundary")
        self.assertIn(b'name="prompt"', body)
        self.assertIn(b"turn it blue", body)
        self.assertIn(b'name="image[]"; filename="input.png"', body)
        self.assertIn(file_bytes, body)
        self.assertTrue(body.endswith(b"--test-boundary--\r\n"))
    def test_edit_sends_multiple_images_and_optional_mask(self):
        payload = {"data": [{"b64_json": base64.b64encode(png_bytes(6, 4)).decode()}]}
        requests = []
        def transport(request):
            requests.append(request)
            return payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.png"
            second = root / "second.jpg"
            mask = root / "mask.png"
            out = root / "edited.png"
            first.write_bytes(encoded_image("PNG", 6, 4))
            second.write_bytes(encoded_image("JPEG", 6, 4))
            mask.write_bytes(encoded_mask(6, 4))
            result = self.mod.edit_one(
                self.config(), "turn the cube blue", [first, second], out,
                mask=mask, model="gpt-image-2-4k", size="1024x1024",
                quality="low", style="vivid", output_format="png",
                moderation="auto", transport=transport,
                sleeper=lambda _: None,
            )
            self.assertTrue(out.exists())
        request = requests[0]
        self.assertTrue(request["url"].endswith("/images/edits"))
        self.assertEqual(request["fields"]["model"], "gpt-image-2-4k")
        self.assertEqual(request["fields"]["prompt"], "turn the cube blue")
        self.assertEqual(request["fields"]["response_format"], "b64_json")
        self.assertEqual([item["field"] for item in request["files"]], ["image[]", "image[]", "mask"])
        self.assertEqual(result["input_image_count"], 2)
        self.assertEqual((result["width"], result["height"]), (6, 4))
    def test_edit_downloads_url_response(self):
        requests = []
        downloads = []
        def transport(request):
            requests.append(request)
            return {"data": [{"url": "https://example.invalid/result.png"}]}
        def downloader(url, timeout):
            downloads.append((url, timeout))
            return png_bytes(5, 4)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            source.write_bytes(encoded_image("PNG", 4, 3))
            result = self.mod.edit_one(
                self.config(), "edit", [source], root / "result.png",
                timeout=123, transport=transport, downloader=downloader,
                sleeper=lambda _: None,
            )
        self.assertEqual(downloads, [("https://example.invalid/result.png", 123)])
        self.assertEqual((result["width"], result["height"]), (5, 4))
    def test_edit_rejects_mask_dimension_mismatch_before_request(self):
        def transport(_request):
            raise AssertionError("transport must not be called")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            mask = root / "mask.png"
            source.write_bytes(encoded_image("PNG", 4, 3))
            mask.write_bytes(encoded_mask(5, 3))
            with self.assertRaisesRegex(ValueError, "mask dimensions"):
                self.mod.edit_one(
                    self.config(), "edit", [source], root / "result.png",
                    mask=mask, transport=transport, sleeper=lambda _: None,
                )
    def test_format_mismatch_stops_without_retry(self):
        raw = encoded_image("PNG")
        payload = {"data": [{"b64_json": base64.b64encode(raw).decode()}]}
        transport = SequenceTransport([payload, payload])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(self.mod.FatalApiError):
                self.mod.generate_one(
                    self.config(), "prompt", Path(tmp) / "image.webp",
                    output_format="webp", max_attempts=2,
                    transport=transport, sleeper=lambda _: None,
                )
        self.assertEqual(transport.calls, 1)
    def test_batch_forwards_format_quality_and_moderation(self):
        raw = encoded_image("JPEG")
        payload = {"data": [{"b64_json": base64.b64encode(raw).decode()}]}
        requests = []
        def transport(request):
            requests.append(request)
            return payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "tasks.jsonl"
            manifest.write_text(json.dumps({
                "id": "one", "prompt": "test", "out": "one.jpg",
                "output_format": "jpeg", "quality": "medium", "moderation": "low",
            }), encoding="utf-8")
            summary = self.mod.run_batch(self.config(), manifest, root, transport=transport, sleeper=lambda _: None)
        self.assertEqual(summary["succeeded"], 1)
        self.assertEqual(requests[0]["payload"]["output_format"], "jpeg")
        self.assertEqual(requests[0]["payload"]["quality"], "medium")
        self.assertEqual(requests[0]["payload"]["moderation"], "low")
    def test_batch_runs_edit_task_with_manifest_relative_paths(self):
        payload = {"data": [{"b64_json": base64.b64encode(png_bytes(4, 3)).decode()}]}
        requests = []
        def edit_transport(request):
            requests.append(request)
            return payload
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "input.png").write_bytes(encoded_image("PNG", 4, 3))
            (root / "mask.png").write_bytes(encoded_mask(4, 3))
            manifest = root / "tasks.jsonl"
            manifest.write_text(json.dumps({
                "id": "edit-one", "prompt": "make it blue",
                "images": ["input.png"], "mask": "mask.png", "out": "edited.png",
                "model": "gpt-image-2-4k", "quality": "low",
                "output_format": "png", "moderation": "auto",
            }), encoding="utf-8")
            summary = self.mod.run_batch(
                self.config(), manifest, root / "results",
                edit_transport=edit_transport, sleeper=lambda _: None,
            )
        self.assertEqual(summary["succeeded"], 1)
        self.assertEqual(requests[0]["fields"]["model"], "gpt-image-2-4k")
        self.assertEqual(Path(requests[0]["files"][0]["path"]), root / "input.png")
        self.assertEqual(Path(requests[0]["files"][1]["path"]), root / "mask.png")

    def test_edit_cli_forwards_repeated_images_mask_and_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            config.write_text(json.dumps(self.config()), encoding="utf-8")
            first = root / "first.png"
            second = root / "second.png"
            mask = root / "mask.png"
            out = root / "edited.png"
            for path in (first, second, mask):
                path.write_bytes(encoded_image("PNG", 4, 3))
            result = {
                "status": "succeeded", "out": str(out), "width": 4,
                "height": 3, "format": "png", "attempts": 1,
            }
            with mock.patch.object(self.mod, "edit_one", return_value=result) as edit:
                exit_code = self.mod.main([
                    "--config", str(config), "edit",
                    "--prompt", "make it blue",
                    "--image", str(first), "--image", str(second),
                    "--mask", str(mask), "--out", str(out),
                    "--model", "gpt-image-2-4k", "--size", "1024x1024",
                    "--quality", "low", "--style", "vivid",
                    "--output-format", "png", "--moderation", "auto",
                    "--max-attempts", "3", "--timeout", "120",
                ])
        self.assertEqual(exit_code, 0)
        edit.assert_called_once_with(
            self.config(), "make it blue", [first, second], out,
            mask=mask, model="gpt-image-2-4k", size="1024x1024",
            quality="low", style="vivid", output_format="png",
            moderation="auto", max_attempts=3, timeout=120,
        )
    def test_quota_error_stops_without_retry(self):
        fatal = self.mod.FatalApiError(403, "insufficient_user_quota")
        transport = SequenceTransport([fatal])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(self.mod.FatalApiError):
                self.mod.generate_one(self.config(), "prompt", Path(tmp) / "image.png", max_attempts=10, transport=transport, sleeper=lambda _: None)
        self.assertEqual(transport.calls, 1)

    def test_deterministic_model_error_is_fatal_even_with_5xx_status(self):
        body = json.dumps({
            "error": {
                "message": "not supported model for image generation, only imagen models are supported",
            },
        })
        error = self.mod._error_from_http(500, body)
        self.assertIsInstance(error, self.mod.FatalApiError)
    def test_batch_resume_skips_verified_existing_image(self):
        payload = {"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
        transport = SequenceTransport([payload])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "done.png").write_bytes(png_bytes())
            manifest = root / "tasks.jsonl"
            manifest.write_text("\n".join([json.dumps({"id": "done", "prompt": "one", "out": "done.png"}), json.dumps({"id": "new", "prompt": "two", "out": "new.png"})]), encoding="utf-8")
            summary = self.mod.run_batch(self.config(), manifest, root, max_attempts=2, resume=True, transport=transport, sleeper=lambda _: None)
            self.assertEqual(summary["skipped"], 1)
            self.assertEqual(summary["succeeded"], 1)
            self.assertEqual(transport.calls, 1)
    def test_logs_and_summary_do_not_contain_api_key(self):
        payload = {"data": [{"b64_json": base64.b64encode(png_bytes()).decode()}]}
        transport = SequenceTransport([payload])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "tasks.jsonl"
            manifest.write_text(json.dumps({"id": "one", "prompt": "test", "out": "one.png"}), encoding="utf-8")
            self.mod.run_batch(self.config(), manifest, root, max_attempts=1, resume=True, transport=transport, sleeper=lambda _: None)
            all_text = "\n".join(p.read_text(encoding="utf-8") for p in root.glob("*.json*"))
            self.assertNotIn("sk-secret-value", all_text)

if __name__ == "__main__":
    unittest.main()
