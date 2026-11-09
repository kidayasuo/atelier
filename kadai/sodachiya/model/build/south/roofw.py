"""西館の屋根の面（梁の上端、西館係）。add_west_south.py・fix_details.py・clip_parts.py・clean_wire.py（Rhino版）が使う。
棟（東の縁 v −0.9）8.15、外周の軒 4.65 で水平。軒の線は南北の妻に接する角（南西・北）だけ丸めない外形（v_eave）。
10-28 夕（ユーザー）：u21〜51 すべて双一次の面（屋根の線＝架構の線 u21〜42・登り梁 u43.5・u45・48・51 の、同じ高さの点を水平のまっすぐな線で結ぶ）。
返す物：roof_f(x, y)：屋根の面の高さ。BAYS・beam_line・ruled_point・ruled_hs：ベイ（光の筋の縁でも分ける）ごとの四隅の双一次。
SPANS：屋根の線のあいだごとの面の種類（すべて 'ruled'。南のけらばの接平面だけ 'plane'、clip_parts のため）。roof_line(u)：放射の線 u の上の
屋根の面の線（棟・軒の xyz）。roof_ruled：面の定義（屋根の線のあいだごと）。roof_old(x, y)：前の面（丸めた外形）。"""
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
    # 10-28 夕（ユーザー：スパン8〜14 を双一次に戻す、監修の項 20261028-1310）：西館の屋根の面はすべて（u21〜51）、屋根の線（架構の線 u21・24 … 42、
    #   北西の登り梁 u43.5、架構の線 u45・48・51。どれも棟 v −0.9 の 8150 から軒＝角を丸めない外形 v_eave の 4650 へのまっすぐな線）の同じ高さの点を
    #   水平のまっすぐな線（母屋）で結んだ面（双一次）。スパンごとの平面（f612dde〜b7eacae）は架構の線で段ができ（棟の端で最大 9.3 cm）、
    #   光の筋をはさむ 2 枚の梁の上端がそろわなかった。双一次なら段が無く、2 枚は同じ形（合板 1 枚のねじれは 2.4 mm 以下、棟も軒も水平）。
    #   南のけらば（u < 21）はスパン8の面をそのまま延ばす（u21 で段なし）。
    FR = [21.0 + 3.0 * k for k in range(8)]          # 21, 24, …, 42（架構の線）
    HS = 0.09                                         # 光の筋の半分の幅（u、m）
    _RB = FR + [43.5, 45.0, 48.0, 51.0]               # 屋根の線（面を決める線）
    _I42o = _RB.index(42.0)
    def _beam_old(u):
        """屋根の線 u：棟の点（v −0.9、8.15）と軒の点（角を丸めない外形、4.65）の平面の座標（mm）。面はこの線の上を棟から軒へまっすぐ下る"""
        return np.array(xy(u, VRIDGE), float).ravel(), np.array(xy(u, v_eave(u)), float).ravel()
    _BL = {u_: _beam_old(u_) for u_ in _RB}
    def _ruled_hs_old(x, y, kmin=0):
        """点 (x, y) の (h, s, 屋根の線のあいだの番号)：h＝棟 0 → 軒 1、s＝南の線 0 → 北の線 1（外へは延ばす）"""
        u, v = uv(x, y)
        k = int(np.clip(np.searchsorted(_RB, u) - 1, kmin, len(_RB) - 2))
        (Ra, Ea), (Rb, Eb) = _BL[_RB[k]], _BL[_RB[k + 1]]
        p = np.array([x, y], float); h = 0.5; s_ = float(np.clip((u - _RB[k]) / (_RB[k + 1] - _RB[k]), 0, 1))
        for _ in range(40):
            A_ = Ra + h * (Ea - Ra); B_ = Rb + h * (Eb - Rb); P_ = A_ + s_ * (B_ - A_)
            J = np.c_[(1 - s_) * (Ea - Ra) + s_ * (Eb - Rb), B_ - A_]
            d = np.linalg.solve(J, p - P_); h += d[0]; s_ += d[1]
            if abs(d[0]) < 1e-12 and abs(d[1]) < 1e-12: break
        return h, s_, k
    def roof_ruled(x, y, kmin=0):
        """屋根の面の定義：となりの屋根の線（_RB）の同じ高さの点を水平の線で結ぶ双一次の面"""
        return ZRIDGE - (ZRIDGE - ZEAVE) * _ruled_hs_old(x, y, kmin)[0]
    _roof_def = roof_ruled
    # ベイ BAYS（ソリッド係の Rhino版が読む。並びは b7eacae と同じ）：21・光の筋の縁（f ± 0.09、f＝24〜42）・43.5・45・48・51。
    #   ベイの境の線は、その u の放射の線と、屋根の線のあいだの棟の水平の線（8150）・軒の水平の線（4650）との交点を結ぶ線（屋根の線の上では屋根の線そのもの）。
    #   どのベイも四隅の双一次（ruled_point）で、もとの定義（roof_ruled）との差は 0.1 mm 未満（bay_check）。
    BAYS = [FR[0]] + [f + d for f in FR[1:] for d in (-HS, HS)] + _RB[_I42o + 1:]
    I42 = len(FR) * 2 - 2                                  # 北西の角の最初のベイ（42.09〜43.5）の番号
    _OUT = lambda u: (np.array(xy(u, VRIDGE), float).ravel(), np.array(xy(u, VRIDGE - 1.0), float).ravel() - np.array(xy(u, VRIDGE), float).ravel())
    def _x_chord(u, A, B):
        P0, d = _OUT(u); M = np.array([d, A - B]).T; t = np.linalg.solve(M, A - P0); return P0 + d * t[0]
    def beam_line(u):
        """ベイの境の線 u：屋根の面の線の両端（棟の点 8150, 軒の点 4650）の平面の座標（mm）。その線の上で面はまっすぐ"""
        if u in _BL: return _BL[u]
        k = int(np.clip(np.searchsorted(_RB, u) - 1, 0, len(_RB) - 2)); (Ra, Ea), (Rb, Eb) = _BL[_RB[k]], _BL[_RB[k + 1]]
        return _x_chord(u, Ra, Rb), _x_chord(u, Ea, Eb)
    _BL3 = {}
    for u_ in BAYS:
        R_, E_ = beam_line(u_); _BL3[u_] = (np.r_[R_, ZRIDGE], np.r_[E_, ZEAVE])
    _BAY = []                                              # ('bil', None, 四隅 C00 C10 C01 C11)
    for k in range(len(BAYS) - 1):
        (Ra, Ea), (Rb, Eb) = _BL3[BAYS[k]], _BL3[BAYS[k + 1]]
        _BAY.append(('bil', None, np.array([Ra, Rb, Ea, Eb])))
    def _bay_of(u):
        return int(np.clip(np.searchsorted(BAYS, u) - 1, 0, len(BAYS) - 2))
    def _sh(C, x, y, s=0.5, h=0.5):
        q = np.array([x, y], float); C2 = C[:, :2]
        for _ in range(40):
            P_ = (1 - s) * (1 - h) * C2[0] + s * (1 - h) * C2[1] + (1 - s) * h * C2[2] + s * h * C2[3]
            J = np.c_[(1 - h) * (C2[1] - C2[0]) + h * (C2[3] - C2[2]), (1 - s) * (C2[2] - C2[0]) + s * (C2[3] - C2[1])]
            d = np.linalg.solve(J, q - P_); s += d[0]; h += d[1]
            if abs(d[0]) < 1e-12 and abs(d[1]) < 1e-12: break
        return s, h
    def ruled_point(k, h, s_):
        """ベイ k（BAYS の番号）の (h, s) の点（x, y, z）：h＝棟 0 → 軒 1（beam_line の両端）、s＝南の線 0 → 北の線 1"""
        C = _BAY[k][2]; return (1 - s_) * (1 - h) * C[0] + s_ * (1 - h) * C[1] + (1 - s_) * h * C[2] + s_ * h * C[3]
    def ruled_hs(x, y, kmin=0):
        """点 (x, y) の (h, s, ベイの番号)（ベイの外へは延ばす）"""
        u = uv(x, y)[0]; k = max(kmin, _bay_of(u)); s, h = _sh(_BAY[k][2], x, y); return h, s, k
    def roof_f(x, y):
        """西館の屋根の面（梁の上端）の高さ（mm）：ベイごとの四隅の双一次（高さは h だけで決まる）"""
        k = _bay_of(uv(x, y)[0]); s, h = _sh(_BAY[k][2], x, y)
        return float(ZRIDGE - (ZRIDGE - ZEAVE) * h)
    roof_planes = roof_f
    def bay_check(n=9):
        """(四隅の roof_f との差 最大, 0, 平面のベイの数 0, ベイの境の線のまっすぐさ 最大, もとの定義 roof_ruled との差 最大)（mm）"""
        dc = dl = dd = 0.0
        for k, (kind, j, C) in enumerate(_BAY):
            for c_ in C: dc = max(dc, abs(roof_ruled(c_[0], c_[1]) - c_[2]), abs(roof_f(c_[0], c_[1]) - c_[2]))
            for h in np.linspace(0, 1, n):
                for s_ in np.linspace(0, 1, n):
                    q = ruled_point(k, h, s_); dd = max(dd, abs(roof_ruled(q[0], q[1]) - q[2]), abs(roof_f(q[0], q[1]) - q[2]))
        for u_ in BAYS:
            R3, E3 = _BL3[u_]
            for t in np.linspace(0, 1, 2 * n + 1):
                q = R3 + t * (E3 - R3); dl = max(dl, abs(roof_f(q[0], q[1]) - q[2]))
        return dc, 0.0, 0, dl, dd
    def roof_line(u, side=None):
        """放射の線 u の上の屋根の面の線：(棟の点 xyz, 軒の点 xyz)（mm）。side は前の作り方の名残（双一次では段が無いので同じ）"""
        R2, E2 = np.array(xy(u, VRIDGE), float).ravel(), np.array(xy(u, v_eave(u)), float).ravel()
        return np.r_[R2, roof_f(*R2)], np.r_[E2, roof_f(*E2)]
    # スパンごとの面の種類（clip_parts・fix_details が読む）：(u0, u1, 'ruled', None)＝beam_line(u0)・beam_line(u1) の同じ高さの点を水平の線で結ぶ双一次の面。
    # 平面のスパンは無い。ただし南のけらば（u < 21）だけ、スパン8の面の u21 の線での接平面を 'plane' として置く（clip_parts が平面の並びを一つ以上読むため。
    # roof_f はけらばでもスパン8の双一次を延ばしたもの。けらばの出の中での接平面との差は gable_dev）
    _R21, _E21 = _BL[FR[0]]
    _hm = 0.5; _A = ruled_point(0, _hm, 0.0); _B_ = ruled_point(0, _hm, 1.0)
    _n = np.cross(_BL3[FR[0]][1] - _BL3[FR[0]][0], _B_ - _A); _n = _n if _n[2] > 0 else -_n
    _GP = (float(_R21[0]), float(_R21[1]), ZRIDGE, float(-_n[0] / _n[2]), float(-_n[1] / _n[2]))
    SPANS = [(FR[0] - 1.0, FR[0], 'plane', _GP)] + [(a_, b_, 'ruled', None) for a_, b_ in zip(_RB, _RB[1:])]
    STRIPS = [(f - HS, f + HS) for f in FR[1:]]         # 光の筋（2 枚の梁のあいだ）。面は筋の中も同じ双一次
    def gable_dev(n=11):
        """南のけらば（u20〜21）で、roof_f と SPANS の接平面との差 最大（mm）"""
        px, py, c0, c1, c2 = _GP; dm = 0.0
        for uu in np.linspace(20.0, 21.0, n):
            for vv in np.linspace(VRIDGE, v_eave(21.0) - 1.0, n):
                q = np.array(xy(uu, vv), float).ravel(); dm = max(dm, abs(roof_f(*q) - (c0 + c1 * (q[0] - px) + c2 * (q[1] - py))))
        return dm
    def _plane_dev():
        return []
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
    return dict(roof_f=roof_f, roof_c=roof_c, BAYS=BAYS, beam_line=beam_line, roof_line=roof_line, SPANS=SPANS, STRIPS=STRIPS, HS=HS, I42=I42, roof_ruled=roof_ruled, ruled_hs=ruled_hs, ruled_point=ruled_point, KINKS=[b_ for b_ in BAYS[I42 + 1:-1]], roof_planes=roof_planes, bay_check=bay_check, roof_def=_roof_def, plane_dev=_plane_dev, gable_dev=gable_dev, FRAMES=FR, roof_old=roof_old, v_out=_v_out, corners=_corners, PSHARP=PSHARP, VRIDGE=VRIDGE)
