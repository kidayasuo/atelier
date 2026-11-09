# -*- coding: utf-8 -*-
"""略算：作り直した架構（Tamediaに倣う、2026-11-09夜、ユーザーの選び）。

決まり：柱300角（2枚の板のあいだ＝柱、光の筋も300）、板2枚×160、架構の間隔3 m、
        東だけ内に柱の列（2階の柱の線 v−3.4）で梁を連続させ、西は今のまま（内に柱を立てない、方杖なし）。
架構k15：東の柱の芯 v−1.20（東の壁の内面v−1.05＋150）、内の列 v−3.4（s＝2.20）、
        西の柱の芯は外壁の内面の150内（s≈13.48）。梁の上端は育ち舎の値（東8.10→西4.90）を当てはめる。
支点：柱脚は固定（鋼板挿入）。梁と東西の柱の頭はピン（剛接合は当てにしない、安全側）。内の柱は両端ピン。
主のスパン（内の列→西の柱）の下端は、端で深く真ん中で浅い放物線（Tamediaのカーブ）。東の短いスパンは端のせい。
荷重・許容値は hikaku_1109.py と同じ（遊具は輪とネットだけを吊る、1本5 kN×2）。
接合で決まる最小のせい：桁（楕円180×260、穴＋10）のまわりに木120 → 頭の半高さ0.68D≥255 → D≥375。
"""
import numpy as np
import hikaku_1109 as H

SE, SI, SW = 0.0, 2.20, 13.48
COL = 0.30


def build(Dm, De, load, inner=SI):
    F = H.Frame()
    main = (inner, SW)
    D = H.depth_fn(Dm, De, main)
    topz = lambda s: H.TOPE + (H.TOPW - H.TOPE) * s / SW
    stops = sorted(set([0.0, inner, SW, SW + H.EAVE] + list(H.S_RING)))
    xs = []
    for a, b in zip(stops[:-1], stops[1:]):
        n = max(2, int(np.ceil((b - a) / 0.25)))
        xs += list(np.linspace(a, b, n + 1)[:-1])
    xs.append(SW + H.EAVE)
    ids = [F.node(x, topz(x) - D(x) / 2) for x in xs]
    for (a, ia), (b, ib) in zip(zip(xs[:-1], ids[:-1]), zip(xs[1:], ids[1:])):
        d = D((a + b) / 2)
        F.elem(ia, ib, H.B2 * d, H.B2 * d**3 / 12, tag='beam')
        w = (H.ROOF + H.GAM * H.B2 * d + (H.SNOW if load == 'S' else 0)) * (b - a)
        for q in (ia, ib):
            F.P.setdefault(q, np.zeros(3)); F.P[q][1] -= w / 2
    for s in H.S_RING:
        q = ids[xs.index(min(xs, key=lambda x: abs(x - s)))]
        F.P.setdefault(q, np.zeros(3)); F.P[q][1] -= H.P_RING
    A, I = COL * COL, COL**4 / 12
    tags = {}
    for s, kind in ((0.0, 'E'), (inner, 'I'), (SW, 'W')):
        top = ids[xs.index(min(xs, key=lambda x: abs(x - s)))]
        x, z = F.N[top]
        base = F.node(x, 0.0)
        if kind == 'I':
            F.fix[base] = [0, 1]
            F.elem(base, top, A, I, hinge=(True, True), tag='post')
        else:
            F.fix[base] = [0, 1, 2]
            F.elem(base, top, A, I, hinge=(False, True), tag='col')
        tags[kind] = len(F.el) - 1
    return F, xs, ids, D, main, tags


def check(Dm, De, inner=SI):
    r = {}
    for load in ('L', 'S'):
        F, xs, ids, D, main, tags = build(Dm, De, load, inner)
        F.solve()
        smax = 0
        for e in F.el:
            if e['tag'] == 'beam':
                d = np.sqrt(e['I'] * 12 / e['A']); Z = H.B2 * d * d / 6
                smax = max(smax, abs(e['f'][2]) / Z, abs(e['f'][5]) / Z)
        s0, s1 = main
        i0 = ids[xs.index(min(xs, key=lambda x: abs(x - s0)))]
        i1 = ids[xs.index(min(xs, key=lambda x: abs(x - s1)))]
        w0, w1 = F.u[3 * i0 + 1], F.u[3 * i1 + 1]
        dmax = max(-(F.u[3 * i + 1] - (w0 + (x - s0) / (s1 - s0) * (w1 - w0))) for x, i in zip(xs, ids) if s0 <= x <= s1)
        N = {k: -F.el[t]['f'][0] for k, t in tags.items()}   # 正＝引張り
        r[load] = (smax, dmax, N)
    rs = max(r['L'][0] / H.FB, r['S'][0] / H.FBS)
    rd = max(2 * r['L'][1], r['S'][1]) / ((SW - inner) / 250)
    return rs, rd, r['L'][2], r['S'][2]


if __name__ == '__main__':
    print('主のスパン %.2f m（内の列 s=%.2f → 西の柱 s=%.2f）' % (SW - SI, SI, SW))
    for De in (0.40, 0.45, 0.50, 0.55):
        for Dm in np.arange(0.25, De + 0.001, 0.025):
            rs, rd, NL, NS = check(Dm, De)
            if rs <= 1 and rd <= 1:
                print('  端%.0f：真ん中 %.0f で足りる（曲げ %.2f・たわみ %.2f）。軸力 長期 東%+.0f・内%+.0f・西%+.0f、雪 東%+.0f・内%+.0f・西%+.0f kN（＋は引張り）'
                      % (De * 1000, Dm * 1000, rs, rd, NL['E'], NL['I'], NL['W'], NS['E'], NS['I'], NS['W']))
                break
        else:
            print('  端%.0f：足りない' % (De * 1000))
