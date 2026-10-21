exec(open('/tmp/claude-0/t/ideas/dots_opt3.py').read().split("import itertools")[0])
exec(open('/tmp/claude-0/t/ideas/common.py').read().split("def unit")[0])
exec("def unit(v):\n    v=np.array(v,float); return v/np.linalg.norm(v)")
exec(open('/tmp/claude-0/t/ideas/common.py').read().split("def frame")[1].join(["def frame",""]) if False else "")
import json
C=json.load(open('dots_opt2.json'))+json.load(open('dots_opt3.json'))
pick={(n,R):v for n,R,v,pen,ga in C}
mrooms=[(1,3,'0・1歳','#F4D9C6'),(4,5,'2歳','#F4D9C6'),(6,7,'事務','#E3E3E3'),(8,10,'ホール','#F6D27A'),(11,11,'','#E3E3E3'),(12,13,'3歳','#F9E7C9'),(14,14,'','#E3E3E3'),(15,16,'4歳','#F9E7C9'),(17,17,'','#E3E3E3'),(18,19,'5歳','#F9E7C9')]
exec(open('/tmp/claude-0/t/ideas/common.py').read()[open('/tmp/claude-0/t/ideas/common.py').read().index('def frame'):])
fig,axs=plt.subplots(1,3,figsize=(19,9.5))
titles={'dots':'案A：珠つなぎ（丸いドットが本館に寄りそう）','pill':'案B：ピル（角の丸いカプセル一つ）','bardot':'案C：遊戯室の帯＋キッチンのドット'}
for ax,name in zip(axs,('dots','pill','bardot')):
    v=pick[(name,120000)]
    pen,ga,d=evalp(120000,*v,name,detail=True)
    f=frame(ax,titles[name])
    bm,thf=d['bm'],d['thf']
    def mp(k0,k1,u0,u1,n=20):
        a=[world(bm,thf(k0+(k1-k0)*i/n),u0,0)[:2] for i in range(n+1)]; b=[world(bm,thf(k1-(k1-k0)*i/n),u1,0)[:2] for i in range(n+1)]; return SP(a+b)
    f(mp(0,19,-3000,0),'#f3efe2',ec='#bbb',lw=.3)
    for s0,s1,t,c in mrooms:
        p=mp(19-s1,20-s0,0,12000); f(p,c); lab(ax,p,t,fs=6)
    at=d['at']
    if name=='pill':
        P=d['sh']['_all']
        cut=SL([tuple(at(8.6,-5000)),tuple(at(8.6,30000))])
        from shapely.ops import split
        parts=sorted(split(P,cut).geoms,key=lambda q:-q.area)
        f(parts[0],'#CFE0F2'); lab(ax,parts[0],'遊戯室\n%.0f㎡'%(parts[0].area/1e6),fs=8)
        f(parts[1],'#BFD7EE'); lab(ax,parts[1],'キッチン\n%.0f㎡'%(parts[1].area/1e6),fs=7)
    else:
        cols={'遊戯室':'#CFE0F2','キッチン':'#BFD7EE','階段':'#ffffff'}
        for k,q in d['sh'].items():
            f(q,cols.get(k,'#ddd')); lab(ax,q,(k+'\n%.0f㎡'%(q.area/1e6)) if k!='階段' else k,fs=7 if k!='階段' else 6)
    f(d['pk'],'#d0d0d0',lw=.5); lab(ax,d['pk'],'P',fs=7)
    ax.text(0,-84500,'園庭（ひと続き）約 %.0f㎡　背骨の半径 120 m'%ga,ha='center',fontsize=9)
    print(name,pen,ga)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/ideas_west_dots.png',dpi=72)
