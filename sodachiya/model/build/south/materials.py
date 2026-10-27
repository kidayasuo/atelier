"""3dm のレイヤーと物に素材（レンダリングの素材）を割り当てる（設計監修、10-27。ユーザー：モデルに素材を割り当てる）。

使い方: python3 materials.py MATERIALS.json FILE.3dm [FILE2.3dm ...]   （ファイルをその場で書き換える）
- 素材の表と、レイヤー・物の名前との対応は data/materials.json（そこだけを直せばよい）。
- レイヤーの名前（親を除く）の頭で素材を探し、レイヤーの素材（RenderMaterialIndex）にする。物は「レイヤーから」に戻す。
- 一つのレイヤーに枠とガラス、幹と葉が混ざっている所（split）は、物の厚さ（いちばん薄い向きの寸法）で分け、物ごとに素材を付ける。
- 物の名前の言葉（names）はレイヤーより先。
- レイヤーの表示の色（平面図の色分け）は変えない。ファイルはその場で書き換える（グループ・親子のレイヤーを保つ）。finish.py のガラスの2つは使われなくなる。
- 物のあるレイヤーで素材の見つからないものは「素材なし」と出す（新しいレイヤーを足したら data/materials.json に一行足す）。
- 縁側のガラス戸のロゴ（10-27、ユーザー：ガラスのロゴのエッチングは、テクスチャマッピングで単に絵を貼り付けて）：
  add_floor.py が戸のガラスに書いたユーザー文字列 'etch'（中心・室内向きの法線・大きさ）の所に、ガラスの室内側の面から 0.5 離して
  絵を貼った板（四角 1 枚のメッシュ、テクスチャ座標つき）を足す。絵は logo/sodachiya_logo.svg から毎回作る PNG
  （白＝エッチング、透明＝ガラスのまま）。Rhino の「デカール」は rhino3dm では足せないので、絵を貼った板にした。
  Rhino 版（clean_wire.py は物のユーザー文字列を写さない）では 'src'（メッシュの版の何番目の物か）でメッシュの版の 'etch' を引く。
  PNG は Rhino 版のある所の logo/ に書き、3dm にも埋め込む（Rhino は 3dm からの相対の場所か、埋め込んだ写しで見つける）。
"""
import json, os, re, sys
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


# ---------------------------------------------------------------- ガラスのロゴ（絵を貼った板）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[1])))           # sodachiya/（data/materials.json の上）
LOGO_SVG = os.path.join(ROOT, 'logo', 'sodachiya_logo.svg')
IMG_DIR = os.path.join(os.path.commonpath([os.path.dirname(os.path.abspath(p)) for p in sys.argv[2:]]), 'logo')   # Rhino 版のある所の logo/
IMG = os.path.join(IMG_DIR, 'sodachiya_logo_etch.png')            # 白、透明の所は α 0（絵）
MASK = os.path.join(IMG_DIR, 'sodachiya_logo_etch_mask.png')      # 白＝エッチング（不透明）、黒＝透明（透明度の絵）
PX = 1024                                                          # 絵の一辺（φ180 → 約 5.7 px/mm）
ETCH_NAME = '園のロゴ（エッチング）'
ETCH_MAT = '園のロゴ（エッチング、絵）'
ETCH_OFF = 0.5                                                     # ガラスの室内側の面から


def logo_images():
    """SVG の黒（fill-rule evenodd）を絵に（形は写さず毎回 SVG から）。直線の輪郭（M・L・Z）だけを読む"""
    from PIL import Image, ImageDraw
    src = open(LOGO_SVG, encoding='utf-8').read()
    vb = re.search(r'viewBox="([^"]*)"', src)
    x0, y0, w, h = map(float, vb.group(1).replace(',', ' ').split()) if vb else (0.0, 0.0, 200.0, 200.0)
    S = 4; N = PX * S                                              # 4 倍で描いて縮める（縁をなめらかに）
    acc = np.zeros((N, N), bool)
    for mm in re.finditer(r'<path\b([^>]*)/?>', src):
        d = re.search(r'\sd="([^"]*)"', mm.group(1)).group(1)
        if re.search(r'[CcQqSsTtAaHhVv]', d):
            raise SystemExit(f'materials: {LOGO_SVG} に直線でない輪郭（C・Q・A など）がある。直線（M・L・Z）で書き出し直す')
        one = np.zeros((N, N), bool)
        for sub in re.split(r'[Mm]', d)[1:]:
            pts = [((float(a) - x0) / w * N, (float(b) - y0) / h * N) for a, b in re.findall(r'(-?[\d.]+)[ ,](-?[\d.]+)', sub)]
            if len(pts) < 3: continue
            im = Image.new('1', (N, N), 0); ImageDraw.Draw(im).polygon(pts, fill=1)
            one ^= np.asarray(im, bool)                            # evenodd
        acc |= one
    a = Image.fromarray((acc * 255).astype(np.uint8), 'L').resize((PX, PX), Image.LANCZOS)
    os.makedirs(IMG_DIR, exist_ok=True)
    al = np.asarray(a)
    rgba = np.dstack([np.full_like(al, 250), np.full_like(al, 250), np.full_like(al, 248), al])
    Image.fromarray(rgba, 'RGBA').save(IMG, optimize=True)
    Image.fromarray((al.astype(float) * 0.85).astype(np.uint8), 'L').save(MASK, optimize=True)   # すりガラス：白の所も少し透ける


ETCH = {}            # メッシュの版の物の番号 → (レイヤーの名前, 'etch' の JSON)


def etch_material():
    a = r.Material()
    a.Name = ETCH_MAT
    a.DiffuseColor = (250, 250, 248, 255)
    a.Shine = 0.25 * 255.0                                         # 艶消しに近い（すりガラス）
    a.SetBitmapTexture(IMG)                                        # 返り値は rhino3dm 8.35 で成り立っても False（読み返すと入っている）
    a.SetTransparencyTexture(MASK)                                 # 白＝不透明、黒＝透明
    a.SetUserString('sodachiya', 'logo/sodachiya_logo.svg → ' + os.path.basename(IMG))
    return a


def quad(c, t, n, w, h, uv=True):
    """中心 c、幅 w（t の向き、室内から見て右が +）、高さ h（上が +）の四角。面は n（室内）を向く"""
    c = np.asarray(c, float) + np.asarray(n, float) * ETCH_OFF; t = np.asarray(t, float); z = np.array([0, 0, 1.0])
    M = r.Mesh()
    for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        q = c + t * (su * w / 2) + z * (sv * h / 2); M.Vertices.Add(float(q[0]), float(q[1]), float(q[2]))
        if uv: M.TextureCoordinates.__add__((su + 1) / 2, (sv + 1) / 2)    # 絵の左下が (0, 0)
    M.Faces.AddFace(0, 1, 2, 3); M.Normals.ComputeNormals()
    return M


def add_etch(m, layers, mat_index):
    """'etch' の所に絵を貼った板を足す（前の板は消してから）→ 板の数"""
    for o in [o for o in m.Objects if o.Attributes.GetUserString('etch_of')]:
        m.Objects.Delete(o.Attributes.Id)
    lidx = {L.Name: i for i, L in enumerate(layers)}
    recs = []
    for i, o in enumerate(m.Objects):
        e = o.Attributes.GetUserString('etch')
        if e:
            recs.append((layers[o.Attributes.LayerIndex].Name, e, str(o.Attributes.Id))); ETCH[i] = (layers[o.Attributes.LayerIndex].Name, e)
    if not recs and ETCH:                                          # Rhino 版：'src' でメッシュの版の 'etch' を引き、物にも写す
        seen = set()
        for o in m.Objects:
            s = o.Attributes.GetUserString('src')
            if not s or not s.isdigit() or int(s) not in ETCH or s in seen: continue
            seen.add(s); ln, e = ETCH[int(s)]
            o.Attributes.SetUserString('etch', e)
            recs.append((ln, e, str(o.Attributes.Id)))
    if not recs: return 0
    have = {mt.Name: i for i, mt in enumerate(m.Materials)}
    mi = have[ETCH_MAT] if ETCH_MAT in have else m.Materials.Add(etch_material())
    emb = set(m.EmbeddedFilePaths())
    for f in (IMG, MASK):
        if f not in emb: m.EmbeddedFiles.Add(r.EmbeddedFile.Read(f))
    n = 0
    for ln, e, gid in recs:
        d = json.loads(e)
        for mk in d['marks']:
            logo = mk['kind'] == 'logo'
            a = r.ObjectAttributes(); a.LayerIndex = lidx[ln]; a.Name = ETCH_NAME + ('' if logo else '：大人の目の高さの帯')
            a.MaterialSource = r.ObjectMaterialSource.MaterialFromObject
            a.MaterialIndex = mi if logo else mat_index('乳白ガラス', layers[lidx[ln]].Color)
            a.ColorSource = r.ObjectColorSource.ColorFromObject; a.ObjectColor = (245, 245, 242, 255)
            a.SetUserString('etch_of', gid)                         # どのガラスの物に貼ったか
            m.Objects.AddMesh(quad(mk['c'], d['t'], d['n'], mk['w'], mk['h'], logo), a); n += 1
    return n


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
        if a.GetUserString('etch_of'): continue                    # 前に足したロゴの板（下の add_etch で作り直す）
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
    ne = add_etch(m, layers, mat_index)
    m.Write(os.path.abspath(path), 8)                               # 絶対の場所で書く（絵の場所を 3dm からの相対でも残すため）
    print(f'materials: {path.split("/")[-1]}：素材 {len(idx)}・物 {len(m.Objects)}・ガラスのロゴの板 {ne}'
          + (f'・素材なし {len(missing)}（{"、".join(missing[:8])}）' if missing else ''))
    return count


logo_images()
for p in sys.argv[2:]:
    apply(p)
