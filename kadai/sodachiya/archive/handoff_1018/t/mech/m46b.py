import json,pickle,sys
PL=sys.argv[1]
src=open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- model')[0].replace("print(","(lambda *a:None)(")
if PL=='shift':
    PLACE_OVERRIDE=json.load(open('/tmp/claude-0/t/mech/opt1.json'))
exec(src)
from shapely import affinity as af
NEl=SL([(0,0),(34860,-43830)])
mainP=band(bm,0,19,-3000,12200)
a_=np.array(world(bm,thf(0),-40000,0)[:2]); b_=np.array(world(bm,thf(0),60000,0)[:2]); t_=(b_-a_)/np.linalg.norm(b_-a_); n_=np.array([-t_[1],t_[0]])
if np.dot(n_,np.array(world(bm,thf(0),5000,0)[:2])-np.array(world(bm,thf(3),5000,0)[:2]))<0: n_=-n_
north=SP([tuple(a_),tuple(b_),tuple(b_+n_*60000),tuple(a_+n_*60000)])
CB=700.0
F=setb.intersection(north).difference(unary_union([mainP,W]).buffer(CB))
F=max(getattr(F,'geoms',[F]),key=lambda g:g.area)
print(PL,'free area %.1f'%(F.area/1e6),'W area',W.area/1e6)
td=np.array([25830,20540.0]); td/=np.linalg.norm(td); nin=np.array([td[1],-td[0]])
if not site.contains(SPt(*(np.array([-12000,-9500])+nin*3000))): nin=-nin
W0=np.array([-25830,-20540.0])
r4=[]
for T in (2.4,2.7,3.0):
    for Lr in np.arange(30.0/T*1000,30.0/T*1000+6001,1000):
        for s in np.arange(0,33000,200):
            p0=W0+td*s+nin*1000
            r=SP([tuple(p0),tuple(p0+td*Lr),tuple(p0+td*Lr+nin*T*1000),tuple(p0+nin*T*1000)])
            if F.contains(r): r4.append((T,Lr,s,NEl.distance(r)/1000,r))
print('4 candidates',len(r4))
for T in (2.4,2.7,3.0):
    c=[b for b in r4 if b[0]==T]
    if c: b=max(c,key=lambda b:(b[1],b[3])); print(' T %.1f maxL %.1f area %.0f NE %.1f'%(T,b[1]/1000,T*b[1]/1000,b[3]))
ab=30e6/math.pi; res6=[]
mn=F.bounds
for asp in (1.0,1.3,1.6,2.0,2.5):
    a=math.sqrt(ab*asp); b=ab/a
    for ang in np.arange(0,180,7.5):
        for x in np.arange(mn[0],mn[2],300):
            for y in np.arange(mn[1],mn[3],300):
                e=af.rotate(af.scale(SPt(x,y).buffer(1000,resolution=32),a/1000,b/1000),ang,origin=(x,y))
                if F.contains(e): res6.append((asp,ang,x,y,NEl.distance(e)/1000,e))
print('6 candidates',len(res6))
for asp in (1.0,1.3,1.6,2.0,2.5):
    c=[r for r in res6 if r[0]==asp]
    if c: r=max(c,key=lambda r:r[4]); print(' asp %.1f NE %.1f ang %.0f'%(asp,r[4],r[1]))
pickle.dump(dict(F=F,r4=r4,res6=res6,td=td,nin=nin,W=W,main=mainP,site=site,setb=setb,bm=bm),open('/tmp/claude-0/t/mech/m46_%s.pkl'%PL,'wb'))
