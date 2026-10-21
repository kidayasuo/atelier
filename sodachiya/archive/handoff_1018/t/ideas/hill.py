exec(open('/tmp/claude-0/t/ideas/roof_render.py').read())
V=dict(N=(0,0),E=(34860,-43830),S=(-14440,-83040),SW=(-21910,-73650),W=(-25830,-20540))
DR=7000.0     # 本館側の縁から棟まで（換気の吹抜け 1.5m＋2階の部屋 5.5m）
def ss(x): x=np.clip(x,0,1); return x*x*(3-2*x)
def lines(k):
    zo=400+2600*np.clip((k-1.6)/(12-1.6),0,1)                 # 道路側の軒：北 0.4m → 南 3.0m
    zr=400+6100*ss((k-1.6)/(7.5-1.6))                          # 棟：北 0.4m → 7.5 で 6.5m、以南は一定
    zi=zr-400                                                  # 本館側の縁（棟から東へゆるく下がる）
    return zi,zr,zo
def zprof(k,d,L):
    zi,zr,zo=lines(k); dr=min(DR,L*0.6)
    if d<=dr: return zi+(zr-zi)*d/max(dr,1)
    return zr+(zo-zr)*(d-dr)/max(L-dr,1)
def zat2(p):
    k,u=ku(p); k=np.clip(k,kk[0],kk[-1])
    a=np.interp(k,kk,uin); b=np.interp(k,kk,uout); L=b-a
    return zprof(k,np.clip(u-a,0,L),L)
def faces_hill():
    F=[]
    nt=12
    for i in range(len(kk)-1):
        for j in range(nt):
            def P(ii,t):
                a,b,L=segs[kk[ii]]; p=a+(b-a)*t; return (p[0],p[1],zprof(kk[ii],t*L,L))
            F.append(([P(i,j/nt),P(i+1,j/nt),P(i+1,(j+1)/nt),P(i,(j+1)/nt)],'roofW'))
    cs=list(W.exterior.coords)
    for a,b in zip(cs,cs[1:]):
        F.append(([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zat2(b)),(a[0],a[1],zat2(a))],'wallW'))
    Fm,_,_=faces_for('A')
    F+=[f for f in Fm if f[1]!='roofW' and f[1]!='wallW']
    return F
COL['roofW']=np.array([0.55,0.68,0.45])   # 草の屋根
F=faces_hill()
Wc=np.array(W.centroid.coords[0]); Vw=np.array(V['W']); bis=unit(unit(np.array(V['N'])-Vw)+unit(np.array(V['SW'])-Vw))
fig=plt.figure(figsize=(18,13))
ax1=fig.add_subplot(2,3,1); render(ax1,F,np.r_[Vw-bis*9000,1500],np.r_[np.array(segs[5.0][1]),1500],'交差点の歩道から（目の高さ 1.5m）',focal=0.62)
ax2=fig.add_subplot(2,3,2); render(ax2,F,np.r_[Vw-bis*30000+np.array([0,-12000]),26000],np.r_[Wc+np.array([3000,-2000]),2000],'北西の上空から',focal=1.5)
ge=np.array(world(bm,thf(4.0),-25000,0)[:2]); render(ax3:=fig.add_subplot(2,3,3),F,np.r_[ge,1500],np.r_[Wc,3500],'園庭から（本館越しに）',focal=0.8)
# 展開立面（道路側の軒と棟）
ax=fig.add_subplot(2,3,4)
sL=np.r_[0,np.cumsum(np.linalg.norm(np.diff(np.array([segs[k][1] for k in kk]),axis=0),axis=1))]/1000
zo=np.array([lines(k)[2] for k in kk]); zr=np.array([lines(k)[1] for k in kk])
ax.fill_between(sL,0,zo/1000,color='#dccdb0',label='道路側の外壁')
ax.plot(sL,zr/1000,color='#4f7a3a',lw=1.6,label='棟（山の尾根）')
ax.axhline(4.0,color='#888',ls='--',lw=.7); ax.text(sL[-1],4.1,'本館の屋根 4.0m',ha='right',fontsize=7,color='#666')
ax.axhline(1.1,color='#c0392b',ls=':',lw=.7); ax.text(0.5,1.2,'手すり・柵の高さの目安 1.1m',fontsize=7,color='#c0392b')
ax.set_ylim(0,8); ax.set_xlabel('北の先端からの長さ（m）',fontsize=8); ax.set_ylabel('高さ m',fontsize=8); ax.legend(fontsize=7,loc='upper left'); ax.set_title('道路側の外壁と尾根の高さ',fontsize=10)
# 尾根の勾配
gr=np.gradient(zr,sL*1000)
ax.twinx().plot(sL,np.degrees(np.arctan(gr)),color='#3c78b4',lw=.8,ls=':')
# 断面（放射方向）
ax=fig.add_subplot(2,3,(5,6))
off=0
for k,lab_ in ((3,'架構3（北：低い巣）'),(6,'架構6（遊戯室）'),(10.5,'架構10.5（キッチン＋2階）')):
    a,b,L=segs[min(kk,key=lambda x:abs(x-k))]
    d=np.linspace(0,L,60); z=[zprof(k,x,L) for x in d]
    X=off+ (L-d)/1000          # 道路側を左に
    ax.fill_between(X,0,np.array(z)/1000,color='#eef3e8',ec='#4f7a3a')
    # 本館（右側）
    ax.add_patch(plt.Rectangle((off+L/1000+0.7,0),12.2,3.4,fc='#eee',ec='#999',lw=.5))
    ax.plot([off+L/1000+0.7,off+L/1000+12.9],[4.0,3.0],color='#777',lw=1)
    if k>9:
        ax.add_patch(plt.Rectangle((off+(L-7000)/1000,3.25),5.5,2.5,fc='#E8DDF3',ec='#7a5a9a',lw=.6)); ax.text(off+(L-4250)/1000,4.4,'2階の部屋',fontsize=7,ha='center')
        ax.text(off+(L-750)/1000,4.4,'吹抜\n(換気)',fontsize=6,ha='center')
        ax.text(off+(L-9500)/1000,1.2,'キッチン',fontsize=7,ha='center')
    elif k<4:
        ax.text(off+L/2000,0.3,'低い巣',fontsize=7,ha='center')
    else:
        ax.text(off+L/2000,1.5,'遊戯室',fontsize=7,ha='center')
    ax.plot([off+0.0,off+0.0],[0,1.1],color='#c0392b',lw=1)
    ax.text(off+L/2000,-0.8,lab_,fontsize=8,ha='center')
    ax.text(off-0.3,-0.4,'道路側',fontsize=6,ha='right')
    off+=L/1000+16
ax.set_aspect('equal'); ax.set_ylim(-1.3,8.5); ax.axhline(0,color='k',lw=.6); ax.axis('off'); ax.set_title('断面（左が道路、右が本館）',fontsize=10)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_hill_roof.png',dpi=65)
print('ridge slope max deg', np.degrees(np.arctan(gr.max())))
for k in (3,6,10.5):
    a,b,L=segs[min(kk,key=lambda x:abs(x-k))]; zi,zr,zo=lines(k); print(k,'L',round(L),'zi zr zo',round(zi),round(zr),round(zo),'west slope deg',round(math.degrees(math.atan((zr-zo)/max(L-min(DR,L*.6),1))),1))
