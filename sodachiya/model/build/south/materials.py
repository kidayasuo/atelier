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
- 床の絵（テクスチャ、10-31。本館係の項 20261031-1430、ユーザー：床を床に見せる）：素材の表で texture の付いた素材（杉の床板・洗い出し）は、
  south/textures.py で絵を毎回作り（決まった種で同じ絵、継ぎ目なしで敷ける）、Rhino 版のある所の textures/ に書いて 3dm に埋め込み、
  素材の絵（旧来の Bitmap ＝物理ベースの Base color の枠）にする。絵の大きさは本当の寸法（杉 2,160×7,280、洗い出し 600 角）。
  * メッシュの版：床のメッシュの頂点にテクスチャ座標を書く。本館の (u, v)（uv.py）で、板の向き v＝放射（架構・梁と平行、庭へ）、
    u＝弧に沿う（texture_dir でレイヤーごとに）。板は放射の線に沿って扇に並ぶので、幅 135 は物の真ん中の半径で合わせ、端で数 % 違う。
    西館・外構も同じ (u, v) で。
  * Rhino 版：ポリサーフェス・押し出しにはテクスチャ座標を持たせられず、rhino3dm 8.35 では物にマッピング（平面・WCS）も付けられない
    （ObjectAttributes にマッピングの口が無い・File3dm にマッピングの表が無い・デカールは足せない）。そこでロゴと同じく、
    メッシュの版の床の上向きの面を写した「絵を貼った板」（テクスチャ座標つきのメッシュ、床の上 1 mm）をレイヤー「床の絵」（錠）に足す。
    床のポリサーフェスには絵なしの同じ色の素材（「〇〇（絵なし）」）を付ける（面の大きさに引き伸ばされた絵が縁に出ないように）。
"""
import json, math, os, re, sys
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
    if 'emission' in spec:                                          # 10-29 プレゼンの準備：越屋根の LED を 3dm の中で初めから光らせる（夜のレンダリングで材料を差し替えると Rhino が落ちる）
        e = spec['emission']; k = spec.get('emission_strength', 1.0)
        a.EmissionColor = (*e, 255)
        pb.EmissionColor = (e[0] / 255 * k, e[1] / 255 * k, e[2] / 255 * k, 1.0)
    set_texture(a, spec)
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


# ---------------------------------------------------------------- 床の絵（テクスチャ）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import textures as TX
TX.DATA_DIR = os.path.dirname(os.path.abspath(sys.argv[1]))          # data/（素材の表の隣に tex/）
from uv import uv as _uv, RW as _RW
TEX_DIR = os.path.join(os.path.dirname(IMG_DIR), 'textures')      # Rhino 版のある所の textures/
TEX = {}                                                           # 種類 → (絵の場所, 幅の向きの mm, 長さの向きの mm)
TEX_DIRS = SPEC.get('texture_dir', [])
SKIN_LAYER = '床の絵（テクスチャを貼った板、materials.py が作り直しのたびに）'
SKIN_OFF = 1.0                                                     # 床の上面から
SKINS = []                                                         # メッシュの版から写す板：(メッシュ, 素材の名前, もとのレイヤー)
PLAIN = '（絵なし）'


def texture_images():
    os.makedirs(TEX_DIR, exist_ok=True)
    for kind in sorted({v['texture'] for v in MATS.values() if v.get('texture')}):
        p = os.path.join(TEX_DIR, TX.FILES[kind]); w, l = TX.MAKERS[kind](p); TEX[kind] = (p, w, l)


def set_texture(a, spec):
    if spec.get('texture'):
        a.SetBitmapTexture(TEX[spec['texture']][0])                # 旧来の Bitmap ＝物理ベースの Base color（返り値は成り立っても False）


def tex_dir(layer_name, spec):
    for pre, d in TEX_DIRS:
        if layer_name.startswith(pre):
            return d
    return spec.get('dir', 'v')


def tex_mapper_angle(kind, ang):
    """本館係の tex_angle（度、ワールドの X から反時計回り＝板の長さの向き）があるとき：その向きの平面で本当の寸法に"""
    _, w, l = TEX[kind]
    t = math.radians(ang); al = np.array([math.cos(t), math.sin(t)]); ac = np.array([-al[1], al[0]])

    def f(Q):
        X = np.asarray(Q)[:, :2]
        return np.stack([X @ ac / w, X @ al / l], 1)
    return f


def tex_mapper(P, kind, d):
    """物の頂点 P（mm）から、点 → テクスチャ座標の関数を作る。絵の横＝板の幅の向き、縦＝板の長さの向き。
    本当の寸法（1 枚の絵＝TEX の mm）。弧の長さは物の真ん中の半径で測る（板の幅は物の真ん中で 135）"""
    vmid = np.median([_uv(x, y)[1] for x, y in P[:, :2]]) * 1000.0
    k = (_RW - vmid) / _RW
    _, w, l = TEX[kind]

    def f(Q):
        U = np.array([_uv(x, y) for x, y in np.asarray(Q)[:, :2]]) * 1000.0
        along_arc = U[:, 0] * k
        across, along = (along_arc, U[:, 1]) if d == 'v' else (U[:, 1], along_arc)
        return np.stack([across / w, along / l], 1)
    return f


def set_uv(g, T):
    tc = g.TextureCoordinates
    n0 = len(tc)
    for i, (a, b) in enumerate(T):
        if i < n0: tc[i] = r.Point2f(float(a), float(b))
        else: tc.__add__(float(a), float(b))


SKIN_EDGE = 3000.0                                                 # 板の三角形の辺の長さの上限（弧の (u, v) をなめらかに追うため、長い三角形を割る）


def top_skin(g, T, fmap):
    """メッシュの上の面（水平な面のうち、真上に同じ物の水平な面が無いもの）だけを写した板。
    面の向き（巻き）は物によって内向きのことがあるので使わない。SKIN_OFF 上げ、上を向くように巻き直す。テクスチャ座標つき"""
    P = np.array([[p.X, p.Y, p.Z] for p in g.Vertices])
    tris = []
    for fi in range(len(g.Faces)):
        q = list(dict.fromkeys(tuple(g.Faces[fi])[:4]))
        if len(q) < 3: continue
        for t in ([q] if len(q) == 3 else [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]):
            A = P[t]; nrm = np.cross(A[1] - A[0], A[2] - A[0]); ln = np.linalg.norm(nrm)
            if ln > 0 and abs(nrm[2]) / ln > 0.95:
                tris.append(t if nrm[2] > 0 else [t[0], t[2], t[1]])
    if not tris: return None
    Tr = np.array(tris); A, B, C = P[Tr[:, 0]], P[Tr[:, 1]], P[Tr[:, 2]]
    cen = (A + B + C) / 3
    d = (B[:, 0] - A[:, 0]) * (C[:, 1] - A[:, 1]) - (B[:, 1] - A[:, 1]) * (C[:, 0] - A[:, 0])
    keep = []
    for i, c in enumerate(cen):
        # 重心の真上に、同じ物のほかの水平な三角形があるか（重心座標で中に入るか）。あれば下の面
        up = cen[:, 2] > c[2] + 0.5
        if up.any():
            j = np.where(up)[0]
            l1 = ((B[j, 0] - c[0]) * (C[j, 1] - c[1]) - (B[j, 1] - c[1]) * (C[j, 0] - c[0])) / d[j]
            l2 = ((C[j, 0] - c[0]) * (A[j, 1] - c[1]) - (C[j, 1] - c[1]) * (A[j, 0] - c[0])) / d[j]
            if ((l1 >= -1e-6) & (l2 >= -1e-6) & (l1 + l2 <= 1 + 1e-6)).any(): continue
        keep.append(i)
    # 長い三角形は辺の中点で四つに割る（メッシュの版の細長い三角形のままだと、弧に沿う板が三角形の中でゆがむ）
    pts = [tuple(p) for p in P]; key = {}
    def mid(a, b):
        k_ = (min(a, b), max(a, b))
        if k_ not in key:
            key[k_] = len(pts); pts.append(tuple((np.array(pts[a]) + np.array(pts[b])) / 2))
        return key[k_]
    out, stack = [], [list(map(int, Tr[i])) for i in keep]
    while stack:
        a, b, c = stack.pop()
        A, B, C = (np.array(pts[i]) for i in (a, b, c))
        if max(np.linalg.norm(A - B), np.linalg.norm(B - C), np.linalg.norm(C - A)) <= SKIN_EDGE:
            out.append((a, b, c)); continue
        ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
        stack += [[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]]
    PP = np.array(pts)
    TT = np.vstack([T, fmap(PP[len(P):])]) if len(PP) > len(P) else T
    S = r.Mesh(); vmap = {}
    for tri in out:
        ids = []
        for vi in tri:
            if vi not in vmap:
                vmap[vi] = len(vmap); S.Vertices.Add(float(PP[vi, 0]), float(PP[vi, 1]), float(PP[vi, 2] + SKIN_OFF))
                S.TextureCoordinates.__add__(float(TT[vi, 0]), float(TT[vi, 1]))
            ids.append(vmap[vi])
        S.Faces.AddFace(ids[0], ids[1], ids[2])
    if not len(S.Faces): return None
    S.Normals.ComputeNormals()
    return S


def add_skins(m, mat_index):
    """Rhino 版に、メッシュの版から写した絵の板を足す（前の板は消してから）→ 板の数"""
    for o in [o for o in m.Objects if o.Attributes.GetUserString('tex_of')]:
        m.Objects.Delete(o.Attributes.Id)
    if not SKINS: return 0
    li = next((i for i, L in enumerate(m.Layers) if L.Name == SKIN_LAYER), None)
    if li is None:
        L = r.Layer(); L.Name = SKIN_LAYER; L.Color = (212, 178, 132, 255); li = m.Layers.Add(L)
    m.Layers[li].Locked = True                                    # 選ぶときは下の床のポリサーフェスが取れるように
    n = 0
    for S, name, src_layer in SKINS:
        a = r.ObjectAttributes(); a.LayerIndex = li; a.Name = f'床の絵：{src_layer}'
        a.MaterialSource = r.ObjectMaterialSource.MaterialFromObject; a.MaterialIndex = mat_index(name, (212, 178, 132))
        a.SetUserString('tex_of', src_layer)
        m.Objects.AddMesh(S, a); n += 1
    return n


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


# 作り直しの印（設計監修、10-28。ユーザー：ビルドに入っていない段階で同じ直しを何回も頼んだ）：どの commit から作ったかを
# 3dm に書く。Rhino で「どこまで入っているか」を見るため。文書のユーザーテキスト（DocumentUserText の「作り直し」）と、
# Rhino版にはレイヤー「N 番号」に文字の点（TextDot、南の妻の南 z 10 m）。作り直すたびに前の点は消して置き直す。
import subprocess, datetime


def _build_info():
    try:
        sha = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip()
    except Exception:
        sha = ''
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%m-%d %H:%M')
    return f'{sha or "?"}まで（{now} 作り直し）'


BUILD = _build_info()


def stamp(m):
    m.Strings['作り直し'] = BUILD
    li = next((i for i, L in enumerate(m.Layers) if L.Name.startswith('N ')), None)
    if li is None:
        return                                                      # メッシュの版（番号のレイヤーが無い）は文書のテキストだけ
    for o in list(m.Objects):
        if o.Attributes.GetUserString('build_stamp'):
            m.Objects.Delete(o.Attributes.Id)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from uv import xy
    x, y = xy(-3.0, 7.0)
    a = r.ObjectAttributes(); a.LayerIndex = li; a.Name = '作り直しの印'; a.SetUserString('build_stamp', BUILD)
    m.Objects.AddTextDot('作り直し：' + BUILD, r.Point3d(x, y, 10000.0), a)


def apply(path):
    m = r.File3dm.Read(path)
    # その場で書き換える（グループ・親子のレイヤー・物の属性を失わないため）。同じ名前の素材があれば使い回す
    have = {mt.Name: i for i, mt in enumerate(m.Materials)}
    idx = {}

    def mat_index(name, layer_color, plain=False):
        if plain:                                                    # Rhino 版の床のポリサーフェス：同じ色で絵なし
            label = name + PLAIN
            if label not in idx:
                sp = {k: v for k, v in MATS[name].items() if k != 'texture'}
                idx[label] = have[label] if label in have else m.Materials.Add(make(label, sp, layer_color))
            return idx[label]
        if name not in MATS:                                         # 表に無い素材の名前（10-28：17k で作り直しが止まった）は止めずに知らせ、レイヤーの色の素材で
            print(f'! materials: 素材の表に無い名前「{name}」（data/materials.json の materials に足す）')
            MATS[name] = {'base': 'layer', 'roughness': 0.7}
        label = name if MATS[name]['base'] != 'layer' else f'{name}：{layer_color[0]},{layer_color[1]},{layer_color[2]}'
        if label not in idx:
            idx[label] = have[label] if label in have else m.Materials.Add(make(label, MATS[name], layer_color))
            if label in have: set_texture(m.Materials[idx[label]], MATS[name])   # 前の作り直しの素材にも絵を
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
        elif used.get(i) and L.Name != SKIN_LAYER:
            missing.append(L.Name)
    count = {}
    ntex = nplain = 0
    for o in m.Objects:
        a = o.Attributes
        if a.GetUserString('tex_of'): continue                     # 前に足した床の絵の板（下の add_skins で作り直す）
        if a.GetUserString('etch_of'): continue                    # 前に足したロゴの板（下の add_etch で作り直す）
        L = layers[a.LayerIndex]
        rule = rule_for(L.Name) if L.Name != SKIN_LAYER else None
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
        sp = MATS.get(name, {})
        if sp.get('texture'):
            g = o.Geometry
            if isinstance(g, r.Mesh):                                # メッシュの版：頂点にテクスチャ座標
                P = np.array([[p.X, p.Y, p.Z] for p in g.Vertices])
                ang = a.GetUserString('tex_angle')                   # 本館係の向き（10-31）があればそれ、無ければ場所から
                fmap = (tex_mapper_angle(sp['texture'], float(ang)) if ang else tex_mapper(P, sp['texture'], tex_dir(L.Name, sp))); T = fmap(P)
                set_uv(g, T); ntex += 1
                S = top_skin(g, T, fmap)
                if S is not None: SKINS.append((S, name, L.Name))
            elif isinstance(g, (r.Brep, r.Extrusion)):               # Rhino 版：絵なしの同じ色に（絵は上に足す板で）
                a.MaterialSource = r.ObjectMaterialSource.MaterialFromObject
                a.MaterialIndex = mat_index(name, L.Color, plain=True); nplain += 1
    emb = set(m.EmbeddedFilePaths())
    for p, _, _ in TEX.values():
        if p not in emb: m.EmbeddedFiles.Add(r.EmbeddedFile.Read(p))
    nskin = add_skins(m, mat_index) if nplain else 0
    ne = add_etch(m, layers, mat_index)
    stamp(m)
    m.Write(os.path.abspath(path), 8)                              # 絶対の場所で書く（絵の場所を 3dm からの相対でも残すため）
    print(f'materials: {path.split("/")[-1]}：素材 {len(idx)}・物 {len(m.Objects)}・ガラスのロゴの板 {ne}'
          + (f'・床の絵：座標 {ntex}' if ntex else '') + (f'・床の絵の板 {nskin}（絵なしにした床 {nplain}）' if nplain else '')
          + (f'・素材なし {len(missing)}（{"、".join(missing[:8])}）' if missing else ''))
    return count


logo_images()
texture_images()
for p in sys.argv[2:]:
    apply(p)
