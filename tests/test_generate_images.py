import base64
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

from pathlib import Path
from unittest import mock


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
            "IMAGEGEN_TIMEOUT",
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

    def run_script_in_cwd(self, cwd, args, env=None):
        clean_env = os.environ.copy()
        for key in (
            "IMAGEGEN_API_KEY",
            "IMAGEGEN_BASE_URL",
            "IMAGEGEN_MODEL",
            "IMAGEGEN_QUALITY",
            "IMAGEGEN_TIMEOUT",
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
            cwd=cwd,
        )

    def run_installed_like_script(self, skill_dir, args, env=None):
        clean_env = os.environ.copy()
        for key in (
            "IMAGEGEN_API_KEY",
            "IMAGEGEN_BASE_URL",
            "IMAGEGEN_MODEL",
            "IMAGEGEN_QUALITY",
            "IMAGEGEN_TIMEOUT",
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

    def load_script_module(self):
        spec = importlib.util.spec_from_file_location("generate_images_under_test", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

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
            self.assertEqual(
                prompts["items"][0]["prompt"],
                "A clean product photo of a ceramic mug on a desk",
            )
            self.assertIn("Prompt-only output created", result.stdout)
            self.assertIn("ceramic mug", index_html)

    def test_default_output_dir_is_under_current_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp)

            result = self.run_script_in_cwd(
                cwd,
                [
                    "--prompt",
                    "A cute little fox",
                    "--backend",
                    "prompt-only",
                ],
            )

            output_root = cwd / "easy-imagegen-outputs"
            runs = list(output_root.iterdir())

            self.assertEqual(len(runs), 1)
            self.assertTrue((runs[0] / "README.md").exists())
            self.assertTrue((runs[0] / "manifest.json").exists())
            self.assertIn(str(output_root), result.stdout)
            self.assertIn("Image:", (runs[0] / "README.md").read_text())

    def test_enhance_prompt_appends_style_guidance_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "run"
            user_prompt = "A cute little fox"

            self.run_script(
                [
                    "--prompt",
                    user_prompt,
                    "--style",
                    "illustration",
                    "--output-dir",
                    str(output_dir),
                    "--backend",
                    "prompt-only",
                    "--enhance-prompt",
                ]
            )

            prompts = json.loads((output_dir / "prompts.json").read_text())

            self.assertIn(user_prompt, prompts["items"][0]["prompt"])
            self.assertIn("Style direction:", prompts["items"][0]["prompt"])

    def test_prompt_file_uses_final_prompt_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "run"
            prompt_path = Path(tmp) / "prompt.txt"
            user_prompt = "淘宝电商主图，极简科技风，深色背景。主视觉：一部手机显示APP界面。"
            prompt_path.write_text(user_prompt, encoding="utf-8")

            self.run_script(
                [
                    "--prompt-file",
                    str(prompt_path),
                    "--style",
                    "product",
                    "--output-dir",
                    str(output_dir),
                    "--backend",
                    "prompt-only",
                ]
            )

            prompts = json.loads((output_dir / "prompts.json").read_text())

            self.assertEqual(prompts["items"][0]["prompt"], user_prompt)

    def test_api_generation_uses_long_default_timeout(self):
        module = self.load_script_module()
        image_payload = base64.b64encode(b"fake-png").decode("ascii")
        timeouts = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps({"data": [{"b64_json": image_payload}]}).encode("utf-8")

        def fake_urlopen(_request, timeout):
            timeouts.append(timeout)
            return FakeResponse()

        env = {
            "IMAGEGEN_DISABLE_SKILL_ENV": "1",
            "IMAGEGEN_API_KEY": "test-key",
            "IMAGEGEN_BASE_URL": "https://router.example.com/v1",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch.object(module.urllib.request, "urlopen", side_effect=fake_urlopen):
                self.assertEqual(module.call_image_api("A cute little fox", "1024x1024"), b"fake-png")

        self.assertEqual(timeouts, [600])

    def test_api_timeout_can_be_configured_by_environment(self):
        module = self.load_script_module()
        image_payload = base64.b64encode(b"fake-png").decode("ascii")
        timeouts = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, _exc_type, _exc, _traceback):
                return False

            def read(self):
                return json.dumps({"data": [{"b64_json": image_payload}]}).encode("utf-8")

        def fake_urlopen(_request, timeout):
            timeouts.append(timeout)
            return FakeResponse()

        env = {
            "IMAGEGEN_DISABLE_SKILL_ENV": "1",
            "IMAGEGEN_API_KEY": "test-key",
            "IMAGEGEN_BASE_URL": "https://router.example.com/v1",
            "IMAGEGEN_TIMEOUT": "900",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch.object(module.urllib.request, "urlopen", side_effect=fake_urlopen):
                self.assertEqual(module.call_image_api("A cute little fox", "1024x1024"), b"fake-png")

        self.assertEqual(timeouts, [900])

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
            self.assertEqual(manifest["api"]["model"], "gpt-image-2")
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
            self.assertIn("Model: gpt-image-2", result.stdout)
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
                    "gpt-image-2",
                    "--quality",
                    "high",
                ],
                env={"CODEX_HOME": str(Path(tmp) / "missing-codex")},
            )

            env_text = (skill_dir / ".env").read_text(encoding="utf-8")
            self.assertIn("IMAGEGEN_BASE_URL=https://router.example.com/v1", env_text)
            self.assertIn("IMAGEGEN_API_KEY=secret-user-key", env_text)
            self.assertIn("IMAGEGEN_TIMEOUT=600", env_text)
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
