"""3dm の物を閉じた立体（manifold3d）として扱う共通の部品（設計監修、10-24）
干渉の一覧（clash.py）と、優先順位で削る段（clip_parts.py）が使う。

部材の種類（優先順位の高い順。高いものが低いものを削る。構造と外皮どうしは削らず報告する）：
  S 構造      柱・梁・桁・2階床梁（11a・11b・11c・22a〜22d）
  E 外皮      屋根（10・20）・外壁（17・21）・光の筋のガラス（10t・20t）・越屋根の蓋（28・50a）・外まわりの建具とガラス（16・19・89）
  F 床        床の板（12・13・14・15・23）
  D 建具      室内の戸（19c・19d）（戸の開口に出ている壁を削る）
  P 間仕切り  間仕切り・鴨居・腰壁・室内窓・しつらえのガラスと格子（18・24・27・38・48・49）
  I 家具      しつらえ・遊具・林・設備の箱（25・35b・37・39・40・46・51・55・58・80〜88）
  X 外の付属  下屋・外構・樋・屋根の上のもの（21g・26・29・30・50b・50c・60〜79、10p・20p）
  （部屋の床の板 31〜36・41〜45・52〜59、敷地・周辺・園庭・コット（00〜04・47・90〜98）は扱わない）
"""
import re, numpy as np, rhino3dm as r, trimesh, manifold3d as mf
from shapely.geometry import Polygon
try:
    import mapbox_earcut as earcut
except ImportError:
    earcut = None

CLASS_RE = [
    ('S', r'^(11a|11b|11c|22a|22b|22c|22d|10v|20v|10s|10b)_'),     # 10-27：垂木（屋根を層に分けた）・通気垂木 10b（本館係、10-27夜）
    ('E', r'^(10|20|10r|20r|17|17y|21|10t|20t|28|50a|16|19|19f|89)_'),     # 10-27：屋根の構造用合板
    ('F', r'^(12|13|14|15|23)_'),
    ('P', r'^(18|24|27|38|48|49)_'),
    ('D', r'^(19c|19d)_'),
    ('I', r'^(25|35b|37|39|40|46|51|51w|55|58|8[0-8])_'),
    ('X', r'^(21g|26|29|30|50b|50c|6[0-9][a-z]?|7[0-9][a-z]?|10p|20p)_'),     # 10-27：外構の樹冠・生垣を英字一つで分ける（67c・70h・77c・79c）
]
RANK = {'S': 0, 'E': 1, 'F': 2, 'D': 3, 'P': 4, 'I': 5, 'X': 6}     # 戸は間仕切りより上（戸の開口に壁が出ていれば壁を削る）
def klass(ln):
    for k, pat in CLASS_RE:
        if re.match(pat, ln): return k
    return None

A3 = lambda ps: np.array([[p.X, p.Y, p.Z] for p in ps], float)
CURVE_TURN = 3.0 * np.pi / 180      # 曲線を折れ線にするときの、一つの辺の両端の接線の開き（10-25 ソリッド係）
def curve_pts(c, n=48):
    """曲線 → 折れ線の点。線は端だけ、曲線は区間（スパン）ごとに、接線の開きが CURVE_TURN 以下になるまで二つに分ける。
    前は曲線全体を n 等分していた：輪郭の線の所に点が多く、柱の頭の曲線は 137 mm おき（折れ 5〜60°）になり、
    Rhino 版でスプラインに戻せなかった（ソリッド係、10-25）。折れが 1.5° 以上になるよう、細かくしすぎない"""
    if isinstance(c, r.PolylineCurve): return [c.Point(i) for i in range(c.PointCount)]
    if isinstance(c, r.LineCurve): return [c.PointAtStart, c.PointAtEnd]
    if isinstance(c, r.PolyCurve):
        out = []
        for i in range(c.SegmentCount):
            q = curve_pts(c.SegmentCurve(i), n)
            out += q if not out else q[1:]
        return out
    nc = c.ToNurbsCurve() if not isinstance(c, r.NurbsCurve) else c
    if nc is None:
        d = c.Domain; return [c.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1)]
    if nc.Degree == 1 and not nc.IsRational: return [r.Point3d(nc.Points[i].X, nc.Points[i].Y, nc.Points[i].Z) for i in range(len(nc.Points))]
    d = nc.Domain; ks = sorted({float(nc.Knots[i]) for i in range(len(nc.Knots))} | {d.T0, d.T1})
    ks = [k for k in ks if d.T0 <= k <= d.T1]
    def tan(t):
        v = nc.TangentAt(t); return np.array([v.X, v.Y, v.Z])
    def rec(t0, t1, a0, a1, dep, acc):
        if dep < 12 and np.arccos(np.clip(a0 @ a1, -1, 1)) > CURVE_TURN:
            tm = 0.5 * (t0 + t1); am = tan(tm)
            rec(t0, tm, a0, am, dep + 1, acc); rec(tm, t1, am, a1, dep + 1, acc)
        else: acc.append(t1)
    ts = [ks[0]]
    for k0, k1 in zip(ks, ks[1:]):
        rec(k0, k1, tan(k0 + 1e-9 * (k1 - k0)), tan(k1 - 1e-9 * (k1 - k0)), 0, ts)
    return [nc.PointAt(t) for t in ts]

def mesh_vf(g):
    V = A3([g.Vertices[i] for i in range(len(g.Vertices))]); F = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; F.append((f[0], f[1], f[2]))
        if f[3] != f[2]: F.append((f[0], f[2], f[3]))
    return V, np.array(F, int).reshape(-1, 3)

def _cap(ring):
    P = np.asarray(ring); c = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c); B = Vt[:2]
    Q = (P - c) @ B.T
    idx = earcut.triangulate_float64(Q, np.array([len(P)], np.uint32))
    return [P[idx[i:i + 3]] for i in range(0, len(idx), 3)]

def extrusion_vf(g):
    """押し出し（柱・梁など）→ 閉じた三角形の網。輪が複数なら、入れ子は穴、離れた輪は別の形（偶奇）"""
    rings = []
    for k in range(g.ProfileCount):
        c = g.Profile3d(k, 0.0)
        if c is None: continue
        p = A3(curve_pts(c, 64))
        if np.linalg.norm(p[0] - p[-1]) < 1.0: p = p[:-1]
        if len(p) >= 3: rings.append(p)
    if not rings: return None
    d = np.array([g.PathEnd.X - g.PathStart.X, g.PathEnd.Y - g.PathStart.Y, g.PathEnd.Z - g.PathStart.Z])
    P = np.vstack(rings); c0 = P.mean(0)
    _, _, Vt = np.linalg.svd(P - c0); B0, B1, nrm = Vt[0], Vt[1], Vt[2]
    h = float(np.dot(d, nrm))
    if abs(h) < 1e-6: return None
    if h < 0: B1 = -B1; nrm = -nrm; h = -h            # 右手系のまま押し出す向きを +z に
    poly = None
    for rg in rings:
        pg = Polygon(np.c_[(rg - c0) @ B0, (rg - c0) @ B1]).buffer(0)
        poly = pg if poly is None else poly.symmetric_difference(pg)
    if poly is None or poly.is_empty: return None
    Vs, Fs, off = [], [], 0
    for pg in getattr(poly, 'geoms', [poly]):
        if pg.geom_type != 'Polygon' or pg.area < 1: continue
        t = trimesh.creation.extrude_polygon(pg, h)
        L = np.asarray(t.vertices)
        W = c0 + np.outer(L[:, 0], B0) + np.outer(L[:, 1], B1) + np.outer(L[:, 2] / h, d)
        Vs.append(W); Fs.append(np.asarray(t.faces) + off); off += len(W)
    if not Vs: return None
    V, F = np.vstack(Vs), np.vstack(Fs)
    if trimesh.Trimesh(V, F, process=False).volume < 0: F = F[:, ::-1]      # 輪の向きと押し出しの向きで裏返る（10-25）
    return V, F

def to_trimesh(V, F):
    """閉じた形になる読み方を順に試す：そのまま → 潰れた面を除く → 0.1 mm でずれた頂点を寄せる
    （閉じていれば寄せない：細かい曲線の点がつぶれる）"""
    t = trimesh.Trimesh(V, F, process=True, validate=True); t.merge_vertices(digits_vertex=1)
    t.update_faces(t.nondegenerate_faces()); t.remove_unreferenced_vertices()
    if not (t.is_watertight and t.is_winding_consistent):
        t1 = trimesh.Trimesh(V, F, process=True)
        if t1.is_watertight and t1.is_winding_consistent: t = t1
    if t.is_watertight and t.volume < 0: t.invert()
    return t

def to_manifold(t):
    if t is None or not t.is_watertight or not t.is_winding_consistent: return None
    try:
        M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
        if M.status() != mf.Error.NoError or M.is_empty(): return None
        return M
    except Exception:
        return None

def to_manifold_raw(t):
    try:
        M = mf.Manifold(mf.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))
        if M.status() != mf.Error.NoError or M.is_empty(): return None
        return M
    except Exception:
        return None

def from_manifold(M):
    m = M.to_mesh()
    return np.asarray(m.vert_properties[:, :3], float), np.asarray(m.tri_verts, int)

def geom_vf(g):
    if isinstance(g, r.Mesh): return mesh_vf(g)
    if isinstance(g, r.Extrusion): return extrusion_vf(g)
    return None

def by_bodies(V, F):
    try:
        raw = trimesh.Trimesh(V, F, process=False)
        bodies = raw.split(only_watertight=False)
    except Exception:
        return None
    if len(bodies) < 2: return None
    out = None
    for b in bodies:
        M = to_manifold(to_trimesh(b.vertices, b.faces))
        if M is None: return None
        out = M if out is None else out + M
    return out

def load(path):
    """→ m（File3dm）、parts（物ごとの dict：i, layer, klass, tm（trimesh）, M（manifold か None）, bb）"""
    m = r.File3dm.Read(path)
    LN = {i: l.FullPath for i, l in enumerate(m.Layers)}
    parts = []
    for i, o in enumerate(m.Objects):
        ln = LN[o.Attributes.LayerIndex]; k = klass(ln)
        if k is None: continue
        vf = geom_vf(o.Geometry)
        if vf is None or len(vf[1]) == 0: continue
        try: t = to_trimesh(*vf)
        except Exception: continue
        if len(t.faces) == 0: continue
        M = to_manifold(t)
        if M is None:              # 削る段で作った網（manifold の書き出し）は頂点の番号のままなら閉じている
            raw = trimesh.Trimesh(*vf, process=False)
            M = to_manifold_raw(raw)
            if M is not None: t = raw
        if M is None:              # 接する箱を一つの物にまとめたもの（辺を 4 枚の面が共有）：箱ごとに閉じて足す
            M = by_bodies(*vf)
            if M is not None: t = to_trimesh(*from_manifold(M))
        repaired = False
        if M is None and isinstance(o.Geometry, r.Mesh):              # T 字の継ぎ目・厚みの無い片・重なった面を直して閉じる（10-25、Rhino で部材が透けて見えた）
            try:
                V2, F2, ok = repair_solid(*vf)
                if ok:
                    t2 = to_trimesh(V2, F2); M = to_manifold(t2)
                    if M is not None: t = t2; repaired = True
            except Exception:
                pass
        if M is None and k in 'FPDI':      # 小さな穴（面の抜け）を埋めて閉じる
            t3 = t.copy(); trimesh.repair.fill_holes(t3); trimesh.repair.fix_winding(t3)
            M = to_manifold(t3)
            if M is not None: t = t3; repaired = True
        inverted = False
        if M is not None and not repaired and isinstance(o.Geometry, r.Mesh):     # （押し出しは Rhino でそのまま閉じた立体）閉じているが面が内向き（Rhino の陰影で裏の色になる）、または元の網目は開いている
            try:
                t0 = trimesh.Trimesh(*vf, process=True)        # （箱ごとに閉じて読めた・小さな穴を埋めた物）→ 読めた立体で書き直す
                inverted = t0.volume < 0 or not t0.is_watertight
            except Exception: pass
        parts.append(dict(i=i, layer=ln, klass=k, name=o.Attributes.Name or '', tm=t, M=M, bb=t.bounds.copy(), repaired=repaired, inverted=inverted))
    return m, LN, parts

def mesh_from_vf(V, F):
    g = r.Mesh()
    for p in V: g.Vertices.Add(float(p[0]), float(p[1]), float(p[2]))
    for f in F: g.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
    g.Normals.ComputeNormals(); g.Compact()
    return g


COVER_LAYERS = ('10', '20', '10r', '20r', '10t', '20t', '50a', '28')     # 屋根・光の筋のガラス・越屋根の蓋
class RoofRaster:
    """屋根の覆いを下から真上へ格子で測る。Zbot＝いちばん下の面、Ztop＝いちばん上の面（覆いが無ければ nan）"""
    def __init__(self, parts, cell=250.0):
        cov = [p for p in parts if p['layer'].split('_')[0] in COVER_LAYERS]
        CM = trimesh.util.concatenate([p['tm'] for p in cov])
        b0, b1 = CM.bounds; self.cell = cell
        self.xs = np.arange(b0[0] - cell, b1[0] + 2 * cell, cell); self.ys = np.arange(b0[1] - cell, b1[1] + 2 * cell, cell)
        self.GX, self.GY = np.meshgrid(self.xs, self.ys, indexing='ij')
        orig = np.c_[self.GX.ravel(), self.GY.ravel(), np.full(self.GX.size, b0[2] - 5000)]
        ri = trimesh.ray.ray_triangle.RayMeshIntersector(CM)
        loc, rid, _ = ri.intersects_location(orig, np.tile([0, 0, 1.0], (len(orig), 1)), multiple_hits=True)
        Zb = np.full(self.GX.size, np.nan); Zt = np.full(self.GX.size, np.nan)
        if len(loc):
            o = np.lexsort((loc[:, 2], rid)); r_ = rid[o]; z = loc[o, 2]
            first = np.r_[True, r_[1:] != r_[:-1]]; last = np.r_[r_[1:] != r_[:-1], True]
            Zb[r_[first]] = z[first]; Zt[r_[last]] = z[last]
        self.Zbot = Zb.reshape(self.GX.shape); self.Ztop = Zt.reshape(self.GX.shape)
        self.hit = np.isfinite(self.Zbot)                    # 本当に覆いのある格子（covered_poly はこれで）
        # 覆いの縁と穴（光の筋の端・軒の先で格子の点が外れた所）を、まわり 2 ますの値で埋める（下の面は低いほう、上の面は高いほう）。
        # 格子の点のすき間から壁の端や木が屋根の上へ抜けないように（10-24、ユーザーの指摘：屋根から出る壁が残っていた）
        from scipy.ndimage import generic_filter
        for name, fn in (('Zbot', np.nanmin), ('Ztop', np.nanmax)):
            Z = getattr(self, name)
            F = generic_filter(np.where(np.isfinite(Z), Z, np.nan), lambda a: fn(a) if np.isfinite(a).any() else np.nan,
                               size=5, mode='constant', cval=np.nan)
            setattr(self, name, np.where(np.isfinite(Z), Z, F))

    def covered_poly(self):
        from shapely.geometry import box
        from shapely.ops import unary_union
        c = self.cell / 2
        return unary_union([box(self.GX[i, j] - c, self.GY[i, j] - c, self.GX[i, j] + c, self.GY[i, j] + c)
                            for i, j in zip(*np.where(self.hit))])

    def above(self, Zg, bb):
        """bb の上（2 ます広く）で、面 Zg より上の立体（manifold）。かからなければ None"""
        xs, ys, c = self.xs, self.ys, self.cell
        i0 = max(0, int((bb[0][0] - xs[0]) // c) - 2); i1 = min(len(xs) - 1, int((bb[1][0] - xs[0]) // c) + 3)
        j0 = max(0, int((bb[0][1] - ys[0]) // c) - 2); j1 = min(len(ys) - 1, int((bb[1][1] - ys[0]) // c) + 3)
        if i1 - i0 < 1 or j1 - j0 < 1: return None
        Zl = Zg[i0:i1 + 1, j0:j1 + 1]
        if not np.isfinite(Zl).any() or np.nanmin(Zl) >= bb[1][2]: return None
        top = max(bb[1][2], np.nanmax(Zl)) + 1000
        Zb = np.where(np.isfinite(Zl), Zl, top - 1)
        nx, ny = Zb.shape
        X = self.GX[i0:i1 + 1, j0:j1 + 1]; Y = self.GY[i0:i1 + 1, j0:j1 + 1]
        V = np.vstack([np.c_[X.ravel(), Y.ravel(), Zb.ravel()], np.c_[X.ravel(), Y.ravel(), np.full(X.size, top)]])
        n = nx * ny; F = []
        id_ = lambda i, j: i * ny + j
        for i in range(nx - 1):
            for j in range(ny - 1):
                a, b_, cc, d = id_(i, j), id_(i + 1, j), id_(i + 1, j + 1), id_(i, j + 1)
                F += [(a, cc, b_), (a, d, cc), (a + n, b_ + n, cc + n), (a + n, cc + n, d + n)]
        ring = [id_(i, 0) for i in range(nx)] + [id_(nx - 1, j) for j in range(1, ny)] + \
               [id_(i, ny - 1) for i in range(nx - 2, -1, -1)] + [id_(0, j) for j in range(ny - 2, 0, -1)]
        for k in range(len(ring)):
            a, b_ = ring[k], ring[(k + 1) % len(ring)]
            F += [(a, b_, b_ + n), (a, b_ + n, a + n)]
        t = trimesh.Trimesh(V, np.array(F), process=True)
        if t.volume < 0: t.invert()
        return to_manifold(t)


def seal_tjunctions(V, F, tol=0.5, rounds=8):
    """T 字の継ぎ目を埋めて閉じる（設計監修 10-25、ユーザー：Rhino で梁や柱の一部が透き通って見える）。
    隣り合う面の分け方が違う（片側の辺の途中に、もう片側の頂点がある）と、辺が共有されず網目が閉じない。
    Rhino ではそこが細い割れ目になって透けて見え、削る段（clip_parts）でも閉じていない物は削る側に入れない。
    開いた辺の上に乗っている開いた頂点で、その辺の面を分ける。最後に面の向きを外向きにそろえる。→ (V, F)"""
    from scipy.spatial import cKDTree
    V = np.asarray(V, float); F = np.asarray(F, np.int64)
    t = trimesh.Trimesh(V, F, process=True); V = np.asarray(t.vertices); F = np.asarray(t.faces)
    for _ in range(rounds):
        t = trimesh.Trimesh(V, F, process=False)
        bi = trimesh.grouping.group_rows(t.edges_sorted, require_count=1)
        if len(bi) == 0: break
        bv = np.unique(t.edges_sorted[bi]); kd = cKDTree(V[bv])
        fe = t.edges_face[bi]; ed = t.edges[bi]               # 面の向きのままの辺 a→b
        split = {}
        for (a, b), f in zip(ed, fe):
            A, B = V[a], V[b]; d = B - A; L2 = d @ d
            if L2 < 1e-6: continue
            cand = kd.query_ball_point((A + B) / 2, np.sqrt(L2) / 2 + tol)
            ps = []
            for j in cand:
                p = bv[j]
                if p in (a, b): continue
                s = (V[p] - A) @ d / L2
                if not (1e-4 < s < 1 - 1e-4): continue
                if np.linalg.norm(A + s * d - V[p]) > tol: continue
                ps.append((s, p))
            if ps: split.setdefault(int(f), []).append((int(a), int(b), [p for _, p in sorted(ps)]))
        if not split: break
        keep = np.ones(len(F), bool); add = []
        for f, edges in split.items():
            keep[f] = False
            # 面の辺を、分ける点を入れた多角形にして、扇形に三角形へ
            fa = list(F[f]); poly = []
            for k in range(3):
                a, b = fa[k], fa[(k + 1) % 3]; poly.append(a)
                for a2, b2, ps in edges:
                    if a2 == a and b2 == b: poly += ps
            # 分けていない頂点（元の三角形の角）のうち、分けた辺の向かいの角から扇にする
            c = next((x for x in fa if all(x not in (a2, b2) for a2, b2, _ in edges)), fa[0])
            i0 = poly.index(c); poly = poly[i0:] + poly[:i0]
            for k in range(1, len(poly) - 1): add.append((poly[0], poly[k], poly[k + 1]))
        F = np.vstack([F[keep], np.array(add, np.int64)]) if add else F[keep]
    t = trimesh.Trimesh(V, F, process=True)
    trimesh.repair.fix_winding(t)
    if t.is_watertight and t.volume < 0: t.invert()
    return np.asarray(t.vertices), np.asarray(t.faces)


def repair_solid(V, F):
    """閉じていない部材を閉じた立体に直す（設計監修 10-25）。→ (V, F, 閉じたか)
    1. 重なった面・潰れた面を除く  2. 体ごとに分け、厚みの無い体（押し出しの輪の偶奇で出る細い面など、体積 1 cm³ 未満）を捨てる
    3. 体ごとに T 字の継ぎ目を埋める（seal_tjunctions）  4. 面を外向きに"""
    t = trimesh.Trimesh(np.asarray(V, float), np.asarray(F, np.int64), process=True)
    t.update_faces(t.unique_faces()); t.update_faces(t.nondegenerate_faces()); t.remove_unreferenced_vertices()
    Vs, Fs, off, ok = [], [], 0, True
    for b in t.split(only_watertight=False):
        if b.is_watertight and abs(b.volume) < 1e3: continue
        if not b.is_watertight:
            V2, F2 = seal_tjunctions(b.vertices, b.faces); b = trimesh.Trimesh(V2, F2, process=False)
            if not b.is_watertight:
                if np.ptp(b.vertices, 0).min() < 1.0: continue          # 平らな片（体積の無い面）は捨てる
                ok = False
        if b.is_watertight and b.volume < 0: b.invert()
        Vs.append(np.asarray(b.vertices)); Fs.append(np.asarray(b.faces) + off); off += len(b.vertices)
    if not Vs: return np.asarray(V, float), np.asarray(F, np.int64), False
    return np.vstack(Vs), np.vstack(Fs), ok
