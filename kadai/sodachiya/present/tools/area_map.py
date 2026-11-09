"""地域のなかの敷地（1枚目の素材14、ユーザー 10-27）。plateau_area.json.gz（PLATEAU）から北を上に 1/10000 で描く。
土地利用（水面・河川敷・公園・山林・田畑・公益施設）を淡い色、道路は白、建物は灰の足もと、敷地は朱の線と建物の屋根。
文字は描かず、場所を返す（Illustratorで文字の部品にする）。"""
import os, json, gzip, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
from shapely.geometry import Polygon
from shapely.ops import unary_union

LU_COL = {"204": "#CFE3EF", "205": "#DDE8D0", "217": "#D6E6C3", "203": "#C8DBB2", "201": "#EAF0DA", "202": "#EAF0DA", "260": "#EAF0DA", "214": "#EEEBE3"}
LU_Z = {"214": 0, "201": 1, "202": 1, "260": 1, "203": 2, "217": 3, "205": 4, "204": 5}


def make(path, data_gz, site_xy, roofs_xy, W=120.0, H=96.0, scale=10000, center=None):
    D = json.load(gzip.open(data_gz, "rt", encoding="utf-8"))
    c = np.array(center if center is not None else np.mean(site_xy, axis=0))
    k = 1000.0 / scale                                   # m → mm
    hw, hh = W / 2 / k, H / 2 / k
    fig = plt.figure(figsize=(W / 25.4, H / 25.4)); ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(c[0] - hw, c[0] + hw); ax.set_ylim(c[1] - hh, c[1] + hh); ax.set_aspect(1); ax.axis("off")
    clip = plt.Rectangle((c[0] - hw, c[1] - hh), 2 * hw, 2 * hh, fc="white", ec="none", zorder=-1); ax.add_patch(clip)
    big = {}
    for u in D["luse"]:
        if u["cls"] in LU_COL and len(u["xy"]) > 2:
            ax.add_patch(MP(u["xy"], closed=True, fc=LU_COL[u["cls"]], ec="none", zorder=1 + LU_Z[u["cls"]] * 0.01, clip_path=clip))
            big.setdefault(u["cls"], []).append(u["xy"])
    for r in D["road"]:
        if len(r["xy"]) > 2:
            ax.add_patch(MP(r["xy"], closed=True, fc="#FFFFFF", ec="#C9C9C9", lw=0.15, zorder=2, clip_path=clip))
    for b in D["bldg"]:
        if len(b["xy"]) > 2:
            ax.add_patch(MP(b["xy"], closed=True, fc="#C3C3C0", ec="none", lw=0, zorder=3, clip_path=clip))
    site = Polygon(site_xy)
    # 敷地にかかる今の建物は描かない（課題の敷地は空き地として）
    # 敷地は線で囲まず、色の濃さで（ユーザー、10-27）：地は周りの建物より濃い灰、屋根はさらに濃く
    ax.add_patch(MP(np.array(site.exterior.coords), closed=True, fc="#8E939A", ec="none", zorder=3.5))
    for g in roofs_xy:
        ax.add_patch(MP(g, closed=True, fc="#2E333A", ec="none", zorder=4))
    ax.add_patch(plt.Rectangle((c[0] - hw, c[1] - hh), 2 * hw, 2 * hh, fc="none", ec="#888888", lw=0.4, zorder=6))
    # 方位（北は上）と縮尺（200 m）
    nx, ny = c[0] + hw - 6 / k, c[1] + hh - 13 / k
    ax.annotate("", xy=(nx, ny + 7 / k), xytext=(nx, ny), arrowprops=dict(arrowstyle="-|>,head_length=0.5,head_width=0.25", lw=0.8, color="#333333"), zorder=7)
    sx0, sy0 = c[0] - hw + 4 / k, c[1] - hh + 4 / k
    ax.add_patch(plt.Rectangle((sx0 - 1.5 / k, sy0 - 1.5 / k), 200 + 3 / k, 3.4 / k, fc="white", ec="none", alpha=0.85, zorder=6.5))
    for i_ in range(2):
        ax.add_patch(plt.Rectangle((sx0 + i_ * 100, sy0), 100, 0.8 / k, fc="#333333" if i_ == 0 else "white", ec="#333333", lw=0.4, zorder=7))
    # 文字の候補の場所（紙の左下から mm）
    P = lambda xy: ((xy[0] - (c[0] - hw)) * k, (xy[1] - (c[1] - hh)) * k)
    lab = {}
    for cls, nm in (("204", "高野川"), ("214", "京都工芸繊維大学")):
        if cls in big:
            gs = [Polygon(x).buffer(0) for x in big[cls]]
            win = Polygon([(c[0] - hw, c[1] - hh), (c[0] + hw, c[1] - hh), (c[0] + hw, c[1] + hh), (c[0] - hw, c[1] + hh)])
            gs = [g.intersection(win) for g in gs]
            if cls == "214":                         # 大学は敷地の北の道の向こう（敷地から 150 m の中でいちばん大きい公益施設）
                near_ = [g for g in gs if g.distance(Polygon(site_xy)) < 150 and g.area > 5000]
                gs = near_ or gs
            g = max(gs, key=lambda g: g.area)
            if not g.is_empty:
                lab[nm] = P(np.array(g.representative_point().coords[0]))
    lab["敷地"] = P(np.array(site.centroid.coords[0]))
    lab["N"] = P((nx, ny + 9.5 / k))
    lab["0"] = P((sx0, sy0 + 1.6 / k)); lab["200 m"] = P((sx0 + 200, sy0 + 1.6 / k))
    fig.savefig(path, transparent=False, facecolor="white"); plt.close(fig)
    return lab
