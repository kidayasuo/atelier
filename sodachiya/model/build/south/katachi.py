"""形の小さな道具（効率化委員会、10-31。ユーザー：新しい部材が毎回、三角形の網や妙に分かれた片になる）。
板・梁・柱・壁・ガラスの帯・家具の箱は、ここの関数で rhino3dm.Extrusion（押し出し）として作る。
押し出しはメッシュの版にそのまま入り、段10（clean_wire.py）は手を付けずに Rhino 版へ写す（kept）。
だから Rhino 版でかならず押し出し（直方体は 6 面）になる。決まりの元は kettei/kanshu.md の点検の7（形が素直）。
座標は mm、(u, v) は本館の座標 m（uv.py）。三角形の網で作ってよいのは、決めた自由な形（クスノキ・地形・丘・水・雨の川）だけ。

使い方：
  import katachi as K
  K.add(m, K.hako_xyz(x0, x1, y0, y1, z0, z1), li)          直方体（世界の軸にそろう）
  K.add(m, K.hako(o, X, Y, sx, sy, sz), li, name='棚')       向きのある直方体（o の角から X・Y・X×Y の向きに）
  K.add(m, K.hako_uv(u0, u1, v0, v1, z0, z1), li)           (u, v) の四隅の板（端は放射の線、辺はまっすぐ）
  K.add(m, K.ougi(u0, u1, v0, v1, z0, z1), li)              (u, v) の板で、v の辺を本館の弧に沿う円弧に
  K.add(m, K.bou(p0, p1, b, h), li)                         梁・母屋・柱（p0→p1 の軸、断面 b×h の長方形、h は上向き）
  K.add(m, K.ita(poly, z0, z1), li)                         平面形（shapely、穴あり可）を z0〜z1 に（Kit.prism の高さ一定の代わり）
  K.add(m, K.oshidashi(outer, holes, O, X, Y, h), li)       平らな輪郭（O・X・Y の面の 2 次元の点）を面に直角に h だけ
  K.add(m, K.enchu(p0, p1, rad), li)                        円柱（管は rin を付ける）
  K.add(m, K.enko(c, r0, r1, a0, a1, z0, z1), li)           円弧の帯（中心 c、半径 r0〜r1、角度 a0〜a1 度）を z0〜z1 に
  K.add(m, K.tama(c, rx, ry, rz, rot), li)                  楕円体（玉石など。中心 c、半径 rx・ry・rz、z まわりに rot 度、一枚の閉じた面の Brep）
  メッシュが要る段（頂点を動かす・manifold で削る）には K.mesh(g)（閉じた網。段10で同じ押し出しに戻る）。
作れないとき（輪郭が閉じない・長さ 0）は ValueError。黙って網にしない。
"""
import math, numpy as np, rhino3dm as r
from uv import xy, CX, CY, RW, TH_S

_P = lambda p: r.Point3d(float(p[0]), float(p[1]), float(p[2]))
_V = lambda p: r.Vector3d(float(p[0]), float(p[1]), float(p[2]))


def _unit(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    if n < 1e-9: raise ValueError('長さ 0 の向き')
    return v / n


def _ring2(P):
    """2 次元の点の並び→閉じた折れ線（z = 0）。一直線にのる途中の点は除く"""
    P = [tuple(map(float, p[:2])) for p in P]
    if len(P) > 1 and math.dist(P[0], P[-1]) < 1e-6: P = P[:-1]
    Q = []
    n = len(P)
    for i in range(n):
        a, b, c = np.array(P[i - 1]), np.array(P[i]), np.array(P[(i + 1) % n])
        u_, w_ = b - a, c - b
        if abs(u_[0] * w_[1] - u_[1] * w_[0]) > 1e-6 * max(1.0, np.linalg.norm(u_) * np.linalg.norm(w_)): Q.append(P[i])
    if len(Q) < 3: raise ValueError('輪郭の点が足りない')
    return r.Polyline([r.Point3d(x, y, 0.0) for x, y in Q + Q[:1]]).ToNurbsCurve()


def _make(curves2d, O, X, Y, h):
    """2 次元の輪郭（外・穴）を、面 (O, X, Y) から Z = X×Y の向きに h だけ押し出す（ON_Extrusion：輪郭の x は X、y は Y）"""
    O = np.asarray(O, float); X = _unit(X); Y = np.asarray(Y, float); Y = _unit(Y - (Y @ X) * X)
    if h < 0: Y = -Y; h = -h; curves2d = [_mirror_y(c) for c in curves2d]
    if h < 1e-6: raise ValueError('押し出しの長さ 0')
    Z = np.cross(X, Y)
    e = r.Extrusion()
    if not e.SetPathAndUp(_P(O), _P(O + h * Z), _V(Y)): raise ValueError('道を作れない')
    outer, holes = curves2d[0], curves2d[1:]
    if not outer.IsClosed: raise ValueError('外の輪郭が閉じていない')
    if not e.SetOuterProfile(outer, True): raise ValueError('外の輪郭を入れられない')
    for c in holes:
        if not e.AddInnerProfile(c): raise ValueError('穴の輪郭を入れられない')
    if not e.IsValid: raise ValueError('押し出しが正しくない')
    return e


def _mirror_y(c):
    c = c.ToNurbsCurve() if not isinstance(c, r.NurbsCurve) else c.Duplicate()
    xf = r.Transform(1.0); xf.M11 = -1.0
    c.Transform(xf); return c


def oshidashi(outer, holes=(), O=(0, 0, 0), X=(1, 0, 0), Y=(0, 1, 0), h=1.0):
    """平らな輪郭の押し出し。outer・holes は面 (O, X, Y) の 2 次元の点の並び（または z = 0 の rhino3dm の閉じた曲線）。
    押し出す向きは X×Y（h が負なら逆）。斜めに押し出したい物は、輪郭を道に直角な面で描く"""
    cv = [c if isinstance(c, r.Curve) else _ring2(c) for c in [outer, *holes]]
    return _make(cv, O, X, Y, h)


def hako(o, X, Y, sx, sy, sz):
    """直方体：角 o から X の向きに sx、Y の向きに sy、X×Y の向きに sz（Y は X に直角に直す）"""
    return _make([_ring2([(0, 0), (sx, 0), (sx, sy), (0, sy)])], o, X, Y, sz)


def hako_xyz(x0, x1, y0, y1, z0, z1):
    """世界の軸にそろう直方体"""
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1)); z0, z1 = sorted((z0, z1))
    return hako((x0, y0, z0), (1, 0, 0), (0, 1, 0), x1 - x0, y1 - y0, z1 - z0)


def _flat(P2, z0, z1):
    """世界の平面の点（x, y）の輪郭を z0〜z1 に"""
    P2 = np.asarray(P2, float); c = P2.mean(0)
    return oshidashi(P2 - c, (), (c[0], c[1], min(z0, z1)), (1, 0, 0), (0, 1, 0), abs(z1 - z0))


def hako_uv(u0, u1, v0, v1, z0, z1):
    """(u, v) の四隅の板・箱（u の端は放射の線、v の辺はまっすぐの弦）。u の幅が数 m を超えるなら ougi を使う"""
    return _flat([xy(u0, v0), xy(u1, v0), xy(u1, v1), xy(u0, v1)], z0, z1)


def ougi(u0, u1, v0, v1, z0, z1):
    """(u, v) の板で、v の辺を本館の弧（中心 CX・CY）に沿う円弧に、u の端を放射の線に"""
    def th(u): return TH_S - u * 1000 / RW
    c = np.array([CX, CY]); ra, rb = sorted((RW - v0 * 1000, RW - v1 * 1000))
    return enko((c[0], c[1]), ra, rb, math.degrees(min(th(u0), th(u1))), math.degrees(max(th(u0), th(u1))), z0, z1)


def enko(c, r0, r1, a0, a1, z0, z1):
    """円弧の帯：中心 c (x, y)、半径 r0〜r1（r0 = 0 なら扇）、角度 a0〜a1（度、反時計回り）を z0〜z1 に"""
    r0, r1 = sorted((float(r0), float(r1))); t0, t1 = math.radians(a0), math.radians(a1)
    if t1 <= t0: raise ValueError('角度の向き')
    tm = (t0 + t1) / 2; rm = (r0 + r1) / 2
    O = np.array([c[0] + rm * math.cos(tm), c[1] + rm * math.sin(tm)])          # 輪郭の座標の原点は帯の中ほど（大きな数を避ける）
    q = lambda rr, t: r.Point3d(c[0] + rr * math.cos(t) - O[0], c[1] + rr * math.sin(t) - O[1], 0.0)
    pc = r.PolyCurve()
    pc.Append(r.Arc(q(r1, t0), q(r1, tm), q(r1, t1)))
    if r0 > 1e-6:
        pc.Append(r.Line(q(r1, t1), q(r0, t1)))
        pc.Append(r.Arc(q(r0, t1), q(r0, tm), q(r0, t0)))
        pc.Append(r.Line(q(r0, t0), q(r1, t0)))
    else:
        cc = r.Point3d(c[0] - O[0], c[1] - O[1], 0.0)
        pc.Append(r.Line(q(r1, t1), cc)); pc.Append(r.Line(cc, q(r1, t0)))
    return _make([pc], (O[0], O[1], min(z0, z1)), (1, 0, 0), (0, 1, 0), abs(z1 - z0))


def bou(p0, p1, b, h, up=(0, 0, 1)):
    """梁・母屋・柱：軸 p0→p1、断面は幅 b（横）×高さ h（up の向き）の長方形で、軸が断面の中心。
    柱（軸が鉛直）は up を (0, 1, 0) などに"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d); d = _unit(d)
    Y = np.asarray(up, float); Y = Y - (Y @ d) * d
    Y = _unit(Y); X = np.cross(Y, d)
    return _make([_ring2([(-b / 2, -h / 2), (b / 2, -h / 2), (b / 2, h / 2), (-b / 2, h / 2)])], p0, X, Y, L)


def enchu(p0, p1, rad, rin=0.0):
    """円柱（rin > 0 で管）：軸 p0→p1、半径 rad"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d); d = _unit(d)
    a = np.array([0, 0, 1.]) if abs(d[2]) < 0.9 else np.array([1., 0, 0])
    X = _unit(np.cross(a, d)); Y = np.cross(d, X)
    cv = [r.Circle(float(rad)).ToNurbsCurve()]
    if rin > 0: cv.append(r.Circle(float(rin)).ToNurbsCurve())
    return _make(cv, p0, X, Y, L)


def ita(poly, z0, z1, simplify=0.5):
    """平面形（shapely の Polygon・MultiPolygon、穴あり可）を z0〜z1 の板に→押し出しの並び（片ごとに一つ）"""
    out = []
    for p in ([poly] if poly.geom_type == 'Polygon' else [g for g in getattr(poly, 'geoms', []) if g.geom_type == 'Polygon']):
        if p.is_empty or p.area < 100: continue
        if simplify: p = p.simplify(simplify)
        c = np.asarray(p.exterior.coords).mean(0)
        rings = [np.asarray(p.exterior.coords)[:-1] - c] + [np.asarray(h.coords)[:-1] - c for h in p.interiors]
        out.append(oshidashi(rings[0], rings[1:], (c[0], c[1], min(z0, z1)), (1, 0, 0), (0, 1, 0), abs(z1 - z0)))
    return out


def tama(c, rx, ry, rz, rot=0.0):
    """楕円体（一枚の閉じた面の Brep）。球の NURBS 面の制御点を軸ごとに縮める（rhino3dm の Brep.Transform は不等な縮尺が効かない）"""
    if min(rx, ry, rz) <= 0: raise ValueError('半径が 0 以下')
    ns = r.Sphere(r.Point3d(0, 0, 0), 1.0).ToNurbsSurface(); P = ns.Points
    for i in range(P.CountU):
        for j in range(P.CountV):
            p = P[i, j]; P[i, j] = r.Point4d(p.X * rx, p.Y * ry, p.Z * rz, p.W)
    ns.Transform(r.Transform.Rotation(math.radians(rot), r.Vector3d(0, 0, 1), r.Point3d(0, 0, 0)))
    ns.Transform(r.Transform.Translation(_V(c)))
    b = r.Brep.CreateFromSurface(ns)
    if b is None: raise ValueError('楕円体を作れない')
    return b


def kaiten(sec, c, a0, a1):
    """回転体（10-31、越屋根の曲げ木のルーバーなど）：鉛直の軸（中心 c=(x,y)）まわりに、r–z の閉じた折れ線 sec=[(r,z),...] を角度 a0〜a1（度）回した閉じた立体（一枚の面の Brep）。
    両端の蓋は同じ面を断面の中心へ平らに畳んで作る（球の極と同じ）。"""
    if abs(sec[0][0]-sec[-1][0])<1e-9 and abs(sec[0][1]-sec[-1][1])<1e-9: sec=sec[:-1]
    # 向き：断面を時計回り（r–z）にすると面の表が外を向く
    A=sum(sec[i][0]*sec[(i+1)%len(sec)][1]-sec[(i+1)%len(sec)][0]*sec[i][1] for i in range(len(sec)))
    if A>0: sec=sec[::-1]
    cr=sum(p[0] for p in sec)/len(sec); cz=sum(p[1] for p in sec)/len(sec)
    ring=sec+[sec[0]]; nu=len(ring)
    t0,t1=math.radians(a0),math.radians(a1); n=max(1,math.ceil(abs(t1-t0)/(math.pi/2)))
    rows=[]  # (list of (r,z), angle, weight, scale)
    def row(pts,t,w,s=1.0): rows.append(([(p[0]*s,p[1]) for p in pts],t,w,s))
    cen=[(cr,cz)]*nu; mid=[((p[0]+cr)/2,(p[1]+cz)/2) for p in ring]
    row(cen,t0,1); row(mid,t0,1); row(ring,t0,1)
    for k in range(n):
        ta=t0+(t1-t0)*k/n; tb=t0+(t1-t0)*(k+1)/n; h=(tb-ta)/2
        row(ring,ta+h,math.cos(h),1/math.cos(h)); row(ring,tb,1)
    row(mid,t1,1); row(cen,t1,1)
    nv=len(rows)
    s=r.NurbsSurface.Create(3,True,2,3,nu,nv)
    for j,(pts,t,w,_) in enumerate(rows):
        for i,(rr,zz) in enumerate(pts):
            x=c[0]+rr*math.cos(t); y=c[1]+rr*math.sin(t)
            s.Points[i,j]=r.Point4d(x*w,y*w,zz*w,w)
    for i in range(nu): s.KnotsU[i]=float(i)
    kv=[]; npieces=(nv-1)//2
    for k in range(npieces+1): kv+= [float(k),float(k)]
    for i,v in enumerate(kv): s.KnotsV[i]=v
    return r.Brep.CreateFromSurface(s)


def mesh(g):
    """押し出し→閉じた三角形の網（頂点を動かす段・manifold で削る段のため）。段10で同じ押し出しに戻る"""
    import solids
    V, F = solids.extrusion_vf(g)
    return solids.mesh_from_vf(V, F)


def add(m, g, li, col=None, name=None):
    """モデル m のレイヤー li に入れる（g は押し出し・Brep・その並び・メッシュ）。col は (r, g, b)"""
    if isinstance(g, (list, tuple)):
        for x in g: add(m, x, li, col, name)
        return
    a = r.ObjectAttributes(); a.LayerIndex = li
    if col is not None:
        a.ColorSource = r.ObjectColorSource.ColorFromObject; a.ObjectColor = (*col, 255)
    if name: a.Name = name
    if isinstance(g, r.Extrusion): m.Objects.AddExtrusion(g, a)
    elif isinstance(g, r.Mesh): g.Normals.ComputeNormals(); g.Compact(); m.Objects.AddMesh(g, a)
    elif isinstance(g, r.Brep): m.Objects.AddBrep(g, a)
    else: m.Objects.Add(g, a)
