"""遊戯室　提出用の図（A1 の 5 枚目の枠 290×230 mm に 1/100 の実寸で貼る）。遊戯室の担当。
平面 1/100（FL+1.2 で切る、上の遊具は淡く）＋縦の断面 1/100（東から 4.3 で切って西を見る）＋凡例。
断面に断熱の帯（屋根 150・外壁 100・床 50、仮）と 2 階の会議室の室内窓。
寸法は data/play.json、建物は model/sodachiya_exact_mesh.3dm と data/wnew.pkl。
出力：out/sodachiya_play_present.pdf・.png（290×230 mm）
"""
import os, sys, math, json, pickle, numpy as np, rhino3dm as r
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon as MP, Circle, Rectangle, Arc, FancyArrowPatch
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
from uv import xy, uv
from meshkit import RW

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"; FONTB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
for f in (FONT, FONTB): matplotlib.font_manager.fontManager.addfont(f)
plt.rcParams['font.family'] = FontProperties(fname=FONT).get_name()
P = json.load(open(os.path.join(ROOT, 'data', 'play.json'), encoding='utf-8'))
_D = pickle.load(open(os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb')); WN_S = _D['WN']   # 架構の輪郭（遊具はこれに沿う）
WN = _D.get('WS', WN_S)                    # 外皮（外壁・床）。北西の斜めの外壁は後退の線まで（10-23）
WNi = WN.buffer(-150, join_style=2)
src = r.File3dm.Read(os.path.join(ROOT, 'model', 'sodachiya_exact_mesh.3dm'))
SLN = {i: l.Name for i, l in enumerate(src.Layers)}
def objs(prefix):
    for o in src.Objects:
        if SLN[o.Attributes.LayerIndex].startswith(prefix): yield o.Geometry

# ---------------------------------------------------------------- 紙と座標
PW, PH = 290.0, 230.0
fig = plt.figure(figsize=(PW / 25.4, PH / 25.4)); ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, PW); ax.set_ylim(0, PH); ax.set_aspect('equal'); ax.axis('off')
C = dict(ink='#2b2b2b', wall='#3a3a3a', floor='#F5EEE2', up='#B08A5A', upf='#E9D9BE', net='#7A5A36', pit='#E7B48A', mat='#F0C9A4',
         soft='#EFE3CC', tree='#7E5E3C', glass='#8DB9D3', wood='#D8C09A', ins='#9A8FB8', hang='#555555', note='#6b5a3a', sub='#8a8a8a')
def T(x, y, s, pt=5.0, c=None, bold=False, **kw):
    ax.text(x, y, s, fontsize=pt, color=c or C['ink'], fontproperties=FontProperties(fname=FONTB if bold else FONT, size=pt), **kw)
def fillg(g, fc, ec='none', lw=0.3, z=2, hatch=None, alpha=1.0, ls='-'):
    for gg in getattr(g, 'geoms', [g]):
        if gg.is_empty or gg.geom_type != 'Polygon': continue
        ax.add_patch(MP(np.array(gg.exterior.coords), closed=True, fc=fc, ec=ec, lw=lw, zorder=z, hatch=hatch, alpha=alpha, ls=ls))
        for h in gg.interiors:
            ax.add_patch(MP(np.array(h.coords), closed=True, fc=C['floor'] if fc != 'none' else 'none', ec=ec, lw=lw, zorder=z + 0.01, ls=ls))
def lineg(g, lw=0.3, c=None, z=3, ls='-'):
    for gg in getattr(g, 'geoms', [g]):
        if gg.is_empty: continue
        if gg.geom_type == 'Polygon':
            a = np.array(gg.exterior.coords); ax.plot(a[:, 0], a[:, 1], lw=lw, c=c or C['ink'], zorder=z, ls=ls, solid_capstyle='butt')
        else:
            a = np.array(gg.coords); ax.plot(a[:, 0], a[:, 1], lw=lw, c=c or C['ink'], zorder=z, ls=ls, solid_capstyle='butt')

# 平面：世界の mm → 紙の mm（1/100、u の向きを横に、北が右・東が下）
t0 = np.array(xy(41, -0.9)) - np.array(xy(39, -0.9)); ROT = -math.degrees(math.atan2(t0[1], t0[0]))
PX0 = 4.0
def M0(g):
    g = affinity.rotate(g, ROT, origin=(0, 0)); return affinity.scale(g, 0.01, 0.01, origin=(0, 0))
_b = M0(WN.intersection(RW(29.6, 53.0, -1.0, 16.0))).bounds
_bx = M0(RW(29.6, 52.4, -1.0, 14.15)).bounds
DX, DY = PX0 - _bx[0], (PH - 1.0) - _b[3]                 # 左を 4、西の壁の上端を紙の上 1 mm に
def M(g): return affinity.translate(M0(g), DX, DY)
PY0 = M(Point(xy(52.0, -0.9))).coords[0][1]
def Mp(u, w): return np.array(M(Point(xy(u, -0.9 - w))).coords[0])
CLIP = M(RW(29.6, 53.0, -1.2, 16.0))
# 平面の上端を w が最大の所にそろえる
top_w = max(Mp(u, 0)[1] for u in (30, 51))

# ================================================================ 平面 1/100
pl_play = M(WNi.intersection(RW(30.0, 53.0, -0.5, 16.0)))
fillg(pl_play, C['floor'], z=1)
walls = M(WN.difference(WNi).intersection(RW(29.6, 53.0, -0.5, 16.0)))
# 開口：南の口（u 33、東から 0〜1.3 は通路）、北の口（東の面 u 44.1–46.1）、大戸（北西の斜めの面）
nm = P['north_mouth']; door = M(RW(nm['u0'], nm['u1'], -0.3, 0.3))
bd = P['big_door']; bdg = M(RW(bd['u_cols'][0] + 0.45, bd['u_cols'][1] - 0.15, 6.0, 12.0)).intersection(walls.buffer(0.01))
walls = walls.difference(door).difference(bdg)
fillg(walls, C['wall'], z=6)
# 本館の西の壁（すき間 0.9 の向こう）

T(*(Mp(30.3, -0.75)), '本館 ↓', 4.0, '#9a9a9a', va='center')

# 柱（3dm の 22a：FL+1.2 の切り口）
for g in objs('22a_'):
    bb = g.GetBoundingBox()
    if bb.Min.Z > 1200: continue
    u0, _ = uv(bb.Min.X, bb.Min.Y); u1, _ = uv(bb.Max.X, bb.Max.Y)
    if max(u0, u1) < 29.6: continue
    fillg(M(box(bb.Min.X, bb.Min.Y, bb.Max.X, bb.Max.Y)).intersection(M(WN.buffer(60))), '#1e1e1e', z=7)
# はれのまとの壁（u 30）・階段の箱・2 階の床の縁
cv = P['cave']
fillg(M(RW(cv['wall_u'] - 0.06, cv['wall_u'] + 0.06, cv['wall_w0'], 16)).intersection(M(WN)), C['wall'], z=6)
stair = M(RW(30.0, 33.0, 1.3, 4.1))
lineg(stair, 0.6, C['wall'], z=6)
for k in range(1, 12):
    uu = 30.0 + 3.0 * k / 12; lineg(M(LineString([xy(uu, -0.9 - 1.35), xy(uu, -0.9 - 2.5)])), 0.2, '#777777', z=5)
lineg(M(LineString([xy(30.0, -0.9 - 2.5), xy(33.0, -0.9 - 2.5)])), 0.2, '#777777', z=5)
T(*Mp(31.5, 3.3), '階段', 3.6, '#777777', ha='center', va='center', rotation=0)
lineg(M(LineString([xy(33.0, -0.9 - 4.1), xy(33.0, -0.9 - 13.0)])).intersection(M(WNi)), 0.5, '#555555', z=5, ls=(0, (4, 2)))
T(*(Mp(33.15, 10.6)), '2 階の床の縁（上は会議室）', 3.4, '#555555', va='center', rotation=90)
T(*(Mp(30.8, 11.4)), 'はれのま', 4.2, '#9a9a9a', ha='center', va='center')
# 洞：道具入れ・クスノキ・やわらかい床
store = M(RW(cv['u0'] + 0.05, cv['u1'] - 0.05, cv['store'][0], cv['store'][1]).intersection(WNi))
fillg(store, '#E4DccB', C['ink'], 0.3, z=4); T(*store.centroid.coords[0], '道具入れ', 3.6, ha='center', va='center', zorder=8)
st = P['stump']; cst = Mp(st['u'], st['w'])
fillg(M(Point(xy(st['u'], -0.9 - st['w'])).buffer(st['soft_r'] * 1000, resolution=48).intersection(WNi)), C['soft'], z=2.5)
upv = Mp(st['u'] + 1, st['w']) - cst; upv /= np.linalg.norm(upv); eav = Mp(st['u'], st['w'] - 1) - cst; eav /= np.linalg.norm(eav)
for ang, Lb in st['branches']:
    a = math.radians(ang); d = upv * math.cos(a) + eav * math.sin(a)
    ax.plot(*np.array([cst + d * 4, cst + d * Lb * 10]).T, lw=1.6, c=C['tree'], zorder=8, solid_capstyle='round')
    ax.plot(*np.array([cst + d * Lb * 6, cst + d * Lb * 10 + np.array([-d[1], d[0]]) * 3]).T, lw=0.7, c=C['tree'], zorder=8)
ax.add_patch(Circle(cst, st['trunk_r'] * 10, fc='#A78058', ec=C['tree'], lw=0.6, zorder=9))
for rr in (1.5, 3.0, 4.2): ax.add_patch(Circle(cst, rr, fc='none', ec='#7E5E3C', lw=0.25, zorder=9.1))
# デッキ・家具階段・登り壁
dk = P['deck']; fillg(M(RW(dk['u0'], dk['u1'], dk['w0'], dk['w1'])), C['wood'], C['ink'], 0.4, z=4)
ds = P['deck_steps']
for k in range(3):
    ua = ds['u0'] + (ds['u1'] - ds['u0']) * k / 3; ub = ds['u0'] + (ds['u1'] - ds['u0']) * (k + 1) / 3
    fillg(M(RW(ua, ub, ds['w0'], ds['w1'])), C['wood'], C['ink'], 0.3, z=4)
cl = P['climb']; fillg(M(RW(cl['u0'], cl['u1'], -0.02, 0.18)), '#C9A26E', C['ink'], 0.3, z=6.5)
# ひだ：くぼみ・丸いベンチ・窓辺の腰掛け
def face_w(u):
    ln = LineString([xy(u, -0.9), xy(u, -30)]); x = ln.intersection(WN.exterior)
    pts = [x] if x.geom_type == 'Point' else list(getattr(x, 'geoms', []))
    return max(-0.9 - uv(p.x, p.y)[1] for p in pts) - 0.15
N_ = P['niche']
for ua, ub in P['niches']:
    wa = min(face_w(ua), face_w(ub)); fillg(M(RW(ua, ub, wa - P['niche_depth'], wa)), C['wood'], C['ink'], 0.3, z=4)
    fillg(M(RW(ua, ub, wa - N_['seat_d'], wa)), '#E6D4B4', 'none', z=4.1)
rb = P['round_bench']
fillg(M(WNi.difference(WNi.buffer(-rb['depth'] * 1000, join_style=1)).intersection(RW(rb['u0'], rb['u1'], 6.5, 20))), C['wood'], C['ink'], 0.3, z=4)
nw = P['north_window']
fillg(M(RW(51.0 - 0.15 - nw['seat_d'], 51.0 - 0.15, nw['w0'], nw['w1']).intersection(WNi)), C['wood'], C['ink'], 0.3, z=4)
glass = M(RW(50.8, 51.15, nw['w0'], nw['w1'])).intersection(M(WN.difference(WNi)))
fillg(glass, C['glass'], z=6.5)
# ついたて（L 字、吸音）
sc = P['screen']
fillg(M(RW(sc['u0'], sc['u1'], sc['w'], sc['w'] + sc['t'])).union(M(RW(sc['u0'], sc['u0'] + sc['t'], 0.0, sc['w'] + sc['t']))), '#CFC6B4', C['ink'], 0.3, z=5)
# 穴の底・摺鉢ネット
nt, pt, rg = P['net'], P['pit'], P['ring']; cn = Mp(nt['u'], nt['w'])
ax.add_patch(Circle(cn, pt['r'] * 10, fc=C['pit'], ec='#9a6a3a', lw=0.4, zorder=3))
ax.add_patch(Circle(cn, pt['r'] * 10 - 1.0, fc=C['mat'], ec='none', zorder=3.1))
for k in range(24):
    a = 2 * math.pi * k / 24
    ax.plot([cn[0] + 3 * math.cos(a), cn[0] + rg['inner_r'] * 10 * math.cos(a)], [cn[1] + 3 * math.sin(a), cn[1] + rg['inner_r'] * 10 * math.sin(a)], lw=0.2, c=C['net'], zorder=9)
for rr in (6, 10, 14, 18): ax.add_patch(Circle(cn, rr, fc='none', ec=C['net'], lw=0.2, zorder=9))
ax.add_patch(Circle(cn, 3, fc='none', ec=C['net'], lw=0.5, zorder=9))
# 上の遊具（h3.0／h2.0、淡く）
cw = P['catwalk']; sp = cw['steps']
band = WN_S.buffer(-cw['inset'] * 1000, join_style=1).difference(WN_S.buffer(-(cw['inset'] + cw['width']) * 1000, join_style=1))
CAT = band.intersection(unary_union([RW(cw['u_start'], 60, -0.5, 1.6), RW(cw['north_u'], 60, -0.5, cw['west_w'])]))
ring_in = Point(xy(nt['u'], -0.9 - nt['w'])).buffer(rg['inner_r'] * 1000, resolution=64)
RING = Point(xy(nt['u'], -0.9 - nt['w'])).buffer(rg['outer_r'] * 1000, resolution=64).difference(ring_in)
ld = P['landing']; LAND = Point(xy(ld['u'], -0.9 - ld['w'])).buffer(ld['r'] * 1000, resolution=3)
UP = M(CAT.union(RING).union(LAND))
fillg(UP, C['upf'], C['up'], 0.5, z=8, alpha=0.88)
for k in range(sp['n'] + 1):
    ww = sp['w0'] + (sp['w1'] - sp['w0']) * k / sp['n']
    lineg(M(LineString([xy(sp['u'] - 0.45, -0.9 - ww), xy(sp['u'] + 0.9, -0.9 - ww)])).intersection(M(CAT.buffer(1))), 0.35, C['up'], z=8.5)
cld = Mp(ld['u'], ld['w'])
dbr = (cld - cn) / np.linalg.norm(cld - cn); nb = np.array([-dbr[1], dbr[0]]) * P['bridge']['width'] * 5
pa = cn + dbr * rg['outer_r'] * 10; pb = cld - dbr * ld['r'] * 9
ax.add_patch(MP(np.array([pa + nb, pb + nb, pb - nb, pa - nb]), closed=True, fc='#EADFCB', ec=C['net'], lw=0.5, hatch='++++', zorder=8.4))
la = P['ladder']; b0, b1 = Mp(*la['base']), Mp(*la['top']); dl = (b1 - b0) / np.linalg.norm(b1 - b0); nl = np.array([-dl[1], dl[0]]) * la['width'] * 5
ax.add_patch(MP(np.array([b0 + nl, b1 + nl, b1 - nl, b0 - nl]), closed=True, fc=C['wood'], ec=C['ink'], lw=0.3, zorder=8.6))
for k in range(1, 6):
    q = b0 + (b1 - b0) * k / 6; ax.plot(*np.array([q + nl, q - nl]).T, lw=0.3, c=C['ink'], zorder=8.7)
sl = P['slide']; s0, s1 = Mp(*sl['from']), Mp(*sl['to']); dd = (s1 - s0) / np.linalg.norm(s1 - s0); ns = np.array([-dd[1], dd[0]]) * sl['width'] * 5
ax.add_patch(MP(np.array([s0 + ns, s1 + ns, s1 - ns, s0 - ns]), closed=True, fc='#D6E6EF', ec='#3d7fb0', lw=0.4, zorder=8.6))
ax.add_patch(FancyArrowPatch(tuple(s0 + dd * 3), tuple(s1 - dd * 1), arrowstyle='-|>', mutation_scale=5, color='#3d7fb0', lw=0.5, zorder=8.7))
# 吊り材（梁の位置）
for u in (36.3, 39.0, 42.0, 45.0, 48.0):
    ax.add_patch(Circle(Mp(u, cw['inset'] + cw['width'] - 0.05), 0.45, fc=C['hang'], ec='none', zorder=9))
for k in range(rg['rods']):
    a = 2 * math.pi * (k + 0.5) / rg['rods']; rr_ = (rg['inner_r'] + rg['outer_r']) / 2 * 10
    ax.add_patch(Circle(cn + rr_ * np.array([math.cos(a), math.sin(a)]), 0.45, fc=C['hang'], ec='none', zorder=9))
# 大戸（外付けの引き戸 2 枚、外皮の外面に沿って左右へ引く）
c45, c48 = Mp(bd['u_cols'][0] + 0.45, face_w(bd['u_cols'][0] + 0.45) + 0.15), Mp(bd['u_cols'][1] - 0.15, face_w(bd['u_cols'][1] - 0.15) + 0.15)
mid = (c45 + c48) / 2; dv = (c48 - c45); half = np.linalg.norm(dv) / 2; du_ = dv / np.linalg.norm(dv); nd = np.array([dv[1], -dv[0]]) / np.linalg.norm(dv)
if np.dot(nd, mid - cn) < 0: nd = -nd
lw_ = bd.get('leaf', 1.85) * 10
for sgn in (-1, 1):
    a_ = mid + nd * 0.7; b_ = a_ + du_ * sgn * lw_
    ax.add_patch(MP(np.array([a_, b_, b_ + nd * 0.45, a_ + nd * 0.45]), closed=True, fc='#8a6a44', ec=C['ink'], lw=0.3, zorder=7))
    o_ = du_ * sgn * lw_                                                        # 開けた位置（破線）
    ax.add_patch(MP(np.array([a_ + o_, b_ + o_, b_ + o_ + nd * 0.45, a_ + o_ + nd * 0.45]), closed=True, fc='none', ec=C['ink'], lw=0.25, ls=(0, (2, 1.5)), zorder=7))
# 番号
NUM = [(1, Mp(31.2, 9.5)), (2, Mp(37.0, 3.4)), (3, Mp(40.0, 4.6)), (4, Mp(46.2, 4.9)), (5, Mp(48.3, 2.7)),
       (6, Mp(38.0, face_w(38.0) - 1.6)), (7, Mp(44.0, 2.3)), (8, (c45 + c48) / 2 + nd * 4)]
for n, p in NUM:
    ax.add_patch(Circle(p, 2.0, fc='white', ec=C['ink'], lw=0.4, zorder=12)); T(p[0], p[1] - 0.15, str(n), 4.6, ha='center', va='center', zorder=13, bold=True)
# 口の矢印
p = Mp(33.6, 0.65); ax.add_patch(FancyArrowPatch(tuple(p + np.array([-5, 0])), tuple(p), arrowstyle='-|>', mutation_scale=5, color='#B04A2A', lw=0.6, zorder=12))
T(*(p + np.array([-5.5, 1.5])), '南の口', 4.0, '#B04A2A', ha='right', va='bottom')
p = Mp(45.1, 0.2); ax.add_patch(FancyArrowPatch(tuple(p + np.array([0, -3.2])), tuple(p), arrowstyle='-|>', mutation_scale=5, color='#B04A2A', lw=0.6, zorder=12))
T(*(p + np.array([1.2, -2.6])), '北の口（西吹き抜けへ）', 3.8, '#B04A2A', ha='left', va='center')
# 断面の位置
sx0, sx1 = Mp(29.8, 4.3), Mp(51.7, 4.3)
ax.plot(*np.array([sx0, sx1]).T, lw=0.5, c='#B04A2A', ls=(0, (6, 2, 1, 2)), zorder=11)
for p in (sx0, sx1):
    ax.add_patch(FancyArrowPatch(tuple(p), tuple(p + np.array([0, 3.2])), arrowstyle='-|>', mutation_scale=5, color='#B04A2A', lw=0.6, zorder=11))
T(*(sx1 + [1.0, 0]), 'A', 5.0, '#B04A2A', va='center', bold=True)
# 方位・縮尺
ox, oy = 240, 20
ax.add_patch(FancyArrowPatch((ox - 5, oy), (ox + 3, oy), arrowstyle='-|>', mutation_scale=6, color=C['ink'], lw=0.6)); T(ox + 4, oy, '北', 4.4, va='center')
bx, by = 232, 8
for i in range(5): ax.add_patch(Rectangle((bx + i * 10, by), 10, 1.0, fc=C['ink'] if i % 2 == 0 else 'white', ec=C['ink'], lw=0.3))
T(bx, by + 1.8, '0', 3.4); T(bx + 50, by + 1.8, '5 m', 3.4, ha='center')


# ================================================================ 断面 A 1/100（東から 4.3 で切って西を見る）
SW = 4.3
SX0, SY0 = 4.0 + 10 * (-29.6), 5.0          # 紙の x = SX0 + 10u、y = SY0 + 10z
def S(u, z): return (SX0 + 10 * u, SY0 + 10 * z)
def SR(u0, u1, z0, z1, fc, ec='none', lw=0.3, zz=3, hatch=None, alpha=1.0):
    ax.add_patch(Rectangle(S(u0, z0), 10 * (u1 - u0), 10 * (z1 - z0), fc=fc, ec=ec, lw=lw, zorder=zz, hatch=hatch, alpha=alpha))
def SL(pts, lw=0.3, c=None, zz=4, ls='-'):
    a = np.array([S(*p) for p in pts]); ax.plot(a[:, 0], a[:, 1], lw=lw, c=c or C['ink'], zorder=zz, ls=ls, solid_capstyle='butt')
# 屋根の上面（3dm）：東から 4.3 の線で
rp = []
for g in objs('20_'):
    if isinstance(g, r.Mesh):
        rp += [[*uv(g.Vertices[i].X, g.Vertices[i].Y), g.Vertices[i].Z / 1000] for i in range(len(g.Vertices))]
rp = np.array(rp); rp[:, 1] = -0.9 - rp[:, 1]
from scipy.interpolate import griddata
def roof_top(u, w):
    z = griddata(rp[:, :2], rp[:, 2], [(u, w)], method='linear')[0]
    if np.isnan(z): z = griddata(rp[:, :2], rp[:, 2], [(u, w)], method='nearest')[0]
    return float(z)
UN = 50.92                                                  # 北の壁（東から 4.3 の線）
us = np.linspace(30.0, UN, 90); zt = np.array([roof_top(u, SW) for u in us])
INS_R, INS_W, INS_F = 0.15, 0.10, 0.05
roof = np.array([S(u, z) for u, z in zip(us, zt)] + [S(u, z - 0.30) for u, z in zip(us[::-1], zt[::-1])])
ax.add_patch(MP(roof, closed=True, fc='#555555', ec='none', zorder=6))
ins = np.array([S(u, z + INS_R) for u, z in zip(us, zt)] + [S(u, z) for u, z in zip(us[::-1], zt[::-1])])
ax.add_patch(MP(ins, closed=True, fc='white', ec=C['ins'], lw=0.3, hatch='xxxx', zorder=6.5))
# 床・地面・床の下の断熱
SR(29.6, UN + 0.35, -0.30, -0.15, '#555555', zz=6); SR(29.6, UN + 0.35, -0.15 - INS_F - 0.0, -0.15, 'white', C['ins'], 0.3, zz=6.4, hatch='xxxx')
SR(29.6, UN + 0.35, -0.15, 0.0, '#8a8a8a', zz=6)
SL([(29.0, -0.30), (UN + 1.8, -0.30)], 0.6, C['ink'], zz=6)
# 穴の底（東から 4.3 で切る）
off = abs(SW - nt['w']); hc = math.sqrt(max(pt['r'] ** 2 - off ** 2, 0))
SR(nt['u'] - hc, nt['u'] + hc, -pt['depth'] - 0.1, 0.0, 'white', zz=6.6)
SR(nt['u'] - hc, nt['u'] + hc, -pt['depth'] - 0.1, -pt['depth'], '#555555', zz=6.7)
SR(nt['u'] - hc, nt['u'] + hc, -pt['depth'], -pt['depth'] + pt['mat'], C['mat'], C['ink'], 0.3, zz=6.8)
# 北の壁（断熱の帯 100）、はれのまとの壁（u 30、2 階の床まで）
SR(UN, UN + 0.15, -0.15, roof_top(UN, SW) - 0.0, '#555555', zz=6); SR(UN + 0.15, UN + 0.15 + INS_W, -0.15, roof_top(UN, SW) + INS_R, 'white', C['ins'], 0.3, zz=6.4, hatch='xxxx')
SR(29.94, 30.06, 0.0, cv['slab'], '#555555', zz=6)
# 2 階の床（u 21–33）と梁、会議室の北の壁と室内窓
SR(29.6, 33.0, cv['slab'], cv['slab_top'], '#555555', zz=6)
for ub in (30.0, 33.0): SR(ub - 0.09, ub + 0.09, cv['beam_bottom'], cv['slab'], '#7a7a7a', zz=5.8)
z_mt = roof_top(33.0, SW) - 0.30
SR(32.94, 33.06, cv['slab_top'], 4.10, '#555555', zz=6); SR(32.94, 33.06, 6.81, z_mt, '#555555', zz=6)
SR(32.96, 33.04, 4.10, 6.81, C['glass'], zz=6.1)
T(*S(31.4, 3.55), '会議室（2 階）', 4.2, ha='center', va='bottom')
T(*S(33.25, 5.45), '室内窓\n（ブラインド）', 3.6, C['glass'], va='center')
# 西の壁（見え掛かり）：壁の上端、くぼみ・覗き窓・地窓、大戸
wtop = np.array([roof_top(u, face_w(u) + 0.15) - 0.30 for u in us])
SL(list(zip(us, wtop)), 0.4, '#777777', zz=3)
for ua, ub in P['niches']:
    SR(ua, ub, 0.0, N_['top_h'] + N_['board'], C['wood'], '#6b6b6b', 0.3, zz=3.2)
    SR(ua + 0.15, ub - 0.15, N_['seat_h'], N_['top_h'] - 0.05, '#EFE5D2', 'none', zz=3.3)
    pk = N_['peek']; SR((ua + ub) / 2 - pk[2] / 2, (ua + ub) / 2 + pk[2] / 2, pk[0], pk[1], C['glass'], 'none', zz=3.4)
for a_, b_ in zip([n[1] for n in P['niches'][:-1]], [n[0] for n in P['niches'][1:]]):
    SR(a_ + 0.3, b_ - 0.3, 0.0, N_['jimado_h'], C['glass'], 'none', zz=3.2, alpha=0.8)
SR(bd['u_cols'][0] + 0.6, bd['u_cols'][1] - 0.4, 0.0, bd['height'], 'none', '#777777', 0.4, zz=3.2)
T(*S((bd['u_cols'][0] + bd['u_cols'][1]) / 2, bd['height'] - 0.4), '大戸（見え掛かり）', 3.4, '#777777', ha='center', va='top')
# 西館の梁（見え掛かり、2 枚組、u 33〜48）と吊り材
for ub in (36.0, 39.0, 42.0, 45.0, 48.0):
    zt_ = roof_top(ub, SW) - 0.30; zb_ = zt_ - 0.70
    SR(ub - 0.18, ub + 0.18, zb_, zt_, '#C7B697', '#8a7a5a', 0.3, zz=3.6)
# 切り株（クスノキ、見え掛かり）
for ang, Lb in st['branches']:
    a = math.radians(ang); du = Lb * math.cos(a)
    tip_u = st['u'] + du; zt2 = 2.9 if tip_u < cv['u1'] else 2.9 + 0.9 * max(0.0, math.cos(a))
    mid_u = st['u'] + du * 0.55
    SL([(st['u'] + 0.3 * math.cos(a), 0.95), (mid_u, (0.95 + zt2) / 2 + 0.3), (tip_u, zt2)], 1.4, C['tree'], zz=4.2)
SR(st['u'] - st['trunk_r'], st['u'] + st['trunk_r'], 0.0, 1.1, '#A78058', C['tree'], 0.5, zz=4.3)
SR(st['u'] - st['soft_r'], st['u'] + st['soft_r'], 0.0, 0.03, C['soft'], zz=4.0)
T(*S(st['u'], -0.95), 'クスノキ', 4.2, C['tree'], ha='center', va='top', bold=True)
# 摺鉢ネット（見え掛かりの輪郭）と輪（東から 4.3 で切る）
H3 = cw['h']
for side in (-1, 1):
    xs_ = np.linspace(nt['ring_r'], nt['bottom_r'], 24); zz_ = nt['bottom_h'] + (H3 - nt['bottom_h']) * ((xs_ - nt['bottom_r']) / (nt['ring_r'] - nt['bottom_r'])) ** 1.6
    SL([(nt['u'] + side * x_, z_) for x_, z_ in zip(xs_, zz_)], 0.9, C['net'], zz=4.5)
for k in range(1, 6):
    zz0 = nt['bottom_h'] + (H3 - nt['bottom_h']) * k / 6; rr = nt['bottom_r'] + (nt['ring_r'] - nt['bottom_r']) * (k / 6) ** (1 / 1.6)
    SL([(nt['u'] - rr, zz0), (nt['u'] + rr, zz0)], 0.2, C['net'], zz=4.4)
ri, ro = math.sqrt(rg['inner_r'] ** 2 - off ** 2), math.sqrt(rg['outer_r'] ** 2 - off ** 2)
for sgn in (-1, 1):
    a_, b_ = sorted((nt['u'] + sgn * ri, nt['u'] + sgn * ro))
    SR(a_, b_, H3 - 0.15, H3, '#6b4f2e', zz=6)
    xo = nt['u'] + sgn * ro; SL([(xo, H3), (xo, H3 + cw['rail'])], 0.8, '#6b4f2e', zz=6)
    for k in range(1, 4): SL([(xo, H3 + cw['rail'] * k / 4 - 0.02), (xo, H3 + cw['rail'] * k / 4)], 0.3, '#6b4f2e', zz=6)
SL([(nt['u'] - ro, H3 + cw['rail']), (nt['u'] + ro, H3 + cw['rail'])], 0.25, '#6b4f2e', zz=4.6, ls=(0, (1, 1)))
# ハの字の吊り材（輪 → 梁 u 39・42・45）
for k, ub in enumerate((39.0, 42.0, 45.0)):
    for dv_ in (-0.45, 0.45):
        xu = nt['u'] + (ub - nt['u']) * 0.55 + dv_ * 0.6
        SL([(xu, H3 + 0.02), (ub + dv_ * 0.3, roof_top(ub, SW) - 1.0)], 0.35, C['hang'], zz=4.7)
# 輪 → 踊り場：網の吊り橋（見え掛かり）、踊り場 h2.0、北の低い所、すべり台、はしご
H2 = ld['h']; ua_ = nt['u'] + 2.2; ub_ = ld['u'] - ld['r'] * 0.7
tt = np.linspace(0, 1, 30); zb = H3 + (H2 - H3) * tt - 4 * P['bridge']['sag'] * tt * (1 - tt)
SL(list(zip(ua_ + (ub_ - ua_) * tt, zb)), 1.0, C['net'], zz=4.8)
SL(list(zip(ua_ + (ub_ - ua_) * tt, zb + 0.9)), 0.3, C['net'], zz=4.8)
for k in range(1, 9):
    t_ = k / 9; SL([(ua_ + (ub_ - ua_) * t_, zb[int(t_ * 29)]), (ua_ + (ub_ - ua_) * t_, zb[int(t_ * 29)] + 0.9)], 0.2, C['net'], zz=4.8)
SR(ld['u'] - ld['r'], UN, H2 - 0.15, H2, '#6b4f2e', zz=5)
SL([(ld['u'] - ld['r'], H2), (ld['u'] - ld['r'], H2 + cw['rail'])], 0.6, '#6b4f2e', zz=5)
SL([(sl['from'][0], H2), (sl['to'][0], 0.35)], 1.6, '#3d7fb0', zz=5.2)
SL([(sl['to'][0], 0.35), (sl['to'][0] - 0.3, 0.3)], 1.6, '#3d7fb0', zz=5.2)
SL([(la['base'][0], 0.0), (la['top'][0], H2)], 0.8, C['ink'], zz=5.3)
for k in range(1, 10):
    t_ = k / 10; uu = la['base'][0] + (la['top'][0] - la['base'][0]) * t_
    SL([(uu - 0.15, H2 * t_), (uu + 0.15, H2 * t_)], 0.5, C['ink'], zz=5.3)
# 人（3〜5 歳 h1.05、大人 1.6）
def kid(u, z0, h=1.05, c='#555555'):
    hd = h * 0.13; ax.add_patch(Circle(S(u, z0 + h - hd), hd * 10, fc='white', ec=c, lw=0.4, zorder=7))
    SL([(u, z0 + h - 2 * hd), (u, z0 + h * 0.45)], 0.5, c, zz=7)
    SL([(u - 0.12, z0), (u, z0 + h * 0.45), (u + 0.12, z0)], 0.5, c, zz=7)
    SL([(u - 0.15, z0 + h * 0.62), (u, z0 + h * 0.72), (u + 0.15, z0 + h * 0.62)], 0.5, c, zz=7)
kid(nt['u'] - 2.5, H3); kid(nt['u'] + 0.2, -pt['depth'] + pt['mat'], 1.0); kid(st['u'] + 1.2, 0.0); kid(ld['u'] - 0.4, H2); kid(sl['to'][0] + 0.6, 0.4, 0.95); kid(37.4, 0.0, 1.6, '#888888')
# 高さの記号
for z_, s_ in ((0.0, 'FL±0'), (H2, '2.0'), (H3, '3.0'), (cv['slab_top'], '2FL 3.25')):
    SL([(29.75, z_), (30.05, z_)], 0.3, C['ink'], zz=8); T(*S(29.72, z_), s_, 3.4, ha='right', va='center')
T(*S(UN + 0.5, roof_top(UN, SW) + 0.5), '断熱（仮）\n屋根 150・壁 100・床 50', 3.4, C['ins'], va='bottom')
T(*S(29.7, 6.4), 'A', 6.0, '#B04A2A', bold=True, va='bottom')

# ================================================================ 凡例（右の列）
LX = 232.0; ly = PH - 4
T(LX, ly, '平面・断面 A 1/100', 5.6, bold=True, va='top'); ly -= 6.5
T(LX, ly, '平面は FL+1.2 で切る。淡い茶は\nキャットウォーク・輪・踊り場\n（h3.0／2.0）、黒い点は吊り材。\n断面 A は東から 4.3 で切って西を見る', 3.8, C['sub'], va='top', linespacing=1.3); ly -= 18
T(LX, ly, '遊び方', 5.6, bold=True, va='top'); ly -= 7
LEG = ['洞とクスノキ\nてっぺんが 2 階の床に届く', 'デッキと登り壁\n→ キャットウォーク h3.0', '摺鉢ネットと穴の底\nネットからも輪へ登れる',
       '輪 → 網の吊り橋 → 踊り場 h2.0\n空中で一周する', '北の段 3.0→2.0・はしご・\nすべり台（落下 2.0 m 以下）', 'ひだ：くぼみ・丸いベンチ・\n窓辺の腰掛け（モミジを見る）',
       '北の口のついたて（吸音）', '搬入の大戸（外付けの引き戸）']
for i, s_ in enumerate(LEG):
    ax.add_patch(Circle((LX + 2.0, ly - 1.6), 2.0, fc='white', ec=C['ink'], lw=0.4)); T(LX + 2.0, ly - 1.75, str(i + 1), 4.4, ha='center', va='center', bold=True)
    T(LX + 5.5, ly, s_, 4.2, va='top', linespacing=1.25); ly -= 9.5
ly -= 2
T(LX, ly, '安全', 5.4, bold=True, va='top'); ly -= 6
T(LX, ly, '手すりは縦格子 h1.1・すき間 90\n（頭が通らない、横桟なし）\n床の板のすき間 8 未満\n網目 上 90・下 50、ロープ φ18', 4.0, va='top', linespacing=1.3); ly -= 20
T(LX, ly, '支え方', 5.4, bold=True, va='top'); ly -= 6
T(LX, ly, '重さは梁から吊る（梁のあいだを\n通す）。横の揺れは壁とハの字の\n吊り材で止め、吊り橋だけ揺れる。\n梁 90×700×2 は満員でも持つ\n（略算：曲げ 8.0／11.0 N/mm²）', 4.0, va='top', linespacing=1.3); ly -= 26
T(LX, ly, '音', 5.4, bold=True, va='top'); ly -= 6
T(LX, ly, '階段の箱がホールとの衝立。\n北の口に吸音のついたて、\n東の覗き窓は夜だけ開く', 4.0, va='top', linespacing=1.3)

out = os.path.join(ROOT, 'out', 'sodachiya_play_present')
fig.savefig(out + '.pdf'); fig.savefig(out + '.png', dpi=200)
print('written', out, 'plan top', top_w)
