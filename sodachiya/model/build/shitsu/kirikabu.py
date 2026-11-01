"""木の切り株（本館係、11-01。ユーザー：教室に切り株を転がす、2歳に2つ・3〜5歳に4つずつ。腰掛け・台・積む遊びの素材）。
園庭の切り株と同じ寸法の決まり（径0.25〜0.6・高さ0.2〜0.45）で、園庭・遊戯室からも使えるように一つの関数に。
  幹と根張り：r–z の断面（足もとで根張りに広がり、上へ少し細る幹の輪郭、上の縁は丸めて樹皮の輪を少し立てる）を
            軸まわりに一周した閉じた回転体（一枚の面の Brep、断面の両端が軸の上なので継ぎ目の蓋が無い）。素材は樹皮。
  根の張り出し：足もとに小さなくさび（輪郭をまっすぐ押し出した物）を3〜5本。先は丸めずに低く切る（高さ12、尖らせない）。樹皮。
  木口：上の切り口に厚さ5の円板（樹皮の輪の内側、輪より1 mm 内）。素材は木口（年輪）。
傾け・横倒し（「転がす」）は軸の向きで作る（形はそのまま、床に一番低い所が載る）。
座標は mm。使い方：
  bark, kiguchi = kirikabu((x, y, z0), d, h, flare=0.22, roots=4, rot=0, tilt=0, tilt_dir=0)
  K.add(m, bark, L_BARK); K.add(m, kiguchi, L_KIGUCHI)
"""
import math, numpy as np, rhino3dm as r
import katachi as K


def _u(v):
    v = np.asarray(v, float); return v / np.linalg.norm(v)


def profile(d, h, flare=0.22, n=14):
    """r–z の断面（軸の足もと (0,0) から外へ、上へ、木口の円板の下 (0, h−5) まで）と、木口の円板の半径"""
    rt = d / 2.0
    rad = lambda z: rt * (1.0 + 0.03 * (1 - z / h) + flare * math.exp(-z / (0.18 * h)))
    zt = h - 12.0
    pts = [(0.0, 0.0)] + [(rad(zt * (i / n) ** 1.6), zt * (i / n) ** 1.6) for i in range(n + 1)]
    r1 = rad(zt)
    rin = r1 - 15.0                                                 # 樹皮の輪の内側（厚さ約14）
    pts += [(r1 - 3.0, h - 3.0), (r1 - 8.0, h), (rin + 1.0, h), (rin + 1.0, h - 5.0), (0.0, h - 5.0)]
    return pts, rin, rad(0.0)


def frame(tilt, tilt_dir):
    """軸の向き a と、それに直角な e1・e2（tilt：鉛直からの傾き 度、tilt_dir：傾ける向き 度、世界の x から反時計回り）"""
    t, p = math.radians(tilt), math.radians(tilt_dir)
    a = np.array([math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t)])
    e1 = np.array([math.cos(t) * math.cos(p), math.cos(t) * math.sin(p), -math.sin(t)])    # 傾ける向きの側（下りの側）
    e2 = np.cross(a, e1)
    return a, e1, e2


def lying_tilt(d, h, flare=0.22):
    """横倒し：足もとの根張りの縁と上の縁が両方床に着く傾き（度、90 より少し大きい）"""
    pts, rin, rb = profile(d, h, flare)
    rtop = max(p[0] for p in pts if p[1] > h - 20)
    return 180.0 - math.degrees(math.atan2(h, rb - rtop))


def kirikabu(c, d, h, flare=0.22, roots=4, rot=0.0, tilt=0.0, tilt_dir=0.0, root_len=0.25, root_h=0.3, skip_down=0.0):
    """c=(x, y, z0) 床の上の点、d 幹の径・h 高さ（mm）。→ (樹皮の物の並び, 木口の円板)。
    roots 根の数、rot 根の向きの回し（度）、root_len 根の出（幹の半径に対して）、root_h 根の高さ（高さに対して）。
    skip_down：横倒しのとき、下になる向きから ±skip_down 度の根は作らない（床に食い込まない）"""
    pts, rin, rb = profile(d, h, flare)
    a, e1, e2 = frame(tilt, tilt_dir)
    # 床に一番低い所を載せる：断面の点を一周させて一番低い z を探す
    zs = []
    for ang in np.linspace(0, 2 * math.pi, 73):
        rd = math.cos(ang) * e1 + math.sin(ang) * e2
        zs += [z * a[2] + rr * rd[2] for rr, z in pts]
    O = np.array([c[0], c[1], c[2] - min(zs)])
    P3 = lambda rr, z, rd=e1: O + z * a + rr * rd
    pl = r.Polyline(0)
    for rr, z in pts:
        q = P3(rr, z); pl.Add(*map(float, q))
    ax = r.Line(r.Point3d(*map(float, O - 1000 * a)), r.Point3d(*map(float, O + 2000 * a)))
    b = r.Brep.CreateFromRevSurface(r.RevSurface.Create(r.PolylineCurve(pl), ax, 0.0, 2 * math.pi), False, False)
    if b is None or not b.IsSolid: raise ValueError('切り株の回転体が閉じない')
    bark = [b]
    rt = d / 2.0; L = root_len * rt; hr = root_h * h; w = max(40.0, 0.22 * d)
    r0 = rb * 0.82                                                  # 根の付け根は根張りの中（重なりは小さく、食い込みの数に入らない）
    for k in range(roots):
        ang = math.radians(rot + 360.0 * k / roots + (17.0 if k % 2 else 0.0))
        if skip_down and abs((math.degrees(ang) + 180) % 360 - 180) < skip_down: continue
        rd = math.cos(ang) * e1 + math.sin(ang) * e2
        nrm = np.cross(rd, a)                                       # 押し出しの向き（X×Y）
        prof = [(r0, 0.0), (rb + L, 0.0), (rb + L, 12.0), (r0, hr)]
        bark.append(K.oshidashi(prof, (), O - nrm * w / 2, rd, a, w))
    kiguchi = K.enchu(O + (h - 5.0) * a, O + h * a, rin)
    return bark, kiguchi
