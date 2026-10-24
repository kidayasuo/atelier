"""Noto Sans CJK JP（OTF、CFF）をTrueType（glyf）に変える。matplotlibのPDFで文字を文字のまま（Type42）埋め込み、
Illustratorで文字として直せるようにするため（CFFのままのType42は字が欠ける）。
使い方：python3 make_ttf.py <出力フォルダ>　→ NotoSansCJKjp-Regular.ttf・-Bold.ttf"""
import sys, os
from fontTools.ttLib import TTFont, newTable
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen

out = sys.argv[1]
os.makedirs(out, exist_ok=True)
for src, name in (("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Regular"),
                  ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "Bold")):
    dst = os.path.join(out, f"NotoSansCJKjp-{name}.ttf")
    if os.path.exists(dst):
        continue
    f = TTFont(src, fontNumber=0)          # 0 = JP
    gs = f.getGlyphSet()
    glyf = newTable("glyf"); glyf.glyphs = {}; glyf.glyphOrder = f.getGlyphOrder()
    for g in f.getGlyphOrder():
        pen = TTGlyphPen(gs)
        gs[g].draw(Cu2QuPen(pen, 1.0, reverse_direction=True))
        glyf.glyphs[g] = pen.glyph()
    f["glyf"] = glyf
    f["loca"] = newTable("loca")
    del f["CFF "]
    if "VORG" in f:
        del f["VORG"]
    f["maxp"] = newTable("maxp"); m = f["maxp"]
    m.tableVersion = 0x00010000
    for k in ("maxZones", "maxTwilightPoints", "maxStorage", "maxFunctionDefs", "maxInstructionDefs",
              "maxStackElements", "maxSizeOfInstructions", "maxComponentElements"):
        setattr(m, k, 0)
    m.maxZones = 1
    m.numGlyphs = len(f.getGlyphOrder())
    f["head"].glyphDataFormat = 0
    f["post"].formatType = 3.0
    f.sfntVersion = "\0\1\0\0"
    f.save(dst)
    print(dst)
