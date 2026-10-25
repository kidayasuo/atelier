"""Rhino 版（sodachiya.3dm）を作る：メッシュの版の物を、Rhino で閉じたソリッド（押し出し・ポリサーフェス）に置き換える。
使い方: python3 clean_wire.py IN.3dm OUT.3dm　　（段10。ソリッド係、10-25。前は更新係）
ユーザー（10-25）：全部閉じたソリッドに。曲線は曲線で。
- 一つの物の、辺でつながる三角形の組ごとに（solidify.py）：
  1. 押し出し（角柱。両端は斜めの面でもよい）にちょうどなる → Extrusion（輪郭の円は円弧、穴は内側の輪郭）。いちばん軽い。
  2. それ以外 → 閉じた Brep（同じ平面の三角形は一枚の面、細かく分けた曲面は円柱・球・円環（管）の面に戻す）。
  3. 自由な形（クスノキ・地形・網の鉢など、三角形ごとに面になってしまうもの）→ 閉じたメッシュのまま。
- 閉じていない面（部屋の色の板・道路・太陽光の板・網・地形）は厚みをつけて閉じる（SHEET）。
- 西館の屋根（20・20p・20t）のねじれた面の片は、線織面（ruled_roof.py）の六枚の組を辺でつないで閉じる
  （平らな面でできた片は上のふつうの道で）。一枚だけの片（薄い板・太陽光）は厚みをつける。
- 開いた輪郭の押し出し（外構の塀・柵の面）は輪郭に厚み FENCE_T をつけ、ふたの無い押し出しにはふたをする。
- 二つより多くの面が集まる辺（触れあう二つの立体）は、立体ごとに分ける。
- 新しいオブジェクトはアイソカーブを表示しない（WireDensity = -1）。同じ物から出た複数の立体はグループに。
"""
import sys, os, math, numpy as np, rhino3dm as r
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ruled_roof as RR
import solidify as SD
from shapely.geometry import LineString

IN, OUT = sys.argv[1], sys.argv[2]
WELD = 0.01                      # 同じ頂点とみなす距離 (mm)。0.5 だと近くの別の立体がつながってしまう（10-25）
# 閉じていない面の厚みのつけ方（レイヤーの番号 → (向き, mm)）。'down'：鉛直に下へ、'base'：いちばん低い所からさらに下の
# 平らな底まで、'both'：面の両側に半分ずつ。無いレイヤーは DEFAULT_SHEET（部屋の色の板は床から 10 mm 上にある → 床まで）
SHEET = {'03': ('down', 100.0), '10p': ('down', 20.0), '20p': ('down', 20.0), '83': ('both', 20.0),
         '90': ('base', 100.0), '78': ('base', 50.0)}
DEFAULT_SHEET = ('down', 10.0)
FENCE_T = 20.0                   # 開いた輪郭の押し出し（塀・柵・生垣の面）につける厚み (mm)

P3 = lambda p: r.Point3d(float(p[0]), float(p[1]), float(p[2]))


def mesh_arrays(g, weld):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
    key = {}; idx = []
    for p in np.round(V / weld).astype(np.int64):
        idx.append(key.setdefault(tuple(p), len(key)))
    W = np.zeros((len(key), 3))
    for i, j in enumerate(idx): W[j] = V[i]
    T = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]
        a, b, c, d = (idx[f[0]], idx[f[1]], idx[f[2]], idx[f[3]])
        if len({a, b, c}) == 3: T.append((a, b, c))
        if d != c and len({a, c, d}) == 3: T.append((a, c, d))
    return W, np.array(T, int).reshape(-1, 3)


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


def copy_attr(a0, grp=None):
    a = r.ObjectAttributes()
    a.LayerIndex = LMAP[a0.LayerIndex]
    for k in ('ColorSource', 'ObjectColor', 'MaterialSource', 'MaterialIndex', 'Name', 'Visible', 'PlotColorSource', 'PlotColor'):
        try: setattr(a, k, getattr(a0, k))
        except Exception: pass
    a.WireDensity = -1
    if grp is not None: a.AddToGroup(grp)
    return a


def thickness(W, T):
    """閉じた薄い片の厚み：体積 ÷ 上を向く面の面積"""
    a, b, c = W[T[:, 0]], W[T[:, 1]], W[T[:, 2]]
    N = np.cross(b - a, c - a); vol = abs(np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6)
    up = np.linalg.norm(N, axis=1)[N[:, 2] > 0.3 * np.linalg.norm(N, axis=1)].sum() / 2
    return vol / up if up > 0 else 10.0


def deviation(geo, W, T):
    """立体の辺の上の点が、もとのメッシュの面からいちばん離れる距離 (mm)"""
    import trimesh
    tm = trimesh.Trimesh(W, T, process=False); pts = []
    for x, k in geo:
        if not isinstance(x, (r.Brep, r.Extrusion)): continue
        b = x.ToBrep(False) if isinstance(x, r.Extrusion) else x
        for i in range(len(b.Edges)):
            e = b.Edges[i]; d = e.Domain
            for t in np.linspace(d.T0, d.T1, 5): p = e.PointAt(t); pts.append((p.X, p.Y, p.Z))
    if not pts: return 0.0
    _, dist, _ = trimesh.proximity.closest_point(tm, np.array(pts))
    return float(dist.max())


def close_extrusion(e):
    """ふたの無い押し出し → ふたをする。開いた輪郭（塀・柵の面）→ 輪郭に厚み FENCE_T。できなければ None"""
    p = e.Profile3d(0, 0.0)
    ps, pe = np.array([e.PathStart.X, e.PathStart.Y, e.PathStart.Z]), np.array([e.PathEnd.X, e.PathEnd.Y, e.PathEnd.Z])
    d = pe - ps; h = float(np.linalg.norm(d)); d = d / h
    if not p.IsClosed:
        X = np.cross(d, [1., 0, 0]) if abs(d[0]) < 0.9 else np.cross(d, [0, 1., 0]); X /= np.linalg.norm(X); Y = np.cross(d, X)
        nc = p.ToNurbsCurve(); dom = nc.Domain
        if nc.Degree == 1: pts = [nc.Points[i] for i in range(len(nc.Points))]; Q = [(q.X, q.Y, q.Z) for q in pts]
        else:
            n = max(32, 64 * nc.SpanCount); Q = [(lambda q: (q.X, q.Y, q.Z))(nc.PointAt(t)) for t in np.linspace(dom.T0, dom.T1, n + 1)]
        Q = np.array(Q); q2 = np.c_[(Q - ps) @ X, (Q - ps) @ Y]
        poly = LineString(q2).buffer(FENCE_T / 2, cap_style=2, join_style=2, mitre_limit=10)
        if poly.geom_type != 'Polygon': return None
        ring = np.array(poly.exterior.coords)[:-1]
        to3 = lambda q: ps + q[0] * X + q[1] * Y
        p = SD._profile(ring, to3, SD._arc_runs(ring))
    for k in range(2):
        if k: p.Reverse()
        x = r.Extrusion.Create(p, h, True)
        if x is None or not x.IsValid: continue
        dd = np.array([x.PathEnd.X - x.PathStart.X, x.PathEnd.Y - x.PathStart.Y, x.PathEnd.Z - x.PathStart.Z])
        if dd @ d > 0: return x
    return None


m = r.File3dm.Read(IN)
out = r.File3dm()
out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
# ---- レイヤーの親（Rhino で親を消すと子もまとめて消える）。子は名前の順。
import uuid, re
PARENTS = [
    ('A 屋根・越屋根', ('10', '10t', '10p', '20', '20t', '20p', '26', '28', '29', '30', '50a', '50b', '50c', '50d')),
    ('B 頭上（ファン・天蓋・物干し）', ('51', '58', '58b')),
    ('C 架構（柱・梁・桁）', ('11a', '11b', '11c', '22a', '22b', '22c', '22d')),
    ('D 壁・建具（外壁・間仕切り・ガラス戸）', ('16', '17', '18', '19', '19b', '19c', '19d', '19e', '21', '16e', '21g', '24', '27', '35', '35b', '35d', '66')),
    ('E 床・部屋の色', ('12', '13', '14', '15', '16b', '23', '25', '31', '32', '33', '34', '36', '41', '42', '43', '44', '45', '52', '53', '54', '56', '57', '59', '43b')),
    ('F しつらえ（家具・水まわり・格子）', ('37', '38', '39', '40', '46', '47', '48', '49', '55')),
    ('G 外（本体）', ('60', '62', '63', '64', '67')),
    ('H 外構（詳細設計）', ('70', '71', '72', '73', '74', '75', '76', '77', '78', '79')),
    ('I 敷地', ('00', '01', '02')),
    ('L 周辺の道路・建物（PLATEAU、data/context_plateau.json）', ('03', '04')),
    ('J 遊戯室の遊具・しつらえ（data/play.json）', ('80', '81', '82', '83', '84', '85', '86', '87', '88', '89')),
    ('K 園庭（data/garden.json、園庭のチャット）', ('90', '91', '92', '93', '94', '95', '96', '97', '98', '99')),
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
stat = {}
odd = {}                     # 閉じたソリッドにならなかった物（レイヤー → 数）
def count(kind, layer):
    stat[kind] = stat.get(kind, 0) + 1
    if kind in ('mesh', 'surface', 'open', 'dropped'): odd.setdefault(layer, {}).setdefault(kind, 0); odd[layer][kind] += 1


for oi, o in enumerate(m.Objects):
    g = o.Geometry; a0 = o.Attributes; lname = m.Layers[a0.LayerIndex].Name; lc = code(lname)
    if isinstance(g, r.Extrusion) and not g.IsSolid:
        x = close_extrusion(g)
        if x is not None:
            out.Objects.AddExtrusion(x, copy_attr(a0)); count('extrusion', lname); continue
    if not isinstance(g, r.Mesh):
        a1 = a0.Duplicate() if hasattr(a0, 'Duplicate') else a0; a1.LayerIndex = LMAP[a0.LayerIndex]
        out.Objects.Add(g, a1)
        if isinstance(g, (r.Brep, r.Extrusion)): count('kept' if g.IsSolid else 'open', lname)
        continue
    sheet = SHEET.get(lc, DEFAULT_SHEET)
    geo = []
    west_roof = any(t in lname for t in ('西館_屋根', '西館_光の筋'))
    if west_roof:
        W, T0 = mesh_arrays(g, 0.5)                      # ruled_roof.py はこの溶接で作った（10-24）
        for T in components(T0):
            # 平らな面でできた片（光の筋のガラス・ふさぐ板・平らな屋根の片）は、ふつうの道でちょうどの立体に。
            # 三角形ごとに面になる（ねじれた）片だけを線織面に
            g1 = SD.to_solids(W, T, sheet)
            if all(k == 'extrusion' or (isinstance(x, r.Brep) and len(x.Faces) <= 60) for x, k in g1):
                geo += g1; continue
            gs = RR.to_surfaces(W, T)                         # 箱で近づける narrow_box は使わない（ずれが 10 cm になる、10-25）
            if not gs:
                geo += g1; continue
            srfs = [x.Faces[0].UnderlyingSurface() for x in gs if isinstance(x, r.Brep)]
            if lc == '20p': th, cen = sheet[1], False         # 太陽光の板（屋根の面 +20）→ 屋根まで
            else: th, cen = thickness(W, T), True             # 薄い片は、測った厚みで面の両側に
            g2 = SD.solids_from_surfaces(srfs, th, cen)
            for x in gs:                                      # けらばの小さなメッシュ
                if isinstance(x, r.Mesh):
                    Wm, Tm = mesh_arrays(x, WELD); g2 += SD.to_solids(Wm, Tm, sheet)
            # 線織面がもとの面から 10 mm より離れる片は、平らな面の立体（ちょうど、ただし面の数が多い）に
            geo += g2 if lc == '20p' or deviation(g2, W, T) <= 10.0 else g1
    else:
        W, T0 = mesh_arrays(g, WELD)
        if len(T0) == 0: continue
        for T in components(T0):
            g1 = SD.to_solids(W, T, sheet)
            if not g1: count('dropped', lname)                # 太さの無い針は捨てる
            geo += g1
    grp = None
    if len(geo) > 1:
        grp = len(out.Groups); out.Groups.Add(r.Group())
    for x, kind in geo:
        at = copy_attr(a0, grp); at.SetUserString('src', str(oi))      # メッシュの版の何番目の物から（確かめ用、check_solids.py）
        if isinstance(x, r.Extrusion): out.Objects.AddExtrusion(x, at)
        elif isinstance(x, r.Brep): out.Objects.AddBrep(x, at)
        else: out.Objects.AddMesh(x, at)
        count(kind, lname)
print(stat)
print('閉じたソリッドでない物（メッシュは閉じている）:', {k: v for k, v in sorted(odd.items())})
out.Write(OUT, 8); print('written', OUT, len(out.Objects))
