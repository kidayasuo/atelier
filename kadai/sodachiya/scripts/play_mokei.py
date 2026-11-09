"""遊戯室の遊具の模型（1/100）の部品：data/play.json から、部品の表（Markdown）と平らな部品の外形（SVG・DXF）を作る。
遊戯室の担当。レーザーの最終データ（mokei/cut/）は模型作成の担当なので、ここは下書き。
色は mokei/laser.py と同じ：赤＝切る、青＝彫る、黒＝参考（送る前に消す）。1 単位＝1 mm（模型の実寸）。
出力：out/sodachiya_play_mokei.md・out/sodachiya_play_mokei_parts.svg・.dxf
"""
import os, sys, math, json, pickle, numpy as np, rhino3dm as r
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'model', 'build', 'south'))
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely import affinity
from uv import xy, uv
from meshkit import RW

P = json.load(open(os.path.join(ROOT, 'data', 'play.json'), encoding='utf-8'))
WN = pickle.load(open(os.path.join(ROOT, 'data', 'wnew.pkl'), 'rb'))['WN']
S = 0.01                                                # 1/100：世界の mm → 模型の mm
def X(u, w): return np.array(xy(u, -0.9 - w))
t0 = X(41, 0) - X(39, 0); ROT = -math.degrees(math.atan2(t0[1], t0[0]))
def M(g):                                               # 世界の形 → 模型の mm（u の向きを横に）
    return affinity.scale(affinity.rotate(g, ROT, origin=(0, 0)), S, S, origin=(0, 0))

cw = P['catwalk']; sp = cw['steps']; rg = P['ring']; nt = P['net']; ld = P['landing']
band = WN.buffer(-cw['inset'] * 1000, join_style=1).difference(WN.buffer(-(cw['inset'] + cw['width']) * 1000, join_style=1))
CAT = band.intersection(unary_union([RW(cw['u_start'], 60, -0.5, 1.6), RW(cw['north_u'], 60, -0.5, cw['west_w'])]))
HIGH = CAT.intersection(unary_union([RW(cw['u_start'], cw['north_u'] + 0.01, -0.5, 1.6), RW(cw['north_u'], 60, -0.5, sp['w0'])]))
LOW = CAT.intersection(RW(cw['north_u'], 60, sp['w1'], cw['west_w']))
c_net = X(nt['u'], nt['w']); ring_in = Point(c_net).buffer(rg['inner_r'] * 1000, resolution=48)
RING = Point(c_net).buffer(rg['outer_r'] * 1000, resolution=48).difference(ring_in)
c_ld = X(ld['u'], ld['w']); LAND = Point(c_ld).buffer(ld['r'] * 1000, resolution=3)
A = M(HIGH.union(RING).buffer(1).buffer(-1))            # 板 A：東のキャットウォーク h3.0＋輪の通路（ひと続き）
B = M(LOW.union(LAND).buffer(1).buffer(-1))             # 板 B：北の低い所 h2.0＋踊り場
steps = []
for k in range(sp['n']):
    wa = sp['w0'] + (sp['w1'] - sp['w0']) * k / sp['n']; wb = sp['w0'] + (sp['w1'] - sp['w0']) * (k + 1) / sp['n']
    steps.append(M(CAT.intersection(RW(cw['north_u'], 60, wa, wb))))

# 手すりの長さ（壁に沿わない縁）
def rail_len(walk, skip):
    e = walk.boundary.difference(WN.buffer(-cw['inset'] * 1000 + 20).exterior.buffer(60)).difference(skip)
    return e.length * S
BR = LineString([c_net, c_ld]).buffer(P['bridge']['width'] * 500, cap_style=2)
railA = rail_len(HIGH.union(RING), ring_in.buffer(5).union(BR).union(LOW.buffer(5)))
railB = rail_len(LOW.union(LAND), BR.union(HIGH.buffer(300)))

# 吊り材（ピアノ線）の長さ：3dm の取り込み用ファイルの 83 の細い管から
pl = r.File3dm.Read(os.path.join(ROOT, 'model', 'sodachiya_play_layers.3dm'))
hang = []
for o in pl.Objects:
    if pl.Layers[o.Attributes.LayerIndex].Name.startswith('83') and isinstance(o.Geometry, r.Mesh):
        g = o.Geometry; V = np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])
        ext = V.max(0) - V.min(0)
        if ext[2] > 1500 and max(ext[0], ext[1]) < 3000:      # 縦長の細い管＝吊り材
            hang.append(round(float(np.linalg.norm(ext)) * S, 1))
hang.sort()

# すべり台・はしご・橋の長さ
sl = P['slide']; spl = np.linalg.norm(X(*sl['from']) - X(*sl['to'])) / 1000; sdrop = sl['h'] - 0.35
slide_L = math.hypot(spl, sdrop); slide_deg = math.degrees(math.atan2(sdrop, spl))
la = P['ladder']; lpl = np.linalg.norm(X(*la['base']) - X(*la['top'])) / 1000; ladder_L = math.hypot(lpl, la['h'])
dbr = (c_ld - c_net) / np.linalg.norm(c_ld - c_net)
br_plan = (np.linalg.norm(c_ld - c_net) - rg['outer_r'] * 1000 - ld['r'] * 900) / 1000
br_L = br_plan + 8 * P['bridge']['sag'] ** 2 / (3 * br_plan)        # 垂れた網の長さ（放物線の近似）
# 摺鉢ネットの型紙（円錐で近似）：上の縁 r2.1・h3.0、下の口 r0.3・h0.15（マットの上から 0.5）
r1, r2, hh = nt['ring_r'] * 10, nt['bottom_r'] * 10, (cw['h'] - nt['bottom_h']) * 10
sl_n = math.hypot(r1 - r2, hh); R1 = sl_n * r1 / (r1 - r2); R2 = R1 - sl_n; ang = 2 * math.pi * r1 / R1

# ---------------------------------------------------------------- 外形の並べ（SVG・DXF）
cut, eng, ref, texts = [], [], [], []
def place(g, x, y):
    b = g.bounds; return affinity.translate(g, x - b[0], y - b[1])
y = 5.0; x = 5.0
a = place(A, x, y); cut.append(a); texts.append((x, a.bounds[3] + 1.5, 'A 航空ベニヤ0.8 キャットウォーク h3.0＋輪（FL+30 の面）', 2.2))
y = a.bounds[3] + 8
b_ = place(B, x, y); cut.append(b_); texts.append((x, b_.bounds[3] + 1.5, 'B 航空ベニヤ0.8 北の低い所 h2.0＋踊り場', 2.2))
xs = b_.bounds[2] + 6
for k, s in enumerate(steps):
    g = place(s, xs, y); cut.append(g); texts.append((g.bounds[0], g.bounds[3] + 1.0, f'C{k + 1}', 1.6)); xs = g.bounds[2] + 3
# 手すり（h1.1＝11、縦格子は 1.0 ごとに彫る）
y = max(b_.bounds[3], y + 10) + 8
for nm, Lr in (('D1 手すり（A の縁）', railA), ('D2 手すり（B の縁）', railB)):
    Lc = min(Lr, 150.0); n = int(math.ceil(Lr / 150.0))
    for i in range(n):
        Li = min(150.0, Lr - 150.0 * i); g = box(5, y, 5 + Li, y + 11); cut.append(g)
        for xx in np.arange(6, 5 + Li, 1.0): eng.append(LineString([(xx, y + 1), (xx, y + 10)]))
        texts.append((5, y + 12.3, f'{nm} {i + 1}/{n}  長さ {Li:.0f}', 1.8)); y += 16
# すべり台・はしご・ついたて
g = box(5, y, 5 + slide_L * 10, y + sl['width'] * 10); cut.append(g)
texts.append((5, y + sl['width'] * 10 + 1.3, f'E すべり台 KROMA1 幅 {sl["width"]*10:.0f}×{slide_L*10:.0f}（{slide_deg:.0f}°）', 1.8))
x2 = 5 + slide_L * 10 + 8
lw, lL = la['width'] * 10, ladder_L * 10
g = box(x2, y, x2 + lL, y + lw); nr = 5
for i in range(nr):                                      # 段は 5 つに省略（実物は 200 ごとに 10 段）
    cx = x2 + lL * (i + 0.5) / nr; g = g.difference(box(cx - 1.2, y + 1.0, cx + 1.2, y + lw - 1.0))
cut.append(g); texts.append((x2, y + lw + 1.3, f'F はしご 航空ベニヤ0.8 {lw:.0f}×{lL:.0f}（段は 5 つに省略）', 1.8))
sc = P['screen']; x3 = x2 + lL + 8
g = box(x3, y, x3 + (sc['u1'] - sc['u0']) * 10, y + sc['h'] * 10); cut.append(g)
g2 = box(x3 + (sc['u1'] - sc['u0']) * 10 + 3, y, x3 + (sc['u1'] - sc['u0']) * 10 + 3 + (sc['w'] + sc['t']) * 10, y + sc['h'] * 10); cut.append(g2)
texts.append((x3, y + sc['h'] * 10 + 1.3, 'G ついたて KROMA1（L 字の 2 枚）', 1.8))
y += max(sc['h'] * 10, lw) + 8
# 摺鉢ネットの型紙（チュール、はさみで切る＝参考の線）
cx, cy = 5 + R1, y + R1
th = np.linspace(-ang / 2, ang / 2, 80) + math.pi / 2
outer = [(cx + R1 * math.cos(t), cy - R1 + R1 * math.sin(t) - R1 + R1) for t in th]
fan = Polygon([(cx + R1 * math.cos(t), y + R1 * math.sin(t)) for t in th] + [(cx + R2 * math.cos(t), y + R2 * math.sin(t)) for t in th[::-1]])
fan = place(fan, 5, y); ref.append(fan)
texts.append((5, fan.bounds[3] + 1.3, f'H 摺鉢ネットの型紙 チュール（はさみ、のりしろ 3）：外の半径 {R1:.1f}・内 {R2:.1f}・角 {math.degrees(ang):.0f}°', 1.8))
g = box(fan.bounds[2] + 8, y, fan.bounds[2] + 8 + br_L * 10, y + P['bridge']['width'] * 10); ref.append(g)
texts.append((g.bounds[0], g.bounds[3] + 1.3, f'I 吊り橋 チュール {P["bridge"]["width"]*10:.0f}×{br_L*10:.0f}（垂れ {P["bridge"]["sag"]*10:.0f}）', 1.8))
pit = Point(0, 0).buffer(P['pit']['r'] * 10 - 0.5, resolution=32)
g = place(pit, g.bounds[2] + 8, y); cut.append(g); texts.append((g.bounds[0], g.bounds[3] + 1.3, 'J 穴の底のマット KROMA1', 1.8))
W_, H_ = 300.0, max(gg.bounds[3] for gg in cut + ref) + 8
cut = [affinity.scale(gg, 1, 1, origin=(0, 0)) for gg in cut]

def rings(geom):
    out = []
    for gg in getattr(geom, 'geoms', [geom]):
        if gg.geom_type == 'Polygon':
            out.append(np.array(gg.exterior.coords)); out += [np.array(i.coords) for i in gg.interiors]
        elif gg.geom_type in ('LineString', 'LinearRing'): out.append(np.array(gg.coords))
    return out
os.makedirs(os.path.join(ROOT, 'out'), exist_ok=True)
base = os.path.join(ROOT, 'out', 'sodachiya_play_mokei_parts')
L = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W_}mm" height="{H_:.1f}mm" viewBox="0 0 {W_} {H_:.1f}">',
     '<rect width="100%" height="100%" fill="white"/>']
for lay, col, gs in (('参考（切らない・送る前に消す）', '#000000', ref), ('彫る（青）', '#0000FF', eng), ('切る（赤）', '#FF0000', cut)):
    L.append(f'<g id="{lay}" fill="none" stroke="{col}" stroke-width="0.1">')
    for gg in gs:
        for a in rings(gg):
            L.append('<path d="M' + ' L'.join(f'{px:.3f},{H_ - py:.3f}' for px, py in a) + ('Z' if np.allclose(a[0], a[-1]) else '') + '"/>')
    L.append('</g>')
L.append('<g id="参考の文字（送る前に消す）" fill="#000000" font-family="Noto Sans CJK JP, sans-serif">')
for tx, ty, t, sz in texts: L.append(f'<text x="{tx:.2f}" y="{H_ - ty:.2f}" font-size="{sz}">{t}</text>')
L.append('</g></svg>'); open(base + '.svg', 'w').write('\n'.join(L))
import ezdxf
doc = ezdxf.new(units=4)
for ln, ci in (('CUT_red', 1), ('ENGRAVE_blue', 5), ('REF_delete', 7)): doc.layers.add(ln, color=ci)
msp = doc.modelspace()
for ln, gs in (('CUT_red', cut), ('ENGRAVE_blue', eng), ('REF_delete', ref)):
    for gg in gs:
        for a in rings(gg): msp.add_lwpolyline([tuple(p) for p in a], dxfattribs={'layer': ln})
for tx, ty, t, sz in texts: msp.add_text(t, dxfattribs={'layer': 'REF_delete', 'height': sz}).set_placement((tx, ty))
doc.saveas(base + '.dxf')

# ---------------------------------------------------------------- 部品の表
bA, bB = A.bounds, B.bounds
md = f"""# 遊戯室の遊具　模型（1/100）の部品

`scripts/play_mokei.py` が `data/play.json` から作る（遊戯室の担当、下書き）。外形は `out/sodachiya_play_mokei_parts.svg`・`.dxf`（色は `mokei/laser.py` と同じ：赤＝切る・青＝彫る・黒＝参考）。レーザーの最終データにするのは模型作成。
3dm は `model/sodachiya_play_layers.3dm`（レイヤー 80〜89）を読めば、位置と高さが全部ある。

模型の高さは FL（床の上面、GL+3.4）から測る。1 m＝10 mm。

## 吊る・留める（実物と同じ考え）
- 重さは **架構の梁から吊る**（屋根の板ではない）。だから屋根を外しても遊具は残る。
- 吊り材はピアノ線 0.5。梁は航空ベニヤ 2 枚で柱を挟んでいて、あいだに柱の厚さ（約 1.6）のすき間がある。**ピアノ線をすき間に通し、上で折り曲げて 2 枚にまたがる鉤に**する（実物の「梁のあいだを通して鋼の板で受ける」と同じ形）。
- キャットウォークの壁ぎわの縁は、外壁の内側に貼る（受け材の代わり）。輪の東の端も外壁の内側に貼る（突っ張りの代わり）。
- 組む順番：西館の架構を立てる → 外壁 → 板 A（輪とネットを先に貼っておく）を吊る → 段 C → 板 B → 吊り橋 → はしご・すべり台 → 屋根。

## 部品

| 記号 | 部品 | 材料 | 大きさ（模型 mm） | 高さ・付け方 |
|---|---|---|---|---|
| A | 東のキャットウォーク＋輪の通路（ひと続き） | 航空ベニヤ 0.8 | 外形 約 {bA[2]-bA[0]:.0f}×{bA[3]-bA[1]:.0f}（輪の穴 φ{rg['inner_r']*20:.0f}） | 上面 FL+30。壁ぎわは外壁に貼る、外側の縁と輪は吊る |
| B | 北の低い所＋踊り場 | 航空ベニヤ 0.8 | 約 {bB[2]-bB[0]:.0f}×{bB[3]-bB[1]:.0f} | 上面 FL+20。北の壁と北西の斜めの面に貼る＋はしごの脇に柱（丸棒 2.0、長さ 19） |
| C1〜C5 | 北の段（200×5） | 航空ベニヤ 0.8 を 2〜3 枚重ね | 各 約 {sp['w1']*10/sp['n']-sp['w0']*10/sp['n']:.0f}×9 | 上面 FL+28・26・24・22・20。北の壁に貼る |
| D | 手すり（縦格子 h1.1） | 航空ベニヤ 0.8 | 高さ 11、長さ 計 約 {railA+railB:.0f}（A の縁 {railA:.0f}・B の縁 {railB:.0f}） | 縦の線を 1.0 ごとに彫る（実物のすき間 90 は模型で 0.9）。板の縁に立てて貼る、曲がる所は少しずつ曲げる |
| E | すべり台 | KROMA 1 | 幅 {sl['width']*10:.0f}×長さ {slide_L*10:.0f}（{slide_deg:.0f}°） | 踊り場の縁（FL+20）から床（FL+3.5）へ |
| F | はしご | 航空ベニヤ 0.8 | 幅 {la['width']*10:.0f}×長さ {ladder_L*10:.0f} | 段は 5 つに省略（実物は 200 ごとに 10 段）。踊り場の東の脇 |
| G | 北の口のついたて（L 字） | KROMA 1 | {(sc['u1']-sc['u0'])*10:.0f}×{sc['h']*10:.0f} と {(sc['w']+sc['t'])*10:.0f}×{sc['h']*10:.0f} | 床に立てる（吸音の面＝オフホワイト） |
| H | 摺鉢ネット | チュール | 型紙：外の半径 {R1:.1f}・内 {R2:.1f}・角 {math.degrees(ang):.0f}° の扇（円錐で近似） | 上の縁を輪の内側（φ{rg['inner_r']*20:.0f}）に一周貼る、下の口 φ{nt['bottom_r']*20:.0f} を穴の底のマットの上から 5 に（実物 0.5、ユーザー 10-29）。下の口に刺繍糸を 1 周 |
| I | 網の吊り橋 | チュール＋刺繍糸 | 幅 {P['bridge']['width']*10:.0f}×長さ 約 {br_L*10:.0f} | 輪の北西の縁（FL+30）→ 踊り場（FL+20）、真ん中が {P['bridge']['sag']*10:.0f} 垂れる。両脇に刺繍糸を 2 本（手すりの綱、高さ 9） |
| J | 穴の底 | 床の 2 層に穴 φ{P['pit']['r']*20:.0f}＋KROMA 1 のマット | 穴の深さは床の 2 層ぶん 3.4（実物 −450 は 4.5、模型では 1 mm 浅い） | 床のレーザーのデータに穴を足す（模型作成へ） |
| K | 吊り材 | ピアノ線 0.5 | {len(hang)} 本、長さ {', '.join(f'{h:.0f}' for h in hang)}（鉤の分 +5） | キャットウォークの外側の縁 5 本（梁 u 36〜48 の位置）、輪のハの字 6 本（梁 u 39・42・45） |
| L | デッキ・家具階段 | シナ 3 | デッキ {(dk:=P['deck'])['u1']*10-dk['u0']*10:.0f}×{dk['w1']*10-dk['w0']*10:.0f}×高さ 12（4 枚重ね）、階段 3・6・9 | 東の壁沿い（スパン 13） |
| M | 切り株（クスノキ） | 3Dプリント（`out/sodachiya_play_tree_1-100.stl`、骨格から自動、閉じた立体。細い枝は印刷できる太さ φ0.9 に太らせた）。断面模型は `_1-50.stl` | 幹 φ{P['stump']['trunk_r']*20:.0f}、高さ 約31、広がり 約51×59（幹の中心が原点） | 洞（スパン 11、2 階の床の下）。3本の枝先を 2 階の床の裏に当てる |
| N | ひだ（くぼみ 3・丸いベンチ・窓辺の腰掛け） | シナ 1.7・3 | くぼみ 18×7×高さ 14、座 3 | 西の壁・北西の角・北の壁に貼る |
| O | 天井扇 | 航空ベニヤ 0.8 の円＋ピアノ線 0.5 | φ11、FL+60 | 本館の天井扇と同じ作り方にそろえる（任せる） |

M は「本物に触れて育つ」の主題に合わせて、本物の小枝を提案する（色の決まり：木とオフホワイトだけ、に合う）。クスノキは京都の街路樹・社寺に多いので、落ちた小枝を拾える。

## 気をつけること
- 手すりの縦格子を切り抜くと 0.9 のすき間で折れやすいので、彫るだけにした。
- 板 A は大きく（約 {bA[2]-bA[0]:.0f} mm）細い（9 mm）ので、外壁に貼るまでは曲がりやすい。吊る前に輪とネットを地上で貼っておく。
- 穴の底（J）を見せるなら、床の 2 層に穴をあけるのを床を切る前に決める（模型作成の 04 の床のデータ）。
"""
open(os.path.join(ROOT, 'out', 'sodachiya_play_mokei.md'), 'w').write(md)
print('A', A.bounds, 'B', B.bounds, 'rail', railA, railB, 'hang', hang, 'slide', slide_L, slide_deg, 'ladder', ladder_L, 'bridge', br_L, 'net', R1, R2, math.degrees(ang))
