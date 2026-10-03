// 攻擊 skill-usage-audit：全部使用假資料；只在記憶體裡改 蒐集.路徑，不改對方檔案
const fs = require('fs'), path = require('path'), os = require('os');
const [,, srcDir, root] = process.argv;
const 蒐集 = require(path.join(srcDir, 'scripts', '蒐集.js'));
const W = (p, c) => { fs.mkdirSync(path.dirname(p), { recursive: true }); fs.writeFileSync(p, c); };
const results = [];
const rec = (id, title, verdict, ev) => { results.push({ id, title, verdict, ev }); console.log((verdict === 'BUG' ? '✘ ' : verdict === 'OK' ? '✔ ' : '· ') + id + ' ' + title + '\n    ' + String(ev).split('\n').slice(0, 5).join('\n    ')); };
const tu = (skill, id, sid = 's1', ts = '2026-10-01T10:00:00.000Z') => JSON.stringify({ type: 'assistant', sessionId: sid, timestamp: ts, message: { role: 'assistant', content: [{ type: 'tool_use', id, name: 'Skill', input: { skill, args: '' } }] } });

(async () => {
  fs.rmSync(root, { recursive: true, force: true });
  // ---- A：同一筆呼叫出現在兩個逐字稿檔（接續對話會把歷史再寫一份）→ 次數被重複計算
  { const t = path.join(root, 'a'); W(path.join(t, 'p1', 'one.jsonl'), tu('interior-ledger', 'toolu_X') + '\n'); W(path.join(t, 'p1', 'two.jsonl'), tu('interior-ledger', 'toolu_X') + '\n');
    const r = await 蒐集.掃逐字稿(t); const n = r.統計['interior-ledger'] && r.統計['interior-ledger'].次數;
    rec('A', '同一個 tool_use（相同 id）出現在兩個檔案', n === 2 ? 'BUG' : 'OK', '實際只呼叫 1 次，統計為 ' + n + ' 次（沒有用 tool_use id 去重）'); }
  // ---- J：skill 名稱是 Object 原型上的屬性（constructor／toString／__proto__）
  for (const nm of ['constructor', 'toString', '__proto__']) {
    const t = path.join(root, 'j_' + nm); W(path.join(t, 'p', 'x.jsonl'), tu(nm, 'toolu_J') + '\n');
    let msg = '正常'; try { const r = await 蒐集.掃逐字稿(t); msg = '統計=' + JSON.stringify(Object.keys(r.統計)); } catch (e) { msg = '崩潰：' + e.message; }
    rec('J-' + nm, 'Skill 名稱為「' + nm + '」', /崩潰/.test(msg) ? 'BUG' : 'OK', msg); }
  // ---- F：壞掉的逐字稿檔（二進位、空檔、超長單行）
  { const t = path.join(root, 'f'); fs.mkdirSync(path.join(t, 'p'), { recursive: true });
    fs.writeFileSync(path.join(t, 'p', 'bin.jsonl'), Buffer.from([0xff, 0xfe, 0x00, 0x01, 0x80, 0x81, 0x0a, 0x7b, 0x22]));
    fs.writeFileSync(path.join(t, 'p', 'empty.jsonl'), ''); fs.writeFileSync(path.join(t, 'p', 'long.jsonl'), '"name":"Skill"' + 'x'.repeat(50 * 1024 * 1024) + '\n');
    let m = '正常'; const t0 = Date.now(); try { const r = await 蒐集.掃逐字稿(t); m = '檔案數=' + r.檔案數 + '，壞行=' + r.壞行 + '，耗時 ' + (Date.now() - t0) + 'ms'; } catch (e) { m = '崩潰：' + e.message; }
    rec('F', '二進位／空檔／50MB 單行', /崩潰/.test(m) ? 'BUG' : 'OK', m); }
  // ---- 以下用 稽核.js 的完整流程：先把路徑指到假資料
  const home = path.join(root, 'home'); fs.mkdirSync(home, { recursive: true });
  const skills = path.join(home, 'skills'), lob = path.join(home, 'lobster'), tr = path.join(home, 'transcripts'), route = path.join(home, 'CLAUDE.md');
  const mk = (n, desc) => W(path.join(skills, n, 'SKILL.md'), '---\nname: ' + n + '\n' + desc + '\n---\n# x');
  mk('interior-ledger', 'description: 記帳');
  mk('ledger', 'description: 另一個很少用的 skill');
  mk('handover-booklet', 'description: >-\n  整理業主交屋手冊與保固通知，一年才用一次');
  mk('plain-unused', 'description: 完全沒用過的東西');
  mk('quoted-seasonal', 'description: "交屋時才會用到"');
  fs.mkdirSync(path.join(skills, '_archive'), { recursive: true }); W(path.join(skills, '_archive', 'old.txt'), 'x');      // 不是 skill 的資料夾
  fs.mkdirSync(path.join(skills, 'node_modules'), { recursive: true });
  // 壞掉的符號連結 / junction
  let broken = false; try { const tgt = path.join(home, 'gone-target'); fs.mkdirSync(tgt); fs.symlinkSync(tgt, path.join(skills, 'broken-link'), 'junction'); fs.rmSync(tgt, { recursive: true }); broken = true; } catch (e) {}
  fs.mkdirSync(lob, { recursive: true });
  W(path.join(tr, 'p', 's.jsonl'), tu('interior-ledger', 'u1') + '\n');
  W(route, '記帳 → interior-ledger skill\n');
  Object.assign(蒐集.路徑, { 逐字稿根: tr, claude技能: skills, 龍蝦技能: lob, 龍蝦DB: path.join(home, 'none.sqlite'), 路由表: [route] });
  const origLog = console.log; let buf = ''; console.log = (...a) => { buf += a.join(' ') + '\n'; };
  process.argv.push('--json'); require(path.join(srcDir, 'scripts', '稽核.js')); await new Promise(r => setTimeout(r, 600)); console.log = origLog;
  let J; try { J = JSON.parse(buf); } catch (e) { rec('主程式', '稽核.js --json 輸出可解析', 'BUG', buf.slice(0, 300)); return fin(); }
  const by = n => J.skills.find(s => s.名稱 === n);
  rec('B', '子字串誤判：skill「ledger」被當成「路由表有指名」', by('ledger') && by('ledger').被路由表指名 ? 'BUG' : 'OK',
    '路由表只寫了 interior-ledger；「ledger」的類別＝' + (by('ledger') && by('ledger').類別) + '（用 indexOf 子字串比對）');
  rec('C', '多行 description（YAML 的 >- ）讀成「>-」，季節性判斷失效', (by('handover-booklet') && by('handover-booklet').類別 === '零次且無人指名') ? 'BUG' : 'OK',
    'handover-booklet 實際是交屋／保固這種季節性 skill，被歸為：' + (by('handover-booklet') && by('handover-booklet').類別) + '；對照：單行引號寫法 quoted-seasonal＝' + (by('quoted-seasonal') && by('quoted-seasonal').類別));
  const names = J.skills.map(s => s.名稱);
  rec('E', '不是 skill 的資料夾（_archive、node_modules，沒有 SKILL.md）被列入並建議可刪', (names.includes('_archive') || names.includes('node_modules')) ? 'BUG' : 'OK',
    '_archive＝' + (by('_archive') && by('_archive').類別) + '；node_modules＝' + (by('node_modules') && by('node_modules').類別));
  rec('D', '壞掉的符號連結 skill 從清單中靜默消失（工具宣稱「任何來源掛掉都要回報」）', (broken && !names.includes('broken-link')) ? 'BUG' : (broken ? 'OK' : 'N/A'),
    '清單中有 broken-link：' + names.includes('broken-link') + '；報告的來源狀態：' + JSON.stringify(J.來源狀態).slice(0, 160));
  fin();
  function fin() { fs.writeFileSync(path.join(root, 'sua_results.json'), JSON.stringify(results, null, 1), 'utf8'); console.log('\n總結：BUG ' + results.filter(r => r.verdict === 'BUG').length + ' ｜ OK ' + results.filter(r => r.verdict === 'OK').length); process.exit(0); }
})();
