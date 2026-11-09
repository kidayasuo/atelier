exec(open('/tmp/claude-0/t/ideas/hill2_core.py').read())
play=W.intersection(SP([tuple(at(1.0,0))]+[tuple(at(k,0)) for k in np.linspace(1,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,1,20)]))
pts=[]
xs=np.arange(play.bounds[0],play.bounds[2],300); ys=np.arange(play.bounds[1],play.bounds[3],300)
for x in xs:
    for y in ys:
        if play.contains(SPt(x,y)): pts.append((x,y))
sL=np.r_[0,np.cumsum(np.linalg.norm(np.diff(np.array([segs[k][1] for k in kk]),axis=0),axis=1))]
for ZR,ZO,K2,SINK in [(4500,2400,9.0,0),(5000,2600,8.0,0),(5000,2600,8.0,800),(5500,2800,8.0,600),(4500,2400,9.0,1000),(5000,2400,7.0,800)]:
    def lines(k,ZR=ZR,ZO=ZO,K2=K2):
        t=np.clip((k-1.6)/(K2-1.6),0,1); zr=400+(ZR-400)*ss(t); zo=400+(ZO-400)*np.clip((k-1.6)/(KH-1.6),0,1); return zr-150,zr,zo
    globals()['lines']=lines
    hs=np.array([(zat2(p)-300+SINK)/1000 for p in pts])
    c=0.09
    zr=np.array([lines(k)[1] for k in kk if k<=KH]); g=np.gradient(zr,sL[:len(zr)])
    print('ridge %.1f eave %.1f top@k%.0f sink %.1f'%(ZR/1000,ZO/1000,K2,SINK/1000),'| floor %.0f, >=2.1m %.0f, >=3m %.0f | ridge max slope %.0f°'%(len(pts)*c,(hs>=2.1).sum()*c,(hs>=3).sum()*c,np.degrees(np.arctan(g.max()))))
