"""6枚目の断面C（空気の環境）と断面D（光の環境）に重ねる図（プレゼンの準備。10-29 の採光の図を 11-01 に作り直した）。

ユーザー（11-01 23:19）：断面Dの光の線は「とても変、どれも意味不明」→ 作り直す。断面Cに空気の動き・天井扇・物干し竿を描き込む。
光の線は物理的に筋の通る向き（太陽の高さと、断面の面に映した角＝プロファイル角）で、季節・時刻を短い注に。乱反射・散乱は細い短い線の放射と淡い面で。

描くもの（決まりの本文：kettei/kyoutsu.md「屋根・光・電気」「屋根の構成」「換気の道」、kettei/honkan.md「越屋根」「屋根：光の筋と太陽光」、
kettei/nishikan.md「屋根」（棟のガラスの帯・排気のスリット・日よけのルーバー・東の高窓）、kettei/yugishitsu.md（覗き窓）、kettei/entei.md「冬の光」）：
- 断面C（空気、青）：夏の夜の道（段の蹴込みのガラリ→床下→西の壁ぎわの床のスリット→部屋→梁間を西へ上る→西の壁の上の縦格子→西吹き抜け→越屋根のすき間
  →すき間→覗き窓→遊戯室の吹き抜け→棟のガラスの帯の排気のスリット）、中間期の昼の道（縁側のガラス戸→部屋→越屋根のすき間から外へ／遊戯室は地窓→排気のスリット）、
  西吹き抜けの天井扇φ1100 h2.8（下向きに混ぜる）、物干しの竹竿（h3.1、昇降。断面Cの位置には無いが描く）。
- 断面D（光、黄〜橙）：西館＝棟のガラスの帯の外のルーバー（向きの合う朝の日だけ通る／高い日は白い板で乱反射）・光の筋の散乱光・東の高窓の朝の日。
  本館＝越屋根（西館の帯と同じルーバーの扱い）・教室の高窓（西の壁の上の縦格子）・光の筋（鏡面の光ダクト、型板ガラス）・
  東の深い軒（夏の高い日を遮る）と落葉樹（夏は葉が朝の低い日を遮り、冬は通す。断面Dの位置には無いが描く）。
- ルーバー（幅120・ピッチ104・東が高い30°）：板の水平の長さ＝120·cos30°＝104＝ピッチなので真上からは閉じている。
  断面に映した角が板の角30°に近い東からの日（板のすき間52、板の長さ120 → 30°±23°）だけ直接通り、ほかは白い艶消しの板に当たって乱反射する。

形は 3dm から（present/tools/kankyo_geo.py）、紙の位置は drawings/<紙>_views.json の draw_to_paper で。
出力（文字は Type42、地は透明、紙の mm のまま 1 mm＝1 mm。ページの左上＝紙の (PAGE[0], PAGE[1]) mm を .json に）：
- present/sozai/17_光の環境_断面.pdf・.json・_parts.json（断面D）
- present/sozai/30_空気の環境_断面.pdf・.json・_parts.json（断面C）
- 見本 /tmp/claude-0/saikou_<断面>.png（commit しない）
_parts.json は Illustrator の部品（layout.json の parts と同じ形）。group が図の中のサブグループ（矢印・線・注のまとまり）。
"""
import argparse, json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))           # sodachiya/
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, HERE)
import fonts42  # noqa: F401  Noto を Type42 で埋め込む
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
import kankyo_geo as KG

LAT = 35.0                                       # 京都
PT = 72 / 25.4
INK = "#4A5562"                                  # 注の文字（灰）
# 光（黄〜橙）：直射は季節で、乱反射・散乱は淡い黄
SUN = {"夏至": "#E0701A", "春秋分": "#E89A17", "冬至": "#D9B000"}
DIF, DIF_F = "#E3AE2E", "#F6D77E"                # 乱反射・散乱の線と面
LEAF = "#8BAA5A"                                 # 落葉樹の葉（夏）
# 空気（青）：夏の夜は濃い青（更新係の風の線と同じ）、中間期の昼は明るい青、天井扇は青緑
NIGHT, MIDA, FAN = "#2F6FB0", "#58A6D6", "#2B8C9E"
POLE = "#9C7A45"                                 # 竹竿・布（線）

# 割付の範囲（紙の mm、左上から）：mock.py の切り抜きと同じ。上へ 30 mm の余白（注と空の光）
CLIP = {"断面C": (432.0, 252.0, 830.0, 382.0)}   # mock.py の CLIP_C2
UP = 30.0


# ---------------------------------------------------------------- 太陽
def sun(dec, t):
    """dec：赤緯（度）、t：太陽時（時）→ 高度・方位（度、北から時計回り）"""
    L, d, h = np.radians(LAT), np.radians(dec), np.radians((t - 12) * 15)
    alt = np.arcsin(np.sin(L) * np.sin(d) + np.cos(L) * np.cos(d) * np.cos(h))
    az = np.arctan2(-np.cos(d) * np.sin(h), np.sin(d) * np.cos(L) - np.cos(d) * np.cos(h) * np.sin(L))
    return np.degrees(alt), np.degrees(az) % 360


def profile(dec, t, right):
    """断面の面に映した太陽の高度（度、断面の右＝東の側から。90°を超えると西の側から）"""
    a, az = sun(dec, t)
    az_r = np.degrees(np.arctan2(right[0], right[1]))
    c = np.cos(np.radians(az - az_r))
    return a, az, float(np.degrees(np.arctan2(np.tan(np.radians(a)), c)))


def time_at(dec, ang, right, t0=5.0, t1=12.0):
    for t in np.linspace(t0, t1, 4201):
        a, _, p = profile(dec, t, right)
        if a > 0 and p >= ang:
            return float(t)
    return None


DEC = {"夏至": 23.44, "春秋分": 0.0, "冬至": -23.44}
hm = lambda t: f"{int(t)}:{int(round((t % 1) * 60)):02d}"


def smooth(P, n=12):
    """点列を通る滑らかな線（Catmull-Rom）"""
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    Q = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-1])
    return np.array(out)


# ---------------------------------------------------------------- 描く道具（見本の PDF と Illustrator の部品を同時に）
class Zu:
    def __init__(self, view, PAGE, key):
        self.T = view["draw_to_paper"]
        self.PAGE, self.key = PAGE, key
        W, H = PAGE[2] - PAGE[0], PAGE[3] - PAGE[1]
        self.fig = plt.figure(figsize=(W / 25.4, H / 25.4))
        self.fig.patch.set_alpha(0)
        ax = self.fig.add_axes([0, 0, 1, 1]); ax.set_xlim(PAGE[0], PAGE[2]); ax.set_ylim(PAGE[3], PAGE[1]); ax.axis("off")
        ax.patch.set_alpha(0)
        self.ax = ax
        self.GR, self.TX, self.cur = {}, [], None

    X = lambda s, h: s.T["a"] * h + s.T["c"]
    Y = lambda s, z: s.T["e"] * z + s.T["f"]

    def P(self, h, z):
        return (self.X(h), self.Y(z))

    def grp(self, k, name):
        self.cur = f"{self.key}.{k}"
        self.GR.setdefault(self.cur, dict(id=self.cur, name=name, kind="lines", layer="説明", paths=[], group=self.cur, group_name=name))

    def _add(self, pts, stroke=None, fill=None, lw=0.0, dash=None, op=1.0, closed=False):
        hx = lambda c: matplotlib.colors.to_hex(c) if c is not None else None
        self.GR[self.cur]["paths"].append(dict(pts=[[round(float(a), 3), round(float(b), 3)] for a, b in pts], closed=closed,
                                               stroke=hx(stroke), fill=hx(fill), lw=round(float(lw), 3), dash=dash, op=round(float(op), 3), eo=False))

    def line(self, pts, c, lw=0.5, a=1.0, dash=None, z=5, cap="round"):
        pts = np.asarray(pts, float)
        k = dict(color=c, lw=lw, alpha=a, zorder=z, solid_capstyle=cap)
        if dash:
            k["ls"] = (0, dash)
        self.ax.plot(pts[:, 0], pts[:, 1], **k)
        self._add(pts, stroke=c, lw=lw, op=a, dash=[d * lw for d in dash] if dash else None)

    def poly(self, pts, fc, a=1.0, ec=None, lw=0.0, z=1):
        self.ax.add_patch(MPoly(pts, closed=True, fc=fc, ec=ec or "none", lw=lw, alpha=a, zorder=z))
        self._add(pts, stroke=ec, fill=fc, lw=lw, op=a, closed=True)

    def head(self, p, q, c, size=1.4, a=1.0, z=6):
        """q に向く矢じり（p→q の向き）。size：長さ mm"""
        p, q = np.array(p, float), np.array(q, float)
        u = (q - p) / max(np.linalg.norm(q - p), 1e-9); n = np.array([-u[1], u[0]])
        tri = [q, q - u * size + n * size * 0.42, q - u * size - n * size * 0.42]
        self.poly(tri, c, a=a, z=z)

    def arrow(self, pts, c, lw=0.55, a=1.0, dash=None, size=1.5, sm=True, z=5):
        """流れの線（紙の点列、滑らかに）と終わりの矢じり"""
        Q = smooth(pts) if sm and len(pts) > 2 else np.asarray(pts, float)
        # 矢じりの分だけ線を短く
        L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Q, axis=0), axis=1))]
        cut = L[-1] - size * 0.7
        k = max(1, int(np.searchsorted(L, cut)))
        Qs = np.vstack([Q[:k], Q[k - 1] + (Q[k] - Q[k - 1]) * ((cut - L[k - 1]) / max(L[k] - L[k - 1], 1e-9))])
        self.line(Qs, c, lw, a, dash, z)
        self.head(Q[max(0, len(Q) - 4)], Q[-1], c, size, a, z + 1)

    def harrow(self, pts_hz, c, **k):
        self.arrow([self.P(h, z) for h, z in pts_hz], c, **k)

    def ray(self, p_hz, ang, L0, L1, c, lw=0.7, a=1.0, head=True, dash=None, size=1.6):
        """日の線：点 p（h, z）を通る、東の側から角 ang（度、断面に映した高度）で下りてくる線。
        L0：p より空の側の長さ、L1：p より先の長さ（どちらも mm、実寸）。ang>90 は西の側から"""
        u = np.array([-np.cos(np.radians(ang)), -np.sin(np.radians(ang))])      # 下りる向き（h, z）
        p = np.array(p_hz, float)
        A, B = p - u * L0, p + u * L1
        if head:
            self.arrow([self.P(*A), self.P(*B)], c, lw, a, dash, size, sm=False)
        else:
            self.line([self.P(*A), self.P(*B)], c, lw, a, dash)
        return A, B

    def scatter(self, h, z, ang0, ang1, n=5, r0=0.6, r1=2.4, c=DIF, lw=0.3, a=0.9):
        """乱反射・散乱の光：点から ang0〜ang1（度、紙の上で右が0、上が90）に細い短い線の放射（紙の mm で r0〜r1）"""
        x, y = self.P(h, z)
        for t in np.linspace(ang0, ang1, n):
            u = np.array([np.cos(np.radians(t)), -np.sin(np.radians(t))])
            self.line([(x + u[0] * r0, y + u[1] * r0), (x + u[0] * r1, y + u[1] * r1)], c, lw, a, cap="butt")

    def txt(self, x, y, s, size=2.6, c=INK, w="normal", ha="left", key=None):
        """注（紙の mm、左上から）。いまのまとまり（grp）に入れる"""
        self.ax.text(x, y, s, fontsize=size * PT, color=c, ha=ha, va="baseline", fontweight=w, zorder=9)
        self.TX.append(dict(id=f"{self.cur}.t{key if key is not None else len(self.TX)}", name=f"注　{s[:20]}", kind="text", layer="説明",
                            x=round(x, 2), y=round(y, 2), s=s, size_pt=round(size * PT, 2), font="W6" if w == "bold" else "W3",
                            color=matplotlib.colors.to_hex(c), align=ha, group=self.cur, group_name=self.GR[self.cur]["name"]))

    def note(self, x, y, lines, c, lh=3.3, size=2.6, ha="left"):
        """見出し（太）＋本文の注。lines[0] が見出し"""
        for k, s in enumerate(lines):
            self.txt(x, y + k * lh, s, size + (0.2 if k == 0 else 0), c if k == 0 else INK, "bold" if k == 0 else "normal", ha=ha, key=k)

    def save(self, base, view, out_pdf, out_json, out_parts, meta):
        self.fig.savefig(out_pdf, transparent=True)
        plt.close(self.fig)
        json.dump(dict({"_": f"{os.path.basename(out_pdf)} の位置：ページの左上＝基の紙の (x, y) mm、1 mm＝1 mm。present/tools/saikou.py が書く。",
                        "base": base, "view": view["name"], "page_paper_mm": list(self.PAGE)}, **meta),
                  open(out_json, "w"), ensure_ascii=False, indent=1)
        lines = []
        for g in self.GR.values():
            if not g["paths"]:
                continue
            A = np.array([p for q in g["paths"] for p in q["pts"]])
            lines.append(dict(g, id=g["id"] + ".l", x=round(float(A[:, 0].min()), 2), y=round(float(A[:, 1].min()), 2),
                              w=round(float(np.ptp(A[:, 0])), 2), h=round(float(np.ptp(A[:, 1])), 2)))
        json.dump({"_": "断面に重ねる図の部品（Illustrator の一つずつの部品）。present/ai/layout.json の parts と同じ形（kind＝text・lines）。"
                        "座標は基の紙（base）の左上からの mm、下向き +。text の (x, y) は揃えの点の基準線、size_pt・lw は pt、dash は pt。"
                        "group は図の中のサブグループ（矢印・線と、その注）。present/tools/saikou.py が書く。手で書き換えない。",
                   "base": base, "view": view["name"], "unit": "mm", "origin": "紙の左上", "page_paper_mm": list(self.PAGE),
                   "parts": lines + self.TX}, open(out_parts, "w"), ensure_ascii=False, indent=1)
        print(os.path.basename(out_parts), "：線のまとまり", len(lines), "・注", len(self.TX))


def legend(Z, x, y, items, title, lh=3.4):
    """凡例：items = [(種類, 色, 文)]。種類：line・dash・scatter・area"""
    Z.grp("legend", "凡例")
    Z.txt(x, y, title, 2.8, INK, "bold", key="h")
    for k, (kind, c, s) in enumerate(items):
        yy = y + lh * (k + 1)
        ym = yy - 0.9
        if kind in ("line", "dash"):
            Z.line([(x, ym), (x + 5.5, ym)], c, 0.8, dash=(3, 1.6) if kind == "dash" else None, cap="butt")
            Z.head((x, ym), (x + 6.5, ym), c, 1.3)
        elif kind == "scatter":
            for t in (-50, -20, 10, 40):
                u = np.array([np.cos(np.radians(t)), -np.sin(np.radians(t))])
                Z.line([(x + 1.0 + u[0] * 0.5, ym + u[1] * 0.5), (x + 1.0 + u[0] * 2.4, ym + u[1] * 2.4)], c, 0.3, cap="butt")
            Z.poly([(x + 3.5, ym - 1.0), (x + 6.5, ym - 1.0), (x + 6.5, ym + 1.0), (x + 3.5, ym + 1.0)], DIF_F, a=0.45)
        elif kind == "area":
            Z.poly([(x, ym - 1.0), (x + 6.5, ym - 1.0), (x + 6.5, ym + 1.0), (x, ym + 1.0)], c, a=0.45)
        Z.txt(x + 8.0, yy, s, 2.5, INK, key=k)


# ================================================================ 断面D：光の環境
def draw_hikari(paper, vname, out_pdf, out_json, out_parts, out_png):
    view = KG.load_view(paper, vname)
    c0 = view["clip_paper_mm"]
    CL = (c0[0], c0[1] + 8, c0[2], c0[3])        # mock.py と同じ（上の 8 mm は図の題）
    PAGE = (CL[0], CL[1] - UP, CL[2], CL[3])
    G = KG.measure(view)
    right = view["right"]
    Z = Zu(view, PAGE, "hikari")
    X, Y, P = Z.X, Z.Y, Z.P
    rW, rM, cW, cM = G["roofW"], G["roofM"], G["ceilW"], G["ceilM"]
    print("形：", {k: G[k] for k in ("hWo", "hWe", "band", "slit", "hiwin", "lid", "lattice", "door", "eave", "fan")}, "代えた物", G["_fallback"])

    # 角：ルーバーを通る朝の日（断面に映して板の角30°）・南中・東の軒
    t30 = time_at(DEC["冬至"], 30.0, right)
    _, _, a_noon = profile(DEC["夏至"], 12.0, right)
    alt_noon_s, alt_noon_w = sun(DEC["夏至"], 12.0)[0], sun(DEC["冬至"], 12.0)[0]
    hd, zd0, zd1 = G["door"][0], G["door"][2], G["door"][3]
    ht, zt0 = G["eave"][0], G["eave"][1]
    cut = float(np.degrees(np.arctan2(zt0 - zd0, ht - hd)))       # 軒先の下と戸の足を結ぶ角
    t_hi = 10.0 if profile(DEC["夏至"], 10.0, right)[2] > cut + 1 else time_at(DEC["夏至"], cut + 2, right)
    a_hi = profile(DEC["夏至"], t_hi, right)[2]
    a_w9 = profile(DEC["冬至"], 9.0, right)[2]
    a_s7 = profile(DEC["夏至"], 7.0, right)[2]
    a_e8 = profile(DEC["春秋分"], 8.0, right)[2]
    print(f"ルーバーを30°で通る：冬至{hm(t30)}／夏至の南中 高さ{alt_noon_s:.1f}°・断面{a_noon:.1f}°／軒の角{cut:.1f}°・夏至{hm(t_hi)} {a_hi:.1f}°"
          f"／冬至9時 {a_w9:.1f}°・夏至7時 {a_s7:.1f}°・春秋分8時 {a_e8:.1f}°")

    # ---------------- 西館：棟のガラスの帯の外のルーバー
    b0, b1, bz0, bz1 = G["band"]
    bandz = lambda h: bz0 + (bz1 - bz0) * (h - b0) / (b1 - b0)
    # 板（見本だけに描く目安ではなく、どの光が通るかの説明に要る：帯の上の板を細く）
    Z.grp("w.louver.direct", f"西館の帯：冬至{hm(t30)}の日がルーバーを通る")
    hits = []
    for hh in (b0 + 350, b0 + 900, b0 + 1450):
        p = (hh, bandz(hh) + 60)
        # 下りる先：西の外壁の内面か床
        u = np.array([-np.cos(np.radians(30)), -np.sin(np.radians(30))])
        hw = G["hWo"] + 250
        s = (p[0] - hw) / -u[0]
        q = np.array(p) + u * s
        if q[1] < 30:
            s = (p[1] - 30) / -u[1]; q = np.array(p) + u * s
        Z.ray(p, 30.0, 2300, s, SUN["冬至"], 0.65)
        hits.append(q)
    q = hits[1]
    Z.scatter(q[0], q[1], -60, 60, n=5, r0=0.5, r1=2.0, c=SUN["冬至"], lw=0.3)       # 当たった所（西の壁）で返る
    Z.note(X(b1) + 4, Y(bz1) - 30.0, [f"棟のガラスの帯：冬至の朝{hm(t30)}（断面に映して30°）",
                                       "ルーバーの板（東が高い30°）に沿う向きの日だけが通り、",
                                       "遊戯室の奥の壁まで差す"], SUN["冬至"])
    Z.grp("w.louver.diffuse", "西館の帯：高い日はルーバーで乱反射")
    for hh in np.linspace(b0 + 250, b1 - 250, 4):
        Z.ray((hh, bandz(hh) + 150), a_noon, 1600, 0, SUN["夏至"], 0.55, head=True, size=1.2)
    for hh in np.linspace(b0 + 150, b1 - 150, 6):
        Z.scatter(hh, bandz(hh) - 120, -155, -25, n=5, r0=0.5, r1=2.2, c=DIF, lw=0.28)
    Z.poly([P(b0, bandz(b0) - 150), P(b1, bandz(b1) - 150), P(b1 - 400, 5200), P(b0 - 900, 4600)], DIF_F, a=0.28, z=1)
    Z.note(X(b1) + 4, Y(bz1) - 18.0, [f"夏至の南中（高さ{alt_noon_s:.0f}°、この断面ではほぼ真上）",
                                       "板に当たり、白い艶消しの面で乱反射した",
                                       "やわらかい光が遊戯室へ降りる"], SUN["夏至"])
    # ---------------- 西館：光の筋の散乱光（架構の線ごとの型板ガラス＋鏡面の溝）
    Z.grp("w.suji", "西館の光の筋：散乱光")
    for hh in np.arange(G["hWo"] + 1800, G["slit"][0] - 600, 2000):
        Z.scatter(hh, KG.zl(cW, hh) - 60, -150, -30, n=4, r0=0.4, r1=1.9, c=DIF, lw=0.28)
    hs = np.linspace(G["hWo"] + 1200, G["slit"][0] - 500, 20)
    Z.poly([P(h, KG.zl(cW, h) - 80) for h in hs] + [P(h, KG.zl(cW, h) - 1500) for h in hs[::-1]], DIF_F, a=0.22, z=1)
    hx = G["hWo"] + 5500
    Z.note(X(G["hWo"]) + 3, Y(KG.zl(rW, hx)) - 7.0, ["光の筋（架構の線ごと）：型板ガラスで散らした",
                                                     "空の光が鏡面の溝を下り、梁の下から降りる"], DIF)
    # ---------------- 西館：東の高窓（はめ殺し）の朝の日
    Z.grp("w.hiwin", "西館の東の高窓：春秋分の朝8時")
    w0, w1 = G["hiwin"][2], G["hiwin"][3]
    for zz in (w0 + 300, w1 - 300):
        p = (G["hiwin"][0], zz)
        u = np.array([-np.cos(np.radians(a_e8)), -np.sin(np.radians(a_e8))])
        s = (zz - 30) / -u[1]
        q = np.array(p) + u * s
        if q[0] < G["hWo"] + 250:
            s = (p[0] - G["hWo"] - 250) / -u[0]; q = np.array(p) + u * s
        Z.ray(p, a_e8, 2600, s, SUN["春秋分"], 0.6)
    Z.note(X(2200), Y(KG.zl(rM, 2200)) - 33.0, ["東の高窓（西館）：春秋分の朝8時（断面に映して%.0f°）" % a_e8,
                                               "本館の屋根を越えた日が遊戯室の床まで"], SUN["春秋分"])
    # ---------------- 本館：越屋根（西館の帯と同じルーバー）
    l0, l1, lz0, lz1 = G["lid"]
    Z.grp("m.kosi.direct", f"越屋根：冬至{hm(t30)}の日がルーバーを通る")
    hW_m = G["floor"][0] + 230                                     # 本館の西の外壁の内面（目安）
    spots = []
    for hh in (l1 - 250, l1 - 750):
        p = (hh, lz1 + 60)
        u = np.array([-np.cos(np.radians(30)), -np.sin(np.radians(30))])
        s = (p[0] - hW_m) / -u[0]
        q = np.array(p) + u * s
        Z.ray(p, 30.0, 1800, s, SUN["冬至"], 0.65)
        spots.append(q)
    for q in spots:
        Z.scatter(q[0], q[1], -70, 70, n=5, r0=0.5, r1=2.0, c=SUN["冬至"], lw=0.3)
    Z.grp("m.kosi.diffuse", "越屋根：高い日はルーバーで乱反射、西吹き抜けへ")
    for hh in np.linspace(l0 + 400, l1 - 300, 3):
        Z.ray((hh, lz1 + 150), a_noon, 1600, 0, SUN["夏至"], 0.55, size=1.2)
    for hh in np.linspace(l0 + 250, l1 - 250, 5):
        Z.scatter(hh, lz0 - 130, -155, -25, n=5, r0=0.5, r1=2.0, c=DIF, lw=0.28)
    Z.poly([P(hW_m, lz0 - 150), P(G["lattice"][0], lz0 - 150), P(G["lattice"][0], 900), P(hW_m, 900)], DIF_F, a=0.25, z=1)
    # ---------------- 本館：教室の高窓（西の壁の上の縦格子）
    Z.grp("m.takamado", "教室の高窓：西の壁の上の縦格子から教室へ")
    la = G["lattice"]
    for zz in np.linspace(la[2] + 250, la[3] - 200, 3):
        Z.harrow([(la[0] - 600, zz + 120), (la[0] + 1500, zz - 180)], DIF, lw=0.45, size=1.1)
    # ---------------- 本館：光の筋（鏡面の光ダクト）
    S = geometry_suji(view)
    sof, (g0, gz0), (g1, gz1) = S["soffit"], S["glass"][0], S["glass"][1]
    zg = lambda h: gz0 + (gz1 - gz0) * (h - g0) / (g1 - g0)
    Z.grp("m.suji", "光の筋：型板ガラスで散らした空の光が鏡面の溝を下りる")
    hs = [h for h, _ in sof]
    Z.poly([P(h, zg(h) - 60) for h in hs] + [P(h, z) for h, z in sof[::-1]], DIF_F, a=0.45, z=2)
    for hh in np.arange(max(g0, 2600), min(g1, 13000), 1500):
        Z.scatter(hh, zg(hh) + 60, 60, 120, n=3, r0=1.0, r1=2.2, c=DIF, lw=0.3)            # 空の光（いろいろな向きから）
        z0 = float(np.interp(hh, [h for h, _ in sof], [z for _, z in sof]))
        Z.scatter(hh, z0 - 40, -160, -20, n=6, r0=0.4, r1=2.6, c=DIF, lw=0.3)              # 梁の下で広がる
    hs2 = np.linspace(2200, 12800, 30)
    zs = np.interp(hs2, [h for h, _ in sof], [z for _, z in sof])
    Z.poly([P(h, z - 60) for h, z in zip(hs2, zs)] + [P(h, z - 1300) for h, z in zip(hs2[::-1], zs[::-1])], DIF_F, a=0.2, z=1)
    # ---------------- 本館：東の深い軒・ガラス戸・落葉樹
    Z.grp("m.noki", f"深い軒：夏至の朝{hm(t_hi)}の日を遮る")
    hb = ht - 350
    zb = KG.zl(rM, hb) + 15
    A, B = Z.ray((hb, zb), a_hi, 3800, 0, SUN["夏至"], 0.7, size=1.5)
    x_, y_ = P(hb, zb)
    Z.line([(x_ - 0.9, y_ - 0.9), (x_ + 0.9, y_ + 0.9)], SUN["夏至"], 0.5); Z.line([(x_ - 0.9, y_ + 0.9), (x_ + 0.9, y_ - 0.9)], SUN["夏至"], 0.5)
    # 落葉樹（断面Dの位置には無いが描く）：幹と枝、夏の葉は淡い面
    hT = ht + 2300
    crown = (hT, 4300.0, 1050.0, 1450.0)
    Z.grp("m.tree", "落葉樹（夏は葉、冬は枝だけ）")
    tt = np.linspace(0, 2 * np.pi, 48)
    Z.poly([P(crown[0] + crown[2] * np.cos(t), crown[1] + crown[3] * np.sin(t)) for t in tt], LEAF, a=0.22, ec=LEAF, lw=0.3, z=1)
    Z.line([P(hT, G["engawa_out"][2]), P(hT, 3300)], "#7A6A55", 0.6)
    for dh, dz in ((-650, 4500), (600, 4700), (-250, 5300), (350, 3900)):
        Z.line([P(hT, 3200), P(hT + dh, dz)], "#7A6A55", 0.35)
    # 冬至9時：葉の落ちた枝のあいだを通り、軒の下からガラス戸へ、床の奥まで
    tn = np.tan(np.radians(a_w9))
    z_top = min(zd1, zt0 - (ht - hd) * tn)
    reach = z_top / tn
    Z.grp("m.touji", "冬至の朝9時：葉の落ちた木を通り、軒の下から部屋の奥へ")
    hstart = crown[0] + crown[2] + 300
    Z.arrow([P(hstart, z_top + (hstart - hd) * tn), P(hd - reach, 0)], SUN["冬至"], 0.75, size=1.6, sm=False)
    Z.poly([P(hd - reach, 0), P(hd, z_top), P(hd, 0)], SUN["冬至"], a=0.14, z=1)
    Z.line([P(hd - reach, 0), P(hd, 0)], SUN["冬至"], 1.4, cap="butt")
    # 夏至7時：同じくらいの低い角、葉が遮る
    Z.grp("m.geshi7", "夏至の朝7時：低い日は落葉樹の葉が遮る")
    tn7 = np.tan(np.radians(a_s7))
    z7 = z_top - 250
    hx7 = crown[0] + crown[2] * 0.75
    Z.arrow([P(hstart, z7 + (hstart - hd) * tn7), P(hx7, z7 + (hx7 - hd) * tn7)], SUN["夏至"], 0.75, size=1.5, sm=False)
    Z.line([P(hx7, z7 + (hx7 - hd) * tn7), P(hd, z7)], SUN["夏至"], 0.4, a=0.6, dash=(1.5, 1.5))
    # 注（東）
    ex, ey = X(ht) - 33.0, Y(6400) - 5.0
    Z.grp("m.noki", f"深い軒：夏至の朝{hm(t_hi)}の日を遮る")
    Z.note(ex, ey - 13.2, [f"深い軒：夏至の朝{hm(t_hi)}（断面に映して{a_hi:.0f}°）", f"軒先と戸の足を結ぶ{cut:.0f}°より高い日は戸に当たらない"], SUN["夏至"])
    Z.grp("m.geshi7", "夏至の朝7時：低い日は落葉樹の葉が遮る")
    Z.note(ex, ey - 5.2, [f"夏至の朝7時（{a_s7:.0f}°）：落葉樹の葉が遮る"], SUN["夏至"])
    Z.grp("m.touji", "冬至の朝9時：葉の落ちた木を通り、軒の下から部屋の奥へ")
    Z.note(ex, ey + 0.4, [f"冬至の朝9時（{a_w9:.0f}°）：葉の落ちた枝を通り、", f"軒の下から床の奥{reach / 1000:.1f} mまで"], SUN["冬至"])
    Z.grp("m.tree", "落葉樹（夏は葉、冬は枝だけ）")
    Z.txt(X(hT), Y(crown[1] + crown[3]) - 4.6, "落葉樹", 2.4, "#5E7A35", ha="center", key=0)
    Z.txt(X(hT), Y(crown[1] + crown[3]) - 1.6, "（この断面の位置には無い）", 2.2, INK, ha="center", key=1)

    # 注（本館の上の空）：越屋根・光の筋・教室の高窓
    mx, my = X(2200), Y(KG.zl(rM, 2200)) - 26.0
    Z.grp("m.kosi.direct", f"越屋根：冬至{hm(t30)}の日がルーバーを通る")
    Z.note(mx, my, ["越屋根：西館の帯と同じルーバー", f"冬至の朝{hm(t30)}（30°）の日は板のあいだを通り、白い西の壁で返る"], SUN["冬至"])
    Z.grp("m.kosi.diffuse", "越屋根：高い日はルーバーで乱反射、西吹き抜けへ")
    Z.note(mx, my + 7.4, ["高い日（夏の南中など）は板で乱反射し、西吹き抜けへ"], SUN["夏至"])
    Z.grp("m.takamado", "教室の高窓：西の壁の上の縦格子から教室へ")
    Z.note(mx, my + 12.6, ["教室の高窓（西の壁の上の縦格子、h2.4より上）：", "吹き抜けの光が教室の西の奥へ"], DIF)
    Z.grp("m.suji", "光の筋：型板ガラスで散らした空の光が鏡面の溝を下りる")
    Z.note(mx, my + 19.4, ["光の筋（鏡面の光ダクト）：型板ガラスで散らした空の光が", "鏡面の溝を下り、梁の下で広がる（約8割が下に出る）"], DIF)

    # 凡例（一つ）
    legend(Z, X(-14000), PAGE[1] + 4.0, [
        ("line", SUN["夏至"], "直射の日：夏至（線の先の×は遮られる所）"),
        ("line", SUN["春秋分"], "直射の日：春分・秋分"),
        ("line", SUN["冬至"], "直射の日：冬至"),
        ("scatter", DIF, "乱反射・散乱の光（細い短い線と淡い面）"),
        ("area", LEAF, "落葉樹の葉（夏）"),
    ], "光の環境　凡例（時刻は太陽時、角は断面に映した太陽の高さ）")
    meta = dict(louver_direct_time={"冬至": hm(t30)}, noon_profile_deg=round(a_noon, 1), eave_cut_deg=round(cut, 1),
                summer_eave_time=hm(t_hi), angles_deg={"冬至9時": round(a_w9, 1), "夏至7時": round(a_s7, 1), "春秋分8時": round(a_e8, 1)},
                fallback=G["_fallback"])
    base = f"drawings/{paper}.pdf"
    Z.save(base, view, out_pdf, out_json, out_parts, meta)
    preview(os.path.join(ROOT, "drawings_rhino", paper + ".pdf"), os.path.join(ROOT, "drawings", paper + "_文字.pdf"), out_pdf, PAGE, out_png)


def geometry_suji(view):
    """光の筋（本館）：切り口から奥のいちばん近い架構の線の型板ガラスと、鏡面の下の縁（梁の下端）"""
    C = KG.Cut(view)
    depth = view.get("depth_mm", 3200)
    slots = []
    for n, nm, P_, F in C.pick("10t"):
        h, d, z = C.hdz(P_)
        if np.ptp(h) > 5000 and -300 < d.mean() < depth:
            slots.append((d.mean(), h, z))
    d_s, h, z = min(slots, key=lambda s: s[0])
    G = dict(slot_d=d_s, glass=((h.min(), z[h < h.min() + 50].max()), (h.max(), z[h > h.max() - 50].max())))
    mir = []
    for n, nm, P_, F in C.pick("10m"):
        hh, dd, zz = C.hdz(P_)
        if abs(dd.mean() - d_s) < 250:
            mir.append((dd.mean(), hh, zz))
    side = min(np.unique(np.round([m[0] for m in mir], -1)), key=lambda x: abs(x - d_s))
    soffit = []
    for dm, hh, zz in mir:
        if abs(dm - side) < 60:
            hz = np.unique(np.round(np.c_[hh, zz], 0), axis=0)
            for hb in np.unique(np.round(hz[:, 0] / 10) * 10):
                soffit.append((hb, hz[np.abs(hz[:, 0] - hb) < 10, 1].min()))
    soffit.sort()
    G["soffit"] = soffit
    return G


# ================================================================ 断面C：空気の環境
def draw_kuuki(paper, vname, out_pdf, out_json, out_parts, out_png):
    view = KG.load_view(paper, vname)
    CL = CLIP[vname]
    PAGE = (CL[0], CL[1] - UP, CL[2], CL[3])
    G = KG.measure(view)
    Z = Zu(view, PAGE, "kuuki")
    X, Y, P = Z.X, Z.Y, Z.P
    rW, rM, cW, cM = G["roofW"], G["roofM"], G["ceilW"], G["ceilM"]
    print("形：", {k: G[k] for k in ("hWo", "hWe", "slit", "hiwin", "gaplid", "lid", "lattice", "door", "garari", "fan")}, "代えた物", G["_fallback"])
    hWe = G["hWe"]
    l0, l1, lz0, lz1 = G["lid"]
    la = G["lattice"]
    sl = G["slit"]
    sh = (sl[0] + sl[1]) / 2
    hg = G["garari"][0]
    hd = G["door"][0]
    zc = lambda h: KG.zl(cM, h)                         # 本館の天井（合板の下）
    zcW = lambda h: KG.zl(cW, h)
    z_uf = -260                                         # 床下の風の高さ（目安）
    z_vent = lz0 - 200                                  # 越屋根のすき間（蓋の下の150）の高さ

    # ---------------- 夏の夜の道
    Z.grp("night.in", "夏の夜：段の蹴込みのガラリから床下へ、西の壁ぎわから部屋へ")
    Z.harrow([(hg + 2600, 700), (hg + 900, 150), (hg + 60, -75)], NIGHT, lw=0.7)
    Z.harrow([(hg - 150, z_uf), (8000, z_uf), (2300, z_uf)], NIGHT, lw=0.7, dash=(3, 1.5))
    Z.harrow([(2150, z_uf), (2100, 150), (2500, 500), (6500, 380)], NIGHT, lw=0.6)
    Z.grp("night.harima", "夏の夜：温まって梁間を西へ上り、西の壁の上の縦格子から西吹き抜けへ")
    Z.harrow([(6800, 420), (9300, 800), (10800, zc(10800) - 380), (8800, zc(8800) - 260), (5000, zc(5000) - 230), (2300, zc(2300) - 260),
              (la[0] - 250, (la[2] + la[3]) / 2 + 350)], NIGHT, lw=0.7)
    Z.grp("night.sukima", "夏の夜：越屋根のすき間からすき間へ、覗き窓（夜だけ開く）から遊戯室へ")
    Z.harrow([(1000, 2600), (900, 3500), (700, z_vent), (-150, z_vent), (-600, 3900), (hWe + 80, 3500), (hWe - 700, 3400)], NIGHT, lw=0.7)
    Z.grp("night.yugi", "夏の夜：遊戯室の吹き抜けを上り、棟のガラスの帯の排気のスリットから外へ")
    Z.harrow([(hWe - 700, 3400), (-2300, 4200), (sh + 150, 6200), (sh, sl[2] - 150), (sh - 40, sl[3] + 900)], NIGHT, lw=0.85, size=1.8)
    # ---------------- 中間期の昼の道
    Z.grp("mid.honkan", "中間期の昼：縁側のガラス戸から部屋へ、越屋根のすき間から外へ")
    Z.harrow([(hd + 2200, 1500), (hd - 300, 1500), (6000, 1750), (3000, 2350), (la[0] + 200, 2850), (la[0] - 300, 3150), (700, 3700),
              (l1 - 150, z_vent), (l1 + 500, z_vent + 300), (l1 + 1300, lz1 + 900)], MIDA, lw=0.7)
    Z.grp("mid.yugi", "中間期の昼：遊戯室は外壁の足もとの地窓から排気のスリットへ")
    hw = G["hWo"]
    Z.harrow([(hw - 1500, 700), (hw + 400, 750), (hw + 3500, 1300), (-7500, 3500), (sh - 500, 6300), (sh - 70, sl[2] - 150), (sh - 120, sl[3] + 900)], MIDA, lw=0.7)
    # ---------------- 天井扇（西吹き抜け φ1100 h2.8）
    hf, zf = G["fan"]
    Z.grp("fan", "西吹き抜けの天井扇φ1100（h2.8）：下向きの風で混ぜる")
    Z.line([P(hf - 550, zf), P(hf + 550, zf)], FAN, 0.9, cap="butt")
    Z.line([P(hf, zf), P(hf, zf + 380)], FAN, 0.4)
    for dh in (-320, 0, 320):
        Z.harrow([(hf + dh, zf - 150), (hf + dh * 1.15, zf - 1500)], FAN, lw=0.5, size=1.1, sm=False)
    for sgn in (-1, 1):
        Z.harrow([(hf + sgn * 380, 1000), (hf + sgn * 700, 350), (hf + sgn * 980, 600), (hf + sgn * 900, 1900), (hf + sgn * 620, zf - 220)], FAN, lw=0.4, size=1.0, dash=(2, 1.2))
    # ---------------- 物干しの竹竿（h3.1、昇降。この断面には無い：0・1歳と2歳の西吹き抜け）
    Z.grp("pole", "物干しの竹竿φ35（h3.1、昇降）と布")
    for hp in (400.0, 1200.0):
        xc, yc = P(hp, 3100)
        tt = np.linspace(0, 2 * np.pi, 20)
        Z.poly([(xc + 0.45 * np.cos(t), yc + 0.45 * np.sin(t)) for t in tt], POLE, a=1.0, z=7)
        for dx in (-0.25, 0.25):
            Z.line([(xc + dx, yc + 0.4), (xc + dx * 1.4, Y(2000))], "#A9A9A9", 0.35, z=6)      # 掛けた布（白い布の両側）
        Z.line([(xc, yc - 0.45), (xc, Y(zc(1700) if 1700 > cM["h0"] else 3700))], "#B9B9B9", 0.2, dash=(1.0, 1.0))  # 昇降の綱
    Z.grp("pole.air", "物干し：上にたまる暖かい空気と天井扇の風で布が乾く")
    for hp in (400.0, 1200.0):
        Z.harrow([(hp, 2200), (hp + 60, 2900), (hp - 40, 3700)], FAN, lw=0.35, size=0.9, dash=(1.6, 1.0))

    # ---------------- 注
    # 本館の上の空：夏の夜（右）・中間期（右の下）・天井扇・物干し
    mx = X(3800)
    my = PAGE[1] + 6.0
    Z.grp("night.in", "夏の夜：段の蹴込みのガラリから床下へ、西の壁ぎわから部屋へ")
    Z.note(mx, my, ["夏の夜（涼しい外気、ダンパーは自動）", "①段の蹴込みのガラリから床下へ（底板を冷やす）",
                    "②西の壁ぎわの床のスリットから部屋へ"], NIGHT)
    Z.grp("night.harima", "夏の夜：温まって梁間を西へ上り、西の壁の上の縦格子から西吹き抜けへ")
    Z.note(mx, my + 10.0, ["③温まって梁間を西へ上り、西の壁の上の縦格子から西吹き抜けへ"], NIGHT)
    Z.grp("night.sukima", "夏の夜：越屋根のすき間からすき間へ、覗き窓（夜だけ開く）から遊戯室へ")
    Z.note(mx, my + 13.6, ["④越屋根のすき間→すき間→覗き窓（夜だけ開く）から遊戯室へ"], NIGHT)
    Z.grp("mid.honkan", "中間期の昼：縁側のガラス戸から部屋へ、越屋根のすき間から外へ")
    Z.note(mx, my + 19.6, ["中間期の昼", "縁側のガラス戸から部屋へ、越屋根のすき間から外へ"], MIDA)
    Z.grp("fan", "西吹き抜けの天井扇φ1100（h2.8）：下向きの風で混ぜる")
    Z.note(mx, my + 28.4, ["天井扇φ1100（西吹き抜け、h2.8）", "下向きに回して混ぜる：夏の昼は体に風、冬は上にたまる暖かい空気を床へ"], FAN)
    Z.grp("pole", "物干しの竹竿φ35（h3.1、昇降）と布")
    Z.note(mx, my + 37.2, ["物干しの竹竿φ35（h3.1、両端の綱で昇降）", "上にたまる暖かい空気と天井扇の風で布が乾く",
                           "（この断面の位置には無い：0・1歳と2歳の西吹き抜け）"], POLE)
    # 西館の上の空：夏の夜の出口・中間期
    wx = X(G["hWo"]) + 4.0
    wy = PAGE[1] + 26.0
    Z.grp("night.yugi", "夏の夜：遊戯室の吹き抜けを上り、棟のガラスの帯の排気のスリットから外へ")
    Z.note(X(sh) - 2.0, Y(sl[3] + 900) - 4.5, ["⑤遊戯室の吹き抜けを上り、棟のガラスの帯の", "排気のスリットから外へ（高低差約8 m）"], NIGHT, ha="right")
    Z.grp("mid.yugi", "中間期の昼：遊戯室は外壁の足もとの地窓から排気のスリットへ")
    Z.note(wx, wy + 8.5, ["中間期の昼：遊戯室は外壁の足もとの地窓から", "排気のスリットへ（煙突の効果）"], MIDA)
    # 凡例
    legend(Z, X(G["hWo"]) + 4.0, PAGE[1] + 4.0, [
        ("line", NIGHT, "夏の夜の道（覗き窓・排気のスリット・床下の入口を開ける）"),
        ("line", MIDA, "中間期の昼の道（越屋根のすき間・地窓を開ける）"),
        ("dash", FAN, "天井扇の風（下向きに混ぜる）"),
    ], "空気の環境　凡例（開け閉めは自動：外気が涼しいとき・タイマー・雨）")
    for t in Z.TX:
        if t["group"].endswith(".legend") and t["id"].endswith(".th"):
            pass
    base = f"drawings/{paper}.pdf"
    Z.save(base, view, out_pdf, out_json, out_parts, dict(fallback=G["_fallback"]))
    preview(os.path.join(ROOT, "drawings_rhino", paper + ".pdf"), os.path.join(ROOT, "drawings", paper + "_文字.pdf"), out_pdf, PAGE, out_png)


# ---------------------------------------------------------------- 見本
# 断面Cの文字の層にある更新係の風の注と線（青 #2f6fb0、前の越屋根の道）は、この図に置き換えるので見本と .ai から外す（mock.py・ai_layout.py）
AIR_RGB = [(0.1843137255, 0.4352941176, 0.6901960784)]
AIR_HEX = "#2f6fb0"


def strip_blue(src, out=None):
    """文字の層の写しから、風の青い文字と線を消す（drawings/ は書き換えない）。out を渡せばそこへ保存して out を返す"""
    import fitz, re
    d = fitz.open(src); p = d[0]
    rs = []
    for b in p.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            if any(("#%06x" % s_["color"]) == AIR_HEX for s_ in l["spans"]):
                rs.append(fitz.Rect(l["bbox"]))
    for r_ in rs:                                       # 文字
        p.add_redact_annot(r_, fill=False)
    p.apply_redactions(images=0, graphics=0)
    for r_ in rs:                                       # 字の白い地（すっぽり入る線と塗りだけ。文字は消さない）
        p.add_redact_annot(r_ + (-4, -4, 4, 4), fill=False)
    p.apply_redactions(images=0, graphics=1, text=1)
    p.clean_contents()
    xref = p.get_contents()[0]
    st = d.xref_stream(xref)

    def rep(m):
        vals = tuple(float(v) for v in m.group(1).split())
        isb = any(all(abs(a - b) < 2e-3 for a, b in zip(vals, c)) for c in AIR_RGB)
        op = m.group(2)
        g = (b"/AirS0" if op == b"RG" else b"/AirF0") if isb else (b"/AirS1" if op == b"RG" else b"/AirF1")
        return m.group(0) + b" " + g + b" gs"
    st = re.sub(rb"((?:[\d.]+ ){2}[\d.]+) (RG|rg)", rep, st)
    d.update_stream(xref, st)
    for nm_, k_, v_ in (("AirS0", "CA", 0), ("AirS1", "CA", 1), ("AirF0", "ca", 0), ("AirF1", "ca", 1)):
        x_ = d.get_new_xref(); d.update_object(x_, f"<< /Type /ExtGState /{k_} {v_} >>")
        d.xref_set_key(p.xref, f"Resources/ExtGState/{nm_}", f"{x_} 0 R")
    if out:
        d.save(out, garbage=3, deflate=True)
        return out
    return d


def preview(lines_pdf, moji_pdf, ovl, PAGE, out_png, px=1600):
    import fitz
    mm = 72 / 25.4
    W, H = (PAGE[2] - PAGE[0]) * mm, (PAGE[3] - PAGE[1]) * mm
    d = fitz.open(); pg = d.new_page(width=W, height=H)
    pg.draw_rect(pg.rect, color=None, fill=(1, 1, 1))
    clip = fitz.Rect(PAGE[0] * mm, PAGE[1] * mm, PAGE[2] * mm, PAGE[3] * mm)
    if os.path.exists(lines_pdf):
        pg.show_pdf_page(pg.rect, fitz.open(lines_pdf), 0, clip=clip)
    if os.path.exists(moji_pdf):
        pg.show_pdf_page(pg.rect, strip_blue(moji_pdf), 0, clip=clip)
    pg.show_pdf_page(pg.rect, fitz.open(ovl), 0)
    z = px / max(W, H)
    pg.get_pixmap(matrix=fitz.Matrix(z, z)).save(out_png)
    print("見本：", out_png)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which", default="CD", help="C（空気）・D（光）・CD")
    a = ap.parse_args()
    S = os.path.join(ROOT, "present", "sozai")
    O = "/tmp/claude-0"
    os.makedirs(O, exist_ok=True)
    if "D" in a.which:
        n = "17_光の環境_断面"
        draw_hikari("sodachiya_sections2_1-100", "断面D", *(os.path.join(S, n + e) for e in (".pdf", ".json", "_parts.json")), os.path.join(O, "saikou_D.png"))
    if "C" in a.which:
        n = "30_空気の環境_断面"
        draw_kuuki("sodachiya_sections_1-100", "断面C", *(os.path.join(S, n + e) for e in (".pdf", ".json", "_parts.json")), os.path.join(O, "saikou_C.png"))
