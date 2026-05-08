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

## Prompt Policy

Use the user's request as the source of truth, but let the agent choose the
final image prompt.

If the request is already a clear image prompt, use it directly. If it is
conversational, incomplete, or mixed with non-image instructions, lightly turn it
into a better image-generation prompt.

Stay faithful to the user's intent:

- Keep the subject, style, composition, count, aspect/size, text requirements,
  and negative constraints.
- Do not invent product claims, brand names, UI copy, selling points, people,
  objects, colors, or scene details that the user did not imply.
- If the user asks for exact/raw/no-change prompting, use their text directly.
- If the user gives a size such as `2000x2000`, pass that size through. Do not
  silently map it to a recommended size; if the API rejects it, report that
  clearly.
- Preserve the final prompt that was actually sent in `prompts.json`.

## Quick Flow

1. Decide the final image prompt from the user's request using the prompt policy.
2. Use the script from the user's current working directory so the result lands
   in `./easy-imagegen-outputs/<timestamp>/`.
3. For a short single-line prompt, pass it directly:

   ```bash
   python scripts/generate_images.py --prompt "A cute little fox"
   ```

4. For a long, multiline, quoted, or punctuation-heavy final prompt, put it in
   a UTF-8 text file and pass `--prompt-file`:

   ```bash
   python scripts/generate_images.py --prompt-file /path/to/prompt.txt
   ```
5. If the user requested count, size, style label, or output path, pass those
   as CLI flags.
6. Return the output directory, generated image path when present, `index.html`,
   `README.md`, and `prompts.json`.

## Claude Code Workflow

Claude Code usually cannot rely on Codex-native image tools. First diagnose the
backend:

```bash
python scripts/generate_images.py doctor
```

If `Backend: api`, generate from the user's current project/work directory:

```bash
python /path/to/easy-imagegen/scripts/generate_images.py --prompt "A cute little fox" --count 1 --style auto
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
IMAGEGEN_BASE_URL=
IMAGEGEN_API_KEY=sk-...
IMAGEGEN_MODEL=
IMAGEGEN_QUALITY=high
IMAGEGEN_TIMEOUT=600
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
easy-imagegen-outputs/<timestamp>/
  images/
  index.html
  README.md
  manifest.json
  prompts.json
  errors.json  # API failures only
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

These are metadata labels by default. They do not modify the prompt unless
`--enhance-prompt` is explicitly set. Prefer agent-side prompt judgment for
normal use; use `--enhance-prompt` only when a fixed style hint is useful.

## User Experience Rules

- Do not make the user configure an API key unless they ask for API mode or native generation is unavailable.
- Do not install dependencies for the default flow.
- Do not expose backend details unless needed to recover from failure.
- Keep the user-facing interaction simple: the user describes the desired image; the agent handles prompt shape, backend, output files, and reporting.
- Image generation can take several minutes. Run generation commands with at least a 10-minute shell/tool timeout or in the background, then inspect the output directory.
- For multiple images, generate or package a small first batch when the direction is uncertain.
- Always preserve the final prompt text in `prompts.json`.
- Write normal results under the user's current directory unless `--output-dir` is explicit.
- Final responses should tell the user where the image is, where the preview is, and where the prompt record is.
- On API failure, keep any successful images and write `errors.json`.
