exec(open('/tmp/claude-0/t/ideas/case3.py').read().replace("model.Write('/home/claude/plans/rhino/sodachiya_west_case3.3dm',8)","pass").replace("print(","(lambda *a:None)("))
import pickle; W=pickle.load(open('/tmp/claude-0/t/exact/wnew.pkl','rb'))['WN']
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
plt.rcParams['font.family']='IPAGothic'
SC=200.0; MM=1/25.4
xs=[p[0] for p in site.exterior.coords]; ys=[p[1] for p in site.exterior.coords]
mx=12000; x0,x1=min(xs)-mx,max(xs)+mx; y0,y1=min(ys)-mx,max(ys)+mx
wmm=(x1-x0)/SC; hmm=(y1-y0)/SC
fig=plt.figure(figsize=(wmm*MM,hmm*MM)); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(x0,x1); ax.set_ylim(y0,y1); ax.set_aspect('equal'); ax.axis('off')
LW=0.12
def pl(pts,c='k',lw=LW,ls='-'):
    pts=list(pts); ax.plot([p[0] for p in pts],[p[1] for p in pts],color=c,lw=lw,ls=ls,solid_capstyle='butt')
# 敷地・1m 線・公園・駐車場
pl(site.exterior.coords,'k',0.2)
pl(setb.exterior.coords,'#888',LW,(0,(6,4)))
# 本館
th=lambda k: thf(k)
mwp=lambda k,u: world(bm,th(k),u,0)[:2]
ks=np.linspace(0,19,200)
out=[mwp(k,-3000) for k in ks]+[mwp(k,12200) for k in ks[::-1]]; out.append(out[0]); pl(out,'#808080',1.0)
for u in (0,12000): pl([mwp(k,u) for k in ks],'k',0.2)
pl([mwp(k,10400) for k in ks],'k',0.2)                              # 教室と西廊下（1.6 m）の境          # 柱の列
for k in range(20): pl([mwp(k,-3000),mwp(k,12200)],'k',0.2)        # 3 m スパンの線（架構）
# 西館
pl(W.exterior.coords,'#808080',1.0)
for k in range(2,13):
    try: a,b,L=segx(k)
    except Exception: continue
    pl([a,b],'k',0.2)
# 機械室
pl(MECH.exterior.coords,'#808080',1.0)
# 縮尺と方位
bx,by=x0+4000,y0+4000
for i in range(5):
    ax.add_patch(plt.Rectangle((bx+i*2000,by),2000,350,fc='k' if i%2==0 else 'none',ec='k',lw=0.1))
ax.text(bx,by+700,'0',fontsize=4); ax.text(bx+10000,by+700,'10 m',fontsize=4,ha='center'); ax.text(bx+11500,by+100,'1/200（A判ではなく実寸の用紙）',fontsize=3.5)
nx,ny=x1-5000,y1-6000
ax.annotate('',xy=(nx,ny+2500),xytext=(nx,ny-1500),arrowprops=dict(arrowstyle='-|>',lw=0.2,color='k',mutation_scale=4)); ax.text(nx,ny+2900,'N',ha='center',fontsize=5)
fig.patch.set_alpha(0); ax.patch.set_alpha(0); fig.savefig('/home/claude/plans/rhino/site_sketch_base_1-200.pdf',transparent=True); print('page mm',round(wmm),round(hmm))
