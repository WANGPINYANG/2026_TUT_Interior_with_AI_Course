import importlib.util, sys, os, copy, json, tempfile, html

AFTER = sys.argv[1]
OUT = sys.argv[2]
ROOT = os.path.dirname(os.path.dirname(AFTER))


def L(p, n):
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


A = L(AFTER, "after")
ET = L(os.path.join(ROOT, "tests", "ergonomics_test.py"), "et")
base = json.load(open(os.path.join(ROOT, "examples", "bedroom_check.json"), encoding="utf-8"))
tmp = tempfile.mkdtemp()
e = html.escape
CASES = []


def add(group, title, data, expect, test, mode="check", path_in_test=True):
    CASES.append(dict(group=group, title=title, data=data, expect=expect, test=test, mode=mode, path=path_in_test))


def codes(r):
    return [i["code"] for i in r["issues"]]


has = lambda r, c: c in codes(r)

# ============================================================ 稽核 12 項
G = "稽核 #1 門口封死"
def sealed(y, gap=0):
    furn = [{"type": "bookshelf", "x": 1 + i * 166, "y": y, "facing": "S", "width": 166} for i in range(3)]
    if gap:
        furn = [{"type": "bookshelf", "x": 1, "y": y, "facing": "S", "width": 200},
                {"type": "bookshelf", "x": 1 + 200 + gap, "y": y, "facing": "S", "width": 500 - 200 - gap - 2}]
    return {"room": {"name": "北牆門・書櫃牆 y=%d" % y, "width": 500, "depth": 600},
            "openings": [{"type": "door", "wall": "N", "offset": 200, "width": 90}], "furniture": furn}


blocked = lambda r: any(c in ("ENTRY_BLOCKED", "NO_ACCESS") for c in codes(r)) and r["score"] == 0.0
for y in (0, 20, 36, 40, 50, 60, 80, 100):
    add(G, "書櫃牆離北牆 %dcm，整排封死" % y, sealed(y), "判定不可用（ENTRY_BLOCKED／NO_ACCESS），總分 0", blocked)
add(G, "書櫃牆留 80cm 缺口（反例）", sealed(40, 80), "可通行，總分 > 0", lambda r: not blocked(r) and r["score"] > 0)
pocket = {"room": {"name": "只有書桌被圍住", "width": 300, "depth": 300}, "openings": [{"type": "door", "wall": "S", "offset": 100, "width": 90, "swing": "sliding"}],
          "furniture": [{"type": "desk", "x": 0, "y": 0, "facing": "S"}, {"type": "tv_cabinet", "x": 125, "y": 0, "facing": "E"}, {"type": "tv_cabinet", "x": 0, "y": 140, "facing": "S"}]}
add(G, "只有書桌被圍在角落（反例）", pocket, "報 UNREACHABLE，但不是 0 分", lambda r: has(r, "UNREACHABLE") and r["score"] > 0)
for wall in "NSEW":
    far = 30
    d = {"room": {"name": "%s牆的門被封死" % {"N": "北", "S": "南", "E": "東", "W": "西"}[wall], "width": 500, "depth": 500}, "openings": [{"type": "door", "wall": wall, "offset": 200, "width": 90}]}
    if wall == "N": d["furniture"] = [{"type": "bookshelf", "x": 1 + i * 166, "y": far, "facing": "S", "width": 166} for i in range(3)]
    elif wall == "S": d["furniture"] = [{"type": "bookshelf", "x": 1 + i * 166, "y": 500 - far - 35, "facing": "N", "width": 166} for i in range(3)]
    elif wall == "W": d["furniture"] = [{"type": "bookshelf", "x": far, "y": 1 + i * 166, "facing": "E", "width": 166} for i in range(3)]
    else: d["furniture"] = [{"type": "bookshelf", "x": 500 - far - 35, "y": 1 + i * 166, "facing": "W", "width": 166} for i in range(3)]
    add(G, "四面牆各一次：%s牆的門被封死" % {"N": "北", "S": "南", "E": "東", "W": "西"}[wall], d, "總分 0", blocked)

G = "稽核 #2 家具在房外"
def mv(x, y):
    d = copy.deepcopy(base)
    for f in d["furniture"]:
        if f["type"] == "bed_double": f["x"], f["y"] = x, y
    d["room"]["name"] = "床在 (%d,%d)" % (x, y)
    return d


add(G, "床在屋內（基準）", mv(104, 0), "可行", lambda r: r["feasible"] is True)
add(G, "床移到 (9000,9000)", mv(9000, 9000), "總分 ≤ 30，標示不可行，且不高於屋內 58.4", lambda r: r["feasible"] is False and r["score"] <= 30 and r["score"] <= 58.4)

G = "稽核 #3 樑拆段"
def beamd(beams, nm):
    return {"room": {"name": nm, "width": 360, "depth": 330}, "openings": [{"type": "door", "wall": "S", "offset": 20, "width": 90}],
            "furniture": [{"type": "bed_double", "x": 104, "y": 0, "facing": "S"}], "beams": beams}


one = [{"x": 100, "y": 20, "w": 170, "d": 30}]
two = [{"x": 100, "y": 20, "w": 85, "d": 30}, {"x": 185, "y": 20, "w": 85, "d": 30}]
bc = lambda r: codes(r).count("BEAM_OVER_HEAD")
add(G, "單根樑（基準）", beamd(one, "單根樑"), "壓床頭只報 1 次", lambda r: bc(r) == 1)
add(G, "同一根拆成兩段", beamd(two, "拆成兩段"), "合併後只報 1 次，分數同單根", lambda r: bc(r) == 1 and r["score"] == 90.4)
add(G, "同一根重複輸入", beamd([one[0], dict(one[0])], "重複輸入"), "只報 1 次", lambda r: bc(r) == 1 and r["score"] == 90.4)
add(G, "兩段重疊", beamd([{"x": 100, "y": 20, "w": 100, "d": 30}, {"x": 150, "y": 20, "w": 120, "d": 30}], "兩段重疊"), "合併後只報 1 次", lambda r: bc(r) == 1)
add(G, "兩根真的分開（反例）", beamd([{"x": 100, "y": 20, "w": 60, "d": 30}, {"x": 220, "y": 20, "w": 60, "d": 30}], "兩根分開"), "不合併，各自計算（仍有樑壓床相關問題）", lambda r: any("BEAM" in c for c in codes(r)))

G = "稽核 #4 鏡子遮擋"
def mir(blocker=None, nm=""):
    d = {"room": {"name": nm, "width": 360, "depth": 330}, "openings": [], "furniture": [
        {"type": "bed_double", "x": 104, "y": 0, "facing": "S"}, {"type": "mirror", "x": 157, "y": 320, "facing": "N"}]}
    if blocker: d["furniture"].append(blocker)
    return d


add(G, "無遮擋", mir(None, "無遮擋"), "報鏡照床", lambda r: has(r, "MIRROR_FACES_BED"))
add(G, "衣櫃完全擋住", mir({"type": "wardrobe", "x": 120, "y": 250, "facing": "N", "width": 120}, "衣櫃完全擋住"), "不報", lambda r: not has(r, "MIRROR_FACES_BED"))
add(G, "衣櫃只擋一小部分（反例）", mir({"type": "wardrobe", "x": 120, "y": 250, "facing": "N", "width": 20}, "只擋一小段"), "仍報", lambda r: has(r, "MIRROR_FACES_BED"))
add(G, "矮茶几擋住（反例）", mir({"type": "coffee_table", "x": 120, "y": 250, "facing": "N", "width": 120}, "矮家具擋住"), "仍報", lambda r: has(r, "MIRROR_FACES_BED"))
def real(block):
    d = copy.deepcopy(base)
    d["room"]["name"] = "真實房間・" + ("衣櫃擋住新鏡子" if block else "新鏡子沒擋")
    d["furniture"].append({"type": "mirror", "x": 157, "y": 320, "facing": "N"})
    if block: d["furniture"].append({"type": "wardrobe", "x": 120, "y": 250, "facing": "N", "width": 120})
    return d


add(G, "真實房間・新鏡子沒擋", real(False), "風水 38、總分 53.6", lambda r: r["fengshui"] == 38 and r["score"] == 53.6)
add(G, "真實房間・衣櫃擋住新鏡子", real(True), "風水 50、總分 58.4（不是 100）", lambda r: r["fengshui"] == 50 and r["score"] == 58.4)

G = "稽核 #6 門窗超出牆長"
def door(nm, **kw):
    o = {"type": "door", "wall": "S", "offset": 20, "width": 90}; o.update(kw)
    return {"room": {"name": nm, "width": 360, "depth": 330}, "openings": [o], "furniture": [{"type": "bed_double", "x": 104, "y": 0, "facing": "S"}]}


add(G, "offset=99999", door("offset=99999", offset=99999), "拒絕", None, "reject")
add(G, "width=99999", door("width=99999", width=99999), "拒絕", None, "reject")
add(G, "offset=-5", door("offset=-5", offset=-5), "拒絕", None, "reject")
add(G, "offset+width 恰等於牆長 360（反例）", door("恰等於牆長", offset=270, width=90), "接受", None, "accept")
add(G, "東牆的門，offset 300 + 90 > 房深 330", {"room": {"name": "東牆超出", "width": 360, "depth": 330}, "openings": [{"type": "door", "wall": "E", "offset": 300, "width": 90}], "furniture": []}, "拒絕（用房深 330 判斷）", None, "reject")

G = "稽核 #7 樑在房外"
bd = lambda nm, **k: {"room": {"name": nm, "width": 360, "depth": 330}, "beams": [dict({"x": 5000, "y": 5000, "w": 100, "d": 30}, **k)], "furniture": [{"type": "bed_double", "x": 104, "y": 0, "facing": "S"}]}
add(G, "樑完全在房間外", bd("樑完全在房外"), "拒絕", None, "reject")
add(G, "樑在左上方外面（負座標）", bd("樑在負座標", x=-500, y=-500), "拒絕", None, "reject")
add(G, "樑只有一部分在房外（牆厚，反例）", bd("樑部分在房外", x=340, y=100), "接受", None, "accept")
add(G, "樑貼著房間邊界（反例）", bd("樑貼邊界", x=0, y=0), "接受", None, "accept")

G = "稽核 #8 count 與 #12 optimize"
def opt(cnt, extra=None):
    w = {"type": "wardrobe", "count": cnt}
    if extra: w.update(extra)
    return {"room": {"name": "count=%s" % cnt, "width": 360, "depth": 330}, "items": [{"type": "bed_double"}, w]}


for cnt in (1.9, -0.5, -1, 51):
    add(G, "count=%s" % cnt, opt(cnt), "拒絕", None, "reject_opt")
for cnt in (0, 1, 2):
    add(G, "count=%s（反例）" % cnt, opt(cnt), "照常，衣櫃件數 ≤ count", (lambda c: (lambda data, r: sum(1 for f in data["furniture"] if f["type"] == "wardrobe") <= c))(cnt), "optimize")
add(G, "optimize 保留 mirror／name／clearance", opt(1, {"mirror": True, "name": "鏡門衣櫃", "clearance": 80}), "輸出的衣櫃帶 mirror=True、name、clearance=80",
    lambda data, r: any(f["type"] == "wardrobe" and f.get("mirror") is True and f.get("name") == "鏡門衣櫃" and f.get("clearance") == 80 for f in data["furniture"]), "optimize")

G = "稽核 #9 #10 #11 輸入驗證"
add(G, "床在房外：不出現「只剩 -」", mv(9000, 9000), "沒有負淨空訊息，仍有 OUT_OF_ROOM", lambda r: not any("只剩 -" in i["message"] for i in r["issues"]) and has(r, "OUT_OF_ROOM"))
d = copy.deepcopy(base); d["room"]["width"] = "360"; d["room"]["name"] = "width='360'"
add(G, "room.width 是字串 '360'", d, "拒絕", None, "reject")
d = copy.deepcopy(base); d["furniture"][0]["x"] = "104"; d["room"]["name"] = "x='104'"
add(G, "furniture.x 是字串 '104'", d, "拒絕", None, "reject")
d = copy.deepcopy(base); d["furniture"][0]["x"] = 1e308; d["room"]["name"] = "x=1e308"
add(G, "x = 1e308", d, "拒絕", None, "reject")
d = copy.deepcopy(base); d["furniture"][0]["x"] = 1000001; d["room"]["name"] = "x=1000001"
add(G, "x = 1000001（超過上限）", d, "拒絕", None, "reject")
d = copy.deepcopy(base); d["furniture"][0]["x"] = 5000; d["room"]["name"] = "x=5000"
add(G, "x = 5000（反例，由 OUT_OF_ROOM 處理）", d, "接受", None, "accept")

# ============================================================ 人體工學邊界
G = "人體工學 走道寬度"
for kind, zh in (("between", "兩件家具之間"), ("wall", "家具與牆之間")):
    for gap in (40, 45, 50, 55, 60, 70):
        d = ET.corridor_case(gap, kind); d["room"]["name"] = "%s缺口 %dcm" % (zh, gap)
        exp = "擋住（UNREACHABLE）" if gap < 50 else ("通行" if gap >= 55 else "邊界：50–54cm 因 5cm 網格，擋或過皆可接受")
        add(G, "%s %dcm" % (zh, gap), d, exp,
            (lambda g: (lambda r: has(r, "UNREACHABLE") if g < 50 else (not has(r, "UNREACHABLE") if g >= 55 else True)))(gap))

G = "人體工學 床邊走道"
for gw, ge, ex in [(100, 100, set()), (60, 0, {"BED_ONE_SIDE"}), (59, 0, {"BED_SIDE"}), (60, 44, {"BED_ONE_SIDE"}), (60, 45, set()), (59, 59, {"BED_SIDE"}), (45, 45, {"BED_SIDE"}), (44, 44, {"BED_SIDE"}), (0, 0, {"BED_SIDE"}), (0, 100, {"BED_ONE_SIDE"})]:
    d = ET.bed_case(gw, ge); d["room"]["name"] = "床兩側 %d / %d" % (gw, ge)
    add(G, "西側 %d／東側 %d" % (gw, ge), d, "報 %s" % (sorted(ex) if ex else "無床邊問題"),
        (lambda e_: (lambda r: set(c for c in codes(r) if c in ("BED_SIDE", "BED_ONE_SIDE")) == e_))(ex), path_in_test=False)

G = "人體工學 家具前方淨空"
for t in ("wardrobe", "desk", "dresser", "bookshelf", "sofa"):
    _, req = ET.front_case(t, 0)
    for gap in (0, req - 1, req, req + 40):
        d, _ = ET.front_case(t, gap); d["room"]["name"] = "%s 前方 %dcm（建議 %d）" % (t, gap, req)
        add(G, "%s 前方 %dcm（需 %d）" % (t, gap, req), d, "報 FRONT_CLEAR" if gap < req else "不報",
            (lambda rq, g: (lambda r: has(r, "FRONT_CLEAR") == (g < rq)))(req, gap), path_in_test=False)

G = "人體工學 餐桌四周"
for gap in (40, 59, 60, 75):
    d = {"room": {"name": "餐桌四周 %dcm" % gap, "width": 150 + 2 * gap, "depth": 90 + 2 * gap}, "openings": [],
         "furniture": [{"type": "dining_table", "x": gap, "y": gap, "facing": "S"}]}
    add(G, "四周各 %dcm" % gap, d, "報 DINING_CLEAR" if gap < 60 else "不報", (lambda g: (lambda r: has(r, "DINING_CLEAR") == (g < 60)))(gap), path_in_test=False)

G = "人體工學 門片開啟範圍"
for dw in (70, 90):
    for off_gap, exp in ((-1, True), (0, False), (1, False)):
        d = {"room": {"name": "門寬%d・家具距門片 %dcm" % (dw, off_gap), "width": 400, "depth": 400}, "openings": [{"type": "door", "wall": "N", "offset": 100, "width": dw}],
             "furniture": [{"type": "bookshelf", "x": 100, "y": dw + off_gap, "facing": "S", "width": 80, "depth": 35}]}
        add(G, "門寬 %d・家具距門片 %dcm" % (dw, off_gap), d, "擋到門（DOOR_BLOCKED）" if exp else "不擋", (lambda x: (lambda r: has(r, "DOOR_BLOCKED") == x))(exp), path_in_test=False)
add(G, "拉門不檢查開門範圍", {"room": {"name": "拉門", "width": 400, "depth": 400}, "openings": [{"type": "door", "wall": "N", "offset": 100, "width": 90, "swing": "sliding"}],
    "furniture": [{"type": "bookshelf", "x": 100, "y": 20, "facing": "S"}]}, "不報", lambda r: not has(r, "DOOR_BLOCKED"), path_in_test=False)

G = "人體工學 沙發與電視"
for dist in (170, 179, 180, 300, 450, 460):
    d = {"room": {"name": "沙發到電視 %dcm" % dist, "width": 400, "depth": 90 + dist + 45 + 40}, "openings": [],
         "furniture": [{"type": "sofa", "x": 95, "y": 0, "facing": "S"}, {"type": "tv_cabinet", "x": 110, "y": 90 + dist, "facing": "N"}]}
    bad = dist < 180 or dist > 450
    add(G, "距離 %dcm（建議 180–450）" % dist, d, "報 TV_DISTANCE" if bad else "不報", (lambda b: (lambda r: has(r, "TV_DISTANCE") == b))(bad), path_in_test=False)


# ============================================================ 執行與繪圖
def svg_of(lay, res, title):
    p = os.path.join(tmp, "x.svg")
    A.render_svg(lay, res, p, title)
    return open(p, encoding="utf-8").read().replace("<svg ", '<svg class="plan" ', 1)


out_cases = []
for c in CASES:
    r = {"c": c, "ok": False, "svg": None, "actual": "", "err": None}
    try:
        if c["mode"] in ("check", "accept", "reject"):
            try:
                lay = A.load_layout(c["data"])
                loaded = True
            except ValueError as ex:
                loaded, r["err"] = False, str(ex)
            if c["mode"] == "reject":
                r["ok"] = not loaded
                r["actual"] = ("拒絕：" + r["err"]) if not loaded else "接受（應該拒絕）"
                if loaded:
                    res = A.evaluate(lay); r["svg"] = svg_of(lay, res, c["data"]["room"].get("name", ""))
            else:
                if not loaded:
                    r["ok"], r["actual"] = False, "被拒絕：" + r["err"]
                else:
                    res = A.evaluate(lay); r["svg"] = svg_of(lay, res, c["data"]["room"].get("name", ""))
                    res_t = res if c["path"] else A.evaluate(lay, with_path=False)
                    r["ok"] = True if c["mode"] == "accept" else bool(c["test"](res_t))
                    r["actual"] = "總分 %.1f｜%s" % (res["score"], "、".join(sorted(set(codes(res)))) or "無問題")
        elif c["mode"] == "reject_opt":
            try:
                A.optimize(copy.deepcopy(c["data"]), top=1, seed=1, iters=50)
                r["ok"], r["actual"] = False, "接受（應該拒絕）"
            except ValueError as ex:
                r["ok"], r["actual"] = True, "拒絕：" + str(ex)
        else:  # optimize
            ch = A.optimize(copy.deepcopy(c["data"]), top=1, seed=1, iters=100)
            data, res = ch[0]
            lay = A.load_layout(data)
            r["svg"] = svg_of(lay, res, c["data"]["room"].get("name", "") + "（optimize 第 1 方案）")
            r["ok"] = bool(c["test"](data, res))
            r["actual"] = "總分 %.1f｜家具：%s" % (res["score"], "、".join(f["type"] for f in data["furniture"]))
    except Exception as ex:
        r["ok"], r["actual"] = False, "測試程式例外：%r" % ex
    out_cases.append(r)

CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1e2430;--mute:#6a7280;--line:#e3e1da;--good:#2f9e6b;--goodbg:#e4f4ec;--bad:#d64545;--badbg:#fbe9e9;--accent:#3a6ea5}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1d2128;--ink:#e8ebf0;--mute:#98a1b0;--line:#2c323c;--good:#4cc38a;--goodbg:#173026;--bad:#ff7070;--badbg:#3a1f1f;--accent:#7fb0e6}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft JhengHei","Noto Sans TC",system-ui,sans-serif;line-height:1.5}
main{max-width:1280px;margin:0 auto;padding:22px 16px 60px}h1{font-size:24px;margin:0 0 4px}.sub{color:var(--mute);font-size:14px}
.bar{position:sticky;top:0;background:var(--bg);padding:10px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center;z-index:5;border-bottom:1px solid var(--line)}
.bar button{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:99px;padding:5px 14px;font:inherit;font-size:13px;cursor:pointer}.bar button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.sum{font-weight:700}.sum .g{color:var(--good)}.sum .b{color:var(--bad)}
h2{font-size:18px;margin:26px 0 8px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:12px}
.cs{background:var(--card);border:2px solid var(--line);border-radius:10px;padding:8px;display:flex;flex-direction:column}.cs.pass{border-color:var(--good)}.cs.fail{border-color:var(--bad)}
.cs h4{margin:0 0 2px;font-size:13px;display:flex;gap:6px;align-items:flex-start}.mk{font-weight:700;border-radius:99px;padding:0 8px;font-size:12px;white-space:nowrap}.pass .mk{background:var(--goodbg);color:var(--good)}.fail .mk{background:var(--badbg);color:var(--bad)}
.ex,.ac{font-size:12px;margin:2px 0}.ex{color:var(--mute)}.plan{width:100%;height:auto;background:#fff;border-radius:6px;margin:4px 0}.rej{padding:26px 8px;text-align:center;background:var(--badbg);color:var(--bad);border-radius:6px;font-size:12px;margin:4px 0;word-break:break-all}.rej.okk{background:var(--goodbg);color:var(--good)}
.hide{display:none}
"""
passn = sum(1 for r in out_cases if r["ok"])
groups = []
for r in out_cases:
    if not groups or groups[-1][0] != r["c"]["group"]:
        groups.append((r["c"]["group"], []))
    groups[-1][1].append(r)
h = ['<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>全案例查驗圖庫</title><style>%s</style></head><body><main>' % CSS,
     '<h1>全案例查驗圖庫</h1><div class="sub">每個測試案例一張平面圖（被拒絕的輸入畫成說明卡）。綠框＝實際結果符合期望，紅框＝不符。圖下方列出「期望」與「實際」，可核對。</div>',
     '<div class="bar"><span class="sum">共 %d 案例：<span class="g">%d 通過</span>、<span class="b">%d 失敗</span></span>'
     '<button class="on" data-f="all">全部</button><button data-f="pass">只看通過</button><button data-f="fail">只看失敗</button></div>' % (len(out_cases), passn, len(out_cases) - passn)]
for g, rs in groups:
    gp = sum(1 for r in rs if r["ok"])
    h.append('<h2>%s <span class="sub">（%d/%d 通過）</span></h2><div class="grid">' % (e(g), gp, len(rs)))
    for r in rs:
        c = r["c"]
        body = r["svg"] if r["svg"] else '<div class="rej okk">%s</div>' % e(r["actual"]) if r["ok"] else '<div class="rej">%s</div>' % e(r["actual"])
        h.append('<div class="cs %s" data-s="%s"><h4><span class="mk">%s</span>%s</h4><div class="ex">期望：%s</div>%s<div class="ac">實際：%s</div></div>' % (
            "pass" if r["ok"] else "fail", "pass" if r["ok"] else "fail", "✔ 通過" if r["ok"] else "✘ 失敗", e(c["title"]), e(c["expect"]), body, e(r["actual"])))
    h.append("</div>")
h.append('<script>document.querySelectorAll(".bar button").forEach(function(b){b.onclick=function(){document.querySelectorAll(".bar button").forEach(function(x){x.classList.remove("on")});b.classList.add("on");var f=b.dataset.f;document.querySelectorAll(".cs").forEach(function(c){c.classList.toggle("hide",f!=="all"&&c.dataset.s!==f)})}})</script></main></body></html>')
open(OUT, "w", encoding="utf-8").write("".join(h))
print("案例 %d，通過 %d，失敗 %d → %s" % (len(out_cases), passn, len(out_cases) - passn, OUT))
for r in out_cases:
    if not r["ok"]:
        print("  ✘", r["c"]["group"], "|", r["c"]["title"], "|", r["actual"][:90])
