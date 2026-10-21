import sys
WSP,WD,WST=10,12000.0,2
exec(open('/tmp/claude-0/t/opt/base2.py').read())
setb=setb.buffer(-150)
NEb=NE
exec(open('/tmp/claude-0/t/opt/refine2.py').read().split("exec(open('/tmp/claude-0/t/opt/base.py').read())")[1].split("init=")[0])
def score2(Rs,x,y,a,gap):
    s,r,pm,pw=score(Rs,x,y,a,gap,ret=True)
    return s+max(0,1150-r['ne'])
best=None
for Rs in (85000,88000,90000):
  for v0 in [(6533,-65070,81.2),(6760,-64723,81.0),(7000,-64500,82)]:
    o=minimize(lambda v: score2(Rs,v[0],v[1],v[2],700),v0,method='Nelder-Mead',options=dict(initial_simplex=[v0,[v0[0]+800,v0[1],v0[2]],[v0[0],v0[1]+800,v0[2]],[v0[0],v0[1],v0[2]+1]],maxiter=600,xatol=10,fatol=0.05))
    s,r,pm,pw=score(Rs,*o.x,700,ret=True)
    print(Rs, [round(float(t),1) for t in o.x], 'score %.2f'%o.fun, 'protr %.0f %.0f ne %.0f P %s'%(pm,pw,r['ne'],r['parking']))
