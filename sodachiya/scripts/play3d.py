"""遊戯室の遊具・しつらえを 3dm の取り込み用ファイルに（遊戯室の担当、寸法は data/play.json）。
出力：model/sodachiya_play_layers.3dm（レイヤー 80〜89、座標は本体と同じ mm、z=0 が FL）。
本体（木造）は 80〜89 をこのファイルで置き換えればよい（園庭の garden_layers と同じ流れ）。模型作成はこれを直接読める。
本体の model/build/south/add_play.py が読んでいた形に、10-21 夜の変更（北の段・踊り場 h2.0・網の吊り橋・はしご・
すべり台 h2.0・ついたて・支え方の吊り材）を足した。床の板 31 の穴（穴の底）は本体の側の仕事なので、ここでは作らない。
使い方: python3 sodachiya/scripts/play3d.py
"""
import os, sys, math, json, pickle, numpy as np, rhino3dm as r
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
from shapely.geometry import Point, LineString, Polygon
from shapely.ops import unary_union
from uv import xy, uv
from meshkit import Kit, RW

P = json.load(open(os.path.join(ROOT, 'data', 'play.json'), encoding='utf-8'))
WN = pickle.load(open(os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb'))['WN']
WNi = WN.buffer(-150, join_style=2)
PLAY = WNi.intersection(RW(30.0, 60.0, -30.0, 0.0) if False else WNi)
src = r.File3dm.Read(os.path.join(ROOT, 'model', 'sodachiya_exact_mesh.3dm'))
SLN = {i: l.Name for i, l in enumerate(src.Layers)}
roofp = []
for o in src.Objects:
    if SLN[o.Attributes.LayerIndex].startswith('20_') and isinstance(o.Geometry, r.Mesh):
        g = o.Geometry; roofp += [[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))]
roofp = np.array(roofp)
def under_roof(x, y):          # 屋根の下面（梁の上端のあたり）
    d = np.hypot(roofp[:, 0] - x, roofp[:, 1] - y); i = np.argsort(d)[:4]
    return float(np.average(roofp[i, 2], weights=1 / (d[i] + 1))) - 300

out = r.File3dm(); out.Settings.ModelUnitSystem = src.Settings.ModelUnitSystem
def layer(name, rgb):
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return out.Layers.Add(L)
K = Kit(out)
MAT, STEEL, WOOD = (233, 201, 166), (90, 90, 90), (176, 138, 90)
L_FL = layer('80_遊戯室_穴の底・やわらかい床', (233, 201, 166))
L_DK = layer('81_遊戯室_デッキ・家具階段・ついたて', (216, 185, 138))
L_CW = layer('82_遊戯室_キャットウォーク・段・輪の通路・踊り場・はしご', (176, 138, 90))
L_NET = layer('83_遊戯室_摺鉢ネット・吊り橋・吊り材', (122, 90, 54))
L_SL = layer('84_遊戯室_すべり台（真っ直ぐ）', (207, 224, 234))
L_SP = layer('84b_遊戯室_すべり台（くるくる、比較）', (226, 196, 214))
L_ST = layer('85_遊戯室_切り株（クスノキ）', (138, 106, 68))
L_HD = layer('86_遊戯室_ひだ（くぼみ・ベンチ・腰掛け）', (217, 196, 154))
L_SO = layer('87_遊戯室_道具入れ', (205, 187, 152))
L_FAN = layer('88_遊戯室_天井扇', (90, 122, 154))
def X(u, w): return np.array(xy(u, -0.9 - w))
def RWw(u0, u1, w0, w1): return RW(u0, u1, w0, w1)        # meshkit.RW は「東から」w

# ---------------------------------------------------------------- 穴の底（縁・底・マット）
nt, pt = P['net'], P['pit']; c_net = X(nt['u'], nt['w'])
pit = Point(c_net).buffer(pt['r'] * 1000, resolution=24); dep = pt['depth'] * 1000
K.prism(pit.difference(pit.buffer(-50)), -dep, 0.0, L_FL, (200, 180, 150))
K.prism(pit, -dep - 50, -dep, L_FL, (200, 180, 150))
K.prism(pit.buffer(-50), -dep, -dep + pt['mat'] * 1000, L_FL, MAT)
# ---------------------------------------------------------------- 切り株（クスノキ）とやわらかい床
st = P['stump']; c_st = X(st['u'], st['w'])
K.prism(Point(c_st).buffer(st['soft_r'] * 1000, resolution=32).intersection(WNi), 0.0, 30.0, L_FL, (239, 226, 200))
K.tube([*c_st, 0], [*c_st, 1100], st['trunk_r'] * 1000, st['trunk_r'] * 900, L_ST, (168, 132, 86), n=16)
up = X(st['u'] + 1, st['w']) - c_st; up /= np.linalg.norm(up)
east = X(st['u'], st['w'] - 1) - c_st; east /= np.linalg.norm(east)
for ang, Lb in st['branches']:
    a = math.radians(ang); d = up * math.cos(a) + east * math.sin(a); tip = c_st + d * Lb * 1000
    zt = 2900.0 if uv(*tip)[0] < P['cave']['u1'] else 2900.0 + 900 * max(0.0, math.cos(a))
    mid = c_st + d * Lb * 550
    K.tube([*(c_st + d * 300), 950], [*mid, (950 + zt) / 2 + 300], 170, 120, L_ST, (138, 106, 68))
    K.tube([*mid, (950 + zt) / 2 + 300], [*tip, zt], 120, 60, L_ST, (138, 106, 68))
# ---------------------------------------------------------------- 洞の道具入れ
cv = P['cave']
K.prism(RWw(cv['u0'], cv['u1'], cv['store'][0], cv['store'][1]).intersection(WNi), 0.0, cv['beam_bottom'] * 1000, L_SO)
# ---------------------------------------------------------------- デッキ・家具階段
dk = P['deck']; K.prism(RWw(dk['u0'], dk['u1'], dk['w0'], dk['w1']), 0.0, dk['h'] * 1000, L_DK)
ds = P['deck_steps']; n_ = len(ds['hs'])
for k, h in enumerate(ds['hs']):
    ua = ds['u0'] + (ds['u1'] - ds['u0']) * k / n_; ub = ds['u0'] + (ds['u1'] - ds['u0']) * (k + 1) / n_
    K.prism(RWw(ua, ub, ds['w0'], ds['w1']), 0.0, h * 1000, L_DK)
# ---------------------------------------------------------------- 北の口のついたて（L 字、h2.4、吸音）
sc = P['screen']
K.prism(RWw(sc['u0'], sc['u1'], sc['w'], sc['w'] + sc['t']), 0.0, sc['h'] * 1000, L_DK)
K.prism(RWw(sc['u0'], sc['u0'] + sc['t'], 0.0, sc['w'] + sc['t']), 0.0, sc['h'] * 1000, L_DK)
# ---------------------------------------------------------------- キャットウォーク（東 h3.0 → 北の段 → h2.0）・輪・踊り場
cw = P['catwalk']; H = cw['h'] * 1000; TH = 100.0; RAIL = cw['rail'] * 1000; sp = cw['steps']
band = WN.buffer(-cw['inset'] * 1000, join_style=1).difference(WN.buffer(-(cw['inset'] + cw['width']) * 1000, join_style=1))
CAT = band.intersection(unary_union([RWw(cw['u_start'], 60, -0.5, 1.6), RWw(cw['north_u'], 60, -0.5, cw['west_w'])]))
HIGH = CAT.intersection(unary_union([RWw(cw['u_start'], cw['north_u'] + 0.01, -0.5, 1.6), RWw(cw['north_u'], 60, -0.5, sp['w0'])]))
LOW = CAT.intersection(RWw(cw['north_u'], 60, sp['w1'], cw['west_w']))
H2 = sp['to_h'] * 1000
K.prism(HIGH, H - TH, H, L_CW, WOOD)
K.prism(LOW, H2 - TH, H2, L_CW, WOOD)
for k in range(sp['n']):                                        # 段 200×5（東から w0 → w1 で下がる）
    wa = sp['w0'] + (sp['w1'] - sp['w0']) * k / sp['n']; wb = sp['w0'] + (sp['w1'] - sp['w0']) * (k + 1) / sp['n']
    z = H - sp['rise'] * 1000 * (k + 1)
    K.prism(CAT.intersection(RWw(cw['north_u'], 60, wa, wb)), z - TH, z, L_CW, WOOD)
rg = P['ring']; ring_in = Point(c_net).buffer(rg['inner_r'] * 1000, resolution=48)
RING = Point(c_net).buffer(rg['outer_r'] * 1000, resolution=48).difference(ring_in)
K.prism(RING.difference(HIGH), H - TH, H, L_CW, WOOD)
ld = P['landing']; c_ld = X(ld['u'], ld['w']); LAND = Point(c_ld).buffer(ld['r'] * 1000, resolution=3)
K.prism(LAND.difference(LOW), ld['h'] * 1000 - TH, ld['h'] * 1000, L_CW, WOOD)
# 手すり（縦格子 h1.1 の面として、厚さ 30）：通路の縁のうち壁に沿わない所
def rail(walk, z, skip=None):
    e = walk.boundary.difference(WN.buffer(-cw['inset'] * 1000 + 20).exterior.buffer(60))
    if skip is not None: e = e.difference(skip)
    g = e.buffer(15, cap_style=2).intersection(walk.buffer(16))
    if not g.is_empty: K.prism(g, z, z + RAIL, L_CW)
dbr = (c_ld - c_net) / np.linalg.norm(c_ld - c_net)
BR_ZONE = LineString([c_net, c_ld]).buffer(P['bridge']['width'] * 500, cap_style=2)
rail(HIGH.union(RING), H, ring_in.buffer(5).union(BR_ZONE).union(LOW.buffer(5)))
rail(LOW.union(LAND), H2, BR_ZONE.union(HIGH.buffer(300)))
K.prism(ring_in.buffer(40).difference(ring_in), H - 150, H, L_NET, STEEL)       # ネットを留める鋼の輪
# ---------------------------------------------------------------- 網の吊り橋（輪 h3.0 → 踊り場 h2.0、真ん中が垂れる）
bw = P['bridge']['width'] * 1000; sag = P['bridge']['sag'] * 1000
pa = c_net + dbr * rg['outer_r'] * 1000; pb = c_ld - dbr * ld['r'] * 1000 * 0.9
nrm = np.array([-dbr[1], dbr[0]]); G = []
for i in range(13):
    t = i / 12; z = H + (ld['h'] * 1000 - H) * t - 4 * sag * t * (1 - t); c = pa + (pb - pa) * t
    G.append([[*(c + nrm * s), z] for s in np.linspace(-bw / 2, bw / 2, 5)])
K.surface(G, L_NET, (122, 90, 54))
for s in (-1, 1):                                               # 両脇の網の壁（上の綱 h0.9）
    G = []
    for i in range(13):
        t = i / 12; z = H + (ld['h'] * 1000 - H) * t - 4 * sag * t * (1 - t); c = pa + (pb - pa) * t + nrm * s * bw / 2
        G.append([[*c, z], [*c, z + 900]])
    K.surface(G, L_NET, (122, 90, 54))
# ---------------------------------------------------------------- 摺鉢ネット
G = []
for i in range(17):
    t = i / 16; rr = (nt['bottom_r'] + (nt['ring_r'] - nt['bottom_r']) * t ** 1.6) * 1000
    z = (nt['bottom_h'] + (cw['h'] - nt['bottom_h']) * t) * 1000
    G.append([[c_net[0] + rr * math.cos(a), c_net[1] + rr * math.sin(a), z] for a in np.linspace(0, 2 * math.pi, 49)])
K.surface(G, L_NET, (122, 90, 54))
K.tube([*c_net, nt['bottom_h'] * 1000 - 20], [*c_net, nt['bottom_h'] * 1000 + 20], nt['bottom_r'] * 1000 + 40, nt['bottom_r'] * 1000 + 40, L_NET, STEEL, n=24)
# ---------------------------------------------------------------- 吊り材 φ16（重さは西館の梁へ。梁の位置 u 36〜48、3.0 ごと）
beams_u = [36.0, 39.0, 42.0, 45.0, 48.0]
for u in beams_u:                                               # キャットウォークの外側の縁
    if u >= cw['u_start'] - 0.5:
        u = max(u, cw['u_start'] + 0.1)
        p = X(u, cw['inset'] + cw['width'] - 0.05); K.tube([*p, H], [*p, under_roof(*p)], 8, 8, L_NET, STEEL, n=6)
vs = P['support']['v_spread'] * 1000
for k in range(rg['rods']):                                     # 輪：ハの字 3 組、上は梁 u 39・42・45
    a = 2 * math.pi * (k + 0.5) / rg['rods']; rr_ = (rg['inner_r'] + rg['outer_r']) / 2 * 1000
    p = c_net + rr_ * np.array([math.cos(a), math.sin(a)])
    uu, vv = uv(*p); ub = min([39.0, 42.0, 45.0], key=lambda b: abs(b - uu))
    q = np.array(xy(ub, vv)); along = X(ub, 0.0) - X(ub, 1.0); along /= np.linalg.norm(along)
    q = q + along * vs * (1 if k % 2 else -1)
    K.tube([*p, H], [*q, under_roof(*q)], 8, 8, L_NET, STEEL, n=6)
# 輪を東の柱へ突っ張る水平材（輪の東の端 → 東の壁）
pe = c_net + np.array(X(nt['u'], 0.0) - c_net) / np.linalg.norm(X(nt['u'], 0.0) - c_net) * rg['outer_r'] * 1000
K.tube([*pe, H - 60], [*X(nt['u'], -0.05), H - 60], 40, 40, L_NET, STEEL, n=8)
# ---------------------------------------------------------------- はしご（踊り場へ、段 200）
la = P['ladder']; b0 = X(*la['base']); b1 = X(*la['top']); dl = (b1 - b0) / np.linalg.norm(b1 - b0); nl = np.array([-dl[1], dl[0]]) * la['width'] * 500
zl = la['h'] * 1000
for s in (1, -1):
    K.tube([*(b0 + nl * s), 0], [*(b1 + nl * s), zl], 25, 25, L_CW, WOOD, n=6)
for k in range(1, int(round(la['h'] / la['rung']))):
    t = k * la['rung'] / la['h']; c = b0 + (b1 - b0) * t
    K.tube([*(c + nl), zl * t], [*(c - nl), zl * t], 15, 15, L_CW, WOOD, n=6)
# ---------------------------------------------------------------- すべり台（踊り場 h2.0 → 床）
sl = P['slide']; s0 = X(*sl['from']); s1 = X(*sl['to']); dd = (s1 - s0) / np.linalg.norm(s1 - s0)
z0s, z1s = sl['h'] * 1000, 350.0
def slab(a, b, za, zb, w, zt):
    n2 = np.array([-dd[1], dd[0]]) * w
    K.box8([[*(a + n2), za], [*(b + n2), zb], [*(b - n2), zb], [*(a - n2), za],
            [*(a + n2), za + zt], [*(b + n2), zb + zt], [*(b - n2), zb + zt], [*(a - n2), za + zt]], L_SL, (207, 224, 234))
slab(s0, s1, z0s - 60, z1s - 60, sl['width'] * 500, 60)
for sgn in (1, -1):
    off = np.array([-dd[1], dd[0]]) * (sl['width'] * 500 - 15) * sgn
    slab(s0 + off, s1 + off, z0s, z1s, 15, 200)
# ---------------------------------------------------------------- くるくるすべり台（比較、84b）
ss = P['slide_spiral']; cc = X(*ss['center']); R0 = ss['r'] * 1000; hw = ss['width'] * 500
p_ld = X(P['landing']['u'], P['landing']['w']); a0 = math.atan2(*(p_ld - cc)[::-1])     # 踊り場の向きから始まる
def heli(sgn):
    n = 73; out = []
    for i in range(n):
        t = i / (n - 1); a = a0 + sgn * 2 * math.pi * ss['turns'] * t
        z = (ss['from_h'] + (ss['to_h'] - ss['from_h']) * t) * 1000
        out.append((a, z))
    return out
# 出口が部屋の中（南東：u と w が減る向き）を向く回り方を選ぶ
into = X(P['landing']['u'] - 1, P['landing']['w'] - 1) - p_ld; into /= np.linalg.norm(into)
best = None
for sgn in (1, -1):
    a_end = a0 + sgn * 2 * math.pi * ss['turns']; tan = np.array([-math.sin(a_end), math.cos(a_end)]) * sgn
    if best is None or tan @ into > best[1]: best = (sgn, tan @ into, tan)
sgn, _, tan_end = best
H_ = heli(sgn)
def ring_pts(rr, dz=0.0):
    return [[cc[0] + rr * math.cos(a), cc[1] + rr * math.sin(a), z + dz] for a, z in H_]
K.surface([ring_pts(R0 - hw), ring_pts(R0 + hw)], L_SP, (226, 196, 214))                       # 滑る面
K.surface([ring_pts(R0 + hw), ring_pts(R0 + hw, ss['side_h_outer'] * 1000)], L_SP, (226, 196, 214))   # 外の壁
K.surface([ring_pts(R0 - hw), ring_pts(R0 - hw, ss['side_h_inner'] * 1000)], L_SP, (226, 196, 214))   # 内の壁
K.tube([*cc, 0], [*cc, ss['from_h'] * 1000 + 900], ss['post_r'] * 1000, ss['post_r'] * 1000, L_SP, STEEL, n=12)   # 中心の柱
a_e, z_e = H_[-1]; pe_ = cc + R0 * np.array([math.cos(a_e), math.sin(a_e)]); nrm_e = np.array([math.cos(a_e), math.sin(a_e)])
q0 = pe_; q1 = pe_ + tan_end * ss['runout'] * 1000
K.box8([[*(q0 - nrm_e * hw), z_e - 60], [*(q1 - nrm_e * hw), z_e - 60], [*(q1 + nrm_e * hw), z_e - 60], [*(q0 + nrm_e * hw), z_e - 60],
        [*(q0 - nrm_e * hw), z_e], [*(q1 - nrm_e * hw), z_e], [*(q1 + nrm_e * hw), z_e], [*(q0 + nrm_e * hw), z_e]], L_SP, (226, 196, 214))
a_s, z_s = H_[0]; ps_ = cc + R0 * np.array([math.cos(a_s), math.sin(a_s)])                    # 踊り場から入口への渡り
K.prism(LineString([p_ld, ps_]).buffer(hw, cap_style=2).difference(Point(p_ld).buffer(P['landing']['r'] * 950, resolution=3)), z_s - 100, z_s, L_SP, WOOD)
print('spiral', 'dir', sgn, 'start', uv(*ps_), 'end', uv(*q1))
# ---------------------------------------------------------------- ひだ
def face_w(u):
    ln = LineString([xy(u, -0.9), xy(u, -30)]); x = ln.intersection(WN.exterior)
    pts = [x] if x.geom_type == 'Point' else list(getattr(x, 'geoms', []))
    return max(-0.9 - uv(p.x, p.y)[1] for p in pts) - 0.15
N_ = P['niche']; b_ = N_['board']
for ua, ub in P['niches']:
    wa = min(face_w(ua), face_w(ub)); w0 = wa - P['niche_depth']
    K.prism(RWw(ua, ub, wa - N_['seat_d'], wa), 0.0, N_['seat_h'] * 1000, L_HD)
    K.prism(RWw(ua - b_, ub + b_, w0, wa), N_['top_h'] * 1000, (N_['top_h'] + b_) * 1000, L_HD)
    for uu in (ua - b_, ub):
        K.prism(RWw(uu, uu + b_, w0, wa), 0.0, N_['top_h'] * 1000, L_HD)
rb = P['round_bench']
K.prism(WNi.difference(WNi.buffer(-rb['depth'] * 1000, join_style=1)).intersection(RWw(rb['u0'], rb['u1'], 6.5, 20)), 0.0, 350.0, L_HD)
nw = P['north_window']
K.prism(RWw(51.0 - 0.15 - nw['seat_d'], 51.0 - 0.15, nw['w0'], nw['w1']).intersection(WNi), 0.0, nw['seat_h'] * 1000, L_HD)
# ---------------------------------------------------------------- 天井扇
fn = P['fans']
for u in fn['u']:
    c = X(u, fn['w'])
    K.prism(Point(c).buffer(fn['d'] * 500, resolution=16), fn['h'] * 1000 - 40, fn['h'] * 1000, L_FAN)
    K.tube([*c, fn['h'] * 1000], [*c, under_roof(*c)], 15, 15, L_FAN, n=6)

OUT = os.path.join(ROOT, 'model', 'sodachiya_play_layers.3dm')
out.Write(OUT, 8); print('written', OUT, len(out.Objects))
