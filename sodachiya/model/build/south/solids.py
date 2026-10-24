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
    ('S', r'^(11a|11b|11c|22a|22b|22c|22d)_'),
    ('E', r'^(10|20|17|21|10t|20t|28|50a|16|19|89)_'),
    ('F', r'^(12|13|14|15|23)_'),
    ('P', r'^(18|24|27|38|48|49)_'),
    ('D', r'^(19c|19d)_'),
    ('I', r'^(25|35b|37|39|40|46|51|55|58|8[0-8])_'),
    ('X', r'^(21g|26|29|30|50b|50c|6[0-9]|7[0-9]|10p|20p)_'),
]
RANK = {'S': 0, 'E': 1, 'F': 2, 'D': 3, 'P': 4, 'I': 5, 'X': 6}     # 戸は間仕切りより上（戸の開口に壁が出ていれば壁を削る）
def klass(ln):
    for k, pat in CLASS_RE:
        if re.match(pat, ln): return k
    return None

A3 = lambda ps: np.array([[p.X, p.Y, p.Z] for p in ps], float)
def curve_pts(c, n=48):
    if isinstance(c, r.PolylineCurve): return [c.Point(i) for i in range(c.PointCount)]
    if isinstance(c, r.LineCurve): return [c.PointAtStart, c.PointAtEnd]
    d = c.Domain; return [c.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1)]

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
    return np.vstack(Vs), np.vstack(Fs)

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
        if M is None and k in 'FPDI':      # 小さな穴（面の抜け）を埋めて閉じる
            t3 = t.copy(); trimesh.repair.fill_holes(t3); trimesh.repair.fix_winding(t3)
            M = to_manifold(t3)
            if M is not None: t = t3
        parts.append(dict(i=i, layer=ln, klass=k, name=o.Attributes.Name or '', tm=t, M=M, bb=t.bounds.copy()))
    return m, LN, parts

def mesh_from_vf(V, F):
    g = r.Mesh()
    for p in V: g.Vertices.Add(float(p[0]), float(p[1]), float(p[2]))
    for f in F: g.Faces.AddFace(int(f[0]), int(f[1]), int(f[2]))
    g.Normals.ComputeNormals(); g.Compact()
    return g


COVER_LAYERS = ('10', '20', '10t', '20t', '50a', '28')     # 屋根・光の筋のガラス・越屋根の蓋
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
