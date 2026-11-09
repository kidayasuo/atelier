# -*- coding: utf-8 -*-
"""3〜5歳の三つの教室の家具配置（本館係の scripts/plan04.py → out/sodachiya_35_furniture.pdf）を、
Illustrator に渡す SVG にする（ユーザー 11-02 22:59：三つの教室を並べる、この図を SVG にして90度回すだけ）。

  - plan04.py をそのまま走らせ、matplotlib の SVG（文字は文字のまま、svg.fonttype none）も書かせる（本館係のファイルは変えない）。
  - 書体はヒラギノ角ゴシック（'HiraginoSans-W3'、Medium 以上は 'HiraginoSans-W6'、ユーザー 11-02）。
  - 時計回りに90度回す（東の外縁側が下）。
  → present/sozai/33_教室_3〜5歳.svgz

  python3 present/tools/kyoushitsu35.py
"""
import gzip, os, re, runpy, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PRESENT = os.path.dirname(HERE)
ROOT = os.path.dirname(PRESENT)
OUTF = os.path.join(PRESENT, "sozai", "33_教室_3〜5歳.svgz")


def make_svg():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    tmp = tempfile.mkdtemp()
    orig = Figure.savefig

    def sv(self, fname, *a, **k):
        if str(fname).endswith(".pdf"):
            with plt.rc_context({"svg.fonttype": "none"}):
                orig(self, os.path.join(tmp, "f.svg"), *a, **k)
        else:
            orig(self, fname, *a, **k)
    Figure.savefig = sv
    os.environ["OUT"] = tmp
    cwd = os.getcwd()
    os.chdir(ROOT)
    try:
        sys.argv = ["plan04.py"]
        runpy.run_path(os.path.join(ROOT, "scripts", "plan04.py"), run_name="__main__")
    finally:
        os.chdir(cwd)
        Figure.savefig = orig
    return open(os.path.join(tmp, "f.svg"), encoding="utf-8").read()


def hiragino(svg):
    def fix(m):
        st = m.group(1)
        w = re.search(r"font-weight:\s*(\d+|bold)", st)
        bold = bool(w) and (w.group(1) == "bold" or int(w.group(1)) >= 500)
        st = re.sub(r"font-weight:\s*[^;]*;?\s*", "", st)
        st = re.sub(r"font-family:\s*[^;]*", "font-family: '%s'" % ("HiraginoSans-W6" if bold else "HiraginoSans-W3"), st)
        return 'style="%s"' % st.strip().rstrip(";")
    return re.sub(r'style="([^"]*font-family[^"]*)"', fix, svg)


def rotate_cw(svg):
    """時計回りに90度（右＝東の外縁側が下へ）"""
    m = re.search(r'<svg\b[^>]*width="([\d.]+)pt" height="([\d.]+)pt" viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    W, H = float(m.group(3)), float(m.group(4))
    head = svg[:m.start()] + m.group(0).replace('width="%spt"' % m.group(1), 'width="%spt"' % m.group(2), 1) \
        .replace('height="%spt"' % m.group(2), 'height="%spt"' % m.group(1), 1) \
        .replace('viewBox="0 0 %s %s"' % (m.group(3), m.group(4)), 'viewBox="0 0 %s %s"' % (m.group(4), m.group(3)), 1)
    rest = svg[m.end():]
    i = rest.find("</metadata>")
    i = i + len("</metadata>") if i >= 0 else rest.find(">") + 1
    j = rest.rfind("</svg>")
    return head + rest[:i] + '\n <g transform="translate(%s 0) rotate(90)">' % H + rest[i:j] + " </g>\n" + rest[j:]


if __name__ == "__main__":
    s = rotate_cw(hiragino(make_svg()))
    open(OUTF, "wb").write(gzip.compress(s.encode("utf-8"), 9, mtime=0))
    print("→", OUTF, "文字", s.count("<text"))
