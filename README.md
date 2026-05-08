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

For Codex:

```bash
bash install_as_skill.sh codex
```

For Claude Code:

```bash
bash install_as_skill.sh claude
```

If the skill already exists, replace it explicitly:

```bash
bash install_as_skill.sh codex --force
```

or:

```bash
bash install_as_skill.sh claude --force
```

## Check Backend

Run this after installation:

```bash
python scripts/generate_images.py doctor
```

Example when a usable API is available:

```text
Backend: api
Base URL: https://router.example.com/v1
Base URL source: Codex config
Model: gpt-image-2
Quality: high
API key: found via Codex auth
```

Example when no image backend is configured:

```text
Backend: prompt-only
API key: missing
```

## One-Time Setup

For Claude Code users without an existing Codex key/config, run:

```bash
cd ~/.claude/skills/easy-imagegen
python scripts/generate_images.py setup \
  --base-url "https://router.example.com/v1" \
  --api-key "$IMAGEGEN_API_KEY" \
  --model gpt-image-2 \
  --quality high
```

The command writes only this skill's `.env` and does not print the API key.

Then verify:

```bash
python scripts/generate_images.py doctor
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

Claude Code users should run `setup`, export environment variables, or let this
skill reuse an existing Codex configuration if Codex is also installed on the
same machine.

Create `.env` in the skill directory or export environment variables:

```env
IMAGEGEN_BASE_URL=
IMAGEGEN_API_KEY=sk-...
IMAGEGEN_MODEL=
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
