/* 壞值矩陣掃描。跑法：node scripts/壞值掃描.test.js
   來源：2026-10-03 課程 SOP 的壞值清單——0／負數／空白／非數字／極大值。

   為什麼要有這支：公式.test.js 是「我想得到的案例」，這支是「照單子逐格掃」。
   2026-10-03 自測時，公式.test.js 15 組全綠、產出檢查 11 項全綠、第三方稽核也沒抓到，
   卻被這份清單掃出 11 個欄位填極大值會算出 Infinity。
   差別在於：這支會自動涵蓋未來新增的欄位與公式，不靠人記得要測。

   判定：每一格的結果只有三種可接受——被擋下、算出有限且非負的數字、或明確的提醒。
         出現 NaN／Infinity／負的用量而沒被擋，就是失敗。 */
'use strict';

var 引擎 = require('./公式.js');

/* 每個公式一組合法基準值，掃描時逐欄替換成壞值 */
var 基準 = {
  油漆: { ping: 10, wallH: 2.8, perim: 0, openArea: 6, rate: 9, coats: 2, loss: 10 },
  窗簾: { 窗寬: 300, 窗高: 240, 倍數: 2, 幅寬: 280, 兩側收邊: 10, 上下摺邊: 25 },
  磁磚: { 長: 4, 寬: 3, 扣除: 0, 磚長: 60, 磚寬: 60, 填縫: 3, 損耗: 8, 每箱片數: 4 }
};

var 壞值 = [
  ['0', 0],
  ['負數', -5],
  ['空白', NaN],
  ['非數字', 'abc'],
  ['極大值', 1e308]
];

var 失敗 = [];
var 總格數 = 0;

Object.keys(基準).forEach(function (公式) {
  if (!引擎.公式[公式]) {
    失敗.push({ 公式: 公式, 欄位: '-', 壞名: '-', 症狀: '基準值裡有這個公式，引擎裡卻沒有' });
    return;
  }
  Object.keys(基準[公式]).forEach(function (欄位) {
    壞值.forEach(function (pair) {
      總格數++;
      var 壞名 = pair[0];
      var 輸入 = {};
      Object.keys(基準[公式]).forEach(function (k) { 輸入[k] = 基準[公式][k]; });
      輸入[欄位] = pair[1];

      var r;
      try {
        r = 引擎.計算(公式, 輸入);
      } catch (e) {
        失敗.push({ 公式: 公式, 欄位: 欄位, 壞名: 壞名, 症狀: '拋出例外：' + e.message });
        return;
      }

      var 擋下 = (r.錯誤 || []).filter(function (e) {
        return e.等級 === '錯誤' || e.等級 === '致命';
      });
      if (擋下.length) {
        /* 被擋下就合格，但錯誤物件的形狀也要對，否則畫面標不到欄位 */
        var 形狀壞 = 擋下.filter(function (e) {
          return typeof e.訊息 !== 'string' || !e.訊息 || !('欄位' in e);
        });
        if (形狀壞.length) {
          失敗.push({ 公式: 公式, 欄位: 欄位, 壞名: 壞名, 症狀: '擋下了但錯誤物件缺欄位或訊息' });
        }
        return;
      }

      var 非有限 = Object.keys(r.值).filter(function (k) {
        return typeof r.值[k] === 'number' && !isFinite(r.值[k]);
      });
      if (非有限.length) {
        失敗.push({ 公式: 公式, 欄位: 欄位, 壞名: 壞名,
                    症狀: '放行且輸出非有限值：' + 非有限.join('、') });
        return;
      }

      var 負值 = Object.keys(r.值).filter(function (k) {
        return typeof r.值[k] === 'number' && r.值[k] < 0;
      });
      if (負值.length) {
        失敗.push({ 公式: 公式, 欄位: 欄位, 壞名: 壞名,
                    症狀: '放行且輸出負數：' + 負值.join('、') });
      }
    });
  });
});

console.log('壞值矩陣掃描：' + Object.keys(基準).length + ' 個公式 × 各欄位 × ' +
            壞值.length + ' 種壞值 = ' + 總格數 + ' 格');
console.log('壞值清單：' + 壞值.map(function (p) { return p[0]; }).join('／'));
console.log('');

if (!失敗.length) {
  console.log('全部 ' + 總格數 + ' 格通過——每格不是被擋下，就是算出有限且非負的結果。');
  process.exit(0);
}

console.log('── 失敗 ' + 失敗.length + ' 格 ──');
失敗.forEach(function (f, i) {
  console.log('  ' + (i + 1) + '. ' + f.公式 + '｜' + f.欄位 + ' 填' + f.壞名 + ' → ' + f.症狀);
});
console.log('');
console.log('共 ' + 失敗.length + ' 格失敗');
process.exit(1);
