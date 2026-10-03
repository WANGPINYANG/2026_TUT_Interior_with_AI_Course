/* 產出檢查器。跑法：node scripts/檢查.js ../油漆用量計算機.html
   把 SKILL.md 的五條硬性規格變成機器判斷，零 AI。
   會用假的 DOM 無頭跑一次頁面程式，所以「公式對但沒接上輸入欄」這種錯抓得到。
   有任何一條沒過就 exit 1。 */
'use strict';

var fs = require('fs');

var 危險id = ['open', 'name', 'top', 'self', 'parent', 'status', 'length',
              'location', 'history', 'closed', 'frames', 'origin'];

var 檔案 = process.argv[2];
if (!檔案) {
  console.error('要給 HTML 檔路徑，例：node scripts/檢查.js ../油漆用量計算機.html');
  process.exit(1);
}
var html = fs.readFileSync(檔案, 'utf8');

var 結果 = [];
function 記(項目, 通過, 說明) { 結果.push({ 項目: 項目, 通過: 通過, 說明: 說明 || '' }); }

/* ── 規格 1：單一檔案，不連任何外部資源 ──
   不能只看 src/href 屬性。CSS 的 @import 與 url() 也會連外，
   2026-10-03 稽核用 @import url("https://…") 穿過了這一關。 */
var 外連 = (html.match(/(src|href)\s*=\s*["']https?:\/\/[^"']*/gi) || [])
  .concat(html.match(/@import\s+[^;]*/gi) || [])
  .concat(html.match(/url\(\s*["']?https?:\/\/[^)]*/gi) || []);
記('規格1 單檔離線', 外連.length === 0,
   外連.length ? '有 ' + 外連.length + ' 處外部資源：' + 外連.join('、') : '無外部資源');

/* ── 規格 5：手機可用 ── */
記('規格5 手機可用', /<meta\s+name="viewport"/i.test(html), 'viewport meta');

/* ── 規格 3：假設參數做成可改輸入欄 ── */
var 假設區 = html.match(/<h2>假設參數（可改）<\/h2>([\s\S]*?)<\/section>/);
var 假設欄數 = 假設區 ? (假設區[1].match(/<input /g) || []).length : 0;
記('規格3 假設可改', 假設欄數 > 0, 假設欄數 + ' 個可修改參數欄位');

/* ── 免責聲明不可拿掉 ── */
記('免責聲明', html.indexOf('不是下單量') !== -1, '輸出區保留「不是下單量」');

/* ── 危險 id ── */
var 撞名 = [];
var idRe = /id="([^"]+)"/g;
var m;
while ((m = idRe.exec(html))) {
  if (危險id.indexOf(m[1]) !== -1 && 撞名.indexOf(m[1]) === -1) { 撞名.push(m[1]); }
}
記('id 未與瀏覽器內建撞名', 撞名.length === 0,
   撞名.length ? '撞名：' + 撞名.join('、') : '無撞名');

/* ── 無頭執行：建一個最小的假 DOM，實際跑一次頁面程式 ── */
function 元素(初值) {
  /* style 要給，否則頁面一用 el.style.x 就拋錯，看起來像頁面壞了，其實是假 DOM 不夠忠實。
     2026-10-03 實際踩到一次。 */
  var o = { value: 初值 || '', className: '', style: {}, _html: '', _text: '—',
            _綁定: [],
            addEventListener: function (type) { o._綁定.push(type); } };
  Object.defineProperty(o, 'innerHTML', {
    get: function () { return o._html; },
    set: function (v) { o._html = String(v); o._text = String(v).replace(/<[^>]*>/g, ''); }
  });
  Object.defineProperty(o, 'textContent', {
    get: function () { return o._text; },
    set: function (v) { o._text = String(v); }
  });
  return o;
}

var 元素表 = {};
var 輸入ids = [];
var inRe = /<input\s+id="([^"]+)"[^>]*\svalue="([^"]*)"/g;
while ((m = inRe.exec(html))) {
  元素表[m[1]] = 元素(m[2]);
  輸入ids.push(m[1]);
}
idRe.lastIndex = 0;
while ((m = idRe.exec(html))) {
  if (!元素表[m[1]]) { 元素表[m[1]] = 元素(''); }
}

var 假document = {
  getElementById: function (id) { return 元素表[id] || null; },
  querySelectorAll: function () { return 輸入ids.map(function (id) { return 元素表[id]; }); }
};

var 程式 = [];
var sRe = /<script>([\s\S]*?)<\/script>/g;
while ((m = sRe.exec(html))) { 程式.push(m[1]); }

var 執行錯誤 = null;
try {
  new Function('document', 程式.join('\n'))(假document);
} catch (e) {
  執行錯誤 = e.message;
}
記('頁面程式可執行', !執行錯誤, 執行錯誤 || '無拋錯');

if (!執行錯誤) {
  /* ── 輸入欄必須真的綁上事件 ──
     頁面載入時 render() 會跑一次，所以就算事件沒綁、畫面照樣是對的，
     只是改數字不會重算——這種壞法光看畫面看不出來。
     假 DOM 記下每個 input 收到的 addEventListener，用行為判定而不是比對原始碼。
     2026-10-03 稽核把事件綁定拔掉，當時這一關穿過去了。 */
  var 沒綁 = 輸入ids.filter(function (id) {
    return (元素表[id]._綁定 || []).indexOf('input') === -1;
  });
  記('輸入欄有綁 input 事件', 沒綁.length === 0,
     沒綁.length ? '沒綁的欄位：' + 沒綁.join('、') + '（改數字不會重算）'
                 : 輸入ids.length + ' 個欄位都綁了');

  /* ── 規格 2：顯示計算過程 ── */
  var 過程列數 = (元素表.steps ? 元素表.steps.innerHTML.match(/<tr>/g) || [] : []).length;
  記('規格2 顯示計算過程', 過程列數 >= 2, 過程列數 + ' 列中間值');

  /* ── 規格 4：驗算區全過 ── */
  var 測試ids = Object.keys(元素表).filter(function (k) { return /^t\d+$|^tRender$/.test(k); });
  var 失敗項 = 測試ids.filter(function (k) { return 元素表[k].className.indexOf('fail') !== -1; });
  var 未跑 = 測試ids.filter(function (k) { return 元素表[k].textContent === '—'; });
  記('規格4 驗算區存在', 測試ids.length >= 2, 測試ids.length + ' 項檢查');
  記('規格4 驗算全過', 測試ids.length > 0 && !失敗項.length && !未跑.length,
     失敗項.length ? '失敗：' + 失敗項.map(function (k) { return 元素表[k].textContent; }).join('｜')
                   : (未跑.length ? '有 ' + 未跑.length + ' 項沒執行' : '全部通過'));

  /* ── 畫面不得有 NaN ── */
  var 畫面 = ['steps', 'out', 'out2', 'assume'].map(function (k) {
    return 元素表[k] ? 元素表[k].textContent : '';
  }).join(' ');
  /* ── 產出不得殘留未代換的佔位符 ── */
  var 殘留 = 畫面.match(/{[^}]+}/g) || [];
  記('無未代換佔位符', 殘留.length === 0,
     殘留.length ? '殘留：' + 殘留.join('、') : '全部代換完成');

  /* Infinity 也要抓。2026-09-19 稽核指出：塗佈率填 0 時整頁顯示 Infinity 加侖，
     而這裡只比對 NaN，所以照樣報通過。只認一種壞值等於沒認。 */
  var 壞值 = ['NaN', 'Infinity', 'undefined', '工具故障', '要修正'];
  var 命中 = 壞值.filter(function (k) { return 畫面.indexOf(k) !== -1; });
  記('畫面無壞值', 命中.length === 0,
     命中.length ? '出現：' + 命中.join('、')
                 : (元素表.out ? '結果欄：' + 元素表.out.textContent : '找不到結果欄'));
}

console.log('檢查：' + 檔案);
console.log('');
var 壞掉 = 0;
結果.forEach(function (r) {
  if (!r.通過) { 壞掉++; }
  console.log('  ' + (r.通過 ? '通過' : '失敗') + '｜' + r.項目 +
              (r.說明 ? '　' + r.說明 : ''));
});
console.log('');
console.log(壞掉 ? '共 ' + 壞掉 + ' 項未通過' : '全部 ' + 結果.length + ' 項通過');
process.exit(壞掉 ? 1 : 0);
