"""西館の屋根の面（西館係、10-24午後）。add_west_south.py と fix_details.py が使う。
棟（東の縁 v −0.9）8.15、外周の軒 4.65 で水平、架構の向き（u 一定の放射の線）にまっすぐ下る。
軒の線は、南北の妻に接する角（南西・北）だけ丸めない外形で決める（前は丸めた外形で、妻に接する所で面がねじれた）。
roof_f(x, y)：新しい面、roof_old(x, y)：前の面（丸めた外形）。"""
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
    # スパン8〜14（u21〜42）はスパンごとの平面（10-25、ユーザー・ソリッド係）。棟（東の縁）は弧、軒（西の面）はまっすぐなので、
    # 両方を水平のまま一枚の平面には載らない。平面は棟の線と軒の線の上の点に最小二乗で合わせ、ずれを両方に分ける（plane_dev で測る）。
    # 架構の線（u24〜42）では隣の平面とのあいだに小さな段ができるので、光の筋（2 枚の梁のあいだ ±0.09）の中で一次で移る（筋の立ち上がりとガラスで隠れる）。スパン15〜17 は曲面のまま。
    FR = [21.0 + 3.0 * k for k in range(8)]          # 21, 24, …, 42
    HS = 0.09
    planes = []
    for ua, ub in zip(FR, FR[1:]):
        Pa = np.array(xy(ua, VRIDGE), float).ravel()
        # 平面 z = c0 + c1·x + c2·y を、棟の線と軒の線の上の点で最小二乗（両方の線の高さのずれを半分ずつにする）
        A_, B_ = [], []
        for uu in np.linspace(ua + HS, ub - HS, 25):
            for vv, w_ in ((VRIDGE, 1.0), (v_eave(uu), 30.0)):          # 10-27夜：軒を水平に（ユーザー：軒の高さは一定に）。ずれは棟の側へ
                p = np.array(xy(uu, vv), float).ravel(); A_.append([w_, w_ * (p[0] - Pa[0]), w_ * (p[1] - Pa[1])]); B_.append(w_ * roof_c(*p))
        cf = np.linalg.lstsq(np.array(A_), np.array(B_), rcond=None)[0]
        planes.append((ua, ub, Pa, cf))
    def _pz(k, x, y):
        ua, ub, Pa, cf = planes[k]; return float(cf[0] + cf[1] * (x - Pa[0]) + cf[2] * (y - Pa[1]))
    # スパン15〜17（u42〜51、北西の角）は母屋がまっすぐ載る面（10-27夜、ユーザー：実際に作る時もまっすぐの材と板で近似する）。
    # 架構の線（と u43.5 の登り梁）の屋根の線は棟（v −0.9、8.15）から軒（角を丸めない外形、4.65）へのまっすぐな線。となりの二本の線の
    # 同じ高さの点を水平のまっすぐな線（母屋）で結んだ面にする。スパン16・17 は前の面と 1 mm 以内で同じ、スパン15 は軒がスパンの中で
    # 曲がるので u43.5 に登り梁を一本足して二つに分けた（前の面との差は最大約 3 cm）。軒先も同じ線の上で水平になる。
    BAYS = [21.0 + 3.0 * k for k in range(8)] + [43.5, 45.0, 48.0, 51.0]   # 10-27夜：西の面（スパン8〜14）も同じ作り方（平面のときは棟が±5 cm 狂い、架構の線で段）
    def beam_line(u):
        """屋根の線 u：棟の点と軒の点（平面、mm）"""
        return np.array(xy(u, VRIDGE), float).ravel(), np.array(xy(u, v_eave(u)), float).ravel()
    _BL = {u_: beam_line(u_) for u_ in BAYS}
    def ruled_hs(x, y):
        """点 (x, y) の (h, s, ベイの番号)：h＝棟 0 → 軒 1、s＝ベイの南の線 0 → 北の線 1（ベイの外へは延ばす）"""
        u, v = uv(x, y)
        k = int(np.clip(np.searchsorted(BAYS, u) - 1, 0, len(BAYS) - 2))
        (Ra, Ea), (Rb, Eb) = _BL[BAYS[k]], _BL[BAYS[k + 1]]
        p = np.array([x, y], float); h = 0.5; s_ = float(np.clip((u - BAYS[k]) / (BAYS[k + 1] - BAYS[k]), 0, 1))
        for _ in range(40):
            A_ = Ra + h * (Ea - Ra); B_ = Rb + h * (Eb - Rb); P_ = A_ + s_ * (B_ - A_)
            J = np.c_[(1 - s_) * (Ea - Ra) + s_ * (Eb - Rb), B_ - A_]
            d = np.linalg.solve(J, p - P_); h += d[0]; s_ += d[1]
            if abs(d[0]) < 1e-12 and abs(d[1]) < 1e-12: break
        return h, s_, k
    def roof_ruled(x, y):
        return ZRIDGE - (ZRIDGE - ZEAVE) * ruled_hs(x, y)[0]
    def ruled_point(k, h, s_):
        """ベイ k の (h, s) の点（x, y, z）"""
        (Ra, Ea), (Rb, Eb) = _BL[BAYS[k]], _BL[BAYS[k + 1]]
        A_ = Ra + h * (Ea - Ra); B_ = Rb + h * (Eb - Rb); P_ = A_ + s_ * (B_ - A_)
        return np.array([P_[0], P_[1], ZRIDGE - (ZRIDGE - ZEAVE) * h])
    def _side(k, x, y):                       # k：スパンの番号（0〜6 が平面、7 は北西の角）
        return _pz(k, x, y) if 0 <= k < len(planes) else roof_ruled(x, y)
    def roof_f(x, y):                          # 10-27夜：西館の屋根の面はすべて、屋根の線（梁）の同じ高さの点を水平のまっすぐな線（母屋）で結んだ面
        return roof_ruled(x, y)
    def roof_planes(x, y):                     # 前のスパンごとの平面（比べるため）
        u, v = uv(x, y)
        if u >= FR[-1] + HS: return roof_ruled(x, y)
        if u < FR[0]: return _pz(0, x, y)                                 # 南のけらば（u < 21）もスパン 8 の平面を延ばす（10-27夜、ソリッド係の項 20261027-2159：曲面に戻すと u21 で最大 2.8 cm の段）
        for j, f in enumerate(FR[1:], start=1):                          # 架構の線 u24〜42 の筋の中は一次で移る
            if abs(u - f) < HS:
                zl, zr = _side(j - 1, x, y), _side(j, x, y); w = (u - (f - HS)) / (2 * HS)
                return zl + (zr - zl) * w
        k = min(int((u - FR[0]) // 3.0), len(planes) - 1)
        return _pz(k, x, y)
    def _plane_dev():
        """スパンごとの平面と曲面の、軒の線でのいちばん大きい差（mm）"""
        out = []
        for k, (ua, ub, *_r) in enumerate(planes):
            de = dr = 0.0
            for uu in np.linspace(ua + HS, ub - HS, 9):
                p = np.array(xy(uu, v_eave(uu)), float).ravel(); de = max(de, abs(_pz(k, *p) - roof_c(*p)))
                p = np.array(xy(uu, VRIDGE), float).ravel(); dr = max(dr, abs(_pz(k, *p) - roof_c(*p)))
            out.append((8 + k, round(dr), round(de)))
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
    return dict(roof_f=roof_f, roof_c=roof_c, BAYS=BAYS, beam_line=beam_line, ruled_hs=ruled_hs, ruled_point=ruled_point, KINKS=[b_ for b_ in BAYS[1:-1]], roof_planes=roof_planes, plane_dev=_plane_dev, FRAMES=FR, roof_old=roof_old, v_out=_v_out, corners=_corners, PSHARP=PSHARP, VRIDGE=VRIDGE)
