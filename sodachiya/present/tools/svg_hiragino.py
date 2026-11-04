# -*- coding: utf-8 -*-
"""素材の PDF から、Illustrator で文字が文字のまま開ける SVG を作る（ユーザー 11-02）。

PDF を Illustrator で開くと「アピアランスを保持するため、一部のテキストがアウトライン化されました」が出た
（Noto 埋め込み・ヒラギノ参照・切り抜きの入れ子のどれでも）。試しの5つで警告が出なかったのは SVG（font-family にヒラギノ）だけ。
そこで素材は SVG でも渡す：
  - 線・面・切り抜きは PyMuPDF の SVG（get_svg_image）のまま。
  - 文字は <text> のまま。書体は Illustrator が書き出すのと同じ PostScript 名（'HiraginoSans-W3'、太字は 'HiraginoSans-W6'）。
  - 一字ずつの x の並びは、行の頭の一つにまとめる（Illustrator で一行が一つの文字になり、ヒラギノの字の送りで組まれる）。
PDF の書体は先に present/tools/hiragino.py でヒラギノ（HiraginoSans-W3・W6）にしておく（Noto のままでも太さで分ける）。

  python3 present/tools/svg_hiragino.py <pdf> [<pdf> ...]     同じ名前の .svgz（圧縮した SVG）を横に作る
"""
import gzip, os, re, sys, html
import fitz
import pikepdf

W3, W6 = "HiraginoSans-W3", "HiraginoSans-W6"


def _tag_fonts(src):
    """PyMuPDF の SVG は書体の名前の '-' から後ろを落とすので、太さが分かる名前に一時的に替えた PDF のバイト列を返す"""
    pdf = pikepdf.open(src)
    seen = set()

    def walk(res):
        if res is None:
            return
        for k, f in res.get("/Font", {}).items():
            if f.objgen in seen:
                continue
            seen.add(f.objgen)
            bf = str(f.get("/BaseFont", ""))
            bold = any(w in bf for w in ("W6", "W7", "W8", "Bold", "Black", "Medium"))
            tag = pikepdf.Name("/SDYW6" if bold else "/SDYW3")
            f.BaseFont = tag
            for d in f.get("/DescendantFonts", []):
                d.BaseFont = tag
                if "/FontDescriptor" in d:
                    d.FontDescriptor.FontName = tag
        for k, x in res.get("/XObject", {}).items():
            if x.get("/Subtype") == pikepdf.Name.Form:
                walk(x.get("/Resources"))
    for pg in pdf.pages:
        walk(pg.obj.get("/Resources"))
    import io
    b = io.BytesIO()
    pdf.save(b)
    return b.getvalue()


_TEXT = re.compile(r'(<text\b[^>]*?)font-family="([^"]*)"([^>]*>)(.*?)(</text>)', re.S)
_TSPAN_X = re.compile(r'(<tspan\b[^>]*?\bx=")([^"]*)(")')


def _fix_text(m):
    head, fam, rest, body, tail = m.groups()
    ps = W6 if "SDYW6" in fam else W3
    body = _TSPAN_X.sub(lambda t: t.group(1) + t.group(2).split()[0] + t.group(3) if t.group(2).split() else t.group(0), body)
    return '%sfont-family="\'%s\'"%s%s%s' % (head, ps, rest, body, tail)


_ONE = re.compile(r'<text\b([^>]*)><tspan y="([^"]*)" x="([^"]*)">(.*?)</tspan></text>', re.S)


def _merge(svg):
    """同じ行（同じ transform・大きさ・色・書体）で続く <text> を一つにまとめる。
    matplotlib は一行の中で欧文と和文の書体を切り替えるので、そのままだと一行が何個もの文字に分かれる"""
    out, last, pos = [], None, 0
    for m in _ONE.finditer(svg):
        gap = svg[pos:m.start()]
        attrs, y, x, body = m.groups()
        if last is not None and not gap.strip() and last[0] == attrs and last[1] == y:
            last[3] += body
        else:
            if last is not None:
                out.append('<text%s><tspan y="%s" x="%s">%s</tspan></text>' % tuple(last))
                last = None
            out.append(gap)
            last = [attrs, y, x, body]
        pos = m.end()
    if last is not None:
        out.append('<text%s><tspan y="%s" x="%s">%s</tspan></text>' % tuple(last))
    out.append(svg[pos:])
    return "".join(out)


_NUM = re.compile(r"-?\d*\.?\d+(?:[eE][-+]?\d+)?")


def _mat(t):
    """transform="matrix(a,b,c,d,e,f)" を (a,b,c,d,e,f) に（無ければ単位）"""
    if not t:
        return (1, 0, 0, 1, 0, 0)
    m = re.match(r"\s*matrix\(([^)]*)\)", t)
    if not m:
        return None
    v = [float(x) for x in _NUM.findall(m.group(1))]
    return tuple(v) if len(v) == 6 else None


def _mul(A, B):
    a, b, c, d, e, f = A
    a2, b2, c2, d2, e2, f2 = B
    return (a * a2 + c * b2, b * a2 + d * b2, a * c2 + c * d2, b * c2 + d * d2, a * e2 + c * f2 + e, b * e2 + d * f2 + f)


def _pts_path(d):
    """絶対座標の M L H V C Q Z だけを読む（PyMuPDF の SVG はこれだけ）。点の列"""
    pts, x, y, cmd = [], 0.0, 0.0, None
    toks = re.findall(r"[MLHVCQZmlhvcqz]|-?\d*\.?\d+(?:[eE][-+]?\d+)?", d)
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                continue
            continue
        if cmd in ("H",):
            x = float(t); i += 1
        elif cmd in ("V",):
            y = float(t); i += 1
        else:
            x, y = float(t), float(toks[i + 1]); i += 2
        pts.append((x, y))
    return pts


def _prune(svg):
    """紙（viewBox）の外にしかない物を消す。切り抜いた素材は紙全体の中身を持っていて、Illustrator は SVG の切り抜きを
    外してしまう（SVG Tiny の警告、11-04：紙の外の文や図が重なって見えた・マスクの画像が黒くなった）"""
    from lxml import etree
    root = etree.fromstring(svg.encode("utf-8"))
    ns = "{http://www.w3.org/2000/svg}"
    vb = [float(x) for x in root.get("viewBox").split()]
    X0, Y0, X1, Y1 = vb[0] - 2, vb[1] - 2, vb[0] + vb[2] + 2, vb[1] + vb[3] + 2
    gone = 0

    def walk(el, M):
        nonlocal gone
        for ch in list(el):
            tag = ch.tag.replace(ns, "") if isinstance(ch.tag, str) else ""
            if tag in ("defs", "clipPath", "mask", "metadata", "title", "style"):
                continue
            T = _mat(ch.get("transform"))
            if T is None:
                continue                                  # 読めない transform は残す
            M2 = _mul(M, T)
            if tag == "g" or tag == "a":
                walk(ch, M2)
                if len(ch) == 0:
                    el.remove(ch)
                continue
            if tag == "path":
                pts = _pts_path(ch.get("d", ""))
            elif tag == "image":
                w, h = float(ch.get("width", 0)), float(ch.get("height", 0))
                pts = [(0, 0), (w, 0), (0, h), (w, h)]
            elif tag == "text":
                xs = [float(v) for t in ch.iter(ns + "tspan") for v in _NUM.findall(t.get("x", "0"))] or [0.0]
                fs = float(ch.get("font-size", "10"))
                pts = [(min(xs), -fs), (max(xs) + fs * max(1, len("".join(ch.itertext()))), fs * 0.3)]
            else:
                continue
            if not pts:
                continue
            a, b, c, d, e, f = M2
            gx = [a * x + c * y + e for x, y in pts]
            gy = [b * x + d * y + f for x, y in pts]
            if max(gx) < X0 or min(gx) > X1 or max(gy) < Y0 or min(gy) > Y1:
                el.remove(ch)
                gone += 1
    walk(root, (1, 0, 0, 1, 0, 0))
    # 使われなくなった切り抜き・マスクを消す
    txt = etree.tostring(root).decode("utf-8")
    used = set(re.findall(r"url\(#([^)]+)\)", txt))
    for defs in root.iter(ns + "defs"):
        for d_ in list(defs):
            if d_.get("id") and d_.get("id") not in used and (d_.tag in (ns + "clipPath", ns + "mask")):
                defs.remove(d_)
    return etree.tostring(root, encoding="unicode"), gone


def convert(src, dst=None):
    dst = dst or os.path.splitext(src)[0] + ".svgz"
    doc = fitz.open(stream=_tag_fonts(src), filetype="pdf")
    svg = doc[0].get_svg_image(text_as_path=False)
    n = len(_TEXT.findall(svg))
    svg = _TEXT.sub(_fix_text, svg)
    svg = _merge(svg)
    svg, _gone = _prune(svg)
    data = svg.encode("utf-8")
    if dst.endswith(".svgz"):                       # 圧縮した SVG（Illustrator でそのまま開ける）。日時を入れないので中身が同じなら同じファイル
        data = gzip.compress(data, 9, mtime=0)
    open(dst, "wb").write(data)
    return dst, n


if __name__ == "__main__":
    for p in sys.argv[1:]:
        d, n = convert(p)
        print("%s：文字 %d" % (d, n))
