import rhino3dm as r3, numpy as np, math
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPo
plt.rcParams['font.family']='IPAGothic'
import rhino3dm as r3
def load(path):
    f=r3.File3dm.Read(path); names={i:l.Name for i,l in enumerate(f.Layers)}
    cols={'10_本館':(0.85,0.82,0.76),'12_本館_2階':(0.80,0.62,0.45),'20_西館_屋根':(0.62,0.58,0.52),'21_西館_外壁':(0.88,0.82,0.72),'23_西館_2階':(0.70,0.60,0.85)}
    F=[]
    for o in f.Objects:
        g=o.Geometry; n=names[o.Attributes.LayerIndex]
        if isinstance(g,r3.Mesh) and n in cols:
            V=[(g.Vertices[i].X,g.Vertices[i].Y,g.Vertices[i].Z) for i in range(len(g.Vertices))]
            for j in range(len(g.Faces)):
                a,b,c,d=g.Faces[j]; idx=[a,b,c] if c==d else [a,b,c,d]
                F.append((np.array([V[i] for i in idx]),cols[n]))
    return F
src=open('/tmp/claude-0/t/ideas/check3dm.py').read()
vsrc=src[src.index("def view("):src.index("W=np.array((-25830")]
exec(vsrc)
W=np.array((-25830,-20540)); N=np.array((0,0)); SW=np.array((-21910,-73650))
u=lambda v: v/np.linalg.norm(v); bis=u(u(N-W)+u(SW-W)); c=np.array([-14000,-32000])
titles={'A':'案1：本館の上に 2 階（休憩 60＋会議 30）','B2':'案2：ホール 2 スパン＋本館に会議室、西館に屋根裏の休憩','B3':'案3：西館一枚屋根、高い側に会議＋休憩、低い側に屋根裏'}
fig,axs=plt.subplots(3,3,figsize=(18,13))
for r,v in enumerate(('A','B2','B3')):
    globals()['faces']=load('/home/claude/plans/rhino/sodachiya_west_var%s.3dm'%v)
    view(axs[r,0],np.r_[W-bis*40000+np.array([0,-10000]),30000],np.r_[c+np.array([3000,-6000]),0],1.4,titles[v]+'｜北西の上空')
    view(axs[r,1],np.r_[np.array([-32000,-48000]),1500],np.r_[np.array([-15000,-40000]),2500],0.7,'西の道路から')
    view(axs[r,2],np.r_[np.array([25000,-25000]),22000],np.r_[c+np.array([0,-8000]),2000],1.2,'園庭の上空（東）から')
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_room_variants.png',dpi=62)
