import base64
import importlib.util
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image


MODULE_PATH = Path(__file__).parents[1] / "scripts" / "native_gemini_probe.py"


def load_module():
    spec = importlib.util.spec_from_file_location("native_gemini_probe", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def png_bytes(width=5, height=4):
    image = Image.new("RGB", (width, height), (200, 20, 30))
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class NativeGeminiProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = load_module()

    def test_extracts_and_validates_inline_image(self):
        raw = png_bytes()
        payload = {
            "candidates": [{
                "content": {
                    "parts": [{
                        "inlineData": {
                            "mimeType": "image/png",
                            "data": base64.b64encode(raw).decode("ascii"),
                        },
                    }],
                },
            }],
        }
        image_data, mime_type = self.mod.extract_image(payload)
        self.assertEqual(image_data, raw)
        self.assertEqual(mime_type, "image/png")
        self.assertEqual(
            self.mod.validate_image(image_data),
            {"format": "png", "width": 5, "height": 4},
        )

    def test_rejects_response_without_inline_image(self):
        payload = {
            "candidates": [{"content": {"parts": [{"text": "no image"}]}}],
        }
        with self.assertRaisesRegex(RuntimeError, "no inline image"):
            self.mod.extract_image(payload)


if __name__ == "__main__":
    unittest.main()
