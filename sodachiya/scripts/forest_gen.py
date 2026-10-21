# ホールの北山杉の林：配列をつくる（data/forest.json の PARAMS を読み、TREES を書き込む）
# 座標は本館の (u, v)。u＝南の妻から北へ、v＝西の外壁から東へ（m）。
# python sodachiya/scripts/forest_gen.py   （乱数の種を変えて最もよい配列を選ぶ）
import json, math, os, random
import numpy as np
from shapely.geometry import Point, LineString, box as sbox
from shapely.ops import unary_union
def R(u0, u1, v0, v1): return sbox(u0, v0, u1, v1)      # (u, v) の矩形

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "forest.json")
F = json.load(open(PATH))
P = F["PARAMS"]

U0, U1, V0, V1 = P["DOMAIN"]                       # 幹の中心が置ける範囲
GAP = P["GAP"]                                     # 幹と幹のあき（最小）
CL = P["CLEARING"]                                 # ひらけ：中心と半径
ROOM = P["ROOM"]                                   # 林の小部屋
VIEW = P["VIEW"]                                   # 築山の頂への見通し
HIEI = math.radians(P["HIEI_BEARING"])

# 方位 → (u, v) の向き（ホールの中ほどで）
CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX) % (2 * math.pi)
def Wm(u, v):
    th = TH_S - u / RW; r = RW - v
    return np.array((CX + r * math.cos(th), CY + r * math.sin(th)))
uc, vc = 26.0, 6.0
eu = Wm(uc + 0.5, vc) - Wm(uc - 0.5, vc); ev = Wm(uc, vc + 0.5) - Wm(uc, vc - 0.5)
tgt = np.array([math.sin(HIEI), math.cos(HIEI)])
duv = np.linalg.solve(np.column_stack([eu, ev]), tgt); duv = duv / np.linalg.norm(duv)

def view_line():
    c = np.array(CL["c"]); t = (VIEW["v_end"] - c[1]) / duv[1]
    return LineString([tuple(c), tuple(c + duv * t)])

# 置けない所
NOGO = unary_union([
    R(U0 - 1, P["FOOD"][0], V0 - 1, P["FOOD"][1]),             # 配膳の道（東の帯 → ホールの西 → 飛び石）
    Point(CL["c"]).buffer(CL["r"]),                                # ひらけ
    view_line().buffer(VIEW["w"] / 2, cap_style=2),                # 見通し
])
FRAMEZ = unary_union([R(uf - P["FRAME_OFF"], uf + P["FRAME_OFF"], V0 - 1, V1 + 1) for uf in P["FRAMES"]])

def snap(u, d):
    """架構の線の近く：線の上（梁の 2 枚のあいだを抜ける、φ100 以下）か、0.3 以上離す。"""
    for uf in P["FRAMES"]:
        if abs(u - uf) < P["FRAME_OFF"]:
            return (uf if d <= P["THREAD_MAX_D"] else None)
    return u

def dens(u, v):
    """その場所の追加のあき（0＝いちばん密）。北西の奥が密、縁側・海峡の側・ひらけのまわりは疎ら。"""
    core = np.array(P["CORE"])
    d = math.hypot(u - core[0], v - core[1])
    e = P["EXTRA"][0] + (P["EXTRA"][1] - P["EXTRA"][0]) * min(1, d / P["CORE_R"]) ** 1.5
    if v > 10.0: e += 0.25 * (v - 10.0) / 1.6                     # 縁側に寄るほど疎ら
    if u < 23.6: e += 0.25                                         # 海峡の縁
    return e

COLS = [(uf, vc) for uf in (21, 24, 27, 30) for vc in (0, 12)]   # 架構の柱（400×180、半径 0.2 とみる）

def ok(p, d, trees):
    u, v = p
    if not (U0 <= u <= U1 and V0 <= v <= V1): return False
    if NOGO.contains(Point(u, v)) or NOGO.distance(Point(u, v)) < d / 2: return False
    e = dens(u, v)
    for (a, b) in COLS:
        if math.hypot(u - a, v - b) < GAP + d / 2 + 0.2: return False
    for (a, b, dd) in trees:
        need = GAP + (d + dd) / 2 + max(e, dens(a, b)) * 0.5 + min(e, dens(a, b)) * 0.5
        if (u - a) ** 2 + (v - b) ** 2 < need ** 2: return False
    return True

def pick_d(u, v, rng):
    e = dens(u, v); w = P["D_WEIGHTS_CORE"] if e < 0.35 else P["D_WEIGHTS_EDGE"]
    return rng.choices(P["D"], weights=w)[0]

def grow(seed):
    rng = random.Random(seed)
    trees = []
    # 林の小部屋：小さな輪
    c = np.array(ROOM["c"])
    for k in range(ROOM["n"]):
        a = ROOM["a0"] + 2 * math.pi * k / ROOM["n"]
        d = 0.10 if k % 2 == 0 else 0.07
        trees.append((c[0] + ROOM["R"] * math.cos(a), c[1] + ROOM["R"] * math.sin(a), d))
    trees.append((*P["NUSHI"]["c"], P["NUSHI"]["d"])) if P["NUSHI"]["on"] else None
    for (a, b, dd) in P["FIXED"]: trees.append((a, b, dd))
    for _ in range(60000):
        u = rng.uniform(U0, U1); v = rng.uniform(V0, V1)
        d = pick_d(u, v, rng)
        u = snap(u, d)
        if u is None: continue
        if Point(u, v).distance(Point(*ROOM["c"])) < ROOM["R"] + 0.2: continue
        if ok((u, v), d, trees): trees.append((u, v, d))
    return trees

# 林の中（へりの帯・配膳の道・ひらけを除く）
REGION = R(23.4, 29.6, 0.4, 11.5).difference(R(U0 - 1, P["FOOD"][0], V0 - 1, P["FOOD"][1])).difference(Point(CL["c"]).buffer(CL["r"] + 0.3))

def longest_run(trees, body=0.3):
    """子どもが（腕を振って幅 0.6 で）まっすぐ走れるいちばん長い直線（林の中だけ）。"""
    obst = unary_union([Point(a, b).buffer(dd / 2 + body, 12) for a, b, dd in trees]
                       + [R(U0 - 0.6, U1 + 0.6, 11.9, 12.6), R(29.9, 30.6, -0.2, 12.6), R(22.0, 22.5 + 0.02, -0.2, 12.6)])
    best = (0, None)
    for ang in np.radians(np.arange(0, 180, 10)):
        dv = np.array([math.cos(ang), math.sin(ang)])
        nv = np.array([-dv[1], dv[0]])
        for off in np.arange(-16, 16, 0.3):
            base = np.array([26.3, 6.0]) + nv * off
            ln = LineString([tuple(base - dv * 20), tuple(base + dv * 20)]).intersection(REGION)
            if ln.is_empty: continue
            free = ln.difference(obst)
            for g in getattr(free, "geoms", [free]):
                if g.geom_type != "LineString": continue
                if g.length > best[0]: best = (g.length, g)
    return best

def break_runs(trees, rng, target):
    """まっすぐ走れる線が target より長ければ、その線の上に 1 本ずつ足す。"""
    for _ in range(60):
        L, g = longest_run(trees)
        if L <= target or g is None: break
        placed = False
        for f in (0.5, 0.4, 0.6, 0.3, 0.7, 0.25, 0.75):
            p = g.interpolate(f, normalized=True)
            for du in (0, 0.15, -0.15, 0.3, -0.3):
                for dv in (0, 0.15, -0.15, 0.3, -0.3):
                    d = rng.choice(P["D"]); u = snap(p.x + du, d)
                    if u is None: continue
                    if ok((u, p.y + dv), d, trees):
                        trees.append((u, p.y + dv, d)); placed = True; break
                if placed: break
            if placed: break
        if not placed: break
    return trees

if __name__ == "__main__":
    res = []
    for seed in range(P["SEEDS"]):
        t = grow(seed); t = break_runs(t, random.Random(seed + 1000), P["RUN_TARGET"]); L, g = longest_run(t)
        res.append((L, -len(t), seed, t, g))
        print(seed, len(t), round(L, 2))
    res.sort(key=lambda r: (round(r[0] * 2) / 2, r[1]))
    L, n, seed, trees, g = res[0]
    F["TREES"] = [{"u": round(a, 2), "v": round(b, 2), "d": dd,
                   "xy_mm": [round(c * 1000, 1) for c in Wm(round(a, 2), round(b, 2))]} for a, b, dd in trees]
    F["RESULT"] = {"seed": seed, "n": len(trees), "longest_run": round(L, 2),
                   "longest_run_line": [[round(x, 2) for x in c] for c in g.coords] if g is not None else None,
                   "view_dir_uv": [round(x, 4) for x in duv]}
    json.dump(F, open(PATH, "w"), ensure_ascii=False, indent=1)
    print("chose", seed, len(trees), round(L, 2))
