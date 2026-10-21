import sys, math, numpy as np
sys.path.insert(0,'/tmp/claude-0/mock2')
from shapely.geometry import Polygon as SP, Point as SPt, LineString as SL
from shapely.ops import unary_union
code=open('/home/claude/plans/rhino/sodachiya_frames_gh.py').read()
code=code.replace("    SPANS=9, ","    SPANS=10, ").replace("    D=11500.0,","    D=12000.0,").replace("    START=3,","    START=2,")
code=code.replace("Columns, Beams, Floor2, Girders, Grid, Footprint, Outside, OK, Report = gh_main()","pass")
G={'__name__':'gh'}; exec(compile(code,'gh','exec'),G)
site=SP([(0,0),(34860,-43830),(-14440,-83040),(-21910,-73650),(-25830,-20540)])
setb=SP([(-160,-1405),(33455,-43670),(-14280,-81635),(-20935,-73269),(-24794,-20994)])
NE=SL([(0,0),(34860,-43830)])
tip=np.array((-14440,-83040)); e1=np.array((-21910,-73650))-tip; e2=np.array((34860,-43830))-tip
e1=e1/np.linalg.norm(e1); e2=e2/np.linalg.norm(e2)
park=SP([tuple(tip),tuple(tip+e1*12000),tuple(tip+e1*12000+e2*12000),tuple(tip+e2*12000)])
RA=np.array((-21910,-73650)); RB=np.array((-25830,-20540)); RT=(RB-RA)/np.linalg.norm(RB-RA); RN=np.array((-RT[1],RT[0]))
if not site.contains(SPt(*(RA+RT*20000+RN*3000))): RN=-RN
world=G['world']
def place(Rs, se, ang_deg, gap):
    G['MAIN']['R']=Rs-G['MAIN']['D']; G['WEST']['GAP']=gap
    u=(math.cos(math.radians(ang_deg)),math.sin(math.radians(ang_deg)))
    G['set_placement_sw'](se,u,G['MAIN']['R']+G['east_edge_u']())
    M,W=G['MAIN'],G['WEST']
    dth=G['PITCH']/(M['R']+M['D']); th0=math.radians(G['THETA_MID_DEG'])-dth*M['SPANS']/2.0
    m=dict(M); m['thetas']=[th0+dth*i for i in range(M['SPANS']+1)]
    w=dict(W); w['R']=M['R']+M['D']+W['GAP']; w['thetas']=[th0+dth*(W['START']+i) for i in range(W['SPANS']+1)]
    return m,w
def band(B,k0,k1,u0,u1,n=24):
    th=lambda k: B['thetas'][0]+(B['thetas'][1]-B['thetas'][0])*k
    a=[world(B,th(k0+(k1-k0)*i/n),u0,0)[:2] for i in range(n+1)]
    b=[world(B,th(k1-(k1-k0)*i/n),u1,0)[:2] for i in range(n+1)]
    return SP(a+b)
def evaluate(Rs,se,ang,gap,detail=False):
    bm,bw=place(Rs,se,ang,gap)
    main=band(bm,0,19,-3000,12200); west=band(bw,0,10,-200,12200)
    blds=unary_union([main,west])
    r={}
    r['out_site']=blds.difference(site).area/1e6
    r['ne']=min(NE.distance(main),NE.distance(west))
    r['out_set']=blds.difference(setb).area/1e6
    r['park']=park.intersection(blds.buffer(1000,resolution=4)).area/1e6
    # parking 12.5 x 12 along west road
    bb=blds.buffer(1000,resolution=4)
    best=None
    for s in np.arange(0,53000-12500,500):
        p=[RA+RT*s+RN*500, RA+RT*(s+12500)+RN*500, RA+RT*(s+12500)+RN*12500, RA+RT*s+RN*12500]
        rect=SP([tuple(x) for x in p])
        if site.contains(rect) and not rect.intersects(bb) and not rect.intersects(park):
            best=s; break
    r['parking']=best
    # clearance margins
    r['margin']=min(setb.exterior.distance(main) if setb.contains(main) else -1, setb.exterior.distance(west) if setb.contains(west) else -1)
    r['garden']=site.difference(blds).area/1e6
    if detail: r['geo']=(bm,bw,main,west)
    return r
