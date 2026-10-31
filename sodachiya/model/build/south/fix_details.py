"""納まりの整理（外皮は架構の外に連続させ、架構は室内に見せる）
使い方: python3 fix_details.py IN.3dm OUT.3dm data/wnew.pkl
本館
- 西の外壁（r=205 m の線、厚さ 150 で柱の真ん中を通っていた）を柱の外（v −0.35〜−0.20）へ。柱・桁は西吹き抜けに見せる。窓も壁の中へ。
- 北の妻壁（厚さ 120 で柱の真ん中、外の梁は外に出ていた）を北の端の架構の外（u 57.19〜57.34）へ。縁側の妻のガラスも同じ線へ。
- 屋根を西 v −0.45・北 u 57.64 まで延ばして外皮を覆う（北はけらば 0.3、ユーザー 10-24）。
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
        map_mesh_uv(g, lambda u, v, z: (UG1 + 0.30 if u > 56.98 else u, -0.45 if v < -0.15 else v, z))   # 北のけらば 0.3（10-24）
    if li == L16:                                                             # 縁側の妻のガラス
        u0, u1, v0, v1, z0, z1 = bbox_uv(g)
        if (u1 - u0) < 0.1 and 11.9 < v0 < 12.1 and v1 > 13:
            if u0 > 56: map_mesh_uv(g, lambda u, v, z: (u + 0.245, v, z))       # 北：妻壁の線（外の梁の外）へ
            else: map_mesh_uv(g, lambda u, v, z: (u, max(v, 12.2), z))        # 南：柱の面から（妻は 2 枚の梁のあいだのまま）
log.append(f'本館：西の外壁 {n_w} 片を柱の外（v −0.35〜−0.20）へ、窓 {n_o} 枚も。北の妻壁 {n_g} 片を架構の外（u 57.19〜57.34）へ。屋根を西 v −0.45・北 u 57.64（けらば 0.3）まで')
def closed_mesh(g):
    """押し出し（柱・梁）は閉じた網目で（10-24夜、西館係）。三角形のスープから溶接すると、側面と端の面の分け方が
    違うので T 字の継ぎ目が残り、閉じない（干渉の一覧の「閉じていない物」に出て、削る段にも入らない）。"""
    if isinstance(g, r.Extrusion):
        import solids
        vf = solids.extrusion_vf(g)
        if vf is not None:
            V_, F_, _ = solids.repair_solid(*vf); mm = r.Mesh()      # 厚みの無い片を捨て、面を外向きに（10-25 監修）
            for x_, y_, z_ in V_: mm.Vertices.Add(float(x_), float(y_), float(z_))
            for a_, b_, c_ in F_: mm.Faces.AddFace(int(a_), int(b_), int(c_))
            return mm
    return welded_mesh(tris(g))
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
# 10-28（監修の項 20261027-2346 の 11a）：柱は押し出しのまま、輪郭を線分と円弧だけに作り直す（前は柱の頭の曲線が 80 点の NURBS で、
# 1 本 最大 127 KB。西の柱は網目にしてから平らにしていた）。穴（桁の楕円）はそのまま。曲線は 0.3 mm 以内の円弧の並びに。
def _col_rebuild(g, vmin=None, tol=0.3):
    """（10-28、監修の項 20261027-2346 の 11a）柱の押し出し g の外の輪郭を、線分と円弧だけに作り直す（穴＝桁の楕円はそのまま）。vmin：v がこれより小さい所は v=vmin の線へ"""
    pl = g.GetProfilePlane(0.0)
    O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z]); X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
    to2 = lambda p: np.array([(np.array([p.X, p.Y, p.Z]) - O) @ X, (np.array([p.X, p.Y, p.Z]) - O) @ Y])
    def vof(q):
        P = O + q[0] * X + q[1] * Y; return uv(P[0], P[1])[1]
    pc = g.Profile3d(0, 0.0)
    segs = [pc.SegmentCurve(i) for i in range(pc.SegmentCount)] if isinstance(pc, r.PolyCurve) else [pc]
    xl = None
    if vmin is not None:
        v0_, v1_ = vof(np.array([0.0, 0.0])), vof(np.array([1000.0, 0.0]))
        xl = (vmin - v0_) / ((v1_ - v0_) / 1000.0)
        sx = np.sign((v1_ - v0_))
    runs = []                                    # [(kind, pts)]：kind 'L' 線、'C' 曲線
    for s in segs:
        lin = isinstance(s, r.LineCurve) or s.IsLinear(0.01)
        d = s.Domain; ts = [d.T0, d.T1] if lin else np.linspace(d.T0, d.T1, 1201)
        Q = np.array([to2(s.PointAt(t)) for t in ts])
        if xl is not None:
            bad = (Q[:, 0] - xl) * sx < 0
            if bad.any():
                out, kinds = [], []
                for i in range(len(Q)):
                    if i and bad[i] != bad[i - 1]:
                        a_, b_ = Q[i - 1], Q[i]; f = (xl - a_[0]) / (b_[0] - a_[0]); c_ = a_ + f * (b_ - a_); c_[0] = xl
                        out.append(c_); kinds.append('x')
                    q = Q[i].copy()
                    if bad[i]: q[0] = xl
                    out.append(q); kinds.append('b' if bad[i] else 'g')
                # 連続する同じ種類で分ける（x は両方に入る）
                cur, ck = [out[0]], kinds[0] if kinds[0] != 'x' else None
                for q, k in zip(out[1:], kinds[1:]):
                    if k == 'x':
                        cur.append(q); runs.append(('L' if (ck == 'b' or lin) else 'C', np.array(cur))); cur = [q]; ck = None; continue
                    if ck is None: ck = k
                    cur.append(q)
                if len(cur) > 1: runs.append(('L' if (ck == 'b' or lin) else 'C', np.array(cur)))
                continue
        runs.append(('L' if lin else 'C', Q))
    # 曲線の並びを円弧に（3 点の円弧、ずれ tol 以下になるまで二つに分ける）
    out = []
    def arc_or_split(Q, i, j):
        a, m_, b = Q[i], Q[(i + j) // 2], Q[j]
        d_ = 2 * (a[0] * (m_[1] - b[1]) + m_[0] * (b[1] - a[1]) + b[0] * (a[1] - m_[1]))
        P = Q[i:j + 1]
        if abs(d_) > 1e-9:
            ux = ((a @ a) * (m_[1] - b[1]) + (m_ @ m_) * (b[1] - a[1]) + (b @ b) * (a[1] - m_[1])) / d_
            uy = ((a @ a) * (b[0] - m_[0]) + (m_ @ m_) * (a[0] - b[0]) + (b @ b) * (m_[0] - a[0])) / d_
            c = np.array([ux, uy]); R = np.linalg.norm(a - c)
            dev = np.abs(np.linalg.norm(P - c, axis=1) - R).max()
            if dev < tol and R < 1e6: out.append(('A', a, m_, b)); return
        t_ = b - a; L = np.linalg.norm(t_)
        if L > 0:
            dl = np.abs((P - a) @ np.array([-t_[1], t_[0]]) / L).max()
            if dl < tol: out.append(('L', a, b)); return
        if j - i < 4: out.append(('L', a, b)); return
        k = (i + j) // 2; arc_or_split(Q, i, k); arc_or_split(Q, k, j)
    for kind, Q in runs:
        if np.linalg.norm(Q[-1] - Q[0]) < 1e-6 and len(Q) < 3: continue
        if kind == 'L': out.append(('L', Q[0], Q[-1]))
        else: arc_or_split(Q, 0, len(Q) - 1)
    # 長さ 0 の線を捨て、端を前の片の終わりにそろえる
    P3 = lambda q: r.Point3d(float(q[0]), float(q[1]), 0.0)
    pc2 = r.PolyCurve(); prev = None; n_arc = 0
    clean = [o for o in out if np.linalg.norm(o[-1] - o[1]) > 1e-4]
    first = clean[0][1]
    for k_, o in enumerate(clean):
        a = prev if prev is not None else o[1]
        b = first if k_ == len(clean) - 1 else o[-1]
        if o[0] == 'L': pc2.Append(r.LineCurve(P3(a), P3(b)))
        else: pc2.Append(r.Arc(P3(a), P3(o[2]), P3(b))); n_arc += 1
        prev = b
    holes = []
    for k in range(1, g.ProfileCount):
        nc = g.Profile3d(k, 0.0).ToNurbsCurve()
        for i in range(len(nc.Points)):
            p = nc.Points[i]; w = p.W if p.W else 1.0
            q = np.array([p.X / w, p.Y / w, p.Z / w]) - O
            nc.Points[i] = r.Point4d(float(q @ X) * w, float(q @ Y) * w, 0.0, w)
        holes.append(nc)
    e = r.Extrusion()
    if not e.SetPathAndUp(g.PathStart, g.PathEnd, pl.YAxis): return None
    if not e.SetOuterProfile(pc2, True): return None
    for h in holes:
        if not e.AddInnerProfile(h): return None
    return e, len(clean), n_arc
EXT_COL = {}
L11A = lidx('11a'); col_new = []; col_drop = set(); _nc_w = _nc_e = 0
for o in m.Objects:
    if o.Attributes.LayerIndex != L11A or not isinstance(o.Geometry, r.Extrusion): continue
    T = tris(o.Geometry); U = to_uv_arr(T.reshape(-1, 3))
    west = U[:, 1].mean() < 1 and U[:, 1].min() < -0.205
    res_ = _col_rebuild(o.Geometry, -0.20 if west else None)
    if res_ is None:
        if west:
            mm = closed_mesh(o.Geometry); map_mesh_uv(mm, lambda u, v, z: (u, max(v, -0.20), z)); mm.Compact()
            col_new.append((mm, o.Attributes)); col_drop.add(str(o.Attributes.Id))
        continue
    EXT_COL[str(o.Attributes.Id)] = res_[0]
    if west: _nc_w += 1
    else: _nc_e += 1
log.append(f'本館：柱 {_nc_w + _nc_e} 本の輪郭を線分と円弧に（押し出しのまま）、西の柱 {_nc_w} 本の頭の膨らみを柱の外面（壁の内面）で平らに。網目にした柱 {len(col_new)}')

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
def ellipse_spans(vc, zc, ua, ub, li, name, N=48):
    """10-28（監修の項 20261028-0843 の 11c）：桁をスパンごとの真っすぐな楕円（幅 200×高さ 400）の押し出しに。
    軸は架構の線（u = 3k）の節点 xy(u, vc) を結ぶ弦、断面は軸に直角な楕円、端は架構の線（放射の線）の鉛直な面で留める
    （となりのスパンの片とちょうど合う）。前は 57 m の弧に沿う管の網目で、Rhino 版で 1 本 150 KB。"""
    nd = [3.0 * k for k in range(0, 20) if ua + 0.01 < 3.0 * k < ub - 0.01]
    segs = [(a_, b_, a_, b_) for a_, b_ in zip(nd, nd[1:])]                     # (端 a, 端 b, 弦の節点 a, 弦の節点 b)
    if segs and ua < nd[0] - 0.01: segs[0] = (ua, segs[0][1], nd[0], nd[1])     # 両端の短い出（南の軒の下 u<0、北 u57〜57.19）は、となりのスパンの弦をそのまま延ばす
    if segs and ub > nd[-1] + 0.01: segs[-1] = (segs[-1][0], ub, nd[-2], nd[-1])
    out_ = []
    for a_, b_, ca_, cb_ in segs:
        A_, B_ = np.asarray(xy(ca_, vc), float), np.asarray(xy(cb_, vc), float)
        d_ = (B_ - A_) / np.linalg.norm(B_ - A_); h_ = np.array([d_[1], -d_[0]])
        ring = [(A_ + 100.0 * math.cos(t) * h_, zc + 200.0 * math.sin(t)) for t in np.linspace(0, 2 * math.pi, N, endpoint=False)]
        V_ = []
        for uu in (a_, b_):
            P0 = np.asarray(xy(uu, vc), float)
            rn = np.asarray(xy(uu, vc + 0.001), float) - P0; rn /= np.linalg.norm(rn)
            nrm = np.array([-rn[1], rn[0]])                              # 架構の線（放射）の面の法線（水平）
            for q, z_ in ring:
                s_ = float(np.dot(P0 - q, nrm) / np.dot(d_, nrm))           # 軸の向きに動かして端の面へ
                V_.append((*(q + s_ * d_), z_))
        mm = r.Mesh()
        for x_, y_, z_ in V_: mm.Vertices.Add(float(x_), float(y_), float(z_))
        for k in range(N):
            mm.Faces.AddFace(k, (k + 1) % N, N + (k + 1) % N, N + k)
        for k in range(1, N - 1):
            mm.Faces.AddFace(0, k + 1, k); mm.Faces.AddFace(N, N + k, N + k + 1)
        Vn = np.array(V_); F_ = [(mm.Faces[i][0], mm.Faces[i][1], mm.Faces[i][2]) for i in range(mm.Faces.Count)]
        vol = sum(np.dot(Vn[a], np.cross(Vn[b], Vn[c])) for a, b, c in F_)
        if vol < 0:
            mm2 = r.Mesh()
            for x_, y_, z_ in V_: mm2.Vertices.Add(float(x_), float(y_), float(z_))
            for i in range(mm.Faces.Count):
                f = mm.Faces[i]
                if f[2] == f[3]: mm2.Faces.AddFace(f[0], f[2], f[1])
                else: mm2.Faces.AddFace(f[0], f[3], f[2], f[1])
            mm = mm2
        mm.Normals.ComputeNormals(); mm.Compact()
        at = r.ObjectAttributes(); at.LayerIndex = li; at.Name = name
        out_.append((mm, at))
    return out_
new_objs = []; drop = set()
for o in m.Objects:
    if o.Attributes.LayerIndex == L11C:
        u0, u1, v0, v1, z0, z1 = bbox_uv(o.Geometry); vc = (v0 + v1) / 2; zc = (z0 + z1) / 2
        ub = 57.19                                       # 北の端の架構（外の梁の外面）で止める（妻壁の内側）
        new_objs += ellipse_spans(vc, zc, u0, ub, L11C, '桁（西）' if vc < 6 else '桁（東）'); drop.add(str(o.Attributes.Id))

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
# 10-29（監修の項 20261028-2355 の D）：架構の柱（輪郭が架構の面、道が厚みの向き）は架構の面の中（水平）だけで動かす。前は壁から出る向きに
# そのまま押したので、柱が厚みの向きに 10〜95 ずれて 2 枚の梁の板に重なった。
def _col_hd(g):
    if not isinstance(g, r.Extrusion): return None
    a_, b_ = g.PathStart, g.PathEnd; pv_ = np.array([b_.X - a_.X, b_.Y - a_.Y])
    if np.linalg.norm(pv_) < 1.0 or abs(b_.Z - a_.Z) > 1.0: return None
    pv_ = pv_ / np.linalg.norm(pv_); return np.array([-pv_[1], pv_[0]])
for o in m.Objects:
    if o.Attributes.LayerIndex not in (L22A, L22D): continue      # 柱と桁（角の丸みを弦で渡る桁が壁から出ていた）
    hd_c = _col_hd(o.Geometry) if o.Attributes.LayerIndex == L22A else None
    for _ in range(6):
        f = foot(o.Geometry).convex_hull
        out = f.difference(WNi)
        if out.area < 50: break
        pts = [Point(p) for p in np.array(f.exterior.coords) if not WNi.contains(Point(p))]
        if not pts: break
        far = max(pts, key=lambda p: WNi.exterior.distance(p))
        near = nearest_points(WNi.exterior, far)[0]
        d = np.array([near.x - far.x, near.y - far.y]); L = np.linalg.norm(d)
        if L < 0.5: break
        if hd_c is not None:
            c_ = float(hd_c @ (d / L))
            if abs(c_) < 0.2: break                                   # 壁が厚みの向きに当たる（妻）：架構の面の中では動かせない
            move_xy(o.Geometry, hd_c * np.sign(c_) * (L + 3.0) / abs(c_))
        else:
            move_xy(o.Geometry, d / L * (L + 3.0))
        worst = max(worst, L)
    n_c += 1
log.append(f'西館：柱・桁 {n_c} 本を壁の内面まで（いちばん大きいずれ {worst:.0f} mm）')

# 3) 梁・2 階の床梁の端：外壁の内面で止める（角の丸みで梁の端が外に出ていた）
# 10-25（ソリッド係の依頼）：柱・梁・桁（22a〜d）は押し出しのまま、輪郭の制御点を動かす（extedit.py）。前は網目にしてから
# 頂点を動かしていて、Rhino 版でその所が細い平らな片の集まりになっていた。押し出しでないものだけ前と同じく網目で。
from shapely.geometry import LineString
import extedit
beam_new = []; beam_drop = set()
EXT = dict(EXT_COL)                                    # 物の Id → 動かした押し出し（22a〜d、本館の柱 11a）
def cur_g(o): return EXT.get(str(o.Attributes.Id), o.Geometry)
_n_end = 0
# 10-28（監修の項 20261028-1310 の 2）：2 枚組の梁（22b・22c）は一つの梁なので、2 枚とも同じ所で止める（角の丸みでは、内側の 1 枚の
# 止まる所（外壁の内面）に 2 枚をそろえる。前は 1 枚ずつ止めたので、u21 の床梁の西の端が −10.24 と −11.01 で違っていた）
from uv import uv as _uvf
def _vmin_after(o):
    """1 枚ずつ外壁の内面で止めたとき（前の止め方：外の輪郭の点を軸に沿って中ほどへ、内面まで）の西の端の v。止めなくてよい梁は None"""
    g0 = o.Geometry; P = tris(g0).reshape(-1, 3)
    if all(WN.buffer(-2).contains(Point(x, y)) for x, y in P[:, :2]): return None
    c = P[:, :2].mean(0); X = P[:, :2] - c; w, vec = np.linalg.eigh(X.T @ X); ax = vec[:, -1]
    Q = extedit._pts(extedit.profiles3d(g0)[0]) if isinstance(g0, r.Extrusion) else P
    vs = []
    for x, y in Q[:, :2]:
        if _uvf(x, y)[1] > -3.0: continue                                   # 西の端だけ（東の端は越屋根の下、そのまま）
        pt = Point(x, y)
        if WNi.contains(pt): vs.append(_uvf(x, y)[1]); continue
        s_ = np.dot(np.array([x, y]) - c, ax); dirn = -np.sign(s_) * ax
        hit = LineString([(x, y), (x + dirn[0] * 3000, y + dirn[1] * 3000)]).intersection(WNi.exterior)
        pts = [hit] if hit.geom_type == 'Point' else list(getattr(hit, 'geoms', []))
        if pts: q = min(pts, key=lambda p: p.distance(pt)); vs.append(_uvf(q.x, q.y)[1])
    return min(vs) if vs else None
_bm = []
for o in m.Objects:
    if o.Attributes.LayerIndex not in (L22B, L22C): continue
    P = tris(o.Geometry).reshape(-1, 3)
    if not len(P): continue
    U_ = to_uv_arr(P)
    if np.ptp(U_[:, 1]) < 3.0: continue
    _bm.append((o, float(U_[:, 0].mean()), float(U_[:, 1].min())))
_vcut = {}
for o, uc_, vmin_ in _bm:
    va = _vmin_after(o)
    if va is None: continue
    for o2, uc2, vmin2 in _bm:
        if o2.Attributes.LayerIndex == o.Attributes.LayerIndex and abs(uc2 - uc_) < 0.4:
            k2 = str(o2.Attributes.Id); _vcut[k2] = max(_vcut.get(k2, -99.0), va + 0.002)
for o, uc_, vmin_ in _bm:
    k_ = str(o.Attributes.Id)
    if k_ not in _vcut or vmin_ >= _vcut[k_] - 1e-4: continue
    vt_ = _vcut[k_]
    g0 = o.Geometry
    P = tris(g0).reshape(-1, 3)
    c = P[:, :2].mean(0); X = P[:, :2] - c; w, vec = np.linalg.eigh(X.T @ X); ax = vec[:, -1]
    def _trim(V, k=0):
        V = V.copy(); vk_ = vt_ + (0.03 if k else 0.0)                       # 穴は外の輪郭の 30 内（重ならないように）
        if k:                                                                 # 穴（丸い設備の穴）は形のまま中ほどへずらす
            vv_ = np.array([_uvf(x, y)[1] for x, y in V[:, :2]])
            if vv_.min() >= vk_: return V
            s_ = np.dot(V[:, :2].mean(0) - c, ax); dirn = -np.sign(s_) * ax
            d_ = (vk_ - vv_.min()) * 1000.0 / max(1e-6, abs(np.dot(dirn, (np.array(xy(uc_, -5.0)) - np.array(xy(uc_, -6.0))) / 1000.0)))
            V[:, :2] += dirn * d_; return V
        ARC = LineString([xy(uu_, vk_) for uu_ in np.arange(uc_ - 1.0, uc_ + 1.0001, 0.05)])
        for i, (x, y, z) in enumerate(V):
            if _uvf(x, y)[1] >= vk_: continue
            s_ = np.dot(np.array([x, y]) - c, ax); dirn = -np.sign(s_) * ax          # 中ほどへ向かって
            hit = LineString([(x, y), (x + dirn[0] * 3000, y + dirn[1] * 3000)]).intersection(ARC)
            pts = [hit] if hit.geom_type == 'Point' else list(getattr(hit, 'geoms', []))
            if pts:
                q = min(pts, key=lambda p: p.distance(Point(x, y))); V[i, 0], V[i, 1] = q.x, q.y
        return V
    e = extedit.edit(g0, _trim) if isinstance(g0, r.Extrusion) else None
    if e is not None: EXT[k_] = e
    else:
        log.append(f'  !! 梁の端を押し出しのまま止められなかった（u{uc_:.2f}）')
        mm = closed_mesh(g0); V = _trim(mesh_V(mm)); mesh_set(mm, V); mm.Normals.ComputeNormals(); mm.Compact()
        beam_new.append((mm, o.Attributes)); beam_drop.add(k_)
    _n_end += 1
log.append(f'西館：梁 {_n_end} 本の端を外壁の内面で止めた（押し出しのまま {sum(1 for k in EXT)} 本）')
# 3b) 屋根の面に合わせる（10-24午後、西館係）：南西・北の角で屋根の面を作り直した（roofw.py）。
# 南の端の架構・角の柱と桁の上の方（屋根の 0.9 下まで）を、前の面との差だけ上げる（下は動かさない）。
# 10-25：スパン8〜14（u21〜42）は屋根がスパンごとの平面になった（roofw.py）ので、その架構も同じく上の方を合わせる（±約3 cm）。
# 柱・梁は輪郭（架構の線の縦の面）の制御点を、桁（道が u の向きに長い）は道の両端の高さを動かす。
import roofw
_RWf = roofw.make(WN)
_bn = {str(at.Id): i for i, (mm, at) in enumerate(beam_new)}
_n_lift = 0; _dmax = 0.0
def _dz(x, y, z):
    zo = _RWf['roof_old'](x, y)
    if z < zo - 900.0: return 0.0
    d_ = _RWf['roof_f'](x, y) - zo
    return d_ if abs(d_) > 2 else 0.0
for o in m.Objects:
    if o.Attributes.LayerIndex not in (L22A, L22B, L22D): continue
    k_ = str(o.Attributes.Id)
    g = cur_g(o)
    if o.Attributes.LayerIndex == L22B and isinstance(g, r.Extrusion) and k_ not in _bn: continue   # 10-28：屋根の梁は 3e で屋根の面から作り直す
    if isinstance(g, r.Extrusion) and k_ not in _bn:
        S_ = extedit.samples(g, 40); U = to_uv_arr(S_)
        if not ((U[:, 0] < 42.2).any() or (U[:, 0] > 49.9).any()): continue
        _ch = [0.0]
        if o.Attributes.LayerIndex == L22D:
            zt = S_[:, 2].max()
            def _path(A, B):
                for E_ in (A, B):
                    d_ = _dz(E_[0], E_[1], zt); E_[2] += d_; _ch[0] = max(_ch[0], abs(d_))
                return A, B
            e = extedit.edit(g, None, _path)
        else:
            def _lift(V, k=0):
                for i, (x, y, z) in enumerate(V):
                    d_ = _dz(x, y, z); V[i, 2] = z + d_; _ch[0] = max(_ch[0], abs(d_))
                return V
            e = extedit.edit(g, _lift)
        if e is None or _ch[0] == 0.0: continue
        EXT[k_] = e; _n_lift += 1; _dmax = max(_dmax, _ch[0]); continue
    if k_ in _bn: mm = beam_new[_bn[k_]][0]
    else:
        if not len(tris(g)): continue
        mm = closed_mesh(g)
    V = mesh_V(mm); U = to_uv_arr(V)
    if not ((U[:, 0] < 42.2).any() or (U[:, 0] > 49.9).any()): continue      # 10-25：スパン8〜14 の平面の屋根にも合わせる
    ch = False
    for i, (x, y, z) in enumerate(V):
        d_ = _dz(x, y, z)
        if d_: V[i, 2] = z + d_; ch = True; _dmax = max(_dmax, abs(d_))
    if not ch: continue
    mesh_set(mm, V); mm.Normals.ComputeNormals(); mm.Compact(); _n_lift += 1
    if k_ not in _bn: beam_new.append((mm, o.Attributes)); beam_drop.add(k_)
log.append(f'西館：南西・北の角とスパン8〜14の平面の屋根に合わせて、柱・梁・桁 {_n_lift} 本の上の方を合わせた（いちばん大きい差 {_dmax:.0f} mm）')

# 3c) 面だけの西館の物に厚みを付けて閉じる（10-24夜、西館係）：階段の箱の壁・2階の北の壁（24）、階段（25）、室内窓（27）は
# 面だけで描かれていて閉じておらず、干渉の一覧にも削る段にも入らなかった。三角形ごとに両側へ厚みの半分ずつ出した三角柱を
# 足し合わせて一つの閉じた立体にする（開口はそのまま残る）。厚さ：間仕切り120、階段の踏み板・蹴込み40、ガラス12。
import manifold3d as _mf
_THK = {lidx('24_'): 120.0, lidx('25_'): 40.0, lidx('27_'): 12.0}
# 階段の下の倉庫（10-25、ユーザー・監修）：上の段（西の半分）と踊り場の下。床 u30.06〜32.94・v−3.45〜−4.94、戸は箱の西の面に遊戯室へ
# 階段を細く（10-25、ユーザー・監修：遊戯室の南の口のあきを約1.1 → 約1.7）：西の面 v−5.0 はそのまま、東の面 v−2.2 → −2.75。
# 階段の箱・階段・階段の床の v を一次で縮める（一本の幅 約1.2 → 約0.96）。
ST_V0, ST_V1, ST_V1N = -5.0, -2.2, -2.99   # 10-25昼（ユーザー）：一本 0.9 に詰める（前は −2.75 で一本 約1.02）
def stair_v(v): return ST_V0 + (v - ST_V0) * (ST_V1N - ST_V0) / (ST_V1 - ST_V0) if ST_V0 - 0.1 <= v <= ST_V1 + 0.1 else v
# 階段（25）は箱の内面いっぱいに（ユーザー 10-25：階段と西の壁のあいだにすき間。元から西に0.45空いていた）：
# 階段の幅 v−4.55〜−2.25 を、箱の壁（厚さ120、芯 −5.0・−2.75）の内面 −4.94〜−2.81 に合わせる（一本 約1.03）。
STAIR_IN = (-4.55, -2.25, -4.94, -3.05)   # 一本 0.9・あいだ 0.09
def stair_v25(v):
    a, b, a2, b2 = STAIR_IN
    return a2 + (v - a) * (b2 - a2) / (b - a) if a - 0.1 <= v <= b + 0.1 else v
def stair_narrow(T, f=None, su=False):
    f = f or stair_v
    P = T.reshape(-1, 3).copy(); Q = to_uv_arr(P)
    for i, (u_, v_) in enumerate(Q):
        x_, y_ = xy(stair_u(u_) if su else u_, f(v_)); P[i, 0], P[i, 1] = float(np.ravel(x_)[0]) if np.ndim(x_) else x_, float(np.ravel(y_)[0]) if np.ndim(y_) else y_
    return P.reshape(T.shape)
_n_stair = 0
# 階段を北へ 0.9 延ばす（10-27、ユーザー：スパン11を本館の先生の道へ開け、南の口の通路から入る。はれのまを削らない素直な形）：
# 箱は u30〜33.9。南の端 u30〜30.9 が 1 階の登り口（東の面から入る）と 2 階の着き口、東の一折れは u30.9 から北へ、踊り場は u33〜33.9。
STAIR_U0, STAIR_FOOT, STAIR_U1 = 30.0, 0.9, 33.9
def stair_u(u): return STAIR_U0 + (u - STAIR_U0) * (STAIR_U1 - STAIR_U0) / 3.0 if STAIR_U0 - 0.1 <= u <= 33.1 else u   # 箱の壁・床を北へ伸ばす
STAIR_STG = (30.06, STAIR_U1 - 0.06, -4.94, round(stair_v25(-3.45), 3)); STAIR_DOOR = (30.30, 31.50)
STAIR_DOOR_H = 2100.0   # 10-28（監修の項 20261028-0015 の 15）：戸の高さ 1750 → 2100（ほかの室内の戸と同じ。上の段の裏 u31.6 で約 z2.67 なので納まる）

def _plates(T, thk, stair=False):
    """面だけの物（三角形 T）→ 平らな面ごとの板（閉じた立体、manifold3d）の組。板はそれぞれ押し出し（Rhino 版で押し出しになる）。
    前は三角形ごとの三角柱を足し合わせた一つの立体で、階段・階段の箱が面の多い一つのポリサーフェスになっていた（10-25 ユーザー：
    階段の壁などは明らかに押し出しで良い → 元の構成を改良。ソリッド係）。
    - 壁（間仕切り・ガラス）：面の両側に厚みの半分ずつ。面と面が角で出会う所は、面積の大きいほうの板を厚みの半分だけ延ばし、
      小さいほうを同じだけ縮める（突き付け、重ならず、角も欠けない）。
    - 階段：踏み板は上の面から下へ、蹴込み板は面から奥へ厚み thk。蹴込み板は上の踏み板の下で止め、下は下の踏み板の下の面まで
      （下の踏み板の小口に突き付け）。下の踏み板・踊り場が蹴込みの奥まで続く所では、その上に載せる。"""
    T = np.asarray(T, float)
    N = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); ar = np.linalg.norm(N, axis=1)
    ok = ar > 1.0; T = T[ok]; N = N[ok] / ar[ok, None]
    # 同じ平面の三角形の組（向きは問わない）
    groups = []
    for i in range(len(T)):
        n = N[i]; d = n @ T[i, 0]
        for g in groups:
            if abs(abs(g['n'] @ n) - 1) < 1e-4 and abs(g['n'] @ T[i, 0] - g['d']) < 0.5: g['ids'].append(i); break
        else: groups.append(dict(n=n.copy(), d=d, ids=[i]))
    if stair:                                    # 階段：同じ平面でも、辺を共有する三角形の組ごとに（踊り場の蹴込みと上の段の蹴込みを分ける）
        g2 = []
        for g in groups:
            key = lambda p: tuple(np.round(p, 1)); par = {i: i for i in g['ids']}
            def fd(x):
                while par[x] != x: par[x] = par[par[x]]; x = par[x]
                return x
            ed = {}
            for i in g['ids']:
                for a_, b_ in ((0, 1), (1, 2), (2, 0)):
                    k_ = tuple(sorted((key(T[i, a_]), key(T[i, b_]))))
                    if k_ in ed: par[fd(i)] = fd(ed[k_])
                    else: ed[k_] = i
            cc = {}
            for i in g['ids']: cc.setdefault(fd(i), []).append(i)
            g2 += [dict(g, ids=v) for v in cc.values()]
        groups = g2
    plates = []
    for g in groups:
        n = g['n']; a = np.array([0, 0, 1.]) if abs(n[2]) < 0.9 else np.array([1., 0, 0])
        X = np.cross(a, n); X /= np.linalg.norm(X); Y = np.cross(n, X); o = T[g['ids'][0], 0]
        to2 = lambda P, o=o, X=X, Y=Y: [((p - o) @ X, (p - o) @ Y) for p in P]
        if stair: poly = unary_union([Polygon(to2(T[i])) for i in g['ids']]).buffer(0)     # 角で触れるだけの板（踊り場の上下の蹴込み）をつながない
        else: poly = unary_union([Polygon(to2(T[i])).buffer(0.01, join_style=2) for i in g['ids']]).buffer(-0.01, join_style=2)
        if poly.is_empty: continue
        plates.append(dict(n=n, o=o, X=X, Y=Y, poly=poly, area=poly.area))
    if stair:                                    # 階段：同じ平面にのる離れた板（二つの段の蹴込み）は別々に
        plates = [dict(pl, poly=pg, area=pg.area) for pl in plates for pg in getattr(pl['poly'], 'geoms', [pl['poly']]) if pg.area > 1.0]
    def to3(pl, q): return pl['o'] + q[0] * pl['X'] + q[1] * pl['Y']
    def strip(pl, a2, b2, out, w):
        """板 pl の面で、辺 a2→b2 から外へ（out）幅 w の帯"""
        a2, b2 = np.array(a2), np.array(b2); e = b2 - a2; e /= np.linalg.norm(e); nn = np.array([-e[1], e[0]])
        if nn @ out < 0: nn = -nn
        return Polygon([a2, b2, b2 + nn * w, a2 + nn * w])
    h = thk / 2
    if not stair:
        # 角の突き付け：二つの板の境の辺
        for i, A in enumerate(plates):
            for j, B in enumerate(plates):
                if j <= i or abs(A['n'] @ B['n']) > 0.9: continue
                for P_, Q_ in ((A, B), (B, A)):
                    ring = [c_ for pg_ in getattr(P_['poly'], 'geoms', [P_['poly']]) for c_ in list(pg_.exterior.coords) + [None]]
                    for k in range(len(ring) - 1):
                        if ring[k] is None or ring[k + 1] is None: continue
                        p3 = [to3(P_, ring[k]), to3(P_, ring[k + 1])]
                        if max(abs((x - Q_['o']) @ Q_['n']) for x in p3) > 1.0: continue
                        q2 = to2_ = [((x - Q_['o']) @ Q_['X'], (x - Q_['o']) @ Q_['Y']) for x in p3]
                        if Q_['poly'].boundary.distance(Point(q2[0])) > 1.0 or Q_['poly'].boundary.distance(Point(q2[1])) > 1.0: continue
                        a2, b2 = np.array(ring[k]), np.array(ring[k + 1])
                        if np.linalg.norm(b2 - a2) < 1.0: continue
                        mid = (a2 + b2) / 2; e = (b2 - a2) / np.linalg.norm(b2 - a2); nn = np.array([-e[1], e[0]])
                        out = nn if not P_['poly'].contains(Point(mid + nn * 0.5)) else -nn
                        if P_['area'] >= Q_['area']: P_['poly'] = P_['poly'].union(strip(P_, a2, b2, out, h)).buffer(0)
                        else: P_['poly'] = P_['poly'].difference(strip(P_, a2, b2, -out, h)).buffer(0)
        offs = {id(pl): (-h, h) for pl in plates}
    else:
        offs = {}
        flat = [pl for pl in plates if abs(pl['n'][2]) > 0.9]; vert = [pl for pl in plates if abs(pl['n'][2]) <= 0.9]
        for pl in flat:
            if pl['n'][2] < 0: pl['n'] = -pl['n']                           # 上向き。板は面から下へ
            offs[id(pl)] = (-thk, 0.0)
        for pl in vert:
            # 外向き（下の踏み板の側）：面の下の縁の少し前に踏み板があるほう
            P3 = [to3(pl, q) for q in pl['poly'].convex_hull.exterior.coords]; zlo = min(p[2] for p in P3); zhi = max(p[2] for p in P3)
            c = np.mean(P3, axis=0); c[2] = zlo
            def on_flat(p, z):
                for f in flat:
                    if abs(f['o'][2] - z) < 1.0 and f['poly'].buffer(0.5).contains(Point((p - f['o']) @ f['X'], (p - f['o']) @ f['Y'])): return True
                return False
            n = pl['n'] if on_flat(c + pl['n'] * 20, zlo) or not on_flat(c - pl['n'] * 20, zlo) else -pl['n']
            if not on_flat(c + n * 20, zlo) and on_flat(c - n * 20, zlo): n = -n
            pl['n'] = n; pl['X'] = -pl['X'] if np.cross(pl['X'], pl['Y']) @ n < 0 else pl['X']
            if np.cross(pl['X'], pl['Y']) @ n < 0: pl['Y'] = -pl['Y']
            pl['poly'] = Polygon([((p - pl['o']) @ pl['X'], (p - pl['o']) @ pl['Y']) for p in P3]).buffer(0)
            ztop = zhi - thk                                                 # 上の踏み板の下で止める
            zbot = zlo if on_flat(c - n * (thk / 2), zlo) or zlo < 1.0 else zlo - thk   # 奥にも踏み板があれば載せる、なければ小口に突き付け
            zy = lambda z: ((np.array([0, 0, z]) - pl['o']) @ pl['Y'])
            yb, yt = sorted((zy(zbot), zy(ztop)))
            xs = [q[0] for q in pl['poly'].exterior.coords]
            pl['poly'] = Polygon([(min(xs), yb), (max(xs), yb), (max(xs), yt), (min(xs), yt)])
            offs[id(pl)] = (-thk, 0.0)                                       # 面から奥へ
    out = []
    for pl in plates:
        lo, hi = offs[id(pl)]
        for pg in getattr(pl['poly'], 'geoms', [pl['poly']]):
            if pg.geom_type != 'Polygon' or pg.area < 1.0: continue
            tm = trimesh.creation.extrude_polygon(pg, hi - lo)
            L = np.asarray(tm.vertices)
            Wv = pl['o'] + np.outer(L[:, 0], pl['X']) + np.outer(L[:, 1], pl['Y']) + np.outer(L[:, 2] + lo, pl['n'])
            F = np.asarray(tm.faces)
            if np.cross(pl['X'], pl['Y']) @ pl['n'] < 0: F = F[:, ::-1]
            M = _mf.Manifold(_mf.Mesh(vert_properties=Wv.astype(np.float32), tri_verts=F.astype(np.uint32)))
            if M.is_empty(): M = _mf.Manifold(_mf.Mesh(vert_properties=Wv.astype(np.float32), tri_verts=F[:, ::-1].astype(np.uint32).copy()))
            if not M.is_empty(): out.append(M)
    return out

def _stair_tris():
    """西館の階段（25）を描き直す（10-25夜、ソリッド係の指摘：踏み板が一段おきに無い）。
    元の面は一折れ 9 段の蹴上げ（1F 0 → 踊り場 1625 → 2F 3250、1 段 180.6）に踏み板が 5 枚（踏面 0.375）しか無く、
    蹴上げが 181・361 の交互になっていた。一折れ 9 段・踏み板 8 枚・踏面 0.2625（2R+G＝0.62）、踊り場の奥行き 0.9（＝階段の幅）。
    東の一折れ（v−3.35〜−2.25）は u30.9 から北へ上り、踊り場（u33〜33.9）、西の一折れ（v−4.55〜−3.45）は南へ上って u30.9 で 2 階の床（10-27、箱を北へ0.9）。
    v は元の描き方の座標（このあと stair_narrow が箱の内面の幅へ縮める）。"""
    RS, G = 3250.0 / 18, 0.2625
    U0, UL = STAIR_U0 + STAIR_FOOT, STAIR_U0 + STAIR_FOOT + 8 * G       # 10-27：登り口（u30〜30.9）の北から上る、踊り場は u33〜33.9
    quads = []
    def tread(u0, u1, v0, v1, z): quads.append([(u0, v0, z), (u1, v0, z), (u1, v1, z), (u0, v1, z)])
    def riser(u, v0, v1, z0, z1): quads.append([(u, v0, z0), (u, v1, z0), (u, v1, z1), (u, v0, z1)])
    E0, E1, W0, W1 = -3.35, -2.25, -4.55, -3.45
    for k in range(1, 9):                                   # 東の一折れ
        riser(U0 + (k - 1) * G, E0, E1, (k - 1) * RS, k * RS); tread(U0 + (k - 1) * G, U0 + k * G, E0, E1, k * RS)
    riser(UL, E0, E1, 8 * RS, 9 * RS)
    tread(UL, STAIR_U1, W0, E1, 9 * RS)                     # 踊り場
    tread(STAIR_U0, U0, W0, E1, 18 * RS)                    # 2 階の着き口（箱の南の端の上、登り口と倉庫の上）
    for k in range(1, 9):                                   # 西の一折れ
        riser(UL - (k - 1) * G, W0, W1, 9 * RS + (k - 1) * RS, 9 * RS + k * RS); tread(UL - k * G, UL - (k - 1) * G, W0, W1, 9 * RS + k * RS)
    riser(U0, W0, W1, 17 * RS, 18 * RS)
    T_ = []
    for q in quads:
        P = [np.r_[np.ravel(xy(u, v)).astype(float), z] for u, v, z in q]
        T_ += [[P[0], P[1], P[2]], [P[0], P[2], P[3]]]
    return np.array(T_)

import mapbox_earcut as _ec0
from shapely.geometry.polygon import orient as _orient0
def _elev_vf(el, p0, d, n, t):
    """立面の形 el（(s, z)、穴あり可）を、壁の線 p0 + s·d の両側へ t/2 ずつ（法線 n）押し出した閉じた立体の (V, F)。面はみな平ら"""
    Vs, Fs, off = [], [], 0
    for pg in getattr(el, 'geoms', [el]):
        if pg.geom_type != 'Polygon' or pg.area < 100: continue
        pg = _orient0(pg, 1.0)
        rings = [np.asarray(pg.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in pg.interiors]
        V2 = np.vstack(rings); k = len(V2); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        c2 = V2.mean(0); tri = _ec0.triangulate_float64(V2 - c2, ends).reshape(-1, 3)
        P3 = lambda sg: np.c_[p0[0] + V2[:, 0] * d[0] + sg * n[0] * t / 2, p0[1] + V2[:, 0] * d[1] + sg * n[1] * t / 2, V2[:, 1]]
        V = np.vstack([P3(-1), P3(1)]); F = [tri[:, [0, 2, 1]], tri + k]; st = 0
        for e in ends:
            i = np.arange(st, e); j = np.r_[i[1:], st]; F += [np.c_[i, j, j + k], np.c_[i, j + k, i + k]]; st = e
        F = np.vstack(F)
        if trimesh.Trimesh(V - V.mean(0), F, process=False).volume < 0: F = F[:, ::-1]
        Vs.append(V); Fs.append(F + off); off += len(V)
    return (np.vstack(Vs), np.vstack(Fs)) if Vs else (None, None)
def _wall_from_elev(el, p0, d, n, t, attr):
    V, F = _elev_vf(el, p0, d, n, t)
    if V is None: return
    mm = r.Mesh()
    for x_, y_, z_ in V: mm.Vertices.Add(float(x_), float(y_), float(z_))
    for a_, b_, c_ in F: mm.Faces.AddFace(int(a_), int(b_), int(c_))
    mm.Normals.ComputeNormals(); beam_new.append((mm, attr))
_BOX_ATTR = None
_n_thk = 0
for o in m.Objects:
    li_ = o.Attributes.LayerIndex
    if li_ not in _THK or not isinstance(o.Geometry, r.Mesh): continue
    T = tris(o.Geometry)
    if not len(T): continue
    U = to_uv_arr(T.reshape(-1, 3))
    if (U[:, 1] > -0.9).any(): continue                                  # 西館だけ
    if li_ in (lidx('24_'), lidx('25_')) and U[:, 0].min() > 29.9 and U[:, 0].max() < 33.1 and U[:, 1].min() > -5.05 and U[:, 1].max() < -2.15:
        if li_ == lidx('25_'): T = _stair_tris(); _log_stair = True   # 段を描き直す（元は一折れ 9 段の蹴上げに踏み板が 5 枚しか無かった）
        T = stair_narrow(T, stair_v25 if li_ == lidx('25_') else None, su=(li_ == lidx('24_'))); U = to_uv_arr(T.reshape(-1, 3)); _n_stair += 1   # 階段と階段の箱を細く（10-25）
    tm_ = trimesh.Trimesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3)); tm_.merge_vertices(digits_vertex=1)
    if tm_.is_watertight: continue
    if trimesh.Trimesh(T.reshape(-1, 3), np.arange(len(T) * 3).reshape(-1, 3)).is_watertight: continue   # 10-28：もう閉じた立体（add_west_south.py の壁ごとの立体）は触らない（0.1 mm に丸めて溶かすと閉じなくなる）
    if li_ == lidx('24_') and (U[:, 1] < -4.9).any() and (U[:, 1] > -3.1).any() and T[:, :, 2].max() > 7000:
        # 10-28（監修の項 20261028-0843）：階段の箱は面ごとの板でなく、壁ごとの「輪郭の押し出し − 開口」の一つの立体に。上端は屋根の下面の
        # 下の平らな面（屋根ができた後、書き出しの前の「階段の箱の壁」で作る）
        _BOX_ATTR = o.Attributes; beam_drop.add(str(o.Attributes.Id)); _n_thk += 1; continue
    if li_ == lidx('24_') and abs(U[:, 0].mean() - 33.0) < 0.2 and np.ptp(U[:, 0]) < 0.3 and T[:, :, 2].min() > 3100:
        # 10-28（同）：2 階の北の壁（u33、会議室｜遊戯室）。面の三角形を壁の面（放射の線）に写した立面の形（開口を除く）を厚さ 120 で押し出す
        _p0 = np.ravel(xy(33.0, -5.0)); _d = np.ravel(xy(33.0, -6.0)) - _p0; _d /= np.linalg.norm(_d); _nn = np.array([-_d[1], _d[0]])
        _P = T.reshape(-1, 3); _S = (_P[:, :2] - _p0) @ _d
        _el = unary_union([Polygon(np.c_[_S[3 * k:3 * k + 3], _P[3 * k:3 * k + 3, 2]]).buffer(0.5, join_style=2) for k in range(len(T))
                           if Polygon(np.c_[_S[3 * k:3 * k + 3], _P[3 * k:3 * k + 3, 2]]).area > 1]).buffer(-0.5, join_style=2).simplify(1.0)
        _wall_from_elev(_el, _p0, _d, _nn, 120.0, o.Attributes); beam_drop.add(str(o.Attributes.Id)); _n_thk += 1; continue
    ms_ = _plates(T, _THK[li_], stair=(li_ == lidx('25_')))         # 面ごとの板（押し出し）に（10-25 ソリッド係、ユーザー）
    if not ms_: continue
    if li_ == lidx('24_') and (U[:, 1] < -4.9).any() and (U[:, 1] > -3.1).any() and T[:, :, 2].max() > 7000:   # 階段の箱：西の面に階段の下の倉庫の戸（10-25）
        _tb = trimesh.creation.extrude_polygon(R(*STAIR_DOOR, -5.3, -4.7, 0.05), STAIR_DOOR_H)
        _box = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(_tb.vertices, np.float32), tri_verts=np.asarray(_tb.faces, np.uint32)))
        ms_ = [M_ - _box for M_ in ms_]
        # 階段の箱の南の面（u30）の登り口と2階の降り口（10-27、ユーザー：登り口が壁でほぼ塞がっている）。元の面は u30 の面が床から
        # 箱の天まで一枚で、東の一折れの登り口（1階）も西の一折れの降り口（2階）も開いていなかった
        # 10-27：箱を北へ延ばし、1 階の登り口は東の面（南の口の通路の側、u30〜30.9）、2 階の着き口は南の面いっぱい
        for _ob, _z0, _z1 in ((R(STAIR_U0 + 0.06, STAIR_U0 + STAIR_FOOT, -2.7, -3.25, 0.05), -10.0, 3170.0),
                              (R(29.7, 30.3, -3.1, -4.94, 0.05), 3170.0, 3250.0 + 2100.0)):
            _tb = trimesh.creation.extrude_polygon(_ob, _z1 - _z0); _tb.apply_translation([0, 0, _z0])
            _cut = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(_tb.vertices, np.float32), tri_verts=np.asarray(_tb.faces, np.uint32)))
            ms_ = [M_ - _cut for M_ in ms_]
    # 板は別々の立体のまま（触れるだけ、重ならない）。頂点も板ごとに別にして、Rhino 版で板ごとの押し出しになるように
    mm = r.Mesh()
    for M_ in ms_:
        if M_.is_empty(): continue
        g_ = M_.to_mesh(); o_ = len(mm.Vertices)
        for x_, y_, z_ in np.asarray(g_.vert_properties)[:, :3]: mm.Vertices.Add(float(x_), float(y_), float(z_))
        for a_, b_, c_ in np.asarray(g_.tri_verts): mm.Faces.AddFace(int(a_) + o_, int(b_) + o_, int(c_) + o_)
    mm.Normals.ComputeNormals()
    at_ = o.Attributes
    if li_ == lidx('27_') and U[:, 0].min() > 32.9 and U[:, 0].max() < 33.1:
        # 10-28（ユーザー、監修の項 20261028-0015 の 9）：会議室から遊戯室を見る室内窓（腰 850、下は遊戯室へ約 4.1 m）ははめ殺し。柵は付けない（見えは変えない）
        at_.Name = '室内窓（2階の会議室から遊戯室を見る、はめ殺し、腰 850、10-28 監修の項 0015 の 9）'; _log_win27 = True
    beam_new.append((mm, at_)); beam_drop.add(str(o.Attributes.Id)); _n_thk += 1
log.append(f'西館：面だけの間仕切り・階段・室内窓 {_n_thk} 個に厚みを付けて閉じた')
if globals().get('_log_win27'): log.append('西館：会議室から遊戯室を見る室内窓（u33）をはめ殺しに（名前、監修の項 0015 の 9）')
log.append(f'西館：階段と階段の箱 {_n_stair} 個を細くした（東の面 v−2.2 → −2.99、一本 0.9、南の口のあき 柱の所 約1.30・柱のあいだ 約1.88）')

# 3d) 外壁ぎわの柱の外の面を、足もとから頭まで外壁の内面にそろえる（10-25、ユーザーの問い・監修）。
# 柱（22a）は縦の断面が先細り（頭が桁を抱いて膨らむ）で、頭だけが壁の内面に届き、足もとでは壁から約0.14離れて
# 遊戯室に下が広いV字のすき間ができていた（腕や頭が挟まる）。高さごとにいちばん外の点（外の面）だけを壁の内面まで出す
# （内の面の先細りの形はそのまま）。本館の柱（外の面が平ら、壁の内面に接する）と同じ納まり。
_bn2 = {str(at.Id): i for i, (mm, at) in enumerate(beam_new)}
_n_col = 0; _gmax = 0.0; _log_cols = []
from scipy.spatial import ConvexHull as _CH
def _envelope(P2, zs_):
    """(sp, z) の点の凸包の、高さごとのいちばん外（sp が大きい側）"""
    H = _CH(P2); env = []
    for z_ in zs_:
        xs_ = []
        for e_ in H.simplices:
            (s0, z0_), (s1, z1_) = P2[e_[0]], P2[e_[1]]
            if min(z0_, z1_) - 1e-6 <= z_ <= max(z0_, z1_) + 1e-6:
                xs_.append(s0 if abs(z1_ - z0_) < 1e-6 else s0 + (s1 - s0) * (z_ - z0_) / (z1_ - z0_))
        env.append(max(xs_) if xs_ else -1e9)
    return np.array(env)
for o in m.Objects:
    if o.Attributes.LayerIndex != L22A: continue
    k_ = str(o.Attributes.Id)
    g = cur_g(o)
    as_ext = isinstance(g, r.Extrusion) and k_ not in _bn2
    if as_ext:
        S_ = extedit.samples(g, 200)
    else:
        mm = beam_new[_bn2[k_]][0] if k_ in _bn2 else closed_mesh(g); S_ = mesh_V(mm)
    c = S_[:, :2].mean(0)
    q = nearest_points(WNi.exterior, Point(*c))[0]; d = np.array([q.x, q.y]) - c; t = np.linalg.norm(d)
    if t < 1 or t > 600: continue
    n = d / t
    P2 = np.c_[(S_[:, :2] - c) @ n, S_[:, 2]]
    try: zs_ = np.linspace(P2[:, 1].min(), P2[:, 1].max(), 200); env = _envelope(P2, zs_)
    except Exception: continue
    gap = float(t - env[1:-1].min())                                  # 足もとのすき間など、いちばん広い所
    _log_cols.append((round(float(to_uv_arr(S_[:1])[0][0]), 2), round(float(to_uv_arr(S_[:1])[0][1]), 2), round(gap)))
    if gap < 5.0 or gap > 350.0: continue                            # 壁から離れて立つ柱（角など）は動かさない（10-25：東の面の u24〜33 の柱 約0.28 も入れる、遊戯室の南の口の柱）
    def _face(V, k=0):
        if k != 0: return V                                           # 穴の輪郭はそのまま
        sp = (V[:, :2] - c) @ n
        on_ = sp >= np.interp(V[:, 2], zs_, env) - 2.0               # 外の縁の上（とその外）の制御点
        V[on_, :2] += np.outer(t - 2.0 - sp[on_], n)
        return V
    if as_ext:
        # 押し出しの輪郭は架構の線の縦の面にあり、道（厚さ 180）はそれに直交する。壁へ向かう向き n を
        # 輪郭の面の中の向き mh と道の向き p に分ける：面の中なら輪郭の外の縁の制御点を mh の向きに、
        # 道の向き（南北の妻の壁）なら道の壁の側の端を伸ばす（柱の側面は平らなので全部の高さで同じだけ）。
        a_, b_ = g.PathStart, g.PathEnd
        p = np.array([b_.X - a_.X, b_.Y - a_.Y]); p = p / max(1e-9, np.linalg.norm(p))
        np_ = float(n @ p)
        if abs(np_) > 0.7:
            mv = (t - 2.0 - env[1:-1].max()) / abs(np_)                  # 壁の側の小口を壁の内面の 2 手前まで
            def _path(A, B):
                if np_ > 0: B[:2] += p * mv
                else: A[:2] -= p * mv
                return A, B
            e = extedit.edit(g, None, _path)
        else:
            mh = n - np_ * p; mh = mh / np.linalg.norm(mh); cs = float(mh @ n)
            TOL_F = 40.0
            S0 = extedit.samples(g, 200, ends=(0.0,))                    # 輪郭の面（道の始まり）の上だけで外の縁を取る
            P20 = np.c_[(S0[:, :2] - c) @ n, S0[:, 2]]; env0 = _envelope(P20, zs_)
            L_ = np.hypot(b_.X - a_.X, b_.Y - a_.Y); off = max(0.0, np_ * L_)   # 道の終わりの面のほうが壁に近ければ、その分だけ手前で止める
            zhead_ = float(S0[:, 2].max()) - 600.0                         # 10-29（項 20261028-2355 の H）：頭の曲線（桁を抱くふくらみ）の制御点は動かさない
            def _face_in(V, k=0):
                if k != 0: return V
                sp = (V[:, :2] - c) @ n
                on_ = (sp >= np.interp(V[:, 2], zs_, env0) - TOL_F) & (V[:, 2] < zhead_)   # 外の縁の近くの制御点（曲線のふくらみがすき間を残さないよう少し広く）
                V[on_, :2] += np.outer((t - 2.0 - off - sp[on_]) / cs, mh)
                return V
            e = extedit.edit(g, _face_in)
        if e is None: continue
        EXT[k_] = e
    else:
        V = _face(mesh_V(mm)); mesh_set(mm, V); mm.Normals.ComputeNormals(); mm.Compact()
        if k_ not in _bn2: beam_new.append((mm, o.Attributes)); beam_drop.add(k_)
    _n_col += 1; _gmax = max(_gmax, gap)
log.append(f'西館：外壁ぎわの柱 {_n_col} 本の外の面を足もとから頭まで壁の内面にそろえた（いちばん大きいすき間 {_gmax:.0f} mm）')

# 3e) 構造の直し（10-27、ユーザー・監修の略算、プロジェクトの「構造_西館_略算」「構造_西館_見直し_10-27昼」、項 20261027-0932-kanshu）
# 1. 屋根の梁（22b）：2 枚組のせい 700 → 800（強い集成材 E105-F300 相当）。上端（＝屋根の下面）はそのまま、下へ深くする
#    （輪郭の点を、梁の上端の線からの深さで 800/700 倍。西の端のハンチもそれに比例）。
#    10-28（ユーザー、監修の項 20261028-1310 の 1）：梁の上端＝屋根の面 roof_f（その 1 枚の上の面。光の筋をはさむ 2 枚は別のスパンの面なので
#    棟の端で ±約5 cm 違う）。もとの梁（3dm）は上端が前の面 roof_old の 150 下にあり、3b は面の差（roof_f − roof_old）だけ上げていたので、
#    梁は屋根の面の 150 下のままだった。また 3b は前の面の 900 下までの点だけを上げたので、角（u21・u48）では西の端の上の方だけが
#    動いて 2 枚の形が違っていた。今は、もとの梁の輪郭の点の上端の線からの深さ（2 枚で同じ）を 800/700 倍して、その 1 枚の上の roof_f から
#    下へ取る（3b では屋根の梁を動かさない）。せい・ハンチ・西の端・下端の線（上端からのせい）は 2 枚で同じ。
# 2. 東の桁（22d、z 約7.3〜7.7）は梁の東の端の穴を通っていた（梁の下端が約半分欠かれていた）→ 梁の下端より下へ下げ、梁の穴をふさぐ。
#    柱の頭つなぎ・水平構面の弦材として柱に留める（金物）。
# 3. 2 階の床梁を受ける骨格の柱：架構 u24・u27 の、1 階のキッチンの東の壁の線（v −3.4）に 180×400（22a、床梁の 2 枚のあいだ、FL〜2 階の床の下）。
#    キッチンの東の面の配膳口・返却口・受け取り台は柱を避けて割り直した（add_west_south.py）。
# 4. 東の高窓の帯（z 4.89〜6.09）：東の柱は帯で継がずに通す（3dm でも通っている）。帯の上下の縁に横材（まぐさ・窓台、120×180、
#    柱と柱のあいだ、外壁の内面の内側）。柱と壁の面材を帯の上下で一体に留める。
# 5. 階段の箱（u30〜33.9）を骨格の耐力壁に：南の面が u30 の床梁を全幅で、東西の面が u33 の床梁を受ける。箱の角・開口の両脇・
#    床梁の下に柱 120×120（壁の厚みの中、22a）、倉庫の戸の上にまぐさ（22d）。箱の壁の下に基礎の立ち上がり（3dm には描かない）。
_XNEW = []                                             # 新しい押し出し（書き出しで out.Objects.Add）
def _xbox(u0_, u1_, v0_, v1_, z0_, z1_, li_, name_):
    """u・v の四角（放射の線と弧の弦）を z0〜z1 に立てた押し出し（Rhino 版で押し出しのまま）"""
    P_ = [xy(u0_, v0_), xy(u1_, v0_), xy(u1_, v1_), xy(u0_, v1_)]
    a2_ = sum((P_[i][0] * P_[(i + 1) % 4][1] - P_[(i + 1) % 4][0] * P_[i][1]) for i in range(4))
    if a2_ < 0: P_ = P_[::-1]                                                     # 反時計回り（上向きに押し出す）
    pl_ = r.Polyline([r.Point3d(float(x_), float(y_), float(z0_)) for x_, y_ in P_ + [P_[0]]])
    e_ = r.Extrusion.Create(pl_.ToNurbsCurve(), float(z1_ - z0_), True)
    at_ = r.ObjectAttributes(); at_.LayerIndex = li_; at_.Name = name_
    _XNEW.append((e_, at_)); return e_
# 1・2) 梁を深く、東の穴をふさぐ
BEAM_K = 800.0 / 700.0
def _deepen(g, off2=None, g_orig=None):
    pl = g.GetProfilePlane(0.0)
    O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z])
    X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
    S_ = extedit.outer_samples(g, 1200)
    hd = np.array([X[0], X[1]]) if abs(X[2]) < 0.5 else np.array([Y[0], Y[1]]); hd = hd / np.linalg.norm(hd)
    s_ = (S_[:, :2] - O[:2]) @ hd
    bins = np.linspace(s_.min(), s_.max(), 41); mx = []
    for a_, b_ in zip(bins, bins[1:]):
        k_ = (s_ >= a_) & (s_ < b_)
        if k_.any(): i_ = np.argmax(np.where(k_, S_[:, 2], -1e18)); mx.append((s_[i_], S_[i_, 2]))   # 区間のいちばん高い点（の位置）
    mx = np.array(mx); mid = mx[int(len(mx) * 0.1):int(len(mx) * 0.9)]
    cf = np.polyfit(mid[:, 0], mid[:, 1], 1)                                       # 梁の上端の線 z = a s + b
    ztop = lambda s: cf[0] * s + cf[1]
    a, b = g.PathStart, g.PathEnd
    hm = np.array([b.X - a.X, b.Y - a.Y]) / 2.0                                     # 厚みの真ん中で屋根の面を取る
    curves2d = []; n_hole = 0
    for k_, nc in enumerate(extedit.profiles3d(g)):
        W = extedit._weights(nc); P = extedit._pts(nc)
        sp = (P[:, :2] - O[:2]) @ hd; zt = ztop(sp)
        zr_ = np.array([_RWf['roof_f'](*(q_ + hm)) for q_ in P[:, :2]])               # その 1 枚の上の屋根の面（梁の上端、厚みの真ん中）
        if k_ == 0:
            dep = zt - P[:, 2]
            # 10-30（梁18）：3) で端を外壁の内面まで縮めた点は、高さをそのままに中ほどへ動いたので、上端の線からの深さを動かす前の点で測る
            #   （北の端の架構 u50.565 は角の丸みで西の端が 0.4 縮み、上端が屋根の面から最大 13 cm 下がっていた）
            if g_orig is not None:
                P0_ = extedit._pts(extedit.profiles3d(g_orig)[0])
                if P0_.shape == P.shape:
                    mv_ = np.linalg.norm(P0_[:, :2] - P[:, :2], axis=1) > 1.0
                    if mv_.any(): dep = np.where(mv_, ztop((P0_[:, :2] - O[:2]) @ hd) - P0_[:, 2], dep)
            if off2 is not None:                                                    # 10-29：北西の角の 2 枚は、上端はそれぞれの面、下の方はもう 1 枚と同じ（低いほうの面から）
                zr2_ = np.array([_RWf['roof_f'](*(q_ + hm + off2)) for q_ in P[:, :2]]); w_ = np.clip(dep / 300.0, 0.0, 1.0)
                zr_ = zr_ * (1 - w_) + np.minimum(zr_, zr2_) * w_
            P[:, 2] = zr_ - np.where(dep > 0, dep * BEAM_K, dep)
        else:
            vh = np.mean([uv(x_, y_)[1] for x_, y_ in P[:, :2]])
            if vh > -2.0: n_hole += 1; continue                                    # 東の桁の穴（桁を下げたので要らない）
            P[:, 2] += float(np.mean(zr_ - zt))                                    # ほかの穴は上端からの深さのまま
        Q = np.c_[(P - O) @ X, (P - O) @ Y, np.zeros(len(P))]
        extedit._set_pts(nc, Q, W); curves2d.append(nc)
    e = r.Extrusion()
    if not e.SetPathAndUp(a, b, pl.YAxis): return None, 0
    if not e.SetOuterProfile(curves2d[0], True): return None, 0
    for c2 in curves2d[1:]:
        if not e.AddInnerProfile(c2): return None, 0
    return e, n_hole
_n_deep = 0; _n_hole = 0; _BEAM_BOT_E = {}; _BEAM_MID_E = {}               # 架構の u → 東の桁の線（v −1.30）での梁の下端（2 枚のうち低いほう）
_deep = []; _g0 = {}; _go = {}
for o in m.Objects:
    if o.Attributes.LayerIndex != L22B: continue
    k_ = str(o.Attributes.Id); g = cur_g(o)
    if not isinstance(g, r.Extrusion) or k_ in _bn2: continue
    e, nh = _deepen(g, None, o.Geometry)
    if e is None: continue
    EXT[k_] = e; _n_deep += 1; _n_hole += nh; _deep.append(k_); _g0[k_] = g; _go[k_] = o.Geometry
# 10-29（監修の項 20261028-2355 の E）：一つの架構の 2 枚の板は同じ形に。2 枚の上の屋根の面の差が 15 以下の架構（u21〜42）は、上の低いほうの
# 1 枚を厚みの向きに平行に写す（前は 1 枚ずつ自分の上の面から作って、下端・穴が 6〜9 違った）。北西の角（u45・48）は 2 枚の上の面が最大 8〜11 cm
# 違うので、それぞれ自分の上の面のまま（2 枚組の梁は 2 枚とも屋根の面に、ユーザー 10-28）、下の方（上端から 300 より下）は 2 枚で同じ（低いほうの面から。
# 前は下端が 76〜101 違い、桁が板の縁にかかった）。
def _pmid(e_):
    a_, b_ = e_.PathStart, e_.PathEnd; return np.array([(a_.X + b_.X) / 2, (a_.Y + b_.Y) / 2, (a_.Z + b_.Z) / 2]), np.array([b_.X - a_.X, b_.Y - a_.Y, b_.Z - a_.Z])
_by_f = {}
for k_ in _deep:
    c_, pv_ = _pmid(EXT[k_]); u_ = uv(c_[0], c_[1])[0]
    kk_ = next((q for q in _by_f if abs(q - u_) < 0.4), u_); _by_f.setdefault(kk_, []).append(k_)
_n_copy = 0; _ply_keep = []
for kk_, ks_ in _by_f.items():
    if len(ks_) != 2: continue
    e1_, e2_ = EXT[ks_[0]], EXT[ks_[1]]
    z1_ = extedit.outer_samples(e1_, 1500)[:, 2]; z2_ = extedit.outer_samples(e2_, 1500)[:, 2]
    S1_ = extedit.outer_samples(e1_, 600); c1_, pv_ = _pmid(e1_); c2_, _ = _pmid(e2_)
    dv_ = []
    for x_, y_, z_ in S1_[::6]:
        q_ = np.array([x_, y_]) + (c2_[:2] - c1_[:2]); dv_.append(abs(_RWf['roof_f'](x_, y_) - _RWf['roof_f'](*q_)))
    if max(dv_) > 15.0:
        _ply_keep.append(round(float(uv(c1_[0], c1_[1])[0]), 2))
        for ka_, kb_ in ((ks_[0], ks_[1]), (ks_[1], ks_[0])):
            ca_, _ = _pmid(EXT[ka_]); cb_, _ = _pmid(EXT[kb_]); e_ = _deepen(_g0[ka_], (cb_ - ca_)[:2], _go[ka_])[0]
            if e_ is not None: EXT[ka_] = e_
        continue
    mst, oth = (ks_[0], ks_[1]) if z1_.max() <= z2_.max() else (ks_[1], ks_[0])
    cm_, pn_ = _pmid(EXT[mst]); co_, _ = _pmid(EXT[oth]); pn_ = pn_ / np.linalg.norm(pn_)
    dup_ = EXT[mst].Duplicate(); t_ = float((co_ - cm_) @ pn_) * pn_
    dup_.Translate(r.Vector3d(float(t_[0]), float(t_[1]), float(t_[2]))); EXT[oth] = dup_; _n_copy += 1
log.append(f'西館：2 枚組の梁 {_n_copy} 組を 1 枚から写して同じ形に（上の面の差が 15 を超える架構 u{_ply_keep} はそれぞれのまま）')
for k_ in _deep:
    e = EXT[k_]
    S_ = extedit.outer_samples(e, 2000); U_ = to_uv_arr(S_)
    near_ = np.abs(U_[:, 1] + 1.30) < 0.03
    if near_.any():
        uk = round(float(np.median(U_[:, 0])) / 3.0) * 3.0 if U_[:, 0].mean() > 22 else 21.3
        _BEAM_BOT_E[uk] = min(_BEAM_BOT_E.get(uk, 1e9), float(S_[near_, 2].min()))
        nc_ = e.Profile3d(0, 0.0).ToNurbsCurve(); dm_ = nc_.Domain                    # 東の桁の線（v −1.30）での梁のせいの真ん中（頭の芯）：節ごとに細かく取った輪郭で
        kn_ = sorted(set([dm_.T0, dm_.T1] + [float(nc_.Knots[i]) for i in range(len(nc_.Knots)) if dm_.T0 < nc_.Knots[i] < dm_.T1]))
        Pk_ = np.array([[q.X, q.Y, q.Z] for q in (nc_.PointAt(t) for t in np.unique(np.concatenate([np.linspace(a_, b_, 25) for a_, b_ in zip(kn_, kn_[1:])])))])
        hm_ = np.array([e.PathEnd.X - e.PathStart.X, e.PathEnd.Y - e.PathStart.Y]) / 2.0
        Vk_ = np.array([uv(*(q_[:2] + hm_))[1] for q_ in Pk_])
        xk_ = Polygon(np.c_[Vk_ * 1000.0, Pk_[:, 2]]).buffer(0).intersection(LineString([(-1300.0, 0.0), (-1300.0, 20000.0)]))
        if not xk_.is_empty: _BEAM_MID_E.setdefault(uk, []).append((xk_.bounds[1] + xk_.bounds[3]) / 2.0)
log.append(f'西館：屋根の梁 {_n_deep} 枚のせいを 700 → 800 に（上端はそのまま、下へ）。東の端の桁の穴 {_n_hole} をふさいだ')
# 10-29 午後（ユーザー：Tamedia に倣った梁の頭の穴に桁を通す）：東の桁（楕円 200×400）は、梁（2 枚組の板）の東の端の丸い頭の芯を通す。
# 芯＝東の桁の線（v −1.30）での梁のせいの真ん中（2 枚の平均）。穴は 3f の 3 で通る桁の断面＋10（全周で同じすき間）、桁は柱の面で止まる
# （柱には穴を作らない、西の桁と同じ）。前（10-27）は桁を梁の下端の 10 下へ下げて穴をふさいでいた。棟は水平なので芯の高さは架構ごとにほぼ同じ。
_MID_E = {k_: float(np.mean(v_)) for k_, v_ in _BEAM_MID_E.items()}
_mid_sp = (max(_MID_E.values()) - min(_MID_E.values())) if _MID_E else 0.0
log.append(f'西館：東の桁を梁の頭の芯へ：芯の高さ {min(_MID_E.values()):.0f}〜{max(_MID_E.values()):.0f}（架構ごとの差 {_mid_sp:.0f} mm）' if _MID_E else '  !! 梁の頭の芯が測れない')
_n_g = 0; _gz = []
for o in m.Objects:
    if o.Attributes.LayerIndex != L22D: continue
    k_ = str(o.Attributes.Id); g = cur_g(o)
    if not isinstance(g, r.Extrusion): continue
    S_ = extedit.samples(g, 40); U_ = to_uv_arr(S_)
    if not (U_[:, 1].mean() > -1.6 and S_[:, 2].min() > 6500): continue              # 東の桁（屋根の高さ）だけ
    def _mid_at(uu):
        ks = sorted(_MID_E, key=lambda q: abs(q - uu))
        return _MID_E[ks[0]] if ks and abs(ks[0] - uu) < 0.6 else None
    a_, b_ = g.PathStart, g.PathEnd
    ua, ub = uv(a_.X, a_.Y)[0], uv(b_.X, b_.Y)[0]
    za_, zb_ = _mid_at(ua), _mid_at(ub)
    if za_ is None or zb_ is None: continue
    S0 = extedit.samples(g, 60, ends=(0.0,)); S1 = extedit.samples(g, 60, ends=(1.0,))
    dza, dzb = za_ - (S0[:, 2].max() + S0[:, 2].min()) / 2.0, zb_ - (S1[:, 2].max() + S1[:, 2].min()) / 2.0
    def _path(A, B, dza=dza, dzb=dzb):
        A[2] += dza; B[2] += dzb; return A, B
    e = extedit.edit(g, None, _path)
    if e is None: continue
    EXT[k_] = e; _n_g += 1; _gz.append(min(dza, dzb))
log.append(f'西館：東の桁 {_n_g} 本を梁の頭の芯へ（動かした量 約{np.mean(_gz) if _gz else 0:+.0f} mm）')
# 10-28（ユーザー、監修の項 20261028-1310 の 3）：東の柱（v −1.05〜−1.8）と西の柱（外壁ぎわ）の頭を、その架構の梁の上端にそろえる
# （梁の上端＝その 1 枚の上の roof_f。2 枚の上端が違う所は低いほう）。柱は 2 枚の梁のあいだ（u ±0.09）にあり、輪郭は架構の線の縦の面。
# 頭の形（桁を抱くふくらみ）はそのまま、頭の上の線からの深さ 300 までの制御点を同じだけ上下し、300〜600 でなだらかに 0 へ（押し出しのまま）。
_n_head = 0; _USE_TOPS = False
_PLY_TOP = {}; _PLY_U = {}                                                          # 梁の板ごとの上端の線（v → z）
for k_ in _deep:
    S_ = extedit.outer_samples(EXT[k_], 4000); U_ = to_uv_arr(S_)
    bins_ = np.round(U_[:, 1] / 0.01).astype(int); vb_, zb_ = [], []
    for b_ in np.unique(bins_):
        vb_.append(b_ * 0.01); zb_.append(S_[bins_ == b_, 2].max())
    _PLY_TOP[k_] = (np.array(vb_), np.array(zb_)); _PLY_U[k_] = float(np.median(U_[:, 0]))
for o in m.Objects:
    if o.Attributes.LayerIndex != L22A: continue
    k_ = str(o.Attributes.Id); g = cur_g(o)
    if not isinstance(g, r.Extrusion) or k_ in _bn2: continue
    S_ = extedit.outer_samples(g, 800); U_ = to_uv_arr(S_)
    vm_ = float(U_[:, 1].mean())
    if S_[:, 2].max() < 4000 or not (-2.0 < vm_ < -0.9 or U_[:, 1].min() < -9.0): continue
    if abs(np.ptp(S_[:, 2])) < 3000: continue                                       # 床からの柱だけ
    a_, b_ = g.PathStart, g.PathEnd
    uc_ = float(np.mean([uv(a_.X, a_.Y)[0], uv(b_.X, b_.Y)[0]]))
    pl = g.GetProfilePlane(0.0); O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z])
    X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
    hd = np.array([X[0], X[1]]) if abs(X[2]) < 0.5 else np.array([Y[0], Y[1]]); hd = hd / np.linalg.norm(hd)
    s_ = (S_[:, :2] - O[:2]) @ hd; zmx_ = float(S_[:, 2].max())
    def _tl(sp):                                                                    # その位置の頭の上の線（輪郭のいちばん高い所）
        out_ = []
        for q in sp:
            kk = np.abs(s_ - q) < 15.0
            out_.append(S_[kk, 2].max() if kk.any() else S_[np.argmin(np.abs(s_ - q)), 2])
        return np.array(out_)
    _tops = [_PLY_TOP[kp_] for kp_ in _PLY_TOP if abs(_PLY_U[kp_] - uc_) < 0.4]
    def _zt(x_, y_):
        v_ = uv(x_, y_)[1]
        z_ = min(_RWf['roof_f'](*np.ravel(xy(uc_ - 0.132, v_))), _RWf['roof_f'](*np.ravel(xy(uc_ + 0.132, v_))))   # 2 枚の梁の上端（厚みの真ん中）の低いほう
        if _USE_TOPS:
            for vb_, zb_ in _tops:                                                  # 10-29（項 20261028-2355 の I）：梁の東の端の丸みでは梁の上端の線（低いほう）
                if vb_[0] - 0.005 <= v_ <= vb_[-1] + 0.005: z_ = min(z_, float(np.interp(v_, vb_, zb_)))
        return z_
    def _head(V, k=0):
        sp = (V[:, :2] - O[:2]) @ hd; tl = _tl(sp)
        for i, (x_, y_, z_) in enumerate(V):
            dep = tl[i] - z_
            if tl[i] < zmx_ - 600.0: continue                                       # 頭の上の線の無い位置（足もとの広がり）
            w = 1.0 if dep < 300.0 else max(0.0, 1.0 - (dep - 300.0) / 300.0)
            if w <= 0: continue
            d_ = _zt(x_, y_) - tl[i]; V[i, 2] = z_ + w * d_
        return V
    e = extedit.edit(g, _head)
    if e is None: log.append(f'  !! 柱の頭を押し出しのまま直せなかった（u{uc_:.2f}）'); continue
    EXT[k_] = e; _n_head += 1
log.append(f'西館：東西の柱 {_n_head} 本の頭を梁の上端（roof_f、2 枚のうち低いほう）にそろえた')
# 3) 2 階の床梁を受ける柱
for uc in (24.0, 27.0):
    _xbox(uc - 0.0885, uc + 0.0885, -3.20, -3.60, 0.0, 3170.0, L22A,     # 10-29：u の 0.09 は v−3.4 で 91.5、床梁の板の内面（±90）の内に
          f'骨格の柱 180×400（架構 u{uc:.0f}、2 階の床梁を受ける、キッチンの東の壁の線）')
# 4) 東の高窓の帯の上下の横材
_ecol = []
for o in m.Objects:
    if o.Attributes.LayerIndex != L22A: continue
    S_ = extedit.samples(cur_g(o), 20) if isinstance(cur_g(o), r.Extrusion) else tris(o.Geometry).reshape(-1, 3)
    U_ = to_uv_arr(S_)
    if U_[:, 1].max() > -0.9 or U_[:, 1].mean() < -2.0 or S_[:, 2].max() < 6500: continue
    _ecol.append((U_[:, 0].min(), U_[:, 0].max()))
_ecol.sort()
BAND_Z0, BAND_Z1 = 4894.0, 6094.0
# 10-29 夕（監修の項 1530）：北の端（u48 の柱の北）の窓台・まぐさは、帯の北の端の北の妻の壁の内面に突き当てて、壁に載せる（受ける柱が無い）
_u_nw = 50.75
for uq_ in np.arange(49.0, 52.0, 0.001):
    if not WNi.contains(Point(*np.ravel(xy(uq_, -1.112)))): _u_nw = float(uq_) + 0.002; break      # 壁の内面（_xbox が 0.002 手前で止める）
_segs = [(a_[1], b_[0]) for a_, b_ in zip(_ecol, _ecol[1:])] + [(_ecol[-1][1], _u_nw)] if _ecol else []
for u0_, u1_ in _segs:
    if u1_ - u0_ < 0.3: continue
    _xbox(u0_ + 0.002, u1_ - 0.002, -1.052, -1.172, BAND_Z0 - 180.0, BAND_Z0, L22D, '東の高窓の帯の窓台（120×180、柱と柱のあいだ）')
    _xbox(u0_ + 0.002, u1_ - 0.002, -1.052, -1.172, BAND_Z1, BAND_Z1 + 180.0, L22D, '東の高窓の帯のまぐさ（120×180、柱と柱のあいだ）')
log.append(f'西館：骨格の柱 2 本（u24・u27、v −3.4、180×400）、東の高窓の帯の窓台・まぐさ {2 * len(_segs)} 本')
# 5) 階段の箱の柱とまぐさ（壁の芯 v −2.99・−5.0、u30・33（床梁の下）・33.9、開口の両脇）
_BOXC = [(30.0, -2.99), (30.0, -5.0), (30.96, -2.99), (30.24, -5.0), (31.56, -5.0), (33.0, -2.99), (33.0, -5.0), (33.9, -2.99), (33.9, -5.0)]
for uc, vc in _BOXC:
    _xbox(uc - 0.06, uc + 0.06, vc - 0.06, vc + 0.06, 0.0, 3170.0, L22A, f'階段の箱の柱 120×120（骨格の耐力壁、u{uc:.2f}）')
_xbox(STAIR_DOOR[0] + 0.001, STAIR_DOOR[1] - 0.001, -4.94, -5.06,     # 10-29：柱（u30.24・31.56）のあいだに（前は柱に 60 ずつ食い込んだ）
       STAIR_DOOR_H, STAIR_DOOR_H + 180.0, L22D, '階段の箱の倉庫の戸のまぐさ（120×180）')
log.append(f'西館：階段の箱を骨格の耐力壁に（柱 {len(_BOXC)} 本 120×120、倉庫の戸のまぐさ、u30・u33 の床梁を受ける）')
# 6) 階段の上の頭のあき（10-28、監修の項 20261028-0015 の 1）：u33 の 2 階の床梁（2 枚組 u32.82〜33.18、下端 z2400）が
#    階段（1 本目の上の段・踊り場・2 本目の下の段）の上を横切り、踊り場の上のあきが 0.78 m だった。梁を階段の箱の東西の壁の内面
#    （v−3.05・−4.94）のあいだで切り、東の片・西の片に分ける。梁の端は箱の壁と、その下の柱（u33、v−2.99・−5.0）が受ける（3e の 5）。
#    押し出しのまま：輪郭の制御点のうち切る側にあるものを切り口の線（u 一定の放射の線の上で v＝切り口）へ寄せ、z を梁の上下端
#    （2400〜3200）に収める。寄せた点は同じ点・同じ線に重なるので、切り口は縦の平らな面になる。穴（端の桁の穴）は残る片のほうに。
#    u30.13 の梁は 2 階の着き口（u30〜30.9）の下で、下は 1 階の登り口・倉庫（あき 2.4 m）なので切らない。
STAIR_CUT_V = (-4.94, -3.05)
def _cut_beam(g, keep_east):
    vc = STAIR_CUT_V[1] if keep_east else STAIR_CUT_V[0]
    zb_ = min(p[2] for p in extedit.samples(g, 400) if STAIR_CUT_V[0] < uv(p[0], p[1])[1] < STAIR_CUT_V[1])
    zt_ = max(p[2] for p in extedit.samples(g, 400) if STAIR_CUT_V[0] < uv(p[0], p[1])[1] < STAIR_CUT_V[1])
    pl = g.GetProfilePlane(0.0)
    O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z])
    X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
    curves2d = []
    for k_, nc in enumerate(extedit.profiles3d(g)):
        W = extedit._weights(nc); P = extedit._pts(nc)
        V_ = np.array([uv(x_, y_) for x_, y_ in P[:, :2]])
        if k_ > 0:                                                    # 穴：残る片の側のものだけ
            if (V_[:, 1].mean() > vc) != keep_east: continue
        else:
            cut = V_[:, 1] < vc if keep_east else V_[:, 1] > vc
            for i in np.where(cut)[0]:
                x_, y_ = xy(V_[i, 0], vc); P[i, 0], P[i, 1] = float(np.ravel(x_)[0]) if np.ndim(x_) else x_, float(np.ravel(y_)[0]) if np.ndim(y_) else y_
                P[i, 2] = min(max(P[i, 2], zb_), zt_)
        Q = np.c_[(P - O) @ X, (P - O) @ Y, np.zeros(len(P))]
        extedit._set_pts(nc, Q, W); curves2d.append(nc)
    e = r.Extrusion()
    if not e.SetPathAndUp(g.PathStart, g.PathEnd, pl.YAxis): return None
    if not e.SetOuterProfile(curves2d[0], True): return None
    for c2 in curves2d[1:]:
        if not e.AddInnerProfile(c2): return None
    return e
_n_cut = 0
for o in list(m.Objects):
    if o.Attributes.LayerIndex != L22C: continue
    k_ = str(o.Attributes.Id); g = cur_g(o)
    if not isinstance(g, r.Extrusion) or k_ in beam_drop: continue
    ua_, ub_ = uv(g.PathStart.X, g.PathStart.Y)[0], uv(g.PathEnd.X, g.PathEnd.Y)[0]
    if not (32.7 < min(ua_, ub_) and max(ua_, ub_) < 33.3): continue
    eE, eW = _cut_beam(g, True), _cut_beam(g, False)
    if eE is None or eW is None: continue
    EXT[k_] = eE
    at_ = r.ObjectAttributes(); at_.LayerIndex = o.Attributes.LayerIndex
    at_.Name = (o.Attributes.Name or '2 階の床梁') + '（階段の上で切った西の片、10-28）'
    _XNEW.append((eW, at_)); _n_cut += 1
log.append(f'西館：u33 の 2 階の床梁 {_n_cut} 枚を階段の上（v{STAIR_CUT_V[0]}〜{STAIR_CUT_V[1]}、箱の東西の壁の内面のあいだ）で切った（端は箱の壁と柱が受ける）')

# 3f) 架構の仕上げ（10-29、西館係。監修の項 20261028-2355、renkei/files/20261028-kanshu-west-frame）：上の段で別々に動かした柱・梁・桁を
#     最後にそろえる。押し出しのまま。
#   1. 架構の柱は 2 枚の板（梁・2 階の床梁）のあいだに（厚みの向きの位置と幅を板の内面に合わせる。D：板に重なっていた）。そのあと外壁に入った分は
#      架構の面の中で内へ。
#   2. 桁の端（架構の芯で終わる）は柱の面で止め、柱のあいだに架ける（C・F：下げた東の桁が柱の細い所を貫いていた、外の板に空の穴）。
#   3. 柱・梁・2 階の床梁（22a〜c）の穴を全部消し、通る桁（22d の丸い桁）の、その材の厚みの中での断面（5 枚の面で切った和）＋10 で作り直す
#      （A・B・C・G：穴と桁が 90〜560 ずれていた・桁が柱の木を貫いていた・空の穴）。
def _v3(p_): return np.array([p_.X, p_.Y, p_.Z])
def _path(g): return _v3(g.PathStart), _v3(g.PathEnd)
def _umed(g): return float(np.median(to_uv_arr(extedit.samples(g, 12))[:, 0]))
_WOOD = []
for o in m.Objects:
    if o.Attributes.LayerIndex in (L22A, L22B, L22C) and str(o.Attributes.Id) not in beam_drop:
        g = cur_g(o)
        if isinstance(g, r.Extrusion): _WOOD.append(['m', str(o.Attributes.Id), o.Attributes.LayerIndex, o.Attributes.Name or '', g])
for i_, (g, at_) in enumerate(_XNEW):
    if at_.LayerIndex in (L22A, L22B, L22C) and isinstance(g, r.Extrusion): _WOOD.append(['x', i_, at_.LayerIndex, at_.Name or '', g])
_WOOD = [w for w in _WOOD if np.median(to_uv_arr(extedit.samples(w[4], 12))[:, 1]) < -0.35]
for w in _WOOD: w.append(_umed(w[4]))
def _wset(w, e):
    w[4] = e
    if w[0] == 'm': EXT[w[1]] = e
    else: _XNEW[w[1]] = (e, _XNEW[w[1]][1])
# 1. 柱
_n_reset = 0; _n_push = 0
for w in _WOOD:
    if w[2] != L22A or w[3]: continue                                       # 架構の柱（名前の無いもの）
    g = w[4]; A, B = _path(g); L_ = np.linalg.norm(B - A)
    if abs(B[2] - A[2]) > 1.0 or not (100.0 < L_ < 400.0): continue
    pd_ = (B - A) / L_
    rng = []
    for x in _WOOD:
        if x[2] not in (L22B, L22C) or abs(x[5] - w[5]) > 0.4 or '出し梁' in x[3] or '登り梁' in x[3]: continue
        Ax, Bx = _path(x[4]); rng.append(sorted(((Ax - A) @ pd_, (Bx - A) @ pd_)))
    neg = [q for q in rng if (q[0] + q[1]) / 2 < L_ / 2]; pos = [q for q in rng if (q[0] + q[1]) / 2 >= L_ / 2]
    if not neg or not pos: continue
    t0_, t1_ = max(q[1] for q in neg), min(q[0] for q in pos)
    if t1_ - t0_ < 100.0 or (abs(t0_) < 0.5 and abs(t1_ - L_) < 0.5): continue
    e = extedit.edit(g, None, lambda A_, B_: (A + pd_ * t0_, A + pd_ * t1_))
    if e is None: continue
    _wset(w, e); _n_reset += 1
    hd_c = np.array([-pd_[1], pd_[0]]); hd_c /= np.linalg.norm(hd_c)
    for _ in range(6):
        f = Polygon(extedit.samples(w[4], 60)[:, :2]).convex_hull
        if f.difference(WNi).area < 50: break
        pts = [Point(p_) for p_ in np.array(f.exterior.coords) if not WNi.contains(Point(p_))]
        far = max(pts, key=lambda p_: WNi.exterior.distance(p_)); near = nearest_points(WNi.exterior, far)[0]
        d = np.array([near.x - far.x, near.y - far.y]); Ld = np.linalg.norm(d)
        if Ld < 0.5: break
        c_ = float(hd_c @ (d / Ld))
        if abs(c_) < 0.2: break
        mv = np.r_[hd_c * np.sign(c_) * (Ld + 3.0) / abs(c_), 0.0]
        e = extedit.edit(w[4], None, lambda A_, B_: (A_ + mv, B_ + mv))
        if e is None: break
        _wset(w, e); _n_push += 1
log.append(f'西館：架構の柱 {_n_reset} 本を 2 枚の板のあいだ（厚みの向き）にそろえ、外壁に入った {_n_push} 回を架構の面の中で内へ')
# 2. 桁の端（架構の芯で終わる）を柱の面で止める（柱のあいだに架ける。C：下げた桁が柱の細い所を貫いていた、F：端の架構の外の板に空の穴）
_GIR = []
for o in m.Objects:
    if o.Attributes.LayerIndex != L22D: continue
    g = cur_g(o)
    if not isinstance(g, r.Extrusion) or g.ProfileCount < 1: continue
    if g.Profile3d(0, 0.0).ToNurbsCurve().Degree < 2: continue                 # 丸い桁だけ（窓台・まぐさは箱）
    if np.median(to_uv_arr(extedit.samples(g, 12))[:, 1]) > -0.35: continue
    _GIR.append([str(o.Attributes.Id), g])
def _outer2d(g, n=400):
    A, B = _path(g); pl = g.GetProfilePlane(0.0); X = _v3(pl.XAxis); Y = _v3(pl.YAxis)
    c = g.Profile3d(0, 0.0); P = np.array([[q.X, q.Y, q.Z] for q in (c.PointAt(t) for t in np.linspace(c.Domain.T0, c.Domain.T1, n))])
    return Polygon(np.c_[(P - A) @ X, (P - A) @ Y]).buffer(0), A, B, X, Y
# 10-31（ユーザー 21:26、監修の項 2131：Tamedia の留め）：桁の端は柱の面で止めず、柱の頭の穴を通す。架構の線で終わる端は、
#   向こうに続きの桁があれば柱の頭の中心（桁の軸が柱を通る区間の真ん中）、無ければ（端の架構）軸が通る板・柱のいちばん外の面まで。
#   軸＝桁の輪郭の重心の線。板・柱（穴を除いた外形）に軸を当てて入る・出る所を測る
def _ext_tm(g):
    T_ = tri.tri_extrusion(g)
    tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(); tm_.fix_normals(); return tm_
def _tm_mf(tm_):
    try:
        M_ = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(tm_.vertices, np.float32), tri_verts=np.asarray(tm_.faces, np.uint32)))
        return None if M_.is_empty() else M_
    except Exception: return None
def _outer_only(g):
    """押し出しの外形だけ（穴を除く）の押し出し"""
    e_ = r.Extrusion()
    if not e_.SetPathAndUp(g.PathStart, g.PathEnd, g.GetProfilePlane(0.0).YAxis): return None
    A_, B_ = _path(g); pl_ = g.GetProfilePlane(0.0); X_ = _v3(pl_.XAxis); Y_ = _v3(pl_.YAxis)
    nc_ = g.Profile3d(0, 0.0).ToNurbsCurve(); W_ = extedit._weights(nc_); P_ = extedit._pts(nc_)
    extedit._set_pts(nc_, np.c_[(P_ - A_) @ X_, (P_ - A_) @ Y_, np.zeros(len(P_))], W_)
    return e_ if e_.SetOuterProfile(nc_, True) else None
def _frame_of(g):
    A, B = _path(g); pl = g.GetProfilePlane(0.0); X = _v3(pl.XAxis); Y = _v3(pl.YAxis)
    iv = 0 if abs(X[2]) > abs(Y[2]) else 1; ih = 1 - iv
    sz = 1.0 if (X if iv == 0 else Y)[2] > 0 else -1.0
    hw = (X if ih == 0 else Y)[:2].copy(); hw /= np.linalg.norm(hw)
    return dict(A=A, B=B, X=X, Y=Y, iv=iv, ih=ih, sz=sz, hw=hw, hm=(B[:2] - A[:2]) / 2.0)
def _l2sz(F, q):                                                              # 輪郭の面の座標 → (s, z)
    q = np.atleast_2d(q); return np.c_[q[:, F['ih']], F['A'][2] + F['sz'] * q[:, F['iv']]]
def _sz2l(F, q):
    q = np.atleast_2d(q); out_ = np.zeros_like(q); out_[:, F['ih']] = q[:, 0]; out_[:, F['iv']] = (q[:, 1] - F['A'][2]) * F['sz']; return out_
def _w2s(F, P):                                                               # 世界の点 → s（輪郭の面への投影）
    P = np.atleast_2d(P); return (P[:, :2] - F['A'][:2]) @ F['hw']
def _s_of_v(F, v_, s0=0.0):                                                   # その材の面の上で v＝v_ の s
    vs = lambda s: uv(*(F['A'][:2] + F['hw'] * s + F['hm']))[1]
    s = s0
    for _ in range(6):
        d_ = (vs(s + 100.0) - vs(s)) / 100.0
        if abs(d_) < 1e-9: break
        s = s + (v_ - vs(s)) / d_
    return s
def _dv(F):                                                                  # s が増える向きに v が増えるなら +1
    return 1.0 if uv(*(F['A'][:2] + F['hw'] * 1000.0))[1] > uv(*F['A'][:2])[1] else -1.0
def _ring_pts(g, k, n=24):
    """輪郭の点：折れ線は頂点、曲線は節（ノット）のあいだごとに n 等分（全体を等分すると、短い節の曲線（梁の端の丸み）に点が 2〜3 しか無い）"""
    c = g.Profile3d(k, 0.0); nc = c.ToNurbsCurve()
    if nc.Degree == 1: return extedit._pts(nc)
    dm = c.Domain; kn = sorted(set([dm.T0, dm.T1] + [float(nc.Knots[i]) for i in range(len(nc.Knots)) if dm.T0 < nc.Knots[i] < dm.T1]))
    ts = np.unique(np.concatenate([np.linspace(a_, b_, n + 1) for a_, b_ in zip(kn, kn[1:])]))
    return np.array([[q.X, q.Y, q.Z] for q in (nc.PointAt(t) for t in ts)])
def _poly_sz(g, F=None, k=0):
    F = F or _frame_of(g); P = _ring_pts(g, k)
    return Polygon(_l2sz(F, np.c_[(P - F['A']) @ F['X'], (P - F['A']) @ F['Y']])).buffer(0)
TAMEDIA = True
def _gaxis(g):
    A_, B_ = _path(g); pl_ = g.GetProfilePlane(0.0); X_ = _v3(pl_.XAxis); Y_ = _v3(pl_.YAxis)
    c_ = g.Profile3d(0, 0.0); P_ = np.array([[q.X, q.Y, q.Z] for q in (c_.PointAt(t) for t in np.linspace(c_.Domain.T0, c_.Domain.T1, 200))])
    cx_ = np.array(Polygon(np.c_[(P_ - A_) @ X_, (P_ - A_) @ Y_]).buffer(0).centroid.coords[0])
    return A_ + X_ * cx_[0] + Y_ * cx_[1], B_ + X_ * cx_[0] + Y_ * cx_[1]
_n_gx = 0; _n_gp = 0; _gx_log = []; _FREE = []                    # _FREE：端の架構で終わる桁の端（穴は桁の線を延ばした断面で）
_TM_OUT = {}
def _tm_outer(w):
    k_ = id(w[4])
    if k_ not in _TM_OUT:
        oo_ = _outer_only(w[4]); _TM_OUT[k_] = _ext_tm(oo_) if oo_ is not None else None
    return _TM_OUT[k_]
for gi in (_GIR if TAMEDIA else []):
    for end in (0, 1):
        g = gi[1]; A0_, B0_ = _gaxis(g); E, F_ = (A0_, B0_) if end == 0 else (B0_, A0_)
        ed = (F_ - E) / np.linalg.norm(F_ - E); uE = uv(E[0], E[1])[0]
        cont_ = False                                                       # 向こうに続きの桁（端がこの端の 600 以内）
        for gj in _GIR:
            if gj is gi: continue
            Aj_, Bj_ = _gaxis(gj[1])
            if min(np.linalg.norm(Aj_ - E), np.linalg.norm(Bj_ - E)) < 600.0: cont_ = True; break
        hits_ = []                                                          # (t：E から外へ, 柱か)
        O_ = E + ed * 800.0
        for w in _WOOD:
            if abs(w[5] - uE) > 0.6 or w[2] not in (L22A, L22B, L22C) or '出し梁' in w[3] or '登り梁' in w[3]: continue
            if w[3] and w[2] == L22A: continue                               # 受け材・楔は除く
            tm_ = _tm_outer(w)
            if tm_ is None: continue
            bb_ = tm_.bounds
            if np.any(bb_[0] - 1500.0 > E) or np.any(E > bb_[1] + 1500.0): continue
            loc_, _ir, _it = tm_.ray.intersects_location([O_], [-ed], multiple_hits=True)
            ts_ = sorted(float((E - l_) @ ed) for l_ in loc_)                 # E から外への距離（負は桁の中）
            ts_ = [t_ for t_ in ts_ if -400.0 < t_ < 900.0]
            if len(ts_) >= 2: hits_.append((ts_[0], ts_[-1], w[2] == L22A))
        if not hits_: continue
        # 桁の軸が柱の輪郭の中を通らない（北西・南西の角の柱は外の面を外壁の内面にそろえたので、斜めの桁が柱の外の縁にかかる）所は、
        #   桁の端（折れ目）を平面で柱の中へ動かす（柱の輪郭の桁の高さの幅の中に、桁の幅＋10＋木 40 が入る所。高さはそのまま）
        if any(h_[2] for h_ in hits_):
            for w in _WOOD:
                if w[2] != L22A or w[3] or abs(w[5] - uE) > 0.6: continue
                Fc_ = _frame_of(w[4]); opc_ = _poly_sz(w[4], Fc_)
                ln_ = opc_.intersection(LineString([(opc_.bounds[0] - 10.0, E[2]), (opc_.bounds[2] + 10.0, E[2])]))
                if ln_.is_empty: continue
                sE_ = float(_w2s(Fc_, E[None, :2] - Fc_['hm'])[0])
                if not (ln_.bounds[0] - 600.0 < sE_ < ln_.bounds[2] + 600.0): continue
                pdc_ = (Fc_['B'] - Fc_['A']) / np.linalg.norm(Fc_['B'] - Fc_['A']); c_ = max(0.3, abs(float(ed @ pdc_))); tn_ = math.sqrt(max(0.0, 1 - c_ * c_)) / c_
                mg_ = 100.0 / c_ + 90.0 * tn_ + 25.0                               # 穴（桁＋10）のまわりに木 15
                s0_, s1_ = ln_.bounds[0] + mg_, ln_.bounds[2] - mg_
                sT_ = (s0_ + s1_) / 2 if s1_ < s0_ else min(max(sE_, s0_), s1_)
                if abs(sT_ - sE_) > 30.0: sT_ = (ln_.bounds[0] + ln_.bounds[2]) / 2       # 大きく外れる折れ目（北西・南西の角）は柱の幅の真ん中へ（折れ目の両側の桁を同じ点に）
                if cont_:                                                       # 続きのある端（折れ目）：端を柱の中の一点 K（架構の線＝柱の厚みの真ん中、
                    #   柱の幅の中の sT、桁の高さ）に。折れ目の両側の桁が同じ K で終わる
                    K_ = np.r_[Fc_['A'][:2] + Fc_['hw'] * sT_ + Fc_['hm'], E[2]]
                    mv_ = K_ - E
                    if np.linalg.norm(mv_) < 0.5: hits_ = []; break
                    e = extedit.edit(g, None, (lambda A_, B_: (A_ + mv_, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + mv_)))
                    if e is not None:
                        gi[1] = e; EXT[gi[0]] = e; _n_gx += 1; _gx_log.append(f'u{uE:.2f}→K({float(mv_ @ ed) * -1:+.0f},{sT_ - sE_:+.0f})')
                    hits_ = []; break
                if abs(sT_ - sE_) < 2.0: break
                mv_ = np.r_[Fc_['hw'] * (sT_ - sE_), 0.0]
                e = extedit.edit(g, None, (lambda A_, B_: (A_ + mv_, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + mv_)))
                if e is None: break
                gi[1] = e; EXT[gi[0]] = e; g = e; _gx_log.append(f'u{uE:.2f}折れ目を柱の中へ{sT_ - sE_:+.0f}')
                A0_, B0_ = _gaxis(g); E, F_ = (A0_, B0_) if end == 0 else (B0_, A0_); ed = (F_ - E) / np.linalg.norm(F_ - E)
                O_ = E + ed * 800.0; hits_ = []
                for w2 in _WOOD:
                    if abs(w2[5] - uE) > 0.6 or w2[2] not in (L22A, L22B, L22C) or '出し梁' in w2[3] or '登り梁' in w2[3]: continue
                    if w2[3] and w2[2] == L22A: continue
                    tm_ = _tm_outer(w2)
                    if tm_ is None: continue
                    loc_, _ir, _it = tm_.ray.intersects_location([O_], [-ed], multiple_hits=True)
                    ts_ = sorted(float((E - l_) @ ed) for l_ in loc_); ts_ = [t_ for t_ in ts_ if -400.0 < t_ < 900.0]
                    if len(ts_) >= 2: hits_.append((ts_[0], ts_[-1], w2[2] == L22A))
                break
        if not hits_: continue
        cols_ = [h_ for h_ in hits_ if h_[2]]
        if cont_ and cols_:
            c_ = min(cols_, key=lambda h_: abs((h_[0] + h_[1]) / 2)); t_new = (c_[0] + c_[1]) / 2; kind_ = '柱の頭の中心'
        elif cont_:
            continue
        else:
            t_new = max(h_[1] for h_ in hits_); kind_ = '外の板の外面'; _n_gp += 1; _FREE.append((gi, end))
            # 軸が外の板の外形の下を通る（梁18 の外の板 u50.70：板の下の縁より低い）所も、その板の外面の面まで（板は下の 2d で桁を包むように深くする）
            for w in _WOOD:
                if w[2] not in (L22B, L22C) or w[3] or abs(w[5] - uE) > 0.6: continue
                Fp_ = _frame_of(w[4]); opp_ = _poly_sz(w[4], Fp_); pdp_ = (Fp_['B'] - Fp_['A']) / np.linalg.norm(Fp_['B'] - Fp_['A'])
                if abs(float(ed @ pdp_)) < 0.2: continue
                for Pf_ in (Fp_['A'], Fp_['B']):
                    tf_ = float((Pf_ - E) @ pdp_) / float(-ed @ pdp_)
                    Q_ = E - ed * tf_
                    if 0.0 < tf_ < 900.0 and opp_.buffer(300.0).contains(Point(float(_w2s(Fp_, Q_[None, :2])[0]), Q_[2])): t_new = max(t_new, tf_)
        if abs(t_new) < 0.5: continue
        lam = -t_new                                                         # 正は縮める
        e = extedit.edit(g, None, (lambda A_, B_: (A_ + ed * lam, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + ed * lam)))
        if e is None: continue
        gi[1] = e; EXT[gi[0]] = e; _n_gx += 1; _gx_log.append(f'u{uE:.2f}{"+" if t_new > 0 else ""}{t_new:.0f}')
# 折れ目の柱（二本の桁の端が同じ K）：二本の桁の柱の厚みの中の断面の和＋10 が柱の輪郭に収まらなければ、K を柱の幅の向きに動かす（2 回まで）
_n_ks = 0
for _it in range(2 if TAMEDIA else 0):
    for w in _WOOD:
        if w[2] != L22A or w[3]: continue
        Fc_ = _frame_of(w[4]); opc_ = _poly_sz(w[4], Fc_); Ac_, Bc_ = _path(w[4]); Lc_ = np.linalg.norm(Bc_ - Ac_); pc_ = (Bc_ - Ac_) / Lc_
        ends_ = []
        for gi in _GIR:
            A0_, B0_ = _gaxis(gi[1])
            for end, P_ in ((0, A0_), (1, B0_)):
                if abs(float((P_ - (Ac_ + Bc_) / 2) @ pc_)) < 5.0 and opc_.buffer(400.0).contains(Point(float(_w2s(Fc_, P_[None, :2] - Fc_['hm'])[0]), P_[2])): ends_.append((gi, end))
        _cl = []                                                             # 同じ K の端の組（高さの違う屋根の桁・床の桁は別）
        for gi, end in ends_:
            P_ = _gaxis(gi[1])[end]
            for c_ in _cl:
                if np.linalg.norm(_gaxis(c_[0][0][1])[c_[0][1]] - P_) < 30.0: c_.append((gi, end)); break
            else: _cl.append([(gi, end)])
        for ends_ in [c_ for c_ in _cl if len(c_) >= 2]:
          secs_ = []
          for gi, end in ends_:
              tm_ = _ext_tm(gi[1])
              for f_ in np.linspace(0.5, Lc_ - 0.5, 5):
                  sc_ = tm_.section(plane_origin=Ac_ + pc_ * f_, plane_normal=pc_)
                  if sc_ is None: continue
                  for lp_ in sc_.discrete:
                      if len(lp_) >= 3: secs_.append(Polygon(np.c_[_w2s(Fc_, lp_), lp_[:, 2]]).buffer(0))
          if not secs_: continue
          H_ = unary_union(secs_).buffer(10.0); zc_ = (H_.bounds[1] + H_.bounds[3]) / 2
          if opc_.buffer(-15.0).contains(H_): continue
          ln_ = opc_.intersection(LineString([(opc_.bounds[0] - 10.0, zc_), (opc_.bounds[2] + 10.0, zc_)]))
          if ln_.is_empty: continue
          dl_ = (ln_.bounds[0] + 25.0) - H_.bounds[0]; dr_ = H_.bounds[2] - (ln_.bounds[2] - 25.0)
          sh_ = dl_ if dl_ > 0 else (-dr_ if dr_ > 0 else 0.0)
          if abs(sh_) < 0.5: continue
          mv_ = np.r_[Fc_['hw'] * sh_, 0.0]
          for gi, end in ends_:
              e = extedit.edit(gi[1], None, (lambda A_, B_: (A_ + mv_, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + mv_)))
              if e is not None: gi[1] = e; EXT[gi[0]] = e
          _n_ks += 1; _gx_log.append(f'u{w[5]:.2f}折れ目を{sh_:+.0f}')
log.append(f'西館：桁の端 {_n_gx} を柱の頭の中心・端の架構の外の板の外面まで（Tamedia の留め、10-31。うち外の板の外面 {_n_gp}）：{" ".join(_gx_log)}')
# 2b. 2 階の床梁（22c）の東の端を柱の東の面（v−1.05、外壁の内面）で止める（I：柱の面から 110〜130 出て宙で終わっていた）
_n_fe = 0
for w in _WOOD:
    if w[2] != L22C: continue
    g = w[4]
    if to_uv_arr(extedit.samples(g, 60))[:, 1].max() < -1.05 + 0.002: continue
    def _fe(V, k=0):
        if k: return V
        for i_, (x_, y_, z_) in enumerate(V):
            uu_, vv_ = uv(x_, y_)
            if vv_ > -1.052: q_ = np.ravel(xy(uu_, -1.052)); V[i_, 0], V[i_, 1] = q_[0], q_[1]
        return V
    e = extedit.edit(g, _fe)
    if e is None: continue
    _wset(w, e); _n_fe += 1
log.append(f'西館：2 階の床梁 {_n_fe} 枚の東の端を柱の東の面（v−1.05）で止めた')
# 2c. 桁の端の当たり（10-29 昼、監修の項 20261029-0928 の 1）：桁（まっすぐな押し出し、小口は道に直角）の端を、柱に重ならず
#     （斜めの桁の小口の角が柱に 0.9〜1.4 L 入っていた）、何かに触れる所に。柱（穴を除いた外形）に重なる端は重ならない所まで縮め、
#     どこにも触れない端（u48 の西の桁：板の端の外で止まり 132 足りなかった）は、柱・板（外形）に触れるまで延ばす（400 まで）。
_n_gr = _n_ge = 0; _gr_max = _ge_max = 0.0; _GCOL = set()
for gi in ([] if TAMEDIA else _GIR):
    for end in (0, 1):
        g = gi[1]; A, B = _path(g); E, F_ = (A, B) if end == 0 else (B, A)
        ed = (F_ - E) / np.linalg.norm(F_ - E); uE = uv(E[0], E[1])[0]
        Ms_ = []
        for w in _WOOD:
            if abs(w[5] - uE) > 0.6 or w[2] not in (L22A, L22B, L22C): continue
            oo_ = _outer_only(w[4])
            if oo_ is None: continue
            M_ = _tm_mf(_ext_tm(oo_))
            if M_ is None: continue
            bb_ = np.array(M_.bounding_box())
            if np.all(bb_[:3] - 600.0 <= E) and np.all(E <= bb_[3:] + 600.0): Ms_.append((w[2], M_))
        if not Ms_: continue
        MC_ = [M_ for l_, M_ in Ms_ if l_ == L22A]; MA_ = [M_ for l_, M_ in Ms_]
        def _moved(lam):
            return extedit.edit(g, None, (lambda A_, B_: (A_ + ed * lam, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + ed * lam)))
        def _ov(lam, Ms):
            e_ = _moved(lam)
            if e_ is None: return 1e12
            Mg_ = _tm_mf(_ext_tm(e_))
            if Mg_ is None: return 1e12                                     # 測れない所は重なるとみる（延ばしすぎない）
            return sum((Mg_ ^ M_).volume() for M_ in Ms)
        v0_ = _ov(0.0, MC_) if MC_ else 0.0
        # 10-29 夜（監修の項 20261029-2027 の 2）：桁の端はかならず柱で受ける。斜めの桁も板の面で止めず、板の穴を通して柱の面まで
        #   （前は板の面で止め、柱まで 74〜198 浮いていた）。柱に重なる端は重ならない所まで縮め、柱に触れない端は柱に触れるまで延ばす（400 まで）。
        #   柱が届く所に無い端だけ、前と同じく柱・板に触れるまで
        lam_new = None
        if MC_ and 1e3 < v0_ < 1e11:                                               # 柱に重なる → 縮める（重ならない最短）
            lo_, hi_ = 0.0, 300.0
            if _ov(hi_, MC_) <= 1e3:
                for _ in range(14):
                    mid_ = (lo_ + hi_) / 2
                    if _ov(mid_, MC_) > 1e3: lo_ = mid_
                    else: hi_ = mid_
                lam_new = hi_; _n_gr += 1; _gr_max = max(_gr_max, hi_); _GCOL.add((id(gi), end))
        elif MC_ and _ov(-3.0, MC_) > 1.0:                                         # 柱に触れている
            _GCOL.add((id(gi), end))
        elif MC_ and _ov(-400.0, MC_) > 10.0:                                      # 柱に触れるまで延ばす（板の穴を通る）
            lo_, hi_ = 0.0, -400.0
            for _ in range(14):
                mid_ = (lo_ + hi_) / 2
                if _ov(mid_, MC_) > 10.0: hi_ = mid_
                else: lo_ = mid_
            lam_new = lo_; _n_ge += 1; _ge_max = max(_ge_max, -lo_); _GCOL.add((id(gi), end))
        elif _ov(-3.0, MA_) <= 1.0:                                                # 3 延ばしても何にも触れない → 触れるまで延ばす
            lo_, hi_ = 0.0, -400.0
            if _ov(hi_, MA_) > 10.0:
                for _ in range(14):
                    mid_ = (lo_ + hi_) / 2
                    if _ov(mid_, MA_) > 10.0: hi_ = mid_                       # 10 mm³ でも重なれば手前（板に穴ができないよう、10-29 夕）
                    else: lo_ = mid_
                lam_new = lo_; _n_ge += 1; _ge_max = max(_ge_max, -lo_)
        if lam_new is None or abs(lam_new) < 0.3: continue
        e = _moved(lam_new)
        if e is None: continue
        gi[1] = e; EXT[gi[0]] = e
log.append(f'西館：桁の端 {_n_gr} を柱に重ならない所まで縮め（いちばん大きく {_gr_max:.0f}）、どこにも触れない端 {_n_ge} を柱・板に触れるまで延ばした（いちばん大きく {_ge_max:.0f}）')
# 3. 穴を通る桁の断面で作り直す
_GTM = []
for gi in _GIR:
    T_ = tri.tri_extrusion(gi[1])
    if not len(T_): continue
    tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(); _GTM.append(tm_)
# 2d. 桁が板の縁の近くを通る所は、板の下を局所的に深くして桁を包む（10-29 夜、監修の項 20261029-2027 の 2：斜めの桁も穴を通して柱まで。
#     桁の断面＋10 の穴のまわりに 70 の木が残るよう、穴の 80 外と、そのまわりの板の外形の凸包を足す。頭のハンチと同じ考え）
def _knot_pts(c, n=24):
    nc = c.ToNurbsCurve(); dm = nc.Domain
    if nc.Degree == 1: return extedit._pts(nc)
    kn = sorted(set([dm.T0, dm.T1] + [float(nc.Knots[i]) for i in range(len(nc.Knots)) if dm.T0 < nc.Knots[i] < dm.T1]))
    return np.array([[q.X, q.Y, q.Z] for q in (nc.PointAt(t) for t in np.unique(np.concatenate([np.linspace(a_, b_, n + 1) for a_, b_ in zip(kn, kn[1:])])))])
_n_wrap = 0
for w in _WOOD:
    if w[2] not in (L22B, L22C) or '出し梁' in w[3]: continue
    g = w[4]; A, B = _path(g); L_ = np.linalg.norm(B - A); pd_ = (B - A) / L_; pl_ = g.GetProfilePlane(0.0); X = _v3(pl_.XAxis); Y = _v3(pl_.YAxis)
    P0_ = _knot_pts(g.Profile3d(0, 0.0)); op_ = Polygon(np.c_[(P0_ - A) @ X, (P0_ - A) @ Y]).buffer(0)
    S_ = extedit.samples(g, 40); lo_, hi_ = S_.min(0) - 50.0, S_.max(0) + 50.0
    secs = []
    for tm_ in _GTM:
        b_ = tm_.bounds
        if np.any(b_[0] > hi_) or np.any(b_[1] < lo_): continue
        for s_ in np.linspace(0.5, L_ - 0.5, 5):
            sc = tm_.section(plane_origin=A + pd_ * s_, plane_normal=pd_)
            if sc is None: continue
            for lp in sc.discrete:
                q_ = np.c_[(lp - A) @ X, (lp - A) @ Y]
                if len(q_) >= 3 and Polygon(q_).buffer(0).area > 500.0: secs.append(Polygon(q_).buffer(0))
    if not secs: continue
    add_ = []
    for h_ in getattr(unary_union(secs).buffer(10.0), 'geoms', [unary_union(secs).buffer(10.0)]):
        if h_.area < 2000.0 or h_.intersection(op_).area < 1.0 or op_.buffer(-60.0).contains(h_): continue
        add_.append(unary_union([op_.intersection(h_.buffer(370.0).envelope), h_.buffer(70.0)]).convex_hull)
    if not add_: continue
    new_ = unary_union([op_] + add_)
    new_ = max(getattr(new_, 'geoms', [new_]), key=lambda q: q.area).simplify(0.3)
    e_ = r.Extrusion()
    if not (e_.SetPathAndUp(g.PathStart, g.PathEnd, pl_.YAxis) and e_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in np.asarray(new_.exterior.coords)]).ToNurbsCurve(), True)): continue
    _wset(w, e_); _n_wrap += 1
log.append(f'西館：桁が縁の近くを通る板 {_n_wrap} 枚の下を局所的に深くして桁を包んだ（穴のまわりに 70 以上の木）')
_FIXPOLY = []
import shapely.affinity as _shp_aff
def _rebuild_holes(g, col=False, bear=False):
    op_, A, B, X, Y = _outer2d(g, 600); L_ = np.linalg.norm(B - A); pd_ = (B - A) / L_
    S_ = extedit.samples(g, 40); lo_, hi_ = S_.min(0) - 50.0, S_.max(0) + 50.0
    secs = []
    for tm_ in _GTM:
        b_ = tm_.bounds
        if np.any(b_[0] > hi_) or np.any(b_[1] < lo_): continue
        for s_ in ([L_ / 2] if col and not TAMEDIA else np.linspace(0.5, L_ - 0.5, 5)):   # 10-31：柱も桁が通る（端は柱の頭の中心）ので 5 枚の面で       # 柱：桁は柱の面で止まるので、通り抜ける桁だけ（厚みの真ん中）
            sc = tm_.section(plane_origin=A + pd_ * s_, plane_normal=pd_)
            if sc is None: continue
            for lp in sc.discrete:
                q_ = np.c_[(lp - A) @ X, (lp - A) @ Y]
                if len(q_) >= 3 and Polygon(q_).buffer(0).area > 500.0: secs.append(Polygon(q_).buffer(0))     # 10-29 夕：小口の角が触れるだけの細い断面は穴にしない
    old_n = g.ProfileCount - 1
    c0_ = g.Profile3d(0, 0.0); Q0_ = np.array([[q.X, q.Y, q.Z] for q in (c0_.PointAt(t) for t in np.linspace(c0_.Domain.T0, c0_.Domain.T1, 600))])
    if not secs and old_n == 0 and Polygon(np.c_[(Q0_ - A) @ X, (Q0_ - A) @ Y]).is_valid: return None, 0, 0, 0
    H_ = unary_union(secs).buffer(10.0, resolution=8).simplify(0.5) if secs else None
    if bear and H_ is not None:                                                # 10-31：一枚の梁も桁のピンに載る（穴の上の縁が桁の上端に）                                                # 10-29 夜（項 2027 の 3）：柱の無い梁（u43.5）は桁に載る：穴の上の縁を桁の上端に合わせる
        up_ = np.array([X[2], Y[2]]); up_ /= np.linalg.norm(up_)
        H_ = _shp_aff.translate(H_, -10.0 * up_[0], -10.0 * up_[1])
    inner, notch = [], 0
    for h_ in (getattr(H_, 'geoms', [H_]) if H_ is not None else []):
        if h_.is_empty or h_.area < 2000.0 or h_.intersection(op_).area < 1.0: continue     # 材の外を通る桁（梁の下など）
        if op_.buffer(-3.0).contains(h_): inner.append(h_)
        else: notch += 1
    nc0 = g.Profile3d(0, 0.0).ToNurbsCurve(); W_ = extedit._weights(nc0); P_ = extedit._pts(nc0)
    extedit._set_pts(nc0, np.c_[(P_ - A) @ X, (P_ - A) @ Y, np.zeros(len(P_))], W_)
    c0_ = g.Profile3d(0, 0.0); Q0_ = np.array([[q.X, q.Y, q.Z] for q in (c0_.PointAt(t) for t in np.linspace(c0_.Domain.T0, c0_.Domain.T1, 600))])
    if not Polygon(np.c_[(Q0_ - A) @ X, (Q0_ - A) @ Y]).is_valid:                # 輪郭が自分と交わる（H：外壁の内面で止めた 2 階の床梁）→ 正しい多角形の折れ線に
        pv_ = max(getattr(op_, 'geoms', [op_]), key=lambda q: q.area).simplify(0.5)
        nc0 = r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in np.asarray(pv_.exterior.coords)]).ToNurbsCurve(); op_ = pv_
        _FIXPOLY.append(1)
    e = r.Extrusion()
    if not e.SetPathAndUp(g.PathStart, g.PathEnd, g.GetProfilePlane(0.0).YAxis): return None, 0, 0, 0
    if not e.SetOuterProfile(nc0, True): return None, 0, 0, 0
    for h_ in inner:
        c_ = np.asarray(h_.exterior.coords)
        pl_ = r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in c_])
        if not e.AddInnerProfile(pl_.ToNurbsCurve()): return None, 0, 0, 0
    return e, old_n, len(inner), notch
_n_ho = _n_hn = _n_notch = _n_rb = 0
for w in _WOOD:
    e, a_, b_, c_ = _rebuild_holes(w[4], w[2] == L22A)
    if e is None: continue
    _wset(w, e); _n_rb += 1; _n_ho += a_; _n_hn += b_; _n_notch += c_
    if c_: log.append(f'  !! 桁が材の縁にかかる（穴にできない）：{m.Layers[w[2]].Name[:3]} u{w[5]:.2f} {c_} か所')
# 4. 東の柱の頭は、その位置の 2 枚の梁の外形（東の端の丸み）の上端まで（10-29、ユーザー・監修の判断③：梁の外形より上に出さない）
_DO_HEADCUT = True; _n_hc = 0; _hc_max = 0.0
for w in (_WOOD if _DO_HEADCUT else []):
    if w[2] != L22A or w[3]: continue
    g = w[4]; S_ = extedit.samples(g, 60); U_ = to_uv_arr(S_)
    if S_[:, 2].max() < 7000.0 or U_[:, 1].mean() < -2.0: continue                    # 東の柱（屋根の高さまで）
    op_, A, B, X, Y = _outer2d(g, 800)
    dn_ = np.array([-X[2], -Y[2]]); dn_ /= np.linalg.norm(dn_); e2_ = np.array([-dn_[1], dn_[0]])
    tops_ = []
    for x in _WOOD:
        if x[2] != L22B or abs(x[5] - w[5]) > 0.4 or '出し梁' in x[3] or '登り梁' in x[3]: continue
        c_ = x[4].Profile3d(0, 0.0); Q_ = np.array([[q.X, q.Y, q.Z] for q in (c_.PointAt(t) for t in np.linspace(c_.Domain.T0, c_.Domain.T1, 2000))])
        tops_.append(Polygon(np.c_[(Q_ - A) @ X, (Q_ - A) @ Y]).buffer(0))
    if len(tops_) < 2: continue
    Cq_ = np.asarray(op_.exterior.coords); ca_ = Cq_ @ e2_; cb_ = Cq_ @ dn_
    al_ = []
    for a0_ in np.linspace(ca_.min() - 5.0, ca_.max() + 5.0, 120):
        tb_ = []
        for tp_ in tops_:
            ln_ = LineString([e2_ * a0_ + dn_ * (cb_.min() - 3000.0), e2_ * a0_ + dn_ * (cb_.max() + 3000.0)]).intersection(tp_)
            tb_.append(min(np.asarray(gg_.coords) @ dn_ for gg_ in getattr(ln_, 'geoms', [ln_]) if not gg_.is_empty).min() if not ln_.is_empty else -1e9)
        al_.append((a0_, max(tb_)))                                                      # 2 枚のうち低いほうの上端（下向きの座標の大きいほう）
    if all(t_ < -1e8 for _, t_ in al_): continue
    al_ = [(a0_, t_ if t_ > -1e8 else cb_.min() - 10.0) for a0_, t_ in al_]
    allow_ = Polygon([e2_ * a0_ + dn_ * t_ for a0_, t_ in al_] + [e2_ * al_[-1][0] + dn_ * (cb_.max() + 100.0), e2_ * al_[0][0] + dn_ * (cb_.max() + 100.0)]).buffer(0)
    cut_ = op_.intersection(allow_)
    if op_.difference(allow_).area < 100.0: continue
    pv_ = max(getattr(cut_, 'geoms', [cut_]), key=lambda q: q.area).simplify(0.5)
    nc_ = r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in np.asarray(pv_.exterior.coords)]).ToNurbsCurve()
    e = r.Extrusion()
    if not (e.SetPathAndUp(g.PathStart, g.PathEnd, g.GetProfilePlane(0.0).YAxis) and e.SetOuterProfile(nc_, True)): continue
    _wset(w, e); _n_hc += 1
    Dq_ = op_.difference(allow_); _hc_max = max(_hc_max, max(np.ptp(np.asarray(gg_.exterior.coords) @ dn_) for gg_ in getattr(Dq_, 'geoms', [Dq_])))
log.append(f'西館：東の柱 {_n_hc} 本の頭を 2 枚の梁の外形の上端（低いほう）で切った（いちばん大きく下げた所 {_hc_max:.0f}）')
log.append(f'西館：柱・梁・2 階の床梁 {_n_rb} 本の穴 {_n_ho} を消し、通る桁の断面＋10 の穴 {_n_hn} に作り直した（縁にかかる {_n_notch}）。自分と交わる輪郭 {len(_FIXPOLY)} を正しい折れ線に')
# 3g. 端の納まり（10-29 昼、西館係。監修の項 20261029-0928 の 1）：端は受ける材の面にぴったり、重ならない。押し出しのまま、
#     外形を折れ線の多角形に作り直す（穴はそのまま）。座標は材ごとの (s, z)：s＝輪郭の面の中の水平の向き、z＝高さ。
#   a. 2 階の床梁（22c）の西の端を外壁の内面の線で切る（u24〜33 で壁の中へ 110〜130 入っていた。2 枚は同じ所＝内側の 1 枚の止まる所）。
#   b. 柱の外の面を、床梁の端の高さ（西は床梁の端、東は高窓の帯の窓台・まぐさと u21.33 の床梁の端）だけ外壁の内面の線まで出す
#      （床梁・窓台・まぐさの端がそこで柱に当たる。u24 の東の柱の床梁の所と同じ。柱の幅の中だけ）。
#   c. 東の柱の頭：梁の下端より上は、2 枚の梁の外形の重なり（低いほう）の、柱の西の面より東の所（梁の東の端の丸みまで柱が満たす。
#      梁の先が柱から 31〜34 浮いていた・頭の西の鉤）。梁の外形より上には出さない（判断③のまま）。
#   d. 柱の輪郭の細い突起・波（20 未満の幅）を除く。
#   e. 出し梁の付く梁（22b）の西の端の上の角を、屋根の面までの直角に（丸みのすき間で出し梁の内の端が梁に触れていなかった）。
def _clean_poly(poly, lmin=2.0, amin=0.5):
    """輪郭の点のうち、となりとの辺が lmin 未満・折れが amin 度未満の点を除く（押し出しの小口の三角形が潰れないよう。10-29 夕、監修の項 1530：
    柱の外の面を切った所に退化三角形 24）"""
    P = [tuple(q) for q in np.asarray(poly.exterior.coords)[:-1]]
    for _ in range(4):
        keep, n = [], len(P)
        for i in range(n):
            a, b, c = np.array(P[i - 1]), np.array(P[i]), np.array(P[(i + 1) % n])
            e1, e2 = b - a, c - b; l1, l2 = np.linalg.norm(e1), np.linalg.norm(e2)
            if l1 < lmin or l2 < 1e-9: continue
            ang = math.degrees(math.acos(max(-1.0, min(1.0, float(e1 @ e2) / (l1 * l2)))))
            if ang < amin: continue
            keep.append(P[i])
        if len(keep) == n or len(keep) < 3: break
        P = keep
    q = Polygon(P).buffer(0)
    return q if (q.geom_type == 'Polygon' and abs(q.area - poly.area) < 0.01 * poly.area + 500.0) else poly
def _rebuild_sz(g, F, poly):
    """外形を (s, z) の多角形 poly に、穴は元のまま"""
    poly = max(getattr(poly, 'geoms', [poly]), key=lambda q: q.area)
    poly = _clean_poly(poly.simplify(0.3))
    loc_ = _sz2l(F, np.asarray(poly.exterior.coords))
    e_ = r.Extrusion()
    if not e_.SetPathAndUp(g.PathStart, g.PathEnd, g.GetProfilePlane(0.0).YAxis): return None
    if not e_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in loc_]).ToNurbsCurve(), True): return None
    for k in range(1, g.ProfileCount):
        hp_ = _poly_sz(g, F, k)
        if not poly.buffer(-2.0).contains(hp_): continue                       # 外形の外に出た穴は捨てる
        nc_ = g.Profile3d(k, 0.0).ToNurbsCurve(); W_ = extedit._weights(nc_); P_ = extedit._pts(nc_)
        extedit._set_pts(nc_, np.c_[(P_ - F['A']) @ F['X'], (P_ - F['A']) @ F['Y'], np.zeros(len(P_))], W_)
        if not e_.AddInnerProfile(nc_): return None
    return e_
def _half(F, s0, keep_pos, z0=-1e5, z1=1e5):                                  # s ≥ s0（keep_pos）か s ≤ s0 の帯
    return Polygon([(s0, z0), (s0 + 1e5, z0), (s0 + 1e5, z1), (s0, z1)]) if keep_pos else Polygon([(s0 - 1e5, z0), (s0, z0), (s0, z1), (s0 - 1e5, z1)])
def _wall_s(F, sref):                                                         # 材の面の水平の線が外壁の内面（WNi）を切る所の s（sref にいちばん近い）
    ln_ = LineString([F['A'][:2] + F['hw'] * (sref - 3000.0) + F['hm'], F['A'][:2] + F['hw'] * (sref + 3000.0) + F['hm']]).intersection(WNi.exterior)
    pts_ = [ln_] if ln_.geom_type == 'Point' else [q for q in getattr(ln_, 'geoms', []) if q.geom_type == 'Point']
    if not pts_: return None
    return min((float(_w2s(F, np.array([[q.x, q.y]]) - F['hm'])[0]) for q in pts_), key=lambda s: abs(s - sref))
_g3 = dict(trim=0, pad=0, head=0, clean=0, sq=0)
_W3 = [w for w in _WOOD if not ('出し梁' in w[3] or '登り梁' in w[3])]
# u. 北西の角の u43.5 の梁を、となりの架構の梁と同じ形の 2 枚組に（10-29 昼、ユーザー：スパン15の真ん中に差し込まれた梁はほかの梁と同じ形に）。
#    u42 の 2 枚を円の中心のまわりに 1.5 m 回して u43.5 の両側（±135）へ。断面の形（せい・ハンチ・東の端の丸い頭）はそのまま、上端はその 1 枚の上の
#    屋根の面へ（縦の線ごとに上端の差だけ上下、せいは同じ）、西の端は外壁の内面の線へ（梁の真ん中から西の点を一次にずらす。西の頭の形はそのまま）。
#    柱は無いので、東の端は東の桁の上（梁の下端の 10 下に桁）、西は西の桁が 2 枚の穴を通る（金物で受ける）。穴は通る桁の断面＋10（3f の 3 と同じ）。
#    出し梁はほかの梁と同じく下で作る。光の筋は無し（2 枚のあいだの上は屋根の板がふさぐ）。
def _rot2(p_, a_):
    c_, s_ = math.cos(a_), math.sin(a_); x_, y_ = p_[0] - CX, p_[1] - CY; return np.array([CX + c_ * x_ - s_ * y_, CY + s_ * x_ + c_ * y_])
U_RAF = 43.5; V_WIN_RAF = -1.052; NAME_RAF = '一枚の梁（北西の角 u43.5、厚さ 190、柱なし：両端は桁のピン、10-31）'
RAF_T = 190.0       # 10-31（ユーザー 21:26、監修の項 2127）：柱を挟まないので 2 枚の合わせ梁をやめ一枚に（2 枚の分をまとめた厚さ）
_RAF_IDX = []
def _raf(): return [_XNEW[i_][0] for i_ in _RAF_IDX]
_w42 = [x for x in _W3 if x[2] == L22B and not x[3] and abs(x[5] - 42.0) < 0.4]
_c42 = np.mean([(_path(x[4])[0] + _path(x[4])[1]) / 2 for x in _w42], axis=0) if _w42 else None    # u42 の 2 枚のあいだの真ん中
for w in _w42[:1]:                                                              # 10-31：一枚（u42 の 1 枚の外形を写し、u43.5 の線の上に厚さ 190）
    g0 = w[4].Duplicate(); dth_ = -(U_RAF - 42.0) * 1000.0 / RW
    g0.Rotate(dth_, r.Vector3d(0, 0, 1), r.Point3d(CX, CY, 0.0))
    _Pa, _Pb = _path(g0); _pd = (_Pb - _Pa) / np.linalg.norm(_Pb - _Pa)
    _C = np.r_[_rot2(_c42[:2], dth_), _c42[2]]; _Pc = _Pa + _pd * float((_C - _Pa) @ _pd)
    _P0, _P1 = _Pc - _pd * RAF_T / 2, _Pc + _pd * RAF_T / 2
    _dP = _P0 - _Pa                                                         # 写した 1 枚から u43.5 の線の上への移し（道の向き）
    g0 = extedit.edit(g0, None, lambda A_, B_: (_P0, _P1)) or g0
    F = _frame_of(g0); op_ = _poly_sz(g0, F); dv_ = _dv(F)
    zT_ = lambda s, F=F: float(_RWf['roof_f'](*(_rot2(F['A'][:2] - _dP[:2] + F['hw'] * s + F['hm'], -dth_))))   # 写す前の面（u42 の 1 枚の上）
    zN_ = lambda s, F=F: float(_RWf['roof_f'](*(F['A'][:2] + F['hw'] * s + F['hm'])))
    sW_ = op_.bounds[0] if dv_ > 0 else op_.bounds[2]; sE_ = op_.bounds[2] if dv_ > 0 else op_.bounds[0]
    sw2_ = _wall_s(F, sW_)
    if sw2_ is None: continue
    dW_ = sw2_ - sW_
    # 西の頭は西の桁に合わせる（u42 の板の西の桁の穴と同じ所に桁が来るように、西の点を桁の位置の差だけずらす。外壁の内面に合わせると桁が
    # 板の下の縁にかかった）。端は外壁の内面の手前になり、出し梁が外壁を貫く（u45・48 の端の板と同じ）
    _hT = [Polygon(_l2sz(F, np.c_[(P_ - F['A']) @ F['X'], (P_ - F['A']) @ F['Y']])).centroid for P_ in [_ring_pts(g0, k_) for k_ in range(1, g0.ProfileCount)]]
    _hT = [c_ for c_ in _hT if uv(*(F['A'][:2] + F['hw'] * c_.x + F['hm']))[1] < -9.0]
    for gi in _GIR:
        Ug_ = to_uv_arr(extedit.samples(gi[1], 60))
        if not (Ug_[:, 1].mean() < -9.0 and Ug_[:, 0].min() < U_RAF < Ug_[:, 0].max() and _hT): continue
        Ag_, Bg_ = _path(gi[1])
        xg_ = LineString([Ag_[:2], Bg_[:2]]).intersection(LineString([F['A'][:2] + F['hw'] * (sW_ - 5000.0) + F['hm'], F['A'][:2] + F['hw'] * (sW_ + 5000.0) + F['hm']]))
        if xg_.geom_type == 'Point':
            sgN_ = float(_w2s(F, np.array([[xg_.x, xg_.y]]) - F['hm'])[0]); dW_ = sgN_ - _hT[0].x
    sa_ = sE_ + (sW_ - sE_) * 0.45; sb_ = sE_ + (sW_ - sE_) * 0.70      # 真ん中（東から 45〜70%）でずらす量を 0 → dW へ
    def _mv(q):
        s, z = q; f_ = float(np.clip((s - sa_) / (sb_ - sa_), 0.0, 1.0)); s2 = s + dW_ * f_
        return (s2, z - zT_(s) + zN_(s2))
    new_ = Polygon([_mv(q) for q in np.asarray(op_.exterior.coords)]).buffer(0)
    e_ = r.Extrusion()
    new_ = max(getattr(new_, 'geoms', [new_]), key=lambda q: q.area)
    sv_ = _s_of_v(F, V_WIN_RAF, sE_)                                          # 10-29 夜（項 2027 の 3）：東の端は外壁の内面で止める（29 食い込んでいた）
    new_ = new_.intersection(Polygon([(sv_, -1e5), (sv_ - dv_ * 1e6, -1e5), (sv_ - dv_ * 1e6, 1e5), (sv_, 1e5)]).buffer(0))
    pv_ = _clean_poly(max(getattr(new_, 'geoms', [new_]), key=lambda q: q.area).simplify(0.3))
    if not (e_.SetPathAndUp(g0.PathStart, g0.PathEnd, g0.GetProfilePlane(0.0).YAxis) and
            e_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in _sz2l(F, np.asarray(pv_.exterior.coords))]).ToNurbsCurve(), True)): continue
    # 西の桁が板の下の縁にかかる所は、桁の断面＋70 を包むように板の下を局所的に深くする（頭のハンチと同じ考え。u43.5 は屋根の線が短く、
    # 同じ v で屋根が低いので、u42 の形のままでは桁が下の縁にかかった）
    A_, B_ = _path(e_); pd_ = (B_ - A_) / np.linalg.norm(B_ - A_); Xl_ = _v3(e_.GetProfilePlane(0.0).XAxis); Yl_ = _v3(e_.GetProfilePlane(0.0).YAxis)
    secs_ = []
    for tm_ in _GTM:
        for sq_ in (5.0, RAF_T / 2, RAF_T - 5.0):
            sc_ = tm_.section(plane_origin=A_ + pd_ * sq_, plane_normal=pd_)
            if sc_ is None: continue
            for lp_ in sc_.discrete:
                if len(lp_) >= 3: secs_.append(Polygon(_l2sz(F, np.c_[(lp_ - A_) @ Xl_, (lp_ - A_) @ Yl_])).buffer(0))
    secs_ = [q_ for q_ in secs_ if not q_.is_empty and uv(*(F['A'][:2] + F['hw'] * q_.centroid.x + F['hm']))[1] < -9.0]     # 西の桁だけ
    if secs_:
        H70_ = unary_union(secs_).buffer(80.0)
        H70_ = max(getattr(H70_, 'geoms', [H70_]), key=lambda q: q.area)
        if H70_.intersects(pv_) and not pv_.buffer(-3.0).contains(H70_):
            loc_ = pv_.intersection(H70_.buffer(300.0).envelope)
            pv_ = unary_union([pv_, unary_union([loc_, H70_]).convex_hull]).buffer(0)
            pv_ = _clean_poly(max(getattr(pv_, 'geoms', [pv_]), key=lambda q: q.area).simplify(0.3))
            e3_ = r.Extrusion()
            if e3_.SetPathAndUp(g0.PathStart, g0.PathEnd, g0.GetProfilePlane(0.0).YAxis) and e3_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in _sz2l(F, np.asarray(pv_.exterior.coords))]).ToNurbsCurve(), True): e_ = e3_
    e2_, _a, _b, _c = _rebuild_holes(e_, bear=True)
    if e2_ is not None: e_ = e2_
    at_ = r.ObjectAttributes(); at_.LayerIndex = L22B; at_.Name = NAME_RAF
    _XNEW.append((e_, at_)); wn_ = ['x', len(_XNEW) - 1, L22B, NAME_RAF, e_, _umed(e_)]
    _WOOD.append(wn_); _W3.append(wn_); _RAF_IDX.append(len(_XNEW) - 1)
log.append(f'西館：u43.5 の一枚の梁（厚さ {RAF_T:.0f}）を u42 の板から写して {len(_RAF_IDX)} 枚（上端はその 1 枚の上の屋根の面、西の端は外壁の内面、柱なし・両端は桁に金物）')
# 0. 2 階の床梁（22c）の上端を 2 階の床の下面 3170 に（10-29 昼、監修の項 20261029-0928 の追記：床の下面 3170 と床梁の上端 3200 が 30 重なっていた。
#    床・1 階の壁の上端・階段の箱の開口 3170 は動かさず、床梁の上を 30 落とす。下端・穴（桁）はそのまま、せい 800 → 770）
FL2_BOT = 3170.0; _n_fb = 0
for w in _W3:
    if w[2] != L22C: continue
    F = _frame_of(w[4]); op_ = _poly_sz(w[4], F)
    if op_.bounds[3] <= FL2_BOT + 0.5: continue
    e_ = _rebuild_sz(w[4], F, op_.intersection(Polygon([(-1e6, -1e5), (1e6, -1e5), (1e6, FL2_BOT), (-1e6, FL2_BOT)])))
    if e_ is not None: _wset(w, e_); _n_fb += 1
log.append(f'西館：2 階の床梁 {_n_fb} 枚の上端を床の下面 {FL2_BOT:.0f} に（30 落とす）')
# a. 2 階の床梁の西の端
_STOPW = {}                                                                   # 架構の u → (止めた v, 床梁の端の z の範囲)
_FU3 = [21.33] + [24.0 + 3.0 * k for k in range(9)]
def _fk(u_): return min(_FU3, key=lambda f_: abs(f_ - u_))
_byf = {}
for w in _W3:
    if w[2] == L22C: _byf.setdefault(_fk(w[5]), []).append(w)
for fk_, ws_ in _byf.items():
    cand_ = []
    for w in ws_:
        F = _frame_of(w[4]); op_ = _poly_sz(w[4], F); dv_ = _dv(F)
        sb_ = op_.bounds; sW_ = sb_[0] if dv_ > 0 else sb_[2]                  # 西の端（v の小さい側）
        if uv(*(F['A'][:2] + F['hw'] * sW_ + F['hm']))[1] > -5.2: continue    # 西の片の無い東の片（階段の上で切った u33 の東の片）
        sw_ = _wall_s(F, sW_)
        if sw_ is None: continue
        cand_.append((w, F, op_, dv_, sW_, sw_, uv(*(F['A'][:2] + F['hw'] * sw_ + F['hm']))[1]))
    if not cand_: continue
    vstop_ = max(c_[6] for c_ in cand_)                                       # 2 枚は同じ所（内側の 1 枚が壁に当たる所）
    for w, F, op_, dv_, sW_, sw_, _v in cand_:
        s_ = _s_of_v(F, vstop_, sw_)
        if (s_ - sW_) * dv_ > 2.0:                                            # 壁の中へ出ている
            e_ = _rebuild_sz(w[4], F, op_.intersection(_half(F, s_, dv_ > 0)))
            if e_ is not None: _wset(w, e_); _g3['trim'] += 1; op_ = _poly_sz(e_, F)
        near_ = [z_ for s2_, z_ in np.asarray(op_.exterior.coords) if abs(s2_ - s_) < 3.0]
        if near_: _STOPW.setdefault(fk_, []).append((vstop_, min(near_), max(near_)))
# b. 柱の外の面を、端の当たる高さだけ外壁の内面の線へ
_BANDS_E = [(BAND_Z0 - 180.0, BAND_Z0), (BAND_Z1, BAND_Z1 + 180.0)]; _PADS = []
for w in _W3:
    if w[2] != L22A or w[3]: continue
    g = w[4]; F = _frame_of(g); op_ = _poly_sz(g, F); dv_ = _dv(F)
    U_ = to_uv_arr(extedit.samples(g, 40)); vmid_ = float(np.median(U_[:, 1]))
    pads_ = []
    if vmid_ < -5.0:                                                          # 西の柱：床梁の端
        for vstop_, z0_, z1_ in _STOPW.get(_fk(w[5]), []): pads_.append((vstop_, z0_, min(z1_, 3170.0)))     # 2 階の床（3170〜）には出さない
    elif vmid_ > -2.5 and op_.bounds[3] > 7000.0:                            # 東の柱：窓台・まぐさ、床梁の東の端
        for z0_, z1_ in _BANDS_E: pads_.append((-1.052, z0_, z1_))
        for x in _W3:
            if x[2] != L22C or abs(x[5] - w[5]) > 0.4: continue
            Fx = _frame_of(x[4]); opx_ = _poly_sz(x[4], Fx); dx_ = _dv(Fx)
            sE_ = opx_.bounds[2] if dx_ > 0 else opx_.bounds[0]
            if uv(*(Fx['A'][:2] + Fx['hw'] * sE_ + Fx['hm']))[1] < -1.2: continue
            zz_ = [z_ for s2_, z_ in np.asarray(opx_.exterior.coords) if abs(s2_ - sE_) < 3.0]
            if zz_: pads_.append((-1.052, min(zz_), min(max(zz_), 3170.0)))
    if not pads_: continue
    _PADS.append((w, pads_))
# c. 東の柱の頭
for w in _W3:
    if w[2] != L22A or w[3]: continue
    g = w[4]; F = _frame_of(g); op_ = _poly_sz(g, F)
    if op_.bounds[3] < 7000.0 or float(np.median(to_uv_arr(extedit.samples(g, 40))[:, 1])) < -2.5: continue
    plies_ = []
    for x in _W3:
        if x[2] != L22B or abs(x[5] - w[5]) > 0.4: continue
        Px_ = _ring_pts(x[4], 0); plies_.append(Polygon(np.c_[_w2s(F, Px_), Px_[:, 2]]).buffer(0))
    if len(plies_) < 2: continue
    Bm_ = plies_[0].intersection(plies_[1])
    dv_ = _dv(F)
    sw_ = se_ = None
    for zq_ in np.arange(op_.bounds[3] - 3000.0, op_.bounds[3] - 2000.0, 50.0):    # 柱の西の面・東の面（頭の下の、まっすぐな所）
        x_ = op_.intersection(LineString([(op_.bounds[0] - 10, zq_), (op_.bounds[2] + 10, zq_)]))
        if x_.is_empty: continue
        b_ = x_.bounds; s_w, s_e = (b_[0], b_[2]) if dv_ > 0 else (b_[2], b_[0])
        sw_ = s_w if sw_ is None else (min(sw_, s_w) if dv_ > 0 else max(sw_, s_w))
        se_ = s_e if se_ is None else (max(se_, s_e) if dv_ > 0 else min(se_, s_e))
    if sw_ is None: continue
    pc_ = Bm_.intersection(_half(F, sw_, dv_ > 0))
    if pc_.is_empty or pc_.area < 1e4: continue
    zc_ = []                                                                  # 柱の幅の上の梁の下端（いちばん高い所で柱を切り、上は梁の外形の重なり）
    for sq_ in np.linspace(min(sw_, se_), max(sw_, se_), 25):
        x_ = Bm_.intersection(LineString([(sq_, op_.bounds[1]), (sq_, op_.bounds[3] + 500.0)]))
        if not x_.is_empty: zc_.append(x_.bounds[1])
    if not zc_: continue
    zb_ = max(zc_) + 1.0
    new_ = unary_union([op_.intersection(Polygon([(-1e5, -1e5), (1e5, -1e5), (1e5, zb_), (-1e5, zb_)])), pc_]).buffer(0.2, join_style=2).buffer(-0.2, join_style=2)
    if new_.geom_type != 'Polygon': log.append(f'  !! 東の柱の頭が二つに分かれた（u{w[5]:.2f}）、そのまま'); continue
    e_ = _rebuild_sz(g, F, new_)
    if e_ is not None: _wset(w, e_); _g3['head'] += 1
# d. 柱の輪郭の細い突起・波
for w in _W3:
    if w[2] != L22A or w[3]: continue
    g = w[4]; F = _frame_of(g); op_ = _poly_sz(g, F)
    cl_ = op_.buffer(-10.0, join_style=2).buffer(10.0, join_style=2).buffer(10.0, join_style=2).buffer(-10.0, join_style=2)
    if op_.symmetric_difference(cl_).area < 300.0: cl_ = op_                  # 10-29 夕：変わらない柱も折れ線の輪郭に作り直す（短い辺・ほぼまっすぐな点を除く。退化三角形）
    e_ = _rebuild_sz(g, F, cl_)
    if e_ is not None: _wset(w, e_); _g3['clean'] += 1
# b2. 柱の受け材（b で決めた高さ。c・d で柱の輪郭を作り直した後の輪郭で）
for w, pads_ in _PADS:
    g = w[4]; F = _frame_of(g); op_ = _poly_sz(g, F)
    sc_ = (op_.bounds[0] + op_.bounds[2]) / 2.0; add_ = []
    for vt_, z0_, z1_ in pads_:
        st_ = _s_of_v(F, vt_, sc_)
        add_.append(Polygon([(min(sc_, st_), z0_), (max(sc_, st_), z0_), (max(sc_, st_), z1_), (min(sc_, st_), z1_)]))
    # 10-29 夕（監修の項 1530：柱の外の面に足した所に退化三角形）：柱の輪郭に足さず、柱の外の面から壁の内面の線までの別の箱（受け材、22a、柱と同じ厚み）に
    for pg_ in [unary_union(add_)]:                                          # 2 枚の床梁で同じ高さが二度来るので、まとめてから
        pz_ = pg_.difference(op_.buffer(0.01))
        for q_ in getattr(pz_, 'geoms', [pz_]):
            if q_.geom_type != 'Polygon' or q_.area < 100.0: continue
            bx_ = q_.buffer(-0.05, join_style=2)                                 # 柱の面からわずかに離す（重ならない）
            ep_ = r.Extrusion()
            if not (ep_.SetPathAndUp(g.PathStart, g.PathEnd, g.GetProfilePlane(0.0).YAxis) and
                    ep_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in _sz2l(F, np.asarray(_clean_poly(bx_.simplify(0.3)).exterior.coords))]).ToNurbsCurve(), True)): continue
            at_ = r.ObjectAttributes(); at_.LayerIndex = L22A; at_.Name = '柱の受け材（窓台・まぐさ・床梁の端が当たる所、柱の外の面から外壁の内面の線まで、柱と同じ厚み）'
            _XNEW.append((ep_, at_)); _g3['pad'] += 1
# e. 出し梁の付く梁の西の端の上の角（10-29 夕、監修の項 1530：一つの架構の 2 枚は、片方だけに出し梁が付く端の架構（u21.33・u48）でも 2 枚とも直角に。
#    前は出し梁の付く 1 枚だけ直したので 2 枚の輪郭が 81 違った）
U_F18 = 50.565                                                                # 北の端の架構（梁18、10-30 ユーザー、run_exact_new.py で足した。2 枚 u50.39〜50.74）
_FR3 = [21.33] + [24.0 + 3.0 * k for k in range(7)] + [43.5, 45.0, 48.0, U_F18]
_fk3 = lambda u_: min(_FR3, key=lambda f_: abs(f_ - u_))
_sqf = set()
for w in _W3:
    if w[2] != L22B: continue
    g = w[4]; F = _frame_of(g); op_ = _poly_sz(g, F); dv_ = _dv(F)
    sW_ = op_.bounds[0] if dv_ > 0 else op_.bounds[2]; pW_ = F['A'][:2] + F['hw'] * sW_ + F['hm']
    if uv(*pW_)[1] < -5.0 and (not WN.contains(Point(*(pW_ - F['hw'] * dv_ * 400.0))) or w[3] == NAME_RAF): _sqf.add(_fk3(w[5]))
for w in _W3:
    if w[2] != L22B: continue
    g = w[4]; F = _frame_of(g); op_ = _poly_sz(g, F); dv_ = _dv(F)
    sW_ = op_.bounds[0] if dv_ > 0 else op_.bounds[2]
    pW_ = F['A'][:2] + F['hw'] * sW_ + F['hm']
    if uv(*pW_)[1] > -5.0 or _fk3(w[5]) not in _sqf: continue    # 出し梁の付かない架構（下の出し梁と同じ見分け：端の 400 先が建物の中）
    def _top(s):                                                              # その s の梁の上端
        x_ = op_.intersection(LineString([(s, op_.bounds[1] - 10.0), (s, op_.bounds[3] + 10.0)]))
        return None if x_.is_empty else x_.bounds[3]
    s1_, s2_ = sW_ + dv_ * 450.0, sW_ + dv_ * 900.0; z1_, z2_ = _top(s1_), _top(s2_)
    if z1_ is None or z2_ is None: continue
    zr_ = lambda s: z1_ + (z2_ - z1_) * (s - s1_) / (s2_ - s1_)               # 上端の線（その梁の上端をそのまま延ばす。2 枚は同じ形）
    cr_ = Polygon([(sW_, zr_(sW_) - 260.0), (s1_, zr_(s1_) - 260.0), (s1_, zr_(s1_)), (sW_, zr_(sW_))])     # 出し梁のせい 240 の所まで
    new_ = unary_union([op_, cr_])
    if new_.area - op_.area < 50.0: continue
    e_ = _rebuild_sz(g, F, new_)
    if e_ is not None: _wset(w, e_); _g3['sq'] += 1
# f. 桁の端が板の厚みの中で止まっている所（斜めの桁を板の面で止めた端の小口の角が板に入り、板に浅い穴ができていた：u44.87 の穴の縁 25、
#    監修の項 1530）は、板（外形）に触れるまで縮め、その板の穴を作り直す
_n_gf = 0; _fixp = set()
for gi in ([] if TAMEDIA else _GIR):                                       # 10-31：Tamedia の留めでは桁の端は柱の頭の中心・外の板の外面（縮めない）
    for end in (0, 1):
        g = gi[1]; A, B = _path(g); E, F_ = (A, B) if end == 0 else (B, A); ed = (F_ - E) / np.linalg.norm(F_ - E)
        for w in _WOOD:
            if w[2] not in (L22B, L22C) or '出し梁' in w[3]: continue
            if (id(gi), end) in _GCOL: continue                                   # 柱で受ける端（板の穴を通る）はそのまま（10-29 夜）
            Aw, Bw = _path(w[4]); Lw = np.linalg.norm(Bw - Aw); pw = (Bw - Aw) / Lw
            if abs((E - Aw) @ pw - Lw / 2) > Lw / 2 + 150.0 or abs(ed @ pw) < 0.3: continue
            oo_ = _outer_only(w[4]); Mw_ = _tm_mf(_ext_tm(oo_)) if oo_ is not None else None
            if Mw_ is None: continue
            def _ovw(lam):
                e_ = extedit.edit(g, None, (lambda A_, B_: (A_ + ed * lam, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + ed * lam)))
                M_ = _tm_mf(_ext_tm(e_)) if e_ is not None else None
                return 1e12 if M_ is None else (M_ ^ Mw_).volume()
            v0_ = _ovw(0.0)
            if not (10.0 < v0_ < 3e6): continue                                  # 触れていない・通り抜ける桁はそのまま
            lo_, hi_ = 0.0, 400.0
            if _ovw(hi_) > 10.0: continue
            for _ in range(16):
                mid_ = (lo_ + hi_) / 2
                if _ovw(mid_) > 10.0: lo_ = mid_
                else: hi_ = mid_
            e_ = extedit.edit(g, None, (lambda A_, B_: (A_ + ed * hi_, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + ed * hi_)))
            if e_ is None: continue
            gi[1] = e_; EXT[gi[0]] = e_; g = e_; _n_gf += 1; _fixp.add(id(w))
# f2. 柱で受ける桁の端（2c）が、そのあと柱の外の面を壁の内面の線へ削ったので離れた所（u21.33 の西の柱、10〜12）：柱に触れるまで延ばす（10-29 夜）
_n_gc2 = 0
for gi in _GIR:
    for end in (0, 1):
        if (id(gi), end) not in _GCOL: continue
        g = gi[1]; A, B = _path(g); E, F_ = (A, B) if end == 0 else (B, A); ed = (F_ - E) / np.linalg.norm(F_ - E); uE = uv(E[0], E[1])[0]
        MC_ = []
        for w in _WOOD:
            if w[2] != L22A or abs(w[5] - uE) > 0.6: continue
            oo_ = _outer_only(w[4]); M_ = _tm_mf(_ext_tm(oo_)) if oo_ is not None else None
            if M_ is None: continue
            bb_ = np.array(M_.bounding_box())
            if np.all(bb_[:3] - 600.0 <= E) and np.all(E <= bb_[3:] + 600.0): MC_.append(M_)
        if not MC_: continue
        def _ovc(lam):
            e_ = extedit.edit(g, None, (lambda A_, B_: (A_ + ed * lam, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + ed * lam)))
            M_ = _tm_mf(_ext_tm(e_)) if e_ is not None else None
            return 1e12 if M_ is None else sum((M_ ^ Mc_).volume() for Mc_ in MC_)
        if _ovc(-3.0) > 1.0 or _ovc(-400.0) <= 10.0: continue
        lo_, hi_ = 0.0, -400.0
        for _ in range(14):
            mid_ = (lo_ + hi_) / 2
            if _ovc(mid_) > 10.0: hi_ = mid_
            else: lo_ = mid_
        e_ = extedit.edit(g, None, (lambda A_, B_: (A_ + ed * lo_, B_)) if end == 0 else (lambda A_, B_: (A_, B_ + ed * lo_)))
        if e_ is None: continue
        gi[1] = e_; EXT[gi[0]] = e_; _n_gc2 += 1
        for w in _WOOD:
            if w[2] in (L22B, L22C) and abs(w[5] - uE) < 0.6: _fixp.add(id(w))
log.append(f'西館：柱の外の面を削ったあと離れた桁の端 {_n_gc2} を柱に触れるまで延ばした')
# f3. 柱の端の角に斜めに来る桁（u21.33 の西の柱、柱の外の面が外壁の内面の線で止まり、桁の端の半分が柱の外に出る）：柱の外に出た桁の下に
#     受け材（柱と同じ厚み、せい 120、柱の端の面から桁の端の先 20 まで。上の面は桁の下の面）を足し、桁の端を載せる（10-29 夜、項 2027 の 2）
_n_pad2 = 0
for gi in _GIR:
    for end in (0, 1):
        if (id(gi), end) not in _GCOL: continue
        g = gi[1]; A, B = _path(g); E = A if end == 0 else B; uE = uv(E[0], E[1])[0]
        T_ = tri.tri_extrusion(g)
        if not len(T_): continue
        tmg_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tmg_.merge_vertices()
        for w in _WOOD:
            if w[2] != L22A or abs(w[5] - uE) > 0.6 or w[3]: continue
            gc_ = w[4]; Ac_, Bc_ = _path(gc_); Lc_ = np.linalg.norm(Bc_ - Ac_); pc_ = (Bc_ - Ac_) / Lc_
            tE_ = (E - Ac_) @ pc_
            if tE_ < -300.0 or tE_ > Lc_ + 300.0: continue
            Fc_ = _frame_of(gc_); opc_ = _poly_sz(gc_, Fc_)
            Xc_ = _v3(gc_.GetProfilePlane(0.0).XAxis); Yc_ = _v3(gc_.GetProfilePlane(0.0).YAxis)
            Sec_ = []
            for tq_ in (2.0, Lc_ - 2.0):
                sc_ = tmg_.section(plane_origin=Ac_ + pc_ * tq_, plane_normal=pc_)
                if sc_ is None: continue
                for lp_ in sc_.discrete:
                    if len(lp_) >= 3: Sec_.append(Polygon(_l2sz(Fc_, np.c_[(lp_ - Ac_) @ Xc_, (lp_ - Ac_) @ Yc_])).buffer(0))
            if not Sec_: continue
            sec_ = unary_union(Sec_)
            out_ = sec_.difference(opc_.buffer(1.0))
            if out_.area < 2000.0: continue                                      # 桁の端は柱の面の中に収まる
            if sec_.intersection(opc_).area < 100.0 and sec_.distance(opc_) > 30.0: continue
            zb_ = sec_.bounds[1]; b_ = out_.bounds                                # 桁の下の面のいちばん低い所（丸い断面の下の点）に平らな上の面で触れる
            pad_ = Polygon([(b_[0] - 200.0, zb_ - 120.0), (b_[2] + 20.0, zb_ - 120.0), (b_[2] + 20.0, zb_ - 0.05), (b_[0] - 200.0, zb_ - 0.05)]).difference(opc_.buffer(0.05)).difference(sec_.buffer(0.05))
            pad_ = max(getattr(pad_, 'geoms', [pad_]), key=lambda q: q.area) if not pad_.is_empty else pad_
            if pad_.is_empty or pad_.distance(opc_) > 0.2: continue                     # 柱の端の面に付く所だけ（柱の頭より上の桁には要らない）
            if pad_.is_empty or pad_.area < 2000.0: continue
            ep_ = r.Extrusion()
            if not (ep_.SetPathAndUp(gc_.PathStart, gc_.PathEnd, gc_.GetProfilePlane(0.0).YAxis) and
                    ep_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in _sz2l(Fc_, np.asarray(_clean_poly(pad_.simplify(0.3)).exterior.coords))]).ToNurbsCurve(), True)): continue
            at_ = r.ObjectAttributes(); at_.LayerIndex = L22A; at_.Name = '柱の受け材（斜めの桁の端が柱の端の角に来る所、桁の下、柱と同じ厚み、せい 120）'
            _XNEW.append((ep_, at_)); _n_pad2 += 1
log.append(f'西館：柱の端の角に来る斜めの桁の端の下に受け材 {_n_pad2} 個')
# f4. 柱の面に斜めに当たる桁の木口（10-29 夜、ユーザー）：桁は押し出しのまま木口をまっすぐ切り、木口と柱の面（＝梁の板の内の面）のあいだの斜めの
#     すき間に楔形の受け材（平らな面だけの三角柱の押し出し、22a、柱の受け材）を足す。桁の断面は楕円なので斜めの切り口は押し出しにできない（網目は残さない）。
#     楔の断面は桁の軸と幅（水平）の面の三角形、桁の上下の向き（断面の Y）に桁のせい 400 押し出す
_n_wedge = 0; _WTM = []
for gi in _GIR:
    for end in (0, 1):
        if (id(gi), end) not in _GCOL: continue
        g = gi[1]; A, B = _path(g); E, F_ = (A, B) if end == 0 else (B, A); ed = (F_ - E) / np.linalg.norm(F_ - E); uE = uv(E[0], E[1])[0]
        best_ = None
        for w in _WOOD:
            if w[2] != L22A or abs(w[5] - uE) > 0.6 or w[3]: continue
            Ac_, Bc_ = _path(w[4]); pc_ = (Bc_ - Ac_) / np.linalg.norm(Bc_ - Ac_)
            op_ = _poly_sz(w[4]); F3_ = _frame_of(w[4]); sE_ = float(_w2s(F3_, E[None, :2] - F3_['hm'])[0])
            if not (op_.bounds[0] - 300.0 < sE_ < op_.bounds[2] + 300.0 and op_.bounds[1] - 300.0 < E[2] < op_.bounds[3] + 300.0): continue
            for P0_ in (Ac_, Bc_):
                dd_ = abs(float((E - P0_) @ pc_))
                if dd_ < 150.0 and (best_ is None or dd_ < best_[0]): best_ = (dd_, P0_, pc_, w)
        if best_ is None: continue
        _, P0_, pc_, best_w_ = best_; c_ = abs(float(ed @ pc_))
        if c_ > 0.985 or c_ < 0.2: continue                                     # 直角に当たる桁はそのまま
        n_ = pc_ if float(ed @ pc_) > 0 else -pc_                                 # 桁の側を向く
        pl_ = g.GetProfilePlane(0.0); Xg_ = _v3(pl_.XAxis); Yg_ = _v3(pl_.YAxis)
        if abs(Xg_[2]) > abs(Yg_[2]): Xg_, Yg_ = Yg_, Xg_                         # Xg：幅（水平に近い）、Yg：せい
        Xg_ = Xg_ - ed * (Xg_ @ ed); Xg_ /= np.linalg.norm(Xg_); Yg_ = np.cross(ed, Xg_); Yg_ /= np.linalg.norm(Yg_)
        # 楔の平面形：桁の幅の帯（±100）の中で、木口の外・柱の面の桁の側・柱のある所（その高さの柱の輪郭の s の範囲）
        Fc3_ = _frame_of(best_w_[4]); opc3_ = _poly_sz(best_w_[4], Fc3_)
        hz_ = opc3_.intersection(LineString([(opc3_.bounds[0] - 10.0, E[2]), (opc3_.bounds[2] + 10.0, E[2])]))
        if hz_.is_empty: continue
        s0_, s1_ = hz_.bounds[0], hz_.bounds[2]
        # 楔は柱の面と木口の面の交わる線の向き dir_ に押し出す三角柱（両方の面に平らに付く、傾いた桁でも）。断面は dir_ に直角な面の上で
        dir_ = np.cross(n_, ed); dir_ /= np.linalg.norm(dir_)
        if dir_[2] < 0: dir_ = -dir_
        b1_ = ed - dir_ * (ed @ dir_); b1_ /= np.linalg.norm(b1_); b2_ = np.cross(dir_, b1_)
        Bg_ = 1.0e5
        reg_ = Polygon([(0.0, -100.0), (0.0, 100.0), (-Bg_, 100.0), (-Bg_, -100.0)])                     # 木口の外（幅の帯）
        na_, nb_ = float(n_ @ b1_), float(n_ @ b2_); c0_ = float(n_ @ (E - P0_))                  # 柱の面：c0 + na x1 + nb x2 ≥ 0
        hw3_ = Fc3_['hw']; O3_ = Fc3_['A'][:2] + Fc3_['hm']
        sa_, sb_ = float(hw3_ @ b1_[:2]), float(hw3_ @ b2_[:2]); sc_ = float(hw3_ @ (E[:2] - O3_))   # s ＝ sc + sa x1 + sb x2
        def _half(a_, b_, c_):                                                   # a x1 + b x2 + c ≥ 0 の半平面（大きな多角形）
            nn_ = np.array([a_, b_]); L_ = np.linalg.norm(nn_); nn_ /= L_; p0_ = -nn_ * c_ / L_; t_ = np.array([-nn_[1], nn_[0]])
            return Polygon([p0_ + t_ * Bg_, p0_ - t_ * Bg_, p0_ - t_ * Bg_ + nn_ * Bg_, p0_ + t_ * Bg_ + nn_ * Bg_])
        reg_ = reg_.intersection(_half(na_, nb_, c0_)).intersection(_half(sa_, sb_, sc_ - s0_)).intersection(_half(-sa_, -sb_, s1_ - sc_))
        reg_ = max(getattr(reg_, 'geoms', [reg_]), key=lambda q: q.area) if not reg_.is_empty else reg_
        if reg_.is_empty or reg_.area < 300.0: continue
        hh_ = 400.0
        tri_ = [E + b1_ * x1_ + b2_ * x2_ - dir_ * hh_ / 2 for x1_, x2_ in np.asarray(_clean_poly(reg_.simplify(0.3)).exterior.coords)[:-1]]
        crv = r.Polyline([r.Point3d(*map(float, c)) for c in tri_ + [tri_[0]]]).ToNurbsCurve(); bw_ = None
        for ex_ in (r.Extrusion.Create(crv, hh_, True), r.Extrusion.Create(crv, -hh_, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm = abs((bb_.Min.Z + bb_.Max.Z) / 2 - E[2])
            if bw_ is None or dm < bw_[0]: bw_ = (dm, ex_)
        if bw_ is None: continue
        at_ = r.ObjectAttributes(); at_.LayerIndex = L22A; at_.Name = '柱の受け材（楔、斜めの桁の木口と柱の面のすき間、平らな面だけ）'
        _XNEW.append((bw_[1], at_)); _n_wedge += 1; _WTM.append(_ext_tm(bw_[1]))
if _WTM:                                                                          # 楔は板の穴の中：穴を楔の分も（全周 10）。あとの作り直しでも楔を含める
    _GTM = _GTM + _WTM
    for w in _WOOD:
        if w[2] not in (L22B, L22C) or '出し梁' in w[3]: continue
        bb_ = np.array([w[4].GetBoundingBox().Min.X, w[4].GetBoundingBox().Min.Y, w[4].GetBoundingBox().Min.Z, w[4].GetBoundingBox().Max.X, w[4].GetBoundingBox().Max.Y, w[4].GetBoundingBox().Max.Z])
        if not any(np.all(t_.bounds[0] <= bb_[3:] + 5.0) and np.all(bb_[:3] - 5.0 <= t_.bounds[1]) for t_ in _WTM): continue
        e_, _a, _b, _c = _rebuild_holes(w[4], False, bear=(w[3] == NAME_RAF))
        if e_ is not None: _wset(w, e_)
        # 楔が板の縁にかかる所（穴にならない）は、板の外形を楔＋10 で欠く
        Fw_ = _frame_of(w[4]); opw_ = _poly_sz(w[4], Fw_); Aw_, Bw_ = _path(w[4]); pw_ = (Bw_ - Aw_) / np.linalg.norm(Bw_ - Aw_)
        Xw_ = _v3(w[4].GetProfilePlane(0.0).XAxis); Yw_ = _v3(w[4].GetProfilePlane(0.0).YAxis); Lw_ = np.linalg.norm(Bw_ - Aw_); sc_ = []
        for t_ in _WTM:
            for f_ in np.linspace(0.5, Lw_ - 0.5, 5):
                x_ = t_.section(plane_origin=Aw_ + pw_ * f_, plane_normal=pw_)
                if x_ is None: continue
                for lp_ in x_.discrete:
                    if len(lp_) >= 3: sc_.append(Polygon(_l2sz(Fw_, np.c_[(lp_ - Aw_) @ Xw_, (lp_ - Aw_) @ Yw_])).buffer(0))
        Hn_ = unary_union(sc_).buffer(10.0) if sc_ else None
        if Hn_ is not None and not Hn_.is_empty and Hn_.intersects(opw_) and not opw_.buffer(-3.0).contains(Hn_):
            e3_ = _rebuild_sz(w[4], Fw_, opw_.difference(Hn_))
            if e3_ is not None:
                _wset(w, e3_); e4_, _a, _b, _c = _rebuild_holes(w[4], False, bear=(w[3] == NAME_RAF))
                if e4_ is not None: _wset(w, e4_)
log.append(f'西館：柱の面に斜めに当たる桁の木口と柱の面のあいだに楔の受け材 {_n_wedge} 個（板の穴は楔の分も）')
if _fixp:
    _GTM = []
    for gi in _GIR:
        T_ = tri.tri_extrusion(gi[1])
        if len(T_): tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(); _GTM.append(tm_)
    _GTM = _GTM + _WTM                                                         # 楔も穴に（10-29 夜）
    for w in _WOOD:
        if id(w) not in _fixp: continue
        e_, _a, _b, _c = _rebuild_holes(w[4], w[2] == L22A, bear=(w[3] == NAME_RAF))
        if e_ is not None: _wset(w, e_)
log.append(f'西館：板の厚みの中で止まっていた桁の端 {_n_gf} を板に触れる所まで縮め、その板の穴を作り直した')
# 10-31（Tamedia の留め）：柱の外形を作り直した段（頭を切る・3g）は穴を落とすので、最後に柱・板の穴を、いまの桁の断面＋10 でもう一度作る
if TAMEDIA:
    _GTM = []
    for gi in _GIR:
        gq_ = gi[1]                                                          # 端の架構の外の板の穴は、桁の線を 250 延ばした断面で（斜めの桁の小口は板の面に平行でないので、
        for gj_, end_ in _FREE:                                             #   板の厚みの全部に桁の断面が来るように。穴の中心が桁の軸の上に）
            if gj_ is gi:
                A_, B_ = _path(gq_); dq_ = (B_ - A_) / np.linalg.norm(B_ - A_)
                gq_ = extedit.edit(gq_, None, (lambda A2, B2: (A2 - dq_ * 250.0, B2)) if end_ == 0 else (lambda A2, B2: (A2, B2 + dq_ * 250.0))) or gq_
        T_ = tri.tri_extrusion(gq_)
        if len(T_): tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(); _GTM.append(tm_)
    _GTM_V = _GTM; _GTM = []                                                  # 延ばした線（板の穴だけ）・本物（柱の穴）
    for gi in _GIR:
        T_ = tri.tri_extrusion(gi[1])
        if len(T_): tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(); _GTM.append(tm_)
    _GTM_R = _GTM
    _n_tc = _n_tn = 0; _NOTCH = []
    for w in _WOOD:
        if w[3] and w[3] != NAME_RAF: continue                                  # 受け材・楔・腕木などは除く（架構の柱・板と u43.5 の梁だけ）
        if '出し梁' in w[3] or '登り梁' in w[3]: continue
        _GTM = _GTM_R if w[2] == L22A else _GTM_V
        e_, a_, b_, c_ = _rebuild_holes(w[4], w[2] == L22A, bear=(w[3] == NAME_RAF))
        if e_ is not None and c_ and w[2] != L22A:                          # 延ばした線で縁にかかる板は本物の桁で
            _GTM = _GTM_R; e_, a_, b_, c_ = _rebuild_holes(w[4], False, bear=(w[3] == NAME_RAF))
        _GTM = _GTM_R
        if e_ is None: continue
        _wset(w, e_)
        if w[2] == L22A and c_:
            # 柱の頭の幅に二本の桁の折れ目の穴が収まらない（u48 の西の柱：柱の頭が細くなる所）：穴＋木 20 を包むように柱の頭を局所的に太らせる
            #   （柱の輪郭の、足もとから頭までの s の幅（外の面＝外壁の内面）の中だけ）
            Fc_ = _frame_of(w[4]); opc_ = _poly_sz(w[4], Fc_); Ac_, Bc_ = _path(w[4]); Lc_ = np.linalg.norm(Bc_ - Ac_); pc_ = (Bc_ - Ac_) / Lc_
            sc2_ = []
            for tm_ in _GTM:
                for f_ in np.linspace(0.5, Lc_ - 0.5, 5):
                    x_ = tm_.section(plane_origin=Ac_ + pc_ * f_, plane_normal=pc_)
                    if x_ is None: continue
                    for lp_ in x_.discrete:
                        if len(lp_) >= 3:
                            q_ = Polygon(np.c_[_w2s(Fc_, lp_), lp_[:, 2]]).buffer(0)
                            if q_.area > 500.0 and q_.intersects(opc_): sc2_.append(q_)
            if sc2_:
                Hc_ = unary_union(sc2_).buffer(10.0)
                sw_ = opc_.bounds[0] if _dv(Fc_) > 0 else opc_.bounds[2]          # 外壁の側（v の小さい側）の外の面の線は越えない。内の側は太らせてよい
                lim_ = Polygon([(sw_, -1e5), (sw_ + 1e5 * _dv(Fc_), -1e5), (sw_ + 1e5 * _dv(Fc_), 1e5), (sw_, 1e5)]).buffer(0)
                wrap_ = unary_union([opc_.intersection(Hc_.buffer(300.0).envelope), Hc_.buffer(20.0)]).convex_hull.intersection(lim_)
                e3_ = _rebuild_sz(w[4], Fc_, unary_union([opc_, wrap_]))
                if e3_ is not None:
                    _wset(w, e3_); e_, a_, b_, c_ = _rebuild_holes(w[4], True)
                    if e_ is not None: _wset(w, e_)
                    _NOTCH.append(f'(太らせた u{w[5]:.2f})')
        if w[2] == L22A and b_: _n_tc += 1
        if c_: _NOTCH.append(f'{m.Layers[w[2]].Name[:3]} u{w[5]:.2f}')
    log.append(f'西館：Tamedia の留め：桁が穴を通る架構の柱 {_n_tc} 本。桁が材の縁にかかる（穴にできない）所 {len(_NOTCH)}：{" ".join(_NOTCH)}')
log.append(f'西館：端の納まり（3g）：2 階の床梁の西の端を外壁の内面で {_g3["trim"]}、柱の外の面を端の高さだけ壁の内面の線へ {_g3["pad"]}、'
           f'東の柱の頭を梁の東の端の丸みまで {_g3["head"]}、柱の輪郭の細い突起を除く {_g3["clean"]}、出し梁の付く梁の西の端の上の角を直角に {_g3["sq"]}')

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
SL_U = [3.0 * k for k in range(1, 19)]; SL_V = (1.76, 13.6); SL_GL = 13.5; SL_HALF = 0.09   # 10-29（ユーザー、監修の項 20261029-0018）：筋の東の端は外皮の線 v13.6 の立ち上がり（前は軒先 v15.0）、軒は屋根を切らずに一枚
ROOF_Z = lambda v: 4150.0 - v * 1000.0 / 12.0
# 10-26夜（ユーザー、決定事項（共通）の「屋根の構成」、監修の項 20261026-1936）：屋根に厚み。下面＝梁の上端（＝垂木の下、元の面の 150 下）、
# 上面＝その 420 上（元の面の 270 上）。構成：太陽光 約40／野地板／通気層 45／透湿防水／木質繊維 t150（外張り）／気密／構造用合板 t24（現し）／垂木 60×150。
# 元の面より上にあった物（光の筋のガラス・立ち上がり・太陽光・越屋根の蓋・ルーバー・LED・外壁と越屋根の立ち上がりの上端）は 270 上げる。
RT_BOT, RT_TOP = -150.0, -41.0      # 10-27夜：梁の上端（RT_BOT）の上は通気垂木・野地・屋根材の約 110 だけ（断熱は梁のあいだ）
# 10-27夜（ユーザー：曲線が見られるのは架構のみ。壁・ガラス・屋根の板は必ず平面で、断面は長方形を面に直角に押し出した形（妻の三角形は別））：
# 屋根の面はスパンごとの平面（架構の線 u=3k と 3k+3 の弦の上）。前は v だけで高さを決めた円錐の面を細かく三角形にしていた。
# 架構の線をまたぐ小さな物（光の筋のガラス・立ち上がり・鋼の平板）は、その架構の線の接線の平面。どちらも架構の線の上では元の高さと 0.1 mm 以内で一致する。
from shapely.geometry.polygon import orient as _orient
def _k_of(u): return int(min(18, max(0, math.floor(u / 3.0))))
_PL = {}
def _plane(key):
    if key not in _PL:
        if key[0] == 's':
            A_ = xy(3.0 * key[1], 0.0); B_ = xy(3.0 * (key[1] + 1), 0.0); c_ = (B_ - A_) / np.linalg.norm(B_ - A_)
        else:
            A_ = xy(3.0 * key[1], 0.0); c_ = xy(3.0 * key[1] + 0.001, 0.0) - A_; c_ /= np.linalg.norm(c_)
        h_ = np.array([c_[1], -c_[0]])
        if np.dot(h_, xy(3.0 * key[1], 1.0) - A_) < 0: h_ = -h_                 # h は v の増える向き（東、下り）
        n_ = np.array([h_[0] / 12.0, h_[1] / 12.0, 1.0]); n_ /= np.linalg.norm(n_)
        _PL[key] = (A_, c_, h_, n_)
    return _PL[key]
def zpl(key, x, y):
    A_, c_, h_, n_ = _plane(key)
    return ROOF_Z(((x - A_[0]) * h_[0] + (y - A_[1]) * h_[1]) / 1000.0)
def xyk(key, u, v):
    """(u, v) をその平面の多角形の上の点に：スパンは弦、架構の線は接線（曲がらない）"""
    if key[0] == 's':
        k_ = key[1]; f_ = (u - 3.0 * k_) / 3.0
        return xy(3.0 * k_, v) * (1.0 - f_) + xy(3.0 * (k_ + 1), v) * f_
    j_ = key[1]; b_ = xy(3.0 * j_, v); t_ = xy(3.0 * j_ + 0.001, v) - b_; t_ /= np.linalg.norm(t_)
    return b_ + (u - 3.0 * j_) * 1000.0 * (RW - v * 1000.0) / RW * t_
def key_for(p):
    cu = uv(p.centroid.x, p.centroid.y)[0]; j_ = int(round(cu / 3.0))
    if 0 <= j_ <= 19 and abs(cu - 3.0 * j_) < 0.3: return ('f', j_)
    return ('s', _k_of(cu))
def straight(key, p):
    def m_(ring): return [tuple(xyk(key, *uv(x, y))) for x, y in np.asarray(ring.coords)]
    q = Polygon(m_(p.exterior), [m_(h) for h in p.interiors]).buffer(0)
    return q.simplify(0.5) if q.geom_type == 'Polygon' else max(getattr(q, 'geoms', [q]), key=lambda g_: g_.area).simplify(0.5)
def zuv(x, y): return ROOF_Z(uv(x, y)[1])
def _rdz(dz, x, y): return dz(*uv(x, y)) if callable(dz) else dz      # 10-27夜：屋根の面からの高さは (u, v) の関数でもよい（軒の細らせ）
_SPAN_STRIPS = None
def _by_span(poly):
    """10-27夜（監修の項 20261027-2020 の 3）：架構の線（u = 3k）でスパンごとに切る（屋根の面はスパンごとの平面）"""
    global _SPAN_STRIPS
    if _SPAN_STRIPS is None:
        _SPAN_STRIPS = [R(3.0 * k, 3.0 * (k + 1), -6.0, 17.0, 0.25) for k in range(-3, 21)]
    ps = [poly] if poly.geom_type == 'Polygon' else list(getattr(poly, 'geoms', []))
    out = []
    for p in ps:
        if p.geom_type != 'Polygon' or p.area < 1e3: continue
        for st in _SPAN_STRIPS:
            if not st.intersects(p): continue
            q = p.intersection(st)
            for g_ in ([q] if q.geom_type == 'Polygon' else [x for x in getattr(q, 'geoms', []) if x.geom_type == 'Polygon']):
                if g_.area >= 1e3: out.append(g_)
    return out
def _plate(p, key, dz0, dz1, vert=False):
    """平面形 p（その平面の多角形の上、穴あり可）を、屋根の面から dz0〜dz1 の閉じた板に。
    ふつうは屋根の面に直角に押し出す（下の面を屋根の面から dz0（鉛直に測る）の平面に置き、法線の向きに）。
    vert=True は鉛直の板（平面形が細く、面が鉛直：外皮の線の固定ガラスなど）：上下の縁は水平、横は鉛直。"""
    A_, c_, h_, n_ = _plane(key); p = _orient(p, 1.0)
    rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(hh.coords)[:-1] for hh in p.interiors]
    V2 = np.vstack(rings); n = len(V2); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
    tri_ = _ec.triangulate_float64(V2, ends).reshape(-1, 3)
    mm = r.Mesh()
    if vert:
        cz = zpl(key, *V2.mean(0))
        for dz in (dz0, dz1):
            for x, y in V2: mm.Vertices.Add(float(x), float(y), float(cz + dz))
    else:
        t_ = (dz1 - dz0) * n_[2]
        for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zpl(key, x, y) + dz0))
        for x, y in V2:
            z0_ = zpl(key, x, y) + dz0
            mm.Vertices.Add(float(x + t_ * n_[0]), float(y + t_ * n_[1]), float(z0_ + t_ * n_[2]))
    for a, b, c in tri_: mm.Faces.AddFace(int(a), int(c), int(b)); mm.Faces.AddFace(int(a + n), int(b + n), int(c + n))
    st = 0
    for e in ends:
        for i in range(st, int(e)):
            j = i + 1 if i + 1 < e else st; mm.Faces.AddFace(i, j, j + n, i + n)
        st = int(e)
    mm.Normals.ComputeNormals(); mm.Compact()
    return mm
def sheet(poly, dz, li, col=None, mat=None):
    """平面形（穴あり可）を屋根の面から dz 上に、屋根と平行な面で（スパンごとの平面）"""
    ms = []
    for p in _by_span(poly):
        key = ('s', _k_of(uv(p.centroid.x, p.centroid.y)[0])); p = straight(key, p)
        rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
        V2 = np.vstack(rings); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri_ = _ec.triangulate_float64(V2, ends).reshape(-1, 3)
        mm = r.Mesh()
        for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zpl(key, x, y) + dz))
        for a, b, c in tri_: mm.Faces.AddFace(int(a), int(b), int(c))
        mm.Normals.ComputeNormals(); mm.Compact(); ms.append(mm)
    return ms
def slab(poly, dz0, dz1, vert=False):
    """屋根の面から dz0〜dz1 の板（架構の線の上の物はその接線の平面、ほかはスパンの平面。切らない）"""
    out_ = []
    for p in ([poly] if poly.geom_type == 'Polygon' else list(poly.geoms)):
        key = key_for(p); out_.append(_plate(straight(key, p), key, dz0, dz1, vert))
    return out_
def thick(poly, dz0, dz1):
    """平面形（穴あり可）をスパンごとに切り、屋根の面から dz0〜dz1 の閉じた板に（屋根の面に直角に押し出す）"""
    out_ = []
    for p in _by_span(poly):
        key = ('s', _k_of(uv(p.centroid.x, p.centroid.y)[0])); out_.append(_plate(straight(key, p), key, dz0, dz1))
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
    MON_OPEN = R(-1.0, 58.5, -1.0, 1.66, 0.2)          # 越屋根の下（西吹き抜けの上、v 1.66 の東の立ち上がりまで）は屋根を開ける（前は面が残っていた）
    # 10-27 夜（ユーザー：屋根の構成を組み直す。断熱を梁のあいだに収め、梁の上に載るのは薄い層だけ。軒は細く。西館も同じに）：
    #   登り梁（2 枚組、3 mおき）のあいだに、母屋 杉 60×150 @455 を桁の方向に渡し（両端は梁の側面の金物）、その上に構造用合板 t24（室内に現す天井）、
    #   気密シート、断熱（硬い木質繊維ボード）t150 を梁のあいだに一枚で（上面＝梁の上端）。梁と断熱の上に、通気垂木 45（勾配の方向、長ビスで母屋へ）・
    #   野地 t24・屋根材と太陽光 40、計約 110（RT_BOT〜RT_TOP）。屋根の重さは断熱を圧して母屋へ伝える。
    #   外皮の線（縁側の杉の壁の外面 v13.6）より東の軒は、同じ上の層が梁の上を軒先まで延び、通気垂木を細らせて軒先の見付け約 64。
    #   軒の下は梁のあいだに母屋を落とし込み（上端＝梁の上端）。屋根の面は段の無い一枚（軒の上でわずかに勾配が強まる）。
    #   レイヤー：上の層と断熱＝10、合板＝10r、母屋＝10v（素材が別、監修の項 20261027-1700）。
    VE, V_TIP, EAVE_TIP = 13.6, 15.0, 64.0
    INS_BOT = RT_BOT - 150.0; PLY_BOT = INS_BOT - 24.0; PUR_BOT = PLY_BOT - 150.0
    # 南の軒（u −4.2〜0）：外なので上の層だけ。軒先に向けて細らせ、軒先の見付け約 64（東と同じ）。
    EAVE, EAVE_AT = None, None
    for o in m.Objects:
        g = o.Geometry
        if o.Attributes.LayerIndex != L10 or not isinstance(g, r.Mesh) or str(o.Attributes.Id) in drop: continue
        u0_, u1_, v0_, v1_, z0_, z1_ = bbox_uv(g)
        if u1_ < 0.05 and u0_ < -3.0:
            EAVE = roof_main_poly(g); EAVE_AT = o.Attributes; drop.add(str(o.Attributes.Id)); break
    def u_edge(v, _c={}):
        k_ = round(v, 2)
        if k_ not in _c:
            uu_ = 0.0
            if EAVE is not None:
                for t_ in np.arange(0.0, -6.0, -0.01):
                    if EAVE.buffer(1.0).contains(Point(*xy(t_, v))): uu_ = t_
            _c[k_] = uu_
        return _c[k_]
    def f_top(u, v):
        tv = min(1.0, max(0.0, (v - VE) / (V_TIP - VE)))
        tu = min(1.0, max(0.0, -u / max(0.3, -u_edge(v)))) if u < 0 else 0.0
        return RT_TOP - (RT_TOP - (RT_BOT + EAVE_TIP)) * max(tv, tu)
    L10R = new_layer('10r_本館_屋根の構造用合板 t24（母屋の上、現し）', (214, 186, 146))
    L10V = new_layer('10v_本館_母屋（杉 60×150 @455、現し）', (196, 160, 118))
    _BIG = lambda u0_, u1_, v0_, v1_: R(u0_, u1_, v0_, v1_, 0.25)
    P_ROOF = RP.difference(SLOTS).difference(MON_OPEN)
    P_IN = P_ROOF.intersection(_BIG(-10.0, 60.0, -3.0, VE))
    P_EAST = P_ROOF.intersection(_BIG(-0.0, 60.0, VE, 16.0))
    BEAMS = unary_union([_BIG(3.0 * k - 0.18, 3.0 * k + 0.18, -3.0, 16.0) for k in range(20)])
    BAYS = P_IN.intersection(_BIG(0.0, 57.19, -3.0, VE)).difference(BEAMS)
    if kind_ == 'new': new_objs.pop(i0)
    else: drop.add(str(at0.Id))
    # 10-27夜（ユーザー：屋根の板は必ず平面、長方形を面に直角に押し出した形。南の軒は屋根の面を一枚のまま）：梁の上の約 110 を
    # 通気垂木 45（10b、60×45 @455、勾配の方向）と、その上の野地＋屋根材 64（10）の板に分ける。屋根の面は折れの無い一枚（スパンごとの平面）。
    # 軒は細らせず、野地＋屋根材の板を通気垂木の先から 150 持ち出して、軒先の見付けを 64 に（東の軒・南の軒とも）。
    at0.Name = '野地 t24＋屋根材と屋根材型の太陽光 40（梁の上、通気垂木の上）'
    for mm in thick(P_ROOF, RT_TOP - EAVE_TIP, RT_TOP): new_objs.append((mm, at0))
    L10B = new_layer('10b_本館_通気垂木（杉 60×45 @455、勾配の方向）', (196, 160, 118))
    def _batten(key, P0, L_, W=60.0):
        A_, c_, h_, n_ = _plane(key)
        q_ = Polygon([P0 - W / 2 * c_, P0 + W / 2 * c_, P0 + W / 2 * c_ + L_ * h_, P0 - W / 2 * c_ + L_ * h_])
        return q_
    _nb = 0
    a_b = r.ObjectAttributes(); a_b.LayerIndex = L10B; a_b.Name = '通気垂木 杉 60×45（勾配の方向、長ビスで母屋へ）'
    for k_ in range(19):
        key = ('s', k_)
        for i_ in range(6):
            ub = 3.0 * k_ + 0.30 + 0.455 * i_
            P0 = xyk(key, ub, SL_V[0] - 0.06)
            q_ = _batten(key, P0, (V_TIP - 0.15 - SL_V[0] + 0.06) * 1000.0).intersection(P_ROOF.buffer(1.0))
            for g_ in ([q_] if q_.geom_type == 'Polygon' else [x for x in getattr(q_, 'geoms', []) if x.geom_type == 'Polygon']):
                if g_.area < 0.02e6: continue
                new_objs.append((_plate(g_.simplify(0.5), key, RT_BOT, RT_TOP - EAVE_TIP), a_b)); _nb += 1
    a_in = r.ObjectAttributes(); a_in.LayerIndex = L10; a_in.Name = '断熱 木質繊維ボード t150（梁のあいだ、上面＝梁の上端）'
    for mm in thick(BAYS, INS_BOT, RT_BOT): new_objs.append((mm, a_in))
    a_r = r.ObjectAttributes(); a_r.LayerIndex = L10R; a_r.Name = '構造用合板 t24（母屋の上、天井に現し、気密はこの上）'
    for mm in thick(BAYS, PLY_BOT, INS_BOT): new_objs.append((mm, a_r))
    if EAVE is not None:
        EAVE_AT.Name = '南の軒：野地 t24＋屋根材と屋根材型の太陽光 40（通気垂木の先から 150 持ち出し、軒先の見付け 64）'
        for mm in thick(EAVE, RT_TOP - EAVE_TIP, RT_TOP): new_objs.append((mm, EAVE_AT))
        key0 = ('s', 0); EAVE_S = straight(key0, EAVE if EAVE.geom_type == 'Polygon' else max(EAVE.geoms, key=lambda g_: g_.area))
        EIN = EAVE_S.buffer(-150.0, join_style=2)
        ub = -0.30
        while ub > -6.0:
            P0 = xyk(key0, ub, -1.0)
            q_ = _batten(key0, P0, 17000.0).intersection(EIN)
            for g_ in ([q_] if q_.geom_type == 'Polygon' else [x for x in getattr(q_, 'geoms', []) if x.geom_type == 'Polygon']):
                if g_.area < 0.02e6: continue
                new_objs.append((_plate(g_.simplify(0.5), key0, RT_BOT, RT_TOP - EAVE_TIP), a_b)); _nb += 1
            ub -= 0.455
    log.append(f'本館：通気垂木 {_nb} 本（10b、60×45 @455、軒先の 150 手前まで）、野地＋屋根材 64 の板は折れの無い一枚（スパンごとの平面）')
    # 南の軒の骨（ユーザー 10-27夜、案 A）：塀（柵＝一本の線 v1.6、乳児の庭の外）の軒先に柱を一本、それより東は鋼の片持ちの骨（黒）で受ける。
    # 骨は約 1.5 mおき、架構 1 の梁の南の面（u −0.18）から軒先の 50 手前まで、上端＝梁の上端（軒の板の下）、せいは根元 200 → 先端 100（H-200×100 を細らせる）。
    # 骨の上の引っぱりは通気層の中の鋼の平板で架構 2 へ返す（3dm には描かない）。軒先の板の中に鋼の縁の材（骨の先をつなぎ、西の端は柱から持ち出す）。
    if EAVE is not None:
        L10S = new_layer('10s_本館_南の軒の鋼の骨と柱（黒）', (40, 40, 42))
        def _box(pts_uv, zf0, zf1):
            # 10-27夜：骨は真っすぐ（スパン 0 の弦と平行）、鉛直に立てる（フランジは水平、ウェブは鉛直の平らな板）
            mm = r.Mesh(); zc_ = zpl(('s', 0), *xyk(('s', 0), pts_uv[0][0], 0.5 * (pts_uv[0][1] + pts_uv[2][1])))
            for zf in (zf0, zf1):
                for (uu_, vv_) in pts_uv:
                    x_, y_ = xyk(('s', 0), uu_, 0.5 * (pts_uv[0][1] + pts_uv[2][1])) + (vv_ - 0.5 * (pts_uv[0][1] + pts_uv[2][1])) * 1000.0 * _plane(('s', 0))[2]
                    mm.Vertices.Add(float(x_), float(y_), float(zc_ + zf(uu_, vv_)))
            n_ = len(pts_uv)
            mm.Faces.AddFace(0, 3, 2, 1); mm.Faces.AddFace(n_, n_ + 1, n_ + 2, n_ + 3)
            for i_ in range(n_):
                j_ = (i_ + 1) % n_; mm.Faces.AddFace(i_, j_, j_ + n_, i_ + n_)
            mm.Normals.ComputeNormals(); mm.Compact(); return mm
        _nrib = 0
        for vc in [0.10] + [round(1.6 + 1.5 * i, 2) for i in range(9)] + [14.90]:
            ue = u_edge(vc) + 0.15; u0r = -0.18            # 10-27夜：通気垂木と同じく軒先の 150 手前まで（軒先は野地＋屋根材 64 だけ）
            if ue > u0r - 0.3: continue
            dep = lambda uu_, vv_, ue=ue: -(200.0 + (100.0 - 200.0) * (uu_ - u0r) / (ue - u0r))
            a_s = r.ObjectAttributes(); a_s.LayerIndex = L10S; a_s.Name = f'南の軒の鋼の骨（片持ち、H-200×100 を細らせる、v {vc:.2f}）'
            for hw_, z0f, z1f in ((0.006, lambda uu_, vv_: RT_BOT + dep(uu_, vv_), lambda uu_, vv_: RT_BOT - 12.0),     # ウェブ
                                  (0.050, lambda uu_, vv_: RT_BOT - 12.0, lambda uu_, vv_: RT_BOT),                     # 上のフランジ
                                  (0.050, lambda uu_, vv_: RT_BOT + dep(uu_, vv_), lambda uu_, vv_: RT_BOT + dep(uu_, vv_) + 12.0)):  # 下のフランジ
                new_objs.append((_box([(u0r, vc - hw_), (ue, vc - hw_), (ue, vc + hw_), (u0r, vc + hw_)], z0f, z1f), a_s))
            _nrib += 1
        # 柱は柵（一本の線）の南の端に立てる（柵と一つの線に。軒先まで出すと避難の帯にかかる）。柵が見つからなければ軒先の 150 内
        _vp, _fu = 1.6, []
        for o in m.Objects:
            if not LN[o.Attributes.LayerIndex].startswith('60_') or not isinstance(o.Geometry, r.Mesh): continue
            for i_ in range(len(o.Geometry.Vertices)):
                q_ = o.Geometry.Vertices[i_]; uu_, vv_ = uv(q_.X, q_.Y)
                if abs(vv_ - _vp) < 0.1 and uu_ < 0: _fu.append(uu_)
        _up = (min(_fu) - 0.05) if _fu else u_edge(1.6) + 0.15
        # 10-30（監修の項 20261030-0552：柱の頭が上の骨から 88 離れていた）：柱の頭は、柱の真上を通る骨（v 1.6）の下のフランジの下面まで。
        # 骨は u0r の点の平面の高さ zc_ に、下へ細る深さ dep を足して作るので、同じ式で測る
        _ue6 = u_edge(_vp) + 0.15; _u0 = -0.18
        _zc6 = zpl(('s', 0), *xyk(('s', 0), _u0, _vp))
        _zt = _zc6 + RT_BOT - (200.0 + (100.0 - 200.0) * (_up - _u0) / (_ue6 - _u0)) if _ue6 <= _u0 - 0.3 else ROOF_Z(_vp) + RT_BOT - 100.0
        a_p = r.ObjectAttributes(); a_p.LayerIndex = L10S; a_p.Name = '南の軒の柱（鋼 角 100、柵＝一本の線の南の端、乳児の庭の外）'
        tmp_ = r.File3dm(); Kt_ = Kit(tmp_); Kt_.prism(R(_up - 0.05, _up + 0.05, _vp - 0.05, _vp + 0.05, 0.05), -300.0, float(_zt), L10S)
        for o2 in tmp_.Objects: new_objs.append((o2.Geometry, a_p))
        log.append(f'本館：南の軒：鋼の片持ちの骨 {_nrib} 本（10s、約 1.5 mおき）と塀の所の柱 1 本（u {_up:.2f}・v {_vp}）、軒先の見付け {EAVE_TIP:.0f}')
    a10 = r.ObjectAttributes(); a10.LayerIndex = L10
    at_g = r.ObjectAttributes(); at_g.LayerIndex = L10T
    if MAT_FROST >= 0: at_g.MaterialSource = r.ObjectMaterialSource.MaterialFromObject; at_g.MaterialIndex = MAT_FROST
    for u in SL_U:
        for mm in slab(R(u - 0.15, u - SL_HALF, SL_V[0] - 0.1, VE, 0.2), RT_TOP, RT_TOP + 60.0): new_objs.append((mm, a10))          # 立ち上がり（南、外皮の線まで）
        for mm in slab(R(u + SL_HALF, u + 0.15, SL_V[0] - 0.1, VE, 0.2), RT_TOP, RT_TOP + 60.0): new_objs.append((mm, a10))          # 立ち上がり（北）
        for mm in slab(R(u - SL_HALF, u + SL_HALF, SL_V[0] - 0.1, SL_V[0], 0.05), RT_TOP, RT_TOP + 60.0): new_objs.append((mm, a10))      # 立ち上がり（西の端）
        for mm in slab(R(u - SL_HALF, u + SL_HALF, VE - 0.05, VE, 0.05), RT_TOP, RT_TOP + 60.0): new_objs.append((mm, a10))              # 立ち上がり（東の端、外皮の線）
        for mm in slab(R(u - 0.15, u + 0.15, SL_V[0] - 0.1, VE, 0.2), RT_TOP + 60.0, RT_TOP + 72.0): new_objs.append((mm, at_g))     # 乳白ガラス（複層、外皮の線まで）
        for mm in slab(R(u - SL_HALF, u + SL_HALF, SL_GL - 0.006, SL_GL + 0.006, 0.05), -250.0, RT_TOP + 60.0, vert=True): new_objs.append((mm, at_g))  # 外皮の線の固定ガラス（複層）
        # 10-29：軒の上（v13.6〜15）の単板のガラスと筋の内側の小口の板はやめた（筋は外皮の線で止め、軒の屋根材・通気垂木・太陽光は切らずに通す）
    def _purlin_box(k_, vc, ztop, q_, W=60.0, D=150.0):
        """10-27夜（ユーザー：母屋が長方形の押し出しでないのは変）：母屋は 60×150 の長方形の断面の真っすぐな材。
        軸はスパンの弦（架構の線 u=3k と 3k+3 の v=vc を結ぶ水平線）、断面は屋根の勾配（1/12）に直角に傾けた長方形
        （上の面が合板・梁の上端の面に沿う）、端は軸に直角（梁の側面とは 0.4° 以下の差で、すき間 0.5 mm 以下）。
        前は平面形を屋根の面から上下に押し出したので、断面が平行四辺形（縦の辺が鉛直、上下が勾配）だった。"""
        A_, B_ = xy(3.0 * k_, vc), xy(3.0 * (k_ + 1), vc)
        c_ = (B_ - A_) / np.linalg.norm(B_ - A_)
        h_ = np.array([c_[1], -c_[0]])
        if np.dot(h_, xy(3.0 * k_ + 1.5, vc + 1.0) - xy(3.0 * k_ + 1.5, vc)) < 0: h_ = -h_      # h は v の増える向き（東）
        P_ = np.asarray(q_.exterior.coords)[:-1] - A_
        s0_, s1_ = float((P_ @ c_).min()), float((P_ @ c_).max())
        z_top = ROOF_Z(vc) + ztop
        t_ = np.array([1.0, -1.0 / 12.0]); t_ /= np.linalg.norm(t_)      # 勾配の向き（h, z）
        n_ = np.array([-t_[1], t_[0]])                                    # 屋根の面に直角、上向き
        sec = [W / 2 * t_, -W / 2 * t_, -W / 2 * t_ - D * n_, W / 2 * t_ - D * n_]
        V_ = np.array([[*(A_ + s_ * c_ + hh * h_), z_top + zz] for s_ in (s0_, s1_) for hh, zz in sec])
        F_ = [(0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
        vol = sum(np.dot(V_[f[0]], np.cross(V_[f[i]] - V_[f[0]], V_[f[i + 1]] - V_[f[0]])) for f in F_ for i in (1, 2))
        if vol < 0: F_ = [f[::-1] for f in F_]                            # 面を外向きに
        mm = r.Mesh()
        for x_, y_, z_ in V_: mm.Vertices.Add(float(x_), float(y_), float(z_))
        for f_ in F_: mm.Faces.AddFace(*f_)
        mm.Normals.ComputeNormals(); mm.Compact()
        return mm
    # 母屋：梁と梁のあいだ（2 枚組の外の面 u ± 0.18 のあいだ）を桁の方向に渡す。室内は合板の下（PUR_BOT〜PLY_BOT）、v 1.79 から 455 おき、
    # 外皮の線の杉の壁（v13.465〜13.6）の手前 v13.40 まで。軒の下は梁の上端にそろえて落とし込む（v13.66・14.11・14.56、軒先の 0.4 手前まで）。
    _nr = 0
    _VI = [round(1.79 + 0.455 * i, 3) for i in range(30) if 1.79 + 0.455 * i <= 13.36] + [13.40]
    for vc in _VI + [VE + 0.06, VE + 0.51, VE + 0.96]:
        z0_, z1_ = (PUR_BOT, PLY_BOT) if vc < VE else (RT_BOT - 150.0, RT_BOT)
        for k_ in range(19):
            seg = R(3.0 * k_ + 0.18, 3.0 * k_ + 2.82, vc - 0.03, vc + 0.03, 99.0)
            if vc < VE: seg = seg.intersection(BAYS.buffer(1.0))
            for q_ in ([seg] if seg.geom_type == 'Polygon' else [g_ for g_ in getattr(seg, 'geoms', []) if g_.geom_type == 'Polygon']):
                if q_.area < 0.02e6: continue
                a_rf = r.ObjectAttributes(); a_rf.LayerIndex = L10V; a_rf.Name = f'母屋 杉 60×150（v {vc:.2f}{"、軒の下" if vc > VE else ""}）'
                new_objs.append((_purlin_box(k_, vc, z1_, q_), a_rf)); _nr += 1
    log.append(f'本館：屋根の構成（10-27夜）：母屋 {_nr} 本（10v）・合板 t24（10r）・断熱 t150 は梁のあいだ、梁の上は {RT_TOP - RT_BOT:.0f}、'
               f'東の軒は軒先で {EAVE_TIP:.0f}')
    ALL = unary_union([RP, EAVE.buffer(1.0)]).buffer(-1.0) if EAVE is not None else RP
    pv_box = unary_union([R(-10.0, 57.49, 1.95, 14.85, 0.25), R(-10.0, -0.35, -1.0, 14.85, 0.25)])
    pv = ALL.buffer(-150.0, join_style=2).intersection(pv_box).intersection(unary_union([RP, EAVE]) if EAVE is not None else RP)
    pv = pv.difference(R(-0.36, 57.49, -1.0, 1.95, 0.1)).difference(unary_union([R(u - 0.25, u + 0.25, SL_V[0] - 0.2, SL_V[1] + 0.05, 0.2) for u in SL_U]))   # 筋の周り ±0.25 は外皮の線の立ち上がりまで（軒の上は太陽光を通す、10-29）
    a_pv = r.ObjectAttributes(); a_pv.LayerIndex = L10P
    # 10-28（監修の項 20261028-2256-kanshu-2）：前は外皮の線（v13.6、_TAPER）で室内と東の軒の上の二つに分けていたので、スパンごとに 2 物に見えた。
    # 屋根の面はスパンごとの一枚の平面なので、分けずにスパンごとに一つ（sheet が架構の線で切る）。高さ・範囲は同じ
    # 10-29（監修の項 20261029-0928-kanshu-2 の 3）：閉じた板（thick(pv, RT_TOP, RT_TOP + 20.0)）にすると、削る段（clip_parts.py）が外の付属（X）として
    # 「建物の中」で削り、太陽光がほとんど消えた（西館の閉じた 20p は削る段で除いてある）。削る段で 10p も除かれるまで、面（sheet）のまま（監修に依頼）
    # 10-29 夕：削る段で 10p も除かれた（監修 d4d0447）ので、閉じた板（屋根の上面から 20、スパンごとに一枚）に
    for mm in thick(pv, RT_TOP, RT_TOP + 20.0): new_objs.append((mm, a_pv))             # 東の軒の上も屋根の面に沿って切れ目なく
    # 軒の見張り（ユーザー 10-27：軒は細くスマートに。約200でも分厚い。非常に重要なので後で壊さないように）：東の軒先（v 14.9〜15.0、架構 2〜19 のあいだ）に
    # 載る屋根の物のいちばん下からいちばん上までが EAVE_MAX を超えたら作り直しを止める。軒を厚くする直しは、ユーザーに聞いてから。
    EAVE_MAX = 80.0
    _ez = []
    for mm, at_ in new_objs:
        if at_.LayerIndex not in (L10, L10R, L10V, L10P, L10T) or not isinstance(mm, r.Mesh): continue
        for i_ in range(len(mm.Vertices)):
            p_ = mm.Vertices[i_]; uu_, vv_ = uv(p_.X, p_.Y)
            if vv_ > 14.9 and 3.3 < uu_ < 53.7: _ez.append(p_.Z - ROOF_Z(vv_))
    _et = (max(_ez) - min(_ez)) if _ez else 0.0
    if _et > EAVE_MAX:
        raise SystemExit(f'✗ 東の軒先の見付けが {_et:.0f} mm（{EAVE_MAX:.0f} 以下に、ユーザー 10-27：軒は細く。決定事項（共通）の「屋根の構成」）')
    log.append(f'本館：東の軒先の見付け {_et:.0f} mm（{EAVE_MAX:.0f} 以下、軒の見張り）')
    log.append(f'本館：光の筋 {len(SL_U)} 本（架構 2〜19、2 枚の梁のあいだ 180、v {SL_V[0]}〜{SL_V[1]}＝越屋根から外皮の線まで、乳白ガラス）、'
               f'屋根材型の太陽光 {pv.area / 1e6:.0f} m²（10p）')
    PV_AREA = pv.area / 1e6
    # 換気扇の出口（ユーザー 10-24：屋根の面に出すと目立つので越屋根に）。天井の換気扇からダクト φ100 を梁間の中で西へ、
    # 越屋根の東の口（東の立ち上がりの上端と蓋のあいだのすき間、外）のガラリの1区画を吹き出し口にする（逆流止めのシャッター付き）。
    # 越屋根のガラリは吐き出す向きのときだけ開く（差圧で自動、ユーザー 10-24）。西のすき間（西館とのすき間＝室内）には出さない。
    # 閉じる部屋 3 室と、0・1歳のおむつ替え・沐浴の上（ユーザー：建物の中で臭いが出るのはここ）。
    L50D = new_layer('50d_越屋根_換気扇の吹き出し口（ガラリの1区画）', (70, 70, 70))
    VENTS = [(19.5, '静養室'), (31.5, '多目的便所'), (41.1, '職員の個室'), (10.5, '0・1歳のおむつ替え・沐浴')]
    for uu, nm in VENTS:
        a_v = r.ObjectAttributes(); a_v.LayerIndex = L50D; a_v.Name = f'換気扇の吹き出し口（{nm}、φ100、逆流止め）'
        for mm in slab(R(uu - 0.3, uu + 0.3, 1.56, 1.64, 0.05), RT_TOP + 175.0, RT_TOP + 305.0, vert=True): new_objs.append((mm, a_v))
    log.append(f'本館：換気扇の吹き出し口 {len(VENTS)} か所（越屋根の東の口）')
    # 光の筋は鏡面の光ダクト（ユーザー 10-26夜、決定事項（共通）の「屋根の構成」）：溝（2 枚の梁のあいだ 180）の両側を、ガラスの下から梁の下端まで
    # 鏡面のアルミ t2 で張る（反射率 約0.95）。室内の分（v 1.76〜13.5、外皮の線の固定ガラスまで）。溝の下の端はふさがない。
    # 東の柱（v 約11.8〜12.2）は 2 枚の梁のあいだに入るので、その所は柱の上端から上だけ。
    L10M = new_layer('10m_本館_光の筋の鏡面（アルミ）', (205, 210, 215))
    _bm = None
    for o in m.Objects:
        if LN[o.Attributes.LayerIndex].startswith('11b') and isinstance(o.Geometry, r.Extrusion):
            _nc = o.Geometry.Profile3d(0, 0).ToNurbsCurve()
            _pp = [(uv(_nc.Points[i].X, _nc.Points[i].Y)[1], _nc.Points[i].Z) for i in range(len(_nc.Points))]
            _bm = Polygon(_pp).buffer(0); break
    def _beam_bot(v):
        if _bm is None: return ROOF_Z(v) - 750.0
        ln_ = LineString([(v, -1e4), (v, 1e5)]).intersection(_bm)
        return ln_.bounds[1] if not ln_.is_empty else ROOF_Z(v) - 750.0
    _COLS = [(11.78, 12.22, 3020.0)]
    def _mirror(u0_, u1_, v0_, v1_, zb_):
        vs_ = np.linspace(v0_, v1_, max(2, int((v1_ - v0_) / 0.25) + 1)); mm = r.Mesh()
        for v_ in vs_:
            zt_ = ROOF_Z(v_) + RT_TOP + 60.0; zz = zb_(v_)
            for uu_, z_ in ((u0_, zz), (u1_, zz), (u1_, zt_), (u0_, zt_)):
                x_, y_ = xy(uu_, v_); mm.Vertices.Add(float(x_), float(y_), float(z_))
        n_ = len(vs_)
        for i in range(n_ - 1):
            b0, b1 = 4 * i, 4 * (i + 1)
            for k in range(4):
                k2 = (k + 1) % 4; mm.Faces.AddFace(b0 + k, b0 + k2, b1 + k2, b1 + k)
        mm.Faces.AddFace(0, 3, 2, 1); e_ = 4 * (n_ - 1); mm.Faces.AddFace(e_, e_ + 1, e_ + 2, e_ + 3)
        mm.Normals.ComputeNormals(); mm.Compact(); return mm
    a_m = r.ObjectAttributes(); a_m.LayerIndex = L10M; a_m.Name = '光の筋の鏡面（アルミ t2、反射率 約0.95）'
    _nmir = 0
    for u in SL_U:
        for uu0, uu1 in ((u - SL_HALF, u - SL_HALF + 0.002), (u + SL_HALF - 0.002, u + SL_HALF)):
            for v0_, v1_, zb_ in ((SL_V[0], _COLS[0][0], _beam_bot), (_COLS[0][0], _COLS[0][1], lambda v: _COLS[0][2]), (_COLS[0][1], SL_GL - 0.006, _beam_bot)):
                new_objs.append((_mirror(uu0, uu1, v0_, v1_, zb_), a_m)); _nmir += 1
    log.append(f'本館：光の筋の鏡面 {_nmir} 片（10m、梁の下端から屋根のガラスの下まで、v {SL_V[0]}〜{SL_GL}）')
    # 光の筋をまたいで屋根の面をつなぐ（10-27、ユーザー・監修の略算、決定事項（共通）の「地震の力は骨格で受ける」）：光の筋で屋根の合板（水平構面）が
    # 架構ごとの帯に切れるので、2 枚の梁の上端に溝をまたぐ鋼の平板 6×60（梁の上端に彫り込み、長さ 340＝両側の梁 90 にかかる）を約 0.9 mおき。
    # 東の柱（v 11.78〜12.22）の所は柱が 2 枚の梁をつなぐので平板は無し。筋の両端（越屋根の東の立ち上がりの側・軒先の側）は溝をまたぐ縁の材
    # （杉 60×150、垂木の高さ、鏡面のあいだ）。合板の端は筋の両側の小口の受け材（垂木の高さ）に釘打ちし、受け材は梁にビス留め。屋根の上からの見えは変えない。
    L10K = new_layer('10k_本館_光の筋をまたぐつなぎ（鋼の平板・縁の材）', (120, 120, 125))
    def _mjoin(ms_):
        o_ = r.Mesh()
        for q_ in ms_: o_.Append(q_)
        o_.Normals.ComputeNormals(); o_.Compact(); return o_
    _VK = [round(2.2 + 0.9 * i, 2) for i in range(14)]
    _VK = [v_ for v_ in _VK if not (_COLS[0][0] - 0.1 <= v_ <= _COLS[0][1] + 0.1) and v_ < VE - 0.25]   # 10-29：外皮の線（立ち上がり）より東の平板は無し（筋の東の端の縁の材が溝をつなぐ、軒の上に溝は無い）
    _nk = 0
    for u in SL_U:
        _pl = []
        for v_ in _VK:
            _pl += slab(R(u - 0.17, u + 0.17, v_ - 0.03, v_ + 0.03, 0.05), RT_BOT - 6.0, RT_BOT)
        a_k = r.ObjectAttributes(); a_k.LayerIndex = L10K; a_k.Name = f'光の筋をまたぐ鋼の平板 6×60（架構 u{u:.0f}、{len(_VK)} 枚、約 0.9 mおき）'
        new_objs.append((_mjoin(_pl), a_k)); _nk += len(_VK)
        for v0_, v1_, nm_ in ((SL_V[0], SL_V[0] + 0.06, '越屋根の側'), (VE - 0.21, VE - 0.15, '外皮の線の側')):
            a_e = r.ObjectAttributes(); a_e.LayerIndex = L10K; a_e.Name = f'光の筋の端の縁の材（杉 60×150、{nm_}、架構 u{u:.0f}）'
            a_e.ColorSource = r.ObjectColorSource.ColorFromObject; a_e.ObjectColor = (196, 160, 118, 255)
            for mm in slab(R(u - SL_HALF + 0.003, u + SL_HALF - 0.003, v0_, v1_, 0.05), RT_BOT - 150.0, RT_BOT): new_objs.append((mm, a_e))   # 2 枚の梁のあいだ、上端＝梁の上端
    log.append(f'本館：光の筋をまたぐつなぎ（10k）：鋼の平板 {_nk} 枚（{len(SL_U)} 本の筋、約 0.9 mおき、東の柱の所は除く）と筋の両端の縁の材 {2 * len(SL_U)}')
    # 10-29（監修の項 20261029-0928-kanshu-2 の 1）：架構の梁（11b、2 枚組 ×20）の東の先（v15）は、上端が梁の上端（RT_BOT）のままで、
    # 通気垂木の止まる所（軒先の 150 手前、v14.85）より先は野地＋屋根材 64 の下面から 45 浮いていた。梁の先の 150 だけ上端を野地の下面
    # （その梁の上のスパンの平面から RT_TOP − EAVE_TIP）まで上げる（通気垂木の高さの段、軒先の見付け 64 と母屋の高さはそのまま）。
    # 押し出しのまま：輪郭の上端の直線（区間の一つ、梁の東の端の縦の面に続く）を、v14.85 で切って 3 つの区間（上端・段・上端）にする。
    def _beam_tip(g, vb=V_TIP - 0.15):
        if not isinstance(g, r.Extrusion) or g.ProfileCount < 1: return None
        pl = g.GetProfilePlane(0.0)
        O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z]); X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
        nc = g.Profile3d(0, 0.0).ToNurbsCurve(); dg = nc.Degree
        P = np.array([[nc.Points[i].X, nc.Points[i].Y, nc.Points[i].Z] for i in range(len(nc.Points))])
        W_ = [nc.Points[i].W for i in range(len(nc.Points))]
        K = [nc.Knots[i] for i in range(len(nc.Knots))]
        if any(abs(w_ - 1.0) > 1e-9 for w_ in W_): return None
        UV_ = np.array([uv(x, y) for x, y in P[:, :2]])
        dz = P[:, 2] - np.array([ROOF_Z(v_) for v_ in UV_[:, 1]])
        i0 = None
        for s_ in range(0, len(P) - 2 * dg, dg):                      # 区間の頭（区間の継ぎ目は次数ぶん重なった節）
            top_ = np.all(np.abs(dz[s_:s_ + dg + 1] - RT_BOT) < 2.0)
            if top_ and abs(UV_[s_ + dg, 1] - V_TIP) < 0.01 and UV_[s_, 1] < vb - 0.5 and np.all(np.abs(UV_[s_ + dg:s_ + 2 * dg + 1, 1] - V_TIP) < 0.01):
                i0 = s_; break
        if i0 is None: return None
        if len(set(round(k_, 6) for k_ in K[i0:i0 + dg])) != 1 or len(set(round(k_, 6) for k_ in K[i0 + dg:i0 + 2 * dg])) != 1: return None
        A0, A1, E1 = P[i0], P[i0 + dg], P[i0 + 2 * dg]                    # 上端の始め・東の角・東の縦の面の下
        key_ = ('s', _k_of(float(np.median(UV_[:, 0]))))
        t_ = (vb - UV_[i0, 1]) / (UV_[i0 + dg, 1] - UV_[i0, 1])
        Q1 = A0 + t_ * (A1 - A0)
        zt = lambda p_: zpl(key_, p_[0], p_[1]) + RT_TOP - EAVE_TIP     # 野地＋屋根材 64 の下面
        Q2 = np.array([Q1[0], Q1[1], zt(Q1)]); Q3 = np.array([A1[0], A1[1], zt(A1)])
        lerp = lambda a_, b_: [a_ + (b_ - a_) * j_ / dg for j_ in range(dg + 1)]
        newP = list(P[:i0]) + lerp(A0, Q1)[:-1] + lerp(Q1, Q2)[:-1] + lerp(Q2, Q3)[:-1] + lerp(Q3, E1)[:-1] + list(P[i0 + 2 * dg:])
        kA, kB = K[i0], K[i0 + dg]; L_ = [np.linalg.norm(Q1 - A0), np.linalg.norm(Q2 - Q1), np.linalg.norm(Q3 - Q2)]
        k1 = kA + (kB - kA) * L_[0] / sum(L_); k2 = kA + (kB - kA) * (L_[0] + L_[1]) / sum(L_)
        newK = K[:i0 + dg] + [k1] * dg + [k2] * dg + K[i0 + dg:]
        # 輪郭の面（2D）へ：押し出しの始まりの面の上の点を、面の座標（X・Y）に
        c2 = r.NurbsCurve(3, False, dg + 1, len(newP))
        for j_, p_ in enumerate(newP):
            q_ = np.asarray(p_) - O; c2.Points[j_] = r.Point4d(float(q_ @ X), float(q_ @ Y), 0.0, 1.0)
        for j_, k_ in enumerate(newK): c2.Knots[j_] = float(k_)
        if not c2.IsValid or not c2.IsClosed: return None
        a_, b_ = g.PathStart, g.PathEnd
        e_ = r.Extrusion();
        up_ = r.Vector3d(*map(float, Y))
        if not e_.SetPathAndUp(a_, b_, up_): return None
        # 輪郭は 2D（面の座標）：外の輪郭を差し替え、穴はもとのまま
        prof = [c2] + [None] * (g.ProfileCount - 1)
        for k_ in range(1, g.ProfileCount):
            h_ = g.Profile3d(k_, 0.0).ToNurbsCurve()
            hc = r.NurbsCurve(3, h_.IsRational, h_.Order, len(h_.Points))
            for j_ in range(len(h_.Points)):
                pp = h_.Points[j_]; w_ = pp.W if pp.W else 1.0; q_ = np.array([pp.X / w_, pp.Y / w_, pp.Z / w_]) - O
                hc.Points[j_] = r.Point4d(float(q_ @ X) * w_, float(q_ @ Y) * w_, 0.0, w_)
            for j_ in range(len(h_.Knots)): hc.Knots[j_] = h_.Knots[j_]
            prof[k_] = hc
        if not e_.SetOuterProfile(prof[0], True): return None
        for hc in prof[1:]:
            if not e_.AddInnerProfile(hc): return None
        return e_ if e_.IsValid else None
    _n_tip = 0; _tip_bad = 0
    for o in m.Objects:
        if not LN[o.Attributes.LayerIndex].startswith('11b') or not isinstance(o.Geometry, r.Extrusion): continue
        e_ = _beam_tip(o.Geometry)
        if e_ is None: _tip_bad += 1; continue
        EXT[str(o.Attributes.Id)] = e_; _n_tip += 1
    log.append(f'本館：架構の梁 {_n_tip} 枚の東の先（v{V_TIP - 0.15:.2f}〜{V_TIP}）の上端を野地＋屋根材の下面（梁の上端＋{RT_TOP - EAVE_TIP - RT_BOT:.0f}）に'
               f'（直せなかった {_tip_bad}）')
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
    # 機械室の戸（アプローチ係の依頼 10-24昼の1）：北西の面（道路側）のまっすぐな所の真ん中に両開き約1.6、外開き、h2.1。
    # 位置は外構の data/approachA.json の NORTH.MECH_DOOR（北西の道路から測る t、面は n=1.16）。戸の板を外面の 20 外に。
    import os as _os, json as _json
    _N = _json.load(open(_os.path.join(_os.path.dirname(_os.path.abspath(sys.argv[3])), 'approachA.json'), encoding='utf-8'))['NORTH']
    _B0, _N0 = np.array((-25.83, -20.54)), np.array((0.0, 0.0))
    _t2 = (_N0 - _B0) / np.linalg.norm(_N0 - _B0); _n2 = np.array([_t2[1], -_t2[0]]); _n2 = _n2 if _n2[1] < 0 else -_n2
    _TT = lambda t, n: (_B0 + _t2 * t + _n2 * n) * 1000.0
    t0, t1 = _N['MECH_DOOR']['t']; tm = (t0 + t1) / 2
    L35D = new_layer('35d_機械室_戸（両開き1.6、外開き）', (120, 90, 60))
    for a_, b_, nm in ((t0, tm - 0.005, '左'), (tm + 0.005, t1, '右')):
        door = Polygon([_TT(a_, 1.10), _TT(b_, 1.10), _TT(b_, 1.14), _TT(a_, 1.14)])
        a35d = r.ObjectAttributes(); a35d.LayerIndex = L35D; a35d.Name = f'機械室の戸（{nm}の扉、外開き）'
        tmp = r.File3dm(); Kt = Kit(tmp); Kt.prism(door, 0.0, 2100.0, L35D)
        for o2 in tmp.Objects: new_objs.append((o2.Geometry, a35d))
    log.append('機械室：北西の面に両開きの戸1.6（35d）')
    # 機械室の外壁も本館の外壁と同じスギの大和張り（10-26）。押縁は付けない（大和張りの重なりが継ぎ目を覆う、ユーザー 10-26 1:59）。
    m.Layers[L35].Color = (196, 160, 118, 255)                               # 3dm の機械室の塊の色をスギに（本館の外壁 17 と同じ）

# 本館の外壁はスギの大和張り（決定事項（共通）の「外壁と窓」）。縦の板は長尺で継がず、押縁は付けない（ユーザー 10-26 1:59、本館の壁は 4.3 m 以下なので水切りも無し）。

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
    g = bm.get(str(o.Attributes.Id), cur_g(o))
    P = tris(g).reshape(-1, 3)[:, :2]
    if len(P) < 3: continue
    c = P.mean(0); X = P - c; w_, vec = np.linalg.eigh(X.T @ X); ax = vec[:, -1]
    ax = ax if ax[0] >= 0 else -ax; nn_ = np.array([-ax[1], ax[0]])
    s0_, s1_ = ((P - c) @ ax).min() - 3000.0, ((P - c) @ ax).max() + 3000.0; t0_, t1_ = ((P - c) @ nn_).min(), ((P - c) @ nn_).max()
    lines_.append((c, ax, Polygon([c + ax * s0_ + nn_ * t0_, c + ax * s1_ + nn_ * t0_, c + ax * s1_ + nn_ * t1_, c + ax * s0_ + nn_ * t1_])))
# 10-28：梁のあいだの層（断熱・合板・母屋）を切る帯は、2 枚の梁の平面形（梁の軸に沿って両へ 3 m 延ばした長方形、出し梁も同じ面）を
# 囲む形にする（前は架構の線の芯から ±180 の帯で、放射の線の 2 枚とは平行でないので、梁の上端を屋根の面に上げると梁に 10〜20 食い込んでいた）
PAIR_BANDS = []
pairs = []; used = set()
for i, (c1, a1, _r1) in enumerate(lines_):
    if i in used: continue
    nrm = np.array([-a1[1], a1[0]])
    js = [j for j, (c2, a2, _r2) in enumerate(lines_) if j != i and j not in used and abs(np.dot(c2 - c1, nrm)) < 400]
    if not js: continue
    j = min(js, key=lambda j: abs(np.dot(lines_[j][0] - c1, nrm))); used |= {i, j}
    c2, a2 = lines_[j][:2]; ax = (a1 + a2); ax /= np.linalg.norm(ax)
    PAIR_BANDS.append(unary_union([lines_[i][2], lines_[j][2]]).convex_hull)
    off = np.dot(c2 - c1, np.array([-ax[1], ax[0]])) / 2.0
    cc = c1 + np.array([-ax[1], ax[0]]) * off
    pairs.append((cc, ax))
PLYFP = unary_union([q_[2] for q_ in lines_])                    # 10-31：梁の板 1 枚ずつの平面形（軸に沿って 3 m 延ばした長方形、排気のスリットの中の物を板の所で切る）
_fp20 = [foot(o.Geometry) for o in m.Objects if o.Attributes.LayerIndex == L20 and isinstance(o.Geometry, r.Mesh)]
WSL = unary_union([f for f in _fp20 if f is not None]).buffer(-1.0)   # 10-24（ユーザー、本館と同じ）：越屋根から軒先まで。軒先＝屋根の面の先（10-24昼：西の軒の出 0.9、軒樋の手前）
EASTV = -2.56                          # 棟のガラスの帯の西の縁（前の越屋根の西の立ち上がりの外面、幅 1.6）
SLIT_W = EASTV - 0.21                  # 10-31：排気のスリット（幅 150）の西の縁の材の西の面（屋根の板・光の筋はここまで）
VRIDGE_W = -0.9                        # 棟（西館の東の縁）
WSi_W = WS_W.buffer(-150.0, join_style=2)   # 外壁の内面（外皮の線の固定ガラス）
slits = []
for cc, ax in pairs:
    uc, vc = uv(*cc)
    if uc < 22.0 or uc > 50.5: continue
    nrm = np.array([-ax[1], ax[0]])
    p0 = cc - ax * 20000; p1 = cc + ax * 20000
    band = Polygon([p0 - nrm * 90, p1 - nrm * 90, p1 + nrm * 90, p0 + nrm * 90])
    zone = WSL.intersection(Polygon([xy(uc - 3, SLIT_W), xy(uc + 3, SLIT_W), xy(uc + 3, -30), xy(uc - 3, -30)]))     # 10-31：東の端は排気のスリットの西の縁
    s_ = band.intersection(zone)
    if s_.geom_type != 'Polygon' or s_.area < 1e5: continue
    # 筋の長さの両端（t0：西の端、t1：東の端）
    T_ = [np.dot(np.array(pt) - cc, ax) for pt in s_.exterior.coords]
    # 10-27夕（ユーザー：光の筋は屋内だけ、柱の内側だけで要る。その外は筋だけ見えて下に中身が無い）：西の端を外壁の内面の線で止め、
    # その外（軒の出）は屋根を切らずに一枚に。軒の出は梁を軒先まで出して支える（下の「出し梁」）。
    e_ = 1 if np.dot(ax, np.array(xy(uc, EASTV)) - np.array(xy(uc, -10))) > 0 else -1
    lo_, hi_ = min(T_), max(T_); tW_ = lo_ if e_ > 0 else hi_
    _x = LineString([cc + ax * (lo_ - 3000), cc + ax * (hi_ + 3000)]).intersection(WSi_W.exterior)
    _xs = [np.dot(np.array([q.x, q.y]) - cc, ax) for q in ([_x] if _x.geom_type == 'Point' else list(getattr(_x, 'geoms', [])))]
    _xs = [t for t in _xs if lo_ - 1 <= t <= hi_ + 1]
    if _xs:
        tW_ = min(_xs, key=lambda t: abs(t - tW_))
        lo_, hi_ = (tW_, hi_) if e_ > 0 else (lo_, tW_)
    slits.append((cc, ax, nrm, lo_, hi_))
def strip(cc, ax, nrm, t0, t1, a, b_):
    return Polygon([cc + ax * t0 + nrm * a, cc + ax * t1 + nrm * a, cc + ax * t1 + nrm * b_, cc + ax * t0 + nrm * b_])
# 出し梁（10-27夕、ユーザー：軒の出を支える構造が無かった → 梁を軒先まで出す、出す部分は細くスマートに）：
# 屋根の梁（22b、2 枚組 90）は外壁の内面で止まっていて、垂木は軒と平行なので、軒の出（約0.8）を持ち出すものが無かった。
# 2 枚組の梁のそれぞれを外壁を貫いて軒先の 0.1 手前まで出す。上端は屋根の下面（梁の上端と同じ面）、せいは外壁の内面で 240、
# 軒先で 120（先細り）。軒の出の垂木（20v）は出し梁から出し梁へ（3 m）。略算：屋根＋雪 約1.44 kN/m²×3 m、軒の出 0.8 で
# M≈1.4 kNm、2×90×240 で約0.8 N/mm²（十分）。外壁（21）は出し梁の所を欠く（構造と外皮は削る段で削らないので、ここで欠く）。
L21W = lidx('21_'); _CANT = []; _cant_ms = []; _CTIP = []; _STUD_FP = []
def _merge_head(g, O, X, Y, hd, sg, sw, s_tip, zt_w, zt_t, _hm):
    """梁の板 g の西の端を、西の桁の穴のまわりの丸い頭＋軒先への細い延長の一つの外形にした押し出し（できなければ None）"""
    from shapely.geometry import Polygon as _Pg, box as _box
    from shapely import affinity as _aff
    profs = extedit.profiles3d(g)
    sz = lambda P: np.c_[(P[:, :2] - O[:2]) @ hd, P[:, 2]]
    def _dense(nc, n=900):
        d_ = nc.Domain; return np.array([[q.X, q.Y, q.Z] for q in (nc.PointAt(t) for t in np.linspace(d_.T0, d_.T1, n))])
    B = _Pg(sz(_dense(profs[0]))).buffer(0)
    if B.geom_type != 'Polygon': B = max(B.geoms, key=lambda q: q.area)
    # 西の桁の穴（端に近い、桁の断面＋10 くらいの穴）
    hole = None
    for k_, nc in enumerate(profs[1:], 1):
        H = sz(_dense(nc, 200)); w_, h_ = np.ptp(H[:, 0]), np.ptp(H[:, 1]); c_ = H.mean(0)
        if 150.0 < w_ < 320.0 and 300.0 < h_ < 520.0 and abs(c_[0] - sw) < 900.0:
            if hole is None or abs(c_[0] - sw) < abs(hole[0] - sw): hole = (c_[0], c_[1])
    zr = lambda s_: float(_RWf['roof_f'](*(O[:2] + hd * s_ + _hm)))
    if hole is None:                                                         # 西の桁が板を通らない所（南西・北西の角の斜めの桁）：頭はほかの架構と同じ位置（端から 280 内、上端から 528 下＝穴を通る架構の並み）
        sh = sw - sg * 280.0; zh = zr(sh) - 528.0
    else:
        sh, zh = hole
    _HEADPOS.append(((sw - sh) * sg, zr(sh) - zh, hole is not None))
    A_, B_ = 280.0, 380.0                                                   # 本館と同じ：桁 100×200 の半径＋180
    E = _aff.scale(Point(sh, zh).buffer(1.0, resolution=64), A_, B_, origin=(sh, zh))
    zr = lambda s_: float(_RWf['roof_f'](*(O[:2] + hd * s_ + _hm)))
    soff = lambda s_: (zt_w - 240.0) + ((zt_t - 120.0) - (zt_w - 240.0)) * (s_ - sw) / (s_tip - sw)
    ss = np.linspace(sh, s_tip, 40)
    band = _Pg([(x_, zr(x_) + 50.0) for x_ in ss] + [(x_, soff(x_)) for x_ in ss[::-1]]).buffer(0)
    far = 1e5
    east = _box(min(sh, sh - sg * far), -far, max(sh, sh - sg * far), far)          # 頭の芯より梁の側
    west = _box(min(sh, sh + sg * far), -far, max(sh, sh + sg * far), far)
    win = _box(min(sh - sg * 1400.0, s_tip), -far, max(sh - sg * 1400.0, s_tip), far)
    U = unary_union([B.intersection(win), E, band]).buffer(300.0, resolution=24).buffer(-300.0, resolution=24)
    newp = unary_union([B.difference(win), B.intersection(win).intersection(east), U.intersection(win)])
    # 上端は屋根の面（梁の上端）で切る、先は s_tip で鉛直に
    s0_, s1_ = min(B.bounds[0], s_tip) - 10.0, max(B.bounds[2], s_tip) + 10.0
    xs_ = np.linspace(s0_, s1_, 400)
    top_ = [zr(x_) if (x_ - sh) * sg > 0 else max(zr(x_), B.intersection(_box(x_ - 2.0, -far, x_ + 2.0, far)).bounds[3] if not B.intersection(_box(x_ - 2.0, -far, x_ + 2.0, far)).is_empty else zr(x_)) for x_ in xs_]
    under = _Pg([(xs_[0], -far)] + list(zip(xs_, top_)) + [(xs_[-1], -far)]).buffer(0)
    tipcut = _box(min(s_tip, s_tip - sg * far), -far, max(s_tip, s_tip - sg * far), far)
    newp = newp.intersection(under).intersection(tipcut).buffer(0)
    if newp.geom_type != 'Polygon': newp = max(newp.geoms, key=lambda q: q.area)
    newp = newp.simplify(0.3)
    for k_, nc in enumerate(profs[1:], 1):                                  # 穴はみな新しい外形の中に
        Hp = _Pg(sz(_dense(nc, 120))).buffer(0)
        if not newp.buffer(-5.0).contains(Hp): raise ValueError('穴が外形の外 %.0f,%.0f' % tuple(np.asarray(Hp.centroid.coords[0])))
    # 押し出しに：外形は折れ線、穴は元のまま
    def to_pl(P3):
        return np.c_[(P3 - O) @ X, (P3 - O) @ Y, np.zeros(len(P3))]
    ext3 = np.array([[*(O[:2] + hd * x_), z_] for x_, z_ in np.asarray(newp.exterior.coords)])
    Q = to_pl(ext3)
    outer = r.Polyline([r.Point3d(*map(float, q_)) for q_ in Q]).ToNurbsCurve()
    e = r.Extrusion()
    if not e.SetPathAndUp(g.PathStart, g.PathEnd, g.GetProfilePlane(0.0).YAxis): return None
    if not e.SetOuterProfile(outer, True): return None
    for nc in profs[1:]:
        W_ = extedit._weights(nc); P_ = extedit._pts(nc); nc2 = nc.Duplicate() if hasattr(nc, 'Duplicate') else nc
        extedit._set_pts(nc2, to_pl(P_), W_)
        if not e.AddInnerProfile(nc2): return None
    return e if e.IsValid else None
def _ply_setter(key_):
    """梁の板の形を差し替える（_WOOD の記録も一緒に）"""
    def _set(e_):
        for w_ in _WOOD:
            if (w_[0] == key_[0]) and (w_[1] == key_[1]): _wset(w_, e_); return
        if key_[0] == 'm': EXT[key_[1]] = e_
        else: _XNEW[key_[1]] = (e_, _XNEW[key_[1]][1])
    return _set
_PLY_ITEMS = [(_ply_setter(('m', str(o.Attributes.Id))), cur_g(o)) for o in m.Objects if o.Attributes.LayerIndex == L22B] + [(_ply_setter(('x', i_)), _XNEW[i_][0]) for i_ in _RAF_IDX]
_n_head = 0; _head_fail = []; _HEADPOS = []
for _setply, g in _PLY_ITEMS:     # 10-29 昼：u43.5 の 2 枚組（_RAF_PLIES）にも
    if not isinstance(g, r.Extrusion): continue
    S_ = _ring_pts(g, 0); U_ = to_uv_arr(S_)                                   # 10-29 昼：節ごとの点（全体を等分すると端の丸みに点が少ない）
    iw = int(np.argmin(U_[:, 1]))                                             # 西の端（v がいちばん小さい点）
    pl = g.GetProfilePlane(0.0); O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z])
    X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
    hd = np.array([X[0], X[1]]) if abs(X[2]) < 0.5 else np.array([Y[0], Y[1]]); hd = hd / np.linalg.norm(hd)
    s_all = (S_[:, :2] - O[:2]) @ hd; sw = s_all[iw]; sg = -1.0 if sw < np.median(s_all) else 1.0     # 外へ向かう向き
    p_w = O[:2] + hd * sw
    _uf_ = _fk3(uv(*((O[:2] + np.array([g.PathEnd.X - g.PathStart.X, g.PathEnd.Y - g.PathStart.Y]) / 2.0 + (np.array([g.PathStart.X, g.PathStart.Y]) - O[:2]))))[0])
    if WS_W.contains(Point(*(p_w + hd * sg * 400.0))) and not any(g is q_ for q_ in _raf()) and _uf_ not in _sqf: continue    # 外壁の内面で止まっていない端（妻の側など）は出さない（u43.5 の 2 枚と、1 枚に出し梁の付く端の架構 u21.33・u48 のもう 1 枚は出す。10-29 夜、監修の項 2027 の 1）
    _x = LineString([p_w, p_w + hd * sg * 4000.0]).intersection(WSL.exterior)
    _ps = [_x] if _x.geom_type == 'Point' else list(getattr(_x, 'geoms', []))
    if not _ps: continue
    s_tip = min(((np.array([q.x, q.y]) - O[:2]) @ hd for q in _ps), key=lambda t: abs(t - sw)) - sg * 100.0
    # 10-29 夜（監修の項 2027 の 4）：先は軒先から 100（軒先の線に直角に測る）。軒先が斜め・曲がる所（南西の角）で、出し梁の向きに 100 では
    #   先が軒の母屋（軒先から 100〜160）に届かなかった（離れ 34）
    _se = s_tip + sg * 100.0; _dm = lambda t: Point(*(O[:2] + hd * t + _hm0)).distance(WSL.exterior)
    _hm0 = (np.array([g.PathEnd.X, g.PathEnd.Y]) - np.array([g.PathStart.X, g.PathStart.Y])) / 2.0 + (np.array([g.PathStart.X, g.PathStart.Y]) - O[:2])
    if _dm(s_tip) < 100.0 - 1.0: pass
    else:
        _lo, _hi = s_tip, _se                                                    # _lo：100 より遠い、_hi：軒先
        for _ in range(20):
            _md = (_lo + _hi) / 2
            if _dm(_md) > 100.0: _lo = _md
            else: _hi = _md
        s_tip = _lo
    if (s_tip - sw) * sg < 300.0: continue
    a_, b_ = g.PathStart, g.PathEnd
    A3 = np.array([a_.X, a_.Y, a_.Z]); B3 = np.array([b_.X, b_.Y, b_.Z])
    def P3(s, z): q = O[:2] + hd * s; return [float(q[0]), float(q[1]), float(z)]
    _hm = (B3[:2] - A3[:2]) / 2.0 + (A3[:2] - O[:2])                       # 10-28：上端は梁と同じ屋根の面 roof_f（その 1 枚の厚みの真ん中）
    zt_w = float(_RWf['roof_f'](*(O[:2] + hd * sw + _hm)))
    # 10-29（監修の項 20261028-2355 の I）：出し梁の内の端は梁の端の面に（前は梁の外形のいちばん西の点から始めて、梁の端と 7〜90 離れた）
    try:
        _bp = Polygon(np.c_[s_all, S_[:, 2]]).buffer(0)
        _sx = []
        for _dz_ in (5.0, 120.0, 235.0):                                             # 出し梁のせいの中で梁がいちばん外へ出る所（重ならない）
            _hz = _bp.intersection(LineString([(s_all.min() - 1000.0, zt_w - _dz_), (s_all.max() + 1000.0, zt_w - _dz_)]))
            if not _hz.is_empty: _bx = _hz.bounds; _sx.append(_bx[0] if sg < 0 else _bx[2])
        if _sx:
            sw = min(_sx) if sg < 0 else max(_sx)
            zt_w = float(_RWf['roof_f'](*(O[:2] + hd * sw + _hm)))
            _vl = _bp.intersection(LineString([(sw - sg * 2.0, zt_w - 1000.0), (sw - sg * 2.0, zt_w + 1000.0)]))   # 10-29 昼：上端は梁の端の上端に（2 枚を写した梁は屋根の面と 15 以内で違う）
            if not _vl.is_empty: zt_w = float(_vl.bounds[3])
    except Exception: pass
    zt_t = float(_RWf['roof_f'](*(O[:2] + hd * s_tip + _hm)))
    pts = [P3(sw, zt_w), P3(s_tip, zt_t), P3(s_tip, zt_t - 120.0), P3(sw, zt_w - 240.0)]
    th = float(np.linalg.norm(B3 - A3)); dvec = (B3 - A3) / th
    off = (A3[:2] - O[:2]); pts = [[p[0] + off[0], p[1] + off[1], p[2]] for p in pts]   # 道の始まりの面の上に
    pl_ = r.Polyline([r.Point3d(*p) for p in pts + [pts[0]]]); crv = pl_.ToNurbsCurve()
    e1 = r.Extrusion.Create(crv, th, True); e2 = r.Extrusion.Create(crv, -th, True)
    best = None
    for e_ in (e1, e2):
        if e_ is None: continue
        bb = e_.GetBoundingBox(); c_ = np.array([(bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2])
        mid = (A3[:2] + B3[:2]) / 2; d_ = abs((c_ - mid) @ dvec[:2])
        if best is None or d_ < best[0]: best = (d_, e_)
    if best is None: continue
    # 10-31（ユーザー 11:15：形は本館の西の端と同じ丸い頭、しかし梁として一体。本館の東の端（軒のための延長が梁と一体の板）が参考）：
    #   別の板の出し梁はやめ、2 枚組の各板の外形を、西の桁の穴のまわりの丸い頭（Tamedia：桁の楕円＋木の厚み 180 の楕円、a 280・b 380）と、
    #   頭から軒先へ同じ板のまま細い延長（上端は屋根の面、下端は外壁の内面で 240 → 先で 120 の直線、先は鉛直に切る）を、本館と同じ丸み（300）で
    #   つないだ一つの外形にする。_CANT（延長の部分の立体）は、母屋・鼻母屋の端と外壁の欠きのために前と同じに残す
    _CANT.append(best[1]); _CTIP.append((O[:2] + hd * s_tip + _hm, hd * sg))     # 先の点（厚みの真ん中）と外向き
    try:
        _e_new = _merge_head(g, O, X, Y, hd, sg, sw, s_tip, zt_w, zt_t, _hm)
    except Exception as _ex:
        _e_new = None; _head_fail.append(f'u{uv(*(O[:2] + hd * sw))[0]:.2f} ' + str(_ex)[:40])
    if _e_new is not None:
        _setply(_e_new); _n_head += 1
        best = (0.0, _e_new)
    else:
        if not _head_fail or not _head_fail[-1].startswith(f'u{uv(*(O[:2] + hd * sw))[0]:.2f}'): _head_fail.append(f'u{uv(*(O[:2] + hd * sw))[0]:.2f}')
        at_ = r.ObjectAttributes(); at_.LayerIndex = L22B; at_.Name = '出し梁（2 枚組の梁の先、外壁を貫いて軒先まで、せい 240 → 120）'
        _XNEW.append((best[1], at_))
    T_c = tri.tri_extrusion(best[1])
    if len(T_c):
        tm_c = trimesh.Trimesh(T_c.reshape(-1, 3), np.arange(len(T_c) * 3).reshape(-1, 3)); tm_c.merge_vertices()
        tm_c.fix_normals()
        try: _cant_ms.append(_mf.Manifold(_mf.Mesh(vert_properties=np.asarray(tm_c.vertices, np.float32), tri_verts=np.asarray(tm_c.faces, np.uint32))))
        except Exception: pass
# 北西の角の u43.5 の梁（10-27夜：一本の登り梁 120×800 → 10-29 昼：ほかの架構と同じ 2 枚組の梁、上の 3g の u）。出し梁は上でほかの梁と同じに作った。
# 外壁を出し梁の所だけ欠く
_nwall = 0
if _cant_ms:
    _CM = _mf.Manifold.batch_boolean([c_ for c_ in _cant_ms if not c_.is_empty()], _mf.OpType.Add)
    _cbb = _CM.bounding_box()
    for o in m.Objects:
        if o.Attributes.LayerIndex != L21W or not isinstance(o.Geometry, r.Mesh) or str(o.Attributes.Id) in drop: continue
        T_w = tris(o.Geometry)
        if not len(T_w): continue
        tm_w = trimesh.Trimesh(T_w.reshape(-1, 3), np.arange(len(T_w) * 3).reshape(-1, 3)); tm_w.merge_vertices(digits_vertex=1)
        if not tm_w.is_watertight: continue
        b0, b1 = tm_w.bounds
        if b1[2] < 3000: continue
        M_w = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(tm_w.vertices, np.float32), tri_verts=np.asarray(tm_w.faces, np.uint32)))
        if M_w.is_empty(): continue
        M2 = M_w - _CM
        if abs(M2.volume() - M_w.volume()) < 1e3: continue
        g_ = M2.to_mesh(); mm_ = r.Mesh()
        for x_, y_, z_ in np.asarray(g_.vert_properties)[:, :3]: mm_.Vertices.Add(float(x_), float(y_), float(z_))
        for a__, b__, c__ in np.asarray(g_.tri_verts): mm_.Faces.AddFace(int(a__), int(b__), int(c__))
        mm_.Normals.ComputeNormals(); mm_.Compact()
        drop.add(str(o.Attributes.Id)); new_objs.append((mm_, o.Attributes)); _nwall += 1
log.append(f'西館：梁の西の端を丸い頭と軒先への細い延長の一つの外形に {_n_head} 枚（10-31、別の板の出し梁はやめた。できなかった {len(_head_fail)}：{_head_fail}、頭の位置（端からの距離・上端からの深さ・穴）{[(round(a_), round(b_), c_) for a_, b_, c_ in _HEADPOS]}）、延長 {len(_CANT)}、外壁 {_nwall} 片を延長の所で欠いた')
if slits:
    L20T = new_layer('20t_西館_光の筋（乳白ガラス、架構の線）', (225, 236, 242), MAT_FROST if MAT_FROST >= 0 else None)
    L20P = new_layer('20p_西館_屋根材型の太陽光（金属の屋根と一体）', (45, 49, 58))
    a20 = r.ObjectAttributes(); a20.LayerIndex = L20
    at_g2 = r.ObjectAttributes(); at_g2.LayerIndex = L20T
    if MAT_FROST >= 0: at_g2.MaterialSource = r.ObjectMaterialSource.MaterialFromObject; at_g2.MaterialIndex = MAT_FROST
    # 10-29 昼（監修の項 20261029-0928 の 5）：筋の西の端は外壁の内面の線で切る（筋の芯の線が線を切る所で直角に止めていたので、斜めの壁（北西）
    # では筋の片側が線の手前で止まっていた）。西へ延ばした帯を外壁の内面の内側（WSi_W）で切る
    def _slit_band(cc, ax, nrm, t0, t1, a, b_, ext=600.0):
        uc_ = uv(*cc)[0]; e_ = 1 if np.dot(ax, np.array(xy(uc_, EASTV)) - np.array(xy(uc_, -10))) > 0 else -1
        tE_ = t1 if e_ > 0 else t0; tW_ = t0 if e_ > 0 else t1; tX_ = tW_ - ext * e_
        return strip(cc, ax, nrm, min(tX_, tE_), max(tX_, tE_), a, b_).intersection(WSi_W)
    SL20 = unary_union([_slit_band(cc, ax, nrm, t0, t1, -90, 90) for cc, ax, nrm, t0, t1 in slits])
    # 屋根の構成（10-27夜、ユーザー、本館係の項 20261027-1937、決定事項_本館・決定事項（共通）の「屋根の構成」）：前の「梁の上に 420」はやめた。
    # 下から：登り梁（2 枚組）／母屋 杉 60×150 @455（梁と梁のあいだ、桁の方向、梁の側面の金物）／構造用合板 t24（母屋の上、室内に現す天井）／
    # 気密シート／断熱 t150（梁のあいだに一枚、上面＝梁の上端）／梁と断熱の上に通気垂木 45・野地 t24・屋根材と太陽光 40＝梁の上は 109。
    # 10-28 昼（ユーザー：西館の屋根の上の層と軒を本館と同じ作り方に。本館係の項 20261028-0043、fix_details.py の本館の節）：
    #   屋根の面はベイ（roofw の BAYS）ごとの面（平面のスパンは平面、光の筋の中の帯と北西の角は双一次）。板はベイごとに切り、平面のベイは面に直角に押し出す
    #   （本館の _plate と同じ、層の高さは鉛直に測る）、双一次のベイは上下の面＝屋根の面＋高さ（網目の点はベイの境と (s, h) の格子の線の上）。
    #   通気垂木 60×45 @455（20b、一本ずつ、平面のスパンは最大傾斜の向き、北西の角は梁の線に沿う向き）を梁と断熱の上に、軒先の 150 手前まで。
    #   野地 t24＋屋根材 40＝64 の板は軒先まで（軒は通気垂木の先から 150 持ち出し、軒先の見付け 64。前の「軒の下面が 45 上がる」はやめた）。
    #   軒の下は母屋を梁の上端にそろえて落とし込む（出し梁から出し梁へ）。
    RT_W = 109.0
    PV_T = 40.0; VENT_TOP = RT_W - PV_T                                 # いちばん上の屋根材 40（太陽光・金属）、その下が野地（〜69）
    BAT_T, BAT_W, BAT_IN = 45.0, 60.0, 150.0                         # 通気垂木 60×45、軒先の 150 手前まで
    INS_T, PLY_T, PUR_T = 150.0, 24.0, 150.0                          # 断熱・合板・母屋
    from shapely import constrained_delaunay_triangles as _cdt
    _BB20 = _RWf['BAYS']; _NB20 = len(_BB20) - 1
    _BC20 = [np.array([_RWf['ruled_point'](k, h_, s_) for h_, s_ in ((0, 0), (0, 1), (1, 0), (1, 1))]) for k in range(_NB20)]   # C00 C10 C01 C11
    _BPL20 = []
    for C_ in _BC20:
        o_ = C_.mean(0); n_ = np.linalg.svd(C_ - o_)[2][2]; n_ = n_ if n_[2] > 0 else -n_
        _BPL20.append((o_, n_) if np.abs((C_ - o_) @ n_).max() <= 0.25 else None)
    def _bay_poly(k):
        ua_ = _BB20[k] if k > 0 else 12.0; ub_ = _BB20[k + 1] if k < _NB20 - 1 else 60.0
        return Polygon([xy(ua_, 4.0), xy(ua_, -40.0), xy(ub_, -40.0), xy(ub_, 4.0)])
    _BPOLY = [_bay_poly(k) for k in range(_NB20)]
    def _bsh(k, P2):
        C2 = _BC20[k][:, :2]; out_ = []
        for q in np.atleast_2d(P2):
            s, h = 0.5, 0.5
            for _ in range(40):
                P_ = (1 - s) * (1 - h) * C2[0] + s * (1 - h) * C2[1] + (1 - s) * h * C2[2] + s * h * C2[3]
                J = np.c_[(1 - h) * (C2[1] - C2[0]) + h * (C2[3] - C2[2]), (1 - s) * (C2[2] - C2[0]) + s * (C2[3] - C2[1])]
                d = np.linalg.solve(J, q - P_); s += d[0]; h += d[1]
                if abs(d[0]) < 1e-12 and abs(d[1]) < 1e-12: break
            out_.append((s, h))
        return np.array(out_)
    def _bz(k, P2):
        P2 = np.atleast_2d(P2)
        if _BPL20[k] is not None:
            o_, n_ = _BPL20[k]; return o_[2] - (n_[0] * (P2[:, 0] - o_[0]) + n_[1] * (P2[:, 1] - o_[1])) / n_[2]
        C = _BC20[k]; S = _bsh(k, P2); s, h = S[:, 0], S[:, 1]
        return (1 - s) * (1 - h) * C[0, 2] + s * (1 - h) * C[1, 2] + (1 - s) * h * C[2, 2] + s * h * C[3, 2]
    def _bcell(k, s0, s1, h0, h1):
        q = [_RWf['ruled_point'](k, h_, s_)[:2] for h_, s_ in ((h0, s0), (h0, s1), (h1, s1), (h1, s0))]
        return Polygon(q)
    def _btri(p, k, cell=400.0):
        """平面形 p（ベイ k の中）の三角形（平面の点 V2、面 F、上向き）。双一次のベイは (s, h) の格子で切ってから"""
        p = p.simplify(0.5)                                                   # 近すぎる点（1 mm 未満）を除く（一つにまとめると面が潰れる）
        if p.geom_type != 'Polygon' or p.is_empty: return np.zeros((0, 2)), np.zeros((0, 3), int)
        if _BPL20[k] is not None: parts = [p]
        else:
            C = _BC20[k]; W_ = max(1.0, np.linalg.norm(C[1, :2] - C[0, :2])); L_ = np.linalg.norm(C[2, :2] - C[0, :2])
            S = _bsh(k, np.asarray(p.exterior.coords)); s_lo, s_hi = S[:, 0].min() - 1e-6, S[:, 0].max() + 1e-6; h_lo, h_hi = S[:, 1].min() - 1e-6, S[:, 1].max() + 1e-6
            ss = np.linspace(s_lo, s_hi, max(2, int(np.ceil((s_hi - s_lo) * W_ / cell)) + 1)); hh = np.linspace(h_lo, h_hi, max(2, int(np.ceil((h_hi - h_lo) * L_ / cell)) + 1))
            parts = []
            for a_, b_ in zip(ss, ss[1:]):
                for c_, d_ in zip(hh, hh[1:]):
                    g_ = p.intersection(_bcell(k, a_, b_, c_, d_))
                    parts += [x for x in getattr(g_, 'geoms', [g_]) if x.geom_type == 'Polygon' and x.area > 1.0]
        V_, F_, idx = [], [], {}
        for q_ in parts:
            for t_ in _cdt(q_).geoms:
                c3 = np.asarray(t_.exterior.coords)[:3]
                e1_, e2_ = c3[1] - c3[0], c3[2] - c3[0]; ar_ = e1_[0] * e2_[1] - e1_[1] * e2_[0]
                if abs(ar_) < 1e-3: continue
                if ar_ < 0: c3 = c3[::-1]
                f_ = []
                for x_, y_ in c3:
                    key_ = (round(x_, 2), round(y_, 2))
                    if key_ not in idx: idx[key_] = len(V_); V_.append((x_, y_))
                    f_.append(idx[key_])
                if len(set(f_)) == 3: F_.append(f_)
        return np.array(V_, float).reshape(-1, 2), np.array(F_, int).reshape(-1, 3)
    def _bplate(p, k, dz0, dz1, vert=False):
        """平面形 p（ベイ k の中、穴あり可）を屋根の面から dz0〜dz1（鉛直に測る）の閉じた板に → manifold。平面のベイは面に直角に押し出す。
        vert：側面を鉛直に（梁のあいだの断熱・合板。10-28：面に直角だと側面が傾いて、梁の上端を屋根の面に上げたら梁に 10〜15 食い込んだ）"""
        V2, F_ = _btri(p, k)
        if not len(F_): return None
        n = len(V2); zb_ = _bz(k, V2) + dz0
        if _BPL20[k] is not None and not vert:
            n_ = _BPL20[k][1]; t_ = (dz1 - dz0) * n_[2]
            Vt = np.r_[np.c_[V2, zb_], np.c_[V2, zb_] + t_ * n_]
        else:
            Vt = np.r_[np.c_[V2, zb_], np.c_[V2, zb_ + (dz1 - dz0)]]
        ed = np.sort(np.vstack([F_[:, [0, 1]], F_[:, [1, 2]], F_[:, [2, 0]]]), axis=1)
        uq, cnt = np.unique(ed, axis=0, return_counts=True); bset = {tuple(e_) for e_ in uq[cnt == 1]}
        side = []
        for a_, b_, c_ in F_:
            for p_, q_ in ((a_, b_), (b_, c_), (c_, a_)):
                if tuple(sorted((p_, q_))) in bset: side += [[p_, q_, q_ + n], [p_, q_ + n, p_ + n]]
        Ft = np.vstack([F_[:, ::-1], F_ + n, np.array(side, int).reshape(-1, 3)])
        o_ = Vt.mean(0)
        M_ = _mf.Manifold(_mf.Mesh(vert_properties=(Vt - o_).astype(np.float32), tri_verts=Ft.astype(np.uint32)))
        if M_.is_empty(): return None
        return M_.translate(o_.tolist()) if hasattr(M_, 'translate') else M_
    def _m2r(M_):
        g_ = M_.to_mesh(); mm_ = r.Mesh()
        for x_, y_, z_ in np.asarray(g_.vert_properties)[:, :3]: mm_.Vertices.Add(float(x_), float(y_), float(z_))
        for a_, b_, c_ in np.asarray(g_.tri_verts): mm_.Faces.AddFace(int(a_), int(b_), int(c_))
        mm_.Normals.ComputeNormals(); mm_.Compact(); return mm_
    def _prism(poly):
        ms_ = []
        for _pg in getattr(poly.buffer(0), 'geoms', [poly.buffer(0)]):
            if _pg.geom_type != 'Polygon' or _pg.area < 1e3: continue
            _t = trimesh.creation.extrude_polygon(_pg, 16000.0); _t.apply_translation([0, 0, -2000.0])
            ms_.append(_mf.Manifold(_mf.Mesh(vert_properties=np.asarray(_t.vertices, np.float32), tri_verts=np.asarray(_t.faces, np.uint32))))
        return _mf.Manifold.batch_boolean(ms_, _mf.OpType.Add) if ms_ else None
    def _by_bay(poly):
        """平面形をベイごとの片に → [(ベイの番号, 片)]"""
        out_ = []
        for k in range(_NB20):
            g_ = poly.intersection(_BPOLY[k])
            out_ += [(k, x) for x in getattr(g_, 'geoms', [g_]) if x.geom_type == 'Polygon' and x.area > 1e3]
        return out_
    # 梁のあいだ：外壁の内面の内側から、架構の線ごとの 2 枚の梁と光の筋の帯（±180）を除いた所
    BANDS = unary_union(PAIR_BANDS)                                   # 10-28：2 枚の梁の平面形を囲む形（上の PAIR_BANDS）
    BANDS = unary_union([BANDS] + [Polygon(extedit.samples(g_, 200)[:, :2]).convex_hull.buffer(1.0) for g_ in _raf()])   # u43.5 の 2 枚（あいだは断熱・合板で埋める。光の筋は無し）
    _RAFB = []                                                         # u43.5 の 2 枚を軸の向きに 3 m 延ばした帯（出し梁を含む。母屋を切るため）
    for g_ in _raf():
        P_ = extedit.samples(g_, 200)[:, :2]; c_ = P_.mean(0); X_ = P_ - c_; ax_ = np.linalg.eigh(X_.T @ X_)[1][:, -1]; nn_ = np.array([-ax_[1], ax_[0]])
        s_ = X_ @ ax_; t_ = X_ @ nn_
        _RAFB.append(Polygon([c_ + ax_ * (s_.min() - 3000) + nn_ * t_.min(), c_ + ax_ * (s_.max() + 3000) + nn_ * t_.min(), c_ + ax_ * (s_.max() + 3000) + nn_ * t_.max(), c_ + ax_ * (s_.min() - 3000) + nn_ * t_.max()]))
    if _RAFB: BANDS = unary_union([BANDS, unary_union(_RAFB).convex_hull])
    L20R = new_layer('20r_西館_屋根の下面の構造用合板（t24、現し）', (214, 190, 150)); a20r = r.ObjectAttributes(); a20r.LayerIndex = L20R
    L20V = new_layer('20v_西館_母屋（杉 60×150 @455、現し）', (196, 160, 118)); a20v = r.ObjectAttributes(); a20v.LayerIndex = L20V
    L20B = new_layer('20b_西館_通気垂木（杉 60×45 @455）', (196, 160, 118))
    roofs20 = []
    for o in m.Objects:                                                     # 屋根の面の網目（add_west_south.py）は平面形だけ使う
        if o.Attributes.LayerIndex != L20 or not isinstance(o.Geometry, r.Mesh): continue
        fp = foot(o.Geometry)
        if fp is None: continue
        roofs20.append(fp); drop.add(str(o.Attributes.Id))
    RP20 = unary_union(roofs20)
    # 10-30（ユーザー 22:20、監修の項 20261030-1431 の追記）：越屋根をやめ、棟から屋根の面に沿う幅 1.6 m（v −0.9〜EASTV、南北の妻の壁の内面のあいだ）を
    #   ガラスの帯に。屋根の板・断熱・合板・通気垂木は帯の所を除く（妻の壁の上と妻の軒の出は屋根のまま棟まで）。帯は下の「棟のガラスの帯」で作る
    BAND_U = (21.15, 50.75)                                                         # 南北の妻の壁の内面（排気のスリット）
    _rpu = [uv(*q_)[0] for g_ in getattr(RP20, 'geoms', [RP20]) for q_ in np.asarray(g_.exterior.coords) if uv(*q_)[1] > EASTV - 0.3]
    BAND_UL, BAND_UH = min(_rpu), max(_rpu)                                         # 10-31：ガラスの帯は屋根の南の端から北の端まで（妻の軒の出の上も）
    BAND_VE = VRIDGE_W + 0.35                                                       # 10-31：東へ同じ面のまま 350 の軒（前の水平な水切りはやめた）
    BAND_HOLE = unary_union([R(BAND_UL - 0.05, BAND_UH + 0.05, EASTV, 0.5, 0.1), R(BAND_U[0], BAND_U[1], SLIT_W, EASTV + 0.01, 0.1)])
    RP20 = RP20.difference(BAND_HOLE).buffer(0)
    INT = RP20.intersection(WSi_W).difference(BANDS)                                   # 梁のあいだ（室内）
    # 太陽光（20p）の範囲：軒先の水切り 150 を残す（10-24、本館と同じ）、越屋根の蓋の西の縁（10-25：−2.85）、光の筋の周り ±0.25
    pv20 = RP20.buffer(-150.0, join_style=2)
    pv20 = pv20.difference(Polygon([xy(u_, 1.0) for u_ in np.arange(19, 53.1, 0.5)] + [xy(u_, -2.85) for u_ in np.arange(53, 18.9, -0.5)]))
    pv20 = pv20.difference(unary_union([strip(cc, ax, nrm, t0 - 200, t1 + 200, -250, 250) for cc, ax, nrm, t0, t1 in slits]))
    a_pv2 = r.ObjectAttributes(); a_pv2.LayerIndex = L20P
    a_up = r.ObjectAttributes(); a_up.LayerIndex = L20; a_up.Name = '野地 t24＋屋根材 40（梁の上、通気垂木の上、軒は通気垂木の先から 150 持ち出し、軒先の見付け 64）'
    _n_up = _npv = 0
    def _parts(g_):
        return [x for x in getattr(g_, 'geoms', [g_]) if x.geom_type == 'Polygon' and x.area > 1e4]
    a_sh = r.ObjectAttributes(); a_sh.LayerIndex = L20; a_sh.Name = '野地 t24（梁の上、通気垂木の上、軒は通気垂木の先から 150 持ち出し）'
    a_up.Name = '屋根材 40（金属、野地の上、軒先の見付けは野地と合わせて 64）'
    def _nsplit(pg_, nmax=28, depth=0, k_=0):
        """10-31（形が素直でない物の点検：30 面を超える板）：輪郭の点（穴も）が nmax を超える平面形を、u の真ん中の放射の線で二つに分ける"""
        pgs_ = [q for q in getattr(pg_, 'geoms', [pg_]) if q.geom_type == 'Polygon' and q.area > 1e3]
        out_ = []
        for q in pgs_:
            nv_ = len(q.exterior.coords) - 1 + sum(len(h.coords) - 1 for h in q.interiors)
            if nv_ <= nmax or depth > 3: out_.append(q); continue
            qs_ = q.simplify(1.0, preserve_topology=True) if _BB20[k_] < 43.4 else q      # 北西のねじれた区間は点を減らさない（段10の線織面に戻らなくなる）
            if qs_.geom_type == 'Polygon' and len(qs_.exterior.coords) - 1 + sum(len(h.coords) - 1 for h in qs_.interiors) <= nmax: out_.append(qs_); continue
            uvs_ = np.array([np.ravel(uv(*c_)) for c_ in np.asarray(q.exterior.coords)]); us_ = uvs_[:, 0]; vs_ = uvs_[:, 1]; um_ = (min(us_) + max(us_)) / 2
            if np.ptp(vs_) > 2.0 * np.ptp(us_):                                # 10-31：v に長い細い板（北の妻の軒の出の合板）は v の真ん中で
                vm_ = (min(vs_) + max(vs_)) / 2
                for a_, b_ in ((min(vs_) - 1.0, vm_), (vm_, max(vs_) + 1.0)):
                    out_ += _nsplit(q.intersection(R(min(us_) - 1.0, max(us_) + 1.0, a_, b_, 0.05)), nmax, depth + 1, k_)
                continue
            for a_, b_ in ((min(us_) - 1.0, um_), (um_, max(us_) + 1.0)):
                out_ += _nsplit(q.intersection(R(a_, b_, -40.0, 4.0, 0.05)), nmax, depth + 1, k_)
        return out_
    for k, p0_ in _by_bay(RP20.difference(SL20)):                        # 野地と屋根材は別の板（太陽光の範囲は平面で分けてから板に。立体の引き算はしない）
      for p_ in _nsplit(p0_, k_=k):
          M_ = _bplate(p_, k, BAT_T, VENT_TOP)
          if M_ is None: log.append(f'  !! 西館の屋根の板が閉じない：ベイ {k}、{p_.area / 1e6:.2f} m²'); continue
          new_objs.append((_m2r(M_), a_sh)); _n_up += 1
          for q_, at_ in [(x, a_pv2) for x0 in _parts(p_.intersection(pv20)) for x in _nsplit(x0, k_=k)] + [(x, a_up) for x0 in _parts(p_.difference(pv20)) for x in _nsplit(x0, k_=k)]:
              # 10-29 昼（監修の項 20261029-0928 の 3）：太陽光（20p）は屋根材（20）と同じ板の押し出し。下の面を野地の上面の 3 上に（ねじれた面を
              # 三角形で近似した野地と 0.1〜1.9 mm 重なり、削る段で 20 に削られて、網目版で閉じない片・退化した三角形になっていた）
              M_ = _bplate(q_, k, VENT_TOP + (3.0 if at_ is a_pv2 else 0.0), RT_W)
              if M_ is None: log.append(f'  !! 西館の屋根材が閉じない：ベイ {k}'); continue
              new_objs.append((_m2r(M_), at_)); _npv += at_ is a_pv2
    # 通気垂木（20b）：梁と断熱の上、軒先（とけらば）の 150 手前まで、光の筋（±0.09 と立ち上がり ±0.15）で切る
    VREG = RP20.buffer(-BAT_IN, join_style=2).union(RP20.intersection(Polygon([xy(u_, 2.0) for u_ in np.arange(21.2, 50.81, 0.2)] + [xy(u_, -3.5) for u_ in np.arange(50.8, 21.19, -0.2)])))
    VREG = VREG.difference(unary_union([strip(cc, ax, nrm, t0 - 100, t1 + 100, -150, 150) for cc, ax, nrm, t0, t1 in slits])).buffer(0)
    a_b20 = r.ObjectAttributes(); a_b20.LayerIndex = L20B; a_b20.Name = '通気垂木 杉 60×45（長ビスで母屋へ）'
    _nb20 = 0
    _RBND = BANDS.buffer(3.0)                                          # 梁（2 枚組・登り梁）の平面形の帯（上の BANDS）
    for k in range(_NB20):
        reg_ = VREG.intersection(_BPOLY[k])
        if reg_.is_empty or reg_.area < 1e5: continue
        C = _BC20[k]; lines_ = []
        if _BPL20[k] is not None:                                            # 平面のスパン：最大傾斜の向き、455 おき
            n_ = _BPL20[k][1]; gd_ = -n_[:2] / np.linalg.norm(n_[:2]); dd_ = np.array([-gd_[1], gd_[0]])
            c0_ = np.asarray(reg_.centroid.coords[0]); pr_ = (np.asarray(reg_.exterior.coords if reg_.geom_type == 'Polygon' else np.vstack([g_.exterior.coords for g_ in reg_.geoms])) - c0_) @ dd_
            a_, b_ = pr_.min(), pr_.max(); t_ = a_ + 180.0
            while t_ < b_ - 100.0:
                lines_.append((c0_ + dd_ * t_ - gd_ * 30000.0, c0_ + dd_ * t_ + gd_ * 30000.0)); t_ += 455.0
        else:                                                                # 双一次のベイ：梁の線に沿う向き（s 一定の線）
            Wm_ = np.linalg.norm(_RWf['ruled_point'](k, 0.5, 1.0)[:2] - _RWf['ruled_point'](k, 0.5, 0.0)[:2])
            if Wm_ < 600.0: continue
            t_ = 180.0
            while t_ < Wm_ - 100.0:
                s_ = t_ / Wm_; lines_.append((_RWf['ruled_point'](k, -0.3, s_)[:2], _RWf['ruled_point'](k, 1.3, s_)[:2])); t_ += 455.0
        for A_, B_ in lines_:
            d_ = (B_ - A_) / np.linalg.norm(B_ - A_); w_ = np.array([-d_[1], d_[0]]) * BAT_W / 2
            # 10-28 夕：梁（2 枚組・登り梁）の上に平行に重なる垂木は、梁の帯（_RBND）にかからない所まで横へずらす（梁の上端は厚みの真ん中で
            # 屋根の面に合わせてあり、北西では面が梁を横切って傾くので、梁の縁の上の垂木が 14〜17 mm 食い込んでいた）
            for o_ in (0.0, 20.0, -20.0, 40.0, -40.0, 60.0, -60.0, 80.0, -80.0, 100.0, -100.0, 120.0, -120.0, 140.0, -140.0, 160.0, -160.0, None):
                if o_ is None: A_ = None; break
                n2_ = w_ / np.linalg.norm(w_) * o_
                if Polygon([A_ + n2_ - w_, B_ + n2_ - w_, B_ + n2_ + w_, A_ + n2_ + w_]).intersection(reg_).intersection(_RBND).area < 1e3:
                    A_, B_ = A_ + n2_, B_ + n2_; break
            if A_ is None: continue
            # 10-29（監修の項 20261028-2345）：一本ずつ真っすぐな 60×45 の箱（前は双一次の面に沿う網目で約1°ずつ折れていた）。芯の線を区域で切り、
            # 下の面＝芯の線の両端の屋根の面の高さを結ぶ平らな面（双一次の面の s 一定の線はまっすぐなので、芯は面の上に載る）、上は鉛直に 45、小口は芯に直角
            cl_ = LineString([A_, B_]).intersection(reg_)
            for g_ in getattr(cl_, 'geoms', [cl_]):
                if g_.geom_type != 'LineString' or g_.length < 333.0: continue
                E0_, E1_ = np.asarray(g_.coords)[0], np.asarray(g_.coords)[-1]
                z0_, z1_ = _bz(k, np.array([E0_, E1_]))
                Vb_ = np.array([[*(E0_ - w_), z0_], [*(E1_ - w_), z1_], [*(E1_ + w_), z1_], [*(E0_ + w_), z0_]])
                Vt_ = np.r_[Vb_, Vb_ + [0.0, 0.0, BAT_T]]
                Fb_ = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
                if trimesh.Trimesh(Vt_ - Vt_.mean(0), Fb_, process=False).volume < 0: Fb_ = Fb_[:, ::-1]
                mm_ = r.Mesh()
                for x_, y_, z_ in Vt_: mm_.Vertices.Add(float(x_), float(y_), float(z_))
                for f_ in Fb_: mm_.Faces.AddFace(int(f_[0]), int(f_[1]), int(f_[2]))
                mm_.Normals.ComputeNormals(); mm_.Compact()
                new_objs.append((mm_, a_b20)); _nb20 += 1
    # 断熱 t150（20）と合板 t24（20r）：梁のあいだ（室内）、ベイごとの板
    a_in20 = r.ObjectAttributes(); a_in20.LayerIndex = L20; a_in20.Name = '断熱 木質繊維ボード t150（梁のあいだ、上面＝梁の上端）'
    a20r.Name = '構造用合板 t24（母屋の上、天井に現す、気密はこの上）'
    for k, p_ in [(k0_, q_) for k0_, p0_ in _by_bay(INT) for q_ in [x_ for x_ in getattr(p0_, 'geoms', [p0_]) if x_.geom_type == 'Polygon'] if not q_.buffer(-60.0).is_empty]:     # 10-31（形が素直でない物：梁18 の外の板の外 u50.74〜50.85、北の妻の壁の中の幅 110 のねじれた細い合板 58 面）：幅 120 未満の細い片は作らない
        for dz0_, dz1_, at_ in ((-INS_T, 0.0, a_in20), (-INS_T - PLY_T, -INS_T, a20r)):
            M_ = _bplate(p_, k, dz0_, dz1_, vert=True)
            if M_ is not None: new_objs.append((_m2r(M_), at_))
    log.append(f'西館：梁の上の層を本館と同じ作り方に（10-28）：通気垂木 {_nb20} 本（20b、60×45 @455、軒先の 150 手前まで）、野地＋屋根材 64 の板 {_n_up} 片・太陽光 {_npv} 片（ベイごと、'
               f'平面のベイ {sum(1 for x in _BPL20 if x is not None)}／{_NB20}、軒は 150 持ち出し、見付け 64）')
    _purl = []; _eave = []
    # 10-29 夜：軒の下の母屋は軒先の 190 手前まで（木口は上の _BCX で鼻母屋の横の面まで延ばす）。10-29 昼（監修の項 20261029-0928 の 4）：軒の下の母屋は軒先の 100 手前まで（母屋の断面は屋根の面に直角で、北西の軒先の折れの所で軒樋に 0.8〜1.5 L 入っていた）
    EAVEZ = RP20.buffer(-190.0, join_style=2).difference(WS_W).difference(BANDS).intersection(Polygon([xy(u_, -1.0) for u_ in np.arange(21.2, 48.31, 0.25)] + [xy(u_, -30.0) for u_ in np.arange(48.3, 21.19, -0.25)]))
    _vr = SLIT_W - 0.03                                                 # 10-31：いちばん上の母屋はスリットの西の縁の材の脇
    while _vr > -16.5:
        _us = np.arange(18.0, 54.01, 0.25)
        _rp = Polygon([xy(u_, _vr + 0.03) for u_ in _us] + [xy(u_, _vr - 0.03) for u_ in _us[::-1]])
        _purl.append(_rp.intersection(INT)); _eave.append(_rp.intersection(EAVEZ))
        _vr -= 0.455
    # 母屋は一本ずつの長方形の押し出し（10-27夜、ユーザー：母屋が長方形の押し出し以外になっているのは変）。前は、屋根の面に沿う板を
    # 弧に沿う帯で鉛直に切り出して一つの網目にまとめていたので、断面が平行四辺形・上下の面が曲面の片の集まりになっていた。
    # 今：梁と梁のあいだ（INT・軒の下は EAVEZ）を通る弦をまっすぐな軸にし、その所の屋根の面（梁の上端）に当てはめた平面の上に、
    # 上の面を合板の下面（室内、梁の上端の 174 下）か梁の上端（軒の下）にそろえ、幅 60 × せい 150（屋根の面に直角）の断面で押し出す。
    from shapely.geometry import MultiPoint as _MPt
    _BCX = unary_union([BANDS] + [_MPt(tri.tri_extrusion(c_).reshape(-1, 3)[:, :2]).convex_hull for c_ in _CANT])     # 梁の帯と出し梁（端の架構の内の 1 枚にも出し梁、10-29 夜）
    _BCX0 = _BCX; _BCX = _BCX.union(WSL.buffer(-100.0, join_style=2).difference(WSL.buffer(-160.0, join_style=2)))    # 鼻母屋（軒先から 100〜160）：軒の下の母屋の木口は鼻母屋の横の面に当てる（10-29 夜、u45〜48 の離れ 26）
    _PREC = []                                                       # 母屋の記録（妻の軒の出へ延ばす、10-29 夜）
    _NPWDG = [0]                                                     # 母屋の木口の楔の受け材の数（10-30）
    _BTMW = []                                                       # 梁の板の立体（母屋の下の縁が本当に板に入っているかを見る、10-30）
    for g_ in [cur_g(o) for o in m.Objects if o.Attributes.LayerIndex == L22B] + _raf():
        if not isinstance(g_, r.Extrusion): continue
        T_ = tri.tri_extrusion(g_)
        if len(T_): tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(); _BTMW.append(tm_)
    _KETA_SKIP = []                                                  # 桁に重なるので作らなかった母屋（10-30）
    _GIRM = [(M_, tm_) for M_, tm_ in ((_tm_mf(_ext_tm(gi_[1])), _ext_tm(gi_[1])) for gi_ in _GIR) if M_ is not None]
    # 10-30（梁18）：板の網目が閉じていないと contains がいつも False になり、楔の直しが抜けた（桁が u48 の板を通るようになって穴が増え、
    #   北西の母屋の木口が u48 の板に最大 約50 入ったまま、板に母屋の穴が開いた）。閉じていない板は、外の輪郭（穴は見ない）と厚みで見る
    _BPLW = []
    for g_ in [cur_g(o) for o in m.Objects if o.Attributes.LayerIndex == L22B] + _raf():
        if not isinstance(g_, r.Extrusion): continue
        try:
            pl_ = g_.GetProfilePlane(0.0); O_ = np.array([pl_.Origin.X, pl_.Origin.Y, pl_.Origin.Z])
            X_ = np.array([pl_.XAxis.X, pl_.XAxis.Y, pl_.XAxis.Z]); Y_ = np.array([pl_.YAxis.X, pl_.YAxis.Y, pl_.YAxis.Z])
            a_, b_ = g_.PathStart, g_.PathEnd; D_ = np.array([b_.X - a_.X, b_.Y - a_.Y, b_.Z - a_.Z]); L_ = float(np.linalg.norm(D_)); D_ = D_ / L_
            nc_ = g_.Profile3d(0, 0.0).ToNurbsCurve(); dm_ = nc_.Domain
            Pp_ = np.array([[q.X, q.Y, q.Z] for q in (nc_.PointAt(t) for t in np.linspace(dm_.T0, dm_.T1, 800))])
            pg_ = Polygon(np.c_[(Pp_ - O_) @ X_, (Pp_ - O_) @ Y_]).buffer(0)
            bb_ = g_.GetBoundingBox()
            _BPLW.append((np.array([bb_.Min.X, bb_.Min.Y, bb_.Min.Z]), np.array([bb_.Max.X, bb_.Max.Y, bb_.Max.Z]), O_, X_, Y_, D_, L_, pg_))
        except Exception:
            continue
    def _in_beam(P3_):
        for t_ in _BTMW:
            if np.all(t_.bounds[0] - 1.0 <= P3_) and np.all(P3_ <= t_.bounds[1] + 1.0) and t_.is_watertight and t_.contains([P3_])[0]: return True
        for lo_, hi_, O_, X_, Y_, D_, L_, pg_ in _BPLW:
            if not (np.all(lo_ - 1.0 <= P3_) and np.all(P3_ <= hi_ + 1.0)): continue
            w_ = P3_ - O_; t_ = float(w_ @ D_)
            if -0.5 <= t_ <= L_ + 0.5 and pg_.contains(Point(float((w_ - D_ * t_) @ X_), float((w_ - D_ * t_) @ Y_))): return True
        return False
    def _purl_x(A2, B2, ztop, name_):
        """平面の A2→B2（水平）、上の面の中心の高さ ztop の 60×150 の押し出し（断面は屋根の面に直角）"""
        A3 = np.r_[A2, ztop]; B3 = np.r_[B2, ztop]; L_ = float(np.linalg.norm(B3 - A3)); d3 = (B3 - A3) / L_
        M2 = (A2 + B2) / 2; e_ = 50.0
        gx = (_RWf['roof_f'](M2[0] + e_, M2[1]) - _RWf['roof_f'](M2[0] - e_, M2[1])) / (2 * e_)
        gy = (_RWf['roof_f'](M2[0], M2[1] + e_) - _RWf['roof_f'](M2[0], M2[1] - e_)) / (2 * e_)
        N_ = np.array([-gx, -gy, 1.0]); N_ = N_ - d3 * (N_ @ d3); N_ /= np.linalg.norm(N_)
        if '軒の下' in name_ and uv(*M2)[0] > 43.0:                          # 10-31（力の道：木口と梁の延長の横の面に 14 のすき間）：北西の軒の下の母屋は断面を鉛直に
            #   （木口が鉛直な梁の延長の横の面にそのまま当たる）。上の面は水平なので、屋根の面の傾きの分（幅 60 の半分）だけ下げて屋根の板に食い込ませない
            N_ = np.array([0.0, 0.0, 1.0]); _gs = float(np.hypot(gx, gy) * abs(np.cross(np.r_[d3[:2], 0.0] / max(1e-9, np.linalg.norm(d3[:2])), [gx, gy, 0.0])[2]) / max(1e-9, np.hypot(gx, gy)))
            A3 = A3 - [0.0, 0.0, 30.0 * _gs]; B3 = B3 - [0.0, 0.0, 30.0 * _gs]
        s3 = np.cross(d3, N_); s3 /= np.linalg.norm(s3)
        # 10-28：母屋の両端を、断面の 4 隅の平面形が梁の帯（BANDS）にかからない所まで縮める（母屋は梁に斜めに当たり、断面は屋根の面に
        # 直角なので、芯の線だけを帯で切ると端の隅が梁に数 mm〜30 食い込んでいた。梁の上端を屋根の面に上げて見えるようになった）
        for _it in range(12):
            _off = [s3 * 30.0, -s3 * 30.0, -s3 * 30.0 - N_ * PUR_T, s3 * 30.0 - N_ * PUR_T]
            _fa = [A3[:2] + o_[:2] for o_ in _off]; _fb = [B3[:2] + o_[:2] for o_ in _off]
            _x = Polygon(_fa + _fb).convex_hull.intersection(BANDS)
            if _x.area < 1.0: break
            _ea = _eb = 0.0
            for _g in getattr(_x, 'geoms', [_x]):
                if _g.area < 0.5: continue
                _c = np.array(_g.centroid.coords[0]); _e = _g.area / 60.0 + 1.0
                if np.linalg.norm(_c - A3[:2]) < np.linalg.norm(_c - B3[:2]): _ea = max(_ea, _e)
                else: _eb = max(_eb, _e)
            A3 = A3 + d3 * _ea; B3 = B3 - d3 * _eb
            L_ = float(np.linalg.norm(B3 - A3))
            if L_ < 300.0: return 0
        # 10-29 夜（監修の項 2027 の追記、力の道）：木口は梁の面に沿って斜めに切る（梁に斜めに当たる母屋は角だけが梁に触れ、すき間 30〜44 だった）。
        #   上の面の 4 隅を、両脇（±30）の線ごとに梁の帯（BANDS）の縁まで延ばし、屋根の面に直角な向き N_ に押し出す（梁の面は鉛直で N_ をほぼ含む）
        T4_ = []
        for end_, P0_, dd_ in ((0, A3, -d3), (1, B3, d3)):
            for w_ in (30.0, -30.0):
                q0_ = P0_ + s3 * w_; t_ = 0.0
                ln_ = LineString([q0_[:2] - dd_[:2] * 20.0, q0_[:2] + dd_[:2] * 150.0]).intersection(_BCX)
                if not ln_.is_empty:
                    pts_ = [np.array(c_) for g_ in getattr(ln_, 'geoms', [ln_]) for c_ in getattr(g_, 'coords', [])]
                    if pts_:
                        tt_ = min(float((c_ - q0_[:2]) @ dd_[:2]) / float(np.linalg.norm(dd_[:2]) ** 2) for c_ in pts_)
                        if -20.0 <= tt_ <= 150.0: t_ = max(tt_ - 0.05, 0.0)
                T4_.append(q0_ + dd_ * t_)
        TOP_ = [T4_[0], T4_[1], T4_[3], T4_[2]]                                  # A+30, A−30, B−30, B+30
        # 10-30（監修の項 0552 の西館の残り、力の道）：木口は屋根の面に直角な向き N_ に押し出すので、梁の面（鉛直）に斜めに当たる北西の母屋は
        #   上の縁が梁の面に触れても下の縁が梁の板に最大 約 50 入っていた（端の架構 u48 では板に母屋の穴が開き、木口が柱から 63 離れた）。
        #   下の縁が梁の面にちょうど触れる所まで縮め、上の縁と梁の面のあいだのすき間に楔の受け材（平らな面だけの三角柱の押し出し、22b）を足す
        _wdg = []
        for (i0_, i1_), dd_ in (((0, 1), -d3), ((2, 3), d3)):
            dd2_ = dd_[:2] / np.linalg.norm(dd_[:2]); pen_ = 0.0
            for c_ in (TOP_[i0_], TOP_[i1_]):
                b2_ = (c_ - N_ * PUR_T)[:2]
                if not _BCX.contains(Point(*b2_)) or _BCX.contains(Point(*(b2_ - dd2_ * 200.0))): continue
                if not _in_beam(c_ - N_ * (PUR_T - 2.0) - dd_ * 2.0): continue           # 板が無い高さ（梁の端の丸みの下など）は前のまま
                lo_, hi_ = 0.0, 200.0                                             # lo_：板の中、hi_：板の外
                for _ in range(30):
                    md_ = (lo_ + hi_) / 2
                    if _BCX.contains(Point(*(b2_ - dd2_ * md_))): lo_ = md_
                    else: hi_ = md_
                pen_ = max(pen_, hi_)
            if pen_ < 10.0 or '軒の下' in name_: continue                          # 10 未満（u21〜42 の 3〜6）は前のまま。軒の下の母屋は出し梁（10-31 から梁の延長）の横の面に当てる（縮めない）
            TOP_[i0_] = TOP_[i0_] - dd_ * pen_; TOP_[i1_] = TOP_[i1_] - dd_ * pen_
            Pt_ = (TOP_[i0_] + TOP_[i1_]) / 2; tp_ = TOP_[i0_] - TOP_[i1_]; Lw_ = float(np.linalg.norm(tp_)); tp_ = tp_ / Lw_
            Pb_ = Pt_ - N_ * PUR_T
            nb_ = np.cross(tp_, [0.0, 0.0, 1.0]); nb_ /= np.linalg.norm(nb_); nb_ = nb_ if nb_ @ dd_ > 0 else -nb_     # 梁の面（鉛直、上の縁の向きを含む）
            wq_ = np.cross(N_, tp_); wq_ /= np.linalg.norm(wq_); wq_ = wq_ if wq_ @ dd_ > 0 else -wq_                # 母屋の上の面の中、上の縁に直角
            lam_ = float(nb_ @ (Pb_ - Pt_)) / float(nb_ @ wq_)
            if not (1.0 < lam_ < 250.0): continue
            Qw_ = Pt_ + wq_ * lam_                                                # 上の面と梁の面の交わる線の上
            _wdg.append(([Pb_ - tp_ * Lw_ / 2, Pt_ - tp_ * Lw_ / 2, Qw_ - tp_ * Lw_ / 2], Lw_, (Pb_ + Pt_ + Qw_) / 3))
        crv = r.Polyline([r.Point3d(*map(float, c_)) for c_ in TOP_ + [TOP_[0]]]).ToNurbsCurve()
        best = None; tgt_ = (A3 + B3) / 2 - N_ * PUR_T / 2
        for ex_ in (r.Extrusion.Create(crv, PUR_T, True), r.Extrusion.Create(crv, -PUR_T, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2, (bb_.Min.Z + bb_.Max.Z) / 2]) - tgt_)
            if best is None or dm < best[0]: best = (dm, ex_)
        if best is None: return 0
        # 10-30（ユーザー 15:06）：斜めのスパン（u45〜48）で斜めの桁の真上を平行に走って桁に重なる母屋は作らない。桁が母屋を兼ね、
        #   桁の上に合板の下面（この母屋の上の面）まで届く飼木を置く（下の _KETA_SKIP、母屋と同じ幅 60、455 おき）
        if '梁から梁へ' in name_ and _GIRM:
            Mp_ = _tm_mf(_ext_tm(best[1]))
            if Mp_ is not None:
                for Mg_, tmg_ in _GIRM:
                    if (Mp_ ^ Mg_).volume() > 5e5:
                        _KETA_SKIP.append(dict(T=[np.array(c_) for c_ in TOP_], d3=d3, s3=s3, N=N_, tm=tmg_, name=name_)); return 0
        at_ = r.ObjectAttributes(); at_.LayerIndex = L20V; at_.Name = name_
        _XNEW.append((best[1], at_)); _PREC.append(dict(i=len(_XNEW) - 1, T=[np.array(c_) for c_ in TOP_], d3=d3, s3=s3, N=N_, name=name_))
        for tri3_, Lw_, cen_ in _wdg:                                             # 楔の受け材：三角形を上の縁の向きに Lw_ 押し出す
            crv_ = r.Polyline([r.Point3d(*map(float, c_)) for c_ in tri3_ + [tri3_[0]]]).ToNurbsCurve(); bw_ = None
            for ex_ in (r.Extrusion.Create(crv_, Lw_, True), r.Extrusion.Create(crv_, -Lw_, True)):
                if ex_ is None: continue
                bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2, (bb_.Min.Z + bb_.Max.Z) / 2]) - cen_)
                if bw_ is None or dm < bw_[0]: bw_ = (dm, ex_)
            if bw_ is None: continue
            atw_ = r.ObjectAttributes(); atw_.LayerIndex = L22B; atw_.Name = '梁の受け材（楔、斜めに当たる母屋の木口と梁の面のすき間、平らな面だけ）'
            _XNEW.append((bw_[1], atw_)); _NPWDG[0] += 1
        return 1
    # 母屋は一本ずつの長方形の押し出し（10-27夜、ユーザー：母屋が長方形の押し出し以外になっているのは変）。屋根の面（roofw）は、屋根の線（梁）の
    # 同じ高さの点を水平のまっすぐな線で結んだ面なので、母屋はその線の上にちょうど載る。ベイごとに、長い方の梁で 455 おき、越屋根の西の縁の外から軒先まで。
    # 室内は上の面＝合板の下面（梁の上端の 174 下）、軒の下は梁の上端にそろえて落とし込む。梁・登り梁の帯（BANDS）と外壁の内面で切る。
    # 10-28（ユーザー：屋根はそもそも平面で作る）：スパン8〜14（u21〜42）は屋根がスパンごとの平面（roofw の SPANS）。母屋は平面の等高線
    # （水平・軒に平行なまっすぐな線）の上に、勾配の向きに 455 おき（軒の線から数える）、越屋根の西の縁の外から軒先の 1 m 外まで。
    # 北西の角（u42〜51）は双一次の面のまま、となりの梁の同じ高さの点を結ぶ（下）。
    _B = _RWf['BAYS']; _npur = 0; _npur_pl = 0; _dpur = 0.0
    for ua_, ub_, kind_, cf_ in _RWf['SPANS']:
        if kind_ != 'plane' or ub_ <= 21.0 + 1e-6: continue                  # 10-28 夕：平面のスパンは無い（南のけらばの接平面は母屋なし）
        px_, py_, c0_, c1_, c2_ = cf_; g_ = float(np.hypot(c1_, c2_)); gd_ = np.array([c1_, c2_]) / g_; dd_ = np.array([-gd_[1], gd_[0]])
        _sp = Polygon([xy(ua_, 3.0), xy(ua_, -30.0), xy(ub_, -30.0), xy(ub_, 3.0)])
        _zf = lambda q: c0_ + c1_ * (q[0] - px_) + c2_ * (q[1] - py_)
        ztop_ = min(_zf(np.array(xy(ua_ + 0.25, EASTV - 0.06), float).ravel()), _zf(np.array(xy(ub_ - 0.25, EASTV - 0.06), float).ravel()))
        zlo_ = 4650.0 - g_ * 1000.0; dz_ = g_ * 455.0
        z_ = 4650.0 + np.floor((ztop_ - 4650.0) / dz_) * dz_
        while z_ > zlo_:
            p0_ = np.array([px_, py_]) + gd_ * (z_ - c0_) / g_                     # 等高線 z_ の上の点
            ln2 = LineString([p0_ - dd_ * 40000.0, p0_ + dd_ * 40000.0]).intersection(_sp)
            if not ln2.is_empty and ln2.geom_type == 'LineString':
                for reg_, off_, nm_ in ((INT, -INS_T - PLY_T, '梁から梁へ'), (EAVEZ, 0.0, '軒の下、梁の上端にそろえる')):
                    x_ = ln2.intersection(reg_)
                    for sg_ in getattr(x_, 'geoms', [x_]):
                        if sg_.geom_type != 'LineString' or sg_.length < 300.0: continue
                        if reg_ is INT and max(uv(*c_)[1] for c_ in (sg_.coords[0], sg_.coords[-1])) > SLIT_W - 0.04: continue   # 10-31：排気のスリットで切れて梁に届かない母屋は置かない
                        A2_, B2_ = np.array(sg_.coords[0]), np.array(sg_.coords[-1])
                        for q_ in (A2_, B2_, (A2_ + B2_) / 2): _dpur = max(_dpur, abs(_RWf['roof_f'](*q_) - z_))
                        n_ = _purl_x(A2_, B2_, float(z_) + off_, f'母屋 杉 60×150（水平、スパン{int(round((ua_ - 21) / 3)) + 8}の平面の等高線、高さ {z_ / 1000:.2f}、{nm_}）')
                        _npur += n_; _npur_pl += n_
            z_ -= dz_
    for k in range(0, len(_B) - 1):                                          # 10-28 夕：西の面（u21〜42）も双一次。光の筋の細いベイ（±0.09）は除く
        if _B[k + 1] - _B[k] < 1.0: continue
        (Ra, Ea), (Rb, Eb) = _RWf['beam_line'](_B[k]), _RWf['beam_line'](_B[k + 1])
        Lm = max(np.linalg.norm(Ea - Ra), np.linalg.norm(Eb - Rb))
        h0 = max(_RWf['ruled_hs'](*np.array(xy(_B[k] + 0.25, EASTV - 0.06), float).ravel())[0],
                 _RWf['ruled_hs'](*np.array(xy(_B[k + 1] - 0.25, EASTV - 0.06), float).ravel())[0])
        for h in np.arange(h0, 1.0 + 1000.0 / Lm, 455.0 / Lm):
            Pa = _RWf['ruled_point'](k, h, 0.0); Pb = _RWf['ruled_point'](k, h, 1.0)        # 梁の芯から芯（帯で切る）
            ln2 = LineString([Pa[:2], Pb[:2]])
            for reg_, off_, nm_ in ((INT, -INS_T - PLY_T, '梁から梁へ'), (EAVEZ, 0.0, '軒の下、梁の上端にそろえる')):
                x_ = ln2.intersection(reg_)
                for sg_ in getattr(x_, 'geoms', [x_]):
                    if sg_.geom_type != 'LineString' or sg_.length < 300.0: continue
                    if reg_ is INT and max(uv(*c_)[1] for c_ in (sg_.coords[0], sg_.coords[-1])) > SLIT_W - 0.04: continue   # 10-31：排気のスリットで切れて梁に届かない母屋は置かない
                    for q_ in (np.array(sg_.coords[0]), np.array(sg_.coords[-1]), np.array(sg_.interpolate(0.5, normalized=True).coords[0])):
                        _dpur = max(_dpur, abs(_RWf['roof_f'](*q_) - float(Pa[2])))
                    _npur += _purl_x(np.array(sg_.coords[0]), np.array(sg_.coords[-1]), float(Pa[2]) + off_,
                                     f'母屋 杉 60×150（水平、u{_B[k]:g}〜{_B[k + 1]:g}、高さ {Pa[2] / 1000:.2f}、{nm_}）')
    # 妻の軒の出（10-29 夜、ユーザー 22 時過ぎ・23 時過ぎ）：端の架構の外の妻の軒の出（南 u20.70〜21.16、北西 u48〜51.3、約 0.45）は、母屋を外へ
    #   片持ちで延ばし（先は軒先から 100、軒先の線に直角に測る）、先の上に屋根の板（野地の下面）まで届く飼木（母屋と同じ幅 60、長さ 150、直方体の押し出し）を
    #   載せて受ける。南で端の架構の 2 枚を貫く所は板に母屋の穴（全周 10）を開け、外壁はその所を欠く。柱に当たる母屋は延ばさない
    _CLm = WSL.buffer(-100.0, join_style=2)
    _CLm = max(getattr(_CLm, 'geoms', [_CLm]), key=lambda q: q.area)
    _colM = [(w, _tm_mf(_ext_tm(w[4]))) for w in _WOOD if w[2] == L22A and (w[5] < 21.7 or w[5] > 47.7)]
    _colM = [(w, M_) for w, M_ in _colM if M_ is not None]
    # 10-30（梁18、ユーザー）：北の端の架構（u50.565、2 枚 u50.39〜50.74）の外の妻の軒の出（u50.75〜51.3）も、南と同じく母屋を端の架構の 2 枚を
    #   貫いて（板に母屋の穴）片持ちで延ばす。北では端の架構の帯だけは越えてよい（ほかの梁・出し梁の帯に当たる母屋は延ばさない）
    _BCX0N = _BCX0.difference(Polygon([xy(u_, -0.5) for u_ in np.arange(U_F18 - 0.3, U_F18 + 0.3001, 0.05)] + [xy(u_, -16.0) for u_ in np.arange(U_F18 + 0.3, U_F18 - 0.3001, -0.05)]))
    _n_gx = _n_gskip = 0; _GX_TM = []; _GX_M = []
    def _box_top(T4, N_, h_, up_):
        """上の面（または下の面）の 4 隅 T4 から N_ の向きに h_ の押し出し（up_：上へ）"""
        crv = r.Polyline([r.Point3d(*map(float, c_)) for c_ in T4 + [T4[0]]]).ToNurbsCurve(); best = None
        tgt_ = np.mean(T4, axis=0) + N_ * (h_ / 2 if up_ else -h_ / 2)
        for ex_ in (r.Extrusion.Create(crv, h_, True), r.Extrusion.Create(crv, -h_, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2, (bb_.Min.Z + bb_.Max.Z) / 2]) - tgt_)
            if best is None or dm < best[0]: best = (dm, ex_)
        return None if best is None else best[1]
    # 10-31（ユーザー：母屋は本館のように梁と梁のあいだだけ、梁から飛び出さない）：妻の軒の出・南西の角の母屋の延長と飼木はやめた
    #   （南西の鼻母屋は壁の中の柱と腕木が受ける、7271768）。延ばす母屋が無いので、端の架構の板の穴・外壁の欠きも作らない
    # 10-30（ユーザー 15:06）：桁に重なるので作らなかった母屋の代わりに、桁の上に飼木（幅 60、長さ 150、455 おき）。上の面は母屋の上の面（合板の下面）、
    #   下の面は桁の上の頂（屋根の面に直角な向き N の、いちばん高い所）にちょうど触れる。横の位置は桁の頂の真上にそろえる
    _n_kk = 0
    for ks_ in _KETA_SKIP:
        T_ = ks_['T']; d3 = ks_['d3']; s3 = ks_['s3']; N_ = ks_['N']; tmg_ = ks_['tm']
        A_ = (T_[0] + T_[1]) / 2; B_ = (T_[2] + T_[3]) / 2; Lk_ = float((B_ - A_) @ d3)
        rmi_ = trimesh.ray.ray_triangle.RayMeshIntersector(tmg_)
        def _hit(P_):
            P_ = np.atleast_2d(P_); loc_, ir_, _ = rmi_.intersects_location(P_, np.tile(-N_, (len(P_), 1)), multiple_hits=False)
            h_ = np.full(len(P_), np.inf)
            for l_, k_ in zip(loc_, ir_): h_[k_] = min(h_[k_], float((P_[k_] - l_) @ N_))
            return h_
        nk_ = max(1, int(np.floor((Lk_ - 150.0) / 455.0)) + 1); t0_ = (Lk_ - 150.0 - (nk_ - 1) * 455.0) / 2
        for j_ in range(nk_):
            tc_ = t0_ + 75.0 + j_ * 455.0; Pc_ = A_ + d3 * tc_
            ss_ = np.arange(-200.0, 200.1, 5.0); hs_ = _hit(np.array([Pc_ + s3 * s_ for s_ in ss_]))
            if not np.isfinite(hs_).any(): continue
            Pc_ = Pc_ + s3 * float(ss_[int(np.argmin(hs_))])                     # 桁の頂の真上
            G_ = np.array([Pc_ + d3 * a_ + s3 * b_ for a_ in np.linspace(-75.0, 75.0, 7) for b_ in np.linspace(-30.0, 30.0, 5)])
            h_ = float(np.min(_hit(G_)))
            if not np.isfinite(h_) or h_ < 3.0 or h_ > 400.0: continue
            T4_ = [Pc_ - d3 * 75.0 + s3 * 30.0, Pc_ - d3 * 75.0 - s3 * 30.0, Pc_ + d3 * 75.0 - s3 * 30.0, Pc_ + d3 * 75.0 + s3 * 30.0]
            e2_ = _box_top(T4_, N_, h_, False)
            if e2_ is None: continue
            at2_ = r.ObjectAttributes(); at2_.LayerIndex = L20V; at2_.Name = f'飼木 杉 60×{h_:.0f}×150（斜めの桁の上、桁が母屋を兼ね、合板を受ける）'
            _XNEW.append((e2_, at2_)); _n_kk += 1
    log.append(f'西館：斜めの桁に重なる母屋 {len(_KETA_SKIP)} 本を作らず（桁が兼ねる）、桁の上に飼木 {_n_kk} 個（{"、".join(k_["name"][:40] for k_ in _KETA_SKIP)}）')
    # 母屋が貫く端の架構の板に穴（桁と同じ作り方、全周 10）、外壁を欠く
    if _GX_TM:
        _GTM_save = _GTM; _GTM = _GTM + _GX_TM
        for w in _WOOD:
            if w[2] != L22B or not (w[5] < 21.7 or w[5] > 47.7) or '出し梁' in w[3]: continue
            e_, _a, _b, _c = _rebuild_holes(w[4], False, bear=(w[3] == NAME_RAF))
            if e_ is not None and _b: _wset(w, e_)
        _GTM = _GTM_save
        _GXU = _mf.Manifold.batch_boolean(_GX_M, _mf.OpType.Add); _nwg = 0
        for k_, (mm0_, at0_) in enumerate(list(new_objs)):
            if at0_.LayerIndex != L21W: continue
            T_w = tris(mm0_)
            if not len(T_w): continue
            tm_w = trimesh.Trimesh(T_w.reshape(-1, 3), np.arange(len(T_w) * 3).reshape(-1, 3)); tm_w.merge_vertices(digits_vertex=1)
            if not tm_w.is_watertight:                                       # 10-30（梁18）：出し梁で欠いた片は 0.1 mm で丸めると近い点がつぶれて閉じない。丸めずに
                tm_w = trimesh.Trimesh(T_w.reshape(-1, 3), np.arange(len(T_w) * 3).reshape(-1, 3)); tm_w.merge_vertices()
            if not tm_w.is_watertight: continue
            M_w = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(tm_w.vertices, np.float32), tri_verts=np.asarray(tm_w.faces, np.uint32)))
            if M_w.is_empty(): continue
            M2 = M_w - _GXU
            if abs(M2.volume() - M_w.volume()) < 1e3: continue
            g_ = M2.to_mesh(); mm_ = r.Mesh()
            for x_, y_, z_ in np.asarray(g_.vert_properties)[:, :3]: mm_.Vertices.Add(float(x_), float(y_), float(z_))
            for a__, b__, c__ in np.asarray(g_.tri_verts): mm_.Faces.AddFace(int(a__), int(b__), int(c__))
            mm_.Normals.ComputeNormals(); mm_.Compact(); new_objs[k_] = (mm_, at0_); _nwg += 1
        for o in m.Objects:
            if o.Attributes.LayerIndex != L21W or not isinstance(o.Geometry, r.Mesh) or str(o.Attributes.Id) in drop: continue
            T_w = tris(o.Geometry)
            if not len(T_w): continue
            tm_w = trimesh.Trimesh(T_w.reshape(-1, 3), np.arange(len(T_w) * 3).reshape(-1, 3)); tm_w.merge_vertices(digits_vertex=1)
            if not tm_w.is_watertight: continue
            M_w = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(tm_w.vertices, np.float32), tri_verts=np.asarray(tm_w.faces, np.uint32)))
            if M_w.is_empty(): continue
            M2 = M_w - _GXU
            if abs(M2.volume() - M_w.volume()) < 1e3: continue
            g_ = M2.to_mesh(); mm_ = r.Mesh()
            for x_, y_, z_ in np.asarray(g_.vert_properties)[:, :3]: mm_.Vertices.Add(float(x_), float(y_), float(z_))
            for a__, b__, c__ in np.asarray(g_.tri_verts): mm_.Faces.AddFace(int(a__), int(b__), int(c__))
            mm_.Normals.ComputeNormals(); mm_.Compact()
            drop.add(str(o.Attributes.Id)); new_objs.append((mm_, o.Attributes)); _nwg += 1
        log.append(f'西館：妻の軒の出へ母屋を片持ちで延ばした {_n_gx} 端（柱に当たり延ばさない {_n_gskip}）、飼木、外壁 {_nwg} 片を欠いた')
    # 軒先の母屋（鼻母屋、10-29 夕、監修の項 1530：出し梁の先端は軒の母屋を受ける）：となりの架構の出し梁の先（2 枚の平均、先から 30 内＝母屋の外の面が
    # 出し梁の先にそろう）を結ぶまっすぐな 60×150、上の面は両端の屋根の面（軒の高さは一定なのでほぼ水平、南西の角だけ上がる）。ほかの軒の下の母屋は軒先の 250 手前まで（重ならない）
    _tipf = {}
    for p_, d_ in _CTIP: _tipf.setdefault(_fk3(uv(*p_)[0]), []).append((p_, d_))
    _tk = sorted(_tipf); _n_hana = 0
    def _purl_e(A2, B2, zA, zB, name_):
        """_purl_x と同じ断面（60×150、屋根の面に直角）で、端を縮めない。上の面の高さは両端でそれぞれ（南西の角では軒の先が上がる）"""
        A3 = np.r_[A2, zA]; B3 = np.r_[B2, zB]; L_ = float(np.linalg.norm(B3 - A3)); d3 = (B3 - A3) / L_; M2 = (A2 + B2) / 2; e_ = 50.0
        gx = (_RWf['roof_f'](M2[0] + e_, M2[1]) - _RWf['roof_f'](M2[0] - e_, M2[1])) / (2 * e_); gy = (_RWf['roof_f'](M2[0], M2[1] + e_) - _RWf['roof_f'](M2[0], M2[1] - e_)) / (2 * e_)
        N_ = np.array([-gx, -gy, 1.0]); N_ = N_ - d3 * (N_ @ d3); N_ /= np.linalg.norm(N_); s3 = np.cross(d3, N_); s3 /= np.linalg.norm(s3)
        C_ = [A3 + s3 * 30.0, A3 - s3 * 30.0, A3 - s3 * 30.0 - N_ * PUR_T, A3 + s3 * 30.0 - N_ * PUR_T]
        crv = r.Polyline([r.Point3d(*map(float, c_)) for c_ in C_ + [C_[0]]]).ToNurbsCurve(); best = None; mid_ = (A3 + B3) / 2
        for ex_ in (r.Extrusion.Create(crv, L_, True), r.Extrusion.Create(crv, -L_, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2]) - mid_[:2])
            if best is None or dm < best[0]: best = (dm, ex_)
        if best is None: return 0
        at_ = r.ObjectAttributes(); at_.LayerIndex = L20V; at_.Name = name_; _XNEW.append((best[1], at_)); return 1
    # 10-29 夜（監修の項 20261029-2027 の 1・新しい鼻母屋）：鼻母屋は屋根の先から 130 内の線（出し梁の先 100＋母屋の半分 30）に沿う。
    #   線が曲がる所（南西・北西の角）は 30 以内で折れ線にした区間ごとのまっすぐな材（前は出し梁の先を結ぶ一本の弦で、南西の角で外壁を貫いた）。
    #   両端の点は前と同じ出し梁の先（先から 30 内、2 枚の真ん中）で、その 400 内の線の点は使わない。
    #   端は出し梁の横の面にちょうど触れる所（その端の近くの出し梁の立体に重ならない最長、前は食い込み・届かないが混じった）
    _CL = WSL.buffer(-130.0, join_style=2)
    _CL = max(getattr(_CL, 'geoms', [_CL]), key=lambda q: q.area).exterior
    _CM_ = [M_ for M_ in (_tm_mf(_ext_tm(c_)) for c_ in _CANT) if M_ is not None]
    _CMB = [np.array(M_.bounding_box()) for M_ in _CM_]
    def _ov_c(A2, B2, P2):
        """A2→B2 の母屋と、点 P2 の近く（800）の出し梁との重なり（mm³）"""
        Ms_ = [M_ for M_, b_ in zip(_CM_, _CMB) if np.all(b_[:2] - 800.0 <= P2) and np.all(P2 <= b_[3:5] + 800.0)]
        if not Ms_: return 0.0
        if not _purl_e(A2, B2, float(_RWf['roof_f'](*A2)), float(_RWf['roof_f'](*B2)), ''): return 0.0
        e_ = _XNEW.pop()[0]; M_ = _tm_mf(_ext_tm(e_))
        return 1e12 if M_ is None else sum((M_ ^ Mc_).volume() for Mc_ in Ms_)
    def _sub(d0, d1):
        """_CL の上の長さの座標 d0 → d1 の部分の点（50 おき）"""
        Lc_ = _CL.length; ds_ = np.arange(min(d0, d1), max(d0, d1), 50.0).tolist() + [max(d0, d1)]
        P_ = [np.asarray(_CL.interpolate(d_ % Lc_).coords[0]) for d_ in ds_]
        return P_ if d0 <= d1 else P_[::-1]
    def _trim_end(A2_, B2_, end_):
        """end_ の端を、その近くの出し梁に重ならない最長（触れる所）に：重なれば縮め（600 まで）、離れていれば延ばす（300 まで）"""
        dl_ = (B2_ - A2_) / np.linalg.norm(B2_ - A2_); P2_ = A2_ if end_ == 0 else B2_
        mv_ = lambda t: (A2_ + dl_ * t, B2_) if end_ == 0 else (A2_, B2_ - dl_ * t)
        ov_ = lambda t: _ov_c(*mv_(t), P2_)
        if ov_(0.0) <= 10.0: bad_, ok_ = -300.0, 0.0                              # 離れている → 延ばす
        else: bad_, ok_ = 0.0, min(600.0, float(np.linalg.norm(B2_ - A2_)) - 60.0)    # 重なる → 縮める（その区間の中で）
        if ov_(bad_) <= 10.0 or ov_(ok_) > 10.0: return mv_(ok_ if bad_ == 0.0 else 0.0), False
        for _ in range(16):
            mid_ = (bad_ + ok_) / 2
            if ov_(mid_) > 10.0: bad_ = mid_
            else: ok_ = mid_
        return mv_(ok_), True
    _dfr = {f_: _CL.project(Point(*np.mean([p_ - d_ * 30.0 for p_, d_ in _tipf[f_]], axis=0))) for f_ in _tk}
    _Lc = _CL.length; _n_hfail = 0
    def _arc(da, db):                                                  # 短いほう（西の側）の向きに
        dd_ = (db - da) % _Lc
        return (da, da + dd_) if dd_ <= _Lc / 2 else (da, da - ((da - db) % _Lc))
    def _purl_cut(A2, B2, cA, cB, name_):
        """_purl_e と同じ断面で、両端の木口を平面の線 c＝(n, h)（n・x＝h、鉛直の面）に沿って斜めに切る（10-29 夜、力の道：
        折れ目の継手は二等分の面、出し梁に当たる端は出し梁の横の面。木口の角だけが当たっていた）"""
        zA, zB = float(_RWf['roof_f'](*A2)), float(_RWf['roof_f'](*B2))
        A3 = np.r_[A2, zA]; B3 = np.r_[B2, zB]; L_ = float(np.linalg.norm(B3 - A3)); d3 = (B3 - A3) / L_; M2 = (A2 + B2) / 2; e_ = 50.0
        gx = (_RWf['roof_f'](M2[0] + e_, M2[1]) - _RWf['roof_f'](M2[0] - e_, M2[1])) / (2 * e_); gy = (_RWf['roof_f'](M2[0], M2[1] + e_) - _RWf['roof_f'](M2[0], M2[1] - e_)) / (2 * e_)
        N_ = np.array([-gx, -gy, 1.0]); N_ = N_ - d3 * (N_ @ d3); N_ /= np.linalg.norm(N_); s3 = np.cross(d3, N_); s3 /= np.linalg.norm(s3)
        C_ = []
        for P3_, (n_, h_) in ((A3, cA), (B3, cB)):
            row_ = []
            for w_ in (30.0, -30.0):
                c_ = P3_ + s3 * w_; den_ = float(d3[:2] @ n_)
                tau_ = (h_ - float(c_[:2] @ n_)) / den_ if abs(den_) > 1e-6 else 0.0
                row_.append(c_ + d3 * float(np.clip(tau_, -400.0, 400.0)))
            C_.append(row_)
        TOP_ = [C_[0][0], C_[0][1], C_[1][1], C_[1][0]]
        crv = r.Polyline([r.Point3d(*map(float, c_)) for c_ in TOP_ + [TOP_[0]]]).ToNurbsCurve(); best = None
        tgt_ = (A3 + B3) / 2 - N_ * PUR_T / 2
        for ex_ in (r.Extrusion.Create(crv, PUR_T, True), r.Extrusion.Create(crv, -PUR_T, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2, (bb_.Min.Z + bb_.Max.Z) / 2]) - tgt_)
            if best is None or dm < best[0]: best = (dm, ex_)
        if best is None: return 0
        at_ = r.ObjectAttributes(); at_.LayerIndex = L20V; at_.Name = name_; _XNEW.append((best[1], at_)); return 1
    def _face_cut(P2, Q2, dc_):
        """P2 の端（向き P2←Q2 の外）を、向き dc_（出し梁の軸）の鉛直の面で、いちばん出し梁に寄った角が触れる所に"""
        do_ = (P2 - Q2) / np.linalg.norm(P2 - Q2); m_ = dc_ / np.linalg.norm(dc_); n_ = np.array([-m_[1], m_[0]])
        if n_ @ do_ < 0: n_ = -n_
        sp_ = np.array([-do_[1], do_[0]])
        return (n_, max(float((P2 + sp_ * w_) @ n_) for w_ in (30.0, -30.0)))
    def _near_ply(f_, other_):
        return min(_tipf[f_], key=lambda pd_: np.linalg.norm(pd_[0] - other_))
    # 10-30（ユーザー、監修の項 0552 の残り）：鼻母屋の受けの柱と腕木。南西の丸い壁（架構 u21.33〜24）と北西の斜めの壁（架構 u48〜u50.1）は
    #   架構のあいだに柱が無く、鼻母屋の継手の下に受ける材が無かった。外壁の内面の内側（面をそろえる、外壁の立体とは重ねない）に柱 120×120
    #   （1 階の床 z0 から腕木の下まで、向きは壁の法線）を約 1.2 m おき（窓は避けて窓の脇に）に立て、柱の頭から壁に直角に外へ腕木（幅 120、
    #   せいは外壁の内面で 240・先で 120、出し梁と同じ先細り）を出し、鼻母屋を載せる。鼻母屋の継手（折れ目）は腕木の上（腕木の芯の線と鼻母屋の芯の線の交わる所）。
    #   腕木の上の面は鼻母屋の下の面の下（鼻母屋の内の面の 20 内まで）、そこから内は水平（屋根は内へ上がるので、室内の母屋・合板の下を通る）。外壁は腕木の所を欠く。
    _RI = WSi_W.exterior if WSi_W.geom_type == 'Polygon' else max(WSi_W.geoms, key=lambda q: q.area).exterior
    _RIL = _RI.length
    def _rp(d_): return np.asarray(_RI.interpolate(d_ % _RIL).coords[0])
    def _rtn(d_):
        t_ = _rp(d_ + 20.0) - _rp(d_ - 20.0); t_ = t_ / np.linalg.norm(t_); n_ = np.array([t_[1], -t_[0]])
        if WSi_W.contains(Point(*(_rp(d_) + n_ * 50.0))): n_ = -n_
        return t_, n_
    def _ring_d(u_):                                                    # 西の側（v < −7）で u の線が外壁の内面を切る所
        ds_ = np.arange(0.0, _RIL, 20.0); best_ = None
        for d_ in ds_:
            uu_, vv_ = uv(*_rp(d_))
            if vv_ < -7.0 and (best_ is None or abs(uu_ - u_) < best_[1]): best_ = (d_, abs(uu_ - u_))
        lo_, hi_ = best_[0] - 20.0, best_[0] + 20.0
        f_ = lambda d_: uv(*_rp(d_))[0] - u_
        for _ in range(30):
            md_ = (lo_ + hi_) / 2
            if (f_(lo_) < 0) == (f_(md_) < 0): lo_ = md_
            else: hi_ = md_
        return (lo_ + hi_) / 2
    def _proj_iv(T3_):
        D_ = [_RI.project(Point(*p_[:2])) for p_ in T3_[::max(1, len(T3_) // 300)] if _RI.distance(Point(*p_[:2])) < 600.0]
        return (min(D_), max(D_)) if D_ else None
    _EXC = []                                                           # 柱の芯を置かない所（窓：枠の外から 100、架構の柱：面から 100）
    for o in m.Objects:
        ln_ = LN[o.Attributes.LayerIndex]
        if not (ln_.startswith('19') or (o.Attributes.LayerIndex == L22A and not (o.Attributes.Name or ''))): continue
        g_ = cur_g(o)
        try: T3_ = tri.tri_extrusion(g_).reshape(-1, 3) if isinstance(g_, r.Extrusion) else (mesh_V(g_) if isinstance(g_, r.Mesh) else None)
        except Exception: T3_ = None
        if T3_ is None or not len(T3_) or T3_[:, 2].max() < 300.0: continue
        iv_ = _proj_iv(T3_)
        if iv_ is not None and iv_[1] - iv_[0] < 8000.0: _EXC.append((iv_[0] - 100.0, iv_[1] + 100.0, 'win' if ln_.startswith('19') else 'col'))
    def _free(d_): return not any(a_ < d_ < b_ for a_, b_, k_ in _EXC)
    _STUD = {}                                                          # 架構の u（鼻母屋の区間の始まり）→ 柱の記録
    _STUD_FP = []                                                       # 柱の平面形（2 階の床を欠く）
    _ev = lambda b_: max(getattr(WSL.buffer(-b_, join_style=2), 'geoms', [WSL.buffer(-b_, join_style=2)]), key=lambda q: q.area)
    _EV100, _EV130, _EV160 = _ev(100.0), _ev(130.0), _ev(160.0)
    def _leave(P0_, n_, poly_):
        lo_, hi_ = 0.0, 3000.0
        if poly_.contains(Point(*(P0_ + n_ * hi_))): return None
        for _ in range(40):
            md_ = (lo_ + hi_) / 2
            if poly_.contains(Point(*(P0_ + n_ * md_))): lo_ = md_
            else: hi_ = md_
        return (lo_ + hi_) / 2
    def _stud_at(d_):
        t_, n_ = _rtn(d_); c_ = _rp(d_) - n_ * 62.5                          # 柱の芯（外の面を外壁の内面の 1 内に）
        P0_ = c_ - n_ * 60.0                                                # 腕木の内の端（柱の内の面）
        s_tip_ = _leave(P0_, n_, _EV100); s_q_ = _leave(P0_, n_, _EV130); s_pi_ = _leave(P0_, n_, _EV160)
        if s_tip_ is None or s_q_ is None or s_pi_ is None: return None
        return dict(d=d_, c=c_, n=n_, t=t_, P0=P0_, s_tip=s_tip_, s_pi=s_pi_, q=P0_ + n_ * s_q_)
    # 柱の位置は鼻母屋の上で決める（南西の角は軒の線が壁の弧と同心でなく、壁の上で等分すると腕木の先が出し梁の先に寄った）：
    #   鼻母屋の芯の線（_CL）の上で、区間の始まり（出し梁の先）から終わり（出し梁の先／北西は u50.1 の壁の所の腕木）までを、窓の脇の柱（窓の枠の外から 100）と
    #   終わりで区切り、1.2 m を超えるあいだを等分する。窓の中に落ちる所には置かない
    for key_, ua_, ub_, end_ in ((21.33, 21.33, 24.0, False), (48.0, 48.0, 50.1, True)):
        fa0_ = next((f_ for f_ in _tk if abs(f_ - ua_) < 0.2), None)
        if fa0_ is None: continue
        da_, db_ = _ring_d(ua_), _ring_d(ub_)
        if da_ > db_: log.append(f'  !! 鼻母屋の受けの柱：外壁の内面の線の向きが逆（u{ua_}〜{ub_}）、作らない'); continue
        c0_ = _dfr[fa0_]
        if end_: st_e_ = _stud_at(db_); c1_ = None if st_e_ is None else _CL.project(Point(*st_e_['q']))
        else: fb0_ = next((f_ for f_ in _tk if abs(f_ - ub_) < 0.2), None); c1_ = None if fb0_ is None else _dfr[fb0_]
        if c1_ is None: continue
        sg_ = 1.0 if (c1_ - c0_) % _Lc <= _Lc / 2 else -1.0
        rel_ = lambda c_: ((c_ - c0_) * sg_) % _Lc
        Lr_ = rel_(c1_)
        smp_ = []                                                          # 壁の上の位置 d → 鼻母屋の上の位置（始まりから）
        for d_ in np.arange(da_ - 2500.0, db_ + 1000.0, 10.0):
            st_ = _stud_at(d_)
            if st_ is None: continue
            x_ = rel_(_CL.project(Point(*st_['q'])))
            if x_ < Lr_ + 500.0: smp_.append((d_, x_))
        if not smp_: continue
        def _d_of(x_): return min(smp_, key=lambda p_: abs(p_[1] - x_))
        fix_ = [0.0, Lr_]; xd_ = {}                                        # 窓の脇の柱は壁の上の位置そのまま
        for a_, b_, k_ in _EXC:
            if k_ != 'win': continue
            for y_ in (a_, b_):
                if da_ - 2500.0 < y_ < db_ + 1000.0 and _free(y_):
                    st_ = _stud_at(y_)
                    if st_ is None: continue
                    x_ = rel_(_CL.project(Point(*st_['q'])))
                    if 300.0 < x_ < Lr_ - (0.0 if end_ else 300.0): fix_.append(x_); xd_[x_] = y_
        fix_ = sorted(fix_); fx2_ = [fix_[0]]
        for x_ in fix_[1:]:
            if x_ - fx2_[-1] < 500.0:
                if abs(x_ - Lr_) < 1e-6: fx2_[-1] = x_                       # 終わりを残す
                continue
            fx2_.append(x_)
        xs_ = [x_ for x_ in fx2_[1:-1]] + ([Lr_] if end_ else [])
        for a_, b_ in zip(fx2_, fx2_[1:]):
            k_ = int(np.ceil((b_ - a_) / 1200.0 - 1e-6))
            for j_ in range(1, k_):
                xs_.append(a_ + (b_ - a_) * j_ / k_)
        rec_ = []
        for x_ in sorted(set(xs_)):
            d_ = db_ if (end_ and abs(x_ - Lr_) < 1e-6) else xd_.get(x_, _d_of(x_)[0])
            if not _free(d_): continue
            st_ = _stud_at(d_)
            if st_ is not None: rec_.append(st_)
        _STUD[key_] = sorted(rec_, key=lambda x_: x_['d'])
    def _purl_planes(A2, B2):
        """_purl_cut と同じ断面の鼻母屋（A2→B2）の下の面：点 p と法線 N"""
        zA, zB = float(_RWf['roof_f'](*A2)), float(_RWf['roof_f'](*B2))
        A3 = np.r_[A2, zA]; B3 = np.r_[B2, zB]; d3 = (B3 - A3) / np.linalg.norm(B3 - A3); M2 = (A2 + B2) / 2; e_ = 50.0
        gx = (_RWf['roof_f'](M2[0] + e_, M2[1]) - _RWf['roof_f'](M2[0] - e_, M2[1])) / (2 * e_); gy = (_RWf['roof_f'](M2[0], M2[1] + e_) - _RWf['roof_f'](M2[0], M2[1] - e_)) / (2 * e_)
        N_ = np.array([-gx, -gy, 1.0]); N_ = N_ - d3 * (N_ @ d3); N_ /= np.linalg.norm(N_)
        return A3 - N_ * PUR_T, N_
    _n_stud = 0; _n_arm = 0; _ARM_M = []; _stud_log = []; _ARM_FP = []
    def _arm_build(st_, segs_):
        """柱と腕木を作る。segs_：腕木に載る鼻母屋（A2, B2）"""
        c_, n_, t_, P0_ = st_['c'], st_['n'], st_['t'], st_['P0']
        s_k_ = st_['s_pi'] - 20.0; s_t_ = st_['s_tip']
        # 腕木の上の面は、載る鼻母屋（作った押し出し）の下の面を下から測って決める（腕木の幅の中でいちばん低い所に触れる）。
        #   鼻母屋の内の面の 5 内と先の 5 手前で測り、その 2 点を結ぶ線を s_k_・s_t_ へ延ばす
        hp_ = [e_ for e_, a_ in _XNEW if e_ is not None and (a_.Name or '').startswith('軒先の母屋') and a_.LayerIndex == L20V
               and np.linalg.norm(np.array([(e_.GetBoundingBox().Min.X + e_.GetBoundingBox().Max.X) / 2, (e_.GetBoundingBox().Min.Y + e_.GetBoundingBox().Max.Y) / 2]) - st_['q']) < 3000.0]
        HM_ = trimesh.util.concatenate([_ext_tm(e_) for e_ in hp_]) if hp_ else None
        # 下の面（法線が下を向く三角形）に当たる所だけ使う（鼻母屋の断面は屋根に直角で傾くので、縁の近くでは横の面に当たる）
        if HM_ is None: log.append(f'  !! 腕木の上の鼻母屋が無い u{uv(*c_)[0]:.2f}'); return 0
        H_ = []                                                               # 下の面に当たった所（s, w, z）
        W9_ = np.linspace(-60.0, 60.0, 9)
        for s_ in np.arange(st_['s_pi'] - 80.0, s_t_ + 1.0, 4.0):
            O_ = np.array([np.r_[P0_ + n_ * s_ + t_ * w_, 0.0] for w_ in W9_])
            loc_, ir_, it_ = HM_.ray.intersects_location(O_, np.tile([0.0, 0.0, 1.0], (len(O_), 1)), multiple_hits=False)
            H_ += [(s_, W9_[k_], l_[2]) for l_, k_, f_ in zip(loc_, ir_, it_) if HM_.face_normals[f_][2] < -0.7]     # 横の面（傾き 35° で −0.57）は除く
        if len(H_) < 6: log.append(f'  !! 腕木の上の鼻母屋を測れない u{uv(*c_)[0]:.2f}'); return 0
        H_ = np.array(H_)
        s_k_ = max(float(H_[:, 0].min()) - 2.0, 130.0)                         # 折れは鼻母屋の下の面の内の縁（断面が屋根に直角に傾くので、北西の急な屋根では内の面の線より 80 ほど内）
        # 鼻母屋の下の面の平面 z ＝ k0 + k1・s + k2・w（腕木の幅の向き w にも傾く所は、腕木の上に楔の受け材を足して面で受ける）
        (k0_, k1_, k2_), *_ = np.linalg.lstsq(np.c_[np.ones(len(H_)), H_[:, 0], H_[:, 1]], H_[:, 2], rcond=None)
        if abs(k2_) * 120.0 < 3.0: k2_ = 0.0
        wl_ = -60.0 if k2_ > 0 else 60.0                                       # 低いほうの縁
        dz_ = min(0.0, float(np.min(H_[:, 2] - (k0_ + k1_ * H_[:, 0] + k2_ * H_[:, 1]))))
        zk_ = k0_ + k1_ * s_k_ + k2_ * wl_ + dz_; zt_ = k0_ + k1_ * s_t_ + k2_ * wl_ + dz_
        st_['shim'] = (abs(k2_) * 120.0, wl_) if k2_ != 0.0 else None
        rise_ = float(_RWf['roof_f'](*P0_)) - float(_RWf['roof_f'](*(P0_ + n_ * s_k_)))
        z0_ = zk_ if rise_ >= 0.0 else zk_ + rise_                                 # 内へ水平（屋根が内へ下がる所は屋根に平行）
        zc_ = z0_ - 240.0                                                     # 柱の頭（腕木の下の面、柱の上は水平）
        prof_ = [(0.0, z0_), (s_k_, zk_), (s_t_, zt_), (s_t_, zt_ - 120.0), (120.0, zc_), (0.0, zc_)]
        if rise_ < 0.0: prof_ = [(0.0, z0_), (s_t_, zt_), (s_t_, zt_ - 120.0), (120.0, zc_), (0.0, zc_)]
        P3_ = [np.r_[P0_ + n_ * s_ - t_ * 60.0, z_] for s_, z_ in prof_]
        crv_ = r.Polyline([r.Point3d(*map(float, p_)) for p_ in P3_ + [P3_[0]]]).ToNurbsCurve(); best_ = None
        tgt_ = np.mean(P3_, axis=0) + np.r_[t_ * 60.0, 0.0]
        for ex_ in (r.Extrusion.Create(crv_, 120.0, True), r.Extrusion.Create(crv_, -120.0, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm_ = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2, (bb_.Min.Z + bb_.Max.Z) / 2]) - tgt_)
            if best_ is None or dm_ < best_[0]: best_ = (dm_, ex_)
        if best_ is None: return 0
        at_ = r.ObjectAttributes(); at_.LayerIndex = L22B; at_.Name = '腕木（片持ち、柱の頭から壁に直角に外へ、鼻母屋を受ける、120×240 → 120）'
        _XNEW.append((best_[1], at_)); M_ = _tm_mf(_ext_tm(best_[1]))
        if M_ is not None: _ARM_M.append(M_)
        _ARM_FP.append((Polygon([P0_ + t_ * 60.0, P0_ - t_ * 60.0, P0_ + n_ * s_t_ - t_ * 60.0, P0_ + n_ * s_t_ + t_ * 60.0]), _ext_tm(best_[1])))
        if st_.get('shim'):                                                   # 楔の受け材：腕木の上の面（幅の向きに水平）と鼻母屋の下の面のあいだ
            hw_, wl_ = st_['shim']; e3_ = np.r_[n_ * (s_t_ - s_k_), zt_ - zk_]; Le_ = float(np.linalg.norm(e3_)); e3_ /= Le_
            up_ = np.r_[-n_ * e3_[2], np.linalg.norm(e3_[:2])]                 # e3_ に直角、上向き（n と z の面の中）
            B0_ = np.r_[P0_ + n_ * s_k_, zk_]; wh_ = -wl_
            tri3_ = [B0_ + np.r_[t_ * wl_, 0.0], B0_ + np.r_[t_ * wh_, 0.0], B0_ + np.r_[t_ * wh_, 0.0] + up_ * hw_ * up_[2]]
            crv_ = r.Polyline([r.Point3d(*map(float, p_)) for p_ in tri3_ + [tri3_[0]]]).ToNurbsCurve(); bw_ = None
            cen_ = np.mean(tri3_, axis=0) + e3_ * Le_ / 2
            for ex_ in (r.Extrusion.Create(crv_, Le_, True), r.Extrusion.Create(crv_, -Le_, True)):
                if ex_ is None: continue
                bb_ = ex_.GetBoundingBox(); dm_ = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2, (bb_.Min.Z + bb_.Max.Z) / 2]) - cen_)
                if bw_ is None or dm_ < bw_[0]: bw_ = (dm_, ex_)
            if bw_ is not None:
                atw_ = r.ObjectAttributes(); atw_.LayerIndex = L22B; atw_.Name = f'腕木の受け材（楔、鼻母屋の下の面の傾きに合わせる、平らな面だけ、最大 {hw_:.0f}）'
                _XNEW.append((bw_[1], atw_))
        Q4_ = [c_ + n_ * 60.0 + t_ * 60.0, c_ + n_ * 60.0 - t_ * 60.0, c_ - n_ * 60.0 - t_ * 60.0, c_ - n_ * 60.0 + t_ * 60.0]
        crv_ = r.Polyline([r.Point3d(float(p_[0]), float(p_[1]), 0.0) for p_ in Q4_ + [Q4_[0]]]).ToNurbsCurve(); best_ = None
        for ex_ in (r.Extrusion.Create(crv_, zc_, True), r.Extrusion.Create(crv_, -zc_, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm_ = abs((bb_.Min.Z + bb_.Max.Z) / 2 - zc_ / 2)
            if best_ is None or dm_ < best_[0]: best_ = (dm_, ex_)
        if best_ is None: return 1
        at_ = r.ObjectAttributes(); at_.LayerIndex = L22A; at_.Name = '柱 120×120（外壁の内面にそろえる、鼻母屋の腕木を受ける、面材の受けを兼ねる）'
        _XNEW.append((best_[1], at_)); _STUD_FP.append(Polygon(Q4_))
        uu_, vv_ = uv(*c_)
        _stud_log.append(f'u{uu_:.2f} v{vv_:.2f} 頭{zc_:.0f} 腕木{s_t_:.0f}（{"水平" if rise_ >= 0 else "屋根に平行"}、内へ{rise_:+.0f}）')
        return 1
    for fa_, fb_ in zip(_tk, _tk[1:]):
        d0_, d1_ = _arc(_dfr[fa_], _dfr[fb_])
        Q_ = [np.asarray(c_) for c_ in LineString(_sub(d0_, d1_)).simplify(30.0).coords]       # 30 以内の折れ線（区間が短いと木口と横の面の見分けがつかない）
        cA_ = np.mean([p_ for p_, d_ in _tipf[fa_]], axis=0); cB_ = np.mean([p_ for p_, d_ in _tipf[fb_]], axis=0)
        pa_, da_ = _near_ply(fa_, cB_); pb_, db_ = _near_ply(fb_, cA_)
        tA_ = pa_ - da_ * 30.0; tB_ = pb_ - db_ * 30.0                          # 端はとなりの架構に近いほうの 1 枚の出し梁の先（先から 30 内）
        Qm_ = [q_ for q_ in Q_[1:-1] if np.linalg.norm(q_ - tA_) > 400.0 and np.linalg.norm(q_ - tB_) > 400.0]
        _sk_ = next((k_ for k_ in _STUD if abs(k_ - fa_) < 0.2), None) if (abs(fb_ - 24.0) < 0.2 or abs(fb_ - U_F18) < 0.2) else None   # 10-30：北西の斜めの壁（u48〜梁18）も腕木の上で折る
        if _sk_ is not None and _STUD[_sk_]: Qm_ = [st_['q'] for st_ in _STUD[_sk_]]      # 10-30：折れ目（継手）は腕木の上だけ
        def _inset(p_, d_, q_):                                                  # 母屋が出し梁に斜めに当たる所は、木口がみな出し梁の横の面に載るよう先から 30／sinθ 内に
            e_ = (q_ - p_) / np.linalg.norm(q_ - p_); sn_ = abs(e_[0] * d_[1] - e_[1] * d_[0]) / np.linalg.norm(d_)
            return p_ - d_ / np.linalg.norm(d_) * (30.0 / max(sn_, 0.5) + 2.0)
        tA_ = _inset(pa_, da_, Qm_[0] if Qm_ else tB_); tB_ = _inset(pb_, db_, Qm_[-1] if Qm_ else tA_)
        Q_ = [tA_] + Qm_ + [tB_]
        (Q_[0], Q_[1]), ok0_ = _trim_end(Q_[0], Q_[1], 0)
        (Q_[-2], Q_[-1]), ok1_ = _trim_end(Q_[-2], Q_[-1], 1)
        _n_hfail += (not ok0_) + (not ok1_)
        cuts_ = [_face_cut(Q_[0], Q_[1], da_)]
        for k_ in range(1, len(Q_) - 1):                                          # 折れ目：二等分の面
            a_ = (Q_[k_] - Q_[k_ - 1]); a_ /= np.linalg.norm(a_); b_ = (Q_[k_ + 1] - Q_[k_]); b_ /= np.linalg.norm(b_)
            n_ = (a_ + b_) / np.linalg.norm(a_ + b_); cuts_.append((n_, float(Q_[k_] @ n_)))
        cuts_.append(_face_cut(Q_[-1], Q_[-2], db_))
        for k_, (A2_, B2_) in enumerate(zip(Q_, Q_[1:])):
            _n_hana += _purl_cut(A2_, B2_, cuts_[k_], cuts_[k_ + 1], f'軒先の母屋 杉 60×150（出し梁の先{"と腕木" if _sk_ is not None else ""}が受ける、金物、u{fa_:g}〜{fb_:g}）')
        if _sk_ is not None and _STUD[_sk_]:
            for j_, st_ in enumerate(_STUD[_sk_]):
                _n_arm += _arm_build(st_, [(Q_[j_], Q_[j_ + 1]), (Q_[j_ + 1], Q_[j_ + 2])])
    # 10-30：北西の斜めの壁（架構 u48〜u50.1）の鼻母屋：u48 の出し梁の先から、腕木の上の折れ目を通り、終わりの腕木の先の面（腕木の芯から 60 先）まで
    #   10-30（梁18）：北の端の架構の出し梁があるときは、上の区間（u48〜梁18 の出し梁の先、腕木の上で折る）が受け持つので作らない
    _skn_ = next((k_ for k_ in _STUD if abs(k_ - 48.0) < 0.2), None); _fn_ = next((f_ for f_ in _tk if abs(f_ - 48.0) < 0.2), None)
    if _skn_ is not None and _fn_ is not None and _STUD[_skn_] and not any(abs(f_ - U_F18) < 0.2 for f_ in _tk):
        Sn_ = _STUD[_skn_]; qs_ = [st_['q'] for st_ in Sn_]
        pa_, da_ = _near_ply(_fn_, qs_[0])
        e_ = (qs_[0] - pa_) / np.linalg.norm(qs_[0] - pa_); sn_ = abs(e_[0] * da_[1] - e_[1] * da_[0]) / np.linalg.norm(da_)
        tA_ = pa_ - da_ / np.linalg.norm(da_) * (30.0 / max(sn_, 0.5) + 2.0)
        dl_ = (qs_[-1] - (qs_[-2] if len(qs_) > 1 else tA_)); dl_ /= np.linalg.norm(dl_)
        Q_ = [tA_] + qs_ + [qs_[-1] + dl_ * 60.0]
        (Q_[0], Q_[1]), ok0_ = _trim_end(Q_[0], Q_[1], 0)
        _n_hfail += (not ok0_)
        cuts_ = [_face_cut(Q_[0], Q_[1], da_)]
        for k_ in range(1, len(Q_) - 2):
            a_ = (Q_[k_] - Q_[k_ - 1]); a_ /= np.linalg.norm(a_); b_ = (Q_[k_ + 1] - Q_[k_]); b_ /= np.linalg.norm(b_)
            n_ = (a_ + b_) / np.linalg.norm(a_ + b_); cuts_.append((n_, float(Q_[k_] @ n_)))
        cuts_.append((dl_, float(Q_[-1] @ dl_)))                                    # 終わりは鼻母屋に直角
        Qn_ = Q_[:-2] + [Q_[-1]]                                                    # 終わりの腕木の芯の点は折れ目でない（そのまま 60 先まで）
        for k_, (A2_, B2_) in enumerate(zip(Qn_, Qn_[1:])):
            _n_hana += _purl_cut(A2_, B2_, cuts_[k_], cuts_[k_ + 1], f'軒先の母屋 杉 60×150（出し梁の先と腕木が受ける、金物、u48〜50.1）')
        for j_, st_ in enumerate(Sn_):
            sg_ = [(Qn_[j_], Qn_[j_ + 1])] + ([(Qn_[j_ + 1], Qn_[j_ + 2])] if j_ + 2 < len(Qn_) else [])
            _n_arm += _arm_build(st_, sg_)
    log.append(f'西館：鼻母屋の受けの柱と腕木 {_n_arm} 組（{"・".join(_stud_log)}）')
    # 10-30：腕木を横切る母屋（南西の角で壁の弧を斜めに通る水平の母屋）は腕木の横の面で切る。母屋の作り方（_purl_x：木口を腕木の面に沿って斜めに、
    #   楔）のまま、腕木を梁の帯に加えて片ごとに作り直す。残すのは元の梁の端を持つ片だけ（腕木と腕木のあいだ・腕木と延ばした先のあいだの片は除き、
    #   延ばした先の飼木も除く。鼻母屋はそこで腕木に載る）
    _n_split = 0
    if _ARM_FP:
        _AFP = unary_union([f_ for f_, t_ in _ARM_FP])
        _BANDS0, _BCX1, _BTMW0 = BANDS, _BCX, list(_BTMW)
        BANDS = BANDS.union(_AFP); _BCX = _BCX.union(_AFP); _BTMW += [t_ for f_, t_ in _ARM_FP]
        for rec_ in list(_PREC):
            k_ = rec_['i']
            if _XNEW[k_][0] is None or not rec_['name'].startswith('母屋'): continue
            T_ = rec_['T']; d3 = rec_['d3']; s3 = rec_['s3']
            A2_ = ((T_[0] + T_[1]) / 2)[:2]; B2_ = ((T_[2] + T_[3]) / 2)[:2]; zt_ = float(np.mean([c_[2] for c_ in T_]))
            dd2_ = (B2_ - A2_) / np.linalg.norm(B2_ - A2_)
            # 10-31（ユーザー：母屋は梁のあいだだけ）：外壁の内で止まる端（梁の帯に触れない端）の 400 先に腕木があれば、その端を腕木の横の面まで
            #   延ばして腕木で受ける（南西の丸い壁の母屋が壁の際で片持ちになっていた。延ばした先の腕木の外の片は下で除く）
            Mp_ = _tm_mf(_ext_tm(_XNEW[k_][0]))
            _hit_arm = Mp_ is not None and any((Mp_ ^ Ma_).volume() > 1e4 for Ma_ in _ARM_M)
            for end_, P_, o_ in ((0, A2_, -dd2_), (1, B2_, dd2_)):
                if _hit_arm or _BCX1.distance(Point(*(P_ + o_ * 40.0))) < 1.0: continue
                seg_ = LineString([P_, P_ + o_ * 400.0]).buffer(30.0, cap_style=2)
                if not any(seg_.intersects(f_) for f_, t_ in _ARM_FP): continue
                if end_ == 0: A2_ = A2_ - dd2_ * 400.0
                else: B2_ = B2_ + dd2_ * 400.0
                rec_['gx'] = rec_.get('gx', ()) + (end_,); _hit_arm = True
            if not _hit_arm: continue
            L2_ = float(np.linalg.norm(B2_ - A2_)); sp2_ = np.array([-dd2_[1], dd2_[0]])
            rect_ = Polygon([A2_ + sp2_ * 32.0, B2_ + sp2_ * 32.0, B2_ - sp2_ * 32.0, A2_ - sp2_ * 32.0])
            blk_ = []
            for f_, t_ in _ARM_FP:
                x_ = rect_.intersection(f_)
                if x_.is_empty or x_.area < 1.0: continue
                ts_ = [float((np.array(c_) - A2_) @ dd2_) for g_ in getattr(x_, 'geoms', [x_]) for c_ in g_.exterior.coords]
                blk_.append((min(ts_), max(ts_)))
            if not blk_: continue
            blk_ = sorted(blk_); iv_ = []; a_ = 0.0
            for b0_, b1_ in blk_:
                if b0_ > a_: iv_.append((a_, b0_))
                a_ = max(a_, b1_)
            if a_ < L2_: iv_.append((a_, L2_))
            gx_ = rec_.get('gx', ())
            keep_ = [(a_, b_) for a_, b_ in iv_ if b_ - a_ >= 600.0 and ((a_ < 1.0 and 0 not in gx_) or (b_ > L2_ - 1.0 and 1 not in gx_))]
            nm_ = rec_['name'].replace('（妻の軒の出へ片持ちで延ばす）', '') + '（腕木の面で切る）'
            _XNEW[k_] = (None, _XNEW[k_][1])
            for e_ in gx_:                                                          # 延ばした先の飼木（鼻母屋を受ける）も除く
                kg_ = rec_.get('kg', {}).get(e_)
                if kg_ is not None and not any((e_ == 0 and a_ < 1.0) or (e_ == 1 and b_ > L2_ - 1.0) for a_, b_ in keep_): _XNEW[kg_] = (None, _XNEW[kg_][1])
            for a_, b_ in keep_:
                k0_ = len(_XNEW)
                _n_split += _purl_x(A2_ + dd2_ * a_, A2_ + dd2_ * b_, zt_, nm_)
                for kk_ in range(k0_, len(_XNEW)):                                 # 腕木の面の楔は作らない（腕木の横の面は短く、楔が何にも載らなかった）。片は元の梁の端で受ける
                    if (_XNEW[kk_][1].Name or '').startswith('梁の受け材（楔'): _XNEW[kk_] = (None, _XNEW[kk_][1])
        BANDS, _BCX, _BTMW[:] = _BANDS0, _BCX1, _BTMW0
        log.append(f'西館：腕木を横切る母屋を腕木の横の面で切って作り直した {_n_split} 片')
    if _ARM_M:                                                                       # 外壁を腕木の所で欠く（出し梁と同じ）
        _AMU = _mf.Manifold.batch_boolean(_ARM_M, _mf.OpType.Add); _nwa = 0
        def _cut_w(mm0_):
            # 前の欠き（出し梁・妻の母屋）で作り直した網目は頂点を共有している：その並びのまま使う（三角形の集まりにして 0.1 で丸めると、
            #   単精度の座標が丸めの境で分かれて閉じない立体に見えた）
            F_ = []
            for i_ in range(mm0_.Faces.Count):
                f_ = mm0_.Faces[i_]; F_.append([f_[0], f_[1], f_[2]])
                if f_[2] != f_[3]: F_.append([f_[0], f_[2], f_[3]])
            tm_w = trimesh.Trimesh(mesh_V(mm0_), np.array(F_), process=False) if F_ else None
            if tm_w is None or not tm_w.is_watertight:
                T_w = tris(mm0_)
                if not len(T_w): return None
                tm_w = trimesh.Trimesh(T_w.reshape(-1, 3), np.arange(len(T_w) * 3).reshape(-1, 3)); tm_w.merge_vertices(digits_vertex=1)
                if not tm_w.is_watertight: return None
            M_w = _mf.Manifold(_mf.Mesh(vert_properties=np.asarray(tm_w.vertices, np.float32), tri_verts=np.asarray(tm_w.faces, np.uint32)))
            if M_w.is_empty(): return None
            M2 = M_w - _AMU
            if abs(M2.volume() - M_w.volume()) < 1e3: return None
            g_ = M2.to_mesh(); mm_ = r.Mesh()
            for x_, y_, z_ in np.asarray(g_.vert_properties)[:, :3]: mm_.Vertices.Add(float(x_), float(y_), float(z_))
            for a__, b__, c__ in np.asarray(g_.tri_verts): mm_.Faces.AddFace(int(a__), int(b__), int(c__))
            mm_.Normals.ComputeNormals(); mm_.Compact(); return mm_
        for k_, (mm0_, at0_) in enumerate(list(new_objs)):
            if at0_.LayerIndex != L21W: continue
            mm_ = _cut_w(mm0_)
            if mm_ is not None: new_objs[k_] = (mm_, at0_); _nwa += 1
        for o in m.Objects:
            if o.Attributes.LayerIndex != L21W or not isinstance(o.Geometry, r.Mesh) or str(o.Attributes.Id) in drop: continue
            mm_ = _cut_w(o.Geometry)
            if mm_ is not None: drop.add(str(o.Attributes.Id)); new_objs.append((mm_, o.Attributes)); _nwa += 1
        log.append(f'西館：外壁 {_nwa} 片を腕木の所で欠いた')
    if _n_hfail: log.append(f'  !! 軒先の母屋の端が出し梁に触れない所 {_n_hfail}')
    log.append(f'西館：軒先の母屋 {_n_hana} 本（屋根の先から 130 内の線に沿う折れ線、端は出し梁の横の面に触れる）')
    # u43.5 の合わせ梁のスペーサー（10-29 夜、ユーザー 20:27・監修の項 20261029-2027 の 3）：2 枚のあいだに短い木（幅＝間、梁のその位置の
    #   せいいっぱい、長さ 150）を、両端（桁に載る所：桁の内側の面から 10）と約 0.9 m おきに挟み、ボルトで締める
    _n_sp = 0; _rp = _raf()
    if len(_rp) == 2:
        g1_, g2_ = _rp; A1_, B1_ = _path(g1_); pd1_ = (B1_ - A1_) / np.linalg.norm(B1_ - A1_)
        if ((np.asarray(_path(g2_)).mean(0) - A1_) @ pd1_) < 0: g1_, g2_ = g2_, g1_
        A1_, B1_ = _path(g1_); pd1_ = (B1_ - A1_) / np.linalg.norm(B1_ - A1_)
        gap_ = min(float((P_ - B1_) @ pd1_) for P_ in _path(g2_))
        F1_ = _frame_of(g1_); op1_ = _poly_sz(g1_, F1_); X1_ = _v3(g1_.GetProfilePlane(0.0).XAxis); Y1_ = _v3(g1_.GetProfilePlane(0.0).YAxis)
        Gs_ = []
        for tm_, f_ in ((tm_, f_) for tm_ in _GTM for f_ in (0.02, 0.25, 0.5, 0.75, 0.98)):     # 斜めの桁：間の厚みのどこでも
            sc_ = tm_.section(plane_origin=B1_ + pd1_ * gap_ * f_, plane_normal=pd1_)
            if sc_ is None: continue
            for lp_ in sc_.discrete:
                if len(lp_) >= 3:
                    q_ = Polygon(_l2sz(F1_, np.c_[(lp_ - A1_) @ X1_, (lp_ - A1_) @ Y1_])).buffer(0)
                    if q_.area > 500.0 and q_.intersects(op1_): Gs_.append(q_)
        Gs_ = list(getattr(unary_union(Gs_), 'geoms', [unary_union(Gs_)])) if Gs_ else []
        Gs_.sort(key=lambda q: q.centroid.x)
        if gap_ > 50.0 and len(Gs_) >= 2:
            sA_ = Gs_[0].bounds[2] + 10.0; sB_ = Gs_[-1].bounds[0] - 10.0; Gu_ = unary_union(Gs_).buffer(10.0)
            nmid_ = max(int(round((sB_ - sA_ - 150.0) / 900.0)), 1)
            for k_ in range(nmid_ + 1):
                s0_ = sA_ + (sB_ - sA_ - 150.0) * k_ / nmid_
                pz_ = op1_.intersection(Polygon([(s0_, -1e5), (s0_ + 150.0, -1e5), (s0_ + 150.0, 1e5), (s0_, 1e5)])).difference(Gu_)
                if pz_.is_empty: continue
                pz_ = _clean_poly(max(getattr(pz_, 'geoms', [pz_]), key=lambda q: q.area).simplify(0.3))
                e_ = r.Extrusion()
                if not (e_.SetPathAndUp(r.Point3d(*map(float, B1_)), r.Point3d(*map(float, B1_ + pd1_ * gap_)), g1_.GetProfilePlane(0.0).YAxis) and
                        e_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in _sz2l(F1_, np.asarray(pz_.exterior.coords))]).ToNurbsCurve(), True)): continue
                at_ = r.ObjectAttributes(); at_.LayerIndex = L22B; at_.Name = '合わせ梁のスペーサー 杉 長さ 150（u43.5 の 2 枚のあいだ、ボルト締め）'
                _XNEW.append((e_, at_)); _n_sp += 1
    log.append(f'西館：u43.5 の合わせ梁のスペーサー {_n_sp} 個（両端の桁の内側と約 0.9 m おき）')
    log.append(f'西館：梁の面に斜めに当たる母屋の木口 {_NPWDG[0]} 端を、下の縁が梁の面に触れる所まで縮め、上のすき間に楔の受け材（22b）')
    # u43.5 の合わせ梁の西の端（10-30、監修の項 0552、力の道）：穴の上の縁が丸い桁の上端に線で当たるだけ（端から 18 離れ、端の 300 以内に支え無し）。
    #   穴の上の縁を桁の上で平らに 40 上げ、そのあいだに受け材（平らな面だけの押し出し、板と同じ厚み、22b）を挟む：下の面は桁のいちばん高い所に、
    #   上の面は穴の平らな上の縁に面で触れる。端の側へ 200・内へ 150 の幅
    _n_rp = 0
    _GIRTM = []
    for gi in _GIR:
        T_ = tri.tri_extrusion(gi[1])
        if len(T_): tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(); _GIRTM.append(tm_)
    for w in [x for x in _WOOD if x[3] == NAME_RAF and not TAMEDIA]:          # 10-31：一枚の梁は桁のピンで留まる（受け材はやめた）
        g1_ = w[4]; F1_ = _frame_of(g1_); A1_, B1_ = _path(g1_); th1_ = float(np.linalg.norm(B1_ - A1_)); pd1_ = (B1_ - A1_) / th1_
        X1_ = _v3(g1_.GetProfilePlane(0.0).XAxis); Y1_ = _v3(g1_.GetProfilePlane(0.0).YAxis)
        Gs_ = []
        for tm_ in _GIRTM:
            for f_ in (0.02, 0.25, 0.5, 0.75, 0.98):
                sc_ = tm_.section(plane_origin=A1_ + pd1_ * th1_ * f_, plane_normal=pd1_)
                if sc_ is None: continue
                for lp_ in sc_.discrete:
                    if len(lp_) < 3: continue
                    q_ = Polygon(_l2sz(F1_, np.c_[(lp_ - A1_) @ X1_, (lp_ - A1_) @ Y1_])).buffer(0)
                    if q_.area > 500.0 and uv(*(F1_['A'][:2] + F1_['hw'] * q_.centroid.x + F1_['hm']))[1] < -9.0: Gs_.append(q_)
        if not Gs_: continue
        sec_ = unary_union(Gs_); zt_ = sec_.bounds[3]
        hk_ = None
        for k_ in range(1, g1_.ProfileCount):
            if _poly_sz(g1_, F1_, k_).intersects(sec_): hk_ = k_
        if hk_ is None: continue
        hp_ = _poly_sz(g1_, F1_, hk_)
        top_pt_ = [c_ for g_ in getattr(sec_, 'geoms', [sec_]) for c_ in np.asarray(g_.exterior.coords) if c_[1] > zt_ - 0.5]
        s0_ = float(np.mean([c_[0] for c_ in top_pt_])); dw_ = -_dv(F1_)                 # 端（西）の側の s の向き
        sa_, sb_ = sorted((s0_ - dw_ * 150.0, s0_ + dw_ * 200.0))
        pad_ = Polygon([(sa_, zt_ + 0.05), (sb_, zt_ + 0.05), (sb_, zt_ + 40.0), (sa_, zt_ + 40.0)])
        hn_ = unary_union([hp_, Polygon([(sa_, zt_ - 20.0), (sb_, zt_ - 20.0), (sb_, zt_ + 40.0), (sa_, zt_ + 40.0)])]).buffer(0)
        hn_ = _clean_poly(max(getattr(hn_, 'geoms', [hn_]), key=lambda q: q.area).simplify(0.3))
        op1_ = _poly_sz(g1_, F1_, 0)
        if not op1_.buffer(-40.0).contains(hn_): log.append('  !! u43.5 の梁の西の受け材：穴が板の縁に近い、作らない'); continue
        e_ = r.Extrusion()
        nc0_ = g1_.Profile3d(0, 0.0).ToNurbsCurve(); W_ = extedit._weights(nc0_); P_ = extedit._pts(nc0_)
        extedit._set_pts(nc0_, np.c_[(P_ - F1_['A']) @ F1_['X'], (P_ - F1_['A']) @ F1_['Y'], np.zeros(len(P_))], W_)
        if not (e_.SetPathAndUp(g1_.PathStart, g1_.PathEnd, g1_.GetProfilePlane(0.0).YAxis) and e_.SetOuterProfile(nc0_, True)): continue
        ok_ = True
        for k_ in range(1, g1_.ProfileCount):
            if k_ == hk_: crv_ = r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in _sz2l(F1_, np.asarray(hn_.exterior.coords))]).ToNurbsCurve()
            else:
                crv_ = g1_.Profile3d(k_, 0.0).ToNurbsCurve(); W2_ = extedit._weights(crv_); P2_ = extedit._pts(crv_)
                extedit._set_pts(crv_, np.c_[(P2_ - F1_['A']) @ F1_['X'], (P2_ - F1_['A']) @ F1_['Y'], np.zeros(len(P2_))], W2_)
            ok_ = ok_ and e_.AddInnerProfile(crv_)
        if not ok_: continue
        ep_ = r.Extrusion()
        pad_ = _clean_poly(pad_.simplify(0.3))
        if not (ep_.SetPathAndUp(g1_.PathStart, g1_.PathEnd, g1_.GetProfilePlane(0.0).YAxis) and
                ep_.SetOuterProfile(r.Polyline([r.Point3d(float(x_), float(y_), 0.0) for x_, y_ in _sz2l(F1_, np.asarray(pad_.exterior.coords))]).ToNurbsCurve(), True)): continue
        _wset(w, e_)
        at_ = r.ObjectAttributes(); at_.LayerIndex = L22B; at_.Name = '合わせ梁の受け材（u43.5 の西の端、桁の上と穴の平らな上の縁のあいだ、平らな面だけ）'
        _XNEW.append((ep_, at_)); _n_rp += 1
    log.append(f'西館：u43.5 の合わせ梁の西の端の穴に受け材 {_n_rp} 個（桁の上に面で載る）')
    log.append(f'西館：母屋 {_npur} 本（一本ずつの 60×150 の押し出し。10-28 夕：u21〜51 すべて、となりの梁の同じ高さの点を結ぶ水平のまっすぐな材、屋根の面との差 最大 {_dpur:.1f} mm）')
    log.append(f'西館：屋根の構成（10-27夜・10-28）：梁の上 {RT_W:.0f}（通気垂木 45・野地 24・屋根材 40、軒は野地＋屋根材 64 を 150 持ち出し、軒先の見付け 64）、梁のあいだに断熱 150（20）・合板 t24（20r）・母屋 60×150 @455（20v）、軒の下は母屋を梁の上端に落とし込む')
    # 筋の両側の梁の下端（鏡面の板の下の端）：2 枚の梁（22b）に下から鉛直の線を当てる
    _bmt = [closed_mesh(EXT[str(o.Attributes.Id)] if str(o.Attributes.Id) in EXT else bm.get(str(o.Attributes.Id), cur_g(o))) for o in m.Objects if o.Attributes.LayerIndex == L22B]   # 10-29 昼：いまの形（端の上の角を直角にした後）で
    _BT = trimesh.util.concatenate([trimesh.Trimesh(mesh_V(g_), np.array([[g_.Faces[i][0], g_.Faces[i][1], g_.Faces[i][2]] for i in range(g_.Faces.Count)]), process=False) for g_ in _bmt])
    _BI = trimesh.ray.ray_triangle.RayMeshIntersector(_BT)
    _BIT = trimesh.ray.ray_triangle.RayMeshIntersector(_BT)                  # 梁の上端（上から当てる）
    def beam_bottom(P):
        org = np.c_[P[:, 0], P[:, 1], np.zeros(len(P))]; d = np.tile([0, 0, 1.0], (len(P), 1))
        loc, ir, _ = _BI.intersects_location(org, d, multiple_hits=True)
        zb = np.full(len(P), np.nan)
        for (x, y, z), k in zip(loc, ir):
            if np.isnan(zb[k]) or z < zb[k]: zb[k] = z
        return zb
    L20M = new_layer('20m_西館_光の筋の鏡面（アルミ）', (200, 205, 210))
    a20m = r.ObjectAttributes(); a20m.LayerIndex = L20M
    def mirror(cc, ax, nrm, t0, t1, a, b_, ztop_d, step=250.0):
        """筋の側面（nrm の a〜b_）に、梁の下端から屋根の面＋ztop_d までの薄い板。一枚の平らな板＝鉛直の面の輪郭を厚さの方向に押し出した
        一つの押し出し（10-27夜：前は step ごとの角柱を一つの網目にまとめていて、Rhino 版で 1 枚 約 145 KB の面の集まりだった）"""
        sgn = 1 if a > 0 else -1
        ts = np.r_[np.arange(t0, t1, step), t1]
        P2 = np.array([cc + ax * t_ + nrm * a for t_ in ts])
        zt_ = roof_z(P2) + ztop_d; zb_ = beam_bottom(P2 + nrm * sgn * 45.0)       # 梁の中ほど（筋の縁から 45 外）の下端
        zb_ = np.where(np.isnan(zb_), zt_ - ztop_d - 600.0, zb_)
        from shapely.geometry import Polygon as _Pg
        pg = _Pg(list(zip(ts, zt_)) + list(zip(ts[::-1], zb_[::-1]))).buffer(0).simplify(2.0)
        if pg.geom_type != 'Polygon' or pg.area < 1e3: return None
        Q = [np.r_[cc + ax * t_ + nrm * a, z_] for t_, z_ in np.asarray(pg.exterior.coords)]
        crv = r.Polyline([r.Point3d(*map(float, q_)) for q_ in Q]).ToNurbsCurve()
        th = float(b_ - a); best = None; want = cc + ax * (t0 + t1) / 2 + nrm * (a + b_) / 2
        for e_ in (r.Extrusion.Create(crv, th, True), r.Extrusion.Create(crv, -th, True)):
            if e_ is None: continue
            bb_ = e_.GetBoundingBox(); d_ = abs((np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2]) - want) @ nrm)
            if best is None or d_ < best[0]: best = (d_, e_)
        return None if best is None else best[1]
    L22T = None; _n22t = 0; _n20t = 0; _gdev = 0.0
    for cc, ax, nrm, t0, t1 in slits:
        uc_ = uv(*cc)[0]; e = 1 if np.dot(ax, np.array(xy(uc_, EASTV)) - np.array(xy(uc_, -10))) > 0 else -1     # 東（高い側）の向き
        tE = t1 if e > 0 else t0; tW = t0 if e > 0 else t1
        lo, hi = min(tW, tE), max(tW, tE)
        # 10-29 昼（監修の項 20261029-0928 の 5）：筋・立ち上がり・ガラスの西の端は外壁の内面の線（斜めの壁では線に沿って斜めに）。
        # 西の端の立ち上がり 60 は線の内側の 60 の帯、ガラスは線まで（前は線の外へ 60 出し、筋は芯の所で直角に止めていた）
        _WIN60 = WSi_W.buffer(-60.0, join_style=2)
        # 東の端は越屋根の西の立ち上がりがふさぐ（端の立ち上がりは足さない）
        # 西の端（外壁の内面の線、10-27夕）に端の立ち上がり 60（水は端の立ち上がりを越えて屋根の上を軒樋へ）
        # 乳白ガラス（複層：遮熱 Low-E＋乳白の合わせ）：越屋根の立ち上がりから外壁の内面の線まで、平らな板（帯の形の多角形を、屋根の面に
        # 当てはめた平面の上で厚さ 12 に押し出す。面との差が 4 を超える所（ねじれた面）は筋の向きに分ける。10-29 昼：前は 500 の格子ごとの角柱の集まり）
        def _gplate20(pg_, dz_=RT_W + 60.0, th_=12.0, at_p=None, depth_=0):
            """平面形 pg_ を屋根の面＋dz_ に当てはめた平面の上の板（厚さ th_）。面との差が 4 を超えれば筋の向きに二つに分ける。at_p＝None はガラス"""
            global _gdev, _n20t
            pgs_ = [q for q in getattr(pg_, 'geoms', [pg_]) if q.geom_type == 'Polygon' and q.area > 200.0]
            if len(pgs_) != 1:
                for q in pgs_: _gplate20(q, dz_, th_, at_p, depth_)
                return
            pg_ = pgs_[0].simplify(0.5)
            Gs_ = np.array([np.asarray(pg_.representative_point().coords[0])] + [np.asarray(pg_.exterior.interpolate(f_, normalized=True).coords[0]) for f_ in np.linspace(0, 1, 80, endpoint=False)])
            Gz_ = np.array([_RWf['roof_f'](*q_) for q_ in Gs_]) + dz_
            A_ = np.c_[np.ones(len(Gs_)), Gs_ - Gs_[0]]; cf_, *_ = np.linalg.lstsq(A_, Gz_, rcond=None)
            dev_ = float(np.abs(A_ @ cf_ - Gz_).max())
            if dev_ > 4.0 and depth_ < 6:
                tt_ = (np.asarray(pg_.exterior.coords) - cc) @ ax; tm_ = (tt_.min() + tt_.max()) / 2
                for a_, b_ in ((tt_.min() - 10.0, tm_), (tm_, tt_.max() + 10.0)):
                    _gplate20(pg_.intersection(strip(cc, ax, nrm, a_, b_, -400, 400)), dz_, th_, at_p, depth_ + 1)
                return
            _gdev = max(_gdev, dev_) if at_p is None else _gdev
            zg_ = lambda q_: float(cf_[0] + (np.asarray(q_) - Gs_[0]) @ cf_[1:])
            Qg_ = [r.Point3d(float(x_), float(y_), zg_((x_, y_))) for x_, y_ in np.asarray(pg_.exterior.coords)]
            crv_ = r.Polyline(Qg_).ToNurbsCurve(); best_ = None
            for ex_ in (r.Extrusion.Create(crv_, th_, True), r.Extrusion.Create(crv_, -th_, True)):
                if ex_ is None: continue
                bb_ = ex_.GetBoundingBox(); zc_ = (bb_.Min.Z + bb_.Max.Z) / 2 - zg_(((bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2))
                if best_ is None or zc_ > best_[0]: best_ = (zc_, ex_)
            if best_ is not None:
                _XNEW.append((best_[1], at_g2 if at_p is None else at_p))
                if at_p is None: _n20t += 1
        _gplate20(_slit_band(cc, ax, nrm, t0, t1, -150, 150))
        # 立ち上がり 60（両側と西の端）も平らな板の押し出し（10-29 昼：前は 500 の格子ごとの角柱の網目で、端に 3 mm の離れた片ができていた）
        for pu_ in (_slit_band(cc, ax, nrm, t0, t1, -150, -90).intersection(_WIN60), _slit_band(cc, ax, nrm, t0, t1, 90, 150).intersection(_WIN60),
                    _slit_band(cc, ax, nrm, t0, t1, -150, 150).difference(_WIN60),
                    strip(cc, ax, nrm, min(tE, tE - 60.0 * e), max(tE, tE - 60.0 * e), -150, 150)):     # 10-31：東の端（排気のスリットの西の縁）にも立ち上がり 60
            _gplate20(pu_, RT_W, 60.0, a20)
        _pts = [True]; tS = tW                                                   # 筋の西の端＝外壁の内面の線（外皮の線の固定ガラスは要らなくなった）
        for a_, b_ in ((-90, -88), (88, 90)):                                                    # 筋の内側：ガラスの下から梁の下端まで鏡面のアルミ t2
            # 10-29 夕（監修の項 1530）：鏡面の西の端も、その側の線が外壁の内面（WSi_W、屋根の穴の高さでの外壁の内面と同じ線）を切る所（斜めの壁で筋の芯の所で止めない）
            _ln = LineString([cc + ax * (t0 - 3000.0) + nrm * (a_ + b_) / 2, cc + ax * (t1 + 3000.0) + nrm * (a_ + b_) / 2]).intersection(WSi_W.exterior)
            _xs = [float((np.array([q.x, q.y]) - cc - nrm * (a_ + b_) / 2) @ ax) for q in ([_ln] if _ln.geom_type == 'Point' else [q for q in getattr(_ln, 'geoms', []) if q.geom_type == 'Point'])]
            t0m, t1m = t0, t1
            if _xs:
                tWs = min(_xs, key=lambda t: abs(t - tW))
                if e > 0: t0m = tWs
                else: t1m = tWs
            _mx = mirror(cc, ax, nrm, t0m, t1m, a_, b_, RT_W + 60.0)
            if _mx is not None: _XNEW.append((_mx, a20m))
        # 光の筋をまたいで屋根の面をつなぐ（10-27、ユーザー・監修の略算、決定事項（共通）の「地震の力は骨格で受ける」）：2 枚の梁の上端に
        # 溝をまたぐ鋼の平板 6×60（長さ 340、梁の上端に彫り込み、22t）を約 0.9 mおき、外壁の内面から越屋根の側まで。筋の両端は溝をまたぐ縁の材
        # （杉 60×150、垂木の高さ、鏡面のあいだ、垂木と同じ 20v）：越屋根の側と軒先の側。屋根の上からの見えは変えない。本館の 10k と同じ。
        if L22T is None: L22T = new_layer('22t_西館_光の筋をまたぐつなぎ（鋼の平板・縁の材）', (120, 120, 125))
        tIn = (tS if _pts else tW + 1200.0 * e) + 300.0 * e; tOut = tE - 300.0 * e          # 平板の範囲（外壁の内面の内 0.3 〜 越屋根の側の 0.3 手前）
        # 10-28（監修の項 2346）：平板・縁の材は一つずつの押し出し（筋をまたぐ向きに水平、勾配の向きは屋根の面に沿う。前は屋根に沿わせた網目を筋ごとに一つに）
        def _span_box(ta_, tb_, w0_, w1_, z0_, z1_, at_):
            zr_ = lambda t_: float(_RWf['roof_f'](*(cc + ax * t_)))
            Q = [np.r_[cc + ax * ta_ + nrm * w0_, zr_(ta_) + z0_], np.r_[cc + ax * tb_ + nrm * w0_, zr_(tb_) + z0_],
                 np.r_[cc + ax * tb_ + nrm * w0_, zr_(tb_) + z1_], np.r_[cc + ax * ta_ + nrm * w0_, zr_(ta_) + z1_]]
            crv = r.Polyline([r.Point3d(*map(float, q_)) for q_ in Q + [Q[0]]]).ToNurbsCurve()
            L_ = float(w1_ - w0_); want = cc + ax * (ta_ + tb_) / 2 + nrm * (w0_ + w1_) / 2; best = None
            for ex_ in (r.Extrusion.Create(crv, L_, True), r.Extrusion.Create(crv, -L_, True)):
                if ex_ is None: continue
                bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2]) - want)
                if best is None or dm < best[0]: best = (dm, ex_)
            if best is not None: _XNEW.append((best[1], at_))
        def _ply_top(q2_):
            loc_, ir_, _ = _BIT.intersects_location(np.array([[q2_[0], q2_[1], 20000.0]]), np.array([[0.0, 0.0, -1.0]]), multiple_hits=False)
            return float(loc_[0][2]) if len(loc_) else float(_RWf['roof_f'](*q2_))
        def _plate_x(t_, at_):
            """鋼の平板 6×60×340：筋をまたぐ向きに、両側の梁のそれぞれの上端に載る（10-29 昼：前は筋の芯の屋根の面の高さの水平な板で、
            2 枚の上端が違う北西の架構（u45・48）で片側の梁から 8〜47 浮き、梁の頭の丸みの上でも浮いていた。ユーザー「梁の上の分離したトゲトゲ」）"""
            zA_ = _ply_top(cc + ax * t_ - nrm * 135.0); zB_ = _ply_top(cc + ax * t_ + nrm * 135.0)
            Q = [np.r_[cc + ax * (t_ - 30.0) - nrm * 170.0, zA_ - 6.0], np.r_[cc + ax * (t_ - 30.0) + nrm * 170.0, zB_ - 6.0],
                 np.r_[cc + ax * (t_ - 30.0) + nrm * 170.0, zB_], np.r_[cc + ax * (t_ - 30.0) - nrm * 170.0, zA_]]
            crv = r.Polyline([r.Point3d(*map(float, q_)) for q_ in Q + [Q[0]]]).ToNurbsCurve(); best = None; want = cc + ax * t_
            for ex_ in (r.Extrusion.Create(crv, 60.0, True), r.Extrusion.Create(crv, -60.0, True)):
                if ex_ is None: continue
                bb_ = ex_.GetBoundingBox(); dm = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2]) - want)
                if best is None or dm < best[0]: best = (dm, ex_)
            if best is not None: _XNEW.append((best[1], at_))
        _nk1 = 0
        for t_ in np.arange(min(tIn, tOut), max(tIn, tOut) + 1.0, 900.0):
            a_k = r.ObjectAttributes(); a_k.LayerIndex = L22T; a_k.Name = f'光の筋をまたぐ鋼の平板 6×60×340（架構 u{uc_:.0f}）'
            _plate_x(t_, a_k); _nk1 += 1
        _n22t += _nk1
        for ta_, tb_, nm_ in ((tW, tW + 60.0 * e, '外壁の側'),):                    # 10-31：東の端はスリットの西の縁の材がふさぐ
            a_e = r.ObjectAttributes(); a_e.LayerIndex = L20V; a_e.Name = f'光の筋の端の縁の材（杉、通気垂木の高さ、{nm_}、架構 u{uc_:.0f}）'   # 杉は垂木の層（一つのレイヤーには一つの素材、10-27夕）
            a_e.ColorSource = r.ObjectColorSource.ColorFromObject; a_e.ObjectColor = (196, 160, 118, 255)
            _span_box(min(ta_, tb_), max(ta_, tb_), -87.0, 87.0, 0.0, VENT_TOP, a_e)
    # ================================================================ 棟のガラスの帯（10-30 ユーザー 22:20、10-31 08:00 の直し）
    # 越屋根をやめ、「越屋根を屋根の面に沈める」。10-31（ユーザー）：棟の所の屋根の外形は外から見て一枚の板。
    # - ガラスの帯：棟（東の縁 v −0.9、8150）から屋根の面に沿う幅 1.6 m（v −0.9〜EASTV）を、屋根の面と同じ勾配・同じ厚み（通気垂木の上から屋根の上面まで
    #   64、上面は屋根の上面と一つの面）の複層ガラス（外に Low-E、内に型板、20t）の板に。東へは同じ面のまま 350 伸ばして軒（本館とのすき間の上、前の水平な
    #   水切りはやめた）。南北は屋根の端から端まで（妻の軒の出の上も）。下は帯の西の縁の材と東の外壁（削る段で外壁の上端をガラスの下面に合わせる）が受ける。
    # - 排気のスリット：帯の西の縁と太陽光の屋根のあいだ（v EASTV −0.15〜EASTV、南北の妻の壁の内面のあいだ）に幅 150 のすき間だけを見せる。中に閉じられる窓
    #   （合板の高さ、複層、自動の開け閉め：外気が涼しいとき・タイマー・雨と強い風で閉じる）と、その上に雨受けの樋（両脇 30 のすき間を空気が通る）を隠す。
    #   緩い屋根（約14°）の棟の近くは風向きによらず負圧なので吸い出す。
    # - 日よけ：本館の越屋根と同じ薄いルーバー（幅 120・ピッチ 104・水平に 30° で東が高い・両面白の艶消し、羽根の下の縁はガラスの上 10）を帯の上に南の端から
    #   北の端まで連続で（30）。
    # - 構面：帯で途切れる合板は、2 枚の梁（3 mおき）に加え、光の筋と同じ鋼の平板 6×60（22t）で帯をまたいで東の外壁の上へ（天井扇の吊り棒もこの平板から）。
    # - 夜の LED（29、発光）は帯の西の縁と棟の側の縁のガラスの下。
    _FRL = [21.33] + [24.0 + 3.0 * k for k in range(7)] + [43.5, 45.0, 48.0, U_F18]     # 架構の線（梁の芯）
    _rf = lambda u_, v_: float(_RWf['roof_f'](*np.ravel(xy(u_, v_))))
    _ZG0 = BAT_T; _GT = RT_W - BAT_T                                              # ガラスの下の面（屋根の面から）・厚さ（屋根の板と同じ 64）
    BV_E, BV_W = BAND_VE, EASTV                                                   # ガラスの東（軒先）・西の縁
    L29 = new_layer('29_西館_棟のガラスの帯_LED（帯の縁、発光）', (255, 211, 77))
    L30 = new_layer('30_西館_棟のガラスの帯_日よけのルーバー（白の艶消し）', (236, 232, 222))
    _n_bg = _n_lv = _n_led = _n_bp = _n_sw = 0
    def _plane_plate(pg_, dz_, th_, at_, depth_=0):
        """平面形 pg_ を屋根の面＋dz_ に当てはめた平面の上の板（厚さ th_、上へ）。面との差が 2 を超えれば u の向きに二つに分ける"""
        pgs_ = [q for q in getattr(pg_, 'geoms', [pg_]) if q.geom_type == 'Polygon' and q.area > 500.0]
        if len(pgs_) != 1:
            return sum(_plane_plate(q, dz_, th_, at_, depth_) for q in pgs_)
        pg_ = pgs_[0].simplify(0.5)
        Gs_ = np.array([np.asarray(pg_.representative_point().coords[0])] + [np.asarray(pg_.exterior.interpolate(f_, normalized=True).coords[0]) for f_ in np.linspace(0, 1, 80, endpoint=False)])
        Gz_ = np.array([_RWf['roof_f'](*q_) for q_ in Gs_]) + dz_
        A_ = np.c_[np.ones(len(Gs_)), Gs_ - Gs_[0]]; cf_, *_ = np.linalg.lstsq(A_, Gz_, rcond=None)
        if float(np.abs(A_ @ cf_ - Gz_).max()) > 2.0 and depth_ < 7:
            us_ = [uv(*q_)[0] for q_ in np.asarray(pg_.exterior.coords)]; um_ = (min(us_) + max(us_)) / 2
            return (_plane_plate(pg_.intersection(R(min(us_) - 0.1, um_, -20.0, 2.0, 0.05)), dz_, th_, at_, depth_ + 1)
                    + _plane_plate(pg_.intersection(R(um_, max(us_) + 0.1, -20.0, 2.0, 0.05)), dz_, th_, at_, depth_ + 1))
        zg_ = lambda q_: float(cf_[0] + (np.asarray(q_) - Gs_[0]) @ cf_[1:])
        crv_ = r.Polyline([r.Point3d(float(x_), float(y_), zg_((x_, y_))) for x_, y_ in np.asarray(pg_.exterior.coords)]).ToNurbsCurve(); best_ = None
        for ex_ in (r.Extrusion.Create(crv_, th_, True), r.Extrusion.Create(crv_, -th_, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); zc_ = (bb_.Min.Z + bb_.Max.Z) / 2 - zg_(((bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2))
            if best_ is None or zc_ > best_[0]: best_ = (zc_, ex_)
        if best_ is None: return 0
        _XNEW.append((best_[1], at_)); return 1
    def _rprof(u_, w_, prof_, at_):
        """放射の線 u_ の鉛直の面の輪郭 prof_ [(v, z)] を u の向きに w_（m）押し出す（u_ から u_+w_）"""
        Q_ = [r.Point3d(*map(float, np.r_[np.ravel(xy(u_, v_)), z_])) for v_, z_ in prof_]
        crv_ = r.Polyline(Q_ + [Q_[0]]).ToNurbsCurve(); L_ = abs(w_) * 1000.0
        want_ = np.ravel(xy(u_ + w_ / 2, np.mean([p_[0] for p_ in prof_]))); best_ = None
        for ex_ in (r.Extrusion.Create(crv_, L_, True), r.Extrusion.Create(crv_, -L_, True)):
            if ex_ is None: continue
            bb_ = ex_.GetBoundingBox(); dm_ = np.linalg.norm(np.array([(bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2]) - want_)
            if best_ is None or dm_ < best_[0]: best_ = (dm_, ex_)
        if best_ is not None: _XNEW.append((best_[1], at_))
        return best_ is not None
    def _att(li_, nm_):
        a_ = r.ObjectAttributes(); a_.LayerIndex = li_; a_.Name = nm_; return a_
    def _chunks(a_, b_, d_):
        xs_ = list(np.arange(a_, b_ - 1e-6, d_)) + [b_]; return list(zip(xs_, xs_[1:]))
    # 10-31（ユーザー 11:26〜11:31・12:xx）：ガラスに限らず材料はできるだけ大きな平面で、屋根の形に沿って折る。棟は弧なので一本の直方体にはならない。
    #   u21〜43.5：架構の線（梁の芯）で区切った区間ごとに一枚の平らな板（両端の棟の点を通り、帯の西の縁の 2 点にいちばん近い平面。ずれ 7 mm 以下）。
    #   北西（u43.5〜51.3）：屋根がねじれる（双一次）ので、区間の四角を対角線で分けた 2 枚の三角形の平らな板（4 隅は屋根の面にぴったり、隣の区間とも
    #   架構の線で段なく折れる）。対角線はどの区間も同じ向き（南の端の軒の側の隅 → 北の端の西の縁の隅）で、三角が揃って並ぶ。ルーバーも同じ区切り。
    #   帯のまわりの物（スリットの縁の材・窓・樋・網・LED）は区間ごとの平らな板（幅が狭いのでねじれは小さい）
    _SEGU = [BAND_UL] + [f_ for f_ in _FRL if BAND_UL + 0.3 < f_ < BAND_UH - 0.3] + [BAND_UH]
    _UTRI = 43.5                                                                   # これより北は三角形
    _zR = lambda u_, v_, dz_: float(_RWf['roof_f'](*np.ravel(xy(u_, v_)))) + dz_
    def _plane3(P3_):
        """3 点（x, y, z）を通る平面の係数 (c0, c1, c2)：z = c0 + c1 x + c2 y"""
        A_ = np.c_[np.ones(3), np.array([p_[:2] for p_ in P3_])]; return np.linalg.solve(A_, np.array([p_[2] for p_ in P3_]))
    def _planeW(P3_, W_):
        A_ = np.c_[np.ones(len(P3_)), np.array([p_[:2] for p_ in P3_])] * np.array(W_)[:, None]
        return np.linalg.lstsq(A_, np.array([p_[2] for p_ in P3_]) * np.array(W_), rcond=None)[0]
    _zc = lambda cf_, x_, y_: float(cf_[0] + cf_[1] * x_ + cf_[2] * y_)
    def _flat_plate(poly_, cf_, th_, at_):
        """平面形 poly_（xy）を平面 cf_ の上に置いた厚さ th_ の板（平面に直角に上へ押し出す、Extrusion）"""
        pgs_ = [q for q in getattr(poly_, 'geoms', [poly_]) if q.geom_type == 'Polygon' and q.area > 200.0]
        n_ = 0
        for pg_ in pgs_:
            pg_ = pg_.simplify(0.2)
            crv_ = r.Polyline([r.Point3d(float(x_), float(y_), _zc(cf_, x_, y_)) for x_, y_ in np.asarray(pg_.exterior.coords)]).ToNurbsCurve(); best_ = None
            for ex_ in (r.Extrusion.Create(crv_, th_, True), r.Extrusion.Create(crv_, -th_, True)):
                if ex_ is None: continue
                bb_ = ex_.GetBoundingBox(); zcen_ = (bb_.Min.Z + bb_.Max.Z) / 2 - _zc(cf_, (bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2)
                if best_ is None or zcen_ > best_[0]: best_ = (zcen_, ex_)
            if best_ is not None: _XNEW.append((best_[1], at_)); n_ += 1
        return n_
    def _P(u_, v_): return np.ravel(xy(u_, v_))
    # ガラスの面（下の面）：区間ごと [(平面形, 係数)]
    _FACETS = []; _gdev = 0.0
    for ua_, ub_ in zip(_SEGU, _SEGU[1:]):
        q_ = Polygon([_P(ua_, BV_W), _P(ub_, BV_W), _P(ub_, BV_E), _P(ua_, BV_E)])
        if ub_ <= _UTRI + 1e-6:
            pts_ = [(*_P(u_, v_), _zR(u_, v_, _ZG0)) for u_ in (ua_, ub_) for v_ in (-0.9, BV_W)]
            cf_ = _planeW(pts_, [100.0, 1.0, 100.0, 1.0])                          # 棟の 2 点はほぼ通す
            _gdev = max(_gdev, max(abs(_zc(cf_, *_P(u_, v_)) - _zR(u_, v_, _ZG0)) for u_ in np.linspace(ua_, ub_, 7) for v_ in np.linspace(BV_W, -0.9, 5)))
            _FACETS.append((ua_, ub_, [(q_, cf_)]))
        else:
            cA, cB, cC, cD = (ua_, BV_W), (ub_, BV_W), (ub_, BV_E), (ua_, BV_E)        # 西の縁の南・北、軒の側の北・南
            T1 = Polygon([_P(*cA), _P(*cB), _P(*cD)]); T2 = Polygon([_P(*cB), _P(*cC), _P(*cD)])     # 対角線：南の軒の側の隅 D → 北の西の縁の隅 B
            f1 = _plane3([(*_P(*c_), _zR(*c_, _ZG0)) for c_ in (cA, cB, cD)]); f2 = _plane3([(*_P(*c_), _zR(*c_, _ZG0)) for c_ in (cB, cC, cD)])
            _FACETS.append((ua_, ub_, [(T1, f1), (T2, f2)]))
    for ua_, ub_, fl_ in _FACETS:
        for pg_, cf_ in fl_:
            _n_bg += _flat_plate(pg_, cf_, _GT, _att(L20T, '棟のガラスの帯（複層：外に Low-E、内に型板、屋根の面と同じ勾配・同じ厚み 64、架構の線で折る平らな板（北西は三角形）、東へ 350 の軒）'))
    def _facet_at(x_, y_):
        p_ = Point(x_, y_)
        best_ = None
        for ua_, ub_, fl_ in _FACETS:
            for pg_, cf_ in fl_:
                d_ = pg_.distance(p_)
                if best_ is None or d_ < best_[0]: best_ = (d_, cf_)
        return best_[1]
    # スリットとその縁の材・窓・樋・網：架構の線で区切った区間ごとの平らな板（板（梁）の所は除く、網は梁の上も通す）
    def _seg_box(ua_, ub_, v0_, v1_, cf_, dz0_, dz1_, at_):
        C_ = [_P(ua_, v0_), _P(ub_, v0_), _P(ub_, v1_), _P(ua_, v1_)]
        V_ = [(*c_, _zc(cf_, *c_) + dz0_) for c_ in C_] + [(*c_, _zc(cf_, *c_) + dz1_) for c_ in C_]
        F_ = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
        tm_ = trimesh.Trimesh(np.array(V_), F_, process=False)
        if tm_.volume < 0: tm_.invert()
        mm_ = r.Mesh()
        for x_, y_, z_ in tm_.vertices: mm_.Vertices.Add(float(x_), float(y_), float(z_))
        for f_ in tm_.faces: mm_.Faces.AddFace(int(f_[0]), int(f_[1]), int(f_[2]))
        mm_.Normals.ComputeNormals(); mm_.Compact(); new_objs.append((mm_, at_)); return 1
    _SEGS = [BAND_U[0]] + [f_ for f_ in _FRL if BAND_U[0] + 0.3 < f_ < BAND_U[1] - 0.3] + [BAND_U[1]]
    for ua_, ub_ in zip(_SEGS, _SEGS[1:]):
        a_ = ua_ + (0.19 if ua_ in _FRL else 0.0); b_ = ub_ - (0.19 if ub_ in _FRL else 0.0)
        cf_ = _planeW([(*_P(u_, v_), _zR(u_, v_, 0.0)) for u_ in (ua_, ub_) for v_ in (SLIT_W, BV_W + 0.06)], [1.0] * 4)   # スリットのあたりの屋根の面（梁の上端）
        _seg_box(a_, b_, BV_W, BV_W + 0.06, cf_, -INS_T - PLY_T, _ZG0 - 25.0, _att(L20V, '帯の縁の材（杉 60、合板の下からガラスの下まで、排気のスリットの東の縁）'))
        _seg_box(a_, b_, SLIT_W, SLIT_W + 0.06, cf_, -INS_T - PLY_T, RT_W, _att(L20V, 'スリットの縁の材（杉 60、合板の下から屋根の上面まで、上は金属で包む、排気のスリットの西の縁）'))
        _seg_box(a_, b_, SLIT_W + 0.06, BV_W, cf_, -INS_T - PLY_T, -INS_T, _att(new_layer('19_西館_建具・ガラス（南の入口・窓）', (127, 179, 213)), '排気のスリットの窓（閉じられる、複層、自動の開け閉め：外気が涼しいとき・タイマー・雨と強い風で閉じる、吹き上げに耐える留め方）')); _n_sw += 1
        _seg_box(a_ + 0.03, b_ - 0.03, SLIT_W + 0.09, BV_W - 0.03, cf_, -110.0, -50.0, _att(new_layer('21g_西館_軒樋・鎖樋（道路の側）', (150, 150, 150)), '排気のスリットの中の雨受けの樋（金属、窓の上、両脇 30 のすき間を空気が通る、両端で外へ）'))
        _seg_box(ua_, ub_, SLIT_W + 0.06, BV_W, cf_, RT_W - 20.0, RT_W - 15.0, _att(L20, '排気のスリットの防虫網（ステンレスの細かい網、屋根の上面の 15 下、外からはすき間に見える）'))
    # LED（帯の西の縁と棟の側の縁、ガラスの下 20×20、区間ごと、ガラスの面から 25〜45 下）
    for ua_, ub_, fl_ in _FACETS:
        a_, b_ = max(ua_, BAND_U[0]), min(ub_, BAND_U[1])
        if b_ - a_ < 0.3: continue
        for v0_, v1_ in ((BV_W + 0.06, BV_W + 0.08), (-1.08, -1.06)):
            cf_ = _planeW([(*_P(u_, v_), _zc(_facet_at(*_P(u_, v_)), *_P(u_, v_))) for u_ in (a_ + 0.01, b_ - 0.01) for v_ in (v0_, v1_)], [1.0] * 4)
            _seg_box(a_, b_, v0_, v1_, cf_, -45.0, -25.0, _att(L29, 'LED 20×20（棟のガラスの帯の縁、ガラスの下、夜に帯が光の線になる）')); _n_led += 1
    # 日よけのルーバー（本館の越屋根と同じ：幅 120・ピッチ 104・水平に 30° で東が高い・厚さ 18、羽根の下の縁はガラスの上 10）：ガラスと同じ区切り（区間・三角形）の平らな板
    _WL, _ANG = 120.0, math.radians(30.0); _dh, _rise = _WL * math.cos(_ANG) / 1000.0, _WL * math.sin(_ANG)
    for ua_, ub_, fl_ in _FACETS:
        vw_ = BV_W + 0.02
        while vw_ + _dh <= BV_E - 0.01:
            ve_ = vw_ + _dh
            blade_ = Polygon([_P(ua_ + 0.005, vw_), _P(ub_ - 0.005, vw_), _P(ub_ - 0.005, ve_), _P(ua_ + 0.005, ve_)])
            for pg_, cf_ in fl_:
                pc_ = blade_.intersection(pg_)
                for pp_ in [q for q in getattr(pc_, 'geoms', [pc_]) if q.geom_type == 'Polygon' and q.area > 500.0]:
                    C_ = np.asarray(pp_.exterior.coords)[:-1]
                    tgt_ = [(x_, y_, _zc(cf_, x_, y_) + _GT + 10.0 + _rise * (uv(x_, y_)[1] - vw_) / _dh) for x_, y_ in C_]
                    cb_ = _planeW(tgt_, [1.0] * len(tgt_))
                    _n_lv += _flat_plate(pp_, cb_, 18.0, _att(L30, '日よけのルーバー（本館の越屋根と同じ、幅 120・ピッチ 104・水平に 30° で東が高い、両面白の艶消し、ガラスと同じ区切りの平らな板）'))
            vw_ += 0.104
    # 帯をまたぐ鋼の平板 6×60（合板の上面の高さ、スリットの西の 0.3 内から東の外壁の内面 v −1.05 まで）：約 0.9 mおき＋天井扇の所
    _FANU = [22.5, 25.5, 28.5, 31.5, 34.5, 37.5, 40.5, 43.5, 46.5, 49.5]
    _pu = [u_ for u_ in np.arange(BAND_U[0] + 0.45, BAND_U[1] - 0.2, 0.9) if min(abs(u_ - f_) for f_ in _FRL) > 0.3 and min(abs(u_ - f_) for f_ in _FANU) > 0.45]
    for u_ in sorted(_pu + _FANU):
        vs_ = (SLIT_W - 0.3, -1.05)
        prof_ = [(vs_[0], _rf(u_, vs_[0]) - INS_T), (vs_[1], _rf(u_, vs_[1]) - INS_T), (vs_[1], _rf(u_, vs_[1]) - INS_T + 6.0), (vs_[0], _rf(u_, vs_[0]) - INS_T + 6.0)]
        _n_bp += _rprof(u_ - 0.03, 0.06, prof_, _att(L22T, f'棟のガラスの帯をまたぐ鋼の平板 6×60（合板から東の外壁の上へ、u{u_:.1f}）'))
    log.append(f'西館：棟のガラスの帯（10-30 越屋根をやめた、10-31 屋根と一つの面）：ガラス {_n_bg} 枚（u{BAND_UL:.2f}〜{BAND_UH:.2f}、v{BV_E}〜{BV_W}、20t、東へ 350 の軒）、'
               f'架構の線で折る平らな板（u21〜43.5 は区間ごと、屋根の面とのずれ 最大 {_gdev:.0f} mm、北西は対角線で分けた三角形）、排気のスリット（幅 150、窓 {_n_sw}・雨受けの樋）、日よけのルーバー {_n_lv} 枚（30）、LED {_n_led}（29）、帯をまたぐ鋼の平板 {_n_bp}（22t）')
    log.append(f'西館：光の筋の乳白ガラス {len(slits)} 本・{_n20t} 枚（平らな板 t12 の押し出し、西の端は外壁の内面の線、屋根の面に当てはめた平面との差 最大 {_gdev:.1f} mm、超える所は筋の向きに分けた）')
    log.append(f'西館：光の筋をまたぐつなぎ（22t）：鋼の平板 {_n22t} 枚（{len(slits)} 本の筋、約 0.9 mおき）と筋の西の端の縁の材 {len(slits)}')
    log.append(f'西館：光の筋 {len(slits)} 本（u ' + '・'.join(f'{uv(*s[0])[0]:.0f}' for s in slits) +
               f'、2 枚の梁のあいだ 180、棟のガラスの帯から外壁の内面まで、型板ガラス、20t）、屋根材型の太陽光 {pv20.area / 1e6:.0f} m²（20p）')

# ================================================================ 書き出し（桁を差し替え、腰壁を足す）
_stg0 = R(STAIR_STG[0], STAIR_STG[1], STAIR_STG[2], STAIR_STG[3], 0.05); _F36 = []    # 階段の床（36）から倉庫の分を除く（10-25）
for _o in m.Objects:
    if LN[_o.Attributes.LayerIndex].startswith('36_'):
        _f = foot(_o.Geometry)
        if _f is not None and _f.intersects(_stg0):
            _f = Polygon([xy(stair_u(_uu), stair_v(_vv)) for _uu, _vv in (uv(*c_) for c_ in _f.segmentize(200).exterior.coords)]).buffer(0)   # 階段を細くした分（10-25）・北へ延ばした分（10-27）
            _F36.append((_f, _o.Attributes.LayerIndex)); drop.add(str(_o.Attributes.Id))
_STX = R(33.0, STAIR_U1 + 0.06, -2.93, -5.06, 0.02); _F31 = []                # 箱を北へ延ばした分を遊戯室の床（31）から除く（10-27）
for _o in m.Objects:
    if LN[_o.Attributes.LayerIndex].startswith('31_') and isinstance(_o.Geometry, r.Mesh):
        _f = foot(_o.Geometry)
        if _f is not None and _f.intersection(_STX).area > 1e4:
            _F31.append((_f, _o.Attributes.LayerIndex, _o.Geometry.GetBoundingBox().Max.Z)); drop.add(str(_o.Attributes.Id))
# 2 階の東の縁を v −1.9 → −2.5 へ（10-25、ユーザー：東の帯の吹き抜けを 1.0 → 1.6、越屋根と同じ幅）と、2 階の部屋の割り直し
# （ユーザー：更衣室を客が通らないように戸、休憩室へは会議室への通路から、ホールの西の戸と休憩室の中の壁はやめる、便所と湯沸を分ける）
EDGE2 = -2.5
_F2 = {}
for _o in m.Objects:
    _ln = LN[_o.Attributes.LayerIndex]
    if not _ln.startswith(('23_', '41_', '42_', '44_', '45_', '43b_')) or not isinstance(_o.Geometry, r.Mesh): continue
    _bb = _o.Geometry.GetBoundingBox()
    if _bb.Min.Z < 3000 or _bb.Max.Z > 3400: continue
    _f = foot(_o.Geometry)
    if _f is None: continue
    _F2.setdefault(_ln[:3], []).append((_f, _o.Attributes, _bb.Min.Z, _bb.Max.Z)); drop.add(str(_o.Attributes.Id))
# ================================================================ 本館：乳児室の南の妻（本館係、10-26夜、ユーザー：比べる絵の B2＋格子）
# 開口は架構の水平に合わせ、ガラスの引き戸の上端を東の縁側の鴨居（h2385〜2445）と同じ高さで一本に通す。鴨居より上（一年中軒の影）は
# 杉の壁（大和張り）を梁の下端まで。ガラス戸の外に杉の縦格子（見付30・見込45、120おき、上の大和張りの割りとそろえる）を固定し、
# 戸を開けても格子が柵になる（はう子が外へ出ない、外気は入る）。冬至の南中の日は格子を約75%抜け、床に縞の日だまり。
# 開口は v1.75〜11.45（東の端は梁が柱の際で下がるので 0.35 の袖壁、西の受け取り土間の側の袖壁と対に）。ガラスの引き戸 6 枚（2 本のレール、引き違い 3 組）。
# 内縁側の端（v12.2〜13.5、同じ南の面・軒の下）のガラスの外にも同じ格子（室内側のガラスはそのまま）。外縁側（v13.5〜15）は通り道なので開けたまま。
def _gplate(u0_, u1_, v0_, v1_, zb_, zt_, n_=None):
    vs_ = np.linspace(v0_, v1_, n_ or max(2, int((v1_ - v0_) / 0.25) + 1)); mm = r.Mesh()
    for v_ in vs_:
        for uu_, z_ in ((u0_, zb_(v_)), (u1_, zb_(v_)), (u1_, zt_(v_)), (u0_, zt_(v_))):
            x_, y_ = xy(uu_, v_); mm.Vertices.Add(float(x_), float(y_), float(z_))
    k_ = len(vs_)
    for i in range(k_ - 1):
        b0, b1 = 4 * i, 4 * (i + 1)
        for j in range(4):
            j2 = (j + 1) % 4; mm.Faces.AddFace(b0 + j, b0 + j2, b1 + j2, b1 + j)
    mm.Faces.AddFace(0, 3, 2, 1); e_ = 4 * (k_ - 1); mm.Faces.AddFace(e_, e_ + 1, e_ + 2, e_ + 3)
    mm.Normals.ComputeNormals(); mm.Compact(); return mm
def _join(ms):
    out_ = r.Mesh()
    for mm in ms: out_.Append(mm)
    out_.Normals.ComputeNormals(); out_.Compact(); return out_
_KAM0, _KAM1 = 2385.0, 2445.0
_SV0, _SV1 = 1.75, 11.45
_BB = (lambda v: _beam_bot(v)) if '_beam_bot' in globals() else (lambda v: 3356.0 - (v - 0.525) * 83.3)
L16S = new_layer('16s_本館_南の妻のガラスの引き戸（乳児室）', (150, 200, 230))
L17G = new_layer('17g_本館_南の妻の縦格子（杉 30×45、120おき）', (169, 134, 92))
L18_ = lidx('18_'); L17_ = lidx('17_')
_pw = (_SV1 - _SV0) / 6
for i_ in range(6):                                                      # ガラスの引き戸（外のレール u0.02〜0.05、内 u0.06〜0.09、引き違い）
    a_ = _SV0 + i_ * _pw - (0.02 if i_ % 2 else 0); b_ = _SV0 + (i_ + 1) * _pw + (0.0 if i_ % 2 else 0.02)
    uu = (0.06, 0.09) if i_ % 2 else (0.02, 0.05)
    at_ = r.ObjectAttributes(); at_.LayerIndex = L16S; at_.Name = f'南の妻のガラスの引き戸（{i_ + 1}、引き違い）'
    new_objs.append((_gplate(uu[0], uu[1], max(a_, _SV0), min(b_, _SV1), lambda v: 0.0, lambda v: _KAM0 - 10.0, 2), at_))
at_ = r.ObjectAttributes(); at_.LayerIndex = L18_; at_.Name = '南の妻の鴨居（東の縁側の鴨居と同じ高さ）'
new_objs.append((_gplate(0.0, 0.11, _SV0, _SV1, lambda v: _KAM0, lambda v: _KAM1), at_))
at_ = r.ObjectAttributes(); at_.LayerIndex = L17_; at_.Name = '南の妻の杉の壁（鴨居の上、大和張り）'
new_objs.append((_gplate(-0.03, 0.11, _SV0, _SV1, lambda v: _KAM1, lambda v: max(_KAM1 + 1.0, _BB(v) - 2.0)), at_))
for v0_, v1_ in ((_SV1, 11.8),):                                           # 東の袖壁（梁が柱の際で下がる所）
    at_ = r.ObjectAttributes(); at_.LayerIndex = L17_; at_.Name = '南の妻の東の袖壁'
    new_objs.append((_gplate(-0.03, 0.11, v0_, v1_, lambda v: 0.0, lambda v: _BB(v) - 2.0), at_))
def _lattice(v0_, v1_, zt_, name_):
    bars = [_gplate(-0.23, -0.185, v_, v_ + 0.03, lambda v: -150.0, lambda v: zt_, 2) for v_ in np.arange(v0_ + 0.045, v1_ - 0.03, 0.12)]
    bars.append(_gplate(-0.185, -0.155, v0_, v1_, lambda v: zt_ - 45.0, lambda v: zt_, 2))           # 上の押さえ（格子の裏、見えない側）
    at_ = r.ObjectAttributes(); at_.LayerIndex = L17G; at_.Name = name_
    new_objs.append((_join(bars), at_)); return len(bars) - 1
_nb = _lattice(_SV0, _SV1, _KAM1, '南の妻の縦格子（乳児室、ガラス戸の外に固定）')
_nb += _lattice(12.2, 13.5, _KAM1, '南の妻の縦格子（内縁側の端）')
# 受け取り土間の戸（v0.2〜1.4）も杉の格子戸に（ユーザー 10-26夜）：框（見付60）・ガラス・外の縦格子（見付30・見込45、120おき）。
# 上端は南の妻の鴨居の線（h2385〜2445）にそろえ、南の面に一本の水平線を通す。土間の床は −300、戸は外開き（plan01 の弧）。鴨居より上は杉の壁。
_DV0, _DV1 = 0.20, 1.40
_L66 = lidx('66_')
# 10-27（ユーザー）：開き戸の振れが待ち受けのベビーカー置き場（戸の前 0.75）に当たるので、格子の引き分け戸に。
# 2 枚とも南の妻の外側（外の格子の内、u −0.12〜−0.035）の上吊りのレールを引く：西の 1 枚（0.55）は外壁の角（v −0.35）まで、
# 東の 1 枚（0.65）は袖壁（v1.4〜1.75）と乳児室の格子の前へ。両方開けて 1.2、人だけなら片方。室内側では引かない（0・1歳の部屋の框・腰壁、はう子の手）。
# 3dm は閉めた位置。框（見付60）・ガラス・外の縦格子 30×45@120 は前と同じ。
def _leaf(a_, b_, nm_):
    fr_ = [_gplate(-0.075, -0.035, a_, a_ + 0.06, lambda v: -300.0, lambda v: _KAM0 - 10.0, 2), _gplate(-0.075, -0.035, b_ - 0.06, b_, lambda v: -300.0, lambda v: _KAM0 - 10.0, 2),
           _gplate(-0.075, -0.035, a_ + 0.06, b_ - 0.06, lambda v: -290.0, lambda v: -180.0, 2), _gplate(-0.075, -0.035, a_ + 0.06, b_ - 0.06, lambda v: _KAM0 - 70.0, lambda v: _KAM0 - 10.0, 2)]
    at_ = r.ObjectAttributes(); at_.LayerIndex = _L66; at_.Name = f'受け取り土間の格子の引き分け戸（{nm_}、框、杉）'; new_objs.append((_join(fr_), at_))
    at_ = r.ObjectAttributes(); at_.LayerIndex = L16S; at_.Name = f'受け取り土間の格子の引き分け戸のガラス（{nm_}）'
    new_objs.append((_gplate(-0.061, -0.049, a_ + 0.06, b_ - 0.06, lambda v: -180.0, lambda v: _KAM0 - 70.0, 2), at_))
    db_ = [_gplate(-0.12, -0.075, v_, v_ + 0.03, lambda v: -180.0, lambda v: _KAM0 - 70.0, 2) for v_ in np.arange(a_ + 0.105, b_ - 0.09, 0.12)]
    at_ = r.ObjectAttributes(); at_.LayerIndex = _L66; at_.Name = f'受け取り土間の格子の引き分け戸（{nm_}、縦格子 30×45、120おき）'; new_objs.append((_join(db_), at_))
_DM = _DV0 + 0.55
_leaf(_DV0, _DM, '西の1枚'); _leaf(_DM, _DV1, '東の1枚')
at_ = r.ObjectAttributes(); at_.LayerIndex = L18_; at_.Name = '受け取り土間の引き分け戸の上吊りのレール（外、v −0.35〜2.05）'
new_objs.append((_gplate(-0.13, -0.03, -0.35, _DV1 + 0.65, lambda v: _KAM0 - 10.0, lambda v: _KAM0 + 50.0, 2), at_))
at_ = r.ObjectAttributes(); at_.LayerIndex = L18_; at_.Name = '受け取り土間の戸の鴨居（南の妻の鴨居と一本）'
new_objs.append((_gplate(0.0, 0.11, _DV0, _DV1, lambda v: _KAM0, lambda v: _KAM1), at_))
at_ = r.ObjectAttributes(); at_.LayerIndex = L17_; at_.Name = '受け取り土間の戸の上の杉の壁'
new_objs.append((_gplate(-0.03, 0.11, _DV0, _DV1, lambda v: _KAM1, lambda v: _BB(v) - 2.0), at_))
log.append(f'本館：乳児室の南の妻（ガラスの引き戸 6 枚 16s・鴨居 h{_KAM0:.0f}〜{_KAM1:.0f}・上の杉の壁・外の縦格子 {_nb} 本 17g、内縁側の端にも格子）')

# 屋根の厚み（10-26夜）：元の屋根の面より上にあった本館の物を RT_TOP 上げる（越屋根の蓋・ルーバー・LED、外壁と越屋根の立ち上がりの上端）。
# 北の妻の壁の上端は屋根の立体の下面（梁の上端）まで下げる（屋根の中に食い込まない）。
_LUP = {lidx('17_'), lidx('50a'), lidx('50b'), lidx('50c')}
def _raise(g, ln):
    V = mesh_V(g); U = np.array([uv(x, y) for x, y in V[:, :2]])
    if ln.startswith('50') and U[:, 1].mean() < -0.8: return False              # 西館の越屋根は西館係
    rz = np.array([ROOF_Z(v) for v in U[:, 1]])
    up = V[:, 2] > rz + 10.0
    gab = ln.startswith('17_') and U[:, 0].min() > 57.1 and U[:, 1].max() > 5.0      # 北の妻の壁（u 57.19〜57.34、v −0.35〜12）
    if gab:
        hi = V[:, 2] > rz + RT_BOT
        if not hi.any(): return False
        V[hi, 2] = rz[hi] + RT_BOT
    else:
        if not up.any(): return False
        V[up, 2] += RT_TOP
    mesh_set(g, V); g.Normals.ComputeNormals(); return True
_nr = 0
for o in m.Objects:
    if o.Attributes.LayerIndex in _LUP and isinstance(o.Geometry, r.Mesh) and str(o.Attributes.Id) not in drop:
        _nr += _raise(o.Geometry, LN[o.Attributes.LayerIndex])
for mm, at in new_objs:
    if at.LayerIndex in _LUP: _nr += _raise(mm, LN[at.LayerIndex])
log.append(f'本館：屋根の上面（梁の上端から {RT_TOP - RT_BOT:.0f}、元の面の {RT_TOP:+.0f}）に合わせて {_nr} 物の上端を上げた・北の妻の上端を屋根の下面へ')
# ================================================================ 本館：壁・ガラス・建具を平らな板に（本館係、10-27夜）
# ユーザー（10-27夜）：曲線が見られるのは架構のみ。壁やガラスは必ず平面で、長方形（妻は三角形もある）の形を面に直角に押し出したもの。
# 前は弧（r = 205 m など）に沿って約 1 m ごとに折れ、端の面が放射の線（面と直角でない）、屋根の下の上端が厚みの向きに傾いていた。
# 壁・ガラス・建具の一つずつを、立面の形（面に投影した輪郭、穴あり）× 厚み に作り直す：
#   u の向きに走る物（西の外壁・縁側の杉の壁・ガラス戸・鴨居など）はスパンごとの弦の上で真っすぐ、厚みは弦に直角。
#   v の向きに走る物（妻・袖壁）は放射の線の上で真っすぐ、厚みはそれに直角。
# 立面の形は表と裏の面の輪郭の重なり（屋根の下で厚みの向きに傾いていた上端は低い方にそろう）。体積が 6% 以上変わる物は作り直さずに残して数える。
_SQ_PRE = ('17_', '17g', '16_', '16b', '16d', '16o', '16h', '16i', '16s', '18_', '19e', '48_', '66_')
def _sq_tris(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))]); T = []
    for i in range(len(g.Faces)):
        f = g.Faces[i]; T.append((f[0], f[1], f[2]))
        if f[2] != f[3]: T.append((f[0], f[2], f[3]))
    return V, np.array(T)
def _sq_vol(V, T): return abs(trimesh.Trimesh(V - V.mean(0), T, process=False).volume)
def _sq_prism(prof, P_of, off):
    """prof：立面の形（(a, z) の多角形、mm）、P_of(a, z) → 表の面の点（x, y, z）、off：厚みのベクトル（裏の面へ）"""
    ms = []
    for p in ([prof] if prof.geom_type == 'Polygon' else list(getattr(prof, 'geoms', []))):
        if p.geom_type != 'Polygon' or p.area < 50.0: continue
        p = _orient(p.simplify(0.3), 1.0)
        rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
        V2 = np.vstack(rings); n = len(V2); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri_ = _ec.triangulate_float64(V2, ends).reshape(-1, 3)
        V = np.array([P_of(a, z) for a, z in V2])
        V = np.vstack([V, np.array([off(a, z) for a, z in V2]) if callable(off) else V + off])
        F = [(a, c, b) for a, b, c in tri_] + [(a + n, b + n, c + n) for a, b, c in tri_]
        st = 0
        for e in ends:
            for i in range(st, int(e)):
                j = i + 1 if i + 1 < e else st; F.append((i, j, j + n)); F.append((i, j + n, i + n))
            st = int(e)
        F = np.array(F)
        if np.einsum('ij,ij->i', V[F[:, 0]], np.cross(V[F[:, 1]], V[F[:, 2]])).sum() < 0: F = F[:, ::-1]
        mm = r.Mesh()
        for x_, y_, z_ in V: mm.Vertices.Add(float(x_), float(y_), float(z_))
        for a, b, c in F: mm.Faces.AddFace(int(a), int(b), int(c))
        mm.Normals.ComputeNormals(); mm.Compact(); ms.append(mm)
    return ms
def _square(g):
    V, T = _sq_tris(g)
    if len(T) < 4: return None
    U = np.array([uv(x, y) for x, y in V[:, :2]]); u0, v0 = U.min(0); u1, v1 = U.max(0)
    if u1 < -0.6 or u0 > 57.9 or v0 < -0.6 or v1 > 15.2: return None        # 本館の外（西館・外構）は触らない
    du, dv = u1 - u0, v1 - v0
    A, B, C = V[T[:, 0]], V[T[:, 1]], V[T[:, 2]]
    N = np.cross(B - A, C - A); ar = np.linalg.norm(N, axis=1); ok = ar > 1e-6
    N[ok] /= ar[ok, None]; cen = (A + B + C) / 3.0
    along_u = dv <= du
    # 面の向き：u に走る物は v の向き（放射）、v に走る物は u の向き（接線）
    rad = np.array([[x - CX, y - CY] for x, y in cen[:, :2]]); rad /= np.linalg.norm(rad, axis=1)[:, None]
    tan = np.stack([-rad[:, 1], rad[:, 0]], 1)
    ax = rad if along_u else tan
    d = np.einsum('ij,ij->i', N[:, :2], ax)
    profs = []
    _bw = 0.6 if _SQ_LN[0].startswith('17_') else 0.05      # 10-28：外壁は片のあいだの 1 mm 未満のすき間を閉じて一つの立面の形に
    for sgn in (1, -1):
        sel = ok & (np.abs(N[:, 2]) < 0.05) & (sgn * d > 0.95)
        if not sel.any(): continue
        ps = []
        for t_ in np.where(sel)[0]:
            tri = T[t_]; q = [((U[i, 0] if along_u else U[i, 1]) * 1000.0, V[i, 2]) for i in tri]
            pg = Polygon(q)
            if pg.area > 1e-3: ps.append(pg.buffer(_bw, join_style=2))
        if ps: profs.append(unary_union(ps).buffer(-_bw, join_style=2))
    if not profs: return None
    if len(profs) == 1: prof = profs[0]
    else:
        # ふつうは表と裏の重なり（屋根の下で厚みの向きに傾いた上端は低い方に）。大きく違う（越屋根の立ち上がりを兼ねる西の外壁の上端など）ときは高い方に
        prof = profs[0].intersection(profs[1])
        if prof.area < 0.97 * max(profs[0].area, profs[1].area): prof = profs[0].union(profs[1])
    if prof.is_empty or prof.area < 100.0: return None
    out_ = []
    if along_u:
        t0, t1 = _SQ_T.get(_sq_key(g, U), (v0, v1)) if _SQ_LN[0].startswith('17_') else (v0, v1)
        for k_ in range(-2, 21):
            part = prof.intersection(Polygon([(3000.0 * k_, -1e4), (3000.0 * (k_ + 1), -1e4), (3000.0 * (k_ + 1), 1e5), (3000.0 * k_, 1e5)]))
            if part.is_empty or part.area < 50.0: continue
            if part.bounds[2] - part.bounds[0] < 5.0: continue            # 10-28：架構の線をわずかに越えた片（幅 1 mm 未満、弧の点が線の外）は捨てる（Rhino で表示できない面になっていた）
            key = ('s', min(18, max(0, k_))); A_, c_, h_, n_ = _plane(key)
            P_of = lambda a, z, key=key: np.array([*xyk(key, a / 1000.0, t0), z])
            # 架構の線で切った所だけ、裏の面の点を同じスパンの弦（v = t1）の上に（留め：となりのスパンの片とちょうど合う）。ほかの端は面に直角
            out_ += _sq_prism(part, P_of, lambda a, z, key=key, h_=h_: np.array([*xyk(key, a / 1000.0, t1), z]) if abs(a / 3000.0 - round(a / 3000.0)) < 1e-6
                              else np.array([*(xyk(key, a / 1000.0, t0) + h_ * (t1 - t0) * 1000.0), z]))
    else:
        t0, t1 = u0, u1; vm = 0.5 * (v0 + v1)
        b_ = xy(t0, vm); tv = xy(t0 + 0.001, vm) - b_; tv /= np.linalg.norm(tv)
        rv = xy(t0, vm + 0.001) - b_; rv /= np.linalg.norm(rv)
        P_of = lambda a, z: np.array([*(b_ + (a / 1000.0 - vm) * 1000.0 * rv), z])
        out_ += _sq_prism(prof, P_of, np.array([*(tv * (t1 - t0) * 1000.0 * (RW - vm * 1000.0) / RW), 0.0]))
    if not out_: return None
    v_old = _sq_vol(V, T); v_new = sum(_sq_vol(*_sq_tris(q)) for q in out_)
    if v_old <= 0 or abs(v_new - v_old) / v_old > 0.06: return 'skip'
    return out_
# 10-28（監修の項 20261027-2346 の 17：外壁は壁ごとに一つの立体）：同じ壁の線の片（開口の上下・横の片）は厚みの線をそろえる。前は片ごとの
# 外形の幅で v0〜v1 を決めていて、開口のある片は 5 mm ほど細く、clip_parts の足し合わせで一つにならなかった（17 が 119 の体）。
# 同じレイヤー・同じ壁の線（v の中ほどを 0.05 で丸める）の、u の向きに走る片の v の幅の外側（min v0〜max v1）に合わせる。
def _sq_key(g, U):
    return (round(float(np.median(U[:, 1])) * 20.0) / 20.0,)
_SQ_T = {}; _SQ_LN = ['']
def _sq_scan(g, li):
    if not isinstance(g, r.Mesh) or not m.Layers[li].Name.startswith('17_'): return
    V, T = _sq_tris(g)
    if len(T) < 4: return
    U = np.array([uv(x, y) for x, y in V[:, :2]]); u0, v0 = U.min(0); u1, v1 = U.max(0)
    if v1 - v0 > u1 - u0 or v1 - v0 > 0.4: return
    _SQ_T.setdefault(_sq_key(g, U), []).append((v0, v1))
for o in m.Objects:
    if str(o.Attributes.Id) not in drop: _sq_scan(o.Geometry, o.Attributes.LayerIndex)
for mm, at in new_objs: _sq_scan(mm, at.LayerIndex)
def _sq_line(L):
    """壁の線の厚みの範囲：片の中ほどの真ん中の値 ± いちばん薄い片の厚みの半分（弧の片の弦の向きのずれで外形の幅は厚みより数 mm 広い）"""
    mid = float(np.median([(a + b) / 2 for a, b in L])); t = min(b - a for a, b in L)
    return (mid - t / 2, mid + t / 2)
_SQ_T = {k: _sq_line(L) for k, L in _SQ_T.items()}
_SQ_T = {k: t for k, t in _SQ_T.items() if t[1] - t[0] < 0.4}
_sq_n = _sq_k = 0; _sq_skip = []
_sq_new = []
# 10-28：外壁（17）の u の向きに走る片は、同じ壁の線ごとに一つの網にまとめてから平らな板にする（壁ごとに一つの立面の形＝輪郭−開口、
# スパンごとに真っすぐ、架構の線で留め）。前は片ごとに作り直していて、越屋根の立ち上がり（約 1 m ごとの片）などが 0.3 mm ずれて一つにならなかった。
_grp = {}
def _sq_group_key(g, li):
    if not isinstance(g, r.Mesh) or not m.Layers[li].Name.startswith('17_'): return None
    V, T = _sq_tris(g)
    if len(T) < 4: return None
    U = np.array([uv(x, y) for x, y in V[:, :2]]); u0, v0 = U.min(0); u1, v1 = U.max(0)
    if u1 < -0.6 or u0 > 57.9 or v0 < -0.6 or v1 > 15.2 or v1 - v0 > u1 - u0 or v1 - v0 > 0.4: return None
    return (li,) + _sq_key(g, U)
for o in m.Objects:
    if str(o.Attributes.Id) in drop: continue
    k_ = _sq_group_key(o.Geometry, o.Attributes.LayerIndex)
    if k_ is not None: _grp.setdefault(k_, []).append(('o', o))
for i_, (mm, at) in enumerate(new_objs):
    k_ = _sq_group_key(mm, at.LayerIndex)
    if k_ is not None: _grp.setdefault(k_, []).append(('n', i_))
_gdone = set(); _ngrp = 0; _gskip = []
for k_, L_ in _grp.items():
    if len(L_) < 2: continue
    big = r.Mesh(); at0_ = None
    for kind, x in L_:
        g_ = x.Geometry if kind == 'o' else new_objs[x][0]
        big.Append(g_)
        if at0_ is None: at0_ = x.Attributes if kind == 'o' else new_objs[x][1]
    _SQ_LN[0] = m.Layers[k_[0]].Name; res_ = _square(big)
    if res_ is None or res_ == 'skip': _gskip.append(f'v{k_[1]:.2f}:{len(L_)}{"×" if res_ is None else "体積"}'); continue
    for kind, x in L_:
        if kind == 'o': drop.add(str(x.Attributes.Id))
        else: _gdone.add(x)
    _sq_new += [(q, at0_) for q in res_]; _sq_n += len(L_); _sq_k += len(res_); _ngrp += 1
if _gdone: new_objs[:] = [x for i_, x in enumerate(new_objs) if i_ not in _gdone]
log.append(f'本館：外壁の壁の線 {_ngrp} 本を一つずつの立面の形にまとめた（まとめなかった線 {_gskip}）')
for o in m.Objects:
    if str(o.Attributes.Id) in drop or not isinstance(o.Geometry, r.Mesh) or not LN[o.Attributes.LayerIndex].startswith(_SQ_PRE): continue
    _SQ_LN[0] = LN[o.Attributes.LayerIndex]; res_ = _square(o.Geometry)
    if res_ is None: continue
    if res_ == 'skip': _sq_skip.append(LN[o.Attributes.LayerIndex][:3]); continue
    drop.add(str(o.Attributes.Id)); _sq_new += [(q, o.Attributes) for q in res_]; _sq_n += 1; _sq_k += len(res_)
_keep = []
for mm, at in new_objs:
    if isinstance(mm, r.Mesh) and m.Layers[at.LayerIndex].Name.startswith(_SQ_PRE):
        _SQ_LN[0] = m.Layers[at.LayerIndex].Name; res_ = _square(mm)
        if res_ is not None and res_ != 'skip':
            _sq_new += [(q, at) for q in res_]; _sq_n += 1; _sq_k += len(res_); continue
        if res_ == "skip": _sq_skip.append(m.Layers[at.LayerIndex].Name[:3])
    _keep.append((mm, at))
def _sq_thin(q):
    V_ = np.array([[q.Vertices[i].X, q.Vertices[i].Y] for i in range(len(q.Vertices))]); U_ = np.array([uv(x, y) for x, y in V_])
    return min(np.ptp(U_[:, 0]), np.ptp(U_[:, 1])) < 0.005          # 10-28：架構の線をわずかに越えた幅 5 mm 未満の片（Rhino で表示できない面）は捨てる
_sq_new = [(q, at) for q, at in _sq_new if not _sq_thin(q)]
new_objs[:] = _keep + _sq_new
from collections import Counter as _Ct
log.append(f'本館：壁・ガラス・建具 {_sq_n} 物を平らな板（立面の形×厚み、スパンごとに真っすぐ）に作り直した（{_sq_k} 片）。作り直さなかった物 {len(_sq_skip)}（体積の差 6% 以上）：{dict(_Ct(_sq_skip))}')
out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for o in m.Objects:
    if str(o.Attributes.Id) in drop or str(o.Attributes.Id) in col_drop or str(o.Attributes.Id) in beam_drop: continue
    out.Objects.Add(EXT.get(str(o.Attributes.Id), o.Geometry), o.Attributes)      # 22a〜d は動かした押し出し（EXT）
for mm, at in new_objs + col_new + beam_new: out.Objects.AddMesh(mm, at)
for g_, at_ in _XNEW:
    if g_ is not None: out.Objects.Add(g_, at_)                                 # 構造の直し（10-27）の柱・横材（押し出し）
K = Kit(out)
ZF2 = 3250.0
_cutE = R(19.0, 35.0, 2.0, EDGE2, 0.1)                        # 2 階の床の東の縁より東（吹き抜け）
def _uni(k): return unary_union([f for f, a, z0, z1 in _F2.get(k, [])]) if _F2.get(k) else None
def _first(k): return _F2[k][0] if _F2.get(k) else None
_toilet = R(25.0, 27.0, -3.9, -5.3, 0.05)                          # 便所（湯沸と分けた、吹き抜けの縁から奥へ、10-25 ユーザー）
_yuwak = unary_union([R(24.0, 27.0, EDGE2, -3.9, 0.05), R(24.0, 25.0, -3.9, -5.0, 0.05)])   # 湯沸（吹き抜けの縁の開いた窪み）と食器棚の窪み
_corr = R(27.75, 29.69, -5.0, -7.0, 0.05)                          # 会議室と休憩室への通路（更衣室の手前）
for k, geom_fn in (('23_', lambda g: g.difference(_cutE)),
                   ('41_', lambda g: unary_union([g.difference(_cutE).difference(_toilet), _yuwak, _corr, R(STAIR_U0, STAIR_U0 + STAIR_FOOT, -2.99, -5.0, 0.05)])),   # 階段の着き口（10-27）
                   ('42_', lambda g: _toilet),
                   ('44_', lambda g: unary_union([g, _uni('45_') or g]).difference(_cutE).difference(R(24.0, 27.75, EDGE2, -5.0, 0.05)).difference(_toilet)),
                   ('43b', lambda g: g.difference(_corr).difference(R(27.7, 29.75, -2.0, -7.0, 0.05)))):
    if not _F2.get(k): continue
    g0 = _uni(k); f0, a0, z0, z1 = _first(k)
    gn = geom_fn(g0).buffer(1).buffer(-1)
    if k == '23_':
        # 10-28（監修の項 2346）：2 階の床は一つの平面形（片を足し、吹き抜けを除き、外壁の内面で切る）を 2FL−80 から 2FL まで押し出した一つの立体
        # （前は片ごとの面を後で厚み付けし、縁の点を外壁の内面へ寄せていたので、Rhino 版で 117 面・曲面の片になった）
        _f23 = unary_union([f_ for f_, a_, za, zb in _F2[k]]).buffer(1).buffer(-1).difference(_cutE).intersection(WNi)
        # 10-28（監修の項 20261028-0843）：平面形の点を減らす（片の継ぎ目・弧の細かい点で 123 面になっていた）。直線は直線に、弧は 2 mm のずれまで少ない点に
        _f23 = _f23.buffer(0).simplify(2.0, preserve_topology=True)
        if _STUD_FP: _f23 = _f23.difference(unary_union(_STUD_FP)).buffer(0)          # 10-30：鼻母屋の受けの柱の所を欠く
        K.prism(_f23, ZF2 - 80.0, ZF2, _F2[k][0][1].LayerIndex)
        continue
    K.flat(gn, z0, a0.LayerIndex)
for _i, _l in enumerate(out.Layers):
    if _l.Name.startswith('42_2F_'): _l.Name = '42_2F_便所'
log.append('西館：2 階の東の縁を v −2.5 へ（東の帯の吹き抜け 1.6）、2 階の部屋を割り直した（便所・湯沸を分ける、通路から会議室と休憩室へ、休憩室とぐったり休憩を一つに、更衣室は通路の奥）')
# 階段の下の倉庫（10-25）：床の板 36b、階段の床（36）からその分を除く、戸（遊戯室の側の片引き、h1.75）
_L36B = out.Layers.Add(r.Layer()); out.Layers[_L36B].Name = '36b_1F_倉庫（階段の下）'; out.Layers[_L36B].Color = (217, 211, 236, 255)
_stg = R(STAIR_STG[0], STAIR_STG[1], STAIR_STG[2], STAIR_STG[3], 0.05)
K.flat(_stg, 10.0, _L36B)
for _f, _li in _F36: K.flat(_f.difference(_stg.buffer(1)), 10.0, _li)
_L19C_ = [i for i, l in enumerate(out.Layers) if l.Name.startswith('19c_')]
if _L19C_: K.prism(R(STAIR_DOOR[0] - 0.05, STAIR_DOOR[1] + 0.05, -5.12, -5.09, 0.05), 10.0, STAIR_DOOR_H, _L19C_[0])
log.append('西館：階段の下の倉庫 %.1f m²（36b、戸は階段の箱の西の面 u%.2f〜%.2f）' % (_stg.area / 1e6, *STAIR_DOOR))
K.prism(R(21.16, 32.95, -2.56, -2.50, 0.1), ZF2, ZF2 + 1100.0, L38)       # 2 階の東の縁（東の帯への吹き抜け、10-25：1.0 → 1.6）
K.prism(R(32.97, 33.03, -2.93, -2.56, 0.02), ZF2, ZF2 + 1100.0, L38)      # 2 階の北の口（遊戯室の吹き抜け、10-27：箱の東の外まで）
# 階段の柵と手すり（10-28、監修の項 20261028-0015 の 2。決定事項_遊戯室の柵の決まり：縦格子・すき間 90・横桟なし・h1,100、ここでは厚さ 30 の面で表す）
# 段の位置は _stair_tris と同じ（蹴上 3250/18、踏面 0.2625、東の一折れ u30.9→33 を上る、西の一折れ u33→30.9 を上る）。
_RS, _G = 3250.0 / 18, 0.2625
_SU0, _SUL = STAIR_U0 + STAIR_FOOT, STAIR_U0 + STAIR_FOOT + 8 * _G
_VW1, _VE0 = round(stair_v25(-3.45), 3), round(stair_v25(-3.35), 3)            # 2 本の階段のあいだのすき間（西の一折れの東の縁・東の一折れの西の縁）
def _z_west(x_, y_):                                                            # 西の一折れの段鼻の線（u30.9 で 2FL、u33 で踊り場）
    u_ = min(max(uv(x_, y_)[0], _SU0), _SUL); return 9 * _RS + (_SUL - u_) / (_SUL - _SU0) * 9 * _RS
_vm = (_VW1 + _VE0) / 2
# 1. 2 本の階段のあいだ：すき間の真ん中に柵（床から、高いほうの西の一折れの段鼻の 1,100 上まで。下は倉庫との仕切りを兼ねる）
K.prism(R(_SU0, _SUL, _vm - 0.015, _vm + 0.015, 0.05), 0.0, lambda x_, y_: _z_west(x_, y_) + 1100.0, L38)
# 2. 2 階の着き口の北の縁（u30.9）の東の半分：下は東の一折れの登り口（落ちると 3.25 m）
K.prism(R(_SU0 - 0.03, _SU0, _vm - 0.015, -3.05, 0.02), ZF2, ZF2 + 1100.0, L38)
# 3. 手すり（令25条）：両方の一折れの壁の側に φ35、段鼻から 800（箱の壁の内面から 0.06 離して、受け金物で壁に）
def _rod(p0, p1, rad, li):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); d_ = p1 - p0; L_ = float(np.linalg.norm(d_))
    pl_ = r.Plane(r.Point3d(*map(float, p0)), r.Vector3d(*map(float, d_ / L_)))
    c_ = r.Circle(float(rad)).ToNurbsCurve(); c_.Transform(r.Transform.PlaneToPlane(r.Plane.WorldXY(), pl_))
    best = None
    for ex in (r.Extrusion.Create(c_, L_, True), r.Extrusion.Create(c_, -L_, True)):
        if ex is None: continue
        bb = ex.GetBoundingBox(); mid = np.array([(bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2, (bb.Min.Z + bb.Max.Z) / 2])
        dm = np.linalg.norm(mid - (p0 + p1) / 2)
        if best is None or dm < best[0]: best = (dm, ex)
    if best is not None:
        at_ = r.ObjectAttributes(); at_.LayerIndex = li; at_.Name = '階段の手すり φ35（段鼻から 800）'; out.Objects.AddExtrusion(best[1], at_)
_vhE, _vhW = -3.05 - 0.06, -4.94 + 0.06
_rod([*np.ravel(xy(_SU0, _vhE)), 800.0], [*np.ravel(xy(_SUL, _vhE)), 9 * _RS + 800.0], 17.5, L38)          # 東の一折れ（東の壁）
_rod([*np.ravel(xy(_SUL, _vhW)), 9 * _RS + 800.0], [*np.ravel(xy(_SU0, _vhW)), 18 * _RS + 800.0], 17.5, L38)   # 西の一折れ（西の壁）
log.append(f'西館：階段の柵（2 本のあいだ v{_vm:.3f}、高いほうの段鼻 +1,100）・2 階の着き口の北の縁の柵（u{_SU0}、h1,100）・手すり 2 本（φ35、h800）')
for _f, _li, _z in _F31: K.flat(_f.difference(_STX), _z, _li)
# 東の帯の吹き抜け（スパン 8〜11、u 21〜33）に天井扇（10-25、ユーザー：設置は可能？ → 吹き抜けを 1.6 にして入る）。
# 遊戯室の天井扇（スパン 12〜17）と同じ φ1.1・h6.0、吹き抜けの真ん中（v −1.8、西館の東の壁の内面から 0.75）。
_LFAN = out.Layers.Add(r.Layer()); out.Layers[_LFAN].Name = '58b_西館_天井扇（東の帯の吹き抜け・部屋）'; out.Layers[_LFAN].Color = (90, 122, 154, 255)
from shapely.geometry import Point as _Pt
for _uf in (22.5, 25.5, 28.5, 31.5):
    _c = xy(_uf, -1.8)
    K.prism(_Pt(*_c).buffer(550, resolution=24), 5980.0, 6000.0, _LFAN)          # 羽根の回る範囲
    K.prism(_Pt(*_c).buffer(110, resolution=16), 5960.0, 6080.0, _LFAN)          # モーター
    K.prism(_Pt(*_c).buffer(15, resolution=8), 6080.0, float(_RWf['roof_f'](*np.ravel(_c))) - 150.0, _LFAN)   # 吊り棒（10-30：棟のガラスの帯をまたぐ鋼の平板の下面へ。前は越屋根の立ち上がりの受け）
log.append('西館：東の帯の吹き抜け（スパン 8〜11）に天井扇 4 台（φ1.1、h6.0、58b）')
# 部屋の天井扇（10-28、ユーザー 23:41：シーリングファンが一部にしか無い。無理・無駄でない限り全スパンに）。天井の低い部屋は羽根 φ0.9：
# いちばん下（モーター）を床から 2.4 以上、羽根の回る範囲の外 0.3 までの真上（屋根の下面の合板 20r・梁・母屋・2 階の床の裏）と羽根の上のあき
# 0.3 以上（作り直した 3dm で測った、下の「あき」）。付けない所：キッチン（フードの捕集を乱す・盛り付けと下処理の上に風を当てない、空調は別の
# 区画）、洞（クスノキの枝が 2 階の床の裏まで）、2 階のホール（通り抜け、吹き抜けの扇の脇）、便所・更衣・前室・通路・階段・倉庫（小さい・通り抜け）。
_ZF2 = 3260.0
for _uf, _vf, _zfl, _zc, _nm in ((22.5, -5.0, _ZF2, 6743.0, '2 階の休憩室（スパン 8、あき 0.85）'),
                                  (25.6, -6.3, _ZF2, 6394.0, '2 階の休憩室（スパン 9、あき 0.51）'),
                                  (28.6, -7.0, 0.0, 3170.0, '1 階の遊戯室の入り口（スパン 10、10-29 夜まではれのま）'),
                                  (31.4, -6.3, _ZF2, 6468.0, '2 階の会議室（スパン 11、あき 0.59）')):
    _c = xy(_uf, _vf); _zb = _zfl + 2420.0                                       # 羽根の下端（モーターの下端 = 床 + 2.40）
    K.prism(_Pt(*_c).buffer(450, resolution=24), _zb, _zb + 20.0, _LFAN)         # 羽根の回る範囲 φ0.9
    K.prism(_Pt(*_c).buffer(110, resolution=16), _zb - 20.0, _zb + 100.0, _LFAN)  # モーター
    K.prism(_Pt(*_c).buffer(15, resolution=8), _zb + 100.0, _zc - 5.0, _LFAN)   # 吊り棒（天井まで）
log.append('西館：部屋に天井扇 4 台（φ0.9、床から 2.4、休憩室 2・はれのま 1・会議室 1、58b）')
_L31 = [i for i, l in enumerate(out.Layers) if l.Name.startswith('31_')]
if _L31: K.flat(R(30.0, 33.0, -2.20, -2.93, 0.05), 10.0, _L31[0])          # 遊戯室の南の口の通路：階段の箱を細くした分の床の板（面積に入れる）
_L37 = [i for i, l in enumerate(out.Layers) if l.Name.startswith('37_')]
_L39 = [i for i, l in enumerate(out.Layers) if l.Name.startswith('39_')]
_L40 = [i for i, l in enumerate(out.Layers) if l.Name.startswith('40_')]
if _L37 and _L39 and _L40:
    # 2 階の内装（10-25午後、ユーザー：お茶は休憩室と会議室のそれぞれの中に、便所・会議室・ロッカー・休憩室のソファなど）
    FU, WA, CU = _L37[0], _L39[0], _L40[0]
    def _bx(u0, u1, v0, v1, h0, h1, li): K.prism(R(u0, u1, v0, v1, 0.05), ZF2 + h0, ZF2 + h1, li)
    # 吹き抜けの縁の窪み：見下ろしの立ち机（h1.0、1階の東の帯と越屋根の光を見る）と共用の本棚
    _bx(24.1, 26.9, -2.62, -3.12, 0, 1000, FU)
    _bx(24.1, 24.94, -3.9, -4.94, 0, 2100, FU)
    # 便所（u25〜27・v−3.9〜−5.3）：便器（西の壁を背に）と手洗い
    _bx(25.08, 25.75, -4.35, -4.75, 0, 420, WA); _bx(25.08, 25.28, -4.32, -4.78, 420, 800, WA)
    _bx(26.25, 26.9, -5.0, -5.25, 750, 850, WA)
    # 休憩室：東の帯（吹き抜けに面する）にお茶の台所（流し・湯沸かし・冷蔵庫）と食卓6人、真ん中にソファ、西の天井の低い側に小上がり（横になれる）
    _bx(23.4, 23.94, -2.9, -4.4, 0, 850, WA)                      # 流し台（便所と背中合わせで水まわりをまとめる）
    _bx(23.4, 23.94, -4.4, -4.94, 0, 1800, FU)                    # 冷蔵庫・食器棚
    _bx(21.9, 22.7, -3.0, -4.6, 0, 720, FU)                       # 食卓 0.8×1.6
    for _vc in (-3.3, -3.8, -4.3):
        _bx(21.45, 21.85, _vc - 0.2, _vc + 0.2, 0, 450, FU); _bx(22.75, 23.15, _vc - 0.2, _vc + 0.2, 0, 450, FU)
    _bx(22.2, 25.2, -6.0, -6.85, 0, 420, CU); _bx(22.2, 25.2, -6.0, -6.2, 420, 800, CU)     # ソファ（L字）
    _bx(22.2, 23.05, -6.85, -8.6, 0, 420, CU); _bx(22.2, 22.4, -6.85, -8.6, 420, 800, CU)
    _bx(23.5, 24.9, -7.1, -8.0, 0, 380, FU)                       # 低いテーブル
    _bx(26.2, 27.4, -7.2, -8.4, 0, 420, CU)                       # 一人がけ
    _bx(22.6, 27.3, -9.6, -11.8, 0, 300, CU)                      # 小上がり（畳、約10m²、天井 約2.0〜1.4）
    # 避難はしごの収納箱（10-30 先生のエスキス：2 階の二方向避難）：10-31 から南の妻の避難の戸（u21、v−9.05〜−9.90、2FL+0.05〜+1.30、外開き・吊元は西、
    # f7fc471）の東の脇へ。戸の前は空ける（戸の開きと横桟に当たらない）。吊り下げ式（戸の外の下屋の屋根へ）
    _bx(21.16, 21.46, -8.4, -8.9, 0, 600, FU)
    out.Objects[len(out.Objects) - 1].Attributes.Name = '避難はしごの収納箱（吊り下げ式、避難の戸の東の脇、10-30 先生のエスキス・10-31 戸へ）'
    # 会議室：会議の机（1.2×3.6、10人）、入口の脇にお茶の台、西の端に棚
    _bx(30.7, 31.9, -7.2, -10.8, 0, 720, FU)
    for _vc in (-7.6, -8.4, -9.2, -10.0, -10.4):
        _bx(30.15, 30.55, _vc - 0.2, _vc + 0.2, 0, 450, FU); _bx(32.05, 32.45, _vc - 0.2, _vc + 0.2, 0, 450, FU)
    _bx(30.95, 31.65, -6.55, -6.95, 0, 450, FU); _bx(30.95, 31.65, -11.05, -11.45, 0, 450, FU)
    _bx(29.85, 31.6, -5.1, -5.7, 0, 850, WA)                      # お茶の台（流し・湯沸かし）
    _bx(29.85, 32.9, -12.2, -12.6, 0, 350, FU)                    # 低い棚（天井の低い西の端、10-26：西の横一文字の窓 2FL+0.4 の下に収める）
    # 更衣・ロッカー（u27.75〜29.69・v−7.0〜−13.3）：ロッカー2段（幅0.4）を両側に、あいだ0.9、奥にベンチ
    _bx(29.15, 29.63, -7.2, -11.6, 0, 1800, FU)                   # 11列×2段＝22
    _bx(27.81, 28.25, -7.6, -10.4, 0, 1800, FU)                   # 7列×2段＝14
    _bx(27.9, 29.5, -11.85, -12.25, 0, 420, FU)                   # ベンチ
    log.append('西館：2 階の内装（便所の器具、休憩室のお茶の台所・食卓・ソファ・小上がり、会議室の机と椅子とお茶の台、ロッカー36、見下ろしの立ち机）')
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
# ================================================================ 西館：階段の箱の壁（西館係、10-28、監修の項 20261028-0843）
# 前は元の面を面ごとの板（_plates）にして屋根の中まで立て、削る段で屋根の層（20・20r・20v）・梁に欠かれて、間仕切り（24）が Rhino版で
# 1.8 万面のメッシュになっていた。今：壁ごとに平面の輪郭（厚さ 120、芯は前と同じ）を床から平らな上端の面まで押し出し、開口（1 階の登り口・
# 2 階の着き口・階段の下の倉庫の戸）を引いた一つの立体（manifold3d、原点を近くへ移す）。上端は間仕切りの構法（決定事項）のとおり：
# 架構の線（u30）に立つ南の壁は 2 枚の梁の下端（A）、ほかは屋根の下面（母屋・合板・断熱の下、梁は除く＝梁は削る段で欠く）（B）。
# どちらも、壁の厚さの中の 5 本の線に沿って 50 ごとに真上の面を測り、その下に収まるいちばん高い平らな面（壁の上端が一つの平らな面になる）。
if _BOX_ATTR is not None:
    from solids import geom_vf as _gvf
    from scipy.optimize import linprog as _lp
    _TR, _TB = [], []
    for o_ in out.Objects:
        ln_ = out.Layers[o_.Attributes.LayerIndex].Name
        if not (ln_.startswith(('20', '22b', '22d', '22t'))): continue
        vf_ = _gvf(o_.Geometry)
        if vf_ is None or not len(vf_[1]): continue
        bb_ = o_.Geometry.GetBoundingBox(); cu_ = uv((bb_.Min.X + bb_.Max.X) / 2, (bb_.Min.Y + bb_.Max.Y) / 2)
        if not (27.0 < cu_[0] < 37.0 or (bb_.Max.X - bb_.Min.X) > 6000 or (bb_.Max.Y - bb_.Min.Y) > 6000): continue
        (_TB if ln_.startswith('22b') else _TR).append(np.asarray(vf_[0], float)[np.asarray(vf_[1])])
    _RI = trimesh.ray.ray_triangle.RayMeshIntersector(trimesh.Trimesh(**trimesh.triangles.to_kwargs(np.vstack(_TR))))
    _BI = trimesh.ray.ray_triangle.RayMeshIntersector(trimesh.Trimesh(**trimesh.triangles.to_kwargs(np.vstack(_TB + _TR))))
    def _up(I, P, z0=5000.0):
        loc, ir, _ = I.intersects_location(np.c_[P, np.full(len(P), z0)], np.tile([0, 0, 1.0], (len(P), 1)), multiple_hits=True)
        h = np.full(len(P), np.inf)
        for q_, k_ in zip(loc, ir): h[k_] = min(h[k_], q_[2])
        return h
    _BW = 0.06                                              # 壁の厚さの半分（m）
    # (名前, 輪郭, 線に沿う点 (u, v) の関数, 線の長さの範囲, A か)
    _walls = [('南（u30、架構の線）', R(30.0 - _BW, 30.0 + _BW, -5.0 - _BW, -2.99 + _BW, 0.02), lambda s, w: (30.0 + w, s), (-5.0, -2.99), True),
              ('北（u33.9）', R(33.9 - _BW, 33.9 + _BW, -5.0 - _BW, -2.99 + _BW, 0.02), lambda s, w: (33.9 + w, s), (-5.0, -2.99), False),
              ('東（v−2.99）', R(30.0 - _BW, 33.9 + _BW, -2.99 - _BW, -2.99 + _BW, 0.78), lambda s, w: (s, -2.99 + w), (30.0, 33.9), False),
              ('西（v−5.0）', R(30.0 - _BW, 33.9 + _BW, -5.0 - _BW, -5.0 + _BW, 0.78), lambda s, w: (s, -5.0 + w), (30.0, 33.9), False)]
    _BO = np.ravel(xy(32.0, -4.0))
    def _prismM(poly, zf):
        poly = _orient0(poly.simplify(0.2), 1.0)
        rings = [np.asarray(poly.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in poly.interiors]
        V2 = np.vstack(rings) - _BO; k = len(V2); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri = _ec0.triangulate_float64(V2, ends).reshape(-1, 3)
        zt = np.array([zf(x + _BO[0], y + _BO[1]) for x, y in V2])
        z0 = np.full(k, -0.0) if not callable(zf) else None
        V = np.vstack([np.c_[V2, np.zeros(k)], np.c_[V2, zt]]); F = [tri[:, [0, 2, 1]], tri + k]; st = 0
        for e in ends:
            i = np.arange(st, e); j = np.r_[i[1:], st]; F += [np.c_[i, j, j + k], np.c_[i, j + k, i + k]]; st = e
        M_ = _mf.Manifold(_mf.Mesh(vert_properties=V.astype(np.float32), tri_verts=np.vstack(F).astype(np.uint32)))
        if M_.status() != _mf.Error.NoError or M_.is_empty() or M_.volume() < 0: raise RuntimeError('階段の箱の壁が閉じない')
        return M_
    def _boxM(poly, z0, z1):
        return _prismM(poly, lambda x, y: z1).translate([0, 0, 0]) if z0 == 0 else \
            _prismM(poly, lambda x, y: z1 - z0).translate([0, 0, z0])
    _box_log = []; _Ms = []
    for nm_, fp_, at_, (s0_, s1_), isA in _walls:
        S_ = np.linspace(s0_ - _BW, s1_ + _BW, max(3, int((s1_ - s0_ + 2 * _BW) / 0.05) + 1))
        if isA:   # 2 枚の梁の下端：両脇（±0.14）の梁・屋根のうち高いほう
            P_ = [np.ravel(xy(*at_(s, w))) for s in S_ for w in (0.0,)]
            hl = _up(_BI, np.array([np.ravel(xy(*at_(s, -0.14))) for s in S_])); hr = _up(_BI, np.array([np.ravel(xy(*at_(s, 0.14))) for s in S_]))
            P_ = np.array([np.ravel(xy(*at_(s, w))) for w in (-_BW + 0.005, _BW - 0.005) for s in S_]); H_ = np.r_[np.maximum(hl, hr), np.maximum(hl, hr)]
        else:
            P_ = np.array([np.ravel(xy(*at_(s, w))) for w in (-_BW + 0.002, -0.03, 0.0, 0.03, _BW - 0.002) for s in S_]); H_ = _up(_RI, P_)
        ok_ = np.isfinite(H_); P_, H_ = P_[ok_] - _BO, H_[ok_] - 10.0
        res = _lp(c=[-len(P_), -P_[:, 0].sum(), -P_[:, 1].sum()], A_ub=np.c_[np.ones(len(P_)), P_], b_ub=H_, bounds=[(None, None), (-2, 2), (-2, 2)])
        if not res.success: raise RuntimeError('階段の箱の壁の上端が決まらない：' + nm_)
        c_ = res.x; zf_ = lambda x, y, c_=c_: float(c_[0] + c_[1] * (x - _BO[0]) + c_[2] * (y - _BO[1]))
        _Ms.append(_prismM(fp_, zf_)); zz = [zf_(*np.ravel(xy(*at_(s, 0.0)))) for s in (s0_, s1_)]
        _box_log.append('%s %.0f〜%.0f' % (nm_, *zz))
    _W = _mf.Manifold.batch_boolean(_Ms, _mf.OpType.Add)
    _cuts = [_boxM(R(STAIR_U0 + 0.06, STAIR_U0 + STAIR_FOOT, -3.2, -2.8, 0.05), -200.0, 3170.0),          # 1 階の登り口（東の面、南の口の通路の側）
             _boxM(R(29.84, 30.16, -3.1, -4.94, 0.05), 3170.0, 3250.0 + 2100.0),                       # 2 階の着き口（南の面、箱の内面のあいだ）
             _boxM(R(*STAIR_DOOR, -5.16, -4.84, 0.05), -200.0, STAIR_DOOR_H)]                            # 階段の下の倉庫の戸（西の面）
    # 10-28 夕：倉庫の戸の両脇の柱（u30.24・u31.56、120×120、壁の厚みの中）の所は壁を欠く（柱が壁の厚みの中に収まる。前は壁と柱が重なり、
    # 削る段の後に「種類をまたぐ食い込み」が 2 残っていた）。欠きは壁の両面の外まで（面を重ねない）、高さは柱と同じ（床の 200 下〜3170）
    _cuts += [_boxM(R(uc - 0.06, uc + 0.06, vc - 0.16, vc + 0.16, 0.02), -200.0, 3170.0) for uc, vc in _BOXC if abs(vc + 5.0) < 1e-6 and STAIR_DOOR[0] - 0.1 < uc < STAIR_DOOR[1] + 0.1]
    _W = _W - _mf.Manifold.batch_boolean(_cuts, _mf.OpType.Add)
    _g = _W.to_mesh(); _V = np.asarray(_g.vert_properties)[:, :3].astype(float); _F = np.asarray(_g.tri_verts)
    _mm = r.Mesh()
    for x_, y_, z_ in _V: _mm.Vertices.Add(float(x_ + _BO[0]), float(y_ + _BO[1]), float(z_))
    for a_, b_, c_ in _F: _mm.Faces.AddFace(int(a_), int(b_), int(c_))
    _mm.Normals.ComputeNormals(); out.Objects.AddMesh(_mm, _BOX_ATTR)
    log.append('西館：階段の箱の壁を壁ごとの輪郭の押し出し−開口の一つの立体に（%d 三角形、上端：%s）' % (len(_F), '・'.join(_box_log)))
out.Write(OUT, 8)
print('\n'.join(log)); print('written', OUT, len(out.Objects))
