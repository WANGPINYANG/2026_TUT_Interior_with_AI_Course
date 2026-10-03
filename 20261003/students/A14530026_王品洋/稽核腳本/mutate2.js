// 變異測試：把「被稽核的 HTML」複製到暫存，一次弄壞一個地方，
// 看他的 檢查.js 抓不抓得到。只讀取被稽核檔案；變異只發生在暫存複本。
const fs = require('fs');
const { spawnSync } = require('child_process');
const [,, htmlPath, wsDir, tmpDir, reportPath] = process.argv;
const orig = fs.readFileSync(htmlPath, 'utf8');

function engineOf(src) {
  const mod = { exports: {} };
  new Function('module', src)(mod);
  return mod.exports;
}
const O = engineOf(orig);

// 只對「油漆公式 + 驗證 + 換算 + 單位表」這段原始碼做變異
const start = orig.indexOf('var 換算 = {');
const end = orig.indexOf('窗簾: {', orig.indexOf('var 公式 = {'));
let seed = 9; const R = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
const rr = (a, b) => a + (b - a) * R();
const inputs = [];
for (let i = 0; i < 400; i++) inputs.push({ ping: rr(0.5, 80), wallH: rr(1.8, 5), perim: R() < 0.5 ? 0 : rr(2, 90), openArea: rr(0, 30), rate: rr(2, 20), coats: 1 + Math.floor(R() * 4), loss: rr(0, 40) });
// 加幾個壞值，讓驗證層的變異也看得出差異
[{ rate: 0 }, { loss: -5 }, { ping: -1 }, { coats: 2.5 }, { wallH: 0 }, { openArea: -1 }, { perim: -3 }, { coats: 0 }, { ping: 1e307 }, { loss: 500 }, { rate: 0.5 }].forEach(o => inputs.push(Object.assign({ ping: 10, wallH: 2.8, perim: 0, openArea: 6, rate: 9, coats: 2, loss: 10 }, o)));
const sig = (E, i) => { try { const r = E.計算('油漆', i); return JSON.stringify([r.值, (r.錯誤 || []).map(e => e.等級 + e.欄位)]); } catch (e) { return 'EXC'; } };
const base = inputs.map(i => sig(O, i));
const unitSig = E => JSON.stringify([E.換算到(10, '坪', '才'), E.換算到(280, 'cm', '台尺'), E.換算到(6, '才', 'm2'), E.換算到(1, '丈', 'm')]);
const baseUnit = unitSig(O);

// 產生變異
const seg = orig.slice(start, end);
const comments = []; { const cr = new RegExp('/\\*[\\s\\S]*?\\*/|//[^\\n]*', 'g'); let c; while ((c = cr.exec(seg))) comments.push([c.index, c.index + c[0].length]); }
const inComment = i => comments.some(([a, b]) => i >= a && i < b);
const strings = []; { const sr = new RegExp("'(?:[^'\\\\\\n]|\\\\.)*'", 'g'); let c; while ((c = sr.exec(seg))) strings.push([c.index, c.index + c[0].length]); }
const inString = i => strings.some(([a, b]) => i >= a && i < b);
const muts = [];
const rules = [
  [/\*/g, '/', '乘改除'], [/ \/ /g, ' * ', '除改乘'], [/ \+ /g, ' - ', '加改減'], [/ - /g, ' + ', '減改加'],
  [/ < /g, ' <= ', '< 改 <='], [/ > /g, ' >= ', '> 改 >='], [/ <= /g, ' < ', '<= 改 <'], [/ >= /g, ' > ', '>= 改 >'],
  [/Math\.ceil/g, 'Math.floor', 'ceil 改 floor'], [/Math\.sqrt/g, 'Math.abs', 'sqrt 改 abs'],
  [/!isFinite/g, 'isFinite', '!isFinite 反轉'], [/\|\|/g, '&&', '|| 改 &&'], [/&&/g, '||', '&& 改 ||'],
  [/\d+\.\d+|\b\d+\b/g, null, '常數 +1']
];
for (const [re, rep, name] of rules) {
  let m; const r = new RegExp(re.source, 'g'); const hits = [];
  while ((m = r.exec(seg))) hits.push([m.index, m[0]]);
  // 每條規則最多抽 10 個位置
  const pick = hits.filter(h => !inComment(h[0]) && !inString(h[0])).sort(() => R() - 0.5).slice(0, 14);
  for (const [idx, tok] of pick) {
    if (inComment(idx) || inString(idx)) continue;
    const lineStart = seg.lastIndexOf('\n', idx) + 1; const line = seg.slice(lineStart, seg.indexOf('\n', idx));
    if (/^\s*(\/\*|\*|\/\/)/.test(line)) continue;
    const newTok = rep === null ? String(Number(tok) + 1) : rep;
    const text = seg.slice(0, idx) + newTok + seg.slice(idx + tok.length);
    muts.push({ name, tok, line: line.trim().slice(0, 70), html: orig.slice(0, start) + text + orig.slice(end) });
  }
}

fs.mkdirSync(tmpDir, { recursive: true });
let n = 0, equivalent = 0, errored = 0; const caught = [], survived = [];
for (const m of muts) {
  let E; try { E = engineOf(m.html); } catch (e) { errored++; continue; }   // 語法壞掉＝一定被抓到，不計入
  const diff = inputs.some((i, k) => sig(E, i) !== base[k]);
  let udiff = false; try { udiff = unitSig(E) !== baseUnit; } catch (e) { udiff = true; }
  if (!diff && !udiff) { equivalent++; continue; }     // 行為完全相同＝等價變異，不算
  n++;
  fs.writeFileSync(wsDir + '/interior-calc-builder/scripts/公式.js', m.html);
  const r = spawnSync('node', ['scripts/全部測試.js'], { encoding: 'utf8', cwd: wsDir + '/interior-calc-builder' });
  fs.writeFileSync(wsDir + '/interior-calc-builder/scripts/公式.js', orig);
  (r.status !== 0 ? caught : survived).push(m);
}
console.log('變異總數', muts.length, '｜語法壞掉', errored, '｜等價（行為沒變）', equivalent, '｜有效變異', n);
console.log('檢查器抓到', caught.length, '｜漏掉（存活）', survived.length, '｜抓到率', (100 * caught.length / n).toFixed(0) + '%');
const byName = {}; survived.forEach(m => { byName[m.name] = (byName[m.name] || 0) + 1; });
console.log('存活變異類型：', JSON.stringify(byName));
fs.writeFileSync(reportPath, JSON.stringify({ n, caught: caught.length, survived: survived.map(m => ({ name: m.name, tok: m.tok, line: m.line })) }, null, 1), 'utf8');
survived.slice(0, 12).forEach(m => console.log(' 漏：[' + m.name + '] ' + m.line));
