import pickle, sys, numpy as np, trimesh, warnings, re
warnings.filterwarnings('ignore')
from common import *
st=sys.argv[1]
P=pickle.load(open(f'st/{st}.3dm.pk','rb'))
# supports: west wall, roof underside layers, floor
m,Q=west_parts(f'st/{st}.3dm', r'^(21|23|20r|20v|20|24|25)_')
SUP=trimesh.util.concatenate([q['tm'] for q in Q]) if Q else None
allS=P
def pq(meshes): return trimesh.proximity.ProximityQuery(trimesh.util.concatenate(meshes))
out=[]
for i,p in enumerate(P):
    t=p['tm']; V=np.asarray(t.vertices)
    others=[q['tm'] for j,q in enumerate(P) if j!=i and np.all(q['tm'].bounds[0]-50<=t.bounds[1]) and np.all(t.bounds[0]-50<=q['tm'].bounds[1])]
    c=V.mean(0); X=V-c; w,vec=np.linalg.eigh(X.T@X); ax=vec[:,-1]; s=X@ax; L=np.ptp(s)
    res=[]
    for side,sel in (('a',s<s.min()+min(60,0.05*L)),('b',s>s.max()-min(60,0.05*L))):
        pts=V[sel]
        if len(pts)>400: pts=pts[np.random.default_rng(0).choice(len(pts),400,replace=False)]
        d1=np.abs(pq(others).signed_distance(pts)).min() if others else 1e9
        d2=np.abs(trimesh.proximity.ProximityQuery(SUP).signed_distance(pts)).min() if SUP is not None else 1e9
        e=pts.mean(0); u,v,_=to_local(e[None])
        res.append((side,min(d1,d2),u[0],v[0],e[2]))
    for side,d,u,v,z in res:
        if d>5: out.append(f"  END {p['ln']} u{p['f']} t{(p['t'].min()+p['t'].max())/2:.0f} {p['name'][:22]:22s} end@ u{u:.2f} v{v:.2f} z{z:.0f}: gap {d:.0f} mm  len {L:.0f}  {p['guid'][:8]}")
print('\n'.join(out))
# overlaps between S parts (wood-wood, girder-wood)
import manifold3d as mf
Ms=[solids.to_manifold(p['tm']) or solids.to_manifold_raw(p['tm']) for p in P]
for i in range(len(P)):
    for j in range(i+1,len(P)):
        a,b=P[i],P[j]
        if not (np.all(a['tm'].bounds[0]<=b['tm'].bounds[1]) and np.all(b['tm'].bounds[0]<=a['tm'].bounds[1])): continue
        if Ms[i] is None or Ms[j] is None: print('  nomanifold',a['ln'],a['f'],b['ln'],b['f']); continue
        v=(Ms[i]^Ms[j]).volume()
        if v>2e5:
            c=np.asarray((Ms[i]^Ms[j]).to_mesh().vert_properties)[:,:3].mean(0); u,vv,_=to_local(c[None])
            print(f"  OVL {v/1e6:.2f} L  {a['ln']}{a['name'][:8]} x {b['ln']}{b['name'][:8]} at u{u[0]:.2f} v{vv[0]:.2f} z{c[2]:.0f}")
