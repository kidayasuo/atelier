exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
import rhino3dm as r3
SINK=0.0
KB=4.0                       # 規則的な架構（奥行き 12m）が始まる位置
def bandpoly(k0,k1,u0,u1,n=40):
    return SP([tuple(at(k,u0)) for k in np.linspace(k0,k1,n)]+[tuple(at(k,u1)) for k in np.linspace(k1,k0,n)])
band=bandpoly(KB,kk[-1]+0.0,700,12700)
tipr=W.intersection(SP([tuple(at(k,0)) for k in np.linspace(0,KB,20)]+[tuple(at(k,60000)) for k in np.linspace(KB,0,20)]))
W=unary_union([band,tipr]).buffer(1,join_style=2).buffer(-1,join_style=2)
# 架構ごとの区間を W から取り直す
segs={}
for k in np.arange(1.0,13.0,0.125):
    Lg=SL([tuple(at(k,0)),tuple(at(k,60000))]).intersection(W)
    if Lg.is_empty: continue
    if Lg.geom_type!='LineString': Lg=max(Lg.geoms,key=lambda g:g.length)
    a,b=np.array(Lg.coords[0]),np.array(Lg.coords[-1]); o=at(k,0)
    if np.linalg.norm(a-o)>np.linalg.norm(b-o): a,b=b,a
    segs[round(k,3)]=(a,b,np.linalg.norm(b-a))
kk=np.array(sorted(segs)); uin=np.array([np.linalg.norm(segs[k][0]-Cc)-Re-12000 for k in kk]); uout=np.array([np.linalg.norm(segs[k][1]-Cc)-Re-12000 for k in kk])
ZB=3000.0                    # 1 階の高さの水平な梁（架構はすべて同じ形）
ZTOP=5400.0
def zridge(k):               # 本館側の尾根：丘の案と同じ高さで南へ上がる（梁の上 0.6m 以上は確保）
    return max(ZB+600.0, 400+(ZTOP-400)*ss(np.clip((k-1.6)/(8.0-1.6),0,1)))
ktip=kk[0]
def zprof(k,d,L):
    if k<=KH:
        kk_=max(k,KB)
        zb=zridge(kk_)+(ZB-zridge(kk_))*min(d,12000.0)/12000.0
        if k>=KB: return zb
        f=0.15+0.85*(k-ktip)/(KB-ktip)              # 北の先端の差し掛け
        return max(500.0,zb*f)
    d2=max(1500.0,min(7000.0,L-4000.0))
    if d<=d2: return 6600.0
    return 3600.0
# --- areas
play=W.intersection(SP([tuple(at(1.0,0))]+[tuple(at(k,0)) for k in np.linspace(1,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,1,20)]))
kit=W.difference(play)
pts=[(x,y) for x in np.arange(play.bounds[0],play.bounds[2],300) for y in np.arange(play.bounds[1],play.bounds[3],300) if play.contains(SPt(x,y))]
h=np.array([(zat2(p)-300+SINK)/1000 for p in pts])
print('playroom %.0f m2, avg ceiling %.2f, >=1.4: %.0f, >=2.1: %.0f, kitchen block %.0f m2'%(play.area/1e6,h.mean(),(h>=1.4).sum()*.09,(h>=2.1).sum()*.09,kit.area/1e6))
# --- model
model=r3.File3dm(); model.Settings.ModelUnitSystem=r3.UnitSystem.Millimeters
def layer(name,rgb):
    L=r3.Layer(); L.Name=name; L.Color=(rgb[0],rgb[1],rgb[2],255); return model.Layers.Add(L)
LY={}
for n,c in [('00_敷地',(80,80,80)),('01_公園・駐車場',(90,150,80)),('10_本館',(200,190,170)),('11_本館_室割り',(150,120,90)),
            ('20_西館_屋根',(110,160,90)),('21_西館_外壁',(215,200,175)),('22_西館_床',(180,170,150)),('23_西館_2階',(160,130,190)),('30_架構の線',(60,60,160))]:
    LY[n]=layer(n,c)
def attrs(n):
    a=r3.ObjectAttributes(); a.LayerIndex=LY[n]; return a
class MB:
    def __init__(s): s.m=r3.Mesh(); s.n=0
    def quad(s,q):
        for p in q: s.m.Vertices.Add(float(p[0]),float(p[1]),float(p[2]))
        if len(q)==4: s.m.Faces.AddFace(s.n,s.n+1,s.n+2,s.n+3)
        else: s.m.Faces.AddFace(s.n,s.n+1,s.n+2)
        s.n+=len(q)
    def add(s,name):
        s.m.Normals.ComputeNormals(); s.m.Compact(); model.Objects.AddMesh(s.m,attrs(name))
def curve(pts,name,z=0.0):
    pl=r3.Polyline(len(pts))
    for p in pts: pl.Add(float(p[0]),float(p[1]),float(p[2] if len(p)>2 else z))
    model.Objects.AddCurve(r3.PolylineCurve(pl),attrs(name))
def poly_fill(poly,z,mb,step=None):
    # triangulate polygon (shapely) and add as flat mesh
    from shapely.ops import triangulate
    for t in triangulate(poly):
        c=t.centroid
        if poly.contains(c):
            q=list(t.exterior.coords)[:3]; mb.quad([(x,y,z) for x,y in q])
# site
curve(list(site.exterior.coords),'00_敷地'); curve(list(setb.exterior.coords),'00_敷地')
curve(list(park.exterior.coords),'01_公園・駐車場'); curve(list(D['pk'].exterior.coords),'01_公園・駐車場')
# main
def mw(k,u,z): p=world(bm,thf(k),u,0); return (p[0],p[1],z)
zm=lambda u: 3000+u/12000*1000
mb=MB()
for k0 in range(19):
    k1=k0+1
    us=[-3000,0,3000,6000,9000,12000,12200]
    for u0,u1 in zip(us,us[1:]):
        mb.quad([mw(k0,u0,zm(u0)),mw(k1,u0,zm(u0)),mw(k1,u1,zm(u1)),mw(k0,u1,zm(u1))])
    for u in (0,12200):
        mb.quad([mw(k0,u,0),mw(k1,u,0),mw(k1,u,zm(u)),mw(k0,u,zm(u))])
for k in (0,19):
    us=[0,6000,12200]
    for u0,u1 in zip(us,us[1:]): mb.quad([mw(k,u0,0),mw(k,u1,0),mw(k,u1,zm(u1)),mw(k,u0,zm(u0))])
mb.add('10_本館')
mrooms=[(1,3,'0・1歳'),(4,5,'2歳'),(6,7,'事務・医務'),(8,10,'ホール'),(11,11,'便・倉庫'),(12,13,'3歳'),(14,14,'便'),(15,16,'4歳'),(17,17,'便'),(18,19,'5歳')]
for s0,s1,t in mrooms:
    k0,k1=19-s1,20-s0
    curve([mw(k0,0,10),mw(k0,12000,10)],'11_本館_室割り')
    p=world(bm,thf((k0+k1)/2),6000,0); model.Objects.AddTextDot(t,r3.Point3d(p[0],p[1],1500),attrs('11_本館_室割り'))
# west roof
mb=MB(); mk=MB(); nt=16
for i in range(len(kk)-1):
    for j in range(nt):
        def P(ii,t):
            a,b,L=segs[kk[ii]]; p=a+(b-a)*t; return (p[0],p[1],zprof(kk[ii],t*L,L))
        (mb if kk[i]<KH else mk).quad([P(i,j/nt),P(i+1,j/nt),P(i+1,(j+1)/nt),P(i,(j+1)/nt)])
mb.add('20_西館_屋根'); mk.add('23_西館_2階')
# ridge line
if False: curve([(lambda a,b,L: tuple(a+(b-a)*min(DRH,L*.5)/L)+(lines(k)[1],))(*segs[k]) for k in kk if k<=KH],'30_架構の線')
# walls
mw_=MB()
cs=list(W.exterior.coords)
for a,b in zip(cs,cs[1:]):
    za,zb=zat2(a) if True else 0,zat2(b)
    ka,_=ku(a); kb,_=ku(b)
    fa=-SINK if ka<KH else 0.0; fb=-SINK if kb<KH else 0.0
    mw_.quad([(a[0],a[1],fa),(b[0],b[1],fb),(b[0],b[1],zb),(a[0],a[1],za)])
# step walls: hill/kitchen junction and 2F west face
a,b,L=segs[min(kk,key=lambda x:abs(x-KH))]
for d0,d1 in zip(np.linspace(0,L,13),np.linspace(0,L,13)[1:]):
    p0=a+(b-a)*d0/L; p1=a+(b-a)*d1/L
    z0a,z1a=zprof(KH-1e-3,d0,L),zprof(KH-1e-3,d1,L); z0b,z1b=zprof(KH+1e-3,d0,L),zprof(KH+1e-3,d1,L)
    mw_.quad([(p0[0],p0[1],min(z0a,z0b)),(p1[0],p1[1],min(z1a,z1b)),(p1[0],p1[1],max(z1a,z1b)),(p0[0],p0[1],max(z0a,z0b))])
ks=[k for k in kk if k>=KH]
for k0,k1 in zip(ks,ks[1:]):
    def Q(k,z):
        a,b,L=segs[k]; d2=max(1500.0,min(7000.0,L-4000.0)); p=a+(b-a)*(d2/L); return (p[0],p[1],z)
    mw_.quad([Q(k0,3600),Q(k1,3600),Q(k1,6600),Q(k0,6600)])
mw_.add('21_西館_外壁')
# floors
mf=MB(); poly_fill(play,-SINK,mf); poly_fill(kit,0.0,mf); mf.add('22_西館_床')
# 2F slab + rooms outline + void
def band_poly(k0,k1,d0,d1,n=10):
    A=[];B=[]
    for k in np.linspace(k0,k1,n):
        kq=min(kk,key=lambda x:abs(x-k)); a,b,L=segs[kq]
        dd1=d1 if d1<7000 else max(1500.0,min(7000.0,L-4000.0))
        A.append(tuple(a+(b-a)*d0/L)); B.append(tuple(a+(b-a)*dd1/L))
    return SP(A+B[::-1])
slab=band_poly(KH+0.02,kk[-1],1500,7000).intersection(W)
m2=MB(); poly_fill(slab,3250.0,m2); m2.add('23_西館_2階')
curve([(x,y,3260) for x,y in slab.exterior.coords],'23_西館_2階')
vo=band_poly(KH+0.02,kk[-1],0,1500).intersection(W); curve([(x,y,6600) for x,y in vo.exterior.coords],'23_西館_2階')
for txt,pt in [('遊戯室（同じ門型 12m×5スパン＋トラス屋根＋北の差し掛け）',play.representative_point()),('キッチン',kit.representative_point()),('2階：休憩室',slab.representative_point()),('換気の吹抜',vo.representative_point())]:
    model.Objects.AddTextDot(txt,r3.Point3d(pt.x,pt.y,2000 if '2階' not in txt else 4500),attrs('22_西館_床' if '2階' not in txt else '23_西館_2階'))
for k in np.arange(KB,KH+0.01,1.0):
    kq=min(kk,key=lambda x:abs(x-k)); a,b,L=segs[kq]
    P=lambda d,z: (a+(b-a)*d/L).tolist()+[z]
    curve([P(0,0),P(0,ZB),P(L,ZB),P(L,0)],'30_架構の線')                 # 門型（梁は 1 階の高さで水平）
    curve([P(0,ZB),P(0,zprof(k,0,L)),P(L,ZB)],'30_架構の線')            # トラスの上弦と端の束
    n=6
    for i in range(1,n):
        d=L*i/n; curve([P(d,ZB),P(d,zprof(k,d,L))],'30_架構の線')        # 束
        if i%2==1: curve([P(L*(i-1)/n,ZB),P(d,zprof(k,d,L))],'30_架構の線')
        else: curve([P(d,zprof(k,d,L)),P(L*(i+1)/n,ZB)],'30_架構の線')
    # 梁の上の床（キャットウォーク／屋根裏の遊び場）を本館側 2.4m に
    curve([P(0,ZB+20),P(2400,ZB+20)],'23_西館_2階')
model.Write('/home/claude/plans/rhino/sodachiya_west_truss.3dm',8)
print('written')
