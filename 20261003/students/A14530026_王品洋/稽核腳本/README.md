# 稽核腳本（只讀取被稽核的檔案，不修改）

| 腳本 | 做什麼 |
|------|--------|
| `shoot.js` | 用 Edge 遠端除錯介面開啟**原始 HTML**，模擬鍵盤輸入與下拉選單並截圖（截圖 003～009） |
| `fuzzui.js` | 對原始 HTML 隨機操作 N 步，檢查畫面不變量（Infinity／NaN、空白被當 0、版面溢出、例外） |
| `exact.py` + `ex_run.js` | 三個公式各 10 萬組隨機輸入，與「精確分數」標準答案比對（找浮點進位誤差） |
| `prop.js` | 20 萬組隨機輸入：單調性、輸入是否被改動、同輸入兩次結果是否相同 |

執行（需 Node 與 uv；路徑請改成自己的）：

```bash
node shoot.js <msedge路徑> <油漆用量計算機.html 的 Windows 路徑> <輸出資料夾>
node fuzzui.js <msedge路徑> <html路徑> <輸出資料夾> 1500 1 640
uv run --no-project python exact.py <被稽核資料夾> <暫存資料夾> 100000
node prop.js <被稽核資料夾>
```
