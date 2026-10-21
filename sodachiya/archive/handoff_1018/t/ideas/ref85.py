import sys
WSP,WD,WST=10,12000.0,2
exec(open('/tmp/claude-0/t/opt/base2.py').read())
from scipy.optimize import minimize
tip=np.array((-14440,-83040))
def mk(Rs,se,ang):
    bm,bw=place(Rs,se,ang,700)
    thf=lambda k: bm['thetas'][0]+(bm['thetas'][1]-bm['thetas'][0])*k
    at=lambda k,u: np.array(world(bm,thf(k),12000+u,0)[:2])
    return bm,thf,at
def layout(name,at):
    sh={}
    if name=='dots':
        sh['キッチン']=SPt(*at(10.5,700+5500)).buffer(5500,resolution=24)
        sh['遊戯室']=SPt(*at(6.6,700+7600)).buffer(7600,resolution=24).union(SPt(*at(3.6,700+7600)).buffer(7600,resolution=24))
        sh['階段']=SPt(*at(8.9,700+2600)).buffer(2300,resolution=16)
    elif name=='bar':
        pts=[tuple(at(k,700)) for k in np.linspace(2,12,21)]+[tuple(at(k,12700)) for k in np.linspace(12,2,21)]
        sh['_all']=SP(pts)
    elif name=='bardot':
        pts=[tuple(at(k,700)) for k in np.linspace(2,9,15)]+[tuple(at(k,12700)) for k in np.linspace(9,2,15)]
        sh['遊戯室']=SP(pts).buffer(1500,resolution=8).buffer(-1500,resolution=8)
        sh['キッチン']=SPt(*at(10.6,700+5600)).buffer(5600,resolution=24)
    elif name=='pill':
        a=at(3.0,700+6500); b=at(11.0,700+6500)
        sh['_all']=SL([tuple(a),tuple(b)]).buffer(6500,resolution=24)
    return sh
def evalp(Rs,x,y,ang,name,detail=False):
    bm,thf,at=mk(Rs,(x,y),ang)
    main=band(bm,0,19,-3000,12200); body=band(bm,0,19,0,12200); eave=band(bm,0,19,-3000,0)
    sh=layout(name,at); west=unary_union(list(sh.values()))
    blds=unary_union([main,west])
    pen=unary_union([body,west]).difference(setb).area/1e6*30+eave.difference(site.buffer(-300)).area/1e6*30+max(0,1000-NE.distance(blds))/50+park.intersection(blds.buffer(1000)).area/1e6*30
    bb=blds.buffer(1000,resolution=4); pk=None
    for s in np.arange(0,40500,500):
        p=[RA+RT*s+RN*500, RA+RT*(s+12500)+RN*500, RA+RT*(s+12500)+RN*12000, RA+RT*s+RN*12000]
        rect=SP([tuple(q) for q in p])
        if site.contains(rect) and not rect.intersects(bb) and not rect.intersects(park): pk=rect; break
    if pk is None: pen+=50; pk=SP()
    g=site.difference(unary_union([blds,park,pk]))
    gs=[q for q in getattr(g,'geoms',[g]) if q.distance(SL([(34860,-43830),(-14440,-83040)]))<3000]
    ga=max([q.area for q in gs] or [0])/1e6
    # east-side garden only: subtract area west of main (approx: pieces on west of main's spine)
    if detail: return pen,ga,dict(bm=bm,thf=thf,at=at,main=main,sh=sh,pk=pk,west=west)
    return pen,ga
def obj(v,Rs,name): pen,ga=evalp(Rs,v[0],v[1],v[2],name); return pen*10-ga/50

print('R85 bar', evalp(85000,6571.2,-64875.1,80.8,'bar'))
