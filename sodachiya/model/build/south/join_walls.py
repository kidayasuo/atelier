"""壁の端をそろえる（設計監修、10-23）
使い方: python3 join_walls.py IN.3dm OUT.3dm

間仕切り（24・38・18）の端が、相手の壁の芯で止まっていると、L字の角の外側に壁の厚さの半分の欠けが残る
（両方の壁が互いの芯で止まる）。平面図で「角が二つの長方形の単なるぶつかり合い」に見える原因。
図の側で閉じても、外側の角の欠けは埋まらない（膨らませて縮めても欠けは同じ形で残る）。そこで 3dm の側で端を延ばす。

- L字（相手の壁もそこで終わる）：相手の壁の外の面まで延ばす → 角が一つの長方形の角になる。
- T字（相手の壁の途中に当たる）：相手の壁の芯まで延ばす（相手の中に隠れる。切り口が一つにまとまる）。
- 延ばすだけで縮めない。延ばす量は 250 まで。開口（戸・窓のすき間）は相手から離れているので触らない。
- 動かすのは箱の形の間仕切りだけ（外壁 17・21 は相手として使うが、形は変えない）。
"""
import sys, re, numpy as np, rhino3dm as r
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

IN, OUT = sys.argv[1:3]
m = r.File3dm.Read(IN)
LN = {i: l.Name for i, l in enumerate(m.Layers)}
MOVE = re.compile(r'^(24|38|18)_')
ANY = re.compile(r'^(17|21|24|38|18)_')
TOL = 120        # 端と相手の壁のすき間（mm）
MAXEXT = 250     # 延ばす量の上限（mm）

def verts(g):
    return np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])

def footprint(V, g):
    """メッシュを上から見た形（三角形の和）"""
    from shapely.ops import unary_union as uu
    ps = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]
        for tri in ((f[0], f[1], f[2]), (f[0], f[2], f[3])) if f[2] != f[3] else ((f[0], f[1], f[2]),):
            P = Polygon(V[list(tri), :2])
            if P.area > 1: ps.append(P.buffer(0))
    u = uu(ps) if ps else Polygon()
    return u.buffer(0.5, join_style=2).buffer(-0.5, join_style=2) if not u.is_empty else u

def strip_ends(fp, V):
    """帯の形の端：長さが厚さほどの辺で、両隣が長い辺のもの。(端の中心, 外向き, 動かす頂点, 厚さ)"""
    if fp.geom_type != 'Polygon' or len(fp.interiors): return []
    P = np.array(fp.exterior.coords)[:-1]
    # 一直線に並ぶ頂点を落とす
    keep = []
    n = len(P)
    for i in range(n):
        a, b, c = P[i - 1], P[i], P[(i + 1) % n]
        if abs((b - a)[0] * (c - b)[1] - (b - a)[1] * (c - b)[0]) > 1e-3 * np.linalg.norm(b - a) * np.linalg.norm(c - b) + 1e-6: keep.append(b)
    P = np.array(keep); n = len(P)
    if n < 4: return []
    E = [(P[i], P[(i + 1) % n]) for i in range(n)]
    Ls = np.array([np.linalg.norm(b - a) for a, b in E])
    th = 2 * fp.area / max(fp.length, 1)            # 帯の厚さの目安（細長いほど正確）
    th = max(th, 1.0)
    out = []
    for i, (a, b) in enumerate(E):
        if not (0.5 * th <= Ls[i] <= 2.2 * th and Ls[i] <= 400): continue
        if Ls[i - 1] < 1.4 * Ls[i] or Ls[(i + 1) % n] < 1.4 * Ls[i]: continue
        t = (b - a) / Ls[i]
        d = np.array([t[1], -t[0]])
        c = (a + b) / 2
        if fp.contains(Point(*(c + d * 2))): d = -d
        # 両隣の辺が端の辺にほぼ直角（帯の向き）であること
        pa, pb = E[i - 1][0], E[(i + 1) % n][1]
        if abs(np.dot((a - pa) / max(np.linalg.norm(a - pa), 1e-9), t)) > 0.35: continue
        sel = (np.linalg.norm(V[:, :2] - a, axis=1) < 1.5) | (np.linalg.norm(V[:, :2] - b, axis=1) < 1.5)
        selA = np.linalg.norm(V[:, :2] - a, axis=1) < 1.5; selB = np.linalg.norm(V[:, :2] - b, axis=1) < 1.5
        out.append(dict(c=c, d=d, sel=sel, th=Ls[i], a=a, b=b, pa=pa, pb=pb, selA=selA, selB=selB))
    return out

walls = []
for idx, o in enumerate(m.Objects):
    g = o.Geometry
    if not isinstance(g, r.Mesh) or not ANY.match(LN[o.Attributes.LayerIndex]): continue
    V = verts(g)
    if len(V) < 4: continue
    fp = footprint(V, g)
    if fp.is_empty or fp.area < 1: continue
    w = dict(idx=idx, ln=LN[o.Attributes.LayerIndex], V=V, fp=fp, z0=V[:, 2].min(), z1=V[:, 2].max(),
             move=bool(MOVE.match(LN[o.Attributes.LayerIndex])))
    w['ends'] = strip_ends(fp, V)
    walls.append(w)

def zover(a, b):
    return min(a['z1'], b['z1']) - max(a['z0'], b['z0'])

def ends_near(b, p, rad):
    return any(np.linalg.norm(e['c'] - p) <= rad for e in b['ends'])

def isect(p1, p2, q1, q2):
    """直線 p1p2 と q1q2 の交点"""
    d1, d2 = p2 - p1, q2 - q1
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9: return None
    t = ((q1 - p1)[0] * d2[1] - (q1 - p1)[1] * d2[0]) / den
    return p1 + d1 * t

def mitre(ea, eb):
    """端どうしで出会う 2 本の帯の留め：ea の 2 つの角の新しい位置（外の面どうし・内の面どうしの交点）"""
    A = [(ea['pa'], ea['a']), (ea['b'], ea['pb'])]          # ea の両側の面の線（a の側・b の側）
    B = [(eb['pa'], eb['a']), (eb['b'], eb['pb'])]
    farA = ea['c'] - ea['d'] * 1000; farB = eb['c'] - eb['d'] * 1000
    for pair in ((0, 1), (1, 0)):
        P = [isect(*A[0], *B[pair[0]]), isect(*A[1], *B[pair[1]])]
        if any(q is None for q in P): continue
        # 留めの線の両側に、ea の本体と eb の本体が分かれること
        n = np.array([-(P[1] - P[0])[1], (P[1] - P[0])[0]])
        sa, sb = np.dot(farA - P[0], n), np.dot(farB - P[0], n)
        if sa * sb >= 0: continue
        if max(np.linalg.norm(P[0] - ea['a']), np.linalg.norm(P[1] - ea['b'])) > MAXEXT + 150: continue
        return P
    return None

moves = {}       # idx -> list of (sel, vec)
log = []
for a in walls:
    if not a['move']: continue
    for e in a['ends']:
        c, d = e['c'], e['d']
        # 1) 端どうしで出会う（L・Y の折れ）：留め
        done = False
        for b in walls:
            if b is a or not b['move'] or zover(a, b) < 300: continue     # 留めは両方を動かせるときだけ（外壁は形を変えない）
            for eb in b['ends']:
                if np.linalg.norm(eb['c'] - c) > (e['th'] + eb['th']) * 0.9: continue
                cosang = abs(np.dot(e['d'], eb['d']))
                if cosang > 0.985: continue                    # 一直線につながる（突きつけ）は対象外
                P = mitre(e, eb)
                if P is None: continue
                moves.setdefault(a['idx'], []).append(('abs', e['selA'], P[0]))
                moves.setdefault(a['idx'], []).append(('abs', e['selB'], P[1]))
                log.append((a['ln'][:2], 'M', 0)); done = True; break
            if done: break
        if done: continue
        # 2) 相手の壁の側面に当たる：T字は芯まで、相手の端に近い L 字は外の面まで延ばす
        best = None
        for b in walls:
            if b is a or zover(a, b) < 300: continue
            if b['fp'].distance(Point(*c)) > TOL: continue
            ray = LineString([c - d * 400, c + d * 600])
            x = ray.intersection(b['fp'].buffer(2, join_style=2))     # 端が相手の面の線の上にあるとき（芯で止まる角）も拾う
            if x.is_empty: continue
            segs = [x] if x.geom_type == 'LineString' else [g for g in getattr(x, 'geoms', []) if g.geom_type == 'LineString']
            for sg in segs:
                ts = sorted(((np.array(q) - c) @ d) for q in sg.coords)
                t_in, t_out = ts[0], ts[-1]
                if t_out <= 0 or t_in > TOL: continue
                if t_out - t_in > 450: continue             # 相手の壁に沿って並ぶ（同じ向き）は対象外
                mid = (t_in + t_out) / 2
                L_corner = ends_near(b, c + d * mid, (t_out - t_in) * 0.7 + e['th'] * 0.7)
                target = (t_out - 2) if L_corner else mid
                if target <= 0.5 or target > MAXEXT: continue
                if best is None or target > best[0]: best = (target, L_corner, b['ln'])
        if best:
            moves.setdefault(a['idx'], []).append(('rel', e['sel'], np.r_[d * best[0], 0.0]))
            log.append((a['ln'][:2], 'L' if best[1] else 'T', round(best[0])))

out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
n = 0
for idx, o in enumerate(m.Objects):
    g = o.Geometry
    if idx in moves:
        V = verts(g)
        for kind_, sel, vec in moves[idx]:
            if kind_ == 'rel': V[sel] += vec
            else: V[sel, 0] = vec[0]; V[sel, 1] = vec[1]
        for i in range(len(V)): g.Vertices.SetPoint3dAt(i, r.Point3d(float(V[i, 0]), float(V[i, 1]), float(V[i, 2])))
        g.Normals.ComputeNormals(); n += 1
    out.Objects.Add(g, o.Attributes)
out.Write(OUT, 8)
import collections
print('join_walls: ends', len(log), 'walls', n, dict(collections.Counter((k, t) for k, t, _ in log)), '→', OUT)
