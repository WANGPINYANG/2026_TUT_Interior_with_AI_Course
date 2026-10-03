const E=require(process.argv[2]+'/interior-calc-builder/scripts/公式.js');
let seed=5;const R=()=>{seed=(seed*1664525+1013904223)%4294967296;return seed/4294967296};const rr=(a,b)=>a+(b-a)*R();
const g=o=>E.計算('油漆',o).值.加侖數;
let mono={},mut=0,idem=0,N=200000,viol=[];
for(let i=0;i<N;i++){
  const b={ping:rr(1,80),wallH:rr(2,5),perim:R()<0.5?0:rr(4,90),openArea:rr(0,25),rate:rr(5,15),coats:1+Math.floor(R()*4),loss:rr(0,40)};
  const base=g(b);
  // 輸入被改動?
  const c=JSON.parse(JSON.stringify(b));E.計算('油漆',c);if(JSON.stringify(c)!==JSON.stringify(b))mut++;
  if(E.計算('油漆',b).值.加侖數!==base)idem++;
  const up={ping:1.2,wallH:1.2,coats:0,loss:0},test=(k,mult,dir)=>{const o=Object.assign({},b);if(k==='coats')o.coats=b.coats+1;else o[k]=b[k]*mult;const v=g(o);
    const bad=dir>0?v<base:v>base;if(bad){mono[k]=(mono[k]||0)+1;if(viol.length<4)viol.push([k,b,base,v])}};
  test('wallH',1.2,1);test('coats',1,1);test('loss',1.2,1);test('rate',1.2,-1);test('openArea',1.2,-1);
  if(b.perim>0)test('perim',1.2,1);else test('ping',1.2,1);
}
console.log('隨機',N,'組；輸入被函式改動',mut,'；同輸入兩次結果不同',idem);
console.log('單調性違反（該增加卻減少／該減少卻增加）:',JSON.stringify(mono));
viol.forEach(v=>console.log(JSON.stringify(v)));
