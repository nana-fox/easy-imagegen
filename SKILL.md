---
name: easy-imagegen
description: Generate images with a zero-install default path and optional OpenAI-compatible API fallback.
---

# easy-imagegen

Use this skill when the user wants to create, iterate on, or package raster images.

## Goal

Make image generation feel immediate:

1. Prefer the current agent's native image generation capability when available.
2. Reuse Codex auth and provider configuration for OpenAI-compatible API calls when available.
3. Use a custom OpenAI-compatible API when the user configured one or explicitly asks for it.
4. If no generator is available, create a prompt-only package instead of failing.

Do not require native image libraries, Python packages, Docker, LibreOffice, or an API key for the default path.

## Quick Flow

1. Clarify only the missing essentials: subject, use case, count, size, and style.
2. Create a concise prompt for each requested image.
3. If native image generation is available, generate images directly and save them under `outputs/<timestamp>/images/`.
4. If the user asks for API mode, or native generation is unavailable and an API key is available from skill `.env`, environment variables, or Codex auth, run:

   ```bash
   python scripts/generate_images.py --backend api --prompt "<request>" --count 1 --style auto
   ```

5. If no generator is available, run prompt-only mode:

   ```bash
   python scripts/generate_images.py --backend prompt-only --prompt "<request>" --count 1 --style auto
   ```

6. Return the output directory and mention `index.html`, `manifest.json`, and `prompts.json`.

## Claude Code Workflow

Claude Code usually cannot rely on Codex-native image tools. First diagnose the
backend:

```bash
python scripts/generate_images.py doctor
```

If `Backend: api`, generate directly:

```bash
python scripts/generate_images.py --prompt "<request>" --count 1 --style auto
```

If `Backend: prompt-only`, configure `IMAGEGEN_API_KEY` in this skill's `.env`
with the setup command:

```bash
python scripts/generate_images.py setup \
  --base-url "https://router.example.com/v1" \
  --api-key "<key>" \
  --model "gpt-image-2"
```

If the user also has Codex installed, this skill can reuse
`~/.codex/auth.json` and `~/.codex/config.toml` automatically.

## Backends

### Native Agent Backend

Use the agent's built-in image generation tools when present. This path requires no API key and no local dependencies. The skill's scripts are still useful for producing a manifest, prompt record, and gallery.

### API Backend

The API backend is optional and uses Python standard library HTTP calls. It expects an OpenAI-compatible `/images/generations` endpoint.

Configuration is resolved in this order:

1. Environment variables or this skill directory's `.env`.
2. Codex auth and active provider config:
   - `~/.codex/auth.json`
   - `~/.codex/config.toml`

This lets normal Codex users generate images without configuring another key.

Optional skill-local configuration:

```env
IMAGEGEN_BASE_URL=https://api.openai.com/v1
IMAGEGEN_API_KEY=sk-...
IMAGEGEN_MODEL=
IMAGEGEN_QUALITY=high
```

Compatibility aliases are also accepted:

```env
OPENAI_API_KEY=sk-...
```

Do not read project-root `.env` files. This avoids accidentally using unrelated application secrets.

Use `setup` for one-time local configuration. It writes only this skill's `.env`
and does not print the API key:

```bash
python scripts/generate_images.py setup --base-url "https://router.example.com/v1" --api-key "<key>"
```

### Prompt-Only Backend

Prompt-only mode creates:

```text
outputs/<timestamp>/
  index.html
  manifest.json
  prompts.json
  images/
```

This is the fallback when no image generator is available. It gives the user reviewable prompts they can paste into another image tool.

## Style Presets

Supported `--style` values:

- `auto`
- `product`
- `poster`
- `illustration`
- `social`
- `avatar`

Keep presets broad and practical. Do not add many narrowly overlapping styles.

## User Experience Rules

- Do not make the user configure an API key unless they ask for API mode or native generation is unavailable.
- Do not install dependencies for the default flow.
- Do not expose backend details unless needed to recover from failure.
- For multiple images, generate or package a small first batch when the direction is uncertain.
- Always preserve the final prompt text in `prompts.json`.
- On API failure, keep any successful images and write `errors.json`.
