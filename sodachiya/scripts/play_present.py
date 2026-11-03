"""遊戯室　提出用の図（A1 の 5 枚目の枠 290×230 mm に 1/100 の実寸で貼る）。遊戯室の担当。
平面 1/100（FL+1.2 で切る、上の遊具は淡く）＋縦の断面 A 1/100（東から 4.3 で切って西を見る）＋凡例。
11-01（西館係）：今の3dmと決定事項に合わせて描き直した。屋根は model/build/south/roofw.py の面（梁の上端、双一次）から
構成（屋根材・野地 +45〜+109、通気垂木 0〜+45、断熱 −150〜0、構造用合板 t24 −174〜−150、母屋 −324〜−174、梁 90×800×2）で、
床は全面の床下空間（draw100.py の floor_build と同じ構成）、外壁・階段の箱・2 階の床・床梁は3dmの切り口から。
寸法は data/play.json、建物は model/sodachiya_exact_mesh.3dm と data/wnew.pkl。
出力：out/sodachiya_play_present.pdf（290×230 mm、Type42）だけ
"""
import os, sys, math, json, pickle, numpy as np, rhino3dm as r
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon as MP, Circle, Rectangle, Arc, FancyArrowPatch
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union, polygonize
from shapely import affinity
from uv import xy, uv
from meshkit import RW
import roofw
import fonts42                                      # 文字は Noto Sans CJK JP を Type42 で埋め込む

_TTF = os.path.expanduser("~/.cache/sodachiya_fonts")
FONT, FONTB = os.path.join(_TTF, "NotoSansCJKjp-Regular.ttf"), os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")
if not os.path.exists(FONTB):
    FONT, FONTB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
P = json.load(open(os.path.join(ROOT, 'data', 'play.json'), encoding='utf-8'))
_D = pickle.load(open(os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb')); WN_S = _D['WN']   # 架構の輪郭（遊具はこれに沿う）
WN = _D.get('WS', WN_S)                    # 外皮（外壁・床）。北西の斜めの外壁は後退の線まで（10-23）
WNi = WN.buffer(-150, join_style=2)
src = r.File3dm.Read(os.path.join(ROOT, 'model', 'sodachiya_exact_mesh.3dm'))
SLN = {i: l.Name for i, l in enumerate(src.Layers)}
def objs(prefix):
    for o in src.Objects:
        if SLN[o.Attributes.LayerIndex].startswith(prefix): yield o.Geometry
RF = roofw.make(WN_S)                       # 西館の屋根の面（梁の上端、SPANS の双一次）
def roof_top(u, w):
    """屋根の面（梁の上端）の高さ（m）：roofw の面（ベイごとの双一次、屋根の線 roof_line の同じ高さの点を水平に結ぶ）"""
    return RF['roof_f'](*np.ravel(xy(u, -0.9 - w))) / 1000.0

# ---------------------------------------------------------------- 3dm の切り口を読む（11-01、西館係）
def _tris(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
    F = []
    for i in range(len(g.Faces)):
        q = g.Faces[i]; F.append((q[0], q[1], q[2]))
        if q[3] != q[2]: F.append((q[0], q[2], q[3]))
    return V, np.array(F, int)
def _loops(segs, nd):
    segs = [LineString([tuple(np.round(a, nd)), tuple(np.round(b, nd))]) for a, b in segs]
    segs = [s_ for s_ in segs if s_.length > 0]
    return unary_union([p_.buffer(0) for p_ in polygonize(unary_union(segs))]) if segs else Polygon()
def sec_mesh(prefix, w, name=None):
    """3dm のメッシュ（レイヤーの頭 prefix）を、東から w の線（v 一定、背骨の弧に沿う）で切った形（u, z、m）"""
    vc = -0.9 - w; out = []
    for o in src.Objects:
        if not SLN[o.Attributes.LayerIndex].startswith(prefix) or not isinstance(o.Geometry, r.Mesh): continue
        if name and name not in (o.Attributes.Name or ''): continue
        V, F = _tris(o.Geometry)
        U = np.array([uv(x_, y_) for x_, y_, _ in V]); d = U[:, 1] - vc
        if d.min() > 0 or d.max() < 0: continue
        segs = []
        for t in F:
            dd = d[t]
            if dd.min() > 0 or dd.max() < 0: continue
            P_ = []
            for i in range(3):
                j = (i + 1) % 3
                if (dd[i] > 0) != (dd[j] > 0):
                    s_ = dd[i] / (dd[i] - dd[j]); a, b = t[i], t[j]
                    P_.append((U[a, 0] + (U[b, 0] - U[a, 0]) * s_, (V[a, 2] + (V[b, 2] - V[a, 2]) * s_) / 1000))
            if len(P_) == 2: segs.append(P_)
        g = _loops(segs, 5)
        if not g.is_empty: out.append(g)
    return unary_union(out) if out else Polygon()
def sec_ext(prefix, w):
    """3dm の押し出し（梁・床梁の板）を東から w の線で切った板：[(u の小, u の大, z の下, z の上)]（m）"""
    vc = -0.9 - w; out = []
    for o in src.Objects:
        g = o.Geometry
        if not SLN[o.Attributes.LayerIndex].startswith(prefix) or not isinstance(g, r.Extrusion): continue
        us, zs = [], []
        for t in (0.0, 1.0):
            c = g.Profile3d(0, t); dm = c.Domain
            Q = np.array([(*uv(p_.X, p_.Y), p_.Z / 1000) for p_ in (c.PointAt(dm.T0 + (dm.T1 - dm.T0) * k / 2000) for k in range(2001))])
            for a, b in zip(Q[:-1], Q[1:]):
                if (a[1] - vc) * (b[1] - vc) <= 0 and a[1] != b[1]:
                    s_ = (vc - a[1]) / (b[1] - a[1]); us.append(a[0] + (b[0] - a[0]) * s_); zs.append(a[2] + (b[2] - a[2]) * s_)
        if len(us) >= 4 and max(zs) - min(zs) > 0.05: out.append((min(us), max(us), min(zs), max(zs)))
    return out
def plan_mesh(prefix, z):
    """3dm のメッシュを高さ z（m）で水平に切った形（世界の mm）"""
    out = []
    for o in src.Objects:
        if not SLN[o.Attributes.LayerIndex].startswith(prefix) or not isinstance(o.Geometry, r.Mesh): continue
        V, F = _tris(o.Geometry); d = V[:, 2] - z * 1000
        if d.min() > 0 or d.max() < 0: continue
        segs = []
        for t in F:
            dd = d[t]
            if dd.min() > 0 or dd.max() < 0: continue
            P_ = []
            for i in range(3):
                j = (i + 1) % 3
                if (dd[i] > 0) != (dd[j] > 0):
                    s_ = dd[i] / (dd[i] - dd[j]); P_.append(V[t[i], :2] + (V[t[j], :2] - V[t[i], :2]) * s_)
            if len(P_) == 2: segs.append(P_)
        g = _loops(segs, 1)
        if not g.is_empty: out.append(g)
    return unary_union(out) if out else Polygon()
def foot_mesh(prefix):
    """3dm のメッシュの平面の外形（上から見た形、世界の mm）"""
    out = []
    for o in src.Objects:
        if not SLN[o.Attributes.LayerIndex].startswith(prefix) or not isinstance(o.Geometry, r.Mesh): continue
        V, F = _tris(o.Geometry)
        out += [Polygon(V[t, :2]).buffer(1) for t in F if Polygon(V[t, :2]).area > 1]
    return unary_union(out).buffer(-1) if out else Polygon()
def col_outline(g, z=1.2):
    """柱の高さ z（m）の平面の切り口（世界の mm）。鉛直の押し出しは断面の形、横に押し出した板（先細りの柱）は両面の切り口を結ぶ。
    押し出しでなければ外接の箱"""
    if isinstance(g, r.Extrusion):
        def prof(t):
            c = g.Profile3d(0, t); dm = c.Domain
            return np.array([(p_.X, p_.Y, p_.Z) for p_ in (c.PointAt(dm.T0 + (dm.T1 - dm.T0) * k / 400) for k in range(401))])
        ps, pe = g.PathStart, g.PathEnd
        if abs(pe.Z - ps.Z) > math.hypot(pe.X - ps.X, pe.Y - ps.Y):
            q = Polygon(prof(0.0)[:, :2]).buffer(0)
            if q.area > 100: return q
        else:
            pts = []
            for t in (0.0, 1.0):
                Q = prof(t)
                for a, b in zip(Q[:-1], Q[1:]):
                    if (a[2] - z * 1000) * (b[2] - z * 1000) <= 0 and a[2] != b[2]:
                        s_ = (z * 1000 - a[2]) / (b[2] - a[2]); pts.append(tuple(a[:2] + (b[:2] - a[:2]) * s_))
            if len(pts) >= 3:
                q = Polygon(pts).convex_hull
                if q.area > 100: return q
    bb = g.GetBoundingBox(); return box(bb.Min.X, bb.Min.Y, bb.Max.X, bb.Max.Y)

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
pl_play = M(WNi.intersection(RW(29.6, 53.0, -0.5, 16.0)))   # 11-01：スパン10（遊戯室の入り口）と u30 の壁は無し
fillg(pl_play, C['floor'], z=1)
walls = M(WN.difference(WNi).intersection(RW(29.6, 53.0, -0.5, 16.0)))
# 開口：南の口（u 33、東から 0〜1.3 は通路）、北の口（東の面 u 44.1–46.1）、大戸（北西の斜めの面）
nm = P['north_mouth']; door = M(RW(nm['u0'], nm['u1'], -0.3, 0.3))
bd = P['big_door']; bdg = M(RW(bd['u_cols'][0] + 0.45, bd['u_cols'][1] - 0.15, 6.0, 12.0)).intersection(walls.buffer(0.01))
walls = walls.difference(door).difference(bdg)
fillg(walls, C['wall'], z=6)
# 本館の西の壁（すき間 0.9 の向こう）

T(*(Mp(48.4, -0.25)), '本館↓', 4.0, '#9a9a9a', va='top')

# 柱（3dm の 22a：FL+1.2 の切り口、柱の形のまま）
for g in objs('22a_'):
    bb = g.GetBoundingBox()
    if bb.Min.Z > 1200 or bb.Max.Z < 1200: continue
    q = col_outline(g)
    if max(uv(*c_)[0] for c_ in q.exterior.coords) < 29.6: continue
    fillg(M(q).intersection(M(WN.buffer(60))), '#1e1e1e', z=7)
cv = P['cave']
# 階段の箱（11-01、スパン11の中）：箱の壁（芯 u30・u33・v−6.34）と階段の下の倉庫の壁は3dm（24）の FL+1.2 の切り口、側桁は（25）
PLR = M(RW(29.6, 34.5, 0.0, 6.0))
fillg(M(plan_mesh('24_', 1.2)).intersection(PLR), C['wall'], z=6)
fillg(M(plan_mesh('25_', 1.2)).intersection(PLR), '#8a8a8a', z=6)
ST = dict(n_u=(31.62, 32.82), s_u=(30.18, 31.38), w_up=2.14, w_land=(4.18, 5.38), tread=0.26, rise=0.1806, n=8)   # 決定事項_西館の「階段」・3dm（25）
def _tl(u0, u1, w, **kw): lineg(M(LineString([xy(u0, -0.9 - w), xy(u1, -0.9 - w)])), z=5.5, **kw)
w_cut = ST['w_up'] + ST['tread'] * 5.5                       # FL+1.2 の切断線（6段目と7段目のあいだ）
for k in range(ST['n'] + 1):                                 # 北の列（西へ上る）：段鼻、FL+1.2 より上は破線
    w_ = ST['w_up'] + ST['tread'] * k
    _tl(*ST['n_u'], w_, lw=0.25, c='#555555', ls='-' if w_ < w_cut else (0, (2, 1.2)))
    w2 = ST['w_land'][0] - ST['tread'] * k                   # 南の列（踊り場から東へ上る）：みな FL+1.2 より上
    _tl(*ST['s_u'], w2, lw=0.25, c='#555555', ls=(0, (2, 1.2)))
lineg(M(RW(ST['s_u'][0], ST['n_u'][1], *ST['w_land'])), 0.3, '#555555', z=5.5, ls=(0, (2, 1.2)))   # 踊り場 h1.625
for uu in ST['s_u'] + ST['n_u']:
    lineg(M(LineString([xy(uu, -0.9 - (ST['w_up'] - 0.04)), xy(uu, -0.9 - ST['w_land'][0])])), 0.25, '#555555', z=5.5, ls='-' if uu in ST['n_u'] else (0, (2, 1.2)))
cb = [Mp(ST['n_u'][0] - 0.05, w_cut + 0.12), Mp(ST['n_u'][1] + 0.05, w_cut - 0.12)]                # 切断線（ジグザグ）
mid = (cb[0] + cb[1]) / 2; ax.plot([cb[0][0], mid[0] - 0.6, mid[0] + 0.6, cb[1][0]], [cb[0][1], mid[1] + 0.8, mid[1] - 0.8, cb[1][1]], lw=0.3, c='#555555', zorder=5.6)
ua_ = sum(ST['n_u']) / 2; ub_ = sum(ST['s_u']) / 2
ax.plot(*np.array([Mp(ua_, ST['w_up'] + 0.05), Mp(ua_, 4.6), Mp(ub_, 4.6), Mp(ub_, ST['w_up'] + 0.1)]).T, lw=0.35, c='#B04A2A', zorder=5.7)
ax.add_patch(Circle(Mp(ua_, ST['w_up'] + 0.05), 0.5, fc='#B04A2A', ec='none', zorder=5.7))
ax.add_patch(FancyArrowPatch(tuple(Mp(ub_, 2.9)), tuple(Mp(ub_, ST['w_up'] + 0.1)), arrowstyle='-|>', mutation_scale=4, color='#B04A2A', lw=0.35, zorder=5.7))
T(*Mp(ua_, ST['w_up'] - 0.35), '上', 3.4, '#B04A2A', ha='center', va='center')
T(*Mp(30.78, 2.6), '倉庫', 3.2, '#777777', ha='center', va='center')
T(*Mp(31.5, 5.0), '踊り場1.625', 3.0, '#777777', ha='center', va='center')
# 2 階の床（3dm の 23 の外形）：上にある物は破線
F2 = M(foot_mesh('23_'))
lineg(F2.boundary.intersection(M(RW(29.75, 34.5, 0.0, 16.0))).intersection(M(WNi.buffer(-20))), 0.5, '#555555', z=5, ls=(0, (4, 2)))
T(*(Mp(33.38, 11.9)), '2階の床の縁（上は会議室）', 3.4, '#555555', ha='center', va='center', rotation=90)
# 洞：道具入れ・クスノキ・やわらかい床
if 'store' in cv:
    store = M(RW(cv['u0'] + 0.05, cv['u1'] - 0.05, cv['store'][0], cv['store'][1]).intersection(WNi))
    fillg(store, '#E4DccB', C['ink'], 0.3, z=4); T(*store.centroid.coords[0], '道具入れ', 3.6, ha='center', va='center', zorder=8)
st = P['stump']; cst = Mp(st['u'], st['w'])
_soft = foot_mesh('80_')                    # やわらかい床（3dm の 80：φ6.6 を u30・階段の箱の西の面の外・西館の壁で切った形）
if _soft.is_empty: _soft = Point(xy(st['u'], -0.9 - st['w'])).buffer(st['soft_r'] * 1000, resolution=48).intersection(WNi)
fillg(M(_soft), C['soft'], z=2.5)
upv = Mp(st['u'] + 1, st['w']) - cst; upv /= np.linalg.norm(upv); eav = Mp(st['u'], st['w'] - 1) - cst; eav /= np.linalg.norm(eav)
sys.path.insert(0, HERE)
from play_tree import plan_shape, side_shape          # 木は骨格から（10-24、本物のライブオークを参考に）
def _uwmap(g, f):
    gs = [g] if g.geom_type == 'Polygon' else list(g.geoms)
    return [Polygon([f(*c) for c in gg.exterior.coords]) for gg in gs]
for g_ in _uwmap(plan_shape(), lambda u_, w_: tuple(Mp(u_, w_))): fillg(g_, '#C9A87C', C['tree'], 0.3, z=8, alpha=0.85)
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
p = Mp(31.4, 0.75); ax.add_patch(FancyArrowPatch(tuple(p + np.array([-5, 0])), tuple(p), arrowstyle='-|>', mutation_scale=5, color='#B04A2A', lw=0.6, zorder=12))
T(*(p + np.array([-5.5, 1.0])), '東の帯から', 4.0, '#B04A2A', ha='right', va='bottom')      # 11-01：「南の口」の呼び方はやめた（東の帯がそのまま遊戯室へ続く）
p = Mp((nm['u0'] + nm['u1']) / 2, 0.2); ax.add_patch(FancyArrowPatch(tuple(p + np.array([0, -3.2])), tuple(p), arrowstyle='-|>', mutation_scale=5, color='#B04A2A', lw=0.6, zorder=12))
T(*(p + np.array([1.2, -2.6])), '北の口（西吹き抜けへ）', 3.8, '#B04A2A', ha='left', va='center')
# 断面の位置
sx0, sx1 = Mp(29.8, 4.3), Mp(51.1, 4.3)
ax.plot(*np.array([sx0, sx1]).T, lw=0.5, c='#B04A2A', ls=(0, (6, 2, 1, 2)), zorder=11)
for p in (sx0, sx1):
    ax.add_patch(FancyArrowPatch(tuple(p), tuple(p + np.array([0, 3.2])), arrowstyle='-|>', mutation_scale=5, color='#B04A2A', lw=0.6, zorder=11))
T(*(sx1 + [0, 3.4]), 'A', 5.0, '#B04A2A', ha='center', va='bottom', bold=True, zorder=12)
# 方位・縮尺
ox, oy = 240, 20
ax.add_patch(FancyArrowPatch((ox - 5, oy), (ox + 3, oy), arrowstyle='-|>', mutation_scale=6, color=C['ink'], lw=0.6)); T(ox + 4, oy, '北', 4.4, va='center')
bx, by = 232, 8
for i in range(5): ax.add_patch(Rectangle((bx + i * 10, by), 10, 1.0, fc=C['ink'] if i % 2 == 0 else 'white', ec=C['ink'], lw=0.3))
T(bx, by + 1.8, '0', 3.4); T(bx + 50, by + 1.8, '5 m', 3.4, ha='center')


# ================================================================ 断面 A 1/100（東から 4.3 で切って西を見る）
SW = 4.3                                     # 東から 4.3（v −5.2）：階段の箱（踊り場）の中を通る
SX0, SY0 = 7.0 + 10 * (-29.6), 11.0          # 紙の x = SX0 + 10u、y = SY0 + 10z（左に高さの記号、床下が紙に入り、屋根が平面にかからないよう 11.0）
U0 = 29.6
def S(u, z): return (SX0 + 10 * u, SY0 + 10 * z)
def SR(u0, u1, z0, z1, fc, ec='none', lw=0.3, zz=3, hatch=None, alpha=1.0, ls='-'):
    ax.add_patch(Rectangle(S(u0, z0), 10 * (u1 - u0), 10 * (z1 - z0), fc=fc, ec=ec, lw=lw, zorder=zz, hatch=hatch, alpha=alpha, ls=ls))
def SL(pts, lw=0.3, c=None, zz=4, ls='-'):
    a = np.array([S(*p) for p in pts]); ax.plot(a[:, 0], a[:, 1], lw=lw, c=c or C['ink'], zorder=zz, ls=ls, solid_capstyle='butt')
def SG(g): return affinity.affine_transform(g, [10, 0, 0, 10, SX0, SY0])     # (u, z) の形 → 紙
def SF(g, fc, ec='none', lw=0.3, zz=6, hatch=None): fillg(SG(g), fc, ec, lw, z=zz, hatch=hatch)
INS = dict(fc='white', ec=C['ins'], lw=0.3, hatch='xxxx')                    # 断熱の帯の表し方（前の図と同じ）
# --- 3dm の切り口：北の外壁（21）・大和張りの上板（21y）・窓（19）・階段の箱の壁（24）・階段（25）・2 階の床（23）・床梁（22c）・梁（22b）
WALL = sec_mesh('21_', SW).intersection(box(45, -1, 53, 10))
_wl = LineString([(45, 1.0), (53, 1.0)]).intersection(WALL).bounds
UN, UO = _wl[0], _wl[2]                      # 北の外壁の内面・外面（3dm で 50.854・51.000、厚み約146）
YAM = sec_mesh('21y', SW).intersection(box(45, -1, 53, 10))
WIN = sec_mesh('19_', SW).intersection(box(45, -1, 53, 10))
BOXW = sec_mesh('24_', SW).intersection(box(U0, -1, 34, 10))
STR = sec_mesh('25_', SW)
F2 = sec_mesh('23_', SW).intersection(box(U0, -1, 34, 10))
FB = [b_ for b_ in sec_ext('22c_', SW) if b_[1] > U0]
BM = [b_ for b_ in sec_ext('22b_', SW) if b_[1] > U0 and b_[0] < UO and b_[1] - b_[0] < 0.25]
UR = max(c_[0] for g_ in getattr(sec_mesh('20_', SW), 'geoms', [sec_mesh('20_', SW)]) for c_ in g_.exterior.coords)   # 北のけらばの先（3dm、約51.29）
RAF = sec_mesh('20b', SW).intersection(box(U0, -1, 60, 20))   # 通気垂木（@455、切り口）
U_RAF = RAF.bounds[2] + 0.05 if not RAF.is_empty else UN
# --- 屋根：roofw の面（梁の上端）から構成の深さで（決定事項_西館の「屋根の構成」）
us = np.linspace(U0, UR, 500)
def band(d0, d1, u0=U0, u1=UR, w=SW):
    uu = us[(us >= u0) & (us <= u1)]; uu = np.r_[u0, uu, u1]
    zz = np.array([roof_top(u_, w) for u_ in uu])
    return Polygon(list(zip(uu, zz + d1)) + list(zip(uu[::-1], zz[::-1] + d0)))
def _bm_poly(b_):
    u0, u1 = b_[:2]; t0, t1 = roof_top(u0, SW), roof_top(u1, SW)
    return Polygon([(u0, t0), (u1, t1), (u1, t1 - 0.8), (u0, t0 - 0.8)])   # 梁 90×800（鉛直のせい、上端＝屋根の面）
BEAMS = unary_union([_bm_poly(b_) for b_ in BM])
def _strip_lines():
    """光の筋のある架構の線（3dm の 20t の筋のガラスが東から w の線を通る所。決定事項では u24〜48 の 9 本）"""
    fs = set()
    for o in src.Objects:
        if not SLN[o.Attributes.LayerIndex].startswith('20t') or not isinstance(o.Geometry, r.Extrusion): continue
        bb = o.Geometry.GetBoundingBox(); (ua, va), (ub, vb) = uv(bb.Min.X, bb.Min.Y), uv(bb.Max.X, bb.Max.Y)
        f_ = round((ua + ub) / 2 / 3.0) * 3.0
        if min(va, vb) < -0.9 - SW < max(va, vb) and abs((ua + ub) / 2 - f_) < 0.3: fs.add(f_)
    return sorted(fs)
FR_S = [(f_ - RF['HS'], f_ + RF['HS']) for f_ in _strip_lines() if U0 < f_ < UN]   # 光の筋（架構の線の 2 枚の梁のあいだ 180、断面 A は筋を横に切る）
GAPS = unary_union([box(a_, -5, b_, 20) for a_, b_ in FR_S])
GL_ = unary_union([box((a_ + b_) / 2 - 0.15, -5, (a_ + b_) / 2 + 0.15, 20) for a_, b_ in FR_S])   # 筋のガラスの幅 300
U_PLY = max(b_[0] for b_ in BM)               # 合板・断熱は梁のあいだ（北の端の架構の内の板まで）
SF(band(0.045, 0.109).difference(GL_), '#4a4a4a', zz=6.3)                                   # 屋根材と野地 +45〜+109
SF(band(0.0, 0.045, U0, U_RAF).difference(GL_).difference(BEAMS), 'white', '#777777', 0.15, zz=6.25)   # 通気層
if not RAF.is_empty: SF(RAF.difference(GL_), C['wood'], zz=6.3)                            # 通気垂木 60×45
SF(band(-0.150, 0.0, U0, UN).difference(BEAMS).difference(GAPS), zz=6.2, **INS)              # 断熱 150（梁のあいだ）
SF(band(-0.174, -0.150, U0, U_PLY).difference(BEAMS).difference(GAPS), '#E9DCC4', '#8a7a5a', 0.15, zz=6.2)   # 構造用合板 t24（天井に現す）
SF(band(-0.324, -0.174, U0, U_PLY, w=SW + 0.1).difference(BEAMS).difference(GAPS), '#F1E7D3', '#a8987a', 0.2, zz=3.4)   # 母屋 60×150（見え掛かり）
SF(BEAMS, '#C7B697', '#6b5a3a', 0.3, zz=6.4)                                                 # 梁 2 枚組 90×800（切り口）
for a_, b_ in FR_S:                                                                          # 光の筋：立ち上がり 60・ガラス・鏡面のアルミ
    f_ = (a_ + b_) / 2; zt_ = roof_top(f_, SW)
    for c0, c1 in ((f_ - 0.15, a_), (b_, f_ + 0.15)): SR(c0, c1, zt_, zt_ + 0.169, '#4a4a4a', zz=6.35)
    SR(f_ - 0.15, f_ + 0.15, zt_ + 0.169, zt_ + 0.181, C['glass'], '#5a8fb0', 0.2, zz=6.4)
    for e_ in (a_, b_): SL([(e_, zt_ - 0.8), (e_, zt_)], 0.25, '#9fb3c4', zz=6.45)
# --- 北の外壁（21）：杉の大和張り（下板＋上板 21y）・通気層・構造用合板の耐力壁・断熱。柱は外壁の内面に立つ
SF(WALL, zz=6.0, **INS)
SF(WALL.intersection(box(UO - 0.015, -1, UO + 0.1, 10)).union(YAM), C['wood'], zz=6.1)
SF(WALL.intersection(box(UO - 0.045, -1, UO - 0.015, 10)), 'white', zz=6.05)
SF(WALL.intersection(box(UO - 0.057, -1, UO - 0.045, 10)), '#555555', zz=6.1)
lineg(SG(WALL), 0.45, C['ink'], z=6.5)
SF(WIN, C['glass'], zz=6.2)
# --- 階段の箱（11-01）：箱の壁 u30・u33（切り口、屋根の下まで）、踊り場 h1.625 と側桁（切り口）、西の壁（見え掛かり、2 階は会議室の東の壁）
for o in src.Objects:
    if not SLN[o.Attributes.LayerIndex].startswith('24_') or '階段の箱の壁（西' not in (o.Attributes.Name or ''): continue
    bb = o.Geometry.GetBoundingBox(); u0_, _ = uv(bb.Min.X, bb.Min.Y); u1_, _ = uv(bb.Max.X, bb.Max.Y)
    u0_, u1_ = sorted((u0_, u1_))
    if u1_ - u0_ > 0.5: SR(max(u0_, 30.06), min(u1_, 32.94), bb.Min.Z / 1000, bb.Max.Z / 1000, '#ECE7DD', '#9a9a9a', 0.25, zz=3.0)
SF(BOXW, C['wall'], zz=6.2)
SF(STR, '#8a6a44', '#3a3a3a', 0.2, zz=6.2)
SF(F2, '#555555', zz=6.2)
SF(unary_union([box(b_[0], b_[2], b_[1], b_[3]) for b_ in FB]) if FB else Polygon(), '#C7B697', '#6b5a3a', 0.3, zz=6.3)
T(*S(31.5, 1.7), '踊り場1.625', 3.2, '#555555', ha='center', va='bottom')
T(*S(31.5, 0.75), '階段の箱', 3.6, '#777777', ha='center', va='center')
T(*S(31.5, 4.5), '会議室（2階）\n箱の西の壁の向こう', 3.2, '#8a8a8a', ha='center', va='center', linespacing=1.2)
# --- 床：全面の床下空間（draw100.py の floor_build と同じ）。スギ板 t30＋合板 t28／大引 90・鋼製束／床下 有効約450／ベタ基礎の底板 t200（上端 FL−0.6）
FLB, SLT, SLB, RISE, INS_T, INS_W = 0.058, -0.600, -0.800, 0.150, 0.050, 0.900
nt, pt, rg = P['net'], P['pit'], P['ring']; st = P['stump']
off = abs(SW - nt['w']); hc = math.sqrt(max(pt['r'] ** 2 - off ** 2, 0))                      # 穴の底 φ3.2 の切り口
DISH_R = 1.8; hd_ = math.sqrt(max(DISH_R ** 2 - off ** 2, 0))                                  # 底板を下げた皿 φ約3.6
p0, p1 = nt['u'] - hc, nt['u'] + hc
for a_, b_ in ((U0, p0), (p1, UN)):
    SR(a_, b_, -FLB, 0.0, '#3a3a3a', zz=6.2)
    SL([(a_, -FLB - 0.09), (b_, -FLB - 0.09)], 0.15, '#777777', zz=5)                            # 大引の下端（見え掛かり）
slab = unary_union([box(U0, SLB, UO, SLT), box(nt['u'] - hd_, SLB - 0.15, nt['u'] + hd_, SLT - 0.15),
                    box(UO - RISE, SLB, UO, -FLB - 0.09)] + [box(u_ - RISE / 2, SLT, u_ + RISE / 2, -FLB - 0.09) for u_ in (30.0, 33.0)])   # 箱の壁の下の立ち上がり
slab = slab.difference(box(nt['u'] - hd_ + RISE, SLT - 0.15, nt['u'] + hd_ - RISE, SLT + 0.01))
SF(slab, '#B8B8B8', C['ink'], 0.35, zz=6.0)
SF(unary_union([box(UO - RISE - INS_T, SLT, UO - RISE, -FLB - 0.09), box(UO - INS_W, SLB - INS_T, UO, SLB)]), zz=6.05, **INS)   # 基礎断熱（立ち上がりの内側・底盤の外周の下）
SL([(UO, -0.30), (UO + 0.8, -0.30)], 0.6, C['ink'], zz=6)                                    # GL（FL−0.3）
T(*S(UO + 0.1, -0.33), 'GL', 3.0, va='top')
# 穴の底（φ3.2、仕上げ FL−0.45、マット 100）：マットの下の床を下げた底板（皿）に載せる
zp = -pt['depth']
SR(p0, p1, zp - FLB, zp, '#3a3a3a', zz=6.6)
SR(p0, p1, zp, zp + pt['mat'], C['mat'], C['ink'], 0.3, zz=6.8)
SL([(p0, zp - FLB - 0.09), (p1, zp - FLB - 0.09)], 0.15, '#777777', zz=5)
for u_ in np.arange(p0 + 0.3, p1 - 0.1, 0.9): SL([(u_, SLT - 0.15), (u_, zp - FLB - 0.09)], 0.3, '#777777', zz=5)   # 鋼製束（短い）
for u_ in (p0, p1): SR(u_ - 0.015, u_ + 0.015, zp - FLB, 0.0, C['wood'], C['ink'], 0.2, zz=6.7)   # 穴の縁の板
# 切り株の基礎（独立、φ約1.6×深さ約0.6、底板を厚くした所）：断面の線より西にあるので、かくれ線
_zb = max(SLT - 0.6, (0.3 - SY0) / 10)                                                      # 紙の下の縁で止める（基礎の下端 FL−1.2 は紙の外）
for s_ in (-1, 1): SL([(st['u'] + s_ * 0.8, SLT), (st['u'] + s_ * 0.8, _zb)], 0.3, '#6b6b6b', zz=6.9, ls=(0, (2, 1.2)))
for s_ in (-1, 1): SL([(st['u'] + s_ * st['trunk_r'], 0.0), (st['u'] + s_ * st['trunk_r'], SLT)], 0.3, '#6b6b6b', zz=6.9, ls=(0, (2, 1.2)))
T(*S(st['u'] + 0.95, SLT - 0.3), '切り株の基礎φ1.6×深さ0.6（独立、かくれ線）', 2.8, '#6b6b6b', va='center')
# --- 西の壁（見え掛かり）：天井の線（合板の下面）、くぼみ・覗き窓・地窓、大戸
UB = 33.06                                                                                   # 階段の箱の北の壁の北の面（これより南は箱の壁で見えない）
uw = np.linspace(UB, UN, 90)
SL([(u_, roof_top(u_, face_w(u_)) - 0.174) for u_ in uw], 0.4, '#777777', zz=3)
for ua, ub in P['niches']:
    SR(ua, ub, 0.0, N_['top_h'] + N_['board'], C['wood'], '#6b6b6b', 0.3, zz=3.2)
    SR(ua + 0.15, ub - 0.15, N_['seat_h'], N_['top_h'] - 0.05, '#EFE5D2', 'none', zz=3.3)
    pk = N_['peek']; SR((ua + ub) / 2 - pk[2] / 2, (ua + ub) / 2 + pk[2] / 2, pk[0], pk[1], C['glass'], 'none', zz=3.4)
for a_, b_ in zip([n[1] for n in P['niches'][:-1]], [n[0] for n in P['niches'][1:]]):
    SR(a_ + 0.3, b_ - 0.3, 0.0, N_['jimado_h'], C['glass'], 'none', zz=3.2, alpha=0.8)
SR(bd['u_cols'][0] + 0.6, bd['u_cols'][1] - 0.4, 0.0, bd['height'], 'none', '#777777', 0.4, zz=3.2)
T(*S((bd['u_cols'][0] + bd['u_cols'][1]) / 2, bd['height'] - 0.4), '大戸（見え掛かり）', 3.4, '#777777', ha='center', va='top')
# 切り株（クスノキ、見え掛かり）：階段の箱より北に見える所だけ
_vis = box(UB, -1, 60, 20)
for g_ in _uwmap(side_shape(), lambda u_, z_: (u_, z_)):
    g2 = g_.buffer(0).intersection(_vis)
    if not g2.is_empty: fillg(SG(g2), '#C9A87C', C['tree'], 0.4, z=4.2)
SR(UB, st['u'] + st['soft_r'], 0.0, 0.03, C['soft'], zz=4.0)
T(*S(34.4, 3.35), 'クスノキ', 4.2, C['tree'], ha='center', va='bottom', bold=True)
# 摺鉢ネット（見え掛かりの輪郭）と輪（東から 4.3 で切る）
H3 = cw['h']
for side in (-1, 1):
    xs_ = np.linspace(nt['ring_r'], nt['bottom_r'], 24); zz_ = nt['bottom_h'] + (H3 - nt['bottom_h']) * ((xs_ - nt['bottom_r']) / (nt['ring_r'] - nt['bottom_r'])) ** (1 / 1.6)   # 3dm と同じ（下ほど急、ユーザー 10-29）
    SL([(nt['u'] + side * x_, z_) for x_, z_ in zip(xs_, zz_)], 0.9, C['net'], zz=4.5)
for k in range(1, 6):
    zz0 = nt['bottom_h'] + (H3 - nt['bottom_h']) * k / 6; rr = nt['bottom_r'] + (nt['ring_r'] - nt['bottom_r']) * (k / 6) ** 1.6
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
        SL([(xu, H3 + 0.02), (ub + dv_ * 0.3, roof_top(ub, SW) - 0.8)], 0.35, C['hang'], zz=4.7)   # 梁の下端へ
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
kid(nt['u'] - 2.5, H3); kid(nt['u'] + 0.2, -pt['depth'] + pt['mat'], 1.0); kid(st['u'] + 1.65, 0.0); kid(ld['u'] - 0.4, H2); kid(sl['to'][0] + 0.6, 0.4, 0.95); kid(37.4, 0.0, 1.6, '#888888')
# 高さの記号
for z_, s_ in ((0.0, 'FL±0'), (H2, '2.0'), (H3, '3.0')):
    SL([(29.3, z_), (29.6, z_)], 0.3, C['ink'], zz=8); T(*S(29.27, z_), s_, 3.0, ha='right', va='center')
T(*S(29.33, 3.36), '2FL 3.25', 3.0, va='bottom')
T(*S(29.27, 5.2), 'A', 6.0, '#B04A2A', bold=True, ha='right', va='bottom')

# ================================================================ 凡例（右の列）
LX = 232.0; ly = PH - 4
T(LX, ly, '平面・断面A 1/100', 5.6, bold=True, va='top'); ly -= 6.5
T(LX, ly, '平面はFL+1.2で切る。淡い茶は\nキャットウォーク・輪・踊り場\n（h3.0／2.0）、黒い点は吊り材。\n断面Aは東から4.3で切って西を見る\n（階段の箱の踊り場を通る）', 3.8, C['sub'], va='top', linespacing=1.3); ly -= 20
T(LX, ly, '遊び方', 5.6, bold=True, va='top'); ly -= 6.5
LEG = ['洞とクスノキ\nてっぺんが2階の床に届く', 'デッキと登り壁\n→キャットウォークh3.0', '摺鉢ネットと穴の底\nネットからも輪へ登れる',
       '輪→網の吊り橋→踊り場h2.0\n空中で一周する', '北の段3.0→2.0・はしご・\nすべり台（落下2.0 m以下）', 'ひだ：くぼみ・丸いベンチ・\n窓辺の腰掛け（モミジを見る）',
       '北の口のついたて（吸音）', '搬入の大戸（外付けの引き戸）']
for i, s_ in enumerate(LEG):
    ax.add_patch(Circle((LX + 2.0, ly - 1.6), 2.0, fc='white', ec=C['ink'], lw=0.4)); T(LX + 2.0, ly - 1.75, str(i + 1), 4.4, ha='center', va='center', bold=True)
    T(LX + 5.5, ly, s_, 4.2, va='top', linespacing=1.25); ly -= 8.6
ly -= 1.5
T(LX, ly, '安全', 5.4, bold=True, va='top'); ly -= 5.5
T(LX, ly, '手すりは縦格子h1.1・すき間90\n（頭が通らない、横桟なし）\n床の板のすき間8未満\n網目は上90・下50、ロープφ18', 4.0, va='top', linespacing=1.3); ly -= 17.5
T(LX, ly, '支え方', 5.4, bold=True, va='top'); ly -= 5.5
T(LX, ly, '重さは梁から吊る（梁のあいだを\n通す、吊り材M20）。横の揺れは壁と\nハの字の吊り材で止め、吊り橋だけ\n揺れる。吊り橋の引きはキャットウォーク\nとの閉じた輪で受ける。梁90×800×2\n（強い集成材）は満員でも持つ', 4.0, va='top', linespacing=1.3); ly -= 24
T(LX, ly, '音', 5.4, bold=True, va='top'); ly -= 5.5
T(LX, ly, '階段の箱がホールとの衝立。\n北の口に吸音のついたて、\n東の覗き窓は夜だけ開く', 4.0, va='top', linespacing=1.3); ly -= 13
T(LX, ly, '断面の構成', 5.4, bold=True, va='top'); ly -= 5.5
T(LX, ly, '屋根：屋根材・野地64／通気垂木45／\n　断熱150（梁のあいだ）／構造用合板t24\n　（天井に現す）／母屋60×150（現し）\n外壁（約150）：杉の大和張り・通気層・\n　構造用合板（耐力壁）・断熱\n床：スギ板t30＋合板t28／大引90・\n　鋼製束／床下約450／ベタ基礎の\n　底板t200（基礎断熱の内側）', 3.7, va='top', linespacing=1.28)
out = os.path.join(ROOT, 'out', 'sodachiya_play_present')
fig.savefig(out + '.pdf')                  # 図の書き出しは PDF だけ（karuku.md の 2）
print('written', out + '.pdf', 'strips', [round((a_ + b_) / 2, 2) for a_, b_ in FR_S], 'UN UO UR', round(UN, 3), round(UO, 3), round(UR, 3))

# 11-02（ユーザー）：PDF の書体はヒラギノ角ゴシック、Illustrator 用に SVG も（sodachiya/CLAUDE.md）
import subprocess as _sp, sys as _sys
for _t in ('hiragino.py', 'svg_hiragino.py'):
    _sp.run([_sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'present', 'tools', _t), out + '.pdf'], check=True)
