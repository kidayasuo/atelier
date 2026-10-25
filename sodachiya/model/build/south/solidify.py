"""閉じた三角形のメッシュ → 閉じた Brep（ポリサーフェス）。ソリッド係（10-25）。
使い方：from solidify import solid_from_mesh;  geo, info = solid_from_mesh(W, T)
- 同じ平面の三角形をまとめて一枚の平らな面に（穴はループ）。三つ以上の面が集まる頂点は、その平面の交点に合わせる。
- 細かく分けられた曲面（丸太・幹・樋・輪など）は、円柱・球を当てはめて曲面に戻す（曲線は曲線で）。
  円柱は回転面（u＝角度、v＝軸に沿う長さ）、半周（170°）を超えるものは面の境で分ける。球も回転面（極は特異点）。
  隣り合う面のすき間は短い角度（1.5°〜40°）のものだけを曲面の候補にする。本館の弧（スパンごとの多角形、0.84°）は
  決めたとおり多角形のまま。
- 辺は、線・円弧・楕円弧（平面と円柱の交わり）を正しい曲線で書き、当てはまらないものはメッシュの頂点を通るポリライン。
- 出来たものは openNURBS で IsValid・IsSolid を確かめる。駄目なら、曲面に戻さない（平らな面だけの）版を試し、
  それも駄目なら None（呼ぶ側がメッシュのままにする）。
"""
import math
import numpy as np
import rhino3dm as r
import onbrep as O

TOL_PLANE = 0.5          # 平面からのずれ (mm)
COS_PLANE = math.cos(math.radians(0.3))
ANG_LO, ANG_HI = math.radians(1.5), math.radians(40.0)   # 曲面の候補になる隣どうしの折れ角
FIT_TOL = 0.5            # 円柱・球の当てはめのずれ (mm)
MAX_R = 50000.0          # これより大きい半径は曲面にしない
SPLIT = math.radians(170.0)
EPS_LINE = 0.02          # 頂点が線・円にのっているとみなすずれ (mm)
EPS8 = 8.0 * 1.4901161193847656e-08


# ---------------------------------------------------------------- 曲面（平面・円柱・球）
class Plane:
    kind = 'plane'

    def __init__(self, n, p):
        n = np.asarray(n, float); self.n = n / np.linalg.norm(n); self.o = np.asarray(p, float)
        a = np.array([1., 0, 0]) if abs(self.n[0]) < 0.9 else np.array([0, 1., 0])
        self.x = np.cross(a, self.n); self.x /= np.linalg.norm(self.x); self.y = np.cross(self.n, self.x)

    def uv(self, p, ref=None):
        q = np.asarray(p) - self.o; return (float(q @ self.x), float(q @ self.y))

    def proj(self, p): return p - ((p - self.o) @ self.n) * self.n
    def dist(self, p): return abs((p - self.o) @ self.n)

    def surface(self, dom):
        pl = r.Plane(r.Point3d(*map(float, self.o)), r.Vector3d(*map(float, self.x)), r.Vector3d(*map(float, self.y)))
        return r.PlaneSurface(pl, r.Interval(*dom[0]), r.Interval(*dom[1]))


class Cyl:
    """軸 c + t a、半径 R。sgn=+1 は外向き（凸）、−1 は内向き（穴の内面）。u＝sgn・角度、v＝軸の座標 − t0"""
    kind = 'cyl'

    def __init__(self, c, a, R, sgn):
        a = np.asarray(a, float); self.a = a / np.linalg.norm(a); self.c = np.asarray(c, float); self.R = float(R); self.sgn = sgn
        b = np.array([1., 0, 0]) if abs(self.a[0]) < 0.9 else np.array([0, 1., 0])
        self.X = np.cross(b, self.a); self.X /= np.linalg.norm(self.X); self.Y = np.cross(self.a, self.X)
        self.t0 = 0.0; self.uc = 0.0

    def ang(self, p):
        q = np.asarray(p) - self.c; return math.atan2(q @ self.Y, q @ self.X)

    def uv(self, p, ref=None):
        th = self.sgn * self.ang(p); ref = self.uc if ref is None else ref
        th = ref + (th - ref + math.pi) % (2 * math.pi) - math.pi
        return (th, float((np.asarray(p) - self.c) @ self.a - self.t0))

    def proj(self, p):
        q = p - self.c; ax = (q @ self.a) * self.a; rad = q - ax; n = np.linalg.norm(rad)
        if n < 1e-9: return p
        return self.c + ax + rad * (self.R / n)

    def dist(self, p):
        q = p - self.c; return abs(np.linalg.norm(q - (q @ self.a) * self.a) - self.R)

    def surface(self, dom):
        (u0, u1), (v0, v1) = dom
        base = self.c + self.R * self.X
        prof = r.LineCurve(r.Point3d(*map(float, base + self.a * (self.t0 + v0))), r.Point3d(*map(float, base + self.a * (self.t0 + v1))))
        prof.SetDomain(r.Interval(v0, v1)) if hasattr(prof, 'SetDomain') else None
        ax = self.a * self.sgn
        s = r.RevSurface.Create(prof, r.Line(r.Point3d(*map(float, self.c)), r.Point3d(*map(float, self.c + ax))), u0, u1)
        s.SetDomain(0, r.Interval(u0, u1)); s.SetDomain(1, r.Interval(v0, v1))
        return s


def arcpar(phi, t0, t1):
    """arc_nurbs(t0→t1) の弧で、角度 phi の点の NURBS のパラメータ（有理 2 次の円弧は角度に比例しない）"""
    n = max(1, int(math.ceil(abs(t1 - t0) / (math.pi / 2) - 1e-9))); h = (t1 - t0) / n / 2
    k = min(max(int((phi - t0) // (2 * h)), 0), n - 1); a = t0 + 2 * h * k
    s = 0.5 + math.tan((phi - a - h) / 2) / (2 * math.tan(h / 2))
    return a + 2 * h * s


def _wrap(x, ref): return ref + (x - ref + math.pi) % (2 * math.pi) - math.pi


class Sph:
    """中心 c、半径 R。軸 a のまわりの回転面：u＝sgn・経度、v＝子午線（緯度 −π/2〜π/2 の円弧）のパラメータ"""
    kind = 'sph'

    def __init__(self, c, R, a, sgn):
        self.c = np.asarray(c, float); self.R = float(R); self.sgn = sgn
        a = np.asarray(a, float); self.a = a / np.linalg.norm(a)
        b = np.array([1., 0, 0]) if abs(self.a[0]) < 0.9 else np.array([0, 1., 0])
        self.X = np.cross(b, self.a); self.X /= np.linalg.norm(self.X); self.Y = np.cross(self.a, self.X)
        self.uc = 0.0; self.vdom = (-math.pi / 2, math.pi / 2)

    def ang(self, p):
        q = np.asarray(p) - self.c; return math.atan2(q @ self.Y, q @ self.X)

    def lat(self, p):
        q = np.asarray(p) - self.c; n = np.linalg.norm(q)
        return math.asin(max(-1.0, min(1.0, (q @ self.a) / n))) if n > 0 else 0.0

    def uv(self, p, ref=None):
        ref = self.uc if ref is None else ref
        return (_wrap(self.sgn * self.ang(p), ref), arcpar(self.lat(p), *self.vdom))

    def is_pole(self, p):
        q = np.asarray(p) - self.c; return np.linalg.norm(q - (q @ self.a) * self.a) < 1e-3 * max(self.R, 1.0)

    def proj(self, p):
        q = p - self.c; n = np.linalg.norm(q)
        return p if n < 1e-9 else self.c + q * (self.R / n)

    def dist(self, p): return abs(np.linalg.norm(p - self.c) - self.R)

    def normal_ok(self, p, n): 
        m = p - self.c; return abs(n @ m) / max(np.linalg.norm(m), 1e-12)

    def surface(self, dom):
        (u0, u1), _ = dom
        P = lambda t: self.c + self.R * (math.cos(t) * self.X + math.sin(t) * self.a)
        crv = O.decode(arc_nurbs(P, self.c, self.vdom[0], self.vdom[1], 3))
        ax = self.a * self.sgn
        s = r.RevSurface.Create(crv, r.Line(r.Point3d(*map(float, self.c)), r.Point3d(*map(float, self.c + ax))), u0, u1)
        s.SetDomain(0, r.Interval(u0, u1))
        return s


def _ell_closest(x, y, A, B):
    """楕円 (A cos t, B sin t) の、点 (x, y) に近い点の t（ニュートン法）"""
    t = math.atan2(y * A, x * B)
    for _ in range(8):
        c, s_ = math.cos(t), math.sin(t)
        fx, fy = A * c - x, B * s_ - y
        dx, dy = -A * s_, B * c
        g = fx * dx + fy * dy; h = dx * dx + dy * dy + fx * (-A * c) + fy * (-B * s_)
        if abs(h) < 1e-12: break
        t -= g / h
    return t


class Tor:
    """管が円に沿う回転面（円環、管の断面は楕円でもよい）：軸 c + t a、中心の円の半径 R、
    管の半径 A（半径の向き）・B（軸の向き）、管の中心の高さ h0。u＝sgn・角度、v＝管の楕円のパラメータ
    （角度 φ：0 が外側、a の向きに増える。輪郭は vc−π〜vc+π）"""
    kind = 'tor'

    def __init__(self, c, a, R, A, B, h0, sgn):
        a = np.asarray(a, float); self.a = a / np.linalg.norm(a); self.c = np.asarray(c, float)
        self.R, self.A, self.B, self.h0, self.sgn = float(R), float(A), float(B), float(h0), sgn
        b = np.array([1., 0, 0]) if abs(self.a[0]) < 0.9 else np.array([0, 1., 0])
        self.X = np.cross(b, self.a); self.X /= np.linalg.norm(self.X); self.Y = np.cross(self.a, self.X)
        self.uc = 0.0; self.vc = 0.0; self.vdom = (-math.pi, math.pi)

    def set_vc(self, vc): self.vc = vc; self.vdom = (vc - math.pi, vc + math.pi)

    def ang(self, p):
        q = np.asarray(p) - self.c; return math.atan2(q @ self.Y, q @ self.X)

    def _rh(self, p):
        q = np.asarray(p) - self.c; h = q @ self.a; rad = q - h * self.a; rho = np.linalg.norm(rad)
        return rho, h, rad

    def phi(self, p):
        rho, h, _ = self._rh(p); return math.atan2((h - self.h0) / self.B, (rho - self.R) / self.A)

    def uv(self, p, ref=None):
        ref = self.uc if ref is None else ref
        return (_wrap(self.sgn * self.ang(p), ref), arcpar(_wrap(self.phi(p), self.vc), *self.vdom))

    def proj(self, p):
        rho, h, rad = self._rh(p)
        if rho < 1e-9: return p
        t = _ell_closest(rho - self.R, h - self.h0, self.A, self.B)
        return self.c + rad / rho * (self.R + self.A * math.cos(t)) + self.a * (self.h0 + self.B * math.sin(t))

    def dist(self, p): return float(np.linalg.norm(self.proj(np.asarray(p, float)) - p))

    def surface(self, dom):
        (u0, u1), _ = dom
        C = self.c + self.R * self.X + self.h0 * self.a
        P = lambda t: C + self.A * math.cos(t) * self.X + self.B * math.sin(t) * self.a
        crv = O.decode(arc_nurbs(P, C, self.vdom[0], self.vdom[1], 3))
        ax = self.a * self.sgn
        s = r.RevSurface.Create(crv, r.Line(r.Point3d(*map(float, self.c)), r.Point3d(*map(float, self.c + ax))), u0, u1)
        s.SetDomain(0, r.Interval(u0, u1))
        return s


def arc_nurbs(P, cen, t0, t1, dim, to2=None, ends=None):
    """円（楕円）の弧 P(t)（t は角度、cen は中心）を有理 2 次の NURBS に。to2 があれば平面の 2 次元へ写す"""
    if t1 < t0:                                   # 逆向き：s = −t で増える向きに
        return arc_nurbs(lambda s: P(-s), cen, -t0, -t1, dim, to2, ends)
    n = max(1, int(math.ceil(abs(t1 - t0) / (math.pi / 2) - 1e-9)))
    ts = [t0 + (t1 - t0) * k / n for k in range(n + 1)]; ts[0] = t0; ts[-1] = t1
    h = (t1 - t0) / n / 2; w = math.cos(h)
    cvs, ws = [], []
    for k in range(n):
        a, b = ts[k], ts[k + 1]
        pa, pb = P(a), P(b)
        # 接線の交点：中心から弧の中ほどの点への向きに 1/cos h 倍（楕円は円のアフィン像なので同じ）
        cv = cen + (P((a + b) / 2) - cen) / w
        if k == 0: cvs.append(pa); ws.append(1.0)
        cvs += [cv, pb]; ws += [w, 1.0]
    knots = [ts[0]] * 2
    for k in range(1, n): knots += [ts[k]] * 2
    knots += [ts[-1]] * 2
    if to2 is not None: cvs = [to2(p) for p in cvs]
    if ends is not None: cvs[0] = ends[0]; cvs[-1] = ends[1]     # 端は頂点にぴったり
    _LAST_CVS[:] = [tuple(p) for p in cvs]
    return O.nurbs(dim, 3, knots, cvs, ws)


_LAST_CVS = []


# ---------------------------------------------------------------- 当てはめ
def fit_circle2(P):
    m = P.mean(0); Q = P - m
    A = np.c_[2 * Q, np.ones(len(Q))]; b = (Q ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:2]; R = math.sqrt(max(sol[2] + c @ c, 0)); return c + m, R


def fit_cyl(pts, normals, wts):
    M = (normals * wts[:, None]).T @ normals
    w, v = np.linalg.eigh(M); a = v[:, 0]
    if w[0] > 0.02 * w.sum(): return None
    b = np.array([1., 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1., 0])
    X = np.cross(b, a); X /= np.linalg.norm(X); Y = np.cross(a, X)
    q = np.c_[pts @ X, pts @ Y]
    c2, R = fit_circle2(q)
    if not (1.0 < R < MAX_R): return None
    res = np.abs(np.linalg.norm(q - c2, axis=1) - R).max()
    c = c2[0] * X + c2[1] * Y
    return res, (c, a, R)


def fit_sph(pts):
    m = pts.mean(0); Q = pts - m
    A = np.c_[2 * Q, np.ones(len(Q))]; b = (Q ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]; R = math.sqrt(max(sol[3] + c @ c, 0)); c = c + m
    if not (1.0 < R < MAX_R): return None
    return np.abs(np.linalg.norm(pts - c, axis=1) - R).max(), (c, R)


def fit_tor(pts):
    """管が円に沿う形（管の断面は軸にそろった楕円）：平面 → 中心の円 → 管。→ (ずれ, (c, a, R, A, B, h0))"""
    if len(pts) < 8: return None
    from scipy.optimize import least_squares
    c0 = pts.mean(0); _, sv, vt = np.linalg.svd(pts - c0, full_matrices=False)
    a = vt[2]; e1, e2 = vt[0], vt[1]
    q = np.c_[(pts - c0) @ e1, (pts - c0) @ e2]; hh = (pts - c0) @ a
    c2, Rm = fit_circle2(q)
    if not (1.0 < Rm < 1e7): return None
    rho = np.linalg.norm(q - c2, axis=1)
    A0 = max((rho.max() - rho.min()) / 2, 1.0); B0 = max((hh.max() - hh.min()) / 2, 1.0)
    x0 = [c2[0], c2[1], (rho.max() + rho.min()) / 2, A0, B0, (hh.max() + hh.min()) / 2]
    def res(x, geo=False):
        rr = np.hypot(q[:, 0] - x[0], q[:, 1] - x[1]) - x[2]; yy = hh - x[5]
        A, B = abs(x[3]) + 1e-9, abs(x[4]) + 1e-9
        if not geo: return (np.hypot(rr / A, yy / B) - 1) * min(A, B)
        t = np.arctan2(yy * A, rr * B)                     # 楕円への本当の距離（ニュートン法）
        for _ in range(6):
            c_, s_ = np.cos(t), np.sin(t); fx, fy = A * c_ - rr, B * s_ - yy; dx, dy = -A * s_, B * c_
            g = fx * dx + fy * dy; h2 = dx * dx + dy * dy - fx * A * c_ - fy * B * s_
            t = t - g / np.where(np.abs(h2) < 1e-12, 1e-12, h2)
        d = np.hypot(A * np.cos(t) - rr, B * np.sin(t) - yy)
        return d * np.sign(np.hypot(rr / A, yy / B) - 1)
    try:
        sol = least_squares(res, x0, x_scale='jac', max_nfev=200)
        sol = least_squares(lambda x: res(x, True), sol.x, x_scale='jac', max_nfev=200, ftol=1e-12, xtol=1e-12)
    except Exception: return None
    cx, cy, R, A, B, h0 = sol.x; A, B = abs(A), abs(B)
    if not (0.5 < min(A, B) and max(A, B) < 0.9 * R and max(A, B) < 5 * min(A, B)): return None
    c = c0 + cx * e1 + cy * e2 + 0 * a
    T = Tor(c, a, R, A, B, h0, 1)
    dev = max(T.dist(p) for p in pts[:: max(1, len(pts) // 400)])
    if dev < FIT_TOL: dev = max(T.dist(p) for p in pts)
    return dev, (c, a, R, A, B, h0)


# ---------------------------------------------------------------- 本体
class Fail(Exception): pass


def _ptol(t0, t1, t):
    dt = (t1 - t0) * EPS8 + (abs(t0) + abs(t1)) * 2.220446049250313e-16
    return t - dt, t + dt


def iso_flag(bmin, bmax, dom):
    """ON_Surface::IsIsoparametric(bbox) と同じ（0 not 1 x 2 y 3 W 4 S 5 E 6 N）"""
    (s0, s1), (t0, t1) = dom
    ds, dt = bmax[0] - bmin[0], bmax[1] - bmin[1]
    stol, ttol = (s1 - s0) / 32.0, (t1 - t0) / 32.0
    iso = 0
    if s0 < s1 and t0 < t1 and (ds <= stol or dt <= ttol):
        if ds * (t1 - t0) <= dt * (s1 - s0):
            if bmax[0] <= s0 + stol:
                a, b = _ptol(s0, s1, s0)
                if a <= bmin[0] and bmax[0] <= b: iso = 3
            elif bmin[0] >= s1 - stol:
                a, b = _ptol(s0, s1, s1)
                if a <= bmin[0] and bmax[0] <= b: iso = 5
            if iso == 0 and (s0 < bmax[0] or bmin[0] < s1):
                a, b = _ptol(s0, s1, 0.5 * (bmin[0] + bmax[0]))
                if a <= bmin[0] and bmax[0] <= b: iso = 1
        else:
            if bmax[1] <= t0 + ttol:
                a, b = _ptol(t0, t1, t0)
                if a <= bmin[1] and bmax[1] <= b: iso = 4
            elif bmin[1] >= t1 - ttol:
                a, b = _ptol(t0, t1, t1)
                if a <= bmin[1] and bmax[1] <= b: iso = 6
            if iso == 0 and (t0 < bmax[1] or bmin[1] < t1):
                a, b = _ptol(t0, t1, 0.5 * (bmin[1] + bmax[1]))
                if a <= bmin[1] and bmax[1] <= b: iso = 2
    return iso


def orient(T):
    """三角形の向きをそろえる（となりどうしで辺が逆向きになるように）。辺に三つ以上の三角形 → Fail"""
    T = np.array(T, int).copy(); ue = {}
    for t, (a, b, c) in enumerate(T):
        for e in ((a, b), (b, c), (c, a)):
            ue.setdefault((min(e), max(e)), []).append(t)
    if any(len(ts) > 2 for ts in ue.values()): raise Fail('not manifold')
    if any(len(ts) < 2 for ts in ue.values()): raise Fail('open')
    nb = [[] for _ in range(len(T))]
    for (a, b), ts in ue.items():
        if len(ts) == 2: nb[ts[0]].append((ts[1], a, b)); nb[ts[1]].append((ts[0], a, b))
    seen = np.zeros(len(T), bool)
    def dirn(t, a, b):
        x, y, z = T[t]; return (x, y) == (a, b) or (y, z) == (a, b) or (z, x) == (a, b)
    for s0 in range(len(T)):
        if seen[s0]: continue
        seen[s0] = True; st = [s0]
        while st:
            t = st.pop()
            for u, a, b in nb[t]:
                if seen[u]:
                    continue
                if dirn(t, a, b) == dirn(u, a, b): T[u] = T[u][::-1]
                seen[u] = True; st.append(u)
    return T


def iso_curve(pts, dom):
    """トリムの iso（ON_Surface::IsIsoparametric(curve)：外接箱で判定し、線でなければ iso にしない）"""
    a = np.asarray(pts, float)[:, :2]; bmin = a.min(0); bmax = a.max(0)
    iso = iso_flag(tuple(bmin), tuple(bmax), dom)
    if iso == 0 or len(a) == 2: return iso
    k = 0 if iso in (1, 3, 5) else 1
    tol = bmax[k] - bmin[k]
    if tol < 2.3283064365386963e-10 and 2.3283064365386963e-10 * 1024 <= bmax[1 - k] - bmin[1 - k]: tol = 2.3283064365386963e-10
    d = a[-1] - a[0]; L = np.linalg.norm(d)
    if L == 0: return 0
    dev = np.abs((a[:, 0] - a[0, 0]) * d[1] - (a[:, 1] - a[0, 1]) * d[0]) / L
    return iso if dev.max() <= tol else 0


def topology(W, T):
    he = {}
    for t, (a, b, c) in enumerate(T):
        for k, e in enumerate(((a, b), (b, c), (c, a))):
            if e in he or e[0] == e[1]: raise Fail('not manifold')
            he[e] = t
    for e in he:
        if (e[1], e[0]) not in he: raise Fail('open')
    return he


def planar_regions(W, T, N, area, he):
    nt = len(T); reg = -np.ones(nt, int); regs = []
    nb = [[] for _ in range(nt)]
    for (a, b), t in he.items(): nb[t].append(he[(b, a)])
    # 細い三角形（高さ 0.3 mm 未満）は法線があてにならない → 面の種にせず、どの面にも入れてよい
    lmax = np.max([np.linalg.norm(W[T[:, i]] - W[T[:, (i + 1) % 3]], axis=1) for i in range(3)], axis=0)
    thin = 2 * area / np.maximum(lmax, 1e-12) < 0.3
    for seed in np.argsort(-area):
        if reg[seed] >= 0 or thin[seed]: continue
        rid = len(regs); n = N[seed].copy(); p0 = W[T[seed]].mean(0)
        reg[seed] = rid; mem = [seed]; q = [seed]; sn = N[seed] * area[seed]
        while q:
            t = q.pop()
            for u in nb[t]:
                if reg[u] >= 0: continue
                if not thin[u] and N[u] @ n < COS_PLANE: continue
                if np.abs((W[T[u]] - p0) @ n).max() > TOL_PLANE: continue
                reg[u] = rid; mem.append(u); q.append(u)
                if not thin[u]:
                    sn = sn + N[u] * area[u]
                    if len(mem) % 32 == 0: n = sn / np.linalg.norm(sn)
        regs.append(mem)
    # 面積の無い三角形：となりの面に入れる
    left = [t for t in range(nt) if reg[t] < 0]
    for _ in range(10):
        if not left: break
        nxt = []
        for t in left:
            cand = [reg[u] for u in nb[t] if reg[u] >= 0]
            if cand: reg[t] = cand[0]; regs[cand[0]].append(t)
            else: nxt.append(t)
        left = nxt
    if left:
        for t in left: reg[t] = len(regs); regs.append([t])
    return reg, regs, nb


def merge_small(W, T, N, area, reg, regs, nb, amin=2.0):
    """小さな面（面積 amin mm² 未満）を、頂点がよくのるとなりの面に入れる（角の頂点を合わせると潰れてしまうので）"""
    def plane_of(mem):
        mem = np.array(mem); s = (N[mem] * area[mem, None]).sum(0); n = np.linalg.norm(s)
        return (s / n, W[T[mem]].reshape(-1, 3).mean(0)) if n > 1e-12 else (None, None)
    alive = [True] * len(regs)
    planes = [plane_of(m) for m in regs]
    order = sorted(range(len(regs)), key=lambda i: area[np.array(regs[i])].sum())
    lmax = lambda t: max(np.linalg.norm(W[T[t][k]] - W[T[t][(k + 1) % 3]]) for k in range(3))
    for i in order:
        A_ = area[np.array(regs[i])].sum()
        if A_ >= amin and not (len(regs[i]) == 1 and 2 * A_ / max(lmax(regs[i][0]), 1e-12) < 1.0): continue
        vs = W[np.unique(T[np.array(regs[i])].ravel())]
        best = None
        for t in regs[i]:
            for u in nb[t]:
                j = reg[u]
                if j == i or not alive[j] or planes[j][0] is None: continue
                d = np.abs((vs - planes[j][1]) @ planes[j][0]).max()
                if best is None or d < best[0]: best = (d, j)
        if best is not None and best[0] < 2 * TOL_PLANE:
            j = best[1]
            for t in regs[i]: reg[t] = j
            regs[j] = regs[j] + regs[i]; regs[i] = []; alive[i] = False
    keep = [i for i in range(len(regs)) if alive[i] and regs[i]]
    ren = {o: k for k, o in enumerate(keep)}
    for t in range(len(reg)): reg[t] = ren[reg[t]]
    return [regs[i] for i in keep]


def solid_from_mesh(W, T, curved=True):
    """→ (rhino3dm.Brep か None, 情報の文字)"""
    W = np.asarray(W, float); T = np.asarray(T, int)
    why = []
    for cv, sn in (((True, True), (False, True), (False, False)) if curved else ((False, True), (False, False))):
        try:
            b = _build(W, T, cv, sn)
            return b, ('curved' if cv else 'planar') + ('' if not why else '(' + why[0] + ')')
        except Fail as e:
            why.append(str(e))
            if str(e) in ('open', 'not manifold'): break
        except Exception as e:
            why.append('error:' + type(e).__name__ + ':' + str(e)[:60])
    return None, ' / '.join(why)


def drop_doubles(T):
    """同じ三つの頂点の三角形の組：向きが逆なら両方消す（重なった内側の面・厚みの無い片）、同じ向きなら一つに"""
    T = np.asarray(T, int); seen = {}
    for t, tri in enumerate(T): seen.setdefault(tuple(sorted(tri)), []).append(t)
    drop = set()
    for ts in seen.values():
        if len(ts) < 2: continue
        fw = [t for t in ts if _cyc(T[t]) == _cyc(T[ts[0]])]; bw = [t for t in ts if t not in fw]
        k = min(len(fw), len(bw)); drop.update(fw[:k]); drop.update(bw[:k])
        rest = fw[k:] + bw[k:]; drop.update(rest[1:])
    if not drop: return T
    return T[[t for t in range(len(T)) if t not in drop]]


def _cyc(tri):
    a, b, c = (int(x) for x in tri); m = min(a, b, c)
    return (a, b, c) if a == m else ((b, c, a) if b == m else (c, a, b))


def shells(T):
    """二つより多くの三角形が集まる辺では三角形をつながず、ふつうの辺でつながる組に分ける"""
    ue = {}
    for t, (a, b, c) in enumerate(T):
        for e in ((a, b), (b, c), (c, a)): ue.setdefault((min(e), max(e)), []).append(t)
    par = list(range(len(T)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for ts in ue.values():
        if len(ts) == 2: par[f(ts[0])] = f(ts[1])
    lab = {}
    for t in range(len(T)): lab.setdefault(f(t), []).append(t)
    return [np.asarray(T)[ix] for ix in lab.values()]


def split_nonmanifold(W, T):
    """四つ以上の三角形が集まる辺を、立体ごとの組に分け、頂点を写して別の辺にする（触れあう二つの立体・自分に触れる立体）。
    向きのそろったメッシュが前提：a→b の三角形は、辺のまわりを右回りに見て次の b→a の三角形と組になる（そのあいだが中身）"""
    W = np.asarray(W, float); T = np.array(T, int)
    ue = {}
    for t, (a, b, c) in enumerate(T):
        for k, e in enumerate(((a, b), (b, c), (c, a))): ue.setdefault((min(e), max(e)), []).append((t, e))
    pair = {}          # (t, 無向の辺) → 組の相手の三角形
    for (a, b), lst in ue.items():
        if len(lst) == 2:
            (t1, _), (t2, _) = lst; pair[(t1, (a, b))] = t2; pair[(t2, (a, b))] = t1; continue
        if len(lst) % 2: raise Fail('not manifold')
        e = W[b] - W[a]; e = e / np.linalg.norm(e)
        x = np.cross(e, [1., 0, 0]) if abs(e[0]) < 0.9 else np.cross(e, [0, 1., 0]); x /= np.linalg.norm(x); y = np.cross(e, x)
        fins = []
        for t, d in lst:
            c = [v for v in T[t] if v not in (a, b)][0]; f = W[c] - W[a]
            fins.append((math.atan2(f @ y, f @ x), t, d == (a, b)))
        fins.sort()
        used = set(); nf_ = len(fins)
        for i, (ang, t, fwd) in enumerate(fins):
            if not fwd: continue
            # 右回り（角度の減る向き）に次の逆向きの三角形。同じ角度の三角形（重なった面）はとばし、
            # 同じ角度の組の中では逆向きのものを選ぶ
            k = 1; got = None
            while k < nf_ and got is None:
                ang2 = fins[(i - k) % nf_][0]
                if abs(((ang - ang2) + math.pi) % (2 * math.pi) - math.pi) < 2e-3: k += 1; continue
                grp = []
                while k < nf_ and abs(fins[(i - k) % nf_][0] - ang2) < 2e-3: grp.append(fins[(i - k) % nf_]); k += 1
                cand = [g for g in grp if not g[2] and g[1] not in used]
                if cand: got = cand[0][1]
                elif any(g[2] for g in grp): raise Fail('not manifold')
            if got is None: raise Fail('not manifold')
            pair[(t, (a, b))] = got; pair[(got, (a, b))] = t; used.add(got)
    # 頂点ごとに、まわりの三角形を組でつないで扇に分け、扇ごとに頂点を写す
    vt = {}
    for t, tri in enumerate(T):
        for v in tri: vt.setdefault(v, []).append(t)
    Wl = list(W); T2 = T.copy()
    for v, ts in vt.items():
        if len(ts) < 2: continue
        tset = set(ts); par = {t: t for t in ts}
        def f(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        for t in ts:
            for u in T[t]:
                if u == v: continue
                k = (min(u, v), max(u, v)); o = pair.get((t, k))
                if o is not None and o in tset: par[f(t)] = f(o)
        groups = {}
        for t in ts: groups.setdefault(f(t), []).append(t)
        if len(groups) < 2: continue
        for gi, g in enumerate(list(groups.values())[1:]):
            nv = len(Wl); Wl.append(W[v].copy())
            for t in g: T2[t] = [nv if x == v else x for x in T2[t]]
    return np.array(Wl), T2


def via_manifold(W, T):
    """manifold3d で多様体に直す：つながりごとに分け、足し合わせ（重なりを解く）、細かい辺をまとめる（0〜0.05 mm）。
    → [(W, T), …]（頂点はできるだけもとの座標に戻す。ゆるい順に試す）"""
    try:
        import manifold3d as mf
        from scipy.spatial import cKDTree
    except Exception:
        return []
    vs = np.unique(T.ravel()); idx = {v: i for i, v in enumerate(vs)}
    P = W[vs]; c = P.mean(0)
    F = np.array([[idx[v] for v in t] for t in orient_loose(T)], dtype=np.uint32)
    out = []
    try:
        M = mf.Manifold(mf.Mesh(vert_properties=(P - c).astype(np.float32), tri_verts=F))
        if M.status() != mf.Error.NoError or M.num_tri() == 0 or M.volume() < 0: return []
        parts = M.decompose()
        U = mf.Manifold.batch_boolean(parts, mf.OpType.Add) if len(parts) > 1 else M
        for tol in (0.0, 0.01, 0.05):
            V = U.set_tolerance(tol).simplify(tol) if tol else U
            o = V.to_mesh()
            Q = np.asarray(o.vert_properties)[:, :3].astype(float) + c; Tq = np.asarray(o.tri_verts).astype(int)
            if len(Tq) == 0: continue
            d, k = cKDTree(P).query(Q)
            out.append((np.where((d < 0.02)[:, None], P[k], Q), Tq))
    except Exception:
        pass
    return out


def orient_loose(T):
    """二つの三角形だけの辺でつながる組ごとに向きをそろえる（それより多い辺はつながない）"""
    T = np.array(T, int).copy(); ue = {}
    for t, (a, b, c) in enumerate(T):
        for e in ((a, b), (b, c), (c, a)): ue.setdefault((min(e), max(e)), []).append(t)
    nb = [[] for _ in range(len(T))]
    for (a, b), ts in ue.items():
        if len(ts) == 2: nb[ts[0]].append((ts[1], a, b)); nb[ts[1]].append((ts[0], a, b))
    seen = np.zeros(len(T), bool)
    def dirn(t, a, b):
        x, y, z = T[t]; return (x, y) == (a, b) or (y, z) == (a, b) or (z, x) == (a, b)
    for s0 in range(len(T)):
        if seen[s0]: continue
        seen[s0] = True; st = [s0]
        while st:
            t = st.pop()
            for u, a, b in nb[t]:
                if seen[u]: continue
                if dirn(t, a, b) == dirn(u, a, b): T[u] = T[u][::-1]
                seen[u] = True; st.append(u)
    return T


def orient_open(T):
    """開いたメッシュの向きをそろえる（辺に三つ以上は不可）"""
    T = np.array(T, int).copy(); ue = {}
    for t, (a, b, c) in enumerate(T):
        for e in ((a, b), (b, c), (c, a)): ue.setdefault((min(e), max(e)), []).append(t)
    if any(len(v) > 2 for v in ue.values()): raise Fail('not manifold')
    nb = [[] for _ in range(len(T))]
    for (a, b), ts in ue.items():
        if len(ts) == 2: nb[ts[0]].append((ts[1], a, b)); nb[ts[1]].append((ts[0], a, b))
    seen = np.zeros(len(T), bool)
    def dirn(t, a, b):
        x, y, z = T[t]; return (x, y) == (a, b) or (y, z) == (a, b) or (z, x) == (a, b)
    for s0 in range(len(T)):
        if seen[s0]: continue
        seen[s0] = True; st = [s0]
        while st:
            t = st.pop()
            for u, a, b in nb[t]:
                if seen[u]: continue
                if dirn(t, a, b) == dirn(u, a, b): T[u] = T[u][::-1]
                seen[u] = True; st.append(u)
    return T


def thicken(W, T, mode, t):
    """開いた面に厚みをつけて閉じる。mode：'down' 鉛直に t 下げた面まで、'base' いちばん低い所から t 下の平らな底まで、
    'both' 面の法線の両側に t/2 ずつ"""
    T = orient_open(T); W = np.asarray(W, float)
    vs = np.unique(T.ravel()); idx = {v: i for i, v in enumerate(vs)}
    P = W[vs]; F = np.array([[idx[v] for v in tri] for tri in T])
    a, b, c = P[F[:, 0]], P[F[:, 1]], P[F[:, 2]]; Nf = np.cross(b - a, c - a)
    if mode in ('down', 'base') and abs(Nf[:, 2].sum()) < 0.5 * np.linalg.norm(Nf, axis=1).sum():
        mode = 'both'                                      # 立った面（ガラス・網）は法線の両側に
    if mode in ('down', 'base') and Nf[:, 2].sum() < 0: F = F[:, ::-1]; Nf = -Nf
    n = len(P)
    if mode == 'down': Q = P - np.array([0, 0, t]); top = P
    elif mode == 'base': Q = P.copy(); Q[:, 2] = P[:, 2].min() - t; top = P
    else:
        vn = np.zeros_like(P)
        for k in range(3): np.add.at(vn, F[:, k], Nf)
        vn /= np.maximum(np.linalg.norm(vn, axis=1), 1e-12)[:, None]
        top = P + vn * t / 2; Q = P - vn * t / 2
    W2 = np.vstack([top, Q])
    T2 = [tuple(f) for f in F] + [(f[0] + n, f[2] + n, f[1] + n) for f in F]
    de = set()
    for f in F:
        for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0])): de.add(e)
    for (x, y) in de:
        if (y, x) in de: continue
        T2 += [(x, x + n, y + n), (x, y + n, y)]
    return W2, np.array(T2)


def _arc_runs(Q):
    """閉じた多角形 Q（2 次元、n 点）で、円にのる点の並び → [(i0, i1)]（i0 から i1 まで、角の点を含む、i1 は i0 より後）"""
    n = len(Q)
    def turn(i):
        a, b, c = Q[(i - 1) % n], Q[i], Q[(i + 1) % n]
        u, v = b - a, c - b
        return math.atan2(u[0] * v[1] - u[1] * v[0], u @ v)
    tr = np.array([turn(i) for i in range(n)])
    smooth = (np.abs(tr) > ANG_LO) & (np.abs(tr) < ANG_HI)
    if smooth.all():
        c, R = fit_circle2(Q)
        if np.abs(np.linalg.norm(Q - c, axis=1) - R).max() < 0.05 and np.all(np.sign(tr) == np.sign(tr[0])):
            return [(0, n)]                                     # 輪全体が円
        return []
    # 角（なめらかでない点）から始める
    st = int(np.argmin(smooth))
    runs = []; i = 0
    while i < n:
        k = (st + i) % n
        if not smooth[k]: i += 1; continue
        j = i
        while j < n and smooth[(st + j) % n] and np.sign(tr[(st + j) % n]) == np.sign(tr[k]): j += 1
        # k-1 .. (st+j)%n までの点が弧の候補（両端は角）
        i0 = st + i - 1; i1 = st + j
        idx = [(x) % n for x in range(i0, i1 + 1)]
        P = Q[idx]
        if len(P) >= 4:
            c, R = fit_circle2(P)
            if np.abs(np.linalg.norm(P - c, axis=1) - R).max() < 0.05 and R < MAX_R: runs.append((i0, i1))
        i = j
    return runs


def _profile(Q2, to3, runs):
    """2 次元の閉じた多角形 Q2（円の並び runs）→ PolyCurve（to3 で 3 次元へ）"""
    n = len(Q2); pc = r.PolyCurve()
    P3 = lambda q: r.Point3d(*map(float, to3(q)))
    if runs == [(0, n)]:
        h = n // 2
        pc.Append(r.Arc(P3(Q2[0]), P3(Q2[h // 2]), P3(Q2[h])))
        pc.Append(r.Arc(P3(Q2[h]), P3(Q2[(h + n) // 2]), P3(Q2[0])))
        return pc
    st = {i0 % n: (i0, i1) for i0, i1 in runs}
    i = min(st) if st else 0
    # 角から始める
    start = min((x for x in range(n) if x not in {(y % n) for a, b in runs for y in range(a + 1, b)}), default=0)
    i = start; cnt = 0
    while cnt < n:
        if i % n in st and cnt + (st[i % n][1] - st[i % n][0]) <= n:
            i0, i1 = st[i % n]; m = (i0 + i1) // 2
            pc.Append(r.Arc(P3(Q2[i0 % n]), P3(Q2[m % n]), P3(Q2[i1 % n])))
            cnt += i1 - i0; i = i1
        else:
            a, b = Q2[i % n], Q2[(i + 1) % n]
            pc.Append(r.Line(P3(a), P3(b))); cnt += 1; i += 1
    return pc


def set_miter(e, N0=None, N1=None):
    """押し出しの両端を斜めの面に（ON_Extrusion の m_bHaveN・m_N を書きかえる。rhino3dm には設定が無い）。
    N は押し出しの座標（輪郭の面の X・Y と道の向き Z）で、Z が正。端の面は道の端点を通り N に直角"""
    import struct as st
    def rd(d, p):
        tc, v = st.unpack_from('<Iq', d, p); p += 12
        return (tc, v, d[p:p + v], p + v) if not tc & 0x80000000 else (tc, v, None, p)
    d = O.enc(e); _, _, body, _ = rd(d, 0); _, _, uu, q = rd(body, 0); _, _, dd, _ = rd(body, q)
    _, _, inner, _ = rd(dd, 0); _, _, _, p3 = rd(inner, 8)
    pre, prof, rest = inner[:8], inner[8:p3], bytearray(inner[p3:-4])
    if N0 is not None: rest[88] = 1; rest[90:114] = st.pack('<3d', *map(float, N0))
    if N1 is not None: rest[89] = 1; rest[114:138] = st.pack('<3d', *map(float, N1))
    a = O.Chunk(O.TC_ANON).raw(pre).sub(prof).raw(bytes(rest))
    cls = O.Chunk(0x00027ffa, crc=False).sub(st.pack('<Iq', 0x0002fffb, len(uu)) + uu).sub(O.Chunk(0x0002fffc).sub(a)) \
        .sub(st.pack('<Iq', 0x80027fff, 0))
    return O.decode(cls.bytes())


def as_extrusion(W, T):
    """押し出し（角柱。両端は斜めの面でもよい）にちょうどなる立体 → rhino3dm.Extrusion（輪郭の円は円弧、穴は内側の輪郭）。
    ならなければ None。側面はすべて道の向き d に平行、ほかの面は二つの平面（始めと終わりの端）にのること"""
    W = np.asarray(W, float)
    T = orient(T); he = topology(W, T)
    a, b, c = W[T[:, 0]], W[T[:, 1]], W[T[:, 2]]
    if (np.einsum('ij,ij->i', a, np.cross(b, c))).sum() < 0:
        T = T[:, ::-1].copy(); he = topology(W, T); a, b, c = W[T[:, 0]], W[T[:, 1]], W[T[:, 2]]
    Nr = np.cross(b - a, c - a); ar2 = np.linalg.norm(Nr, axis=1); area = ar2 / 2
    N = Nr / np.maximum(ar2, 1e-30)[:, None]
    lmax = np.max([np.linalg.norm(W[T[:, i]] - W[T[:, (i + 1) % 3]], axis=1) for i in range(3)], axis=0)
    good = 2 * area / np.maximum(lmax, 1e-12) > 0.3
    vs = np.unique(T.ravel())
    top = [i for i in np.argsort(-area)[:8] if good[i]]
    cands = [N[i] for i in top]
    for x in range(len(top)):
        for y in range(x + 1, len(top)):
            cr = np.cross(N[top[x]], N[top[y]]); n_ = np.linalg.norm(cr)
            if n_ > 0.05: cands.append(cr / n_)
    tried = []
    for d in cands:
        if any(abs(d @ t_) > 0.99999 for t_ in tried): continue
        tried.append(d)
        dots = N @ d
        hts = W[vs] @ d; span = max(hts.max() - hts.min(), 1.0)
        side = np.abs(dots) * span < 0.1                       # 側面の傾きによるずれ 0.1 mm まで
        if np.any(good & ~side & (np.abs(dots) < 0.2)): continue
        cap0 = good & (dots <= -0.2); cap1 = good & (dots >= 0.2)
        if not cap0.any() or not cap1.any(): continue
        planes = []
        okp = True
        for cap in (cap0, cap1):
            ids = np.where(cap)[0]; n0 = (N[ids] * area[ids, None]).sum(0); n0 /= np.linalg.norm(n0)
            p0 = W[T[ids]].reshape(-1, 3).mean(0)
            if np.abs((W[T[ids]].reshape(-1, 3) - p0) @ n0).max() > 0.05: okp = False; break
            planes.append((n0, p0))
        if not okp: continue
        (n0, p0), (n1, p1) = planes
        # すべての頂点がどちらかの端の面に
        d0 = np.abs((W[vs] - p0) @ n0); d1 = np.abs((W[vs] - p1) @ n1)
        if np.any(np.minimum(d0, d1) > 0.05): continue
        # 端の三角形（細いものも含め、端の平面にのるもの）
        on0 = np.abs((W[T] - p0) @ n0).max(1) < 0.05
        cap0 = on0 & (dots < 0) | (on0 & ~good)
        nxt = {}
        for (x, y), t in he.items():
            if cap0[t] and not cap0[he[(y, x)]]: nxt.setdefault(x, []).append(y)
        if not nxt or any(len(v) != 1 for v in nxt.values()): continue
        loops = []; left = set(nxt); bad = False
        while left:
            s0 = left.pop(); lp = [s0]; x = nxt[s0][0]
            while x != s0:
                lp.append(x); left.discard(x); x = nxt[x][0]
                if len(lp) > len(nxt) + 1: bad = True; break
            if bad: break
            loops.append(lp)
        if bad: continue
        X = np.cross(d, [1., 0, 0]) if abs(d[0]) < 0.9 else np.cross(d, [0, 1., 0]); X /= np.linalg.norm(X); Y = np.cross(d, X)
        B = W[loops[0][0]]
        tS = ((p0 - B) @ n0) / (d @ n0); S = B + tS * d
        tE = ((p1 - B) @ n1) / (d @ n1); E = B + tE * d
        Lh = (E - S) @ d
        if Lh < 0.5: continue
        to2 = lambda p: np.array([(p - S) @ X, (p - S) @ Y])
        L2 = [np.array([to2(W[v]) for v in lp]) for lp in loops]
        sa = [0.5 * (Q[:, 0] * np.roll(Q[:, 1], -1) - np.roll(Q[:, 0], -1) * Q[:, 1]).sum() for Q in L2]
        k0 = int(np.argmax(np.abs(sa)))
        runs0 = _arc_runs(L2[k0])

        def make(S_, Lh_):
            to3_ = lambda q: S_ + q[0] * X + q[1] * Y
            outer = _profile(L2[k0], to3_, runs0)
            if not outer.IsClosed: return None
            for k_ in range(2):
                if k_: outer.Reverse()                       # 押し出しは輪郭の面の法線の向き（輪郭の回る向きで決まる）
                e_ = r.Extrusion.Create(outer, Lh_, True)
                if e_ is None or not e_.IsValid: continue
                ps_ = np.array([e_.PathStart.X, e_.PathStart.Y, e_.PathStart.Z]); pe_ = np.array([e_.PathEnd.X, e_.PathEnd.Y, e_.PathEnd.Z])
                if (pe_ - ps_) @ d > 0: return e_, ps_, pe_
            return None
        to3 = lambda q: S + q[0] * X + q[1] * Y
        try:
            got = make(S, Lh)
            if got is None: continue
            e, ps, pe = got
            # 道の始まりは輪郭の面のどこか（Rhino が決める）。斜めの端の面がそこを通るように、輪郭の面を d に沿って動かす
            t0 = ((p0 - ps) @ n0) / (d @ n0); P0 = ps + t0 * d
            t1 = ((p1 - P0) @ n1) / (d @ n1)
            if abs(t0) > 1e-6:
                S = S + t0 * d; got = make(S, t1)
                if got is None: continue
                e, ps, pe = got
            if np.linalg.norm(ps - P0) > 0.01 or abs((pe - p1) @ n1) > 0.01: continue
            to3 = lambda q: S + q[0] * X + q[1] * Y
            pp = e.GetProfilePlane(0.0)
            O_ = np.array([pp.Origin.X, pp.Origin.Y, pp.Origin.Z])
            X_ = np.array([pp.XAxis.X, pp.XAxis.Y, pp.XAxis.Z]); Y_ = np.array([pp.YAxis.X, pp.YAxis.Y, pp.YAxis.Z])
            Z_ = np.cross(X_, Y_)
            if Z_ @ d < 0: Z_ = -Z_
            okh = True
            for k, Q in enumerate(L2):
                if k == k0: continue
                to3h = lambda q: np.array([(to3(q) - O_) @ X_, (to3(q) - O_) @ Y_, 0.0])
                if not e.AddInnerProfile(_profile(Q, to3h, _arc_runs(Q))): okh = False; break
            if not okh or not e.IsValid: continue
            m0 = -n0 if abs(n0 @ d) < 1 - 1e-9 else None
            m1 = n1 if abs(n1 @ d) < 1 - 1e-9 else None
            if m0 is not None or m1 is not None:
                loc = lambda v: (v @ X_, v @ Y_, v @ Z_)
                e = set_miter(e, None if m0 is None else loc(m0), None if m1 is None else loc(m1))
                if e is None or not e.IsValid: continue
            return e
        except Exception:
            continue
    return None


def cap_holes(W, T):
    """開いた立体の、平らな縁の穴に蓋をする（三角形に分けて）。平らな板（全体が一つの平面）や、
    平らでない穴があれば None"""
    W = np.asarray(W, float); T = orient_open(T)
    P = W[np.unique(T.ravel())]; c0 = P.mean(0); _, sv, vt = np.linalg.svd(P - c0, full_matrices=False)
    if np.abs((P - c0) @ vt[2]).max() < 0.5: return None
    de = set()
    for a, b, c in T:
        for e in ((a, b), (b, c), (c, a)): de.add(e)
    nxt = {}
    for (x, y) in de:
        if (y, x) not in de: nxt.setdefault(y, []).append(x)       # 穴の縁を逆向きにたどる（蓋の向き）
    if any(len(v) != 1 for v in nxt.values()): return None
    left = set(nxt); new = []
    import mapbox_earcut as earcut
    while left:
        s0 = left.pop(); lp = [s0]; x = nxt[s0][0]
        while x != s0:
            lp.append(x); left.discard(x); x = nxt[x][0]
            if len(lp) > len(nxt) + 1: return None
        Q = W[lp]; q0 = Q.mean(0); _, sv, vt = np.linalg.svd(Q - q0, full_matrices=False)
        if np.abs((Q - q0) @ vt[2]).max() > 0.5: return None
        q2 = np.c_[(Q - q0) @ vt[0], (Q - q0) @ vt[1]]
        tri = earcut.triangulate_float64(q2, np.array([len(q2)], dtype=np.uint32)).reshape(-1, 3)
        if len(tri) != len(lp) - 2: return None
        # 向き：縁の向き（lp）に合わせる
        sa = 0.5 * (q2[:, 0] * np.roll(q2[:, 1], -1) - np.roll(q2[:, 0], -1) * q2[:, 1]).sum()
        for t in tri:
            a, b, c = (lp[i] for i in t)
            ta = q2[t[0]]; tb = q2[t[1]]; tc = q2[t[2]]
            ar = (tb[0] - ta[0]) * (tc[1] - ta[1]) - (tb[1] - ta[1]) * (tc[0] - ta[0])
            new.append((a, b, c) if (ar > 0) == (sa > 0) else (a, c, b))
    return np.vstack([T, np.array(new)]) if new else None


def to_solids(W, T, sheet=('down', 10.0), _depth=0):
    """閉じた立体に → [(ジオメトリ, 種類)]。種類：'curved'（曲面あり）・'planar'・'mesh'（閉じたメッシュのまま）
    閉じていない面は sheet の決まりで厚みをつける。二つより多くの面が集まる辺は、立体ごとに分ける。"""
    W = np.asarray(W, float); T = np.asarray(T, int)
    T = drop_doubles(T)
    if len(T) == 0: return []
    P = W[np.unique(T.ravel())]
    if np.sort(np.ptp(P, axis=0))[1] < 0.1: return []      # 太さの無い針（削った残り、二方向とも 0.1 mm 未満）は捨てる
    try:
        ex = as_extrusion(W, T)
        if ex is not None: return [(ex, 'extrusion')]
    except Fail:
        pass
    b, info = solid_from_mesh(W, T)
    if b is not None:
        # 自由な形（クスノキ・地形・網の鉢など、三角形ごとに面になる）は閉じたメッシュのまま
        if len(b.Faces) > 400 and len(T) / len(b.Faces) < 3: return [(submesh(W, T), 'mesh')]
        return [(b, info.split('(')[0])]
    if info.startswith('not manifold') and _depth < 2:
        To = orient_loose(T)
        for Tt in (To, To[:, ::-1]):
            try:
                W2, T2 = split_nonmanifold(W, Tt)
            except Fail:
                continue
            b, info2 = solid_from_mesh(W2, T2)
            if b is not None: return [(b, info2.split('(')[0])]
            if not info2.startswith('not manifold'): break
        # manifold3d で一つながりの多様体に直す（重なった面・触れる辺）。頂点はもとの座標に戻す
        for Wm, Tm in via_manifold(W, T):
            b, info2 = solid_from_mesh(Wm, Tm)
            if b is not None: return [(b, info2.split('(')[0])]
        sh = shells(T)
        if len(sh) > 1:
            out = []
            for T1 in sh: out += to_solids(W, T1, None, _depth + 1)
            return out
    if info.startswith('open') and _depth < 3:
        try: Tc = cap_holes(W, T)
        except Fail: Tc = None
        if Tc is not None:
            b, info2 = solid_from_mesh(W, Tc)
            if b is not None: return [(b, info2.split('(')[0])]
            return [(submesh(W, Tc), 'mesh')]
    if info.startswith('open') and _depth < 3:
        if sheet is None: sheet = ('down', 10.0)
        try:
            W2, T2 = thicken(W, T, *sheet)
        except Fail:
            W2 = None
        if W2 is not None:
            out = to_solids(W2, T2, None, _depth + 1)
            return out
    return [(submesh(W, T), 'mesh')]


def submesh(W, T):
    mm = r.Mesh(); ids = {}
    for v in np.unique(np.asarray(T).ravel()): ids[v] = len(ids); mm.Vertices.Add(*map(float, W[v]))
    for a, b, c in T: mm.Faces.AddFace(ids[a], ids[b], ids[c])
    mm.Normals.ComputeNormals(); mm.Compact(); return mm


def segment_curved(W, rverts, rn, rp, ra, adj):
    """細かく分けられた曲面の片（平らな面）を、円柱・球ごとにまとめる → [(kind, prm, [面])]
    なめらかにつながる片の集まりごとに、小さな組から円柱・球を当てはめ、その形にのる片を一番多く集める候補を選ぶ（RANSAC 風）"""
    nr = len(rverts)
    ang = lambda x, y: math.acos(max(-1.0, min(1.0, float(rn[x] @ rn[y]))))
    sm = {x: [y for y in adj.get(x, ()) if ANG_LO < ang(x, y) < ANG_HI] for x in range(nr)}
    seen = np.zeros(nr, bool); out = []
    flat_v = np.concatenate(rverts); off = np.r_[0, np.cumsum([len(v) for v in rverts])]
    for s0 in range(nr):
        if seen[s0] or not sm[s0]: continue
        comp = []; st = [s0]; seen[s0] = True
        while st:
            x = st.pop(); comp.append(x)
            for y in sm[x]:
                if not seen[y]: seen[y] = True; st.append(y)
        if len(comp) < 3: continue
        # まず全体を一つの形で
        pts = W[np.unique(np.concatenate([rverts[g] for g in comp]))]
        whole = None
        for kind in ('cyl', 'sph', 'tor'):
            f = fit_cyl(pts, rn[comp], ra[comp]) if kind == 'cyl' else (fit_sph(pts) if kind == 'sph' else fit_tor(pts))
            if f and f[0] < FIT_TOL:
                G = _consistent(kind, f[1], comp[0], set(comp), W, rverts, rn, rp, ra, sm)
                if len(G) == len(comp): whole = (kind, f[1], comp); break
        if whole is not None:
            if max(ang(x, y) for x in comp for y in comp) >= math.radians(8): out.append(whole)
            continue
        rest = set(comp); found = []
        for _ in range(64):
            if len(rest) < 3: break
            cands = []
            pool = sorted(rest, key=lambda x: -ra[x])
            step = max(1, len(pool) // 24)
            for x in pool[::step]:
                nb = [y for y in sm[x] if y in rest]
                if len(nb) < 1: continue
                trio = [x] + nb[:2]
                if len(trio) < 3:
                    nb2 = [z for z in sm[nb[0]] if z in rest and z != x]
                    if not nb2: continue
                    trio.append(nb2[0])
                pts = W[np.unique(np.concatenate([rverts[g] for g in trio]))]
                f = fit_cyl(pts, rn[trio], ra[trio])
                if f and f[0] < FIT_TOL: cands.append(('cyl', f[1], x))
                f = fit_sph(pts)
                if f and f[0] < FIT_TOL: cands.append(('sph', f[1], x))
            best = None
            for kind, prm, x in cands:
                G = _consistent(kind, prm, x, rest, W, rverts, rn, rp, ra, sm)
                if len(G) < 3: continue
                # 当てはめ直して、もう一度
                pts = W[np.unique(np.concatenate([rverts[g] for g in G]))]
                f = fit_cyl(pts, rn[G], ra[G]) if kind == 'cyl' else fit_sph(pts)
                if not f or f[0] >= FIT_TOL: continue
                G2 = _consistent(kind, f[1], x, rest, W, rverts, rn, rp, ra, sm)
                if len(G2) >= len(G):
                    pts = W[np.unique(np.concatenate([rverts[g] for g in G2]))]
                    f2 = fit_cyl(pts, rn[G2], ra[G2]) if kind == 'cyl' else fit_sph(pts)
                    if f2 and f2[0] < FIT_TOL: G, f = G2, f2
                sc = ra[G].sum()
                if best is None or sc > best[0]: best = (sc, kind, f[1], G)
            if best is None: break
            _, kind, prm, G = best
            turn = max(ang(x, y) for x in G for y in G)
            if turn < math.radians(8):
                for g in G: rest.discard(g)
                continue
            found.append([kind, prm, G])
            for g in G: rest.discard(g)
        # となりあう同じ太さの円柱を円環にまとめる（弧に沿って曲がる丸太・樋）
        merged = True
        while merged:
            merged = False
            for i in range(len(found)):
                if found[i][0] not in ('cyl', 'tor'): continue
                Gi = set(found[i][2])
                for j in range(len(found)):
                    if j == i or found[j][0] not in ('cyl', 'tor'): continue
                    if not any(z in Gi for g in found[j][2] for z in sm[g]): continue
                    U = list(Gi | set(found[j][2]))
                    f = fit_tor(W[np.unique(np.concatenate([rverts[g] for g in U]))])
                    if not f or f[0] >= FIT_TOL: continue
                    G = _consistent('tor', f[1], U[0], set(U), W, rverts, rn, rp, ra, sm)
                    if len(G) != len(U): continue
                    found[i] = ['tor', f[1], U]; del found[j]; merged = True; break
                if merged: break
        out += [tuple(x) for x in found]
    return out


def _consistent(kind, prm, x0, rest, W, rverts, rn, rp, ra, sm):
    """形 prm にのる片（頂点のずれ・法線の向き）のうち、x0 とつながるもの"""
    ok = set()
    for g in rest:
        P = W[rverts[g]]
        if kind == 'cyl':
            c, a, R = prm; q = P - c; rad = q - np.outer(q @ a, a)
            if np.abs(np.linalg.norm(rad, axis=1) - R).max() >= FIT_TOL: continue
            m = rp[g] - c; m = m - (m @ a) * a; nm = np.linalg.norm(m)
            if nm < 1e-9 or abs(rn[g] @ m) / nm < math.cos(math.radians(6)): continue
        elif kind == 'tor':
            Tg = Tor(*prm, 1)
            if max(Tg.dist(p) for p in P) >= FIT_TOL: continue
            rho, h, rad = Tg._rh(rp[g])
            if rho < 1e-9: continue
            x, y = rho - Tg.R, h - Tg.h0
            m = rad / rho * (x / Tg.A ** 2) + Tg.a * (y / Tg.B ** 2); nm = np.linalg.norm(m)
            if nm < 1e-12 or abs(rn[g] @ m) / nm < math.cos(math.radians(6)): continue
        else:
            c, R = prm
            if np.abs(np.linalg.norm(P - c, axis=1) - R).max() >= FIT_TOL: continue
            m = rp[g] - c; nm = np.linalg.norm(m)
            if nm < 1e-9 or abs(rn[g] @ m) / nm < math.cos(math.radians(6)): continue
        ok.add(g)
    if x0 not in ok: return []
    G = []; st = [x0]; vis = {x0}
    while st:
        y = st.pop(); G.append(y)
        for z in sm[y]:
            if z in ok and z not in vis: vis.add(z); st.append(z)
    return G


def split_pinched(W, T):
    """一つの頂点のまわりの三角形が、辺でつながる扇に分かれていたら（立体が頂点で自分に触れる）、扇ごとに頂点を写す"""
    vt = {}
    for t, tri in enumerate(T):
        for v in tri: vt.setdefault(int(v), []).append(t)
    Wl = None; T2 = T
    for v, ts in vt.items():
        if len(ts) < 3: continue
        par = {t: t for t in ts}
        def f(x):
            while par[x] != x: par[x] = par[par[x]]; x = par[x]
            return x
        ed = {}
        for t in ts:
            for u in T[t]:
                if u != v: ed.setdefault(int(u), []).append(t)
        for u, tt in ed.items():
            for k in range(1, len(tt)): par[f(tt[k])] = f(tt[0])
        groups = {}
        for t in ts: groups.setdefault(f(t), []).append(t)
        if len(groups) < 2: continue
        if Wl is None: Wl = list(W); T2 = T.copy()
        for g in list(groups.values())[1:]:
            nv = len(Wl); Wl.append(np.array(W[v], float))
            for t in g: T2[t] = [nv if x == v else x for x in T2[t]]
    return (W, T) if Wl is None else (np.array(Wl), T2)


def _build(W, T, curved, snap=True):
    T = orient(T)
    W, T = split_pinched(np.asarray(W, float), T)
    he = topology(W, T)
    a, b, c = W[T[:, 0]], W[T[:, 1]], W[T[:, 2]]
    Nr = np.cross(b - a, c - a); ar2 = np.linalg.norm(Nr, axis=1)
    vol = (np.einsum('ij,ij->i', a, np.cross(b, c))).sum() / 6
    if vol < 0:
        T = T[:, ::-1].copy(); he = topology(W, T)
        a, b, c = W[T[:, 0]], W[T[:, 1]], W[T[:, 2]]; Nr = np.cross(b - a, c - a); ar2 = np.linalg.norm(Nr, axis=1)
    area = ar2 / 2
    N = Nr / np.maximum(ar2, 1e-30)[:, None]
    reg, regs, nb = planar_regions(W, T, N, area, he)
    regs = merge_small(W, T, N, area, reg, regs, nb)
    nr = len(regs)
    # 面ごとの平面
    rn, rp, ra = [], [], []
    for mem in regs:
        mem = np.array(mem); s = (N[mem] * area[mem, None]).sum(0); A_ = area[mem].sum()
        if np.linalg.norm(s) < 1e-12: s = N[mem[0]] if np.linalg.norm(N[mem[0]]) > 0 else np.array([0, 0, 1.])
        n = s / np.linalg.norm(s)
        vs = np.unique(T[mem].ravel()); p = W[vs].mean(0)
        rn.append(n); rp.append(p); ra.append(A_)
    rn = np.array(rn); ra = np.array(ra)
    rverts = [np.unique(T[np.array(m)].ravel()) for m in regs]
    # となりの面
    adj = {}
    for (x, y), t in he.items():
        u = he[(y, x)]
        if reg[t] != reg[u]: adj.setdefault(reg[t], set()).add(reg[u])
    # ---- 曲面のまとまり
    srf_of = [None] * nr          # 面（Plane・Cyl・Sph）
    group = list(range(nr))       # 面の番号（曲面はまとめた番号）
    if curved:
        for kind, prm, G in segment_curved(W, rverts, rn, rp, ra, adj):
            gid = G[0]
            for g in G: group[g] = gid
            cen = np.array([rp[g] for g in G])
            if kind == 'cyl':
                cc, ax, R = prm
                rad = cen - cc - ((cen - cc) @ ax)[:, None] * ax
                sgn = 1 if (np.einsum('ij,ij->i', rad, rn[G]) * ra[G]).sum() > 0 else -1
                srf_of[gid] = Cyl(cc, ax, R, sgn)
            elif kind == 'tor':
                cc, ax, R, A_, B_, h0 = prm
                q = cen - cc; h = q @ ax; rad = q - h[:, None] * ax
                tc = cc + rad / np.linalg.norm(rad, axis=1)[:, None] * R + h0 * ax
                sgn = 1 if (np.einsum('ij,ij->i', cen - tc, rn[G]) * ra[G]).sum() > 0 else -1
                srf_of[gid] = Tor(cc, ax, R, A_, B_, h0, sgn)
            else:
                cc, R = prm
                sgn = 1 if (np.einsum('ij,ij->i', cen - cc, rn[G]) * ra[G]).sum() > 0 else -1
                # 軸はドームの頂の向き。極はメッシュの頂点に合わせる（面の境に来るように）
                d = (cen * ra[G, None]).sum(0) / ra[G].sum() - cc
                d = d if np.linalg.norm(d) > 1e-6 * R else np.array([0, 0, 1.])
                vs = np.unique(np.concatenate([rverts[g] for g in G])); q = W[vs] - cc
                k = int(np.argmax(q @ d / np.maximum(np.linalg.norm(q, axis=1), 1e-12)))
                srf_of[gid] = Sph(cc, R, q[k], sgn)
    for g in range(nr):
        if group[g] == g and srf_of[g] is None: srf_of[g] = Plane(rn[g], rp[g])
    # ---- 半周を超える曲面を分ける（面の境で）
    face_of_reg = {}
    faces = []                    # [(surface, [regions])]
    members = {}
    for g in range(nr): members.setdefault(group[g], []).append(g)
    for gid, G in members.items():
        s = srf_of[gid]
        if s.kind == 'plane':
            face_of_reg[G[0]] = len(faces); faces.append((s, G)); continue
        import copy
        def bins_of(angs):
            srt = np.sort(angs); gaps = np.diff(np.r_[srt, srt[0] + 2 * math.pi])
            k = int(np.argmax(gaps)); start = srt[(k + 1) % len(srt)]
            rel = (angs - start) % (2 * math.pi); span = rel.max()
            npc = max(1, int(math.ceil(span / SPLIT)))
            bins = np.minimum((rel / (span + 1e-9) * npc).astype(int), npc - 1) if npc > 1 else np.zeros(len(angs), int)
            return bins, start, rel
        au = np.array([s.ang(rp[g]) for g in G])
        bu, su, relu = bins_of(au)
        if s.kind == 'tor':
            av = np.array([s.phi(rp[g]) for g in G]); bv, sv, relv = bins_of(av)
        else:
            bv = np.zeros(len(G), int); relv = np.zeros(len(G)); sv = 0.0
        for key in sorted(set(zip(bu, bv))):
            sel = [G[i] for i in range(len(G)) if (bu[i], bv[i]) == key]
            rest = set(sel)
            while rest:
                x = rest.pop(); comp = [x]; st = [x]
                while st:
                    y = st.pop()
                    for z in adj.get(y, ()):
                        if z in rest: rest.discard(z); comp.append(z); st.append(z)
                s2 = copy.copy(s)
                idx = [G.index(g) for g in comp]
                s2.uc = _wrap(s2.sgn * (su + np.mean(relu[idx])), 0.0)
                if s.kind == 'tor': s2.set_vc(_wrap(sv + np.mean(relv[idx]), 0.0))
                for g in comp: face_of_reg[g] = len(faces)
                faces.append((s2, comp))
    fot = np.array([face_of_reg[reg[t]] for t in range(len(T))])
    nf = len(faces)
    # ---- 境のループと辺
    bnd = {}   # 面 → {a: [(a,b)]}
    for (x, y), t in he.items():
        u = he[(y, x)]
        if fot[t] != fot[u]: bnd.setdefault(fot[t], {}).setdefault(x, []).append(y)
    vfaces = {}
    for (x, y), t in he.items(): vfaces.setdefault(x, set()).add(fot[t])
    corner = {v for v, fs in vfaces.items() if len(fs) >= 3}

    def loops_of(f):
        out = []; nxt = {a: list(bs) for a, bs in bnd.get(f, {}).items()}
        while any(nxt.values()):
            a0 = next(a for a, bs in nxt.items() if bs)
            lp = [a0]; a = a0
            while True:
                bs = nxt[a]
                if len(bs) > 1:
                    # つまんだ所：入ってきた向きから一番右へ曲がる辺
                    prev = W[lp[-2]] if len(lp) > 1 else None
                    if prev is not None:
                        s = faces[f][0]; nrm = s.n if s.kind == 'plane' else np.cross(W[bs[0]] - W[a], W[bs[1]] - W[a])
                        din = W[a] - prev
                        def turn(bb):
                            dv = W[bb] - W[a]
                            return math.atan2(np.cross(din, dv) @ nrm, din @ dv)
                        bs.sort(key=turn)
                b_ = bs.pop(0)
                if b_ == a0: break
                lp.append(b_); a = b_
                if len(lp) > 100000: raise Fail('loop')
            out.append(lp)
        return out

    L = {f: loops_of(f) for f in range(nf)}
    for f, lps in L.items():
        for lp in lps:
            ks = [i for i, v in enumerate(lp) if v in corner]
            if not ks:
                corner.add(lp[0]); corner.add(lp[len(lp) // 2])
                if len(lp) >= 6: corner.add(lp[len(lp) // 4]); corner.add(lp[3 * len(lp) // 4])
            elif len(ks) == 1:                         # 角が一つだけ：一周する辺にならないよう、反対側にも角
                corner.add(lp[(ks[0] + len(lp) // 2) % len(lp)])
    # 面が変わる所も角
    for f, lps in L.items():
        for lp in lps:
            n = len(lp)
            for i in range(n):
                a_, b_ = lp[i], lp[(i + 1) % n]; c_ = lp[(i + 2) % n]
                fa = fot[he[(b_, a_)]]; fb = fot[he[(c_, b_)]]
                if fa != fb: corner.add(b_)
    # ---- 頂点を面に合わせる
    P = {}
    for v, fs in vfaces.items():
        if len(fs) < 2: continue
        x = W[v].copy(); ss = [faces[f][0] for f in fs]
        pl = [s for s in ss if s.kind == 'plane']
        if len(pl) == len(ss) and len(pl) >= 3:
            A = np.array([s.n for s in pl]); bb = np.array([s.n @ s.o for s in pl])
            lam = 1e-6
            x = np.linalg.solve(A.T @ A + lam * np.eye(3), A.T @ bb + lam * W[v])
        else:
            for _ in range(30):
                for s in ss: x = s.proj(x)
        if not snap or np.linalg.norm(x - W[v]) > 2.0: x = W[v].copy()
        P[v] = x
    # ---- 辺（鎖）
    chains = {}     # 鍵 → 辺の情報
    edge_of_he = {}
    E = []          # dict(v=(a,b), pts=[...], curve=..., faces)
    face_loops = []

    def make_edge(seq, fA, fB):
        pts = np.array([P[v] for v in seq])
        sA, sB = faces[fA][0], faces[fB][0]
        e = dict(v=(seq[0], seq[-1]), seq=seq, pts=pts, faces=(fA, fB))
        d = pts[-1] - pts[0]; L_ = np.linalg.norm(d)
        if L_ > 1e-9 and len(pts) > 2:
            dd = d / L_; off = pts - pts[0]; dev = np.linalg.norm(off - np.outer(off @ dd, dd), axis=1).max()
        else: dev = 0.0
        if len(pts) == 2 or dev < EPS_LINE:
            e['type'] = 'line'
        else:
            e['type'] = 'poly'
            con = conic(pts, sA, sB) if (sA.kind != 'plane' or sB.kind != 'plane') and _smooth_chain(pts) else None
            if con is not None: e['type'] = 'conic'; e['con'] = con
        return e

    def conic(pts, sA, sB):
        c0 = pts.mean(0); u_, s_, vt = np.linalg.svd(pts - c0)
        nrm = vt[2]
        if np.abs((pts - c0) @ nrm).max() > EPS_LINE: return None
        cyl = sA if sA.kind == 'cyl' else (sB if sB.kind == 'cyl' else None)
        sph = sA if sA.kind == 'sph' else (sB if sB.kind == 'sph' else None)
        pln = sA if sA.kind == 'plane' else (sB if sB.kind == 'plane' else None)
        plane_n = nrm
        if pln is not None and abs(pln.n @ nrm) > 0.999:      # 平らな面があれば、その平面で（頂点はその上にある）
            plane_n = pln.n; c0 = pln.proj(c0)
            vt = np.array([pln.x, pln.y, pln.n])
        if cyl is not None:
            ca = abs(plane_n @ cyl.a)
            if ca < 1e-6: return None
            # 楕円：中心＝軸と平面の交点、短軸＝R（軸と平面の両方に直角）、長軸＝R/ca
            t = ((c0 - cyl.c) @ plane_n) / (cyl.a @ plane_n); C = cyl.c + t * cyl.a
            minor = np.cross(cyl.a, plane_n)
            if np.linalg.norm(minor) < 1e-9:
                U = cyl.X; V = cyl.Y; a_ = b_ = cyl.R; nn = cyl.a
            else:
                V = minor / np.linalg.norm(minor); U = np.cross(V, plane_n); U /= np.linalg.norm(U)
                a_ = cyl.R / ca; b_ = cyl.R
        else:
            if sph is not None:
                t = (sph.c - c0) @ plane_n; C = sph.c - t * plane_n; rr = sph.R ** 2 - t ** 2
                if rr <= 0: return None
                a_ = b_ = math.sqrt(rr)
            else:
                pl = sA if sA.kind == 'plane' else sB
                q = np.c_[(pts - c0) @ vt[0], (pts - c0) @ vt[1]]
                c2, R = fit_circle2(q)
                C = c0 + c2[0] * vt[0] + c2[1] * vt[1]; a_ = b_ = R
            U = vt[0]; V = np.cross(plane_n, U)
        if max(a_, b_) > 20 * min(a_, b_) or max(a_, b_) > MAX_R: return None
        q = pts - C; x = q @ U / a_; y = q @ V / b_
        if np.abs(np.hypot(x, y) - 1).max() * max(a_, b_) > 0.05: return None
        if np.abs(q @ plane_n).max() > 0.05: return None
        ph = np.unwrap(np.arctan2(y, x))
        if not (np.all(np.diff(ph) > 0) or np.all(np.diff(ph) < 0)): return None
        Pf = lambda t: C + a_ * math.cos(t) * U + b_ * math.sin(t) * V
        dPf = lambda t: -a_ * math.sin(t) * U + b_ * math.cos(t) * V
        # 弧は頂点のあいだを通る：弦ごとに、弧の中ほどと弦の中点の差が弦の矢高（の 1.5 倍＋0.1 mm）を超えない
        for k in range(len(pts) - 1):
            c_ = np.linalg.norm(pts[k + 1] - pts[k]); mid = Pf((ph[k] + ph[k + 1]) / 2)
            sag = c_ * c_ / (8 * min(a_, b_))
            if np.linalg.norm(mid - (pts[k] + pts[k + 1]) / 2) > 1.5 * sag + 0.1 or abs(ph[k + 1] - ph[k]) > math.radians(45): return None
        return dict(P=Pf, dP=dPf, t0=float(ph[0]), t1=float(ph[-1]), C=C, U=U, V=V, a=a_, b=b_, n=plane_n)

    for f in range(nf):
        flp = []
        for lp in L[f]:
            n = len(lp)
            ks = [i for i in range(n) if lp[i] in corner]
            if not ks: raise Fail('no corner')
            segs = []
            for j, k0 in enumerate(ks):
                k1 = ks[(j + 1) % len(ks)]
                seq = [lp[(k0 + i) % n] for i in range(((k1 - k0) % n) or n) ] + [lp[k1]]
                a_, b_ = seq[0], seq[1]
                key = (min(a_, b_), max(a_, b_))
                if key in edge_of_he:
                    ei = edge_of_he[key]; rev = int(not (E[ei]['seq'][0] == seq[0] and E[ei]['seq'][1] == seq[1]))
                    if rev and E[ei]['seq'][::-1] != seq: raise Fail('chain mismatch')
                    if not rev and E[ei]['seq'] != seq: raise Fail('chain mismatch2')
                else:
                    fB = fot[he[(b_, a_)]]
                    e = make_edge(seq, f, fB); E.append(e); ei = len(E) - 1
                    for x, y in zip(seq, seq[1:]): edge_of_he[(min(x, y), max(x, y))] = ei
                    rev = 0
                segs.append((ei, rev, seq))
            flp.append(segs)
        face_loops.append(flp)
    # ---- 書き出し
    C2, C3, S = [], [], []
    # 線・折れ線の辺は、続いて作った辺（端がつながるもの）と一本の 3 次元の折れ線を分けあう（ファイルを小さく）
    bp, bt, pend = [], [], []

    def flush3():
        if len(bp) >= 2:
            C3.append(O.polyline(bp, 3, bt)); ci = len(C3) - 1
            for e_ in pend: e_['c3i'] = ci
        bp.clear(); bt.clear(); pend.clear()
    for e in E:
        typ = e['type']; pts = e['pts']
        if typ == 'conic':
            flush3()
            cn = e['con']; C3.append(arc_nurbs(cn['P'], cn['C'], cn['t0'], cn['t1'], 3, ends=(pts[0], pts[-1])))
            e['dom'] = (cn['t0'], cn['t1']) if cn['t1'] > cn['t0'] else (-cn['t0'], -cn['t1'])
            e['sample'] = lambda t, cn=cn: cn['P'](cn['t0'] + (cn['t1'] - cn['t0']) * t)
            e['c3i'] = len(C3) - 1
            continue
        Q = [pts[0], pts[-1]] if typ == 'line' else list(pts)
        if bp and tuple(bp[-1]) != tuple(map(float, Q[0])): flush3()
        if len(bp) > 2000: flush3()
        if not bp: bp.append(tuple(map(float, Q[0]))); bt.append(0.0)
        t0 = bt[-1]
        for x in Q[1:]:
            x = tuple(map(float, x))
            bt.append(bt[-1] + max(1e-9, math.dist(x, bp[-1]))); bp.append(x)
        e['dom'] = (t0, bt[-1]); pend.append(e)
        if typ == 'line': e['sample'] = lambda t, p0=pts[0], p1=pts[-1]: p0 + (p1 - p0) * t
        else:
            ts = [0.0]
            for x, y in zip(pts, pts[1:]): ts.append(ts[-1] + float(np.linalg.norm(y - x)))
            e['sample'] = lambda t, pts=pts, ts=np.array(ts): _pl_eval(pts, ts, t)
    flush3()
    Vlist = sorted({v for e in E for v in e['v']})
    vid = {v: i for i, v in enumerate(Vlist)}
    vei = [[] for _ in Vlist]
    Erec = []
    for k, e in enumerate(E):
        a_, b_ = e['v']
        vei[vid[a_]].append(k)
        if b_ != a_: vei[vid[b_]].append(k)
        e['ti'] = []
    # ループの向き（flip した辺）を直す
    for flp in face_loops:
        for segs in flp:
            for j, (ei, rev, seq) in enumerate(segs):
                segs[j] = (ei, int(not (E[ei]['seq'][0] == seq[0] and E[ei]['seq'][1] == seq[1])), seq)
    Trec, Lrec, Frec = [], [], []
    for f, (s, G) in enumerate(faces):
        loops_uv = []
        for segs in face_loops[f]:
            luv = []
            ref = s.uc if s.kind != 'plane' else None
            for ei, rev, seq in segs:
                e = E[ei]
                uvs = trim_uv(s, e, rev, ref)
                luv.append((ei, rev, seq, uvs))
            loops_uv.append(luv)
        # 定義域
        allp = np.array([p for luv in loops_uv for (_, _, _, uvs) in luv for p in uvs])
        lo = allp.min(0); hi = allp.max(0); pad = np.full(2, 1.0) if s.kind == 'plane' else np.maximum((hi - lo) * 1e-6, 1e-9)
        dom = ((float(lo[0] - pad[0]), float(hi[0] + pad[0])), (float(lo[1] - pad[1]), float(hi[1] + pad[1])))
        if hasattr(s, 'vdom'): dom = (dom[0], tuple(s.vdom))
        if s.kind == 'cyl':
            s.t0 = 0.0
        S.append(s.surface(dom)); si = len(S) - 1
        lis = []
        # 外側のループ（uv で左回り、面積最大）を先に
        def sarea(luv):
            pp = np.array([p for (_, _, _, uvs) in luv for p in uvs[:-1]])
            x, y = pp[:, 0], pp[:, 1]; return 0.5 * (x * np.roll(y, -1) - np.roll(x, -1) * y).sum()
        areas = [sarea(l) for l in loops_uv]
        order = sorted(range(len(loops_uv)), key=lambda i: -areas[i])
        if areas[order[0]] <= 0: raise Fail('outer loop orientation')
        for kk, li0 in enumerate(order):
            luv = loops_uv[li0]
            if kk > 0 and areas[li0] > 0: raise Fail('two outer loops')
            li = len(Lrec); tis = []
            # 一つのループの線・折れ線のトリムは一本の 2 次元の折れ線を分けあう（ファイルを小さく。トリムは定義域の一部を使う）
            bp, bt, pend = [], [], []

            def flush():
                if len(bp) >= 2:
                    C2.append(O.polyline(bp, 2, bt)); ci = len(C2) - 1
                    for t_ in pend: Trec[t_][0] = ci
                bp.clear(); bt.clear(); pend.clear()

            def add(pts):
                if bp and (bp[-1][0] != pts[0][0] or bp[-1][1] != pts[0][1]): flush()
                if not bp: bp.append(tuple(pts[0])); bt.append(0.0)
                t0_ = bt[-1]
                for x in pts[1:]:
                    bt.append(bt[-1] + max(1e-12, math.hypot(x[0] - bp[-1][0], x[1] - bp[-1][1]))); bp.append(tuple(x))
                return (t0_, bt[-1])
            for j, (ei, rev, seq, uvs) in enumerate(luv):
                # 特異点（球の極）：前のトリムの終わりとこのトリムの始まりの u がちがう
                prev_uv = luv[j - 1][3][-1]
                if s.kind == 'sph' and abs(prev_uv[0] - uvs[0][0]) > 1e-9 and s.is_pole(P[seq[0]]):
                    p0 = prev_uv; p1 = (uvs[0][0], prev_uv[1])
                    bmin = (min(p0[0], p1[0]), p0[1]); bmax = (max(p0[0], p1[0]), p0[1])
                    ti = len(Trec)
                    Trec.append([None, add([p0, p1]), -1, (vid[seq[0]], vid[seq[0]]), 0, 4, iso_flag(bmin, bmax, dom), li])
                    pend.append(ti); tis.append(ti)
                if s.kind == 'plane' and E[ei]['type'] == 'conic':
                    flush()
                    cn = E[ei]['con']; ta, tb = (cn['t1'], cn['t0']) if rev else (cn['t0'], cn['t1'])
                    to2 = lambda p, s=s: s.uv(p)
                    C2.append(arc_nurbs(cn['P'], cn['C'], ta, tb, 2, to2, ends=(uvs[0], uvs[-1])))
                    pd2 = (min(ta, tb), max(ta, tb)) if tb > ta else (-ta, -tb)
                    arr = np.array(_LAST_CVS); ci = len(C2) - 1
                else:
                    if len(uvs) == 2 or _straight(uvs): uvs = [uvs[0], uvs[-1]]
                    pd2 = add(uvs); arr = np.array(uvs); ci = None
                ti = len(Trec)
                Trec.append([ci, pd2, ei, (vid[seq[0]], vid[seq[-1]]), rev, 2, iso_curve(arr, dom), li])
                if ci is None: pend.append(ti)
                E[ei]['ti'].append(ti); tis.append(ti)
            flush()
            Lrec.append((tis, 1 if kk == 0 else 2, f)); lis.append(li)
        Frec.append((lis, si, 0))
    # 許容差
    Vrec = []
    for v in Vlist:
        tol = max([faces[f][0].dist(P[v]) for f in vfaces[v]] + [0.0])
        Vrec.append((tuple(map(float, P[v])), vei[vid[v]], float(tol * 1.01)))
    for k, e in enumerate(E):
        if len(e['ti']) != 2: raise Fail('edge with %d trims' % len(e['ti']))
        tol = 0.0
        for t in np.linspace(0, 1, 9):
            p = e['sample'](t)
            for f in e['faces']: tol = max(tol, faces[f][0].dist(p))
        for p in e['pts']:
            for f in e['faces']: tol = max(tol, faces[f][0].dist(p))
        Erec.append((e['c3i'], e['dom'], (vid[e['v'][0]], vid[e['v'][1]]), e['ti'], float(tol * 1.01)))
    import re
    for _ in range(40):
        Tt = [(t[0], t[1], t[2], t[3], t[4], t[5], t[6], t[7]) for t in Trec]
        brep = O.write_brep(C2, C3, S, Vrec, Erec, Tt, Lrec, Frec)
        if brep is None: raise Fail('decode')
        ok, log = brep.IsValidWithLog
        fix = re.findall(r'm_T\[(\d+)\]\.m_iso = (\d+) and it should be (\d+)', log)
        if ok or not fix: break
        for k, _, should in fix: Trec[int(k)][6] = int(should)     # 境目の iso は openNURBS の判定に合わせる
    if not ok: raise Fail('invalid: ' + log[:600])
    if not brep.IsSolid: raise Fail('not solid')
    return brep


def _smooth_chain(pts):
    """曲線を細かく分けた折れ線らしいか：中の頂点の折れが 40° 以下で、向きがそろう"""
    if len(pts) < 3: return False
    d = np.diff(pts, axis=0); d = d / np.maximum(np.linalg.norm(d, axis=1), 1e-12)[:, None]
    c = np.einsum('ij,ij->i', d[:-1], d[1:])
    if np.any(c < math.cos(ANG_HI)): return False
    if len(pts) >= 4:
        cr = np.cross(d[:-1], d[1:]); nz = np.linalg.norm(cr, axis=1) > 1e-9
        if nz.sum() >= 2:
            ref = cr[nz][0]
            if np.any((cr[nz] @ ref) < 0): return False       # 折れる向きが入れかわる（S 字・コの字）
    return True


def _pl_eval(pts, ts, t):
    s = t * ts[-1]; k = min(max(int(np.searchsorted(ts, s)) - 1, 0), len(ts) - 2)
    w = (s - ts[k]) / max(ts[k + 1] - ts[k], 1e-12); return pts[k] + (pts[k + 1] - pts[k]) * w


def trim_uv(s, e, rev, ref):
    """辺 e を面 s の uv の点列に（トリムの向き：rev なら辺の逆）"""
    typ = e['type']; pts = e['pts']
    if s.kind == 'plane':
        if typ == 'conic':
            K = max(8, int(abs(e['con']['t1'] - e['con']['t0']) / math.radians(2)) + 1)
            Q = [e['sample'](t) for t in np.linspace(0, 1, K + 1)]
        else: Q = list(pts) if typ == 'poly' else [pts[0], pts[-1]]
        Q[0] = pts[0]; Q[-1] = pts[-1]
        uv = [s.uv(p) for p in Q]
        return uv[::-1] if rev else uv
    # 曲面：線（母線）・軸に直角の円はそのまま 2 点、ほかは細かく
    if typ == 'line':
        Q = [pts[0], pts[-1]]
        if s.kind == 'cyl' and abs(np.dot(pts[-1] - pts[0], s.a)) < 0.999 * np.linalg.norm(pts[-1] - pts[0]):
            Q = [e['sample'](t) for t in np.linspace(0, 1, 17)]
        if s.kind in ('sph', 'tor'): Q = [e['sample'](t) for t in np.linspace(0, 1, 17)]
    elif typ == 'conic':
        K = max(8, int(abs(e['con']['t1'] - e['con']['t0']) / math.radians(1.5)) + 1)
        Q = [e['sample'](t) for t in np.linspace(0, 1, K + 1)]
    else:
        Q = []
        for x, y in zip(pts, pts[1:]):
            for t in np.linspace(0, 1, 5)[:-1]: Q.append(x + (y - x) * t)
        Q.append(pts[-1])
    Q[0] = pts[0]; Q[-1] = pts[-1]
    if rev: Q = Q[::-1]
    out = []
    for i, p in enumerate(Q):
        if s.kind == 'sph' and s.is_pole(p):
            out.append(None); continue
        u, v = s.uv(p, ref); out.append((u, v))
    # 極の点は、となりの点の u に
    for i, q in enumerate(out):
        if q is None:
            nb = out[i - 1] if i > 0 and out[i - 1] is not None else out[i + 1]
            out[i] = (nb[0], math.copysign(math.pi / 2, s.lat(Q[i])))
    if s.kind == 'cyl' and typ == 'conic' and abs(e['con']['n'] @ s.a) > 1 - 1e-9:
        out = [out[0], out[-1]] if len(out) > 2 and _straight(out) else out
    return out


def _straight(uv):
    a = np.array(uv); d = a[-1] - a[0]; L = np.linalg.norm(d)
    if L < 1e-12: return False
    off = a - a[0]; t = (off @ d) / (L * L)
    if np.any(np.diff(t) <= 0): return False
    tol = 1e-7 * max(1.0, np.abs(a).max())
    return np.abs(off[:, 0] * d[1] - off[:, 1] * d[0]).max() / L < tol


# ---------------------------------------------------------------- 切らない面（線織面など）を辺でつないで閉じる
def _ns_data(s):
    """NurbsSurface → (次数+1 u・v、節点 u・v、制御点 [nu][nv] の (x,y,z,w))"""
    P = s.Points; nu, nv = P.CountU, P.CountV
    C = [[None] * nv for _ in range(nu)]
    for i in range(nu):
        for j in range(nv):
            p = P[i, j]; C[i][j] = (p.X, p.Y, p.Z, p.W)
    return s.OrderU, s.OrderV, list(s.KnotsU), list(s.KnotsV), C, s.IsRational


def join_untrimmed(srfs, tol=0.01):
    """切らない NURBS 面の組（境の縁どうしが重なる）→ 閉じた Brep か None"""
    data = []
    for s in srfs:
        ns = s.ToNurbsSurface() if not isinstance(s, r.NurbsSurface) else s
        if ns is None: return None
        ou, ov, ku, kv, C, rat = _ns_data(ns)
        du, dv = ns.Domain(0), ns.Domain(1)
        data.append(dict(ns=ns, ou=ou, ov=ov, ku=ku, kv=kv, C=C, rat=rat, dom=((du.T0, du.T1), (dv.T0, dv.T1))))
    def eu(c):                                   # 同次 → 普通の座標
        return np.array(c[:3]) / c[3] if c[3] not in (0, 1) else np.array(c[:3])
    sides = []                                   # (面, 辺の名前, 3 次元の曲線の点と重み, uv の始め・終わり, 向き)
    for fi, D in enumerate(data):
        (u0, u1), (v0, v1) = D['dom']; C = D['C']; nu, nv = len(C), len(C[0])
        # 左回り：S（v0、u0→u1）・E（u1、v0→v1）・N（v1、u1→u0）・W（u0、v1→v0）
        rows = {'S': ([C[i][0] for i in range(nu)], D['ou'], D['ku'], (u0, v0), (u1, v0), 4),
                'E': ([C[nu - 1][j] for j in range(nv)], D['ov'], D['kv'], (u1, v0), (u1, v1), 5),
                'N': ([C[i][nv - 1] for i in range(nu)][::-1], D['ou'], D['ku'], (u1, v1), (u0, v1), 6),
                'W': ([C[0][j] for j in range(nv)][::-1], D['ov'], D['kv'], (u0, v1), (u0, v0), 3)}
        for nm, (cv, order, knots, a, b, iso) in rows.items():
            pts = [eu(c) for c in cv]
            if np.linalg.norm(pts[0] - pts[-1]) < 1e-9 and max(np.linalg.norm(p - pts[0]) for p in pts) < 1e-9:
                return None                      # 潰れた辺（特異点）は扱わない
            sides.append(dict(f=fi, nm=nm, cv=cv, order=order, knots=knots, uv0=a, uv1=b, iso=iso,
                              p0=pts[0], p1=pts[-1], pm=_side_mid(D['ns'], a, b), rev_cv=nm in ('N', 'W')))
    # 縁の組
    used = [False] * len(sides); pairs = []
    for i, a in enumerate(sides):
        if used[i]: continue
        for j in range(i + 1, len(sides)):
            b = sides[j]
            if used[j] or b['f'] == a['f']: continue
            if np.linalg.norm(a['pm'] - b['pm']) > tol: continue
            if np.linalg.norm(a['p0'] - b['p1']) < tol and np.linalg.norm(a['p1'] - b['p0']) < tol: same = False
            elif np.linalg.norm(a['p0'] - b['p0']) < tol and np.linalg.norm(a['p1'] - b['p1']) < tol: same = True
            else: continue
            used[i] = used[j] = True; pairs.append((i, j, same)); break
        else:
            return None
    # 頂点
    Vp = []
    def vid(p):
        for k, q in enumerate(Vp):
            if np.linalg.norm(p - q) < tol: return k
        Vp.append(p); return len(Vp) - 1
    # 面の向き：辺ごとに、二つの面の実際の向き（自然な向き xor bRev）が逆
    nf = len(data); rev = [None] * nf; rev[0] = 0
    adj = [[] for _ in range(nf)]
    for i, j, same in pairs:
        a, b = sides[i], sides[j]
        adj[a['f']].append((b['f'], same)); adj[b['f']].append((a['f'], same))
    st = [0]
    while st:
        f = st.pop()
        for g, same in adj[f]:
            want = rev[f] ^ (1 if same else 0)    # 同じ向きに回るなら、片方を裏返す
            if rev[g] is None: rev[g] = want; st.append(g)
            elif rev[g] != want: return None
    if any(x is None for x in rev): return None
    # 全体の向き：いちばん大きい面の法線が外向きか（全体の重心から）
    cen = np.mean([eu(c) for D in data for row in D['C'] for c in row], axis=0)
    def fnorm(D):
        (u0, u1), (v0, v1) = D['dom']; u, v = (u0 + u1) / 2, (v0 + v1) / 2
        p = D['ns'].PointAt(u, v); n = D['ns'].NormalAt(u, v)
        return np.array([p.X, p.Y, p.Z]), np.array([n.X, n.Y, n.Z])
    score = 0.0
    for f, D in enumerate(data):
        p, n = fnorm(D); w = 1.0
        score += ((p - cen) @ n) * (-1 if rev[f] else 1)
    if score < 0: rev = [1 - x for x in rev]
    # 書き出し
    C2, C3, S, E, Tr, Lp, F = [], [], [], [], [], [], []
    edge_of = {}
    for k, (i, j, same) in enumerate(pairs):
        a = sides[i]
        cv = a['cv'][::-1] if a['rev_cv'] else a['cv']          # 面の制御点の並び（節点の向き）
        pts = [eu(c) for c in cv]; ws = [c[3] for c in cv]
        C3.append(O.nurbs(3, a['order'], a['knots'], pts, ws if any(w != 1 for w in ws) else None))
        d0, d1 = a['knots'][0], a['knots'][-1]
        v0_ = vid(pts[0]); v1_ = vid(pts[-1])
        E.append([len(C3) - 1, (d0, d1), (v0_, v1_), [], 0.0])
        edge_of[i] = (k, a['rev_cv']); edge_of[j] = (k, None)
    vei = {}
    for f, D in enumerate(data):
        S.append(D['ns']); li = len(Lp); tis = []
        for nm in ('S', 'E', 'N', 'W'):
            si = next(x for x in range(len(sides)) if sides[x]['f'] == f and sides[x]['nm'] == nm)
            sd = sides[si]
            k, rv = edge_of[si]
            e = E[k]
            # この縁の 3 次元の向きと辺の向き
            pts_side = (sd['p0'], sd['p1'])
            fwd = np.linalg.norm(pts_side[0] - Vp[e[2][0]]) < tol
            a, b = sd['uv0'], sd['uv1']
            L_ = math.hypot(b[0] - a[0], b[1] - a[1])
            C2.append(O.line(a, b, 2, 0.0, L_))
            ti = len(Tr)
            vs = (e[2][0], e[2][1]) if fwd else (e[2][1], e[2][0])
            Tr.append([len(C2) - 1, (0.0, L_), k, vs, 0 if fwd else 1, 2, sd['iso'], li])
            e[3].append(ti); tis.append(ti)
        Lp.append((tis, 1, f)); F.append(([li], f, rev[f]))
    # 許容差：二つの面の縁の点のずれ
    for k, (i, j, same) in enumerate(pairs):
        a, b = sides[i], sides[j]
        ta = _side_pts(data[a['f']]['ns'], a['uv0'], a['uv1']); tb = _side_pts(data[b['f']]['ns'], b['uv0'], b['uv1'])
        if not same: tb = tb[::-1]
        dev = max(np.min(np.linalg.norm(tb - p, axis=1)) for p in ta)
        if dev > tol: return None
        E[k][4] = float(dev * 1.01)
    for k, e in enumerate(E):
        for v in e[2]: vei.setdefault(v, []).append(k)
    V = [(tuple(map(float, Vp[k])), vei.get(k, []), tol) for k in range(len(Vp))]
    Er = [(e[0], e[1], e[2], e[3], e[4]) for e in E]
    import re
    for _ in range(10):
        b = O.write_brep(C2, C3, S, V, Er, [tuple(t) for t in Tr], Lp, F)
        if b is None: return None
        ok, log = b.IsValidWithLog
        fix = re.findall(r'm_T\[(\d+)\]\.m_iso = (\d+) and it should be (\d+)', log)
        if ok or not fix: break
        for k, _, should in fix: Tr[int(k)][6] = int(should)
    if not ok or not b.IsSolid: return None
    return b


def _side_mid(ns, a, b):
    p = ns.PointAt((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); return np.array([p.X, p.Y, p.Z])


def _side_pts(ns, a, b, n=9):
    out = []
    for t in np.linspace(0, 1, n):
        p = ns.PointAt(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t); out.append([p.X, p.Y, p.Z])
    return np.array(out)


def ruled_between(rowA, rowB, order, knots):
    """二つの制御点の並び（同じ節点）を直線でつなぐ面（u：order 次、v：1 次）"""
    n = len(rowA)
    ns = r.NurbsSurface.Create(3, False, order, 2, n, 2)
    for i in range(n):
        for j, row in enumerate((rowA, rowB)):
            c = row[i]; ns.Points[i, j] = r.Point4d(float(c[0]), float(c[1]), float(c[2]), 1.0)
    for i, k in enumerate(knots): ns.KnotsU[i] = float(k)
    ns.KnotsV[0] = 0.0; ns.KnotsV[1] = 1.0
    return ns


def thicken_surface(s, t, up=0.0):
    """一枚の切らない面に、鉛直に t 下げた面と四つの小口をつけた 6 枚（閉じる組）。up：先に面を上げる量"""
    ns = s.ToNurbsSurface() if not isinstance(s, r.NurbsSurface) else s
    ou, ov, ku, kv, C, rat = _ns_data(ns)
    if rat: return None
    nu, nv = len(C), len(C[0])
    if up:
        top = r.NurbsSurface.Create(3, False, ou, ov, nu, nv)
        for i in range(nu):
            for j in range(nv):
                x, y, z, w = C[i][j]; top.Points[i, j] = r.Point4d(x, y, z + up, 1.0); C[i][j] = (x, y, z + up, 1.0)
        for i, k in enumerate(ku): top.KnotsU[i] = k
        for i, k in enumerate(kv): top.KnotsV[i] = k
        ns = top
    low = r.NurbsSurface.Create(3, False, ou, ov, nu, nv)
    for i in range(nu):
        for j in range(nv):
            x, y, z, w = C[i][j]; low.Points[i, j] = r.Point4d(x, y, z - t, 1.0)
    for i, k in enumerate(ku): low.KnotsU[i] = k
    for i, k in enumerate(kv): low.KnotsV[i] = k
    D = lambda row: [(c[0], c[1], c[2] - t) for c in row]
    rows = [([C[i][0] for i in range(nu)], ou, ku), ([C[i][nv - 1] for i in range(nu)], ou, ku),
            ([C[0][j] for j in range(nv)], ov, kv), ([C[nu - 1][j] for j in range(nv)], ov, kv)]
    out = [ns, low] + [ruled_between(row, D(row), o, k) for row, o, k in rows]
    return out


def solids_from_surfaces(srfs, thick=None, center=False):
    """線織面の組（6 枚ずつで閉じる片）→ [(ジオメトリ, 種類)]。一枚だけの片は thick があれば厚みをつける
    （center なら面を厚みの真ん中に）。閉じない面は面のまま（'surface'）"""
    out = []; k = 0; n = len(srfs)
    while k < n:
        b = join_untrimmed(srfs[k:k + 6]) if k + 6 <= n else None
        if b is not None: out.append((b, 'curved')); k += 6; continue
        s = srfs[k]
        if thick:
            grp = thicken_surface(s, thick, thick / 2 if center else 0.0)
            b = join_untrimmed(grp) if grp else None
            if b is not None: out.append((b, 'curved')); k += 1; continue
        out.append((r.Brep.CreateFromSurface(s), 'surface')); k += 1
    return out
