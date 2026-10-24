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
L_MED = lidx('59_1F_医務'); L_WV = lidx('59_1F_西吹き抜け'); L_FURN = lidx('37_')
L_OFF7 = layer('59_1F_事務（スパン 7、おはようの窓口）', hexc('E9DCC4'))
L_DOOR = layer('89_遊戯室_搬入の大戸（閉じた状態）', (150, 110, 70))   # レイヤー表を new へ写す前に作る（後で作ると大戸が 00 に落ちる）
L_RAIN = layer('21g_西館_軒樋・鎖樋（道路の側）', (120, 120, 125))     # 同じく写す前に
WV = []
# ガラスの材質は本館のガラス戸（16）と同じ
mi = m.Layers[lidx('16_')].RenderMaterialIndex
if mi >= 0: m.Layers[L_GL].RenderMaterialIndex = mi

_D = pickle.load(open(WNPKL, 'rb')); WN = _D['WN']
WS = _D.get('WS', WN)          # 外皮の輪郭（外壁・屋根）。北西の斜めの外壁は壁面後退の線まで（10-23、西館係）。架構と間仕切りは WN

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
    s = ring.project(Point(x, y))
    return float(np.interp(s, S, Z, period=ring.length))
# 屋根（20）の上面：WS が WN の外へ出た所は、屋根の面をそのまま延ばす（近くの屋根の点で平面を当てはめる）
L_ROOF = lidx('20_')
RP = np.vstack([np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
                for o in m.Objects for g in [o.Geometry] if o.Attributes.LayerIndex == L_ROOF and isinstance(g, r.Mesh)])
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
def mesh_prism(poly, z0, zfun, li, col=None):
    """平面形 poly（穴あり可）を z0 から zfun(x,y) まで（天端は点ごと）"""
    polys = [poly] if poly.geom_type == 'Polygon' else list(poly.geoms)
    for p in polys:
        if p.area < 100: continue
        p = p.simplify(0.5)
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
FP_HALL = R(21.15, 30.0, -1.4, -0.5)          # 南の壁の角（u 21–21.15）は残す
HB_SILL = ZLID_E + 350.0; HB_HEAD = HB_SILL + 1200.0   # 東の高窓（蓋の上の外壁に横長の窓、はめ殺し）
FP_BAND = R(21.15, 50.85, -1.4, -0.5)          # 10-24（ユーザー）：東の面いっぱいの一本の帯（2階・遊戯室とも、遊戯室の東の高窓もこれにまとめた）
OPEN = [  # (足元の形, 下, 上)  上=None は天端まで
    (R(20.6, 21.4, -2.75, -0.95), 0, 2270),       # 入口の引き戸 1.8
    (R(20.6, 21.4, -4.4, -3.5), 450, 1050),       # 今日のごはんの窓（子どもの高さ）
    (R(20.6, 21.4, -9.6, -4.6), 800, 2270),       # キッチンの南のガラス
    (FP_HALL, 0, ZLID_E),                         # ホールの範囲：東の面はすき間の蓋の下まで開く（ひと続き）。蓋より上は外壁
    (FP_BAND, HB_SILL, HB_HEAD),                  # その上に東の面いっぱいの横長の高窓（本館の屋根越しに東の空）
    (R(28.5, 29.3, -14.5, -12.3), 0, 2100),       # 調理の職員の外からの戸（西の面）
]
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
    surf(EXT.buffer(20).intersection(WS), roof_z, L_ROOF)                       # 屋根の面をそのまま延ばす（重なり 20）
    flat(EXT.buffer(20).intersection(WS), 10, lidx('31_'))                      # 遊戯室の床の板
    print('skin beyond WN: %.2f m2, roof z at the new eave %.0f' % (EXT.area / 1e6, min(roof_z(*c) for c in np.asarray(EXT.exterior.coords))))
WALLC = None
base = wall_ring.difference(unary_union([o[0] for o in OPEN]))
mesh_prism(base, 0.0, ztop, L_WALL)
GRP = {}                                         # 同じ足元の開口（覗き窓と高窓など）はまとめて、残る壁を上下に分ける
for fp, zb, zt in OPEN: GRP.setdefault(id(fp), [fp, []])[1].append((zb, zt))
# 足元が重なる開口（10-24：東の面いっぱいの高窓の帯と、覗き窓・口②・ホールの範囲）は、重なりで区切ってから開口をまとめる
cells = []
for fp, iv in GRP.values():
    rest = wall_ring.intersection(fp); nxt = []
    for g, ivs in cells:
        a = g.intersection(fp); b = g.difference(fp)
        if a.area > 100: nxt.append((a, ivs + iv))
        if b.area > 100: nxt.append((b, ivs))
        rest = rest.difference(g)
    if rest.area > 100: nxt.append((rest, list(iv)))
    cells = nxt
for piece, iv in cells:
    iv = sorted(iv, key=lambda t: t[0]); z = 0.0
    for zb, zt in iv:
        if z is None: break
        if zb > z: mesh_prism(piece, z, const(float(zb)), L_WALL)
        if zt is None: z = None; break
        z = max(z, float(zt))
    if z is not None: mesh_prism(piece, z, ztop, L_WALL)

# ガラス・建具（厚さ 30、壁の中ほど）
def pane_u(u, v0, v1, z0, z1, t=0.03):
    mesh_prism(R(u - t / 2, u + t / 2, v0, v1, 0.02), z0, const(z1), L_GL)
uS = 21.0 + 0.075 / 1.0 * 1.0   # 南の面の壁の中（外面 u=21、厚さ 150 → 中心 u≈21.075）
pane_u(21.06, -1.90, -0.95, 0, 2270); pane_u(21.10, -2.75, -1.80, 0, 2270)   # 引き戸 2 枚
pane_u(21.075, -4.4, -3.5, 450, 1050)                                         # 今日のごはんの窓
pane_u(21.075, -9.6, -4.6, 800, 2270)                                         # キッチンの南のガラス
# 遊戯室の窓・大戸：壁の厚さの中ほどの薄い板
PANES.append((FP_BAND, HB_SILL, HB_HEAD, L_GL))
L_WD = layer('19b_西館_外の戸（木、開き戸）', (150, 110, 70))
PANES.append((R(28.5, 29.3, -14.5, -12.3), 0, 2100, L_WD))     # 調理の職員の外からの戸（開口だけで戸が無かった）
print('hall face: open to lid', round(ZLID_E), 'high window', round(HB_SILL), round(HB_HEAD))
mid_ring = WS.buffer(-60, join_style=2).difference(WS.buffer(-90, join_style=2))
for fp, z0, z1, li in PANES:
    mesh_prism(mid_ring.intersection(fp), float(z0), const(float(z1)), li)
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

# ---------------------------------------------------------------- 床
WNi = WN.buffer(-T_W, join_style=2)
KN = 27.25                     # キッチンの北の壁（60.5 m²）
CB = -11.1                     # 調理の職員の更衣・便所・前室：はれのまの西の端、v −11.1 から西の面まで（外から直接）
flat(R(21, KN, -20, -3.4).intersection(WN), 10, L_KIT)          # 面積は外形で（plan05 と同じ）
cook = R(KN, 30, -20, CB).intersection(WN)
store = R(KN, 30, CB, CB + 0.6)                                   # はれのまの収納（西の端の壁、奥行き 0.6）
flat(cook, 10, L_COOK)
flat(R(KN, 30, CB, -3.4).intersection(WN).buffer(-5).buffer(5), 10, L_HARE)
flat(unary_union([R(22.5, 30, -3.4, -0.9).intersection(WN), R(22.5, 30, -0.9, -0.2)]).buffer(1).buffer(-1), 10, L_BAND)
# 海峡を東の帯の南端まで（土足 −150、床の板は −450〜−150）
mesh_prism(unary_union([R(21, 22.5, -3.4, -0.9).intersection(WN), R(21, 22.5, -0.9, -0.2)]), -450.0, const(-150.0), L_STR)
mesh_prism(R(22.45, 22.55, -3.4, -0.2, 0.05), -150.0, const(0.0), L_KAMA, (150, 110, 70))   # 框

# ---------------------------------------------------------------- 間仕切り（厚さ 100、h3100）
H = 3170.0                     # 2 階の床の下まで（キッチン・はれのま・更衣、音も切る）
def wall_u(u, v0, v1, holes=()):
    """u 一定（放射方向の直線）の壁。holes=[(v0, v1, zb, zt)]"""
    fp = lambda a, b: R(u - 0.05, u + 0.05, a, b, 0.02).intersection(WNi)
    cuts = sorted(set([v0, v1] + [h[0] for h in holes] + [h[1] for h in holes]))
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2; zs = [(0.0, H)]
        for h in holes:
            if min(h[0], h[1]) <= mid <= max(h[0], h[1]): zs = [(0.0, h[2]), (h[3], H)]
        for z0, z1 in zs:
            if z1 - z0 > 5: mesh_prism(fp(a, b), z0, const(z1), L_PART)
def wall_v(v, u0, u1, holes=()):
    """v 一定（弧に沿う）の壁。holes=[(u0, u1, zb, zt)]"""
    cuts = sorted(set([u0, u1] + [h[0] for h in holes] + [h[1] for h in holes]))
    for a, b in zip(cuts, cuts[1:]):
        mid = (a + b) / 2; zs = [(0.0, H)]
        for h in holes:
            if h[0] <= mid <= h[1]: zs = [(0.0, h[2]), (h[3], H)]
        for z0, z1 in zs:
            if z1 - z0 > 5: mesh_prism(R(a, b, v - 0.05, v + 0.05).intersection(WNi), z0, const(z1), L_PART)
GLK = [(21.3, 22.6), (24.4, 25.5), (26.5, 27.15)]                                  # オープンキッチン：低い位置（h450）からのガラス
wall_v(-3.4, 21.0, 30.0, [(22.7, 24.3, 850, 1900), (25.6, 26.4, 850, 1900),        # 配膳口・返却口
                          (28.2, 29.4, 0, 2100)] + [(a, b, 450, 2270) for a, b in GLK])   # はれのまの戸
for a, b in GLK:
    mesh_prism(R(a, b, -3.415, -3.385, 0.05), 450.0, const(2270.0), L_GL)
wall_u(KN, -3.4, -20, [(-7.8, -9.6, 850, 1900), (-11.25, -11.95, 0, 2100)])        # 見える台所・前室 → キッチン
wall_u(30.0, -3.4, -20)                                                             # はれのま｜遊戯室（2 階の床の下まで）
wall_v(CB, KN, 30.0)                                                                # はれのま｜更衣・前室・便所
wall_u(28.25, CB, -20, [(-11.3, -11.95, 0, 2100), (-12.4, -12.95, 0, 2100)])       # 前室・便所｜更衣
wall_v(-12.2, KN, 28.25)                                                            # 前室｜便所
mesh_prism(store.intersection(WNi), 0.0, const(2100.0), L_FURN, (210, 190, 160))   # はれのまの収納（延長の箱・季節の棚）
mesh_prism(R(KN + 0.07, KN + 0.47, -10.4, -3.6, 0.05), 0.0, const(600.0), L_FURN, (196, 160, 110))   # カウンター h600（子どもの流し・おやつの台）
mesh_prism(R(26.5, 27.15, -3.38, -2.98, 0.05), 0.0, const(500.0), L_FURN, (196, 160, 110))   # 生ごみの受け取り台 h500（返却口の北隣、東の帯の側。3〜5歳のコンポスト当番）

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

# ---------------------------------------------------------------- 西の軒の軒樋と鎖樋（アプローチ係が決めた形、連携10-23夜3）
# 屋根は西へ流れ、西の縁（外壁の外面＝WS、z 4650）から落ちる。軒樋（120×120）を西の面のまっすぐな所の北の端から
# 南西の丸みに沿って下屋の西の端まで、外壁の外面に沿わせて水平に回す。鎖樋は 2 本：北＝西の面のまっすぐな所の北の端、
# 南＝下屋の西の端（下屋の樋もここへ集める）。行き先（雨水樽・北の雨庭）は外構（75・76）。
ringS = WS.exterior
def _s(u, v): return ringS.project(Point(*xy(u, v)))
sN, sS = _s(40.6, -14.99), _s(21.0, -10.1)
from shapely.ops import substring
gpath = substring(ringS, min(sN, sS), max(sN, sS))
gut = gpath.buffer(130, cap_style=2).difference(WS.buffer(10))
mesh_prism(gut, 4470.0, const(4590.0), L_RAIN)
for sp in (sN, sS):
    q = ringS.interpolate(sp); q2 = ringS.interpolate(sp + 50)
    t_ = np.array([q2.x - q.x, q2.y - q.y]); t_ /= np.linalg.norm(t_); nrm_ = np.array([t_[1], -t_[0]])
    c_ = np.array([q.x, q.y]) + nrm_ * 70
    if WS.contains(Point(*c_)): c_ = np.array([q.x, q.y]) - nrm_ * 70
    mesh_prism(Point(*c_).buffer(18, 8), -300.0, const(4470.0), L_RAIN)
print('rain: gutter %.1f m, chains 2' % (gpath.length / 1000))

new.Write(OUT, 8); print('written', OUT, len(new.Objects))
