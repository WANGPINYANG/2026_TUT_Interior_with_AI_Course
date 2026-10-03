# 王品洋的學生資料夾

- 學號：A14530026
- 日期：2026-10-03

## 今日實作：對上次作業（家具配置＋風水檢查）做暴力測試

- `furniture-layout-fengshui/tests/fuzz_layout.py`：隨機壞資料、性質檢查、鏡射對稱、optimize、CLI 的暴力測試
- `furniture-layout-fengshui/tests/ergonomics_test.py`：以 `references/ergonomics.md` 為標準答案，對走道、床邊、前方淨空等門檻做邊界掃描，並轉四個方向驗證

### 抓到並修正的問題（`scripts/layout.py`）

- 門對門（DOOR_TO_DOOR）用記憶體位址判斷，結果不穩定
- 自訂家具 id 重複時結果錯誤 → 改為拒絕
- 房間尺寸 0／負數／過小崩潰、過大跑不完 → 加驗證與自適應網格
- optimize 家具清單為空或只有依附家具時崩潰
- BOM、空檔、壞 JSON、檔案不存在等直接噴 Traceback → 改為中文錯誤訊息
- `--top`、`--iters` 無效值未擋
- 欄位缺漏或型別錯誤的輸入驗證
- 開口 wall 非字串崩潰；畫平面圖遇極大座標無限迴圈
- 動線貼牆時 43cm 就判定可通過（規範 50cm）→ 牆邊界與家具一致

### 驗證

暴力測試 4 個種子（各 2500 案例）0 個問題；人體工學邊界驗證全部與規範相符。

執行：`uv run --no-project python tests/fuzz_layout.py` 與 `tests/ergonomics_test.py`

### 已知限制

- UNREACHABLE 只要使用區有一格走得到就算通過（偏寬鬆）
- 測試只驗證不崩潰與規範門檻，不驗證風水規則本身

## 稽核報告與截圖

- `稽核報告.md`：Part 3 第 1 段「自測」報告（10 類問題，附修正前後對照）
- `screenshots/001-修正前後對照.png`：同一份壞輸入，修正前後的輸出
- `screenshots/002-測試報告.png`：圖示化測試報告（走道門檻掃描、規則卡片）

## 交叉稽核

- `稽核報告-交叉-黃建升.md`：稽核 A14530068_黃建升 的「油漆用量計算機」，發現 21 項（對方工具只跑不改，含對產生器的設定檔攻擊、變異測試，以及 course-submit、skill-usage-audit 兩個工具）
- `screenshots/003~014`；`稽核腳本/` 放可重跑的稽核程式：各項發現的重現畫面

## 總報告

- `稽核總報告-黃建升工具-21項.md`：21 項問題的整理報告（摘要、方法、總覽表、四項高嚴重度詳述、修復優先順序、限制）
- 逐項重現步驟在 `稽核報告-交叉-黃建升.md`，證據在 `screenshots/`，可重跑的程式在 `稽核腳本/`

## 修正黃建升對我的稽核（12 項）

- 我先把他報告的 12 項逐項用原始壞輸入重跑，全部屬實，再修。修法與取捨寫在 `稽核報告.md` 最後一節。
- `furniture-layout-fengshui/tests/audit_regression_test.py`：56 項回歸測試（含不能修過頭的反例），全過。

## 查驗圖庫與修正前後對照圖

- `furniture-layout-fengshui/tests/全案例查驗圖庫.html`（與 `.png`）：109 個測試案例各一張平面圖，標出期望、實際、通過或失敗；重新產生：`python tests/make_gallery.py scripts/layout.py tests/全案例查驗圖庫.html`
- `furniture-layout-fengshui/tests/修正前後對照.html`（與 `.png`）：黃建升稽核到的問題，同一份壞輸入在修正前後的平面圖對照
