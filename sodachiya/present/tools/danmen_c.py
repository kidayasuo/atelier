# -*- coding: utf-8 -*-
"""6枚目の断面図C を「純然たる図面」の素材にする（ユーザー 11-04 12:23）。

中身は図の線と寸法・高さの記号・通り芯（W・E）・図名と方位だけ。換気の矢印・注、空気の色などは入れない（木田さんが自分で足す）。
- 図の線：drawings_rhino/sodachiya_sections_1-100.svg（rhino/zumen.py、Rhino のレイヤーの組のまま）の、断面C の範囲
  （drawings/sodachiya_sections_1-100_views.json の clip_paper_mm、紙の上 mm、左上が原点）にかかる要素だけを残す（外の要素は消す）。
- 寸法と高さの記号：model/build/south/draw100.py（更新係の持ち物、ファイルは変えない）を読み込んで、断面C の寸法と高さの記号を
  描く関数だけを呼ぶ。描く関数を包んで、呼ばれるたびに描いた物をひとまとめにし（寸法ごと・▽ごと）、SVG の <g> にする。
  数・置き場所は draw100 のまま。寸法の列（chain_dims）は区間ごとに分けて呼ぶ（同じ線・同じ位置、端の黒丸は両側の組に入る）。
- 二つは同じ紙の座標（mm、左上が原点）。matplotlib の SVG（pt）は 25.4/72 倍して mm に合わせる。
- 書体：ヒラギノ角ゴシック（'HiraginoSans-W3'、図名は 'HiraginoSans-W6'）。文字は文字のまま（svg.fonttype none）。

  python3 present/tools/danmen_c.py        → present/sozai/35_断面C_図面.svgz（gzip、mtime=0）と /tmp/claude-0/danmenC_check.png
"""
import gzip, io, json, os, re, sys, copy
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
D100 = os.path.join(ROOT, 'model', 'build', 'south', 'draw100.py')
MODEL = os.path.join(ROOT, 'model', 'sodachiya_exact_mesh.3dm')
RHINO_SVG = os.path.join(ROOT, 'drawings_rhino', 'sodachiya_sections_1-100.svg')
VIEWS = os.path.join(ROOT, 'drawings', 'sodachiya_sections_1-100_views.json')
OUT = os.path.join(ROOT, 'present', 'sozai', '35_断面C_図面.svgz')
PNG = '/tmp/claude-0/danmenC_check.png'
TMP = '/tmp/claude-0/danmenC_tmp'
MARGIN = 10.0
MARGIN_L = 16.0                # 左は西館の高さの記号の字（最高高さ +8,427）が図の範囲の外へ出るので広く
W3, W6 = 'HiraginoSans-W3', 'HiraginoSans-W6'
SVGNS, INK = 'http://www.w3.org/2000/svg', 'http://www.inkscape.org/namespaces/inkscape'
ET.register_namespace('', SVGNS); ET.register_namespace('inkscape', INK)

VC = next(v for v in json.load(open(VIEWS, encoding='utf-8'))['views'] if v['name'] == '断面C')
CL, CT, CR, CB = VC['clip_paper_mm']


# ---------------------------------------------------------------- 1. draw100 で断面C の寸法と高さの記号を描く
def draw_annotations():
    """draw100 の頭（3dm の読み込み・関数）だけを読み込み、断面C の切り口を作ってから、寸法・高さ・通り芯・図名を描く。
    返り値：(図, [(組の種類, 組の名前, [アーティスト])])"""
    os.makedirs(TMP, exist_ok=True)
    os.environ['DRAW_ONLY'] = '__none__'            # 下の紙の作図はしない（関数だけを使う）
    sys.argv = [D100, MODEL, TMP]
    g = {'__name__': 'draw100', '__file__': D100}
    exec(compile(open(D100, encoding='utf-8').read(), D100, 'exec'), g)
    plt = g['plt']

    groups = []                                     # [種類, 名前, [アーティスト]]
    cur = {'g': None}
    def hook(ax):
        for nm in ('add_collection', 'add_patch', 'add_line'):
            f = getattr(ax, nm)
            def w(*a, _f=f, **k):
                art = _f(*a, **k)
                if cur['g'] is not None: cur['g'][2].append(art)
                return art
            setattr(ax, nm, w)
        ft = ax.text
        def wt(*a, **k):
            art = ft(*a, **k)
            if cur['g'] is not None: cur['g'][2].append(art)
            return art
        ax.text = wt

    def begin(kind, name=''):
        cur['g'] = [kind, name, []]; groups.append(cur['g'])
    def end(): cur['g'] = None

    # 寸法：hdim・vdim は一つの呼び出しが一つの寸法
    for fn in ('hdim', 'vdim'):
        orig = g[fn]
        def wrap(*a, _o=orig, **k):
            begin('寸法'); r = _o(*a, **k); end(); return r
        g[fn] = wrap
    # 寸法の列：区間ごとに分けて呼ぶ（draw100 の線・黒丸・寸法補助線・数字と同じ位置）
    orig_chain = g['chain_dims']
    def chain(A, xs, y, *a, **k):
        xs = sorted(xs)
        for p, q in zip(xs, xs[1:]):
            begin('寸法'); orig_chain(A, [p, q], y, *a, **k); end()
    g['chain_dims'] = chain
    # 高さの記号：level_marks は一度に幾つも描く。一つの記号は 線（▽）・線（水平）・字 の三つ
    orig_lv = g['level_marks']
    def lv(A, items, *a, **k):
        begin('高さ_tmp'); r = orig_lv(A, items, *a, **k); arts = groups.pop()[2]; end()
        assert len(arts) % 3 == 0, len(arts)
        for i in range(0, len(arts), 3):
            groups.append(['高さ', '', arts[i:i + 3]])
        return r
    g['level_marks'] = lv

    # 断面C の紙と図（make_sections と同じ置き場所）
    Sheet = g['Sheet']; SECTIONS = g['SECTIONS']
    nm, kind_, val, cap_ = SECTIONS[2]
    assert nm == 'C'
    W_, H_ = 841, 594
    S = Sheet(W_, H_, 'tmp')
    extX = (-17500, 21500, -2600, 10500)
    i = 1
    A = S.axes(30 + i * (390 + 15), H_ - 40 - 161 - 45 - 131, extX)
    hook(A.ax)
    A.insul_x = (-1e5, 13500); A.rafter_cut = True; A.dimrec = g['DIM_REC_C']
    th_ = g['theta_u'](val); u_r, u_t, p0 = g['section_frame'](th_)
    S.view(A, '断面C', 'section', origin=p0 + 205000 * u_r, right=-u_r, up=(0.0, 0.0, 1.0), view_dir=u_t,
           cut_plane_point=p0 + 205000 * u_r, cut_plane_normal=u_t, depth_mm=g['SEC_DEPTH'], u_mm=val)
    v = S.views[-1]
    assert all(abs(a - b) < 0.01 for a, b in zip(v['clip_paper_mm'], VC['clip_paper_mm'])), (v['clip_paper_mm'], VC['clip_paper_mm'])
    cutb = g['section_u'](A, th_)                   # 切り口（寸法・高さの値を読む元）。描いた線は使わない
    westx = min([b[0] for k, b in cutb.items() if k.startswith('21_')] or [-900])
    g['west_chain'](A, westx)
    for nm2, x in (('W', 0), ('E', 12000)):
        begin('通り芯', nm2)
        A.lines([[(x, -1550), (x, 9800)]], '40_通り芯', lw=0.09, color='#B03030', ls=(0, (10, 3, 2, 3)), z=2)
        A.bubble(x, -2000, nm2)
        end()
    g['levels'](A, cutb, 18500, westx < -2000)
    g['sec_dims_ew'](A, westx)                      # 換気（airflow）と西館の外壁の注（断面 B だけ）は呼ばない
    PT_TITLE, PT_NOTE = g['PT_TITLE'], g['PT_NOTE']
    begin('図名と方位', '図名')
    A.text(extX[0] + 300, extX[3] - 200, f'断面図 {nm}　1/100　{cap_}', PT_TITLE, '80_図名・縮尺・方位', ha='left', va='top'); end()
    begin('図名と方位', '西')
    A.text(extX[0] + 300, -2400, '← 西', PT_NOTE, '80_図名・縮尺・方位', ha='left', va='bottom'); end()
    begin('図名と方位', '東')
    A.text(16000, -2400, '東 →', PT_NOTE, '80_図名・縮尺・方位', ha='right', va='bottom'); end()
    groups[:] = [gr for gr in groups if gr[2]]
    return plt, S, groups


def label_of(arts):
    """組の中の字（寸法の値・高さの名前と値）"""
    for a in arts:
        if a.__class__.__name__ == 'Text': return a.get_text()
    return ''


def annotations_svg():
    plt, S, groups = draw_annotations()
    fig = S.fig
    keep = set()
    n = {'寸法': 0, '高さ': 0}
    for gr in groups:
        kind, name, arts = gr
        if kind in n:
            n[kind] += 1
            t = label_of(arts)
            gr[1] = f'{kind}_{n[kind]:02d}_{t}'.replace(' ', '')
        else:
            gr[1] = f'{kind}_{name}'
        for j, a in enumerate(arts):
            a.set_gid(f'SDY{groups.index(gr):03d}__{j:02d}')
            a.set_clip_on(False); keep.add(id(a))
    for ax in fig.axes:
        ax.patch.set_visible(False)
        for a in ax.get_children():
            if id(a) not in keep: a.set_visible(False)
    for a in list(fig.patches) + list(fig.texts): a.set_visible(False)
    fig.patch.set_visible(False)
    plt.rcParams['svg.fonttype'] = 'none'
    plt.rcParams['svg.hashsalt'] = 'danmenC'
    buf = io.BytesIO(); fig.savefig(buf, format='svg', transparent=True); plt.close(fig)
    return ET.fromstring(buf.getvalue()), groups, (S.w, S.h)


# ---------------------------------------------------------------- 2. Rhino の線を断面C の範囲で切り出す
def _seg_hits(p, q, R):
    l, t, r, b = R
    (x0, y0), (x1, y1) = p, q
    if max(x0, x1) < l or min(x0, x1) > r or max(y0, y1) < t or min(y0, y1) > b: return False
    if l <= x0 <= r and t <= y0 <= b: return True
    if l <= x1 <= r and t <= y1 <= b: return True
    # 線分が矩形を横切るか（Liang–Barsky）
    dx, dy = x1 - x0, y1 - y0; u0, u1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - l), (dx, r - x0), (-dy, y0 - t), (dy, b - y0)):
        if pp == 0:
            if qq < 0: return False
        else:
            u = qq / pp
            if pp < 0: u0 = max(u0, u)
            else: u1 = min(u1, u)
            if u0 > u1: return False
    return True


def rhino_lines():
    tree = ET.parse(RHINO_SVG); root = tree.getroot()
    R = (CL, CT, CR, CB)
    stat = [0, 0]
    def prune(e):
        for k in list(e):
            if k.tag == f'{{{SVGNS}}}g':
                prune(k)
                if len(k) == 0: e.remove(k)
            elif k.tag in (f'{{{SVGNS}}}polyline', f'{{{SVGNS}}}polygon'):
                v = [float(s) for s in re.split(r'[\s,]+', k.get('points').strip())]
                P = list(zip(v[0::2], v[1::2]))
                if k.tag.endswith('polygon'): P.append(P[0])
                hit = any(_seg_hits(a, b, R) for a, b in zip(P, P[1:])) if len(P) > 1 else (P and _seg_hits(P[0], P[0], R))
                stat[0 if hit else 1] += 1
                if not hit: e.remove(k)
            elif k.tag == f'{{{SVGNS}}}line':
                p = (float(k.get('x1')), float(k.get('y1'))); q = (float(k.get('x2')), float(k.get('y2')))
                hit = _seg_hits(p, q, R); stat[0 if hit else 1] += 1
                if not hit: e.remove(k)
            else:
                raise RuntimeError('Rhino の SVG に知らない要素：' + k.tag)
    prune(root)
    print('Rhino の線：残す', stat[0], '消す', stat[1])
    return [k for k in root if k.tag == f'{{{SVGNS}}}g']


# ---------------------------------------------------------------- 3. 重ねて書く
def layer(id_, label=None):
    return ET.Element(f'{{{SVGNS}}}g', {'id': id_, f'{{{INK}}}groupmode': 'layer', f'{{{INK}}}label': label or id_})


def fix_fonts(el, bold=False):
    for t in el.iter(f'{{{SVGNS}}}text'):
        st = t.get('style', '')
        st = re.sub(r"font-family:\s*[^;]+", f"font-family: '{W6 if bold else W3}'", st)
        st = re.sub(r"font-weight:\s*[^;]+;?\s*", '', st)
        t.set('style', st)


def main():
    asvg, groups, (pw, ph) = annotations_svg()
    # matplotlib の SVG：id="SDY000__00" の <g> がアーティストごと。組ごとに集める
    found = {}
    def collect(e):
        for k in list(e):
            m = re.match(r'SDY(\d{3})__(\d{2})$', k.get('id') or '')
            if m: found.setdefault(int(m.group(1)), []).append((int(m.group(2)), k))
            else: collect(k)
    collect(asvg)
    defs = asvg.find(f'{{{SVGNS}}}defs')
    k_pt = 25.4 / 72.0                              # matplotlib の SVG（pt、左上が原点）→ 紙の mm
    tops = {nm: layer(nm) for nm in ('線（Rhino）', '寸法', '高さ', '通り芯', '図名と方位')}
    for gl in rhino_lines():
        tops['線（Rhino）'].append(gl)
    for i, (kind, name, arts) in enumerate(groups):
        els = [e for _, e in sorted(found.get(i, []))]
        if not els: continue
        G = ET.Element(f'{{{SVGNS}}}g', {'id': name, 'transform': f'scale({k_pt:.9f})'})
        for e in els:
            e.attrib.pop('id', None); G.append(e)
        fix_fonts(G, bold=(name == '図名と方位_図名'))
        tops[kind].append(G)
    W, H = CR - CL + MARGIN_L + MARGIN, CB - CT + 2 * MARGIN
    svg = ET.Element(f'{{{SVGNS}}}svg', {'width': f'{W:g}mm', 'height': f'{H:g}mm',
                                         'viewBox': f'{CL - MARGIN_L:g} {CT - MARGIN:g} {W:g} {H:g}', 'version': '1.1'})
    if defs is not None and len(defs): svg.append(defs)
    for nm in ('線（Rhino）', '寸法', '高さ', '通り芯', '図名と方位'):
        svg.append(tops[nm])
    data = b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(svg, encoding='utf-8')
    with open(OUT, 'wb') as f:
        with gzip.GzipFile(filename='', mode='wb', fileobj=f, mtime=0) as z: z.write(data)
    cnt = {nm: len(tops[nm]) for nm in tops}
    print('書いた', OUT, '組の数', cnt, 'text', data.count(b'<text'))
    # 確かめ用の PNG（白地、長辺 1600 px 以下）
    import subprocess
    s = data.replace(f"'{W3}'".encode(), b"'Noto Sans CJK JP'").replace(f"'{W6}'".encode(), b"'Noto Sans CJK JP'")
    r = subprocess.run(['rsvg-convert', '-w', '1600', '-b', 'white', '-o', PNG], input=s, capture_output=True)
    print('PNG', PNG if r.returncode == 0 else r.stderr.decode()[:300])


if __name__ == '__main__':
    main()
