#!/usr/bin/env python3
"""3dm を絵で見る・二つを並べて比べる（効率化委員会、10-31）。使い捨ての描画スクリプトを書かずに、まずこれで見る。

  python3 tools/kuraberu.py sw                              既定の 3dm を南西の上から（PNG、長い辺1600 px以下）
  python3 tools/kuraberu.py nishi --an /tmp/claude-0/out/preview/model/sodachiya_exact_mesh.3dm
                                                            左に「今」（既定の 3dm）、右に「案」を同じ向きで並べる
  python3 tools/kuraberu.py nishi_yane --layers 20,21,22    レイヤーを絞る（hakaru.py と同じ選び方）
  python3 tools/kuraberu.py sw --box 20,52,-16,0            u・v（,z）の範囲の三角形だけ描く（切った断面のようにも使える）
  python3 tools/kuraberu.py --list                          見る場所の一覧（tools/views.json）

  --file F   「今」のファイル（既定 model/sodachiya_exact_mesh.3dm）
  --an F     「案」のファイル（付けると左右に並べる）
  --hide 03,04   消すレイヤーの番号の頭（既定は views.json の hide、無ければ 03,04＝周辺の道路・建物）
  --out P    書き出す PNG（既定 /tmp/claude-0/out/kuraberu_<見る場所>.png）
  --eye u,v,z --tgt u,v,z [--ortho 半幅 | --fov 度]   views.json に無い向きをその場で

描くのは model/build/view/ の道具（3dm → glb → three.js をヘッドレスの chromium で）。先に一度
bash model/build/setup.sh（/tmp/claude-0/t/view に node の道具が入る）。色はレイヤー（物）の色、ガラスは半透明。
線（曲線）は描かない。見えない（非表示の）レイヤーは --layers で名指ししたときだけ描く。
座標は hakaru.py と同じ u・v・z（m、本館の背骨の弧）。読むだけ。3dm は変わらない。
同じ時に二つ走らせない（描画の小さなサーバーが同じ口 8765 を使う）。
"""
import argparse, json, os, re, subprocess, sys, tempfile
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import hakaru  # noqa: E402  （u・v の変換・レイヤーの選び方・三角形）
from uv import xy  # noqa: E402

VIEWS = os.path.join(HERE, 'views.json')
VDIR = '/tmp/claude-0/t/view'          # setup.sh が node_modules を入れる所（render.js と page.html もここ）


def world(p):
    """[u, v, z]（m）→ 世界座標（m）"""
    x, y = xy(p[0], p[1]) / 1000.0
    return [float(x), float(y), float(p[2])]


def to_glb(path, out, layers, hide, box):
    import rhino3dm as r, trimesh
    m = r.File3dm.Read(path)
    LA = hakaru.pick_layers(m, layers) if layers else None
    hid = [h for h in hide.split(',') if h] if hide else []
    groups, ntri = {}, 0
    for o in m.Objects:
        li = o.Attributes.LayerIndex; L = m.Layers[li]; ln = L.Name
        if LA is not None:
            if li not in LA: continue
        elif not L.Visible or any(hakaru.code(ln).startswith(h) for h in hid):
            continue
        T, _ = hakaru.tris(o.Geometry)
        if T is None or len(T) == 0: continue
        T = np.asarray(T, float)
        if box is not None:
            Q = hakaru.uv_arr(T.mean(1))
            k = (Q[:, 0] >= box[0]) & (Q[:, 0] <= box[1]) & (Q[:, 1] >= box[2]) & (Q[:, 1] <= box[3])
            if len(box) == 6: k &= (Q[:, 2] >= box[4]) & (Q[:, 2] <= box[5])
            T = T[k]
            if not len(T): continue
        c = o.Attributes.ObjectColor if o.Attributes.ColorSource == r.ObjectColorSource.ColorFromObject else L.Color
        groups.setdefault(ln, []).append((T.reshape(-1, 3) / 1000.0, c))
        ntri += len(T)
    scene = trimesh.Scene()
    for ln, items in groups.items():
        V = np.vstack([v for v, _ in items])
        C = np.vstack([np.tile([c[0], c[1], c[2], 255], (len(v), 1)) for v, c in items])
        F = np.arange(len(V)).reshape(-1, 3)
        tm = trimesh.Trimesh(V[:, [0, 2, 1]] * [1, 1, -1], F[:, ::-1], vertex_colors=C, process=False)
        scene.add_geometry(tm, node_name=re.sub(r'[^0-9A-Za-z_]', '', hakaru.code(ln)) + '|' + ln, geom_name=ln)
    if not groups:
        return 0, 0
    scene.export(out)
    return len(groups), ntri


def font(size):
    from PIL import ImageFont
    for f in ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
              '/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc'):
        if os.path.exists(f): return ImageFont.truetype(f, size)
    try:
        out = subprocess.run(['fc-match', '-f', '%{file}', 'Noto Sans CJK JP'], capture_output=True, text=True).stdout
        return ImageFont.truetype(out, size)
    except Exception:
        return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument('view', nargs='?')
    ap.add_argument('--file', default=hakaru.DEFAULT)
    ap.add_argument('--an')
    ap.add_argument('--layers'); ap.add_argument('--hide'); ap.add_argument('--box')
    ap.add_argument('--eye'); ap.add_argument('--tgt'); ap.add_argument('--ortho', type=float); ap.add_argument('--fov', type=float)
    ap.add_argument('--out'); ap.add_argument('--list', action='store_true')
    ap.add_argument('-h', '--help', action='store_true')
    a = ap.parse_args()
    VS = {k: v for k, v in json.load(open(VIEWS, encoding='utf-8')).items() if not k.startswith('_')}
    if a.list:
        for k, v in VS.items(): print(f"{k:12s} {v.get('名', '')}")
        return 0
    if a.help or not (a.view or a.eye):
        print(__doc__); return 2
    if a.view and a.view not in VS:
        print(f"見る場所「{a.view}」が無い。一覧：python3 tools/kuraberu.py --list"); return 1
    V = dict(VS.get(a.view, {})) if a.view else {}
    if a.eye: V['eye'] = [float(x) for x in a.eye.split(',')]
    if a.tgt: V['tgt'] = [float(x) for x in a.tgt.split(',')]
    if a.ortho: V['ortho'] = a.ortho; V.pop('fov', None)
    if a.fov: V['fov'] = a.fov; V.pop('ortho', None)
    if 'eye' not in V or 'tgt' not in V:
        print("--eye と --tgt の両方が要る"); return 2
    box = [float(x) for x in a.box.split(',')] if a.box else V.get('box')
    hide = a.hide if a.hide is not None else V.get('hide', '03,04')
    if not os.path.exists(os.path.join(VDIR, 'node_modules')):
        print(f"描画の道具が無い（{VDIR}/node_modules）。先に bash model/build/setup.sh"); return 1
    files = [('今', a.file)] + ([('案', a.an)] if a.an else [])
    for _, f in files:
        if not os.path.exists(f): print(f"ファイルが無い：{f}"); return 1
    name = a.view or 'kuraberu'
    out = a.out or f"/tmp/claude-0/out/kuraberu_{name}.png"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    W, H = (800, 640) if a.an else (1600, 1000)
    tmp = tempfile.mkdtemp(prefix='kuraberu_')
    shots, tag = [], f"k{os.getpid()}"
    for i, (lab, f) in enumerate(files):
        g = os.path.join(VDIR, f"{tag}_{i}.glb")
        nl, nt = to_glb(f, g, a.layers, hide, box)
        if not nl:
            print(f"{lab}：描く物が無い（--layers・--box を見直す）"); return 1
        print(f"{lab}：{os.path.basename(f)}　レイヤー{nl}・三角形{nt}")
        v = {'glb': os.path.basename(g), 'eye': world(V['eye']), 'tgt': world(V['tgt']),
             'w': W, 'h': H, 'out': os.path.join(tmp, f"{i}.png")}
        if 'ortho' in V:   # 並べるときは横の幅を一枚のときと同じに
            v['ortho'] = V['ortho'] * ((1600 / 1000) / (W / H) if a.an else 1)
        else: v['fov'] = V.get('fov', 40)
        if 'clipz' in V: v['clipz'] = V['clipz']
        shots.append(v)
    vj = os.path.join(tmp, 'views.json'); json.dump(shots, open(vj, 'w'))
    p = subprocess.run(['node', os.path.join(VDIR, 'render.js'), vj], capture_output=True, text=True, timeout=600)
    for v in shots:
        try: os.remove(os.path.join(VDIR, v['glb']))
        except OSError: pass
    if p.returncode != 0 or not all(os.path.exists(v['out']) for v in shots):
        print("描画が止まった：", (p.stderr or p.stdout).strip().splitlines()[-3:]); return 1
    from PIL import Image, ImageDraw
    ims = [Image.open(v['out']).convert('RGB') for v in shots]
    top = 36
    img = Image.new('RGB', (sum(i.width for i in ims), ims[0].height + top), 'white')
    d = ImageDraw.Draw(img); fn = font(20); x = 0
    title = V.get('名', '') or f"eye {V['eye']} tgt {V['tgt']}"
    for (lab, f), im in zip(files, ims):
        img.paste(im, (x, top))
        d.text((x + 10, 6), f"{lab}：{os.path.basename(f)}" if a.an else title, fill='black', font=fn)
        x += im.width
        if a.an and x < img.width: d.line([(x, 0), (x, img.height)], fill='#888888', width=2)
    if a.an:
        d.text((10, img.height - 30), title, fill='#444444', font=font(18))
    s = min(1.0, 1600 / max(img.size))
    if s < 1: img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    img.save(out)
    print(f"絵：{out}（{img.width}×{img.height}）")
    return 0


if __name__ == '__main__':
    sys.exit(main())
