# -*- coding: utf-8 -*-
"""断面・立面の図面（Rhino の線＋JIS の寸法と文字）を一つの SVG に重ねる（ユーザー 11-05）。
平面図の彩色（heimen_saishoku.py）と同じ作り方：同じ紙（841×594 mm）・同じ位置の二つを、Illustrator のレイヤーになる組に。
  線（Rhino）：rhino/zumen.py の drawings_rhino（レイヤーの組のまま）
  寸法と文字：自動の図の文字の層（素材36、JIS）。断面は換気・光の説明の色（青・黄など）を外し、黒・灰と通り芯の赤だけを残す
  （風の流れは木田さんが描く、11-04）。切り抜きは使わない（Illustrator で崩れる）。

  python3 present/tools/zumen_svg.py      → present/sozai/38_<名前>_図面.svgz
"""
import gzip, os, re, sys
from lxml import etree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from heimen_saishoku import _load, _layer, NS, XL, PT2MM, P, A

SHEETS = [("断面A・B・C", "sodachiya_sections_1-100", "36_文字の層_断面A・B・C", True),
          ("断面D", "sodachiya_sections2_1-100", "36_文字の層_断面D", True),
          ("立面_園庭と道路", "sodachiya_elevations_1-100", "36_文字の層_立面_園庭と道路", False),
          ("立面_川と北の妻", "sodachiya_elevations2_1-100", "36_文字の層_立面_川と北の妻", False)]
KEEP_RED = {"#b03030"}


def _gray_or_red(col):
    c = col.lower()
    if c in KEEP_RED or c in ("none", ""):
        return True
    m = re.match(r"#([0-9a-f]{6})$", c)
    if not m:
        return True
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    return max(r, g, b) - min(r, g, b) < 24


def _drop_colored(root):
    """色の付いた物（換気の矢・注、光の帯など）を消す。黒・灰・白と通り芯の赤だけ残す"""
    n = 0
    for el in list(root.iter()):
        if not isinstance(el.tag, str) or el.tag in ("{%s}g" % NS, "{%s}svg" % NS):
            continue
        cols = [el.get("fill", ""), el.get("stroke", "")]
        st = el.get("style", "")
        cols += re.findall(r"(?:fill|stroke)\s*:\s*(#[0-9a-fA-F]{6})", st)
        if el.tag == "{%s}tspan" % NS:
            continue
        if not all(_gray_or_red(c) for c in cols):
            p = el.getparent()
            if p is not None:
                p.remove(el)
                n += 1
    return n


def build(name, rhino, moji, sec):
    root = etree.Element("{%s}svg" % NS, nsmap={None: NS, "xlink": XL}, width="841mm", height="594mm", viewBox="0 0 841 594")
    defs = etree.SubElement(root, "{%s}defs" % NS)
    g1, d1 = _layer("線（Rhino）", _load(os.path.join(A, "drawings_rhino", rhino + ".svg")), 1.0, "r_", True)
    mroot = _load(os.path.join(P, "sozai", moji + ".svgz"))
    gone = _drop_colored(mroot) if sec else 0
    g2, d2 = _layer("寸法と文字", mroot, PT2MM, "t_", True)
    for d in d1 + d2:
        for x in list(d):
            defs.append(x)
    root.append(g1)
    root.append(g2)
    if len(defs) == 0:
        root.remove(defs)
    out = os.path.join(P, "sozai", "38_%s_図面.svgz" % name)
    data = etree.tostring(root, xml_declaration=True, encoding="utf-8")
    open(out, "wb").write(gzip.compress(data, 9, mtime=0))
    s = data.decode("utf-8")
    print(out, "外した色の物", gone, "切り抜き", s.count("<clipPath"), "文字", s.count("<text"))


if __name__ == "__main__":
    for x in SHEETS:
        build(*x)
