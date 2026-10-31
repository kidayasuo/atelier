"""3歳の保育室（スパン12–13）1/50 平面・断面2つ：分け方のたたき台（本館係、10-24）。
西＝二つのグループの巣（静か、天井は高いまま）、東＝二つで共有。黒・灰＝今の3dm、色＝この案で足すもの。
3dm（model/sodachiya_exact_mesh.3dm）から切り口と見えがかりを取り、案の部材を重ねる。
出力：out/sodachiya_room3_1-50.pdf（A2横）
"""
import os, sys, math, numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'model/build/south'))
from uv import uv
import rhino3dm as r, trimesh
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Rectangle, Circle
from shapely.geometry import Polygon, box, MultiPolygon
from shapely.ops import unary_union

plt.rcParams['font.family'] = 'Noto Sans CJK JP'
# 文字をIllustratorで文字として直せるように（ヒラギノへ置き換える、プレゼンの準備 10-24）、TrueTypeのNotoをType42で埋め込む
import subprocess, matplotlib.font_manager as _fm
_TTF = os.path.expanduser('~/.cache/sodachiya_fonts')
if not os.path.exists(os.path.join(_TTF, 'NotoSansCJKjp-Bold.ttf')):
    subprocess.run([sys.executable, os.path.join(ROOT, 'present', 'tools', 'make_ttf.py'), _TTF], check=False)
if os.path.exists(os.path.join(_TTF, 'NotoSansCJKjp-Bold.ttf')):
    for _f in ('Regular', 'Bold'): _fm.fontManager.addfont(os.path.join(_TTF, f'NotoSansCJKjp-{_f}.ttf'))
    plt.rcParams['font.family'] = _fm.FontProperties(fname=os.path.join(_TTF, 'NotoSansCJKjp-Regular.ttf')).get_name()
    plt.rcParams['pdf.fonttype'] = 42
OUT = os.environ.get('OUT', os.path.join(ROOT, 'out'))
U0, U1 = 32.6, 39.4                     # スパン12–13（架構12・13・14 = u33・36・39）
UA, UB = 34.5, 37.5                     # 断面A（スパン12）・断面B（スパン13）、北を見る
ZP = 1.0                                # 平面の切断の高さ
WALL_V = (1.6, 6.2)                     # 腰の壁（架構の線 u36）
HANG = 2.00                             # 吊り桟の高さ（3段の脚立の2段目に立って目の高さで結べる、子ども中心、ユーザー 10-30。前は 2.40）
ACC, ACC2 = '#1f7a8c', '#c8e6ea'        # 案の色
SKY = '#e9eef2'

# ---------- 3dm を (u, v, z) に ----------
m = r.File3dm.Read(os.environ.get('MESH', os.path.join(ROOT, 'model/sodachiya_exact_mesh.3dm')))
LN = {i: l.Name for i, l in enumerate(m.Layers)}
meshes, beams = [], []
for o in m.Objects:
    g, ln = o.Geometry, LN[o.Attributes.LayerIndex]
    if ln[:2] in ('47', '58', '59', '51') or ln[0] in '06789': continue   # 午睡のコット・床の名前・外構・園庭は描かない
    if isinstance(g, r.Extrusion) and ln.startswith('11b'):
        c = g.Profile3d(0, 0.0)
        P = np.array([[*uv(p.X, p.Y), p.Z / 1000] for p in (c.PointAt(t) for t in np.linspace(c.Domain.T0, c.Domain.T1, 60))])
        if U0 - 0.5 < P[0, 0] < U1 + 0.5: beams.append(P)
        continue
    if not isinstance(g, r.Mesh) or len(g.Vertices) == 0: continue
    bb = g.GetBoundingBox()
    V = np.array([[p.X, p.Y, p.Z] for p in g.Vertices])
    UV = np.array([uv(x, y) for x, y in V[:, :2]])
    if not ((UV[:, 0] > U0 - 3) & (UV[:, 0] < U1 + 3)).any(): continue
    F = []
    for f in g.Faces:
        F.append((f[0], f[1], f[2]))
        if f[2] != f[3]: F.append((f[0], f[2], f[3]))
    meshes.append((ln, np.c_[UV, V[:, 2] / 1000], np.array(F)))

def kind(ln):
    if ln.startswith(('17', '21', '38', '12', '13', '14', '10_', '10p', '20', '50_', '50e', '18')): return 'cut'
    if ln.startswith(('16', '48', '50a', '10t', '19')): return 'glass'
    if ln.startswith('11'): return 'struct'
    return 'thing'

def sec(P, F, o, n):
    try:
        s = trimesh.Trimesh(P, F, process=False).section(plane_origin=o, plane_normal=n)
    except Exception:
        return []
    return [] if s is None else s.discrete

# ---------- 図の枠 ----------
MM = 1 / 25.4
W, H = 594, 420
fig = plt.figure(figsize=(W * MM, H * MM))
S = 20.0                                  # 1/50：1 m = 20 mm
V0, V1 = -1.2, 15.4
def axes(x, y, z0, z1, flip=False):
    a = fig.add_axes([x / W, y / H, (V1 - V0) * S / W, (z1 - z0) * S / H])
    a.set_xlim(V0, V1); a.set_ylim(z0, z1); a.set_aspect('equal'); a.axis('off'); return a
X0 = 22
axP = axes(X0, 262, U0, U1)               # 平面（横＝v 西が左、縦＝u 北が上）
axA = axes(X0, 140, -0.6, 4.9)            # 断面A
axB = axes(X0, 20, -0.6, 4.9)             # 断面B

def T(ax, x, y, s, size=7, ha='left', va='center', c='#222', **kw):
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=c, zorder=20, **kw)
def poly(ax, pts, fc='none', ec='k', lw=0.5, z=3, ls='-', alpha=1):
    ax.add_patch(MP(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, alpha=alpha))
def line(ax, pts, lw=0.5, c='k', z=3, ls='-'):
    pts = np.asarray(pts); ax.plot(pts[:, 0], pts[:, 1], lw=lw, color=c, zorder=z, ls=ls, solid_capstyle='butt')
def shp(ax, g, **kw):
    for p in getattr(g, 'geoms', [g]):
        if p.is_empty or p.geom_type != 'Polygon': continue
        poly(ax, np.array(p.exterior.coords), **kw)

# ---------- 平面 ----------
clipP = box(V0, U0, V1, U1)
cut_pl, gl_pl, thing_pl = [], [], []
for ln, P, F in meshes:
    k = kind(ln)
    for e in sec(P, F, [0, 0, ZP], [0, 0, 1]):
        if len(e) < 3: continue
        pg = Polygon(e[:, [1, 0]]).buffer(0)
        if pg.is_empty: continue
        (gl_pl if k == 'glass' else cut_pl).append(pg)
    if k == 'thing' and ln[:2] in ('37', '46', '40', '39', '49'):
        T3 = P[F]
        lo = T3[:, :, 2].min(axis=1) < ZP
        tri = [Polygon(t[:, [1, 0]]) for t in T3[lo] if Polygon(t[:, [1, 0]]).area > 1e-6]
        if tri: thing_pl.append((ln, unary_union(tri).buffer(0.002)))
cut = unary_union(cut_pl).intersection(clipP)
shp(axP, cut, fc='#3a3a3a', ec='k', lw=0.4, z=6)
shp(axP, unary_union(gl_pl).intersection(clipP), fc='#bfd7ea', ec='#4a6a80', lw=0.3, z=6)
for ln, g in thing_pl:
    shp(axP, g.intersection(clipP), fc='none', ec='#888', lw=0.35, z=4)
# 上にあるもの（破線）：梁の2枚・ロフトの床
for P in beams:
    u = P[:, 0].mean()
    if U0 < u < U1:
        line(axP, [(0.0, u), (15.0, u)], lw=0.35, c='#888', ls=(0, (6, 3)), z=5)
poly(axP, [(1.68, 36.15), (3.6, 36.15), (3.6, 38.9), (1.68, 38.9)], ec='#555', lw=0.5, ls=(0, (4, 2)), z=5)
T(axP, 2.0, 38.6, 'ロフト（床h1.1、今のまま）', 6, c='#444')

# 案：西の巣2つ・東の共有（塗り）
nestA = box(1.66, 33.06, WALL_V[1], 35.94); nestB = box(1.66, 36.06, WALL_V[1], 38.94)
room = box(1.66, 33.06, 11.9, 38.94)
shared = room.difference(box(1.66, 33.06, WALL_V[1], 38.94))
shp(axP, nestA, fc='#dfe9f2', ec='none', z=1); shp(axP, nestB, fc='#dfe9f2', ec='none', z=1)
shp(axP, shared, fc='#eef3e2', ec='none', z=1)
shp(axP, box(11.9, 33.0, 13.5, 39.0), fc='#f6f1e6', ec='none', z=1)
# 腰の壁 h1.1＋上は格子（架構の線 u36、西の壁から4.6）
T(axP, 1.8, 35.75, '腰の壁h1.1＋上は梁の下まで格子（架構の線の上、長さ4.6）', 6.2, c=ACC)
# 吊り桟 h2.0（南北に、梁と梁のあいだ、v0.9ごと、部屋全体、10-30：東の柱の線の手前 v11.9 まで）。ロフトと家具階段の上は除く
HV = [round(2.0 + 0.9 * k, 2) for k in range(12)]
for v in HV:
    line(axP, [(v, 33.13), (v, 35.87)], lw=0.6, c=ACC, ls=(0, (2, 1.5)), z=7)
    if v > 4.2: line(axP, [(v, 36.13), (v, 38.87)], lw=0.6, c=ACC, ls=(0, (2, 1.5)), z=7)
# 10-30（ユーザー）：ロフトのすぐ脇 v4.2（柵から0.6）に一本、巣Bだけ。家具階段の口（u36.4〜37.2）の両側0.6を除く（u37.8〜38.87）
line(axP, [(4.2, 37.8), (4.2, 38.87)], lw=0.6, c=ACC, ls=(0, (2, 1.5)), z=7)
T(axP, 4.3, 38.2, 'ロフトの子の目の高さに桟（触れない距離0.6）', 5.2, c=ACC)
T(axP, 7.6, 33.35, '吊り桟h2.0（0.9ごと、部屋全体、梁から吊る。ロフトと家具階段の上は除く）', 5.8, c=ACC)
# 布の天蓋（スパン12の巣）。10-31（ユーザー）：東へ桟二つ分（v3.8〜7.4）、しずかな角の上を空け、先生の席が下に入る
poly(axP, [(3.8, 33.4), (7.4, 33.4), (7.4, 35.6), (3.8, 35.6)], fc='none', ec=ACC, lw=0.8, ls=(0, (1, 1.2)), z=7)
T(axP, 3.95, 35.35, '布の天蓋（吊り桟から）', 6, c=ACC)
# 横木（東、梁の2枚のあいだ φ30＠450）
for u in (33.0, 36.0, 39.0):
    for v in np.arange(7.9, 11.8, 0.45):
        axP.add_patch(Circle((v, u), 0.05, fc=ACC, ec='none', zorder=8))
T(axP, 8.6, 36.35, '横木φ30＠450（梁の2枚のあいだ、光の筋の下の影）', 5.8, c=ACC)
# ロフトの下の巣
T(axP, 2.0, 37.1, 'ロフトの下の巣（h1.1、こどもだけ）', 6, c=ACC)
T(axP, 6.1, 34.0, '先生の席（巣Aの南の壁）', 6, c=ACC)
T(axP, 6.65, 33.9, '移動式の低い腰壁（棚h0.7）', 5.8, c=ACC)
T(axP, 6.65, 37.4, '移動式の低い腰壁', 5.8, c=ACC)
# 区域の名前
area = lambda g: g.area
T(axP, 3.9, 34.2, '巣A', 9, ha='center', c='#2b4a66', weight='bold')
T(axP, 3.9, 33.75, f'{area(nestA):.1f}m²・10人', 6.5, ha='center', c='#2b4a66')
T(axP, 4.8, 37.75, '巣B', 9, ha='center', c='#2b4a66', weight='bold')
T(axP, 4.8, 37.35, f'{area(nestB):.1f}m²・10人', 6.5, ha='center', c='#2b4a66')
T(axP, 9.0, 37.9, 'ふたつのクラスの共有', 9, ha='center', c='#4b5e2a', weight='bold')
T(axP, 9.0, 37.45, f'{area(shared):.1f}m²（集まる・食べる・寝る）', 6.5, ha='center', c='#4b5e2a')
T(axP, 12.7, 37.9, '内縁側', 7, ha='center', c='#7a6a4a')
T(axP, 0.7, 36.0, '西吹き抜け\n（先生の道）', 6.5, ha='center', c='#555')
T(axP, 14.3, 36.0, '外縁側', 6.5, ha='center', c='#7a6a4a')
for u, s in ((33.0, '12'), (36.0, '13'), (39.0, '14')):
    T(axP, -1.1, u, f'架構{s}', 6, c='#666')
for u in (UA, UB):
    line(axP, [(-0.9, u), (-0.5, u)], lw=1.2, c='k'); line(axP, [(15.0, u), (15.4, u)], lw=1.2, c='k')
    axP.annotate('', xy=(-0.7, u + 0.45), xytext=(-0.7, u), arrowprops=dict(arrowstyle='-|>', lw=0.6, color='k'))
T(axP, -0.6, UA - 0.25, 'A', 8, weight='bold'); T(axP, -0.6, UB - 0.25, 'B', 8, weight='bold')
T(axP, V0, U1 + 0.45, '平面　1/50（床から1.0で切る。灰の破線＝上の梁の2枚、色の破線＝吊り桟）　西が左、北が上', 9, weight='bold')

# ---------- 断面 ----------
def section(ax, U, title):
    cut_s, gl_s = [], []
    for ln, P, F in meshes:
        k = kind(ln)
        for e in sec(P, F, [U, 0, 0], [1, 0, 0]):
            if len(e) < 3: continue
            pg = Polygon(e[:, 1:]).buffer(0)
            if pg.is_empty: continue
            if k == 'glass': gl_s.append(pg)
            elif k == 'thing': shp(ax, pg, fc='white', ec='#555', lw=0.4, z=5)
            else: cut_s.append(pg)
    clip = box(V0, -0.6, V1, 4.9)
    shp(ax, unary_union(cut_s).intersection(clip), fc='#3a3a3a', ec='k', lw=0.4, z=6)
    shp(ax, unary_union(gl_s).intersection(clip), fc='#bfd7ea', ec='#4a6a80', lw=0.3, z=6)
    # 見えがかり：北の架構の梁（u が U より北でいちばん近い架構）
    fr = 3 * math.ceil(U / 3)
    for P in beams:
        if abs(P[:, 0].mean() - fr) < 0.2:
            poly(ax, P[:, 1:3], fc='#e4e4e4', ec='#777', lw=0.35, z=2); break
    # 見えがかりの家具（U から北の架構まで）
    for ln, P, F in meshes:
        if kind(ln) != 'thing' and not ln.startswith('11a'): continue
        c = P[F].mean(axis=1)
        sel = (c[:, 0] > U) & (c[:, 0] < fr + 0.2) & (c[:, 1] > V0) & (c[:, 1] < V1)
        if not sel.any(): continue
        tri = [Polygon(t[:, 1:]) for t in P[F][sel] if Polygon(t[:, 1:]).area > 1e-6]
        if tri: shp(ax, unary_union(tri).buffer(0.002), fc='#f4f4f4', ec='#9a9a9a', lw=0.3, z=3)
    line(ax, [(V0, -0.3), (V1, -0.3)], lw=0.8)
    T(ax, V0, 4.75, title, 9, weight='bold')
    T(ax, 14.9, -0.42, 'GL', 6, c='#555'); T(ax, 0.15, 0.12, 'FL', 6, c='#555')

beam_bot = lambda v: 3.335 - (v - 0.784) * (3.335 - 2.471) / (11.144 - 0.784)
roof_bot = lambda v: 3.995 - v / 12

# 断面A：スパン12（巣A：高く開けた静けさ）
section(axA, UA, '断面A　1/50（スパン12、北を見る）：巣Aは天井を張らず高いまま、低さは布の天蓋で')
for v in HV:
    axA.add_patch(Rectangle((v - 0.02, HANG - 0.02), 0.04, 0.04, fc=ACC, ec='none', zorder=8))
    line(axA, [(v, HANG), (v, beam_bot(v))], lw=0.3, c=ACC, z=7)
vv = np.linspace(3.8, 7.4, 60)
for sag, ls, lab, lx in ((0.15, '-', 'ふだん（約1.8〜1.95）', 6.55), (0.7, (0, (3, 2)), '午睡（低く下ろす）', 6.75)):
    # 10-30：ふだんは 3dm と同じく吊り桟ごとに 1.95 から 1.8 へたるむ（0.9ごと）。午睡は 1.95 から一つの弧で下ろす
    zz = (HANG - 0.05 - sag * np.abs(np.sin(np.pi * (vv - 3.8) / 0.9))) if ls == '-' else (HANG - 0.05 - sag * np.sin(np.pi * (vv - 3.8) / 3.6) ** 0.8)
    line(axA, np.c_[vv, zz], lw=1.1 if ls == '-' else 0.8, c=ACC, ls=ls, z=8)
    T(axA, lx, HANG - 0.05 - sag - 0.13, lab, 6, ha='center', c=ACC)
# 吸音（垂木のあいだ、巣の上）
vs = np.linspace(1.7, WALL_V[1], 2)
poly(axA, [(1.7, roof_bot(1.7)), (WALL_V[1], roof_bot(WALL_V[1])), (WALL_V[1], roof_bot(WALL_V[1]) - 0.12), (1.7, roof_bot(1.7) - 0.12)],
     fc=ACC2, ec=ACC, lw=0.4, z=7)
T(axA, 4.0, roof_bot(4.0) + 0.28, '垂木のあいだに吸音（木毛板）', 6, ha='center', c=ACC)
# 越屋根の光
for x0, x1 in ((0.2, 2.6), (0.7, 3.4), (1.2, 4.2)):
    axA.annotate('', xy=(x1, 1.0), xytext=(x0, 4.35), arrowprops=dict(arrowstyle='-|>', lw=0.5, color='#d9a400', alpha=0.8), zorder=9)
T(axA, 1.75, 1.75, '越屋根の光（朝は直射、\nあとはルーバーの拡散光）', 5.8, c='#a07800')
# 腰の壁（見えがかり、u36）＋格子
poly(axA, [(WALL_V[0], 0), (WALL_V[1], 0), (WALL_V[1], 1.1), (WALL_V[0], 1.1)], fc=ACC2, ec=ACC, lw=0.5, z=4)
for v in np.arange(WALL_V[0] + 0.15, WALL_V[1], 0.15):
    line(axA, [(v, 1.1), (v, beam_bot(v))], lw=0.25, c=ACC, z=4)
T(axA, WALL_V[1] + 0.1, 0.6, '腰の壁h1.1、上は格子（奥、架構の線）', 6, c=ACC)
# 横木（梁の2枚のあいだ、東）
for v in np.arange(7.9, 11.8, 0.45):
    axA.add_patch(Circle((v, beam_bot(v) + 0.1), 0.025, fc=ACC, ec='none', zorder=8))
T(axA, 9.8, beam_bot(9.8) - 0.18, '横木（梁の2枚のあいだ、光の筋の下の影）', 5.5, ha='center', c=ACC)
# 吊り桟の説明・寸法
T(axA, 6.6, HANG + 0.12, f'吊り桟h{HANG:.1f}', 6, c=ACC)
T(axA, 6.6, 1.62, '吊り桟h2.0：3段の脚立の2段目（約0.55）に立って\n目の高さで結べる。子ども中心、部屋全体でそろえる', 5.5, c=ACC)
for v, lab in ((1.75, f'{roof_bot(1.75):.1f}'), (WALL_V[1], f'{roof_bot(WALL_V[1]):.1f}'), (11.8, f'{roof_bot(11.8):.1f}')):
    T(axA, v + 0.05, roof_bot(v) - 0.25, f'屋根の下{lab}', 5.2, c='#777')
# 人
def kid(ax, v, h=1.0, sit=False, c='#6d84a0', z0=0.0):
    hd = 0.11
    top = h * (0.62 if sit else 1.0)
    ax.add_patch(Rectangle((v - 0.12, z0), 0.24, top - 2 * hd, fc=c, ec='none', zorder=9))
    ax.add_patch(Circle((v, z0 + top - hd), hd, fc=c, ec='none', zorder=9))
kid(axA, 3.2, sit=True); kid(axA, 4.1, sit=True); kid(axA, 9.0); kid(axA, 10.0, 1.6, c='#8a8a8a')
T(axA, 3.65, 0.95, '巣A', 8, ha='center', c='#2b4a66', weight='bold')
T(axA, 9.4, 1.8, '共有', 8, ha='center', c='#4b5e2a', weight='bold')

# 断面B：スパン13（巣B：ロフトの上と下）
section(axB, UB, '断面B　1/50（スパン13、北を見る）：巣Bはロフトの上（高く開けた）と下（低くこもる）')
for v in HV:
    if v > 4.2:
        axB.add_patch(Rectangle((v - 0.02, HANG - 0.02), 0.04, 0.04, fc=ACC, ec='none', zorder=8))
        line(axB, [(v, HANG), (v, beam_bot(v))], lw=0.3, c=ACC, z=7)
T(axB, 3.7, 2.55, 'ロフトと家具階段の上は吊り桟なし（子どもが立つと届く）', 5.6, c=ACC)
# 10-30：ロフトのすぐ脇 v4.2 の桟（断面の奥 u37.8〜38.87、見えがかり）。西の端は母屋の下の受け材から吊る
axB.add_patch(Rectangle((4.2 - 0.02, HANG - 0.02), 0.04, 0.04, fc=ACC, ec='none', zorder=8))
line(axB, [(4.2, HANG), (4.2, roof_bot(4.2) - 0.361)], lw=0.3, c=ACC, z=7)
T(axB, 4.3, HANG - 0.28, 'ロフトの子の目の高さに桟（触れない距離0.6）', 5.2, c=ACC)
poly(axB, [(1.7, 0), (3.6, 0), (3.6, 1.1), (1.7, 1.1)], fc=ACC2, ec='none', z=1, alpha=0.8)
T(axB, 2.65, 0.55, 'ロフトの下の巣\nh1.1、こどもだけ', 6, ha='center', c=ACC)
kid(axB, 2.2, 0.95, sit=True, z0=0.0); kid(axB, 2.9, 1.0, z0=1.2); kid(axB, 8.5, sit=True); kid(axB, 9.6, 1.6, c='#8a8a8a')
poly(axB, [(1.7, roof_bot(1.7)), (WALL_V[1], roof_bot(WALL_V[1])), (WALL_V[1], roof_bot(WALL_V[1]) - 0.12), (1.7, roof_bot(1.7) - 0.12)],
     fc=ACC2, ec=ACC, lw=0.4, z=7)
T(axB, 4.4, 2.0, '巣B', 8, ha='center', c='#2b4a66', weight='bold')
T(axB, 9.0, 1.8, '共有', 8, ha='center', c='#4b5e2a', weight='bold')

# ---------- 右の欄 ----------
tx = X0 + (V1 - V0) * S + 14
fig.text(tx / W, 395 / H, '3歳の保育室の分け方', fontsize=15, weight='bold')
fig.text(tx / W, 386 / H, '本館係　2026-10-24　スパン12–13（どの学年も同じ形）', fontsize=8, color='#555')
notes = [
    ('ふたつの巣と共有の場所', [
        '20人を10人ずつの二つのグループに。西の半分を架構の線（u36）で',
        '分けて、それぞれの「巣」に。東の半分は二つで一緒に使う。',
        '同じ部屋を左右に並べず、みんなの場所 → 自分たちの場所と',
        '奥へ入っていく。隣の便所・倉庫のスパンも隣の学年と共有。']),
    ('西は静か、でも天井は張らない', [
        '・梁と梁のあいだは東から越屋根へ空気が上る換気の道。',
        '　西に天井を張るとその出口をふさぐ。',
        '・西は建物でいちばん高く、越屋根の光が落ちる所。',
        '　「高くて明るくて静か」＝森の中、お堂の落ち着き。']),
    ('低さは物で', [
        '・巣A：吊り桟（h2.0）から布の天蓋（しずかな角の上は空け、東へ）。ふだんは約1.8〜1.95、',
        '　午睡は低く下ろす。先生が自分で吊り替えられる。',
        '・巣B：今のロフトの下（h1.1）がこどもだけの巣、',
        '　ロフトの上は高く開けた場所。一つの西に二つの静けさ。']),
    ('静けさは音で', [
        '・巣の上の垂木のあいだに吸音（木毛板）。',
        '・巣の床はやわらかく（コルクか畳）。',
        '・腰の壁h1.1と格子で東のにぎやかさから少し離す。',
        '　上は格子なので見通しと光の筋の光は通る。']),
    ('脚立の2段目で目の高さ（子ども中心）', [
        '・吊り桟h2.0を部屋全体に：3段の脚立の2段目（約0.55）に立った先生',
        '　（身長155〜160）の目の高さで結べる。背の高い先生は少しかがむ。',
        '　リボン・布の下端は子どもの手の届く高さより上で止める（首に絡まない）。']),
    ('先生の席と移動式の腰壁', [
        '・先生の机は巣Aの南の壁に沿って、しずかな角の東（巣Aと共有の境、天蓋の下）。',
        '　壁を背にして、巣Aと共有を横から見守る（巣Bは腰の壁の格子ごし）。',
        '・移動式の低い腰壁2台（1.2×0.35×h0.7、両面の棚）：',
        '　共有に島として置き、8の字に回れる。午睡は囲い、行事は端へ。']),
    ('ロフト（巣B）', [
        '・床の上端h1.2、下は1.1：3歳はぎりぎり立て、大人はかがむ。',
        '・手すりh+1.1（縦格子90以下）、家具階段は1段0.2×5。']),
]
y = 372
for h, ls in notes:
    fig.text(tx / W, y / H, h, fontsize=9.5, weight='bold', color=ACC); y -= 6.5
    for s in ls:
        fig.text(tx / W, y / H, s, fontsize=7.6, color='#222'); y -= 5.0
    y -= 3.5
# 凡例
y -= 2
fig.patches.append(Rectangle((tx / W, y / H), 8 / W, 4 / H, transform=fig.transFigure, fc='#3a3a3a', ec='k', lw=0.3))
fig.text((tx + 11) / W, (y + 1) / H, '今の3dm（切り口）　灰の線＝今の家具・見えがかり', fontsize=7)
y -= 7
fig.patches.append(Rectangle((tx / W, y / H), 8 / W, 4 / H, transform=fig.transFigure, fc=ACC2, ec=ACC, lw=0.6))
fig.text((tx + 11) / W, (y + 1) / H, 'この案で足したもの（3dmのスクリプトに入れた、更新係の作り直し待ち）', fontsize=7, color=ACC)
y -= 7
for fc, lab in (('#dfe9f2', '巣（静か）'), ('#eef3e2', '共有'), ('#f6f1e6', '内縁側')):
    fig.patches.append(Rectangle((tx / W, y / H), 8 / W, 4 / H, transform=fig.transFigure, fc=fc, ec='none'))
    fig.text((tx + 11) / W, (y + 1) / H, lab, fontsize=7); y -= 6
fig.text(tx / W, (y - 4) / H, '面積は壁芯でなく床の上の概算（m²）。保育室全体は面積表の3歳（約60m²）。', fontsize=6.5, color='#666')

os.makedirs(OUT, exist_ok=True)
fig.savefig(os.path.join(OUT, 'sodachiya_room3_1-50.pdf'))
fig.savefig(os.path.join(OUT, 'sodachiya_room3_1-50.png'), dpi=110)
print('ok', round(nestA.area, 1), round(nestB.area, 1), round(shared.area, 1))
