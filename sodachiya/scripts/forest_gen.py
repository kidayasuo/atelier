# ホールの北山杉の林：配列をつくる（data/forest.json の PARAMS を読み、TREES を書き込む）
# 座標は本館の (u, v)。u＝南の妻から北へ、v＝西の外壁から東へ（m）。
# 2 版（10-21 夜）：向きをもつ「群」で組む。群の中では木が列に並び、列に沿って見ると透け、列を横切って見ると幹が重なって壁になる。
# 群と群のあいだは空き地（疎）。KAIT 工房（石上純也）の、柱の向きで見え方が変わる考え方を、丸い幹の「並びの向き」に置き換えた。
# python sodachiya/scripts/forest_gen.py
import json, math, os, random
import numpy as np
from shapely.geometry import Point, LineString, box as sbox
from shapely.ops import unary_union
def R(u0, u1, v0, v1): return sbox(u0, v0, u1, v1)      # (u, v) の矩形

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "forest.json")
F = json.load(open(PATH))
P = F["PARAMS"]

U0, U1, V0, V1 = P["DOMAIN"]
GAP = P["GAP"]
CL = P["CLEARING"]
ROOM = P["ROOM"]
VIEW = P["VIEW"]
HIEI = math.radians(P["HIEI_BEARING"])

CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX) % (2 * math.pi)
def Wm(u, v):
    th = TH_S - u / RW; r = RW - v
    return np.array((CX + r * math.cos(th), CY + r * math.sin(th)))
uc, vc = 26.0, 6.0
eu = Wm(uc + 0.5, vc) - Wm(uc - 0.5, vc); ev = Wm(uc, vc + 0.5) - Wm(uc, vc - 0.5)
tgt = np.array([math.sin(HIEI), math.cos(HIEI)])
duv = np.linalg.solve(np.column_stack([eu, ev]), tgt); duv = duv / np.linalg.norm(duv)
HIEI_UV_DEG = math.degrees(math.atan2(duv[1], duv[0]))           # (u, v) の面での向き（+u から +v へ）

def view_line():
    c = np.array(CL["c"]); t = (VIEW["v_end"] - c[1]) / duv[1]
    return LineString([tuple(c), tuple(c + duv * t)])

NOGO = unary_union([
    R(U0 - 1, P["FOOD"][0], V0 - 1, P["FOOD"][1]),
    Point(CL["c"]).buffer(CL["r"]),
    view_line().buffer(VIEW["w"] / 2, cap_style=2),
    Point(ROOM["c"]).buffer(ROOM["hole"]),                          # 林の小部屋（列の目を抜いた穴）
])
COLS = [(uf, vc_) for uf in (21, 24, 27, 30) for vc_ in (0, 12)]

def frame_ok(u, d):
    """架構の線の近く：線の上（梁の 2 枚のあいだを抜ける、φ100 以下）にちょうど乗るか、0.3 以上離れているか。"""
    for uf in P["FRAMES"]:
        if abs(u - uf) < P["FRAME_OFF"]:
            if abs(u - uf) <= P["THREAD_SNAP"] and d <= P["THREAD_MAX_D"]: return uf
            return None
    return u

def ok(u, v, d, trees, gap=GAP):
    if not (U0 <= u <= U1 and V0 <= v <= V1): return False
    pt = Point(u, v)
    if NOGO.contains(pt) or NOGO.distance(pt) < d / 2: return False
    for (a, b) in COLS:
        if math.hypot(u - a, v - b) < gap + d / 2 + 0.2: return False
    for (a, b, dd, *_ ) in trees:
        if (u - a) ** 2 + (v - b) ** 2 < (gap + (d + dd) / 2) ** 2: return False
    return True

def group_points(g, rng):
    """群：中心 c、列の向き ang（(u, v) の面で +u から +v へ、度）、列に沿う長さ L・横切る幅 B、
    列の中の間隔 pitch、列と列の間隔 row、隣の列のずらし stag（pitch の割合）。輪郭は楕円にゆらぎ、縁ほど抜ける。"""
    a = math.radians(g["ang"]); ea = np.array([math.cos(a), math.sin(a)]); eb = np.array([-ea[1], ea[0]])
    c = np.array(g["c"]); pts = []
    nr = int(g["B"] / g["row"]) + 2; npch = int(g["L"] / g["pitch"]) + 2
    for i in range(-nr, nr + 1):
        y = i * g["row"]
        off = (i * g["stag"] % 1.0) * g["pitch"]
        for j in range(-npch, npch + 1):
            x = j * g["pitch"] + off + rng.uniform(-g["jit"], g["jit"])
            yy = y + rng.uniform(-g["jit"] * 0.5, g["jit"] * 0.5)
            q = (x / (g["L"] / 2)) ** 2 + (yy / (g["B"] / 2)) ** 2
            wob = 1 + 0.18 * math.sin(3 * math.atan2(yy, x) + g.get("phase", 0))
            if q > wob: continue
            if q > 0.55 * wob and rng.random() < g["edge_drop"] * (q / wob - 0.55) / 0.45: continue
            p = c + ea * x + eb * yy
            pts.append((p[0], p[1], q))
    pts.sort(key=lambda t: t[2])                                   # 群の芯から置く
    return pts

def grow(seed):
    rng = random.Random(seed)
    trees = []
    c = np.array(ROOM["c"])
    for k in range(ROOM["n"]):                                     # 林の小部屋
        a = ROOM["a0"] + 2 * math.pi * k / ROOM["n"]
        trees.append((c[0] + ROOM["R"] * math.cos(a), c[1] + ROOM["R"] * math.sin(a), 0.1 if k % 2 == 0 else 0.07, "room"))
    if P["NUSHI"]["on"]: trees.append((*P["NUSHI"]["c"], P["NUSHI"]["d"], "nushi"))
    for (a, b, dd) in P["FIXED"]: trees.append((a, b, dd, "light"))
    for g in P["GROUPS"]:
        a = math.radians(g["ang"]); ea = np.array([math.cos(a), math.sin(a)])
        for (u, v, q) in group_points(g, rng):
            rr = rng.random(); k = 3 if rr < g.get("triple", 0) else (2 if rr < g.get("triple", 0) + g.get("pair", 0) else 1)
            if k > 1:                                              # 株立ち：2〜3 本が触れあって立つ（あきは 0、列の向きに並ぶ）
                d = rng.choice(P["PAIR_D"]); u2 = frame_ok(u, k * d)
                if u2 is None or (u2 != u and abs(ea[0]) > 0.2): continue
                if ok(u2, v, k * d, trees):
                    for j in range(k):
                        o = (j - (k - 1) / 2) * d
                        trees.append((u2 + ea[0] * o, v + ea[1] * o, d, g["name"] + "・株立ち"))
                continue
            d = rng.choices(P["D"], weights=g["dw"])[0]
            u2 = frame_ok(u, d)
            if u2 is None: continue
            if ok(u2, v, d, trees): trees.append((u2, v, d, g["name"]))
    # はぐれ木：空き地に少しだけ（広いあき）
    n = 0
    for _ in range(20000):
        if n >= P["STRAYS"]["n"]: break
        u = rng.uniform(U0, U1); v = rng.uniform(V0, V1); d = rng.choice(P["D"])
        u2 = frame_ok(u, d)
        if u2 is None: continue
        if ok(u2, v, d, trees, gap=P["STRAYS"]["gap"]): trees.append((u2, v, d, "stray")); n += 1
    return trees

REGION = R(23.4, 29.6, 2.0, 11.5).difference(R(U0 - 1, P["FOOD"][0], V0 - 1, P["FOOD"][1])).difference(Point(CL["c"]).buffer(CL["r"] + 0.3))

def longest_run(trees, body=0.3):
    obst = unary_union([Point(a, b).buffer(dd / 2 + body, 12) for a, b, dd, *_ in trees]
                       + [R(U0 - 0.6, U1 + 0.6, 11.9, 12.6), R(29.9, 30.6, -0.2, 12.6), R(22.0, 22.52, -0.2, 12.6)])
    best = (0, None)
    for ang in np.radians(np.arange(0, 180, 10)):
        dv = np.array([math.cos(ang), math.sin(ang)]); nv = np.array([-dv[1], dv[0]])
        for off in np.arange(-16, 16, 0.3):
            base = np.array([26.3, 6.0]) + nv * off
            ln = LineString([tuple(base - dv * 20), tuple(base + dv * 20)]).intersection(REGION)
            if ln.is_empty: continue
            free = ln.difference(obst)
            for g in getattr(free, "geoms", [free]):
                if g.geom_type == "LineString" and g.length > best[0]: best = (g.length, g)
    return best

if __name__ == "__main__":
    res = []
    for seed in range(P["SEEDS"]):
        t = grow(seed); L, g = longest_run(t)
        res.append((round(L * 2) / 2, -len(t), seed, t, g, L))
        print(seed, len(t), round(L, 2))
    res.sort(key=lambda r: (r[0], r[1]))
    _, _, seed, trees, g, L = res[0]
    gang = {g["name"]: g["ang"] for g in P["GROUPS"]}
    out = []
    for a, b, dd, grp in trees:
        t = {"u": round(a, 2), "v": round(b, 2), "d": dd, "group": grp, "shape": "round"}
        if grp in gang and dd >= P["TAIKO"]["min_d"]:                # 株立ちは丸太のまま
            t["shape"] = "taiko"; t["t"] = round(dd * P["TAIKO"]["ratio"], 3); t["ang"] = gang[grp]   # 平らな面を列の向きに
        t["xy_mm"] = [round(c * 1000, 1) for c in Wm(round(a, 2), round(b, 2))]
        out.append(t)
    F["TREES"] = out
    F["RESULT"] = {"seed": seed, "n": len(trees), "longest_run": round(L, 2),
                   "longest_run_line": [[round(x, 2) for x in c] for c in g.coords] if g is not None else None,
                   "view_dir_uv": [round(x, 4) for x in duv], "hiei_uv_deg": round(HIEI_UV_DEG, 1)}
    json.dump(F, open(PATH, "w"), ensure_ascii=False, indent=1)
    print("chose", seed, len(trees), round(L, 2), "hiei_uv_deg", round(HIEI_UV_DEG, 1))
