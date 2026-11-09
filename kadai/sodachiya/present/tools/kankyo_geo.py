"""断面C（空気の環境）・断面D（光の環境）の図のための形の測り（プレゼンの準備、11-01）。

3dm（model/sodachiya_exact_mesh.3dm）の物を、断面の面（drawings/<紙>_views.json の origin・right・view_dir）で切って、
断面の座標 h（右へ、西の柱の列 W から東へ mm）・z（FL ±0 から上へ mm）で返す。present/tools/saikou.py が使う。
測れない物は決定事項の値で代える（fallback、どれを代えたかは G["_fallback"] に）。
"""
import json, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))           # sodachiya/
MESH = os.path.join(ROOT, "model", "sodachiya_exact_mesh.3dm")
_M = {}


def load_view(paper, vname):
    vj = os.path.join(ROOT, "drawings", paper + "_views.json")
    return [v for v in json.load(open(vj, encoding="utf-8"))["views"] if v["name"] == vname][0]


def _objs():
    if "o" not in _M:
        import rhino3dm as r
        m = r.File3dm.Read(MESH)
        L = {i: l.Name for i, l in enumerate(m.Layers)}
        out = []
        for o in m.Objects:
            g = o.Geometry
            if isinstance(g, r.Mesh):
                P = np.array([(v.X, v.Y, v.Z) for v in g.Vertices])
                F = []
                for i in range(len(g.Faces)):
                    f = g.Faces[i]
                    F.append([f[0], f[1], f[2]] if f[2] == f[3] else [f[0], f[1], f[2], f[3]])
            elif isinstance(g, (r.Extrusion, r.Brep)):
                b = g.ToBrep(False) if isinstance(g, r.Extrusion) else g
                P = np.array([(b.Vertices[i].Location.X, b.Vertices[i].Location.Y, b.Vertices[i].Location.Z) for i in range(len(b.Vertices))])
                F = None
            else:
                continue
            if len(P):
                out.append((L[o.Attributes.LayerIndex], o.Attributes.Name or "", P, F))
        _M["o"] = out
    return _M["o"]


class Cut:
    def __init__(self, view):
        self.O, self.R, self.D = (np.array(view[k], float) for k in ("origin", "right", "view_dir"))

    def hdz(self, P):
        Q = P - self.O
        return Q @ self.R, Q @ self.D, P[:, 2]

    def pick(self, pre, name=None):
        pre = (pre,) if isinstance(pre, str) else pre
        return [(n, nm, P, F) for n, nm, P, F in _objs() if n.startswith(pre) and (name is None or name in nm)]

    def slice(self, pre, dc=50.0, name=None, zr=None, hr=None, per=False):
        """切り口の点（h, z）。per=True なら物ごとのリスト"""
        res = []
        for n, nm, P, F in self.pick(pre, name):
            if F is None:
                continue
            h, d, z = self.hdz(P)
            if d.max() < dc or d.min() > dc:
                continue
            pts = []
            for idx in F:
                for a, b in zip(idx, idx[1:] + idx[:1]):
                    da, db = d[a] - dc, d[b] - dc
                    if (da < 0) != (db < 0):
                        t = da / (da - db)
                        pts.append((h[a] + t * (h[b] - h[a]), z[a] + t * (z[b] - z[a])))
            if not pts:
                continue
            p = np.array(pts)
            if zr is not None and not (zr[0] <= p[:, 1].mean() <= zr[1]):
                continue
            if hr is not None and not (hr[0] <= p[:, 0].mean() <= hr[1]):
                continue
            res.append(p)
        if per:
            return res
        return np.vstack(res) if res else np.zeros((0, 2))

    def near(self, pre, d0, d1, name=None):
        """奥行き d0〜d1 にかかる物の頂点（h, z）の外接箱のリスト"""
        out = []
        for n, nm, P, F in self.pick(pre, name):
            h, d, z = self.hdz(P)
            if d.max() < d0 or d.min() > d1:
                continue
            out.append((h.min(), h.max(), z.min(), z.max(), d.mean()))
        return out


def _line(p, top=True):
    """切り口の点から、上面（top）か下面の直線 z = a h + b（h の幅 200 ごとの上端／下端に合わせる）"""
    h0, h1 = p[:, 0].min(), p[:, 0].max()
    bins = np.arange(h0, h1 + 200, 200)
    H, Z = [], []
    for a, b in zip(bins[:-1], bins[1:]):
        q = p[(p[:, 0] >= a) & (p[:, 0] < b)]
        if len(q):
            H.append(q[:, 0].mean()); Z.append(q[:, 1].max() if top else q[:, 1].min())
    k = np.polyfit(H, Z, 1)
    return dict(a=float(k[0]), b=float(k[1]), h0=float(h0), h1=float(h1))


def zl(L, h):
    return L["a"] * h + L["b"]


def _lineof(b):
    """帯の外接箱（西が低い）の上面の直線"""
    a = (b[3] - b[2]) / (b[1] - b[0])
    return dict(a=a, b=b[3] - a * b[1])


def louvers(h0, h1, zbase, pitch=104.0, w=120.0, ang=30.0):
    """板の中心（h, z）。板は東が高い ang°、幅 w。zbase(h)：板の下の縁の高さ＋半分の立ち上がり"""
    out, h = [], h0 + w / 2 * np.cos(np.radians(ang))
    while h < h1:
        out.append((float(h), float(zbase(h))))
        h += pitch
    return out


def measure(view, dc=50.0):
    C = Cut(view)
    G, fb = {}, []

    def bb(p):
        return (float(p[:, 0].min()), float(p[:, 0].max()), float(p[:, 1].min()), float(p[:, 1].max()))

    # ---- 西館
    p = C.slice("21_", dc)
    G["hWo"], G["hWe"] = (float(p[:, 0].min()), float(p[:, 0].max())) if len(p) else (-15000.0, -900.0)
    p = C.slice("20_", dc, name="野地")
    G["roofW"] = _line(p[p[:, 0] < -2800], top=True)
    p = C.slice("20r", dc)
    G["ceilW"] = _line(p, top=False) if len(p) else dict(G["roofW"], b=G["roofW"]["b"] - 330)
    nb = [b for b in C.near("20t", dc - 1, dc + 1, name="棟のガラスの帯")]
    if nb:
        G["band"] = (min(b[0] for b in nb), max(b[1] for b in nb), min(b[2] for b in nb), max(b[3] for b in nb))
    else:
        G["band"] = (-2575.0, -550.0, 7780.0, 8350.0); fb.append("棟のガラスの帯")
    # ルーバー（幅120・ピッチ104・東が高い30°）：板は曲がった物や長い物なので、帯・蓋の範囲から並べる（決定事項_西館・本館）
    G["band_louvers"] = louvers(G["band"][0] + 25, G["band"][1] - 60, lambda h: zl(_lineof(G["band"]), h) + 10 + 30)
    p = C.slice("19", dc, name="排気のスリット")
    G["slit"] = bb(p) if len(p) else (-2710.0, -2560.0, 7520.0, 7590.0)
    p = C.slice("19", dc, zr=(4000, 7000), hr=(G["hWe"] - 400, G["hWe"] + 200))
    if len(p):
        G["hiwin"] = bb(p)
    else:
        G["hiwin"] = (G["hWe"] - 90, G["hWe"] - 60, 4750.0, 5950.0); fb.append("東の高窓")
    p = C.slice("20t", dc, zr=(3500, 5200))
    G["gaplid"] = bb(p) if len(p) else (-918.0, -350.0, 4496.0, 4604.0)
    p = C.slice("31_", dc)
    G["yugi_floor"] = bb(p) if len(p) else None
    # ---- 本館
    p = C.slice("50a", dc)
    G["lid"] = bb(p) if len(p) else (-350.0, 1950.0, 4264.0, 4515.0)
    G["lid_louvers"] = louvers(G["lid"][0] + 20, G["lid"][1] - 20, lambda h: G["lid"][3] + 10 + 30)
    p = C.slice("10_", dc, name="野地")
    G["roofM"] = _line(p, top=True)
    G["eave"] = (float(p[:, 0].max()), float(p[p[:, 0] > p[:, 0].max() - 40, 1].min()), float(p[p[:, 0] > p[:, 0].max() - 40, 1].max()))
    p = C.slice("10r", dc)
    G["ceilM"] = _line(p, top=False) if len(p) else dict(G["roofM"], b=G["roofM"]["b"] - 250)
    p = C.slice("49", dc, zr=(2300, 4200), hr=(1300, 1900))
    if len(p):
        G["lattice"] = bb(p)
    else:
        G["lattice"] = (1586.0, 1616.0, 2400.0, 3560.0); fb.append("西の壁の上の縦格子")
    p = C.slice("12_", dc)
    G["floor"] = bb(p) if len(p) else (-200.0, 13500.0, -450.0, -10.0)
    p = C.slice("16d", dc)
    if not len(p):
        p = C.slice("16o", dc)
    G["door"] = bb(p) if len(p) else (13437.0, 13449.0, 90.0, 2315.0)
    p = C.slice("16b", dc)
    G["garari"] = bb(p) if len(p) else (13508.0, 13528.0, -130.0, -20.0)
    p = C.slice("14_", dc)
    G["engawa_out"] = bb(p) if len(p) else (13500.0, 15000.0, -300.0, -150.0)
    fans = C.near("58_", -2500, 2500)
    if fans:
        rod = [f for f in fans if f[3] - f[2] > 200]
        h_ = (rod or fans)[0][0]
        G["fan"] = (float(h_), 2800.0)
    else:
        G["fan"] = (830.0, 2800.0); fb.append("天井扇")
    G["_fallback"] = fb
    return G
