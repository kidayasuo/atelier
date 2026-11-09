# -*- coding: utf-8 -*-
"""略算：遊戯室の架構の3案（今の単純梁・連続＋片持ち・方杖）を、梁のせいで比べる（2026-11-09）。

前提（課題の基本編の値）
  木 E=9,500 N/mm²、長期の許容曲げ fb=12 N/mm²、たわみ δ/L<1/250（長期はクリープ×2）。
  板は2枚×160（Tamediaに合わせる、ユーザー 11-09）。架構の間隔3.0 m。
  荷重：屋根0.84 kN/m²（育ち舎の略算）＋梁の自重（集成材5 kN/m³）、雪30 cm＝0.6 kN/m²。
        遊具：キャットウォーク・段・踊り場は床からの柱で支える（ユーザー 11-09）。屋根の梁に吊るのは輪の通路と摺鉢ネットだけ。
        輪＋ネット約26 m²×（子ども0.5 kN/m²×衝撃1.5＋遊具の自重0.4）≈30 kN、吊り材6本で1本5 kN、梁1本に2本。
  架構k15（いちばん長い）：東の柱の芯s=0、西の柱の芯s=13.34、梁の上端 東8.10・西4.90 m（育ち舎の値）、軒の出0.78。
  支点：柱脚は固定（鋼板挿入）。梁と柱の頭はピン（Tamediaの留めの剛性は当てにしない、安全側）。
  方杖・柱の中の列はピンの棒。
短期（雪）は fb×1.6/1.1 と比べる。たわみは長期（固定＋遊具）×2 と、雪を足した短期×1 の大きい方。
"""
import numpy as np

E = 9.5e6           # kN/m²
GAM = 5.0           # kN/m³
B2 = 0.32           # 2枚×160
FB, FBS = 12e3, 12e3 * 1.6 / 1.1   # kN/m²
SP, TOPE, TOPW, SW, EAVE = 3.0, 8.10, 4.90, 13.34, 0.78
ROOF, SNOW = 0.84 * SP, 0.6 * SP
P_RING, S_RING = 5.0, (1.0, 5.3)


def topz(s):
    return TOPE + (TOPW - TOPE) * s / SW


class Frame:
    def __init__(s):
        s.N, s.el, s.fix, s.P = [], [], {}, {}

    def node(s, x, z):
        for i, (a, b) in enumerate(s.N):
            if abs(a - x) < 1e-6 and abs(b - z) < 1e-6:
                return i
        s.N.append((x, z)); return len(s.N) - 1

    def elem(s, i, j, A, I, hinge=(False, False), tag=''):
        s.el.append(dict(i=i, j=j, A=A, I=I, h=hinge, tag=tag))

    def solve(s):
        n = len(s.N); K = np.zeros((3 * n, 3 * n)); F = np.zeros(3 * n)
        for e in s.el:
            k, T = s._k(e)
            dof = [3 * e['i'], 3 * e['i'] + 1, 3 * e['i'] + 2, 3 * e['j'], 3 * e['j'] + 1, 3 * e['j'] + 2]
            K[np.ix_(dof, dof)] += T.T @ k @ T
        for i, f in s.P.items():
            F[3 * i:3 * i + 3] += f
        fixed = []
        for i, d in s.fix.items():
            fixed += [3 * i + q for q in d]
        free = [q for q in range(3 * n) if q not in fixed]
        Kf = K[np.ix_(free, free)] + np.eye(len(free)) * 1e-9
        u = np.zeros(3 * n); u[free] = np.linalg.solve(Kf, F[free])
        s.u = u
        for e in s.el:
            k, T = s._k(e)
            dof = [3 * e['i'], 3 * e['i'] + 1, 3 * e['i'] + 2, 3 * e['j'], 3 * e['j'] + 1, 3 * e['j'] + 2]
            e['f'] = k @ (T @ u[dof])
        return u

    def _k(s, e):
        (x1, z1), (x2, z2) = s.N[e['i']], s.N[e['j']]
        L = np.hypot(x2 - x1, z2 - z1); c, sn = (x2 - x1) / L, (z2 - z1) / L
        A, I = e['A'], e['I']
        a, b1, b2, b3 = E * A / L, 12 * E * I / L**3, 6 * E * I / L**2, E * I / L
        k = np.array([[a, 0, 0, -a, 0, 0], [0, b1, b2, 0, -b1, b2], [0, b2, 4 * b3, 0, -b2, 2 * b3],
                      [-a, 0, 0, a, 0, 0], [0, -b1, -b2, 0, b1, -b2], [0, b2, 2 * b3, 0, -b2, 4 * b3]])
        hi, hj = e['h']
        if hi or hj:   # 端のピン：回転の自由度を縮約
            r = [q for q, h in ((2, hi), (5, hj)) if h]
            kk = [q for q in range(6) if q not in r]
            krr = k[np.ix_(r, r)]; krk = k[np.ix_(r, kk)]
            kc = np.zeros((6, 6))
            kc[np.ix_(kk, kk)] = k[np.ix_(kk, kk)] - krk.T @ np.linalg.solve(krr, krk)
            k = kc
        T = np.zeros((6, 6))
        for o in (0, 3):
            T[o:o + 2, o:o + 2] = [[c, sn], [-sn, c]]; T[o + 2, o + 2] = 1
        return k, T


def depth_fn(Dm, De, spans):
    """主のスパンで、端が深く真ん中が浅い（Tamediaの下端のカーブ）。spans=[(s0,s1)] の主のスパン"""
    s0, s1 = spans
    def D(s):
        if s < s0 or s > s1:
            return De
        x = (s - s0) / (s1 - s0)
        return Dm + (De - Dm) * (2 * x - 1) ** 2
    return D


def build(scheme, Dm, De, load):
    F = Frame()
    cols = {'E': 0.0, 'W': SW}
    braces = []
    inner = []
    if scheme == 'renzoku':
        inner = [1.0, SW - 3.0]                    # キャットウォークの縁の列・西の3.0 mの列
        main = (inner[0], inner[1])
    elif scheme == 'houzue':
        braces = [(0.0, 2.0, 2.1), (SW, SW - 2.0, 2.1)]   # 柱の芯, 梁の点s, 下がり
        main = (2.0, SW - 2.0)
    else:
        main = (0.0, SW)
    D = depth_fn(Dm, De, main)
    stops = sorted(set([-0.0, SW + EAVE] + list(cols.values()) + inner + [b[1] for b in braces] + list(S_RING)))
    xs = []
    for a, b in zip(stops[:-1], stops[1:]):
        n = max(2, int(np.ceil((b - a) / 0.25)))
        xs += list(np.linspace(a, b, n + 1)[:-1])
    xs.append(SW + EAVE)
    ids = [F.node(x, topz(x) - D(x) / 2) for x in xs]
    for (a, ia), (b, ib) in zip(zip(xs[:-1], ids[:-1]), zip(xs[1:], ids[1:])):
        d = D((a + b) / 2)
        F.elem(ia, ib, B2 * d, B2 * d**3 / 12, tag='beam')
        L = b - a
        w = (ROOF + GAM * B2 * d + (SNOW if load == 'S' else 0)) * L
        for q in (ia, ib):
            F.P.setdefault(q, np.zeros(3)); F.P[q][1] -= w / 2
    for s in S_RING:
        q = ids[xs.index(min(xs, key=lambda x: abs(x - s)))]
        F.P.setdefault(q, np.zeros(3)); F.P[q][1] -= P_RING
    def col(s, w, hinge_top=True):
        top = ids[xs.index(min(xs, key=lambda x: abs(x - s)))]
        x, z = F.N[top]
        base = F.node(x, 0.0); F.fix[base] = [0, 1, 2]
        mid = F.node(x, z / 2)
        F.elem(base, mid, 0.18 * w, 0.18 * w**3 / 12, tag='col')
        F.elem(mid, top, 0.18 * w, 0.18 * w**3 / 12, hinge=(False, hinge_top), tag='col')
        return base, mid, top
    cE = col(0.0, 0.48); cW = col(SW, 0.40)
    for s in inner:
        top = ids[xs.index(min(xs, key=lambda x: abs(x - s)))]
        x, z = F.N[top]; base = F.node(x, 0.0); F.fix[base] = [0, 1]
        F.elem(base, top, 0.18 * 0.24, 0.18 * 0.24**3 / 12, hinge=(True, True), tag='post')
    for sc, sb, drop in braces:
        top = ids[xs.index(min(xs, key=lambda x: abs(x - sb)))]
        xb, zb = F.N[top]
        xc, zc0 = sc, topz(sc) - D(sc) / 2
        foot = F.node(xc, zc0 - drop - (topz(sc) - topz(sb)) * 0)
        # 柱の途中に節：柱を作り直す
        c = cE if sc == 0.0 else cW
        F.el = [e for e in F.el if not (e['tag'] == 'col' and (e['i'] in c or e['j'] in c))]
        base, _, ctop = c
        F.elem(base, foot, 0.18 * (0.48 if sc == 0 else 0.40), 0.18 * (0.48 if sc == 0 else 0.40)**3 / 12, tag='col')
        F.elem(foot, ctop, 0.18 * (0.48 if sc == 0 else 0.40), 0.18 * (0.48 if sc == 0 else 0.40)**3 / 12, hinge=(False, True), tag='col')
        F.elem(foot, top, 0.18 * 0.24, 0.18 * 0.24**3 / 12, hinge=(True, True), tag='brace')
    return F, xs, ids, D, main


def check(scheme, Dm, De):
    out = {}
    for load in ('L', 'S'):
        F, xs, ids, D, main = build(scheme, Dm, De, load)
        F.solve()
        smax = 0
        for e in F.el:
            if e['tag'] != 'beam':
                continue
            d = np.sqrt(e['I'] * 12 / e['A'])
            Z = B2 * d * d / 6
            smax = max(smax, abs(e['f'][2]) / Z, abs(e['f'][5]) / Z)
        # 主のスパンのたわみ（両端を結ぶ線から）
        s0, s1 = main
        i0 = ids[xs.index(min(xs, key=lambda x: abs(x - s0)))]
        i1 = ids[xs.index(min(xs, key=lambda x: abs(x - s1)))]
        w0, w1 = F.u[3 * i0 + 1], F.u[3 * i1 + 1]
        dmax = 0
        for x, i in zip(xs, ids):
            if s0 <= x <= s1:
                t = (x - s0) / (s1 - s0)
                dmax = max(dmax, -(F.u[3 * i + 1] - (w0 + t * (w1 - w0))))
        brace = max([abs(e['f'][0]) for e in F.el if e['tag'] in ('brace', 'post')] or [0])
        csig = 0
        for e in F.el:
            if e['tag'] == 'col':
                d = np.sqrt(e['I'] * 12 / e['A'])
                csig = max(csig, (abs(e['f'][0]) / e['A'] + max(abs(e['f'][2]), abs(e['f'][5])) / (0.18 * d * d / 6)) / 1e3)
        out[load] = (smax, dmax, s1 - s0, brace, csig)
    sL, dL, L, nb, cL = out['L']; sS, dS, _, nbS, cS = out['S']
    rs = max(sL / FB, sS / FBS)
    rd = max(2 * dL, dS) / (L / 250)
    return rs, rd, L, max(nb, nbS), max(cL, cS)


if __name__ == '__main__':
    for scheme, name in (('tanjun', '今の単純梁'), ('renzoku', '連続＋片持ち'), ('houzue', '方杖')):
        print('==', name)
        for ratio in (1.0, 1.3):
            for Dm in np.arange(0.25, 1.21, 0.05):
                rs, rd, L, nb, cs = check(scheme, Dm, Dm * ratio)
                if rs <= 1 and rd <= 1:
                    print('  端/中=%.1f：真ん中のせい %.0f・端 %.0f（主のスパン %.2f m、曲げ %.2f・たわみ %.2f、棒の軸力 %.0f kN、柱の応力度 %.1f N/mm²）'
                          % (ratio, Dm * 1000, Dm * ratio * 1000, L, rs, rd, nb, cs))
                    break

    print('== 図に描いたせい（端560・真ん中420、今の案は650一定）')
    for scheme, Dm, De in (('tanjun', 0.65, 0.65), ('renzoku', 0.42, 0.56), ('houzue', 0.42, 0.56)):
        rs, rd, L, nb, cs = check(scheme, Dm, De)
        print('  %s：曲げ %.2f・たわみ %.2f（主のスパン %.2f m）、棒の軸力 %.0f kN、柱 %.1f N/mm²' % (scheme, rs, rd, L, nb, cs))
