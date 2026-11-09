"""育ち舎 1/100 模型：室内の間仕切り（航空ベニヤ 0.6）の組み立て用の形（模型作成）。

laser.py の「9. 室内の壁」から使う。3dm は読まない（板の形・位置は laser.py が渡す）。
  1. 同じ線の上でつながる板を 1 枚の「壁」（Run）にまとめる（戸の上の欄間は両側の壁とつながる）
  2. 壁どうしの交点（T・L・十字）に半欠きのかみ合い（上から／下から切り込み）を入れる
  3. 交点を持たない（ほかの壁と組まない）壁には足（T 字）をつける
座標：壁ごとの局所座標は x＝壁の線（A→B）に沿って、y＝高さ（模型 mm）。世界座標は実寸 mm。
"""
import math
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity

S = 0.01                 # 1/100：実寸 mm → 模型 mm
T_BOARD = 0.6            # 板の厚さ（航空ベニヤ 0.6）
KERF = 0.2               # 切り幅（T5 の結果が mokei.json に無いあいだは 0.2 と仮定）
END_TOL = 100.0          # 交点がこの距離（実寸 mm）より壁の端に近ければ、その端で組む（T・L）
JOIN_TOL = 40.0          # 交点を探すときの余裕（実寸 mm）
FOOT_LEN = 8.0           # 足の長さ（模型 mm、壁の両側へ 4 mm ずつ）
FOOT_MAX_H = 12.0        # 足の高さの上限


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _parts(g):
    return [p for p in getattr(g, 'geoms', [g]) if not p.is_empty and p.geom_type == 'Polygon']


class Run:
    """1 枚の壁。A→B が壁の線（実寸 mm の世界座標）、poly が立面（局所 x は A から、y は zref から。模型 mm）"""

    def __init__(self, rid, A, B, poly, zref, members):
        self.id = rid
        self.A, self.B = np.array(A, float), np.array(B, float)
        self.poly = poly
        self.zref = zref                       # 実寸 mm：y=0 の高さ
        self.members = members                 # 3dm の板の番号
        self.notes = []                        # この壁に入れた直し・かみ合い（文字）
        self.joints = []
        self.foot_of = None                    # 足なら、親の壁の番号

    @property
    def e(self):
        return _unit(self.B - self.A)

    @property
    def n(self):
        e = self.e
        return np.array([-e[1], e[0]])

    @property
    def L(self):                                # 壁の線の長さ（模型 mm）
        return float(np.linalg.norm(self.B - self.A)) * S

    def world(self, x):                         # 局所 x（模型 mm）→ 世界座標（実寸 mm）
        return self.A + self.e * (x / S)

    def x_of(self, P):                          # 世界座標 → 局所 x（模型 mm）
        return float((np.asarray(P) - self.A) @ self.e) * S

    def z_of(self, y):                          # 局所 y → 実寸の高さ mm
        return self.zref + y / S

    def y_of(self, z):
        return (z - self.zref) * S

    def top(self):
        return self.z_of(self.poly.bounds[3])

    def bottom(self):
        return self.z_of(self.poly.bounds[1])

    def reframe(self):
        """poly の左端が x=0 になるように A を動かす"""
        b = self.poly.bounds
        if abs(b[0]) > 1e-9:
            self.A = self.A + self.e * (b[0] / S)
            self.poly = affinity.translate(self.poly, -b[0], 0)
        self.B = self.A + self.e * ((self.poly.bounds[2]) / S)

    def local_z(self, x0, x1):
        """x0〜x1 の範囲で材のある高さ（実寸 mm の下端・上端）。無ければ None"""
        g = self.poly.intersection(box(x0, -1e4, x1, 1e4))
        if g.is_empty or g.area < 1e-6:
            return None
        b = g.bounds
        return self.z_of(b[1]), self.z_of(b[3])


# ---------- 1. 同じ線の上の板をまとめる ----------
def make_runs(pieces, ang_tol=4.0, off_tol=45.0, gap_tol=40.0):
    """pieces：dict(num, poly, A, B, z0)。poly は左下が (0,0) の立面（模型 mm）、A→B は実寸 mm の壁の線。
    同じ線の上（向きの差 ang_tol 度以内、横のずれ off_tol mm 以内）で端が触れる／重なる板を 1 枚にまとめる"""
    n = len(pieces)
    par = list(range(n))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    def line(p):
        d = np.array(p['B']) - np.array(p['A'])
        return np.array(p['A'], float), _unit(d) if np.linalg.norm(d) > 1e-6 else np.array([1.0, 0.0]), float(np.linalg.norm(d))

    for i in range(n):
        for j in range(i + 1, n):
            pa, pb = pieces[i], pieces[j]
            Ai, ei, Li = line(pa)
            Aj, ej, Lj = line(pb)
            # 短い板の向きはあてにならないので、長い方の向きを使う
            e = ei if Li >= Lj else ej
            A0 = Ai if Li >= Lj else Aj
            if min(Li, Lj) > 300 and abs(ei @ ej) < math.cos(math.radians(ang_tol)):
                continue
            nrm = np.array([-e[1], e[0]])
            offs = [abs((np.array(q) - A0) @ nrm) for q in (pa['A'], pa['B'], pb['A'], pb['B'])]
            if max(offs) > off_tol:
                continue
            si = sorted([(np.array(pa['A']) - A0) @ e, (np.array(pa['B']) - A0) @ e])
            sj = sorted([(np.array(pb['A']) - A0) @ e, (np.array(pb['B']) - A0) @ e])
            gap = max(sj[0] - si[1], si[0] - sj[1])
            if gap > gap_tol:
                continue
            za = (pa['z0'], pa['z0'] + pa['poly'].bounds[3] / S)
            zb = (pb['z0'], pb['z0'] + pb['poly'].bounds[3] / S)
            if max(za[0], zb[0]) > min(za[1], zb[1]) + 30:
                continue
            par[find(j)] = find(i)
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    # 弧に沿う長い壁は、まっすぐな板をつないだもの。1 枚にまとめた線から 30 mm 以上外れる板は別の壁にする
    sub = []
    for g in groups.values():
        mem = sorted(g, key=lambda i: min(np.array(pieces[i]['A']) @ _dir_of(pieces, g), np.array(pieces[i]['B']) @ _dir_of(pieces, g)))
        cur = []
        for i in mem:
            trial = cur + [i]
            if _fit_dev(pieces, trial) > FIT_TOL and cur:
                sub.append(cur); cur = [i]
            else:
                cur = trial
        if cur:
            sub.append(cur)
    runs = []
    for g in sub:
        mem = [pieces[i] for i in g]
        pts = [np.array(p[k], float) for p in mem for k in ('A', 'B')]
        d0 = _dir_of(pieces, g)
        sv = [q @ d0 for q in pts]
        P0, P1 = pts[int(np.argmin(sv))], pts[int(np.argmax(sv))]
        A0 = P0
        e = _unit(P1 - P0) if np.linalg.norm(P1 - P0) > 1e-6 else d0
        zref = min(p['z0'] for p in mem)
        polys = []
        for p in mem:
            a = (np.array(p['A']) - A0) @ e
            b = (np.array(p['B']) - A0) @ e
            q = p['poly']
            w = q.bounds[2]
            if b < a:                                   # 向きが逆の板は左右を返す
                q = affinity.scale(q, -1, 1, origin=(0, 0))
                q = affinity.translate(q, w, 0)
                a = b
            q = affinity.translate(q, a * S, (p['z0'] - zref) * S)
            polys.append(q.buffer(0.004).buffer(-0.004))
        u = unary_union(polys)
        u = unary_union([x for x in _parts(u) if x.area > 0.02])
        b = u.bounds
        r = Run(0, A0 + e * (b[0] / S), A0 + e * (b[2] / S), affinity.translate(u, -b[0], 0), zref, sorted(p['num'] for p in mem))
        runs.append(r)
    return runs


FIT_TOL = 30.0


def _dir_of(pieces, g):
    best = max(g, key=lambda i: np.linalg.norm(np.array(pieces[i]['B']) - np.array(pieces[i]['A'])))
    d = np.array(pieces[best]['B'], float) - np.array(pieces[best]['A'])
    return _unit(d) if np.linalg.norm(d) > 1e-6 else np.array([1.0, 0.0])


def _fit_dev(pieces, g):
    pts = [np.array(pieces[i][k], float) for i in g for k in ('A', 'B')]
    d0 = _dir_of(pieces, g)
    sv = [q @ d0 for q in pts]
    P0, P1 = pts[int(np.argmin(sv))], pts[int(np.argmax(sv))]
    if np.linalg.norm(P1 - P0) < 1e-6:
        return 0.0
    e = _unit(P1 - P0); n = np.array([-e[1], e[0]])
    return max(abs((q - P0) @ n) for q in pts)


# ---------- 2. 交点 ----------
class Joint:
    def __init__(self, R, S_, X, theta):
        self.R, self.S, self.X, self.theta = R, S_, np.array(X), theta   # X：世界座標（実寸 mm）、theta：二つの壁の線のなす角
        self.kind = ''          # 'T'（S が通り R が端）, 'L', '十字'
        self.note = ''
        self.cut = {}           # run.id → 切り込みの説明


def _line_x(A1, B1, A2, B2):
    d1, d2 = B1 - A1, B2 - A2
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((A2[0] - A1[0]) * d2[1] - (A2[1] - A1[1]) * d2[0]) / den
    return A1 + d1 * t


def find_joints(runs, t3=None):
    """壁どうしの交点。t3：壁ごとの 3dm の厚さ（実寸 mm、run.id → 値）。交点が端に近ければ端で組む"""
    J = []
    for i in range(len(runs)):
        for j in range(i + 1, len(runs)):
            R, S_ = runs[i], runs[j]
            if R.foot_of is not None or S_.foot_of is not None:
                continue
            sinth = abs(R.e[0] * S_.e[1] - R.e[1] * S_.e[0])
            if sinth < 0.25:
                continue
            X = _line_x(R.A, R.B, S_.A, S_.B)
            if X is None:
                continue
            tR = (t3 or {}).get(R.id, 120.0)
            tS = (t3 or {}).get(S_.id, 120.0)
            LR, LS = np.linalg.norm(R.B - R.A), np.linalg.norm(S_.B - S_.A)
            sR, sS = (X - R.A) @ R.e, (X - S_.A) @ S_.e
            if not (-(tS / 2 / sinth + JOIN_TOL) <= sR <= LR + tS / 2 / sinth + JOIN_TOL):
                continue
            if not (-(tR / 2 / sinth + JOIN_TOL) <= sS <= LS + tR / 2 / sinth + JOIN_TOL):
                continue
            j_ = Joint(R, S_, X, math.asin(min(1.0, sinth)))
            J.append(j_)
    return J


def end_of(run, X, tol=END_TOL):
    """交点 X が壁の端に近いなら 'A' か 'B'、そうでなければ None（壁の途中）"""
    s = (np.asarray(X) - run.A) @ run.e
    L = np.linalg.norm(run.B - run.A)
    if s <= tol:
        return 'A'
    if s >= L - tol:
        return 'B'
    return None


def classify(J):
    for j in J:
        a, b = end_of(j.R, j.X), end_of(j.S, j.X)
        if a and b:
            j.kind = 'L'
        elif a and not b:
            j.kind = 'T'          # R が端、S が通る
        elif b and not a:
            j.kind = 'T'
            j.R, j.S = j.S, j.R   # R を端の壁に
        else:
            j.kind = '十字'


def extend_stems(J):
    """T・L で端になる壁は、相手の壁の向こう側の面まで伸ばす（ちょうどその面にそろう）。
    向かい合う 2 本が同じ壁の両側から来るときは、壁の線までにする。"""
    ext = {}                                           # (run.id, 'A'/'B') → 伸ばす量（実寸 mm）
    for j in J:
        ends = [(j.R, 'A' if end_of(j.R, j.X) == 'A' else 'B')] if end_of(j.R, j.X) else []
        if j.kind == 'L' and end_of(j.S, j.X):
            ends.append((j.S, end_of(j.S, j.X)))
        for r, side in ends:
            other = j.S if r is j.R else j.R
            # 相手の面までの距離：交点（相手の線）から相手の向こう側の面
            sinth = abs(r.e[0] * other.e[1] - r.e[1] * other.e[0])
            far = (T_BOARD / S / 2) / sinth                       # 実寸 mm（相手の板の半分の厚さを r の線方向に直す）
            s_end = (r.B - r.A) @ r.e if side == 'B' else 0.0
            s_x = (j.X - r.A) @ r.e
            want = (s_x + far - s_end) if side == 'B' else (s_end - (s_x - far))
            key = (r.id, side)
            ext[key] = max(ext.get(key, -1e9), want)
    return ext


def apply_extensions(runs, ext):
    by = {r.id: r for r in runs}
    for (rid, side), v in ext.items():
        r = by[rid]
        if abs(v) < 1e-6:
            continue
        b = r.poly.bounds
        if v < 0:
            if side == 'B':
                r.poly = unary_union(_parts(r.poly.intersection(box(-1e4, -1e4, b[2] + v * S, 1e4))))
                r.B = r.B + r.e * v
            else:
                r.poly = unary_union(_parts(r.poly.intersection(box(b[0] - v * S, -1e4, 1e4, 1e4))))
                r.reframe()
            continue
        if side == 'B':
            x1 = b[2]
            prof = r.poly.intersection(box(x1 - 0.05, -1e4, x1 + 1e-9, 1e4))
            ys = [p.bounds for p in _parts(prof)]
            add = unary_union([box(x1 - 0.001, y0, x1 + v * S, y1) for (_, y0, _, y1) in ys])
            r.poly = unary_union([r.poly, add]).buffer(0.002).buffer(-0.002)
            r.B = r.B + r.e * v
        else:
            x0 = b[0]
            prof = r.poly.intersection(box(x0 - 1e-9, -1e4, x0 + 0.05, 1e4))
            ys = [p.bounds for p in _parts(prof)]
            add = unary_union([box(x0 - v * S, y0, x0 + 0.001, y1) for (_, y0, _, y1) in ys])
            r.poly = unary_union([r.poly, add]).buffer(0.002).buffer(-0.002)
            r.poly = affinity.translate(r.poly, v * S, 0)
            r.A = r.A - r.e * v


def cut_joints(J, kerf=KERF, closed_w=None):
    """半欠き：高いほう（上端が高い壁）に下から、低いほうに上から切り込み。
    切り込みの幅（描く）：両側に木が残る切り込み＝相手の厚さ−切り幅（0.6−0.2＝0.4）、端の切り込み＝相手の厚さ−切り幅/2。
    高さの境は、組む所の材の高さ（下端と上端）の真ん中。"""
    wc = closed_w if closed_w else T_BOARD - kerf
    log = []
    for j in J:
        R, S_ = j.R, j.S
        sinth = abs(R.e[0] * S_.e[1] - R.e[1] * S_.e[0])
        xr, xs = R.x_of(j.X), S_.x_of(j.X)
        half = (T_BOARD / 2) / sinth                     # 相手の板が自分の線の上で占める半分の幅（模型 mm）
        zr = R.local_z(xr - half - 0.2, xr + half + 0.2) or (R.bottom(), R.top())
        zs = S_.local_z(xs - half - 0.2, xs + half + 0.2) or (S_.bottom(), S_.top())
        lo, hi = max(zr[0], zs[0]), min(zr[1], zs[1])
        zm = (lo + hi) / 2
        # 上端が高い壁が「下から」、低い壁が「上から」。同じ高さなら T・L で端になるほう（R）が下から
        r_low = (zr[1] > zs[1] + 50) or (abs(zr[1] - zs[1]) <= 50 and True)
        j.zm, j.lo, j.hi = zm, lo, hi
        j.r_from = 'bottom' if r_low else 'top'
        j.s_from = 'top' if r_low else 'bottom'
        for run, x, frm, other, here_end in ((R, xr, j.r_from, S_, end_of(R, j.X)), (S_, xs, j.s_from, R, end_of(S_, j.X))):
            sinth_ = abs(run.e[0] * other.e[1] - run.e[1] * other.e[0])
            w_full = (T_BOARD) / sinth_                    # 相手が自分の線の上で占める幅
            y_m = run.y_of(zm)
            y_lo, y_hi = run.poly.bounds[1] - 1, run.poly.bounds[3] + 1
            if here_end is None:
                w = w_full - kerf
                x0, x1 = x - w / 2, x + w / 2
                desc = f'切り込み 幅{w:.2f}（両側に木）'
            elif here_end == 'A':
                far = x - w_full / 2                       # 相手の近い面
                # この壁の端（x≒0）から、相手の近い面まで
                w = (x + w_full / 2) - (kerf / 2) if x - w_full / 2 <= 0.05 else None
                x1 = x + w_full / 2 - kerf / 2
                x0 = -1.0
                w = x1 - 0.0
                desc = f'端の切り込み 長さ{w:.2f}'
            else:
                Lr = run.poly.bounds[2]
                x0 = x - w_full / 2 + kerf / 2
                x1 = Lr + 1.0
                w = Lr - x0
                desc = f'端の切り込み 長さ{w:.2f}'
            if frm == 'bottom':
                cut = box(x0, y_lo, x1, y_m)
                desc += f'・下から（高さ{run.y_of(run.zref):.0f}→{y_m:.2f}）'
            else:
                cut = box(x0, y_m, x1, y_hi)
                desc += f'・上から'
            before = run.poly.area
            run.poly = run.poly.difference(cut)
            removed = before - run.poly.area
            run.joints.append((j, frm, x, w, removed))
            j.cut[run.id] = (frm, x, w, removed, desc)
        log.append(j)
    return log


# ---------- 3. 孤立した壁 ----------
def components(runs, J):
    par = {r.id: r.id for r in runs}

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    for j in J:
        par[find(j.R.id)] = find(j.S.id)
    comp = {}
    for r in runs:
        comp.setdefault(find(r.id), []).append(r)
    return list(comp.values())


def is_braced(group):
    """組んだ壁が、向きの違う 2 本以上（20 度以上）で支え合っているか"""
    if len(group) < 2:
        return False
    for a in group:
        for b in group:
            if a is not b and abs(a.e[0] * b.e[1] - a.e[1] * b.e[0]) > math.sin(math.radians(20)):
                return True
    return False


def make_feet(run, next_id, short=15.0):
    """孤立した壁の端に T 字の足（壁の線に直角、長さ FOOT_LEN、高さは壁の端の高さの半分で 6 mm まで）。
    足の向こう側の面が壁の端にそろう。長さ short mm 未満の壁は A 端だけ。返す：[(足の Run, 足と壁の Joint)]"""
    feet = []
    sides = ('A',) if run.L < short else ('A', 'B')
    for side in sides:
        x_end = 0.0 if side == 'A' else run.poly.bounds[2]
        xc = T_BOARD / 2 if side == 'A' else x_end - T_BOARD / 2
        loc = run.poly.intersection(box(x_end - 0.5 if side == 'A' else x_end - 1.5, -1e4, x_end + 1.5 if side == 'A' else x_end + 0.5, 1e4))
        if loc.is_empty:
            continue
        y0, y1 = loc.bounds[1], loc.bounds[3]
        hf = min(6.0, (y1 - y0) * 0.5)
        C = run.world(xc)
        A_ = C - run.n * (FOOT_LEN / S / 2)
        B_ = C + run.n * (FOOT_LEN / S / 2)
        f = Run(next_id, A_, B_, box(0, 0, FOOT_LEN, hf), run.z_of(y0), [])
        f.foot_of = run.id
        f.side = side
        f.notes.append(f'足（壁{run.id}の{"A端" if side == "A" else "B端"}）')
        j = Joint(run, f, C, math.pi / 2)
        j.kind = 'T'
        feet.append((f, j))
        next_id += 1
    return feet
