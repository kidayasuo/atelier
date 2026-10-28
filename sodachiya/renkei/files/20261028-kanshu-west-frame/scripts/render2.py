from ana import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
st=sys.argv[1]; P=pickle.load(open(f'st/{st}.3dm.pk','rb'))
for p in P: p['tc']=float((p['t'].min()+p['t'].max())/2)
def draw(ax,pg,**kw):
    if pg is None or pg.is_empty: return
    for g in getattr(pg,'geoms',[pg]):
        if g.geom_type!='Polygon': continue
        x,y=g.exterior.xy; ax.plot(np.array(x)/1000,y,**kw)
        for r in g.interiors: x,y=r.xy; ax.plot(np.array(x)/1000,y,ls=':',**kw)
def shot(name,f,v0,v1,z0,z1,title):
    fig,axs=plt.subplots(1,3,figsize=(15,5.5),sharey=True)
    for ax,(tt,lab) in zip(axs,[(-135,'ply t=-135 (−u side)'),(0,'column plane t=0'),(135,'ply t=+135 (+u side)')]):
        for p in P:
            if p['f']!=f and p['ln']!='22d': continue
            if p['tm'].bounds[1][2]<z0 or p['tm'].bounds[0][2]>z1: continue
            s=section(p['tm'],f,tt)
            if s is None or s.is_empty: continue
            col={'22a':'tab:red','22b':'tab:blue','22c':'tab:green','22d':'k'}[p['ln']]
            draw(ax,s,color=col,lw=1.3 if p['ln']!='22d' else 2.0)
        ax.set_xlim(v0,v1); ax.set_ylim(z0,z1); ax.set_aspect(1/1000); ax.set_title(lab,fontsize=9); ax.set_xlabel('v (m)'); ax.grid(alpha=.3)
    axs[0].set_ylabel('z (mm)')
    fig.suptitle(f'{title}\nred=柱22a blue=梁22b green=2階床梁22c black=桁22d (girder section); dotted=holes'.replace('柱22a','col 22a').replace('梁22b','beam 22b').replace('2階床梁22c','floor beam 22c').replace('桁22d','girder 22d'),fontsize=10)
    fig.savefig(f'png/{name}.png',dpi=95,bbox_inches='tight'); plt.close(fig)
import os; os.makedirs('png',exist_ok=True)
shot(f'{st}_01_u30_east_head',30,-2.0,-0.8,6500,8200,f'[{st}] u30 east column head / roof beam east end')
shot(f'{st}_02_u30_west_joint',30,-13.8,-12.3,3900,4900,f'[{st}] u30 west joint (column head, 2 plies, west girder)')
shot(f'{st}_03_u21_south_west',21.33,-11.4,-9.6,3900,5400,f'[{st}] u21.33 south end frame, west joint')
shot(f'{st}_04_u48_west',48,-10.2,-8.6,3900,4900,f'[{st}] u48 north end frame, west joint')
shot(f'{st}_05_u21_floorbeam',21.33,-11.0,-0.6,2100,3300,f'[{st}] u21.33 2F floor beam (whole length)')
shot(f'{st}_06_u27_floor_west',27,-13.6,-12.2,2300,3300,f'[{st}] u27 2F floor beam west end')
