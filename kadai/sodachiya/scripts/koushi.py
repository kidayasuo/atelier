# 高野川沿いの木の縦格子の柵（ユーザー 10-31：だいさんかく・しずかのもり・みなみのさんかくを一続きに）。
# 寸法は data/approachA.json の RIVER_LATTICE。クリの心材、無塗装。横材は上（笠木）と下だけ、格子のすき間 gap 以下。
# 柱はステンレスの柱脚金物（GL〜GL+foot）に載せ、土から離す。格子は上下の横材にビスで一本ずつ留める（取り替えられる）。
# 座標は 3dm の xy（m）。layout() が柱・格子の位置を決め、plan() が平面の線、to3dm() が閉じた箱を作る。
import os, json, math
import numpy as np
from shapely.geometry import Polygon, LineString, Point

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
R = json.load(open(os.path.join(_ROOT, "data", "approachA.json"), encoding="utf-8"))["RIVER_LATTICE"]
SITE = [(0.0, 0.0), (34.86, -43.83), (-14.44, -83.04), (-21.91, -73.65), (-25.83, -20.54)]   # approachA.SITE と同じ


def _gc():
    """garden_common（園庭）の座標の変換を借りる。読み込むときに model/build/south を sys.path の先頭に足すので、元に戻す
    （そこにも yamato.py があり、approachA.py の import yamato が取り違える）"""
    import sys
    keep = list(sys.path)
    import garden_common as gc
    sys.path[:] = keep
    return gc


def _uv2xy(u, v):
    return _gc().UV(u, v)


def _frame():
    """敷地の南東の辺（高野川の崖の上の縁）：東の角 E から南の角へ t、内側へ n"""
    E, S = np.array(SITE[1]), np.array(SITE[2])
    t = (S - E) / np.linalg.norm(S - E); n = np.array([-t[1], t[0]])
    if n @ (np.mean(np.array(SITE), axis=0) - E) < 0: n = -n
    return E, t, n


def layout():
    """{'posts': [(s, 半幅, 自分の柱か)], 'segs': [(s0, s1)], 'bays': [(s0, s1)], 'P': s→xy, 't', 'n'}（s は東の角からの距離 m）"""
    import minami_common as MN
    gc = _gc()
    E, t, n = _frame(); ins = R["inset"]
    def P(s, o=0.0): q = E + t * s + n * (ins + o); return (float(q[0]), float(q[1]))
    def s_of(xy): return float((np.array(xy) - E) @ t)
    hw = R["post"]["w"] / 2
    # 東の端：北東の隣地の境（SITE[0]→E）から end_gap 内側で止める
    ne = LineString([SITE[0], SITE[1]])
    s_end = 0.0
    while Point(P(s_end)).distance(ne) < R["end_gap"] + hw: s_end += 0.005
    s_end += hw                                                                  # 東の端の柱の中心
    # 木戸の柱（みなみのさんかく、120 角）：東の木戸の川の側の柱、西の非常用の門の柱
    gates = {nm: h for nm, h, e, hh, deg in MN.gates()}
    e_post = _uv2xy(gates["東の木戸・親扉"][1], gates["東の木戸・親扉"][0])
    w_post = _uv2xy(gates["西の門・子扉"][1], gates["西の門・子扉"][0])
    s_e, s_w = s_of(e_post), s_of(w_post)
    GHW = 0.06 + 0.005                                                           # 木戸の柱の半幅（面で止める）
    avoid = [s_of(gc.X(56.0, d)) for d in R["avoid"]["garden_d"]]
    def spaced(sa, sb):
        k = max(1, math.ceil((sb - sa) / R["post"]["pitch"] - 1e-6))
        out = list(np.linspace(sa, sb, k + 1)[1:-1])
        for i, s in enumerate(out):
            for c in avoid:
                if abs(s - c) < R["avoid"]["clear"]:
                    out[i] = c - R["avoid"]["clear"] if s < c else c + R["avoid"]["clear"]
        return out
    posts = [(s_end, hw, True)] + [(s, hw, True) for s in spaced(s_end, s_e)] + [(s_e, GHW, False)] \
        + [(s, hw, True) for s in spaced(s_e, s_w)] + [(s_w, GHW, False)]
    bays = [(a + ha, b - hb) for (a, ha, _), (b, hb, _) in zip(posts, posts[1:])]
    segs = [(s_end - hw, s_e - GHW), (s_e + GHW, s_w - GHW)]                   # 笠木は柱の上を通して、木戸の柱の面で止める
    return {"posts": posts, "bays": bays, "segs": segs, "P": P, "t": t, "n": n, "s_e": s_e, "s_w": s_w, "avoid": avoid}


def _rect(L, s0, s1, w, o=0.0):
    P = L["P"]
    return [P(s0, o - w / 2), P(s1, o - w / 2), P(s1, o + w / 2), P(s0, o + w / 2)]


def pickets(L):
    """格子の中心の s（各柱間で、すき間が gap 以下になる最少の本数を等しく割る）"""
    w, g = R["picket"]["w"], R["picket"]["gap"]; out = []
    for a, b in L["bays"]:
        c = b - a; k = max(0, math.ceil((c - g) / (w + g) - 1e-9))
        gap = (c - k * w) / (k + 1)
        out += [a + gap * (i + 1) + w * i + w / 2 for i in range(k)]
    return out


def max_gap(L):
    ps = pickets(L); w = R["picket"]["w"]; m = 0.0
    for a, b in L["bays"]:
        q = [s for s in ps if a < s < b]
        edges = [a] + sum([[s - w / 2, s + w / 2] for s in q], []) + [b]
        m = max(m, max(edges[i + 1] - edges[i] for i in range(0, len(edges), 2)))
    return m


def length(L):
    return L["segs"][-1][1] - L["segs"][0][0]


def plan(L, line, rect, wood="#7a5a36", lw=0.6, z=6.2, pickets_too=False):
    """平面：笠木の帯（細い二重線）と柱。pickets_too で格子も（1/50 用）。rect(pts, fc) は塗りの多角形"""
    for s0, s1 in L["segs"]:
        for o in (-R["top"]["w"] / 2, R["top"]["w"] / 2):
            line([L["P"](s0, o), L["P"](s1, o)], lw=lw * 0.5, c=wood, z=z)
    for s, hw, own in L["posts"]:
        if own: rect(_rect(L, s - hw, s + hw, R["post"]["w"]), wood)
    if pickets_too:
        for s in pickets(L): rect(_rect(L, s - R["picket"]["w"] / 2, s + R["picket"]["w"] / 2, R["picket"]["d"]), wood)


def to3dm(L, slab, lay_wood, lay_shoe):
    """閉じた箱：柱脚金物（lay_shoe）、柱・下の横材・格子・笠木（lay_wood、クリ）。z は GL＝0（m）"""
    h, ft = R["h"], R["post"]["foot"]; th = R["top"]["h"]; bz, bh = R["bottom"]["z"], R["bottom"]["h"]; n = 0
    for s, hw, own in L["posts"]:
        if not own: continue
        sh = R["post"]["shoe"] / 2
        slab(_rect(L, s - sh, s + sh, R["post"]["shoe"]), 0.0, ft, lay_shoe)
        slab(_rect(L, s - hw, s + hw, R["post"]["w"]), ft, h - th - ft, lay_wood); n += 2
    for a, b in L["bays"]:
        slab(_rect(L, a, b, R["bottom"]["w"]), bz, bh, lay_wood); n += 1
    for s in pickets(L):
        slab(_rect(L, s - R["picket"]["w"] / 2, s + R["picket"]["w"] / 2, R["picket"]["d"]), bz + bh, h - th - bz - bh, lay_wood); n += 1
    for s0, s1 in L["segs"]:
        slab(_rect(L, s0, s1, R["top"]["w"]), h - th, th, lay_wood); n += 1
    return n


if __name__ == "__main__":
    L = layout()
    print("lattice: length %.2f m, posts %d (own %d), bays %d, pickets %d, max gap %.3f m, max bay %.2f m"
          % (length(L), len(L["posts"]), sum(1 for p in L["posts"] if p[2]), len(L["bays"]), len(pickets(L)), max_gap(L),
             max(b - a for a, b in L["bays"])))
