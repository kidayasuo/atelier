exec(open('/tmp/claude-0/t/ideas/common.py').read())
import sys
sys.path.insert(0,'/tmp/claude-0/mock2')
import Rhino.Geometry as rg
from shapely.ops import polylabel
exec(open('/tmp/claude-0/t/site.py').read())
P=rg.Point3d
g0=run(R=205.0, MainSE=P(5870,-66029,0), MainNE=P(7676,-14301,0))
print([l for l in g0['Report'].split('\n') if '点' in l])
bm,bw=g0['buildings'](); world=g0['world']
th=lambda B,k: B['thetas'][0]+(B['thetas'][1]-B['thetas'][0])*k
def mpoly(k0,k1,u0,u1,n=24):
    a=[world(bm,th(bm,k0+(k1-k0)*i/n),u0,0)[:2] for i in range(n+1)]
    b=[world(bm,th(bm,k1-(k1-k0)*i/n),u1,0)[:2] for i in range(n+1)]
    return SP(a+b)
mrooms=[(1,3,'0・1歳','#F4D9C6'),(4,5,'2歳','#F4D9C6'),(6,7,'事務・医務','#E3E3E3'),(8,10,'ホール','#F6D27A'),(11,11,'','#E3E3E3'),(12,13,'3歳','#F9E7C9'),(14,14,'','#E3E3E3'),(15,16,'4歳','#F9E7C9'),(17,17,'','#E3E3E3'),(18,19,'5歳','#F9E7C9')]
main=mpoly(0,19,-3000,12200)
hall=mpoly(9,12,0,12000)
hall_w=np.array(world(bm,th(bm,10.5),12000,0)[:2])   # ホールの西面の中央
west_dir=unit(np.array(world(bm,th(bm,10.5),20000,0)[:2])-hall_w)
free=setb.difference(main.buffer(700)).difference(park.buffer(1000))
def draw_main(ax,f):
    f(mpoly(0,19,-3000,0),'#f3efe2',ec='#bbb',lw=.3)
    for s0,s1,t,c in mrooms:
        p=mpoly(19-s1,20-s0,0,12000); f(p,c); lab(ax,p,t,fs=6)
