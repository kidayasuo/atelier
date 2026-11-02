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


def convert(src, dst=None):
    dst = dst or os.path.splitext(src)[0] + ".svgz"
    doc = fitz.open(stream=_tag_fonts(src), filetype="pdf")
    svg = doc[0].get_svg_image(text_as_path=False)
    n = len(_TEXT.findall(svg))
    svg = _TEXT.sub(_fix_text, svg)
    svg = _merge(svg)
    data = svg.encode("utf-8")
    if dst.endswith(".svgz"):                       # 圧縮した SVG（Illustrator でそのまま開ける）。日時を入れないので中身が同じなら同じファイル
        data = gzip.compress(data, 9, mtime=0)
    open(dst, "wb").write(data)
    return dst, n


if __name__ == "__main__":
    for p in sys.argv[1:]:
        d, n = convert(p)
        print("%s：文字 %d" % (d, n))
