#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交叉稽核回歸測試：黃建升稽核報告 11 項 + 1 項未驗證，每項都用他的原始壞輸入重現，
修好後必須消失；每項另有「不能修過頭」的反例（合法輸入不該被誤擋）。

用法：python tests/audit_regression_test.py
"""
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT = os.path.abspath(os.path.join(HERE, "..", "scripts", "layout.py"))
EXAMPLES = os.path.abspath(os.path.join(HERE, "..", "examples"))
spec_ = importlib.util.spec_from_file_location("layout", LAYOUT)
lay = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(lay)

FAILS = []
COUNT = [0]


def check(name, ok, detail=""):
    COUNT[0] += 1
    print("  {} {}{}".format("✔" if ok else "✘", name, "" if ok else "　" + detail))
    if not ok:
        FAILS.append(name)


def ev(d):
    return lay.evaluate(lay.load_layout(d))


def rejects(d):
    try:
        lay.load_layout(d)
        return False
    except ValueError:
        return True


def codes(r):
    return [i["code"] for i in r["issues"]]


base = json.load(open(os.path.join(EXAMPLES, "bedroom_check.json"), encoding="utf-8"))


# ---------------------------------------------------------------- #1 門口被封死
def sealed(y, gap=0):
    furn = [{"type": "bookshelf", "x": 1 + i * 166, "y": y, "facing": "S", "width": 166} for i in range(3)]
    if gap:   # 在中間留一個缺口
        furn = [{"type": "bookshelf", "x": 1, "y": y, "facing": "S", "width": 200},
                {"type": "bookshelf", "x": 1 + 200 + gap, "y": y, "facing": "S", "width": 500 - 200 - gap - 2}]
    return {"room": {"width": 500, "depth": 600}, "openings": [{"type": "door", "wall": "N", "offset": 200, "width": 90}],
            "furniture": furn}


BLOCK = ("ENTRY_BLOCKED", "NO_ACCESS")


def is_blocked(r):
    return any(c in BLOCK for c in codes(r)) and r["score"] == 0.0 and r["feasible"] is False


print("\n[#1] 整排家具把門口封死 → 判定不可用，總分 0（他：y=0/20/36/40/50 漏報）")
for y in (0, 20, 36, 40, 50, 60, 80, 100):
    r = ev(sealed(y))
    check("書櫃牆 y={} 封死 → {} 總分 {}".format(y, [c for c in codes(r) if c in BLOCK], r["score"]), is_blocked(r))
check("反例：書櫃牆留 80cm 缺口 → 可通行，不是 0 分", not is_blocked(ev(sealed(40, gap=80))) and ev(sealed(40, gap=80))["score"] > 0)
pocket = {"room": {"width": 300, "depth": 300}, "openings": [{"type": "door", "wall": "S", "offset": 100, "width": 90, "swing": "sliding"}],
          "furniture": [{"type": "desk", "x": 0, "y": 0, "facing": "S"}, {"type": "tv_cabinet", "x": 125, "y": 0, "facing": "E"},
                        {"type": "tv_cabinet", "x": 0, "y": 140, "facing": "S"}]}
rp = ev(pocket)
check("反例：只有書桌被圍在角落（房間大部分可走）→ 報 UNREACHABLE、不是 0 分",
      "UNREACHABLE" in codes(rp) and rp["score"] > 0 and not is_blocked(rp))
check("反例：沒有擋門 → 可通行，不是 0 分", not is_blocked(ev({"room": {"width": 500, "depth": 600},
      "openings": [{"type": "door", "wall": "N", "offset": 200, "width": 90}],
      "furniture": [{"type": "bookshelf", "x": 10, "y": 300, "facing": "S"}]})))
for wall in "NSEW":     # 四面牆的門
    d = {"room": {"width": 500, "depth": 500}, "openings": [{"type": "door", "wall": wall, "offset": 200, "width": 90}], "furniture": []}
    # 在門口內側 30cm 處築一道牆（書櫃 80×35 排滿）
    far = 30
    if wall == "N":
        d["furniture"] = [{"type": "bookshelf", "x": 1 + i * 166, "y": far, "facing": "S", "width": 166} for i in range(3)]
    elif wall == "S":
        d["furniture"] = [{"type": "bookshelf", "x": 1 + i * 166, "y": 500 - far - 35, "facing": "N", "width": 166} for i in range(3)]
    elif wall == "W":
        d["furniture"] = [{"type": "bookshelf", "x": far, "y": 1 + i * 166, "facing": "E", "width": 166} for i in range(3)]
    else:
        d["furniture"] = [{"type": "bookshelf", "x": 500 - far - 35, "y": 1 + i * 166, "facing": "W", "width": 166} for i in range(3)]
    check("{}牆的門被封死 → 0 分".format(wall), is_blocked(ev(d)))


# ---------------------------------------------------------------- #2 房外不可行
def mv(x, y):
    d = copy.deepcopy(base)
    for f in d["furniture"]:
        if f["type"] == "bed_double":
            f["x"], f["y"] = x, y
    return d


print("\n[#2] 家具在房間外：總分不能高於屋內（他：58.4 → 75.2）")
inn, outn = ev(mv(104, 0)), ev(mv(9000, 9000))
check("房外總分 {} ≤ 屋內 {}".format(outn["score"], inn["score"]), outn["score"] <= inn["score"])
check("房外配置標示為不可行", outn.get("feasible") is False)
check("反例：屋內配置可行", inn.get("feasible") is True)


# ---------------------------------------------------------------- #3 樑
def beamd(beams):
    return {"room": {"width": 360, "depth": 330}, "openings": [{"type": "door", "wall": "S", "offset": 20, "width": 90}],
            "furniture": [{"type": "bed_double", "x": 104, "y": 0, "facing": "S"}], "beams": beams}


print("\n[#3] 同一根樑拆兩段、重複輸入，分數要相同")
one = [{"x": 100, "y": 20, "w": 170, "d": 30}]
two = [{"x": 100, "y": 20, "w": 85, "d": 30}, {"x": 185, "y": 20, "w": 85, "d": 30}]
dup = [one[0], dict(one[0])]
s1, s2, s3 = ev(beamd(one))["score"], ev(beamd(two))["score"], ev(beamd(dup))["score"]
check("單根={} 拆兩段={} 重複={}".format(s1, s2, s3), s1 == s2 == s3)
overlap_ = [{"x": 100, "y": 20, "w": 100, "d": 30}, {"x": 150, "y": 20, "w": 120, "d": 30}]
check("重疊的兩段也合併", ev(beamd(overlap_))["score"] == s1)
apart = [{"x": 100, "y": 20, "w": 60, "d": 30}, {"x": 220, "y": 20, "w": 60, "d": 30}]
check("反例：兩根真的分開的樑不合併", len(lay.load_layout(beamd(apart))["beams"]) == 2)


# ---------------------------------------------------------------- #4 鏡子遮擋
def mir(blocker=None):
    d = {"room": {"width": 360, "depth": 330}, "openings": [], "furniture": [
        {"type": "bed_double", "x": 104, "y": 0, "facing": "S"}, {"type": "mirror", "x": 157, "y": 320, "facing": "N"}]}
    if blocker:
        d["furniture"].append(blocker)
    return d


print("\n[#4] 鏡子與床之間被高櫃完全擋住，不報鏡照床")
check("無遮擋 → 報", "MIRROR_FACES_BED" in codes(ev(mir())))
check("衣櫃完全擋住 → 不報", "MIRROR_FACES_BED" not in codes(
    ev(mir({"type": "wardrobe", "x": 120, "y": 250, "facing": "N", "width": 120}))))
check("反例：衣櫃只擋一小部分 → 仍報", "MIRROR_FACES_BED" in codes(
    ev(mir({"type": "wardrobe", "x": 120, "y": 250, "facing": "N", "width": 20}))))
check("反例：矮的茶几擋住不算遮擋 → 仍報", "MIRROR_FACES_BED" in codes(
    ev(mir({"type": "coffee_table", "x": 120, "y": 250, "facing": "N", "width": 120}))))

def real_room(block):
    d = copy.deepcopy(base)      # 有門、有窗、有樑的真實房間
    d["furniture"].append({"type": "mirror", "x": 157, "y": 320, "facing": "N"})
    if block:
        d["furniture"].append({"type": "wardrobe", "x": 120, "y": 250, "facing": "N", "width": 120})
    return d


r_open, r_blk = ev(real_room(False)), ev(real_room(True))
check("真實房間：擋住鏡子只少一項扣分（風水 {}→{}），總分 {}→{}，不會變 100".format(
    r_open["fengshui"], r_blk["fengshui"], r_open["score"], r_blk["score"]),
    r_blk["fengshui"] == r_open["fengshui"] + 12 and r_blk["score"] < 100)

# ---------------------------------------------------------------- #5 輸出路徑
print("\n[#5] --svg / --out-dir 不能含 ..")
tmp = tempfile.mkdtemp()
work = os.path.join(tmp, "a", "b")
os.makedirs(work)
inp = os.path.join(work, "in.json")
json.dump(base, open(inp, "w", encoding="utf-8"), ensure_ascii=False)
sp = os.path.join(work, "sp.json")
json.dump({"room": {"width": 360, "depth": 330}, "items": [{"type": "bed_double"}]}, open(sp, "w"))
r1 = subprocess.run([sys.executable, LAYOUT, "check", inp, "--svg", "../../escape.svg"], cwd=work, capture_output=True)
check("--svg ../../ 被拒絕且沒寫出去", r1.returncode != 0 and not os.path.exists(os.path.join(tmp, "escape.svg")))
r2 = subprocess.run([sys.executable, LAYOUT, "optimize", sp, "--out-dir", "../escape_dir", "--iters", "50"], cwd=work, capture_output=True)
check("--out-dir ../ 被拒絕且沒建出去", r2.returncode != 0 and not os.path.isdir(os.path.join(tmp, "a", "escape_dir")))
r3 = subprocess.run([sys.executable, LAYOUT, "check", inp, "--svg", "sub/ok.svg"], cwd=work, capture_output=True)
check("反例：子資料夾 sub/ok.svg 正常", r3.returncode == 0 and os.path.exists(os.path.join(work, "sub", "ok.svg")))
r4 = subprocess.run([sys.executable, LAYOUT, "optimize", sp, "--out-dir", "plans/v1", "--iters", "50", "--seed", "1"], cwd=work, capture_output=True)
check("反例：--out-dir plans/v1 正常", r4.returncode == 0 and os.path.isdir(os.path.join(work, "plans", "v1")))


# ---------------------------------------------------------------- #6 門窗超出牆長
def door(**kw):
    o = {"type": "door", "wall": "S", "offset": 20, "width": 90}
    o.update(kw)
    return {"room": {"width": 360, "depth": 330}, "openings": [o], "furniture": []}


print("\n[#6] 門窗 offset + width 不能超出牆長")
check("offset=99999 拒絕", rejects(door(offset=99999)))
check("width=99999 拒絕", rejects(door(width=99999)))
check("offset=-5 拒絕", rejects(door(offset=-5)))
check("反例：offset+width 恰好等於牆長 360 → 接受", not rejects(door(offset=270, width=90)))
check("反例：東牆的門用房深 330 判斷", rejects({"room": {"width": 360, "depth": 330},
      "openings": [{"type": "door", "wall": "E", "offset": 300, "width": 90}], "furniture": []}))

# ---------------------------------------------------------------- #7 樑在房外
print("\n[#7] 樑完全在房間外要拒絕")
b = lambda **k: {"room": {"width": 360, "depth": 330}, "beams": [dict({"x": 5000, "y": 5000, "w": 100, "d": 30}, **k)], "furniture": []}
check("完全在房外 → 拒絕", rejects(b()))
check("在左上方外面（負座標）→ 拒絕", rejects(b(x=-500, y=-500)))
check("反例：只有一部分在房外（牆厚）→ 接受", not rejects(b(x=340, y=100)))
check("反例：貼著房間邊界 → 接受", not rejects(b(x=0, y=0)))


# ---------------------------------------------------------------- #8 count
print("\n[#8] count 必須是 0～50 的整數")
def opt(cnt):
    return {"room": {"width": 360, "depth": 330}, "items": [{"type": "bed_double"}, {"type": "wardrobe", "count": cnt}]}


for cnt in (1.9, -0.5, -1, 51):
    try:
        lay.optimize(copy.deepcopy(opt(cnt)), top=1, seed=1, iters=50)
        check("count={} 拒絕".format(cnt), False, "沒有拒絕")
    except ValueError:
        check("count={} 拒絕".format(cnt), True)
for cnt in (0, 1, 2):
    ch = lay.optimize(copy.deepcopy(opt(cnt)), top=1, seed=1, iters=100)
    n = sum(1 for f in ch[0][0]["furniture"] if f["type"] == "wardrobe")
    check("反例：count={} 照常（放 {} 件）".format(cnt, n), n <= cnt)

# ---------------------------------------------------------------- #9 負淨空
print("\n[#9] 超出房間的家具不再產生負的淨空訊息")
check("床在房外：沒有「只剩 -」", not any("只剩 -" in i["message"] for i in ev(mv(9000, 9000))["issues"]))
check("床在房外：仍有 OUT_OF_ROOM", "OUT_OF_ROOM" in codes(ev(mv(9000, 9000))))

# ---------------------------------------------------------------- #10 字串
print("\n[#10] 數字欄位不接受字串")
d = copy.deepcopy(base)
d["room"]["width"] = "360"
check("room.width='360' 拒絕", rejects(d))
d = copy.deepcopy(base)
d["furniture"][0]["x"] = "104"
check("furniture.x='104' 拒絕", rejects(d))

# ---------------------------------------------------------------- #11 座標上限
print("\n[#11] 座標與尺寸有上限")
d = copy.deepcopy(base)
d["furniture"][0]["x"] = 1e308
check("x=1e308 拒絕", rejects(d))
d = copy.deepcopy(base)
d["furniture"][0]["x"] = 1000001
check("x=1000001（超過 1,000,000cm）拒絕", rejects(d))
d = copy.deepcopy(base)
d["furniture"][0]["x"] = 5000
check("反例：x=5000 接受（雖在房外，由 OUT_OF_ROOM 處理）", not rejects(d))

# ---------------------------------------------------------------- 未驗證：mirror
print("\n[#12] optimize 保留 mirror / tall / clearance / name")
sp2 = {"room": {"width": 360, "depth": 330}, "items": [{"type": "bed_double"}, {"type": "wardrobe", "mirror": True, "name": "鏡門衣櫃", "clearance": 80}]}
ch = lay.optimize(copy.deepcopy(sp2), top=1, seed=1, iters=100)
w = [f for f in ch[0][0]["furniture"] if f["type"] == "wardrobe"][0]
check("輸出的衣櫃帶 mirror=True", w.get("mirror") is True)
check("輸出的衣櫃帶 name 與 clearance", w.get("name") == "鏡門衣櫃" and w.get("clearance") == 80)
r = lay.evaluate(lay.load_layout(ch[0][0]))
check("optimize 回報分數 = 輸出檔重新 check 的分數", r["score"] == ch[0][1]["score"], "{} vs {}".format(r["score"], ch[0][1]["score"]))

print("\n" + "=" * 60)
if FAILS:
    print("回歸測試：{} / {} 項失敗".format(len(FAILS), COUNT[0]))
    for n in FAILS:
        print(" - " + n)
    sys.exit(1)
print("回歸測試：全部 {} 項通過".format(COUNT[0]))
