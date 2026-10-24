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
             ("78_外構_みなみのさんかく（丘・小径・砂場・水）", (176, 138, 90)), ("79_外構_みなみのさんかく（木・ハーブ）", (110, 154, 78))]:
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
def post(p, h, s=0.12, lay="72_外構_柱"):
    x, y = p; q = [(x - s / 2, y - s / 2), (x + s / 2, y - s / 2), (x + s / 2, y + s / 2), (x - s / 2, y + s / 2)]
    slab(q, 0, h, lay)
def coords(g):
    gs = [g] if g.geom_type == "Polygon" else list(g.geoms)
    return [list(q.exterior.coords)[:-1] for q in gs if q.geom_type == "Polygon"]
P, Q, srect, E, W = A.P, A.Q, A.srect, A.E, A.W

# 70 hedges (h1.2), board fence (h1.8), lattice (h1.8)
for h in A.HEDGE: wall(Q(h), 1.2, "70_外構_生垣・塀・格子")
wall([P(A.S_PATH0, A.HEDGE_D), P(*A.TIP)], 1.2, "70_外構_生垣・塀・格子")
_pd0, _pd = A.STAFF_BIKE["pocket"][2], A.STAFF_BIKE["pocket"][3]; _g0, _g1 = A.STAFF_BIKE["gate"]
wall([P(22.7, _pd), P(_g0, _pd)], 1.8, "70_外構_生垣・塀・格子")          # board fence: east side of the staff bike pocket
wall([P(_g1, _pd), P(A.SX, _pd)], 1.8, "70_外構_生垣・塀・格子")
wall([P(_g0 + 0.03, _pd), P(_g1 - 0.03, _pd)], 1.8, "72_外構_柱")                          # staff gate leaf (closed)
for _k, _s in enumerate(A.STAFF_POS):                                                    # staff bikes (outlines on the ground)
    _d0 = _pd0 + (0.05 if _k % 2 == 0 else 0.2)
    add_curve([P(_s - 0.15, _d0), P(_s + 0.15, _d0), P(_s + 0.15, _d0 + 1.75), P(_s - 0.15, _d0 + 1.75)], "74_外構_駐車・駐輪・バンプ", close=True)
slab(srect(*A.WOOD), 0, 1.2, "75_外構_ひろばの家具")                                      # wood rack next to the kamado
wall([E(A.GA1, 0), A.FENCE_END], 1.8, "70_外構_生垣・塀・格子")
wall([E(0, 0), E(A.GA0, 0)], 1.8, "70_外構_生垣・塀・格子")
# 71 roofs (flat placeholders, 100 thick): kido 2.6, temizu 2.7, lean-to 2.6, back-door canopy 2.6
slab(srect(*A.TEM), 2.7, 0.1, "71_外構_屋根（木戸・手水・下屋）")
import north_common as _NC0
NC_WS = _NC0.WS
slab(list(A.LEAN_ROOF.exterior.coords)[:-1], 2.6, 0.1, "71_外構_屋根（木戸・手水・下屋）")      # 下屋＋南西の丸みへの回り込み（勝手口の庇は外した、10-24）
for _g in getattr(A.LEAN_GUTTER, "geoms", [A.LEAN_GUTTER]): add_curve(list(_g.coords), "75_外構_ひろばの家具", 2.6)   # 下屋の軒樋
# 72 posts
s0, s1, d0, d1 = A.TEM
for p in [P(s0 + 0.3, d0 + 0.3), P(s1 - 0.3, d0 + 0.3), P(s0 + 0.3, d1 - 0.3), P(s1 - 0.3, d1 - 0.3)]: post(p, 2.7)
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
# 73 木戸の内側の三角のムベの棚（小径の棚の続き、10-24）：柱・桁 h2.25、梁は 1.5 ごとに弓なり
for p in A.TRI_POSTS: post(p, 2.25, 0.12, "73_外構_アーチの棚")
for g in A.TRI_GIRDERS: add_curve(g, "73_外構_アーチの棚", 2.25)
for b0, b1 in A.TRI_BEAMS:
    L_ = math.dist(b0, b1); rise = min(0.28, 0.12 * L_); pts = []
    for t in np.linspace(0, 1, 13):
        p = (b0[0] + (b1[0] - b0[0]) * t, b0[1] + (b1[1] - b0[1]) * t)
        pts.append(r.Point3d(p[0] * MM, p[1] * MM, (2.25 + rise * math.sin(math.pi * t)) * MM))
    m.Objects.AddCurve(r.Polyline(pts).ToNurbsCurve(), attr("73_外構_アーチの棚"))
# 74 parking, bump, bikes, curb cut
for k in range(3): add_curve(srect(7.2, 12.2, A.STALL_D0 + 2.5 * k, A.STALL_D0 + 2.5 * (k + 1)), "74_外構_駐車・駐輪・バンプ", close=True)
for k in range(2): add_curve(srect(17.7, 22.7, A.STALL_D0 + 2.5 * k, A.STALL_D0 + 2.5 * (k + 1)), "74_外構_駐車・駐輪・バンプ", close=True)
slab(srect(12.3, 17.6, *A.BUMP), 0, 0.05, "74_外構_駐車・駐輪・バンプ")
for kind, a, b in A.BIKES:
    q = srect(a, a + 0.7, b, b + 1.9) if kind == "d" else srect(a, a + 1.9, b, b + 0.7)
    add_curve(q, "74_外構_駐車・駐輪・バンプ", close=True)
# 75 plaza furniture
for b in A.BEDS: slab(srect(*b), 0, 0.4, "75_外構_ひろばの家具")
slab(srect(*A.KAM), 0, 0.8, "75_外構_ひろばの家具")
for (va, vb) in A.TEA["benches_v"]: slab(A.rect(19.6, 20.5, va, vb, 2), 0, 0.42, "75_外構_ひろばの家具")
slab(A.rect(19.3, 20.8, *A.TEA["shelf_v"], 2), 0, 0.9, "75_外構_ひろばの家具")
slab(srect(18.9, 19.8, 10.7, 11.25), 0, 0.7, "75_外構_ひろばの家具")        # temizu basin
for k in range(5):                                                           # strollers (outline)
    u0 = -4.0 + 0.7 * k; add_curve(A.rect(u0 + 0.06, u0 + 0.64, -0.85, 0.15, 2), "75_外構_ひろばの家具", close=True)
slab(A.rect(-3.6, -1.4, 1.05, 1.45, 2), 0, 0.42, "75_外構_ひろばの家具")      # porch bench
# 76 paving zones (outlines on the ground)
for g in [A.plz]:
    for c in coords(g): add_curve(c, "76_外構_舗装の区分", close=True)
for q in [srect(A.S_PATH0 - 0.4, 29.5, A.HEDGE_D + A.HW, A.WALL_D), srect(*A.DEL), srect(*A.VWALK)]:
    add_curve(q, "76_外構_舗装の区分", close=True)
# 77 trees (canopy circles at 3.0, trunk line)
for (p, rr) in [(P(25.0, 11.3), 1.9)]:                                         # 入江の木（公園の真ん中の木は無い、10-24）
    c = r.Circle(P3(p, 3.0), rr * MM).ToNurbsCurve(); m.Objects.AddCurve(c, attr("77_外構_樹木"))
    m.Objects.AddLine(P3(p, 0), P3(p, 3.0), attr("77_外構_樹木"))
# 75・76 西館の西の軒の雨：南の雨水樽（円柱）と鎖樋（線）、北の雨庭（輪郭）と鎖樋
R = A.RAIN
rb = R["S_BARREL"]; c = r.Circle(P3(P(rb[0], rb[1]), 0), rb[2] * MM).ToNurbsCurve()
e = up(c, rb[3], True)
if e: m.Objects.AddExtrusion(e, attr("75_外構_ひろばの家具"))
m.Objects.AddLine(P3(P(*R["S_CHAIN"]), 0.9), P3(P(*R["S_CHAIN"]), 2.6), attr("75_外構_ひろばの家具"))
add_curve(srect(*R["N_GARDEN"]), "76_外構_舗装の区分", close=True)
m.Objects.AddLine(P3(P(*R["N_DOWN"]), 0.1), P3(P(*R["N_DOWN"]), 4.0), attr("76_外構_舗装の区分"))
# 78・79 みなみのさんかく（data/minami.json、minami_common.py）。平面の (x, y)＝(v, u) を本館の W(u, v) で 3dm の xy へ
import minami_common as MN
def mw(g): return [W(y, x) for x, y in list(g.exterior.coords)[:-1]]
L78, L79 = "78_外構_みなみのさんかく（丘・小径・砂場・水）", "79_外構_みなみのさんかく（木・ハーブ）"
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
# 78 木戸（閉じた位置の扉の板、厚さ 40 の帯として壁で）と柱 120 角
for name, h, e, hh, deg in MN.gates():
    wall([W(h[1], h[0]), W(e[1], e[0])], hh, L78, 0.05)
    hp = W(h[1], h[0]); post(hp, hh + 0.1, 0.12, L78)
# 79 ハーブの帯（h0.3 の塊）、木（幹と樹冠の円）
slab(mw(MN.HERB), 0, 0.3, L79)
tp = W(*MN.D["TREE"]["c"])
m.Objects.AddLine(P3(tp, 0), P3(tp, 4.5), attr(L79))
for zc, rr in ((MN.D["TREE"]["under"], MN.D["TREE"]["r"] * 0.8), (3.4, MN.D["TREE"]["r"]), (4.5, MN.D["TREE"]["r"] * 0.6)):
    m.Objects.AddCurve(r.Circle(P3(tp, zc), rr * MM).ToNurbsCurve(), attr(L79))
sph = r.Sphere(P3(tp, 3.4), MN.D["TREE"]["r"] * MM).ToBrep()
m.Objects.AddBrep(sph, attr(L79))
# 70・72・76・77 西館の周りと北（north_common.py、data/approachA.json の NORTH）
import north_common as NC
def polys(g): return [q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and not q.is_empty]
for f in NC.FENCE: wall(f, NC.N["FENCE_H"], "70_外構_生垣・塀・格子")                   # 読書の庭の板塀
_gm = tuple((NC.np.array(NC.GATE[0]) + NC.np.array(NC.GATE[1])) / 2)
for _a, _b in ((NC.GATE[0], _gm), (_gm, NC.GATE[1])):                                         # 角の両開きの木戸（閉じた位置、扉2枚）
    wall([_a, _b], NC.N["KOMICHI_GATE"]["h"], "72_外構_柱", 0.05)
for q in NC.GATE: post(q, NC.N["KOMICHI_GATE"]["h"] + 0.1)
for g in (NC.STAFF_PATH, NC.APRON, NC.MAPRON, NC.GRAVEL, NC.KOMICHI):
    for q in polys(g): add_curve(list(q.exterior.coords)[:-1], "76_外構_舗装の区分", close=True)
_PL = NC.N["PLANTS"]
for g, k in ((NC.HEDGE, "HEDGE"), (NC.MID, "MID"), (NC.LOW, "LOW")):                     # 香りの刈り込み・花の低木・低い香りの草（塊）
    for q in polys(g): slab(list(q.simplify(0.02).exterior.coords)[:-1], 0, _PL[k]["h"], "77_外構_樹木")
for q in polys(NC.GAPRON): add_curve(list(q.exterior.coords)[:-1], "76_外構_舗装の区分", close=True)
slab(list(NC.READ.simplify(0.02).exterior.coords)[:-1], 0, 0.03, "77_外構_樹木")        # 読書の庭の苔
m.Write(OUTF, 7)
print("wrote", OUTF, len(m.Objects), "objects")
