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
L11A = lidx('11a'); col_new = []; col_drop = set()
for o in m.Objects:
    if o.Attributes.LayerIndex != L11A: continue
    T = tris(o.Geometry); U = to_uv_arr(T.reshape(-1, 3))
    if U[:, 1].mean() > 1 or U[:, 1].min() > -0.205: continue
    mm = closed_mesh(o.Geometry); map_mesh_uv(mm, lambda u, v, z: (u, max(v, -0.20), z)); mm.Compact()   # 閉じた網目で（10-25 監修：三角形のスープから溶接すると閉じず、Rhino で柱が透けて見えた）
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
# 10-25（ソリッド係の依頼）：柱・梁・桁（22a〜d）は押し出しのまま、輪郭の制御点を動かす（extedit.py）。前は網目にしてから
# 頂点を動かしていて、Rhino 版でその所が細い平らな片の集まりになっていた。押し出しでないものだけ前と同じく網目で。
from shapely.geometry import LineString
import extedit
beam_new = []; beam_drop = set()
EXT = {}                                               # 物の Id → 動かした押し出し（22a〜d）
def cur_g(o): return EXT.get(str(o.Attributes.Id), o.Geometry)
_n_end = 0
for o in m.Objects:
    if o.Attributes.LayerIndex not in (L22B, L22C): continue
    g0 = o.Geometry
    P = tris(g0).reshape(-1, 3)
    if all(WN.buffer(-2).contains(Point(x, y)) for x, y in P[:, :2]): continue    # 壁の中で止まっている端（見えない）はそのまま
    c = P[:, :2].mean(0); X = P[:, :2] - c; w, vec = np.linalg.eigh(X.T @ X); ax = vec[:, -1]
    def _trim(V, k=0):
        V = V.copy()
        for i, (x, y, z) in enumerate(V):
            pt = Point(x, y)
            if WNi.contains(pt): continue
            s_ = np.dot(np.array([x, y]) - c, ax); dirn = -np.sign(s_) * ax          # 中ほどへ向かって
            ln = LineString([(x, y), (x + dirn[0] * 3000, y + dirn[1] * 3000)])
            hit = ln.intersection(WNi.exterior)
            pts = [hit] if hit.geom_type == 'Point' else list(getattr(hit, 'geoms', []))
            if pts:
                q = min(pts, key=lambda p: p.distance(pt)); V[i, 0], V[i, 1] = q.x + dirn[0] * 2, q.y + dirn[1] * 2
        return V
    e = extedit.edit(g0, _trim) if isinstance(g0, r.Extrusion) else None
    if e is not None: EXT[str(o.Attributes.Id)] = e
    else:
        mm = closed_mesh(g0); V = _trim(mesh_V(mm)); mesh_set(mm, V); mm.Normals.ComputeNormals(); mm.Compact()
        beam_new.append((mm, o.Attributes)); beam_drop.add(str(o.Attributes.Id))
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
    ms_ = _plates(T, _THK[li_], stair=(li_ == lidx('25_')))         # 面ごとの板（押し出し）に（10-25 ソリッド係、ユーザー）
    if not ms_: continue
    if li_ == lidx('24_') and (U[:, 1] < -4.9).any() and (U[:, 1] > -3.1).any() and T[:, :, 2].max() > 7000:   # 階段の箱：西の面に階段の下の倉庫の戸（10-25）
        _tb = trimesh.creation.extrude_polygon(R(*STAIR_DOOR, -5.3, -4.7, 0.05), 1750.0)
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
    beam_new.append((mm, o.Attributes)); beam_drop.add(str(o.Attributes.Id)); _n_thk += 1
log.append(f'西館：面だけの間仕切り・階段・室内窓 {_n_thk} 個に厚みを付けて閉じた')
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
            def _face_in(V, k=0):
                if k != 0: return V
                sp = (V[:, :2] - c) @ n
                on_ = sp >= np.interp(V[:, 2], zs_, env0) - TOL_F          # 外の縁の近くの制御点（曲線のふくらみがすき間を残さないよう少し広く）
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
def _deepen(g):
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
    curves2d = []; n_hole = 0
    for k_, nc in enumerate(extedit.profiles3d(g)):
        W = extedit._weights(nc); P = extedit._pts(nc)
        if k_ == 0:
            sp = (P[:, :2] - O[:2]) @ hd; zt = ztop(sp); dep = zt - P[:, 2]
            P[:, 2] = np.where(dep > 0, zt - dep * BEAM_K, P[:, 2])
        else:
            vh = np.mean([uv(x_, y_)[1] for x_, y_ in P[:, :2]])
            if vh > -2.0: n_hole += 1; continue                                    # 東の桁の穴（桁を下げたので要らない）
        Q = np.c_[(P - O) @ X, (P - O) @ Y, np.zeros(len(P))]
        extedit._set_pts(nc, Q, W); curves2d.append(nc)
    e = r.Extrusion()
    if not e.SetPathAndUp(a, b, pl.YAxis): return None, 0
    if not e.SetOuterProfile(curves2d[0], True): return None, 0
    for c2 in curves2d[1:]:
        if not e.AddInnerProfile(c2): return None, 0
    return e, n_hole
_n_deep = 0; _n_hole = 0; _BEAM_BOT_E = {}               # 架構の u → 東の桁の線（v −1.30）での梁の下端（2 枚のうち低いほう）
for o in m.Objects:
    if o.Attributes.LayerIndex != L22B: continue
    k_ = str(o.Attributes.Id); g = cur_g(o)
    if not isinstance(g, r.Extrusion) or k_ in _bn2: continue
    e, nh = _deepen(g)
    if e is None: continue
    EXT[k_] = e; _n_deep += 1; _n_hole += nh
    S_ = extedit.outer_samples(e, 2000); U_ = to_uv_arr(S_)
    near_ = np.abs(U_[:, 1] + 1.30) < 0.03
    if near_.any():
        uk = round(float(np.median(U_[:, 0])) / 3.0) * 3.0 if U_[:, 0].mean() > 22 else 21.3
        _BEAM_BOT_E[uk] = min(_BEAM_BOT_E.get(uk, 1e9), float(S_[near_, 2].min()))
log.append(f'西館：屋根の梁 {_n_deep} 枚のせいを 700 → 800 に（上端はそのまま、下へ）。東の端の桁の穴 {_n_hole} をふさいだ')
_n_g = 0; _gz = []
for o in m.Objects:
    if o.Attributes.LayerIndex != L22D: continue
    k_ = str(o.Attributes.Id); g = cur_g(o)
    if not isinstance(g, r.Extrusion): continue
    S_ = extedit.samples(g, 40); U_ = to_uv_arr(S_)
    if not (U_[:, 1].mean() > -1.6 and S_[:, 2].min() > 6500): continue              # 東の桁（屋根の高さ）だけ
    def _bot_at(uu):
        ks = sorted(_BEAM_BOT_E, key=lambda q: abs(q - uu))
        return _BEAM_BOT_E[ks[0]] if ks and abs(ks[0] - uu) < 0.6 else None
    a_, b_ = g.PathStart, g.PathEnd
    ua, ub = uv(a_.X, a_.Y)[0], uv(b_.X, b_.Y)[0]
    za_, zb_ = _bot_at(ua), _bot_at(ub)
    if za_ is None or zb_ is None: continue
    S0 = extedit.samples(g, 60, ends=(0.0,)); S1 = extedit.samples(g, 60, ends=(1.0,))
    dza, dzb = (za_ - 10.0) - S0[:, 2].max(), (zb_ - 10.0) - S1[:, 2].max()
    def _path(A, B, dza=dza, dzb=dzb):
        A[2] += dza; B[2] += dzb; return A, B
    e = extedit.edit(g, None, _path)
    if e is None: continue
    EXT[k_] = e; _n_g += 1; _gz.append(min(dza, dzb))
log.append(f'西館：東の桁 {_n_g} 本を梁の下端の 10 下へ（下げた量 約{-np.mean(_gz) if _gz else 0:.0f} mm）')
# 3) 2 階の床梁を受ける柱
for uc in (24.0, 27.0):
    _xbox(uc - 0.09, uc + 0.09, -3.20, -3.60, 0.0, 3170.0, L22A, f'骨格の柱 180×400（架構 u{uc:.0f}、2 階の床梁を受ける、キッチンの東の壁の線）')
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
_segs = [(a_[1], b_[0]) for a_, b_ in zip(_ecol, _ecol[1:])] + [(_ecol[-1][1], 50.75)] if _ecol else []
for u0_, u1_ in _segs:
    if u1_ - u0_ < 0.3: continue
    _xbox(u0_ + 0.002, u1_ - 0.002, -1.052, -1.172, BAND_Z0 - 180.0, BAND_Z0, L22D, '東の高窓の帯の窓台（120×180、柱と柱のあいだ）')
    _xbox(u0_ + 0.002, u1_ - 0.002, -1.052, -1.172, BAND_Z1, BAND_Z1 + 180.0, L22D, '東の高窓の帯のまぐさ（120×180、柱と柱のあいだ）')
log.append(f'西館：骨格の柱 2 本（u24・u27、v −3.4、180×400）、東の高窓の帯の窓台・まぐさ {2 * len(_segs)} 本')
# 5) 階段の箱の柱とまぐさ（壁の芯 v −2.99・−5.0、u30・33（床梁の下）・33.9、開口の両脇）
_BOXC = [(30.0, -2.99), (30.0, -5.0), (30.96, -2.99), (30.24, -5.0), (31.56, -5.0), (33.0, -2.99), (33.0, -5.0), (33.9, -2.99), (33.9, -5.0)]
for uc, vc in _BOXC:
    _xbox(uc - 0.06, uc + 0.06, vc - 0.06, vc + 0.06, 0.0, 3170.0, L22A, f'階段の箱の柱 120×120（骨格の耐力壁、u{uc:.2f}）')
_xbox(STAIR_DOOR[0] - 0.12, STAIR_DOOR[1] + 0.12, -4.94, -5.06, 1750.0, 1930.0, L22D, '階段の箱の倉庫の戸のまぐさ（120×180）')
log.append(f'西館：階段の箱を骨格の耐力壁に（柱 {len(_BOXC)} 本 120×120、倉庫の戸のまぐさ、u30・u33 の床梁を受ける）')

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
# 10-26夜（ユーザー、決定事項（共通）の「屋根の構成」、監修の項 20261026-1936）：屋根に厚み。下面＝梁の上端（＝垂木の下、元の面の 150 下）、
# 上面＝その 420 上（元の面の 270 上）。構成：太陽光 約40／野地板／通気層 45／透湿防水／木質繊維 t150（外張り）／気密／構造用合板 t24（現し）／垂木 60×150。
# 元の面より上にあった物（光の筋のガラス・立ち上がり・太陽光・越屋根の蓋・ルーバー・LED・外壁と越屋根の立ち上がりの上端）は 270 上げる。
RT_BOT, RT_TOP = -150.0, -41.0      # 10-27夜：梁の上端（RT_BOT）の上は通気垂木・野地・屋根材の約 110 だけ（断熱は梁のあいだ）
def zuv(x, y): return ROOF_Z(uv(x, y)[1])
def _rdz(dz, x, y): return dz(*uv(x, y)) if callable(dz) else dz      # 10-27夜：屋根の面からの高さは (u, v) の関数でもよい（軒の細らせ）
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
        for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zuv(x, y) + _rdz(dz, x, y)))
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
            for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zuv(x, y) + _rdz(dz, x, y)))
        for a, b, c in tri_: mm.Faces.AddFace(int(a), int(c), int(b)); mm.Faces.AddFace(int(a + n), int(b + n), int(c + n))
        for i in range(n):
            j = (i + 1) % n; mm.Faces.AddFace(i, j, j + n, i + n)
        mm.Normals.ComputeNormals(); mm.Compact(); out_.append(mm)
    return out_
def thick(poly, dz0, dz1):
    """平面形（穴あり可）を屋根の面から dz0〜dz1 の閉じた板に（屋根と平行）"""
    out_ = []
    for p in ([poly] if poly.geom_type == 'Polygon' else list(poly.geoms)):
        if p.area < 1e3: continue
        p = p.simplify(0.5)
        rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(h.coords)[:-1] for h in p.interiors]
        V2 = np.vstack(rings); n = len(V2); ends = np.cumsum([len(x) for x in rings]).astype(np.uint32)
        tri_ = _ec.triangulate_float64(V2, ends).reshape(-1, 3)
        mm = r.Mesh()
        for dz in (dz0, dz1):
            for x, y in V2: mm.Vertices.Add(float(x), float(y), float(zuv(x, y) + _rdz(dz, x, y)))
        for a, b, c in tri_: mm.Faces.AddFace(int(a), int(c), int(b)); mm.Faces.AddFace(int(a + n), int(b + n), int(c + n))
        st = 0
        for e in ends:
            for i in range(st, int(e)):
                j = i + 1 if i + 1 < e else st; mm.Faces.AddFace(i, j, j + n, i + n)
            st = int(e)
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
    for mm in thick(P_IN, RT_BOT, RT_TOP): new_objs.append((mm, at0))
    for mm in thick(P_EAST, RT_BOT, f_top): new_objs.append((mm, at0))
    a_in = r.ObjectAttributes(); a_in.LayerIndex = L10; a_in.Name = '断熱 木質繊維ボード t150（梁のあいだ、上面＝梁の上端）'
    for mm in thick(BAYS, INS_BOT, RT_BOT): new_objs.append((mm, a_in))
    a_r = r.ObjectAttributes(); a_r.LayerIndex = L10R; a_r.Name = '構造用合板 t24（母屋の上、天井に現し、気密はこの上）'
    for mm in thick(BAYS, PLY_BOT, INS_BOT): new_objs.append((mm, a_r))
    if EAVE is not None:
        for mm in thick(EAVE, RT_BOT, f_top): new_objs.append((mm, EAVE_AT))
    # 南の軒の骨（ユーザー 10-27夜、案 A）：塀（柵＝一本の線 v1.6、乳児の庭の外）の軒先に柱を一本、それより東は鋼の片持ちの骨（黒）で受ける。
    # 骨は約 1.5 mおき、架構 1 の梁の南の面（u −0.18）から軒先の 50 手前まで、上端＝梁の上端（軒の板の下）、せいは根元 200 → 先端 100（H-200×100 を細らせる）。
    # 骨の上の引っぱりは通気層の中の鋼の平板で架構 2 へ返す（3dm には描かない）。軒先の板の中に鋼の縁の材（骨の先をつなぎ、西の端は柱から持ち出す）。
    if EAVE is not None:
        L10S = new_layer('10s_本館_南の軒の鋼の骨と柱（黒）', (40, 40, 42))
        def _box(pts_uv, zf0, zf1):
            mm = r.Mesh()
            for zf in (zf0, zf1):
                for (uu_, vv_) in pts_uv:
                    x_, y_ = xy(uu_, vv_); mm.Vertices.Add(float(x_), float(y_), float(ROOF_Z(vv_) + zf(uu_, vv_)))
            n_ = len(pts_uv)
            mm.Faces.AddFace(0, 3, 2, 1); mm.Faces.AddFace(n_, n_ + 1, n_ + 2, n_ + 3)
            for i_ in range(n_):
                j_ = (i_ + 1) % n_; mm.Faces.AddFace(i_, j_, j_ + n_, i_ + n_)
            mm.Normals.ComputeNormals(); mm.Compact(); return mm
        _nrib = 0
        for vc in [0.10] + [round(1.6 + 1.5 * i, 2) for i in range(9)] + [14.90]:
            ue = u_edge(vc) + 0.05; u0r = -0.18
            if ue > u0r - 0.3: continue
            dep = lambda uu_, vv_, ue=ue: -(200.0 + (100.0 - 200.0) * (uu_ - u0r) / (ue - u0r))
            a_s = r.ObjectAttributes(); a_s.LayerIndex = L10S; a_s.Name = f'南の軒の鋼の骨（片持ち、H-200×100 を細らせる、v {vc:.2f}）'
            for hw_, z0f, z1f in ((0.006, lambda uu_, vv_: RT_BOT + dep(uu_, vv_), lambda uu_, vv_: RT_BOT - 12.0),     # ウェブ
                                  (0.050, lambda uu_, vv_: RT_BOT - 12.0, lambda uu_, vv_: RT_BOT),                     # 上のフランジ
                                  (0.050, lambda uu_, vv_: RT_BOT + dep(uu_, vv_), lambda uu_, vv_: RT_BOT + dep(uu_, vv_) + 12.0)):  # 下のフランジ
                new_objs.append((_box([(u0r, vc - hw_), (ue, vc - hw_), (ue, vc + hw_), (u0r, vc + hw_)], z0f, z1f), a_s))
            _nrib += 1
        _up, _vp = u_edge(1.6) + 0.15, 1.6
        _zt = ROOF_Z(_vp) + RT_BOT - 100.0
        a_p = r.ObjectAttributes(); a_p.LayerIndex = L10S; a_p.Name = '南の軒の柱（鋼 角 100、塀＝一本の線の上、乳児の庭の外）'
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
        for mm in slab(R(u - SL_HALF, u + SL_HALF, VE, V_TIP, 0.2), lambda u_, v_: f_top(u_, v_) - 12.0, f_top): new_objs.append((mm, at_g))     # 東の軒の筋：屋根の面にそろえた合わせガラス t12（外なので単板）
        for mm in slab(R(u - SL_HALF, u + SL_HALF, SL_GL - 0.006, SL_GL + 0.006, 0.05), -250.0, RT_TOP + 60.0): new_objs.append((mm, at_g))  # 外皮の線の固定ガラス（複層）
        for uu in (u - SL_HALF - 0.012, u + SL_HALF):                                                                       # 筋の内側の板（上の層の小口をふさぐ）
            for mm in slab(R(uu, uu + 0.012, SL_V[0], VE, 0.2), RT_BOT, RT_TOP): new_objs.append((mm, a10))
            for mm in slab(R(uu, uu + 0.012, VE, V_TIP, 0.2), RT_BOT, f_top): new_objs.append((mm, a10))
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
                for mm in thick(q_, z0_, z1_): new_objs.append((mm, a_rf)); _nr += 1
    log.append(f'本館：屋根の構成（10-27夜）：母屋 {_nr} 本（10v）・合板 t24（10r）・断熱 t150 は梁のあいだ、梁の上は {RT_TOP - RT_BOT:.0f}、'
               f'東の軒は軒先で {EAVE_TIP:.0f}')
    ALL = unary_union([RP, EAVE.buffer(1.0)]).buffer(-1.0) if EAVE is not None else RP
    pv_box = unary_union([R(-10.0, 57.49, 1.95, 14.85, 0.25), R(-10.0, -0.35, -1.0, 14.85, 0.25)])
    pv = ALL.buffer(-150.0, join_style=2).intersection(pv_box).intersection(unary_union([RP, EAVE]) if EAVE is not None else RP)
    pv = pv.difference(R(-0.36, 57.49, -1.0, 1.95, 0.1)).difference(unary_union([R(u - 0.25, u + 0.25, SL_V[0] - 0.2, SL_V[1] + 0.2, 0.2) for u in SL_U]))
    a_pv = r.ObjectAttributes(); a_pv.LayerIndex = L10P
    _TAPER = unary_union([_BIG(0.0, 60.0, VE, 16.0), _BIG(-10.0, 0.0, -3.0, 16.0)]); pv_e = pv.intersection(_TAPER); pv_i = pv.difference(_TAPER)
    for mm in sheet(pv_i, RT_TOP + 20.0, L10P): new_objs.append((mm, a_pv))
    for mm in sheet(pv_e, lambda u_, v_: f_top(u_, v_) + 20.0, L10P): new_objs.append((mm, a_pv))           # 東の軒の上も屋根の面に沿って切れ目なく
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
    log.append(f'本館：光の筋 {len(SL_U)} 本（架構 2〜19、2 枚の梁のあいだ 180、v {SL_V[0]}〜{SL_V[1]}＝越屋根から軒先まで、乳白ガラス）、'
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
        for mm in slab(R(uu - 0.3, uu + 0.3, 1.56, 1.64, 0.05), RT_TOP + 175.0, RT_TOP + 305.0): new_objs.append((mm, a_v))
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
    _VK = [v_ for v_ in _VK if not (_COLS[0][0] - 0.1 <= v_ <= _COLS[0][1] + 0.1)]
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
_fp20 = [foot(o.Geometry) for o in m.Objects if o.Attributes.LayerIndex == L20 and isinstance(o.Geometry, r.Mesh)]
WSL = unary_union([f for f in _fp20 if f is not None]).buffer(-1.0)   # 10-24（ユーザー、本館と同じ）：越屋根から軒先まで。軒先＝屋根の面の先（10-24昼：西の軒の出 0.9、軒樋の手前）
EASTV = -2.56                          # 越屋根の西の立ち上がりの外面（10-25：越屋根の幅 1.0 → 1.6）
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
L21W = lidx('21_'); _CANT = []; _cant_ms = []
for o in m.Objects:
    if o.Attributes.LayerIndex != L22B: continue
    g = cur_g(o)
    if not isinstance(g, r.Extrusion): continue
    S_ = extedit.outer_samples(g, 1500); U_ = to_uv_arr(S_)
    iw = int(np.argmin(U_[:, 1]))                                             # 西の端（v がいちばん小さい点）
    pl = g.GetProfilePlane(0.0); O = np.array([pl.Origin.X, pl.Origin.Y, pl.Origin.Z])
    X = np.array([pl.XAxis.X, pl.XAxis.Y, pl.XAxis.Z]); Y = np.array([pl.YAxis.X, pl.YAxis.Y, pl.YAxis.Z])
    hd = np.array([X[0], X[1]]) if abs(X[2]) < 0.5 else np.array([Y[0], Y[1]]); hd = hd / np.linalg.norm(hd)
    s_all = (S_[:, :2] - O[:2]) @ hd; sw = s_all[iw]; sg = -1.0 if sw < np.median(s_all) else 1.0     # 外へ向かう向き
    p_w = O[:2] + hd * sw
    if WS_W.contains(Point(*(p_w + hd * sg * 400.0))): continue                # 外壁の内面で止まっていない端（妻の側など）は出さない
    _x = LineString([p_w, p_w + hd * sg * 4000.0]).intersection(WSL.exterior)
    _ps = [_x] if _x.geom_type == 'Point' else list(getattr(_x, 'geoms', []))
    if not _ps: continue
    s_tip = min(((np.array([q.x, q.y]) - O[:2]) @ hd for q in _ps), key=lambda t: abs(t - sw)) - sg * 100.0
    if (s_tip - sw) * sg < 300.0: continue
    a_, b_ = g.PathStart, g.PathEnd
    A3 = np.array([a_.X, a_.Y, a_.Z]); B3 = np.array([b_.X, b_.Y, b_.Z])
    def P3(s, z): q = O[:2] + hd * s; return [float(q[0]), float(q[1]), float(z)]
    zt_w = float(roof_z(np.array([O[:2] + hd * sw]))[0]); zt_t = float(roof_z(np.array([O[:2] + hd * s_tip]))[0])
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
    at_ = r.ObjectAttributes(); at_.LayerIndex = L22B; at_.Name = '出し梁（2 枚組の梁の先、外壁を貫いて軒先まで、せい 240 → 120）'
    _XNEW.append((best[1], at_)); _CANT.append(best[1])
    T_c = tri.tri_extrusion(best[1])
    if len(T_c):
        tm_c = trimesh.Trimesh(T_c.reshape(-1, 3), np.arange(len(T_c) * 3).reshape(-1, 3)); tm_c.merge_vertices()
        tm_c.fix_normals()
        try: _cant_ms.append(_mf.Manifold(_mf.Mesh(vert_properties=np.asarray(tm_c.vertices, np.float32), tri_verts=np.asarray(tm_c.faces, np.uint32))))
        except Exception: pass
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
log.append(f'西館：出し梁 {len(_CANT)} 枚（2 枚組の梁の先を外壁を貫いて軒先の 0.1 手前まで、せい 240 → 120）、外壁 {_nwall} 片を出し梁の所で欠いた')
if slits:
    L20T = new_layer('20t_西館_光の筋（乳白ガラス、架構の線）', (225, 236, 242), MAT_FROST if MAT_FROST >= 0 else None)
    L20P = new_layer('20p_西館_屋根材型の太陽光（金属の屋根と一体）', (45, 49, 58))
    a20 = r.ObjectAttributes(); a20.LayerIndex = L20
    at_g2 = r.ObjectAttributes(); at_g2.LayerIndex = L20T
    if MAT_FROST >= 0: at_g2.MaterialSource = r.ObjectMaterialSource.MaterialFromObject; at_g2.MaterialIndex = MAT_FROST
    SL20 = unary_union([strip(cc, ax, nrm, t0, t1, -90, 90) for cc, ax, nrm, t0, t1 in slits])
    # 屋根に厚み（10-27、ユーザー・監修 20261026-1936）：下面＝梁の上端（今までの屋根の面）、上面＝その 420 上（軒・棟は水平のまま、
    # 勾配も同じ。棟 8.15 → 8.57、軒 4.65 → 5.07）。構成は本館と同じ（太陽光／野地板／通気層 45／透湿防水／木質繊維 t150 外張り／気密／
    # 構造用合板 t24 現し／垂木 60×150）。屋根の面（20 の面それぞれ）を上へ 420 の閉じた立体にし、光の筋を厚さいっぱい抜く。
    RT_W = 420.0
    def _thicken(g, dz, dz0=0.0):
        T_ = tris(g)
        if not len(T_): return None
        tm_ = trimesh.Trimesh(T_.reshape(-1, 3), np.arange(len(T_) * 3).reshape(-1, 3)); tm_.merge_vertices(digits_vertex=0)
        tm_.update_faces(tm_.nondegenerate_faces()); tm_.remove_unreferenced_vertices()
        V_, F_ = np.asarray(tm_.vertices), np.asarray(tm_.faces); n_ = len(V_)
        if np.mean(tm_.face_normals[:, 2]) < 0: F_ = F_[:, ::-1]                       # 上向きの面に
        Vt = np.vstack([V_ + [0, 0, dz0], V_ + [0, 0, dz]])
        Ft = [F_[:, ::-1], F_ + n_]                                                     # 下面（下向き）・上面（上向き）
        ed = np.sort(np.vstack([F_[:, [0, 1]], F_[:, [1, 2]], F_[:, [2, 0]]]), axis=1)
        uq, cnt = np.unique(ed, axis=0, return_counts=True); bset = {tuple(e_) for e_ in uq[cnt == 1]}
        side = []
        for a_, b_, c_ in F_:                                                           # 縁の辺の向きは面の向きにそろえる
            for p_, q_ in ((a_, b_), (b_, c_), (c_, a_)):
                if tuple(sorted((p_, q_))) in bset: side += [[p_, q_, q_ + n_], [p_, q_ + n_, p_ + n_]]
        Ft.append(np.array(side, int).reshape(-1, 3))
        M_ = _mf.Manifold(_mf.Mesh(vert_properties=Vt.astype(np.float32), tri_verts=np.vstack(Ft).astype(np.uint32)))
        return M_ if not M_.is_empty() else None
    def _m2r(M_):
        g_ = M_.to_mesh(); mm_ = r.Mesh()
        for x_, y_, z_ in np.asarray(g_.vert_properties)[:, :3]: mm_.Vertices.Add(float(x_), float(y_), float(z_))
        for a_, b_, c_ in np.asarray(g_.tri_verts): mm_.Faces.AddFace(int(a_), int(b_), int(c_))
        mm_.Normals.ComputeNormals(); mm_.Compact(); return mm_
    _sl_ms = []
    for _pg in getattr(SL20.buffer(0), 'geoms', [SL20.buffer(0)]):
        _slit_tm = trimesh.creation.extrude_polygon(_pg, 14000.0); _slit_tm.apply_translation([0, 0, -1000.0])
        _sl_ms.append(_mf.Manifold(_mf.Mesh(vert_properties=np.asarray(_slit_tm.vertices, np.float32), tri_verts=np.asarray(_slit_tm.faces, np.uint32))))
    _SLIT_M = _mf.Manifold.batch_boolean(_sl_ms, _mf.OpType.Add)
    roofs20 = []; _n_thk20 = 0
    RAF_W, RT_W0 = 150.0, 174.0                                   # 垂木のせい、合板の上（梁の上端から）
    L20R = new_layer('20r_西館_屋根の下面の構造用合板（t24、現し）', (214, 190, 150)); a20r = r.ObjectAttributes(); a20r.LayerIndex = L20R
    L20V = new_layer('20v_西館_垂木（杉 60×150 @455、現し）', (196, 160, 118)); a20v = r.ObjectAttributes(); a20v.LayerIndex = L20V
    for o in m.Objects:
        if o.Attributes.LayerIndex != L20 or not isinstance(o.Geometry, r.Mesh): continue
        fp = foot(o.Geometry)
        if fp is None: continue
        roofs20.append(fp)
        # 屋根を層に分ける（10-27夕、監修の項 20261027-1700：室内から見上げると屋根の立体の素材（黒い金属）が見えていた）：
        # 梁の上端から 0〜150 は垂木（20v、下で足す）、150〜174 は構造用合板 t24（20r、現し）、174〜420 が上の層（金属・太陽光〜断熱、20 のまま）。
        M_ = _thicken(o.Geometry, RT_W, RT_W0)
        Mr_ = _thicken(o.Geometry, RT_W0, RAF_W)
        if M_ is None or Mr_ is None:
            if fp.intersection(SL20).area >= 1e4:
                drop.add(str(o.Attributes.Id)); new_objs.append((drape(fp.difference(SL20), RT_W0, RT_W), o.Attributes))
                new_objs.append((drape(fp.difference(SL20), RAF_W, RT_W0), a20r))
            continue
        if fp.intersection(SL20).area >= 1e4: M_ = M_ - _SLIT_M; Mr_ = Mr_ - _SLIT_M
        drop.add(str(o.Attributes.Id)); new_objs.append((_m2r(M_), o.Attributes)); new_objs.append((_m2r(Mr_), a20r)); _n_thk20 += 1
    log.append(f'西館：屋根 {_n_thk20} 片を梁の上端から 420 の閉じた立体に（光の筋を厚さいっぱい抜いた）')
    RP20 = unary_union(roofs20)
    # 垂木（20v）：弧（v 一定）に沿って @455、梁から梁へ（光の筋の縁＝梁の内面で止まる）、梁の上端から 150。越屋根の下（屋根の面を開けた所）は無い。
    _RAFZ = RP20.difference(SL20.buffer(0.5)); _vr = -2.56 - 0.03; _nraf = 0; _raf_rows = []
    while _vr > -16.5:
        _us = np.arange(18.0, 54.01, 0.25)
        _rp = Polygon([xy(u_, _vr + 0.03) for u_ in _us] + [xy(u_, _vr - 0.03) for u_ in _us[::-1]])
        _pc = _rp.intersection(_RAFZ)
        for _pg in ([_pc] if _pc.geom_type == 'Polygon' else [q for q in getattr(_pc, 'geoms', []) if q.geom_type == 'Polygon']):
            if _pg.area < 60.0 * 400.0: continue
            _raf_rows.append(_pg); _nraf += 1
        _vr -= 0.455
    for _k in range(0, len(_raf_rows), 40):                         # 40 本ずつ一つの物に（物の数を増やしすぎない）
        _mm = r.Mesh()
        for _pg in _raf_rows[_k:_k + 40]: _mm.Append(drape(_pg, 0.0, RAF_W))
        _mm.Normals.ComputeNormals(); _mm.Compact()
        _av = r.ObjectAttributes(); _av.LayerIndex = L20V; _av.Name = '垂木 杉 60×150 @455（梁から梁へ、現し）'
        new_objs.append((_mm, _av))
    log.append(f'西館：屋根を層に分けた（上の層 20：梁の上端から 174〜420、構造用合板 t24 20r：150〜174、垂木 60×150 @455 20v：{_nraf} 本）')
    # 筋の両側の梁の下端（鏡面の板の下の端）：2 枚の梁（22b）に下から鉛直の線を当てる
    _bmt = [closed_mesh(bm.get(str(o.Attributes.Id), cur_g(o))) for o in m.Objects if o.Attributes.LayerIndex == L22B]
    _BT = trimesh.util.concatenate([trimesh.Trimesh(mesh_V(g_), np.array([[g_.Faces[i][0], g_.Faces[i][1], g_.Faces[i][2]] for i in range(g_.Faces.Count)]), process=False) for g_ in _bmt])
    _BI = trimesh.ray.ray_triangle.RayMeshIntersector(_BT)
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
        """筋の側面（nrm の a〜b_）に、梁の下端から屋根の面＋ztop_d までの薄い板（step ごとの角柱の集まり）"""
        mm_ = r.Mesh(); sgn = 1 if a > 0 else -1
        ts = np.r_[np.arange(t0, t1, step), t1]
        for ta, tb in zip(ts, ts[1:]):
            P4 = np.array([cc + ax * ta + nrm * a, cc + ax * tb + nrm * a, cc + ax * tb + nrm * b_, cc + ax * ta + nrm * b_])
            zr = roof_z(P4); zb_ = beam_bottom(P4 + nrm * sgn * 45.0)               # 梁の中ほど（筋の縁から 45 外）の下端
            if np.isnan(zb_).any(): zb_ = zr - 600.0
            base = len(mm_.Vertices)
            for (x_, y_), z_ in zip(P4, zb_): mm_.Vertices.Add(float(x_), float(y_), float(z_))
            for (x_, y_), z_ in zip(P4, zr): mm_.Vertices.Add(float(x_), float(y_), float(z_ + ztop_d))
            for f_ in ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7), (0, 1, 5), (0, 5, 4), (1, 2, 6), (1, 6, 5), (2, 3, 7), (2, 7, 6), (3, 0, 4), (3, 4, 7)):
                mm_.Faces.AddFace(*[base + i for i in f_])
        mm_.Normals.ComputeNormals(); mm_.Compact(); return mm_
    L22T = None; _n22t = 0
    for cc, ax, nrm, t0, t1 in slits:
        uc_ = uv(*cc)[0]; e = 1 if np.dot(ax, np.array(xy(uc_, EASTV)) - np.array(xy(uc_, -10))) > 0 else -1     # 東（高い側）の向き
        tE = t1 if e > 0 else t0; tW = t0 if e > 0 else t1
        lo, hi = min(tW, tE), max(tW, tE)
        new_objs.append((drape(strip(cc, ax, nrm, lo, hi, -150, -90), RT_W, RT_W + 60.0), a20))     # 立ち上がり（屋根の上面の上）
        new_objs.append((drape(strip(cc, ax, nrm, lo, hi, 90, 150), RT_W, RT_W + 60.0), a20))
        # 東の端は越屋根の西の立ち上がりがふさぐ（端の立ち上がりは足さない）
        # 西の端（外壁の内面の線、10-27夕）に端の立ち上がり 60 を足し、ガラスはその上まで（水は端の立ち上がりを越えて屋根の上を軒樋へ）
        kW0, kW1 = sorted((tW, tW - 60.0 * e))
        new_objs.append((drape(strip(cc, ax, nrm, kW0, kW1, -150, 150), RT_W, RT_W + 60.0), a20))
        glo, ghi = min(tW - 60.0 * e, tE), max(tW - 60.0 * e, tE)                # ガラスは越屋根の立ち上がりから西の端の立ち上がりまで
        new_objs.append((drape(strip(cc, ax, nrm, glo, ghi, -150, 150), RT_W + 60.0, RT_W + 72.0), at_g2))    # 乳白ガラス（複層：遮熱 Low-E＋乳白の合わせ）
        _pts = [True]; tS = tW                                                   # 筋の西の端＝外壁の内面の線（外皮の線の固定ガラスは要らなくなった）
        for a_, b_ in ((-90, -88), (88, 90)):                                                    # 筋の内側：ガラスの下から梁の下端まで鏡面のアルミ t2
            new_objs.append((mirror(cc, ax, nrm, t0, t1, a_, b_, RT_W + 60.0), a20m))
        # 光の筋をまたいで屋根の面をつなぐ（10-27、ユーザー・監修の略算、決定事項（共通）の「地震の力は骨格で受ける」）：2 枚の梁の上端に
        # 溝をまたぐ鋼の平板 6×60（長さ 340、梁の上端に彫り込み、22t）を約 0.9 mおき、外壁の内面から越屋根の側まで。筋の両端は溝をまたぐ縁の材
        # （杉 60×150、垂木の高さ、鏡面のあいだ、垂木と同じ 20v）：越屋根の側と軒先の側。屋根の上からの見えは変えない。本館の 10k と同じ。
        if L22T is None: L22T = new_layer('22t_西館_光の筋をまたぐつなぎ（鋼の平板・縁の材）', (120, 120, 125))
        tIn = (tS if _pts else tW + 1200.0 * e) + 300.0 * e; tOut = tE - 300.0 * e          # 平板の範囲（外壁の内面の内 0.3 〜 越屋根の側の 0.3 手前）
        _pl22 = r.Mesh(); _nk1 = 0
        for t_ in np.arange(min(tIn, tOut), max(tIn, tOut) + 1.0, 900.0):
            _pl22.Append(drape(strip(cc, ax, nrm, t_ - 30.0, t_ + 30.0, -170.0, 170.0), -6.0, 0.0)); _nk1 += 1
        _pl22.Normals.ComputeNormals(); _pl22.Compact()
        a_k = r.ObjectAttributes(); a_k.LayerIndex = L22T; a_k.Name = f'光の筋をまたぐ鋼の平板 6×60（架構 u{uc_:.0f}、{_nk1} 枚、約 0.9 mおき）'
        new_objs.append((_pl22, a_k)); _n22t += _nk1
        for ta_, tb_, nm_ in ((tE - 60.0 * e, tE, '越屋根の側'), (tW, tW + 60.0 * e, '外壁の側')):
            a_e = r.ObjectAttributes(); a_e.LayerIndex = L20V; a_e.Name = f'光の筋の端の縁の材（杉 60×150、{nm_}、架構 u{uc_:.0f}）'   # 杉は垂木の層（一つのレイヤーには一つの素材、10-27夕）
            a_e.ColorSource = r.ObjectColorSource.ColorFromObject; a_e.ObjectColor = (196, 160, 118, 255)
            new_objs.append((drape(strip(cc, ax, nrm, min(ta_, tb_), max(ta_, tb_), -87.0, 87.0), 0.0, 150.0), a_e))
    log.append(f'西館：光の筋をまたぐつなぎ（22t）：鋼の平板 {_n22t} 枚（{len(slits)} 本の筋、約 0.9 mおき）と筋の両端の縁の材 {2 * len(slits)}')
    pv20 = RP20.buffer(-150.0, join_style=2)                  # 軒先の水切り150を残す（10-24、本館と同じ）
    pv20 = pv20.difference(Polygon([xy(u_, 1.0) for u_ in np.arange(19, 53.1, 0.5)] + [xy(u_, -2.85) for u_ in np.arange(53, 18.9, -0.5)]))   # 越屋根の蓋の西の縁（10-25：−2.25 → −2.85）
    pv20 = pv20.difference(unary_union([strip(cc, ax, nrm, t0 - 200, t1 + 200, -250, 250) for cc, ax, nrm, t0, t1 in slits]))
    a_pv2 = r.ObjectAttributes(); a_pv2.LayerIndex = L20P
    new_objs.append((drape(pv20, RT_W + 20.0), a_pv2))                       # 屋根の上面の 20 上
    log.append(f'西館：光の筋 {len(slits)} 本（u ' + '・'.join(f'{uv(*s[0])[0]:.0f}' for s in slits) +
               f'、2 枚の梁のあいだ 180、越屋根から外壁の内面まで、乳白ガラス、20t）、屋根材型の太陽光 {pv20.area / 1e6:.0f} m²（20p）')

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
out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for o in m.Objects:
    if str(o.Attributes.Id) in drop or str(o.Attributes.Id) in col_drop or str(o.Attributes.Id) in beam_drop: continue
    out.Objects.Add(EXT.get(str(o.Attributes.Id), o.Geometry), o.Attributes)      # 22a〜d は動かした押し出し（EXT）
for mm, at in new_objs + col_new + beam_new: out.Objects.AddMesh(mm, at)
for g_, at_ in _XNEW: out.Objects.Add(g_, at_)                                 # 構造の直し（10-27）の柱・横材（押し出し）
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
        for f_, a_, za, zb in _F2[k]:
            if zb - za < 5: K.flat(f_.difference(_cutE), za, a_.LayerIndex)
            else: K.prism(f_.difference(_cutE), za, zb, a_.LayerIndex)
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
if _L19C_: K.prism(R(STAIR_DOOR[0] - 0.05, STAIR_DOOR[1] + 0.05, -5.12, -5.09, 0.05), 10.0, 1750.0, _L19C_[0])
log.append('西館：階段の下の倉庫 %.1f m²（36b、戸は階段の箱の西の面 u%.2f〜%.2f）' % (_stg.area / 1e6, *STAIR_DOOR))
K.prism(R(21.16, 32.95, -2.56, -2.50, 0.1), ZF2, ZF2 + 1100.0, L38)       # 2 階の東の縁（東の帯への吹き抜け、10-25：1.0 → 1.6）
K.prism(R(32.97, 33.03, -2.93, -2.56, 0.02), ZF2, ZF2 + 1100.0, L38)      # 2 階の北の口（遊戯室の吹き抜け、10-27：箱の東の外まで）
for _f, _li, _z in _F31: K.flat(_f.difference(_STX), _z, _li)
# 東の帯の吹き抜け（スパン 8〜11、u 21〜33）に天井扇（10-25、ユーザー：設置は可能？ → 吹き抜けを 1.6 にして入る）。
# 遊戯室の天井扇（スパン 12〜17）と同じ φ1.1・h6.0、吹き抜けの真ん中（v −1.8、西館の東の壁の内面から 0.75）。
_LFAN = out.Layers.Add(r.Layer()); out.Layers[_LFAN].Name = '58b_西館_東の帯の吹き抜け_天井扇'; out.Layers[_LFAN].Color = (90, 122, 154, 255)
from shapely.geometry import Point as _Pt
for _uf in (22.5, 25.5, 28.5, 31.5):
    _c = xy(_uf, -1.8)
    K.prism(_Pt(*_c).buffer(550, resolution=24), 5980.0, 6000.0, _LFAN)          # 羽根の回る範囲
    K.prism(_Pt(*_c).buffer(110, resolution=16), 5960.0, 6080.0, _LFAN)          # モーター
    K.prism(_Pt(*_c).buffer(15, resolution=8), 6080.0, 7500.0, _LFAN)           # 吊り棒（越屋根の立ち上がりの受けへ）
log.append('西館：東の帯の吹き抜け（スパン 8〜11）に天井扇 4 台（φ1.1、h6.0、58b）')
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
out.Write(OUT, 8)
print('\n'.join(log)); print('written', OUT, len(out.Objects))
