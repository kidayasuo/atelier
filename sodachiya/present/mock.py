"""育ち舎　提出A1×5枚の仮の割付（プレゼンの準備のチャット）

実寸の確認が目的：3dm（sodachiya_exact_mesh.3dm）から平面・配置・立面の外形を
その縮尺のまま描き、自動の断面（drawings/）や他のチャットの図（out/）を
実寸または縮小で貼り込む。未作成のものは破線の枠（大きさは実寸）で示す。
紫の文字は割付の注記（本番では消す）。

python sodachiya/present/mock.py  →  sodachiya/presentation.pdf（5枚）／ present/out/ の全体の画像
"""
import os, re, subprocess, sys, json, glob
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
HDR = 24.0                     # 上の帯の高さ（mm、10-29 15:16：16→21、16:02：40 pt の表題で24）
HDR_BL = 17.0                  # 帯の上端から字の基準線まで
PT2MM = 0.3528 * 0.72          # Illustrator の pt → 文字の高さ（mm）
SCHOOL = "松ヶ崎こども園"        # 枠の表題（ユーザー 10-29 16:02、前は「こどもたちの育ち舎」）
NAME_SZ, THEME_SZ, THEME_X = 40 * PT2MM, 40 * PT2MM, 112.0   # 園の名前・テーマの字（40 pt）、テーマの左（M から）
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
C_SHARE = "#F6E3A4"            # こどものみんなの場所：遊戯室（はれのまは10-29に遊戯室の入り口へ）
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
    _lv = LIVE_TXT[0]
    if _lv is not None and ax is _lv["ax"] and s and matplotlib.colors.to_hex(color) != matplotlib.colors.to_hex(NOTE):
        # 図の中の文字を図に焼き込まず、一つずつ Illustrator の部品に（図ごとのグループ、ユーザー 10-30 23:07）。見本には後から重ねる（TOPT）
        e_ = size / 0.72
        by_ = y + {"center": -0.35 * e_, "top": -0.88 * e_, "bottom": 0.12 * e_}.get(va, 0.0)
        TOPT[_lv["sheet"]].append((x, by_, s, size, bold, kw.get("font"), matplotlib.colors.to_hex(color),
                                   dict(id="t." + re.sub(r"[\s　/\\|:]+", "", s)[:14], name=s[:24], align=ha if ha in ("left", "center", "right") else "left",
                                        group=_lv["group"], group_name=_lv["name"])))
        LIVE_N[0] += 1
        return
    kw.pop("group", None)
    fnt = kw.pop("font", None)                     # Illustratorで使う書体の名前（無ければヒラギノ）。見本では似た書体で
    pt = size / 0.3528 / 0.72
    ax.text(x, y, s, fontsize=pt, color=color, ha=ha, va=va,
            fontproperties=FontProperties(fname=FONT_ALT.get(fnt, FONTB if bold else FONT), size=pt), **kw)
    if s:
        _airec(ax.figure, kind="text", x=x, y=y, s=s, size=size, color=color, bold=bold, ha=ha, va=va, font=fnt)


LIVE_TXT = [None]   # dict(ax, sheet, group, name)：このあいだの T は部品の文字（TOPT）に
LIVE_N = [0]


def _live(ax_, sheet_, group_, name_):
    LIVE_TXT[0] = dict(ax=ax_, sheet=sheet_, group=group_, name=name_) if group_ else None


FRAME_TOP = {3, 4}   # 4枚目も周りの図の上に枠（10-30 18:05）。 枠を図の上に重ねる紙（3枚目は1階の平面図が紙いっぱいで白い地、ユーザー 10-29 18:01。10-30 の6枚で4枚目→3枚目）


PAGE_TITLES = {}


def frame(ax, no, theme, focus, order):
    PAGE_TITLES[no] = f"{no}{theme}"
    AIMUTE[0] += 1
    ax.add_patch(Rectangle((M, M), W - 2 * M, H - 2 * M, fill=False, lw=0.6, ec=INK, gid="aipart"))
    ax.plot([M, W - M], [H - M - HDR, H - M - HDR], color=INK, lw=0.4, gid="aipart")
    T(ax, M + 4, H - M - HDR_BL, SCHOOL, NAME_SZ, bold=True)
    T(ax, M + THEME_X, H - M - HDR_BL, f"{no}{theme}", THEME_SZ, bold=True)
    T(ax, W - M - 4, M + 4, "建築設計実習Ⅱ—Ⅰ　2026.11.05　木田", 3.0, ha="right")   # 名前などは右下（ユーザー、10-25）
    # 注記
    T(ax, M + 4, M - 6, f"［割付の注記］フォーカス：{focus}　／　目に入る順：{order}", 3.2, NOTE)
    AIMUTE[0] -= 1
    _airec(ax.figure, kind="frame", top=no in FRAME_TOP)
    _airec(ax.figure, kind="text", id="pagetitle", name="ページとサブタイトル", x=M + THEME_X, y=H - M - HDR_BL, s=f"{no}{theme}", size=THEME_SZ, color=INK, bold=True, ha="left", va="baseline")
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


TITLE_GAP = 2.5                                  # 図・絵・表の題は絵の上、左揃え。絵の上端から題の基準線まで（ユーザー 10-29 15:27：上にそろえる）


def _topalign(sheet, top):
    """直前に置いた図（embeds の最後）を、上端が top にそろうように下から上へ寄せる（fit で縮んだ分）"""
    src_, pno_, clip_, (x_, y_, w_, h_) = embeds[sheet][-1]
    embeds[sheet][-1] = (src_, pno_, clip_, (x_, top - h_, w_, h_))


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


def draw_plan(ax, ox, oy, scale, x0, y0, wbox, hbox, keyhi=None, thin=False, outdoor=True):
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
            if not outdoor:                         # ゾーニング（10-30）：外構は別に塗る
                continue
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

embeds = {i: [] for i in range(1, 7)}
EMB_DWG = {}  # (枚, embeds の番号) → 図面のグループに入れる重ね（採光の図を断面図Dのグループに、10-29）
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


TOPT = {i: [] for i in range(1, 7)}     # 貼った図の上に置く文字（紙のmm、左下）：(x, y, 文字, 高さmm, 太字)
TOPL = {i: [] for i in range(1, 7)}     # 貼った図の上に描く引き出し線（紙のmm）：(点, 箱の端, 色)


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


# 1枚目の説明の箱は案H（ユーザー、10-28 14:04）：枠と塗りなし、見出しの頭に番号の印（自然＝青の○、地域＝茶の□、白抜きの数字）、
# 配置図の上の点にも同じ印（引き出し線なし）。印は一つずつ Illustrator の部品（○か□と数字のグループ）
MARKS = []          # dict(id, cat, num, cx, cy（紙のmm、下原点）, r, ring, group, group_name, follow)
MARK_R_BOX, MARK_R_PLAN = 4.3, 4.3                  # 箱の印は見出し 20 pt に合わせて大きく（10-29 16:02）。配置図の上の印も同じ大きさ（10-30）
MARK_NUM_BOX = 15.5 * PT2MM  # 箱の印の数字（15.5 pt、10-29 17:49）
MARK_NUM = MARK_NUM_BOX      # 配置図の上の印の数字も箱と同じ（ユーザー 10-30）
HIND = 1 + 2 * MARK_R_BOX + 2.5                     # 見出しと本文の字下げ（印の幅）


BOX_TS, BOX_FS = 20 * PT2MM, 14 * PT2MM             # 1枚目の説明の箱：見出し（W6）20 pt、本文（W3）14 pt（ユーザー 10-29 16:02、10-30 22:17 本文だけ14 pt）
BOX_TOP, BOX_BODY = 9.0, 20.0                        # 箱の上端から見出しの基準線・本文の1行目の基準線まで


def ibox_h(ax, x, y, w, h, title, lines, color, cat, num, key, size=BOX_FS):
    """案Hの説明の箱。部品は ibox.{key}.mark（印）・.title（見出し）・.text（本文）。番号は MARKS で描く"""
    hy = y + h - BOX_TOP
    tx = x + HIND
    _airec(ax.figure, kind="text", id=f"ibox.{key}.title", name=f"見出し：{title}", x=tx, y=hy, s=title, size=BOX_TS, color=color, bold=True, ha="left", va="baseline")
    _airec(ax.figure, kind="area", id=f"ibox.{key}.text", name=f"本文：{title}", x=tx, y=y + h - BOX_BODY, w=w - HIND - 3, h=h - BOX_BODY - 1,
           s="\n".join(lines), size=size, color=INK, bold=False, leading=1.5, para_space=1.0)
    MARKS.append(dict(id=f"ibox.{key}.mark", cat=cat, num=num, cx=x + 1 + MARK_R_BOX, cy=hy + 0.35 * BOX_TS / 0.72, r=MARK_R_BOX, ring=False,
                      group=f"ibox.{key}.mark", group_name=f"印（箱）　{title}", key=key))
    AIMUTE[0] += 1
    T(ax, tx, hy, title, BOX_TS, color, bold=True)
    yy = y + h - BOX_BODY
    for ln_ in lines:
        for s_ in jwrap(ln_, (w - HIND - 3) / (size / 0.72)):
            T(ax, tx, yy, s_, size)
            yy -= size / 0.72 * 1.5
        yy -= size / 0.72
    AIMUTE[0] -= 1
SEC = os.path.join(ROOT, "drawings", "sodachiya_sections_1-100.pdf")
CLIP_A = (25, 38, 841, 201)
CLIP_B = (25, 244, 410, 377)
CLIP_C = (430, 244, 812, 377)


# 課題の要求の図面は Rhino 経由（決定事項（共通）、ユーザー 10-28 17:54）：平面・断面・立面は、木田さんが Rhino で出した線
# drawings_rhino/<紙の名前>.pdf（rhino/zumen.py、線だけ・元のレイヤーごと、drawings/ の図と同じ紙・同じ位置）に、
# drawings/<紙の名前>_文字.pdf（文字と寸法だけ）を重ねる。Rhino の図が無い・切り抜く所に線が無い（断面Aの弧の展開はまだ描かない）ときは今の自動の図のまま
RHINO_DIR = os.path.join(ROOT, "drawings_rhino")
RHINO_MAP = {   # drawings/ の自動の図 → drawings_rhino/ の名前（zumen.py は drawings/<名前>_views.json の <名前> で書く）
    "sodachiya_plan_1-100.pdf": "sodachiya_plan_1-100.pdf",
    "sodachiya_elevations_1-100.pdf": "sodachiya_elevations_1-100.pdf",
    "sodachiya_elevations2_1-100.pdf": "sodachiya_elevations2_1-100.pdf",
    "sodachiya_sections_1-100.pdf": "sodachiya_sections_1-100.pdf",
    "sodachiya_sections2_1-100.pdf": "sodachiya_sections2_1-100.pdf",   # 断面D（更新係が別の紙にしたとき）
}
RHINO_TXT = {}      # (枚, embeds の番号) → 上に重ねる文字と寸法のPDF
RHINO_USED = []


def _rhino_of(src, pageno, clip):
    """自動の図 src の Rhino の線の図（と文字の図）。切り抜く所に線が無ければ None"""
    nm = RHINO_MAP.get(os.path.basename(src))
    if not nm or os.path.dirname(os.path.abspath(src)) != os.path.join(ROOT, "drawings"):
        return None
    rp_, tp_ = os.path.join(RHINO_DIR, nm), src[:-4] + "_文字.pdf"
    if not (os.path.exists(rp_) and os.path.exists(tp_)):
        return None
    try:
        pg_ = fitz.open(rp_)[pageno]
        cr_ = fitz.Rect(clip[0] * MM, clip[1] * MM, clip[2] * MM, clip[3] * MM) if clip else pg_.rect
        if not any(fitz.Rect(d_["rect"]).intersects(cr_) for d_ in pg_.get_drawings()):
            print("Rhino の図", nm, "の切り抜く所に線が無い：自動の図のまま", clip)
            return None
    except Exception as e_:
        print("Rhino の図", nm, "を読めない：自動の図のまま", e_)
        return None
    return rp_, tp_


DWG = {}            # (枚, embeds の番号) → 課題の要求の図面（文字と寸法をIllustratorの部品にする、ユーザー 10-29 0:16）


def embed(sheet, src, clip, x, y, scale_factor=1.0, pageno=0, fit=None, dwg=None, dwg_opt=None):
    """clip（元のPDFのmm、上原点）を、紙の(x,y)（下原点、左下）に倍率scale_factorで置く。
    fit=(w,h)を渡すと、その枠に縮めて入れる。戻り値は置いた大きさ（mm）。
    dwg=(鍵, 名前)：課題の要求の図面。.ai では線だけのリンクと、文字の層（<図>_文字.pdf）の文字と寸法の部品を、名前のグループに"""
    if clip is None:
        pr = fitz.open(src)[pageno].rect
        clip = (0, 0, pr.width / MM, pr.height / MM)
    w0, h0 = clip[2] - clip[0], clip[3] - clip[1]
    if fit:
        scale_factor = min(fit[0] / w0, fit[1] / h0)
    w, h = w0 * scale_factor, h0 * scale_factor
    rh_ = _rhino_of(src, pageno, clip)
    if dwg and os.path.exists(src[:-4] + "_文字.pdf"):
        DWG[(sheet, len(embeds[sheet]))] = dict(key=dwg[0], name=dwg[1], auto=src, moji=src[:-4] + "_文字.pdf", rhino=bool(rh_), src=rh_[0] if rh_ else src,
                                                **(dwg_opt or {}))   # dwg_opt：parts_clip・exclude・noparts（10-30：1階の平面図を三つの四角で切り抜くとき）
    if rh_:                                        # Rhino の線を下に、文字と寸法を上に（同じ切り抜き・同じ位置）
        RHINO_TXT[(sheet, len(embeds[sheet]))] = rh_[1]
        RHINO_USED.append(f"{sheet}枚目 {os.path.basename(src)}")
        src = rh_[0]
    embeds[sheet].append((src, pageno, clip, (x, y, w, h)))
    return w, h


figs = []
FIGS = {}           # 枚の番号 → 図（6枚、先生のエスキス 10-30）。最後に番号の順に figs へ

# ================================================================ 1　敷地と応答
fig, ax = page()
frame(ax, 1, "敷地と自然環境・地域", "周囲の自然環境との関係と地域環境への配慮。配置図の上に夏の夜の風・比叡への視線",
      "タイトルと趣旨 → 真ん中の配置図 → 左右の箱（青＝自然環境、茶＝地域）→ 用水のネットワーク・地域のなかの敷地")
top = H - M - HDR
T(ax, M + 6, top - 15, "地に足をつけて育つ", 40 * PT2MM, bold=True)   # 40 pt（ユーザー 10-29 16:02）
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


CSZ, CCH = 20 * PT2MM, 29                        # 設計趣旨：20 pt、1行29字（ユーザーの箱の幅 206 mm、10-29 16:02）
_y = top - 28
_airec(fig, kind="area", id="concept", name="設計趣旨", x=M + 6, y=_y, w=CCH * CSZ / 0.72 + 1, h=0, s="\n".join(p_.lstrip("　 ") for p_ in _paras),
       size=CSZ, color=INK, bold=False, leading=1.5, para_space=1.0)
_ystart = _y
AIMUTE[0] += 1
for _p in _paras:
    for s in jwrap(_p.lstrip("　 "), CCH):     # 一字下げしない（ユーザー、10-25夕）
        T(ax, M + 6, _y, s, CSZ)
        _y -= CSZ / 0.72 * 1.5        # 行送りは文字の1.5倍（ユーザー、10-25夕）
    _y -= CSZ / 0.72                  # 段落のあいだは1行分（ユーザー、10-25夕）
AIMUTE[0] -= 1
AIREC[-1]["h"] = _ystart - _y + 6
CONCEPT_BOT = _y - 6                                     # 設計趣旨の下端（左の箱の列はここから下）
dimnote(ax, M + 6, _y + 1, f"設計趣旨 約{len(concept.replace(' ', ''))}字（課題は300字程度）。文字20 pt（5.1 mm）")
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



def lab(ax, xfun, P3, text, dxy=(0, 0), size=3.0, color=INK, ha="left", lead=True, bold=False):
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
NAT = [("用水を借りる", ["高野川の上の堰で取った水が、松ヶ崎の田を潤してきた用水の網を巡る。その水を借りる。", "北の道の下の暗渠から敷地の北の角へ、おくのもりのみなもとに湧き出し、小川になって高野川へ返る。"]),
       ("山から川へ", ["みなもとから縁側の前・原っぱを流れ、護岸の溝を滑り落ちて高野川に合流するまでを、こどもが追える。", "雨は樋に隠さず、雨の川から同じ溝で川へ。"]),
       ("比叡と高野川のうつし", ["築山は比叡のうつし。ホールから頂の向こうに比叡が見える。", "小川は高野川のうつし。足もとを掘った土で築山を盛る。"]),
       ("地下の水と北山の木も借りる", ["松ヶ崎は地面を走る用水と地下の水の両方が豊か。涌泉寺の井戸に見るように井戸水が豊富で、その地下水も借りる。", "京都北山の北山杉の間伐材141本を、ホールの林に立てる。"])]
cy = M + 8 + 26.0 + 400                          # 上の段の下端の目安（配置図の上）

# 配置図1/200：敷地＋西の道路と向かいの住宅、北は大学の角、南は高野川の河川敷まで
VX0, VX1, VY0, VY1 = -26.0, QX1 + 2.0, -21.0, QY1 + 8.0  # 南へ延ばして高野川が見えるように、北は用水路の尻尾をやめて矢印と名前だけ（ユーザー、10-26夕）
sw, sh = (VX1 - VX0) * 5, (VY1 - VY0) * 5
sx, sy = M + 6, H - M - 16 - 3 - sh                            # 配置図は上の帯のすぐ下まで上げる（ユーザー、10-26：配置図の注を消し、下の景観立面との窮屈さを解く）   # 帯を太くしても配置図は動かさない（ユーザーの切り抜きと目印のまま、10-29）
sx = (W - sw) / 2                                            # 配置図を紙の真ん中に（ユーザー）
P1_BOT = M + 10                                              # 下の帯（沿川の景観立面）は2枚目（景観）へ移した（ユーザー、10-27夜：景観の枚の方が親和性が高い）。下の端の目安
# 題は図の下に、大きく（ユーザー、10-26）。配置図が紙の上下いっぱいになったので（10-28）、題は図の上に重ねる文字（配置図のまとめのグループに入る）
TOPT[1].append((sx + 120, sy - 18, "配置図", 6.0, True, None, INK, dict(id="t.配置図", name="配置図の題", plan=True)))
TOPT[1].append((sx + 120 + 3 * 8.4 + 4, sy - 18, "1/200　高野川を下に（川向こうから見る向き、北は右上）", 3.4, False, None, INK,
                dict(id="t.1200高野川を下に（川向こ", name="配置図の縮尺と向き", plan=True)))
xf = xform(sx, sy, 200, VX0, VY0)
# 素材の配置図は見せる窓より大きく描き、Illustratorの切り抜きの四角で使う大きさを選ぶ（ユーザー、10-26夕）
# 上下は紙いっぱい（ユーザー、10-28 18:01：「上下いっぱいの幅を作ってください。おそらく枠でクリップします」）。見本の位置と、木田さんが .ai で
# 配置図を動かした位置の両方で、紙の上の縁（0）から下の縁（H）まで素材があるように、北と南へ延ばす（5 m 刻み、ゆとり 25 mm）。東西は今のまま
try:
    _lu = json.load(open(os.path.join(HERE, "ai", "layout_user.json"), encoding="utf-8"))
except Exception:
    _lu = {}
_org = xf(np.array([[0.0, 0.0]]))[0]
O_M = (float(_org[0]), float(H - _org[1]))                    # 見本の配置図の原点（3dmを回した座標の(0,0)、紙の左上からmm）
_ua0 = _lu.get("anchors", {}).get("p1.siteplan") or {}
_u01 = _lu.get("parts", {}).get("p1.sozai.01a") or {}
MAT_LEGACY = (-(VX0 - 12.0) * 5, (VY0 - 6.0) * 5)            # 10-28 夕までの素材：原点は素材の左から190 mm、下から135 mm（西へ12 m・南へ6 m 広く描いた）
if "x" in _u01 and "h" in _u01:                               # .ai の配置図の原点 ＝ 素材01aの左上 ＋ 素材の中の原点の位置（組んだときの anchors の mat）
    _mo = _ua0.get("mat") or [MAT_LEGACY[0], _u01["h"] + MAT_LEGACY[1]]
    O_U = (_u01["x"] + _mo[0], _u01["y"] + _mo[1])
else:
    O_U = O_M
BX0, BX1 = VX0 - 12.0, VX1 + 10.0
BY1 = 5.0 * np.ceil((max(O_M[1], O_U[1]) + 25.0) / 25.0)                  # 北：紙の上の縁まで
BY0 = -5.0 * np.ceil((H - min(O_M[1], O_U[1]) + 25.0) / 25.0)             # 南：紙の下の縁まで（高野川と向こう岸）
bsx, bsy = sx + (BX0 - VX0) * 5, sy + (BY0 - VY0) * 5
bsw, bsh = (BX1 - BX0) * 5, (BY1 - BY0) * 5
SITE_SHIFT = (round(O_U[0] - O_M[0], 2), round(O_U[1] - O_M[1], 2))       # 木田さんが .ai で配置図を動かした分（見本 → .ai）
_usc = _lu.get("siteclip")
# 見せる窓（切り抜きの四角）：上下は内枠いっぱい（M〜H−M）。左右は木田さんの四角（.ai の座標から見本の座標へ戻す）、無ければ今の窓
SCX0, SCX1 = ((_usc["x"] - SITE_SHIFT[0], _usc["x"] + _usc["w"] - SITE_SHIFT[0]) if _usc else (sx, sx + sw))
print(f"配置図の素材：北へ{BY1:.0f} m・南へ{-BY0:.0f} m（{bsw:.0f}×{bsh:.0f} mm）、.ai で動かした分 {SITE_SHIFT}")
# 図の置き場所の目印（3dmを回した座標の(0,0)が紙のどこか、左上からmm）。前の窓（南−6 m、北＋14 m）からのずれで、木田さんの描いた物を一緒に動かす
_top = sy + sh
_org_prev = (sx + (0 - VX0) * 5, _top - (QY1 + 14.0) * 5)
PLAN_ANCHOR = dict(origin=[round(O_M[0], 2), round(O_M[1], 2)], window=[round(SCX0, 2), M, round(SCX1 - SCX0, 2), H - 2 * M])
PLAN_ANCHOR_PREV = dict(origin=[round(_org_prev[0], 2), round(H - _org_prev[1], 2)],
                        window=[round(sx, 2), round(H - _top, 2), round(sw, 2), round((QY1 + 14.0 + 6.0) * 5, 2)])
# layout.json の目印は .ai に置く位置（木田さんが動かした配置図の上）。mat ＝ 素材の左上から原点まで（次に .ai から原点を求める）、clipv ＝ 切り抜きを上下いっぱいにした版
PLAN_ANCHOR_AI = dict(origin=[round(O_U[0], 2), round(O_U[1], 2)], window=[round(SCX0 + SITE_SHIFT[0], 2), M, round(SCX1 - SCX0, 2), H - 2 * M],
                      mat=[round((0 - BX0) * 5, 2), round(BY1 * 5, 2)], mat_legacy=[round(MAT_LEGACY[0], 2), round(MAT_LEGACY[1], 2)], clipv="full-1028")
# 見本に描く木田さんの物は、.ai の配置図の位置から見本の配置図の位置へ動かす（.ai で配置図ごと動かしたとき、ユーザー 10-28）
if "x" in _u01:
    _udx, _udy = -SITE_SHIFT[0], -SITE_SHIFT[1]
    _uwin = [_usc["x"], _usc["y"], _usc["w"], _usc["h"]] if _usc else [sx + SITE_SHIFT[0], H - sy - sh + SITE_SHIFT[1], sw, sh]
else:                                                          # 素材の記録が無い：前に組んだときの目印から
    _ua = _ua0 or PLAN_ANCHOR_PREV
    _udx, _udy = O_M[0] - _ua["origin"][0], O_M[1] - _ua["origin"][1]
    _uwin = _ua["window"]


def _shift_ui(d, dx, dy):
    if "x" in d: d["x"] += dx
    if "y" in d: d["y"] += dy
    if d.get("pts"): d["pts"] = [[[q[0] + dx, q[1] + dy] for q in pt_] for pt_ in d["pts"]]
    for ch in d.get("children", []) or []: _shift_ui(ch, dx, dy)


if abs(_udx) + abs(_udy) > 0.05:
    _w = _uwin
    for _ui in USER_ITEMS.get(1, []):
        _cx, _cy = _ui.get("x", 0) + _ui.get("w", 0) / 2, _ui.get("y", 0) + _ui.get("h", 0) / 2
        if _w[0] <= _cx <= _w[0] + _w[2] and _w[1] <= _cy <= _w[1] + _w[3]:
            _shift_ui(_ui, _udx, _udy)
# 配置図は別の図に描き、線・色・文字の三つに分けて書き出す（ユーザー、10-25朝：配置図として書き、その上に色、文字。
# 園庭のチャットの図（garden01）は重ねない。屋根・外構・園庭はすべて3dmから）。1枚目にはこの三つを重ねて貼る
_ax_page, _fig_page = ax, fig
# 配置図の素材の紙（ユーザー 10-28：紙の上下いっぱい）。素材は A1 の紙の外まで描くので、図は縦に長い紙に描く：
# 下の端 YB・上の端 YT（見本の紙の下原点のmm）。この紙の左上からのmm ＝ 見本の紙の左上からのmm ＋ SDY_
YB, YT = min(0.0, float(bsy) - 1.0), max(H, float(bsy + bsh) + 1.0)
HS, SDY_ = YT - YB, YT - H
figS = plt.figure(figsize=(W / 25.4, HS / 25.4))
ax = figS.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(YB, YT); ax.axis("off")
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
lab(ax, xf, R3inv([14.0, -5.6])[0], "高野川", (0, 0), size=3.4, color="#2F6FA0", bold=True)
lab(ax, xf, np.array(gc.PARK.centroid.coords[0]), "小竹薮公園", (0, 0), ha="center", lead=False)
# 建物と園庭の名前（部屋の名前・スパンの番号・園庭のチャットの記号は描かない、ユーザー 10-25）
_RS = lambda P: np.c_[np.atleast_2d(P)[:, 0] * np.cos(_rr) - np.atleast_2d(P)[:, 1] * np.sin(_rr), np.atleast_2d(P)[:, 0] * np.sin(_rr) + np.atleast_2d(P)[:, 1] * np.cos(_rr)]
def _zl(g_s, text, dxy=(0, 0), size=3.2, color="#3F5F2F", bold=True):
    q = xf(_RS(np.array(g_s.representative_point().coords[0])))[0] + np.array(dxy)
    T(ax, q[0], q[1], text, size, color, ha="center", va="center", bold=bold)
def _zl3(pref, text, dxy=(0, 0), size=3.2, color=INK, bold=True):
    U_ = _U(pref)
    q = xf(np.array(U_.representative_point().coords))[0] + np.array(dxy)
    T(ax, q[0], q[1], text, size, color, ha="center", va="center", bold=bold)
_zl3("31_", "遊戯室", size=3.2, color="white")          # 屋根（太陽光）の上なので白
_zl3("23_", "西館（2階建て）", size=3.2, color="white")
_zl3("12_", "本館（平屋）", (8, 6), size=3.6, color="white")
_zl(GD["north"], "だいさんかく", (6, -4), size=3.6)
_zl(GD["shizu"], "しずかのもり", (-4, 0), size=3.2)
_stl0 = gc.XS([tuple(p) for p in GJ["STREAM"]["line"]])[0]
_q0 = xf(R3(_stl0))[0]
# 部品の鍵（site.t.北のもり）を変えない：木田さんが .ai でこの名前を「かぜのもり」に書き換えて動かした（10-30）
T(ax, _q0[0] - 4, _q0[1] - 10, "北のもり", 3.2, "#3F5F2F", ha="right", va="center", bold=True)
# 園庭の名前（name.md、10-30 22:14）：木田さんが「北のもり」を「かぜのもり」に、「しずかのもり」を「みなみのさんかく」に書き換えて動かしたので、
# おくのもり・しずかのもり・てんぐのたにを別の部品で足す（鍵 site.t.おくのもり・site.t.しずかのもり~2・site.t.てんぐのたに）
_zl(GD["shizu"], "しずかのもり", (0, -6), size=3.2)
T(ax, _q0[0] - 4, _q0[1] - 4, "おくのもり", 3.2, "#3F5F2F", ha="right", va="center", bold=True)
_mc3 = rot(GD["mound"]).centroid
_eNE = LineString(R3(np.array([SITE_C["N"], SITE_C["E"]])))
_tg3 = np.array(_mc3.coords[0]) * 0.45 + np.array(_eNE.interpolate(_eNE.project(_mc3)).coords[0]) * 0.55
_qt = xf(np.atleast_2d(_tg3))[0]
T(ax, _qt[0], _qt[1], "てんぐのたに", 3.0, "#3F5F2F", ha="center", va="center", bold=True)
_car = [x for x in (_poly_of(o) for o in _rp_("74_")) if x is not None and x.geom_type.endswith("Polygon") and x.area > 8]   # 車室
if _car:
    _cu = unary_union(_car)
    q = xf(np.array(_cu.centroid.coords))[0]
    T(ax, q[0], q[1], "駐車場", 3.2, ha="center", va="center", bold=True)
_mk("t")
# 方位は「太陽の線」の丸の中の北の矢印に（ユーザー、10-26夜）。前の矢印とNは外した
_mk("t")
lab(ax, xf, SITE_C["NW"] + 0.12 * _LN * _eN + 3.5 * _oN, "北の道（車を止めて建物と庭の手入れ）", (0, 0), size=3.0)
# 北の用水路は尾を描かず、窓の北の端から入ってくる矢印と名前だけ（ユーザー、10-26夕）
_yh = xf(np.array([[33.5, min(58.8, VY1 - 3.0)]]))[0]; _yt = xf(np.array([[33.5, VY1 - 0.3]]))[0]
# 矢印も配置図に焼き込まず、文字と一つのグループの部品に（ユーザー、10-27：配置図は純粋に、書き込むものは別のオブジェクト）
SITEPARTS.append(dict(kind="line", id="site.l.用水路の矢印", pts=[tuple(_yt), tuple(_yh)], color="#1F6FB2", lw=1.2, arrow=2.4,
                      group="site.g.用水路", name="用水路の矢印"))
T(ax, _yt[0] - 2.5, _yt[1] - 3.5, "用水路（北から来て、暗渠で敷地の北の角へ）", 3.0, "#1F6FB2", ha="right", group="site.g.用水路")
_g66 = unary_union([g_ for g_ in (_sh(o) for o in _rp_("66_")) if g_ is not None])
if not _g66.is_empty:
    lab(ax, xf, R3inv(np.array(_g66.centroid.coords))[0], "公園からの入口（木戸）", (-25, 2), size=3.0, color="#4A3A2A", ha="right", bold=True)
_g73 = [g_ for g_ in (_sh(o) for o in _rp_("73_") if o["kind"] == "curve") if g_ is not None and g_.length > 9.5]
if _g73:
    lab(ax, xf, R3inv(np.array(_g73[0].interpolate(0.5, normalized=True).coords))[0], "ムベのアーチ", (-60, -6), size=3.0, color="#7A5530", ha="right", bold=True)
lab(ax, xf, R3inv(_RAIN_LAB)[0], "雨の川（樋なしで軒から落ちた雨を、雨落ちの溝から高野川へ）", (8, -10), size=3.0, color="#2F7FBF", ha="left")
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
T(ax, _wl[0], _wl[1], "夏の夜の風（高野川の谷を下りる風）", 3.2, "#3A7FB5", bold=True, ha="right")
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
    T(ax, _q[-1][0] - 2, _q[-1][1] + 3, f"比叡山へ　約{_DIST:.0f} km", 3.2, "#5E4380", bold=True, ha="right")
    T(ax, (_q[0][0] + _q[1][0]) / 2 + 2, (_q[0][1] + _q[1][1]) / 2 - 4, "ホールから築山の頂の向こうに比叡", 3.0, "#5E4380")
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
        T(ax, _pp[0], _pp[1], _txt, 2.8, _col, ha="left" if _v[0] >= 0 else "right", va="center")
    _vn = _c0 + _nv * (_SR * _k + 3.5)
    T(ax, _vn[0], _vn[1], "N", 3.0, INK, bold=True, ha="center", va="center")
    T(ax, _c0[0] - _SR * _k - 4, _c0[1] + _SR * _k + 8, "太陽の通り道（京都、北緯35°）", 3.2, INK, bold=True)
    T(ax, _c0[0] - _SR * _k - 4, _c0[1] - _SR * _k - 9, f"南中の高さ　夏至 {_alt_s:.0f}°・冬至 {_alt_w:.1f}°", 3.0, INK)
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
    _P = lambda xy: [fitz.Point(u_ * MM, (YT - v_) * MM) for u_, v_ in xf(np.asarray(xy, float))]
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
    # 高野川と河原の幅（ユーザー 10-28 23:54：「高野川はそんなに広くないんです」、10-29 0:13：「河原の幅が、橋の近くで狭くなっているでしょう？」、航空写真）。
    # 崖の上の縁（敷地の川の辺の延長）から川に直角に、馬橋の東の縁＝敷地の南西の端からの距離 d（m、北東へ＋）ごとに測った（写真の縮尺の棒で 6.95 px/m）。
    # 敷地の側の河原（草と石）は北東で広く（13 m）、公園の前で細い（7 m 台）。水の向こうの縁は崖の上から約33〜31 m、その先は向こう岸の土手 3 m・並木と歩道 4 m・道 10 m（4車線）・歩道と柵 2 m、その南は区画
    RIV = dict(dike=3.0, trees=4.0, road=10.0, walk=2.0)
    RIV_D = [-40.0, -20.0, 0.0, 10.0, 17.0, 20.0, 30.0, 40.0, 50.0, 63.0, 80.0, 100.0, 140.0]   # 馬橋の東の縁から（m）
    RIV_BED = [6.5, 6.5, 8.0, 7.9, 7.4, 7.3, 7.6, 8.4, 9.0, 10.5, 12.6, 13.1, 13.5]           # 河原の幅（崖の上から水際まで、m）
    RIV_FAR = [33.2, 33.2, 33.2, 33.2, 33.0, 32.9, 32.5, 32.1, 31.7, 31.4, 31.0, 30.8, 30.5]  # 水の向こうの縁（崖の上から、m）
    _cE, _cS = R3(SITE_C["E"])[0], R3(SITE_C["S"])[0]
    _yc = _cS[1] + (_xs - _cS[0]) * (_cE[1] - _cS[1]) / (_cE[0] - _cS[0])            # 崖の上の縁（回した座標、m）
    _dd = _xs - float(_cS[0])
    _sm = lambda v_: np.convolve(np.pad(v_, 10, mode="edge"), np.ones(21) / 21, mode="valid")   # なめらかに
    _bedw, _farw = _sm(np.interp(_dd, RIV_D, RIV_BED)), _sm(np.interp(_dd, RIV_D, RIV_FAR))
    _wv = _yc - _bedw + 0.35 * np.sin(_xs * 0.9) + 0.25 * np.sin(_xs * 2.3 + 1.0) + 0.15      # 水の北の縁（ゆらす）
    _yf = _yc - _farw - (0.3 * np.sin(_xs * 0.8 + 2.0) + 0.2 * np.sin(_xs * 2.1)) - 0.1      # 水の南の縁
    _yD = _yc - _farw - RIV["dike"]                                                  # 土手の上＝並木の帯の北の縁
    _yT = _yD - RIV["trees"]                                                         # 道の北の縁
    _yR = _yT - RIV["road"]                                                          # 道の南の縁
    _yK = _yR - RIV["walk"]                                                          # 歩道と柵の南の縁
    _lo = np.full_like(_xs, BY0 - 6.0)
    _band_ = lambda ya, yb: Polygon(list(zip(_xs, ya)) + list(zip(_xs[::-1], yb[::-1]))).buffer(0)
    _WATER = _band_(_wv, _yf)
    _RDR = unary_union([rot(g) for ln, g in CTX if ln.startswith("03_") and g is not None]).buffer(0)
    _NBED = _band_(np.maximum(_yb + 0.05, _wv), _wv)                                 # 3dm の河川敷の南の端から水際まで（河原を写真の幅に）
    _BEDALL = unary_union([_BED, _NBED]).buffer(0.05).buffer(-0.05)
    _DIKE, _TREEB, _ROAD2, _WALK2, _BLOCK = _band_(_yf, _yD), _band_(_yD, _yT), _band_(_yT, _yR), _band_(_yR, _yK), _band_(_yK, _lo)
    _SOUTHZ = _band_(_yc - 0.2, _lo)                                                 # 崖の上の縁より南（3dm の周辺の道は描かない）
    # 馬橋（人と車の二本、決定事項の「敷地の現況」）：写真では公園の西の縁の延長に、東に人の橋（約4 m）、西に車の橋（約9 m）。崖の上から向こうの道まで
    _xb = float(_cS[0]); _ycb = float(np.interp(_xb, _xs, _yc)); _yTb = float(np.interp(_xb, _xs, _yT))
    _BR_P = Polygon([(_xb - 4.0, _ycb), (_xb, _ycb), (_xb, _yTb), (_xb - 4.0, _yTb)])
    _BR_C = Polygon([(_xb - 13.4, _ycb), (_xb - 4.4, _ycb), (_xb - 4.4, _yTb), (_xb - 13.4, _yTb)])
    _BRIDGE = unary_union([_BR_P, _BR_C])
    _XST = Polygon([(_xb - 13.4, _yTb + 0.5), (_xb - 5.4, _yTb + 0.5), (_xb - 5.4, BY0 - 6), (_xb - 13.4, BY0 - 6)]).intersection(_band_(_yR + 0.01, _lo))   # 橋から南へ続く道（8 m）
    _ROADS2 = unary_union([_ROAD2, _XST])
    _BLDR = unary_union([rot(g) for ln, g in CTX if ln.startswith("04_") and g is not None]).buffer(0).intersection(_BLOCK).difference(_XST.buffer(0.5))   # 道の向こうの家（3dm の周辺の建物）
    _BLDR = unary_union([g_ for g_ in getattr(_BLDR, "geoms", [_BLDR]) if g_.geom_type == "Polygon" and g_.area > 4.0]) if not _BLDR.is_empty else _BLDR
    _TREES = [(x_, float(np.interp(x_, _xs, (_yD + _yT) / 2))) for x_ in np.arange(BX0 + 2.0, BX1, 6.5)
              if not _BRIDGE.buffer(1.5).contains(Point(x_, float(np.interp(x_, _xs, (_yD + _yT) / 2))))]
    print("高野川：崖の上 y≈", round(float(np.mean(_yc)), 1), "m、水", round(float(np.mean(_wv)), 1), "〜", round(float(np.mean(_yf)), 1), "、道", round(float(np.mean(_yT)), 1), "〜", round(float(np.mean(_yR)), 1),
          "、3dm の河川敷の南の端", round(float(np.mean(_yb)), 1), "、馬橋 x", round(_xb - 13.4, 1), "〜", round(_xb, 1))
    _STONES = []
    for x_ in np.arange(BX0, BX1, 0.42):
        for k_ in range(2):
            xx = x_ + _rng.uniform(-0.2, 0.2); yy = np.interp(xx, _xs, _wv) + _rng.uniform(0.1, 1.3) * (1 if k_ else 0.55)
            if not _BRIDGE.contains(Point(xx, yy)):
                _STONES.append((xx, yy, _rng.uniform(0.07, 0.17), _rng.uniform(0, 180)))
            xx = x_ + _rng.uniform(-0.2, 0.2); yy = np.interp(xx, _xs, _yf) - _rng.uniform(0.1, 1.0) * (1 if k_ else 0.55)   # 向こう岸の水際
            if not _BRIDGE.contains(Point(xx, yy)):
                _STONES.append((xx, yy, _rng.uniform(0.07, 0.15), _rng.uniform(0, 180)))
    import gzip
    _PLA = json.load(gzip.open(os.path.join(HERE, "plateau_area.json.gz"), "rt", encoding="utf-8"))
    _Rp = lambda xy: Polygon(R3(np.array(xy, float))).buffer(0)
    # 北の道の向こうの京都工芸繊維大学の構内（PLATEAU の土地利用 214）を淡い色に（地域のなかの敷地と同じ色、10-28）。道・敷地には塗らない
    _BIG = Polygon([(BX0 - 2, BY0 - 2), (BX1 + 2, BY0 - 2), (BX1 + 2, BY1 + 2), (BX0 - 2, BY1 + 2)])
    _UNIV = unary_union([g_ for g_ in (_Rp(u_["xy"]) for u_ in _PLA["luse"] if u_["cls"] == "214" and len(u_["xy"]) > 2) if g_.intersects(_BIG)])
    _UNIV = _UNIV.intersection(_BIG).difference(_RDR).difference(_SITEP.buffer(0.5)) if not _UNIV.is_empty else _UNIV
    _UNIV = unary_union([g_ for g_ in getattr(_UNIV, "geoms", [_UNIV]) if g_.geom_type == "Polygon" and g_.centroid.y > 40.0])   # 北の道の向こうだけ
    _TUFTS = []
    for x_ in np.arange(BX0 + 0.8, BX1, 2.6):
        for y_ in np.arange(float(np.min(_wv)) + 1.0, -2.0, 2.4):
            xx, yy = x_ + _rng.uniform(-0.9, 0.9), y_ + _rng.uniform(-0.6, 0.6)
            if not _BRIDGE.contains(Point(xx, yy)) and _BEDALL.buffer(-0.4).contains(Point(xx, yy)) and yy > np.interp(xx, _xs, _wv) + 1.6:
                _TUFTS.append((xx, yy))
        for y_ in np.arange(float(np.min(_yD)), float(np.max(_yf)), 1.2):              # 向こう岸の土手の草
            xx, yy = x_ + _rng.uniform(-0.9, 0.9), y_ + _rng.uniform(-0.3, 0.3)
            if not _BRIDGE.buffer(0.3).contains(Point(xx, yy)) and _DIKE.buffer(-0.5).contains(Point(xx, yy)):
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
        _nd = fitz.open(); _pg = _nd.new_page(width=W * MM, height=HS * MM)
        # 向こうの紙の外（南の高野川の水面など）は、こちらの描いた線と色で補う（ユーザー 10-26夕：南へ延ばして川を見せる）
        _bw = (bsx, YT - bsy - bsh, bsx + bsw, YT - bsy)                         # 縦に長い紙の左上から
        _iP = (_ia[0], _ia[1] + SDY_, _ia[2], _ia[3] + SDY_)
        for _r in ((_bw[0], _bw[1], _bw[2], _iP[1]),
                   (_bw[0], max(_bw[1], _iP[1]), _iP[0], min(_bw[3], _iP[3])), (_iP[2], max(_bw[1], _iP[1]), _bw[2], min(_bw[3], _iP[3]))):
            _r = (max(_r[0], 0), max(_r[1], 0), min(_r[2], W), min(_r[3], HS))
            if _r[2] - _r[0] > 0.1 and _r[3] - _r[1] > 0.1:
                _cr = fitz.Rect(_r[0] * MM, _r[1] * MM, _r[2] * MM, _r[3] * MM)
                _pg.show_pdf_page(_cr, fitz.open(_SITE_PDF[gr]), 0, clip=_cr)
        # 南（向こうの図の外）：水と橋だけ（こちらの描いた川の線は描かない）
        if gr == "c":
            _fillg(_pg, _WATER, _hx("#CFE3EF"))
            _fillg(_pg, _UNIV, _hx("#EEEBE3"))                                           # 大学の構内（10-28）
            _fillg(_pg, _BRIDGE, _hx("#F7F7F7"))
            _fillg(_pg, _PARK_R, _hx("#D9E8C6"))                                        # 公園を緑に（ユーザー、10-26夜）
            if _g73a: _fillg(_pg, _ARCH, _hx("#C9DFB0"))                                  # ムベのアーチの範囲を緑に
        _src = fitz.open(_SPB + suf)
        _cl = fitz.Rect((_ia[0] - _off[0] + 0.35) * MM, (_ia[1] - _off[1] + 0.35) * MM, (_ia[2] - _off[0] - 0.35) * MM, (_ia[3] - _off[1] - 0.35) * MM)
        _pg.show_pdf_page(fitz.Rect((_iP[0] + 0.35) * MM, (_iP[1] + 0.35) * MM, (_iP[2] - 0.35) * MM, (_iP[3] - 0.35) * MM), _src, 0, clip=_cl)   # 枠の線は入れない
        if gr == "c":
            _fillg(_pg, _MINAMI, _hx("#DDE9CC"))                                           # みなみのさんかくを緑に（芝かどうかは別。向こうの図の白い地の上に）
            _fillg(_pg, _SANDP, _hx("#EFE2B8"))                                            # 砂場・粒の遊び場
            _fillg(_pg, _WATERP, _hx("#BFDDEE"))                                           # 水遊び（水のテーブル・噴水・あめのわ・霧のわ）
            _fillg(_pg, _RAINP, _hx("#DCE4E6"))                                            # 雨庭（玉石の浜）
            _fillg(_pg, _HUT, _hx("#5E636C"))                                              # 園庭の小屋の屋根（片流れ、更新係の図に無い）
            # 川の向こう（10-28 夜、航空写真の幅）：区画（グラウンド・駐車場・家）を淡く、土手は草、並木の帯と歩道は淡い舗装、道
            _fillg(_pg, _BLOCK, _hx("#EEF1E7"))
            _fillg(_pg, _BLDR, _hx("#E2E2E0"))
            _fillg(_pg, _DIKE, _hx("#DDE8D0"))
            _fillg(_pg, unary_union([_TREEB, _WALK2]), _hx("#EDEBE5"))
            _fillg(_pg, _ROADS2, _hx("#E2E2E0"))
            # 周りの道を少し濃く（ユーザー 10-27夜：西の道とその先の白い敷地の差をつける）。敷地の中は塗らない。崖より南は上の道（3dm の周辺の道は使わない）
            _fillg(_pg, _RDR.difference(_SITEP.buffer(0.05)).difference(_SOUTHZ), _hx("#E2E2E0"))
            # 西の道沿いの歩道（幅 1 m）を洗い出しのベージュに、スピードバンプは今までの灰のまま（ユーザー 10-27夜）
            _swS = _SITEP.intersection(LineString([_A_ - _tW * 10, _B_ + _tW * 10]).buffer(1.0, cap_style=2)).intersection(_slab).difference(_PARK_R.buffer(0.02))
            # 歩道は搬入口の前まで（approachA.json の SIDEWALK s 0〜30）。更新係の図の歩道（白）の北の端が駐車の帯（s 29まで）の先に白い三角で残っていた（10-30 22:14）
            _swS = _swS.union(Polygon(R3(np.array(json.load(open(os.path.join(ROOT, "data", "siteplan_approach.json"), encoding="utf-8"))["sidewalk"]["pts"]))).buffer(0).intersection(_SITEP)).difference(_PARK_R.buffer(0.02))
            _bumps = [g_ for g_ in (_shp_(o_) for o_ in _rp_("74_") if o_["kind"] == "solid") if g_ is not None and g_.area > 0.2 and g_.intersection(_swS).area > 0.5 * g_.area]
            _fillg(_pg, _swS.difference(unary_union(_bumps)) if _bumps else _swS, _hx("#EDDDBA"))
            _fillg(_pg, _BEDALL.difference(_BRIDGE).difference(_WATER), _hx("#DDE8D0"))   # 河原（3dm の河川敷＋写真の幅まで）
            _fillg(_pg, _WATER.difference(_BRIDGE), _hx("#CFE3EF"))
            for xx, yy, rr, an in _STONES:
                _fillg(_pg, affinity.rotate(affinity.scale(Point(xx, yy).buffer(rr, 8), 1.0, 0.7), an), _hx("#E4DED0"))
            _fillg(_pg, _BR_C, _hx("#E2E2E0")); _fillg(_pg, _BR_P, _hx("#EDEBE5"))          # 馬橋（車・人）
            for xx, yy in _TREES:                                                          # 並木
                _fillg(_pg, Point(xx, yy).buffer(1.4, 12), _hx("#C4D7AC"))
        else:
            if not _BED.is_empty:                 # 河川敷の片の継ぎ目の線を、同じ緑で覆って消す（上の縁の線は残す）
                _fillg(_pg, _BEDALL.buffer(-0.06).difference(_BRIDGE).difference(_WATER), _hx("#DDE8D0"))
                _fillg(_pg, _WATER.difference(_BRIDGE), _hx("#CFE3EF"))
            _fillg(_pg, _BR_C, _hx("#E2E2E0"), _hx("#999999"), 0.25); _fillg(_pg, _BR_P, _hx("#EDEBE5"), _hx("#999999"), 0.25)   # 馬橋（下の古い線を隠す）
            for xx, yy, rr, an in _STONES:
                _fillg(_pg, affinity.rotate(affinity.scale(Point(xx, yy).buffer(rr, 8), 1.0, 0.7), an), None, _hx("#9C9587"), 0.35)
            _fillg(_pg, _SANDP, None, _hx("#A89A70"), 0.3)
            _fillg(_pg, _WATERP, None, _hx("#6FA3C4"), 0.3)
            _fillg(_pg, _HUT, None, _hx("#222222"), 0.5)
            _fillg(_pg, _BLDR, None, _hx("#A8A8A8"), 0.15)                                 # 道の向こうの家（淡く）
            _hl = lambda ys_, col, w_, dash=None: _pg.draw_polyline(_P([(x_, y_) for x_, y_ in zip(_xs, ys_)]), color=_hx(col), width=w_, dashes=dash)
            _hl(_yT, "#999999", 0.2); _hl(_yR, "#999999", 0.2)                                   # 道の縁
            _hl((_yT + _yR) / 2, "#CFCFCF", 0.3)                                                  # 車線の線（淡く）：中央は実線、両側は破線
            _hl(_yT - RIV["road"] / 4, "#D6D6D6", 0.25, "[14 20] 0"); _hl(_yR + RIV["road"] / 4, "#D6D6D6", 0.25, "[14 20] 0")
            _hl(_yK, "#8C8C8C", 0.2, "[2 2] 0")                                                 # 柵
            _fillg(_pg, _XST, _hx("#E2E2E0"), _hx("#999999"), 0.2)
            _fillg(_pg, _BR_C, None, _hx("#999999"), 0.25); _fillg(_pg, _BR_P, None, _hx("#999999"), 0.25)
            for xx, yy in _TREES:
                _fillg(_pg, Point(xx, yy).buffer(1.4, 12), None, _hx("#7E9A68"), 0.3)
            for xx, yy in _TUFTS:
                for da, ln_ in ((-28, 0.26), (-10, 0.34), (8, 0.36), (26, 0.27)):
                    t_ = np.radians(90 + da)
                    _pg.draw_line(*_P([(xx, yy), (xx + np.cos(t_) * ln_, yy + np.sin(t_) * ln_)]), color=_hx("#7E9C6A"), width=0.35)
        if not _NESTUB.is_empty:                 # 向こうの図の北東の辺から出る道を白で消す（更新係に直してもらうまで、ユーザー 10-26夜）
            _wp = _NESTUB.buffer(0.12 if gr == "l" else 0.03, join_style=2).difference(Polygon(to_s(np.array(list(SITE_C.values())))).buffer(0.25, join_style=2))
            for g_ in getattr(_wp, "geoms", [_wp]):
                if g_.geom_type != "Polygon" or g_.area < 0.01: continue
                _q = xf(np.array(rot(g_).exterior.coords))
                _sh = _pg.new_shape(); _sh.draw_polyline([fitz.Point(u_ * MM, (YT - v_) * MM) for u_, v_ in _q])
                _sh.finish(color=None, fill=(1, 1, 1), closePath=True); _sh.commit()
        _fn = os.path.join(OUT, f"_site_{gr}_upd.pdf"); _nd.save(_fn); _nd.close()
        _SITE_PDF[gr] = _fn
    print("配置図：線と色は更新係の配置図から（ずれ", np.round(_off, 1), "mm）")
_SCLIP = (SCX0, M + SDY_, SCX1, H - M + SDY_)                                          # 元のPDFのmm（左上から）。上下は内枠いっぱい（ユーザー 10-28 18:01）
for gr in ("c", "l", "t", "o"):                                               # 1枚目：色 → 線 → 文字 → 風と視線の順に重ねる（太陽は外した、ユーザー 10-26）
    embed(1, _SITE_PDF[gr], _SCLIP, SCX0, M, 1.0)
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
    TOPT[1].append((_sux + _x - _tw / 2, _suy + _y - _th * 0.35, _s, _th, False, "Apple-Chancery", "#F2F3F4", dict(plan=True)))
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
    _th = {"高野川": 3.0, "京都工芸繊維大学": 2.8, "敷地": 3.0, "N": 3.0}.get(_s, 2.6)   # 最低 2.6 mm（ユーザー 10-29 15:16）
    _tw = _FR.text_length(_s, _th / 0.72)
    _dx, _dy = {"敷地": (4, -1), "0": (0, 1.2), "200 m": (0, 1.2)}.get(_s, (0, 0))
    _cx = _amx + _x + _dx - (0 if _s == "敷地" else _tw / 2)
    TOPT[1].append((_cx, _amy + _y + _dy - _th * 0.35, _s, _th, _s in ("敷地", "N", "高野川"), None, "#2E333A" if _s == "敷地" else ("#2F6FA0" if _s == "高野川" else "#333333")))
    if _s == "京都工芸繊維大学":                 # 災害の箱の印（□4）を大学の名前の左に（ユーザー 10-30：配置図に□4が無かった）。名前と一緒に動く
        _rq = MARK_R_PLAN * 0.9
        MARKS.append(dict(id="mark.com.saigai.1", cat="com", num=None, cx=_cx - 1.5 - _rq, cy=_amy + _y + _dy - _th * 0.35 + 0.53 * _th,
                          r=MARK_R_PLAN, ring=True, group="mark.com.saigai.1", group_name="印　災害時の持ちつ持たれつ（大学）", key="com.saigai",
                          follow="top.京都工芸繊維大学"))
TOPT[1].append((_amx, _amy + _AH + TITLE_GAP, "地域のなかの敷地　1/10000", 4.2, True))
TOPT[1].append((_amx, _amy - 4.5, "出典：国土交通省 Project PLATEAU（京都市 2025）の建物・道路・土地利用から作図", 2.6, False))
# 縮尺のスケールは部品に（ユーザー、10-27：「その他の絵」ごと隠したので、一つのグループで出す）
def scalebar_parts(x, y, scale, meters, grp):
    k = 1000 / scale; hb = 1.2; n_ = meters // 5
    for i in range(n_):
        SITEPARTS.append(dict(kind="line", id=f"{grp}.bar{i}", pts=[(x + i * 5 * k, y + hb / 2), (x + (i + 1) * 5 * k, y + hb / 2)],
                              color="#222222" if i % 2 == 0 else "#FFFFFF", lw=hb * 72 / 25.4, group=f"site.g.{grp}", name=f"縮尺 {i}"))
    SITEPARTS.append(dict(kind="line", id=f"{grp}.frame", pts=[(x, y), (x + meters * k, y), (x + meters * k, y + hb), (x, y + hb), (x, y)],
                          color="#222222", lw=0.3, group=f"site.g.{grp}", name="縮尺の枠"))
    SITEPARTS.append(dict(kind="text", x=x, y=y - 4, s="0", size=2.6, color="#222222", bold=False, ha="center", va="baseline", group=f"site.g.{grp}"))
    SITEPARTS.append(dict(kind="text", x=x + meters * k, y=y - 4, s=f"{meters} m", size=2.6, color="#222222", bold=False, ha="center", va="baseline", group=f"site.g.{grp}"))


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
# 番号（ユーザー、10-28：番号は一か所で決める）。決め方の順：.ai で書き換えた箱の印の数字 → 配置図の印の数字 → 番号の表
# present/ai/numbers.json（手で直してよい。mock.py が今の番号を書き戻す）→ 前の見出しの「自然4　」の数字 → 並びの順
_UP = _lu.get("parts", {})
_NUMF = os.path.join(HERE, "ai", "numbers.json")
try:
    _numtab = json.load(open(_NUMF, encoding="utf-8")).get("numbers", {})
except Exception:
    _numtab = {}
_int = lambda s_: (int(re.search(r"\d+", str(s_)).group()) if s_ is not None and re.search(r"\d+", str(s_)) else None)
_oldhead = lambda k_: re.match(r"^(自然|地域)(\d+)[　 ]*(.*)$", (_UP.get(f"p1.ibox.{k_}.head") or {}).get("s", "") or "")


def _num_of(k_, i_, npts):
    for v_ in [_int((_UP.get(f"p1.ibox.{k_}.mark.num") or {}).get("s"))] + [_int((_UP.get(f"p1.mark.{k_}.{j_ + 1}.num") or {}).get("s")) for j_ in range(npts)] + \
              [_numtab.get(k_), _int(_oldhead(k_).group(2)) if _oldhead(k_) else None, i_ + 1]:
        if v_ is not None:
            return int(v_)


def _title_of(k_, h1):
    s_ = (_UP.get(f"p1.ibox.{k_}.title") or {}).get("s")
    return s_ if s_ else (_oldhead(k_).group(3) if _oldhead(k_) else h1)


def _body_of(k_, ls_):
    s_ = (_UP.get(f"p1.ibox.{k_}.text") or {}).get("s") or (_UP.get(f"p1.ibox.{k_}.body") or {}).get("s")
    return s_.split("\n") if s_ else ls_


ITEMS = [(_title_of("nat." + k1, h1), _body_of("nat." + k1, ls_), C_NAT, "#F6FAFD", pts, fx_, "nat." + k1) for i_, (k1, h1, ls_, pts, fx_) in enumerate(NAT)]
ITEMS += [(_title_of("com." + k1, h1), _body_of("com." + k1, ls_), C_COM, "#FBF7F2", pts, fx_, "com." + k1) for i_, (k1, h1, ls_, pts, fx_) in enumerate(COM)]
NUMS = {it[6]: _num_of(it[6], i_ if it[6].startswith("nat.") else i_ - len(NAT), len(it[4])) for i_, it in enumerate(ITEMS)}
for _mk_ in MARKS:                                         # 番号の前に置いた印（大学の□）に番号
    if _mk_["num"] is None:
        _mk_["num"] = NUMS[_mk_["key"]]
json.dump(dict(note="1枚目の説明の箱と配置図の印の番号（鍵 → 番号）。手で直してよい（.ai で書き換えて書き出した数字があればそちらが先）。mock.py が今の番号を書き戻す",
               numbers=NUMS), open(_NUMF, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
AI_SHIFT = {}                                             # 前の箱（ibox.{key}）の .ai の位置へ、新しい部品をまとめて動かす（一度だけの移し替え）


def _hbox(x_, y_, w_, h_, head, ls_, col, key_):
    ibox_h(ax, x_, y_, w_, h_, head, ls_, col, key_.split(".")[0], NUMS[key_], key_, size=BOX_FS)
    ub_ = _UP.get(f"p1.ibox.{key_}")
    if ub_ and "x" in ub_:
        AI_SHIFT[f"ibox.{key_}."] = (ub_["x"] - x_, ub_["y"] - (H - y_ - h_))


# 配置図の上の印は、箱の印と同じ大きさ（ユーザー 10-30：.ai で箱の印を小さくした大きさに合わせる）。○の径＝箱の○の幅、□は○の0.9
_bw = sorted(v_["w"] for k_, v_ in _UP.items() if re.match(r"^p1\.ibox\.nat\.[^.]+\.mark\.shape$", k_) and v_.get("w"))
if _bw:
    MARK_R_PLAN = _bw[len(_bw) // 2] / 2


def _pmarks(key_, pts, head):
    for k_, q_ in enumerate(pts):                         # 配置図の上の点に同じ印（引き出し線なし）
        MARKS.append(dict(id=f"mark.{key_}.{k_ + 1}", cat=key_.split(".")[0], num=NUMS[key_], cx=q_[0], cy=q_[1], r=MARK_R_PLAN, ring=True,
                          group=f"mark.{key_}.{k_ + 1}", group_name=f"印　{head}" + (f"（{k_ + 1}）" if len(pts) > 1 else ""), key=key_, follow="sozai.01a"))
_mid = sx + sw / 2
BOXW = 175.0                                              # 説明の箱は少し狭く、配置図の側に寄せる（ユーザー、10-26：引き出し線が短くなる）
LCW = RCW = BOXW
LCX = sx - 8 - LCW
RCX = sx + sw + 8
_hof = lambda it, colw: BOX_BODY + 2 + sum(len(jwrap(t_, (colw - HIND - 3) / (BOX_FS / 0.72))) for t_ in it[1]) * (BOX_FS / 0.72 * 1.5) + (len(it[1]) - 1) * (BOX_FS / 0.72)
_fixbot = {}                                              # 置き場所を決めた箱の下端（紙のmm、下から）
for (head, ls_, col, fill, pts, fx_, key_) in ITEMS:
    if fx_ is None:
        continue
    h_ = _hof((head, ls_), RCW)
    x_, t_ = fx_[0], H - fx_[1]                          # 上端
    _hbox(x_, t_ - h_, RCW, h_, head, ls_, col, key_)
    _fixbot[(x_ >= RCX - 5)] = min(_fixbot.get(x_ >= RCX - 5, 1e9), t_ - h_)
    _pmarks(key_, pts, head)
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
        _hbox(colx, t_ - h_, colw, h_, head, ls_, col, key_)
        _pmarks(key_, pts, head)

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
# 表題と出典は素材02の絵に入れず、Illustratorの別の文字の部品に（ユーザー、10-28：図をクリップしても置き直せるように）。素材02と一緒に動く
TOPT[1].append((_nbx + _nw, _ny1 + TITLE_GAP, "松ヶ崎の用水ネットワーク", 4.2, True, None, C_NAT,   # 題は絵の上（10-29）。右寄せ：左上に地域のなかの敷地が重なる（ユーザーの割付）
                dict(id="water.title", name="用水ネットワークの表題", align="right", follow="sozai.02")))   # 右寄せ：左上は地域のなかの敷地（素材14）を重ねる（ユーザー、10-27）
T(ax, _nbx + 6, _ny1 - 13, "N↑", 3.2, bold=True)
_ym = lambda P: np.c_[_fx0 + (_yr(P)[:, 0] - _lo[0]) * _k, _fy0 + (_yr(P)[:, 1] - _lo[1]) * _k]
for _rn, _rl in YS.get("roads", {}).items():             # 道は北山通だけ（ユーザー）
    q = _ym(_rl); ax.plot(q[:, 0], q[:, 1], color="#D8A84E", lw=1.4, zorder=2.5, solid_capstyle="butt")
    T(ax, q[-1, 0] - 1, q[-1, 1] - 4.0, _rn, 2.6, "#A87A22", ha="right", zorder=6)
for pl in YS["water_fills"]:
    q = _ym(pl); ax.fill(q[:, 0], q[:, 1], fc="#BFDDF2", ec="none", zorder=3)
for ln_ in YS["water_lines"]:
    q = _ym(ln_); ax.plot(q[:, 0], q[:, 1], color=C_NAT, lw=0.6, zorder=4, solid_capstyle="round")
for (px_, py_), t_, dx_, dy_, ha_ in [((272, 76), "井出ヶ鼻井堰", 3, -1, "left"), ((127, 55), "宝が池", 2, 2, "left"),
                                       ((200, 151), "東松ヶ崎の井戸", -2, 1.5, "right"), ((246, 166), "樋ノ上川", 1, -3.5, "left"),
                                       ((170, 182), "前川", 1, 1, "left"), ((163, 216), "橋上川", 1, 1, "left"),
                                       ((133, 231), "正田川", 1, 1, "left"), ((113, 248), "久土川", 1, 1, "left"), ((118, 318), "高野川", 2, -4, "left"), ((225, 30), "岩倉川", 0, 2, "left"), ((318, 177), "音羽川", 0, 2, "right")]:
    q = _ym([(px_, py_)])[0]
    T(ax, q[0] + dx_, q[1] + dy_, t_, 2.6, C_NAT if ("川" in t_ or "堰" in t_ or "池" in t_) and "井戸" not in t_ else INK, ha=ha_, zorder=6)
_wq = _ym([(272, 76)])[0]; ax.plot([_wq[0]], [_wq[1]], marker="v", ms=4, color=C_NAT, zorder=7)
_eq = _ym([(200, 151)])[0]; ax.plot([_eq[0]], [_eq[1]], "o", ms=3, mfc="white", mec=INK, zorder=7)
_sq = _ym([(247, 148)])[0] + np.array([4.5, -1.2])   # 図の「樋ノ上川」の「樋」の字のあたり（ユーザー、10-24夜）
# 敷地の印は描かない（ユーザー、10-25朝：不要）
TOPT[1].append((_fx0, _ny0 + 5.5, "大正から昭和初期の図（https://kyoto-machisen.jp/chiiki_hp/matsugasaki_hp/history/history.htm）", 2.6, False, None, "#666666",
                dict(id="water.source", name="用水ネットワークの出典（1行目）", follow="sozai.02")))
TOPT[1].append((_fx0, _ny0 + 2.0, "図：http://ksdobokuisan.stars.ne.jp/80_takaragaike/takaragaike.html の図をなぞって描き直し", 2.6, False, None, "#666666",
                dict(id="water.source2", name="用水ネットワークの出典（2行目）", follow="sozai.02")))
sozai("02", "松ヶ崎の用水の網（北が上）", 1, _nbx, _ny0, _box_patch.get_width(), _ny1 - _ny0)
FIGS[1] = fig

# 図のPDF（3dmから自動の図）
DRW = os.path.join(ROOT, "drawings")   # 図のPDFは sodachiya/drawings/（10-24）
PLAN = os.path.join(DRW, "sodachiya_plan_1-100.pdf")
ELE1 = os.path.join(DRW, "sodachiya_elevations_1-100.pdf")
ELE2 = os.path.join(DRW, "sodachiya_elevations2_1-100.pdf")

# 面積表とinspired by（3枚目・4枚目で使う）
AJ = json.load(open(os.path.join(ROOT, "model", "drawings", "sodachiya_areas.json"), encoding="utf-8"))


def area_table(ax, tx, ty, tw, size=2.2, cols=1, gap=10):
    """面積表。cols=2 で行を二つの欄に分ける（tw は一つの欄の幅）"""
    title(ax, tx, ty, "面積表", "m²（壁芯、3dmから自動）")
    _hc = "#666666"                                # 列の見出し（注の紫は本番で消えるので灰に、10-29）
    rows_ = [r_ for r_ in AJ["rooms"] if not (r_["planned"] is None and not r_["judge"])]
    per = -(-(len(rows_) + 1) // cols)
    yb = ty
    for c_ in range(cols):
        x_ = tx + c_ * (tw + gap)
        T(ax, x_, ty - 8, "室", size, _hc); T(ax, x_ + tw * 0.55, ty - 8, "要求", size, _hc); T(ax, x_ + tw, ty - 8, "計画", size, _hc, ha="right")
        ax.plot([x_, x_ + tw], [ty - 9.6, ty - 9.6], color="#BBBBBB", lw=0.25)
        yy = ty - 14
        for r_ in rows_[c_ * per:(c_ + 1) * per]:
            nm = r_["room"].replace(" ", "")
            T(ax, x_, yy, nm[:11], size)
            T(ax, x_ + tw * 0.55, yy, r_["required"].replace(" ", "")[:8], size)
            T(ax, x_ + tw, yy, f"{r_['planned']:.1f}" if r_["planned"] else r_["judge"], size, ha="right")
            yy -= size + 2.2
        if c_ == cols - 1:
            ax.plot([x_, x_ + tw], [yy + size + 0.6, yy + size + 0.6], color="#BBBBBB", lw=0.25)
            T(ax, x_, yy, "延床（2,000以内）", size, bold=True)
            T(ax, x_ + tw, yy, f"{AJ['floor']['total']:,.1f}", size, ha="right", bold=True)
        yb = min(yb, yy)
    return yb


def _area_rows_h(size, cols=1):
    n_ = sum(1 for r_ in AJ["rooms"] if not (r_["planned"] is None and not r_["judge"]))
    return 14 + -(-(n_ + 1) // cols) * (size + 2.2)


INSP = [("Asilo Nido Iride", "Mario Cucinella Architects・Guastalla・2015", "梁の列が並ぶ長細い本館と、外に付く付属の建物"),
        ("Tamedia", "坂茂・Zürich・2013", "梁の端の楕円の頭と、それを貫く楕円の桁"),
        ("レイモンド斑鳩こども園", "キノアーキテクツ・斑鳩・2026", "室内に木を立てる（ホールの北山杉）・内と外の回廊・回廊と遊戯室に居場所"),   # 項 20261029-1334-kanshu
        ("KAIT工房", "石上純也・厚木・2008", "柱の配列：見る向きで景色が変わる並び"),
        ("認定こども園らみどり", "はりゅうウッドスタジオ・須賀川・2026", "内と外の二重の縁側、遊具を置かない地形の園庭"),
        ("仙田満の園舎", "環境デザイン研究所", "摺鉢のネット、キャットウォーク、ニッチ"),
        ("Waldorf School of the Peninsula", "California", "遊戯室の切り株"),
        ("スターバックス京都二寧坂ヤサカ茶屋店","町家の改修・京都・2017", "放射冷房")]   # ユーザー 10-29




INSP_PITCH = 13.5                                # 一件の高さ（mm）。字は名前2.6・出どころ2.2・理由2.4（右下の縦長の囲み、10-29：2.2 mm 以上）


def inspired(ax, tx, ty, colw, rows=4, head=True):
    if head:
        T(ax, tx, ty, "inspired by", 3.0, bold=True)
    for i, (n, src, what) in enumerate(INSP):
        c_, r_ = divmod(i, rows)
        x_, y2 = tx + c_ * colw, ty - (6 if head else 0) - r_ * INSP_PITCH
        T(ax, x_, y2, n, 2.6, bold=True)
        T(ax, x_, y2 - 3.9, src, 2.2, "#666666")
        T(ax, x_ + 1.5, y2 - 7.8, "→" + what, 2.4)


# ================================================================ 5　立面・景観（10-30：6枚の5枚目、前の2枚目のまま。10-28：もとの2枚目、いちど4枚目にしてから13:17に2枚目へ。ユーザー、10-24夜：立面図2面 → 鳥瞰・約束・素材と色。10-27夜：沿川の景観立面（昼・夜）を1枚目から下の段へ）
fig, ax = page()
frame(ax, 5, "立面・景観", "建物に正対する二つの立面（園庭の側・道路の側）で、伸びやかな梁と縁側、西館の立ち上がり。下の段に外から見た姿：目の高さの透視図（公園の角から西の道、お向かいさんとの関係）と、川の向こう岸から見た沿川の景観（昼・夜、透視図）",
      "園庭の側・道路の側の立面図 → 透視図（A4）・沿川の景観（昼・夜）→ 景観の法規・素材と色")
CLIP_E1 = (25, 35.6, 788.5, 143.0)         # 自動の立面図1：園庭の側（10-28：右の高さの記号・左の高さの寸法・下の全長まで。縮尺の棒は外す）
CLIP_E2 = (25, 200.1, 788.5, 308.6)        # 自動の立面図1：道路の側（10-28：上は表題の切れ端を外し、右の高さの記号・下の全長まで）
CLIP_SA = (54, 46.6, 821.5, 171)           # 自動の断面図：縦断A（10-28：左は敷地の境から、上は通り芯の頭から。右は高さの記号まで（更新係が図を3 m左へ寄せた）。「← 南」は表題に書いてあるので外す）

ex = M + 6
y_ = H - M - HDR - 3
BH2 = 210                                    # 4行目（鳥瞰＝透視図 A4・約束・素材と色）の高さ。鳥瞰は A4（297×210）で課題の透視図を兼ねる（ユーザー、10-27夜）
G2 = (y_ - (M + 8) - BH2 - 2 * 7 - (CLIP_E1[3] - CLIP_E1[1]) - (CLIP_E2[3] - CLIP_E2[1])) / 3
# 二つの立面を対比で見せる（ユーザー、10-27夜：園庭にひらく／まちに溶け込みつつやさしく守る）。箱は立面の右上の空に
CONTRAST = {
    "garden": ("園庭にひらく", ["縁側と深い軒が57 m続き、3 mごとの柱とガラス戸の半分が開く。屋根の光の筋が架構を照らし、こどもは縁側から庭へ下りる。"]),
    "road": ("まちに溶け込み、やさしく守る", ["杉の大和張りの静かな板の壁。西館は向かいの住宅に向けて1階の高さまで下げ、窓は小さく面ごとのリズムで。道からは中が見えすぎず、園を包む。"]),
}
y_ -= G2 / 2
title(ax, ex, y_ - 7 + TITLE_GAP, "園庭の側の立面図", "1/100　円弧の中心の方向から弧の真ん中に正対")
T(ax, ex + 300, y_ - 7 + TITLE_GAP, CONTRAST["garden"][0], 4.2, "#4E8A3A", bold=True)
T(ax, ex + 340, y_ - 7 + TITLE_GAP, CONTRAST["garden"][1][0], 2.8)
y_ -= 7
_, h_ = embed(5, ELE1, CLIP_E1, ex, y_ - (CLIP_E1[3] - CLIP_E1[1]), 1.0, dwg=("E1", "立面図　園庭の側"))
y_ -= h_ + G2
title(ax, ex, y_ - 7 + TITLE_GAP, "道路の側の立面図", "1/100　西の道路から")
T(ax, ex + 300, y_ - 7 + TITLE_GAP, CONTRAST["road"][0], 4.2, "#8A5A2B", bold=True)
T(ax, ex + 372, y_ - 7 + TITLE_GAP, CONTRAST["road"][1][0], 2.8)
y_ -= 7
_, h_ = embed(5, ELE1, CLIP_E2, ex, y_ - (CLIP_E2[3] - CLIP_E2[1]), 1.0, dwg=("E2", "立面図　道路の側"))
y_ -= h_ + G2
bh = BH2
_pw = 297
def _img_box(path, x, y, w, h, fit="cover", align="center"):
    """絵を枠に。cover＝枠いっぱい（はみ出す分を切る）、contain＝枠に収める（縦横の比を保つ）。返り値は絵の範囲 (x, y, w, h)"""
    ci_ = plt.imread(path)
    ih_, iw_ = ci_.shape[:2]
    s_ = (max if fit == "cover" else min)(w / iw_, h / ih_)
    dw_, dh_ = iw_ * s_, ih_ * s_
    x0_ = x + (w - dw_) / 2 if (fit == "cover" or align == "center") else x
    y0_ = y + (h - dh_) / 2 if fit == "cover" else y + h - dh_         # contain は上にそろえる
    rp_ = clip_rect(ax, x, y, w, h)
    xl_, yl_ = ax.get_xlim(), ax.get_ylim()
    im_ = ax.imshow(ci_, extent=(x0_, x0_ + dw_, y0_, y0_ + dh_), origin="upper", interpolation="lanczos", zorder=2, aspect="auto")
    im_.set_clip_path(rp_)
    ax.set_xlim(xl_); ax.set_ylim(yl_)
    return (max(x, x0_), max(y, y0_), min(w, dw_), min(h, dh_))


# 透視図（A4）：目の高さの透視図（ユーザー 10-29：公園の角から西の道を北へ、お向かいさんとの関係）。絵は上から順に探す：
#   写真 photo/me.jpg（.png）→ Rhino のレンダリング rhino/out/me.png（rhino/me_render.py）→ 仮の図 out/me_kari.png（tools/me_kari.py）。鳥瞰（choukan）は2枚目から外した
_ME_PHOTO = [os.path.join(HERE, "photo", "me" + e_) for e_ in (".jpg", ".jpeg", ".png")]
_ME_RH = os.path.join(HERE, "rhino", "out", "me.png")
_ME_KARI = os.path.join(HERE, "out", "me_kari.png")
_me = next((p_ for p_ in _ME_PHOTO if os.path.exists(p_)), None) or (_ME_RH if os.path.exists(_ME_RH) else (_ME_KARI if os.path.exists(_ME_KARI) else None))
_me_kind = "写真" if _me and _me in _ME_PHOTO else ("Rhino のレンダリング" if _me == _ME_RH else "仮の図")
title(ax, ex, M + 8 + bh + TITLE_GAP, "透視図（A4）　公園の角から西の道を見る", "目の高さ1.5 m、左に向かいの住宅、右に西館の低い軒")
if _me:
    _img_box(_me, ex, M + 8, _pw, bh, fit="cover")
    sozai("16", "透視図（A4）", 5, ex, M + 8, _pw, bh, _me_kind + "（" + os.path.relpath(_me, HERE) + "）")
    dimnote(ax, ex + 2, M + 8 + 2, "透視図：" + _me_kind + "（" + os.path.relpath(_me, HERE) + "）")
    print("透視図（A4）：", _me_kind, os.path.relpath(_me, HERE))
else:
    box(ax, ex, M + 8, _pw, bh, "透視図（A4）　公園の角から西の道を見る", "rhino/me_render.py のレンダリングを待つ")
# 透視図の右に、沿川の景観 昼（上）・夜（下）（ユーザー 10-29：立面である必要はなく景観なので透視図に）。
# Rhino の絵（rhino/keikan_render.py）は keikan_view.json に projection: "perspective" があるときだけ使う（前の平行投影の絵は使わない）。無ければ仮の図 out/keikan_kari_*.png
_lx = ex + _pw + 8
_lw1 = W - M - 6 - 126 - 8 - _lx              # 右の景観の法規の箱（126 mm、前と同じ）の左まで
_lh1 = (bh - 10) / 2                          # 二枚と、夜の題（昼の題は透視図の題と同じ高さ、絵の上）
_ly_d = M + 8 + bh - _lh1
_ly_n = M + 8
try:
    _kv = json.load(open(os.path.join(HERE, "rhino", "out", "keikan_view.json"), encoding="utf-8"))
except Exception:
    _kv = {}
_kpersp = _kv.get("projection") == "perspective"
for _night, _yy in ((False, _ly_d), (True, _ly_n)):
    _nm = "yoru" if _night else "hiru"
    _rh = os.path.join(HERE, "rhino", "out", f"keikan_{_nm}.png")
    _ka = os.path.join(HERE, "out", f"keikan_kari_{_nm}.png")
    _src, _kind = (_rh, "Rhino") if _kpersp and os.path.exists(_rh) else ((_ka, "仮の図") if os.path.exists(_ka) else (None, None))
    if _src is None and _night and os.path.exists(os.path.join(HERE, "out", "keikan_kari_hiru.png")):
        _src, _kind = os.path.join(HERE, "out", "keikan_kari_hiru.png"), "仮の図（昼）"
    title(ax, _lx, _yy + _lh1 + TITLE_GAP, "沿川の景観　" + ("夜" if _night else "昼"), "高野川の向こう岸の歩道から、目の高さ1.5 m" + ("　本館と西館の越屋根の光" if _night else ""))
    if _src:
        _r = _img_box(_src, _lx, _yy, _lw1, _lh1, fit="contain", align="left")
        sozai("04" if _night else "03", "沿川の景観　" + ("夜" if _night else "昼"), 5, _r[0], _r[1], _r[2], _r[3], _kind + "（" + os.path.relpath(_src, HERE) + "）")
        if _night and _kind != "Rhino":
            dimnote(ax, _r[0] + 2, _r[1] + 2, "夜はRhinoの絵を待つ（いまは" + _kind + "）")
        print("沿川の景観", "夜" if _night else "昼", "：", _kind, os.path.relpath(_src, HERE))
    else:
        box(ax, _lx, _yy, _lw1, _lh1, "沿川の景観　" + ("夜" if _night else "昼"), "rhino/keikan_render.py の絵を待つ")
# 右の列：景観の法規と素材と色を一つの箱に（ユーザー 10-29：「景観のお約束を、景観の法規に。ここは情緒ではなく正確に。」「素材と色は上の囲みのなかに。色ラベルをもう少し小さくしてコンパクトに。」）
# 根拠は決定事項（共通）の「地区と法規」。高さは自動の図（立面）の縦の寸法「9,049　西館の最高」（GLから。+8,717 は FL±0 からの高さの記号）
_kx = _lx + _lw1 + 8
_kw = W - M - 6 - _kx
_KL = [
    "用途地域：第一種低層住居専用地域（都市計画法）。最高の高さは西館の棟で約9.0 m（GLから）。",
    "風致地区（京都市風致地区条例）：高野川特別修景地域（同条例第6条第1項による指定、許可基準は基準告示第7条）。右岸の基準：既存の樹木を保全する／河川に面する部分に植栽帯を設ける／建築物は原則として河川の側に勾配のある下屋を設けた和風の外観とする。"
    "対応：川の側に園庭の林と生垣、南に深い軒（下屋）、深い軒と縁側・杉の大和張りの板壁・ゆるい勾配の屋根。",
    "屋根の太陽光：同基準第7条第1項(80)で屋根に太陽光発電装置を原則として設けない。屋根材と一体の太陽電池で、黒い金属の屋根と見分けがつかず周辺の風致に不調和でない（同(80)の例外）。こども園で、同第7条第2項の例外（建築物全体のデザイン・公益上やむを得ない学校等の施設）にもあたるとする。",
    "遠景デザイン保全区域（京都市眺望景観創生条例）：外壁・屋根に禁止色を用いない、山並みと調和する。対応：黒い金属の屋根、木の色のまま。"]
_KS = 2.8                                      # 本文の文字
_sw = [("#B88A5A", "木の柱・梁（木の色のまま）"), ("#C9A77C", "杉の大和張り（銀鼠に枯れる）"), ("#2E2E30", "黒い金属の屋根（太陽光一体）"),
       ("#EDE7DA", "越屋根のガラス・縁側の白"), ("#8E9B86", "生垣と園庭の緑")]
_SWW, _SWH, _SWT = 8.0, 5.0, 2.4                # 色の見本：四角 8×5 mm、文字 2.4 mm、2列
_colw = (_kw - 6) / 2
_swl = [jwrap(t_, (_colw - _SWW - 6) / (_SWT / 0.72)) for _, t_ in _sw]
_rowh = [max(_SWH, len(l_) * _SWT / 0.72 * 1.3) + 2.0 for l_ in _swl]
_rows = [max(_rowh[i_:i_ + 2]) for i_ in range(0, len(_sw), 2)]
_body = sum(len(jwrap(t_, (_kw - 6) / (_KS / 0.72))) for t_ in _KL) * (_KS / 0.72 * 1.5) + (len(_KL) - 1) * (_KS / 0.72)
_mh = 7 + sum(_rows)                            # 素材と色（見出し＋見本）
_kh = 14 + _body + 2 + _mh + 3
_ky = M + 8 + bh - _kh                          # 箱の上は鳥瞰の上端にそろえ、下に余白（置き場所は木田さんが .ai で）
ibox(ax, _kx, _ky, _kw, _kh, "景観の法規", _KL, "#4E6FB0", "#F6F8FC", size=_KS, key="景観の約束")
dimnote(ax, _kx + 2, _ky - 4, "敷地が高野川の右岸にあるという読みは要確認（決定事項：たたき台の読み）")
_mtop = _ky + 3 + _mh                           # 素材と色の上端（箱の中、法規の文の下）
T(ax, _kx + 3, _mtop - 4, "素材と色", 3.2, "#4E6FB0", bold=True)
_yy = _mtop - 7
for r_ in range(0, len(_sw), 2):
    for c_ in range(2):
        i_ = r_ + c_
        if i_ >= len(_sw): continue
        x_ = _kx + 3 + c_ * _colw
        ax.add_patch(Rectangle((x_, _yy - _SWH), _SWW, _SWH, fc=_sw[i_][0], ec="#777777", lw=0.2))
        for j_, s_ in enumerate(_swl[i_]):
            T(ax, x_ + _SWW + 2, _yy - _SWH / 2 - 0.9 - j_ * _SWT / 0.72 * 1.3, s_, _SWT)
    _yy -= _rows[r_ // 2]
sozai("05", "素材と色", 5, _kx + 1, _ky + 1, _kw - 2, _mh + 2)
FIGS[5] = fig

# ================================================================ 6　断面・構造（10-30：6枚の6枚目。先生のエスキス 10-30、ユーザーが選んだ「6枚の構成」）
# 前の3枚目（断面と環境）から縦断A・断面C（空気）・断面D（光、採光の図）と inspired by。季節ごとの空気環境と環境への配慮は2枚目へ、面積表は4枚目へ。
# 構造の図（別の手伝い：present/sozai/18_構造_架構と耐力壁.pdf）を左下に
fig, ax = page()
frame(ax, 6, "断面・構造", "上に縦断A（弧の長さ）を一続きに。その下に二つの横断（1/100）：断面Cに空気の環境（本館と西館の架構と風の道）、断面D（本館、光の筋で切る）に光の環境。下に構造（架構と耐力壁の分布）・季節ごとの空気環境と環境への配慮・inspired byと面積表",
      "縦断A（上の帯）→断面C（空気）・断面D（光）→季節ごとの空気環境・配慮→構造→inspired by・面積表")
# 10-29 9:46（ユーザー）：横断の断面図が説明の主役。断面Cと断面Dは上と左右に矢印や注を描き込める余白（ユーザーが .ai で）。光の筋 1/20 と接合部の詳細は外した。
# 10-29 14:03（ユーザー）：「上繋がりで、それ（縦断）を一番上に置くのはどうでしょう」→ 縦断A を紙の上の帯のすぐ下に左から右へ。上下の空白（通り芯の上・地面の下）は切り抜きで詰めた
CLIP_SA3 = (54, 57.5, 821.5, 165.5)   # 10-29 15:16：上の帯が太くなったので上下をもう少し詰めた
_tA = H - M - HDR - 7
title(ax, M + 6, _tA, "縦断面図A", "1/100　保育室の中ほどの弧で切って展開、西を見る（左が南の高野川）")
_ya = _tA - TITLE_GAP - (CLIP_SA3[3] - CLIP_SA3[1])
embed(6, SEC, CLIP_SA3, M + 6 + (W - 2 * M - 12 - (CLIP_SA3[2] - CLIP_SA3[0])) / 2, _ya, 1.0, dwg=("SA", "縦断面図A"))
CLIP_C2 = (432, 252, 830, 382)
CSC = 1.0                                       # 課題は断面 1/100・2面以上（ユーザー、10-27夜：1/75 をやめる）
hC = (CLIP_C2[3] - CLIP_C2[1]) * CSC
wC = (CLIP_C2[2] - CLIP_C2[0]) * CSC
AIR = 30                                        # 断面の上に、矢印と注を描き込む余白（mm、10-29 14:03：40→30）
SIDE = 30                                       # 断面の左右の余白（mm）
_tC = _ya - 10                                  # 断面Cの題の高さ（縦断Aの下）
cx, cy = M + 6 + SIDE, _tC - 8 - AIR - hC
title(ax, M + 6, _tC, "断面図C　東西に切る（4歳・遊戯室）", "1/100　空気の環境：本館と西館の架構、昼と夏の夜の風の道")
embed(6, SEC, CLIP_C2, cx, cy, CSC, dwg=("C", "断面図C"))
_rx5 = cx + wC + SIDE + 6
_rw5 = W - M - 6 - _rx5
# 季節ごとの運転と環境への配慮（ユーザー 10-29 9:43：監修のまとめに従い、ボードに合う短さで。8つの箱はやめ、同じ範囲に三つ）
# 文字は一つずつ Illustrator の部品（鍵は固定：unten.*・reibou.*・hairyo.*。10-30 から2枚目）
C_UNTEN, C_HAIRYO = "#5B4A9E", "#4E8A3A"        # 見出しの色（運転＝紫、配慮＝緑）
UNTEN_SUM = "夏は夜の外気で床下の重さを冷やし、昼はその冷えと、触れて冷たい壁と天井扇で過ごす。冬は閉じて床から暖め、熱と湿気を逃がさない。春と秋は床下から越屋根へ風を通す。"
UNTEN_COLS = [("季節", 16), ("開け閉め", 67), ("動かすもの", 70), ("効くもの", 0)]   # 幅 mm（最後は残り）
UNTEN = [
    ("夏の昼", "窓・越屋根・床下の入口を閉じる", "放射冷房のパネル・天井扇（下向き）・床下の送風", "深い軒、夜に冷やした底板"),
    ("夏の夜", "縁側のガラリと西館の越屋根を開く（本館の越屋根は閉じる）", "開け閉めは自動（外気が涼しいとき・雨で閉じる）", "外気が床下の底板を冷やす。遊戯室の吹き抜けの高低差約8 mで引く"),
    ("春・秋", "窓・越屋根を開く", "機械は止める", "通風（梁間から越屋根へ）"),
    ("冬", "すべて閉じる", "床下の暖房・全熱交換の換気・加湿・天井扇（上向きに弱く）", "断熱と気密。ガラス戸の際の床からの暖気がガラスの冷えを止める")]
REIBOU = "保育室と遊戯室の壁、こどもの手の届く高さに置く。表面は約15℃で、触れて「つめた！」とわかる。結露した水を外へ流して除湿も兼ねる。風が無いので静かで、午睡を妨げない。"
HAIRYO = [                                      # LEED v5 BD+C の評価項目の順（ユーザー 10-29 12:52：評価項目に沿わせる、Gold を「目指す」）
    ("統合的なプロセス（IP）", "一つの形で二つ以上を解く。本館の弧＝朝の日と、夏の夜に谷を下りる冷気（1枚目）。片流れの屋根＝景観と、越屋根へ上る空気の流れ（断面C）。縁側の段のガラリ＝夜の外気を床下へ入れ、ガラス戸をすっきり保つ。井戸＝冷暖房の熱源と、災害時の近隣の水"),   # ユーザー 10-29：具体例で
    ("立地と交通（LT）", "車は5台に絞り、送迎は徒歩と自転車（駐輪21台）。西の道に歩道を開く"),
    ("持続可能な敷地（SS）", "小竹薮公園と既存の木を残す。園庭の林。雨庭と浸透側溝で雨を敷地に返す"),
    ("水の効率（WE）", "雨を庭へ。地下水を使う"),
    ("エネルギーと大気（EA）", "断熱・気密、深い軒と遮熱Low-Eで日射を切る、ベタ基礎の底板に夜の冷えをためる、放射冷房と全熱交換、地下水を熱源にしたヒートポンプ、屋根材型の太陽光と蓄電池"),
    ("材料と資源（MR）", "北山杉の間伐材、木造。3 mの架構は残し中は変えられる（スケルトン＆インフィル）。野菜くずのコンポスト"),
    ("室内環境の質（EQ）", "光の筋の鏡面で奥まで昼光。風の音のない放射冷房。自然換気（床下→梁間→越屋根）。静養室と大人の便所は別の換気。2階の窓から川と空"),
    ("地域の優先（PR）", "災害時の持ちつ持たれつ：太陽光と蓄電池の電気と、地下水を近隣に提供できる。浸水のときは京都工芸繊維大学へ避難の協定")]   # ユーザー 10-29：「拠点」は役所が決めること


def _part(id_, x, y, w, lines, size, color=INK, bold=False, lead=1.3, name=None, group=None, ha="left"):
    """文字の部品（固定の鍵）。lines は折り返した行。見本は T で描く。返り値は使った高さ（mm）。group＝.ai でまとめるグループ（鍵, 名前）"""
    s_ = "".join(lines)
    g_ = dict(group=group[0], group_name=group[1]) if group else {}
    if w:
        _airec(fig, kind="area", id=id_, name=name or ("文：" + s_[:12]), x=x, y=y, w=w, h=len(lines) * size / 0.72 * lead + 1,
               s=s_, size=size, color=color, bold=bold, leading=lead, para_space=0, **g_)
    else:
        _airec(fig, kind="text", id=id_, name=name or ("文：" + s_[:12]), x=x, y=y, s=s_, size=size, color=color, bold=bold, ha=ha, va="baseline", **g_)
    AIMUTE[0] += 1
    for k_, l_ in enumerate(lines):
        T(ax, x, y - k_ * size / 0.72 * lead, l_, size, color, bold=bold, ha=ha)
    AIMUTE[0] -= 1
    return len(lines) * size / 0.72 * lead


def _rule(id_, pts, color, lw, group=None, name=None):
    """罫線の部品（パス、固定の鍵）。pts は紙の mm（下原点）、lw は pt"""
    P_ = np.asarray(pts, float)
    ax.plot(P_[:, 0], P_[:, 1], color=color, lw=lw, gid="aipart", solid_capstyle="butt")
    _airec(fig, kind="line", id=id_, name=name or "罫線", pts=[list(map(float, q)) for q in P_], color=color, lw=lw,
           **(dict(group=group[0], group_name=group[1]) if group else {}))


G_UNTEN = ("unten", "季節ごとの空気環境")
G_HAIRYO = ("hairyo", "環境への配慮")
G_IA = ("insp_area", "inspired by と面積表")

# 断面D（本館の横断、光の筋で切る、1/100、北を見る）：光の環境。図は更新係に依頼（20261029-0946-present）。
# drawings/sodachiya_sections*_views.json に「断面D」があれば、その範囲を断面Cと同じ仕組み（Rhinoの図があればRhino、文字と寸法は部品）で
_SD = None
for _vf in sorted(glob.glob(os.path.join(ROOT, "drawings", "sodachiya_sections*_1-100_views.json"))):
    try:
        for _v in json.load(open(_vf, encoding="utf-8")).get("views", []):
            if _v.get("name", "").startswith("断面D"):
                _c = _v["clip_paper_mm"]                  # 上の 8 mm は図の題（題は mock.py が書く）なので切る
                _SD = (_vf[:-len("_views.json")] + ".pdf", (_c[0], _c[1] + 8, _c[2], _c[3]))
    except Exception:
        pass
DW, DH = (_SD[1][2] - _SD[1][0], _SD[1][3] - _SD[1][1]) if _SD else (250.0, 90.0)   # 無いあいだは約25 m×約9 m（西の吹き抜けの縁から東の外縁側の先まで）
# 右下の縦長の囲み：上に inspired by、細い罫線、下に面積表（ユーザー 10-29 10:26・12:49・12:50：縦長に、イメージではなく文字に、列ごとに一つの文字）
# 部品はグループ「inspired by と面積表」：囲み p3.ia.box、罫線 p3.area.rule.*、inspired by は一つの文字 p3.insp.text（8件を段落で、名前は太・出どころは小さく灰）、
# 面積表は列ごとに一つの文字 p3.area.col.room／req／plan（1行目が見出し、最後が延床、どちらも太。計画は右揃え）。数は sodachiya_areas.json から自動
IA_W = 133                                      # 囲みの幅（mm）。inspired by を2行にしたので、いちばん長い行（斑鳩の2行目、約120 mm）が入る幅（ユーザー 10-30）
IA_PAD = 6
IA_FS = 2.4                                     # 面積表の字
IA_ROW = IA_FS + 1.9                            # 面積表の行送り（mm、10-29 15:16：2.2→1.9）
_ia_rows = [r_ for r_ in AJ["rooms"] if not (r_["planned"] is None and not r_["judge"]) or r_["room"] == "食堂"]


def _mpart(id_, x, y, paras, group, name, ha="left"):
    """段落ごとに書式のある一つの文字の部品。paras = [(文, 字mm, 色, 太字, 前の行からの送りmm)]。返り値は最後の行の基準線"""
    paras = [tuple(q_) + (None,) * (6 - len(q_)) for q_ in paras]     # 6つ目：後ろの区間 (何文字目から, 字mm, 色, 太字)（10-30）
    st_ = [dict(size_pt=sz_ / 0.72 / 0.3528, font="W6" if bd_ else "W3", color=matplotlib.colors.to_hex(c_), leading_pt=ld_ / 0.3528,
                **({"tail": dict(**{"from": tl_[0]}, size_pt=tl_[1] / 0.72 / 0.3528, font="W6" if tl_[3] else "W3", color=matplotlib.colors.to_hex(tl_[2]))} if tl_ else {}))
           for (_, sz_, c_, bd_, ld_, tl_) in paras]
    _airec(fig, kind="text", id=id_, name=name, x=x, y=y, s="\n".join(t_ for t_, *_ in paras), size=paras[0][1], color=paras[0][2], bold=paras[0][3],
           ha=ha, va="baseline", para_styles=st_, group=group[0], group_name=group[1])
    AIMUTE[0] += 1
    yy = y
    for k_, (t_, sz_, c_, bd_, ld_, tl_) in enumerate(paras):
        if k_:
            yy -= ld_
        if tl_:
            h_ = t_[:tl_[0]]
            T(ax, x, yy, h_, sz_, c_, bold=bd_, ha=ha)
            T(ax, x + fitz.Font(fontfile=FONTB if bd_ else FONT).text_length(h_, sz_ / 0.72), yy, t_[tl_[0]:], tl_[1], tl_[2], bold=tl_[3], ha=ha)
        else:
            T(ax, x, yy, t_, sz_, c_, bold=bd_, ha=ha)
    AIMUTE[0] -= 1
    return yy


# 10-30 16:15（ユーザー）：inspired by と面積表は6枚目の右下の縦長の囲みに戻す（前の3枚目の割付、上から inspired by・面積表）
_INS_P = []
for i_, (n_, src_, what_) in enumerate(INSP):
    # 2行に（ユーザー 10-30）：1行目＝名前（太）＋出どころ（小さく灰）、2行目＝何を参考にしたか
    _INS_P += [(n_ + "　" + src_, 2.6, INK, True, 0 if i_ == 0 else 5.7, (len(n_) + 1, 2.2, "#666666", False)), ("→" + what_, 2.4, INK, False, 3.9)]
_ins_h = sum(p_[4] for p_ in _INS_P)
_bw = IA_W
_bh = IA_PAD + 4 + 9 + _ins_h + 4 + 8 + 9 + (len(_ia_rows) + 1) * IA_ROW + IA_PAD
_bx0 = W - M - 6 - _bw
_by = M + 8
ax.add_patch(Rectangle((_bx0, _by), _bw, _bh, fc="none", ec="#8A8A8A", lw=0.3, gid="aipart"))
_airec(fig, kind="box", id="ia.box", name="囲み：inspired by と面積表", x=_bx0, y=_by, w=_bw, h=_bh, fill="none", stroke="#8A8A8A", lw=0.3, dash=None,
       group=G_IA[0], group_name=G_IA[1])
_ix = _bx0 + IA_PAD
_iw = _bw - 2 * IA_PAD
_y = _by + _bh - IA_PAD - 4
_part("insp.head", _ix, _y, 0, ["inspired by"], 4.2, INK, True, name="見出し：inspired by", group=G_IA)
_part("insp.sub", _ix + 34, _y, 0, ["参照した建築"], 3.0, INK, name="見出しの添え：参照した建築", group=G_IA)
_y -= 9
_y = _mpart("insp.text", _ix, _y, _INS_P, G_IA, "inspired by（8件）")
_y -= 4
_rule("area.rule.sep", [(_ix, _y), (_ix + _iw, _y)], "#BBBBBB", 0.25, G_IA, "罫線：inspired by と面積表のあいだ")
_y -= 8
_part("area.head", _ix, _y, 0, ["面積表"], 4.2, INK, True, name="見出し：面積表", group=G_IA)
_part("area.sub", _ix + 21, _y, 0, ["m²（壁芯、3dmから自動）"], 3.0, INK, name="見出しの添え：面積表", group=G_IA)
_y -= 9
_rule("area.rule.top", [(_ix, _y + IA_FS + 1.2), (_ix + _iw, _y + IA_FS + 1.2)], "#666666", 0.35, G_IA, "罫線：面積表の上")
_rule("area.rule.head", [(_ix, _y - 1.6), (_ix + _iw, _y - 1.6)], "#999999", 0.25, G_IA, "罫線：面積表の見出しの下")
_cols = {"room": ["室"], "req": ["要求"], "plan": ["計画"]}
for r_ in _ia_rows:
    _cols["room"].append(r_["room"].replace(" ", ""))
    _cols["req"].append(r_["required"].replace(" ", ""))
    # 食堂は「なし」、駐車・駐輪は台数（サービス車・職員の分も、ユーザー 10-30）。台数は areas.json の parts（決定事項_外構・外構の図の counts）から
    _pl = {"食堂": "なし", "駐車場": "5台（うち搬入1）",
           "駐輪スペース": "21台（保護者12・職員9）"}.get(r_["room"].replace(" ", ""))
    if r_["room"].replace(" ", "") == "駐車場" and "南 3" not in r_.get("parts", ""):
        _pl = None; print("面積表：駐車場の台数が変わった。mock.py の台数を直す：", r_.get("parts"))
    if r_["room"].replace(" ", "") == "駐輪スペース" and "計 21" not in r_.get("parts", ""):
        _pl = None; print("面積表：駐輪の台数が変わった。mock.py の台数を直す：", r_.get("parts"))
    _cols["plan"].append(_pl or (f"{r_['planned']:.1f}" if r_["planned"] else r_["judge"]))
_cols["room"].append("延床（2,000以内）"); _cols["req"].append(""); _cols["plan"].append(f"{AJ['floor']['total']:,.1f}")
_cx = {"room": _ix, "req": _ix + 44, "plan": _ix + _iw}       # 要求は左揃え、計画は右揃え（小数点がそろう）
_nm = {"room": "室", "req": "要求", "plan": "計画"}
for k_, col_ in _cols.items():
    n_ = len(col_)
    _yl = _mpart(f"area.col.{k_}", _cx[k_], _y, [(t_, IA_FS, INK, j_ in (0, n_ - 1), IA_ROW) for j_, t_ in enumerate(col_)], G_IA,
                 f"面積表の列：{_nm[k_]}", ha="right" if k_ == "plan" else "left")
_rule("area.rule.bottom", [(_ix, _yl - 1.6), (_ix + _iw, _yl - 1.6)], "#666666", 0.35, G_IA, "罫線：面積表の下")
# 断面D：10-30（6枚）から、既定は木田さんが .ai で置いた所と大きさ（layout_user.json の p6.link.sodachiya_sections2_1-100 と題の文字）。
# 6枚目の左下を構造の図に空けるため（.ai では断面Dは断面Cの右）。記録が無ければ前の既定（断面Cの下、1/100）。上に光の矢印を描く余白 AIR_D
AIR_D = 42
_uD = _UP.get("p6.link.sodachiya_sections2_1-100") or {}
_uDt = _UP.get("p6.t.断面図D本館の横断（光の筋で") or {}
D_SC = 1.0
if _SD and all(k_ in _uD for k_ in ("x", "y", "w")):
    # .ai の断面Dのリンクは木田さんの記録の幅（240 mm）で置かれる（ai_layout が w から倍率を出す）。図面の文字・寸法の部品と採光の図も同じ倍率にそろえる
    # （10-30：更新係の断面Dが 395×123 mm に広がったので約0.61倍。1/100 に戻すかは木田さんが .ai で決める）
    D_SC = round(_uD["w"] / DW, 4)
    dx, dy = _uD["x"], H - _uD["y"] - DH * D_SC
    _tD = H - _uDt["y"] if "y" in _uDt else dy + DH * D_SC + AIR_D * D_SC + 8
    _tDx = _uDt.get("x", dx)
else:
    _r2t, _r2b = cy - 14, M + 8
    _tD = (_r2t + _r2b) / 2 + (8 + AIR_D + DH) / 2
    dx, dy = cx + (wC - DW) / 2, _tD - 8 - AIR_D - DH
    _tDx = M + 6
title(ax, _tDx, _tD, "断面図D　本館の横断（光の筋で切る）", "1/100　北を見る　光の環境：光の筋の鏡面の溝・東のガラス戸・深い軒・西の吹き抜けの越屋根")
if _SD and os.path.exists(_SD[0]):
    embed(6, _SD[0], _SD[1], dx, dy, D_SC, dwg=("D", "断面図D"))
    print("断面D：", os.path.basename(_SD[0]), _SD[1])
    # 採光の図（素材17、present/tools/saikou.py）を断面Dの上に重ねる。置き場所は 17_光の環境_断面.json（断面Dの紙の mm、1 mm＝1 mm）。
    # 見本には PDF を重ね、.ai では 17_光の環境_断面_parts.json の文字と線の部品を、断面図Dのグループの中のグループ「光の環境」に（ユーザー 10-29 14:11）
    _s17 = os.path.join(HERE, "sozai", "17_光の環境_断面.pdf")
    _j17 = os.path.join(HERE, "sozai", "17_光の環境_断面.json")
    _q17 = os.path.join(HERE, "sozai", "17_光の環境_断面_parts.json")
    if os.path.exists(_s17) and os.path.exists(_j17):
        _p17 = json.load(open(_j17, encoding="utf-8"))["page_paper_mm"]
        _x17 = dx + (_p17[0] - _SD[1][0]) * D_SC
        _y17 = (dy + DH * D_SC) - (_p17[3] - _SD[1][1]) * D_SC
        EMB_DWG[(6, len(embeds[6]))] = dict(dwg="断面図D", parts=_q17 if os.path.exists(_q17) else None,
                                            tl=(dx, H - (dy + DH * D_SC)), origin=(_SD[1][0], _SD[1][1]), group=("saikou", "光の環境"), scale=D_SC)
        embed(6, _s17, None, _x17, _y17, D_SC)
        print("採光の図（素材17）：断面Dの上に、上へ %.1f mm はみ出す（余白 %d mm）、.ai は%s" % (_SD[1][1] - _p17[1], AIR_D, "部品" if os.path.exists(_q17) else "PDF"))
else:
    box(ax, dx, dy, DW * D_SC, DH * D_SC, "断面図D　本館の横断（光の筋で切る）1/100　北を見る",
        "光の環境：光の筋の鏡面の溝・東のガラス戸・深い軒・西の吹き抜けの越屋根\n（更新係の図を待つ：20261029-0946-present）")
    print("断面D：まだ図が無いので枠")
# 構造の図（10-30、先生のエスキス）：別の手伝いが present/sozai/18_構造_架構と耐力壁.pdf を作る。左下（断面Cの下）に約380×150 mm。
# 無いあいだは同じ大きさの仮の枠。ファイルができたら mock.py を走らせ直すだけで入る（見本は貼り込み、.ai はリンク）
KOZO = os.path.join(HERE, "sozai", "18_構造_架構と耐力壁.pdf")
KZ_W, KZ_H = 380.0, 150.0
_kzt = H - 352.0
title(ax, M + 6, _kzt, "構造", "架構と耐力壁の分布")
if os.path.exists(KOZO):
    embed(6, KOZO, None, M + 6, _kzt - TITLE_GAP - KZ_H, fit=(KZ_W, KZ_H))
    _topalign(6, _kzt - TITLE_GAP)
    print("構造の図：", os.path.relpath(KOZO, HERE))
else:
    box(ax, M + 6, _kzt - TITLE_GAP - KZ_H, KZ_W, KZ_H, "構造：架構と耐力壁の分布（作成中）", "sozai/18_構造_架構と耐力壁.pdfができたら入る")
    print("構造の図：まだ無いので仮の枠")
# ---- 季節ごとの空気環境と環境への配慮（10-30 18:05、ユーザー：最後の枚に属する。2枚目から6枚目へ。断面Cの下、構造の図の右、inspired by の囲みの左。少し窮屈でよい）
_rx5 = M + 6 + KZ_W + 8
_rw5 = W - M - 6 - IA_W - 8 - _rx5
_top5 = H - 343.0                               # 範囲の上端（断面Cの下）
_bot5 = M + 8
_HAIRYO_TOP_EST = None
_gap5 = 9                                       # 運転と配慮のあいだ
_Lw = _rw5                                      # 一つの列に上から：季節ごとの運転・放射冷房のパネル・環境への配慮
_Rw = _rw5
_FS = None
for _fs in (3.0, 2.8, 2.6, 2.4, 2.2):                     # 入る字の大きさを選ぶ
    _cpl = lambda w_: w_ / (_fs / 0.72)
    _lh = _fs / 0.72 * 1.3
    _cw = [w_ or (_Lw - sum(c[1] for c in UNTEN_COLS)) for _, w_ in UNTEN_COLS]
    _rows_h = [max(len(jwrap(t_, _cpl(_cw[j_] - 2))) for j_, t_ in enumerate(r_)) * _lh + 2.4 for r_ in UNTEN]
    _hl = 6 + len(jwrap(UNTEN_SUM, _cpl(_Lw))) * _lh + 2 + (_lh + 2.4) + sum(_rows_h) + 5 + 6 + len(jwrap(REIBOU, _cpl(_Lw - 4))) * _lh + 4
    _nw = max(len(n_) for n_, _ in HAIRYO) * _fs / 0.72 + 3
    _hr = 6 + sum(len(jwrap(t_, _cpl(_Rw - _nw))) * _lh + 1.6 for _, t_ in HAIRYO)
    if _hl + _gap5 + _hr <= _top5 - _bot5:
        _FS = _fs
        break
if _FS is None:
    raise SystemExit("6枚目：季節ごとの運転と環境への配慮が 2.2 mm でも入らない（運転 %.0f・配慮 %.0f／%.0f mm）" % (_hl, _hr, _top5 - _bot5))
print("6枚目の運転と配慮：字 %.1f mm、運転 %.0f・配慮 %.0f／%.0f mm" % (_FS, _hl, _hr, _top5 - _bot5))
# 素材12・12bはやめた：文字と罫線は Illustrator の部品（ユーザー 10-29 12:49：イメージではなく文字に）
# 左：季節ごとの運転
_x0, _y = _rx5, _top5 - 4
_part("unten.head", _x0, _y, 0, ["季節ごとの空気環境"], 3.2, C_UNTEN, True, name="見出し：季節ごとの空気環境", group=G_UNTEN)   # ユーザー 10-29：「運転」→「空気環境」
_y -= 6
_y -= _part("unten.sum", _x0, _y, _Lw, jwrap(UNTEN_SUM, _cpl(_Lw)), _FS, name="まとめ：季節ごとの運転", group=G_UNTEN) + 1
_xs = [_x0]
for w_ in _cw[:-1]:
    _xs.append(_xs[-1] + w_)
_rule("unten.rule.top", [(_x0, _y), (_x0 + _Lw, _y)], C_UNTEN, 0.5, G_UNTEN)
_ytb = _y
_y -= _lh
for j_, (h_, _) in enumerate(UNTEN_COLS):
    _part(f"unten.h.c{j_}", _xs[j_] + 1, _y, 0, [h_], _FS, C_UNTEN, True, name="表の見出し：" + h_, group=G_UNTEN)
_y -= 2.4
_rule("unten.rule.head", [(_x0, _y + 1), (_x0 + _Lw, _y + 1)], C_UNTEN, 0.3, G_UNTEN)
for i_, r_ in enumerate(UNTEN):
    _yt = _y - _lh + 0.6
    for j_, t_ in enumerate(r_):
        _part(f"unten.r{i_}.c{j_}", _xs[j_] + 1, _yt, _cw[j_] - 2, jwrap(t_, _cpl(_cw[j_] - 2)), _FS, bold=(j_ == 0), name=f"表：{r_[0]}・{UNTEN_COLS[j_][0]}", group=G_UNTEN)
    _y -= _rows_h[i_]
    _rule(f"unten.rule.r{i_}", [(_x0, _y + 1), (_x0 + _Lw, _y + 1)], "#9A9A9A", 0.2, G_UNTEN)
for j_, x_ in enumerate(_xs[1:]):
    _rule(f"unten.rule.c{j_ + 1}", [(x_ - 0.5, _y + 1), (x_ - 0.5, _ytb)], "#BBBBBB", 0.2, G_UNTEN)
# 左の下：放射冷房のパネル（小さな段、左に色の帯）
_y -= 5
_rl = jwrap(REIBOU, _cpl(_Lw - 4))
_rh = 6 + len(_rl) * _lh + 1
_rule("reibou.bar", [(_x0 + 0.6, _y + 2), (_x0 + 0.6, _y - _rh + 2)], C_UNTEN, 1.2 / 0.3528, G_UNTEN)
_part("reibou.head", _x0 + 4, _y - 2, 0, ["放射冷房のパネル"], 3.0, C_UNTEN, True, name="見出し：放射冷房のパネル", group=G_UNTEN)
_part("reibou.text", _x0 + 4, _y - 2 - 5.5, _Lw - 4, _rl, _FS, name="本文：放射冷房のパネル", group=G_UNTEN)
_HAIRYO_TOP_EST = _top5 - _hl - _gap5
if _HAIRYO_TOP_EST - _hr < _bot5 - 0.5:
    raise SystemExit("6枚目：環境への配慮が紙の下に入らない")
# 右：環境への配慮（一年を通して効くもの）
_HAIRYO_TOP = _top5 - _hl - _gap5              # 季節ごとの運転の下に続ける

_x1, _y = _rx5, _HAIRYO_TOP - 4
_part("hairyo.head", _x1, _y, 0, ["環境への配慮（LEED v5 Goldを目指す）"], 3.2, C_HAIRYO, True, name="見出し：環境への配慮", group=G_HAIRYO)
_part("hairyo.url", _x1 + _Rw, _y, 0, ["LEED v5（USGBC）　https://www.usgbc.org/leed/v5"], 2.2, "#777777", False,
      name="LEED v5 のURL", group=G_HAIRYO, ha="right")    # ユーザー 10-29：LEED v5 の文書のURL
_y -= 3
_rule("hairyo.rule", [(_x1, _y), (_x1 + _Rw, _y)], C_HAIRYO, 0.5, G_HAIRYO)
_y -= _lh
for i_, (n_, t_) in enumerate(HAIRYO):
    _part(f"hairyo.{i_}.name", _x1, _y, 0, [n_], _FS, C_HAIRYO, True, name="配慮の項目：" + n_, group=G_HAIRYO)
    _tl = jwrap(t_, _cpl(_Rw - _nw))
    _part(f"hairyo.{i_}.text", _x1 + _nw, _y, _Rw - _nw, _tl, _FS, name="配慮の文：" + n_, group=G_HAIRYO)
    _y -= len(_tl) * _lh + 1.6
FIGS[6] = fig

# ================================================================ 3　平面図　1階（10-30：6枚の3枚目。前の4枚目の平面図のうち1階。ユーザー、10-25：敷地全体1/100を配置図と同じ向き。図は更新係のdraw100.pyがA1の一枚で出す）
fig, ax = page()
# 共通の枠をそのまま当てる（ユーザー 10-29 18:01）：平面図は動かさず縮めず（枠の帯と重なってよい）。白い地の紙いっぱいの図なので、枠はその上に重ねる（FRAME_TOP）
frame(ax, 3, "平面図　1階", "敷地全体の1階の平面図1/100、配置図と同じ向き。2階（西館）は4枚目", "平面図→色の凡例・面積")
PLAN3 = os.environ.get("SODACHIYA_PLAN3", PLAN)        # 確かめるときだけ手元の書き出しを指す
# 1階だけを前と同じ紙の位置（1:1）に。更新係の一枚では2階（西館）が左上（西の道路の外）にあるので、三つの四角で切り抜いて外す（仮、10-30）：
# 2階の角は x≈393 mm・y≈71 mm、下の端は y≈295 mm。キッチンの左の端は x≈387 mm（y 190〜290 mm）なので、細い帯で拾う。
# 四角の境をまたぐ寸法・文字は部品にならない（parts_for は中に収まる物だけ）
# 文字と寸法の部品は紙全体から作り（鍵が前の4枚目と同じ）、2階の範囲（PLAN_2F_EX）に中心のある物だけ除く。線だけのリンクは三つ（部品は一つ目に）
PLAN_1F_CLIPS = [(394, 0, 841, 594), (380, 90, 394, 594), (0, 298, 380, 594)]
PLAN_2F_EX = [(0, 0, 380, 298), (380, 0, 394, 90)]
# 10-30 18:05（ユーザー）：平面図を 200 pt（約70.6 mm）左へ動かし、道路・お向かいさん・隣家で紙全体を埋める（木田さんの .ai に平面図の切り抜きの記録は無いので、既定の位置からずらす）。
# 周りは配置図と同じ情報（西の道・北の道・向かいの住宅・東の隣家・公園、PLATEAU と理想化した道）を1/100で薄く。平面図（白い地）の下に一枚の素材（sozai/24）として敷く。
# 左端の色の凡例・方位・縮尺は紙の外へ出る
PLAN_SX = -200 * 0.3528
_pv = {v_["name"]: v_ for v_ in json.load(open(os.path.join(DRW, "sodachiya_plan_1-100_views.json"), encoding="utf-8"))["views"]}
_m1, _m2 = _pv["1階平面"]["model_to_paper"], _pv["2階平面（西館）"]["model_to_paper"]
_A3P = [1000 * _m1["a"], 1000 * _m1["b"], -1000 * _m1["d"], -1000 * _m1["e"], _m1["c"] + PLAN_SX, H - _m1["f"]]   # 3dm（m）→ 紙（下原点）
T3P = lambda g_: affinity.affine_transform(g_, _A3P) if g_ is not None else None
TRP = lambda g_: T3P(affinity.affine_transform(g_, [_INV[0, 0], _INV[1, 0], _INV[0, 1], _INV[1, 1], _INV[2, 0], _INV[2, 1]])) if g_ is not None else None   # 回した座標 → 紙
_XID = lambda P_: np.asarray(P_, float)[:, :2]
_PAGE = Polygon([(M, M), (W - M, M), (W - M, H - M - HDR), (M, H - M - HDR)])   # 枠の内（上の帯は除く）


def _mawari(path, extra=None, cut=None):
    """平面図の周り（紙の座標の一枚の透明な PDF）。extra(ax)＝足して描く物、cut＝描かない範囲（紙の座標）"""
    f_ = plt.figure(figsize=(W / 25.4, H / 25.4))
    a_ = f_.add_axes([0, 0, 1, 1]); a_.set_xlim(0, W); a_.set_ylim(0, H); a_.axis("off")
    cl_ = (lambda g_: g_.intersection(_PAGE).difference(cut) if cut is not None else g_.intersection(_PAGE))
    draw_shape(a_, cl_(T3P(ROADS)), _XID, fc="#ECECEA", ec="#C8C8C6", lw=0.15, z=1)
    for b_ in BLDS:
        g_ = cl_(T3P(b_))
        if not g_.is_empty:
            draw_shape(a_, g_, _XID, fc="#F3F3F1", ec="#B5B5B5", lw=0.15, z=2)
    draw_shape(a_, cl_(T3P(gc.PARK)), _XID, fc="#EEF3E8", ec="#B9C9A8", lw=0.15, z=1.5)
    draw_shape(a_, cl_(T3P(_SITE3).exterior), _XID, ec="#999999", lw=0.2, z=3, ls=(0, (6, 1.5, 1, 1.5)))
    if extra:
        extra(a_, cl_)
    f_.savefig(path, transparent=True)
    plt.close(f_)
    return path


MAWARI3 = _mawari(os.path.join(HERE, "sozai", "24_平面図の周り_1階.pdf"))
embed(3, MAWARI3, None, 0, 0, 1.0)                # 平面図の下（先に置いた物が下）
for _i1, _c1 in enumerate(PLAN_1F_CLIPS):
    embed(3, PLAN3, _c1, _c1[0] + PLAN_SX, H - _c1[3], 1.0, dwg=("plan", "平面図　1階"),
          dwg_opt=dict(parts_clip=(0, 0, W, H), exclude=PLAN_2F_EX) if _i1 == 0 else dict(noparts=True))
FIGS[3] = fig

# ================================================================ 2　ゾーニングと動線・環境（10-30：6枚の2枚目。先生のエスキス 10-30）
# 10-30 16:15（ユーザー）：こどもたちの環境も全部2枚目に詰める。左：ゾーニング1/200（園庭と一体、土足・トイレ・駐車場・歩道）と樹木図1/400。
# 右：一日の帯3コマ（朝・日中・時間外）、季節ごとの空気環境と環境への配慮、遊戯室（平面）・教室3つ・居場所2つの軸測図
fig, ax = page()
frame(ax, 2, "ゾーニングと動線・環境", "左にゾーニング（園庭と一体、使う人・土足・トイレ）と樹木。右の上に一日の帯（朝と帰り・日中・食事・延長保育）、下に教室・居場所・遊戯室",
      "ゾーニング→一日の帯→教室・居場所・遊戯室→樹木")
Y = lambda t_: H - t_                            # 紙の上からの mm → 下からの mm
_RX = M + 6 + 340 + 8                           # 右の列の左（左の列はゾーニング1/200の幅）
_RW = W - M - 6 - _RX
# 一日の帯・ゾーニング・樹木図も配置図と同じ向き（高野川を下辺）に回す（ユーザー、10-25）。描くあいだだけ形を回したものに入れ替える
_rs = lambda P: np.c_[np.asarray(P)[:, 0] * np.cos(_rr) - np.asarray(P)[:, 1] * np.sin(_rr), np.asarray(P)[:, 0] * np.sin(_rr) + np.asarray(P)[:, 1] * np.cos(_rr)]
_SAVE = (list(plan_items), dict(GD), roofs_plan)
plan_items[:] = [(ln_, k_, rot(g_)) for ln_, k_, g_ in plan_items]
GD.update({k_: ([rot(x_) for x_ in v_] if isinstance(v_, list) else rot(v_)) for k_, v_ in GD.items()})
roofs_plan = rot(roofs_plan)
def lcen(prefixes):
    gs = [g for ln, k, g in plan_items if ln.startswith(tuple(prefixes)) and k == "mesh"]
    return np.array(unary_union(gs).centroid.coords[0])


def _c(name):
    """動線の点：部屋のレイヤーの頭か、園庭の名前（GD）か、公園"""
    if name == "park":
        return _rs(to_s(np.atleast_2d(np.array(gc.PARK.centroid.coords[0]))))[0]
    if name in GD:
        return np.array(GD[name].centroid.coords[0])
    return lcen([name])


# 図の範囲：敷地と西の道路（ユーザー 10-30 16:15：西の道路を含める）。西（左）と北西（上）へ 4 m、ほかは 1 m
_sb = _SITEP.bounds
WX0, WY0, WX1, WY1 = _sb[0] - 4.0, _sb[1] - 1.0, _sb[2] + 1.0, _sb[3] + 4.0
_WIN = Polygon([(WX0, WY0), (WX1, WY0), (WX1, WY1), (WX0, WY1)])
_ROADS_R = unary_union([rot(g_) for ln_, g_ in CTX if ln_.startswith("03_") and g_ is not None and g_.geom_type.endswith("Polygon")]).buffer(0).intersection(_WIN)
_swS2 = _SITEP.intersection(LineString([_A_ - _tW * 10, _B_ + _tW * 10]).buffer(1.0, cap_style=2)).intersection(_slab).difference(_PARK_R.buffer(0.02))   # 西の道沿いの歩道 1 m

# ---- 一日の帯（10-30 22:44：4コマ）は、ゾーニングの色の体系で塗るので、ゾーニングの形を作ったあと（下）で描く
fh = 150
fy = Y(45) - fh

# ---- ゾーニング 1/200（10-30 22:14 直し、ユーザー）：園庭も土足。セキュリティ外・セキュリティ内（外構）・建物の中の土足・乳児の園庭・しずかのもり・だいさんかくを
# 同じ色相（H 28°）で彩度・明度を変えた一族に。塀・柵・木戸（セキュリティの線）は太い線。駐車・駐輪は灰、トイレ・倉庫・水はそれぞれの色。白い抜けは下に地の色を敷いて無くす
import colorsys
_HSB = lambda h_, s_, b_: matplotlib.colors.to_hex(colorsys.hsv_to_rgb(h_ / 360, s_, b_))
F_H = 28                                          # 土足の一族の色相
Z_COL = {"z02": "#C5DE9A", "z35": "#7FB872", "share": C_SHARE, "adult": C_ADULT, "kitchen": "#E8A6A6",
         "wc": "#6FA8C6", "store": "#8E8E8E",                                     # 倉庫は無彩色の濃い灰（大人の紫と分ける、10-30 23:07）
         # セキュリティ外は青みの灰の族、セキュリティ内（外構・土足・園庭）は土の色相の族（ユーザー 10-30 23:07：内と外をはっきり）
         "out": _HSB(212, 0.07, 0.93), "in_ext": _HSB(F_H, 0.20, 0.90), "shoe": _HSB(F_H, 0.30, 0.88),
         "g02": _HSB(F_H, 0.28, 0.80), "gboth": _HSB(F_H, 0.40, 0.71), "g35": _HSB(F_H, 0.52, 0.62),
         "park_car": _HSB(212, 0.10, 0.70), "water": "#B8DDF2", "park": "#E3EDD8"}
Z_LEG1 = [("z02", "0〜2歳"), ("z35", "3〜5歳"), ("share", "みんなの場所"), ("adult", "大人"), ("kitchen", "調理"), ("wc", "トイレ"), ("store", "倉庫")]
Z_LEG2 = [("out", "セキュリティ外（歩道・ひろば・搬入路）"), ("in_ext", "セキュリティ内の外構（北の坪庭・読書の庭）"),
          ("shoe", "土足（木戸の内の小径・ムベの下、受け取り土間・あまのがわ・外縁側）")]
Z_LEG3 = [("g02", "乳児の園庭（みなみのさんかく）"), ("gboth", "しずかのもり（両方）"), ("g35", "だいさんかく（3〜5歳）"),
          ("park_car", "駐車場・駐輪場"), ("water", "水遊び場・雨庭"), ("park", "公園")]
ZONE = {"53_": "z02", "54_": "z02",
        "59_1F_3歳": "z35", "59_1F_4歳": "z35", "59_1F_5歳": "z35",
        "31_": "share", "33_": "share", "12_": "share", "13_": "share", "56_": "share",
        "59_1F_ホール": "share", "59_1F_西吹き抜け": "share", "59_1F_路地": "share",
        "14_": "shoe", "15_": "shoe", "52_": "shoe",
        "59_1F_便所": "wc", "59_1F_多目的便所": "wc", "57_": "wc",             # 調理の更衣・便所・前室は一つの形なのでトイレの色（10-30 22:14）
        "59_1F_倉庫": "store", "36b_": "store",
        "59_1F_事務": "adult", "59_1F_医務": "adult", "59_1F_静養室": "adult",
        "35_": "adult", "36_": "adult",
        "32_": "kitchen"}
Z_BASE = ("12_", "13_", "56_", "59_1F_西吹き抜け", "59_1F_路地")       # 0〜2歳の教室の範囲では 0〜2歳の色（内廊下・西の窓際まで教室、ユーザー）
Z2 = []                                        # 西館の2階（会議・更衣・休憩・便所・ホール）。plan_items は1階だけ（高さ2 m より下）なので3dmから
for o in objs:
    if o["layer"].startswith(("41_", "42_", "43_", "43b_", "44_", "45_")):         # 43b 職員の更衣・ロッカーも（10-30 23:07）
        g_ = shape(o, "plan")
        if g_ is not None and g_.area > 1e-3:
            Z2.append((o["layer"], rot(g_)))


def _zg(pref, kinds=("mesh", "solid", "curve")):
    """外構・園庭のレイヤーの面（回した座標）"""
    gs_ = [g_ for g_ in (_poly_of(o) for o in objs if o["layer"].startswith(pref) and o["kind"] in kinds) if g_ is not None and g_.geom_type.endswith("Polygon")]
    return unary_union(gs_).buffer(0) if gs_ else None


_fill = lambda g_: unary_union([Polygon(p_.exterior) for p_ in getattr(g_, "geoms", [g_]) if p_.geom_type == "Polygon"]) if g_ is not None and not g_.is_empty else g_   # 穴を埋める
# 3dm（m）→ 回した座標
_M3 = np.array([[_INV[0, 0], _INV[0, 1], 0], [_INV[1, 0], _INV[1, 1], 0], [_INV[2, 0], _INV[2, 1], 1]])
_Mi = np.linalg.inv(_M3)
_G3R = lambda g_: affinity.affine_transform(g_, [_Mi[0, 0], _Mi[1, 0], _Mi[0, 1], _Mi[1, 1], _Mi[2, 0], _Mi[2, 1]])
_SAJ = json.load(open(os.path.join(ROOT, "data", "siteplan_approach.json"), encoding="utf-8"))
_AAJ = json.load(open(os.path.join(ROOT, "data", "approachA.json"), encoding="utf-8"))
_PSD = lambda s_, d_: _A_ + _tW * s_ - _nW * d_ if (_SITEP.contains(Point(_A_ + _tW * 5 - _nW * 3))) else _A_ + _tW * s_ + _nW * d_   # 道路の座標（s 公園の角から北へ、d 敷地の内へ）
_MINAMI = _zg("62_")
_STREAM_W = _zg("92_")
_CONT = [g_ for g_ in (_sh(o) for o in objs if o["layer"].startswith("91_")) if g_ is not None]
_zname = lambda ln_: re.split(r"[（(]", ln_.split("_")[-1])[0]
# 建物の足もと（部屋・壁・外縁側。穴を埋める）
_BLD = _fill(unary_union([g_.buffer(0.05) for ln_, k_, g_ in plan_items if g_ is not None and ln_[:1] in "12345" and g_.geom_type.endswith("Polygon")]).buffer(0.1).buffer(-0.1))
# セキュリティの線：塀・生垣・格子（70）・柵（60）・扉（66）と、南の生垣の線（siteplan_approach.json の security_line）。
# 3dm の塀は板一枚ずつの箱なので、太らせて縮め、途切れない一続きの帯に（10-30 23:07：セキュリティを切る線ははっきり）
_SECL = _G3R(LineString(_SAJ["security_line"]["pts"]))
_FEN = unary_union([g_.buffer(0.3) for g_ in (_sh(o) for o in objs if o["layer"].startswith(("70_", "60_", "66_"))) if g_ is not None]
                   + [_SECL.buffer(0.3)]).buffer(-0.15)
# 塀と建物で分けた外構のかたまり。道路（西・北）に開いたかたまりがセキュリティ外。キッチン前のひろば（78a と家具 75）は外（ユーザー）
# 北の塀の東の端（FENCE_T_END）と機械室の北西の面のあいだ（約2 m）は、塀が機械室の壁へ折れてつながる（3dm に無い）。最短の線で閉じる
from shapely.ops import nearest_points as _np_pts
_fp = [f_ for f_ in getattr(_FEN, "geoms", [_FEN]) if f_.area > 0.2]
_add = []
for i_, f_ in enumerate(_fp):                      # 木戸（扉の形の無い、閉じれば線になる開口）：塀どうしの 2.5 m 以下の隙間をつなぐ
    for g_ in _fp[i_ + 1:]:
        if 0.05 < f_.distance(g_) < 2.5:
            a_, b_ = _np_pts(f_, g_); _add.append(LineString([a_, b_]).buffer(0.15))
    if R35 is not None and 0.05 < f_.distance(R35) < 4.0:   # 塀の端と機械室の壁
        a_, b_ = _np_pts(f_, R35); _add.append(LineString([a_, b_]).buffer(0.15))
if R35 is not None:                                # 機械室と敷地の境（北・北東）のあいだ 1.5 m 以下
    for e_ in (LineString(R3(np.array([SITE_C["NW"], SITE_C["N"]]))), LineString(R3(np.array([SITE_C["N"], SITE_C["E"]])))):
        if R35.distance(e_) < 1.5:
            a_, b_ = _np_pts(R35, e_); _add.append(LineString([a_, b_]).buffer(0.15))
if _add:
    _FEN = unary_union([_FEN] + _add)
_SEAL = 0.7                                       # 塀と壁のあいだの細い隙間は閉じて数える（分けたあとで元の広さに戻す）
_EXT0 = _SITEP.difference(_BLD).difference(_FEN).difference(_PARK_R)          # 公園（小竹薮公園）は敷地の角にあるが公の場所なので別に
_EXT = _SITEP.difference(_BLD.buffer(_SEAL)).difference(_FEN.buffer(_SEAL)).difference(_PARK_R.buffer(_SEAL))
_OPEN = LineString(R3(np.array([SITE_C["SW"], SITE_C["NW"], SITE_C["N"]]))).difference(_FEN.buffer(0.4)).difference(_BLD.buffer(0.4))
_HIROBA = unary_union([g_ for g_ in [_zg("78a")] + [(_sh(o).convex_hull if _sh(o) is not None else None) for o in objs if o["layer"].startswith("75_")] if g_ is not None])
_GATEP = _G3R(Point(_SAJ["entrance"]["xy"]))
_GARDEN_ALL = unary_union([g_ for g_ in (GD["garden"], GD["shizu"], _MINAMI) if g_ is not None])
_o_, _a_, _i_ = [], [], []
for p_ in getattr(_EXT, "geoms", [_EXT]):
    if p_.area < 0.05:
        continue
    if p_.buffer(0.3).intersection(_OPEN).length > 1.0 and p_.intersection(_GARDEN_ALL).area < 5.0:   # 園庭とつながるかたまりは内（塀の描かれていない所から漏れても）
        _o_.append(p_)
    elif p_.distance(_GATEP) < 1.5:
        _a_.append(p_)                             # 公園の木戸の内（見送りの小径・ムベの下）：土足の色
    else:
        _i_.append(p_)
_cl = lambda L_: unary_union(L_).buffer(_SEAL + 0.05).intersection(_EXT0) if L_ else None
_OUT, _APPR, _IN = _cl(_o_), _cl(_a_), _cl(_i_)
_hb_ = _HIROBA.buffer(0.3).intersection(_SITEP).difference(_BLD) if not _HIROBA.is_empty else None
if _hb_ is not None:
    _OUT = _OUT.union(_hb_) if _OUT is not None else _hb_
    _APPR = _APPR.difference(_hb_) if _APPR is not None else None
    _IN = _IN.difference(_hb_) if _IN is not None else None
print("ゾーニング：セキュリティ外 %.0f m²・木戸の内 %.0f m²・内の外構 %.0f m²" % (_OUT.area if _OUT else 0, _APPR.area if _APPR else 0, _IN.area if _IN else 0))
_swS3 = _swS2.union(_G3R(Polygon(_SAJ["sidewalk"]["pts"])).intersection(_SITEP))
_sb_ = _AAJ["STAFF_BIKE"]["pocket"]                                       # 職員の駐輪（s0, s1, d0, d1）
_BIKE_ST = Polygon([_PSD(_sb_[0], _sb_[2]), _PSD(_sb_[1], _sb_[2]), _PSD(_sb_[1], _sb_[3]), _PSD(_sb_[0], _sb_[3])]).intersection(_SITEP)
_RESERVE = unary_union([_G3R(Polygon(p_)).buffer(0) for p_ in _SAJ.get("reserve", {}).get("polygons", []) if len(p_) > 2])
_PARKING = unary_union([g_ for g_ in (_Z, _RESERVE, _BIKE_ST) if g_ is not None and not g_.is_empty]).difference(_swS3)
_AMANIWA = rot(_gs(Polygon(gc.XS([tuple(p_) for p_ in GJ["AMANIWA"]["poly"]])).buffer(0))) if "poly" in GJ.get("AMANIWA", {}) else None
_WATER = unary_union([g_ for g_ in [GD["fountain"], _AMANIWA] + [(lambda q_: q_.centroid.buffer(np.sqrt(q_.area) / 2, 32) if q_ is not None else None)(_sh(o)) for o in objs if o["layer"].startswith("96_") and "噴水" in (o["name"] or "")] if g_ is not None and g_.geom_type.endswith("Polygon")])
_HUT_WC = unary_union([g_ for g_ in (_sh(o) for o in objs if o["layer"].startswith("93_") and (o["name"] or "").startswith("便所")) if g_ is not None and g_.geom_type.endswith("Polygon")])
_HUT_ST = unary_union([g_ for g_ in (_sh(o) for o in objs if o["layer"].startswith("93_") and (o["name"] or "").startswith("倉庫")) if g_ is not None and g_.geom_type.endswith("Polygon")])
# 0〜2歳の教室の範囲（本館の軸に沿った u の範囲。回す前の座標の x）
_unrot = lambda g_: affinity.rotate(g_, -ROT, origin=(0, 0))
_g02 = unary_union([g_ for ln_, k_, g_ in plan_items if ln_.startswith(("53_", "54_")) and k_ == "mesh"])
_ub = _unrot(_g02).bounds
_STRIP02 = rot(Polygon([(_ub[0] - 0.3, -200), (_ub[2], -200), (_ub[2], 200), (_ub[0] - 0.3, 200)]))
_u0_south = _ub[0] + 1.0
ZSC = 200
zw, zh = (WX1 - WX0) * 1000 / ZSC, (WY1 - WY0) * 1000 / ZSC
zox, zoy = M + 6, Y(55) - zh
_live(ax, 2, "zoning", "ゾーニング（文字）")
title(ax, M + 6, Y(51), "ゾーニング", f"1/{ZSC}　使う人ごとの色、セキュリティの内と外、園庭と一体（配置図と同じ向き、高野川を下に）")
_GRAYL = lambda c_: (lambda r_: matplotlib.colors.to_hex([0.55 + 0.45 * (0.299 * r_[0] + 0.587 * r_[1] + 0.114 * r_[2])] * 3))(matplotlib.colors.to_rgb(c_))   # 使っていない所は無彩色（明るさだけ残す）
# 0〜2歳の部屋の中のトイレ：3dm には部屋の形が無いので、更新係の平面図（drawings/sodachiya_plan_1-100.pdf）の「水まわり」の塗り（淡い水色）を紙→3dm→回した座標に戻して使う
_wc02 = []
try:
    _mp = json.load(open(os.path.join(DRW, "sodachiya_plan_1-100_views.json"), encoding="utf-8"))["views"][0]["model_to_paper"]
    _Ai = np.linalg.inv(np.array([[_mp["a"], _mp["b"]], [_mp["d"], _mp["e"]]]))
    _p2m = lambda q_: (_Ai @ (np.array(q_) - np.array([_mp["c"], _mp["f"]]))) / 1000.0
    for d_ in fitz.open(PLAN)[0].get_drawings():
        f_ = d_.get("fill")
        if not f_ or abs(f_[0] - 0.835) > 0.02 or abs(f_[1] - 0.922) > 0.02 or abs(f_[2] - 0.933) > 0.02:
            continue
        pts_ = []
        for it_ in d_["items"]:
            if it_[0] == "l":
                pts_ += [it_[1], it_[2]]
            elif it_[0] == "re":
                r_ = it_[1]; pts_ += [r_.tl, r_.tr, r_.br, r_.bl]
            elif it_[0] == "c":
                pts_ += [it_[1], it_[4]]
        if len(pts_) < 3:
            continue
        pg_ = _G3R(Polygon([_p2m((q_.x / MM, q_.y / MM)) for q_ in pts_]).buffer(0))
        if pg_.intersects(_g02) and pg_.intersection(_g02).area > 0.5 * pg_.area:
            _wc02.append(pg_)
except Exception as e_:
    print("0〜2歳のトイレ（平面図の水まわり）を読めない：", e_)
_WC02 = unary_union(_wc02) if _wc02 else None
print("0〜2歳のトイレ：%d か所" % len(_wc02))


def _zcol(ln_, g_=None):
    best = None
    for k_, z_ in ZONE.items():
        if ln_.startswith(k_) and (best is None or len(k_) > len(best[0])):
            best = (k_, z_)
    return best[1] if best else None


def _zone_paint(ax, ox, oy, sc, w_, h_, act=None, lw_room=0.12, lw_fen=0.3, contours=True):
    """ゾーニングの色で塗る（ゾーニング図と一日の帯で共通）。act(種類, レイヤー, 形) が True・False か、使う範囲の形を返す。
    act が無ければ全部に色。使っていない所は無彩色。種類：site・out・in_ext・g35・gboth・g02・parking・water・hut・bld・room"""
    xf_ = xform(ox, oy, sc, WX0, WY0)
    rp_ = clip_rect(ax, ox, oy, w_, h_)
    s0_, l0_ = len(ax.patches), len(ax.lines)

    def P(g_, col_, kind_, ln_="", z_=1.0, ec_="none", lw_=0.0):
        if g_ is None or g_.is_empty:
            return
        a_ = True if act is None else act(kind_, ln_, g_)
        if a_ is True or a_ is False:
            draw_shape(ax, g_, xf_, fc=col_ if a_ else _GRAYL(col_), ec=ec_, lw=lw_, z=z_)
        else:                                       # 一部だけ使う：使う所は色、ほかは無彩色
            draw_shape(ax, g_.intersection(a_), xf_, fc=col_, ec=ec_, lw=lw_, z=z_)
            draw_shape(ax, g_.difference(a_), xf_, fc=_GRAYL(col_), ec=ec_, lw=lw_, z=z_)
    draw_shape(ax, _ROADS_R, xf_, fc="#E6E6E4", ec="none", z=0.3)
    P(_SITEP, Z_COL["in_ext"], "site", z_=0.35)        # 地（どのかたまりにも入らない塀ぎわの細い所はセキュリティ内の色）
    P(_PARK_R, Z_COL["park"], "out", z_=0.37)
    P(_OUT, Z_COL["out"], "out", z_=0.4)
    P(_IN, Z_COL["in_ext"], "in_ext", z_=0.41)
    P(_APPR, Z_COL["shoe"], "approach", z_=0.42)
    P(_fill(GD["garden"]), Z_COL["g35"], "g35", z_=0.5)
    P(GD["shizu"], Z_COL["gboth"], "gboth", z_=0.55)
    P(_fill(_MINAMI) if _MINAMI is not None else None, Z_COL["g02"], "g02", z_=0.55)
    P(_PARKING, Z_COL["park_car"], "parking", z_=0.58)
    if contours:
        for g_ in _CONT:
            draw_shape(ax, g_, xf_, ec=_HSB(F_H, 0.55, 0.45), lw=0.12, z=0.6)
        draw_shape(ax, GD["mound"], xf_, fc="none", ec=_HSB(F_H, 0.6, 0.38), lw=0.3, z=0.62)
    P(_STREAM_W, "#9ECBE6", "water", z_=0.65)
    P(_WATER, Z_COL["water"], "water", z_=0.67)
    P(GD["compost"], "#CDBFAA", "hut", z_=0.8)
    P(_HUT_WC, Z_COL["wc"], "hut", z_=0.81)
    P(_HUT_ST, Z_COL["store"], "hut", z_=0.81)
    P(_BLD, C_SHARE, "bld", z_=0.9)
    its_ = sorted([it for it in plan_items if it[2] is not None and it[2].geom_type.endswith("Polygon") and _zcol(it[0])],
                  key=lambda it: 0 if it[0].startswith("12_") else (1 if it[0].startswith(Z_BASE) else 2))
    for ln_, k_, g_ in its_:
        z_ = _zcol(ln_)
        g_ = _fill(g_)
        lay_ = 1.0 if ln_.startswith("12_") else (1.01 if ln_.startswith(Z_BASE) else (1.03 if z_ in ("wc", "store") else 1.02))
        e_ = ("none", 0) if ln_.startswith(("12_",) + Z_BASE) else ("#9A9A9A", lw_room)
        if ln_.startswith(Z_BASE):
            P(g_.difference(_STRIP02), Z_COL[z_], "room", ln_, lay_)
            P(g_.intersection(_STRIP02), Z_COL["z02"], "room", ln_, lay_)
        elif ln_.startswith("14_") and _unrot(g_).centroid.x < _u0_south:
            P(g_, Z_COL["z02"], "room", ln_, lay_, *e_)
        else:
            P(g_, Z_COL[z_], "room", ln_, lay_, *e_)
    P(_WC02, Z_COL["wc"], "room", "53_便所", 1.04, "#9A9A9A", lw_room)
    for a_ in ax.patches[s0_:]:
        a_.set_clip_path(rp_)
    for a_ in ax.lines[l0_:]:
        a_.set_clip_path(rp_)
    rs_ = dict(ROOM)
    ROOM.clear(); ROOM.update({k_: "none" for k_ in ZONE})     # 壁・建具・屋根の破線だけ draw_plan で（部屋の塗りは上で、ここは輪郭だけ）
    draw_plan(ax, ox, oy, sc, WX0, WY0, w_, h_, thin=True, outdoor=False)
    ROOM.clear(); ROOM.update(rs_)
    l2_ = len(ax.lines)
    draw_shape(ax, _FEN.intersection(_WIN), xf_, fc="#1E1E1E", ec="#1E1E1E", lw=lw_fen, z=6)   # セキュリティの線（塀・柵・木戸・南の生垣）
    if R35 is not None:                              # 機械室の外の壁（draw_plan では部屋の扱いなので線が出ない）
        draw_shape(ax, R35.exterior if R35.geom_type == "Polygon" else R35.boundary, xf_, ec="#333333", lw=0.5 * lw_fen / 0.3, z=5.5)
    for a_ in ax.patches[s0_:] + ax.lines[l2_:]:
        a_.set_clip_path(rp_)
    return xf_


# ---- ゾーニングは白地図（10-31 00:10、ユーザー）：線だけにして木田さんが Illustrator で彩色する。
# レイヤー「ゾーニング　境界」：ゾーン（部屋・庭・外構の区分）ごとの閉じたパス（塗りなし、細い線、名前＝ゾーンの名前。隣とは境界を共有して隙間なく）と、
# セキュリティの線（塀・柵・木戸・南の生垣、太い帯の閉じたパス）。レイヤー「ゾーニング　上の線」：等高線・築山・車室・駐輪・バンプ。
# 色を付けた版は参考として sozai/19_ゾーニング_彩色（参考）.pdf（.ai には貼らない）
zxf = xform(zox, zoy, ZSC, WX0, WY0)
_z2b = unary_union([g_ for _, g_ in Z2]).bounds if Z2 else (0, 0, 1, 1)
z2w, z2h = (_z2b[2] - _z2b[0] + 2) * 1000 / ZSC, (_z2b[3] - _z2b[1] + 2) * 1000 / ZSC
_r20 = zxf(np.array(R20.envelope.exterior.coords)) if R20 is not None else None   # 1階の西館（屋根の範囲）の紙の上の位置
z2ox = max(zox + 2, _r20[:, 0].min() - z2w - 8) if _r20 is not None else zox + 2         # 西館のすぐ左（西の道の上）に寄せる（10-30 23:07）
z2oy = min(Y(55) - 6 - z2h, _r20[:, 1].max() - z2h - 6) if _r20 is not None else Y(55) - 6 - z2h
z2xf = xform(z2ox, z2oy, ZSC, _z2b[0] - 1, _z2b[1] - 1)
# 参考の彩色版（別の図）
_figZ = plt.figure(figsize=(zw / 25.4, zh / 25.4))
_axZ = _figZ.add_axes([0, 0, 1, 1]); _axZ.set_xlim(zox, zox + zw); _axZ.set_ylim(zoy, zoy + zh); _axZ.axis("off")
_zone_paint(_axZ, zox, zoy, ZSC, zw, zh)
_axZ.add_patch(Rectangle((z2ox - 1, z2oy - 1), z2w + 2, z2h + 7, fc="white", ec="#888888", lw=0.25, zorder=9))
for ln_, g_ in Z2:
    draw_shape(_axZ, _fill(g_), z2xf, fc=Z_COL["wc"] if ln_.startswith("42_") else Z_COL["adult"], ec="#9A9A9A", lw=0.12, z=9.5)
_figZ.savefig(os.path.join(HERE, "sozai", "19_ゾーニング_彩色（参考）.pdf"))
plt.close(_figZ)
# ゾーンの区分（回した座標、上の物が先）：重ならないよう、先に取った所を引いて境界を共有させる
_ZL = []


def _za(name_, g_):
    if g_ is not None and not g_.is_empty:
        _ZL.append((name_, g_))


_rooms = {}
for ln_, k_, g_ in plan_items:
    z_ = _zcol(ln_)
    if z_ and g_ is not None and g_.geom_type.endswith("Polygon"):
        pr_ = 3 if z_ in ("wc", "store") else (0 if ln_.startswith("12_") else (1 if ln_.startswith(Z_BASE) else 2))
        _rooms.setdefault((pr_, ln_), []).append(_fill(g_))
_za("便所（0〜2歳）", _WC02)
for (pr_, ln_), gs_ in sorted(_rooms.items(), key=lambda kv: -kv[0][0]):
    u_ = unary_union(gs_)
    nm_ = "本館の床（廊下ほか）" if ln_.startswith("12_") else _zname(ln_)
    if ln_.startswith(Z_BASE):
        _za(nm_ + "（0〜2歳の範囲）", u_.intersection(_STRIP02))
        _za(nm_, u_.difference(_STRIP02))
    elif ln_.startswith("14_"):
        _s_ = [p_ for p_ in getattr(u_, "geoms", [u_]) if _unrot(p_).centroid.x < _u0_south]
        _za("外縁側（0・1歳の南）", unary_union(_s_) if _s_ else None)
        _za(nm_, u_.difference(unary_union(_s_)) if _s_ else u_)
    else:
        _za(nm_, u_)
_za("建物（壁・すき間）", _BLD)
_za("小屋の便所", _HUT_WC); _za("小屋の倉庫", _HUT_ST); _za("コンポスト", GD["compost"])
_za("水遊び場・雨庭", _WATER); _za("小川", _STREAM_W)
_za("みなみのさんかく", _fill(_MINAMI) if _MINAMI is not None else None); _za("しずかのもり", GD["shizu"]); _za("だいさんかく", _fill(GD["garden"]))
_za("職員の駐輪場", _BIKE_ST); _za("駐車場", _PARKING)
_za("歩道", _swS3); _za("ひろば", _hb_)
_za("木戸の内（小径・ムベの下）", _APPR); _za("セキュリティ内の外構", _IN); _za("セキュリティ外の外構", _OUT)
_za("公園", _PARK_R); _za("敷地（そのほか）", _SITEP); _za("道路", _ROADS_R); _za("周り", _WIN)
_taken = None
_ZP = []                                          # (名前, 形)
for nm_, g_ in _ZL:
    g_ = g_.buffer(0).intersection(_WIN)
    if _taken is not None:
        g_ = g_.difference(_taken)
    if g_.area > 0.02:
        _ZP.append((nm_, g_))
    _taken = g_ if _taken is None else _taken.union(g_)


def _rings(g_, xf_):
    """形 → パス（穴のある形は rings、無ければ pts）。紙の mm（下原点）"""
    out_ = []
    for p_ in getattr(g_, "geoms", [g_]):
        if p_.geom_type != "Polygon" or p_.area < 0.02:
            continue
        p_ = p_.simplify(0.01, preserve_topology=True)
        ex_ = [list(map(float, q_)) for q_ in xf_(np.array(p_.exterior.coords))[:-1]]
        if p_.interiors:
            out_.append(dict(rings=[ex_] + [[list(map(float, q_)) for q_ in xf_(np.array(r_.coords))[:-1]] for r_ in p_.interiors]))
        else:
            out_.append(dict(pts=ex_, closed=True))
    return out_


G_ZB = ("zoning_border", "ゾーニング　境界")
G_ZU = ("zoning_upper", "ゾーニング　上の線")
_nz, _nzp = 0, 0


def _zpart(id_, name_, paths_, layer_, group_, fill_=None, stroke_="#555555", lw_=0.2):
    global _nz, _nzp
    for q_ in paths_:
        q_.update(fill=fill_, stroke=stroke_, lw=lw_, name=name_)
        rs_ = q_.get("rings") or [q_["pts"]]
        for r_ in rs_:
            P_ = np.array(r_)
            ax.add_patch(MPoly(P_, closed=bool(q_.get("closed", True)) or "rings" in q_, fc=fill_ or "none", ec=stroke_ if lw_ else "none",
                               lw=lw_ * 0.35 if lw_ else 0, zorder=7, gid="aipart")) if (q_.get("closed") or "rings" in q_) else \
                ax.plot(P_[:, 0], P_[:, 1], color=stroke_, lw=lw_ * 0.35, zorder=7, gid="aipart")
    if paths_:
        _airec(fig, kind="lines", id=id_, name=name_, paths=paths_, layer=layer_, group=group_[0], group_name=group_[1], keep_fill=True)
        _nz += 1; _nzp += len(paths_)


_zs_ = lambda s_: re.sub(r"[\s　/\\|:（）()、。・]+", "", s_)[:14]
for nm_, g_ in _ZP:
    _zpart("zone." + _zs_(nm_), nm_, _rings(g_, zxf), "ゾーニング　境界", G_ZB)
_FENW = _FEN.intersection(_WIN)
_zpart("zone.セキュリティの線", "セキュリティの線（塀・柵・木戸・南の生垣）", _rings(_FENW, zxf), "ゾーニング　境界", G_ZB, fill_="#1E1E1E", stroke_=None, lw_=0)
# 2階（西館）の差し込み：枠と部屋（同じ縮尺）
_z2bg = Polygon([(_z2b[0] - 1, _z2b[1] - 1), (_z2b[2] + 1, _z2b[1] - 1), (_z2b[2] + 1, _z2b[3] + 1 + 7 * ZSC / 1000), (_z2b[0] - 1, _z2b[3] + 1 + 7 * ZSC / 1000)])
_t2 = None
for ln_, g_ in sorted(Z2, key=lambda t_: 0 if t_[0].startswith("42_") else 1):
    g_ = _fill(g_)
    if _t2 is not None:
        g_ = g_.difference(_t2)
    _zpart("zone2." + _zs_(_zname(ln_)), "2階　" + _zname(ln_), _rings(g_, z2xf), "ゾーニング　境界", G_ZB)
    _t2 = g_ if _t2 is None else _t2.union(g_)
if _t2 is not None:
    _zpart("zone2.ホールほか", "2階　ホール・すき間", _rings(_fill(unary_union([g_.buffer(0.08) for _, g_ in Z2])).difference(_t2), z2xf), "ゾーニング　境界", G_ZB)
    _zpart("zone2.枠", "2階（西館）の枠", _rings(_z2bg.difference(_fill(unary_union([g_.buffer(0.08) for _, g_ in Z2]))), z2xf), "ゾーニング　境界", G_ZB, fill_="#FFFFFF")
# 上の線
_up = lambda gs_: [dict(pts=[list(map(float, q_)) for q_ in zxf(np.array(l_.coords))], closed=False) for g0_ in gs_ for l_ in
                   (lambda g1_: [b_ for b_ in getattr(g1_, "geoms", [g1_]) if b_.geom_type.endswith("LineString") and len(b_.coords) > 1])(
                       (g0_.boundary if g0_.geom_type.endswith("Polygon") else g0_).intersection(_WIN))]
_zpart("zup.等高線", "等高線 0.2 m", _up(_CONT), "ゾーニング　上の線", G_ZU, stroke_="#8A8A8A", lw_=0.15)
_zpart("zup.築山", "築山の輪郭", _up([GD["mound"]]), "ゾーニング　上の線", G_ZU, stroke_="#666666", lw_=0.3)
_zpart("zup.車室", "車室・駐輪の区画・バンプ", _up([g_ for g_ in (_sh(o) for o in objs if o["layer"].startswith(("74_", "74w"))) if g_ is not None]),
       "ゾーニング　上の線", G_ZU, stroke_="#666666", lw_=0.15)
print("ゾーニング（白地図）：区分 %d、部品 %d、閉じたパス・線 %d" % (len(_ZP), _nz, _nzp))
_lab = {}
for ln_, k_, g_ in plan_items:                 # 部屋の名前（小さく）
    if k_ == "mesh" and _zcol(ln_, g_) and not ln_.startswith(("12_", "59_1F_倉庫")):
        _lab.setdefault(ln_, []).append(g_)
for ln_, gs_ in _lab.items():
    u_ = unary_union(gs_)
    if u_.area < 3.0:
        continue
    q_ = zxf(np.array([u_.representative_point().coords[0]]))[0]
    T(ax, q_[0], q_[1], _zname(ln_), 1.8, "#333333", ha="center", va="center")
for nm_, g_ in (("だいさんかく", GD["north"]), ("しずかのもり", GD["shizu"]), ("みなみのさんかく", _MINAMI), ("公園", _PARK_R), ("駐車場", _Z)):
    if g_ is not None and not g_.is_empty:
        q_ = zxf(np.array([g_.representative_point().coords[0]]))[0]
        T(ax, q_[0], q_[1], nm_, 2.4, "#3F3528" if nm_ != "駐車場" else "#333333", bold=True, ha="center", va="center")
T(ax, z2ox + 1, z2oy + z2h + 2, "2階（西館）", 2.4, bold=True, zorder=10)
for ln_, g_ in Z2:
    q_ = z2xf(np.array([g_.representative_point().coords[0]]))[0]
    T(ax, q_[0], q_[1], _zname(ln_), 1.8, "#333333", ha="center", va="center", zorder=10)
# 凡例：色の見本は外し、項目の名前と塗りなしの四角（木田さんが色を付ける）
_ly = zoy - 6
for row_ in (Z_LEG1, Z_LEG2, Z_LEG3):
    _lx = M + 6
    for k_, nm_ in row_:
        ax.add_patch(Rectangle((_lx, _ly - 1.2), 6, 4, fc="none", ec="#777777", lw=0.2, gid="aipart"))
        _airec(fig, kind="box", id=f"zleg.{k_}", name="凡例の四角：" + nm_, x=_lx, y=_ly - 1.2, w=6, h=4, fill=None, stroke="#777777", lw=0.2, dash=None,
               group="zoning", group_name="ゾーニング（文字）")
        T(ax, _lx + 7.5, _ly, nm_, 2.5)
        _lx += 7.5 + fitz.Font(fontfile=FONT).text_length(nm_, 2.5 / 0.72) + 5
    _ly -= 6
ax.plot([M + 6, M + 13], [_ly + 0.6, _ly + 0.6], color="#2B2B2B", lw=1.1)
T(ax, M + 15, _ly, "塀・柵・木戸・生垣（セキュリティの線）", 2.5)
ax.plot([M + 105, M + 111], [_ly + 0.6, _ly + 0.6], color="#8A8A8A", lw=0.4)
T(ax, M + 113, _ly, "等高線 0.2 m（園庭の地形・築山）", 2.5)
_ly += 7                                         # 樹木図の題は _ly − 14
print("ゾーニングの色：", {k_: Z_COL[k_] for k_ in ("out", "in_ext", "shoe", "g02", "gboth", "g35")})

# ---- 一日の帯（10-30 22:44、ユーザー：4コマ。朝（と帰り）／日中／食事／延長保育。動線の線は描かない。使われている所だけゾーニングの色、ほかは無彩色）
_u_ama = _unrot(unary_union([g_ for ln_, k_, g_ in plan_items if ln_.startswith("15_")])).centroid.x    # あまのがわの位置（本館の軸の u）
_SOUTH_AMA = rot(Polygon([(-200, -200), (_u_ama, -200), (_u_ama, 200), (-200, 200)]))
_NORTH_AMA = rot(Polygon([(_u_ama, -200), (300, -200), (300, 200), (_u_ama, 200)]))


def _act_morning(kind_, ln_, g_):
    if kind_ in ("out", "site", "approach"):
        return True                                  # 公園の木戸・ムベのアーチの下・ひろば・小径
    if kind_ == "room":
        if ln_.startswith(("52_", "15_", "57_", "59_1F_事務（スパン")):   # 受け取り土間・あまのがわ・勝手口と検収・おはようの窓口
            return True
        if ln_.startswith("14_"):                    # 外縁側（あまのがわから北の外廊下も）
            return True
    return False


def _act_day(kind_, ln_, g_):
    return kind_ in ("room", "bld", "g35", "gboth", "g02", "water", "hut")


def _act_late(kind_, ln_, g_):
    if kind_ == "room":
        if ln_.startswith(("54_", "13_", "15_")):    # 2歳の部屋・内縁側・あまのがわ
            return True
        if ln_.startswith("59_1F_西吹き抜け"):       # 西の吹き抜けのうち、あまのがわより南
            return _SOUTH_AMA
    return False


frames_ = [
    ("朝（と帰り）", _act_morning, "公園の木戸からムベのアーチの下へ。0・1歳は受け取り土間で手渡し、ひろばで見送り、おはようの窓口で挨拶。食材は勝手口で検収。帰りはこの逆"),
    ("日中", _act_day, "建物の中のすべてと、だいさんかく・しずかのもり・みなみのさんかくで過ごす"),
    ("食事", _act_day, "保育室の食卓でクラスごとに食べる。キッチンから配膳口を通って運ぶ"),
    ("延長保育", _act_late, "2歳の部屋で迎えを待つ。内縁側・あまのがわ・西の吹き抜けの南だけを使い、ほかは閉じる"),
]
nf = len(frames_)
fw = (_RW - (nf - 1) * 5) / nf
txt_h = 3 * 3.3 + 3
ksc = next(s_ for s_ in (500, 600, 700, 800, 1000)
           if (WX1 - WX0) * 1000 / s_ <= fw - 4 and (WY1 - WY0) * 1000 / s_ <= fh - 10 - txt_h)
for i, (h1, act_, s1_) in enumerate(frames_):
    _live(ax, 2, f"day{i + 1}", f"一日の帯　{h1}（文字）")
    fx = _RX + i * (fw + 5)
    ax.add_patch(Rectangle((fx, fy), fw, fh, fc="none", ec="#BBBBBB", lw=0.3))
    sozai(f"{6 + i:02d}", f"一日の帯　{h1}（小さな配置1/{ksc}）", 2, fx, fy, fw, fh)
    T(ax, fx + 3, fy + fh - 6, h1, 3.4, bold=True)
    kw_, kh_ = (WX1 - WX0) * 1000 / ksc, (WY1 - WY0) * 1000 / ksc
    _zone_paint(ax, fx + (fw - kw_) / 2, fy + fh - 9 - kh_, ksc, kw_, kh_, act=act_, lw_room=0.06, lw_fen=0.25, contours=False)
    for k_, ln_ in enumerate(jwrap(s1_, (fw - 6) / (2.3 / 0.72))[:3]):
        T(ax, fx + 3, fy + fh - 9 - kh_ - 4.5 - k_ * 3.3, ln_, 2.3)
dimnote(ax, _RX, Y(45) + 2, f"一日の帯：1/{ksc}の小さな配置（西の道路から高野川まで）。その時間に使う所だけゾーニングの色、ほかは灰。動線は .ai で")

_live(ax, 2, "trees", "樹木（文字）")
# ---- 樹木図 1/400（10-30 18:05 作り直し：常緑と落葉の2色で塗り、香り・花・紅葉・実・ちくちくを小さな印で。園児が目にする木を全部）
# 入れる物：園庭の木（94c、garden.json の TREES。柳の家も）、読書の庭のモミジ（67c）、ムベのアーチ（73c）、外構の木（siteplan_approach.json の trees＝77）、
# 緑の目隠しのムベ（79c）、刈り込み・植え込み（77c の低い物）、生垣（70h・97h、線で）。木の性格は一般の植物の知識（確かでない物は付けない）
TSC = 400
tw_, th_ = (WX1 - WX0) * 1000 / TSC, (WY1 - WY0) * 1000 / TSC
_tt = _ly - 14                                   # 題の基準線（凡例の下）
tox, toy = M + 6, _tt - TITLE_GAP - th_
title(ax, M + 6, _tt, "樹木", f"1/{TSC}　園児が目にする木。塗りは常緑・落葉、印は香り・花・紅葉・実・ちくちく")
txf = xform(tox, toy, TSC, WX0, WY0)
_trp = clip_rect(ax, tox, toy, tw_, th_)
_ts, _tls = len(ax.patches), len(ax.lines)
draw_shape(ax, _ROADS_R, txf, fc="#EEEEEC", ec="none", z=0.3)
draw_shape(ax, _PARK_R, txf, fc="none", ec="#C9D3BE", lw=0.15, z=0.35)
draw_shape(ax, _SITEP, txf, fc="none", ec="#999999", lw=0.2, z=0.36, ls=(0, (6, 1.5, 1, 1.5)))
draw_shape(ax, roofs_plan, txf, fc="#F2F2F2", ec="#AAAAAA", lw=0.2, z=0.5)
draw_shape(ax, GD["garden"], txf, fc="none", ec="#C8D2BC", lw=0.2, z=0.5)
draw_shape(ax, GD["stream"], txf, ec="#8DB8D8", lw=0.5, z=0.55)
# 木の性格（E＝常緑、D＝落葉。印：香＝香り、花、紅＝紅葉・黄葉、実、痛＝とげ・葉がちくちく）
TRAIT = {"ウメ": ("D", "香花実"), "ロウバイ": ("D", "香花"), "クロモジ": ("D", "香紅"), "キンモクセイ": ("E", "香花"), "コブシ": ("D", "香花"),
         "ヒイラギ": ("E", "香花痛"), "ホオノキ": ("D", "香花"), "アオダモ": ("D", "花"), "サルスベリ": ("D", "花紅"), "ハナモモ": ("D", "花"),
         "ヤマザクラ": ("D", "花紅"), "ヤマボウシ": ("D", "花実紅"), "イロハモミジ": ("D", "紅"), "オオモミジ": ("D", "紅"), "モミジ": ("D", "紅"),
         "ナツハゼ": ("D", "実紅"), "カキ": ("D", "実紅"), "クリ": ("D", "実痛"), "クワ": ("D", "実"), "ジューンベリー": ("D", "花実紅"),
         "ユズ": ("E", "香実痛"), "シラカシ": ("E", "実"), "ソヨゴ": ("E", "実"), "ナンテン": ("E", "実紅"), "ホウライチク": ("E", ""),
         "エノキ": ("D", "実"), "カシワ": ("D", "実"), "カツラ": ("D", "香紅"), "クヌギ": ("D", "実"), "ケヤキ": ("D", "紅"),
         "コナラ": ("D", "実紅"), "ムクノキ": ("D", "実"), "ヤナギ": ("D", ""), "ムベ": ("E", "香花実"),
         "刈り込み・植え込み": ("E", ""), "入江の木": ("D", "")}
# 印は色相と形をはっきり変える（ユーザー 10-30 22:44：赤系ばかりで分かりにくい）。塗りの緑と紛れない色
BADGE = [("香", "#7A4FC0", "香り", "o"), ("花", "#E8B400", "花", "D"), ("紅", "#E0621B", "紅葉・黄葉", "^"), ("実", "#2B6CD6", "実", "s"), ("痛", "#111111", "ちくちく（とげ・痛い葉）", "X")]
C_EVER, C_DECI, C_UNK = "#4F8A5B", "#B9D98F", "#CFCFCF"
TRAIT.update({"ギンモクセイ": ("E", "香"), "クスノキ": ("E", "香"), "ベニシダレ": ("D", "紅")})     # クスノキは葉の香り（樟脳）
# 香りの木は（この中では）花の香りなので、香りと花が重なる木は香りの印だけ（ユーザー 10-30 22:44）
_tr = lambda sp_: (lambda t_: (t_[0], t_[1].replace("花", "") if "香" in t_[1] else t_[1]))(TRAIT.get(sp_.split("（")[0], (None, "")))
# 図の上での読み替え（データ（garden.json など）はほかの係の物なので書き換えない。ユーザー 10-30 22:44）
# モミジの種類（ユーザー 10-30 22:53）：園庭のモミジ＝イロハモミジ（garden.json のオオモミジも）、入江の木＝オオモミジ、読書の庭（67）＝ベニシダレ（枝垂れの細葉）
SP_READ = {"モミジ（読書の庭）": "ベニシダレ", "オオモミジ": "イロハモミジ", "入江の木": "オオモミジ",
           "ムベ（アーチの棚）": "ムベ", "ムベ（緑の目隠し）": "ムベ",
           "刈り込み・植え込み（キンモクセイ・ギンモクセイ・苔など）": "ギンモクセイ"}
KUSU_AT = (46.68, 1.77)                          # クスノキに読み替える木：garden.json の TREES のシラカシ（北東の境の並び、キンモクセイとイロハモミジのあいだ）
_trees = []                                      # (樹種, 回した座標の点, 形)
for o in objs:
    ln_ = o["layer"]
    if not ln_.startswith(("94c", "67c", "73c", "79c")):
        continue
    g_ = _sh(o)
    if g_ is None:
        continue
    if ln_.startswith("94c"):
        nm_ = (o["name"] or "木")
        sp_ = "ヤナギ（柳の家）" if nm_.startswith("柳の家") or "柳" in nm_.split("（")[0] else nm_.split("（")[0]
    elif ln_.startswith("67c"):
        sp_ = "モミジ（読書の庭）"
    elif ln_.startswith("73c"):
        sp_ = "ムベ（アーチの棚）"
    else:
        if o["V"][:, 2].max() < 0.5:                 # 低い物はハーブの帯（木ではない）
            continue
        sp_ = "ムベ（緑の目隠し）"
        if g_.geom_type.endswith("LineString"):     # 柵ぎわの帯（開いた線の押し出し）は幅をつける
            g_ = g_.buffer(0.45, cap_style=2)
    for gg_ in (g_.geoms if hasattr(g_, "geoms") else [g_]):
        if gg_.area > 0.05:
            if ln_.startswith(("94c", "67c")) and o["kind"] == "solid":     # 樹冠の箱（外形は四角になる）は丸に
                gg_ = gg_.centroid.buffer(np.sqrt(gg_.area) / 2, 24)
            _trees.append((sp_, np.array(gg_.representative_point().coords[0]), gg_))
for o in objs:                                   # 刈り込み・植え込み（77c の低い物、キンモクセイ・ギンモクセイなど）
    if o["layer"].startswith("77c") and o["kind"] != "mesh" and o["V"][:, 2].max() < 1.5:
        g_ = _sh(o)
        if g_ is not None and g_.area > 0.5:
            _trees.append(("刈り込み・植え込み（キンモクセイ・ギンモクセイ・苔など）", np.array(g_.representative_point().coords[0]), g_))
try:                                             # 外構の木（77、アプローチ係の siteplan_approach.json の trees）。読書の庭のモミジは 67c で入れた
    for t_ in json.load(open(os.path.join(ROOT, "data", "siteplan_approach.json"), encoding="utf-8")).get("trees", []):
        if t_["name"] == "モミジ":
            continue
        p_ = R3(np.array([t_["xy"]]))[0]
        sp_ = t_["name"].replace("（落葉樹）", "").replace("（現況）", "（現況、樹種不明）")
        _trees.append((sp_, p_, Point(p_).buffer(t_.get("r", 1.0), 24)))
except Exception as e_:
    print("外構の木：", e_)
_trees = [(SP_READ.get(sp_, sp_), p_, g_) for sp_, p_, g_ in _trees]
_kp = rot(_gs(Point(gc.XS([KUSU_AT])[0])))
_ki = min((i_ for i_, t_ in enumerate(_trees) if t_[0] == "シラカシ"), key=lambda i_: _trees[i_][2].centroid.distance(_kp), default=None)
if _ki is not None:
    _trees[_ki] = ("クスノキ",) + tuple(_trees[_ki][1:])
    print("クスノキ：シラカシ（%.1f m 先の木）を読み替え" % _trees[_ki][2].centroid.distance(_kp))
_HEDGE = [g_ for g_ in (_sh(o) for o in objs if o["layer"].startswith(("70h", "97h"))) if g_ is not None]
for sp_, p_, g_ in sorted(_trees, key=lambda t_: -t_[2].area):
    ev_ = _tr(sp_)[0]
    draw_shape(ax, g_, txf, fc=C_EVER if ev_ == "E" else (C_DECI if ev_ == "D" else C_UNK), ec="#5E6E52", lw=0.1, z=1)
for g_ in _HEDGE:                                 # 生垣は線で
    draw_shape(ax, g_.convex_hull.exterior if g_.geom_type == "Polygon" else g_, txf, ec="#3E6B3A", lw=0.9, z=1.2)
for a_ in ax.patches[_ts:]:
    a_.set_clip_path(_trp)
for a_ in ax.lines[_tls:]:
    a_.set_clip_path(_trp)
_order = sorted({sp_ for sp_, _, _ in _trees if _tr(sp_)[0] is not None}, key=lambda sp_: ({"E": 0, "D": 1}.get(_tr(sp_)[0], 2), -len(_tr(sp_)[1]), sp_))
_num = {sp_: i_ + 1 for i_, sp_ in enumerate(_order)}
_BR = 0.75                                       # 印の丸の半径（mm）


def _badges(x_, y_, tr_, z=3):
    for k_, (b_, c_, _, m_) in enumerate([b for b in BADGE if b[0] in tr_]):
        ax.plot([x_ + k_ * 1.7], [y_], marker=m_, ms=4.0 if m_ != "X" else 4.4, mfc=c_, mec="white", mew=0.25, ls="none", zorder=z)


for sp_, p_, g_ in _trees:
    if (g_.area < 0.6 and sp_ != "ギンモクセイ") or _tr(sp_)[0] is None:   # 樹種不明は灰で塗るだけ（番号も凡例も無し）
        continue
    q_ = txf(np.array([p_]))[0]
    if sp_ in ("ギンモクセイ", "ムベ"):
        q_ = txf(np.array([g_.representative_point().coords[0]]))[0]
    T(ax, q_[0], q_[1] + 0.6, str(_num[sp_]), 1.5, "white" if _tr(sp_)[0] == "E" else "#222222", ha="center", va="baseline")
    tr_ = _tr(sp_)[1]
    _badges(q_[0] - (len([b for b in BADGE if b[0] in tr_]) - 1) * 0.85, q_[1] - 0.6, tr_)
sozai("22", f"樹木（1/{TSC}）", 2, tox, toy, tw_, th_)
# 凡例：常緑・落葉、印、樹種の表（常緑→落葉、印の多い順）
_cnt = {}
for sp_, _, _ in _trees:
    _cnt[sp_] = _cnt.get(sp_, 0) + 1
_lx = tox + tw_ + 5
_col_w = (M + 6 + 340 - _lx) / 2
_yy = _tt - 1
for c_, nm_ in ((C_EVER, "常緑"), (C_DECI, "落葉")):
    ax.add_patch(Rectangle((_lx, _yy - 1.0), 4, 3, fc=c_, ec="#777777", lw=0.15))
    T(ax, _lx + 5, _yy, nm_, 2.3)
    _yy -= 3.6
ax.plot([_lx, _lx + 4], [_yy + 0.5, _yy + 0.5], color="#3E6B3A", lw=0.9)
T(ax, _lx + 5, _yy, "生垣（線）", 2.3)
_yy -= 3.6
for b_, c_, nm_, m_ in BADGE:
    ax.plot([_lx + 2], [_yy + 0.6], marker=m_, ms=4.0, mfc=c_, mec="white", mew=0.25, ls="none")
    T(ax, _lx + 5, _yy, nm_, 2.3)
    _yy -= 3.4
_yy -= 1.5
_y_list = _yy
_ci = 0
_n_per = -(-len(_order) // 2)
for i_, sp_ in enumerate(_order):
    if i_ == _n_per:
        _ci, _yy = 1, _y_list
    x_ = _lx + _ci * _col_w
    ev_, tr_ = _tr(sp_)
    ax.add_patch(Rectangle((x_, _yy - 0.6), 2.4, 2.2, fc=C_EVER if ev_ == "E" else (C_DECI if ev_ == "D" else C_UNK), ec="#777777", lw=0.1))
    s_ = f"{_num[sp_]}　{sp_}" + (f"（{_cnt[sp_]}）" if _cnt[sp_] > 1 else "")
    T(ax, x_ + 3.4, _yy, s_, 2.1)
    _badges(x_ + 3.4 + fitz.Font(fontfile=FONT).text_length(s_, 2.1 / 0.72) + 1.6, _yy + 0.7, tr_)
    _yy -= 3.1
print("樹木図：1/%d、%d 本・%d 種（生垣 %d）" % (TSC, len(_trees), len(_order), len(_HEDGE)))
print("樹木図の樹種：", "、".join(_order))
_live(None, 2, None, None)
plan_items[:] = _SAVE[0]
GD.clear(); GD.update(_SAVE[1])
roofs_plan = _SAVE[2]

# ---- 遊戯室（平面だけ）・教室3つ・居場所2つ（右の下、3列×2段のます。10-30 18:05：季節ごとの空気環境と配慮を6枚目へ移したので大きく）
_cell_w = (_RW - 2 * 8) / 3
_cell_h = (fy - 8 - (M + 8) - 2 * 10 - 8) / 2
_gy0 = M + 8                                    # 下の段の下端
_cells = [(_RX + c_ * (_cell_w + 8), _gy0 + (1 - r_) * (_cell_h + 10)) for r_ in range(2) for c_ in range(3)]
# 教室と居場所は Rhino のレンダリング（ユーザー 10-30 18:05、別の手伝いが視点を作る：rhino/out/room_*_hiru.png）。無ければ軸測図（sozai/20a〜21b）を仮に
AXO = [("20a_教室_3〜5歳.pdf", "教室　3〜5歳", "room_3to5_hiru.png", "23a"), ("20b_教室_0・1歳.pdf", "教室　0・1歳", "room_01_hiru.png", "23b"),
       ("20c_教室_2歳.pdf", "教室　2歳", "room_2_hiru.png", "23c"), ("21a_居場所_読書.pdf", "居場所　読書", "room_dokusho_hiru.png", "23d"),
       ("21b_居場所_遊戯室の箱.pdf", "居場所　遊戯室の箱", "room_hako_hiru.png", "23e")]
for (fn_, nm_, png_, key_), (cx_, cy_) in zip(AXO, _cells):
    p_ = os.path.join(HERE, "sozai", fn_)
    r_ = os.path.join(HERE, "rhino", "out", png_)
    if os.path.exists(r_):
        title(ax, cx_, cy_ + _cell_h + TITLE_GAP, nm_, "")
        _r = _img_box(r_, cx_, cy_, _cell_w, _cell_h, fit="contain", align="left")
        sozai(key_, nm_.replace("　", "_") + "（Rhinoのレンダリング）", 2, _r[0], _r[1], _r[2], _r[3], "rhino/out/" + png_)
        continue
    title(ax, cx_, cy_ + _cell_h + TITLE_GAP, nm_, "軸測図（レンダリングを待つあいだ）")
    if os.path.exists(p_):
        embed(2, p_, None, cx_, cy_, fit=(_cell_w, _cell_h))
        _topalign(2, cy_ + _cell_h)
    else:
        box(ax, cx_, cy_, _cell_w, _cell_h, nm_ + "（作成中）", "sozai/" + fn_ + "ができたら入る")
PLAYP = os.path.join(ROOT, "out", "sodachiya_play_present.pdf")
_pcx, _pcy = _cells[5]
title(ax, _pcx, _pcy + _cell_h + TITLE_GAP, "遊戯室", "平面")
# 遊戯室の図の平面だけ（断面は外す、ユーザー 10-30 16:15）。文字は図から外して一つずつ部品に（グループ「遊戯室（文字）」、10-30 23:07）
PLAY_CLIP = (0, 0, 230, 150)
PLAYP_NT = os.path.join(HERE, "sozai", "26_遊戯室_平面_文字なし.pdf")
_pd = fitz.open(PLAYP)
_pp = _pd[0]
_spans = []
for b_ in _pp.get_text("dict")["blocks"]:
    for l_ in b_.get("lines", []):
        for sp_ in l_["spans"]:
            if sp_["text"].strip():
                _spans.append(sp_)
                _pp.add_redact_annot(fitz.Rect(sp_["bbox"]), fill=False)
_pp.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
_pd.save(PLAYP_NT, garbage=3, deflate=True)
embed(2, PLAYP_NT, PLAY_CLIP, _pcx, _pcy, fit=(_cell_w, _cell_h))
_topalign(2, _pcy + _cell_h)
_e_ = embeds[2][-1][3]
_psc = _e_[2] / (PLAY_CLIP[2] - PLAY_CLIP[0])
_live(ax, 2, "play", "遊戯室（文字）")
_np = 0
for sp_ in _spans:
    ox_, oy_ = sp_["origin"][0] / MM, sp_["origin"][1] / MM
    if not (PLAY_CLIP[0] <= ox_ <= PLAY_CLIP[2] and PLAY_CLIP[1] <= oy_ <= PLAY_CLIP[3]):
        continue
    c_ = sp_["color"]
    T(ax, _e_[0] + (ox_ - PLAY_CLIP[0]) * _psc, _e_[1] + _e_[3] - (oy_ - PLAY_CLIP[1]) * _psc, sp_["text"].strip(),
      sp_["size"] * 0.3528 * 0.72 * _psc, "#%06x" % c_, bold=("Bold" in sp_["font"] or "W6" in sp_["font"]))
    _np += 1
_live(None, 2, None, None)
print("遊戯室の平面：文字 %d を部品に" % _np)
_AXO_TOP = _gy0 + 2 * _cell_h + 10 + 8           # 軸測図のますの上端（題を含む）

FIGS[2] = fig

# ================================================================ 4　平面図　2階（10-30：6枚の4枚目。10-30 16:15（ユーザー）：メインは平面図。
# 2階の平面図を1階（3枚目）と紙の上で同じ位置・同じ大きさに（1/100、重ねると上下が合う）。余った所は空けておく（面積表・こどもたちの環境は外した）
fig, ax = page()
frame(ax, 4, "平面図　2階", "2階（西館）の平面図1/100。1階（3枚目）と紙の上で同じ位置・同じ大きさ（重ねると上下が合う）", "平面図")
# 更新係の一枚では2階を西の道路の外へずらして描いている（views.json の shift_mm）。1階と2階の紙への写し（c・f）の差だけ戻し、3枚目と同じく 200 pt 左へ
P2_DX, P2_DY = _m1["c"] - _m2["c"] + PLAN_SX, _m1["f"] - _m2["f"]
# 一枚の左上の2階のまわりを、南東の外壁（x≈391 mm・y≈71 mm から南西へ）に沿った階段の形の四つの四角で切り抜く（仮）：道路・キッチンの角を入れない
CLIP_2F = (12, 20, 394, 298)
CLIP_2F_ST = [(12, 20, 394, 90), (12, 90, 378, 150), (12, 150, 323, 220), (12, 220, 258, 298)]
_EX2 = [(c_[2], c_[1], CLIP_2F[2], c_[3]) for c_ in CLIP_2F_ST[1:]]
for _i2, _c2 in enumerate(CLIP_2F_ST):
    embed(4, PLAN3, _c2, _c2[0] + P2_DX, H - (_c2[3] + P2_DY), 1.0, dwg=("plan2", "平面図　2階"),
          dwg_opt=dict(parts_clip=CLIP_2F, exclude=_EX2) if _i2 == 0 else dict(noparts=True))
# 2階で切った平面なので、下に見える本館の屋根伏せ（屋根・太陽光・光の筋・越屋根）と園庭、周り（3枚目と同じ）を薄く（10-30 18:05、ユーザー）。
# 2階の図（白い地）の上に重ねる一枚の素材（sozai/25）。西館の屋根の範囲には描かない（2階の図のまま）
_CUT4 = TRP(R20.buffer(0.6)) if R20 is not None else None


def _shita(a_, cl_):
    draw_shape(a_, cl_(TRP(rot(GD["garden"]))), _XID, fc="#EEF3E8", ec="#B5C4A5", lw=0.15, z=4)
    draw_shape(a_, cl_(TRP(rot(GD["mound"]))), _XID, fc="none", ec="#9DB08A", lw=0.2, z=4.1)
    draw_shape(a_, cl_(TRP(rot(GD["stream"]))), _XID, ec="#7FB2D6", lw=0.6, z=4.2)
    for g_, c_, z_ in ((R10, "#E7E4DE", 5), (R35, "#E7E4DE", 5), (SOL, "#6B7178", 5.2), (STR_, "#F8F6EF", 5.3), (LIDS, "#E6EFF3", 5.4)):
        if g_ is not None:
            draw_shape(a_, cl_(TRP(g_)), _XID, fc=c_, ec="none", z=z_)
    draw_shape(a_, cl_(TRP(unary_union([x for x in (R10, R35) if x is not None]))), _XID, fc="none", ec="#555555", lw=0.35, z=5.5)


MAWARI4 = _mawari(os.path.join(HERE, "sozai", "25_平面図の周り_2階と屋根伏せ.pdf"), extra=_shita, cut=_CUT4)
embed(4, MAWARI4, None, 0, 0, 1.0)                # 2階の図の上（2階の範囲は抜いてある）
print("2階の平面図：1階と同じ位置へ %.1f・%.1f mm" % (P2_DX, P2_DY))
FIGS[4] = fig
figs[:] = [FIGS[i_] for i_ in range(1, 7)]      # 枚の番号の順（ai_layout は figs の順で p1〜p6）

# ---------------------------------------------------------------- 書き出し
base = os.path.join(OUT, "_base.pdf")
from matplotlib.backends.backend_pdf import PdfPages
with PdfPages(base) as pp:
    for f in figs:
        pp.savefig(f)
doc = fitz.open(base)
for si in range(1, 7):
    pg = doc[si - 1]
    for k_e, (src, pno, clip, (x, y, w, h)) in enumerate(embeds[si]):
        sd = fitz.open(src)
        cr = fitz.Rect(clip[0] * MM, clip[1] * MM, clip[2] * MM, clip[3] * MM)
        dr = fitz.Rect(x * MM, (H - y - h) * MM, (x + w) * MM, (H - y) * MM)
        pg.show_pdf_page(dr, sd, pno, clip=cr)
        if (si, k_e) in RHINO_TXT:                     # Rhino の線の上に文字と寸法
            pg.show_pdf_page(dr, fitz.open(RHINO_TXT[(si, k_e)]), pno, clip=cr)
    if si in FRAME_TOP:                                # 紙いっぱいの図（4枚目の平面図、白い地）の上に枠を重ねる（.ai も枠をその図の上のレイヤーに、10-29）
        pg.draw_rect(fitz.Rect(M * MM, M * MM, (W - M) * MM, (H - M) * MM), color=(0.133, 0.133, 0.133), width=0.6)
        pg.draw_line(fitz.Point(M * MM, (M + HDR) * MM), fitz.Point((W - M) * MM, (M + HDR) * MM), color=(0.133, 0.133, 0.133), width=0.4)
        pg.insert_text(fitz.Point((M + 4) * MM, (M + HDR_BL) * MM), SCHOOL, fontsize=NAME_SZ / 0.72 * MM, fontname="F_B", fontfile=FONTB, color=(0.133, 0.133, 0.133))
        pg.insert_text(fitz.Point((M + THEME_X) * MM, (M + HDR_BL) * MM), PAGE_TITLES.get(si, ""), fontsize=THEME_SZ / 0.72 * MM, fontname="F_B", fontfile=FONTB, color=(0.133, 0.133, 0.133))
doc_clean = fitz.open("pdf", doc.tobytes())          # 素材は引き出し線・重ねた文字を入れる前から切り抜く（ユーザー、10-25）
for si in range(1, 7):
    pg = doc[si - 1]
    for (pts, col, *_k) in TOPL[si]:                     # 引き出し線は貼った図の上に（箱 → 折れ点 → 配置図の点）
        rgb = tuple(int(col[k:k + 2], 16) / 255 for k in (1, 3, 5))
        P_ = [fitz.Point(q[0] * MM, (H - q[1]) * MM) for q in pts]
        pg.draw_polyline(P_, color=rgb, width=0.6)
        pg.draw_circle(P_[-1], 0.9 * MM, color=rgb, fill=rgb)
    for ui_ in USER_ITEMS.get(si, []):                # 木田さんがIllustratorで足した物（export_layout.jsx の user_items）を見本にも（矢じりなどは出ない）
        _draw_user_item(pg, ui_)
    for (tx, ty, ts, th, tb, *ex) in TOPT[si]:
        if len(ex) > 2 and ex[2].get("align") in ("right", "center"):       # 右寄せ：x は右の端、中央：x は真ん中
            tx -= fitz.Font(fontfile=FONTB if tb else FONT).text_length(ts, th / 0.72) * (1.0 if ex[2]["align"] == "right" else 0.5)
        _fa = FONT_ALT.get(ex[0]) if ex and ex[0] else None
        _cc = tuple(int(ex[1][k:k + 2], 16) / 255 for k in (1, 3, 5)) if len(ex) > 1 else (0.1, 0.1, 0.1)
        pg.insert_text(fitz.Point(tx * MM, (H - ty) * MM), ts, fontsize=th / 0.72 * MM, fontname=("F_A" if _fa else ("F_B" if tb else "F_R")),
                       fontfile=_fa or (FONTB if tb else FONT), color=_cc)
    if si == 1:                                     # 番号の印（案H）：配置図の上と箱の見出しの頭。.ai で動かした印は見本にも（配置図からの位置で）
        _hx = lambda c_: tuple(int(c_[k:k + 2], 16) / 255 for k in (1, 3, 5))
        _FB = fitz.Font(fontfile=FONTB)
        for mk in MARKS:
            cx_, cy_, r_ = mk["cx"], mk["cy"], mk["r"]
            _um = _UP.get(f"p1.{mk['id']}.shape") or {}
            if mk.get("follow") == "sozai.01a" and "x" in _um:
                cx_, cy_ = _um["x"] + _um.get("w", 2 * r_) / 2 + _udx, H - (_um["y"] + _um.get("h", 2 * r_) / 2 + _udy)
            col_ = _hx(C_NAT if mk["cat"] == "nat" else C_COM)
            ring_ = (1, 1, 1) if mk["ring"] else None
            if mk["cat"] == "nat":
                pg.draw_circle(fitz.Point(cx_ * MM, (H - cy_) * MM), r_ * MM, color=ring_, fill=col_, width=0.8 if ring_ else 0)
            else:
                s_ = r_ * 0.9
                pg.draw_rect(fitz.Rect((cx_ - s_) * MM, (H - cy_ - s_) * MM, (cx_ + s_) * MM, (H - cy_ + s_) * MM), color=ring_, fill=col_, width=0.8 if ring_ else 0)
            e_ = (MARK_NUM if mk["ring"] else MARK_NUM_BOX) / 0.72
            t_ = str(mk["num"])
            pg.insert_text(fitz.Point((cx_ - _FB.text_length(t_, e_) / 2) * MM, (H - (cy_ - 0.35 * e_)) * MM), t_, fontsize=e_ * MM, fontname="F_B", fontfile=FONTB, color=(1, 1, 1))
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
    pg_.show_pdf_page(pg_.rect, fitz.open(_SITE_PDF[gr]), 0, clip=fitz.Rect(bsx * MM, (YT - bsy - bsh) * MM, (bsx + bsw) * MM, (YT - bsy) * MM))
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
axF.plot([M, W - M], [H - M - HDR, H - M - HDR], color=INK, lw=0.4)
T(axF, M + 4, H - M - HDR_BL, SCHOOL, NAME_SZ, bold=True)
T(axF, M + THEME_X, H - M - HDR_BL, "1サブタイトル", THEME_SZ, bold=True)
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
for sh_ in range(1, 7):
    for k_e, (src, pno, clip, (x, y, w, h)) in enumerate(embeds[sh_]):
        rel = os.path.relpath(src, ROOT) + (f"`＋`{os.path.relpath(RHINO_TXT[(sh_, k_e)], ROOT)}`（上に重ねる）" if (sh_, k_e) in RHINO_TXT else "")
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
# 番号の振り直し（前に組んだ .ai の番号 → 今の番号）。maps のキーは前に組んだときの renumber の id（_none は最初の番号）。
# 10-28 13:17（ユーザー）：5枚の番号を振り直した（id 2026-10-28b）。10-30（先生のエスキス、ユーザー）：6枚に組み直した（id 2026-10-30）。
# 前の id の写し方は、今の番号まで続けて写した形（2026-10-28 → 2026-10-28b → 2026-10-30）。
# split：枚が分かれた部品（前の3枚目の季節ごとの空気環境・配慮は2枚目、面積表は4枚目。前の5枚目のこどもたちの環境は4枚目）。部品の名前の頭 → 新しい頭（長い方が先）。
# export_layout が前の番号の .ai から書き出すとき、split に当たった部品は位置を書き出さない（前の紙の位置なので）
RENUMBER = dict(id="2026-10-30",
                maps={"2026-10-28b": {"1": 1, "2": 5, "3": 6, "4": 3, "5": 2},
                      "2026-10-28": {"1": 1, "2": 3, "3": 2, "4": 5, "5": 6},
                      "_none": {"1": 1, "2": 5, "3": 3, "4": 2, "5": 6}},
                split={"2026-10-28b": {"p5.link.": "p4.link.", "p5.box.": "p4.box.", "p5.t.こどもたちの環境": "p4.t.こどもたちの環境",
                                       "p5.t.園庭": "p4.t.園庭", "p5.t.だいさんかく": "p4.t.だいさんかく", "p5.t.遊戯室": "p4.t.遊戯室",
                                       "p5.t.ホールの北山杉の林": "p4.t.ホールの北山杉の林", "p5.t.教室": "p4.t.教室", "p5.t.3歳の保育室": "p4.t.3歳の保育室",
                                       "p5.t.廊下の本棚と読む場所": "p4.t.廊下の本棚と読む場所", "p5.t.（図は本館係に依頼）": "p4.t.（図は本館係に依頼）",
                                       "p5.t.表の畑と火のオーブン": "p4.t.表の畑と火のオーブン", "p5.t.入口の前の菜園": "p4.t.入口の前の菜園",
                                       "p5.t.（図はアプローチ係に依頼）": "p4.t.（図はアプローチ係に依頼）"}},
                note="10-30：6枚に組み直した（先生のエスキス、ユーザー）。16:15に面積表、18:05に季節ごとの空気環境・配慮を6枚目へ戻した（splitから外した）。前（2026-10-28b）の1→1、2→5、3→6、4→3、5→2。"
                     "枚が分かれた部品は split（前の番号の .ai から書き出すと位置は書き出さない）。前の id の写し方は今の番号まで続けた形")
print("Rhino の図：", "、".join(RHINO_USED) if RHINO_USED else "無し（drawings_rhino/ が無いので自動の図のまま）")
# 地域のなかの敷地（素材14）は用水のネットワークと同じレイヤー（説明）の、その上に（ユーザー 10-29 17:24）。表題・出典はユーザーが隠した・離したので、図だけのグループ
_GROUPS = {f"p1.{k_}": ("water", "用水のネットワーク") for k_ in ("sozai.02", "water.title", "water.source", "water.source2")}
_GROUPS["p1.link.14_地域のなかの敷地_1-10000"] = ("areamap", "地域のなかの敷地")
_GROUPS["p1.top.地域のなかの敷地110000"] = ("areamap", "地域のなかの敷地")
ai_layout.write(dict(order=[dict(layer="説明", name="地域のなかの敷地", above="用水のネットワーク")], groups=_GROUPS, frame_hdr=(HDR, HDR_BL, NAME_SZ, SCHOOL), mark_num_box=MARK_NUM_BOX, emb_dwg=EMB_DWG, siteparts=SITEPARTS, figs=figs, rec=AIREC, sozai=SOZAI, sozfn=SOZFN, sitemap=SITEMAP, sitebig=[bsx, H - bsy - bsh, bsw, bsh], site_shift=SITE_SHIFT, rhino_txt=RHINO_TXT, dwg=DWG, siteclip_full=[M, H - 2 * M], plan_links=[_SUNF], anchors={"p1.siteplan": PLAN_ANCHOR_AI}, anchors_prev={"p1.siteplan": PLAN_ANCHOR_PREV}, embeds=embeds, topl=TOPL, topt=TOPT, marks=MARKS, ai_shift=AI_SHIFT, mark_num=MARK_NUM, cnat=C_NAT, ccom=C_COM,
                     renumber=RENUMBER,
                     W=W, H=H, MM=MM, NOTE=NOTE, INK=INK, ROOT=ROOT, HERE=HERE))

# 壁に貼ったときの全体（2段×3列：上の段1・3・5、下の段2・4・6、10-30）。枠と注をmatplotlibで描き、6枚はPDFのまま縮めて貼る
fig = plt.figure(figsize=(841 / 25.4, 594 / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
SC = 594 / 2500                       # 壁のmm → 紙のmm
ax.set_xlim(0, 841 / SC)
ax.set_ylim(0, 2500)
ax.axis("off")
x0w, base_ = 250, 350
_cx = lambda c_: x0w + c_ * (841 + 120)
_top = base_ + 594 + 60
pos = {1: (_cx(0), _top), 2: (_cx(0), base_), 3: (_cx(1), _top), 4: (_cx(1), base_), 5: (_cx(2), _top), 6: (_cx(2), base_)}
# 壁の並び（先生のエスキス 10-30、ユーザー）：2段×3列、上の段1・3・5、下の段2・4・6。
# 列ごとに：配置図とゾーニング・動線／1階と2階の平面／立面と断面
for i in range(6):
    x, y = pos[i + 1]
    ax.add_patch(Rectangle((x, y), 841, 594, fill=False, ec="#555555", lw=0.5, zorder=2))
ax.plot([100, 3300], [0 + 5, 5], color=INK, lw=1)
ax.plot([100, 3300], [1500, 1500], color=NOTE, lw=0.8, ls=(0, (6, 4)))
def TW(x, y, s, size, **kw):  # sizeは紙のmm
    T(ax, x, y, s, size, **kw)
TW(110, 1515, "目の高さ1.5 m", 3.2, color=NOTE)
TW(110, 20, "床", 3.2)
TW(x0w, 2400, "壁に貼ったとき　2段×3列：上の段1・3・5、下の段2・4・6", 6.0, bold=True)
notes = ["1　敷地と自然環境・地域、その下に2　ゾーニングと動線・環境。",
         "真ん中の列に3　平面図1階、その下に4　平面図2階・こどもたちの環境。",
         "右の列に5　立面・景観、その下に6　断面・構造。",
         "3・4・5・6枚目の平面・立面・断面は3dmから自動の図を実寸で貼る。"]
for i, s_ in enumerate(notes):
    TW(x0w, base_ - 60 - i * 55, s_, 3.2, color=NOTE)
ov = os.path.join(OUT, "_overview.pdf")
fig.savefig(ov)
plt.close(fig)
_od = fitz.open(ov)
_pg = _od[0]
for i in range(6):
    x, y = pos[i + 1]
    _pg.show_pdf_page(fitz.Rect(x * SC * MM, (594 - (y + 594) * SC) * MM, (x + 841) * SC * MM, (594 - y * SC) * MM), doc, i)
_od.save(os.path.join(OUT, "sodachiya_present_overview.pdf"), garbage=3, deflate=True)
_od.close()

for f in (base, ov, *_SITE_PDF.values()):
    os.remove(f)
json.dump(dict(info, areas={k: round(v, 1) for k, v in AREA.items()}), open(os.path.join(OUT, "mock_info.json"), "w"), ensure_ascii=False, indent=1)
print("ok")
