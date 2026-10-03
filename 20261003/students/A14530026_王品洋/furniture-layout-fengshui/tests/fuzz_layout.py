#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
layout.py 暴力測試（fuzz / brute-force）

用法：python tests/fuzz_layout.py [--n 3000] [--seed 1] [--opt 25]

測試四類東西：
  A. 隨機壞資料：把合法輸入的欄位隨機刪除、改成 None/字串/負數/NaN...，看有沒有「未處理的例外」
  B. 性質檢查：合法輸入下，分數範圍、重複執行結果、OUT_OF_ROOM / OVERLAP 與獨立暴力算法比對
  C. 對稱檢查：左右鏡射、上下鏡射後，問題清單應該一致（不一致 = 規則有方向偏差）
  D. optimize 與 CLI：最佳化結果自己再 check 一次、種子可重現、BOM / 壞 JSON / 超大房間
"""
import argparse
import copy
import importlib.util
import json
import math
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
LAYOUT = os.path.join(HERE, "..", "scripts", "layout.py")
spec_ = importlib.util.spec_from_file_location("layout", LAYOUT)
lay = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(lay)

CJK = re.compile(r"[一-鿿]")
BUGS = defaultdict(lambda: {"count": 0, "repro": None, "msg": ""})
TYPES = list(lay.CATALOG)


def record(group, title, repro, msg=""):
    b = BUGS[(group, title)]
    b["count"] += 1
    if b["repro"] is None:
        b["repro"], b["msg"] = repro, msg


def crash_key(exc):
    tb = traceback.extract_tb(exc.__traceback__)
    last = [f for f in tb if f.filename.endswith("layout.py")]
    f = last[-1] if last else tb[-1]
    return "{} @ layout.py:{} ({})".format(type(exc).__name__, f.lineno, f.name)


def guarded(group, repro, fn):
    """執行 fn；ValueError 且有中文訊息 = 有好好處理的輸入錯誤，其餘例外 = 未處理崩潰"""
    try:
        return fn()
    except ValueError as e:
        if CJK.search(str(e)):
            return None
        record(group, crash_key(e), repro, str(e))
    except Exception as e:  # noqa
        record(group, crash_key(e), repro, "{}: {}".format(type(e).__name__, e))
    return None


# ------------------------------------------------------------ 產生器
def gen_valid(rng):
    W, D = rng.randrange(150, 801, 5), rng.randrange(150, 801, 5)
    data = {"room": {"name": "fuzz", "width": W, "depth": D}, "openings": [], "beams": [], "furniture": []}
    for _ in range(rng.randint(0, 4)):
        wall = rng.choice("NSEW")
        ln = W if wall in "NS" else D
        wd = rng.choice([60, 70, 80, 90, 120, 150])
        o = {"type": rng.choice(["door", "window"]), "wall": wall,
             "offset": rng.randrange(0, max(1, ln - wd), 5), "width": wd}
        if o["type"] == "door":
            if rng.random() < 0.3:
                o["kind"] = rng.choice(["bathroom", "entry"])
            if rng.random() < 0.2:
                o["swing"] = "sliding"
        data["openings"].append(o)
    for _ in range(rng.randint(0, 2)):
        data["beams"].append({"x": rng.randrange(0, W, 5), "y": rng.randrange(0, D, 5),
                              "w": rng.choice([20, 30, 60, W]), "d": rng.choice([20, 30, 60, D])})
    for _ in range(rng.randint(0, 8)):
        f = {"type": rng.choice(TYPES), "x": rng.randrange(-20, W, 5), "y": rng.randrange(-20, D, 5),
             "facing": rng.choice("NSEW")}
        if rng.random() < 0.2:
            f["width"] = rng.randrange(30, 250, 5)
        if rng.random() < 0.2:
            f["depth"] = rng.randrange(30, 250, 5)
        data["furniture"].append(f)
    return data


BAD = [None, "abc", "", -1, 0, 0.001, 1e9, -1e9, float("nan"), float("inf"), [], {}, True, 10 ** 30, "N", "n", "S "]


def leaves(node, path=()):
    if isinstance(node, dict):
        for k, v in list(node.items()):
            yield node, k, path + (k,)
            yield from leaves(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield node, i, path + (i,)
            yield from leaves(v, path + (i,))


def mutate(data, rng):
    d = copy.deepcopy(data)
    targets = [t for t in leaves(d) if t[2][:2] not in (("room", "width"), ("room", "depth"))]
    if not targets:
        return d
    for _ in range(rng.randint(1, 2)):
        node, key, _ = rng.choice(targets)
        if isinstance(node, dict) and key in node and rng.random() < 0.35:
            del node[key]
        elif key in (node if isinstance(node, dict) else range(len(node))):
            node[key] = rng.choice(BAD)
    return d


# ------------------------------------------------------------ A. 壞資料
def test_bad_data(rng, n, svg_path):
    for i in range(n):
        base = gen_valid(rng)
        d = mutate(base, rng)
        repro = json.dumps(d, ensure_ascii=False, default=str)

        def run():
            L = lay.load_layout(d)
            res = lay.evaluate(L)
            if i % 5 == 0:
                lay.render_svg(L, res, svg_path, "t")
            return res
        guarded("A 壞資料", repro, run)


# ------------------------------------------------------------ B. 性質
def oracle_issues(L):
    W, D = L["room"]
    out_room, overlaps = set(), set()
    rs = [(it["id"], lay.rect(it)) for it in L["items"]]
    for k, (i, r) in enumerate(rs):
        if r[0] < -0.01 or r[1] < -0.01 or r[2] > W + 0.01 or r[3] > D + 0.01:
            out_room.add(i)
        for j, s in rs[k + 1:]:
            if min(r[2], s[2]) - max(r[0], s[0]) > 0.01 and min(r[3], s[3]) - max(r[1], s[1]) > 0.01:
                overlaps.add(frozenset((i, j)))
    return out_room, overlaps


def test_properties(rng, n):
    for _ in range(n):
        d = gen_valid(rng)
        repro = json.dumps(d, ensure_ascii=False)
        L = guarded("B 性質", repro, lambda: lay.load_layout(d))
        if L is None:
            continue
        res = guarded("B 性質", repro, lambda: lay.evaluate(L))
        if res is None:
            continue
        for k in ("score", "ergonomics", "fengshui"):
            if not (0 <= res[k] <= 100) or math.isnan(res[k]):
                record("B 性質", "{} 超出 0~100".format(k), repro, str(res[k]))
        if lay.evaluate(L) != res:
            record("B 性質", "同一輸入兩次結果不同（不確定性）", repro)
        for isu in res["issues"]:
            if isu["level"] not in lay.PENALTY or isu["category"] not in ("人體工學", "風水"):
                record("B 性質", "issue 欄位異常", repro, str(isu))
        ids = [it["id"] for it in L["items"]]
        if len(ids) != len(set(ids)):
            record("B 性質", "id 重複（本來就不該發生）", repro)
        got_out = {i for i in ids if any(x["code"] == "OUT_OF_ROOM" and x["message"].startswith(
            next(it["name"] for it in L["items"] if it["id"] == i)) for x in res["issues"])}
        o_out, o_ovl = oracle_issues(L)
        n_ovl = sum(1 for x in res["issues"] if x["code"] == "OVERLAP")
        if n_ovl != len(o_ovl):
            record("B 性質", "OVERLAP 數量與暴力算法不符", repro, "程式 {} vs 暴力 {}".format(n_ovl, len(o_ovl)))
        n_out = sum(1 for x in res["issues"] if x["code"] == "OUT_OF_ROOM")
        if n_out != len(o_out):
            record("B 性質", "OUT_OF_ROOM 數量與暴力算法不符", repro, "程式 {} vs 暴力 {}".format(n_out, len(o_out)))
    # 重複 id（使用者自訂 id 相同）
    d = {"room": {"width": 400, "depth": 400}, "openings": [],
         "furniture": [{"type": "bed_double", "id": "a", "x": 0, "y": 0, "facing": "S"},
                       {"type": "bed_double", "id": "a", "x": 200, "y": 0, "facing": "S"},
                       {"type": "wardrobe", "id": "a", "x": 0, "y": 300, "facing": "N"}]}
    try:
        lay.load_layout(d)
        record("B 性質", "使用者自訂 id 重複沒有被拒絕（rects 字典會互相覆蓋）", json.dumps(d, ensure_ascii=False))
    except ValueError:
        pass   # 正確：應該明確拒絕重複 id


# ------------------------------------------------------------ C. 鏡射對稱
def flip(d, axis):
    """axis='x' 左右鏡射（E<->W），axis='y' 上下鏡射（N<->S）"""
    W, D = float(d["room"]["width"]), float(d["room"]["depth"])
    swap = {"x": {"E": "W", "W": "E"}, "y": {"N": "S", "S": "N"}}[axis]
    out = copy.deepcopy(d)
    for f, raw in zip(out["furniture"], d["furniture"]):
        it = lay.make_item(raw)
        if axis == "x":
            f["x"] = W - it["x"] - it["w"]
        else:
            f["y"] = D - it["y"] - it["d"]
        f["facing"] = swap.get(raw.get("facing", "S"), raw.get("facing", "S"))
    for o in out["openings"]:
        ln = W if o["wall"] in "NS" else D
        along = (axis == "x" and o["wall"] in "NS") or (axis == "y" and o["wall"] in "EW")
        if along:
            o["offset"] = ln - o["offset"] - o["width"]
        o["wall"] = swap.get(o["wall"], o["wall"])
    for b in out["beams"]:
        if axis == "x":
            b["x"] = W - b["x"] - b["w"]
        else:
            b["y"] = D - b["y"] - b["d"]
    return out


def sig(res):
    return Counter((x["code"], x["level"]) for x in res["issues"])


def test_symmetry(rng, n):
    for _ in range(n):
        d = gen_valid(rng)
        base = guarded("C 對稱", json.dumps(d, ensure_ascii=False), lambda: lay.evaluate(lay.load_layout(d)))
        if base is None or any(x["code"] in ("OUT_OF_ROOM", "OVERLAP") for x in base["issues"]):
            continue   # 家具超出房間時，網格會被截斷而不對稱，那是壞輸入，不算規則偏差
        for axis in "xy":
            f = flip(d, axis)
            r = guarded("C 對稱", json.dumps(f, ensure_ascii=False), lambda: lay.evaluate(lay.load_layout(f)))
            if r is None:
                continue
            if sig(base) != sig(r):
                diff = (sig(base) - sig(r)) + (sig(r) - sig(base))
                code = sorted(c for c, _ in diff)
                record("C 對稱", "{}鏡射後問題清單不同：{}".format("左右" if axis == "x" else "上下", "/".join(sorted(set(code)))),
                       json.dumps(d, ensure_ascii=False),
                       "原始 {} / 鏡射 {}".format(dict(sig(base)), dict(sig(r))))


# ------------------------------------------------------------ D. optimize
def gen_spec(rng):
    d = gen_valid(rng)
    d.pop("furniture")
    items = []
    for _ in range(rng.randint(0, 6)):
        t = rng.choice(TYPES)
        it = {"type": t}
        if rng.random() < 0.3:
            it["count"] = rng.choice([0, 1, 2, 3, -1])
        if rng.random() < 0.3:
            it["walls"] = rng.sample(list("NSEW"), rng.randint(0, 3))
        if rng.random() < 0.2:
            it["width"] = rng.randrange(30, 300, 10)
        items.append(it)
    d["items"] = items
    return d


def test_optimize(rng, n):
    for k in range(n):
        spec = gen_spec(rng)
        repro = json.dumps(spec, ensure_ascii=False)
        seed = rng.randrange(1000)
        ch = guarded("D optimize", repro, lambda: lay.optimize(copy.deepcopy(spec), top=3, seed=seed, iters=150))
        if not ch:
            continue
        if len(ch) > 3:
            record("D optimize", "top=3 卻回傳超過 3 個方案", repro, str(len(ch)))
        ch2 = guarded("D optimize", repro, lambda: lay.optimize(copy.deepcopy(spec), top=3, seed=seed, iters=150))
        if ch2 and [c[1]["score"] for c in ch] != [c[1]["score"] for c in ch2]:
            record("D optimize", "相同 seed 結果不同（不可重現）", repro)
        for data, res in ch:
            rt = json.loads(json.dumps(data))
            L = guarded("D optimize", repro, lambda: lay.load_layout(rt))
            if L is None:
                continue
            res2 = lay.evaluate(L)
            if res2["score"] != res["score"]:
                record("D optimize", "plan.json 重新 check 分數與 optimize 回報不同", repro,
                       "{} vs {}".format(res["score"], res2["score"]))
            bad = [x["code"] for x in res2["issues"] if x["code"] in ("OUT_OF_ROOM", "OVERLAP")]
            if bad:
                record("D optimize", "最佳化方案含 OUT_OF_ROOM/OVERLAP", repro, str(bad))
            want = {}
            for s in spec["items"]:
                try:
                    want[s["type"]] = want.get(s["type"], 0) + max(int(s.get("count", 1)), 0)
                except Exception:
                    pass
            have = Counter(f["type"] for f in data["furniture"])
            for t, c in want.items():
                if t not in lay.ATTACHED and have[t] != c:
                    record("D optimize", "非依附家具數量不符（要 {} 放 {}）".format(c, have[t]), repro, t)
            if any(f["type"] in lay.ATTACHED and have[f["type"]] > want.get(f["type"], 0) for f in data["furniture"]):
                record("D optimize", "依附家具超過 count", repro)


# ------------------------------------------------------------ D2. CLI / 檔案 / 效能
def run_cli(args, timeout=60, cwd=None):
    t = time.time()
    try:
        p = subprocess.run([sys.executable, LAYOUT] + args, capture_output=True, timeout=timeout, cwd=cwd)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace"), time.time() - t
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "", "", time.time() - t


def test_cli(tmp):
    base = {"room": {"width": 360, "depth": 330}, "openings": [{"type": "door", "wall": "S", "offset": 20, "width": 90}],
            "furniture": [{"type": "bed_double", "x": 104, "y": 0, "facing": "S"}]}

    def write(name, content, mode="w", enc="utf-8"):
        p = os.path.join(tmp, name)
        with open(p, mode, **({} if "b" in mode else {"encoding": enc})) as fh:
            fh.write(content)
        return p

    good = json.dumps(base, ensure_ascii=False)
    cases = {
        "UTF-8 BOM（Windows 記事本存檔）": write("bom.json", b"\xef\xbb\xbf" + good.encode(), "wb"),
        "空檔案": write("empty.json", ""),
        "壞 JSON": write("badjson.json", "{room:"),
        "JSON 是陣列不是物件": write("arr.json", "[]"),
        "Big5/cp950 編碼存檔": write("big5.json", good.replace("360", "360").replace("bed_double", "bed_double"), enc="cp950"),
        "不存在的檔案": os.path.join(tmp, "nope.json"),
    }
    for title, path in cases.items():
        rc, out, err, _ = run_cli(["check", path])
        if rc != 0 and "Traceback" in err:
            last = err.strip().splitlines()[-1]
            record("D CLI", "{} → 直接噴 Traceback".format(title), "check " + path, last)
    for flag in (["--top", "0"], ["--top", "-1"], ["--iters", "0"], ["--iters", "-5"], ["--top", "abc"]):
        spec = {"room": {"width": 360, "depth": 330}, "items": [{"type": "bed_double"}, {"type": "nightstand", "count": 2}]}
        p = write("spec.json", json.dumps(spec))
        rc, out, err, _ = run_cli(["optimize", p, "--out-dir", os.path.join(tmp, "o"), "--seed", "1"] + flag)
        if rc != 0 and "Traceback" in err:
            record("D CLI", "optimize {} → Traceback".format(" ".join(flag)), " ".join(flag), err.strip().splitlines()[-1])
        elif flag[0] == "--top" and flag[1] in ("0", "-1") and rc == 0:
            n = out.count("方案")
            record("D CLI", "optimize {} 沒擋掉無效數值（輸出 {} 個方案）".format(" ".join(flag), n), " ".join(flag))
    for items, title in (([], "optimize 家具清單為空"), ([{"type": "nightstand"}], "optimize 只有依附家具（無床）")):
        p = write("e.json", json.dumps({"room": {"width": 360, "depth": 330}, "items": items}))
        rc, out, err, _ = run_cli(["optimize", p, "--out-dir", os.path.join(tmp, "o2"), "--seed", "1"])
        if "Traceback" in err:
            record("D CLI", title + " → Traceback", json.dumps(items), err.strip().splitlines()[-1])
    # 超大 / 極小房間
    for W, D in ((100000, 100000), (30000, 30000), (3, 3), (0, 0), (-300, 300)):
        p = write("room.json", json.dumps({"room": {"width": W, "depth": D}, "furniture": [
            {"type": "bed_double", "x": 0, "y": 0, "facing": "S"}], "openings": [{"type": "door", "wall": "S", "offset": 0, "width": 90}]}))
        rc, out, err, sec = run_cli(["check", p], timeout=20)
        if rc == "TIMEOUT":
            record("D CLI", "房間 {}x{} cm → 20 秒內跑不完（動線網格 O(W×D)）".format(W, D), "room {}x{}".format(W, D))
        elif rc != 0 and "Traceback" in err:
            record("D CLI", "房間 {}x{} → Traceback".format(W, D), "room {}x{}".format(W, D), err.strip().splitlines()[-1])
        elif rc == 0 and (W <= 0 or D <= 0):
            record("D CLI", "房間 {}x{} 這種不合理尺寸沒有被拒絕".format(W, D), "room {}x{}".format(W, D))
    # 輸出檔路徑：不存在的資料夾
    p = write("g.json", good)
    rc, out, err, _ = run_cli(["check", p, "--svg", os.path.join(tmp, "no", "such", "dir", "x.svg")])
    if "Traceback" in err:
        record("D CLI", "--svg 指到不存在的資料夾 → Traceback", "--svg no/such/dir/x.svg", err.strip().splitlines()[-1])
    # 家具名稱含 XML 特殊字元 / 非字串
    for nm in ('<script>"&', 123):
        d = copy.deepcopy(base)
        d["furniture"][0]["name"] = nm
        p = write("n.json", json.dumps(d))
        rc, out, err, _ = run_cli(["check", p, "--svg", os.path.join(tmp, "n.svg")])
        if "Traceback" in err:
            record("D CLI", "家具 name={!r} → Traceback".format(nm), "name", err.strip().splitlines()[-1])


# ------------------------------------------------------------ 主程式
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=3000, help="每類隨機案例數")
    ap.add_argument("--opt", type=int, default=25, help="optimize 隨機案例數（較慢）")
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    rng = random.Random(a.seed)
    tmp = tempfile.mkdtemp(prefix="fuzz_layout_")
    t0 = time.time()
    steps = [("A 壞資料", lambda: test_bad_data(rng, a.n, os.path.join(tmp, "t.svg"))),
             ("B 性質", lambda: test_properties(rng, a.n)),
             ("C 對稱", lambda: test_symmetry(rng, a.n // 2)),
             ("D optimize", lambda: test_optimize(rng, a.opt)),
             ("D CLI", lambda: test_cli(tmp))]
    for name, fn in steps:
        s = time.time()
        fn()
        print("[{}] 完成 {:.1f}s".format(name, time.time() - s), flush=True)

    print("\n" + "=" * 70)
    print("發現 {} 種不同的問題（種子 {}，總耗時 {:.0f}s）".format(len(BUGS), a.seed, time.time() - t0))
    print("=" * 70)
    report = []
    for k, ((group, title), b) in enumerate(sorted(BUGS.items()), 1):
        print("\n#{} [{}] {}  （{} 次）".format(k, group, title, b["count"]))
        if b["msg"]:
            print("   訊息：{}".format(b["msg"][:300]))
        print("   最小重現：{}".format((b["repro"] or "")[:600]))
        report.append({"group": group, "title": title, "count": b["count"], "message": b["msg"], "repro": b["repro"]})
    out = os.path.join(HERE, "fuzz_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\n完整報告：{}".format(out))


if __name__ == "__main__":
    main()
