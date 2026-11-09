"""西館の屋根（20・20p・20t）を Rhino 版で NURBS の面にする（更新係、10-24。ユーザー：西の屋根はワイヤフレームでも黒い、本館の屋根のように）。
西館の屋根の面は、架構の向き（u 一定の放射の線）にまっすぐ下る（roofw.py）。だから屋根の一片は、
u の向きに滑らかな 2 本の縁の線（西の縁・東の縁）を、放射の線でつないだ線織面になる：
  S(s, t) = (1 − t)·C西(s) + t·C東(s)   （t の向きは 1 次、s の向きは 3 次の B スプライン）
上の面と下の面（屋根の面からの高さ dz が二つの値）、西と東の小口、南北の端の 4 枚で一片を閉じる。
u ごとに片の幅が一つの区間にならないもの、dz が二つの値に分かれないもの、合わない（誤差 15 mm 超）ものはメッシュのまま返す。"""
import math, pickle, os, sys
import numpy as np
import rhino3dm as r
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely import affinity as shp_aff

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from uv import uv, xy
import roofw

_RF = None
def roof_f():
    global _RF
    if _RF is None:
        for p in (os.path.join(HERE, '..', '..', '..', 'data', 'wnew.pkl'), '/tmp/claude-0/t/exact/wnew.pkl'):
            if os.path.isfile(p):
                D = pickle.load(open(p, 'rb')); break
        _RF = roofw.make(D['WN'])['roof_f']
    return _RF

TOL = 15.0     # mm

def _basis(knots, deg, s):
    """クランプした B スプラインの基底（s は配列）→ (len(s), n)"""
    n = len(knots) - deg - 1
    N = np.zeros((len(s), n))
    for j, x in enumerate(s):
        if x >= knots[-1]: N[j, -1] = 1.0; continue
        b = np.array([1.0 if knots[i] <= x < knots[i + 1] else 0.0 for i in range(len(knots) - 1)])
        for d in range(1, deg + 1):
            nb = np.zeros(len(knots) - d - 1)
            for i in range(len(nb)):
                a = 0.0
                if knots[i + d] > knots[i]: a += (x - knots[i]) / (knots[i + d] - knots[i]) * b[i]
                if knots[i + d + 1] > knots[i + 1]: a += (knots[i + d + 1] - x) / (knots[i + d + 1] - knots[i + 1]) * b[i + 1]
                nb[i] = a
            b = nb
        N[j] = b[:n]
    return N

def _fit(s, P, ncv):
    """点列 P（len(s), 3）に、制御点 ncv の 3 次 B スプライン（両端は点を通る）を最小二乗で"""
    deg = min(3, ncv - 1)
    inner = list(np.linspace(0, 1, ncv - deg + 1)[1:-1])
    knots = [0.0] * (deg + 1) + inner + [1.0] * (deg + 1)
    N = _basis(knots, deg, s)
    C, *_ = np.linalg.lstsq(N, P, rcond=None)
    err = np.abs(N @ C - P).max()
    return deg, knots, C, err

def _surface(deg, knots, rows):
    """rows：[C0, C1]（t=0, 1 の制御点の列）→ NurbsSurface（u：s の向き deg、v：t の向き 1 次）"""
    n = len(rows[0])
    ns = r.NurbsSurface.Create(3, False, deg + 1, 2, n, 2)
    for i in range(n):
        for j in range(2):
            ns.Points[i, j] = r.Point4d(*map(float, rows[j][i]), 1.0)
    kk = knots[1:-1]                       # Rhino は端の余分な節点を持たない
    for i, k in enumerate(kk): ns.KnotsU[i] = float(k)
    ns.KnotsV[0] = 0.0; ns.KnotsV[1] = 1.0
    return ns

WHY = []
def _levels(dz):
    """dz の値の一つか二つ（上と下）。外れ値（2%まで）は無視"""
    ds = np.sort(dz); n = len(ds)
    best = None
    for k in range(-1, n - 1):
        groups = [ds] if k < 0 else [ds[:k + 1], ds[k + 1:]]
        meds = [float(np.median(g)) for g in groups]
        ok = sum(int((np.abs(g - md) <= TOL).sum()) for g, md in zip(groups, meds))
        if ok >= 0.98 * n and (best is None or len(meds) < len(best)):
            best = meds
        if k < 0 and best: break
    if best is None:
        k = int(np.argmax(np.diff(ds))); best = [float(np.median(ds[:k + 1])), float(np.median(ds[k + 1:]))]
        if sum(int((np.abs(ds - b) <= TOL).sum()) for b in best) < 0.98 * n: return None
    return best

def _intervals(F, u):
    try:
        x_ = LineString([(u, F.bounds[1] - 1), (u, F.bounds[3] + 1)]).intersection(F)
    except Exception:
        return [None, None, None]
    _ = LineString([(u, F.bounds[1] - 1), (u, F.bounds[3] + 1)]).intersection(F)
    segs = [g for g in getattr(x_, 'geoms', [x_]) if g.geom_type == 'LineString' and g.length > 1e-5]
    return sorted((min(c[1] for c in g.coords), max(c[1] for c in g.coords)) for g in segs)

def _edge(F, ua, ub, k):
    """ua では区間が k 個、ub では違う → 境の u（0.1 mm まで）"""
    for _ in range(20):
        um = 0.5 * (ua + ub)
        if len(_intervals(F, um)) == k: ua = um
        else: ub = um
    return ua

U_IN = (21.002, 50.998)       # roof_f が放射の線で決まる範囲（南北の妻の外のけらばは別の形）

def _mesh_heights(W, T):
    """上を向く三角形と下を向く三角形から、下の面と上の面の高さ（片方だけなら一つ）"""
    N = np.cross(W[T[:, 1]] - W[T[:, 0]], W[T[:, 2]] - W[T[:, 0]])
    nz = N[:, 2] / np.maximum(np.linalg.norm(N, axis=1), 1e-9)
    out = []
    for sel in (nz < -0.3, nz > 0.3):
        if sel.sum() == 0: continue
        f = _mesh_height(W, T[sel])
        if f is None: return None
        out.append(f)
    return out or None

def _mesh_height(W, T):
    """一枚の面（重なりの無いメッシュ）の高さ z(x, y)。重なっていれば None"""
    from shapely.strtree import STRtree
    tris = [Polygon(W[t, :2]) for t in T]
    ok = [i for i, p in enumerate(tris) if p.area > 1.0]
    if not ok: return None
    if sum(tris[i].area for i in ok) > 1.02 * unary_union([tris[i] for i in ok]).area: return None
    tree = STRtree([tris[i] for i in ok])
    from shapely.geometry import Point
    def f(x, y):
        pt = Point(x, y)
        cand = tree.query(pt.buffer(5))
        best = None
        for c in cand:
            t = T[ok[c]]; A, B, C = W[t]
            M = np.array([[B[0] - A[0], C[0] - A[0]], [B[1] - A[1], C[1] - A[1]]])
            try: l1, l2 = np.linalg.solve(M, [x - A[0], y - A[1]])
            except np.linalg.LinAlgError: continue
            d = max(0.0, -l1, -l2, l1 + l2 - 1)
            if best is None or d < best[0]: best = (d, A[2] + l1 * (B[2] - A[2]) + l2 * (C[2] - A[2]))
        return best[1] if best else float('nan')
    return f

def mesh_of(W, T):
    mm = r.Mesh(); ids = {}
    for v in np.unique(T.ravel()): ids[v] = len(ids); mm.Vertices.Add(*map(float, W[v]))
    for a, b, c in T: mm.Faces.AddFace(int(ids[a]), int(ids[b]), int(ids[c]))
    mm.Normals.ComputeNormals(); mm.Compact(); return mm

def to_surfaces(W, T):
    """W：頂点（mm）、T：三角形の添字（一つのつながった片）→ [Brep（とけらばの小さなメッシュ）] か None（メッシュのままにする）。
    足もと（uv）を、u の向きに区間の数が変わる所で分け、区間ごとに一枚の線織面の片にする（光の筋の穴・すき間をよける）。
    南北の妻の外（けらば）は roof_f の形でないので、その三角形だけメッシュで残す"""
    rf = roof_f()
    idx = np.unique(T.ravel())
    Wuv = {i: uv(*W[i, :2]) for i in idx}
    cu = np.array([np.mean([Wuv[a][0], Wuv[b][0], Wuv[c][0]]) for a, b, c in T])
    inside = (cu > U_IN[0]) & (cu < U_IN[1])
    Tin, Tout = T[inside], T[~inside]
    if len(Tin) == 0: return WHY.append('outside') or None
    ii = np.unique(Tin.ravel()); P = W[ii]
    uu = np.array([Wuv[i][0] for i in ii]); keep = (uu > U_IN[0]) & (uu < U_IN[1])
    if keep.sum() < 3: return WHY.append('outside') or None
    dz = P[keep, 2] - np.array([rf(x, y) for x, y in P[keep, :2]])
    levels = _levels(dz)
    if levels is None:
        # roof_f と合わない片（北西の角の太陽光・角の軒の縁など）：上の面と下の面の高さをメッシュから読む
        H = _mesh_heights(W, Tin)
        if H is None: return WHY.append('dz') or None
    else:
        H = [(lambda x, y, lv=lv: rf(x, y) + lv) for lv in levels]
    polys = [Polygon([Wuv[a], Wuv[b], Wuv[c]]) for a, b, c in Tin]
    polys = [p.buffer(0) for p in polys if p.area > 1e-9]
    if not polys: return WHY.append('flat') or None
    FF = unary_union([p.buffer(1e-3, join_style=2) for p in polys]).buffer(-1e-3, join_style=2)
    try: FF = FF.buffer(0).intersection(box(U_IN[0], -100, U_IN[1], 100))
    except Exception: return WHY.append('invalid') or None
    out = []
    for F in getattr(FF, 'geoms', [FF]):
        if F.geom_type != 'Polygon' or F.area < 1e-4: continue
        F = F.buffer(0)
        if F.geom_type != 'Polygon': return WHY.append('invalid') or None
        res = _part(F, None, H)
        if res is None: return None
        out += res
    if not out: return WHY.append('empty') or None
    if len(Tout):
        fr = _free(W, Tout)
        out += fr if fr else [mesh_of(W, Tout)]
    return out

def _free(W, T):
    """けらばの片：高さはメッシュから（下の面と上の面）、足もとは同じ分け方"""
    H = _mesh_heights(W, T)
    if H is None: return None
    polys = [Polygon([uv(*W[a, :2]), uv(*W[b, :2]), uv(*W[c, :2])]) for a, b, c in T]
    polys = [p.buffer(0) for p in polys if p.area > 1e-9]
    if not polys: return None
    FF = unary_union([p.buffer(1e-3, join_style=2) for p in polys]).buffer(-1e-3, join_style=2)
    out = []
    for F in getattr(FF, 'geoms', [FF]):
        if F.geom_type != 'Polygon' or F.area < 1e-4: continue
        F = F.buffer(0)
        if F.geom_type != 'Polygon': return None
        res = _part(F, None, H)
        if res is None: return None
        out += res
    return out or None

SWAP = [False]
def _part(F, rf, levels):
    u0, u1 = F.bounds[0], F.bounds[2]
    if u1 - u0 < 0.15:
        # 放射の線に沿う細い片（光の筋の立ち上がり・ふさぐ板）：向きを入れ替えて、v の向きに縁の線を取る
        if F.bounds[3] - F.bounds[1] < 0.15: return WHY.append('small') or None
        SWAP[0] = True
        try: return _part0(shp_aff.affine_transform(F, [0, 1, 1, 0, 0, 0]), rf, levels)
        finally: SWAP[0] = False
    return _part0(F, rf, levels)

def _xy(a, b):
    return xy(b, a) if SWAP[0] else xy(a, b)

def _part0(F, rf, levels):
    u0, u1 = F.bounds[0], F.bounds[2]
    us = np.r_[np.arange(u0 + 1e-5, u1, 0.01), u1 - 1e-5]
    IV = [_intervals(F, u) for u in us]
    cnt = [len(x) for x in IV]
    def jump(k):                                   # 区間の端が急に跳ぶ（足もとの段）
        return cnt[k] == cnt[k - 1] and any(abs(p[0] - q[0]) > 0.03 or abs(p[1] - q[1]) > 0.03 for p, q in zip(IV[k], IV[k - 1]))
    runs, a = [], 0
    for k in range(1, len(us) + 1):
        if k == len(us) or cnt[k] != cnt[a] or jump(k):
            runs.append((a, k - 1)); a = k
    out = []
    for ka, kb in runs:
        n = cnt[ka]
        if n == 0: continue
        ua = us[ka] if ka == 0 or cnt[ka - 1] == n else _edge(F, us[ka], us[ka - 1], n)
        ub = us[kb] if kb == len(us) - 1 or cnt[kb + 1] == n else _edge(F, us[kb], us[kb + 1], n)
        if ub - ua < 0.002: continue
        for i in range(n):
            res = _patch(F, rf, ua, ub, levels, i, n)
            if res is None: return None
            out += res
    return out or (WHY.append('empty') or None)

def _patch(F, rf, ua, ub, levels, i_, n_):
    n = max(8, int((ub - ua) / 0.05))
    us0 = np.linspace(ua, ub, n + 1)
    lo_v, hi_v, us = [], [], []
    for u in us0:
        x = _intervals(F, u)
        if len(x) != n_: continue
        us.append(u); lo_v.append(x[i_][0]); hi_v.append(x[i_][1])
    if len(us) < max(3, 0.3 * len(us0)): return WHY.append('gap') or None
    us = np.array(us)
    s = (us - us[0]) / (us[-1] - us[0])
    H = levels                                   # 高さの関数（下→上）
    def curve(vs, h):
        Q = np.array([[*_xy(u, v), 0.0] for u, v in zip(us, vs)])
        Q[:, 2] = [h(q[0], q[1]) for q in Q]
        return Q
    QS = [(curve(lo_v, h), curve(hi_v, h)) for h in H]
    if any(np.isnan(q).any() for pair in QS for q in pair): return WHY.append('nan') or None
    for ncv in (2, 4, 6, 8, 12, 16, 24, 32, 48, 64):
        if ncv > len(us): break
        fits = [(_fit(s, qw, ncv), _fit(s, qe, ncv)) for qw, qe in QS]
        err = max(max(fw[3], fe[3]) for fw, fe in fits)
        if err <= TOL / 3: break
    if err > TOL: return WHY.append(('fit', round(err), round(ub - ua, 3))) or None
    dw, kn = fits[0][0][0], fits[0][0][1]
    out = []
    def brep(rows): return r.Brep.CreateFromSurface(_surface(dw, kn, rows))
    rowsW = [fw[2] for fw, fe in fits]
    rowsE = [fe[2] for fw, fe in fits]
    levels = H
    for i in range(len(levels)):
        out.append(brep([rowsW[i], rowsE[i]]))                    # 上・下の面
    if len(levels) == 2:
        out.append(brep([rowsW[0], rowsW[1]]))                    # 西の小口
        out.append(brep([rowsE[0], rowsE[1]]))                    # 東の小口
        for i in (0, -1):                                         # 南北の端（2×2）
            ns = r.NurbsSurface.Create(3, False, 2, 2, 2, 2)
            pts = [[rowsW[0][i], rowsE[0][i]], [rowsW[1][i], rowsE[1][i]]]
            for a in range(2):
                for b_ in range(2): ns.Points[a, b_] = r.Point4d(*map(float, pts[a][b_]), 1.0)
            ns.KnotsU[0], ns.KnotsU[1] = 0.0, 1.0; ns.KnotsV[0], ns.KnotsV[1] = 0.0, 1.0
            out.append(r.Brep.CreateFromSurface(ns))
    if any(b is None for b in out): return WHY.append('brep') or None
    return out

def _quad(p00, p10, p01, p11):
    ns = r.NurbsSurface.Create(3, False, 2, 2, 2, 2)
    for (a, b_), p in (((0, 0), p00), ((1, 0), p10), ((0, 1), p01), ((1, 1), p11)):
        ns.Points[a, b_] = r.Point4d(*map(float, p), 1.0)
    ns.KnotsU[0], ns.KnotsU[1] = 0.0, 1.0; ns.KnotsV[0], ns.KnotsV[1] = 0.0, 1.0
    return r.Brep.CreateFromSurface(ns)

def narrow_box(W, T):
    """細長い片（光の筋の立ち上がり・ふさぐ板・けらばの細い板）：長い向きに沿う箱。
    上と下の縁は長い向きに沿って直線（傾いてよい）。頂点の 98% が 15 mm 以内に入らなければ None"""
    P = W[np.unique(T.ravel())]
    c = P[:, :2].mean(0); X = P[:, :2] - c
    w_, V_ = np.linalg.eigh(X.T @ X); d = V_[:, 1]; n = V_[:, 0]
    a = X @ d; b = X @ n
    if np.ptp(b) > 400 or np.ptp(a) < 5 * np.ptp(b): return None
    z = P[:, 2]
    # 上と下：長い向きの区間ごとの最大・最小に直線をあてる
    bins = np.linspace(a.min(), a.max(), 21); top, bot, am = [], [], []
    for i in range(20):
        sel = (a >= bins[i]) & (a <= bins[i + 1])
        if sel.sum(): am.append(a[sel].mean()); top.append(z[sel].max()); bot.append(z[sel].min())
    if len(am) < 3: return None
    kt = np.polyfit(am, top, 1); kb = np.polyfit(am, bot, 1)
    zt, zb = np.polyval(kt, a), np.polyval(kb, a)
    dev = np.minimum(np.abs(z - zt), np.abs(z - zb))
    inside = (z <= zt + TOL) & (z >= zb - TOL)
    if (inside & ((dev < TOL) | True)).mean() < 0.98: return None
    if np.mean(np.abs(z - np.clip(z, zb, zt)) < TOL) < 0.98: return None
    a0, a1, b0, b1 = a.min(), a.max(), b.min(), b.max()
    def pt(aa, bb, top_):
        q = c + d * aa + n * bb; return (q[0], q[1], np.polyval(kt if top_ else kb, aa))
    C = {(i, j, k): pt([a0, a1][i], [b0, b1][j], k) for i in (0, 1) for j in (0, 1) for k in (0, 1)}
    faces = [(C[0, 0, 1], C[1, 0, 1], C[0, 1, 1], C[1, 1, 1]), (C[0, 0, 0], C[1, 0, 0], C[0, 1, 0], C[1, 1, 0]),
             (C[0, 0, 0], C[1, 0, 0], C[0, 0, 1], C[1, 0, 1]), (C[0, 1, 0], C[1, 1, 0], C[0, 1, 1], C[1, 1, 1]),
             (C[0, 0, 0], C[0, 1, 0], C[0, 0, 1], C[0, 1, 1]), (C[1, 0, 0], C[1, 1, 0], C[1, 0, 1], C[1, 1, 1])]
    out = [_quad(*f) for f in faces]
    return None if any(x is None for x in out) else out
