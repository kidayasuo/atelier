# -*- coding: utf-8 -*-
"""3・4枚目の平面図（1階・2階）を、彩色して一つの SVG に重ねる（ユーザー 11-05）。
同じ紙（841×594 mm）・同じ位置の4つを、Illustrator のレイヤーになる組に分けて下から重ねる：
  部屋の色（素材27a・27b）／園庭の等高線（29b・29c）／線（Rhino の zumen.py、drawings_rhino、レイヤーの組のまま）／文字と寸法（36、JIS）。
切り抜き（clip-path）は Illustrator で外れて崩れるので使わない（部屋の色・等高線・文字の層の切り抜きは軸の枠だけなので外す）。

  python3 present/tools/heimen_saishoku.py      → present/sozai/37_平面図_1階_彩色.svgz・37_平面図_2階_彩色.svgz
"""
import gzip, json, os, re
from lxml import etree

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.dirname(HERE)
A = os.path.dirname(P)
NS = "http://www.w3.org/2000/svg"
XL = "http://www.w3.org/1999/xlink"
PT2MM = 25.4 / 72.0

SHEETS = {
    "1階": dict(color="27a_平面図_1階_部屋の色", cont="29b_平面図_1階_園庭の等高線", rhino="sodachiya_plan1F_1-100", moji="36_文字の層_平面図1階"),
    "2階": dict(color="27b_平面図_2階_部屋の色", cont="29c_平面図_2階_園庭の等高線", rhino="sodachiya_plan2F_1-100", moji="36_文字の層_平面図2階"),
}


def _load(path):
    raw = open(path, "rb").read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return etree.fromstring(raw)


def _prefix_ids(root, pre):
    """id と参照（url(#…)・href）に頭を付けて、重ねたときにぶつからないように"""
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        if el.get("id"):
            el.set("id", pre + el.get("id"))
        for k in list(el.attrib):
            v = el.get(k)
            if "url(#" in v:
                el.set(k, re.sub(r"url\(#([^)]+)\)", lambda m: "url(#%s%s)" % (pre, m.group(1)), v))
            if k in ("href", "{%s}href" % XL) and v.startswith("#"):
                el.set(k, "#" + pre + v[1:])


def _strip_clips(root):
    for el in root.iter():
        if isinstance(el.tag, str) and el.get("clip-path"):
            del el.attrib["clip-path"]
    for cp in list(root.iter("{%s}clipPath" % NS)):
        cp.getparent().remove(cp)


def _layer(name, src_root, scale, pre, strip):
    _prefix_ids(src_root, pre)
    if strip:
        _strip_clips(src_root)
    defs = [d for d in src_root if isinstance(d.tag, str) and d.tag == "{%s}defs" % NS]
    g = etree.Element("{%s}g" % NS, id=name)
    inner = g if scale == 1.0 else etree.SubElement(g, "{%s}g" % NS, transform="scale(%.9f)" % scale)
    for ch in list(src_root):
        if not isinstance(ch.tag, str) or ch.tag in ("{%s}defs" % NS, "{%s}metadata" % NS, "{%s}title" % NS):
            continue
        inner.append(ch)
    return g, defs


def _contours(view_json, thin):
    """園庭の等高線（3dm の 91、名前に高さ）を、平面図の紙の座標（mm）の <g> に。mock.py の素材29b・29cは建物の足もとを
    引く所で大半が消えていた（11-05）ので、3dm から直に描く。1.0 m ごとは太く"""
    import rhino3dm as r_
    v = [x for x in json.load(open(view_json))["views"] if x.get("kind") == "plan"][0]["model_to_paper"]
    m = r_.File3dm.Read(os.path.join(A, "model", "sodachiya_exact_mesh.3dm"))
    L = {i: l.FullPath.split("::")[-1] for i, l in enumerate(m.Layers)}
    g = etree.Element("{%s}g" % NS, id="園庭の等高線")
    n = 0
    for o in m.Objects:
        if not L[o.Attributes.LayerIndex].startswith("91_"):
            continue
        c = o.Geometry
        try:
            pts = [c.Point(i) for i in range(c.PointCount)]
        except Exception:
            continue
        try:
            h = float(re.sub(r"[^0-9.+-]", "", o.Attributes.Name or ""))
        except ValueError:
            h = 0.1
        thick = abs(h - round(h)) < 0.01 and abs(h) > 0.01
        lw = (0.35 if thick else 0.18) if thin else (0.6 if thick else 0.3)
        d = " ".join(("M" if i == 0 else "L") + "%.3f %.3f" % (v["a"] * p.X + v["b"] * p.Y + v["c"], v["d"] * p.X + v["e"] * p.Y + v["f"])
                     for i, p in enumerate(pts))
        etree.SubElement(g, "{%s}path" % NS, d=d, fill="none", stroke="#9AAE8C" if thin else "#6F8C5A",
                         **{"stroke-width": "%.4f" % (lw * PT2MM), "stroke-linejoin": "round"})
        n += 1
    print("等高線", n, "本")
    return g


def build(floor, cfg):
    root = etree.Element("{%s}svg" % NS, nsmap={None: NS, "xlink": XL}, width="841mm", height="594mm", viewBox="0 0 841 594")
    alldefs = etree.SubElement(root, "{%s}defs" % NS)
    parts = [("部屋の色", os.path.join(P, "sozai", cfg["color"] + ".svgz"), PT2MM, "c_", True),
             ("等高線", None, None, None, None),
             ("線（Rhino）", os.path.join(A, "drawings_rhino", cfg["rhino"] + ".svg"), 1.0, "r_", True),
             ("文字と寸法", os.path.join(P, "sozai", cfg["moji"] + ".svgz"), PT2MM, "t_", True)]
    for name, path, sc, pre, strip in parts:
        if path is None:
            root.append(_contours(os.path.join(A, "drawings", cfg["rhino"] + "_views.json"), floor == "2階"))
            continue
        if not os.path.exists(path):
            print("無い：", path)
            continue
        g, defs = _layer(name, _load(path), sc, pre, strip)
        for d in defs:
            for x in list(d):
                alldefs.append(x)
        root.append(g)
    if len(alldefs) == 0:
        root.remove(alldefs)
    out = os.path.join(P, "sozai", "37_平面図_%s_彩色.svgz" % floor)
    data = etree.tostring(root, xml_declaration=True, encoding="utf-8")
    open(out, "wb").write(gzip.compress(data, 9, mtime=0))
    s = data.decode("utf-8")
    print(out, "切り抜き", s.count("<clipPath"), "マスク", s.count("<mask"), "文字", s.count("<text"))
    return out


if __name__ == "__main__":
    for f, c in SHEETS.items():
        build(f, c)
