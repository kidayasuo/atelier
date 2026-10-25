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
L_logo=layer('16e_本館_ガラスのロゴ（衝突防止、エッチング、FIX）',(60,90,110))
L_dc=layer('16d_本館_縁側の片引き戸（閉）',(150,200,230))
L_do=layer('16o_本館_縁側の片引き戸（開）',(150,200,230))
for _i,_l in enumerate(m.Layers):
    if _l.Name=='16o_本館_縁側の片引き戸（開）': _l.Visible=False                # 開けた位置は最初は隠す（Rhinoで表示を切り替えて見比べる）
# 10-25：本物のロゴ（sodachiya/logo/sodachiya_logo.svg、黒＝エッチング）。形は毎回 SVG から読む（ユーザーが書き換えてもよい）。
# 200 単位＝ロゴの直径 → ガラスでは φ180。ガラスの室内側の面から 0.5 離して厚さ 1.0 の薄い板（閉じた立体）。中心 FL+1.0。
# 大人の目の高さ（FL+1.5）には幅 10・長さ 600 の細い横の帯。
import os as _os, re as _re
import mapbox_earcut as _ec
from shapely.geometry import Polygon as _Pg
from shapely.ops import unary_union as _uu
def _logo_polys(path):
    src=open(path,encoding='utf-8').read(); out=[]
    for mm in _re.finditer(r'<path\b([^>]*)/?>', src):
        d=_re.search(r'\sd="([^"]*)"', mm.group(1)).group(1)
        rings=[]
        for sub in _re.split(r'[Mm]', d)[1:]:
            pts=[tuple(map(float,q)) for q in _re.findall(r'(-?[\d.]+)[ ,](-?[\d.]+)', sub)]
            if len(pts)>=3: rings.append(_Pg(pts).buffer(0))
        g=None
        for rg in rings: g=rg if g is None else g.symmetric_difference(rg)   # fill-rule evenodd
        if g is not None: out.append(g)
    return _uu(out)
_LOGO_SVG=_os.path.join(_os.environ.get('SODACHIYA_ROOT',''),'logo','sodachiya_logo.svg')   # run_all.sh が SODACHIYA_ROOT を渡す
_LOGO=_logo_polys(_LOGO_SVG) if _os.path.exists(_LOGO_SVG) else None
print('logo', _LOGO_SVG, 'ok' if _LOGO is not None else 'なし（場所の帯だけ）')
def _plate(g2, c, off, li, thick=1.0):
    """g2：(x, z) の平面形（x はガラスに沿って南が +、z は上が +、mm）を、ガラスの線上の点 c の室内側 off の面に厚さ thick の板で。
    一つのロゴは一つの物（離れた輪・線は同じ網目の中の別の閉じた立体）。白の艶消し（エッチングに似せる、ソリッド係 10-25）"""
    d=np.array(c)-C; d=d/np.linalg.norm(d); t=np.array([-d[1],d[0]])            # d：室内（西）、t：南
    M=r.Mesh()
    for pg in getattr(g2,'geoms',[g2]):
        if pg.is_empty or pg.area<0.5: continue
        rings=[np.asarray(pg.exterior.coords)[:-1]]+[np.asarray(h.coords)[:-1] for h in pg.interiors]
        V2=np.vstack(rings); ends=np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri=np.array(_ec.triangulate_float64(V2.astype(np.float64),ends)).reshape(-1,3)
        b=len(M.Vertices); n=len(V2)
        for o_ in (off,off+thick):
            for x,z in V2:
                q=np.array(c)+d*o_+t*x; M.Vertices.Add(float(q[0]),float(q[1]),float(z))
        for a_,b_,c_ in tri: M.Faces.AddFace(int(b+a_),int(b+c_),int(b+b_)); M.Faces.AddFace(int(b+n+a_),int(b+n+b_),int(b+n+c_))
        st=0
        for e in ends:
            for i_ in range(st,e):
                j_=i_+1 if i_+1<e else st; M.Faces.AddFace(int(b+i_),int(b+j_),int(b+n+j_),int(b+n+i_))
            st=int(e)
    if len(M.Faces)==0: return
    M.Normals.ComputeNormals(); M.Compact()
    a_=r.ObjectAttributes(); a_.LayerIndex=li; a_.Name='園のロゴ（エッチング）'
    a_.ColorSource=r.ObjectColorSource.ColorFromObject; a_.ObjectColor=(245,245,242,255)   # 白の艶消し（すりガラスに似せる）
    m.Objects.AddMesh(M,a_)
def _marks(c, off, li):
    if _LOGO is not None:
        from shapely import affinity as _af
        g=_af.scale(_LOGO.buffer(0), 0.9, -0.9, origin=(100,100))             # 200 → 180 mm、SVG の y（下が +）を上が + に
        g=_af.translate(g, -100, 1000-100)
        _plate(g.buffer(0), c, off, li)                                     # ロゴで一つの物
    _plate(_Pg([(-300,1495),(300,1495),(300,1505),(-300,1505)]), c, off, li)  # 大人の目の高さの細い帯（同じ作り方）
for k in range(19):
    a_n,a_s=TH[k],(TH[k+1] if k<18 else th19); mid=(a_n+a_s)/2
    fix=[P(RG,a) for a in np.linspace(a_n,mid,8)]
    door_c=[P(RG+60,a) for a in np.linspace(mid-50/RG,a_s,8)]                 # 閉：南の半分、FIX に 50 かかる
    _L=(a_s-(mid-50/RG)); door_o=[P(RG+60,a) for a in np.linspace(a_n,a_n+_L,8)]
    wall_along(fix,lambda x,y:0,lambda x,y:KAMOI,30,L_gl)                   # FIX
    wall_along(door_c,lambda x,y:0,lambda x,y:KAMOI-10,40,L_dc)             # 片引き戸（閉）
    wall_along(door_o,lambda x,y:0,lambda x,y:KAMOI-10,40,L_do)             # 片引き戸（開）
    span_no=19-k                                                             # 南から数えたスパンの番号
    if span_no>=5:                                                           # 0・1歳（スパン1–4）の低い所には入れない
        _marks(P(RG,(a_n+mid)/2), 15.5, L_logo)                              # FIX の室内側の面（RG+15）から 0.5
        _marks(P(RG,(mid-50/RG+a_s)/2), 80.5, L_dc)                          # 戸の室内側の面（RG+80）から 0.5（閉）
        _marks(P(RG,a_n+_L/2), 80.5, L_do)                                   # 戸（開）
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
