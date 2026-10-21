# 0・1歳（plan01.py）と 2歳（plan02.py）の家具配置を 1/200 の配置図へ移す。
# plan01/02 と同じ本館の座標 (u: 南の妻から北へ m, v: 西の外壁から東へ m) をそのまま使う。
import math
import numpy as np
from matplotlib.patches import Polygon

K = 0.55          # line-weight factor for 1/200

def draw(ax, W, z0=4.0):
    def pts_rect(u0, u1, v0, v1, n=4):
        return [W(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [W(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]
    def fill(u0, u1, v0, v1, c, z=0):
        ax.add_patch(Polygon(pts_rect(u0, u1, v0, v1), closed=True, fc=c, ec="none", zorder=z0 + 0.1 + z * 0.01))
    def box(u0, u1, v0, v1, lw=0.45, fc="white", ls="-", z=3, ec="black"):
        ax.add_patch(Polygon(pts_rect(u0, u1, v0, v1), closed=True, fc=fc, ec=ec, lw=lw * K, ls=ls, zorder=z0 + 0.3 + z * 0.02))
    def line(uv, lw=0.45, ls="-", c="black", z=3):
        xs, ys = zip(*[W(u, v) for u, v in uv]); ax.plot(xs, ys, lw=lw * K, ls=ls, color=c, zorder=z0 + 0.3 + z * 0.02, solid_capstyle="butt")
    def wall(u0, u1, v0, v1):
        box(u0, u1, v0, v1, lw=0.4, fc="#333333", z=5)
    def ell(u, v, wv, hu, fc="white", ec="black", lw=0.35, z=4, ls="-"):
        t = np.linspace(0, 2 * math.pi, 28)
        ax.add_patch(Polygon([W(u + hu / 2 * math.sin(a), v + wv / 2 * math.cos(a)) for a in t], closed=True, fc=fc, ec=ec, lw=lw * K, ls=ls, zorder=z0 + 0.3 + z * 0.02))
    def txt(u, v, s, size=5.5, **kw):
        x, y = W(u, v); ax.text(x, y, s, fontsize=size, ha="center", va="center", zorder=z0 + 0.5, rotation=-3, **kw)

    C_01, C_2, C_ROOF, C_WET, C_DOMA, C_OUT = "#E6EFC2", "#C5DE9A", "#F4EBDD", "#D5EBEE", "#E4E1DA", "#EEF3E6"
    # ================= 0・1歳 (u 0–12) =================
    fill(0, 12, 1.6, 12, C_01)
    fill(9, 12, 1.6, 4.6, C_WET, 1); fill(12, 13.6, 1.6, 4.6, C_WET, 1)
    fill(0, 6, 0, 1.6, C_DOMA)
    fill(6, 13.6, 0, 1.0, C_ROOF); fill(9, 13.6, 1.0, 1.6, C_ROOF)
    fill(6, 9, 1.0, 1.6, "#DCE7B0", 1)
    fill(0, 12, 12, 15, C_ROOF)
    sw = south_engawa_uv()
    sw = [W(u, v) for u, v in sw] if sw else [W(0, 1.6), W(-2.4, 1.6)] + [W(-2.4 * (11.5 - v) / 9.9, v) for v in [3, 5, 7, 9, 11.5]] + [W(0, 11.5)]
    ax.add_patch(Polygon(sw, closed=True, fc=C_ROOF, ec="black", lw=0.45 * K, zorder=z0 + 0.12))
    # columns
    for uf in [0, 3, 6, 9, 12, 15, 18]:
        for vc in [0, 12]:
            box(uf - 0.09, uf + 0.09, vc - 0.2, vc + 0.2, lw=0.3, fc="black", z=6)
    # doma: low wall h600, kamachi, shikidai + gate, lattice rail
    box(0, 5.4, 1.6, 1.72, lw=0.4, fc="#999999", z=5)
    box(5.4, 6.0, 0.1, 1.0, fc="#F7F1E6"); line([(6.0, 0.08), (6.0, 1.0)], lw=0.8)
    box(6.0, 9.0, 0.98, 1.06, lw=0.3, z=5)
    # water core walls
    wall(9.0, 13.6, 1.6, 1.72); wall(11.93, 12.07, 1.6, 4.6); wall(12.0, 13.6, 4.55, 4.67)
    wall(11.94, 12.06, 4.6, 10.2); wall(11.94, 12.06, 11.4, 11.8)
    # water core furniture
    box(9.0, 9.7, 1.72, 3.2); box(9.0, 11.1, 3.9, 4.6); box(11.25, 11.93, 1.72, 2.7)
    ell(11.6, 2.2, 0.45, 0.75, fc="#F2F7F8", lw=0.3)
    # teacher's bench desk
    box(8.6, 9.0, 1.75, 3.15, fc="#F7F1E6"); box(7.85, 8.45, 1.85, 3.05)
    # 0-yr: check table, lockers, nest + canopy, cradles, mound, movable shelves
    box(3.6, 4.4, 1.95, 2.45); box(0.6, 4.1, 3.0, 3.4)
    fill(2.2, 5.6, 4.0, 7.6, "#F3F5E4", 2); box(2.2, 5.6, 4.0, 7.6, lw=0.6, fc="none", z=4)
    for vv in [(4.25, 5.45), (6.15, 7.35)]:
        for uu in [(2.45, 3.15), (3.55, 4.25), (4.65, 5.35)]:
            box(uu[0], uu[1], vv[0], vv[1], lw=0.3)
    for vc in [8.5, 9.7]:
        ell(3.0, vc, 0.5, 0.85, lw=0.35)
    ell(1.25, 9.6, 1.8, 2.4, fc="#DCE7B0", lw=0.4, z=2)
    for v0, v1 in [(3.5, 5.0), (6.4, 8.2), (9.0, 10.8)]:
        box(5.8, 6.2, v0, v1)
    # 1-yr: tables, lockers, cot cabinet, steps + slide, milk nook
    for u0 in [6.9, 9.5]:
        box(u0, u0 + 1.5, 5.5, 6.1)
    for vv in [(4.85, 5.9), (6.75, 7.8)]:
        for uc in [6.7, 7.65, 8.6, 9.55, 10.5]:
            box(uc, uc + 0.55, vv[0], vv[1], lw=0.25, ls=(0, (2, 1.5)), fc="none", ec="#6b7f3a", z=2)
    box(11.55, 11.94, 5.0, 7.0); box(11.3, 11.94, 7.1, 8.35, lw=0.5, fc="#DDDDDD")
    box(7.4, 9.9, 9.2, 10.8); box(6.8, 7.4, 9.7, 10.3, lw=0.3)
    fill(10.3, 11.94, 8.5, 10.0, "#EAF4F6", 1); box(11.3, 11.94, 8.55, 9.95)
    line([(10.3, 8.5), (11.3, 8.5)], lw=0.9, c="#777777"); line([(10.3, 10.0), (11.3, 10.0)], lw=0.9, c="#777777")
    line([(10.3, 8.5), (10.3, 9.0)], lw=0.9, c="#777777"); line([(10.3, 9.6), (10.3, 10.0)], lw=0.9, c="#777777")
    # laundry nook on the path, drying poles overhead
    box(9.15, 11.85, 0.95, 1.6, lw=0.5, fc="#EEF5F7", z=4)
    for vp in [0.4, 1.2]:
        line([(6.2, vp), (17.8, vp)], lw=0.5, ls=(0, (5, 1.5, 1, 1.5)), c="#3d6f8a", z=7)
    # engawa: insulated glass doors in the middle (r = 191.5, v = 13.5; same as 3-5, 3dm 10-21), outer half is shoes-on (−150)
    fill(0, 18, 13.5, 15, "#E9E2D4", 1)
    line([(0, 13.5), (18, 13.5)], lw=0.9, c="#3d7fb0", z=6)
    for a, b in [(0, 2.2), (3.2, 8.4), (9.4, 15.0), (16.0, 18.0)]:
        box(a, b, 14.9, 15.0, lw=0.3, fc="#bbbbbb", z=5)
    for g0, g1 in [(2.2, 3.2), (8.4, 9.4), (15.0, 16.0)]:
        box(g0 - 0.2, g1 + 0.2, 15.0, 15.3, lw=0.3); box(g0 - 0.2, g1 + 0.2, 15.3, 15.6, lw=0.3)
        line([(g0 + 0.1, 15.08), (g1 - 0.1, 15.08)], lw=1.6, c="#7b5ea7", z=6)
    box(11.97, 12.03, 12.2, 13.0, lw=0.3, fc="#bbbbbb", z=5); box(11.97, 12.03, 13.9, 14.6, lw=0.3, fc="#bbbbbb", z=5)
    # south outside: bassinets, crawl-out mound + two steps, shed on the garden side of the fence
    for vc in [2.4, 3.4]:
        ell(-1.0, vc, 0.5, 0.8, lw=0.3)
    ell(-2.4, 7.2, 2.4, 2.0, fc="#DCE7B0", lw=0.4, z=0)
    box(-2.1, -1.65, 4.6, 5.6, lw=0.3, z=2); box(-2.55, -2.1, 4.6, 5.6, lw=0.3, z=2)
    box(-4.3, -2.6, 1.7, 2.75, lw=0.5, fc="#EDE6D6", z=3)
    line([(-4.3, 1.7), (-2.6, 2.75)], lw=0.2); line([(-4.3, 2.75), (-2.6, 1.7)], lw=0.2)
    # morning garden (east of the engawa): grain play field, bank + hedge, two trees, big kids' bench
    fill(0, 12, 15.6, 22.0, C_OUT, -1)
    for a, b in [(-0.5, 2.6), (4.2, 8.0), (9.8, 13.0)]:
        line([(a, 21.2), (b, 21.2)], lw=0.7, ls=(0, (1, 1.5)), c="#5a7a3a"); line([(a, 21.7), (b, 21.7)], lw=0.7, ls=(0, (1, 1.5)), c="#5a7a3a")
    ell(5.5, 18.3, 2.2, 3.2, fc="#F4EFE2", ls=(0, (2, 1.5)), lw=0.4, z=1)
    for (uu, vv) in [(1.5, 17.6), (10.3, 18.6)]:
        ell(uu, vv, 3.2, 3.2, fc="#DCE8C8", ec="#5a7a3a", lw=0.5, z=1)
    box(4.0, 6.5, 15.15, 15.5, lw=0.3)

    # ================= 2歳 (u 12–18) =================
    fill(12, 18, 1.6, 12, C_2); fill(12, 14.7, 1.6, 4.6, C_WET, 1); fill(12, 18, 1.2, 1.6, "#D8E8B6", 1)
    fill(12, 18, 12, 15, C_ROOF)
    wall(14.63, 14.77, 1.6, 4.6); wall(17.95, 18.07, 1.6, 12.0); wall(12.0, 14.7, 1.6, 1.72)
    for uc in [13.15, 13.85, 14.45]:
        ell(uc, 2.1, 0.42, 0.34, lw=0.3)
    box(14.77, 15.12, 1.75, 4.55); box(15.9, 16.3, 2.2, 4.0, fc="#F7F1E6"); box(17.3, 17.95, 1.75, 3.0)
    box(16.9, 17.95, 3.3, 4.6, lw=0.6, fc="#E9DFC9", z=3)
    box(12.1, 13.3, 4.67, 5.2); box(12.07, 12.35, 6.0, 8.4); box(12.4, 13.3, 6.1, 8.3, lw=0.3, fc="#EFE6D2")
    for va in [5.9, 7.6]:
        box(13.6, 15.1, va, va + 0.6)
    box(16.2, 17.95, 5.0, 6.9, lw=0.3, ls=(0, (1, 1.2)), fc="#F6EFE0")
    box(12.07, 12.7, 8.55, 10.05, lw=0.5, fc="#DDDDDD")
    def hill(k, ru=1.9, re=2.2, rw=1.3, vc=9.6, n=30):
        out = []
        for i in range(n + 1):
            t = math.pi * i / n; r = re if math.cos(t) >= 0 else rw
            out.append(W(17.95 - ru * k * math.sin(t), vc + r * k * math.cos(t)))
        return out
    for k, fc in [(1.0, "#E3EDC9"), (0.66, "#D3E3AE"), (0.33, "#C3D894")]:
        ax.add_patch(Polygon(hill(k), closed=True, fc=fc, ec="black", lw=0.35 * K, zorder=z0 + 0.35))

    # captions
    txt(4.6, 10.9, "0歳", 6.5, color="#4d6b1f")
    txt(9.0, 7.3, "1歳", 6.5, color="#4d6b1f")
    txt(15.0, 5.0, "2歳", 6.5, color="#3d5a1a")

def south_engawa_uv():
    """南の縁側（ぽってり、すべて凸）の輪郭を 3dm から読む（14_本館_外縁側 の u<0 の部分）。読めなければ None。"""
    try:
        import os, rhino3dm as r
        from shapely.geometry import MultiPoint
        CX, CY, RW = 194.66293237, -41.34826335, 205.0177
        TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX) % (2 * math.pi)
        f = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model", "sodachiya_exact.3dm")
        m = r.File3dm.Read(f)
        lay = {l.Index: l.FullPath for l in m.Layers}
        for o in m.Objects:
            if lay[o.Attributes.LayerIndex].startswith("14_") and isinstance(o.Geometry, r.Mesh):
                pts = []
                for vtx in o.Geometry.Vertices:
                    x, y = vtx.X / 1000, vtx.Y / 1000
                    th = math.atan2(y - CY, x - CX) % (2 * math.pi)
                    pts.append(((TH_S - th) * RW, RW - math.hypot(x - CX, y - CY)))
                if max(p[0] for p in pts) <= 0.01:
                    return list(MultiPoint(pts).convex_hull.exterior.coords)
    except Exception:
        return None
    return None

# items for the legend: (number, u, v, text)
ITEMS = [
    (20, 3.9, 8.1, "ねどこ（ベビーベッド×6、囲い h900、布の天蓋）"),
    (21, 3.0, 11.0, "吊りかご×2（寝かしつけ）とほふくの丘"),
    (22, 10.3, 3.1, "水まわり：おむつ替え台・沐浴・手洗い（2歳トイレと背中合わせ）"),
    (23, 10.9, 9.25, "調乳（おむつと分ける、柵＋戸）"),
    (24, 8.15, 3.6, "先生の腰掛ける机（背はおむつ台の腰壁）"),
    (25, 8.0, 7.3, "1歳の食卓×2／午睡はコット×10（破線）・段々とすべり台"),
    (26, 5.7, 0.5, "式台＋木戸（2歳はここで靴を脱ぐ）、2歳の道 幅1.0"),
    (27, 13.6, 3.3, "2歳のトイレ（座る便器×3）・手洗い"),
    (28, 16.9, 10.6, "2歳の山（頂上 h900、中はかくれ家）"),
    (29, 17.0, 6.0, "ままごとの家（柱と低い屋根）・くぼみ・記録台"),
    (30, 6.0, 14.25, "縁側：中ほどに断熱ガラス戸、外の半分は土足（−150）"),
    (31, -1.0, 4.4, "南の縁側（外気浴）と這い出せる一点"),
    (32, -3.45, 3.4, "外の物置（散歩車・砂場の道具）"),
    (33, 5.5, 19.9, "朝の庭（粒の遊び場、土手＋生垣）"),
]
