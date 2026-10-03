# 空間家具配置 + 風水檢查 Skill

> 設計運算及 AI 整合應用｜課程作業

這是一個 Claude Skill，結合**程式運算**與 **AI 判斷**來規劃室內家具配置：

- 🧮 **運算**：Python 腳本負責量測走道淨空、用網格搜尋檢查動線、比對風水禁忌，並用隨機搜尋加爬山法自動找出高分配置
- 🤖 **AI**：Claude 負責理解使用者需求、把描述轉成座標資料、判讀結果，並補上採光、插座等腳本無法量化的建議

## 範例

用自然語言描述房間：

> 我的主臥是 360×330 公分，房門在南牆靠西側，北牆中間有一扇 150 公分的窗，天花板靠北邊有一根樑。我要放雙人床、兩個床頭櫃、衣櫃和書桌，幫我看怎麼擺比較好，也順便看風水。

| 原本的配置（58.4 分） | 自動最佳化（99.2 分） |
|:---:|:---:|
| ![檢查](examples/sample_check.svg) | ![方案](examples/plans/plan_1.svg) |
| 床頭靠窗、樑壓床、門沖床、鏡子照床、走道不足 | 只剩一個「書桌面壁」的輕微提醒 |

## 檢查項目

**人體工學**：家具超出房間、家具重疊、擋到門片開啟範圍、床邊走道、衣櫃/書桌/書櫃前方淨空、餐桌四周淨空、沙發與電視的距離、高櫃擋窗、從門口到每件家具的動線（網格 BFS 路徑搜尋）

**風水**：床頭無靠、床頭靠窗、門沖床、開門見床、廁所門對床、樑壓床、鏡子照床、背門而坐、沙發無靠或背窗、書桌面壁、穿堂煞、門對門

完整規則、傳統說法、實際理由與化解方式見 [references/fengshui-rules.md](references/fengshui-rules.md)。

## 檔案結構

```
furniture-layout-fengshui/
├── SKILL.md                  # Skill 主檔：告訴 Claude 何時使用、怎麼做
├── scripts/
│   └── layout.py             # 核心：檢查、最佳化、繪製平面圖
├── references/
│   ├── input-format.md       # 輸入 JSON 格式與座標系統
│   ├── ergonomics.md         # 家具尺寸與淨空規範
│   └── fengshui-rules.md     # 風水規則與化解方式
└── examples/
    ├── bedroom_check.json    # 範例：有問題的臥室配置
    ├── bedroom_optimize.json # 範例：臥室自動配置
    ├── living_optimize.json  # 範例：客廳自動配置（含廁所門）
    ├── sample_check.svg
    └── plans/                # optimize 的輸出範例
```

## 單獨使用腳本

只需要 Python 3，不用安裝任何套件：

```bash
python scripts/layout.py catalog
python scripts/layout.py check examples/bedroom_check.json --svg check.svg
python scripts/layout.py optimize examples/bedroom_optimize.json --top 3 --out-dir plans
```

## 安裝到 Claude

- **Claude Code**：把整個資料夾複製到 `~/.claude/skills/furniture-layout-fengshui/`
- **Claude.ai**：將資料夾壓縮成 zip，到 Settings → Capabilities → Skills 上傳

## 演算法說明

1. **檢查 (check)**：把每件家具視為矩形，依「正面朝向」計算前方到最近障礙物的距離；動線用 5cm 網格，把家具往外擴張 25cm（人的半身寬）後，從房門做廣度優先搜尋 (BFS)，確認每件家具的使用區走得到
2. **最佳化 (optimize)**：家具貼牆擺放，隨機產生 3000 組配置，淘汰重疊與超出範圍的；取前 15 名，各做 150 次爬山法微調（一次移動一件家具）；最後用完整檢查（含動線）排名，挑出靠牆方式不同的前幾名
3. **評分**：人體工學與風水各 100 分，依問題等級扣分；總分 = 人體工學 × 60% + 風水 × 40%

## 限制

- 只處理矩形房間與矩形家具
- 風水以巒頭（形勢）派的居家禁忌為主，不含理氣、八宅等需要方位與生辰的派別
- 風水為傳統文化參考，配置應以安全與實用為優先

## License

MIT
