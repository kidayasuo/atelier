WSHIFT=1000.0                                              # 西館を本館の円弧に沿って南へ 1 m
exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
import rhino3dm as r3
from shapely.ops import triangulate
ZE,ZW=8000.0,4500.0; Z2=3250.0; KH=9.0; K2=8.0; CL=2500.0; SH=1000.0; HB2=800.0   # CL: 土間とキッチンの境（柱なし）, HB2: 2 階の床梁のせい, SH: 階段を奥へずらす量（吹抜の幅）
def zroof(k,d,L): return ZE+(ZW-ZE)*d/max(L,1)
def seg(k):
    kq=min(kk,key=lambda x:abs(x-k)); return segs[kq]
def P(k,d,z):
    a,b,L=seg(k); dd=min(d,L); p=a+(b-a)*dd/L; return (p[0],p[1],z)
def Lk(k): return seg(k)[2]
UIN0=float(np.median(uin))
def segx(k):
    Lx=SL([tuple(at(k,-20000)),tuple(at(k,60000))]).intersection(W)
    if Lx.geom_type!='LineString': Lx=max(Lx.geoms,key=lambda g:g.length)
    a,b=np.array(Lx.coords[0]),np.array(Lx.coords[-1])
    if np.linalg.norm(a-at(k,-20000))>np.linalg.norm(b-at(k,-20000)): a,b=b,a
    return a,b,np.linalg.norm(b-a)
_ks=[ku(c)[0] for c in W.exterior.coords]; KEND=max(_ks)          # 南の壁（本館の放射線に沿った直線）
KE=KEND-0.07                                                   # 南の妻の架構（壁の内側 200）
DLIM=lambda L: (ZE-(Z2+2100))/(ZE-ZW)*L                         # 天井高 2.1 m の線

def region(k0,k1,d0,d1,n=16):
    A=[tuple(at(k,UIN0+d0 if d0>0 else -5000)) for k in np.linspace(k0,k1,n)]
    B=[tuple(at(k,UIN0+min(d1,40000))) for k in np.linspace(k1,k0,n)]
    return SP(A+B).buffer(0).intersection(W)
# ---------- rooms ----------
ktip=kk[0]
R1={}
KS=11.0
R1['土間']=region(KH,KEND+1,0,CL)
R1['キッチン']=region(KH,KS,CL,60000)                     # 食品庫・検収を含む。搬入は西の道路側の扉から
R1['食べる土間']=region(KS,KEND+1,CL,60000)              # 土間の続き：キッチンの南のカウンターの前、南の光
STAIR=region(K2,KH,300+SH,3100+SH)                        # 折り返し階段（囲われた箱、土間から入る）
R1['階段']=STAIR
R1['遊戯室']=W.difference(unary_union([R1[k] for k in R1]))
R2={}
R2['ホール2']=unary_union([region(9,10,1000,4100),region(10,11,3000,4100)])
R2['便所・湯沸']=region(10,11,1000,3000)
KM=9.75
R2['会議室']=region(K2,KM,4100,60000)                     # 遊戯室に面する 2 スパン、西の端まで。北の壁に室内窓
R2['休憩室']=unary_union([region(KM,KEND+1,4100,7200),region(11,KEND+1,1000,4100)])
R2['ぐったり休憩']=region(KM,KEND+1,7200,60000)           # 西の端まで（低い）
R2['吹抜']=unary_union([region(K2,9,0,1300),region(9,KEND+1,0,1000)])
def counted(poly,h):
    lim=SP([tuple(at(k,UIN0-5000)) for k in np.linspace(K2-1,KEND+1,40)]+[tuple(at(k,np.interp(k,kk,uin)+(ZE-(Z2+h))/(ZE-ZW)*np.interp(k,kk,uout-uin))) for k in np.linspace(KEND+1,K2-1,40)])
    return poly.intersection(lim).area/1e6
print('会議室 天井2.1m以上 %.1f m2 / 全体 %.1f'%(counted(R2['会議室'],2100),R2['会議室'].area/1e6))
print('休憩室+ぐったり 2.1m以上 %.1f, 1.4m以上 %.1f, 全体 %.1f'%(counted(unary_union([R2['休憩室'],R2['ぐったり休憩']]),2100),counted(unary_union([R2['休憩室'],R2['ぐったり休憩']]),1400),(R2['休憩室'].area+R2['ぐったり休憩'].area)/1e6))
for n,p in list(R1.items())+list(R2.items()): print('%s %.0f m2'%(n,p.area/1e6))
# ---------- model ----------
model=r3.File3dm(); model.Settings.ModelUnitSystem=r3.UnitSystem.Millimeters
LY={}
def layer(name,rgb):
    L=r3.Layer(); L.Name=name; L.Color=(rgb[0],rgb[1],rgb[2],255); LY[name]=model.Layers.Add(L)
for n,c in [('00_敷地',(80,80,80)),('01_公園・駐車場',(90,150,80)),('10_本館_屋根',(200,190,170)),('11_本館_骨組み',(140,100,60)),
            ('20_西館_屋根',(150,140,120)),('21_西館_外壁',(215,200,175)),('22_西館_骨組み',(140,100,60)),('23_西館_2階床',(170,160,150)),('24_西館_間仕切り',(235,230,220)),('25_西館_階段',(120,110,100)),('27_西館_室内窓',(170,210,230)),
            ('31_1F_遊戯室',(205,224,242)),('32_1F_キッチン',(190,215,238)),('33_1F_土間',(250,233,184)),('34_1F_食べる土間',(245,222,160)),('35_機械室（本館の北）',(190,190,190)),('26_室外機置場（屋根の上）',(150,150,150)),('36_1F_階段',(120,110,100)),
            ('41_2F_ホール',(240,240,240)),('42_2F_便所・湯沸',(210,210,210)),('43_2F_会議室',(220,205,240)),('44_2F_休憩室',(232,221,243)),('45_2F_ぐったり休憩',(245,225,235))]:
    layer(n,c)
def at_(n): a=r3.ObjectAttributes(); a.LayerIndex=LY[n]; return a
class MB:
    def __init__(s): s.m=r3.Mesh(); s.n=0
    def f(s,q):
        _q=np.array(q,float)
        if np.linalg.norm(np.cross(_q[1]-_q[0],_q[-1]-_q[0]))<1.0 and (len(q)==3 or np.linalg.norm(np.cross(_q[2]-_q[1],_q[3]-_q[1]))<1.0): return
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
kint=[k for k in kint if k<=11.01]                             # 12 は飛ばして、南の壁に妻の架構
WCOLS=[]
FR=[(k,)+tuple(segs[k]) for k in kint]+[(KE,)+segx(KE)]
for k,a,b,L in FR:
    rad=b-a; endf=(k==KE)
    din,dout=200.0,L-200.0
    cols=[din,dout] if not endf else list(np.linspace(200,L-200,int(math.ceil((L-400)/3000))+1))
    def Pk(d,z): p=a+(b-a)*min(d,L)/L; return (p[0],p[1],z)
    u0=np.linalg.norm(a-np.array(G['CENTER']))-bm['R']-12000; ui=np.interp(k,kk,uin)
    off=u0-ui                                                  # 妻の架構は角の丸みの分だけ内側から始まる
    zr=lambda d: zroof(k,d+off,np.interp(k,kk,uout-uin))
    for d in cols: wf.col(Pk(d,0)[:2],0,zr(d),axis=rad); WCOLS.append(Pk(d,0)[:2])
    wf.box(Pk(0,zr(0)),Pk(L,zr(L)),360,700)                    # 屋根梁
    if k>=K2-0.01:
        wf.box(Pk(0,Z2),Pk(dout,Z2),360,HB2 if not endf else 450)  # 2 階の床梁（中の柱なしで外の柱まで）
# 桁（柱の列に沿って）：架構の間は直線、最後の区間（11 → 南の壁）は角の丸みに沿う
for (k0,a0,b0,L0),(k1,a1,b1,L1) in zip(FR,FR[1:]):
    last=(k1==KE)
    for side in ('in','out'):
        if not last:
            d0=200.0 if side=='in' else L0-200; d1=200.0 if side=='in' else L1-200
            p0=a0+(b0-a0)*d0/L0; p1=a1+(b1-a1)*d1/L1; pts=[p0,p1]
        else:
            ring=W.buffer(-200).exterior
            p0=a0+(b0-a0)*(200.0 if side=='in' else L0-200)/L0
            p1=a1+(b1-a1)*(200.0 if side=='in' else L1-200)/L1
            s0=ring.project(SPt(*p0)); s1=ring.project(SPt(*p1))
            if abs(s1-s0)>ring.length/2: s0,s1=(s0,s1+ring.length) if s1<s0 else (s0+ring.length,s1)
            pts=[np.array(ring.interpolate((s0+(s1-s0)*t)%ring.length).coords[0]) for t in np.linspace(0,1,12)]
        for q0,q1 in zip(pts,pts[1:]):
            wf.box((q0[0],q0[1],zat3(q0)-300),(q1[0],q1[1],zat3(q1)-300),200,400)
            if k0>=K2-0.01: wf.box((q0[0],q0[1],Z2-80),(q1[0],q1[1],Z2-80),200,400)
SCOLS=[]
wf.add('22_西館_骨組み')
# ---------- floors, partitions, stair ----------
lay1={'遊戯室':'31_1F_遊戯室','キッチン':'32_1F_キッチン','土間':'33_1F_土間','食べる土間':'34_1F_食べる土間','階段':'36_1F_階段'}
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
    return (Z2-HB2) if level==1 and ku(p)[0]>=K2 else zat3(p)-150
def walls_between(A,B,level,z0,mb):
    L=A.boundary.intersection(B.boundary)
    for ln in getattr(L,'geoms',[L]):
        if ln.is_empty or ln.length<300 or ln.geom_type not in ('LineString',): continue
        cs=list(ln.coords)
        for a,b in zip(cs,cs[1:]):
            za=zceil(a,level); zb=zceil(b,level)
            mb.f([(a[0],a[1],z0),(b[0],b[1],z0),(b[0],b[1],za),(a[0],a[1],zb if False else za)])
pw=MB()
pairs1=[('キッチン','遊戯室')]                    # 土間・食べる土間の側はカウンター（壁なし）
for a,b in pairs1: walls_between(R1[a].buffer(1),R1[b].buffer(1),1,0,pw)
pairs2=[('会議室','休憩室'),('会議室','ぐったり休憩'),('便所・湯沸','ホール2'),('便所・湯沸','休憩室'),('会議室','ホール2'),('便所・湯沸','吹抜'),('休憩室','吹抜')]
for a,b in pairs2: walls_between(R2[a].buffer(1),R2[b].buffer(1),2,Z2,pw)
# 2 階の北の面 (k=8)：会議室は腰壁 + 室内窓、ぐったりは壁
gl=MB()
def kface(d0,d1,z0,z1,mb,n=6):
    ds=np.linspace(d0,d1,n+1)
    for a,b in zip(ds,ds[1:]):
        pa=P(K2,a,0); pb=P(K2,b,0)
        za=zroof(K2,a,Lk(K2))-80 if z1 is None else z1; zb=zroof(K2,b,Lk(K2))-80 if z1 is None else z1
        mb.f([(pa[0],pa[1],z0),(pb[0],pb[1],z0),(pb[0],pb[1],zb),(pa[0],pa[1],za)])
_dl=DLIM(Lk(K2))
kface(4100,_dl,Z2,Z2+850,pw)               # 腰壁 h=850（座ると子どもが見える／子どもからは見上げにくい）
kface(4100,_dl,Z2+850,None,gl)             # 室内窓（天井 2.1 m 以上の部分）
kface(_dl,Lk(K2),Z2,None,pw)               # 低い部分は壁
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
# 本館の北の三角形の空き地に、おむすび三角の機械室（B：本館側 2.0 m、道路・隣家側を均等、角の丸み 1.3 m、30 m2）
from scipy.optimize import brentq
_N0=np.array([0.0,0.0]); _Wv=np.array([-25830,-20540.0]); _Ev=np.array([34860,-43830.0])
_a=np.array(world(bm,thf(0),-40000,0)[:2]); _b=np.array(world(bm,thf(0),60000,0)[:2])
def _isect(p,d,q,e):
    A=np.array([d,-e]).T; t=np.linalg.solve(A,q-p); return p+d*t[0]
_dR=(_N0-_Wv)/np.linalg.norm(_N0-_Wv); _dN=(_Ev-_N0)/np.linalg.norm(_Ev-_N0); _dM=(_b-_a)/np.linalg.norm(_b-_a)
_tri=SP([tuple(_isect(_Wv,_dR,_a,_dM)),tuple(_N0),tuple(_isect(_N0,_dN,_a,_dM))]); _cen=np.array(_tri.centroid.coords[0])
def _inw(p,d):
    n=np.array([-d[1],d[0]]); return n if np.dot(_cen-p,n)>0 else -n
def onigiri(mr,mn,mm,r):
    Ls=[(_N0+_inw(_N0,_dR)*mr,_dR),(_N0+_inw(_N0,_dN)*mn,_dN),(_a+_inw(_a,_dM)*mm,_dM)]
    v=[_isect(*Ls[0],*Ls[1]),_isect(*Ls[1],*Ls[2]),_isect(*Ls[2],*Ls[0])]
    return SP([tuple(x) for x in v]).buffer(-r,resolution=32).buffer(r,resolution=32)
_g=brentq(lambda g: onigiri(g,g,2000.0,1300.0).area-30e6,300,3500)
MECH=onigiri(_g,_g,2000.0,1300.0)
HM=3200.0; HP=600.0
dr=MB(); cs=list(MECH.exterior.coords)
for p0,p1 in zip(cs,cs[1:]): dr.f([(p0[0],p0[1],0),(p1[0],p1[1],0),(p1[0],p1[1],HM),(p0[0],p0[1],HM)])
dr.flat(MECH,HM)
inner=MECH.buffer(-150)
ci=list(inner.exterior.coords)
for p0,p1 in zip(cs,cs[1:]): dr.f([(p0[0],p0[1],HM),(p1[0],p1[1],HM),(p1[0],p1[1],HM+HP),(p0[0],p0[1],HM+HP)])   # 立ち上がり（室外機を隠す）
for p0,p1 in zip(ci,ci[1:]): dr.f([(p1[0],p1[1],HM),(p0[0],p0[1],HM),(p0[0],p0[1],HM+HP),(p1[0],p1[1],HM+HP)])
dr.flat(MECH.difference(inner),HM+HP)
dr.add('35_機械室（本館の北）')
# 室外機：屋根の上（3 台、立ち上がりの内側）
yd=MB(); c=np.array(MECH.centroid.coords[0])
for i in (-1,0,1):
    p=c+_dR*i*1100
    q=[p-_dR*450-_inw(_N0,_dR)*175,p+_dR*450-_inw(_N0,_dR)*175,p+_dR*450+_inw(_N0,_dR)*175,p-_dR*450+_inw(_N0,_dR)*175]
    yd.flat(SP([tuple(x) for x in q]),HM+10)
    for k in range(4):
        a0,a1=q[k],q[(k+1)%4]; yd.f([(a0[0],a0[1],HM),(a1[0],a1[1],HM),(a1[0],a1[1],HM+700),(a0[0],a0[1],HM+700)])
    yd.flat(SP([tuple(x) for x in q]),HM+700)
yd.add('26_室外機置場（屋根の上）')
print('mech %.1f m2, gaps main %.2f road %.2f neighbour %.2f'%(MECH.area/1e6,MECH.distance(band(bm,0,19,-3000,12200))/1000,SL([(-25830,-20540),(0,0)]).distance(MECH)/1000,SL([(0,0),(34860,-43830)]).distance(MECH)/1000))
model.Write('/home/claude/plans/rhino/sodachiya_west_case3.3dm',8)
print('written')
