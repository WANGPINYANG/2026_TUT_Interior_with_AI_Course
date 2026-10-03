/* 交件前防呆檢查。零 AI，全部是可機器判斷的條件。
   跑法：node scripts/檢查.js
   阻擋項存在就 exit 1。交件.js 會先跑這支，沒過不准 commit。 */
'use strict';

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

function 讀設定() {
  return JSON.parse(fs.readFileSync(path.join(__dirname, '..', '設定.json'), 'utf8'));
}

function git(設定, 參數, 可失敗) {
  try {
    return execFileSync('git', 參數, {
      cwd: 設定.repo, encoding: 'utf8', windowsHide: true,
      /* 允許失敗的指令（fetch、rev-list）把 stderr 吞掉，
         否則沒設好上游時畫面會噴一堆 fatal，看起來像工具壞了 */
      stdio: 可失敗 ? ['ignore', 'pipe', 'ignore'] : ['ignore', 'pipe', 'pipe']
    }).trim();
  } catch (e) {
    if (可失敗) return null;
    throw new Error('git ' + 參數.join(' ') + ' 失敗：' + (e.stderr || e.message).toString().trim());
  }
}

/* git status --porcelain -z：用 NUL 分隔，避免中文路徑被跳脫成 \351\273 */
function 變更清單(設定) {
  const 原始 = execFileSync('git',
    ['status', '--porcelain=v1', '-z', '--untracked-files=all'],
    { cwd: 設定.repo, encoding: 'utf8', windowsHide: true });
  const 片段 = 原始.split('\0').filter(function (s) { return s.length; });
  const out = [];
  for (let i = 0; i < 片段.length; i++) {
    const s = 片段[i];
    const 狀態 = s.slice(0, 2);
    const 路徑 = s.slice(3);
    if (狀態[0] === 'R' || 狀態[0] === 'C') { i++; }   /* 改名會多一段舊路徑 */
    out.push({ 狀態: 狀態, 路徑: 路徑 });
  }
  return out;
}

function 檢查(設定) {
  const 阻擋 = [], 提醒 = [];

  if (!fs.existsSync(path.join(設定.repo, '.git'))) {
    return { 阻擋: ['找不到 git repo：' + 設定.repo], 提醒: [], 變更: [], 分支: null };
  }

  /* remote 設定 */
  const remotes = git(設定, ['remote']).split('\n').map(s => s.trim());
  if (!remotes.includes(設定.我的fork)) {
    阻擋.push('remote「' + 設定.我的fork + '」不存在，推不上去。先 git remote add ' +
              設定.我的fork + ' ' + 設定.fork網址 + '.git');
  }
  if (remotes.includes(設定.我的fork) && remotes.includes(設定.上游remote)) {
    const f = git(設定, ['remote', 'get-url', 設定.我的fork]);
    const o = git(設定, ['remote', 'get-url', 設定.上游remote]);
    if (f === o) 阻擋.push('fork 與上游指向同一個網址，會推到別人的 repo');
  }

  /* 分支 */
  const 分支 = git(設定, ['rev-parse', '--abbrev-ref', 'HEAD']);
  if (分支 === 設定.主分支) {
    阻擋.push('目前在 ' + 設定.主分支 + ' 上。先開分支：git checkout -b ' +
              設定.分支前綴 + '-<主題>');
  }

  /* 變更內容 */
  const 變更 = 變更清單(設定);
  const 我的資料夾 = 設定.上課日期資料夾.map(function (d) {
    return d + '/students/' + 設定.學號姓名 + '/';
  });

  const 越界 = 變更.filter(function (c) {
    return !我的資料夾.some(function (p) { return c.路徑.indexOf(p) === 0; });
  });
  if (越界.length) {
    阻擋.push('有 ' + 越界.length + ' 個檔案不在你的資料夾底下，會動到別人或主 repo：\n      ' +
              越界.map(c => c.路徑).join('\n      '));
  }

  /* 大檔案與機密檔 */
  for (const c of 變更) {
    const 副檔名 = path.extname(c.路徑).toLowerCase();
    if (設定.大檔案副檔名.includes(副檔名)) {
      阻擋.push('大檔案不進 repo：' + c.路徑 + '（' + 副檔名 + '，原檔留本機）');
    }
    if (設定.機密檔樣式.some(function (p) { return c.路徑.toLowerCase().includes(p); })) {
      阻擋.push('疑似機密檔：' + c.路徑);
    }
    const 全路徑 = path.join(設定.repo, c.路徑);
    try {
      const st = fs.statSync(全路徑);
      if (st.isFile() && st.size > 設定.單檔上限MB * 1024 * 1024) {
        阻擋.push('檔案超過 ' + 設定.單檔上限MB + ' MB：' + c.路徑 +
                  '（' + (st.size / 1048576).toFixed(1) + ' MB）');
      }
    } catch (e) { /* 已刪除的檔案 stat 不到，正常 */ }
  }

  /* 與上游的落差 */
  git(設定, ['fetch', 設定.上游remote, '--quiet'], true);
  const 落後 = git(設定, ['rev-list', '--count',
    'HEAD..' + 設定.上游remote + '/' + 設定.主分支], true);
  if (落後 && +落後 > 0) {
    提醒.push('你的分支落後上游 ' + 落後 + ' 筆。不影響交件，但建議先同步：git pull ' +
              設定.上游remote + ' ' + 設定.主分支);
  }

  if (!變更.length) {
    const 待推 = git(設定, ['rev-list', '--count',
      設定.我的fork + '/' + 分支 + '..HEAD'], true);
    if (待推 && +待推 > 0) 提醒.push('沒有未提交的變更，但有 ' + 待推 + ' 筆 commit 還沒 push');
    else 提醒.push('沒有任何變更可交');
  }

  return { 阻擋: 阻擋, 提醒: 提醒, 變更: 變更, 分支: 分支 };
}

if (require.main === module) {
  const 設定 = 讀設定();
  const r = 檢查(設定);
  console.log('交件前檢查：' + 設定.repo);
  console.log('分支：' + r.分支 + '　變更檔案：' + r.變更.length + ' 個');
  console.log('');
  if (r.變更.length) {
    r.變更.forEach(function (c) { console.log('  ' + c.狀態 + ' ' + c.路徑); });
    console.log('');
  }
  r.提醒.forEach(function (s) { console.log('  提醒｜' + s); });
  r.阻擋.forEach(function (s) { console.log('  阻擋｜' + s); });
  console.log('');
  console.log(r.阻擋.length ? '有 ' + r.阻擋.length + ' 項阻擋，先處理再交件' : '檢查通過');
  process.exit(r.阻擋.length ? 1 : 0);
}

module.exports = { 讀設定, 檢查, git, 變更清單 };
