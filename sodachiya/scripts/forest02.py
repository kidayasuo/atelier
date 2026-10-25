# ホールの北山杉の林：こどもの目の高さ（0.9）から見た 4 つの景色（円筒投影、横＝方位、縦＝仰角）
# 配列は data/forest.json。見る向きで透けたり壁になったりするかを確かめる図。A3 横。
import json, math, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Circle, FancyArrowPatch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.environ.get("OUT", os.path.join(ROOT, "out"))
plt.rcParams["font.family"] = "Noto Sans CJK JP"
F = json.load(open(os.path.join(ROOT, "data", "forest.json")))
P, TR, TOPC = F["PARAMS"], F["TREES"], F["TOP"]

def top(v, u=None, d=0.0):
    """幹の上端：屋根の下（垂木の下端）、西吹き抜けは越屋根の中。梁の真下なら梁の下端の 0.03 手前。"""
    if u is not None and any(abs(u - uf) < P["BEAM_HALF"] + d / 2 for uf in P["FRAMES"]):
        return 4.0 - max(0.0, v) / 12.0 - 0.6 - TOPC["BEAM_GAP"]
    return TOPC["WEST_VOID_TOP"] if v < TOPC["WEST_VOID_V"] else 4.0 - v / 12.0
def roof(v):
    if v < 0: return 3.25                     # west building 2nd floor (east band)
    if v < 1.6: return 4.6
    return 4.0 - v / 12.0 if v <= 12 else 3.0 - (v - 12) / 12.0

C = dict(t50="#C9A27A", t70="#9C6B3F", t100="#6B4423", nushi="#3E2512", floor="#E9D3A9", strait="#D9CBB4",
         glass="#E6EEF2", garden="#DDE3CF", wall="#EFE7D8", kit="#F4DCC4", band="#F4EBDD")
DCOL = {0.05: C["t50"], 0.07: C["t70"], 0.1: C["t100"], 0.2: C["nushi"]}

# the room: u 22.5–30, v −3.4–15 (plus the strait open to the south)
def boundary(p, r):
    """ray from p in direction r (uv) → (distance, kind)"""
    best = (30.0, "far")
    for (axis, val, kind) in [(0, 30.0, "wall"), (0, 21.0, "wall"), (1, 15.0, "garden"), (1, -3.4, "kit")]:
        if abs(r[axis]) < 1e-9: continue
        t = (val - p[axis]) / r[axis]
        if t <= 0.05: continue
        q = p + r * t; o = 1 - axis
        if axis == 0 and not (-3.4 <= q[o] <= 15): continue
        if axis == 1 and not (21.0 <= q[o] <= 30): continue
        if t < best[0]: best = (t, kind)
    return best

def render(ax, p, fwd, eye, title, fov=110):
    p = np.array(p, float); fwd = np.array(fwd, float); fwd /= np.linalg.norm(fwd)
    a0 = math.atan2(fwd[1], fwd[0])
    ax.set_xlim(-fov / 2, fov / 2); ax.set_ylim(-48, 52); ax.axis("off")
    # background: floor, far boundary as a band floor→roof
    ax.add_patch(Polygon([(-fov / 2, -48), (fov / 2, -48), (fov / 2, 0), (-fov / 2, 0)], fc=C["floor"], ec="none", zorder=0))
    az = np.linspace(-fov / 2, fov / 2, 400)
    lo, hi, cols = [], [], []
    for a in az:
        ang = a0 + math.radians(a)                         # (u, v) is left-handed on the ground (+u north, +v east): +angle = to the right
        r = np.array([math.cos(ang), math.sin(ang)])
        D, kind = boundary(p, r)
        q = p + r * D
        z1 = roof(q[1]) if kind != "garden" else 2.445   # 縁側のガラス戸の鴨居の上端（10-26）
        lo.append(math.degrees(math.atan2(-eye, D))); hi.append(math.degrees(math.atan2(z1 - eye, D))); cols.append(kind)
    col = {"wall": C["wall"], "garden": C["garden"], "kit": C["kit"], "far": C["strait"]}
    for i in range(len(az) - 1):
        ax.add_patch(Polygon([(az[i], lo[i]), (az[i + 1], lo[i + 1]), (az[i + 1], hi[i + 1]), (az[i], hi[i])], fc=col[cols[i]], ec="none", zorder=1))
    # roof underside (sky of the hall)
    for i in range(len(az) - 1):
        ax.add_patch(Polygon([(az[i], hi[i]), (az[i + 1], hi[i + 1]), (az[i + 1], 52), (az[i], 52)], fc="#F7F2E8", ec="none", zorder=1))
    # trunks, far to near
    items = []
    for t_ in TR:
        q = np.array([t_["u"], t_["v"]]); dvec = q - p; D = np.linalg.norm(dvec)
        if D < 0.3: continue
        ang = math.atan2(dvec[1], dvec[0]); rel = math.degrees(math.atan2(math.sin(ang - a0), math.cos(ang - a0)))
        if abs(rel) > fov / 2 + 10: continue
        if t_["shape"] == "taiko":
            fa = math.radians(t_["ang"]); phi = ang - fa
            w = t_["d"] * abs(math.sin(phi)) + t_["t"] * abs(math.cos(phi))
        else:
            w = t_["d"]
        items.append((D, rel, w, t_))
    items.sort(key=lambda x: -x[0])
    for D, rel, w, t_ in items:
        half = math.degrees(math.atan2(w / 2, D))
        b = math.degrees(math.atan2(-eye, D)); tp = math.degrees(math.atan2(t_["h"] - eye, D))
        shade = min(1, 2.2 / D)
        ax.add_patch(Polygon([(rel - half, b), (rel + half, b), (rel + half, tp), (rel - half, tp)],
                             fc=DCOL[t_["d"]], ec="none", alpha=0.45 + 0.55 * shade, zorder=3 + 1 / D))
    # opacity: share of the horizon (eye level) hidden by trunks within the room
    cover = np.zeros(1100)
    xs = np.linspace(-fov / 2, fov / 2, 1100)
    for D, rel, w, t_ in items:
        half = math.degrees(math.atan2(w / 2, D)); cover[(xs > rel - half) & (xs < rel + half)] = 1
    ax.text(-fov / 2, 50, title, fontsize=8, weight="bold", va="top")
    ax.text(fov / 2, 50, f"目の高さで幹に隠れる割合 {cover.mean() * 100:.0f}%", fontsize=6, va="top", ha="right", color="#555555")
    for a in (-45, 0, 45): ax.plot([a, a], [-48, -45], lw=0.4, color="#999999")
    return cover.mean()

MM = 1 / 25.4
fig = plt.figure(figsize=(420 * MM, 297 * MM))
fig.text(14 / 420, 288 / 297, "ホールの北山杉の林　こどもの目の高さ（0.9 m）から見た景色　（たたき台・6 版：すべて自立）", fontsize=11, weight="bold", va="top")
fig.text(14 / 420, 281 / 297, "円筒投影（横＝方位 110°、縦＝仰角）。幹は北山杉（φ50 は磨き丸太、群の φ70・100 は太鼓落とし＝両側を平らに挽いた丸太、平らな面を列の向きにそろえる）。"
         "奥の色：うす緑＝縁側のガラス越しの園庭、ベージュ＝壁、橙＝キッチンのガラス、灰＝海峡。低い木（0.85〜1.1）はこどもの目の高さを隠し、高い木は屋根の近くまで", fontsize=6.2, va="top")
VIEWS = [
    ("A　海峡から北を見る（登園のこども）", (22.2, 8.6), (1, 0), 0.75),
    ("B　外縁側から西を見る（園庭から入ってくる）", (25.6, 14.2), (0, -1), 0.9),
    ("C　東の帯から東を見る（遊戯室から戻る）", (28.6, -1.8), (0, 1), 0.9),
    ("D　絵本の通りの入口から南東を見る", (29.8, 0.8), (-0.6, 0.8), 0.9),
]
W_, H_ = 196, 100
pos = [(14, 168), (214, 168), (14, 62), (214, 62)]
res = {}
for (title, p, fwd, eye), (x, y) in zip(VIEWS, pos):
    ax = fig.add_axes([x / 420, y / 297, W_ / 420, H_ / 297])
    res[title[0]] = render(ax, p, fwd, eye, title)
# ---------------------------------------------------------------- key plan and the "rose" of see-through
def proj_w(t_, ang):
    if t_["shape"] == "taiko":
        phi = ang - math.radians(t_["ang"]); return t_["d"] * abs(math.sin(phi)) + t_["t"] * abs(math.cos(phi))
    return t_["d"]
def blocked(theta):
    """theta: direction in (u, v), rad. Share of parallel sight lines across the hall (u 22.5–30, v 0–12) that hit a trunk."""
    r = np.array([math.cos(theta), math.sin(theta)]); n = np.array([-r[1], r[0]])
    c = np.array([26.25, 6.0]); offs = np.arange(-8, 8, 0.02)
    hit = np.zeros(len(offs), bool); inside = np.zeros(len(offs), bool)
    for k, o in enumerate(offs):
        p0 = c + n * o
        # does this line cross the hall box?
        ts = []
        for axis, lo_, hi_ in [(0, 22.5, 30.0), (1, 0.0, 12.0)]:
            if abs(r[axis]) < 1e-9:
                if not (lo_ <= p0[axis] <= hi_): ts = None; break
                continue
            ts.append(sorted([(lo_ - p0[axis]) / r[axis], (hi_ - p0[axis]) / r[axis]]))
        if ts is None: continue
        if ts:
            a = max(t[0] for t in ts); b = min(t[1] for t in ts)
            if a < b: inside[k] = True
    for t_ in TR:
        q = np.array([t_["u"], t_["v"]]); o = (q - c) @ n; w = proj_w(t_, theta)
        hit |= (np.abs(offs - o) < w / 2)
    return (hit & inside).sum() / max(1, inside.sum())

kx = fig.add_axes([14 / 420, 6 / 297, 118 / 420, 50 / 297]); kx.set_aspect("equal"); kx.axis("off")
kx.add_patch(Polygon([(0, 22.5), (12, 22.5), (12, 30), (0, 30)], fc="#E3C08D", ec="none"))
kx.add_patch(Polygon([(-3.4, 21), (15, 21), (15, 22.5), (-3.4, 22.5)], fc="#D9CBB4", ec="none"))
kx.add_patch(Polygon([(-3.4, 22.5), (0, 22.5), (0, 30.5), (-3.4, 30.5)], fc="#F4EBDD", ec="none"))
kx.add_patch(Polygon([(12, 22.5), (15, 22.5), (15, 30.5), (12, 30.5)], fc="#F4EBDD", ec="none"))
from shapely.geometry import LineString as _LS
_b = _LS([(v, u) for u, v in F["CHANNEL"]["line_uv"]]).buffer(P["CHANNEL"]["clear"] / 2, cap_style=2)
kx.add_patch(Polygon(list(_b.exterior.coords), fc="#FFF6E6", ec="#B07A2A", lw=0.3, ls=(0, (3, 2))))
for t_ in TR: kx.add_patch(Circle((t_["v"], t_["u"]), max(t_["d"] / 2, 0.09), fc=DCOL[t_["d"]], ec="none"))
for (title, p, fwd, eye) in VIEWS:
    f = np.array(fwd, float); f /= np.linalg.norm(f)
    kx.add_patch(FancyArrowPatch((p[1], p[0]), (p[1] + f[1] * 1.6, p[0] + f[0] * 1.6), arrowstyle="-|>", mutation_scale=6, lw=0.8, color="#C0392B"))
    kx.text(p[1] - f[1] * 0.6, p[0] - f[0] * 0.6, title[0], fontsize=6.5, color="#C0392B", ha="center", va="center", weight="bold")
kx.set_xlim(-4, 16); kx.set_ylim(20.5, 31)
kx.text(-4, 31.3, "見る位置（赤）と林　上が北", fontsize=6, va="bottom")

def group_block(name, th):
    T = [t for t in TR if t["group"].startswith(name)]
    c = np.mean([[t["u"], t["v"]] for t in T], axis=0)
    r = np.array([math.cos(th), math.sin(th)]); n = np.array([-r[1], r[0]])
    os_ = [(np.array([t["u"], t["v"]]) - c) @ n for t in T]
    offs = np.arange(min(os_) - 0.3, max(os_) + 0.3, 0.01); hit = np.zeros(len(offs), bool)
    for t, o in zip(T, os_): hit |= np.abs(offs - o) < proj_w(t, th) / 2
    return hit.mean()
ROSE = {}
for k, name in enumerate(["西の群", "海峡の群"]):  # 縁側の群は疎らなので省く
    rx = fig.add_axes([(140 + k * 56) / 420, 8 / 297, 42 / 420, 42 / 297], projection="polar")
    ths = np.radians(np.arange(0, 360, 5))
    vals = np.array([group_block(name, t % math.pi) for t in ths])
    pa = math.pi / 2 - ths                                          # +u up, +v right
    rx.plot(np.r_[pa, pa[:1]], np.r_[vals, vals[:1]] * 100, color="#6B4423", lw=1.0)
    rx.fill(np.r_[pa, pa[:1]], np.r_[vals, vals[:1]] * 100, color="#C9A27A", alpha=0.35)
    rx.set_rlim(0, 75); rx.set_rticks([20, 40, 60]); rx.tick_params(labelsize=4.2)
    rx.set_xticks(np.radians([90, 0, 270, 180])); rx.set_xticklabels(["北", "東", "南", "西"], fontsize=5.2)
    rx.grid(lw=0.3); rx.set_title(name, fontsize=6.4, pad=4)
    ROSE[name] = (vals.min(), vals.max())
fig.text(250 / 420, 54 / 297, "透け方のばら（群ごと）：その向きに群を横切る視線のうち、幹に当たる割合（%）", fontsize=6.4, weight="bold", va="top")
import textwrap
msg = (f"西の群：列に沿う東西は {ROSE['西の群'][0] * 100:.0f}%、横切る向きは {ROSE['西の群'][1] * 100:.0f}%。"
       f"海峡の群：列に沿う南北は {ROSE['海峡の群'][0] * 100:.0f}%、横切ると {ROSE['海峡の群'][1] * 100:.0f}%。"
       "株立ち（2〜3 本が触れあう）を列の向きに並べると、KAIT 工房の扁平な柱と同じく、向きで薄くも厚くも見える。"
       "群ごとに向きを変えたので、ホール全体ではどの向きにも透ける筋と詰まる所がある。")
for i, ln in enumerate(textwrap.wrap(msg, 44)):
    fig.text(250 / 420, (48 - i * 3.3) / 297, ln, fontsize=5.9, va="top", color="#333333")
os.makedirs(OUT, exist_ok=True)
for ext in ("pdf", "png"):
    fig.savefig(os.path.join(OUT, f"sodachiya_forest_02.{ext}"), dpi=200 if ext == "png" else None)
print({k: round(v, 2) for k, v in res.items()}, {k: (round(a, 2), round(b, 2)) for k, (a, b) in ROSE.items()})
