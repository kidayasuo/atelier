exec(open('/tmp/claude-0/t/ideas/dots_opt3.py').read().split("import itertools")[0])
def unit(v):
    v=np.array(v,float); return v/np.linalg.norm(v)
def conform(bm,thf,at,mode,kcut=12.0,gap=700):
    main=band(bm,0,19,-3000,12200)
    a=at(kcut,-20000); b=at(kcut,60000); t=unit(b-a); n=np.array([-t[1],t[0]])
    if np.dot(n,at(kcut-3,5000)-at(kcut,5000))<0: n=-n
    half=SP([tuple(a),tuple(b),tuple(b+n*90000),tuple(a+n*90000)])
    base=setb if mode=='tri' else setb.buffer(-14000,resolution=24).buffer(14000,resolution=24)
    R=base.intersection(half).difference(main.buffer(gap))
    q0=SPt(*at(kcut-2,6000))
    gs=[g for g in getattr(R,"geoms",[R]) if g.distance(q0)<1]
    if not gs: return SP()
    R=gs[0]
    r=3000 if mode=='tri' else 2500
    R=R.buffer(-r,resolution=16).buffer(r,resolution=16)
    return R
def evalc(Rs,x,y,ang,mode,detail=False):
    bm,thf,at=mk(Rs,(x,y),ang)
    main=band(bm,0,19,-3000,12200); body=band(bm,0,19,0,12200); eave=band(bm,0,19,-3000,0)
    west=conform(bm,thf,at,mode)
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
if __name__=='__main__':
    import json
    out=[]
    for mode in ('tri','maga'):
      for Rs in (205000,160000):
        best=None
        for v0 in [(5870,-66029,88.0),(6200,-66500,86),(6500,-65500,84)]:
            f=lambda v: (lambda r: r[0]*10-r[1]/50)(evalc(Rs,v[0],v[1],v[2],mode))
            o=minimize(f,v0,method='Nelder-Mead',options=dict(initial_simplex=[v0,[v0[0]+2000,v0[1],v0[2]],[v0[0],v0[1]+2000,v0[2]],[v0[0],v0[1],v0[2]+3]],maxiter=300,xatol=30,fatol=0.05))
            if best is None or o.fun<best.fun: best=o
        pen,ga,wa=evalc(Rs,*best.x,mode)
        print(mode,Rs//1000,[round(float(t),1) for t in best.x],'pen %.2f garden %.0f west %.0f'%(pen,ga,wa))
        out.append((mode,Rs,list(map(float,best.x))))
    json.dump(out,open('/tmp/claude-0/t/ideas/conform.json','w'))
