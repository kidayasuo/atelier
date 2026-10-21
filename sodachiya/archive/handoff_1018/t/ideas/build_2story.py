exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
import rhino3dm as r3
SINK=0.0
ZOUT=6300.0; NSL=50.0          # 道路側の軒 6.3m（2 階の天井高から）、勾配 1/50 で本館側へ上がる
def zprof(k,d,L):
    return ZOUT+(L-d)/NSL
# --- areas
play=W.intersection(SP([tuple(at(1.0,0))]+[tuple(at(k,0)) for k in np.linspace(1,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,1,20)]))
kit=W.difference(play)
pts=[(x,y) for x in np.arange(play.bounds[0],play.bounds[2],300) for y in np.arange(play.bounds[1],play.bounds[3],300) if play.contains(SPt(x,y))]
h=np.array([(zat2(p)-300+SINK)/1000 for p in pts])
print('playroom %.0f m2, avg ceiling(参考) %.2f, >=1.4: %.0f, >=2.1: %.0f, kitchen block %.0f m2'%(play.area/1e6,h.mean(),(h>=1.4).sum()*.09,(h>=2.1).sum()*.09,kit.area/1e6))
# --- model
model=r3.File3dm(); model.Settings.ModelUnitSystem=r3.UnitSystem.Millimeters
def layer(name,rgb):
    L=r3.Layer(); L.Name=name; L.Color=(rgb[0],rgb[1],rgb[2],255); return model.Layers.Add(L)
LY={}
for n,c in [('00_敷地',(80,80,80)),('01_公園・駐車場',(90,150,80)),('10_本館',(200,190,170)),('11_本館_室割り',(150,120,90)),
            ('20_西館_屋根',(150,140,120)),('21_西館_外壁',(215,200,175)),('22_西館_床',(180,170,150)),('23_西館_2階',(160,130,190)),('30_架構の線',(60,60,160))]:
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
        mb.quad([P(i,j/nt),P(i+1,j/nt),P(i+1,(j+1)/nt),P(i,(j+1)/nt)])
mb.add('20_西館_屋根')
# ridge line
if False: curve([(lambda a,b,L: tuple(a+(b-a)*min(DRH,L*.5)/L)+(lines(k)[1],))(*segs[k]) for k in kk if k<=KH],'30_尾根の線')
# walls
mw_=MB()
cs=list(W.exterior.coords)
for a,b in zip(cs,cs[1:]):
    za,zb=zat2(a) if True else 0,zat2(b)
    ka,_=ku(a); kb,_=ku(b)
    fa=-SINK if ka<KH else 0.0; fb=-SINK if kb<KH else 0.0
    mw_.quad([(a[0],a[1],fa),(b[0],b[1],fb),(b[0],b[1],zb),(a[0],a[1],za)])
mw_.add('21_西館_外壁')
# floors
mf=MB(); poly_fill(play,-SINK,mf); poly_fill(kit,0.0,mf); mf.add('22_西館_床')
# 2F slab + rooms outline + void
def band_poly(k0,k1,d0,d1,n=10):
    A=[];B=[]
    for k in np.linspace(k0,k1,n):
        kq=min(kk,key=lambda x:abs(x-k)); a,b,L=segs[kq]
        dd1=min(d1,L)
        A.append(tuple(a+(b-a)*d0/L)); B.append(tuple(a+(b-a)*dd1/L))
    return SP(A+B[::-1])
slab=band_poly(KH+0.02,kk[-1],1500,60000).intersection(W)
m2=MB(); poly_fill(slab,3250.0,m2); m2.add('23_西館_2階')
curve([(x,y,3260) for x,y in slab.exterior.coords],'23_西館_2階')
vo=band_poly(KH+0.02,kk[-1],0,1500).intersection(W); curve([(x,y,6600) for x,y in vo.exterior.coords],'23_西館_2階')
for txt,pt in [('遊戯室（吹抜け）',play.representative_point()),('キッチン',kit.representative_point()),('2階：休憩室',slab.representative_point()),('換気の吹抜',vo.representative_point())]:
    model.Objects.AddTextDot(txt,r3.Point3d(pt.x,pt.y,2000 if '2階' not in txt else 4500),attrs('22_西館_床' if '2階' not in txt else '23_西館_2階'))
for k in np.arange(2.0,12.01,1.0):
    kq=min(kk,key=lambda x:abs(x-k)); a,b,L=segs[kq]
    P=lambda d,z: (a+(b-a)*d/L).tolist()+[z]
    curve([P(0,0),P(0,zprof(kq,0,L)),P(L,zprof(kq,L,L)),P(L,0)],'30_架構の線')
    if k>=KH: curve([P(1500,3250),P(L,3250)],'30_架構の線')
# キャットウォーク（2 階の高さ、道路側の壁に沿って幅 1.2m）
cw=[]
for k in [x for x in kk if 3.0<=x<=KH]:
    a,b,L=segs[k]; cw.append((a+(b-a)*(L-1200)/L).tolist()+[3250])
curve(cw,'23_西館_2階')
model.Write('/home/claude/plans/rhino/sodachiya_west_2story.3dm',8)
print('written')
