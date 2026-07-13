import hashlib
import json
import struct
import subprocess
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path


SCRIPT = Path(__file__).with_name("build_image_deck.py")


def make_png(path: Path, color: str) -> None:
    colors = {"white": (255, 255, 255), "navy": (18, 59, 109), "teal": (25, 167, 160)}
    red, green, blue = colors[color]
    width, height = 32, 18
    raw = b"".join(b"\x00" + bytes((red, green, blue)) * width for _ in range(height))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


class BuildImageDeckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.images = self.root / "images"
        self.images.mkdir()
        make_png(self.images / "01.png", "white")
        make_png(self.images / "02.png", "navy")
        make_png(self.images / "03.png", "teal")

    def tearDown(self):
        self.temp.cleanup()

    def run_builder(self, *args, check=True):
        return subprocess.run(
            ["python", str(SCRIPT), *map(str, args)],
            text=True,
            capture_output=True,
            check=check,
        )

    def test_builds_plain_deck_and_preserves_image_bytes(self):
        output = self.root / "plain.pptx"
        report = self.root / "plain.json"
        self.run_builder("--images-dir", self.images, "--output", output, "--report", report)

        result = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(result["slides"], 3)
        self.assertEqual(result["style"], "plain")
        self.assertTrue(result["all_images_match"])
        with zipfile.ZipFile(output) as deck:
            self.assertIsNone(deck.testzip())
            for index in range(1, 4):
                source = (self.images / f"{index:02d}.png").read_bytes()
                embedded = deck.read(f"ppt/media/image{index}.png")
                self.assertEqual(hashlib.sha256(source).digest(), hashlib.sha256(embedded).digest())

    def test_builds_decorated_deck_from_markdown_titles(self):
        titles = self.root / "titles.md"
        titles.write_text(
            "| 最终页码 | 原始标识 | 页面类型 | 页面标题 |\n"
            "|---:|---|---|---|\n"
            "| 1 | 第1页 | 封面 | 封面标题 |\n"
            "| 2 | 章节过渡页1 | 章节过渡页 | 第一部分 测试 |\n"
            "| 3 | 第2页 | 内容页 | 普通页面标题 |\n",
            encoding="utf-8",
        )
        output = self.root / "decorated.pptx"
        report = self.root / "decorated.json"
        self.run_builder(
            "--images-dir", self.images,
            "--titles", titles,
            "--style", "decorated",
            "--output", output,
            "--report", report,
        )

        result = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(result["titles"], 3)
        with zipfile.ZipFile(output) as deck:
            cover = deck.read("ppt/slides/slide1.xml").decode("utf-8")
            chapter = deck.read("ppt/slides/slide2.xml").decode("utf-8")
            content = deck.read("ppt/slides/slide3.xml").decode("utf-8")
        self.assertIn("封面眉题", cover)
        self.assertIn("章节浅色大序号", chapter)
        self.assertIn("标题科技青竖线", content)
        self.assertIn("03 / 03", content)

    def test_applies_builtin_theme_profile_and_json_overrides(self):
        titles = self.root / "titles.md"
        titles.write_text(
            "| Final page | Source label | Page type | Page title |\n"
            "|---:|---|---|---|\n"
            "| 1 | Page 1 | cover | Theme Test |\n"
            "| 2 | Section 1 | section | First Section |\n"
            "| 3 | Page 2 | content | Content Title |\n",
            encoding="utf-8",
        )
        theme = self.root / "theme.json"
        theme.write_text(
            json.dumps({
                "font": "Arial",
                "primary_color": "112233",
                "cover_eyebrow": "CUSTOM DECK",
                "show_page_number": False,
                "show_section_label": False,
            }),
            encoding="utf-8",
        )
        output = self.root / "themed.pptx"
        report = self.root / "themed.json"
        self.run_builder(
            "--images-dir", self.images,
            "--titles", titles,
            "--style", "decorated",
            "--theme-profile", "financial-red",
            "--theme", theme,
            "--output", output,
            "--report", report,
        )

        result = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(result["theme_profile"], "financial-red")
        with zipfile.ZipFile(output) as deck:
            cover = deck.read("ppt/slides/slide1.xml").decode("utf-8")
            content = deck.read("ppt/slides/slide3.xml").decode("utf-8")
            ppt_theme = deck.read("ppt/theme/theme1.xml").decode("utf-8")
        self.assertIn("CUSTOM DECK", cover)
        self.assertIn('val="112233"', content)
        self.assertIn('typeface="Arial"', ppt_theme)
        self.assertNotIn("03 / 03", content)
        self.assertNotIn("PART 01", content)

    def test_rejects_missing_sequence_number(self):
        (self.images / "02.png").unlink()
        output = self.root / "broken.pptx"
        result = self.run_builder("--images-dir", self.images, "--output", output, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing", result.stderr.lower())

    def test_rejects_title_count_mismatch(self):
        titles = self.root / "titles.md"
        titles.write_text("# Titles\n\n1. One\n2. Two\n", encoding="utf-8")
        output = self.root / "mismatch.pptx"
        result = self.run_builder(
            "--images-dir", self.images,
            "--titles", titles,
            "--style", "decorated",
            "--output", output,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("title", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
