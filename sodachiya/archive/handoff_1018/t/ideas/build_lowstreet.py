exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
import rhino3dm as r3
SINK=0.0
K2=5.0                      # これより北（北西の角）が 2 階の職員の部屋
ZW=4500.0                   # 西の道沿いの軒
ZE=7000.0                   # 本館側の高い縁
Z2I,Z2O=7000.0,6600.0       # 北西の角の 2 階の屋根（本館側→道路側）
def zprof(k,d,L):
    if k<K2: return Z2I+(Z2O-Z2I)*d/max(L,1)
    return ZE+(ZW-ZE)*d/max(L,1)
# --- areas
play=W.intersection(SP([tuple(at(K2,0))]+[tuple(at(k,0)) for k in np.linspace(K2,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,K2,20)]))
blk=W.intersection(SP([tuple(at(0.5,0))]+[tuple(at(k,0)) for k in np.linspace(0.5,K2,20)]+[tuple(at(K2,60000))]+[tuple(at(k,60000)) for k in np.linspace(K2,0.5,20)]))
kit=W.difference(play).difference(blk)
pts=[(x,y) for x in np.arange(play.bounds[0],play.bounds[2],300) for y in np.arange(play.bounds[1],play.bounds[3],300) if play.contains(SPt(x,y))]
h=np.array([(zat2(p)-300+SINK)/1000 for p in pts])
print('playroom %.0f m2 (avg ceiling %.2f), kitchen %.0f m2, NW block %.0f m2 (1F nest + 2F)'%(play.area/1e6,h.mean(),kit.area/1e6,blk.area/1e6))
# --- model
model=r3.File3dm(); model.Settings.ModelUnitSystem=r3.UnitSystem.Millimeters
def layer(name,rgb):
    L=r3.Layer(); L.Name=name; L.Color=(rgb[0],rgb[1],rgb[2],255); return model.Layers.Add(L)
LY={}
for n,c in [('00_敷地',(80,80,80)),('01_公園・駐車場',(90,150,80)),('10_本館',(200,190,170)),('11_本館_室割り',(150,120,90)),
            ('20_西館_屋根',(150,140,120)),('21_西館_外壁',(215,200,175)),('22_西館_床',(180,170,150)),('23_西館_2階',(160,130,190)),('30_架構の線',(60,60,160)),('24_縦格子',(120,90,60)),('25_西館_ハイサイド',(170,210,230))]:
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
mw_=MB(); mg=MB(); lat=[]
cs=list(W.exterior.coords)
def is_outer(p):
    k,u=ku(p); k=np.clip(k,kk[0],kk[-1]); return abs(u-np.interp(k,kk,uout))<150 and k>=K2
for a,b in zip(cs,cs[1:]):
    za,zb=zat2(a),zat2(b)
    m=((a[0]+b[0])/2,(a[1]+b[1])/2)
    if is_outer(m):
        mw_.quad([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zb-450),(a[0],a[1],za-450)])
        mg.quad([(a[0],a[1],za-450),(b[0],b[1],zb-450),(b[0],b[1],zb),(a[0],a[1],za)])
        seg=np.linalg.norm(np.array(b)-np.array(a))
        for t in np.arange(0,1,300/max(seg,1)):
            p=np.array(a)+(np.array(b)-np.array(a))*t; lat.append((p,zat2(p)-450))
    else:
        mw_.quad([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zb),(a[0],a[1],za)])
mg.add('25_西館_ハイサイド')
for p,z in lat:
    curve([(p[0],p[1],0),(p[0],p[1],z)],'24_縦格子')
mw_.add('21_西館_外壁')
# floors
mf=MB(); poly_fill(play,0.0,mf); poly_fill(kit,0.0,mf); poly_fill(blk,0.0,mf); mf.add('22_西館_床')
# 北西の角の 2 階
m2=MB(); poly_fill(blk,3250.0,m2); m2.add('23_西館_2階')
curve([(x,y,3260) for x,y in blk.exterior.coords],'23_西館_2階')
for txt,pt,z in [('遊戯室（本館側が高い吹抜け）',play.representative_point(),2000),('キッチン（平屋・高天井）',kit.representative_point(),2000),('1階：低い巣（遊戯室の一部）',blk.representative_point(),1500),('2階：休憩室・会議室・機械室',blk.representative_point(),4500)]:
    model.Objects.AddTextDot(txt,r3.Point3d(pt.x,pt.y,z),attrs('22_西館_床' if z<3000 else '23_西館_2階'))
mw2=MB()
a_,b_,L_=segs[min(kk,key=lambda x:abs(x-K2))]
for d0,d1 in zip(np.linspace(0,L_,13),np.linspace(0,L_,13)[1:]):
    p0=a_+(b_-a_)*d0/L_; p1=a_+(b_-a_)*d1/L_
    za0,za1=zprof(K2-1e-3,d0,L_),zprof(K2-1e-3,d1,L_); zb0,zb1=zprof(K2+1e-3,d0,L_),zprof(K2+1e-3,d1,L_)
    mw2.quad([(p0[0],p0[1],min(za0,zb0)),(p1[0],p1[1],min(za1,zb1)),(p1[0],p1[1],max(za1,zb1)),(p0[0],p0[1],max(za0,zb0))])
mw2.add('21_西館_外壁')
cw=[]
for k in [x for x in kk if K2<=x<=KH]:
    a,b,L=segs[k]; cw.append((a+(b-a)*1200/L).tolist()+[3250])
curve(cw,'23_西館_2階')
st=[]
for k in [x for x in kk if K2<=x<=KH]:
    a,b,L=segs[k]; t=(KH-k)/(KH-K2); st.append((a+(b-a)*2600/L).tolist()+[3250*t])
curve(st,'23_西館_2階')
for k in np.arange(2.0,12.01,1.0):
    kq=min(kk,key=lambda x:abs(x-k)); a,b,L=segs[kq]
    P=lambda d,z: (a+(b-a)*d/L).tolist()+[z]
    curve([P(0,0),P(0,zprof(kq,0,L)),P(L,zprof(kq,L,L)),P(L,0)],'30_架構の線')
    if k<K2: curve([P(0,3250),P(L,3250)],'30_架構の線')
model.Write('/home/claude/plans/rhino/sodachiya_west_lowstreet.3dm',8)
print('written')
