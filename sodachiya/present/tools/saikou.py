"""採光の図（光の環境）の下書き：本館の横断の上に重ねる素材（プレゼンの準備、10-29、ユーザー「採光の図、ドラフトしていただけますか？」）。

描くもの（決定事項（共通）の「屋根・光・電気」「屋根の構成」、決定事項_本館の「屋根：光の筋と太陽光」「越屋根」）：
- 光の筋：2枚の梁のあいだ180の上の乳白ガラスから入る空の光が、鏡面のアルミの溝を下りて梁の下へ（約8割、杉のままなら約1割）。
  保育室の暗い帯（西から約2〜8 m）を明るくする。溝の向きの断面は小さな差し込みの図（断面Cは1/25、断面Dは1/30）で。
- 越屋根（白の艶消しの木のルーバーのすき間＋ガラスの蓋）から、西の吹き抜けと奥へ落ちる上からの柔らかい光。
- 東の縁側のガラス戸と深い軒：朝9時（太陽時）の日を、夏至・春秋分・冬至で。断面の面に映した高度（プロファイル角）で描く。
  南中の日はこの東西の断面ではほぼ真上（82〜89°）なので、軒と屋根が受ける。軒先とガラスの足を結ぶ角より高い日はガラスに当たらない。
- 光だけに集中する（ユーザー 10-29 13:09）：空気・空調・換気の線と注は描かない。昼光率（曲線と数）は語らない（ユーザーが検証できないため）。
  見本の下地からも空気の注（AIR_NOTES の文字と AIR_RGB の色の線）を消して見せる。断面Dでも同じ。

形はすべて3dm（model/sodachiya_exact_mesh.3dm）から、紙の位置は drawings/<紙>_views.json の draw_to_paper で。
断面Cは架構の線で切っていないので、切り口の奥の架構の線（いちばん近い光の筋）の形を使う。
断面D（光の筋で切る）ができたら：python3 present/tools/saikou.py --paper <紙の名前> --view 断面D

出力：
- present/sozai/17_光の環境_断面.pdf：重ねる図だけ（地は透明、文字は Type42）。紙の mm のまま（1 mm＝1 mm）、
  ページの左上＝紙の (PAGE[0], PAGE[1]) mm（present/sozai/17_光の環境_断面.json に書く）。Illustrator ではその位置で断面に重ねる。
- present/out/saikou_preview.png：断面の同じ範囲に重ねた見本（長辺1600 px 以下）。
"""
import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))           # sodachiya/
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import fonts42  # noqa: F401  Noto を Type42 で埋め込む
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, FancyArrowPatch

LAT = 35.0                                       # 京都
MESH = os.path.join(ROOT, "model", "sodachiya_exact_mesh.3dm")

# 色
SUN = {"夏至": "#E07B1F", "春秋分": "#E8A317", "冬至": "#D9B21A"}
SKY, SKY_F = "#5E94C8", "#BFD7EE"               # 拡散光（空の光）：線・面
INK = "#4A5562"                                  # 注の文字
PT = 72 / 25.4


# ---------------------------------------------------------------- 太陽
def sun(dec, t):
    """dec：赤緯（度）、t：太陽時（時）→ 高度・方位（度、北から時計回り）"""
    L, d, h = np.radians(LAT), np.radians(dec), np.radians((t - 12) * 15)
    alt = np.arcsin(np.sin(L) * np.sin(d) + np.cos(L) * np.cos(d) * np.cos(h))
    az = np.arctan2(-np.cos(d) * np.sin(h), np.sin(d) * np.cos(L) - np.cos(d) * np.cos(h) * np.sin(L))
    return np.degrees(alt), np.degrees(az) % 360


def profile(dec, t, right):
    """断面の面に映した太陽の高度（度、断面の右＝東の側から）。right：3dm の断面の右の向き（+Y＝北）。"""
    a, az = sun(dec, t)
    az_r = np.degrees(np.arctan2(right[0], right[1]))
    c = np.cos(np.radians(az - az_r))
    return a, az, (np.degrees(np.arctan2(np.tan(np.radians(a)), c)) if c > 1e-6 else None)


def time_at_profile(dec, ang, right, t0=6.0, t1=12.0):
    ts = np.linspace(t0, t1, 3601)
    for t in ts:
        p = profile(dec, t, right)[2]
        if p is not None and p >= ang:
            return t
    return None


# ---------------------------------------------------------------- 3dm の形
def geometry(view):
    import rhino3dm as r
    O, R, D = (np.array(view[k], float) for k in ("origin", "right", "view_dir"))
    m = r.File3dm.Read(MESH)
    L = {i: l.Name for i, l in enumerate(m.Layers)}

    def pts(g):
        if isinstance(g, r.Mesh):
            P = np.array([(g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z) for i in range(len(g.Vertices))])
        elif isinstance(g, (r.Extrusion, r.Brep)):
            b = g.ToBrep(False) if isinstance(g, r.Extrusion) else g
            P = np.array([(v.Location.X, v.Location.Y, v.Location.Z) for v in (b.Vertices[i] for i in range(len(b.Vertices)))])
        else:
            return None
        P = P - O
        return np.c_[P @ R, P @ D, P[:, 2] + O[2]]          # h, 奥行き d, z

    def slice_(g, d0):
        if not isinstance(g, r.Mesh): return []
        Q = pts(g); segs = []
        for i in range(len(g.Faces)):
            f = g.Faces[i]; idx = [f[0], f[1], f[2]] if f[2] == f[3] else [f[0], f[1], f[2], f[3]]
            s = []
            for a, b in zip(idx, idx[1:] + idx[:1]):
                da, db = Q[a, 1] - d0, Q[b, 1] - d0
                if (da < 0) != (db < 0):
                    t = da / (da - db); p = Q[a] + t * (Q[b] - Q[a]); s.append((p[0], p[2]))
            if len(s) >= 2: segs.append(s[:2])
        return segs

    objs = [(L[o.Attributes.LayerIndex], o.Geometry) for o in m.Objects]
    by = lambda pre: [(n, g) for n, g in objs if n.startswith(pre)]
    depth = view.get("depth_mm", 3200)

    # 光の筋：切り口から奥（見る向き）のいちばん近い架構の線の乳白ガラス（長いもの）
    slots = []
    for n, g in by("10t"):
        Q = pts(g)
        if Q is not None and np.ptp(Q[:, 0]) > 5000 and -300 < Q[:, 1].mean() < depth:
            slots.append((Q[:, 1].mean(), Q))
    d_s, Q = min(slots, key=lambda s: s[0])
    i0, i1 = Q[:, 0].argmin(), Q[:, 0].argmax()
    G = dict(slot_d=d_s, glass=((Q[:, 0].min(), Q[Q[:, 0] < Q[:, 0].min() + 50, 2].max()),
                                (Q[:, 0].max(), Q[Q[:, 0] > Q[:, 0].max() - 50, 2].max())))
    # 鏡面（溝の両側）：その架構の線のもの。下の縁＝梁の下端、上の縁＝ガラスの下
    mir = [pts(g) for n, g in by("10m")]
    mir = [q for q in mir if q is not None and abs(q[:, 1].mean() - d_s) < 250]
    side = min(np.unique(np.round([q[:, 1].mean() for q in mir], -1)), key=lambda x: abs(x - d_s))
    pieces = sorted([q for q in mir if abs(q[:, 1].mean() - side) < 60], key=lambda q: q[:, 0].min())
    soffit, top = [], []
    for q in pieces:
        hz = np.unique(np.round(q[:, [0, 2]], 0), axis=0)
        for h in np.unique(np.round(hz[:, 0] / 10) * 10):
            zz = hz[np.abs(hz[:, 0] - h) < 10, 1]
            soffit.append((h, zz.min())); top.append((h, zz.max()))
    soffit.sort(); top.sort()
    G["soffit"], G["mirror_top"] = soffit, top
    # 柱（東）：その架構の線の東の柱
    cols = []
    for n, g in by("11a"):
        q = pts(g)
        if q is not None and abs(q[:, 1].mean() - d_s) < 400:
            cols.append(q)
    ce = max(cols, key=lambda q: q[:, 0].mean())
    G["col_e"] = (ce[:, 0].min(), ce[:, 0].max(), ce[:, 2].max())
    # 縁側のガラス戸（全高のガラス）：切り口にいちばん近いもの
    ds = []
    for n, g in by("16d"):
        q = pts(g)
        if q is not None and np.ptp(q[:, 2]) > 2000:
            ds.append((abs(q[:, 1].mean()), q))
    q = min(ds, key=lambda s: s[0])[1]
    G["door"] = (q[:, 0].mean(), q[:, 2].min(), q[:, 2].max())
    # 切り口の面（d＝少し奥）で、軒先・越屋根の蓋・床・西の外壁を切る
    dc = min(60.0, d_s)
    eave = [p for n, g in by("10_") for s in slice_(g, dc) for p in s]
    eave = np.array(eave); ht = eave[:, 0].max()
    G["eave_tip"] = (ht, eave[eave[:, 0] > ht - 30, 1].min(), eave[eave[:, 0] > ht - 30, 1].max())
    lid = np.array([p for n, g in by("50a") for s in slice_(g, dc) for p in s])
    G["lid"] = (lid[:, 0].min(), lid[:, 0].max(), lid[:, 1].min(), lid[:, 1].max())
    lv = []                                            # 越屋根の木のルーバー：板ごとの中心と板の向き
    for n, g in by("50c"):
        q = np.array([p for s_ in slice_(g, dc) for p in s_])
        if len(q) < 3: continue
        c_ = q.mean(0); u, sv, vt = np.linalg.svd(q - c_)
        ax_ = vt[0] if vt[0][1] < 0 else -vt[0]       # 板の向き（下向き）
        lv.append((c_, ax_))
    G["louvers"] = sorted(lv, key=lambda t: t[0][0])
    fl = np.array([p for n, g in by("12_") for s in slice_(g, dc) for p in s])
    G["west_in"] = fl[:, 0].min()
    G["d_cut"] = dc
    return G


def interp(poly, h):
    a = np.array(poly)
    return float(np.interp(h, a[:, 0], a[:, 1]))


# ---------------------------------------------------------------- 割付（ページの左上からの mm）
# 越屋根の注 kosi、差し込み（溝の断面）inset と縮尺、東の注 east、行の間 lh。
# 断面D：3枚目では図の範囲（clip_paper_mm）の上に 30 mm の余白（mock.py の AIR_D）。差し込みと東の注はその余白に、
# 越屋根の注は断面Dの図の題の下に置く。
LAYOUT = {
    "断面C": dict(kosi=(17.5, 26.0), inset=(77.0, 4.0), inset_scale=25, east=(165.0, 20.0), lh=3.6),
    "断面D": dict(kosi=(17.5, 37.5), inset=(25.0, 0.8), inset_scale=30, east=(118.0, 1.8), lh=3.3),
}


# ---------------------------------------------------------------- 描く
def draw(paper, vname, out_pdf, out_json, out_png):
    vj = os.path.join(ROOT, "drawings", paper + "_views.json")
    view = [v for v in json.load(open(vj))["views"] if v["name"] == vname][0]
    T = view["draw_to_paper"]
    X = lambda h: T["a"] * h + T["c"]
    Y = lambda z: T["e"] * z + T["f"]
    G = geometry(view)
    right = view["right"]
    LY = LAYOUT.get(vname, LAYOUT["断面D"])

    hW = G["west_in"]                                  # 西の外壁の内面
    hd, zd0, zd1 = G["door"]                           # ガラス戸
    ht, zt0, zt1 = G["eave_tip"]                       # 軒先（下・上）
    l0, l1, lz0, lz1 = G["lid"]                        # 越屋根の蓋
    (g0, gz0), (g1, gz1) = G["glass"]                  # 光の筋のガラス
    c0, c1, cz = G["col_e"]
    zg = lambda h: gz0 + (gz1 - gz0) * (h - g0) / (g1 - g0)

    PAGE = tuple(float(round(v, 1)) for v in (X(hW - 1300), Y(lz1 + 5300), X(ht + 6600), Y(0) + 24))
    W, H = PAGE[2] - PAGE[0], PAGE[3] - PAGE[1]
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    fig.patch.set_alpha(0)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(PAGE[0], PAGE[2]); ax.set_ylim(PAGE[3], PAGE[1]); ax.axis("off")
    ax.patch.set_alpha(0)
    P = lambda h, z: (X(h), Y(z))

    def txt(x, y, s, size=2.7, c=INK, ha="left", va="center", w="normal", **k):
        return ax.text(x, y, s, fontsize=size * PT, color=c, ha=ha, va=va, fontweight=w, **k)

    def arrow(p, q, c, lw=0.5, ms=4.0, a=1.0, z=5):
        ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=ms, lw=lw, color=c, alpha=a,
                                     shrinkA=0, shrinkB=0, zorder=z))

    # ---- 光の筋：空の光 → 乳白ガラス → 鏡面の溝 → 梁の下へ
    sof = G["soffit"]
    seg = [(h, z) for h, z in sof if h <= c0 + 5] , [(h, z) for h, z in sof if h >= c1 - 5]
    for part in seg:                                   # 溝（ガラスの下〜梁の下端）を淡い青で
        if len(part) < 2: continue
        hs = [h for h, _ in part]
        poly = [P(h, zg(h) - 70) for h in hs] + [P(h, z) for h, z in part[::-1]]
        ax.add_patch(MPoly(poly, closed=True, fc=SKY_F, ec="none", alpha=0.55, zorder=2))
        ax.plot([X(h) for h, _ in part], [Y(z) for _, z in part], color=SKY, lw=0.35, zorder=3)
    # 梁の下へ広がる光（西から約2〜8 m を濃く）
    for k in range(10):
        f = k / 10
        z_lo = lambda h: interp(sof, h) - 300 - f * 1700
        hs = np.linspace(1800, 11700, 60)
        wgt = np.clip(1 - np.abs(hs - 5000) / 5200, 0.25, 1)
        poly = [P(h, interp(sof, h)) for h in hs] + [P(h, z_lo(h)) for h in hs[::-1]]
        ax.add_patch(MPoly(poly, closed=True, fc=SKY_F, ec="none", alpha=0.07 * (1 - f), zorder=1))
    for h in (2500, 4000, 5500, 7000):                 # 空 → ガラス
        arrow(P(h + 250, zg(h) + 900), P(h, zg(h) + 90), SKY, lw=0.55)
        z0 = interp(sof, h)
        arrow(P(h, z0 - 80), P(h - 120, z0 - 950), SKY, lw=0.5, a=0.9)
        arrow(P(h, z0 - 80), P(h + 260, z0 - 880), SKY, lw=0.4, a=0.6)
    for h in (8500, 10000):
        arrow(P(h + 250, zg(h) + 900), P(h, zg(h) + 90), SKY, lw=0.45, a=0.6)
    # ---- 越屋根：ルーバーのすき間とガラスの蓋から、西の吹き抜けと奥へ
    lvs = G["louvers"]
    gaps = [((c1_ + c2_) / 2, (a1_ + a2_) / 2) for (c1_, a1_), (c2_, a2_) in zip(lvs[:-1], lvs[1:])]
    for k, (c_, d_) in enumerate(gaps[1::3]):
        d_ = d_ / np.linalg.norm(d_)
        p0 = c_ - d_ * 650; p1 = c_ + d_ * 120          # 空 → すき間（板の向きに）
        arrow(P(*p0), P(*p1), SKY, lw=0.45, ms=3.0)
        z_end = 900 + 500 * (k % 3)                    # すき間 → 吹き抜けの下へ、少し広がりながら
        dx = (p1[0] - hW) * 0.25 + 150 * ((k % 2) - 0.5)
        arrow(P(p1[0], lz0 - 150), P(p1[0] - dx, z_end), SKY, lw=0.4, a=0.75)
    # 吹き抜けを満たす柔らかい光（上ほど濃く）
    hv0, hv1 = hW, G["glass"][0][0]
    for k in range(8):
        f = k / 8
        ax.add_patch(MPoly([P(hv0, lz0), P(hv1, lz0), P(hv1, lz0 - 600 - f * 3300), P(hv0, lz0 - 600 - f * 3300)],
                           closed=True, fc=SKY_F, ec="none", alpha=0.06 * (1 - f), zorder=1))
    arrow(P(hW + 60, 2300), P(hW + 1500, 1300), SKY, lw=0.4, a=0.7)         # 白い西の壁で返り、奥へ
    kx, ky = PAGE[0] + LY["kosi"][0], PAGE[1] + LY["kosi"][1]
    txt(kx, ky, "越屋根：ガラスの蓋とルーバーのすき間から", 2.9, SKY, w="bold")
    txt(kx, ky + 3.6, "上からの柔らかい光が西の吹き抜けと奥へ", 2.6, SKY)

    # ---- 東のガラス戸と深い軒：朝9時（太陽時）
    t9 = 9.0
    rays, rays_az = [], {}
    for nm, dec in (("夏至", 23.44), ("春秋分", 0.0), ("冬至", -23.44)):
        a, az, th = profile(dec, t9, right)
        tn = np.tan(np.radians(th))
        z_e = zt0 - (ht - hd) * tn                     # 軒先の下を通る線がガラスの面で
        top = min(zd1, z_e)
        reach = top / tn                               # 床の日だまりの奥行き（ガラスから西へ）
        rays.append((nm, dec, a, th, tn, top, reach)); rays_az[nm] = az
    for i, (nm, dec, a, th, tn, top, reach) in enumerate(rays):
        c = SUN[nm]
        h_in = hd - reach
        # 日の線：床の日だまりの奥 → ガラスの面の上の端（軒先の下を通る）→ 軒の外へ少し
        h_out = ht + 1500
        far = (h_out, (h_out - h_in) * tn)
        ax.add_patch(MPoly([P(h_in, 0), P(hd, top), P(hd, 0)], closed=True, fc=c, ec="none", alpha=0.13, zorder=1))
        ax.plot(*zip(P(h_in, 0), P(*far)), color=c, lw=0.55, zorder=4)
        ax.plot([X(h_in), X(hd)], [Y(0) - 0.35 - 0.55 * i] * 2, color=c, lw=1.4, solid_capstyle="butt", zorder=5)
        print(f"{nm} 9:00 高度 {a:.1f}° 方位 {rays_az[nm]:.1f}° → 断面の角 {th:.1f}°、床の日だまり {reach/1000:.2f} m")
    # 軒先とガラスの足を結ぶ角
    cut = np.degrees(np.arctan2(zt0, ht - hd))
    ax.plot(*zip(P(hd, 0), P(ht + 900, zt0 + 900 * np.tan(np.radians(cut)))), color=INK, lw=0.3, ls=(0, (3, 2)), zorder=4)
    tcut = {nm: time_at_profile(dec, cut, right) for nm, dec in (("夏至", 23.44), ("春秋分", 0.0), ("冬至", -23.44))}
    hm = lambda t: f"{int(t)}:{int(round((t % 1) * 60)):02d}"
    # 南中：この断面ではほぼ真上（屋根が受ける）
    noon = [(nm, *profile(dec, 12.0, right)[::2]) for nm, dec in (("夏至", 23.44), ("春秋分", 0.0), ("冬至", -23.44))]
    for nm, a, th in noon:
        print(f"{nm} 南中 高度 {a:.1f}° → 断面の角 {th:.1f}°")
    for i, (nm, a, th) in enumerate(noon):
        nx = 12700 + 160 * i
        tn = np.tan(np.radians(th)); z0 = zg(nx) + 10
        arrow(P(nx + 1100 / tn, z0 + 1100), P(nx, z0), SUN[nm], lw=0.45, ms=3.0)

    # 注：東（屋根の上の余白）
    ex, ey = PAGE[0] + LY["east"][0], PAGE[1] + LY["east"][1]
    L = [("深い軒（出約1.5 m）と縁側のガラス戸", 2.9, "bold"),
         ("ガラス戸は半分が片引き戸、半分は壁", 2.6, "normal"),
         (f"{cut:.0f}°より高い日はガラスに当たらない", 2.6, "normal"),
         (f"夏至{hm(tcut['夏至'])}・春秋分{hm(tcut['春秋分'])}・冬至{hm(tcut['冬至'])}から（太陽時）", 2.6, "normal"),
         (f"南中の日はこの断面ではほぼ真上（{min(t for _,_,t in noon):.0f}〜{max(t for _,_,t in noon):.0f}°）", 2.6, "normal")]
    for k, (s_, sz, w_) in enumerate(L):
        txt(ex, ey + LY["lh"] * k, s_, sz, INK, w=w_)
    for k, (nm, dec, a, th, tn, top, reach) in enumerate(rays):      # 日の線の凡例（朝9時、太陽時）
        yy = ey + LY["lh"] * (len(L) + k) + 0.6
        ax.plot([ex, ex + 4.0], [yy, yy], color=SUN[nm], lw=1.2, solid_capstyle="butt")
        txt(ex + 5.0, yy, f"{nm}の朝9時：断面の角{th:.0f}°、床の日だまり{reach / 1000:.1f} m", 2.6, SUN[nm], w="bold")

    # ---- 光の筋の溝の断面（差し込み、1/25）
    S = 1 / LY["inset_scale"]                         # 実寸 mm → 紙 mm
    ix, iy = PAGE[0] + LY["inset"][0], PAGE[1] + LY["inset"][1]   # 左上
    bw, gap, dep = 90, 180, 750
    ox = ix
    def R_(x0_, y0_, w_, h_, **k):
        ax.add_patch(plt.Rectangle((x0_, y0_), w_, h_, **k))
    y_g = iy + 3.5                                     # ガラスの下端
    for bx in (0, bw + gap):
        R_(ox + bx * S, y_g - 60 * S, bw * S, (dep + 60) * S, fc="#E9D9BF", ec="#7A6A55", lw=0.3, zorder=6)
    R_(ox + bw * S - 3 * S, y_g - 60 * S, (gap + 6) * S, 60 * S, fc="#EEF4FA", ec=SKY, lw=0.4, zorder=6)   # 乳白ガラス
    for xx in (ox + bw * S, ox + (bw + gap) * S):
        ax.plot([xx, xx], [y_g, y_g + dep * S], color="#9AA7B4", lw=0.9, zorder=7)                   # 鏡面
    # 跳ね返りながら下りる光
    xL, xR = ox + bw * S + 0.15, ox + (bw + gap) * S - 0.15
    Dp = dep * S
    pts = [(xL + 1.6, y_g - 3.2), (xL + 2.2, y_g + 0.2), (xR, y_g + 0.22 * Dp), (xL, y_g + 0.48 * Dp), (xR, y_g + 0.75 * Dp), (xL + 0.4 * (xR - xL), y_g + Dp + 3.5)]
    for p, q in zip(pts[:-1], pts[1:]):
        ax.plot(*zip(p, q), color=SKY, lw=0.5, zorder=8)
    arrow(pts[-2], pts[-1], SKY, lw=0.5, z=8)
    pts2 = [(xR - 1.0, y_g - 3.2), (xR - 1.3, y_g + 0.2), (xL, y_g + 0.33 * Dp), (xR, y_g + 0.62 * Dp), (xR - 0.4 * (xR - xL), y_g + Dp + 3.5)]
    for p, q in zip(pts2[:-1], pts2[1:]):
        ax.plot(*zip(p, q), color=SKY, lw=0.4, alpha=0.7, zorder=8)
    arrow(pts2[-2], pts2[-1], SKY, lw=0.4, a=0.7, z=8)
    tx = ox + (2 * bw + gap) * S + 2.0
    txt(tx, y_g - 0.5, f"光の筋：溝の断面1/{LY['inset_scale']}", 2.9, INK, w="bold")
    txt(tx, y_g + 1 * LY["lh"], "架構の線ごと、2枚の梁のあいだ180", 2.6, INK)
    txt(tx, y_g + 2 * LY["lh"], "上：乳白の複層ガラス（外は遮熱Low-E）", 2.6, INK)
    txt(tx, y_g + 3 * LY["lh"], "両側：鏡面のアルミ（反射率約0.95）、梁の下端まで", 2.6, INK)
    txt(tx, y_g + 4 * LY["lh"] + 0.6, "梁の下に出る光：鏡面で約8割", 2.6, SKY, w="bold")
    txt(tx, y_g + 5 * LY["lh"] + 0.6, "（杉の面のままなら約1割）", 2.6, INK)

    # ---- 保育室の暗い帯（西から約2〜8 m）を光の筋が照らす
    zb = interp(sof, 8000) - 250
    xa, xb = X(hW + 2000), X(hW + 8000)
    ax.plot([xa, xa, xb, xb], [Y(zb) - 1.0, Y(zb), Y(zb), Y(zb) - 1.0], color=SKY, lw=0.4, zorder=6)
    for k_, s_ in enumerate(("保育室の暗い帯（西から約2〜8 m）", "を光の筋が照らす")):
        txt(xa + 0.6, Y(zb) + 2.6 + 3.5 * k_, s_, 2.6, SKY, w="bold", zorder=6, bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.5))

    fig.savefig(out_pdf, transparent=True)
    plt.close(fig)
    meta = {"_": "17_光の環境_断面.pdf の位置：ページの左上＝基の紙の (x, y) mm、1 mm＝1 mm。present/tools/saikou.py が書く。",
            "base": f"drawings/{paper}.pdf", "view": vname, "page_paper_mm": list(PAGE),
            "frame_line_depth_mm": round(G["slot_d"]), "eave_cut_deg": round(cut, 1),
            "sun_9h_profile_deg": {nm: round(th, 1) for nm, _, _, th, *_ in rays},
            "noon_profile_deg": {nm: round(th, 1) for nm, _, th in noon},
            "glass_sunlit_until": {k: hm(v) for k, v in tcut.items()}}
    json.dump(meta, open(out_json, "w"), ensure_ascii=False, indent=1)
    preview(os.path.join(ROOT, "drawings", paper + ".pdf"), out_pdf, PAGE, out_png)
    print("軒の角", round(cut, 1), "ガラスに日が当たる終わり", {k: hm(v) for k, v in tcut.items()})
    print("PAGE", PAGE, "架構の線の奥行き", round(G["slot_d"]))


# 見本の下地から外す空気・空調・換気の注（採光の図は光だけ、ユーザー 10-29 13:09）。断面Dの下地にも使う
AIR_NOTES = ["越屋根のすき間から外へ", "梁間", "西へ上る", "夏の夜", "蹴込みのガラリ", "床下へ", "ガラス戸を開けて", "風", "空気", "換気", "空調",
             "冷気", "すき間の下で"]
AIR_RGB = [(0.1843137255, 0.4352941176, 0.6901960784)]   # 風の線と注の青（drawings の断面図）


def strip_air(base):
    """下地のPDFから空気の注（文字）と風の青い線を消した写しを返す（見本だけに使う。drawings/ は書き換えない）。"""
    import fitz, re
    d = fitz.open(base); p = d[0]
    for b in p.get_text("dict")["blocks"]:
        if b["type"] != 0: continue
        for l in b["lines"]:                           # 行ごと（同じ塊に別の注が入っていることがある）
            t = "".join(s_["text"] for s_ in l["spans"])
            if any(k in t for k in AIR_NOTES):
                p.add_redact_annot(fitz.Rect(l["bbox"]))
    p.apply_redactions(images=0, graphics=0)
    # 青い線：その色の後は透明に（CA/ca 0）、ほかの色の後は不透明に戻す
    p.clean_contents()
    xref = p.get_contents()[0]
    st = d.xref_stream(xref)
    blue = [rb"%.4f %.4f %.4f" % c for c in AIR_RGB]
    def rep(m):
        vals = tuple(float(v) for v in m.group(1).split())
        isb = any(all(abs(a - b) < 2e-3 for a, b in zip(vals, c)) for c in AIR_RGB)
        op = m.group(2)
        g = (b"/AirS0" if op == b"RG" else b"/AirF0") if isb else (b"/AirS1" if op == b"RG" else b"/AirF1")
        return m.group(0) + b" " + g + b" gs"
    st = re.sub(rb"((?:[\d.]+ ){2}[\d.]+) (RG|rg)", rep, st)
    d.update_stream(xref, st)
    res = d.xref_get_key(p.xref, "Resources")
    gsx = {}
    for nm_, k_, v_ in (("AirS0", "CA", 0), ("AirS1", "CA", 1), ("AirF0", "ca", 0), ("AirF1", "ca", 1)):
        x_ = d.get_new_xref(); d.update_object(x_, f"<< /Type /ExtGState /{k_} {v_} >>"); gsx[nm_] = x_
    rx = p.xref
    for nm_, x_ in gsx.items():
        d.xref_set_key(rx, f"Resources/ExtGState/{nm_}", f"{x_} 0 R")
    return d


def preview(base, ovl, PAGE, out_png, px=1600):
    import fitz
    mm = 72 / 25.4
    W, H = (PAGE[2] - PAGE[0]) * mm, (PAGE[3] - PAGE[1]) * mm
    d = fitz.open(); pg = d.new_page(width=W, height=H)
    pg.draw_rect(pg.rect, color=None, fill=(1, 1, 1))
    b = strip_air(base)
    pg.show_pdf_page(pg.rect, b, 0, clip=fitz.Rect(PAGE[0] * mm, PAGE[1] * mm, PAGE[2] * mm, PAGE[3] * mm))
    pg.show_pdf_page(pg.rect, fitz.open(ovl), 0)
    z = px / max(W, H)
    pg.get_pixmap(matrix=fitz.Matrix(z, z)).save(out_png)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", default="sodachiya_sections2_1-100")
    ap.add_argument("--view", default="断面D")
    ap.add_argument("--name", default="17_光の環境_断面")
    a = ap.parse_args()
    S = os.path.join(ROOT, "present", "sozai"); O = os.path.join(ROOT, "present", "out")
    draw(a.paper, a.view, os.path.join(S, a.name + ".pdf"), os.path.join(S, a.name + ".json"), os.path.join(O, "saikou_preview.png"))
