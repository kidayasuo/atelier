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
if 'W_OVERRIDE' in globals(): W=W_OVERRIDE                          # 2026-10-19：最新の西館の輪郭（wnew.pkl）を差し込む
# radial segments through W
ks=np.arange(-1,14,0.125)
segs={}
for k in ks:
    L=SL([tuple(at(k,0)),tuple(at(k,60000))]).intersection(W)
    if L.is_empty: continue
    if L.geom_type!='LineString': L=max(L.geoms,key=lambda g:g.length)
    if L.length<1000:                                            # 輪郭の直線の端（架構 2・12）にちょうど乗る線：少し内側で測る
        for eps in (0.01,-0.01):
            L2=SL([tuple(at(k+eps,0)),tuple(at(k+eps,60000))]).intersection(W)
            if not L2.is_empty:
                if L2.geom_type!='LineString': L2=max(L2.geoms,key=lambda g:g.length)
                if L2.length>1000: L=L2; break
        if L.length<1000: continue
    a,b=np.array(L.coords[0]),np.array(L.coords[-1])
    o=at(k,0)
    if np.linalg.norm(a-o)>np.linalg.norm(b-o): a,b=b,a
    segs[round(k,3)]=(a,b,np.linalg.norm(b-a))
kk=sorted(segs)
Ls=np.array([segs[k][2] for k in kk])
print('frames',kk[0],kk[-1],'L range',Ls.min(),Ls.max())
for k in range(0,13): 
    if k in segs: print(k, round(segs[k][2]))
