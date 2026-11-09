exec(open('/tmp/claude-0/t/ideas/case3.py').read().replace("model.Write(","_w=(").replace("print('written')",""))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPo
plt.rcParams['font.family']='IPAGothic'
# plans
fig,axs=plt.subplots(1,2,figsize=(16,9))
cols1={'遊戯室':'#CDE0F2','キッチン':'#BED7EE','土間':'#FAE9B8','食べる土間':'#F5DEA0','階段':'#786E64'}
cols2={'ホール2':'#F0F0F0','便所・湯沸':'#D2D2D2','会議室':'#DCCDF0','休憩室':'#E8DDF3','ぐったり休憩':'#F5E1EB','吹抜':'#FFFFFF'}
thm=(bm['thetas'][0]+bm['thetas'][-1])/2; rot=math.pi-thm
def T(x,y): c,s_=math.cos(rot),math.sin(rot); return (x*c-y*s_, x*s_+y*c)
def draw(ax,R,cols,title,show_play=True):
    mainpoly=SP([world(bm,thf(k),u,0)[:2] for k,u in [(kk_,0) for kk_ in np.linspace(0,19,30)]]+[world(bm,thf(k),12200,0)[:2] for k in np.linspace(19,0,30)])
    ax.add_patch(MPo([T(*p) for p in mainpoly.exterior.coords],fc='#eeeeee',ec='#999',lw=.6))
    ax.add_patch(MPo([T(*p) for p in W.exterior.coords],fc='#fafafa',ec='k',lw=1.2))
    for n,p in sorted(R.items(),key=lambda x: x[0]!='遊戯室'):
        for g in getattr(p,'geoms',[p]):
            if g.area<1e5: continue
            ax.add_patch(MPo([T(*q) for q in g.exterior.coords],fc=cols[n],ec='#333',lw=.6,ls='--' if n=='吹抜' else '-'))
            c=g.representative_point(); x,y=T(c.x,c.y)
            ax.text(x,y,'%s\n%.0f㎡'%(n.replace('2',''),g.area/1e6),ha='center',va='center',fontsize=7,color='w' if n=='階段' else 'k')
    for q in WCOLS:
        x,y=T(q[0],q[1]); ax.plot(x,y,'s',ms=3.5,color='#6b4a2b')
    for q in SCOLS:
        x,y=T(q.x,q.y); ax.plot(x,y,'s',ms=3.5,color='#6b4a2b')
    if show_play:
        up=region(K2,KEND+1,0,60000)
        for g in getattr(up,'geoms',[up]):
            ax.plot(*zip(*[T(*q) for q in g.exterior.coords]),ls=(0,(4,3)),color='#7a3b8f',lw=1)
        lo=R1['遊戯室'].intersection(region(K2,KH,0,60000)); up=region(K2,KEND+1,0,60000); c=lo.representative_point(); x,y=T(c.x,c.y)
        ax.text(x,y,'2階の下\n天井 約3.1m（梁下 2.45m）',ha='center',va='center',fontsize=6,color='#7a3b8f')
    xs=[T(*p) for p in W.exterior.coords]
    ax.set_xlim(min(p[0] for p in xs)-3000,max(p[0] for p in xs)+16000); ax.set_ylim(min(p[1] for p in xs)-3000,max(p[1] for p in xs)+3000)
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title)
draw(axs[0],R1,cols1,'西館 1 階（上が北、右が本館、■ は柱、紫の破線は 2 階の範囲）')
draw(axs[1],R2,cols2,'西館 2 階',show_play=False)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_case3_plans.png',dpi=72)
