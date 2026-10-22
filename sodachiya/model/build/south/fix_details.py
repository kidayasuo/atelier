"""納まりの整理（見せる架構は全部見せ、隠すものは全部隠す）
使い方: python3 fix_details.py IN.3dm OUT.3dm data/wnew.pkl
本館
- 西の外壁（r=205 m の線、厚さ 150 で柱の真ん中を通っていた）を柱の奥行き 400 と同じ厚さ 420 にし、柱と桁を壁の中に納める
  （西吹き抜けの西の内壁は「白い反射面」＝柱の出っ張りなしの平らな面。外にも柱・桁は出ない）。
- 北の妻壁（厚さ 120 で柱 180 の真ん中）を柱の幅 180 にそろえ、柱を壁の中に。外側の梁は南の妻と同じく外に見せ、屋根を 0.3 延ばして覆う。
- 桁（楕円 200×400）：西の桁は北の妻壁の中で止める（外へ 0.6 突き出ていた）。東の桁は北の端を外側の梁の外面まで。南の端はそのまま（南の軒の下で見せる）。
- 縁側の妻のガラス（16、u=0・57 の v 12–13.5）を柱の面から始める。
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
n_w = n_g = 0
for o in m.Objects:
    g = o.Geometry; li = o.Attributes.LayerIndex
    if li == L17 and isinstance(g, r.Mesh):
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if v0 > -0.09 and v1 < 0.09 and u1 - u0 > 0.2:                     # 西の外壁（r=205 の線）
            map_mesh_uv(g, lambda u, v, z: (u, v * 0.21 / 0.075, z)); n_w += 1
        elif 56.9 < u0 and u1 < 57.1 and v0 > -0.05 and v1 > 11.5:            # 北の妻壁
            map_mesh_uv(g, lambda u, v, z: (57.0 + (u - 57.0) * 1.5, v, z)); n_g += 1
    if li == L10 and isinstance(g, r.Mesh):                                   # 屋根：北の端を 0.3 延ばす
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if u1 > 56.9: map_mesh_uv(g, lambda u, v, z: (57.30 if u > 56.98 else u, v, z))
    if li == L16 and isinstance(g, r.Mesh):                                   # 縁側の妻のガラス：柱の面から
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if (u1 - u0) < 0.1 and v0 > 11.9 and v0 < 12.1 and v1 > 13:
            map_mesh_uv(g, lambda u, v, z: (u, max(v, 12.2), z))
log.append(f'本館：西の外壁 {n_w} 片を厚さ 420 に、北の妻壁 {n_g} 片を 180 に、屋根の北の端 u 57.3')
# 西の柱の頭の、桁を抱く膨らみ（v −0.28 まで）が壁の外に出るので、壁の外面 v −0.20 で平らに（桁も壁の中なので抱く形は見えない）
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
L11A = lidx('11a'); col_new = []; col_drop = set()
for o in m.Objects:
    if o.Attributes.LayerIndex != L11A: continue
    T = tris(o.Geometry); U = to_uv_arr(T.reshape(-1, 3))
    if U[:, 1].mean() > 1 or U[:, 1].min() > -0.205: continue
    mm = welded_mesh(T); map_mesh_uv(mm, lambda u, v, z: (u, max(v, -0.20), z)); mm.Compact()
    col_new.append((mm, o.Attributes)); col_drop.add(str(o.Attributes.Id))
log.append(f'本館：西の柱 {len(col_new)} 本の頭の膨らみを壁の外面で平らに')

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
        ub = 57.0 if vc < 6 else 57.2                    # 西の桁は北の妻壁の中で止める、東は外側の梁の外面まで
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
    if not (v0 > -0.22 and v1 < 0.22 and z1 < 3950 and u1 - u0 > 0.2): continue
    V = mesh_V(g); top = V[:, 2] > z1 - 5; zb = roof10_bottom(V[top])
    ok = ~np.isnan(zb)
    if ok.any():
        Vt = V[top]; Vt[ok, 2] = np.maximum(Vt[ok, 2], zb[ok] - 5.0); V[top] = Vt; mesh_set(g, V); g.Normals.ComputeNormals(); n_t += 1
log.append(f'本館：西の外壁 {n_t} 片の天端を屋根の下面まで')

# ================================================================ 外構：柵 h1.2（60）の南の端を門の柱で止める（詳細設計の依頼 10-22 夕 2）
L60 = lidx('60_')
for o in m.Objects:
    g = o.Geometry
    if o.Attributes.LayerIndex == L60 and isinstance(g, r.Mesh):
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if u0 < -8.45: map_mesh_uv(g, lambda u, v, z: (max(u, -8.45), v, z)); log.append('外構：柵の南の端を u −8.45 に')
FENCE_RET = (R(-8.57, -8.45, 0.96, 1.40, 0.05), -300.0, 900.0)

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
out.Write(OUT, 8)
print('\n'.join(log)); print('written', OUT, len(out.Objects))
