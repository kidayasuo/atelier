# approachA.py の外構を 3dm（mm、sodachiya_exact.3dm と同じ座標）に書き出す。取り込み用（Rhino の Import）。
# z=0 は 3dm の敷地面。高さは m で書いて mm に直す。
import os, sys, importlib.util, math
import numpy as np
import rhino3dm as r
HERE = os.path.dirname(os.path.abspath(__file__))
import tempfile
os.environ.setdefault("OUT", tempfile.mkdtemp())
spec = importlib.util.spec_from_file_location("A", os.path.join(HERE, "approachA.py")); A = importlib.util.module_from_spec(spec); spec.loader.exec_module(A)
OUTF = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "model", "sodachiya_approachA_layers.3dm")

m = r.File3dm(); m.Settings.ModelUnitSystem = r.UnitSystem.Millimeters
LAY = {}
def layer(name, rgb):
    l = r.Layer(); l.Name = name; l.Color = (*rgb, 255); LAY[name] = m.Layers.Add(l)
for n, c in [("70_外構_生垣・塀・格子", (90, 122, 58)), ("71_外構_屋根（木戸・手水・下屋）", (80, 80, 80)), ("72_外構_柱", (20, 20, 20)),
             ("73_外構_アーチの棚", (122, 90, 54)), ("74_外構_駐車・駐輪・バンプ", (130, 130, 130)), ("75_外構_ひろばの家具", (185, 142, 94)),
             ("76_外構_舗装の区分", (200, 190, 170)), ("77_外構_樹木", (90, 140, 60)),
             ("78_外構_みなみのさんかく（丘・小径・砂場・水）", (176, 138, 90)), ("79_外構_みなみのさんかく（緑の目隠しの株）", (110, 154, 78)),
             # 一つのレイヤーには一つの素材（設計監修 10-27）：葉（樹冠・生垣・植え込み）は英字付きの別のレイヤーへ
             ("70h_外構_生垣（葉）", (90, 140, 60)), ("77c_外構_樹冠・植え込み・苔（葉）", (110, 160, 80)),
             ("79c_外構_みなみのさんかく_ハーブ・緑の目隠し（葉）", (120, 170, 90)),
             ("75t_外構_地中の雨水槽", (120, 120, 120)), ("75s_外構_石の受け桝", (150, 146, 138)),
             # 公園の中身（ユーザー 10-29）：一つのレイヤーに一つの素材
             ("74p_外構_公園の鉄の物（鉄棒・柵・車止め）", (60, 60, 64)), ("74s_外構_公園のすべり台", (200, 204, 208)),
             ("75p_外構_公園の木のベンチ", (170, 128, 86)),
             ("76g_外構_公園の芝生", (120, 160, 84)), ("74a_外構_駐車の舗装（アスファルト）", (62, 62, 64)), ("74w_外構_駐車の白線", (236, 236, 232)),
             ("76b_外構_歩く舗装（ベージュ）", (204, 186, 156)), ("78a_外構_ひろばの真砂土", (190, 172, 140)), ("76s_外構_土（植栽・砂利・すき間）", (140, 116, 88)), ("73c_外構_アーチの棚のムベ（葉）", (80, 130, 60))]:
    layer(n, c)
def attr(name):
    a = r.ObjectAttributes(); a.LayerIndex = LAY[name]; return a
MM = 1000.0
def P3(p, z=0.0): return r.Point3d(p[0] * MM, p[1] * MM, z * MM)
def pl(pts, z=0.0, close=False):
    pts = list(pts) + ([pts[0]] if close else [])
    return r.Polyline([P3(p, z) for p in pts]).ToNurbsCurve()
def add_curve(pts, lay, z=0.0, close=False):
    m.Objects.AddCurve(pl(pts, z, close), attr(lay))
def up(c, h, cap):                                             # Extrusion.Create follows the curve's normal: force +Z
    e = r.Extrusion.Create(c, h * MM, cap)
    z0 = c.PointAtStart.Z
    if e and e.GetBoundingBox().Max.Z < z0 + h * MM * 0.5:
        e = r.Extrusion.Create(c, -h * MM, cap)
    return e
def wall(pts, h, lay, z0=0.0):                                 # vertical strip along a polyline
    e = up(pl(pts, z0), h, False)
    if e: m.Objects.AddExtrusion(e, attr(lay))
def slab(pts, z0, t, lay):                                     # closed outline extruded upward t
    e = up(pl(pts, z0, True), t, True)
    if e: m.Objects.AddExtrusion(e, attr(lay))
def smooth_outline(pts, z=0.0, tol=0.001, corner=15.0):        # 細かい折れ線（円弧を分けた点）を、直線と円弧の閉じた PolyCurve にする（10-28）
    q = [tuple(p[:2]) for p in pts]
    if q[0] == q[-1]: q = q[:-1]
    n = len(q)
    def turn(i):
        a, b, c = q[i - 1], q[i], q[(i + 1) % n]
        d = math.degrees(math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(b[1] - a[1], b[0] - a[0]))
        return abs((d + 180) % 360 - 180)
    cs = [i for i in range(n) if turn(i) >= corner] or [0]
    q = q[cs[0]:] + q[:cs[0]]; cs = [(c - cs[0]) % n for c in cs] + [n]; q = q + [q[0]]
    def seg_dev(i, j):                                          # line i→j: max distance of the points between
        a, b = np.array(q[i]), np.array(q[j]); d = b - a; L = np.hypot(*d)
        if L < 1e-9: return 0.0, None
        return max([abs(d[0] * (q[k][1] - a[1]) - d[1] * (q[k][0] - a[0])) / L for k in range(i + 1, j)] + [0.0]), None
    def arc_dev(i, j):                                          # 3-point arc through i, the middle point (by length) and j
        if j - i < 2: return 1e9, None
        cum = np.concatenate([[0], np.cumsum([math.dist(q[k], q[k + 1]) for k in range(i, j)])])
        k = i + 1 + int(np.argmin(np.abs(cum[1:-1] - cum[-1] / 2)))
        (ax, ay), (bx, by), (cx, cy) = q[i], q[k], q[j]
        D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(D) < 1e-12: return 1e9, None
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / D
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / D
        R = math.hypot(ax - ux, ay - uy)
        dev = max(abs(math.hypot(q[m_][0] - ux, q[m_][1] - uy) - R) for m_ in range(i, j + 1))
        sag = max(abs(math.hypot((q[m_][0] + q[m_ + 1][0]) / 2 - ux, (q[m_][1] + q[m_ + 1][1]) / 2 - uy) - R) for m_ in range(i, j))
        return (dev if sag <= 3 * tol else 1e9), k                # 点の間で弧が折れ線から離れすぎない（弦の中点で 3 mm まで）
    pc = r.PolyCurve()
    for s0, s1 in zip(cs[:-1], cs[1:]):
        i = s0
        while i < s1:
            j = i + 1; kind = ("L", None)
            for jj in range(i + 1, s1 + 1):
                if seg_dev(i, jj)[0] <= tol: j, kind = jj, ("L", None)
                else:
                    d, k = arc_dev(i, jj)
                    if d <= tol: j, kind = jj, ("A", k)
                    elif jj - i > 2: break
            if kind[0] == "L": pc.Append(r.LineCurve(P3(q[i], z), P3(q[j], z)))
            else: pc.Append(r.Arc(P3(q[i], z), P3(q[kind[1]], z), P3(q[j], z)))
            i = j
    return pc
def slab_smooth(pts, z0, t, lay):                              # slab() の、輪郭を直線と円弧にした版
    e = up(smooth_outline(pts, z0), t, True)
    if e: m.Objects.AddExtrusion(e, attr(lay))
POSTS = []                                                       # 柱の中心と半径（塀の板を柱の間に納めるため、10-27）
def post(p, h, s=0.12, lay="72_外構_柱"):
    x, y = p; q = [(x - s / 2, y - s / 2), (x + s / 2, y - s / 2), (x + s / 2, y + s / 2), (x - s / 2, y + s / 2)]
    slab(q, 0, h, lay); POSTS.append(((x, y), s * 0.71))
FENCES = []                                                      # 塀と木戸の扉は柱を全部置いてから最後に作る
class _Y:
    @staticmethod
    def to3dm(slab_, p0, p1, lay, h=None, foot=None): FENCES.append((p0, p1, lay, h, foot))
def coords(g):
    gs = [g] if g.geom_type == "Polygon" else list(g.geoms)
    return [list(q.exterior.coords)[:-1] for q in gs if q.geom_type == "Polygon"]
P, Q, srect, E, W = A.P, A.Q, A.srect, A.E, A.W

# 70 hedges (h1.2), board fence (h1.8), lattice (h1.8)
for h in A.HEDGE: wall(Q(h), 1.2, "70h_外構_生垣（葉）")
wall([P(A.S_PATH0, A.HEDGE_D), P(*A.TIP)], 1.2, "70h_外構_生垣（葉）")
_pd0, _pd = A.STAFF_BIKE["pocket"][2], A.STAFF_BIKE["pocket"][3]; _g0, _g1 = A.STAFF_BIKE["gate"]
import yamato
_Y.to3dm(slab, P(22.7, _pd), P(_g0, _pd), "70_外構_生垣・塀・格子")          # board fence: east side of the staff bike pocket
_Y.to3dm(slab, P(_g1, _pd), P(A.SX, _pd), "70_外構_生垣・塀・格子")
_Y.to3dm(slab, P(_g0 + 0.03, _pd), P(_g1 - 0.03, _pd), "72_外構_柱")                          # staff gate leaf (closed)
for _k, _s in enumerate(A.STAFF_POS):                                                    # staff bikes (outlines on the ground)
    _d0 = _pd0 + (0.05 if _k % 2 == 0 else 0.2)
    add_curve([P(_s - 0.15, _d0), P(_s + 0.15, _d0), P(_s + 0.15, _d0 + 1.75), P(_s - 0.15, _d0 + 1.75)], "74_外構_駐車・駐輪・バンプ", close=True)
slab(srect(*A.WOOD), 0, 1.2, "75_外構_ひろばの家具")                                      # wood rack next to the kamado
import yamato                                                                            # 塀と木戸はすべてスギの大和張り（ユーザー 10-27）
L70 = "70_外構_生垣・塀・格子"
_Y.to3dm(slab, E(A.GA1, 0), A.FENCE_END, L70)                                         # 公園側の塀
_Y.to3dm(slab, E(0, 0), E(A.GA0, 0), L70)
_Y.to3dm(slab, E(A.GA0 + 0.02, 0), E(A.GA1 - 0.02, 0), "72_外構_柱")                   # 公園の木戸の扉（閉じた位置）
# 71 roofs (flat placeholders, 100 thick): kido 2.6, lean-to 2.6, back-door canopy 2.6
# 手水の屋根は無し（ユーザー 10-30）
import north_common as _NC0
NC_WS = _NC0.WS
slab_smooth(list(A.LEAN_ROOF.exterior.coords)[:-1], 2.6, 0.1, "71_外構_屋根（木戸・手水・下屋）")      # 下屋＋南西の丸みへの回り込み（勝手口の庇は外した、10-24）
for _g in getattr(A.LEAN_GUTTER, "geoms", [A.LEAN_GUTTER]): add_curve(list(_g.coords), "75_外構_ひろばの家具", 2.6)   # 下屋の軒樋
# 72 posts
for p in A.LEAN_POSTS: post(p, 2.6)
# 73 arched trellis: posts at the frames, 桁, arched beams every ~1.5 m (spring 2.25, rise 0.28) to the wall
PG_D = A.HEDGE_D + A.HW + 0.15
s_fr = [A.inv(W(u, 0))[0] for u in (0.75, 3, 6, 9)]; s_a, s_b = s_fr[0], A.TEM[0]
for s in [s_a] + s_fr[1:] + [s_b]: post(P(s, PG_D), 2.25, 0.12, "73_外構_アーチの棚")
add_curve([P(s_a, PG_D), P(s_b, PG_D)], "73_外構_アーチの棚", 2.25)
n = round((s_b - s_a) / 1.5)
for s in np.linspace(s_a, s_b, n + 1):
    pts = []
    for t in np.linspace(0, 1, 13):
        d = PG_D + (A.WALL_D - PG_D) * t; p = P(s, d)
        pts.append(r.Point3d(p[0] * MM, p[1] * MM, (2.25 + 0.28 * math.sin(math.pi * t)) * MM))
    m.Objects.AddCurve(r.Polyline(pts).ToNurbsCurve(), attr("73_外構_アーチの棚"))
# 73c 小径のアーチの棚にムベ（ユーザー 10-29：ムベのアーチにムベを）：梁の上に葉の層（h2.30〜2.60）
slab([P(s_a, PG_D), P(s_b, PG_D), P(s_b, A.WALL_D), P(s_a, A.WALL_D)], 2.30, 0.30, "73c_外構_アーチの棚のムベ（葉）")
# 73 木戸の内側の三角のムベの棚（小径の棚の続き、10-24）：柱・桁 h2.25、梁は 1.5 ごとに弓なり
for p in A.TRI_POSTS: post(p, 2.25, 0.12, "73_外構_アーチの棚")
for g in A.TRI_GIRDERS: add_curve(g, "73_外構_アーチの棚", 2.25)
for b0, b1 in A.TRI_BEAMS:
    L_ = math.dist(b0, b1); rise = min(0.28, 0.12 * L_); pts = []
    for t in np.linspace(0, 1, 13):
        p = (b0[0] + (b1[0] - b0[0]) * t, b0[1] + (b1[1] - b0[1]) * t)
        pts.append(r.Point3d(p[0] * MM, p[1] * MM, (2.25 + rise * math.sin(math.pi * t)) * MM))
    m.Objects.AddCurve(r.Polyline(pts).ToNurbsCurve(), attr("73_外構_アーチの棚"))
# 73c 木戸の内側の三角の棚にもムベ（軒の下は屋根が覆うので葉は軒の外だけ、10-24）
_mube = A.TRI.difference(A.EAVE_S)
for _g in getattr(_mube, "geoms", [_mube]):
    if _g.area > 0.3: slab(list(_g.exterior.coords)[:-1], 2.30, 0.30, "73c_外構_アーチの棚のムベ（葉）")
# 74 parking, bump, bikes, curb cut
for k in range(3): add_curve(srect(7.2, 12.2, A.STALL_D0 + 2.5 * k, A.STALL_D0 + 2.5 * (k + 1)), "74_外構_駐車・駐輪・バンプ", close=True)
for k in range(2): add_curve(srect(17.7, 22.7, A.STALL_D0 + 2.5 * k, A.STALL_D0 + 2.5 * (k + 1)), "74_外構_駐車・駐輪・バンプ", close=True)
slab(srect(12.3, 17.6, *A.BUMP), 0, 0.05, "74a_外構_駐車の舗装（アスファルト）")      # スピードバンプ（地はアスファルト）
for _s in A.BUMP_STRIPES: slab(srect(_s, _s + 0.45, *A.BUMP), 0.05, 0.002, "74w_外構_駐車の白線")   # 横断歩道の縞（ユーザー 10-29）
add_curve(srect(A.SIDEWALK["s"][0], A.SIDEWALK["s"][1], *A.SIDEWALK["d"]), "76_外構_舗装の区分", close=True)   # 歩道（開放）
for kind, a, b in A.BIKES:
    q = srect(a, a + 0.7, b, b + 1.9) if kind == "d" else srect(a, a + 1.9, b, b + A.BIKE_ROW2["pitch"])
    add_curve(q, "74_外構_駐車・駐輪・バンプ", close=True)
# 75 plaza furniture
for b in A.BEDS: slab(srect(*b), 0, 0.4, "75_外構_ひろばの家具")
slab(srect(*A.KAM), 0, 0.8, "75_外構_ひろばの家具")
for (va, vb) in A.TEA["benches_v"]: slab(A.rect(19.6, 20.5, va, vb, 2), 0, 0.42, "75_外構_ひろばの家具")
slab(A.rect(19.3, 20.8, *A.TEA["shelf_v"], 2), 0, 0.9, "75_外構_ひろばの家具")
slab(srect(18.9, 19.8, 10.7, 11.25), 0, 0.7, "75_外構_ひろばの家具")        # temizu basin
for k in range(5):                                                           # strollers (outline)
    _st = A.PORCH["strollers"]; u1 = _st["u0"] - _st["pitch"] * k
    if k < _st["n"]: add_curve(A.rect(u1 - _st["w"], u1, _st["v"][0], _st["v"][1], 2), "75_外構_ひろばの家具", close=True)
_bn = A.PORCH["bench"]
slab([E(_bn["a"][0], _bn["b"][0]), E(_bn["a"][1], _bn["b"][0]), E(_bn["a"][1], _bn["b"][1]), E(_bn["a"][0], _bn["b"][1])], 0, _bn["h"], "75_外構_ひろばの家具")      # 腰掛け（公園側の塀ぎわ）
# 76 paving zones (outlines on the ground)
for g in [A.plz]:
    for c in coords(g): add_curve(c, "76_外構_舗装の区分", close=True)
for q in [srect(A.S_PATH0 - 0.4, 29.5, A.HEDGE_D + A.HW, A.WALL_D), srect(*A.DEL), srect(*A.VWALK)]:
    add_curve(q, "76_外構_舗装の区分", close=True)
# 77 trees (canopy circles at 3.0, trunk line)
for (p, rr) in [(P(24.4, 9.6), 1.9)]:                                          # 入江の木（外構の図と同じ位置、10-27 に P(25.0,11.3) から合わせた）
    m.Objects.AddBrep(r.Sphere(P3(p, 3.0), rr * MM).ToBrep(), attr("77c_外構_樹冠・植え込み・苔（葉）"))   # 樹冠は球（10-29 ユーザー：水平な円だけでは宙に浮いた輪に見えた）
    m.Objects.AddLine(P3(p, 0), P3(p, 3.0), attr("77_外構_樹木"))
# 75・76 西館の西の軒の雨：南の地中の雨水槽・受け桝・手押しポンプと鎖樋（線）、北の雨庭（輪郭）と鎖樋
R = A.RAIN
tk = R["S_TANK"]; slab(srect(tk["s"][0], tk["s"][1], *tk["d"]), -tk["depth"], tk["depth"] - 0.3, "75t_外構_地中の雨水槽")   # 地中の雨水槽（上は土 0.3。z は GL から、本体では GL＝−300 なので −1500〜−600）
ri = R["S_INLET"]; e = up(r.Circle(P3(P(ri[0], ri[1]), 0), ri[2] * MM).ToNurbsCurve(), 0.15, True)
if e: m.Objects.AddExtrusion(e, attr("75s_外構_石の受け桝"))                    # 石の受け桝
m.Objects.AddLine(P3(P(*R["S_PUMP"]), 0), P3(P(*R["S_PUMP"]), R["S_PUMP_H"]), attr("75_外構_ひろばの家具"))   # 手押しポンプ
m.Objects.AddLine(P3(P(*R["S_CHAIN"]), 0.9), P3(P(*R["S_CHAIN"]), 2.6), attr("75_外構_ひろばの家具"))
add_curve(srect(*R["N_GARDEN"]), "76_外構_舗装の区分", close=True)
m.Objects.AddLine(P3(P(*R["N_DOWN"]), 0.1), P3(P(*R["N_DOWN"]), 4.0), attr("76_外構_舗装の区分"))
# 78・79 みなみのさんかく（data/minami.json、minami_common.py）。平面の (x, y)＝(v, u) を本館の W(u, v) で 3dm の xy へ
import minami_common as MN
def mw(g): return [W(y, x) for x, y in list(g.exterior.coords)[:-1]]
L78, L79 = "78_外構_みなみのさんかく（丘・小径・砂場・水）", "79_外構_みなみのさんかく（緑の目隠しの株）"
# 丘：楕円の中を三角形のメッシュに（z は mound_z）
rings = MN.mound_rings()
mesh = r.Mesh(); vid = []
for ring in rings:
    ids = []
    for x, y in ring:
        p = W(y, x); ids.append(mesh.Vertices.Add(p[0] * MM, p[1] * MM, MN.mound_z(x, y) * MM))
    vid.append(ids)
N = len(vid[0])
for a_, b_ in zip(vid, vid[1:]):
    for i in range(N): mesh.Faces.AddFace(a_[i], a_[(i + 1) % N], b_[(i + 1) % N], b_[i])
cpt = W(*MN.D["MOUND"]["c"]); ci = mesh.Vertices.Add(cpt[0] * MM, cpt[1] * MM, MN.D["MOUND"]["h"] * MM)
for i in range(N): mesh.Faces.AddFace(vid[-1][i], vid[-1][(i + 1) % N], ci)
mesh.Normals.ComputeNormals(); mesh.Compact()
o = m.Objects.AddMesh(mesh, attr(L78))
# はだしの小径（面一、厚さ 0.02 の板で区分ごとに）
for name, g in MN.loop_parts():
    for q in ([g] if g.geom_type == "Polygon" else list(g.geoms)):
        if q.geom_type == "Polygon": slab(mw(q.simplify(0.01)), 0, 0.02, L78)
# 砂場：縁 h0.15（幅 0.1）と砂の面
sb = MN.SAND
wall(mw(sb) + [mw(sb)[0]], MN.D["SAND"]["h_rim"], L78)
wall(mw(sb.buffer(-0.1)) + [mw(sb.buffer(-0.1))[0]], MN.D["SAND"]["h_rim"], L78)
slab(mw(sb.buffer(-0.1)), 0, 0.02, L78)
# 水のテーブル（石の水盤 h0.45）
slab(mw(MN.WATER), 0, MN.D["WATER"]["h"], L78)
# 避難の帯の遊び：芝の川の輪郭、足あとの石（面一の円）
m.Objects.AddCurve(r.Polyline([P3(W(y, x), 0.005) for x, y in MN.GRASS_RIVER.exterior.coords]).ToNurbsCurve(), attr(L78))
for (xy, _a) in MN.footprints():
    m.Objects.AddCurve(r.Circle(P3(W(xy[1], xy[0]), 0.005), MN.EP["d"] / 2 * MM).ToNurbsCurve(), attr(L78))
# 78 木戸（閉じた位置の扉の板、厚さ 40 の帯として壁で）と柱 120 角
for name, h, e, hh, deg in MN.gates():
    wall([W(h[1], h[0]), W(e[1], e[0])], hh, L78, 0.05)
    hp = W(h[1], h[0]); post(hp, hh + 0.1, 0.12, L78)
# 79 ハーブの帯（h0.3 の塊）、木（幹と樹冠の円）
L79c = "79c_外構_みなみのさんかく_ハーブ・緑の目隠し（葉）"
slab(mw(MN.HERB), 0, 0.3, L79c)
_sc = [W(y, x) for x, y in MN.SCREEN.coords]                     # 川の柵の緑の目隠し：ワイヤー h1.5 にムベ（緑の帯）
wall(_sc, MN.RS["h"], L79c)
for (xy, k) in MN.screen_plants():
    m.Objects.AddLine(P3(W(xy[1], xy[0]), 0), P3(W(xy[1], xy[0]), MN.RS["h"]), attr(L79))
tp = W(*MN.D["TREE"]["c"])                                       # みなみのさんかくの木は外構の樹木のレイヤーへ（10-28 ユーザー：樹木は樹木レイヤに）
m.Objects.AddLine(P3(tp, 0), P3(tp, 4.5), attr("77_外構_樹木"))
# 樹冠の高さごとの円（3本）はやめた（10-29 ユーザー：球の上に水平な筋が光って見えた）。樹冠は球だけ
sph = r.Sphere(P3(tp, 3.4), MN.D["TREE"]["r"] * MM).ToBrep()
m.Objects.AddBrep(sph, attr("77c_外構_樹冠・植え込み・苔（葉）"))
# 70・72・76・77 西館の周りと北（north_common.py、data/approachA.json の NORTH）
import north_common as NC
def polys(g): return [q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and not q.is_empty]
for f in NC.FENCE: _Y.to3dm(slab, f[0], f[1], "70_外構_生垣・塀・格子", h=NC.N["FENCE_H"])                   # 読書の庭の塀（大和張り）
_gm = tuple((NC.np.array(NC.GATE[0]) + NC.np.array(NC.GATE[1])) / 2)
for _a, _b in ((NC.GATE[0], _gm), (_gm, NC.GATE[1])):                                         # 角の両開きの木戸（閉じた位置、扉2枚）
    _Y.to3dm(slab, _a, _b, "72_外構_柱", h=NC.N["KOMICHI_GATE"]["h"])
for q in NC.GATE: post(q, NC.N["KOMICHI_GATE"]["h"] + 0.1)
_Y.to3dm(slab, NC.NE_FENCE[0], NC.NE_FENCE[1], "70_外構_生垣・塀・格子", h=NC.NG["h"])                                     # 北のもりの北の端の塀（大和張り、10-25）
_Y.to3dm(slab, NC.NE_GATE[0], NC.NE_GATE[1], "72_外構_柱", h=NC.NG["h"])                                              # その木戸（閉じた位置）
for q in (NC.NE_FENCE[0], NC.NE_GATE[0], NC.NE_GATE[1]): post(q, NC.NG["h"] + 0.1)
for g in (NC.STAFF_PATH, NC.APRON, NC.MAPRON, NC.GRAVEL, NC.KOMICHI):
    for q in polys(g): add_curve(list(q.exterior.coords)[:-1], "76_外構_舗装の区分", close=True)
_PL = NC.N["PLANTS"]
for g, k in ((NC.HEDGE, "HEDGE"), (NC.MID, "MID"), (NC.LOW, "LOW")):                     # 香りの刈り込み・花の低木・低い香りの草（塊）
    for q in polys(g): slab(list(q.simplify(0.02).exterior.coords)[:-1], 0, _PL[k]["h"], "77c_外構_樹冠・植え込み・苔（葉）")
for q in polys(NC.GAPRON): add_curve(list(q.exterior.coords)[:-1], "76_外構_舗装の区分", close=True)
slab(list(NC.READ.simplify(0.02).exterior.coords)[:-1], 0, 0.03, "77c_外構_樹冠・植え込み・苔（葉）")        # 読書の庭の苔
# 公園の木戸と職員の通用口の柱（10-27：扉と塀の板を柱で受ける）
for q in (E(A.GA0, 0), E(A.GA1, 0)): post(q, 1.9)          # E(0,0) は棚の柱（TIP）が兼ねる
for q in (P(_g0, _pd), P(_g1, _pd)): post(q, 1.9)
for (p0, p1, lay, h, foot) in FENCES: yamato.to3dm(slab, p0, p1, lay, h=h, foot=foot, posts=POSTS)
# 公園の中身（ユーザー 10-29、data/approachA.jsonのPARK_PLAN、局所座標はapproachA.PK）。どれも閉じた立体、z＝0（GL）から上
PK, PP = A.PK, A.PARK_PLAN
L74p, L74s, L75p, L76p = "74p_外構_公園の鉄の物（鉄棒・柵・車止め）", "74s_外構_公園のすべり台", "75p_外構_公園の木のベンチ", "76p_外構_公園の芝の保護材（車の帯）"
def kbox(x0, x1, y0, y1, z0, z1, lay): slab([PK(x0, y0), PK(x1, y0), PK(x1, y1), PK(x0, y1)], z0, z1 - z0, lay)
def kcyl(p, rr, z0, h, lay):                                   # 立てた丸棒
    e = up(r.Circle(P3(p, z0), rr * MM).ToNurbsCurve(), h, True)
    if e: m.Objects.AddExtrusion(e, attr(lay))
_ax = np.array(PK(1, 0)) - np.array(PK(0, 0))
def kbar(x0, x1, y, z, rr, lay):                               # 川と平行な横の丸棒（立てた円柱を寝かせる）
    L_ = x1 - x0; p0 = PK(x0, y)
    b = up(r.Circle(P3(p0, 0), rr * MM).ToNurbsCurve(), L_, True).ToBrep(False)
    b.Transform(r.Transform.Rotation(math.pi / 2, r.Vector3d(-_ax[1], _ax[0], 0), P3(p0, 0)))
    c = b.GetBoundingBox().Center; tgt = PK((x0 + x1) / 2, y)
    if (c.X - tgt[0] * MM) ** 2 + (c.Y - tgt[1] * MM) ** 2 > (L_ * MM / 4) ** 2:             # 逆向きに寝たら回し直す
        b.Transform(r.Transform.Rotation(math.pi, r.Vector3d(0, 0, 1), P3(p0, 0)))
    b.Transform(r.Transform.Translation(0, 0, z * MM))
    m.Objects.AddBrep(b, attr(lay))
# 搬入の車の帯（芝の保護材）は芝の下なので3dmに入れない（ユーザー 10-29：見せない）
# 公園は全面を芝生（ユーザー 10-29）：12×12の輪郭いっぱいに芝の面（厚さ0.01）
slab(A.PARK, 0.0, 0.01, "76g_外構_公園の芝生")
# 道路側の鉄柵h1.1（柱□50、上下の横材□40、縦格子□16を0.12ごと、開口のほかの区間）と車止め（上げ下げ式、φ0.1 h0.8、上げた姿）
_rl = PP["rail"]; xr = _rl["x"]
for y0r, y1r in _rl["segments"]:
    _ps = A.rail_posts(y0r, y1r, _rl["post_pitch"])
    for _y in _ps: kbox(xr - 0.025, xr + 0.025, max(y0r, _y - 0.025), min(y1r, _y + 0.025), 0.0, _rl["h"], L74p)
    for z0, z1 in ((0.08, 0.12), (_rl["h"] - 0.04, _rl["h"])): kbox(xr - 0.02, xr + 0.02, y0r + 0.025, y1r - 0.025, z0, z1, L74p)
    for _y in np.arange(y0r + 0.1, y1r - 0.05, _rl["bar_pitch"]):
        if min(abs(_y - q) for q in _ps) > 0.04: kbox(xr - 0.008, xr + 0.008, _y - 0.008, _y + 0.008, 0.12, _rl["h"] - 0.04, L74p)
_op = PP["opening"]
for _y in _op["bollards_y"]: kcyl(PK(xr, _y), _op["bollard_d"] / 2, 0.0, _op["bollard_h"], L74p)
# 鉄棒：柱φ0.06（高い方の棒 +0.05）、棒φ0.03を0.9・1.1・1.3
_br = PP["bars"]; _bx = [_br["x0"] + _br["len"] * k for k in range(len(_br["h"]) + 1)]
for k, _x in enumerate(_bx):
    hh = max(_br["h"][max(0, k - 1)], _br["h"][min(len(_br["h"]) - 1, k)]) + 0.05
    kcyl(PK(_x, _br["y"]), _br["post_d"] / 2, 0.0, hh, L74p)
for k, hb in enumerate(_br["h"]):
    kbar(_bx[k] + _br["post_d"] / 2, _bx[k + 1] - _br["post_d"] / 2, _br["y"], hb, _br["bar_d"] / 2, L74p)
# すべり台（簡単な形、真南へ滑り降りる）：踊り場の台h1.2、滑り面（側面の形を東へ幅0.6で押し出す）、はしご（くさび）。SLD(a, s)＝はしごの後ろから真南へ a、東へ s
_sl = PP["slide"]; H = _sl["h"]; SLD = A.SLD
slab(A.SLR(*_sl["deck"], _sl["w_deck"]), 0.0, H, L74s)
def side_prism(prof, w, lay):                                  # 側面の形 (a, z) を、s＝−w/2 の面から東へ w 押し出す
    c = r.Polyline([P3(SLD(a, -w / 2), z) for a, z in prof + [prof[0]]]).ToNurbsCurve()
    e = r.Extrusion.Create(c, w * MM, True)
    if e.GetBoundingBox().Center.X < SLD(0, 0)[0] * MM - 1: e = r.Extrusion.Create(c, -w * MM, True)
    m.Objects.AddExtrusion(e, attr(lay))
a0c, a1c = _sl["chute"]; al0, al1 = _sl["landing"]
side_prism([(a0c, 0.0), (al1, 0.0), (al1, 0.25), (al0, 0.3), (a0c + 0.3, H), (a0c, H)], _sl["w"], L74s)
aa0, aa1 = _sl["ladder"]
side_prism([(aa0, 0.0), (aa1, 0.0), (aa1, H)], _sl["w"], L74s)
# ベンチ（座t0.04 at h0.42、脚2枚）
for _b in PP["benches"]["list"]:
    (bx0, bx1), (by0, by1) = _b["x"], _b["y"]; hb = PP["benches"]["h"]
    kbox(bx0, bx1, by0, by1, hb - 0.04, hb, L75p)
    if bx1 - bx0 > by1 - by0:
        for xx in (bx0 + 0.15, bx1 - 0.21): kbox(xx, xx + 0.06, by0 + 0.03, by1 - 0.03, 0.0, hb - 0.04, L75p)
    else:
        for yy in (by0 + 0.15, by1 - 0.21): kbox(bx0 + 0.03, bx1 - 0.03, yy, yy + 0.06, 0.0, hb - 0.04, L75p)
# キンモクセイ3本：幹φ0.12 h1.0（77）、樹冠は球（77c）
_km = PP["kinmokusei"]
for _y in _km["y"]:
    p = PK(_km["x"], _y)
    kcyl(p, 0.06, 0.0, _km["trunk_h"], "77_外構_樹木")
    m.Objects.AddBrep(r.Sphere(P3(p, _km["crown_z"]), _km["r"] * MM).ToBrep(), attr("77c_外構_樹冠・植え込み・苔（葉）"))

# 外構の地面（ユーザー 10-29：地面が無く、落ちると奈落の底。監修の項 20261029-1457-kanshu、色は航空写真から）
# 閉じた板 厚さ0.01（本体で −300〜−290）。敷地から建物・公園・みなみのさんかくとポーチ・園庭（本館の西の面より東）を引いた所を、
# 駐車（アスファルト）→ 歩く所（ベージュ）→ ひろば（真砂土）→ ほか（土）の順に分ける。上に立つ植え込み・家具・バンプ・受け桝の足もとは抜く
from shapely.geometry import Polygon as _GP, Point as _GPt
from shapely.ops import unary_union as _GU
def _sr(s0, s1, d0, d1): return _GP(srect(s0, s1, d0, d1))
_WEST = _GP([W(-30, -0.35), W(80, -0.35), W(80, -60), W(-30, -60)])                       # 本館の西の外壁の外面より西
_SOUTH_X = _GP([W(-0.1, -1.0), W(-0.1, 20), W(-30, 20), W(-30, -1.0)])                     # みなみのさんかく・ポーチ（本館係・みなみの地面がある）
_gs = _GP(A.SITE).intersection(_WEST).intersection(_sr(-5, 29.6, -2, 40))
_gs = _gs.difference(NC._CLOSED).difference(NC.MECH).difference(_GP(A.PARK)).difference(_SOUTH_X)
_gn = _GU([NC.BAND_W, NC.MSTRIP, NC.FSTRIP, NC.GAPRON, NC.KOMICHI, NC.MAPRON]).difference(NC._CLOSED).difference(NC.MECH)
_GROUND = _GU([_gs, _gn])
_holes = [NC.READ, NC.HEDGE, NC.MID, NC.LOW, _sr(12.3, 17.6, *A.BUMP), _sr(18.9, 19.8, 10.7, 11.25), _sr(*A.KAM),
          _GP(A.rect(19.3, 20.8, *A.TEA["shelf_v"], 2))] + [_sr(*b) for b in A.BEDS] + [_GP(A.rect(19.6, 20.5, va, vb, 2)) for (va, vb) in A.TEA["benches_v"]] \
         + [_GPt(P(ri[0], ri[1])).buffer(ri[2], 32)]
_GROUND = _GROUND.difference(_GU(_holes))
_walk = _GU([_sr(A.SIDEWALK["s"][0], A.SIDEWALK["s"][1], *A.SIDEWALK["d"]), _sr(*A.VWALK), _sr(A.S_PATH0 - 0.4, 29.5, A.HEDGE_D + A.HW, A.WALL_D),
             A.TRI, _sr(*A.DEL), A.POCKET, _sr(22.7, 30.0, A.SIDEWALK["d"][1], A.STALL_D0), NC.STAFF_PATH, NC.APRON, NC.MAPRON, NC.KOMICHI, NC.GAPRON])
_park = _GU([_sr(-5, 17.7, A.SIDEWALK["d"][1], A.HEDGE_D), _sr(17.7, 22.7, A.SIDEWALK["d"][1], A.NHEDGE_D)]).difference(_walk)
_zones = [("74a_外構_駐車の舗装（アスファルト）", _GROUND.intersection(_park))]
_zones.append(("76b_外構_歩く舗装（ベージュ）", _GROUND.intersection(_walk).difference(_park)))
_PLZ = A.plz.intersection(_sr(-5, 40, -5, A.WALL_D))                                      # 本館の壁の足もと（小径の先の0.3）は砂利＝土の色（10-30）
_zones.append(("78a_外構_ひろばの真砂土", _GROUND.intersection(_PLZ).difference(_walk).difference(_park)))
_zones.append(("76s_外構_土（植栽・砂利・すき間）", _GROUND.difference(_walk).difference(_park).difference(_PLZ)))
GROUND_AREA = {}
for _ln, _g in _zones:
    _g = _g.buffer(0.002, join_style=2).buffer(-0.004, join_style=2)                     # 隣の板と0.002あけ、細い切れ端を落とす
    GROUND_AREA[_ln] = 0.0
    for _q in polys(_g):
        if _q.area < 0.05: continue
        _q = _q.simplify(0.005)
        if not list(_q.interiors):
            slab_smooth(list(_q.exterior.coords)[:-1], 0.0, 0.01, _ln)
        else:                                                            # 穴のある板は、穴を切る線で分けて穴なしにする
            from shapely.ops import split as _split
            from shapely.geometry import LineString as _GL
            # 切る線は道路に直交する向き（局所の d）で、その穴を持つ一片だけを切る（10-30：世界の x で全部を切ると斜めの細い切れ端ができた）
            _o = np.array(P(0, 0)); _dd = np.array(P(0, 1)) - _o
            _pcs = [_q]
            for _h in _q.interiors:
                _c = np.array(_GP(_h).representative_point().coords[0])
                _cut = _GL([tuple(_c - 80 * _dd), tuple(_c + 80 * _dd)])
                _hp = _GP(_h)
                _new = []
                for pc in _pcs:
                    if any(_GP(i).equals(_hp) or _GP(i).contains(_hp.representative_point()) for i in pc.interiors):
                        _new += list(_split(pc, _cut).geoms)
                    else: _new.append(pc)
                _pcs = _new
            for _pc in _pcs:
                for _pp in polys(_pc):
                    if _pp.area >= 0.05 and not list(_pp.interiors): slab_smooth(list(_pp.simplify(0.005).exterior.coords)[:-1], 0.0, 0.01, _ln)
        GROUND_AREA[_ln] += _q.area
# 駐車の白線（幅0.1、舗装の上に+0.002）：車室の境の線（車室の長い向き＝道路に沿う向き）
for (_s0, _s1, _n) in ((7.2, 12.2, 3), (17.7, 22.7, 2)):
    for _k in range(_n + 1):
        _d = A.STALL_D0 + 2.5 * _k
        slab(srect(_s0, _s1, _d - 0.05, _d + 0.05), 0.01, 0.002, "74w_外構_駐車の白線")
print("ground", {k[:6]: round(v, 1) for k, v in GROUND_AREA.items()})
# お向かいの南の張り出しの突端の木（ユーザー 10-29：5mくらい、樹冠が道の半分少しまで）。地面は道路と同じ−320（GLの0.02下）
import json as _json
_OT = _json.load(open(os.path.join(os.path.dirname(HERE), "data", "approachA.json"), encoding="utf-8"))["OPP_TREE"]
kcyl(_OT["xy"], _OT["trunk_r"], -0.02, _OT["crown_z"] + 0.02, "77_外構_樹木")
_ns = r.Sphere(r.Point3d(0, 0, 0), _OT["crown_r"] * MM).ToNurbsSurface(); _cp = _ns.Points   # 樹冠は横に広い楕円体（制御点の z を縮める）
for _i in range(_cp.CountU):
    for _j in range(_cp.CountV):
        _q = _cp[_i, _j]; _cp[_i, _j] = r.Point4d(_q.X, _q.Y, _q.Z * _OT["crown_rz"] / _OT["crown_r"], _q.W)
_sp = r.Brep.CreateFromSurface(_ns); _sp.Transform(r.Transform.Translation(_OT["xy"][0] * MM, _OT["xy"][1] * MM, _OT["crown_z"] * MM))
m.Objects.AddBrep(_sp, attr("77c_外構_樹冠・植え込み・苔（葉）"))
m.Write(OUTF, 7)
print("wrote", OUTF, len(m.Objects), "objects")
