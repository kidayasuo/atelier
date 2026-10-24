"""育ち舎　提出A1×5枚の仮の割付（プレゼンの準備のチャット）

実寸の確認が目的：3dm（sodachiya_exact_mesh.3dm）から平面・配置・立面の外形を
その縮尺のまま描き、自動の断面（drawings/）や他のチャットの図（out/）を
実寸または縮小で貼り込む。未作成のものは破線の枠（大きさは実寸）で示す。
紫の文字は割付の注記（本番では消す）。

python sodachiya/present/mock.py  →  sodachiya/presentation.pdf（5枚）／ present/out/ の全体の画像
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
        prof, prof_closed = None, True
        for s in (0.0, 1.0):
            c = g.Profile3d(0, s)
            if c is not None:
                if isinstance(c, r.NurbsCurve) and c.Degree == 1:
                    pts = [(c.Points[i].X, c.Points[i].Y, c.Points[i].Z) for i in range(len(c.Points))]
                else:
                    pts = curve_pts(c, 64)
                P += pts
                if prof is None:
                    prof = np.array(pts) / 1000
                    prof_closed = c.IsClosed
        if P:
            # 平面は押し出しの断面（下の輪郭）そのもので描く。凸包にすると折れた塀などが大きな三角になる
            objs.append(dict(layer=ln, kind="solid", V=np.array(P) / 1000, prof=prof, prof_closed=prof_closed))
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
    if o["kind"] == "solid" and mode == "plan" and o.get("prof") is not None:
        if not o.get("prof_closed"):             # 開いた線の押し出し＝塀・格子などの面。平面では線
            return LineString(to_s(o["prof"])) if len(o["prof"]) > 1 else None
        if len(o["prof"]) >= 3:
            pg = Polygon(to_s(o["prof"])).buffer(0)
            if pg.area > 1e-5:
                return pg
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
            if len(gg.interiors) == 0:
                xy = xf(np.array(gg.exterior.coords))
                ax.add_patch(MPoly(xy, closed=True, fc=fc, ec=ec, lw=lw, zorder=z, ls=ls))
            else:                                   # 穴のある形（ひと続きにした外壁など）は穴を抜いて描く
                from matplotlib.path import Path as MPath
                from matplotlib.patches import PathPatch
                verts, codes = [], []
                for ring in [gg.exterior] + list(gg.interiors):
                    xy = xf(np.array(ring.coords))
                    verts += list(map(tuple, xy))
                    codes += [MPath.MOVETO] + [MPath.LINETO] * (len(xy) - 2) + [MPath.CLOSEPOLY]
                ax.add_patch(PathPatch(MPath(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z, ls=ls))
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
SEC = os.path.join(ROOT, "drawings", "sodachiya_sections_1-100.pdf")
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
frame(ax, 1, "敷地と自然環境", "周囲の自然環境との関係（用水・比叡と高野川のうつし・河川敷）と地域への配慮、屋外遊戯場としての園庭",
      "模型写真（入口の一枚）→ タイトルと趣旨 → 配置図と園庭 → 園庭の筋 → 自然環境と地域")
top = H - M - 16
T(ax, M + 6, top - 15, "地に足をつけて育つ", 10.0, bold=True)
# 設計趣旨はpresent/設計趣旨.txt（ユーザーが編集する）。改行は無視してつなぐ
# 設計趣旨は sodachiya/concept.txt（ユーザーが編集する、10-24に直下へ）。「#」の行は読まない。空行で段落を分け、段落の中の改行はつなぐ
_paras, _cur = [], []
for _l in open(os.path.join(ROOT, "concept.txt"), encoding="utf-8").read().splitlines():
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
# 自然環境と地域（趣旨の右、2×2）
rx = M + 6 + 250
title(ax, rx, top - 12, "自然環境と地域")
cw, ch = 120, 80
for i, (h1, s1) in enumerate([
        ("借りぐらし　水と木を借りる", "松ヶ崎の用水のネットワークから水を借りる\n（小さな地図1/2500）\n京都北山から北山杉の間伐材を借りる\n（ホールの林）。地下水の豊かな土地（物語）"),
        ("山から川へ", "北のもりのみなもとから縁側の前・原っぱ\nを流れ、護岸の溝を滑り落ちて高野川へ\n築山＝比叡、小川＝高野川のうつし"),
        ("河川敷とつなぐ", "のぞき（生垣の口から水面）\n小川と雨の川が護岸の溝で河川敷へ\n避難の帯・非常用の門から公園・河川敷へ"),
        ("地域への配慮", "車は突き出た木より南（川側）で出入り\n西館の西端は1階の高さ（向かいの住宅）\n北東の隣家：1 m・木の帯・小屋が声の衝立\n小竹薮公園を残す")]):
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
T(ax, sx + 6, sy + 16, "災害時は地下水をくみ上げて、近隣に水を届ける", 2.8)
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
# 右の列：模型写真（A4）・園庭の断面・鳥瞰
px = W - M - 6 - 297
box(ax, px, top - 8 - 210, 297, 210, "模型写真　A4（入口の一枚）",
    "園庭からこどもの目線（模型で約10 mm）\n縁側・深い庇・築山の向こうに比叡の方向\n選抜で最初に目に入る位置")
_gy = top - 8 - 210 - 10
title(ax, px, _gy, "園庭の断面", "1/200　A 比叡へ／B 高野川・河川敷へ")
wG, hG = embed(1, os.path.join(ROOT, "out", "sodachiya_garden_01.pdf"), (0, 313, 420, 522), px, _gy - 4 - 105, 0.5)
box(ax, px, M + 8, 297, _gy - 4 - 105 - 6 - (M + 8), "模型写真　鳥瞰", "敷地と高野川・崖・公園・西の道・園庭\n配置図と同じ向き（高野川を手前）にそろえる")
figs.append(fig)

# ================================================================ 2　すべての人の一日（1階平面）
# 課題の「食べる・寝る・遊ぶ」に答える。こどもだけでなく保育士・調理の職員の一日も重ねる（ユーザー、10-24）
DRW = os.path.join(ROOT, "drawings")   # 図のPDFは sodachiya/drawings/（10-24）
PLAN = os.path.join(DRW, "sodachiya_plan_1-100.pdf")
ELE1 = os.path.join(DRW, "sodachiya_elevations_1-100.pdf")
ELE2 = os.path.join(DRW, "sodachiya_elevations2_1-100.pdf")
fig, ax = page()
frame(ax, 2, "すべての人の一日　1階平面", "こども・保育士・調理の職員が一日を過ごす場所としての平面（食べる・寝る・遊ぶ）",
      "1階平面（家具・先生の席）→ 一日の帯（こども／保育士／調理）")
CLIP_P1 = (15, 189, 752, 562)              # 自動の平面図の1階の部分（1/100、図の見出しを含む）
px, top2 = M + 6, H - M - 16 - 4
wP, hP = embed(2, PLAN, CLIP_P1, px, top2 - (CLIP_P1[3] - CLIP_P1[1]), 1.0)
py = top2 - hP
dimnote(ax, px + wP + 4, top2 - 6, "3dmから自動の平面図")
dimnote(ax, px + wP + 4, top2 - 11, "（1/100、実寸）")
for j, s_ in enumerate(["描き足す注記：", "・各保育室の先生の席", "　（机h700＋ついたて）", "・0・1歳の腰掛ける机",
                        "・記録・連絡の机", "・オープンキッチンの", "　東面のガラス", "・生ごみの受け取り台",
                        "・はれのま", "・2階の休憩室は4枚目"]):
    dimnote(ax, px + wP + 4, top2 - 24 - j * 5, s_)


def lcen(prefixes):
    gs = [g for ln, k, g in plan_items if ln.startswith(tuple(prefixes)) and k == "mesh"]
    return np.array(unary_union(gs).centroid.coords[0])


_kit = lcen(["32_"])
_hall = lcen(["59_1F_ホール"])
_edge_y = GD["amaochi"].bounds[3] + 0.8
_path = np.array([_kit, [_kit[0], _hall[1]], [_hall[0], _hall[1]], [_hall[0], _edge_y], [_hc[0], _edge_y], _hc])
frames_ = [
    ("登園 8:00", ["52_", "15_", "59_1F_ホール", "33_", "59_1F_事務（スパン"], (), None,
     ["公園→木戸→小径→海峡。0・1歳は受け取り土間", "おはようの窓口で挨拶、受け取り土間で手渡し", "検収と下処理（南のガラス越しに見える）"]),
    ("外で遊ぶ 9:30", ["31_", "13_", "14_", "62_"], ("north", "shizu", "fountain"), None,
     ["3〜5歳はだいさんかく、0〜2歳はしずかのもり", "縁側の縁に腰掛けて庭全体を見る", "仕込み。今日のごはんの窓にこどもが寄る"]),
    ("食べる 11:30", ["32_", "34_", "33_", "59_1F_3歳", "59_1F_4歳", "59_1F_5歳"], (), None,
     ["保育室の食卓、はれのまでクラスごと", "配膳口から飛び石を渡って配る。いっしょに座って食べる", "オープンキッチンでこどもと目が合う"]),
    ("寝る 12:45", ["53_", "54_", "59_1F_3歳", "59_1F_4歳"], ("mound",), None,
     ["ねどこ・ロフトの下。起きている5歳は北の築山と遊戯室", "交代で2階の休憩室へ（こどもから離れる）、記録の机", "片付けと洗浄、おやつの仕込み"]),
    ("当番 15:00", ["32_", "33_", "59_1F_ホール"], ("hut", "compost"), _path,
     ["4・5歳のコンポスト当番：キッチン→小屋", "当番に付き添い、できた土を菜園へ", "受け取り台で野菜くずを渡す、はれのまでおやつ"]),
    ("降園 16:30", ["34_", "52_", "15_"], ("north",), None,
     ["はれのまで延長保育、迎えを待つ夕方の園庭", "縁台でお茶をしながら保護者と話す、2階で会議", "職員の通用口から帰る"]),
]
ROLES = [("こども", "#3E8A3A"), ("保育士", "#B5651D"), ("調理", "#4E6FB0")]
nf = len(frames_)
fw = (W - 2 * M - 12 - (nf - 1) * 5) / nf
fy = M + 7
fh = py - 6 - fy
txt_h = 3 * (3.4 + 2 * 3.3) + 2
kx0, kx1 = BX0 - 1.5, BX1 + 0.5
ky0, ky1 = GD["garden"].bounds[1] - 1.0, BY1 + 0.5
ksc = next(s_ for s_ in (500, 600, 700, 800, 1000)
           if (kx1 - kx0) * 1000 / s_ <= fw - 6 and (ky1 - ky0) * 1000 / s_ <= fh - 10 - txt_h)
for i, (h1, keys, ghi, path, lines3) in enumerate(frames_):
    fx = px + i * (fw + 5)
    ax.add_patch(Rectangle((fx, fy), fw, fh, fc="none", ec="#BBBBBB", lw=0.3))
    T(ax, fx + 3, fy + fh - 6, h1, 3.4, bold=True)
    kw_, kh_ = (kx1 - kx0) * 1000 / ksc, (ky1 - ky0) * 1000 / ksc
    kox, koy = fx + (fw - kw_) / 2, fy + txt_h + 2
    kxf = xform(kox, koy, ksc, kx0, ky0)
    draw_garden(ax, kxf, hi=ghi, thin=True)
    draw_plan(ax, kox, koy, ksc, kx0, ky0, kw_, kh_, keyhi=keys, thin=True)
    if path is not None:
        q = kxf(path)
        ax.plot(q[:, 0], q[:, 1], color="#B5651D", lw=0.9, ls=(0, (2, 1.2)), zorder=8)
        ax.annotate("", xy=tuple(q[-1]), xytext=tuple(q[-2]), arrowprops=dict(arrowstyle="-|>", lw=0.8, color="#B5651D"), zorder=8)
    yy = fy + txt_h - 1
    for (rn, rc), s_ in zip(ROLES, lines3):
        T(ax, fx + 3, yy - 3.0, rn, 2.4, rc, bold=True)
        for k_, ln_ in enumerate(jwrap(s_, (fw - 16) / (2.3 / 0.72))[:2]):
            T(ax, fx + 13, yy - 3.0 - k_ * 3.3, ln_, 2.3)
        yy -= 3.4 + 2 * 3.3
dimnote(ax, px + 230, py - 4.5, f"一日の帯：上は1/{ksc}の小さな配置（建物＋園庭）、下にこども・保育士・調理の三つの一日")
figs.append(fig)

# ================================================================ 3　景観
fig, ax = page()
frame(ax, 3, "景観", "高野川の側は低く、北の大学に向かって高く（地域の高低差の流れ）。同時に、伸びやかな梁・西館の立ち上がり・夜の水平の光で主張する",
      "園庭の側の立面 → 縦断A（川から北へ）→ 道路の側の立面 → 高野川の側・夜")
CLIP_E1 = (25, 36, 772, 153)               # 自動の立面図1：園庭の側
CLIP_E2 = (25, 199, 772, 316)              # 自動の立面図1：道路の側
CLIP_SA = (31, 50, 830, 206)               # 自動の断面図：縦断A
CLIP_E3 = (112, 36, 712, 153)              # 自動の立面図2：高野川の側
ex = M + 6
y_ = H - M - 16 - 3
title(ax, ex, y_ - 4, "園庭の側の立面図", "1/100　円弧の中心の方向から弧の真ん中に正対")
y_ -= 7
_, h_ = embed(3, ELE1, CLIP_E1, ex, y_ - (CLIP_E1[3] - CLIP_E1[1]), 1.0)
dimnote(ax, ex + 520, y_ + 3, "伸びやかな梁と縁側（梁の端・庇が3 mごとに並ぶ）。屋根は屋根材型の太陽光")
y_ -= h_ + 2
title(ax, ex, y_ - 4, "縦断面図A", "1/100　保育室の中ほどの弧で切って展開、西を見る（左が南の高野川）")
y_ -= 7
_, h_ = embed(3, SEC, CLIP_SA, ex, y_ - (CLIP_SA[3] - CLIP_SA[1]), 1.0)
dimnote(ax, ex + 330, y_ + 3, "左（南）の高野川の崖から右（北）の大学へ、低い本館 → 高い西館 → おむすび。地域の建物の高低の流れに沿う")
dimnote(ax, ex + 330, y_ - 2, "（3dmの周辺の建物の箱（PLATEAU）を背景に薄く重ねる）")
y_ -= h_ + 2
title(ax, ex, y_ - 4, "道路の側の立面図", "1/100　西の道路から")
y_ -= 7
_, h_ = embed(3, ELE1, CLIP_E2, ex, y_ - (CLIP_E2[3] - CLIP_E2[1]), 1.0)
dimnote(ax, ex + 520, y_ + 3, "西館の西端は1階の高さ（向かいの住宅を点線で描き足す）。西館の立ち上がりが北で主張する")
y_ -= h_ + 3
bh = y_ - (M + 8)
w3, h3 = embed(3, ELE2, CLIP_E3, ex, M + 8, 0.5)
title(ax, ex, M + 8 + h3 + 2, "高野川の側の立面図", "1/200　川の向こうから")
bx3 = ex + w3 + 8
box(ax, bx3, M + 8, 220, bh, "夜の立面（園庭の側）", "黒地に越屋根の東の縁の光の線だけ\n水平の光が一本、川向こうから見える\n（模型の夜景写真でもよい）")
box(ax, bx3 + 228, M + 8, W - M - 6 - (bx3 + 228), bh, "景観の約束", "景観条例の基準（高さ・屋根の形・色）を\n守ることを一行で（地区の基準は確認）\n高野川沿いの修景\n小竹薮公園を残す", fill="#FAF8FF")
figs.append(fig)

# ================================================================ 4　環境
fig, ax = page()
frame(ax, 4, "環境", "木造・パッシブ（床下・越屋根・光の筋）で空調を補う。エネルギー・資源・時間（S&I）まで",
      "断面C 1/50（昼と夏の夜の風、光の筋、床下）→ 運転表と4つの配慮 → 断面B → 2階（職員の側）")
CLIP_C2 = (432, 252, 830, 382)
hC = (CLIP_C2[3] - CLIP_C2[1]) * 2
cx, cy = M + 6, H - M - 16 - 10 - hC
title(ax, cx, cy + hC + 3, "断面図C　4歳・遊戯室の摺鉢ネット", "1/50（1/100の自動の図を2倍）　西の道路から園庭へ")
wC, _ = embed(4, SEC, CLIP_C2, cx, cy, 2.0)
dimnote(ax, cx + 470, cy + hC + 3, "矢印：昼の道（青）と夏の夜の道（紺）。床下の底板t200と断熱の帯。光の筋の光")
oy_ = cy - 8 - 48
cells4 = [("夏の昼", "庇で遮る・天井扇\n床下空調（底板の冷え）"), ("夏の夜", "縁側の段のガラリ→床下→梁間\n→越屋根・遊戯室の吹き抜け"),
          ("春・秋", "越屋根の換気口を開ける\n縁側を開け放す"), ("冬", "換気口を閉じる・熱交換\n基礎断熱・屋根の断熱"),
          ("パッシブ", "床下に冷えをためる\n越屋根の通風、光の筋の昼光"), ("エネルギー", "屋根材型の太陽光\n蓄電池（災害時の拠点）"),
          ("資源", "北山杉の間伐材（山の手入れを支える）\n地域のスギ、土・雨・生ごみを敷地で回す"), ("時間", "スケルトン＆インフィル\n水まわりはどのスパンにも")]
cw4 = (W - 2 * M - 12 - 7 * 4) / 8
for i, (h1, s1) in enumerate(cells4):
    box(ax, cx + i * (cw4 + 4), oy_, cw4, 48, h1, s1, fill="#FAF8FF" if i < 4 else "#F5FAF0", color=NOTE if i < 4 else "#4E8A3A")
T(ax, cx, oy_ + 50, "運転表", 3.2, bold=True)
T(ax, cx + 4 * (cw4 + 4), oy_ + 50, "環境への配慮（LEED v5 Gold相当を目指す）", 3.2, bold=True)
by = M + 8
wB, hB = embed(4, SEC, (25, 252, 422, 382), cx, by, 1.0)
title(ax, cx, by + hB + 3, "断面図B　海峡", "1/100　南の入口・キッチン・2階・すき間・本館・縁側")
CLIP_P2 = (355, 28, 700, 185)
w2, h2 = embed(4, PLAN, CLIP_P2, W - M - 6 - (CLIP_P2[2] - CLIP_P2[0]), by, 1.0)
title(ax, W - M - 6 - w2, by + h2 + 3, "西館2階平面図", "1/100　職員の側")
dimnote(ax, W - M - 6 - w2, by + h2 + 9, "西館2階＝職員の側（休憩室・ぐったり休憩・会議室・更衣）。こどもから離れて休む")
figs.append(fig)

# ================================================================ 5　こどもたちへの環境
fig, ax = page()
frame(ax, 5, "こどもたちへの環境", "娘にこんな環境を与えたい、という空間：遊戯室・切り株・北山杉の林・組み方・変わり方",
      "内観 → 遊戯室 → 同じ部屋の一日 → 林・洞 → 接合部 → S&I → 面積表 → inspired by")
top = H - M - 16 - 6
box(ax, M + 6, top - 210, 297, 210, "内観　ホール（A4）", "北山杉の林・海峡と飛び石・オープンキッチン\n梁の見える天井・光の筋・越屋根の光の線\n（レンダリングか模型写真）")
PLAYP = os.path.join(ROOT, "out", "sodachiya_play_present.pdf")
wPl, hPl = embed(5, PLAYP, None, W - M - 6 - 290, top - 230, 1.0)
x1 = M + 6 + 297 + 8
title(ax, x1, top - 4, "同じ部屋の一日", "3〜5歳の保育室　断面")
SEC35 = os.path.join(ROOT, "out", "sodachiya_35_section.pdf")
CL35 = (30, 70, 360, 215)
for i, t_ in enumerate([("10:00", "遊ぶ"), ("11:30", "食べる"), ("13:30", "寝る")]):
    yy = top - 10 - (i + 1) * 72
    embed(5, SEC35, CL35, x1 + 20, yy, 0.5)
    T(ax, x1, yy + 40, t_[0], 3.0, bold=True)
    T(ax, x1, yy + 34, t_[1], 2.8)
dimnote(ax, x1, top - 10 - 3 * 72 - 5, "今は同じ図。部屋の分け方と天井の高低が決まったら描き分ける")
by = M + 8
bt = top - 238                     # 下の段の上端
FOREST = os.path.join(ROOT, "out", "sodachiya_forest_02.pdf")
title(ax, M + 6, bt - 4, "ホールの北山杉の林", "こどもの目の高さ（0.9 m）から")
wF, hF = embed(5, FOREST, (0, 8, 420, 118), M + 6, bt - 10 - 105, fit=(230, 105))
T(ax, M + 6, bt - 10 - hF - 5, "京都北山の北山杉の間伐材141本。こどもには林、先生には見渡せる（低い木は0.85〜1.1 m）", 2.6)
JD = os.path.join(ROOT, "out", "joint_detail.pdf")
title(ax, M + 6, bt - 10 - hF - 14, "接合部", "楕円の頭と桁、2枚の梁で柱を挟む（縮小）")
embed(5, JD, None, M + 6, by, fit=(230, bt - 10 - hF - 20 - by))
x2 = M + 6 + 238
CAVE = os.path.join(ROOT, "out", "sodachiya_play_cave.pdf")
title(ax, x2, bt - 4, "洞のクスノキ", "断面パース（遊戯室のチャット）")
embed(5, CAVE, None, x2, bt - 10 - 112, 1.0)
box(ax, x2, by, 160, bt - 10 - 112 - 8 - by, "光の筋と架構　1/20", "2枚の梁のあいだ180の上に\n乳白ガラスの光の筋\n垂木・楕円の桁と一枚で（作成）")
x3 = x2 + 168
box(ax, x3, by, 200, bt - 4 - by, "スケルトン＆インフィル", "3 mスパンの架構（固定）と\n間仕切りA・B・C、家具（可変）を色分け\nどのスパンにも上水・下水の口\n\n今 ／ 定員が変わる ／ 学童・地域の場\nの3コマ")
tx = x3 + 208
AJ = json.load(open(os.path.join(ROOT, "model", "drawings", "sodachiya_areas.json"), encoding="utf-8"))
title(ax, tx, bt - 4, "面積表", "m²（壁芯、3dmから自動）")
T(ax, tx, bt - 12, "室", 2.4, NOTE); T(ax, tx + 50, bt - 12, "要求", 2.4, NOTE); T(ax, W - M - 8, bt - 12, "計画", 2.4, NOTE, ha="right")
yy = bt - 18
for r_ in AJ["rooms"]:
    if r_["planned"] is None and not r_["judge"]:
        continue
    nm = r_["room"].replace(" ", "")
    T(ax, tx, yy, nm[:12], 2.3)
    T(ax, tx + 50, yy, r_["required"].replace(" ", ""), 2.3)
    T(ax, W - M - 8, yy, f"{r_['planned']:.1f}" if r_["planned"] else r_["judge"], 2.3, ha="right")
    yy -= 4.6
T(ax, tx, yy, "延床（2,000以内）", 2.3, bold=True)
T(ax, W - M - 8, yy, f"{AJ['floor']['total']:,.1f}", 2.3, ha="right", bold=True)
INSP = [("Asilo Nido Iride", "Mario Cucinella Architects・Guastalla・2015", "梁の列が並ぶ長細い本館と、外に付く付属の建物"),
        ("Tamedia", "坂茂・Zürich・2013", "梁の端の楕円の頭と、それを貫く楕円の桁"),
        ("レイモンド斑鳩こども園", "キノアーキテクツ・斑鳩・2026", "室内に木を立てる（ホールの北山杉）"),
        ("KAIT工房", "石上純也・厚木・2008", "柱の配列：見る向きで景色が変わる並び"),
        ("認定こども園らみどり", "はりゅうウッドスタジオ・須賀川・2026", "内と外の二重の縁側、遊具を置かない地形の園庭"),
        ("仙田満の園舎", "環境デザイン研究所", "摺鉢のネット、キャットウォーク、ニッチ"),
        ("Waldorf School of the Peninsula", "California", "遊戯室の切り株")]


def _tw(t, size):
    return sum(size / 0.72 * (0.6 if ord(c) < 0x2000 else 1.0) for c in t)


iy = yy - 9
T(ax, tx, iy, "inspired by", 3.0, bold=True)
for i, (n, src, what) in enumerate(INSP):
    y2 = iy - 6 - i * 10.5
    T(ax, tx, y2, n, 2.2, bold=True)
    T(ax, tx, y2 - 3.4, src, 1.8, "#666666")
    T(ax, tx + 1.5, y2 - 6.6, "→ " + what, 1.9)
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
# 提出の5枚は sodachiya/presentation.pdf の一つだけ（ユーザー、10-24：前は5枚と「全体＋5枚」の2つがあった）。
# 壁に貼ったときの全体は present/out/sodachiya_present_overview.png
sheets = os.path.join(ROOT, "presentation.pdf")
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
notes = ["課題の言葉の順：1 敷地と自然環境 → 2 すべての人の一日 → 3 景観。",
         "右の列：4 環境 → 5 こどもたちへの環境。",
         "目の高さに来るのは1階平面（最も細かい図）と断面C。",
         "2〜4枚目の平面・立面・断面は3dmから自動の図を実寸で貼る。",
         "製図台に置くなら2＋2＋1（1・2／3・4／5）に切り分ける。"]
for i, s in enumerate(notes):
    TW(x0w + 841 * 2 + 200, 2050 - i * 70, s, 3.2, color=NOTE)
ov = os.path.join(OUT, "_overview.pdf")
fig.savefig(ov)
fig.savefig(os.path.join(OUT, "sodachiya_present_overview.png"), dpi=40)

for f in (base, ov):
    os.remove(f)
json.dump(dict(info, areas={k: round(v, 1) for k, v in AREA.items()}), open(os.path.join(OUT, "mock_info.json"), "w"), ensure_ascii=False, indent=1)
print("ok")
