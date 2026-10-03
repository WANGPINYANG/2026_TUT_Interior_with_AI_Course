#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
跑完所有測試，產生可用瀏覽器開啟的圖示化報告 tests/report.html

用法：python tests/make_report.py [--n 800] [--seed 1] [--open]
"""
import argparse
import contextlib
import html
import importlib.util
import io
import os
import random
import sys
import tempfile
import time
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ET = load("ergonomics_test")
FZ = load("fuzz_layout")
e = html.escape


# ------------------------------------------------------------ 跑人體工學測試，逐項記錄
def run_ergonomics():
    rows = []          # (section, name, ok, detail)
    cur = {"title": ""}

    def rec_check(name, ok, detail=""):
        rows.append((cur["title"], name, bool(ok), detail))
        return ok
    ET.check = rec_check
    sections = []
    for fn in (ET.test_corridor, ET.test_bed, ET.test_front, ET.test_dining,
               ET.test_door_swing, ET.test_tv, ET.test_reach_targets):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cur["title"] = fn.__name__
            first = len(rows)
            fn()
        title = next((ln.strip() for ln in buf.getvalue().splitlines() if ln.strip().startswith("[")), fn.__name__)
        rows[:] = [(title if s == fn.__name__ else s, n, ok, d) for s, n, ok, d in rows]
        sections.append(title)
    return sections, rows


# ------------------------------------------------------------ 圖：走道門檻掃描條
def sweep(kind):
    res = []
    for gap in range(30, 91):
        res.append((gap, "UNREACHABLE" in ET.codes(ET.corridor_case(gap, kind))))
    return res


def strip_svg(res, title):
    x0, cw, h = 10, 9, 34
    W = x0 + cw * len(res) + 20
    out = ['<svg viewBox="0 0 {} 118" class="strip" role="img" aria-label="{}">'.format(W, e(title))]
    out.append('<text x="0" y="14" class="lbl">{}</text>'.format(e(title)))
    thr = next((g for g, blocked in res if not blocked), None)
    for i, (gap, blocked) in enumerate(res):
        out.append('<rect x="{}" y="22" width="{}" height="{}" class="{}"/>'.format(
            x0 + i * cw, cw, h, "bad" if blocked else "good"))
    for g in (30, 40, 50, 60, 70, 80, 90):
        x = x0 + (g - 30) * cw
        out.append('<text x="{}" y="80" class="tick" text-anchor="middle">{}</text>'.format(x + cw / 2, g))
    sx = x0 + (50 - 30) * cw
    out.append('<line x1="{0}" x2="{0}" y1="18" y2="64" class="ref"/><text x="{0}" y="94" class="refl" text-anchor="middle">規範 50cm</text>'.format(sx))
    if thr is not None:
        tx = x0 + (thr - 30) * cw
        out.append('<path d="M{0},66 l-5,8 h10z" class="mk"/><text x="{0}" y="110" class="mkl" text-anchor="middle">實測 {1}cm 起通過</text>'.format(tx, thr))
    out.append("</svg>")
    return "".join(out)


def plan_svg(d, title):
    L = ET.lay.load_layout(d)
    r = ET.lay.evaluate(L)
    p = os.path.join(tempfile.gettempdir(), "_rep.svg")
    ET.lay.render_svg(L, r, p, title)
    s = open(p, encoding="utf-8").read()
    return s.replace("<svg ", '<svg class="plan" ', 1)


# ------------------------------------------------------------ 暴力測試
def run_fuzz(n, seed):
    rng = random.Random(seed)
    tmp = tempfile.mkdtemp(prefix="rep_")
    groups = [("A 壞資料", "欄位被刪除或改成 None／字串／NaN／負數", n, lambda: FZ.test_bad_data(rng, n, os.path.join(tmp, "t.svg"))),
              ("B 性質", "分數範圍、可重現、與暴力算法比對", n, lambda: FZ.test_properties(rng, n)),
              ("C 對稱", "左右、上下鏡射後問題清單應一致", n // 2 * 2, lambda: FZ.test_symmetry(rng, n // 2)),
              ("D optimize", "最佳化結果重新檢查、種子可重現", 25, lambda: FZ.test_optimize(rng, 25)),
              ("D CLI", "BOM、壞 JSON、超大／極小房間、無效參數", 30, lambda: FZ.test_cli(tmp))]
    out = []
    for key, desc, cases, fn in groups:
        before = {k for k in FZ.BUGS if k[0] == key}
        t = time.time()
        fn()
        bugs = [(k[1], v) for k, v in FZ.BUGS.items() if k[0] == key]
        out.append({"key": key, "desc": desc, "cases": cases, "sec": time.time() - t, "bugs": bugs})
        print("  [{}] {} 案例，{} 種問題".format(key, cases, len(bugs)), flush=True)
    return out


# ------------------------------------------------------------ HTML
CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1e2430;--mute:#6a7280;--line:#e3e1da;--good:#2f9e6b;--goodbg:#e4f4ec;
--bad:#d64545;--badbg:#fbe9e9;--accent:#3a6ea5}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--ink:#e8ebf0;--mute:#98a1b0;--line:#2c323c;
--good:#4cc38a;--goodbg:#173026;--bad:#ff7070;--badbg:#3a1f1f;--accent:#7fb0e6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font-family:"Microsoft JhengHei","PingFang TC","Noto Sans TC",system-ui,sans-serif;line-height:1.55}
main{max-width:960px;margin:0 auto;padding:28px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:19px;margin:36px 0 12px}
.sub{color:var(--mute);font-size:14px}
.hero{display:flex;gap:14px;flex-wrap:wrap;margin:20px 0 4px}
.tile{flex:1 1 150px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.tile b{display:block;font-size:30px;line-height:1.1}.tile span{color:var(--mute);font-size:13px}
.tile.good b{color:var(--good)}.tile.bad b{color:var(--bad)}
.verdict{display:inline-block;padding:4px 14px;border-radius:99px;font-weight:700;font-size:14px}
.verdict.good{background:var(--goodbg);color:var(--good)}.verdict.bad{background:var(--badbg);color:var(--bad)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:12px 0}
.card h3{margin:0 0 4px;font-size:16px;display:flex;justify-content:space-between;gap:8px;align-items:center}
.card p{margin:2px 0 10px;color:var(--mute);font-size:13px}
.pill{font-size:12px;padding:2px 10px;border-radius:99px;font-weight:700;white-space:nowrap}
.pill.good{background:var(--goodbg);color:var(--good)}.pill.bad{background:var(--badbg);color:var(--bad)}
.bar{height:8px;background:var(--badbg);border-radius:4px;overflow:hidden;margin:6px 0 10px}
.bar i{display:block;height:100%;background:var(--good)}
.grid{display:flex;flex-wrap:wrap;gap:5px}
.dot{width:14px;height:14px;border-radius:3px;background:var(--good)}.dot.bad{background:var(--bad)}
details{margin-top:8px}summary{cursor:pointer;color:var(--accent);font-size:13px}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:6px}
td,th{border-bottom:1px solid var(--line);padding:5px 8px;text-align:left}td.ok{color:var(--good)}td.no{color:var(--bad);font-weight:700}
.strip{width:100%;height:auto;max-width:720px;display:block}
.strip .good{fill:var(--good)}.strip .bad{fill:var(--bad)}
.strip text{fill:var(--ink);font-family:inherit}.strip .tick{font-size:10px;fill:var(--mute)}.strip .lbl{font-size:13px;font-weight:700}
.strip .ref{stroke:var(--ink);stroke-width:2;stroke-dasharray:4 3}.strip .refl{font-size:11px}
.strip .mk{fill:var(--accent)}.strip .mkl{font-size:11px;fill:var(--accent);font-weight:700}
.plans{display:flex;gap:14px;flex-wrap:wrap}.plans figure{margin:0;flex:1 1 300px}
.plans figcaption{font-size:13px;color:var(--mute);margin-bottom:4px}
.plan{width:100%;height:auto;background:#fff;border-radius:8px;border:1px solid var(--line)}
code,pre{font-family:ui-monospace,Consolas,monospace;font-size:12px}pre{white-space:pre-wrap;word-break:break-all;background:var(--bg);padding:8px;border-radius:6px}
.legend{font-size:12px;color:var(--mute);margin-top:6px}.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;vertical-align:middle;margin:0 4px 0 10px}
"""


def render(sections, rows, fuzz, sweeps, plans, seed, n, secs):
    ok_e = sum(1 for r in rows if r[2])
    bad_e = len(rows) - ok_e
    bugs = sum(len(g["bugs"]) for g in fuzz)
    cases = sum(g["cases"] for g in fuzz)
    allgood = bad_e == 0 and bugs == 0
    h = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">',
         '<meta name="viewport" content="width=device-width,initial-scale=1">',
         '<title>測試報告</title><style>{}</style></head><body><main>'.format(CSS)]
    h.append('<h1>家具配置 Skill 測試報告</h1><div class="sub">{} ｜ 隨機種子 {} ｜ 耗時 {:.0f} 秒</div>'.format(
        time.strftime("%Y-%m-%d %H:%M"), seed, secs))
    h.append('<p><span class="verdict {}">{}</span></p>'.format(
        "good" if allgood else "bad", "全部通過" if allgood else "有項目未通過"))
    h.append('<div class="hero">'
             '<div class="tile {g1}"><b>{a}/{b}</b><span>人體工學規則檢查通過</span></div>'
             '<div class="tile {g2}"><b>{c}</b><span>暴力測試發現的問題（{d} 個隨機案例）</span></div></div>'.format(
                 g1="good" if bad_e == 0 else "bad", a=ok_e, b=len(rows),
                 g2="good" if bugs == 0 else "bad", c=bugs, d=cases))

    # ---- 人體工學
    h.append('<h2>一、人體工學規則驗證</h2><div class="sub">以 ergonomics.md 的規範當標準答案，在門檻上逐一測試，並轉 0°／90°／180°／270° 四個方向。</div>')
    h.append('<div class="card"><h3>走道寬度掃描（規範最低 50cm）</h3>'
             '<p>把缺口從 30cm 逐公分加寬到 90cm：紅色＝判定走不過去，綠色＝判定走得過去。</p>')
    h.append(strip_svg(sweeps["between"], "兩件家具之間"))
    h.append(strip_svg(sweeps["wall"], "家具與牆之間"))
    h.append('<div class="legend"><i style="background:var(--bad)"></i>走不過<i style="background:var(--good)"></i>走得過</div>')
    h.append('<div class="plans" style="margin-top:12px">')
    for cap, svg in plans:
        h.append("<figure><figcaption>{}</figcaption>{}</figure>".format(e(cap), svg))
    h.append("</div></div>")
    for sec in sections:
        rs = [r for r in rows if r[0] == sec]
        okc = sum(1 for r in rs if r[2])
        good = okc == len(rs)
        h.append('<div class="card"><h3>{}<span class="pill {}">{}/{}</span></h3>'.format(
            e(sec), "good" if good else "bad", okc, len(rs)))
        h.append('<div class="bar"><i style="width:{:.0f}%"></i></div><div class="grid">'.format(100.0 * okc / max(1, len(rs))))
        for _, name, ok, detail in rs:
            h.append('<span class="dot {}" title="{}"></span>'.format("" if ok else "bad", e(name + (" ｜ " + detail if detail else ""))))
        h.append("</div>")
        shown = [r for r in rs if not r[2]]
        h.append("<details{}><summary>{}</summary><table><tr><th></th><th>檢查項目</th><th>說明</th></tr>".format(
            " open" if shown else "", "未通過項目" if shown else "展開全部 {} 項".format(len(rs))))
        for _, name, ok, detail in (shown or rs):
            h.append('<tr><td class="{}">{}</td><td>{}</td><td>{}</td></tr>'.format("ok" if ok else "no", "✔" if ok else "✘", e(name), e(detail)))
        h.append("</table></details></div>")

    # ---- 暴力測試
    h.append('<h2>二、暴力測試（Fuzz）</h2><div class="sub">隨機產生大量合法與刻意破壞的輸入，找出崩潰、不一致或與獨立算法不符的地方。</div>')
    for g in fuzz:
        good = not g["bugs"]
        h.append('<div class="card"><h3>{}<span class="pill {}">{}</span></h3><p>{}｜{} 個案例｜{:.1f} 秒</p>'.format(
            e(g["key"]), "good" if good else "bad", "0 個問題" if good else "{} 種問題".format(len(g["bugs"])), e(g["desc"]), g["cases"], g["sec"]))
        for title, b in g["bugs"]:
            h.append("<details open><summary>{}（{} 次）</summary><pre>{}</pre><pre>{}</pre></details>".format(
                e(title), b["count"], e(b["msg"][:400]), e((b["repro"] or "")[:1500])))
        h.append("</div>")
    h.append('<div class="sub" style="margin-top:28px">限制：暴力測試證明「試過的案例沒壞」，不代表完全沒有問題；風水規則本身的對錯不在測試範圍。</div>')
    h.append("</main></body></html>")
    return "".join(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=800)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", default=os.path.join(HERE, "report.html"))
    ap.add_argument("--open", action="store_true")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    t0 = time.time()
    print("人體工學驗證…", flush=True)
    sections, rows = run_ergonomics()
    sweeps = {k: sweep(k) for k in ("between", "wall")}
    plans = [("兩件家具之間 缺口 45cm（應被擋住）", plan_svg(ET.corridor_case(45, "between"), "缺口 45cm")),
             ("兩件家具之間 缺口 60cm（應可通行）", plan_svg(ET.corridor_case(60, "between"), "缺口 60cm"))]
    print("暴力測試…", flush=True)
    fuzz = run_fuzz(a.n, a.seed)
    page = render(sections, rows, fuzz, sweeps, plans, a.seed, a.n, time.time() - t0)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("報告：{}".format(a.out))
    if a.open:
        webbrowser.open("file:///" + a.out.replace("\\", "/"))


if __name__ == "__main__":
    main()
