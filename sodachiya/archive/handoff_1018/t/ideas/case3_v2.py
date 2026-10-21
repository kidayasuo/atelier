exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
import rhino3dm as r3
from shapely.ops import triangulate
ZE,ZW=8000.0,4500.0; Z2=3250.0; KH=9.0; K2=8.0; CL=2500.0; SH=1000.0   # CL: 中の柱の列, SH: 階段を奥へずらす量（吹抜の幅）
def zroof(k,d,L): return ZE+(ZW-ZE)*d/max(L,1)
def seg(k):
    kq=min(kk,key=lambda x:abs(x-k)); return segs[kq]
def P(k,d,z):
    a,b,L=seg(k); dd=min(d,L); p=a+(b-a)*dd/L; return (p[0],p[1],z)
def Lk(k): return seg(k)[2]
UIN0=float(np.median(uin))
def region(k0,k1,d0,d1,n=16):
    A=[tuple(at(k,UIN0+d0 if d0>0 else -5000)) for k in np.linspace(k0,k1,n)]
    B=[tuple(at(k,UIN0+min(d1,40000))) for k in np.linspace(k1,k0,n)]
    return SP(A+B).buffer(0).intersection(W)
# ---------- rooms ----------
ktip=kk[0]
R1={}
R1['土間']=region(KH,13.5,0,CL)
R1['キッチン']=region(KH,11.0,CL,60000)                  # 食品庫を含む
R1['検収・職員口']=region(11.0,13.5,CL,60000)            # 南の端：搬入と職員の出入り
STAIR=region(K2,KH,300+SH,3100+SH)                              # 折り返し階段（囲われた箱、土間から入る）
R1['階段']=STAIR
R1['遊戯室']=W.difference(unary_union([R1[k] for k in R1]))
R2={}
R2['ホール2']=unary_union([region(9,10,1000,4100),region(10,11,3000,4100)])
R2['便所・湯沸']=region(10,11,1000,3000)
R2['会議室']=region(K2,10,4100,9000)                      # 北の壁 (k=8) に遊戯室を見下ろす室内窓
R2['休憩室']=unary_union([region(10,13.5,4100,7200),region(11,13.5,1000,4100)])
R2['ぐったり休憩']=unary_union([region(10,13.5,7200,10500),region(K2,10,9000,10500)])
R2['吹抜']=unary_union([region(K2,9,0,1300),region(9,13.5,0,1000)])
for n,p in list(R1.items())+list(R2.items()): print('%s %.0f m2'%(n,p.area/1e6))
# ---------- model ----------
model=r3.File3dm(); model.Settings.ModelUnitSystem=r3.UnitSystem.Millimeters
LY={}
def layer(name,rgb):
    L=r3.Layer(); L.Name=name; L.Color=(rgb[0],rgb[1],rgb[2],255); LY[name]=model.Layers.Add(L)
for n,c in [('00_敷地',(80,80,80)),('01_公園・駐車場',(90,150,80)),('10_本館_屋根',(200,190,170)),('11_本館_骨組み',(140,100,60)),
            ('20_西館_屋根',(150,140,120)),('21_西館_外壁',(215,200,175)),('22_西館_骨組み',(140,100,60)),('23_西館_2階床',(170,160,150)),('24_西館_間仕切り',(235,230,220)),('25_西館_階段',(120,110,100)),('27_西館_室内窓',(170,210,230)),
            ('31_1F_遊戯室',(205,224,242)),('32_1F_キッチン',(190,215,238)),('33_1F_土間',(250,233,184)),('34_1F_検収・職員口',(170,200,225)),('35_機械室（本館の北）',(190,190,190)),('26_室外機置場',(150,150,150)),('36_1F_階段',(120,110,100)),
            ('41_2F_ホール',(240,240,240)),('42_2F_便所・湯沸',(210,210,210)),('43_2F_会議室',(220,205,240)),('44_2F_休憩室',(232,221,243)),('45_2F_ぐったり休憩',(245,225,235))]:
    layer(n,c)
def at_(n): a=r3.ObjectAttributes(); a.LayerIndex=LY[n]; return a
class MB:
    def __init__(s): s.m=r3.Mesh(); s.n=0
    def f(s,q):
        for p in q: s.m.Vertices.Add(float(p[0]),float(p[1]),float(p[2]))
        if len(q)==4: s.m.Faces.AddFace(s.n,s.n+1,s.n+2,s.n+3)
        else: s.m.Faces.AddFace(s.n,s.n+1,s.n+2)
        s.n+=len(q)
    def box(s,p0,p1,w,h,up=None):
        """p0→p1 の軸、幅 w（水平）、高さ h（上端が p0-p1、下へ h）"""
        p0=np.array(p0,float); p1=np.array(p1,float); ax=p1-p0
        hz=np.array([ax[0],ax[1],0.0])
        side=np.array([-hz[1],hz[0],0.0]); 
        if np.linalg.norm(side)<1e-6: side=np.array([1.0,0,0])
        side=side/np.linalg.norm(side)*w/2; dn=np.array([0,0,-h])
        c=[p0-side,p0+side,p1+side,p1-side]; c2=[x+dn for x in c]
        for q in ([c[0],c[1],c[2],c[3]],[c2[3],c2[2],c2[1],c2[0]],[c[0],c[3],c2[3],c2[0]],[c[1],c2[1],c2[2],c[2]],[c[0],c2[0],c2[1],c[1]],[c[3],c[2],c2[2],c2[3]]): s.f(q)
    def col(s,p,z0,z1,w=400,t=180,axis=(1,0)):
        ax=np.array([axis[0],axis[1],0.0]); ax/=np.linalg.norm(ax); sd=np.array([-ax[1],ax[0],0.0])
        p=np.array([p[0],p[1],0.0]); c=[p-ax*w/2-sd*t/2,p+ax*w/2-sd*t/2,p+ax*w/2+sd*t/2,p-ax*w/2+sd*t/2]
        lo=[x+[0,0,z0] for x in c]; hi=[x+[0,0,z1] for x in c]
        for q in ([lo[3],lo[2],lo[1],lo[0]],[hi[0],hi[1],hi[2],hi[3]])+tuple([lo[i],lo[(i+1)%4],hi[(i+1)%4],hi[i]] for i in range(4)): s.f(q)
    def flat(s,poly,z):
        for t in triangulate(poly):
            if poly.contains(t.centroid): s.f([(x,y,z) for x,y in list(t.exterior.coords)[:3]])
    def add(s,n):
        if s.n: s.m.Normals.ComputeNormals(); s.m.Compact(); model.Objects.AddMesh(s.m,at_(n))
def curve(pts,n):
    pl=r3.Polyline(len(pts))
    for p in pts: pl.Add(float(p[0]),float(p[1]),float(p[2] if len(p)>2 else 0))
    model.Objects.AddCurve(r3.PolylineCurve(pl),at_(n))
# site
curve(list(site.exterior.coords),'00_敷地'); curve(list(setb.exterior.coords),'00_敷地')
curve(list(park.exterior.coords),'01_公園・駐車場'); curve(list(D['pk'].exterior.coords),'01_公園・駐車場')
# ---------- main: roof + frames ----------
def mw(k,u,z): p=world(bm,thf(k),u,0); return (p[0],p[1],z)
zm=lambda u: 3000+u/12000*1000
m=MB()
for k0 in range(19):
    us=[-3000,0,3000,6000,9000,12000,12200]
    for u0,u1 in zip(us,us[1:]): m.f([mw(k0,u0,zm(u0)+150),mw(k0+1,u0,zm(u0)+150),mw(k0+1,u1,zm(u1)+150),mw(k0,u1,zm(u1)+150)])
m.add('10_本館_屋根')
mf=MB()
for k in range(20):
    rad=np.array(world(bm,thf(k),1000,0)[:2])-np.array(world(bm,thf(k),0,0)[:2])
    for u in (0,12000): mf.col(mw(k,u,0),0,zm(u),axis=rad)
    mf.box(mw(k,-3000,zm(-3000)),mw(k,12200,zm(12200)),360,600)
for k in range(19):
    for u,zz in ((0,zm(0)-300),(12000,zm(12000)-300)):
        mf.box(mw(k,u,zz+100),mw(k+1,u,zz+100),200,400)
mf.add('11_本館_骨組み')
# ---------- west: roof ----------
mr=MB(); nt=14
for i in range(len(kk)-1):
    for j in range(nt):
        def Q(ii,t):
            a,b,L=segs[kk[ii]]; p=a+(b-a)*t; return (p[0],p[1],zroof(kk[ii],t*L,L)+150)
        mr.f([Q(i,j/nt),Q(i+1,j/nt),Q(i+1,(j+1)/nt),Q(i,(j+1)/nt)])
mr.add('20_西館_屋根')
def zat3(p):
    k,u=ku(p); k=np.clip(k,kk[0],kk[-1]); a=np.interp(k,kk,uin); b=np.interp(k,kk,uout); L=b-a
    return zroof(k,np.clip(u-a,0,L),L)+150
mw_=MB(); cs=list(W.exterior.coords)
for a,b in zip(cs,cs[1:]): mw_.f([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zat3(b)),(a[0],a[1],zat3(a))])
mw_.add('21_西館_外壁')
# ---------- west: frames ----------
wf=MB()
kint=[k for k in range(int(math.ceil(ktip+0.3)),13) if min(abs(kk-k))<0.2 or k==12]
kint=[k for k in kint if k<=kk[-1]+0.01] ; kint=[min(kk,key=lambda x:abs(x-k)) for k in kint]
for k in kint:
    a,b,L=segs[k]; rad=b-a
    din,dout=200.0,L-200.0
    cols=[din,dout]+([CL] if k>=K2-0.01 else [])
    for d in cols:
        top=zroof(k,d,L)-(700 if d in (din,dout) else 700)
        wf.col(P(k,d,0)[:2],0,zroof(k,d,L),axis=rad)
    wf.box(P(k,0,zroof(k,0,L)),P(k,L,zroof(k,L,L)),360,700)            # 屋根梁（集成材 2 枚合わせ）
    if k>=K2-0.01:
        wf.box(P(k,0,Z2),P(k,dout,Z2),360,600)                    # 2 階の床梁：外の柱まで渡す（k=8,9,10,11 の 4 本）

# 桁（柱の列に沿って）
for k0,k1 in zip(kint,kint[1:]):
    for d in (200.0,'out'):
        dd0=d if d!='out' else Lk(k0)-200; dd1=d if d!='out' else Lk(k1)-200
        wf.box(P(k0,dd0,zroof(k0,dd0,Lk(k0))-150),P(k1,dd1,zroof(k1,dd1,Lk(k1))-150),200,400)
    if k0>=K2-0.01:
        for d in (200.0,CL,7200.0,10500.0):
            wf.box(P(k0,d,Z2-80),P(k1,d,Z2-80),200,400)
        wf.box(P(k0,CL,zroof(k0,CL,Lk(k0))-150),P(k1,CL,zroof(k1,CL,Lk(k1))-150),200,400)
wf.add('22_西館_骨組み')
# ---------- floors, partitions, stair ----------
lay1={'遊戯室':'31_1F_遊戯室','キッチン':'32_1F_キッチン','土間':'33_1F_土間','検収・職員口':'34_1F_検収・職員口','階段':'36_1F_階段'}
for n,p in R1.items():
    for g in getattr(p,'geoms',[p]):
        if g.area>1e5: mm=MB(); mm.flat(g,10.0); mm.add(lay1[n])
lay2={'ホール2':'41_2F_ホール','便所・湯沸':'42_2F_便所・湯沸','会議室':'43_2F_会議室','休憩室':'44_2F_休憩室','ぐったり休憩':'45_2F_ぐったり休憩'}
for n,p in R2.items():
    if n in lay2:
        for g in getattr(p,'geoms',[p]):
            if g.area>1e5: mm=MB(); mm.flat(g,Z2+10); mm.add(lay2[n])
# partitions: boundaries between 1F rooms (except 遊戯室-階段 open) and 2F rooms
def zceil(p,level):
    return (Z2-600) if level==1 and ku(p)[0]>=K2 else zat3(p)-150
def walls_between(A,B,level,z0,mb):
    L=A.boundary.intersection(B.boundary)
    for ln in getattr(L,'geoms',[L]):
        if ln.is_empty or ln.length<300 or ln.geom_type not in ('LineString',): continue
        cs=list(ln.coords)
        for a,b in zip(cs,cs[1:]):
            za=zceil(a,level); zb=zceil(b,level)
            mb.f([(a[0],a[1],z0),(b[0],b[1],z0),(b[0],b[1],za),(a[0],a[1],zb if False else za)])
pw=MB()
pairs1=[('キッチン','土間'),('キッチン','検収・職員口'),('キッチン','遊戯室')]
for a,b in pairs1: walls_between(R1[a].buffer(1),R1[b].buffer(1),1,0,pw)
pairs2=[('会議室','休憩室'),('会議室','ぐったり休憩'),('休憩室','ぐったり休憩'),('便所・湯沸','ホール2'),('便所・湯沸','休憩室'),('会議室','ホール2'),('便所・湯沸','吹抜'),('休憩室','吹抜')]
for a,b in pairs2: walls_between(R2[a].buffer(1),R2[b].buffer(1),2,Z2,pw)
# 2 階の北の面 (k=8)：会議室は腰壁 + 室内窓、ぐったりは壁
gl=MB()
def kface(d0,d1,z0,z1,mb,n=6):
    ds=np.linspace(d0,d1,n+1)
    for a,b in zip(ds,ds[1:]):
        pa=P(K2,a,0); pb=P(K2,b,0)
        za=zroof(K2,a,Lk(K2))-80 if z1 is None else z1; zb=zroof(K2,b,Lk(K2))-80 if z1 is None else z1
        mb.f([(pa[0],pa[1],z0),(pb[0],pb[1],z0),(pb[0],pb[1],zb),(pa[0],pa[1],za)])
kface(4100,9000,Z2,Z2+850,pw)              # 腰壁 h=850（座ると子どもが見える／子どもからは見上げにくい）
kface(4100,9000,Z2+850,None,gl)            # 室内窓
kface(9000,10500,Z2,None,pw); kface(10500,Lk(K2),Z2,None,pw)
gl.add('27_西館_室内窓')
pw.add('24_西館_間仕切り')
# 2F slab (rooms) 
sl=MB(); sl.flat(unary_union([R2[k] for k in lay2]).buffer(0),Z2-80); sl.add('23_西館_2階床')
# stair: 折り返し（土間から北へ 9 段 → 踊り場 → 南へ 9 段で 2 階のホールへ）
st=MB(); n=8; kb,kl=KH,8.33; rz=Z2/18                      # 蹴上 3250/18 = 181、各 8 段＋踊り場
def tread(k0,k1,d0,d1,z):
    st.f([P(k0,d0,z),P(k0,d1,z),P(k1,d1,z),P(k1,d0,z)]); st.f([P(k0,d0,z-rz),P(k0,d1,z-rz),P(k0,d1,z),P(k0,d0,z)])
for i in range(n):
    tread(kb-(kb-kl)*i/n,kb-(kb-kl)*(i+1)/n,350+SH,1450+SH,rz*(i+1))
tread(kl,8.06,350+SH,2650+SH,rz*9)                            # 踊り場
for i in range(n):
    tread(kl+(kb-kl)*i/n,kl+(kb-kl)*(i+1)/n,1550+SH,2650+SH,rz*(10+i))
st.add('25_西館_階段')
# 階段を囲う壁（遊戯室の側は天井まで閉じる。土間の側だけ開く）
ew=MB()
cs=list(STAIR.exterior.coords)
for a,b in zip(cs,cs[1:]):
    m=((a[0]+b[0])/2,(a[1]+b[1])/2); km,um=ku(m)
    dm=um-np.interp(km,kk,uin)
    if km>KH-0.05 and dm<CL: continue                        # 土間側の入口（キッチン側は閉じる）
    za=zat3(a)-150; zb=zat3(b)-150
    ew.f([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zb),(a[0],a[1],za)])
ew.add('24_西館_間仕切り')
# 本館の北の三角形の空き地に、丸い機械室と室外機置場
from shapely.ops import polylabel
mainP=SP([world(bm,thf(0),u,0)[:2] for u in np.linspace(-3000,12200,10)]+[world(bm,thf(k),12200,0)[:2] for k in np.linspace(0,19,30)]+[world(bm,thf(19),u,0)[:2] for u in np.linspace(12200,-3000,10)]+[world(bm,thf(k),-3000,0)[:2] for k in np.linspace(19,0,30)])
a_=np.array(world(bm,thf(0),-40000,0)[:2]); b_=np.array(world(bm,thf(0),60000,0)[:2]); t_=(b_-a_)/np.linalg.norm(b_-a_); n_=np.array([-t_[1],t_[0]])
if np.dot(n_,np.array(world(bm,thf(0),5000,0)[:2])-np.array(world(bm,thf(3),5000,0)[:2]))<0: n_=-n_
tri=site.intersection(SP([tuple(a_),tuple(b_),tuple(b_+n_*60000),tuple(a_+n_*60000)])).difference(unary_union([mainP,W]).buffer(500))
tri=max(getattr(tri,'geoms',[tri]),key=lambda g:g.area)
NRd=np.array((0,0))-np.array((-25830,-20540)); NRd=NRd/np.linalg.norm(NRd); NRn=np.array([NRd[1],-NRd[0]])   # 北の道路から敷地の内側へ
RD=3100.0
best=None
for x in np.arange(tri.bounds[0],tri.bounds[2],250):
    for y in np.arange(tri.bounds[1],tri.bounds[3],250):
        c=SPt(x,y)
        if tri.contains(c.buffer(RD)) :
            dn=SL([(0,0),(34860,-43830)]).distance(c)
            if best is None or dn>best[0]: best=(dn,(x,y))
cx,cy=best[1]; print('drum centre',round(cx),round(cy),'dist to neighbour edge %.1f m'%(best[0]/1000))
dr=MB(); nseg=40
ang=np.linspace(0,2*math.pi,nseg+1)
for a0,a1 in zip(ang,ang[1:]):
    p0=(cx+RD*math.cos(a0),cy+RD*math.sin(a0)); p1=(cx+RD*math.cos(a1),cy+RD*math.sin(a1))
    dr.f([(p0[0],p0[1],0),(p1[0],p1[1],0),(p1[0],p1[1],3200),(p0[0],p0[1],3200)])
    dr.f([(cx,cy,3200),(p0[0],p0[1],3200),(p1[0],p1[1],3200)])
dr.add('35_機械室（本館の北）')
# 室外機置場：丸い機械室と北の道路の間（隣家から最も遠い側）
yard=SPt(cx,cy).buffer(RD+2200).difference(SPt(cx,cy).buffer(RD+200)).intersection(tri)
side=SP([tuple(np.array([cx,cy])-NRn*20000-NRd*20000),tuple(np.array([cx,cy])-NRn*20000+NRd*20000),tuple(np.array([cx,cy])+NRd*20000),tuple(np.array([cx,cy])-NRd*20000)])
yard=yard.intersection(side)
yd=MB()
for g in getattr(yard,'geoms',[yard]):
    if g.area>2e5: yd.flat(g,20.0)
yd.add('26_室外機置場')
print('yard %.1f m2'%(yard.area/1e6))
model.Write('/home/claude/plans/rhino/sodachiya_west_case3.3dm',8)
print('written')
