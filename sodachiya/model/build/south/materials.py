"""3dm のレイヤーと物に素材（レンダリングの素材）を割り当てる（設計監修、10-27。ユーザー：モデルに素材を割り当てる）。

使い方: python3 materials.py MATERIALS.json FILE.3dm [FILE2.3dm ...]   （ファイルをその場で書き換える）
- 素材の表と、レイヤー・物の名前との対応は data/materials.json（そこだけを直せばよい）。
- レイヤーの名前（親を除く）の頭で素材を探し、レイヤーの素材（RenderMaterialIndex）にする。物は「レイヤーから」に戻す。
- 一つのレイヤーに枠とガラス、幹と葉が混ざっている所（split）は、物の厚さ（いちばん薄い向きの寸法）で分け、物ごとに素材を付ける。
- 物の名前の言葉（names）はレイヤーより先。
- レイヤーの表示の色（平面図の色分け）は変えない。ファイルはその場で書き換える（グループ・親子のレイヤーを保つ）。finish.py のガラスの2つは使われなくなる。
- 物のあるレイヤーで素材の見つからないものは「素材なし」と出す（新しいレイヤーを足したら data/materials.json に一行足す）。
"""
import json, sys
import numpy as np
import rhino3dm as r

SPEC = json.load(open(sys.argv[1], encoding='utf-8'))
MATS, LAYERS, NAMES = SPEC['materials'], SPEC['layers'], SPEC.get('names', [])


def rule_for(layer_name):
    for pre, m in LAYERS:
        if layer_name.startswith(pre):
            return m
    return None


def points(g):
    """物の頂点（mm）。厚さを測るためだけ"""
    if isinstance(g, r.Mesh):
        return np.array([[p.X, p.Y, p.Z] for p in g.Vertices])
    if isinstance(g, r.Extrusion):
        g = g.ToBrep(False)
    if isinstance(g, r.Brep):
        return np.array([[v.Location.X, v.Location.Y, v.Location.Z] for v in g.Vertices])
    b = g.GetBoundingBox()
    return np.array([[b.Min.X, b.Min.Y, b.Min.Z], [b.Max.X, b.Max.Y, b.Max.Z]])


def thickness(g):
    """いちばん薄い向きの寸法（主成分で回した箱）。弧に沿って回った戸・ガラスでも測れる"""
    P = points(g)
    if len(P) < 6:
        # 頂点の少ない物（球の樹冠・円の押し出しの幹など）は外接の箱で測る
        b = g.GetBoundingBox()
        return float(min(b.Max.X - b.Min.X, b.Max.Y - b.Min.Y, b.Max.Z - b.Min.Z))
    Q = P - P.mean(0)
    _, _, vt = np.linalg.svd(Q, full_matrices=False)
    ext = Q @ vt.T
    return float((ext.max(0) - ext.min(0)).min())


def make(name, spec, layer_color):
    a = r.Material()
    a.Name = name
    base = spec['base']
    rgb = tuple(layer_color[:3]) if base == 'layer' else tuple(base)
    op = spec.get('opacity', 1.0)
    a.DiffuseColor = (*rgb, 255)
    a.Transparency = round(1.0 - op, 3)
    if 'ior' in spec:
        a.IndexOfRefraction = spec['ior']
    a.Shine = (1.0 - spec.get('roughness', 0.8)) * 255.0
    a.Reflectivity = spec.get('metallic', 0.0) * 0.8 + (0.1 if op < 1 else 0.0)
    a.ToPhysicallyBased()
    pb = a.PhysicallyBased
    pb.BaseColor = (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255, 1.0)
    pb.Roughness = spec.get('roughness', 0.8)
    pb.Metallic = spec.get('metallic', 0.0)
    pb.Opacity = op
    if 'ior' in spec:
        pb.OpacityIOR = spec['ior']
    if 'clearcoat' in spec:
        pb.Clearcoat = spec['clearcoat']
    a.SetUserString('sodachiya', 'data/materials.json')
    return a


def apply(path):
    m = r.File3dm.Read(path)
    # その場で書き換える（グループ・親子のレイヤー・物の属性を失わないため）。同じ名前の素材があれば使い回す
    have = {mt.Name: i for i, mt in enumerate(m.Materials)}
    idx = {}

    def mat_index(name, layer_color):
        label = name if MATS[name]['base'] != 'layer' else f'{name}：{layer_color[0]},{layer_color[1]},{layer_color[2]}'
        if label not in idx:
            idx[label] = have[label] if label in have else m.Materials.Add(make(label, MATS[name], layer_color))
        return idx[label]

    layers = list(m.Layers)
    used = {}
    for o in m.Objects:
        used[o.Attributes.LayerIndex] = used.get(o.Attributes.LayerIndex, 0) + 1
    missing = []
    for i, L in enumerate(layers):
        rule = rule_for(L.Name)
        if isinstance(rule, str):
            m.Layers[i].RenderMaterialIndex = mat_index(rule, L.Color)
        elif isinstance(rule, dict):
            m.Layers[i].RenderMaterialIndex = mat_index(rule['else'], L.Color)
        elif used.get(i):
            missing.append(L.Name)
    count = {}
    for o in m.Objects:
        a = o.Attributes
        L = layers[a.LayerIndex]
        rule = rule_for(L.Name)
        name = next((mt for word, mt in NAMES if word in (a.Name or '')), None)
        if name is None and isinstance(rule, dict):
            name = rule['thin'] if thickness(o.Geometry) <= rule['split'] else rule['else']
        if name is not None:
            a.MaterialSource = r.ObjectMaterialSource.MaterialFromObject
            a.MaterialIndex = mat_index(name, L.Color)
        else:
            a.MaterialSource = r.ObjectMaterialSource.MaterialFromLayer
            name = rule if isinstance(rule, str) else '（素材なし）'
        count[name] = count.get(name, 0) + 1
    m.Write(path, 8)
    print(f'materials: {path.split("/")[-1]}：素材 {len(idx)}・物 {len(m.Objects)}'
          + (f'・素材なし {len(missing)}（{"、".join(missing[:8])}）' if missing else ''))
    return count


for p in sys.argv[2:]:
    apply(p)
