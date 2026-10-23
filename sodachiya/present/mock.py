"""育ち舎　提出A1×5枚の仮の割付（プレゼンの準備のチャット）

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

W, H = 841.0, 594.0            # A1横（mm）
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
ux0 = (roof @ d).min()                 # 南の端を0に


def to_s(P):
    Q = P[:, :2] - C0
    return np.c_[Q @ d - ux0, Q @ wv]


NORTH = np.array([0.0, 1.0])           # 3dmの+Yを北とする
north_s = np.array([NORTH @ d, NORTH @ wv])


def proj(o, mode):
    """mode: plan / east / west → 2D点（m）"""
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
    """sizeは文字の高さ（mm）"""
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
    """モデル（m）→ 紙（mm）。ox,oy＝紙の上の(x0,y0)の位置"""
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

# ---------------------------------------------------------------- 園庭（園庭のチャットのdata/garden.jsonを読むだけ）
import sys
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import garden_common as gc
GJ = gc.G


def _gs(geom):
    """3dmのxy（m）の形 → 紙の座標（to_s）"""
    from shapely.ops import transform as _tf
    return _tf(lambda x, y, z=None: tuple(to_s(np.c_[np.atleast_1d(x), np.atleast_1d(y)]).T), geom)


def _ad_poly(pts):
    return Polygon(gc.XS([tuple(p) for p in pts])).buffer(0)


def _ad_ell(c, ra, rd, rot=0.0, n=48):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ca, sa = np.cos(np.radians(rot)), np.sin(np.radians(rot))
    a = c[0] + ra * np.cos(t) * ca - rd * np.sin(t) * sa
    d = c[1] + ra * np.cos(t) * sa + rd * np.sin(t) * ca
    return _ad_poly(np.c_[a, d])


GARDEN_X = gc.garden_poly()                                   # 3dmのxy（m）
_bank = [tuple(p) for p in GJ["BANK"]["line"]]
_shz = Polygon(gc.XS(_bank + [(56.0, 18.2), (56.0, 37.0), (53.6, 36.0)]
                     + [(a, gc.d_edge(a)) for a in np.linspace(53.4, 40.6, 20)])).buffer(0).intersection(GARDEN_X)
_mo = GJ["MOUND"]
_t = np.linspace(0, 2 * np.pi, 64, endpoint=False)
_mound = _ad_poly(np.c_[_mo["top"][0] + np.cos(_t) * np.where(np.cos(_t) > 0, _mo["r_se"], _mo["r_nw"]),
                        _mo["top"][1] + np.sin(_t) * np.where(np.sin(_t) > 0, _mo["r_sw"], _mo["r_ne"])])
_hut = GJ["HUT"]
GD = dict(
    garden=_gs(GARDEN_X),
    shizu=_gs(_shz),
    mound=_gs(_mound),
    stream=_gs(LineString(gc.XS([tuple(p) for p in GJ["STREAM"]["line"]]))),
    culvert=_gs(LineString(gc.XS([tuple(p) for p in GJ["STREAM"]["culvert"]]))),
    fountain=_gs(_ad_ell(GJ["FOUNTAIN"]["c"], GJ["FOUNTAIN"]["r"][0], GJ["FOUNTAIN"]["r"][1], GJ["FOUNTAIN"].get("rot", 0))),
    willow=_gs(_ad_ell(GJ["WILLOW"]["c"], GJ["WILLOW"]["r"], GJ["WILLOW"]["r"])),
    bowl=_gs(_ad_ell(GJ["BOWL"]["c"], GJ["BOWL"]["r"], GJ["BOWL"]["r"])),
    hut=_gs(_ad_poly([(_hut["a"][0], _hut["d"][0]), (_hut["closed_a"], _hut["d"][0]),
                      (_hut["closed_a"], _hut["d"][1]), (_hut["a"][0], _hut["d"][1])])),
    compost=_gs(_ad_poly([(_hut["closed_a"], _hut["d"][0]), (_hut["a"][1], _hut["d"][0]),
                          (_hut["a"][1], _hut["d"][1]), (_hut["closed_a"], _hut["d"][1])])),
    sand=_gs(_ad_poly(GJ["SAND"]["poly"])),
    trees=[_gs(_ad_ell((t[0], t[1]), t[3] * 0.55, t[3] * 0.55, n=16)) for t in GJ["TREES"]],
    amaochi=_gs(LineString([gc.UV(u, GJ["EDGE_V"]) for u in np.linspace(0.0, 57.0, 40)])),
)
GD["north"] = GD["garden"].difference(GD["shizu"].buffer(0.5))   # だいさんかく（しずかのもりを除く）
_hc = np.array(GD["hut"].centroid.coords[0])
print("園庭（m²）", round(GD["garden"].area), " しずかのもり", round(GD["shizu"].area))


def draw_garden(ax, xf, hi=(), thin=False):
    """園庭を描く（紙の座標）。hi＝強調する場所：north/shizu/mound/fountain/hut/compost"""
    def on(k):
        return k in hi
    base = "#E9F0DF" if hi else "#DDE9CF"
    draw_shape(ax, GD["garden"], xf, fc=base, ec="#9DB08A", lw=0.15, z=0.6)
    draw_shape(ax, GD["north"], xf, fc="#B9D99A" if on("north") else base, ec="none", z=0.7)
    draw_shape(ax, GD["shizu"], xf, fc="#C9DDB8" if on("shizu") else ("#E2EAD8" if hi else "#D3E2C6"), ec="none", z=0.7)
    draw_shape(ax, GD["mound"], xf, fc="#A6CC85" if on("north") or on("mound") else "#CFE0BC", ec="#8FA77A", lw=0.12, z=0.8)
    if not thin:
        for tg in GD["trees"]:
            draw_shape(ax, tg, xf, fc="#C3D7AE", ec="#A3B98E", lw=0.08, z=0.85)
    draw_shape(ax, GD["sand"], xf, fc="#EFE2B8", ec="none", z=0.9)
    draw_shape(ax, GD["bowl"], xf, fc="#D6E4C6", ec="#9DB08A", lw=0.1, z=0.9)
    draw_shape(ax, GD["willow"], xf, fc="#9EC07E", ec="none", z=0.9)
    draw_shape(ax, GD["fountain"], xf, fc="#9ECBE6" if on("fountain") else "#CFE3EF", ec="none", z=0.9)
    draw_shape(ax, GD["culvert"], xf, ec="#6FA8D0", lw=0.25, z=0.95, ls=(0, (2, 1.5)))
    draw_shape(ax, GD["stream"], xf, ec="#3E8CC4", lw=0.9 if thin else 1.2, z=0.95)
    draw_shape(ax, GD["amaochi"], xf, ec="#8FB8D6", lw=0.3, z=0.95, ls=(0, (1, 1)))
    draw_shape(ax, GD["hut"], xf, fc="#8A7A66" if on("hut") else "#B9AE9F", ec="none", z=0.97)
    draw_shape(ax, GD["compost"], xf, fc="#7A5230" if on("compost") else "#CDBFAA", ec="none", z=0.97)

# 面積（1階の部屋の床）
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
    """1階平面（3dmから）。窓(wbox,hbox)は紙のmm。keyhi＝強調する層の頭"""
    xf = xform(ox, oy, scale, x0, y0)
    rp = clip_rect(ax, ox, oy, wbox, hbox)
    start = len(ax.patches)
    lstart = len(ax.lines)
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
    for a in ax.lines[lstart:]:
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

embeds = {i: [] for i in range(1, 6)}   # (src_pdf, page, clip_mm(x0,y0,x1,y1)|None, dest_mm(x,y,w,h)下原点, keep_ratio)
SEC = os.path.join(ROOT, "model", "drawings", "sodachiya_sections_1-100.pdf")
CLIP_A = (25, 38, 841, 201)
CLIP_B = (25, 244, 410, 377)
CLIP_C = (430, 244, 812, 377)


def embed(sheet, src, clip, x, y, scale_factor=1.0, pageno=0, fit=None):
    """clip（元のPDFのmm、上原点）を、紙の(x,y)（下原点、左下）に倍率scale_factorで置く。
    fit=(w,h)を渡すと、その枠に縮めて入れる。戻り値は置いた大きさ（mm）"""
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
frame(ax, 1, "敷地と園庭", "この案が敷地から生まれたこと（比叡・高野川・扇状地・西の細い道）と、主題の舞台としての園庭",
      "模型写真（入口の一枚）→ タイトルと趣旨の冒頭 → 配置図と園庭 → 園庭の筋 → 立地と応答")
top = H - M - 16
T(ax, M + 6, top - 15, "地に足をつけて育つ", 10.0, bold=True)
# 設計趣旨はpresent/設計趣旨.txt（ユーザーが編集する）。改行は無視してつなぐ
# 設計趣旨は present/設計趣旨.txt（ユーザーが編集する）。「#」の行は読まない。空行で段落を分け、段落の中の改行はつなぐ
_paras, _cur = [], []
for _l in open(os.path.join(HERE, "設計趣旨.txt"), encoding="utf-8").read().splitlines():
    _l = _l.strip()
    if _l.startswith("#"):
        continue
    if not _l:
        if _cur:
            _paras.append("".join(_cur)); _cur = []
        continue
    _cur.append(_l)
if _cur:
    _paras.append("".join(_cur))
concept = "".join(_paras)
import textwrap
def jwrap(t, width=40.0):
    """全角1・半角0.5で数えて折り返す。句読点は行頭に置かない（ぶら下げ）"""
    out, cur, n = [], "", 0.0
    for ch_ in t:
        w_ = 0.5 if ord(ch_) < 0x2000 else 1.0
        if n + w_ > width and ch_ not in "。、）」":
            out.append(cur); cur, n = "", 0.0
            if ch_ == " ":
                continue
        cur += ch_; n += w_
    return out + ([cur] if cur else [])


_y = top - 28
for _p in _paras:
    for s in jwrap("　" + _p, 40):     # 段落の頭は全角1字下げ
        T(ax, M + 6, _y, s, 3.6)
        _y -= 6.0
    _y -= 2.0                         # 段落のあいだ
dimnote(ax, M + 6, _y + 1, f"設計趣旨 約{len(concept.replace(' ', ''))}字（課題は300字程度）。文字3.6 mmなら1 m離れて読める")
# 立地と応答（趣旨の右、2×2）
rx = M + 6 + 250
title(ax, rx, top - 12, "立地と応答")
cw, ch = 120, 80
for i, (h1, s1) in enumerate([
        ("比叡（東から24°）", "冷気→本館は東向き\n越屋根で夏の夜に冷やす"),
        ("高野川と崖4〜5 m", "川へ下がる屋根・植栽帯\n浸水1.5 m→大学へ避難"),
        ("扇状地と用水", "用水を借りた小川と築山\n＝園内の高野川と比叡"),
        ("西の細い道と住宅", "西館の屋根を西で低く\n車は突き出た木より南で")]):
    cx = rx + (i % 2) * (cw + 6)
    cy = top - 18 - ch - (i // 2) * (ch + 5)
    box(ax, cx, cy, cw, ch, h1, "小さな図＋\n" + s1, fill="#FAF8FF")

# 配置図1/200（高野川の辺を下に水平：川向こうから見る向き、ユーザー。園庭の図と同じ回し方）
from shapely import affinity
_Ms = np.array([d, wv])                                # to_sの回転の部分（3dmのxy → 紙の座標）
assert np.linalg.det(_Ms) > 0
_phi = np.degrees(np.arctan2(_Ms[1, 0], _Ms[0, 0]))
ROT = GJ["VIEW_ROT"]["deg"] - _phi                    # 3dmから見てVIEW_ROT（園庭の図と同じ）
rot = lambda g: affinity.rotate(g, ROT, origin=(0, 0)) if g is not None else None
_site = max([o for o in L("00_") if o["kind"] == "curve"], key=lambda o: len(o["V"]))
_S = to_s(_site["V"])
_Q = np.array(rot(Polygon(_S)).exterior.coords)
QX0, QY0 = _Q.min(0)
QX1, QY1 = _Q.max(0)
sx, sy = M + 6, M + 8
pad = 2.0
sw, sh = (QX1 - QX0 + 2 * pad) * 5, 322
title(ax, sx, sy + sh + 4, "配置図", "1/200　高野川を下に（川向こうから見る向き、北は右上）")
xf = xform(sx, sy, 200, QX0 - pad, QY0 - pad)
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
draw_shape(ax, rot(roofs_plan), xf, fc="#E9E6E0", ec="#8A847A", lw=0.3, z=5)   # 園庭の図と同じ色
for a_ in ax.patches[st:] + ax.lines[stl:]:
    a_.set_clip_path(rp)
# 園庭は園庭のチャットの図（out/sodachiya_garden_01.pdfの配置1/200）をそのまま重ねる（同じ縮尺・同じ向き）
_GR = affinity.rotate(GARDEN_X, GJ["VIEW_ROT"]["deg"], origin=(0, 0)).bounds
GVX0, GVY0, GVX1, GVY1 = _GR[0] - 6.0, _GR[1] - 6.0, _GR[2] + 3.0, _GR[3] + 3.0
_p0 = to_s(np.array([[0.0, 0.0]]))[0]
_rr = np.radians(ROT)
_t0 = np.array([_p0[0] * np.cos(_rr) - _p0[1] * np.sin(_rr), _p0[0] * np.sin(_rr) + _p0[1] * np.cos(_rr)])   # 3dmの原点 → 回した紙の座標
_ll = xf(np.array([[GVX0 + _t0[0], GVY0 + _t0[1]]]))[0]                   # 園庭の図の左下（紙）
_gw, _gh = (GVX1 - GVX0) * 5, (GVY1 - GVY0) * 5
_x0c, _y0c = max(_ll[0], sx), max(_ll[1], sy)                              # 配置図の枠で切る
_x1c, _y1c = min(_ll[0] + _gw, sx + sw), min(_ll[1] + _gh, sy + sh)
GCLIP = (14 + (_x0c - _ll[0]), 40 + (_ll[1] + _gh - _y1c), 14 + (_x1c - _ll[0]), 40 + (_ll[1] + _gh - _y0c))
embed(1, os.path.join(ROOT, "out", "sodachiya_garden_01.pdf"), GCLIP, _x0c, _y0c, 1.0)
ax.add_patch(Rectangle((_x0c, _y0c), _x1c - _x0c, _y1c - _y0c, fill=False, ec=NOTE, lw=0.3, ls=(0, (2, 2)), zorder=30))
dimnote(ax, sx + 175, sy + sh + 4, "点線の枠＝園庭のチャットの配置1/200（garden01）を実寸で重ねた。本番は一枚に描き直す")
_nv = north_s / np.linalg.norm(north_s)
_r = np.radians(ROT)
_nv = np.array([_nv[0] * np.cos(_r) - _nv[1] * np.sin(_r), _nv[0] * np.sin(_r) + _nv[1] * np.cos(_r)])
_nx, _ny = sx + 14, sy + sh - 20
ax.annotate("", xy=(_nx + _nv[0] * 12, _ny + _nv[1] * 12), xytext=(_nx, _ny), arrowprops=dict(arrowstyle="-|>", lw=0.6, color=INK))
T(ax, _nx + _nv[0] * 16, _ny + _nv[1] * 16, "N", 3.2, ha="center", va="center", bold=True)
scalebar(ax, sx + 6, sy + 6, 200, 20)
print(f"配置図：回転{ROT:.1f}°（3dmから{GJ['VIEW_ROT']['deg']}°）、敷地{QX1-QX0:.1f}×{QY1-QY0:.1f} m、枠{sw:.0f}×{sh} mm")

# 園庭の筋（配置図の右、上から下へ）
gx = sx + sw + 6
gwid = W - M - 6 - 297 - 8 - gx
title(ax, gx, sy + sh + 4, "園庭　本物に触れて遊ぶ")
gcells = [
    ("見立て　築山＝比叡、小川＝高野川", "ホールから頂の向こうに比叡\n足もとを掘った土で盛る\n遊具を置かず、地形と木で遊ぶ"),
    ("水の行方を隠さない", "用水→みなもと→小川→護岸の溝→高野川\n雨は樋なしで屋根から落ち、雨の川へ\n溢れたらすりばちが雨の池に"),
    ("土と世代のめぐり", "キッチンの野菜くず→コンポスト（4・5歳の当番）\n→入口前の菜園→給食、余りは農家へ\n柳の家は上の子が小さい子のために編む"),
    ("静かな場所と先生の目", "南のしずかのもり（寝ている0〜2歳の前）\nニッチ11か所、死角は植え込みだけ\n取り除くのは命に関わる危険だけ"),
]
gch = (sh - 3 * 5) / 4
for i, (h1, s1) in enumerate(gcells):
    cy = sy + sh - (i + 1) * gch - i * 5
    box(ax, gx, cy, gwid, gch, h1, "小さな図＋\n" + s1, fill="#F5FAF0", color="#4E8A3A")
# 右の列：模型写真2枚
px = W - M - 6 - 297
box(ax, px, top - 8 - 210, 297, 210, "模型写真　A4（入口の一枚）",
    "園庭からこどもの目線（模型で約10 mm）\n縁側・深い庇・築山の向こうに比叡の方向\n選抜で最初に目に入る位置")
box(ax, px, M + 8, 297, 300, "模型写真　鳥瞰", "敷地と高野川・崖・公園・西の道・園庭\n配置図と同じ向き（高野川を手前）にそろえる")
figs.append(fig)

# ================================================================ 2　こどもの一日（1階平面）
fig, ax = page()
frame(ax, 2, "こどもの一日　1階平面", "こどもが一日を過ごす場所としての平面（家具・午睡・靴の線・歳とともに延びる道）",
      "部屋の色 → 海峡とホール・キッチン → 縁側 → 家具 → 一日の帯（部屋と園庭）")
pw, ph = W - 2 * M - 12, 392
px, py = M + 6, H - M - 16 - 12 - ph
title(ax, px, py + ph + 3, "1階平面図", "1/100　道路・隣地境界線・家具。北が右、園庭が下（縁側の前の園庭まで）")
x0p = BX0 - 1.5
y0p = BY0 - 6.0
_rp2 = clip_rect(ax, px, py, pw, ph)
_st2, _sl2 = len(ax.patches), len(ax.lines)
draw_garden(ax, xform(px, py, 100, x0p, y0p))
for a_ in ax.patches[_st2:] + ax.lines[_sl2:]:
    a_.set_clip_path(_rp2)
draw_plan(ax, px, py, 100, x0p, y0p, pw, ph)
north(ax, px + pw - 18, py + 16)
scalebar(ax, px + 4, py + 4, 100, 10)
dimnote(ax, px + 70, py + 4, f"建物（庇・おむすび・みなみのさんかくまで）{info['building'][0]}×{info['building'][1]} m → 1/100で{info['building'][0]*10:.0f}×{info['building'][1]*10:.0f} mm。"
        f"窓{pw:.0f}×{ph} mmに入る。西の道路の幅は3dmに無いので描き足す")
title(ax, px, py - 9, "こどもの一日　園庭と部屋を行き来して", "食べる・遊ぶ・寝る・当番")


def lcen(prefixes):
    gs = [g for ln, k, g in plan_items if ln.startswith(tuple(prefixes)) and k == "mesh"]
    return np.array(unary_union(gs).centroid.coords[0])


_kit = lcen(["32_"])
_hall = lcen(["59_1F_ホール"])
_edge_y = GD["amaochi"].bounds[3] + 0.8                     # 縁側の外の線のあたり
_path = np.array([_kit, [_kit[0], _hall[1]], [_hall[0], _hall[1]], [_hall[0], _edge_y], [_hc[0], _edge_y], _hc])
frames_ = [
    ("登園8:00", ["52_", "15_", "59_1F_ホール", "33_", "59_1F_事務（スパン"], (), None,
     "公園→木戸→小径→海峡／0・1歳は受け取り土間"),
    ("外で遊ぶ9:30", ["31_", "13_", "14_", "62_"], ("north", "shizu", "fountain"), None,
     "3〜5歳はだいさんかく（築山・小川・もり、夏は床の噴水）\n0〜2歳はしずかのもり／雨の日は遊戯室"),
    ("食べる11:30", ["32_", "34_", "33_", "59_1F_3歳", "59_1F_4歳", "59_1F_5歳"], (), None,
     "キッチンから海峡を通って配膳\n縁側から見える台所"),
    ("寝る12:45", ["53_", "54_", "59_1F_3歳", "59_1F_4歳"], ("mound",), None,
     "ねどこ・ロフトの下／南のしずかのもりは静かに\n起きている5歳は北の築山・遊戯室で"),
    ("当番15:00", ["32_", "33_", "59_1F_ホール"], ("hut", "compost"), _path,
     "4・5歳のコンポスト当番：キッチンの野菜くず→小屋\nできた土は入口前の菜園へ（余りは農家へ）"),
    ("降園16:30", ["34_", "52_", "15_"], ("north",), None,
     "はれのまで延長保育／縁台でお茶\n迎えを待つあいだ夕方の園庭"),
]
nf = len(frames_)
fw = (pw - (nf - 1) * 5) / nf
fy = M + 7
fh = py - 14 - fy
kx0, kx1 = BX0 - 1.5, BX1 + 0.5
ky0, ky1 = GD["garden"].bounds[1] - 1.0, BY1 + 0.5
ksc = next(s_ for s_ in (500, 600, 700, 800, 1000)
           if (kx1 - kx0) * 1000 / s_ <= fw - 6 and (ky1 - ky0) * 1000 / s_ <= fh - 26)
for i, (h1, keys, ghi, path, s1) in enumerate(frames_):
    fx = px + i * (fw + 5)
    ax.add_patch(Rectangle((fx, fy), fw, fh, fc="none", ec="#BBBBBB", lw=0.3))
    T(ax, fx + 3, fy + fh - 7, h1, 3.4, bold=True)
    kw_, kh_ = (kx1 - kx0) * 1000 / ksc, (ky1 - ky0) * 1000 / ksc
    kox, koy = fx + (fw - kw_) / 2, fy + 13
    kxf = xform(kox, koy, ksc, kx0, ky0)
    draw_garden(ax, kxf, hi=ghi, thin=True)
    draw_plan(ax, kox, koy, ksc, kx0, ky0, kw_, kh_, keyhi=keys, thin=True)
    if path is not None:
        q = kxf(path)
        ax.plot(q[:, 0], q[:, 1], color="#B5651D", lw=0.9, ls=(0, (2, 1.2)), zorder=8)
        ax.annotate("", xy=tuple(q[-1]), xytext=tuple(q[-2]), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="#B5651D"), zorder=8)
    for j, line_ in enumerate(s1.split("\n")):
        T(ax, fx + 3, fy + 7.5 - j * 4.2, line_, 2.6)
dimnote(ax, px + pw - 330, py - 9, f"一日の帯は1/{ksc}の小さな配置（建物＋園庭、3dmとgarden.jsonから自動）。北が右・園庭が下")
figs.append(fig)

# ================================================================ 3　長手の帯（立面・縦断）
fig, ax = page()
frame(ax, 3, "どう見えるか　立面と縦断", "57 mの縁側と深い庇のリズム（東）、街に対して低い構え（西）",
      "東立面（平面の真下、柱がそろう）→ 縦断 → 西立面")
ex, ew = M + 6, W - 2 * M - 12
x0e = x0p
y = H - M - 16 - 14 - 100
title(ax, ex, y + 104, "東立面図（園庭側）", "1/100　1階平面と同じ横位置")
draw_elev(ax, "east", ex, y, 100, x0e, ew, 100)
dimnote(ax, ex + ew - 250, y + 104, "2枚目の真下に貼ると、平面と柱の位置が縦にそろう")
y2 = y - 12 - 163
title(ax, ex, y2 + 166, "縦断面図A", "1/100　保育室の中ほどr=197 mで切って展開、西を見る")
embed(3, SEC, CLIP_A, ex, y2, 1.0)
dimnote(ax, ex + ew - 250, y2 + 166, "自動の断面Aをそのまま実寸で（model/drawings）")
y3 = M + 10
title(ax, ex, y3 + 108, "西立面図（道路側）", "1/100　北が左")
draw_elev(ax, "west", ex, y3, 100, -(BX1 + 1.5), ew, 104)
dimnote(ax, ex + ew - 330, y3 + 108, "道の向かいの住宅の高さを点線で描き足す（圧迫感の説明）")
gh = y2 - 4 - (y3 + 116)
gw = gh * 297 / 210
bx_ = ex + ew - 2 * gw - 10
for i, (h1, s1) in enumerate([("模型写真　西の道から", "人の目の高さ1.5 m（模型15 mm）\n低い軒と縦格子"),
                               ("模型写真　公園の木戸から", "アプローチの入口\n見送りの小径の奥にひろば")]):
    box(ax, bx_ + i * (gw + 10), y3 + 116, gw, gh, h1, s1)
figs.append(fig)

# ================================================================ 4　どう息をするか
fig, ax = page()
frame(ax, 4, "どう息をするか　断面と環境", "空気・光・熱の流れが形の理由になっていること（断面Cを主役に）",
      "断面C 1/50 → ①〜⑨ と環境の枠 → 運転表 → 断面B → 2階")
CLIP_C2 = (455, 256, 800, 380)
hC = (CLIP_C2[3] - CLIP_C2[1]) * 2
cx, cy = M + 6, H - M - 16 - 12 - hC
title(ax, cx, cy + hC + 3, "断面図C　4歳・遊戯室", "1/50（1/100の自動の図を2倍）　西の道路から園庭へ")
wC, _ = embed(4, SEC, CLIP_C2, cx, cy, 2.0)
dimnote(ax, cx + 380, cy + hC + 3, "左右に 道・向かいの住宅／園庭・築山 を描き足す。空気の矢印と①〜⑨を重ねる。断熱は帯で")
ex_ = cx + wC + 8
box(ax, ex_, cy, W - M - 6 - ex_, hC, "環境の枠", "LEED v5\nGold相当\n\n脱炭素 ①〜⑤\n生活の質 ⑥⑦\n生態系 ⑧⑨", fill="#FAF8FF")
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
title(ax, cx, by + 136 + 4, "断面図B　海峡", "1/100　南の入口・キッチン・2階・すき間・本館・縁側")
wB, hB = embed(4, SEC, CLIP_B, cx, by, 1.0)
f2x = W - M - 6 - w2
title(ax, f2x, by + h2 + 3, "2階平面図（西館）", "1/100")
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
dimnote(ax, f2x, by - 6, f"西館{w2/10:.0f}×{h2/10:.0f} m → {w2:.0f}×{h2:.0f} mm（1階平面と同じ向き）")
figs.append(fig)

# ================================================================ 5　暮らしと構造
fig, ax = page()
frame(ax, 5, "暮らしと構造", "近づいて読む人のための細部：寝る・遊ぶ・組み方・変わり方",
      "内観 → 同じ部屋の一日 → 遊戯室 → 接合部 → S&I → 面積表 → inspired by")
top = H - M - 16 - 8
box(ax, M + 6, top - 210, 297, 210, "内観　ホール（A4）", "海峡と飛び石・オープンキッチン\n梁の見える天井・越屋根の光の線\n（レンダリングか模型写真）")
x1 = M + 6 + 297 + 12
title(ax, x1, top - 4, "同じ部屋の一日", "3〜5歳の保育室　断面1/100")
SEC35 = os.path.join(ROOT, "out", "sodachiya_35_section.pdf")
CL35 = (30, 70, 360, 215)
for i, t_ in enumerate([("10:00", "遊ぶ"), ("11:30", "食べる"), ("13:30", "寝る")]):
    yy = top - 12 - (i + 1) * 74
    embed(5, SEC35, CL35, x1 + 22, yy, 0.5)
    T(ax, x1, yy + 40, t_[0], 3.0, bold=True)
    T(ax, x1, yy + 34, t_[1], 2.8)
dimnote(ax, x1, top - 12 - 3 * 74 - 6, "今は同じ図（既存の1/50を縮小）。時刻ごとに家具・人・光を描き分ける")
x2 = x1 + 200
title(ax, x2, top - 4, "遊戯室", "平面・断面（縮小、遊戯室のチャット）")
PLAY = os.path.join(ROOT, "out", "sodachiya_play_01.pdf")
embed(5, PLAY, (0, 10, 297, 390), x2, top - 12 - 232, fit=(W - M - 6 - x2, 230))
by = M + 10
title(ax, M + 6, by + 228, "接合部", "タメディア型　2枚の梁で柱を挟む（縮小）")
JD = os.path.join(ROOT, "out", "joint_detail.pdf")
embed(5, JD, None, M + 6, by + 30, fit=(255, 190))
T(ax, M + 6, by + 18, "京都の間伐材・金物を減らした接合", 3.4, bold=True)
x3 = M + 6 + 265
box(ax, x3, by, 200, 232, "スケルトン＆インフィル", "3 mスパンの骨格（固定）と\n間仕切り・家具（可変）を色分け\n\n今 ／ 定員が変わる ／\n学童・地域の場 の3コマ")
GPDF = os.path.join(ROOT, "out", "sodachiya_garden_01.pdf")
x4 = x3 + 210
title(ax, x4, by + 228, "園庭の断面", "縮小（園庭のチャット）")
embed(5, GPDF, (0, 388, 420, 575), x4, by + 100, fit=(200, 122))
T(ax, x4, by + 90, "築山・小川・水遊び場は遊ぶの答え", 3.0, bold=True)
REQ = [("乳児室（0・1歳）", "53_", "約60×2"), ("保育室（2歳）", "54_", "約60"),
       ("保育室（3歳）", "59_1F_3歳", "約60"), ("保育室（4歳）", "59_1F_4歳", "約60"), ("保育室（5歳）", "59_1F_5歳", "約60"),
       ("遊戯室", "31_", "240以上"), ("調理室", "32_", "約60"), ("医務室", "59_1F_医務", "約30"),
       ("事務室", "59_1F_事務", "約60"), ("休憩・会議（2階）", "4", "60＋30"), ("はれのま", "34_", "（追加）")]
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
for j, s in enumerate(["3dmの床から自動で測った仮の値。", "医務・事務の不足を確かめる。", "園庭350・駐車5・延床2,000・",
                       "倉庫30・機械室30を本番で足す"]):
    T(ax, tx, by + 210 - len(REQ) * 7.0 - 2 - j * 5, s, 2.4, NOTE)
# inspired by（小さく、面積表の下）
INSP = [("Asilo Nido Iride", "Mario Cucinella Architects・Guastalla・2015", "梁の列が並ぶ長細い本館と、外に付く付属の建物"),
        ("Tamedia", "坂茂・Zürich・2013", "梁の端の楕円の頭と、それを貫く楕円の桁"),
        ("レイモンド斑鳩こども園", "キノアーキテクツ・斑鳩・2026", "室内に木を立てる（ホールの北山杉）"),
        ("KAIT工房", "石上純也・厚木・2008", "柱の配列：見る向きで景色が変わる並び"),
        ("認定こども園らみどり", "はりゅうウッドスタジオ・須賀川・2026", "内と外の二重の縁側、遊具を置かない地形の園庭"),
        ("仙田満の園舎", "環境デザイン研究所", "摺鉢のネット、キャットウォーク、ニッチ"),
        ("Waldorf School of the Peninsula", "California", "遊戯室の切り株")]


def _tw(t, size):
    return sum(size / 0.72 * (0.6 if ord(c) < 0x2000 else 1.0) for c in t)


iy = by + 100
T(ax, tx, iy, "inspired by", 3.4, bold=True)
for i, (n, src, what) in enumerate(INSP):
    yy = iy - 8 - i * 13.0
    T(ax, tx, yy, n, 2.6, bold=True)
    T(ax, tx + _tw(n, 2.6) + 2, yy, src, 2.1, "#666666")
    T(ax, tx + 2, yy - 4.6, "→ " + what, 2.3)
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

# 壁に貼ったときの全体（3枚＋2枚）
pix = []
for i in range(5):
    p = doc[i].get_pixmap(dpi=60)
    fn = os.path.join(OUT, f"sheet{i+1}.png")
    p.save(fn)
    pix.append(plt.imread(fn))
fig = plt.figure(figsize=(841 / 25.4, 594 / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
SC = 594 / 2500                       # 壁のmm → 紙のmm
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
def TW(x, y, s, size, **kw):  # sizeは紙のmm
    T(ax, x, y, s, size, **kw)
TW(110, 1515, "目の高さ1.5 m", 3.2, color=NOTE)
TW(110, 20, "床", 3.2)
TW(x0w, 2400, "壁に貼ったとき　左：1〜3を縦につなぐ（高さ約1.8 m）　右：4・5を縦につなぐ", 6.0, bold=True)
notes = ["左の列は 配置1/200 → 1階平面1/100 → 立面・縦断1/100。",
         "2・3は北が右・園庭が下で柱が縦にそろう。1の配置は高野川が下（北は右上）。",
         "目の高さに来るのは1階平面（最も細かい図）と断面C。",
         "右の列は下端が約0.6 m。暮らしと構造は近づいて読む。",
         "製図台に置くなら2＋2＋1（1・2／3・4／5）に切り分ける。"]
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
