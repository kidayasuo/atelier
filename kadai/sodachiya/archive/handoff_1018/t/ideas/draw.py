exec(open('/tmp/claude-0/t/ideas/idea1.py').read().split("for variant in")[0])
import sys
sys.path.insert(0,'/tmp/claude-0/mock2')
def east_garden(bl, extra_block=[]):
    g=site.difference(unary_union([bl,park]+extra_block))
    gs=[q for q in getattr(g,'geoms',[g]) if q.distance(SL([V['E'],V['S']]))<3000 or q.distance(SL([V['N'],V['E']]))<3000]
    return max(q.area for q in gs)/1e6
fig,axs=plt.subplots(1,3,figsize=(19,9.5))
# --- reference R85 (current) ---
exec(open('/tmp/claude-0/t/site.py').read())
g0=run(); bm,bw=g0['buildings'](); world=g0['world']
th=lambda B,k: B['thetas'][0]+(B['thetas'][1]-B['thetas'][0])*k
def poly(B,k0,k1,u0,u1,n=24):
    a=[world(B,th(B,k0+(k1-k0)*i/n),u0,0)[:2] for i in range(n+1)]
    b=[world(B,th(B,k1-(k1-k0)*i/n),u1,0)[:2] for i in range(n+1)]
    return SP(a+b)
ax=axs[0]; f=frame(ax,'いまの案（二重の弧、背骨の半径 85 m）')
refrooms=[(1,3,'0・1歳','#F4D9C6'),(4,5,'2歳','#F4D9C6'),(6,7,'事務','#E3E3E3'),(8,10,'ホール','#F6D27A'),(11,11,'','#E3E3E3'),(12,13,'3歳','#F9E7C9'),(14,14,'','#E3E3E3'),(15,16,'4歳','#F9E7C9'),(17,17,'','#E3E3E3'),(18,19,'5歳','#F9E7C9')]
blist=[]
for s0,s1,t,c in refrooms:
    p=poly(bm,19-s1,20-s0,0,12000); f(p,c); lab(ax,p,t,fs=6); blist.append(p)
e=poly(bm,0,19,-3000,0); f(e,'#f3efe2',ec='#bbb',lw=.3); blist.append(e)
pl=poly(bw,0,7,0,12000); f(pl,'#CFE0F2'); lab(ax,pl,'遊戯室',fs=7); blist.append(pl)
k=poly(bw,7,10,0,12000); f(k,'#BFD7EE'); lab(ax,k,'キッチン',fs=6); blist.append(k)
bl0=unary_union(blist)
ax.text(0,-84500,'園庭（ひと続きの部分）約 %.0f㎡'%east_garden(bl0),ha='center',fontsize=9)
# --- idea 1 drum & 2 Y ---
for ax,variant,title,rf,Lw in ((axs[1],'drum','案1：くの字＋円い遊戯室',16000,25000),(axs[2],'Y','案2：Y字（遊戯室が園庭へ伸びる腕）',16000,19000)):
    S,parts,eave,extra,bad,Lw,Ln=build(rf,Lw,variant)
    f=frame(ax,title)
    f(eave,'#f3efe2',ec='#bbb',lw=.3)
    for q,t,c in parts: f(q,c); lab(ax,q,t,fs=6)
    for q,t,c in extra:
        f(q,c); lab(ax,q,(t%(q.area/1e6)) if '%' in t else t,fs=7)
    bl=unary_union([q for q,_,_ in parts]+[eave]+[q for q,_,_ in extra])
    ax.text(0,-84500,'園庭（ひと続きの部分）約 %.0f㎡'%east_garden(bl),ha='center',fontsize=9)
    print(variant,'bad',bad,'garden',east_garden(bl),'Lw',Lw,'Ln',Ln)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/ideas_hinge.png',dpi=70)
print('ref garden',east_garden(bl0))
