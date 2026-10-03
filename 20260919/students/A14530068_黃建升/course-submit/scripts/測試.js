/* 自我檢查：跑法 node scripts/測試.js
   在暫存目錄建一個假的課程 repo，實際觸發每一條防呆，確認它真的擋得住。
   自報成功不算通過——每條阻擋都要有一個會踩到它的情境。 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const 檢 = require('./檢查.js');

let 失敗 = 0;
function 驗(名稱, 條件, 說明) {
  if (!條件) 失敗++;
  console.log('  ' + (條件 ? '通過' : '失敗') + '｜' + 名稱 + (說明 ? '　' + 說明 : ''));
}
function 有阻擋(r, 關鍵字) {
  return r.阻擋.some(function (s) { return s.indexOf(關鍵字) !== -1; });
}

const 暫存 = fs.mkdtempSync(path.join(os.tmpdir(), 'course-submit-test-'));
function g(參數) {
  return execFileSync('git', 參數, { cwd: 暫存, encoding: 'utf8', windowsHide: true });
}
function 寫(相對, 內容) {
  const p = path.join(暫存, 相對);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, 內容 || 'x', 'utf8');
}

const 設定 = {
  repo: 暫存,
  學號姓名: 'A14530068_黃建升',
  上游remote: 'origin',
  我的fork: 'fork',
  上游網址: 'https://example.invalid/上游/course',
  fork網址: 'https://example.invalid/我/course',
  主分支: 'main',
  分支前綴: 'student/A14530068',
  上課日期資料夾: ['20260919', '20261003'],
  大檔案副檔名: ['.skp', '.rvt', '.mp4'],
  機密檔樣式: ['.env', '.key'],
  單檔上限MB: 1
};

g(['init', '--quiet', '-b', 'main']);
g(['config', 'user.email', 'test@example.invalid']);
g(['config', 'user.name', 'test']);
g(['remote', 'add', 'origin', path.join(暫存, 'no-such-upstream')]);
g(['remote', 'add', 'fork', path.join(暫存, 'no-such-fork')]);
寫('README.md', '課程主 repo');
g(['add', '.']);
g(['commit', '--quiet', '-m', 'init']);

console.log('情境 1：還在 main 分支上');
寫('20260919/students/A14530068_黃建升/a.md', '我的作業');
let r = 檢.檢查(設定);
驗('擋住在 main 上交件', 有阻擋(r, '先開分支'));

g(['checkout', '--quiet', '-b', 'student/A14530068-測試']);

console.log('');
console.log('情境 2：只動自己的資料夾（應該放行）');
r = 檢.檢查(設定);
驗('沒有阻擋', r.阻擋.length === 0, r.阻擋.join('｜'));
驗('抓到 1 個變更檔', r.變更.length === 1, r.變更.map(c => c.路徑).join('、'));
驗('中文路徑沒被跳脫', r.變更[0].路徑.indexOf('黃建升') !== -1, r.變更[0].路徑);

console.log('');
console.log('情境 3：動到別人的資料夾');
寫('20260919/students/A15530027_黃麟珍/b.md', '別人的東西');
r = 檢.檢查(設定);
驗('擋住越界修改', 有阻擋(r, '不在你的資料夾底下'));
fs.rmSync(path.join(暫存, '20260919/students/A15530027_黃麟珍'), { recursive: true, force: true });

console.log('');
console.log('情境 4：動到主 repo 的共用檔');
寫('README.md', '偷改主 repo');
r = 檢.檢查(設定);
驗('擋住改共用檔', 有阻擋(r, '不在你的資料夾底下'));
g(['checkout', '--', 'README.md']);

console.log('');
console.log('情境 5：夾帶大檔案');
寫('20260919/students/A14530068_黃建升/模型.skp', 'fake');
r = 檢.檢查(設定);
驗('擋住 .skp', 有阻擋(r, '大檔案不進 repo'));
fs.rmSync(path.join(暫存, '20260919/students/A14530068_黃建升/模型.skp'));

console.log('');
console.log('情境 6：夾帶機密檔');
寫('20260919/students/A14530068_黃建升/.env', 'TOKEN=abc');
r = 檢.檢查(設定);
驗('擋住 .env', 有阻擋(r, '疑似機密檔'));
fs.rmSync(path.join(暫存, '20260919/students/A14530068_黃建升/.env'));

console.log('');
console.log('情境 7：單檔超過上限');
寫('20260919/students/A14530068_黃建升/big.txt', 'x'.repeat(1.2 * 1024 * 1024));
r = 檢.檢查(設定);
驗('擋住超大檔', 有阻擋(r, '超過 1 MB'));
fs.rmSync(path.join(暫存, '20260919/students/A14530068_黃建升/big.txt'));

console.log('');
console.log('情境 8：fork remote 不見了');
g(['remote', 'remove', 'fork']);
r = 檢.檢查(設定);
驗('擋住沒有 fork remote', 有阻擋(r, 'remote「fork」不存在'));

console.log('');
console.log('情境 9：fork 與上游指向同一個地方');
g(['remote', 'add', 'fork', path.join(暫存, 'no-such-upstream')]);
r = 檢.檢查(設定);
驗('擋住 fork 等於上游', 有阻擋(r, '同一個網址'));

fs.rmSync(暫存, { recursive: true, force: true });
console.log('');
console.log(失敗 ? '共 ' + 失敗 + ' 項失敗' : '全部通過');
process.exit(失敗 ? 1 : 0);
