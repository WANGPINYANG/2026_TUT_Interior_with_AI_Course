const E=require(process.argv[2]+'/interior-calc-builder/scripts/公式.js');
const cs=require(process.argv[3]);const fs=require('fs');
const out=cs.map(c=>{const r=E.計算(c.f,c.i);const er=(r.錯誤||[]).filter(e=>e.等級!=='提醒');return er.length?{err:er.map(e=>e.訊息).join('|')}:{v:r.值};});
fs.writeFileSync(process.argv[4],JSON.stringify(out));
