import pickle,numpy as np,math
from shapely.geometry import Polygon as SP, LineString as SL, Point as SPt
for PL in ('cur','shift'):
    d=pickle.load(open('/tmp/claude-0/t/mech/m46_%s.pkl'%PL,'rb')); F=d['F']; td=d['td']; nin=d['nin']
    W0=np.array([-25830,-20540.0]); best={}
    for T in (2.0,2.4,3.0):
        for s in np.arange(15000,33000,200):
            for Lr in np.arange(4000,16001,250):
                p0=W0+td*s+nin*1050
                r=SP([tuple(p0),tuple(p0+td*Lr),tuple(p0+td*Lr+nin*T*1000),tuple(p0+nin*T*1000)])
                if F.contains(r) and Lr>best.get(T,(0,))[0]: best[T]=(Lr,s)
    print(PL,{T:(round(v[0]/1000,2),round(T*v[0]/1000,1)) for T,v in best.items()})
    # 道路の 1m 線上の三角の脚の長さ
    p=W0+nin*1050; ln=SL([tuple(p),tuple(p+td*40000)]).intersection(F)
    print('  road-leg length in F %.1f'%(ln.length/1000))
