"""育ち舎　部屋の切断の軸測図（2枚目「ゾーニングと動線・環境」に載せる素材、プレゼンの準備 10-30）

ユーザー（10-30 16:15）：教室3つ（3〜5歳・0・1歳・2歳）と居場所2つ（読書・遊戯室の箱）を、3dm からの切断の軸測図で。
- 屋根・母屋・垂木・光の筋のガラスと鏡・越屋根・2階の床は外し、壁・建具・ガラスは床から CUT（2.4 m）で切る。
  柱・梁（2枚組のすき間＝光の筋が見える）・吊り桟と天蓋は切らない。手前（南）の辺のそばの物（間仕切り・架構も）は LOW（0.9 m）で低く切って中を見せる。
- 部屋の外は描かない：部屋の範囲（本館の (u, v)、model/build/south/uv.py）の四角で、面と線を切り取る（壁の厚みの分だけ外へ余らせる）。
- 見る向きは配置図と同じ（3dm の xy を VIEW_ROT 回した紙の下＝高野川の側、南東の上から）。紙の上で全部同じ縮尺（1/150）。
- 色は data/materials.json の素材の色を白に寄せて淡く。布はレイヤーの色。
- 遊戯室の箱＝西の壁の「ひだ」（スギの板の箱を壁に付けたくぼみ3つ、kettei/yugishitsu.md）とその前の床（見当、10-30）。

python3 sodachiya/present/tools/rooms3d.py [確認用の出力フォルダ]
  → present/sozai/20a_教室_3〜5歳.pdf・20b_教室_0・1歳.pdf・20c_教室_2歳.pdf・21a_居場所_読書.pdf・21b_居場所_遊戯室の箱.pdf
  （確認用のフォルダを渡すと、各 png と5つを並べた PDF もそこに）
"""
import os, sys, math, json
import numpy as np
import rhino3dm as r
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_rgb

HERE = os.path.dirname(os.path.abspath(__file__))
SOD = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(SOD, "scripts"))
import fonts42  # noqa: F401,E402　文字は Type42（TrueType に変えた Noto）
sys.path.insert(0, os.path.join(SOD, "model", "build", "south"))
from uv import uv, xy  # noqa: E402

SOZAI = os.path.join(SOD, "present", "sozai")
CHK = sys.argv[1] if len(sys.argv) > 1 else None
SCALE = 150.0                           # 1/150（0・1歳の部屋が幅 約130 mm に入る縮尺、5つとも同じ）
MMPM = 1000.0 / SCALE                   # 紙の mm / m
CUT, LOW = 2.4, 0.9                     # 壁を切る高さ、手前の間仕切りを切る高さ（m）
PALE = 0.42                             # 素材の色を白に寄せる割合（ふつう）
PALE_BY = (("17", 0.62), ("21_", 0.62), ("24_", 0.62), ("38_", 0.55), ("5", 0.40), ("31_", 0.40),
           ("11", 0.15), ("22", 0.15), ("37_", 0.28), ("46_", 0.28), ("49_", 0.30), ("86_", 0.25), ("81_", 0.28))   # 壁は淡く、架構と家具は少し濃く
INK = "#2A2A2A"
FSN, FS = 9.5, 7.0                      # 部屋の名前・注（pt）

# ---------------------------------------------------------------- 素材の色
MAT = json.load(open(os.path.join(SOD, "data", "materials.json"), encoding="utf-8"))
VIEW_ROT = json.load(open(os.path.join(SOD, "data", "garden.json"), encoding="utf-8"))["VIEW_ROT"]["deg"]
m = r.File3dm.Read(os.path.join(SOD, "model", "sodachiya_exact_mesh.3dm"))
LAY = {l.Index: l for l in m.Layers}


def material(ln, name, thick_mm):
    for w, mt in MAT["names"]:
        if w in name:
            return mt
    for pre, mt in MAT["layers"]:
        if ln.startswith(pre):
            if isinstance(mt, dict):
                return mt["thin"] if thick_mm <= mt["split"] else mt["else"]
            return mt
    return None


def color_of(o, thick_mm):
    l = LAY[o.Attributes.LayerIndex]
    mt = material(l.Name, o.Attributes.Name or "", thick_mm)
    if mt is None:
        return (0.85, 0.85, 0.85), 1.0, None
    d = MAT["materials"][mt]
    if d["base"] == "layer":
        c = np.array(l.Color[:3]) / 255
    else:
        c = np.array(d["base"]) / 255
    a = d.get("opacity", 1.0)
    pale = next((k for pre, k in PALE_BY if l.Name.startswith(pre)), PALE)
    if d["base"] == "layer":
        pale = 0.2
    c = c * (1 - pale) + pale
    return tuple(c), (0.18 if a < 0.5 else a), mt


# 描かないレイヤー（クスノキの切り株は洞の物で、ひだの図では切れ端になるので外す。屋根・光の筋のガラスと鏡・越屋根・2階の床・外の物・午睡のコット・天井扇・外壁の板）
SKIP = ("00_", "01", "02_", "03", "04_", "10_", "10b_", "10k_", "10m_", "10p_", "10r_", "10s_", "10t_", "10v_",
        "20", "21g_", "21y_", "17y_", "17g_", "17k_", "23_", "26_", "28_", "29_", "30_", "47_", "50", "58", "88_",
        "6", "7", "9", "85_", "12_", "13_", "14_", "16b_", "41_", "42_", "43", "44_", "45_")
KEEP_FULL = ("11a_", "11b_", "11c_", "51_", "51w_")                # 切らない（本館の柱・梁・吊り桟・天蓋。西館の柱は高いので切る）
WALLISH = ("16", "17", "18", "19", "21_", "24_", "27", "38_", "48_", "49_")   # 手前で低く切る候補（壁・建具・ガラス・格子）
FLOOR = ("5", "31_", "33_", "80_")                                    # 床（先に描く）

# ---------------------------------------------------------------- 場面（範囲は本館の (u, v)）
SCENES = [
    dict(key="20a_教室_3〜5歳", title="4歳の保育室", u=(42.0, 48.0), v=(1.6, 12.0), low="S",
         labels=[(43.5, 3.0, 1.9, "巣A（天蓋）", -10, 6), (46.8, 2.6, 1.2, "巣B（ロフト）", -10, 14),
                 (45.0, 5.8, 1.1, "腰の壁（上は縦格子）", 16, 22), (45.0, 10.5, 3.3, "光の筋（2枚組の梁のすき間）", 8, 14),
                 (45.0, 9.0, 0.0, "共有（集まる・食べる・寝る）", 16, -14)]),
    dict(key="20b_教室_0・1歳", title="0・1歳の保育室", u=(0.0, 12.0), v=(1.6, 12.0), low="S",
         labels=[(6.0, 9.0, 3.0, "光の筋（2枚組の梁のすき間）", 12, 8)]),
    dict(key="20c_教室_2歳", title="2歳の保育室", u=(12.0, 18.0), v=(1.6, 12.0), low="S",
         labels=[(15.0, 9.0, 3.0, "光の筋（2枚組の梁のすき間）", 12, 8)]),
    dict(key="21a_居場所_読書", title="絵本の通りと本の奥", u=(45.0, 57.34), v=(-0.4, 1.6), low="SE",
         labels=[(48.0, 0.8, 0.5, "絵本の通り（棚・くぼみ）", 12, -10), (55.5, 0.6, 0.4, "本の奥（畳・クッション）", 10, -14)]),
    dict(key="21b_居場所_遊戯室の箱", title="遊戯室の箱（西の壁のひだ）", u=(33.3, 44.6), v=(-15.4, -11.0), low="",
         labels=[(34.5, -13.5, 0.6, "くぼみ（座+300、奥に覗き窓）", -4, -12), (34.5, -13.5, 1.42, "天板h1.4（先生の飾り棚）", -10, 14)]),
]


def region_xy(sc, pad=0.18):
    (u0, u1), (v0, v1) = sc["u"], sc["v"]
    u0, u1, v0, v1 = u0 - pad, u1 + pad, v0 - pad, v1 + pad
    P = np.array([xy(u0, v0), xy(u1, v0), xy(u1, v1), xy(u0, v1)]) / 1000
    e1, e2 = P[1] - P[0], P[2] - P[1]
    if e1[0] * e2[1] - e1[1] * e2[0] < 0:
        P = P[::-1]
    return P


# ---------------------------------------------------------------- 3dm の形
def sample(c, n=36):
    if isinstance(c, r.PolylineCurve):
        P = [(c.Point(i).X, c.Point(i).Y, c.Point(i).Z) for i in range(c.PointCount)]
    elif isinstance(c, r.NurbsCurve) and c.Degree == 1:
        P = [(c.Points[i].X, c.Points[i].Y, c.Points[i].Z) for i in range(len(c.Points))]
    else:
        d = c.Domain
        P = [(p.X, p.Y, p.Z) for p in (c.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1))]
    P = np.array(P) / 1000
    if len(P) > 2 and np.linalg.norm(P[0] - P[-1]) < 1e-6:
        P = P[:-1]
    return P


def feature_edges(V, F, ang=28.0):
    nrm = []
    for f in F:
        P = V[f]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if len(f) == 4:
            n = n + np.cross(P[2] - P[0], P[3] - P[0])
        nl = np.linalg.norm(n)
        nrm.append(n / nl if nl > 0 else n)
    _, inv = np.unique(np.round(V, 4), axis=0, return_inverse=True)
    inv = inv.ravel()
    E = {}
    for fi, f in enumerate(F):
        for a, b in zip(f, f[1:] + f[:1]):
            k = (min(inv[a], inv[b]), max(inv[a], inv[b]))
            if k[0] != k[1]:
                E.setdefault(k, [a, b, []])[2].append(fi)
    ca = math.cos(math.radians(ang))
    return [(V[a], V[b]) for a, b, fs in E.values()
            if len(fs) == 1 or any(abs(float(nrm[fs[0]] @ nrm[j])) < ca for j in fs[1:])]


def geom(o):
    g = o.Geometry
    if isinstance(g, r.Mesh):
        V = np.array([(p.X, p.Y, p.Z) for p in g.Vertices]) / 1000
        F = []
        for i in range(len(g.Faces)):
            f = g.Faces[i]
            F.append([f[0], f[1], f[2]] if f[3] == f[2] else [f[0], f[1], f[2], f[3]])
        return [V[f] for f in F], feature_edges(V, F)
    if isinstance(g, r.Extrusion):
        A = sample(g.Profile3d(0, 0.0)); B = sample(g.Profile3d(0, 1.0))
        n = min(len(A), len(B)); A, B = A[:n], B[:n]
        faces = [A, B[::-1]] + [np.array([A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]]) for i in range(n)]
        edges = [(A[i], A[(i + 1) % n]) for i in range(n)] + [(B[i], B[(i + 1) % n]) for i in range(n)]
        if n <= 12:
            edges += [(A[i], B[i]) for i in range(n)]
        return faces, edges
    return None


# ---------------------------------------------------------------- 切る（凸の多角形の面と線を、平面の半空間で）
def clip_poly(P, planes):
    for n, d in planes:                 # 内側：P·n ≤ d
        if len(P) == 0:
            return P
        out = []
        s = P @ n - d
        for i in range(len(P)):
            a, b, sa, sb = P[i], P[(i + 1) % len(P)], s[i], s[(i + 1) % len(P)]
            if sa <= 0:
                out.append(a)
            if (sa <= 0) != (sb <= 0):
                out.append(a + (b - a) * sa / (sa - sb))
        P = np.array(out) if out else np.zeros((0, 3))
    return P


def clip_seg(a, b, planes):
    t0, t1 = 0.0, 1.0
    for n, d in planes:
        sa, sb = a @ n - d, b @ n - d
        if sa > 0 and sb > 0:
            return None
        if sa > 0:
            t0 = max(t0, sa / (sa - sb))
        elif sb > 0:
            t1 = min(t1, sa / (sa - sb))
    if t1 - t0 < 1e-6:
        return None
    return a + (b - a) * t0, a + (b - a) * t1


def side_planes(Q):
    pl = []
    for i in range(4):
        a, b = Q[i], Q[(i + 1) % 4]
        t = b - a
        n = np.array([t[1], -t[0], 0.0]); n /= np.linalg.norm(n)     # 左回りの外向き
        pl.append((n, float(n[:2] @ a)))
    return pl


def split_big(P, lim=0.7):
    """painter の順を良くするため、大きい面を三角に割る"""
    out = []
    tris = [np.array([P[0], P[i], P[i + 1]]) for i in range(1, len(P) - 1)]
    while tris:
        T = tris.pop()
        L = [np.linalg.norm(T[(i + 1) % 3] - T[i]) for i in range(3)]
        i = int(np.argmax(L))
        if L[i] > lim and len(out) + len(tris) < 400:
            a, b, c = T[i], T[(i + 1) % 3], T[(i + 2) % 3]
            mid = (a + b) / 2
            tris += [np.array([a, mid, c]), np.array([mid, b, c])]
        else:
            out.append(T)
    return out


# ---------------------------------------------------------------- 見る向き（配置図と同じ：紙の下＝高野川の側から）
EL = math.radians(40.0)
_rr = math.radians(VIEW_ROT)
_down = np.array([math.sin(-_rr), -math.cos(_rr)])           # 紙の下の向き（3dm の xy、VIEW_ROT を戻す）
CAM = np.r_[_down * math.cos(EL), math.sin(EL)]
CAM /= np.linalg.norm(CAM)
FWD = -CAM
RIGHT = np.cross(FWD, [0, 0, 1.0]); RIGHT /= np.linalg.norm(RIGHT)
UP = np.cross(RIGHT, FWD)
LIGHT = np.array([-0.3, 0.5, 0.81]); LIGHT /= np.linalg.norm(LIGHT)


def pj(P):
    P = np.atleast_2d(P)
    return np.c_[P @ RIGHT, P @ UP] * MMPM


def shade(c, P):
    if len(P) < 3:
        return c
    n = np.cross(P[1] - P[0], P[2] - P[0]); nl = np.linalg.norm(n)
    k = abs(float(n @ LIGHT)) / nl if nl > 0 else 0.6
    return tuple(np.clip(np.array(c) * (0.84 + 0.16 * k), 0, 1))


# ---------------------------------------------------------------- 物を集める（どれかの場面の範囲に掛かる物だけ）
REG = [region_xy(sc, pad=0.6) for sc in SCENES]
objs = []
for o in m.Objects:
    ln = LAY[o.Attributes.LayerIndex].Name
    if ln.startswith(SKIP):
        continue
    bb = o.Geometry.GetBoundingBox()
    lo = np.array([bb.Min.X, bb.Min.Y]) / 1000; hi = np.array([bb.Max.X, bb.Max.Y]) / 1000
    if not any((lo <= Q.max(0)).all() and (hi >= Q.min(0)).all() for Q in REG):
        continue
    gm = geom(o)
    if gm is None:
        continue
    thick = min(bb.Max.X - bb.Min.X, bb.Max.Y - bb.Min.Y, bb.Max.Z - bb.Min.Z)
    col, alpha, mt = color_of(o, thick)
    objs.append(dict(ln=ln, faces=gm[0], edges=gm[1], col=col, a=alpha, lo=lo, hi=hi))


def draw_scene(sc):
    Q = region_xy(sc)
    sides = side_planes(Q)
    um, vm = np.mean(sc["u"]), np.mean(sc["v"])
    _ud = xy(um + 0.5, vm) - xy(um - 0.5, vm)
    _vd = xy(um, vm + 0.5) - xy(um, vm - 0.5)
    lows = []                                                          # 低く切る辺（S＝南の u0、E＝東の v1）の面
    if "S" in sc["low"]:
        lows.append(max(sides, key=lambda t: -float(t[0][:2] @ _ud)))
    if "E" in sc["low"]:
        lows.append(max(sides, key=lambda t: float(t[0][:2] @ _vd)))
    near = lambda X: any((X @ n_ - d_) > -0.35 for n_, d_ in lows)
    items = []
    for ob in objs:
        if not ((ob["lo"] <= Q.max(0)).all() and (ob["hi"] >= Q.min(0)).all()):
            continue
        ln = ob["ln"]
        planes = list(sides)
        if not ln.startswith(KEEP_FULL):
            planes.append((np.array([0, 0, 1.0]), CUT))
        floor = ln.startswith(FLOOR)
        low = bool(lows) and not floor               # 手前の辺のそばは梁・柱も含めて低く（手前の架構で中が隠れないように）
        for P in ob["faces"]:
            C = clip_poly(P, planes)
            if len(C) < 3:
                continue
            if low and near(C.mean(0)):
                C = clip_poly(C, [(np.array([0, 0, 1.0]), LOW)])
                if len(C) < 3:
                    continue
            fc = shade(ob["col"], C) + (ob["a"],)
            for T in [C]:                  # 大きい面を割ると painter の順で継ぎ目が出るので割らない
                dep = -1e3 if floor else float(T.mean(0) @ CAM)
                items.append((dep, pj(T), fc, fc if ob["a"] >= 1 else "none", 0.08))
        ec = (0.22, 0.2, 0.18, 0.85 if ob["a"] >= 1 else 0.35)
        for a, b in ob["edges"]:
            s = clip_seg(a, b, planes)
            if s is None:
                continue
            if low and near((s[0] + s[1]) / 2):
                s = clip_seg(s[0], s[1], [(np.array([0, 0, 1.0]), LOW)])
                if s is None:
                    continue
            S = np.array(s)
            dep = (-1e3 + 1) if floor else float(S.mean(0) @ CAM) + 0.02
            items.append((dep, pj(S), "none", ec, 0.16))
    items.sort(key=lambda t: t[0])
    allp = np.vstack([t[1] for t in items])
    lo, hi = allp.min(0), allp.max(0)

    fig = plt.figure(figsize=((hi[0] - lo[0] + 60) / 25.4, (hi[1] - lo[1] + 40) / 25.4))
    W_, H_ = hi[0] - lo[0] + 60, hi[1] - lo[1] + 40
    ax = fig.add_axes([0, 0, 1, 1])
    ox, oy = 30 - lo[0], 20 - lo[1]
    ax.set_xlim(0, W_); ax.set_ylim(0, H_); ax.set_aspect("equal"); ax.axis("off")
    ax.add_collection(PolyCollection([t[1] + (ox, oy) for t in items], facecolors=[t[2] for t in items],
                                     edgecolors=[t[3] for t in items], linewidths=[t[4] for t in items],
                                     closed=True, joinstyle="round"))
    for (u, v, z, s, dx, dy) in sc["labels"]:
        p = pj(np.r_[xy(u, v) / 1000, z])[0] + (ox, oy)
        t = (p[0] + dx, p[1] + dy)
        ax.plot([p[0], t[0]], [p[1], t[1]], color=INK, lw=0.3)
        ax.plot([p[0]], [p[1]], "o", ms=1.0, color=INK)
        ax.text(t[0] + (0.8 if dx >= 0 else -0.8), t[1], s, fontsize=FS, ha="left" if dx >= 0 else "right",
                va="center", color=INK, bbox=dict(boxstyle="square,pad=0.12", fc="white", ec="none", alpha=0.8))
    ax.text(30, H_ - 6, sc["title"], fontsize=FSN, fontweight="bold", ha="left", va="center", color=INK)
    # 切り抜き：図と文字の外形（軸の枠は数えない）
    from matplotlib.transforms import Bbox
    rd = fig.canvas.get_renderer()
    pts = allp + (ox, oy)
    ex = [Bbox([[pts[:, 0].min(), pts[:, 1].min()], [pts[:, 0].max(), pts[:, 1].max()]]).transformed(ax.transData)]
    ex += [t.get_window_extent(rd) for t in ax.texts]
    bb = Bbox.union(ex).transformed(fig.dpi_scale_trans.inverted()).padded(1.5 / 25.4)
    out = os.path.join(SOZAI, sc["key"] + ".pdf")
    fig.savefig(out, bbox_inches=bb)
    if CHK:
        fig.savefig(os.path.join(CHK, sc["key"] + ".png"), dpi=200, bbox_inches=bb)
    plt.close(fig)
    return out


outs = []
only = os.environ.get("ROOMS3D_ONLY")
for sc in SCENES:
    if only and only not in sc["key"]:
        continue
    outs.append(draw_scene(sc))
    print(outs[-1])

if CHK and not only:
    import fitz
    doc = fitz.open()
    pg = doc.new_page(width=420 * 72 / 25.4, height=230 * 72 / 25.4)
    x = y = 20.0; rowh = 0.0
    for f in outs:
        src = fitz.open(f); rct = src[0].rect
        if x + rct.width > pg.rect.width - 10:
            x, y, rowh = 20.0, y + rowh + 14, 0.0
        pg.show_pdf_page(fitz.Rect(x, y, x + rct.width, y + rct.height), src, 0)
        x += rct.width + 14; rowh = max(rowh, rct.height)
    doc.save(os.path.join(CHK, "rooms3d_5つ.pdf"))
