"""遊戯室のしつらえ・遊具を 3dm に（寸法は data/play.json、遊戯室のスレッドの担当。レイヤー 80〜89）
使い方: python3 add_play.py IN.3dm OUT.3dm PLAY.json WNEW.pkl
窓・大戸の開口は add_west_south.py が外壁に開ける（同じ play.json を読む）。
"""
import sys, math, json, pickle, numpy as np, rhino3dm as r
sys.path.insert(0, '/tmp/claude-0/t/south')
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from uv import xy, uv
from meshkit import Kit, R, RW

IN, OUT, PJ, WNPKL = sys.argv[1:5]
P = json.load(open(PJ, encoding='utf-8'))
m = r.File3dm.Read(IN)
LN = {i: l.FullPath for i, l in enumerate(m.Layers)}
def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.FullPath == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)
WN = pickle.load(open(WNPKL, 'rb'))['WN']
WNi = WN.buffer(-150, join_style=2)
PLAY = WNi.intersection(R(30.0, 60.0, -0.9, -30.0))
K = Kit(m)
WOOD, WOOD2, MAT, STEEL = (216, 191, 153), (176, 138, 90), (233, 201, 166), (90, 90, 90)
L_FL = layer('80_遊戯室_穴の底・やわらかい床', (233, 201, 166))
L_DK = layer('81_遊戯室_デッキ・家具階段・洞の台', (216, 185, 138))
L_CW = layer('82_遊戯室_キャットウォーク・輪の通路・橋', (176, 138, 90))
L_NET = layer('83_遊戯室_摺鉢ネット・吊り材', (122, 90, 54))
L_SL = layer('84_遊戯室_すべり台', (207, 224, 234))
L_ST = layer('85_遊戯室_切り株', (138, 106, 68))
L_HD = layer('86_遊戯室_ひだ（くぼみ・ベンチ・腰掛け）', (217, 196, 154))
L_SO = layer('87_遊戯室_道具入れ', (205, 187, 152))
L_FAN = layer('88_遊戯室_天井扇', (90, 122, 154))
P3 = lambda u, w, z: np.array([*xy(u, -0.9 - w), z])

# 遊戯室の天井（西館の屋根の下）の高さ：屋根の点から近いものを
roofp = []
for o in m.Objects:
    if LN[o.Attributes.LayerIndex].startswith('20_') and isinstance(o.Geometry, r.Mesh):
        g = o.Geometry; roofp += [[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))]
roofp = np.array(roofp)
def under_roof(x, y):
    d = np.hypot(roofp[:, 0] - x, roofp[:, 1] - y); i = np.argsort(d)[:4]
    return float(np.average(roofp[i, 2], weights=1 / (d[i] + 1))) - 300

# ---------------------------------------------------------------- 穴の底（床の板 31 に穴をあける）
nt, pt = P['net'], P['pit']
c_net = np.array(xy(nt['u'], -0.9 - nt['w']))
pit = Point(c_net).buffer(pt['r'] * 1000, resolution=24)
out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
for l in m.Layers: out.Layers.Add(l)
for mt in m.Materials: out.Materials.Add(mt)
L31 = [i for i, n in LN.items() if n.startswith('31_')][0]
plate31 = []
for o in m.Objects:
    if o.Attributes.LayerIndex == L31 and isinstance(o.Geometry, r.Mesh):
        g = o.Geometry; V = np.array([[g.Vertices[i].X, g.Vertices[i].Y] for i in range(len(g.Vertices))])
        ps = [Polygon(V[[g.Faces[i][0], g.Faces[i][1], g.Faces[i][2]]]).buffer(0) for i in range(g.Faces.Count)]
        plate31.append(unary_union([p.buffer(1) for p in ps if p.area > 0]).buffer(-1)); continue
    out.Objects.Add(o.Geometry, o.Attributes)
K.m = out
for p in plate31: K.flat(p.difference(pit), 10, L31)
dep = pt['depth'] * 1000
K.prism(pit.difference(pit.buffer(-50)), -dep, 0.0, L_FL, (200, 180, 150))                 # 穴の縁
K.prism(pit, -dep - 50, -dep, L_FL, (200, 180, 150))                                        # 穴の底
K.prism(pit.buffer(-50), -dep, -dep + pt['mat'] * 1000, L_FL, MAT)                          # マット
# ---------------------------------------------------------------- 切り株とやわらかい床
st = P['stump']; c_st = np.array(xy(st['u'], -0.9 - st['w']))
STAIR_BOX = RW(29.9, 34.02, -1.0, 4.16)                 # 10-28（監修の項 0015 の 5）：φ6.6 に広げ、階段の箱で切る（幹のまわりの穴は取り込み用ファイル play3d.py の側）
SOFT_ST = Point(c_st).buffer(st['soft_r'] * 1000, resolution=48).intersection(PLAY).intersection(RW(30.07, 60.0, -1.0, 20.0)).difference(STAIR_BOX)
K.prism(SOFT_ST, 0.0, 30.0, L_FL, (239, 226, 200))
K.tube([*c_st, 0], [*c_st, 1100], st['trunk_r'] * 1000, st['trunk_r'] * 900, L_ST, (168, 132, 86), n=16)
up = np.array(xy(st['u'] + 1, -0.9 - st['w'])) - c_st; up /= np.linalg.norm(up)
east = np.array(xy(st['u'], -0.9 - st['w'] + 1)) - c_st; east /= np.linalg.norm(east)
for ang, L in st['branches']:
    a = math.radians(ang); d = up * math.cos(a) + east * math.sin(a)
    tip = c_st + d * L * 1000
    zt = 2900.0 if uv(*tip)[0] < P['cave']['u1'] else 2900.0 + 900 * max(0.0, math.cos(a))     # 洞の中は 2 階の床の下まで、北の枝は高い側へ
    mid = c_st + d * L * 550
    K.tube([*(c_st + d * 300), 950], [*mid, (950 + zt) / 2 + 300], 170, 120, L_ST, (138, 106, 68))
    K.tube([*mid, (950 + zt) / 2 + 300], [*tip, zt], 120, 60, L_ST, (138, 106, 68))
# ---------------------------------------------------------------- 洞の台・道具入れ
cv = P['cave']
if 'platform' in cv:                                    # 腰掛けの台（10-21 夜 9 でやめた。キーがあれば作る）
    pf = cv['platform']
    K.prism(RW(cv['u0'] + 0.1, cv['u1'] - 0.1, pf[0], pf[1]).intersection(PLAY), 0.0, pf[2] * 1000, L_DK)
if 'store' in cv:                                   # 10-25：洞の道具入れの箱はやめた（play.json に store が無い）
    store = RW(cv['u0'], cv['u1'], cv['store'][0], cv['store'][1]).intersection(PLAY)
    K.prism(store, 0.0, cv['beam_bottom'] * 1000, L_SO)
# ---------------------------------------------------------------- デッキ・家具階段
dk = P['deck']
K.prism(RW(dk['u0'], dk['u1'], dk['w0'], dk['w1']), 0.0, dk['h'] * 1000, L_DK)
ds = P['deck_steps']; n_ = len(ds['hs'])
for k, h in enumerate(ds['hs']):
    ua = ds['u0'] + (ds['u1'] - ds['u0']) * k / n_; ub = ds['u0'] + (ds['u1'] - ds['u0']) * (k + 1) / n_
    K.prism(RW(ua, ub, ds['w0'], ds['w1']), 0.0, h * 1000, L_DK)
if 'soft' in dk:                                        # デッキの下のやわらかい床（10-28、監修の項 0015 の 4。80 は play3d.py の取り込み用ファイルで置き換わる）
    sf = dk['soft']; _st = lambda k: RW(ds['u0'] + (ds['u1'] - ds['u0']) * k / n_, ds['u0'] + (ds['u1'] - ds['u0']) * (k + 1) / n_, ds['w0'], ds['w1'])
    DK_ALL = unary_union([RW(dk['u0'], dk['u1'], dk['w0'], dk['w1'])] + [_st(k) for k in range(n_)])
    DK_HI = unary_union([RW(dk['u0'], dk['u1'], dk['w0'], dk['w1'])] + [_st(k) for k, h in enumerate(ds['hs']) if h > sf['from_h']])
    K.prism(DK_HI.buffer(sf['margin'] * 1000, resolution=16).intersection(WNi).difference(DK_ALL.buffer(5)).difference(pit).difference(SOFT_ST).difference(STAIR_BOX),
            0.0, sf['t'] * 1000, L_FL, (239, 226, 200))
# 北の口のついたて（L 字、吸音、h2.4）
if 'screen' in P:
    sc = P['screen']
    K.prism(RW(sc['u0'], sc['u1'], sc['w'], sc['w'] + sc['t']), 0.0, sc['h'] * 1000, L_DK, (201, 183, 154))
    K.prism(RW(sc['u0'], sc['u0'] + sc['t'], sc['return_w'], sc['w'] + sc['t'], 0.02), 0.0, sc['h'] * 1000, L_DK, (201, 183, 154))
# ---------------------------------------------------------------- キャットウォーク（h3.0、北で段で h2.0 へ）・輪の通路・網の吊り橋・踊り場・はしご
cw = P['catwalk']; H = cw['h'] * 1000; TH = 100.0; RAIL = cw['rail'] * 1000
band = WN.buffer(-cw['inset'] * 1000, join_style=1).difference(WN.buffer(-(cw['inset'] + cw['width']) * 1000, join_style=1))
zone = unary_union([RW(cw['u_start'], 60, -0.5, 1.6), RW(cw['north_u'], 60, -0.5, cw['west_w'])])
CAT = band.intersection(zone)
stp = cw.get('steps')
ld = P.get('landing'); HL = ld['h'] * 1000 if ld else H
def cat_pieces():
    """キャットウォークを高さごとに分ける：東から w0 まで h3.0、段（n 段）、w1 から西は踊り場の高さ"""
    if not stp: return [(CAT, H)]
    out = [(CAT.intersection(RW(0, 60, -1, stp['w0'])), H)]
    for k in range(stp['n']):
        wa = stp['w0'] + (stp['w1'] - stp['w0']) * k / stp['n']; wb = stp['w0'] + (stp['w1'] - stp['w0']) * (k + 1) / stp['n']
        out.append((CAT.intersection(RW(0, 60, wa, wb)), (stp['from_h'] - stp['rise'] * (k + 1)) * 1000))
    out.append((CAT.intersection(RW(0, 60, stp['w1'], 30)), stp['to_h'] * 1000))
    return out
for g, z in cat_pieces(): K.prism(g, z - TH, z, L_CW)
rg = P['ring']; ring_in = Point(c_net).buffer(rg['inner_r'] * 1000, resolution=48); ring_out = Point(c_net).buffer(rg['outer_r'] * 1000, resolution=48)
RING = ring_out.difference(ring_in)
K.prism(RING, H - TH, H, L_CW)
LAND = None
if ld:
    c_ld = np.array(xy(ld['u'], -0.9 - ld['w']))
    LAND = Point(c_ld).buffer(ld['r'] * 1000, resolution=3)          # 踊り場（六角形に近い多角形）
    K.prism(LAND, HL - TH, HL, L_CW)
    for k in range(3):                                                # 低い柱
        a = 2 * math.pi * k / 3 + 0.3; p = c_ld + 0.6 * ld['r'] * 1000 * np.array([math.cos(a), math.sin(a)])
        K.tube([*p, 0], [*p, HL - TH], 45, 45, L_CW, n=8)
    # 網の吊り橋：輪 h3.0 → 踊り場 h2.0、真ん中が sag だけ垂れる（網の面）
    br = P['bridge']; d_ = c_ld - c_net; L_ = np.linalg.norm(d_); e_ = d_ / L_; n2 = np.array([-e_[1], e_[0]]) * br['width'] * 500
    s0_ = rg['outer_r'] * 1000; s1_ = L_ - ld['r'] * 1000 * 0.85
    G = []
    for t in np.linspace(0, 1, 13):
        p = c_net + e_ * (s0_ + (s1_ - s0_) * t)
        z = br['h_from'] * 1000 + (br['h_to'] - br['h_from']) * 1000 * t - br['sag'] * 1000 * 4 * t * (1 - t)
        G.append([[*(p + n2), z], [*(p - n2), z]])
    G = np.array(G).transpose(1, 0, 2)
    K.surface(G, L_NET, (122, 90, 54))
    for side in (1, -1):                                              # 網の手すりの縁綱（h0.9 上）
        for i in range(12):
            a_ = G[0 if side > 0 else 1][i]; b_ = G[0 if side > 0 else 1][i + 1]
            K.tube([a_[0], a_[1], a_[2] + 900], [b_[0], b_[1], b_[2] + 900], 12, 12, L_NET, STEEL, n=6, caps=False)
WALK = unary_union([CAT, RING] + ([LAND] if LAND is not None else []))
# 手すり：通路の縁のうち、壁に沿わない所（縦格子 h1.1、ここでは厚さ 30 の面で表す）
edge = WALK.boundary.difference(WN.buffer(-cw['inset'] * 1000 + 20).exterior.buffer(60)).difference(ring_in.buffer(5))
for g, z in cat_pieces() + [(RING, H)] + ([(LAND, HL)] if LAND is not None else []):
    e_g = edge.intersection(g.buffer(20))
    if not e_g.is_empty: K.prism(e_g.buffer(15, cap_style=2).intersection(g.buffer(16)), z, z + RAIL, L_CW)
# はしご（踊り場へ）
if 'ladder' in P:
    la = P['ladder']; a0 = np.array(xy(la['base'][0], -0.9 - la['base'][1])); a1 = np.array(xy(la['top'][0], -0.9 - la['top'][1]))
    dl = (a1 - a0) / np.linalg.norm(a1 - a0); nl = np.array([-dl[1], dl[0]]) * la['width'] * 500
    for sgn in (1, -1):
        K.tube([*(a0 + nl * sgn), 0], [*(a1 + nl * sgn), la['h'] * 1000], 25, 25, L_CW, n=8)
    nr = int(round(la['h'] / la['rung']))
    for k in range(1, nr):
        t = k / nr; p = a0 + (a1 - a0) * t
        K.tube([*(p + nl), t * la['h'] * 1000], [*(p - nl), t * la['h'] * 1000], 15, 15, L_CW, n=6)
# ネットを留める鋼の輪
K.prism(ring_in.buffer(40).difference(ring_in), H - 150, H, L_NET, STEEL)
# 吊り材（support：吊るのは西館の梁だけ、梁の位置 u = 3 の倍数、梁の 2 枚のあいだを通す）
SUP = P.get('support', {})
for ub in (36, 39, 42, 45, 48):                                       # キャットウォークの外側の縁（東の壁沿い）
    for g, z in cat_pieces():
        p_ = g.intersection(LineString([xy(ub, -0.9), xy(ub, -30)]))
        if p_.is_empty: continue
        q = list(p_.coords) if p_.geom_type == 'LineString' else [c for gg in getattr(p_, 'geoms', []) for c in gg.coords]
        if not q: continue
        far = max(q, key=lambda c: -uv(*c)[1])                          # 部屋の側（西寄り）の縁
        K.tube([*far, z - TH], [*far, under_roof(*far)], 8, 8, L_NET, STEEL, n=6)
        break
rr_ = (rg['inner_r'] + rg['outer_r']) / 2 * 1000
spread = SUP.get('v_spread', 0.9) * 500
for ub in (39, 42, 45):                                               # 輪：ハの字の 3 組
    cand = sorted([(abs(uv(*(c_net + rr_ * np.array([math.cos(a), math.sin(a)])))[0] - ub), a) for a in np.linspace(0, 2 * math.pi, 72, endpoint=False)])
    a_best = cand[0][1]
    for da in (-0.35, 0.35):
        p = c_net + rr_ * np.array([math.cos(a_best + da), math.sin(a_best + da)])
        pu, pv = uv(*p); top = np.array(xy(ub, pv + (spread / 1000) * np.sign(da)))
        K.tube([*p, H], [*top, under_roof(*top)], 8, 8, L_NET, STEEL, n=6)
    # 東の壁の柱への水平の突っ張り
    p = c_net + rg['outer_r'] * 1000 * np.array([math.cos(a_best), math.sin(a_best)])
    wall = np.array(xy(ub, -0.9 - 0.15))
    K.tube([*p, H - 60], [*wall, H - 60], 30, 30, L_NET, STEEL, n=8)
# ---------------------------------------------------------------- 摺鉢ネット（上の縁 r2.1・h3.0 → 下の口 r0.3・h0.15＝マットの上から 0.5）
G = []
for i in range(17):
    t = i / 16                                         # 0 = 下の口、1 = 上の縁
    rr = (nt['bottom_r'] + (nt['ring_r'] - nt['bottom_r']) * t ** 1.6) * 1000
    z = (nt['bottom_h'] + (cw['h'] - nt['bottom_h']) * t) * 1000
    G.append([[c_net[0] + rr * math.cos(a), c_net[1] + rr * math.sin(a), z] for a in np.linspace(0, 2 * math.pi, 49)])
K.surface(G, L_NET, (122, 90, 54))
K.tube([*c_net, nt['bottom_h'] * 1000 - 20], [*c_net, nt['bottom_h'] * 1000 + 20], nt['bottom_r'] * 1000 + 40, nt['bottom_r'] * 1000 + 40, L_NET, STEEL, n=24)
# ---------------------------------------------------------------- すべり台（踊り場 h2.0 → 床）
sl = P['slide']; s0 = np.array(xy(sl['from'][0], -0.9 - sl['from'][1])); s1 = np.array(xy(sl['to'][0], -0.9 - sl['to'][1]))
dd = (s1 - s0) / np.linalg.norm(s1 - s0); nn = np.array([-dd[1], dd[0]]) * sl['width'] * 500
z0s, z1s = sl.get('h', cw['h']) * 1000, 350.0
def slab(a, b, za, zb, w, zt):
    n_ = np.array([-dd[1], dd[0]]) * w
    K.box8([[*(a + n_), za], [*(b + n_), zb], [*(b - n_), zb], [*(a - n_), za],
            [*(a + n_), za + zt], [*(b + n_), zb + zt], [*(b - n_), zb + zt], [*(a - n_), za + zt]], L_SL, (207, 224, 234))
slab(s0, s1, z0s - 60, z1s - 60, sl['width'] * 500, 60)
for sgn in (1, -1):                                            # 両脇の立ち上がり h200
    off = np.array([-dd[1], dd[0]]) * (sl['width'] * 500 - 15) * sgn
    slab(s0 + off, s1 + off, z0s, z1s, 15, 200)
# ---------------------------------------------------------------- ひだ：柱と柱のあいだのくぼみ（造作の箱）、丸いベンチ、北の窓辺の腰掛け
def face_w(u):
    ln = LineString([xy(u, -0.9), xy(u, -30)]); x = ln.intersection(WN.exterior)
    pts = [x] if x.geom_type == 'Point' else list(getattr(x, 'geoms', []))
    return max(-0.9 - uv(p.x, p.y)[1] for p in pts) - 0.15      # 内側の面（壁の厚さ 150）
N_ = P['niche']; b_ = N_['board']
for ua, ub in P['niches']:
    wa = min(face_w(ua), face_w(ub)); w0 = wa - P['niche_depth']
    K.prism(RW(ua, ub, wa - N_['seat_d'], wa), 0.0, N_['seat_h'] * 1000, L_HD)                     # 座（下は引き出し）
    K.prism(RW(ua - b_, ub + b_, w0, wa), N_['top_h'] * 1000, (N_['top_h'] + b_) * 1000, L_HD)    # 天板（飾り棚）
    for uu in (ua - b_, ub):
        K.prism(RW(uu, uu + b_, w0, wa, 0.02), 0.0, N_['top_h'] * 1000, L_HD)                    # 側板
rb = P['round_bench']
K.prism(WNi.difference(WNi.buffer(-rb['depth'] * 1000, join_style=1)).intersection(RW(rb['u0'], rb['u1'], 6.5, 20)), 0.0, 350.0, L_HD)
nw = P['north_window']
K.prism(RW(51.0 - 0.15 - nw['seat_d'], 51.0 - 0.15, nw['w0'], nw['w1']).intersection(WNi), 0.0, nw['seat_h'] * 1000, L_HD)
# ---------------------------------------------------------------- 天井扇 φ1.1（越屋根の吹き抜けの下、h6.0）
fn = P['fans']
for u in fn['u']:
    c = np.array(xy(u, -0.9 - fn['w']))
    K.prism(Point(c).buffer(fn['d'] * 500, resolution=16), fn['h'] * 1000 - 40, fn['h'] * 1000, L_FAN)
    K.tube([*c, fn['h'] * 1000], [*c, under_roof(*c)], 15, 15, L_FAN, n=6)

out.Write(OUT, 8); print('written', OUT, len(out.Objects))
