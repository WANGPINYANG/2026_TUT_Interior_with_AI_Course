/* 主程式：跑法 node scripts/稽核.js [--json]
   把三個來源合起來，分類每個 skill 的處置建議。只讀不刪。
   分類規則寫死在這裡，因為「0 次的原因不同，處置完全相反」是這個工具的全部價值。 */
'use strict';

const 蒐集 = require('./蒐集.js');

const 活躍天數 = 30;
const 季節性關鍵字 = ['交屋', '保固', '回訪', '結案', '年度', '報稅',
                      '口試', '投稿', '期末', '驗收', '合約', '簽約'];

function 天前(iso) {
  if (!iso) return null;
  return Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
}

function 分類(s) {
  if (s.次數 > 0) {
    const d = 天前(s.最近);
    if (d !== null && d <= 活躍天數) return { 類別: '活躍', 建議: '留著' };
    if (s.次數 >= 3) return { 類別: '低頻但常回來', 建議: '留著' };
    return { 類別: '低頻', 建議: '留著，再觀察' };
  }
  if (s.無資料來源) {
    return { 類別: '無用量資料', 建議: '不能判斷，先別動' };
  }
  if (s.被路由表指名) {
    return { 類別: '零次但路由表有指名', 建議: '修觸發條件，不是刪' };
  }
  if (s.是連結) {
    return { 類別: '零次且是外部連結', 建議: '刪連結不等於刪 skill，先查來源' };
  }
  if (s.季節性) {
    return { 類別: '零次但看起來是季節性', 建議: '留著，等那個季節到再評估' };
  }
  return { 類別: '零次且無人指名', 建議: '可刪候選，你確認後手動刪' };
}

(async function () {
  const 輸出JSON = process.argv.includes('--json');

  const 逐字稿 = await 蒐集.掃逐字稿();
  const 龍蝦 = 蒐集.讀龍蝦用量();
  const 路由 = 蒐集.讀路由表();
  /* 排除這支工具自己，否則它永遠會把自己列成可刪候選 */
  const 清單 = 蒐集.盤點(蒐集.路徑.claude技能, 'Claude')
    .concat(蒐集.盤點(蒐集.路徑.龍蝦技能, '龍蝦'))
    .filter(function (i) { return i.名稱 !== 'skill-usage-audit'; });

  /* 龍蝦的 skill_usage 整張表都是空的時，代表沒有資料，不是用了 0 次。
     兩者處置完全不同：前者不能下任何刪除建議。 */
  const 龍蝦無資料 = !!龍蝦.錯誤 || 龍蝦.筆數 === 0;

  const 結果 = 清單.map(function (item) {
    const 用量 = item.擁有者 === 'Claude'
      ? (逐字稿.統計[item.名稱] || { 次數: 0, 首次: null, 最近: null, sessions: new Set() })
      : (龍蝦.統計[item.名稱] || { 次數: 0, 首次: null, 最近: null });

    const 無資料來源 = item.擁有者 === 'Claude' ? !!逐字稿.錯誤 : 龍蝦無資料;
    const 文字 = item.名稱 + ' ' + item.描述;

    const s = {
      名稱: item.名稱,
      擁有者: item.擁有者,
      是連結: item.是連結,
      連結目標: item.連結目標,
      次數: 用量.次數 || 0,
      首次: 用量.首次,
      最近: 用量.最近,
      sessions: 用量.sessions ? 用量.sessions.size : null,
      被路由表指名: 路由.內容.indexOf(item.名稱) !== -1,
      季節性: 季節性關鍵字.some(function (k) { return 文字.indexOf(k) !== -1; }),
      無資料來源: 無資料來源
    };
    const c = 分類(s);
    s.類別 = c.類別;
    s.建議 = c.建議;
    return s;
  });

  if (輸出JSON) {
    console.log(JSON.stringify({
      產生時間: new Date().toISOString(),
      資料涵蓋: { 最早: 逐字稿.最早, 最晚: 逐字稿.最晚 },
      來源狀態: {
        逐字稿: 逐字稿.錯誤 || (逐字稿.檔案數 + ' 檔 / ' + 逐字稿.行數 + ' 行 / 壞行 ' + 逐字稿.壞行),
        龍蝦: 龍蝦.錯誤 || (龍蝦.筆數 + ' 筆'),
        路由表: { 讀到: 路由.讀到, 讀不到: 路由.讀不到 }
      },
      skills: 結果
    }, null, 2));
    return;
  }

  console.log('skill 使用稽核');
  console.log('');
  console.log('資料來源');
  console.log('  Claude 逐字稿：' + (逐字稿.錯誤 ||
    (逐字稿.檔案數 + ' 個檔、' + 逐字稿.行數 + ' 行，解析失敗 ' + 逐字稿.壞行 + ' 行')));
  console.log('  涵蓋期間　　：' + (逐字稿.最早 || '?').slice(0, 10) + ' ～ ' + (逐字稿.最晚 || '?').slice(0, 10));
  console.log('  龍蝦 skill_usage：' + (龍蝦.錯誤 ||
    (龍蝦.筆數 + ' 筆' + (龍蝦.筆數 === 0 ? '（表存在但沒有資料，龍蝦的 skill 一律列為無法判斷）' : ''))));
  if (路由.讀不到.length) console.log('  路由表讀不到：' + 路由.讀不到.join('、'));
  console.log('');

  const 順序 = ['活躍', '低頻但常回來', '低頻', '零次但路由表有指名',
                '零次但看起來是季節性', '零次且是外部連結', '零次且無人指名', '無用量資料'];
  for (const 類 of 順序) {
    const 群 = 結果.filter(function (r) { return r.類別 === 類; });
    if (!群.length) continue;
    console.log('── ' + 類 + '（' + 群.length + '）　→ ' + 群[0].建議 + ' ──');
    群.sort(function (a, b) { return b.次數 - a.次數; });
    for (const r of 群) {
      console.log('  ' + String(r.次數).padStart(3) + ' 次  ' +
                  (r.最近 ? r.最近.slice(0, 10) : '　　　　　') + '  ' +
                  r.名稱.padEnd(28) + ' [' + r.擁有者 + (r.是連結 ? '/連結' : '') + ']');
    }
    console.log('');
  }

  const 可刪 = 結果.filter(function (r) { return r.類別 === '零次且無人指名'; });
  console.log('小結：共 ' + 結果.length + ' 個 skill，' +
              結果.filter(r => r.次數 > 0).length + ' 個有使用紀錄，' +
              可刪.length + ' 個列為可刪候選。');
  console.log('');
  console.log('注意：零次不等於沒用。逐字稿只記 Skill 工具的顯式呼叫——');
  console.log('工作被直接做掉而沒走 skill，這裡就是零次。刪之前請先確認是哪一種。');
  console.log('這支腳本只讀不刪，刪除一律由你手動執行。');
})();
