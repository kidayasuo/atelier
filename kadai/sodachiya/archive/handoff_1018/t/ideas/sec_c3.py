import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon
plt.rcParams['font.family']='IPAGothic'
ZE,ZW,Z2,L,CL=8000,4500,3250,12300,2500
zr=lambda d: ZE+(ZW-ZE)*d/L
X=lambda d: -d/1000
fig,ax=plt.subplots(figsize=(14,7.5))
# roof deck (150) and beam behind (700)
ax.add_patch(Polygon([(X(0),zr(0)/1000),(X(L),zr(L)/1000),(X(L),(zr(L)+150)/1000),(X(0),(zr(0)+150)/1000)],fc='#8a7a66',ec='k',lw=.8))
ax.add_patch(Polygon([(X(0),zr(0)/1000),(X(L),zr(L)/1000),(X(L),(zr(L)-700)/1000),(X(0),(zr(0)-700)/1000)],fc='#c9a77c',ec='#7a5a3a',lw=.6,alpha=.55,hatch='///'))
# 2F slab and floor beam behind
ax.add_patch(Rectangle((X(L-200),(Z2-80)/1000),(L-200-1000)/1000,.08,fc='#777',ec='k',lw=.6))
ax.add_patch(Rectangle((X(L-200),(Z2-600)/1000),(L-200)/1000,.52,fc='#c9a77c',ec='#7a5a3a',lw=.6,alpha=.4,hatch='///'))
for d in (200,CL,L-200):
    ax.add_patch(Rectangle((X(d)-.09,0),.18,zr(d)/1000,fc='#8b5a2b',ec='k',lw=.5))
ax.plot([X(-500),X(L+1500)],[0,0],'k',lw=1.5)
# partitions 2F
for d in (1000,4100,9000,10500):
    top=zr(d)/1000; ax.plot([X(d),X(d)],[Z2/1000,top],color='#555',lw=1.4 if d!=1000 else .8,ls='-' if d!=1000 else '--')
ax.plot([X(CL),X(CL)],[0,(Z2-600)/1000],color='#555',lw=1.2)
def lab(d,z,t,**k):
    k.setdefault('fontsize',11); ax.text(X(d),z/1000,t,ha='center',va='center',**k)
lab(500,5200,'吹抜'); lab(2550,4300,'ホール'); lab(6550,4300,'会議室'); lab(9750,4650,'ぐったり',fontsize=10); lab(11400,3700,'収納',fontsize=9,color='#666')
lab(1250,1300,'土間'); lab(7000,1300,'キッチン（1 階）')
# heights
for d in (4100,7200,9000,10500):
    z=zr(d); ax.annotate('',xy=(X(d)+.12,z/1000),xytext=(X(d)+.12,Z2/1000),arrowprops=dict(arrowstyle='<->',color='#1f5fa8',lw=1))
    ax.annotate('',xy=(X(d)-.12,(z-700)/1000),xytext=(X(d)-.12,Z2/1000),arrowprops=dict(arrowstyle='<->',color='#c0392b',lw=1))
    ax.text(X(d)+.2,(Z2+ (z-Z2)*.55)/1000,'%.2f'%((z-Z2)/1000),color='#1f5fa8',fontsize=10,ha='left')
    ax.text(X(d)-.2,(Z2+(z-700-Z2)*.45)/1000,'%.2f'%((z-700-Z2)/1000),color='#c0392b',fontsize=10,ha='right')
ax.text(X(L)-.3,8.6,'青＝梁と梁の間（屋根板の下まで）\n赤＝屋根梁（せい 700）の直下',fontsize=11,va='top')
ax.text(X(0)+.3,8.6,'本館側（東）',ha='right',fontsize=10); ax.text(X(L)+.3,0.3,'西の道路側',fontsize=10)
ax.text(X(6000),-0.6,'k=9 と 10 の間で切って北を見る。奥に見えているのが k=9 の屋根梁と 2 階の床梁（斜線）。単位 m',ha='center',fontsize=10)
ax.set_xlim(X(L+1600),X(-900)); ax.set_ylim(-1,9); ax.set_aspect('equal'); ax.axis('off')
plt.savefig('/home/claude/plans/rhino/west_case3_section.png',dpi=130,bbox_inches='tight')
