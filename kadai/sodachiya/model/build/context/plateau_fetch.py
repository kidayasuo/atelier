"""周辺の道路・建物を PLATEAU（国土交通省 3D 都市モデル、京都市 2025 年度、CityGML）から取り、3dm の座標に直して data/context_plateau.json へ
使い方: python3 plateau_fetch.py data/context_plateau.json [半径 m（既定 230）]
- 出典：国土交通省 Project PLATEAU「3D 都市モデル 京都市（2025 年度）」（G 空間情報センター、CC BY 4.0 互換の PLATEAU のライセンス）。
- 大きな zip（2.7 GB）から敷地のまわりの 3 次メッシュ 4 枚（52354652・53・62・63）の bldg（LOD1）と tran（道路 LOD1）だけを部分的に読む（remotezip）。
- 位置合わせ（data/georef.json）：3dm の (x, y) m ＋ (dx, dy) ＝ 平面直角座標 VI 系（EPSG:6674）の (X, Y)。回転なし（3dm の +y は北、子午線収差 約 0.1° は無視）。
  敷地の西の辺を南北の公道 6 m の東の端に、北西の辺を北の公道の南東の端に合わせた（10-22、図と PLATEAU の道路で、ずれは 2 m 程度まで）。
- 高さ：建物の LOD1 の下端（標高 m）から、敷地のまわりの地盤を 74.06 m（敷地の近くの建物の下端の中央値）として、3dm の z（mm、FL±0、GL−300）に直す。
  道路の LOD1 は高さを持たない（z=0）ので、近くの建物の下端から内挿した地盤の高さを付ける。
"""
import sys, os, json, glob, numpy as np
from lxml import etree
from pyproj import Transformer
from remotezip import RemoteZip
OUT = sys.argv[1]; RAD = float(sys.argv[2]) if len(sys.argv) > 2 else 230.0
HERE = os.path.dirname(os.path.abspath(OUT))
G = json.load(open(os.path.join(HERE, 'georef.json')))
DX, DY = G['model_origin_EPSG6674']; GL_TP = G['site_GL_TP_m']
URL = G['plateau_citygml_zip']; MESH = G['plateau_meshes']
CACHE = '/tmp/plateau_cache'; os.makedirs(CACHE, exist_ok=True)
with RemoteZip(URL) as z:
    for m in MESH:
        for k in ('bldg', 'tran'):
            n = f'udx/{k}/{m}_{k}_6697_op.gml'
            if not os.path.exists(os.path.join(CACHE, n)): z.extract(n, CACHE); print('got', n)
T = Transformer.from_crs(6697, 6674, always_xy=True)
NS = {'gml': 'http://www.opengis.net/gml', 'bldg': 'http://www.opengis.net/citygml/building/2.0',
      'tran': 'http://www.opengis.net/citygml/transportation/2.0'}
C = np.array(G['site_centroid_model_m'])
def to_model(pl):
    v = np.array(pl.text.split(), float).reshape(-1, 3)
    X, Y = T.transform(v[:, 1], v[:, 0])
    return np.c_[X - DX, Y - DY, (v[:, 2] - GL_TP) * 1000.0 - 300.0]
def near(q): return np.hypot(*(q[:, :2].mean(0) - C)) < RAD
B, RD = [], []
for f in sorted(glob.glob(CACHE + '/udx/bldg/*.gml')):
    for _, el in etree.iterparse(f, tag='{%s}Building' % NS['bldg']):
        faces = [to_model(p) for p in el.iterfind('.//bldg:lod1Solid//gml:posList', NS)]
        if faces and near(faces[0]):
            allp = np.vstack(faces); z0, z1 = allp[:, 2].min(), allp[:, 2].max()
            foot = min(faces, key=lambda q: q[:, 2].mean())[:, :2]
            h = el.find('bldg:measuredHeight', NS)
            B.append(dict(id=el.get('{http://www.opengis.net/gml}id'), z0=round(z0), z1=round(z1),
                          h=float(h.text) if h is not None else None, foot=np.round(foot, 3).tolist()))
        el.clear()
for f in sorted(glob.glob(CACHE + '/udx/tran/*.gml')):
    for _, el in etree.iterparse(f, tag='{%s}Road' % NS['tran']):
        fn = el.find('tran:function', NS)
        for p in el.iterfind('.//tran:lod1MultiSurface//gml:posList', NS):
            q = to_model(p)
            if near(q): RD.append(dict(func=fn.text if fn is not None else '', xy=np.round(q[:, :2], 3).tolist()))
        el.clear()
json.dump(dict(_=('周辺の道路・建物（PLATEAU 京都市 2025、bldg LOD1・tran LOD1）。座標は 3dm と同じ（m、z は mm で FL±0）。'
                  '出典：国土交通省 Project PLATEAU。plateau_fetch.py で作る。'), radius_m=RAD, bldg=B, road=RD),
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
print('bldg', len(B), 'road', len(RD), '→', OUT)
