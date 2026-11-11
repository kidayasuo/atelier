# -*- coding: utf-8 -*-
#! python 3
# r: shapely==2.0.6
VERSION = 'kakou 2026-11-11 09:59'     # 版（直すたびに、そのときの時刻に）。log の1行目にも出る
"""
「架構」部品（遊戯室の架構、第4課題「架構と建築」）　2026-11-09夜に作り直し
版：VERSION（下の定数）。log の1行目にも出る。直すたびに日時を書き換える。
Rhino 8 Mac の Grasshopper、Python 3 のスクリプト部品に貼る。単位は mm。

架構の線・柱の列・梁の上端の高さ・荷重から、一組の架構（対の梁2本・柱・2階の床梁）を作る。梁のせいは荷重から決める（11-11）。
Tamedia（Shigeru Ban、Zürich 2013）に倣う：
  - 柱は角材（既定300角）。梁は平らな対の梁2本（梁の幅（1本）既定160）で、幅の1/3を柱の両面の凹み（梁の形）に沈めて挟む。
    梁のあいだ（光の筋）＝柱の幅−2×凹み（結果）。頭の下の縁が柱の肩に載り、鉛直の力はその支圧で柱へ。
    柱は頭の下で広がり、頭の中では頭の形いっぱい。
  - 楕円の桁（既定180×260）が梁と柱の穴を通り、回転を止める。
  - 梁は内の柱の列の上を途切れずに続く（連続梁）。長いスパンの下端は端で深く真ん中で浅いカーブ。
  - 梁の端・柱の上には、桁の穴を包む楕円の頭。頭は下端より下がり、下端とはハンチでつながる。柱は頭の下で広がる。
  - 形は寸法を写さず、Tamediaの詳細図の比で梁のせい D から決める：
    桁の中心は下端から 0.14D、頭は半幅 0.58D・半高さ 0.68D（穴のまわりに木 120 以上）、ハンチ 1.1D、柱の広がり 0.55D。
西の端は、頭と軒先への細い延長を一つの部材にする（せい240→先で120、先は鉛直、丸み300でつなぐ）。

架構の位置：背骨（西館の東の柱の列）の円弧の中心からの放射の直線。
  架構kは u＝3(k−1) m、u は本館の背骨の円弧（v＝0）の上で測る（育ち舎の uv.py・3dm と同じ、k15.5 も可）。
  柱は colLines（柱の芯の曲線）と架構の線の交わる所。無ければ、東は東の壁の内面 v−1.05 から柱の幅の半分の内、内の列は vIn、西は west から柱の幅の半分の内。
  frames（架構の線）を渡せば、放射の線でなくその線で作る。
梁の上端：屋根の面（Brep）と、梁（1本ずつ）の真ん中の鉛直面の交線を直線で近似（ずれは CSV に出す）。
  屋根の面を差し替えれば、A・B・C 案の架構がそのまま作り直される。
例外は「柱を出すか」だけ。それ以外は Bake してから手で直す。

入力（名前・型・既定は README の表）
  位置：frames（架構の線）か k（放射の線）、colLines（柱の列の曲線）か west・vIn
  高さ：roof（屋根の面）か zE・zW（梁の上端、東と西の柱の芯で）
  荷重：qD・qS・sp・hang（吊り荷重 "s:kN;…"）。梁のせいはここから決める（D・Dm を入れれば確かめるだけ）
  意匠：t（梁の幅（1本））・col（柱）・keyR（凹み／梁の幅）・DmR・same、ほか eave・showCol・mids・FL・Df・eR・haR・hbR・ext0・ext1・vU・csv
出力           spine（v−0.9・東の柱の芯・内の列の円弧）・rays（架構kの放射の線）：k だけつなげば出る下書き
               plates（対の梁）・cols（柱、芯と両面の層）・floors（2階の床梁）
               ptE・ptI・ptW・ptM（桁が通る点）・axis（桁の向き）・lines（架構の線）・table（CSV の文）・log
"""
import math


# ------------------------------------------------------------------ 既定の値（mm）
DEF = dict(
    FL=0.0,
    t=160.0,      # 梁の幅（1本、対で2本）。荷重から梁のせいを決めるときの前提（意匠で選ぶ）
    col=300.0,    # 柱の幅（角材、意匠で選ぶ）。梁のあいだ（光の筋）＝col−2×凹みの深さ（結果）
    keyR=1.0 / 3, # 凹みの深さ／梁の幅（Tamedia：梁の幅240の1/3≈80、kadai/kako/tamedia.md）
    DmR=0.8,      # 長いスパンの真ん中のせい／端のせい（Tamediaのカーブ。ryakusan/shin_1109.py の500→400）
    qD=0.84,      # 屋根の固定荷重（kN/m²、育ち舎の略算）
    qS=0.6,       # 雪（kN/m²、30 cm）
    sp=3000.0,    # 架構の間隔（負担の幅）
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
NOTCH_CLR = 3.0                     # 柱の凹みは梁の外形より3大きく
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


def _arc_n(T1, cf, T2, seg=8.0):
    """弧を弦 seg 以下に分ける数"""
    a1 = math.atan2(T1[1] - cf[1], T1[0] - cf[0])
    a2 = math.atan2(T2[1] - cf[1], T2[0] - cf[0])
    da = abs((a2 - a1 + math.pi) % (2 * math.pi) - math.pi)
    return max(8, int(math.ceil(math.hypot(T1[0] - cf[0], T1[1] - cf[1]) * da / seg)))


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


# ------------------------------------------------------------------ 構造の略算（Rhino を使わない）
# 梁は連続梁（支点＝柱の芯、柱の頭はピン、剛接合は当てにしない＝鉛直の荷重に対して安全側）。
# 水平の投影で解き、傾きは EI·cos²α で見込む。単位は kN・m。
E_W = 9.5e6            # kN/m²（基本編）
FB_L = 12e3            # 長期の曲げ（基本編）
FB_S = 12e3 * 1.6 / 1.1
FC_L, FC_S = 8.0e3, 14.5e3     # 圧縮（集成材の一般的な値、基本編に無い）
FCV_L, FCV_S = 2.2e3, 4.0e3    # めり込み（同）
GAM_W = 5.0            # kN/m³
DEFL = 250.0
D_STEP = 25.0          # mm
D_MIN, D_MAX = 300.0, 1000.0


def _band_solve(K, F, hb):
    """帯の行列（dict の行）を解く。K[i] は {j: 値}、|i−j|≤hb"""
    n = len(F)
    A = [dict(r) for r in K]
    b = list(F)
    for i in range(n):
        piv = A[i].get(i, 0.0)
        if abs(piv) < 1e-30:
            raise RuntimeError('解けない（支点が足りない）')
        for r in range(i + 1, min(n, i + hb + 1)):
            f = A[r].get(i, 0.0) / piv
            if f == 0.0:
                continue
            for c, v in A[i].items():
                if c >= i:
                    A[r][c] = A[r].get(c, 0.0) - f * v
            b[r] -= f * b[i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = b[i] - sum(v * x[c] for c, v in A[i].items() if c > i)
        x[i] = s / A[i][i]
    return x


def beam_solve(xs, EI, q, P, sup):
    """xs：節点の s（m、昇順）。EI[e]、q[e]（kN/m、下向き正、要素ごと一様）。P{節点: kN}。sup：支点の節点。
    返す：たわみ w（下向き正）、要素の端の曲げ（kN·m、下端引張り正）、反力{節点: kN（上向き正）}"""
    n = len(xs)
    K = [dict() for _ in range(2 * n)]
    F = [0.0] * (2 * n)
    for e in range(n - 1):
        L = xs[e + 1] - xs[e]
        k = EI[e] / L ** 3
        m = [[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
             [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]]
        dof = [2 * e, 2 * e + 1, 2 * e + 2, 2 * e + 3]
        fe = [q[e] * L / 2, q[e] * L * L / 12, q[e] * L / 2, -q[e] * L * L / 12]
        for a in range(4):
            F[dof[a]] += fe[a]
            for c in range(4):
                K[dof[a]][dof[c]] = K[dof[a]].get(dof[c], 0.0) + k * m[a][c]
    for i, v in P.items():
        F[2 * i] += v
    BIG = 1e18
    for i in sup:
        K[2 * i][2 * i] += BIG
    u = _band_solve(K, F, 3)
    w = [u[2 * i] for i in range(n)]
    R = {i: BIG * u[2 * i] for i in sup}          # 上向き正
    # 曲げ（下端引張り正）：東の端（自由）から力のつりあいで
    M = [0.0] * n
    V = 0.0
    for i in range(n):
        V += R.get(i, 0.0) - P.get(i, 0.0)
        if i < n - 1:
            L = xs[i + 1] - xs[i]
            M[i + 1] = M[i] + V * L - q[i] * L * L / 2
            V -= q[i] * L
    return w, M, R


def frame_check(sup, top, s_tip, t, C, d, FL, loads, hang, De, Dm, long_span=4.0):
    """一つの架構の略算。sup：柱の s（m、東→西）。top=(z0, m)：梁の上端 z=z0+m·s（m）。s_tip：延長の先（m）。
    De・Dm：せい（m）。t：梁の幅（1本、m、対で2本）。C：柱の幅、d：凹みの深さ（m）。FL（m）。
    loads=(屋根の固定 kN/m², 雪 kN/m², 間隔 m)。hang=[(s, kN)]（吊り荷重）。
    返す：比の dict と、柱の軸力"""
    z0, m = top
    cos2 = 1.0 / (1.0 + m * m)
    sp = sorted(sup)
    def D(s):
        for a, b in zip(sp[:-1], sp[1:]):
            if a <= s <= b and b - a >= long_span:
                x = (s - a) / (b - a)
                return Dm + (De - Dm) * (2 * x - 1) ** 2
        return De
    stops = sorted(set([sp[0]] + sp + [s_tip] + [h[0] for h in hang if sp[0] <= h[0] <= s_tip]))
    xs = []
    for a, b in zip(stops[:-1], stops[1:]):
        n = max(2, int(math.ceil((b - a) / 0.25)))
        xs += [a + (b - a) * i / n for i in range(n)]
    xs.append(stops[-1])
    idx = lambda s: min(range(len(xs)), key=lambda i: abs(xs[i] - s))
    b2 = 2 * t
    EI, qd, qs = [], [], []
    roof, snow, spc = loads
    sec = math.sqrt(1.0 + m * m)
    for a, b in zip(xs[:-1], xs[1:]):
        dd = D((a + b) / 2)
        EI.append(E_W * b2 * dd ** 3 / 12 * cos2)
        g = roof * spc + GAM_W * b2 * dd * sec
        qd.append(g)
        qs.append(g + snow * spc)
    P = {}
    for s, kn in hang:
        i = idx(s)
        P[i] = P.get(i, 0.0) + kn
    supi = [idx(s) for s in sp]
    res = {}
    for key, q in (('L', qd), ('S', qs)):
        w, M, R = beam_solve(xs, EI, q, P, supi)
        sig = max(abs(M[i]) / (b2 * D(xs[i]) ** 2 / 6) for i in range(len(xs)))
        dmax = 0.0
        for a, b in zip(supi[:-1], supi[1:]):
            L = xs[b] - xs[a]
            for i in range(a, b + 1):
                rel = w[i] - (w[a] + (xs[i] - xs[a]) / L * (w[b] - w[a]))
                dmax = max(dmax, rel / (L / DEFL))
        res[key] = (sig, dmax, [R[i] for i in supi])
    r = dict(曲げ=max(res['L'][0] / FB_L, res['S'][0] / FB_S),
             たわみ=max(2 * res['L'][1], res['S'][1]))
    NL, NS = res['L'][2], res['S'][2]
    # 柱
    g = C - 2 * d
    i_ = C / math.sqrt(12)
    cz, cg, cs = 0.0, 0.0, 0.0
    for j, s in enumerate(sp):
        h = z0 + m * s - De - FL
        lam = h / i_
        eta = 1.0 if lam <= 30 else (1.3 - 0.01 * lam if lam <= 100 else 3000.0 / lam ** 2)
        nl, ns = max(0.0, NL[j]), max(0.0, NS[j])
        cz = max(cz, nl / (C * C * eta * FC_L), ns / (C * C * eta * FC_S))
        cg = max(cg, nl / (g * C * FC_L), ns / (g * C * FC_S))
        cs = max(cs, nl / (2 * d * C * FCV_L), ns / (2 * d * C * FCV_S))
    r.update(座屈=cz, 凹み=cg, 肩=cs)
    return r, NL, NS


def size_beam(sup, top, s_tip, t, C, d, FL, loads, hang, DmR, long_span=4.0):
    """曲げ・たわみが足りる、いちばん浅い端のせい De（m）。長いスパンの真ん中は De·DmR。足りなければ None"""
    De = D_MIN / 1000.0
    while De <= D_MAX / 1000.0 + 1e-9:
        r, NL, NS = frame_check(sup, top, s_tip, t, C, d, FL, loads, hang, De, De * DmR, long_span)
        if r['曲げ'] <= 1 and r['たわみ'] <= 1:
            return De, De * DmR, r, NL, NS
        De += D_STEP / 1000.0
    return None


def cap_pts(G, a, Ht, m, seg=4.0):
    """頭の上半分（外の端）：x＝G0＋a·cos t、z＝G1＋sin t·(H＋m·a·cos t)（0≤t≤π）。
    両端は赤道で頭の楕円に鉛直の接線でなめらかにつながり、上は傾き m の上端の直線（G0 で G1＋Ht）に接する。
    （前は傾けた半楕円と三角形の組で、赤道で段ができた、11-11）。H は接するように二分法で決める"""
    def top_gap(H):
        best = -1e30
        for i in range(721):
            t = math.pi * i / 720
            best = max(best, math.sin(t) * (H + m * a * math.cos(t)) - m * a * math.cos(t))
        return best
    lo, hi = abs(m) * a, 4 * Ht + abs(m) * a
    for _ in range(60):
        mid = (lo + hi) / 2
        if top_gap(mid) < Ht:
            lo = mid
        else:
            hi = mid
    H = (lo + hi) / 2
    n = max(48, int(math.pi * max(a, H) / seg))
    return [(G[0] + a * math.cos(math.pi * i / n),
             G[1] + math.sin(math.pi * i / n) * (H + m * a * math.cos(math.pi * i / n))) for i in range(n + 1)]


def head_shape(G, h, cap=None):
    """頭の外形（shapely）：楕円、外の端なら冠を足したもの"""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    g = Polygon(prim_pts(ellipse(G, h['ha'], h['hb']), seg=2.0))
    if cap:
        g = unary_union([g, Polygon(cap)])
    return g


def fillet_shape(p0, d, n, shape, R, pin):
    """直線（p0 から d の向きに形へ近づく、n は材の無い側）と、凸の形 shape（shapely）の入隅の半径 R の丸み。
    pin は形の中で直線の材の側の点。返す：('poly', 点の並び) か None"""
    from shapely.geometry import Point, LineString
    far = 1e5
    hit = LineString([p0, (p0[0] + d[0] * far, p0[1] + d[1] * far)]).intersection(shape.exterior)
    pts = [hit] if hit.geom_type == 'Point' else [q for q in getattr(hit, 'geoms', []) if q.geom_type == 'Point']
    if not pts:
        return None
    xX = min((q.x - p0[0]) * d[0] + (q.y - p0[1]) * d[1] for q in pts)
    cen = lambda x: (p0[0] + d[0] * x + n[0] * R, p0[1] + d[1] * x + n[1] * R)
    def f(x):
        c = Point(cen(x))
        dd = shape.exterior.distance(c)
        return (-dd if shape.contains(c) else dd) - R
    hi = xX
    if f(hi) > 0:
        return None
    lo = xX - 3 * R
    k = 0
    while f(lo) <= 0 and k < 20:
        lo -= 2 * R
        k += 1
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    x = (lo + hi) / 2
    cf = cen(x)
    T1 = (p0[0] + d[0] * x, p0[1] + d[1] * x)
    q = shape.exterior.interpolate(shape.exterior.project(Point(cf)))
    T2 = (q.x, q.y)
    X = (p0[0] + d[0] * xX, p0[1] + d[1] * xX)
    I = (X[0] + 0.15 * (pin[0] - X[0]), X[1] + 0.15 * (pin[1] - X[1]))
    return ('poly', [T1] + _arc_pts(T1, cf, T2, _arc_n(T1, cf, T2)) + [T2, I])


def _haunch(G, h, side, soffit):
    """支点 G の side（+1＝西、−1＝東）の側の、梁の下端と頭の入隅の丸み（半径 R）。
    丸みは実際の下端の曲線 soffit(s) に接する（下端が放物線のスパンでも、直線に置き換えない）。
    返す：('poly', 点の並び)。丸みの弧・頭の楕円の接点・楕円の中の点・下端より1 mm上を通って戻る（下端と辺を重ねない）"""
    R, a, b = h['R'], h['ha'], h['hb']
    f = soffit
    df = lambda s_: (f(s_ + 0.5) - f(s_ - 0.5))
    def center(s_):
        m_ = df(s_)
        L = math.hypot(1.0, m_)
        return (s_ + R * m_ / L, f(s_) - R / L)       # 下端の下（材の無い側）へ R
    inside = lambda s_: ((s_ - G[0]) / a) ** 2 + ((f(s_) - G[1]) / b) ** 2 < 1.0
    # 下端が楕円に入る所 X
    s_far = G[0] + side * 4 * R
    if inside(s_far):
        return None
    lo, hi = s_far, G[0]
    for _ in range(60):
        mid = (lo + hi) / 2
        if inside(mid):
            hi = mid
        else:
            lo = mid
    sX = hi
    g = lambda s_: ell_sdist(center(s_), G, a, b)[0] - R
    if g(s_far) <= 0 or g(sX) > 0:
        return None
    lo, hi = s_far, sX
    for _ in range(60):
        mid = (lo + hi) / 2
        if g(mid) > 0:
            lo = mid
        else:
            hi = mid
    s1 = (lo + hi) / 2
    cf = center(s1)
    T1 = (s1, f(s1))
    T2 = ell_sdist(cf, G, a, b)[1]
    I = (sX + 0.15 * (G[0] - sX), f(sX) + 0.15 * (G[1] - f(sX)))
    nb = max(8, int(abs(sX - s1) / 10))
    back = [(sX + (s1 - sX) * k / nb, f(sX + (s1 - sX) * k / nb) + 1.0) for k in range(nb + 1)]
    na = max(8, int(R * abs(math.atan2(T2[1] - cf[1], T2[0] - cf[0]) - math.atan2(T1[1] - cf[1], T1[0] - cf[0])) / 8))
    return ('poly', [T1] + _arc_pts(T1, cf, T2, na) + [T2, I] + back)


def beam_2d(P, top, supports, Dfn, ext=None):
    """梁（または2階の床梁）の1本の外形の基本形・上端で切る多角形・穴・頭の点。
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
            # 外の端の上：頭の楕円の赤道から立ち上がり、上端の直線に接する「冠」（cap_pts）
            pr.append(('poly', cap_pts(G, h['ha'], zt(s) - G[1], m)))
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
        # 延長の下端と頭の入隅の丸み：実際の頭の外形（楕円＋冠）に接する
        pA = (s_tip, zt(s_tip) - a1)
        pB = (s_wall, zt(s_wall) - a0)
        L = math.hypot(pB[0] - pA[0], pB[1] - pA[1])
        d = ((pB[0] - pA[0]) / L, (pB[1] - pA[1]) / L)
        nn = (d[1], -d[0])
        if nn[1] > 0:
            nn = (-nn[0], -nn[1])
        shape = head_shape(GW, hW, cap_pts(GW, hW['ha'], zt(sW) - GW[1], m))
        zl = pA[1] + (pB[1] - pA[1]) * (GW[0] - pA[0]) / (pB[0] - pA[0])
        pin = (GW[0], (zl + zt(sW)) / 2)
        fl = fillet_shape(pA, d, nn, shape, EAVE_R, pin)
        if fl is None:
            raise RuntimeError('軒への延長と頭をつなぐ丸みが、頭の外形に接しない（EAVE_R・ext0・ext1を見直す）')
        pr.append(fl)
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
        n = 4 * max(12, int(math.ceil(2 * math.pi * r / seg / 4)))     # 4の倍数：上下左右の端の点を必ず通る
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
    return _dedup(list(big.exterior.coords)[:-1])


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
    return _drop_collinear(out)


COLLINEAR_TOL = 1e-6    # mm。これより直線から外れない点は、直線の途中の点として除く（直線の辺を1本の線に戻す）


def _drop_collinear(ring):
    """直線の上に並ぶだけの点を除く（閉じた並び）。曲線の点（弦の中のずれは1e-4 mm以上）は残る"""
    pts = list(ring)
    changed = True
    while changed and len(pts) > 3:
        changed = False
        out = []
        n = len(pts)
        for i in range(n):
            a, b, c = (out[-1] if out else pts[i - 1]), pts[i], pts[(i + 1) % n]
            L = math.hypot(c[0] - a[0], c[1] - a[1])
            dev = abs((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / L if L > 0 else 0.0
            inside = (b[0] - a[0]) * (c[0] - a[0]) + (b[1] - a[1]) * (c[1] - a[1]) > 0
            if dev < COLLINEAR_TOL and inside:
                changed = True
                continue
            out.append(b)
        pts = out
    return pts


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
    T = [turn(i) for i in range(n)]
    # 角：大きく折れる点、または前後の点よりはっきり大きく折れる点（2つの曲線が角度を持って出会う所。
    # 曲線の点の取り方による折れは前後でほぼ同じ）
    corner = lambda i: T[i] >= CORNER_DEG or (T[i] >= 1.0 and T[i] > 3 * max(T[i - 1], T[(i + 1) % n], 0.05))
    # 区切りの点：角、または長い辺の端
    brk = [i for i in range(n) if corner(i) or seglen(i) >= LINE_MIN or seglen(i - 1) >= LINE_MIN]
    if not brk:
        brk = [0, n // 2]          # 角の無い輪は2つに分ける（周期の曲線を使わない）
    runs = []
    for j, i0 in enumerate(brk):
        i1 = brk[(j + 1) % len(brk)]
        k = (i1 - i0) % n or n
        pts = [ring[(i0 + t) % n] for t in range(k + 1)]
        if len(pts) == 2:
            runs.append(('line', pts[0], pts[1]))
        else:
            runs.append(('curve', _resample(pts)))
    return runs


CURVE_SEG = 6.0     # 曲線の区切りを、この長さ以下の等しい間隔の点に取り直してから曲線にする


def _resample(pts, seg=CURVE_SEG):
    """折れ線を、長さに沿って等しい間隔の点に取り直す（両端はそのまま）。
    間隔が不ぞろいな点を3次の曲線で結ぶと、短い間の所で曲線がはね返り、輪が自分と交わる（11-11、k9〜k17）"""
    cum = [0.0]
    for a, b in zip(pts[:-1], pts[1:]):
        cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    L = cum[-1]
    n = max(2, int(math.ceil(L / seg)))
    out, j = [], 0
    for k in range(n + 1):
        t = L * k / n
        while j < len(cum) - 2 and cum[j + 1] < t:
            j += 1
        a, b = pts[j], pts[j + 1]
        u = (t - cum[j]) / (cum[j + 1] - cum[j]) if cum[j + 1] > cum[j] else 0.0
        out.append((a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1])))
    out[0], out[-1] = pts[0], pts[-1]
    return out


def key_shape(G, h, grow=0.0):
    """食い込み（梁のキー・柱の欠き込み）の外形：頭の楕円そのもの（Tamediaの写真：梁の頭がまるごと柱に食い込み、
    頭の下の縁が柱の肩に載る）。grow：欠き込みを少し大きくするとき"""
    return ellipse(G, h['ha'] + grow, h['hb'] + grow)


def column_2d(Gs, w, FL, ztop, heads, roofG):
    """柱（架構の面）。heads：この柱に取りつく頭 [(点, 大きさ)]（屋根と2階）。roofG：屋根の頭の点。
    返すのは柱の基本形（足し合わせる）と、切る形（屋根の梁の外形と足す、屋根の頭より下の帯）"""
    pr = [('poly', [(Gs - w / 2, FL), (Gs + w / 2, FL), (Gs + w / 2, ztop + 2000), (Gs - w / 2, ztop + 2000)])]
    for G, h in heads:
        pr.append(ellipse(G, h['ha'], h['hb']))     # 柱は頭の中では頭の形いっぱい（下から見て、広がりが頭の下端に取りつく）
        # 広がりの丸みは頭の楕円に接する。柱の面の層では、凹み（頭＋NOTCH_CLR）で切られて、広がりの先は頭の手前で
        # 細く尖って止まる（Tamediaの立面も同じ：広がりの先は頭から10離れ、角度は約11°）
        ea, eb = h['ha'], h['hb']
        for side in (-1, 1):
            nrm = (side, 0.0)
            fl = fillet((Gs + side * w / 2, FL), (0.0, 1.0), nrm, G, ea, eb, h['Rc'], G)
            if fl:
                pr.append(fl)
            if G is not roofG:      # 2階の頭は上からも
                fl = fillet((Gs + side * w / 2, roofG[1]), (0.0, -1.0), nrm, G, ea, eb, h['Rc'], G)
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
    segs = []
    for r in runs:
        if r[0] == 'line':
            segs.append(rg.LineCurve(F.P(r[1][0], r[1][1], off), F.P(r[2][0], r[2][1], off)))
        else:
            pts = [F.P(a, b, off) for a, b in r[1]]
            # 点をそのまま通る3次の曲線（Fit で間引くと、尖った先の近くで2本の曲線が交わることがある）
            c = rg.Curve.CreateInterpolatedCurve(pts, 3, rg.CurveKnotStyle.Chord)
            if c is None:
                raise RuntimeError('曲線を作れない（点%d）' % len(pts))
            segs.append(c)
    j = rg.Curve.JoinCurves(segs, 0.05)
    if not j or len(j) != 1 or not j[0].IsClosed:
        raise RuntimeError('輪の曲線がつながらない（区切り%d、つないだ結果%d本）' % (len(segs), len(j) if j else 0))
    return j[0], segs


def _ring_check(F, ring, off, tol):
    """一つの輪の曲線と、直線の区切りの数。曲線が閉じて平らで、自分と交わらないことを確かめる"""
    c, segs = _ring_curve(F, ring, off, tol)
    runs = smooth_runs(ring)
    nline = sum(1 for r in runs if r[0] == 'line')
    probs = []
    if not c.IsClosed:
        probs.append('閉じていない')
    if not c.IsPlanar(tol):
        probs.append('平らでない')
    xs = _X.CurveSelf(c, tol)
    if xs and xs.Count:
        q = xs[0].PointA
        probs.append('自分と交わる（%d所、たとえば x%.0f y%.0f z%.0f）' % (xs.Count, q.X, q.Y, q.Z))
    return c, segs, nline, probs


def _slabs(F, g, off, thick, tol, tag='', log=None, holes=()):
    """shapely の形を、off の面から +perp へ thick 押し出した立体（形が分かれていれば複数）。
    holes：桁の穴（楕円の基本形）。shapely で引かず、ちょうどの楕円の曲線にして、その中心を含む部分に開ける。
    確かめる：輪の曲線が閉じて平らで交わらない、平らな面ができる、直線の区切りの数だけ側面が平ら"""
    from shapely.geometry import Point
    out = []
    parts = [x for x in (list(g.geoms) if hasattr(g, 'geoms') else [g]) if x.geom_type == 'Polygon' and x.area >= 100.0]
    for n_, part in enumerate(parts):
        ext = _dedup(list(part.exterior.coords)[:-1])
        if part.interiors:
            raise RuntimeError('%s（%d）：思わぬ穴がある（%d）' % (tag, n_, len(part.interiors)))
        crvs, nline, probs = [], 0, []
        c, segs, nline, pr = _ring_check(F, ext, off, tol)
        crvs.append(c)
        side_curves = list(segs)
        probs += ['外：%s' % x for x in pr]
        for k_, hp in enumerate(holes):
            if part.contains(Point(hp[2], hp[3])):
                crvs.append(F.curve(hp, off))
                side_curves.append(crvs[-1])
                if not crvs[-1].IsClosed:
                    probs.append('穴%d：閉じていない' % (k_ + 1))
        for a_ in range(len(crvs)):
            for b_ in range(a_ + 1, len(crvs)):
                ev = _X.CurveCurve(crvs[a_], crvs[b_], tol, tol)
                if ev and ev.Count:
                    probs.append('輪%dと輪%dが交わる' % (a_, b_))
        br = rg.Brep.CreatePlanarBreps(crvs, tol) if not probs else None
        if not br or len(br) != 1:
            raise RuntimeError('%s（%d）：平らな面ができない。%s' % (tag, n_, '・'.join(probs) or '曲線は正しいのに面ができない'))
        # 側面は区切り（直線・曲線）ごとに1枚ずつ押し出してつなぐ。面を一度に押し出すと、直線と曲線が接線でつながる所が
        # 1枚の面になり、直線の辺の側面が平らな面として残らない（11-11、柱の層で平らな面が2枚足りなかった）
        v = F.P(0, 0, off + thick) - F.P(0, 0, off)
        bot = br[0]
        top = bot.DuplicateBrep()
        top.Translate(v)
        pieces = [bot, top]
        for cv in side_curves:
            sf = rg.Surface.CreateExtrusion(cv, v)
            if sf is None:
                raise RuntimeError('%s（%d）：側面を押し出せない' % (tag, n_))
            pieces.append(sf.ToBrep())
        jb = rg.Brep.JoinBreps(pieces, tol)
        if not jb or len(jb) != 1:
            raise RuntimeError('%s（%d）：面がつながらない（%d個に分かれる）' % (tag, n_, len(jb) if jb else 0))
        sld = jb[0]
        # 完全な立体か：閉じていて（裸の辺が無い）、正しい向きで、体積が形の面積×厚さに合う
        if not sld.IsValid or not sld.IsSolid:
            naked = sum(1 for e in sld.Edges if e.Valence == rg.EdgeAdjacency.Naked)
            raise RuntimeError('%s（%d）：閉じた立体にならない（裸の辺%d）' % (tag, n_, naked))
        if sld.SolidOrientation != rg.BrepSolidOrientation.Outward:
            sld.Flip()
        vm = rg.VolumeMassProperties.Compute(sld)
        hole_a = sum(math.pi * hp[4] * hp[7] for hp in holes if part.contains(Point(hp[2], hp[3])))
        v_want = (part.area - hole_a) * abs(thick)
        if vm is None or abs(vm.Volume - v_want) > 0.002 * v_want:
            raise RuntimeError('%s（%d）：体積が合わない（%.0f、形から%.0f）' % (tag, n_, vm.Volume if vm else -1, v_want))
        flat = sum(1 for f in sld.Faces if f.IsPlanar(tol))
        if log is not None and flat != nline + 2:
            log.append('%s（%d）：平らな面 %d（直線の辺%d＋上下2のはず）' % (tag, n_, flat, nline))
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


def parse_hang(x):
    """吊り荷重 "s:kN;s:kN"（s は東の柱の芯から西へ m）→ [(s, kN)]"""
    out = []
    if x is None:
        return out
    for q in str(x).replace(',', ';').split(';'):
        if ':' in q:
            a, b = q.split(':', 1)
            try:
                out.append((float(a), float(b)))
            except ValueError:
                pass
    return out


def _line_s(F, crv, s_lo=-5000.0, s_hi=60000.0):
    """架構の線（平面、O から d の向き）と曲線の交わる s の全部"""
    flat = rg.Curve.ProjectToPlane(crv, rg.Plane.WorldXY)
    ln = rg.LineCurve(F.P(s_lo, 0), F.P(s_hi, 0))
    ev = _X.CurveCurve(ln, flat, 0.1, 0.1)
    out = []
    for x in ev or []:
        q = x.PointA
        out.append(((q.X - F.O[0]) * F.d[0] + (q.Y - F.O[1]) * F.d[1], flat.TangentAt(x.ParameterB)))
    return sorted(out, key=lambda a: a[0])


def _hit_s(F, crv, s_min=1000.0):
    """架構の線が曲線と交わる s（s_min より先でいちばん近いもの）と、その所の曲線の向き"""
    for s, tg in _line_s(F, crv):
        if s > s_min:
            return s, tg
    return None


def plan_one(i, kk, fr, P, A, log):
    """架構一つの位置・支点・上端・軒、と荷重から梁のせい。fr：架構の線（Curve）か None（k から放射の線）"""
    C, t = P['col'], P['t']
    d = P['keyR'] * t
    if fr is not None:
        a, b = fr.PointAtStart, fr.PointAtEnd
        L = math.hypot(b.X - a.X, b.Y - a.Y)
        dd = ((b.X - a.X) / L, (b.Y - a.Y) / L)
        F = Frame3((a.X, a.Y), dd, (-dd[1], dd[0]))
        th = math.atan2(dd[1], dd[0])
    else:
        O, dd, pp, th = frame_axis(kk, C)
        F = Frame3(O, dd, pp)
    # 柱の芯の s
    if A['colLines']:
        ss = []
        s_end = 60000.0 if fr is None else math.hypot(fr.PointAtEnd.X - fr.PointAtStart.X, fr.PointAtEnd.Y - fr.PointAtStart.Y)
        for c in A['colLines']:
            h = [q for q in _line_s(F, c) if -1000.0 <= q[0] <= s_end + 1000.0]
            if h:
                ss.append(h[0][0])     # 線の東の端に近いもの
        ss = sorted(set(round(x, 1) for x in ss))
        if len(ss) < 2:
            raise RuntimeError('柱の列の曲線と交わる所が2つ未満')
        if A['west'] is not None:
            hw = _hit_s(F, A['west'], ss[0] + 500)
            s_wall = hw[0] if hw else ss[-1] + C / 2
        else:
            s_wall = ss[-1] + C / 2
    else:
        if fr is not None:
            raise RuntimeError('frames を使うときは colLines も要る')
        if A['west'] is None:
            raise RuntimeError('west（外壁の内面の線）か colLines が要る')
        hw = _hit_s(F, A['west'])
        if hw is None:
            raise RuntimeError('架構の線が西の線と交わらない')
        s_wall = hw[0]
        sW = s_wall - C / 2.0
        s_in = sorted(v * 1000.0 - (V_EAST_FACE + C / 2) for v in A['vin'] if v > 0)
        ss = [0.0] + [s for s in s_in if 500 < s < sW - 500] + [sW]
    # 原点を東の柱の芯へ
    s0 = ss[0]
    F = Frame3((F.O[0] + s0 * F.d[0], F.O[1] + s0 * F.d[1]), F.d, F.p)
    sup = [x - s0 for x in ss]
    s_wall -= s0
    # 軒
    if A['eave'] is not None:
        he = _hit_s(F, A['eave'], s_wall)
        if he is None:
            raise RuntimeError('架構の線が軒先の線と交わらない')
        tg = he[1]
        cosphi = abs(-tg.Y * F.d[0] + tg.X * F.d[1]) / max(1e-9, math.hypot(tg.X, tg.Y))
        s_tip = he[0] - TIP_GAP / max(cosphi, 0.2)
    else:
        s_tip = s_wall + EAVE_OUT - TIP_GAP
    # 梁の上端：屋根の面、なければ両端の高さ
    off_pl = C / 2 - d + t / 2
    offs = {'+': off_pl, '-': -off_pl, '0': 0.0}
    tops = {}
    if A['roof'] is not None:
        s_lo, s_hi = -C - 600, s_tip + 10
        for key, off in offs.items():
            try:
                tops[key] = _top_fit(F, A['roof'], off, s_lo, s_hi, A['tol'])
            except RuntimeError:
                tops[key] = None
        if tops['0'] is None:
            raise RuntimeError('屋根の面と交わらない（架構の線の上）')
        miss = [k_ for k_ in ('+', '-') if tops[k_] is None]
        if miss:
            raise RuntimeError('梁（%s）の面が屋根の面の外。屋根の面を、端の架構の梁の外まで（本来の屋根の縁まで）描く' % '・'.join(
                '架構の線の左' if k_ == '+' else '架構の線の右' for k_ in miss))
    else:
        zE, zW = _pick(A['zE'], i, None), _pick(A['zW'], i, None)
        if zE is None or zW is None:
            raise RuntimeError('roof（屋根の面）か、zE・zW（梁の上端の高さ、東と西の柱の芯で）が要る')
        zE, zW = _f(zE), _f(zW)
        m = (zW - zE) / sup[-1]
        for key in offs:
            tops[key] = (zE, m, 0.0)
    # 荷重から梁のせい（m・kN で）
    hang = parse_hang(_pick(A['hang'], i, None))
    loads = (P['qD'], P['qS'], P['sp'] / 1000.0)
    z0, m, _ = tops['0']
    args = ([x / 1000.0 for x in sup], (z0 / 1000.0, m), s_tip / 1000.0, t / 1000.0, C / 1000.0, d / 1000.0,
            P['FL'] / 1000.0, loads, hang)
    Din = A['D']
    if Din is not None:
        De = _f(_pick(Din, i, Din)) / 1000.0
        Dm = _f(_pick(A['Dm'], i, None)) / 1000.0 if A['Dm'] is not None else De * P['DmR']
        res = frame_check(*args, De=De, Dm=Dm)
        ok = (De, Dm) + res
    else:
        ok = size_beam(*args, DmR=P['DmR'])
        if ok is None:
            raise RuntimeError('梁のせい%.0fでも足りない' % D_MAX)
    return dict(i=i, kk=kk, F=F, th=th, sup=sup, s_wall=s_wall, s_tip=s_tip, tops=tops, d=d, hang=hang,
                args=args, De=round(ok[0] * 1000.0, 1), Dm=round(ok[1] * 1000.0, 1), r=ok[2], NL=ok[3], NS=ok[4], fr=fr)


def geom_one(pl, P, showcol, mids, tol, log):
    """架構一つの形（対の梁2本・柱・2階の床梁）。凹み：平らな梁が幅の keyR を柱の頭の形の凹みに沈める（Tamedia）"""
    F, sup, tops = pl['F'], pl['sup'], pl['tops']
    C, t, d = P['col'], P['t'], pl['d']
    s_wall, s_tip = pl['s_wall'], pl['s_tip']
    Dfn = depth_fn(sup, pl['De'], pl['Dm'])
    out = dict(plates=[], cols=[], floors=[], ptM=[])
    tag = 'k%g' % pl['kk']
    # 梁の位置：内の面が柱の面から d 内、外へ t
    pos = {'+': (C / 2 - d), '-': -(C / 2 - d + t)}
    B0 = beam_2d(P, tops['0'][:2], sup, Dfn, ext=(s_wall, s_tip))
    plate_g = {}
    for key in ('+', '-'):
        B = beam_2d(P, tops[key][:2], sup, Dfn, ext=(s_wall, s_tip))
        g = region_2d(B['prims'], [[B['clip']]])
        plate_g[key] = g
        out['plates'] += _slabs(F, g, pos[key], t, tol, tag + '梁' + key, log, B0['holes'])
    heads = B0['heads']
    # 2階の床梁
    mid_heads = {j: [] for j in range(len(sup))}
    floor_g = []
    for hz in mids:
        ztop = P['FL'] + hz
        Bf = beam_2d(P, (ztop, 0.0), sup, lambda s: P['Df'])
        g = region_2d(Bf['prims'], [[Bf['clip']]])
        floor_g.append(g)
        for key in ('+', '-'):
            out['floors'] += _slabs(F, g, pos[key], t, tol, tag + '床梁' + key, log, Bf['holes'])
        for j, gh in enumerate(Bf['heads']):
            mid_heads[j].append(gh)
            out['ptM'].append(F.P(gh[0][0], gh[0][1]))
    # 柱：芯（凹みの奥、厚さ C−2d）と両面の層（厚さ d、梁の形の凹みを抜く）
    if showcol:
        from shapely.ops import unary_union
        o0 = outline_2d(B0['prims'], [[B0['clip']]])
        z0, m, _ = tops['0']
        cut = {k_: unary_union([plate_g[k_]] + floor_g).buffer(NOTCH_CLR) for k_ in plate_g}
        for j, s in enumerate(sup):
            G, h = heads[j]
            Cc = column_2d(s, C, P['FL'], z0 + m * s, [(G, h)] + mid_heads[j], G)
            g = region_2d(Cc['prims'], [[('poly', o0), Cc['band']]])
            if d > 0:
                out['cols'] += _slabs(F, g, -C / 2 + d, C - 2 * d, tol, tag + '柱%d芯' % j, log, Cc['holes'])
                # 面の層の上は、その側の梁の外形で切る（芯と同じ架構の線の外形で切ると、梁の上端が少し低い側で、
                # 頭の上に細い切れ端が残った、11-11）
                for k_, off_ in (('+', C / 2 - d), ('-', -C / 2)):
                    ok_ = [tuple(q) for q in list(plate_g[k_].exterior.coords)[:-1]]
                    gf = region_2d(Cc['prims'], [[('poly', ok_), Cc['band']]]).difference(cut[k_])
                    out['cols'] += _slabs(F, gf, off_, d, tol, tag + '柱%d面%s' % (j, k_), log, Cc['holes'])
            else:
                out['cols'] += _slabs(F, g, -C / 2, C, tol, tag + '柱%d' % j, log, Cc['holes'])
    out['ptE'] = F.P(heads[0][0][0], heads[0][0][1])
    out['ptW'] = F.P(heads[-1][0][0], heads[-1][0][1])
    out['ptI'] = [F.P(G[0], G[1]) for G, h in heads[1:-1]]
    out['axis'] = rg.Vector3d(F.p[0], F.p[1], 0)
    out['line'] = rg.LineCurve(F.P(0, P['FL']), F.P(sup[-1], P['FL']))
    return out


COLS = ['k', 'sup', 'span_max', 's_tip', 'slope_deg', 'topE', 'topW', 'De', 'Dm', 'hang',
        'r_bend', 'r_defl', 'r_buckle', 'r_notch', 'r_shoulder', 'N_long', 'N_snow', 'gap', 'fit_dev']


def _row(pl, P):
    z0, m, dev = pl['tops']['0']
    sup = pl['sup']
    r = pl['r']
    return dict(
        k=pl['kk'], sup=';'.join('%.0f' % s for s in sup),
        span_max=max(b - a for a, b in zip(sup[:-1], sup[1:])), s_tip=pl['s_tip'],
        slope_deg=math.degrees(math.atan(m)), topE=z0, topW=z0 + m * sup[-1], De=pl['De'], Dm=pl['Dm'],
        hang=';'.join('%g:%g' % h for h in pl['hang']),
        r_bend=r['曲げ'], r_defl=r['たわみ'], r_buckle=r['座屈'], r_notch=r['凹み'], r_shoulder=r['肩'],
        N_long=';'.join('%.0f' % x for x in pl['NL']), N_snow=';'.join('%.0f' % x for x in pl['NS']),
        gap=P['col'] - 2 * pl['d'], fit_dev=max(v[2] for v in pl['tops'].values()))


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
    frames_ = _in('frames')
    frames_ = [_raw(x) for x in _as_list(frames_)] if frames_ is not None else []
    ks = _nums(_in('k')) if _in('k') is not None else []
    if not frames_ and not ks:
        return None, '入力 k（架構の番号）か frames（架構の線）が要る'
    if frames_ and not ks:
        ks = list(range(1, len(frames_) + 1))
    vin = _nums(_in('vIn', V_IN))
    global V_U
    vu = _in('vU')
    V_U = _f(vu) * 1000.0 if vu is not None else 0.0
    arcs, rays = guides(ks, vin, P['col'], P['FL']) if not frames_ else ([], [])
    cl = _in('colLines')
    A = dict(roof=_in('roof'), west=_in('west'), eave=_in('eave'), zE=_in('zE'), zW=_in('zW'),
             colLines=[_raw(x) for x in _as_list(cl)] if cl is not None else [],
             hang=_in('hang'), D=_in('D'), Dm=_in('Dm'), vin=vin, tol=tol)
    if A['roof'] is None and (A['zE'] is None or A['zW'] is None):
        return dict(spine=arcs, rays=rays), '下書きだけ（spine・rays）。架構を作るには roof か zE・zW も要る'
    cols_ = _in('showCol')
    mids_ = _in('mids')
    same = _in('same')
    same = True if same is None else (str(_raw(same)).strip().lower() not in ('false', '0', 'no', ''))
    res = dict(plates=[], cols=[], floors=[], ptE=[], ptI=[], ptW=[], ptM=[], axis=[], lines=[], spine=arcs, rays=rays)
    log = []
    if not HAVE_SHAPELY:
        return res, 'shapely が入っていない（コードの頭の # r: shapely で入るはず）'
    # 1. 位置と荷重から梁のせい
    plans = []
    for i, kk in enumerate(ks):
        fr = frames_[i] if i < len(frames_) else None
        try:
            plans.append(plan_one(i, kk, fr, P, A, log))
        except Exception as ex:
            log.append('k%g：%s' % (kk, ex))
    if not plans:
        log.append('架構 0 本')
        return res, '\n'.join(log)
    # 2. せいをそろえる（same、既定）：いちばん深いものに
    if same and A['D'] is None:
        De = max(p_['De'] for p_ in plans)
        deciders = [p_['kk'] for p_ in plans if p_['De'] >= De - 1e-6]
        for p_ in plans:
            if abs(p_['De'] - De) > 1e-6:
                r, NL, NS = frame_check(*p_['args'], De=De / 1000.0, Dm=De * P['DmR'] / 1000.0)
                p_.update(De=De, Dm=De * P['DmR'], r=r, NL=NL, NS=NS)
        log.append('梁のせい：端%.0f・真ん中%.0f（全部の架構でそろえる。決めたのは %s）' % (
            De, De * P['DmR'], '・'.join('k%g' % kk_ for kk_ in deciders)))
    # 3. 形
    rows = []
    for p_ in plans:
        r = p_['r']
        bad = [k_ for k_, v in r.items() if v > 1]
        if bad:
            log.append('k%g：足りない（%s）。%s' % (p_['kk'], '・'.join('%s %.2f' % (k_, r[k_]) for k_ in bad),
                                                   '柱を太く・梁の幅を広くする' if set(bad) & {'肩', '座屈', '凹み'} else 'せいを深く'))
        sc = _pick(cols_, p_['i'], True)
        if isinstance(sc, str):
            sc = sc.strip().lower() not in ('false', '0', 'no', '')
        mids_i = parse_mids(_pick(mids_, p_['i'], None))
        try:
            o = geom_one(p_, P, bool(sc), mids_i, tol, log)
        except Exception as ex:
            log.append('k%g：形ができない：%s' % (p_['kk'], ex))
            continue
        for key in ('plates', 'cols', 'floors', 'ptM', 'ptI'):
            res[key] += o[key]
        res['ptE'].append(o['ptE'])
        res['ptW'].append(o['ptW'])
        res['axis'].append(o['axis'])
        res['lines'].append(o['line'])
        rows.append(_row(p_, P))
    worst = {k_: max(p_['r'][k_] for p_ in plans) for k_ in plans[0]['r']}
    log.append('比のいちばん大きいもの（1以下でよい）：' + '・'.join('%s %.2f' % kv for kv in worst.items()))
    log.append('梁の幅%.0f×2本・柱%.0f・凹み%.0f・梁のあいだ%.0f' % (P['t'], P['col'], P['keyR'] * P['t'], P['col'] - 2 * P['keyR'] * P['t']))
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
    for key, name in (('plates', '梁'), ('cols', '柱'), ('floors', '床梁')):
        bs = res[key]
        if bs:
            bad = sum(1 for b in bs if b is None or not b.IsValid or not b.IsSolid)
            log.append('%s：%d 個（閉じた立体でないもの %d）' % (name, len(bs), bad))
    log.append('架構 %d 本（失敗 %d）' % (len(rows), len(ks) - len(rows)))
    res['table'] = text
    return res, '\n'.join(log)


# Rhino 8 の部品は、入力と上の定義を globals でなく別の名前の場所（locals）に置くことがある。一つにまとめる
globals().update(locals())
log = VERSION + '\n部品は動いたが、入力 k が見えない（k の名前と List Access を確かめる）'
if _RHINO and ('k' in globals() or 'frames' in globals()):
    _res, log = run()
    log = VERSION + '\n' + log
    if _res:
        spine, rays = _res['spine'], _res['rays']
    if _res and 'plates' in _res:
        plates, cols, floors = _res['plates'], _res['cols'], _res['floors']
        ptE, ptI, ptW, ptM = _res['ptE'], _res['ptI'], _res['ptW'], _res['ptM']
        axis, lines, table = _res['axis'], _res['lines'], _res['table']
