#!/usr/bin/env bash
set -euo pipefail

target="${1:-codex}"
force="false"
skill_name="easy-imagegen"

if [ "${2:-}" = "--force" ]; then
  force="true"
fi

case "$target" in
  codex)
    dest="${CODEX_HOME:-$HOME/.codex}/skills/$skill_name"
    ;;
  claude)
    dest="$HOME/.claude/skills/$skill_name"
    ;;
  *)
    echo "Usage: bash install_as_skill.sh [codex|claude]" >&2
    exit 2
    ;;
esac

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$(dirname "$dest")"
if [ -e "$dest" ]; then
  if [ "$force" != "true" ]; then
    echo "$dest already exists. Re-run with --force to replace it." >&2
    exit 1
  fi
  rm -rf "$dest"
fi
cp -R "$src" "$dest"

if [ ! -f "$dest/.env" ]; then
  cp "$dest/.env.example" "$dest/.env"
fi

echo "Installed $skill_name to $dest"
