# -*- coding: utf-8 -*-
"""図：遊戯室の架構k15の3案（今の単純梁・連続＋片持ち・方杖）の立面（架構の面）、1/100、A3縦。
数は ../ryakusan/hikaku_1109.py。接合の形は ../gh/kakou.py の核（Tamediaの比：e＝0.14D、頭 0.58D×0.68D、ハンチ 1.1D）。
  python3 hikaku_1109_zu.py  → hikaku_1109.pdf（書体はあとで hiragino.py で差し替える）
"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, '..', 'gh'), os.path.join(HERE, '..', 'ryakusan'),
                os.path.join(HERE, '..', '..', 'sodachiya', 'scripts')]
import fonts42  # noqa: F401
import matplotlib.pyplot as plt
from shapely.geometry import Polygon, box, LineString
from shapely.ops import unary_union
import kakou as K
import hikaku_1109 as H

SW, EAVE = H.SW * 1000, H.EAVE * 1000
top = lambda s: H.topz(s / 1000) * 1000
GA, GB = K.GIRDER_A + K.HOLE_CLR, K.GIRDER_B + K.HOLE_CLR
WOOD = '#e8cf9c'; EDGE = '#5a4a2a'


def P(pr):
    k = pr[0]
    if k == 'poly':
        return Polygon(pr[1]).buffer(0)
    if k == 'aff':
        _, w, s0, z0, a11, a12, a21, a22 = pr
        ts = [2 * math.pi * i / 160 for i in range(160)] if w == 'circle' else [math.pi * i / 80 for i in range(81)]
        return Polygon([(s0 + a11 * math.cos(t) + a12 * math.sin(t), z0 + a21 * math.cos(t) + a22 * math.sin(t)) for t in ts]).buffer(0)
    _, T1, cf, R, T2, I = pr
    return Polygon([T1] + K._arc_pts(T1, cf, T2, 24) + [T2, I]).buffer(0)


def head(Dj):
    """Tamediaの比で頭の大きさ（桁の穴のまわりに木120以上）"""
    return dict(e=0.14 * Dj, ha=max(0.58 * Dj, GA + 120), hb=max(0.68 * Dj, GB + 120), R=1.1 * Dj)


def beam(Dfn, joints, s_wall, s_tip):
    """joints：[(s, 'end'|'mid')]。返す：板の外形、穴、桁の点"""
    sE, sW = joints[0][0], joints[-1][0]
    ss = [sE + (sW - sE) * i / 200 for i in range(201)]
    body = Polygon([(s, top(s)) for s in ss] + [(s, top(s) - Dfn(s)) for s in reversed(ss)])
    parts, holes, Gs = [body], [], []
    m = (top(1000) - top(0)) / 1000
    for s, kind in joints:
        Dj = Dfn(s); h = head(Dj)
        G = (s, top(s) - Dj + h['e']); Gs.append((G, h))
        parts.append(P(K.ellipse(G, h['ha'], h['hb'])))
        if kind == 'end':
            Hh = top(s) - G[1]
            parts.append(P(('aff', 'half', G[0], G[1], h['ha'], 0.0, m * h['ha'], Hh)))
            parts.append(Polygon([(G[0] - h['ha'], G[1]), (G[0] + h['ha'], G[1]), (G[0] + h['ha'], G[1] + m * h['ha']), (G[0] - h['ha'], G[1] - m * h['ha'])]).buffer(0))
        for side in (-1, 1):
            if (kind == 'end' and ((s == sE and side < 0) or (s == sW and side > 0))):
                continue
            # 下端の接線（頭から 1.5R 離れた所）でハンチ
            sf = s + side * 1.5 * h['R']
            z1 = top(sf) - Dfn(sf); z2 = top(sf + 1) - Dfn(sf + 1)
            ms = z2 - z1
            far = s + side * 4 * h['R']
            p0 = (far, z1 + ms * (far - sf))
            L = math.hypot(1, ms); d = (-side / L, -side * ms / L)
            n = (d[1], -d[0])
            if n[1] > 0:
                n = (-n[0], -n[1])
            fl = K.fillet(p0, d, n, G, h['ha'], h['hb'], h['R'], G)
            if fl:
                parts.append(P(fl))
        holes.append(P(K.ellipse(G, GA, GB)))
    # 西の軒への延長（せい240→120、丸み300）
    GW, hW = Gs[-1]
    ext = Polygon([(sW, top(sW)), (s_tip, top(s_tip)), (s_tip, top(s_tip) - 120), (s_wall, top(s_wall) - 240), (sW, top(sW) - 240)])
    parts.append(ext)
    Hh = top(sW) - GW[1]
    q = lambda s, z: (s, z - m * (s - sW)); r = lambda s, z: (s, z + m * (s - sW))
    pA, pB = q(s_tip, top(s_tip) - 120), q(s_wall, top(s_wall) - 240)
    L = math.hypot(pB[0] - pA[0], pB[1] - pA[1]); d = ((pB[0] - pA[0]) / L, (pB[1] - pA[1]) / L)
    n = (d[1], -d[0]); n = (-n[0], -n[1]) if n[1] > 0 else n
    fl = K.fillet(pA, d, n, GW, hW['ha'], Hh, 300.0, (GW[0], GW[1] + 0.85 * Hh))
    if fl:
        _, T1, cf, R, T2, I = fl
        parts.append(Polygon([r(*T1)] + [r(*p) for p in K._arc_pts(T1, cf, T2, 16)] + [r(*T2), r(*I)]).buffer(0))
    clip = Polygon([(sE - 2000, top(sE - 2000)), (s_tip, top(s_tip)), (s_tip, -1000), (sE - 2000, -1000)])
    out = unary_union(parts).intersection(clip)
    return out, holes, Gs


def column(s, w, Gs_here, plate):
    """柱：頭の下で広がる（R＝1.1Dの半分）。上は板の外形の中"""
    zt = top(s) + 2000
    parts = [box(s - w / 2, 0, s + w / 2, zt)]
    for G, h in Gs_here:
        for side in (-1, 1):
            fl = K.fillet((s + side * w / 2, 0.0), (0, 1), (side, 0), G, h['ha'], h['hb'], 0.55 * h['R'], G)
            if fl:
                parts.append(P(fl))
    Gtop = max(Gs_here, key=lambda g: g[0][1])[0]
    band = box(s - w / 2 - 2000, -1, s + w / 2 + 2000, Gtop[1])
    return unary_union(parts).intersection(unary_union([plate, band]))


def fill(ax, g, fc=WOOD, ec=EDGE, lw=0.5, z=2):
    for gg in getattr(g, 'geoms', [g]):
        if gg.is_empty:
            continue
        x, y = gg.exterior.xy
        ax.fill(x, y, fc=fc, ec=ec, lw=lw, zorder=z)
        for ri in gg.interiors:
            x, y = ri.xy; ax.fill(x, y, fc='white', ec=ec, lw=lw, zorder=z + 0.1)


def scheme_ax(ax, name, Dm, De, kind):
    s_wall = SW + 200; s_tip = s_wall + EAVE - 100
    main = {'tanjun': (0, SW), 'renzoku': (1000, SW - 3000), 'houzue': (2000, SW - 2000)}[kind]
    Dfn = lambda s: De if (s < main[0] or s > main[1]) else Dm + (De - Dm) * (2 * (s - main[0]) / (main[1] - main[0]) - 1) ** 2
    joints = [(0.0, 'end')] + ([(1000.0, 'mid'), (SW - 3000, 'mid')] if kind == 'renzoku' else []) + [(SW, 'end')]
    plate, holes, Gs = beam(Dfn, joints, s_wall, s_tip)
    # 地面・床・壁・屋根の仕上げ
    ax.plot([-2600, SW + 2200], [0, 0], color='k', lw=0.8)
    ax.fill([-390, -240, -240, -390], [0, 0, top(-240) + 109, top(-390) + 109], fc='#d8d8d8', ec='#888', lw=0.3)
    ax.fill([s_wall, s_wall + 200, s_wall + 200, s_wall], [0, 0, top(s_wall) - 240, top(s_wall) - 240], fc='#d8d8d8', ec='#888', lw=0.3)
    ax.plot([-390, s_tip + 100], [top(-390) + 109, top(s_tip + 100) + 109], color='#666', lw=0.6)
    ax.fill([-2500, -940, -940, -2500], [0, 0, 5200, 5200], fc='#f0f0f0', ec='#bbb', lw=0.3)
    ax.text(-1700, 2600, '本館', ha='center', va='center', fontsize=6, color='#888')
    # 柱・方杖
    cols = [(0.0, 480), (SW, 400)]
    if kind == 'renzoku':
        cols += [(1000.0, 300), (SW - 3000, 300)]
    for s, w in cols:
        here = [g for g in Gs if abs(g[0][0] - s) < 1]
        fill(ax, column(s, w, here, plate), fc='#d9b77a', z=1)
        for g in here:
            ax.add_patch(plt.Polygon(list(P(K.ellipse(g[0], GA, GB)).exterior.coords), fc='#b08850', ec=EDGE, lw=0.4, zorder=1.5))
    if kind == 'houzue':
        for sc, sb in ((0.0, 2000.0), (SW, SW - 2000.0)):
            zb = top(sb) - Dfn(sb)
            zc = zb - 2100 - (top(sc) - top(sb))
            dx, dz = sb - sc, zb - zc; L = math.hypot(dx, dz); nx, nz = -dz / L * 90, dx / L * 90
            br = LineString([(sc, zc), (sb, zb)]).buffer(90, cap_style=1)
            fill(ax, br, fc='#d9b77a', z=1.2)
            for p in ((sc, zc), (sb, zb)):
                ax.add_patch(plt.Circle(p, 45, fc='#b08850', ec=EDGE, lw=0.4, zorder=3))
    fill(ax, plate, z=2)
    for hh in holes:
        fill(ax, hh, fc='#b08850', z=2.5)
    # 遊具：キャットウォーク（h3.0、幅0.9）と輪・摺鉢ネット
    cw0, cw1 = -240 + 250 - 250, -240 + 250 + 900
    ax.fill([cw0, cw1, cw1, cw0], [2880, 2880, 3000, 3000], fc='#c9a46a', ec=EDGE, lw=0.4, zorder=3)
    ax.plot([cw1, cw1], [3000, 4100], color='#7a6a4a', lw=0.5, zorder=3)
    if kind != 'renzoku':
        ax.plot([cw1 - 60, cw1 - 60], [0, 2880], color='#7a6a4a', lw=1.2, zorder=3)
        ax.text(cw1 + 80, 2300, 'キャットウォークの\n柱（細い）', fontsize=5, va='center', color='#5a4a2a')
    rc = -240 + 3250
    ax.fill([rc + 2100, rc + 2900, rc + 2900, rc + 2100], [2880, 2880, 3000, 3000], fc='#c9a46a', ec=EDGE, lw=0.4, zorder=3)
    ax.fill([cw1, rc - 2100, rc - 2100, cw1], [2880, 2880, 3000, 3000], fc='#c9a46a', ec=EDGE, lw=0.4, zorder=3)
    ts = [i / 20 for i in range(21)]
    for sg in (-1, 1):
        ax.plot([rc + sg * (300 + 1800 * t ** 1.6) for t in ts], [150 + 2850 * t for t in ts], color='#8a6f3a', lw=0.7, zorder=3)
    for sh in (1000.0, 5300.0):
        if kind == 'renzoku' and sh == 1000.0:
            continue
        zb = top(sh) - Dfn(sh)
        ax.plot([sh - 240, sh - 240], [3000, zb], color='#555', lw=0.4, ls=(0, (4, 2)), zorder=1)
    ax.text(rc + 250, 500, '摺鉢ネット', fontsize=5, ha='center', color='#5a4a2a')
    # 寸法
    yd = -700
    xs = sorted(set([0.0, SW] + [c[0] for c in cols if c[0] not in (0.0, SW)] + ([2000.0, SW - 2000] if kind == 'houzue' else [])))
    for a, b in zip(xs[:-1], xs[1:]):
        ax.annotate('', (a, yd), (b, yd), arrowprops=dict(arrowstyle='<->', lw=0.4, shrinkA=0, shrinkB=0))
        ax.text((a + b) / 2, yd - 120, '%.2f' % ((b - a) / 1000), ha='center', va='top', fontsize=5.5)
    for s in xs:
        ax.plot([s, s], [yd - 100, 150], color='#999', lw=0.3)
    smid = (main[0] + main[1]) / 2
    ax.text(smid, top(smid) + 450, 'せい %d' % Dfn(smid), ha='center', fontsize=6)
    for s in (main[0] + 300 if kind == 'tanjun' else main[0], main[1]):
        pass
    if Dm != De:
        ax.text(main[0] + 350, top(main[0]) + 450, '端 %d' % De, ha='left', fontsize=6)
    ax.set_title(name, loc='left', fontsize=9, pad=4)
    ax.set_xlim(-2600, SW + 2200); ax.set_ylim(-1300, 9200); ax.set_aspect('equal'); ax.axis('off')


NOTE = {
    'tanjun': '今の案（板を2×160にし、遊具の積載を見直した値）\n東の柱から西の柱まで一つのスパン 13.34 m。\nたわみで決まり、せい650（たわみ0.97・曲げ0.35）。',
    'renzoku': 'Tamediaの3スパン（3.2＋11＋3.2）に倣い、柱の列を内に2本足す。\n東：キャットウォークの縁の列（1.0）が遊具の床も受ける。\n西：外壁から3.0内の列。道に沿う低い帯が「間の場」になる。\n梁は柱を越えて続き、軒の延長が片持ち。\n真ん中9.34 m、せい端560→真ん中420\n（たわみ0.31・曲げ0.17、内の柱の軸力約66 kN）。\nせいはスパンでなく、桁の穴を包む頭の大きさで決まる。',
    'houzue': '床に柱を立てず、東西の柱の頭に方杖。\n東の方杖はキャットウォークの頭の上（下端h約5.2）、\n西は軒の下でh約2.1から。主のスパン9.34 m。\nせい端560→真ん中420（たわみ0.59・曲げ0.24）。\n方杖が柱を外へ押す（約62 kN）ので、柱の曲げが大きい\n（西の柱180×400で約9 N/mm²）。柱を太くするか、梁を引張りの材として効かせる。',
}

fig = plt.figure(figsize=(297 / 25.4, 420 / 25.4))
# 1/100：図の 1 mm＝100 mm。幅 (SW+4800)/100 mm
W = (SW + 4800) / 100 / 297; Hh = 10500 / 100 / 420
for i, (kind, name, Dm, De) in enumerate((('tanjun', 'A　今の単純梁（参考）', 650, 650),
                                           ('renzoku', 'B　連続＋片持ち（内に柱の列）', 420, 560),
                                           ('houzue', 'C　方杖', 420, 560))):
    y0 = 1 - 0.05 - (i + 1) * (Hh + 0.035)
    ax = fig.add_axes([0.04, y0, W, Hh])
    scheme_ax(ax, name, Dm, De, kind)
    fig.text(0.04 + W + 0.015, y0 + Hh - 0.01, NOTE[kind], fontsize=6.3, va='top', linespacing=1.6)
fig.text(0.04, 0.975, '遊戯室の架構 k15（いちばん長いスパン）の3案　立面（架構の面）1/100', fontsize=11)
fig.text(0.04, 0.958, '板2×160、木E＝9,500・fb＝12、δ/L＜1/250（長期×2）。屋根0.84＋雪0.6 kN/m²。遊具は輪とネットだけを吊る（1本5 kN×2）。'
         '\n接合の形はTamediaの比（桁の中心は下端から0.14D、頭0.58D×0.68D、ハンチ1.1D）。数は kadai/kako/ryakusan/hikaku_1109.py。', fontsize=6.5, va='top', linespacing=1.5)
out = os.path.join(HERE, 'hikaku_1109.pdf')
fig.savefig(out)
fig.savefig('/tmp/claude-0/hikaku_1109.png', dpi=110)
print(out)
