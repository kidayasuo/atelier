exec(open('/tmp/claude-0/t/opt/base.py').read())
import json
edges={'北東(隣家)':((0,0),(34860,-43830)),'南東(川)':((34860,-43830),(-14440,-83040)),'南西(橋)':((-14440,-83040),(-21910,-73650)),'西(道路)':((-21910,-73650),(-25830,-20540)),'北西(大学)':((-25830,-20540),(0,0))}
for Rs,gap,v,s,pm,pw in json.load(open('/tmp/claude-0/t/opt/refined2.json')):
    r=evaluate(Rs,(v[0],v[1]),v[2],gap,detail=True); bm,bw,main,west=r['geo']
    col=band(bm,0,19,0,12200)  # main without eave
    out=[]
    for nm,poly in (('本館(庇含む)',main),('本館(柱)',col),('西館',west)):
        d={}
        for en,(a,b) in edges.items():
            L=SL([a,b]); m=min(L.distance(SPt(p)) for p in poly.exterior.coords)
            d[en]=round(m/1000,2)
        out.append((nm,{k:v for k,v in d.items() if v<2.5}))
    print(Rs//1000,out)
