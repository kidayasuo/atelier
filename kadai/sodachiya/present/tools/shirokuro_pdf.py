# -*- coding: utf-8 -*-
"""PDF を白黒（灰の濃淡）にする（ユーザー 11-05：SVG は Illustrator で切り抜きが外れて崩れたので、PDF のまま白黒に）。
線・面の色（rg・RG・k・K・sc・scn で DeviceRGB／CMYK の物）を明るさを保った灰（g・G）に、画像も灰に。入れ子の図（Form XObject）の中も。
文字の無い図は PDF のまま Illustrator で開ける（切り抜きは切り抜きマスクになる）。

  python3 present/tools/shirokuro_pdf.py <in.pdf> [<out.pdf>] [--notext]     既定は「<名前>_白黒.pdf」、--notext で文字を消す
"""
import io, re, sys
import pikepdf
from pikepdf import Name
from PIL import Image


def _y(r, g, b):
    return 0.299 * r + 0.587 * g + 0.114 * b


def _cmyk(c, m, y, k):
    return _y((1 - c) * (1 - k), (1 - m) * (1 - k), (1 - y) * (1 - k))


NOTEXT = [False]


def _fix_ops(owner, pdf, seen):
    try:
        ops = pikepdf.parse_content_stream(owner)
    except Exception:
        return
    out, cs, intext = [], {"f": None, "s": None}, False
    for operands, op in ops:
        o = str(op)
        if NOTEXT[0] and o == "BT":
            intext = True
            continue
        if intext:
            if o == "ET":
                intext = False
            continue
        if o == "rg":
            operands, op = [round(_y(*[float(x) for x in operands]), 4)], pikepdf.Operator("g")
        elif o == "RG":
            operands, op = [round(_y(*[float(x) for x in operands]), 4)], pikepdf.Operator("G")
        elif o == "k":
            operands, op = [round(_cmyk(*[float(x) for x in operands]), 4)], pikepdf.Operator("g")
        elif o == "K":
            operands, op = [round(_cmyk(*[float(x) for x in operands]), 4)], pikepdf.Operator("G")
        elif o in ("cs", "CS"):
            cs["f" if o == "cs" else "s"] = str(operands[0])
        elif o in ("sc", "scn", "SC", "SCN"):
            nums = [x for x in operands if not isinstance(x, pikepdf.Name)]
            if len(nums) == 3 and len(nums) == len(operands):
                operands, op = [round(_y(*[float(x) for x in nums]), 4)], pikepdf.Operator("g" if o in ("sc", "scn") else "G")
            elif len(nums) == 4 and len(nums) == len(operands):
                operands, op = [round(_cmyk(*[float(x) for x in nums]), 4)], pikepdf.Operator("g" if o in ("sc", "scn") else "G")
        out.append((operands, op))
    data = pikepdf.unparse_content_stream(out)
    if isinstance(owner, pikepdf.Page):
        owner.obj.Contents = pdf.make_stream(data)
    else:
        owner.write(data)


def _fix_res(res, pdf, seen):
    if res is None:
        return
    for k, x in res.get("/XObject", {}).items():
        if x.objgen in seen:
            continue
        seen.add(x.objgen)
        st = x.get("/Subtype")
        if st == Name.Form:
            _fix_ops(x, pdf, seen)
            _fix_res(x.get("/Resources"), pdf, seen)
        elif st == Name.Image:
            try:
                pim = pikepdf.PdfImage(x)
                if pim.colorspace in ("/DeviceGray",) or x.get("/ImageMask", False):
                    continue
                im = pim.as_pil_image().convert("L")
                x.write(im.tobytes(), filter=Name.FlateDecode) if False else x.write(__import__("zlib").compress(im.tobytes()), filter=Name.FlateDecode)
                x.ColorSpace = Name.DeviceGray
                x.BitsPerComponent = 8
                for kk in ("/DecodeParms", "/Decode"):
                    if kk in x:
                        del x[kk]
            except Exception as e:
                print("画像は灰にできなかった：", e)
    for k, pt in res.get("/Pattern", {}).items():
        if pt.objgen not in seen and isinstance(pt, pikepdf.Stream):
            seen.add(pt.objgen)
            _fix_ops(pt, pdf, seen)
            _fix_res(pt.get("/Resources"), pdf, seen)


def convert(src, dst=None):
    dst = dst or re.sub(r"\.pdf$", "", src) + "_白黒.pdf"
    pdf = pikepdf.open(src)
    seen = set()
    for pg in pdf.pages:
        _fix_ops(pg, pdf, seen)
        _fix_res(pg.obj.get("/Resources"), pdf, seen)
    pdf.save(dst)
    return dst


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--notext"]
    NOTEXT[0] = "--notext" in sys.argv          # 文字を消す（紙の外の文が Illustrator でアウトライン化の警告を出すので、文字の無い図に）
    print(convert(a[0], a[1] if len(a) > 1 else None))
