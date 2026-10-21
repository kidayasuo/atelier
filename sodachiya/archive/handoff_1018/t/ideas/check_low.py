import rhino3dm as r3, numpy as np, math
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPo
plt.rcParams['font.family']='IPAGothic'
f=r3.File3dm.Read('/home/claude/plans/rhino/sodachiya_west_lowstreet.3dm')
names={i:l.Name for i,l in enumerate(f.Layers)}
from collections import Counter
print(Counter((names[o.Attributes.LayerIndex],type(o.Geometry).__name__) for o in f.Objects))
cols={'10_本館':(0.85,0.82,0.76),'20_西館_屋根':(0.62,0.58,0.52),'21_西館_外壁':(0.88,0.82,0.72),'22_西館_床':(0.75,0.72,0.66),'23_西館_2階':(0.78,0.72,0.85),'25_西館_ハイサイド':(0.70,0.82,0.90)}
faces=[]
for o in f.Objects:
    g=o.Geometry; n=names[o.Attributes.LayerIndex]
    if isinstance(g,r3.Mesh) and n in cols:
        V=[(g.Vertices[i].X,g.Vertices[i].Y,g.Vertices[i].Z) for i in range(len(g.Vertices))]
        for j in range(len(g.Faces)):
            a,b,c,d=g.Faces[j]
            idx=[a,b,c] if c==d else [a,b,c,d]
            faces.append((np.array([V[i] for i in idx]),cols[n]))
def view(ax,E,T,focal,title):
    E=np.array(E,float);T=np.array(T,float);fw=(T-E)/np.linalg.norm(T-E);r=np.cross(fw,[0,0,1]);r/=np.linalg.norm(r);up=np.cross(r,fw)
    Lt=np.array([-0.5,-0.4,0.75]);Lt/=np.linalg.norm(Lt);items=[]
    for P,c in faces:
        Vv=P-E;d=Vv@fw
        if (d<500).any(): continue
        nrm=np.cross(P[1]-P[0],P[2]-P[0]);nn=np.linalg.norm(nrm)
        if nn<1e-6: continue
        nrm/=nn
        if nrm@(E-P.mean(0))<0: nrm=-nrm
        sh=0.55+0.45*max(0,nrm@Lt)
        items.append((d.mean(),np.c_[(Vv@r)/d*focal,(Vv@up)/d*focal],np.clip(np.array(c)*sh,0,1)))
    items.sort(key=lambda t:-t[0])
    fh=fw.copy();fh[2]=0;fh/=np.linalg.norm(fh);hy=(fh@up)/(fh@fw)*focal
    ax.add_patch(plt.Rectangle((-3,-3),6,3+hy,fc='#e9e6df',zorder=-5));ax.add_patch(plt.Rectangle((-3,hy),6,3,fc='#eef3f7',zorder=-6))
    for _,xy,c in items: ax.add_patch(MPo(xy,closed=True,fc=c,ec=c*0.85,lw=0.1))
    ax.set_xlim(-0.95,0.95);ax.set_ylim(-0.5,0.6);ax.set_aspect('equal');ax.axis('off');ax.set_title(title,fontsize=10)
W=np.array((-25830,-20540)); N=np.array((0,0)); SW=np.array((-21910,-73650))
u=lambda v: v/np.linalg.norm(v); bis=u(u(N-W)+u(SW-W))
fig,axs=plt.subplots(2,2,figsize=(16,10))
c=np.array([-14000,-32000])
view(axs[0,0],np.r_[W-bis*9000,1500],np.r_[c,1500],0.6,'交差点の歩道から')
view(axs[0,1],np.r_[W-bis*40000+np.array([0,-10000]),30000],np.r_[c+np.array([3000,-6000]),0],1.4,'北西の上空から')
view(axs[1,0],np.r_[np.array([25000,-25000]),22000],np.r_[c+np.array([0,-8000]),2000],1.2,'園庭の上空（東）から')
view(axs[1,1],np.r_[np.array([-32000,-48000]),1500],np.r_[np.array([-15000,-40000]),2500],0.7,'西の道路から（台所棟の前）')
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_lowstreet_model_views.png',dpi=70)
