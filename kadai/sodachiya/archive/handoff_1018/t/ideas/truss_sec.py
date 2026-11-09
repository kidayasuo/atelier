exec(open('/tmp/claude-0/t/ideas/build_truss.py').read().split("# --- areas")[0])
fig,axs=plt.subplots(1,3,figsize=(18,4.8))
for ax,k in zip(axs,(4,6,8)):
    kq=min(kk,key=lambda x:abs(x-k)); L=segs[kq][2]
    X=lambda d: (L-d)/1000      # 道路側を左
    # 本館
    ax.add_patch(plt.Rectangle((L/1000+0.7,0),12.2,3.4,fc='#f0f0f0',ec='#aaa',lw=.6)); ax.plot([L/1000+0.7,L/1000+12.9],[4.0,3.0],color='#888')
    ax.text(L/1000+6.8,1.5,'本館',ha='center',fontsize=8,color='#888')
    # 門型
    for d in (0,L): ax.plot([X(d)]*2,[0,ZB/1000],color='#7a5a3a',lw=3)
    ax.plot([X(0),X(L)],[ZB/1000]*2,color='#7a5a3a',lw=4)
    # トラス
    zr=zprof(kq,0,L)/1000
    ax.plot([X(0),X(0)],[ZB/1000,zr],color='#b08050',lw=1.5); ax.plot([X(0),X(L)],[zr,ZB/1000],color='#b08050',lw=2)
    n=6
    for i in range(1,n):
        d=L*i/n; ax.plot([X(d)]*2,[ZB/1000,zprof(kq,d,L)/1000],color='#b08050',lw=1)
        d0=L*(i-1)/n if i%2==1 else L*(i+1)/n
        ax.plot([X(d0),X(d)],[ZB/1000,zprof(kq,d,L)/1000],color='#b08050',lw=1)
    # 屋根裏の床（キャットウォーク）
    ax.plot([X(0),X(2400)],[ZB/1000+0.05]*2,color='#c0392b',lw=3); ax.text(X(1200),ZB/1000+0.25,'屋根裏の床',fontsize=7,ha='center',color='#c0392b')
    ax.plot([X(L)-0.2,X(L)+0.2],[0,0],color='k')
    ax.text(X(L/2),1.2,'遊戯室（天井 3.0m まで）',ha='center',fontsize=8)
    ax.text(X(L)-0.2,-0.5,'道路側',fontsize=7,ha='right')
    ax.axhline(0,color='k',lw=.6); ax.set_aspect('equal'); ax.set_xlim(-1.5,L/1000+14); ax.set_ylim(-0.8,6.2)
    ax.set_title('架構 %d：尾根 %.1fm・梁 %.1fm・道路側 %.1fm（勾配 1/%.0f）'%(k,zr,ZB/1000,ZB/1000,L/((zr*1000-ZB) or 1)),fontsize=9)
    ax.set_yticks(range(0,7)); ax.grid(alpha=.2)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_truss_sections.png',dpi=70)
