#!/usr/bin/env bash
# 把這個 skill 連到常見 agent 的 skills 目錄（symlink，不複製，更新時只要 git pull）。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
for root in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.agents/skills"; do
  mkdir -p "$root"
  target="$root/paper-explainer"
  if [ -e "$target" ] && [ "$(cd "$target" && pwd -P)" = "$(cd "$HERE" && pwd -P)" ]; then
    echo "✓ $target（已是這份）"
  elif [ -e "$target" ]; then
    echo "⚠ $target 已存在且不是這份，略過；要換請先移走它"
  else
    ln -s "$HERE" "$target" && echo "✓ 連結 $target"
  fi
done
python3 "$HERE/scripts/pe.py" doctor || true
echo "Claude Code 要開新 session 才會看到新 skill。"
