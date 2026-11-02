#!/usr/bin/env python3
"""こどもたちの環境　0〜2歳（2枚目の素材31、プレゼンの準備 11-02）。

0・1歳と2歳の部屋、受け取り土間・ふきぬけのみち・縁側、みなみのさんかく、しずかのもりを一枚の平面に。
描き方は scripts/plan01.py・plan02.py（淡い色の床、白い家具の箱、番号の丸、凡例の行）に倣い、形は3dm
（model/sodachiya_exact_mesh.3dm）からレイヤーごとに上から見た外形を取って描く（配置が3dmと必ず合う）。
向きは配置図と同じ（高野川を下の辺、3dm の xy を時計回りに 38.5°、data/garden.json の VIEW_ROT）。縮尺 1/200。

  python3 present/tools/nyuji_kankyo.py            → present/sozai/31_こどもたちの環境_0〜2歳.pdf
  python3 present/tools/nyuji_kankyo.py --png F    確かめ用の PNG も（/tmp/claude-0/ に）
"""
import argparse, json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PRESENT = os.path.dirname(HERE)
A = os.path.dirname(PRESENT)                                   # sodachiya/
sys.path.insert(0, os.path.join(A, "tools"))
sys.path.insert(0, os.path.join(A, "scripts"))
import hakaru as H                                             # noqa: E402  3dm の読み方と u・v（tools/hakaru.py）
import garden_common as gc                                     # noqa: E402  園庭の (a, d)・(u, v) → xy
import matplotlib                                              # noqa: E402
matplotlib.use("Agg")
import fonts42                                                 # noqa: E402,F401  文字は Type42（Noto Sans CJK JP）
import matplotlib.pyplot as plt                                # noqa: E402
from matplotlib.patches import Polygon as MPoly, Circle        # noqa: E402
from matplotlib.path import Path                               # noqa: E402
from matplotlib.patches import PathPatch                       # noqa: E402
import shapely                                                 # noqa: E402
from shapely.geometry import Polygon, LineString, MultiPolygon, box as sbox   # noqa: E402
from shapely.ops import unary_union                            # noqa: E402

OUT = os.path.join(PRESENT, "sozai", "31_こどもたちの環境_0〜2歳.pdf")
SCALE = 200                                                    # 1/200
K = 1000 / SCALE                                               # 紙の mm／m
PAPER = (298.0, 170.0)                                         # 2枚目の 0・1歳と2歳のますを合わせたくらい（木田さんが .ai で縮める）
ROT = gc.G["VIEW_ROT"]["deg"]                                  # −38.5：配置図・園庭説明図と同じ向き
_cr, _sr = math.cos(math.radians(ROT)), math.sin(math.radians(ROT))

# ---- 色と線（plan01 に合わせる）
C = dict(r01="#E6EFC2", r2="#DCE9B4", doma="#E4E1DA", path="#F4EBDD", engi="#F4EBDD", engo="#EAE0CF", wet="#D5EBEE",
         span7="#EEEEEC", out="#EEF3E6", porch="#E8E4DC", shizu="#E2EBD5", sand="#F2E8CC", water="#D6ECF2", rain="#F1F0EA",
         hill="#DCE7B0", cork="#DCE7B0", wood="#F1E4CC", cloth="#F3EEDD", rattan="#EBDCC2", stump="#E3D2B5", bark="#6b4f2e",
         glass="#DCEBF3", lattice="#8a6a45", wall="#444444", low="#9a9a9a", tree="#5a7a3a", bowl="#E8E2D2", stream="#BFE0EA")
LW_F, LW_T = 0.35, 0.22                                        # 家具・細い線（pt）

# 番号のグループ（凡例の見出しと丸の色）
GROUPS = [("共通", "受け取り土間・ふきぬけのみち・水まわり・縁側（0〜2歳で共に使う所）", "#5b5b5b"),
          ("0歳", "", "#C9672A"), ("1歳", "", "#4E8A2E"), ("2歳", "", "#2F6DB5"),
          ("みなみのさんかく", "乳児の園庭（柵の内側）", "#8A4F9E"), ("しずかのもり", "乳児室の前の静かな森", "#1F7F7A")]
GCOL = {g: c for g, _, c in GROUPS}


def W(u, v):
    """本館の (u, v) → 3dm の xy（m）"""
    return gc.UV(u, v)


def rot(P):
    """3dm の xy（m、N×2）→回した座標（m）"""
    P = np.asarray(P, float)
    return np.c_[P[:, 0] * _cr - P[:, 1] * _sr, P[:, 0] * _sr + P[:, 1] * _cr]


def uv_poly(pts):
    return Polygon(rot([W(u, v) for u, v in pts])).buffer(0)


def uv_rect(u0, u1, v0, v1, n=8):
    pts = [(u0 + (u1 - u0) * i / n, v0) for i in range(n + 1)] + [(u1 - (u1 - u0) * i / n, v1) for i in range(n + 1)]
    return uv_poly(pts)


def RP(u, v):
    """(u, v)→回した座標（m）"""
    return tuple(rot([W(u, v)])[0])


# ---------------------------------------------------------------- 3dm を読む
def load(path):
    import rhino3dm as r
    m = r.File3dm.Read(path)
    want = ("11a", "13", "14", "15", "16", "17", "37", "38", "39", "40", "46", "48", "49", "51", "52", "53", "54", "56", "59",
            "60", "62", "64", "66", "70", "72", "75", "77", "78", "79", "90", "92", "94", "95", "96", "99", "10", "19d")
    layers = set()
    for i, L in enumerate(m.Layers):
        code = L.Name.split("_")[0]
        if any(code == w or (code.startswith(w) and code[len(w):].isalpha()) for w in want):
            layers.add(i)
    return H.gather(m, layers, (-14, 23, -5, 33), None)


def footprint(T, P):
    """物の三角形（mm）か線の点（mm）→回した座標の形（m）"""
    if T is not None:
        T = np.asarray(T, float)
        if len(T) == 0:
            return None
        xy = rot(T[:, :, :2].reshape(-1, 2) / 1000).reshape(-1, 3, 2)
        a = 0.5 * np.abs((xy[:, 1, 0] - xy[:, 0, 0]) * (xy[:, 2, 1] - xy[:, 0, 1]) - (xy[:, 2, 0] - xy[:, 0, 0]) * (xy[:, 1, 1] - xy[:, 0, 1]))
        xy = xy[a > 1e-8]
        if len(xy) == 0:
            return None
        polys = shapely.polygons(np.concatenate([xy, xy[:, :1]], axis=1))
        g = shapely.union_all(polys).buffer(0.004, join_style=2).buffer(-0.004, join_style=2)
        return g if not g.is_empty else None
    if P is not None and len(P) > 1:
        return LineString(rot(np.asarray(P)[:, :2] / 1000))
    return None


# ---------------------------------------------------------------- 描く
class Fig:
    def __init__(self):
        MM = 1 / 25.4
        self.fig = plt.figure(figsize=(PAPER[0] * MM, PAPER[1] * MM))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, PAPER[0]); self.ax.set_ylim(0, PAPER[1]); self.ax.set_aspect("equal"); self.ax.axis("off")
        self.o = np.array([0.0, 0.0])                         # 回した座標（m）の原点が紙のどこ（mm）か

    def pm(self, P):
        P = np.atleast_2d(np.asarray(P, float))
        return P * K + self.o

    def poly(self, g, fc="none", ec="none", lw=0.0, z=1, ls="-", alpha=1.0):
        if g is None or g.is_empty:
            return
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon":
                rings = [p.exterior] + list(p.interiors)
                verts, codes = [], []
                for r_ in rings:
                    c = self.pm(np.asarray(r_.coords)[:, :2])
                    verts += list(c); codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
                self.ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, alpha=alpha, joinstyle="miter"))
            elif p.geom_type in ("LineString", "LinearRing"):
                self.line(p, c=ec if ec != "none" else "black", lw=lw or LW_T, z=z, ls=ls)
            elif p.geom_type in ("MultiPolygon", "GeometryCollection", "MultiLineString"):
                self.poly(p, fc, ec, lw, z, ls, alpha)

    def line(self, g, c="black", lw=LW_T, z=3, ls="-"):
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon":
                p = p.exterior
            if p.geom_type not in ("LineString", "LinearRing"):
                continue
            q = self.pm(np.asarray(p.coords)[:, :2])
            self.ax.plot(q[:, 0], q[:, 1], color=c, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")

    def text(self, x, y, s, size=1.8, color="#222222", bold=False, ha="left", va="baseline", z=20, rotation=0):
        pt = size / 0.3528 / 0.72                               # size は文字の高さ（mm、mock.py と同じ）
        self.ax.text(x, y, s, fontsize=pt, color=color, ha=ha, va=va, zorder=z, rotation=rotation,
                     fontweight="bold" if bold else "normal")

    def num(self, xy, n, col, r=1.25):
        x, y = xy
        self.ax.add_patch(Circle((x, y), r, fc="white", ec=col, lw=0.7, zorder=30))
        self.text(x, y - 0.02, str(n), size=1.35, color=col, bold=True, ha="center", va="center", z=31)


SLAB = ("13", "14", "52", "53", "54", "56", "59", "62", "64", "96g", "95", "90g", "92s", "15")


def _noholes(g):
    if g is None or g.geom_type not in ("Polygon", "MultiPolygon"):
        return g
    return unary_union([Polygon(p.exterior) for p in getattr(g, "geoms", [g])])


def classify(objs):
    """レイヤーと物→(層, 色の決まり)。返すのは描く物の並び (z, g, style)"""
    items = []
    for ln, nm, T, P, Q in objs:
        code = ln.split("_")[0]
        lo, hi = Q.min(0), Q.max(0)
        g = None

        def add(z, **st):
            nonlocal g
            if g is None:
                g = footprint(T, P)
                if code in SLAB:
                    g = _noholes(g)
            if g is not None:
                items.append((z, g, st, ln, nm, lo, hi))

        # 頭上（h1.9 より上だけにある物）は描かない。屋根の縁・天蓋・木の樹冠だけ破線や輪郭で
        if code == "10":
            add(9, kind="eave"); continue
        if code == "51":
            add(9, ec="#555555", lw=LW_T, ls=(0, (4, 2)), fc="none"); continue
        if code in ("94c", "77c"):
            add(8.5, kind="crown", willow="柳" in nm); continue
        if code in ("94", "77"):
            add(8.6, kind="trunk"); continue
        if lo[2] > 1.9:
            continue
        if code == "62":   add(0.2, fc=C["out"])
        elif code == "64": add(0.3, fc=C["porch"])
        elif code == "99": add(0.6, fc="#D9D7CF")
        elif code == "92s": add(0.5, fc=C["rain"], ec="#BDBAB0", lw=LW_T, ls=(0, (1, 1)))
        elif code == "92": add(0.7, fc=C["stream"])
        elif code == "92f": continue
        elif code == "96g": continue                           # 床の噴水と
        elif code == "90g": continue                           # くぼ地の底は3dmの面の三角形が粗い（四角に見える）ので、下で garden.json の円で描く
        elif code == "96": add(0.9, fc="#CFCCC4", ec="#777777", lw=LW_T)
        elif code == "95": add(0.8, fc=C["sand"])
        elif code == "95r": add(0.85, fc="none", ec=C["lattice"], lw=0.4)
        elif code == "90l":
            if "ひみつのたに" in nm: add(0.55, fc="none", ec="#9a8f73", lw=LW_T, ls=(0, (2, 1.5)))
        elif code in ("95h", "95k", "40s", "40t"):
            add(6.6 if code in ("40s", "95h") else 6.7, fc=C["stump"] if code in ("40s", "95h") else "#EDE0C6", ec=C["bark"], lw=LW_T)
        elif code == "79c": add(0.8, fc="#CFE0B0", ec=C["tree"], lw=LW_T, ls=(0, (1, 1)))
        elif code == "78":
            if T is None:
                add(0.9, kind="curve78")
            elif abs(hi[2] + 0.15) < 0.03: add(0.85, fc=C["sand"], ec=C["lattice"], lw=LW_T)
            elif abs(hi[2] - 0.15) < 0.03: add(0.85, fc=C["water"], ec="#7fa9b8", lw=LW_T)
            elif hi[2] < -0.2 and hi[0] - lo[0] < 1.8 and hi[1] - lo[1] < 1.8: add(0.85, fc=C["sand"], ec=C["lattice"], lw=LW_T)   # 浅い砂場
            elif hi[2] > 1.0: add(5, fc=C["lattice"])
            else: add(0.8, fc="none", ec=C["tree"], lw=LW_T)
        elif code in ("60",): add(5, fc="#555555")
        elif code in ("70", "70k", "72"): add(5, fc=C["lattice"]) if code != "72" else add(5, fc="#333333")
        elif code == "70h": add(0.9, fc="#CFE0B0")
        elif code == "75":
            add(4, fc="white", ec="black", lw=LW_T) if T is not None else add(4, kind="curve75")
        elif code == "52": add(1, fc=C["doma"])
        elif code == "53": add(1, fc=C["r01"])
        elif code == "54": add(1, fc=C["r2"])
        elif code == "56": add(1, fc=C["path"])
        elif code == "59": add(1, fc=C["path"] if "西吹き抜け" in ln else C["span7"])
        elif code == "13": add(1, fc=C["engi"])
        elif code == "14": add(0.95, fc=C["engo"], ec="black", lw=LW_T)
        elif code == "15": add(1, fc=C["doma"])
        elif code == "37": add(3 + hi[2] * 0.1, fc="white", ec="black", lw=LW_T)
        elif code == "19d": add(3, fc="white", ec="black", lw=LW_T)
        elif code == "39": add(3 + hi[2] * 0.1, fc="#F4F9FA", ec="black", lw=LW_T)
        elif code == "40": add(2.5 if hi[2] < 0.1 else 3.2, fc=C["cloth"], ec="#8a7a55", lw=LW_T)
        elif code == "40k": add(2.6, fc=C["cork"], ec="#7a8a50", lw=LW_T)
        elif code == "40r": add(3.3, fc=C["rattan"], ec="#8a6a3a", lw=LW_T)
        elif code == "46": add(3 + hi[2] * 0.1, fc=C["wood"], ec="black", lw=LW_T)
        elif code == "38": add(5, fc=C["wall"] if hi[2] >= 1.8 else C["low"])
        elif code in ("17",): add(5.2, fc=C["wall"])
        elif code in ("16s", "16d", "48", "48f"): add(5.3, fc=C["glass"], ec="#3d6f8a", lw=0.15)
        elif code in ("16h", "17g", "66", "49"): add(5.4, fc=C["lattice"])
        elif code == "11a": add(5.6, fc="black")
    return items


# ---------------------------------------------------------------- 番号と凡例（u・v は 3dm で測った置き場。丸は物の上か脇）
# (グループ, u, v, 文)。文は短く：何か＋大きさ・素材・使い方の要点。名前は name.md の「決定」だけ
LEG = [
    ("共通", 3.0, 0.8, "受け取り土間（GL−300）：ベビーカーのまま入る。南の妻の格子の引き分け戸（開けて1.2）"),
    ("共通", 2.6, 1.95, "框＋腰壁h600：受け渡しのカウンター（0・1歳はここで手渡し）"),
    ("共通", 5.7, 0.55, "式台150＋木戸：2歳はここで靴を脱ぎ、先生と奥へ"),
    ("共通", 9.0, 0.45, "ふきぬけのみち：2歳が先生と歩く道（幅1.0、西の外壁の覗き窓）"),
    ("共通", 7.5, 1.3, "窓辺の小上がりh300＋格子h600（中は引き出し）"),
    ("共通", 8.15, 2.45, "先生の腰掛ける机（座h300）とおむつ替え台h850（部屋を向く）"),
    ("共通", 11.0, 2.2, "水まわり：沐浴槽・手洗い・おむつの棚h850"),
    ("共通", 10.4, 1.27, "洗濯（洗濯乾燥機・予洗い・たたむ棚）、上に物干しの竿h3.1"),
    ("共通", 10.8, 9.25, "調乳：おむつと分ける（シンク・冷蔵庫、柵h900＋戸）"),
    ("共通", 6.0, 12.75, "縁側：内縁側1.5（はだし）＋外縁側1.5（土足−150、洗い出し）"),
    ("共通", 2.7, 15.25, "高欄h900と高欄の戸・沓脱ぎ石（庭へは先生が開ける）"),
    ("共通", 12.45, 13.2, "縁側の低い柵の戸（0・1歳｜2歳、朝夕の合同保育）"),
    ("0歳", 4.0, 2.2, "受け入れの小机（検温・連絡帳）"),
    ("0歳", 2.3, 3.2, "個人棚h700（10人分）"),
    ("0歳", 3.85, 5.8, "ベビーベッド×6：囲いh900と布の天蓋（破線）"),
    ("0歳", 2.15, 9.1, "吊りかご×2：籐、底h450。先生が座って揺らす"),
    ("0歳", 1.25, 9.6, "はいはいの丘：h200のゆるい起伏、コルク"),
    ("0歳", 6.0, 8.6, "動かせる低い棚h600（0歳｜1歳の境、寄せれば閉じる）"),
    ("0歳", -0.45, 9.3, "南の妻：ガラスの引き戸の外に格子戸6枚（まとめて大きく開く）"),
    ("切り株0", 0, 0, ""),
    ("1歳", 9.1, 5.8, "食卓h350×2・椅子×10（午睡はコットを並べる）"),
    ("1歳", 11.75, 6.0, "個人棚（二段）"),
    ("1歳", 11.62, 7.72, "コットの収納（10台）"),
    ("1歳", 9.45, 10.0, "段々150×3と真ん中のすべり台（h450から床へ）"),
    ("1歳", 11.5, 3.15, "小さな便器と、2歳のトイレへの戸"),
    ("切り株1", 0, 0, ""),                                    # 0・1歳の切り株（下で3dmの物から置く）
    ("2歳", 15.3, 3.1, "じぶんの場所：個人棚・フックh900とゆっくりのベンチh250"),
    ("2歳", 13.3, 3.2, "トイレ：座る便器×3（低い仕切り）・手洗い×2 h500"),
    ("2歳", 14.4, 7.0, "食卓h400×2・椅子×10"),
    ("2歳", 12.2, 7.2, "絵本の棚h600・ござ"),
    ("2歳", 12.4, 9.3, "コットの収納（10台）"),
    ("2歳", 17.3, 2.4, "先生の記録台h900と高い腰掛け"),
    ("2歳", 17.3, 4.0, "ティピ：木の柱φ30×6と生成りの帆布、中は円い敷物"),
    ("2歳", 17.05, 5.95, "ままごとをする壁のない家（60°の切妻h1400）"),
    ("2歳", 17.0, 10.0, "小さな山：頂h900・崖h350、中にかくれ家（入口は西）"),
    ("2歳", 14.9, 10.0, "ひらけた床（積み木・ブロック）"),
    ("切り株2", 0, 0, ""),
    ("みなみのさんかく", -6.2, 0.55, "ポーチ：軒の下にベビーカー5台、塀ぎわに腰掛け"),
    ("みなみのさんかく", -3.3, 2.2, "柵h1.2：保育室の西の壁の線を延ばし、大人の側と分ける"),
    ("みなみのさんかく", -9.75, 2.75, "非常用の門（公園の側、h1.8、内からは鍵なし）"),
    ("みなみのさんかく", -2.0, 14.2, "東の木戸（しずかのもりと分ける、親子の両開きh1.2）"),
    ("みなみのさんかく", -1.3, 4.0, "南の縁側：外気浴（深い軒の下、土足−150）"),
    ("みなみのさんかく", -4.7, 6.6, "転がって遊ぶ低い丘h0.3と、まわりのはだしで歩く小径（幅0.6）"),
    ("みなみのさんかく", -5.1, 3.15, "浅い砂場1.6×1.4（縁はほぼ面一、布の覆い）"),
    ("みなみのさんかく", -6.6, 1.85, "柵の内側のハーブの帯・ヤマボウシ（南西の隅）"),
    ("みなみのさんかく", -1.0, 12.3, "水のテーブル（石の水盤h0.45）"),
    ("みなみのさんかく", -5.7, 9.6, "避難の帯（平らな芝）：刈り分けた芝の流れ・足あとの石・走る直線"),
    ("しずかのもり", 16.5, 20.5, "やなぎのくぐり：生きたヤナギのドームφ3、招かれた入口"),
    ("しずかのもり", 3.1, 18.2, "床の噴水φ4.0：ゴムチップの床に低い泡、輪から霧"),
    ("しずかのもり", 6.8, 19.3, "粒の遊び場（1〜2 mm、三日月約5 m²）：木の縁h0.10"),
    ("しずかのもり", 10.9, 19.2, "小さなくぼ地（底−0.4）：お話の輪"),
    ("切り株S", 0, 0, ""),
    ("しずかのもり", 2.0, 21.2, "雨庭：白い玉石の洲浜と景石（溢れたら護岸の溝へ）"),
    ("しずかのもり", 12.6, 15.75, "雨落ちの溝（玉石、本館の屋根の雨を受ける）"),
    ("土手", 0, 0, "縁：低い土手。地面が芝から苔と落ち葉に変わる所から静かに入る"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", default=None)
    ap.add_argument("--file", default=H.DEFAULT)
    a = ap.parse_args()
    objs = load(a.file)
    items = classify(objs)

    # 描く範囲：本館の架構1〜8（u 0〜21）・縁側、みなみのさんかく・ポーチ、しずかのもり
    mn = json.load(open(os.path.join(A, "data", "minami.json"), encoding="utf-8"))
    bank = [tuple(p) for p in gc.G["BANK"]["line"]]
    shz_xy = Polygon(gc.XS(bank + [(56.0, 18.2), (56.0, 37.0), (53.6, 36.0)] + [(aa, gc.d_edge(aa)) for aa in np.linspace(53.4, 40.6, 20)])).buffer(0).intersection(gc.garden_poly())
    SHZ = Polygon(rot(np.asarray(shz_xy.exterior.coords))).buffer(0)
    MIN = uv_poly(mn["AREA"])
    REG = unary_union([uv_rect(-0.5, 21.0, -0.5, 15.1), MIN.buffer(0.3), uv_poly([(0.0, -3.45), (-1.25, -3.45), (-8.55, 0.95), (-9.7, 1.75), (0.0, 1.75)]), SHZ.buffer(0.3)]).buffer(0.05)

    F = Fig()
    minx, miny, maxx, maxy = REG.bounds
    LEG_W = 112.0
    F.o = np.array([4.0 - minx * K, (PAPER[1] - (maxy - miny) * K) / 2 - miny * K + 4])

    # 地：しずかのもりの面（土手の線は破線）
    F.poly(SHZ, fc=C["shizu"], z=0.1)
    F.line(SHZ.exterior, c="#6f8f5a", lw=0.3, z=0.15, ls=(0, (3, 2)))
    # 床の噴水（φ4.0）とくぼ地の底（直径2.0）：garden.json の中心と半径（3dm の 96g・90g と同じ所）
    for key_, r_, fc_, ec_ in (("SPLASH", gc.G["SPLASH"]["r"][0], C["water"], "#7fa9b8"), ("BOWL", gc.G["BOWL"]["flat_r"], C["bowl"], "#9a8f73")):
        cx_, cy_ = rot([gc.X(*gc.G[key_]["c"])])[0]
        F.poly(shapely.geometry.Point(cx_, cy_).buffer(r_, 64), fc=fc_, ec=ec_, lw=LW_T, z=0.7)
    # 南の縁側（3dm の 14 の南の三角は上面が取れないので、同じ形の写し minami.json の ENGAWA で塗る）
    F.poly(uv_poly([(0.0, -3.45), (-1.25, -3.45), (-8.55, 0.95), (-9.1, 1.4), (-9.1, -0.3), (0.0, -0.3)]).union(
        uv_poly([(-9.1, -0.3), (0.0, -0.3), (0.0, 1.6), (-9.1, 1.4)])), fc=C["porch"], z=0.25)   # 木戸の内側の三角とポーチ（壁も柵も無く一続き、外構の決定）
    F.poly(uv_poly(mn["ENGAWA"]), fc=C["engo"], ec="black", lw=LW_T, z=0.96)
    # 0・1歳の水まわりと2歳のトイレの床（壁で囲まれた所、3dm の 38 の壁の内のり）
    F.poly(uv_rect(9.0, 11.94, 1.72, 4.6), fc=C["wet"], z=1.1)
    F.poly(uv_rect(12.06, 14.64, 1.72, 4.55), fc=C["wet"], z=1.1)

    crowns = []
    for z, g, st, ln, nm, lo, hi in sorted(items, key=lambda t: t[0]):
        g = g.intersection(REG) if st.get("kind") not in ("crown", "trunk") else g
        if g.is_empty:
            continue
        k = st.get("kind")
        if k == "eave":
            continue
        if k == "crown":
            crowns.append((g, st))
            continue
        if k == "trunk":
            if REG.contains(g.centroid):
                F.poly(g.convex_hull, fc=C["tree"], z=8.6)
            continue
        if k == "curve78":
            F.line(g, c="#8a7a55", lw=0.3, z=0.9, ls=(0, (1, 1)))
            continue
        if k == "curve75":
            F.line(g, c="black", lw=LW_T, z=4)
            continue
        F.poly(g, fc=st.get("fc", "none"), ec=st.get("ec", "none"), lw=st.get("lw", 0), z=z, ls=st.get("ls", "-"))
    # 屋根の縁（破線）
    roof = unary_union([g for z, g, st, *_ in items if st.get("kind") == "eave"])
    if not roof.is_empty:
        F.line(roof.buffer(0.35, join_style=2).buffer(-0.35, join_style=2).boundary.intersection(REG.buffer(0.2)), c="#555555", lw=0.25, z=9, ls=(0, (5, 2.5)))
    # 木の樹冠（輪郭だけ、範囲の中の物）
    for g, st in crowns:
        h = g.convex_hull
        if not REG.contains(h.centroid):
            continue
        if st.get("willow"):
            F.poly(h, fc="#DCE7B0", ec=C["tree"], lw=0.35, z=2.0)
        else:
            F.poly(h, fc="none", ec="#7f9d63", lw=0.25, z=8.5)

    # 架構の番号（南の妻の西、細い字）
    for k_ in range(1, 9):
        x, y = F.pm(RP(3 * (k_ - 1), -1.0))[0]
        F.text(x, y, str(k_), size=1.1, color="#888888", ha="center", va="center")
    x, y = F.pm(RP(-0.9, -1.0))[0]
    F.text(x, y, "架構", size=1.1, color="#888888", ha="center", va="center")

    # 番号
    cnt = {}
    rows = []
    for grp, u, v, s in LEG:
        if grp.startswith("切り株"):
            # 切り株（3dm の木口の中心。0歳の側 u<6、1歳の側 u6〜12、2歳、しずかのもり）
            k_ = grp[-1]
            g_ = {"0": "0歳", "1": "1歳", "2": "2歳", "S": "しずかのもり"}[k_]
            if k_ == "S":
                ss = [(Q[:, 0].mean(), Q[:, 1].mean(), nm) for ln, nm, T, P, Q in objs if ln.startswith("95k")]
            else:
                lo_, hi_ = {"0": (-1, 6), "1": (6, 12), "2": (12, 18)}[k_]
                ss = [(Q[:, 0].mean(), Q[:, 1].mean(), nm) for ln, nm, T, P, Q in objs if ln.startswith("40t") and lo_ <= Q[:, 0].mean() < hi_]
            if not ss:
                continue
            cnt[g_] = cnt.get(g_, 0) + 1
            for (uu, vv, _) in ss:
                F.num(F.pm(RP(uu + 0.55, vv))[0], cnt[g_], GCOL[g_], r=1.0)
            n_ = len(ss)
            rows.append((g_, cnt[g_], {"0": f"切り株×{n_}：低く太い（h0.19）、手をついて立つ",
                                         "1": f"切り株×{n_}：低く太い（h0.18〜0.19）、手をついて立つ",
                                         "2": f"切り株×{n_}：腰掛け・台・積む遊び（h0.21）",
                                         "S": f"切り株×{n_}：低め（h0.16〜0.30）、腰掛け・つかまり立ち"}[k_]))
            print("切り株", g_, [(round(a_, 2), round(b_, 2)) for a_, b_, _ in ss])
            continue
        if grp == "土手":
            cnt["しずかのもり"] = cnt.get("しずかのもり", 0) + 1
            q_ = SHZ.exterior.interpolate(SHZ.exterior.project(shapely.geometry.Point(RP(18.0, 26.0))))
            F.num(F.pm((q_.x, q_.y))[0], cnt["しずかのもり"], GCOL["しずかのもり"])
            rows.append(("しずかのもり", cnt["しずかのもり"], s))
            continue
        cnt[grp] = cnt.get(grp, 0) + 1
        if u is None:                                          # 置き場はそのレイヤーの物の中の一点
            g_ = unary_union([g for z, g, st, ln, *_ in items if ln.startswith(v)]).intersection(REG)
            q_ = g_.representative_point()
            F.num(F.pm((q_.x, q_.y))[0], cnt[grp], GCOL[grp])
            rows.append((grp, cnt[grp], s))
            continue
        F.num(F.pm(RP(u, v))[0], cnt[grp], GCOL[grp])
        rows.append((grp, cnt[grp], s))

    # 方位と縮尺
    nx, ny = 12.0, PAPER[1] - 14
    north = rot([[0, 1]])[0]
    F.ax.annotate("", xy=(nx + north[0] * 7, ny + north[1] * 7), xytext=(nx, ny), arrowprops=dict(arrowstyle="-|>", lw=0.6, color="#222222"))
    F.text(nx + north[0] * 9.5, ny + north[1] * 9.5, "N", size=2.2, bold=True, ha="center", va="center")
    sx, sy = 6.0, 6.0
    for i in range(2):
        F.ax.add_patch(plt.Rectangle((sx + i * 5 * K, sy), 5 * K, 0.9, fc="#222222" if i == 0 else "white", ec="#222222", lw=0.3))
    F.text(sx, sy - 3.0, "0", size=1.4); F.text(sx + 10 * K, sy - 3.0, "10 m", size=1.4, ha="center")
    F.text(sx + 10 * K + 6, sy - 0.1, "1/200（A1）　高野川を下に（配置図と同じ向き）。破線は軒の線・天蓋・しずかのもりの縁", size=1.4, color="#555555")

    # 凡例
    lx = PAPER[0] - LEG_W
    y = PAPER[1] - 6
    LH = 2.4
    cur = None
    for grp, n, s in rows:
        if grp != cur:
            cur = grp
            y -= 1.0
            sub = next(d for g_, d, _ in GROUPS if g_ == grp)
            F.text(lx, y, grp, size=2.0, bold=True, color=GCOL[grp])
            if sub:
                F.text(lx + 2.0 * len(grp) / 0.72 * 0.98 + 2, y, sub, size=1.5, color="#666666")
            y -= LH + 0.2
        F.num((lx + 1.3, y + 0.6), n, GCOL[grp], r=1.05)
        F.text(lx + 3.4, y, s, size=1.6)
        y -= LH
    print(f"凡例 {len(rows)} 行、下端 {y:.1f} mm")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    F.fig.savefig(OUT)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import hiragino
    hiragino.convert(OUT, OUT)                 # 書体をヒラギノ角ゴシックに（ユーザー 11-02）
    import svg_hiragino
    svg_hiragino.convert(OUT)                  # Illustrator 用の SVG（文字は文字のまま、ユーザー 11-02）
    if a.png:
        F.fig.savefig(a.png, dpi=140)
    print("→", OUT)


if __name__ == "__main__":
    main()
