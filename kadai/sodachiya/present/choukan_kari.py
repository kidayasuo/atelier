# -*- coding: utf-8 -*-
"""2枚目の鳥瞰の仮の想像図（プレゼンの準備、10-29）

Rhino のレンダリング（rhino/choukan_render.py → rhino/out/choukan.png）が来るまでの仮。
3dm のメッシュ（model/sodachiya_exact_mesh.3dm）を、choukan_render.py と同じカメラの透視で、
面の向きによる簡単な陰影（11/5 10:00 の太陽＋空の明るさ、色はレイヤーの色）で描く。
奥行きの板（z バッファ）で前後を決める。線・ガラスの透け・影は無い（仮なので）。
使い方：python3 choukan_kari.py [出力.png]（既定 out/choukan_kari.png、mock.py が呼ぶ）
"""
import os, sys, re, math, json
import numpy as np
import rhino3dm as r

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUTP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out", "choukan_kari.png")

# カメラは rhino/choukan_render.py の CAM・TGT・LENS と同じ（そちらを読む）
_src = open(os.path.join(HERE, "rhino", "choukan_render.py"), encoding="utf-8").read()
def _const(name):
    return tuple(float(x) for x in re.search(r"^%s\s*=\s*\(([^)]*)\)" % name, _src, re.M).group(1).split(","))
CAM = np.array(_const("CAM")); TGT = np.array(_const("TGT"))
LENS = float(re.search(r"^LENS\s*=\s*([0-9.]+)", _src, re.M).group(1))
PX = (1754, 1240)                       # A4 横・150 dpi（仮なので）
SKY_TOP, SKY_BOT = np.array([0xC9, 0xDC, 0xEC]) / 255, np.array([0xEE, 0xF2, 0xF4]) / 255
CONTEXT = np.array([0xD9, 0xD6, 0xCF]) / 255
SKIP = re.compile(r"^(47_|16i_|16o_|0[01]_|91_|98_|3[1-4]_|5[2-4]_|5[67]_|59_|41_|42_|43|44_)")

# 太陽（11/5 10:00、京都）：方位約 147°（南東）、高度約 33°
_az, _al = math.radians(147.0), math.radians(33.0)
SUN = np.array([math.sin(_az) * math.cos(_al), math.cos(_az) * math.cos(_al), math.sin(_al)])

m = r.File3dm.Read(os.path.join(ROOT, "model", "sodachiya_exact_mesh.3dm"))
LAY = list(m.Layers)


MJ = json.load(open(os.path.join(ROOT, "data", "materials.json"), encoding="utf-8"))
def col_of(ln, c):
    """色：materials.json（レイヤーの頭で探す。厚さで分けるものは else）、無ければレイヤーの色。周りの建物は淡い灰"""
    if ln.startswith("04_"): return CONTEXT
    if ln.startswith("02_"): return np.array([0.72, 0.74, 0.70])
    for k, v in MJ["layers"]:
        if ln.startswith(k):
            nm = v if isinstance(v, str) else v.get("else")
            base = MJ["materials"].get(nm, {}).get("base")
            if base and "レイヤーの色" not in nm:
                return np.array(base[:3]) / 255.0
            break
    return np.array([c[0], c[1], c[2]]) / 255.0


tris, cols = [], []
def add(P, F, col):
    P = np.asarray(P, float); F = np.asarray(F, int)
    if len(F) == 0: return
    tris.append(P[F]); cols.append(np.repeat(col[None, :], len(F), 0))


def mesh_arrays(g):
    V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
    F = []
    for i in range(len(g.Faces)):
        f = g.Faces[i]
        F.append((f[0], f[1], f[2]))
        if f[3] != f[2]: F.append((f[0], f[2], f[3]))
    return V, F


def curve_pts(c, n=24):
    d = c.Domain
    return np.array([[p.X, p.Y, p.Z] for p in (c.PointAt(d.T0 + (d.T1 - d.T0) * k / n) for k in range(n + 1))])


def prism(A, B):
    """二つの同じ点数の輪（A・B）の側面と蓋の三角"""
    n = len(A); P = np.vstack([A, B]); F = []
    for k in range(n - 1):
        F += [(k, k + 1, n + k + 1), (k, n + k + 1, n + k)]
    for k in range(1, n - 2):
        F += [(0, k, k + 1), (n, n + k, n + k + 1)]
    return P, F


def ellipsoid(bb, nu=14, nv=8):
    c = (np.array([bb.Min.X, bb.Min.Y, bb.Min.Z]) + np.array([bb.Max.X, bb.Max.Y, bb.Max.Z])) / 2
    rr = (np.array([bb.Max.X, bb.Max.Y, bb.Max.Z]) - np.array([bb.Min.X, bb.Min.Y, bb.Min.Z])) / 2
    P = []; F = []
    for j in range(nv + 1):
        v = math.pi * j / nv
        for i in range(nu):
            u = 2 * math.pi * i / nu
            P.append(c + rr * np.array([math.sin(v) * math.cos(u), math.sin(v) * math.sin(u), math.cos(v)]))
    for j in range(nv):
        for i in range(nu):
            a, b = j * nu + i, j * nu + (i + 1) % nu
            F += [(a, b, b + nu), (a, b + nu, a + nu)]
    return np.array(P), F


nobj = 0
for o in m.Objects:
    g = o.Geometry; lay = LAY[o.Attributes.LayerIndex]; ln = lay.Name
    if SKIP.match(ln): continue
    col = col_of(ln, lay.Color)
    try:
        if isinstance(g, r.Mesh):
            V, F = mesh_arrays(g)
            if ln.startswith("02_"):                      # 護岸：水・河川敷・石積み（配置図と同じ分け方）
                z0_, z1_ = V[:, 2].min(), V[:, 2].max()
                col = np.array([0.62, 0.76, 0.86]) if z1_ <= -5700 else (np.array([0.72, 0.80, 0.62]) if z1_ - z0_ < 800 and z1_ < -4000 else np.array([0.70, 0.68, 0.63]))
            add(V, F, col)
        elif isinstance(g, r.Extrusion):
            A = curve_pts(g.Profile3d(0, 0.0)); B = curve_pts(g.Profile3d(0, 1.0))
            P, F = prism(A, B); add(P, F, col)
        elif isinstance(g, r.Brep):
            bb = g.GetBoundingBox()
            P, F = ellipsoid(bb); add(P, F, col)
        else:
            continue
        nobj += 1
    except Exception:
        continue
# 地面（川の水面より下に一枚。周りの道と敷地の地の色）
G_ = 400000.0
add(np.array([[CAM[0] - G_, CAM[1] - G_, -6200], [CAM[0] + G_, CAM[1] - G_, -6200], [CAM[0] + G_, CAM[1] + G_, -6200], [CAM[0] - G_, CAM[1] + G_, -6200]]),
    [(0, 1, 2), (0, 2, 3)], np.array([0.84, 0.83, 0.78]))
# 小竹薮公園（3dm には線だけ）：地の上に淡い緑
try:
    sys.path.insert(0, os.path.join(ROOT, "scripts")); import garden_common as GC
    pk = np.array(GC.PARK.exterior.coords)[:-1] * 1000
    add(np.c_[pk, np.full(len(pk), 20.0)], [(0, k, k + 1) for k in range(1, len(pk) - 1)], np.array([0.72, 0.82, 0.60]))
except Exception as e:
    print("公園：", e)
T = np.concatenate(tris); C = np.concatenate(cols)

# 透視（カメラの座標へ）
fwd = TGT - CAM; fwd /= np.linalg.norm(fwd)
rgt = np.cross(fwd, [0, 0, 1.0]); rgt /= np.linalg.norm(rgt)
up = np.cross(rgt, fwd)
Q = T - CAM
x, y, z = Q @ rgt, Q @ up, Q @ fwd
f_ = (PX[0] / 2) / (18.0 / LENS)        # 35 mm 換算：横 36 mm
keep = (z > 1000).all(1)
nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0])
ln_ = np.linalg.norm(nrm, axis=1); keep &= ln_ > 1e-6
nrm = nrm / np.maximum(ln_, 1e-9)[:, None]
cen = T.mean(1)
nrm *= np.where(((CAM - cen) * nrm).sum(1) < 0, -1, 1)[:, None]   # カメラの側へ向ける
sx = PX[0] / 2 + f_ * x / np.maximum(z, 1); sy = PX[1] / 2 - f_ * y / np.maximum(z, 1)
keep &= ~((sx < -50).all(1) | (sx > PX[0] + 50).all(1) | (sy < -50).all(1) | (sy > PX[1] + 50).all(1))
lam = np.clip(nrm @ SUN, 0, 1); sky = 0.5 + 0.5 * nrm[:, 2]
shade = 0.42 + 0.48 * lam + 0.18 * sky
Cs = np.clip(C * shade[:, None], 0, 1)
# 奥行きの板（z バッファ）で描く。2倍の大きさで描いて縮める（ぎざぎざを減らす）
SS = 2
Wz, Hz = PX[0] * SS, PX[1] * SS
sxs, sys_ = sx * SS, sy * SS
img = np.zeros((Hz, Wz, 3))
yy_ = np.linspace(0, 1, Hz)[:, None, None]
img[:] = SKY_TOP + (SKY_BOT - SKY_TOP) * yy_
zb = np.full((Hz, Wz), np.inf)
idx = np.where(keep)[0]
x0 = np.clip(np.floor(sxs[idx].min(1)), 0, Wz - 1).astype(int); x1 = np.clip(np.ceil(sxs[idx].max(1)), 0, Wz - 1).astype(int)
y0 = np.clip(np.floor(sys_[idx].min(1)), 0, Hz - 1).astype(int); y1 = np.clip(np.ceil(sys_[idx].max(1)), 0, Hz - 1).astype(int)
for k, t in enumerate(idx):
    if x1[k] < x0[k] or y1[k] < y0[k]: continue
    ax_, ay_, az_ = sxs[t], sys_[t], z[t]
    X, Y = np.meshgrid(np.arange(x0[k], x1[k] + 1) + 0.5, np.arange(y0[k], y1[k] + 1) + 0.5)
    d = (ay_[1] - ay_[2]) * (ax_[0] - ax_[2]) + (ax_[2] - ax_[1]) * (ay_[0] - ay_[2])
    if abs(d) < 1e-9: continue
    l0 = ((ay_[1] - ay_[2]) * (X - ax_[2]) + (ax_[2] - ax_[1]) * (Y - ay_[2])) / d
    l1 = ((ay_[2] - ay_[0]) * (X - ax_[2]) + (ax_[0] - ax_[2]) * (Y - ay_[2])) / d
    l2 = 1 - l0 - l1
    ins = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
    if not ins.any(): continue
    zz = 1.0 / (l0 / az_[0] + l1 / az_[1] + l2 / az_[2])      # 透視で正しい奥行き
    sub = zb[y0[k]:y1[k] + 1, x0[k]:x1[k] + 1]
    w_ = ins & (zz < sub)
    sub[w_] = zz[w_]
    img[y0[k]:y1[k] + 1, x0[k]:x1[k] + 1][w_] = Cs[t]
from PIL import Image
im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).resize(PX, Image.LANCZOS)
os.makedirs(os.path.dirname(OUTP), exist_ok=True)
im.save(OUTP)
print("choukan_kari:", OUTP, "物", nobj, "三角", len(idx), "カメラ", CAM.tolist(), "→", TGT.tolist(), "レンズ", LENS)
