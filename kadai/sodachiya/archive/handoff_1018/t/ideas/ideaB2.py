exec(open('common.py').read())
W=np.array(V['W']); bis=unit(unit(np.array(V['N'])-W)+unit(np.array(V['SW'])-W))
NEl=SL([V['N'],V['E']])
res=[]
for Rs in range(20000,70001,2500):
  span=57000/Rs
  for d in range(-10000,50001,2500):
    for rot in np.radians(np.arange(-30,31,3)):
      C=W+bis*d; mid=math.atan2(bis[1],bis[0])+rot
      a0,a1=mid-span/2,mid+span/2
      main=annulus(C,Rs-200,Rs+15000,a0,a1)
      out=main.difference(setb).area/1e6
      bad=out+ main.intersection(park.buffer(1000)).area/1e6*5 + max(0,1000-NEl.distance(main))/100
      inner=site.intersection(SPt(*C).buffer(Rs-900)).difference(main).area/1e6
      outer=site.difference(unary_union([main,park,SPt(*C).buffer(Rs)])).area/1e6
      res.append((round(bad,1),-round(outer),Rs,d,round(math.degrees(rot)),round(inner)))
res.sort()
for r in res[:12]: print(r)
