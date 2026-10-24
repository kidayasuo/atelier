"""納まりの整理（外皮は架構の外に連続させ、架構は室内に見せる）
使い方: python3 fix_details.py IN.3dm OUT.3dm data/wnew.pkl
本館
- 西の外壁（r=205 m の線、厚さ 150 で柱の真ん中を通っていた）を柱の外（v −0.35〜−0.20）へ。柱・桁は西吹き抜けに見せる。窓も壁の中へ。
- 北の妻壁（厚さ 120 で柱の真ん中、外の梁は外に出ていた）を北の端の架構の外（u 57.19〜57.34）へ。縁側の妻のガラスも同じ線へ。
- 屋根を西 v −0.45・北 u 57.45 まで延ばして外皮を覆う。
- 桁（楕円 200×400）：北の端を架構の外面（u 57.19）で止める（外へ 0.6 突き出ていた）。南の端はそのまま（南の軒の下で見せる）。
- 南の妻（ガラスは 2 枚の梁のあいだ、決定事項）のガラスは柱の面から。
西館
- 南の端の架構（u≈21、梁の片方と 2 階の床梁が南の壁の中に埋まり、西の柱が外に出ていた）を北へ寄せて壁の内側に。
- 柱が外壁に 30〜130 mm めり込んでいたのを、壁の内面に接するまで内へ寄せる（柱はすべて室内に見せる）。
- 2 階の間仕切り（24・38、天井は張らない）は屋根の下面まで（屋根を突き抜けていた・屋根との間が空いていた）。
- 2 階の床の東の縁（v −1.9、下の東の帯への吹き抜け）と、2 階の北の口（u 33、遊戯室の吹き抜けに面する）に腰壁 h1100。
"""
import sys, math, pickle, numpy as np, rhino3dm as r, trimesh
sys.path.insert(0, '/tmp/claude-0/t/south')
from shapely.geometry import Polygon, Point
from shapely.ops import unary_union, nearest_points
from uv import uv, xy, CX, CY, RW
from meshkit import Kit, R

IN, OUT, WNPKL = sys.argv[1:4]
m = r.File3dm.Read(IN)
WN = pickle.load(open(WNPKL, 'rb'))['WN']
WNi = WN.buffer(-150, join_style=2)
LN = {i: l.Name for i, l in enumerate(m.Layers)}
def lidx(prefix): return [i for i, n in LN.items() if n.startswith(prefix)][0]

def to_uv_arr(V): return np.array([uv(x, y) for x, y in V[:, :2]])
def from_uv(u, v): return xy(u, v)
def mesh_V(g): return np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
def mesh_set(g, V):
    for i, (x, y, z) in enumerate(V): g.Vertices.SetPoint3dAt(i, r.Point3d(float(x), float(y), float(z)))
def map_mesh_uv(g, fn):
    """メッシュの頂点を (u, v, z) → (u', v', z') で動かす"""
    V = mesh_V(g); U = to_uv_arr(V); out = []
    for (u, v), z in zip(U, V[:, 2]):
        u2, v2, z2 = fn(u, v, z); p = from_uv(u2, v2); out.append((p[0], p[1], z2))
    mesh_set(g, out); g.Normals.ComputeNormals()
def bbox_uv(g):
    V = mesh_V(g) if isinstance(g, r.Mesh) else tris(g).reshape(-1, 3)
    U = to_uv_arr(V); return U[:, 0].min(), U[:, 0].max(), U[:, 1].min(), U[:, 1].max(), V[:, 2].min(), V[:, 2].max()

sys.path.insert(0, '/tmp/claude-0/t/view'); import tri
def tris(g):
    if isinstance(g, r.Extrusion): return tri.tri_extrusion(g)
    if isinstance(g, r.Brep): return tri.tri_brep(g)
    if isinstance(g, r.Mesh): return tri.tri_mesh(g)
    return np.zeros((0, 3, 3))
def foot(g):
    T = tris(g); ps = [Polygon(t[:, :2]).buffer(0) for t in T]; ps = [p for p in ps if p.area > 1]
    return unary_union([p.buffer(0.5) for p in ps]).buffer(-0.5) if ps else None

L17 = lidx('17_'); L10 = lidx('10_'); L11C = lidx('11c'); L16 = lidx('16_')
L22A, L22B, L22C, L22D = (lidx(p) for p in ('22a', '22b', '22c', '22d'))
L20 = lidx('20_'); L24 = lidx('24_'); L38 = lidx('38_')
log = []

# ================================================================ 本館
# 外皮（壁・ガラス）は架構の外に連続させる（木造の標準：断熱・防水の層を柱で切らない、柱と桁は室内に見せる）
VW0, VW1 = -0.35, -0.20          # 西の外壁（厚さ 150）：柱の外面 v −0.20 の外
UG0, UG1 = 57.19, 57.34          # 北の妻壁（厚さ 150）：北の端の架構（外の梁の外面 u 57.19）の外
L48 = lidx('48_')
n_w = n_g = n_o = 0
for o in m.Objects:
    g = o.Geometry; li = o.Attributes.LayerIndex
    if not isinstance(g, r.Mesh): continue
    if li == L17:
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if v0 > -0.09 and v1 < 0.09 and u1 - u0 > 0.2 and z0 < 3700:          # 西の外壁（越屋根の立ち上がりはそのまま）
            map_mesh_uv(g, lambda u, v, z: (u, v - 0.275, z)); n_w += 1
        elif 56.9 < u0 and u1 < 57.1 and v0 > -0.05 and v1 > 11.5:            # 北の妻壁
            map_mesh_uv(g, lambda u, v, z: (UG0 + (u - 56.94) / 0.12 * (UG1 - UG0), VW0 if v < 0.01 else v, z)); n_g += 1
    if li == L48:                                                             # 西の外壁の窓：壁の中へ
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if v0 > -0.05 and v1 < 0.05 and 0.5 < u0 and u1 < 56.5:
            map_mesh_uv(g, lambda u, v, z: (u, v - 0.275, z)); n_o += 1
    if li == L10:                                                             # 屋根：西の端と北の端を外皮の外まで
        map_mesh_uv(g, lambda u, v, z: (57.45 if u > 56.98 else u, -0.45 if v < -0.15 else v, z))
    if li == L16:                                                             # 縁側の妻のガラス
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if (u1 - u0) < 0.1 and 11.9 < v0 < 12.1 and v1 > 13:
            if u0 > 56: map_mesh_uv(g, lambda u, v, z: (u + 0.245, v, z))       # 北：妻壁の線（外の梁の外）へ
            else: map_mesh_uv(g, lambda u, v, z: (u, max(v, 12.2), z))        # 南：柱の面から（妻は 2 枚の梁のあいだのまま）
log.append(f'本館：西の外壁 {n_w} 片を柱の外（v −0.35〜−0.20）へ、窓 {n_o} 枚も。北の妻壁 {n_g} 片を架構の外（u 57.19〜57.34）へ。屋根を西 v −0.45・北 u 57.45 まで')
def welded_mesh(T):
    mm = r.Mesh(); idx = {}
    def vid(p):
        k = (round(p[0], 1), round(p[1], 1), round(p[2], 1))
        if k not in idx: idx[k] = mm.Vertices.Add(float(p[0]), float(p[1]), float(p[2]))
        return idx[k]
    for t in T:
        a_, b_, c_ = vid(t[0]), vid(t[1]), vid(t[2])
        if len({a_, b_, c_}) == 3: mm.Faces.AddFace(a_, b_, c_)
    return mm

# 西の柱の頭の、桁を抱く膨らみ（v −0.28 まで）が壁の中へ 80 mm 入るので、柱の外面 v −0.20 で平らに
L11A = lidx('11a'); col_new = []; col_drop = set()
for o in m.Objects:
    if o.Attributes.LayerIndex != L11A: continue
    T = tris(o.Geometry); U = to_uv_arr(T.reshape(-1, 3))
    if U[:, 1].mean() > 1 or U[:, 1].min() > -0.205: continue
    mm = welded_mesh(T); map_mesh_uv(mm, lambda u, v, z: (u, max(v, -0.20), z)); mm.Compact()
    col_new.append((mm, o.Attributes)); col_drop.add(str(o.Attributes.Id))
log.append(f'本館：西の柱 {len(col_new)} 本の頭の膨らみを柱の外面（壁の内面）で平らに')

# 桁（Brep）→ メッシュで作り直す（楕円 幅 200×高さ 400、弧に沿って）
def ellipse_tube(vc, zc, ua, ub, li, name):
    us = np.linspace(ua, ub, max(2, int((ub - ua) / 0.25) + 1)); N = 24
    mm = r.Mesh()
    for u in us:
        for k in range(N):
            t = 2 * math.pi * k / N; p = xy(u, vc + 0.1 * math.cos(t)); mm.Vertices.Add(float(p[0]), float(p[1]), float(zc + 200 * math.sin(t)))
    for i in range(len(us) - 1):
        for k in range(N): mm.Faces.AddFace(i * N + k, i * N + (k + 1) % N, (i + 1) * N + (k + 1) % N, (i + 1) * N + k)
    for i, rev in ((0, True), (len(us) - 1, False)):
        p = xy(us[i], vc); c = mm.Vertices.Add(float(p[0]), float(p[1]), float(zc))
        for k in range(N):
            a_, b_ = i * N + k, i * N + (k + 1) % N
            mm.Faces.AddFace(c, b_, a_) if rev else mm.Faces.AddFace(c, a_, b_)
    mm.Normals.ComputeNormals(); mm.Compact()
    at = r.ObjectAttributes(); at.LayerIndex = li; at.Name = name
    return mm, at
new_objs = []; drop = set()
for o in m.Objects:
    if o.Attributes.LayerIndex == L11C:
        u0, u1, v0, v1, z0, z1 = bbox_uv(o.Geometry); vc = (v0 + v1) / 2; zc = (z0 + z1) / 2
        ub = 57.19                                       # 北の端の架構（外の梁の外面）で止める（妻壁の内側）
        new_objs.append(ellipse_tube(vc, zc, u0, ub, L11C, '桁（西）' if vc < 6 else '桁（東）')); drop.add(str(o.Attributes.Id))

# ================================================================ 西館の架構
rot = lambda du: -du * 1000.0 / RW                     # u を du 動かす回転角（中心 C）
def move_u(g, du):
    g.Rotate(rot(du), r.Vector3d(0, 0, 1), r.Point3d(CX, CY, 0))
def move_xy(g, d):
    g.Translate(r.Vector3d(float(d[0]), float(d[1]), 0.0))
# 1) 南の端の架構を北へ（梁の外の板の外面 ≥ 南の壁の内面 u 21.15）
south = [o for o in m.Objects if o.Attributes.LayerIndex in (L22A, L22B, L22C) and bbox_uv(o.Geometry)[1] < 21.7]
if south:
    umin = min(bbox_uv(o.Geometry)[0] for o in south)
    du = max(0.0, 21.15 + 0.005 - umin)
    for o in south: move_u(o.Geometry, du)
    log.append(f'西館：南の端の架構 {len(south)} 本を北へ {du * 1000:.0f} mm')
# 2) 柱：壁にめり込んだ分だけ内へ
n_c = 0; worst = 0
for o in m.Objects:
    if o.Attributes.LayerIndex not in (L22A, L22D): continue      # 柱と桁（角の丸みを弦で渡る桁が壁から出ていた）
    for _ in range(3):
        f = foot(o.Geometry).convex_hull
        out = f.difference(WNi)
        if out.area < 50: break
        pts = [Point(p) for p in np.array(f.exterior.coords) if not WNi.contains(Point(p))]
        if not pts: break
        far = max(pts, key=lambda p: WNi.exterior.distance(p))
        near = nearest_points(WNi.exterior, far)[0]
        d = np.array([near.x - far.x, near.y - far.y]); L = np.linalg.norm(d)
        if L < 0.5: break
        move_xy(o.Geometry, d / L * (L + 3.0)); worst = max(worst, L)
    n_c += 1
log.append(f'西館：柱・桁 {n_c} 本を壁の内面まで（いちばん大きいずれ {worst:.0f} mm）')

# 3) 梁・2 階の床梁の端：外壁の内面で止める（角の丸みで梁の端が外に出ていた）
from shapely.geometry import LineString
beam_new = []; beam_drop = set()
for o in m.Objects:
    if o.Attributes.LayerIndex not in (L22B, L22C): continue
    T = tris(o.Geometry); P = T.reshape(-1, 3)
    if all(WN.buffer(-2).contains(Point(x, y)) for x, y in P[:, :2]): continue    # 壁の中で止まっている端（見えない）はそのまま
    mm = welded_mesh(T); V = mesh_V(mm)
    c = V[:, :2].mean(0); X = V[:, :2] - c; w, vec = np.linalg.eigh(X.T @ X); ax = vec[:, -1]
    for i, (x, y, z) in enumerate(V):
        pt = Point(x, y)
        if WNi.contains(pt): continue
        s_ = np.dot(np.array([x, y]) - c, ax); dirn = -np.sign(s_) * ax          # 中ほどへ向かって
        ln = LineString([(x, y), (x + dirn[0] * 3000, y + dirn[1] * 3000)])
        hit = ln.intersection(WNi.exterior)
        pts = [hit] if hit.geom_type == 'Point' else list(getattr(hit, 'geoms', []))
        if pts:
            q = min(pts, key=lambda p: p.distance(pt)); V[i, 0], V[i, 1] = q.x + dirn[0] * 2, q.y + dirn[1] * 2
    mesh_set(mm, V); mm.Normals.ComputeNormals(); mm.Compact()
    beam_new.append((mm, o.Attributes)); beam_drop.add(str(o.Attributes.Id))
log.append(f'西館：梁 {len(beam_new)} 本の端を外壁の内面で止めた')

# ================================================================ 屋根の下面（西館 20・本館 10）
def roof_mesh(li):
    T = [tris(o.Geometry) for o in m.Objects if o.Attributes.LayerIndex == li]
    T = np.vstack([t for t in T if len(t)])
    return trimesh.Trimesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3), process=False)
RM20 = roof_mesh(L20); I20 = trimesh.ray.ray_triangle.RayMeshIntersector(RM20)
def roof_bottom(P):
    org = np.c_[P[:, 0], P[:, 1], np.full(len(P), 3500.0)]; d = np.tile([0, 0, 1.0], (len(P), 1))
    loc, ir, _ = I20.intersects_location(org, d, multiple_hits=True)
    zb = np.full(len(P), np.nan)
    for (x, y, z), k in zip(loc, ir):
        if np.isnan(zb[k]) or z < zb[k]: zb[k] = z
    return zb
# 3) 2 階の間仕切りは屋根の下面まで
n_p = 0
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex not in (L24, L38) or not isinstance(g, r.Mesh): continue
    V = mesh_V(g)
    if V[:, 2].min() < 3150 or not WN.contains(Point(V[:, :2].mean(0))): continue
    top = V[:, 2] > V[:, 2].max() - 5
    zb = roof_bottom(V[top])
    if np.isnan(zb).any(): continue
    V[top, 2] = zb - 30.0; mesh_set(g, V); g.Normals.ComputeNormals(); n_p += 1
log.append(f'西館：2 階の間仕切り {n_p} 枚を屋根の下面まで')
# 4) 2 階の床（23）の縁を外壁の内面に（外壁の外面と重なって線がちらついていた）
L23 = lidx('23_')
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex != L23 or not isinstance(g, r.Mesh): continue
    V = mesh_V(g)
    for i, (x, y, z) in enumerate(V):
        pt = Point(x, y)
        if not WNi.contains(pt):
            q = nearest_points(WNi.exterior, pt)[0]; V[i, 0], V[i, 1] = q.x, q.y
    mesh_set(g, V); g.Normals.ComputeNormals()
    log.append('西館：2 階の床の縁を外壁の内面に')
# 5) 本館の西の外壁の天端を屋根の下面まで（柱の頭が壁の上に少し出ていた）
RM10 = roof_mesh(L10); I10 = trimesh.ray.ray_triangle.RayMeshIntersector(RM10)
def roof10_bottom(P):
    org = np.c_[P[:, 0], P[:, 1], np.full(len(P), 1000.0)]; d = np.tile([0, 0, 1.0], (len(P), 1))
    loc, ir, _ = I10.intersects_location(org, d, multiple_hits=True)
    zb = np.full(len(P), np.nan)
    for (x, y, z), k in zip(loc, ir):
        if np.isnan(zb[k]) or z < zb[k]: zb[k] = z
    return zb
n_t = 0
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex != L17 or not isinstance(g, r.Mesh): continue
    u0, u1, v0, v1, z0, z1 = bbox_uv(g)
    west = v0 > -0.36 and v1 < -0.19 and 3500 < z1 < 3950 and u1 - u0 > 0.2   # 窓・口の下の腰の片（z1 が低い）は上げない
    gable = u0 > 57.1 and v1 > 11.5
    if not (west or gable): continue
    V = mesh_V(g); top = V[:, 2] > V[:, 2].max() - 5 if west else V[:, 2] > 1000
    zb = roof10_bottom(V[top]); ok = ~np.isnan(zb)
    if ok.any():
        Vt = V[top]; Vt[ok, 2] = (np.maximum(Vt[ok, 2], zb[ok] - 5.0) if west else zb[ok] - 5.0); V[top] = Vt
        mesh_set(g, V); g.Normals.ComputeNormals(); n_t += 1
log.append(f'本館：西の外壁・北の妻壁 {n_t} 片の天端を屋根の下面に合わせた')

# 6) 越屋根の西の立ち上がりを外皮の線へ（監修の指摘 10-23 朝2 の 3b）
# 外壁を柱の外へ移したあとも、越屋根の西の立ち上がり（v −0.06〜0.06、h 約 3.9〜4.3）が元の線に残り、
# 柱の頭と桁に食い込んでいた。外皮は一枚に続ける：西の外壁をそのまま立ち上がりの上端まで立ち上げ、
# 元の立ち上がりと、その外の屋根の細い帯（v −0.45〜0、外壁の上に載っていた）を消す。
# 立ち上がりの上端と蓋のあいだのすき間 150（換気）はそのまま。
UPS = []
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex != L17 or not isinstance(g, r.Mesh): continue
    u0, u1, v0, v1, z0, z1 = bbox_uv(g)
    if v0 > -0.09 and v1 < 0.09 and z0 >= 3700: UPS.append(z1); drop.add(str(o.Attributes.Id))
UP_TOP = max(UPS) if UPS else None
n_e = 0
for o in m.Objects:                                                           # 越屋根の南北の妻の立ち上がり：西の端を外壁の外面まで、北は北の妻壁の線へ
    g = o.Geometry
    if o.Attributes.LayerIndex != L17 or not isinstance(g, r.Mesh): continue
    u0, u1, v0, v1, z0, z1 = bbox_uv(g)
    if not (z0 >= 3700 and v0 < 0 and v1 > 1.5 and u1 - u0 < 0.2): continue
    if u0 > 56.5: map_mesh_uv(g, lambda u, v, z: (UG0 + (u - 56.94) / 0.12 * (UG1 - UG0), VW0 if v < 0.01 else v, z))
    else: map_mesh_uv(g, lambda u, v, z: (u, VW0 if v < 0.01 else v, z))
    n_e += 1
log.append(f'本館：越屋根の南北の妻の立ち上がり {n_e} 片を外皮の線へ')
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex != L10 or not isinstance(g, r.Mesh): continue
    T = tris(g); c = to_uv_arr(T.mean(1))
    if c[:, 0].max() - c[:, 0].min() < 50: continue                           # 本館の屋根の本体だけ（南の軒などは触らない）
    keep = c[:, 1] >= 0.0
    if keep.all(): continue
    mm = welded_mesh(T[keep]); mm.Normals.ComputeNormals(); new_objs.append((mm, o.Attributes)); drop.add(str(o.Attributes.Id))
    log.append(f'本館：屋根の西の細い帯（越屋根の外、三角形 {int((~keep).sum())}）を消した')
# 7) 西の外壁を立ち上がりの上端まで（窓・口の下の腰の片はそのまま）
# 前の版では 5) で窓・口の下の腰の片まで屋根の下面へ上げてしまい、窓 4 つと遊戯室の口②が埋まっていた（監修の指摘 3a）。
n_up = 0
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex != L17 or not isinstance(g, r.Mesh) or UP_TOP is None: continue
    u0, u1, v0, v1, z0, z1 = bbox_uv(g)
    if not (v0 > -0.36 and v1 < -0.19 and u1 - u0 > 0.2 and 3500 < z1 < 4400): continue
    V = mesh_V(g); V[V[:, 2] > z1 - 5, 2] = UP_TOP; mesh_set(g, V); g.Normals.ComputeNormals(); n_up += 1
log.append(f'本館：西の外壁 {n_up} 片を越屋根の立ち上がりの上端（{UP_TOP:.0f}）まで立ち上げた（元の立ち上がり {len(UPS)} 片は消した）')

# すき間の南の端のガラス（19）：本館の西の外壁の外面（v −0.35）まで
L19 = lidx('19_')
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex == L19 and isinstance(g, r.Mesh):
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if 20.9 < u0 and u1 < 21.1 and v1 > -0.3: map_mesh_uv(g, lambda u, v, z: (u, min(v, -0.35), z))

# ================================================================ 外構：柵 h1.2（60）の南の端を門の柱で止める（詳細設計の依頼 10-22 夕 2）
L60 = lidx('60_')
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex == L60 and isinstance(g, r.Mesh):
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if u0 < -8.45: map_mesh_uv(g, lambda u, v, z: (max(u, -8.45), v, z)); log.append('外構：柵の南の端を u −8.45 に')
FENCE_RET = (R(-8.57, -8.45, 0.96, 1.40, 0.05), -300.0, 900.0)

# ================================================================ 本館：光の筋（トップライト）と屋根材型の太陽光（本館係、10-23夜）
# 決定事項（ユーザー、10-23）：トップライトは架構の線に沿う（スパンごとに同じ、部屋の使い方に合わせない）。
# 2 枚の梁のあいだ（180）の上を開け、垂木はそれぞれ自分の側の梁に載せる（垂木を切らない）ので、すき間がそのまま光の筋になる。
# 範囲は全長（ユーザー、10-23夜：途中で止める設計上の理由が無ければ全体に）：越屋根の東の立ち上がり（v 1.66）から東の軒先（v 15.0）まで。
# 西は越屋根の光の帯から、東は軒先へ抜けて、架構の線がそのまま光の線になる。乳白ガラス（東向きの緩い屋根で直射が入るため）。
# 断熱ガラス戸の線（v 13.5）で外皮を切るので、筋の中（2 枚の梁のあいだ）に固定ガラス（屋根の面の 250 下から筋のガラスの下まで）。
# 架構 2〜19（u 3〜54、両妻の架構は除く）、ホールも同じ（スケルトンを揃える）。
# 3dm の屋根は厚みの無い面（z = 4150 − v/12）。筋の両側に立ち上がり 60（幅 60、水はガラスの上を東へ流れる）、
# その上に乳白ガラス t12（幅 300、v 3.5〜9.7）。筋の内側は垂木の小口をふさぐ板（屋根の面から 150 下まで）。
# 屋根の仕上げは屋根材型の太陽光（金属の屋根と一体）：越屋根の蓋の東の縁（v 1.95）から東の軒先の水切りの手前（v 14.85、ユーザー 10-24：庇の先まで）まで、
# 筋の周りを除く。3dm では屋根の面の 20 上に黒い面を置く（色だけ、目地は描かない）。
import mapbox_earcut as _ec
SL_U = [3.0 * k for k in range(1, 19)]; SL_V = (1.76, 15.0); SL_GL = 13.5; SL_HALF = 0.09
ROOF_Z = lambda v: 4150.0 - v * 1000.0 / 12.0
def zuv(x, y): return ROOF_Z(uv(x, y)[1])
def sheet(poly, dz, li, col=None, mat=None):
    """平面形（穴あり可）を屋根の面から dz 上に、屋根と平行な面で"""
    ms = []
    for p in ([poly] if poly.geom_type == 'Polygon' else list(poly.geoms)):
        if p.area < 1e3: continue
        p = p.simplify(1.0)
        rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
        V2 = np.vstack(rings); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri_ = _ec.triangulate_float64(V2, ends).reshape(-1, 3)
        mm = r.Mesh()
        for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zuv(x, y) + dz))
        for a, b, c in tri_: mm.Faces.AddFace(int(a), int(b), int(c))
        mm.Normals.ComputeNormals(); mm.Compact(); ms.append(mm)
    return ms
def slab(poly, dz0, dz1):
    """屋根の面から dz0〜dz1（屋根と平行）の板"""
    out_ = []
    for p in ([poly] if poly.geom_type == 'Polygon' else list(poly.geoms)):
        p = p.simplify(0.5); V2 = np.asarray(p.exterior.coords)[:-1]; n = len(V2)
        tri_ = _ec.triangulate_float64(V2, np.array([n], dtype=np.uint32)).reshape(-1, 3)
        mm = r.Mesh()
        for dz in (dz0, dz1):
            for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zuv(x, y) + dz))
        for a, b, c in tri_: mm.Faces.AddFace(int(a), int(c), int(b)); mm.Faces.AddFace(int(a + n), int(b + n), int(c + n))
        for i in range(n):
            j = (i + 1) % n; mm.Faces.AddFace(i, j, j + n, i + n)
        mm.Normals.ComputeNormals(); mm.Compact(); out_.append(mm)
    return out_
def new_layer(name, rgb, mat=None):
    for i, l in enumerate(m.Layers):
        if l.Name == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255)
    if mat is not None: L.RenderMaterialIndex = mat
    return m.Layers.Add(L)
MAT_FROST = next((i for i, mt in enumerate(m.Materials) if mt.Name == '乳白ガラス'), -1)
L10T = new_layer('10t_本館_光の筋（乳白ガラス、架構の線）', (225, 236, 242), MAT_FROST if MAT_FROST >= 0 else None)
L10P = new_layer('10p_本館_屋根材型の太陽光（金属の屋根と一体）', (45, 49, 58))
# 屋根の本体（u 0〜57.45 の大きな面）を、筋を抜いた面に作り直す
SLOTS = unary_union([R(u - SL_HALF, u + SL_HALF, SL_V[0], SL_V[1], 0.2) for u in SL_U])
def roof_main_poly(g):
    T = tris(g); ps = [Polygon(t[:, :2]).buffer(0) for t in T]
    return unary_union([q.buffer(0.5) for q in ps if q.area > 1]).buffer(-0.5)
cand = [(i, mm, at) for i, (mm, at) in enumerate(new_objs) if at.LayerIndex == L10 and len(mm.Vertices) > 60]
src = None
if cand: i0, g0, at0 = cand[0]; src = ('new', i0, g0, at0)
else:
    for o in m.Objects:
        g = o.Geometry
        if o.Attributes.LayerIndex == L10 and isinstance(g, r.Mesh) and str(o.Attributes.Id) not in drop:
            c = to_uv_arr(tris(g).mean(1))
            if c[:, 0].max() - c[:, 0].min() > 50: src = ('old', None, g, o.Attributes); break
if src is not None:
    kind_, i0, g0, at0 = src
    RP = roof_main_poly(g0)
    roof_new = sheet(RP.difference(SLOTS), 0.0, L10)
    if kind_ == 'new': new_objs.pop(i0)
    else: drop.add(str(at0.Id))
    for mm in roof_new: new_objs.append((mm, at0))
    a10 = r.ObjectAttributes(); a10.LayerIndex = L10
    at_g = r.ObjectAttributes(); at_g.LayerIndex = L10T
    if MAT_FROST >= 0: at_g.MaterialSource = r.ObjectMaterialSource.MaterialFromObject; at_g.MaterialIndex = MAT_FROST
    for u in SL_U:
        for mm in slab(R(u - 0.15, u - SL_HALF, SL_V[0] - 0.1, SL_V[1], 0.2), 0.0, 60.0): new_objs.append((mm, a10))          # 立ち上がり（南）
        for mm in slab(R(u + SL_HALF, u + 0.15, SL_V[0] - 0.1, SL_V[1], 0.2), 0.0, 60.0): new_objs.append((mm, a10))          # 立ち上がり（北）
        for mm in slab(R(u - SL_HALF, u + SL_HALF, SL_V[0] - 0.1, SL_V[0], 0.05), 0.0, 60.0): new_objs.append((mm, a10))      # 立ち上がり（西の端）
        for mm in slab(R(u - 0.15, u + 0.15, SL_V[0] - 0.1, SL_V[1], 0.2), 60.0, 72.0): new_objs.append((mm, at_g))           # 乳白ガラス t12（東は軒先で止める、水はそのまま落ちる）
        for mm in slab(R(u - SL_HALF, u + SL_HALF, SL_GL - 0.006, SL_GL + 0.006, 0.05), -250.0, 60.0): new_objs.append((mm, at_g))  # 外皮の線の固定ガラス
        for uu in (u - SL_HALF - 0.012, u + SL_HALF):                                                                       # 筋の内側の板（垂木の小口をふさぐ）
            for mm in slab(R(uu, uu + 0.012, SL_V[0], SL_V[1], 0.2), -150.0, 0.0): new_objs.append((mm, a10))
    pv = R(0.3, 57.15, 1.95, 14.85, 0.25).intersection(RP).difference(unary_union([R(u - 0.25, u + 0.25, SL_V[0] - 0.2, SL_V[1] + 0.2, 0.2) for u in SL_U]))
    a_pv = r.ObjectAttributes(); a_pv.LayerIndex = L10P
    for mm in sheet(pv, 20.0, L10P): new_objs.append((mm, a_pv))
    log.append(f'本館：光の筋 {len(SL_U)} 本（架構 2〜19、2 枚の梁のあいだ 180、v {SL_V[0]}〜{SL_V[1]}＝越屋根から軒先まで、乳白ガラス）、'
               f'屋根材型の太陽光 {pv.area / 1e6:.0f} m²（10p）')
    PV_AREA = pv.area / 1e6
    # 閉じる部屋の換気扇の出口（連携 10-23夜9、本館係）：天井（梁の下端）の換気扇からダクト φ100 を垂木のあいだに真上へ、
    # 屋根の上の低い換気の頭（ベントキャップ、350 角・高さ 200、屋根の金属と同じ黒）。西の外壁へ横に引くと西吹き抜けを横切るので、真上に抜く。
    VENTS = [(19.5, 3.0, '静養室'), (32.2, 3.1, '多目的便所'), (41.3, 3.0, '職員の個室')]
    for uu, vv, nm in VENTS:
        a_v = r.ObjectAttributes(); a_v.LayerIndex = L10; a_v.Name = f'換気の頭（{nm}の換気扇、φ100）'
        for mm in slab(R(uu - 0.175, uu + 0.175, vv - 0.175, vv + 0.175, 0.05), 20.0, 220.0): new_objs.append((mm, a_v))
    log.append(f'本館：閉じる部屋の換気の頭 {len(VENTS)} 個（屋根の上）')
# 機械室（おむすび）に蓄電池の場所（ユーザー、10-23：夜と停電のときに使う、園は災害時の拠点にもなる）。
# 機械室は 3dm では塊なので、中に箱を置いて場所だけ示す（約 1.2×2.0 = 2.4 m²、h1.6、家具程度）。
L35 = lidx('35_')
mech = [foot(o.Geometry) for o in m.Objects if o.Attributes.LayerIndex == L35]
mech = unary_union([g for g in mech if g is not None])
if not mech.is_empty:
    c = mech.centroid; cu, cv = uv(c.x, c.y)
    bat = R(cu - 1.0, cu + 1.0, cv - 0.6, cv + 0.6, 0.1)
    if mech.buffer(-300).contains(bat):
        L35B = new_layer('35b_機械室_蓄電池（家具程度、約 2.4 m²）', (70, 110, 90))
        a35 = r.ObjectAttributes(); a35.LayerIndex = L35B; a35.Name = '蓄電池（屋根材型の太陽光、夜と停電のとき）'
        tmp = r.File3dm(); Kt = Kit(tmp); Kt.prism(bat, 0.0, 1600.0, L35B)
        for o2 in tmp.Objects: new_objs.append((o2.Geometry, a35))
        log.append(f'機械室：蓄電池の箱（u {cu:.1f}・v {cv:.1f}、2.0×1.2×h1.6、35b）')

# ================================================================ 西館：光の筋と屋根材型の太陽光（西館係、10-23夜、本館係の依頼 連携10-23夜5の6）
# 本館と同じ考えと寸法：架構の線ごとに、2 枚の梁のあいだ（180）の上を開けて光の筋にする（垂木はそれぞれ自分の側の梁に載せる）。
# 筋の両側と東の端（高い側、水は西へ流れる）に立ち上がり 60、その上に乳白ガラス t12（幅 300）、筋の内側に垂木の小口をふさぐ板 150。
# 範囲：越屋根の西の立ち上がり（v −1.96）から西の軒先まで（10-24、ユーザー：本館と同じに全長）。軒先ではガラスを止め端の立ち上がりは付けない、外壁の内面の線に固定ガラス。南の端の架構（u≈21）は除く。
# 遊戯室の吊り材の受け（2 枚の梁に渡した鋼の板）は筋の下に影を落とす。
# 屋根は東 8.15 → 西 4.65 を幅いっぱいに流すねじれた面なので、高さは元の屋根（RM20）に鉛直の線を当てて 0.5 m の格子ごとに取る。
# 太陽光：越屋根の蓋の西の縁（v −2.25）から軒先の 0.15 手前まで（10-24）、筋の周り ±0.25 を除く。屋根の面の 20 上の黒い面（20p）。
WS_W = pickle.load(open(WNPKL, 'rb')).get('WS', WN)
def roof_z(P):
    P = np.asarray(P, float); z = roof_bottom(P)
    if np.isnan(z).any():
        vv = RM20.vertices; bad = np.where(np.isnan(z))[0]
        for k in bad: z[k] = vv[np.argmin(((vv[:, :2] - P[k, :2]) ** 2).sum(1)), 2]
    return z
def drape(poly, dz0, dz1=None, cell=500.0):
    """平面形を屋根の面に沿わせる（cell の格子で切って高さを取る）。dz1 があれば dz0〜dz1 の板（格子ごとの小さな角柱の集まり）"""
    from shapely.geometry import box
    out_ = r.Mesh()
    if poly.is_empty: return out_
    x0, y0, x1, y1 = poly.bounds
    for gx in np.arange(x0, x1, cell):
        for gy in np.arange(y0, y1, cell):
            pc = poly.intersection(box(gx, gy, gx + cell, gy + cell))
            for p in ([pc] if pc.geom_type == 'Polygon' else [q for q in getattr(pc, 'geoms', []) if q.geom_type == 'Polygon']):
                if p.area < 50: continue
                p = p.simplify(0.5)
                rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
                V2 = np.vstack(rings); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
                T = _ec.triangulate_float64(V2, ends).reshape(-1, 3); zr = roof_z(V2)
                b = len(out_.Vertices); n = len(V2)
                if dz1 is None:
                    for (x, y), z in zip(V2, zr): out_.Vertices.Add(float(x), float(y), float(z + dz0))
                    for a, b2, c in T: out_.Faces.AddFace(int(a + b), int(b2 + b), int(c + b))
                else:
                    for dz in (dz0, dz1):
                        for (x, y), z in zip(V2, zr): out_.Vertices.Add(float(x), float(y), float(z + dz))
                    for a, b2, c in T:
                        out_.Faces.AddFace(int(a + b), int(c + b), int(b2 + b)); out_.Faces.AddFace(int(a + b + n), int(b2 + b + n), int(c + b + n))
                    k0 = 0
                    for ring in rings:
                        L_ = len(ring)
                        for i in range(L_):
                            i0 = k0 + i; i1 = k0 + (i + 1) % L_
                            out_.Faces.AddFace(int(b + i0), int(b + i1), int(b + i1 + n), int(b + i0 + n))
                        k0 += L_
    out_.Normals.ComputeNormals(); out_.Compact()
    return out_
# 架構の線（2 枚の梁のあいだの芯）を梁から求める
bm = {str(at.Id): mm for mm, at in beam_new}
lines_ = []
for o in m.Objects:
    if o.Attributes.LayerIndex != L22B: continue
    g = bm.get(str(o.Attributes.Id), o.Geometry)
    P = tris(g).reshape(-1, 3)[:, :2]
    if len(P) < 3: continue
    c = P.mean(0); X = P - c; w_, vec = np.linalg.eigh(X.T @ X); ax = vec[:, -1]
    lines_.append((c, ax if ax[0] >= 0 else -ax))
pairs = []; used = set()
for i, (c1, a1) in enumerate(lines_):
    if i in used: continue
    nrm = np.array([-a1[1], a1[0]])
    js = [j for j, (c2, a2) in enumerate(lines_) if j != i and j not in used and abs(np.dot(c2 - c1, nrm)) < 400]
    if not js: continue
    j = min(js, key=lambda j: abs(np.dot(lines_[j][0] - c1, nrm))); used |= {i, j}
    c2, a2 = lines_[j]; ax = (a1 + a2); ax /= np.linalg.norm(ax)
    off = np.dot(c2 - c1, np.array([-ax[1], ax[0]])) / 2.0
    cc = c1 + np.array([-ax[1], ax[0]]) * off
    pairs.append((cc, ax))
WSL = WS_W.buffer(1.0)                 # 10-24（ユーザー、本館と同じ）：越屋根から軒先まで
EASTV = -1.96                          # 越屋根の西の立ち上がりの外面
WSi_W = WS_W.buffer(-150.0, join_style=2)   # 外壁の内面（外皮の線の固定ガラス）
slits = []
for cc, ax in pairs:
    uc, vc = uv(*cc)
    if uc < 22.0 or uc > 50.5: continue
    nrm = np.array([-ax[1], ax[0]])
    p0 = cc - ax * 20000; p1 = cc + ax * 20000
    band = Polygon([p0 - nrm * 90, p1 - nrm * 90, p1 + nrm * 90, p0 + nrm * 90])
    zone = WSL.intersection(Polygon([xy(uc - 3, EASTV), xy(uc + 3, EASTV), xy(uc + 3, -30), xy(uc - 3, -30)]))
    s_ = band.intersection(zone)
    if s_.geom_type != 'Polygon' or s_.area < 1e5: continue
    # 筋の長さの両端（t0：西の端、t1：東の端）
    T_ = [np.dot(np.array(pt) - cc, ax) for pt in s_.exterior.coords]
    slits.append((cc, ax, nrm, min(T_), max(T_)))
def strip(cc, ax, nrm, t0, t1, a, b_):
    return Polygon([cc + ax * t0 + nrm * a, cc + ax * t1 + nrm * a, cc + ax * t1 + nrm * b_, cc + ax * t0 + nrm * b_])
if slits:
    L20T = new_layer('20t_西館_光の筋（乳白ガラス、架構の線）', (225, 236, 242), MAT_FROST if MAT_FROST >= 0 else None)
    L20P = new_layer('20p_西館_屋根材型の太陽光（金属の屋根と一体）', (45, 49, 58))
    a20 = r.ObjectAttributes(); a20.LayerIndex = L20
    at_g2 = r.ObjectAttributes(); at_g2.LayerIndex = L20T
    if MAT_FROST >= 0: at_g2.MaterialSource = r.ObjectMaterialSource.MaterialFromObject; at_g2.MaterialIndex = MAT_FROST
    SL20 = unary_union([strip(cc, ax, nrm, t0, t1, -90, 90) for cc, ax, nrm, t0, t1 in slits])
    # 屋根の本体（20 の面それぞれ）から筋を抜く
    roofs20 = []
    for o in m.Objects:
        if o.Attributes.LayerIndex != L20 or not isinstance(o.Geometry, r.Mesh): continue
        fp = foot(o.Geometry)
        if fp is None: continue
        roofs20.append(fp)
        if fp.intersection(SL20).area < 1e4: continue
        drop.add(str(o.Attributes.Id))
        new_objs.append((drape(fp.difference(SL20), 0.0), o.Attributes))
    RP20 = unary_union(roofs20)
    for cc, ax, nrm, t0, t1 in slits:
        uc_ = uv(*cc)[0]; e = 1 if np.dot(ax, np.array(xy(uc_, EASTV)) - np.array(xy(uc_, -10))) > 0 else -1     # 東（高い側）の向き
        tE = t1 if e > 0 else t0; tW = t0 if e > 0 else t1
        lo, hi = min(tW, tE), max(tW, tE)
        new_objs.append((drape(strip(cc, ax, nrm, lo, hi, -150, -90), 0.0, 60.0), a20))     # 立ち上がり
        new_objs.append((drape(strip(cc, ax, nrm, lo, hi, 90, 150), 0.0, 60.0), a20))
        # 東の端は越屋根の西の立ち上がりがふさぐ（端の立ち上がりは足さない）
        glo, ghi = min(tW, tE), max(tW, tE)                                    # ガラスは越屋根の立ち上がりから西の軒先まで（水はそのまま軒樋へ）
        new_objs.append((drape(strip(cc, ax, nrm, glo, ghi, -150, 150), 60.0, 72.0), at_g2))    # 乳白ガラス t12
        _ln = LineString([cc + ax * (tW - 2000 * e), cc + ax * (tW + 4000 * e)]).intersection(WSi_W.exterior)
        _pts = [_ln] if _ln.geom_type == 'Point' else list(getattr(_ln, 'geoms', []))
        if _pts:
            tS = min((np.dot(np.array([q.x, q.y]) - cc, ax) for q in _pts), key=lambda t: abs(t - tW))
            new_objs.append((drape(strip(cc, ax, nrm, tS - 6, tS + 6, -90, 90), -250.0, 60.0), at_g2))   # 外皮の線の固定ガラス（2枚の梁のあいだ）
        for a_, b_ in ((-102, -90), (90, 102)):                                                  # 筋の内側の板
            new_objs.append((drape(strip(cc, ax, nrm, t0, t1, a_, b_), -150.0, 0.0), a20))
    pv20 = RP20.buffer(-150.0, join_style=2)                  # 軒先の水切り150を残す（10-24、本館と同じ）
    pv20 = pv20.difference(Polygon([xy(u_, 1.0) for u_ in np.arange(19, 53.1, 0.5)] + [xy(u_, -2.25) for u_ in np.arange(53, 18.9, -0.5)]))
    pv20 = pv20.difference(unary_union([strip(cc, ax, nrm, t0 - 200, t1 + 200, -250, 250) for cc, ax, nrm, t0, t1 in slits]))
    a_pv2 = r.ObjectAttributes(); a_pv2.LayerIndex = L20P
    new_objs.append((drape(pv20, 20.0), a_pv2))
    log.append(f'西館：光の筋 {len(slits)} 本（u ' + '・'.join(f'{uv(*s[0])[0]:.0f}' for s in slits) +
               f'、2 枚の梁のあいだ 180、越屋根から軒先まで、乳白ガラス、20t）、屋根材型の太陽光 {pv20.area / 1e6:.0f} m²（20p）')

# ================================================================ 書き出し（桁を差し替え、腰壁を足す）
out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for o in m.Objects:
    if str(o.Attributes.Id) in drop or str(o.Attributes.Id) in col_drop or str(o.Attributes.Id) in beam_drop: continue
    out.Objects.Add(o.Geometry, o.Attributes)
for mm, at in new_objs + col_new + beam_new: out.Objects.AddMesh(mm, at)
K = Kit(out)
ZF2 = 3250.0
K.prism(R(21.16, 32.95, -1.96, -1.90, 0.1), ZF2, ZF2 + 1100.0, L38)       # 2 階の東の縁（東の帯への吹き抜け）
K.prism(R(32.97, 33.03, -5.0, -1.96, 0.02), ZF2, ZF2 + 1100.0, L38)       # 2 階の北の口（遊戯室の吹き抜け）
log.append('西館：2 階の腰壁 h1100（東の縁 u 21.2–33、北の口 u 33）')
K.prism(FENCE_RET[0], FENCE_RET[1], FENCE_RET[2], L60); log.append('外構：柵を門の柱（u −8.45・v 0.96）へ折り返した')
# 遊戯室の北の口（口②、u 45.6–47.6、柱 u45・48 のあいだ、10-24 ユーザー）に引き戸（ユーザー、10-23：要るなら引き戸で）。
# ふだんは北へ引いて開けておき、先生がいないとき（高い遊具）・午睡のとき（音）・冬（大きな気積を分ける）に閉める。
# 遊戯室の側は柱が壁の内面に接していて戸が走れないので、すき間の側（西館の東の壁の外面 v −0.9 の外）を走る上吊り。
# 北の引きしろ u 47.6–49.7（すき間には柱が無い）。
L19C = None
for i, l in enumerate(out.Layers):
    if l.Name.startswith('19c_'): L19C = i
if L19C is None:
    lay = r.Layer(); lay.Name = '19c_西館_室内の引き戸（木）'; lay.Color = (165, 120, 75, 255); L19C = out.Layers.Add(lay)
K.prism(R(45.55, 47.65, -0.88, -0.84, 0.05), 10.0, 2400.0, L19C)           # 戸（閉めた位置、幅 2.1・厚さ 40）
K.prism(R(45.5, 49.75, -0.89, -0.85, 0.05), 2410.0, 2470.0, L19C)          # 上吊りのレール（開口の上の壁に）
log.append('西館：遊戯室の北の口（口②、u45.6–47.6）に上吊りの片引き戸 2.1×2.4（すき間の側、北へ引く、19c）')
out.Write(OUT, 8)
print('\n'.join(log)); print('written', OUT, len(out.Objects))
