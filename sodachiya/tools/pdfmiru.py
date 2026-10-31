#!/usr/bin/env python3
"""図面 PDF を画像を見ずに確かめる道具（効率化委員会、10-31）。トークンを節約するため、まず文字で調べ、要るときだけ画像で見る。

  python3 tools/pdfmiru.py <pdf>                          ページ数と各ページの大きさ（mm）
  python3 tools/pdfmiru.py moji <pdf> [--page N] [--grep 語] [--box x0,y0,x1,y1]
                                                          文字の一覧（位置・フォント・大きさ pt）。60行まで、残りは件数
  python3 tools/pdfmiru.py font <pdf>                     使われているフォントと埋め込み・種別（TrueType=Type42 / Type3）
  python3 tools/pdfmiru.py kasanari <pdf> [--page N]      重なっている文字の組（ぶつかり）
  python3 tools/pdfmiru.py kiri <pdf> --box x0,y0,x1,y1 [--page N] [--dpi D] [-o out.png]
                                                          その長方形だけを PNG に（既定 /tmp/claude-0/pdfmiru_*.png、長辺1600px以内）

座標：すべて mm、シート（ページ）の左下が原点、x は右へ、y は上へ。ページ番号は 1 から（既定 1）。
  moji は同じ行・同じフォント・同じ大きさで続く文字を一つにまとめる（字間が大きさの0.6倍を超えると別）。
  縦書き・回転した文字は一文字ずつ別になることがある。
  kasanari は moji と同じまとまりの外接長方形どうしの重なり（0.2 mm 以上）。同じ文字の重ね打ちも出る。
読むだけ。PDF は変わらない。
"""
import os, subprocess, sys, tempfile
from collections import defaultdict

PT = 25.4 / 72
CAP = 60


def mm(v):
    return v * PT


def pages_of(pdf, a):
    n = len(pdf.pages)
    if a.get('page'):
        p = int(a['page'])
        if not 1 <= p <= n:
            sys.exit(f"ページは 1〜{n}")
        return [(p, pdf.pages[p - 1])]
    return [(1, pdf.pages[0])] if 'kiri' == a['cmd'] else list(enumerate(pdf.pages, 1))


def parse_box(s):
    try:
        b = [float(x) for x in s.split(',')]
        assert len(b) == 4 and b[0] < b[2] and b[1] < b[3]
        return b
    except Exception:
        sys.exit("--box は x0,y0,x1,y1（mm、左下原点、x0<x1、y0<y1）")


def blocks(page):
    """文字をまとめて [(text, x0, y0, x1, y1, font, size)]（mm、左下原点）にする。"""
    H = float(page.height)
    rows = defaultdict(list)
    for c in page.chars:
        t = c['text']
        if not t.strip():
            continue
        up = c.get('upright', True)
        key = (up, c['fontname'], round(c['size'], 1), round(c['bottom'] if up else c['x0'], 0))
        rows[key].append(c)
    out = []
    for (up, fn, sz, _), cs in rows.items():
        cs.sort(key=(lambda c: c['x0']) if up else (lambda c: -c['bottom']))
        cur = [cs[0]]
        groups = [cur]
        for c in cs[1:]:
            p = cur[-1]
            gap = c['x0'] - p['x1'] if up else p['top'] - c['bottom']
            if gap > 0.6 * sz or gap < -sz * 1.5:
                cur = [c]; groups.append(cur)
            else:
                cur.append(c)
        for g in groups:
            x0 = min(c['x0'] for c in g); x1 = max(c['x1'] for c in g)
            t0 = min(c['top'] for c in g); t1 = max(c['bottom'] for c in g)
            out.append((''.join(c['text'] for c in g), mm(x0), mm(H - t1), mm(x1), mm(H - t0),
                        fn.split('+')[-1], sz))
    out.sort(key=lambda b: (-round(b[2]), b[1]))
    return out


def cmd_moji(pdf, a):
    box = parse_box(a['box']) if a.get('box') else None
    rows = []
    for pn, pg in pages_of(pdf, a):
        for t, x0, y0, x1, y1, fn, sz in blocks(pg):
            if a.get('grep') and a['grep'] not in t:
                continue
            if box and not (x1 >= box[0] and x0 <= box[2] and y1 >= box[1] and y0 <= box[3]):
                continue
            rows.append(f"p{pn} ({x0:.1f},{y0:.1f})-({x1:.1f},{y1:.1f}) {fn} {sz:.1f}pt 「{t}」")
    print('\n'.join(rows[:CAP]))
    print(f"全部で {len(rows)} 件" + (f"（残り {len(rows) - CAP} 件は省略。--grep か --box で絞る）" if len(rows) > CAP else ''))


def cmd_font(pdf, a):
    seen = {}
    for pn, pg in enumerate(pdf.pages, 1):
        fonts = (pg.page_obj.resources or {}).get('Font')
        fonts = fonts.resolve() if hasattr(fonts, 'resolve') else (fonts or {})
        for k, ref in fonts.items():
            f = ref.resolve() if hasattr(ref, 'resolve') else ref
            st = f.get('Subtype'); st = getattr(st, 'name', str(st))
            bf = f.get('BaseFont'); bf = getattr(bf, 'name', str(bf)).split('+')[-1]
            emb = False
            subs = [f]
            for d in (f.get('DescendantFonts') or []):
                d = d.resolve() if hasattr(d, 'resolve') else d
                subs += d if isinstance(d, list) else [d]
            for s in subs:
                s = s.resolve() if hasattr(s, 'resolve') else s
                fd = s.get('FontDescriptor')
                fd = fd.resolve() if hasattr(fd, 'resolve') else fd
                if fd and any(x in fd for x in ('FontFile', 'FontFile2', 'FontFile3')):
                    emb = True
                if st != 'Type0' and hasattr(s.get('Subtype'), 'name'):
                    pass
            kind = {'Type3': 'Type3', 'TrueType': 'TrueType(Type42)', 'Type0': 'Type0(CID)',
                    'Type1': 'Type1'}.get(st, st)
            if st == 'Type0':
                ds = [(d.resolve() if hasattr(d, 'resolve') else d) for d in f.get('DescendantFonts', [])]
                ds = [x.get('Subtype') for x in (ds[0] if ds and isinstance(ds[0], list) else ds)]
                if ds and getattr(ds[0], 'name', '') == 'CIDFontType2':
                    kind = 'Type0/TrueType(Type42)'
            s = seen.setdefault((bf, kind, emb), set()); s.add(pn)
    for (bf, kind, emb), ps in sorted(seen.items()):
        pl = ','.join(map(str, sorted(ps)))
        print(f"{bf}  {kind}  {'埋め込み' if emb else '埋め込み無し'}  p{pl if len(pl) < 30 else pl[:27] + '…'}")
    if any(k == 'Type3' for _, k, _ in seen):
        print("注意：Type3 がある（文字が図形になり、文字として選べない・検索できない）")
    if not seen:
        print("フォント無し")


def cmd_kasanari(pdf, a):
    rows = []
    for pn, pg in pages_of(pdf, a):
        bs = blocks(pg)
        bs.sort(key=lambda b: b[1])
        for i, p in enumerate(bs):
            for q in bs[i + 1:]:
                if q[1] >= p[3] - 0.2:
                    break
                ox = min(p[3], q[3]) - max(p[1], q[1]); oy = min(p[4], q[4]) - max(p[2], q[2])
                if ox > 0.2 and oy > 0.2:
                    rows.append((ox * oy, f"p{pn} 「{p[0][:20]}」({p[1]:.1f},{p[2]:.1f})-({p[3]:.1f},{p[4]:.1f}) × "
                                 f"「{q[0][:20]}」({q[1]:.1f},{q[2]:.1f})-({q[3]:.1f},{q[4]:.1f}) 重なり {ox:.1f}×{oy:.1f}mm"))
    rows.sort(key=lambda r: -r[0])
    print('\n'.join(r[1] for r in rows[:CAP]))
    print(f"重なり {len(rows)} 組" + (f"（大きい順に {CAP} 組まで）" if len(rows) > CAP else ''))


def cmd_kiri(pdf, a):
    if not a.get('box'):
        sys.exit("--box x0,y0,x1,y1（mm）が要る")
    x0, y0, x1, y1 = parse_box(a['box'])
    pn, pg = pages_of(pdf, a)[0]
    W, H = float(pg.width) * PT, float(pg.height) * PT
    x0, x1 = max(0, x0), min(W, x1); y0, y1 = max(0, y0), min(H, y1)
    if x0 >= x1 or y0 >= y1:
        sys.exit(f"箱がページの外（ページは {W:.0f}×{H:.0f} mm）")
    long_mm = max(x1 - x0, y1 - y0)
    dpi = int(a['dpi']) if a.get('dpi') else max(20, min(300, int(1600 / (long_mm / 25.4))))
    while long_mm / 25.4 * dpi > 1600 and dpi > 20:
        dpi -= 1
    out = a.get('o') or f"/tmp/claude-0/pdfmiru_p{pn}_{int(x0)}_{int(y0)}_{int(x1)}_{int(y1)}.png"
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    px = lambda v: int(round(v / 25.4 * dpi))
    r = subprocess.run(['pdftoppm', '-png', '-singlefile', '-r', str(dpi), '-f', str(pn), '-l', str(pn),
                        '-x', str(px(x0)), '-y', str(px(H - y1)), '-W', str(px(x1 - x0)), '-H', str(px(y1 - y0)),
                        a['pdf'], out[:-4] if out.endswith('.png') else out], capture_output=True, text=True)
    if r.returncode:
        sys.exit(r.stderr.strip())
    print(f"{out}  {px(x1 - x0)}×{px(y1 - y0)}px  {dpi}dpi  p{pn} ({x0:.0f},{y0:.0f})-({x1:.0f},{y1:.0f})mm")


def cmd_info(pdf, a):
    for i, pg in enumerate(pdf.pages, 1):
        if i > 30:
            print(f"…（残り {len(pdf.pages) - 30} ページ）"); break
        print(f"p{i}: {float(pg.width) * PT:.0f}×{float(pg.height) * PT:.0f} mm")
    print(f"全部で {len(pdf.pages)} ページ")


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ('-h', '--help'):
        print(__doc__); return 2
    cmds = {'moji': cmd_moji, 'font': cmd_font, 'kasanari': cmd_kasanari, 'kiri': cmd_kiri}
    cmd = argv.pop(0) if argv[0] in cmds else 'info'
    a = {'cmd': cmd}
    opts = {'--page': 'page', '--grep': 'grep', '--box': 'box', '--dpi': 'dpi', '-o': 'o'}
    i = 0
    while i < len(argv):
        if argv[i] in opts and i + 1 < len(argv):
            a[opts[argv[i]]] = argv[i + 1]; i += 2
        elif 'pdf' not in a:
            a['pdf'] = argv[i]; i += 1
        else:
            sys.exit(f"分からない引数：{argv[i]}")
    if 'pdf' not in a:
        print(__doc__); return 2
    import pdfplumber
    with pdfplumber.open(a['pdf']) as pdf:
        (cmds.get(cmd) or cmd_info)(pdf, a)
    return 0


if __name__ == '__main__':
    sys.exit(main())
