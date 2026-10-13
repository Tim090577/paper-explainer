#!/usr/bin/env python3
"""把講稿裡的「原文引句」對到 PDF 的頁碼與逐行框。

PDF 有引用括號 [13,40,41]、行尾斷字、ﬁ 連字、頁眉頁腳，講稿裡的引句沒有，
所以兩邊都正規化成「只剩小寫英數字（含中日韓字）」再比對，並保留
「正規化字元 → PDF 字詞」的對照，最後把字詞框依行合併。

錨點寫法（script.py 每一句的 a）：
    "原文中的一句話"                     → 找這句
    ["開頭幾個字", "結尾幾個字"]          → 從開頭到結尾整段
    {"page": 3}                          → 只捲到第 3 頁，不標行
    {"page": 3, "rect": [x0,y0,x1,y1]}   → 標一個固定框（圖、表），單位 pt
"""

import re
import unicodedata

import fitz

CITE = re.compile(r"\[[\d,\s–\-−]+\]")
REF_HEAD = re.compile(r"^\s*(references|reference|bibliography|literature cited|參考文獻|参考文献)\s*$", re.I)


def norm_chars(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return [c for c in s if c.isalnum()]


def norm(s):
    return "".join(norm_chars(CITE.sub(" ", s)))


class Locator:
    def __init__(self, pdf_path, header=0.06, footer=0.94, body_end_page=None, stop_at_references=True):
        doc = fitz.open(pdf_path)
        self.page_size = [(p.rect.width, p.rect.height) for p in doc]
        self.words = []          # (page, x0, y0, x1, y1, block, line)
        self.body_pages = 0
        chars, owner = [], []
        stop = False
        for p in doc:
            if stop or (body_end_page and p.number + 1 > body_end_page):
                break
            self.body_pages = p.number + 1
            h = p.rect.height
            ws = [w for w in p.get_text("words") if w[1] > h * header and w[3] < h * footer]
            lines = {}
            for w in ws:
                lines.setdefault((w[5], w[6]), []).append(w)
            for key in sorted(lines):
                row = sorted(lines[key], key=lambda w: w[7])
                text = " ".join(w[4] for w in row)
                if stop_at_references and p.number >= 1 and REF_HEAD.match(text):
                    stop = True
                    break
                buf, spans = "", []
                for w in row:
                    start = len(buf)
                    buf += w[4] + " "
                    spans.append((start, len(buf), len(self.words)))
                    self.words.append((p.number + 1, w[0], w[1], w[2], w[3], w[5], w[6]))
                drop = set()
                for m in CITE.finditer(buf):
                    drop.update(range(m.start(), m.end()))
                for start, end, wi in spans:
                    for i in range(start, end):
                        if i not in drop:
                            for c in norm_chars(buf[i]):
                                chars.append(c)
                                owner.append(wi)
        self.text = "".join(chars)
        self.owner = owner
        self.cursor = 0          # 講稿通常照原文順序走：從上一句的位置往後找

    def _find(self, needle, lo=0):
        n = norm(needle)
        if not n:
            raise KeyError(f"引句是空的：{needle!r}")
        for start in (lo, 0):
            i = self.text.find(n, start)
            if i >= 0:
                return i, i + len(n)
        raise KeyError(f"找不到：{needle[:70]!r}")

    def locate(self, a):
        if isinstance(a, dict):
            if "rect" in a:
                return [{"page": a["page"], "rects": [a["rect"]]}]
            return [{"page": a["page"], "rects": []}]
        if isinstance(a, str):
            i, j = self._find(a, self.cursor)
        elif isinstance(a, (list, tuple)) and len(a) == 2:
            i, _ = self._find(a[0], self.cursor)
            n_end = norm(a[1])
            j0 = self.text.find(n_end, i)
            if j0 < 0:
                raise KeyError(f"找不到結尾：{a[1][:70]!r}")
            j = j0 + len(n_end)
        else:
            raise ValueError(f"看不懂的錨點：{a!r}")
        self.cursor = i
        return self._rows(sorted(set(self.owner[i:j])))

    def _rows(self, wids):
        rows = {}
        for wi in wids:
            pg, x0, y0, x1, y1, b, ln = self.words[wi]
            r = rows.setdefault((pg, b, ln), [x0, y0, x1, y1])
            r[0], r[1], r[2], r[3] = min(r[0], x0), min(r[1], y0), max(r[2], x1), max(r[3], y1)
        out = {}
        for (pg, _, _), r in sorted(rows.items(), key=lambda kv: (kv[0][0], kv[1][1], kv[1][0])):
            out.setdefault(pg, []).append([round(v, 1) for v in r])
        return [{"page": pg, "rects": rs} for pg, rs in out.items()]


def dump_text(pdf_path, out_path, header=0.06, footer=0.94):
    """把 PDF 正文依頁、依段落輸出成 Markdown，方便寫講稿時直接複製引句；附上圖片區塊座標。"""
    doc = fitz.open(pdf_path)
    lines = [f"# {pdf_path}\n", "引句請直接從這裡複製；圖片框座標可用在 {\"page\": n, \"rect\": [...]}。\n"]
    for p in doc:
        h = p.rect.height
        lines.append(f"\n## p.{p.number + 1}  （{p.rect.width:.0f} × {h:.0f} pt）\n")
        for b in p.get_text("dict")["blocks"]:
            x0, y0, x1, y1 = b["bbox"]
            if y1 < h * header or y0 > h * footer:
                continue
            if b["type"] == 1:
                lines.append(f"\n[圖片區塊] rect = [{x0:.0f}, {y0:.0f}, {x1:.0f}, {y1:.0f}]\n")
                continue
            txt = unicodedata.normalize("NFKC", " ".join("".join(s["text"] for s in ln["spans"]) for ln in b["lines"])).strip()
            if txt:
                lines.append(f"\n{txt}\n")
    open(out_path, "w").write("".join(lines))
    return out_path
