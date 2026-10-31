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
# 10-30（ユーザー 22:20、監修の項 20261030-1431 の追記）：西館の越屋根（立ち上がり・妻・ガラスの蓋・LED・木のルーバー）はやめた。
# 棟から屋根の面に沿う幅 1.6 m のガラスの帯と排気窓・雨よけのルーバー・LED は fix_details.py の西館の節で作る。ここでは本館と西館のすき間の蓋と
# 本館の西吹き抜けのシーリングファンだけ（棟の点 edge・半径 R0 はすき間の蓋が使う）。
S=0.0; ZC=ZTOP+CURB
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
# --- 本館と西館のすき間の蓋（本館の蓋を西館の壁まで延ばす） ---
# 10-31（本館係の項 20261031-1149、ユーザー）：すき間の蓋のガラスは型板ガラス（光の筋・棟の帯と同じ材＝20t）、上に本館の越屋根と同じルーバー
L_gap=layer('20t_西館_光の筋（乳白ガラス、架構の線）',(225,236,242))
def zlid_main(x,y): return ztop(rr_of(x,y))+CURB+GAP+GT
a_e=[math.atan2(p[1]-C[1],p[0]-C[0])%(2*math.pi) for p,u in edge[1:-1]]
r_e=[np.linalg.norm(p-C) for p,u in edge[1:-1]]
pts=[P(RW+OVH,a) for a in a_e]+[P(rr+20,a) for rr,a in zip(r_e,a_e)][::-1]
gp=Polygon(pts).buffer(0)
# 弧に沿う帯で、上の面が本館の蓋の面にちょうど沿うように（前は外形を earcut で三角に分けて、長い弦の所で面が盛り上がっていた、10-25）
_zl=lambda rr: ztop(rr)+CURB+GAP+GT
if gp.area>0: sector_mesh(RW+OVH,R0+20,lambda rr:_zl(rr)-GT,_zl,L_gap,a0=min(a_e),a1=max(a_e))
# ルーバー：本館の越屋根の羽根（add_south.py：幅 120・ピッチ 104・水平に 30° で東が高い・厚さ 18、羽根の下の縁は蓋の上 10）の並びを、
#   同じ高さの式（蓋の上面 ztop(r)＋CURB＋GAP＋GT）・同じピッチのまま西へ続けて、すき間の蓋の上に（本館の越屋根 → すき間の蓋 → 西館の棟の帯の向きとピッチがそろう）
L_glv=layer('30_西館_棟のガラスの帯_日よけのルーバー（白の艶消し）',(236,232,222))
_rw=RW+OVH-20+PITCH; _nlv=0
while _rw<=R0+20-1.0:
    _re=_rw-W_*math.cos(ANG)
    if _re>=RW+OVH-21.0:
        sector_mesh(_re,_rw,lambda rr,rw=_rw:_zl(rr)+10+(rw-rr)*math.tan(ANG),lambda rr,rw=_rw:_zl(rr)+28+(rw-rr)*math.tan(ANG),L_glv,a0=min(a_e),a1=max(a_e)); _nlv+=1
    _rw+=PITCH
print('gap lid louvers',_nlv)
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
print('west ridge pts',len(edge),'ZTOP',ZTOP,'gap area m2',round(gp.area/1e6,1),'（西館の越屋根はやめた、10-30）')
