import json
import subprocess
import sys
import tempfile
import unittest

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_images.py"


class GenerateImagesTest(unittest.TestCase):
    def test_prompt_only_backend_writes_reviewable_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "run"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--prompt",
                    "A clean product photo of a ceramic mug on a desk",
                    "--count",
                    "2",
                    "--style",
                    "product",
                    "--output-dir",
                    str(output_dir),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            manifest = json.loads((output_dir / "manifest.json").read_text())
            prompts = json.loads((output_dir / "prompts.json").read_text())
            index_html = (output_dir / "index.html").read_text()

            self.assertEqual(manifest["backend"], "prompt-only")
            self.assertEqual(manifest["status"], "ready_for_generation")
            self.assertEqual(manifest["count"], 2)
            self.assertEqual(len(prompts["items"]), 2)
            self.assertEqual(prompts["items"][0]["style"], "product")
            self.assertIn("ceramic mug", prompts["items"][0]["prompt"])
            self.assertIn("Prompt-only output created", result.stdout)
            self.assertIn("ceramic mug", index_html)


if __name__ == "__main__":
    unittest.main()
