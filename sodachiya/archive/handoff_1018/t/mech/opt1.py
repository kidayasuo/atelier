exec(open('/tmp/claude-0/t/ideas/conform.py').read().split("if __name__")[0])
import json
K0=-1
def conform2(bm,thf,at,mode,kcut=12.0,gap=700):
    main=band(bm,K0,19,-3000,12200)
    a=at(kcut,-20000); b=at(kcut,60000); t=unit(b-a); n=np.array([-t[1],t[0]])
    if np.dot(n,at(kcut-3,5000)-at(kcut,5000))<0: n=-n
    half=SP([tuple(a),tuple(b),tuple(b+n*90000),tuple(a+n*90000)])
    R=setb.intersection(half).difference(main.buffer(gap))
    q0=SPt(*at(kcut-2,6000))
    gs=[g for g in getattr(R,"geoms",[R]) if g.distance(q0)<1]
    if not gs: return SP()
    R=gs[0].buffer(-3000,resolution=16).buffer(3000,resolution=16)
    return R
def evalc2(Rs,x,y,ang,detail=False):
    bm,thf,at=mk(Rs,(x,y),ang)
    main=band(bm,K0,19,-3000,12200); body=band(bm,K0,19,0,12200); eave=band(bm,K0,19,-3000,0)
    west=conform2(bm,thf,at,'tri')
    blds=unary_union([main,west])
    pen=body.difference(setb).area/1e6*30+eave.difference(site.buffer(-300)).area/1e6*30+max(0,1000-NE.distance(blds))/50+park.intersection(blds.buffer(1000)).area/1e6*30
    bb=blds.buffer(1000,resolution=4); pk=None
    for s in np.arange(0,40500,500):
        p=[RA+RT*s+RN*500, RA+RT*(s+12500)+RN*500, RA+RT*(s+12500)+RN*12000, RA+RT*s+RN*12000]
        rect=SP([tuple(q) for q in p])
        if site.contains(rect) and not rect.intersects(bb) and not rect.intersects(park): pk=rect; break
    if pk is None: pen+=50; pk=SP()
    wa=west.area/1e6
    pen+=max(0,380-wa)/5
    g=site.difference(unary_union([blds,park,pk]))
    gs=[q for q in getattr(g,'geoms',[g]) if q.distance(SL([(34860,-43830),(-14440,-83040)]))<3000]
    ga=max([q.area for q in gs] or [0])/1e6
    if detail: return pen,ga,wa,dict(bm=bm,thf=thf,at=at,main=main,west=west,pk=pk)
    return pen,ga,wa
C=[c for c in json.load(open('/tmp/claude-0/t/ideas/conform.json')) if c[0]=='tri' and c[1]==205000][0]
print('current with ext',evalc2(C[1],*C[2]))
res=[]
for v0 in [C[2],[C[2][0]-2000,C[2][1]-2000,C[2][2]],[C[2][0]+1000,C[2][1]-3000,C[2][2]-1.5],[C[2][0]-1000,C[2][1]-3000,C[2][2]+1.5]]:
    f=lambda v: (lambda r: r[0]*10-r[1]/50)(evalc2(205000,*v))
    o=minimize(f,v0,method='Nelder-Mead',options=dict(initial_simplex=[v0,[v0[0]+1500,v0[1],v0[2]],[v0[0],v0[1]+1500,v0[2]],[v0[0],v0[1],v0[2]+2]],maxiter=250,xatol=20,fatol=0.02))
    r=evalc2(205000,*o.x); res.append((o.fun,list(map(float,o.x)),r)); print([round(float(t),1) for t in o.x],'pen %.3f garden %.0f west %.0f'%r)
best=min(res,key=lambda t:t[0]); json.dump(best[1],open('/tmp/claude-0/t/mech/opt1.json','w')); print('best',best)
