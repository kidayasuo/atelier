#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""死角の図：先生がいつもの通り道から見ても見えない所（ユーザー 11-03 09:29、見る線を足したのは同日）。

2枚目のゾーニング図（1/250）に重ねる SVG を作る。
  - 見る点（下の LINES・DOORS）：内縁側（v 12.75）・外縁側（v 14.25）・ふきぬけのみち（v 0.7、床のある所だけ）の中心線、
    くすのきひろばのデッキの上の中心線を 0.25 m おき、くすのきひろばの出入口ごとに1点。
    目の高さは床から 1.5 m（内縁側 z 1.5、外縁側 z 1.35、デッキ z 2.7）。
  - 視線をさえぎる物：3dm（model/sodachiya_exact_mesh.3dm）の物を z 1.21（FL から）で水平に切った断面。
    つまり上の端が 1.2 m を超え、下の端がそれより下の物だけ。見通せない物＝壁・間仕切り・柱・家具・布の囲い・塀・建物・小屋・
    すりガラス。見通せる物＝ガラス・格子・柵・手すり・ネット・樹木（下の OPAQUE・SEE_THROUGH）。
  - 見える範囲：建物の中は、各点からの 2D の見える範囲（障害物の縁の影を引いた残り）を全部の点で足す。範囲の外＝死角。
    園庭は 3D の見通し（ユーザー 11-03 09:57）：0.5 m（境は 0.25 m）の格子の点の上のこどもの頭（地面＋1.0 m）へ、
    どれか一つの見る点から、2D で見えて、しかも線分が地形・小屋・石積み・低木の茂みの高さの面より上を通れば見える。
  - 対象：こどもがいる所（present/ai/layout.json のゾーニングの区分の形と名前を使う）。大人の場所・個室の中は「対象外」。
座標：3dm の xy → 配置図の向き（VIEW_ROT、時計回りに約38.5°）の回した座標（mock.py の R3 と同じ）→ 1/250 の紙。
紙はゾーニング図・園庭説明図（素材22）と同じ範囲（mock.py の WX0〜WX1・WY0〜WY1、layout.json の world）。

  python3 present/tools/shikaku.py        → present/sozai/34_ゾーニング_死角.svgz、/tmp/claude-0/shikaku_check.png
"""
import gzip, json, math, os, pickle, re, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PRESENT = os.path.dirname(HERE)
A = os.path.dirname(PRESENT)
sys.path.insert(0, os.path.join(A, "tools"))
sys.path.insert(0, os.path.join(A, "scripts"))
import hakaru as H                                   # noqa: E402  3dm の物の三角形（tools/hakaru.py）
import garden_common as gc                           # noqa: E402  (u, v) → xy、VIEW_ROT
import shapely                                       # noqa: E402
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box   # noqa: E402
from shapely.ops import unary_union                  # noqa: E402
from shapely import affinity                         # noqa: E402

M3DM = os.path.join(A, "model", "sodachiya_exact_mesh.3dm")
LAYOUT = os.path.join(PRESENT, "ai", "layout.json")
OUT = os.path.join(PRESENT, "sozai", "34_ゾーニング_死角.svgz")
TMP = "/tmp/claude-0"
CHECK = os.path.join(TMP, "shikaku_check.png")
CACHE = os.path.join(TMP, "shikaku_cache.pkl")
os.makedirs(TMP, exist_ok=True)

SC = 250                                             # 1/250
K = 1000 / SC                                        # 紙の mm／m
Z_CUT = 1.21                                         # 視線をさえぎる物：この高さ（FL から m）で切った断面
EYE = 1.5                                            # 大人の目の高さ（床から）
STEP = 0.25                                          # 見る点の間隔（m）
# 先生のいつもの通り道（ユーザー 11-03：縁側に、ふきぬけのみちと、くすのきひろばの入口とデッキを足した）
# 線：名前・v（通り道の中心線）・u の範囲・床の高さ（目は床＋1.5）・床の形で絞るか
LINES = [("内縁側", 12.75, (0.0, 57.0), 0.0, None),
         ("外縁側", 14.25, (0.0, 57.0), -0.15, None),
         ("ふきぬけのみち", 0.7, (6.0, 57.0), 0.0, ("56_", "59_1F_西吹き抜け")),   # 窓辺・2歳の道・絵本の通り（事務・あまのがわの所は床が無いので点を置かない）
         ("くすのきひろばのデッキ", -2.325, (36.45, 39.15), 1.2, None)]            # デッキ（81、u36.2〜39.4・v−3.5〜−1.15、上面 h1.2）の東西の真ん中
DOORS = [("くすのきひろばの入口（東の帯から）", 33.5, -1.8),                     # スパン11の東の帯がそのまま続く所（階段の箱の北）
         ("くすのきひろばの北の口", 46.6, -1.4)]                                 # 口②（u45.6〜47.6）の内

# ---- 視線をさえぎる物（レイヤーの番号）。z 1.21 の断面があるものだけが効く
OPAQUE = {"10s",                                     # 南の軒の鋼の柱
          "11a", "17", "17y", "17k", "18",           # 本館の柱・外壁・縁側の杉の壁・建具の枠
          "19b", "19c", "19d", "19e", "19g",         # 木の戸・すりガラスの窓
          "21", "21y", "22a", "24", "25",            # 西館の外壁・柱・間仕切り・階段
          "35", "35d",                               # 機械室
          "37", "38", "39", "40", "40c", "40d", "40e",   # 家具・間仕切り・腰壁（h1.2 超）・水まわり・布の囲い（ティピ・暖簾）・ロフトのクッション
          "48f",                                     # すりガラス（2歳のトイレの西）
          "55",                                      # はやし（ホールの間伐材の林）
          "66",                                      # 入口の扉・背くらべの柱（格子の戸は下で外す）
          "70", "72", "75",                          # 大和張りの塀・外構の柱・ひろばの家具
          "81", "82", "84", "85", "86", "89",        # 遊戯室（くすのきひろば）のデッキ・ついたて・ねこのみち・すべり台・切り株・ひだ・大戸
          "93"}                                      # 園庭の小屋（便所・倉庫）
SEE_NAME = re.compile(r"格子")                       # 名前に「格子」がある物は見通せる（受け取り土間の格子の引き分け戸など）
# 見通せる（使わない）：16・16d・16o・16s（ガラス戸）・16h・16i（ガラス戸の框）・17g（縦格子）・19（ガラス）・48（ガラス）・49（格子・手すり）・
# 70k（川沿いの縦格子）・73（アーチの棚）・83（ネット）・95（雲梯・ハンモック・シャワーの柱）・樹木（67・77・94）・公園の鉄の物
TERRAIN = "90"                                       # 園庭の地形のメッシュ
FLOOR = {"56", "59", "62"}                                 # 床（ゾーニングの部品が戻せないときの部屋の形）：1階の部屋・みなみのさんかく

# ---- 対象（ゾーニングの区分の名前 → 報告の名前）。None は対象外（薄い灰）
TARGET = {
    "0・1歳": "0・1歳", "2歳": "2歳", "3歳": "3歳", "4歳": "4歳", "5歳": "5歳",
    "外縁側（0・1歳の南、はだしの縁側）": "0・1歳の南の縁側",
    "西吹き抜け（0〜2歳の範囲）": "ふきぬけのみち（0〜2歳）", "西吹き抜け": "ふきぬけのみち（3〜5歳ほか）",
    "内縁側（0〜2歳の範囲）": "縁側", "内縁側": "縁側", "外縁側": "縁側",
    "本館の床（廊下ほか）（0〜2歳の範囲）": "ふきぬけのみち（0〜2歳）", "本館の床（廊下ほか）": "ふきぬけのみち（3〜5歳ほか）",
    "ホール": "ホール", "東の帯": "ホール", "遊戯室": "くすのきひろば", "路地": "路地",
    "便所（0〜2歳）": "便所（0〜2歳）", "便所": "便所（3〜5歳）",
    "受け取り土間": "受け取り土間", "あまのがわ": "あまのがわ",
    "みなみのさんかく": "みなみのさんかく", "しずかのもり": "しずかのもり", "だいさんかく": "だいさんかく",
    "水遊び場・雨庭": "水遊び場・雨庭", "小川": "おがわ",
}
NONTARGET_IN = {"医務", "事務室", "事務", "静養室", "階段", "倉庫", "キッチン", "調理の更衣・便所・前室", "多目的便所",
                "小屋の便所", "小屋の倉庫", "コンポスト", "機械室"}
ORDER = ["0・1歳", "0・1歳の南の縁側", "2歳", "ふきぬけのみち（0〜2歳）", "受け取り土間", "便所（0〜2歳）",
         "3歳", "4歳", "5歳", "便所（3〜5歳）", "路地", "ふきぬけのみち（3〜5歳ほか）", "ホール", "あまのがわ", "くすのきひろば", "縁側",
         "みなみのさんかく", "しずかのもり", "だいさんかく", "水遊び場・雨庭", "おがわ"]


# ================================================================ 座標
def frame_world():
    """layout.json の素材22（園庭説明図）の world＝ゾーニング図と同じ範囲：(WX0, WY0, WX1, WY1)（回した座標の m）"""
    d = json.load(open(LAYOUT, encoding="utf-8"))
    w = None

    def walk(x):
        nonlocal w
        if isinstance(x, dict):
            if x.get("id") == "p2.sozai.22":
                w = x["world"]
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    x0, ytop, ww, hh = w
    return x0, ytop - hh, x0 + ww, ytop


WX0, WY0, WX1, WY1 = frame_world()
PW, PH = (WX1 - WX0) * K, (WY1 - WY0) * K          # 紙の大きさ（mm）
VR = math.radians(gc.G["VIEW_ROT"]["deg"])
_c, _s = math.cos(VR), math.sin(VR)
# mock.py の R3（3dm の xy → 回した座標）は VIEW_ROT の回転＋平行移動。平行移動は敷地の角（mock.py の SITE_C）と
# 図の範囲（敷地の外形の西・北西へ 4 m、ほかへ 1 m、mock.py の WX0・WY1）から決める
SITE_C = np.array([(0.0, 0.0), (34.86, -43.83), (-14.44, -83.04), (-21.91, -73.65), (-25.83, -20.54)])
_sr = np.c_[SITE_C[:, 0] * _c - SITE_C[:, 1] * _s, SITE_C[:, 0] * _s + SITE_C[:, 1] * _c]
TX = (WX0 + 4.0) - _sr[:, 0].min()
TY = (WY1 - 4.0) - _sr[:, 1].max()
assert abs((_sr[:, 0].max() + TX + 1.0) - WX1) < 0.02 and abs((_sr[:, 1].min() + TY - 1.0) - WY0) < 0.02, "図の範囲と敷地の角が合わない"


def R(P):
    """3dm の xy（m、N×2）→ 回した座標（m）"""
    P = np.asarray(P, float)
    return np.c_[P[:, 0] * _c - P[:, 1] * _s + TX, P[:, 0] * _s + P[:, 1] * _c + TY]


def Rg(g):
    return affinity.affine_transform(g, [_c, -_s, _s, _c, TX, TY])


def paper(P):
    """回した座標（m）→ 紙（mm、左上が原点、下向き）"""
    P = np.asarray(P, float)
    return np.c_[(P[:, 0] - WX0) * K, (WY1 - P[:, 1]) * K]


# ================================================================ ゾーニングの区分
# 形と名前は present/ai/layout.json の p2.zc.zone.*（mock.py が書く。1/400 の紙の mm）。ただしその点は部品ごとに .ai の木田さんの
# 置き場へ平行移動してあるので、部品ごとのずれを、同じ時に mock.py が描いた素材19（ゾーニング_彩色（参考）、1/400、図の枠＝紙）の
# 塗りの形と突き合わせて戻す（形の大きさが同じで点が重なる所）。戻せない部品（3〜5歳の教室・みなみのさんかく）は 3dm の床から取る
def _pdf19():
    import fitz
    mm = 25.4 / 72
    out = []
    for x in fitz.open(os.path.join(PRESENT, "sozai", "19_ゾーニング_彩色（参考）.pdf"))[0].get_drawings():
        if x.get("fill") is None:
            continue
        pts = [(q.x * mm, q.y * mm) for it in x["items"] if it[0] == "l" for q in (it[1], it[2])]
        if len(pts) > 4:
            out.append(np.array(pts))
    return out


def zones():
    from collections import Counter
    d = json.load(open(LAYOUT, encoding="utf-8"))
    parts = {}

    def walk(x):
        if isinstance(x, dict):
            if str(x.get("id", "")).startswith("p2.zc.zone."):
                parts[x["id"]] = x
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(d)
    P19 = _pdf19()
    fs = 0.4                                          # 1/400：紙の 1 mm＝0.4 m

    def m(P):                                         # 素材19の紙（mm、左上から下へ）→ 回した座標
        P = np.asarray(P, float)
        return np.c_[WX0 + P[:, 0] * fs, WY1 - P[:, 1] * fs]
    out, missing = [], []
    for pid, x in parts.items():
        offs = []
        for p in x["paths"]:
            for r_ in (p["rings"] if "rings" in p else [p["pts"]]):
                r_ = np.array(r_)
                if len(r_) < 4:
                    continue
                wr = r_.max(0) - r_.min(0)
                for Q in P19:
                    if np.all(np.abs(Q.max(0) - Q.min(0) - wr) < 0.03):
                        off = Q.min(0) - r_.min(0)
                        dmin = np.array([np.min(np.hypot(*(Q - q).T)) for q in r_ + off])
                        if np.mean(dmin < 0.03) > 0.8:
                            offs.append(tuple(off.round(2)))
                if len(offs) >= 3:
                    break
            if len(offs) >= 3:
                break
        if not offs:
            missing.append(pid)
            continue
        off = np.array(Counter(offs).most_common(1)[0][0])
        for p in x["paths"]:
            g = None
            for r_ in (p["rings"] if "rings" in p else [p["pts"]]):
                if len(r_) < 3:
                    continue
                q = Polygon(m(np.array(r_) + off)).buffer(0)
                g = q if g is None else g.symmetric_difference(q)
            if g is not None and not g.is_empty:
                out.append((p.get("name", ""), pid.split(".")[-1], g))
    print("ゾーニングの区分：%d（素材19と合わない部品：%s）" % (len(out), "、".join(missing) or "なし"))
    return out, missing


# ================================================================ 3dm：断面と地形
def slice_tris(T, h):
    """三角形（N×3×3、m）を z=h で切った線分（M×2×2）"""
    z = T[:, :, 2]
    ab = z > h
    n = ab.sum(1)
    T = T[(n == 1) | (n == 2)]
    if len(T) == 0:
        return np.zeros((0, 2, 2))
    z = T[:, :, 2]
    pts = []
    for i, j in ((0, 1), (1, 2), (2, 0)):
        cr = (z[:, i] > h) != (z[:, j] > h)
        t = np.where(cr, (h - z[:, i]) / np.where(cr, z[:, j] - z[:, i], 1.0), np.nan)
        p = T[:, i, :2] + t[:, None] * (T[:, j, :2] - T[:, i, :2])
        pts.append(p)
    P = np.stack(pts, 1)                              # N×3×2（交わらない辺は nan）
    ok = ~np.isnan(P[:, :, 0])
    seg = np.array([P[k][ok[k]][:2] for k in range(len(P)) if ok[k].sum() >= 2])
    return seg.reshape(-1, 2, 2)


def section_poly(seg):
    """断面の線分 → 形（閉じた輪は偶奇で面に、閉じない線は細い帯に）"""
    if len(seg) == 0:
        return None
    seg = np.round(seg, 5)
    seg = seg[np.hypot(*(seg[:, 1] - seg[:, 0]).T) > 1e-6]
    if len(seg) == 0:
        return None
    ml = shapely.multilinestrings(seg)
    merged = shapely.line_merge(ml)
    lines = list(getattr(merged, "geoms", [merged]))
    face, band = None, []
    for ln in lines:
        c = np.asarray(ln.coords)
        if ln.is_closed and len(c) >= 4:
            q = Polygon(c).buffer(0)
            if q.area > 1e-6:
                face = q if face is None else face.symmetric_difference(q)
                continue
        band.append(ln)
    gs = [g for g in [face] + [unary_union(band).buffer(0.01, cap_style=2, join_style=2)] if band or g is not None]
    gs = [g for g in gs if g is not None and not g.is_empty]
    # 閉じた輪の縁も細く足す（面がつぶれた所の取りこぼしを防ぐ）
    gs.append(ml.buffer(0.004, cap_style=2, join_style=2))
    return unary_union(gs)


def load_model():
    if os.path.exists(CACHE) and os.path.getmtime(CACHE) > max(os.path.getmtime(M3DM), os.path.getmtime(__file__)):
        return pickle.load(open(CACHE, "rb"))
    import rhino3dm as r
    t0 = time.time()
    m = r.File3dm.Read(M3DM)
    lname = {i: L.Name for i, L in enumerate(m.Layers)}
    obst, terr, used, floors, stalls, tall, terr_fp = [], [], {}, {}, [], [], []
    for o in m.Objects:
        ln = lname[o.Attributes.LayerIndex]
        code = ln.split("_")[0]
        nm = o.Attributes.Name or ""
        if code in FLOOR:
            T, P = H.tris(o.Geometry)
            if T is not None and len(T):
                T = np.asarray(T, float)[:, :, :2] / 1000.0
                a_ = 0.5 * np.abs((T[:, 1, 0] - T[:, 0, 0]) * (T[:, 2, 1] - T[:, 0, 1]) - (T[:, 2, 0] - T[:, 0, 0]) * (T[:, 1, 1] - T[:, 0, 1]))
                T = T[a_ > 1e-8]
                g = shapely.union_all(shapely.polygons(np.concatenate([T, T[:, :1]], 1))).buffer(0.004, join_style=2).buffer(-0.004, join_style=2)
                floors[ln] = g if ln not in floors else floors[ln].union(g)
            continue
        if code not in OPAQUE and code != TERRAIN and code not in TALL:
            continue
        if code in OPAQUE and SEE_NAME.search(nm):
            continue
        T, P = H.tris(o.Geometry)
        if T is None or len(T) == 0:
            continue
        T = np.asarray(T, float) / 1000.0
        if code == TERRAIN:
            terr.append(T)
            terr_fp.append(shapely.union_all(shapely.polygons(np.concatenate([T[:, :, :2], T[:, :1, :2]], 1))))
            continue
        if code in TALL and T[:, :, 2].min() < Z_CUT:   # 高さの面へ：壁の高さ（z 1.21 か半ば）で切った外形を埋め、上端の高さで（屋根の軒の下は入れない）
            z0_, z1_ = float(T[:, :, 2].min()), float(T[:, :, 2].max())
            sec = section_poly(slice_tris(T, min(Z_CUT, 0.5 * (z0_ + z1_))))
            if sec is not None and not sec.is_empty:
                sec = unary_union([Polygon(q_.exterior) for q_ in getattr(sec, "geoms", [sec]) if q_.geom_type == "Polygon"])
                tall.append((code, nm, sec, z1_))
        if "個室" in nm:                               # こどもの便所の丸い個室：仕切りの中は対象外
            stalls.append(shapely.MultiPoint(T[:, :, :2].reshape(-1, 2)).convex_hull)
        if T[:, :, 2].max() <= Z_CUT or T[:, :, 2].min() >= Z_CUT:
            continue
        g = section_poly(slice_tris(T, Z_CUT))
        if g is not None and not g.is_empty:
            obst.append((code, nm, g))
            used[ln] = used.get(ln, 0) + 1
    terr = np.vstack(terr) if terr else np.zeros((0, 3, 3))
    res = dict(obst=obst, terr=terr, used=used, floors=floors, stalls=stalls, tall=tall, terr_fp=terr_fp)
    pickle.dump(res, open(CACHE, "wb"))
    print("3dm を読んだ：%.0f 秒、さえぎる物 %d" % (time.time() - t0, len(obst)))
    return res


def terrain_block(terr, h):
    """地形のメッシュの h より高い所（3dm の xy）"""
    seg = slice_tris(terr, h)
    if len(seg) == 0:
        return None
    seg = np.round(seg, 5)
    merged = shapely.line_merge(shapely.multilinestrings(seg))
    g = None
    for ln in getattr(merged, "geoms", [merged]):
        if ln.is_closed and len(ln.coords) >= 4:
            q = Polygon(ln.coords).buffer(0)
            g = q if g is None else g.symmetric_difference(q)
    return g


def viewpoints(mod):
    """見る点：(線の名前, 目の z, 回した座標)"""
    out = []
    for nm, v, (u0, u1), f, only in LINES:
        keep = unary_union([g for k, g in mod["floors"].items() if k.startswith(only)]) if only else None
        for u in np.arange(u0, u1 + 1e-6, STEP):
            xy = gc.UV(float(u), v)
            if keep is not None and not keep.contains(Point(xy)):
                continue
            out.append((nm, round(f + EYE, 3), R(np.atleast_2d(xy))[0]))
    for nm, u, v in DOORS:
        out.append((nm, EYE, R(np.atleast_2d(gc.UV(u, v)))[0]))
    return out


# ================================================================ 見える範囲
def front_edges(O):
    """障害物の縁の線分（外の輪は反時計回り、穴は時計回りにそろえる）→ (a, b) の配列"""
    E = []
    for p in getattr(O, "geoms", [O]):
        p = shapely.geometry.polygon.orient(p, 1.0)
        for ring in [p.exterior] + list(p.interiors):
            c = np.asarray(ring.coords)
            E.append(np.stack([c[:-1], c[1:]], 1))
    return np.vstack(E)


def visible(p, E, win, L=1000.0):
    """点 p から見える範囲＝枠から、p に向いた縁の影（五角形）を引いた残り"""
    a, b = E[:, 0], E[:, 1]
    cr = (b[:, 0] - a[:, 0]) * (p[1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (p[0] - a[:, 0])
    sel = cr < -1e-12                                 # p が辺の右（外）にある＝こちらを向いた辺
    a, b = a[sel], b[sel]
    da, db = a - p, b - p
    na, nb = np.hypot(*da.T)[:, None], np.hypot(*db.T)[:, None]
    ok = (na[:, 0] > 1e-6) & (nb[:, 0] > 1e-6)
    a, b, da, db, na, nb = a[ok], b[ok], da[ok], db[ok], na[ok], nb[ok]
    ua, ub = da / na, db / nb
    mid = ua + ub
    mn = np.hypot(*mid.T)[:, None]
    mid = np.where(mn > 1e-9, mid / np.maximum(mn, 1e-9), np.c_[-ua[:, 1], ua[:, 0]])
    Q = np.stack([a, b, p + ub * L, p + mid * L, p + ua * L, a], 1)
    sh = shapely.polygons(Q)
    sh = sh[shapely.is_valid(sh)] if len(sh) else sh
    shadow = shapely.union_all(sh) if len(sh) else Polygon()
    return win.difference(shadow)


def main():
    t0 = time.time()
    mod = load_model()
    print("使った物：", ", ".join("%s %d" % (k, v) for k, v in sorted(mod["used"].items())))
    win = box(WX0, WY0, WX1, WY1)
    O3 = unary_union([g for _, _, g in mod["obst"]])
    O = Rg(O3).intersection(win.buffer(5)).simplify(0.005)
    pts = viewpoints(mod)
    # 2D（平面の見える範囲）：地形は入れない（園庭は下の 3D の見通しで地形を見る）
    E = front_edges(O)
    vps = []                                          # (目の z, 点, 見える範囲)
    for nm, z, q in pts:
        if O.contains(Point(q)):
            continue
        vps.append((z, q, visible(q, E, win)))
    print("2D：縁 %d、点 %d（%s）、%.0f 秒" % (len(E), len(vps), "・".join(dict.fromkeys(n for n, _, _ in pts)), time.time() - t0))
    VIS = unary_union([v for _, _, v in vps])
    # 園庭：3D の見通し（地形と小屋などの高さ）
    GDEAD, gstat = garden3d(mod, O, vps)
    print("園庭の 3D：%s、%.0f 秒" % (gstat, time.time() - t0))
    res = dict(VIS=VIS, O=O, GDEAD=GDEAD, gstat=gstat, pts=[q for _, _, q in pts], vp=pts, floors={k: Rg(g) for k, g in mod["floors"].items()},
               stalls=unary_union([Rg(g) for g in mod["stalls"]]) if mod["stalls"] else Polygon())
    pickle.dump(res, open(os.path.join(TMP, "shikaku_vis.pkl"), "wb"))
    draw(res)
    print("%.0f 秒" % (time.time() - t0))


# ================================================================ 園庭：3D の見通し
OUTDOOR = {"みなみのさんかく", "しずかのもり", "だいさんかく", "水遊び場・雨庭", "おがわ"}
HEAD = 1.0                                           # こどもの頭（地面＋1.0 m）
GSTEP = 0.5                                          # 格子（境は 0.25 に細かく）
HSTEP = 0.1                                          # 高さの面のます
TALL = {"93", "96w", "94b"}                          # 高さの面に足す物（園庭の小屋・石積み・低木の茂み）。塀・柱は 2D で効く
# 94b（ヤマブキの株・築山の北東の肩の茂み、h1.5 の扁平な半球）：木（幹・樹冠）は見通せるが、こどもの頭より高い茂みは見通せないとする
# （11-03 09:57 の指摘のあと。茂みを見通せるとすると、てんぐのたには北の縁側から境に沿って斜めに見通せて死角 0 m²）


def _ad_poly(a0, a1, d0, d1, n=24):
    P = [gc.X(a, d0) for a in np.linspace(a0, a1, n)] + [gc.X(a, d1) for a in np.linspace(a1, a0, n)]
    return Rg(Polygon(P).buffer(0))


def garden_areas():
    """表の行に足す所（ユーザー 11-03 09:57）：てんぐのたに・小屋の後ろ・おやまの裏（回した座標）"""
    G = gc.G
    hut = G["HUT"]
    t = G["MOUND"]
    a0, d0 = t["top"]
    ring = []
    for th in np.linspace(0, 2 * math.pi, 145):
        ca, sd = math.cos(th), math.sin(th)
        ra = t["r_se"] if ca > 0 else t["r_nw"]
        rd = t["r_sw"] if sd > 0 else t["r_ne"]
        ring.append(gc.X(a0 + ra * ca, d0 + rd * sd))
    mound = Rg(Polygon(ring).buffer(0))
    tengu = _ad_poly(33.0, 43.0, 0.0, 2.2)
    back = _ad_poly(hut["a"][0] - 0.5, hut["a"][1] + 0.5, 0.0, hut["d"][0])
    ura = mound.intersection(_ad_poly(a0 - 12, a0 + 12, -1.0, d0)).difference(tengu)   # 頂より隣家の側（北東）
    return {"てんぐのたに": tengu, "小屋の後ろ": back, "おやまの裏": ura}


def heightfield(mod):
    """回した座標の高さの面（地形＋小屋など）。外は GL−0.3"""
    from scipy.interpolate import LinearNDInterpolator
    nx, ny = int((WX1 - WX0) / HSTEP) + 1, int((WY1 - WY0) / HSTEP) + 1
    X, Y = np.meshgrid(WX0 + np.arange(nx) * HSTEP, WY0 + np.arange(ny) * HSTEP)
    T = mod["terr"].reshape(-1, 3)
    V, idx = np.unique(np.round(T, 3), axis=0, return_index=True)
    xy = R(V[:, :2])
    f = LinearNDInterpolator(xy, V[:, 2])
    Z = f(X, Y)
    hull = unary_union([Rg(g) for g in mod["terr_fp"]]) if mod.get("terr_fp") else None
    if hull is not None:                              # メッシュの外（凸包の埋め草）は GL
        Z = np.where(shapely.contains_xy(hull.buffer(0.05), X, Y), Z, np.nan)
    G0 = np.where(np.isnan(Z), -0.3, Z)              # 地面（こどもの足もと）
    Hh = G0.copy()
    for code, nm, sec, ztop in mod["tall"]:
        fp = Rg(sec).buffer(0.01)
        b = fp.bounds
        i0, i1 = max(0, int((b[1] - WY0) / HSTEP)), min(ny, int((b[3] - WY0) / HSTEP) + 2)
        j0, j1 = max(0, int((b[0] - WX0) / HSTEP)), min(nx, int((b[2] - WX0) / HSTEP) + 2)
        if i0 >= i1 or j0 >= j1:
            continue
        m_ = shapely.contains_xy(fp, X[i0:i1, j0:j1], Y[i0:i1, j0:j1])
        Hh[i0:i1, j0:j1] = np.where(m_, np.maximum(Hh[i0:i1, j0:j1], ztop), Hh[i0:i1, j0:j1])
    return G0, Hh


def _hz(A, P):
    j = np.clip(np.round((P[..., 0] - WX0) / HSTEP).astype(int), 0, A.shape[1] - 1)
    i = np.clip(np.round((P[..., 1] - WY0) / HSTEP).astype(int), 0, A.shape[0] - 1)
    return A[i, j]


def _seen(G0, Hh, vps, Q, O):
    """格子の点 Q（回した座標）がどれか一つの見る点から見えるか。2D で見える範囲に入り、3D で地形・小屋の上を通る"""
    seen = np.zeros(len(Q), bool)
    zt = _hz(G0, Q) + HEAD
    for ze, p, vis in vps:
        rest = np.where(~seen)[0]
        if len(rest) == 0:
            break
        ok = shapely.contains_xy(vis, Q[rest, 0], Q[rest, 1])
        rest = rest[ok]
        if len(rest) == 0:
            continue
        D = Q[rest] - p
        L = np.hypot(D[:, 0], D[:, 1])
        n = int(L.max() / 0.15) + 2
        t = np.linspace(0, 1, n)[None, :]
        P = p + t[..., None] * D[:, None, :]           # k×n×2
        zl = ze + t * (zt[rest][:, None] - ze)
        hz = _hz(Hh, P)
        dist = t * L[:, None]
        mask = (dist > 0.3) & (dist < L[:, None] - 0.25)   # 目の近くと頭の近くは見ない
        blocked = np.any((hz > zl) & mask, axis=1)
        seen[rest[~blocked]] = True
    return seen


def garden3d(mod, O, vps):
    zs, missing = zones()
    out = [g for n_, c_, g in zs if c_ in ("g02", "gboth", "g35", "water", "stream")]
    if "p2.zc.zone.g02" in missing:
        out += [Rg(g) for k, g in mod["floors"].items() if k.startswith("62_")]
    dom = unary_union(out + list(garden_areas().values())).intersection(box(WX0, WY0, WX1, WY1)).difference(O)
    G0, Hh = heightfield(mod)
    vps_g = [v for v in vps if v[0] < 2.0]           # デッキ（z 2.7）は園庭が見えないので外す
    b = dom.bounds
    xs = np.arange(b[0] + GSTEP / 2, b[2], GSTEP)
    ys = np.arange(b[1] + GSTEP / 2, b[3], GSTEP)
    X, Y = np.meshgrid(xs, ys)
    Q = np.c_[X.ravel(), Y.ravel()]
    Q = Q[shapely.contains_xy(dom.buffer(GSTEP), Q[:, 0], Q[:, 1])]
    s1 = _seen(G0, Hh, vps_g, Q, O)
    # 境（見える・見えないが隣り合う所）だけ 0.25 に細かく
    key = {tuple(np.round(q / GSTEP, 3)): v for q, v in zip(Q, s1)}
    cells_dead, fine = [], []
    h = GSTEP / 2
    for q, v in zip(Q, s1):
        nb = [key.get(tuple(np.round((q + d) / GSTEP, 3))) for d in ((GSTEP, 0), (-GSTEP, 0), (0, GSTEP), (0, -GSTEP))]
        if any(x is not None and x != v for x in nb):
            fine.append(q)
        elif not v:
            cells_dead.append(box(q[0] - h, q[1] - h, q[0] + h, q[1] + h))
    if fine:
        F = np.vstack([np.array(fine) + np.array(d) for d in ((-h / 2, -h / 2), (h / 2, -h / 2), (-h / 2, h / 2), (h / 2, h / 2))])
        s2 = _seen(G0, Hh, vps_g, F, O)
        cells_dead += [box(q[0] - h / 2, q[1] - h / 2, q[0] + h / 2, q[1] + h / 2) for q, v in zip(F, s2) if not v]
    D = unary_union(cells_dead).intersection(dom) if cells_dead else Polygon()
    return D, "格子 %d 点（境を細かく %d 点）、見る点 %d、死角 %.1f m²" % (len(Q), 4 * len(fine), len(vps_g), D.area)


# ================================================================ 描く
def draw(res):
    zs, missing = zones()
    fl = res["floors"]
    if "p2.zc.zone.z35" in missing:                  # 3〜5歳の教室：3dm の床（59_1F_3歳ほか）
        zs += [(k_.split("_")[-1], "z35", g_) for k_, g_ in fl.items() if re.match(r"59_1F_[345]歳$", k_)]
    if "p2.zc.zone.g02" in missing:                  # みなみのさんかく：3dm の 62
        zs += [("みなみのさんかく", "g02", g_) for k_, g_ in fl.items() if k_.startswith("62_")]
    VIS, O, GDEAD = res["VIS"], res["O"], res["GDEAD"]
    GA = garden_areas()
    win = box(WX0, WY0, WX1, WY1)
    tgt, non = {}, []
    staff = [g_ for k_, g_ in res["floors"].items() if "便所（職員）" in k_]
    for name, cat, g in zs:
        g = g.intersection(win)
        if g.is_empty:
            continue
        if name == "便所" and staff and g.intersection(unary_union(staff)).area > 0.5 * g.area:
            non.append(g)                             # 職員の便所は対象外
            continue
        if name in TARGET:
            tgt.setdefault(TARGET[name], []).append(g)
        elif name in NONTARGET_IN:
            non.append(g)
    tgt = {k: unary_union(v) for k, v in tgt.items()}
    if "だいさんかく" in tgt:                        # 小屋の後ろ・てんぐのたにが区分から漏れていても、だいさんかくに入れる
        tgt["だいさんかく"] = unary_union([tgt["だいさんかく"]] + [g_.difference(unary_union([tgt[k_] for k_ in tgt if k_ != "だいさんかく"])) for g_ in GA.values()]).intersection(win)
    NON = unary_union(non) if non else Polygon()
    # 便所の丸い個室の仕切りの中は対象外（ほかの囲まれた所＝ティピの中・くぼみなどは死角として出す）
    HOLES = res.get("stalls", Polygon())
    dead, rows = {}, []
    for k in ORDER:
        if k not in tgt:
            continue
        if k in OUTDOOR:                              # 園庭：3D の見通しの格子の結果
            g = tgt[k].intersection(GDEAD).difference(O).difference(NON)
        else:                                         # 建物の中：2D
            g = tgt[k].difference(VIS).difference(O).difference(HOLES).difference(NON)
        g = g.buffer(-0.02).buffer(0.02)               # 視線のすき間の細い筋（2 cm 未満）は消す
        dead[k] = g
        rows.append((k, tgt[k].area, g.area))
    for k, ga in GA.items():                          # うちわけ（だいさんかくの中の所）
        a_ = ga.intersection(win).difference(O)
        rows.append(("（うち）" + k, a_.area, ga.intersection(unary_union(list(dead.values()))).area))
    NONALL = unary_union([NON, HOLES.intersection(unary_union(list(tgt.values())))])
    res.update(dead=dead, rows=rows, NONALL=NONALL)
    write_svg(res)
    check_png(res)
    tot = sum(r[2] for r in rows if not r[0].startswith("（うち）"))
    print("場所ごとの死角（m²）")
    for k, a, d in rows:
        print("  %-24s 面積 %7.1f  死角 %6.1f（%4.1f %%）" % (k, a, d, 100 * d / a if a else 0))
    print("  計 %.1f m²" % tot)
    json.dump([dict(name=k, area=round(a, 1), dead=round(d, 1)) for k, a, d in rows], open(os.path.join(TMP, "shikaku_rows.json"), "w"), ensure_ascii=False, indent=1)


def _path_d(g):
    out = []
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon" or p.area < 1e-4:
            continue
        for r_ in [p.exterior] + list(p.interiors):
            c = paper(np.asarray(r_.coords)[:-1])
            out.append("M" + " L".join("%.2f %.2f" % (x, y) for x, y in c) + " Z")
    return " ".join(out)


def _hatch(g, gap=1.5, ang=45.0):
    """紙の上の斜線（mm）：形の中の平行線"""
    pg = shapely.affinity.affine_transform(g, [K, 0, 0, -K, -WX0 * K, WY1 * K])   # 紙の座標（下向き）
    if pg.is_empty:
        return []
    x0, y0, x1, y1 = pg.bounds
    t = math.radians(ang)
    d = np.array([math.cos(t), -math.sin(t)])      # 線の向き（紙の上で右上へ）
    n = np.array([-d[1], d[0]])
    cs = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]])
    s = cs @ n
    Lg = math.hypot(x1 - x0, y1 - y0) + 2
    cx = cs.mean(0)
    lines = []
    for k in np.arange(math.floor(s.min() / gap) * gap, s.max() + gap, gap):
        base = cx + n * (k - cx @ n)
        lines.append(LineString([base - d * Lg, base + d * Lg]))
    inter = shapely.intersection(np.array(lines, dtype=object), pg)
    segs = []
    for gg in inter:
        for ln in getattr(gg, "geoms", [gg]):
            if ln.geom_type == "LineString" and ln.length > 0.05:
                segs.append(np.asarray(ln.coords))
    return segs


FONT = "HiraginoSans-W3"


def write_svg(res):
    dead, NONALL = res["dead"], res["NONALL"]
    D = unary_union(list(dead.values()))
    PT = 25.4 / 72
    lw_h, lw_e = 0.25 * PT, 0.3 * PT
    s = []
    s.append('<?xml version="1.0" encoding="UTF-8"?>')
    s.append('<svg xmlns="http://www.w3.org/2000/svg" width="%.2fmm" height="%.2fmm" viewBox="0 0 %.2f %.2f">' % (PW, PH, PW, PH))
    s.append('<title>死角（ゾーニング図に重ねる、1/%d）</title>' % SC)
    # 位置合わせの枠（ゾーニング図の外枠と同じ。線なし・塗りなし）
    s.append('<g id="位置合わせの枠"><rect x="0" y="0" width="%.2f" height="%.2f" fill="none" stroke="none"/></g>' % (PW, PH))
    # 対象外（大人の場所・個室の中）
    s.append('<g id="対象外" opacity="1"><path d="%s" fill="#D9D9D9" fill-opacity="0.75" stroke="none" fill-rule="evenodd"/></g>' % _path_d(NONALL))
    # 死角：斜線と破線の縁
    s.append('<g id="死角">')
    s.append('<g id="死角_斜線" fill="none" stroke="#333333" stroke-width="%.3f" stroke-linecap="butt">' % lw_h)
    for c in _hatch(D):
        s.append('<path d="M%.2f %.2f L%.2f %.2f"/>' % (c[0][0], c[0][1], c[-1][0], c[-1][1]))
    s.append('</g>')
    s.append('<g id="死角_縁"><path d="%s" fill="none" stroke="#333333" stroke-width="%.3f" stroke-dasharray="0.8 0.5" fill-rule="evenodd"/></g>' % (_path_d(D), lw_e))
    s.append('</g>')
    # 見る通り道（先生のいつもの通り道、細い点線。入口は小さな丸）
    lw_r = 0.5 * PT
    s.append('<g id="見る通り道" fill="none" stroke="#333333" stroke-width="%.3f" stroke-linecap="round" stroke-dasharray="0.01 0.7">' % lw_r)
    for nm in [l_[0] for l_ in LINES]:
        P = [q for n_, _, q in res.get("vp", []) if n_ == nm]
        chain = []
        for q in P + [None]:
            if q is not None and (not chain or math.hypot(*(q - chain[-1])) < STEP * 1.6):
                chain.append(q)
                continue
            if len(chain) >= 2:
                c = paper(np.array(chain))
                s.append('<path d="M%s"/>' % " L".join("%.2f %.2f" % (x, y) for x, y in c))
            chain = [q] if q is not None else []
    for nm, u_, v_ in DOORS:
        x, y = paper(R(np.atleast_2d(gc.UV(u_, v_))))[0]
        s.append('<circle cx="%.2f" cy="%.2f" r="0.6" fill="#FFFFFF" stroke="#333333" stroke-width="%.3f" stroke-dasharray="none"/>' % (x, y, lw_r))
    s.append('</g>')
    # 凡例（別の小さな部品、左上の余白）
    lx, ly = 3.0, 2.0
    fs = 8 * PT                                       # 8 pt
    s.append('<g id="死角_凡例">')
    s.append('<rect x="%.2f" y="%.2f" width="6" height="4" fill="#FFFFFF" stroke="#333333" stroke-width="%.3f" stroke-dasharray="0.8 0.5"/>' % (lx, ly, lw_e))
    for k in np.arange(-4 + 0.75, 6, 1.5):
        x_a, y_a, x_b, y_b = lx + k, ly + 4, lx + k + 4, ly
        # 箱の中に切る
        ln = LineString([(x_a, y_a), (x_b, y_b)]).intersection(box(lx, ly, lx + 6, ly + 4))
        if not ln.is_empty and ln.length > 0.05:
            c = np.asarray(ln.coords)
            s.append('<path d="M%.2f %.2f L%.2f %.2f" stroke="#333333" stroke-width="%.3f"/>' % (c[0][0], c[0][1], c[-1][0], c[-1][1], lw_h))
    s.append('<text x="%.2f" y="%.2f" font-family="%s" font-size="%.3f" fill="#222222">死角：先生がいつもの通り道（縁側・ふきぬけのみち・くすのきひろばの入口とデッキ）から見ても見えない所</text>' % (lx + 8, ly + 3.1, FONT, fs))
    s.append('<path d="M%.2f %.2f L%.2f %.2f" fill="none" stroke="#333333" stroke-width="%.3f" stroke-linecap="round" stroke-dasharray="0.01 0.7"/>' % (lx, ly + 14, lx + 6, ly + 14, 0.5 * PT))
    s.append('<circle cx="%.2f" cy="%.2f" r="0.6" fill="#FFFFFF" stroke="#333333" stroke-width="%.3f"/>' % (lx + 3, ly + 14, 0.3 * PT))
    s.append('<text x="%.2f" y="%.2f" font-family="%s" font-size="%.3f" fill="#222222">先生のいつもの通り道（点線、丸は入口）</text>' % (lx + 8, ly + 15.1, FONT, fs))
    s.append('<rect x="%.2f" y="%.2f" width="6" height="4" fill="#D9D9D9" fill-opacity="0.75" stroke="none"/>' % (lx, ly + 6))
    s.append('<text x="%.2f" y="%.2f" font-family="%s" font-size="%.3f" fill="#222222">対象外（大人の場所・便所の個室の中）</text>' % (lx + 8, ly + 9.1, FONT, fs))
    s.append('</g>')
    s.append('</svg>')
    data = "\n".join(s).encode("utf-8")
    with gzip.open(OUT, "wb") as f:
        f.write(data)
    open(os.path.join(TMP, "shikaku.svg"), "wb").write(data)
    print("書いた：", OUT, "（%.0f×%.0f mm）" % (PW, PH))


def check_png(res):
    """確かめ用：ゾーニング（素材19、1/400）を 1/250 の大きさに広げて、その上に SVG を重ねる"""
    import fitz
    from PIL import Image
    dpi = 1600 / (max(PW, PH) / 25.4)
    src = os.path.join(PRESENT, "sozai", "19_ゾーニング_彩色（参考）.pdf")
    doc = fitz.open(src)
    pg = doc[0]
    zoom = dpi / 72 * (PW / (pg.rect.width / 72 * 25.4))
    pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    bg = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("RGBA")
    ov_path = os.path.join(TMP, "shikaku_ov.png")
    subprocess.run(["rsvg-convert", "-w", str(bg.width), "-h", str(bg.height), "-o", ov_path, os.path.join(TMP, "shikaku.svg")], check=True)
    ov = Image.open(ov_path).convert("RGBA").resize(bg.size)
    out = Image.alpha_composite(bg, ov)
    # 見る点（赤い点、確かめ用だけ）
    from PIL import ImageDraw
    dr = ImageDraw.Draw(out)
    sx = out.width / PW
    for q in res["pts"][::4]:
        x, y = paper(np.atleast_2d(q))[0] * sx
        dr.ellipse([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=(220, 30, 30, 255))
    out.convert("RGB").save(CHECK)
    print("確かめ：", CHECK, out.size)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--draw":
        draw(pickle.load(open(os.path.join(TMP, "shikaku_vis.pkl"), "rb")))
    else:
        main()
