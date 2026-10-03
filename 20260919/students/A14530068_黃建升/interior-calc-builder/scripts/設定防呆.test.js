/* 產生器防呆測試。跑法：node scripts/設定防呆.test.js
   用惡意／畸形設定檔攻擊產生器，確認該拒絕的拒絕、該逸出的逸出。

   來源：2026-10-03 暴力測試。當時 20 個惡意設定有 12 個被接受，包括
   '../逃脫.html' 真的寫到指定資料夾之外、標題含 </script> 時注入的程式碼實際執行。

   兩種合格：
   A 結構性錯誤 → 產生器必須 exit 1 拒絕
   B 文字含 HTML／引號 → 不該拒絕（那是合法內容），但產出必須是死的字面資料

   B 的判定方式是把產出的 script 區塊實際執行一次，看注入的全域變數有沒有被設。
   只比對文字有沒有出現在 script 區塊裡是不夠的——逸出後的 JSON 字串裡
   照樣看得到那串文字，但它是資料不是程式碼。這個分辨錯誤在 2026-10-03 犯過一次。 */
'use strict';

var fs = require('fs');
var os = require('os');
var path = require('path');
var spawnSync = require('child_process').spawnSync;

var 產生器 = path.join(__dirname, '建立計算機.js');
var 原設定 = JSON.parse(fs.readFileSync(path.join(__dirname, '..', '設定', '油漆用量.json'), 'utf8'));
var 暫存 = fs.mkdtempSync(path.join(os.tmpdir(), 'calc-gen-test-'));
var 輸出 = path.join(暫存, 'out');
fs.mkdirSync(輸出, { recursive: true });

var 失敗 = 0;
function 記(過, 說明) {
  if (!過) { 失敗++; }
  console.log('  ' + (過 ? '通過' : '失敗') + '｜' + 說明);
}

var 序號 = 0;
function 產生(改) {
  var c = JSON.parse(JSON.stringify(原設定));
  c.檔名 = 'case' + (++序號) + '.html';
  改(c);
  var 設定檔 = path.join(暫存, 'case' + 序號 + '.json');
  fs.writeFileSync(設定檔, JSON.stringify(c), 'utf8');
  var r = spawnSync(process.execPath, [產生器, 設定檔, 輸出], { encoding: 'utf8', timeout: 20000 });
  return { 拒絕: r.status !== 0, 產出: path.join(輸出, c.檔名) };
}

/* ── A：結構性錯誤必須被拒絕 ── */
var 必須拒絕 = [
  ['重複的欄位 id', function (c) { c.輸入[1].id = c.輸入[0].id; }],
  ['空的預期答案（會變成假驗算）', function (c) { c.驗算.forEach(function (v) { v.預期 = {}; }); }],
  ['缺結果單位', function (c) { delete c.結果.單位; }],
  ['缺結果欄位', function (c) { delete c.結果.欄位; }],
  ['結果欄位不在公式輸出裡', function (c) { c.結果.欄位 = '不存在'; }],
  ['沒有驗算案例', function (c) { c.驗算 = []; }],
  ['驗算案例缺欄位', function (c) { delete c.驗算[0].輸入.rate; }],
  ['欄位沒有預設值', function (c) { delete c.輸入[0].預設; }],
  ['欄位 id 與瀏覽器內建撞名', function (c) {
    c.輸入[0].id = 'open';
    c.驗算.forEach(function (v) { v.輸入.open = 10; });
  }],
  ['公式不存在', function (c) { c.公式 = '不存在'; }],
  ['檔名含 .. 路徑越界', function (c) { c.檔名 = '../逃脫.html'; }],
  ['檔名含路徑分隔符', function (c) { c.檔名 = 'sub/逃脫.html'; }],
  ['標題超長', function (c) { c.標題 = 'x'.repeat(100000); }]
];

console.log('── A 結構性錯誤必須被拒絕 ──');
必須拒絕.forEach(function (p) {
  記(產生(p[1]).拒絕, p[0]);
});

/* ── B：文字注入不該拒絕，但必須是死的 ── */
function 執行後的全域(html檔) {
  var h = fs.readFileSync(html檔, 'utf8');
  var 區塊 = [];
  var re = /<script>([\s\S]*?)<\/script>/g;
  var m;
  while ((m = re.exec(h))) { 區塊.push(m[1]); }
  var win = {};
  var els = {};
  var 造 = function () {
    return { value: '10', className: '', style: {}, innerHTML: '',
             textContent: '—', addEventListener: function () {} };
  };
  var doc = {
    getElementById: function (id) { return els[id] || (els[id] = 造()); },
    querySelectorAll: function () { return []; }
  };
  var 例外 = null;
  try {
    new Function('document', 'window', 區塊.join('\n'))(doc, win);
  } catch (e) { 例外 = e.message; }
  return { 區塊數: 區塊.length, 全域: Object.keys(win), 例外: 例外,
           關閉標籤數: (h.match(/<\/script>/g) || []).length };
}

var 注入案例 = [
  ['標題含 script 標籤', function (c) { c.標題 = '油漆<script>window.注入1=1;</script>計算機'; }],
  ['說明含提早關閉 script', function (c) { c.說明 = '說明</script><script>window.注入2=1;</script>'; }],
  ['免責含事件屬性', function (c) { c.免責 = '<img src=x onerror="window.注入3=1">免責'; }],
  ['次要結果含 script', function (c) { c.次要結果 = '</script><script>window.注入4=1;</script>'; }],
  ['欄位標籤含 HTML', function (c) { c.輸入[0].標籤 = '<b onclick="window.注入5=1">地坪</b>'; }],
  ['驗算標題含 script', function (c) { c.驗算[0].標題 = '</script><script>window.注入6=1;</script>'; }],
  ['欄位說明含引號', function (c) { c.輸入[0].說明 = '他說"這樣"對嗎' + String.fromCharCode(39); }]
];

console.log('');
console.log('── B 文字注入不該拒絕，但必須是死的 ──');
注入案例.forEach(function (p) {
  var r = 產生(p[1]);
  if (r.拒絕) {
    記(false, p[0] + '　被拒絕了，但合法文字不該被拒絕，應該逸出');
    return;
  }
  var e = 執行後的全域(r.產出);
  var 注入的 = e.全域.filter(function (k) { return k.indexOf('注入') === 0; });
  var 過 = !注入的.length && !e.例外 && e.區塊數 === 2 && e.關閉標籤數 === 2;
  記(過, p[0] + '　' +
       (注入的.length ? '注入執行成功：' + 注入的.join('、')
        : e.例外 ? '執行拋錯：' + e.例外
        : e.關閉標籤數 !== 2 ? '多出 </script> 標籤：' + e.關閉標籤數 + ' 個'
        : '注入已成為死的字面資料'));
});

/* ── 路徑越界實際落點 ── */
console.log('');
console.log('── C 產出沒有寫到指定資料夾之外 ──');
記(!fs.existsSync(path.join(暫存, '逃脫.html')), '上一層沒有被寫入檔案');
記(!fs.existsSync(path.join(暫存, 'sub')), '子目錄沒有被建立');

fs.rmSync(暫存, { recursive: true, force: true });
console.log('');
console.log(失敗 ? '共 ' + 失敗 + ' 項失敗' : '全部通過');
process.exit(失敗 ? 1 : 0);
