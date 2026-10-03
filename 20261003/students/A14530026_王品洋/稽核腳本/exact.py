import json,random,subprocess,sys,math
from fractions import Fraction as F
from decimal import Decimal,getcontext
getcontext().prec=60
ENG=sys.argv[1]; S=sys.argv[2]
rng=random.Random(11)
def dec(lo,hi,step): return F(rng.randint(int(lo/step),int(hi/step)))*step
cases=[]
def mk(formula,inp): cases.append(dict(f=formula,i={k:float(v) for k,v in inp.items()},ex={k:str(v) for k,v in inp.items()}))
N=int(sys.argv[3])
for _ in range(N):
    r=rng.random()
    # 油漆（周長>0 才能精確比對；周長=0 另測）
    mk('油漆',dict(ping=dec(1,60,F(1,10)),wallH=dec(2,4.5,F(1,10)),perim=dec(4,80,F(1,10)),openArea=dec(0,20,F(1,2)),rate=dec(6,14,F(1,2)),coats=F(rng.randint(1,4)),loss=F(rng.randint(0,30))))
    mk('窗簾',dict(窗寬=dec(60,600,F(1)),窗高=dec(60,300,F(1)),倍數=dec(1,3,F(1,10)),幅寬=F(rng.choice([110,140,150,280,300])),兩側收邊=dec(0,20,F(1)),上下摺邊=dec(0,40,F(1))))
    mk('磁磚',dict(長=dec(1,12,F(1,10)),寬=dec(1,12,F(1,10)),扣除=dec(0,5,F(1,10)),磚長=F(rng.choice([30,45,60,80,120])),磚寬=F(rng.choice([30,45,60,80,120])),填縫=F(rng.choice([0,1,2,3,5])),損耗=F(rng.randint(0,20)),每箱片數=F(rng.randint(1,12))))
json.dump(cases,open(S+"/ex_cases.json","w"))
subprocess.run(["node",S+"/ex_run.js",ENG,S+"/ex_cases.json",S+"/ex_out.json"],check=True)
out=json.load(open(S+"/ex_out.json",encoding="utf-8"))
def ceil(x): return -((-x.numerator)//x.denominator)
bad={'油漆':[], '窗簾':[], '磁磚':[]}; tot={'油漆':0,'窗簾':0,'磁磚':0}; nonfin={}
for c,o in zip(cases,out):
    f=c['f']; e={k:F(v) for k,v in c['ex'].items()}; tot[f]+=1
    if o.get('err'): nonfin.setdefault(f,[]).append((c['i'],o['err'])); continue
    v=o['v']
    if f=='油漆':
        # 周長>0：牆面積=周長*高-開口
        a=max(e['perim']*e['wallH']-e['openArea'],F(0)); L=a*e['coats']/e['rate']*(1+e['loss']/100)
        ex=ceil(L/F(3785,1000)); got=v['加侖數']
    elif f=='窗簾':
        w=e['窗寬']*e['倍數']+e['兩側收邊']; n=ceil(w/e['幅寬']); ex=ceil(n*(e['窗高']+e['上下摺邊'])/F(9144,100)); got=v['建議碼數']
    else:
        a=max(e['長']*e['寬']-e['扣除'],F(0)); s=((e['磚長']+e['填縫']/10)/100)*((e['磚寬']+e['填縫']/10)/100)
        p=ceil(a/s*(1+e['損耗']/100)); ex=ceil(F(p)/e['每箱片數']); got=v['箱數']
        if p!=v['片數']: bad[f].append((c['ex'],'片數',p,v['片數']))
    if ex!=got: bad[f].append((c['ex'],ex,got))
for f in bad:
    print(f,'案例',tot[f],'與精確答案不同',len(bad[f]),'| 被擋下',len(nonfin.get(f,[])))
    for b in bad[f][:2]: print('   ',json.dumps(b,ensure_ascii=False)[:300])
