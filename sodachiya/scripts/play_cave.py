"""洞のクスノキ　プレゼン用の一枚（断面パース：u 32.9 で切って南を見る）。遊戯室の担当。
2 階の床の下の低い洞に、クスノキの枝の先が天井に触れ、木が 2 階を支えて見える。上は 2 階の会議室。
寸法は data/play.json（洞・切り株）と 3dm から読んだ値（2 階の床 3.17〜3.25、階段の箱、屋根 8.15−0.25w）。
出力：out/sodachiya_play_cave.pdf・.png（160×112 mm）
"""
import os, math, json, numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Polygon as MP, Ellipse
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"; FONTB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
# 提出の図はIllustratorで書体を置き換えるので、TrueTypeに変えたNotoをType42で埋め込む（連携 20261024-1552-present）
import subprocess as _sp
_TTF = os.path.expanduser("~/.cache/sodachiya_fonts")
if not os.path.exists(os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")):
    _sp.run([__import__("sys").executable, os.path.join(ROOT, "present", "tools", "make_ttf.py"), _TTF], check=False)
if os.path.exists(os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")):
    FONT, FONTB = os.path.join(_TTF, "NotoSansCJKjp-Regular.ttf"), os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")
    plt.rcParams["pdf.fonttype"] = 42
for f in (FONT, FONTB): matplotlib.font_manager.fontManager.addfont(f)
P = json.load(open(os.path.join(ROOT, 'data', 'play.json'), encoding='utf-8'))
st, cv = P['stump'], P['cave']
rng = np.random.default_rng(11)

UC = 32.9                                     # 切る所（u）。梁 u 33 のすぐ南
C = np.array([UC + 10.5, 6.6, 1.35])          # カメラ（u, w, z）：一点透視、南（−u）を見る
F = 10.5 / 7.4                                # 切断面で幅 14.8 m が画面の幅 2 になる
def proj(u, w, z):
    d = C[0] - u
    return np.array([-(w - C[1]) / d * F, (z - C[2]) / d * F]), d   # 東（w 小）が右、西が左
def pts(L): return np.array([proj(*p)[0] for p in L])

PW, PH = 160.0, 112.0
fig = plt.figure(figsize=(PW / 25.4, PH / 25.4)); ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(-1.0, 1.0); ax.set_ylim(-0.42, -0.42 + 2.0 * PH / PW); ax.set_aspect('equal'); ax.axis('off')
INK = '#3b342c'; POCHE = '#2f2a25'
def poly(L, fc, ec=INK, lw=0.5, z=1, alpha=1.0):
    ax.add_patch(MP(pts(L), closed=True, fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha, joinstyle='round'))
def ln(L, c=INK, lw=0.4, z=1.5, ls='-'):
    a = pts(L); ax.plot(a[:, 0], a[:, 1], c=c, lw=lw, zorder=z, ls=ls, solid_capstyle='round')
def width_pt(w_m, d): return max(0.3, w_m / d * F * (PW / 2) / 25.4 * 72)

WW = 12.9                                     # 西の壁の内側（u 30〜33 のあたり）
zroof = lambda w: 8.15 - 0.25 * w
U_MT = 21.0                                   # 会議室の奥の壁（2 階の床の南の端）
# ---------------------------------------------------------------- 奥：会議室（2 階）
poly([(U_MT, 4.1, cv['slab_top']), (U_MT, WW, cv['slab_top']), (U_MT, WW, zroof(WW)), (U_MT, 4.1, zroof(4.1))], '#EEE7DA', INK, 0.4, 1)
poly([(U_MT, 4.1, cv['slab_top']), (UC, 4.1, cv['slab_top']), (UC, WW, cv['slab_top']), (U_MT, WW, cv['slab_top'])], '#E2D2B4', INK, 0.4, 1.1)
poly([(U_MT, WW, cv['slab_top']), (UC, WW, cv['slab_top']), (UC, WW, zroof(WW)), (U_MT, WW, zroof(WW))], '#F2ECE0', INK, 0.4, 1.1)
poly([(U_MT, 4.1, zroof(4.1)), (UC, 4.1, zroof(4.1)), (UC, WW, zroof(WW)), (U_MT, WW, zroof(WW))], '#E8DDCB', INK, 0.4, 1.1)
for u in np.arange(U_MT + 3, UC, 3.0):        # 西館の梁（屋根の下、見え掛かり）
    poly([(u, 4.1, zroof(4.1) - 0.02), (u, WW, zroof(WW) - 0.02), (u, WW, zroof(WW) - 0.72), (u, 4.1, zroof(4.1) - 0.72)], '#CDB48C', INK, 0.3, 1.2)
poly([(24.5, 6.0, cv['slab_top'] + 0.72), (27.5, 6.0, cv['slab_top'] + 0.72), (27.5, 9.5, cv['slab_top'] + 0.72), (24.5, 9.5, cv['slab_top'] + 0.72)], '#C9AE84', INK, 0.3, 1.3)
for (u, w) in ((28.2, 7.0), (28.4, 8.6), (24.0, 7.6)):
    d = C[0] - u
    ax.add_patch(Ellipse(proj(u, w, cv['slab_top'] + 1.18)[0], 0.18 / d * F, 0.2 / d * F, fc='#BFB2A0', ec='none', zorder=1.35))
    b0 = proj(u, w, cv['slab_top'])[0]; b1 = proj(u, w, cv['slab_top'] + 1.05)[0]
    ax.plot([b0[0], b1[0]], [b0[1], b1[1]], c='#BFB2A0', lw=width_pt(0.34, d), zorder=1.34, solid_capstyle='round')
a = proj(UC, 8.4, cv['slab_top'] + 0.25)[0]
ax.text(a[0], a[1], '会議室（2 階）\n北の窓から遊戯室を見渡す', fontproperties=FontProperties(fname=FONT, size=5.6), color='#6b6156', ha='center', va='bottom', zorder=1.4)

# ---------------------------------------------------------------- 奥：洞（u 30〜32.9）
poly([(30, 4.1, 0), (30, WW, 0), (30, WW, cv['slab']), (30, 4.1, cv['slab'])], '#EFE6D6', INK, 0.5, 2)
for w in np.arange(4.4, WW, 0.3): ln([(30, w, 0.05), (30, w, cv['beam_bottom'] - 0.02)], '#DCCFB8', 0.3, 2.05)
poly([(30, 4.1, 0), (UC, 4.1, 0), (UC, WW, 0), (30, WW, 0)], '#E9D7B6', INK, 0.4, 2.1)
for w in np.arange(4.25, WW, 0.25): ln([(30, w, 0.0), (UC, w, 0.0)], '#D5BE98', 0.25, 2.15)
th = np.linspace(0, 2 * np.pi, 80)
poly([(min(st['u'] + st['soft_r'] * math.cos(t), UC), st['w'] + st['soft_r'] * math.sin(t), 0.002) for t in th], '#F1E5CF', '#CDB48C', 0.3, 2.2)
poly([(30, WW, 0), (UC, WW, 0), (UC, WW, cv['slab']), (30, WW, cv['slab'])], '#F3ECDD', INK, 0.5, 2.1)
poly([(30, 4.1, 0), (UC, 4.1, 0), (UC, 4.1, cv['slab']), (30, 4.1, cv['slab'])], '#E6DCCB', INK, 0.5, 2.1)
for u in np.arange(30.3, UC, 0.3): ln([(u, 4.1, 0.05), (u, 4.1, cv['slab'] - 0.05)], '#D2C6B0', 0.3, 2.12)
poly([(30, 4.1, cv['slab']), (UC, 4.1, cv['slab']), (UC, WW, cv['slab']), (30, WW, cv['slab'])], '#D7BE96', INK, 0.5, 2.1)
for w in np.arange(4.4, WW, 0.45): ln([(30, w, cv['slab'] - 0.001), (UC, w, cv['slab'] - 0.001)], '#BCA17A', 0.3, 2.12)
t_ = 0.18
poly([(30 + t_ / 2, 4.1, cv['beam_bottom']), (30 + t_ / 2, WW, cv['beam_bottom']), (30 + t_ / 2, WW, cv['slab']), (30 + t_ / 2, 4.1, cv['slab'])], '#C9AE84', INK, 0.5, 2.3)
poly([(30, 11.0, 0), (UC, 11.0, 0), (UC, 11.0, cv['beam_bottom']), (30, 11.0, cv['beam_bottom'])], '#E2D3B7', INK, 0.5, 2.3)
for u in (31.0, 32.0): ln([(u, 11.0, 0.05), (u, 11.0, cv['beam_bottom'] - 0.05)], INK, 0.35, 2.31)
poly([(30, 11.0, cv['beam_bottom']), (UC, 11.0, cv['beam_bottom']), (UC, WW, cv['beam_bottom']), (30, WW, cv['beam_bottom'])], '#D9C9AA', INK, 0.4, 2.29)
a = proj(31.0, 11.0, 1.5)[0]; ax.text(a[0], a[1], '道具入れ', fontproperties=FontProperties(fname=FONT, size=5.2), color='#6b6156', ha='center', va='center', zorder=6)

# ---------------------------------------------------------------- クスノキ・こども（奥から描く）
segs = []
def seg(p, q, w_m, col):
    p, q = np.array(p, float), np.array(q, float)
    if max(p[0], q[0]) > UC:
        if min(p[0], q[0]) > UC: return
        t = (UC - p[0]) / (q[0] - p[0]); r_ = p + (q - p) * t
        if p[0] > UC: p = r_
        else: q = r_
        segs.append((C[0] - UC - 0.001, 'cut', (proj(*r_)[0], w_m / 2 / (C[0] - UC) * F)))
    (a, da), (b, db) = proj(*p), proj(*q)
    segs.append(((da + db) / 2, 's', (np.array([a, b]), col, width_pt(w_m, (da + db) / 2))))
def branch(p0, p1, r0, r1, n=6, wob=0.07, depth=0, col='#7A5A3A'):
    P_ = [np.array(p0, float) + (np.array(p1, float) - np.array(p0, float)) * t + (rng.normal(0, wob, 3) * [1, 1, 0.5] if 0 < t < 1 else 0) for t in np.linspace(0, 1, n)]
    for p in P_:
        if p[0] < UC + 0.2: p[2] = min(p[2], cv['slab'] - 0.02)
    for i in range(n - 1):
        seg(P_[i], P_[i + 1], 2 * (r0 + (r1 - r0) * i / (n - 1)), col)
    if depth < 2:
        d = np.array(p1, float) - np.array(p0, float); d /= np.linalg.norm(d)
        for k in range(2):
            q = P_[int((0.5 + 0.3 * k) * (n - 1))]; side = np.cross(d, [0, 0, 1]); side /= (np.linalg.norm(side) + 1e-9)
            tip = q + d * 0.55 + side * 0.45 * (1 if k else -1) + [0, 0, 0.3]
            branch(q, tip, r1 * 0.85 + 0.01, 0.012, 4, 0.03, depth + 1, col)
import sys; sys.path.insert(0, HERE)
from play_tree import branches                        # 木は骨格から（10-24、本物のライブオークを参考に）
for k_, (name_, c_, cut_) in enumerate(branches()):
    col_ = '#8A6644' if name_ in ('幹', '根') else ('#7E5D3E' if k_ % 2 else '#8A6644')
    for p_, q_ in zip(c_[:-1], c_[1:]):
        if min(p_[2], q_[2]) < 0.0: continue           # 床の下（根の先）は描かない
        seg(p_[:3], q_[:3], p_[3] + q_[3], col_)
def kid(u, w, h=1.05, pose='stand', shirt='#C8714F', pants='#4E5D6C'):
    p = np.array([u, w, 0.0]); hd = h * 0.13
    head = p + [0, 0, h - hd]; neck = p + [0, 0, h - 2 * hd]
    hip = p + [0, 0, 0.32] if pose == 'sit' else p + [0, 0, h * 0.45]
    if pose == 'sit':
        knee = hip + [0.3, 0.05, 0.02]; seg(hip, knee, 0.11, pants); seg(knee, knee + [0.02, 0, -0.32], 0.09, pants)
    else:
        seg(hip, p + [0, 0.1, 0.02], 0.1, pants); seg(hip, p + [0, -0.1, 0.02], 0.1, pants)
    seg(neck, hip, 0.25, shirt)
    if pose == 'reach':
        for s in (1, -1): seg(neck + [0, 0, -0.04], neck + [0, 0.12 * s, 0.42], 0.07, shirt)
    elif pose == 'hug':
        for s in (1, -1): seg(neck + [0, 0, -0.06], neck + [-0.28, 0.22 * s, -0.1], 0.07, shirt)
    else:
        for s in (1, -1): seg(neck + [0, 0, -0.04], neck + [0.05, 0.18 * s, -0.3], 0.07, shirt)
    c, dd = proj(*head); segs.append((dd - 0.01, 'head', (c, hd / dd * F)))
kid(st['u'] + 0.55, st['w'] - 0.15, 1.0, 'hug', '#D9A441', '#6B5B4B')
kid(st['u'] + 0.5, st['w'] - 1.7, 1.05, 'reach', '#5E8CA8', '#4E5D6C')
kid(st['u'] + 0.3, st['w'] + 1.55, 1.0, 'stand', '#C8714F', '#5d6b55')
kid(32.4, 9.9, 0.98, 'stand', '#8C6BA8', '#4E5D6C')
for dep, kind, d in sorted(segs, key=lambda x: -x[0]):
    if kind == 's':
        xy, col, lw = d; ax.plot(xy[:, 0], xy[:, 1], c=col, lw=lw, solid_capstyle='round', zorder=3)
    elif kind == 'head':
        c, r_ = d; ax.add_patch(Ellipse(c, 2 * r_, 2 * r_, fc='#F2D9C0', ec='#5a4a3a', lw=0.4, zorder=3))
        ax.add_patch(Ellipse(c + [0, r_ * 0.35], 1.7 * r_, 1.3 * r_, fc='#3d2f25', ec='none', zorder=3))
    elif kind == 'cut':
        c, r_ = d; ax.add_patch(Ellipse(c, 2 * r_, 2 * r_, fc='#C9A57A', ec=POCHE, lw=0.5, zorder=5.5))

# ---------------------------------------------------------------- 切る面（u 32.9）
def cut(L, fc=POCHE): poly([(UC, w, z) for w, z in L], fc, 'none', 0, 5)
cut([(-0.15, -0.6), (WW + 0.3, -0.6), (WW + 0.3, 0.0), (-0.15, 0.0)], '#5b544c')
cut([(WW, 0.0), (WW + 0.15, 0.0), (WW + 0.15, zroof(WW) + 0.3), (WW, zroof(WW) + 0.3)])
cut([(-0.15, 0.0), (0.0, 0.0), (0.0, zroof(0.0) + 0.3), (-0.15, zroof(0.0) + 0.3)])
cut([(4.1, cv['slab']), (WW, cv['slab']), (WW, cv['slab_top']), (4.1, cv['slab_top'])])
cut([(-0.15, zroof(-0.15)), (WW + 0.15, zroof(WW + 0.15)), (WW + 0.15, zroof(WW + 0.15) + 0.3), (-0.15, zroof(-0.15) + 0.3)])
ins = [(UC, w, zroof(w) + 0.3) for w in (-0.15, WW + 0.15)] + [(UC, w, zroof(w) + 0.45) for w in (WW + 0.15, -0.15)]
ax.add_patch(MP(pts(ins), closed=True, fc='white', ec='#9A8FB8', lw=0.3, hatch='xxxx', zorder=5))
poly([(UC, 1.45, 0.0), (UC, 3.95, 0.0), (UC, 3.95, 7.55), (UC, 1.45, 7.55)], '#EDE6DA', 'none', 0, 3.9)
for k in range(10):                                                                              # 階段（見え掛かり）
    z = 0.3 * (k + 1); ln([(UC - 0.25 * k - 0.01, 1.45, z), (UC - 0.25 * k - 0.01, 3.95, z)], '#8a8076', 0.5, 4)
for wa, wb in ((1.3, 1.45), (3.95, 4.1)): cut([(wa, 0.0), (wb, 0.0), (wb, 7.65), (wa, 7.65)])
cut([(1.3, 7.55), (4.1, 7.55), (4.1, 7.65), (1.3, 7.65)])
a = proj(UC, 2.7, 4.6)[0]; ax.text(a[0], a[1], '階段', fontproperties=FontProperties(fname=FONT, size=5.2), color='#6b6156', ha='center', zorder=6)
for z, s in ((0.0, 'FL±0'), (cv['beam_bottom'], '2.23'), (cv['slab'], '3.17')):
    a = proj(UC, WW + 0.25, z)[0]; ax.plot([a[0], a[0] - 0.03], [a[1], a[1]], c=INK, lw=0.4, zorder=6)
    ax.text(a[0] - 0.035, a[1], s, ha='right', fontproperties=FontProperties(fname=FONT, size=4.8), color=INK, va='center', zorder=6)
fp = FontProperties(fname=FONTB, size=9.0); fr = FontProperties(fname=FONT, size=5.8)
y0 = ax.get_ylim()[0]
ax.text(-0.98, y0 + 0.085, '洞のクスノキ', fontproperties=fp, color=INK, zorder=7)
ax.text(-0.98, y0 + 0.02, '2 階の床の下の低い洞（梁の下 2.23）。クスノキの枝の先が天井に触れ、木が 2 階を支えているように見える。\n'
        '北の枝は床の縁の下をくぐって遊戯室の高い側へ（この図では切断面で切れている）。', fontproperties=fr, color='#5a5148', zorder=7, linespacing=1.45)
ax.text(-0.98, ax.get_ylim()[1] - 0.06, '断面パース　スパン 11 の北の端（u 32.9）で切って南を見る', fontproperties=FontProperties(fname=FONT, size=5.0), color='#8a8a8a', ha='left', zorder=7)
out = os.path.join(ROOT, 'out', 'sodachiya_play_cave')
fig.savefig(out + '.pdf'); fig.savefig(out + '.png', dpi=220); print('written', out)
