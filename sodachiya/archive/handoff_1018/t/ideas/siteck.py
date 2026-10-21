exec(open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- model')[0].replace('print(','(lambda *a:None)('))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']='IPAGothic'
pk=D['pk']; print('W area',W.area/1e6)
print('W to site boundary',W.distance(site.exterior)/1000)
print('W to parking',W.distance(pk)/1000, 'W to park',W.distance(park)/1000)
fig,ax=plt.subplots(figsize=(10,10))
for g,c in ((site,'k'),(setb,'#999'),(park,'g'),(pk,'b'),(W,'r')):
    for q in getattr(g,'geoms',[g]): ax.plot(*q.exterior.xy,color=c,lw=1)
mainP=SP([world(bm,thf(k),u,0)[:2] for k in np.linspace(0,19,30) for u in [0]]+[world(bm,thf(k),12200,0)[:2] for k in np.linspace(19,0,30)])
ax.plot(*mainP.exterior.xy,color='#555')
for k in range(0,20):
    a=at(k,-3000); b=at(k,16000); ax.plot([a[0],b[0]],[a[1],b[1]],color='#ddd',lw=.5); ax.text(*b,str(k),fontsize=7)
ax.set_aspect('equal'); plt.savefig('/tmp/claude-0/t/ideas/siteck.png',dpi=70)
# distances of W boundary to site boundary, per region
cs=np.array(W.exterior.coords)
for c in cs[::8]:
    print(round(ku(c)[0],2), round(SPt(*c[:2]).distance(site.exterior)/1000,2))
