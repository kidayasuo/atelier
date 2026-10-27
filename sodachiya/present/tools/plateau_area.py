"""地域のなかの敷地（1枚目、ユーザー 10-27）：PLATEAU（国土交通省 3D 都市モデル 京都市 2025）から、敷地のまわり約2 km四方の
建物（LOD1 の足もと）・道路（tran LOD1）・土地利用（luse：河川・公園・農地・山林など）を取り、3dm の座標（m）に直して present/plateau_area.json.gz へ。
使い方: python3 plateau_area.py [キャッシュのフォルダ]
位置合わせは data/georef.json（plateau_fetch.py と同じ）。出典：国土交通省 Project PLATEAU。"""
import sys, os, json, gzip, numpy as np
from lxml import etree
from pyproj import Transformer
from remotezip import RemoteZip
HERE = os.path.dirname(os.path.abspath(__file__)); SDY = os.path.dirname(os.path.dirname(HERE))
G = json.load(open(os.path.join(SDY, "data", "georef.json"), encoding="utf-8"))
DX, DY = G["model_origin_EPSG6674"]; URL = G["plateau_citygml_zip"]; C = np.array(G["site_centroid_model_m"])
CACHE = sys.argv[1] if len(sys.argv) > 1 else "/tmp/plateau_area"; os.makedirs(CACHE, exist_ok=True)
HX, HY = 1100.0, 900.0                                  # 敷地の中心から東西・南北に（m）
MESH = [f"523546{a}{b}" for a in "4567" for b in "1234"]
T = Transformer.from_crs(6697, 6674, always_xy=True)
NS = {"gml": "http://www.opengis.net/gml", "bldg": "http://www.opengis.net/citygml/building/2.0",
      "tran": "http://www.opengis.net/citygml/transportation/2.0", "luse": "http://www.opengis.net/citygml/landuse/2.0"}
want = []
with RemoteZip(URL) as z:
    names = set(z.namelist())
    for m in MESH:
        for k in ("bldg", "tran"):
            n = f"udx/{k}/{m}_{k}_6697_op.gml"
            if n in names: want.append(n)
    want.append("udx/luse/523546_luse_6697_op.gml")
    for n in want:
        if not os.path.exists(os.path.join(CACHE, n)):
            z.extract(n, CACHE); print("got", n, flush=True)
def to_model(pl):
    v = np.array(pl.text.split(), float).reshape(-1, 3)
    X, Y = T.transform(v[:, 1], v[:, 0])
    return np.c_[X - DX, Y - DY]
inside = lambda q: (abs(q[:, 0].mean() - C[0]) < HX + 50) and (abs(q[:, 1].mean() - C[1]) < HY + 50)
B, R, LU = [], [], []
for n in want:
    f = os.path.join(CACHE, n)
    if "/bldg/" in n:
        for _, el in etree.iterparse(f, tag="{%s}Building" % NS["bldg"]):
            fs = list(el.iterfind(".//bldg:lod0RoofEdge//gml:posList", NS)) or list(el.iterfind(".//bldg:lod0FootPrint//gml:posList", NS))
            if fs:
                q = to_model(fs[0])
            else:
                faces = list(el.iterfind(".//bldg:lod1Solid//gml:posList", NS))
                if not faces: el.clear(); continue
                vv = [np.array(p.text.split(), float).reshape(-1, 3) for p in faces]
                k_ = int(np.argmin([v[:, 2].mean() for v in vv])); q = to_model(faces[k_])
            if inside(q):
                h = el.find("bldg:measuredHeight", NS)
                B.append(dict(h=float(h.text) if h is not None else None, xy=np.round(q, 1).tolist()))
            el.clear()
    elif "/tran/" in n:
        for _, el in etree.iterparse(f, tag="{%s}Road" % NS["tran"]):
            fn = el.find("tran:function", NS)
            for p in el.iterfind(".//tran:lod1MultiSurface//gml:posList", NS):
                q = to_model(p)
                if inside(q): R.append(dict(func=fn.text if fn is not None else "", xy=np.round(q, 1).tolist()))
            el.clear()
    else:
        for _, el in etree.iterparse(f, tag="{%s}LandUse" % NS["luse"]):
            cl = el.find("luse:class", NS)
            for p in el.iterfind(".//luse:lod1MultiSurface//gml:posList", NS):
                q = to_model(p)
                if inside(q): LU.append(dict(cls=cl.text if cl is not None else "", xy=np.round(q, 1).tolist()))
            el.clear()
out = os.path.join(os.path.dirname(HERE), "plateau_area.json.gz")
json.dump(dict(_="地域のなかの敷地：PLATEAU 京都市 2025（bldg LOD0/1 の足もと・tran LOD1・luse）。3dm の座標（m）。出典：国土交通省 Project PLATEAU。present/tools/plateau_area.py",
               center=C.tolist(), half=[HX, HY], bldg=B, road=R, luse=LU), gzip.open(out, "wt", encoding="utf-8"), ensure_ascii=False)
print("bldg", len(B), "road", len(R), "luse", len(LU), "→", out)
