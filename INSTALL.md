# 安裝（給接手的人）

最快：`git clone https://github.com/Tim090577/paper-explainer.git && cd paper-explainer && ./install.sh`（自動連到下表三個目錄）。

把整個 `paper-explainer/` 資料夾放到你的 agent 會讀的 skills 目錄：

| 工具 | 放這裡 |
|---|---|
| Claude Code | `~/.claude/skills/paper-explainer/`（或專案內 `.claude/skills/`） |
| Codex | `~/.codex/skills/paper-explainer/` |
| 其他讀 SKILL.md 的 agent | `~/.agents/skills/paper-explainer/` |

同一台機器要給好幾個 agent 用時，放一份實體、其他用 symlink，避免版本分岔。

## 依賴

- Python 3.9 以上、PyMuPDF（`pip install pymupdf`，或每次用 `uv run --with pymupdf python …`）
- ffmpeg／ffprobe
- Google Chrome 或 Chromium（截投影片；路徑特殊時設環境變數 `CHROME`）
- 配音（擇一）：macOS 內建 `say`（預設）、自己的錄音檔、或自己的 TTS 指令——見 `references/voice.md`
- 選用：whisper-cli＋`PE_WHISPER_MODEL`（回聽檢查）、uv（edge-tts、pypinyin）

裝好後跑一次：

```bash
python3 <skill 路徑>/scripts/pe.py doctor
```

然後跟 agent 說：「用 paper-explainer 把這篇論文做成講解影片跟 PDF 同步播放頁」，或照 `SKILL.md` 的流程手動跑。
