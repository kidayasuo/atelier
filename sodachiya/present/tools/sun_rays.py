"""太陽の線（1枚目の配置図の方位、ユーザー 10-26夜）。
地は濃い丸、太陽の向きへ1時間ごとの太い線。線の長さ＝上から見た太陽の位置（中心に近いほど高い）、
色＝高度（低いほど赤く、高いと白）、夏至と冬至は同じ色の決まり。北は丸の中に白抜きの矢印。
線は高度 MIN_ALT 以上の正時だけ（夏至と冬至の始まりと終わりをだいたい同じ明るさに）。時刻は京都の太陽時（日本の標準時とは数分の差）。
文字（時刻・N）はここでは描かず、場所を返す（Illustratorで Apple Chancery の文字の部品にする）。"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

LAT = np.radians(35.05)
MIN_ALT = 8.0
BG, NCOL = "#3E4652", "#D8DCE2"
STOPS = [(0, "#E4502C"), (6, "#FF9340"), (15, "#FFC45C"), (30, "#FFE6A6"), (55, "#FFFFFF"), (90, "#FFFFFF")]


def sun(dec, H):
    d, h = np.radians(dec), np.radians(H)
    alt = np.arcsin(np.sin(LAT) * np.sin(d) + np.cos(LAT) * np.cos(d) * np.cos(h))
    az = np.arctan2(-np.cos(d) * np.sin(h), np.sin(d) * np.cos(LAT) - np.cos(d) * np.cos(h) * np.sin(LAT))
    return alt, az % (2 * np.pi)


def scol(adeg):
    for (a0, c0), (a1, c1) in zip(STOPS[:-1], STOPS[1:]):
        if adeg <= a1:
            t = (adeg - a0) / (a1 - a0)
            return tuple(np.array(to_rgb(c0)) * (1 - t) + np.array(to_rgb(c1)) * t)
    return to_rgb(STOPS[-1][1])


def make(path, north_deg, R=20.0, margin=5.0, lw_pt=1.8):
    """north_deg：紙の上で北の向き（+xから反時計回り、度）。R：線の最大の長さ（mm）。
    戻り値：(直径mm, 文字のリスト[(s, x, y, ha)]（丸の左下からmm、y上向き）)"""
    NA = np.radians(north_deg)
    pdir = lambda az: np.array([np.cos(NA - az), np.sin(NA - az)])
    D = 2 * (R + margin)
    c = np.array([R + margin, R + margin])
    fig = plt.figure(figsize=(D / 25.4, D / 25.4))
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, D); ax.set_ylim(0, D); ax.set_aspect(1); ax.axis("off")
    ax.add_patch(plt.Circle(tuple(c), R + margin * 0.8, fc=BG, ec="none", zorder=0))
    labels = []
    for dec, z in ((-23.44, 2), (23.44, 3)):
        hrs = [h for h in range(0, 24) if np.degrees(sun(dec, (h - 12) * 15)[0]) >= MIN_ALT]
        for h in hrs:
            a, az = sun(dec, (h - 12) * 15)
            k = np.sin(a)
            al = 0.82 + 0.18 * min(1, k / np.sin(np.radians(60)))
            p = c + pdir(az) * R * np.cos(a)
            ax.plot([c[0], p[0]], [c[1], p[1]], color=(*scol(np.degrees(a)), al), lw=lw_pt, solid_capstyle="round", zorder=z)
            if h in (hrs[0], hrs[-1]) or (dec < 0 and h == 12):
                q = c + pdir(az) * (R * np.cos(a) + 2.4)
                labels.append((str(h), q[0], q[1], "center"))
    n = pdir(0)
    ax.annotate("", xy=tuple(c + n * (R + 1)), xytext=tuple(c + n * (R - 7)),
                arrowprops=dict(arrowstyle="-|>,head_length=0.35,head_width=0.18", lw=0.7, color=NCOL), zorder=7)
    q = c + n * (R - 10)
    labels.append(("N", q[0], q[1], "center"))
    fig.savefig(path, transparent=True)
    plt.close(fig)
    return D, labels
