// 對「原始 HTML」做隨機介面操作（只輸入文字、選下拉選單），檢查不變量。不修改任何檔案。
const { spawn } = require('child_process');
const fs = require('fs');
const [,, edge, filePath, outDir, stepsArg, seedArg, widthArg] = process.argv;
const STEPS = +stepsArg || 1500; let seed = +seedArg || 1; const WIDTH = +widthArg || 640;
const PORT = 9334;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const R = () => { seed = (seed * 1664525 + 1013904223) % 4294967296; return seed / 4294967296; };
const pick = a => a[Math.floor(R() * a.length)];

(async () => {
  const proc = spawn(edge, ['--headless=new', '--disable-gpu', '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + process.env.TEMP + '\\cdp_fuzz_' + Date.now(), 'about:blank'], { stdio: 'ignore' });
  let targets;
  for (let i = 0; i < 50; i++) { try { targets = await (await fetch('http://127.0.0.1:' + PORT + '/json')).json(); if (targets.length) break; } catch (e) {} await sleep(200); }
  const ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = {}; const exceptions = [];
  ws.onmessage = m => { const d = JSON.parse(m.data);
    if (d.id && pending[d.id]) { pending[d.id](d); delete pending[d.id]; }
    if (d.method === 'Runtime.exceptionThrown') exceptions.push(d.params.exceptionDetails.exception ? d.params.exceptionDetails.exception.description : d.params.exceptionDetails.text); };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = async expr => (await send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.result.value;
  await send('Page.enable'); await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: WIDTH, height: 1450, deviceScaleFactor: 1, mobile: WIDTH < 500 });
  await send('Page.navigate', { url: require('url').pathToFileURL(filePath).href }); await sleep(900);

  const fields = { ping: ['坪', 'm2', '才'], wallH: ['m', 'cm', '台尺'], perim: ['m', 'cm', '台尺', '丈'], openArea: ['m2', 'cm2', '才', '坪'], rate: null, coats: null, loss: null };
  const keys = Object.keys(fields);
  const texts = ['', '0', '-1', '-0', '1e308', '1e307', '1e-320', '1e-7', '0.1', '0.5', '1e5', '999999999999999999999', '.', '1e', '--1', '5e-1', '2.5', '10', '2.8', '100', '9', '12345678901234567890', '0.0000001', '1e300', '+5'];
  const found = {};
  const note = (cls, detail, shotName) => { if (!found[cls]) { found[cls] = { n: 0, detail, shot: shotName }; } found[cls].n++; };
  const history = [];
  for (let s = 0; s < STEPS; s++) {
    const k = pick(keys); let desc;
    if (fields[k] && R() < 0.3) { const u = pick(fields[k]); await ev(`(function(){var e=document.getElementById('u_${k}');e.value='${u}';e.dispatchEvent(new Event('change',{bubbles:true}));})()`); desc = `${k} 單位→${u}`; }
    else { const t = pick(texts); await ev(`(function(){var e=document.getElementById('${k}');e.focus();e.select();})()`);
      if (t === '') for (const ty of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', { type: ty, key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 });
      else await send('Input.insertText', { text: t });
      desc = `${k} 輸入 "${t}"`; }
    history.push(desc); if (history.length > 6) history.shift();
    const st = await ev(`(function(){var o={};
      o.steps=document.getElementById('steps').textContent;o.out=document.getElementById('out').textContent;o.out2=document.getElementById('out2').textContent;
      o.badFields=Array.from(document.querySelectorAll('input.bad')).map(e=>e.id);
      o.errTexts=Array.from(document.querySelectorAll('.err.on')).map(e=>e.textContent);
      o.vals={};['ping','wallH','perim','openArea','rate','coats','loss'].forEach(function(i){var e=document.getElementById(i);o.vals[i]=e.value+'|valid='+e.validity.valid+'|bad='+e.validity.badInput});
      o.sw=document.documentElement.scrollWidth;o.iw=window.innerWidth;return o})()`);
    const screen = st.steps + st.out + st.out2;
    const ctx = history.join(' ← ');
    const snap = async cls => { const f = cls.replace(/[^\w一-鿿]/g, '_') + '.png'; if (!found[cls]) { const r = await send('Page.captureScreenshot', { format: 'png' }); fs.writeFileSync(outDir + '/' + f, Buffer.from(r.result.data, 'base64')); } return f; };
    if (/Infinity|NaN|undefined/.test(screen)) note('畫面出現 Infinity/NaN/undefined', ctx + ' ⇒ out=' + st.out, await snap('畫面出現 Infinity/NaN/undefined'));
    if (/e\+|e-/.test(st.out) && !st.badFields.length) note('結果以科學記號顯示當作正常結果', ctx + ' ⇒ ' + st.out, await snap('結果以科學記號顯示當作正常結果'));
    if (st.out !== '—' && st.badFields.length) note('有欄位標紅卻仍顯示結果（陳舊/不一致）', ctx + ' ⇒ ' + st.out, await snap('有欄位標紅卻仍顯示結果'));
    if (st.out === '—' && !st.badFields.length && !/故障/.test(st.out2)) note('結果為「—」卻沒有任何紅字說明', ctx + ' ⇒ out2=' + st.out2, await snap('結果為破折號卻沒有紅字'));
    if (st.sw > st.iw + 1) note('版面橫向溢出（出現水平捲軸）', ctx + ' ⇒ scrollWidth=' + st.sw + ' > ' + st.iw, await snap('版面橫向溢出'));
    for (const i of keys) { const v = st.vals[i].split('|'); if (v[0] === '' && v[2] === 'bad=false' && /^0 /.test(st.out) === false && false) {} }
    // 欄位是空的，但畫面卻照算（空白被當成 0）
    const blank = keys.filter(i => st.vals[i].startsWith('|') && !st.badFields.includes(i));
    if (blank.length && st.out !== '—') note('欄位空白卻照算出結果（空白被當成 0）', ctx + ' ⇒ 空白欄位=' + blank.join(',') + '，結果=' + st.out, await snap('欄位空白卻照算'));
    if (exceptions.length) note('頁面丟出未捕捉的例外', ctx + ' ⇒ ' + exceptions[exceptions.length - 1], await snap('頁面例外')); exceptions.length = 0;
  }
  console.log('步數', STEPS, '種子', seedArg, '寬度', WIDTH);
  for (const [cls, v] of Object.entries(found)) console.log('■', cls, '×' + v.n, '\n    例：', v.detail.slice(0, 260));
  if (!Object.keys(found).length) console.log('沒有觸發任何不變量');
  ws.close(); proc.kill(); process.exit(0);
})();
