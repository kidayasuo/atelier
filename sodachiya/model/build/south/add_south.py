"""本館の南端まわり（2026-10-19 決定、受け取り土間 B 案）を sodachiya_exact.3dm に追加する。
入力: IN（既存の 3dm）  出力: OUT"""
import sys, math, numpy as np, rhino3dm as r
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
IN=sys.argv[1]; OUT=sys.argv[2]
C=np.array([194645.51027008,-41347.80985094])
TH=np.array([2.98003,2.99466,3.0093,3.02393,3.03857,3.0532,3.06783,3.08247,3.0971,3.11174,3.12637,3.14101,3.15564,3.17027,3.18491,3.19954,3.21418,3.22881,3.24344,3.25808])
TH[-1]=np.radians(-173.3258)+2*np.pi; th19=TH[19]
def P(rr,a): return C+rr*np.array([np.cos(a),np.sin(a)])
t=np.array([-np.sin(th19),np.cos(th19)])
if (P(200000,th19)-P(200000,TH[18]))@t<0: t=-t
RE,RC,RK,RW,RO=190000,193000,203400,205000,205200
def ztop(rr): return 3000+(rr-193000)/12.0+167.0      # 屋根の上面（梁天端 3.0→4.0 m + 167）
site=Polygon([(0,0),(34860,-43830),(-14440,-83040),(-21910,-73650),(-25830,-20540)])
park=Polygon([(-14440,-83040),(-21911,-73649),(-12519,-66180),(-5048,-75570)])
E_=np.array([34860,-43830.]); S_=np.array([-14440,-83040.]); pn=np.array([-12519,-66180.]); pe=np.array([-5048,-75570.])
m=r.File3dm.Read(IN)
def layer(name,rgb):
    for i,l in enumerate(m.Layers):
        if l.FullPath==name: return i
    L=r.Layer(); L.Name=name; L.Color=(rgb[0],rgb[1],rgb[2],255); return m.Layers.Add(L)
def hexc(h): return tuple(int(h[i:i+2],16) for i in (0,2,4))
def attr(li): a=r.ObjectAttributes(); a.LayerIndex=li; return a
def mesh_prism(bot,top):
    """bot/top: 同じ数の 3D 点列（閉じていない多角形）。側面と上下面（earcut で三角分割、凹形も可）"""
    import mapbox_earcut as _ec
    M=r.Mesh(); n=len(bot)
    for p in list(bot)+list(top): M.Vertices.Add(float(p[0]),float(p[1]),float(p[2]))
    xy=np.array([(float(p[0]),float(p[1])) for p in bot],dtype=np.float64)
    s=0.5*np.sum(xy[:,0]*np.roll(xy[:,1],-1)-np.roll(xy[:,0],-1)*xy[:,1])
    tri=np.array(_ec.triangulate_float64(xy,np.array([n],dtype=np.uint32))).reshape(-1,3)
    for a,b,c in tri:
        a,b,c=int(a),int(b),int(c)
        if s<0: b,c=c,b
        M.Faces.AddFace(a,c,b); M.Faces.AddFace(n+a,n+b,n+c)
    for i in range(n):
        j=(i+1)%n
        if s>0: M.Faces.AddFace(i,j,n+j,n+i)
        else: M.Faces.AddFace(j,i,n+i,n+j)
    M.Normals.ComputeNormals(); M.Compact(); return M
def slab(poly2d,z0,z1,li):
    pts=list(poly2d.exterior.coords)[:-1]
    m.Objects.AddMesh(mesh_prism([(x,y,z0) for x,y in pts],[(x,y,z1) for x,y in pts]),attr(li))
def sloped(poly2d,thick,li,zf):
    pts=list(poly2d.exterior.coords)[:-1]
    m.Objects.AddMesh(mesh_prism([(x,y,zf(x,y)-thick) for x,y in pts],[(x,y,zf(x,y)) for x,y in pts]),attr(li))
def quad(r0,r1,a0,a1,n=12):
    a=np.linspace(a0,a1,n); return Polygon([P(r0,x) for x in a]+[P(r1,x) for x in a[::-1]])
def wall_along(pts2d,z0f,z1f,thick,li):
    """2D の線に沿う厚さ thick の壁（高さは位置の関数でもよい）"""
    for p0,p1 in zip(pts2d,pts2d[1:]):
        d=np.array(p1)-np.array(p0); d/=np.linalg.norm(d); nrm=np.array([-d[1],d[0]])*thick/2
        q=[np.array(p0)-nrm,np.array(p1)-nrm,np.array(p1)+nrm,np.array(p0)+nrm]
        z0=[z0f(*x) for x in q]; z1=[z1f(*x) for x in q]
        m.Objects.AddMesh(mesh_prism([(x[0],x[1],a) for x,a in zip(q,z0)],[(x[0],x[1],b) for x,b in zip(q,z1)]),attr(li))
# 平面上の r（中心からの距離）
def rr_of(x,y): return float(np.hypot(x-C[0],y-C[1]))
K0=13
# ---------- 室（床の塗り、z=10） ----------
L_doma=layer('52_1F_受け取り土間',hexc('E3D3B5')); L_01=layer('53_1F_0・1歳',hexc('E6EFC2')); L_2=layer('54_1F_2歳',hexc('C5DE9A'))
L_wet=layer('55_1F_水まわり（沐浴・2歳トイレ）',hexc('D5EBEE')); L_strip=layer('56_1F_西吹き抜け（窓辺）',hexc('F4EBDD'))
doma=quad(RK,RO,TH[17],th19)
rooms=quad(RC,RO,TH[K0],th19,40).difference(doma)
lo,hi=TH[K0],th19
for _ in range(50):
    mid=(lo+hi)/2; a=rooms.intersection(quad(RC,RO,mid,th19,40)).area/1e6
    lo,hi=(mid,hi) if a>120 else (lo,mid)
thp=TH[15]                                   # 2026-10-21：0・1 歳と 2 歳の境は架構 15（別チャットの平面図に合わせる）
r01=rooms.intersection(quad(RC,RO,thp,th19,40)); r2=rooms.difference(quad(RC,RO,thp,th19,40))
slab(doma,-300,-290,L_doma)
for g,li in ((r01.intersection(quad(RC,RK,TH[K0],th19,40)),L_01),(r2.intersection(quad(RC,RK,TH[K0],th19,40)),L_2),(quad(RK,RO,TH[K0],TH[17],40),L_strip)):
    for gg in getattr(g,'geoms',[g]):
        if gg.geom_type=='Polygon' and gg.area>0.5e6: slab(gg,0,10,li)
dth=lambda mm: mm/RK
# (10-21 削除：しつらえは add_shitsurae.py) wet=[quad(RK-3000,RK,thp-dth(2700),thp),quad(RK-3000,RK,thp,thp+dth(2200))]
# (10-21 削除：しつらえは add_shitsurae.py) for g in wet: slab(g,10,20,L_wet)
# 間仕切り（0・1 歳｜2 歳）と、框（低い腰壁 h=600、木戸のところは框だけ）
# (10-21 削除：しつらえは add_shitsurae.py) L_part=layer('57_1F_間仕切り・框',(120,90,60))
# (10-21 削除：しつらえは add_shitsurae.py) wall_along([P(RC,thp),P(RK-3000,thp)],lambda x,y:0,lambda x,y:2400,100,L_part)
# (10-21 削除：しつらえは add_shitsurae.py) kam=[P(RK,a) for a in np.linspace(TH[17],th19,6)]
# (10-21 削除：しつらえは add_shitsurae.py) wall_along(kam,lambda x,y:-300,lambda x,y:600,120,L_part)                       # 東の框＋腰壁（0・1 歳の手渡し）
# (10-21 削除：しつらえは add_shitsurae.py) n0,n1=P(RK,TH[17]),P(RO,TH[17])
# (10-21 削除：しつらえは add_shitsurae.py) wall_along([n0,n0+(n1-n0)*0.25],lambda x,y:-300,lambda x,y:600,120,L_part)
# (10-21 削除：しつらえは add_shitsurae.py) wall_along([n0+(n1-n0)*0.85,n1],lambda x,y:-300,lambda x,y:600,120,L_part)
# (10-21 削除：しつらえは add_shitsurae.py) wall_along([n0+(n1-n0)*0.25,n0+(n1-n0)*0.85],lambda x,y:-300,lambda x,y:0,600,L_part)   # 木戸の下の框と式台
# ---------- 越屋根「浮いた蓋」（2026-10-19 改）----------
# 立ち上がり 150（西吹き抜けの両側の壁の延長）＋すき間 150（両側に連続した風の出口、冬は閉じる）
# ＋屋根と平行（1/12）な透明ガラスの蓋 t=60、出 350（東西南北）＋蓋の上に南北に通る木のルーバー（幅 120、間隔 104、東へ 30°）
# （10-24 ユーザー：透明ガラスの上にルーバー。東から 30° より低い朝の日はルーバーのあいだを抜けて西吹き抜けに直接差す
#   ＝京都で夏至 約7:30・春分 約8:30・冬至 約9:30 まで。それより高い日は板の上面で受けて板のあいだで跳ね返し、拡散光にして落とす。
#   板は両面とも白の艶消し：上面は日を受けて跳ね返す面、下面は室内から見上げて光る面）
L_mon=layer('50_本館_越屋根_立ち上がり',(150,120,190)); L_lid=layer('50a_本館_越屋根_ガラスの蓋',(127,179,213))
L_led=layer('50b_越屋根_LED',(255,211,77)); L_lv=layer('50c_越屋根_木のルーバー（白の艶消し）',(236,232,222))
CURB=150; GAP=150; GT=60; OVH=350
arc_e=[P(RK,a) for a in np.linspace(TH[0],th19,60)]; arc_w=[P(RW,a) for a in np.linspace(TH[0],th19,60)]
for arc in (arc_e,arc_w):
    wall_along(arc,lambda x,y:ztop(rr_of(x,y))-250,lambda x,y:ztop(rr_of(x,y))+CURB,120,L_mon)
L_end=layer('50e_本館_越屋根_妻（壁と同じ材で閉じる）',(215,200,175))
for a_ in (TH[0],th19):                       # 南北の端は屋根から蓋の下まで壁で閉じる
    wall_along([P(RK-60,a_),P(RW+60,a_)],lambda x,y:ztop(rr_of(x,y))-250,lambda x,y:ztop(rr_of(x,y))+CURB+GAP,120,L_end)
aN=TH[0]-640/RW; aS=th19+OVH/RW           # 北は屋根のけらば（北の妻壁の外面から 0.3）にそろえる（10-24）
def zlid(x,y): return ztop(rr_of(x,y))+CURB+GAP+GT
lid=quad(RK-OVH,RW+OVH,aN,aS,60)
# 西の出 350（10-24、ユーザー）：外壁の外面（v −0.35）から 350 出して、すき間の換気口（ガラリ）を横からの雨から守る。
# 西館とのすき間（u 21〜51）は「すき間の蓋」が西館まで覆うので、そこは延ばさない。
aG0=th19-51000/RW; aG1=th19-21000/RW
lid=lid.union(quad(RW+OVH-1,RW+OVH+350,aN,aG0,30)).union(quad(RW+OVH-1,RW+OVH+350,aG1,aS,30)).buffer(0)
sloped(lid,GT,L_lid,zlid)
led=[P(RK-OVH+60,a) for a in np.linspace(aN,aS,60)]
wall_along(led,lambda x,y:zlid(x,y)-GT-40,lambda x,y:zlid(x,y)-GT,40,L_led)
import math
W_=120.0; PITCH=104.0; ANG=math.radians(30)
rw=RW+OVH-20
while rw-W_*math.cos(ANG)>RK-OVH:
    re_=rw-W_*math.cos(ANG)
    def zs(x,y,rw=rw): return zlid(x,y)+10+(rw-rr_of(x,y))*math.tan(ANG)
    sloped(quad(re_,rw,aN,aS,60),18,L_lv,zs)
    rw-=PITCH
# ---------- 南の軒（屋根面の延長、東 1.8 m → 西 4.2 m） ----------
# (10-21) 南の軒は 10_本館_屋根 へ（下で作る）
def eave_pt(rr): return P(rr,th19)+t*(1800+(4200-1800)*(rr-RE)/(RO-RE))
rs=np.linspace(RE,RO,30); eave=Polygon([P(x,th19) for x in rs]+[eave_pt(x) for x in rs[::-1]])
L_eave=layer('10_本館_屋根',(200,190,170))          # 10-21：南の軒は同じ屋根の一部（同じレイヤ・同じ材）
_pts=list(eave.exterior.coords)[:-1]
_M=r.Mesh()
for x,y in _pts: _M.Vertices.Add(float(x),float(y),float(ztop(rr_of(x,y))))
import mapbox_earcut as _ec
_xy=np.array(_pts,dtype=np.float64)
for a_,b_,c_ in np.array(_ec.triangulate_float64(_xy,np.array([len(_pts)],dtype=np.uint32))).reshape(-1,3): _M.Faces.AddFace(int(a_),int(b_),int(c_))
_M.Normals.ComputeNormals(); _M.Compact(); m.Objects.AddMesh(_M,attr(L_eave))
# ---------- 外構 ----------
L_f=layer('60_外構_柵（一本の線の延長）',(192,57,43)); L_se=layer('61_外構_南の縁側',hexc('F4EBDD'))
L_g=layer('62_外構_みなみのさんかく（乳児の園庭）',hexc('EEF4D2')); L_ev=layer('63_外構_避難の帯',(58,120,194)); L_po=layer('64_外構_ポーチ',hexc('F7D3B0'))
L_rp=layer('65_縁側の端のスロープ',(201,167,122)); L_ent=layer('66_入口（扉・背くらべの柱）',(62,122,46))
kp=P(RK,th19); ray=LineString([kp,kp+t*20000])
hits=[ray.intersection(LineString([pn,pe])),ray.intersection(LineString([E_,S_]))]
hits=[np.array(h.coords[0]) for h in hits if not h.is_empty]; fh=min(hits,key=lambda h:np.linalg.norm(h-kp))
fh_in=fh-t*300
EO_S=2450   # 柵は南の外縁側（u −2.42 まで）の外の縁で止める（10-24、外縁側と重なっていた）
wall_along([kp+t*EO_S,fh_in],lambda x,y:-300,lambda x,y:900,60,L_f)
bldg=quad(RE,RO,TH[K0],th19,40)
south=Polygon([P(RE,th19),P(RO,th19),P(RO,th19)+t*30000,P(RE,th19)+t*30000]).intersection(site).difference(park).difference(bldg)
west=Polygon([kp,fh,fh+np.array([-30000,-5000]),kp+np.array([-30000,10000])])
garden=south.difference(west); garden=max(getattr(garden,'geoms',[garden]),key=lambda g:g.area)
porch=south.intersection(west).difference(Polygon([P(RO,th19),pn,pn+np.array([-8000,3000]),P(RO,th19)+np.array([-8000,6000])]))
porch=max(getattr(porch,'geoms',[porch]),key=lambda g:g.area)
r0=194500; W1=2400
# 南の縁側（10-21 改 2）：ぽってり。外の縁はすべて外へふくらむ曲線（楕円の 1/4、変曲点なし）で、細い側も太る。
# 柵の側の外の角は半径 0.6 m で丸める（壁に接する側の角はそのまま）
RR=600.0
_A=RK-r0; _el=[]
for th_ in np.linspace(0,math.pi/2,80):
    s_=RK-_A*math.cos(th_); d_=W1*math.sin(th_)
    _el.append(P(s_,th19)+t*d_)
_g=Polygon([P(x,th19) for x in np.linspace(r0,RK,40)]+[P(RK,th19)+t*W1]+_el[::-1]).buffer(0)
_rounded=_g.buffer(-RR,resolution=24).buffer(RR,resolution=24)
_cq=Polygon([P(RK-2.5*RR,th19)+t*(W1-2.5*RR),P(RK+50,th19)+t*(W1-2.5*RR),P(RK+50,th19)+t*(W1+50),P(RK-2.5*RR,th19)+t*(W1+50)])
seng=unary_union([_g.difference(_cq),_rounded.intersection(_cq)]).buffer(1).buffer(-1)
seng=max(getattr(seng,'geoms',[seng]),key=lambda g:g.area)
evac=LineString([E_,S_]).buffer(1500,cap_style=2).intersection(garden)
for g,li,z in ((garden.difference(seng),L_g,-300),(porch,L_po,-300)):
    for gg in getattr(g,'geoms',[g]):
        if gg.geom_type=='Polygon': slab(gg.simplify(5),z-10,z,li)
for gg in getattr(evac,'geoms',[evac]):
    if gg.geom_type=='Polygon': slab(gg.simplify(5),-300,-295,L_ev)
slab(seng,-300,-150,L_se)                     # 南の縁側は外（土足）：FL −150
# 外縁側の最後のスパンをスロープに（FL −150 → GL −300、南へ下がる）
ramp=quad(RE,191500,TH[18],th19,8)
def zr(x,y):
    a=np.arctan2(y-C[1],x-C[0]); a=a if a>0 else a+2*np.pi
    return -150-150*(a-TH[18])/(th19-TH[18])
sloped(ramp,60,L_rp,zr)
# 入口：扉（受け取り土間の南の妻）と背くらべの柱（北山杉 φ200、h=3.0 m）
d0,d1=P(RK+200,th19),P(RO-300,th19)
wall_along([d0,d1],lambda x,y:-300,lambda x,y:1950,50,L_ent)
post=d1+t*350+(d1-d0)/np.linalg.norm(d1-d0)*350
circ=r.Circle(r.Point3d(float(post[0]),float(post[1]),-300.0),100.0).ToNurbsCurve()
m.Objects.AddExtrusion(r.Extrusion.Create(circ,3300.0,True),attr(L_ent))
m.Write(OUT,8)
print('0-1',round(r01.area/1e6,1),'2',round(r2.area/1e6,1),'doma',round(doma.area/1e6,1),'garden',round(garden.difference(seng).area/1e6,1),'porch',round(porch.area/1e6,1),'fence',round(np.linalg.norm(fh-kp)/1000,2))
