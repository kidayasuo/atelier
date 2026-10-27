# 配置図 1/200（更新係が 3dm から自動で描く、draw100.py）に描く外構の中身。アプローチ係が決める（設計監修 10-25、役割分担「図の分け方」）。
# approachA.py の最後から呼ばれ、data/siteplan_approach.json を書く。座標はすべて 3dm の xy（m）＝取り込み用ファイル（70〜79）と同じ。
# 形（線・面）は 3dm のレイヤーにある。ここに書くのは：レイヤーの描き方、名前（文字）とその位置、数、記号、道すじ、注。
import os, json, math
import numpy as np
import north_common as NC
import minami_common as MN

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
OUTP = os.path.join(ROOT, "data", "siteplan_approach.json")

def _r(q): return [round(float(q[0]), 2), round(float(q[1]), 2)]
def _c(g): q = g.representative_point(); return _r((q.x, q.y))
def _mw(xy): return MN_W(xy[1], xy[0])                        # みなみの (v, u) → 3dm


def _reserve(g):
    """駐車・駐輪に確保する場所（灰色 #D8D8D4、プレゼンの準備 0139・ユーザー 10-25夜）：歩道 1.0 の奥から、ひろば・小径・ムベの棚・屋根まで、公園の北から職員の駐輪の北の端まで。"""
    from shapely.geometry import Polygon as SP, LineString as SL
    from shapely.ops import unary_union
    P, Q = g["P"], g["Q"]
    SB = g["STAFF_BIKE"]; PD = SB["pocket"][3]; SX = g["SX"]; TIP = tuple(map(float, g["TIP"]))
    out = SP(Q([(SX, PD), (22.7, PD), (22.7, g["NHEDGE_D"]), (17.7, g["NHEDGE_D"]), (17.7, g["HEDGE_D"]), (g["S_PATH0"], g["HEDGE_D"]), TIP,
                (-5, TIP[1]), (-5, -5), (SX, -5)]))                         # セキュリティの線の外（西）
    z = SP(g["SITE"]).intersection(out).intersection(SP(Q([(-5, g["SIDEWALK"]["d"][1]), (SX + 0.01, g["SIDEWALK"]["d"][1]), (SX + 0.01, 20), (-5, 20)])))
    cut = unary_union([SP(g["PARK"]), g["WB"], g["LEAN_ROOF"], g["TRI"],
                       SL(Q(g["HEDGE"][0])).buffer(g["HW"], cap_style=2, join_style=2),
                       SP(g["srect"](g["STAFF_BIKE"]["road_gap"][1], 29.4, 0.15, g["STALL_D0"] - 0.1))])   # 納品場より北の道路側の植栽帯
    z = z.difference(cut.buffer(0.005))
    gs = [q for q in getattr(z, "geoms", [z]) if q.geom_type == "Polygon" and q.area > 1.0]
    return {"fc": "#D8D8D4", "area_m2": round(sum(q.area for q in gs), 1),
            "polygons": [[_r(c) for c in q.exterior.coords] for q in gs],
            "note": "駐車・駐輪・搬入路・来客の歩道を含む灰色の地。下に置く（車室の枠・駐輪の記号・バンプはその上）。屋根（下屋）・ムベの棚・生垣・ひろば・西館で止める"}

def write(g):
    global MN_W
    P, W, E = g["P"], g["W"], g["E"]; MN_W = W
    tt = g["tt"]; ROAD = _r(tt)                                   # 西の道路に沿う向き（3dm）
    r0, r1 = (np.array(_mw(MN.xy(p))) for p in MN.D["RIVER_EDGE"])
    RIV = _r((r1 - r0) / np.linalg.norm(r1 - r0))                # 高野川の柵に沿う向き
    GA0, GA1 = g["GA0"], g["GA1"]
    S0 = g["STALL_D0"]

    labels = []                                                  # 文字：text, xy, kind（名前の大きさ）, along（線に沿わせるとき、無ければ紙に水平）
    def L(text, xy, kind="name", along=None, note=None):
        d = {"text": text, "xy": _r(xy), "kind": kind}
        if along is not None: d["along"] = along
        if note: d["note"] = note
        labels.append(d)

    # --- 南：アプローチ（公園 → 木戸 → ポーチ／見送りの小径 → 手水 → ひろば）
    L("公園の木戸", E((GA0 + GA1) / 2, -2.4), "key", note="保護者・来客の出入口はここだけ（赤い点）")
    L("待ち受け（ベビーカーは柵ぎわ）", W(-2.2, -0.3))
    L("大和張りの塀 h1.8", E(5.2, -0.6), "small", along=None)
    L("見送りの小径（ムベの棚）", P(12.8, 11.55), "key", along=ROAD)
    L("手水", P(21.6, 11.7))
    L("ひろば", P(23.2, 8.6), "key")
    L("菜園", P(20.1, 8.45), "small", note="大豆・カブとダイコン・サツマイモ")
    L("お茶の縁台", W(20.1, -10.9), "small")
    L("かまど", P(25.0, 8.1), "small")
    _tk = g["RAIN"]["S_TANK"]
    L("雨水槽（地中）・手押しポンプ", P(sum(_tk["s"]) / 2, _tk["d"][1] + 0.5), "small", note="鎖樋→受け桝→地中の槽→菜園の脇のポンプ")
    L("大和張りの塀 h1.8", P(28.0, g["FENCE_D"] + 0.6), "small", along=ROAD)
    L("生垣 h1.2", P(10.0, g["HEDGE_D"] - 0.7), "small", along=ROAD)
    L("西館の南の入口", W(21.0, -2.0), "small")
    # --- 南：線の外（駐車・駐輪・搬入）
    L("車路 5.5", P(14.95, 5.0), "small", along=ROAD)
    L("歩道（開放）1.0", P(4.0, 0.5), "small", along=ROAD, note="公園の上の端〜食材納品場、敷地の境から1.0")
    L("搬入路 1.6", P(27.4, 2.1), "small", along=[-ROAD[1], ROAD[0]])
    L("勝手口", W(21.2, -12.2), "small")
    L("職員の自転車 %d台" % g["STAFF_N"], P(25.0, 2.1), "small", along=[-ROAD[1], ROAD[0]])
    L("駐輪 %d台" % g["N_BIKE"], P(2.4, 4.6), "name", note="保護者、子乗せ 0.7 ピッチ")
    L("来客の歩道", P(10.0, 9.45), "small", along=ROAD)
    # --- 北：西館の周り
    L("読書の庭（モミジ・苔）", NC.READ.centroid.coords[0], "name")
    L("角の両開きの木戸", NC.T(sum(NC.N["KOMICHI_GATE"]["t"]) / 2, NC.FN - 1.0), "small")
    L("大和張りの塀 h1.8", NC.T(16.5, NC.FN - 0.6), "small", along=_r(NC.t2))
    L("北の小径", NC.KOMICHI.centroid.coords[0], "small")
    L("機械室の戸", NC.T(sum(NC.N["MECH_DOOR"]["t"]) / 2, -0.6), "small")
    L("キンモクセイ・ギンモクセイの刈り込み", NC.P(41.0, -0.9), "small", along=ROAD)
    L("雨庭", NC.RAINGARDEN.centroid.coords[0], "small")
    L("北東の木戸", np.array(NC.NE_GATE[1]) + np.array([0.0, 1.2]), "small")
    # --- みなみのさんかく（0〜2歳の園庭）
    L("みなみのさんかく", W(-8.3, 5.2), "key")
    L("ころころの丘", _mw(MN.xy(MN.D["MOUND"]["c"])), "small")
    L("砂場", _mw(MN.SAND.centroid.coords[0]), "small")
    L("避難の帯 1.5", _mw(tuple(MN.R0 + (MN.R1 - MN.R0) * 0.4 + MN.NRM * 1.0)), "small", along=RIV)
    L("緑の目隠し h1.5（ムベ）", _mw(tuple(MN.R0 + (MN.R1 - MN.R0) * 0.75 - MN.NRM * 0.9)), "small", along=RIV)
    _gs = {}
    for name, h, e, hh, deg in MN.gates(): _gs.setdefault(name.split("・")[0], []).extend([h, e])
    for name, pts in _gs.items():
        c = np.mean(np.array(pts), axis=0)
        L("非常用の門 h1.8" if "西" in name else "東の木戸 h0.9", _mw(tuple(c + MN.NRM * 0.9)), "small")
    # --- 周り（PLATEAU の名前は無いので、課題の所要：道路・河川）
    L("西の道路（歩道なし）", P(55.0, -2.5), "context", along=ROAD)
    L("北西の道路", NC.T(20.0, -2.5), "context", along=_r(NC.t2))
    L("公園", (-13.4, -77.5), "context")
    L("高野川", _mw(tuple(MN.R0 + (MN.R1 - MN.R0) * 0.5 - MN.NRM * 6.0)), "context", along=RIV)

    trees = [                                                    # 樹木：名前、幹の位置、樹冠の半径（3dm の 77・79 にも円がある）
        {"name": "入江の木（落葉樹）", "xy": _r(P(24.4, 9.6)), "r": 1.9},
        {"name": "モミジ", "xy": _r(NC.MOMIJI), "r": 1.5},
        {"name": "ヤマボウシ", "xy": _r(_mw(MN.xy(MN.D["TREE"]["c"]))), "r": MN.D["TREE"]["r"]},
    ]
    stalls = []                                                  # 車室：中心と記号（P／搬入）
    for k in range(3): stalls.append({"xy": _r(P(9.7, S0 + 2.5 * k + 1.25)), "mark": "P"})
    stalls.append({"xy": _r(P(20.2, S0 + 1.25)), "mark": "搬入"}); stalls.append({"xy": _r(P(20.2, S0 + 3.75)), "mark": "P"})

    spec = {
        "_": "配置図 1/200 に描く外構の中身（アプローチ係、scripts/siteplan_spec.py が approachA.py から書く。手で直さない）。座標は 3dm の xy（m）。"
             "形は取り込み用ファイルのレイヤー 70〜79（本体では外構の層）。ここは描き方・文字・数・記号・道すじ・注。"
             "文字の大きさは kind：key（場所の名前、9pt くらい）・name（7pt）・small（5.5pt）・context（周りの名前、7pt、灰色）。along があれば線に沿わせ、無ければ紙に水平。"
             "note は文字の下に小さく（省いてよい）。",
        "layers": {                                              # 1/200 の描き方（線の太さは紙の mm）
            "70_外構_生垣・塀・格子": {"draw": "line", "lw": 0.35, "note": "塀と木戸はすべてスギの大和張り（ユーザー 10-27、外壁と同じ）：3dm は板と胴縁の箱、1/200 では塀の線（濃い茶）に表裏の板の短い線（二重の破線に見える）でも、太い一本の線でもよい。生垣は緑の帯"},
            "71_外構_屋根（木戸・手水・下屋）": {"draw": "outline", "ls": "dashed", "lw": 0.18, "note": "頭上の屋根は破線（建物の屋根伏せと同じ扱いでもよい）"},
            "72_外構_柱": {"draw": "fill", "fc": "black", "note": "■ 小さく"},
            "73_外構_アーチの棚": {"draw": "outline", "ls": "dashed", "lw": 0.13, "fc": "#9DBE7A", "alpha": 0.25, "note": "ムベの棚：薄い緑を重ねる、桁と梁は細い破線"},
            "74_外構_駐車・駐輪・バンプ": {"draw": "outline", "lw": 0.18, "note": "車室の枠、駐輪の記号、スピードバンプ（黄と黒）"},
            "75_外構_ひろばの家具": {"draw": "outline", "lw": 0.13},
            "76_外構_舗装の区分": {"draw": "fill", "note": "洗い出し・砂利・真砂土の区分は薄い色（色は approachA.py と同じでよい）"},
            "70h_外構_生垣（葉）": {"draw": "fill", "fc": "#9DBE7A", "note": "生垣の緑の帯（10-27 に 70 から分けた）"},
            "77c_外構_樹冠・植え込み・苔（葉）": {"draw": "tree", "note": "樹冠の円と、刈り込み・低木・苔の緑の塗り（10-27 に 77 から分けた）"},
            "79c_外構_みなみのさんかく_樹冠・ハーブ・緑の目隠し（葉）": {"draw": "tree", "note": "ヤマボウシの樹冠、ハーブの帯、川の柵の緑の目隠し（10-27 に 79 から分けた）"},
            "77_外構_樹木": {"draw": "tree", "note": "樹冠の円＋幹の点、刈り込みと低木は緑の塗り"},
            "78_外構_みなみのさんかく（丘・小径・砂場・水）": {"draw": "outline", "lw": 0.13, "note": "丘の等高線、小径、砂場、水のテーブル、芝の川と足あとの石"},
            "79_外構_みなみのさんかく（木・ハーブ）": {"draw": "tree", "note": "ヤマボウシ、ハーブの帯、川の柵の緑の目隠し（緑の帯）"},
        },
        "labels": labels,
        "trees": trees,
        "parking": {"stalls": stalls, "count": 5, "delivery": 1, "bump": "車路の道路から0.5に"},
        "bikes": {"parents": g["N_BIKE"], "staff": g["STAFF_N"]},
        "reserve": _reserve(g),
        "bump": {"style": "zebra", "fc": "#8E8E8A", "stripe": "#F4F4F2", "pitch": 0.45,
                 "pts": [_r(q) for q in g["srect"](12.3, 17.6, *g["BUMP"])],
                 "note": "横断歩道のような縞（灰と白、0.45ごと）。縞は車路の向き（道路に平行な帯）に並べる、つまり長い辺（車路の幅 5.3）に沿って区切る。歩道 1.0 の上にあり、歩道は白のまま続いて見える"},
        "sidewalk": {"pts": [_r(q) for q in g["srect"](g["SIDEWALK"]["s"][0], g["SIDEWALK"]["s"][1], *g["SIDEWALK"]["d"])], "fc": "white",
                     "note": "西の道沿い 1.0 は歩道（白）。灰色の範囲には入れない"},
        "entrance": {"xy": _r(E((GA0 + GA1) / 2, 0)), "mark": "red_dot", "note": "セキュリティの線の出入口（公園の木戸）"},
        "security_line": {"pts": [_r(q) for q in g["LINE"]], "style": "赤い破線 0.25",
                          "note": "線は大和張りの塀・生垣と建物の外壁でつながる。ここは南の生垣の線だけ、北は大和張りの塀（70）と木戸がそのまま線"},
        "walks": {"pts": [[_r(q) for q in w] for w in g["WALKS"]], "style": "茶の細い破線（道すじ）", "note": "一つ目が保護者と子の道すじ、ほかは来客・駐輪から"},
        "counts": [
            "駐車 5台（うち搬入 1）・乗入れ 1か所",
            "歩道（開放）敷地の境から 1.0、公園の上の端〜食材納品場",
            "駐輪 保護者 %d台・職員 %d台" % (g["N_BIKE"], g["STAFF_N"]),
        ],
        "notes": [
            "保護者・来客の出入口は公園の木戸だけ（赤い破線＝セキュリティの線）。",
            "送り迎えは徒歩と自転車が前提。車は南（川沿い）から入り、駐車 5台（うち搬入 1）。行事の日は駐車場を駐輪に。",
            "高野川沿いは緑の目隠し h1.5（ムベ）。上は開けて本館の南の妻の架構を見せる。",
            "避難の帯 1.5（平らで固い芝）から非常用の門を通って公園へ。",
            "西の道路沿いの敷地の境から 1.0 は歩道として開放（公園の上の端〜食材納品場）。車路の前はスピードバンプが歩道を続ける。",
        ],
        "omit": "approachA.py の番号の丸と凡例、A-A の断面、0〜2歳の家具の番号は配置図に描かない（外構の詳しい図にだけ）。",
    }
    json.dump(spec, open(OUTP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return spec
