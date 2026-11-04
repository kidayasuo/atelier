# -*- coding: utf-8 -*-
"""素材の SVG（.svgz）を白黒（灰色の濃淡）にする（ユーザー 11-04：園庭の図の白黒版）。
色は明るさ（輝度）を保った灰に、埋め込みの画像も灰に。文字・線・組はそのまま。

  python3 present/tools/shirokuro.py <in.svgz> [<out.svgz>]     既定の出力は「<名前>_白黒.svgz」
"""
import base64, gzip, io, os, re, sys
from PIL import Image


def _gray(r, g, b):
    y = int(round(0.299 * r + 0.587 * g + 0.114 * b))
    return "#%02x%02x%02x" % (y, y, y)


def _hex(m):
    h = m.group(1)
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return _gray(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def _rgb(m):
    v = [float(x) for x in re.split(r"[ ,]+", m.group(1).strip())[:3]]
    if max(v) <= 1.0 and "%" not in m.group(1):
        v = [x * 255 for x in v] if all(x <= 1.0 for x in v) and any(x < 1.0 and x > 0 for x in v) else v
    return _gray(*[int(round(x)) for x in v])


def _img(m):
    data = base64.b64decode(m.group(2))
    im = Image.open(io.BytesIO(data))
    alpha = im.getchannel("A") if im.mode in ("RGBA", "LA") else None
    g = im.convert("L")
    if alpha is not None:
        g = Image.merge("LA", (g, alpha))
    b = io.BytesIO()
    g.save(b, "PNG")
    return m.group(1) + base64.b64encode(b.getvalue()).decode("ascii")


def convert(src, dst=None):
    dst = dst or re.sub(r"\.svgz?$", "", src) + "_白黒.svgz"
    raw = open(src, "rb").read()
    s = (gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw).decode("utf-8")
    s = re.sub(r"#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", _hex, s)
    s = re.sub(r"rgb\(([^)]*)\)", _rgb, s)
    s = re.sub(r'(data:image/(?:png|jpeg);base64,)([A-Za-z0-9+/=\s]+)', _img, s)
    data = s.encode("utf-8")
    if dst.endswith(".svgz"):
        data = gzip.compress(data, 9, mtime=0)
    open(dst, "wb").write(data)
    return dst


if __name__ == "__main__":
    print(convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
