# 西館の周りと北（読書の庭・機械室）の外構の形。data/approachA.json の NORTH を読み、図（approachN.py）と 3dm（export3dm.py）で共通に使う。
# 座標は 3dm の xy（m）。西の道路沿いは (s, d)、北西の道路沿いは (t, n)：どちらも道路の境から敷地の内へ。
import os, json, pickle
import numpy as np
import rhino3dm as r
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity as af

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
AJ = json.load(open(os.path.join(ROOT, "data", "approachA.json"), encoding="utf-8"))
N = AJ["NORTH"]; RAIN = AJ["RAIN"]

SITE = Polygon([(0.0, 0.0), (34.86, -43.83), (-14.44, -83.04), (-21.91, -73.65), (-25.83, -20.54)])
SETB = Polygon([(-0.16, -1.41), (33.45, -43.67), (-14.28, -81.64), (-20.93, -73.27), (-24.79, -20.99)])
BAND = SITE.difference(SETB)                                    # the 1.0 m setback band

A0 = np.array((-21.91, -73.65)); B0 = np.array((-25.83, -20.54)); N0 = np.array((0.0, 0.0))
tt = (B0 - A0) / np.linalg.norm(B0 - A0); nn = np.array([tt[1], -tt[0]]); nn = nn if nn[0] > 0 else -nn
t2 = (N0 - B0) / np.linalg.norm(N0 - B0); n2 = np.array([t2[1], -t2[0]]); n2 = n2 if n2[1] < 0 else -n2
def P(s, d): return tuple(map(float, A0 + tt * s + nn * d))      # west road
def T(t, n): return tuple(map(float, B0 + t2 * t + n2 * n))      # north-west road
def sbox(s0, s1, d0, d1): return Polygon([P(s0, d0), P(s1, d0), P(s1, d1), P(s0, d1)])
def tbox(t0, t1, n0, n1): return Polygon([T(t0, n0), T(t1, n0), T(t1, n1), T(t0, n1)])

# buildings
_D = pickle.load(open(os.path.join(ROOT, "data", "wnew.pkl"), "rb"))
WS = af.scale(_D.get("WS", _D["WN"]), 0.001, 0.001, origin=(0, 0))
import math
CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX)
if TH_S < 0: TH_S += 2 * math.pi
def W(u, v):
    th = TH_S - u / RW; rr = RW - v
    return (CX + rr * math.cos(th), CY + rr * math.sin(th))
def urect(u0, u1, v0, v1, k=24):
    return Polygon([W(u0 + (u1 - u0) * i / k, v0) for i in range(k + 1)] + [W(u1 - (u1 - u0) * i / k, v1) for i in range(k + 1)])
HONKAN = urect(-0.1, 57.34, -0.35, 13.5)                        # outer walls (glass line on the east), enough for the north

def _mech():
    m = r.File3dm.Read(os.path.join(ROOT, "model", "sodachiya_exact_mesh.3dm"))
    L = [l.Name for l in m.Layers]
    for o in m.Objects:
        if L[o.Attributes.LayerIndex].startswith("35_"):
            g = o.Geometry; V = [(g.Vertices[i].X / 1000, g.Vertices[i].Y / 1000) for i in range(len(g.Vertices))]
            ps = [Polygon([V[i] for i in dict.fromkeys(g.Faces[f])]) for f in range(len(g.Faces)) if len(set(g.Faces[f])) >= 3]
            U = unary_union([p.buffer(0) for p in ps if p.area > 1e-6])
            return U if U.geom_type == "Polygon" else max(U.geoms, key=lambda q: q.area)
MECH = _mech()                                                  # おむすび（機械室）

# ---- fence and gate of 読書の庭 (on the setback line n = 1.0)
FN = N["FENCE_N"]
def _fence_start():                                             # where the n = FN line leaves the 西館 skin, north end
    ln = LineString([T(0, FN), T(N["FENCE_T_END"], FN)])
    x = ln.difference(WS.buffer(0.001))
    seg = max(getattr(x, "geoms", [x]), key=lambda q: q.coords[-1][1])
    p0 = np.array(seg.coords[0]); return float((p0 - B0) @ t2)
T_FS = _fence_start()
G0, G1 = N["KOMICHI_GATE"]["t"]
FENCE = [[T(T_FS, FN), T(G0, FN)], [T(G1, FN), T(N["FENCE_T_END"], FN)]]
_q = np.array(T(N["FENCE_T_END"], FN)); _c = MECH.exterior.interpolate(MECH.exterior.project(Point(_q)))
FENCE.append([tuple(_q), (float(_c.x), float(_c.y))])          # short return to the おむすび wall
GATE = [T(G0, FN), T(G1, FN)]

# ---- 読書の庭: the pocket between 西館 (north face), 本館 (west wall) and the fence
_bulk = Polygon([T(T_FS - 0.5, FN), T(G0, FN), T(G0, 12), T(T_FS - 0.5, 12)])
_CLOSED = unary_union([WS, HONKAN]).buffer(0.4, join_style=2).buffer(-0.4, join_style=2)   # buildings + the expansion gap
_R = _bulk.difference(_CLOSED.buffer(0.02)).difference(MECH)
_R = _R if _R.geom_type == "Polygon" else max(_R.geoms, key=lambda q: q.area)
READ = _R.intersection(Point(T((T_FS + G0) / 2, FN + 1.5)).buffer(9)).buffer(0)
READ = READ if READ.geom_type == "Polygon" else max(READ.geoms, key=lambda q: q.area)
MOMIJI = (-10.35, -10.6)

# ---- the band along 西館 (west face + north-west face)
NEAR = WS.buffer(1.3)
BAND_W = BAND.intersection(NEAR).intersection(sbox(28.0, 70.0, -1, 3).union(tbox(-5.0, T_FS, -1, 3)))
BAND_W = BAND_W.difference(WS)
GW = N["GRAVEL_W"]
SL = N["DAIDO_SLIDE"]
GRAVEL = BAND_W.intersection(WS.buffer(GW).union(tbox(SL["t"][0], SL["t"][1], -1, 3).intersection(WS.buffer(SL["gravel_w"])))).difference(WS)
SP_ = N["STAFF_PATH"]
STAFF_PATH = BAND_W.intersection(sbox(SP_["s"][0], SP_["s"][1], -0.5, 3)).difference(GRAVEL)
DA = N["DAIDO_APRON"]
APRON = BAND_W.intersection(tbox(DA["t"][0], DA["t"][1], -0.5, 3))
RG = RAIN["N_GARDEN"]
RAINGARDEN = sbox(RG[0], RG[1], RG[2], RG[3])
PLANT = BAND_W.difference(GRAVEL).difference(STAFF_PATH).difference(APRON).difference(RAINGARDEN)
PLANT = unary_union([g for g in getattr(PLANT, "geoms", [PLANT]) if g.area > 0.2])
def _clean(g): return unary_union([q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and q.area > 0.2])
HEDGE = _clean(PLANT.intersection(sbox(N["HEDGE_S"][0], N["HEDGE_S"][1], -1, 3).union(tbox(N["HEDGE_T"][0], N["HEDGE_T"][1], -1, 3))))
LOW = _clean(PLANT.difference(HEDGE))

# ---- machine room: door on the north-west face, apron to the road
MD = N["MECH_DOOR"]; MA = N["MECH_APRON"]
MDOOR = [T(MD["t"][0], 1.16), T(MD["t"][1], 1.16)]
MAPRON = tbox(MA["t"][0], MA["t"][1], 0.0, 1.16).difference(MECH)
# the strip in front of おむすび beside the apron (low planting) and the 北の小径 mouth
MSTRIP = BAND.intersection(tbox(N["FENCE_T_END"], 32.5, -0.5, 1.16)).difference(MECH).difference(MAPRON)
MSTRIP = unary_union([g for g in getattr(MSTRIP, "geoms", [MSTRIP]) if g.area > 0.2])
# the band outside the fence (between the road and the 板塀), except in front of the gate
FSTRIP = _clean(BAND.intersection(tbox(T_FS, N["FENCE_T_END"], -0.5, FN)).difference(tbox(G0 - 0.2, G1 + 0.2, -0.5, FN)))
GAPRON = BAND.intersection(tbox(G0 - 0.2, G1 + 0.2, -0.5, FN))
MID = _clean(unary_union([FSTRIP, MSTRIP]))
KOMICHI = tbox(G0 - 0.2, G1 + 0.4, FN, 6).difference(HONKAN).difference(MECH)
KOMICHI = KOMICHI if KOMICHI.geom_type == "Polygon" else max(KOMICHI.geoms, key=lambda q: q.area)

if __name__ == "__main__":
    print("fence start t", round(T_FS, 2), "fence len", round(sum(LineString(f).length for f in FENCE[:2]), 2))
    print("読書の庭 m2", round(READ.area, 1), "植栽 m2", round(PLANT.area, 1), "砂利", round(GRAVEL.area, 1),
          "職員の道", round(STAFF_PATH.area, 1), "大戸の前", round(APRON.area, 1), "機械室の前", round(MAPRON.area, 1), "おむすびの前の植栽", round(MSTRIP.area, 1), "香りの刈り込み", round(HEDGE.area, 1), "低い草", round(LOW.area, 1), "中くらい", round(MID.area, 1))
