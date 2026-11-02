# -*- coding: utf-8 -*-
"""PDF の文字の書体をヒラギノ角ゴシックにする（ユーザー 11-02：PDF を作るときはヒラギノ角ゴシック）。

このコンテナにはヒラギノが無い（Mac の書体）ので、図は今までどおり Noto Sans CJK JP（Type42）で描き、
最後にこの道具で書体だけを差し替える：
  - Noto の埋め込みをやめ、ヒラギノ角ゴシックの名前（HiraginoSans-W3、太字は W6）を指す（埋め込まない）。
  - 文字は Unicode のまま（Encoding UniJIS-UTF16-H、Adobe-Japan1）。Mac の Illustrator・プレビューは入っているヒラギノで表示し、
    文字は文字のまま直せる。
  - 字の送りは Noto の幅を使う（欧文・数字は Noto の幅、和文は全角）。並びは Noto で組んだときとほぼ同じ。

  python3 present/tools/hiragino.py <pdf> [<pdf> ...]        その場で書き換える
  python3 present/tools/hiragino.py <pdf> -o <out.pdf>        別のファイルへ
Noto でない書体（Apple Chancery の代わりの TeX Gyre Chorus など）は触らない。
"""
import argparse, re, sys
import pikepdf
from pikepdf import Name, Array, Dictionary, String
from fontTools.ttLib import TTCollection

NOTO = {False: "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        True: "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"}
HIRA = {False: "HiraginoSans-W3", True: "HiraginoSans-W6"}
_adv = {}


def ascii_widths(bold):
    """ASCII 0x20〜0x7E の Noto Sans CJK JP の送り（1000 単位）。Adobe-Japan1 の CID 1〜95（プロポーショナルの欧文）に当てる"""
    if bold not in _adv:
        ttc = TTCollection(NOTO[bold])
        f = next(t for t in ttc.fonts if "JP" in t["name"].getDebugName(1))
        upm = f["head"].unitsPerEm
        cmap, hm = f.getBestCmap(), f["hmtx"].metrics
        _adv[bold] = [round(hm[cmap[c]][0] * 1000 / upm) if c in cmap else 500 for c in range(0x20, 0x7F)]
    return _adv[bold]


def tounicode(stream):
    """ToUnicode の CMap から 2 バイトの字の番号 → 文字"""
    s = stream.read_bytes().decode("latin-1")
    m = {}
    h = lambda x: int(x, 16)
    u = lambda x: bytes.fromhex(x).decode("utf-16-be")
    for blk in re.findall(r"beginbfchar(.*?)endbfchar", s, re.S):
        for a, b in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", blk):
            m[h(a)] = u(b)
    for blk in re.findall(r"beginbfrange(.*?)endbfrange", s, re.S):
        for a, b, c in re.findall(r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(<[0-9A-Fa-f]+>|\[[^\]]*\])", blk):
            a, b = h(a), h(b)
            if c.startswith("<"):
                base = u(c[1:-1])
                for i in range(b - a + 1):
                    m[a + i] = base[:-1] + chr(ord(base[-1]) + i)
            else:
                for i, x in enumerate(re.findall(r"<([0-9A-Fa-f]+)>", c)):
                    m[a + i] = u(x)
    return m


def new_font(pdf, bold):
    name = HIRA[bold]
    fd = pdf.make_indirect(Dictionary(Type=Name.FontDescriptor, FontName=Name("/" + name), Flags=4,
                                      FontBBox=Array([-200, -150, 1100, 950]), ItalicAngle=0, Ascent=880, Descent=-120,
                                      CapHeight=760, StemV=(140 if bold else 80)))
    cid = pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.CIDFontType0, BaseFont=Name("/" + name),
                                       CIDSystemInfo=Dictionary(Registry=String("Adobe"), Ordering=String("Japan1"), Supplement=6),
                                       FontDescriptor=fd, DW=1000, W=Array([1, Array(ascii_widths(bold))])))
    return pdf.make_indirect(Dictionary(Type=Name.Font, Subtype=Name.Type0, BaseFont=Name("/" + name),
                                        Encoding=Name("/UniJIS-UTF16-H"), DescendantFonts=Array([cid])))


def recode(b, gmap):
    out = []
    for i in range(0, len(bytes(b)) - 1, 2):
        g = bytes(b)[i] << 8 | bytes(b)[i + 1]
        out.append(gmap.get(g, "〓"))        # 分からない字は〓
    return String("".join(out).encode("utf-16-be"))


def fix_stream(pdf, owner, res, done):
    fonts = res.get("/Font") if res is not None else None
    swap = {}
    if fonts is not None:
        for k in list(fonts.keys()):
            f = fonts[k]
            bf = str(f.get("/BaseFont", ""))
            if f.get("/Subtype") == Name.Type0 and "NotoSansCJK" in bf and "/ToUnicode" in f:
                key = (f.objgen, bf)
                if key not in done:
                    bold = "Bold" in bf or "Black" in bf or "Medium" in bf
                    done[key] = (new_font(pdf, bold), tounicode(f.ToUnicode))
                fonts[k] = done[key][0]
                swap[k] = done[key][1]
    xo = res.get("/XObject") if res is not None else None
    if xo is not None:
        for k in xo.keys():
            x = xo[k]
            if x.get("/Subtype") == Name.Form:
                fix_stream(pdf, x, x.get("/Resources"), done)
    if not swap:
        return 0
    ops = pikepdf.parse_content_stream(owner)
    cur, n, new = None, 0, []
    for operands, op in ops:
        o = str(op)
        if o == "Tf":
            cur = swap.get(str(operands[0]))
        elif cur is not None and o in ("Tj", "'"):
            operands = [recode(operands[0], cur)]; n += 1
        elif cur is not None and o == '"':
            operands = [operands[0], operands[1], recode(operands[2], cur)]; n += 1
        elif cur is not None and o == "TJ":
            operands = [Array([recode(x, cur) if isinstance(x, pikepdf.String) else x for x in operands[0]])]; n += 1
        new.append((operands, op))
    data = pikepdf.unparse_content_stream(new)
    if isinstance(owner, pikepdf.Page):
        owner.obj.Contents = pdf.make_stream(data)
    else:
        owner.write(data)
    return n


def convert(src, dst):
    pdf = pikepdf.open(src, allow_overwriting_input=True)
    done, n = {}, 0
    for pg in pdf.pages:
        n += fix_stream(pdf, pg, pg.obj.get("/Resources"), done)
    pdf.save(dst)
    return len(done), n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="+")
    ap.add_argument("-o")
    a = ap.parse_args()
    for p in a.pdf:
        f, n = convert(p, a.o or p)
        print("%s：Noto の書体 %d をヒラギノ角ゴシックに、文字の組 %d" % (a.o or p, f, n))
