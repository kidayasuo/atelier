"""周辺の道路と建物（PLATEAU、data/context_plateau.json）を 3dm に
使い方: python3 add_context.py IN.3dm OUT.3dm data/context_plateau.json
- 03_周辺_道路（PLATEAU）：道路 LOD1 の面を一枚にまとめ、平らに（敷地の GL −300 の 20 下、10-25 ユーザー）。厚さ 100 の押し出し（穴あり）。西の道・北の道の建物の側の縁は敷地の境にそろえる。
- 03g_周辺_地面（平ら）：PLATEAU の範囲全体（入れた道路・建物の凸包を5 m広げた範囲）から敷地と高野川（02の平面）を抜いた一枚。上面−340（道路の20下、道路の下にも続く）・厚さ100（10-30）。
- 04_周辺_建物（PLATEAU LOD1）：建物の外形を下端から上端まで押し出した箱（LOD1 なので屋根の形は無い）。
- 敷地の中の今の住宅と、敷地の中を通る今の道は入れない（課題はそれを取り払った計画）。
- 出典：国土交通省 Project PLATEAU（京都市 2025 年度）。
"""
import sys, json, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/south')
from shapely.geometry import Polygon, LineString
from shapely import constrained_delaunay_triangles
from meshkit import Kit

IN, OUT, CJ = sys.argv[1:4]
J = json.load(open(CJ, encoding='utf-8'))
m = r.File3dm.Read(IN)
def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)
L_RD = layer('03_周辺_道路（PLATEAU）', (175, 175, 170))
L_BL = layer('04_周辺_建物（PLATEAU LOD1）', (205, 200, 190))
K = Kit(m)

# 敷地（00 の大きい方、mm）
site = None
for o in m.Objects:
    if m.Layers[o.Attributes.LayerIndex].Name.startswith('00_') and isinstance(o.Geometry, r.PolylineCurve):
        g = o.Geometry; P = np.array([[g.Point(i).X, g.Point(i).Y] for i in range(g.PointCount)])
        if site is None or Polygon(P).area > Polygon(site).area: site = P
S = Polygon(site)

# 地盤の高さ：建物の下端（mm）を点として内挿
GP = np.array([[*Polygon(np.array(b['foot']) * 1000).centroid.coords[0], b['z0']] for b in J['bldg']])
def ground(x, y):
    d = np.hypot(GP[:, 0] - x, GP[:, 1] - y) + 1000.0
    w = 1.0 / d ** 2; i = np.argsort(d)[:8]
    return float((GP[i, 2] * w[i]).sum() / w[i].sum())

# 西の道の向かいの住宅3軒（北の三軒）を、塊の南の角を中心に回して、課題の敷地図の道の縁に沿わせる（ユーザー、10-26）。
# PLATEAU では道の縁に対して約12.6°開いていた。課題の敷地図（present/kadai_map.json の西の道の西の縁）の向きに合わせる
from shapely import affinity as _aff
ROT_BLOCK = {'ids': ('bldg_15ae39bf-872c-42a8-889f-3138a573794e', 'bldg_d62c7741-c440-4c87-ab0c-1fd708e067e3',
                     'bldg_cb1d1a2b-6ef5-4bb0-890a-fffa0ca64a4f'),
             'pivot': (-32517.4, -46079.2), 'deg': -12.65}   # 10-26 周辺を(-1.369, 1.722) m動かした分も
nb = nr = skip_b = skip_r = 0
HB = []                             # 回した三軒の外形（道の西の縁を合わせる、下）
PL = []                             # 入れた建物の外形（周辺の地面03gの範囲、下）
for b in J['bldg']:
    F = Polygon(np.array(b['foot']) * 1000).buffer(0)
    if b.get('id') in ROT_BLOCK['ids']: F = _aff.rotate(F, ROT_BLOCK['deg'], origin=ROT_BLOCK['pivot']); HB.append(F)
    if F.is_empty or F.area < 2e6: continue
    if F.intersection(S).area > 0.5e6: skip_b += 1; continue          # 敷地にかかる建物は入れない（今の住宅、北で敷地に入る隣家も、ユーザー10-26）
    if b['z1'] - b['z0'] < 500: continue
    K.prism(F, float(b['z0']), float(b['z1']), L_BL); nb += 1; PL.append(F)
# 道路（10-25、ユーザー）：平らな一枚に（道の少々の起伏は無視する。平面図に道路の片の継ぎ目や斜めの三角形の筋が入らないように）。
# 敷地に接する西の道・北の道は、建物の側の縁だけを敷地の境にそろえる（道が敷地にかかる所は削り、敷地とのすき間は道で埋める。
# 道の向こう側の縁は PLATEAU のまま）。元々道路と敷地が正確ではない（ユーザー）。
from shapely.geometry import LineString
from shapely.ops import unary_union
Z_RD = -320.0                       # 舗装の面：敷地の GL（−300）の 20 下
# 敷地の西の辺・北の辺（敷地の外形のうち、道に接する辺：00 の外形の頂点の並びから、道に 3 m 以内の辺）
ring = list(S.exterior.coords)
EDG = [LineString([ring[k], ring[k + 1]]) for k in range(len(ring) - 1)]
def _out(e):        # 辺の外向きの向き
    (x0, y0), (x1, y1) = e.coords; d = np.array([x1 - x0, y1 - y0]) / e.length; n = np.array([d[1], -d[0]])
    c = np.array(e.centroid.coords[0])
    return n if not S.contains(Polygon([c, c + n * 10 + d, c + n * 10 - d]).centroid) else -n
# 西の道（外向きが西）と北の道（外向きが北西＝川と直角）の辺だけ。川・公園・北東の隣家の辺は触らない
EDG = [e for e in EDG if e.length > 5000 and (_out(e) @ np.array([-1.0, 0.0]) > 0.9 or _out(e) @ np.array([-0.6225, 0.7826]) > 0.95)]
from shapely.ops import linemerge
ED = linemerge(unary_union(EDG))       # 一本の線に（角で帯が途切れて三角のすき間が残らないように）
# 北東の辺（外向きが北東、隣家の側）：辺の中ほどに接する道の片（今の住宅のあいだを通る、高野川に並行な道の続き）は入れない。
# 北の道・東の角にかかる片（辺の両端から 8 m 以内で接する）は残す（10-26 夜、ユーザー、renkei 20261026-2040-present）
_ring = list(S.exterior.coords); NE = None
for k in range(len(_ring) - 1):
    e = LineString([_ring[k], _ring[k + 1]])
    if e.length > 5000 and _out(e) @ np.array([0.7826, 0.6225]) > 0.9: NE = e
from shapely.geometry import Point as _Pt
from shapely.ops import nearest_points as _np_
def _ne_mid(Q):
    if NE is None or Q.distance(NE) > 500: return False
    q = _np_(NE, Q)[0]
    s_ = NE.project(q)
    return 8000 < s_ < NE.length - 8000
skip_ne = 0
RQ = []
for rd in J['road']:
    Q = Polygon(np.array(rd['xy']) * 1000).buffer(0)
    if Q.is_empty: continue
    if _ne_mid(Q): skip_ne += 1; continue
    QS = Q.intersection(S)
    # 敷地の中を通る今の道は入れない。ただし西の道・北の道の片が敷地にかかっているだけ（かかる所がおもに辺から 8 m 以内）なら入れる（かかる所は後で削る）
    if QS.area > 0.3 * Q.area and not QS.difference(ED.buffer(8000)).area < 0.25 * QS.area: skip_r += 1; continue
    RQ.append(Q)
RD = unary_union(RQ).buffer(50, join_style=2).buffer(-50, join_style=2)     # 片のあいだの細いすき間を閉じる
WB = 12000.0
band = S.buffer(WB, join_style=2).difference(S).intersection(ED.buffer(WB + 500, cap_style=2, join_style=2))
outer = S.buffer(WB, join_style=2).exterior
gaps = []
rest = band.difference(RD)
for g in getattr(rest, 'geoms', [rest]):
    if g.geom_type != 'Polygon' or g.area < 1e4: continue
    if g.distance(ED) < 50 and g.distance(outer) > 50:      # 敷地の辺と道のあいだに挟まれたすき間だけ（道の向こう側へ抜ける所は埋めない）
        gaps.append(g)
RD = unary_union([RD] + gaps).difference(S)
RD = RD.buffer(20, join_style=2).buffer(-20, join_style=2).difference(S)
# 西の道の向かい側（西）の縁を、お向かいの三軒（ROT_BLOCK で回した家）の道側の面の線に合わせる（10-28、ユーザー、項 20261028-1346-present）。
# 家は動かさず道を家に添わせる：三軒の前では道の西の縁を面の線で切り（道が家に食い込んでいた所）、面とのすき間は道で埋める。
# 前後は今の縁へ斜めになめらかにつなぐ。敷地の側の縁は今のまま。
_W = [e for e in EDG if _out(e) @ np.array([-1.0, 0.0]) > 0.9]
if len(HB) == 3 and _W:
    _e = max(_W, key=lambda e: e.length)
    _p = np.array(_e.coords)
    _A = _p[np.argmin(_p[:, 1])]                                  # 敷地の南西の角
    _d = _p[np.argmax(_p[:, 1])] - _A; _d /= np.linalg.norm(_d)   # 辺に沿って北へ
    _n = _out(_e)                                                 # 道の側（西）
    _st = lambda q: ((np.asarray(q) - _A) @ _d, (np.asarray(q) - _A) @ _n)
    _xy = lambda s_, t_: tuple(_A + _d * s_ + _n * t_)
    # 三軒の道側の面（外向きが敷地の方を向く辺）の端点に一本の線 t = a + b·s を当てる
    FP = []
    from shapely.geometry.polygon import orient as _orient
    for F in HB:
        c = list(_orient(F, 1).exterior.coords)                   # 左回り：辺の右が外
        for k in range(len(c) - 1):
            v = np.subtract(c[k + 1], c[k]); L_ = np.hypot(*v)
            if L_ > 1000 and np.array([v[1], -v[0]]) / L_ @ -_n > 0.9: FP += [_st(c[k]), _st(c[k + 1])]
    FP = np.array(FP)
    _b, _a = np.polyfit(FP[:, 0], FP[:, 1], 1)
    _ln = lambda s_: _a + _b * s_
    s0, s1 = FP[:, 0].min(), FP[:, 0].max()                       # 面の線の南端・北端（約 28.3〜48.4 m）
    _dep = min(_st(q)[1] - _ln(_st(q)[0]) for F in HB for q in F.exterior.coords if _st(q)[1] - _ln(_st(q)[0]) > 2000)   # 家の奥の面で一番浅い所（切るのはその 9 割まで）
    def _edge(s_):          # 今の道の西の縁（敷地の辺から道の中を西へ続く所の端、辺からの距離）
        x = LineString([_xy(s_, 100), _xy(s_, 30000)]).intersection(RD)
        for g in sorted(getattr(x, 'geoms', [x]), key=lambda g: min(_st(q)[1] for q in g.coords)):
            if not g.is_empty and min(_st(q)[1] for q in g.coords) < 300: return max(_st(q)[1] for q in g.coords)
        return 0.0
    LB = 8000.0             # 北のつなぎの長さ
    LBS = 500.0             # 南は斜めでなく、ほぼ直角に張り出す（10-29、ユーザー：実際にはほぼ直角。その突端に木、アプローチ係のexport3dm.py）
    tS, tN = _edge(s0 - LB), _edge(s1 + LB)
    cut = Polygon([_xy(s0, _ln(s0)), _xy(s1, _ln(s1)), _xy(s1, _ln(s1) + 0.9 * _dep), _xy(s0, _ln(s0) + 0.9 * _dep)])
    fill = [Polygon([_xy(s0, -500), _xy(s1, -500), _xy(s1, _ln(s1)), _xy(s0, _ln(s0))]),
            Polygon([_xy(s0 - LBS, -500), _xy(s0, -500), _xy(s0, _ln(s0)), _xy(s0 - LBS, tS)])]
    cutS = Polygon([_xy(s0 - LB, tS), _xy(s0 - LBS, tS), _xy(s0 - LBS, tS + 30000), _xy(s0 - LB, tS + 30000)])   # 南の張り出し：今の斜めの縁を削る
    if tN < _ln(s1): fill.append(Polygon([_xy(s1, -500), _xy(s1 + LB, -500), _xy(s1 + LB, tN), _xy(s1, _ln(s1))]))
    a0 = RD.intersection(unary_union(HB)).area
    RD0 = RD
    RD = unary_union([RD] + fill).difference(cut).difference(cutS).difference(unary_union(HB)).difference(S)
    print('road: 南の張り出しの突端 xy %.2f, %.2f m' % tuple(np.array(_xy(s0 - LBS, tS)) / 1000))
    print('road: 三軒の面の線 辺から %.2f〜%.2f m（s %.1f〜%.1f m）、家への食い込み %.1f→%.1f m2、埋めた %.1f m2、削った %.1f m2'
          % (_ln(s0) / 1000, _ln(s1) / 1000, s0 / 1000, s1 / 1000, a0 / 1e6, RD.intersection(unary_union(HB)).area / 1e6,
             RD.difference(RD0).area / 1e6, RD0.difference(RD).area / 1e6))
print('road: 北東の辺の中ほどの道', skip_ne, 'removed')
print('road: edges', len(EDG), 'gaps', len(gaps), round(sum(g.area for g in gaps) / 1e6, 1), 'm2')
# 道路は外形と穴の閉じた押し出し（厚さ 100、上面は Z_RD）。Rhino版（段10）で輪郭と穴の Extrusion 一つになる
# （10-27夜、監修の項 20261027-2346：前は平らな三角形の一枚で、Rhino版で 424 面・穴 42 の重いポリサーフェスになっていた）
T_RD = 100.0
for g in getattr(RD, 'geoms', [RD]):
    if g.geom_type != 'Polygon' or g.area < 1e5: continue
    g = g.simplify(20)
    # 穴が外形や別の穴に一点で触れる所があると、押し出しの輪郭にならない（頂点が二つ重なる）。3 mm 縮めて離す（図には出ない）
    g = g.buffer(-3, join_style=2)
    n0 = len(m.Objects)
    K.prism(g, Z_RD - T_RD, Z_RD, L_RD)
    for o in list(m.Objects)[n0:]: o.Attributes.Name = '道路（平ら）'
    nr += len(m.Objects) - n0
# 周辺の平らな地面（03g）：PLATEAU の範囲全体に一枚（10-30、ユーザーの項 20261029-2211-present：レイトレースの鳥瞰で、
# 道路と建物のあいだに地面が無く空が四角く抜けていた。前は敷地から30 mの帯だけ、10-29）。
# 範囲は入れた道路（03）・建物（04）の凸包を5 m広げた所。そこから敷地（00）と高野川（02：護岸・河川敷・水・川底の平面）を抜く。
# 上面は道路の20下（−340）なので、道路とは平面で重なってよい（道路の下に続き、継ぎ目のすき間が残らない）。建物（04）はその上に立つ
L_GR = layer('03g_周辺_地面（平ら、上面−340）', (165, 150, 125))
Z_GR = Z_RD - 20.0
def _plan(g):
    """メッシュの面を平面に写した多角形の和（add_site.py と同じ）"""
    if not isinstance(g, r.Mesh): return None
    V = np.array([[p.X, p.Y] for p in g.Vertices]); T = []
    for i in range(g.Faces.Count):
        f = g.Faces[i]; ids = [f[0], f[1], f[2]] + ([f[3]] if f[3] != f[2] else [])
        P = Polygon(V[ids])
        if abs(P.area) > 1e3: T.append(P.buffer(0))
    return unary_union(T) if T else None
RV = [_plan(o.Geometry) for o in m.Objects if m.Layers[o.Attributes.LayerIndex].Name.startswith('02_')]
RV = unary_union([f for f in RV if f is not None and not f.is_empty])
HULL = unary_union(PL + [RD]).convex_hull.buffer(5000, join_style=2)
GR = HULL.difference(S).difference(RV)
GR = GR.buffer(-3, join_style=2)                     # 敷地・川と3 mm離す（輪が一点で触れる所も離れる）
ng = 0
for g in getattr(GR, 'geoms', [GR]):
    if g.geom_type != 'Polygon' or g.area < 1e6: continue          # 1 m²より小さいかけらは入れない
    g = g.simplify(2)                                              # 敷地・川の縁から出ないように細かく
    n0 = len(m.Objects)
    K.prism(g, Z_GR - T_RD, Z_GR, L_GR)
    for o in list(m.Objects)[n0:]: o.Attributes.Name = '周辺の地面（平ら）'
    ng += len(m.Objects) - n0
print('ground: 範囲%.1f m2、敷地%.1f m2・川%.1f m2を抜いて、周辺の地面%.1f m2（%d枚）' % (HULL.area / 1e6, HULL.intersection(S).area / 1e6, HULL.intersection(RV).difference(S).area / 1e6, sum(g.area for g in getattr(GR, 'geoms', [GR]) if g.geom_type == 'Polygon' and g.area >= 1e6) / 1e6, ng))
m.Write(OUT, 8)
print('context: bldg', nb, '(site', skip_b, 'removed)  road', nr, '(site', skip_r, 'removed) →', OUT, len(m.Objects))
