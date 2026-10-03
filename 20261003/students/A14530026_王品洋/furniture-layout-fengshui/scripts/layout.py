#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
空間家具配置 + 風水檢查工具（只使用 Python 標準函式庫）

指令：
  python layout.py catalog                          列出家具型錄與預設尺寸
  python layout.py check    input.json [--svg out.svg] [--json]
  python layout.py optimize input.json [--top 3] [--out-dir out] [--seed 1] [--json]

座標系統（單位 cm）：
  原點在房間左上角（西北角），x 往東增加，y 往南增加
  北牆 y=0、南牆 y=depth、西牆 x=0、東牆 x=width
詳細輸入格式見 references/input-format.md
"""
import argparse
import html
import json
import math
import os
import random
import sys
from collections import deque

DIRS = {"N": (0, -1), "S": (0, 1), "E": (1, 0), "W": (-1, 0)}
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}
PERP = {"N": ("W", "E"), "S": ("W", "E"), "E": ("N", "S"), "W": ("N", "S")}
WALL_ZH = {"N": "北", "S": "南", "E": "東", "W": "西"}

# type: (中文名稱, 正面寬度, 前後深度, 正面淨空需求, 是否為高櫃, 顏色)
CATALOG = {
    "bed_single":   ("單人床",     106, 188, 0,  False, "#c9d8f0"),
    "bed_double":   ("雙人床",     152, 188, 0,  False, "#c9d8f0"),
    "bed_queen":    ("雙人加大床", 182, 188, 0,  False, "#c9d8f0"),
    "nightstand":   ("床頭櫃",      45,  40, 0,  False, "#e8dcc8"),
    "wardrobe":     ("衣櫃",       120,  60, 60, True,  "#d9c3a5"),
    "desk":         ("書桌",       120,  60, 75, False, "#cfe3c4"),
    "dresser":      ("梳妝台",     100,  45, 70, False, "#f0d0dc"),
    "bookshelf":    ("書櫃",        80,  35, 60, True,  "#d9c3a5"),
    "sofa":         ("沙發",       210,  90, 35, False, "#f3dfb5"),
    "coffee_table": ("茶几",       110,  55, 0,  False, "#e8dcc8"),
    "tv_cabinet":   ("電視櫃",     180,  45, 0,  False, "#dcdcdc"),
    "dining_table": ("餐桌",       150,  90, 0,  False, "#e6d2b8"),
    "mirror":       ("穿衣鏡",      45,   5, 0,  True,  "#bfe3ea"),
}
BEDS = {"bed_single", "bed_double", "bed_queen"}
MIRROR_TYPES = {"mirror", "dresser"}
ATTACHED = {"nightstand", "coffee_table"}   # 自動最佳化時依附在床 / 沙發旁
PERSON_HALF = 25                            # 動線檢查：人通過需要 50cm 寬
GRID = 5                                    # 動線網格解析度 (cm)
MAX_CELLS = 250000                          # 動線網格上限，超過就把網格放大

PENALTY = {"error": 15, "warning": 6, "high": 12, "medium": 6, "low": 2}
LEVEL_ZH = {"error": "嚴重", "warning": "注意", "high": "高", "medium": "中", "low": "低"}


# ---------------------------------------------------------------- 輸入驗證
MAX_ROOM = 100000      # cm，超過視為輸入錯誤（1 公里）
MIN_ROOM = 50          # cm


def num(v, label, positive=False):
    """轉成有限的數字；不合法就丟出看得懂的 ValueError"""
    if isinstance(v, bool) or v is None or isinstance(v, (list, dict)):
        raise ValueError("{} 必須是數字，目前是 {!r}".format(label, v))
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise ValueError("{} 必須是數字，目前是 {!r}".format(label, v))
    if not math.isfinite(x):
        raise ValueError("{} 不能是 NaN 或無限大".format(label))
    if positive and x <= 0:
        raise ValueError("{} 必須大於 0，目前是 {}".format(label, v))
    return x


def need(d, key, label):
    if not isinstance(d, dict):
        raise ValueError("{} 必須是物件（大括號 {{ }}），目前是 {!r}".format(label, d))
    if key not in d:
        raise ValueError("{} 缺少欄位 {}".format(label, key))
    return d[key]


def room_size(data):
    if not isinstance(data, dict):
        raise ValueError("輸入檔最外層必須是物件（大括號 { }）")
    room = need(data, "room", "輸入檔")
    W = num(need(room, "width", "room"), "room.width", True)
    D = num(need(room, "depth", "room"), "room.depth", True)
    for v, k in ((W, "width"), (D, "depth")):
        if v < MIN_ROOM or v > MAX_ROOM:
            raise ValueError("room.{} 必須介於 {} 到 {} cm，目前是 {:g}".format(k, MIN_ROOM, MAX_ROOM, v))
    return room, W, D


def as_list(data, key):
    v = data.get(key, [])
    if v is None:
        return []
    if not isinstance(v, list):
        raise ValueError("{} 必須是清單（中括號 [ ]）".format(key))
    return v


# ---------------------------------------------------------------- 幾何工具
def make_item(raw, idx=0):
    label = "furniture[{}]".format(idx)
    t = need(raw, "type", label)
    if not isinstance(t, str) or t not in CATALOG:
        raise ValueError("未知的家具類型：{}（可用 catalog 指令查詢）".format(t))
    name, cw, cd, req, tall, _ = CATALOG[t]
    width = num(raw.get("width", cw), label + ".width", True)
    depth = num(raw.get("depth", cd), label + ".depth", True)
    facing = raw.get("facing", "S")
    if not isinstance(facing, str) or facing not in DIRS:
        raise ValueError("{} 的 facing 必須是 N/S/E/W，目前是 {!r}".format(t, facing))
    w, d = (width, depth) if facing in ("N", "S") else (depth, width)
    return {
        "id": str(raw.get("id", "{}_{}".format(t, idx))),
        "type": t,
        "name": str(raw.get("name", name)),
        "x": num(need(raw, "x", label), label + ".x"), "y": num(need(raw, "y", label), label + ".y"),
        "w": w, "d": d,
        "width": width, "depth": depth, "facing": facing,
        "mirror": bool(raw.get("mirror", t in MIRROR_TYPES)),
        "tall": bool(raw.get("tall", tall)),
        "req": num(raw.get("clearance", req), label + ".clearance"),
    }


def rect(it):
    return (it["x"], it["y"], it["x"] + it["w"], it["y"] + it["d"])


def overlap(a, b, eps=0.01):
    return a[0] < b[2] - eps and b[0] < a[2] - eps and a[1] < b[3] - eps and b[1] < a[3] - eps


def center(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def side_span(r, direction):
    """與 direction 垂直方向上的範圍"""
    return (r[0], r[2]) if direction in ("N", "S") else (r[1], r[3])


def span_overlap(a, b):
    return min(a[1], b[1]) - max(a[0], b[0])


def zone(r, direction, depth, span=None):
    """r 在 direction 那一側、深度 depth 的矩形區域"""
    x1, y1, x2, y2 = r
    if span:
        if direction in ("N", "S"):
            x1, x2 = span
        else:
            y1, y2 = span
    if direction == "N":
        return (x1, y1 - depth, x2, y1)
    if direction == "S":
        return (x1, y2, x2, y2 + depth)
    if direction == "E":
        return (x2, y1, x2 + depth, y2)
    return (x1 - depth, y1, x1, y2)


def inner_zone(r, direction, depth):
    """r 內部、靠 direction 那一側、深度 depth 的矩形"""
    z = zone(r, direction, -depth)
    return (min(z[0], z[2]), min(z[1], z[3]), max(z[0], z[2]), max(z[1], z[3]))


def wall_gap(r, direction, room):
    W, D = room
    return {"N": r[1], "S": D - r[3], "E": W - r[2], "W": r[0]}[direction]


def free_distance(r, direction, obstacles, room, span=None):
    """從 r 的某一側往外量，到最近障礙物或牆的距離"""
    sp = span or side_span(r, direction)
    best, who = wall_gap(r, direction, room), "牆"
    for name, o in obstacles:
        osp = (o[0], o[2]) if direction in ("N", "S") else (o[1], o[3])
        if span_overlap(sp, osp) <= 0.01:
            continue
        if direction == "N" and o[3] <= r[1] + 0.01:
            dist = r[1] - o[3]
        elif direction == "S" and o[1] >= r[3] - 0.01:
            dist = o[1] - r[3]
        elif direction == "E" and o[0] >= r[2] - 0.01:
            dist = o[0] - r[2]
        elif direction == "W" and o[2] <= r[0] + 0.01:
            dist = r[0] - o[2]
        else:
            continue
        if dist < best:
            best, who = dist, name
    return best, who


def opening_span(o):
    return (float(o["offset"]), float(o["offset"]) + float(o["width"]))


def wall_point(wall, t, room):
    W, D = room
    return {"N": (t, 0.0), "S": (t, D), "W": (0.0, t), "E": (W, t)}[wall]


def opening_center(o, room):
    a, b = opening_span(o)
    return wall_point(o["wall"], (a + b) / 2.0, room)


def corridor(o, room):
    """從門窗往室內直直看過去的通道"""
    W, D = room
    a, b = opening_span(o)
    return (a, 0, b, D) if o["wall"] in ("N", "S") else (0, a, W, b)


def door_swing(o, room):
    if o.get("swing") == "sliding":
        return None
    W, D = room
    a, b = opening_span(o)
    s = b - a
    return {"N": (a, 0, b, s), "S": (a, D - s, b, D),
            "W": (0, a, s, b), "E": (W - s, a, W, b)}[o["wall"]]


def load_layout(data):
    room, W, D = room_size(data)
    items = [make_item(raw, i) for i, raw in enumerate(as_list(data, "furniture"))]
    seen = set()
    for it in items:
        if it["id"] in seen:
            raise ValueError("家具 id 重複：{}（id 必須唯一，或省略讓程式自動編號）".format(it["id"]))
        seen.add(it["id"])
    openings = []
    for k, o in enumerate(as_list(data, "openings")):
        label = "openings[{}]".format(k)
        if (not isinstance(o, dict) or not isinstance(o.get("wall"), str) or o["wall"] not in DIRS
                or o.get("type") not in ("door", "window")):
            raise ValueError("{} 需要 type=door/window 與 wall=N/S/E/W：{}".format(label, o))
        o = dict(o)
        o["offset"] = num(need(o, "offset", label), label + ".offset")
        o["width"] = num(need(o, "width", label), label + ".width", True)
        openings.append(o)
    beams = []
    for k, b in enumerate(as_list(data, "beams")):
        label = "beams[{}]".format(k)
        x, y = num(need(b, "x", label), label + ".x"), num(need(b, "y", label), label + ".y")
        w, d = num(need(b, "w", label), label + ".w", True), num(need(b, "d", label), label + ".d", True)
        beams.append((x, y, x + w, y + d))
    return {"room": (W, D), "name": str(room.get("name", "房間")), "items": items,
            "openings": openings, "beams": beams}


# ---------------------------------------------------------------- 檢查
def issue(cat, level, code, msg, fix, at):
    return {"category": cat, "level": level, "code": code, "message": msg, "fix": fix,
            "at": [round(at[0], 1), round(at[1], 1)]}


def check_ergonomics(L):
    W, D = L["room"]
    items = L["items"]
    doors = [o for o in L["openings"] if o["type"] == "door"]
    windows = [o for o in L["openings"] if o["type"] == "window"]
    out = []
    rects = {it["id"]: rect(it) for it in items}

    for it in items:
        r = rects[it["id"]]
        if r[0] < -0.01 or r[1] < -0.01 or r[2] > W + 0.01 or r[3] > D + 0.01:
            out.append(issue("人體工學", "error", "OUT_OF_ROOM", "{} 超出房間範圍".format(it["name"]),
                             "調整位置或換小一號的尺寸", center(r)))
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if overlap(rects[a["id"]], rects[b["id"]]):
                out.append(issue("人體工學", "error", "OVERLAP", "{} 與 {} 重疊".format(a["name"], b["name"]),
                                 "移開其中一件家具", center(rects[a["id"]])))
    for dr in doors:
        sw = door_swing(dr, L["room"])
        if not sw:
            continue
        for it in items:
            if overlap(sw, rects[it["id"]]):
                out.append(issue("人體工學", "error", "DOOR_BLOCKED",
                                 "{} 擋到{}牆房門的開門範圍".format(it["name"], WALL_ZH[dr["wall"]]),
                                 "家具離開門片旋轉範圍（約等於門寬），或改用拉門", center(sw)))

    for it in items:
        r = rects[it["id"]]
        others = [(o["name"], rects[o["id"]]) for o in items if o is not it]
        if it["type"] in BEDS:
            head = OPP[it["facing"]]
            dists = []
            for side in PERP[it["facing"]]:
                # 只看床尾 2/3，床頭旁邊放床頭櫃是正常的
                lo, hi = side_span(r, side)
                span = (lo + (hi - lo) / 3.0, hi) if head in ("N", "W") else (lo, hi - (hi - lo) / 3.0)
                dist, who = free_distance(r, side, others, L["room"], span)
                dists.append((dist, side, who))
            dists.sort(reverse=True)
            if dists[0][0] < 60:
                lvl = "error" if dists[0][0] < 45 else "warning"
                out.append(issue("人體工學", lvl, "BED_SIDE",
                                 "{} 兩側走道都不足 60cm（最寬 {:.0f}cm）".format(it["name"], dists[0][0]),
                                 "讓床至少一側留 60cm 以上走道", center(r)))
            elif it["type"] != "bed_single" and dists[1][0] < 45:
                out.append(issue("人體工學", "warning", "BED_ONE_SIDE",
                                 "{} 一側只剩 {:.0f}cm，睡內側的人上下床不便".format(it["name"], dists[1][0]),
                                 "雙人床兩側建議各留 45cm 以上", center(zone(r, dists[1][1], 20))))
        elif it["type"] == "dining_table":
            for side in DIRS:
                dist, who = free_distance(r, side, others, L["room"])
                if dist < 60:
                    out.append(issue("人體工學", "warning", "DINING_CLEAR",
                                     "{} {}側只有 {:.0f}cm，椅子拉不開".format(it["name"], WALL_ZH[side], dist),
                                     "餐桌四周建議留 60cm 以上（有人走動處 90cm）", center(zone(r, side, 20))))
        elif it["req"] > 0:
            dist, who = free_distance(r, it["facing"], others, L["room"])
            if dist < it["req"]:
                lvl = "error" if dist < it["req"] * 0.7 else "warning"
                out.append(issue("人體工學", lvl, "FRONT_CLEAR",
                                 "{} 前方只有 {:.0f}cm（被{}擋住，建議 {:.0f}cm）".format(it["name"], dist, who, it["req"]),
                                 "拉開前方空間或移動{}".format(who), center(zone(r, it["facing"], max(dist, 10)))))

    tvs = [it for it in items if it["type"] == "tv_cabinet"]
    for sofa in [it for it in items if it["type"] == "sofa"]:
        if not tvs:
            break
        sr = rects[sofa["id"]]
        sight = zone(sr, sofa["facing"], max(W, D))
        facing_tv = [tv for tv in tvs if tv["facing"] == OPP[sofa["facing"]] and overlap(sight, rects[tv["id"]])]
        if not facing_tv:
            out.append(issue("人體工學", "warning", "SOFA_TV", "坐在沙發上沒有正對電視",
                             "沙發與電視櫃面對面擺放", center(sr)))
            continue
        dist, _ = free_distance(sr, sofa["facing"], [("tv", rects[t["id"]]) for t in facing_tv], L["room"])
        if dist < 180 or dist > 450:
            out.append(issue("人體工學", "warning", "TV_DISTANCE",
                             "沙發到電視 {:.0f}cm，觀看距離不理想（建議 180–450cm，約螢幕對角線 3 倍）".format(dist),
                             "調整沙發或電視位置", center(zone(sr, sofa["facing"], min(dist, 100)))))

    for it in items:
        if not it["tall"] or it["type"] == "mirror":
            continue
        r = rects[it["id"]]
        for wd in windows:
            if wall_gap(r, wd["wall"], L["room"]) <= 10 and span_overlap(side_span(r, wd["wall"]), opening_span(wd)) > 0:
                out.append(issue("人體工學", "warning", "WINDOW_BLOCKED",
                                 "{} 擋住{}牆的窗戶".format(it["name"], WALL_ZH[wd["wall"]]),
                                 "高櫃避開窗戶，改放低矮家具", opening_center(wd, L["room"])))
    return out


def check_paths(L):
    """從房門出發，用網格 BFS 確認每件家具的使用區走得到"""
    W, D = L["room"]
    grid = GRID
    while (W / grid) * (D / grid) > MAX_CELLS:   # 大房間放大網格，避免跑太久或吃光記憶體
        grid *= 2
    nx, ny = max(1, int(W // grid)), max(1, int(D // grid))
    blocked = [[False] * ny for _ in range(nx)]
    R = PERSON_HALF
    rects = [rect(it) for it in L["items"]]
    for i in range(nx):
        cx = i * grid + grid / 2.0
        for j in range(ny):
            cy = j * grid + grid / 2.0
            if cx < R or cy < R or cx > W - R or cy > D - R:   # 人體寬 50cm，身體不能嵌進牆裡
                blocked[i][j] = True
                continue
            for r in rects:
                dx = max(r[0] - cx, 0, cx - r[2])
                dy = max(r[1] - cy, 0, cy - r[3])
                if dx * dx + dy * dy < R * R:
                    blocked[i][j] = True
                    break

    def cell(p):
        return min(max(int(p[0] // grid), 0), nx - 1), min(max(int(p[1] // grid), 0), ny - 1)

    doors = [o for o in L["openings"] if o["type"] == "door" and o.get("kind") != "bathroom"]
    doors = doors or [o for o in L["openings"] if o["type"] == "door"]
    if not doors:
        return []
    seen = [[False] * ny for _ in range(nx)]
    q = deque()
    for dr in doors:
        cx, cy = opening_center(dr, L["room"])
        vx, vy = DIRS[OPP[dr["wall"]]]
        si, sj = cell((cx + vx * 40, cy + vy * 40))
        # 起點被擋住時，往附近找空格
        for rad in range(0, max(8, int(80 // grid))):
            found = None
            for di in range(-rad, rad + 1):
                for dj in range(-rad, rad + 1):
                    a, b = si + di, sj + dj
                    if 0 <= a < nx and 0 <= b < ny and not blocked[a][b]:
                        found = (a, b)
                        break
                if found:
                    break
            if found:
                seen[found[0]][found[1]] = True
                q.append(found)
                break
    while q:
        i, j = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < nx and 0 <= b < ny and not blocked[a][b] and not seen[a][b]:
                seen[a][b] = True
                q.append((a, b))

    def reachable(z):
        i1, j1 = cell((max(z[0], 0), max(z[1], 0)))
        i2, j2 = cell((min(z[2], W - 0.1), min(z[3], D - 0.1)))
        return any(seen[i][j] for i in range(i1, i2 + 1) for j in range(j1, j2 + 1))

    out = []
    for it in L["items"]:
        r = rect(it)
        if it["type"] in BEDS:
            zones = [zone(r, s, 60) for s in PERP[it["facing"]]] + [zone(r, it["facing"], 60)]
        elif it["type"] == "dining_table":
            zones = [zone(r, s, 60) for s in DIRS]
        elif it["req"] > 0:
            zones = [zone(r, it["facing"], max(it["req"], 60))]
        else:
            continue
        if not any(reachable(z) for z in zones):
            out.append(issue("人體工學", "error", "UNREACHABLE",
                             "從房門走不到 {} 的使用區（通道小於 50cm）".format(it["name"]),
                             "整理出一條 50cm 以上、從門口到該家具前方的走道", center(zones[0])))
    return out


def check_fengshui(L):
    W, D = L["room"]
    items = L["items"]
    doors = [o for o in L["openings"] if o["type"] == "door"]
    windows = [o for o in L["openings"] if o["type"] == "window"]
    out = []

    for bed in [it for it in items if it["type"] in BEDS]:
        r = rect(bed)
        head = OPP[bed["facing"]]
        gap = wall_gap(r, head, L["room"])
        if gap > 15:
            out.append(issue("風水", "medium", "BED_NO_BACKING", "床頭沒有靠牆（床頭無靠）",
                             "床頭貼實牆，或加高床頭板", center(zone(r, head, 1))))
        for wd in windows:
            if wd["wall"] == head and gap <= 30 and span_overlap(side_span(r, head), opening_span(wd)) > 0:
                out.append(issue("風水", "high", "BED_HEAD_WINDOW", "床頭靠窗（頭部無靠、易受風擾）",
                                 "床頭改靠實牆；無法移動時加厚窗簾與實木床頭板", opening_center(wd, L["room"])))
        for dr in doors:
            if not overlap(corridor(dr, L["room"]), r):
                continue
            at = opening_center(dr, L["room"])
            if dr.get("kind") == "bathroom":
                out.append(issue("風水", "high", "BATH_DOOR_BED", "廁所門正對床",
                                 "床移開廁所門的直線範圍；廁所門保持關閉並掛門簾", at))
            elif dr["wall"] == bed["facing"]:
                out.append(issue("風水", "high", "DOOR_FACES_BED", "床尾正對房門（門沖床）",
                                 "床橫向錯開房門；或在床尾與門之間放屏風、矮櫃", at))
            elif dr["wall"] == head:
                out.append(issue("風水", "medium", "DOOR_AT_HEAD", "床頭緊鄰房門，開門即到頭部",
                                 "床往房門反方向移，讓床頭避開門的直線", at))
            else:
                out.append(issue("風水", "medium", "DOOR_SEES_BED", "一開門就直視床鋪（隱私不足）",
                                 "床錯開門的直線，或以衣櫃、屏風遮擋視線", at))
        head_third = inner_zone(r, head, bed["depth"] / 3.0)
        for bm in L["beams"]:
            if overlap(bm, r):
                if overlap(bm, head_third):
                    out.append(issue("風水", "high", "BEAM_OVER_HEAD", "橫樑壓在床頭（樑壓床）",
                                     "床移開橫樑下方；或以天花板包覆橫樑", center(bm)))
                else:
                    out.append(issue("風水", "medium", "BEAM_OVER_BED", "橫樑經過床鋪上方",
                                     "床移開橫樑下方；或以天花板包覆橫樑", center(bm)))
        for m in items:
            if not m["mirror"] or m is bed:
                continue
            mr = rect(m)
            sight = zone(mr, m["facing"], max(W, D))
            if overlap(sight, r):
                out.append(issue("風水", "high", "MIRROR_FACES_BED", "{}的鏡面正對床".format(m["name"]),
                                 "鏡子轉向避開床，或改放衣櫃門內側", center(mr)))

    for it in items:
        if it["type"] not in ("desk", "dresser", "sofa"):
            continue
        r = rect(it)
        cx, cy = center(r)
        if it["type"] == "sofa":
            look = it["facing"]
            seat = (cx, cy)
        else:
            look = OPP[it["facing"]]
            fx, fy = DIRS[it["facing"]]
            half = (r[3] - r[1]) / 2.0 if it["facing"] in ("N", "S") else (r[2] - r[0]) / 2.0
            seat = (cx + fx * (half + 30), cy + fy * (half + 30))
        lx, ly = DIRS[look]
        for dr in doors:
            px, py = opening_center(dr, L["room"])
            vx, vy = px - seat[0], py - seat[1]
            n = math.hypot(vx, vy) or 1
            if (lx * vx + ly * vy) / n < -0.5:
                out.append(issue("風水", "medium", "BACK_TO_DOOR", "坐在{}時背對房門（背門而坐）".format(it["name"]),
                                 "調整成能用眼角看到門的方向；或在椅背後方放高背椅、屏風", seat))
                break
        if it["type"] == "sofa":
            back = OPP[it["facing"]]
            if wall_gap(r, back, L["room"]) > 15:
                out.append(issue("風水", "medium", "SOFA_NO_BACKING", "沙發背後沒有靠牆（背後無靠）",
                                 "沙發背貼牆；無法時在後方放矮櫃當靠山", center(zone(r, back, 1))))
            elif any(wd["wall"] == back and span_overlap(side_span(r, back), opening_span(wd)) > 0 for wd in windows):
                out.append(issue("風水", "medium", "SOFA_BACK_WINDOW", "沙發背後是窗戶（背後無靠）",
                                 "沙發改靠實牆；無法移動時加厚窗簾或在窗前放矮櫃", center(zone(r, back, 1))))
        if it["type"] == "desk" and wall_gap(r, look, L["room"]) <= 10:
            has_window = any(wd["wall"] == look and span_overlap(side_span(r, look), opening_span(wd)) > 0 for wd in windows)
            if not has_window:
                out.append(issue("風水", "low", "DESK_FACES_WALL", "書桌面壁，視野受限",
                                 "可接受；若空間允許，書桌側向窗戶或背後靠牆面向房間較佳", center(r)))

    for di, dr in enumerate(doors):
        if dr.get("kind") == "bathroom":
            continue
        for oi, other in enumerate(doors + windows):
            if other is dr or other["wall"] != OPP[dr["wall"]]:
                continue
            if span_overlap(opening_span(dr), opening_span(other)) > 0:
                if other["type"] == "window":
                    out.append(issue("風水", "medium", "DOOR_WINDOW_LINE", "房門與窗戶成一直線（穿堂煞）",
                                     "在門窗之間放屏風、櫃子或掛窗簾，讓氣流轉折", center(corridor(dr, L["room"]))))
                elif other.get("kind") != "bathroom" and di < oi:   # 兩扇都不是廁所門才算；用清單順序去重
                    out.append(issue("風水", "low", "DOOR_TO_DOOR", "兩扇門正對（門對門）",
                                     "平時關上其中一扇或掛門簾", center(corridor(dr, L["room"]))))
    return out


def evaluate(L, with_path=True):
    issues = check_ergonomics(L)
    if with_path:
        issues += check_paths(L)
    issues += check_fengshui(L)
    ergo = max(0, 100 - sum(PENALTY[i["level"]] for i in issues if i["category"] == "人體工學"))
    fs = max(0, 100 - sum(PENALTY[i["level"]] for i in issues if i["category"] == "風水"))
    return {"score": round(ergo * 0.6 + fs * 0.4, 1), "ergonomics": ergo, "fengshui": fs, "issues": issues}


# ---------------------------------------------------------------- 最佳化
def place_on_wall(t, wall, pos, room, size=None):
    _, cw, cd = CATALOG[t][:3]
    width, depth = (size or (cw, cd))
    W, D = room
    facing = OPP[wall]
    w, d = (width, depth) if facing in ("N", "S") else (depth, width)
    x, y = {"N": (pos, 0), "S": (pos, D - d), "W": (0, pos), "E": (W - w, pos)}[wall]
    return {"type": t, "x": x, "y": y, "facing": facing, "width": width, "depth": depth}


def attach(t, host, room, size):
    """床頭櫃放在床頭兩側、茶几放在沙發前 40cm"""
    width, depth = size
    hr = rect(make_item(host))
    f = host["facing"]
    w, d = (width, depth) if f in ("N", "S") else (depth, width)
    res = []
    if t == "nightstand":
        head = OPP[f]
        if f in ("N", "S"):
            y = hr[1] if head == "N" else hr[3] - d
            res = [(hr[0] - w, y), (hr[2], y)]
        else:
            x = hr[0] if head == "W" else hr[2] - w
            res = [(x, hr[1] - d), (x, hr[3])]
    elif t == "coffee_table":
        cx, cy = center(hr)
        gap = 40
        res = [{"S": (cx - w / 2, hr[3] + gap), "N": (cx - w / 2, hr[1] - gap - d),
                "E": (hr[2] + gap, cy - d / 2), "W": (hr[0] - gap - w, cy - d / 2)}[f]]
    return [{"type": t, "x": x, "y": y, "facing": f, "width": width, "depth": depth} for x, y in res]


def build(spec, genome):
    room = (float(spec["room"]["width"]), float(spec["room"]["depth"]))
    raws, placed = [], []
    anchors = [s for s in spec["_expanded"] if s["type"] not in ATTACHED]
    for s, (wall, pos) in zip(anchors, genome):
        raw = place_on_wall(s["type"], wall, pos, room, s["size"])
        r = rect(make_item(raw))
        if r[0] < 0 or r[1] < 0 or r[2] > room[0] or r[3] > room[1]:
            return None
        if any(overlap(r, p) for p in placed):
            return None
        raws.append(raw)
        placed.append(r)
    for s in [s for s in spec["_expanded"] if s["type"] in ATTACHED]:
        host_types = BEDS if s["type"] == "nightstand" else {"sofa"}
        hosts = [r for r in raws if r["type"] in host_types]
        if not hosts:
            continue
        for cand in attach(s["type"], hosts[0], room, s["size"]):
            r = rect(make_item(cand))
            if r[0] >= 0 and r[1] >= 0 and r[2] <= room[0] and r[3] <= room[1] and not any(overlap(r, p) for p in placed):
                if sum(1 for x in raws if x["type"] == s["type"]) < s["_limit"]:
                    raws.append(cand)
                    placed.append(r)
    data = dict(spec)
    data["furniture"] = raws
    return data


def random_gene(spec, s, rng):
    W, D = float(spec["room"]["width"]), float(spec["room"]["depth"])
    walls = s.get("walls") or ["N", "S", "E", "W"]
    wall = rng.choice(walls)
    width = s["size"][0]
    length = W if wall in ("N", "S") else D
    if width > length:
        return wall, 0
    return wall, rng.randrange(0, int(length - width) + 1, 5)


def optimize(spec, top=3, seed=None, iters=3000):
    if top < 1:
        raise ValueError("--top 必須 >= 1")
    if iters < 1:
        raise ValueError("--iters 必須 >= 1")
    room_size(spec)
    rng = random.Random(seed)
    expanded = []
    for k, s in enumerate(as_list(spec, "items")):
        t = need(s, "type", "items[{}]".format(k))
        if not isinstance(t, str) or t not in CATALOG:
            raise ValueError("未知的家具類型：{}".format(t))
        size = (num(s.get("width", CATALOG[t][1]), "items[{}].width".format(k), True),
                num(s.get("depth", CATALOG[t][2]), "items[{}].depth".format(k), True))
        n = int(num(s.get("count", 1), "items[{}].count".format(k)))
        if n < 0:
            raise ValueError("items[{}].count 不能是負數".format(k))
        walls = s.get("walls")
        if walls is not None and (not isinstance(walls, list) or any(w not in DIRS for w in walls)):
            raise ValueError("items[{}].walls 必須是 N/S/E/W 的清單".format(k))
        if t in ATTACHED:
            expanded.append({"type": t, "size": size, "_limit": n})
        else:
            for _ in range(n):
                expanded.append({"type": t, "size": size, "walls": s.get("walls")})
    spec = dict(spec)
    spec["_expanded"] = expanded
    anchors = [s for s in expanded if s["type"] not in ATTACHED]
    if not anchors:
        raise ValueError("items 至少要有一件主要家具（床頭櫃、茶几只能依附在床、沙發旁）")

    def score(g):
        data = build(spec, g)
        if data is None:
            return None, None
        return evaluate(load_layout(data), with_path=False)["score"], data

    pool = []
    for _ in range(iters):
        g = [random_gene(spec, s, rng) for s in anchors]
        sc, data = score(g)
        if sc is not None:
            pool.append((sc, g))
    if not pool:
        raise ValueError("找不到任何放得下的配置，請確認房間尺寸或減少家具")
    pool.sort(key=lambda p: -p[0])

    # 爬山法微調：一次移動一件家具
    refined = []
    for sc, g in pool[:15]:
        for _ in range(150):
            g2 = list(g)
            k = rng.randrange(len(g2))
            if rng.random() < 0.3:
                g2[k] = random_gene(spec, anchors[k], rng)
            else:
                g2[k] = (g2[k][0], max(0, g2[k][1] + rng.choice([-30, -15, -5, 5, 15, 30])))
            sc2, _ = score(g2)
            if sc2 is not None and sc2 >= sc:
                sc, g = sc2, g2
        refined.append((sc, g))

    # 完整評估（含動線），挑出配置方式不同的前幾名
    results, seen = [], set()
    for sc, g in sorted(refined, key=lambda p: -p[0]):
        data = build(spec, g)
        res = evaluate(load_layout(data))
        results.append((res["score"], tuple(w for w, _ in g), data, res))
    results.sort(key=lambda p: -p[0])
    chosen = []
    for sc, sig, data, res in results:
        if sig in seen:
            continue
        seen.add(sig)
        chosen.append((data, res))
        if len(chosen) == top:
            break
    for sc, sig, data, res in results:
        if len(chosen) >= top:
            break
        if all(data is not c[0] for c in chosen):
            chosen.append((data, res))
    for data, res in chosen:
        res["notes"] = []
        for s in [s for s in expanded if s["type"] in ATTACHED]:
            got = sum(1 for r in data["furniture"] if r["type"] == s["type"])
            if got < s["_limit"]:
                res["notes"].append("{} 需要 {} 個，這個方案只放得下 {} 個".format(CATALOG[s["type"]][0], s["_limit"], got))
        data.pop("_expanded", None)
        data.pop("items", None)
    return chosen


# ---------------------------------------------------------------- 繪圖
def render_svg(L, result, path, title):
    W, D = L["room"]
    s = 560.0 / max(W, D)
    m = 70
    issues = result["issues"]
    legend_h = 40 + 22 * len(issues)
    vw, vh = W * s + m * 2, D * s + m * 2 + legend_h
    X = lambda v: m + v * s
    Y = lambda v: m + v * s
    e = html.escape
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {:.0f} {:.0f}" width="{:.0f}" height="{:.0f}" '
           'font-family="Microsoft JhengHei, PingFang TC, Noto Sans TC, sans-serif">'.format(vw, vh, vw, vh),
           '<rect width="100%" height="100%" fill="#ffffff"/>',
           '<text x="{}" y="28" font-size="18" font-weight="bold" fill="#222">{}</text>'.format(m, e(title)),
           '<text x="{}" y="50" font-size="13" fill="#555">總分 {} ｜ 人體工學 {} ｜ 風水 {}</text>'.format(
               m, result["score"], result["ergonomics"], result["fengshui"]),
           '<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" fill="#faf7f2" stroke="#333" stroke-width="6"/>'.format(
               X(0), Y(0), W * s, D * s)]
    # 尺寸
    out.append('<text x="{:.1f}" y="{:.1f}" font-size="12" fill="#666" text-anchor="middle">{:.0f} cm</text>'.format(
        X(W / 2), Y(D) + 22, W))
    out.append('<text x="{:.1f}" y="{:.1f}" font-size="12" fill="#666" text-anchor="middle" '
               'transform="rotate(-90 {:.1f} {:.1f})">{:.0f} cm</text>'.format(X(0) - 18, Y(D / 2), X(0) - 18, Y(D / 2), D))
    # 指北針
    nx_, ny_ = X(W) + 35, Y(0) + 5
    out.append('<path d="M{0:.1f},{1:.1f} l-8,22 l8,-6 l8,6 z" fill="#333"/>'
               '<text x="{0:.1f}" y="{2:.1f}" font-size="12" text-anchor="middle" fill="#333">N</text>'.format(nx_, ny_, ny_ + 36))
    # 樑
    for b in L["beams"]:
        out.append('<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" fill="#b0503f" fill-opacity="0.08" '
                   'stroke="#b0503f" stroke-dasharray="6 4"/>'.format(X(b[0]), Y(b[1]), (b[2] - b[0]) * s, (b[3] - b[1]) * s))
        out.append('<text x="{:.1f}" y="{:.1f}" font-size="11" fill="#b0503f">樑</text>'.format(X(b[0]) + 3, Y(b[1]) + 12))
    # 家具
    for it in L["items"]:
        r = rect(it)
        color = CATALOG[it["type"]][5]
        out.append('<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" rx="3" fill="{}" stroke="#555" stroke-width="1.2"/>'.format(
            X(r[0]), Y(r[1]), it["w"] * s, it["d"] * s, color))
        # 正面標示（粗線）
        f = it["facing"]
        x1, y1, x2, y2 = {"N": (r[0], r[1], r[2], r[1]), "S": (r[0], r[3], r[2], r[3]),
                          "E": (r[2], r[1], r[2], r[3]), "W": (r[0], r[1], r[0], r[3])}[f]
        out.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#333" stroke-width="3"/>'.format(
            X(x1), Y(y1), X(x2), Y(y2)))
        if it["type"] in BEDS:   # 枕頭
            head = OPP[f]
            hz = inner_zone(r, head, 25)
            out.append('<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" fill="#ffffff" stroke="#8aa" rx="4"/>'.format(
                X(hz[0]) + 3, Y(hz[1]) + 3, (hz[2] - hz[0]) * s - 6, (hz[3] - hz[1]) * s - 6))
        cx, cy = center(r)
        fs = 12 if min(it["w"], it["d"]) * s > 30 else 9
        out.append('<text x="{:.1f}" y="{:.1f}" font-size="{}" text-anchor="middle" fill="#222">{}</text>'.format(
            X(cx), Y(cy) + 4, fs, e(it["name"])))
    # 門窗
    for o in L["openings"]:
        a, b = opening_span(o)
        p1, p2 = wall_point(o["wall"], a, L["room"]), wall_point(o["wall"], b, L["room"])
        out.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#faf7f2" stroke-width="8"/>'.format(
            X(p1[0]), Y(p1[1]), X(p2[0]), Y(p2[1])))
        if o["type"] == "window":
            out.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="#3a8fc7" stroke-width="5"/>'.format(
                X(p1[0]), Y(p1[1]), X(p2[0]), Y(p2[1])))
        else:
            col = "#9b59b6" if o.get("kind") == "bathroom" else "#c0392b"
            u = (1, 0) if o["wall"] in ("N", "S") else (0, 1)
            v = DIRS[OPP[o["wall"]]]
            wdt = b - a
            if o.get("swing") == "sliding":
                out.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="3"/>'.format(
                    X(p1[0]), Y(p1[1]), X(p2[0]), Y(p2[1]), col))
            else:
                leaf = (p1[0] + v[0] * wdt, p1[1] + v[1] * wdt)
                out.append('<line x1="{:.1f}" y1="{:.1f}" x2="{:.1f}" y2="{:.1f}" stroke="{}" stroke-width="2"/>'.format(
                    X(p1[0]), Y(p1[1]), X(leaf[0]), Y(leaf[1]), col))
                pts = []
                for k in range(13):
                    th = math.pi / 2 * k / 12
                    px = p1[0] + wdt * (math.cos(th) * u[0] + math.sin(th) * v[0])
                    py = p1[1] + wdt * (math.cos(th) * u[1] + math.sin(th) * v[1])
                    pts.append("{:.1f},{:.1f}".format(X(px), Y(py)))
                out.append('<polyline points="{}" fill="none" stroke="{}" stroke-dasharray="3 3"/>'.format(" ".join(pts), col))
            label = "廁所門" if o.get("kind") == "bathroom" else "門"
            c = opening_center(o, L["room"])
            out.append('<text x="{:.1f}" y="{:.1f}" font-size="11" fill="{}" text-anchor="middle">{}</text>'.format(
                X(c[0]) - v[0] * 14, Y(c[1]) - v[1] * 14 + 4, col, label))
    # 問題標記（避開家具名稱與其他標記）
    labels = [(X(center(rect(it))[0]), Y(center(rect(it))[1])) for it in L["items"]]
    used = []
    for k, isu in enumerate(issues, 1):
        col = "#c0392b" if isu["level"] in ("error", "high") else ("#e67e22" if isu["level"] in ("warning", "medium") else "#7f8c8d")
        # 夾在房間範圍內：家具座標很大時，px += 22 會因浮點精度加不動而無限迴圈
        px = min(max(X(isu["at"][0]), X(0)), X(W))
        py = min(max(Y(isu["at"][1]), Y(0)), Y(D))
        if any(abs(px - lx) < 30 and abs(py - ly) < 14 for lx, ly in labels):
            py -= 22
        for _ in range(100):
            if not any(math.hypot(px - ux, py - uy) < 20 for ux, uy in used):
                break
            px += 22
        used.append((px, py))
        out.append('<circle cx="{:.1f}" cy="{:.1f}" r="10" fill="{}" stroke="#fff" stroke-width="2"/>'
                   '<text x="{:.1f}" y="{:.1f}" font-size="11" fill="#fff" text-anchor="middle" font-weight="bold">{}</text>'.format(
                       px, py, col, px, py + 4, k))
    # 圖例
    ly = Y(D) + 50
    out.append('<text x="{}" y="{:.1f}" font-size="14" font-weight="bold" fill="#222">{}</text>'.format(
        m, ly, "檢查結果：沒有發現問題" if not issues else "檢查結果"))
    for k, isu in enumerate(issues, 1):
        out.append('<text x="{}" y="{:.1f}" font-size="12" fill="#333">{}. [{}・{}] {}</text>'.format(
            m, ly + 22 * k, k, isu["category"], LEVEL_ZH[isu["level"]], e(isu["message"])))
    out.append("</svg>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


# ---------------------------------------------------------------- 輸出
def print_report(L, res, title):
    print("=" * 50)
    print(title)
    print("總分 {}（人體工學 {} × 60% + 風水 {} × 40%）".format(res["score"], res["ergonomics"], res["fengshui"]))
    print("-" * 50)
    for it in L["items"]:
        print("  {:<6} 位置({:.0f},{:.0f}) 尺寸 {:.0f}×{:.0f} 正面朝{}".format(
            it["name"], it["x"], it["y"], it["w"], it["d"], WALL_ZH[it["facing"]]))
    print("-" * 50)
    for note in res.get("notes", []):
        print("備註：{}".format(note))
    if not res["issues"]:
        print("沒有發現問題")
    for k, isu in enumerate(res["issues"], 1):
        print("{}. [{}・{}] {}".format(k, isu["category"], LEVEL_ZH[isu["level"]], isu["message"]))
        print("   建議：{}".format(isu["fix"]))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="空間家具配置 + 風水檢查")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("catalog")
    c = sub.add_parser("check")
    c.add_argument("input")
    c.add_argument("--svg")
    c.add_argument("--json", action="store_true")
    o = sub.add_parser("optimize")
    o.add_argument("input")
    o.add_argument("--top", type=int, default=3)
    o.add_argument("--out-dir", default="layout_out")
    o.add_argument("--seed", type=int)
    o.add_argument("--iters", type=int, default=3000)
    o.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.cmd == "catalog":
        print("{:<14}{:<8}{:>6}{:>6}{:>8}".format("type", "名稱", "寬", "深", "前方淨空"))
        for t, v in CATALOG.items():
            print("{:<14}{:<8}{:>6}{:>6}{:>8}".format(t, v[0], v[1], v[2], v[3]))
        return

    try:
        with open(a.input, encoding="utf-8-sig") as fh:   # utf-8-sig：相容記事本存的 BOM
            data = json.load(fh)
    except OSError as e:
        sys.exit("無法讀取檔案：{}".format(e))
    except ValueError as e:
        sys.exit("輸入檔不是正確的 JSON（{}）".format(e))
    try:
        run(a, data)
    except ValueError as e:
        sys.exit("輸入有誤：{}".format(e))
    except OSError as e:
        sys.exit("無法寫入檔案：{}".format(e))


def run(a, data):
    if a.cmd == "check":
        L = load_layout(data)
        res = evaluate(L)
        title = "{}｜配置檢查".format(L["name"])
        if a.svg:
            d = os.path.dirname(a.svg)
            if d:
                os.makedirs(d, exist_ok=True)
            render_svg(L, res, a.svg, title)
        if a.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print_report(L, res, title)
            if a.svg:
                print("平面圖：{}".format(a.svg))
        return

    chosen = optimize(data, top=a.top, seed=a.seed, iters=a.iters)
    os.makedirs(a.out_dir, exist_ok=True)
    summary = []
    for k, (layout_data, res) in enumerate(chosen, 1):
        L = load_layout(layout_data)
        title = "{}｜方案 {}".format(L["name"], k)
        base = os.path.join(a.out_dir, "plan_{}".format(k))
        with open(base + ".json", "w", encoding="utf-8") as fh:
            json.dump(layout_data, fh, ensure_ascii=False, indent=2)
        render_svg(L, res, base + ".svg", title)
        summary.append({"plan": k, "json": base + ".json", "svg": base + ".svg", **res})
        if not a.json:
            print_report(L, res, title)
            print("檔案：{}.json / {}.svg".format(base, base))
    if a.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
