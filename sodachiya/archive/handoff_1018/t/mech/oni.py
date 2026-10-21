exec(open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- model')[0].replace("print(","(lambda *a:None)("))
from scipy.optimize import brentq
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
plt.rcParams['font.family']='IPAGothic'
NEl=SL([(0,0),(34860,-43830)]); NWl=SL([(-25830,-20540),(0,0)])
mainP=band(bm,0,19,-3000,12200)
N0=np.array([0.0,0.0]); Wv=np.array([-25830,-20540.0]); Ev=np.array([34860,-43830.0])
a_=np.array(world(bm,thf(0),-40000,0)[:2]); b_=np.array(world(bm,thf(0),60000,0)[:2])
def isect(p,d,q,e):
    A=np.array([d,-e]).T; t=np.linalg.solve(A,q-p); return p+d*t[0]
dR=(N0-Wv)/np.linalg.norm(N0-Wv); dN=(Ev-N0)/np.linalg.norm(Ev-N0); dM=(b_-a_)/np.linalg.norm(b_-a_)
P_RN=N0; P_RM=isect(Wv,dR,a_,dM); P_NM=isect(N0,dN,a_,dM)
tri=SP([tuple(P_RM),tuple(P_RN),tuple(P_NM)]); cen=np.array(tri.centroid.coords[0])
print('triangle area %.1f'%(tri.area/1e6),'corners',[tuple(np.round(p/1000,1)) for p in (P_RM,P_RN,P_NM)])
def inward(p,d):
    n=np.array([-d[1],d[0]]); return n if np.dot(cen-p,n)>0 else -n
def shape(mr,mn,mm,r):
    L=[(P_RN+inward(P_RN,dR)*mr,dR),(P_RN+inward(P_RN,dN)*mn,dN),(a_+inward(a_,dM)*mm,dM)]
    v=[isect(*L[0],*L[1]),isect(*L[1],*L[2]),isect(*L[2],*L[0])]
    t=SP([tuple(x) for x in v])
    return t.buffer(-r,resolution=32).buffer(r,resolution=32)
res={}
for name,(mm,r) in {'A 均等':(None,1300.0),'B 本館側を広く':(2000.0,1300.0),'C 丸め大':(None,1800.0)}.items():
    if mm is None:
        g=brentq(lambda g: shape(g,g,g,r).area-30e6,500,3500); s=shape(g,g,g,r); mar=(g,g,g)
    else:
        g=brentq(lambda g: shape(g,g,mm,r).area-30e6,300,3500); s=shape(g,g,mm,r); mar=(g,g,mm)
    gap_main=s.distance(mainP)/1000; gap_W=s.distance(W)/1000
    res[name]=(s,mar,r,gap_main,gap_W,NEl.distance(s)/1000,NWl.distance(s)/1000)
    print(name,'margins road/neighbor/main %.2f/%.2f/%.2f'%tuple(m/1000 for m in mar),'r',r,'gap main %.2f west %.2f NE %.2f road %.2f'%(gap_main,gap_W,NEl.distance(s)/1000,NWl.distance(s)/1000),'area',round(s.area/1e6,1))
import pickle; pickle.dump({k:(v[0],)+v[1:] for k,v in res.items()},open('oni.pkl','wb'))
fig,axs=plt.subplots(1,3,figsize=(18,7.5))
cx,cy=cen
for ax,(name,v) in zip(axs,res.items()):
    s=v[0]
    ax.plot(*site.exterior.xy,color='k',lw=1.2); ax.plot(*setb.exterior.xy,color='#999',lw=.6,ls='--')
    ax.add_patch(MP(list(mainP.exterior.coords),fc='#eee',ec='#555',lw=.8))
    for k in range(20): p=world(bm,thf(k),-3000,0)[:2]; q=world(bm,thf(k),12200,0)[:2]; ax.plot([p[0],q[0]],[p[1],q[1]],color='#bbb',lw=.4)
    ax.add_patch(MP(list(W.exterior.coords),fc='#e6eef7',ec='#555',lw=.8))
    ax.add_patch(MP(list(s.exterior.coords),fc='#d9a35f',ec='k',lw=1))
    ax.set_xlim(cx-15000,cx+15000); ax.set_ylim(cy-13000,cy+11000); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title('%s\n30 m²　すき間：本館 %.1f m／道路 %.1f m／隣家 %.1f m\n角の丸み 半径 %.1f m'%(name,v[3],v[6],v[5],v[2]/1000),fontsize=11,pad=12)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/machine_onigiri.png',dpi=80)
