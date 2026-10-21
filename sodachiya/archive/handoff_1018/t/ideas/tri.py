exec(open('/tmp/claude-0/t/ideas/case3.py').read().split("# ---------- model ----------")[0])
from shapely.ops import polylabel
main=SP([world(bm,thf(0),u,0)[:2] for u in np.linspace(-3000,12200,10)]+[world(bm,thf(k),12200,0)[:2] for k in np.linspace(0,19,30)]+[world(bm,thf(19),u,0)[:2] for u in np.linspace(12200,-3000,10)]+[world(bm,thf(k),-3000,0)[:2] for k in np.linspace(19,0,30)])
a=np.array(world(bm,thf(0),-40000,0)[:2]); b=np.array(world(bm,thf(0),60000,0)[:2]); t=(b-a)/np.linalg.norm(b-a); n=np.array([-t[1],t[0]])
if np.dot(n,np.array(world(bm,thf(0),5000,0)[:2])-np.array(world(bm,thf(3),5000,0)[:2]))<0: n=-n
half=SP([tuple(a),tuple(b),tuple(b+n*60000),tuple(a+n*60000)])
free=site.intersection(half).difference(unary_union([main,W]).buffer(500))
pcs=sorted(getattr(free,'geoms',[free]),key=lambda g:-g.area)
for g in pcs[:3]:
    pl=polylabel(g,10); print('area %.0f m2, max circle r %.1f m, centroid'%(g.area/1e6,g.exterior.distance(pl)/1000),[round(v) for v in g.centroid.coords[0]])
tri=pcs[0]
NE=SL([(0,0),(34860,-43830)]); NR=SL([(-25830,-20540),(0,0)])
print('dist to NE edge from tri centroid %.1f m, to north road %.1f m'%(NE.distance(tri.centroid)/1000,NR.distance(tri.centroid)/1000))
print('triangle within 1m setback area %.0f'%(tri.intersection(setb).area/1e6))
import pickle; pickle.dump((tri,),open('tri.pkl','wb'))
