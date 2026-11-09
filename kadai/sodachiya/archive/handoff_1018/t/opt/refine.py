exec(open('/tmp/claude-0/t/opt/search.py').read().split("best=[]")[0])
import json
from scipy.optimize import minimize
best=json.load(open('/tmp/claude-0/t/opt/best1.json'))
res=[]
for Rs in [100000,120000,140000,160000,180000,205000,250000,300000,400000,700000]:
  for gap in (700,900):
    starts=[b for b in best if b[1]==Rs][:2] or [best[0]]
    bb=None
    for b in starts:
        f=lambda v: score(Rs,v[0],v[1],v[2],gap)[0]
        o=minimize(f,[b[2],b[3],b[4]],method='Nelder-Mead',options=dict(initial_simplex=[[b[2],b[3],b[4]],[b[2]+2000,b[3],b[4]],[b[2],b[3]+2000,b[4]],[b[2],b[3],b[4]+3]],maxiter=400,xatol=50,fatol=0.5))
        if bb is None or o.fun<bb[0]: bb=(o.fun,o.x)
    s,r=score(Rs,*bb[1],gap)
    res.append((s,Rs,gap,list(bb[1]),{k:(round(v,2) if isinstance(v,float) else v) for k,v in r.items()}))
    print(round(s,1),Rs,gap,[round(v,1) for v in bb[1]],{k:(round(v,2) if isinstance(v,float) else v) for k,v in r.items()})
json.dump(res,open('/tmp/claude-0/t/opt/refined.json','w'))
