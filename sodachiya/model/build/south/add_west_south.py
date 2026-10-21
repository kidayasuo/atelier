"""西館の南の部分（2026-10-21 夕の決定、詳細設計チャットの plan05.py に合わせる）
使い方: python3 add_west_south.py IN.3dm OUT.3dm     （finish.py の後、レイヤー番号は 00〜69 の後）
- 西館の外壁（21）を厚さ 150 で作り直す：南の面に入口の引き戸 1.8・今日のごはんの窓・キッチンの南のガラス、
  東の面はホールの範囲（u 21–30）を開け、遊戯室の口①②（u 30.6–32.6、44.1–46.1）
- すき間の南の端にガラス（入口の脇、v −0.15〜−0.85）
- 床の板：キッチン u 21–27.25／調理の更衣・便所・前室 u 27.25–29.25（v −3.4〜−6.4）／はれのま（仮、34）残り／
  東の帯 u 22.5–30（すき間を含む、はだし ±0）
- 海峡を東の帯の南端まで延ばす（u 21–22.5、v −0.2〜−3.4、−150）、u 22.5 に框
- 西館 1 階の間仕切り（キッチン・更衣・はれのま、h3100＝2 階の床の下まで）：配膳口・返却口・戸・見える台所の窓
- スパン 7（10-21 午後）：事務を西の壁に寄せる（v 0〜4.5、西吹き抜けを含む）、医務 v 4.5〜12。
  海峡の側：事務は開ける（低いカウンター「おはようの窓口」＋開いた口、框 150）、医務は壁。境は引き込み戸。
  海峡に飛び石 1 つ（u 21.75、v 3.4、径 0.9、上面 ±0）
"""
import sys, math, pickle, numpy as np, rhino3dm as r
from shapely.geometry import Polygon, Point, LineString, MultiPolygon
from shapely.ops import unary_union
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
WV = []
# ガラスの材質は本館のガラス戸（16）と同じ
mi = m.Layers[lidx('16_')].RenderMaterialIndex
if mi >= 0: m.Layers[L_GL].RenderMaterialIndex = mi

WN = pickle.load(open(WNPKL, 'rb'))['WN']

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
def ztop(x, y):
    s = ring.project(Point(x, y))
    return float(np.interp(s, S, Z, period=ring.length))

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
wall_ring = WN.difference(WN.buffer(-T_W, join_style=2))
OPEN = [  # (足元の形, 下, 上)  上=None は天端まで
    (R(20.6, 21.4, -2.75, -0.95), 0, 2270),       # 入口の引き戸 1.8
    (R(20.6, 21.4, -4.4, -3.5), 450, 1050),       # 今日のごはんの窓（子どもの高さ）
    (R(20.6, 21.4, -9.6, -4.6), 800, 2270),       # キッチンの南のガラス
    (R(21.0, 30.0, -1.4, -0.5), 0, None),         # ホールの範囲：東の面は開く（ひと続き）
    (R(30.6, 32.6, -1.4, -0.5), 0, 2400),         # 遊戯室の口①
    (R(44.1, 46.1, -1.4, -0.5), 0, 2400),         # 遊戯室の口②
]
WALLC = None
base = wall_ring.difference(unary_union([o[0] for o in OPEN]))
mesh_prism(base, 0.0, ztop, L_WALL)
for fp, zb, zt in OPEN:
    piece = wall_ring.intersection(fp)
    if piece.is_empty: continue
    if zb > 0: mesh_prism(piece, 0.0, const(zb), L_WALL)
    if zt is not None: mesh_prism(piece, float(zt), ztop, L_WALL)

# ガラス・建具（厚さ 30、壁の中ほど）
def pane_u(u, v0, v1, z0, z1, t=0.03):
    mesh_prism(R(u - t / 2, u + t / 2, v0, v1, 0.02), z0, const(z1), L_GL)
uS = 21.0 + 0.075 / 1.0 * 1.0   # 南の面の壁の中（外面 u=21、厚さ 150 → 中心 u≈21.075）
pane_u(21.06, -1.90, -0.95, 0, 2270); pane_u(21.10, -2.75, -1.80, 0, 2270)   # 引き戸 2 枚
pane_u(21.075, -4.4, -3.5, 450, 1050)                                         # 今日のごはんの窓
pane_u(21.075, -9.6, -4.6, 800, 2270)                                         # キッチンの南のガラス
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
KN = 27.25
flat(R(21, KN, -20, -3.4).intersection(WN), 10, L_KIT)          # 面積は外形で（plan05 と同じ）
cook = R(KN, 29.25, -6.4, -3.4)
flat(cook.intersection(WN), 10, L_COOK)
flat(R(KN, 30, -20, -3.4).intersection(WN).difference(cook).buffer(-5).buffer(5), 10, L_HARE)
flat(unary_union([R(22.5, 30, -3.4, -0.9).intersection(WN), R(22.5, 30, -0.9, -0.2)]).buffer(1).buffer(-1), 10, L_BAND)
# 海峡を東の帯の南端まで（土足 −150、床の板は −450〜−150）
mesh_prism(unary_union([R(21, 22.5, -3.4, -0.9).intersection(WN), R(21, 22.5, -0.9, -0.2)]), -450.0, const(-150.0), L_STR)
mesh_prism(R(22.45, 22.55, -3.4, -0.2, 0.05), -150.0, const(0.0), L_KAMA, (150, 110, 70))   # 框

# ---------------------------------------------------------------- 間仕切り（厚さ 100、h3100）
H = 3100.0
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
wall_v(-3.4, 21.0, 30.0, [(22.7, 24.3, 850, 1900), (25.6, 26.4, 850, 1900),        # 配膳口・返却口
                          (28.3, 29.1, 0, 2100), (29.3, 29.95, 0, 2100)])           # 更衣・はれのまへの戸
wall_u(KN, -3.4, -20, [(-3.7, -4.5, 0, 2100), (-7.8, -9.6, 850, 1900)])            # キッチンへの戸・見える台所
wall_u(30.0, -3.4, -20)                                                             # はれのま｜遊戯室
wall_u(29.25, -3.4, -6.4)
wall_v(-6.4, KN, 29.25)
wall_v(-5.25, KN, 29.25, [(28.4, 29.0, 0, 2100)])                                   # 更衣｜便所
wall_u(28.0, -3.4, -5.25, [(-3.7, -4.4, 0, 2100)])                                  # 前室｜更衣

# ---------------------------------------------------------------- スパン 7：事務・医務・おはようの窓口・飛び石
def mesh_poly(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y] for i in range(len(g.Vertices))])
    ps = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; ps.append(Polygon(V[[f[0], f[1], f[2]]]).buffer(0))
    return unary_union([p.buffer(1) for p in ps if p.area > 0]).buffer(-1)
for g in WV:                                   # 西吹き抜けの板からスパン 7 を抜く
    flat(mesh_poly(g).difference(R(18.0, 21.0, -0.3, 1.9)), 10, L_WV)
flat(R(18.0, 21.0, 0.0, 4.5), 10, L_OFF7)
flat(R(18.0, 21.0, 4.5, 12.0), 10, L_MED)
mesh_prism(R(20.95, 21.05, 4.5, 12.0, 0.02), 0.0, const(2400.0), L_KAMA)            # 医務｜海峡の壁
mesh_prism(R(20.95, 21.05, 0.0, 4.5, 0.02), -150.0, const(0.0), L_KAMA, (150, 110, 70))   # 框 150（海峡 −150 → ±0）
mesh_prism(R(20.50, 20.95, 0.15, 2.9, 0.05), 0.0, const(700.0), L_FURN, (196, 160, 110))  # おはようの窓口（低いカウンター）
for a_, b_ in ((18.0, 19.0), (20.2, 21.0)):                                         # 事務｜医務（引き込み戸 u 19.0–20.2、ふだんは開けておく）
    mesh_prism(R(a_, b_, 4.45, 4.55), 0.0, const(2400.0), L_KAMA)
mesh_prism(R(19.0, 20.2, 4.45, 4.55), 2100.0, const(2400.0), L_KAMA)
c0 = xy(21.75, 3.4)
mesh_prism(Point(c0).buffer(450, resolution=16), -150.0, const(0.0), L_KAMA, (165, 160, 150))   # 飛び石

new.Write(OUT, 8); print('written', OUT, len(new.Objects))
