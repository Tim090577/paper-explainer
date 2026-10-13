# AGENTS.md

This repository is the **paper-explainer** skill: it turns a paper PDF into a narrated Traditional-Chinese explainer video plus a PDF-synced player page.

When the user asks for a paper explainer video, 論文講解影片, 論文導讀, or a video synced with the PDF:

1. Read [`SKILL.md`](SKILL.md) and follow its workflow exactly.
2. Write the script per [`references/script-format.md`](references/script-format.md) (`script.py` or `script.json`).
3. Run every step with `python3 scripts/pe.py <command> <project-dir>` from this repository; do not copy the scripts into the project.
4. Before delivering, go through [`references/qa-checklist.md`](references/qa-checklist.md).

Never publish, upload, or send narration to a cloud TTS without the user's explicit consent.
