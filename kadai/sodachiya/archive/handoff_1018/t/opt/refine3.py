import sys, json
WSP,WD,WST=int(sys.argv[1]),float(sys.argv[2]),int(sys.argv[3])
exec(open('/tmp/claude-0/t/opt/base2.py').read())
exec(open('/tmp/claude-0/t/opt/refine2.py').read().split("exec(open('/tmp/claude-0/t/opt/base.py').read())")[1].split("init=")[0])
edges={'北(大学)':((-25830,-20540),(0,0)),'川':((34860,-43830),(-14440,-83040)),'西道路':((-21910,-73650),(-25830,-20540))}
out=[]
for Rs in (120000,160000,205000,250000):
    v0=(6200,-66600,85.0); gap=700
    bestv=None
    for v0 in [(6200,-66600,85.0),(6400,-65900,83.5),(6000,-67100,86.5)]:
        o=minimize(lambda v: score(Rs,v[0],v[1],v[2],gap),v0,method='Nelder-Mead',options=dict(initial_simplex=[v0,[v0[0]+1500,v0[1],v0[2]],[v0[0],v0[1]+1500,v0[2]],[v0[0],v0[1],v0[2]+2]],maxiter=500,xatol=20,fatol=0.2))
        if bestv is None or o.fun<bestv.fun: bestv=o
    s,r,pm,pw=score(Rs,*bestv.x,gap,ret=True)
    bm,bw,main,west=r['geo']
    d={nm:{en:round(min(SL([a,b]).distance(SPt(p)) for p in poly.exterior.coords)/1000,2) for en,(a,b) in edges.items()} for nm,poly in (('本館',main),('西館',west))}
    print(Rs//1000,[round(t,1) for t in bestv.x],'protrude %.0f/%.0f'%(pm,pw),'ne %.2f'%(r['ne']/1000),'P',r['parking'],d)
    out.append((Rs,gap,list(map(float,bestv.x)),s,pm,pw))
json.dump(out,open('/tmp/claude-0/t/opt/r3_%d_%d_%d.json'%(WSP,WD,WST),'w'))
