exec(open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- rooms')[0].replace("print(","(lambda *a:None)("))
from shapely import affinity as af
Cc_=np.array(G['CENTER'])
def halfk(k,side):   # side=-1: north of radial line k (smaller k), +1: south
    a=np.array(at(k,-20000)); b=np.array(at(k,80000)); t=(b-a)/np.linalg.norm(b-a); n=np.array([-t[1],t[0]])
    if np.dot(n,np.array(at(k+side,5000))-np.array(at(k,5000)))<0: n=-n
    return SP([tuple(a-t*1e5),tuple(b+t*1e5),tuple(b+t*1e5+n*1e5),tuple(a-t*1e5+n*1e5)])
mainB=band(bm,0,19,-3000,12200)
R=setb.intersection(halfk(14,-1)).difference(mainB.buffer(700,join_style=2))
q0=SPt(*at(8,6000)); R=[g for g in getattr(R,'geoms',[R]) if g.distance(q0)<1][0]
r_=np.linalg.norm(np.array(R.centroid.coords[0])-Cc_); dk=1 if (bm['thetas'][1]-bm['thetas'][0])>0 else -1
R=af.rotate(R,dk*1000/r_,origin=tuple(Cc_),use_radians=True).intersection(setb).difference(mainB.buffer(700,join_style=2))
R=R.intersection(halfk(12,-1))
R=max(getattr(R,'geoms',[R]),key=lambda g:g.area)
ks=[ku(c)[0] for c in R.exterior.coords]; print('k range',min(ks),max(ks))
for k in (1.5,2,2.5,3):
    L=SL([tuple(at(k,-5000)),tuple(at(k,40000))]).intersection(R); print(k,round(L.length))
def kreg(k0,k1,u0,u1,n=12):
    A=[tuple(at(k,u0)) for k in np.linspace(k0,k1,n)]+[tuple(at(k,u1)) for k in np.linspace(k1,k0,n)]
    return SP(A)
KN,KS=2.0,12.0
Rc=R.intersection(halfk(KN,+1))
def wfinal(rr=3000.0,box=3800.0):
    Rr=Rc.buffer(-rr,resolution=24).buffer(rr,resolution=24)
    bx=unary_union([kreg(KN,KN+1.6,-500,900+box),kreg(KS-1.6,KS,-500,900+box)]).intersection(Rc)
    out=unary_union([Rr,bx]).buffer(1).buffer(-1)
    return max(getattr(out,'geoms',[out]),key=lambda g:g.area)
WN=wfinal()
print('new W area %.1f (old %.1f)'%(WN.area/1e6,W.area/1e6))
import pickle; pickle.dump(dict(WN=WN,KN=KN,KS=KS),open('/tmp/claude-0/t/exact/wnew.pkl','wb'))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
fig,ax=plt.subplots(figsize=(7,10)); ax.plot(*W.exterior.xy,color='#bbb'); ax.plot(*WN.exterior.xy,color='k'); ax.plot(*mainB.exterior.xy,color='#888')
for k in range(0,15): p=at(k,-12000); q=at(k,16000); ax.plot([p[0],q[0]],[p[1],q[1]],color='#eee',lw=.5)
b=WN.bounds; ax.set_xlim(b[0]-14000,b[2]+3000); ax.set_ylim(b[1]-3000,b[3]+3000); ax.set_aspect('equal'); plt.savefig('/tmp/claude-0/t/exact/wnew.png',dpi=60)
