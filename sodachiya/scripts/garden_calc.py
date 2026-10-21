"""園庭の数字の確かめ：土の釣り合い、小川の水の量、夏の床の噴水の日陰。
結果は out/garden_calc.json（図 garden01 の数字とは別に、説明の根拠として残す）。"""
import json, math, os
import numpy as np
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely.affinity import translate
import garden_common as gc

G = gc.G
OUT = {}
STEP = 0.25
GA = np.arange(10.0, 57.01, STEP); GD = np.arange(-1.0, 37.01, STEP)
AA, DD = np.meshgrid(GA, GD)
gpoly = Polygon([gc.AD(*p) for p in gc.garden_poly().exterior.coords])
inside = np.vectorize(lambda a, d: gpoly.contains(Point(a, d)))(AA, DD)
cell = STEP * STEP

# ---------------- 土の釣り合い ----------------
h_all = gc.height(AA, DD)
bowl = gc.bowl_h(AA, DD)
hp = np.where(inside, h_all - bowl, 0.0)          # 盛り（すりばちを除いた地形の高さ）
fill = float(np.clip(hp, 0, None).sum() * cell)
bowl_cut = float(-np.where(inside, bowl, 0).sum() * cell)
s = G["STREAM"]; s_len = LineString(s["line"]).length
stream_cut = s_len * 0.8 * 0.35                   # 川床の掘り（石を据える幅 0.8、深さ 平均 0.35）
r = G["AMAOCHI"]; rain_cut = (r["u"][1] - r["u"][0]) * 0.8 * 0.35   # 雨の川（玉石の下地を含む）
F = G["FOUNTAIN"]; fount_cut = math.pi * F["r"][0] * F["r"][1] * 0.35   # 床の噴水の下地・配管
SP = G["SPLASH"]; splash_cut = math.pi * SP["r"][0] ** 2 * 0.3
pit_cut = math.pi * 1.6 ** 2 * 0.55              # 遊戯室の穴の底（φ3.2、−450＋マットと下地）
# 建物の根切り。案 A＝ベタ基礎（深さ 約 0.4 m、外へ 0.3 m 広く）。
# 案 B＝布基礎＋土間：根切りは基礎の下だけ（幅 0.6×深さ 0.5）。床の下は表土を 0.10 剥ぎ、掘った下の土で 0.10 埋め戻して締め固め、その上に砕石・断熱・土間。
foot = 57 * 15.0 + 366 + 30                         # 本館 57×15、西館 約 366、おむすび 30
found_A = (foot + 0.3 * 2 * (57 + 15 + 80)) * 0.4
footing_len = 3 * 57 + 20 * 15 + 125 + 25          # 本館の柱の列 3 本＋架構 20 本、西館の外周と間仕切り、おむすび（目安）
found_B = footing_len * 0.6 * 0.5
top_B = foot * 0.10
backfill_B = foot * 0.10
garden_cut = bowl_cut + stream_cut + rain_cut + fount_cut + splash_cut
mound_area = float(((gc.mound_h(AA, DD) > 0.02) & inside).sum() * cell)
cap = mound_area * 0.2                              # 築山の表面 0.2 は表土
TH0 = {"big": 3.0, "climb": 3.2, "mid": 2.1, "fruit": 2.3, "ever": 1.9}
woods = unary_union([Point(t[0], t[1]).buffer(TH0[t[2]]) for t in G["TREES"]]).intersection(gpoly)
forest = woods.area * 0.15                           # 木の下（林床）に表土を 0.15 足す
subsoil_B = found_B + garden_cut + pit_cut
use_sub_B = (fill - cap) + backfill_B
OUT["soil"] = dict(fill_m3=round(fill), garden_cut_m3=round(garden_cut), pit_cut_m3=round(pit_cut),
                   A_found_cut_m3=round(found_A), A_surplus_m3=round(garden_cut + pit_cut + found_A - fill),
                   B_footing_cut_m3=round(found_B), B_subsoil_cut_m3=round(subsoil_B), B_subsoil_use_m3=round(use_sub_B),
                   B_subsoil_balance_m3=round(subsoil_B - use_sub_B), B_backfill_m3=round(backfill_B),
                   B_topsoil_m3=round(top_B), B_topsoil_cap_m3=round(cap), B_woods_m2=round(woods.area), B_topsoil_forest_m3=round(forest),
                   B_topsoil_left_m3=round(top_B - cap - forest),
                   B_total_cut_m3=round(subsoil_B + top_B), B_total_use_m3=round(use_sub_B + cap + forest),
                   note="A＝ベタ基礎 0.4 m、B＝布基礎＋土間（床の下は掘った土で埋め戻す）。盛り土は締め固めた量、目安")
# ---------------- 小川の水の量（マニング） ----------------
w = 0.5; n = 0.035                                # 幅 0.5、底は平らな石と砂利
z0, z1 = 0.20, -0.40; S = (z0 - z1) / s_len
rows = []
for y in (0.03, 0.05, 0.08):
    A = w * y; R = A / (w + 2 * y); v = (1 / n) * R ** (2 / 3) * math.sqrt(S)
    rows.append(dict(depth_cm=round(y * 100), v=round(v, 2), Q_Ls=round(A * v * 1000, 1), m3_day=round(A * v * 86400)))
OUT["stream"] = dict(length_m=round(s_len, 1), slope=round(S, 4), rows=rows)

# ---------------- 夏の床の噴水の日陰 ----------------
LAT = math.radians(35.05)
def sun(doy, hour):
    dec = math.radians(23.44) * math.sin(2 * math.pi * (284 + doy) / 365)
    H = math.radians(15 * (hour - 12))
    alt = math.asin(math.sin(LAT) * math.sin(dec) + math.cos(LAT) * math.cos(dec) * math.cos(H))
    az = math.atan2(-math.sin(H), math.tan(dec) * math.cos(LAT) - math.sin(LAT) * math.cos(H))  # 北から東回り
    return alt, az % (2 * math.pi)

ca, sa = math.cos(math.radians(F["rot"])), math.sin(math.radians(F["rot"]))
fp = Polygon([gc.X(F["c"][0] + F["r"][0] * math.cos(q) * ca - F["r"][1] * math.sin(q) * sa,
                   F["c"][1] + F["r"][0] * math.cos(q) * sa + F["r"][1] * math.sin(q) * ca) for q in np.linspace(0, 2 * math.pi, 64)])
roof = gc.read_mesh_layers(["10_本館_屋根"])["10_本館_屋根"]
TH = {"big": (6.5, 3.2), "climb": (6.0, 3.4), "mid": (4.0, 2.2), "fruit": (3.2, 2.0), "ever": (3.0, 1.6)}   # 樹冠の中心の高さ、半径
def shade(alt, az):
    k = 1 / math.tan(alt); dx, dy = -math.sin(az) * k, -math.cos(az) * k
    sh = [translate(roof, dx * h, dy * h) for h in np.linspace(0, 3.0, 7)]   # 軒の高さ 約 3 m の屋根と壁
    for t in G["TREES"]:
        hc, rc = TH[t[2]]; x, y = gc.X(t[0], t[1])
        sh.append(Point(x + dx * hc, y + dy * hc).buffer(rc * 0.85))         # 葉のすき間で少し小さく
    return unary_union(sh)
sh_rows = []
for hour in (9, 10, 11, 12, 13, 14, 15, 16):
    alt, az = sun(205, hour - 0.25)                # 7 月下旬、日本標準時（京都は経度 135.8° で約 3 分のずれ、無視）
    frac = shade(alt, az).intersection(fp).area / fp.area
    sh_rows.append(dict(hour=hour, alt=round(math.degrees(alt)), az=round(math.degrees(az)), shaded=round(frac, 2)))
OUT["fountain_shade_jul"] = sh_rows

os.makedirs(os.path.join(gc.ROOT, "out"), exist_ok=True)
json.dump(OUT, open(os.path.join(gc.ROOT, "out", "garden_calc.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(OUT, ensure_ascii=False))
