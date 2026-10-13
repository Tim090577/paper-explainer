#!/usr/bin/env python3
"""paper-explainer：把一篇論文做成「講解影片 × PDF 原文同步」播放頁。

    python3 pe.py doctor                       # 檢查依賴
    python3 pe.py init   <專案> --pdf 論文.pdf  # 建專案骨架（paper.json、script.py、src/）
    python3 pe.py text   <專案>                 # 正文逐段輸出 src/text.md，寫講稿時從這裡複製引句
    python3 pe.py crop   <專案> 頁 x0 y0 x1 y1 輸出.png   # 從 PDF 裁圖（圖表），座標見 text.md
    python3 pe.py check   <專案>                # 只檢查講稿結構（script.py 或 script.json）
    python3 pe.py anchors <專案>                # 每句引句 → PDF 頁碼與逐行框（找不到就停）
    python3 pe.py slides  <專案>                # 一句一狀態的投影片 PNG
    python3 pe.py export  <專案>                # 匯出念稿清單，給要自己配音／錄音的人
    python3 pe.py voice   <專案> [句號 …]       # 依 paper.json 的 voice 設定配音 → video/audio/NN.wav
    python3 pe.py check-voice <專案>            # （選用）本機 whisper 回聽比對
    python3 pe.py video   <專案>                # 轉場＋整軌音訊 → video/video.mp4、字幕
    python3 pe.py pages   <專案>                # PDF 頁面轉圖（播放頁右側）
    python3 pe.py page    <專案>                # data/cues.json＋index.html 播放頁
    python3 pe.py serve   <專案> [埠]            # 本機預覽（支援影片跳轉）
    python3 pe.py publish <專案> [--artifact]   # 打包 publish/ 靜態網站；--artifact 給 claude.ai Artifact 用
    python3 pe.py all     <專案>                # anchors → slides → voice → video → pages → page

需要 PyMuPDF：沒有的話用  uv run --with pymupdf python pe.py …
"""

import json
import os
import re
import shutil
import subprocess
import sys
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / "scripts"))

DEFAULT_CFG = {
    "title": "論文導讀",
    "cite_short": "Author et al. · Journal Year",
    "citation_html": "Author A, et al. <i>Title.</i> Journal Year;Vol:Page",
    "license": "",
    "links": {},
    "pdf": "src/paper.pdf",
    "pdf_body": {"header": 0.06, "footer": 0.94, "end_page": None, "stop_at_references": True},
    "page_images": {"scale": 2.2},
    "voice": {"engine": "say", "voice": "Meijia", "rate": 205, "command": None, "files_dir": "voice-in", "post": "warm"},
    "video": {"fps": 30, "gap": 0.40, "gap_scene_end": 0.95, "lead": 0.30, "xfade": 0.40, "xfade_scene": 0.55},
    "disclaimer": "講解稿與版面由 AI 依論文自撰，內容尚未經專業人員審查；請以原文為準。",
    "publish": {"include_pdf": True, "max_mb": 15},
}


# ───────────────────────────── 共用
def die(msg):
    print(f"✗ {msg}", file=sys.stderr)
    sys.exit(1)


def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


class Proj:
    def __init__(self, path):
        self.dir = Path(path).resolve()
        cfgp = self.dir / "paper.json"
        if not cfgp.exists():
            die(f"{cfgp} 不存在；先跑 pe.py init")
        self.cfg = merge(DEFAULT_CFG, json.load(open(cfgp)))
        self.pdf = self.dir / self.cfg["pdf"]
        self.vid = self.dir / "video"
        self.data = self.dir / "data"
        self.tmp = self.vid / "temp"

    def script(self):
        js = self.dir / "script.json"
        if js.exists():   # 聊天型 AI（ChatGPT、Claude.ai、Gemini）產出的 JSON 講稿
            d = json.load(open(js))
            scenes = d["scenes"] if isinstance(d, dict) else d
        else:
            spec = importlib.util.spec_from_file_location("paper_script", self.dir / "script.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            scenes = mod.SCENES
        validate(scenes)
        return scenes

    def states(self):
        out = []
        scenes = self.script()
        for si, sc in enumerate(scenes):
            seen = []
            for k, st in enumerate(sc["steps"]):
                show = st.get("show", [])
                seen = seen + [x for x in show if x not in seen]
                out.append({"n": len(out) + 1, "scene": si, "k": k, "last": k == len(sc["steps"]) - 1,
                            "t": st["t"], "s": st.get("s", st["t"]), "a": st.get("a"),
                            "visible": list(seen), "focus": st.get("focus", show)})
        return scenes, out


KINDS = {"card", "stat", "bar", "pts", "chip", "arrow", "note", "quiz", "img", "svg", "group", "stack"}


def validate(scenes):
    """講稿結構檢查：元素類型、id、每句的 show 都要對得到。錯誤一次列完。"""
    errs = []
    for si, sc in enumerate(scenes, 1):
        ids = set()

        def walk(el):
            k = el.get("k")
            if k not in KINDS:
                errs.append(f"第 {si} 幕：未知元素類型 {k!r}")
            if el.get("id"):
                if el["id"] in ids:
                    errs.append(f"第 {si} 幕：元素 id 重複 {el['id']!r}")
                ids.add(el["id"])
            for c in el.get("els", []):
                walk(c)
        for key in ("title", "rows", "steps"):
            if key not in sc:
                errs.append(f"第 {si} 幕：缺 {key}")
        for row in sc.get("rows", []):
            for el in row:
                walk(el)
        for k, st in enumerate(sc.get("steps", []), 1):
            if not st.get("t"):
                errs.append(f"第 {si} 幕第 {k} 句：缺字幕 t")
            for x in st.get("show", []) + st.get("focus", []):
                if x not in ids:
                    errs.append(f"第 {si} 幕第 {k} 句：show/focus 的 {x!r} 不在這一幕的 rows 裡")
            a = st.get("a")
            if a is not None and not (isinstance(a, str) or (isinstance(a, list) and len(a) == 2)
                                      or (isinstance(a, dict) and "page" in a)):
                errs.append(f"第 {si} 幕第 {k} 句：錨點格式不對 {a!r}")
    if errs:
        die("講稿有問題：\n  " + "\n  ".join(errs))


def tool(name, env=None):
    p = os.environ.get(env) if env else None
    p = p or shutil.which(name) or (f"/opt/homebrew/bin/{name}" if Path(f"/opt/homebrew/bin/{name}").exists() else None)
    return p


def chrome():
    for c in [os.environ.get("CHROME"), "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium", shutil.which("google-chrome"),
              shutil.which("chromium"), shutil.which("chromium-browser"), shutil.which("chrome")]:
        if c and Path(c).exists():
            return c
    return None


def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def dur(p):
    out = subprocess.run([tool("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


# ───────────────────────────── doctor / init / text / crop
def cmd_doctor(_=None):
    ok = True
    for name, val, need in [("python ≥ 3.9", sys.version_info >= (3, 9), True),
                            ("PyMuPDF (fitz)", importlib.util.find_spec("fitz") is not None, True),
                            ("ffmpeg", tool("ffmpeg"), True), ("ffprobe", tool("ffprobe"), True),
                            ("Chrome／Chromium（截圖）", chrome(), True),
                            ("macOS say（預設配音）", shutil.which("say"), False),
                            ("uv／uvx（edge-tts、pypinyin 選用）", shutil.which("uv"), False),
                            ("whisper-cli（回聽檢查選用）", shutil.which("whisper-cli"), False)]:
        mark = "✓" if val else ("✗" if need else "–")
        ok &= bool(val) or not need
        print(f"{mark} {name}{'' if val else ('  ← 必要' if need else '  （選用）')}")
    print("可以開始" if ok else "缺必要依賴；PyMuPDF 可用 uv run --with pymupdf python pe.py …")


def cmd_init(path, pdf=None, force=False):
    d = Path(path).resolve()
    d.mkdir(parents=True, exist_ok=True)
    (d / "src").mkdir(exist_ok=True)
    if pdf:
        shutil.copyfile(pdf, d / "src/paper.pdf")
    for name in ("paper.json", "script.py"):
        dst = d / name
        if dst.exists() and not force:
            print(f"保留既有 {dst.name}")
            continue
        shutil.copyfile(SKILL / "templates" / name, dst)
        print(f"建立 {dst}")
    print("下一步：填 paper.json → pe.py text 產生 src/text.md → 依 references/script-format.md 寫 script.py")


def cmd_text(p):
    from locator import dump_text
    b = p.cfg["pdf_body"]
    out = dump_text(str(p.pdf), str(p.dir / "src/text.md"), b["header"], b["footer"])
    print(f"已輸出 {out}")


def cmd_crop(p, page, x0, y0, x1, y1, out):
    import fitz
    doc = fitz.open(str(p.pdf))
    pix = doc[int(page) - 1].get_pixmap(matrix=fitz.Matrix(3, 3), clip=fitz.Rect(float(x0), float(y0), float(x1), float(y1)))
    outp = p.dir / out
    outp.parent.mkdir(parents=True, exist_ok=True)
    pix.save(str(outp))
    print(f"已裁 {outp}（{pix.width}×{pix.height}）")


# ───────────────────────────── anchors
def cmd_anchors(p):
    from locator import Locator
    b = p.cfg["pdf_body"]
    loc = Locator(str(p.pdf), b["header"], b["footer"], b["end_page"], b["stop_at_references"])
    _, sts = p.states()
    res, miss = [], []
    for st in sts:
        if st["a"] is None:
            res.append([])
            print(f"{st['n']:02d} ——  （沒有錨點）{st['t'][:28]}")
            continue
        try:
            r = loc.locate(st["a"])
        except (KeyError, ValueError) as e:
            miss.append((st["n"], str(e)))
            r = []
        res.append(r)
        pg = ",".join(str(x["page"]) for x in r) or "?"
        print(f"{st['n']:02d} p{pg:<5} {sum(len(x['rects']) for x in r):>2} 行  {st['t'][:28]}")
    p.data.mkdir(exist_ok=True)
    json.dump({"pages": loc.page_size, "body_pages": loc.body_pages, "anchors": res}, open(p.data / "anchors.json", "w"))
    if miss:
        for n, e in miss:
            print(f"✗ 第 {n} 句：{e}")
        die(f"{len(miss)} 句錨點找不到。引句要從 src/text.md 原樣複製（可省略引用括號）。")
    print(f"錨點 OK：{len(res)} 句（正文到 p.{loc.body_pages}）")


# ───────────────────────────── slides
def cmd_slides(p):
    from render import slide_html
    scenes, sts = p.states()
    anchors = json.load(open(p.data / "anchors.json"))["anchors"]
    if len(anchors) != len(sts):
        die("anchors.json 和講稿句數不同；先重跑 anchors")
    sd = p.vid / "slides"
    sd.mkdir(parents=True, exist_ok=True)
    for f in sd.glob("slide_*"):
        f.unlink()
    for st in sts:
        (sd / f"slide_{st['n']:02d}.html").write_text(
            slide_html(scenes[st["scene"]], st, anchors[st["n"] - 1], len(scenes), p.cfg["cite_short"], p.dir))
    ch = chrome() or die("找不到 Chrome／Chromium；設定環境變數 CHROME")

    def shot(n):
        h = sd / f"slide_{n:02d}.html"
        subprocess.run([ch, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                        "--virtual-time-budget=3000", f"--screenshot={sd / f'slide_{n:02d}.png'}",
                        "--window-size=1920,1080", h.as_uri()], check=True, capture_output=True)

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(shot, [s["n"] for s in sts]))
    n_png = len(list(sd.glob("slide_*.png")))
    if n_png != len(sts):
        die(f"截圖 {n_png} 張 ≠ {len(sts)} 句")
    print(f"投影片 {n_png} 張。請逐張打開檢查：字有沒有被切掉、元素有沒有擠出畫面。")


# ───────────────────────────── voice
def tts_text(s):
    s = s.replace("／", "，").replace("/", " ").replace("（", "，").replace("）", "，").replace("(", "，").replace(")", "，")
    return re.sub(r"\s+", " ", s).strip()


def cmd_export(p):
    _, sts = p.states()
    vin = p.dir / p.cfg["voice"]["files_dir"]
    vin.mkdir(exist_ok=True)
    rows = ["編號\t幕\t念稿（TTS 或錄音照這個念）\t字幕"]
    for st in sts:
        rows.append(f"{st['n']:02d}\t{st['scene'] + 1}\t{tts_text(st['s'])}\t{st['t']}")
    (p.dir / "narration.tsv").write_text("\n".join(rows) + "\n")
    (vin / "README.txt").write_text(
        "自己配音：每句錄一個檔，檔名用兩位數編號（01.wav、02.m4a、03.mp3 …），對照 ../narration.tsv。\n"
        "句首句尾不用留白，pe.py voice 會自動補停頓並對齊影格。錄好後把 paper.json 的 voice.engine 設成 \"files\"。\n")
    print(f"已匯出 narration.tsv（{len(sts)} 句）與 {vin}/README.txt")


def synth(p, st, raw):
    v = p.cfg["voice"]
    eng = v["engine"]
    text = tts_text(st["s"])
    if eng == "say":
        run(["say", "-v", v.get("voice") or "Meijia", "-r", str(v.get("rate") or 205), "-o", str(raw.with_suffix(".aiff")), text])
        return raw.with_suffix(".aiff")
    if eng == "edge":   # 會把念稿送到微軟的服務；不要放病人或私人資料
        out = raw.with_suffix(".mp3")
        run(["uvx", "edge-tts", "--voice", v.get("voice") or "zh-TW-HsiaoChenNeural", "--rate", v.get("edge_rate", "+0%"),
             "--text", text, "--write-media", str(out)], capture_output=True)
        return out
    if eng == "command":  # 例：["python3","my_tts.py","--in","{text_file}","--out","{out}"]
        tf = raw.with_suffix(".txt")
        tf.write_text(text)
        out = raw.with_suffix(".wav")
        cmd = [c.replace("{text}", text).replace("{text_file}", str(tf)).replace("{out}", str(out)) for c in v["command"]]
        run(cmd)
        return out
    if eng == "files":
        vin = p.dir / v["files_dir"]
        for ext in (".wav", ".m4a", ".mp3", ".aiff", ".flac"):
            f = vin / f"{st['n']:02d}{ext}"
            if f.exists():
                return f
        die(f"缺錄音檔 {vin}/{st['n']:02d}.*")
    if eng == "none":   # 靜音草稿：依字數估時間，先看節奏，之後再配音
        secs = max(1.2, len(re.sub(r"\s", "", st["s"])) / 4.6)
        out = raw.with_suffix(".wav")
        run([tool("ffmpeg"), "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", f"{secs:.2f}", str(out)])
        return out
    die(f"未知的 voice.engine：{eng}（say／edge／command／files／none）")


# 溫和後製（取自 exam-explainer-video 的護耳鏈，去掉降調）：去低頻、去齒音、切刺耳高頻、補一點暖、輕壓縮
POST = {
    "none": "",
    "warm": ("highpass=f=60,deesser=i=0.5:m=0.5:f=0.45,lowpass=f=9200,"
             "equalizer=f=150:t=q:w=1:g=2,equalizer=f=5000:t=q:w=1.2:g=-3,"
             "acompressor=threshold=-22dB:ratio=2:attack=5:release=80,"),
}


def cmd_voice(p, only=None):
    vc = p.cfg["video"]
    fps = vc["fps"]
    ad = p.vid / "audio"
    ad.mkdir(parents=True, exist_ok=True)
    p.tmp.mkdir(parents=True, exist_ok=True)
    _, sts = p.states()
    eng = p.cfg["voice"]["engine"]
    if eng == "edge":
        print("⚠ edge 引擎會把念稿送到微軟的語音服務；確認念稿沒有病人或私人資料。")
    for st in sts:
        n = st["n"]
        if only and n not in only:
            continue
        src = synth(p, st, p.tmp / f"raw_{n:02d}")
        lead = vc["lead"] if st["k"] == 0 else 0.0
        tail = vc["gap_scene_end"] if st["last"] else vc["gap"]
        d = lead + dur(src) + tail
        d = round(d * fps + 0.4999) / fps           # 對齊影格邊界，影音才不會累積漂移
        post = POST.get(p.cfg["voice"].get("post", "warm"), "")
        run([tool("ffmpeg"), "-loglevel", "error", "-y", "-i", str(src), "-af",
             f"{post}adelay={int(lead * 1000)}:all=1,apad,atrim=0:{d:.6f},aresample=44100", "-ac", "2",
             str(ad / f"slide_{n:02d}.wav")])
        print(f"{n:02d} {d:6.2f}s  {st['t'][:30]}")


def cmd_check_voice(p):
    wc = shutil.which("whisper-cli")
    model = os.environ.get("PE_WHISPER_MODEL")
    if not (wc and model and Path(model).exists()):
        print("略過：需要 whisper-cli 與環境變數 PE_WHISPER_MODEL（ggml 模型路徑）")
        return
    _, sts = p.states()
    rows = []
    for st in sts:
        n = st["n"]
        w16 = p.tmp / f"asr_{n:02d}.wav"
        run([tool("ffmpeg"), "-loglevel", "error", "-y", "-i", str(p.vid / f"audio/slide_{n:02d}.wav"),
             "-ar", "16000", "-ac", "1", str(w16)])
        out = subprocess.run([wc, "-m", model, "-l", "zh", "-nt", "-np", "-f", str(w16)],
                             capture_output=True, text=True).stdout.strip()
        rows.append({"n": n, "ref": st["s"], "asr": out})
    pj = p.tmp / "asr_pairs.json"
    json.dump(rows, open(pj, "w"), ensure_ascii=False)
    code = r"""
import json,re,sys
from collections import Counter
from pypinyin import lazy_pinyin
NUM=set("0123456789〇零一二三四五六七八九十百千萬万兩两億亿")
CJK=re.compile(r"[一-鿿]")
def clean(s): return "".join(c for c in CJK.findall(s) if c not in NUM)
def sim(a,b):
    pa,pb=lazy_pinyin(clean(a)),lazy_pinyin(clean(b))
    if not pa or not pb: return 1.0
    return sum((Counter(pa)&Counter(pb)).values())/max(len(pa),len(pb))
rows=json.load(open(sys.argv[1])); bad=0
for r in rows:
    s=sim(r["ref"],r["asr"]); r["sim"]=round(s,3); bad+=s<0.85
    print(("✗ " if s<0.85 else "  ")+f'{r["n"]:02d} {s:.2f}  {r["asr"][:60]}')
json.dump(rows,open(sys.argv[1],"w"),ensure_ascii=False,indent=1)
print("低於 0.85：",bad,"/",len(rows),"（同音字、數字常是假警報，人工聽一下再決定）")
"""
    run(["uv", "run", "--with", "pypinyin", "python", "-c", code, str(pj)]) if shutil.which("uv") else \
        run([sys.executable, "-c", code, str(pj)])


# ───────────────────────────── video
def cmd_video(p):
    vc = p.cfg["video"]
    fps = vc["fps"]
    ff = tool("ffmpeg")
    sd, ad = p.vid / "slides", p.vid / "audio"
    p.tmp.mkdir(parents=True, exist_ok=True)
    _, sts = p.states()
    clips = []
    for st in sts:
        n = st["n"]
        d = round(dur(ad / f"slide_{n:02d}.wav") * fps) / fps
        prev, cur = sd / f"slide_{max(1, n - 1):02d}.png", sd / f"slide_{n:02d}.png"
        xf = (f"xfade=transition=slideleft:duration={vc['xfade_scene']}:offset=0.02" if st["k"] == 0 and n > 1
              else f"xfade=transition=fade:duration={vc['xfade']}:offset=0.02")
        clip = p.tmp / f"clip_{n:02d}.mp4"
        run([ff, "-loglevel", "error", "-y",
             "-loop", "1", "-framerate", str(fps), "-t", f"{d + 1:.3f}", "-i", str(prev),
             "-loop", "1", "-framerate", str(fps), "-t", f"{d + 1:.3f}", "-i", str(cur),
             "-filter_complex", f"[0:v][1:v]{xf},format=yuv420p[v]", "-map", "[v]",
             "-frames:v", str(round(d * fps)), "-r", str(fps),
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-tune", "stillimage", str(clip)])
        clips.append(clip)
        print(f"clip {n:02d} {d:6.2f}s")
    (p.tmp / "concat_v.txt").write_text("".join(f"file '{c.name}'\n" for c in clips))
    wavs = [(ad / "slide_{:02d}.wav".format(s["n"])).as_posix() for s in sts]
    (p.tmp / "concat_a.txt").write_text("".join(f"file '{w}'\n" for w in wavs))
    run([ff, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(p.tmp / "concat_v.txt"),
         "-c", "copy", str(p.tmp / "video_only.mp4")])
    run([ff, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(p.tmp / "concat_a.txt"),
         "-c", "pcm_s16le", str(p.tmp / "audio_full.wav")])
    out = p.vid / "video.mp4"
    af = (["-af", "loudnorm=I=-18.5:TP=-1.8:LRA=9,alimiter=limit=0.9,aresample=44100"]
          if p.cfg["voice"].get("post", "warm") != "none" else [])   # 全片統一音量
    run([ff, "-loglevel", "error", "-y", "-i", str(p.tmp / "video_only.mp4"), "-i", str(p.tmp / "audio_full.wav"),
         "-map", "0:v", "-map", "1:a", *af, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", str(out)])
    real = [round(dur(c) * fps) / fps for c in clips]   # 時間軸用實際片長，不用推算
    t, timeline = 0.0, []
    for d in real:
        timeline.append((t, t + d))
        t += d
    json.dump(timeline, open(p.tmp / "timeline.json", "w"))
    write_subs(p, sts, timeline)
    print(f"video.mp4 {dur(out):.1f}s")


def fmt_ts(t, sep=","):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)) % 1000:03d}"


def split_lines(t, width=26):
    out, cur = [], ""
    for ch in t:
        cur += ch
        if len(cur) >= width and ch in "，。；：、？！,.;:?!":
            out.append(cur)
            cur = ""
    if cur:
        out.append(cur)
    return out


def write_subs(p, sts, timeline):
    vc = p.cfg["video"]
    srt, vtt, i = [], ["WEBVTT", ""], 0
    for st, (t0, t1) in zip(sts, timeline):
        lead = vc["lead"] if st["k"] == 0 else 0.0
        parts = split_lines(st["t"])
        total = sum(len(x) for x in parts)
        a = t0 + lead
        span = (t1 - t0 - lead) - (vc["gap_scene_end"] if st["last"] else vc["gap"])
        for part in parts:
            b = a + span * len(part) / total
            i += 1
            srt += [str(i), f"{fmt_ts(a)} --> {fmt_ts(b)}", part, ""]
            vtt += [f"{fmt_ts(a, '.')} --> {fmt_ts(b, '.')}", part, ""]
            a = b
    (p.vid / "subtitles.srt").write_text("\n".join(srt))
    (p.vid / "subtitles.vtt").write_text("\n".join(vtt))


# ───────────────────────────── pages / page / publish
def cmd_pages(p):
    import fitz
    out = p.dir / "pdf"
    out.mkdir(exist_ok=True)
    for f in out.glob("p*.jpg"):
        f.unlink()
    body = json.load(open(p.data / "anchors.json"))["body_pages"]
    sc = p.cfg["page_images"]["scale"]
    doc = fitz.open(str(p.pdf))
    for pg in doc:
        if pg.number >= body:
            break
        pg.get_pixmap(matrix=fitz.Matrix(sc, sc)).save(str(out / f"p{pg.number + 1:02d}.jpg"), jpg_quality=82)
    print(f"PDF 頁面圖：{body} 頁")


def cmd_page(p):
    scenes_src, sts = p.states()
    timeline = json.load(open(p.tmp / "timeline.json"))
    anc = json.load(open(p.data / "anchors.json"))
    cues = [{"t0": round(t0, 3), "t1": round(t1, 3), "scene": st["scene"], "text": st["t"], "a": a}
            for st, (t0, t1), a in zip(sts, timeline, anc["anchors"])]
    scenes = []
    for si, sc in enumerate(scenes_src):
        first = next(c for c in cues if c["scene"] == si)
        scenes.append({"kick": sc.get("kick", ""), "title": re.sub("<[^>]+>", "", sc["title"]), "t0": first["t0"]})
    pages = [{"n": i + 1, "w": w, "h": h, "src": f"pdf/p{i + 1:02d}.jpg"}
             for i, (w, h) in enumerate(anc["pages"][:anc["body_pages"]])]
    json.dump({"scenes": scenes, "cues": cues, "pages": pages, "scale": p.cfg["page_images"]["scale"]},
              open(p.data / "cues.json", "w"), ensure_ascii=False)
    c = p.cfg
    links = " ".join(f'<a href="{u}" target="_blank" rel="noopener">{k}</a>' for k, u in c["links"].items())
    pdf_link = f'<a href="{c["pdf"]}" target="_blank" rel="noopener">原始 PDF</a> ' if c["publish"]["include_pdf"] else ""
    lic = f" · {c['license']}" if c["license"] else ""
    s = (SKILL / "templates/player.html").read_text()
    for k, v in {"{{TITLE}}": c["title"], "{{CITATION}}": c["citation_html"] + lic,
                 "{{LINKS}}": pdf_link + links, "{{DISCLAIMER}}": c["disclaimer"]}.items():
        s = s.replace(k, v)
    (p.dir / "index.html").write_text(s)
    print(f"cues.json：{len(cues)} 句、{len(scenes)} 幕、{len(pages)} 頁；播放頁 index.html")
    print(f"本機預覽：python3 {Path(__file__)} serve '{p.dir}' 8790  → http://localhost:8790/")


def cmd_publish(p, artifact=False):
    c = p.cfg
    out = p.dir / "publish"
    if out.exists():
        shutil.rmtree(out)
    (out / "video").mkdir(parents=True)
    run([tool("ffmpeg"), "-loglevel", "error", "-y", "-i", str(p.vid / "video.mp4"),
         "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "30",
         "-tune", "stillimage", "-g", "600", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "48k", "-ac", "1", "-movflags", "+faststart", str(out / "video/video.mp4")])
    shutil.copyfile(p.vid / "subtitles.vtt", out / "video/subtitles.vtt.txt")   # 有些平台不收 .vtt
    shutil.copytree(p.data, out / "data", ignore=shutil.ignore_patterns("anchors.json"))
    shutil.copytree(p.dir / "pdf", out / "pdf")
    if c["publish"]["include_pdf"]:
        (out / Path(c["pdf"]).parent).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p.pdf, out / c["pdf"])
    s = (p.dir / "index.html").read_text()
    s = s.replace('<track kind="captions" srclang="zh-Hant" label="中文字幕" src="video/subtitles.vtt">',
                  '<track kind="captions" srclang="zh-Hant" label="中文字幕" id="trk">')
    s = s.replace("/*VTT_BLOB*/", "fetch('video/subtitles.vtt.txt').then((r) => r.text()).then((t) => {"
                  " document.getElementById('trk').src = URL.createObjectURL(new Blob([t], { type: 'text/vtt' })); }).catch(() => {});")
    if artifact:   # claude.ai Artifact 會自己包 <!DOCTYPE>/<html>/<head>/<body>，這裡拿掉
        s = re.sub(r"<!DOCTYPE html>\s*<html[^>]*>\s*<head>\s*", "", s)
        s = re.sub(r'<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*', "", s)
        s = s.replace("</head>\n<body>\n", "\n").replace("</body>\n</html>", "")
        s = s.replace("height:100dvh", "height:100%").replace("max-height:28dvh", "max-height:28vh")
    (out / "index.html").write_text(s)
    files = [f for f in out.rglob("*") if f.is_file()]
    big = [f.relative_to(out) for f in files if f.stat().st_size > c["publish"]["max_mb"] * 2**20]
    if big:
        die(f"超過 {c['publish']['max_mb']} MB：{big}")
    print(f"publish/：{len(files)} 個檔、{sum(f.stat().st_size for f in files) / 2**20:.1f} MB")
    if not c["license"]:
        print("⚠ paper.json 沒填 license。非開放授權的論文不要公開 PDF 頁面圖。")


# ───────────────────────────── serve（支援 Range，影片才能拖曳跳轉）
def cmd_serve(p, port="8790"):
    import http.server
    import functools

    class H(http.server.SimpleHTTPRequestHandler):
        def send_head(self):
            rng = self.headers.get("Range")
            path = self.translate_path(self.path)
            if not rng or not os.path.isfile(path):
                return super().send_head()
            size = os.path.getsize(path)
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            a = int(m.group(1)) if m and m.group(1) else 0
            b = int(m.group(2)) if m and m.group(2) else size - 1
            b = min(b, size - 1)
            f = open(path, "rb")
            f.seek(a)
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(path))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {a}-{b}/{size}")
            self.send_header("Content-Length", str(b - a + 1))
            self.end_headers()
            self.range_left = b - a + 1
            return f

        def copyfile(self, src, dst):
            left = getattr(self, "range_left", None)
            if left is None:
                return super().copyfile(src, dst)
            while left > 0:
                buf = src.read(min(65536, left))
                if not buf:
                    break
                dst.write(buf)
                left -= len(buf)

    h = functools.partial(H, directory=str(p.dir))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", int(port)), h)
    print(f"http://localhost:{port}/   （Ctrl-C 結束）")
    srv.serve_forever()


# ───────────────────────────── main
def main():
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = a[0]
    if cmd == "doctor":
        return cmd_doctor()
    if cmd == "init":
        if len(a) < 2:
            die("用法：pe.py init <專案> [--pdf 論文.pdf] [--force]")
        pdf = a[a.index("--pdf") + 1] if "--pdf" in a else None
        return cmd_init(a[1], pdf, "--force" in a)
    if len(a) < 2:
        die("請給專案資料夾")
    p = Proj(a[1])
    rest = a[2:]
    steps = {"text": cmd_text, "anchors": cmd_anchors, "slides": cmd_slides, "export": cmd_export,
             "check-voice": cmd_check_voice, "video": cmd_video, "pages": cmd_pages, "page": cmd_page,
             "publish": cmd_publish}
    if cmd == "crop":
        return cmd_crop(p, *rest)
    if cmd == "check":
        scenes, sts = p.states()
        return print(f"講稿 OK：{len(scenes)} 幕、{len(sts)} 句（下一步 anchors 會檢查引句對不對得到原文）")
    if cmd == "serve":
        return cmd_serve(p, *rest)
    if cmd == "voice":
        return cmd_voice(p, {int(x) for x in rest} or None)
    if cmd == "all":
        for f in (cmd_anchors, cmd_slides, cmd_voice, cmd_video, cmd_pages, cmd_page):
            f(p)
        return
    if cmd == "publish":
        return cmd_publish(p, "--artifact" in rest)
    if cmd not in steps:
        die(f"未知指令 {cmd}")
    steps[cmd](p)


if __name__ == "__main__":
    main()
