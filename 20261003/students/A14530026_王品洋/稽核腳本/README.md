# 稽核腳本（只讀取被稽核的檔案，不修改）

| 腳本 | 做什麼 |
|------|--------|
| `shoot.js` | 用 Edge 遠端除錯介面開啟**原始 HTML**，模擬鍵盤輸入與下拉選單並截圖（截圖 003～009） |
| `fuzzui.js` | 對原始 HTML 隨機操作 N 步，檢查畫面不變量（Infinity／NaN、空白被當 0、版面溢出、例外） |
| `exact.py` + `ex_run.js` | 三個公式各 10 萬組隨機輸入，與「精確分數」標準答案比對（找浮點進位誤差） |
| `genfuzz.js` | 對「計算機產生器」餵 300 個隨機壞設定檔（輸出寫暫存資料夾），統計崩潰、注入、接受壞設定 |
| `mutate.js` / `mutate2.js` | 變異測試：在暫存複本上一次弄壞一處，看檢查器（`mutate.js`）與整套測試（`mutate2.js`）抓不抓得到 |
| `cs_attack.js` / `cs_fix.js` | 攻擊 `course-submit`：在暫存資料夾建假的上游與 fork（本機空倉庫），逐項測試檢查器與交件流程 |
| `sua_attack.js` | 攻擊 `skill-usage-audit`：假逐字稿與假 skill 資料夾，只在記憶體改路徑 |
| `prop.js` | 20 萬組隨機輸入：單調性、輸入是否被改動、同輸入兩次結果是否相同 |

執行（需 Node 與 uv；路徑請改成自己的）：

```bash
node shoot.js <msedge路徑> <油漆用量計算機.html 的 Windows 路徑> <輸出資料夾>
node fuzzui.js <msedge路徑> <html路徑> <輸出資料夾> 1500 1 640
uv run --no-project python exact.py <被稽核資料夾> <暫存資料夾> 100000
node prop.js <被稽核資料夾>
```
