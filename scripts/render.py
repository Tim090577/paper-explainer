"""投影片 HTML：一句旁白＝一個狀態，元素逐句浮現。版面元素的寫法見 references/script-format.md。"""

import html
from pathlib import Path

TONES = {
    "red": ("#b4372b", "#fbeae6"), "blue": ("#245c9c", "#e7eef8"), "amber": ("#a36a00", "#fbf1dc"),
    "green": ("#2d7a4f", "#e3f2e9"), "gray": ("#5d6470", "#eef0f2"), "ink": ("#1f2a3c", "#ffffff"),
}

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:1920px;height:1080px;overflow:hidden;background:#f6f2ea;color:#1f2a3c;
 font-family:'PingFang TC','Noto Sans TC','Heiti TC','Microsoft JhengHei','Helvetica Neue',sans-serif;position:relative}
body:before{content:"";position:absolute;inset:0;background:
 radial-gradient(1200px 600px at 100% 0%,rgba(180,55,43,.07),transparent 60%),
 radial-gradient(900px 600px at 0% 100%,rgba(36,92,156,.06),transparent 60%)}
.head{position:absolute;left:80px;right:80px;top:56px;display:flex;justify-content:space-between;align-items:flex-start;gap:40px}
.kick{font-size:28px;letter-spacing:.06em;color:#8a7f6e;font-weight:600}
h1{font-size:64px;font-weight:700;line-height:1.15;margin-top:8px;letter-spacing:.01em}
h1 small{display:block;font-size:32px;font-weight:500;color:#5d6470;margin-top:10px;font-style:italic}
.meta{text-align:right;font-size:24px;color:#8a7f6e;line-height:1.6;white-space:nowrap}
.meta b{font-size:40px;color:#1f2a3c;font-weight:700;font-variant-numeric:tabular-nums}
.meta .pg{display:inline-block;margin-top:6px;padding:4px 14px;border-radius:999px;background:#1f2a3c;color:#f6f2ea;font-size:24px}
.stage{position:absolute;left:80px;right:80px;top:250px;bottom:150px;display:flex;flex-direction:column;justify-content:center;gap:26px}
.stage.tall{top:236px;bottom:120px}
.row{display:flex;gap:26px;align-items:stretch}
.hid{opacity:0}
.card{background:var(--bg);border:2px solid #e3dccf;border-left:12px solid var(--c);border-radius:18px;padding:24px 32px;flex:var(--w) 1 0;min-width:0}
.card h3{font-size:40px;font-weight:700;color:var(--c);line-height:1.25}
.card p{font-size:32px;line-height:1.45;margin-top:8px;color:#26303f}
.card p b,.note b{color:var(--c)}
.focus{box-shadow:0 0 0 4px var(--c),0 18px 40px rgba(31,42,60,.18);border-color:var(--c)}
.stat{flex:var(--w) 1 0;text-align:center;background:#fff;border:2px solid #e3dccf;border-radius:18px;padding:26px 18px;display:flex;flex-direction:column;justify-content:center}
.stat .n{font-size:100px;font-weight:800;color:var(--c);line-height:1;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.stat .l{font-size:32px;line-height:1.35;margin-top:14px;color:#3a4352}
.chip{flex:1 1 0;white-space:nowrap;text-align:center;font-size:50px;font-weight:800;color:var(--c);background:var(--bg);border:3px solid var(--c);border-radius:999px;padding:22px 10px}
.arrow{flex:0 0 auto;align-self:center;font-size:64px;color:#9a8f7c;font-weight:700}
.note{flex:1 1 0;background:#fff6dd;border:2px dashed #c99a2e;border-radius:18px;padding:22px 30px;font-size:34px;line-height:1.45;color:#5a3d00;display:flex;align-items:center;gap:18px}
.note:before{content:"⚠";font-size:48px}
.group{flex:var(--w) 1 0;background:#fff;border:2px solid #e3dccf;border-radius:18px;padding:24px 34px;display:flex;flex-direction:column;gap:18px;justify-content:center}
.group>h4{font-size:34px;color:#5d6470;font-weight:700}
.stack{flex:var(--w) 1 0;display:flex;flex-direction:column;gap:20px;min-width:0}
.stack>.card{flex:1 1 auto}
.bar{display:flex;align-items:center;gap:24px;border-radius:12px;padding:4px 8px}
.bar .l{width:300px;font-size:34px;font-weight:600}
.bar .tr{flex:1;height:46px;background:#efe9de;border-radius:10px;overflow:hidden}
.bar .f{height:100%;background:var(--c);border-radius:10px}
.bar .v{width:220px;font-size:40px;font-weight:800;color:var(--c);text-align:right;font-variant-numeric:tabular-nums}
.pts{display:flex;align-items:center;gap:22px;border-radius:12px;padding:4px 8px}
.pts .l{width:470px;font-size:34px;font-weight:600}
.pts .bx{display:flex;gap:8px;flex:1}
.pts .bx i{width:46px;height:46px;border-radius:8px;background:var(--c)}
.pts .bx i.o{background:transparent;border:3px dashed #d8cfbf}
.pts .v{width:120px;font-size:40px;font-weight:800;color:var(--c);text-align:right}
.bar.focus,.pts.focus{background:var(--bg)}
.quiz{flex:1 1 0;background:#fff;border:2px solid #e3dccf;border-radius:18px;padding:24px 30px;display:grid;grid-template-columns:1fr 132px;gap:6px 24px;align-items:center}
.quiz .src{grid-column:1/3;font-size:28px;color:#8a7f6e;font-weight:600}
.quiz .stem{font-size:36px;font-weight:700;line-height:1.35}
.quiz .ans{grid-row:2/4;grid-column:2;width:132px;height:132px;border-radius:50%;background:#b4372b;color:#fff;font-size:60px;font-weight:800;display:flex;align-items:center;justify-content:center}
.quiz .why{font-size:31px;line-height:1.45;color:#26303f}
.quiz .why b{color:#b4372b}
.quiz.focus{box-shadow:0 0 0 4px #b4372b,0 18px 40px rgba(31,42,60,.18)}
.fig{flex:var(--w) 1 0;min-width:0;background:#fff;border:2px solid #e3dccf;border-radius:18px;padding:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px}
.fig img{max-width:100%;max-height:520px;object-fit:contain}
.fig figcaption{font-size:24px;color:#6b6457}
.svg{flex:var(--w) 1 0;display:flex;align-items:center;justify-content:center}
.svg svg{width:100%;height:auto;max-height:420px}
"""


def tone_vars(t, w=1):
    c, bg = TONES.get(t, TONES["ink"])
    return f'style="--c:{c};--bg:{bg};--w:{w}"'


def render_el(el, vis, foc, proj):
    k, i = el["k"], el.get("id", "")
    shown = i in vis
    cls = ("" if shown else " hid") + (" focus" if i in foc else "")
    if k == "card":
        body = f"<p>{el['b']}</p>" if el.get("b") else ""
        return f'<div class="card{cls}" {tone_vars(el.get("tone", "ink"), el.get("w", 1))}><h3>{el["h"]}</h3>{body}</div>'
    if k == "stat":
        return (f'<div class="stat{cls}" {tone_vars(el.get("tone", "red"), el.get("w", 1))}><div class="n">{el["n"]}</div>'
                f'<div class="l">{el["l"]}</div></div>')
    if k == "chip":
        return f'<div class="chip{cls}" {tone_vars(el.get("tone", "blue"))}>{el["t"]}</div>'
    if k == "arrow":
        return f'<div class="arrow{cls}">{el.get("t", "→")}</div>'
    if k == "note":
        return f'<div class="note{cls}" {tone_vars(el.get("tone", "amber"))}>{el["t"]}</div>'
    if k == "bar":
        return (f'<div class="bar{cls}" {tone_vars(el.get("tone", "blue"))}><div class="l">{el["l"]}</div>'
                f'<div class="tr"><div class="f" style="width:{el["v"] * 100:.1f}%"></div></div>'
                f'<div class="v">{el["t"]}</div></div>')
    if k == "pts":
        mx = el.get("max", 8)
        bx = "<i></i>" * el["n"] + '<i class="o"></i>' * (mx - el["n"])
        return (f'<div class="pts{cls}" {tone_vars(el.get("tone", "blue"))}><div class="l">{el["l"]}</div>'
                f'<div class="bx">{bx}</div><div class="v">{el["n"]} 分</div></div>')
    if k == "quiz":
        return (f'<div class="quiz{cls}"><div class="src">{el["src"]}</div><div class="stem">{el["stem"]}</div>'
                f'<div class="ans">{el["ans"]}</div><div class="why">{el["why"]}</div></div>')
    if k == "img":
        src = (Path(proj) / el["src"]).resolve().as_uri()
        cap = f'<figcaption>{el["cap"]}</figcaption>' if el.get("cap") else ""
        return f'<figure class="fig{cls}" style="--w:{el.get("w", 1)}"><img src="{src}">{cap}</figure>'
    if k == "svg":
        return f'<div class="svg{cls}" style="--w:{el.get("w", 1)}">{el["svg"]}</div>'
    if k in ("group", "stack"):
        kids = el["els"]
        any_shown = shown or any(c.get("id") in vis for c in kids)
        inner = "".join(render_el(c, vis, foc, proj) for c in kids)
        if k == "group":
            hcls = "" if any_shown else " hid"
            return f'<div class="group{hcls}" style="--w:{el.get("w", 1)}"><h4>{el["h"]}</h4>{inner}</div>'
        return f'<div class="stack" style="--w:{el.get("w", 1)}">{inner}</div>'
    raise ValueError(f"未知的元素類型：{k}")


def slide_html(scene, st, anchors, total_scenes, cite, proj):
    vis, foc = set(st["visible"]), set(st["focus"])
    rows = "".join(f'<div class="row">{"".join(render_el(e, vis, foc, proj) for e in r)}</div>' for r in scene["rows"])
    pages = sorted({a["page"] for a in anchors})
    pg = ("原文 p." + "–".join(str(p) for p in ([pages[0], pages[-1]] if len(pages) > 1 else pages))) if pages else ""
    sub = f"<small>{scene['sub']}</small>" if scene.get("sub") else ""
    tall = " tall" if len(scene["rows"]) >= 3 else ""
    pgspan = f'<br><span class="pg">{pg}</span>' if pg else ""
    return f"""<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div class="head"><div><div class="kick">{html.escape(scene.get('kick', ''))}</div><h1>{scene['title']}{sub}</h1></div>
<div class="meta"><b>{st['scene'] + 1:02d}</b> / {total_scenes}<br>{html.escape(cite)}{pgspan}</div></div>
<div class="stage{tall}">{rows}</div></body></html>"""
