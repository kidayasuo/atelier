"""メッシュを Rhino で見やすい形に置き換える（ワイヤフレームの放射状の筋をなくす）
使い方: python3 clean_wire.py IN.3dm OUT.3dm
- 平らな面ごとに三角形をまとめ直す（同じ平面で 1 mm 以内）
- 向かい合う 2 枚の平らな面＋それに垂直な側面だけでできた立体 → 押し出し（穴は内側の輪郭）
- それ以外（屋根の面、斜めの床など）→ 平面ごとのトリム平面（穴は切って分ける）、オブジェクトのグループにまとめる
- 新しいオブジェクトはアイソカーブを表示しない（WireDensity = -1）
"""
import sys, os, math, numpy as np, rhino3dm as r
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ruled_roof as RR
from shapely.geometry import Polygon, MultiPolygon, LineString
from shapely.ops import unary_union, split

IN, OUT = sys.argv[1], sys.argv[2]
KEEP_MESH = ('14_',)
# 西館の屋根（20・20p・20t）はねじれた面なので、平面に分けると三角の面が数千枚になり、縁の線が屋根の模様に見える（ユーザー、10-24昼）。
# メッシュのままでもワイヤフレームで黒い（ユーザー、10-24夕）→ 放射の線でつないだ線織面（NURBS、ruled_roof.py）にする（更新係）
# 弧に沿って曲がる細いルーバー（本館の 50c）は平面に分けると数千枚になるので、押し出しにならなければメッシュのまま   # 他のスクリプトがメッシュとして読む（infant200.py が南の縁側の輪郭を読む）
TOL_D = 1.0                      # 平面からのずれ (mm)
TOL_A = math.cos(math.radians(0.15))

A = lambda v: np.array([v.X, v.Y, v.Z], float)
P3 = lambda p: r.Point3d(float(p[0]), float(p[1]), float(p[2]))

def mesh_arrays(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
    key = {}; idx = []
    for p in np.round(V / 0.5).astype(np.int64):
        k = tuple(p); idx.append(key.setdefault(k, len(key)))
    W = np.zeros((len(key), 3))
    for i, j in enumerate(idx): W[j] = V[i]
    T = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]
        a, b, c, d = (idx[f[0]], idx[f[1]], idx[f[2]], idx[f[3]])
        T.append((a, b, c))
        if d != c: T.append((a, c, d))
    return W, np.array(T)

def basis(n):
    a = np.array([1., 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1., 0])
    x = np.cross(n, a); x /= np.linalg.norm(x); y = np.cross(n, x)
    return x, y

def clusters(W, T):
    """三角形を平面ごとにまとめる → [(n, d, [tri...])]"""
    a, b, c = W[T[:, 0]], W[T[:, 1]], W[T[:, 2]]
    N = np.cross(b - a, c - a); ar = np.linalg.norm(N, axis=1)
    out = []
    for i in np.argsort(-ar):
        if ar[i] < 1.0: continue
        n = N[i] / ar[i]
        for cl in out:
            if n @ cl[0] > TOL_A and all(abs(W[v] @ cl[0] - cl[1]) < TOL_D for v in T[i]):
                cl[2].append(i); break
        else:
            out.append([n, float(a[i] @ n), [i]])
    return out

def region(W, T, cl):
    n, d, tris = cl
    x, y = basis(n); o = n * d
    polys = [Polygon([((W[v] - o) @ x, (W[v] - o) @ y) for v in T[t]]) for t in tris]
    u = unary_union([p.buffer(0.05, join_style=2) for p in polys if p.area > 0]).buffer(-0.05, join_style=2)
    u = u.simplify(0.2)
    geoms = [g for g in getattr(u, 'geoms', [u]) if g.area > 10]
    return dict(n=n, d=d, x=x, y=y, o=o, geoms=geoms, area=sum(g.area for g in geoms))

def to3(R, pts2):
    return [R['o'] + R['x'] * p[0] + R['y'] * p[1] for p in pts2]

def ring_curve(R, ring):
    pts = to3(R, list(ring.coords))
    return r.PolylineCurve([P3(p) for p in pts])

def copy_attr(a0, grp=None):
    a = r.ObjectAttributes()
    a.LayerIndex = LMAP[a0.LayerIndex]
    for k in ('ColorSource', 'ObjectColor', 'MaterialSource', 'MaterialIndex', 'Name', 'Visible', 'PlotColorSource', 'PlotColor'):
        try: setattr(a, k, getattr(a0, k))
        except Exception: pass
    a.WireDensity = -1
    if grp is not None: a.AddToGroup(grp)
    return a

def as_prism(regs, bb):
    """向かい合う 2 枚の面＋側面がその向きに平行 → [(region, polygon, height)]
    側面の傾きはずれ 8 mm まで許す（屋根に沿う壁の天端、扇形に並ぶルーバーなど）"""
    for i in sorted(range(len(regs)), key=lambda i: -regs[i]['area']):
        n = regs[i]['n']
        opp = [j for j in range(len(regs)) if j != i and regs[j]['n'] @ n < -math.cos(math.radians(2))]
        if len(opp) != 1: continue
        j = opp[0]
        if abs(regs[i]['area'] - regs[j]['area']) > 1e-2 * regs[i]['area'] + 50: continue
        # 向かい合う面がわずかに開いている（扇形に切った端）ときは、そのずれが 3 mm 以内なら押し出しで近似
        b = regs[i]['geoms'][0].bounds; diam = math.hypot(b[2] - b[0], b[3] - b[1])
        ang = math.acos(min(1.0, -(regs[j]['n'] @ n)))
        if ang * diam > 3.0: continue
        cj = regs[j]['geoms'][0].centroid; pj = regs[j]['o'] + regs[j]['x'] * cj.x + regs[j]['y'] * cj.y
        h = abs((pj - regs[i]['o']) @ n)
        tol = min(0.12, max(2e-3, 8.0 / max(h, 1.0)))   # 側面のずれ 8 mm まで
        if any(abs(regs[k]['n'] @ n) > tol for k in range(len(regs)) if k not in (i, j)): continue
        dirv = n * np.sign((pj - regs[i]['o']) @ n)
        return [(regs[i], g, h, dirv) for g in regs[i]['geoms']]
    return None

def extrusion(R, g, h, dirv):
    """R の面の輪郭 g を dirv の向き（もう一方の面の側）へ h だけ押し出す"""
    outer = ring_curve(R, g.exterior)
    e = r.Extrusion.Create(outer, h, True)
    if e is None or not e.IsValid: return None
    if (A(e.PathEnd) - A(e.PathStart)) @ dirv < 0:
        e = r.Extrusion.Create(outer, -h, True)
        if e is None or not e.IsValid: return None
    if g.interiors:
        pp = e.GetProfilePlane(0.0); O, X, Y = A(pp.Origin), A(pp.XAxis), A(pp.YAxis)
        for hole in g.interiors:
            pts = [((p - O) @ X, (p - O) @ Y) for p in to3(R, list(hole.coords))]
            e.AddInnerProfile(r.PolylineCurve([r.Point3d(float(a), float(b), 0) for a, b in pts]))
    return e

def holefree(g):
    out, todo = [], [g]
    while todo:
        p = todo.pop()
        if not p.interiors: out.append(p); continue
        cx = p.interiors[0].centroid.x
        y0, y1 = p.bounds[1] - 1, p.bounds[3] + 1
        parts = split(p, LineString([(cx, y0), (cx, y1)]))
        todo += [q for q in parts.geoms if q.area > 1]
    return out

def trimmed(R, g):
    pl = r.Plane(P3(R['o']), r.Vector3d(*map(float, R['x'])), r.Vector3d(*map(float, R['y'])))
    res = []
    for q in holefree(g):
        b = r.Brep.CreateTrimmedPlane(pl, ring_curve(R, q.exterior))
        if b is not None and b.IsValid: res.append(b)
    return res

m = r.File3dm.Read(IN)
out = r.File3dm()
out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
# ---- レイヤーの親（Rhino で親を消すと子もまとめて消える）。子は名前の順。
import uuid, re
PARENTS = [
    ('A 屋根・越屋根', ('10', '10t', '10p', '20', '20t', '20p', '26', '28', '29', '30', '50a', '50b', '50c', '50d')),
    ('B 頭上（ファン・天蓋・物干し）', ('51', '58')),
    ('C 架構（柱・梁・桁）', ('11a', '11b', '11c', '22a', '22b', '22c', '22d')),
    ('D 壁・建具（外壁・間仕切り・ガラス戸）', ('16', '17', '18', '19', '19b', '19c', '19d', '21', '16e', '21g', '24', '27', '35', '35b', '35d', '66')),
    ('E 床・部屋の色', ('12', '13', '14', '15', '16b', '23', '25', '31', '32', '33', '34', '36', '41', '42', '43', '44', '45', '52', '53', '54', '56', '57', '59', '43b')),
    ('F しつらえ（家具・水まわり・格子）', ('37', '38', '39', '40', '46', '47', '48', '49', '55')),
    ('G 外（本体）', ('60', '62', '63', '64', '67')),
    ('H 外構（詳細設計）', ('70', '71', '72', '73', '74', '75', '76', '77', '78', '79')),
    ('I 敷地', ('00', '01', '02')),
    ('L 周辺の道路・建物（PLATEAU、data/context_plateau.json）', ('03', '04')),
    ('J 遊戯室の遊具・しつらえ（data/play.json）', ('80', '81', '82', '83', '84', '85', '86', '87', '88', '89')),
    ('K 園庭（data/garden.json、園庭のチャット）', ('90', '91', '92', '93', '94', '95', '96', '97', '98')),
]
def code(name):
    mm_ = re.match(r'^(\d+[a-z]?)_', name); return mm_.group(1) if mm_ else None
pid = {}
# 空の作業用レイヤーを0番に（ユーザー、10-24：開いたときの現在のレイヤーが屋根のグループにならないように。
# rhino3dmは現在のレイヤーを書けないが、Rhinoは指定の無いファイルを0番のレイヤーで開く）
_d = r.Layer(); _d.Name = '既定（作業用、空）'; _d.Id = uuid.uuid4(); _d.Color = (0, 0, 0, 255)
out.Layers.Add(_d)
for pname, codes in PARENTS:
    p = r.Layer(); p.Name = pname; p.Id = uuid.uuid4(); p.Color = (90, 90, 90, 255)
    out.Layers.Add(p); pid[pname] = p.Id
LMAP = {}
order = sorted(range(len(m.Layers)), key=lambda i: m.Layers[i].Name)
for i in order:
    l = m.Layers[i]; c = code(l.Name)
    for pname, codes in PARENTS:
        if c in codes: l.ParentLayerId = pid[pname]; break
    LMAP[i] = len(out.Layers); out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for gr in m.Groups: out.Groups.Add(gr)
stat = dict(prism=0, planes=0, keep=0, objs=0, ruled=0)
def components(T):
    """辺を共有する三角形どうしをつなぐ（頂点だけ接する箱は別の立体）"""
    par = list(range(len(T)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    E = {}
    for i, (a, b, c) in enumerate(T):
        for e in ((a, b), (b, c), (c, a)):
            k = (min(e), max(e))
            if k in E: par[f(i)] = f(E[k])
            else: E[k] = i
    lab = {}
    for i in range(len(T)): lab.setdefault(f(i), []).append(i)
    return [T[ix] for ix in lab.values()]

def process(W, T, allow_planes=True):
    """→ (種類, [ジオメトリ])"""
    if not allow_planes and len(T) > 3000:          # 細かい自由な形（クスノキ 約6万面など）は面を調べずにメッシュのまま（10-24）
        return 'keep', [submesh(W, T)]
    bb = np.r_[W[T.ravel()].min(0), W[T.ravel()].max(0)]
    regs = [R for R in (region(W, T, cl) for cl in clusters(W, T)) if R['geoms']]
    pr = as_prism(regs, bb)
    if pr:
        es = [extrusion(R, gg, h, dv) for R, gg, h, dv in pr]
        if all(e is not None for e in es): return 'prism', es
    bs = [b for R in regs for gg in R['geoms'] for b in trimmed(R, gg)] if allow_planes else []
    if bs: return 'planes', bs
    return 'keep', [submesh(W, T)]

def submesh(W, T):
    mm = r.Mesh(); ids = {}
    for v in np.unique(T.ravel()): ids[v] = len(ids); mm.Vertices.Add(*map(float, W[v]))
    for a, b, c in T: mm.Faces.AddFace(ids[a], ids[b], ids[c])
    mm.Normals.ComputeNormals(); mm.Compact(); return mm

for o in m.Objects:
    g = o.Geometry; a0 = o.Attributes
    if not isinstance(g, r.Mesh) or m.Layers[a0.LayerIndex].Name.startswith(KEEP_MESH):
        a1 = a0.Duplicate() if hasattr(a0, 'Duplicate') else a0; a1.LayerIndex = LMAP[a0.LayerIndex]
        out.Objects.Add(g, a1); stat['keep'] += 1; continue
    W, T0 = mesh_arrays(g)
    if len(T0) == 0: continue
    geo = []
    west_roof = any(t in m.Layers[a0.LayerIndex].Name for t in ('西館_屋根', '西館_光の筋'))
    for T in components(T0):
        if west_roof:                     # 10-24：線織面（ruled_roof.py）→ 平らな面が少なければ平面 → メッシュ
            gs = RR.to_surfaces(W, T) or RR.narrow_box(W, T)
            if gs: stat['ruled'] += 1; geo += gs; continue
            k, gs = process(W, T, True)
            if k != 'planes' or len(gs) <= 40: stat[k] += 1; geo += gs; continue
            stat['keep'] += 1; geo += [submesh(W, T)]; continue
        k, gs = process(W, T, not any(t in m.Layers[a0.LayerIndex].Name for t in ('ルーバー', 'ネット', '切り株', '地形', '林', '周辺_道路', '本館_桁', '西館_屋根', '西館_光の筋'))); stat[k] += 1; geo += gs
    grp = None
    if len(geo) > 1:
        grp = len(out.Groups); out.Groups.Add(r.Group())
    for x in geo:
        at = copy_attr(a0, grp)
        if isinstance(x, r.Extrusion): out.Objects.AddExtrusion(x, at)
        elif isinstance(x, r.Brep): out.Objects.AddBrep(x, at)
        else: out.Objects.AddMesh(x, at)
        stat['objs'] += 1
print(stat)
out.Write(OUT, 8); print('written', OUT, len(out.Objects))
