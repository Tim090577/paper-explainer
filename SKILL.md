---
name: paper-explainer
description: 把一篇期刊論文（PDF）做成「繁體中文講解影片 × 原文 PDF 逐句同步」播放頁——講到哪一句，右邊原文就捲到那一段並標黃，點原文也能跳回講解。Use when the user wants a 論文導讀影片／論文講解動畫／影片跟 PDF 同步播放／paper explainer video synced with the PDF. 配音可換：預設 macOS 繁中本機語音，也能自錄或接任何 TTS。
---

# paper-explainer：論文講解影片 × PDF 同步

產出一個資料夾，用瀏覽器打開就是：左邊講解影片＋字幕＋章節，右邊論文原文，播放時原文自動捲動並標出這一句的出處。

```
<專案>/
  paper.json        設定（標題、引用、授權、配音引擎…）
  script.py         講稿：唯一手寫來源（幕、版面、逐句、錨點）
  src/paper.pdf     論文
  index.html        播放頁（pe.py page 產生）
  video/video.mp4   講解影片＋subtitles.vtt/srt
  pdf/pNN.jpg       原文頁面圖
  data/cues.json    每句的時間與 PDF 行框
```

所有指令都用 skill 內的 `scripts/pe.py`，以**絕對路徑**呼叫、把專案資料夾當參數，不要把腳本複製進專案：

```bash
PE=<這個 skill 的路徑>/scripts/pe.py      # 例：~/.agents/skills/paper-explainer/scripts/pe.py
python3 $PE doctor                         # 先檢查依賴；缺 PyMuPDF 就改用 uv run --with pymupdf python $PE …
```

## 安全與版權（先讀）

- **公開發佈要授權**：只有開放授權（CC BY 等）的論文才能把 PDF 頁面圖、原文 PDF、論文圖表放進公開網址。非開放授權 → 只做本機版，`paper.json` 的 `publish.include_pdf` 設 `false`，也不要裁原文圖。
- **配音資料外送**：`say`、`files`、`none` 都在本機。`edge` 或你自己接的雲端 TTS 會把念稿送出去——念稿裡不能有病人資料、私人筆記；第一次用前要跟使用者說清楚並取得同意。
- **醫學或專業內容**：講稿是 AI 依論文自撰，片頭與播放頁要保留「尚未經專業審查」聲明；數字一律要有原文錨點，不能憑記憶寫。
- 上傳、發佈到任何外部網站都要使用者明確同意。

## 流程

1. **建專案**：`python3 $PE init <專案> --pdf 論文.pdf`，然後填 `paper.json`（title、cite_short、citation_html、license、links）。
2. **讀原文**：`python3 $PE text <專案>` → `src/text.md`。先通讀全文，列出論文的問題、方法、主要結果、限制，再分幕。引句一律從 text.md **原樣複製**。
3. **寫講稿** `script.py`（或 `script.json`，兩者擇一，JSON 優先）：格式與寫作規則見 [references/script-format.md](references/script-format.md)。重點：一句一狀態、`t` 給字幕、`s` 給念稿、`a` 給原文錨點。圖表要放進投影片時，用 `python3 $PE crop <專案> 頁 x0 y0 x1 y1 figs/figN.png`（座標見 text.md 的「圖片區塊」）。
   寫完先跑 `python3 $PE check <專案>` 檢查結構（元素 id、show、錨點格式）。
4. **對錨點**：`python3 $PE anchors <專案>`。有任何一句找不到就會停下來並列出是哪一句——修引句，不要刪錨點。
5. **投影片**：`python3 $PE slides <專案>`，然後**逐張打開** `video/slides/slide_NN.png` 看：字被切掉、元素擠出畫面、太空或太擠都要回頭改 script.py。
6. **配音**：依 `paper.json` 的 `voice.engine` → `python3 $PE voice <專案>`（只重做某幾句：`voice <專案> 3 7 12`）。引擎與自錄流程見 [references/voice.md](references/voice.md)。要讓別人配音時先跑 `export` 給他念稿清單。
7. **（選用）回聽檢查**：`python3 $PE check-voice <專案>`（需要 whisper-cli 與 `PE_WHISPER_MODEL`）。
8. **合成影片**：`python3 $PE video <專案>`。
9. **播放頁**：`python3 $PE pages <專案>` → `python3 $PE page <專案>` → `python3 $PE serve <專案> 8790` 開 http://localhost:8790/ 實際播一遍。**不要用 `python3 -m http.server`**：它不支援 Range，影片不能拖曳跳轉。
10. **品質檢查**：照 [references/qa-checklist.md](references/qa-checklist.md) 一項項過。
11. **（使用者同意後）發佈**：`python3 $PE publish <專案>` 產生 `publish/` 靜態網站；要上傳 claude.ai Artifact 時加 `--artifact`（單檔上限 15 MB，影片會壓成 720p）。

一次跑完 4–9：`python3 $PE all <專案>`。改了講稿只要從 anchors 重跑；只改配音就從 voice 重跑。

## 沒辦法跑指令時（ChatGPT、Claude.ai、Gemini 等聊天介面）

用 [chat/PROMPT.md](chat/PROMPT.md)：聊天 AI 負責讀論文、問使用者問題、給大綱、輸出 `paper.json`＋`script.json`；使用者在自己電腦跑 `check` → `all` → `serve`。`anchors` 的錯誤訊息貼回對話讓 AI 修正。

## 交接給別人時

- 這個 skill 不綁定特定 agent：Claude Code、Codex、其他讀 SKILL.md 的 agent 都能照上面流程做；沒有 agent 的人也能照著手動跑。
- 「配音讓對方自己配」：把專案資料夾給對方，請他改 `paper.json` 的 `voice`（換聲音、自己的 TTS 指令，或 `files` 自錄），然後從 `voice` 往後重跑即可，講稿與錨點不用動。
- 踩過的坑與原因見 [references/lessons.md](references/lessons.md)。
