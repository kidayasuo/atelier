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
_D = pickle.load(open(os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb')); WN = _D['WN']
WS = _D.get('WS', WN)                     # 外皮（北西の斜めの外壁は後退の線まで、10-23）。遊具は架構の輪郭 WN に沿い、柱に留める
WSi = WS.buffer(-150, join_style=2)
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
L_SL = layer('84_遊戯室_すべり台', (207, 224, 234))
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
K.prism(Point(c_st).buffer(st['soft_r'] * 1000, resolution=32).intersection(WNi).intersection(RWw(30.07, 60.0, -1.0, 20.0)), 0.0, 30.0, L_FL, (239, 226, 200))   # はれのまとの壁（u30）の北で止める（10-24夜）
# 木は骨格（stump.tree）から play_tree.py で滑らかな閉じた網目に（10-24、本物のライブオークを参考に）
from play_tree import tree_mesh
TV, TF = tree_mesh(0.025, 20000)          # 約2万面（Rhino版・3dmを軽く、10-24 本館係の知らせ）
tm = r.Mesh()
for x_, y_, z_ in TV: tm.Vertices.Add(float(x_), float(y_), float(z_))
for a_, b_, c_ in TF: tm.Faces.AddFace(int(a_), int(b_), int(c_))
K.add(tm, L_ST, (150, 112, 72))
# ---------------------------------------------------------------- 洞の道具入れ
cv = P['cave']
if 'store' in cv: K.prism(RWw(cv.get('store_u0', cv['u0']), cv['u1'], cv['store'][0], cv['store'][1]).intersection(WNi), 0.0, cv['beam_bottom'] * 1000, L_SO)   # 10-25：道具入れの箱はやめた
# ---------------------------------------------------------------- デッキ・家具階段
dk = P['deck']; K.prism(RWw(dk['u0'], dk['u1'], dk['w0'], dk['w1']), 0.0, dk['h'] * 1000, L_DK)
ds = P['deck_steps']; n_ = len(ds['hs'])
for k, h in enumerate(ds['hs']):
    ua = ds['u0'] + (ds['u1'] - ds['u0']) * k / n_; ub = ds['u0'] + (ds['u1'] - ds['u0']) * (k + 1) / n_
    K.prism(RWw(ua, ub, ds['w0'], ds['w1']), 0.0, h * 1000, L_DK)
# ---------------------------------------------------------------- 北の口のついたて（L 字、h2.4、吸音）
sc = P['screen']
K.prism(RWw(sc['u0'], sc['u1'], sc['w'], sc['w'] + sc['t']), 0.0, sc['h'] * 1000, L_DK)
K.prism(RWw(sc['u0'], sc['u0'] + sc['t'], 0.15, sc['w'] + sc['t']), 0.0, sc['h'] * 1000, L_DK)   # 折り返しは東の壁の内面（東から0.15）まで（設計監修10-23）
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
LAND = LAND.intersection(WN.buffer(-cw['inset'] * 1000, join_style=1))   # 壁から0.1手前で止める（キャットウォークと同じ線。設計監修10-23：北西の斜めの壁を突き抜けていた）
K.prism(LAND.difference(LOW), ld['h'] * 1000 - TH, ld['h'] * 1000, L_CW, WOOD)
# 手すり（縦格子 h1.1 の面として、厚さ 30）：通路の縁のうち壁に沿わない所
def rail(walk, z, skip=None):
    e = walk.boundary.difference(WS.buffer(-cw['inset'] * 1000 + 20).exterior.buffer(60))   # 外皮の壁に沿う縁だけ手すりを省く（北西の斜めは外壁まで約0.7あくので手すり）
    if skip is not None: e = e.difference(skip)
    g = e.buffer(15, cap_style=2).intersection(walk.buffer(16))
    if not g.is_empty: K.prism(g, z, z + RAIL, L_CW)
dbr = (c_ld - c_net) / np.linalg.norm(c_ld - c_net)
BR_ZONE = LineString([c_net, c_ld]).buffer(P['bridge']['width'] * 500, cap_style=2)
rail(HIGH.union(RING), H, ring_in.buffer(5).union(BR_ZONE).union(LOW.buffer(5)))
rail(LOW.union(LAND), H2, BR_ZONE.union(HIGH.buffer(300)))
# 北の段（10-28、監修の項 20261028-0015 の 3）：段ごとの西の開いた縁にも柵（前は段だけ柵が無く、西へ落ちると 1.9〜2.8 m）
for k in range(sp['n']):
    wa = sp['w0'] + (sp['w1'] - sp['w0']) * k / sp['n']; wb = sp['w0'] + (sp['w1'] - sp['w0']) * (k + 1) / sp['n']
    STP = CAT.intersection(RWw(cw['north_u'], 60, wa, wb))
    risers = unary_union([RWw(cw['north_u'], 60, w_ - 0.01, w_ + 0.01) for w_ in (wa, wb)])   # 段の境（蹴上げの線、v 一定の弧）には柵を立てない
    rail(STP, H - sp['rise'] * 1000 * (k + 1), risers)
K.prism(ring_in.buffer(40).difference(ring_in), H - 150, H, L_NET, STEEL)       # ネットを留める鋼の輪
# ---------------------------------------------------------------- 網の吊り橋（輪 h3.0 → 踊り場 h2.0、真ん中が垂れる）
bw = P['bridge']['width'] * 1000; sag = P['bridge']['sag'] * 1000
pa = c_net + dbr * rg['outer_r'] * 1000; pb = c_ld - dbr * ld['r'] * 1000 * 0.9
nrm = np.array([-dbr[1], dbr[0]]); G = []
for i in range(13):
    t = i / 12; z = H + (ld['h'] * 1000 - H) * t - 4 * sag * t * (1 - t); c = pa + (pb - pa) * t
    G.append([[*(c + nrm * s), z] for s in np.linspace(-bw / 2, bw / 2, 5)])
K.surface(G, L_NET, (122, 90, 54))
for s in (-1, 1):                                               # 両脇の網の壁（上の綱 h1.1）
    G = []
    for i in range(13):
        t = i / 12; z = H + (ld['h'] * 1000 - H) * t - 4 * sag * t * (1 - t); c = pa + (pb - pa) * t + nrm * s * bw / 2
        G.append([[*c, z], [*c, z + RAIL]])                     # 10-28（監修の項 0015 の 7）：900 → 1,100（キャットウォークの柵と同じ）
    K.surface(G, L_NET, (122, 90, 54))
# ---------------------------------------------------------------- 丸い材は円の押し出し（10-28、監修の項 2346：前は 6〜8 角の網目）
def rod(p0, p1, rad, li, col):
    p0 = np.asarray(p0, float); p1 = np.asarray(p1, float); d = p1 - p0; L_ = float(np.linalg.norm(d))
    if L_ < 1.0: return
    pl = r.Plane(r.Point3d(*map(float, p0)), r.Vector3d(*map(float, d / L_)))
    c = r.Circle(float(rad)).ToNurbsCurve(); c.Transform(r.Transform.PlaneToPlane(r.Plane.WorldXY(), pl))
    best = None
    for ex in (r.Extrusion.Create(c, L_, True), r.Extrusion.Create(c, -L_, True)):
        if ex is None: continue
        bb = ex.GetBoundingBox(); mid = np.array([(bb.Min.X + bb.Max.X) / 2, (bb.Min.Y + bb.Max.Y) / 2, (bb.Min.Z + bb.Max.Z) / 2])
        dm = np.linalg.norm(mid - (p0 + p1) / 2)
        if best is None or dm < best[0]: best = (dm, ex)
    if best is not None: out.Objects.AddExtrusion(best[1], K.attr(li, col))
# ---------------------------------------------------------------- 摺鉢ネット
# 10-28（監修の項 2346）：鉢は一つの回転体（断面＝厚さ 20 の帯を中心の軸のまわりに一周、閉じた立体）。前は 17×49 の四角形の面で 770 面
_pr = []
for i in range(17):
    t = i / 16; rr = (nt['bottom_r'] + (nt['ring_r'] - nt['bottom_r']) * t ** 1.6) * 1000
    z = (nt['bottom_h'] + (cw['h'] - nt['bottom_h']) * t) * 1000
    _pr.append((rr, z))
_pr = np.array(_pr); _d = np.gradient(_pr, axis=0); _n = np.c_[_d[:, 1], -_d[:, 0]]; _n /= np.linalg.norm(_n, axis=1)[:, None]
_sec = list(_pr + _n * 10.0) + list((_pr - _n * 10.0)[::-1])
_crv = r.Curve.CreateControlPointCurve([r.Point3d(c_net[0] + q[0], c_net[1], q[1]) for q in _sec] + [r.Point3d(c_net[0] + _sec[0][0], c_net[1], _sec[0][1])], 1)
_axis = r.Line(r.Point3d(c_net[0], c_net[1], 0.0), r.Point3d(c_net[0], c_net[1], 1000.0))
_rev = r.RevSurface.Create(_crv, _axis, 0.0, 2 * math.pi)
_bw = r.Brep.CreateFromRevSurface(_rev, False, False)
out.Objects.AddBrep(_bw, K.attr(L_NET, (122, 90, 54)))
print('net bowl: revolution solid', _bw.IsSolid, len(_bw.Faces))
rod([*c_net, nt['bottom_h'] * 1000 - 20], [*c_net, nt['bottom_h'] * 1000 + 20], nt['bottom_r'] * 1000 + 40, L_NET, STEEL)
# ---------------------------------------------------------------- 吊り材 M20（φ20、10-27：M16 では揺れ・跳びの衝撃に余裕が無い。重さは西館の梁へ。梁の位置 u 36〜48、3.0 ごと）
beams_u = [36.0, 39.0, 42.0, 45.0, 48.0]
for u in beams_u:                                               # キャットウォークの外側の縁
    if u >= cw['u_start'] - 0.5:
        u = max(u, cw['u_start'] + 0.1)
        p = X(u, cw['inset'] + cw['width'] - 0.05); rod([*p, H], [*p, under_roof(*p)], 10, L_NET, STEEL)
vs = P['support']['v_spread'] * 1000
for k in range(rg['rods']):                                     # 輪：ハの字 3 組、上は梁 u 39・42・45
    a = 2 * math.pi * (k + 0.5) / rg['rods']; rr_ = (rg['inner_r'] + rg['outer_r']) / 2 * 1000
    p = c_net + rr_ * np.array([math.cos(a), math.sin(a)])
    uu, vv = uv(*p); ub = min([39.0, 42.0, 45.0], key=lambda b: abs(b - uu))
    q = np.array(xy(ub, vv)); along = X(ub, 0.0) - X(ub, 1.0); along /= np.linalg.norm(along)
    q = q + along * vs * (1 if k % 2 else -1)
    if -0.9 - uv(*q)[1] < 0.25: q = np.array(xy(ub, -0.9 - 0.25))   # 上端は壁の内面（東から0.15）より0.1内側まで（設計監修10-23：東の壁に入っていた）
    rod([*p, H], [*q, under_roof(*q)], 10, L_NET, STEEL)
# 輪を東の柱へ突っ張る水平材（輪の東の端 → 東の壁）
pe = c_net + np.array(X(nt['u'], 0.0) - c_net) / np.linalg.norm(X(nt['u'], 0.0) - c_net) * rg['outer_r'] * 1000
rod([*pe, H - 60], [*X(nt['u'], 0.15), H - 60], 40, L_NET, STEEL)   # 柱の内面（＝壁の内面、東から0.15）で止める（設計監修10-23）
# 輪とキャットウォークをつなぐ材（10-27、監修の略算）：網の吊り橋が輪を北西へ引く力（満員 約8.4 kN、u の向き 約7.8）を、東の柱の弱い向きに
# 掛けず、キャットウォーク（突っ張り）→ 北の段 → 踊り場（北の壁・北西の斜めの面に固める）→ 吊り橋 → 輪 の閉じた輪で受ける。u42〜45 の東寄り。
_bl = P['support'].get('bridge_loop', {}); pc_ = X(_bl.get('u', 44.4), cw['inset'] + cw['width'] - 0.05)
pr_ = c_net + (pc_ - c_net) / np.linalg.norm(pc_ - c_net) * rg['outer_r'] * 1000
rod([*pr_, H - 60], [*pc_, H - 60], 40, L_NET, STEEL)
# ---------------------------------------------------------------- はしご（踊り場へ、段 200）
la = P['ladder']; b0 = X(*la['base']); b1 = X(*la['top']); dl = (b1 - b0) / np.linalg.norm(b1 - b0); nl = np.array([-dl[1], dl[0]]) * la['width'] * 500
zl = la['h'] * 1000
for s in (1, -1):
    rod([*(b0 + nl * s), 0], [*(b1 + nl * s), zl], 25, L_CW, WOOD)
for k in range(1, int(round(la['h'] / la['rung']))):
    t = k * la['rung'] / la['h']; c = b0 + (b1 - b0) * t
    rod([*(c + nl), zl * t], [*(c - nl), zl * t], 15, L_CW, WOOD)
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
# ---------------------------------------------------------------- ひだ
def face_w(u):
    ln = LineString([xy(u, -0.9), xy(u, -30)]); x = ln.intersection(WS.exterior)
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
K.prism(WSi.difference(WSi.buffer(-rb['depth'] * 1000, join_style=1)).intersection(RWw(rb['u0'], rb['u1'], 6.5, 20)), 0.0, 350.0, L_HD)
nw = P['north_window']
K.prism(RWw(51.0 - 0.15 - nw['seat_d'], 51.0 - 0.15, nw['w0'], nw['w1']).intersection(WNi), 0.0, nw['seat_h'] * 1000, L_HD)
# ---------------------------------------------------------------- 天井扇（中心は東から1.2：羽根の先と壁の内面のあいだ約0.45。設計監修10-23）
fn = P['fans']
for u in fn['u']:
    c = X(u, fn['w'])
    K.prism(Point(c).buffer(fn['d'] * 500, resolution=16), fn['h'] * 1000 - 40, fn['h'] * 1000, L_FAN)
    rod([*c, fn['h'] * 1000], [*c, under_roof(*c)], 15, L_FAN, (90, 90, 90))

OUT = os.path.join(ROOT, 'model', 'sodachiya_play_layers.3dm')
out.Write(OUT, 8); print('written', OUT, len(out.Objects))
