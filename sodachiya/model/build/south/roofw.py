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
    return dict(roof_f=roof_f, roof_old=roof_old, v_out=_v_out, corners=_corners, PSHARP=PSHARP, VRIDGE=VRIDGE)
