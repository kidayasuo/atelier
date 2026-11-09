exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
play=W.intersection(SP([tuple(at(1.0,0))]+[tuple(at(k,0)) for k in np.linspace(1,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,1,20)]))
pts=[(x,y) for x in np.arange(play.bounds[0],play.bounds[2],300) for y in np.arange(play.bounds[1],play.bounds[3],300) if play.contains(SPt(x,y))]
for sink in (0,300,450,600,800):
    h=np.array([(zat2(p)-300+sink)/1000 for p in pts])
    print('sink %.2f avg ceiling %.2f  1/3=%.2f  ->'%(sink/1000,h.mean(),h.mean()/3), '地階にならない' if sink/1000<h.mean()/3 else '地階', '| >=1.4m %.0f ㎡ >=2.1m %.0f ㎡'%((h>=1.4).sum()*0.09,(h>=2.1).sum()*0.09))
