/* 暴力測試。跑法：node scripts/暴力測試.test.js
   攻擊面超出課程壞值清單的範圍，約一萬次呼叫。

   A 型別攻擊　灌入非數字型別，確認引擎不把它們當數字算
   B 數值邊界　MAX_VALUE／MIN_VALUE／denormal／負零／極小正數
   C 組合溢位　多欄同時給大值；每欄單獨都不爆，乘起來才爆
   D 隨機模糊　固定種子的亂數組合，每個公式數千次

   跟 壞值掃描.test.js 的分工：那支是「照課程清單逐格掃」，看得懂、對得上 SOP；
   這支是「盡量亂打」，涵蓋清單想不到的組合。兩支都要留。

   合格定義：被擋下（錯誤物件完整），或算出有限且非負的值。
   任何 NaN／Infinity／負的用量／拋出例外，都算失敗。
   種子固定，所以每次跑的案例完全相同——失敗可以重現。 */
'use strict';

var 引擎 = require('./公式.js');

var 基準 = {
  油漆: { ping: 10, wallH: 2.8, perim: 0, openArea: 6, rate: 9, coats: 2, loss: 10 },
  窗簾: { 窗寬: 300, 窗高: 240, 倍數: 2, 幅寬: 280, 兩側收邊: 10, 上下摺邊: 25 },
  磁磚: { 長: 4, 寬: 3, 扣除: 0, 磚長: 60, 磚寬: 60, 填縫: 3, 損耗: 8, 每箱片數: 4 }
};

var 失敗 = [];
var 次數 = 0;

function 複製(o) {
  var n = {};
  Object.keys(o).forEach(function (k) { n[k] = o[k]; });
  return n;
}

function 判(公式, 標籤, 輸入) {
  次數++;
  var r;
  try {
    r = 引擎.計算(公式, 輸入);
  } catch (e) {
    失敗.push({ 公式: 公式, 標籤: 標籤, 症狀: '拋出例外：' + e.message });
    return;
  }
  if (!r || typeof r !== 'object') {
    失敗.push({ 公式: 公式, 標籤: 標籤, 症狀: '回傳不是物件' });
    return;
  }

  var 擋下 = (r.錯誤 || []).filter(function (e) {
    return e.等級 === '錯誤' || e.等級 === '致命';
  });
  if (擋下.length) {
    var 形狀壞 = 擋下.filter(function (e) {
      return typeof e.訊息 !== 'string' || !e.訊息 || !('欄位' in e) || !e.等級;
    });
    if (形狀壞.length) {
      失敗.push({ 公式: 公式, 標籤: 標籤, 症狀: '擋下了但錯誤物件形狀不對（畫面會標不到欄位）' });
    }
    return;
  }

  var 壞 = [];
  Object.keys(r.值).forEach(function (k) {
    var v = r.值[k];
    if (typeof v !== 'number') { 壞.push(k + ' 不是數字'); return; }
    if (!isFinite(v)) { 壞.push(k + '=' + v); return; }
    if (v < 0) { 壞.push(k + '=' + v + '（負數）'); }
  });
  if (壞.length) {
    失敗.push({ 公式: 公式, 標籤: 標籤, 症狀: '放行但輸出壞值：' + 壞.join('、') });
  }
}

/* ── A 型別攻擊 ── */
var 怪型別 = [
  ['null', null], ['undefined', undefined], ['true', true], ['false', false],
  ['空字串', ''], ['空白字串', '   '], ['數字字串', '5'], ['陣列', []],
  ['物件', {}], ['函式', function () {}], ['Infinity', Infinity],
  ['-Infinity', -Infinity], ['科學記號字串', '1e309'], ['十六進位字串', '0x10']
];

/* ── B 數值邊界 ── */
var 邊界 = [
  ['MAX_VALUE', Number.MAX_VALUE], ['MIN_VALUE', Number.MIN_VALUE],
  ['EPSILON', Number.EPSILON], ['負零', -0], ['極小正數', 1e-308],
  ['denormal', 5e-324], ['MAX_SAFE_INTEGER', Number.MAX_SAFE_INTEGER],
  ['1e308', 1e308], ['0.1', 0.1], ['三分之一', 1 / 3]
];

[['A 型別', 怪型別], ['B 邊界', 邊界]].forEach(function (組) {
  Object.keys(基準).forEach(function (公式) {
    Object.keys(基準[公式]).forEach(function (欄位) {
      組[1].forEach(function (p) {
        var i = 複製(基準[公式]);
        i[欄位] = p[1];
        判(公式, 組[0] + '｜' + 欄位 + '=' + p[0], i);
      });
    });
  });
});

/* ── C 組合溢位 ── */
Object.keys(基準).forEach(function (公式) {
  var 欄 = Object.keys(基準[公式]);
  [1e100, 1e150, 1e200, 1e300].forEach(function (v) {
    var 全 = 複製(基準[公式]);
    欄.forEach(function (k) { 全[k] = v; });
    判(公式, 'C 組合｜全欄=' + v, 全);
    for (var a = 0; a < 欄.length; a++) {
      for (var b = a + 1; b < 欄.length; b++) {
        var j = 複製(基準[公式]);
        j[欄[a]] = v;
        j[欄[b]] = v;
        判(公式, 'C 組合｜' + 欄[a] + '+' + 欄[b] + '=' + v, j);
      }
    }
  });
});

/* ── D 隨機模糊（固定種子，失敗可重現）── */
var 候選 = [0, 1, -1, 0.5, -0.5, 1e-300, 1e300, 1e308, 1e-10, 12345678,
            NaN, Infinity, -Infinity, Number.MAX_VALUE, Number.MIN_VALUE];
var 種子 = 20261003;
function 亂() {
  種子 = (種子 * 1103515245 + 12345) % 2147483648;
  return 種子 / 2147483648;
}
Object.keys(基準).forEach(function (公式) {
  var 欄 = Object.keys(基準[公式]);
  for (var n = 0; n < 3000; n++) {
    var i = 複製(基準[公式]);
    欄.forEach(function (k) {
      if (亂() < 0.5) { i[k] = 候選[Math.floor(亂() * 候選.length)]; }
    });
    判(公式, 'D 隨機 #' + n, i);
  }
});

console.log('暴力測試：共 ' + 次數 + ' 次呼叫（種子 20261003，可重現）');
console.log('');

if (!失敗.length) {
  console.log('全部通過——沒有一次算出 NaN／Infinity／負的用量，也沒有拋出例外。');
  process.exit(0);
}

var 歸類 = {};
失敗.forEach(function (f) {
  var key = f.公式 + '｜' + f.症狀.replace(/#\d+/, '').replace(/=[-\d.e+]+/g, '=…');
  歸類[key] = (歸類[key] || 0) + 1;
});
console.log('── 失敗 ' + 失敗.length + ' 次，歸類後 ' + Object.keys(歸類).length + ' 種 ──');
Object.keys(歸類).sort(function (a, b) { return 歸類[b] - 歸類[a]; }).forEach(function (k) {
  console.log('  ' + String(歸類[k]).padStart(5) + ' 次  ' + k);
});
console.log('');
console.log('── 前 8 個實例（種子固定，可直接重現）──');
失敗.slice(0, 8).forEach(function (f, i) {
  console.log('  ' + (i + 1) + '. ' + f.公式 + '｜' + f.標籤 + ' → ' + f.症狀);
});
console.log('');
console.log('共 ' + 失敗.length + ' 次失敗');
process.exit(1);
