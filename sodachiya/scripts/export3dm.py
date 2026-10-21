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
             ("76_外構_舗装の区分", (200, 190, 170)), ("77_外構_樹木", (90, 140, 60))]:
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
wall([P(22.7, A.FENCE_D), P(A.FENCE_S1, A.FENCE_D)], 1.8, "70_外構_生垣・塀・格子")
wall([E(A.GA1, 0), A.FENCE_END], 1.8, "70_外構_生垣・塀・格子")
wall([E(0, 0), E(A.GA0, 0)], 1.8, "70_外構_生垣・塀・格子")
# 71 roofs (flat placeholders, 100 thick): kido 2.6, temizu 2.7, lean-to 2.6, back-door canopy 2.6
slab(A.KR, 2.6, 0.1, "71_外構_屋根（木戸・手水・下屋）")
slab(srect(*A.TEM), 2.7, 0.1, "71_外構_屋根（木戸・手水・下屋）")
slab(A.rect(*A.LEAN_UV, 4), 2.6, 0.1, "71_外構_屋根（木戸・手水・下屋）")
slab(srect(28.6, 31.2, 1.3, 3.0), 2.6, 0.1, "71_外構_屋根（木戸・手水・下屋）")
# 72 posts
for p in [E(-0.05, -0.15), E(2.35, -0.15), E(-0.05, 2.6), E(2.35, 2.6)]: post(p, 2.6)
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
for (va, vb) in [(-9.0, -7.2), (-6.6, -4.8)]: slab(A.rect(19.6, 20.5, va, vb, 2), 0, 0.42, "75_外構_ひろばの家具")
slab(A.rect(19.3, 20.8, -9.95, -9.5, 2), 0, 0.9, "75_外構_ひろばの家具")
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
for (p, rr) in [(P(25.0, 11.3), 1.9), ((-13.6, -75.2), 3.4)]:
    c = r.Circle(P3(p, 3.0), rr * MM).ToNurbsCurve(); m.Objects.AddCurve(c, attr("77_外構_樹木"))
    m.Objects.AddLine(P3(p, 0), P3(p, 3.0), attr("77_外構_樹木"))
m.Write(OUTF, 7)
print("wrote", OUTF, len(m.Objects), "objects")
