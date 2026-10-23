"""間仕切りと戸（設計監修、10-23夜。ユーザー：平面図で先生が気づきそうなところを全て直す）
使い方:
  python3 add_inner.py walls IN.3dm OUT.3dm   … 2 階の間仕切り（納まりの次、壁の端をそろえるの前）
  python3 add_inner.py doors IN.3dm OUT.3dm   … 室内の戸の板（壁の端をそろえるの次）

walls：2 階（西館）の部屋の床の板の境に間仕切りを立てる。今まで 2 階の壁は更衣・ロッカーの北の壁と腰壁だけで、
  便所・湯沸に壁が無かった。厚さ 100（ほかの間仕切りと同じ）、床（2FL）から上の屋根の下面か梁の下端まで（その位置で上に
  ある、いちばん低い面まで）。戸の所は h2100 で開け、上はまぐさ（壁）を残す。レイヤーは 24（西館の間仕切り）。
  → 西館係：西館の持ち分なので、`add_west_south.py` に移してよい（中身はこの WALLS2 の表）。

doors：壁の「まぐさ」（床から 1.7〜2.6 m の高さに浮いた壁の片で、その下が空いている所＝戸の開口）を全部拾い、戸の板を入れる。
  きまり（保育所の室内は引き戸が基本：指を挟みにくく、開けたままにできる）：
  - 室内：開口の脇の壁が開口の幅以上続く側へ引く片引き戸。両脇とも短ければ開き戸（部屋の側へ開く）。
  - 外に面する戸：外開きの開き戸（雨仕舞・防犯）。
  - すでに戸やガラスの物がある開口（16・19・19c・27・48・66・89）と、長さ 2.5 m を超える片（路地の梁など）は触らない。
  板は厚さ 36、高さ 2,050、閉じた位置。レイヤー `19d_建具_室内の戸（木）`、名前に種類と向き
  （「片引き戸 W900 引く+／面+」「開き戸 W800 吊元+／開く+」：+／− は開口の軸・法線の向き）。図は名前を読んで
  開き戸の弧を描く（draw100.py）。
"""
import sys, re, math, numpy as np, rhino3dm as r
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

MODE, IN, OUT = sys.argv[1:4]
HERE = __import__('os').path.dirname(__import__('os').path.abspath(__file__))
sys.path.insert(0, HERE)
from uv import uv, xy

m = r.File3dm.Read(IN)
LN = {i: l.Name for i, l in enumerate(m.Layers)}

def layer(name, rgb):
    for i, l in enumerate(m.Layers):
        if l.Name == name: return i
    L = r.Layer(); L.Name = name; L.Color = (*rgb, 255); return m.Layers.Add(L)

def verts(g):
    return np.array([[g.Vertices[i].X, g.Vertices[i].Y, g.Vertices[i].Z] for i in range(len(g.Vertices))])

def box_mesh(P4, z_bot, z_top):
    """P4：下の 4 点（xy）、z_top：4 点それぞれの上端"""
    M = r.Mesh()
    for (x, y) in P4: M.Vertices.Add(float(x), float(y), float(z_bot))
    for (x, y), zt in zip(P4, z_top): M.Vertices.Add(float(x), float(y), float(zt))
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        M.Faces.AddFace(*f)
    M.Normals.ComputeNormals(); M.Compact()
    return M

def attrs(li, name=''):
    a = r.ObjectAttributes(); a.LayerIndex = li; a.Name = name; return a

def write(extra):
    out = r.File3dm(); out.Settings.ModelUnitSystem = m.Settings.ModelUnitSystem
    for l in m.Layers: out.Layers.Add(l)
    for mt in m.Materials: out.Materials.Add(mt)
    for o in m.Objects: out.Objects.Add(o.Geometry, o.Attributes)
    for g, a in extra: out.Objects.Add(g, a)
    out.Write(OUT, 8)

# ================================================================ walls（2 階）
FL2 = 3260
DOOR_H = 2100
T_WALL = 100
# 線（u 一定か v 一定）、範囲、戸の開口 [(から, まで)]（同じ座標の向きで）
WALLS2 = [
    # 便所・湯沸（u 24〜27、v −3.9〜−1.9）を個室に
    dict(u=24.0, v=(-3.9, -1.9)),                                   # 便所｜休憩室
    dict(u=27.0, v=(-3.9, -1.9)),                                   # 便所｜ホール
    dict(v=-3.9, u=(24.0, 27.0), doors=[(25.9, 26.7)]),             # 便所｜ホール：戸 0.8（ホールの側から）
    dict(v=-1.9, u=(24.0, 27.0)),                                   # 便所の東：床の縁（下は東の帯の吹き抜け）、腰壁の所を壁に
    # 休憩室とホール・ぐったり休憩
    dict(u=24.0, v=(-5.0, -3.9)),                                   # 休憩室｜ホール
    dict(v=-5.0, u=(24.0, 27.75), doors=[(25.0, 25.9)]),            # 休憩室｜ホール：戸 0.9
    dict(v=-8.1, u=(21.0, 27.75), doors=[(26.55, 27.45)]),          # 休憩室｜ぐったり休憩：戸 0.9（更衣の側に寄せる）
    # 更衣・ロッカー（北の壁 u 29.69 は既にある）
    dict(u=27.75, v=(-13.3, -5.0)),                                 # 休憩室・ぐったり休憩｜更衣
    dict(v=-5.0, u=(27.75, 29.69), doors=[(28.3, 29.1)]),           # 更衣｜ホール：戸 0.8
    # 会議室（遊戯室を見渡す北の縁は腰壁のまま）
    dict(v=-5.0, u=(29.69, 33.0), doors=[(30.05, 30.95)]),          # 会議室｜ホール・階段：戸 0.9
]

def top_heights(pts_xy, tris):
    """各点の真上で、2FL より上のいちばん低い面（屋根の下面・梁の下端）の高さ"""
    out = []
    for (x, y) in pts_xy:
        best = None
        for T in tris:
            # 点 (x, y) を含む三角形の高さ（重心座標）
            a, b, c = T[:, :2]
            v0, v1, v2 = b - a, c - a, np.array([x, y]) - a
            d = v0[0] * v1[1] - v0[1] * v1[0]
            if abs(d) < 1e-6: continue
            s = (v2[0] * v1[1] - v2[1] * v1[0]) / d; t = (v0[0] * v2[1] - v0[1] * v2[0]) / d
            if s < -1e-6 or t < -1e-6 or s + t > 1 + 1e-6: continue
            z = T[0, 2] + s * (T[1, 2] - T[0, 2]) + t * (T[2, 2] - T[0, 2])
            if z > FL2 + 1500 and (best is None or z < best): best = z
        out.append(best if best is not None else FL2 + 2400)
    return out

if MODE == 'walls':
    # 屋根（20）・梁（22b）・桁（22d）の三角形（押し出しは draw100 と同じ方法で三角形に）
    src = open(__import__('os').path.join(HERE, 'draw100.py'), encoding='utf-8').read()
    ns = {}
    exec(compile(src[:src.index('# ================================================================ ここから描画')].replace('IN, OUTD = sys.argv[1], sys.argv[2]', 'IN, OUTD = "' + IN + '", "/tmp"'), 'd100', 'exec'), ns)
    TRIS = []
    for ob in ns['OBJ']:
        if re.match(r'^(20|22b|22d)_', ob['layer']):
            TRIS += [t for t in ob['T']]
    TRIS = [t for t in TRIS if abs(np.cross(t[1] - t[0], t[2] - t[0])[2]) > 1.0]      # 鉛直の面は除く
    L24 = [i for i, n in LN.items() if n.startswith('24_')][0]
    extra = []
    h = T_WALL / 2000.0
    for w in WALLS2:
        if 'u' in w and isinstance(w['u'], float):
            u = w['u']; a0, a1 = w['v']
            P = lambda s, e: [xy(u - h, s), xy(u + h, s), xy(u + h, e), xy(u - h, e)]
            along = 'v'
        else:
            v = w['v']; a0, a1 = w['u']
            P = lambda s, e: [xy(s, v - h), xy(e, v - h), xy(e, v + h), xy(s, v + h)]
            along = 'u'
        cuts = sorted(w.get('doors', []))
        segs, s = [], a0
        for c0, c1 in cuts: segs.append((s, c0, None)); segs.append((c0, c1, 'door')); s = c1
        segs.append((s, a1, None))
        for s0, s1, kind in segs:
            if s1 - s0 < 0.01: continue
            P4 = P(s0, s1); zt = top_heights(P4, TRIS)
            if kind == 'door':
                extra.append((box_mesh(P4, FL2 + DOOR_H, zt), attrs(L24, '2階の間仕切り（戸の上）')))
            else:
                extra.append((box_mesh(P4, FL2, zt), attrs(L24, '2階の間仕切り')))
    write(extra)
    print('add_inner walls:', len(extra), 'pieces →', OUT)

# ================================================================ doors
if MODE == 'doors':
    T_DOOR, H_DOOR = 36, 2050
    def fp_of(g, V):
        ps = []
        for i in range(g.Faces.Count):
            f = g.Faces[i]
            for t in ((f[0], f[1], f[2]), (f[0], f[2], f[3])) if f[2] != f[3] else ((f[0], f[1], f[2]),):
                P_ = Polygon(V[list(t), :2])
                if P_.area > 1: ps.append(P_.buffer(0))
        return unary_union(ps) if ps else Polygon()
    WALL = re.compile(r'^(17|21|24|38)_')
    FILL = re.compile(r'^(16|19|19c|27|48|66|89)_')
    W, F, ROOMS = [], [], []
    for o in m.Objects:
        ln = LN[o.Attributes.LayerIndex]; g = o.Geometry
        if not isinstance(g, r.Mesh): continue
        V = verts(g)
        if WALL.match(ln): W.append(dict(ln=ln, fp=fp_of(g, V), z0=V[:, 2].min(), z1=V[:, 2].max()))
        elif FILL.match(ln): F.append(dict(fp=fp_of(g, V), z0=V[:, 2].min(), z1=V[:, 2].max()))
        elif re.match(r'^(3[1-6]|4[1-5]|43b|5[2-9]|15)[a-z]?_', ln): ROOMS.append(dict(ln=ln, fp=fp_of(g, V), z=V[:, 2].max()))
    INSIDE = [dict(fp=fp_of(o.Geometry, verts(o.Geometry)), z=verts(o.Geometry)[:, 2].max()) for o in m.Objects
              if isinstance(o.Geometry, r.Mesh) and re.match(r'^(12|13|23|25|36)_', LN[o.Attributes.LayerIndex])]
    def room_at(p, z):
        for rm in ROOMS:
            if abs(rm['z'] - z) < 1500 and rm['fp'].contains(Point(*p)): return rm['ln']
        for rm in INSIDE:                      # 部屋の名前の無い床（本館の床・2 階の床・階段）は「中」
            if abs(rm['z'] - z) < 1500 and rm['fp'].buffer(50).contains(Point(*p)): return '中'
        return '中' if z > FL2 - 100 else None            # 2 階に外へ出る戸は無い（階段の吹き抜けの縁など）
    WN = unary_union([w_['fp'] for w_ in W if w_['z1'] - w_['z0'] > 2000])
    L19D = layer('19d_建具_室内の戸（木）', (165, 120, 75))
    extra, log = [], []
    for w in W:
        for base in (0.0, float(FL2)):
            h0 = w['z0'] - base
            if not (1700 <= h0 <= 2600): continue
            fp = w['fp']
            if fp.is_empty: continue
            below = [b for b in W if b is not w and b['z0'] < base + 900 and b['z1'] > base + 300 and b['fp'].intersection(fp).area > 0.3 * fp.area]
            if below: continue
            rect = fp.minimum_rotated_rectangle; c = np.array(rect.exterior.coords)[:4]
            e1, e2 = c[1] - c[0], c[2] - c[1]
            if np.linalg.norm(e1) >= np.linalg.norm(e2): ax, thv = e1, e2
            else: ax, thv = e2, e1
            Lw = np.linalg.norm(ax); th = np.linalg.norm(thv)
            if not (550 <= Lw <= 2500): continue
            ax = ax / Lw; n = np.array([-ax[1], ax[0]])
            mid = c.mean(0)
            if any(f['z0'] < base + 1500 and f['z1'] > base + 300 and f['fp'].distance(fp) < 250 and f['fp'].buffer(300).intersection(fp).area > 0.3 * fp.area for f in F): continue   # 既に戸・ガラスがある
            ra = room_at(mid + n * 400, base + 10); rb = room_at(mid - n * 400, base + 10)
            outside = ra is None or rb is None
            if outside:
                po = mid + n * 400 * (1 if ra is None else -1)
                if WN.distance(Point(*po)) < 700 and Point(*po).distance(Point(*mid)) > 0: 
                    # 外の側がすぐ別の壁（本館と西館のすき間など）なら通り抜けの口：戸は向こうの側にある
                    near = [w_ for w_ in W if w_ is not w and w_['z1'] - w_['z0'] > 2000 and w_['fp'].distance(Point(*po)) < 700 and w_['fp'].distance(fp) > 150]
                    if near: continue
            # 開口の脇の壁が、軸の向きにどれだけ続くか（床から 1 m の高さで）
            def run(sign):
                d = 0.0; step = 50.0
                while d < Lw + 200:
                    p = mid + ax * sign * (Lw / 2 + d + step / 2)
                    if not any(b['z0'] < base + 1000 < b['z1'] and b['fp'].buffer(5).contains(Point(*p)) for b in W): break
                    d += step
                return d
            rp, rm_ = run(+1), run(-1)
            if outside:
                kind = '開き戸'; hinge = +1 if rp >= rm_ else -1; swing = +1 if ra is None else -1          # 外へ開く
            elif max(rp, rm_) < Lw - 50 and min(rp, rm_) >= Lw / 2 - 50 and Lw >= 1150:
                kind = '引き分け戸'
                def busy(rn): return bool(rn) and any(k in rn for k in ('西吹き抜け', 'ホール', '東の帯', '海峡', '中'))
                face = +1 if busy(ra) and not busy(rb) else -1 if busy(rb) and not busy(ra) else +1
            elif max(rp, rm_) >= Lw - 50:
                kind = '片引き戸'; slide = +1 if rp >= rm_ else -1
                # 引き戸は人の多い側（廊下・ホール・西吹き抜け・東の帯）の面を走る。どちらでもなければ広い部屋の側
                def busy(rn): return bool(rn) and any(k in rn for k in ('西吹き抜け', 'ホール', '東の帯', '海峡', '中'))
                face = +1 if busy(ra) and not busy(rb) else -1 if busy(rb) and not busy(ra) else +1
            else:
                kind = '開き戸'; hinge = +1 if rp >= rm_ else -1
                def busy(rn): return bool(rn) and any(k in rn for k in ('西吹き抜け', 'ホール', '東の帯', '海峡', '中'))
                swing = -1 if busy(ra) else +1                                       # 廊下の側へは開かない（部屋の側へ）
            Wd = Lw
            if kind == '引き分け戸':
                off = th / 2 + T_DOOR / 2 + 10; cc = mid + n * face * off; t = n * T_DOOR / 2
                for sg in (-1, +1):
                    b0 = cc + ax * sg * 0; b1 = cc + ax * sg * (Wd / 2 + 20)
                    extra.append((box_mesh([b0 - t, b1 - t, b1 + t, b0 + t], base + 10, [base + H_DOOR] * 4),
                                  attrs(L19D, f'引き分け戸 W{round(Wd)} 面{"+" if face > 0 else "-"}')))
                ua = uv(*mid)
                log.append((round(ua[0], 2), round(ua[1], 2), round(base / FL2) + 1, f'引き分け戸 W{round(Wd)}', (ra or '外')[:14], (rb or '外')[:14]))
                continue
            if kind == '片引き戸':
                off = th / 2 + T_DOOR / 2 + 10
                cc = mid + n * face * off
                a0 = cc - ax * (Wd / 2 + 20); a1 = cc + ax * (Wd / 2 + 20)
                name = f'片引き戸 W{round(Wd)} 引く{"+" if slide > 0 else "-"} 面{"+" if face > 0 else "-"}'
            else:
                cc = mid
                a0 = cc - ax * (Wd / 2 - 5); a1 = cc + ax * (Wd / 2 - 5)
                hp = mid + ax * hinge * (Wd / 2); od = n * swing
                name = f'開き戸 W{round(Wd)} 吊元 {hp[0]:.0f},{hp[1]:.0f} 開く {od[0]:.4f},{od[1]:.4f}'
            t = n * T_DOOR / 2
            P4 = [a0 - t, a1 - t, a1 + t, a0 + t]
            extra.append((box_mesh(P4, base + 10, [base + H_DOOR] * 4), attrs(L19D, name)))
            ua = uv(*mid)
            log.append((round(ua[0], 2), round(ua[1], 2), round(base / FL2) + 1, name, (ra or '外')[:14], (rb or '外')[:14]))
    write(extra)
    for l_ in sorted(log): print(' ', l_)
    print('add_inner doors:', len(extra), '→', OUT)
