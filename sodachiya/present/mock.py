"""育ち舎　提出A1×5枚の仮の割付（プレゼンの準備のチャット）

実寸の確認が目的：3dm（sodachiya_exact_mesh.3dm）から平面・配置・立面の外形を
その縮尺のまま描き、自動の断面（drawings/）や他のチャットの図（out/）を
実寸または縮小で貼り込む。未作成のものは破線の枠（大きさは実寸）で示す。
紫の文字は割付の注記（本番では消す）。

python sodachiya/present/mock.py  →  sodachiya/presentation.pdf（5枚）／ present/out/ の全体の画像
"""
import os, re, subprocess, sys, json
import numpy as np
import rhino3dm as r
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPoly
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon, MultiPolygon, MultiPoint, LineString, Point
from shapely.ops import unary_union
import fitz

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONTB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_ALT = {"Apple-Chancery": "/usr/share/texmf/fonts/opentype/public/tex-gyre/texgyrechorus-mediumitalic.otf"}   # 見本でApple Chanceryの代わり（Zapf Chanceryに似た形）
# 文字をIllustratorで文字として直せるように、TrueTypeに変えたNoto（tools/make_ttf.py）をType42で埋め込む。無ければ前のまま（Type3）
_TTF = os.path.expanduser("~/.cache/sodachiya_fonts")
if not os.path.exists(os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")):
    subprocess.run([sys.executable, os.path.join(HERE, "tools", "make_ttf.py"), _TTF], check=False)
if os.path.exists(os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")):
    FONT, FONTB = os.path.join(_TTF, "NotoSansCJKjp-Regular.ttf"), os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")
    plt.rcParams["pdf.fonttype"] = 42
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
        objs.append(dict(layer=ln, name=o.Attributes.Name or "", kind="mesh", V=V, F=np.array(F)))
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
            objs.append(dict(layer=ln, name=o.Attributes.Name or "", kind="solid", V=np.array(P) / 1000, prof=prof, prof_closed=prof_closed))
    elif isinstance(g, r.Brep):
        for fi in range(len(g.Faces)):
            mm = g.Faces[fi].GetMesh(r.MeshType.Any)
            if mm is None:
                continue
        bb = g.GetBoundingBox()
        P = [(x, y, z) for x in (bb.Min.X, bb.Max.X) for y in (bb.Min.Y, bb.Max.Y) for z in (bb.Min.Z, bb.Max.Z)]
        objs.append(dict(layer=ln, name=o.Attributes.Name or "", kind="solid", V=np.array(P) / 1000))
    elif isinstance(g, (r.PolylineCurve, r.NurbsCurve, r.LineCurve)):
        objs.append(dict(layer=ln, name=o.Attributes.Name or "", kind="curve", V=np.array(curve_pts(g)) / 1000))


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
# 色の計画（ユーザー、10-24夜：0〜5歳は緑のグラデーションに戻す。大人の場所は一つの色相、通りとつなぐ場所は一つの色）
C_KIDS = {"53_": "#E6EFC2", "54_": "#C5DE9A", "59_1F_3歳": "#9FCB84", "59_1F_4歳": "#86BC78", "59_1F_5歳": "#6FA96E"}
C_SHARE = "#F6E3A4"            # こどものみんなの場所（遊ぶ・食べる）：遊戯室・はれのま（食べる土間）
C_WAY = "#E9DFCF"              # 通り・つなぐ場所（はだし）：ホール・東の帯（キッチンの前）・西の吹き抜け・内縁側・2階のホール
C_WAY_SHOE = "#D8CCB8"         # 同じ色相の土足の所：外縁側・海峡・受け取り土間
C_ADULT = "#D9D3EC"            # 大人の場所（キッチン以外は一色、階段・機械室も、ユーザー）
C_ADULT_DK = "#C9C1E3"         #   キッチン・調理の更衣（園の中心なので少し濃く）
C_WATER = "#D5EBEE"            # 水まわり（こどもの便所・多目的便所）
ROOM = dict(C_KIDS, **{
    "31_": C_SHARE, "34_": C_SHARE,
    "59_1F_ホール": C_WAY, "33_": C_WAY, "56_": C_WAY, "59_1F_西吹き抜け": C_WAY, "13_": C_WAY, "12_": C_WAY, "41_": C_WAY, "36_": C_ADULT,
    "14_": C_WAY_SHOE, "15_": C_WAY_SHOE, "52_": C_WAY_SHOE,
    "59_1F_事務": C_ADULT, "43_": C_ADULT, "43b_": C_ADULT, "44_": C_ADULT, "45_": C_ADULT, "42_": C_ADULT, "59_1F_便所（職員）": C_ADULT, "35_": C_ADULT,
    "59_1F_医務": C_ADULT, "59_1F_静養室": C_ADULT, "59_1F_園長室": C_ADULT,
    "32_": C_ADULT_DK, "57_": C_ADULT_DK,
    "59_1F_便所・倉庫": C_WATER, "59_1F_便所（こども）": C_WATER, "59_1F_倉庫": C_ADULT, "59_1F_多目的便所": C_WATER, "59_1F_便所": C_WATER,
})


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


# Illustratorの割付（present/ai/、ユーザー、10-25夕）：ページの文字・箱・素材を部品として記録し、layout.json に書き出す
AIREC = []          # dict(kind=…, fig=…, …)。紙のmm、左下が原点（書き出しで左上の原点に直す）
AIMUTE = [0]        # 箱などが自分で記録するあいだ、中の T は記録しない


def _airec(fig, **kw):
    if AIMUTE[0] == 0:
        AIREC.append(dict(fig=fig, **kw))


SITE_LIVE = [None]   # 配置図の中の文字・注の線・突き出た木を、Illustratorで一つずつ動かせる部品にする（ユーザー、10-25夕）。その間の配置図の軸
SITEPARTS = []       # dict(kind=text|line|circle, …)。紙のmm、左下が原点。1枚目に貼った図の上に描き、layout.json の部品に


def _sid(s):
    return re.sub(r"[\s　/\\|:（）()、。・]+", "", s)[:16] or "x"


def T(ax, x, y, s, size=3.0, color=INK, bold=False, ha="left", va="baseline", **kw):
    """sizeは文字の高さ（mm）"""
    if SITE_LIVE[0] is not None and ax is SITE_LIVE[0] and s:
        SITEPARTS.append(dict(kind="text", x=x, y=y, s=s, size=size, color=matplotlib.colors.to_hex(color), bold=bold, ha=ha, va=va, group=kw.get("group")))
        return
    kw.pop("group", None)
    fnt = kw.pop("font", None)                     # Illustratorで使う書体の名前（無ければヒラギノ）。見本では似た書体で
    pt = size / 0.3528 / 0.72
    ax.text(x, y, s, fontsize=pt, color=color, ha=ha, va=va,
            fontproperties=FontProperties(fname=FONT_ALT.get(fnt, FONTB if bold else FONT), size=pt), **kw)
    if s:
        _airec(ax.figure, kind="text", x=x, y=y, s=s, size=size, color=color, bold=bold, ha=ha, va=va, font=fnt)


def frame(ax, no, theme, focus, order):
    AIMUTE[0] += 1
    ax.add_patch(Rectangle((M, M), W - 2 * M, H - 2 * M, fill=False, lw=0.6, ec=INK, gid="aipart"))
    ax.plot([M, W - M], [H - M - 16, H - M - 16], color=INK, lw=0.4, gid="aipart")
    T(ax, M + 4, H - M - 11, "こどもたちの育ち舎", 6.5, bold=True)
    T(ax, M + 92, H - M - 11, f"{no}/5　{theme}", 5.0, bold=True)
    T(ax, W - M - 4, M + 4, "建築設計実習Ⅱ—Ⅰ　2026.11.05　木田", 3.0, ha="right")   # 名前などは右下（ユーザー、10-25）
    # 注記
    T(ax, M + 4, M - 6, f"［割付の注記］フォーカス：{focus}　／　目に入る順：{order}", 3.2, NOTE)
    AIMUTE[0] -= 1
    _airec(ax.figure, kind="frame")
    _airec(ax.figure, kind="text", id="pagetitle", name="ページとサブタイトル", x=M + 92, y=H - M - 11, s=f"{no}/5　{theme}", size=5.0, color=INK, bold=True, ha="left", va="baseline")
    _airec(ax.figure, kind="text", id="note.footer", name="割付の注記", x=M + 4, y=M - 6, s=f"［割付の注記］フォーカス：{focus}　／　目に入る順：{order}", size=3.2, color=NOTE, bold=False, ha="left", va="baseline")


def box(ax, x, y, w, h, label, sub="", color=NOTE, fill="#F4F1FF"):
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=color, lw=0.6, ls=(0, (3, 2)), gid="aipart"))
    _airec(ax.figure, kind="box", id=f"box.{label}", name=f"枠：{label}", x=x, y=y, w=w, h=h, fill=fill, stroke=color, lw=0.6, dash=[3, 2])
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
    # 床は部屋ごとに塗って輪郭を細く引く。ただしホール・西の吹き抜け・内縁側はこどもには一つの場所なので、
    # 一つにまとめて継ぎ目の線を出さない（ユーザー、10-24夜）。12（本館の床の板）は塗るだけ
    ONE = ("59_1F_ホール", "56_", "59_1F_西吹き抜け", "13_")
    _grp = {}
    for i_, (ln, kind, g) in enumerate(order):
        c = room_color(ln)
        if c and g is not None:
            fc = c
            if keyhi is not None:
                fc = c if ln.startswith(tuple(keyhi)) else "#F1F1F1"
            key = ("one", fc) if ln.startswith(ONE) else (ln, i_)
            _grp.setdefault(key, [fc, 0 if ln.startswith(base) else 1, ln.startswith("12_"), []])[3].append(g.buffer(0.02) if key[0] == "one" else g)
    for key, (fc, lay, noline, gs) in sorted(_grp.items(), key=lambda kv: kv[1][1]):
        draw_shape(ax, unary_union(gs), xf, fc=fc, ec="none" if noline else "#9A9A9A", lw=0 if noline else 0.12, z=1 + 0.01 * lay)
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

embeds = {i: [] for i in range(1, 6)}
SOZAI = []   # 素材：mock.pyが描いた図の範囲（紙のmm、左下）。書き出しで一つずつPDFに（ユーザー、10-25：.aiは素材から作る）


def sozai(key, name, sheet, x, y, w, h, note=""):
    SOZAI.append((key, name, sheet, (x, y, w, h), note))


# 木田さんが足した物（present/ai/layout_user.json の user_items、アートボードの左上からmm）
USER_ITEMS = {}
try:
    for _ui in json.load(open(os.path.join(HERE, "ai", "layout_user.json"), encoding="utf-8")).get("user_items", []):
        USER_ITEMS.setdefault(int(_ui.get("artboard", 0)), []).append(_ui)
except Exception:
    pass


def _hexrgb(h):
    if not h or not isinstance(h, str) or not h.startswith("#"):
        return None
    return tuple(int(h[k:k + 2], 16) / 255 for k in (1, 3, 5))


def _draw_user_item(pg, d):
    P = lambda q: fitz.Point(q[0] * MM, q[1] * MM)
    try:
        if d.get("type") == "PathItem" and d.get("pts"):
            sh_ = pg.new_shape()
            pts = d["pts"]
            sh_.draw_line(P(pts[0][0]), P(pts[0][0])) if len(pts) == 1 else None
            for k_ in range(len(pts) - 1 + (1 if d.get("closed") else 0)):
                a_, b_ = pts[k_], pts[(k_ + 1) % len(pts)]
                sh_.draw_bezier(P(a_[0]), P(a_[2]), P(b_[1]), P(b_[0]))
            sw_ = float(d.get("stroke_pt") or 0)
            sh_.finish(color=_hexrgb(d.get("stroke")), fill=_hexrgb(d.get("fill")), width=sw_, closePath=bool(d.get("closed")),
                       stroke_opacity=float(d.get("opacity", 100)) / 100, fill_opacity=float(d.get("opacity", 100)) / 100, lineCap=1)
            sh_.commit()
        elif d.get("type") == "TextFrame" and d.get("s"):
            pg.insert_text(fitz.Point(d["x"] * MM, (d["y"] + d.get("h", 4)) * MM), d["s"], fontsize=float(d.get("size_pt", 9)),
                           fontname="F_R", fontfile=FONT, color=_hexrgb(d.get("color")) or (0.1, 0.1, 0.1))
        elif d.get("children"):
            for c_ in d["children"]:
                _draw_user_item(pg, c_)
    except Exception as e_:
        print("木田さんの物を見本に描けなかった：", d.get("name") or d.get("type"), e_)


TOPT = {i: [] for i in range(1, 6)}     # 貼った図の上に置く文字（紙のmm、左下）：(x, y, 文字, 高さmm, 太字)
TOPL = {i: [] for i in range(1, 6)}     # 貼った図の上に描く引き出し線（紙のmm）：(点, 箱の端, 色)


def topline(sheet, p_pt, p_box, color, via=(), key=None):
    """配置図の点p_ptから箱の端p_boxへ。viaは途中の折れ点（箱の側から）。key＝部品の名前（箱のkey＋番号、10-26：番号でなく箱に結ぶ）"""
    TOPL[sheet].append(([tuple(p_box)] + [tuple(v) for v in via] + [tuple(p_pt)], color, key))


def ibox(ax, x, y, w, h, head, lines, color, fill, size=3.2, key=None):
    """説明の箱（見出し＋本文、左寄せ）。key を渡すと部品のidが見出しの文に依らない（見出しを直しても同じ部品）"""
    k_ = key or head
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=color, lw=0.5, gid="aipart"))
    _airec(ax.figure, kind="box", id=f"ibox.{k_}", name=f"箱：{head}", x=x, y=y, w=w, h=h, fill=fill, stroke=color, lw=0.5, dash=None)
    _airec(ax.figure, kind="text", id=f"ibox.{k_}.head", name=f"見出し：{head}", x=x + 3, y=y + h - 7, s=head, size=3.8, color=color, bold=True, ha="left", va="baseline")
    _airec(ax.figure, kind="area", id=f"ibox.{k_}.body", name=f"本文：{head}", x=x + 3, y=y + h - 14, w=w - 6, h=h - 16,
           s="\n".join(lines), size=size, color=INK, bold=False, leading=1.5, para_space=1.0)
    AIMUTE[0] += 1
    T(ax, x + 3, y + h - 7, head, 3.8, color, bold=True)
    yy = y + h - 14
    for ln_ in lines:
        for s_ in jwrap(ln_, (w - 6) / (size / 0.72)):
            T(ax, x + 3, yy, s_, size)
            yy -= size / 0.72 * 1.5                 # 行送りは文字の1.5倍（ユーザー、10-25夕）
        yy -= size / 0.72                       # 段落のあいだは1行分（ユーザー、10-25夕）
    AIMUTE[0] -= 1
   # (src_pdf, page, clip_mm(x0,y0,x1,y1)|None, dest_mm(x,y,w,h)下原点, keep_ratio)
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
frame(ax, 1, "敷地と自然環境・地域", "周囲の自然環境との関係と地域環境への配慮。配置図の上に夏の夜の風・比叡への視線",
      "タイトルと趣旨 → 真ん中の配置図 → 左右の箱（青＝自然環境、茶＝地域）→ 用水のネットワーク・地域のなかの敷地")
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
        if n + w_ > width and ch_ not in "。、）」" and not (cur and ord(cur[-1]) < 0x2000 and ord(ch_) < 0x2000 and ch_ != " "):   # 欧文・数字の語の途中では折らない
            k_ = len(cur)
            while k_ > 0 and ord(cur[k_ - 1]) < 0x2000 and cur[k_ - 1] != " ":
                k_ -= 1
            if 0 < k_ < len(cur) and ord(ch_) < 0x2000:
                out.append(cur[:k_]); cur = cur[k_:]; n = sum(0.5 if ord(c) < 0x2000 else 1.0 for c in cur)
                cur += ch_; n += w_
                continue
            out.append(cur); cur, n = "", 0.0
            if ch_ == " ":
                continue
        cur += ch_; n += w_
    return out + ([cur] if cur else [])


_y = top - 28
_airec(fig, kind="area", id="concept", name="設計趣旨", x=M + 6, y=_y, w=40 * 3.6 / 0.72 + 1, h=0, s="\n".join(p_.lstrip("　 ") for p_ in _paras),
       size=3.6, color=INK, bold=False, leading=1.5, para_space=1.0)
_ystart = _y
AIMUTE[0] += 1
for _p in _paras:
    for s in jwrap(_p.lstrip("　 "), 40):     # 一字下げしない（ユーザー、10-25夕）
        T(ax, M + 6, _y, s, 3.6)
        _y -= 3.6 / 0.72 * 1.5        # 行送りは文字の1.5倍（ユーザー、10-25夕）
    _y -= 3.6 / 0.72                  # 段落のあいだは1行分（ユーザー、10-25夕）
AIMUTE[0] -= 1
AIREC[-1]["h"] = _ystart - _y + 6
CONCEPT_BOT = _y - 6                                     # 設計趣旨の下端（左の箱の列はここから下）
dimnote(ax, M + 6, _y + 1, f"設計趣旨 約{len(concept.replace(' ', ''))}字（課題は300字程度）。文字3.6 mmなら1 m離れて読める")
# 配置図1/200と小さな地図の共通（高野川の辺を下に水平：川向こうから見る向き、ユーザー。園庭の図と同じ回し方）
from shapely import affinity
_Ms = np.array([d, wv])                                # to_sの回転の部分（3dmのxy → 紙の座標）
assert np.linalg.det(_Ms) > 0
_phi = np.degrees(np.arctan2(_Ms[1, 0], _Ms[0, 0]))
ROT = GJ["VIEW_ROT"]["deg"] - _phi                    # 3dmから見てVIEW_ROT（園庭の図と同じ）
rot = lambda g: affinity.rotate(g, ROT, origin=(0, 0)) if g is not None else None
_rr = np.radians(ROT)


def R3(P):
    """3dmのxy（m）→ 回した座標（m）"""
    S_ = to_s(np.atleast_2d(np.asarray(P, float)))
    return np.c_[S_[:, 0] * np.cos(_rr) - S_[:, 1] * np.sin(_rr), S_[:, 0] * np.sin(_rr) + S_[:, 1] * np.cos(_rr)]


_site = max([o for o in L("00_") if o["kind"] == "curve"], key=lambda o: len(o["V"]))
_S = to_s(_site["V"])
_Q = np.array(rot(Polygon(_S)).exterior.coords)
QX0, QY0 = _Q.min(0)
QX1, QY1 = _Q.max(0)
CTX = [(o["layer"], shape(o, "plan")) for o in objs if o["layer"].startswith(("03_", "04_"))]   # 周辺の道路・建物（PLATEAU）
WT = json.load(open(os.path.join(HERE, "water_trace.json"), encoding="utf-8"))                 # 敷地図の用水路と高野川（なぞった線）
_nv = north_s / np.linalg.norm(north_s)
_nv = np.array([_nv[0] * np.cos(_rr) - _nv[1] * np.sin(_rr), _nv[0] * np.sin(_rr) + _nv[1] * np.cos(_rr)])
SITE_C = {k: np.array(v) for k, v in dict(N=(0.0, 0.0), E=(34.86, -43.83), S=(-14.44, -83.04),
                                         SW=(-21.91, -73.65), NW=(-25.83, -20.54)).items()}

# 敷地の北東の辺から顔を出す道（今の住宅のあいだを高野川に並行に通る道の続き、PLATEAU）は描かない（ユーザー、10-26夜）。周辺の形は s の座標
_neN, _neE = to_s(np.atleast_2d(SITE_C["N"]))[0], to_s(np.atleast_2d(SITE_C["E"]))[0]
_NEe = LineString([_neN, _neE])
_ned = (_neE - _neN) / np.linalg.norm(_neE - _neN); _nen = np.array([_ned[1], -_ned[0]])
if Polygon(to_s(np.array(list(SITE_C.values())))).contains(Point(*(np.array(_NEe.centroid.coords[0]) + _nen))): _nen = -_nen
_neA, _neB = _neN + (_neE - _neN) * 0.2, _neN + (_neE - _neN) * 0.95       # 辺の両端（北の道・東の角）にかかる道は残す
_NESTRIP = Polygon([_neA, _neB, _neB + _nen * 40, _neA + _nen * 40])
_RD3 = unary_union([g for ln, g in CTX if ln.startswith("03_") and g is not None]).buffer(0)
_x = _RD3.intersection(_NESTRIP)
_NESTUB = unary_union([g for g in getattr(_x, "geoms", [_x]) if g.geom_type == "Polygon" and g.distance(_NEe) < 1.0])
if not _NESTUB.is_empty:
    print("北東の辺から出る道を消す：", round(_NESTUB.area, 1), "m2　辺から", round(max(float(np.dot(np.array(c_) - _neN, _nen)) for g_ in getattr(_NESTUB, "geoms", [_NESTUB]) for c_ in g_.exterior.coords), 1), "m まで")
    CTX = [(ln, (g.difference(_NESTUB.buffer(0.05)) if ln.startswith("03_") and g is not None else g)) for ln, g in CTX]
# 沿川の景観立面：川の辺に直角に、川の向こうから。3dmの建物と周りの建物（PLATEAU）・崖を投影して影絵で（1/300）
_eRv = (SITE_C["S"] - SITE_C["E"]) / np.linalg.norm(SITE_C["S"] - SITE_C["E"])
_oRv = np.array([-_eRv[1], _eRv[0]])
if _oRv @ (SITE_C["E"] - SITE_C["NW"]) < 0:
    _oRv = -_oRv                                     # 川の側
_tdir, _ddir = -_eRv, -_oRv                          # 川から見て右へ（北東へ）、奥へ（北西へ）
LE_T0, LE_T1, LE_Z0, LE_Z1, LE_SC = -22.0, 86.0, -6.5, 19.0, 300
_mine = ("10", "11", "14", "16", "17", "18", "19", "20", "21", "22", "23", "28", "35", "50")   # 29（西館の越屋根の LED）は led


def _elev_items():
    out = []
    for o in objs:
        if o["kind"] != "mesh":
            continue
        ln = o["layer"]
        cls = "ctx" if ln.startswith("04_") else ("cliff" if ln.startswith("02_") else ("led" if ln.startswith(("50b", "29_")) else ("me" if ln[:2] in _mine else None)))
        if cls is None:
            continue
        V = o["V"]
        rel = V[:, :2] - SITE_C["S"]
        t, dpt, z = rel @ _tdir, rel @ _ddir, V[:, 2]
        if t.max() < LE_T0 or t.min() > LE_T1 or dpt.min() > 160 or dpt.max() < -8:
            continue
        P = np.c_[t, z]
        polys = [Polygon(P[f]) for f in o["F"]]
        polys = [q for q in polys if q.area > 1e-4]
        if not polys:
            continue
        out.append((cls, float(np.mean(dpt)), unary_union(polys).buffer(0)))
    return out


ELEV = _elev_items()


def land_elev(ax, x0, y0, night):
    """沿川の景観立面（影絵）。x0,y0＝紙の左下"""
    k = 1000 / LE_SC
    f = lambda P: np.c_[x0 + (np.asarray(P)[:, 0] - LE_T0) * k, y0 + (np.asarray(P)[:, 1] - LE_Z0) * k]
    w, h = (LE_T1 - LE_T0) * k, (LE_Z1 - LE_Z0) * k
    ax.add_patch(Rectangle((x0, y0), w, h, fc="#18233A" if night else "#F7F9FB", ec="none", zorder=0.5))
    rp_ = clip_rect(ax, x0, y0, w, h)
    st_ = len(ax.patches)
    # Rhino のレイトレースの絵があればそれを使う（present/rhino/keikan_render.py → rhino/out/、ユーザー 10-27）。無ければ影絵
    _png = os.path.join(HERE, "rhino", "out", "keikan_yoru.png" if night else "keikan_hiru.png")
    _vj = os.path.join(HERE, "rhino", "out", "keikan_view.json")
    if os.path.exists(_png) and os.path.exists(_vj):
        _v = json.load(open(_vj, encoding="utf-8"))
        ax.add_patch(Rectangle((x0, y0), w, (0 - LE_Z0 - 5.0) * k, fc="#2E5D86" if night else "#DCE8EE", ec="none", zorder=0.8))
        _xl, _yl = ax.get_xlim(), ax.get_ylim()
        _im = ax.imshow(plt.imread(_png), extent=(x0 + (_v["t0"] / 1000 - LE_T0) * k, x0 + (_v["t1"] / 1000 - LE_T0) * k,
                                                  y0 + (_v["z0"] / 1000 - LE_Z0) * k, y0 + (_v["z1"] / 1000 - LE_Z0) * k),
                        origin="upper", interpolation="lanczos", zorder=2, aspect="auto")
        _im.set_clip_path(rp_)
        ax.set_xlim(_xl); ax.set_ylim(_yl)
        for a_ in ax.patches[st_:]:
            a_.set_clip_path(rp_)
        print("沿川の景観立面：Rhino の絵", os.path.basename(_png), _v.get("made"))
        return w, h
    dmax = max(d for c, d, g in ELEV) or 1
    for cls, dpt, g in sorted(ELEV, key=lambda e: -e[1]):
        if cls == "ctx":
            v = 0.86 - 0.18 * (1 - min(1, max(0, dpt / 120)))
            fc = "#2B3753" if night else (v, v, v + 0.01)
            if night:
                fc = (0.17 + 0.05 * (1 - dpt / 160), 0.21 + 0.05 * (1 - dpt / 160), 0.32 + 0.06 * (1 - dpt / 160))
            draw_shape(ax, g, f, fc=fc, ec="none", z=1)
        elif cls == "cliff":
            draw_shape(ax, g, f, fc="#2A3A52" if night else "#C9D3DA", ec="none", z=1.5)
        elif cls == "me":
            draw_shape(ax, g, f, fc="#3B4866" if night else "#E9E6E0", ec="#3B4866" if night else "#8A847A", lw=0.08, z=2)
        elif cls == "led" and night:
            draw_shape(ax, g.buffer(0.35), f, fc="#FFD98A", ec="none", z=3)
            draw_shape(ax, g.buffer(1.2), f, fc=(1.0, 0.85, 0.5, 0.18), ec="none", z=2.9)
    ax.add_patch(Rectangle((x0, y0), w, (0 - LE_Z0 - 5.0) * k, fc="#2E5D86" if night else "#DCE8EE", ec="none", zorder=0.8))   # 高野川の水面（GL−5より下）
    for a_ in ax.patches[st_:]:
        a_.set_clip_path(rp_)
    return w, h



def lab(ax, xfun, P3, text, dxy=(0, 0), size=2.6, color=INK, ha="left", lead=True, bold=False):
    """3dmの点P3に注記（紙でdxyずらし、引き出し線）"""
    q = xfun(R3(P3))[0]
    t = q + np.array(dxy)
    live = SITE_LIVE[0] is not None and ax is SITE_LIVE[0]
    grp = f"site.g.{_sid(text)}" if live else None
    if lead and (abs(dxy[0]) + abs(dxy[1]) > 0):
        if live:
            SITEPARTS.append(dict(kind="line", pts=[tuple(t), tuple(q)], color=matplotlib.colors.to_hex(color), lw=0.25, dot=0.25, group=grp, name=f"注の線　{text[:16]}"))
        else:
            ax.plot([q[0], t[0]], [q[1], t[1]], color=color, lw=0.25, zorder=40)
            ax.plot([q[0]], [q[1]], "o", ms=1.2, color=color, zorder=40)
    for k_, s_ in enumerate(text.split("\n")):
        T(ax, t[0] + (1 if ha == "left" else -1), t[1] + 1 - k_ * (size + 1.2), s_, size, color, ha=ha, bold=bold, group=grp)


# 周囲の自然環境との関係（青）と地域環境への配慮（茶）。配置図を真ん中に置き、左右の箱から引き出し線で点へ（ユーザー、10-24夜）
C_NAT, C_COM = "#2F6FA0", "#8A5A2B"
NAT = [("用水を借りる", ["高野川の上の堰で取った水が、松ヶ崎の田を潤してきた用水の網を巡る。その水を借りる。", "北の道の下の暗渠から敷地の北の角へ、北のもりのみなもとに湧き出し、小川になって高野川へ返る。"]),
       ("山から川へ", ["みなもとから縁側の前・原っぱを流れ、護岸の溝を滑り落ちて高野川に合流するまでを、こどもが追える。", "雨は樋に隠さず、雨の川から同じ溝で川へ。"]),
       ("比叡と高野川のうつし", ["築山は比叡のうつし。ホールから頂の向こうに比叡が見える。", "小川は高野川のうつし。足もとを掘った土で築山を盛る。"]),
       ("地下の水と北山の木も借りる", ["松ヶ崎は地面を走る用水と地下の水の両方が豊か。涌泉寺の井戸に見るように井戸水が豊富で、その地下水も借りる。", "京都北山の北山杉の間伐材141本を、ホールの林に立てる。"])]
cy = M + 8 + 26.0 + 400                          # 上の段の下端の目安（配置図の上）

# 配置図1/200：敷地＋西の道路と向かいの住宅、北は大学の角、南は高野川の河川敷まで
VX0, VX1, VY0, VY1 = -26.0, QX1 + 2.0, -21.0, QY1 + 8.0  # 南へ延ばして高野川が見えるように、北は用水路の尻尾をやめて矢印と名前だけ（ユーザー、10-26夕）
sw, sh = (VX1 - VX0) * 5, (VY1 - VY0) * 5
sx, sy = M + 6, H - M - 16 - 3 - sh                            # 配置図は上の帯のすぐ下まで上げる（ユーザー、10-26：配置図の注を消し、下の景観立面との窮屈さを解く）
sx = (W - sw) / 2                                            # 配置図を紙の真ん中に（ユーザー）
P1_BOT = M + 10                                              # 下の帯（沿川の景観立面）は2枚目（景観）へ移した（ユーザー、10-27夜：景観の枚の方が親和性が高い）。下の端の目安
T(ax, sx + 120, sy - 18, "配置図", 6.0, bold=True)                 # 題は図の下に、大きく（ユーザー、10-26）
T(ax, sx + 120 + 3 * 8.4 + 4, sy - 18, "1/200　高野川を下に（川向こうから見る向き、北は右上）", 3.4)
xf = xform(sx, sy, 200, VX0, VY0)
# 素材の配置図は見せる窓より大きく描き、Illustratorの切り抜きの四角で使う大きさを選ぶ（ユーザー、10-26夕）
BX0, BX1, BY0, BY1 = VX0 - 12.0, VX1 + 10.0, VY0 - 6.0, VY1 + 6.0                # 北は紙の上の縁まで（A1の紙の外は描けない）
bsx, bsy = sx + (BX0 - VX0) * 5, sy + (BY0 - VY0) * 5
bsw, bsh = (BX1 - BX0) * 5, (BY1 - BY0) * 5
# 図の置き場所の目印（3dmを回した座標の(0,0)が紙のどこか、左上からmm）。前の窓（南−6 m、北＋14 m）からのずれで、木田さんの描いた物を一緒に動かす
_org = xf(np.array([[0.0, 0.0]]))[0]
_top = sy + sh
_org_prev = (sx + (0 - VX0) * 5, _top - (QY1 + 14.0) * 5)
PLAN_ANCHOR = dict(origin=[round(_org[0], 2), round(H - _org[1], 2)], window=[round(sx, 2), round(H - sy - sh, 2), round(sw, 2), round(sh, 2)])
PLAN_ANCHOR_PREV = dict(origin=[round(_org_prev[0], 2), round(H - _org_prev[1], 2)],
                        window=[round(sx, 2), round(H - _top, 2), round(sw, 2), round((QY1 + 14.0 + 6.0) * 5, 2)])
# 見本に描く木田さんの物も、描いたときの配置図の目印から今の目印へ動かす（layout_user.json の anchors、無ければ前の窓）
try:
    _ua = json.load(open(os.path.join(HERE, "ai", "layout_user.json"), encoding="utf-8")).get("anchors", {}).get("p1.siteplan") or PLAN_ANCHOR_PREV
except Exception:
    _ua = PLAN_ANCHOR_PREV
_udx, _udy = PLAN_ANCHOR["origin"][0] - _ua["origin"][0], PLAN_ANCHOR["origin"][1] - _ua["origin"][1]


def _shift_ui(d, dx, dy):
    if "x" in d: d["x"] += dx
    if "y" in d: d["y"] += dy
    if d.get("pts"): d["pts"] = [[[q[0] + dx, q[1] + dy] for q in pt_] for pt_ in d["pts"]]
    for ch in d.get("children", []) or []: _shift_ui(ch, dx, dy)


if abs(_udx) + abs(_udy) > 0.05:
    _w = _ua["window"]
    for _ui in USER_ITEMS.get(1, []):
        _cx, _cy = _ui.get("x", 0) + _ui.get("w", 0) / 2, _ui.get("y", 0) + _ui.get("h", 0) / 2
        if _w[0] <= _cx <= _w[0] + _w[2] and _w[1] <= _cy <= _w[1] + _w[3]:
            _shift_ui(_ui, _udx, _udy)
# 配置図は別の図に描き、線・色・文字の三つに分けて書き出す（ユーザー、10-25朝：配置図として書き、その上に色、文字。
# 園庭のチャットの図（garden01）は重ねない。屋根・外構・園庭はすべて3dmから）。1枚目にはこの三つを重ねて貼る
_ax_page, _fig_page = ax, fig
figS, ax = page()
rp = clip_rect(ax, bsx, bsy, bsw, bsh)                          # 大きい方の窓で描く（見本には見せる窓だけ貼る）
st = len(ax.patches); stl = len(ax.lines)
SGRP = {"l": [], "c": [], "t": []}
_snap = [0, 0, 0, 0]


def _mk(gr):
    """前の印からあとに描いたものを gr（l 線・c 色・t 文字）に入れる"""
    cur = [len(ax.patches), len(ax.lines), len(ax.texts), len(ax.collections)]
    SGRP[gr] += ax.patches[_snap[0]:cur[0]] + ax.lines[_snap[1]:cur[1]] + ax.texts[_snap[2]:cur[2]] + ax.collections[_snap[3]:cur[3]]
    _snap[:] = cur


def SF(g, fc, z=1, alpha=1.0):
    """色：塗りだけ"""
    _mk("t") if False else None
    draw_shape(ax, g, xf, fc=fc, ec="none", lw=0, z=z)
    if alpha < 1:
        for a_ in ax.patches[_snap[0]:]:
            a_.set_alpha(alpha)
    _mk("c")


COVER = None                     # 上から見て屋根に隠れる所（地面の線は消す：線と色を別の層にするので、塗りでは隠れない）


def SL(g, ec=INK, lw=0.2, z=10, ls="-", grp="l", hide=True):
    """線：輪郭だけ"""
    if g is not None and not g.is_empty and g.geom_type.endswith("Polygon"):
        g = g.boundary
    if hide and COVER is not None and g is not None and not g.is_empty:
        g = g.difference(COVER)
    draw_shape(ax, g, xf, fc="none", ec=ec, lw=lw, z=z, ls=ls)
    _mk(grp)
# 周りは敷地に沿わせて理想化する（ユーザー、10-24：敷地の形が簡略化されているので、PLATEAUのままだと道路とのあいだに余りが見える）
_eW = (SITE_C["SW"] - SITE_C["NW"]) / np.linalg.norm(SITE_C["SW"] - SITE_C["NW"])   # 西の辺（北から南へ）
_oW = np.array([-_eW[1], _eW[0]])
if _oW @ (SITE_C["NW"] - SITE_C["E"]) < 0:
    _oW = -_oW                                                                 # 外（西）へ
_eN = (SITE_C["N"] - SITE_C["NW"]) / np.linalg.norm(SITE_C["N"] - SITE_C["NW"])     # 北の辺（西から東へ）
_oN = np.array([-_eN[1], _eN[0]])
if _oN @ (SITE_C["N"] - SITE_C["S"]) < 0:
    _oN = -_oN                                                                 # 外（北西）へ
_eE = (SITE_C["E"] - SITE_C["N"]) / np.linalg.norm(SITE_C["E"] - SITE_C["N"])       # 北東の辺（北から東へ）
_oE = np.array([-_eE[1], _eE[0]])
if _oE @ (SITE_C["E"] - SITE_C["SW"]) < 0:
    _oE = -_oE
RW_W, RW_N = 6.0, 6.0                                                          # 西の道路・北の道の幅（m）


def _band(P0, e, o, a0, a1, b0, b1):
    """辺の点P0から、辺の向きeにa0〜a1、外の向きoにb0〜b1の四角（3dmのm）"""
    return Polygon([P0 + a * e + b * o for a, b in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))])


def _line_x(P, d, Q, f):
    """P + t d と Q + s f の交点"""
    t = np.linalg.solve(np.c_[d, -f], Q - P)[0]
    return P + t * d


_LW = np.linalg.norm(SITE_C["SW"] - SITE_C["NW"])
_LN = np.linalg.norm(SITE_C["N"] - SITE_C["NW"])
_cNW = _line_x(SITE_C["NW"] + RW_W * _oW, _eW, SITE_C["NW"] + RW_N * _oN, _eN)   # 二つの道の外の角
# 敷地に接する道（西の道・公園の脇で折れて川へ・北の道）は敷地の辺に沿わせ、その先（交差点・二本の橋・川沿いの道）と建物はPLATEAUを使う（ユーザー、10-24）
_eS = (SITE_C["S"] - SITE_C["SW"]) / np.linalg.norm(SITE_C["S"] - SITE_C["SW"])     # 公園の脇の辺（折れた所から川へ）
_oS = np.array([-_eS[1], _eS[0]])
if _oS @ (SITE_C["SW"] - SITE_C["E"]) < 0:
    _oS = -_oS
_LS = np.linalg.norm(SITE_C["S"] - SITE_C["SW"])
RW_N = 7.0
_cSW = _line_x(SITE_C["SW"] + RW_W * _oW, _eW, SITE_C["SW"] + RW_W * _oS, _eS)   # 折れ目の外の角
ROAD_EDGE = unary_union([
    _band(SITE_C["NW"], _eW, _oW, -9.0, _LW, 0.0, RW_W),                        # 西の道（北の道を渡るまで）
    Polygon([SITE_C["SW"], SITE_C["SW"] + RW_W * _oW, _cSW, SITE_C["SW"] + RW_W * _oS]).convex_hull,
    _band(SITE_C["SW"], _eS, _oS, 0.0, _LS + 6.5, 0.0, RW_W),                  # 公園の脇を川へ（橋のたもとまで）
    _band(SITE_C["SW"], _eS, _oS, _LS - 4.0, _LS + 6.5, 0.0, RW_W + 2.0),     # 川沿いの道とつなぐ
    _band(SITE_C["NW"], _eN, _oN, -12.0, _LN + 60.0, 0.0, RW_N)])              # 北の道
_ZONE = unary_union([_band(SITE_C["NW"], _eW, _oW, 4.0, _LW + 2.0, 0.0, 13.0),
                     _band(SITE_C["SW"], _eS, _oS, -2.0, _LS, 0.0, 13.0),
                     _band(SITE_C["NW"], _eN, _oN, 4.0, _LN + 60.0, 0.0, 14.0)])
_SITE3 = Polygon([SITE_C[k] for k in ("N", "E", "S", "SW", "NW")])
_A3 = np.c_[R3(np.array([SITE_C[k] for k in ("N", "E", "S")])), np.ones(3)]
_B3 = np.array([SITE_C[k] for k in ("N", "E", "S")])
_INV = np.linalg.solve(_A3, _B3)                                               # 回した座標 → 3dm（アフィン）


def R3inv(Q):
    Q = np.atleast_2d(np.asarray(Q, float))
    return np.c_[Q, np.ones(len(Q))] @ _INV


def _to3(g):
    if g is None or g.is_empty:
        return None
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        return unary_union([x for x in (_to3(p) for p in g.geoms) if x is not None])
    if g.geom_type != "Polygon":
        return None
    return Polygon(R3inv(np.array(g.exterior.coords)), [R3inv(np.array(r.coords)) for r in g.interiors])


_P_ROAD = unary_union([x for x in (_to3(rot(gg)) for ln, gg in CTX if gg is not None and ln.startswith("03_")) if x is not None]).buffer(0)
_P_BLD = [x for x in (_to3(rot(gg)) for ln, gg in CTX if gg is not None and ln.startswith("04_")) if x is not None]
ROADS = unary_union([_P_ROAD.difference(_ZONE), ROAD_EDGE]).buffer(0.3).buffer(-0.3).buffer(-0.4).buffer(0.4).difference(_SITE3)
# 道の向かいの家は道に沿って建つ（ユーザー、10-24）：西の道が敷地の辺へ寄った分だけ、向かいの街区（北の三軒とその奥）を道へ寄せる
def _ab(g):
    c = np.array(g.centroid.coords[0]) - SITE_C["NW"]
    return c @ _eW, c @ _oW


_blk = [b for b in _P_BLD if -6.0 < _ab(b)[0] < 34.0 and RW_W < _ab(b)[1] < 45.0]
_front = [b for b in _blk if _ab(b)[1] < 22.0]
_gap = min(min((np.array(p_) - SITE_C["NW"]) @ _oW for p_ in b.exterior.coords) for b in _front) - (RW_W + 0.8) if _front else 0.0
_P_BLD = [affinity.translate(b, *(-_gap * _oW)) if any(b is x for x in _blk) else b for b in _P_BLD]
_front = [b for b in _P_BLD if -6.0 < _ab(b)[0] < 34.0 and RW_W < _ab(b)[1] < RW_W + 16.0]
_angW = np.degrees(np.arctan2(_eW[1], _eW[0]))


def _face_road(b):
    """前の列の家：いちばん道に近い辺を道と平行に回し、道の端から0.5 mに寄せる"""
    r = b.minimum_rotated_rectangle
    cs = np.array(r.exterior.coords)[:4]
    best = None
    for i in range(4):
        d = cs[(i + 1) % 4] - cs[i]
        ang = np.degrees(np.arctan2(d[1], d[0]))
        diff = (_angW - ang + 90) % 180 - 90
        if best is None or abs(diff) < abs(best):
            best = diff
    b2 = affinity.rotate(b, best, origin="centroid")
    bmin = min((np.array(p_) - SITE_C["NW"]) @ _oW for p_ in b2.exterior.coords)
    return affinity.translate(b2, *(-(bmin - (RW_W + 1.0)) * _oW))


_P_BLD = [_face_road(b) if any(b is x for x in _front) else b for b in _P_BLD]
# 三軒は突き出た木（西の折れ目と北の交差点の中ほど＝住宅とアパートの境）から北に並ぶ（ユーザー、10-24）
TREE_A = 0.5 * _LW
_f2 = [b for b in _P_BLD if -6.0 < _ab(b)[0] < 34.0 and RW_W < _ab(b)[1] < RW_W + 16.0]
_f2.sort(key=lambda b: _ab(b)[0])
_f2 = _f2[:3]
if _f2:
    _a0 = min(min((np.array(p_) - SITE_C["NW"]) @ _eW for p_ in b.exterior.coords) for b in _f2)
    _a1 = max(max((np.array(p_) - SITE_C["NW"]) @ _eW for p_ in b.exterior.coords) for b in _f2)
    _k = (TREE_A - 0.8 - 0.5) / (_a1 - _a0)
    _moved = []
    for b in _f2:
        ca = _ab(b)[0]
        _moved.append((b, affinity.translate(b, *((0.5 + (ca - _a0) * _k - (ca - _a0) - (_a0 - 0.0)) * _eW))))
    _P_BLD = [next((m for o, m in _moved if o is b), b) for b in _P_BLD]
    print(f"三軒：{_a0:.1f}〜{_a1:.1f} m → 0.5〜{TREE_A - 0.8:.1f} m（木はNWから{TREE_A:.1f} m）")
_front = []
BLDS = [b.buffer(0).difference(ROADS) for b in _P_BLD if not b.buffer(0).intersects(_SITE3)]
print(f"向かいの街区を道へ{_gap:.1f} m寄せ、前の列の家を道に向けた")


def _to_rot(g):
    if g.geom_type in ("MultiPolygon", "GeometryCollection"):
        return unary_union([_to_rot(p) for p in g.geoms if p.geom_type == "Polygon"])
    return Polygon(R3(np.array(g.exterior.coords)), [R3(np.array(r.coords)) for r in g.interiors])


SF(Polygon([(-90.0, -10.5), (-18.0, -9.5), (-18.0, -3.2), (QX1 + 20, -3.2), (QX1 + 20, -60.0), (-90.0, -60.0)]), "#E4EEF2", z=-0.5)   # 高野川（回した座標）
KMAP = json.load(open(os.path.join(HERE, "kadai_map.json"), encoding="utf-8"))
KCANAL = []
_eR = (SITE_C["S"] - SITE_C["E"]) / np.linalg.norm(SITE_C["S"] - SITE_C["E"])
_oR = np.array([-_eR[1], _eR[0]])
if _oR @ (SITE_C["E"] - SITE_C["NW"]) < 0:
    _oR = -_oR                                                                  # 川の側へ
for _ln in KMAP["lines"]:
    _L = np.array(_ln)
    _len = np.sum(np.linalg.norm(np.diff(_L, axis=0), axis=1))
    _Ls = np.array(LineString(_L).simplify(0.35).coords)
    _d = np.diff(_Ls, axis=0)
    _tn = _d[:-1, 0] * _d[1:, 1] - _d[:-1, 1] * _d[1:, 0]
    _sg = np.sign(_tn[np.abs(_tn) > 1e-4])
    _c = _L.mean(0)
    _zone = ((_c - SITE_C["E"]) @ _oR > 2.0) or ((_c - SITE_C["NW"]) @ _oN > 4.0)   # 川の側か、北の道の向こう
    _wavy = _zone and len(_sg) > 2 and np.sum(_sg[1:] != _sg[:-1]) >= 2          # 波線＝水（用水路・川岸）
    _q = xf(R3(_L))
    _qr = R3(_L)                                                               # 回した座標（m）
    _cr = _qr.mean(0)
    _dy = abs(_qr[-1, 1] - _qr[0, 1])
    _canal = (30.0 < _cr[0] < 58.0 and 55.0 < _cr[1] < 72.0 and not (_dy < 0.12 * _len))   # 北の用水路（波線の二本、ユーザー：強調する）
    if _canal:
        KCANAL.append(_q)
    if not (_canal or _wavy) and ((_c - SITE_C["NW"]) @ _oN > RW_N + 2.0):
        continue                                                                 # 北の道の向こう（大学の側）の線は描かない（ユーザーが描き足す）
    ax.plot(_q[:, 0], _q[:, 1], color="#1F6FB2" if _canal else ("#4F8DBF" if _wavy else "#505050"),
            lw=1.1 if _canal else (0.35 if _wavy else 0.3), zorder=6 if _canal else 1, solid_capstyle="round")
    _mk("c" if (_canal or _wavy) else "l")
# ---- 地面・外構・園庭（3dm）。色は塗り、線は輪郭
_rp_ = lambda L_: [o for o in objs if o["layer"].startswith(L_)]
def _sh(o):
    g_ = shape(o, "plan")
    return rot(g_) if g_ is not None else None
def _poly_of(o):
    """閉じた線は面に"""
    g_ = _sh(o)
    if g_ is not None and g_.geom_type == "LineString" and len(g_.coords) > 3 and np.allclose(g_.coords[0], g_.coords[-1], atol=0.05):
        return Polygon(g_.coords).buffer(0)
    return g_
_PARK_R = rot(Polygon(to_s(np.array(gc.PARK.exterior.coords))))
# ---- 建物：屋根伏せ（最新の3dm：屋根・屋根材型の太陽光・光の筋・越屋根）
def _U(pref):
    gs_ = [g_ for g_ in (_sh(o) for o in _rp_(pref)) if g_ is not None and g_.geom_type.endswith("Polygon")]
    return unary_union(gs_).buffer(0) if gs_ else None
R10, R20, R35 = _U("10_"), _U("20_"), _U("35_")
SOL, STR_ = unary_union([x for x in (_U("10p"), _U("20p")) if x is not None]), unary_union([x for x in (_U("10t"), _U("20t")) if x is not None])
LIDS = unary_union([x for x in (_U("50a"), _U("28_")) if x is not None]).buffer(0.05).buffer(-0.05)   # 二枚の蓋の継ぎ目の細い隙間を閉じる
LOUV = unary_union([x for x in (_U("50c"), _U("30_")) if x is not None])
# 園庭の小屋：屋根（「小屋の屋根（ひとつの屋根、南西に軒 1.5）」、高さ2.5より上）だけが見える。下のコンポストの枠は屋根の外の分
_HUT = unary_union([g_ for g_ in (_sh(o) for o in _rp_("93_") if o["V"][:, 2].min() > 2.0) if g_ is not None and g_.geom_type.endswith("Polygon")])
_CMP = unary_union([g_ for g_ in (_sh(o) for o in _rp_("93_") if o["V"][:, 2].max() < 1.0) if g_ is not None and g_.geom_type.endswith("Polygon")])
if not _CMP.is_empty:
    _CMP = _CMP.difference(_HUT)
    SF(_CMP, "#CDBFAA", z=0.95); SL(_CMP, "#8C7A66", 0.12, z=4.8)
SMALLR = unary_union([x for x in (_U("71_"), _HUT, _U("26_")) if x is not None and not x.is_empty])
ROOFALL = unary_union([x for x in (R10, R20, R35) if x is not None])
COVER = unary_union([ROOFALL, SMALLR]).buffer(0.02)
for o in _rp_("02_"):
    g_ = _sh(o); SF(g_, "#DCE8EE", z=0)
_rv2 = xf(R3(WT["river"]))
ax.plot(_rv2[:, 0], _rv2[:, 1], color="#5A93BF", lw=0.8, zorder=1, alpha=0.7); _mk("c")
for o in _rp_("01_"):                                    # 公園・駐車場
    g_ = _poly_of(o)
    if g_ is None:
        continue
    if g_.representative_point().distance(_PARK_R) >= 0.5:
        continue                                         # 01の駐車場の枠は初めの敷地のデータで、設計の車室（74）と合わない（ユーザー、10-25：影に見える）。描かない
    if g_.geom_type.endswith("Polygon"):
        SF(g_, "#E3ECD9", z=0.2)
    SL(g_, "#666666", 0.3, z=3)
SF(rot(GD["garden"]), "#DDE9CF", z=0.5)                  # 園庭（data/garden.json）
SF(rot(GD["shizu"]), "#D0E1C2", z=0.55)
SF(rot(GD["mound"]), "#CBDDB6", z=0.6)
SF(rot(GD["sand"]), "#EFE2B8", z=0.65); SL(rot(GD["sand"]), "#A89A70", 0.12, z=4)
SF(rot(GD["bowl"]), "#D6E4C6", z=0.65)
SF(rot(GD["willow"]), "#A9C78A", z=0.65)
SF(rot(GD["fountain"]), "#CFE3EF", z=0.65)
for L_, fc_ in (("62_", "#E2ECD4"), ("63_", "#EEE9DF"), ("64_", "#E8E1D4"), ("67_", "#E2ECD4")):
    for o in _rp_(L_):
        g_ = _sh(o)
        SF(g_, fc_, z=0.7); SL(g_, "#8C8C80", 0.12, z=4)
for o in _rp_("91_"):                                    # 等高線（0.2 mごと。築山がはっきり見えるように、0.4 mごとを太く。ユーザー 10-25夕）
    _zc = float(np.mean(o["V"][:, 2])) if len(o["V"]) else 0.0
    _ix = abs(((_zc - 0.1) / 0.4) - round((_zc - 0.1) / 0.4)) < 0.05
    SL(_sh(o), "#5F8049" if _ix else "#7E9A68", 0.5 if _ix else 0.3, z=4.95)
for o in _rp_("92_"):                                    # 水（小川・雨の川・噴水・水浴び場・溝）
    g_ = _sh(o)
    if g_ is not None:
        draw_shape(ax, g_, xf, fc="none", ec="#3E8CC4", lw=0.9 if g_.length > 20 else 0.4, z=5); _mk("c")
def _tree_g(o):
    """木：線は閉じた輪（樹冠）を面に。立体（幹と樹冠の箱）は箱に内接する円（平面の四角にしない）"""
    if o["kind"] == "solid" and o.get("prof") is None:
        V_ = R3(o["V"][:, :2])
        c_ = (V_.min(0) + V_.max(0)) / 2
        r_ = float(np.min(V_.max(0) - V_.min(0))) / 2
        return Point(c_).buffer(r_, 24) if r_ > 0.05 else None
    return _poly_of(o)
from shapely.geometry import Point
for L_ in ("94_", "77_", "79_"):                         # 木：樹冠の円（色は淡い緑、線は細く）と幹
    for o in _rp_(L_):
        g_ = _tree_g(o)
        if g_ is None:
            continue
        if g_.geom_type.endswith("Polygon") and g_.area > 1.5:
            SF(g_, "#A8C88A", z=0.9, alpha=0.45); SL(g_, "#7D9468", 0.1, z=4.5)
        elif g_.geom_type.endswith("Polygon"):
            SF(g_, "#6E5A44", z=4.6)
        elif g_.length < 0.05:                       # 幹（縦の線）は点
            SF(g_.buffer(0.25), "#6E5A44", z=4.6)
        else:
            SL(g_, "#7D9468", 0.1, z=4.5)
for L_, ec_, lw_ in (("60_", "#444444", 0.3), ("70_", "#555555", 0.3), ("72_", "#555555", 0.2),
                     ("74_", "#666666", 0.2), ("75_", "#777777", 0.15), ("76_", "#888888", 0.15), ("78_", "#888888", 0.15),
                     ("95_", "#8C8C80", 0.15), ("96_", "#8C8C80", 0.15), ("97_", "#6E7E5E", 0.2)):
    for o in _rp_(L_):
        SL(_sh(o), ec_, lw_, z=4.8)
# ムベのアーチ（73：小径の上のアーチの棚）。棚のある範囲全体を淡い緑に塗るだけ（ユーザー 10-25夜：線や点は要らない）
_g73a = [g_ for g_ in (_sh(o) for o in _rp_("73_")) if g_ is not None]
if _g73a:
    _ARCH = unary_union([g_.buffer(0.35) for g_ in _g73a]).buffer(0.9).buffer(-0.9)
    SF(_ARCH, "#C9DFB0", z=0.9)
# 公園からの入口（66：木戸と背くらべの柱）。扉は太く、開く向きの弧
for o in _rp_("66_"):
    g_ = _sh(o)
    if g_ is None:
        continue
    SF(g_, "#4A3A2A", z=5.4); SL(g_, "#2E241A", 0.5, z=5.4, hide=False)
    if o["kind"] == "mesh":
        _mr = np.array(g_.minimum_rotated_rectangle.exterior.coords)[:4]
        _ed = [(_mr[k_], _mr[(k_ + 1) % 4]) for k_ in range(4)]
        _a, _b = max(_ed, key=lambda e_: np.linalg.norm(e_[1] - e_[0]))      # 扉の長い辺：吊元 _a、先 _b
        _rr_ = np.linalg.norm(_b - _a); _t0 = np.arctan2(*(_b - _a)[::-1])
        _arc = LineString([_a + _rr_ * np.array([np.cos(_t0 + d_), np.sin(_t0 + d_)]) for d_ in np.linspace(0, np.pi / 2, 12)])
        SL(_arc, "#2E241A", 0.2, z=5.4, ls=(0, (1.5, 1.0)), hide=False)
# 駐車場（74の車室を囲む舗装、道路の側の敷地の境まで）を灰色に。バンプは横断歩道のような縞（ユーザー 10-25夕）
# 駐車・駐輪のために確保する場所全体を灰色に（ユーザー 10-25夜、塗る範囲の図をもらった）：敷地の西の境から、ひろば・小径・ムベのアーチ・屋根までの、
# 公園の北で、職員の駐輪の北の端までの範囲。西の道沿い1 mは歩道で白。公園ぎわの駐輪が歩道にはみ出している（アプローチ係に依頼）
_SITEP = Polygon(R3(np.array([SITE_C[k] for k in ("N", "E", "S", "SW", "NW")])))
_A_ = R3(SITE_C["SW"])[0]; _B_ = R3(SITE_C["NW"])[0]; _tW = (_B_ - _A_) / np.linalg.norm(_B_ - _A_)
_nW = np.array([-_tW[1], _tW[0]])
_cells = [x for x in (_poly_of(o) for o in _rp_("74_") if o["kind"] == "curve") if x is not None and x.geom_type == "Polygon" and x.area > 0.3]
_tof = lambda g_: [(np.array(c_) - _A_) @ _tW for c_ in g_.exterior.coords]
_tmax = max(max(_tof(c_)) for c_ in _cells) + 0.4
_big76 = [x for x in (_poly_of(o) for o in _rp_("76_") if o["kind"] == "curve") if x is not None and x.geom_type == "Polygon" and x.area > 20]
_cut = unary_union([x for x in [_PARK_R.buffer(0.02), ROOFALL, SMALLR, _ARCH if _g73a else None] + _big76 if x is not None])
_slab = Polygon([_A_ - _tW * 5 - _nW * 50, _A_ + _tW * _tmax - _nW * 50, _A_ + _tW * _tmax + _nW * 50, _A_ - _tW * 5 + _nW * 50])
_Z = _SITEP.intersection(_slab).difference(_cut)
_Z = unary_union([z_ for z_ in (_Z.geoms if hasattr(_Z, "geoms") else [_Z]) if any(z_.intersects(c_) for c_ in _cells)])
_Z = _Z.difference(LineString([_A_ - _tW * 10, _B_ + _tW * 10]).buffer(1.0, cap_style=2))   # 西の道沿い1 mは歩道（白、ユーザー 10-25夜。バンプもこの中）
SF(_Z, "#D8D8D4", z=0.75)
for o in _rp_("74_"):
    if o["kind"] != "solid":
        continue
    g_ = _sh(o)
    if g_ is None or g_.area < 1.0:
        continue
    _mr = np.array(g_.minimum_rotated_rectangle.exterior.coords)[:4]
    _e1, _e2 = _mr[1] - _mr[0], _mr[2] - _mr[1]
    if np.linalg.norm(_e1) < np.linalg.norm(_e2):
        _o_, _L_, _S_ = _mr[0], _e2, _e1                     # 長い辺 _L_ に沿って縞、縞は短い辺 _S_ の向き
    else:
        _o_ = _mr[0]; _L_, _S_ = _e1, _e2
    SF(g_, "#8E8E8A", z=0.8)
    _n_ = int(np.linalg.norm(_L_) / 0.45)
    for k_ in range(_n_):
        if k_ % 2:
            continue
        a0_, a1_ = k_ / _n_, (k_ + 1) / _n_
        SF(Polygon([_o_ + a0_ * _L_, _o_ + a1_ * _L_, _o_ + a1_ * _L_ + _S_, _o_ + a0_ * _L_ + _S_]), "#F4F4F2", z=0.81)
    SL(g_, "#666666", 0.15, z=4.8)
for o in _rp_("00_"):                                    # 敷地の境（一点鎖線）
    if o["kind"] == "curve":
        SL(_sh(o), INK, 0.5, z=12, ls=(0, (6, 2, 1, 2)))
SF(R10, "#E7E4DE", z=6); SF(R35, "#E7E4DE", z=6); SF(R20, "#E2DED7", z=6.2)
SF(SOL, "#4B525A", z=6.5)                                 # 屋根材型の太陽光
SF(STR_, "#F8F6EF", z=6.6)                                # 光の筋（乳白ガラス）
SF(LIDS, "#E6EFF3", z=6.7); SF(SMALLR, "#DCD6CB", z=6.2)
# 越屋根の蓋（50a・28、屋根より高い）は光の筋・太陽光・屋根の縁の上にかかる：蓋の下になる線は消す（ユーザー 10-25夕：筋が蓋の上に見えた。
# 色の層では蓋の塗りが上だが、線の層は色の層の上に重なるので、線を蓋で切らないと筋の縁が蓋の上に出る）
_LID = LIDS.buffer(0.01) if LIDS is not None and not LIDS.is_empty else None
_cut = (lambda g_: g_.boundary.difference(_LID) if _LID is not None else g_) if True else None
SL(_cut(SOL), "#2F3338", 0.1, z=13, hide=False); SL(_cut(STR_), "#9A958A", 0.1, z=13, hide=False); SL(LOUV, "#B5B5B5", 0.06, z=13, hide=False); SL(LIDS, "#7A8A92", 0.15, z=13, hide=False)
SL(_cut(R10), "#555555", 0.15, z=13.5, hide=False); SL(_cut(R20), "#555555", 0.15, z=13.5, hide=False)
SL(unary_union([ROOFALL, LIDS]) if LIDS is not None else ROOFALL, INK, 0.55, z=14, hide=False)   # 建物の外形（太く、蓋の出も含む）
SL(SMALLR, "#444444", 0.3, z=14, hide=False)
_GR = affinity.rotate(GARDEN_X, GJ["VIEW_ROT"]["deg"], origin=(0, 0)).bounds          # 5枚目で園庭の図（garden01）を切り抜く大きさ
GVX0, GVY0, GVX1, GVY1 = _GR[0] - 6.0, _GR[1] - 6.0, _GR[2] + 3.0, _GR[3] + 3.0
_gw, _gh = (GVX1 - GVX0) * 5, (GVY1 - GVY0) * 5
# 雨落ち（本館の軒の下の石の帯。3dmに無いので data/garden.json の線）
# 雨の川（決定事項_園庭：本館の雨は樋なしで東の軒から落とし、真下の雨落ちの溝 幅0.5・玉石 を本館に沿って南へ、南東の角から護岸のもう一本の溝で高野川へ）
_am = rot(GD["amaochi"])
_amc = np.array(_am.coords)
if _amc[0][1] < _amc[-1][1]:
    _amc = _amc[::-1]                                     # 北から南へ（流れの向き）
# 溝は軒先の真下の外（0.5の溝の中心を軒の線から0.3外へ）：屋根の塗りに隠れないように
for _sd in (0.3, -0.3):
    _off = LineString(_amc).offset_curve(_sd)
    if not ROOFALL.buffer(0.05).contains(Point(_off.interpolate(0.5, normalized=True))):
        break
_amc = np.array(_off.coords)
if _amc[0][1] < _amc[-1][1]:
    _amc = _amc[::-1]
_drops = []
for o in _rp_("92_"):
    g_ = _sh(o)
    if o["kind"] == "curve" and g_ is not None and g_.length < 0.5 and float(o["V"][:, 2].max()) > -1.0:
        _drops.append(np.array(g_.centroid.coords[0]))
_stream = unary_union([g_ for g_ in (_sh(o) for o in _rp_("92_") if o["kind"] == "mesh") if g_ is not None and g_.area > 5])
if _drops:
    _dp = max(_drops, key=lambda d_: Point(d_).distance(_stream))      # 小川の落ち口でない方＝雨の溝の落ち口
    _rain = LineString(list(map(tuple, _amc)) + [tuple(_dp)])
else:
    _rain = LineString(_amc)
SF(LineString(_amc).buffer(0.25, cap_style=2), "#C9E0EF", z=0.85)                      # 溝（玉石）
SL(LineString(_amc).buffer(0.25, cap_style=2), "#7FA9C6", 0.12, z=4.9, hide=False)
SL(_rain, "#2F7FBF", 0.6, z=4.95, ls=(0, (3, 1.5)), hide=False)                       # 雨の道（破線）
for d_ in np.arange(6.0, _rain.length - 1.0, 9.0):                                      # 流れの向きの矢印
    p0_ = np.array(_rain.interpolate(d_).coords[0]); p1_ = np.array(_rain.interpolate(d_ + 0.9).coords[0])
    v_ = (p1_ - p0_) / max(np.linalg.norm(p1_ - p0_), 1e-6); w_ = np.array([-v_[1], v_[0]])
    SF(Polygon([p1_, p0_ + 0.45 * w_, p0_ - 0.45 * w_]), "#2F7FBF", z=0.95)
_RAIN_LAB = np.array(_rain.interpolate(0.55 * _rain.length).coords[0])
for a_ in ax.patches[st:] + ax.lines[stl:] + ax.collections:
    a_.set_clip_path(rp)
# 周りの注記（西の道路・向かいの住宅・突き出た木・大学・用水・高野川・公園）
_u = (SITE_C["SW"] - SITE_C["NW"]) / np.linalg.norm(SITE_C["SW"] - SITE_C["NW"])
_n = np.array([-_u[1], _u[0]])
if _n @ (SITE_C["NW"] - SITE_C["E"]) < 0:
    _n = -_n                                                                  # 敷地の外（西）へ向く
_tree = SITE_C["NW"] + TREE_A * _u + (RW_W + 1.0) * _n
_tq = xf(R3(_tree))[0]
_tc = xf(R3(_tree - 2.0 * _n))[0]                                          # 枝は道の上へ張り出す（ユーザー：地図に出るくらい）
_mk("l")
SITE_LIVE[0] = ax                                                          # ここから配置図の文字・注の線・突き出た木は部品に（01cに焼き込まない）
SITEPARTS.append(dict(kind="circle", cx=_tc[0], cy=_tc[1], r=3.6 * 5, fill="#9DBB82", alpha=0.6, stroke="#5E7F45", lw=0.4,
                      group="site.g.tree", id="tree.canopy", name="突き出た木　枝"))
SITEPARTS.append(dict(kind="circle", cx=_tq[0], cy=_tq[1], r=1.4, fill="#5E7F45", alpha=1.0, stroke=None, lw=0,
                      group="site.g.tree", id="tree.trunk", name="突き出た木　幹"))
lab(ax, xf, _tree, "突き出た木（住宅とアパートの境）", (sx + 3 - _tq[0], -12), ha="left")
lab(ax, xf, SITE_C["NW"] + 30.0 * _u + 3.0 * _n, "西の道路（公園の角で折れて川の橋へ）", (-4, -6), ha="right")
_hq = SITE_C["NW"] + 13.0 * _u + (RW_W + 4.0) * _n
lab(ax, xf, _hq, "向かいの住宅（木から北の三軒）", (sx + 3 - xf(R3(_hq))[0][0], 14), ha="left")
lab(ax, xf, R3inv([-23.5, -5.0])[0], "二本の橋（車・人）へ", (4, -5), ha="left")
_nwmid = (SITE_C["N"] + SITE_C["NW"]) / 2
_out = -(SITE_C["E"] - SITE_C["N"]) / np.linalg.norm(SITE_C["E"] - SITE_C["N"])
_uq = SITE_C["NW"] + 0.02 * _LN * _eN + (RW_N + 6.0) * _oN               # 大学の敷地の中（南の線の上に文字を置かない）
lab(ax, xf, _uq, "北の道の向こうは京都工芸繊維大学", (-48, (sy + sh - 5) - xf(R3(_uq))[0][1]), ha="right")
lab(ax, xf, R3inv([14.0, -5.6])[0], "高野川", (0, 0), size=3.0, color="#2F6FA0", bold=True)
lab(ax, xf, np.array(gc.PARK.centroid.coords[0]), "小竹薮公園", (0, 0), ha="center", lead=False)
# 建物と園庭の名前（部屋の名前・スパンの番号・園庭のチャットの記号は描かない、ユーザー 10-25）
_RS = lambda P: np.c_[np.atleast_2d(P)[:, 0] * np.cos(_rr) - np.atleast_2d(P)[:, 1] * np.sin(_rr), np.atleast_2d(P)[:, 0] * np.sin(_rr) + np.atleast_2d(P)[:, 1] * np.cos(_rr)]
def _zl(g_s, text, dxy=(0, 0), size=3.0, color="#3F5F2F", bold=True):
    q = xf(_RS(np.array(g_s.representative_point().coords[0])))[0] + np.array(dxy)
    T(ax, q[0], q[1], text, size, color, ha="center", va="center", bold=bold)
def _zl3(pref, text, dxy=(0, 0), size=3.0, color=INK, bold=True):
    U_ = _U(pref)
    q = xf(np.array(U_.representative_point().coords))[0] + np.array(dxy)
    T(ax, q[0], q[1], text, size, color, ha="center", va="center", bold=bold)
_zl3("31_", "遊戯室", size=3.0, color="white")          # 屋根（太陽光）の上なので白
_zl3("23_", "西館（2階建て）", size=3.0, color="white")
_zl3("12_", "本館（平屋）", (8, 6), size=3.2, color="white")
_zl(GD["north"], "だいさんかく", (6, -4), size=3.4)
_zl(GD["shizu"], "しずかのもり", (-4, 0), size=3.0)
_stl0 = gc.XS([tuple(p) for p in GJ["STREAM"]["line"]])[0]
_q0 = xf(R3(_stl0))[0]
T(ax, _q0[0] - 4, _q0[1] - 10, "北のもり", 3.0, "#3F5F2F", ha="right", va="center", bold=True)
_car = [x for x in (_poly_of(o) for o in _rp_("74_")) if x is not None and x.geom_type.endswith("Polygon") and x.area > 8]   # 車室
if _car:
    _cu = unary_union(_car)
    q = xf(np.array(_cu.centroid.coords))[0]
    T(ax, q[0], q[1], "駐車場", 2.8, ha="center", va="center", bold=True)
_mk("t")
# 方位は「太陽の線」の丸の中の北の矢印に（ユーザー、10-26夜）。前の矢印とNは外した
_mk("t")
lab(ax, xf, SITE_C["NW"] + 0.12 * _LN * _eN + 3.5 * _oN, "北の道（車を止めて建物と庭の手入れ）", (0, 0), size=2.6)
# 北の用水路は尾を描かず、窓の北の端から入ってくる矢印と名前だけ（ユーザー、10-26夕）
_yh = xf(np.array([[33.5, min(58.8, VY1 - 3.0)]]))[0]; _yt = xf(np.array([[33.5, VY1 - 0.3]]))[0]
# 矢印も配置図に焼き込まず、文字と一つのグループの部品に（ユーザー、10-27：配置図は純粋に、書き込むものは別のオブジェクト）
SITEPARTS.append(dict(kind="line", id="site.l.用水路の矢印", pts=[tuple(_yt), tuple(_yh)], color="#1F6FB2", lw=1.2, arrow=2.4,
                      group="site.g.用水路", name="用水路の矢印"))
T(ax, _yt[0] - 2.5, _yt[1] - 3.5, "用水路（北から来て、暗渠で敷地の北の角へ）", 2.6, "#1F6FB2", ha="right", group="site.g.用水路")
_g66 = unary_union([g_ for g_ in (_sh(o) for o in _rp_("66_")) if g_ is not None])
if not _g66.is_empty:
    lab(ax, xf, R3inv(np.array(_g66.centroid.coords))[0], "公園からの入口（木戸）", (-25, 2), size=2.6, color="#4A3A2A", ha="right", bold=True)
_g73 = [g_ for g_ in (_sh(o) for o in _rp_("73_") if o["kind"] == "curve") if g_ is not None and g_.length > 9.5]
if _g73:
    lab(ax, xf, R3inv(np.array(_g73[0].interpolate(0.5, normalized=True).coords))[0], "ムベのアーチ", (-60, -6), size=2.6, color="#7A5530", ha="right", bold=True)
lab(ax, xf, R3inv(_RAIN_LAB)[0], "雨の川（樋なしで軒から落ちた雨を、雨落ちの溝から高野川へ）", (8, -10), size=2.6, color="#2F7FBF", ha="left")
_mk("t")
# ---- 重ねる図（ユーザー、10-26）：夏の夜の風・比叡への視線（01d）と太陽の通り道（01e）。どちらも配置図と同じ大きさの透明な層
SGRP["o"] = []; SGRP["s"] = []
_mk("t")                                                   # ここまでの残りを文字の組に閉じる
_rot_cw = lambda v, deg: np.array([v[0] * np.cos(np.radians(deg)) + v[1] * np.sin(np.radians(deg)),
                                   -v[0] * np.sin(np.radians(deg)) + v[1] * np.cos(np.radians(deg))])   # 北から時計回りに deg 度
_rU = lambda pre: rot(unary_union([g for ln, k, g in plan_items if ln.startswith(pre)]))
_HALLc = np.array(_rU("59_1F_ホール").centroid.coords[0])
_ENGc = np.array(_rU("14_").centroid.coords[0])
_FUKIc = np.array(_rU("59_1F_西吹き抜け").centroid.coords[0])
_MOUc = np.array(rot(GD["mound"]).centroid.coords[0])
_GARc = np.array(rot(GD["garden"]).centroid.coords[0])
_pE = R3(SITE_C["E"])[0]
def _chaikin(P, n=3):
    P = np.asarray(P, float)
    for _ in range(n):
        Q = [P[0]]
        for a_, b_ in zip(P[:-1], P[1:]):
            Q += [0.75 * a_ + 0.25 * b_, 0.25 * a_ + 0.75 * b_]
        Q.append(P[-1]); P = np.array(Q)
    return P
# 夏の夜の風：高野川の谷を下りてくる風（北東から川に沿って）→ 園庭を渡って縁側 → 越屋根から西へ。太く柔らかく透ける矢印
_out_ = (_ENGc - _FUKIc) / np.linalg.norm(_ENGc - _FUKIc)       # 建物の内（越屋根）→ 外（園庭）
_ax_ = np.array([-_out_[1], _out_[0]])
if _ax_[1] < 0:
    _ax_ = -_ax_                                                     # 縁側に沿って北東へ
# 風は高野川から吹いてきて本館の南の端にぶつかり、北東へ向きを変えて縁側に沿い、建物に入って越屋根から抜ける（ユーザー、10-26 1:02）
_eg = _rU("14_")
_egp = np.array(_eg.exterior.coords) if _eg.geom_type == "Polygon" else np.vstack([np.array(g_.exterior.coords) for g_ in _eg.geoms])
_po = _egp @ _out_
_east = _egp[_po >= _po.max() - 3.0]                             # 東の縁側（外の側の縁）の点だけ
_Ssouth = _east[np.argmin(_east @ _ax_)]                         # 東の縁側の南の端（南の縁側の回り込みは除く）
_din = np.linalg.norm(_ENGc - _FUKIc)
_fo = float((_FUKIc - _Ssouth) @ _out_)                         # 越屋根の線（縁側の南の端から内へ）
_ry = _Ssouth[1] - 3.0                                           # 川の上（敷地の南の辺の少し下）
_wp = _chaikin([np.array([_pE[0] + 6.0, _ry]), np.array([_pE[0] - 14.0, _ry]),        # 右（高野川の上流）から川に沿って流れてくる
                _Ssouth + _out_ * 4.0 + np.array([3.0, -2.5]),                        # 本館の南の端にぶつかる
                _Ssouth + _out_ * 2.5 + _ax_ * 5.0, _Ssouth + _out_ * 1.5 + _ax_ * 14.0,  # 北東へ向きを変えて縁側に沿う
                _Ssouth + _ax_ * 21.0 - _out_ * 2.0, _Ssouth + _ax_ * 24.0 + _out_ * _fo,  # 建物に入って越屋根へ
                _Ssouth + _ax_ * 25.0 + _out_ * (_fo - 6.0)])
_L = LineString(_wp); _N_ = 80
_pts = np.array([_L.interpolate(t_, normalized=True).coords[0] for t_ in np.linspace(0, 0.9, _N_)])
_tip = np.array(_L.interpolate(1.0, normalized=True).coords[0])
_lft, _rgt = [], []
for k_, p_ in enumerate(_pts):
    d_ = _pts[min(k_ + 1, _N_ - 1)] - _pts[max(k_ - 1, 0)]; d_ /= np.linalg.norm(d_)
    n_ = np.array([-d_[1], d_[0]]); hw = 1.6 - 0.8 * k_ / (_N_ - 1)   # 幅は前の半分（ユーザー、10-26）
    _lft.append(p_ + n_ * hw); _rgt.append(p_ - n_ * hw)
_d1 = _pts[-1] - _pts[-2]; _d1 /= np.linalg.norm(_d1); _n1 = np.array([-_d1[1], _d1[0]])
_head = [_pts[-1] + _n1 * 1.6, _tip, _pts[-1] - _n1 * 1.6]
_WIND = Polygon(np.vstack([_lft, _head, _rgt[::-1]])).buffer(0.4).buffer(-0.4)
WIND_BY_USER = True                                            # 風の矢印は木田さんがIllustratorで描く（10-26 1:45）。素材には描かない
if not WIND_BY_USER:
    draw_shape(ax, _WIND, xf, fc="#8EC3E6", ec="none", lw=0, z=20)
    ax.patches[-1].set_alpha(0.45)
_mk("o")
_wl = xf(np.array([_wp[0] + np.array([-1.0, 3.0])]))[0]
T(ax, _wl[0], _wl[1], "夏の夜の風（高野川の谷を下りる風）", 2.8, "#3A7FB5", bold=True, ha="right")
# 比叡への視線：ホール → 築山の頂 → 比叡山（大比叡 北緯35.0670° 東経135.8344°、敷地 35.0546° 135.7905° から方位約71°、約4.2 km）
_dn = (35.0670 - 35.0546) * 111.0; _de = (135.8344 - 135.7905) * 111.32 * np.cos(np.radians(35.06))
_BRG = np.degrees(np.arctan2(_de, _dn)); _DIST = np.hypot(_dn, _de)
_hv = _rot_cw(_nv, _BRG)                                   # 配置図の上での比叡の向き
_win = Polygon([(VX0, VY0), (VX1, VY0), (VX1, VY1), (VX0, VY1)]).buffer(-1.5)
_far = LineString([_MOUc, _MOUc + _hv * 200]).intersection(_win)
_sl = [tuple(_HALLc), tuple(_MOUc), tuple(np.array(_far.coords)[-1])]
HIEI_ON = False                                          # 比叡への視線の矢印は外す（ユーザー、10-27）
if HIEI_ON:
    _q = xf(np.array(_sl))
    ax.plot(_q[:, 0], _q[:, 1], color="#7A5A9A", lw=0.9, ls=(0, (4, 2.5)), zorder=21, solid_capstyle="round")
    ax.annotate("", xy=tuple(_q[-1]), xytext=tuple(_q[-1] - (_q[-1] - _q[-2]) / np.linalg.norm(_q[-1] - _q[-2]) * 5),
                arrowprops=dict(arrowstyle="-|>", lw=0.9, color="#7A5A9A"), zorder=21)
    for _qq in _q[:2]:
        ax.add_patch(plt.Circle(tuple(_qq), 0.9, fc="#7A5A9A", ec="none", zorder=21))
    _mk("o")
    T(ax, _q[-1][0] - 2, _q[-1][1] + 3, f"比叡山へ　約{_DIST:.0f} km", 2.8, "#5E4380", bold=True, ha="right")
    T(ax, (_q[0][0] + _q[1][0]) / 2 + 2, (_q[0][1] + _q[1][1]) / 2 - 4, "ホールから築山の頂の向こうに比叡", 2.4, "#5E4380")
# 太陽の通り道（北緯35.05°、大気差なし：cos A＝sin δ／cos φ）。配置図の左上の空きに、配置図と同じ向きの方位円
SUN_ON = False                                           # 太陽の通り道は外す（ユーザー、10-26 9:50：前に自分で作ったものを使う）。素材01eは空のまま残す
if SUN_ON:
    _phi = 35.05; _dl = 23.44
    _Asr = np.degrees(np.arccos(np.sin(np.radians(_dl)) / np.cos(np.radians(_phi))))     # 夏至の日の出（北から時計回り）
    _Awr = 180 - _Asr
    _alt_s, _alt_w = 90 - _phi + _dl, 90 - _phi - _dl
    _SC0 = np.array([VX0 + 19.0, VY1 - 19.0]); _SR = 6.5      # 中心と半径（m）
    _c0 = xf(np.array([_SC0]))[0]; _k = 5.0
    ax.add_patch(plt.Circle(tuple(_c0), _SR * _k + 6, fc="white", ec="none", alpha=0.85, zorder=19))
    ax.add_patch(plt.Circle(tuple(_c0), _SR * _k, fc="none", ec="#888888", lw=0.4, zorder=20))
    for _deg in range(0, 360, 30):
        _v = _rot_cw(_nv, _deg)
        ax.plot([_c0[0] + _v[0] * _SR * _k * 0.92, _c0[0] + _v[0] * _SR * _k], [_c0[1] + _v[1] * _SR * _k * 0.92, _c0[1] + _v[1] * _SR * _k], color="#888888", lw=0.4, zorder=20)
    for _deg, _col in ((_Asr, "#E08A2E"), (360 - _Asr, "#E08A2E"), (_Awr, "#4F78B0"), (360 - _Awr, "#4F78B0")):
        _v = _rot_cw(_nv, _deg)
        ax.annotate("", xy=(_c0[0] + _v[0] * _SR * _k, _c0[1] + _v[1] * _SR * _k), xytext=tuple(_c0),
                    arrowprops=dict(arrowstyle="-|>", lw=1.0, color=_col), zorder=21)
    _v = _rot_cw(_nv, 0)
    ax.plot([_c0[0], _c0[0] + _v[0] * _SR * _k], [_c0[1], _c0[1] + _v[1] * _SR * _k], color=INK, lw=0.5, zorder=21)
    ax.add_patch(plt.Circle(tuple(_c0), 0.8, fc=INK, ec="none", zorder=22))
    _mk("s")
    _SOFF = _SR * _k + 4
    for _deg, _txt, _col in ((_Asr, f"夏至の日の出 {_Asr:.0f}°", "#B8661A"), (360 - _Asr, f"夏至の日の入り {360 - _Asr:.0f}°", "#B8661A"),
                             (_Awr, f"冬至の日の出 {_Awr:.0f}°", "#3A5F94"), (360 - _Awr, f"冬至の日の入り {360 - _Awr:.0f}°", "#3A5F94")):
        _v = _rot_cw(_nv, _deg); _pp = _c0 + _v * _SOFF
        T(ax, _pp[0], _pp[1], _txt, 2.3, _col, ha="left" if _v[0] >= 0 else "right", va="center")
    _vn = _c0 + _nv * (_SR * _k + 3.5)
    T(ax, _vn[0], _vn[1], "N", 2.6, INK, bold=True, ha="center", va="center")
    T(ax, _c0[0] - _SR * _k - 4, _c0[1] + _SR * _k + 8, "太陽の通り道（京都、北緯35°）", 2.8, INK, bold=True)
    T(ax, _c0[0] - _SR * _k - 4, _c0[1] - _SR * _k - 9, f"南中の高さ　夏至 {_alt_s:.0f}°・冬至 {_alt_w:.1f}°", 2.4, INK)
_mk("t")
SITE_LIVE[0] = None
# 文字に入った引き出し線（lab の線と点）は文字の組に入れたまま（文字と一緒に動かす）
_SITE_PDF = {}
for gr, nm in (("l", "線"), ("c", "色"), ("t", "文字"), ("o", "風と視線"), ("s", "太陽")):
    allart = SGRP["l"] + SGRP["c"] + SGRP["t"] + SGRP["o"] + SGRP["s"]
    for a_ in allart:
        a_.set_visible(a_ in SGRP[gr])
    fn_ = os.path.join(OUT, f"_site_{gr}.pdf")
    figS.savefig(fn_, transparent=True)
    _SITE_PDF[gr] = fn_
plt.close(figS)
ax, fig = _ax_page, _fig_page
# 線と色は、更新係が3dmから自動で描く配置図（drawings/sodachiya_siteplan_1-200_線・_色.pdf、ユーザー 10-26：正しさと自動の更新を優先）に差し替える。
# 3dmのxy（m）→ 向こうの紙のmm（…_xform.json）と、こちらの紙のmm（xf(R3(…))）で、二つの紙の位置のずれを求めて、A1の紙に置き直す
_SPD = os.environ.get("SODACHIYA_SITEPLAN_DIR", os.path.join(ROOT, "drawings"))
_SPB = os.path.join(_SPD, "sodachiya_siteplan_1-200")
SITE_FROM_UPD = all(os.path.exists(_SPB + x_) for x_ in ("_線.pdf", "_色.pdf", "_xform.json"))
if SITE_FROM_UPD:
    _XJ = json.load(open(_SPB + "_xform.json", encoding="utf-8"))
    _thr = lambda P: np.array([_XJ["a"] * P[0] + _XJ["b"] * P[1] + _XJ["c"], _XJ["d"] * P[0] + _XJ["e"] * P[1] + _XJ["f"]])
    _our = lambda P: (lambda q: np.array([q[0], H - q[1]]))(xf(R3(np.array(P)))[0])
    _P1, _P2 = SITE_C["S"], SITE_C["N"]
    _dv = (_our(_P2) - _our(_P1)) - (_thr(_P2) - _thr(_P1))
    if np.abs(_dv).max() > 0.3:
        print("配置図：更新係の配置図と向き・縮尺が合わない（", np.round(_dv, 2), "mm）。こちらの描き方のまま")
        SITE_FROM_UPD = False
if SITE_FROM_UPD:
    _off = _our(_P1) - _thr(_P1)                                  # 向こうの紙をこちらの紙のどこに置くか（左上から mm）
    _pw, _ph = _XJ["paper_mm"]
    _ia = (_off[0] + 10, _off[1] + 10, _off[0] + _pw - 10, _off[1] + _ph - 10)      # 向こうの図の描いてある範囲（紙の縁から10 mm内、ここに枠の線がある）
    _ytl = lambda yr: H - (sy + (yr - VY0) * 5)                                     # 回した座標のy（m）→ こちらの紙の上からmm
    _yr_of = lambda ytl: VY0 + ((H - ytl) - sy) / 5
    _YW = _yr_of(_ia[3])                                                            # 向こうの図の南の端＝高野川の水際（回した座標）
    _P = lambda xy: [fitz.Point(u_ * MM, (H - v_) * MM) for u_, v_ in xf(np.asarray(xy, float))]
    def _fillg(pg_, g_, fc, ec=None, w=0.0, op=1.0):
        for q_ in getattr(g_, "geoms", [g_]):
            if q_.geom_type != "Polygon" or q_.is_empty: continue
            sh_ = pg_.new_shape(); sh_.draw_polyline(_P(q_.exterior.coords))
            for r_ in q_.interiors: sh_.draw_polyline(_P(r_.coords))
            sh_.finish(color=ec, fill=fc, width=w, closePath=True, even_odd=True, fill_opacity=op); sh_.commit()
    _hx = lambda c_: tuple(int(c_[k:k + 2], 16) / 255 for k in (1, 3, 5))
    _rng = np.random.default_rng(7)
    # 河原（ユーザー、10-26夜：もっと河原らしく）：水際をゆるく揺らし、水際に丸石の帯、河川敷に草の印
    _BED = unary_union([_sh(o) for o in _rp_("02_") if o.get("V") is not None and o["V"][:, 2].max() - o["V"][:, 2].min() < 0.8
                        and -5.7 < o["V"][:, 2].max() < -4.0 and _sh(o) is not None]).buffer(0.02).buffer(-0.02)   # 河川敷（草の平ら）
    _xs = np.linspace(BX0, BX1, 240)
    def _bot(x_):                                 # 河川敷の南の端（水際）
        q_ = LineString([(x_, BY0 - 5), (x_, 0)]).intersection(_BED)
        return q_.bounds[1] if not q_.is_empty else np.nan
    _yb = np.array([_bot(x_) for x_ in _xs])
    _yb = np.where(np.isnan(_yb), np.nanmin(_yb), _yb)
    _yb = np.convolve(np.pad(_yb, 6, mode="edge"), np.ones(13) / 13, mode="valid")      # 片の段をならす
    _wv = _yb + 0.35 * np.sin(_xs * 0.9) + 0.25 * np.sin(_xs * 2.3 + 1.0) + 0.15
    _WATER = Polygon(list(zip(_xs, _wv)) + [(BX1, BY0 - 1), (BX0, BY0 - 1)])
    _RDR = unary_union([rot(g) for ln, g in CTX if ln.startswith("03_") and g is not None]).buffer(0)
    _BRIDGE = _RDR.intersection(Polygon([(BX0, BY0 - 1), (BX1, BY0 - 1), (BX1, _YW + 1), (BX0, _YW + 1)]))
    _STONES = []
    for x_ in np.arange(BX0, BX1, 0.42):
        for k_ in range(2):
            xx = x_ + _rng.uniform(-0.2, 0.2); yy = np.interp(xx, _xs, _wv) + _rng.uniform(0.1, 1.3) * (1 if k_ else 0.55)
            if not _BRIDGE.contains(Point(xx, yy)):
                _STONES.append((xx, yy, _rng.uniform(0.07, 0.17), _rng.uniform(0, 180)))
    _TUFTS = []
    for x_ in np.arange(BX0 + 0.8, BX1, 2.6):
        for y_ in np.arange(float(np.min(_yb)) + 2.2, -6.0, 2.4):
            xx, yy = x_ + _rng.uniform(-0.9, 0.9), y_ + _rng.uniform(-0.6, 0.6)
            if not _BRIDGE.contains(Point(xx, yy)) and _BED.buffer(-0.4).contains(Point(xx, yy)) and yy > np.interp(xx, _xs, _wv) + 1.6:
                _TUFTS.append((xx, yy))
    # みなみのさんかく・砂場・水・小屋の屋根（ユーザー、10-26夜：更新係の図に無い色と屋根を足す）
    _pg_ = lambda o: (lambda g_: g_ if g_ is not None and g_.geom_type.endswith("Polygon") else None)(_poly_of(o))
    _uu = lambda gs: unary_union([g for g in gs if g is not None]).buffer(0) if any(g is not None for g in gs) else Polygon()
    _MINAMI = _uu([_pg_(o) for o in _rp_("62_")]).difference(COVER)                  # 屋根の下は塗らない
    _SANDP = _uu([_pg_(o) for o in _rp_("78_") if o["kind"] == "solid" and abs(o["V"][:, 2].max() + 0.15) < 0.02]
                 + [_pg_(o) for o in _rp_("95_") if ("砂場" in o["name"] or "粒の遊び場" in o["name"])])
    _WATERP = _uu([_pg_(o) for o in _rp_("78_") if o["kind"] == "solid" and abs(o["V"][:, 2].max() - 0.15) < 0.02]
                  + [_pg_(o) for o in _rp_("95_") if "あめのわ（" in o["name"]]
                  + [_pg_(o) for o in _rp_("92_") if any(k_ in o["name"] for k_ in ("床の噴水", "霧のわ（", "滝壺の水面"))])
    _RAINP = _uu([_pg_(o) for o in _rp_("92_") if "雨庭" in o["name"]])
    print("配置図に足す：みなみのさんかく", round(_MINAMI.area, 1), "砂", round(_SANDP.area, 1), "水", round(_WATERP.area, 1), "雨庭", round(_RAINP.area, 1), "小屋の屋根", round(_HUT.area, 1), "m2")
    _shp_ = _sh                                   # 下の「北東の辺から出る道」で _sh が図形に上書きされるので、形を取る関数を取っておく
    for gr, suf in (("l", "_線.pdf"), ("c", "_色.pdf")):
        _nd = fitz.open(); _pg = _nd.new_page(width=W * MM, height=H * MM)
        # 向こうの紙の外（南の高野川の水面など）は、こちらの描いた線と色で補う（ユーザー 10-26夕：南へ延ばして川を見せる）
        _bw = (bsx, H - bsy - bsh, bsx + bsw, H - bsy)
        for _r in ((_bw[0], _bw[1], _bw[2], _ia[1]),
                   (_bw[0], max(_bw[1], _ia[1]), _ia[0], min(_bw[3], _ia[3])), (_ia[2], max(_bw[1], _ia[1]), _bw[2], min(_bw[3], _ia[3]))):
            _r = (max(_r[0], 0), max(_r[1], 0), min(_r[2], W), min(_r[3], H))
            if _r[2] - _r[0] > 0.1 and _r[3] - _r[1] > 0.1:
                _cr = fitz.Rect(_r[0] * MM, _r[1] * MM, _r[2] * MM, _r[3] * MM)
                _pg.show_pdf_page(_cr, fitz.open(_SITE_PDF[gr]), 0, clip=_cr)
        # 南（向こうの図の外）：水と橋だけ（こちらの描いた川の線は描かない）
        if gr == "c":
            _fillg(_pg, _WATER, _hx("#CFE3EF"))
            _fillg(_pg, _BRIDGE, _hx("#F7F7F7"))
            _fillg(_pg, _PARK_R, _hx("#D9E8C6"))                                        # 公園を緑に（ユーザー、10-26夜）
            if _g73a: _fillg(_pg, _ARCH, _hx("#C9DFB0"))                                  # ムベのアーチの範囲を緑に
        else:
            _fillg(_pg, _BRIDGE, None, _hx("#999999"), 0.2)
        _src = fitz.open(_SPB + suf)
        _cl = fitz.Rect((_ia[0] - _off[0] + 0.35) * MM, (_ia[1] - _off[1] + 0.35) * MM, (_ia[2] - _off[0] - 0.35) * MM, (_ia[3] - _off[1] - 0.35) * MM)
        _pg.show_pdf_page(fitz.Rect((_ia[0] + 0.35) * MM, (_ia[1] + 0.35) * MM, (_ia[2] - 0.35) * MM, (_ia[3] - 0.35) * MM), _src, 0, clip=_cl)   # 枠の線は入れない
        if gr == "c":
            _fillg(_pg, _MINAMI, _hx("#DDE9CC"))                                           # みなみのさんかくを緑に（芝かどうかは別。向こうの図の白い地の上に）
            _fillg(_pg, _SANDP, _hx("#EFE2B8"))                                            # 砂場・粒の遊び場
            _fillg(_pg, _WATERP, _hx("#BFDDEE"))                                           # 水遊び（水のテーブル・噴水・あめのわ・霧のわ）
            _fillg(_pg, _RAINP, _hx("#DCE4E6"))                                            # 雨庭（玉石の浜）
            _fillg(_pg, _HUT, _hx("#5E636C"))                                              # 園庭の小屋の屋根（片流れ、更新係の図に無い）
            # 周りの道を少し濃く（ユーザー 10-27夜：西の道とその先の白い敷地の差をつける）。敷地の中は塗らない
            _fillg(_pg, _RDR.difference(_SITEP.buffer(0.05)), _hx("#E2E2E0"))
            # 西の道沿いの歩道（幅 1 m）を洗い出しのベージュに、スピードバンプは今までの灰のまま（ユーザー 10-27夜）
            _swS = _SITEP.intersection(LineString([_A_ - _tW * 10, _B_ + _tW * 10]).buffer(1.0, cap_style=2)).intersection(_slab).difference(_PARK_R.buffer(0.02))
            _bumps = [g_ for g_ in (_shp_(o_) for o_ in _rp_("74_") if o_["kind"] == "solid") if g_ is not None and g_.area > 0.2 and g_.intersection(_swS).area > 0.5 * g_.area]
            _fillg(_pg, _swS.difference(unary_union(_bumps)) if _bumps else _swS, _hx("#EDDDBA"))
            _fillg(_pg, _WATER.difference(_BRIDGE), _hx("#CFE3EF"))
            for xx, yy, rr, an in _STONES:
                _fillg(_pg, affinity.rotate(affinity.scale(Point(xx, yy).buffer(rr, 8), 1.0, 0.7), an), _hx("#E4DED0"))
        else:
            if not _BED.is_empty:                 # 河川敷の片の継ぎ目の線を、同じ緑で覆って消す（上の縁の線は残す）
                _fillg(_pg, _BED.buffer(-0.06).difference(_BRIDGE).difference(_WATER), _hx("#DDE8D0"))
                _fillg(_pg, _WATER.difference(_BRIDGE), _hx("#CFE3EF"))
            for xx, yy, rr, an in _STONES:
                _fillg(_pg, affinity.rotate(affinity.scale(Point(xx, yy).buffer(rr, 8), 1.0, 0.7), an), None, _hx("#9C9587"), 0.35)
            _fillg(_pg, _SANDP, None, _hx("#A89A70"), 0.3)
            _fillg(_pg, _WATERP, None, _hx("#6FA3C4"), 0.3)
            _fillg(_pg, _HUT, None, _hx("#222222"), 0.5)
            for xx, yy in _TUFTS:
                for da, ln_ in ((-28, 0.26), (-10, 0.34), (8, 0.36), (26, 0.27)):
                    t_ = np.radians(90 + da)
                    _pg.draw_line(*_P([(xx, yy), (xx + np.cos(t_) * ln_, yy + np.sin(t_) * ln_)]), color=_hx("#7E9C6A"), width=0.35)
        if not _NESTUB.is_empty:                 # 向こうの図の北東の辺から出る道を白で消す（更新係に直してもらうまで、ユーザー 10-26夜）
            _wp = _NESTUB.buffer(0.12 if gr == "l" else 0.03, join_style=2).difference(Polygon(to_s(np.array(list(SITE_C.values())))).buffer(0.25, join_style=2))
            for g_ in getattr(_wp, "geoms", [_wp]):
                if g_.geom_type != "Polygon" or g_.area < 0.01: continue
                _q = xf(np.array(rot(g_).exterior.coords))
                _sh = _pg.new_shape(); _sh.draw_polyline([fitz.Point(u_ * MM, (H - v_) * MM) for u_, v_ in _q])
                _sh.finish(color=None, fill=(1, 1, 1), closePath=True); _sh.commit()
        _fn = os.path.join(OUT, f"_site_{gr}_upd.pdf"); _nd.save(_fn); _nd.close()
        _SITE_PDF[gr] = _fn
    print("配置図：線と色は更新係の配置図から（ずれ", np.round(_off, 1), "mm）")
_SCLIP = (sx, H - sy - sh, sx + sw, H - sy)                                  # 元のPDFのmm（左上から）
for gr in ("c", "l", "t", "o"):                                               # 1枚目：色 → 線 → 文字 → 風と視線の順に重ねる（太陽は外した、ユーザー 10-26）
    embed(1, _SITE_PDF[gr], _SCLIP, sx, sy, 1.0)
# 太陽の線（方位を兼ねる、ユーザー 10-26夜）：配置図の左上。線は素材の図、時刻とNは Apple Chancery の文字の部品
sys.path.insert(0, os.path.join(HERE, "tools"))
import sun_rays
# 地の色は二つ（ユーザー、10-27：c 中の灰・d 屋根の色）。.ai には屋根の色を置く（中の灰は控え）
_SUNF = os.path.join(HERE, "sozai", "13b_太陽の線_屋根の色.pdf")                  # 屋根の色に決めた（ユーザー、10-27 0:24）
_SD, _SL = sun_rays.make(_SUNF, float(np.degrees(np.arctan2(_nv[1], _nv[0]))), bg="#5A5F68", ring="#FFFFFF")
sun_rays.make(os.path.join(HERE, "sozai", "13a_太陽の線_中の灰.pdf"), float(np.degrees(np.arctan2(_nv[1], _nv[0]))), bg="#A9ADB3", ring="#FFFFFF")
for _old in ("13_太陽の線.pdf",):
    if os.path.exists(os.path.join(HERE, "sozai", _old)): os.remove(os.path.join(HERE, "sozai", _old))
_sux, _suy = sx + 3, sy + sh - 3 - _SD
embed(1, _SUNF, None, _sux, _suy, 1.0)
for _s, _x, _y, _ha in _SL:                     # 文字は図の上に（見本では貼った図の上に描く TOPT）。中心合わせ：幅の半分と高さの1/3を戻す
    _th = 1.9 if _s != "N" else 2.4
    _tw = fitz.Font(fontfile=FONT_ALT["Apple-Chancery"]).text_length(_s, _th / 0.72) 
    TOPT[1].append((_sux + _x - _tw / 2, _suy + _y - _th * 0.35, _s, _th, False, "Apple-Chancery", "#F2F3F4"))
# 地域のなかの敷地（ユーザー、10-27：PLATEAU とともに）。北を上に 1/10000。置き場所はユーザーが選ぶ（いまは左下の仮の場所）
import area_map
_AMF = os.path.join(HERE, "sozai", "14_地域のなかの敷地_1-10000.pdf")
_rt = []
for o in L("10_") + L("20_") + L("35_"):
    if o["kind"] == "mesh":
        _rt += [Polygon(o["V"][f_, :2]).buffer(0.01) for f_ in o["F"] if Polygon(o["V"][f_, :2]).area > 1e-4]
_ru = unary_union(_rt)
_AW, _AH = 120.0, 96.0
_AL = area_map.make(_AMF, os.path.join(HERE, "plateau_area.json.gz"), list(SITE_C.values()), [np.array(g_.exterior.coords) for g_ in getattr(_ru, "geoms", [_ru])], W=_AW, H=_AH)
_amx, _amy = M + 6, P1_BOT                                  # 左下（帯が2枚目へ移ったので紙の下の端まで）
embed(1, _AMF, None, _amx, _amy, 1.0)
_FR = fitz.Font(fontfile=FONT)
for _s, (_x, _y) in _AL.items():
    _th = {"高野川": 2.6, "京都工芸繊維大学": 2.4, "敷地": 2.4, "N": 2.6}.get(_s, 1.9)
    _tw = _FR.text_length(_s, _th / 0.72)
    _dx, _dy = {"敷地": (4, -1), "0": (0, 1.2), "200 m": (0, 1.2)}.get(_s, (0, 0))
    _cx = _amx + _x + _dx - (0 if _s == "敷地" else _tw / 2)
    TOPT[1].append((_cx, _amy + _y + _dy - _th * 0.35, _s, _th, _s in ("敷地", "N", "高野川"), None, "#2E333A" if _s == "敷地" else ("#2F6FA0" if _s == "高野川" else "#333333")))
TOPT[1].append((_amx, _amy + _AH + 3, "地域のなかの敷地　1/10000", 3.0, True))
TOPT[1].append((_amx, _amy - 4.5, "出典：国土交通省 Project PLATEAU（京都市 2025）の建物・道路・土地利用から作図", 1.9, False))
# 縮尺のスケールは部品に（ユーザー、10-27：「その他の絵」ごと隠したので、一つのグループで出す）
def scalebar_parts(x, y, scale, meters, grp):
    k = 1000 / scale; hb = 1.2; n_ = meters // 5
    for i in range(n_):
        SITEPARTS.append(dict(kind="line", id=f"{grp}.bar{i}", pts=[(x + i * 5 * k, y + hb / 2), (x + (i + 1) * 5 * k, y + hb / 2)],
                              color="#222222" if i % 2 == 0 else "#FFFFFF", lw=hb * 72 / 25.4, group=f"site.g.{grp}", name=f"縮尺 {i}"))
    SITEPARTS.append(dict(kind="line", id=f"{grp}.frame", pts=[(x, y), (x + meters * k, y), (x + meters * k, y + hb), (x, y + hb), (x, y)],
                          color="#222222", lw=0.3, group=f"site.g.{grp}", name="縮尺の枠"))
    SITEPARTS.append(dict(kind="text", x=x, y=y - 4, s="0", size=2.4, color="#222222", bold=False, ha="center", va="baseline", group=f"site.g.{grp}"))
    SITEPARTS.append(dict(kind="text", x=x + meters * k, y=y - 4, s=f"{meters} m", size=2.4, color="#222222", bold=False, ha="center", va="baseline", group=f"site.g.{grp}"))


scalebar_parts(sx + 6, sy - 22, 200, 20, "縮尺")
# 沿川の景観立面　昼・夜 1/300 は2枚目（景観）の下の段へ（ユーザー、10-27夜）
_lw1 = (LE_T1 - LE_T0) * 1000 / LE_SC; _lh1 = (LE_Z1 - LE_Z0) * 1000 / LE_SC
SOZAI_FILES = [("01a", "配置図　1/200　線（屋根伏せ・外構・園庭・道・敷地の境）", "線", "色の上、文字の下に置く"),
               ("01b", "配置図　1/200　色（屋根・太陽光・光の筋・園庭・水・木）", "色", "いちばん下に置く"),
               ("01c", "配置図　1/200　文字（建物と園庭の名前・道の注・方位のN）", "文字", "いちばん上に置く"),
               ("01d", "配置図　1/200　夏の夜の風と比叡への視線（重ねる層、地は透明）", "風と視線", "文字の上に重ねる"),
]
print(f"配置図：回転{ROT:.1f}°（3dmから{GJ['VIEW_ROT']['deg']}°）、枠{sw:.0f}×{sh:.0f} mm")

# 引き出しの点（紙のmm）
Rs = lambda P: np.c_[np.atleast_2d(P)[:, 0] * np.cos(_rr) - np.atleast_2d(P)[:, 1] * np.sin(_rr),
                     np.atleast_2d(P)[:, 0] * np.sin(_rr) + np.atleast_2d(P)[:, 1] * np.cos(_rr)]   # sの座標 → 回した座標
P3p = lambda P: xf(R3(P))[0]                       # 3dmのm → 紙
Psp = lambda P: xf(Rs(np.asarray(P, float)))[0]    # sの座標 → 紙
_stl = gc.XS([tuple(p) for p in GJ["STREAM"]["line"]])
_cen = lambda pre: Psp(np.array(unary_union([g for ln, k, g in plan_items if ln.startswith(pre)]).centroid.coords[0]))
# 解説の箱（ユーザー、10-25 23:38：文を差し替え。番号は大事な順。引き出し線は短く、交わらないように）
# 置き場所を決めた箱は FIX（Illustratorでの木田さんの割付、アートボードの左上からmm）：用水を借りる＝用水ネットワークの図の真下、災害＝上の真ん中
_rainend = xf(np.array([_rain.coords[-1]]))[0]
NAT = [("yousui", "用水を借りる", ["井出ヶ鼻井堰に端を発する松ヶ崎の用水ネットワークから、水を借り、園庭の小川にする。"], [P3p(_stl[0])], (609.68, 186.77)),
       ("compost", "野菜くずコンポスト", ["野菜くずや落ち葉をこどもたちの手で土に還す。発酵する暖かい土とミミズに驚く。野菜を育てる。命の循環を知る。"],
        [Psp(np.array(GD["compost"].centroid.coords[0]))], None),
       ("mitate", "高野川と比叡にみたてる", ["日本文化が育ててきた「みたて」。園内の小川と築山を高野川と比叡にみたてる。それを超えて視線を遠くにすると、高野川を超えて比叡の山。"],
        [Psp(np.array(GD["mound"].centroid.coords[0])), P3p(_stl[len(_stl) // 2])], None),
       ("mizu", "水の行方を見る", ["小川は暗渠に隠さず高野川に注ぐ。屋根に降った雨は、雨落ちに落ち、雨水浸透側溝と雨庭を経て、溢れは高野川に。"],
        [P3p(_stl[-1]), _rainend], None),
       ("kaze", "風の道", ["夏の夜、高野川の谷を下りてくる涼しい風を、縁側の床下から越屋根へ抜く。床下に冷えをためて、昼の冷房を抑える。"], [_cen("14_")], None),
       ("rin", "間伐材を使った林", ["京都北山の北山杉の間伐材141本を、ホールの林として立てる。"], [_cen("59_1F_ホール")], None)]
COM = [("park", "小竹薮公園を残す", ["地域の記憶である小竹薮公園をそのまま残し、園への入口の前庭にする。そこから北へ、西の道沿いに幅1 mの歩道を開き、歩く人を車から守る。"],
        [P3p(np.array(gc.PARK.centroid.coords[0]))], None),
       ("traffic", "車と自転車の出入りを南にまとめる", ["西の道の中ほどでは、道に突き出た木が見通しをさえぎる。車と送り迎えの自転車の出入りはこの木より南にまとめ、出入口にはスピードバンプを置いて速度を落とす。"],
        [P3p(SITE_C["NW"] + 0.78 * _LW * _u - 3.0 * _n)], None),
       ("mukai", "お向かいさん", ["西の道の北半分は狭い道を挟んで向かいに住宅がある。圧迫感を与えないよう、この面の建物高さを1階程度に抑える。"],
        [P3p(SITE_C["NW"] + 0.3 * _LW * _u - 4.0 * _n)], None),
       ("saigai", "災害時の持ちつ持たれつ", ["大洪水が予想される場合の緊急避難先として京都工芸繊維大学と協定（京都市ハザードマップによる浸水深1.5 m）。太陽光発電、蓄電池、地下水の利用によって、災害時に水を地域に提供。"],
        [], None),                                            # 場所が特に無いので引き出し線なし（ユーザー、10-26）。配置図を上げたので左の列の上へ
       ("east", "東の隣家への配慮", ["東の隣家との境は1 m下げ（セットバック）、園庭の小屋と植樹で視線と音をやわらげる。"],
        [P3p(SITE_C["N"] + 0.55 * (SITE_C["E"] - SITE_C["N"]) - 3.0 * _out)], None)]
ITEMS = [(f"自然{i_ + 1}　" + h1, ls_, C_NAT, "#F6FAFD", pts, fx_, "nat." + k1) for i_, (k1, h1, ls_, pts, fx_) in enumerate(NAT)]
ITEMS += [(f"地域{i_ + 1}　" + h1, ls_, C_COM, "#FBF7F2", pts, fx_, "com." + k1) for i_, (k1, h1, ls_, pts, fx_) in enumerate(COM)]
_mid = sx + sw / 2
BOXW = 175.0                                              # 説明の箱は少し狭く、配置図の側に寄せる（ユーザー、10-26：引き出し線が短くなる）
LCW = RCW = BOXW
LCX = sx - 8 - LCW
RCX = sx + sw + 8
_hof = lambda it, colw: 16 + sum(len(jwrap(t_, (colw - 6) / (3.0 / 0.72))) for t_ in it[1]) * (3.0 / 0.72 + 1.2) + 1.5 * len(it[1])
_fixbot = {}                                              # 置き場所を決めた箱の下端（紙のmm、下から）
for (head, ls_, col, fill, pts, fx_, key_) in ITEMS:
    if fx_ is None:
        continue
    h_ = _hof((head, ls_), RCW)
    x_, t_ = fx_[0], H - fx_[1]                          # 上端
    ibox(ax, x_, t_ - h_, RCW, h_, head, ls_, col, fill, size=3.0, key=key_)
    _fixbot[(x_ >= RCX - 5)] = min(_fixbot.get(x_ >= RCX - 5, 1e9), t_ - h_)
    for k_, q_ in enumerate(pts):                         # 点に近い縁から
        ex_ = x_ if q_[0] < x_ else (x_ + RCW if q_[0] > x_ + RCW else x_ + RCW / 2)
        ey_ = (t_ - h_) if ex_ == x_ + RCW / 2 else min(t_ - 3, max(t_ - h_ + 3, q_[1]))
        topline(1, q_, (ex_, ey_), col, key=f"{key_}.{k_ + 1}")
for side, colx, colw in (("L", LCX, LCW), ("R", RCX, RCW)):
    COL_BOT = (_amy + _AH + 12) if side == "L" else P1_BOT   # 左の列は地域のなかの敷地の上で、右の列は紙の下の端まで
    COL_TOP = min(sy + sh + 2, CONCEPT_BOT - 14) if side == "L" else min(sy + sh + 2, _fixbot.get(True, 1e9) - 8)
    _FSIDE = {"nat.rin": "L", "com.saigai": "L"}           # 林は左から（ユーザー、10-26）。災害は線なしで左の列のいちばん上
    its = [it for it in ITEMS if it[5] is None and (_FSIDE.get(it[6]) or ("L" if np.mean([q[0] for q in it[4]]) < _mid else "R")) == side]
    its.sort(key=lambda it: -(np.mean([q[1] for q in it[4]]) if it[4] else 1e6))
    hs = [_hof(it, colw) for it in its]
    gap = max(5.0, min(14.0, (COL_TOP - COL_BOT - sum(hs)) / max(1, len(its) - 1)))
    # 理想の位置＝点の高さを中心に。上から順に、重ならないよう下へずらし、はみ出したら下から詰め直す
    want = [np.mean([q[1] for q in it[4]]) if it[4] else COL_TOP + 1e3 for it in its]   # 点の無い箱（災害）はいちばん上
    tops = []
    cur = COL_TOP
    for w_, h_ in zip(want, hs):
        t_ = min(cur, w_ + h_ / 2)
        tops.append(t_)
        cur = t_ - h_ - gap
    over = (COL_BOT) - (tops[-1] - hs[-1]) if tops else 0
    if over > 0:
        cur = COL_BOT
        for k in range(len(tops) - 1, -1, -1):
            tops[k] = max(tops[k], cur + hs[k])
            cur = tops[k] + gap
    for (head, ls_, col, fill, pts, fx_, key_), t_, h_ in zip(its, tops, hs):
        ibox(ax, colx, t_ - h_, colw, h_, head, ls_, col, fill, size=3.0, key=key_)
        ex_ = colx + colw if side == "L" else colx
        for k_, q_ in enumerate(pts):
            topline(1, q_, (ex_, min(t_ - 3, max(t_ - h_ + 3, q_[1] if len(pts) == 1 else t_ - h_ / 2 + (k_ - (len(pts) - 1) / 2) * 6))), col, key=f"{key_}.{k_ + 1}")

# 上の段：配置図の注と、用水のネットワーク全体の図（場所の確保。涌泉寺からの水の道、平安京の外の条里の地割のまま）
NTX = M + 6 + 250
# 配置図の注は消した（ユーザー、10-26）
_nbx = 611.41                                            # 用水ネットワークの図はIllustratorの割付どおり右上（木田さん、10-25）
# 松ヶ崎の用水の網（土木遺産のページ「宝ヶ池」の図をなぞった線、tools/trace_yousui.py。ユーザー、10-24夜）。配置図と同じ向きに回す
_ny0, _ny1 = top - 8 - 130, top - 8                      # 図の大きさは配置図の位置に依らない（前の割付のまま）
YS = json.load(open(os.path.join(HERE, "matsugasaki_yousui.json"), encoding="utf-8"))
_ang = 0.0                                               # 広域の図は北が上（ユーザー）
_ca, _sa = np.cos(_ang), np.sin(_ang)
_yr = lambda P: np.c_[np.asarray(P, float)[:, 0] * _ca + np.asarray(P, float)[:, 1] * _sa,
                      np.asarray(P, float)[:, 0] * _sa - np.asarray(P, float)[:, 1] * _ca]   # 画素（y下向き）→ 回した座標
_allp = np.vstack([_yr(l) for l in YS["water_lines"] + list(YS.get("roads", {}).values())])
_lo, _hi = _allp.min(0), _allp.max(0)
_CR = 10.0                                               # 下の出典2行
_k = min((W - M - 6 - _nbx - 36) / (_hi[0] - _lo[0]), ((_ny1 - _ny0) - 12 - _CR) / (_hi[1] - _lo[1]))
_mw_, _mh_ = (_hi[0] - _lo[0]) * _k, (_hi[1] - _lo[1]) * _k
_nw = max(_mw_ + 30, 122)                                # 枠は図と名前・出典に必要十分な大きさ（ユーザー、10-25）
_ny1 = _ny0 + _CR + _mh_ + 12
_dY = (H - 48.02) - _ny1; _ny0 += _dY; _ny1 += _dY       # 図の上端をアートボードの上から48 mmに
_fx0, _fy0 = _nbx + 4, _ny0 + _CR
_box_patch = Rectangle((_nbx, _ny0), _nw, _ny1 - _ny0, fc="#F6FAFD", ec="#7FA6C8", lw=0.5)
ax.add_patch(_box_patch)
T(ax, _nbx + _nw - 3, _ny1 - 6, "松ヶ崎の用水ネットワーク", 3.4, C_NAT, bold=True, ha="right")   # 右寄せ：左上は地域のなかの敷地（素材14）を重ねる（ユーザー、10-27）
T(ax, _nbx + 6, _ny1 - 13, "N↑", 3.0, bold=True)
_ym = lambda P: np.c_[_fx0 + (_yr(P)[:, 0] - _lo[0]) * _k, _fy0 + (_yr(P)[:, 1] - _lo[1]) * _k]
for _rn, _rl in YS.get("roads", {}).items():             # 道は北山通だけ（ユーザー）
    q = _ym(_rl); ax.plot(q[:, 0], q[:, 1], color="#D8A84E", lw=1.4, zorder=2.5, solid_capstyle="butt")
    T(ax, q[-1, 0] - 1, q[-1, 1] - 4.0, _rn, 2.2, "#A87A22", ha="right", zorder=6)
for pl in YS["water_fills"]:
    q = _ym(pl); ax.fill(q[:, 0], q[:, 1], fc="#BFDDF2", ec="none", zorder=3)
for ln_ in YS["water_lines"]:
    q = _ym(ln_); ax.plot(q[:, 0], q[:, 1], color=C_NAT, lw=0.6, zorder=4, solid_capstyle="round")
for (px_, py_), t_, dx_, dy_, ha_ in [((272, 76), "井出ヶ鼻井堰", 3, -1, "left"), ((127, 55), "宝が池", 2, 2, "left"),
                                       ((200, 151), "東松ヶ崎の井戸", -2, 1.5, "right"), ((246, 166), "樋ノ上川", 1, -3.5, "left"),
                                       ((170, 182), "前川", 1, 1, "left"), ((163, 216), "橋上川", 1, 1, "left"),
                                       ((133, 231), "正田川", 1, 1, "left"), ((113, 248), "久土川", 1, 1, "left"), ((118, 318), "高野川", 2, -4, "left"), ((225, 30), "岩倉川", 0, 2, "left"), ((318, 177), "音羽川", 0, 2, "right")]:
    q = _ym([(px_, py_)])[0]
    T(ax, q[0] + dx_, q[1] + dy_, t_, 2.2, C_NAT if ("川" in t_ or "堰" in t_ or "池" in t_) and "井戸" not in t_ else INK, ha=ha_, zorder=6)
_wq = _ym([(272, 76)])[0]; ax.plot([_wq[0]], [_wq[1]], marker="v", ms=4, color=C_NAT, zorder=7)
_eq = _ym([(200, 151)])[0]; ax.plot([_eq[0]], [_eq[1]], "o", ms=3, mfc="white", mec=INK, zorder=7)
_sq = _ym([(247, 148)])[0] + np.array([4.5, -1.2])   # 図の「樋ノ上川」の「樋」の字のあたり（ユーザー、10-24夜）
# 敷地の印は描かない（ユーザー、10-25朝：不要）
T(ax, _fx0, _ny0 + 5.5, "大正から昭和初期の図（https://kyoto-machisen.jp/chiiki_hp/matsugasaki_hp/history/history.htm）", 1.8, NOTE)
T(ax, _fx0, _ny0 + 2.0, "図：http://ksdobokuisan.stars.ne.jp/80_takaragaike/takaragaike.html の図をなぞって描き直し", 1.8, NOTE)
sozai("02", "松ヶ崎の用水の網（北が上）", 1, _nbx, _ny0, _box_patch.get_width(), _ny1 - _ny0)
figs.append(fig)

# 図のPDF（3dmから自動の図）
DRW = os.path.join(ROOT, "drawings")   # 図のPDFは sodachiya/drawings/（10-24）
PLAN = os.path.join(DRW, "sodachiya_plan_1-100.pdf")
ELE1 = os.path.join(DRW, "sodachiya_elevations_1-100.pdf")
ELE2 = os.path.join(DRW, "sodachiya_elevations2_1-100.pdf")

# 面積表とinspired by（3枚目・4枚目で使う）
AJ = json.load(open(os.path.join(ROOT, "model", "drawings", "sodachiya_areas.json"), encoding="utf-8"))


def area_table(ax, tx, ty, tw, size=2.2):
    title(ax, tx, ty, "面積表", "m²（壁芯、3dmから自動）")
    T(ax, tx, ty - 8, "室", size, NOTE); T(ax, tx + tw * 0.55, ty - 8, "要求", size, NOTE); T(ax, tx + tw, ty - 8, "計画", size, NOTE, ha="right")
    yy = ty - 14
    for r_ in AJ["rooms"]:
        if r_["planned"] is None and not r_["judge"]:
            continue
        nm = r_["room"].replace(" ", "")
        T(ax, tx, yy, nm[:11], size)
        T(ax, tx + tw * 0.55, yy, r_["required"].replace(" ", "")[:8], size)
        T(ax, tx + tw, yy, f"{r_['planned']:.1f}" if r_["planned"] else r_["judge"], size, ha="right")
        yy -= size + 2.2
    T(ax, tx, yy, "延床（2,000以内）", size, bold=True)
    T(ax, tx + tw, yy, f"{AJ['floor']['total']:,.1f}", size, ha="right", bold=True)
    return yy


INSP = [("Asilo Nido Iride", "Mario Cucinella Architects・Guastalla・2015", "梁の列が並ぶ長細い本館と、外に付く付属の建物"),
        ("Tamedia", "坂茂・Zürich・2013", "梁の端の楕円の頭と、それを貫く楕円の桁"),
        ("レイモンド斑鳩こども園", "キノアーキテクツ・斑鳩・2026", "室内に木を立てる（ホールの北山杉）"),
        ("KAIT工房", "石上純也・厚木・2008", "柱の配列：見る向きで景色が変わる並び"),
        ("認定こども園らみどり", "はりゅうウッドスタジオ・須賀川・2026", "内と外の二重の縁側、遊具を置かない地形の園庭"),
        ("仙田満の園舎", "環境デザイン研究所", "摺鉢のネット、キャットウォーク、ニッチ"),
        ("Waldorf School of the Peninsula", "California", "遊戯室の切り株")]




def inspired(ax, tx, ty, colw, rows=4):
    T(ax, tx, ty, "inspired by", 3.0, bold=True)
    for i, (n, src, what) in enumerate(INSP):
        c_, r_ = divmod(i, rows)
        x_, y2 = tx + c_ * colw, ty - 6 - r_ * 11.0          # 行の間を広げた（9 では次の行に重なった）
        T(ax, x_, y2, n, 2.2, bold=True)
        T(ax, x_, y2 - 3.3, src, 1.8, "#666666")
        T(ax, x_ + 1.5, y2 - 6.4, "→ " + what, 1.9)


# ================================================================ 2　景観（10-28：もとの2枚目、いちど4枚目にしてから13:17に2枚目へ。ユーザー、10-24夜：立面図2面 → 鳥瞰・約束・素材と色。10-27夜：沿川の景観立面（昼・夜）を1枚目から下の段へ）
fig, ax = page()
frame(ax, 2, "景観", "建物に正対する二つの立面（園庭の側・道路の側）で、伸びやかな梁と縁側、西館の立ち上がり。下の段に外から見た姿：鳥瞰と、川の向こうから見た沿川の景観立面（昼・夜）",
      "園庭の側・道路の側の立面図 → 鳥瞰・沿川の景観立面（昼・夜）→ 景観の約束・素材と色")
CLIP_E1 = (25, 35.6, 788.5, 143.0)         # 自動の立面図1：園庭の側（10-28：右の高さの記号・左の高さの寸法・下の全長まで。縮尺の棒は外す）
CLIP_E2 = (25, 200.1, 788.5, 308.6)        # 自動の立面図1：道路の側（10-28：上は表題の切れ端を外し、右の高さの記号・下の全長まで）
CLIP_SA = (84, 46.6, 830.5, 171)           # 自動の断面図：縦断A（10-28：左は敷地の境から、上は通り芯の頭から。右は元の図の枠の手前まで。「← 南」は表題に書いてあるので外す）

ex = M + 6
y_ = H - M - 16 - 3
BH2 = 210                                    # 4行目（鳥瞰＝透視図 A4・約束・素材と色）の高さ。鳥瞰は A4（297×210）で課題の透視図を兼ねる（ユーザー、10-27夜）
G2 = (y_ - (M + 8) - BH2 - 2 * 7 - (CLIP_E1[3] - CLIP_E1[1]) - (CLIP_E2[3] - CLIP_E2[1])) / 3
# 二つの立面を対比で見せる（ユーザー、10-27夜：園庭にひらく／まちに溶け込みつつやさしく守る）。箱は立面の右上の空に
CONTRAST = {
    "garden": ("園庭にひらく", ["縁側と深い軒が57 m続き、3 mごとの柱とガラス戸の半分が開く。屋根の光の筋が架構を照らし、こどもは縁側から庭へ下りる。"]),
    "road": ("まちに溶け込み、やさしく守る", ["杉の大和張りの静かな板の壁。西館は向かいの住宅に向けて1階の高さまで下げ、窓は小さく面ごとのリズムで。道からは中が見えすぎず、園を包む。"]),
}
y_ -= G2 / 2
title(ax, ex, y_ - 4, "園庭の側の立面図", "1/100　円弧の中心の方向から弧の真ん中に正対")
T(ax, ex + 300, y_ - 4, CONTRAST["garden"][0], 4.2, "#4E8A3A", bold=True)
T(ax, ex + 340, y_ - 4, CONTRAST["garden"][1][0], 2.8)
y_ -= 7
_, h_ = embed(2, ELE1, CLIP_E1, ex, y_ - (CLIP_E1[3] - CLIP_E1[1]), 1.0)
y_ -= h_ + G2
title(ax, ex, y_ - 4, "道路の側の立面図", "1/100　西の道路から")
T(ax, ex + 300, y_ - 4, CONTRAST["road"][0], 4.2, "#8A5A2B", bold=True)
T(ax, ex + 372, y_ - 4, CONTRAST["road"][1][0], 2.8)
y_ -= 7
_, h_ = embed(2, ELE1, CLIP_E2, ex, y_ - (CLIP_E2[3] - CLIP_E2[1]), 1.0)
y_ -= h_ + G2
bh = BH2
_pw = 297
box(ax, ex, M + 8, _pw, bh, "透視図（A4）　模型写真の鳥瞰", "南西の上空（公園と高野川の橋の上）から北東を見る\n手前に道の側の静かな壁と公園、奥に弧の縁側と園庭\n（模型ができるまでは Rhino の鳥瞰を仮に）")
# 鳥瞰の右に、沿川の景観立面 昼（上）・夜（下）1/300（ユーザー、10-27夜：1枚目の下から移した。外から見た姿を鳥瞰と並べる）
_lx = ex + _pw + 8
_ly_d = M + 8 + bh - _lh1                    # 昼の上端を鳥瞰の上端にそろえる
_ly_n = M + 8 + 9                            # 夜は下（題は図の下）
title(ax, _lx, _ly_d - 5.5, "沿川の景観立面　昼", f"1/{LE_SC}　高野川の向こうから（川の辺に直角）、周りの建物とともに")
title(ax, _lx, _ly_n - 5.5, "沿川の景観立面　夜", "本館と西館の越屋根の東の縁の光が水平に二本")
land_elev(ax, _lx, _ly_d, False)
land_elev(ax, _lx, _ly_n, True)
sozai("03", f"沿川の景観立面　昼　1/{LE_SC}", 2, _lx, _ly_d, _lw1, _lh1)
sozai("04", f"沿川の景観立面　夜　1/{LE_SC}", 2, _lx, _ly_n, _lw1, _lh1)
# 右の列：景観の約束（上）・素材と色（下）
_kx = _lx + _lw1 + 8
_kw = W - M - 6 - _kx
_KL = [
    "第一種低層住居専用地域。西館の棟は約8.5 m（GLから）。",
    "高野川特別修景地域（右岸）：河岸の樹木と清流が一体の水と緑の空間。川に面する側に植栽帯（園庭の林と生垣）、川に面する側に勾配のある下屋（南の深い軒）。深い軒と縁側、杉の大和張りの板壁（無塗装、銀鼠に枯れる）、ゆるい勾配の屋根――これをいまの和風の外観とする。",
    "遠景デザイン保全区域（高野川・修学院離宮・船岡山公園からの眺め）：外壁と屋根に禁止色を使わず、山並みと調和する色（黒い金属の屋根、木の色のまま）。",
    "小竹薮公園と既存の木を残す。"]
_kh = 16 + sum(len(jwrap(t_, (_kw - 6) / (2.8 / 0.72))) for t_ in _KL) * (2.8 / 0.72 + 1.2) + 1.5 * len(_KL) + 12
ibox(ax, _kx, M + 8 + bh - _kh, _kw, _kh, "景観の約束", _KL, "#4E6FB0", "#F6F8FC", size=2.8)
_mx = _kx
_mw = _kw
_mtop = M + 8 + bh - _kh - 8                 # 素材と色の上端
T(ax, _mx, _mtop - 4, "素材と色", 3.8, bold=True)
_sw = [("#B88A5A", "木の柱・梁（木の色のまま）"), ("#C9A77C", "杉の大和張りの外壁（銀鼠に枯れる）"), ("#2E2E30", "屋根：黒い金属（屋根材型の太陽光）"),
       ("#EDE7DA", "越屋根のガラスの蓋・縁側の白"), ("#8E9B86", "生垣と園庭の緑")]
_sst = min(13.0, (_mtop - 10 - (M + 8)) / len(_sw))
for i_, (c_, t_) in enumerate(_sw):
    yy = _mtop - 10 - (i_ + 1) * _sst + 2
    ax.add_patch(Rectangle((_mx, yy), 16, _sst - 4, fc=c_, ec="#777777", lw=0.2))
    T(ax, _mx + 20, yy + (_sst - 4) / 2 - 1, t_, 2.6)
sozai("05", "素材と色", 2, _mx - 1, M + 8, _mw + 1, _mtop - (M + 8))
figs.append(fig)

# ================================================================ 3　環境（10-28 13:17：5枚目から3枚目へ。ユーザー、10-24夜：断面2面と環境への配慮、縦断Aもここ）
fig, ax = page()
frame(ax, 3, "断面と環境", "二つの断面（1/100）と空気の環境。東西に切った断面Cで本館と西館の架構と風の道、縦断Aで弧の長さ。屋根材型の太陽光と蓄電池、資源のめぐり、時間（S&I は言葉で）",
      "断面C（架構と風の道）→ 運転表と配慮 → 縦断A → 光の筋・接合部 → inspired by・面積表")
CLIP_C2 = (432, 252, 830, 382)
CSC = 1.0                                       # 課題は断面 1/100・2面以上（ユーザー、10-27夜：1/75 をやめる）
hC = (CLIP_C2[3] - CLIP_C2[1]) * CSC
wC = (CLIP_C2[2] - CLIP_C2[0]) * CSC
cx, cy = M + 6, H - M - 16 - 10 - hC
title(ax, cx, cy + hC + 3, "断面図C　東西に切る（4歳・遊戯室）", "1/100　本館と西館の架構、昼と夏の夜の風の道")
embed(3, SEC, CLIP_C2, cx, cy, CSC)
_rx5 = cx + wC + 8
_rw5 = W - M - 6 - _rx5
cells4 = [("夏の昼", "庇・天井扇\n床下空調"), ("夏の夜", "床下→梁間\n→越屋根・遊戯室"), ("春・秋", "越屋根を開ける\n縁側を開け放す"), ("冬", "換気口を閉じる\n熱交換・断熱"),
          ("パッシブ", "床下に冷えをためる\n通風・光の筋"), ("エネルギー", "屋根材型の太陽光\n蓄電池"), ("資源", "北山杉の間伐材\n土・雨・生ごみを回す"), ("時間", "スケルトン＆インフィル\n3 mの架構は残し、中は変えられる")]
_cw5, _ch5 = (_rw5 - 4) / 2, (hC - 10 - 3 * 4) / 4
T(ax, _rx5, cy + hC - 2, "運転表", 3.2, bold=True)
sozai("12", "運転表と環境への配慮（8つの箱）", 3, _rx5, cy, _rw5, hC + 4)
T(ax, _rx5 + _cw5 + 4, cy + hC - 2, "環境への配慮（LEED v5 Gold相当）", 3.0, bold=True)
for i_, (h1, s1) in enumerate(cells4):
    c_, r_ = divmod(i_, 4)
    box(ax, _rx5 + c_ * (_cw5 + 4), cy + hC - 8 - (r_ + 1) * _ch5 - r_ * 4, _cw5, _ch5, h1, s1,
        fill="#FAF8FF" if c_ == 0 else "#F5FAF0", color=NOTE if c_ == 0 else "#4E8A3A")
ya = cy - 12 - (CLIP_SA[3] - CLIP_SA[1])
title(ax, cx, cy - 6, "縦断面図A", "1/100　保育室の中ほどの弧で切って展開、西を見る（左が南の高野川）")
embed(3, SEC, CLIP_SA, cx, ya, 1.0)
# 下の段：光の筋と架構・接合部・inspired by（断面Bと S&I の図は外した、ユーザー 10-27夜：S&I は言葉だけ）
by = M + 8
_bx = cx
_bh5 = ya - 10 - by
box(ax, _bx, by, 200, _bh5, "光の筋と架構　1/20", "2枚の梁のあいだ180の上にガラス\n溝の内側は鏡面のアルミ（光ダクト）")
JD = os.path.join(ROOT, "out", "joint_detail.pdf")
_jx = _bx + 208
wJ, hJ = embed(3, JD, None, _jx, by, fit=(260, _bh5 - 6))
T(ax, _jx, by + hJ + 2, "接合部（2枚の梁で柱を挟む）", 2.4, bold=True)
_ix = _jx + max(wJ, 120) + 10
# 面積表は最後の枚、inspired by の近くに（ユーザー、10-27夜）：右の端に面積表、その左に inspired by
_atw = 100
_atx = W - M - 6 - _atw
inspired(ax, _ix, by + _bh5 - 2, (_atx - 10 - _ix) / 2, rows=4)
_aty = by + _bh5 - 2
_atb = area_table(ax, _atx, _aty, _atw, size=2.4)
sozai("15", "面積表（壁芯、3dmから自動）", 3, _atx - 1, _atb - 3, _atw + 2, _aty - _atb + 8)
figs.append(fig)

# ================================================================ 4　平面図（10-28：もとの3枚目、いちど2枚目にしてから13:17に4枚目へ。ユーザー、10-25：敷地全体1/100を配置図と同じ向き、2階は西の道路の外。図は更新係のdraw100.pyがA1の一枚で出す：表題・色の凡例・縮尺・方位も入っている）
fig, ax = page()
PLAN3 = os.environ.get("SODACHIYA_PLAN3", PLAN)        # 確かめるときだけ手元の書き出しを指す
embed(4, PLAN3, None, 0, 0, 1.0)
TOPT[4].append((14, H - 12, "こどもたちの育ち舎　4/5　平面図　1階・2階", 3.6, True))
figs.append(fig)

# ================================================================ 5　こどもたち（と働く人たち）の環境（ユーザー、10-24夜：一日の帯を先頭に、透視図もここ）
fig, ax = page()
frame(ax, 5, "動線とこどもたちの環境", "上は一日の動線（4枚目の平面図の続き）。分離線の下は、こどもたちが地に足をつけて育つ場所：園庭・遊戯室・北山杉の林・教室・廊下の本棚・表の畑と火のオーブン",
      "一日の帯と動線 → 分離線 → 園庭 → 遊戯室・林 → 教室・本棚・畑")
STRIP_H = 150
px, py = M + 6, H - M - 16 - 2
# 一日の帯の小さな配置も配置図と同じ向き（高野川を下辺）に回す（ユーザー、10-25）。帯を描くあいだだけ形を回したものに入れ替える
_rs = lambda P: np.c_[np.asarray(P)[:, 0] * np.cos(_rr) - np.asarray(P)[:, 1] * np.sin(_rr), np.asarray(P)[:, 0] * np.sin(_rr) + np.asarray(P)[:, 1] * np.cos(_rr)]
_SAVE = (list(plan_items), dict(GD), roofs_plan)
plan_items[:] = [(ln_, k_, rot(g_)) for ln_, k_, g_ in plan_items]
GD.update({k_: ([rot(x_) for x_ in v_] if isinstance(v_, list) else rot(v_)) for k_, v_ in GD.items()})
roofs_plan = rot(roofs_plan)
def lcen(prefixes):
    gs = [g for ln, k, g in plan_items if ln.startswith(tuple(prefixes)) and k == "mesh"]
    return np.array(unary_union(gs).centroid.coords[0])


_kit = lcen(["32_"])
_hall = lcen(["59_1F_ホール"])
_edge_y = GD["amaochi"].bounds[3] + 0.8
_path = None
def _c(name):
    """動線の点：部屋のレイヤーの頭か、園庭の名前（GD）か、公園"""
    if name == "park":
        return _rs(to_s(np.atleast_2d(np.array(gc.PARK.centroid.coords[0]))))[0]
    if name in GD:
        return np.array(GD[name].centroid.coords[0])
    return lcen([name])


# 一日の帯の動線（ユーザー、10-24夜：時間ごとの図に線を加える）：こども（緑）・保育士（茶）・調理（青）
FLOW = {
    "登園 8:00": [["park", "15_", "59_1F_4歳"], ["59_1F_事務（スパン", "52_"], ["57_", "32_"]],
    "外で遊ぶ 9:30": [["59_1F_4歳", "13_", "north"], ["59_1F_3歳", "14_"], []],
    "食べる 11:30": [["59_1F_5歳", "34_"], ["32_", "33_", "59_1F_3歳"], ["32_", "33_"]],
    "寝る 12:45": [["59_1F_5歳", "mound"], ["59_1F_3歳", "36_"], []],
    "当番 15:00": [["32_", "59_1F_ホール", "13_", "hut", "compost"], ["compost", "north"], ["32_", "33_"]],
    "降園 16:30": [["34_", "52_", "15_", "park"], ["34_", "52_"], ["57_", "52_"]],
}
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
fh = STRIP_H
fy = py - 6 - fh
txt_h = 3 * (3.4 + 2 * 3.3) + 2
_kb = unary_union([roofs_plan, GD["garden"]]).bounds
kx0, ky0, kx1, ky1 = _kb[0] - 1.0, _kb[1] - 1.0, _kb[2] + 1.0, _kb[3] + 1.0
ksc = next(s_ for s_ in (500, 600, 700, 800, 1000)
           if (kx1 - kx0) * 1000 / s_ <= fw - 6 and (ky1 - ky0) * 1000 / s_ <= fh - 10 - txt_h)
for i, (h1, keys, ghi, path, lines3) in enumerate(frames_):
    fx = px + i * (fw + 5)
    ax.add_patch(Rectangle((fx, fy), fw, fh, fc="none", ec="#BBBBBB", lw=0.3))
    sozai(f"{6 + i:02d}", f"一日の帯　{h1}（小さな配置1/{ksc}と三者の動線）", 5, fx, fy, fw, fh)
    T(ax, fx + 3, fy + fh - 6, h1, 3.4, bold=True)
    kw_, kh_ = (kx1 - kx0) * 1000 / ksc, (ky1 - ky0) * 1000 / ksc
    kox, koy = fx + (fw - kw_) / 2, fy + txt_h + 2
    kxf = xform(kox, koy, ksc, kx0, ky0)
    draw_garden(ax, kxf, hi=ghi, thin=True)
    draw_plan(ax, kox, koy, ksc, kx0, ky0, kw_, kh_, keyhi=keys, thin=True)
    for (rn, rc), way in zip(ROLES, FLOW.get(h1, [])):
        if len(way) < 2:
            continue
        q = kxf(np.array([_c(w_) for w_ in way]))
        ax.plot(q[:, 0], q[:, 1], color=rc, lw=0.9, zorder=8, solid_capstyle="round")
        ax.annotate("", xy=tuple(q[-1]), xytext=tuple(q[-1] + (q[-2] - q[-1]) * min(1.0, 3.0 / max(np.linalg.norm(q[-2] - q[-1]), 1e-6))),
                    arrowprops=dict(arrowstyle="-|>", lw=0.8, color=rc), zorder=8)
    yy = fy + txt_h - 1
    for (rn, rc), s_ in zip(ROLES, lines3):
        T(ax, fx + 3, yy - 3.0, rn, 2.4, rc, bold=True)
        for k_, ln_ in enumerate(jwrap(s_, (fw - 16) / (2.3 / 0.72))[:2]):
            T(ax, fx + 13, yy - 3.0 - k_ * 3.3, ln_, 2.3)
        yy -= 3.4 + 2 * 3.3
plan_items[:] = _SAVE[0]
GD.clear(); GD.update(_SAVE[1])
roofs_plan = _SAVE[2]
dimnote(ax, px + 230, py - 4.5, f"一日の帯：上は1/{ksc}の小さな配置（建物＋園庭）と三者の動線（こども緑・保育士茶・調理青）、下にそれぞれの一日")

# 一日の帯は4枚目の平面図の続き（ユーザー、10-27夜）。その下に分離線、下は「こどもたちの環境」
_sep = fy - 8
ax.plot([M + 6, W - M - 6], [_sep, _sep], color="#888888", lw=0.5, zorder=5)
T(ax, M + 6, _sep - 9, "こどもたちの環境", 5.0, bold=True)
rt = _sep - 16                                 # 下の段の上端
by = M + 8
_avh = rt - by                                  # 使える高さ
# 左：園庭（だいさんかく・しずかのもり。配置1/200を縮小）
GSC = min(0.62, (_avh - 8) / _gh)
title(ax, M + 6, rt - 4, "園庭", f"だいさんかく・しずかのもり　約1/{int(round(200 / GSC, -1))}（配置1/200を縮小）")
wGa, hGa = embed(5, os.path.join(ROOT, "out", "sodachiya_garden_01.pdf"), (14, 40, 14 + _gw, 40 + _gh), M + 6, rt - 8 - _gh * GSC, GSC)
x2 = M + 6 + wGa + 8
_rw = W - M - 6 - x2
# 右の上の行：遊戯室・北山杉の林
PLAYP = os.path.join(ROOT, "out", "sodachiya_play_present.pdf")
_rowh = (_avh - 14) * 0.56
title(ax, x2, rt - 4, "遊戯室", "")
wPl, hPl = embed(5, PLAYP, None, x2, rt - 8 - _rowh, fit=(_rw * 0.58, _rowh))
x3 = x2 + wPl + 8
FOREST = os.path.join(ROOT, "out", "sodachiya_forest_02.pdf")
title(ax, x3, rt - 4, "ホールの北山杉の林", "")
embed(5, FOREST, (0, 8, 420, 118), x3, rt - 8 - _rowh, fit=(W - M - 6 - x3, _rowh))
# 右の下の行：教室・廊下の本棚と読む場所・表の畑と火のオーブン
_r2t = rt - 8 - _rowh - 8
_r2h = _r2t - 6 - by
ROOM3 = os.path.join(ROOT, "out", "sodachiya_room3_1-50.pdf")
title(ax, x2, _r2t, "教室", "3歳の保育室")
wR3, hR3 = embed(5, ROOM3, None, x2, by, fit=(_rw * 0.42, _r2h))
_bx4 = x2 + wR3 + 8
_bw4 = (W - M - 6 - _bx4 - 8) / 2
box(ax, _bx4, by, _bw4, _r2h, "廊下の本棚と読む場所", "（図は本館係に依頼）")
box(ax, _bx4 + _bw4 + 8, by, _bw4, _r2h, "表の畑と火のオーブン", "入口の前の菜園とひろばのかまど\n（図はアプローチ係に依頼）")
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
doc_clean = fitz.open("pdf", doc.tobytes())          # 素材は引き出し線・重ねた文字を入れる前から切り抜く（ユーザー、10-25）
for si in range(1, 6):
    pg = doc[si - 1]
    for (pts, col, *_k) in TOPL[si]:                     # 引き出し線は貼った図の上に（箱 → 折れ点 → 配置図の点）
        rgb = tuple(int(col[k:k + 2], 16) / 255 for k in (1, 3, 5))
        P_ = [fitz.Point(q[0] * MM, (H - q[1]) * MM) for q in pts]
        pg.draw_polyline(P_, color=rgb, width=0.6)
        pg.draw_circle(P_[-1], 0.9 * MM, color=rgb, fill=rgb)
    for ui_ in USER_ITEMS.get(si, []):                # 木田さんがIllustratorで足した物（export_layout.jsx の user_items）を見本にも（矢じりなどは出ない）
        _draw_user_item(pg, ui_)
    for (tx, ty, ts, th, tb, *ex) in TOPT[si]:
        _fa = FONT_ALT.get(ex[0]) if ex and ex[0] else None
        _cc = tuple(int(ex[1][k:k + 2], 16) / 255 for k in (1, 3, 5)) if len(ex) > 1 else (0.1, 0.1, 0.1)
        pg.insert_text(fitz.Point(tx * MM, (H - ty) * MM), ts, fontsize=th / 0.72 * MM, fontname=("F_A" if _fa else ("F_B" if tb else "F_R")),
                       fontfile=_fa or (FONTB if tb else FONT), color=_cc)
    if si == 1:                                     # 配置図の中の文字・注の線・突き出た木（Illustratorでは一つずつの部品）
        _hx = lambda c_: tuple(int(c_[k:k + 2], 16) / 255 for k in (1, 3, 5))
        _FNT = {False: fitz.Font(fontfile=FONT), True: fitz.Font(fontfile=FONTB)}
        for sp in SITEPARTS:
            if sp["kind"] == "circle":
                pg.draw_circle(fitz.Point(sp["cx"] * MM, (H - sp["cy"]) * MM), sp["r"] * MM, color=_hx(sp["stroke"]) if sp["stroke"] else None,
                               fill=_hx(sp["fill"]) if sp["fill"] else None, fill_opacity=sp.get("alpha", 1.0), width=sp["lw"] or 0)
            elif sp["kind"] == "line":
                P_ = [fitz.Point(q[0] * MM, (H - q[1]) * MM) for q in sp["pts"]]
                pg.draw_polyline(P_, color=_hx(sp["color"]), width=sp["lw"])
                if sp.get("dot"):
                    pg.draw_circle(P_[-1], sp["dot"] * MM, color=_hx(sp["color"]), fill=_hx(sp["color"]))
                if sp.get("arrow"):                       # 終わりの点に矢じり（長さ arrow mm）
                    _a, _b = np.array(sp["pts"][-2], float), np.array(sp["pts"][-1], float)
                    _u = (_b - _a) / np.linalg.norm(_b - _a); _n = np.array([-_u[1], _u[0]]); L_ = sp["arrow"]
                    _tri = [_b, _b - _u * L_ + _n * L_ * 0.35, _b - _u * L_ - _n * L_ * 0.35]
                    pg.draw_polyline([fitz.Point(q[0] * MM, (H - q[1]) * MM) for q in _tri] + [fitz.Point(_b[0] * MM, (H - _b[1]) * MM)],
                                     color=_hx(sp["color"]), fill=_hx(sp["color"]), width=0)
        for sp in SITEPARTS:
            if sp["kind"] != "text":
                continue
            fs_ = sp["size"] / 0.72 * MM
            e_ = sp["size"] / 0.72
            by_ = sp["y"] + {"center": -0.35 * e_, "top": -0.88 * e_, "bottom": 0.12 * e_}.get(sp["va"], 0.0)
            w_ = _FNT[bool(sp["bold"])].text_length(sp["s"], fs_) / MM
            bx_ = sp["x"] - {"center": w_ / 2, "right": w_}.get(sp["ha"], 0.0)
            pg.insert_text(fitz.Point(bx_ * MM, (H - by_) * MM), sp["s"], fontsize=fs_, fontname="F_B" if sp["bold"] else "F_R",
                           fontfile=FONTB if sp["bold"] else FONT, color=_hx(sp["color"]))
# 提出の5枚は sodachiya/presentation.pdf の一つだけ（ユーザー、10-24：前は5枚と「全体＋5枚」の2つがあった）。
# 壁に貼ったときの全体は present/out/sodachiya_present_overview.pdf（ベクターのPDF、ユーザー、10-24夜：リポジトリの画像はPDFに）
sheets = os.path.join(ROOT, "presentation.pdf")
doc.save(sheets)

# 素材（present/sozai/）：mock.pyが描いた図は範囲を切り抜いて一つずつPDFに（ベクター、文字はType42）。
# ほかの係の図は元のPDFの場所と切り抜く範囲を一覧に。中身が変わった素材だけ日時を進める（state.json）
import hashlib, datetime, re, subprocess as _sp
SZ = os.path.join(HERE, "sozai")
os.makedirs(SZ, exist_ok=True)
_stp = os.path.join(SZ, "state.json")
try:
    _st = json.load(open(_stp, encoding="utf-8"))
except Exception:
    _st = {}
_now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
_rows = []
SOZFN, SITEMAP = {}, {}
for key, name, sh_, (x, y, w, h), note in SOZAI:
    fn = f"{key}_{re.sub(r'[　 ]+', '_', name.split('（')[0].strip()).replace('/', '-').replace(':', '')}.pdf"
    SOZFN[key] = fn
    nd = fitz.open()
    pg_ = nd.new_page(width=w * MM, height=h * MM)
    pg_.show_pdf_page(pg_.rect, doc_clean, sh_ - 1, clip=fitz.Rect(x * MM, (H - y - h) * MM, (x + w) * MM, (H - y) * MM))
    hs = hashlib.md5(pg_.get_pixmap(dpi=40).samples).hexdigest()
    nd.save(os.path.join(SZ, fn), garbage=3, deflate=True)
    nd.close()
    old = _st.get(fn, {})
    _st[fn] = dict(hash=hs, updated=old.get("updated", _now) if old.get("hash") == hs else _now)
    _rows.append(f"| {key} | `{fn}` | {name} | {sh_}枚目 | {w:.0f}×{h:.0f} | {_st[fn]['updated']} | {note} |")
for key, name, gr_nm, note in SOZAI_FILES:                    # 配置図の三つ（線・色・文字、同じ大きさ・同じ位置）
    gr = {"線": "l", "色": "c", "文字": "t", "風と視線": "o", "太陽": "s"}[gr_nm]
    fn = f"{key}_配置図_1-200_{gr_nm}.pdf"
    SITEMAP[_SITE_PDF[gr]] = fn
    nd = fitz.open()
    pg_ = nd.new_page(width=bsw * MM, height=bsh * MM)                    # 大きい方の窓（Illustratorで切り抜く）
    pg_.show_pdf_page(pg_.rect, fitz.open(_SITE_PDF[gr]), 0, clip=fitz.Rect(bsx * MM, (H - bsy - bsh) * MM, (bsx + bsw) * MM, (H - bsy) * MM))
    hs = hashlib.md5(pg_.get_pixmap(dpi=40).samples).hexdigest()
    nd.save(os.path.join(SZ, fn), garbage=3, deflate=True)
    nd.close()
    old = _st.get(fn, {})
    _st[fn] = dict(hash=hs, updated=old.get("updated", _now) if old.get("hash") == hs else _now)
    _rows.insert(len([r_ for r_ in _rows if r_.startswith("| 01")]), f"| {key} | `{fn}` | {name} | 1枚目 | {bsw:.0f}×{bsh:.0f}（見本は{sw:.0f}×{sh:.0f}で切り抜き） | {_st[fn]['updated']} | {note} |")
for _old in ("01_配置図_1-200.pdf", "01e_配置図_1-200_太陽.pdf"):          # 太陽の素材（空）は外す（ユーザー、10-26夕）
    if os.path.exists(os.path.join(SZ, _old)):
        os.remove(os.path.join(SZ, _old))
    _st.pop(_old, None)
# 00 枠（全ページ共通、ユーザー、10-25：Illustratorでシンボルにする）：外枠・上の帯の線・表題・ページ・サブタイトル・右下の名前。地は透明
figF = plt.figure(figsize=(W / 25.4, H / 25.4))
axF = figF.add_axes([0, 0, 1, 1]); axF.set_xlim(0, W); axF.set_ylim(0, H); axF.axis("off")
axF.add_patch(Rectangle((M, M), W - 2 * M, H - 2 * M, fill=False, lw=0.6, ec=INK))
axF.plot([M, W - M], [H - M - 16, H - M - 16], color=INK, lw=0.4)
T(axF, M + 4, H - M - 11, "こどもたちの育ち舎", 6.5, bold=True)
T(axF, M + 92, H - M - 11, "1/5", 5.0, bold=True)
T(axF, M + 106, H - M - 11, "サブタイトル", 5.0, bold=True)
T(axF, W - M - 4, M + 4, "建築設計実習Ⅱ—Ⅰ　2026.11.05　木田", 3.0, ha="right")
_fn0 = "00_枠.pdf"
figF.savefig(os.path.join(SZ, _fn0), transparent=True)
plt.close(figF)
_hs0 = hashlib.md5(fitz.open(os.path.join(SZ, _fn0))[0].get_pixmap(dpi=40).samples).hexdigest()
_o0 = _st.get(_fn0, {})
_st[_fn0] = dict(hash=_hs0, updated=_o0.get("updated", _now) if _o0.get("hash") == _hs0 else _now)
_rows.append(f"| 00 | `{_fn0}` | 枠（外枠・上の帯の線・表題・ページ・サブタイトル・右下の名前） | 全ページ | {W:.0f}×{H:.0f} | {_st[_fn0]['updated']} | シンボルにして5枚に。ページとサブタイトルは各ページで書き換える |")
_rows.sort(key=lambda r_: r_.split("|")[1].strip())
_ext = []
for sh_ in range(1, 6):
    for src, pno, clip, (x, y, w, h) in embeds[sh_]:
        rel = os.path.relpath(src, ROOT)
        _ext.append(f"| {sh_}枚目 | `{rel}` | {'全体' if clip[0] == 0 and clip[1] == 0 else '切り抜き (%.0f, %.0f)–(%.0f, %.0f) mm' % tuple(clip)} | {w / (clip[2] - clip[0]):.2f} 倍 |")
json.dump(_st, open(_stp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(os.path.join(SZ, "README.md"), "w", encoding="utf-8").write("\n".join([
    "# プレゼンの素材（`present/mock.py`が書き出す）", "",
    "ユーザー（10-25）：割付の見本は`sodachiya/presentation.pdf`。ユーザーは素材から .ai を作り、見本に倣って仕上げる。素材が変わったらプレゼンの準備が知らせる。",
    "「最後に変わった」は中身（絵）が変わったときだけ進む。文字は Type42（Noto Sans CJK JP）なので Illustrator でヒラギノに置き換えられる。", "",
    "## mock.pyが描いた図（このフォルダのPDF）", "",
    "| 番号 | ファイル | 中身 | 見本の位置 | 大きさ（mm） | 最後に変わった | 注 |", "|---|---|---|---|---|---|---|", *_rows, "",
    "## ほかの係の図（元のPDFをそのまま使う）", "",
    "| 見本の位置 | ファイル（`sodachiya/`から） | 使う範囲（元のPDFのmm、左上から） | 倍率 |", "|---|---|---|---|", *_ext, ""]))

# Illustratorの割付（present/ai/layout.json と部品のPDF、ユーザー、10-25夕：部品ごとに動かせる .ai をスクリプトで組む）
import ai_layout
ai_layout.write(dict(siteparts=SITEPARTS, figs=figs, rec=AIREC, sozai=SOZAI, sozfn=SOZFN, sitemap=SITEMAP, sitebig=[bsx, H - bsy - bsh, bsw, bsh], anchors={"p1.siteplan": PLAN_ANCHOR}, anchors_prev={"p1.siteplan": PLAN_ANCHOR_PREV}, embeds=embeds, topl=TOPL, topt=TOPT,
                     renumber=dict(id="2026-10-28b", maps={"2026-10-28": {"4": 2, "5": 3, "2": 4, "3": 5}, "_none": {"5": 3, "3": 4, "4": 5}},
                                   note="ユーザー、10-28 13:17：5枚の番号を振り直した（前の番号 → 新しい番号）。maps のキーは前に組んだときの renumber の id（_none は最初の番号）。前の .ai の木田さんの物は build で新しい番号の枚へ写す"),
                     W=W, H=H, MM=MM, NOTE=NOTE, INK=INK, ROOT=ROOT, HERE=HERE))

# 壁に貼ったときの全体（3列：1 ｜ 2・3 ｜ 4・5）。枠と注をmatplotlibで描き、5枚はPDFのまま縮めて貼る
fig = plt.figure(figsize=(841 / 25.4, 594 / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
SC = 594 / 2500                       # 壁のmm → 紙のmm
ax.set_xlim(0, 841 / SC)
ax.set_ylim(0, 2500)
ax.axis("off")
x0w, base_ = 250, 350
_cx = lambda c_: x0w + c_ * (841 + 120)
_top = base_ + 594 + 60
pos = {1: (_cx(0), base_ + (594 + 60) / 2), 2: (_cx(1), _top), 3: (_cx(1), base_), 4: (_cx(2), _top), 5: (_cx(2), base_)}
# 壁の並び（ユーザー、10-28 13:17）：3列「1 ｜ 2・3 ｜ 4・5」。1は二段の真ん中の高さ。立面（2）の下に断面（3）、平面（4）の下に一日の帯（5）。
# 読む順は外から中へ：敷地→外から見た姿と切った姿→中の平面と暮らし。濃い面（配置図・色の平面）と軽い面（線の立面・断面）が濃・淡・濃。
# 1の川の辺の右に沿川の景観立面。主題（こどもたちの環境）で締める
for i in range(5):
    x, y = pos[i + 1]
    ax.add_patch(Rectangle((x, y), 841, 594, fill=False, ec="#555555", lw=0.5, zorder=2))
ax.plot([100, 3300], [0 + 5, 5], color=INK, lw=1)
ax.plot([100, 3300], [1500, 1500], color=NOTE, lw=0.8, ls=(0, (6, 4)))
def TW(x, y, s, size, **kw):  # sizeは紙のmm
    T(ax, x, y, s, size, **kw)
TW(110, 1515, "目の高さ1.5 m", 3.2, color=NOTE)
TW(110, 20, "床", 3.2)
TW(x0w, 2400, "壁に貼ったとき　3列：1 ｜ 2・3 ｜ 4・5（1は二段の真ん中）", 6.0, bold=True)
notes = ["1　敷地と自然環境・地域（二段の真ん中）。",
         "その右に2　景観（立面図1/100、下の段に沿川の景観立面）、その下に3　断面と環境（断面図1/100）。",
         "その右に4　平面図、その下に5　動線とこどもたちの環境（一日の帯は平面図の続き）。",
         "外から中へ：敷地→外から見た姿と切った姿→中の平面と暮らし。",
         "2・3・4枚目の立面・断面・平面は3dmから自動の図を実寸で貼る。"]
for i, s_ in enumerate(notes):
    TW(x0w, pos[1][1] - 80 - i * 70, s_, 3.2, color=NOTE)
ov = os.path.join(OUT, "_overview.pdf")
fig.savefig(ov)
plt.close(fig)
_od = fitz.open(ov)
_pg = _od[0]
for i in range(5):
    x, y = pos[i + 1]
    _pg.show_pdf_page(fitz.Rect(x * SC * MM, (594 - (y + 594) * SC) * MM, (x + 841) * SC * MM, (594 - y * SC) * MM), doc, i)
_od.save(os.path.join(OUT, "sodachiya_present_overview.pdf"), garbage=3, deflate=True)
_od.close()

for f in (base, ov, *_SITE_PDF.values()):
    os.remove(f)
json.dump(dict(info, areas={k: round(v, 1) for k, v in AREA.items()}), open(os.path.join(OUT, "mock_info.json"), "w"), ensure_ascii=False, indent=1)
print("ok")
