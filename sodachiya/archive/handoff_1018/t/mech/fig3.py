import json
PLACE_OVERRIDE=json.load(open('/tmp/claude-0/t/mech/opt1.json'))
exec(open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- model')[0].replace("print(","(lambda *a:None)("))
import pickle
from shapely import affinity as af
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
plt.rcParams['font.family']='IPAGothic'
NEl=SL([(0,0),(34860,-43830)]); NWl=SL([(-25830,-20540),(0,0)])
d=pickle.load(open('/tmp/claude-0/t/mech/m46_shift.pkl','rb')); F=d['F']; td=d['td']; nin=d['nin']
mainP=band(bm,0,19,-3000,12200)
# 1: 延長スパン
ext=band(bm,-1,0,-3000,12200); extb=band(bm,-1,0,0,12200)
o1=dict(poly=ext,area=extb.area/1e6,ne=NEl.distance(ext)/1000,nw=NWl.distance(extb)/1000)
# 4: 道路沿いの細長い棟
W0=np.array([-25830,-20540.0]); best=None
for T in (3.0,):
    Lr=30.0/T*1000
    for s in np.arange(15000,33000,100):
        p0=W0+td*s+nin*1050
        r=SP([tuple(p0),tuple(p0+td*Lr),tuple(p0+td*Lr+nin*T*1000),tuple(p0+nin*T*1000)])
        if F.contains(r):
            sc=(NEl.distance(r),)
            if best is None or sc>best[3]: best=(T,Lr,s,sc,r)
    if best: break
T4,L4,s4,_,r4=best
o4=dict(poly=r4,area=r4.area/1e6,ne=NEl.distance(r4)/1000,T=T4,L=L4/1000)
# 6: 楕円（長短比 1.6、隣家から最も離れる位置）
ab=30e6/math.pi; asp=1.6; a=math.sqrt(ab*asp); b=ab/a; best=None
mn=F.bounds
for ang in np.arange(0,180,3):
    for x in np.arange(mn[0],mn[2],200):
        for y in np.arange(mn[1],mn[3],200):
            e=af.rotate(af.scale(SPt(x,y).buffer(1000,resolution=48),a/1000,b/1000),ang,origin=(x,y))
            if F.contains(e):
                sc=NEl.distance(e)
                if best is None or sc>best[0]: best=(sc,ang,x,y,e)
o6=dict(poly=best[4],area=best[4].area/1e6,ne=best[0]/1000,ang=best[1],a=a/1000,b=b/1000)
pickle.dump(dict(o1=o1,o4=o4,o6=o6),open('/tmp/claude-0/t/mech/opts.pkl','wb'))
print('1',o1['area'],o1['ne']); print('4',o4['T'],o4['L'],o4['area'],o4['ne']); print('6',o6['a']*2,o6['b']*2,o6['ang'],o6['ne'])
fig,axs=plt.subplots(1,3,figsize=(18,7.5))
cx,cy=np.array(F.centroid.coords[0])
for ax,(name,o,col) in zip(axs,[('1. 本館を1スパン延ばす',o1,'#d9a35f'),('4. 道路に沿う細長い棟',o4,'#d9a35f'),('6. 楕円',o6,'#d9a35f')]):
    ax.plot(*site.exterior.xy,color='k',lw=1.2); ax.plot(*setb.exterior.xy,color='#999',lw=.6,ls='--')
    ax.add_patch(MP(list(mainP.exterior.coords),fc='#eee',ec='#555',lw=.8))
    for k in range(20): p=world(bm,thf(k),-3000,0)[:2]; q=world(bm,thf(k),12200,0)[:2]; ax.plot([p[0],q[0]],[p[1],q[1]],color='#bbb',lw=.4)
    ax.add_patch(MP(list(W.exterior.coords),fc='#e6eef7',ec='#555',lw=.8))
    ax.add_patch(MP(list(o['poly'].exterior.coords),fc=col,ec='k',lw=1))
    if name.startswith('1'):
        for k in (-1,0): p=world(bm,thf(k),-3000,0)[:2]; q=world(bm,thf(k),12200,0)[:2]; ax.plot([p[0],q[0]],[p[1],q[1]],color='k',lw=.6)
    ax.set_xlim(cx-17000,cx+17000); ax.set_ylim(cy-15000,cy+13000); ax.set_aspect('equal'); ax.axis('off')
    txt='%s\n面積 %.0f m²　隣家まで %.1f m'%(name,o['area'],o['ne'])
    if 'T' in o: txt+='\n%.1f m × %.1f m'%(o['T'],o['L'])
    if 'ang' in o: txt+='\n%.1f m × %.1f m（長短比 1.6）'%(o['a']*2,o['b']*2)
    ax.set_title(txt,fontsize=11,pad=14)
    rp=W0+td*24000-nin*1800; ax.text(rp[0],rp[1],'北の道路（大学側）',rotation=38.5,fontsize=9,color='#555',ha='center',va='center')
    npnt=np.array([6500,-8200])+np.array([0.78,0.62])*1500; ax.text(npnt[0],npnt[1],'隣家',rotation=-51.5,fontsize=9,color='#555',ha='center',va='center')
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/machine_options.png',dpi=80)
print('garden etc', evalc(205000,*PLACE_OVERRIDE,'tri')[:3])
