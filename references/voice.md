# 配音：預設繁中自然語音，也可換成自己的

`paper.json` 的 `voice` 決定用什麼配音。換引擎後只要從 `voice` 往後重跑（voice → video → page），講稿、錨點、投影片都不用動。

```json
"voice": { "engine": "say", "voice": "Meijia", "rate": 205, "command": null, "files_dir": "voice-in" }
```

| engine | 在哪裡跑 | 適合 | 設定 |
|---|---|---|---|
| `say`（預設） | macOS 本機 | 快速、免費、不外傳 | `voice`：繁中可選 Meijia（預設，最自然）、Flo、Sandy、Shelley、Reed、Eddy；`rate` 190–215 |
| `files` | 本機 | **真人錄音**或在別處做好的配音 | 先 `pe.py export` 產生 `narration.tsv`，每句錄一檔放 `voice-in/01.wav`、`02.m4a` … |
| `command` | 看你接什麼 | 自己的 TTS（BreezyVoice、ElevenLabs、OpenAI、Azure…） | `command` 是參數陣列，可用 `{text}`、`{text_file}`、`{out}`（輸出 wav） |
| `edge` | 微軟線上服務 | 很自然的 zh-TW 神經語音 | `voice`：zh-TW-HsiaoChenNeural、zh-TW-HsiaoYuNeural、zh-TW-YunJheNeural。**會外傳念稿**，且服務端偶爾擋（403），失敗就換回 `say` |
| `none` | 本機 | 先做靜音草稿看節奏 | 依字數估時間，之後再換成真的配音 |

## 例子

自己的 TTS 腳本（輸出 wav）：

```json
"voice": { "engine": "command",
           "command": ["python3", "/path/my_tts.py", "--text-file", "{text_file}", "--out", "{out}"] }
```

真人錄音：

```bash
python3 $PE export <專案>          # 產生 narration.tsv 與 voice-in/README.txt
# 照 narration.tsv 的「念稿」欄一句錄一檔：voice-in/01.wav、02.wav …（句首句尾不用留白）
# paper.json 改成 "engine": "files"
python3 $PE voice <專案> && python3 $PE video <專案> && python3 $PE page <專案>
```

## 讓配音聽起來自然

- `s`（念稿）才是 TTS 看到的文字：數字、百分比、單位、縮寫都要改成念法（見 script-format.md）。
- 句子長度控制在 15–40 字；太長的句子 TTS 會一口氣念完、沒有換氣。
- 句間停頓由 `video.gap`（預設 0.4 秒）、幕末停頓由 `video.gap_scene_end`（0.95 秒）控制，不要在念稿裡塞空白。
- 有句子念錯：改那句的 `s`，然後只重做那句 `voice <專案> 句號`，再跑 `video` 與 `page`。
- 回聽檢查（`check-voice`）用拼音相似度比對，同音字、數字常是假警報；低分的句子人工聽一次再決定要不要改。
