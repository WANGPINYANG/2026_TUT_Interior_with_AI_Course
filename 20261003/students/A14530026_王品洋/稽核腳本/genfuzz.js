// 對「計算機產生器」做設定檔暴力測試。設定檔與輸出一律在暫存資料夾，只「執行」對方的產生器與檢查器。
const fs = require('fs');
const { spawnSync } = require('child_process');
const [,, builderDir, outRoot, nArg, seedArg] = process.argv;
const N = +nArg || 300; let seed = +seedArg || 1;
const R = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
const pick = a => a[Math.floor(R() * a.length)];
const base = JSON.parse(fs.readFileSync(builderDir + '/設定/油漆用量.json', 'utf8'));
const BAD = [null, '', 'abc', 0, -1, 1e308, -1e308, 1e-320, 0.5, 2.5, 1e5, [], {}, true, false, '{公升}', '{不存在}', '<b>x</b>', '😀', '\n', 'a'.repeat(5000), 'NaN', 'Infinity', -0, 1e21, 99999999999];

function leaves(node, path) {
  const out = [];
  if (node && typeof node === 'object') for (const k of Object.keys(node)) { out.push([node, k, path.concat(k)]); out.push(...leaves(node[k], path.concat(k))); }
  return out;
}
const outdir = outRoot; fs.mkdirSync(outdir, { recursive: true });
const classes = {}; const add = (c, ex) => { (classes[c] = classes[c] || { n: 0, ex }).n++; };
let accepted = 0, rejected = 0, crashed = 0;
for (let i = 0; i < N; i++) {
  const cfg = JSON.parse(JSON.stringify(base));
  const ls = leaves(cfg, []).filter(l => l[2][0] !== '檔名');          // 檔名另有專門測試，這裡保持合法
  const muts = [];
  for (let k = 0; k < 1 + Math.floor(R() * 2); k++) {
    const [node, key, path] = pick(ls);
    if (!(key in node)) continue;
    if (R() < 0.3) { muts.push('刪除 ' + path.join('.')); if (Array.isArray(node)) node.splice(key, 1); else delete node[key]; }
    else { const v = pick(BAD); muts.push(path.join('.') + ' = ' + JSON.stringify(v).slice(0, 40)); node[key] = v; }
  }
  cfg['檔名'] = 'g' + i + '.html';
  const cfgPath = outdir + '/cfg_' + i + '.json'; fs.writeFileSync(cfgPath, JSON.stringify(cfg), 'utf8');
  const gdir = outdir + '/out_' + i; fs.mkdirSync(gdir, { recursive: true });
  const r = spawnSync('node', [builderDir + '/scripts/建立計算機.js', cfgPath, gdir], { encoding: 'utf8', timeout: 20000 });
  const desc = muts.join('；');
  if (r.status !== 0) {
    const graceful = /產生失敗/.test(r.stderr) && !/\n\s+at /.test(r.stderr);
    if (graceful) rejected++; else { crashed++; add('產生器崩潰（沒有「產生失敗」訊息，直接噴例外）', desc + ' ⇒ ' + r.stderr.split('\n').filter(l => /Error/.test(l))[0]); }
    continue;
  }
  accepted++;
  const html = gdir + '/g' + i + '.html';
  if (!fs.existsSync(html)) { add('產生器說成功卻沒有輸出檔', desc); continue; }
  const c = spawnSync('node', [builderDir + '/scripts/檢查.js', html], { encoding: 'utf8', timeout: 20000 });
  if (c.status !== 0) add('產生器接受設定，但產出的頁面通不過它自己的檢查器', desc + ' ⇒ ' + (c.stdout.split('\n').filter(l => /失敗/.test(l))[0] || '').trim());
  // 接受的設定，頁面預設畫面該是可用的（不是「—」）
  const page = fs.readFileSync(html, 'utf8');
  const d = (cfg.輸入 || []).concat(cfg.參數 || []);
  if (d.some(f => f && typeof f.預設 === 'number' && f.預設 < 0)) add('接受了負的預設值', desc);
  if (/NaN|undefined|\[object Object\]/.test(page.replace(/<script>[\s\S]*?<\/script>/g, '').replace(/<style>[\s\S]*?<\/style>/g, ''))) add('產出的 HTML 含 NaN／undefined／[object Object]（不在腳本內）', desc);
  if (!/<title>[^<]/.test(page)) add('產出頁面沒有標題', desc);
  if (/&lt;b&gt;x/.test(page) === false && /<b>x<\/b>/.test(page.replace(/<script>[\s\S]*?<\/script>/g, ''))) add('設定文字沒逸出（HTML 注入）', desc);
}
console.log('設定檔', N, '個｜被擋下（有說明）', rejected, '｜被接受', accepted, '｜崩潰', crashed);
for (const [c, v] of Object.entries(classes)) console.log('■', c, '×' + v.n, '\n    例：', v.ex.slice(0, 280));
if (!Object.keys(classes).length) console.log('沒有觸發任何不變量');
