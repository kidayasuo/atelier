"""西館の越屋根（本館と同じ「浮いた蓋」＋木のルーバー）、本館と西館のすき間の蓋、
本館の西吹き抜けのシーリングファン（1 スパン 1 台）を追加する。add_south.py の後に実行。
python3 -I add_monitor_west.py IN OUT"""
import sys, math, numpy as np, rhino3dm as r
exec(open('/tmp/claude-0/t/south/add_south.py').read().split("m=r.File3dm.Read(IN)")[0].replace("IN=sys.argv[1]; OUT=sys.argv[2]",""))
IN,OUT=sys.argv[1],sys.argv[2]
m=r.File3dm.Read(IN)
exec(open('/tmp/claude-0/t/south/add_south.py').read().split("m=r.File3dm.Read(IN)")[1].split("K0=13")[0])
CURB=150; GAP=150; GT=60; OVH=350; W_=120.0; PITCH=104.0; ANG=math.radians(30)
VOID=1000.0          # 西館の換気の吹抜（東の縁から d 0–1.0 m）＝越屋根の幅
# --- 西館の屋根メッシュから東の縁（棟）を取り出す ---
Lyr={i:l.FullPath for i,l in enumerate(m.Layers)}
roofm=[o.Geometry for o in m.Objects if Lyr[o.Attributes.LayerIndex]=='20_西館_屋根'][0]
V=np.array([(roofm.Vertices[i].X,roofm.Vertices[i].Y,roofm.Vertices[i].Z) for i in range(len(roofm.Vertices))])
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
L_led=layer('70b_西館_越屋根_LED',(255,211,77)); L_lv=layer('70c_西館_越屋根_木のルーバー',(138,106,58))
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
        bot=[(*Pw(a,b),zw(a,b)-250) for a,b in q]; top=[(*Pw(a,b),ZC-S*b) for a,b in q]
        m.Objects.AddMesh(mesh_prism(bot,top),attr(L_mon))
L_end=layer('70e_西館_越屋根_妻（壁と同じ材で閉じる）',(215,200,175))
for i in (1,ne-2):                              # 南北の端は屋根から蓋の下まで壁で閉じる
    for dd0,dd1 in zip(np.linspace(-60,VOID+60,6),np.linspace(-60,VOID+60,6)[1:]):
        p0,p1=Pw(i,dd0),Pw(i,dd1); t_=(Pw(i+1 if i==1 else i-1,0)-Pw(i,0)); t_=t_/np.linalg.norm(t_)*60
        q=[p0-t_,p1-t_,p1+t_,p0+t_]
        m.Objects.AddMesh(mesh_prism([(*x,zroof_at(x)-250) for x in q],[(*x,ZC+GAP-S*float(np.dot(x-edge[i][0],edge[i][1]))) for x in q]),attr(L_end))
# 蓋（屋根と平行）
lidtop=lambda i,d: ZTOP+CURB+GAP+GT-S*d
strip_mesh(-OVH,VOID+OVH,lambda i,d:lidtop(i,d)-GT,lidtop,L_lid)
strip_mesh(-OVH+20,-OVH+60,lambda i,d:lidtop(i,d)-GT-40,lambda i,d:lidtop(i,d)-GT,L_led)
# ルーバー（水平に対して 30°、東＝本館側が高い）
dw=VOID+OVH-20
while dw-W_*math.cos(ANG)>-OVH:
    de=dw-W_*math.cos(ANG)
    zt=lambda i,d,dw=dw: lidtop(i,dw)+10+(dw-d)*math.tan(ANG)
    strip_mesh(de,dw,lambda i,d,zt=zt:zt(i,d)-18,zt,L_lv)
    dw-=PITCH
# --- 本館と西館のすき間の蓋（本館の蓋を西館の壁まで延ばす） ---
L_gap=layer('50d_本館_すき間の蓋（西館まで）',(127,179,213))
def zlid_main(x,y): return ztop(rr_of(x,y))+CURB+GAP+GT
a_e=[math.atan2(p[1]-C[1],p[0]-C[0])%(2*math.pi) for p,u in edge[1:-1]]
r_e=[np.linalg.norm(p-C) for p,u in edge[1:-1]]
pts=[P(RW+OVH,a) for a in a_e]+[P(rr+20,a) for rr,a in zip(r_e,a_e)][::-1]
gp=Polygon(pts).buffer(0)
if gp.area>0: sloped(gp.simplify(5),GT,L_gap,zlid_main)
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
