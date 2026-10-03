/* 單一入口：一個指令跑完全部測試。
   跑法：node scripts/全部測試.js
        node scripts/全部測試.js --詳細    連通過的也印出完整輸出

   課程 README 要求「課前 15 分鐘先跑一次自己的工具，確認現在還能動」，
   這支就是給那件事用的。任何一套失敗就 exit 1，並印出那一套的完整輸出。

   順序是有意義的：先驗引擎，再驗產生，最後驗產出。
   引擎壞了的話後面全都不用看，所以引擎的測試排在最前面。 */
'use strict';

var path = require('path');
var spawnSync = require('child_process').spawnSync;

var 詳細 = process.argv.indexOf('--詳細') !== -1 || process.argv.indexOf('--verbose') !== -1;
var 這裡 = __dirname;
var 專案 = path.join(這裡, '..');
var 產出 = path.join(專案, '..', '油漆用量計算機.html');

var 項目 = [
  { 名: '引擎測試', 說: '算得對不對、錯誤輸入擋不擋得住', 檔: '公式.test.js' },
  { 名: '整數邊界', 說: '正常值剛好落在整數時不可多進一位', 檔: '整數邊界.test.js' },
  { 名: '單位測試', 說: '換算值、可逆性、設定標籤與引擎單位一致', 檔: '單位.test.js' },
  { 名: '壞值掃描', 說: '課程壞值清單 × 每個欄位', 檔: '壞值掃描.test.js' },
  { 名: '暴力測試', 說: '型別／邊界／組合溢位／隨機模糊', 檔: '暴力測試.test.js' },
  { 名: '設定防呆', 說: '惡意設定檔攻擊產生器', 檔: '設定防呆.test.js' },
  { 名: '重新產生', 說: '設定檔 → 單檔 HTML', 檔: '建立計算機.js',
    參: [path.join(專案, '設定', '油漆用量.json')] },
  { 名: '產出檢查', 說: '產出是否合規，含假 DOM 無頭執行', 檔: '檢查.js', 參: [產出] },
  { 名: '第三方稽核', 說: '非我所寫的獨立稽核', 檔: '稽核.test.js' }
];

var 結果 = [];
var 開始 = Date.now();

項目.forEach(function (it) {
  var t0 = Date.now();
  var r = spawnSync(process.execPath, [path.join(這裡, it.檔)].concat(it.參 || []), {
    cwd: 專案, encoding: 'utf8', timeout: 180000
  });
  var 輸出 = ((r.stdout || '') + (r.stderr || '')).trim();

  /* 摘要取「有結論的那一行」，不是最後一行——
     第三方稽核的最後一行是暫存目錄路徑，拿來當摘要等於沒講結果。 */
  var 行 = 輸出.split('\n').map(function (l) { return l.trim(); })
                .filter(function (l) { return l; });
  var 結論 = 行.filter(function (l) {
    return /總計|全部|共\s*\d+|通過|失敗|bytes/.test(l);
  });
  結果.push({
    名: it.名, 說: it.說, 過: r.status === 0,
    秒: ((Date.now() - t0) / 1000).toFixed(1),
    摘要: (結論.length ? 結論[結論.length - 1] : 行[行.length - 1]) || '（無輸出）',
    輸出: 輸出
  });
});

var 壞 = 結果.filter(function (r) { return !r.過; });

console.log('計算機產生器　全部測試');
console.log('');
結果.forEach(function (r) {
  console.log('  ' + (r.過 ? '通過' : '失敗') + '　' +
              r.名 + '　'.repeat(Math.max(1, 6 - r.名.length)) +
              r.秒 + 's　' + r.摘要);
});
console.log('');

/* 失敗的一定要看完整輸出，否則這支就只是個比較漂亮的 exit code */
壞.forEach(function (r) {
  console.log('════ ' + r.名 + ' 的完整輸出 ════');
  console.log(r.輸出);
  console.log('');
});

if (詳細) {
  結果.filter(function (r) { return r.過; }).forEach(function (r) {
    console.log('──── ' + r.名 + ' ────');
    console.log(r.輸出);
    console.log('');
  });
}

console.log('共 ' + 結果.length + ' 套，' + (結果.length - 壞.length) + ' 套通過，' +
            '耗時 ' + ((Date.now() - 開始) / 1000).toFixed(1) + 's');
if (壞.length) {
  console.log('');
  console.log('失敗的：' + 壞.map(function (r) { return r.名; }).join('、'));
  console.log('先修到全綠再交件——course-submit 不會幫你擋這個，它只檢查 git 層面的事。');
}
process.exit(壞.length ? 1 : 0);
