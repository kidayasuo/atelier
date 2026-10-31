"""本館の床（2026-10-19 夜）。縁側 3 m の中ほど（r=191.5 m）に断熱ガラス戸、外縁側（土足 FL −150）と内縁側（はだし FL ±0）に分ける。
高さの約束：地面 GL −300／土足の床 −150（外縁側・あまのがわ・南の縁側）／はだしの床 ±0／受け取り土間 −300（GL と同じ）。
python3 -I add_floor.py IN OUT   （add_south.py → add_monitor_west.py の後）"""
import sys, os as _os, numpy as np, rhino3dm as r
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
L_out=layer('82_本館_外縁側（土足 −150）',(176,140,100)); L_kai=layer('83_本館_あまのがわ（土足 −150）',(200,190,170))
L_gl=layer('85_本館_断熱ガラス戸（縁側の中ほど）',(150,200,230))
# あまのがわ：ホール（8–10）の南端、ガラス戸の線から西の外壁まで。10-28（ユーザー、案4、決定事項（本館）の「靴：」）：南の縁（架構の線 u21）は
# まっすぐ、北の縁（ホールとの段 150、框）はゆらゆらの曲線（data/amanogawa.json の (v, 幅)、PCHIP）。前は幅 1.5 の直線。kai は下で（u, v）の形から作る
a8n,a8s=span(8)
doma=quad(RK,RO,TH[17],th19)                                   # 受け取り土間（add_south で −300 の板あり）
# 10-28（監修の項 20261027-2346 の 12・20261027-2020 の 4、ユーザー 10-27夜：曲線は架構だけ）：床・内縁側・あまのがわの板はスパンごとに真っすぐ
# （架構の線 u=3k と 3k+3 の弦、外壁・縁側の杉の壁の squaring と同じ）。前は r の弧を 60 に分けた多角形で、弦の壁と 5 mm 食い違い、
# 縁側の杉の壁（各スパンの北の半分、v 13.465〜13.6）で −150〜−10 だけ欠かれて 138 面になっていた。床の板は杉の壁の所で壁の内面
# v 13.465 まで（壁の下まで全部の深さで止める）、戸の所はガラス戸の線 v 13.5 まで。一枚ずつ輪郭の押し出し。
sys.path.insert(0,'/tmp/claude-0/t/south')
from uv import xy as _xy
from shapely.geometry import box as _box
def _chord(u,v):
    k=int(min(18,max(0,np.floor(u/3.0)))); f=(u-3.0*k)/3.0
    return _xy(3.0*k,v)*(1.0-f)+_xy(3.0*(k+1),v)*f
def _dense(ring):
    P_=list(ring.coords); out_=[]
    for (u0,v0),(u1,v1) in zip(P_,P_[1:]):
        out_.append((u0,v0))
        if abs(u1-u0)>1e-9:
            for uk in sorted([3.0*k for k in range(20) if min(u0,u1)+1e-6<3.0*k<max(u0,u1)-1e-6],reverse=u1<u0):
                out_.append((uk,v0+(v1-v0)*(uk-u0)/(u1-u0)))
    return out_
def _uvslab(g,z0,z1,li):
    for gg in getattr(g,'geoms',[g]):
        if gg.geom_type!='Polygon' or gg.area<0.05: continue
        slab(Polygon([tuple(_chord(u,v)) for u,v in _dense(gg.exterior)]),z0,z1,li)
V_RG,V_RO,V_RC,V_RK,V_WALL=13.5,-0.2,12.0,1.6,13.465
import json as _json
from scipy.interpolate import PchipInterpolator as _Pchip
_AMA=_json.load(open(_os.path.join(_os.environ.get('SODACHIYA_ROOT','/home/claude/atelier/sodachiya'),'data','amanogawa.json'),encoding='utf-8'))
_C=np.array(_AMA['CONTROL']); _wf=_Pchip(_C[:,0],_C[:,1]); U_S=float(_AMA['U_SOUTH'])
KAMACHI=0.06                                                     # 框（杉、見付 60）：北の縁の内側（川の側）に、川の床の上 −150〜0（延床は川の床で数える）
_vs=np.r_[V_RO,np.arange(-0.15,V_RG-0.025,0.05),V_RG]            # 曲線は 50 mm おきの点（弦の高さ 0.1 mm 未満、Rhino 版でスプラインに）
_un=U_S+_wf(_vs)
_kai=Polygon([(U_S,V_RO)]+list(zip(_un,_vs))+[(U_S,V_RG)]).buffer(0)                        # あまのがわ（−150）
_kam=Polygon(list(zip(_un-KAMACHI,_vs))+list(zip(_un[::-1],_vs[::-1]))).buffer(0)          # 框
_kaiK=_kai                                                                                    # 床から抜く形（川、框を含む）
kai=Polygon([tuple(_chord(u,v)) for u,v in _dense(_kai.exterior)])                         # 世界の座標（室の板・ガラリで使う）
kaiK=Polygon([tuple(_chord(u,v)) for u,v in _dense(_kaiK.exterior)])
_walls=unary_union([_box(3.0*s_-1.5,V_WALL,3.0*s_,V_RG) for s_ in range(1,20)])
# 西の端は外壁の内面（v −0.1997、弦）の 1 mm 内、西の外壁の足もとの小さな壁（u30.0〜30.1、南の妻 v1.40〜1.75）の所は欠く（削る段で高さの途中まで欠かれて押し出しでなくなっていた）
_stubs=unary_union([_box(29.99,-0.2,30.11,0.085),_box(-0.08,1.395,0.08,1.755)])
inner=_box(0.0,-0.199,57.0,V_RG).difference(_kaiK).difference(_box(0.0,-0.199,6.0,V_RK)).difference(_walls).difference(_stubs)
# 本の奥（スパン18–19、西吹き抜けの北の行き止まり）の掘りごたつの溝（ユーザー 10-31 14:21、決定事項（本館）の「本の奥」）：溝は窓際
# （西の外壁の内面 v−0.2 から、部屋の側の畳の座の縁 v0.75 まで。縁の杉の框 30 を含む）。南の口の段（u51.6〜51.9、−150）から北の妻（u57.0）まで下げる
# （溝の底 −300＝低い窓の下端、木の床）。架構の線 u54・57 の柱（v−0.28〜0.28）の足もとは床を残す（柱は ±0 に立つ）。
# 框・畳の座は shitsu/add_shitsurae.py の hon_no_oku。床の塊は溝の所を抜き、底の塊（上面 −310／段 −160、框の内）を足す
HON_U0, HON_US, HON_U1, HON_V0, HON_V1, HON_K = 51.6, 51.9, 57.0, -0.2, 0.75, 0.03
_HON_COLS=unary_union([_box(53.91,-0.3,54.09,0.28),_box(56.91,-0.3,57.09,0.28)])
_hon_uv=lambda u0_,u1_,v1_,v0_=-0.199: _box(u0_,v0_,u1_,v1_).difference(_HON_COLS)
inner=inner.difference(_hon_uv(HON_U0,HON_U1,HON_V1))
_n0=len(m.Objects)                                              # 10-31：杉の床板の絵の向き（add_south.py の tex_tag）。床組は v、内縁側は u
_uvslab(inner,-450,-10,L_fl)                                    # 床組（上面 −10、色付きの室の板 0〜10 の下）
_uvslab(_hon_uv(HON_U0,HON_US,HON_V1-HON_K),-450,-160,L_fl)   # 本の奥の溝の南の段（−150）
_uvslab(_hon_uv(HON_US,HON_U1,HON_V1-HON_K),-450,-310,L_fl)   # 本の奥の溝の底（−300）
tex_tag(_n0,'v'); _n0=len(m.Objects)
_uvslab(_box(0.0,V_RC,57.0,V_RG).difference(_kaiK).difference(_walls),-10,0,L_in)  # 内縁側の仕上げ
tex_tag(_n0,'u')
_uvslab(_kai,-450,-150,L_kai)
# 框：曲線の杉（見付 60、−150〜0）。はだしの床と色・素材を変える（間仕切り・框のレイヤー 91 → 38、杉板）。輪郭の押し出し
L_kmc=layer('91_しつらえ_間仕切り・框・腰壁',(200,185,160))
_uvslab(_kam,-150,0,L_kmc)
# 内縁側（v12〜13.5）で先生が川へ下りて渡る（給食、10-28 ユーザー）：段 150 はそのまま、両岸の段に手すり（丸棒 φ35・h800、柱 φ40）。
# 手すりは渡る帯の西の側（v12.1）に、段をはさんで ±0.3。東の側は東の口の戸（u21.06〜22.45）への川の道なのであける
L_hr=layer('96b_しつらえ_格子・手すり（木）',(185,150,105))
def _rod(p0,p1,rad,li):
    p0=np.asarray(p0,float); p1=np.asarray(p1,float); d_=p1-p0; L_=float(np.linalg.norm(d_))
    pl_=r.Plane(r.Point3d(*map(float,p0)),r.Vector3d(*map(float,d_/L_)))
    c_=r.Circle(float(rad)).ToNurbsCurve(); c_.Transform(r.Transform.PlaneToPlane(r.Plane.WorldXY(),pl_))
    ex_=r.Extrusion.Create(c_,L_,True)
    if ex_ is None: return
    bb=ex_.GetBoundingBox(); mid=np.array([(bb.Min.X+bb.Max.X)/2,(bb.Min.Y+bb.Max.Y)/2,(bb.Min.Z+bb.Max.Z)/2])
    if np.linalg.norm(mid-(p0+p1)/2)>1.0: ex_=r.Extrusion.Create(c_,-L_,True)
    a_=attr(li); a_.Name='あまのがわを渡る段の手すり φ35 h800'; m.Objects.AddExtrusion(ex_,a_)
_VH=12.1
for _ub in (U_S,U_S+float(_wf(_VH))):
    _p=lambda u_,z_: [*_chord(u_,_VH),z_]
    _rod(_p(_ub-0.3,800.0),_p(_ub+0.3,800.0),17.5,L_hr)
    for _uu in (_ub-0.3,_ub+0.3): _rod(_p(_uu,-150.0 if U_S<_uu<U_S+float(_wf(_VH)) else 0.0),_p(_uu,800.0),20.0,L_hr)   # 柱の足もと：川の中は −150
outer=quad(RE,RG,TH[0],TH[18],60)                              # 外縁側（最後のスパンはスロープ）
slab(outer,-300,-150,L_out)
# 断熱ガラス戸：r=191.5 の線、FL ±0 から 2.6 m（あまのがわの口は開閉する引戸として同じ線上）
gl=[P(RG,a) for a in np.linspace(TH[0],th19,60)]
# 10-21：引き戸＋鴨居の上は枠なしの固定ガラスで屋根の下まで。10-26（ユーザー）：鴨居の上端を梁の下端（ガラスの線 v13.5 で h2450）の 5 下 h2445 まで上げた（鴨居 h2385〜2445、戸 h2375）
KAMOI=2385; ZUND=lambda x,y: ztop(rr_of(x,y))-150   # 鴨居の上の固定ガラスは屋根の立体の下面（梁の上端）まで（10-26夜）
L_kam=layer('18_本館_鴨居・建具枠（木）',(150,110,70))
# 10-24夜（ユーザーの決定、監修と相談）：架構のスパンごとに半分FIX＋半分片引き戸、19スパンとも同じ向き。
# 各スパンの南の半分が開く側、戸は北の半分のFIXの室内側（西）を走る（閉じた形で、戸は南の半分に、FIXに 50 かかる）。
# ガラスは強化か合わせ。衝突防止に園のロゴをエッチング：板の真ん中、こどもの目の高さ（中心 FL+1.0）、大人の目の高さ（FL+1.5）に小さな印。
# 0・1歳（スパン1–4）の低い所には入れない（ユーザー：はいはいの子はぶつかってよい）。戸の板の印は少しずらす（開けて重なっても模様に見える）。
# 10-26夜（ユーザー、監修の計算）：FIX をやめて杉の壁に（各スパンの北の半分）。光の筋の鏡面化と組で、中ほどの昼光率は約3.5%。
# 壁は外が大和張り・内が杉板、厚さ 135（RG−100〜RG+35、戸のレール RG+40〜80 の外）。床（外縁側 −150）から鴨居の下まで。外壁と同じ 97（→ 17）。
L_ew=layer('97_本館_外壁（西・南北の妻）',(196,160,118))
L_dc=layer('16d_本館_縁側のガラスの片引き戸（閉）',(150,200,230))
L_do=layer('16o_本館_縁側のガラスの片引き戸（開）',(150,200,230))
# 10-27（監修の項 20261027-1704、一つのレイヤーには一つの素材）：戸の框（杉）を別のレイヤーに。ガラスは 16d・16o のまま。
L_hc=layer('16h_本館_縁側の片引き戸の框（杉、閉）',(196,160,118))
L_ho=layer('16i_本館_縁側の片引き戸の框（杉、開）',(196,160,118))
for _li in (L_do,L_ho): m.Layers[_li].Visible=False                          # 開けた位置は最初は隠す（Rhinoで表示を切り替えて見比べる）
# 戸の板：框は見付 60（縦框・上框）・下框 90、見込み 40（戸の厚さ）。ガラスは框の中に t12（強化か合わせ）、戸の厚さの真ん中。
DOOR_R=RG+60; DOOR_GL=12
def _arc_band(R_,a0,a1,z0f,z1f,thick,li,at=None,n=8):
    """10-29（監修の依頼の 5）：弧 R_ に沿う厚さ thick の板を一つの物で（前は wall_along で弧の区間ごとに 7 片、
    _square が片ごとに平らな板にして幅 約200 の短冊になり、シェーディングで縦の線に見えた）。fix_details.py の _square がスパンの弦の上の一枚の平らな板にする"""
    a_=np.linspace(a0,a1,n); q=[P(R_-thick/2,x) for x in a_]+[P(R_+thick/2,x) for x in a_[::-1]]
    m.Objects.AddMesh(mesh_prism([(x,y,float(z0f(x,y))) for x,y in q],[(x,y,float(z1f(x,y))) for x,y in q]),at if at is not None else attr(li))
def door_leaf(a0,a1,li_f,li_g,mark=False):
    da=np.sign(a1-a0)*60/DOOR_R
    for b0,b1 in ((a0,a0+da),(a1-da,a1)):                                   # 縦框
        wall_along([P(DOOR_R,b0),P(DOOR_R,b1)],lambda x,y:0,lambda x,y:KAMOI-10,40,li_f)
    _arc_band(DOOR_R,a0+da,a1-da,lambda x,y:0,lambda x,y:90,40,li_f)                    # 下框（一本）
    _arc_band(DOOR_R,a0+da,a1-da,lambda x,y:KAMOI-70,lambda x,y:KAMOI-10,40,li_f)       # 上框（一本）
    # ガラス（戸 1 枚に 1 枚。ロゴを貼る場所をユーザー文字列 'etch' で書いておく → 最後の段 materials.py が絵を貼る）
    at=attr(li_g)
    if mark: at.SetUserString('etch',_etch((a0+a1)/2))
    _arc_band(DOOR_R,a0+da,a1-da,lambda x,y:90.0,lambda x,y:float(KAMOI-70),DOOR_GL,li_g,at)
# 10-25：本物のロゴ（sodachiya/logo/sodachiya_logo.svg、黒＝エッチング）。φ180、中心 FL+1.0、ガラスの室内側の面に。
# 大人の目の高さ（FL+1.5）には幅 10・長さ 600 の細い横の帯。
# 10-27（ユーザー：ガラスのロゴのエッチングは、テクスチャマッピングで単に絵を貼り付けて）：ここでは形を作らない（前の網目は
# 1 枚約 1 万の三角形でファイルが重かった）。戸のガラスの物に、貼る場所だけを書く。絵（SVG から毎回作る PNG）と貼る板は
# 最後の段 materials.py が両方の 3dm に足す。
import json as _json
def _etch(ang):
    """ガラスの室内側の面（RG+60+6）の上の、戸の左右の真ん中。n：室内（西）向きの法線、t：南（室内から見て右）"""
    c=np.array(P(DOOR_R+DOOR_GL/2,ang)); d=(c-np.array(C)); d=d/np.linalg.norm(d); t=np.array([-d[1],d[0]])
    f=lambda v: [round(float(x),3) for x in v]
    return _json.dumps(dict(n=f([d[0],d[1],0.0]),t=f([t[0],t[1],0.0]),
        marks=[dict(kind='logo',c=f([c[0],c[1],1000.0]),w=180,h=180),                 # 園のロゴ φ180、中心 FL+1.0
               dict(kind='band',c=f([c[0],c[1],1500.0]),w=600,h=10)]),ensure_ascii=False)   # 大人の目の高さの帯
for k in range(19):
    a_n,a_s=TH[k],(TH[k+1] if k<18 else th19); mid=(a_n+a_s)/2
    fix=[P(RG,a) for a in np.linspace(a_n,mid,8)]
    door_c=[P(RG+60,a) for a in np.linspace(mid-50/RG,a_s,8)]                 # 閉：南の半分、FIX に 50 かかる
    _L=(a_s-(mid-50/RG)); door_o=[P(RG+60,a) for a in np.linspace(a_n,a_n+_L,8)]
    # 杉の壁は耐力壁（10-27、監修の略算：縁側の壁が無いと桁の方向の耐力・偏心率とも足りない）。力を屋根の合板まで通すため、
    # 壁は土台から屋根の下面（梁の上端）まで一枚（鴨居の上のガラスは戸の側の半分だけ）。梁の下端（h2450）より上は、
    # 架構の線の 180 の内（光の筋のすき間と梁）を避けて、梁の南の面から（壁の真上に抱き合わせの垂木、ホールダウン 15〜20 kN 級）
    a_b=a_n+np.sign(mid-a_n)*180/RG
    # 10-27（ユーザー：FIX の壁に複雑な線）：前は外の 100 と内の 35 を別々に、弧の 7 区間ごとに箱を置いて重ねていたので、継ぎ目が残り、
    # 二つの壁は Rhino 版で閉じた立体に戻らなかった。壁は厚さ 135（RG−100〜RG+35）の一つの立体を二つ（下：外縁側の上 −150 から鴨居の上 KAMOI+60、
    # 上：梁の南の面から屋根の下面まで）にする。内縁側の床（±0）より下の分は床が削られる（優先順位 E＞F）。
    _ring=lambda b0,b1: [P(RG-100,a) for a in np.linspace(b0,b1,8)]+[P(RG+35,a) for a in np.linspace(b1,b0,8)]
    _q=_ring(a_n,mid); m.Objects.AddMesh(mesh_prism([(x,y,-150.0) for x,y in _q],[(x,y,KAMOI+60.0) for x,y in _q]),attr(L_ew))
    _q=_ring(a_b,mid); m.Objects.AddMesh(mesh_prism([(x,y,KAMOI+60.0) for x,y in _q],[(x,y,float(ZUND(x,y))) for x,y in _q]),attr(L_ew))
    _arc_band(RG,mid,a_s,lambda x,y:KAMOI+60,ZUND,20,L_gl)   # 鴨居の上の固定ガラス（戸の側の半分だけ、一枚）
    span_no=19-k                                                             # 南から数えたスパンの番号
    mk=span_no>=5                                                            # 0・1歳（スパン1–4）の低い所には入れない
    door_leaf(mid-50/RG,a_s,L_hc,L_dc,mk)                                   # 片引き戸（閉）
    door_leaf(a_n,a_n+_L,L_ho,L_do,mk)                                       # 片引き戸（開）
# 鴨居（10-29、監修の項 20261029-0928-kanshu-2 の 2）：スパンごとに戸の側の半分（杉の壁の端 mid から次の架構の線まで）だけに。
# 前は全長に通して杉の壁と重なる所を優先順位で削らせていたので、壁（RG−100〜RG+35）から室内へ 10 出た細い片（厚さ 10、
# 架構の線で切れた短いものは 3〜9 万 mm³ の離れた片）が壁の半分ごとに残った。戸の側の形は前と同じ
for k in range(19):
    a_n,a_s=TH[k],(TH[k+1] if k<18 else th19); mid=(a_n+a_s)/2
    _arc_band(RG,mid,a_s,lambda x,y:KAMOI,lambda x,y:KAMOI+60,90,L_kam)       # 一本
# 鴨居の上の固定ガラスは、上のスパンごとの所で戸の側の半分だけに作る（10-27）
# 10-24：床下の風の道（決定事項（共通）の「床下の風の道」）。外縁側（−150）から内縁側（±0）への段の蹴込みにガラリ
# （夏の夜の外気 → 床下、防虫網・ごみよけ・防犯の格子・ダンパー）。ガラス戸は腰の無いシンプルな引き戸（上のまま）。あまのがわの口は除く。
from shapely.geometry import Point
L_gal=layer('16b_本館_蹴込みのガラリ（夏の夜の外気を床下へ）',(90,90,90))
_kb=kai.buffer(300)
# 杉の壁の所（各スパンの北の半分）は、ガラリを壁の足もと（外面 RG−100 の外）に（10-26夜）
_WALLA=[(min(TH[k],(TH[k]+(TH[k+1] if k<18 else th19))/2),max(TH[k],(TH[k]+(TH[k+1] if k<18 else th19))/2)) for k in range(19)]
_inw=lambda a: any(lo<=a<=hi for lo,hi in _WALLA)
_run=[]; _prev=None
for a in list(np.linspace(TH[0],th19,240))+[None]:
    f=None if a is None else _inw(a)
    p_=None if a is None else P(RG-110 if f else RG-15,a)
    if p_ is not None and not _kb.contains(Point(*p_)) and (f==_prev or not _run): _run.append(p_); _prev=f; continue
    if len(_run)>=2: wall_along(_run,lambda x,y:-130,lambda x,y:-20,20,L_gal)
    _run=[p_] if (p_ is not None and not _kb.contains(Point(*p_))) else []; _prev=f
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
    if name=='ホール': g=g.difference(kaiK)
    _n0=len(m.Objects)
    for gg in getattr(g,'geoms',[g]): slab(gg,0,10,li)
    if not name.startswith('便所'): tex_tag(_n0,'v')            # 杉の床板は v（便所・倉庫は磁器タイル）
    areas[name]=areas.get(name,0)+g.area/1e6
_hon=lambda u0_,u1_,v0_=HON_V0: Polygon([tuple(_chord(u,v)) for u,v in _dense(_hon_uv(u0_,u1_,HON_V1-HON_K,v0_).exterior)])
_n0=len(m.Objects)
strip=quad(RK,RO,TH[0],span(5)[1],60).difference(kai).difference(_hon(HON_U0,HON_U1,-0.25))   # 西の端は外壁の内面（RO）の外まで抜く（細い残りを作らない）
for g in getattr(strip,'geoms',[strip]):
    if g.area>1e5: slab(g,0,10,L_cor)
slab(_hon(HON_U0,HON_US),-150,-140,L_cor); slab(_hon(HON_US,HON_U1),-300,-290,L_cor)   # 本の奥の溝：室の板は溝の底へ（面積は同じ）
tex_tag(_n0,'u')                                                 # 西吹き抜け（南北に長い通り）は u
m.Write(OUT,8)
sp=lambda s: quad(RG,RC,*span(s)).area/1e6
print({k:round(v,1) for k,v in areas.items()},'内縁側 1 スパン',round(sp(10),2),'m2','あまのがわ',round(kai.area/1e6,1),'框',round(_kam.area,2))
