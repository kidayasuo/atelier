"""切った部品（01〜06）に、今の 3dm から作る部品を合わせるための変換と、切った部品の「正」の形。

背景（測った結果は mokei/切った部品とのずれ.md）：
  - 架構（柱 40 本・梁）の 3dm の座標は、切ったとき（10-26）から 0.001 mm（模型）も動いていない。
    laser.py の sheet_angle() が 0.49° 違うのは、西の柱がメッシュで、その PathStart（頂点）の拾い方が
    3dm の作り直しで変わっただけ（板の上の向きの違いで、建物は動いていない）。
  - 切った 04・05・06a の板の座標 ＝ 3dm の座標を剛体（回転 CUT_ANG と平行移動）で写したもの。
    つまり「今の 3dm → 切った部品」の剛体は、板ごとの固定の定数だけ（_PARTS）。
  - 動いたのは設計（床の外形・光の筋の東の端など）。これは剛体では表せない → 切った SVG の形を「正」として読む。

使い方（laser.py は書き換えない。今のデータで作る部品の側から呼ぶ）：

    import kirita as K
    K.world_to_cut(g, '05')      # 3dm の座標（実寸 mm）の形 g → 05 の板の座標（模型 mm、左下原点・y 上向き = laser.py の Sheet と同じ）
    K.cut_to_world(g, '05')      # その逆
    K.cut_world('05')            # 05 の SVG の切る線を、3dm の座標（実寸 mm）の MultiPolygon で（穴つき）
    K.cut_found()                # 実際の基礎 ＝ 05 の外形 ＋ 05b の継ぎ足し（穴なし、3dm の座標）。台の表面の「本館の穴」はこれにする
    K.cut_floor('upper'|'lower') # 04 の上の層・下の層（3dm の座標）
    K.cut_roof()                 # 06a（3dm の座標、光の筋の穴 18 本つき）
    K.uv(x, y) / K.xy(f, v)      # 3dm の座標 ⇄ （架構の番号 f：南 1 〜 北 20 の連続値、v＝庇の先から半径方向の距離 mm）
    K.column_world(side, k)      # 架構 k の東 'E'・西 'W' の柱の中心（3dm の座標）
    K.mortise_world(side, k)     # 05 のほぞ穴（描いた形、3dm の座標）
    K.check(laser)               # laser.py（import 済みのモジュール）の今の floors()・roof_parts() と切った部品との差を出す

部品の名前 part：'04l'（04 の下の層）'04u'（04 の上の層）'05'（ベタ基礎）'06a'（屋根の上の層）。
座標の約束：3dm は実寸 mm（FL ＝ z 0）。板は模型 mm（1/100）。板の座標の y は上向き（SVG の y は H − y）。
SVG は書き換えない（読むだけ）。出力の形は「描いた形」（切り幅 0.2 を足す前）。

  python3 mokei/kirita.py         # 定数の自己点検（SVG だけで確かめる。3dm は読まない）
"""
import math, os, re
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
from shapely.ops import unary_union
from shapely import affinity

HERE = os.path.dirname(os.path.abspath(__file__))
CUT = os.path.join(HERE, 'cut')

CX, CY = 194662.93237, -41348.26335      # 本館の弧の中心（laser.py と同じ）
S = 0.01                                  # 1/100
R0 = 190000.0                             # 庇の先（模型の x=0）
# 切ったときの板の向き（laser.sheet_angle() の 10-26 の値）。今の sheet_angle() は −90.4123° で 0.485° 違うが、建物は動いていない
CUT_ANG = -1.5695189530856422             # rad（−89.92681187759875°）

# 板ごとの平行移動（模型 mm。板の座標 ＝ R(CUT_ANG)·S·(3dm の座標) ＋ t）。SVG の形に合わせて 0.001 mm で確かめ済み
_PARTS = {
    '04l': dict(file='04_本館の床_シナ1.7.svg',      t=(676.0727, 484.6225), W=841, H=594),   # 下の層（はだし＋外縁側・あまのがわ）
    '04u': dict(file='04_本館の床_シナ1.7.svg',      t=(676.0724, 298.9085), W=841, H=594),   # 上の層（はだし）
    '05':  dict(file='05_本館のベタ基礎_シナ3.svg',  t=(676.0725, 484.6229), W=841, H=594),
    '06a': dict(file='06a_本館の屋根_上の層_シナ1.7.svg', t=(697.0802, 123.7073), W=841, H=220),
}

# 架構（3dm、10-26 と今で同じ）：南 1 → 北 20 の中心線の角度（度）と、東・西の柱の中心の半径（実寸 mm）
FRAME_TH1 = 186.67341427679315            # 架構 1（南）
FRAME_STEP = 0.8383993583138573           # 1 つ北へ減る角度
COL_R = {'E': 193017.39, 'W': 205017.38}
MORTISE_W, MORTISE_T = 2.1, 1.64          # 05 のほぞ穴（半径方向 × 接線方向、模型 mm。laser.py の MORTISE_W・MORTISE_T）


# ---------------- 変換 ----------------
def _fwd(part):
    return CUT_ANG, _PARTS[part]['t']

def world_to_cut(g, part='05'):
    """3dm の座標（実寸 mm）の形 → 部品 part の板の座標（模型 mm、y 上向き）"""
    ang, t = _fwd(part)
    g = affinity.scale(g, S, S, origin=(0, 0))
    g = affinity.rotate(g, ang, origin=(0, 0), use_radians=True)
    return affinity.translate(g, t[0], t[1])

def cut_to_world(g, part='05'):
    """板の座標 → 3dm の座標（world_to_cut の逆）"""
    ang, t = _fwd(part)
    g = affinity.translate(g, -t[0], -t[1])
    g = affinity.rotate(g, -ang, origin=(0, 0), use_radians=True)
    return affinity.scale(g, 1 / S, 1 / S, origin=(0, 0))

def uv(x, y):
    """3dm の座標 → (f, v)。f：架構の番号（南 1 〜 北 20 の連続値）、v：庇の先から半径方向（実寸 mm）"""
    t = math.degrees(math.atan2(y - CY, x - CX)) % 360
    return 1 + (FRAME_TH1 - t) / FRAME_STEP, math.hypot(x - CX, y - CY) - R0

def xy(f, v):
    t = math.radians(FRAME_TH1 - (f - 1) * FRAME_STEP); r_ = R0 + v
    return CX + r_ * math.cos(t), CY + r_ * math.sin(t)

def column_world(side, k):
    return np.array(xy(k, COL_R[side] - R0))

def rect_world(side, k, rad_w, tan_w):
    """架構 k の柱の位置に、半径方向 rad_w × 接線方向 tan_w（模型 mm）の長方形（3dm の座標）"""
    t = math.radians(FRAME_TH1 - (k - 1) * FRAME_STEP)
    er = np.array([math.cos(t), math.sin(t)]); et = np.array([-math.sin(t), math.cos(t)])
    c = column_world(side, k); hr, ht = rad_w / S / 2, tan_w / S / 2
    return Polygon([c - hr * er - ht * et, c + hr * er - ht * et, c + hr * er + ht * et, c - hr * er + ht * et])

def mortise_world(side, k):
    return rect_world(side, k, MORTISE_W, MORTISE_T)


# ---------------- 切った SVG を読む ----------------
_cache = {}
def _rings(fname):
    """SVG の「切る（赤）」の線を、(点列, 閉じているか) の列で（板の座標、y 上向き）"""
    t = open(os.path.join(CUT, fname), encoding='utf-8').read()
    H = float(re.search(r'viewBox="0 0 [\d.]+ ([\d.]+)"', t).group(1))
    cut = t.split('<g id="切る（赤）"')[1].split('</g>')[0]
    out = []
    for d in re.findall(r'<path d="([^"]+)"', cut):
        pts = [tuple(map(float, p.split(','))) for p in re.findall(r'[-\d.]+,[-\d.]+', d)]
        out.append(([(x, H - y) for x, y in pts], d.strip().endswith('Z')))
    return out

def _assemble(rings):
    """閉じた線と、つなぎ（切り残し）で切れた線を、穴つきの Polygon の列にする。
    つなぎの切れた外形は laser.Sheet.tabbed の順 [c0+h→c1−h, c1+h→L, 0→c0−h] を、0→… の順につなぎ直す"""
    closed = [Polygon(p) for p, c in rings if c and len(p) > 3]
    opens = [p for p, c in rings if not c]
    for i in range(0, len(opens) - len(opens) % 3, 3):
        s1, s2, s3 = opens[i:i + 3]
        closed.append(Polygon(s3 + s1 + s2))
    closed.sort(key=lambda p: -p.area)
    ext, holes = [], []
    for p in closed:
        rp = p.representative_point()
        host = next((i for i, e in enumerate(ext) if e.contains(rp)), None)
        if host is None: ext.append(p); holes.append([])
        else: holes[host].append(p)
    return [Polygon(e.exterior, [h.exterior for h in hs]) for e, hs in zip(ext, holes)]

def cut_sheet(part):
    """部品 part の切る線を、板の座標の MultiPolygon で（穴つき）"""
    key = ('sheet', part)
    if key in _cache: return _cache[key]
    polys = _assemble(_rings(_PARTS[part]['file']))
    if part in ('04l', '04u'):
        ymin = max(polys, key=lambda p: p.area).bounds[1]           # いちばん大きい外形＝下の層。それより下に置いたものが上の層
        polys = [p for p in polys if (p.centroid.y >= ymin - 1) == (part == '04l')]
    elif part == '06a':
        polys = [max(polys, key=lambda p: p.area)] if len(polys) == 1 else polys
    g = MultiPolygon(polys) if len(polys) > 1 else polys[0]
    _cache[key] = g
    return g

def cut_world(part):
    """部品 part の切る線を、3dm の座標（実寸 mm）で"""
    return cut_to_world(cut_sheet(part), part)

def _outer(g):
    return unary_union([Polygon(p.exterior) for p in getattr(g, 'geoms', [g])])

def cut_floor(layer='lower'):
    """04 の床（3dm の座標）。layer：'lower'（はだし＋外縁側）か 'upper'（はだし）。柱の穴つき"""
    return cut_world('04l' if layer == 'lower' else '04u')

def cut_roof():
    """06a（3dm の座標）。穴は光の筋 18 本（東の端は今の 3dm より約 14.5 mm 長い。06c の差し込み小片が埋める）"""
    return cut_world('06a')

def pads_world():
    """05b の継ぎ足し（南北の妻の柱 4 本のほぞ穴の外半分）を、3dm の座標で。laser.found_ext_sheets と同じ作り方を、切った 05 の外形から"""
    outer = Polygon(_outer(cut_world('05')).geoms[0].exterior) if hasattr(_outer(cut_world('05')), 'geoms') else Polygon(_outer(cut_world('05')).exterior)
    pads = []
    for side in 'EW':
        for k in range(1, 21):
            mo = mortise_world(side, k)
            if outer.buffer(-1).contains(mo): continue
            blk = mo.buffer(260, join_style=2)
            q = blk.difference(outer.buffer(-1)).difference(mo).difference(outer)
            if q.is_empty: continue
            pads.append(max(getattr(q, 'geoms', [q]), key=lambda x: x.area))
    return pads

def cut_found(with_pads=True):
    """実際のベタ基礎の外形（穴なし、3dm の座標）。05 の外形（柱のほぞ穴は穴にしない。妻の柱のほぞ穴が外へ開いた切れ込みは残る）
    ＋ 05b の継ぎ足し（縁に貼る）。台の表面の「本館の穴」「西館の穴の差し引き」は laser.floors() の found の代わりにこれを使う。
    1 つの Polygon（外形に切れ込みがあれば、継ぎ足しで埋まる）"""
    key = ('found', with_pads)
    if key in _cache: return _cache[key]
    g = _outer(cut_world('05'))
    if with_pads:
        g = unary_union([g] + pads_world()).buffer(1).buffer(-1)
        g = unary_union([Polygon(p.exterior) for p in getattr(g, 'geoms', [g])])
    _cache[key] = g
    return g


# ---------------- 点検 ----------------
def _ray(poly, f, rmax=2.2e5):
    t = math.radians(FRAME_TH1 - (f - 1) * FRAME_STEP)
    ln = LineString([(CX + 1.8e5 * math.cos(t), CY + 1.8e5 * math.sin(t)), (CX + rmax * math.cos(t), CY + rmax * math.sin(t))])
    g = poly.intersection(ln); out = []
    for s in getattr(g, 'geoms', [g]):
        if s.is_empty: continue
        rr = sorted(math.hypot(x - CX, y - CY) for x, y in s.coords); out.append((rr[0], rr[-1]))
    return sorted(out)

def check(laser, tol=0.3):
    """今の 3dm（laser.floors()・roof_parts()）と切った部品の差。外縁の位置を架構の線の上と間（0.5 おき）で測り、
    tol（模型 mm）を超える所と、面の差（0.03 m² 以上）の場所を出す。戻り：差の一覧"""
    up, lo, fo = laser.floors()
    roof = laser.roof_parts()[0]
    pairs = [('04上', cut_floor('upper'), up), ('04下', cut_floor('lower'), lo), ('05', cut_found(False), fo), ('06a', cut_roof(), roof)]
    rep = []
    for nm, cut, now in pairs:
        cut_e, now_e = Polygon(_outer(cut).geoms[0].exterior) if hasattr(_outer(cut), 'geoms') else _outer(cut), Polygon(_outer(now).geoms[0].exterior) if hasattr(_outer(now), 'geoms') else _outer(now)
        for f in np.arange(1.02, 19.99, 0.5):
            a, b = _ray(cut, f), _ray(now, f)
            if not a or not b: continue
            for side, i, j in (('東', 0, 0), ('西', -1, 1)):
                d = (b[i][j] - a[i][j]) * S
                if abs(d) > tol: rep.append((nm, round(f, 2), side + 'の縁', round(d, 2)))
        for lab, g in (('切った部品にだけある', cut.difference(now)), ('今の 3dm にだけある', now.difference(cut))):
            for p in getattr(g, 'geoms', [g]):
                if p.area < 0.03e6: continue
                fs = [uv(*q) for q in p.exterior.coords]
                rep.append((nm, lab, round(p.area / 1e6, 2), 'f %.2f〜%.2f' % (min(q[0] for q in fs), max(q[0] for q in fs)),
                            'v %.2f〜%.2f m' % (min(q[1] for q in fs) / 1e3, max(q[1] for q in fs) / 1e3)))
    return rep


def _selftest():
    """SVG だけで：板の座標 ⇄ 3dm の座標が往復で戻ること、05 の外形・ほぞ穴 36 個が柱の位置と合うこと"""
    g05 = cut_sheet('05')
    back = world_to_cut(cut_to_world(g05, '05'), '05')
    assert g05.symmetric_difference(back).area < 1e-6
    holes = [Polygon(i) for i in g05.interiors]
    assert len(holes) == 36, len(holes)                                     # 40 本のうち妻の 4 本は外へ開いた切れ込み
    worst = 0
    for h in holes:
        c = Point(h.centroid)
        best = min((world_to_cut(mortise_world(s, k), '05').centroid.distance(c) for s in 'EW' for k in range(1, 21)))
        worst = max(worst, best)
    print('05 ほぞ穴 36 個の中心と、柱の位置（定数）との最大のずれ', round(worst, 4), 'mm（模型）')
    assert worst < 0.01
    f = cut_found()
    print('実際の基礎 面積 %.1f m2、%s、穴 %d' % (f.area / 1e6, f.geom_type, len(f.interiors) if f.geom_type == 'Polygon' else -1))
    r = cut_roof(); print('06a 外形 面積 %.1f m2、穴 %d' % (Polygon(r.exterior).area / 1e6, len(r.interiors)))
    for l in ('upper', 'lower'):
        g = cut_floor(l); print('04', l, g.geom_type, '%.1f m2' % (g.area / 1e6))

if __name__ == '__main__':
    _selftest()
