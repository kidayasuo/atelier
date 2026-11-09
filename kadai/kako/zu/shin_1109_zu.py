# -*- coding: utf-8 -*-
"""図：作り直した架構（Tamediaに倣う、2026-11-09夜）。k15の立面1/100と、接合の詳細1/20（立面・断面）。A3横。
形は ../gh/kakou.py の核、数は ../ryakusan/shin_1109.py。
  python3 shin_1109_zu.py → shin_1109.pdf（書体はあとで hiragino.py で差し替える）
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'gh'), os.path.join(HERE, '..', 'sodachiya_dummy'),
                os.path.join(HERE, '..', '..', 'sodachiya', 'scripts')]
import fonts42  # noqa: F401
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import kakou as K

P = dict(K.DEF)
w, t, kd = P['col'], P['t'], P['key']
TOPE, TOPW = 8100.0, 4900.0
sW = 13480.0; s_wall = sW + w / 2; s_tip = s_wall + 780 - 100
m = (TOPW - TOPE) / sW; z0 = TOPE
top = lambda s: z0 + m * s
sup = [0.0, 2200.0, sW]
Dfn = K.depth_fn(sup, P['D'], P['Dm'])
WOOD, COLC, KEYC, GIR = '#ecd5a3', '#d5b47a', '#c0392b', '#9a7442'
EDGE = '#4a3c22'


def poly(pr):
    k = pr[0]
    if k == 'poly':
        return Polygon(pr[1]).buffer(0)
    if k == 'body':
        return Polygon(pr[1] + list(reversed(pr[2]))).buffer(0)
    if k == 'aff':
        _, wh, s0, zz, a11, a12, a21, a22 = pr
        ts = [2 * math.pi * i / 200 for i in range(200)] if wh == 'circle' else [math.pi * i / 100 for i in range(101)]
        return Polygon([(s0 + a11 * math.cos(q) + a12 * math.sin(q), zz + a21 * math.cos(q) + a22 * math.sin(q)) for q in ts]).buffer(0)
    _, T1, cf, R, T2, I = pr
    return Polygon([T1] + K._arc_pts(T1, cf, T2, 30) + [T2, I]).buffer(0)


B = K.beam_2d(P, (z0, m), sup, Dfn, ext=(s_wall, s_tip))
outer = unary_union([poly(q) for q in B['prims']]).intersection(poly(B['clip']))
plate = outer
for h in B['holes']:
    plate = plate.difference(poly(h))
cols, keys = [], []
for i, s in enumerate(sup):
    G, h = B['heads'][i]
    C = K.column_2d(s, w, 0.0, top(s), [(G, h)], G)
    c = unary_union([poly(q) for q in C['prims']]).intersection(unary_union([outer, poly(C['band'])]))
    for hh in C['holes']:
        c = c.difference(poly(hh))
    cols.append(c)
    keys.append(poly(K.key_shape(G, h)))


def fill(ax, g, fc, ec=EDGE, lw=0.5, z=2, ls='-'):
    for gg in getattr(g, 'geoms', [g]):
        if gg.is_empty:
            continue
        x, y = gg.exterior.xy
        ax.fill(x, y, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls)
        for ri in gg.interiors:
            x, y = ri.xy
            ax.fill(x, y, fc='white', ec=ec, lw=lw, zorder=z + 0.1)


def elevation(ax, xl, yl, detail=False):
    if not detail:
        ax.plot([-2600, s_tip + 800], [0, 0], color='k', lw=0.8)
        ax.fill([-300, -150, -150, -300], [0, 0, top(-150) + 109, top(-300) + 109], fc='#ddd', ec='#888', lw=0.3)
        ax.fill([s_wall, s_wall + 200, s_wall + 200, s_wall], [0, 0, top(s_wall) - 240, top(s_wall) - 240], fc='#ddd', ec='#888', lw=0.3)
        ax.plot([-300, s_tip + 100], [top(-300) + 109, top(s_tip + 100) + 109], color='#666', lw=0.6)
        ax.fill([-2500, -850, -850, -2500], [0, 0, 5200, 5200], fc='#f2f2f2', ec='#bbb', lw=0.3)
        ax.text(-1675, 2600, '本館', ha='center', fontsize=6, color='#888')
        # キャットウォーク（h3.0、幅0.9、壁から0.25あけ）と細い柱
        a, b = -150 + 250, -150 + 250 + 900
        ax.fill([a, b, b, a], [2880, 2880, 3000, 3000], fc='#c9a46a', ec=EDGE, lw=0.4, zorder=3)
        ax.plot([b - 40, b - 40], [0, 2880], color='#7a6a4a', lw=1.0, zorder=3)
        ax.plot([b, b], [3000, 4100], color='#7a6a4a', lw=0.5, zorder=3)
        ax.text(b + 60, 3150, 'キャットウォーク（床から細い柱で）', fontsize=5.5, color='#5a4a2a')
    for c in cols:
        fill(ax, c, COLC, z=1)
    fill(ax, plate, WOOD, z=2)
    for kk in keys:
        fill(ax, kk, 'none', ec=KEYC, lw=0.6 if detail else 0.3, z=3, ls=(0, (3, 2)))
    for G, h in B['heads']:
        fill(ax, poly(K.ellipse(G, K.GIRDER_A, K.GIRDER_B)), GIR, z=2.5)
    ax.set_xlim(*xl); ax.set_ylim(*yl); ax.set_aspect('equal'); ax.axis('off')


def dim(ax, a, b, y, txt, vert=False, fs=5.5, off=0):
    if vert:
        ax.annotate('', (y, a), (y, b), arrowprops=dict(arrowstyle='<->', lw=0.4, shrinkA=0, shrinkB=0))
        ax.text(y + 25 + off, (a + b) / 2, txt, fontsize=fs, va='center', rotation=90)
    else:
        ax.annotate('', (a, y), (b, y), arrowprops=dict(arrowstyle='<->', lw=0.4, shrinkA=0, shrinkB=0))
        ax.text((a + b) / 2, y - 30 + off, txt, fontsize=fs, ha='center', va='top')


fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4))
fig.text(0.03, 0.955, '遊戯室の架構（作り直し、Tamediaに倣う）　架構k15', fontsize=12)
fig.text(0.03, 0.935, '柱300角を板2枚×160がじかに挟み、板の頭がまるごと柱に食い込む。楕円の桁180×260が板と柱を貫く。梁は東の内の柱の列（2階の柱の線v−3.4）の上を続き、西は外壁の柱まで一つのスパン。'
         '\n架構の間隔3 m、2枚のあいだ（光の筋）は柱の幅300。形の比はTamediaの詳細図から（桁の中心は下端から0.14D、頭0.58D×0.68D、ハンチ1.1D）。', fontsize=7, va='top', linespacing=1.5)

# 立面 1/100：幅 (s_tip+3400)/100 mm
W1 = (s_tip + 3400) / 100 / 420; H1 = 9600 / 100 / 297
ax = fig.add_axes([0.03, 0.43, W1, H1])
elevation(ax, (-2600, s_tip + 800), (-1200, 8400))
ax.set_title('立面（架構の面）1/100', loc='left', fontsize=8, pad=2)
yd = -500
for a, b in zip(sup[:-1], sup[1:]):
    dim(ax, a, b, yd, '%.2f' % ((b - a) / 1000))
for s in sup:
    ax.plot([s, s], [yd - 80, 120], color='#999', lw=0.3)
ax.text(2200, -1050, '内の柱の列（v−3.4、2階の柱の線）', fontsize=5.5, ha='center')
smid = (2200 + sW) / 2
ax.text(smid, top(smid) + 380, 'せい 端%d→真ん中%d' % (P['D'], P['Dm']), fontsize=6, ha='center')

# 詳細 1/20：東の端・内の列
def detail(rect, s, title, xr=(-700, 700), yr=(-750, 650)):
    G, h = B['heads'][sup.index(s)]
    wmm = (xr[1] - xr[0]) / 20 / 420; hmm = (yr[1] - yr[0]) / 20 / 297
    ax = fig.add_axes([rect[0], rect[1], wmm, hmm])
    elevation(ax, (s + xr[0], s + xr[1]), (G[1] + yr[0], G[1] + yr[1]), detail=True)
    ax.set_title(title, loc='left', fontsize=8, pad=2)
    ax.plot([s - 900, s + 900], [G[1], G[1]], color='#888', lw=0.3, ls='-.')
    ax.plot([s, s], [G[1] - 900, G[1] + 900], color='#888', lw=0.3, ls='-.')
    return ax, G, h

axE, GE, hE = detail((0.03, 0.05), 0.0, '東の端の接合　立面 1/20')
dim(axE, -w / 2, w / 2, GE[1] - hE['hb'] - 330, '柱 %d' % w)
dim(axE, GE[1] - hE['hb'], GE[1] + hE['hb'], 0 + 0 - hE['ha'] - 120, '頭 %d' % (2 * hE['hb']), vert=True)
axE.text(hE['ha'] + 40, GE[1] - 30, '桁 %d×%d\n（楕円）' % (2 * K.GIRDER_A, 2 * K.GIRDER_B), fontsize=5.5)
axE.text(-650, GE[1] + 560, '赤の点線：食い込み（頭の形まるごと、柱の欠き込み）', fontsize=5.5, color=KEYC)

axI, GI, hI = detail((0.27, 0.05), 2200.0, '内の列の接合　立面 1/20', xr=(-900, 900))
dim(axI, 2200 - w / 2, 2200 + w / 2, GI[1] - hI['hb'] - 330, '柱 %d' % w)
axI.text(2200 + 420, GI[1] + 330, '梁は途切れずに続く\n（2枚の板が柱を挟む）', fontsize=5.5)

# 断面 1/20（内の列の接合、架構に直角に切る）
xr = (-700, 700); yr = (-900, 650)
axS = fig.add_axes([0.56, 0.05, (xr[1] - xr[0]) / 20 / 420, (yr[1] - yr[0]) / 20 / 297])
axS.set_title('内の列の接合　断面（架構に直角）1/20', loc='left', fontsize=8, pad=2)
zt = top(2200); zb = GI[1] - hI['hb']; zk = hI['hb']
colS = box(-w / 2, GI[1] - 1500, w / 2, zt).difference(box(w / 2 - kd, GI[1] - zk, w / 2 + 1, GI[1] + zk)).difference(box(-w / 2 - 1, GI[1] - zk, -w / 2 + kd, GI[1] + zk))
fill(axS, colS, COLC, z=1)
for sg in (1, -1):
    pl = box(min(sg * w / 2, sg * (w / 2 + t)), zb, max(sg * w / 2, sg * (w / 2 + t)), zt)
    fill(axS, pl, WOOD, z=2)
    kb = box(min(sg * (w / 2 - kd), sg * w / 2), GI[1] - zk, max(sg * (w / 2 - kd), sg * w / 2), GI[1] + zk)
    fill(axS, kb, '#e9b9a5', ec=KEYC, z=2.2)
gir = box(-700, GI[1] - K.GIRDER_B, 700, GI[1] + K.GIRDER_B)
fill(axS, gir, GIR, z=3)
axS.plot([-700, 700], [zt + 109, zt + 109], color='#666', lw=0.6)
axS.text(0, zt + 140, '屋根（合板・断熱・屋根材）', fontsize=5.5, ha='center')
dim(axS, -(w / 2 + t), -w / 2, zb - 80, '%d' % t)
dim(axS, -w / 2, w / 2, zb - 80, '%d' % w)
dim(axS, w / 2, w / 2 + t, zb - 80, '%d' % t)
dim(axS, GI[1] - zk, GI[1] + zk, w / 2 + t + 90, '頭 %d' % (2 * zk), vert=True)
axS.text(w / 2 + t + 40, GI[1] - zk - 160, '食い込み %d（片側、頭の形まるごと）\n頭の下の縁が柱の肩に載る（支圧）' % kd, fontsize=5.5)
axS.text(-680, GI[1] + K.GIRDER_B + 30, '桁（楕円、隣の架構へ）', fontsize=5.5)
axS.set_xlim(*xr); axS.set_ylim(GI[1] + yr[0], GI[1] + yr[1]); axS.set_aspect('equal'); axS.axis('off')

NOTE = ('略算（kadai/kako/ryakusan/shin_1109.py、k15）\n'
        '・主のスパン11.28 m（内の列→西の柱）、東の短いスパン2.20 m。\n'
        '・せい 端500→真ん中400で、たわみ0.94以下・曲げ0.40（長期×2、δ/L＜1/250）。\n'
        '・接合で決まる最小のせいは約375（桁の穴のまわりに木120）。\n'
        '・東の外の柱は引張り（雪で約33 kN）→柱脚で引き抜きを止める。\n'
        '・内の柱は圧縮約90 kN（300角、両端ピン）。\n'
        '・梁と柱の頭はピンとした（剛接合は当てにしない、安全側）。\n'
        '\n宿題\n'
        '・内の列はk15で摺鉢ネットを貫く→ネットを西か北へ動かす。\n'
        '・キャットウォークは床から細い柱で（遊具の決まりの変更、意匠の先生に報告）。')
fig.text(0.60, 0.82, NOTE, fontsize=6.5, va='top', linespacing=1.6)
out = os.path.join(HERE, 'shin_1109.pdf')
fig.savefig(out)
fig.savefig('/tmp/claude-0/shin_1109.png', dpi=100)
print(out)
