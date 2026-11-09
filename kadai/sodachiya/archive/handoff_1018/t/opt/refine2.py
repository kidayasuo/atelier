exec(open('/tmp/claude-0/t/opt/base.py').read())
from scipy.optimize import minimize
def protr(poly):
    return max([setb.exterior.distance(SPt(p)) for p in poly.exterior.coords if not setb.contains(SPt(p))] or [0.0])
def score(Rs,x,y,ang,gap,ret=False):
    r=evaluate(Rs,(x,y),ang,gap,detail=True)
    bm,bw,main,west=r['geo']
    pm,pw=protr(main),protr(west)
    s=r['out_site']*1000+max(0,1000-r['ne'])*1.0+r['park']*200+(0 if r['parking'] is not None else 300)+max(pm,pw)/10.0
    if ret: return s,r,pm,pw
    return s
init={100000:(6517,-65459,82.1),120000:(6403,-65971,83.3),140000:(6333,-66309,84.2),160000:(6264,-66521,84.8),180000:(6217,-66615,85.3),205000:(6143,-66881,85.6),250000:(6100,-67000,86.0),300000:(6007,-67127,86.6)}
out=[]
for Rs,v0 in init.items():
  for gap in (700,):
    o=minimize(lambda v: score(Rs,v[0],v[1],v[2],gap),v0,method='Nelder-Mead',options=dict(initial_simplex=[v0,[v0[0]+1500,v0[1],v0[2]],[v0[0],v0[1]+1500,v0[2]],[v0[0],v0[1],v0[2]+2]],maxiter=500,xatol=20,fatol=0.2))
    s,r,pm,pw=score(Rs,*o.x,gap,ret=True)
    print(Rs,gap,[round(t,1) for t in o.x],'score %.1f'%s,'protrude main %.0f west %.0f mm'%(pm,pw),'ne %.0f'%r['ne'],'parking',r['parking'],'site %.2f'%r['out_site'],'park %.2f'%r['park'])
    out.append((Rs,gap,list(map(float,o.x)),s,pm,pw))
import json; json.dump(out,open('/tmp/claude-0/t/opt/refined2.json','w'))
