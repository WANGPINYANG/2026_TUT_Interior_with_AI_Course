/* 自我檢查：跑法 node scripts/測試.js
   用假逐字稿驗解析器，確認它抓得到該抓的、不抓不該抓的。
   最重要的一條：skill 名字出現在對話文字裡（例如路由表被注入）不可以被算成一次呼叫——
   2026-09-19 建這支工具時實測過，天真的字串比對會把 interior-boq-quote 算成 216 次。 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const 蒐集 = require('./蒐集.js');

let 失敗 = 0;
function 驗(名稱, 實得, 預期) {
  const 過 = JSON.stringify(實得) === JSON.stringify(預期);
  if (!過) 失敗++;
  console.log('  ' + (過 ? '通過' : '失敗') + '｜' + 名稱 +
              (過 ? '' : '　預期 ' + JSON.stringify(預期) + '，實得 ' + JSON.stringify(實得)));
}

const 暫存 = fs.mkdtempSync(path.join(os.tmpdir(), 'skill-audit-test-'));
const 假稿 = path.join(暫存, 'fake.jsonl');

const 行 = [
  /* 真的呼叫，要算 */
  JSON.stringify({
    type: 'assistant', sessionId: 's1', timestamp: '2026-09-01T10:00:00.000Z',
    message: { role: 'assistant', content: [
      { type: 'tool_use', id: 'a', name: 'Skill', input: { skill: 'interior-ledger', args: '記一筆' } }
    ] }
  }),
  /* 同一個 skill 第二次，不同 session */
  JSON.stringify({
    type: 'assistant', sessionId: 's2', timestamp: '2026-09-05T10:00:00.000Z',
    message: { role: 'assistant', content: [
      { type: 'tool_use', id: 'b', name: 'Skill', input: { skill: 'interior-ledger', args: '' } }
    ] }
  }),
  /* 陷阱一：skill 名出現在使用者訊息文字裡（路由表注入），不可算 */
  JSON.stringify({
    type: 'user', sessionId: 's1', timestamp: '2026-09-02T10:00:00.000Z',
    message: { role: 'user', content: [
      { type: 'text', text: '報價 → interior-boq-quote skill；記帳 → interior-ledger skill' }
    ] }
  }),
  /* 陷阱二：別的工具，名字裡有 skill 字樣，不可算 */
  JSON.stringify({
    type: 'assistant', sessionId: 's1', timestamp: '2026-09-03T10:00:00.000Z',
    message: { role: 'assistant', content: [
      { type: 'tool_use', id: 'c', name: 'ListSkills', input: {} }
    ] }
  }),
  /* 陷阱三：壞掉的 JSON，要被算進壞行而不是讓整支掛掉 */
  '{"type":"assistant","message":{"content":[{"name":"Skill"',
  /* 另一個 skill，只有一次 */
  JSON.stringify({
    type: 'assistant', sessionId: 's3', timestamp: '2026-08-20T10:00:00.000Z',
    message: { role: 'assistant', content: [
      { type: 'tool_use', id: 'd', name: 'Skill', input: { skill: 'thesis-workbench', args: '' } }
    ] }
  })
];
fs.writeFileSync(假稿, 行.join('\n') + '\n', 'utf8');

(async function () {
  const r = await 蒐集.掃逐字稿(暫存);

  驗('interior-ledger 算到 2 次', r.統計['interior-ledger'] && r.統計['interior-ledger'].次數, 2);
  驗('interior-ledger 橫跨 2 個 session', r.統計['interior-ledger'].sessions.size, 2);
  驗('interior-ledger 最近一次', r.統計['interior-ledger'].最近, '2026-09-05T10:00:00.000Z');
  驗('thesis-workbench 算到 1 次', r.統計['thesis-workbench'].次數, 1);
  驗('路由表注入不算呼叫', r.統計['interior-boq-quote'], undefined);
  驗('ListSkills 不算呼叫', Object.keys(r.統計).sort(), ['interior-ledger', 'thesis-workbench']);
  驗('壞行被記錄而非中斷', r.壞行, 1);
  驗('最早時間', r.最早, '2026-08-20T10:00:00.000Z');

  const 龍蝦 = 蒐集.讀龍蝦用量();
  console.log('  ' + (龍蝦.錯誤 ? '注意' : '通過') + '｜龍蝦資料庫　' +
              (龍蝦.錯誤 || 龍蝦.筆數 + ' 筆'));

  fs.rmSync(暫存, { recursive: true, force: true });
  console.log('');
  console.log(失敗 ? '共 ' + 失敗 + ' 項失敗' : '全部通過');
  process.exit(失敗 ? 1 : 0);
})();
