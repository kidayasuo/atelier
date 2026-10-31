#! python 3
# -*- coding: utf-8 -*-
"""育ち舎　後処理（Rhino で sodachiya.3dm を開いたあと、手で一度走らせる。設計監修 10-31）

今していること（段を足すときはこの一覧と main() に足す）：
  1. 床の絵を床の立体に直接貼る（ユーザー 10-31：重ねた板でなく立体にマッピング）

自動の作り直しは Rhino でなく rhino3dm で 3dm を作るので、立体にテクスチャマッピングを付けられない。
そこで作り直しは「床の絵の板」を床の上 1 mm に重ねている（materials.py）。このスクリプトは Rhino の中で、
床の立体そのものに本当の寸法の平面マッピングを付け、絵の付いた素材に替え、重ねた板のレイヤーを隠す。

使い方（Rhino 8、Mac）：
  1. sodachiya/sodachiya.3dm を開く（git pull の後に）。
  2. コマンド RunPythonScript で、このファイル（sodachiya/post_process.py、sodachiya.3dm の隣）を選ぶ。数秒〜数十秒。
  3. 保存するなら別名で（sodachiya.3dm は作り直しのたびに上書きされるので、開き直したらもう一度走らせる）。
何度走らせてもよい（同じ結果になる）。

決まり：
  - 対象：素材の名前が「（絵なし）」で終わる物（materials.py が床の立体に付けた、絵なしの同じ色の素材）。
    その物に、同じ名前から「（絵なし）」を取った、絵の付いた素材を付ける。
  - マッピング：物ごとの平面マッピング（チャンネル 1）。平面の原点は物の真ん中、向きはその場所の本館の放射の向き
    （model/build/south/uv.py の弧の中心から）。板の長さの向き＝dir（v＝放射、架構と平行／u＝弧に沿う）。
    dir はレイヤーごとに data/materials.json の texture_dir、無ければ素材の dir（materials.py と同じ）。
  - 絵の大きさ（1 枚の絵の本当の寸法、mm）は model/build/south/textures.py と同じ：杉 2400×2400（本館係の絵 data/tex/sugi_floor.png、10-31 ユーザー：A）、
    洗い出し 600×600。
  - 物にユーザー文字列 tex_angle（度、ワールドの X から反時計回り＝板の長さの向き、本館係）があれば、それを優先する。
  - 床の絵の板のレイヤーは隠す（消さない。元に戻すときはレイヤーを表示にする）。
"""
import io, json, math, os
import Rhino
import scriptcontext as sc
import rhinoscriptsyntax as rs

CX, CY = 194662.93237, -41348.26335                       # 本館の背骨の弧の中心（uv.py）
PLAIN = '（絵なし）'
SKIN_LAYER = '床の絵（テクスチャを貼った板、materials.py が作り直しのたびに）'
TILE = {'sugi': (2400.0, 2400.0), 'arai': (600.0, 600.0)}  # 種類 → (絵の横＝板の幅の向き, 縦＝板の長さの向き) mm


# data/materials.json が見つからないとき（3dm をリポジトリの外で開いたときなど）の既定（materials.json と同じ値）
DEFAULT_SPEC = {'materials': {'杉の床板 t30': {'texture': 'sugi', 'dir': 'v'},
                              '洗い出し（土足の床・ポーチ）': {'texture': 'arai'}},
                'texture_dir': [['13_', 'u'], ['81_', 'u'], ['56_', 'u'], ['59_', 'u']]}


def load_spec():
    """このスクリプトの隣（sodachiya/data/）、3dm の隣の順に探す。無ければ既定で続ける（止めない）"""
    here = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else ''
    for d in (here, os.path.dirname(sc.doc.Path or '')):
        p = os.path.join(d, 'data', 'materials.json') if d else ''
        if p and os.path.exists(p):
            return json.load(io.open(p, encoding='utf-8')), p
    return DEFAULT_SPEC, '（既定の値。data/materials.json が見つからなかった）'


def tex_dir(layer_name, spec, rules):
    for pre, d in rules:
        if layer_name.startswith(pre):
            return d
    return spec.get('dir', 'v')


def floor_mapping():
    SPEC, src = load_spec()
    print('素材の表：' + src)
    mats, rules = SPEC['materials'], SPEC.get('texture_dir', [])
    doc = sc.doc
    names = {doc.Materials[i].Name: i for i in range(doc.Materials.Count)}
    n = 0; miss = set()
    for o in list(doc.Objects.GetObjectList(Rhino.DocObjects.ObjectType.AnyObject)):
        mi = o.Attributes.MaterialIndex
        if mi < 0 or mi >= doc.Materials.Count: continue
        mname = doc.Materials[mi].Name
        if not mname.endswith(PLAIN): continue
        base = mname[:-len(PLAIN)]
        spec = mats.get(base, {})
        kind = spec.get('texture')
        if base not in names or kind not in TILE:
            miss.add(base); continue
        bb = o.Geometry.GetBoundingBox(True)
        c = bb.Center
        rad = Rhino.Geometry.Vector3d(c.X - CX, c.Y - CY, 0); rad.Unitize()    # 放射（外向き）
        tan = Rhino.Geometry.Vector3d(-rad.Y, rad.X, 0)                         # 弧に沿う
        lay = doc.Layers[o.Attributes.LayerIndex].Name
        ang = o.Attributes.GetUserString('tex_angle')                            # 本館係の向きがあれば優先
        if ang:
            t = math.radians(float(ang))
            along = Rhino.Geometry.Vector3d(math.cos(t), math.sin(t), 0)
        else:
            along = rad if tex_dir(lay, spec, rules) == 'v' else tan            # 板の長さの向き
        across = Rhino.Geometry.Vector3d(-along.Y, along.X, 0)
        pl = Rhino.Geometry.Plane(Rhino.Geometry.Point3d(c.X, c.Y, bb.Max.Z), across, along)
        w, l = TILE[kind]
        m = Rhino.Render.TextureMapping.CreatePlaneMapping(pl, Rhino.Geometry.Interval(0, w), Rhino.Geometry.Interval(0, l),
                                                           Rhino.Geometry.Interval(-1, 1))
        doc.Objects.ModifyTextureMapping(o, 1, m)
        a = o.Attributes.Duplicate()
        a.MaterialSource = Rhino.DocObjects.ObjectMaterialSource.MaterialFromObject
        a.MaterialIndex = names[base]
        doc.Objects.ModifyAttributes(o, a, True)
        n += 1
    li = doc.Layers.FindByFullPath(SKIN_LAYER, -1)
    if li < 0:
        for i in range(doc.Layers.Count):
            if doc.Layers[i].Name == SKIN_LAYER: li = i
    if li >= 0:
        L = doc.Layers[li]; L.IsVisible = False; L.IsLocked = True
    doc.Views.Redraw()
    print('床の絵：立体 %d にマッピングを付けた。重ねた板のレイヤーを%s。%s' % (
        n, '隠した' if li >= 0 else '見つけられなかった', ('素材が見つからない：' + '・'.join(sorted(miss))) if miss else ''))


def main():
    floor_mapping()


main()
