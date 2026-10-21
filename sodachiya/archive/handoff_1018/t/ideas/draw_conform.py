import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams["font.family"]="IPAGothic"
exec(open('/tmp/claude-0/t/ideas/conform.py').read().split("if __name__")[0])
exec(open('/tmp/claude-0/t/ideas/common.py').read()[open('/tmp/claude-0/t/ideas/common.py').read().index('def frame'):])
from shapely.ops import split
import json
C=json.load(open('conform.json'))
mrooms=[(1,3,'0・1歳','#F4D9C6'),(4,5,'2歳','#F4D9C6'),(6,7,'事務','#E3E3E3'),(8,10,'ホール','#F6D27A'),(11,11,'','#E3E3E3'),(12,13,'3歳','#F9E7C9'),(14,14,'','#E3E3E3'),(15,16,'4歳','#F9E7C9'),(17,17,'','#E3E3E3'),(18,19,'5歳','#F9E7C9')]
fig,axs=plt.subplots(1,2,figsize=(14,9.5))
titles={'tri':'案D：残りの敷地にすなおな、角の丸い三角形','maga':'案E：角に向かって曲がる帯、中は詰まっている（勾玉）'}
for ax,(mode,Rs,v) in zip(axs,[c for c in C if c[1]==205000]):
    pen,ga,wa,d=evalc(Rs,*v,mode,detail=True)
    f=frame(ax,titles[mode]); bm,thf,at=d['bm'],d['thf'],d['at']
    def mp(k0,k1,u0,u1,n=20):
        a=[world(bm,thf(k0+(k1-k0)*i/n),u0,0)[:2] for i in range(n+1)]; b=[world(bm,thf(k1-(k1-k0)*i/n),u1,0)[:2] for i in range(n+1)]; return SP(a+b)
    f(mp(0,19,-3000,0),'#f3efe2',ec='#bbb',lw=.3)
    for s0,s1,t,c in mrooms:
        p=mp(19-s1,20-s0,0,12000); f(p,c); lab(ax,p,t,fs=6)
    W=d['west']
    cut=SL([tuple(at(9.0,-5000)),tuple(at(9.0,60000))])
    pcs=sorted(split(W,cut).geoms,key=lambda q:-q.area)
    play,kit=pcs[0],pcs[1]
    f(play,'#CFE0F2'); lab(ax,play,'遊戯室\n%.0f㎡'%(play.area/1e6),fs=9)
    doma=kit.intersection(mp(8.9,12.1,12700,15700)); kit2=kit.difference(doma)
    f(kit2,'#BFD7EE'); lab(ax,kit2,'キッチン\n%.0f㎡'%(kit2.area/1e6),fs=7)
    f(doma,'#FBE9B8'); lab(ax,doma,'土間',fs=6)
    st=mp(7.9,8.95,13500,15000); f(st,'#fff'); lab(ax,st,'階段',fs=5)
    # radial frame lines through west building (shared radial lines)
    for k in np.arange(0,13,1):
        L=SL([tuple(at(k,700)),tuple(at(k,60000))]).intersection(W)
        for seg in getattr(L,'geoms',[L]):
            if not seg.is_empty:
                x,y=seg.xy; ax.plot(x,y,color='#7a9cc0',lw=.35)
    f(d['pk'],'#d0d0d0',lw=.5); lab(ax,d['pk'],'P',fs=7)
    ax.text(0,-84500,'園庭（ひと続き）約 %.0f㎡　本館は今の形（背骨の半径 205 m）'%ga,ha='center',fontsize=9)
    print(mode,pen,ga,wa,play.area/1e6,kit2.area/1e6,doma.area/1e6)
    # max radial depth of west
    dep=max(SL([tuple(at(k,700)),tuple(at(k,60000))]).intersection(W).length for k in np.arange(0,12.01,0.5))
    print('max frame length in west', dep)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/ideas_west_conform.png',dpi=72)
