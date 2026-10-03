/* 計算機產生器。跑法：node scripts/建立計算機.js 設定/油漆用量.json [輸出資料夾]
   輸出單一 HTML 檔（公式引擎內嵌，無任何外部連線）。
   不要手改產出的 HTML——要改就改設定檔或 公式.js，然後重跑這支。 */
'use strict';

var fs = require('fs');
var path = require('path');
var 引擎 = require('./公式.js');

var 危險id = ['open', 'name', 'top', 'self', 'parent', 'status', 'length',
              'location', 'history', 'closed', 'frames', 'origin'];

function 爆掉(訊息) { console.error('產生失敗：' + 訊息); process.exit(1); }

/* 設定檔的文字一律逸出再插進 HTML。
   2026-10-03 暴力測試實證：標題寫 '</script><script>…' 時，注入的程式碼會落在
   產出的 <script> 區塊裡並實際執行。設定檔現在是自己寫的不代表以後也是。 */
function 逸出(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/* 內嵌進 <script> 的 JSON：即使在字串裡，</script> 也會被 HTML 解析器當成結束標籤，
   所以 < 一律轉成 <。 */
function 安全JSON(o) {
  return JSON.stringify(o).replace(/</g, '\\u003c');
}

var 設定路徑 = process.argv[2];
if (!設定路徑) { 爆掉('要給設定檔路徑，例：node scripts/建立計算機.js 設定/油漆用量.json'); }
var 設定 = JSON.parse(fs.readFileSync(設定路徑, 'utf8'));
var 輸出資料夾 = process.argv[3] || path.join(__dirname, '..', '..');

['檔名', '標題', '說明', '公式', '結果', '免責'].forEach(function (k) {
  if (!設定[k]) { 爆掉('設定檔缺少「' + k + '」'); }
});
if (!引擎.公式[設定.公式]) {
  爆掉('公式「' + 設定.公式 + '」不存在，目前有：' + Object.keys(引擎.公式).join('、'));
}
if (!Array.isArray(設定.驗算) || !設定.驗算.length) {
  爆掉('至少要有一組驗算案例，沒有驗算的計算機不准產生');
}

var 全部欄位 = (設定.輸入 || []).concat(設定.參數 || []);
if (!全部欄位.length) { 爆掉('沒有任何輸入欄位'); }

全部欄位.forEach(function (f) {
  if (!f.id || !f.標籤) { 爆掉('每個欄位都要有 id 與標籤'); }
  if (危險id.indexOf(f.id) !== -1) {
    爆掉('欄位 id「' + f.id + '」與瀏覽器內建物件同名，會讀不到值。換一個名字。');
  }
  if (typeof f.預設 !== 'number') { 爆掉('欄位「' + f.id + '」缺少數字型別的預設值'); }
});

/* 檔名只能是單純檔名。2026-10-03 實證 '../逃脫.html' 真的寫到了指定資料夾之外。 */
if (/[\\/]/.test(設定.檔名) || 設定.檔名.indexOf('..') !== -1) {
  爆掉('檔名只能是單純檔名，不得含路徑分隔符或 ..：' + 設定.檔名);
}
if (!設定.結果.欄位) { 爆掉('結果缺少「欄位」'); }
if (!設定.結果.單位) { 爆掉('結果缺少「單位」，產出會變成沒有單位的裸數字'); }
if (設定.標題.length > 200) { 爆掉('標題過長（' + 設定.標題.length + ' 字），上限 200'); }

var ids = 全部欄位.map(function (f) { return f.id; });
ids.forEach(function (id, n) {
  if (ids.indexOf(id) !== n) { 爆掉('欄位 id 重複：' + id + '；重複的 id 會讓其中一欄讀不到值'); }
});

/* 設定宣告的欄位必須蓋住公式需要的全部輸入。
   少一個的話頁面讀不到那個值，計算永遠回傳「要填數字」，
   等於產出一個開起來就是壞的工具。2026-10-03 稽核指出，當時產生器照收。 */
/* 每個欄位的基準單位來自引擎的規則，不是設定檔——公式認什麼單位由公式決定。
   設定檔只能決定「讓使用者可以選哪些單位」，選了之後換算回基準單位再進公式。 */
var 基準單位 = {};
全部欄位.forEach(function (f) {
  var d = (引擎.規則[設定.公式] || {})[f.id];
  if (d && d.單位) { 基準單位[f.id] = d.單位; }
  if (f.可選單位) {
    if (!d || !d.單位) {
      爆掉('欄位「' + f.id + '」宣告了可選單位，但引擎規則沒有為它定義基準單位');
    }
    if (f.可選單位.indexOf(d.單位) === -1) {
      爆掉('欄位「' + f.id + '」的可選單位必須包含基準單位 ' + d.單位 +
           '，目前是：' + f.可選單位.join('、'));
    }
    f.可選單位.forEach(function (u) {
      try { 引擎.換算到(1, u, d.單位); }
      catch (e) { 爆掉('欄位「' + f.id + '」的可選單位 ' + u + ' 不能換算成 ' + d.單位 + '：' + e.message); }
    });
  }
});

var 公式需要 = Object.keys(引擎.規則[設定.公式] || {});
var 缺欄位 = 公式需要.filter(function (k) { return ids.indexOf(k) === -1; });
if (缺欄位.length) {
  爆掉('設定少了公式「' + 設定.公式 + '」需要的輸入欄：' + 缺欄位.join('、') +
       '；少一欄的話頁面讀不到值，開起來就是壞的');
}

設定.驗算.forEach(function (c, n) {
  if (!c.預期 || !Object.keys(c.預期).length) {
    爆掉('第 ' + (n + 1) + ' 組驗算案例沒有任何預期值——' +
         '那會產出一個永遠顯示「通過」的假驗算，比沒有驗算更糟');
  }
  ids.forEach(function (id) {
    if (typeof c.輸入[id] !== 'number') {
      爆掉('第 ' + (n + 1) + ' 組驗算案例缺少欄位「' + id + '」');
    }
  });
  var 值 = 引擎.計算(設定.公式, c.輸入).值;
  Object.keys(c.預期).forEach(function (k) {
    if (typeof 值[k] === 'undefined') { 爆掉('驗算案例的預期欄位「' + k + '」不在公式輸出裡'); }
  });
});

var 樣本 = 引擎.計算(設定.公式, 設定.驗算[0].輸入).值;
if (typeof 樣本[設定.結果.欄位] === 'undefined') {
  爆掉('結果欄位「' + 設定.結果.欄位 + '」不在公式輸出裡，可用：' + Object.keys(樣本).join('、'));
}

function 欄(f) {
  /* 每個欄位自帶一行錯誤訊息的位置，才能把錯誤標在出錯的那一格旁邊，
     而不是全部擠在頁尾——手機上使用者看不到頁尾。
     宣告 可選單位 的欄位會多一個下拉選單，換單位時數值自動換算。 */
  var 輸入 = '<input id="' + f.id + '" type="number" value="' + f.預設 +
             '" step="' + (f.step || 1) + '" min="' + (typeof f.min === 'number' ? f.min : 0) + '">';

  var 內容;
  if (f.可選單位 && f.可選單位.length > 1) {
    var 選項 = f.可選單位.map(function (u) {
      return '<option value="' + 逸出(u) + '"' +
             (u === f.可選單位[0] ? ' selected' : '') + '>' + 逸出(u) + '</option>';
    }).join('');
    內容 = '\n      <div class="欄"> ' + 輸入 +
           '\n        <select id="u_' + f.id + '">' + 選項 + '</select>\n      </div>';
  } else {
    內容 = '\n      ' + 輸入;
  }

  return '    <label>' + 逸出(f.標籤) +
         (f.說明 ? '<span>' + 逸出(f.說明) + '</span>' : '') +
         內容 +
         '\n      <p class="err" id="err_' + f.id + '"></p></label>\n';
}

var 驗算列 = 設定.驗算.map(function (c, n) {
  return '    <p class="test" id="t' + n + '">—</p>\n';
}).join('') + '    <p class="test" id="tRender">—</p>';

var 樣式 = [
  '  :root { --line:#ddd; --ink:#222; --sub:#666; --ok:#1a7f4b; --bad:#b3261e;',
  '          --warn:#8a5d00; --bg:#faf9f7; }',
  '  * { box-sizing:border-box; }',
  '  body { margin:0; padding:16px; background:var(--bg); color:var(--ink);',
  '         font-family:"Noto Sans TC","Microsoft JhengHei",sans-serif; line-height:1.7; }',
  '  main { max-width:560px; margin:0 auto; }',
  '  h1 { font-size:20px; margin:0 0 4px; }',
  '  p.lead { margin:0 0 20px; color:var(--sub); font-size:14px; }',
  '  section { background:#fff; border:1px solid var(--line); border-radius:8px;',
  '            padding:14px 16px; margin-bottom:14px; }',
  '  h2 { font-size:15px; margin:0 0 10px; }',
  '  label { display:block; margin-bottom:10px; font-size:14px; }',
  '  label span { display:block; color:var(--sub); font-size:12px; }',
  '  input { width:100%; padding:10px; font-size:16px; border:1px solid var(--line);',
  '          border-radius:6px; margin-top:4px; }',
  '  table { width:100%; border-collapse:collapse; font-size:14px; }',
  '  td { padding:5px 0; border-bottom:1px solid var(--line); }',
  '  td:last-child { text-align:right; font-variant-numeric:tabular-nums; }',
  '  .result { font-size:28px; font-weight:500; margin:4px 0; }',
  '  .sub-result { font-size:14px; color:var(--sub); }',
  '  .note { font-size:12px; color:var(--sub); }',
  '  .test { font-size:13px; margin:4px 0; }',
  '  .pass { color:var(--ok); } .fail { color:var(--bad); font-weight:500; }',
  '  input.bad { border-color:var(--bad); background:#fdf5f5; }',
  '  .err { display:none; color:var(--bad); font-size:12px; margin:4px 0 0; }',
  '  .err.on { display:block; }',
  '  .err.warn { color:var(--warn); }',
  '  .result.none { color:var(--sub); font-weight:400; }',
  '  .sub-result.bad { color:var(--bad); }',
  '  .sub-result.warn { color:var(--warn); }',
  '  .欄 { display:flex; gap:8px; align-items:stretch; }',
  '  .欄 input { flex:1; min-width:0; }',
  '  .欄 select { margin-top:4px; padding:10px 8px; font-size:16px;',
  '               border:1px solid var(--line); border-radius:6px; background:#fff; }'
].join('\n');

var 執行期 = [
  'var 設定 = ' + 安全JSON({
    公式: 設定.公式,
    欄位: ids,
    基準單位: 基準單位,
    結果: 設定.結果,
    次要結果: 設定.次要結果 || null,
    驗算: 設定.驗算
  }) + ';',
  '',
  'function $(id) { return document.getElementById(id); }',
  'function f2(v) { return (Math.round(v * 100) / 100).toFixed(2); }',
  '',
  '/* 使用者可以自己選單位；公式只認基準單位，所以讀值時換算回去。',
  '   這樣公式完全不用知道介面讓人選了什麼，換算只發生在這一個地方。 */',
  'function 讀單位(k) {',
  '  var s = $("u_" + k);',
  '  return (s && s.value) ? s.value : 設定.基準單位[k];',
  '}',
  '',
  'function read() {',
  '  var o = {};',
  '  設定.欄位.forEach(function (k) {',
  '    var v = +$(k).value;',
  '    var 從 = 讀單位(k);',
  '    var 到 = 設定.基準單位[k];',
  '    if (從 && 到 && 從 !== 到 && isFinite(v)) {',
  '      try { v = 換算到(v, 從, 到); } catch (e) { /* 換算失敗就交給驗證去報 */ }',
  '    }',
  '    o[k] = v;',
  '  });',
  '  return o;',
  '}',
  '',
  '/* 換單位時把數值一起換算，而不是重新詮釋同一個數字。',
  '   300 公分切成公尺要變成 3，不是維持 300——後者正是差 100 倍的來源。',
  '',
  '   每個欄位另外記一份「基準單位下的值」當作真正的資料，畫面上的數字只是它的呈現。',
  '   換單位時一律從基準值換算，不從上一個顯示值接著換——',
  '   否則修整誤差會一路累積，坪→才→m²→坪 繞一圈會變成 9.9999999。 */',
  'var 目前單位 = {};',
  'var 基準值 = {};',
  '',
  'function 同步基準(k) {',
  '  var v = +$(k).value;',
  '  var 從 = 讀單位(k);',
  '  var 到 = 設定.基準單位[k];',
  '  if (從 && 到 && 從 !== 到 && isFinite(v)) {',
  '    try { 基準值[k] = 換算到(v, 從, 到); return; } catch (e) {}',
  '  }',
  '  基準值[k] = v;',
  '}',
  '',
  'function 換單位(k) {',
  '  var 新 = 讀單位(k);',
  '  var 到 = 設定.基準單位[k];',
  '  if (新 && 到 && isFinite(基準值[k])) {',
  '    /* 用有效位數而不是小數位數修整：固定小數位會讓 360 顯示成 359.999997，',
  '       也會把很小的值（公釐、填縫）直接截成 0。 */',
  '    try { $(k).value = parseFloat(換算到(基準值[k], 到, 新).toPrecision(8)); } catch (e) {}',
  '  }',
  '  目前單位[k] = 新;',
  '  render();',
  '}',
  '',
  'function 清欄位() {',
  '  設定.欄位.forEach(function (k) {',
  '    $(k).className = "";',
  '    var e = $("err_" + k);',
  '    if (e) { e.className = "err"; e.textContent = ""; }',
  '  });',
  '}',
  '',
  'function 標欄位(清單) {',
  '  清單.forEach(function (e) {',
  '    if (!e.欄位 || !$(e.欄位)) { return; }',
  '    if (e.等級 === "錯誤") { $(e.欄位).className = "bad"; }',
  '    var p = $("err_" + e.欄位);',
  '    if (!p) { return; }',
  '    /* 提醒用黃字且不擋計算；錯誤用紅字並擋住結果。',
  '       一律走 class 不用 inline style——class 無頭測試驗得到，style 驗不到。 */',
  '    p.className = e.等級 === "提醒" ? "err on warn" : "err on";',
  '    p.textContent = (e.等級 === "提醒" ? "提醒：" : "") + e.訊息;',
  '  });',
  '}',
  '',
  'function 空結果(主文, 副文, 壞) {',
  '  $("steps").innerHTML = "";',
  '  $("assume").textContent = "";',
  '  $("out").className = "result none";',
  '  $("out").textContent = 主文;',
  '  $("out2").className = 壞 ? "sub-result bad" : "sub-result";',
  '  $("out2").textContent = 副文;',
  '}',
  '',
  'function render() {',
  '  var r = 計算(設定.公式, read());',
  '  var 清單 = r.錯誤 || [];',
  '  清欄位();',
  '  標欄位(清單);',
  '',
  '  var 致命 = 清單.filter(function (e) { return e.等級 === "致命"; });',
  '  if (致命.length) {',
  '    空結果("工具故障", 致命[0].訊息 + "（請回報，不要依賴這次的結果）", true);',
  '    return;',
  '  }',
  '',
  '  var 錯 = 清單.filter(function (e) { return e.等級 === "錯誤"; });',
  '  if (錯.length) {',
  '    /* 絕不留上一次的數字——陳舊數字看起來像新算的，是假自信的來源 */',
  '    var 有欄位 = 錯.filter(function (e) { return e.欄位; });',
  '    空結果("—", 有欄位.length ? 有欄位.length + " 個欄位要修正，詳見上方紅字"',
  '                              : 錯[0].訊息, true);',
  '    return;',
  '  }',
  '',
  '  $("out").className = "result";',
  '  $("out2").className = "sub-result";',
  '  var html = "";',
  '  r.過程.forEach(function (s) {',
  '    html += "<tr><td>" + s.標籤 + "</td><td>" + s.算式 + "</td></tr>";',
  '  });',
  '  $("steps").innerHTML = html;',
  '  $("assume").textContent = r.註記 || "";',
  '  $("out").textContent = r.值[設定.結果.欄位] + " " + 設定.結果.單位;',
  '  if (設定.次要結果) {',
  '    $("out2").textContent = 設定.次要結果.replace(/\{([^}]+)\}/g, function (_, k) {',
  '      return f2(r.值[k]);',
  '    });',
  '  }',
  '',
  '  /* 有提醒時結果區也要講一聲。只在欄位旁放小黃字的話，畫面中央仍是一個',
  '     28px 的大數字，看起來像完全正常的結果——那正是「假自信」的形狀。',
  '     數字照給（提醒不擋計算），但旁邊要說它可疑。 */',
  '  var 提 = 清單.filter(function (e) { return e.等級 === "提醒"; });',
  '  if (提.length) {',
  '    $("out2").className = "sub-result warn";',
  '    $("out2").textContent = $("out2").textContent + "　⚠ " + 提.length +',
  '      " 項提醒，詳見上方黃字";',
  '  }',
  '}',
  '',
  'function mark(el, 通過, 說明) {',
  '  el.className = "test " + (通過 ? "pass" : "fail");',
  '  el.textContent = (通過 ? "通過" : "失敗") + "｜" + 說明;',
  '}',
  '',
  'function 驗算() {',
  '  設定.驗算.forEach(function (c, n) {',
  '    var 值 = 計算(設定.公式, c.輸入).值;',
  '    var 壞掉 = [];',
  '    Object.keys(c.預期).forEach(function (k) {',
  '      var 實得 = Math.round(值[k] * 100) / 100;',
  '      if (實得 !== c.預期[k]) { 壞掉.push(k + " 預期 " + c.預期[k] + "，實得 " + 實得); }',
  '    });',
  '    mark($("t" + n), !壞掉.length, c.標題 + (壞掉.length ? "：" + 壞掉.join("；") : ""));',
  '  });',
  '  var 畫面 = $("steps").textContent + $("out").textContent + $("out2").textContent;',
  '  var 壞值 = ["NaN", "Infinity", "undefined", "工具故障", "要修正"];',
  '  var 有壞值 = 壞值.some(function (k) { return 畫面.indexOf(k) !== -1; });',
  '  mark($("tRender"), !有壞值 && $("out").textContent !== "—",',
  '       "畫面渲染檢查：輸入欄有接到計算引擎，預設值算得出正常結果");',
  '}',
  '',
  '設定.欄位.forEach(function (k) { 目前單位[k] = 讀單位(k); 同步基準(k); });',
  '',
  '/* 逐個欄位綁，不要靠 el.id 反查——元素不一定有 id 屬性可讀，',
  '   綁定時就把欄位名閉包進去比較穩。 */',
  '設定.欄位.forEach(function (k) {',
  '  var 欄 = $(k);',
  '  if (欄) {',
  '    欄.addEventListener("input", function () { 同步基準(k); render(); });',
  '  }',
  '  var 選 = $("u_" + k);',
  '  if (選) {',
  '    選.addEventListener("change", function () { 換單位(k); });',
  '  }',
  '});',
  'render();',
  '驗算();'
].join('\n');

var html = [
  '<!DOCTYPE html>',
  '<html lang="zh-Hant">',
  '<head>',
  '<meta charset="utf-8">',
  '<meta name="viewport" content="width=device-width, initial-scale=1">',
  '<title>' + 逸出(設定.標題) + '</title>',
  '<style>',
  樣式,
  '</style>',
  '</head>',
  '<body>',
  '<main>',
  '  <h1>' + 逸出(設定.標題) + '</h1>',
  '  <p class="lead">' + 逸出(設定.說明) + '</p>',
  '',
  '  <section>',
  '    <h2>現場量到的數字</h2>',
  (設定.輸入 || []).map(欄).join('').replace(/\n$/, ''),
  '  </section>',
  '',
  '  <section>',
  '    <h2>假設參數（可改）</h2>',
  (設定.參數 || []).map(欄).join('').replace(/\n$/, ''),
  '  </section>',
  '',
  '  <section>',
  '    <h2>計算過程</h2>',
  '    <table id="steps"></table>',
  '    <p class="note" id="assume"></p>',
  '  </section>',
  '',
  '  <section>',
  '    <h2>結果</h2>',
  '    <div class="result" id="out">—</div>',
  '    <div class="sub-result" id="out2">—</div>',
  '    <p class="note">' + 逸出(設定.免責) + '</p>',
  '  </section>',
  '',
  '  <section>',
  '    <h2>引擎自我測試</h2>',
  '    <p class="note">固定案例，開頁時跑一次，<strong>與你目前輸入的數字無關</strong>。',
  '      上面出現紅字是你的輸入要改，這裡是綠的代表計算引擎本身沒壞，兩件事不衝突。</p>',
  驗算列,
  '    <p class="note">這裡顯示失敗代表公式或設定被改壞了，',
  '      先重新手算公式，不要直接改預期值。</p>',
  '  </section>',
  '</main>',
  '',
  '<script>',
  fs.readFileSync(path.join(__dirname, '公式.js'), 'utf8').trim(),
  '</script>',
  '<script>',
  執行期,
  '</script>',
  '</body>',
  '</html>',
  ''
].join('\n');

var 輸出路徑 = path.join(輸出資料夾, 設定.檔名);
fs.writeFileSync(輸出路徑, html, 'utf8');
console.log('已產生：' + 輸出路徑);
console.log('  ' + html.length + ' bytes，' + 設定.驗算.length + ' 組驗算，公式「' + 設定.公式 + '」');
