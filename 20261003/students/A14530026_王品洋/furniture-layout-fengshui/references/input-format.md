# 輸入格式

## 座標系統

```
          北牆 N (y = 0)
   (0,0) ┌────────────────┐ (width, 0)
         │  x →           │
西牆 W   │  y ↓           │   東牆 E
(x = 0)  │                │   (x = width)
         └────────────────┘ (width, depth)
          南牆 S (y = depth)
```

- 單位一律是 **公分 (cm)**
- 原點在左上角（西北角）；平面圖以「上方為北」繪製。若使用者的平面圖不是上北，就把「圖面上方」當成 N，並在回覆中說明

## 共用欄位

```json
{
  "room": { "name": "主臥室", "width": 360, "depth": 330 },
  "openings": [
    { "type": "door",   "wall": "S", "offset": 20,  "width": 90 },
    { "type": "door",   "wall": "E", "offset": 250, "width": 70, "kind": "bathroom", "swing": "sliding" },
    { "type": "window", "wall": "N", "offset": 110, "width": 150 }
  ],
  "beams": [
    { "x": 0, "y": 40, "w": 360, "d": 30 }
  ]
}
```

| 欄位 | 說明 |
|------|------|
| `openings[].type` | `door` 或 `window` |
| `openings[].wall` | 在哪面牆：`N` `S` `E` `W` |
| `openings[].offset` | 從牆的起點量到開口起點的距離。北、南牆從**西端**量起；東、西牆從**北端**量起 |
| `openings[].width` | 開口寬度 |
| `openings[].kind` | 門的種類，可省略：`entry` 房門/大門、`bathroom` 廁所門 |
| `openings[].swing` | `sliding` 表示拉門（不檢查開門範圍）；預設是往室內開的推門 |
| `beams` | 天花板橫樑的平面投影矩形（x, y, w, d），沒有就省略 |

## check：檢查現有配置

再加上 `furniture`，每件家具都要給位置與朝向：

```json
"furniture": [
  { "type": "bed_double", "x": 104, "y": 0, "facing": "S" },
  { "type": "wardrobe",   "x": 300, "y": 180, "facing": "W", "width": 150 }
]
```

| 欄位 | 說明 |
|------|------|
| `type` | 家具類型，見 `python scripts/layout.py catalog` |
| `x`, `y` | 家具佔地矩形的**左上角** |
| `facing` | 家具**正面**朝向：床＝床尾方向；書桌/梳妝台＝人坐的那一側；沙發＝坐著看出去的方向；衣櫃＝門片那一側；鏡子＝鏡面方向 |
| `width`, `depth` | 可省略，覆寫型錄尺寸。width 是正面寬度，depth 是前後深度（程式會依 facing 自動旋轉） |
| `name` | 可省略，自訂顯示名稱 |
| `mirror` | 可省略，設 `true` 表示這件家具有鏡面（例如衣櫃門有鏡子） |

**旋轉提醒**：facing 是 E 或 W 時，佔地的 x 方向長度是 depth、y 方向長度是 width。例如雙人床 facing E，佔地是 188 × 152。

## optimize：自動找配置

不給位置，改給 `items` 清單：

```json
"items": [
  { "type": "bed_double" },
  { "type": "nightstand", "count": 2 },
  { "type": "wardrobe", "walls": ["E", "W"] },
  { "type": "desk", "width": 100 }
]
```

- 大部分家具會貼牆擺放、正面朝向室內
- `nightstand` 自動放在床頭兩側、`coffee_table` 自動放在沙發前 40cm
- `walls` 可限制家具只能靠哪幾面牆
- `count` 可指定數量

輸出的 `plan_N.json` 就是 check 格式，可以手動修改後再用 check 驗證。
