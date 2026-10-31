#! python 3
# -*- coding: utf-8 -*-
"""育ち舎　図の線を Rhino で：sodachiya.3dm から平面・断面・立面の線を出し、今の図（draw100.py）と同じ紙・同じ位置に置く（更新係、10-28、項 20261028-0911-kanshu）

使い方（Rhino 8、Mac）：
  1. sodachiya/sodachiya.3dm を開く（drawings/ の …_views.json と同じ版の 3dm で。git pull したあとに）。
  2. コマンド RunPythonScript で、このファイル（sodachiya/rhino/zumen.py）を選ぶ。数分〜十数分かかる（コマンドの行に進み具合）。
  3. sodachiya/drawings_rhino/ に、図ごと（紙ごと）に <図の名前>.svg・.pdf（と .ai）ができる。
     Illustrator で開き、同じ名前の drawings/<図の名前>_文字.pdf（文字と寸法だけの層）を上に重ねる。紙の大きさ（A1 841×594 mm）と
     位置は同じなので、左上をそろえて置けばぴったり重なる。彩色は Illustrator で手で。
  4. できたら drawings_rhino/ を git add して commit・push する（git add drawings_rhino && git commit && git push）。

描くもの（どの図も 1/100、線だけ。塗り・文字は無し）：
  - 1階平面（FL+1500 で切る）・2階平面（西館、2FL+1000、西の道路の外へずらす）・断面 B・C・D（D は別の紙 sodachiya_sections2_1-100、
    本館と西館の横断を架構 13 の手前（約 0.5 m 南、柱を切らない）で切る。json の skip_layers_re の物は描かない）・立面（園庭の側・道路の側・南の妻・北の妻・高野川の側）。
    断面 A（縦断、r=197 m の円筒で切って平らに伸ばす、西を見る）も（下の draw_section_arc）。
  - 3・4枚目（10-30、項 20261030-2258-present）：sodachiya_plan1F_1-100（1階平面、周りまで紙いっぱい）と sodachiya_plan2F_1-100
    （2階平面、1階と同じ紙の位置・縮尺。西館は 2FL+1000 で切り、その外の本館の屋根・園庭・周りは切らずに真上から見た見えがかり。
    西館の外壁の外形の内は消す：draw_below_top）。周り（PLATEAU の道・建物、公園の線）は組「周り」（細 0.09）：draw_context。
  - 配置図 1/200（項 20261030-0750-present）：sodachiya_siteplan_1-200。真上から見た見えがかり（屋根・越屋根・光の筋・太陽光・
    外構・園庭の物・樹冠・高野川の側）と周り・敷地の境（外の一本）：draw_roofplan。色は draw100 の _色.pdf のまま。
  - 切断（太 0.35）：切断面で物を切った線（Brep は Intersection.BrepPlane、メッシュは MeshPlane）。
  - 見えがかり（細 0.13）：切断面の奥（平面は下）の見える線。RhinoCommon の HiddenLineDrawing（Make2D と同じ計算）にクリッピング平面を付けて。
  - 想像線（細 0.09 の破線）：平面だけ。切断より上の、あえて示す物（屋根・軒の外形、光の筋、越屋根、2階の床の縁、遊戯室の上の遊具、
    天袋、高窓、樹冠）を真上から見た外形。どれを描くかは draw100.py が json に書いた決まり（rules）を読む。
  - 線は「図_<紙>::<図>::切断｜見えがかり｜想像線::<元のレイヤー>」の組に分けて書く（SVG のグループ、PDF の層）。Illustrator で
    元のレイヤーごとに色・太さを変えられる。
  - 描かない物：レイヤー「N 番号」、園のロゴの板（名前が「園のロゴ」）、部屋の色の板（31〜59 の床の面積の板）、隠したレイヤー、
    文字・点・寸法などの立体でない物。平面では梁も描かない（draw100 と同じ）。

置き場所：drawings/<紙>_views.json（draw100.py が書く。3dm の mm → 紙の mm、左上が原点・下へ y）をそのまま使う。
  書き出しの座標は紙の mm（SVG・PDF とも左上が原点、y は下へ。PDF の中では普通どおり左下が原点）。
3dm は変えない：線はメモリの中で作って直接ファイルに書く。.ai だけは Rhino の書き出し（_-Export）を使うので、一時的に線を
  レイヤー「図_…」に足し、書き出したら消す（KEEP_IN_DOC = True にすると残す。保存しなければ 3dm は元のまま）。

ここ（クラウド）では Rhino が無いので走らせて確かめていない。うまく行かないときは、下の「変えてよい所」と、コマンドの行の
メッセージ（どの図のどの段で止まったか）をチャットに貼ってください。
"""
import os, re, json, math, zlib, glob

try:                     # Rhino の外（クラウドの試し）でも、展開の式（arc_unroll_fn）だけ読めるように
    import Rhino
    import Rhino.Geometry as G
    import scriptcontext as sc
    import rhinoscriptsyntax as rs
except ImportError:
    Rhino = G = sc = rs = None

# ---------------------------------------------------------------- 変えてよい所
VIS_MM = 0.13            # 見えがかりの線の太さ（紙の mm）。切断・想像線の太さは json（draw100 の LW_CUT・LW_THIN）から
DASH_MM = (1.6, 0.5, 0.3, 0.5)   # 想像線の破線（紙の mm：線・すき・点・すき）
CURVE_TOL = 2.0          # 曲線を折れ線にするときの許し（モデルの mm、紙では 0.02 mm）
EXPORT_AI = True         # .ai も書き出す（Rhino の _-Export。書き出しの設定は Rhino の既定のまま）
KEEP_IN_DOC = False      # True：線を 3dm のレイヤー「図_…」に残す（.ai 用に足した線を消さない）
AI_ORIGIN = (0.0, 300000.0)      # .ai 用に線を置く所（モデルの mm。建物から離れた空き地。紙の左下がここ）
ONLY = ''                # '断面B' などにすると、その名前を含む図だけ（試すとき）
MULTI_THREAD = True      # HiddenLineDrawing を並列で
# draw100.py と同じ「描かない物」（レイヤーの頭の番号）。平面：objs_for_plan、断面：section_u、立面：elev_objs
PLAN_SKIP = (3, 4, 90, 98)
PLAN1_SKIP = (41, 42, 43, 44, 45)                 # 1 階では 2 階の部屋の板を描かない
SEC_SKIP = (2, 3, 4, 76, 77) + tuple(range(91, 99))
SEC_NOVIS = (2, 12, 13, 90)                       # 断面で切り口だけ（見えがかりは描かない）物
ARC_MAX_EDGE = 1000.0    # 断面 A：展開する前のメッシュの辺の長さの上限（モデルの mm）
ARC_MESH_TOL = 5.0       # 断面 A：Brep をメッシュにするときの許し（モデルの mm）
# ---------------------------------------------------------------- ここまで

doc = sc.doc if sc else None
TOL = (doc.ModelAbsoluteTolerance or 0.01) if doc else 0.01


def say(*a):
    print(u' '.join(u'%s' % x for x in a))
    try:
        Rhino.RhinoApp.Wait()
    except Exception:
        pass


def num(leaf):
    m = re.match(r'(\d+)', leaf)
    return int(m.group(1)) if m else -1


# ---------------------------------------------------------------- 3dm の物
class Obj(object):
    def __init__(s, ro, geo, leaf, full):
        s.id, s.geo, s.leaf, s.full = ro.Id, geo, leaf, full
        s.n = num(leaf)
        b = geo.GetBoundingBox(True)
        s.bmin, s.bmax = (b.Min.X, b.Min.Y, b.Min.Z), (b.Max.X, b.Max.Y, b.Max.Z)


# sodachiya.3dm で開いたときに消してあるレイヤー（clean_wire.py の HIDE_DEFAULT：街の建物・樹木、ユーザー 10-28）は、消えていても読む
HIDE_DEFAULT = ('04', '67', '67c', '77', '77c', '79', '79c', '91', '94', '94b', '94c', '94g')   # 樹木は親の「T 樹木」で消している（10-29）、91 園庭の等高線（10-29）
def _code(name):
    m_ = re.match(r'^(\d+[a-z]?)_', name)
    return m_.group(1) if m_ else None
def layer_visible(ly):
    if _code(ly.Name) in HIDE_DEFAULT:
        return True
    if not ly.IsVisible:
        return False
    p = ly.ParentLayerId
    while p and str(p) != '00000000-0000-0000-0000-000000000000':
        pl = doc.Layers.FindId(p)
        if pl is None:
            break
        if not pl.IsVisible:
            return False
        p = pl.ParentLayerId
    return True


def load_objects():
    out = []
    st = Rhino.DocObjects.ObjectEnumeratorSettings()
    st.HiddenObjects = False
    st.LockedObjects = True
    st.NormalObjects = True
    for ro in doc.Objects.GetObjectList(st):
        ly = doc.Layers[ro.Attributes.LayerIndex]
        full = ly.FullPath or ly.Name
        if full.startswith(u'N 番号') or not layer_visible(ly):
            continue
        if (ro.Attributes.Name or u'').startswith(u'園のロゴ'):
            continue
        g = ro.Geometry
        if isinstance(g, G.Extrusion):
            g = g.ToBrep(True)
        elif isinstance(g, G.SubD):
            try:
                g = g.ToBrep(G.SubDToBrepOptions())
            except Exception:
                continue
        if not isinstance(g, (G.Brep, G.Mesh)) or g is None:
            continue
        out.append(Obj(ro, g, ly.Name, full))
    say(u'物', len(out))
    return out


def site_curves(pat=r'^00_'):
    out = []
    rx = re.compile(pat)
    for ro in doc.Objects:
        ly = doc.Layers[ro.Attributes.LayerIndex]
        if rx.match(ly.Name) and isinstance(ro.Geometry, G.Curve) and layer_visible(ly):
            out.append(ro.Geometry)
    return out


def site_outer():
    """敷地の境の外の一本（00 には境から 1 m 内の線もある。配置図は外の一本だけ、draw100 と同じ）"""
    cs = [c for c in site_curves() if c.IsClosed]
    if not cs:
        return site_curves()
    return [max(cs, key=lambda c: c.GetBoundingBox(True).Diagonal.Length)]


# ---------------------------------------------------------------- 折れ線
def polyline_pts(crv):
    """曲線 → 点の並び（モデルの座標）"""
    if crv is None:
        return []
    ok, pl = crv.TryGetPolyline()
    if not ok:
        try:
            pc = crv.ToPolyline(CURVE_TOL, math.radians(3), 0, 0)
            ok, pl = pc.TryGetPolyline()
        except Exception:
            ok = False
    if ok:
        return [pl[i] for i in range(pl.Count)]
    d = crv.Domain
    n = max(8, int(crv.GetLength() / 200.0))
    return [crv.PointAt(d.T0 + (d.T1 - d.T0) * i / n) for i in range(n + 1)]


def clip_poly(P, R):
    """折れ線（紙の mm）を図の範囲 R=(左, 上, 右, 下) で切る → 折れ線のリスト"""
    x0, y0, x1, y1 = R
    out, cur = [], []

    def inside(p):
        return x0 <= p[0] <= x1 and y0 <= p[1] <= y1
    for a, b in zip(P[:-1], P[1:]):
        t0, t1 = 0.0, 1.0
        dx, dy = b[0] - a[0], b[1] - a[1]
        ok = True
        for p_, q_ in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
            if abs(p_) < 1e-12:
                if q_ < 0:
                    ok = False
                    break
            else:
                r = q_ / p_
                if p_ < 0:
                    t0 = max(t0, r)
                else:
                    t1 = min(t1, r)
        if not ok or t0 > t1:
            if len(cur) > 1:
                out.append(cur)
            cur = []
            continue
        pa = (a[0] + dx * t0, a[1] + dy * t0)
        pb = (a[0] + dx * t1, a[1] + dy * t1)
        if not cur or abs(cur[-1][0] - pa[0]) > 1e-9 or abs(cur[-1][1] - pa[1]) > 1e-9:
            if len(cur) > 1:
                out.append(cur)
            cur = [pa]
        cur.append(pb)
        if t1 < 1.0:
            out.append(cur)
            cur = []
    if len(cur) > 1:
        out.append(cur)
    return out


def _pip(x, y, R):
    """点 (x, y) が閉じた折れ線 R の内か（偶奇）"""
    ins, j = False, len(R) - 1
    for i in range(len(R)):
        (xi, yi), (xj, yj) = R[i], R[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            ins = not ins
        j = i
    return ins


def mask_out(P, rings):
    """折れ線 P（紙の mm）から、rings（閉じた形、どれか一つの内なら除く）の内の所を除く → 折れ線のリスト。
    2 階の紙で、西館の外の見えがかりを西館の外壁の外形の内で消す（2 階の図がある所、10-30）"""
    if not rings or len(P) < 2:
        return [P]
    xs, ys = [p[0] for p in P], [p[1] for p in P]
    bb = [(min(q[0] for q in R), min(q[1] for q in R), max(q[0] for q in R), max(q[1] for q in R)) for R in rings]
    act = [k for k, b in enumerate(bb) if not (max(xs) < b[0] or min(xs) > b[2] or max(ys) < b[1] or min(ys) > b[3])]
    if not act:
        return [P]
    out, cur = [], []

    def flush():
        if len(cur) > 1:
            out.append(list(cur))
    for a, b in zip(P[:-1], P[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ts = [0.0, 1.0]
        sx0, sx1, sy0, sy1 = min(a[0], b[0]), max(a[0], b[0]), min(a[1], b[1]), max(a[1], b[1])
        for k in act:
            B = bb[k]
            if sx1 < B[0] or sx0 > B[2] or sy1 < B[1] or sy0 > B[3]:
                continue
            R = rings[k]
            for c, d in zip(R, R[1:] + R[:1]):
                ex, ey = d[0] - c[0], d[1] - c[1]
                den = dx * ey - dy * ex
                if abs(den) < 1e-12:
                    continue
                t = ((c[0] - a[0]) * ey - (c[1] - a[1]) * ex) / den
                u = ((c[0] - a[0]) * dy - (c[1] - a[1]) * dx) / den
                if 0.0 < t < 1.0 and 0.0 <= u <= 1.0:
                    ts.append(t)
        ts.sort()
        for t0, t1 in zip(ts[:-1], ts[1:]):
            if t1 - t0 < 1e-9:
                continue
            tm = (t0 + t1) / 2
            mx, my = a[0] + dx * tm, a[1] + dy * tm
            pa, pb = (a[0] + dx * t0, a[1] + dy * t0), (a[0] + dx * t1, a[1] + dy * t1)
            if any(bb[k][0] <= mx <= bb[k][2] and bb[k][1] <= my <= bb[k][3] and _pip(mx, my, rings[k]) for k in act):
                flush()
                cur = []
                continue
            if cur and abs(cur[-1][0] - pa[0]) < 1e-9 and abs(cur[-1][1] - pa[1]) < 1e-9:
                cur.append(pb)
            else:
                flush()
                cur = [pa, pb]
    flush()
    return out


# ---------------------------------------------------------------- 一つの紙の線
class Sheet(object):
    def __init__(s, name, J):
        s.name, s.J = name, J
        s.W, s.H = J['paper_mm']
        lw = J.get('line_weights_mm', {})
        s.LW = {u'切断': lw.get('cut', 0.35), u'見えがかり': VIS_MM, u'想像線': lw.get('thin', 0.09), u'敷地の境': lw.get('thin', 0.09),
                u'周り': lw.get('thin', 0.09)}          # 周り：PLATEAU の道・建物、公園の線（細い見えがかり、10-30）
        s.groups = {}          # レイヤーの組 → [折れ線（紙 mm、y 下）]

    def add(s, view, cls, leaf, polys2d, clip):
        key = u'図_%s::%s::%s::%s' % (s.name.replace('sodachiya_', ''), view, cls, leaf)
        L = s.groups.setdefault(key, [])
        for P in polys2d:
            if len(P) >= 2:
                L += clip_poly(P, clip)

    # SVG（Illustrator で開くとグループが残る）
    def write_svg(s, path):
        def esc(t):
            return t.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')
        tree = {}
        for key in sorted(s.groups):
            node = tree
            for part in key.split('::'):
                node = node.setdefault(part, {})
            node[None] = key
        out = [u'<?xml version="1.0" encoding="UTF-8"?>',
               u'<svg xmlns="http://www.w3.org/2000/svg" xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape" '
               u'width="%gmm" height="%gmm" viewBox="0 0 %g %g">' % (s.W, s.H, s.W, s.H)]

        used = {}

        def walk(node, depth):
            for k in sorted(x for x in node if x is not None):
                ch = node[k]
                used[k] = used.get(k, 0) + 1                 # id は重ねない（同じ名前の 2 つ目からは _2…）
                gid = k if used[k] == 1 else u'%s_%d' % (k, used[k])
                out.append(u'%s<g id="%s" inkscape:groupmode="layer" inkscape:label="%s">' % (' ' * depth, esc(gid), esc(k)))
                if None in ch:
                    key = ch[None]
                    cls = key.split('::')[2]
                    da = u' stroke-dasharray="%s"' % ' '.join('%g' % d for d in DASH_MM) if cls == u'想像線' else u''
                    for P in s.groups[key]:
                        out.append(u'%s <polyline fill="none" stroke="#000" stroke-width="%g"%s stroke-linejoin="round" points="%s"/>'
                                   % (' ' * depth, s.LW.get(cls, VIS_MM), da, ' '.join('%.3f,%.3f' % p for p in P)))
                walk(ch, depth + 1)
                out.append(u'%s</g>' % (' ' * depth))
        walk(tree, 0)
        out.append(u'</svg>')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(u'\n'.join(out))

    # PDF（層＝Optional Content。Acrobat で層ごとに出し入れできる）
    def write_pdf(s, path):
        k = 72.0 / 25.4
        keys = sorted(s.groups)
        cs = [u'q %.6f 0 0 %.6f 0 %.4f cm 1 J 1 j 0 0 0 RG' % (k, -k, s.H * k)]
        for i, key in enumerate(keys):
            cls = key.split('::')[2]
            cs.append(u'/OC /oc%d BDC %g w %s 0 d' % (i, s.LW.get(cls, VIS_MM),
                                                     '[%s]' % ' '.join('%g' % d for d in DASH_MM) if cls == u'想像線' else '[]'))
            for P in s.groups[key]:
                cs.append(u'%.3f %.3f m %s S' % (P[0][0], P[0][1], ' '.join('%.3f %.3f l' % p for p in P[1:])))
            cs.append(u'EMC')
        cs.append(u'Q')
        stream = zlib.compress(u'\n'.join(cs).encode('latin-1'))
        objs = []

        def hexs(t):
            return b'<FEFF' + t.encode('utf-16-be').hex().upper().encode('ascii') + b'>'
        n_oc0 = 5
        ocs = b' '.join(b'%d 0 R' % (n_oc0 + i) for i in range(len(keys)))
        objs.append(b'<< /Type /Catalog /Pages 2 0 R /OCProperties << /OCGs [' + ocs + b'] /D << /Order [' + ocs + b'] /ON [' + ocs + b'] >> >> >>')
        objs.append(b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>')
        props = b' '.join(b'/oc%d %d 0 R' % (i, n_oc0 + i) for i in range(len(keys)))
        objs.append(b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.3f %.3f] /Resources << /Properties << ' % (s.W * k, s.H * k)
                    + props + b' >> >> /Contents 4 0 R >>')
        objs.append(b'<< /Length %d /Filter /FlateDecode >>\nstream\n' % len(stream) + stream + b'\nendstream')
        for key in keys:
            objs.append(b'<< /Type /OCG /Name ' + hexs(key) + b' >>')
        data = b'%PDF-1.5\n%\xe2\xe3\xcf\xd3\n'
        offs = []
        for i, o in enumerate(objs):
            offs.append(len(data))
            data += b'%d 0 obj\n' % (i + 1) + o + b'\nendobj\n'
        xref = len(data)
        data += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1) + b''.join(b'%010d 00000 n \n' % o for o in offs)
        data += b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objs) + 1, xref)
        with open(path, 'wb') as f:
            f.write(data)

    # .ai（Rhino の書き出し）：一時的に 3dm に線を足し、紙の枠ごと選んで書き出し、消す
    def write_ai(s, path):
        ox, oy = AI_ORIGIN
        ids, tops = [], set()

        def P3(p):
            return G.Point3d(ox + p[0], oy + s.H - p[1], 0)
        frame = u'図_%s::紙の枠' % s.name.replace('sodachiya_', '')
        rs.AddLayer(frame)
        ids.append(doc.Objects.AddPolyline([P3(p) for p in ((0, 0), (s.W, 0), (s.W, s.H), (0, s.H), (0, 0))], attr_on(frame)))
        for key, polys in s.groups.items():
            if not polys:
                continue
            rs.AddLayer(key)
            tops.add(key.split('::')[0])
            cls = key.split('::')[2]
            try:
                rs.LayerPrintWidth(key, s.LW.get(cls, VIS_MM))
                if cls == u'想像線':
                    rs.LayerLinetype(key, 'Dashed')
            except Exception:
                pass
            at = attr_on(key)
            for P in polys:
                ids.append(doc.Objects.AddPolyline([P3(p) for p in P], at))
        tops.add(frame.split('::')[0])
        rs.UnselectAllObjects()
        rs.SelectObjects(ids)
        rs.Command(u'_-Export "%s" _Enter _Enter _Enter' % path, False)
        rs.UnselectAllObjects()
        if not KEEP_IN_DOC:
            doc.Objects.Delete(ids, True)
            for t in tops:
                try:
                    rs.PurgeLayer(t)
                except Exception:
                    pass
        doc.Views.Redraw()


def attr_on(layer_path):
    a = Rhino.DocObjects.ObjectAttributes()
    a.LayerIndex = doc.Layers.FindByFullPath(layer_path, -1)
    return a


# ---------------------------------------------------------------- 計算の道具
def view_plane(v):
    """図の面：原点、右、上。局所の座標 (X, Y, Z) の X が図の右、Y が上、Z は見る人の側（見る向きの逆）"""
    if v['kind'] == 'plan':
        return G.Plane(G.Point3d(0, 0, v['cut_z_mm']), G.Vector3d(1, 0, 0), G.Vector3d(0, 1, 0))
    o, r, u = v['origin'], v['right'], v['up']
    return G.Plane(G.Point3d(*o), G.Vector3d(*r), G.Vector3d(*u))


def paper_fn(v):
    """局所の (X, Y) → 紙の mm（左上が原点、下へ y）"""
    if v['kind'] in ('plan', 'roofplan'):                     # 局所の X, Y はモデルの x, y（2 階のずらしは model_to_paper に入っている）
        M = v['model_to_paper']
    else:                                       # 局所の X, Y は (h, z)
        M = v['draw_to_paper']
    a, b, c, d, e, f = M['a'], M['b'], M['c'], M['d'], M['e'], M['f']
    return lambda X, Y: (a * X + b * Y + c, d * X + e * Y + f)


def paper_box_model(v):
    """図の範囲（clip_paper_mm）をモデルの xy に戻した範囲 (x0, y0, x1, y1)。平面・配置図だけ（範囲の外の物を先に除く）"""
    M = v['model_to_paper']
    a, b, c, d, e, f = M['a'], M['b'], M['c'], M['d'], M['e'], M['f']
    det = a * e - b * d
    x0, y0, x1, y1 = v['clip_paper_mm']
    pts = []
    for px, py in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        u, w = px - c, py - f
        pts.append(((e * u - b * w) / det, (a * w - d * u) / det))
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))


def in_box(o, B, pad=0.0):
    return not (o.bmax[0] < B[0] - pad or o.bmin[0] > B[2] + pad or o.bmax[1] < B[1] - pad or o.bmin[1] > B[3] + pad)


def local_xf(pl):
    return G.Transform.PlaneToPlane(pl, G.Plane.WorldXY)


def cut_curves(o, pl):
    """物を面 pl で切った線（モデルの座標の曲線のリスト）"""
    out = []
    try:
        if isinstance(o.geo, G.Brep):
            rc = G.Intersect.Intersection.BrepPlane(o.geo, pl, TOL)
            if rc and rc[0] and rc[1]:
                out += list(rc[1])
        else:
            pls = G.Intersect.Intersection.MeshPlane(o.geo, pl)
            if pls:
                out += [G.PolylineCurve(p) for p in pls]
    except Exception as ex:
        say(u'  切れない', o.leaf, ex)
    return out


def to_local_pts(crv, xf):
    pts = []
    for p in polyline_pts(crv):
        q = G.Point3d(p)
        q.Transform(xf)
        pts.append((q.X, q.Y, q.Z))
    return pts


def local_bbox(objs, xf):
    lo, hi = [1e30] * 3, [-1e30] * 3
    for o in objs:
        b = o.geo.GetBoundingBox(xf)
        for i, (a_, b_) in enumerate(((b.Min.X, b.Max.X), (b.Min.Y, b.Max.Y), (b.Min.Z, b.Max.Z))):
            lo[i] = min(lo[i], a_)
            hi[i] = max(hi[i], b_)
    return lo, hi


def hidden_lines(objs, xf, clip=None):
    """objs を局所の座標（xf）に置き、真上（局所の −Z を見る）から HiddenLineDrawing。
    clip=(z_near, z_far)：局所の z_far < Z < z_near だけ残す（クリッピング平面 2 枚）。
    返り値：[(物, [(X, Y), …])]（局所の X, Y）。
    HiddenLineDrawing の出す 2D の座標は Rhino の内側の決め方なので、物の外に置いた目印の線（局所の X・Y 向き 1 m）を
    いっしょに描いて、その写りから局所の X, Y に戻す。クリッピング平面の向き（どちらの側を消すか）も目印で確かめ、逆なら向きを変えて描き直す"""
    if not objs:
        return []
    lo, hi = local_bbox(objs, xf)
    L = 1000.0
    rx, ry = lo[0] - 3000.0, lo[1] - 3000.0
    rz = (clip[0] - 1.0) if clip else hi[2] + 1000.0
    refx = G.LineCurve(G.Point3d(rx, ry, rz), G.Point3d(rx + L, ry, rz))
    refy = G.LineCurve(G.Point3d(rx, ry, rz), G.Point3d(rx, ry + L, rz))
    lo[0], lo[1] = rx - 1000, ry - 1000
    hi[2] = max(hi[2], rz) + 1000
    for flip in ((1.0, -1.0) if clip else (1.0,)):
        p = G.HiddenLineDrawingParameters()
        p.AbsoluteTolerance = TOL
        p.IncludeTangentEdges = False
        p.IncludeHiddenCurves = False
        vp = Rhino.DocObjects.ViewportInfo()
        vp.ChangeToParallelProjection(True)
        cx, cy = (lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2
        w, h = (hi[0] - lo[0]) * 1.05 + 10, (hi[1] - lo[1]) * 1.05 + 10
        camz = hi[2] + 10000.0
        vp.SetCameraLocation(G.Point3d(cx, cy, camz))
        vp.SetCameraDirection(G.Vector3d(0, 0, -1))
        vp.SetCameraUp(G.Vector3d(0, 1, 0))
        vp.SetFrustum(-w / 2, w / 2, -h / 2, h / 2, 1.0, camz - lo[2] + 10000.0)
        try:
            vp.SetScreenPort(0, 2000, 0, max(1, int(2000 * h / w)), 0, 1)
        except Exception:
            pass
        p.SetViewport(vp)
        if clip:
            # クリッピング平面：法線の側を消す（と見込む。逆なら目印が消えるので flip で描き直す）
            p.AddClippingPlane(G.Plane(G.Point3d(0, 0, clip[0]), G.Vector3d(0, 0, flip)))
            if clip[1] is not None:
                p.AddClippingPlane(G.Plane(G.Point3d(0, 0, clip[1]), G.Vector3d(0, 0, -flip)))
        for i, o in enumerate(objs):
            p.AddGeometry(o.geo, xf, i)
        p.AddGeometry(refx, G.Transform.Identity, 'refx')
        p.AddGeometry(refy, G.Transform.Identity, 'refy')
        res = G.HiddenLineDrawing.Compute(p, MULTI_THREAD)
        if res is None:
            say(u'  HiddenLineDrawing が空')
            return []
        segs, ref = [], {'refx': [], 'refy': []}
        sect = getattr(G.SilhouetteType, 'SectionCut', None)
        for sg in res.Segments:
            if str(sg.SegmentVisibility) != 'Visible' or sg.ParentCurve is None:
                continue
            if sect is not None and sg.ParentCurve.SilhouetteType == sect:
                continue                                    # 切り口は自分で描く（cut_curves）
            tag = sg.ParentCurve.SourceObject.Tag if sg.ParentCurve.SourceObject is not None else None
            crv = sg.CurveGeometry
            if crv is None:
                continue
            if tag in ref:
                ref[tag] += [crv.PointAtStart, crv.PointAtEnd]
                continue
            segs.append((tag, crv))
        if ref['refx'] and ref['refy']:
            break
        say(u'  目印が見えない：クリッピング平面の向きを変えて描き直す')
    else:
        say(u'  ！目印が見えないまま。この図の見えがかりは描かない（クリッピング平面の向きを確かめる）')
        return []
    # 目印の写りから、HiddenLineDrawing の 2D → 局所の X, Y
    X = ref['refx']
    Yp = ref['refy']
    best = min(((a, b) for a in X for b in Yp), key=lambda t: t[0].DistanceTo(t[1]))
    o2 = best[0]
    ex = max(X, key=lambda q: q.DistanceTo(o2))
    ey = max(Yp, key=lambda q: q.DistanceTo(o2))
    ax, ay = ex.X - o2.X, ex.Y - o2.Y
    bx, by = ey.X - o2.X, ey.Y - o2.Y
    det = ax * by - ay * bx
    if abs(det) < 1e-9:
        say(u'  ！目印がつぶれた')
        return []

    def back(q):
        dx, dy = q.X - o2.X, q.Y - o2.Y
        s_ = (dx * by - dy * bx) / det
        t_ = (ax * dy - ay * dx) / det
        return (rx + s_ * L, ry + t_ * L)
    out = []
    for tag, crv in segs:
        if not isinstance(tag, int):
            continue
        out.append((objs[tag], [back(q) for q in polyline_pts(crv)]))
    return out


def outlines(objs, pl_world=None):
    """物をまとめた真上からの外形（メッシュの GetOutlines）→ 折れ線（モデルの座標）のリスト"""
    pl_world = pl_world or G.Plane.WorldXY
    m = G.Mesh()
    for o in objs:
        if isinstance(o.geo, G.Mesh):
            m.Append(o.geo)
        else:
            ms = G.Mesh.CreateFromBrep(o.geo, G.MeshingParameters.FastRenderMesh)
            if ms:
                for x in ms:
                    m.Append(x)
    if m.Faces.Count == 0:
        return []
    try:
        pls = m.GetOutlines(pl_world)
    except Exception as ex:
        say(u'  外形が取れない', ex)
        return []
    out = [[(pl[i].X, pl[i].Y) for i in range(pl.Count)] for pl in (pls or [])]
    if len(out) > 1:
        # 細かく分けた物（西館の棟のガラスの帯など）は片ごとの外形が細い縞になるので、平面の上で一つに足し合わせる（10-31）。
        # 足し合わせられなければ片ごとのまま
        try:
            crvs = [G.PolylineCurve([G.Point3d(x, y, 0) for x, y in (Q + [Q[0]])]) for Q in out if len(Q) >= 3]
            uni = G.Curve.CreateBooleanUnion(crvs, 1.0)
            if uni and len(uni) > 0:
                res = []
                for c in uni:
                    ok, pl = c.TryGetPolyline()
                    if not ok:
                        pl = c.ToPolyline(0, 0, 0.05, 0, 0, 1.0, 0, 0, True).ToPolyline()
                    res.append([(pl[i].X, pl[i].Y) for i in range(pl.Count)])
                return res
        except Exception as ex:
            say(u'  外形を一つにできない（片ごとのまま）', ex)
    return out


# ---------------------------------------------------------------- 平面
def draw_plan(sheet, v, OBJS):
    R = v['rules']
    cut, lv = float(v['cut_z_mm']), float(v['level_z_mm'])
    is2 = lv > 1000
    up_dash, light, room, roof, tree = (re.compile(R[k]) for k in ('up_dash_re', 'up_light_re', 'room_re', 'roof_re', 'tree_re'))
    beam = tuple(R['beam_prefix'])
    fit = tuple(R['fitting_prefix'])
    glass_w = R['glass_words']

    def is_glass_or_fit(o):
        return (any(w in o.leaf for w in glass_w) and u'ルーバー' not in o.leaf) or o.leaf.startswith(fit)
    sel = []
    if is2:
        x0, y0, x1, y1 = v['select_xy_mm']
        play = outlines([o for o in OBJS if o.leaf.startswith('31_')])
        play_c = [G.PolylineCurve([G.Point3d(p[0], p[1], 0) for p in P]) for P in play if len(P) > 3]

        def in_play(o):
            c = G.Point3d((o.bmin[0] + o.bmax[0]) / 2, (o.bmin[1] + o.bmax[1]) / 2, 0)
            return any(pc.IsClosed and str(pc.Contains(c, G.Plane.WorldXY, 1.0)) == 'Inside' for pc in play_c)
        for o in OBJS:
            n = o.n
            if o.leaf.startswith('47') or n in (90, 94, 98) or (n < 20 and not o.leaf.startswith('19d')) or n in (50, 51) \
                    or 60 <= n < 80 or 89 < n < 100:
                continue
            if not (n == 21 or (o.bmin[0] > x0 and o.bmin[1] > y0 and o.bmax[0] < x1 and o.bmax[1] < y1)):
                continue
            upper = o.bmax[2] > 3000 or n in (21, 22, 25)
            if not upper and not in_play(o):
                continue
            sel.append(o)
        roofs = [o for o in OBJS if o.n == 20 and roof.match(o.leaf)]
    else:
        for o in OBJS:
            if o.leaf.startswith('47') or o.n in PLAN_SKIP or o.n in PLAN1_SKIP:
                continue
            sel.append(o)
        roofs = [o for o in OBJS if roof.match(o.leaf)]
    sel = [o for o in sel if not room.match(o.leaf)]
    dash, below, cutting = [], [], []
    for o in sel:
        zmin, zmax = o.bmin[2], o.bmax[2]
        if light.match(o.leaf) and zmin >= cut:
            dash.append(o)                                 # 光の筋（想像線）
            continue
        if o.n in (10, 20) and not (o.leaf.startswith('10s_') and zmin < lv + 100):
            continue                                       # 屋根（10・20 の層すべて）は外形だけ（下の roofs）。南の軒の柱（10s、床から）は切る
        if zmin >= cut:
            if up_dash.match(o.leaf) or (is_glass_or_fit(o) and zmin < lv + R['high_window_below_mm']):
                dash.append(o)                             # 越屋根・2階の床の縁・遊具・天袋・高窓
            continue
        if tree.match(o.leaf) and zmax > cut:
            dash.append(o)                                 # 樹冠（想像線）。幹は下の見えがかりにも
        if o.leaf.split('_')[0] in beam:
            continue
        below.append(o)
        if zmax > cut:
            cutting.append(o)
    pl = view_plane(v)
    xf = local_xf(pl)
    P = paper_fn(v)
    clip = v['clip_paper_mm']
    nm = v['name']
    say(u'%s：切る %d・下に見える %d・想像線 %d' % (nm, len(cutting), len(below), len(dash)))
    for o in cutting:
        for c in cut_curves(o, pl):
            sheet.add(nm, u'切断', o.leaf, [[P(q[0], q[1]) for q in to_local_pts(c, xf)]], clip)
    for o, pts in hidden_lines(below, xf, clip=(0.0, None)):
        sheet.add(nm, u'見えがかり', o.leaf, [[P(*q) for q in pts]], clip)
    # 想像線：屋根はまとめた外形、ほかはレイヤーごと（樹冠・高窓は一つずつ）
    for Q in outlines(roofs):
        sheet.add(nm, u'想像線', u'屋根の外形（10・20）', [[P(*q) for q in Q]], clip)
    byl = {}
    for o in dash:
        key = o.leaf if not (tree.match(o.leaf) or is_glass_or_fit(o)) else (o.leaf, str(o.id))
        byl.setdefault(key, []).append(o)
    for key, L in byl.items():
        leaf = key if isinstance(key, str) else key[0]
        for Q in outlines(L):
            sheet.add(nm, u'想像線', leaf, [[P(*q) for q in Q]], clip)
    if not is2:
        for c in site_curves():
            sheet.add(nm, u'敷地の境', u'00_敷地', [[P(p.X, p.Y) for p in polyline_pts(c)]], clip)
    draw_context(sheet, v, OBJS)
    if v.get('below_top'):
        draw_below_top(sheet, v, OBJS, set(str(o.id) for o in sel))


# ---------------------------------------------------------------- 周り（3・4枚目の平面、配置図。項 20261030-2258-present）
def draw_context(sheet, v, OBJS):
    """周り：context_re の物（PLATEAU の道・建物）を一つずつ真上からの外形で、context_curves_re の曲線（公園・駐車場）も。
    組「周り」（細い見えがかり）。json に context_re が無い図（今の平面図など）は何もしない"""
    if not v.get('context_re'):
        return
    cre = re.compile(v['context_re'])
    skip = re.compile(v['context_skip_re']) if v.get('context_skip_re') else None
    P = paper_fn(v)
    clip = v['clip_paper_mm']
    nm = v['name']
    B = paper_box_model(v)
    L = [o for o in OBJS if cre.match(o.leaf) and not (skip and skip.match(o.leaf)) and in_box(o, B)]
    say(u'%s：周り %d' % (nm, len(L)))
    for o in L:
        for Q in outlines([o]):
            sheet.add(nm, u'周り', o.leaf, [[P(*q) for q in Q]], clip)
    if v.get('context_curves_re'):
        for c in site_curves(v['context_curves_re']):
            sheet.add(nm, u'周り', u'01_公園・駐車場', [[P(p.X, p.Y) for p in polyline_pts(c)]], clip)


def draw_below_top(sheet, v, OBJS, skip_ids):
    """2 階の紙：西館の外の物（below_top.layers_re、2 階に描いた物を除く）を切らずに真上から見た見えがかり（本館の屋根・太陽光・
    光の筋・越屋根、園庭、高野川の側）。HiddenLineDrawing（クリッピング平面なし）で隠れ線を消す。西館の外壁（mask_re）の
    真上からの外形の内は消す（2 階の図がある所）。敷地の境も"""
    Bt = v['below_top']
    tre, mre = re.compile(Bt['layers_re']), re.compile(Bt['mask_re'])
    room = re.compile(v['rules']['room_re'])
    P = paper_fn(v)
    clip = v['clip_paper_mm']
    nm = v['name']
    B = paper_box_model(v)
    sel = [o for o in OBJS if tre.match(o.leaf) and str(o.id) not in skip_ids and not room.match(o.leaf)
           and not o.leaf.startswith('47') and in_box(o, B)]
    rings = [[P(*q) for q in Q] for Q in outlines([o for o in OBJS if mre.match(o.leaf)]) if len(Q) > 3]
    say(u'%s：下に見える（真上から）%d・消す外形 %d' % (nm, len(sel), len(rings)))
    for o, pts in hidden_lines(sel, G.Transform.Identity, clip=None):
        sheet.add(nm, u'見えがかり', o.leaf, mask_out([P(*q) for q in pts], rings), clip)
    for c in site_curves():
        sheet.add(nm, u'敷地の境', u'00_敷地', mask_out([P(p.X, p.Y) for p in polyline_pts(c)], rings), clip)


# ---------------------------------------------------------------- 配置図（真上から、1/200。項 20261030-0750-present）
def draw_roofplan(sheet, v, OBJS):
    """配置図の線：layers_re の物（屋根・越屋根・光の筋・太陽光・外構・園庭の物・樹冠・高野川の側）を真上から見た見えがかり
    （切らない、隠れ線を消す）。周り（PLATEAU）は外形、敷地の境は外の一本。紙・位置・向き・縮尺は draw100 の _xform.json と同じ"""
    tre = re.compile(v['layers_re'])
    room = re.compile(v.get('room_re') or r'^(3[1-4]|36|4[1-5]|5[2-47]|59)[a-z]?_')
    P = paper_fn(v)
    clip = v['clip_paper_mm']
    nm = v['name']
    B = paper_box_model(v)
    sel = [o for o in OBJS if tre.match(o.leaf) and not room.match(o.leaf) and not o.leaf.startswith('47') and in_box(o, B)]
    say(u'%s：真上から %d' % (nm, len(sel)))
    for o, pts in hidden_lines(sel, G.Transform.Identity, clip=None):
        sheet.add(nm, u'見えがかり', o.leaf, [[P(*q) for q in pts]], clip)
    draw_context(sheet, v, OBJS)
    for c in (site_outer() if v.get('site_outer_only') else site_curves()):
        sheet.add(nm, u'敷地の境', u'00_敷地', [[P(p.X, p.Y) for p in polyline_pts(c)]], clip)


# ---------------------------------------------------------------- 断面
def draw_section(sheet, v, OBJS):
    pl = view_plane(v)
    xf = local_xf(pl)
    P = paper_fn(v)
    clip = v['clip_paper_mm']
    nm = v['name']
    depth = float(v['depth_mm'])
    skip_re = re.compile(v['skip_layers_re']) if v.get('skip_layers_re') else None     # 断面 D：読書の庭の木（67c、draw100 と同じ）
    sel = []
    for o in OBJS:
        if o.leaf.startswith('47') or o.n in SEC_SKIP:
            continue
        if skip_re and skip_re.match(o.leaf):
            continue
        b = o.geo.GetBoundingBox(xf)
        if b.Max.Z < -depth or b.Min.Z > 0:
            continue                                       # 切断面より手前、または奥の限りより奥
        sel.append((o, b))
    cutting = [o for o, b in sel if b.Min.Z < 0 < b.Max.Z]
    vis = [o for o, b in sel if o.n not in SEC_NOVIS]
    say(u'%s：切る %d・奥に見える %d' % (nm, len(cutting), len(vis)))
    for o in cutting:
        for c in cut_curves(o, pl):
            sheet.add(nm, u'切断', o.leaf, [[P(q[0], q[1]) for q in to_local_pts(c, xf)]], clip)
    for o, pts in hidden_lines(vis, xf, clip=(0.0, -depth)):
        sheet.add(nm, u'見えがかり', o.leaf, [[P(*q) for q in pts]], clip)


# ---------------------------------------------------------------- 断面 A（円筒 r=Rc で切って平らに伸ばす）
# やり方（10-28、項 20261028-1801-present）：物をメッシュにして、頂点を一つずつ展開の座標 (h, z, Rc − r) に移す（arc_unroll_fn）。
#   展開した空間では、円筒 r=Rc は平面 Z=0 になり、西（r の大きい方）を見ることは −Z を見ることになる。なので断面 B・C と
#   同じ道具（MeshPlane で切り口、クリッピング平面つきの HiddenLineDrawing で見えがかり）がそのまま使える。
#   draw100.py の section_arc も三角形の頂点を同じ式で (h, z) に移して切り口・見えがかりを描いているので、紙の上の置き場所は
#   draw100 と同じになる（クラウドで 3dm のメッシュを同じ式で切り、今の断面 A の切り口と重なるのを確かめた）。
# 採らなかった案：スパンごとに半径の向きに平行投影して継ぐ。奥の物ほど横にずれ（30 m 奥で 1.15 倍）、スパンの継ぎ目で
#   線が食い違う（draw100 は角度で写すので、奥の物は弧の中心へ向けて縮む）。円筒の Brep との BrepBrep も、切り口は正しいが
#   見えがかりが出せないので、切り口と見えがかりを同じ展開のメッシュから出す方にそろえた。
# Brep は面ごとのメッシュを溶接せずに一つにまとめる：面の境が裸の辺になり、HiddenLineDrawing が稜線として描く。
#   辺は ARC_MAX_EDGE まで（真っすぐな辺は展開で少し曲がるので。1 m で紙の上 0.01 mm 未満）。
def arc_unroll_fn(v):
    """断面 A の展開の式（Rhino 無しでも使える）。v は _views.json の断面 A。
    返り値 F(x, y, z) → (h, z, Rc − r)：h = sign·(θ − theta0)·Rc（θ は中心 C からの角度を [0, 2π) に。draw100 の unwrap と同じ）。
    紙へは draw_to_paper（x = a·h + c、y = e·z + f）"""
    cx, cy = float(v['center_xy_mm'][0]), float(v['center_xy_mm'][1])
    Rc, th0, sg = float(v['radius_mm']), float(v['theta0_rad']), float(v['sign'])
    two = 2.0 * math.pi

    def F(x, y, z):
        dx, dy = x - cx, y - cy
        th = math.atan2(dy, dx) % two
        return (sg * (th - th0) * Rc, z, Rc - math.hypot(dx, dy))
    return F


class _Unrolled(object):
    """展開したメッシュ（Obj の代わりに cut_curves・hidden_lines に渡す）"""
    def __init__(s, geo, src):
        s.geo, s.leaf, s.n, s.full, s.id = geo, src.leaf, src.n, src.full, src.id


def unroll_mesh(o, F, mp, flip):
    if isinstance(o.geo, G.Mesh):
        parts = [o.geo]
    else:
        parts = G.Mesh.CreateFromBrep(o.geo, mp) or []
    m = G.Mesh()
    for q in parts:
        m.Append(q)                                        # 溶接しない（面の境＝稜線を残す）
    V = m.Vertices
    if V.Count == 0 or m.Faces.Count == 0:
        return None
    for i in range(V.Count):
        p = V[i]
        h, z, d = F(p.X, p.Y, p.Z)
        V.SetVertex(i, h, z, d)
    if flip:
        m.Flip(True, True, True)
    m.Normals.ComputeNormals()
    m.FaceNormals.ComputeFaceNormals()
    return m


def draw_section_arc(sheet, v, OBJS):
    F = arc_unroll_fn(v)
    cx, cy = float(v['center_xy_mm'][0]), float(v['center_xy_mm'][1])
    Rc, depth = float(v['radius_mm']), float(v['depth_mm'])
    P = paper_fn(v)
    M = v['draw_to_paper']
    clip = list(v['clip_paper_mm'])
    if v.get('xcut_h_mm') is not None:                     # 南は敷地の境で止める（draw100 と同じ。破断線・「敷地の境」は _文字.pdf に）
        xc = M['a'] * float(v['xcut_h_mm']) + M['c']
        if M['a'] > 0:
            clip[0] = max(clip[0], xc)
        else:
            clip[2] = min(clip[2], xc)
    h_a, h_b = sorted(((clip[0] - M['c']) / M['a'], (clip[2] - M['c']) / M['a']))
    flip = float(v['sign']) > 0                            # 展開で向きが裏返るとき（sign = +1）は面の向きを戻す
    mp = G.MeshingParameters()
    mp.MaximumEdgeLength = ARC_MAX_EDGE
    mp.Tolerance = ARC_MESH_TOL
    mp.SimplePlanes = False
    mp.RefineGrid = True
    mp.JaggedSeams = False
    nm = v['name']
    cutting, vis = [], []
    for o in OBJS:                                         # draw100 の section_arc と同じ「描かない物」（SEC_SKIP に護岸 2 も入っている）
        if o.leaf.startswith('47') or o.n in SEC_SKIP:
            continue
        (x0, y0, _), (x1, y1, _) = o.bmin, o.bmax
        if x1 > cx - 1000.0:
            continue                                       # 中心 C の東（角度の継ぎ目の側。建物は C の西）
        rmin = math.hypot(min(max(cx, x0), x1) - cx, min(max(cy, y0), y1) - cy)
        rmax = max(math.hypot(x_ - cx, y_ - cy) for x_ in (x0, x1) for y_ in (y0, y1))
        if rmax < Rc or rmin > Rc + depth:
            continue
        m = unroll_mesh(o, F, mp, flip)
        if m is None:
            continue
        b = m.GetBoundingBox(True)
        if b.Max.X < h_a or b.Min.X > h_b or b.Min.Z > 0 or b.Max.Z < -depth:
            continue                                       # 図の外、円筒より内（Z > 0）、奥の限りより奥
        u = _Unrolled(m, o)
        if b.Min.Z < 0 < b.Max.Z:
            cutting.append(u)
        if o.n not in SEC_NOVIS:
            vis.append(u)
    say(u'%s：切る %d・奥に見える %d（展開した空間で）' % (nm, len(cutting), len(vis)))
    I = G.Transform.Identity
    for u in cutting:
        for c in cut_curves(u, G.Plane.WorldXY):
            sheet.add(nm, u'切断', u.leaf, [[P(q[0], q[1]) for q in to_local_pts(c, I)]], clip)
    for u, pts in hidden_lines(vis, I, clip=(0.0, None)):  # 奥の限りは物の選び方だけ（draw100 も奥の面では切らない）
        sheet.add(nm, u'見えがかり', u.leaf, [[P(*q) for q in pts]], clip)


# ---------------------------------------------------------------- 立面
def draw_elevation(sheet, v, OBJS, room_re):
    pl = view_plane(v)
    xf = local_xf(pl)
    P = paper_fn(v)
    clip = v['clip_paper_mm']
    nm = v['name']
    sel = []
    for o in OBJS:                                         # draw100 の elev_objs と同じ：建物（05〜69 と 89）だけ
        n = o.n
        if not (5 <= n <= 69 or n == 89):
            continue
        if o.leaf.startswith('47') or n in (62, 63, 64, 55) or u'外構' in o.leaf or room_re.match(o.leaf):
            continue
        if (80 <= n <= 88) or n in (37, 39, 40, 46, 51, 75) or u'しつらえ' in o.leaf:
            continue                                       # 室内の家具
        if o.bmax[2] - o.bmin[2] < 60 and o.bmax[2] < -200:
            continue                                       # 地面に張り付いた板
        sel.append(o)
    say(u'%s：%d' % (nm, len(sel)))
    for o, pts in hidden_lines(sel, xf, clip=None):
        sheet.add(nm, u'見えがかり', o.leaf, [[P(*q) for q in pts]], clip)


# ---------------------------------------------------------------- 本体
def main():
    if not doc.Path:
        say(u'3dm を保存してから（sodachiya/sodachiya.3dm を開いて）走らせてください')
        return
    # drawings/ を探す：3dm の隣 → このスクリプトの隣（rhino/ の上）→ 選んでもらう
    # （10-28：3dm をダウンロードのフォルダから開くと、隣に drawings/ が無くて止まっていた）
    try:
        here = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        here = ''
    cands = [os.path.dirname(doc.Path)]
    if here: cands.append(os.path.dirname(here))
    root = next((c for c in cands if glob.glob(os.path.join(c, 'drawings', '*_views.json'))), None)
    if root is None:
        say(u'drawings/*_views.json が見つからない（3dm の隣・スクリプトの上のフォルダ）。リポジトリの sodachiya フォルダを選んでください')
        pick = rs.BrowseForFolder(message=u'atelier/sodachiya フォルダ（drawings/ がある所）を選ぶ')
        if pick and glob.glob(os.path.join(pick, 'drawings', '*_views.json')):
            root = pick
        elif pick and glob.glob(os.path.join(pick, '*_views.json')):
            root = os.path.dirname(pick)                 # drawings/ そのものを選んだとき
        else:
            say(u'drawings/*_views.json が無い（git pull してから。作り直しに入る前なら、入ってから）')
            return
    say(u'読む：', os.path.join(root, 'drawings'))
    dd = os.path.join(root, 'drawings')
    js = sorted(glob.glob(os.path.join(dd, '*_views.json')))
    outd = os.path.join(root, 'drawings_rhino')
    if not os.path.isdir(outd):
        os.makedirs(outd)
    OBJS = load_objects()
    room_re = re.compile(r'^(3[1-4]|36|4[1-5]|5[2-47]|59)[a-z]?_')     # 平面の json の決まりがあればそれ（下）
    for jp in js:
        for v in json.load(open(jp, encoding='utf-8'))['views']:
            if v['kind'] == 'plan':
                room_re = re.compile(v['rules']['room_re'])
    for jp in js:
        J = json.load(open(jp, encoding='utf-8'))
        name = os.path.basename(jp)[:-len('_views.json')]
        sh = Sheet(name, J)
        for v in J['views']:
            if ONLY and ONLY not in v['name']:
                continue
            say(u'== %s / %s' % (name, v['name']))
            try:
                if v['kind'] == 'plan':
                    draw_plan(sh, v, OBJS)
                elif v['kind'] == 'section':
                    draw_section(sh, v, OBJS)
                elif v['kind'] == 'elevation':
                    draw_elevation(sh, v, OBJS, room_re)
                elif v['kind'] == 'section_arc':
                    draw_section_arc(sh, v, OBJS)
                elif v['kind'] == 'roofplan':
                    draw_roofplan(sh, v, OBJS)
                else:
                    say(u'  %s（%s）は Rhino では描かない' % (v['name'], v['kind']))
            except Exception as ex:
                import traceback
                say(u'  ！止まった：', ex)
                traceback.print_exc()
        if not any(sh.groups.values()):
            continue
        base = os.path.join(outd, name)
        sh.write_svg(base + '.svg')
        sh.write_pdf(base + '.pdf')
        say(u'書いた', base + '.svg・.pdf', u'線の組', len(sh.groups))
        if EXPORT_AI:
            try:
                sh.write_ai(base + '.ai')
                say(u'書いた', base + '.ai')
            except Exception as ex:
                say(u'  .ai は書けなかった（SVG を Illustrator で開いてください）：', ex)
    say(u'おわり。drawings_rhino/ の図に drawings/…_文字.pdf を重ねる')


if __name__ == '__main__':
    main()
