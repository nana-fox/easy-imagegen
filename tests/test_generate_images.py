import json
import os
import subprocess
import sys
import tempfile
import unittest

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "generate_images.py"


class GenerateImagesTest(unittest.TestCase):
    def run_script(self, args, env=None):
        clean_env = os.environ.copy()
        for key in (
            "IMAGEGEN_API_KEY",
            "IMAGEGEN_BASE_URL",
            "IMAGEGEN_MODEL",
            "IMAGEGEN_QUALITY",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "CODEX_HOME",
        ):
            clean_env.pop(key, None)
        if env:
            clean_env.update(env)
        clean_env.setdefault("IMAGEGEN_DISABLE_SKILL_ENV", "1")
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=True,
            capture_output=True,
            text=True,
            env=clean_env,
        )

    def run_installed_like_script(self, skill_dir, args, env=None):
        clean_env = os.environ.copy()
        for key in (
            "IMAGEGEN_API_KEY",
            "IMAGEGEN_BASE_URL",
            "IMAGEGEN_MODEL",
            "IMAGEGEN_QUALITY",
            "OPENAI_API_KEY",
            "OPENAI_BASE_URL",
            "CODEX_HOME",
            "IMAGEGEN_DISABLE_SKILL_ENV",
        ):
            clean_env.pop(key, None)
        if env:
            clean_env.update(env)
        return subprocess.run(
            [sys.executable, str(skill_dir / "scripts" / "generate_images.py"), *args],
            check=True,
            capture_output=True,
            text=True,
            env=clean_env,
            cwd=skill_dir,
        )

    def test_prompt_only_backend_writes_reviewable_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "run"

            result = self.run_script(
                [
                    "--prompt",
                    "A clean product photo of a ceramic mug on a desk",
                    "--count",
                    "2",
                    "--style",
                    "product",
                    "--output-dir",
                    str(output_dir),
                    "--backend",
                    "prompt-only",
                ],
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

    def test_auto_backend_uses_codex_auth_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            codex_home.mkdir()
            (codex_home / "auth.json").write_text(
                json.dumps({"OPENAI_API_KEY": "codex-key"}),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                '\n'.join(
                    [
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://router.example.com"',
                    ]
                ),
                encoding="utf-8",
            )
            output_dir = Path(tmp) / "run"

            result = self.run_script(
                [
                    "--prompt",
                    "A cute little fox",
                    "--count",
                    "1",
                    "--style",
                    "illustration",
                    "--output-dir",
                    str(output_dir),
                    "--dry-run",
                ],
                env={"CODEX_HOME": str(codex_home)},
            )

            manifest = json.loads((output_dir / "manifest.json").read_text())

            self.assertEqual(manifest["backend"], "api")
            self.assertEqual(manifest["status"], "dry_run")
            self.assertEqual(manifest["api"]["base_url"], "https://router.example.com/v1")
            self.assertEqual(manifest["api"]["model"], "gpt-image-1")
            self.assertNotIn("codex-key", (output_dir / "manifest.json").read_text())
            self.assertIn("Dry-run output created", result.stdout)

    def test_doctor_reports_backend_without_leaking_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            codex_home = Path(tmp) / "codex-home"
            codex_home.mkdir()
            (codex_home / "auth.json").write_text(
                json.dumps({"OPENAI_API_KEY": "secret-codex-key"}),
                encoding="utf-8",
            )
            (codex_home / "config.toml").write_text(
                '\n'.join(
                    [
                        'model_provider = "custom"',
                        "",
                        "[model_providers.custom]",
                        'base_url = "https://router.example.com"',
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_script(["doctor"], env={"CODEX_HOME": str(codex_home)})

            self.assertIn("Backend: api", result.stdout)
            self.assertIn("Base URL: https://router.example.com/v1", result.stdout)
            self.assertIn("Model: gpt-image-1", result.stdout)
            self.assertIn("API key: found via Codex auth", result.stdout)
            self.assertNotIn("secret-codex-key", result.stdout)

    def test_setup_writes_skill_env_and_doctor_uses_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "skill"
            skill_dir.mkdir()
            (skill_dir / "scripts").mkdir()
            temp_script = skill_dir / "scripts" / "generate_images.py"
            temp_script.write_text(SCRIPT.read_text(encoding="utf-8"), encoding="utf-8")

            result = self.run_installed_like_script(
                skill_dir,
                [
                    "setup",
                    "--base-url",
                    "https://router.example.com",
                    "--api-key",
                    "secret-user-key",
                    "--model",
                    "gpt-image-1",
                    "--quality",
                    "high",
                ],
                env={"CODEX_HOME": str(Path(tmp) / "missing-codex")},
            )

            env_text = (skill_dir / ".env").read_text(encoding="utf-8")
            self.assertIn("IMAGEGEN_BASE_URL=https://router.example.com/v1", env_text)
            self.assertIn("IMAGEGEN_API_KEY=secret-user-key", env_text)
            self.assertNotIn("secret-user-key", result.stdout)

            doctor = self.run_installed_like_script(
                skill_dir,
                ["doctor"],
                env={"CODEX_HOME": str(Path(tmp) / "missing-codex")},
            )

            self.assertIn("Backend: api", doctor.stdout)
            self.assertIn("Base URL: https://router.example.com/v1", doctor.stdout)
            self.assertIn("API key: found via skill .env IMAGEGEN_API_KEY", doctor.stdout)
            self.assertNotIn("secret-user-key", doctor.stdout)


if __name__ == "__main__":
    unittest.main()
