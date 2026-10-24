"""本館の床（2026-10-19 夜）。縁側 3 m の中ほど（r=191.5 m）に断熱ガラス戸、外縁側（土足 FL −150）と内縁側（はだし FL ±0）に分ける。
高さの約束：地面 GL −300／土足の床 −150（外縁側・海峡・南の縁側）／はだしの床 ±0／受け取り土間 −300（GL と同じ）。
python3 -I add_floor.py IN OUT   （add_south.py → add_monitor_west.py の後）"""
import sys, numpy as np, rhino3dm as r
src=open('/tmp/claude-0/t/south/add_south.py').read()
exec(src.split("m=r.File3dm.Read(IN)")[0].replace("IN=sys.argv[1]; OUT=sys.argv[2]",""))
IN,OUT=sys.argv[1],sys.argv[2]
m=r.File3dm.Read(IN)
exec(src.split("m=r.File3dm.Read(IN)")[1].split("K0=13")[0])
RG=191500            # 断熱ガラス戸の線
def span(s):         # 南から s 番目のスパン（1..19）の角度範囲（北側, 南側）
    return TH[19-s],TH[20-s]
# --- 高さの層（床の板：厚さ 300 の「床の塊」を上面の高さ違いで作る）---
L_fl=layer('80_本館_床（はだし ±0）',(222,205,170)); L_in=layer('81_本館_内縁側（はだし ±0）',hexc('F4EBDD'))
L_out=layer('82_本館_外縁側（土足 −150）',(176,140,100)); L_kai=layer('83_本館_海峡（土足 −150）',(200,190,170))
L_gl=layer('85_本館_断熱ガラス戸（縁側の中ほど）',(150,200,230))
# 海峡：ホール（8–10）の南端 1.5 m（8 スパン目の南側）、ガラス戸の線から西の外壁まで
a8n,a8s=span(8); akai=a8s-1500/RK
kai=quad(RG,RO,akai,a8s,20)
doma=quad(RK,RO,TH[17],th19)                                   # 受け取り土間（add_south で −300 の板あり）
inner=quad(RG,RO,TH[0],th19,60).difference(kai).difference(doma)
for g in getattr(inner,'geoms',[inner]):
    if g.area>1e5: slab(g.simplify(3),-450,-10,L_fl)            # 床組（上面 −10、色付きの室の板 0〜10 の下）
_in=quad(RG,RC,TH[0],th19,60).difference(kai)
for g in getattr(_in,'geoms',[_in]): slab(g,-10,0,L_in)     # 内縁側の仕上げ
slab(kai,-450,-150,L_kai)
outer=quad(RE,RG,TH[0],TH[18],60)                              # 外縁側（最後のスパンはスロープ）
slab(outer,-300,-150,L_out)
# 断熱ガラス戸：r=191.5 の線、FL ±0 から 2.6 m（海峡の口は開閉する引戸として同じ線上）
gl=[P(RG,a) for a in np.linspace(TH[0],th19,60)]
# 10-21：引き戸（鴨居は梁の下端 h2270、2 スパン通し）＋鴨居の上は枠なしの固定ガラスで屋根の下まで
KAMOI=2270; ZUND=lambda x,y: ztop(rr_of(x,y))-250
L_kam=layer('18_本館_鴨居・建具枠（木）',(150,110,70))
# 10-24夜（ユーザーの決定、監修と相談）：架構のスパンごとに半分FIX＋半分片引き戸、19スパンとも同じ向き。
# 各スパンの南の半分が開く側、戸は北の半分のFIXの室内側（西）を走る（閉じた形で、戸は南の半分に、FIXに 50 かかる）。
# ガラスは強化か合わせ。衝突防止に園のロゴをエッチング：板の真ん中、こどもの目の高さ（中心 FL+1.0）、大人の目の高さ（FL+1.5）に小さな印。
# 0・1歳（スパン1–4）の低い所には入れない（ユーザー：はいはいの子はぶつかってよい）。戸の板の印は少しずらす（開けて重なっても模様に見える）。
L_logo=layer('16e_本館_ガラスのロゴ（衝突防止、エッチング）',(120,150,170))
def _disc(c,z,rad,li,off):
    """ガラスの面に貼った薄い円（ロゴの場所の印、φ2·rad、厚さ4）。c：ガラスの線上の点、off：面からの距離（室内が +）"""
    d=np.array(c)-C; d=d/np.linalg.norm(d); t=np.array([-d[1],d[0]])
    ring=[(float((np.array(c)+d*off+t*rad*np.cos(a))[0]),float((np.array(c)+d*off+t*rad*np.cos(a))[1]),z+rad*np.sin(a)) for a in np.linspace(0,2*np.pi,25)[:-1]]
    M=r.Mesh()
    for q in ring: M.Vertices.Add(*q)
    for q in ring: M.Vertices.Add(q[0]+d[0]*4,q[1]+d[1]*4,q[2])
    n=len(ring)
    for i in range(1,n-1): M.Faces.AddFace(0,i,i+1); M.Faces.AddFace(n,n+i+1,n+i)
    for i in range(n): j=(i+1)%n; M.Faces.AddFace(i,j,n+j,n+i)
    M.Normals.ComputeNormals(); M.Compact()
    a_=r.ObjectAttributes(); a_.LayerIndex=li; m.Objects.AddMesh(M,a_)
for k in range(19):
    a_n,a_s=TH[k],(TH[k+1] if k<18 else th19); mid=(a_n+a_s)/2
    fix=[P(RG,a) for a in np.linspace(a_n,mid,8)]
    door=[P(RG+60,a) for a in np.linspace(mid-50/RG,a_s,8)]
    wall_along(fix,lambda x,y:0,lambda x,y:KAMOI,30,L_gl)                   # FIX
    wall_along(door,lambda x,y:0,lambda x,y:KAMOI-10,40,L_gl)               # 片引き戸（室内側を北へ引く）
    span_no=19-k                                                             # 南から数えたスパンの番号
    if span_no>=5:
        for aa,off,dz in (((a_n+mid)/2,16,0.0),((mid+a_s)/2+150/RG,81,0.0)):   # 室内側の面
            _disc(P(RG,aa),1000+dz,150,L_logo,off)
            _disc(P(RG,aa),1500+dz,40,L_logo,off)
wall_along(gl,lambda x,y:KAMOI,lambda x,y:KAMOI+60,90,L_kam)               # 鴨居
wall_along(gl,lambda x,y:KAMOI+60,ZUND,20,L_gl)                             # 固定ガラス
# 10-24：床下の風の道（決定事項（共通）の「床下の風の道」）。外縁側（−150）から内縁側（±0）への段の蹴込みにガラリ
# （夏の夜の外気 → 床下、防虫網・ごみよけ・防犯の格子・ダンパー）。ガラス戸は腰の無いシンプルな引き戸（上のまま）。海峡の口は除く。
from shapely.geometry import Point
L_gal=layer('16b_本館_蹴込みのガラリ（夏の夜の外気を床下へ）',(90,90,90))
_kb=kai.buffer(300)
_gp=[P(RG-15,a) for a in np.linspace(TH[0],th19,240)]
_run=[]
for p_ in _gp+[None]:
    if p_ is not None and not _kb.contains(Point(*p_)): _run.append(p_); continue
    if len(_run)>=2: wall_along(_run,lambda x,y:-130,lambda x,y:-20,20,L_gal)
    _run=[]
for a_ in (TH[0],th19):                                         # 内縁側の南北の端もガラスで閉じる
    wall_along([P(RG,a_),P(RC,a_)],lambda x,y:0,ZUND,30,L_gl)
# --- 室の色の板（スパン 7〜19。1〜6 は add_south の 0・1 歳／2 歳） ---
ROOMS=[(7,7,'医務','F7F3EA'),(8,10,'ホール','E3C08D'),(11,11,'事務','E9DCC4'),(12,13,'3歳','9FCB84'),(14,14,'便所・倉庫','D5EBEE'),
       (15,16,'4歳','86BC78'),(17,17,'便所・倉庫','D5EBEE'),(18,19,'5歳','6FA96E')]
L_cor=layer('59_1F_西吹き抜け（スパン 5〜19、先生の道・廊下）',hexc('F4EBDD'))
areas={}
for s0,s1,name,col in ROOMS:
    li=layer(f'59_1F_{name}',hexc(col))
    an,_=span(s1); _,as_=span(s0)
    g=quad(RC,RK,an,as_,20)
    if name=='ホール': g=g.difference(kai)
    for gg in getattr(g,'geoms',[g]): slab(gg,0,10,li)
    areas[name]=areas.get(name,0)+g.area/1e6
strip=quad(RK,RO,TH[0],span(5)[1],60).difference(kai)
for g in getattr(strip,'geoms',[strip]):
    if g.area>1e5: slab(g,0,10,L_cor)
m.Write(OUT,8)
sp=lambda s: quad(RG,RC,*span(s)).area/1e6
print({k:round(v,1) for k,v in areas.items()},'内縁側 1 スパン',round(sp(10),2),'m2','海峡',round(kai.area/1e6,1))
