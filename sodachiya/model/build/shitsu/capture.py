"""別チャットの平面図スクリプト（plan01/02/04）を、P(u,v) を恒等写像にして実行し、
描かれた図形を (u, v)[m] のまま記録する。記録には呼び出し元の行番号を付ける。"""
import sys, math, traceback, types, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.axes as maxes, matplotlib.figure as mfig
from matplotlib.patches import Polygon, Circle, Ellipse
import numpy as np, warnings; warnings.filterwarnings('ignore')
REC=[]
HELP={'box','fill','line','wall','poly','draw_shape','bx','wl','seg','rect_pts','txt','num','t','pt','sbox_','rect','add_patch','plot','<lambda>','fbox','hline','vline','circ','ell','label','door','win'}
def _caller(fname):
    st=[fr for fr in traceback.extract_stack() if fr.filename==fname]
    for fr in st[::-1]:
        if fr.name not in HELP: return fr.lineno
    return st[-1].lineno if st else -1
def prep(path):
    """capture が実行するのと同じ書き換えをした行のリスト（行番号の対応用）"""
    src=open(path).read().replace('plt.rcParams["font.family"] = "Noto Sans CJK JP"','')
    src=src.replace("def P(u, v):","def _P_orig(u, v):",1)
    head,sep,tail=src.partition("def _P_orig(u, v):")
    lines=tail.split('\n'); i=1
    while i<len(lines) and (lines[i].startswith(' ') or lines[i].strip()==''): i+=1
    tail='\n'.join(lines[:i])+"\ndef P(u, v):\n    return (u, v)\n"+'\n'.join(lines[i:])
    return (head+sep+tail).split('\n')
def capture(path):
    REC.clear(); src=open(path).read()
    src=src.replace('plt.rcParams["font.family"] = "Noto Sans CJK JP"','')
    fname='<'+path+'>'
    _ap=maxes.Axes.add_patch; _pl=maxes.Axes.plot
    def add_patch(self,p):
        ln=_caller(fname)
        try:
            if isinstance(p,Ellipse):
                c=p.center; w,h=p.width,p.height; a=np.linspace(0,2*np.pi,25)[:-1]
                pts=np.c_[c[0]+w/2*np.cos(a),c[1]+h/2*np.sin(a)]; kind='ellipse'
            elif isinstance(p,Circle):
                c=p.center; rr=p.radius; a=np.linspace(0,2*np.pi,25)[:-1]
                pts=np.c_[c[0]+rr*np.cos(a),c[1]+rr*np.sin(a)]; kind='circle'
            else:
                pts=np.array(p.get_xy()); kind='poly'
            REC.append(dict(ln=ln,kind=kind,pts=pts,fc=p.get_facecolor(),ec=p.get_edgecolor(),lw=p.get_linewidth(),ls=p.get_linestyle()))
        except Exception as e: pass
        return _ap(self,p)
    def plot(self,*a,**k):
        ln=_caller(fname)
        if len(a)>=2:
            REC.append(dict(ln=ln,kind='line',pts=np.c_[np.asarray(a[0],float),np.asarray(a[1],float)],lw=k.get('lw',k.get('linewidth',1)),c=k.get('color',k.get('c'))))
        return _pl(self,*a,**k)
    maxes.Axes.add_patch=add_patch; maxes.Axes.plot=plot
    mfig.Figure.savefig=lambda *a,**k: None
    g={'__name__':'__cap__','__file__':path}
    # P を恒等写像に：P(u,v)=(u,v)。helpers が P を名前で引くので、定義直後に差し替える
    src=src.replace("def P(u, v):","def _P_orig(u, v):",1)
    head,sep,tail=src.partition("def _P_orig(u, v):")
    # 関数本体を飛ばして P を差し込む
    lines=tail.split('\n'); i=1
    while i<len(lines) and (lines[i].startswith(' ') or lines[i].strip()==''): i+=1
    tail='\n'.join(lines[:i])+"\ndef P(u, v):\n    return (u, v)\n"+'\n'.join(lines[i:])
    src=head+sep+tail
    try:
        exec(compile(src,fname,'exec'),g)
    finally:
        maxes.Axes.add_patch=_ap; maxes.Axes.plot=_pl; plt.close('all')
    return list(REC), src.split('\n')
if __name__=='__main__':
    rec,lines=capture(sys.argv[1])
    from collections import defaultdict
    by=defaultdict(list)
    for r_ in rec: by[r_['ln']].append(r_)
    for ln in sorted(by):
        rs=by[ln]; b=np.vstack([r_['pts'] for r_ in rs])
        print(f"{ln:4d} n={len(rs):3d} {rs[0]['kind']:7s} u[{b[:,0].min():5.1f},{b[:,0].max():5.1f}] v[{b[:,1].min():5.1f},{b[:,1].max():5.1f}] | {lines[ln-1].strip()[:90]}")
