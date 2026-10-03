/* 計算引擎測試。跑法：node scripts/公式.test.js
   預期值一律用手算求得後寫死，不准從程式輸出回填——那樣測試就只是在複誦程式。
   改公式之後這裡沒過，先確認是公式對還是預期值對，不要直接改預期值。 */
'use strict';

var 計算 = require('./公式.js').計算;

var 失敗 = 0;

/* ── 正常案例：算得對不對 ── */
var 案例 = [
  {
    名稱: '油漆｜10 坪、淨高 2.8、扣 6 m²、由坪數推估',
    公式: '油漆',
    輸入: { ping: 10, wallH: 2.8, perim: 0, openArea: 6, rate: 9, coats: 2, loss: 10 },
    預期: { 公升: 14.27, 加侖數: 4 }
  },
  {
    名稱: '油漆｜實測周長 20 m、淨高 2.8、扣 6 m²',
    公式: '油漆',
    輸入: { ping: 10, wallH: 2.8, perim: 20, openArea: 6, rate: 9, coats: 2, loss: 10 },
    預期: { 公升: 12.22, 加侖數: 4 }
  },
  {
    名稱: '窗簾｜窗寬 300、窗高 240、2 倍摺、幅寬 280',
    公式: '窗簾',
    輸入: { 窗寬: 300, 窗高: 240, 倍數: 2, 幅寬: 280, 兩側收邊: 10, 上下摺邊: 25 },
    預期: { 幅數: 3, 總碼數: 8.69, 建議碼數: 9 }
  },
  {
    名稱: '磁磚｜4×3 m、60×60 磚、填縫 3 mm、損耗 8%、每箱 4 片',
    公式: '磁磚',
    輸入: { 長: 4, 寬: 3, 扣除: 0, 磚長: 60, 磚寬: 60, 填縫: 3, 損耗: 8, 每箱片數: 4 },
    預期: { 片數: 36, 箱數: 9 }
  }
];

console.log('── 算得對不對 ──');
案例.forEach(function (c) {
  var r = 計算(c.公式, c.輸入);
  var 壞掉 = [];
  var 被擋 = (r.錯誤 || []).filter(function (e) { return e.等級 !== '提醒'; });
  if (被擋.length) {
    壞掉.push('不該被擋下：' + 被擋.map(function (e) { return e.訊息; }).join('、'));
  }
  Object.keys(c.預期).forEach(function (k) {
    var 實得 = Math.round(r.值[k] * 100) / 100;
    if (實得 !== c.預期[k]) { 壞掉.push(k + ' 預期 ' + c.預期[k] + '，實得 ' + 實得); }
  });
  if (壞掉.length) {
    失敗++;
    console.log('  失敗｜' + c.名稱);
    壞掉.forEach(function (s) { console.log('        ' + s); });
  } else {
    console.log('  通過｜' + c.名稱);
  }
});

/* ── 錯誤輸入：擋不擋得住 ──
   全部來自 2026-09-19 第三方稽核實際踩出來的案例。
   沒有驗證時這些會算出 Infinity、負數或 NaN，而且畫面照樣顯示。 */
var 基本 = { ping: 10, wallH: 2.8, perim: 0, openArea: 6, rate: 9, coats: 2, loss: 10 };
function 改(覆蓋) {
  var o = {};
  Object.keys(基本).forEach(function (k) { o[k] = 基本[k]; });
  Object.keys(覆蓋).forEach(function (k) { o[k] = 覆蓋[k]; });
  return o;
}

var 錯誤案例 = [
  { 名稱: '塗佈率填 0（原本會算出 Infinity）', 輸入: 改({ rate: 0 }), 應含: '每公升塗佈面積' },
  { 名稱: '塗佈率填負數', 輸入: 改({ rate: -5 }), 應含: '每公升塗佈面積' },
  { 名稱: '塗佈率是 NaN（欄位清空）', 輸入: 改({ rate: NaN }), 應含: '要填數字' },
  { 名稱: '損耗率填負數（原本會算出負加侖）', 輸入: 改({ loss: -200 }), 應含: '損耗率' },
  { 名稱: '坪數填負數（原本會算出 NaN）', 輸入: 改({ ping: -5 }), 應含: '地坪' },
  { 名稱: '淨高填 0', 輸入: 改({ wallH: 0 }), 應含: '牆面淨高' },
  { 名稱: '道數填小數', 輸入: 改({ coats: 2.5 }), 應含: '整數' },
  { 名稱: '道數填 0', 輸入: 改({ coats: 0 }), 應含: '塗刷道數' }
];

console.log('');
console.log('── 錯誤輸入擋不擋得住 ──');
錯誤案例.forEach(function (c) {
  var r = 計算('油漆', c.輸入);
  var 擋下 = (r.錯誤 || []).filter(function (e) { return e.等級 === '錯誤'; });
  var 有擋 = 擋下.length > 0;
  var 訊息對 = 擋下.some(function (e) { return e.訊息.indexOf(c.應含) !== -1; });
  var 有欄位 = 擋下.every(function (e) { return e.欄位 !== undefined; });
  var 值是空的 = Object.keys(r.值).length === 0;
  if (有擋 && 訊息對 && 值是空的 && 有欄位) {
    console.log('  通過｜' + c.名稱);
  } else {
    失敗++;
    console.log('  失敗｜' + c.名稱 +
                (有擋 ? (訊息對 ? (值是空的 ? '　錯誤物件缺欄位' : '　但值沒清空')
                                : '　訊息是「' + 擋下.map(function (e) { return e.訊息; }).join('、') + '」')
                      : '　完全沒擋'));
  }
});

/* ── 其他公式的必要驗證 ── */
console.log('');
console.log('── 其他公式 ──');
[
  { 名稱: '窗簾｜幅寬 0', 公式: '窗簾',
    輸入: { 窗寬: 300, 窗高: 240, 倍數: 2, 幅寬: 0, 兩側收邊: 10, 上下摺邊: 25 }, 應含: '幅寬' },
  { 名稱: '磁磚｜每箱片數 0', 公式: '磁磚',
    輸入: { 長: 4, 寬: 3, 扣除: 0, 磚長: 60, 磚寬: 60, 填縫: 3, 損耗: 8, 每箱片數: 0 }, 應含: '每箱片數' },
  { 名稱: '磁磚｜磚長 0（會造成除以零）', 公式: '磁磚',
    輸入: { 長: 4, 寬: 3, 扣除: 0, 磚長: 0, 磚寬: 60, 填縫: 3, 損耗: 8, 每箱片數: 4 }, 應含: '磚長' }
].forEach(function (c) {
  var r = 計算(c.公式, c.輸入);
  var 過 = (r.錯誤 || []).some(function (e) {
    return e.等級 === '錯誤' && e.訊息.indexOf(c.應含) !== -1;
  });
  if (!過) 失敗++;
  console.log('  ' + (過 ? '通過' : '失敗') + '｜' + c.名稱);
});

console.log('');
console.log(失敗 ? '共 ' + 失敗 + ' 組失敗' : '全部通過');
process.exit(失敗 ? 1 : 0);
