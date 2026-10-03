const fs=require('fs'),path=require('path');const {spawnSync}=require('child_process');
const root=process.argv[2];const ME='A14530068_黃建升';
function setup(n){const base=path.join(root,n);fs.rmSync(base,{recursive:true,force:true});fs.mkdirSync(base,{recursive:true});
 const g=(c,a)=>spawnSync('git',a,{cwd:c,encoding:'utf8'});const up=path.join(base,'up.git'),fk=path.join(base,'fork.git'),wk=path.join(base,'work');
 g(base,['init','--bare','-b','main',up]);g(base,['init','--bare','-b','main',fk]);g(base,['clone',up,wk]);
 g(wk,['config','user.email','t@t']);g(wk,['config','user.name','t']);
 for(const d of ['20260919','20261003','20261017','20261121','20261219','20270116']){fs.mkdirSync(path.join(wk,d,'students',ME),{recursive:true});fs.writeFileSync(path.join(wk,d,'students',ME,'README.md'),'x');}
 g(wk,['add','-A']);g(wk,['commit','-m','init']);g(wk,['push','origin','HEAD:main']);g(wk,['remote','add','fork',fk]);g(wk,['checkout','-b','student/A14530068-t']);
 const cs=path.join(base,'cs');fs.cpSync(process.argv[3],cs,{recursive:true});const cfg=JSON.parse(fs.readFileSync(path.join(cs,'設定.json'),'utf8'));cfg.repo=wk.split(path.sep).join('/');fs.writeFileSync(path.join(cs,'設定.json'),JSON.stringify(cfg));
 return {wk,cs,dir:path.join(wk,'20260919','students',ME)};}
const chk=E=>spawnSync('node',[path.join(E.cs,'scripts','檢查.js')],{encoding:'utf8'});
let E=setup('f1');fs.writeFileSync(path.join(E.dir,'exact.bin'),Buffer.alloc(5*1024*1024));let c=chk(E);
console.log('恰好 5MB 檔案：',/超過/.test(c.stdout)?'被擋':'放行','(exit '+c.status+')');
E=setup('f2');fs.writeFileSync(path.join(E.dir,'plus1.bin'),Buffer.alloc(5*1024*1024+1));c=chk(E);
console.log('5MB+1 檔案：',/超過/.test(c.stdout)?'被擋':'放行','(exit '+c.status+')');
E=setup('f3');for(let i=0;i<30;i++)fs.writeFileSync(path.join(E.dir,'p'+i+'.bin'),Buffer.alloc(Math.floor(4.9*1024*1024)));c=chk(E);
console.log('30 個 4.9MB 檔案（約 147MB 合計）：',c.status===0?'全部放行，單檔上限不管總量':'被擋','(exit '+c.status+')');
E=setup('f4');for(const n of ['model.rvt.bak','model.rvt.zip','scene.skp.txt','house.rvt.7z'])fs.writeFileSync(path.join(E.dir,n),'z');c=chk(E);
console.log('把 Revit/SketchUp 原檔改副檔名（.rvt.bak／.rvt.zip／.skp.txt／.rvt.7z）：',c.status===0?'全部放行':'被擋','(exit '+c.status+')');
E=setup('f5');fs.writeFileSync(path.join(E.dir,'model.RVT'),'z');c=chk(E);console.log('model.RVT（大寫）：',c.status===0?'放行':'被擋（大小寫處理正確）');
