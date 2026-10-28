"""西館の屋根の面（梁の上端、西館係）。add_west_south.py・fix_details.py・clean_wire.py（Rhino版）が使う。
棟（東の縁 v −0.9）8.15、外周の軒 4.65 で水平。軒の線は南北の妻に接する角（南西・北）だけ丸めない外形（v_eave）。
10-28：スパン8〜14（u21〜42）はスパンごとに一枚の平面（軒にちょうど載る、棟は最小二乗）、架構の線の光の筋（±0.09）の中で一次で移る。
北西の角（u42〜51）は双一次の面（beam_line の同じ高さの点を水平の線で結ぶ）。
返す物：roof_f(x, y)：屋根の面の高さ。SPANS：スパンごとの面の種類と平面の係数、STRIPS：一次で移る筋。roof_line(u, side)：放射の線 u の上の
屋根の面の線（棟・軒の xyz）。beam_line(u)：双一次の面を決める線（平面のスパンでは屋根の面の上に無い）。roof_ruled：双一次の面（比べるため）。
roof_old(x, y)：前の面（丸めた外形）。plane_dev()：スパンごとの棟・軒のずれと双一次の面との差。"""
import numpy as np
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
from uv import xy, uv
def make(WN):
    ZRIDGE, ZEAVE, VRIDGE = 8150.0, 4650.0, -0.9
    _c = np.array(WN.exterior.coords)
    _edges = [(a, b) for a, b in zip(_c, _c[1:]) if np.hypot(*(b - a)) > 1500 and min(uv(*a)[1], uv(*b)[1]) < -1.2]
    def _isect(a1, b1, a2, b2):
        d1 = b1 - a1; d2 = b2 - a2; M = np.array([d1, -d2]).T
        t = np.linalg.solve(M, a2 - a1); return a1 + d1 * t[0]
    _corners = []
    for i in range(len(_edges)):                       # 外周の順に隣り合う 2 辺（あいだに角の丸み）
        a1, b1 = _edges[i]; a2, b2 = _edges[(i + 1) % len(_edges)]
        gap = np.hypot(*(a2 - b1))
        if gap < 100 or gap > 12000: continue
        rake = lambda a, b: abs(uv(*a)[0] - uv(*b)[0]) < 0.05           # 南北の妻（放射の線に沿う辺）
        if not (rake(a1, b1) or rake(a2, b2)): continue                 # 軒どうしの角（西の面と北西の面）は丸みのまま（ねじれない）
        try: q = _isect(a1, b1, a2, b2)
        except np.linalg.LinAlgError: continue
        _corners.append(Polygon([tuple(b1), tuple(q), tuple(a2)]))
    PSHARP = unary_union([WN] + [t.buffer(0) for t in _corners if t.area > 1e4]).buffer(1).buffer(-1)
    def v_eave(u):
        """放射の線 u と角を丸めない外形の、いちばん西の交点の v"""
        uu = min(max(u, 21.0005), 50.9995)
        ln = LineString([xy(uu, VRIDGE + 0.5), xy(uu, -40.0)]); x_ = ln.intersection(PSHARP.exterior)
        pts = [c_ for g_ in getattr(x_, 'geoms', [x_]) for c_ in np.asarray(g_.coords)]   # 線が外形の辺に重なると LineString（10-27夜）
        return min(uv(*c_)[1] for c_ in pts)
    _ve_cache = {}
    def roof_f(x, y):
        u, v = uv(x, y); k = round(u, 3)
        if k not in _ve_cache: _ve_cache[k] = v_eave(u)
        vb = _ve_cache[k]
        return ZRIDGE - (ZRIDGE - ZEAVE) * max(0.0, VRIDGE - v) / max(1e-6, VRIDGE - vb)
    roof_c = roof_f
    # 10-28（ユーザー：屋根はそもそも平面で作る、軒の高さは守る、どうしてもうまくゆかない所だけ曲面。項 20261028-0841-solid）：
    #   スパン8〜14（u21〜42）はスパンごとに一枚の平面。平面はその所の軒の線（4.65、角を丸めない外形 v_eave）にちょうど載る（軒は水平）。
    #   棟（東の縁 v −0.9）は最小二乗（ずれ ±3〜5.5 cm）。架構の線（u24〜42）では、隣の平面（u42 では北西の角の面）とのあいだを
    #   光の筋（2 枚の梁のあいだ ±0.09）の中で一次で移る（筋の立ち上がりとガラスで隠れる）。南のけらば（u < 21）はスパン8の平面を延ばす。
    #   u39〜42 は軒が角の丸みの始まりで少し曲がるので、軒の点に当てはめたまっすぐな線を軒にする（ずれ 約1 cm）。
    #   北西の角（u42〜51、スパン15〜17）は平面にできない（軒が棟の向きから回っていくので、軒を水平に保つと棟が ±0.1〜0.7 m 狂う）ので、
    #   双一次の面のまま（となりの屋根の線の同じ高さの点を水平のまっすぐな線＝母屋で結ぶ、10-27夜）。u43.5 の登り梁もそのまま。
    FR = [21.0 + 3.0 * k for k in range(8)]          # 21, 24, …, 42（架構の線）
    HS = 0.09                                         # 光の筋の半分の幅（u、m）
    planes = []
    for ua, ub in zip(FR, FR[1:]):
        Pa = np.array(xy(ua, VRIDGE), float).ravel()
        us_ = np.linspace(ua + (HS if ua > FR[0] else 0.0), ub - HS, 31)
        E_ = np.array([np.array(xy(uu, v_eave(uu)), float).ravel() for uu in us_])
        R_ = np.array([np.array(xy(uu, VRIDGE), float).ravel() for uu in us_])
        # 平面は軒の線（平面の座標で最小二乗のまっすぐな線、高さ 4.65 で水平）を含み、勾配 g だけを棟の点（8.15）で最小二乗で決める。
        # 軒がまっすぐなスパンは軒にちょうど載る。u39〜42（角の丸みの始まり）は軒の点と線の差×勾配だけずれる（最大約 1 cm）
        c_ = E_.mean(0); d_ = np.linalg.svd(E_ - c_)[2][0]; n_ = np.array([-d_[1], d_[0]])
        if (R_.mean(0) - c_) @ n_ < 0: n_ = -n_
        t_ = (R_ - c_) @ n_; g_ = float((ZRIDGE - ZEAVE) * t_.sum() / (t_ @ t_))
        cf = np.array([ZEAVE + g_ * float(n_ @ (Pa - c_)), g_ * n_[0], g_ * n_[1]])   # z = c0 + c1·(x − Pa.x) + c2·(y − Pa.y)
        planes.append((ua, ub, Pa, cf))
    def _pz(k, x, y):
        ua, ub, Pa, cf = planes[k]; return float(cf[0] + cf[1] * (x - Pa[0]) + cf[2] * (y - Pa[1]))
    # 北西の角の双一次の面の屋根の線（架構の線 u42・45・48・51 と u43.5 の登り梁）
    BAYS = [21.0 + 3.0 * k for k in range(8)] + [43.5, 45.0, 48.0, 51.0]   # 屋根の線の u（21〜42 は架構の線＝平面のスパンの境、42〜51 は双一次のベイの境）
    I42 = BAYS.index(42.0)
    def beam_line(u):
        """双一次の面（北西の角、u42〜51）を決める屋根の線 u：棟の点（v −0.9、8.15）と軒の点（角を丸めない外形、4.65）の平面の座標（mm）。
        その面は、この線の上を棟から軒へまっすぐ下る。平面のスパン（u21〜42）では屋根の面はこの線の上に無い（棟が ±3〜5.5 cm ずれる）ので、
        屋根の面の線は roof_line(u, side) を使う"""
        return np.array(xy(u, VRIDGE), float).ravel(), np.array(xy(u, v_eave(u)), float).ravel()
    _BL = {u_: beam_line(u_) for u_ in BAYS}
    def ruled_hs(x, y, kmin=I42):
        """点 (x, y) の (h, s, ベイの番号)：h＝棟 0 → 軒 1、s＝ベイの南の線 0 → 北の線 1（ベイの外へは延ばす）。ベイは BAYS の番号（kmin 以上＝北西の角）"""
        u, v = uv(x, y)
        k = int(np.clip(np.searchsorted(BAYS, u) - 1, kmin, len(BAYS) - 2))
        (Ra, Ea), (Rb, Eb) = _BL[BAYS[k]], _BL[BAYS[k + 1]]
        p = np.array([x, y], float); h = 0.5; s_ = float(np.clip((u - BAYS[k]) / (BAYS[k + 1] - BAYS[k]), 0, 1))
        for _ in range(40):
            A_ = Ra + h * (Ea - Ra); B_ = Rb + h * (Eb - Rb); P_ = A_ + s_ * (B_ - A_)
            J = np.c_[(1 - s_) * (Ea - Ra) + s_ * (Eb - Rb), B_ - A_]
            d = np.linalg.solve(J, p - P_); h += d[0]; s_ += d[1]
            if abs(d[0]) < 1e-12 and abs(d[1]) < 1e-12: break
        return h, s_, k
    def roof_ruled(x, y, kmin=I42):
        return ZRIDGE - (ZRIDGE - ZEAVE) * ruled_hs(x, y, kmin)[0]
    def ruled_point(k, h, s_):
        """ベイ k（BAYS の番号）の (h, s) の点（x, y, z）"""
        (Ra, Ea), (Rb, Eb) = _BL[BAYS[k]], _BL[BAYS[k + 1]]
        A_ = Ra + h * (Ea - Ra); B_ = Rb + h * (Eb - Rb); P_ = A_ + s_ * (B_ - A_)
        return np.array([P_[0], P_[1], ZRIDGE - (ZRIDGE - ZEAVE) * h])
    def _side(k, x, y):                       # k：平面のスパンの番号（0〜6＝スパン8〜14）、7 は北西の角の双一次の面
        return _pz(k, x, y) if 0 <= k < len(planes) else roof_ruled(x, y)
    def roof_f(x, y):
        """西館の屋根の面（梁の上端）の高さ（mm）。u21〜42 はスパンごとの平面（架構の線の光の筋の中は一次で移る）、u42〜51 は双一次の面"""
        u, v = uv(x, y)
        if u >= FR[-1] + HS: return roof_ruled(x, y)
        if u < FR[0]: return _pz(0, x, y)                                 # 南のけらばはスパン8の平面を延ばす
        for j, f in enumerate(FR[1:], start=1):                          # 架構の線 u24〜42 の筋の中は一次で移る
            if abs(u - f) < HS:
                zl, zr = _side(j - 1, x, y), _side(j, x, y); w = (u - (f - HS)) / (2 * HS)
                return zl + (zr - zl) * w
        return _pz(min(int((u - FR[0]) // 3.0), len(planes) - 1), x, y)
    roof_planes = roof_f
    def roof_line(u, side=None):
        """放射の線 u の上の屋根の面の線：(棟の点 xyz, 軒の点 xyz)（mm）。屋根の面は放射の線の上でまっすぐ（平面・筋の中の一次の移り・
        双一次の面の屋根の線の上）なので、二点で決まる。side='S'／'N'：架構の線 u24〜42 では、南／北のスパンの面を架構の線まで延ばした線
        （2 枚の梁の上端・出し梁はそれぞれの側の面に載る。筋の縁 u ∓ 0.09 では roof_line(u ∓ 0.09) と同じ面）。side なし：roof_f の線"""
        R2, E2 = np.array(xy(u, VRIDGE), float).ravel(), np.array(xy(u, v_eave(u)), float).ravel()
        if side is None or not (FR[0] < u <= FR[-1] + 1e-9):
            f_ = roof_f
        else:
            j = int(round((u - FR[0]) / 3.0)); k = j - 1 if side == 'S' else j
            f_ = lambda x, y, k=k: _side(k, x, y)
        return np.r_[R2, f_(*R2)], np.r_[E2, f_(*E2)]
    # スパンごとの面の種類（ソリッド係の Rhino版が読む）：(u0, u1, 'plane', (Pa.x, Pa.y, c0, c1, c2))＝z = c0 + c1·(x − Pa.x) + c2·(y − Pa.y)、
    # (u0, u1, 'ruled', None)＝beam_line(u0)・beam_line(u1) の同じ高さの点を水平の線で結ぶ双一次の面。境（u24〜42）の筋 STRIPS は一次の移り
    SPANS = [(ua, ub, 'plane', (float(Pa[0]), float(Pa[1]), *map(float, cf))) for ua, ub, Pa, cf in planes] + \
            [(a_, b_, 'ruled', None) for a_, b_ in zip(BAYS[I42:], BAYS[I42 + 1:])]
    STRIPS = [(f - HS, f + HS) for f in FR[1:]]
    def _plane_dev():
        """スパンごとの（番号, 棟のずれ 最大, 軒のずれ 最大, 双一次の面との差 最大）（mm）"""
        out = []
        for k, (ua, ub, *_r) in enumerate(planes):
            de = dr = dd = 0.0
            for uu in np.linspace(ua + (HS if k else 0.0), ub - HS, 31):
                pe = np.array(xy(uu, v_eave(uu)), float).ravel(); de = max(de, abs(_pz(k, *pe) - ZEAVE))
                pr = np.array(xy(uu, VRIDGE), float).ravel(); dr = max(dr, abs(_pz(k, *pr) - ZRIDGE))
                for t in np.linspace(0, 1, 9):
                    q = pr + t * (pe - pr); dd = max(dd, abs(_pz(k, *q) - roof_ruled(*q, kmin=0)))
            out.append((8 + k, round(dr), round(de, 1), round(dd)))
        return out
    def _v_out(u):
        ln = LineString([xy(u, VRIDGE + 0.5), xy(u, -40.0)]); x_ = ln.intersection(WN.exterior)
        pts = [x_] if x_.geom_type == 'Point' else list(getattr(x_, 'geoms', []))
        vs = [uv(q.x, q.y)[1] for q in pts]
        return (max(vs), min(vs)) if vs else (VRIDGE, VRIDGE)
    _vo = {}
    def roof_old(x, y):
        u, v = uv(x, y); k = round(min(max(u, 21.0005), 50.9995), 3)
        if k not in _vo: _vo[k] = _v_out(k)[1]
        return ZRIDGE - (ZRIDGE - ZEAVE) * max(0.0, VRIDGE - v) / max(1e-6, VRIDGE - _vo[k])
    return dict(roof_f=roof_f, roof_c=roof_c, BAYS=BAYS, beam_line=beam_line, roof_line=roof_line, SPANS=SPANS, STRIPS=STRIPS, HS=HS, I42=I42, roof_ruled=roof_ruled, ruled_hs=ruled_hs, ruled_point=ruled_point, KINKS=[b_ for b_ in BAYS[I42 + 1:-1]], roof_planes=roof_planes, plane_dev=_plane_dev, FRAMES=FR, roof_old=roof_old, v_out=_v_out, corners=_corners, PSHARP=PSHARP, VRIDGE=VRIDGE)
