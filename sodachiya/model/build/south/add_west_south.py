"""西館の南の部分（2026-10-21 夕の決定、詳細設計チャットの plan05.py に合わせる）
使い方: python3 add_west_south.py IN.3dm OUT.3dm     （finish.py の後、レイヤー番号は 00〜69 の後）
- 西館の外壁（21）を厚さ 150 で作り直す：南の面に入口の引き戸 1.8・今日のごはんの窓・キッチンの南のガラス、
  東の面はホールの範囲（u 21–30）を開け、遊戯室の口①②（u 30.6–32.6、口②は play.json の north_mouth）
- すき間の南の端にガラス（入口の脇、v −0.15〜−0.85）
- 床の板：キッチン u 21–27.25／調理の更衣・便所・前室 u 27.25–29.25（v −3.4〜−6.4）／はれのま（仮、34）残り／
  東の帯 u 22.5–30（すき間を含む、はだし ±0）
- 海峡を東の帯の南端まで延ばす（u 21–22.5、v −0.2〜−3.4、−150）、u 22.5 に框
- 西館 1 階の間仕切り（キッチン・更衣・はれのま、h3170＝2 階の床の下まで）：配膳口・返却口・戸・見える台所の窓、
  オープンキッチン（東の面に h450〜2270 のガラス）、更衣・前室・便所ははれのまの西の端（西の面に外への戸）、収納とカウンター
- スパン 7：医務 v 4.5〜12 の床と海峡の側の壁、框 150、医務との引き込み戸。窓口の帯（v 0〜1.6）・静養室（v 1.6〜4.5）・
  カウンター・飛び石は add_hall.py の「スパン 7」の節（本館係、10-23夜）。
"""
import sys, math, pickle, numpy as np, rhino3dm as r
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from shapely.geometry.polygon import orient as _orient
import mapbox_earcut as earcut
sys.path.insert(0, '/tmp/claude-0/t/south')
from uv import xy, uv

IN, OUT = sys.argv[1], sys.argv[2]
WNPKL = sys.argv[3] if len(sys.argv) > 3 else '/home/claude/atelier/sodachiya/data/wnew.pkl'
m = r.File3dm.Read(IN)
LN = {i: l.FullPath for i, l in enumerate(m.Layers)}

def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)
def lidx(prefix):
    return [i for i, n in LN.items() if n.startswith(prefix)][0]
def rename(prefix, new):
    i = lidx(prefix); m.Layers[i].Name = new
hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

L_WALL = lidx('21_'); L_PART = lidx('24_'); L_STR = lidx('15_'); L_KAMA = lidx('38_')
L_KIT = lidx('32_'); L_HARE = lidx('34_'); L_BAND = lidx('33_')
L_GL = layer('19_西館_建具・ガラス（南の入口・窓）', (120, 170, 200))
L_COOK = layer('57_1F_調理の更衣・便所・前室', hexc('E3DAF0'))
rename('33_', '33_1F_東の帯（はだし ±0、ホールと一続き）')
rename('34_', '34_1F_はれのま')                                    # 10-28（監修の項 20261028-0015 の 19）：name.md の名前に（前は「食べる土間」）
L_MED = lidx('59_1F_医務'); L_WV = lidx('59_1F_西吹き抜け'); L_FURN = lidx('37_')
L_OFF7 = layer('59_1F_事務（スパン 7、おはようの窓口）', hexc('E9DCC4'))
L_DOOR = layer('89_遊戯室_搬入の大戸（閉じた状態）', (150, 110, 70))   # レイヤー表を new へ写す前に作る（後で作ると大戸が 00 に落ちる）
L_WD = layer('19b_西館_外の戸（木、開き戸）', (150, 110, 70))   # 10-27：調理の職員の外からの戸が 00_敷地 に落ちていた（ここで作る）
L_RAIN = layer('21g_西館_軒樋・鎖樋（道路の側）', (120, 120, 125))     # 同じく写す前に
L_STG_T = layer('59_1F_倉庫（すき間、先生の道）', hexc('D9D3EC'))      # 10-25：本館と西館のすき間の倉庫（写す前に）
L_STG_P = layer('59_1F_倉庫（すき間、遊戯室）', hexc('D9D3EC'))
L_SLD = layer('19c_西館_室内の引き戸（木）', (165, 120, 75))
L_19D = layer('19d_建具_室内の戸（木）', (165, 120, 75))       # 自動の戸（add_inner.py）と同じレイヤー：ここに置いた開口には自動の戸が出ない
# 10-26（ユーザー・監修）：不透明な外壁はスギの大和張り。外壁（21）の色をスギに（押縁はやめた、下の「水切り」）
CEDAR = (196, 160, 118)                    # 本館の外壁（17）と同じ
m.Layers[L_WALL].Color = (*CEDAR, 255)
WV = []
# ガラスの材質は本館のガラス戸（16）と同じ
mi = m.Layers[lidx('16_')].RenderMaterialIndex
if mi >= 0: m.Layers[L_GL].RenderMaterialIndex = mi

_D = pickle.load(open(WNPKL, 'rb')); WN = _D['WN']
WS = _D.get('WS', WN)          # 外皮の輪郭（外壁・屋根）。北西の斜めの外壁は壁面後退の線まで（10-23、西館係）。架構と間仕切りは WN
# すき間の倉庫（10-25、ユーザー・監修）：本館の西の外壁（外面 v−0.35）と西館の東の壁（外面 v−0.90）のあいだ 0.55。
# 南 u30〜40 は先生の道の側から（本館の西の外壁の引き戸は本館係）、北は遊戯室の側から（西館の東の壁の下に引き違いの口）。
# 口②（u45.6〜47.6）とその引き戸が北へ走る所（〜49.75）は除く。棚は本館の側に留め、西館の壁とは 80 あける。
GAP_T = [(33.10, 39.95)]                       # 10-27：スパン11（u30〜33）は本館から遊戯室・階段への口にした（倉庫はスパン12から）
GAP_P = [(40.05, 41.85), (42.15, 44.85), (49.80, 50.70)]

# ---------------------------------------------------------------- 消す：西館の外壁（一枚の面）・床の板 32/33/34
ztop_src = None
keep = []
for o in m.Objects:
    li = o.Attributes.LayerIndex; g = o.Geometry
    if li == L_WALL and isinstance(g, r.Mesh) and len(g.Vertices) > 500:
        ztop_src = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
        continue
    if li in (L_KIT, L_HARE, L_BAND, L_MED): continue
    if li == L_WV and isinstance(g, r.Mesh):
        WV.append(g); continue
    keep.append((g, o.Attributes))
# ---------------------------------------------------------------- 西館の屋根の面（10-24午後、ユーザー：軒は水平のまま、南北の端の屋根の形がヘンテコなのを直す）
# 決まり：棟（東の縁 v −0.9）は 8.15、外周の軒は 4.65 で水平、架構の向き（u 一定の放射の線）に沿ってまっすぐ下る。
# 前は、その線が外周（角の丸み R 付き）と交わる所を軒とした。角の丸みが南北の妻（放射の線そのもの）に接する所では、
# 線の長さが急に変わり（接する点では変わり方が無限大）、南北の端で面がねじれて谷やしわになっていた。
# 今：軒の線は、南北の妻に接する角（南西・北）だけ丸めない外形（軒の辺と妻の辺を延ばして交わらせた形）で決める。
# 直線の辺と西の面・北西の面のあいだの角は前と同じ。南西・北の角では、妻（けらば）の勾配のまま丸みを回って軒へ下りる。
# 北西の斜めの面と北の妻のあいだは、線の長さが直線的に変わるなめらかな面（ねじれは一様）。
import roofw
_RW = roofw.make(WN); roof_f = _RW['roof_f']; VRIDGE = _RW['VRIDGE']; _corners = _RW['corners']
# 前の屋根（比べるため）と置き換え
_old = [g for g, a in keep if a.LayerIndex == lidx('20_') and isinstance(g, r.Mesh) and len(g.Vertices) > 200]
_P = np.vstack([np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))]) for g in _old])
from scipy.interpolate import LinearNDInterpolator
_zo = LinearNDInterpolator(_P[:, :2], _P[:, 2])
keep = [(g, a) for g, a in keep if not (a.LayerIndex == lidx('20_') and isinstance(g, r.Mesh) and len(g.Vertices) > 200)]
_v_out = _RW['v_out']
_us = np.unique(np.r_[[f_ + d_ for f_ in _RW['FRAMES'][1:] for d_ in (-0.09, 0.09)], _RW['KINKS'], np.arange(21.0, 23.6, 0.05), np.arange(23.6, 40.4, 0.25), np.arange(40.4, 44.1, 0.05), np.arange(44.1, 49.9, 0.25), np.arange(49.9, 51.0001, 0.02)])
_us[0] += 0.0005; _us[-1] -= 0.0005
_NV = 40
rm = r.Mesh()
MON_W = 1.6                                      # 越屋根の幅（10-25：1.0 → 1.6）。屋根の面は越屋根の西の立ち上がりの外面から（越屋根の下は開ける）
for u in _us:
    ve, vw = _v_out(u); ve = min(ve, VRIDGE - MON_W - 0.06)
    for t in np.linspace(0, 1, _NV + 1):
        v = ve + (vw - ve) * t; x, y = xy(u, v); rm.Vertices.Add(float(x), float(y), float(roof_f(x, y)))
for i in range(len(_us) - 1):
    for j in range(_NV):
        a0 = i * (_NV + 1) + j; b0 = (i + 1) * (_NV + 1) + j
        rm.Faces.AddFace(a0, b0, b0 + 1, a0 + 1)
rm.Normals.ComputeNormals(); rm.Compact()
_ar = r.ObjectAttributes(); _ar.LayerIndex = lidx('20_'); keep.append((rm, _ar))
_n_def = 0                                         # 架構（押し出し）は fix_details.py の「屋根の面に合わせる」で動かす
_dmax = max(abs(roof_f(x, y) - float(_zo(x, y))) for x, y in np.asarray(WN.buffer(-50).exterior.coords) if np.isfinite(float(_zo(x, y))))
print('roof: level eave by the unrounded outline (corners %d), %d strips, frame verts moved %d, max change at the edge %.0f' % (len(_corners), len(_us) - 1, _n_def, _dmax))

new = r.File3dm()
new.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: new.Layers.Add(l)
for mt in m.Materials: new.Materials.Add(mt)
for g, a in keep: new.Objects.Add(g, a)
print('removed west wall sheet:', ztop_src is not None)

# 外壁の天端：元の面の天端を外周の長さ方向に補間
ring = WN.exterior
top = {}
for x, y, z in ztop_src:
    k = (round(x), round(y)); top[k] = max(top.get(k, -1e9), z)
S = np.array([ring.project(Point(k)) for k in top]); Z = np.array(list(top.values()))
o_ = np.argsort(S); S, Z = S[o_], Z[o_]
def ztop_old(x, y):
    q = ring.interpolate(ring.project(Point(x, y)))       # 10-24午後：外壁の天端は新しい屋根の面の縁（前は元の外壁の天端）
    q2 = WN.buffer(-30).exterior.interpolate(WN.buffer(-30).exterior.project(q))
    return float(roof_f(q2.x, q2.y))
# 屋根（20）の上面：WS が WN の外へ出た所は、屋根の面をそのまま延ばす（近くの屋根の点で平面を当てはめる）
L_ROOF = lidx('20_')
RP = np.vstack([np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
                for o in new.Objects for g in [o.Geometry] if o.Attributes.LayerIndex == L_ROOF and isinstance(g, r.Mesh)])
RPu = np.unique(np.round(RP), axis=0)
def roof_z(x, y, k=40):
    d = np.hypot(RPu[:, 0] - x, RPu[:, 1] - y); i = np.argsort(d)[:k]
    A = np.c_[RPu[i, 0] - x, RPu[i, 1] - y, np.ones(len(i))]
    c, *_ = np.linalg.lstsq(A, RPu[i, 2], rcond=None)
    return float(c[2])
def ztop(x, y):
    p = Point(x, y)
    if WN.exterior.distance(p) < 40 or WN.buffer(-40).contains(p): return ztop_old(x, y)
    q = WN.exterior.interpolate(WN.exterior.project(p))                 # 元の外壁の天端と屋根の差をそのまま保つ
    return roof_z(x, y) + (ztop_old(q.x, q.y) - roof_z(q.x, q.y))

# ---------------------------------------------------------------- 形の道具
def mesh_prism(poly, z0, zfun, li, col=None, name=None):
    """平面形 poly（穴あり可）を z0 から zfun(x,y) まで（天端は点ごと）"""
    polys = [poly] if poly.geom_type == 'Polygon' else list(poly.geoms)
    for p in polys:
        if p.area < 100: continue
        p = _orient(p.simplify(0.5), 1.0)          # 外の輪を左回りに（右回りだと立体が裏返しになっていた、10-25 監修）
        rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
        V2 = np.vstack(rings); n = len(V2)
        ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri = earcut.triangulate_float64(V2, ends).reshape(-1, 3)
        zt = np.array([zfun(x, y) for x, y in V2])
        if np.all(zt - z0 < 5): continue
        zt = np.maximum(zt, z0 + 5)
        mm = r.Mesh()
        for (x, y) in V2: mm.Vertices.Add(float(x), float(y), float(z0))
        for (x, y), z in zip(V2, zt): mm.Vertices.Add(float(x), float(y), float(z))
        for a, b, c in tri:
            mm.Faces.AddFace(int(a), int(c), int(b)); mm.Faces.AddFace(int(a + n), int(b + n), int(c + n))
        st = 0
        for e in ends:
            for i in range(st, e):
                j = i + 1 if i + 1 < e else st
                mm.Faces.AddFace(int(i), int(j), int(j + n), int(i + n))
            st = e
        mm.Normals.ComputeNormals(); mm.Compact()
        a = r.ObjectAttributes(); a.LayerIndex = li
        if name: a.Name = name
        if col is not None:
            a.ColorSource = r.ObjectColorSource.ColorFromObject; a.ObjectColor = (*col, 255)
        new.Objects.AddMesh(mm, a)

def flat(poly, z, li):
    polys = [poly] if poly.geom_type == 'Polygon' else list(poly.geoms)
    for p in polys:
        if p.area < 1e4: continue
        p = p.simplify(0.5)
        rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
        V2 = np.vstack(rings); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri = earcut.triangulate_float64(V2, ends).reshape(-1, 3)
        mm = r.Mesh()
        for (x, y) in V2: mm.Vertices.Add(float(x), float(y), float(z))
        for a, b, c in tri: mm.Faces.AddFace(int(a), int(b), int(c))
        mm.Normals.ComputeNormals(); mm.Compact()
        at = r.ObjectAttributes(); at.LayerIndex = li; new.Objects.AddMesh(mm, at)

def R(u0, u1, v0, v1, step=0.25):
    """(u, v) の長方形 → 世界座標の多角形（u の方向は弧に沿って細かく）"""
    us = np.linspace(u0, u1, max(2, int(abs(u1 - u0) / step) + 1))
    pts = [xy(u, v0) for u in us] + [xy(u, v1) for u in us[::-1]]
    return Polygon(pts).buffer(0)
const = lambda z: (lambda x, y: z)

# ---------------------------------------------------------------- 外壁（厚さ 150）と開口
T_W = 150.0
wall_ring = WS.difference(WS.buffer(-T_W, join_style=2))
# すき間の蓋（50a）の下端：西館の東の面の、ホールの範囲（u 21–30）
_lid = []
for o in m.Objects:
    if LN.get(o.Attributes.LayerIndex, '').startswith('50a') and isinstance(o.Geometry, r.Mesh):
        g = o.Geometry
        for i in range(len(g.Vertices)):
            p = g.Vertices[i]; uu, vv = uv(p.X, p.Y)
            if 21 < uu < 30 and -1.2 < vv < -0.4: _lid.append(p.Z)
ZLID_E = min(_lid) if _lid else 4400.0
FP_HALL = R(21.25, 33.0, -1.4, -0.5)          # 南の壁の角（u 21–21.15）は残す。10-27（ユーザー）：スパン11 も開け、キッチンの前からスパン11 まで本館へひと続きに開く（柱が見える）
HB_SILL = ZLID_E + 350.0; HB_HEAD = HB_SILL + 1200.0   # 東の高窓（蓋の上の外壁に横長の窓、はめ殺し）
FP_BAND = R(21.25, 50.75, -1.4, -0.5)          # 10-24（ユーザー）：東の面いっぱいの一本の帯（2階・遊戯室とも、遊戯室の東の高窓もこれにまとめた）
# 10-27夜：帯とホールの範囲の端を南北の妻の内面（u21.15・50.85）から 0.1 内へ（端が妻の内面と同じ面にあると、東の壁の内面が帯の上下で
# 幅 0 の所でつながり、Rhino版で面の輪郭が自分と交わって表示されなかった）
OPEN = [  # (足元の形, 下, 上)  上=None は天端まで
    (R(20.6, 21.4, -2.75, -0.95), 0, 2270),       # 入口の引き戸 1.8
    (R(20.6, 21.4, -4.4, -3.5), 450, 1050),       # 今日のごはんの窓（子どもの高さ）
    (R(20.6, 21.4, -9.6, -4.6), 800, 2270),       # キッチンの南のガラス
    (FP_HALL, 0, ZLID_E),                         # ホールの範囲：東の面はすき間の蓋の下まで開く（ひと続き）。蓋より上は外壁
    (FP_BAND, HB_SILL, HB_HEAD),                  # その上に東の面いっぱいの横長の高窓（本館の屋根越しに東の空）
    (R(28.5, 29.3, -14.5, -12.3), 0, 2100),       # 調理の職員の外からの戸（西の面）
]
# 勝手口（検収のすぐ外、南西の丸みの始まり、10-24昼：3dmに戸が抜けていた。上は下屋を回り込ませる＝アプローチ係へ依頼）
_rk = WS.exterior; _sk = _rk.project(Point(*xy(21.2, -10.95)))      # plan05 の勝手口（21.06,−10.49〜21.38,−11.41）と同じ
from shapely.ops import substring as _sub
KATTE = _sub(_rk, _sk - 500.0, _sk + 500.0).buffer(400.0, cap_style=2)      # 幅 1.0
OPEN.append((KATTE, 0, 2100))
# ---- 遊戯室の開口（data/play.json、遊戯室のスレッドの寸法）
import json, os
PJ = os.path.join(os.path.dirname(os.path.dirname(WNPKL)), 'data', 'play.json') if WNPKL.endswith('wnew.pkl') else None
PANES = []      # (足元の形, 下, 上, レイヤー)
def face_v(u):
    """u の放射線と西館の外形の、いちばん西の交点の v"""
    ln = LineString([xy(u, -0.9), xy(u, -30)]); x = ln.intersection(WS.exterior)
    pts = [x] if x.geom_type == 'Point' else list(getattr(x, 'geoms', []))
    return min(uv(p.x, p.y)[1] for p in pts)
if PJ and os.path.exists(PJ):
    P = json.load(open(PJ, encoding='utf-8'))
    _nm = P['north_mouth']; OPEN.append((R(_nm['u0'], _nm['u1'], -1.4, -0.5), 0, 2400))   # 遊戯室の口②（10-24：柱 u45・48 のあいだ）
    for a, b in GAP_P:                                               # すき間の倉庫（遊戯室の側）の口（10-25、柱 u42・45 を避ける）
        OPEN.append((R(a, b, -1.4, -0.5), 0, 2100))
    for a, b in [(36.4, 39.0), (39.6, 41.8), (47.0, 49.6)]:        # 東の壁：覗き窓（キャットウォークの高さ）と東の高窓（同じ柱の間と仮定）
        for k in ('east_peek',) + (() if P['east_high'].get('band') else ('east_high',)):
            fp = R(a, b, -1.4, -0.5); OPEN.append((fp, P[k]['h0'] * 1000, P[k]['h1'] * 1000)); PANES.append((fp, P[k]['h0'] * 1000, P[k]['h1'] * 1000, L_GL))
    nw = P['north_window']                                           # 北の窓辺（読書の庭のモミジを見る）
    fp = R(50.3, 51.8, -0.9 - nw['w1'], -0.9 - nw['w0']); OPEN.append((fp, nw['h0'] * 1000, nw['h1'] * 1000)); PANES.append((fp, nw['h0'] * 1000, nw['h1'] * 1000, L_GL))
    N_ = P['niche']
    for ua, ub in P['niches']:                                       # ひだ：くぼみの奥の覗き窓
        pc = (ua + ub) / 2; vf = face_v(pc)
        fp = R(pc - N_['peek'][2] / 2, pc + N_['peek'][2] / 2, vf - 0.6, vf + 0.6)
        OPEN.append((fp, N_['peek'][0] * 1000, N_['peek'][1] * 1000)); PANES.append((fp, N_['peek'][0] * 1000, N_['peek'][1] * 1000, L_GL))
    for (a0, a1), (b0, b1) in zip(P['niches'], P['niches'][1:]):       # くぼみのあいだの柱の両脇に地窓
        c = (a1 + b0) / 2; vf = face_v(c)
        for u0_, u1_ in ((c - 0.45, c - 0.15), (c + 0.15, c + 0.45)):
            fp = R(u0_, u1_, vf - 0.6, vf + 0.6); OPEN.append((fp, 50, N_['jimado_h'] * 1000)); PANES.append((fp, 50, N_['jimado_h'] * 1000, L_GL))
    # 搬入の大戸：北西の斜めの面、u 45 と u 48 の西の柱のあいだ、幅 3.6×h3.0
    cols = []
    for o in m.Objects:
        if LN.get(o.Attributes.LayerIndex, '').startswith('22a'):
            bb = o.Geometry.GetBoundingBox(); cx_, cy_ = (bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2
            cols.append((uv(cx_, cy_), np.array([cx_, cy_])))
    pick = []
    for uc in P['big_door']['u_cols']:
        cand = [c for c in cols if abs(c[0][0] - uc) < 0.8]
        if cand: pick.append(min(cand, key=lambda c: c[0][1])[1])
    if len(pick) == 2:
        mid = (pick[0] + pick[1]) / 2; d = (pick[1] - pick[0]) / np.linalg.norm(pick[1] - pick[0])
        hw = P['big_door']['width'] * 500; hh = P['big_door']['height'] * 1000
        # 開口は外皮（WS）の壁に。柱の線から外へ約0.7出た壁まで、足元の形で覆う
        fp = LineString([mid - d * hw, mid + d * hw]).buffer(1500, cap_style=2)
        OPEN.append((fp, 0, hh))
        # 外付けの引き戸 2 枚（10-23、監修の提案：外開きだと扉の先が北西の道路に出る＝建築基準法44条）。閉じた状態を描く
        nrm = np.array([-d[1], d[0]])
        if WS.contains(Point(*(mid + nrm * 2000))): nrm = -nrm                   # 外向き
        hit = LineString([mid, mid + nrm * 4000]).intersection(WS.exterior)
        t_out = min(np.linalg.norm(np.array(g.coords[0]) - mid) for g in getattr(hit, 'geoms', [hit]))
        lw = P['big_door'].get('leaf', 1.85) * 1000; tl = 40.0; gap = 30.0
        for sgn in (-1, 1):                                                        # 戸 2 枚（真ん中で合わさる）
            a_ = mid + d * sgn * 0.0; b_ = mid + d * sgn * lw
            leaf = LineString([a_, b_]).buffer(tl / 2, cap_style=2)
            leaf = affinity.translate(leaf, *(nrm * (t_out + gap + tl / 2)))
            mesh_prism(leaf, 0.0, const(hh + 50.0), L_DOOR)
        rail = affinity.translate(LineString([mid - d * (hw + 3700 - 1800), mid + d * (hw + 3700 - 1800)]).buffer(60, cap_style=2), *(nrm * (t_out + 70)))
        mesh_prism(rail, hh + 50.0, const(hh + 200.0), L_DOOR, (90, 90, 90))      # 上の吊りレール（引きしろ 1.8 ずつ）
        print('big door between columns', [tuple(np.round(uv(*p), 2)) for p in pick], 'wall out %.2f' % (t_out / 1000))
# ---------------------------------------------------------------- 外への窓（10-26、ユーザー・監修：外壁と窓）
# 窓に格子は付けない。面ごとのリズムで：キッチンは架構の間に一つずつ同じ窓、遊戯室は中の遊びの高さに合わせて散らす（ちょっとランダム）、
# 2 階は横一文字（西の低い軒の壁に一本の帯、休憩室の南の妻は座った目の高さ）。道に面するガラスは室内から拭ける開き方（引き違い・内倒し）。
_RK = WS.exterior
def _s_of(u):
    return _RK.project(Point(*xy(u, face_v(u))))
def win_u(u0, u1, z0, z1, name=None):
    """西・北西の面（u の範囲）の窓：外周に沿う帯を足元の形に"""
    a_, b_ = sorted((_s_of(u0), _s_of(u1)))
    if b_ - a_ > _RK.length / 2:                                    # 外周の始まり（u約41）をまたぐ
        fp = unary_union([_sub(_RK, b_, _RK.length).buffer(400.0, cap_style=2), _sub(_RK, 0.0, a_).buffer(400.0, cap_style=2)])
    else:
        fp = _sub(_RK, a_, b_).buffer(400.0, cap_style=2)
    OPEN.append((fp, z0, z1)); PANES.append((fp, z0, z1, L_GL, name)); return fp
def win_gable(u_face, v0, v1, z0, z1, name=None):
    """南北の妻（u 一定の面）の窓"""
    fp = R(u_face - 0.4, u_face + 0.4, min(v0, v1), max(v0, v1), 0.05)
    OPEN.append((fp, z0, z1)); PANES.append((fp, z0, z1, L_GL, name)); return fp
WIN_LOG = []
def _w(kind, *a, name=None):
    (win_u if kind == 'u' else win_gable)(*a, name=name); WIN_LOG.append((kind, a))
ZF2_ = 3250.0
# キッチン（西の面、スパン 24〜27）：作業台の上 h1.0〜2.0、幅 2.2（引き違い）。南西の丸みの先 u22.6〜23.9 にも同じ高さの細い窓
_w('u', 24.4, 26.6, 1000.0, 2000.0)
_w('u', 22.7, 23.7, 1000.0, 2000.0)
# 調理の更衣・便所（u27〜30、職員の戸の南）：目隠しの高い窓 h1.6〜2.1、幅 0.6
_w('u', 27.5, 28.1, 1600.0, 2100.0)
# 遊戯室（西の面と北西の面、北の妻）：ちょっとランダム。くぼみの覗き窓・地窓（play.json）に足して、遊びの高さに合わせて散らす
_w('u', 30.7, 31.5, 300.0, 900.0)        # 洞（2 階の床の下）の低い窓：床に座った子の目
_w('u', 34.2, 35.1, 2100.0, 2900.0)      # くぼみ 1 の上：大人の目の上、空
_w('u', 36.3, 36.75, 1300.0, 2700.0)     # 縦長の細い窓（くぼみ 1 と 2 のあいだの柱の北）
_w('u', 37.7, 38.3, 1500.0, 2100.0)      # くぼみ 2 の上：立った子の目
_w('u', 39.8, 41.1, 2500.0, 3300.0)      # くぼみ 3 の上：高い窓（午後の光）
_w('u', 42.5, 43.7, 450.0, 1050.0)       # 丸いベンチ（u42.15〜44）に座った目
_w('u', 49.0, 49.9, 2300.0, 3000.0)      # 踊り場（h2.0）の子の目：北西の道を見下ろす
_w('g', 51.0, -0.9 - 3.6, -0.9 - 4.8, 2150.0, 3100.0)   # 北の妻：吊り橋・段（h2〜3）から北の庭（水切り h3.25 の下に収める）
# 2 階：横一文字。西の低い軒の壁（2FL+0.4〜+0.8）に休憩室・更衣・会議室を通す一本の帯（架構の線の柱の所で区切る）
# 10-28（ユーザー、監修の項 20261028-0015 の 9）：腰が低い（400・800、1,100 未満）ので、柵は付けずに開き方を限る（見えは変えない）。
# 内倒し窓（室内から拭ける）でストッパーにより開く幅を 100 mm 未満に（こどもが体を出せない）。3dm の形は閉じた姿のまま、名前で示す。
# 2 階は職員だけの所だが、こどもが上がることもあるので同じにする。
WIN2_NAME = '2階の外への窓（腰 %d、内倒し・ストッパーで開く幅 100 mm 未満、柵なし、10-28 監修の項 0015 の 9）'
for a_, b_ in ((22.75, 23.88), (24.12, 26.88), (27.12, 29.88), (30.12, 32.88)):
    _w('u', a_, b_, ZF2_ + 400.0, ZF2_ + 800.0, name=WIN2_NAME % 400)
# 休憩室の南の妻：座った目の高さ（2FL+0.8〜+1.3）で川と空を見る横長の窓（腰 800 なので同じく開く幅を限る）
_w('g', 21.0, -2.9, -9.0, ZF2_ + 800.0, ZF2_ + 1300.0, name=WIN2_NAME % 800)
print('windows (10-26):', len(WIN_LOG))
# ---------------------------------------------------------------- 外皮が架構の輪郭（WN）より外へ出た所：屋根を延ばし、床を足す（10-23、西館係）
EXT = WS.difference(WN).buffer(-1).buffer(1)
def surf(poly, zfun, li, col=None):
    for p in ([poly] if poly.geom_type == 'Polygon' else list(poly.geoms)):
        if p.area < 1e4: continue
        p = Polygon(np.asarray(p.exterior.coords)).buffer(0).segmentize(250)
        V2 = np.asarray(p.exterior.coords)[:-1]; tri = earcut.triangulate_float64(V2, np.array([len(V2)], dtype=np.uint32)).reshape(-1, 3)
        mm = r.Mesh()
        for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zfun(x, y)))
        for a, b, c in tri: mm.Faces.AddFace(int(a), int(b), int(c))
        mm.Normals.ComputeNormals(); mm.Compact()
        at = r.ObjectAttributes(); at.LayerIndex = li
        if col is not None: at.ColorSource = r.ObjectColorSource.ColorFromObject; at.ObjectColor = (*col, 255)
        new.Objects.AddMesh(mm, at)
if EXT.area > 1e5:
    surf(EXT.buffer(20).intersection(WS), roof_f, L_ROOF)                       # 屋根の面の式をそのまま延ばす（重なり 20、10-27夜：前は近くの点に当てはめた面で、屋根の式から最大約10 cm ずれた）
    flat(EXT.buffer(20).intersection(WS), 10, lidx('31_'))                      # 遊戯室の床の板
    print('skin beyond WN: %.2f m2, roof z at the new eave %.0f' % (EXT.area / 1e6, min(roof_z(*c) for c in np.asarray(EXT.exterior.coords))))
# 外壁（21）は一つの閉じた立体（10-27夜、三代目の西館係。ユーザー：Rhino のレイトレースで北の妻に段差や穴ぼこ、シェーディングで北と西の壁が消える）。
# 前は、開口の足元ごとに外壁の輪を片に切り、高さごとの角柱を積んでいた。片ごとに輪郭を簡略化（0.5）していたので、となりの片との境が
# 1 mm 未満ずれ、削る段で足し合わせると細い隙間・厚さの無い三角形・3 枚以上の面が集まる辺が残った（北・西・南の面で 47 本）。
# Rhino版にすると、同じ平面の三角形をまとめた面の輪郭が自分と交わり（穴の角と外の縁が一点で触れる）、Rhino が面を表示できなかった。
# 今：外壁の輪を床から天端まで一つの角柱にし、開口（足元の形×高さ）をまとめて引き、水切り・すき間の北の端の壁を足した一つの立体にする
# （manifold3d、原点を近くに移して float32 の桁落ちを避ける）。形は前と同じ。
import manifold3d as _mf
WALL_ADD, WALL_SUB = [], []
_O = np.array(WS.centroid.coords[0])
def prism_vf(poly, z0, zfun, seg=None):
    """平面形（穴あり可）を z0 から zfun(x, y) まで、閉じた角柱の (V, F) の列（V は _O を原点に）"""
    out_ = []
    for p in ([poly] if poly.geom_type == 'Polygon' else [g for g in getattr(poly, 'geoms', []) if g.geom_type == 'Polygon']):
        if p.area < 100: continue
        p = _orient(p.simplify(0.2), 1.0)
        if seg: p = p.segmentize(seg)
        def _dedup(c):                              # 3 mm より近い続きの点は一つに（外周の始まり u41 などで 1 mm の細い面が残っていた）
            c = np.asarray(c)[:-1]; k = [0]
            for i in range(1, len(c)):
                if np.linalg.norm(c[i] - c[k[-1]]) >= 3.0: k.append(i)
            if len(k) > 1 and np.linalg.norm(c[k[-1]] - c[k[0]]) < 3.0: k.pop()
            return c[k]
        rings = [_dedup(p.exterior.coords)] + [_dedup(h.coords) for h in p.interiors]
        V2 = np.vstack(rings); n = len(V2)
        ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri = earcut.triangulate_float64(V2 - _O, ends).reshape(-1, 3)
        if len(tri) != n - 2 + 2 * (len(rings) - 1): raise RuntimeError('外壁の片の三角分けが欠けた（%d / %d）' % (len(tri), n - 2 + 2 * (len(rings) - 1)))
        zt = np.maximum(np.array([zfun(x, y) for x, y in V2]), z0 + 5)
        V = np.vstack([np.c_[V2 - _O, np.full(n, z0)], np.c_[V2 - _O, zt]])
        F = [tri[:, [0, 2, 1]], tri + n]
        st = 0
        for e in ends:
            i = np.arange(st, e); j = np.r_[i[1:], st]
            F += [np.c_[i, j, j + n], np.c_[i, j + n, i + n]]; st = e
        out_.append((V, np.vstack(F).astype(np.uint32)))
    return out_
def _man(vf):
    V, F = vf
    M = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(V, np.float32), tri_verts=np.asarray(F, np.uint32)))
    if M.status() != _mf.Error.NoError or M.is_empty(): raise RuntimeError('外壁の片が閉じていない')
    if M.volume() < 0: raise RuntimeError('外壁の片が裏返し')
    return M
WALL_ADD += prism_vf(wall_ring, 0.0, ztop)      # 細かく分けない（細い輪で一直線に並んだ点があると earcut が三角を落とす）
for fp, zb, zt in OPEN:                       # 足元が床（0）の開口は床の下まで、天端まで（None）の開口は屋根の上まで引く
    z0_ = -200.0 if zb <= 0 else float(zb); z1_ = 20000.0 if zt is None else float(zt)
    WALL_SUB += prism_vf(fp.intersection(WS.buffer(200.0)), z0_, const(z1_))
# 水切り（10-26 2時、ユーザー・監修）：大和張りは縦の長尺（〜6 m）で継がず、押縁もやめた（重なりが継ぎ目を覆うので押縁は飾りになる）。
# 6 m を超える南北の妻だけ、2 階の床の高さに水切りを一本（壁から 30 出る薄い板 t20、妻の幅いっぱい、外皮）
_ring_out = WS.buffer(30.0, join_style=2).difference(WS).buffer(1.0, join_style=2)     # 外壁の外面に 1 食い込ませて一つの立体に
# 端は角の丸みの終わり（まっすぐな壁に移る所）まで回す（10-26 監修：前は丸みの途中 u21.05・v−7.2 で切れ、立面で壁の途中で止まって見えた）。
# 南：u21 の妻 → 丸み → 西の壁に移る (u23.65, v−12.92)。北：u51 の妻 → 丸み → 北西の斜めの壁に移る (u50.08, v−7.68)
# 10-28（監修の項 20261028-0015 の 12）：丸みの終わりで水切りの 30 が道路側の 1 m の線（＝西・北西のまっすぐな外壁の外面の延長）を越えていた
# （u23.65 v−12.95、u50.11 v−7.70）。その線の内側で切る。
def _inside_of(p0, p1):
    p0 = np.array(xy(*p0), float).ravel(); p1 = np.array(xy(*p1), float).ravel(); d_ = (p1 - p0) / np.linalg.norm(p1 - p0); n_ = np.array([-d_[1], d_[0]])
    if not WS.contains(Point(*((p0 + p1) / 2 + n_ * 500))): n_ = -n_
    a_, b_ = p0 - d_ * 30000, p1 + d_ * 30000
    return Polygon([a_, b_, b_ + n_ * 60000, a_ + n_ * 60000])
_LINE_W = _inside_of((23.654, -12.919), (40.554, -14.983)); _LINE_NW = _inside_of((43.913, -14.188), (50.085, -7.675))
for box_ in (R(20.9, 23.65, -13.1, -0.92, 0.05), R(50.08, 51.1, -7.9, -0.92, 0.05)):
    WALL_ADD += prism_vf(_ring_out.intersection(box_).intersection(_LINE_W).intersection(_LINE_NW), 3250.0, const(3270.0))
def emit_wall():
    """外壁の立体を一つにまとめて 21 に書く（すき間の北の端の壁を足した後に呼ぶ）"""
    A_ = _mf.Manifold.batch_boolean([_man(x) for x in WALL_ADD], _mf.OpType.Add)
    S_ = _mf.Manifold.batch_boolean([_man(x) for x in WALL_SUB], _mf.OpType.Add) if WALL_SUB else None
    W_ = A_ - S_ if S_ is not None else A_
    if W_.status() != _mf.Error.NoError or W_.is_empty(): raise RuntimeError('外壁の立体が作れなかった')
    g_ = W_.to_mesh(); V_ = np.asarray(g_.vert_properties)[:, :3].astype(float); F_ = np.asarray(g_.tri_verts)
    mm = r.Mesh()
    for x_, y_, z_ in V_: mm.Vertices.Add(float(x_ + _O[0]), float(y_ + _O[1]), float(z_))
    for a_, b_, c_ in F_: mm.Faces.AddFace(int(a_), int(b_), int(c_))
    mm.Normals.ComputeNormals(); mm.Compact()
    at = r.ObjectAttributes(); at.LayerIndex = L_WALL; new.Objects.AddMesh(mm, at)
    print('west wall: one solid, %d tris, %.2f m3, genus %d (openings %d)' % (len(F_), W_.volume() / 1e9, W_.genus(), len(WALL_SUB)))

# ガラス・建具（厚さ 30、壁の中ほど）
def pane_u(u, v0, v1, z0, z1, t=0.03):
    mesh_prism(R(u - t / 2, u + t / 2, v0, v1, 0.02), z0, const(z1), L_GL)
uS = 21.0 + 0.075 / 1.0 * 1.0   # 南の面の壁の中（外面 u=21、厚さ 150 → 中心 u≈21.075）
pane_u(21.06, -1.90, -0.95, 0, 2270); pane_u(21.10, -2.75, -1.80, 0, 2270)   # 引き戸 2 枚
pane_u(21.075, -4.4, -3.5, 450, 1050)                                         # 今日のごはんの窓
pane_u(21.075, -9.6, -4.6, 800, 2270)                                         # キッチンの南のガラス
# 遊戯室の窓・大戸：壁の厚さの中ほどの薄い板
PANES.append((FP_BAND, HB_SILL, HB_HEAD, L_GL))
PANES.append((R(28.5, 29.3, -14.5, -12.3), 0, 2100, L_WD))     # 調理の職員の外からの戸（開口だけで戸が無かった）
print('hall face: open to lid', round(ZLID_E), 'high window', round(HB_SILL), round(HB_HEAD))
mid_ring = WS.buffer(-60, join_style=2).difference(WS.buffer(-90, join_style=2))
for pn in PANES:
    fp, z0, z1, li = pn[:4]
    mesh_prism(mid_ring.intersection(fp), float(z0), const(float(z1)), li, name=pn[4] if len(pn) > 4 else None)
# すき間の南の端のガラス：海峡の床 −150 から すき間の蓋の下まで
lid = []
for o in new.Objects:
    if LN.get(o.Attributes.LayerIndex, '').startswith('50a') and isinstance(o.Geometry, r.Mesh):
        g = o.Geometry
        for i in range(len(g.Vertices)):
            p = g.Vertices[i]; uu, vv = uv(p.X, p.Y)
            if 19.5 < uu < 23 and -1.2 < vv < 0.3: lid.append(p.Z)
zlid = min(lid) if lid else 4200.0
pane_u(21.0, -0.85, -0.15, -150, zlid)
print('gap glass top', round(zlid))
# すき間の北の端を閉じる（設計監修 10-25、ユーザー：本館と西館のあいだの外壁のすき間を断熱気密の観点から）。
# すき間は室内（換気の道・倉庫、蓋は西館の壁まで届いている）なのに、北の端 u51 が床から蓋の下まで開いていた（幅 0.55、高さ 約4.5）。
# 西館の北の外壁（外面 u51.0、厚さ 150）を本館の西の外壁の外面（v −0.35）の 10 手前まで延ばす（10 は伸縮の目地：西館に留め、
# 本館の側は気密の伸縮目地＋目地カバーで、二つの建物が別に動いてよい）。北は寒い側で見せる必要もないので、ガラスでなく断熱した外壁にした。
lidN = []
for o in new.Objects:
    if LN.get(o.Attributes.LayerIndex, '').startswith('50a') and isinstance(o.Geometry, r.Mesh):
        g = o.Geometry
        for i in range(len(g.Vertices)):
            p = g.Vertices[i]; uu, vv = uv(p.X, p.Y)
            if 49.0 < uu < 52.5 and -1.2 < vv < 0.3: lidN.append(p.Z)
zlidN = min(lidN) if lidN else zlid
# 外面は北の妻の外面（WS の北の辺）の延長にぴったり（前の R(50.85, 51.0) は妻の外面と 0.1 mm ずれて細い面が残った）。西館の東の壁に 20 食い込ませる
_gn = np.array([c for c in WS.exterior.coords if abs(uv(*c)[0] - 51.0) < 0.01])
_ga, _gb = _gn[np.argmax(np.array([uv(*c)[1] for c in _gn]))], _gn[np.argmin(np.array([uv(*c)[1] for c in _gn]))]
_gd = (_ga - _gb) / np.linalg.norm(_ga - _gb); _gin = np.array(xy(50.0, uv(*_ga)[1])) - _ga; _gin = _gin - _gd * (_gin @ _gd); _gin /= np.linalg.norm(_gin)
def _gat(vt):                                    # 北の辺の延長の上で v = vt の点
    lo, hi = -3000.0, 3000.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if uv(*(_ga + _gd * mid))[1] < vt: lo = mid
        else: hi = mid
    return _ga + _gd * lo
_g0, _g1 = _gat(-0.92), _gat(-0.36)
WALL_ADD.extend(prism_vf(Polygon([_g0, _g1, _g1 + _gin * T_W, _g0 + _gin * T_W]), 0.0, const(zlidN)))
print('gap north wall top', round(zlidN))
emit_wall()

# ---------------------------------------------------------------- 床
WNi = WN.buffer(-T_W, join_style=2)
KN = 27.25                     # キッチンの北の壁（60.5 m²）
CB = -11.1                     # 調理の職員の更衣・便所・前室：はれのまの西の端、v −11.1 から西の面まで（外から直接）
flat(R(21, KN, -20, -3.4).intersection(WN), 10, L_KIT)          # 面積は外形で（plan05 と同じ）
cook = R(KN, 30, -20, CB).intersection(WN)
store = R(KN + 0.06, 30 - 0.06, CB + 0.06, CB + 0.6)                # はれのまの収納（西の端の壁、奥行き 0.6。まわりの壁の芯の半分＝60を避ける、監修10-24の4）
flat(cook, 10, L_COOK)
flat(R(KN, 30, CB, -3.4).intersection(WN).buffer(-5).buffer(5), 10, L_HARE)
flat(unary_union([R(22.5, 30, -3.4, -0.9).intersection(WN), R(22.5, 30, -0.9, -0.2), R(30.0, 33.0, -0.9, -0.35)]).buffer(1).buffer(-1), 10, L_BAND)   # 10-27：スパン11 のすき間の床（本館の先生の道から南の口へ）
# 海峡を東の帯の南端まで（土足 −150、床の板は −450〜−150）
mesh_prism(unary_union([R(21, 22.5, -3.4, -0.9).intersection(WN), R(21, 22.5, -0.9, -0.2)]), -450.0, const(-150.0), L_STR)
mesh_prism(R(22.45, 22.55, -3.4, -0.2, 0.05), -150.0, const(0.0), L_KAMA, (150, 110, 70))   # 框

# ---------------------------------------------------------------- 間仕切り（厚さ 100、h3100）
H = 3170.0                     # 2 階の床の下まで（キッチン・はれのま・更衣、音も切る）
# 10-28（監修の項 20261028-0843、ユーザー：大きい・メッシュなのは間違っている印）：壁ごとに「平面の輪郭を床から H まで押し出した角柱 − 開口」の
# 一つの閉じた立体に（外壁 21 と同じ作り方、manifold3d、原点を _O へ移して float32 の桁落ちを避ける）。前は開口の上下・脇ごとの片
# （厚さ 100）を積んでいて、削る段で一つに足すと片の継ぎ目に 4 枚の面が集まる辺が残り、Rhino版で 1.8 万面のメッシュになっていた。
# 厚さは間仕切りの構法の 120（walls_spec.py が 100 → 120 にしていた。芯はそのまま、形は前と同じ）。開口の箱は壁の面から 0.1 外まで、
# 床からの開口は床の 200 下から（壁の面・底とちょうど同じ所に置かない）。弧に沿う壁の点は約 1 m ごと（弧とのずれ 0.6 mm 以下）。
T_P = 120.0
def _Rb(u0, u1, v0, v1, breaks=(), step=1.0):
    """R と同じ（u の方向は弧に沿う）。点は u0・u1・breaks と約 step ごと"""
    us = sorted(set([u0, u1] + list(np.linspace(u0, u1, max(2, int(math.ceil(abs(u1 - u0) / step)) + 1))) +
                    [b for b in breaks if min(u0, u1) < b < max(u0, u1)]))
    return Polygon([xy(u, v0) for u in us] + [xy(u, v1) for u in us[::-1]]).buffer(0)
def _emit_part(add_, sub_, li=None, name=None):
    """角柱の (V, F) の組 add_ から sub_ を引いた一つの立体を li に書く"""
    A_ = _mf.Manifold.batch_boolean([_man(x) for x in add_], _mf.OpType.Add)
    W_ = A_ - _mf.Manifold.batch_boolean([_man(x) for x in sub_], _mf.OpType.Add) if sub_ else A_
    if W_.status() != _mf.Error.NoError or W_.is_empty(): raise RuntimeError('間仕切りの立体が作れなかった')
    g_ = W_.to_mesh(); V_ = np.asarray(g_.vert_properties)[:, :3].astype(float); F_ = np.asarray(g_.tri_verts)
    mm = r.Mesh()
    for x_, y_, z_ in V_: mm.Vertices.Add(float(x_ + _O[0]), float(y_ + _O[1]), float(z_))
    for a_, b_, c_ in F_: mm.Faces.AddFace(int(a_), int(b_), int(c_))
    mm.Normals.ComputeNormals(); mm.Compact()
    at = r.ObjectAttributes(); at.LayerIndex = L_PART if li is None else li
    if name: at.Name = name
    new.Objects.AddMesh(mm, at); _NPART.append(len(F_))
_NPART = []
def _hole_vf(fp, zb, zt):
    return prism_vf(fp, -200.0 if zb <= 0 else float(zb), const(H + 200.0 if zt >= H else float(zt)))
def wall_u(u, v0, v1, holes=()):
    """u 一定（放射方向の直線）の壁。holes=[(v0, v1, zb, zt)]"""
    fp = R(u - T_P / 2000, u + T_P / 2000, min(v0, v1), max(v0, v1), 0.02).intersection(WNi)
    sub_ = [x for h in holes for x in _hole_vf(R(u - 0.16, u + 0.16, min(h[0], h[1]), max(h[0], h[1]), 0.02), h[2], h[3])]
    _emit_part(prism_vf(fp, 0.0, const(H)), sub_)
def wall_v(v, u0, u1, holes=()):
    """v 一定（弧に沿う）の壁。holes=[(u0, u1, zb, zt)]"""
    fp = _Rb(u0, u1, v - T_P / 2000, v + T_P / 2000).intersection(WNi)       # 点を開口の端に置かない（開口の脇の面が輪郭の折れの線と重なると、立体の頂点が二重になる）
    sub_ = [x for h in holes for x in _hole_vf(_Rb(h[0], h[1], v - 0.16, v + 0.16), h[2], h[3])]
    _emit_part(prism_vf(fp, 0.0, const(H)), sub_)
# 10-27（構造の直し、監修の略算）：架構 u24・u27 のキッチンの東の壁の線に 2 階の床梁を受ける骨格の柱（180×400、fix_details.py）。
# 配膳口・返却口・受け取り台を柱を避けて割り直した（配膳口 1.6 → 1.15、返却口 0.8 → 0.8、受け取り台 0.65 のまま、ガラス 1.1 → 1.05）。
GLK = [(21.3, 22.6), (24.15, 25.2), (26.2, 26.85)]                                 # オープンキッチン：低い位置（h450）からのガラス
# 階段の登り口（10-27、ユーザー）：スパン11 を本館の先生の道へ開け、階段は南の口の通路の側（箱の東の面）から入る（fix_details.py）。
# はれのまの角を欠いた溜まり（10-27朝）はやめて元の長方形に戻した。
wall_v(-3.4, 21.0, 30.0, [(22.7, 23.85, 850, 1900), (25.3, 26.1, 850, 1900),       # 配膳口・返却口
                          (27.65, 28.65, 0, 2100)] + [(a, b, 450, 2270) for a, b in GLK])   # はれのまの戸
for a, b in GLK:
    mesh_prism(R(a, b, -3.415, -3.385, 0.05), 450.0, const(2270.0), L_GL)
wall_u(KN, -3.4, -20, [(-7.8, -9.6, 850, 1900), (-11.25, -11.95, 0, 2100)])        # 見える台所・前室 → キッチン
wall_u(30.0, -3.4, -20)                                                             # はれのま｜遊戯室（2 階の床の下まで）
wall_v(CB, KN, 30.0)                                                                # はれのま｜更衣・前室・便所
wall_u(28.25, CB, -20, [(-11.3, -11.95, 0, 2100), (-12.4, -12.95, 0, 2100)])       # 前室・便所｜更衣
wall_v(-12.2, KN, 28.25)                                                            # 前室｜便所
print('partitions (24): %d walls, one solid each, %d tris' % (len(_NPART), sum(_NPART)))
mesh_prism(store.intersection(WNi), 0.0, const(2100.0), L_FURN, (210, 190, 160))   # はれのまの収納（延長の箱・季節の棚）
mesh_prism(R(KN + 0.07, KN + 0.47, -10.4, -3.6, 0.05), 0.0, const(600.0), L_FURN, (196, 160, 110))   # カウンター h600（子どもの流し・おやつの台）
mesh_prism(R(26.2, 26.85, -3.38, -2.98, 0.05), 0.0, const(500.0), L_FURN, (196, 160, 110))   # 生ごみの受け取り台 h500（返却口の北隣、東の帯の側。3〜5歳のコンポスト当番）

# ---------------------------------------------------------------- スパン 7：医務・框（中身は add_hall.py）
def mesh_poly(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y] for i in range(len(g.Vertices))])
    ps = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; ps.append(Polygon(V[[f[0], f[1], f[2]]]).buffer(0))
    return unary_union([p.buffer(1) for p in ps if p.area > 0]).buffer(-1)
for g in WV:                                   # 西吹き抜けの板からスパン 7 を抜く
    flat(mesh_poly(g).difference(R(18.0, 21.0, -0.3, 1.9)), 10, L_WV)
# 事務の板・おはようの窓口のカウンター・飛び石は add_hall.py の「スパン 7」の節で作る（窓口の帯 v 0–1.6・静養室 v 1.6–4.5、本館係 10-23夜）
flat(R(18.0, 21.0, 4.5, 12.0), 10, L_MED)
mesh_prism(R(20.95, 21.05, 4.5, 12.0, 0.02), 0.0, const(2400.0), L_KAMA)            # 医務｜海峡の壁
mesh_prism(R(20.95, 21.05, 0.0, 4.5, 0.02), -150.0, const(0.0), L_KAMA, (150, 110, 70))   # 框 150（海峡 −150 → ±0）
for a_, b_ in ((18.0, 19.0), (20.4, 21.0)):                                         # 静養室｜医務（引き込み戸 u 19.0–20.4）
    mesh_prism(R(a_, b_, 4.45, 4.55), 0.0, const(2400.0), L_KAMA)
mesh_prism(R(19.0, 20.4, 4.45, 4.55), 2100.0, const(2400.0), L_KAMA)

# ---------------------------------------------------------------- 西の軒の出と軒樋・鎖樋（10-24昼、ユーザー：西は庇が無い、0.9出す）
# 屋根は東 8.15 → 外周 4.65 へ流れ、低い縁（西の面・南西と北西の丸み・北西の斜めの面）から落ちる。
# 低い縁に軒の出 0.9（軒樋を含む：屋根の面 0.78＋軒樋 0.12）、南北の妻の縁（けらば）に 0.3。あいだは屋根の高さで滑らかにつなぐ。
# 軒先は敷地の境の 0.1 手前で止める（外壁は壁面後退の線＝道路から1.0 の上）。本館の側（東の面）には出さない（すき間 0.55）。
# 屋根の面は外皮の縁から外へ、近くの屋根の点で当てはめた面をそのまま延ばす（roof_z）。
# 軒樋（120×150、軒先の内側に収める）は低い縁の全長。鎖樋は 2 本：北＝西の面のまっすぐな所の北の端（北の雨庭）、南＝勝手口の北の端から約0.5北の軒先（回り込んだ下屋の上に落とし、下屋の集水から雨水樽へ、10-24）。
from shapely.ops import substring
_site = sorted([Polygon([[g.Point(i).X, g.Point(i).Y] for i in range(g.PointCount)]) for o in m.Objects
                for g in [o.Geometry] if m.Layers[o.Attributes.LayerIndex].Name.startswith('00') and isinstance(g, r.PolylineCurve)],
               key=lambda q: -q.area)[0]
EAVE_LOW, EAVE_RAKE, GUT_W = 900.0, 300.0, 120.0
Z_LOW, Z_RAKE = 4760.0, 5100.0                 # 縁の屋根の高さ：これより低い所は軒、高い所はけらば、あいだは比例
ringS = WS.exterior
ring_ccw = ringS if Polygon(ringS).exterior.is_ccw else LineString(list(ringS.coords)[::-1])
Ls = ring_ccw.length; NS = int(Ls / 100.0)
# 北西の角（u42〜51）の軒先（10-27夜、ユーザー：実際に作る時もまっすぐの材で近似する、軒の高さは一定に）：屋根の線（架構の線と u43.5 の登り梁）を
# 軒の点から外へ同じ割合だけ延ばした点（＝同じ高さ）を、まっすぐな水平の線で結ぶ。軒の出は西の面の 0.78 から北の妻へ細くなり、けらばの 0.3 に続く。
_BAYS = _RW['BAYS']; _BL = {u_: _RW['beam_line'](u_) for u_ in _BAYS}
_L42 = np.linalg.norm(_BL[42.0][1] - _BL[42.0][0]); _HT = 1.0 + (EAVE_LOW - GUT_W) / _L42          # 西の面の軒の出（屋根の面 0.78）と同じ高さ
_CH = [_BL[u_][0] + _HT * (_BL[u_][1] - _BL[u_][0]) for u_ in _BAYS]
_rake = WS.buffer(EAVE_RAKE, join_style=2).exterior                          # 北の妻のけらばの線（妻の外面の 0.3 外）
_d_ = (_CH[-1] - _CH[-2]) / np.linalg.norm(_CH[-1] - _CH[-2])
_hk = LineString([_CH[-1], _CH[-1] + _d_ * 3000.0]).intersection(_rake)
_hk = [_hk] if _hk.geom_type == 'Point' else list(getattr(_hk, 'geoms', []))
if _hk: _CH = _CH[:-1] + [min((np.array([q.x, q.y]) for q in _hk), key=lambda q: np.linalg.norm(q - _CH[-2]))]
CHORD = LineString(_CH)
print('NW eave: level straight chord through roof lines', _BAYS, 'tip z %.0f' % roof_f(*_CH[0]))
eave_pts = []                                  # (s, p, n, d_eave, z_edge)
for k in range(NS):
    s_ = Ls * k / NS
    q0 = ring_ccw.interpolate(s_); q1 = ring_ccw.interpolate((s_ + 30.0) % Ls); qm = ring_ccw.interpolate((s_ - 30.0) % Ls)
    t_ = np.array([q1.x - qm.x, q1.y - qm.y]); t_ /= np.linalg.norm(t_)
    n_ = np.array([t_[1], -t_[0]])             # 反時計回りの輪の右＝外
    if WS.contains(Point(q0.x + n_[0] * 50, q0.y + n_[1] * 50)): n_ = -n_
    p_ = np.array([q0.x, q0.y]); uu_, vv_ = uv(*p_)
    if vv_ > -0.95: eave_pts.append(None); continue          # 東の面（本館の側）には出さない
    ze = roof_z(*p_)
    f_ = float(np.clip((ze - Z_LOW) / (Z_RAKE - Z_LOW), 0.0, 1.0))
    d_ = EAVE_LOW * (1 - f_) + EAVE_RAKE * f_
    hit = LineString([p_, p_ + n_ * 3000]).intersection(_site.exterior)
    hp = [hit] if hit.geom_type == 'Point' else list(getattr(hit, 'geoms', []))
    if 42.0 <= uu_ < 50.995 and vv_ < -1.2:                                    # 北西の角：軒先はまっすぐな水平の線（CHORD）まで
        hc = LineString([p_, p_ + n_ * 3000]).intersection(CHORD)
        hc = [hc] if hc.geom_type == 'Point' else list(getattr(hc, 'geoms', []))
        if hc:
            d_ = min(np.hypot(h.x - p_[0], h.y - p_[1]) for h in hc) + GUT_W; f_ = 0.0
    if hp: d_ = min(d_, min(np.hypot(h.x - p_[0], h.y - p_[1]) for h in hp) - 100.0)
    eave_pts.append((s_, p_, n_, d_, ze, f_))
# 東の面で切れる所から、つながった区間ごとに帯の面（内＝外皮の縁、外＝軒先）
_k0 = eave_pts.index(None); eave_pts = eave_pts[_k0:] + eave_pts[:_k0]     # 東の面から始める（区間が輪の継ぎ目で割れない）
runs, cur = [], []
for e_ in eave_pts:
    if e_ is None:
        if cur: runs.append(cur); cur = []
    else: cur.append(e_)
if cur: runs.append(cur)
# 軒先の高さ：外皮の縁の高さ（屋根の点の線形補間）＋縁の内側 0.6 の勾配をそのまま外へ（前後 ±1 m でならす）
from scipy.interpolate import LinearNDInterpolator
_top = {}
for x_, y_, z_ in RPu:                          # 同じ所（50 角）にある点はいちばん上だけ（縁の立ち上がり・小口の点を除く）
    k_ = (int(x_ // 50), int(y_ // 50))
    if k_ not in _top or z_ > _top[k_][2]: _top[k_] = (x_, y_, z_)
_T = np.array(list(_top.values()))
_zi = LinearNDInterpolator(_T[:, :2], _T[:, 2])
def _zlin(P):
    z_ = float(_zi(*P))
    return z_ if np.isfinite(z_) else roof_z(*P)
for run in runs:
    ze_ = np.array([_zlin(e_[1] - e_[2] * 30.0) for e_ in run]); zi_ = np.array([_zlin(e_[1] - e_[2] * 630.0) for e_ in run])
    ff_ = np.array([e_[5] for e_ in run])
    sl_ = (ze_ - zi_) / 600.0 * (1 - ff_); k_ = 10        # けらばは水平に出す（妻の側の屋根はねじれていて、縁と直角の勾配が大きい）
    sl_ = np.array([sl_[max(0, i - k_): i + k_ + 1].mean() for i in range(len(sl_))])
    ze_ = np.array([ze_[max(0, i - 5): i + 6].mean() for i in range(len(ze_))])   # 縁の高さの小さなぎざぎざをならす
    for i, e_ in enumerate(run): run[i] = e_ + (ze_[i], float(sl_[i]))
def zt_tip(e_, dd):                                  # 10-27夜：屋根の面の式（roofw）をそのまま延ばす（ならさない。軒の下の線が波打っていた）
    q_ = e_[1] + e_[2] * dd; return float(roof_f(q_[0], q_[1]))
RT_W = 109.0                                     # 10-27夜：屋根の上面は梁の上端＝この面の約 109 上（前は 420）。軒樋・鎖樋は上面の先に合わせる
def zt_top(e_, dd): return zt_tip(e_, dd) + RT_W
n_eave = 0; gut_line = []
for run in runs:
    if len(run) < 3: continue
    mm = r.Mesh()
    for e_ in run:
        dd = e_[3] - GUT_W * (1 - e_[5])        # 軒は軒樋の分だけ屋根を控える
        for t_ in (-20.0, dd / 2, dd):                                     # 内（外皮の縁の 20 内）・中・軒先の 3 列
            c_ = e_[1] + e_[2] * t_; mm.Vertices.Add(float(c_[0]), float(c_[1]), float(zt_tip(e_, t_)))
    for k in range(len(run) - 1):
        i0 = 3 * k
        mm.Faces.AddFace(i0, i0 + 1, i0 + 4, i0 + 3); mm.Faces.AddFace(i0 + 1, i0 + 2, i0 + 5, i0 + 4)
    mm.Normals.ComputeNormals(); mm.Compact()
    at = r.ObjectAttributes(); at.LayerIndex = L_ROOF; new.Objects.AddMesh(mm, at); n_eave += 1
    gut_line += [e_ for e_ in run if e_[5] < 0.05]
# 軒樋：低い縁の軒先（屋根の面の外、幅 120）。高さは軒先のいちばん低い所の 20 下を上端に、水平
if len(gut_line) > 3:
    segs, cur = [], [gut_line[0]]
    for a_, b_ in zip(gut_line, gut_line[1:]):
        if min(abs(b_[0] - a_[0]), Ls - abs(b_[0] - a_[0])) > 150: segs.append(cur); cur = []
        cur.append(b_)
    segs.append(cur)
    seg = max(segs, key=len)
    # 軒樋は軒先に沿う（上端＝屋根の先の 20 下、深さ 150、幅 120）。10-28（監修の項 2346）：軒先の線をまっすぐな区間に分け（ずれ 2 mm）、
    # 区間ごとに断面 120×150 の押し出し（前は 100 ごとの箱を一つの網目にまとめ、Rhino 版で 404 面）。北西の角は軒先がまっすぐな水平の線なのでそのまま
    from shapely.geometry import LineString as _LS
    _C3 = np.array([np.r_[e_[1] + e_[2] * (e_[3] - GUT_W / 2), zt_top(e_, e_[3] - GUT_W) - 20.0] for e_ in seg])
    _keep = np.asarray(_LS(_C3[:, :2]).simplify(2.0).coords)
    _ix = [int(np.argmin(np.linalg.norm(_C3[:, :2] - q_, axis=1))) for q_ in _keep]
    _ngut = 0
    for i0, i1 in zip(_ix, _ix[1:]):
        if i1 <= i0: continue
        A3, B3 = _C3[i0], _C3[i1]; d3 = B3 - A3; L_ = float(np.linalg.norm(d3))
        if L_ < 10.0: continue
        d3 /= L_; s3 = np.cross(d3, [0.0, 0.0, 1.0]); s3 /= np.linalg.norm(s3); n3 = np.cross(s3, d3)
        Cq = [A3 + s3 * GUT_W / 2, A3 - s3 * GUT_W / 2, A3 - s3 * GUT_W / 2 - n3 * 150.0, A3 + s3 * GUT_W / 2 - n3 * 150.0]
        crv = r.Polyline([r.Point3d(*map(float, q_)) for q_ in Cq + [Cq[0]]]).ToNurbsCurve()
        best = None
        for ex_ in (r.Extrusion.Create(crv, L_, True), r.Extrusion.Create(crv, -L_, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2]) - (A3[:2] + B3[:2]) / 2)
            if best is None or dm < best[0]: best = (dm, ex_)
        if best is None: continue
        at = r.ObjectAttributes(); at.LayerIndex = L_RAIN; at.Name = '軒樋 120×150'
        new.Objects.AddExtrusion(best[1], at); _ngut += 1
    g_bot = min(zt_top(e_, e_[3] - GUT_W) for e_ in seg) - 170.0; g_top = g_bot + 150.0
    gpath = LineString([e_[1] + e_[2] * (e_[3] - GUT_W / 2) for e_ in seg])
    def chain_at(c_):
        c_ = np.asarray(c_, float); e_ = min(seg, key=lambda e: np.hypot(*(e[1] - c_)))
        z0_, z1_ = -300.0, zt_top(e_, e_[3] - GUT_W) - 170.0                      # 10-28：円の押し出し（前は 8 角の網目）
        cir = r.Circle(r.Point3d(float(c_[0]), float(c_[1]), float(z0_)), 18.0)
        ex_ = r.Extrusion.Create(cir.ToNurbsCurve(), float(z1_ - z0_), True)
        bb_ = ex_.GetBoundingBox()
        if bb_.Max.Z < z0_ + 1: ex_ = r.Extrusion.Create(cir.ToNurbsCurve(), -float(z1_ - z0_), True)
        at = r.ObjectAttributes(); at.LayerIndex = L_RAIN; at.Name = '鎖樋 φ36'
        new.Objects.AddExtrusion(ex_, at)
    pN = np.array(xy(40.6, -14.99)); qN = gpath.interpolate(gpath.project(Point(*pN))); chain_at((qN.x, qN.y))
    _qS = gpath.interpolate(gpath.project(Point(*xy(21.6, -12.6))))            # 南：勝手口の北の端から約0.5北の軒先（回り込んだ下屋の上、外構の集水で受ける。10-24 アプローチ係）
    pS = np.array([_qS.x, _qS.y]); chain_at(pS)
    print('eave: %d strips, gutter %d pieces, low %.1f m / gutter %.1f m, lowest %.0f, chains N(u %.1f) S(u %.1f v %.1f)' %
          (n_eave, _ngut, len(seg) * Ls / NS / 1000, gpath.length / 1000, g_top, uv(qN.x, qN.y)[0], *uv(*pS)))

# ---------------------------------------------------------------- 調理の更衣・便所の戸（10-25、監修の指摘）
# u28.25 の壁の2つの口（v−11.1〜−11.95 と v−12.14〜−13.18）は、自動の戸だとあいだの細い壁（0.19）の両側を吊元にして
# 同じ向きに開き、弧がぶつかる。北の口（v−11.1〜−11.95）だけ吊元を反対の端（v−11.105）にする。
# 10-28（監修の項 2331・2346）：戸を開口（v−11.30〜−11.95）に合わせて W630 にし、吊元を北の端（−11.31）、前室（u の小さい側）へ開く
# （前は W840 で開口より広く、90° に開くと板が北の間仕切りに重なった。自動の戸（add_inner.py）が同じ開口に二重に置かれていたのは 19d を見ていなかったため）
_hp = tuple(float(v_) for v_ in np.ravel(xy(28.25, -11.31)))
_od = np.ravel(xy(27.25, -11.31)) - np.ravel(xy(28.25, -11.31)); _od = _od / np.linalg.norm(_od)
_at = r.ObjectAttributes(); _at.LayerIndex = L_19D
_at.Name = '開き戸 W630 吊元 %.0f,%.0f 開く %.4f,%.4f' % (_hp[0], _hp[1], _od[0], _od[1])
_mmd = r.Mesh()
_pd = R(28.232, 28.268, -11.945, -11.31, 0.05)
_tm = __import__('trimesh').creation.extrude_polygon(_pd, 2040.0)
for x_, y_, z_ in _tm.vertices: _mmd.Vertices.Add(float(x_), float(y_), float(z_) + 10.0)
for a_, b_, c_ in _tm.faces: _mmd.Faces.AddFace(int(a_), int(b_), int(c_))
_mmd.Normals.ComputeNormals(); new.Objects.AddMesh(_mmd, _at)

# ---------------------------------------------------------------- すき間の倉庫（10-25）
from meshkit import Kit
_K = Kit(new); _nshelf = 0
for rngs, li in ((GAP_T, L_STG_T), ([(40.05, 45.45), (49.80, 50.70)], L_STG_P)):
    for a, b in rngs:
        _K.flat(R(a, b, -0.90, -0.35, 0.1), 10.0, li)                                # 床の板（面積の板）
        n_ = max(1, int(math.ceil((b - a) / 0.9)))
        for k in range(n_ + 1):                                                     # 縦の仕切り（t25、約0.9ごと）
            uu = a + (b - a) * k / n_; uu = min(max(uu, a + 0.0125), b - 0.0125)
            mesh_prism(R(uu - 0.0125, uu + 0.0125, -0.82, -0.40, 0.05), 0.0, const(2400.0), L_FURN); _nshelf += 1
        for zb in (100.0, 500.0, 900.0, 1300.0, 1700.0, 2100.0, 2375.0):            # 棚板（t25、奥行き0.42）
            mesh_prism(R(a, b, -0.82, -0.40, 0.1), zb, const(zb + 25.0), L_FURN)
for a, b in GAP_P:                                                                  # 遊戯室の側の口に引き違いの戸（2枚、t30、壁の厚みの中）
    m_ = (a + b) / 2
    mesh_prism(R(a, m_ + 0.02, -0.96, -0.93, 0.05), 10.0, const(2090.0), L_SLD)
    mesh_prism(R(m_ - 0.02, b, -1.00, -0.97, 0.05), 10.0, const(2090.0), L_SLD)
print('gap storage: %.1f m2 (先生の道 %.1f、遊戯室 %.1f)' % (sum((b - a) * 0.55 for a, b in GAP_T + [(40.05, 45.45), (49.80, 50.70)]), sum((b - a) * 0.55 for a, b in GAP_T), sum((b - a) * 0.55 for a, b in [(40.05, 45.45), (49.80, 50.70)])))

new.Write(OUT, 8); print('written', OUT, len(new.Objects))
