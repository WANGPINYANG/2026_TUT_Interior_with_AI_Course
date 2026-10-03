/* 交件主流程：檢查 → commit → push 到 fork →（可選）用 gh 發 PR。
   跑法：node scripts/交件.js "commit 訊息"
        node scripts/交件.js "訊息" --pr     連 PR 一起發
        node scripts/交件.js "訊息" --dry    只看會做什麼，不真的動手

   順序是刻意的：檢查沒過就不 commit，commit 沒成功就不 push。
   全程只用指令，不操作瀏覽器。發 PR 需要 gh CLI 且已 gh auth login。 */
'use strict';

const fs = require('fs');
const { execFileSync } = require('child_process');
const 檢 = require('./檢查.js');

const 設定 = 檢.讀設定();
const 訊息 = process.argv[2];
const 試跑 = process.argv.includes('--dry');
const 要發PR = process.argv.includes('--pr');

/* gh 裝在 Program Files 時不一定在 PATH 上，兩個地方都找 */
function 找gh() {
  const 候選 = ['gh', 'C:\\Program Files\\GitHub CLI\\gh.exe'];
  for (const c of 候選) {
    try {
      execFileSync(c, ['--version'], { stdio: 'ignore', windowsHide: true });
      return c;
    } catch (e) { /* 換下一個 */ }
  }
  return null;
}

function 跑(參數) {
  if (試跑) { console.log('  [試跑] git ' + 參數.join(' ')); return ''; }
  return execFileSync('git', 參數, {
    cwd: 設定.repo, encoding: 'utf8', windowsHide: true
  }).trim();
}

if (!訊息) {
  console.error('要給 commit 訊息，例：node scripts/交件.js "20260919 完成油漆計算機"');
  process.exit(1);
}

/* ── 第 1 步：檢查 ── */
console.log('第 1 步　交件前檢查');
const r = 檢.檢查(設定);
console.log('  分支：' + r.分支 + '　變更檔案：' + r.變更.length + ' 個');
r.變更.forEach(function (c) { console.log('    ' + c.狀態 + ' ' + c.路徑); });
r.提醒.forEach(function (s) { console.log('  提醒｜' + s); });
if (r.阻擋.length) {
  r.阻擋.forEach(function (s) { console.log('  阻擋｜' + s); });
  console.log('');
  console.log('檢查沒過，沒有 commit 任何東西。');
  process.exit(1);
}
console.log('  檢查通過');
console.log('');

/* ── 第 2 步：commit ── */
let 有新commit = false;
if (r.變更.length) {
  console.log('第 2 步　commit');
  const 我的資料夾 = 設定.上課日期資料夾.map(function (d) {
    return d + '/students/' + 設定.學號姓名;
  });
  跑(['add', '--'].concat(我的資料夾));
  跑(['commit', '-m', 訊息]);
  有新commit = true;
  if (!試跑) console.log('  ' + 跑(['log', '--oneline', '-1']));
  console.log('');
} else {
  console.log('第 2 步　沒有未提交的變更，跳過 commit');
  console.log('');
}

/* ── 第 3 步：push 到 fork ── */
console.log('第 3 步　push 到 ' + 設定.我的fork);
跑(['push', '-u', 設定.我的fork, r.分支]);
console.log('  已推上 ' + 設定.我的fork + '/' + r.分支 + '（push 到 fork 就算交件）');
console.log('');

/* ── 第 4 步：PR ── */
const fork帳號 = 設定.fork網址.split('/')[3];
const repo名 = 設定.fork網址.split('/')[4];
const 上游全名 = 設定.上游網址.replace('https://github.com/', '');
const compare網址 = 設定.上游網址 + '/compare/' + 設定.主分支 + '...' +
                    fork帳號 + ':' + repo名 + ':' + r.分支 + '?expand=1';

console.log('第 4 步　PR');

if (!要發PR) {
  console.log('  沒帶 --pr，不發 PR。課程規則是 push 到 fork 就算交件。');
  console.log('  要發的話：加 --pr，或自己開這個連結：');
  console.log('  ' + compare網址);
} else if (試跑) {
  console.log('  [試跑] gh pr create --repo ' + 上游全名 +
              ' --base ' + 設定.主分支 + ' --head ' + fork帳號 + ':' + r.分支);
} else {
  const gh = 找gh();
  if (!gh) {
    console.log('  找不到 gh CLI。裝法：winget install --id GitHub.cli');
    console.log('  裝好後先跑一次 gh auth login 登入，再重跑本指令。');
    console.log('  或先用連結手動開：' + compare網址);
    process.exit(1);
  }

  /* commit 訊息第一行當 PR 標題，整段當內文 */
  const 標題 = 訊息.split('\n')[0].trim();
  const 內文檔 = require('path').join(require('os').tmpdir(), 'pr-body-' + Date.now() + '.md');
  fs.writeFileSync(內文檔, 訊息, 'utf8');

  try {
    const 結果 = execFileSync(gh, [
      'pr', 'create',
      '--repo', 上游全名,
      '--base', 設定.主分支,
      '--head', fork帳號 + ':' + r.分支,
      '--title', 標題,
      '--body-file', 內文檔
    ], { cwd: 設定.repo, encoding: 'utf8', windowsHide: true }).trim();
    console.log('  PR 已建立：' + 結果);
  } catch (e) {
    const 錯 = ((e.stderr || '') + (e.stdout || '')).toString().trim();
    if (錯.includes('already exists')) {
      console.log('  這條分支已經有開著的 PR，新的 commit 會自動加進去，不用重開。');
      console.log('  ' + 錯.split('\n').filter(function (l) { return l.includes('http'); }).join(' '));
    } else if (錯.includes('auth') || 錯.includes('logged')) {
      console.log('  gh 還沒登入。自己跑一次 gh auth login 再重試。');
      process.exit(1);
    } else {
      console.log('  gh pr create 失敗：');
      console.log('  ' + 錯.split('\n').slice(0, 5).join('\n  '));
      console.log('  可改用連結手動開：' + compare網址);
      process.exit(1);
    }
  } finally {
    try { fs.unlinkSync(內文檔); } catch (e) { /* 清不掉不影響結果 */ }
  }
}

console.log('');
console.log(試跑 ? '以上是試跑，沒有真的動任何東西。' :
            (有新commit ? '交件完成。' : '沒有新 commit，只做了 push。'));
