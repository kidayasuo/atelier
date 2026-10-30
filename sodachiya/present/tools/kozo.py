"""育ち舎　構造の図（6枚目に貼る素材）：架構の軸測図＋1階の耐力壁の分布（プレゼンの準備 10-30）

ユーザー（10-30）：「架構、耐力壁の分布がわかるように。計算は不要。南の軒など細かいところは不要。」
- 左：建物全体の架構の軸測図（南西の上から、平行投影）。柱・梁・桁・2階の床梁は薄い面と細い線、耐力壁を色で。
  屋根・床・家具・ガラス・母屋・垂木・大和張り・南の軒の鋼の骨・光の筋のつなぎは描かない。
- 右：1階の耐力壁の分布（1/600、配置図と同じ向き：3dm の xy を VIEW_ROT 回して高野川の辺が下）。
- 耐力壁（決定事項 本館11〜15・66行、西館25〜26行）：
  本館　南北＝西の外壁・縁側の杉の壁（19か所）、東西＝北の妻（南の妻は垂れ壁と袖壁を架構1と一体の門型、淡く）。
  　　　東西は架構1〜20（柱と梁の門型）が受ける。間仕切りは構造にしない。
  西館　西の面・北西の斜め・南北の妻の外壁（窓を含めて合板で通す）、階段の箱（u30〜33.9）。東の面は耐力壁にしない。
  色は壁の向きで分ける（南北＝桁の方向に効く、東西＝梁間に効く、斜め＝両方）。
- 3dm：本館の外壁は 17（西・南北の妻・縁側の壁がひとつのメッシュ）、西館の外壁は 21（ひとつのメッシュ）なので、
  面ごとに本館の (u, v)（model/build/south/uv.py）で振り分ける。17 の v1.6 の帯（越屋根の西の立ち上がり）は描かない。
  階段の箱は 24 のうち名前が「階段の箱の壁」の物。

python3 sodachiya/present/tools/kozo.py [確認用の png]  →  present/sozai/18_構造_架構と耐力壁.pdf
"""
import os, sys, math, json
import numpy as np
import rhino3dm as r
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.colors import to_rgb
from scipy.spatial import ConvexHull

HERE = os.path.dirname(os.path.abspath(__file__))
SOD = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(SOD, "scripts"))
import fonts42  # noqa: F401,E402　文字は Type42（TrueType に変えた Noto）
sys.path.insert(0, os.path.join(SOD, "model", "build", "south"))
from uv import uv, xy  # noqa: E402

OUT = os.path.join(SOD, "present", "sozai", "18_構造_架構と耐力壁.pdf")
PNG = sys.argv[1] if len(sys.argv) > 1 else None

W, H = 380.0, 150.0                     # 貼る枠（A1の紙の mm）
INK = "#222222"
C_MEM = "#EEEAE3"                       # 架構の面
C_MEM_E = "#3A3A3A"                     # 架構の線
C_NS = "#D24A2A"                        # 南北（桁の方向）に効く耐力壁
C_EW = "#2E6DB4"                        # 東西（梁間）に効く耐力壁
C_DG = "#8A4FB5"                        # 斜めの壁（両方向）
C_PT = "#9DB8DA"                        # 南の妻の垂れ壁・袖壁（架構1と一体の門型）
WALL_C = {"NS": C_NS, "EW": C_EW, "DG": C_DG, "PT": C_PT}
FS = 8.5                                # 注・凡例の字（pt）
FSL = 9.0                               # 図の中の名前（pt）

# ---------------------------------------------------------------- 3dm
m = r.File3dm.Read(os.path.join(SOD, "model", "sodachiya_exact_mesh.3dm"))
lname = {l.Index: l.Name for l in m.Layers}
VIEW_ROT = json.load(open(os.path.join(SOD, "data", "garden.json"), encoding="utf-8"))["VIEW_ROT"]["deg"]

MEMBER_LAYERS = ("11a_", "11b_", "11c_", "22a_", "22b_", "22c_", "22d_")
P0 = np.r_[xy(28.5, -1.0), 0.0] / 1000          # 軸測図の原点（m）


def sample(c, n=40):
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


def mesh_faces(g):
    V = np.array([(p.X, p.Y, p.Z) for p in g.Vertices]) / 1000
    F = []
    for i in range(len(g.Faces)):
        f = g.Faces[i]
        F.append([f[0], f[1], f[2]] if f[3] == f[2] else [f[0], f[1], f[2], f[3]])
    return V, F


def feature_edges(V, F, ang=25.0):
    """面の向きが ang 度より折れる辺と、片側にしか面の無い辺"""
    nrm = []
    for f in F:
        P = V[f]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if len(f) == 4:
            n = n + np.cross(P[2] - P[0], P[3] - P[0])
        nl = np.linalg.norm(n)
        nrm.append(n / nl if nl > 0 else n)
    key = np.round(V, 4)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.ravel()
    E = {}
    for fi, f in enumerate(F):
        for a, b in zip(f, f[1:] + f[:1]):
            k = tuple(sorted((inv[a], inv[b])))
            if k[0] == k[1]:
                continue
            E.setdefault(k, [a, b, []])[2].append(fi)
    out = []
    ca = math.cos(math.radians(ang))
    for a, b, fs in E.values():
        if len(fs) == 1 or any(abs(float(nrm[fs[0]] @ nrm[j])) < ca for j in fs[1:]):
            out.append((V[a], V[b]))
    return nrm, out


def prism(g):
    """押し出し（柱・梁・桁）→ 面のリストと、描く辺"""
    A = sample(g.Profile3d(0, 0.0))
    B = sample(g.Profile3d(0, 1.0))
    n = min(len(A), len(B))
    A, B = A[:n], B[:n]
    faces = [A, B[::-1]] + [np.array([A[i], A[(i + 1) % n], B[(i + 1) % n], B[i]]) for i in range(n)]
    edges = [(A[i], A[(i + 1) % n]) for i in range(n)] + [(B[i], B[(i + 1) % n]) for i in range(n)]
    if n <= 12:                                  # 角の立った断面（柱・桁）は長手の辺も
        edges += [(A[i], B[i]) for i in range(n)]
    return faces, edges


members = []        # (面, 辺, 層)
for o in m.Objects:
    ln = lname[o.Attributes.LayerIndex]
    if not ln.startswith(MEMBER_LAYERS):
        continue
    g = o.Geometry
    if isinstance(g, r.Extrusion):
        f, e = prism(g)
    elif isinstance(g, r.Mesh):
        V, F = mesh_faces(g)
        f = [V[ff] for ff in F]
        _, e = feature_edges(V, F)
    else:
        continue
    members.append((f, e, ln))


def u_dir(u, v):
    a, b = xy(u - 0.25, v), xy(u + 0.25, v)
    t = (b - a) / np.linalg.norm(b - a)
    return t


def cls_honkan(u, v, z):
    if v > 13.0:
        return "NS"                     # 縁側の杉の壁
    if u > 57.1:
        return "EW"                     # 北の妻
    if u < 0.3:
        return "PT"                     # 南の妻（垂れ壁・袖壁、架構1と一体の門型）
    if v < 0.15:
        return "NS"                     # 西の外壁
    return None                         # v1.6 の帯（越屋根の西の立ち上がり）は構造でない


def cls_nishi(u, v, z, n):
    if u >= 50.7:
        return "EW"                     # 北の妻
    if u <= 21.6 and v > -10.0:
        return "EW"                     # 南の妻
    if v > -1.6:
        return None                     # 東の面（耐力壁にしない）
    if v < -12.0 and 24.0 < u < 41.8:
        return "NS"                     # 西の面（両面）
    if u > 42.6 and v > -14.6:
        return "DG"                     # 北西の斜め
    # 角の丸み：面の向きで
    t = u_dir(u, v)
    c = abs(float(n[:2] @ t)) / max(np.linalg.norm(n[:2]), 1e-9) if np.linalg.norm(n[:2]) > 0.3 else None
    if c is None:
        return "NS"
    return "EW" if c > 0.7 else "NS"            # 南西の角の丸み：南の妻と西の面に分ける


walls = []          # (面, 色の分類, 辺のリスト)
wall_cut = []       # 平面の切断に使う三角形 (V3, 分類, 切る高さ)


def add_wall_mesh(g, fn, zcut):
    V, F = mesh_faces(g)
    nrm, edges = feature_edges(V, F)
    cls_f = []
    for fi, f in enumerate(F):
        c = V[f].mean(0)
        u, v = uv(c[0] * 1000, c[1] * 1000)
        k = fn(u, v, c[2], nrm[fi])
        cls_f.append(k)
        if k:
            walls.append((V[f], k))
            P = V[f]
            for tri in ([P[0], P[1], P[2]],) + (([P[0], P[2], P[3]],) if len(f) == 4 else ()):
                wall_cut.append((np.array(tri), k, zcut))
    # 辺はそばの面の分類で
    for a, b in edges:
        c = (a + b) / 2
        u, v = uv(c[0] * 1000, c[1] * 1000)
        k = fn(u, v, c[2], np.array([0.0, 0.0, 1.0]))
        if k:
            walls.append((np.array([a, b]), "edge:" + k))


for o in m.Objects:
    ln = lname[o.Attributes.LayerIndex]
    g = o.Geometry
    if ln.startswith("17_") and isinstance(g, r.Mesh):
        add_wall_mesh(g, lambda u, v, z, n: cls_honkan(u, v, z), 1.0)
    elif ln.startswith("21_") and isinstance(g, r.Mesh):
        add_wall_mesh(g, cls_nishi, 0.05)
    elif ln.startswith("24_") and (o.Attributes.Name or "").startswith("階段の箱の壁") and isinstance(g, r.Mesh):
        def fn(u, v, z, n):
            t = u_dir(u, v)
            nh = n[:2]
            if np.linalg.norm(nh) < 0.3:     # 上下の面：箱の南北の面か東西の面か、位置で
                return "EW" if (u < 30.2 or u > 33.7) else "NS"
            return "EW" if abs(float(nh @ t)) / np.linalg.norm(nh) > 0.7 else "NS"
        add_wall_mesh(g, fn, 1.0)

# ---------------------------------------------------------------- 軸測図（南西の上から、平行投影）
AZ, EL = math.radians(225.0), math.radians(33.0)       # 見る人の方角（3dm の +Y を北）、見下ろす角
CAM = np.array([math.sin(AZ) * math.cos(EL), math.cos(AZ) * math.cos(EL), math.sin(EL)])
FWD = -CAM
RIGHT = np.cross(FWD, [0, 0, 1.0]); RIGHT /= np.linalg.norm(RIGHT)
UP = np.cross(RIGHT, FWD)
LIGHT = np.array([-0.35, -0.55, 0.76]); LIGHT /= np.linalg.norm(LIGHT)


def pj(P):
    Q = np.atleast_2d(P) - P0
    return np.c_[Q @ RIGHT, Q @ UP]


def dep(P):
    return float((np.atleast_2d(P) - P0).mean(0) @ CAM)


def shade(col, P):
    if len(P) < 3:
        return to_rgb(col)
    n = np.cross(P[1] - P[0], P[2] - P[0])
    nl = np.linalg.norm(n)
    k = abs(float(n @ LIGHT)) / nl if nl > 0 else 0.5
    c = np.array(to_rgb(col))
    return tuple(np.clip(c * (0.82 + 0.18 * k), 0, 1))


items = []          # (深さ, 2D, 面の色, 線の色, 線の太さ)
for faces, edges, ln in members:
    for P in faces:
        items.append((dep(P), pj(P), shade(C_MEM, P) + (1.0,), "none", 0.0))
    for a, b in edges:
        items.append((dep(np.array([a, b])) + 0.02, pj(np.array([a, b])), "none", C_MEM_E, 0.18))
for P, k in walls:
    if k.startswith("edge:"):
        k = k[5:]
        cc = tuple(np.array(to_rgb(WALL_C[k])) * 0.72)
        items.append((dep(P) + 0.03, pj(P), "none", cc + ((0.55 if k == "PT" else 0.9),), 0.25 if k != "PT" else 0.18))
    else:
        a = 0.28 if k == "PT" else 0.55
        items.append((dep(P), pj(P), shade(WALL_C[k], P) + (a,), "none", 0.0))
items.sort(key=lambda t: t[0])

allp = np.vstack([t[1] for t in items])
lo, hi = allp.min(0), allp.max(0)
# 割付（mm）：軸測図は左（左に名前の余白）、右の列に平面と凡例
AX_L = 20.0
sc = min(244.0 / (hi[0] - lo[0]), (H - 6) / (hi[1] - lo[1]))     # mm / m
ox = AX_L - lo[0] * sc
oy = 3 - lo[1] * sc
COL_X = AX_L + (hi[0] - lo[0]) * sc + 8                           # 右の列の左端

def A2(Q):
    return np.c_[Q[:, 0] * sc + ox, Q[:, 1] * sc + oy]


fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal"); ax.axis("off")
pc = PolyCollection([A2(t[1]) for t in items], facecolors=[t[2] for t in items], edgecolors=[t[3] for t in items],
                    linewidths=[t[4] for t in items], closed=True, joinstyle="round", capstyle="round")
ax.add_collection(pc)


def P3(u, v, z):
    return np.r_[xy(u, v) / 1000, z]


def lab(u, v, z, s, dx, dy, ha="left", bold=False, size=FSL, color=INK, at=None):
    p = A2(pj(P3(u, v, z)))[0]
    t = (p[0] + dx, 7.0) if at == "bottom" else (at if at else (p[0] + dx, p[1] + dy))
    dy = t[1] - p[1]
    ax.plot([p[0], t[0]], [p[1], t[1] - (0.6 if dy > 0 else -1.6)], color=color, lw=0.3)
    ax.plot([p[0]], [p[1]], "o", ms=1.2, color=color)
    ax.text(t[0], t[1], s, fontsize=size, ha=ha, va="bottom" if dy > 0 else "top", color=color,
            fontweight="bold" if bold else "normal",
            bbox=dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=0.8))


def name(u, v, z, s, dx=0, dy=0):
    p = A2(pj(P3(u, v, z)))[0]
    ax.text(p[0] + dx, p[1] + dy, s, fontsize=12, fontweight="bold", ha="center", va="center", color=INK)


# ---------------------------------------------------------------- 1階の耐力壁の分布（1/600、高野川の辺が下）
PL = 1000.0 / 600.0                     # mm / m（1/400 では枠の高さ150 mm に入らないので1/600）
_rr = math.radians(VIEW_ROT)
_R = np.array([[math.cos(_rr), -math.sin(_rr)], [math.sin(_rr), math.cos(_rr)]])


def rp(P):
    return (np.atleast_2d(P)[:, :2]) @ _R.T


segs = {k: [] for k in WALL_C}
for T, k, h in wall_cut:
    s = T[:, 2] - h
    if s.min() > 0 or s.max() < 0:
        continue
    pts = []
    for i in range(3):
        a, b = T[i], T[(i + 1) % 3]
        sa, sb = a[2] - h, b[2] - h
        if (sa <= 0 < sb) or (sb <= 0 < sa):
            pts.append(a + (b - a) * sa / (sa - sb))
    if len(pts) == 2:
        segs[k].append(np.array(pts))

plan_cols, plan_beams = [], []
for o in m.Objects:
    ln = lname[o.Attributes.LayerIndex]
    g = o.Geometry
    if ln.startswith(("11a_", "22a_")) and isinstance(g, r.Extrusion):
        A_ = sample(g.Profile3d(0, 0.0)); B_ = sample(g.Profile3d(0, 1.0))
        if min(A_[:, 2].min(), B_[:, 2].min()) > 0.5:       # 2階だけの柱は描かない
            continue
        Q = np.vstack([A_, B_])[:, :2]
        plan_cols.append(Q[ConvexHull(Q).vertices])
    elif ln.startswith(("11b_", "22b_")) and isinstance(g, r.Extrusion):
        Q = np.vstack([sample(g.Profile3d(0, 0.0)), sample(g.Profile3d(0, 1.0))])[:, :2]
        plan_beams.append(Q[ConvexHull(Q).vertices])

allq = rp(np.vstack([s[:, :2] for L_ in segs.values() for s in L_] + plan_cols))
qlo, qhi = allq.min(0), allq.max(0)
PX0 = (COL_X + W - (qhi[0] - qlo[0]) * PL) / 2
PY0 = H - 4 - (qhi[1] - qlo[1]) * PL


def B2(P):
    Q = rp(P)
    return np.c_[(Q[:, 0] - qlo[0]) * PL + PX0, (Q[:, 1] - qlo[1]) * PL + PY0]


ax.add_collection(PolyCollection([B2(q) for q in plan_beams], facecolors="none", edgecolors="#9A9A9A", linewidths=0.2))
order = ["PT", "NS", "DG", "EW"]
for k in order:
    if segs[k]:
        ax.add_collection(LineCollection([B2(s) for s in segs[k]], colors=WALL_C[k],
                                         linewidths=0.9 if k == "PT" else 1.7, capstyle="butt"))
ax.add_collection(PolyCollection([B2(q) for q in plan_cols], facecolors=INK, edgecolors=INK, linewidths=0.15))

# 平面の注：方位と架構の番号
nv = np.array([0.0, 1.0]) @ _R.T
nx, ny = W - 14, H - 18                          # 平面の右上の空き
ax.annotate("", xy=(nx + nv[0] * 7, ny + nv[1] * 7), xytext=(nx, ny),
            arrowprops=dict(arrowstyle="-|>,head_length=0.5,head_width=0.22", lw=0.5, color=INK))
ax.text(nx + nv[0] * 9.2, ny + nv[1] * 9.2, "N", fontsize=FS, ha="center", va="center")
for fr, u, ha in ((1, -1.0, "right"), (20, 58.0, "left")):
    p = B2(np.r_[xy(u, 14.0)] / 1000)[0]
    ax.text(p[0], p[1], f"架構{fr}", fontsize=7.0, ha=ha, va="center", color="#555555")
ax.text(W - 3, H - 36, "1階　1/600", fontsize=FS, ha="right", va="center", color=INK)

# ---------------------------------------------------------------- 軸測図の名前と注
SEL = os.environ.get("KOZO_NOLABEL")
if not SEL:
    name(10.0, 18.0, 8.0, "本館")
    ax.text(AX_L + 4, H - 8, "西館", fontsize=12, fontweight="bold", ha="left", va="center", color=INK)
    lab(0.0, 12.0, 2.6, "架構1", -2, 16, ha="right")
    lab(57.0, 6.0, 4.1, "架構20", 8, 6)
    lab(39.0, 13.6, 2.8, "縁側の杉の壁（19か所）", 10, 8)
    lab(57.3, 10.0, 3.0, "北の妻", 10, 5)
    lab(0.0, 11.6, 1.2, "南の妻（門型）", 3, 0, at="bottom")
    lab(14.0, -0.35, 1.0, "西の外壁", 0, -10, ha="center")
    lab(46.0, -12.5, 1.0, "北西の斜め", 0, 0, ha="right", at=(AX_L - 2, 40))
    lab(51.0, -5.0, 5.0, "北の妻", 0, 0, ha="right", at=(AX_L - 2, 120))
    lab(29.0, -14.2, 0.8, "西の面（両面に合板）", 0, -12, ha="center")
    lab(21.0, -6.0, 1.5, "南の妻", 0, -14, ha="center")
    lab(32.5, -4.0, 1.2, "階段の箱", 0, 0, ha="center", at=(100.0, 20.0))

# 凡例と注（右の列、平面の下）
LX, LY = COL_X + 2, PY0 - 6
leg = [("NS", "南北（桁の方向）に効く耐力壁"), ("EW", "東西（梁間）に効く耐力壁"), ("DG", "斜めの壁（両方向に効く）"),
       ("PT", "南の妻の垂れ壁・袖壁（門型の一部）")]
y = LY
for k, s in leg:
    ax.add_patch(plt.Rectangle((LX, y - 1.6), 7.0, 3.2, fc=WALL_C[k], ec="none", alpha=0.85 if k != "PT" else 0.6))
    ax.text(LX + 9.0, y, s, fontsize=FS, va="center")
    y -= 5.2
ax.add_patch(plt.Rectangle((LX, y - 1.6), 7.0, 3.2, fc=C_MEM, ec=C_MEM_E, lw=0.3))
ax.text(LX + 9.0, y, "柱・梁・桁・2階の床梁（架構）", fontsize=FS, va="center")
y -= 7.0
notes = ["本館の東西は架構1〜20（柱と梁の門型）で受ける。",
         "間仕切りは構造にしない（動かせるように）。",
         "西館の外壁は窓を含めて構造用合板で通す。",
         "屋根は母屋の上の合板を水平構面に。"]
for s in notes:
    ax.text(LX, y, s, fontsize=FS - 0.5, va="center", color="#444444")
    y -= 4.0

fig.savefig(OUT)
if PNG:
    fig.savefig(PNG, dpi=1600 / (W / 25.4))
print(OUT)
