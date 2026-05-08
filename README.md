# easy-imagegen

**一句话生成图片的 Claude Code / Codex Skill。**

默认使用 `gpt-image-2`，优先复用 Codex 已有的登录态和自定义 provider；在 Claude Code 中也可以通过一次 `setup` 配置后直接出图。整个默认路径不安装 Pillow、OpenCV、Docker、LibreOffice、`python-pptx` 等底层依赖。

---

## 能做什么

- **一句话出图**：把自然语言需求整理成稳定 prompt，并保存输出结果。
- **默认 `gpt-image-2`**：未显式配置 `IMAGEGEN_MODEL` 时使用 `gpt-image-2`。
- **Codex 零配置优先**：自动读取 `~/.codex/auth.json` 和 `~/.codex/config.toml`，复用当前 Codex API key 与 provider `base_url`。
- **Claude Code 可一次配置**：没有 Codex 配置时，用 `setup` 写入 skill-local `.env`。
- **OpenAI-compatible API**：支持 OpenAI、Azure/OpenAI-compatible router、LiteLLM、new-api、自建中转等 `/images/generations` 接口。
- **不会误吃密钥**：只读取环境变量、skill 自己目录的 `.env`、Codex auth/config；不会向上递归读取项目根目录 `.env`。
- **可审阅输出包**：每次生成或降级都会保留 `index.html`、`manifest.json`、`prompts.json`。
- **Prompt-only 兜底**：没有可用图片后端时不假装成功，而是输出可复制的 prompt 包。
- **可选原样提示词**：默认会追加轻量风格方向；需要完全按原文生成时使用 `--raw-prompt`。

---

## 安装

### Codex

```bash
git clone https://github.com/nana-fox/easy-imagegen.git ~/.codex/skills/easy-imagegen
```

已有本地 checkout 时：

```bash
cd easy-imagegen
bash install_as_skill.sh codex --force
```

安装位置：

```text
~/.codex/skills/easy-imagegen
```

### Claude Code

```bash
git clone https://github.com/nana-fox/easy-imagegen.git ~/.claude/skills/easy-imagegen
```

已有本地 checkout 时：

```bash
cd easy-imagegen
bash install_as_skill.sh claude --force
```

安装位置：

```text
~/.claude/skills/easy-imagegen
```

---

## 安装后先检查

进入安装目录后运行：

```bash
python scripts/generate_images.py doctor
```

如果已经有可用后端，会看到类似：

```text
Backend: api
Base URL: https://router.example.com/v1
Base URL source: Codex config
Model: gpt-image-2
Quality: high
API key: found via Codex auth
```

如果还不能直接出图，会看到：

```text
Backend: prompt-only
API key: missing
```

这时看下一节配置一次即可。

---

## Claude Code 没有 Codex 密钥时

Claude Code 用户如果没有 `~/.codex/auth.json` / `~/.codex/config.toml`，运行一次 `setup`：

```bash
cd ~/.claude/skills/easy-imagegen
python scripts/generate_images.py setup \
  --base-url "https://router.example.com/v1" \
  --api-key "$IMAGEGEN_API_KEY" \
  --model gpt-image-2 \
  --quality high
```

`setup` 只写当前 skill 目录的 `.env`，不会打印 API key。

再检查：

```bash
python scripts/generate_images.py doctor
```

看到 `Backend: api` 后就可以直接生成图片。

---

## 怎么用

### 让 agent 使用

安装后直接对 Claude Code 或 Codex 说：

> 用 easy-imagegen 生成一张可爱的小狐狸图片，儿童绘本风格，暖色调，1024x1024。

agent 会按 `SKILL.md` 的流程选择后端、生成或降级，并告诉你输出目录。

### 直接用 CLI

```bash
python scripts/generate_images.py \
  --prompt "A cute little fox, warm children's book illustration, soft orange fur, bright curious eyes" \
  --count 1 \
  --style illustration
```

如果你希望完全按输入提示词生成，不追加任何风格说明：

```bash
python scripts/generate_images.py \
  --prompt "A cute little fox, warm children's book illustration" \
  --raw-prompt
```

指定输出目录：

```bash
python scripts/generate_images.py \
  --prompt "A clean product photo of a ceramic mug on a desk" \
  --count 2 \
  --style product \
  --output-dir outputs/mug-test
```

---

## 输出结构

```text
outputs/<timestamp>/
  images/
    image-01.png        # 生成成功时存在
  index.html            # 可浏览预览页
  manifest.json         # 后端、状态、模型、输出文件
  prompts.json          # 每张图最终 prompt
  errors.json           # API 部分失败或全部失败时存在
```

`manifest.json` 示例：

```json
{
  "backend": "api",
  "status": "generated",
  "count": 1,
  "style": "illustration",
  "size": "1024x1024",
  "images": {
    "image-01": "image-01.png"
  },
  "api": {
    "base_url": "https://router.example.com/v1",
    "model": "gpt-image-2",
    "quality": "high",
    "api_key_source": "Codex auth",
    "base_url_source": "Codex config"
  }
}
```

---

## 后端优先级

`--backend auto` 默认按这个顺序：

1. 当前环境变量或 skill-local `.env`：`IMAGEGEN_API_KEY` / `IMAGEGEN_BASE_URL` / `IMAGEGEN_MODEL`。
2. 兼容环境变量：`OPENAI_API_KEY` / `OPENAI_BASE_URL`。
3. Codex 配置：`~/.codex/auth.json` 和 `~/.codex/config.toml`。
4. 没有 API key 时进入 `prompt-only`。

`.env` 示例：

```env
IMAGEGEN_BASE_URL=
IMAGEGEN_API_KEY=sk-...
IMAGEGEN_MODEL=
IMAGEGEN_QUALITY=high
```

留空 `IMAGEGEN_MODEL` 时使用脚本默认值 `gpt-image-2`。

---

## 风格预设

当前内置轻量风格确实存在于 `styles/` 目录中，但它们不是复杂模板库，而是用于给 prompt 追加一小段方向提示：

| 风格 | 适用场景 |
| --- | --- |
| `auto` | 让 agent 根据需求选择方向 |
| `product` | 产品图、商品展示、商业摄影 |
| `poster` | 海报、活动视觉、强主视觉 |
| `illustration` | 插画、绘本、编辑视觉 |
| `social` | 社媒图、小红书/推文配图 |
| `avatar` | 头像、角色、标识性图像 |

脚本当前内置的实际风格提示在 `scripts/generate_images.py` 的 `STYLE_HINTS` 中，`styles/*.md` 是给 agent 和用户阅读的说明文件。默认生成时最终 prompt 会是：

```text
<你的原始提示词>

Style direction: <所选风格的一句话方向>
Create a high-quality raster image. Avoid text unless explicitly requested.
```

使用 `--raw-prompt` 时不会追加这些内容。

---

## 常见问题

### `doctor` 显示 `Backend: prompt-only`

说明没有找到 API key。Claude Code 用户运行：

```bash
python scripts/generate_images.py setup --base-url "https://router.example.com/v1" --api-key "$IMAGEGEN_API_KEY"
```

### API 失败但输出目录存在

这是预期行为。检查输出目录里的 `errors.json`。成功生成的图片会保留在 `images/`，失败项会记录错误。

### 想强制只生成 prompt 包

```bash
python scripts/generate_images.py \
  --backend prompt-only \
  --prompt "A cute little fox" \
  --style illustration
```

### 想换模型

临时指定：

```bash
python scripts/generate_images.py setup --base-url "https://router.example.com/v1" --api-key "$IMAGEGEN_API_KEY" --model gpt-image-2
```

或在 `.env` 写：

```env
IMAGEGEN_MODEL=gpt-image-2
```

---

## 开发验证

```bash
python -m unittest discover -s tests
```

本项目只使用 Python 标准库。

---

## License

MIT License. See [LICENSE](./LICENSE) if present.
