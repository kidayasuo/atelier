exec(open('/tmp/claude-0/t/ideas/dots_base.py').read())
zone=free
def at(k,u):  # point at main frame k (fractional), radial distance u beyond the west column line
    return np.array(world(bm,th(bm,k),12000+u,0)[:2])
def circ(k,u,r): return SPt(*at(k,u)).buffer(r,resolution=32)
# I1: kitchen dot at hall centre
best=None
for rk in np.arange(4000,7001,250):
  for kk in np.arange(9.5,12.01,0.25):
    K=circ(kk,700+rk,rk)
    if not zone.contains(K): continue
    for rp in np.arange(5500,8001,250):
      for d in np.arange(0.6*rp,1.8*rp,250):     # centre spacing of the two playroom dots
        for k1 in np.arange(2,9,0.25):
          A=circ(k1,700+rp,rp)
          # second circle north of first, spacing d along spine (approx 1 frame = 3000 at spine)
          k0=k1-d/3000.0
          B=circ(k0,700+rp,rp)
          Pl=A.union(B)
          if not zone.contains(Pl): continue
          if Pl.intersection(K).area>2e6: continue
          gapk=Pl.distance(K)
          if gapk>3000: continue
          a=Pl.area/1e6
          if a<240: continue
          score=a+K.area/1e6*0.3
          if best is None or score>best[0]: best=(score,rk,kk,rp,d,k1,a,K.area/1e6,gapk)
print('I1',best)
