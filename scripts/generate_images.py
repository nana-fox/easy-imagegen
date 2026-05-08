#!/usr/bin/env python3
"""Create an easy-imagegen output package with zero required dependencies."""

import argparse
import base64
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

from datetime import datetime
from pathlib import Path


STYLE_HINTS = {
    "auto": "Choose the most suitable visual style for the user's request.",
    "product": "Clean commercial product photography, controlled lighting, crisp details.",
    "poster": "Bold poster composition, strong hierarchy, memorable focal point.",
    "illustration": "Polished editorial illustration, coherent palette, expressive shapes.",
    "social": "Scroll-stopping social media visual, clear subject, strong crop.",
    "avatar": "Distinctive avatar image, readable silhouette, simple background.",
}


def parse_args():
    parser = argparse.ArgumentParser(description="Generate an easy-imagegen output package.")
    parser.add_argument("command", nargs="?", default="generate", choices=["generate", "doctor", "setup"])
    parser.add_argument("--prompt", help="User image request.")
    parser.add_argument("--count", type=int, default=1, help="Number of prompt variants.")
    parser.add_argument("--style", default="auto", help="Style preset name.")
    parser.add_argument("--size", default="1024x1024", help="Requested image size.")
    parser.add_argument("--output-dir", help="Directory for generated package.")
    parser.add_argument("--backend", default="auto", choices=["auto", "api", "prompt-only"])
    parser.add_argument("--dry-run", action="store_true", help="Resolve backend and write files without calling an API.")
    parser.add_argument("--base-url", help="Write this OpenAI-compatible base URL during setup.")
    parser.add_argument("--api-key", help="Write this API key during setup. It is not printed.")
    parser.add_argument("--model", default="gpt-image-1", help="Image model for setup/API generation.")
    parser.add_argument("--quality", default="high", help="Image quality for setup/API generation.")
    return parser.parse_args()


def default_output_dir():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path("outputs") / stamp


def build_prompt(user_prompt, style, index, count):
    hint = STYLE_HINTS.get(style, STYLE_HINTS["auto"])
    variant = f" Variant {index + 1} of {count}." if count > 1 else ""
    return (
        f"{user_prompt.strip()}\n\n"
        f"Style direction: {hint}{variant}\n"
        "Create a high-quality raster image. Avoid text unless explicitly requested."
    )


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def skill_root():
    return Path(__file__).resolve().parents[1]


def read_skill_env():
    if os.environ.get("IMAGEGEN_DISABLE_SKILL_ENV") == "1":
        return {}
    env_path = skill_root() / ".env"
    if not env_path.exists():
        return {}

    values = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def codex_home():
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()


def read_codex_api_key():
    auth_path = codex_home() / "auth.json"
    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return ""
    return data.get("OPENAI_API_KEY", "")


def detect_api_key(local_env):
    if os.environ.get("IMAGEGEN_API_KEY"):
        return os.environ["IMAGEGEN_API_KEY"], "IMAGEGEN_API_KEY env"
    if local_env.get("IMAGEGEN_API_KEY"):
        return local_env["IMAGEGEN_API_KEY"], "skill .env IMAGEGEN_API_KEY"
    if os.environ.get("OPENAI_API_KEY"):
        return os.environ["OPENAI_API_KEY"], "OPENAI_API_KEY env"
    if local_env.get("OPENAI_API_KEY"):
        return local_env["OPENAI_API_KEY"], "skill .env OPENAI_API_KEY"
    codex_key = read_codex_api_key()
    if codex_key:
        return codex_key, "Codex auth"
    return "", "missing"


def normalize_base_url(base_url):
    base_url = base_url.rstrip("/")
    if base_url and not base_url.endswith("/v1"):
        base_url += "/v1"
    return base_url


def read_codex_base_url():
    config_path = codex_home() / "config.toml"
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""

    provider_match = re.search(r'(?m)^model_provider\s*=\s*"([^"]+)"', text)
    provider = provider_match.group(1) if provider_match else ""
    if not provider:
        return ""

    section_re = re.compile(
        r'(?ms)^\[model_providers\.' + re.escape(provider) + r'\]\s*(.*?)(?=^\[|\Z)'
    )
    section_match = section_re.search(text)
    if not section_match:
        return ""

    base_match = re.search(r'(?m)^base_url\s*=\s*"([^"]+)"', section_match.group(1))
    return normalize_base_url(base_match.group(1)) if base_match else ""


def detect_base_url(local_env):
    if os.environ.get("IMAGEGEN_BASE_URL"):
        return normalize_base_url(os.environ["IMAGEGEN_BASE_URL"]), "IMAGEGEN_BASE_URL env"
    if local_env.get("IMAGEGEN_BASE_URL"):
        return normalize_base_url(local_env["IMAGEGEN_BASE_URL"]), "skill .env IMAGEGEN_BASE_URL"
    if os.environ.get("OPENAI_BASE_URL"):
        return normalize_base_url(os.environ["OPENAI_BASE_URL"]), "OPENAI_BASE_URL env"
    if local_env.get("OPENAI_BASE_URL"):
        return normalize_base_url(local_env["OPENAI_BASE_URL"]), "skill .env OPENAI_BASE_URL"
    codex_url = read_codex_base_url()
    if codex_url:
        return codex_url, "Codex config"
    return "https://api.openai.com/v1", "default"


def config_value(local_env, key, default=None):
    return os.environ.get(key) or local_env.get(key) or default


def api_config():
    local_env = read_skill_env()
    api_key, api_key_source = detect_api_key(local_env)
    base_url, base_url_source = detect_base_url(local_env)
    return {
        "api_key": api_key,
        "base_url": normalize_base_url(base_url),
        "api_key_source": api_key_source,
        "base_url_source": base_url_source,
        "model": config_value(local_env, "IMAGEGEN_MODEL", "gpt-image-1"),
        "quality": config_value(local_env, "IMAGEGEN_QUALITY", "high"),
    }


def choose_backend(requested):
    if requested == "prompt-only":
        return "prompt-only"
    config = api_config()
    if requested == "api" or config["api_key"]:
        return "api" if config["api_key"] else "prompt-only"
    return "prompt-only"


def public_api_config(config):
    return {
        "base_url": config["base_url"],
        "model": config["model"],
        "quality": config["quality"],
        "api_key_source": config["api_key_source"] if config["api_key"] else "missing",
        "base_url_source": config["base_url_source"],
    }


def run_doctor():
    config = api_config()
    backend = "api" if config["api_key"] else "prompt-only"
    print(f"Backend: {backend}")
    print(f"Base URL: {config['base_url']}")
    print(f"Base URL source: {config['base_url_source']}")
    print(f"Model: {config['model']}")
    print(f"Quality: {config['quality']}")
    if config["api_key"]:
        print(f"API key: found via {config['api_key_source']}")
    else:
        print("API key: missing")
    return 0


def prompt_if_missing(value, label, secret=False):
    if value:
        return value
    if not sys.stdin.isatty():
        raise SystemExit(f"Missing {label}. Pass --{label.replace('_', '-')} for non-interactive setup.")
    if secret:
        import getpass

        return getpass.getpass(f"{label}: ").strip()
    return input(f"{label}: ").strip()


def write_skill_env(base_url, api_key, model, quality):
    env_path = skill_root() / ".env"
    content = "\n".join(
        [
            f"IMAGEGEN_BASE_URL={normalize_base_url(base_url)}",
            f"IMAGEGEN_API_KEY={api_key}",
            f"IMAGEGEN_MODEL={model}",
            f"IMAGEGEN_QUALITY={quality}",
            "",
        ]
    )
    env_path.write_text(content, encoding="utf-8")
    try:
        env_path.chmod(0o600)
    except OSError:
        pass
    return env_path


def run_setup(args):
    base_url = prompt_if_missing(args.base_url, "base_url")
    api_key = prompt_if_missing(args.api_key, "api_key", secret=True)
    model = args.model or "gpt-image-1"
    quality = args.quality or "high"
    env_path = write_skill_env(base_url, api_key, model, quality)
    print(f"Config written: {env_path}")
    print(f"Base URL: {normalize_base_url(base_url)}")
    print(f"Model: {model}")
    print(f"Quality: {quality}")
    print("API key: saved")
    return 0


def call_image_api(prompt, size):
    config = api_config()
    payload = {
        "model": config["model"],
        "prompt": prompt,
        "size": size,
        "quality": config["quality"],
        "n": 1,
    }
    request = urllib.request.Request(
        f"{config['base_url']}/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    item = data.get("data", [{}])[0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    if item.get("url"):
        with urllib.request.urlopen(item["url"], timeout=120) as image_response:
            return image_response.read()
    raise RuntimeError("Image API response did not include b64_json or url")


def render_gallery(prompts, image_files, manifest):
    rows = []
    for item in prompts["items"]:
        image_name = image_files.get(item["id"])
        image_html = (
            f'<img src="images/{html.escape(image_name)}" alt="{html.escape(item["id"])}">'
            if image_name
            else '<div class="placeholder">Prompt ready</div>'
        )
        rows.append(
            "<article>"
            f"{image_html}"
            f"<h2>{html.escape(item['id'])}</h2>"
            f"<pre>{html.escape(item['prompt'])}</pre>"
            "</article>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>easy-imagegen output</title>
  <style>
    body {{ margin: 0; font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #20242a; background: #f7f7f4; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px; }}
    header {{ margin-bottom: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 16px; }}
    article {{ background: #fff; border: 1px solid #deded8; border-radius: 8px; overflow: hidden; }}
    img, .placeholder {{ width: 100%; aspect-ratio: 1; object-fit: cover; display: grid; place-items: center; background: #e9ece8; color: #596057; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; }}
    h2 {{ margin: 16px 16px 8px; font-size: 16px; }}
    pre {{ margin: 0 16px 16px; white-space: pre-wrap; font: 13px/1.45 ui-monospace, SFMono-Regular, Menlo, monospace; }}
    code {{ background: #ecece7; padding: 2px 6px; border-radius: 5px; }}
  </style>
</head>
<body>
<main>
  <header>
    <h1>easy-imagegen output</h1>
    <div>Backend: <code>{html.escape(manifest['backend'])}</code> Status: <code>{html.escape(manifest['status'])}</code></div>
  </header>
  <section class="grid">
    {''.join(rows)}
  </section>
</main>
</body>
</html>
"""


def main():
    args = parse_args()
    if args.command == "doctor":
        return run_doctor()
    if args.command == "setup":
        return run_setup(args)
    if not args.prompt:
        print("--prompt is required for generate", file=sys.stderr)
        return 2
    if args.count < 1:
        print("--count must be at least 1", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir) if args.output_dir else default_output_dir()
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    prompts = {
        "items": [
            {
                "id": f"image-{index + 1:02d}",
                "style": args.style,
                "size": args.size,
                "prompt": build_prompt(args.prompt, args.style, index, args.count),
            }
            for index in range(args.count)
        ]
    }

    backend = choose_backend(args.backend)
    config = api_config()
    status = "ready_for_generation"
    errors = []
    image_files = {}

    if backend == "api" and args.dry_run:
        status = "dry_run"
    elif backend == "api":
        for item in prompts["items"]:
            try:
                image_bytes = call_image_api(item["prompt"], item["size"])
                image_name = f"{item['id']}.png"
                (images_dir / image_name).write_bytes(image_bytes)
                image_files[item["id"]] = image_name
            except (RuntimeError, urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as error:
                errors.append({"id": item["id"], "error": str(error)})
        status = "generated" if len(image_files) == len(prompts["items"]) else "partial" if image_files else "failed"
        if errors:
            write_json(output_dir / "errors.json", {"items": errors})

    manifest = {
        "backend": backend,
        "status": status,
        "count": args.count,
        "style": args.style,
        "size": args.size,
        "images": image_files,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    if backend == "api":
        manifest["api"] = public_api_config(config)

    write_json(output_dir / "prompts.json", prompts)
    write_json(output_dir / "manifest.json", manifest)
    (output_dir / "index.html").write_text(render_gallery(prompts, image_files, manifest), encoding="utf-8")

    if args.dry_run:
        print(f"Dry-run output created: {output_dir}")
    elif backend == "prompt-only":
        print(f"Prompt-only output created: {output_dir}")
    else:
        print(f"Image output created: {output_dir} ({status})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
