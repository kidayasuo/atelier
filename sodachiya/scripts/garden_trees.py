"""園庭の木の配置の下書き：林ごとにすきまを決めて点を置き、data/garden.json の TREES に書く。
一度書いたら図は TREES を読むので、ここを動かすのは林の組み方を変えるときだけ（手で直した木は消える）。
10-21 夜から TREES は手で直した（木の種類・噴水の木陰のケヤキ）。もう動かさないこと：動かすと種類が消える。"""
import json, os, random
import numpy as np
from shapely.geometry import Polygon, Point, LineString
import garden_common as gc

G = gc.G
rnd = random.Random(7)
trees = []


def ok(a, d, rmin, avoid):
    p = Point(a, d)
    if any(g.distance(p) < m for g, m in avoid):
        return False
    return all(np.hypot(a - t[0], d - t[1]) >= max(rmin, t[3]) for t in trees)


def put(a, d, kind, note=""):
    trees.append([round(a, 2), round(d, 2), kind, {"big": 3.0, "climb": 3.2, "mid": 2.1, "fruit": 2.3, "ever": 1.9}[kind], note])


# 避ける所
s = G["STREAM"]
stream = LineString(s["line"])
veh = LineString(G["VEHICLE"]["line"])
hut = Polygon([(G["HUT"]["a"][0] - 0.3, 0), (G["HUT"]["a"][1] + 0.3, 0), (G["HUT"]["a"][1] + 0.3, G["HUT"]["d"][1] + G["HUT"]["eave"] + 0.5), (G["HUT"]["a"][0] - 0.3, G["HUT"]["d"][1] + G["HUT"]["eave"] + 0.5)])
m = G["MOUND"]; a0, d0 = m["top"]
roll = Polygon([(a0 - 3.5, d0 + 0.5), (a0 + 7.5, d0 + 0.5), (a0 + 8.5, d0 + m["r_sw"] + 1.5), (a0 - 3.0, d0 + m["r_sw"] + 1.5)])   # 転がる斜面と原っぱの芯
field = Polygon([(36.0, 12.5), (45.5, 11.5), (47.0, 17.0), (38.0, 17.5)])
pool = Point(*G["FOUNTAIN"]["c"]).buffer(G["FOUNTAIN"]["r"][0] + 0.6)
sand = Polygon(G["SAND"]["poly"]).buffer(0.2)
look = Point(*G["LOOKOUT"]["c"]).buffer(2.0).union(Polygon([(54.4, 0), (56, 0), (56, 24), (54.4, 24)]))
splash = Point(*G["SPLASH"]["c"]).buffer(2.6); grain = Point(*G["GRAIN"]["c"]).buffer(2.0)
bowl = Point(*G["BOWL"]["c"]).buffer(G["BOWL"]["r"] - 0.3)
willow = Point(*G["WILLOW"]["c"]).buffer(2.2)
bank = LineString(G["BANK"]["line"])
edge = LineString([(a, gc.d_edge(a) - 2.0) for a in np.linspace(12, 54, 60)])
base_avoid = [(stream, 1.1), (veh, 1.6), (hut, 0.2), (roll, 0.01), (field, 0.01), (pool, 0), (sand, 0), (look, 0),
              (splash, 0), (grain, 0), (bowl, 0), (willow, 0), (edge, 0.01)]

# 決めて置く木
put(38.8, 4.0, "big", "築山の頂の木（エノキ）")
put(43.6, 12.6, "climb", "木登りの木（エノキ）")
put(33.4, 7.6, "big", "みずべの木陰（ケヤキ）")
put(36.6, 19.6, "big", "ホールの縁側の前（ムクノキ、夏の朝の日陰）")
put(41.2, 21.6, "fruit", "カキ")
put(24.2, 9.8, "fruit", "ジューンベリー（3歳の前）")
put(18.0, 4.0, "big", "北のもりの大木（コナラ）")

# 境の帯（北東の辺に沿って、d 1.5〜2.0）
a = 13.5
while a < 55.0:
    d = 1.6 + rnd.uniform(-0.1, 0.4)
    if ok(a, d, 2.0, [(hut, 0.2), (look, 0)]):
        put(a, d, "ever" if rnd.random() < 0.55 else "mid", "境")
    a += rnd.uniform(2.3, 3.0)


def fill(poly, n, kinds, rmin, extra=()):
    tries = 0; k = 0
    minx, miny, maxx, maxy = poly.bounds
    while k < n and tries < 4000:
        tries += 1
        a, d = rnd.uniform(minx, maxx), rnd.uniform(miny, maxy)
        if not poly.contains(Point(a, d)):
            continue
        if ok(a, d, rmin, base_avoid + list(extra)):
            put(a, d, rnd.choice(kinds)); k += 1


gpoly = Polygon([(a, d) for a, d in [(12.5, 0)] + [(56, 0), (56, 36)] + [(x, gc.d_edge(x)) for x in np.linspace(54, 12.5, 40)]])
north = Polygon([(12.5, 2.4), (21.5, 2.4), (21.5, 12), (12.5, 12)]).intersection(gpoly)
oku = Polygon([(46.0, 2.6), (55.2, 2.6), (55.2, 10.0), (47.5, 11.0)])
shizu = Polygon(G["BANK"]["line"][::-1] + [(40.0, 26.0), (53.0, 36.0), (53.2, 36.0)]).buffer(0)
shizu = Polygon([(40.6, 23.6), (44.5, 24.4), (48.5, 23.4), (52.0, 21.4), (53.2, 20.6), (53.2, 34.0), (40.0, 26.0)])
mound_ne = Polygon([(31.0, 2.4), (46.0, 2.4), (46.0, 4.0), (31.0, 4.0)])

fill(north, 10, ["mid", "mid", "big"], 2.2)
fill(oku, 14, ["mid", "big", "mid", "fruit"], 2.2)
fill(shizu, 18, ["mid", "mid", "fruit"], 2.3, [(bank, 1.4)])
fill(mound_ne, 3, ["mid"], 2.6)
# 縁側と小川のあいだ（3〜5 歳の前、縁側の前 1.5 m はあける）
front = Polygon([(a, gc.d_edge(a) - 1.6) for a in np.linspace(20, 40, 12)] + [(a, d) for a, d in [(40, 17.6), (33, 12.6), (27, 8.6), (20, 5.4)]])
fill(front, 6, ["mid", "fruit", "mid"], 2.6)
# 小川の岸のところどころ
for t in np.linspace(0.08, 0.9, 7):
    p = stream.interpolate(t, normalized=True)
    for side in (1.4, -1.4):
        q = stream.interpolate(min(1, t + 0.005), normalized=True)
        tx, ty = q.x - p.x, q.y - p.y; L = np.hypot(tx, ty) or 1
        a, d = p.x - ty / L * side, p.y + tx / L * side
        if rnd.random() < 0.8 and ok(a, d, 2.4, [(veh, 1.6), (roll, 0), (field, 0), (pool, 0), (sand, 0), (look, 0), (edge, 0)]):
            put(a, d, "mid", "川辺（アオダモ・ヤマボウシ）")

gp = Polygon(gc.XS([(12.5, 0), (56, 0), (56, 36)] + [(x, gc.d_edge(x)) for x in np.linspace(54, 12.5, 40)]))
trees = [t for t in trees if gc.SITE.buffer(-1.0).contains(Point(*gc.X(t[0], t[1])))]
F = G["FOUNTAIN"]; ca, sa = np.cos(np.radians(F["rot"])), np.sin(np.radians(F["rot"]))
fpoly = Polygon([(F["c"][0] + F["r"][0] * np.cos(q) * ca - F["r"][1] * np.sin(q) * sa, F["c"][1] + F["r"][0] * np.cos(q) * sa + F["r"][1] * np.sin(q) * ca) for q in np.linspace(0, 2 * np.pi, 48)])
trees = [t for t in trees if fpoly.distance(Point(t[0], t[1])) >= 0.8 and stream.distance(Point(t[0], t[1])) >= 0.9]
G["TREES"] = trees
json.dump(G, open(os.path.join(gc.ROOT, "data", "garden.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
from collections import Counter
print(len(trees), Counter(t[2] for t in trees))
