import sys, json, math
WSP,WD,WST=int(sys.argv[1]),float(sys.argv[2]),int(sys.argv[3])
exec(open('/tmp/claude-0/t/opt/base2.py').read())
exec(open('/tmp/claude-0/t/opt/refine2.py').read().split("exec(open('/tmp/claude-0/t/opt/base.py').read())")[1].split("init=")[0])
for Rs in [int(a)*1000 for a in sys.argv[4].split(',')]:
    bestv=None
    for v0 in [(6800,-64900,85.0),(6400,-65900,83.5),(6200,-66600,85.0)]:
        o=minimize(lambda v: score(Rs,v[0],v[1],v[2],700),v0,method='Nelder-Mead',options=dict(initial_simplex=[v0,[v0[0]+1500,v0[1],v0[2]],[v0[0],v0[1]+1500,v0[2]],[v0[0],v0[1],v0[2]+2]],maxiter=500,xatol=20,fatol=0.2))
        if bestv is None or o.fun<bestv.fun: bestv=o
    s,r,pm,pw=score(Rs,*bestv.x,700,ret=True)
    bm,bw,main,west=r['geo']
    dth=bw['thetas'][1]-bw['thetas'][0]; npl=WSP-3
    play=npl*dth*(bw['R']+WD/2)*WD/1e6
    print(WSP,WD,WST,Rs//1000,'playroom %.0f'%play,'protrude %.0f/%.0f'%(pm,pw),'ne %.2f'%(r['ne']/1000),'P',r['parking'],'score %.1f'%s,[round(float(t),1) for t in bestv.x])
