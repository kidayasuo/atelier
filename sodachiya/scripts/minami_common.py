# みなみのさんかく（乳児の園庭）の形。data/minami.json を読み、図（minami01.py）と 3dm（export3dm.py）で共通に使う。
# 平面の座標は (x, y) = (v, u)：x は東、y は北（本館の座標をそのまま、真北から約 7° ずれ）。
import os, json, math
import numpy as np
from shapely.geometry import Polygon, LineString, Point
from shapely import affinity as af

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(os.path.dirname(HERE), "data", "minami.json"), encoding="utf-8"))

def xy(uv): return (uv[1], uv[0])
def poly(key): return Polygon([xy(p) for p in D[key]]).buffer(0)

AREA, EVAC, ENGAWA, ROOF, PORCH = (poly(k) for k in ("AREA", "EVAC", "ENGAWA", "ROOF", "PORCH"))
R0, R1 = (np.array(xy(p)) for p in D["RIVER_EDGE"])
DIR = (R1 - R0) / np.linalg.norm(R1 - R0)                    # along the river edge
NRM = np.array([-DIR[1], DIR[0]])
if NRM[1] < 0: NRM = -NRM                                    # into the site (north-west)
ANG = math.degrees(math.atan2(DIR[1], DIR[0]))
def dist_river(p): return float((np.array(p) - R0) @ NRM)  # distance from the river edge (m)
BIG = 40.0
def band(w):                                                 # strip of width w along the river edge
    a, b = R0 - DIR * BIG, R1 + DIR * BIG
    return Polygon([tuple(a), tuple(b), tuple(b + NRM * w), tuple(a + NRM * w)]).intersection(AREA)
CLEAR = band(D["CLEAR"]["w"])
PLAY = AREA.difference(CLEAR)

def ellipse(c, a, b, n=96):
    e = af.scale(Point(xy(c)).buffer(1.0, resolution=n // 4), a, b)
    return af.rotate(e, ANG, origin=xy(c))

M, Lp, S, T, H, Wt = (D[k] for k in ("MOUND", "LOOP", "SAND", "TREE", "HERB", "WATER"))
MOUND = ellipse(M["c"], M["a"], M["b"])
MOUND_TOP = ellipse(M["c"], M["top"], M["top"] * M["b"] / M["a"])
def mound_z(x, y):                                           # height above GL (m): flat top, straight slopes
    c = np.array(xy(M["c"])); q = np.array([x, y]) - c
    s, t = q @ DIR / M["a"], q @ NRM / M["b"]
    rr = math.hypot(s, t); r0 = M["top"] / M["a"]
    if rr >= 1: return 0.0
    if rr <= r0: return M["h"]
    return M["h"] * (1 - rr) / (1 - r0)

LOOP_C = ellipse(Lp["c"], Lp["a"], Lp["b"]).exterior          # centerline
LOOP = LOOP_C.buffer(Lp["w"] / 2, resolution=8)
def loop_parts():                                            # [(name, Polygon)]
    out, s0, Lt = [], 0.0, LOOP_C.length
    from shapely.ops import substring
    for name, f in Lp["parts"]:
        s1 = s0 + f * Lt
        seg = substring(LOOP_C, s0, min(s1, Lt))
        out.append((name, seg.buffer(Lp["w"] / 2, cap_style=2, resolution=8).intersection(LOOP)))
        s0 = s1
    return out

def rrect(c, w, l, ang, r=0.15):                             # rounded rectangle, l along ang
    base = Polygon([(-l / 2 + r, -w / 2 + r), (l / 2 - r, -w / 2 + r), (l / 2 - r, w / 2 - r), (-l / 2 + r, w / 2 - r)]).buffer(r, resolution=8)
    return af.translate(af.rotate(base, ang, origin=(0, 0)), *xy(c))
SAND = rrect(S["c"], S["w"], S["l"], 0)
TREE = Point(xy(T["c"])).buffer(T["r"], resolution=32)
HERB = Polygon([xy((H["u"][0], H["v"][0])), xy((H["u"][1], H["v"][0])), xy((H["u"][1], H["v"][1])), xy((H["u"][0], H["v"][1]))])
WATER = rrect(Wt["c"], Wt["w"], Wt["l"], 0, 0.1)
Sh = D["SHED"]
SHED = Polygon([xy((Sh["u"][0], Sh["v"][0])), xy((Sh["u"][1], Sh["v"][0])), xy((Sh["u"][1], Sh["v"][1])), xy((Sh["u"][0], Sh["v"][1]))])

def check():
    msgs = []
    for n, g in (("丘", MOUND), ("小径", LOOP), ("砂場", SAND), ("水のテーブル", WATER), ("ハーブ", HERB)):
        if g.intersects(EVAC): msgs.append(f"{n} が避難の帯に掛かる")
        if g.intersects(ENGAWA): msgs.append(f"{n} が縁側に掛かる")
    if Point(xy(T["c"])).buffer(0.3).intersects(CLEAR): msgs.append("木が空ける帯に掛かる")
    for a, b, na in ((SAND, LOOP, "砂場と小径"), (SAND, MOUND, "砂場と丘"), (HERB, LOOP, "ハーブと小径"), (WATER, LOOP, "水と小径"), (SHED, SAND, "物置と砂場"), (SHED, HERB, "物置とハーブ"), (SHED, LOOP, "物置と小径")):
        if a.intersects(b): msgs.append(na + "が重なる")
    if not LOOP.within(AREA): msgs.append("小径がはみ出す")
    return msgs

def mound_rings(N=48, fs=(1.0, 0.75, 0.5, 0.25, 0.0)):   # same N points per ring, outer -> top
    import numpy as _np
    c = _np.array(xy(M["c"])); out = []
    for f in fs:
        a = M["a"] * f + M["top"] * (1 - f); b = a * M["b"] / M["a"]
        out.append([tuple(c + DIR * a * math.cos(t) + NRM * b * math.sin(t)) for t in _np.linspace(0, 2 * math.pi, N, endpoint=False)])
    return out
