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
        pts = [x_] if x_.geom_type == 'Point' else list(getattr(x_, 'geoms', []))
        return min(uv(q.x, q.y)[1] for q in pts)
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
            for vv in (VRIDGE, v_eave(uu)):
                p = np.array(xy(uu, vv), float).ravel(); A_.append([1.0, p[0] - Pa[0], p[1] - Pa[1]]); B_.append(roof_c(*p))
        cf = np.linalg.lstsq(np.array(A_), np.array(B_), rcond=None)[0]
        planes.append((ua, ub, Pa, cf))
    def _pz(k, x, y):
        ua, ub, Pa, cf = planes[k]; return float(cf[0] + cf[1] * (x - Pa[0]) + cf[2] * (y - Pa[1]))
    def _side(k, x, y):                       # k：スパンの番号（0〜6 が平面、7 は曲面）
        return _pz(k, x, y) if 0 <= k < len(planes) else roof_c(x, y)
    def roof_f(x, y):
        u, v = uv(x, y)
        if u >= FR[-1] + HS: return roof_c(x, y)
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
    return dict(roof_f=roof_f, roof_c=roof_c, plane_dev=_plane_dev, FRAMES=FR, roof_old=roof_old, v_out=_v_out, corners=_corners, PSHARP=PSHARP, VRIDGE=VRIDGE)
