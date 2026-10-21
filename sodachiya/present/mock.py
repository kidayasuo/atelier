"""育ち舎　提出 A1×5 枚の仮の割付（プレゼンの準備のチャット）

実寸の確認が目的：3dm（sodachiya_exact_mesh.3dm）から平面・配置・立面の外形を
その縮尺のまま描き、自動の断面（model/drawings）や他のチャットの図（out/）を
実寸または縮小で貼り込む。未作成のものは破線の枠（大きさは実寸）で示す。
紫の文字は割付の注記（本番では消す）。

python sodachiya/present/mock.py  →  sodachiya/present/out/sodachiya_present_mock.pdf / .png
"""
import os, json
import numpy as np
import rhino3dm as r
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPoly
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, MultiPolygon, MultiPoint, LineString
from shapely.ops import unary_union
import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONTB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
plt.rcParams["font.family"] = FontProperties(fname=FONT).get_name()
for f in (FONT, FONTB):
    if os.path.exists(f):
        matplotlib.font_manager.fontManager.addfont(f)

W, H = 841.0, 594.0            # A1 横（mm）
M = 15.0                       # 余白
NOTE = "#6B4FE0"               # 割付の注記（本番では消す）
INK = "#222222"
MM = 72 / 25.4

# ---------------------------------------------------------------- 3dm
m = r.File3dm.Read(os.path.join(ROOT, "model", "sodachiya_exact_mesh.3dm"))
lname = {l.Index: l.Name for l in m.Layers}


def curve_pts(c, n=64):
    if isinstance(c, r.PolylineCurve):
        return [(c.Point(i).X, c.Point(i).Y, c.Point(i).Z) for i in range(c.PointCount)]
    d = c.Domain
    out = []
    for i in range(n + 1):
        p = c.PointAt(d.T0 + (d.T1 - d.T0) * i / n)
        out.append((p.X, p.Y, p.Z))
    return out


objs = []   # dict(layer, kind, tris|pts)
for o in m.Objects:
    g = o.Geometry
    ln = lname[o.Attributes.LayerIndex]
    if isinstance(g, r.Mesh):
        v = g.Vertices
        V = np.array([(v[i].X, v[i].Y, v[i].Z) for i in range(len(v))]) / 1000
        F = []
        fs = g.Faces
        for i in range(len(fs)):
            f = fs[i]
            F.append((f[0], f[1], f[2]))
            if f[3] != f[2]:
                F.append((f[0], f[2], f[3]))
        objs.append(dict(layer=ln, kind="mesh", V=V, F=np.array(F)))
    elif isinstance(g, r.Extrusion):
        P = []
        for s in (0.0, 1.0):
            c = g.Profile3d(0, s)
            if c is not None:
                P += curve_pts(c, 24)
        if P:
            objs.append(dict(layer=ln, kind="solid", V=np.array(P) / 1000))
    elif isinstance(g, r.Brep):
        for fi in range(len(g.Faces)):
            mm = g.Faces[fi].GetMesh(r.MeshType.Any)
            if mm is None:
                continue
        bb = g.GetBoundingBox()
        P = [(x, y, z) for x in (bb.Min.X, bb.Max.X) for y in (bb.Min.Y, bb.Max.Y) for z in (bb.Min.Z, bb.Max.Z)]
        objs.append(dict(layer=ln, kind="solid", V=np.array(P) / 1000))
    elif isinstance(g, (r.PolylineCurve, r.NurbsCurve, r.LineCurve)):
        objs.append(dict(layer=ln, kind="curve", V=np.array(curve_pts(g)) / 1000))


def L(prefix):
    return [o for o in objs if o["layer"].startswith(prefix)]


def cen(prefix):
    return np.vstack([o["V"][:, :2] for o in L(prefix)]).mean(0)


# 紙の座標：x＝南の妻から北へ、y＝東（園庭、下）から西（道路、上）へ
C0 = np.vstack([o["V"][:, :2] for o in L("10_")]).mean(0)
ax_sn = cen("35_") - cen("52_")
ax_sn /= np.linalg.norm(ax_sn)
roof = np.vstack([o["V"][:, :2] for o in L("10_")]) - C0
uS = roof @ ax_sn
# 主軸は屋根の主成分に合わせる（向きは南→北）
_, _, vt = np.linalg.svd(roof)
d = vt[0] * np.sign(vt[0] @ ax_sn)
wv = np.array([-d[1], d[0]])
if (cen("20_") - C0) @ wv < 0:
    wv = -wv
ux0 = (roof @ d).min()                 # 南の端を 0 に


def to_s(P):
    Q = P[:, :2] - C0
    return np.c_[Q @ d - ux0, Q @ wv]


NORTH = np.array([0.0, 1.0])           # 3dm の +Y を北とする
north_s = np.array([NORTH @ d, NORTH @ wv])


def proj(o, mode):
    """mode: plan / east / west → 2D 点（m）"""
    V = o["V"]
    S = to_s(V)
    if mode == "plan":
        return S
    if mode == "east":
        return np.c_[S[:, 0], V[:, 2]]
    if mode == "west":
        return np.c_[-S[:, 0], V[:, 2]]


def shape(o, mode):
    P = proj(o, mode)
    if o["kind"] == "mesh":
        polys = []
        for f in o["F"]:
            t = Polygon(P[f])
            if t.area > 1e-5:
                polys.append(t)
        if not polys:
            return None
        return unary_union(polys).buffer(0)
    if o["kind"] == "solid":
        h = MultiPoint([tuple(p) for p in P]).convex_hull
        return h if h.area > 1e-5 else None
    if o["kind"] == "curve":
        return LineString(P) if len(P) > 1 else None


def depth(o, mode):
    S = to_s(o["V"])
    return S[:, 1].mean() if mode == "east" else -S[:, 1].mean()


# ---------------------------------------------------------------- 色
ROOM = {
    "53_": "#E6EFC2", "54_": "#C5DE9A", "59_1F_3歳": "#9FCB84", "59_1F_4歳": "#86BC78",
    "59_1F_5歳": "#6FA96E", "59_1F_医務": "#F7F3EA", "59_1F_事務": "#E9DCC4",
    "59_1F_ホール": "#E3C08D", "31_": "#F6E3A4", "32_": "#F0B98A", "34_": "#F7D3B0",
    "33_": "#E3C08D", "57_": "#D5EBEE", "59_1F_便所": "#D5EBEE", "52_": "#E8E2D6",
    "56_": "#F4EBDD", "59_1F_西吹き抜け": "#F4EBDD", "13_": "#F4EBDD", "14_": "#EFE6D6",
    "15_": "#D9CFBF", "12_": "#F7F2E8", "36_": "#E3DAF0",
    "41_": "#E3DAF0", "42_": "#D5EBEE", "43_": "#E3DAF0", "44_": "#E3DAF0", "45_": "#E3DAF0",
}


def room_color(ln):
    best = None
    for k, c in ROOM.items():
        if ln.startswith(k) and (best is None or len(k) > len(best[0])):
            best = (k, c)
    return best[1] if best else None


# ---------------------------------------------------------------- 描画の道具
def page():
    fig = plt.figure(figsize=(W / 25.4, H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    return fig, ax


def T(ax, x, y, s, size=3.0, color=INK, bold=False, ha="left", va="baseline", **kw):
    """size は文字の高さ（mm）"""
    pt = size / 0.3528 / 0.72
    ax.text(x, y, s, fontsize=pt, color=color, ha=ha, va=va,
            fontproperties=FontProperties(fname=FONTB if bold else FONT, size=pt), **kw)


def frame(ax, no, theme, focus, order):
    ax.add_patch(Rectangle((M, M), W - 2 * M, H - 2 * M, fill=False, lw=0.6, ec=INK))
    ax.plot([M, W - M], [H - M - 16, H - M - 16], color=INK, lw=0.4)
    T(ax, M + 4, H - M - 11, "こどもたちの育ち舎", 6.5, bold=True)
    T(ax, M + 92, H - M - 11, f"{no}/5　{theme}", 5.0, bold=True)
    T(ax, W - M - 4, H - M - 11, "建築設計実習Ⅱ—Ⅰ　2026.11.05　木田", 3.0, ha="right")
    # 注記
    T(ax, M + 4, M - 6, f"［割付の注記］フォーカス：{focus}　／　目に入る順：{order}", 3.2, NOTE)


def box(ax, x, y, w, h, label, sub="", color=NOTE, fill="#F4F1FF"):
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=color, lw=0.6, ls=(0, (3, 2))))
    T(ax, x + w / 2, y + h / 2 + 2.5, label, 3.6, color, bold=True, ha="center", va="center")
    if sub:
        for i, s in enumerate(sub.split("\n")):
            T(ax, x + w / 2, y + h / 2 - 3 - 4.5 * i, s, 2.6, color, ha="center", va="center")


def dimnote(ax, x, y, s):
    T(ax, x, y, s, 2.6, NOTE)


def title(ax, x, y, s, scale=""):
    T(ax, x, y, s, 4.2, bold=True)
    if scale:
        T(ax, x + sum(5.9 if ord(ch) > 0x2000 else 3.2 for ch in s) + 3, y, scale, 3.0)


def draw_shape(ax, g, xf, fc="none", ec=INK, lw=0.2, z=1, ls="-"):
    if g is None or g.is_empty:
        return
    geoms = getattr(g, "geoms", [g])
    for gg in geoms:
        if gg.geom_type == "Polygon":
            xy = xf(np.array(gg.exterior.coords))
            ax.add_patch(MPoly(xy, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls))
        elif gg.geom_type in ("LineString", "LinearRing"):
            xy = xf(np.array(gg.coords))
            ax.plot(xy[:, 0], xy[:, 1], color=ec, lw=lw, zorder=z, ls=ls)
        elif gg.geom_type in ("MultiPolygon", "GeometryCollection", "MultiLineString"):
            draw_shape(ax, gg, xf, fc, ec, lw, z, ls)


def xform(ox, oy, scale, x0=0, y0=0, sx=1):
    """モデル（m）→ 紙（mm）。ox,oy＝紙の上の (x0,y0) の位置"""
    k = 1000 / scale

    def f(P):
        P = np.asarray(P, float)
        return np.c_[ox + sx * (P[:, 0] - x0) * k, oy + (P[:, 1] - y0) * k]
    return f


def clip_rect(ax, x, y, w, h):
    rp = Rectangle((x, y), w, h, transform=ax.transData, fc="none", ec="none")
    ax.add_patch(rp)
    return rp


def apply_clip(ax, rp, start):
    for a in ax.patches[start:] + ax.lines[:]:
        if a is not rp and getattr(a, "_clipme", True):
            pass
    for a in list(ax.patches)[start:]:
        if a is not rp:
            a.set_clip_path(rp)


def north(ax, x, y, ln=12):
    v = north_s / np.linalg.norm(north_s)
    ax.annotate("", xy=(x + v[0] * ln, y + v[1] * ln), xytext=(x, y),
                arrowprops=dict(arrowstyle="-|>", lw=0.6, color=INK))
    T(ax, x + v[0] * (ln + 4), y + v[1] * (ln + 4), "N", 3.2, ha="center", va="center", bold=True)


def scalebar(ax, x, y, scale, meters=10):
    k = 1000 / scale
    for i in range(meters // 5):
        ax.add_patch(Rectangle((x + i * 5 * k, y), 5 * k, 1.2, fc=INK if i % 2 == 0 else "white", ec=INK, lw=0.3))
    T(ax, x, y - 4, "0", 2.4)
    T(ax, x + meters * k, y - 4, f"{meters}m", 2.4, ha="center")


# 縮尺ごとに形をまとめて作る
PLAN_SKIP = ("10_", "20_", "28_", "29_", "30_", "50", "51_", "26_", "11b", "11c", "22b", "22c", "22d",
             "23_", "41_", "42_", "43_", "44_", "45_", "47_", "58_", "88_", "83_", "82_")
plan_items = []
for o in objs:
    ln = o["layer"]
    if ln.startswith(PLAN_SKIP) or ln.startswith(("00_", "01_", "02_")):
        continue
    if o["kind"] != "curve" and o["V"][:, 2].min() > 2.0:
        continue
    g = shape(o, "plan")
    if g is None:
        continue
    plan_items.append((ln, o["kind"], g))

roofs_plan = unary_union([shape(o, "plan") for o in L("10_") + L("20_") + L("35_") if shape(o, "plan")])
site_items = [(o["layer"], shape(o, "plan")) for o in objs if o["layer"].startswith(("00_", "01_", "02_", "6", "7"))]

# 面積（1 階の部屋の床）
areas = {}
for ln, kind, g in plan_items:
    if room_color(ln) and kind == "mesh":
        areas.setdefault(ln, []).append(g)
for o in L("4"):
    if o["layer"].startswith(("41_", "42_", "43_", "44_", "45_")):
        g = shape(o, "plan")
        if g is not None:
            areas.setdefault(o["layer"], []).append(g)
AREA = {k: unary_union(v).area for k, v in areas.items()}


def draw_plan(ax, ox, oy, scale, x0, y0, wbox, hbox, keyhi=None, thin=False):
    """1 階平面（3dm から）。窓 (wbox,hbox) は紙の mm。keyhi＝強調する層の頭"""
    xf = xform(ox, oy, scale, x0, y0)
    rp = clip_rect(ax, ox, oy, wbox, hbox)
    start = len(ax.patches)
    # 屋根の輪郭（破線、庇の位置）
    draw_shape(ax, roofs_plan, xf, ec="#999999", lw=0.15, ls=(0, (4, 2)), z=6)
    base = ("12_", "13_", "14_", "15_", "56_", "59_1F_西吹き抜け", "33_")
    order = sorted(plan_items, key=lambda it: 0 if it[0].startswith(base) else 1)
    for ln, kind, g in order:
        c = room_color(ln)
        if c:
            fc = c
            if keyhi is not None:
                fc = c if ln.startswith(tuple(keyhi)) else "#F1F1F1"
            draw_shape(ax, g, xf, fc=fc, ec="none", lw=0, z=1)
    for ln, kind, g in plan_items:
        if room_color(ln):
            continue
        if ln.startswith(("17_", "21_", "24_", "11a", "22a", "35_")):
            draw_shape(ax, g, xf, fc="#333333", ec="#333333", lw=0.1, z=5)
        elif ln.startswith(("16_", "19_", "27_", "48_")):
            draw_shape(ax, g, xf, fc="#BFD9EA", ec="#6A9CBF", lw=0.1, z=4)
        elif ln.startswith(("6", "7")):
            draw_shape(ax, g, xf, fc="none" if kind == "curve" else "#EDF2E6", ec="#8A9A7A", lw=0.12, z=2)
        elif not thin:
            draw_shape(ax, g, xf, fc="white", ec="#777777", lw=0.1, z=3)
    for a in ax.patches[start:]:
        a.set_clip_path(rp)
    for a in ax.lines:
        a.set_clip_path(rp)
    return xf


def draw_elev(ax, mode, ox, oy, scale, x0, wbox, hbox):
    xf = xform(ox, oy, scale, x0, -0.3)
    rp = clip_rect(ax, ox, oy, wbox, hbox)
    start = len(ax.patches)
    keep = ("10_", "11a", "11b", "11c", "14_", "16_", "17_", "18_", "19_", "20_", "21_", "22a", "22d",
            "26_", "28_", "30_", "35_", "50a", "50c", "60_", "66_", "70_", "71_", "72_", "73_", "62_", "64_")
    items = [o for o in objs if o["layer"].startswith(keep) and o["kind"] != "curve"]
    items.sort(key=lambda o: -depth(o, mode))
    for o in items:
        g = shape(o, mode)
        ln = o["layer"]
        if ln.startswith(("10_", "20_", "35_", "26_")):
            fc = "#8C8C8C"
        elif ln.startswith(("16_", "19_", "28_")):
            fc = "#D6E6F0"
        elif ln.startswith(("11", "22", "18_", "30_", "50c")):
            fc = "#D9BE94"
        elif ln.startswith("7") or ln.startswith("6"):
            fc = "#E9EFE2"
        else:
            fc = "white"
        draw_shape(ax, g, xf, fc=fc, ec="#333333", lw=0.12, z=2)
    gl = xf(np.array([[x0 - 50, -0.3], [x0 + 200, -0.3]]))
    ax.plot(gl[:, 0], gl[:, 1], color=INK, lw=0.6)
    for a in ax.patches[start:]:
        a.set_clip_path(rp)
    ax.lines[-1].set_clip_path(rp)
    return xf


# ---------------------------------------------------------------- 寸法の確認
S_all = to_s(np.vstack([o["V"] for o in L("10_") + L("20_") + L("35_") + L("14_") + L("52_") + L("62_")]))
BX0, BY0 = S_all.min(0)
BX1, BY1 = S_all.max(0)
site_s = to_s(np.vstack([o["V"] for o in L("00_")]))
SX0, SY0 = site_s.min(0)
SX1, SY1 = site_s.max(0)
info = dict(building=[round(BX1 - BX0, 1), round(BY1 - BY0, 1)], site=[round(SX1 - SX0, 1), round(SY1 - SY0, 1)])
print("建物の外形（m）", info["building"], " 敷地（m）", info["site"])

embeds = {i: [] for i in range(1, 6)}   # (src_pdf, page, clip_mm(x0,y0,x1,y1)|None, dest_mm(x,y,w,h) 下原点, keep_ratio)
SEC = os.path.join(ROOT, "model", "drawings", "sodachiya_sections_1-100.pdf")
CLIP_A = (25, 38, 841, 201)
CLIP_B = (25, 244, 410, 377)
CLIP_C = (430, 244, 812, 377)


def embed(sheet, src, clip, x, y, scale_factor=1.0, pageno=0, fit=None):
    """clip（元の PDF の mm、上原点）を、紙の (x,y)（下原点、左下）に倍率 scale_factor で置く。
    fit=(w,h) を渡すと、その枠に縮めて入れる。戻り値は置いた大きさ（mm）"""
    if clip is None:
        pr = fitz.open(src)[pageno].rect
        clip = (0, 0, pr.width / MM, pr.height / MM)
    w0, h0 = clip[2] - clip[0], clip[3] - clip[1]
    if fit:
        scale_factor = min(fit[0] / w0, fit[1] / h0)
    w, h = w0 * scale_factor, h0 * scale_factor
    embeds[sheet].append((src, pageno, clip, (x, y, w, h)))
    return w, h


figs = []

# ================================================================ 1　敷地と応答
fig, ax = page()
frame(ax, 1, "敷地と応答", "この案が敷地から生まれたこと（比叡・高野川・扇状地・西の細い道）",
      "模型写真（入口の一枚）→ タイトルと趣旨の冒頭 → 配置図 → 立地と応答")
top = H - M - 16
T(ax, M + 6, top - 15, "地に足をつけて育つ", 10.0, bold=True)
concept = ("比叡から降りる冷気と高野川の流れが出会う松ヶ崎の扇状地に、こどもたちが地に足をつけて育つ場所をつくる。"
           "ゆるやかな弧を描く木造平屋の本館に 0 歳から 5 歳までのすべての部屋を 1 階に並べ、東の縁側と深い庇で園庭へ開く。"
           "園庭には用水を借りた小川と、比叡に見立てた築山を置く。玄関ホールに面したオープンキッチンを園の中心に据え、"
           "食べることを日々の求心力とする。歳とともに一人で歩ける道が延び、3 歳からは海峡と呼ぶ通り土間をこどもだけで渡る。"
           "3 m スパンの木造架構によるスケルトン＆インフィルでクラスや用途の変化を受け止め、"
           "越屋根の温度差換気と夏の夜の冷気で、LEED v5 Gold 相当・ZEB Ready 相当を目指す。")
import textwrap
lines = textwrap.wrap(concept, 40)
for i, s in enumerate(lines):
    T(ax, M + 6, top - 28 - i * 6.0, s, 3.6)
dimnote(ax, M + 6, top - 28 - len(lines) * 6.0 - 1, f"設計趣旨 約 {len(concept)} 字（課題は 300 字程度）。文字 3.6 mm なら 1 m 離れて読める")
# 立地と応答（趣旨の右）
rx = M + 6 + 250
title(ax, rx, top - 12, "立地と応答")
cw, ch = 107, 92
for i, (h1, s1) in enumerate([
        ("比叡（東から 24°）", "冷気→本館は東向き\n越屋根で夏の夜に冷やす\n築山の頂から望む"),
        ("高野川と崖 4〜5 m", "修景地域の右岸→\n川へ下がる屋根・植栽帯\n浸水 1.5 m→大学へ避難"),
        ("扇状地と用水", "用水を借りた小川と築山\n＝園内の高野川と比叡"),
        ("西の細い道と住宅", "西館の屋根を西で低く\n車は突き出た木より南で")]):
    cx = rx + (i % 2) * (cw + 6)
    cy = top - 18 - ch - (i // 2) * (ch + 6)
    box(ax, cx, cy, cw, ch, h1, "小さな図＋\n" + s1, fill="#FAF8FF")
# 配置図 1/200（高野川の辺を下辺に水平：川向こうから見る向き、ユーザー案）
from shapely import affinity
_site = max([o for o in L("00_") if o["kind"] == "curve"], key=lambda o: len(o["V"]))
_S = to_s(_site["V"])
_riv = to_s(np.vstack([o["V"] for o in L("02_")])).mean(0)
_best = None
for i in range(len(_S) - 1):
    p, q = _S[i], _S[i + 1]
    if np.linalg.norm(q - p) < 5:
        continue
    dd = np.linalg.norm((p + q) / 2 - _riv)
    if _best is None or dd < _best[0]:
        _best = (dd, p, q)
_e = _best[2] - _best[1]
ROT = -np.degrees(np.arctan2(_e[1], _e[0]))
for cand in (ROT, ROT + 180):
    r = np.radians(cand)
    if (_riv @ np.array([np.sin(r), np.cos(r)])) < (_S @ np.array([np.sin(r), np.cos(r)])).mean():
        ROT = cand
        break
rot = lambda g: affinity.rotate(g, ROT, origin=(0, 0)) if g is not None else None
_Q = np.array(rot(Polygon(_S)).exterior.coords)
QX0, QY0 = _Q.min(0)
QX1, QY1 = _Q.max(0)
sx, sy = M + 6, M + 8
sw, sh = 460, 322
title(ax, sx, sy + sh + 4, "配置図", "1/200　高野川を下に（川向こうから見る向き）")
pad = 6
xf = xform(sx + (sw - (QX1 - QX0 + 2 * pad) * 5) / 2, sy, 200, QX0 - pad, QY0 - pad)
rp = clip_rect(ax, sx, sy, sw, sh)
st = len(ax.patches); stl = len(ax.lines)
for ln, g in site_items:
    if g is None:
        continue
    g = rot(g)
    if ln.startswith("02_"):
        draw_shape(ax, g, xf, fc="#DCE8EE", ec="#8FB0C0", lw=0.15, z=0)
    elif ln.startswith("00_"):
        draw_shape(ax, g, xf, ec=INK, lw=0.5, z=3, ls=(0, (6, 2, 1, 2)))
    elif ln.startswith("01_"):
        draw_shape(ax, g, xf, ec="#666666", lw=0.3, z=3)
    else:
        draw_shape(ax, g, xf, fc="none" if g.geom_type.endswith("String") else "#EEF2E8", ec="#7D8C70", lw=0.12, z=2)
draw_shape(ax, rot(roofs_plan), xf, fc="#9A9A9A", ec="#444444", lw=0.25, z=5)
for a_ in ax.patches[st:] + ax.lines[stl:]:
    a_.set_clip_path(rp)
_gd = Polygon(_S).difference(roofs_plan.buffer(3))
_gd = max(getattr(_gd, "geoms", [_gd]), key=lambda g: g.area)
draw_shape(ax, rot(_gd), xf, fc="none", ec=NOTE, lw=0.6, ls=(0, (3, 2)), z=6)
_c = xf(np.array([rot(_gd).representative_point().coords[0]]))[0]
T(ax, _c[0], _c[1] + 3, "園庭（だいさんかく）", 3.6, NOTE, bold=True, ha="center")
T(ax, _c[0], _c[1] - 3, "園庭のチャットの図（1/200）を重ねる", 2.6, NOTE, ha="center")
_nv = north_s / np.linalg.norm(north_s)
_r = np.radians(ROT)
_nv = np.array([_nv[0] * np.cos(_r) - _nv[1] * np.sin(_r), _nv[0] * np.sin(_r) + _nv[1] * np.cos(_r)])
_nx, _ny = sx + sw - 20, sy + sh - 30
ax.annotate("", xy=(_nx + _nv[0] * 12, _ny + _nv[1] * 12), xytext=(_nx, _ny), arrowprops=dict(arrowstyle="-|>", lw=0.6, color=INK))
T(ax, _nx + _nv[0] * 16, _ny + _nv[1] * 16, "N", 3.2, ha="center", va="center", bold=True)
scalebar(ax, sx + 6, sy + 6, 200, 20)
dimnote(ax, sx + 130, sy + 6, f"高野川の辺を水平にすると敷地は {QX1-QX0:.0f}×{QY1-QY0:.0f} m → 1/200 で {(QX1-QX0)*5:.0f}×{(QY1-QY0)*5:.0f} mm（入る）。建物は約 {abs(ROT):.0f}° 傾く")
# 右の列：模型写真 2 枚
px = W - M - 6 - 297
box(ax, px, top - 8 - 210, 297, 210, "模型写真　A4（入口の一枚）",
    "園庭からこどもの目線（模型で約 10 mm）\n縁側・深い庇・比叡の方向を見る\n選抜で最初に目に入る位置")
box(ax, px, M + 8, 297, 300, "模型写真　鳥瞰", "敷地と高野川・崖・公園・西の道\n配置図と同じ向き（高野川を手前）にそろえる")
figs.append(fig)

# ================================================================ 2　こどもの一日（1 階平面）
fig, ax = page()
frame(ax, 2, "こどもの一日　1 階平面", "こどもが一日を過ごす場所としての平面（家具・午睡・靴の線・歳とともに延びる道）",
      "部屋の色 → 海峡とホール・キッチン → 縁側 → 家具 → 一日の帯")
pw, ph = W - 2 * M - 12, 410
px, py = M + 6, H - M - 16 - 12 - ph
title(ax, px, py + ph + 3, "1 階平面図", "1/100　道路・隣地境界線・家具。北が右、園庭が下")
x0p = BX0 - 1.5
y0p = BY0 - 4.0
draw_plan(ax, px, py, 100, x0p, y0p, pw, ph)
north(ax, px + pw - 18, py + 16)
scalebar(ax, px + 4, py + 4, 100, 10)
dimnote(ax, px + 70, py + 4, f"建物（庇・おむすび・みなみのさんかくまで）{info['building'][0]}×{info['building'][1]} m → 1/100 で {info['building'][0]*10:.0f}×{info['building'][1]*10:.0f} mm。"
        f"窓 {pw:.0f}×{ph} mm に入る。西の道路の幅は 3dm に無いので描き足す")
title(ax, px, py - 9, "こどもの一日　食べる・寝る・遊ぶ")
frames_ = [("登園 8:00", ["52_", "15_", "59_1F_ホール", "33_", "59_1F_事務（スパン"], "公園→木戸→小径→海峡／0・1 歳は受け取り土間"),
           ("遊ぶ 9:30", ["31_", "14_", "13_", "62_"], "遊戯室・縁側・園庭・回遊のはしご"),
           ("食べる 11:30", ["32_", "34_", "33_", "59_1F_3歳", "59_1F_4歳", "59_1F_5歳"], "キッチンから海峡を通って配膳"),
           ("寝る 12:45", ["53_", "54_", "59_1F_3歳", "59_1F_4歳"], "ねどこ・ロフトの下／5 歳は秋から段階的に"),
           ("降園 16:30", ["34_", "52_", "15_"], "はれのまで延長保育／縁台でお茶")]
fw = (pw - 4 * 6) / 5
for i, (h1, keys, s1) in enumerate(frames_):
    fx = px + i * (fw + 6)
    fy = M + 7
    ax.add_patch(Rectangle((fx, fy), fw, py - 14 - fy, fc="none", ec="#BBBBBB", lw=0.3))
    T(ax, fx + 3, py - 21, h1, 3.4, bold=True)
    draw_plan(ax, fx + 3, fy + 9, 600, x0p, y0p, fw - 6, 56, keyhi=keys, thin=True)
    T(ax, fx + 3, fy + 3, s1, 2.6)
dimnote(ax, px + pw - 330, py - 9, "一日の帯は 1/600 の小さな平面に色で（3dm から自動）")
figs.append(fig)

# ================================================================ 3　長手の帯（立面・縦断）
fig, ax = page()
frame(ax, 3, "どう見えるか　立面と縦断", "57 m の縁側と深い庇のリズム（東）、街に対して低い構え（西）",
      "東立面（平面の真下、柱がそろう）→ 縦断 → 西立面")
ex, ew = M + 6, W - 2 * M - 12
x0e = x0p
y = H - M - 16 - 14 - 100
title(ax, ex, y + 104, "東立面図（園庭側）", "1/100　1 階平面と同じ横位置")
draw_elev(ax, "east", ex, y, 100, x0e, ew, 100)
dimnote(ax, ex + ew - 250, y + 104, "2 枚目の真下に貼ると、平面と柱の位置が縦にそろう")
y2 = y - 12 - 163
title(ax, ex, y2 + 166, "縦断面図 A", "1/100　保育室の中ほど r=197 m で切って展開、西を見る")
embed(3, SEC, CLIP_A, ex, y2, 1.0)
dimnote(ax, ex + ew - 250, y2 + 166, "自動の断面 A をそのまま実寸で（model/drawings）")
y3 = M + 10
title(ax, ex, y3 + 108, "西立面図（道路側）", "1/100　北が左")
draw_elev(ax, "west", ex, y3, 100, -(BX1 + 1.5), ew, 104)
dimnote(ax, ex + ew - 330, y3 + 108, "道の向かいの住宅の高さを点線で描き足す（圧迫感の説明）")
gh = y2 - 4 - (y3 + 116)
gw = gh * 297 / 210
bx_ = ex + ew - 2 * gw - 10
for i, (h1, s1) in enumerate([("模型写真　西の道から", "人の目の高さ 1.5 m（模型 15 mm）\n低い軒と縦格子"),
                               ("模型写真　公園の木戸から", "アプローチの入口\n見送りの小径の奥にひろば")]):
    box(ax, bx_ + i * (gw + 10), y3 + 116, gw, gh, h1, s1)
figs.append(fig)

# ================================================================ 4　どう息をするか
fig, ax = page()
frame(ax, 4, "どう息をするか　断面と環境", "空気・光・熱の流れが形の理由になっていること（断面 C を主役に）",
      "断面 C 1/50 → ①〜⑨ と環境の枠 → 運転表 → 断面 B → 2 階")
CLIP_C2 = (455, 256, 800, 380)
hC = (CLIP_C2[3] - CLIP_C2[1]) * 2
cx, cy = M + 6, H - M - 16 - 12 - hC
title(ax, cx, cy + hC + 3, "断面図 C　4 歳・遊戯室", "1/50（1/100 の自動の図を 2 倍）　西の道路から園庭へ")
wC, _ = embed(4, SEC, CLIP_C2, cx, cy, 2.0)
dimnote(ax, cx + 380, cy + hC + 3, "左右に 道・向かいの住宅／園庭・築山 を描き足す。空気の矢印と①〜⑨を重ねる。断熱は帯で")
ex_ = cx + wC + 8
box(ax, ex_, cy, W - M - 6 - ex_, hC, "環境の枠", "LEED v5\nGold 相当\nZEB Ready\n相当\n\n脱炭素 ①〜⑤\n生活の質 ⑥⑦\n生態系 ⑧⑨", fill="#FAF8FF")
# 運転表（帯）
oy_ = cy - 8 - 52
for i, (h1, s1) in enumerate([("夏の昼", "庇で遮る・越屋根から抜く"), ("夏の夜", "比叡の冷気で冷やす（自動の窓）"),
                               ("春・秋", "手で開ける（表示灯）"), ("冬", "床暖房・熱交換の換気・断熱")]):
    box(ax, cx + i * 200, oy_, 192, 52, h1, s1, fill="#FAF8FF")
by = M + 10
S2 = to_s(np.vstack([o["V"] for o in L("20_")]))
x02, y02 = S2.min(0) - 1
w2 = (S2.max(0)[0] - S2.min(0)[0] + 2) * 10
h2 = (S2.max(0)[1] - S2.min(0)[1] + 2) * 10
title(ax, cx, by + 136 + 4, "断面図 B　海峡", "1/100　南の入口・キッチン・2 階・すき間・本館・縁側")
wB, hB = embed(4, SEC, CLIP_B, cx, by, 1.0)
f2x = W - M - 6 - w2
title(ax, f2x, by + h2 + 3, "2 階平面図（西館）", "1/100")
xf2 = xform(f2x, by, 100, x02, y02)
rp = clip_rect(ax, f2x, by, w2, h2)
st = len(ax.patches)
draw_shape(ax, unary_union([shape(o, "plan") for o in L("31_")]), xf2, fc="#FBF3D9", ec="none", z=0)
for o in objs:
    ln = o["layer"]
    if ln.startswith(("41_", "42_", "43_", "44_", "45_", "36_", "25_", "23_", "82_")):
        g = shape(o, "plan")
        draw_shape(ax, g, xf2, fc=room_color(ln) or "#F7F2E8", ec="#555555", lw=0.15, z=1)
    elif ln.startswith(("21_", "24_", "22a")):
        g = shape(o, "plan")
        draw_shape(ax, g, xf2, fc="#333333", ec="#333333", lw=0.1, z=3)
draw_shape(ax, unary_union([shape(o, "plan") for o in L("20_")]), xf2, ec="#999999", lw=0.15, ls=(0, (4, 2)), z=4)
for a in ax.patches[st:]:
    a.set_clip_path(rp)
T(ax, f2x + w2 * 0.72, by + h2 * 0.45, "遊戯室の吹き抜け", 3.0, "#8A7A40", ha="center")
dimnote(ax, f2x, by - 6, f"西館 {w2/10:.0f}×{h2/10:.0f} m → {w2:.0f}×{h2:.0f} mm（1 階平面と同じ向き）")
figs.append(fig)

# ================================================================ 5　暮らしと構造
fig, ax = page()
frame(ax, 5, "暮らしと構造", "近づいて読む人のための細部：寝る・遊ぶ・組み方・変わり方",
      "内観 → 同じ部屋の一日 → 遊戯室 → 接合部 → S&I → 面積表")
top = H - M - 16 - 8
box(ax, M + 6, top - 210, 297, 210, "内観　ホール（A4）", "海峡と飛び石・オープンキッチン\n梁の見える天井・越屋根の光の線\n（レンダリングか模型写真）")
x1 = M + 6 + 297 + 12
title(ax, x1, top - 4, "同じ部屋の一日", "3〜5 歳の保育室　断面 1/100")
SEC35 = os.path.join(ROOT, "out", "sodachiya_35_section.pdf")
CL35 = (30, 70, 360, 215)
for i, t_ in enumerate(["10:00 遊ぶ", "11:30 食べる", "13:30 寝る"]):
    yy = top - 12 - (i + 1) * 74
    embed(5, SEC35, CL35, x1 + 22, yy, 0.5)
    T(ax, x1, yy + 40, t_.split()[0], 3.0, bold=True)
    T(ax, x1, yy + 34, t_.split()[1], 2.8)
dimnote(ax, x1, top - 12 - 3 * 74 - 6, "今は同じ図（既存の 1/50 を縮小）。時刻ごとに家具・人・光を描き分ける")
x2 = x1 + 200
title(ax, x2, top - 4, "遊戯室", "平面・断面（縮小、遊戯室のチャット）")
PLAY = os.path.join(ROOT, "out", "sodachiya_play_01.pdf")
embed(5, PLAY, (0, 10, 297, 390), x2, top - 12 - 232, fit=(W - M - 6 - x2, 230))
by = M + 10
title(ax, M + 6, by + 228, "接合部", "タメディア型　2 枚の梁で柱を挟む（縮小）")
JD = os.path.join(ROOT, "out", "joint_detail.pdf")
embed(5, JD, None, M + 6, by + 30, fit=(255, 190))
T(ax, M + 6, by + 18, "京都の間伐材・金物を減らした接合", 3.4, bold=True)
x3 = M + 6 + 265
box(ax, x3, by, 200, 232, "スケルトン＆インフィル", "3 m スパンの骨格（固定）と\n間仕切り・家具（可変）を色分け\n\n今 ／ 定員が変わる ／\n学童・地域の場 の 3 コマ")
GD = os.path.join(ROOT, "out", "sodachiya_garden_01.pdf")
x4 = x3 + 210
title(ax, x4, by + 228, "園庭の断面", "縮小（園庭のチャット）")
embed(5, GD, (0, 388, 420, 575), x4, by + 100, fit=(200, 122))
T(ax, x4, by + 90, "築山・小川・水遊び場は遊ぶの答え", 3.0, bold=True)
REQ = [("乳児室（0・1 歳）", "53_", "約 60×2"), ("保育室（2 歳）", "54_", "約 60"),
       ("保育室（3 歳）", "59_1F_3歳", "約 60"), ("保育室（4 歳）", "59_1F_4歳", "約 60"), ("保育室（5 歳）", "59_1F_5歳", "約 60"),
       ("遊戯室", "31_", "240 以上"), ("調理室", "32_", "約 60"), ("医務室", "59_1F_医務", "約 30"),
       ("事務室", "59_1F_事務", "約 60"), ("休憩・会議（2 階）", "4", "60＋30"), ("はれのま", "34_", "（追加）")]
tx = x4 + 210
title(ax, tx, by + 228, "面積表", "㎡（仮）")
T(ax, tx, by + 218, "室", 2.6, NOTE); T(ax, tx + 52, by + 218, "要求", 2.6, NOTE); T(ax, W - M - 8, by + 218, "計画", 2.6, NOTE, ha="right")
for i, (n, k, q) in enumerate(REQ):
    if k == "4":
        a = sum(v for kk, v in AREA.items() if kk.startswith(("43_", "44_", "45_")))
    else:
        a = sum(v for kk, v in AREA.items() if kk.startswith(k))
    yy = by + 210 - i * 7.0
    T(ax, tx, yy, n, 2.7)
    T(ax, tx + 52, yy, q, 2.7)
    T(ax, W - M - 8, yy, f"{a:.1f}" if a else "—", 2.7, ha="right")
for j, s in enumerate(["3dm の床から自動で測った仮の値。", "医務・事務の不足を確かめる。", "園庭 350・駐車 5・延床 2,000・",
                       "倉庫 30・機械室 30 を本番で足す"]):
    T(ax, tx, by + 210 - len(REQ) * 7.0 - 2 - j * 5, s, 2.4, NOTE)
figs.append(fig)

# ---------------------------------------------------------------- 書き出し
base = os.path.join(OUT, "_base.pdf")
from matplotlib.backends.backend_pdf import PdfPages
with PdfPages(base) as pp:
    for f in figs:
        pp.savefig(f)
doc = fitz.open(base)
for si in range(1, 6):
    pg = doc[si - 1]
    for src, pno, clip, (x, y, w, h) in embeds[si]:
        sd = fitz.open(src)
        cr = fitz.Rect(clip[0] * MM, clip[1] * MM, clip[2] * MM, clip[3] * MM)
        dr = fitz.Rect(x * MM, (H - y - h) * MM, (x + w) * MM, (H - y) * MM)
        pg.show_pdf_page(dr, sd, pno, clip=cr)
sheets = os.path.join(OUT, "sodachiya_present_sheets.pdf")
doc.save(sheets)

# 壁に貼ったときの全体（3 枚＋2 枚）
pix = []
for i in range(5):
    p = doc[i].get_pixmap(dpi=60)
    fn = os.path.join(OUT, f"sheet{i+1}.png")
    p.save(fn)
    pix.append(plt.imread(fn))
fig = plt.figure(figsize=(841 / 25.4, 594 / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
SC = 594 / 2500                       # 壁の mm → 紙の mm
ax.set_xlim(0, 841 / SC)
ax.set_ylim(0, 2500)
ax.axis("off")
x0w, base_ = 250, 350
pos = {1: (x0w, base_ + 594 * 2), 2: (x0w, base_ + 594), 3: (x0w, base_),
       4: (x0w + 841 + 120, base_ + 594 + 297), 5: (x0w + 841 + 120, base_ + 297)}
for i in range(5):
    x, y = pos[i + 1]
    ax.imshow(pix[i], extent=(x, x + 841, y, y + 594), zorder=1, aspect="auto")
    ax.add_patch(Rectangle((x, y), 841, 594, fill=False, ec="#555555", lw=0.5, zorder=2))
ax.plot([100, 2100], [0 + 5, 5], color=INK, lw=1)
ax.plot([100, 2100], [1500, 1500], color=NOTE, lw=0.8, ls=(0, (6, 4)))
def TW(x, y, s, size, **kw):  # size は紙の mm
    T(ax, x, y, s, size, **kw)
TW(110, 1515, "目の高さ 1.5 m", 3.2, color=NOTE)
TW(110, 20, "床", 3.2)
TW(x0w, 2400, "壁に貼ったとき　左：1〜3 を縦につなぐ（高さ約 1.8 m）　右：4・5 を縦につなぐ", 6.0, bold=True)
notes = ["左の列は 配置 1/200 → 1 階平面 1/100 → 立面・縦断 1/100。",
         "どれも北が右・園庭が下で、建物の位置が縦にそろう。",
         "目の高さに来るのは 1 階平面（最も細かい図）と断面 C。",
         "右の列は下端が約 0.6 m。暮らしと構造は近づいて読む。",
         "製図台に置くなら 2＋2＋1（1・2／3・4／5）に切り分ける。"]
for i, s in enumerate(notes):
    TW(x0w + 841 * 2 + 200, 2050 - i * 70, s, 3.2, color=NOTE)
ov = os.path.join(OUT, "_overview.pdf")
fig.savefig(ov)
fig.savefig(os.path.join(OUT, "sodachiya_present_overview.png"), dpi=40)

final = fitz.open(ov)
final.insert_pdf(fitz.open(sheets))
final.save(os.path.join(OUT, "sodachiya_present_mock.pdf"))
for f in (base, ov):
    os.remove(f)
json.dump(dict(info, areas={k: round(v, 1) for k, v in AREA.items()}), open(os.path.join(OUT, "mock_info.json"), "w"), ensure_ascii=False, indent=1)
print("ok")
