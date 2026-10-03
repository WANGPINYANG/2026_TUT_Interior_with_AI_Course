---
name: course-submit
description: 南應室設「設計運算與 AI 整合應用」課程的交件流程：先跑防呆檢查，通過才 commit，再 push 到自己的 fork，需要時用 gh 發 PR。觸發語：「交作業」「上傳作業」「交件」「這次上課的東西推上去」「幫我 commit 然後發 PR」。全程只用指令，不操作瀏覽器。檢查沒過就不會 commit。
---

# 課程交件

把「commit 確定沒問題再 PR」這件事固化成流程。順序是刻意的：**檢查沒過就不 commit，commit 沒成功就不 push。**

這支 skill 只住在這個 repo，不安裝到 `~/.claude/skills`——它只有上課會用到。

## 跑法

```bash
node scripts/交件.js "20260919 完成油漆用量計算機"        # 交件（不發 PR）
node scripts/交件.js "訊息" --pr                         # 交件並發 PR
node scripts/交件.js "訊息" --dry                        # 試跑，只看會做什麼
node scripts/檢查.js                                     # 只檢查不交
node scripts/測試.js                                     # 改過檢查邏輯後必跑
```

設定在 `設定.json`：repo 路徑、學號姓名、remote 名稱、日期資料夾清單。
換學期或換電腦只要改這一份。

## 全程只用指令

**不用瀏覽器點按鈕。**發 PR 走 `gh pr create`，需要：

```bash
winget install --id GitHub.cli    # 裝一次
gh auth login                     # 登入一次，要自己跑
```

`gh auth login` 涉及帳號認證，一律由本人執行。腳本只呼叫 `gh pr create`，不碰登入。

PR 標題取 commit 訊息的第一行，內文用整段訊息。
分支上已經有開著的 PR 時，新的 commit 會自動加進去，腳本會告訴你不用重開。

## 這個 repo 的特殊之處（最容易搞錯的一點）

**`origin` 不是你的，是業師的主 repo。**你的 fork 叫 `fork`。

| remote | 指向 | 能不能推 |
|---|---|---|
| `origin` | `h30190/2026_TUT_Interior_with_AI_Course` | **不能**，main 有分支保護 |
| `fork` | `jasonhuang719-lgtm/...` | 可以，交件推這裡 |

推錯地方會被拒絕，檢查器會先擋下來。

## 檢查器擋什麼

| 阻擋項 | 為什麼 |
|---|---|
| 還在 `main` 分支上 | 應該開分支，`student/A14530068-<主題>` |
| 有檔案不在你的資料夾底下 | 課程頭號雷。只准動 `<日期>/students/A14530068_黃建升/` |
| 夾帶大檔案（`.rvt`／`.skp`／影片等） | 課程規定原檔留本機 |
| 單檔超過 5 MB | 同上 |
| 疑似機密檔（`.env`／`.key`／`.pem`） | 公開 repo |
| `fork` remote 不存在 | 推不上去 |
| `fork` 與 `origin` 同網址 | 會推到別人的 repo |

提醒（不擋）：分支落後上游、沒有變更可交、有 commit 沒 push。

九條防呆每一條都有對應的失敗情境測試，`測試.js` 會建一個假 repo 實際觸發它們。
自報成功不算通過。

## 交件範圍

`git add` 的是 `設定.json` 裡列出的**所有**日期資料夾底下屬於你的那一層，
所以六次上課的資料夾會一起帶上去——哪個資料夾有東西就交哪個，不用逐次指定。

## 交件前如果上游有更新

檢查器會提醒落後幾筆。先同步再交比較不會有衝突：

```bash
git pull origin main
```

衝突了就停手找業師，不要硬解——這是課程 README 明寫的。

## 邊界

- **只動你自己的那一層。**別人的資料夾、主 repo 的 `README.md`／`LICENSE` 一律不碰，檢查器會擋。
- **不自動 merge、不改 main、不碰 `gh auth login`。**
- 交件前如果工作區有你不認得的檔案，先問清楚來源再交，不要照單全收。
