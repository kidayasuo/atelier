exec(open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- model')[0].replace("print(","(lambda *a:None)("))
from shapely import affinity as af
NEl=SL([(0,0),(34860,-43830)]); NWl=SL([(-25830,-20540),(0,0)])
mainP=band(bm,0,19,-3000,12200)
# 北の三角：本館の架構 0 の線より北
a_=np.array(world(bm,thf(0),-40000,0)[:2]); b_=np.array(world(bm,thf(0),60000,0)[:2]); t_=(b_-a_)/np.linalg.norm(b_-a_); n_=np.array([-t_[1],t_[0]])
if np.dot(n_,np.array(world(bm,thf(0),5000,0)[:2])-np.array(world(bm,thf(3),5000,0)[:2]))<0: n_=-n_
north=SP([tuple(a_),tuple(b_),tuple(b_+n_*60000),tuple(a_+n_*60000)])
F=site.intersection(north).difference(unary_union([mainP,W]).buffer(1500)).difference(NEl.buffer(1000)).intersection(setb.buffer(0))
F=max(getattr(F,'geoms',[F]),key=lambda g:g.area)
print('free area',F.area/1e6)
# --- 4: 道路に沿う細長い棟
td=np.array([25830,20540.0]); td/=np.linalg.norm(td)          # 道路の向き（W→N）
nin=np.array([td[1],-td[0]])                                     # 道路から敷地の内側へ
if not site.contains(SPt(*(np.array([-12000,-9500])+nin*3000))): nin=-nin
W0=np.array([-25830,-20540.0])
best4=[]
for T in (2.5,3.0):
    Lr=30.0/T*1000
    for s in np.arange(0,33000,250):
        p0=W0+td*s+nin*1000
        r=SP([tuple(p0),tuple(p0+td*Lr),tuple(p0+td*Lr+nin*T*1000),tuple(p0+nin*T*1000)])
        if F.contains(r):
            best4.append((T,s,NEl.distance(r)/1000,mainP.distance(r)/1000,W.distance(r)/1000,r))
for T in (2.5,3.0):
    c=[b for b in best4 if b[0]==T]
    if c: print('4: T',T,'s range',c[0][1],c[-1][1],'NE dist max %.1f'%max(b[2] for b in c))
# --- 6: 楕円
best6=None
def ell(cx,cy,a,b,ang):
    e=af.scale(SPt(cx,cy).buffer(1000,resolution=32),a/1000,b/1000)
    return af.rotate(e,ang,origin=(cx,cy))
ab=30e6/math.pi
res6=[]
road_ang=math.degrees(math.atan2(td[1],td[0]))
mn=F.bounds
for asp in (1.3,1.6,2.0):
    a=math.sqrt(ab*asp); b=ab/a
    for ang in np.arange(0,180,7.5):
        for x in np.arange(mn[0],mn[2],400):
            for y in np.arange(mn[1],mn[3],400):
                e=ell(x,y,a,b,ang)
                if F.contains(e):
                    res6.append((asp,ang,x,y,NEl.distance(e)/1000,mainP.distance(e)/1000,e))
print('6: candidates',len(res6))
for asp in (1.3,1.6,2.0):
    c=[r for r in res6 if r[0]==asp]
    if c:
        r=max(c,key=lambda r:r[4]); print('asp',asp,'best NE dist %.1f ang %.0f (road %.0f) main %.1f'%(r[4],r[1],road_ang%180,r[5]))
import pickle; pickle.dump(dict(F=F,best4=best4,res6=res6,td=td,nin=nin,road_ang=road_ang),open('/tmp/claude-0/t/mech/m46.pkl','wb'))
