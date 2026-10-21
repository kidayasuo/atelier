exec(open('/tmp/claude-0/t/ideas/hill2_core.py').read())
import shapely
play=W.intersection(SP([tuple(at(1.0,0))]+[tuple(at(k,0)) for k in np.linspace(1,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,1,20)]))
xs=np.arange(play.bounds[0],play.bounds[2],250); ys=np.arange(play.bounds[1],play.bounds[3],250)
tot=0; h={0.9:0,1.4:0,2.1:0,3.0:0}
for x in xs:
    for y in ys:
        if play.contains(SPt(x,y)):
            tot+=1; z=(zat2((x,y))-300)/1000
            for t in h:
                if z>=t: h[t]+=1
c=0.0625
print('playroom floor %.0f m2'%(tot*c), {k:'%.0f'%(v*c) for k,v in h.items()})
