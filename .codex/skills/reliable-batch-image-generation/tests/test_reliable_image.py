import base64
import importlib.util
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

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
    def test_quota_error_stops_without_retry(self):
        fatal = self.mod.FatalApiError(403, "insufficient_user_quota")
        transport = SequenceTransport([fatal])
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(self.mod.FatalApiError):
                self.mod.generate_one(self.config(), "prompt", Path(tmp) / "image.png", max_attempts=10, transport=transport, sleeper=lambda _: None)
        self.assertEqual(transport.calls, 1)
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
