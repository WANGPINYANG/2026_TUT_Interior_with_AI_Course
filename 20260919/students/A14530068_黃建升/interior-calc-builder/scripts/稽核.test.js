/* 獨立稽核：不改正式設定或產出。故障案例存在時 exit 1。
   node interior-calc-builder/scripts/稽核.test.js [JSON報告路徑]
   使用最小 DOM 測頁面邏輯，不代表真實瀏覽器或手機排版驗證。 */
'use strict';
const fs = require('fs');
const os = require('os');
const path = require('path');
const vm = require('vm');
const {spawnSync} = require('child_process');
const root = path.resolve(__dirname, '..', '..');
const base = JSON.parse(fs.readFileSync(path.join(__dirname, '../設定/油漆用量.json'), 'utf8'));
const source = fs.readFileSync(path.join(root, '油漆用量計算機.html'), 'utf8');
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'interior-calc-audit-'));
const rows = [];
let seq = 0;
function run(file, args = []) {
  const r = spawnSync(process.execPath, [path.join(__dirname, file), ...args], {encoding:'utf8', timeout:10000});
  if (r.error) throw r.error;
  return {status:r.status, output:(r.stdout + r.stderr).trim()};
}
function test(name, fn) {
  try { const r = fn(); rows.push({name, ...r}); }
  catch(e) { rows.push({name, pass:false, detail:'測試例外：' + e.message}); }
}
function generate(edit) {
  const c = JSON.parse(JSON.stringify(base));
  if (edit) edit(c);
  const dir = path.join(scratch, String(++seq));
  const out = path.join(dir, 'out');
  fs.mkdirSync(out, {recursive:true});
  const config = path.join(dir, 'config.json');
  fs.writeFileSync(config, JSON.stringify(c));
  const r = run('建立計算機.js', [config, out]);
  return {...r, config:c, dir, out, file:path.join(out, c.檔名)};
}
function check(html) {
  const file = path.join(scratch, 'check-' + (++seq) + '.html');
  fs.writeFileSync(file, html);
  return run('檢查.js', [file]);
}
function page(html = source) {
  const elements = {};
  for(const m of html.matchAll(/id="([^"]+)"/g)) {
    if(elements[m[1]]) continue;
    const e = {value:'', className:'', _text:'—', _html:'', events:{}};
    e.addEventListener = (type, cb) => { e.events[type] = cb; };
    Object.defineProperty(e, 'textContent', {get:()=>e._text, set:v=>{e._text=String(v);}});
    Object.defineProperty(e, 'innerHTML', {get:()=>e._html, set:v=>{e._html=String(v);e._text=String(v).replace(/<[^>]*>/g,'');}});
    elements[m[1]] = e;
  }
  const inputs = [];
  for(const m of html.matchAll(/<input\s+id="([^"]+)"[^>]*\svalue="([^"]*)"/g)) {
    elements[m[1]].value = m[2]; inputs.push(elements[m[1]]);
  }
  const context = {document:{getElementById:id=>elements[id] || null, querySelectorAll:()=>inputs}};
  vm.createContext(context);
  const code = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]).join('\n');
  vm.runInContext(code, context, {timeout:1000});
  return {elements, context, change(id, value) {
    elements[id].value = String(value);
    context.auditInput = elements[id];
    vm.runInContext('auditInput.events.input()', context, {timeout:1000});
    return elements.out.textContent + ' / ' + elements.out2.textContent;
  }};
}
test('原有四組公式測試', ()=>{const r=run('公式.test.js');return {pass:r.status===0,detail:r.output};});
test('原有十一項產出檢查', ()=>{const r=check(source);return {pass:r.status===0,detail:r.output};});
test('重新產生與正式 HTML 完全一致', ()=>{const r=generate();return {pass:r.status===0 && fs.readFileSync(r.file,'utf8')===source,detail:r.output};});
test('非預設輸入：實測周長 30 m', ()=>{
  const p=page(); const detail=p.change('perim',30);
  // (30×2.8−6)×2÷9×1.1 = 19.0666… L，進位為 6 加侖。
  return {pass:p.elements.out.textContent==='6 加侖' && p.elements.out2.textContent.includes('19.07'),detail};
});
for(const [label,id,value] of [['塗佈率為零','rate',0],['清空塗佈率','rate',''],['負損耗率','loss',-200],['负坪數','ping',-10],['小數道數','coats',1.5]]) {
  test('拒絕錯誤輸入：'+label, ()=>{
    const p=page();const detail=p.change(id,value);
    return {pass:!/(?:Infinity|NaN|^-?\d.*加侖)/.test(detail),detail:detail+'；驗算標示：'+p.elements.tRender.textContent};
  });
}
for(const [label,edit] of [
  ['危險 id',c=>{c.輸入[0].id='open';}],
  ['沒有驗算案例',c=>{c.驗算=[];}],
  ['缺數字預設值',c=>{delete c.輸入[0].預設;}],
  ['驗算缺欄位',c=>{delete c.驗算[0].輸入.ping;}],
  ['不存在的結果欄位',c=>{c.結果.欄位='不存在';}],
  ['重複輸入 id',c=>{c.輸入.push({...c.輸入[0]});}],
  ['漏掉公式必需的輸入欄',c=>{c.輸入=c.輸入.filter(f=>f.id!=='ping');}],
  ['空的預期答案',c=>{c.驗算.forEach(t=>{t.預期={};});}],
  ['結果單位缺失',c=>{delete c.結果.單位;}]
]) test('設定防呆：'+label, ()=>{
  const r=generate(edit);
  const checked=r.status===0?run('檢查.js',[r.file]):null;
  return {pass:r.status!==0,detail:r.status!==0?r.output:'產生器接受；後續檢查器 '+(checked.status===0?'也通過':'有擋下')};
});
test('輸出檔名不能越過指定資料夾', ()=>{
  const r=generate(c=>{c.檔名='../escaped.html';});
  return {pass:r.status!==0,detail:r.status===0?'在測試暫存區成功寫到 out 的上一層；未碰觸正式檔案':r.output};
});
test('設定文字應以純文字顯示', ()=>{
  const r=generate(c=>{c.標題='<b>audit-marker</b>';});
  const html=fs.readFileSync(r.file,'utf8');
  return {pass:html.includes('&lt;b&gt;audit-marker&lt;/b&gt;'),detail:html.includes('<h1><b>audit-marker</b></h1>')?'標題中的 HTML 被直接插入標記':'已轉義或拒絕'};
});
test('JSON 內容不可提早關閉 script', ()=>{
  const r=generate(c=>{c.驗算[0].標題='</script><b>audit-marker</b>';});
  const html=fs.readFileSync(r.file,'utf8');
  return {pass:!html.includes('</script><b>audit-marker</b>'),detail:'只檢查產出文字，未開啟測試 HTML 或執行插入內容'};
});
test('檢查器能抓 Infinity 結果', ()=>{
  const r=generate(c=>{c.參數.find(f=>f.id==='rate').預設=0;});
  const checked=run('檢查.js',[r.file]);
  return {pass:checked.status!==0,detail:checked.output};
});
test('檢查器能抓移除 input 事件的頁面', ()=>{
  // 2026-10-03 改了錨點字串，沒有改這條測試在驗什麼。
  // 原錨點是 'el.addEventListener("input", render);'，可自選單位改版後綁定方式改寫，
  // 那行字不再存在。這裡只更新「怎麼找到綁定那一行」，斷言仍是「拔掉事件後檢查器要抓到」。
  const modified=source.replace('欄.addEventListener("input", function () { 同步基準(k); render(); });','/* 故意拔掉事件以測檢查器 */');
  if(modified===source) throw Error('找不到測試修改位置');
  const r=check(modified); return {pass:r.status!==0,detail:r.output};
});
test('檢查器能抓 CSS 外部資源', ()=>{
  const r=check(source.replace('<style>','<style>\n@import url("https://example.invalid/audit.css");'));
  return {pass:r.status!==0,detail:r.output};
});
const report={date:new Date().toISOString(), limitations:['最小 DOM 不具備真實瀏覽器驗證與排版能力','瀏覽器工具政策阻擋本機 file URL；未繞過政策'],scratch,total:rows.length,passed:rows.filter(r=>r.pass).length,failed:rows.filter(r=>!r.pass).length,rows};
if(process.argv[2]) fs.writeFileSync(process.argv[2],JSON.stringify(report,null,2));
for(const r of rows) console.log((r.pass?'PASS':'FAIL')+' '+r.name+'\n  '+r.detail.replace(/\n/g,'\n  '));
console.log('\n總計 '+report.total+'，通過 '+report.passed+'，未通過 '+report.failed);
console.log('暫存測試產物：'+scratch);
process.exitCode=report.failed?1:0;
