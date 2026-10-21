# ホールの北山杉の林：配列をつくる（data/forest.json の PARAMS を読み、TREES と CHANNEL を書き込む）
# 座標は本館の (u, v)。u＝南の妻から北へ、v＝西の外壁から東へ（m）。
# 3 版（10-21 夜、ユーザー）：
#  - あきは 0.4 以上（頭が挟まる 0.10〜0.23 を避け、こどもは横向きに抜けられる。速く動けなくてよい）。
#  - ひらけ・小部屋・見通しは決めない（疎密の中にできた空き地を、こどもが見つける）。梁を抜ける木はやめる（架構の線の下には立てない）。
#  - 内縁側と西吹き抜けにも生やす。
#  - 向きをもつ群（列・株立ち）で、見る向きで景色が変わる（KAIT 工房に学ぶ）。疎密は場所ごとの「残す割合」のむらで出す。
#  - 置いたあとで、東（縁側）から西（東の帯）へ抜けられる筋を経路探索で見つけ、そこだけあき 0.9 になるよう木を抜く（チャネル）。
# python sodachiya/scripts/forest_gen.py
import json, math, os, random, heapq
import numpy as np
from shapely.geometry import Point, LineString, box as sbox
from shapely.ops import unary_union
def R(u0, u1, v0, v1): return sbox(u0, v0, u1, v1)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "forest.json")
F = json.load(open(PATH))
P = F["PARAMS"]
U0, U1, V0, V1 = P["DOMAIN"]
GAP = P["GAP"]

CX, CY, RW = 194.66293237, -41.34826335, 205.0177
TH_S = math.atan2(-65.17347495 - CY, -8.9654788 - CX) % (2 * math.pi)
def Wm(u, v):
    th = TH_S - u / RW; r = RW - v
    return np.array((CX + r * math.cos(th), CY + r * math.sin(th)))

NOGO = unary_union([R(U0 - 1, P["FOOD"][0], V0 - 1, P["FOOD"][1]), R(*P["SLALOM"]["box"])]
                   + [R(uf - P["FRAME_OFF"], uf + P["FRAME_OFF"], V0 - 1, V1 + 1) for uf in P["FRAMES"]])
COLS = [(uf, vc) for uf in (21, 24, 27, 30) for vc in (0, 12)]

def field(u, v, ph):
    """残す割合（0〜1）：北西が密、南東（縁側・海峡の側）が疎ら、そこにゆるいむら（空き地と茂み）。"""
    g = P["FIELD"]
    t = ((u - g["dense"][0]) * (g["sparse"][0] - g["dense"][0]) + (v - g["dense"][1]) * (g["sparse"][1] - g["dense"][1])) / \
        ((g["sparse"][0] - g["dense"][0]) ** 2 + (g["sparse"][1] - g["dense"][1]) ** 2)
    base = g["hi"] + (g["lo"] - g["hi"]) * min(1, max(0, t))
    n = sum(math.sin(k1 * u + k2 * v + p) for (k1, k2, p) in ph) / len(ph)
    return min(1, max(0, base + g["noise"] * n))

def ok(u, v, d, trees, gap=GAP):
    if not (U0 <= u <= U1 and V0 <= v <= V1): return False
    pt = Point(u, v)
    if NOGO.contains(pt) or NOGO.distance(pt) < d / 2: return False
    for (a, b) in COLS:
        if math.hypot(u - a, v - b) < gap + d / 2 + 0.2: return False
    for (a, b, dd, *_) in trees:
        if (u - a) ** 2 + (v - b) ** 2 < (gap + (d + dd) / 2) ** 2: return False
    return True

def lattice(g, rng):
    a = math.radians(g["ang"]); ea = np.array([math.cos(a), math.sin(a)]); eb = np.array([-ea[1], ea[0]])
    c = np.array(g["c"]); pts = []
    nr = int(g["B"] / g["row"]) + 2; npch = int(g["L"] / g["pitch"]) + 2
    for i in range(-nr, nr + 1):
        off = (i * g["stag"] % 1.0) * g["pitch"]
        for j in range(-npch, npch + 1):
            x = j * g["pitch"] + off + rng.uniform(-g["jit"], g["jit"]); y = i * g["row"] + rng.uniform(-g["jit"] * 0.6, g["jit"] * 0.6)
            q = (x / (g["L"] / 2)) ** 2 + (y / (g["B"] / 2)) ** 2
            if q > 1 + 0.2 * math.sin(3 * math.atan2(y, x) + g.get("phase", 0)): continue
            p = c + ea * x + eb * y
            pts.append((p[0], p[1], rng.random()))
    rng.shuffle(pts)
    return pts, ea

def beam_fix(u, half):
    """架構の線（梁 2 枚組：線から ±0.09〜0.18 が梁の板、あいだ 0.18）。幹（u 方向の半幅 half）が板に当たるなら、
    少しずらして板のあいだに入れるか、板の外へ出す。決まりではなく、立った位置がたまたま梁のあいだなら抜けて屋根まで。"""
    for uf in P["FRAMES"]:
        x = u - uf
        if abs(x) - half >= 0.185 or (abs(x) + half <= 0.085): continue
        if half <= 0.085:
            xin = max(-(0.085 - half), min(0.085 - half, x))
            if abs(xin - x) <= 0.06: return uf + xin
        xo = math.copysign(0.185 + half, x if x != 0 else 1)
        if abs(xo - x) <= 0.15: return uf + xo
        return None
    return u

def grow(seed):
    rng = random.Random(seed)
    ph = [(rng.uniform(0.6, 1.4) * s1, rng.uniform(0.6, 1.4) * s2, rng.uniform(0, 6.28)) for s1, s2 in [(1.1, 0.4), (0.3, 0.9), (0.8, -0.7)]]
    trees = []
    if P["NUSHI"]["on"]: trees.append((*P["NUSHI"]["c"], P["NUSHI"]["d"], "ぬし"))
    for row in P["SLALOM"]["rows"]:                                  # 減速の茂み：あき 0.7 の口を左右互い違いに開けた列
        u = row["u"]; v = row["v"][0]
        while v <= row["v"][1] + 1e-9:
            if row["open"][0] - 0.03 < v < row["open"][1] + 0.03:
                v = row["open"][1] + 0.03; continue
            k = rng.choice([1, 2, 2, 3]); d = rng.choice(P["PAIR_D"])
            span = k * d
            if v + span > row["v"][1] + d or (v < row["open"][0] < v + span + 0.4 and v + span > row["open"][0] - 0.0):
                k = 1; span = d
            if not (v + span <= row["open"][0] or v >= row["open"][1]):
                v = row["open"][1] + 0.03; continue
            for j in range(k):
                trees.append((u, v + d / 2 + j * d, d, "減速の茂み" + ("・株立ち" if k > 1 else "")))
            v += span + P["GAP"] + 0.01
    for g in P["GROUPS"]:
        pts, ea = lattice(g, rng)
        for (u, v, r) in pts:
            if r > max(field(u, v, ph), g.get("keep_min", 0)): continue   # 疎密のむら
            rr = rng.random(); k = 3 if rr < g["triple"] else (2 if rr < g["triple"] + g["pair"] else 1)
            if k > 1:
                d = rng.choice(P["PAIR_D"])
                u = beam_fix(u, abs(ea[0]) * (k - 1) * d / 2 + d / 2)
                if u is None: continue
                if ok(u, v, k * d, trees):
                    for j in range(k):
                        o = (j - (k - 1) / 2) * d
                        trees.append((u + ea[0] * o, v + ea[1] * o, d, g["name"] + "・株立ち"))
                continue
            d = rng.choices(P["D"], weights=g["dw"])[0]
            u = beam_fix(u, d / 2)
            if u is None: continue
            if ok(u, v, d, trees): trees.append((u, v, d, g["name"]))
    return trees, ph

# ---------------------------------------------------------------- channel: found after planting
def find_channel(trees):
    """東の帯の側（v = V0）から縁側のガラス戸（v = V1）へ。木を抜く数が少なく、短い経路（折れてよい）。
    格子 0.1 m、セルの費用＝1＋（そのセルの 0.45＋r 以内にある木の数）× 重み。"""
    h = 0.1; us = np.arange(22.6, 29.95, h); vs = np.arange(V0 - 0.3, V1 + 0.15, h)
    cost = np.ones((len(us), len(vs)))
    UU, VV = np.meshgrid(us, vs, indexing="ij")
    for (a, b, dd, *_) in trees:
        m = (UU - a) ** 2 + (VV - b) ** 2 < (P["CHANNEL"]["clear"] / 2 + dd / 2) ** 2
        cost[m] += P["CHANNEL"]["w_tree"]
    # 架構の柱の近く・配膳の道は通らない
    for (a, b) in COLS:
        cost[(UU - a) ** 2 + (VV - b) ** 2 < (0.2 + P["CHANNEL"]["clear"] / 2) ** 2] = 1e6
    cost[UU < P["CHANNEL"]["u_min"]] = 1e6                          # 海峡がすでに南の筋なので、林の中を通す
    dist = np.full(cost.shape, np.inf); prev = {}
    pq = []
    for i in range(len(us)):
        dist[i, 0] = cost[i, 0]; heapq.heappush(pq, (dist[i, 0], i, 0))
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    end = None
    while pq:
        dcur, i, j = heapq.heappop(pq)
        if dcur > dist[i, j]: continue
        if j == len(vs) - 1: end = (i, j); break
        for di, dj, s in nb:
            a, b = i + di, j + dj
            if 0 <= a < len(us) and 0 <= b < len(vs):
                nd = dcur + cost[a, b] * s
                if nd < dist[a, b]: dist[a, b] = nd; prev[(a, b)] = (i, j); heapq.heappush(pq, (nd, a, b))
    path = [end]
    while path[-1] in prev: path.append(prev[path[-1]])
    pts = [(us[i], vs[j]) for i, j in path[::-1]]
    return LineString(pts).simplify(0.25)

def find_slalom(trees):
    """内縁側のホールの南の端（減速の茂み）：北から南へ、大人がけがの子を抱えて通れるあき 0.7 の道。
    茂みの列（東西）を横切るので、抜く木が少ない経路はおのずと曲がる。"""
    S = P["SLALOM"]; h = 0.05
    us = np.arange(S["u"][0], S["u"][1] + 1e-9, h); vs = np.arange(S["v"][0], S["v"][1] + 1e-9, h)
    UU, VV = np.meshgrid(us, vs, indexing="ij"); cost = np.ones(UU.shape)
    for (a, b, dd, *_) in trees:
        cost[(UU - a) ** 2 + (VV - b) ** 2 < (S["clear"] / 2 + dd / 2) ** 2] += S["w_tree"]
    for (a, b) in COLS:
        cost[(UU - a) ** 2 + (VV - b) ** 2 < (0.2 + S["clear"] / 2) ** 2] = 1e6
    cost[VV > 13.5 - S["clear"] / 2] = 1e6                          # ガラス戸から 0.35
    dist = np.full(cost.shape, np.inf); prev = {}; pq = []
    top_i = len(us) - 1
    for j in range(len(vs)): dist[top_i, j] = cost[top_i, j]; heapq.heappush(pq, (dist[top_i, j], top_i, j))
    nb = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    end = None
    while pq:
        dcur, i, j = heapq.heappop(pq)
        if dcur > dist[i, j]: continue
        if i == 0: end = (i, j); break
        for di, dj, sc in nb:
            a, b = i + di, j + dj
            if 0 <= a < len(us) and 0 <= b < len(vs):
                nd = dcur + cost[a, b] * sc
                if nd < dist[a, b]: dist[a, b] = nd; prev[(a, b)] = (i, j); heapq.heappush(pq, (nd, a, b))
    path = [end]
    while path[-1] in prev: path.append(prev[path[-1]])
    return LineString([(us[i], vs[j]) for i, j in path[::-1]]).simplify(0.02)

def longest_run(trees, body=0.3):
    REGION = R(22.6, 29.9, -0.0, 13.3).difference(R(U0 - 1, P["FOOD"][0], V0 - 1, P["FOOD"][1]))
    obst = unary_union([Point(a, b).buffer(dd / 2 + body, 10) for a, b, dd, *_ in trees])
    best = (0, None)
    for ang in np.radians(np.arange(0, 180, 10)):
        dv = np.array([math.cos(ang), math.sin(ang)]); nv = np.array([-dv[1], dv[0]])
        for off in np.arange(-16, 16, 0.25):
            base = np.array([26.3, 6.5]) + nv * off
            ln = LineString([tuple(base - dv * 20), tuple(base + dv * 20)]).intersection(REGION)
            if ln.is_empty: continue
            free = ln.difference(obst)
            for g in getattr(free, "geoms", [free]):
                if g.geom_type == "LineString" and g.length > best[0]: best = (g.length, g)
    return best

def pockets(trees, n=6):
    """空き地の例（決めない、記録だけ）：幹から最も遠い点を順に。半径と場所。"""
    obst = [(a, b, dd) for a, b, dd, *_ in trees]
    pts = []
    for u in np.arange(23.0, 29.6, 0.1):
        for v in np.arange(0.2, 13.2, 0.1):
            if u < P["FOOD"][0] and v < P["FOOD"][1]: continue
            r = min([math.hypot(u - a, v - b) - dd / 2 for a, b, dd in obst] + [u - 22.5, 30 - u, v + 0.0 + 0.9, 13.5 - v])
            pts.append((r, u, v))
    pts.sort(reverse=True); out = []
    for r, u, v in pts:
        if all(math.hypot(u - a, v - b) > 1.5 for _, a, b in out): out.append((round(r, 2), round(u, 2), round(v, 2)))
        if len(out) >= n: break
    return out

if __name__ == "__main__":
    res = []
    for seed in range(P["SEEDS"]):
        t, ph = grow(seed)
        ch = find_channel(t)
        band = ch.buffer(P["CHANNEL"]["clear"] / 2)
        removed = [x for x in t if band.distance(Point(x[0], x[1])) < x[2] / 2 and x[3] != "ぬし"]
        t2 = [x for x in t if x not in removed]
        sl = find_slalom(t2); sband = sl.buffer(P["SLALOM"]["clear"] / 2)
        srem = [x for x in t2 if sband.distance(Point(x[0], x[1])) < x[2] / 2]
        t2 = [x for x in t2 if x not in srem]
        L, g = longest_run(t2)
        res.append((round(L * 2) / 2, len(removed), -len(t2), seed, t2, ch, removed, L, g, sl, srem))
        print(seed, len(t2), "removed", len(removed), "run", round(L, 2), "channel", round(ch.length, 1))
    res.sort(key=lambda r: (r[0], r[1], r[2]))
    _, nrem, _, seed, trees, ch, removed, L, g, sl, srem = res[0]
    gang = {gg["name"]: gg["ang"] for gg in P["GROUPS"]}
    out = []
    for a, b, dd, grp in trees:
        t = {"u": round(a, 3), "v": round(b, 3), "d": dd, "group": grp, "shape": "round"}
        if grp in gang and dd >= P["TAIKO"]["min_d"]:
            t["shape"] = "taiko"; t["t"] = round(dd * P["TAIKO"]["ratio"], 3); t["ang"] = gang[grp]
        t["xy_mm"] = [round(c * 1000, 1) for c in Wm(a, b)]
        out.append(t)
    F["TREES"] = out
    RM = P["REMOVABLE"]
    for t in out:
        t["removable"] = bool(RM["u"][0] <= t["u"] <= RM["u"][1] and RM["v"][0] <= t["v"] <= RM["v"][1]
                              and not any(t["group"].startswith(x) for x in RM["exclude"]) and t["d"] <= 0.1)
    F["SLALOM"] = {"line_uv": [[round(x, 2), round(y, 2)] for x, y in sl.coords], "length": round(sl.length, 2),
                   "removed": [[round(a, 2), round(b, 2), dd] for a, b, dd, *_ in srem]}
    F["CHANNEL"] = {"line_uv": [[round(x, 2), round(y, 2)] for x, y in ch.coords], "length": round(ch.length, 2),
                    "removed": [[round(a, 2), round(b, 2), dd] for a, b, dd, *_ in removed]}
    F["RESULT"] = {"seed": seed, "n": len(trees), "removed_for_channel": nrem, "longest_run": round(L, 2),
                   "longest_run_line": [[round(x, 2) for x in c] for c in g.coords] if g is not None else None,
                   "pockets_r_u_v": pockets(trees)}
    json.dump(F, open(PATH, "w"), ensure_ascii=False, indent=1)
    print("chose", seed, len(trees), "removed", nrem, "run", round(L, 2), F["RESULT"]["pockets_r_u_v"][:4])
