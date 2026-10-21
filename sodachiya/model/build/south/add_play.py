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
K.prism(Point(c_st).buffer(st['soft_r'] * 1000, resolution=32).intersection(PLAY), 0.0, 30.0, L_FL, (239, 226, 200))
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
cv = P['cave']; pf = cv['platform']
K.prism(RW(cv['u0'] + 0.1, cv['u1'] - 0.1, pf[0], pf[1]).intersection(PLAY), 0.0, pf[2] * 1000, L_DK)
store = RW(cv['u0'], cv['u1'], cv['store'][0], cv['store'][1]).intersection(PLAY)
K.prism(store, 0.0, cv['beam_bottom'] * 1000, L_SO)
# ---------------------------------------------------------------- デッキ・家具階段
dk = P['deck']
K.prism(RW(dk['u0'], dk['u1'], dk['w0'], dk['w1']), 0.0, dk['h'] * 1000, L_DK)
ds = P['deck_steps']; n_ = len(ds['hs'])
for k, h in enumerate(ds['hs']):
    ua = ds['u0'] + (ds['u1'] - ds['u0']) * k / n_; ub = ds['u0'] + (ds['u1'] - ds['u0']) * (k + 1) / n_
    K.prism(RW(ua, ub, ds['w0'], ds['w1']), 0.0, h * 1000, L_DK)
# ---------------------------------------------------------------- キャットウォーク（h3.0、幅 0.9、手すり h1.1）・輪の通路・橋
cw = P['catwalk']; H = cw['h'] * 1000; TH = 100.0; RAIL = cw['rail'] * 1000
band = WN.buffer(-cw['inset'] * 1000, join_style=1).difference(WN.buffer(-(cw['inset'] + cw['width']) * 1000, join_style=1))
zone = unary_union([RW(cw['u_start'], 60, -0.5, 1.6), RW(cw['north_u'], 60, -0.5, cw['west_w'])])
CAT = band.intersection(zone)
rg = P['ring']; ring_in = Point(c_net).buffer(rg['inner_r'] * 1000, resolution=48); ring_out = Point(c_net).buffer(rg['outer_r'] * 1000, resolution=48)
RING = ring_out.difference(ring_in)
bf, bt, bw = P['bridge']['from'], P['bridge']['to'], P['bridge']['width']
BRIDGE = RW(bf[0], bt[0], bf[1] - bw / 2, bf[1] + bw / 2).difference(ring_in)
WALK = unary_union([CAT, RING, BRIDGE])
K.prism(WALK, H - TH, H, L_CW)
# 手すり：通路の縁のうち、壁に沿わない所（厚さ 30）
edge = WALK.boundary.difference(WN.buffer(-cw['inset'] * 1000 + 20).exterior.buffer(60)).difference(ring_in.buffer(5))
K.prism(edge.buffer(15, cap_style=2).intersection(WALK.buffer(16)), H, H + RAIL, L_CW)
# ネットを留める鋼の輪と吊り材 6 本
K.prism(ring_in.buffer(40).difference(ring_in), H - 150, H, L_NET, STEEL)
for k in range(rg['rods']):
    a = 2 * math.pi * (k + 0.5) / rg['rods']; rr_ = (rg['inner_r'] + rg['outer_r']) / 2 * 1000
    p = c_net + rr_ * np.array([math.cos(a), math.sin(a)])
    K.tube([*p, H], [*p, under_roof(*p)], 15, 15, L_NET, STEEL, n=6)
# ---------------------------------------------------------------- 摺鉢ネット（上の縁 r2.1・h3.0 → 下の口 r0.3・h0.5）
G = []
for i in range(17):
    t = i / 16                                         # 0 = 下の口、1 = 上の縁
    rr = (nt['bottom_r'] + (nt['ring_r'] - nt['bottom_r']) * t ** 1.6) * 1000
    z = (nt['bottom_h'] + (cw['h'] - nt['bottom_h']) * t) * 1000
    G.append([[c_net[0] + rr * math.cos(a), c_net[1] + rr * math.sin(a), z] for a in np.linspace(0, 2 * math.pi, 49)])
K.surface(G, L_NET, (122, 90, 54))
K.tube([*c_net, nt['bottom_h'] * 1000 - 20], [*c_net, nt['bottom_h'] * 1000 + 20], nt['bottom_r'] * 1000 + 40, nt['bottom_r'] * 1000 + 40, L_NET, STEEL, n=24)
# ---------------------------------------------------------------- すべり台（キャットウォークの西の端 → 床）
sl = P['slide']; s0 = np.array(xy(sl['from'][0], -0.9 - sl['from'][1])); s1 = np.array(xy(sl['to'][0], -0.9 - sl['to'][1]))
dd = (s1 - s0) / np.linalg.norm(s1 - s0); nn = np.array([-dd[1], dd[0]]) * sl['width'] * 500
z0s, z1s = H, 350.0
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
