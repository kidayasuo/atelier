exec(open('/tmp/claude-0/t/ideas/dots_base.py').read())
q0=SPt(*(hall_w+west_dir*5000))
west=[q for q in getattr(free,'geoms',[free]) if q.contains(q0)][0]
print('west free', round(west.area/1e6), [round(v) for v in west.bounds])
pl=polylabel(west,tolerance=100); print('max r', round(west.exterior.distance(pl)), pl)
# width profile: distance across from main to road along main frames
for k in range(0,20,2):
    p=np.array(world(bm,th(bm,k),12200,0)[:2]); d=unit(np.array(world(bm,th(bm,k),30000,0)[:2])-p)
    L=SL([tuple(p),tuple(p+d*40000)]).intersection(setb)
    print(k, 'width to setback', round(L.length) if not L.is_empty else None)
