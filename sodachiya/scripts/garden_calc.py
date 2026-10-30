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
# 建物の根切り（目安）。10-23 夜：本館の床は全面の床下空間（ユーザー）＝ベタ基礎の底板 t200 の上端 GL−0.3、
# 下に防湿・断熱・砕石 t100 で根切りの底 約 GL−0.6、外へ 0.3 m 広く（本館係、連携 10-23夜10）。
# 西館・おむすびは前の案 B（布基礎＋土間、根切りは基礎の下だけ、床の下は表土 0.10 を剥いで掘った土で埋め戻す）のまま
# → 10-23 夜15 で西館も床下空間に（下の west_cut_all）。
honkan = 57 * 15.0; west = 366 + 30
honkan_cut = (honkan + 0.3 * 2 * (57 + 15)) * 0.6
honkan_top = (honkan + 0.3 * 2 * (57 + 15)) * 0.12           # そのうち表土（よい土、剥いでおく）
# 10-23 夜15：西館の1階も床下空間に決まった（ユーザー、西館係）。西館も根切り GL−0.6。おむすび（30）は布基礎＋土間のまま
west_cut_all = (366 + 0.3 * 2 * 80) * 0.6
west_top_all = (366 + 0.3 * 2 * 80) * 0.12
omu_footing = 25 * 0.6 * 0.5; omu_top = 30 * 0.10; omu_backfill = 30 * 0.10
west_footing = (west_cut_all - west_top_all) + omu_footing
west_top = west_top_all + omu_top; west_backfill = omu_backfill
west_if_crawl = 0.0
garden_cut = bowl_cut + stream_cut + rain_cut + fount_cut + splash_cut
mound_area = float(((gc.mound_h(AA, DD) > 0.02) & inside).sum() * cell)
cap = mound_area * 0.2                                         # 築山の表面 0.2 は表土
TH0 = {"small": 0.7, "big": 3.0, "climb": 3.2, "mid": 2.1, "fruit": 2.3, "ever": 1.9}
woods = unary_union([Point(t[0], t[1]).buffer(TH0[t[2]]) for t in G["TREES"]]).intersection(gpoly)
forest = woods.area * 0.2                                      # 木の下（林床）に表土 0.2（10-24、西館の表土も）
topsoil = honkan_top + west_top
subsoil = (honkan_cut - honkan_top) + west_footing + garden_cut + pit_cut
use_sub = (fill - cap) + west_backfill
use_top = cap + forest + 20                                    # ＋菜園の土の入れ替え 約 20
OUT["soil"] = dict(fill_m3=round(fill), garden_cut_m3=round(garden_cut), pit_cut_m3=round(pit_cut),
                   honkan_cut_m3=round(honkan_cut), west_cut_m3=round(west_footing + west_top),
                   total_cut_m3=round(subsoil + topsoil), subsoil_m3=round(subsoil), topsoil_m3=round(topsoil),
                   use_subsoil_m3=round(use_sub), use_topsoil_m3=round(use_top), woods_m2=round(woods.area),
                   out_subsoil_m3=round(subsoil - use_sub), out_topsoil_m3=round(topsoil - use_top),
                   out_total_m3=round(subsoil + topsoil - use_sub - use_top),
                   west_if_crawl_extra_m3=round(west_if_crawl),
                   note="本館＝床下空間（根切り GL−0.6）、西館・おむすび＝布基礎＋土間。盛り土は締め固めた量、目安")
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
TH = {"small": (1.2, 0.7), "big": (6.5, 3.2), "climb": (6.0, 3.4), "mid": (4.0, 2.2), "fruit": (3.2, 2.0), "ever": (3.0, 1.6)}   # 樹冠の中心の高さ、半径
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
spp = Polygon([gc.X(SP["c"][0] + SP["r"][0] * math.cos(q), SP["c"][1] + SP["r"][0] * math.sin(q)) for q in np.linspace(0, 2 * math.pi, 64)])
rows2 = []
for hour in (9, 10, 11, 12, 13, 14, 15, 16):
    alt, az = sun(205, hour - 0.25)
    rows2.append(dict(hour=hour, shaded=round(shade(alt, az).intersection(spp).area / spp.area, 2)))
OUT["infant_fountain_shade_jul"] = rows2

os.makedirs(os.path.join(gc.ROOT, "out"), exist_ok=True)
json.dump(OUT, open(os.path.join(gc.ROOT, "out", "garden_calc.json"), "w"), ensure_ascii=False, indent=1)
print(json.dumps(OUT, ensure_ascii=False))
