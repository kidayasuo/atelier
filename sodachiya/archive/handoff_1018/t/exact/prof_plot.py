exec(open('/tmp/claude-0/t/exact/exact_model.py').read().replace("model.Write(OUT,8)","pass"))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Ellipse
plt.rcParams['font.family']='IPAGothic'
fig,axs=plt.subplots(2,1,figsize=(15,11))
def draw(ax,prof_list,holes,title,xlim):
    for segs,fc in prof_list:
        ax.add_patch(MP(seg_poly(segs),fc=fc,ec='k',lw=.5,alpha=.85))
    for hu,hz in holes: ax.add_patch(Ellipse((hu,hz),GW,GH_,fc='#5a3d22',ec='k',lw=.5))
    ax.set_aspect('equal'); ax.set_xlim(*xlim); ax.set_ylim(-300,8500); ax.set_title(title); ax.axhline(0,color='k',lw=1)
B=G['buildings']()[0]; P=B['prof']
draw(axs[0],[(P['beam'],'#d9b98c')]+[(c['segs'],'#b08458') for c in P['cols']],P['holes'],'本館の架構（u = 東の柱芯から、mm）',(-3500,12800))
k=9.0; a,b,L=segs[k]; Dk=L-800; te=zroof(k,400,L); tw=zroof(k,L-400,L)
Bk=dict(R=1,D=Dk,EAVE=0.0); Pk=G['frame_profiles'](Bk,te,tw,700.0,0.0,250.0); Bk.update(prof=Pk,TOP_E=te,TOP_W=tw,FLOOR2_TOP=Z2-50,FLOOR2_DEPTH=HB2)
F=G['floor2_profile_tamedia'](Bk)
draw(axs[1],[(Pk['beam'],'#d9b98c'),(F['beam'],'#e6c99c')]+[(c['segs'],'#b08458') for c in F['cols']],Pk['holes']+F['holes'],'西館の架構 k=9（u = 本館側の柱芯から、左が本館側）',(-800,Dk+800))
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/exact_profiles.png',dpi=70)
