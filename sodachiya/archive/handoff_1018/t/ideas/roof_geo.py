import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"]="IPAGothic"
exec(open('/tmp/claude-0/t/ideas/conform.py').read().split("if __name__")[0])
import json
C=[c for c in json.load(open('/tmp/claude-0/t/ideas/conform.json')) if c[0]=='tri' and c[1]==205000][0]
C=['tri',C[1],globals().get('PLACE_OVERRIDE',C[2])]; pen,ga,wa,D=evalc(C[1],*C[2],'tri',detail=True)
bm,thf,at,W=D['bm'],D['thf'],D['at'],D['west']
WSHIFT=globals().get('WSHIFT',0.0)     # 西館を本館の円弧に沿って南へずらす量 (mm)
if WSHIFT:
    from shapely import affinity as _af
    _C=np.array(G['CENTER']); _r=np.linalg.norm(np.array(W.centroid.coords[0])-_C)
    _dk=1 if (bm['thetas'][1]-bm['thetas'][0])>0 else -1
    W=_af.rotate(W,_dk*WSHIFT/_r,origin=tuple(_C),use_radians=True)
    W=W.intersection(setb).buffer(0); W=max(getattr(W,'geoms',[W]),key=lambda g:g.area)   # 西の道路側も 1 m は守る
# radial segments through W
ks=np.arange(-1,14,0.125)
segs={}
for k in ks:
    L=SL([tuple(at(k,0)),tuple(at(k,60000))]).intersection(W)
    if L.is_empty: continue
    if L.geom_type!='LineString': L=max(L.geoms,key=lambda g:g.length)
    a,b=np.array(L.coords[0]),np.array(L.coords[-1])
    o=at(k,0)
    if np.linalg.norm(a-o)>np.linalg.norm(b-o): a,b=b,a
    segs[round(k,3)]=(a,b,np.linalg.norm(b-a))
kk=sorted(segs)
Ls=np.array([segs[k][2] for k in kk])
print('frames',kk[0],kk[-1],'L range',Ls.min(),Ls.max())
for k in range(0,13): 
    if k in segs: print(k, round(segs[k][2]))
