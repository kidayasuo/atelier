WSHIFT=1000.0
exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
print('W area',W.area/1e6,'to site',W.distance(site.exterior)/1000,'outside setb m2',W.difference(setb).area/1e6,'to parking',W.distance(D['pk'])/1000)
cs=np.array(W.exterior.coords)
print('k range',min(ku(c)[0] for c in cs),max(ku(c)[0] for c in cs))
print('kk',kk[0],kk[-1])
o=W.difference(setb)
for g in getattr(o,'geoms',[o]): print('outside at k',ku(g.centroid.coords[0])[0],'area',g.area/1e6)
W0=W
