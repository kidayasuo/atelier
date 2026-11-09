# -*- coding: utf-8 -*-
#! python 3
"""
「架構」部品（遊戯室の架構、第4課題「架構と建築」）
Rhino 8 Mac の Grasshopper、Python 3 のスクリプト部品に貼る。単位は mm。

一つの部品で、架構kの梁（2枚の板）・東西の柱・2階の床梁（あれば）を同時に作る。
接合は Tamedia（Shigeru Ban、Zürich 2013）に倣う：
  - 柱は1本の材で、2枚の板が両側から挟む。
  - 柱の頭で、楕円の桁（ピン）が板と柱の穴を通る。
  - 板の端は、桁の穴を包む楕円の頭。頭は梁の下端より下がり、
    梁の下端とは大きな丸みのハンチでつながる。端の上は、上端から頭へ回る丸み。
  - 柱は、頭の下で丸みで広がって頭に取りつく（2階の頭では上下とも）。柱の上は板の外形の中で終わる。
  - 寸法は決めず、Tamedia の詳細図の比で梁のせい D から決める（ユーザー 11-09：あのデザインを達成する）：
    桁の中心は下端から 0.14D、頭は半幅 0.58D・半高さ 0.68D、ハンチ 1.1D、柱の広がり 0.55D。
    ただし頭は桁の穴のまわりに木 120 以上を残す。
西の端は、頭と軒先への細い延長を一つの板にする（せい240→先で120、先は鉛直、丸み300でつなぐ）。

架構の位置：背骨（西館の東の柱の列）の円弧の中心からの放射の直線。
  架構kは u＝3(k−1) m、u は東の線 v−0.9 の上で測る（k15.5 も可）。
梁の上端：屋根の面（Brep）と、各板の真ん中の鉛直面の交線を直線で近似（ずれは CSV に出す）。
  屋根の面を差し替えれば、A・B・C 案の架構がそのまま作り直される。
例外は「柱を出すか」だけ。それ以外は Bake してから手で直す。

入力（必須）  roof：屋根の面（梁の上端の面、Brep、Item）
               k：架構の番号（float、List）
               west：西の柱の外の面＝外壁の内面の線（平面の曲線、Curve、Item）
入力（任意、無ければ既定の値。部品に入力を足したものだけ効く）
               eave：軒先の線（Curve、Item）。無ければ外壁の内面から EAVE_OUT
               showCol：柱を出すか（bool、List。1つなら全部に、kと同じ数なら1本ずつ）
               mids：2階の床梁の上端の高さ（FL から、str、List。"3200"、無しは空。kと同じ数か1つ）
               FL・D・t・gap・colE・colW・ext0・ext1・Dm・eR・haR・hbR（float、Item）
               csv：CSV を書くファイルの道（str、Item）
出力           plates（板）・cols（柱）・floors（2階の床梁）・ptE・ptW・ptM（桁が通る点）
               axis（桁の向き＝梁に直角）・lines（架構の線）・table（CSV の文）・log
"""
import math

# ------------------------------------------------------------------ 既定の値（mm）
DEF = dict(
    FL=0.0,
    D=650.0,      # 梁のせい（鉛直）。今の単純梁で、板2×160・遊具の見直しの略算（ryakusan/hikaku_1109.py）
    t=160.0,      # 板の厚さ（Tamediaに合わせる、ユーザー 11-09）
    gap=180.0,    # 光の筋の幅＝柱の厚さ
    colE=480.0,   # 東の柱の幅（架構の向き）
    colW=400.0,   # 西の柱の幅
    eR=0.14,      # 桁の中心の、梁の下端からの高さ／D（Tamedia）
    haR=0.58,     # 頭の楕円の半幅／D
    hbR=0.68,     # 頭の楕円の半高さ／D
    ext0=240.0,   # 軒への延長のせい（外壁の内面で）
    ext1=120.0,   # 同（先で）
    Dm=400.0,     # 2階の床梁のせい
)
GIRDER_A, GIRDER_B = 100.0, 200.0   # 桁（楕円 200×400）の半径
HOLE_CLR = 5.0                      # 穴は桁の断面＋10（半径で＋5）
HAUNCH_RR = 1.1                     # 梁の下端と頭のつなぎの丸み／D（Tamedia R600／せい550）
COL_RR = 0.55                       # 柱の面と頭のつなぎの丸み／D
WOOD_MIN = 120.0                    # 桁の穴のまわりに残す木
EAVE_R = 300.0                      # 延長の下端と頭のつなぎ
TIP_GAP = 100.0                     # 延長の先は軒先の線の0.1手前（線に直角に測る）
EAVE_OUT = 780.0                    # eave が無いときの軒の出（外壁の内面から）
V_EAST_FACE = 1050.0                # 東の柱の外の面＝西館の東の壁の内面 v−1.05
V_U = 900.0                         # u を測る線 v−0.9
PITCH = 3000.0
# 本館の (u, v) の円（model/build/south/uv.py と同じ定数）
CX, CY, RW = 194662.93237, -41348.26335, 205017.7
TH_S = math.atan2(-65173.47495 - CY, -8965.4788 - CX) % (2 * math.pi)


# ================================================================== 2D の核（Rhino を使わない）
# 架構ごとの平面の座標 (s, z)：s は東の柱の芯から西へ、z は高さ（世界の z）。
# 形は「基本形」の和で表し、Rhino の側で曲線にして足し合わせる。
#   ('poly', [(s,z),...])                 閉じた多角形
#   ('aff', kind, s0, z0, a11, a12, a21, a22)
#        単位円（kind='circle'）か上半分の単位円（'half'）を (s,z)=(s0+a11x+a12y, z0+a21x+a22y) へ写したもの
#   ('fillet', T1, cf, R, T2, I)          T1→（中心cf、半径Rの円弧）→T2→I→T1

def frame_axis(k, colE):
    """架構kの東の柱の芯 O（平面）と向き dir（西へ）・perp（dir を左へ90°）"""
    th = TH_S - PITCH * (k - 1.0) / (RW + V_U)
    c, s = math.cos(th), math.sin(th)
    r = RW + V_EAST_FACE + colE / 2.0
    return (CX + r * c, CY + r * s), (c, s), (-s, c), th


def fit_line(pts):
    """[(s,z)] の最小二乗の直線 z=z0+m s と、最大のずれ"""
    n = len(pts)
    ms = sum(p[0] for p in pts) / n
    mz = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - ms) ** 2 for p in pts)
    m = sum((p[0] - ms) * (p[1] - mz) for p in pts) / sxx if sxx > 1e-9 else 0.0
    z0 = mz - m * ms
    dev = max(abs(p[1] - (z0 + m * p[0])) for p in pts)
    return z0, m, dev


def _ell_pt(c, a, b, th):
    return (c[0] + a * math.cos(th), c[1] + b * math.sin(th))


def ell_sdist(p, c, a, b, n=720):
    """楕円の周への距離（中なら負）と、いちばん近い周の点"""
    best, bt = 1e30, 0.0
    for i in range(n):
        th = 2 * math.pi * i / n
        q = _ell_pt(c, a, b, th)
        d = (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2
        if d < best:
            best, bt = d, th
    lo, hi = bt - 2 * math.pi / n, bt + 2 * math.pi / n
    f = lambda th: (_ell_pt(c, a, b, th)[0] - p[0]) ** 2 + (_ell_pt(c, a, b, th)[1] - p[1]) ** 2
    for _ in range(60):
        m1, m2 = lo + (hi - lo) / 3, hi - (hi - lo) / 3
        if f(m1) < f(m2):
            hi = m2
        else:
            lo = m1
    th = (lo + hi) / 2
    q = _ell_pt(c, a, b, th)
    d = math.sqrt(f(th))
    inside = ((p[0] - c[0]) / a) ** 2 + ((p[1] - c[1]) / b) ** 2 < 1.0
    return (-d if inside else d), q


def first_hit(p0, d, c, a, b):
    """直線 p0+d·x（x≥0）が楕円に最初に当たる x（当たらなければ None）"""
    px, pz = (p0[0] - c[0]) / a, (p0[1] - c[1]) / b
    dx, dz = d[0] / a, d[1] / b
    A = dx * dx + dz * dz
    B = 2 * (px * dx + pz * dz)
    C = px * px + pz * pz - 1.0
    disc = B * B - 4 * A * C
    if disc < 0:
        return None
    r1 = (-B - math.sqrt(disc)) / (2 * A)
    r2 = (-B + math.sqrt(disc)) / (2 * A)
    xs = [x for x in (r1, r2) if x >= 0]
    return min(xs) if xs else None


def fillet(p0, d, n, c, a, b, R, pin):
    """直線（p0 から d の向きに楕円へ近づく、n は材の無い側）と楕円の入隅を半径Rの円弧で埋める基本形。
    pin は楕円の中で、直線の材の側にある点。つなげなければ None"""
    xX = first_hit(p0, d, c, a, b)
    if xX is None:
        return None
    cen = lambda x: (p0[0] + d[0] * x + n[0] * R, p0[1] + d[1] * x + n[1] * R)
    f = lambda x: ell_sdist(cen(x), c, a, b)[0] - R
    hi = xX
    if f(hi) > 0:
        return None
    lo = xX - 3 * R
    k = 0
    while f(lo) <= 0 and k < 20:
        lo -= 2 * R
        k += 1
    for _ in range(50):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    x = (lo + hi) / 2
    cf = cen(x)
    T1 = (p0[0] + d[0] * x, p0[1] + d[1] * x)
    T2 = ell_sdist(cf, c, a, b)[1]
    X = (p0[0] + d[0] * xX, p0[1] + d[1] * xX)
    I = (X[0] + 0.15 * (pin[0] - X[0]), X[1] + 0.15 * (pin[1] - X[1]))
    return ('fillet', T1, cf, R, T2, I)


def head_size(P, D):
    """せい D の梁の頭の大きさ（Tamediaの比、桁の穴のまわりに木 WOOD_MIN 以上）"""
    return dict(e=P['eR'] * D,
                ha=max(P['haR'] * D, GIRDER_A + HOLE_CLR + WOOD_MIN),
                hb=max(P['hbR'] * D, GIRDER_B + HOLE_CLR + WOOD_MIN),
                R=HAUNCH_RR * D, Rc=COL_RR * D)


def ellipse(c, a, b):
    return ('aff', 'circle', c[0], c[1], a, 0.0, 0.0, b)


def head_prims(G, ztop, m, h, span_dir, soffit_line):
    """桁の点 G のまわり：頭の楕円・上端へ回る丸み・梁の下端とのハンチ。
    span_dir：G から梁のスパンの側への向き（+1 か −1）。soffit_line：(z0, m) 梁の下端"""
    ha, hb, R_haunch = h['ha'], h['hb'], h['R']
    pr = [ellipse(G, ha, hb)]
    H = ztop - G[1]
    if H > 1.0:
        # 上半分の楕円を、上端の直線に接するよう傾けた丸み（端の上の角）
        pr.append(('aff', 'half', G[0], G[1], ha, 0.0, m * ha, H))
        if abs(m) > 1e-6:
            pr.append(('poly', [(G[0] - ha, G[1]), (G[0] + ha, G[1]),
                                (G[0] + ha, G[1] + m * ha), (G[0] - ha, G[1] - m * ha)]))
    # ハンチ：梁の下端の直線を、スパンの側から G へ近づく
    z0, ms = soffit_line
    far = G[0] + span_dir * 4 * R_haunch
    p0 = (far, z0 + ms * far)
    L = math.hypot(1.0, ms)
    d = (-span_dir / L, -span_dir * ms / L)
    n = (d[1], -d[0])                     # 下向き（材の無い側）にそろえる
    if n[1] > 0:
        n = (-n[0], -n[1])
    fl = fillet(p0, d, n, G, ha, hb, R_haunch, G)
    if fl:
        pr.append(fl)
    return pr


def beam_2d(P, top, sE, sW, ext=None):
    """梁（または2階の床梁）の板の外形の基本形と、上端で切る多角形と、穴。
    top=(z0, m)。ext=(s_wall, s_tip)：西の端の軒への延長"""
    z0, m = top
    zt = lambda s: z0 + m * s
    D = P['D_beam']
    h = head_size(P, D)
    e = h['e']
    soff = (z0 - D, m)
    GE = (sE, zt(sE) - D + e)
    GW = (sW, zt(sW) - D + e)
    pr = [('poly', [(sE, zt(sE)), (sW, zt(sW)), (sW, zt(sW) - D), (sE, zt(sE) - D)])]
    pr += head_prims(GE, zt(sE), m, h, +1, soff)
    pr += head_prims(GW, zt(sW), m, h, -1, soff)
    s_hi = sW + h['ha'] + 10
    if ext:
        s_wall, s_tip = ext
        a0, a1 = P['ext0'], P['ext1']
        pr.append(('poly', [(sW, zt(sW)), (s_tip, zt(s_tip)), (s_tip, zt(s_tip) - a1),
                            (s_wall, zt(s_wall) - a0), (sW, zt(sW) - a0)]))
        # 延長の下端と頭の上の丸みの入隅（丸み EAVE_R）。頭の上の丸みは傾いた楕円なので、
        # 傾きを除いた座標（z' = z − m(s−sW)）で楕円として扱い、結果を戻す
        H = zt(sW) - GW[1]
        q = lambda s, z: (s, z - m * (s - sW))
        r = lambda s, z: (s, z + m * (s - sW))
        pA, pB = q(s_tip, zt(s_tip) - a1), q(s_wall, zt(s_wall) - a0)
        L = math.hypot(pB[0] - pA[0], pB[1] - pA[1])
        d = ((pB[0] - pA[0]) / L, (pB[1] - pA[1]) / L)
        n = (d[1], -d[0])
        if n[1] > 0:
            n = (-n[0], -n[1])
        pin = (GW[0], GW[1] + 0.85 * H)
        fl = fillet(pA, d, n, GW, h['ha'], H, EAVE_R, pin)
        if fl:
            _, T1, cf, R, T2, I = fl
            # 傾きを除いた座標の円弧は、戻すと少し楕円になる。円弧の点を細かく戻して多角形にする
            pr.append(('poly', [r(*T1)] + [r(*p) for p in _arc_pts(T1, cf, T2, 16)] + [r(*T2), r(*I)]))
        s_hi = s_tip
    s_lo = sE - h['ha'] - 10
    big = 20000.0
    clip = ('poly', [(s_lo - 1, zt(s_lo - 1)), (s_hi + 1, zt(s_hi + 1)),
                     (s_hi + 1, zt(s_hi) - big), (s_lo - 1, zt(s_lo) - big)])
    holes = [ellipse(GE, GIRDER_A + HOLE_CLR, GIRDER_B + HOLE_CLR),
             ellipse(GW, GIRDER_A + HOLE_CLR, GIRDER_B + HOLE_CLR)]
    return dict(prims=pr, clip=clip, holes=holes, GE=(GE, h), GW=(GW, h), s_lo=s_lo, s_hi=s_hi)


def _arc_pts(T1, cf, T2, n):
    a1 = math.atan2(T1[1] - cf[1], T1[0] - cf[0])
    a2 = math.atan2(T2[1] - cf[1], T2[0] - cf[0])
    da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    R = math.hypot(T1[0] - cf[0], T1[1] - cf[1])
    return [(cf[0] + R * math.cos(a1 + da * i / n), cf[1] + R * math.sin(a1 + da * i / n)) for i in range(1, n)]


def column_2d(P, Gs, w, FL, top, heads, roofG):
    """柱（架構の面）。heads：この柱に取りつく頭 [(点, 大きさ)]（屋根と2階）。roofG：屋根の頭の点。
    返すのは柱の基本形（足し合わせる）と、切る形の指定（屋根の板の外形と、屋根の頭より下の帯の和）"""
    z0, m = top
    ztop = z0 + m * Gs
    pr = [('poly', [(Gs - w / 2, FL), (Gs + w / 2, FL), (Gs + w / 2, ztop + 2000), (Gs - w / 2, ztop + 2000)])]
    for G, h in heads:
        ha, hb = h['ha'], h['hb']
        for side in (-1, 1):
            n = (side, 0.0)
            # 下から頭へ
            fl = fillet((Gs + side * w / 2, FL), (0.0, 1.0), n, G, ha, hb, h['Rc'], G)
            if fl:
                pr.append(fl)
            # 2階の頭は上からも
            if G is not roofG:
                fl = fillet((Gs + side * w / 2, roofG[1]), (0.0, -1.0), n, G, ha, hb, h['Rc'], G)
                if fl:
                    pr.append(fl)
    band = ('poly', [(Gs - w / 2 - 3000, FL - 1), (Gs + w / 2 + 3000, FL - 1),
                     (Gs + w / 2 + 3000, roofG[1]), (Gs - w / 2 - 3000, roofG[1])])
    holes = [ellipse(G, GIRDER_A + HOLE_CLR, GIRDER_B + HOLE_CLR) for G, h in heads]
    return dict(prims=pr, band=band, holes=holes)


def parse_mids(x):
    if x is None:
        return []
    out = []
    for p in str(x).replace(',', ';').split(';'):
        p = p.strip()
        if p:
            try:
                out.append(float(p))
            except ValueError:
                pass
    return out


# ================================================================== Rhino の側
try:
    import Rhino.Geometry as rg
    from Rhino.Geometry.Intersect import Intersection as _X
    import Rhino
    _RHINO = True
except ImportError:
    _RHINO = False


def _in(name, default=None):
    v = globals().get(name)
    if v is None:
        return default
    if isinstance(v, (list, tuple)) and len(v) == 0:
        return default
    return v


def _num(name):
    v = _in(name)
    return float(v) if v is not None else DEF[name]


def _pick(lst, i, default):
    """1つなら全部に、k と同じ数なら i 番目"""
    if lst is None:
        return default
    if not isinstance(lst, (list, tuple)):
        lst = list(lst) if hasattr(lst, '__iter__') and not isinstance(lst, str) else [lst]
    if len(lst) == 0:
        return default
    if len(lst) == 1:
        return lst[0]
    return lst[i] if i < len(lst) else default


class Frame3:
    """架構の面 (s, z) と、その面から off だけ横へずらした面を世界の座標へ"""

    def __init__(self, O, d, p):
        self.O, self.d, self.p = O, d, p

    def P(self, s, z, off=0.0):
        return rg.Point3d(self.O[0] + s * self.d[0] + off * self.p[0],
                          self.O[1] + s * self.d[1] + off * self.p[1], z)

    def curve(self, prim, off):
        kind = prim[0]
        if kind == 'poly':
            pts = [self.P(s, z, off) for s, z in prim[1]]
            pts.append(pts[0])
            return rg.PolylineCurve(pts)
        if kind == 'aff':
            _, which, s0, z0, a11, a12, a21, a22 = prim
            if which == 'circle':
                c = rg.Circle(rg.Plane.WorldXY, 1.0).ToNurbsCurve()
            else:
                arc = rg.Arc(rg.Plane.WorldXY, 1.0, math.pi).ToNurbsCurve()
                ln = rg.LineCurve(rg.Point3d(-1, 0, 0), rg.Point3d(1, 0, 0))
                c = rg.Curve.JoinCurves([arc, ln], 0.001)[0]
            # 制御点を写す（写しは一次なので、重みはそのまま）
            for i in range(c.Points.Count):
                cp = c.Points[i]
                x, y, w = cp.Location.X, cp.Location.Y, cp.Weight
                c.Points.SetPoint(i, self.P(s0 + a11 * x + a12 * y, z0 + a21 * x + a22 * y, off), w)
            return c
        if kind == 'fillet':
            _, T1, cf, R, T2, I = prim
            a1 = math.atan2(T1[1] - cf[1], T1[0] - cf[0])
            a2 = math.atan2(T2[1] - cf[1], T2[0] - cf[0])
            da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
            M = (cf[0] + R * math.cos(a1 + da / 2), cf[1] + R * math.sin(a1 + da / 2))
            arc = rg.ArcCurve(rg.Arc(self.P(T1[0], T1[1], off), self.P(M[0], M[1], off), self.P(T2[0], T2[1], off)))
            pl = rg.PolylineCurve([self.P(T2[0], T2[1], off), self.P(I[0], I[1], off), self.P(T1[0], T1[1], off)])
            return rg.Curve.JoinCurves([arc, pl], 0.01)[0]
        raise ValueError(kind)


def _tol():
    try:
        return Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance
    except Exception:
        return 0.01


def _largest(crvs):
    best, ba = None, -1.0
    for c in crvs or []:
        if c is None or not c.IsClosed:
            continue
        mp = rg.AreaMassProperties.Compute(c)
        a = mp.Area if mp else 0.0
        if a > ba:
            best, ba = c, a
    return best


def _union(crvs, tol):
    if len(crvs) == 1:
        return crvs[0]
    r = rg.Curve.CreateBooleanUnion(crvs, tol)
    if not r:
        raise RuntimeError('外形の和ができない')
    return _largest(r)


def _inter(a, b, tol):
    r = rg.Curve.CreateBooleanIntersection(a, b, tol)
    if not r:
        raise RuntimeError('外形の切り取りができない')
    return _largest(r)


def _solid(F, outer, holes2d, off, thick, tol):
    """外形（off の面）と穴から、+perp へ thick の押し出しの立体"""
    crvs = [outer] + [F.curve(h, off) for h in holes2d]
    br = rg.Brep.CreatePlanarBreps(crvs, tol)
    if not br:
        raise RuntimeError('平らな面ができない')
    face = br[0].Faces[0]
    p0 = F.P(0, 0, off)
    path = rg.LineCurve(p0, F.P(0, 0, off + thick))
    s = face.CreateExtrusion(path, True)
    if s is None:
        raise RuntimeError('押し出しができない')
    return s


def _top_fit(F, roof, off, s_lo, s_hi, tol):
    """屋根の面と、off の鉛直面の交線を (s,z) の直線に"""
    org = F.P(0, 0, off)
    pl = rg.Plane(org, rg.Vector3d(F.d[0], F.d[1], 0), rg.Vector3d.ZAxis)
    ok, crvs, pts = _X.BrepPlane(roof, pl, tol)
    if not ok or not crvs:
        raise RuntimeError('屋根の面と交わらない（off=%.0f）' % off)
    sz = []
    for c in crvs:
        for t in c.DivideByCount(60, True) or []:
            q = c.PointAt(t)
            s = (q.X - org.X) * F.d[0] + (q.Y - org.Y) * F.d[1]
            if s_lo <= s <= s_hi:
                sz.append((s, q.Z))
    if len(sz) < 2:
        raise RuntimeError('屋根の面が架構の範囲を覆っていない（off=%.0f）' % off)
    return fit_line(sz)


def _hit_s(F, crv, s_min=1000.0):
    """架構の線（平面）が曲線と交わる s（s_min より先でいちばん近いもの）と、その所の曲線の向き"""
    flat = rg.Curve.ProjectToPlane(crv, rg.Plane.WorldXY)
    ln = rg.LineCurve(F.P(-5000, 0), F.P(60000, 0))
    ev = _X.CurveCurve(ln, flat, 0.1, 0.1)
    best = None
    for x in ev or []:
        q = x.PointA
        s = (q.X - F.O[0]) * F.d[0] + (q.Y - F.O[1]) * F.d[1]
        if s > s_min and (best is None or s < best[0]):
            tg = flat.TangentAt(x.ParameterB)
            best = (s, tg)
    return best


def build_one(kk, roof, west, eave, showcol, mids, P, tol):
    O, d, p, th = frame_axis(kk, P['colE'])
    F = Frame3(O, d, p)
    hw = _hit_s(F, west)
    if hw is None:
        raise RuntimeError('架構の線が西の線と交わらない')
    s_wall = hw[0]
    sW = s_wall - P['colW'] / 2.0
    if eave is not None:
        he = _hit_s(F, eave, s_wall)
        if he is None:
            raise RuntimeError('架構の線が軒先の線と交わらない')
        tg = he[1]
        cosphi = abs(-tg.Y * d[0] + tg.X * d[1]) / max(1e-9, math.hypot(tg.X, tg.Y))
        s_tip = he[0] - TIP_GAP / max(cosphi, 0.2)
    else:
        s_tip = s_wall + EAVE_OUT - TIP_GAP
    s_lo, s_hi = -head_size(P, P['D'])['ha'] - 300, s_tip + 10
    offs = {'+': P['gap'] / 2 + P['t'] / 2, '-': -(P['gap'] / 2 + P['t'] / 2), '0': 0.0}
    tops = {key: _top_fit(F, roof, off, s_lo, s_hi, tol) for key, off in offs.items()}

    Pb = dict(P, D_beam=P['D'])
    out = dict(plates=[], cols=[], floors=[], ptM=[])
    plate_lo = {'+': P['gap'] / 2, '-': -(P['gap'] / 2 + P['t'])}
    for key in ('+', '-'):
        B = beam_2d(Pb, tops[key][:2], 0.0, sW, ext=(s_wall, s_tip))
        off = plate_lo[key]
        outer = _union([F.curve(q, off) for q in B['prims']], tol)
        outer = _inter(outer, F.curve(B['clip'], off), tol)
        out['plates'].append(_solid(F, outer, B['holes'], off, P['t'], tol))
    B0 = beam_2d(Pb, tops['0'][:2], 0.0, sW, ext=(s_wall, s_tip))
    (GE, hE), (GW, hW) = B0['GE'], B0['GW']

    # 2階の床梁
    mid_heads = {0: [], 1: []}
    for hz in mids:
        ztop = P['FL'] + hz
        Pf = dict(P, D_beam=P['Dm'])
        for key in ('+', '-'):
            Bf = beam_2d(Pf, (ztop, 0.0), 0.0, sW)
            off = plate_lo[key]
            outer = _union([F.curve(q, off) for q in Bf['prims']], tol)
            outer = _inter(outer, F.curve(Bf['clip'], off), tol)
            out['floors'].append(_solid(F, outer, Bf['holes'], off, P['t'], tol))
        mid_heads[0].append(Bf['GE'])
        mid_heads[1].append(Bf['GW'])
        out['ptM'] += [F.P(Bf['GE'][0][0], Bf['GE'][0][1]), F.P(Bf['GW'][0][0], Bf['GW'][0][1])]

    if showcol:
        roof_outer0 = _union([F.curve(q, -P['gap'] / 2) for q in B0['prims']], tol)
        roof_outer0 = _inter(roof_outer0, F.curve(B0['clip'], -P['gap'] / 2), tol)
        for i, (Gs, w, G, h) in enumerate(((0.0, P['colE'], GE, hE), (sW, P['colW'], GW, hW))):
            C = column_2d(P, Gs, w, P['FL'], tops['0'][:2], [(G, h)] + mid_heads[i], G)
            off = -P['gap'] / 2
            body = _union([F.curve(q, off) for q in C['prims']], tol)
            clip = _union([roof_outer0, F.curve(C['band'], off)], tol)
            outer = _inter(body, clip, tol)
            out['cols'].append(_solid(F, outer, C['holes'], off, P['gap'], tol))

    out['ptE'] = F.P(GE[0], GE[1])
    out['ptW'] = F.P(GW[0], GW[1])
    out['axis'] = rg.Vector3d(p[0], p[1], 0)
    out['line'] = rg.LineCurve(F.P(0, P['FL']), F.P(sW, P['FL']))
    z0, m, dev = tops['0']
    row = dict(
        k=kk, u=3 * (kk - 1), th_deg=math.degrees(th), span=sW, s_wall=s_wall, s_tip=s_tip,
        slope_deg=math.degrees(math.atan(m)), topE=z0, topW=z0 + m * sW,
        gE=GE[1], gW=GW[1], length=(s_tip + hE['ha']), fit_dev=max(tops[k_][2] for k_ in tops),
        dtopE=tops['+'][0] - tops['-'][0],
        dtopW=(tops['+'][0] + tops['+'][1] * sW) - (tops['-'][0] + tops['-'][1] * sW),
        col=int(bool(showcol)), mids=';'.join('%.0f' % h for h in mids))
    return out, row


COLS = ['k', 'u', 'th_deg', 'span', 's_wall', 's_tip', 'slope_deg', 'topE', 'topW', 'gE', 'gW',
        'length', 'fit_dev', 'dtopE', 'dtopW', 'col', 'mids']


def run():
    tol = _tol()
    P = {n: _num(n) for n in DEF}
    roof_ = _in('roof')
    west_ = _in('west')
    ks = _in('k')
    if roof_ is None or west_ is None or ks is None:
        return None, '入力 roof・west・k が要る'
    if not isinstance(ks, (list, tuple)):
        ks = [ks]
    eave_ = _in('eave')
    cols_ = _in('showCol')
    mids_ = _in('mids')
    res = dict(plates=[], cols=[], floors=[], ptE=[], ptW=[], ptM=[], axis=[], lines=[])
    rows, log = [], []
    for i, kk in enumerate(ks):
        kk = float(kk)
        sc = _pick(cols_, i, True)
        mids_i = parse_mids(_pick(mids_, i, None))
        try:
            o, row = build_one(kk, roof_, west_, eave_, bool(sc), mids_i, P, tol)
        except Exception as ex:
            log.append('k%g：%s' % (kk, ex))
            continue
        for key in ('plates', 'cols', 'floors', 'ptM'):
            res[key] += o[key]
        res['ptE'].append(o['ptE'])
        res['ptW'].append(o['ptW'])
        res['axis'].append(o['axis'])
        res['lines'].append(o['line'])
        rows.append(row)
    lines = [','.join(COLS)]
    for r in rows:
        lines.append(','.join(('%.4g' % r[c]) if isinstance(r[c], float) else str(r[c]) for c in COLS))
    text = '\n'.join(lines)
    path = _in('csv')
    if path:
        try:
            with open(str(path), 'w', encoding='utf-8') as f:
                f.write(text + '\n')
            log.append('CSV：%s' % path)
        except Exception as ex:
            log.append('CSV を書けない：%s' % ex)
    log.append('架構 %d 本（失敗 %d）' % (len(rows), len(ks) - len(rows)))
    res['table'] = text
    return res, '\n'.join(log)


if _RHINO and 'roof' in globals():
    _res, log = run()
    if _res:
        plates, cols, floors = _res['plates'], _res['cols'], _res['floors']
        ptE, ptW, ptM = _res['ptE'], _res['ptW'], _res['ptM']
        axis, lines, table = _res['axis'], _res['lines'], _res['table']
