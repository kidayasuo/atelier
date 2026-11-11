# -*- coding: utf-8 -*-
"""略算：Tamediaの形（平らな板2枚が厚さの1/3を柱の凹みに沈める）を、遊戯室の荷重に合う太さに応用する（2026-11-11）。

形の決まり（kadai/kako/tamedia.md）：
  板の厚さ t（2枚）、凹みの深さ d＝t/3、柱の幅 C、板のあいだ（光の筋）g＝C−2d（結果）。
確かめること（架構k15、shin_1109.py と同じ荷重・支点・許容値）：
  1. 梁：曲げ・たわみ（板2枚の幅 2t）。端のせい De・真ん中 Dm の、足りるいちばん浅い組。
  2. 柱：座屈（柱の全断面 C×C、ピンの長さ）。内の柱は両端ピン、東の柱は柱脚固定・柱頭ピン（長さはそのまま、安全側）。
  3. 柱の凹みのところ：残りの断面 g×C の圧縮。
  4. 肩の支圧：頭の下の縁が凹みの下の縁に載る。板の繊維に直角（めり込み）、面積は2枚で 2·d·C（肩の長さを柱の幅で見る）。
     桁も力を伝えるが、ここでは肩だけで受けるとする（安全側）。
許容値：E・fb は基本編。圧縮・めり込みは基本編に無いので、集成材の一般的な値：
  fc 長期8.0・短期14.5 N/mm²、めり込み fcv 長期2.2・短期4.0 N/mm²（スプルースの集成材の程度）。
  座屈の低減 η：λ≤30で1、30<λ≤100で1.3−0.01λ、λ>100で3000/λ²。
"""
import numpy as np
import hikaku_1109 as H
import shin_1109 as S

FC, FCS = 8.0, 14.5
FCV, FCVS = 2.2, 4.0
L_IN, L_E = 7.6, 8.1      # 内の柱・東の柱の高さ（m、梁の芯まで）


def eta(lam):
    if lam <= 30:
        return 1.0
    if lam <= 100:
        return 1.3 - 0.01 * lam
    return 3000.0 / lam ** 2


def beam_min(t):
    H.B2 = 2 * t / 1000.0
    best = None
    for De in np.arange(0.35, 0.801, 0.025):
        for Dm in np.arange(0.25, De + 0.001, 0.025):
            rs, rd, NL, NS = S.check(Dm, De)
            if rs <= 1 and rd <= 1:
                if best is None or De < best[0] - 1e-9:
                    best = (De, Dm, rs, rd, NL, NS)
                break
        if best:
            break
    return best


def col_check(C, t, NL, NS):
    d = t / 3.0
    g = C - 2 * d
    out = {}
    i = C / np.sqrt(12)
    for k, L in (('I', L_IN), ('E', L_E)):
        lam = L * 1000 / i
        e = eta(lam)
        nL, nS = max(0, -NL[k]), max(0, -NS[k])
        out['座屈' + k] = max(nL * 1e3 / (C * C * e * FC), nS * 1e3 / (C * C * e * FCS))
    nL, nS = max(0, -NL['I']), max(0, -NS['I'])
    out['凹み'] = max(nL * 1e3 / (g * C * FC), nS * 1e3 / (g * C * FCS))
    out['肩'] = max(nL * 1e3 / (2 * d * C * FCV), nS * 1e3 / (2 * d * C * FCVS))
    return g, out


if __name__ == '__main__':
    print('架構k15、主のスパン %.2f m。比は1以下でよい' % (S.SW - S.SI))
    for t in (120, 160, 200, 240):
        b = beam_min(t)
        De, Dm, rs, rd, NL, NS = b
        print('\n板 %d×2（凹み %d）：梁 端%.0f・真ん中%.0f（曲げ%.2f・たわみ%.2f）、内の柱の軸力 長期%.0f・雪%.0f kN'
              % (t, t / 3, De * 1000, Dm * 1000, rs, rd, -NL['I'], -NS['I']))
        for C in (240, 300, 360, 440):
            if C - 2 * t / 3 <= 0:
                continue
            g, o = col_check(C, t, NL, NS)
            ok = all(v <= 1 for v in o.values())
            print('   柱%d：光の筋%.0f  ' % (C, g) + '・'.join('%s %.2f' % kv for kv in o.items()) + ('  ○' if ok else '  ×'))
