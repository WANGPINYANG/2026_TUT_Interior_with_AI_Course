/* 資料蒐集層：三個來源，純讀取，不改任何檔案。
   1. Claude 逐字稿  ~/.claude/projects/**  的 Skill 工具呼叫
   2. 龍蝦 SQLite    ~/.openclaw/state/openclaw.sqlite 的 skill_usage 表
   3. 檔案系統       ~/.claude/skills 與 D:/Claude/skills 的清單、description、符號連結
   任何一個來源掛掉都要回報，不可以靜默當成「沒用過」。 */
'use strict';

const fs = require('fs');
const path = require('path');
const readline = require('readline');

const 路徑 = {
  逐字稿根: 'C:/Users/jason/.claude/projects',
  claude技能: 'C:/Users/jason/.claude/skills',
  龍蝦技能: 'D:/Claude/skills',
  龍蝦DB: 'C:/Users/jason/.openclaw/state/openclaw.sqlite',
  路由表: ['D:/Claude/CLAUDE.md', 'D:/Claude/AGENTS.md']
};

/* ── 來源 1：Claude 逐字稿 ── */
async function 掃逐字稿(根 = 路徑.逐字稿根) {
  const out = { 統計: {}, 檔案數: 0, 行數: 0, 壞行: 0, 最早: null, 最晚: null, 錯誤: null };
  let 檔案 = [];
  try {
    (function 走(d) {
      for (const e of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, e.name);
        if (e.isDirectory()) 走(p);
        else if (e.name.endsWith('.jsonl')) 檔案.push(p);
      }
    })(根);
  } catch (e) {
    out.錯誤 = '讀不到逐字稿目錄：' + e.message;
    return out;
  }

  for (const f of 檔案) {
    out.檔案數++;
    const rl = readline.createInterface({
      input: fs.createReadStream(f, 'utf8'), crlfDelay: Infinity
    });
    for await (const line of rl) {
      out.行數++;
      const 有時間 = line.indexOf('"timestamp"') !== -1;
      const 有技能 = line.indexOf('"name":"Skill"') !== -1;
      if (!有時間 && !有技能) continue;
      let rec;
      try { rec = JSON.parse(line); } catch (e) { out.壞行++; continue; }
      if (rec.timestamp) {
        if (!out.最早 || rec.timestamp < out.最早) out.最早 = rec.timestamp;
        if (!out.最晚 || rec.timestamp > out.最晚) out.最晚 = rec.timestamp;
      }
      if (!有技能) continue;
      const msg = rec.message;
      if (!msg || !Array.isArray(msg.content)) continue;
      for (const c of msg.content) {
        if (c && c.type === 'tool_use' && c.name === 'Skill' && c.input && c.input.skill) {
          const k = c.input.skill;
          if (!out.統計[k]) out.統計[k] = { 次數: 0, 首次: null, 最近: null, sessions: new Set() };
          const s = out.統計[k];
          s.次數++;
          if (rec.sessionId) s.sessions.add(rec.sessionId);
          if (rec.timestamp) {
            if (!s.首次 || rec.timestamp < s.首次) s.首次 = rec.timestamp;
            if (!s.最近 || rec.timestamp > s.最近) s.最近 = rec.timestamp;
          }
        }
      }
    }
  }
  return out;
}

/* ── 來源 2：龍蝦 skill_usage ── */
function 讀龍蝦用量(db路徑 = 路徑.龍蝦DB) {
  const out = { 統計: {}, 筆數: 0, 錯誤: null };
  let DatabaseSync;
  try { ({ DatabaseSync } = require('node:sqlite')); }
  catch (e) { out.錯誤 = '這個 Node 沒有 node:sqlite（需要 Node 22 以上）：' + e.message; return out; }
  let db;
  try { db = new DatabaseSync(db路徑, { readOnly: true }); }
  catch (e) { out.錯誤 = '開不了龍蝦資料庫：' + e.message; return out; }
  try {
    const 有表 = db.prepare('SELECT name FROM sqlite_master WHERE type=? AND name=?')
      .get('table', 'skill_usage');
    if (!有表) { out.錯誤 = 'skill_usage 資料表不存在（龍蝦版本可能不同）'; return out; }
    for (const r of db.prepare('SELECT * FROM skill_usage').all()) {
      out.筆數++;
      out.統計[r.skill_name] = {
        次數: r.use_count,
        首次: new Date(r.first_used_at_ms).toISOString(),
        最近: new Date(r.last_used_at_ms).toISOString(),
        來源: r.skill_source
      };
    }
  } catch (e) {
    out.錯誤 = '查詢失敗：' + e.message;
  } finally {
    try { db.close(); } catch (e) { /* 關不掉不影響結果 */ }
  }
  return out;
}

/* ── 來源 3：檔案系統盤點 ── */
function 讀描述(skillMd) {
  try {
    const s = fs.readFileSync(skillMd, 'utf8');
    const m = s.match(/^---\r?\n([\s\S]*?)\r?\n---/);
    if (!m) return '';
    const d = m[1].match(/^description:\s*(.+)$/m);
    return d ? d[1].trim() : '';
  } catch (e) { return ''; }
}

function 盤點(目錄, 擁有者) {
  const out = [];
  let entries;
  try { entries = fs.readdirSync(目錄, { withFileTypes: true }); }
  catch (e) { return out; }
  for (const e of entries) {
    const p = path.join(目錄, e.name);
    const 是連結 = e.isSymbolicLink();
    let 是目錄 = e.isDirectory();
    let 連結目標 = null;
    if (是連結) {
      try { 連結目標 = fs.readlinkSync(p); } catch (err) { /* 目標可能已消失 */ }
      try { 是目錄 = fs.statSync(p).isDirectory(); } catch (err) { 是目錄 = false; }
    }
    if (!是目錄) continue;
    out.push({
      名稱: e.name,
      擁有者: 擁有者,
      路徑: p,
      是連結: 是連結,
      連結目標: 連結目標,
      描述: 讀描述(path.join(p, 'SKILL.md'))
    });
  }
  return out.sort((a, b) => a.名稱.localeCompare(b.名稱));
}

/* ── 路由表：這個 skill 有沒有被指名 ── */
function 讀路由表(檔案清單 = 路徑.路由表) {
  const out = { 內容: '', 讀到: [], 讀不到: [] };
  for (const f of 檔案清單) {
    try { out.內容 += fs.readFileSync(f, 'utf8') + '\n'; out.讀到.push(f); }
    catch (e) { out.讀不到.push(f); }
  }
  return out;
}

module.exports = { 路徑, 掃逐字稿, 讀龍蝦用量, 盤點, 讀路由表 };
