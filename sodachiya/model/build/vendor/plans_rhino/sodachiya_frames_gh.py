# -*- coding: utf-8 -*-
"""
育ち舎 架構ジェネレータ（本館＋遊戯室棟） — Grasshopper 版
下の「Grasshopper 部分」の説明を参照
Rhino 7 / 8 の Python で実行する。単位は mm（Rhino のモデル単位を「ミリメートル」に）。

使い方
  Rhino 8: ScriptEditor を開く → このファイルを開く → Run（Python 3）
  Rhino 7: EditPythonScript → このファイルを開く → Run
  先頭の PARAMETERS を書き換えて再実行すると、前回生成したものを消して作り直す。

作るもの（レイヤー別）
  SDC_grid        通り芯（放射線）と柱列の円弧（FL 高さ）
  SDC_column      柱（梁に挟まれる 1 本材）
  SDC_beam        2 枚組の梁（柱の両側）。柱際は曲率連続のハンチで柱に沿って下がる
  SDC_floor2      遊戯室棟の 2 階床梁（2 枚組）
  SDC_girder      桁（楕円断面、梁と柱を貫いて弧に沿って通る）
  SDC_laser       模型用の部品の外形（1/100、平置き）と必要枚数

座標の考え方
  共通の中心 CENTER から見て、建物は THETA_MID_DEG の方向（180 = 真西）にある。
  各棟の「東の柱列」の半径 R と、そこから外側（西）へ測る奥行き D で決まる。
  架構は放射線上に並び、本館の東の柱列でのピッチが PITCH。遊戯室棟も同じ放射線に乗る。
"""
import math

# =============================== PARAMETERS ===============================
# 配置は Grasshopper の入力 MainSE・MainNE・WestHandle（3 つの点）で決まる（下の説明を参照）
CENTER = (0.0, 0.0)          # 実行時に MainSW / MainNW から計算される
THETA_MID_DEG = 180.0        # 実行時に MainSW / MainNW から計算される
PITCH = 3000.0               # 本館の西の柱列（背骨）でのスパン（mm）。東の柱列では少し狭くなる

MAIN = dict(
    R=73000.0,               # 中心から本館の東の柱列までの距離（既定：背骨の半径 85 m）（背骨の半径 = R + D。GH では入力 R が背骨の半径）
    SPANS=19,                # スパン数（架構の本数は +1）
    D=12000.0,               # 東の柱列 → 西の柱列（奥行き）
    EAVE=3000.0,             # 東の庇の出（柱芯から）
    LOW_SOFFIT=2400.0,       # 【固定】低い側（東の柱列＝ガラス面）での梁の下端の高さ（FL から）
    SLOPE_N=12.0,            # 勾配 1/N（東が低く、西へ上がる）。GH の入力 SlopeMain があればそちら
    TOP_E=0.0, TOP_W=0.0,    # 梁の上端の高さ（上の 2 つから自動計算）
    BEAM_DEPTH=600.0,        # 梁せい（スパン中央）
    EAVE_TIP_DEPTH=250.0,    # 庇の先端の梁せい
)
WEST = dict(
    GAP=700.0,               # 本館の西の柱列 → 遊戯室棟の東の柱列（800 = 柱を背中合わせ＋エキスパンションジョイント。3000 にすると間に通り土間）
    START=2,                 # 本館の何本目の放射線から始めるか（0 = 北端）。WestHandle があればそちらで決まる
    SPANS=10,                # 北 7 スパン＝遊戯室（約 270㎡）、南 3 スパン＝キッチン（本館のホール 3 スパンの真向かい）
    D=12000.0,
    EAVE=0.0,
    CEIL2=2400.0,            # 【固定】低い側（西）での 2 階の天井高（梁の下端まで）
    FLOOR2_FINISH=50.0,      # 2 階床梁の上の床仕上げ
    SLOPE_N=50.0,            # 勾配 1/N（西が低く、東へ上がる）。GH の入力 SlopeWest があればそちら
    TOP_E=0.0, TOP_W=0.0,    # 梁の上端の高さ（自動計算）
    BEAM_DEPTH=650.0,
    EAVE_TIP_DEPTH=250.0,
    FLOOR2_FRAMES=(5, 10),   # 2 階床梁を入れる架構の範囲（START からの番号、0 = 北端、両端含む）。キッチンの上＋遊戯室の南 2 スパン
    FLOOR2_TOP=3200.0,       # 2 階床梁の上端
    FLOOR2_DEPTH=400.0,
)



def apply_heights(n_main=None, n_west=None):
    """低い側の高さを固定し、勾配から高い側を決める（N <= 0 は水平）"""
    if n_main is not None:
        MAIN['SLOPE_N'] = n_main
    if n_west is not None:
        WEST['SLOPE_N'] = n_west
    sm = 1.0 / MAIN['SLOPE_N'] if MAIN['SLOPE_N'] > 0 else 0.0
    sw = 1.0 / WEST['SLOPE_N'] if WEST['SLOPE_N'] > 0 else 0.0
    MAIN['TOP_E'] = MAIN['LOW_SOFFIT'] + MAIN['BEAM_DEPTH']
    MAIN['TOP_W'] = MAIN['TOP_E'] + sm * MAIN['D']
    WEST['TOP_W'] = WEST['FLOOR2_TOP'] + WEST['FLOOR2_FINISH'] + WEST['CEIL2'] + WEST['BEAM_DEPTH']
    WEST['TOP_E'] = WEST['TOP_W'] + sw * WEST['D']


apply_heights()

COL_T = 180.0                # 柱の厚み（弧の方向）
COL_D_BASE = 400.0           # 柱の幅（放射方向）脚元（オリジナルに倣い一定の太さ。テーパーにするなら 250 など）
COL_D_TOP = 400.0            # 柱の幅 頭
BEAM_T = 90.0                # 梁 1 枚の厚み（柱の両側に 1 枚ずつ）

JOINT_STYLE = 'tamedia'      # 'tamedia' = 柱と梁の交わりを、桁を同じ厚みで包む楕円でつなぐ（オリジナルの断面に倣う）
                             # 'oval' = 梁の端を楕円の頭に膨らませるだけ / 'haunch' = 柱に沿って長く下がるハンチ
JOINT_MARGIN = 180.0         # 'tamedia'：桁のまわりを包む木の厚み（楕円の半径 = 桁の半径 + これ）
JOINT_FILLET = 300.0         # 'tamedia'：梁の下面と楕円のつなぎの丸み（大きいほどなだらか）
COL_FILLET = 150.0           # 'tamedia'：柱の面と楕円のつなぎの丸み
TOP_ROUND = 150.0            # 'tamedia'：梁の丸い端が上端と出会う角の丸み（上端に沿った長さ）
HEAD_A = 400.0               # 楕円の頭の半幅（放射方向）
HEAD_B = 450.0               # 楕円の頭の半高さ（中心は桁の中心）
HEAD_SMOOTH = 60.0           # 頭と梁の下端のつなぎ目の丸み（大きいほどなだらか）
HAUNCH_DROP = 900.0          # 梁が柱に沿って下がる長さ（梁下端から）
HAUNCH_RUN = 1200.0          # ハンチの曲線が梁下端に沿って始まる距離（柱面から）
HAUNCH_RUN_EAVE = 700.0      # 庇側のハンチ
HAUNCH_FULL = 0.75           # 曲線のふくらみ 0.5（浅い）〜 0.9（角に近い）

GIRDER_W = 200.0             # 桁（楕円）の幅（放射方向）
GIRDER_H = 400.0             # 桁の高さ
GIRDER_OVERHANG = 600.0      # 端の架構から桁が突き出す長さ
GIRDER_FROM_TOP = GIRDER_H / 2.0 + JOINT_MARGIN   # 梁の上端から桁の中心まで（= 380）。オリジナルに倣い、桁を包む楕円の上端が梁の上端に接する位置。None = 梁せいの中央
GIRDER_FROM_TOP2 = 350.0     # 2 階床梁での同じ距離
MIN_CLEAR = 2200.0           # 桁の下端の最低高さ（これを下回ると警告。建具の高さ 2.0〜2.1m＋余裕）
NEIGHBOR_DIR_DEG = 45.0      # 隣家のある辺の外向きの方角（45 = 北東）。この辺だけは 1m 余裕線の外をエラーにする
NEIGHBOR_CLEAR = 1000.0      # 隣家側で必要なあき
GAP_CLEAR = 100.0            # 本館と遊戯室棟の架構どうしのすき間の最小（エキスパンションジョイント）。WestHandle を近づけてもこれより近づかない
HOLE_CLEAR = 10.0            # 穴のクリアランス（片側、実寸。模型では 0.1mm）

LASER = True                 # 模型用の部品外形を描くか
LASER_SCALE = 0.01           # 1/100
LASER_ORIGIN = (60000.0, -20000.0)  # 部品を並べる場所（敷地の東の外、実寸座標）
MODEL_COL_LAYERS = 2         # 模型で柱を何枚重ねにするか（0.8mm×2 = 1.6mm）
# ==========================================================================


# ---------------------------- pure geometry ----------------------------
def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def g2_ctrl(A, C, B, full=HAUNCH_FULL):
    """直線 A→C と C→B を角 C で曲率連続（両端で曲率 0）につなぐ 5 次ベジエの制御点"""
    k1, k2 = full * 0.5, full
    return [A, lerp(A, C, k1), lerp(A, C, k2), lerp(B, C, k2), lerp(B, C, k1), B]


def bez(ctrl, t):
    n = len(ctrl) - 1
    x = y = 0.0
    for i, p in enumerate(ctrl):
        c = math.factorial(n) / (math.factorial(i) * math.factorial(n - i)) * (1 - t) ** (n - i) * t ** i
        x += c * p[0]; y += c * p[1]
    return (x, y)


def intersect(p1, p2, p3, p4):
    """2 直線（p1p2, p3p4）の交点"""
    x1, y1 = p1; x2, y2 = p2; x3, y3 = p3; x4, y4 = p4
    d = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    a = x1 * y2 - y1 * x2; b = x3 * y4 - y3 * x4
    return ((a * (x3 - x4) - (x1 - x2) * b) / d, (a * (y3 - y4) - (y1 - y2) * b) / d)


class Col(object):
    """放射方向 u に中心をもつテーパー柱。face(+1) は西側（u が大きい側）、face(-1) は東側"""
    def __init__(self, u, height):
        self.u, self.h = u, height

    def half(self, z):
        return 0.5 * (COL_D_BASE + (COL_D_TOP - COL_D_BASE) * z / self.h)

    def face_pt(self, side, z):
        return (self.u + side * self.half(z), z)

    def face_line(self, side):
        return self.face_pt(side, 0.0), self.face_pt(side, self.h)


def smin(a, b, k):
    """なめらかな最小値（2 本の線の交わりを丸める）"""
    m = min(a, b)
    return m - k * math.log(math.exp(-(a - m) / k) + math.exp(-(b - m) / k))


def oval_beam(top, soff_fn, u_heads, zc_fn, u_start, start_tip, a=None, b=None):
    """梁の外形（楕円の頭つき）を点列で返す。
    top(u): 上端, soff_fn(u): 下端（頭が無いとき）, u_heads: 頭の中心（柱芯）, zc_fn(u): 頭の中心の高さ
    u_start: 東端の u。start_tip=(u, z_bottom) なら東端は庇の先端（垂直に切る）、None なら楕円の丸い端"""
    a = HEAD_A if a is None else a
    b = HEAD_B if b is None else b
    k = HEAD_SMOOTH

    def ebot(u, uc):
        x = (u - uc) / a
        if abs(x) >= 1.0:
            return None
        return zc_fn(uc) - b * math.sqrt(1.0 - x * x)

    def zbot(u):
        z = soff_fn(u)
        for uc in u_heads:
            e = ebot(u, uc)
            if e is not None:
                z = smin(z, e, k)
        return z

    def arc(uc, side, n=24):
        """楕円の外側の半分：上端との交点 → 最下点（side=+1 西端、-1 東端）"""
        zc = zc_fn(uc); t0 = top(uc)
        s0 = math.asin(max(-1.0, min(1.0, (t0 - zc) / b)))
        pts = []
        for i in range(n + 1):
            ang = s0 + (-math.pi / 2 - s0) * i / float(n)
            pts.append((uc + side * a * math.cos(ang), zc + b * math.sin(ang)))
        return pts

    uw = u_heads[-1]
    west = arc(uw, +1)                                 # 西端の丸い頭（上 → 下）
    T1 = (west[0][0], top(west[0][0]))
    west[0] = T1
    # 下端：西の頭の最下点 → 東へ
    if start_tip is not None:
        u_end = start_tip[0]
    else:
        u_end = u_heads[0]
    n = max(40, int(abs(uw - u_end) / 40.0))
    bottom = [(uw + (u_end - uw) * i / float(n), 0.0) for i in range(n + 1)]
    bottom = [(u, zbot(u)) for u, _ in bottom]
    bottom[0] = west[-1]
    segs = [('P', west), ('P', bottom)]
    if start_tip is not None:
        bottom[-1] = start_tip
        T0 = (start_tip[0], top(start_tip[0]))
        segs.append(('L', [start_tip, T0]))
    else:
        east = arc(u_heads[0], -1)                     # 東端の丸い頭（上 → 下）
        east.reverse()                                 # 下 → 上
        bottom[-1] = east[0]
        T0 = (east[-1][0], top(east[-1][0]))
        east[-1] = T0
        segs.append(('P', east))
    segs.append(('L', [T0, T1]))
    return segs, zbot


def rev_segs(segs):
    return [(k, list(reversed(p))) for k, p in reversed(segs)]


def smin3(a, b, k):
    """曲率連続のなめらかな最小値（差が k より大きいところは正確に min）"""
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * h * k / 6.0


def sd_ellipse(x, y, a, b):
    """楕円（半径 a, b）までのおよその符号付き距離（内側が負）"""
    k0 = math.hypot(x / a, y / b)
    k1 = math.hypot(x / (a * a), y / (b * b))
    if k1 < 1e-12:
        return -min(a, b)
    return k0 * (k0 - 1.0) / k1


def _root(f, p_in, d, step=10.0, far=3000.0):
    """p_in（内側）から向き d へ進み、外へ出る境界の点を返す"""
    s0 = 0.0
    s = step
    while s < far and f(p_in[0] + d[0] * s, p_in[1] + d[1] * s) < 0.0:
        s0 = s
        s += step
    if s >= far:
        return None
    lo, hi = s0, s
    for _ in range(26):
        m = 0.5 * (lo + hi)
        if f(p_in[0] + d[0] * m, p_in[1] + d[1] * m) < 0.0:
            lo = m
        else:
            hi = m
    m = 0.5 * (lo + hi)
    return (p_in[0] + d[0] * m, p_in[1] + d[1] * m)


def _runs(pts, straight):
    """点列を、直線上の区間は 'L'、曲がる区間は 'P' に分ける"""
    segs, cur, kind = [], [pts[0]], straight(pts[0])
    for p in pts[1:]:
        k = straight(p)
        cur.append(p)
        if k != kind:
            segs.append((kind, cur)); cur = [p]; kind = k
    segs.append((kind, cur))
    out = []
    for k, ps in segs:
        if len(ps) < 2:
            continue
        if k and len(ps) >= 2:
            out.append(('L', [ps[0], ps[-1]]))
        elif len(ps) == 2:
            out.append(('L', ps))
        else:
            out.append(('P', ps))
    return out


def joint_heads(heads):
    """桁を同じ厚みで包む楕円：[(u, zc)] → [(u, zc, a, b)]"""
    return [(u, z, GIRDER_W / 2.0 + JOINT_MARGIN, GIRDER_H / 2.0 + JOINT_MARGIN) for u, z in heads]


def round_top(pts, side, top):
    """丸い端（上端の点 → 下）の、上端と出会う角を丸める。
    返り値: (segs, 外形の点列)。segs = [('B', 上端の点 → 端の曲線), ('P', 端の曲線の残り)]"""
    if TOP_ROUND <= 0:
        return [('P', pts)], pts
    T = pts[0]
    L, j = 0.0, 1
    while j < len(pts) - 3 and L < TOP_ROUND:
        L += math.hypot(pts[j][0] - pts[j - 1][0], pts[j][1] - pts[j - 1][1])
        j += 1
    Bp = pts[j]
    tx, tz = pts[j + 1][0] - pts[j - 1][0], pts[j + 1][1] - pts[j - 1][1]
    ua = T[0] - side * TOP_ROUND
    A = (ua, top(ua))
    try:
        C = intersect(A, T, Bp, (Bp[0] + tx, Bp[1] + tz))
    except ZeroDivisionError:
        return [('P', pts)], pts
    if side * (C[0] - A[0]) <= 0 or C[1] < Bp[1]:      # 角が素直でないときは丸めない
        return [('P', pts)], pts
    ctrl = g2_ctrl(A, C, Bp)
    full = [bez(ctrl, i / 20.0) for i in range(20)] + pts[j:]
    return [('B', ctrl), ('P', pts[j:])], full


def tamedia_beam(top, soff, u_lo, u_hi, heads, eave_tip=None):
    """梁 1 枚の外形。帯（上端 top・下端 soff、u_lo〜u_hi）と、桁を包む楕円の頭をなめらかにつなぐ。
    u_lo / u_hi が頭の中心と同じなら、その端は楕円がそのまま丸い端になる。
    eave_tip=True なら u_lo で垂直に切る（庇の先端）。上端は top で切る。"""
    E = joint_heads(heads)
    k = JOINT_FILLET

    def f(u, z):
        d = max(soff(u) - z, z - top(u), u_lo - u, u - u_hi)
        for uc, zc, a, b in E:
            d = smin3(d, sd_ellipse(u - uc, z - zc, a, b), k)
        return max(d, z - top(u))

    reach = max(a for _, _, a, _ in E) + 2.0 * k

    def bottom_at(u):
        if all(abs(u - h[0]) > reach for h in E):     # 頭から遠いところはまっすぐな下面
            return (u, soff(u))
        return _root(f, (u, soff(u) + 50.0), (0.0, -1.0), step=10.0)

    def cap(uc, zc, side, n=48):
        """自由な端：上端との交点 → 真下（side=+1 は u が大きい側）"""
        ray = lambda ph: _root(f, (uc, zc), (side * math.cos(ph), math.sin(ph)), step=5.0)
        lo, hi = 0.0, math.pi / 2.0                     # lo: 境界が上端より下、hi: 上端に当たる
        for _ in range(40):
            m = 0.5 * (lo + hi)
            p = _root(f, (uc, zc), (side * math.cos(m), math.sin(m)), step=5.0)
            if p is not None and p[1] < top(p[0]) - 1e-6:
                lo = m
            else:
                hi = m
        ph0 = lo
        pts = [ray(ph0 + (-math.pi / 2.0 - ph0) * i / float(n)) for i in range(n + 1)]
        pts[0] = (pts[0][0], top(pts[0][0]))
        return round_top(pts, side, top)

    hs = sorted(E)
    # 下端：u_hi 側 → u_lo 側
    u_a = u_hi
    u_b = u_lo
    n = max(60, int(abs(u_a - u_b) / 25.0))
    bot = [bottom_at(u_a + (u_b - u_a) * i / float(n)) for i in range(n + 1)]
    segs = []
    free_hi = abs(hs[-1][0] - u_hi) < 1e-6
    free_lo = (not eave_tip) and abs(hs[0][0] - u_lo) < 1e-6
    caps = {}
    if free_hi:
        cs, cfull = cap(hs[-1][0], hs[-1][1], +1)
        caps[hs[-1][0]] = (+1, cfull)
        bot[0] = cfull[-1]
        segs += cs
        T1 = cfull[0]
    else:
        T1 = (u_hi, top(u_hi))
        segs.append(('L', [T1, bot[0]]))
    if free_lo:
        cs0, cfull0 = cap(hs[0][0], hs[0][1], -1)
        caps[hs[0][0]] = (-1, cfull0)
        bot[-1] = cfull0[-1]
    straight = lambda p: abs(p[1] - soff(p[0])) < 0.05
    segs += _runs(bot, straight)
    if free_lo:
        segs += rev_segs(cs0)
        T0 = cfull0[0]
    else:
        T0 = (u_lo, top(u_lo))
        segs.append(('L', [bot[-1], T0]))
    segs.append(('L', [T0, T1]))
    return segs, bot, caps


def tamedia_col(uc, ztop_fn, heads, cap=None):
    """柱 1 本の外形：一定の幅の柱と、桁を包む楕円をなめらかにつなぐ（脚元 → 頭 → 脚元）。
    cap=(side, 点列) は梁の丸い端：柱の頭がその外へはみ出さないよう、その側を丸い端に合わせる"""
    E = joint_heads(heads)
    k = COL_FILLET
    half = COL_D_TOP / 2.0

    def f(u, z):
        d = max(abs(u - uc) - half, -z)
        for hu, zc, a, b in E:
            d = smin3(d, sd_ellipse(u - hu, z - zc, a, b), k)
        return d

    ztop = min(ztop_fn(uc - half - 400.0), ztop_fn(uc + half + 400.0)) - 1.0
    zlow = max(0.0, min(zc - b for _, zc, _, b in E) - 2.0 * k)
    sides = []
    for side in (-1, +1):
        n = max(20, int((ztop - zlow) / 10.0))
        pts = [_root(f, (uc, zlow + (ztop - zlow) * i / float(n)), (side, 0.0), step=5.0) for i in range(n + 1)]
        pts = [(uc + side * half, 0.0)] + pts
        if cap is not None and cap[0] == side:
            cf = cap[1]
            imax = max(range(len(cf)), key=lambda i: side * cf[i][0])   # 丸い端のいちばん外の点
            upper = cf[:imax + 1]                                       # 上端 → いちばん外（z は下がる）

            def ucap(z):
                if z >= upper[0][1]:
                    return upper[0][0]
                for i in range(1, len(upper)):
                    z0, z1 = upper[i - 1][1], upper[i][1]
                    if z1 <= z <= z0:
                        t = (z0 - z) / (z0 - z1) if z0 > z1 else 0.0
                        return upper[i - 1][0] + (upper[i][0] - upper[i - 1][0]) * t
                return None
            q = []
            for pp in pts:
                uu = ucap(pp[1]) if pp[1] > upper[-1][1] else None
                q.append(pp if uu is None or side * (uu - pp[0]) >= 0 else (uu, pp[1]))
            zl = q[-1][1]
            pts = q + [pp for pp in reversed(upper) if pp[1] > zl + 1.0]   # 残りは丸い端に沿って上端まで
        else:
            pts.append((pts[-1][0], ztop_fn(pts[-1][0])))
        sides.append(pts)
    left, right = sides
    straight = lambda p: abs(abs(p[0] - uc) - half) < 0.05
    segs = []
    segs += _runs(right, straight)                      # 西の面：脚元 → 頭
    segs.append(('L', [right[-1], left[-1]]))           # 上端
    segs += _runs(list(reversed(left)), straight)       # 東の面：頭 → 脚元
    segs.append(('L', [left[0], right[0]]))             # 脚元
    return dict(u=uc, segs=segs, cap=cap)


def frame_profiles_tamedia(B, top_e, top_w, depth, eave, tip_depth):
    """オリジナル（Tamedia）に倣う：梁・柱とも、桁の楕円を同じ厚みで包む楕円で柱と梁をつなぐ。
    自由な端はその楕円がそのまま梁の丸い端になる。柱へ向かう出っ張りはない"""
    D = B['D']
    slope = (top_w - top_e) / D
    top = lambda u: top_e + slope * u
    gft = girder_from_top(depth)
    zc = lambda u: top(u) - gft
    if eave > 0:
        tip_z = top(-eave) - tip_depth
        root_z = top(0.0) - depth

        def soff(u):
            if u >= 0.0:
                return top(u) - depth
            return tip_z + (root_z - tip_z) * (u + eave) / eave
        u_lo = -eave
    else:
        soff = lambda u: top(u) - depth
        u_lo = 0.0
    heads = [(0.0, zc(0.0)), (D, zc(D))]
    seg, bot, caps = tamedia_beam(top, soff, u_lo, D, heads, eave_tip=eave > 0)
    cols = [tamedia_col(uc, top, [h], caps.get(uc)) for uc, h in zip((0.0, D), heads)]
    holes = list(heads)
    low_e = min(p[1] for p in bot if abs(p[0]) < 600.0)
    low_w = min(p[1] for p in bot if abs(p[0] - D) < 600.0)
    return dict(beam=seg, cols=cols, holes=holes, top=top, low=(low_e, low_w), soffit=(soff(0.0), soff(D)),
                heads=heads)


_PROF_CACHE = {}


def frame_profiles(B, top_e, top_w, depth, eave, tip_depth, run=HAUNCH_RUN, drop=HAUNCH_DROP):
    if JOINT_STYLE == 'tamedia':
        key = (B['D'], top_e, top_w, depth, eave, tip_depth, JOINT_MARGIN, JOINT_FILLET, COL_FILLET, GIRDER_FROM_TOP)
        if key not in _PROF_CACHE:
            _PROF_CACHE[key] = frame_profiles_tamedia(B, top_e, top_w, depth, eave, tip_depth)
        return _PROF_CACHE[key]
    if JOINT_STYLE == 'oval':
        return frame_profiles_oval(B, top_e, top_w, depth, eave, tip_depth)
    return frame_profiles_haunch(B, top_e, top_w, depth, eave, tip_depth, run, drop)


def girder_from_top(depth):
    return depth / 2.0 if GIRDER_FROM_TOP is None else GIRDER_FROM_TOP


def frame_profiles_oval(B, top_e, top_w, depth, eave, tip_depth):
    """楕円の頭で柱と梁をつなぐ架構（桁は頭の中心を貫く）"""
    D = B['D']
    slope = (top_w - top_e) / D
    top = lambda u: top_e + slope * u
    gft = girder_from_top(depth)
    zc = lambda uc: top(uc) - gft
    if eave > 0:
        tip_z = top(-eave) - tip_depth
        root_z = top(0.0) - depth

        def soff(u):
            if u >= 0.0:
                return top(u) - depth
            t = (u + eave) / eave
            return tip_z + (root_z - tip_z) * t
        tip = (-eave, tip_z)
    else:
        soff = lambda u: top(u) - depth
        tip = None
    segs, zbot = oval_beam(top, soff, [0.0, D], zc, -eave, tip)
    cols = []
    for uc in (0.0, D):
        c = Col(uc, top(uc))
        zt = top(uc)
        cols.append([c.face_pt(-1, 0.0), c.face_pt(+1, 0.0), c.face_pt(+1, zt), c.face_pt(-1, zt)])
    holes = [(0.0, zc(0.0)), (D, zc(D))]
    return dict(beam=segs, cols=cols, holes=holes, top=top, zbot=zbot)


def frame_profiles_haunch(B, top_e, top_w, depth, eave, tip_depth, run=HAUNCH_RUN, drop=HAUNCH_DROP):
    """1 つの架構の 2D 断面（u = 東の柱芯からの放射距離、z = FL からの高さ）。
    返り値: beam = [('L', [p0, p1]) | ('B', ctrl6)], cols = [poly], holes = [(u, z)]"""
    D = B['D']
    slope = (top_w - top_e) / D
    top = lambda u: top_e + slope * u
    soff = lambda u: top(u) - depth
    cE, cW = Col(0.0, top(0.0)), Col(D, top(D))
    seg = []

    zhb_w = soff(D) - drop
    zhb_e = soff(0.0) - drop
    # 上端：庇の先端（または東の柱の外面）→ 西の柱の外面
    u0 = -eave if eave > 0 else cE.face_pt(-1, top(0.0))[0]
    uW = cW.face_pt(+1, top(D))[0]
    T0, T1 = (u0, top(u0)), (uW, top(uW))
    seg.append(('L', [T0, T1]))
    # 西の柱の外面を下りる → 柱を横切る
    Wo = cW.face_pt(+1, zhb_w); Wi = cW.face_pt(-1, zhb_w)
    seg.append(('L', [T1, Wo])); seg.append(('L', [Wo, Wi]))
    # 西のハンチ（柱の内面 → 梁下端）
    sl = ((0.0, soff(0.0)), (D, soff(D)))
    Cw = intersect(cW.face_line(-1)[0], cW.face_line(-1)[1], sl[0], sl[1])
    Aw = (Cw[0] - run, soff(Cw[0] - run))
    seg.append(('B', g2_ctrl(Wi, Cw, Aw)))
    # 梁下端 → 東のハンチ
    Ce = intersect(cE.face_line(+1)[0], cE.face_line(+1)[1], sl[0], sl[1])
    Ae = (Ce[0] + run, soff(Ce[0] + run))
    seg.append(('L', [Aw, Ae]))
    Ei = cE.face_pt(+1, zhb_e); Eo = cE.face_pt(-1, zhb_e)
    seg.append(('B', g2_ctrl(Ae, Ce, Ei)))
    seg.append(('L', [Ei, Eo]))
    if eave > 0:
        # 庇：せいが先端に向かって細くなる直線の下端
        tip = (-eave, top(-eave) - tip_depth)
        root = (0.0, soff(0.0))
        Ceo = intersect(cE.face_line(-1)[0], cE.face_line(-1)[1], tip, root)
        dx, dz = root[0] - tip[0], root[1] - tip[1]
        L = math.hypot(dx, dz)
        Aeo = (Ceo[0] - HAUNCH_RUN_EAVE * dx / L, Ceo[1] - HAUNCH_RUN_EAVE * dz / L)
        seg.append(('B', g2_ctrl(Eo, Ceo, Aeo)))
        seg.append(('L', [Aeo, tip])); seg.append(('L', [tip, T0]))
    else:
        seg.append(('L', [Eo, T0]))
    cols = []
    for c in (cE, cW):
        zt = top(c.u) + 0.0
        cols.append([c.face_pt(-1, 0.0), c.face_pt(+1, 0.0), c.face_pt(+1, zt), c.face_pt(-1, zt)])
    gft = depth / 2.0 if GIRDER_FROM_TOP is None else GIRDER_FROM_TOP
    holes = [(0.0, top(0.0) - gft), (D, top(D) - gft)]
    return dict(beam=seg, cols=cols, holes=holes, top=top)


def floor2_profile_tamedia(B):
    """2 階床梁（'tamedia'）。この床梁がある架構の柱は、屋根の頭と床の頭の 2 つの楕円をもつ"""
    D = B['D']; zt = B['FLOOR2_TOP']; dp = B['FLOOR2_DEPTH']
    top = lambda u: zt
    heads = [(0.0, zt - GIRDER_FROM_TOP2), (D, zt - GIRDER_FROM_TOP2)]
    seg, bot, _caps = tamedia_beam(top, lambda u: zt - dp, 0.0, D, heads)
    P = B['prof']
    cols = [tamedia_col(c['u'], P['top'], [h for h in P['heads'] + heads if abs(h[0] - c['u']) < 1.0], c['cap'])
            for c in P['cols']]
    return dict(beam=seg, holes=heads, cols=cols, low=(min(p[1] for p in bot if abs(p[0]) < 600.0),
                                                       min(p[1] for p in bot if abs(p[0] - D) < 600.0)))


def floor2_profile(B):
    if JOINT_STYLE == 'tamedia':
        key = ('f2', B['D'], B['FLOOR2_TOP'], B['FLOOR2_DEPTH'], B['TOP_E'], B['TOP_W'], GIRDER_FROM_TOP2)
        if key not in _PROF_CACHE:
            _PROF_CACHE[key] = floor2_profile_tamedia(B)
        return _PROF_CACHE[key]
    if JOINT_STYLE == 'oval':
        D = B['D']; zt = B['FLOOR2_TOP']; dp = B['FLOOR2_DEPTH']
        top = lambda u: zt
        gft = GIRDER_FROM_TOP2
        segs, zbot = oval_beam(top, lambda u: zt - dp, [0.0, D], lambda uc: zt - gft, 0.0, None,
                               a=HEAD_A * 0.8, b=HEAD_B * 0.8)
        return dict(beam=segs, holes=[(0.0, zt - gft), (D, zt - gft)], zbot=zbot)
    return floor2_profile_haunch(B)


def floor2_profile_haunch(B):
    """遊戯室棟の 2 階床梁（上端水平、両外面は柱の外面まで、内側にハンチ）"""
    D = B['D']; zt = B['FLOOR2_TOP']; dp = B['FLOOR2_DEPTH']
    full_top = lambda u: B['TOP_E'] + (B['TOP_W'] - B['TOP_E']) / D * u
    cE, cW = Col(0.0, full_top(0.0)), Col(D, full_top(D))
    drop, run = HAUNCH_DROP * 0.6, HAUNCH_RUN * 0.6
    zs = zt - dp; zhb = zs - drop
    sl = ((0.0, zs), (D, zs))
    T0 = cE.face_pt(-1, zt); T1 = cW.face_pt(+1, zt)
    Wo, Wi = cW.face_pt(+1, zhb), cW.face_pt(-1, zhb)
    Ei, Eo = cE.face_pt(+1, zhb), cE.face_pt(-1, zhb)
    Cw = intersect(cW.face_line(-1)[0], cW.face_line(-1)[1], sl[0], sl[1])
    Ce = intersect(cE.face_line(+1)[0], cE.face_line(+1)[1], sl[0], sl[1])
    Aw, Ae = (Cw[0] - run, zs), (Ce[0] + run, zs)
    seg = [('L', [T0, T1]), ('L', [T1, Wo]), ('L', [Wo, Wi]), ('B', g2_ctrl(Wi, Cw, Aw)),
           ('L', [Aw, Ae]), ('B', g2_ctrl(Ae, Ce, Ei)), ('L', [Ei, Eo]), ('L', [Eo, T0])]
    holes = [(0.0, zt - GIRDER_FROM_TOP2), (D, zt - GIRDER_FROM_TOP2)]
    return dict(beam=seg, holes=holes)


def buildings():
    """各棟の放射線（角度）、東の柱列の半径、断面を返す"""
    dth = PITCH / (MAIN['R'] + MAIN['D'])
    th_mid = math.radians(THETA_MID_DEG)
    th0 = th_mid - dth * MAIN['SPANS'] / 2.0
    out = []
    m = dict(MAIN); m['name'] = 'main'
    m['thetas'] = [th0 + dth * i for i in range(MAIN['SPANS'] + 1)]
    m['prof'] = frame_profiles(m, m['TOP_E'], m['TOP_W'], m['BEAM_DEPTH'], m['EAVE'], m['EAVE_TIP_DEPTH'])
    out.append(m)
    w = dict(WEST); w['name'] = 'west'
    w['R'] = MAIN['R'] + MAIN['D'] + WEST['GAP']
    w['thetas'] = [th0 + dth * (WEST['START'] + i) for i in range(WEST['SPANS'] + 1)]
    w['prof'] = frame_profiles(w, w['TOP_E'], w['TOP_W'], w['BEAM_DEPTH'], w['EAVE'], w['EAVE_TIP_DEPTH'])
    w['floor2'] = floor2_profile(w)
    out.append(w)
    return out


def world(Bd, th, u, z, t=0.0):
    """断面座標 (u, z) と弧方向のずれ t をワールド座標へ"""
    r = Bd['R'] + u
    cx, cy = CENTER
    ux, uy = math.cos(th), math.sin(th)          # 外向き（西）
    tx, ty = -math.sin(th), math.cos(th)         # 弧方向（角度が増える向き = 南）
    return (cx + r * ux + t * tx, cy + r * uy + t * ty, z)






# =========================== Grasshopper 部分 ===========================
# このファイルの全文を Grasshopper の Script コンポーネント（Rhino 8: Python 3）
# または GhPython コンポーネント（Rhino 7）に貼り付ける。
#
# 入力（名前・型ヒントをこのとおりに）
#   R          float    円弧の半径［m］（中心 → 本館の西の柱列＝背骨）。スライダ 50〜1000 など
#   SlopeMain  float    本館の屋根勾配 1/N の N（12 なら 1/12）。0 で水平。
#                       低い東側（ガラス面での梁下 MAIN['LOW_SOFFIT']）を固定し、西の高さが決まる
#   SlopeWest  float    遊戯室棟の屋根勾配 1/N の N（50 なら 1/50）。0 で水平。
#                       低い西側（2 階の床＋天井高 WEST['CEIL2']）を固定し、東の高さが決まる
#   MainSE     Point3d  本館の南東の角（庇の先端の南端。いちばん敷地からはみ出しやすい角）。建物の位置
#   MainNE     Point3d  本館の北東の角の方向を示す点。SE → NE の向きが本館の北の向き（距離は使わない）
#                       （古い入力名 MainSW / MainNW＝西の柱列の角も使える。MainSE / MainNE が優先）
#                       2 点をグループにしておくと、クリックで 2 点まとめて移動（平行移動）、
#                       Cmd+Shift+クリック（Windows は Ctrl+Shift）で 1 点だけ選んで回転
#   WestHandle Point3d  遊戯室棟の北西の角（西の柱列の北端）。ドラッグすると本館に対する
#                       南北のずれ（架構の位置に吸着）と、本館との間隔 GAP が決まる
#   Site       Curve    敷地境界（SITE レイヤーの線を参照）
#   Setback    Curve    1m 余裕線（任意。SITE_setback_1m の線を参照）
# 出力
#   Columns, Beams, Floor2, Girders  架構の立体（右クリック → Bake で Rhino に書き出し）
#   Grid       通り芯
#   Footprint  各棟の外形線（庇の先端〜西の柱の外面）
#   Outside    はみ出している点（エラー：敷地境界の外、または隣家側の 1m 余裕線の外）
#   NearEdge   1m 余裕線の外に出ている外形の部分（注意。目立たない線）
#   OK         True / False
#   Report     長さ・はみ出しの報告
#   Snapped    角の位置（本館の南東・北東、遊戯室棟の北西）。Bake すると、上の 3 つの入力に使う点になる
import Rhino.Geometry as rg
import Rhino
try:
    from System.Collections.Generic import List as _NetList
except Exception:            # Rhino の外（テスト用）
    _NetList = None


def NL(T, items):
    """Python のリストを .NET の List<T> に（Python 3 / 2 どちらでも確実に渡すため）"""
    items = list(items)
    if _NetList is None:
        return items
    l = _NetList[T]()
    for x in items:
        l.Add(x)
    return l

TOL = Rhino.RhinoDoc.ActiveDoc.ModelAbsoluteTolerance if Rhino.RhinoDoc.ActiveDoc else 0.01


def _num(v, d):
    try:
        return d if v is None else float(v)
    except Exception:
        return d


def P3(p):
    return rg.Point3d(p[0], p[1], p[2])


def gh_curve(seg, to3d):
    parts = []
    for kind, pts in seg:
        p3 = [P3(to3d(p)) for p in pts]
        if kind == 'L':
            parts.append(rg.LineCurve(p3[0], p3[1]))
        elif kind == 'P':
            parts.append(rg.Curve.CreateInterpolatedCurve(NL(rg.Point3d, p3), 3))
        else:
            parts.append(rg.NurbsCurve.Create(False, 5, NL(rg.Point3d, p3)))
    if any(c is None for c in parts):
        DIAG.append('曲線を作れない区間があった')
    j = rg.Curve.JoinCurves(NL(rg.Curve, [c for c in parts if c is not None]), TOL)
    if j and len(j) == 1 and j[0].IsClosed:
        return j[0]
    # つながらない／閉じないとき：同じ点を通る折れ線で代用（形はほぼ同じ）
    DIAG.append('外形が閉じず、折れ線で代用した（%d 本に分かれた）' % (len(j) if j else 0))
    pts = []
    for kind, ps in seg:
        q = [bez(ps, i / 20.0) for i in range(21)] if kind == 'B' else list(ps)
        pts += q if not pts else q[1:]
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    return rg.PolylineCurve(NL(rg.Point3d, [P3(to3d(p)) for p in pts]))


def gh_ellipse(Bd, th, uz, t, w, h):
    o = P3(world(Bd, th, uz[0], uz[1], t))
    plane = rg.Plane(o, rg.Vector3d(math.cos(th), math.sin(th), 0), rg.Vector3d(0, 0, 1))
    return rg.Ellipse(plane, w / 2.0, h / 2.0).ToNurbsCurve()


def gh_plate(Bd, th, outer, holes, t0, thick):
    to3d = lambda p: world(Bd, th, p[0], p[1], t0)
    crvs = [outer(to3d)]
    for hz in holes:
        crvs.append(gh_ellipse(Bd, th, hz, t0, GIRDER_W + 2 * HOLE_CLEAR, GIRDER_H + 2 * HOLE_CLEAR))
    out = []
    breps = rg.Brep.CreatePlanarBreps(NL(rg.Curve, crvs), TOL) if crvs[0] is not None else None
    if not breps:
        DIAG.append('板（平面）を作れなかった')
    for b in (breps or []):
        a = P3(world(Bd, th, 0, 0, t0)); c = P3(world(Bd, th, 0, 0, t0 + thick))
        e = b.Faces[0].CreateExtrusion(rg.LineCurve(a, c), True)
        if e:
            out.append(e)
    return out


DIAG = []


def gh_build():
    cols, beams, f2s, girs, grid, feet = [], [], [], [], [], []
    for Bd in buildings():
        P = Bd['prof']
        f2on = lambda i: 'floor2' in Bd and Bd['FLOOR2_FRAMES'][0] <= i <= Bd['FLOOR2_FRAMES'][1]
        for i, th in enumerate(Bd['thetas']):
            clist = Bd['floor2']['cols'] if (f2on(i) and 'cols' in Bd['floor2']) else P['cols']
            for poly in clist:
                if isinstance(poly, dict):              # 'tamedia'：曲線の外形
                    uc = poly['u']
                    fn = lambda to3d, s=poly['segs']: gh_curve(s, to3d)
                else:
                    uc = (poly[0][0] + poly[1][0]) / 2.0
                    fn = lambda to3d, poly=poly: rg.PolylineCurve(NL(rg.Point3d, [P3(to3d(p)) for p in poly + [poly[0]]]))
                hs = [h for h in P['holes'] if abs(h[0] - uc) < 1.0]
                if f2on(i):
                    hs += [h for h in Bd['floor2']['holes'] if abs(h[0] - uc) < 1.0]
                cols += gh_plate(Bd, th, fn, hs, -COL_T / 2, COL_T)
            for t0 in (-COL_T / 2 - BEAM_T, COL_T / 2):
                beams += gh_plate(Bd, th, lambda to3d: gh_curve(P['beam'], to3d), P['holes'], t0, BEAM_T)
                if f2on(i):
                    F = Bd['floor2']
                    f2s += gh_plate(Bd, th, lambda to3d: gh_curve(F['beam'], to3d), F['holes'], t0, BEAM_T)
            grid.append(rg.LineCurve(P3(world(Bd, th, -max(Bd['EAVE'], 1000.0), 0)),
                                     P3(world(Bd, th, Bd['D'] + 1000.0, 0))))
        # 桁
        hl = [(False, h) for h in P['holes']]
        if 'floor2' in Bd:
            hl += [(True, h) for h in Bd['floor2']['holes']]
        for f2, uz in hl:
            r = Bd['R'] + uz[0]
            ia, ib = (Bd['FLOOR2_FRAMES'] if f2 else (0, len(Bd['thetas']) - 1))
            tha = Bd['thetas'][ia] - GIRDER_OVERHANG / r
            thb = Bd['thetas'][ib] + GIRDER_OVERHANG / r
            arc = rg.ArcCurve(rg.Arc(P3(world(Bd, tha, uz[0], uz[1])), P3(world(Bd, (tha + thb) / 2, uz[0], uz[1])),
                                     P3(world(Bd, thb, uz[0], uz[1]))))
            prof = gh_ellipse(Bd, tha, uz, 0.0, GIRDER_W, GIRDER_H)
            for s in (rg.Brep.CreateFromSweep(arc, prof, True, TOL) or []):
                capped = s.CapPlanarHoles(TOL)
                girs.append(capped if capped else s)
            if not f2:
                grid.append(rg.ArcCurve(rg.Arc(P3(world(Bd, tha, uz[0], 0)), P3(world(Bd, (tha + thb) / 2, uz[0], 0)),
                                               P3(world(Bd, thb, uz[0], 0)))))
        # 外形（庇の先端 〜 西の柱の外面）
        ue = -Bd['EAVE'] if Bd['EAVE'] > 0 else -COL_D_TOP / 2.0
        uw = Bd['D'] + COL_D_TOP / 2.0
        th0, th1 = Bd['thetas'][0], Bd['thetas'][-1]
        tt = [th0 + (th1 - th0) * k / 40.0 for k in range(41)]
        pts = [world(Bd, t, ue, 0) for t in tt] + [world(Bd, t, uw, 0) for t in reversed(tt)]
        pts.append(pts[0])
        feet.append((Bd['name'], rg.PolylineCurve(NL(rg.Point3d, [P3(p) for p in pts])), pts[:-1]))
    return cols, beams, f2s, girs, grid, feet


def _in(name):
    """入力を名前で取り出す（入力端子が無くても既定値で動く）"""
    return globals().get(name, None)


MAIN_HANDLE_DEFAULT = ((6571.2, -64875.1), 80.8)    # 本館の南東の角（庇の先端）、北の向き（度）。敷地に収まるよう探した値（背骨の半径 85 m のとき）
HANDLE_Z = 10000.0           # Snapped の点の高さ（屋根より上。位置の計算には XY だけを使う）


def east_edge_u():
    """本館の東の外形（庇の先端）の放射方向の位置 u（東の柱芯から）"""
    return -MAIN['EAVE'] if MAIN['EAVE'] > 0 else -COL_D_TOP / 2.0


def set_placement_sw(p0, u, r=None):
    """本館の弧（半径 r。既定は西の柱列＝背骨）の南端 p0 と、北へ向かう単位ベクトル u から中心と向きを決める。
    同じ 2 本の放射線にはさまれた弦は、どの半径でも平行なので、u はどの弧で測っても同じ"""
    global CENTER, THETA_MID_DEG
    if r is None:
        r = MAIN['R'] + MAIN['D']
    a = MAIN['SPANS'] * PITCH / (MAIN['R'] + MAIN['D'])
    c = 2 * r * math.sin(a / 2.0)
    mid = (p0[0] + u[0] * c / 2.0, p0[1] + u[1] * c / 2.0)
    n = (u[1], -u[0])                           # 北に向かって右 = 東（中心の側）
    h = r * math.cos(a / 2.0)
    CENTER = (mid[0] + n[0] * h, mid[1] + n[1] * h)
    THETA_MID_DEG = math.degrees(math.atan2(-n[1], -n[0]))


def handle_from_points(p0, p1):
    dx, dy = p1.X - p0.X, p1.Y - p0.Y
    l = math.hypot(dx, dy)
    if l < 1e-6:
        return (p0.X, p0.Y), (0.0, 1.0)
    return (p0.X, p0.Y), (dx / l, dy / l)


def _seg_us(segs):
    us = []
    for kind, ps in segs:
        us += [p[0] for p in ps]
    return us


def gap_min():
    """本館の西端と遊戯室棟の東端がぶつからない最小の GAP（柱列どうしの間隔、100 mm 単位に切り上げ）。
    丸い端や柱のふくらみも含めた、平面で見たいちばん外側どうしで測る"""
    Bm = dict(MAIN); Bw = dict(WEST)
    Pm = frame_profiles(Bm, MAIN['TOP_E'], MAIN['TOP_W'], MAIN['BEAM_DEPTH'], MAIN['EAVE'], MAIN['EAVE_TIP_DEPTH'])
    Pw = frame_profiles(Bw, WEST['TOP_E'], WEST['TOP_W'], WEST['BEAM_DEPTH'], WEST['EAVE'], WEST['EAVE_TIP_DEPTH'])
    um = _seg_us(Pm['beam'])
    uw = _seg_us(Pw['beam'])
    for c in Pm['cols']:
        um += _seg_us(c['segs']) if isinstance(c, dict) else [p[0] for p in c]
    for c in Pw['cols']:
        uw += _seg_us(c['segs']) if isinstance(c, dict) else [p[0] for p in c]
    if JOINT_STYLE == 'tamedia':
        Bw['prof'] = Pw
        F = floor2_profile(Bw)
        uw += _seg_us(F['beam'])
        for c in F.get('cols', []):
            uw += _seg_us(c['segs'])
    ext_m = max(um) - MAIN['D']          # 本館：西の柱芯より外へ出る量
    ext_w = -min(uw)                     # 遊戯室棟：東の柱芯より外へ出る量
    return math.ceil((ext_m + ext_w + GAP_CLEAR) / 100.0) * 100.0


def west_from_handle(h):
    """遊戯室棟の北西の角の点から、START（架構の番号）と GAP を決める"""
    cx, cy = CENTER
    rho = math.hypot(h.X - cx, h.Y - cy)
    th = math.atan2(h.Y - cy, h.X - cx)
    dth = PITCH / (MAIN['R'] + MAIN['D'])
    th0 = math.radians(THETA_MID_DEG) - dth * MAIN['SPANS'] / 2.0
    d = (th - th0 + math.pi) % (2 * math.pi) - math.pi
    WEST['START'] = int(round(d / dth))
    gap = rho - (MAIN['R'] + MAIN['D'] + WEST['D'])
    gmin = gap_min()
    WEST['GAP'] = max(gmin, round(gap / 100.0) * 100.0)
    WEST['GAP_CLAMPED'] = gap < gmin - 50.0


def seg_dist(p, seg):
    (ax, ay), (bx, by) = seg
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def neighbor_edge(site):
    """敷地境界のうち、外向きの向きが NEIGHBOR_DIR_DEG にいちばん近い辺（隣家のある北東辺）"""
    if site is None:
        return None
    try:
        segs = [((c.PointAtStart.X, c.PointAtStart.Y), (c.PointAtEnd.X, c.PointAtEnd.Y)) for c in site.DuplicateSegments()]
    except Exception:
        return None
    want = (math.cos(math.radians(NEIGHBOR_DIR_DEG)), math.sin(math.radians(NEIGHBOR_DIR_DEG)))
    best, bs = None, -2.0
    for a, b in segs:
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1000.0:
            continue
        n = (dy / L, -dx / L)
        m = ((a[0] + b[0]) / 2.0 + n[0] * 500.0, (a[1] + b[1]) / 2.0 + n[1] * 500.0)
        if site.Contains(rg.Point3d(m[0], m[1], 0), rg.Plane.WorldXY, TOL) != rg.PointContainment.Outside:
            n = (-n[0], -n[1])                          # 外向きにそろえる
        sc = n[0] * want[0] + n[1] * want[1]
        if sc > bs:
            best, bs = (a, b), sc
    return best


def gh_main():
    R_in, SM_in, SW_in = _in('R'), _in('SlopeMain'), _in('SlopeWest')
    Site, Setback = _in('Site'), _in('Setback')
    r_m = _num(R_in, (MAIN['R'] + MAIN['D']) / 1000.0)
    MAIN['R'] = r_m * 1000.0 - MAIN['D']               # 内部では東の柱列の半径を使う
    nm = _num(SM_in, MAIN['SLOPE_N'])
    nw = _num(SW_in, WEST['SLOPE_N'])
    apply_heights(nm, nw)                               # 低い側を固定し、高い側は勾配で決まる
    MainSE, MainNE, WestHandle = _in('MainSE'), _in('MainNE'), _in('WestHandle')
    MainSW, MainNW = _in('MainSW'), _in('MainNW')       # 古い入力名（西の角）にも対応
    if MainSE is not None and MainNE is not None:
        p0, u = handle_from_points(MainSE, MainNE)
        set_placement_sw(p0, u, MAIN['R'] + east_edge_u())
    elif MainSW is not None and MainNW is not None:
        p0, u = handle_from_points(MainSW, MainNW)
        set_placement_sw(p0, u)
    else:
        p0, ang = MAIN_HANDLE_DEFAULT
        set_placement_sw(p0, (math.cos(math.radians(ang)), math.sin(math.radians(ang))), MAIN['R'] + east_edge_u())
    if WestHandle is not None:
        west_from_handle(WestHandle)

    del DIAG[:]
    c, b, f, g, gr, feet = gh_build()
    outside, near, lines, ok, soft = [], [], [], True, False
    warn_extra = []
    ne = neighbor_edge(Site)
    for name, crv, pts in feet:
        n_site = n_ne = n_set = 0
        run = []
        for p in pts + [pts[0]]:
            q = rg.Point3d(p[0], p[1], 0)
            bad_set = False
            if Site is not None and Site.Contains(q, rg.Plane.WorldXY, TOL) == rg.PointContainment.Outside:
                n_site += 1; outside.append(q)
            elif Setback is not None and Setback.Contains(q, rg.Plane.WorldXY, TOL) == rg.PointContainment.Outside:
                if ne is not None and seg_dist((p[0], p[1]), ne) < NEIGHBOR_CLEAR:
                    n_ne += 1; outside.append(q)          # 隣家側（北東）は 1m でもエラー
                else:
                    n_set += 1; bad_set = True
            if bad_set:
                run.append(q)
            elif run:
                near.append(rg.PolylineCurve(NL(rg.Point3d, run)) if len(run) > 1 else rg.Circle(run[0], 300.0).ToNurbsCurve())
                run = []
        if run:
            near.append(rg.PolylineCurve(NL(rg.Point3d, run)) if len(run) > 1 else rg.Circle(run[0], 300.0).ToNurbsCurve())
        lab = {'main': '本館', 'west': '西館'}[name]
        if n_site:
            ok = False; lines.append('%s：敷地境界の外に %d 点' % (lab, n_site))
        if n_ne:
            ok = False; lines.append('%s：隣家側（北東）の 1m 余裕線の外に %d 点' % (lab, n_ne))
        if n_set:
            soft = True; lines.append('%s：1m 余裕線の外に %d 点（注意。NearEdge に線で表示）' % (lab, n_set))
    lab_s = lambda n: ('1/%g' % n) if n > 0 else '水平'
    rs = MAIN['R'] + MAIN['D']
    lines.append('本館 背骨（西の柱列）%.1f m・東の柱列 %.1f m（ピッチ 西 %.0f / 東 %.0f mm）、架構 %d 本、屋根 %s（東 %.2f m → 西 %.2f m）'
                 % (MAIN['SPANS'] * PITCH / 1000.0, MAIN['SPANS'] * PITCH * MAIN['R'] / rs / 1000.0,
                    PITCH, PITCH * MAIN['R'] / rs, MAIN['SPANS'] + 1, lab_s(nm), MAIN['TOP_E'] / 1000.0, MAIN['TOP_W'] / 1000.0))
    lines.append('西館 屋根 %s（東 %.2f m → 西 %.2f m）、ピッチ 東 %.0f / 西 %.0f mm'
                 % (lab_s(nw), WEST['TOP_E'] / 1000.0, WEST['TOP_W'] / 1000.0,
                    (rs + WEST['GAP']) * PITCH / rs, (rs + WEST['GAP'] + WEST['D']) * PITCH / rs))
    for Bd in buildings():
        lab = {'main': '本館', 'west': '西館'}[Bd['name']]
        hs = list(Bd['prof']['holes'])
        if 'floor2' in Bd:
            hs += Bd['floor2']['holes']
        lows = sorted(set(round(h[1] - GIRDER_H / 2.0) for h in hs))
        bad = [z for z in lows if z < MIN_CLEAR]
        if 'low' in Bd['prof']:
            lo = Bd['prof']['low']; so = Bd['prof']['soffit']
            lines.append('%s 梁の下端：東 %.2f m / 西 %.2f m、桁を包む楕円の下端：東 %.2f m / 西 %.2f m'
                         % (lab, so[0] / 1000.0, so[1] / 1000.0, lo[0] / 1000.0, lo[1] / 1000.0))
        if 'zbot' in Bd['prof']:
            zb = Bd['prof']['zbot']
            lines.append('%s 頭の最下点：東 %.2f m / 西 %.2f m' % (lab, zb(0.0) / 1000.0, zb(Bd['D']) / 1000.0))
        lines.append('%s 桁の下端：%s m%s' % (lab, ' / '.join('%.2f' % (z / 1000.0) for z in lows),
                                          ('  ← %.1f m 未満あり' % (MIN_CLEAR / 1000.0)) if bad else ''))
        if bad:
            ok = False
            warn_extra.append('%s：桁の下端が低い（%.2f m）' % (lab, min(bad) / 1000.0))
    lines.append('出力：柱 %d・梁 %d・2 階床梁 %d・桁 %d（立体の数）' % (len(c), len(b), len(f), len(g)))
    for d in sorted(set(DIAG)):
        lines.append('注意：%s ×%d' % (d, DIAG.count(d)))
    lines.append('西館：本館の北端から %d スパン南（%.1f m）、本館との柱列の間隔 GAP %.0f mm（最小 %.0f mm）%s'
                 % (WEST['START'], WEST['START'] * PITCH / 1000.0, WEST['GAP'], gap_min(),
                    '  ← WestHandle が近すぎるので最小に合わせた' if WEST.get('GAP_CLAMPED') else ''))
    bm, bw = buildings()
    ue = east_edge_u()
    zh = HANDLE_Z                                       # 屋根より上に置き、上から見て梁に隠れないようにする（高さは計算に使わない）
    snapped = [rg.Point3d(*world(bm, bm['thetas'][-1], ue, zh)), rg.Point3d(*world(bm, bm['thetas'][0], ue, zh)),
               rg.Point3d(*world(bw, bw['thetas'][0], bw['D'], zh))]
    if MainSE is not None and MainNE is not None and WestHandle is not None:
        snapped = []                                    # つかむ点がそろったら表示しない（空中の ✖ を消す）
    globals()['Snapped'] = snapped
    try:
        import Grasshopper
        comp = _in('ghenv').Component
        if not ok:
            comp.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Warning,
                                   ' / '.join([l for l in lines if '点' in l and '注意' not in l] + warn_extra))
        elif soft:
            comp.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Remark,
                                   ' / '.join([l for l in lines if '注意' in l and '点' in l]))
    except Exception:
        pass
    globals()['NearEdge'] = near
    return c, b, f, g, gr, [x[1] for x in feet], outside, ok, '\n'.join(lines)


try:
    Columns, Beams, Floor2, Girders, Grid, Footprint, Outside, OK, Report = gh_main()
except Exception:
    import traceback
    Columns = Beams = Floor2 = Girders = Grid = Footprint = Outside = None
    OK = False
    Report = 'エラー:\n' + traceback.format_exc()
    try:
        import Grasshopper
        _in('ghenv').Component.AddRuntimeMessage(Grasshopper.Kernel.GH_RuntimeMessageLevel.Error,
                                                  traceback.format_exc().strip().split('\n')[-1])
    except Exception:
        pass
