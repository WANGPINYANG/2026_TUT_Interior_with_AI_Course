// 用 CDP 操作「原始 HTML」（不改檔、不注入腳本到檔案），模擬鍵盤輸入與下拉選單，然後截圖
const { spawn } = require('child_process');
const fs = require('fs');
const [,, edge, fileUrl, outDir] = process.argv;
const PORT = 9333;
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const proc = spawn(edge, ['--headless=new', '--disable-gpu', '--remote-debugging-port=' + PORT,
    '--user-data-dir=' + process.env.TEMP + '\\cdp_profile_' + Date.now(), 'about:blank'], { stdio: 'ignore' });
  let targets;
  for (let i = 0; i < 50; i++) {
    try { targets = await (await fetch('http://127.0.0.1:' + PORT + '/json')).json(); if (targets.length) break; } catch (e) {}
    await sleep(200);
  }
  const page = targets.find(t => t.type === 'page');
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise(r => ws.onopen = r);
  let id = 0; const pending = {};
  ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pending[d.id]) { pending[d.id](d); delete pending[d.id]; } };
  const send = (method, params = {}) => new Promise(r => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  const ev = expr => send('Runtime.evaluate', { expression: expr, returnByValue: true });

  await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 640, height: 1450, deviceScaleFactor: 1, mobile: false });

  async function open() { await send('Page.navigate', { url: require('url').pathToFileURL(fileUrl).href }); await sleep(900); }
  // 像使用者一樣：點進欄位、全選、打字（Input.insertText 會觸發真實的 input 事件）
  async function type(idn, text) {
    await ev(`(function(){var e=document.getElementById('${idn}');e.focus();e.select();})()`);
    if (text === '') { for (const t of ['keyDown', 'keyUp']) await send('Input.dispatchKeyEvent', { type: t, key: 'Backspace', code: 'Backspace', windowsVirtualKeyCode: 8 }); }
    else await send('Input.insertText', { text });
    await sleep(120);
  }
  // 下拉選單：選好選項後觸發 change，等同使用者操作
  async function pick(idn, val) { await ev(`(function(){var s=document.getElementById('u_${idn}');s.value='${val}';s.dispatchEvent(new Event('change',{bubbles:true}));})()`); await sleep(150); }
  async function shot(name) {
    const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
    fs.writeFileSync(outDir + '/' + name, Buffer.from(r.result.data, 'base64'));
    const t = await ev(`document.getElementById('out').textContent+' | '+document.getElementById('steps').textContent.slice(0,200)`);
    console.log(name, '→', t.result.result.value);
  }

  await open(); await type('ping', '5'); await type('openArea', '50'); await shot('003-開口面積大於牆面積.png');
  await open(); await pick('wallH', '台尺'); await type('wallH', '9.24'); await shot('004-計算過程浮點雜訊.png');
  await open(); await type('ping', ''); await shot('005-空白當成0.png');
  await open(); await type('ping', '50'); await type('perim', '10'); await shot('006-不可能的幾何組合.png');
  await open(); for (const [k, v] of [['perim', '17.6'], ['wallH', '5.9'], ['openArea', '13'], ['rate', '3'], ['coats', '4'], ['loss', '25']]) await type(k, v); await shot('007-進位誤差40變41.png');
  await open(); await type('ping', '1e307'); await shot('008-畫面顯示Infinity.png');
  await open(); await type('ping', '1e307'); await pick('ping', '才'); await shot('009-切單位欄位被清空變0.png');

  ws.close(); proc.kill();
  process.exit(0);
})();
