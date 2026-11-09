exec(open('/tmp/claude-0/t/opt/base.py').read())
import random, json
random.seed(1)
def score(Rs,x,y,ang,gap):
    r=evaluate(Rs,(x,y),ang,gap)
    s=0
    s+=r['out_site']*1000+max(0,1000-r['ne'])*1.0+r['park']*200+(0 if r['parking'] is not None else 300)
    s+=r['out_set']*30
    s-=max(-1,r['margin'])/100.0   # 余裕（mm）を少し好む
    return s,r
best=[]
for i in range(15000):
    Rs=random.choice([100,120,140,160,180,205,230,260,300,350,400,500,700,1000])*1000
    ang=random.uniform(75,100); gap=random.choice([700,800,900,1000])
    x=random.uniform(-6000,14000); y=random.uniform(-74000,-58000)
    s,r=score(Rs,x,y,ang,gap)
    best.append((s,Rs,x,y,ang,gap))
best.sort()
for b in best[:15]: print([round(v,1) for v in b])
json.dump(best[:40],open('/tmp/claude-0/t/opt/best1.json','w'))
