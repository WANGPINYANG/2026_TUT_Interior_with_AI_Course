#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
人體工學規則驗證：拿 references/ergonomics.md 的規範當標準答案，
用「邊界掃描」確認 layout.py 在規範的門檻上真的有反應，而且四個方向的結果一致。

用法：python tests/ergonomics_test.py
"""
import copy
import importlib.util
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
spec_ = importlib.util.spec_from_file_location("layout", os.path.join(HERE, "..", "scripts", "layout.py"))
lay = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(lay)

FAILS = []
ROT = {"N": "E", "E": "S", "S": "W", "W": "N"}


# ------------------------------------------------------------ 旋轉：把同一個情境轉 4 個方向
def rotate(d):
    """順時針轉 90 度：(x,y)->(D-y,x)，新房間寬=D、深=W"""
    W, D = float(d["room"]["width"]), float(d["room"]["depth"])
    out = copy.deepcopy(d)
    out["room"]["width"], out["room"]["depth"] = D, W
    for f, raw in zip(out.get("furniture", []), d.get("furniture", [])):
        it = lay.make_item(raw)
        f["x"], f["y"] = D - it["y"] - it["d"], it["x"]
        f["facing"] = ROT[raw.get("facing", "S")]
    for o in out.get("openings", []):
        w, a = o["width"], o["offset"]
        if o["wall"] in ("E", "W"):
            o["offset"] = D - a - w
        o["wall"] = ROT[o["wall"]]
    return out


def four(d):
    ds = [d]
    for _ in range(3):
        ds.append(rotate(ds[-1]))
    return ds


def codes(d, with_path=True):
    res = lay.evaluate(lay.load_layout(d), with_path=with_path)
    return Counter(i["code"] for i in res["issues"] if i["category"] == "人體工學")


def check(name, ok, detail=""):
    if not ok:
        FAILS.append((name, detail))
        print("  ✘ {} {}".format(name, detail))
    return ok


def all_rotations(name, d, expect, with_path=True):
    """四個方向都要得到 expect（一個 code 集合）"""
    for k, dd in enumerate(four(d)):
        got = set(codes(dd, with_path))
        if not check("{} [轉{}°]".format(name, k * 90), got == expect,
                     "預期 {} 實際 {}".format(sorted(expect), sorted(got))):
            return False
    return True


# ------------------------------------------------------------ 1. 走道 / 動線（網格 BFS）
def corridor_case(gap, kind):
    """北牆衣櫃、南牆拉門，中間一排電視櫃擋住，只留一個缺口 gap"""
    if kind == "between":     # 缺口在兩件家具之間
        W = 360 + gap
        furn = [{"type": "tv_cabinet", "x": 0, "y": 250, "facing": "S"},
                {"type": "tv_cabinet", "x": 180 + gap, "y": 250, "facing": "S"}]
    else:                     # 缺口在家具與牆之間
        W = 180 + gap
        furn = [{"type": "tv_cabinet", "x": gap, "y": 250, "facing": "S"}]
    furn.append({"type": "wardrobe", "x": (W - 120) / 2.0, "y": 0, "facing": "S"})
    return {"room": {"width": W, "depth": 500},
            "openings": [{"type": "door", "wall": "S", "offset": max(0, W / 2 - 45), "width": 90, "swing": "sliding"}],
            "furniture": furn}


def test_corridor():
    print("\n[1] 動線寬度：兩件家具之間／家具與牆之間，最窄能過幾公分？（規範：最低 50cm）")
    for kind, zh in (("between", "家具之間"), ("wall", "家具與牆")):
        thr = None
        for gap in range(30, 91):
            if "UNREACHABLE" not in codes(corridor_case(gap, kind)):
                thr = gap
                break
        print("  {}：從 {} cm 起判定走得過去".format(zh, thr))
        check("動線 {} 門檻接近 50".format(zh), thr is not None and 50 <= thr <= 55,
              "實測門檻 {}cm（過寬鬆 <50 會放行 50cm 以下走道；過嚴 >55 會誤報）".format(thr))
        # 四方向一致
        for gap in (40, 60):
            exp = {"UNREACHABLE"} if gap < 50 else set()
            for k, dd in enumerate(four(corridor_case(gap, kind))):
                got = "UNREACHABLE" in codes(dd)
                check("動線 {} gap={} 轉{}°".format(zh, gap, k * 90), got == bool(exp),
                      "預期{}被擋 實際{}".format("" if exp else "不", "被擋" if got else "通過"))


# ------------------------------------------------------------ 2. 床邊走道
def bed_case(gw, ge):
    W = 152 + gw + ge
    return {"room": {"width": W, "depth": 400}, "openings": [],
            "furniture": [{"type": "bed_double", "x": gw, "y": 0, "facing": "S"}]}


def test_bed():
    print("\n[2] 床邊走道（規範：至少一側 60、最低 45；雙人床兩側各最低 45）")
    cases = [  # (西側, 東側, 預期 code)
        (100, 100, set()), (60, 0, {"BED_ONE_SIDE"}), (59, 0, {"BED_SIDE"}),
        (60, 44, {"BED_ONE_SIDE"}), (60, 45, set()), (60, 60, set()),
        (59, 59, {"BED_SIDE"}), (50, 50, {"BED_SIDE"}), (45, 45, {"BED_SIDE"}),
        (44, 44, {"BED_SIDE"}), (0, 0, {"BED_SIDE"}), (0, 100, {"BED_ONE_SIDE"}),
    ]
    for gw, ge, exp in cases:
        all_rotations("床 側邊 {}/{}".format(gw, ge), bed_case(gw, ge), exp, with_path=False)
    # 嚴重程度：兩側都 < 45 要是 error
    res = lay.evaluate(lay.load_layout(bed_case(44, 44)), with_path=False)
    lv = [i["level"] for i in res["issues"] if i["code"] == "BED_SIDE"]
    check("床 兩側 44 → error", lv == ["error"], str(lv))
    res = lay.evaluate(lay.load_layout(bed_case(50, 50)), with_path=False)
    lv = [i["level"] for i in res["issues"] if i["code"] == "BED_SIDE"]
    check("床 兩側 50 → warning", lv == ["warning"], str(lv))
    # 單人床：只有一側不夠也不該報 BED_ONE_SIDE
    d = bed_case(60, 0)
    d["furniture"][0]["type"] = "bed_single"
    d["room"]["width"] = 106 + 60
    check("單人床 一側靠牆不報 ONE_SIDE", "BED_ONE_SIDE" not in codes(d, False))


# ------------------------------------------------------------ 3. 家具前方淨空
def front_case(t, gap):
    req = lay.CATALOG[t][3]
    w = lay.CATALOG[t][1]
    W = max(w, 180) + 40
    return {"room": {"width": W, "depth": 600}, "openings": [],
            "furniture": [{"type": t, "x": 20, "y": 0, "facing": "S"},
                          {"type": "coffee_table", "x": 20, "y": lay.CATALOG[t][2] + gap, "facing": "S", "width": 180}]}, req


def test_front():
    print("\n[3] 家具前方淨空（規範：衣櫃60 書桌75 梳妝台70 書櫃60 沙發35；<70% 為嚴重）")
    for t in ("wardrobe", "desk", "dresser", "bookshelf", "sofa"):
        _, req = front_case(t, 0)
        for gap in (0, int(req * 0.7) - 1, int(req * 0.7), req - 1, req, req + 1, req + 40):
            d, _ = front_case(t, gap)
            exp = set() if gap >= req else {"FRONT_CLEAR"}
            all_rotations("{} 前方 {}cm".format(t, gap), d, exp, with_path=False)
        lv = lambda g: [i["level"] for i in lay.evaluate(lay.load_layout(front_case(t, g)[0]), False)["issues"]
                        if i["code"] == "FRONT_CLEAR"]
        check("{} 前方 {}cm → error".format(t, int(req * 0.7) - 1), lv(int(req * 0.7) - 1) == ["error"], str(lv(int(req * 0.7) - 1)))
        check("{} 前方 {}cm → warning".format(t, req - 1), lv(req - 1) == ["warning"], str(lv(req - 1)))
    # 沙發前面是茶几：規範「沙發到茶几最低 30、以 35 檢查」
    for gap, exp in ((30, True), (34, True), (35, False), (45, False)):
        d = {"room": {"width": 400, "depth": 600}, "openings": [],
             "furniture": [{"type": "sofa", "x": 100, "y": 0, "facing": "S"},
                           {"type": "coffee_table", "x": 145, "y": 90 + gap, "facing": "N"}]}
        got = "FRONT_CLEAR" in codes(d, False)
        check("沙發到茶几 {}cm".format(gap), got == exp, "預期{}報 實際{}報".format("" if exp else "不", "" if got else "不"))


# ------------------------------------------------------------ 4. 餐桌四周
def test_dining():
    print("\n[4] 餐桌四周（規範：只坐人 60 以上）")
    for gap in (40, 59, 60, 75):
        W = 150 + 2 * gap
        d = {"room": {"width": W, "depth": 90 + 2 * gap}, "openings": [],
             "furniture": [{"type": "dining_table", "x": gap, "y": gap, "facing": "S"}]}
        exp = set() if gap >= 60 else {"DINING_CLEAR"}
        all_rotations("餐桌四周 {}cm".format(gap), d, exp, with_path=False)


# ------------------------------------------------------------ 5. 門片開啟範圍
def test_door_swing():
    print("\n[5] 門片開啟範圍（規範：門寬×門寬不得有家具）")
    for wall in "NSEW":
        for dw in (70, 90):
            for off_gap, exp in ((-1, True), (0, False), (1, False)):
                # 北牆門，書櫃放在門片範圍邊緣；以 N 為基準旋轉到其他牆
                d = {"room": {"width": 400, "depth": 400},
                     "openings": [{"type": "door", "wall": "N", "offset": 100, "width": dw}],
                     "furniture": [{"type": "bookshelf", "x": 100, "y": dw + off_gap, "facing": "S", "width": 80, "depth": 35}]}
                dd = d
                for _ in range("NESW".index(wall)):
                    dd = rotate(dd)
                got = "DOOR_BLOCKED" in codes(dd, False)
                check("門{}牆 寬{} 家具距門片{}".format(wall, dw, off_gap), got == exp,
                      "預期{}擋 實際{}擋".format("" if exp else "不", "" if got else "不"))
    d = {"room": {"width": 400, "depth": 400},
         "openings": [{"type": "door", "wall": "N", "offset": 100, "width": 90, "swing": "sliding"}],
         "furniture": [{"type": "bookshelf", "x": 100, "y": 20, "facing": "S"}]}
    check("拉門不檢查開門範圍", "DOOR_BLOCKED" not in codes(d, False))


# ------------------------------------------------------------ 6. 沙發與電視
def test_tv():
    print("\n[6] 沙發到電視距離（規範：180–450）")
    for dist, exp in ((170, True), (179, True), (180, False), (300, False), (450, False), (460, True)):
        D = 90 + dist + 45 + 40
        d = {"room": {"width": 400, "depth": D}, "openings": [],
             "furniture": [{"type": "sofa", "x": 95, "y": 0, "facing": "S"},
                           {"type": "tv_cabinet", "x": 110, "y": 90 + dist, "facing": "N"}]}
        got = "TV_DISTANCE" in codes(d, False)
        check("沙發到電視 {}cm".format(dist), got == exp, "預期{}報 實際{}報".format("" if exp else "不", "" if got else "不"))
    d = {"room": {"width": 400, "depth": 500}, "openings": [],
         "furniture": [{"type": "sofa", "x": 95, "y": 0, "facing": "S"},
                       {"type": "tv_cabinet", "x": 10, "y": 400, "facing": "S"}]}
    check("沙發背對電視 → SOFA_TV", "SOFA_TV" in codes(d, False))


# ------------------------------------------------------------ 7. 動線：床／餐桌／家具使用區真的走得到
def test_reach_targets():
    print("\n[7] 被圍住的家具使用區要報 UNREACHABLE")
    # 書桌被衣櫃與牆圍成死角：門在對面，桌前被封死
    d = {"room": {"width": 300, "depth": 300},
         "openings": [{"type": "door", "wall": "S", "offset": 100, "width": 90, "swing": "sliding"}],
         "furniture": [{"type": "desk", "x": 0, "y": 0, "facing": "S"},
                       {"type": "tv_cabinet", "x": 125, "y": 0, "facing": "E"},
                       {"type": "tv_cabinet", "x": 0, "y": 140, "facing": "S"}]}
    got = "UNREACHABLE" in codes(d)
    check("書桌前方被封死 → UNREACHABLE", got, "沒有報")
    # 反例：同一房間沒有封死
    d2 = copy.deepcopy(d)
    d2["furniture"] = d2["furniture"][:1]
    check("書桌前方暢通 → 不報", "UNREACHABLE" not in codes(d2))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    for fn in (test_corridor, test_bed, test_front, test_dining, test_door_swing, test_tv, test_reach_targets):
        fn()
    print("\n" + "=" * 60)
    if FAILS:
        print("人體工學驗證：{} 項與規範不符".format(len(FAILS)))
        for n, dtl in FAILS:
            print(" - {} {}".format(n, dtl))
        sys.exit(1)
    print("人體工學驗證：全部與規範相符")


if __name__ == "__main__":
    main()
