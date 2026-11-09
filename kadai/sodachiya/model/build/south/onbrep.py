"""openNURBS の ON_Brep を Python で書く（ソリッド係、10-25）。
rhino3dm（Python）には面をつなぐ（Join）・面から Brep を組む機能が無いので、ON_Brep の書き出し（版 3.3）を
自分で組み、rhino3dm.CommonObject.Decode で読んで rhino3dm.Brep にする。
- 面（平面・回転面）は rhino3dm の物を Encode した書き出しをそのまま埋め込む。
- 曲線（線・ポリライン・有理 NURBS、2 次元と 3 次元）はここで書く。
書式は rhino3dm が書いたもの（箱・穴あきの押し出しの Brep）と一つずつ突き合わせて確かめた：
- 塊（chunk）は 4 バイトの印＋8 バイトの長さ。印に 0x8000 があれば最後に CRC32。CRC はその塊の直接のバイトだけ
  （入れ子の塊は頭も含めて除く）。
- 面の配列は版 1.1（面の後に面ごとの uuid 16 バイト）。描画・解析メッシュの塊は面ごとに 1 バイト（0＝無し）。
- トリムは：番号・c2i・代理の定義域・ei・vi[2]・bRev3d・種類・iso・li・許容差[2]・定義域・予備 4・旧い許容差 2。
"""
import struct, zlib, base64
import rhino3dm as r

TC_ANON = 0x40008000
UNSET = -1.23432101234321e+308
_ENC = None


class Chunk:
    def __init__(self, tc, crc=True):
        self.tc, self.crc, self.parts, self.direct = tc, crc, [], bytearray()

    def raw(self, b):
        b = bytes(b); self.parts.append(b); self.direct += b; return self

    def i(self, *v): return self.raw(struct.pack('<%di' % len(v), *[int(x) for x in v]))
    def d(self, *v): return self.raw(struct.pack('<%dd' % len(v), *[float(x) for x in v]))
    def byte(self, v): return self.raw(bytes([v]))
    def iarr(self, a): return self.i(len(a), *a)

    def sub(self, ch):
        self.parts.append(ch if isinstance(ch, (bytes, bytearray)) else ch.bytes()); return self

    def bytes(self):
        body = b''.join(self.parts)
        if self.crc: body += struct.pack('<I', zlib.crc32(bytes(self.direct)) & 0xffffffff)
        return struct.pack('<Iq', self.tc, len(body)) + body


def enc(obj):
    global _ENC
    e = obj.Encode()
    if _ENC is None: _ENC = {k: v for k, v in e.items() if k != 'data'}
    return base64.b64decode(e['data'])


def decode(b):
    if _ENC is None: enc(r.LineCurve(r.Point3d(0, 0, 0), r.Point3d(1, 0, 0)))
    e = dict(_ENC); e['data'] = base64.b64encode(b).decode()
    return r.CommonObject.Decode(e)


def _cls(uu, data):
    u = Chunk(0x0002fffb).raw(uu)
    return Chunk(0x00027ffa, crc=False).sub(u).sub(data).sub(struct.pack('<Iq', 0x80027fff, 0)).bytes()


_BREP_UU = bytes.fromhex('c5dbb56060e6d311bfe40010830122f0')
_LINE_UU = bytes.fromhex('dbd4d74e47e9d311bfe50010830122f0')
_PLINE_UU = bytes.fromhex('e6d4d74e47e9d311bfe50010830122f0')
_NURBS_UU = bytes.fromhex('ddd4d74e47e9d311bfe50010830122f0')


def line(p0, p1, dim, t0=0.0, t1=1.0):
    q0 = list(p0) + [0.0] * (3 - len(p0)); q1 = list(p1) + [0.0] * (3 - len(p1))
    return _cls(_LINE_UU, Chunk(0x0002fffc).byte(0x10).d(*q0[:3], *q1[:3]).d(t0, t1).i(dim))


def polyline(pts, dim, ts=None):
    if ts is None:
        ts = [0.0]
        for a, b in zip(pts, pts[1:]): ts.append(ts[-1] + sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5)
    c = Chunk(0x0002fffc).byte(0x10).i(len(pts))
    for p in pts:
        q = list(p) + [0.0] * (3 - len(p)); c.d(*q[:3])
    c.i(len(ts)).d(*ts).i(dim)
    return _cls(_PLINE_UU, c)


def nurbs(dim, order, knots, cvs, weights=None):
    """cvs は普通の座標（dim 個）。weights があれば有理（同次座標で書く）"""
    rat = weights is not None
    c = Chunk(0x0002fffc).byte(0x11).i(dim, 1 if rat else 0, order, len(cvs), 0, 0).d(1, 0, 0, -1, 0, 0)
    c.i(len(knots)).d(*knots).i(len(cvs))
    for k, p in enumerate(cvs):
        if rat:
            w = weights[k]; c.d(*[x * w for x in p[:dim]], w)
        else: c.d(*p[:dim])
    c.raw(b'\0')            # 版 1.1 の 1 バイト（rhino3dm の書き出しと同じ）
    return _cls(_NURBS_UU, c)


def write_brep(C2, C3, S, V, E, T, L, F, solid=True):
    """C2・C3：曲線の書き出し（bytes）、S：rhino3dm の面。
    V：[(xyz, [ei], tol)]、E：[(c3i, (d0,d1), (v0,v1), [ti], tol)]、
    T：[(c2i, (t0,t1), ei, (v0,v1), rev3d, type, iso, li)]（type 1 境界 2 つながり 4 特異点）、
    L：[([ti], type, fi)]、F：[([li], si, rev)]"""
    data = Chunk(0x0002fffc).byte(0x33)
    for arr in (C2, C3, S):
        a = Chunk(TC_ANON).byte(0x10).i(len(arr))
        for o in arr:
            a.i(1).sub(o if isinstance(o, (bytes, bytearray)) else enc(o))
        data.sub(a)
    a = Chunk(TC_ANON).byte(0x10).i(len(V))
    for k, (p, ei, tol) in enumerate(V): a.i(k).d(*p).iarr(ei).d(tol)
    data.sub(a)
    a = Chunk(TC_ANON).byte(0x10).i(len(E))
    for k, (c3i, dom, vi, ti, tol) in enumerate(E):
        a.i(k, c3i, 0).d(*dom).i(*vi).iarr(ti).d(tol).d(*dom)
    data.sub(a)
    a = Chunk(TC_ANON).byte(0x10).i(len(T))
    for k, (c2i, pd, ei, vi, rev3d, typ, iso, li) in enumerate(T):
        a.i(k, c2i).d(*pd).i(ei, *vi).i(rev3d, typ, iso, li).d(0, 0).d(*pd).d(0, 0, 0, 0).d(UNSET, UNSET)
    data.sub(a)
    a = Chunk(TC_ANON).byte(0x10).i(len(L))
    for k, (ti, typ, fi) in enumerate(L): a.i(k).iarr(ti).i(typ, fi)
    data.sub(a)
    a = Chunk(TC_ANON).byte(0x11).i(len(F))
    for k, (li, si, rev) in enumerate(F): a.i(k).iarr(li).i(si, rev, 0)
    for _ in F: a.raw(b'\0' * 16)
    data.sub(a)
    data.d(1, 0, 0, -1, 0, 0)                                   # 外接箱（空：読み込みで作り直す）
    for _ in range(2): data.sub(Chunk(TC_ANON).raw(b'\0' * len(F)))   # 面ごとの描画・解析メッシュ（無し）
    data.i(0).sub(Chunk(TC_ANON).raw(bytes.fromhex('010000000100000000')))   # 版 3.2・3.3 の欄（rhino3dm の箱と同じ）
    return decode(_cls(_BREP_UU, data))
