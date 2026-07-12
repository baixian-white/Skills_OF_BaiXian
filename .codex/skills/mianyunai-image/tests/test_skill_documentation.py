import unittest
from pathlib import Path


SKILL_PATH = Path(__file__).parents[1] / "SKILL.md"


class SkillDocumentationTests(unittest.TestCase):
    def test_skill_name_matches_directory(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")
        self.assertEqual(SKILL_PATH.parent.name, "mianyunai-image")
        self.assertIn("name: mianyunai-image", skill)

    def test_requires_asking_user_to_choose_model(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("required model selection", skill)
        self.assertIn("ask the user which model to use", skill)
        self.assertIn("do not select a model silently", skill)
        self.assertIn("before the final parameter confirmation", skill)
        for model in (
            "gpt-image-2",
            "gpt-image-2-4k",
            "gemini-3-pro-image-preview",
            "gemini-3.1-flash-image-preview",
        ):
            with self.subTest(model=model):
                self.assertIn(model, skill)

    def test_requires_explicit_parameter_confirmation_before_request(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("explicit parameter confirmation", skill)
        self.assertIn(
            "do not send any image-generation request until the user explicitly confirms",
            skill,
        )
        for field in (
            "resolution tier",
            "aspect ratio",
            "api request size",
            "quality",
            "output_format",
            "moderation",
            "quantity",
        ):
            with self.subTest(field=field):
                self.assertIn(field, skill)

    def test_documents_image_and_prompt_editing_workflow(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("/images/edits", skill)
        self.assertIn("--image", skill)
        self.assertIn("image[]", skill)
        self.assertIn("optional mask", skill)
        self.assertIn("local images are uploaded to the configured third-party api", skill)
        self.assertIn("confirm the exact image paths", skill)
        self.assertIn("gpt-image-2-4k", skill)
        self.assertIn("gemini-3.1-flash-image-preview", skill)

    def test_documents_model_specific_generation_routes_and_results(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("fixed 4k sku", skill)
        self.assertIn("2880x2880", skill)
        self.assertIn("quality=high", skill)
        self.assertIn("three 524", skill)
        self.assertIn("only imagen models are supported", skill)
        self.assertIn("/v1beta/models/{model}:generatecontent", skill)
        self.assertIn('responsemodalities=["image"]', skill)
        self.assertIn("native_gemini_probe.py", skill)
        self.assertIn("1,314,944", skill)
        self.assertIn("1,320,148", skill)

    def test_documents_complete_website_size_matrix_and_live_results(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("24/24", skill)
        self.assertIn("historical observed actual", skill)
        for tier in ("1k", "2k", "4k"):
            self.assertIn(tier, skill)
        for ratio in ("1:1", "3:2", "2:3", "16:9", "9:16", "4:3", "3:4", "21:9"):
            self.assertIn(ratio, skill)
        for request_size in (
            "1024x1024", "1536x1024", "1024x1536", "1280x720",
            "720x1280", "1024x768", "768x1024", "1280x544",
            "2048x2048", "2160x1440", "1440x2160", "2560x1440",
            "1440x2560", "2048x1536", "1536x2048", "2560x1088",
            "2880x2880", "3456x2304", "2304x3456", "3840x2160",
            "2160x3840", "3200x2400", "2400x3200", "3840x1600",
        ):
            with self.subTest(request_size=request_size):
                self.assertIn(request_size, skill)

    def test_requires_original_png_delivery_and_actual_dimensions(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")
        normalized = skill.lower()
        self.assertIn("do not crop or resize generated images", normalized)
        self.assertIn("deliver the validated original image at its returned dimensions", normalized)
        self.assertIn("report the actual width and height", normalized)
        self.assertNotIn("center-crop", normalized)
        self.assertNotIn("cropping to 1672x940", normalized)

    def test_documents_live_configurable_parameters(self):
        skill = SKILL_PATH.read_text(encoding="utf-8")
        self.assertIn("output_format", skill)
        self.assertIn("auto / low / medium / high", skill)
        self.assertIn("moderation", skill)
        self.assertIn("png / jpeg / webp", skill)

    def test_requires_alpha_evidence_for_transparency(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("transparent pixels", skill)
        self.assertIn("prompt injection", skill)
        self.assertIn("do not report transparency", skill)

    def test_documents_native_and_website_transparency_outcomes(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("background=transparent", skill)
        self.assertIn("0 transparent pixels", skill)
        self.assertIn("website post-processing", skill)
        self.assertIn("#00ff00", skill)
        self.assertIn("#ff00ff", skill)
        self.assertIn("forces png", skill)
        self.assertIn("border-connected", skill)
        self.assertIn("1672x941 rgba png", skill)
        self.assertIn("720x405 webp", skill)

    def test_documents_default_relay_format_mismatch(self):
        skill = SKILL_PATH.read_text(encoding="utf-8").lower()
        self.assertIn("requested webp", skill)
        self.assertIn("returned png", skill)
        self.assertIn("url + webp", skill)
        self.assertIn("also returned png", skill)
        self.assertIn("do not retry", skill)


if __name__ == "__main__":
    unittest.main()
