# 図のPDFの文字を文字のまま（Type42）埋め込む（プレゼンの準備 10-24：仕上げはIllustratorでヒラギノに置き換える）。
# NotoのOTF（CFF）をType42にすると字が欠けるので、TrueTypeに変えたNoto（present/tools/make_ttf.py）を使う。無ければ作る、作れなければ前のまま。
import os, sys, subprocess
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
_HERE = os.path.dirname(os.path.abspath(__file__))
_TTF = os.path.expanduser("~/.cache/sodachiya_fonts")
_R, _B = os.path.join(_TTF, "NotoSansCJKjp-Regular.ttf"), os.path.join(_TTF, "NotoSansCJKjp-Bold.ttf")
if not os.path.exists(_B):
    subprocess.run([sys.executable, os.path.join(os.path.dirname(_HERE), "present", "tools", "make_ttf.py"), _TTF], check=False)
if os.path.exists(_B):
    _fm = matplotlib.font_manager.fontManager
    _name = FontProperties(fname=_R).get_name()
    _fm.ttflist = [e for e in _fm.ttflist if not (e.name == _name or "NotoSansCJK" in os.path.basename(e.fname) or "NotoSerifCJK" in os.path.basename(e.fname))]   # OTF（CFF）の同じ名前を外す
    for f in (_R, _B): _fm.addfont(f)
    matplotlib.font_manager._get_font.cache_clear() if hasattr(matplotlib.font_manager, "_get_font") else None
    plt.rcParams["font.family"] = FontProperties(fname=_R).get_name()
    plt.rcParams["pdf.fonttype"] = 42
else:
    plt.rcParams["font.family"] = "Noto Sans CJK JP"
