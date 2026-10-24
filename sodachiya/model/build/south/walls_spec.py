"""間仕切りの構法（設計監修、10-23夜。ユーザーの決定：A＋B、必要な所に C）
使い方: python3 walls_spec.py IN.3dm OUT.3dm      （2階の間仕切りの次、壁の端をそろえるの前）

構法（決定事項「間仕切りの構法」）：
  A 架構の線に立つ壁：間柱 90＋両面にスギ板 t15＝厚さ 120。上端は 2 枚の梁の下端で止める
    （壁の上の 2 枚の梁のあいだは開いたまま。光の筋の光が落ち、架構が一続きに見える）。
  B それ以外の壁：同じ厚さ 120。上端は梁の下端か屋根の下面（垂木の下）まで（その位置で上にあるいちばん低い所）。
  C 見通しを残したい所は腰壁（h0.6〜1.1）。高さはそのまま、厚さだけ 120。

3dm の間仕切り（24・38）のうち、厚さ 85〜140 の壁の片について：
  - 厚さ：芯はそのまま、長い面を両側へ (120 − 今の厚さ)/2 ずつ出す。端の面（小口）は動かさない（戸の幅は変わらない）。
  - 高さ：床から 2.35 m 以上ある片（壁と、戸の上の片）は、上端を上の A・B の高さへ。腰壁・窓の下の片はそのまま。
    上にあるものは屋根（10・20）・梁（11b・22b）・桁（11c・22d）・2 階の床と床梁（23・22c）。
    架構の線かどうかは形で見る：壁の芯の真上が梁のあいだで抜けていて（芯の上が両脇の 140 の所（梁の中）より 150 以上高い）
    → A（両脇の梁の下端）。そうでなければ B（芯の真上）。
    片の上端は、長さに沿って 250 ごとに測った高さの下に収まるいちばん高い直線（屋根の勾配に沿う。途中に梁があれば梁の下）。
"""
import sys, re, numpy as np, rhino3dm as r
from shapely.geometry import Polygon, Point, LineString
from shapely.geometry.polygon import orient
from shapely.ops import unary_union, nearest_points
from scipy.optimize import linprog
import os as _os
sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from uv import uv

IN, OUT = sys.argv[1:3]
m = r.File3dm.Read(IN)
LN = {i: l.Name for i, l in enumerate(m.Layers)}
T_NEW = 120.0
WALL = re.compile(r'^(24|38)_')
ABOVE = re.compile(r'^(10|20|11b|11c|22b|22c|22d|23)_')

def verts(g):
    return np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])

def tris_of(g, V):
    out = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]
        out.append(V[[f[0], f[1], f[2]]])
        if f[2] != f[3]: out.append(V[[f[0], f[2], f[3]]])
    return out

def footprint(g, V):
    ps = []
    for T in tris_of(g, V):
        P = Polygon(T[:, :2])
        if P.area > 1: ps.append(P.buffer(0))
    u = unary_union(ps) if ps else Polygon()
    return u.buffer(0.5, join_style=2).buffer(-0.5, join_style=2) if not u.is_empty else u

def thickness(fp):
    A, L = fp.area, fp.length
    q = (L / 2) ** 2 - 4 * A
    return (L / 2 - np.sqrt(max(q, 0))) / 2

# ---------------------------------------------------------------- 上にある面（三角形、鉛直の面は除く）
import os
HERE = os.path.dirname(os.path.abspath(__file__))
src = open(os.path.join(HERE, 'draw100.py'), encoding='utf-8').read()
ns = {}
exec(compile(src[:src.index('# ================================================================ ここから描画')].replace('IN, OUTD = sys.argv[1], sys.argv[2]', 'IN, OUTD = "' + IN + '", "/tmp"'), 'd100', 'exec'), ns)
TR, TBM = [], []
BEAM = re.compile(r'^(11b|11c|22b|22c|22d)_')
for ob in ns['OBJ']:
    if ABOVE.match(ob['layer']):
        ts = [t for t in ob['T'] if abs(np.cross(t[1] - t[0], t[2] - t[0])[2]) > 1.0]
        TR += ts; TBM += [bool(BEAM.match(ob['layer']))] * len(ts)
TBM = np.array(TBM)
TR = np.array(TR)
TA, TB, TC = TR[:, 0], TR[:, 1], TR[:, 2]
TMIN = TR[:, :, :2].min(axis=1); TMAX = TR[:, :, :2].max(axis=1)
print('walls_spec: surfaces above', len(TR))

def hit(x, y, z0, nobeam=False, onlybeam=False):
    """(x, y) の真上で z0 より上のいちばん低い面の高さ（無ければ None）。nobeam：梁・桁を除く"""
    sel = (TMIN[:, 0] <= x) & (TMAX[:, 0] >= x) & (TMIN[:, 1] <= y) & (TMAX[:, 1] >= y)
    if nobeam: sel &= ~TBM
    if onlybeam: sel &= TBM
    if not sel.any(): return None
    a, b, c = TA[sel], TB[sel], TC[sel]
    v0 = b[:, :2] - a[:, :2]; v1 = c[:, :2] - a[:, :2]; v2 = np.array([x, y]) - a[:, :2]
    d = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
    ok = np.abs(d) > 1e-6
    s = np.where(ok, (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / np.where(ok, d, 1), -1)
    t = np.where(ok, (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / np.where(ok, d, 1), -1)
    inside = ok & (s >= -1e-6) & (t >= -1e-6) & (s + t <= 1 + 1e-6)
    if not inside.any(): return None
    z = a[:, 2] + s * (b[:, 2] - a[:, 2]) + t * (c[:, 2] - a[:, 2])
    z = z[inside]; z = z[z > z0]
    return float(z.min()) if len(z) else None

# ---------------------------------------------------------------- 厚さ：長い面を出す（小口は動かさない）
def thicken(V, fp, t):
    d = (T_NEW - t) / 2
    if abs(d) < 1: return V, 0
    P = np.array(orient(fp, 1).exterior.coords)[:-1]
    n = len(P)
    E = [(P[i], P[(i + 1) % n]) for i in range(n)]
    Ls = np.array([np.linalg.norm(b - a) for a, b in E])
    long_ = Ls > 1.6 * t
    nrm = [np.array([(b - a)[1], -(b - a)[0]]) / max(Ls[i], 1e-9) for i, (a, b) in enumerate(E)]   # CCW の外向き
    newP = []
    for i in range(n):
        ep, en = (i - 1) % n, i
        o1 = nrm[ep] * (d if long_[ep] else 0); o2 = nrm[en] * (d if long_[en] else 0)
        a1, b1 = E[ep][0] + o1, E[ep][1] + o1
        a2, b2 = E[en][0] + o2, E[en][1] + o2
        d1, d2 = b1 - a1, b2 - a2
        den = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(den) < 1e-6 * Ls[ep] * Ls[en]:
            newP.append(P[i] + (o1 if np.linalg.norm(o1) > 0 else o2))
        else:
            tt = ((a2 - a1)[0] * d2[1] - (a2 - a1)[1] * d2[0]) / den
            q = a1 + d1 * tt
            if np.linalg.norm(q - P[i]) > 4 * abs(d) + 5: q = P[i] + o1 + o2
            newP.append(q)
    newP = np.array(newP)
    V2 = V.copy(); moved = 0
    for k in range(len(V)):
        dd = np.linalg.norm(P - V[k, :2], axis=1)
        j = int(np.argmin(dd))
        if dd[j] < 2.0:
            V2[k, :2] = newP[j]; moved += 1
        else:                                   # 辺の途中の点：その辺の向きに
            best = None
            for i, (a, b) in enumerate(E):
                dist = LineString([a, b]).distance(Point(V[k, :2]))
                if best is None or dist < best[0]: best = (dist, i)
            if best and best[0] < 2.0 and long_[best[1]]:
                V2[k, :2] = V[k, :2] + nrm[best[1]] * d; moved += 1
    return V2, moved

# ---------------------------------------------------------------- 換気の道（ユーザー 10-23夜）
# 本館の梁間（2 枚組の梁と梁、屋根に囲まれた空間）は、東の縁側の段の蹴込みのガラリから床下を通って部屋に出た空気が屋根に沿って西へ上り、
# 西の壁の上の縦格子を抜けて西吹き抜け → 越屋根のすき間へ出る道。これを横切る壁（梁と平行に走る壁）は梁の下端で止める。
from uv import xy
from shapely.geometry import MultiPoint
def in_honkan(p):
    u_, v_ = uv(*p); return -0.5 <= u_ <= 57.5 and -0.1 <= v_ <= 12.5
def flow_dir(p):
    u_, v_ = uv(*p); d = xy(u_, v_ + 0.01) - xy(u_, v_); return d / np.linalg.norm(d)
def beam_bottom(p, z0):
    """本館の梁の下端の高さ（同じ v で、いちばん近い架構の線の 2 枚の梁）"""
    u_, v_ = uv(*p); uf = min(57.0, max(0.0, round(u_ / 3.0) * 3.0))
    hs = [hit(*xy(uf + k, v_), z0, onlybeam=True) for k in (0.135, -0.135)]
    hs = [h for h in hs if h is not None]
    return min(hs) if hs else None
# 壁の上にある格子・ガラス（48・49）：保育室などの西の壁の上の縦格子（裏にガラス、上部が開く）。その下の壁は高さを変えない
OVER = []
for ob in ns['OBJ']:
    if re.match(r'^(48|49)_', ob['layer']):
        P = ob['T'].reshape(-1, 3)
        if len(P) >= 3: OVER.append((MultiPoint([tuple(q) for q in P[:, :2]]).convex_hull.buffer(5), P[:, 2].min()))

# ---------------------------------------------------------------- 高さ：A・B
def top_line(fp, t, zfloor):
    """片の長さの軸に沿う上端の直線 (原点, 軸, z(s)=c0+c1*s) と種類"""
    mr = np.array(fp.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = mr[1] - mr[0], mr[2] - mr[1]
    ax = e1 if np.linalg.norm(e1) >= np.linalg.norm(e2) else e2
    Lw = np.linalg.norm(ax); ax = ax / Lw
    pr = np.array([-ax[1], ax[0]])
    c = np.array(fp.centroid.coords[0])
    core = fp.buffer(-(t / 2 - 5), join_style=2)
    if core.is_empty: core = fp
    s0 = -Lw / 2 + min(300, Lw / 4); s1 = Lw / 2 - min(300, Lw / 4)
    S = np.linspace(s0, s1, max(2, int((s1 - s0) / 250) + 1))
    hc, hl = [], []
    z0 = zfloor + 1500
    for s in S:
        p = c + ax * s
        q = nearest_points(core, Point(*p))[0]; p = np.array(q.coords[0])
        h0 = hit(p[0], p[1], z0)                 # 芯の真上（梁も）
        hr = hit(p[0], p[1], z0, nobeam=True)    # 芯の真上（屋根・床だけ）
        hs = [hit(*(p + pr * k), z0) for k in (140, -140)]
        if h0 is None: h0 = 1e9                   # 真上が開いている（光の筋）
        if hr is None: hr = h0
        if h0 >= 1e9 and not all(h is not None for h in hs): continue
        hA = max(hs) if all(h is not None for h in hs) and max(hs) < h0 - 150 else None    # 両脇とも低い＝梁のあいだの下
        hc.append((s, h0, hr, hA))
    if not hc: return None
    cross = in_honkan(c) and abs(float(np.dot(ax, flow_dir(c)))) < 0.94     # 梁と平行（流れを横切る）・斜めの壁
    if cross:
        pts = []
        for s_ in S:
            p = c + ax * s_
            q = nearest_points(core, Point(*p))[0]; p = np.array(q.coords[0])
            hb = beam_bottom(p, z0)
            if hb is not None: pts.append((s_, hb))
        if pts:
            A_ub = [[1, s_] for s_, h in pts]; b_ub = [h for s_, h in pts]
            res = linprog(c=[-2, 0], A_ub=A_ub, b_ub=b_ub, bounds=[(None, None), (-0.4, 0.4)])
            if res.success: return c, ax, res.x[0], res.x[1], 'X'
    nA = sum(1 for x in hc if x[3] is not None)
    nUnder = sum(1 for x in hc if x[1] < x[2] - 150)        # 芯の真上が梁（梁の下を沿って走る）
    if nA >= max(1, len(hc) // 2):
        kind = 'A'; pts = [(x[0], x[3]) for x in hc if x[3] is not None]
    elif nUnder >= max(1, (len(hc) + 1) // 2):
        kind = 'B'; pts = [(x[0], x[1]) for x in hc]                # 梁の下を走る壁は梁の下まで
    else:
        kind = 'B'; pts = [(x[0], x[2]) for x in hc]                # 屋根の下面（垂木の下）まで。横切る梁は欠き込む
    pts = [(a, b) for a, b in pts if b < 1e8]
    if not pts: return None
    # z(s) = c0 + c1*s が全点の下に収まり、両端の高さの和が最大
    A_ub = [[1, s] for s, h in pts]; b_ub = [h for s, h in pts]
    res = linprog(c=[-2, 0], A_ub=A_ub, b_ub=b_ub, bounds=[(None, None), (-0.4, 0.4)])
    if not res.success: return None
    return c, ax, res.x[0], res.x[1], kind

# ---------------------------------------------------------------- 閉じる部屋の天井（ユーザー 10-23夜）
# 静養室（換気は別系統：具合の悪い子の空気をほかへ流さない）と大人の便所 2 室（音とプライバシー）は、
# 梁の下端の高さに天井を張って閉じ、換気扇で外へ出す。天井の上の梁間は換気の道として開いたまま。
from shapely.ops import triangulate
CEIL_ROOMS = ('59_1F_静養室', '59_1F_多目的便所', '59_1F_便所（職員）')
L38 = [i for i, n in LN.items() if n.startswith('38_')][0]
CEIL_G = {}
for rn in CEIL_ROOMS:
    polys = []
    for ob in ns['OBJ']:
        if ob['layer'] == rn:
            for T in ob['T']:
                Pg = Polygon(T[:, :2])
                if Pg.area > 1: polys.append(Pg.buffer(0.5))
    if polys:
        G = unary_union(polys).buffer(-0.5)
        CEIL_G[rn] = max(getattr(G, 'geoms', [G]), key=lambda g: g.area).simplify(5)
CLOSED = unary_union(list(CEIL_G.values())) if CEIL_G else Polygon()

stats = {'thick': 0, 'A': 0, 'B': 0, 'X': 0, 'grille': 0, 'skip': 0, 'ceil': 0, 'westline': 0}
log = []
out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
for o in m.Objects:
    g = o.Geometry; ln = LN[o.Attributes.LayerIndex]
    if isinstance(g, r.Mesh) and WALL.match(ln) and len(g.Vertices) >= 8:
        V = verts(g); fp = footprint(g, V)
        if fp.geom_type == 'Polygon' and not fp.interiors and fp.area > 1e4:
            t = thickness(fp)
            if 85 <= t <= 140:
                V2, mv = thicken(V, fp, t)
                if mv: stats['thick'] += 1
                zmin, zmax = V[:, 2].min(), V[:, 2].max()
                zfloor = 3260 if zmin >= 3200 else 0
                fb = fp.buffer(80)
                gs = [hull.intersection(fb) for hull, zg in OVER if abs(zg - zmax) < 80 and hull.intersects(fb)]
                under_grille = bool(gs) and unary_union(gs).area > 0.3 * fp.area
                if under_grille: stats['grille'] += 1
                cu0 = uv(*fp.centroid.coords[0])
                west_line = zfloor == 0 and 1.3 <= cu0[1] <= 1.9 and 0 <= cu0[0] <= 57.5 and not fp.buffer(150).intersects(CLOSED)
                if west_line: stats['westline'] += 1        # 保育室などの西の壁の線（v1.6、「一本の線」）：下 2.4 は壁、上は縦格子か開いたまま（西吹き抜けへの換気の出口）。閉じる部屋の壁だけ天井まで
                if zmax - zfloor >= 2350 and not (zfloor == 0 and zmax >= 3100) and not under_grille and not west_line:     # 西館の 1 階で 2 階の床の下まである壁、格子の下の壁はそのまま
                    tl = top_line(fp, t, zfloor)
                    if tl:
                        c, ax, c0, c1, kind = tl
                        top = V[:, 2] > zmax - 1
                        for k in np.where(top)[0]:
                            s = float(np.dot(V2[k, :2] - c, ax))
                            V2[k, 2] = c0 + c1 * s
                        if (V2[top, 2] - V[:, 2].min()).min() > 200:
                            stats[kind] += 1; cu = uv(*fp.centroid.coords[0]); log.append((ln[:2], kind, round(zmax), round(V2[top, 2].min()), round(V2[top, 2].max()), round(cu[0], 2), round(cu[1], 2), round(fp.length / 2), ax.round(2).tolist()))
                        else:
                            V2[top, 2] = V[top, 2]; stats['skip'] += 1
                for i in range(len(V2)): g.Vertices.SetPoint3dAt(i, r.Point3d(*map(float, V2[i])))
                g.Normals.ComputeNormals()
    out.Objects.Add(g, o.Attributes)
for rn, G in CEIL_G.items():
    tris = [t for t in triangulate(G) if G.buffer(1).contains(t.centroid) and t.area > 10]
    M = r.Mesh(); TH_C = 30
    def zt(x, y):
        h = beam_bottom((x, y), 1500); return h if h is not None else 2400.0
    for t in tris:
        pts = list(t.exterior.coords)[:3]
        i0 = len(M.Vertices)
        for (x, y) in pts: M.Vertices.Add(float(x), float(y), float(zt(x, y)))
        for (x, y) in pts: M.Vertices.Add(float(x), float(y), float(zt(x, y) - TH_C))
        M.Faces.AddFace(i0, i0 + 1, i0 + 2); M.Faces.AddFace(i0 + 3, i0 + 5, i0 + 4)
    ring = list(G.exterior.coords)[:-1]
    for k in range(len(ring)):
        (x1, y1), (x2, y2) = ring[k], ring[(k + 1) % len(ring)]
        i0 = len(M.Vertices)
        M.Vertices.Add(x1, y1, zt(x1, y1)); M.Vertices.Add(x2, y2, zt(x2, y2))
        M.Vertices.Add(x2, y2, zt(x2, y2) - TH_C); M.Vertices.Add(x1, y1, zt(x1, y1) - TH_C)
        M.Faces.AddFace(i0, i0 + 1, i0 + 2, i0 + 3)
    M.Normals.ComputeNormals(); M.Compact()
    a = r.ObjectAttributes(); a.LayerIndex = L38; a.Name = '天井（' + rn.split('_')[-1] + '、閉じて換気扇で外へ。上の梁間は換気の道）'
    out.Objects.Add(M, a); stats['ceil'] += 1
out.Write(OUT, 8)
import collections
print('walls_spec:', stats, '→', OUT)
for k, v in sorted(collections.Counter((a, b, z) for a, b, z, *_ in log).items()): print('  ', k, v)
if _os.environ.get('WS_LOG'):
    for x in sorted(log, key=lambda x: (x[0], x[5])): print('   ', x)
