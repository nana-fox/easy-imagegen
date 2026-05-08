# easy-imagegen

`easy-imagegen` is a Codex skill for lightweight image generation workflows.
It keeps the default path zero-install and lets advanced users opt into an
OpenAI-compatible image API.

## What It Does

- Uses the current agent's native image generation capability when available.
- Reuses Codex auth and active provider config for OpenAI-compatible
  `/images/generations` calls when available.
- Lets users override with a custom API when needed.
- Falls back again to a prompt-only output package instead of failing.
- Writes reviewable outputs: `index.html`, `manifest.json`, and `prompts.json`.
- Avoids native image dependencies such as Pillow, OpenCV, Docker, LibreOffice,
  or `python-pptx`.

## Install

From a local checkout:

```bash
bash install_as_skill.sh codex
```

The skill installs to:

```text
~/.codex/skills/easy-imagegen
```

If the skill already exists, replace it explicitly:

```bash
bash install_as_skill.sh codex --force
```

## Prompt-Only Smoke Test

```bash
python scripts/generate_images.py \
  --backend prompt-only \
  --prompt "A clean product photo of a ceramic mug on a desk" \
  --count 2 \
  --style product
```

This creates:

```text
outputs/<timestamp>/
  index.html
  manifest.json
  prompts.json
  images/
```

## API Mode

Most Codex users do not need to configure anything else. When `IMAGEGEN_API_KEY`
is not set, the script tries:

- `~/.codex/auth.json` for `OPENAI_API_KEY`
- `~/.codex/config.toml` for the active provider `base_url`

You can still override per skill or per shell session.

Create `.env` in the skill directory or export environment variables:

```env
IMAGEGEN_BASE_URL=
IMAGEGEN_API_KEY=sk-...
IMAGEGEN_MODEL=gpt-image-1
IMAGEGEN_QUALITY=high
```

Then run:

```bash
python scripts/generate_images.py \
  --backend api \
  --prompt "A clean product photo of a ceramic mug on a desk" \
  --count 1 \
  --style product
```

The script uses Python standard library HTTP calls only.

## Test

```bash
python -m unittest discover -s tests
```
