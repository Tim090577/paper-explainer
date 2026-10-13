"""講稿：唯一手寫來源。格式說明見 skill 的 references/script-format.md。

每一幕（scene）：kick（小標）、title、sub（選填）、rows（版面，列 × 元素）、steps（逐句）。
每一句（step）：
    t     字幕（顯示用，可以有數字、符號）
    s     念稿（TTS／錄音用；省略時同 t）。數字、百分比、單位、縮寫要寫成念得出來的樣子
    a     PDF 錨點：原文引句字串／[開頭, 結尾]／{"page": n}／{"page": n, "rect": [x0,y0,x1,y1]}
    show  這一句要浮現的元素 id（會累加）
    focus 要框起來強調的元素 id（省略時＝show）
"""


def card(id, h, b="", tone="ink", w=1):
    return {"id": id, "k": "card", "h": h, "b": b, "tone": tone, "w": w}


def stat(id, n, l, tone="red", w=1):
    return {"id": id, "k": "stat", "n": n, "l": l, "tone": tone, "w": w}


def bar(id, l, v, t, tone="blue"):
    return {"id": id, "k": "bar", "l": l, "v": v, "t": t, "tone": tone}


def pts(id, l, n, tone="blue", max_n=8):
    return {"id": id, "k": "pts", "l": l, "n": n, "tone": tone, "max": max_n}


def chip(id, t, tone="blue"):
    return {"id": id, "k": "chip", "t": t, "tone": tone}


def arrow(id, t="→"):
    return {"id": id, "k": "arrow", "t": t}


def note(id, t, tone="amber"):
    return {"id": id, "k": "note", "t": t, "tone": tone}


def quiz(id, src, stem, ans, why):
    return {"id": id, "k": "quiz", "src": src, "stem": stem, "ans": ans, "why": why}


def img(id, src, cap="", w=1):
    return {"id": id, "k": "img", "src": src, "cap": cap, "w": w}


def group(id, h, els, w=1):
    return {"id": id, "k": "group", "h": h, "els": els, "w": w}


def stack(els, w=1):
    return {"id": "", "k": "stack", "els": els, "w": w}


SCENES = [
    {
        "kick": "期刊導讀 · Journal 2024", "title": "這篇論文在問什麼", "sub": "English title here",
        "rows": [
            [stat("s1", "40%", "某個<br>重要比例"), stat("s2", "20–30", "歲<br>好發年齡", "blue")],
            [card("disc", "本片由 AI 製作", "講解稿與版面依論文自撰，內容尚未經專業人員審查。", "gray")],
        ],
        "steps": [
            {"t": "這支影片帶你讀一篇 2024 年的論文。", "a": {"page": 1}, "show": ["disc"]},
            {"t": "第一個重點：約 40% 的病人會出現這個表現。",
             "s": "第一個重點：大約百分之四十的病人，會出現這個表現。",
             "a": "把原文裡支持這句話的那一句，原樣貼在這裡", "show": ["s1"]},
            {"t": "好發年齡在 20 到 30 歲。", "s": "好發年齡在二十到三十歲。",
             "a": ["原文那段的開頭幾個字", "同一段結尾的幾個字"], "show": ["s2"]},
        ],
    },
]
