# -*- coding: utf-8 -*-
#! python 3
# r: shapely==2.0.6
"""
「架構」部品（遊戯室の架構、第4課題「架構と建築」）　2026-11-09夜に作り直し
版：VERSION（下の定数）。log の1行目にも出る。直すたびに日時を書き換える。
Rhino 8 Mac の Grasshopper、Python 3 のスクリプト部品に貼る。単位は mm。

一つの部品で、架構kの梁（2枚の板）・柱（東・内の列・西）・2階の床梁（あれば）を同時に作る。
Tamedia（Shigeru Ban、Zürich 2013）に倣う：
  - 柱は角材（既定300角）。2枚の板（既定160）が柱をじかに挟む。2枚のあいだ＝柱の幅＝光の筋。
  - 柱と板は互いに食い込む：板の頭（楕円）がまるごと、柱の両面の同じ形の欠き込みに入る（板の内の面に頭の形の突起）。
    頭の下の縁が柱の肩に載り、鉛直の力はその支圧で柱へ。回転は楕円の桁と楕円の食い込みで止める。
    柱は頭の下で広がり、頭の中では頭の形いっぱい（欠き込みの分だけ細い芯が板のあいだを上へ通る）。
  - 楕円の桁（既定180×260）が板と柱の穴を通り、回転を止める。
  - 梁は内の柱の列の上を途切れずに続く（連続梁）。長いスパンの下端は端で深く真ん中で浅いカーブ。
  - 板の端・柱の上には、桁の穴を包む楕円の頭。頭は下端より下がり、下端とはハンチでつながる。柱は頭の下で広がる。
  - 形は寸法を写さず、Tamediaの詳細図の比で梁のせい D から決める：
    桁の中心は下端から 0.14D、頭は半幅 0.58D・半高さ 0.68D（穴のまわりに木 120 以上）、ハンチ 1.1D、柱の広がり 0.55D。
西の端は、頭と軒先への細い延長を一つの板にする（せい240→先で120、先は鉛直、丸み300でつなぐ）。

架構の位置：背骨（西館の東の柱の列）の円弧の中心からの放射の直線。
  架構kは u＝3(k−1) m、u は本館の背骨の円弧（v＝0）の上で測る（育ち舎の uv.py・3dm と同じ、k15.5 も可）。
  東の柱の芯は東の壁の内面 v−1.05 から柱の幅の半分の内。内の列は v（vIn）で指定。西の柱の芯は west から柱の幅の半分の内。
梁の上端：屋根の面（Brep）と、各板の真ん中の鉛直面の交線を直線で近似（ずれは CSV に出す）。
  屋根の面を差し替えれば、A・B・C 案の架構がそのまま作り直される。
例外は「柱を出すか」だけ。それ以外は Bake してから手で直す。

入力（必須）  roof：屋根の面（梁の上端の面、Brep、Item）
               k：架構の番号（float、List）
               west：西の柱の外の面＝外壁の内面の線（平面の曲線、Curve、Item）
入力（任意、無ければ既定の値。部品に入力を足したものだけ効く）
               vU：u を測る円弧の v（m、float、Item）。既定 0＝本館の背骨の円弧（育ち舎の uv.py・3dm の架構と同じ）
               vIn：内の柱の列の v（m、正の数、float、List。既定 [3.4]＝2階の柱の線。空にするには 0 を一つ）
               eave：軒先の線（Curve、Item）。無ければ外壁の内面から EAVE_OUT
               showCol：柱を出すか（bool、List。1つなら全部に、kと同じ数なら1本ずつ）
               mids：2階の床梁の上端の高さ（FL から、str、List。"3200"、無しは空。kと同じ数か1つ）
               FL・D・Dm・t・col・key・Df・eR・haR・hbR（float、Item）
               csv：CSV を書くファイルの道（str、Item）
出力           spine（v−0.9・東の柱の芯・内の列の円弧）・rays（架構kの放射の線）：k だけつなげば出る下書き
               plates（板、キー付き）・cols（柱、欠き込み付き）・floors（2階の床梁）
               ptE・ptI・ptW・ptM（桁が通る点）・axis（桁の向き）・lines（架構の線）・table（CSV の文）・log
"""
import math

VERSION = 'kakou 2026-11-11 09:10'

# ------------------------------------------------------------------ 既定の値（mm）
DEF = dict(
    FL=0.0,
    D=500.0,      # 梁のせい：支点の所（鉛直）。ryakusan/shin_1109.py
    Dm=400.0,     # 梁のせい：長いスパンの真ん中
    t=160.0,      # 板の厚さ（Tamediaに合わせる、ユーザー 11-09）
    col=300.0,    # 柱の幅（角材）＝2枚のあいだ＝光の筋（ユーザー 11-09）
    key=50.0,     # 食い込みの深さ（片側、柱の幅の約0.17、Tamedia 77/440）
    Df=400.0,     # 2階の床梁のせい
    eR=0.14,      # 桁の中心の、梁の下端からの高さ／D（Tamedia）
    haR=0.58,     # 頭の楕円の半幅／D
    hbR=0.68,     # 頭の楕円の半高さ／D
    ext0=240.0,   # 軒への延長のせい（外壁の内面で）
    ext1=120.0,   # 同（先で）
)
V_IN = [3.4]                        # 内の柱の列の v（m）
GIRDER_A, GIRDER_B = 90.0, 130.0    # 桁（楕円 180×260）の半径（Tamediaの比：柱の幅の0.6）
HOLE_CLR = 5.0                      # 穴は桁の断面＋10（半径で＋5）
WOOD_MIN = 120.0                    # 桁の穴のまわりに残す木
HAUNCH_RR = 1.1                     # 梁の下端と頭のつなぎの丸み／D（Tamedia R600／せい550）
COL_RR = 0.55                       # 柱の面と頭のつなぎの丸み／D
LONG_SPAN = 4000.0                  # これより長いスパンは下端をカーブに（短いスパンは D 一定）
EAVE_R = 300.0                      # 延長の下端と頭のつなぎ
TIP_GAP = 100.0                     # 延長の先は軒先の線の0.1手前（線に直角に測る）
EAVE_OUT = 980.0                    # eave が無いときの屋根の縁：外壁の内面から（壁200＋軒の出0.78。軒樋まで0.9で敷地の境の0.1手前）
V_EAST_FACE = 1050.0                # 東の柱の外の面＝西館の東の壁の内面 v−1.05
V_U = 0.0                           # u を測る円弧の v（mm）。0＝本館の背骨（uv.py と同じ、ユーザー 11-09）。入力 vU（m）で変えられる
V_EAST_OUT = 900.0                  # 西館の東の壁の外面 v−0.9（下書きの円弧）
PITCH = 3000.0
# 本館の (u, v) の円（kadai/sodachiya/model/build/south/uv.py と同じ定数）
CX, CY, RW = 194662.93237, -41348.26335, 205017.7
TH_S = math.atan2(-65173.47495 - CY, -8965.4788 - CX) % (2 * math.pi)


# ================================================================== 2D の核（Rhino を使わない）
# 架構ごとの平面の座標 (s, z)：s は東の柱の芯から西へ、z は高さ（世界の z）。
# 形は「基本形」の和で表し、Rhino の側で曲線にして足し合わせる。
#   ('poly', [(s,z),...])                 閉じた多角形
#   ('body', [(s,z) 上端], [(s,z) 下端])   上端は直線、下端はなめらかな曲線（点を通る）
#   ('aff', kind, s0, z0, a11, a12, a21, a22)
#        単位円（kind='circle'）か上半分の単位円（'half'）を (s,z)=(s0+a11x+a12y, z0+a21x+a22y) へ写したもの
#   ('fillet', T1, cf, R, T2, I)          T1→（中心cf、半径Rの円弧）→T2→I→T1

def frame_axis(k, col):
    """架構kの東の柱の芯 O（平面）と向き dir（西へ）・perp（dir を左へ90°）"""
    th = TH_S - PITCH * (k - 1.0) / (RW + V_U)
    c, s = math.cos(th), math.sin(th)
    r = RW + V_EAST_FACE + col / 2.0
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


def _arc_pts(T1, cf, T2, n):
    a1 = math.atan2(T1[1] - cf[1], T1[0] - cf[0])
    a2 = math.atan2(T2[1] - cf[1], T2[0] - cf[0])
    da = (a2 - a1 + math.pi) % (2 * math.pi) - math.pi
    R = math.hypot(T1[0] - cf[0], T1[1] - cf[1])
    return [(cf[0] + R * math.cos(a1 + da * i / n), cf[1] + R * math.sin(a1 + da * i / n)) for i in range(1, n)]


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



def head_size(P, D):
    """せい D の梁の頭の大きさ（Tamediaの比、桁の穴のまわりに木 WOOD_MIN 以上）"""
    return dict(e=P['eR'] * D,
                ha=max(P['haR'] * D, GIRDER_A + HOLE_CLR + WOOD_MIN),
                hb=max(P['hbR'] * D, GIRDER_B + HOLE_CLR + WOOD_MIN),
                R=HAUNCH_RR * D, Rc=COL_RR * D)


def ellipse(c, a, b):
    return ('aff', 'circle', c[0], c[1], a, 0.0, 0.0, b)


def depth_fn(supports, De, Dm):
    """支点の s の並びから、梁のせいの関数。長いスパンは端 De→真ん中 Dm の放物線、短いスパンは De"""
    sp = sorted(supports)

    def D(s):
        for a, b in zip(sp[:-1], sp[1:]):
            if a <= s <= b and b - a >= LONG_SPAN:
                x = (s - a) / (b - a)
                return Dm + (De - Dm) * (2 * x - 1) ** 2
        return De
    return D


def _haunch(G, h, side, soffit):
    """支点 G の side（+1＝西、−1＝東）の側の、梁の下端と頭の入隅。soffit(s)＝下端の z"""
    R = h['R']
    sf = G[0] + side * 1.5 * R
    ms = soffit(sf + 1.0) - soffit(sf)
    far = G[0] + side * 4 * R
    p0 = (far, soffit(sf) + ms * (far - sf))
    L = math.hypot(1.0, ms)
    d = (-side / L, -side * ms / L)
    n = (d[1], -d[0])
    if n[1] > 0:
        n = (-n[0], -n[1])
    return fillet(p0, d, n, G, h['ha'], h['hb'], R, G)


def beam_2d(P, top, supports, Dfn, ext=None):
    """梁（または2階の床梁）の板の外形の基本形・上端で切る多角形・穴・頭の点。
    top=(z0, m)。supports：支点の s（東から西へ、両端が端の支点）。Dfn(s)：せい。
    ext=(s_wall, s_tip)：西の端の軒への延長"""
    z0, m = top
    zt = lambda s: z0 + m * s
    soffit = lambda s: zt(s) - Dfn(s)
    sE, sW = supports[0], supports[-1]
    n = max(40, int((sW - sE) / 20))     # 下端は細かく取り、Rhino の側でなめらかな曲線に戻す
    ss = [sE + (sW - sE) * i / n for i in range(n + 1)]
    pr = [('body', [(sE, zt(sE)), (sW, zt(sW))], [(s, soffit(s)) for s in ss])]
    heads = []
    for j, s in enumerate(supports):
        h = head_size(P, Dfn(s))
        G = (s, soffit(s) + h['e'])
        heads.append((G, h))
        pr.append(ellipse(G, h['ha'], h['hb']))
        if j in (0, len(supports) - 1):
            # 外の端：上端の直線に接するよう傾けた上半分の楕円（端の上の角）
            H = zt(s) - G[1]
            pr.append(('aff', 'half', G[0], G[1], h['ha'], 0.0, m * h['ha'], H))
            if abs(m) > 1e-6:
                pr.append(('poly', [(G[0] - h['ha'], G[1]), (G[0] + h['ha'], G[1]),
                                    (G[0] + h['ha'], G[1] + m * h['ha']), (G[0] - h['ha'], G[1] - m * h['ha'])]))
        for side in (-1, 1):
            if (j == 0 and side < 0) or (j == len(supports) - 1 and side > 0):
                continue
            fl = _haunch(G, h, side, soffit)
            if fl:
                pr.append(fl)
    hW = heads[-1][1]
    s_hi = sW + hW['ha'] + 10
    if ext:
        s_wall, s_tip = ext
        a0, a1 = P['ext0'], P['ext1']
        GW = heads[-1][0]
        pr.append(('poly', [(sW, zt(sW)), (s_tip, zt(s_tip)), (s_tip, zt(s_tip) - a1),
                            (s_wall, zt(s_wall) - a0), (sW, zt(sW) - a0)]))
        # 延長の下端と頭の上の丸みの入隅：傾きを除いた座標（z' = z − m(s−sW)）で楕円として扱い、戻す
        H = zt(sW) - GW[1]
        q = lambda s, z: (s, z - m * (s - sW))
        r = lambda s, z: (s, z + m * (s - sW))
        pA, pB = q(s_tip, zt(s_tip) - a1), q(s_wall, zt(s_wall) - a0)
        L = math.hypot(pB[0] - pA[0], pB[1] - pA[1])
        d = ((pB[0] - pA[0]) / L, (pB[1] - pA[1]) / L)
        nn = (d[1], -d[0])
        if nn[1] > 0:
            nn = (-nn[0], -nn[1])
        fl = fillet(pA, d, nn, GW, hW['ha'], H, EAVE_R, (GW[0], GW[1] + 0.85 * H))
        if fl:
            _, T1, cf, R, T2, I = fl
            pr.append(('poly', [r(*T1)] + [r(*p) for p in _arc_pts(T1, cf, T2, 16)] + [r(*T2), r(*I)]))
        s_hi = s_tip
    s_lo = sE - heads[0][1]['ha'] - 10
    big = 20000.0
    clip = ('poly', [(s_lo - 1, zt(s_lo - 1)), (s_hi + 1, zt(s_hi + 1)),
                     (s_hi + 1, zt(s_hi) - big), (s_lo - 1, zt(s_lo) - big)])
    holes = [ellipse(G, GIRDER_A + HOLE_CLR, GIRDER_B + HOLE_CLR) for G, h in heads]
    return dict(prims=pr, clip=clip, holes=holes, heads=heads, s_lo=s_lo, s_hi=s_hi)


def prim_pts(prim, seg=8.0):
    """基本形を (s,z) の閉じた点の並びに（弧は弦 seg 以下）。外形の和を2Dで取るため"""
    kind = prim[0]
    if kind == 'poly':
        return list(prim[1])
    if kind == 'body':
        _, tp, bt = prim
        return [tp[0], tp[1]] + list(reversed(bt))
    if kind == 'aff':
        _, which, s0, z0, a11, a12, a21, a22 = prim
        r = max(math.hypot(a11, a21), math.hypot(a12, a22))
        n = max(48, int(2 * math.pi * r / seg))
        if which == 'circle':
            uv = [(math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)) for i in range(n)]
        else:
            m = n // 2
            uv = [(math.cos(math.pi * i / m), math.sin(math.pi * i / m)) for i in range(m + 1)]
        return [(s0 + a11 * x + a12 * y, z0 + a21 * x + a22 * y) for x, y in uv]
    if kind == 'fillet':
        _, T1, cf, R, T2, I = prim
        n = max(8, int(R * math.pi / 2 / seg))
        return [T1] + _arc_pts(T1, cf, T2, n) + [T2, I]
    raise ValueError(kind)


def outline_2d(prims, clips):
    """基本形の和を、clips（基本形の list の list：各組の和）で順に切った外形。shapely で（無ければ None）。
    返すのは (s,z) の外の輪郭の点の並び（いちばん大きい一つ）"""
    try:
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
    except ImportError:
        return None
    poly = lambda q: Polygon(prim_pts(q)).buffer(0)
    g = unary_union([poly(q) for q in prims])
    for grp in clips:
        g = g.intersection(unary_union([poly(q) for q in grp]))
    if g.is_empty:
        return []
    parts = list(g.geoms) if hasattr(g, 'geoms') else [g]
    parts = [p for p in parts if p.geom_type == 'Polygon']
    if not parts:
        return []
    big = max(parts, key=lambda p: p.area)
    big = big.simplify(0.05)
    return list(big.exterior.coords)[:-1]


try:
    import shapely  # noqa: F401
    HAVE_SHAPELY = True
except ImportError:
    HAVE_SHAPELY = False


def _sp(prim):
    from shapely.geometry import Polygon
    return Polygon(prim_pts(prim)).buffer(0)


def _holes_g(prims):
    from shapely.ops import unary_union
    return unary_union([_sp(q) for q in prims])


def region_2d(prims, clips=(), minus=()):
    """shapely の形：基本形の和を clips の各組の和で切り、いちばん大きい一つを取り、minus（基本形）を引く"""
    from shapely.ops import unary_union
    g = unary_union([_sp(q) for q in prims])
    for grp in clips:
        g = g.intersection(unary_union([_sp(q) for q in grp]))
    parts = [x for x in (list(g.geoms) if hasattr(g, 'geoms') else [g]) if x.geom_type == 'Polygon']
    if not parts:
        return None
    g = max(parts, key=lambda x: x.area)
    if minus:
        g = g.difference(unary_union([_sp(q) for q in minus]))
    return g


def _dedup(ring, eps=0.5):
    """近すぎる点を除く（閉じた並び）"""
    out = []
    for q in ring:
        if not out or math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) > eps:
            out.append(q)
    while len(out) > 2 and math.hypot(out[0][0] - out[-1][0], out[0][1] - out[-1][1]) <= eps:
        out.pop()
    return out


def polys_2d(g, min_area=100.0):
    """shapely の形 → [(外の点の並び, [穴の点の並び])]（小さな切れ端は捨てる）"""
    if g is None or g.is_empty:
        return []
    out = []
    for x in (list(g.geoms) if hasattr(g, 'geoms') else [g]):
        if x.geom_type != 'Polygon' or x.area < min_area:
            continue
        out.append((_dedup(list(x.exterior.coords)[:-1]), [_dedup(list(r.coords)[:-1]) for r in x.interiors]))
    return out


CORNER_DEG = 20.0      # これより大きく折れる点は角（曲線を分ける）
LINE_MIN = 40.0        # これより長い辺は直線のまま


def smooth_runs(ring):
    """閉じた点の並び（2D）を、直線と曲線の区切りに分ける。
    返す：[('line', p, q) | ('curve', [点…])]（順につながる）、角が一つも無く短い辺だけなら [('closed', [点…])]"""
    n = len(ring)
    if n < 3:
        return []

    def turn(i):
        a, b, c = ring[i - 1], ring[i], ring[(i + 1) % n]
        u = (b[0] - a[0], b[1] - a[1])
        v = (c[0] - b[0], c[1] - b[1])
        return abs(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])))

    seglen = lambda i: math.hypot(ring[(i + 1) % n][0] - ring[i][0], ring[(i + 1) % n][1] - ring[i][1])
    # 区切りの点：角、または長い辺の端
    brk = [i for i in range(n) if turn(i) >= CORNER_DEG or seglen(i) >= LINE_MIN or seglen(i - 1) >= LINE_MIN]
    if not brk:
        return [('closed', list(ring))]
    runs = []
    for j, i0 in enumerate(brk):
        i1 = brk[(j + 1) % len(brk)]
        k = (i1 - i0) % n or n
        pts = [ring[(i0 + t) % n] for t in range(k + 1)]
        if len(pts) == 2:
            runs.append(('line', pts[0], pts[1]))
        else:
            runs.append(('curve', pts))
    return runs


def key_shape(G, h, grow=0.0):
    """食い込み（板のキー・柱の欠き込み）の外形：頭の楕円そのもの（Tamediaの写真：板の頭がまるごと柱に食い込み、
    頭の下の縁が柱の肩に載る）。grow：欠き込みを少し大きくするとき"""
    return ellipse(G, h['ha'] + grow, h['hb'] + grow)


def column_2d(Gs, w, FL, ztop, heads, roofG):
    """柱（架構の面）。heads：この柱に取りつく頭 [(点, 大きさ)]（屋根と2階）。roofG：屋根の頭の点。
    返すのは柱の基本形（足し合わせる）と、切る形（屋根の板の外形と足す、屋根の頭より下の帯）"""
    pr = [('poly', [(Gs - w / 2, FL), (Gs + w / 2, FL), (Gs + w / 2, ztop + 2000), (Gs - w / 2, ztop + 2000)])]
    for G, h in heads:
        pr.append(ellipse(G, h['ha'], h['hb']))     # 柱は頭の中では頭の形いっぱい（下から見て、広がりが頭の下端に取りつく）
        for side in (-1, 1):
            nrm = (side, 0.0)
            fl = fillet((Gs + side * w / 2, FL), (0.0, 1.0), nrm, G, h['ha'], h['hb'], h['Rc'], G)
            if fl:
                pr.append(fl)
            if G is not roofG:      # 2階の頭は上からも
                fl = fillet((Gs + side * w / 2, roofG[1]), (0.0, -1.0), nrm, G, h['ha'], h['hb'], h['Rc'], G)
                if fl:
                    pr.append(fl)
    band = ('poly', [(Gs - w / 2 - 3000, FL - 1), (Gs + w / 2 + 3000, FL - 1),
                     (Gs + w / 2 + 3000, roofG[1]), (Gs - w / 2 - 3000, roofG[1])])
    holes = [ellipse(G, GIRDER_A + HOLE_CLR, GIRDER_B + HOLE_CLR) for G, h in heads]
    keys = [key_shape(G, h, 3.0) for G, h in heads]
    return dict(prims=pr, band=band, holes=holes, keys=keys)


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


def _raw(x):
    """GH の型（GH_String・GH_Number など）なら中の値を出す"""
    for _ in range(3):
        if hasattr(x, 'Value') and not isinstance(x, (str, int, float)):
            try:
                x = x.Value
                continue
            except Exception:
                pass
        break
    return x


def _f(x):
    """GH から来た値を数に（文字・数・GH の型・.NET の型のどれでも）"""
    x = _raw(x)
    try:
        return float(x)
    except Exception:
        pass
    try:
        return float(str(x).strip())
    except Exception:
        raise ValueError('数にできない：%r' % (str(x)[:40],))


def _as_list(v):
    """GH の List Access（Python の list でも .NET の List でも）と、一つの値を、Python の list に（中の値を出して）"""
    if v is None:
        return []
    if isinstance(v, (str, bytes)):
        return [v]
    try:
        return [_raw(x) for x in v]
    except TypeError:
        return [_raw(v)]


def _nums(v):
    """数の並び：list の中の文字に改行・カンマ・空白で並んだ数があれば、分けて数に（Panel の Multiline Data が切ってあるとき）"""
    out = []
    for x in _as_list(_raw(v) if isinstance(_raw(v), str) else v):
        if isinstance(x, str):
            out += [float(q) for q in x.replace(',', ' ').replace(';', ' ').split()]
        else:
            out.append(_f(x))
    return out


def _num(name):
    v = _in(name)
    return _f(v) if v is not None else DEF[name]


def _pick(lst, i, default):
    """1つなら全部に、k と同じ数なら i 番目"""
    if lst is None:
        return default
    lst = _as_list(lst)
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
        if kind == 'body':
            _, tp, bt = prim
            soff = rg.Curve.CreateInterpolatedCurve([self.P(s, z, off) for s, z in bt], 3)
            a, b = self.P(tp[0][0], tp[0][1], off), self.P(tp[1][0], tp[1][1], off)
            segs = [rg.LineCurve(a, b), rg.LineCurve(b, soff.PointAtEnd), soff, rg.LineCurve(soff.PointAtStart, a)]
            j = rg.Curve.JoinCurves(segs, 0.01)
            return j[0]
        if kind == 'aff':
            _, which, s0, z0, a11, a12, a21, a22 = prim
            if which == 'circle':
                c = rg.Circle(rg.Plane.WorldXY, 1.0).ToNurbsCurve()
            else:
                arc = rg.Arc(rg.Plane.WorldXY, 1.0, math.pi).ToNurbsCurve()
                ln = rg.LineCurve(rg.Point3d(-1, 0, 0), rg.Point3d(1, 0, 0))
                c = rg.Curve.JoinCurves([arc, ln], 0.001)[0].ToNurbsCurve()
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


def _outline(F, prims, clips, off, tol, rh_clips=None):
    """外形：shapely があれば2Dで和と切り取り（点の並び→ポリライン）。無ければ Rhino の曲線の和・積。
    rh_clips：Rhino の道で使う、切る曲線（無ければ clips の各組の和）"""
    pts = outline_2d(prims, clips)
    if pts is not None:
        if len(pts) < 3:
            raise RuntimeError('外形が空')
        q = [F.P(a, b, off) for a, b in pts]
        q.append(q[0])
        return rg.PolylineCurve(q)
    outer = _union([F.curve(x, off) for x in prims], tol)
    for c in (rh_clips if rh_clips is not None else [_union([F.curve(x, off) for x in g], tol) for g in clips]):
        outer = _inter(outer, c, tol)
    return outer


def _solid(F, outer, holes2d, off, thick, tol):
    """外形（off の面）と穴から、+perp へ thick の押し出しの立体"""
    crvs = [outer] + [F.curve(h, off) for h in holes2d]
    br = rg.Brep.CreatePlanarBreps(crvs, tol)
    if not br:
        raise RuntimeError('平らな面ができない')
    face = br[0].Faces[0]
    path = rg.LineCurve(F.P(0, 0, off), F.P(0, 0, off + thick))
    s = face.CreateExtrusion(path, True)
    if s is None:
        raise RuntimeError('押し出しができない')
    return s


def _ring_curve(F, ring, off, tol):
    """2Dの点の並び → 直線となめらかな曲線をつないだ閉じた曲線"""
    runs = smooth_runs(ring)
    if runs and runs[0][0] == 'closed':
        pts = [F.P(a, b, off) for a, b in runs[0][1]]
        c = rg.Curve.CreateInterpolatedCurve(pts, 3, rg.CurveKnotStyle.ChordPeriodic)
        f = c.Fit(3, 0.1, 0.0) if c is not None else None
        return f if f is not None and f.IsClosed else c
    segs = []
    for r in runs:
        if r[0] == 'line':
            segs.append(rg.LineCurve(F.P(r[1][0], r[1][1], off), F.P(r[2][0], r[2][1], off)))
        else:
            pts = [F.P(a, b, off) for a, b in r[1]]
            c = rg.Curve.CreateInterpolatedCurve(pts, 3)
            if c is None:
                c = rg.PolylineCurve(pts)
            else:
                f = c.Fit(3, 0.1, 0.0)
                if f is not None:
                    c = f
            segs.append(c)
    j = rg.Curve.JoinCurves(segs, 0.05)
    if j and len(j) == 1 and j[0].IsClosed:
        return j[0]
    q = [F.P(a, b, off) for a, b in ring]
    q.append(q[0])
    return rg.PolylineCurve(q)


def _slabs(F, g, off, thick, tol):
    """shapely の形を、off の面から +perp へ thick 押し出した立体（形が分かれていれば複数）"""
    out = []
    for ext, holes in polys_2d(g):
        crvs = []
        for ring in [ext] + holes:
            crvs.append(_ring_curve(F, ring, off, tol))
        br = rg.Brep.CreatePlanarBreps(crvs, tol)
        if not br:
            raise RuntimeError('平らな面ができない')
        path = rg.LineCurve(F.P(0, 0, off), F.P(0, 0, off + thick))
        sld = br[0].Faces[0].CreateExtrusion(path, True)
        if sld is None:
            raise RuntimeError('押し出しができない')
        out.append(sld)
    return out


def _join(pieces, tol, fails, what):
    """層の立体を一つに（面で接するだけの和）。できなければ層のまま返し、fails に数える"""
    if len(pieces) <= 1:
        return pieces
    try:
        r = rg.Brep.CreateBooleanUnion(pieces, tol)
        if r and len(r) == 1 and r[0].IsSolid:
            r[0].MergeCoplanarFaces(tol)
            return [r[0]]
    except Exception:
        pass
    fails[what] = fails.get(what, 0) + 1
    return pieces


def _bool(kind, a, bs, tol, log, what):
    """立体の和・差。できなければ元のまま（和は部品を並べて）返し、log に書く"""
    try:
        if kind == 'union':
            r = rg.Brep.CreateBooleanUnion([a] + bs, tol)
        else:
            r = rg.Brep.CreateBooleanDifference([a], bs, tol)
        if r and len(r) == 1:
            return [r[0]]
    except Exception:
        pass
    log.append('%s：立体の%sができず、別の部品のまま' % (what, '和' if kind == 'union' else '差'))
    return [a] + (bs if kind == 'union' else [])


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
            best = (s, flat.TangentAt(x.ParameterB))
    return best


def build_one(kk, roof, west, eave, showcol, mids, vin, P, tol, log, fails):
    w = P['col']
    O, d, p, th = frame_axis(kk, w)
    F = Frame3(O, d, p)
    hw = _hit_s(F, west)
    if hw is None:
        raise RuntimeError('架構の線が西の線と交わらない')
    s_wall = hw[0]
    sW = s_wall - w / 2.0
    if eave is not None:
        he = _hit_s(F, eave, s_wall)
        if he is None:
            raise RuntimeError('架構の線が軒先の線と交わらない')
        tg = he[1]
        cosphi = abs(-tg.Y * d[0] + tg.X * d[1]) / max(1e-9, math.hypot(tg.X, tg.Y))
        s_tip = he[0] - TIP_GAP / max(cosphi, 0.2)
    else:
        s_tip = s_wall + EAVE_OUT - TIP_GAP
    s_in = sorted(v * 1000.0 - (V_EAST_FACE + w / 2) for v in vin if v > 0)
    s_in = [s for s in s_in if 500 < s < sW - 500]
    sup = [0.0] + s_in + [sW]
    Dfn = depth_fn(sup, P['D'], P['Dm'])
    s_lo, s_hi = -head_size(P, P['D'])['ha'] - 300, s_tip + 10
    offs = {'+': w / 2 + P['t'] / 2, '-': -(w / 2 + P['t'] / 2), '0': 0.0}
    tops = {}
    for key, off in offs.items():
        try:
            tops[key] = _top_fit(F, roof, off, s_lo, s_hi, tol)
        except RuntimeError:
            tops[key] = None
    if tops['0'] is None:
        raise RuntimeError('屋根の面と交わらない（架構の線の上）')
    for a, b in (('+', '-'), ('-', '+')):
        if tops[a] is None:
            # 端の架構の外の板が屋根の面の外：架構の線と内の板から延ばす（板の面は架構の線に対して対称）
            if tops[b] is None:
                tops[a] = tops['0']
            else:
                tops[a] = (2 * tops['0'][0] - tops[b][0], 2 * tops['0'][1] - tops[b][1], tops['0'][2])
            log.append('k%g：%s の板は屋根の面の外なので、架構の線と内の板から延ばした' % (kk, '東南' if a == '+' else '北西'))

    out = dict(plates=[], cols=[], floors=[], ptM=[])
    tag = 'k%g' % kk
    colpos = sup if showcol else []
    # 板（2枚、上端は板ごとの直線）。穴・キー・頭の点は架構の面の上端（'0'）で決め、2枚で同じにする
    B0 = beam_2d(P, tops['0'][:2], sup, Dfn, ext=(s_wall, s_tip))
    for key in ('+', '-'):
        B = beam_2d(P, tops[key][:2], sup, Dfn, ext=(s_wall, s_tip))
        sgn = 1 if key == '+' else -1
        w_, t_, kd = P['col'], P['t'], P['key']
        off = w_ / 2 if sgn > 0 else -(w_ / 2 + t_)
        if HAVE_SHAPELY:
            g = region_2d(B['prims'], [[B['clip']]])
            pcs = _slabs(F, g.difference(_holes_g(B0['holes'])), off, t_, tol)
            if colpos and kd > 0:
                kg = _holes_g([key_shape(G, h) for G, h in B0['heads']]).difference(_holes_g(B0['holes'])).intersection(g)
                koff = w_ / 2 - kd if sgn > 0 else -(w_ / 2)
                pcs += _slabs(F, kg, koff, kd, tol)
            out['plates'] += pcs
            continue
        outer = _outline(F, B['prims'], [[B['clip']]], off, tol)
        pl = _solid(F, outer, B0['holes'], off, t_, tol)
        if colpos and kd > 0:
            koff = w_ / 2 - kd if sgn > 0 else -(w_ / 2) - 1.0
            keys = [_solid(F, F.curve(key_shape(G, h), koff), [ellipse(G, GIRDER_A + HOLE_CLR, GIRDER_B + HOLE_CLR)],
                           koff, kd + 1.0, tol) for G, h in B0['heads']]
            out['plates'] += _bool('union', pl, keys, tol, log, tag + '板')
        else:
            out['plates'].append(pl)
    heads = B0['heads']

    # 2階の床梁（上端は水平、支点は同じ）
    mid_heads = {i: [] for i in range(len(sup))}
    for hz in mids:
        ztop = P['FL'] + hz
        Pf = dict(P)
        Dff = lambda s: P['Df']
        Bf = beam_2d(Pf, (ztop, 0.0), sup, Dff)
        for sgn in (1, -1):
            off = w / 2 if sgn > 0 else -(w / 2 + P['t'])
            if HAVE_SHAPELY:
                g = region_2d(Bf['prims'], [[Bf['clip']]])
                pcs = _slabs(F, g.difference(_holes_g(Bf['holes'])), off, P['t'], tol)
                if colpos and P['key'] > 0:
                    kg = _holes_g([key_shape(G, h) for G, h in Bf['heads']]).difference(_holes_g(Bf['holes'])).intersection(g)
                    koff = w / 2 - P['key'] if sgn > 0 else -(w / 2)
                    pcs += _slabs(F, kg, koff, P['key'], tol)
                out['floors'] += pcs
                continue
            outer = _outline(F, Bf['prims'], [[Bf['clip']]], off, tol)
            pl = _solid(F, outer, Bf['holes'], off, P['t'], tol)
            if colpos and P['key'] > 0:
                koff = w / 2 - P['key'] if sgn > 0 else -(w / 2) - 1.0
                keys = [_solid(F, F.curve(key_shape(G, h), koff), [ellipse(G, GIRDER_A + HOLE_CLR, GIRDER_B + HOLE_CLR)],
                               koff, P['key'] + 1.0, tol) for G, h in Bf['heads']]
                out['floors'] += _bool('union', pl, keys, tol, log, tag + '床梁')
            else:
                out['floors'].append(pl)
        for i, gh in enumerate(Bf['heads']):
            mid_heads[i].append(gh)
            out['ptM'].append(F.P(gh[0][0], gh[0][1]))

    # 柱（東・内の列・西）：架構の面で外形 → 押し出し → 両面の欠き込み
    if showcol:
        o0 = outline_2d(B0['prims'], [[B0['clip']]])
        roof_outer0 = None if o0 is not None else _outline(F, B0['prims'], [[B0['clip']]], -w / 2, tol)
        z0, m, _ = tops['0']
        for i, s in enumerate(sup):
            G, h = heads[i]
            C = column_2d(s, w, P['FL'], z0 + m * s, [(G, h)] + mid_heads[i], G)
            off = -w / 2
            if HAVE_SHAPELY:
                # 層で作る：芯（欠き込みの奥、穴あり）と両面の層（頭の形の欠き込みを抜く）。立体の差は使わない
                g = region_2d(C['prims'], [[('poly', o0), C['band']]])
                kd = P['key']
                if kd > 0:
                    pcs = _slabs(F, g.difference(_holes_g(C['holes'])), -w / 2 + kd, w - 2 * kd, tol)
                    face = g.difference(_holes_g(C['keys'] + C['holes']))
                    pcs += _slabs(F, face, -w / 2, kd, tol) + _slabs(F, face, w / 2 - kd, kd, tol)
                else:
                    pcs = _slabs(F, g.difference(_holes_g(C['holes'])), -w / 2, w, tol)
                out['cols'] += pcs
                continue
            if o0 is not None:
                outer = _outline(F, C['prims'], [[('poly', o0), C['band']]], off, tol)
            else:
                clip = _union([roof_outer0, F.curve(C['band'], off)], tol)
                outer = _outline(F, C['prims'], [], off, tol, rh_clips=[clip])
            col = _solid(F, outer, C['holes'], off, w, tol)
            if P['key'] > 0:
                cuts = []
                for big in C['keys']:
                    cuts.append(_solid(F, F.curve(big, w / 2 - P['key']), [], w / 2 - P['key'], P['key'] + 5, tol))
                    cuts.append(_solid(F, F.curve(big, -w / 2 - 5), [], -w / 2 - 5, P['key'] + 5, tol))
                out['cols'] += _bool('diff', col, cuts, tol, log, tag + '柱')
            else:
                out['cols'].append(col)

    out['ptE'] = F.P(heads[0][0][0], heads[0][0][1])
    out['ptW'] = F.P(heads[-1][0][0], heads[-1][0][1])
    out['ptI'] = [F.P(G[0], G[1]) for G, h in heads[1:-1]]
    out['axis'] = rg.Vector3d(p[0], p[1], 0)
    out['line'] = rg.LineCurve(F.P(0, P['FL']), F.P(sW, P['FL']))
    z0, m, dev = tops['0']
    row = dict(
        k=kk, u=3 * (kk - 1), th_deg=math.degrees(th), sW=sW, s_in=';'.join('%.0f' % s for s in s_in),
        span_main=(sW - (s_in[-1] if s_in else 0.0)), s_wall=s_wall, s_tip=s_tip,
        slope_deg=math.degrees(math.atan(m)), topE=z0, topW=z0 + m * sW,
        gE=heads[0][0][1], gW=heads[-1][0][1], D=P['D'], Dm=P['Dm'], fit_dev=max(tops[k_][2] for k_ in tops),
        dtopE=tops['+'][0] - tops['-'][0],
        dtopW=(tops['+'][0] + tops['+'][1] * sW) - (tops['-'][0] + tops['-'][1] * sW),
        col=int(bool(showcol)), mids=';'.join('%.0f' % h for h in mids))
    return out, row


COLS = ['k', 'u', 'th_deg', 'sW', 's_in', 'span_main', 's_wall', 's_tip', 'slope_deg', 'topE', 'topW', 'gE', 'gW',
        'D', 'Dm', 'fit_dev', 'dtopE', 'dtopW', 'col', 'mids']


def uv_xy(u, v):
    """育ち舎の (u, v)（m、u は V_U の円弧の上で測る、既定は本館の背骨 v＝0）→ 世界の点（mm）"""
    th = TH_S - u * 1000.0 / (RW + V_U)
    r = RW + v * 1000.0
    return rg.Point3d(CX + r * math.cos(th), CY + r * math.sin(th), 0.0)


def guides(ks, vin, w, FL):
    """屋根や壁を描く前の下書き：西館の東の壁の外面の円弧（v−0.9）・東の柱の芯の円弧・内の列の円弧と、架構kの放射の線（v−0.9→v−17）"""
    u0, u1 = 3 * (min(ks) - 1) - 1.5, 3 * (max(ks) - 1) + 1.5
    arcs = []
    for v in [V_EAST_OUT / 1000.0, (V_EAST_FACE + w / 2) / 1000.0] + [x for x in vin if x > 0]:
        c = rg.ArcCurve(rg.Arc(uv_xy(u0, v), uv_xy((u0 + u1) / 2, v), uv_xy(u1, v)))
        c.Translate(rg.Vector3d(0, 0, FL))
        arcs.append(c)
    rays = []
    for k_ in ks:
        u = 3 * (k_ - 1)
        a, b = uv_xy(u, V_EAST_OUT / 1000.0), uv_xy(u, 17.0)
        a.Z = FL
        b.Z = FL
        rays.append(rg.LineCurve(a, b))
    return arcs, rays


def run():
    tol = _tol()
    P = {n: _num(n) for n in DEF}
    roof_ = _in('roof')
    west_ = _in('west')
    ks = _in('k')
    if ks is None:
        return None, '入力 k が要る'
    ks = _nums(ks)
    if not ks:
        return None, '入力 k が空'
    vin = _nums(_in('vIn', V_IN))
    global V_U
    vu = _in('vU')
    V_U = _f(vu) * 1000.0 if vu is not None else 0.0
    arcs, rays = guides(ks, vin, P['col'], P['FL'])
    if roof_ is None or west_ is None:
        return dict(spine=arcs, rays=rays), '下書きだけ（spine・rays）。架構を作るには roof・west も要る'
    eave_ = _in('eave')
    cols_ = _in('showCol')
    mids_ = _in('mids')
    res = dict(plates=[], cols=[], floors=[], ptE=[], ptI=[], ptW=[], ptM=[], axis=[], lines=[], spine=arcs, rays=rays)
    rows, log, fails = [], [], {}
    log.append('外形：' + ('shapely（2Dで和、層を重ねて立体、層は分けたまま）' if HAVE_SHAPELY else 'Rhino の曲線の和（shapely が無い）'))
    for i, kk in enumerate(ks):
        sc = _pick(cols_, i, True)
        if isinstance(sc, str):
            sc = sc.strip().lower() not in ('false', '0', 'no', '')
        mids_i = parse_mids(_pick(mids_, i, None))
        try:
            o, row = build_one(kk, roof_, west_, eave_, bool(sc), mids_i, vin, P, tol, log, fails)
        except Exception as ex:
            log.append('k%g：%s' % (kk, ex))
            continue
        for key in ('plates', 'cols', 'floors', 'ptM', 'ptI'):
            res[key] += o[key]
        res['ptE'].append(o['ptE'])
        res['ptW'].append(o['ptW'])
        res['axis'].append(o['axis'])
        res['lines'].append(o['line'])
        rows.append(row)
    lines_ = [','.join(COLS)]
    for r in rows:
        lines_.append(','.join(('%.4g' % r[c]) if isinstance(r[c], float) else str(r[c]) for c in COLS))
    text = '\n'.join(lines_)
    path = _in('csv')
    if path:
        try:
            with open(str(path), 'w', encoding='utf-8') as f:
                f.write(text + '\n')
            log.append('CSV：%s' % path)
        except Exception as ex:
            log.append('CSV を書けない：%s' % ex)
    for key, name in (('plates', '板'), ('cols', '柱'), ('floors', '床梁')):
        bs = res[key]
        if bs:
            bad = sum(1 for b in bs if b is None or not b.IsValid)
            bb = rg.BoundingBox.Empty
            for b in bs:
                if b is not None:
                    bb.Union(b.GetBoundingBox(True))
            log.append('%s：%d 個（不正 %d）、範囲 x %.0f〜%.0f・y %.0f〜%.0f・z %.0f〜%.0f' % (
                name, len(bs), bad, bb.Min.X, bb.Max.X, bb.Min.Y, bb.Max.Y, bb.Min.Z, bb.Max.Z))
    log.append('架構 %d 本（失敗 %d）' % (len(rows), len(ks) - len(rows)))
    res['table'] = text
    return res, '\n'.join(log)


# Rhino 8 の部品は、入力と上の定義を globals でなく別の名前の場所（locals）に置くことがある。一つにまとめる
globals().update(locals())
log = VERSION + '\n部品は動いたが、入力 k が見えない（k の名前と List Access を確かめる）'
if _RHINO and 'k' in globals():
    _res, log = run()
    log = VERSION + '\n' + log
    if _res:
        spine, rays = _res['spine'], _res['rays']
    if _res and 'plates' in _res:
        plates, cols, floors = _res['plates'], _res['cols'], _res['floors']
        ptE, ptI, ptW, ptM = _res['ptE'], _res['ptI'], _res['ptW'], _res['ptM']
        axis, lines, table = _res['axis'], _res['lines'], _res['table']
