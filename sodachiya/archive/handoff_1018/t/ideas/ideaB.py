exec(open('common.py').read())
W=np.array(V['W']); bis=unit(unit(np.array(V['N'])-W)+unit(np.array(V['SW'])-W))
NEl=SL([V['N'],V['E']])
best=None
for Rs in range(26000,48001,2000):
  span=57000/Rs
  for d in range(0,40001,2000):
    for rot in np.radians(np.arange(-20,21,2)):
      C=W+bis*d; mid=math.atan2(bis[1],bis[0])+rot
      a0,a1=mid-span/2,mid+span/2
      main=annulus(C,Rs-200,Rs+15000,a0,a1)
      if not setb.contains(main) or main.intersects(park.buffer(1000)) or NEl.distance(main)<1000: continue
      inner=site.intersection(annulus(C,0,Rs-900,a0-0.3,a1+0.3)).area/1e6
      g=site.difference(unary_union([main,park])).area/1e6
      # garden outside the fan only (convex side)
      outer=site.difference(unary_union([main,park,SPt(*C).buffer(Rs)])).area/1e6
      key=outer
      if inner<520: continue
      if best is None or key>best[0]: best=(key,Rs,d,math.degrees(rot),inner)
print(best)
