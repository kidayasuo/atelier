"""廊下の本棚と読む場所（4枚目「動線とこどもたちの環境」の下の段、枠 218×143 mm）。本館係、10-28。
3〜5歳の西吹き抜け＝絵本の通り（棚・くぼみ h300＋カーテン）と、北の行き止まり＝本の奥（畳・クッション・格子の引き戸・足入れ・低い窓・読書の庭）。
平面（北が右、西が上）・展開（西を見る、平面の下にそろえる）・断面（南を見る、本の奥を切る）、すべて1/60。
寸法・位置は kettei/honkan.md、scripts/plan04.py（家具）、model/build/shitsu/add_shitsurae.py（高さ）、3dm（model/sodachiya_exact_mesh.3dm：梁・柱・越屋根・天井扇・塀・モミジ）から。
出力：out/sodachiya_present_books.pdf（文字は Type42）・.png
"""
import os, sys, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import fonts42   # noqa: F401  文字は文字のまま（Type42、Noto Sans CJK JP）
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Rectangle, Circle, Ellipse, FancyArrowPatch
OUT = os.environ.get('OUT', os.path.join(ROOT, 'out'))

# ---------------- 3dm から：梁（架構54）・柱（架構54）の形 ----------------
sys.path.insert(0, os.path.join(ROOT, 'model/build/south'))
BEAM54 = COL54 = None
try:
    import rhino3dm as r
    from uv import uv
    _m = r.File3dm.Read(os.environ.get('MESH', os.path.join(ROOT, 'model/sodachiya_exact_mesh.3dm')))
    _LN = {i: l.Name for i, l in enumerate(_m.Layers)}
    for o in _m.Objects:
        g, ln = o.Geometry, _LN[o.Attributes.LayerIndex]
        if not isinstance(g, r.Extrusion) or ln[:3] not in ('11a', '11b'): continue
        c = g.Profile3d(0, 0.0)
        P = np.array([[*uv(p.X, p.Y), p.Z / 1000] for p in (c.PointAt(t) for t in np.linspace(c.Domain.T0, c.Domain.T1, 200))])
        if abs(P[:, 0].mean() - 53.87) < 0.06 and ln.startswith('11b'): BEAM54 = P[:, 1:]
        if abs(P[:, 0].mean() - 53.91) < 0.1 and ln.startswith('11a') and P[:, 1].mean() < 3: COL54 = P[:, 1:]
except Exception as e:
    print('3dm を読めなかった（梁・柱は式で描く）', e)
if BEAM54 is None:     # 予備：決定事項の式（梁の上端＝屋根の面−150、下端は西の壁ぎわ約3.3）
    vv = np.linspace(-0.26, 1.95, 20)
    BEAM54 = np.r_[np.c_[vv, 4.0 - vv / 12], np.c_[vv[::-1], 3.335 - (vv[::-1] - 0.784) * 0.0834]]
if COL54 is None:
    COL54 = np.array([[-0.2, 0], [-0.2, 4.0], [0.2, 3.95], [0.2, 0]])

# ---------------- 紙と縮尺 ----------------
MM = 1 / 25.4
W, H = 218.0, 143.0
S = 1000 / 60                        # 1/60：1 m = 16.67 mm
fig = plt.figure(figsize=(W * MM, H * MM))
fig.patch.set_facecolor('white')

def axes(x0, y0, xl, yl):
    a = fig.add_axes([x0 / W, y0 / H, (xl[1] - xl[0]) * S / W, (yl[1] - yl[0]) * S / H])
    a.set_xlim(*xl); a.set_ylim(*yl); a.set_aspect('equal'); a.axis('off'); return a

# 色（決定事項（共通）の「色」：通り E9DFCF、5歳 6FA96E）
C_CUT = '#2a2a2a'; C_ST = '#E9DFCF'; C_5 = '#6FA96E'; C_WOOD = '#E8D3AE'; C_WOOD2 = '#C9A77C'
C_TATAMI = '#E6DEB4'; C_GLASS = '#BFD7EA'; C_GL_E = '#4A6A80'; C_CUR = '#9B6F8C'; C_LIGHT = '#D9A400'
C_MOSS = '#B9CDA0'; C_MOSS2 = '#7E9D5E'; C_TREE = '#5A7A3A'; C_GREY = '#8A8A8A'; C_TXT = '#222222'
C_KID = '#6D84A0'; C_ADULT = '#8A8A8A'
BOOK = ['#C8574A', '#E0A43A', '#5B8CB8', '#7AA95C', '#B57AA8', '#E4C76B', '#4F7F7A', '#D98B5F']

def poly(ax, pts, fc='none', ec='k', lw=0.4, z=3, ls='-', alpha=1.0, hatch=None):
    ax.add_patch(MP(np.asarray(pts, float), closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls, alpha=alpha, hatch=hatch))
def rect(ax, x0, y0, x1, y1, **kw):
    poly(ax, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], **kw)
def line(ax, pts, lw=0.4, c='k', z=4, ls='-', alpha=1.0):
    p = np.asarray(pts, float); ax.plot(p[:, 0], p[:, 1], lw=lw, color=c, zorder=z, ls=ls, alpha=alpha, solid_capstyle='butt')
def T(ax, x, y, s, size=5.2, ha='left', va='center', c=C_TXT, z=20, **kw):
    ax.text(x, y, s, fontsize=size, ha=ha, va=va, color=c, zorder=z, **kw)
def leader(ax, xy, xyt, s, size=4.8, ha='left', c=C_TXT):
    ax.annotate(s, xy=xy, xytext=xyt, fontsize=size, ha=ha, va='center', color=c, zorder=21,
                arrowprops=dict(arrowstyle='-', lw=0.3, color='#555', shrinkA=0.5, shrinkB=0))
    ax.add_patch(Circle(xy, 0.025, fc='#555', ec='none', zorder=21))
def dim(ax, a, b, off, s, horiz=True, size=4.3, side=1):
    """寸法線：horiz=True なら x 方向（y=off）、False なら y 方向（x=off）"""
    if horiz:
        line(ax, [(a, off), (b, off)], lw=0.3, c='#444', z=19)
        for x in (a, b): line(ax, [(x - 0.04, off - 0.04), (x + 0.04, off + 0.04)], lw=0.5, c='#444', z=19)
        T(ax, (a + b) / 2, off + side * 0.09, s, size, ha='center', va='bottom' if side > 0 else 'top', c='#444')
    else:
        line(ax, [(off, a), (off, b)], lw=0.3, c='#444', z=19)
        for y in (a, b): line(ax, [(off - 0.04, y - 0.04), (off + 0.04, y + 0.04)], lw=0.5, c='#444', z=19)
        T(ax, off + side * 0.07, (a + b) / 2, s, size, ha='left' if side > 0 else 'right', c='#444', rotation=0)

def kid_stand(ax, x, h=1.0, c=C_KID, z=12, face=1):
    """立つ人：胴＋頭（room3_50 と同じ描き方）"""
    hd = 0.11 * h / 1.0 if h < 1.3 else 0.12
    ax.add_patch(Rectangle((x - 0.12 * min(h, 1.2), 0), 0.24 * min(h, 1.2), h - 2 * hd, fc=c, ec='none', zorder=z))
    ax.add_patch(Circle((x, h - hd), hd, fc=c, ec='none', zorder=z))
def kid_sit(ax, x, z0=0.0, h=0.62, c=C_KID, z=12, legs=None):
    """座る子：胴（座から h）＋頭、legs=(dx, dz) で脚を伸ばす向き"""
    hd = 0.105
    ax.add_patch(Rectangle((x - 0.11, z0), 0.22, h - 2 * hd, fc=c, ec='none', zorder=z))
    ax.add_patch(Circle((x, z0 + h - hd), hd, fc=c, ec='none', zorder=z))
    if legs is not None:
        dx, dz = legs
        poly(ax, [(x - 0.07, z0), (x + 0.07, z0 + 0.0), (x + 0.07 + dx, z0 + dz), (x - 0.07 + dx, z0 + dz)], fc=c, ec='none', z=z)

# ======================================================================
# 平面 1/60（北が右、西が上：x＝u、y＝−v）　床から0.5で切る
# ======================================================================
UP0, UP1 = 48.55, 57.45
VP0, VP1 = -2.62, 1.86
PX0, PH = 2.0, (VP1 - VP0) * S
axP = axes(PX0, H - 1.5 - PH, (UP0, UP1), (-VP1, -VP0))
def Pr(u0, u1, v0, v1, **kw): rect(axP, u0, -v0, u1, -v1, **kw)
def Pl(pts, **kw): line(axP, [(u, -v) for u, v in pts], **kw)
def Pt(u, v, s, **kw): T(axP, u, -v, s, **kw)

# 床の塗り：西吹き抜け（通り）・本の奥・5歳の部屋（東の端）・路地
Pr(UP0, 57.19, -0.20, 1.60, fc=C_ST, ec='none', z=0)
Pr(51.06, 57.0, 1.66, VP1, fc=C_5, ec='none', z=0, alpha=0.55)
Pr(49.56, 50.94, 1.66, VP1, fc=C_ST, ec='none', z=0)
Pr(UP0, 49.44, 1.66, VP1, fc='#ECE9E3', ec='none', z=0)          # 教材庫
# 読書の庭（苔）：本館の西の壁・西館の北の面・塀に囲まれた坪庭（3dm の塀 70・柱 72、西館の壁 21 から）
garden = [(51.0, -0.36), (57.34, -0.36), (57.5, -0.57), (56.75, -1.30), (55.38, -2.62), (51.0, -2.62)]
poly(axP, [(u, -v) for u, v in garden], fc=C_MOSS, ec='none', z=0, alpha=0.75)
rng = np.random.default_rng(7)
for _ in range(260):
    u = rng.uniform(51.05, 57.3); v = rng.uniform(-2.6, -0.4)
    if v < -0.36 - (u - 51) * 0 and v > -2.62 and (u < 55.38 or v > -2.62 + (u - 55.38) * (1.32 / 1.37) - 0.02) and not (u > 56.75 and v < -1.3 + (u - 56.75)) :
        axP.add_patch(Circle((u, -v), 0.018, fc=C_MOSS2, ec='none', zorder=1, alpha=0.7))
# 塀（大和張り h1.8）と木戸の柱
Pl([(54.25, -3.55), (56.75, -1.30), (57.5, -0.57)], lw=1.6, c='#8C6A45', z=6)
# 西館（遊戯室）：北東の角の壁と北の窓（3dm 21・19）
Pr(UP0, 49.80, -1.05, -0.90, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)
Pr(50.70, 51.00, -1.40, -0.36, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)
Pr(50.88, 50.96, -2.62, -1.40, fc=C_GLASS, ec=C_GL_E, lw=0.3, z=6)    # 遊戯室の北の窓（腰掛け+300）
Pr(49.80, 50.70, -1.00, -0.93, fc='#F4EFE6', ec='#777', lw=0.3, z=5)   # すき間の倉庫の引き戸
Pr(UP0, 50.88, -2.62, -1.05, fc='#F1EEE8', ec='none', z=0)
Pt(49.6, -1.85, '西館（遊戯室）', size=4.6, ha='center', c='#666')
Pt(49.6, -0.6, 'すき間の倉庫', size=4.0, ha='center', c='#777')
# モミジ（3dm 67：幹 u54.4・v−2.3、樹冠 約φ3）
axP.add_patch(Circle((54.4, 2.3), 1.45, fc='none', ec=C_TREE, lw=0.5, ls=(0, (3, 2)), zorder=7))
axP.add_patch(Circle((54.4, 2.3), 0.09, fc=C_TREE, ec='none', zorder=7))
for k in range(9):
    a = 2 * math.pi * k / 9 + 0.3; rr = 0.95 + 0.35 * ((k * 37) % 5) / 5
    axP.add_patch(Ellipse((54.4 + rr * math.cos(a), 2.3 + rr * math.sin(a)), 0.36, 0.26, angle=math.degrees(a) + 40,
                          fc='none', ec=C_TREE, lw=0.35, zorder=7, alpha=0.8))
Pt(52.15, -2.12, '読書の庭', size=6.2, weight='bold', c='#45632A')
Pt(52.15, -1.78, '苔とモミジ（入らない坪庭）', size=4.4, c='#45632A')

# 外壁（柱の外、v−0.35〜−0.20）と地窓（GLまで、h−300〜600）
for a, b in [(UP0, 52.6), (53.85, 54.15), (56.4, 57.34)]:
    Pr(a, b, -0.35, -0.20, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)
for a, b in [(52.6, 53.85), (54.15, 56.4)]:
    Pr(a, b, -0.35, -0.20, fc='white', ec='none', z=6)
    Pl([(a, -0.35), (a, -0.20)], lw=0.4, c=C_CUT, z=7); Pl([(b, -0.35), (b, -0.20)], lw=0.4, c=C_CUT, z=7)
    Pr(a, b, -0.29, -0.25, fc=C_GLASS, ec=C_GL_E, lw=0.3, z=7)
Pr(57.19, 57.34, -0.35, VP1, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)       # 北の妻壁
# 柱 180×400（架構51・54・57）
for uc in (51.0, 54.0, 57.0):
    if uc < 57.1: Pr(uc - 0.09, uc + 0.09, -0.20, 0.20, fc=C_CUT, ec=C_CUT, lw=0.2, z=8)
Pr(56.91, 57.19, -0.20, 0.20, fc=C_CUT, ec=C_CUT, lw=0.2, z=8)
# 保育室の西の壁（v1.54〜1.66、h2.4）・路地の口・教材庫
Pr(UP0, 49.56, 1.54, 1.66, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)
Pr(49.44, 49.56, 1.54, VP1, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)
Pr(50.94, 57.19, 1.54, 1.66, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)
Pr(50.94, 51.06, 1.54, VP1, fc=C_CUT, ec=C_CUT, lw=0.2, z=6)
Pr(UP0, 49.44, 1.66, VP1, fc='none', ec='none', z=0)
Pr(48.55, 49.38, 1.66, 1.86, fc=C_WOOD, ec='#555', lw=0.25, z=5)     # 教材庫の棚
Pt(50.25, 1.76, '路地へ', size=4.6, ha='center', c='#555')
Pt(54.0, 1.77, '5歳の部屋', size=4.6, ha='center', c='#2F5E2E')

# 絵本の通り：棚（奥行き300、h1.2）＋くぼみ（腰掛け h300、幅1.2・奥行き620）＋カーテン
Pr(UP0, 50.80, 0.08, 0.38, fc=C_WOOD, ec='#444', lw=0.4, z=7)
for u in np.arange(48.75, 50.8, 0.3):
    if not 48.6 <= u <= 49.8: Pl([(u, 0.10), (u, 0.36)], lw=0.15, c='#8C6A45', z=7)
Pr(48.60, 49.80, 0.08, 0.70, fc='#F3E7CF', ec='#444', lw=0.5, z=8)      # くぼみの腰掛け（h300、床より上）
Pr(48.60, 48.63, 0.08, 0.70, fc=C_WOOD2, ec='#444', lw=0.3, z=9)
Pr(49.77, 49.80, 0.08, 0.70, fc=C_WOOD2, ec='#444', lw=0.3, z=9)
axP.add_patch(Ellipse((49.2, -0.45), 0.8, 0.28, fc='#E8D7E6', ec=C_CUR, lw=0.3, zorder=9))   # クッション
Pl([(48.62, 0.72), (49.78, 0.72)], lw=1.3, c=C_CUR, ls=(0, (1.4, 0.9)), z=10)               # カーテン（引いた所）
# 本の奥：格子の引き戸（引き違い2枚、架構51の柱の北の面）
for k, (v0, v1, du) in enumerate([(0.20, 0.92, 0.0), (0.82, 1.54, 0.045)]):
    Pr(51.10 + du, 51.13 + du, v0, v1, fc=C_WOOD2, ec='#5A4128', lw=0.35, z=9)
# 畳（u51.6〜56.9、v0.5〜1.54、h+50）を6枚に
Pr(51.60, 56.90, 0.50, 1.54, fc=C_TATAMI, ec='#555', lw=0.45, z=4)
for k in range(1, 6):
    u = 51.6 + 5.3 * k / 6; Pl([(u, 0.5), (u, 1.54)], lw=0.3, c='#7a6a3a', z=5)
# 足入れ（GLまで300下がる、u52.2〜56.6、壁の内面 v−0.20 から 0.50 まで）
Pr(52.20, 56.60, -0.20, 0.50, fc='#D9E6CF', ec='#444', lw=0.5, z=4)
for u in np.arange(52.3, 56.6, 0.12):
    Pl([(u, 0.44), (u + 0.06, 0.50)], lw=0.15, c='#5d7a46', z=5)
# クッション（3dm 40 の位置）
CUSH = [(51.96, 1.34, .36), (52.2, 1.28, .41), (52.62, 1.2, .45), (52.95, 1.39, .39), (53.04, 1.11, .38), (53.35, 0.77, .45),
        (54.17, 1.25, .45), (54.79, 1.19, .33), (55.33, 1.37, .38), (55.75, 1.07, .45), (55.92, 1.08, .43), (56.12, 0.82, .34)]
for k, (u, v, d) in enumerate(CUSH):
    axP.add_patch(Circle((u, -v), d / 2.2, fc=['#E8D7E6', '#F3E1C7', '#D9E6CF'][k % 3], ec=C_CUR, lw=0.3, zorder=6))
# 上にあるもの（破線）：越屋根の蓋の縁、天井扇 φ1100、梁の2枚
Pl([(UP0, 1.95), (57.45, 1.95)], lw=0.35, c='#5B7FA0', ls=(0, (5, 2.5)), z=11)
for uf in (49.5, 52.5, 55.5):
    axP.add_patch(Circle((uf, -0.8), 0.55, fc='none', ec=C_GREY, lw=0.35, ls=(0, (2, 1.5)), zorder=11))
    axP.add_patch(Circle((uf, -0.8), 0.06, fc=C_GREY, ec='none', zorder=11))
for uc in (51.0, 54.0, 57.0):
    for du in (-0.135, 0.135):
        if uc + du < UP1: Pl([(uc + du, -0.26), (uc + du, 1.6)], lw=0.3, c='#999', ls=(0, (4, 2.5)), z=3)
# 切る線：断面A（u55.0、南を見る）、展開B（v0.9、西を見る）
for v in (-2.45, 1.75):
    Pl([(55.0, v - 0.14), (55.0, v + 0.14)], lw=1.4, c='k', z=15)
axP.annotate('', xy=(54.55, 2.18), xytext=(55.0, 2.18), arrowprops=dict(arrowstyle='-|>', lw=0.5, color='k'), zorder=15)
Pt(55.12, -2.18, 'A', size=6.5, weight='bold')
for u in (48.6, 57.38):
    Pl([(u, 0.9), (u, 0.9)], lw=0, c='k')
Pl([(UP1 - 0.18, 0.9), (UP1 - 0.01, 0.9)], lw=1.4, c='k', z=15)
axP.annotate('', xy=(UP1 - 0.1, -0.45), xytext=(UP1 - 0.1, -0.9), arrowprops=dict(arrowstyle='-|>', lw=0.5, color='k'), zorder=15)
Pt(UP1 - 0.25, -0.62, 'B', size=6.5, weight='bold', ha='right')
# ラベル
Pt(50.05, 0.23, '絵本の棚h1.2', size=4.4, ha='center')
Pt(48.66, 1.2, 'くぼみ\n腰掛けh300・カーテン', size=4.3, c='#6B3F5E')
Pt(54.45, 0.66, '本の奥', size=6.8, ha='center', weight='bold', c='#5A4A20')
Pt(54.45, 0.9, '畳（+50）とクッション', size=4.2, ha='center', c='#5A4A20')
Pt(55.75, 0.17, '足入れ−300（GLまで）', size=4.3, ha='center', c='#34502A')
leader(axP, (51.12, -1.2), (50.98, -1.35), '格子の引き戸', size=4.3, ha='right')
leader(axP, (53.2, 0.27), (53.0, 0.75), '地窓h−300〜600（読書の庭へ）', size=4.3, ha='left')
Pt(50.1, -0.55 - 0.0, '', size=1)
Pt(50.4, 0.72, '絵本の通り\n（西吹き抜け）', size=5.0, ha='center', weight='bold', c='#5A4A20')
T(axP, 52.45, 0.13, '', size=1)
T(axP, 53.0, -1.79, '', size=1)
# 方位（北は u の向きから約8°西）
nx, ny = 56.6, 2.15
ang = math.radians(8.3)
axP.annotate('', xy=(nx + 0.45 * math.cos(ang), ny + 0.45 * math.sin(ang)), xytext=(nx, ny),
             arrowprops=dict(arrowstyle='-|>', lw=0.6, color='k'), zorder=16)
T(axP, nx + 0.52 * math.cos(ang), ny + 0.52 * math.sin(ang), 'N', size=5.5, weight='bold')
T(axP, UP0 + 0.08, -VP0 - 0.17, '平面　1/60　床から0.5で切る（破線＝上の梁・天井扇・越屋根の蓋の縁）', size=5.4, weight='bold', va='top')

# ======================================================================
# 展開B　1/60（v0.9で切って西を見る：x＝u、y＝z）
# ======================================================================
ZE0, ZE1 = -0.36, 2.98
EH = (ZE1 - ZE0) * S
axE = axes(PX0, 1.8, (UP0, UP1), (ZE0, ZE1))
# 西の内壁（白い反射面）を背景に
rect(axE, UP0, 0.0, 57.19, ZE1, fc='#FBFAF7', ec='none', z=0)
# 床（切り口）・北の妻壁（切り口）
rect(axE, UP0, -0.36, 57.19, -0.0, fc='#CFC8BC', ec='none', z=1)
line(axE, [(UP0, 0), (57.19, 0)], lw=0.9, c=C_CUT, z=8)
rect(axE, 57.19, ZE0, 57.34, ZE1, fc=C_CUT, ec=C_CUT, lw=0.2, z=8)
rect(axE, 51.60, 0.0, 56.90, 0.05, fc=C_TATAMI, ec=C_CUT, lw=0.4, z=8)    # 畳（切り口）
# 柱（見えがかり、架構51・54）
for uc in (51.0, 54.0):
    rect(axE, uc - 0.09, 0.0, uc + 0.09, ZE1, fc=C_WOOD, ec='#6b5236', lw=0.35, z=3)
rect(axE, 56.91, 0.0, 57.19, ZE1, fc=C_WOOD, ec='#6b5236', lw=0.35, z=3)
# 地窓（見えがかり：床より上 0〜0.6、下は破線）、足入れ（破線）
for a, b in [(52.6, 53.85), (54.15, 56.4)]:
    rect(axE, a, 0.05, b, 0.6, fc='#DDEAD0', ec=C_GL_E, lw=0.45, z=2)
    for k in range(18):   # 窓の向こうの苔
        x = a + (b - a) * (k + 0.5) / 18
        axE.add_patch(Ellipse((x, 0.1 + 0.05 * (k % 3)), 0.16, 0.08, fc=C_MOSS2, ec='none', alpha=0.5, zorder=2))
    rect(axE, a, -0.30, b, 0.0, fc='none', ec=C_GL_E, lw=0.35, ls=(0, (2, 1.5)), z=9)
rect(axE, 52.2, -0.30, 56.6, 0.0, fc='none', ec='#444', lw=0.4, ls=(0, (3, 2)), z=9)
T(axE, 54.4, -0.18, '足入れ−300（奥、破線）', size=4.2, ha='center', c='#333')
# 棚（見えがかり：h1.2、4段＠300、絵本を面陳と背で）
rect(axE, UP0, 0.0, 50.80, 1.2, fc=C_WOOD, ec='#6b5236', lw=0.45, z=3)
rng = np.random.default_rng(3)
for (a, b) in [(UP0, 48.6), (49.8, 50.8)]:
    for zs in (0.3, 0.6, 0.9):
        line(axE, [(a, zs), (b, zs)], lw=0.35, c='#6b5236', z=4)
    for z0 in (0.02, 0.32, 0.62, 0.92):
        x = a + 0.03
        while x < b - 0.06:
            if z0 >= 0.9 and rng.random() < 0.55:      # 上の段は表紙を見せる（面陳）
                w = 0.2; rect(axE, x, z0, x + w, z0 + 0.25, fc=BOOK[rng.integers(8)], ec='#555', lw=0.2, z=5); x += w + 0.04
            else:
                w = rng.uniform(0.02, 0.05); hh = rng.uniform(0.16, 0.26)
                rect(axE, x, z0, x + w, z0 + hh, fc=BOOK[rng.integers(8)], ec='none', z=5); x += w + 0.005
# くぼみ（腰掛け h300、内の高さ1.0、天板 h1.3）＋カーテン（片側に寄せた所）
rect(axE, 48.60, 0.0, 49.80, 0.30, fc='#F3E7CF', ec='#6b5236', lw=0.45, z=6)
rect(axE, 48.63, 0.30, 49.77, 1.30, fc='#F7EEDC', ec='none', z=4)
rect(axE, 48.60, 0.30, 48.63, 1.34, fc=C_WOOD2, ec='#6b5236', lw=0.3, z=7)
rect(axE, 49.77, 0.30, 49.80, 1.34, fc=C_WOOD2, ec='#6b5236', lw=0.3, z=7)
rect(axE, 48.60, 1.30, 49.80, 1.34, fc=C_WOOD2, ec='#6b5236', lw=0.3, z=7)
for k in range(6):   # くぼみの奥の棚（低い）
    rect(axE, 48.66 + 0.05 * k, 0.32, 48.69 + 0.05 * k, 0.52, fc=BOOK[k], ec='none', z=5)
xs = np.linspace(49.30, 49.76, 40)
cur = [(49.76, 1.30), (49.30, 1.30)] + [(x, 0.31 + 0.02 * math.sin((x - 49.3) * 70)) for x in xs]
poly(axE, cur, fc='#E8D7E6', ec=C_CUR, lw=0.4, z=8)
for x in np.arange(49.36, 49.76, 0.09): line(axE, [(x, 0.33), (x + 0.02, 1.29)], lw=0.25, c=C_CUR, z=9)
line(axE, [(48.62, 1.27), (49.78, 1.27)], lw=0.6, c='#555', z=9)          # カーテンの棒
kid_sit(axE, 48.95, z0=0.30, h=0.60, legs=(0.28, 0.0))
rect(axE, 49.12, 0.52, 49.27, 0.68, fc=BOOK[1], ec='none', z=13)
# 格子の引き戸（切り口、架構51の北）
rect(axE, 51.10, 0.0, 51.175, 2.0, fc=C_WOOD2, ec='#5A4128', lw=0.35, z=8)
# 天井扇（見えがかり、羽根 h2.8・φ1100）
for uf in (49.5, 52.5, 55.5):
    rect(axE, uf - 0.55, 2.80, uf + 0.55, 2.84, fc='#666', ec='none', z=6)
    rect(axE, uf - 0.06, 2.77, uf + 0.06, 2.86, fc='#555', ec='none', z=6)
    line(axE, [(uf, 2.86), (uf, ZE1)], lw=0.6, c='#555', z=6)
# 越屋根からの光（上から）
for x0 in (50.2, 52.0, 53.6, 55.2, 56.4):
    axE.annotate('', xy=(x0 - 0.35, 1.55), xytext=(x0, ZE1 - 0.02),
                 arrowprops=dict(arrowstyle='-|>', lw=0.45, color=C_LIGHT, alpha=0.85), zorder=10)
# 人：本の奥で読む子、棚の前の子と先生
kid_sit(axE, 52.75, z0=0.05, h=0.58)
kid_sit(axE, 53.5, z0=0.05, h=0.60)
kid_sit(axE, 55.6, z0=0.05, h=0.55)
ax_ = axE; ax_.add_patch(Ellipse((56.25, 0.13), 0.55, 0.16, fc=C_KID, ec='none', zorder=12))   # 寝ころぶ子
ax_.add_patch(Circle((56.62, 0.17), 0.1, fc=C_KID, ec='none', zorder=12))
kid_stand(axE, 50.2, 1.05)
kid_stand(axE, 50.62, 1.58, c=C_ADULT)
# 寸法・ラベル
T(axE, 48.62, 1.48, 'くぼみ：腰掛けh300、カーテンで隠れ家に', size=4.4)
T(axE, 49.85, 1.3, '棚h1.2', size=4.3)
T(axE, 48.62, 2.1, '西の壁（内側は白、越屋根の光を返す）', size=4.4, c='#555')
T(axE, 51.25, 2.1, '格子の引き戸h2.0', size=4.4, c='#555')
T(axE, 52.65, 0.86, '地窓の向こうに苔とモミジの根元', size=4.4, c='#34502A')
T(axE, 52.55, 2.6, '天井扇φ1100・h2.8', size=4.4, c='#555')
T(axE, 54.25, 1.85, '越屋根の光（朝は直射、昼はルーバーの拡散光）', size=4.4, c='#A07800')
T(axE, UP0 + 0.08, 2.62, '展開B　1/60（西を見る）', size=5.4, weight='bold', va='top')
T(axE, 57.12, 0.38, 'FL', size=4.2, ha='right', c='#555')

# ======================================================================
# 断面A　1/60（u55.0で切って南を見る：x＝−v（西が右）、y＝z）
# ======================================================================
SX0 = PX0 + (UP1 - UP0) * S + 3.0
VS0, VS1 = 1.86, -1.92           # 左が東、右が西
ZS0, ZS1 = -0.50, 4.78
SH = (ZS1 - ZS0) * S
axS = axes(SX0, H - 1.5 - SH, (-VS0, -VS1), (ZS0, ZS1))
def X(v): return -v
def Sr(v0, v1, z0, z1, **kw): rect(axS, X(v0), z0, X(v1), z1, **kw)
def Sp(pts, **kw): poly(axS, [(X(v), z) for v, z in pts], **kw)
def Sl(pts, **kw): line(axS, [(X(v), z) for v, z in pts], **kw)
def St(v, z, s, **kw): T(axS, X(v), z, s, **kw)
ztop = lambda v: 4.109 - v / 12          # 屋根の上面（ROOF_Z＋RT_TOP）
zbt = lambda v: 4.000 - v / 12           # 梁の上端（ROOF_Z＋RT_BOT）
zply = lambda v: 3.826 - v / 12          # 合板の下
zpur = lambda v: 3.676 - v / 12          # 母屋の下
zlid = lambda v: 4.263 + (1.95 - v) / 12  # 蓋の下面

# 地面（外、GL−300）・苔
Sp([(-0.36, -0.30), (VS1, -0.30), (VS1, ZS0), (-0.36, ZS0)], fc='#E4DED2', ec='none', z=1)
Sl([(-0.36, -0.30), (VS1, -0.30)], lw=0.7, c=C_CUT, z=8)
for k in range(26):
    v = -0.42 - 1.45 * k / 25
    axS.add_patch(Ellipse((X(v), -0.27), 0.12, 0.07, fc=C_MOSS2, ec='none', zorder=9, alpha=0.8))
# モミジ（見えがかり、幹は約1 m 先）
for (v, z, w, h) in [(-1.25, 2.55, 1.2, 0.75), (-1.7, 2.95, 1.0, 0.7), (-1.0, 2.95, 0.7, 0.5), (-1.55, 2.35, 0.8, 0.45)]:
    axS.add_patch(Ellipse((X(v), z), w, h, fc='#C9DDB0', ec=C_TREE, lw=0.35, zorder=2, alpha=0.9))
St(-1.88, 3.42, 'モミジ（幹は奥、約1 m）', size=4.2, ha='right', c='#45632A')
St(-1.88, -0.42, '読書の庭（苔）', size=4.4, ha='right', c='#45632A')
# 床：はだしの床 ±0（スラブ 450）、足入れは GL まで
Sp([(-0.20, -0.30), (0.50, -0.30), (0.50, 0.0), (VS0, 0.0), (VS0, -0.45), (-0.20, -0.45)], fc='#CFC8BC', ec=C_CUT, lw=0.5, z=5)
Sr(-0.20, 0.50, -0.30, -0.27, fc='#D9E6CF', ec=C_CUT, lw=0.3, z=6)
Sr(0.50, 1.54, 0.0, 0.05, fc=C_TATAMI, ec=C_CUT, lw=0.45, z=7)             # 畳 +50
Sr(1.66, VS0, 0.0, 0.02, fc='#D8C7A5', ec=C_CUT, lw=0.3, z=7)
# 西の外壁（切り口）：地窓 h−300〜600、その上は壁、上端は屋根の上面まで
Sr(-0.36, -0.20, 0.60, 4.281, fc=C_CUT, ec=C_CUT, lw=0.2, z=8)
Sr(-0.36, -0.20, ZS0, -0.30, fc=C_CUT, ec=C_CUT, lw=0.2, z=8)
Sr(-0.36, -0.20, -0.30, -0.27, fc='#555', ec='none', z=8)
Sr(-0.36, -0.20, 0.56, 0.60, fc='#555', ec='none', z=8)
Sr(-0.29, -0.25, -0.27, 0.56, fc=C_GLASS, ec=C_GL_E, lw=0.35, z=8)
# 柱（架構54、見えがかり）と梁（架構54、見えがかり）：3dm から
poly(axS, [(X(v), z) for v, z in COL54], fc=C_WOOD, ec='#6b5236', lw=0.35, z=3)
poly(axS, [(X(v), z) for v, z in BEAM54 if v <= VS0 + 0.4], fc='#E9DCC4', ec='#6b5236', lw=0.35, z=3)
# 格子の引き戸（架構51の北、見えがかり）
Sr(0.20, 1.54, 0.0, 2.0, fc='none', ec='#8C6A45', lw=0.4, z=2)
for v in np.arange(0.32, 1.54, 0.12): Sl([(v, 0.03), (v, 1.97)], lw=0.25, c='#A88560', z=2)
for z in (0.6, 1.3): Sl([(0.2, z), (1.54, z)], lw=0.25, c='#A88560', z=2)
# 保育室の西の壁（h2.4）と上の縦格子（梁の下まで）
Sr(1.54, 1.66, 0.0, 2.40, fc=C_CUT, ec=C_CUT, lw=0.2, z=8)
Sr(1.585, 1.615, 2.40, 3.70, fc='#7a6a55', ec='none', z=8)
# 越屋根の東の立ち上がり（v1.54〜1.66）とすき間（ガラリ）
Sr(1.54, 1.66, 3.79, 4.14, fc=C_CUT, ec=C_CUT, lw=0.2, z=8)
for z in np.arange(4.16, zlid(1.6) - 0.01, 0.035): Sl([(1.54, z), (1.66, z + 0.02)], lw=0.3, c='#444', z=8)
for z in np.arange(4.30, zlid(-0.28) - 0.01, 0.035): Sl([(-0.36, z), (-0.20, z + 0.02)], lw=0.3, c='#444', z=8)
# 屋根（5歳の部屋の上）：母屋 60×150・合板 t24・断熱 t150・通気垂木・野地＋屋根材
vR = np.array([1.66, VS0])
Sp([(1.66, zply(1.66)), (VS0, zply(VS0)), (VS0, ztop(VS0)), (1.66, ztop(1.66))], fc='#E2D3B8', ec=C_CUT, lw=0.4, z=8)
Sl([(1.66, zbt(1.66)), (VS0, zbt(VS0))], lw=0.25, c='#555', z=9)
Sr(1.75, 1.82, zpur(1.78), zply(1.78), fc='#C9A77C', ec=C_CUT, lw=0.3, z=8)
# 越屋根：ガラスの蓋 t60（v−0.70〜1.95）、木のルーバー（幅120・104おき・東へ30°）、LED
Sp([(1.95, zlid(1.95)), (-0.70, zlid(-0.70)), (-0.70, zlid(-0.70) + 0.06), (1.95, zlid(1.95) + 0.06)], fc=C_GLASS, ec=C_GL_E, lw=0.4, z=9)
for v in np.arange(-0.30, 1.86, 0.104):
    zb = zlid(v) + 0.06
    Sl([(v, zb + 0.005), (v + 0.104, zb + 0.065)], lw=0.9, c='#B8A88A', z=9)
Sr(1.87, 1.91, 4.227, 4.270, fc='#F2C640', ec='none', z=9)
# 天井扇（架構の手前、見えがかり u52.5）
Sr(0.25, 1.35, 2.80, 2.84, fc='#666', ec='none', z=6); Sr(0.74, 0.86, 2.77, 2.86, fc='#555', ec='none', z=6)
Sl([(0.8, 2.86), (0.8, 3.45)], lw=0.6, c='#555', z=6)
# 光：ルーバーの拡散光が西吹き抜けへ、白い西の壁で返る
for (v0, v1) in [(1.4, 0.95), (0.9, 0.55), (0.4, 0.1), (1.7, 1.25)]:
    axS.annotate('', xy=(X(v1), 0.55), xytext=(X(v0), zlid(v0) - 0.05),
                 arrowprops=dict(arrowstyle='-|>', lw=0.45, color=C_LIGHT, alpha=0.85), zorder=10)
axS.annotate('', xy=(X(0.45), 1.6), xytext=(X(-0.18), 3.0),
             arrowprops=dict(arrowstyle='-|>', lw=0.4, color=C_LIGHT, alpha=0.6, ls=(0, (2, 1.5))), zorder=10)
# 人：足入れに足を下ろして窓の外を見る子、寝ころぶ子
kid_sit(axS, X(0.66), z0=0.05, h=0.60)
Sp([(0.58, 0.05), (0.58, 0.16), (0.40, 0.16), (0.36, -0.27), (0.46, -0.27), (0.50, 0.05)], fc=C_KID, ec='none', z=12)
Sl([(0.62, 0.48), (-1.25, -0.25)], lw=0.4, c='#34502A', ls=(0, (2, 1.5)), z=11)
axS.add_patch(Ellipse((X(1.0), 0.14), 0.5, 0.17, fc=C_KID, ec='none', zorder=12))
axS.add_patch(Circle((X(1.3), 0.18), 0.1, fc=C_KID, ec='none', zorder=12))
axS.add_patch(Ellipse((X(1.15), 0.13), 0.3, 0.12, fc='#F3E1C7', ec=C_CUR, lw=0.3, zorder=11))
# 寸法
dim(axS, -0.30, 0.0, X(-0.06), '300', horiz=False, side=-1)
dim(axS, -0.30, 0.60, X(-0.50) + 0.0, '900', horiz=False, side=1)
dim(axS, 0.0, 2.80, X(1.15), '2800', horiz=False, side=1)
dim(axS, X(1.6), X(0.0), -0.40, '1600', horiz=True, side=-1)
St(1.80, 0.18, 'FL±0', size=4.0, c='#555')
St(-1.88, -0.18, 'GL−300', size=4.0, ha='right', c='#555')
# ラベル
St(-0.45, 4.02, '越屋根：ガラスの蓋\n＋木のルーバー', size=4.3, c='#2E5373')
St(1.35, 2.35, '天井扇', size=4.2, c='#555')
St(1.0, 1.75, '格子の引き戸（奥）', size=4.2, c='#6b5236')
St(1.5, 0.5, '畳＋クッション', size=4.2, c='#5A4A20')
St(0.26, -0.40, '足入れ', size=4.2, c='#34502A', ha='center')
St(-0.38, 0.95, '地窓', size=4.2, c='#2E5373', ha='left')
T(axS, X(VS0) + 0.05, ZS1 - 0.06, '断面A　1/60（南を見る）', size=5.4, weight='bold', va='top')

# ======================================================================
# 説明（右下）
# ======================================================================
nx0 = SX0 / W; y = (H - 1.5 - SH - 3.5)
notes = [
    ('絵本の通り', ['西吹き抜けの壁いっぱいに棚h1.2。くぼみは床から', '300上がった腰掛けで、カーテンを引くと隠れ家に。']),
    ('本の奥', ['北の行き止まりに畳とクッション。格子の引き戸は', '閉じても光と気配が通る。足入れに足を下ろすと、', '地窓の向こうに読書の庭の苔とモミジ。']),
    ('上から光', ['越屋根のガラスの蓋と木のルーバーから、朝は直射、', '昼は拡散光が落ちる。天井扇が空気をまわす。']),
]
for h, ls in notes:
    fig.text(nx0, y / H, h, fontsize=5.6, weight='bold', color='#5A4A20', va='top'); y -= 2.9
    for s in ls:
        fig.text(nx0, y / H, s, fontsize=4.8, color=C_TXT, va='top'); y -= 2.45
    y -= 1.2
# スケールバー（1/60：0〜2 m）
y -= 1.0
x0 = SX0
for k in range(4):
    fig.patches.append(Rectangle(((x0 + k * 0.5 * S) / W, y / H), 0.5 * S / W, 1.0 / H, transform=fig.transFigure,
                                 fc='k' if k % 2 == 0 else 'white', ec='k', lw=0.3))
for k, s in enumerate(['0', '1', '2 m']):
    fig.text((x0 + k * S) / W, (y - 0.6) / H, s, fontsize=4.2, ha='center', va='top')
fig.text((x0 + 2 * S + 6) / W, (y + 0.5) / H, '1/60　寸法はmm', fontsize=4.4, va='center')

os.makedirs(OUT, exist_ok=True)
fig.savefig(os.path.join(OUT, 'sodachiya_present_books.pdf'))
fig.savefig(os.path.join(OUT, 'sodachiya_present_books.png'), dpi=1600 / (W * MM))
print('ok', 'plan', round((UP1 - UP0) * S, 1), 'x', round(PH, 1), 'mm; sec', round((VS0 - VS1) * S, 1), 'x', round(SH, 1), 'mm')
