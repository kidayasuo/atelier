"""西館の越屋根（本館と同じ「浮いた蓋」＋木のルーバー）、本館と西館のすき間の蓋、
本館の西吹き抜けのシーリングファン（1 スパン 1 台）を追加する。add_south.py の後に実行。
python3 -I add_monitor_west.py IN OUT"""
import sys, math, numpy as np, rhino3dm as r
exec(open('/tmp/claude-0/t/south/add_south.py').read().split("m=r.File3dm.Read(IN)")[0].replace("IN=sys.argv[1]; OUT=sys.argv[2]",""))
IN,OUT=sys.argv[1],sys.argv[2]
m=r.File3dm.Read(IN)
exec(open('/tmp/claude-0/t/south/add_south.py').read().split("m=r.File3dm.Read(IN)")[1].split("K0=13")[0])
CURB=150; GAP=150; GT=60; OVH=350; W_=120.0; PITCH=104.0; ANG=math.radians(30)
VOID=1600.0          # 西館の換気の吹抜（東の縁から d 0–1.6 m）＝越屋根の幅（10-25 ユーザー：1.0 → 1.6、本館とそろえる。東の帯の吹き抜けも 1.6）
# --- 西館の屋根メッシュから東の縁（棟）を取り出す ---
Lyr={i:l.FullPath for i,l in enumerate(m.Layers)}
roofm=[o.Geometry for o in m.Objects if Lyr[o.Attributes.LayerIndex]=='20_西館_屋根'][0]
V=np.array([(roofm.Vertices[i].X,roofm.Vertices[i].Y,roofm.Vertices[i].Z) for i in range(len(roofm.Vertices))])
RT=109.0             # 10-27夜（ユーザー、本館係の項 20261027-1937）：屋根の上面は梁の上端（この面）の約 109 上（前は 420）。越屋根の物はみなその分上げる
V[:,2]+=RT
ZTOP=V[:,2].max()
E=V[V[:,2]>ZTOP-5][:,:2]
E=np.unique(E.round(0),axis=0)
ang=np.arctan2(E[:,1]-C[1],E[:,0]-C[0]); ang=np.where(ang<0,ang+2*np.pi,ang)
E=E[np.argsort(ang)]
# 外側（西）に向かう単位ベクトル u（架構の放射方向）。蓋は完全に水平（2026-10-19 改）
from scipy.spatial import cKDTree
tree=cKDTree(V[:,:2])
def zroof_at(p):
    d,i=tree.query(p,k=6); w=1/(d+1); return float((V[i,2]*w).sum()/w.sum())
edge=[(p,(p-C)/np.linalg.norm(p-C)) for p in E]
sel=[edge[0]]
for e in edge[1:]:
    if np.linalg.norm(e[0]-sel[-1][0])>600: sel.append(e)
if np.linalg.norm(edge[-1][0]-sel[-1][0])>50: sel.append(edge[-1])
edge=sel
# 両端を 350 延ばす（棟の接線方向）
def ext(i0,i1):
    p0,u0=edge[i0]; p1,_=edge[i1]; t_=(p0-p1)/np.linalg.norm(p0-p1); return (p0+t_*350.0,u0)
edge=[ext(0,1)]+edge+[ext(-1,-2)]
def Pw(i,d): p,u=edge[i]; return p+u*d
def zw(i,d): return zroof_at(Pw(i,d))          # 立ち上がりの足元（屋根面）
def strip_mesh(d0,d1,zf0,zf1,li):
    n=len(edge)
    for i in range(n-1):
        q=[(i,d0),(i+1,d0),(i+1,d1),(i,d1)]
        bot=[(*Pw(a,b),zf0(a,b)) for a,b in q]; top=[(*Pw(a,b),zf1(a,b)) for a,b in q]
        m.Objects.AddMesh(mesh_prism(bot,top),attr(li))
L_mon=layer('70_西館_越屋根_立ち上がり',(150,120,190)); L_lid=layer('70a_西館_越屋根_ガラスの蓋',(127,179,213))
L_led=layer('70b_西館_越屋根_LED',(255,211,77)); L_lv=layer('70c_西館_越屋根_木のルーバー（白の艶消し）',(236,232,222))
# 立ち上がり（東の縁 d=0 と d=VOID）
# 長手方向は水平、屋根の流れ方向は屋根の主な部分の勾配 S で一定（2026-10-19 改）
_out=V[V[:,2]<V[:,2].min()+20][:,:2]          # 屋根の西の縁（軒）
_ss=[]
for p,u in edge[1:-1]:
    rel=_out-p; along=rel@u; lat=np.abs(rel@np.array([-u[1],u[0]]))
    ok=lat<400
    if ok.any(): _ss.append((ZTOP-V[:,2].min())/along[ok].max())
S=float(np.median(_ss))                       # 屋根の主な部分の勾配（棟 8.15 → 軒 4.65 を各断面の奥行きで割った中央値）
ZC=ZTOP+CURB                                   # 立ち上がりの天端（東の縁）
ne=len(edge)
for d in (0.0,VOID):
    for i in range(1,ne-2):                     # 延長した端の区間には立ち上がりを付けない
        q=[(i,d-60),(i+1,d-60),(i+1,d+60),(i,d+60)]
        bot=[(*Pw(a,b),zw(a,b)-250-RT) for a,b in q]; top=[(*Pw(a,b),ZC-S*b) for a,b in q]
        m.Objects.AddMesh(mesh_prism(bot,top),attr(L_mon))
L_end=layer('70e_西館_越屋根_妻（壁と同じ材で閉じる）',(215,200,175))
for i in (1,ne-2):                              # 南北の端は屋根から蓋の下まで壁で閉じる
    for dd0,dd1 in zip(np.linspace(-60,VOID+60,6),np.linspace(-60,VOID+60,6)[1:]):
        p0,p1=Pw(i,dd0),Pw(i,dd1); t_=(Pw(i+1 if i==1 else i-1,0)-Pw(i,0)); t_=t_/np.linalg.norm(t_)*60
        q=[p0+t_/60,p1+t_/60,p1+2*t_,p0+2*t_]                # 10-28：外の面は外壁の外面の 1 内（同じ面にあると、外壁と足したとき厚さ0の膜が残った、監修の項 2346）                # 10-27夜：外の面を外壁の外面（棟の端＝妻の外面）にそろえ、内へ 120（前は端を中心に ±60 で、北の妻から 59 出て段に見えた）
        m.Objects.AddMesh(mesh_prism([(*x,zroof_at(x)-250-RT) for x in q],[(*x,ZC+GAP-S*float(np.dot(x-edge[i][0],edge[i][1]))) for x in q]),attr(L_end))
# 蓋（屋根と平行）
lidtop=lambda i,d: ZTOP+CURB+GAP+GT-S*d
# 棟（東の縁）は弧の中心 C のまわりの円（半径 R0、ずれ 2 mm 以内）で、蓋・LED・ルーバーの高さは d（棟からの距離）だけで決まる
# → 弧に沿う一本の帯（回転体）。前は棟の点ごと（約 0.6 m）の小さな角柱 40 個ずつで、Rhino 版で 882 個の押し出しになっていた
# （10-25 ソリッド係、ユーザー：越屋根の作り方を本館と同じように合理化）。端は前と同じく棟の両端から 350 延ばした所まで。
R0=float(np.median([np.linalg.norm(p-C) for p,u in edge[1:-1]]))
_ae=[math.atan2(p[1]-C[1],p[0]-C[0])%(2*math.pi) for p,u in edge]
A0,A1=_ae[0],_ae[-1]
def sector_mesh(r0,r1,zf0,zf1,li,a0=None,a1=None,n=80):
    """中心 C のまわりの帯（半径 r0〜r1、角度 a0〜a1）の閉じた板。下の面 zf0(r)・上の面 zf1(r)（r だけの関数）"""
    a0=A0 if a0 is None else a0; a1=A1 if a1 is None else a1
    A=np.linspace(a0,a1,n); M=r.Mesh()
    for a in A:
        for rr in (r0,r1):
            x,y=C+rr*np.array([math.cos(a),math.sin(a)])
            M.Vertices.Add(float(x),float(y),float(zf0(rr))); M.Vertices.Add(float(x),float(y),float(zf1(rr)))
    q=lambda i,j,t: 4*i+2*j+t
    F=[]
    for i in range(n-1):
        F+=[(q(i,0,1),q(i,1,1),q(i+1,1,1),q(i+1,0,1)),(q(i,0,0),q(i+1,0,0),q(i+1,1,0),q(i,1,0)),
            (q(i,0,0),q(i,0,1),q(i+1,0,1),q(i+1,0,0)),(q(i,1,0),q(i+1,1,0),q(i+1,1,1),q(i,1,1))]
    F+=[(q(0,0,0),q(0,1,0),q(0,1,1),q(0,0,1)),(q(n-1,0,0),q(n-1,0,1),q(n-1,1,1),q(n-1,1,0))]
    import trimesh as _tm
    V_=np.array([[M.Vertices[i].X,M.Vertices[i].Y,M.Vertices[i].Z] for i in range(len(M.Vertices))])
    T_=_tm.Trimesh(V_,[f[:3] for f in F]+[(f[0],f[2],f[3]) for f in F],process=False); _tm.repair.fix_normals(T_)
    for a_,b_,c_ in T_.faces: M.Faces.AddFace(int(a_),int(b_),int(c_))
    M.Normals.ComputeNormals(); M.Compact(); m.Objects.AddMesh(M,attr(li))
sector_mesh(R0-OVH,R0+VOID+OVH,lambda rr:lidtop(0,rr-R0)-GT,lambda rr:lidtop(0,rr-R0),L_lid)
sector_mesh(R0-OVH+20,R0-OVH+60,lambda rr:lidtop(0,rr-R0)-GT-40,lambda rr:lidtop(0,rr-R0)-GT,L_led)
# ルーバー（水平に対して 30°、東＝本館側が高い。両面白の艶消し、蓋は透明ガラス＝本館と同じ、10-24 ユーザー）
# 西日は高さによらず羽根に当たって入らない。東の朝日（高さ約7〜53°）は羽根のあいだを抜けて吹き抜けに直接差す。
dw=VOID+OVH-20
while dw-W_*math.cos(ANG)>-OVH:
    de=dw-W_*math.cos(ANG)
    zt=lambda i,d,dw=dw: lidtop(i,dw)+28+(dw-d)*math.tan(ANG)      # 羽根の下の縁を蓋の 10 上に（前は +10 で 8 食い込み、削る段で切られていた。本館と同じ、10-25）
    sector_mesh(R0+de,R0+dw,lambda rr,zt=zt:zt(0,rr-R0)-18,lambda rr,zt=zt:zt(0,rr-R0),L_lv)   # 弧に沿う一本の羽根（回転体）
    dw-=PITCH
# --- 本館と西館のすき間の蓋（本館の蓋を西館の壁まで延ばす） ---
L_gap=layer('50d_本館_すき間の蓋（西館まで）',(127,179,213))
def zlid_main(x,y): return ztop(rr_of(x,y))+CURB+GAP+GT
a_e=[math.atan2(p[1]-C[1],p[0]-C[0])%(2*math.pi) for p,u in edge[1:-1]]
r_e=[np.linalg.norm(p-C) for p,u in edge[1:-1]]
pts=[P(RW+OVH,a) for a in a_e]+[P(rr+20,a) for rr,a in zip(r_e,a_e)][::-1]
gp=Polygon(pts).buffer(0)
# 弧に沿う帯で、上の面が本館の蓋の面にちょうど沿うように（前は外形を earcut で三角に分けて、長い弦の所で面が盛り上がっていた、10-25）
_zl=lambda rr: ztop(rr)+CURB+GAP+GT
if gp.area>0: sector_mesh(RW+OVH,R0+20,lambda rr:_zl(rr)-GT,_zl,L_gap,a0=min(a_e),a1=max(a_e))
# --- シーリングファン：西吹き抜けの各スパン中央に 1 台（羽根 φ1100、羽根の高さ 2.8 m） ---
L_fan=layer('58_1F_西吹き抜け_シーリングファン',(90,90,90))
rf=(RK+RW)/2
for k in range(19):
    a=(TH[k]+TH[k+1])/2; c=P(rf,a)
    z0=ztop(rf)-650                      # 梁下あたりから吊る
    disc=r.Circle(r.Point3d(float(c[0]),float(c[1]),2800.0),550.0).ToNurbsCurve()
    m.Objects.AddExtrusion(r.Extrusion.Create(disc,40.0,True),attr(L_fan))
    rod=r.Circle(r.Point3d(float(c[0]),float(c[1]),2840.0),25.0).ToNurbsCurve()
    m.Objects.AddExtrusion(r.Extrusion.Create(rod,float(z0-2840.0),True),attr(L_fan))
m.Write(OUT,8)
print('west ridge pts',len(edge),'ZTOP',ZTOP,'gap area m2',round(gp.area/1e6,1),'S',round(S,4),'west curb h min/max',round(min(ZC-S*VOID-zw(i,VOID) for i in range(1,ne-1))),round(max(ZC-S*VOID-zw(i,VOID) for i in range(1,ne-1))))
