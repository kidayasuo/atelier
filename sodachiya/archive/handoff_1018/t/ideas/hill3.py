exec(open('/tmp/claude-0/t/ideas/hill.py').read().split("COL['roofW']")[0])
KH=9.0              # 丘（遊戯室）と台所棟の境
def lines(k):
    t=np.clip((k-1.6)/(KH-1.6),0,1)
    zr=400+4600*ss(np.clip((k-1.6)/(8.0-1.6),0,1))   # 尾根：北の先端 0.4m → 架構8で 5.0m
    zo=400+2200*t                     # 道路側の軒：0.4m → 2.6m
    zi=zr-150
    return zi,zr,zo
DRH=3000.0
def zprof(k,d,L):
    if k<=KH:
        zi,zr,zo=lines(k); dr=min(DRH,L*0.5)
        if d<=dr: return zi+(zr-zi)*d/max(dr,1)
        return zr+(zo-zr)*(d-dr)/max(L-dr,1)
    # 台所棟：西（道路側）は丘の頂のテラス 4.5m→軒 3.0m、東の 2 階（d 1.5–7.0）は 6.6m、東端の吹抜も 6.6m
    if d<=7000: return 6600.0
    return 5000.0+(3000.0-5000.0)*(d-7000)/max(L-7000,1)
def faces_hill():
    F=[]; nt=16
    for i in range(len(kk)-1):
        for j in range(nt):
            def P(ii,t):
                a,b,L=segs[kk[ii]]; p=a+(b-a)*t; return (p[0],p[1],zprof(kk[ii],t*L,L))
            typ='roofW' if kk[i]<KH else 'roofK'
            F.append(([P(i,j/nt),P(i+1,j/nt),P(i+1,(j+1)/nt),P(i,(j+1)/nt)],typ))
    # 台所棟の 2 階の西面（d=7.0）の段差の壁
    ks=[k for k in kk if k>=KH]
    for k0,k1 in zip(ks,ks[1:]):
        def Q(k,z):
            a,b,L=segs[k]; p=a+(b-a)*(7000/L); return (p[0],p[1],z)
        F.append(([Q(k0,5000),Q(k1,5000),Q(k1,6600),Q(k0,6600)],'wallK'))
    k0=ks[0]; a,b,L=segs[k0]
    for d0,d1 in ((0,7000),):
        p0=a+(b-a)*(d0/L); p1=a+(b-a)*(d1/L)
        F.append(([(p0[0],p0[1],zprof(k0-0.01,d0,L)),(p1[0],p1[1],zprof(k0-0.01,d1,L)),(p1[0],p1[1],6600),(p0[0],p0[1],6600)],'wallK'))
    cs=list(W.exterior.coords)
    for a,b in zip(cs,cs[1:]):
        F.append(([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zat2(b)),(a[0],a[1],zat2(a))],'wallW'))
    Fm,_,_=faces_for('A')
    F+=[f for f in Fm if f[1] not in ('roofW','wallW')]
    return F
COL['roofW']=np.array([0.55,0.68,0.45]); COL['roofK']=np.array([0.6,0.58,0.55]); COL['wallK']=np.array([0.88,0.84,0.78])
F=faces_hill()
Wc=np.array(W.centroid.coords[0]); Vw=np.array(V['W']); bis=unit(unit(np.array(V['N'])-Vw)+unit(np.array(V['SW'])-Vw))
fig=plt.figure(figsize=(18,15)); gs=fig.add_gridspec(3,3,height_ratios=[1,0.9,1.0])
render(fig.add_subplot(gs[0,0]),F,np.r_[Vw-bis*9000,1500],np.r_[np.array(segs[6.0][1]),1500],'交差点の歩道から（目の高さ 1.5m）',focal=0.62)
render(fig.add_subplot(gs[0,1]),F,np.r_[Vw-bis*30000+np.array([0,-12000]),26000],np.r_[Wc+np.array([3000,-2000]),2000],'北西の上空から',focal=1.5)
p9=np.array(segs[10.0][1]); o9=unit(p9-segs[10.0][0])
render(fig.add_subplot(gs[0,2]),F,np.r_[p9+o9*20000+np.array([0,-6000]),1500],np.r_[p9,2500],'西の道路から（台所棟の前）',focal=0.8)
ax=fig.add_subplot(gs[2,0])
kh=[k for k in kk if k<=KH]
sL=np.r_[0,np.cumsum(np.linalg.norm(np.diff(np.array([segs[k][1] for k in kk]),axis=0),axis=1))]/1000
zo=np.array([zprof(k,segs[k][2],segs[k][2]) for k in kk]); zr=np.array([lines(k)[1] if k<=KH else 6600 for k in kk])
ax.fill_between(sL,0,zo/1000,color='#dccdb0',label='道路側の外壁')
ax.plot(sL,zr/1000,color='#4f7a3a',lw=1.6,label='尾根（丘）／ 2階の屋根')
ax.axhline(4.0,color='#888',ls='--',lw=.7); ax.text(sL[-1],4.1,'本館の屋根 4.0m',ha='right',fontsize=7,color='#666')
ax.set_ylim(0,8); ax.set_xlabel('北の先端からの長さ（m）',fontsize=8); ax.set_ylabel('高さ m',fontsize=8); ax.legend(fontsize=7,loc='upper left'); ax.set_title('道路側の外壁と尾根の高さ',fontsize=10)
ax=fig.add_subplot(gs[1,:]); off=0
for k,lab_ in ((3,'架構3：低い巣'),(6,'架構6：遊戯室'),(10.5,'架構10.5：キッチン＋2階')):
    kq=min(kk,key=lambda x:abs(x-k)); a,b,L=segs[kq]
    d=np.linspace(0,L,120); z=np.array([zprof(kq,x,L) for x in d])
    X=off+(L-d)/1000
    sink=0.8 if kq<=KH else 0.0
    ax.fill_between(X,-sink,z/1000,color='#eef3e8',ec='#4f7a3a')
    if sink: ax.plot([X.min()+0.6,X.max()-0.6],[-sink,-sink],color='#4f7a3a',lw=.8)
    ax.add_patch(plt.Rectangle((off+L/1000+0.7,0),12.2,3.4,fc='#eee',ec='#999',lw=.5)); ax.plot([off+L/1000+0.7,off+L/1000+12.9],[4.0,3.0],color='#777',lw=1)
    ax.text(off+L/1000+6.8,1.6,'本館',fontsize=7,ha='center',color='#777')
    if kq>KH:
        ax.add_patch(plt.Rectangle((off+(L-7000)/1000,3.25),5.5,3.0,fc='#E8DDF3',ec='#7a5a9a',lw=.6)); ax.text(off+(L-4250)/1000,4.6,'休憩室',fontsize=7,ha='center')
        ax.text(off+(L-750)/1000,4.6,'吹抜\n換気',fontsize=6,ha='center'); ax.text(off+(L-8000)/1000,1.4,'キッチン',fontsize=7,ha='center')
        ax.text(off+(L-10500)/1000,4.9,'丘の頂の\nテラス',fontsize=6,ha='center',color='#4f7a3a')
    else:
        ax.text(off+L/2000,0.35 if k<4 else 1.4,'低い巣' if k<4 else '遊戯室',fontsize=7,ha='center')
    ax.text(off+L/2000,-1.6,lab_,fontsize=8,ha='center'); ax.text(off-0.3,-0.35,'道路',fontsize=6,ha='right')
    # 人（子ども 1.0m）on roof
    if k==6:
        dd=L*0.35; zz=zprof(kq,dd,L)/1000; ax.plot([off+(L-dd)/1000]*2,[zz,zz+1.0],color='#c0392b',lw=2); ax.text(off+(L-dd)/1000+0.3,zz+1.0,'屋根の上の子ども',fontsize=6,color='#c0392b')
    off+=L/1000+15
ax.set_aspect('equal'); ax.set_ylim(-1.9,8.0); ax.axhline(0,color='k',lw=.6); ax.axis('off'); ax.set_title('断面（左が道路、右が本館）',fontsize=10)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_hill_roof.png',dpi=65)
gr=np.gradient(zr[:len(kh)],sL[:len(kh)]*1000); print('ridge max slope deg %.1f'%np.degrees(np.arctan(gr.max())))
for k in (3,5,6,8):
    kq=min(kk,key=lambda x:abs(x-k)); a,b,L=segs[kq]; zi,zr_,zo_=lines(kq); dr=min(DRH,L*.5)
    print(k,'L',round(L),'ridge',round(zr_),'eave',round(zo_),'cross slope deg %.1f'%math.degrees(math.atan((zr_-zo_)/(L-dr))))
# 遊戯室の床面積と天井高の分布
