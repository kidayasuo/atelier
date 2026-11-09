exec(open('/tmp/claude-0/t/ideas/roof_geo.py').read())
Cc=np.array(G['CENTER']); dth=bm['thetas'][1]-bm['thetas'][0]; th0=bm['thetas'][0]; Re=bm['R']
def ku(p):
    v=np.array(p[:2])-Cc; th=math.atan2(v[1],v[0]); k=(((th-th0)+math.pi)%(2*math.pi)-math.pi)/dth; u=np.linalg.norm(v)-Re-12000; return k,u
kk=np.array(sorted(segs)); uin=np.array([np.linalg.norm(segs[k][0]-Cc)-Re-12000 for k in kk]); uout=np.array([np.linalg.norm(segs[k][1]-Cc)-Re-12000 for k in kk]); Larr=uout-uin
ZLOW=6300.0; N=10.0
Lk=12619.0   # キッチン側（架構 9）の長さ：2 階の天井高を確保するのに使う
H=ZLOW+Lk/N
def heights(opt):
    zi=np.zeros_like(Larr); zo=np.zeros_like(Larr)
    for i,L in enumerate(Larr):
        if opt=='A':   # 勾配一定・下端一定
            zo[i]=ZLOW; zi[i]=ZLOW+L/N
        elif opt=='B': # 勾配一定・棟（本館側）の高さを保つ。北の先端は外側が上がりすぎない範囲で
            zo[i]=min(H-L/N, ZLOW+600.0); zi[i]=zo[i]+L/N
            if zi[i]>H: zi[i]=H; zo[i]=H-L/N
        elif opt=='C': # 両端の高さ一定・勾配が変化（急すぎる北の先端は 1/4 まで）
            zo[i]=ZLOW; zi[i]=ZLOW+min(H-ZLOW, L/4.0)
        elif opt=='D': # 本館側の棟は一定、外側の軒が交差点（北の先端）に向かってなめらかに上がる
            t=np.clip((kk[i]-9.0)/(2.0-9.0),0,1); sm=t*t*(3-2*t)
            zo[i]=ZLOW+1500.0*sm; zi[i]=max(H,zo[i]+300.0)
    return zi,zo
def zat(p,zi,zo):
    k,u=ku(p); k=np.clip(k,kk[0],kk[-1])
    a=np.interp(k,kk,uin); b=np.interp(k,kk,uout); t=np.clip((u-a)/max(b-a,1),0,1)
    return np.interp(k,kk,zi)*(1-t)+np.interp(k,kk,zo)*t
def faces_for(opt):
    zi,zo=heights(opt); F=[]
    # west roof mesh
    for i in range(len(kk)-1):
        for j in range(6):
            t0,t1=j/6,(j+1)/6
            def P(ii,t):
                a,b,_=segs[kk[ii]]; p=a+(b-a)*t; z=zi[ii]*(1-t)+zo[ii]*t; return (p[0],p[1],z)
            F.append(([P(i,t0),P(i+1,t0),P(i+1,t1),P(i,t1)],'roofW'))
    # west walls
    cs=list(W.exterior.coords)
    for a,b in zip(cs,cs[1:]):
        za,zb=zat(a,zi,zo),zat(b,zi,zo)
        F.append(([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zb),(a[0],a[1],za)],'wallW'))
    # main roof & walls
    zm=lambda u: 3000+u/12000*1000
    for k in range(19):
        for u0,u1 in ((-3000,0),(0,6000),(6000,12200)):
            q=[world(bm,thf(k),u0,0),world(bm,thf(k+1),u0,0),world(bm,thf(k+1),u1,0),world(bm,thf(k),u1,0)]
            F.append(([(q[0][0],q[0][1],zm(u0)),(q[1][0],q[1][1],zm(u0)),(q[2][0],q[2][1],zm(u1)),(q[3][0],q[3][1],zm(u1))],'roofM'))
        for u,typ in ((12200,'wallM'),(0,'glassM')):
            a=world(bm,thf(k),u,0); b=world(bm,thf(k+1),u,0)
            F.append(([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zm(u)),(a[0],a[1],zm(u))],typ))
    for k in (0,19):
        a=world(bm,thf(k),0,0); b=world(bm,thf(k),12200,0)
        F.append(([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zm(12200)),(a[0],a[1],zm(0))],'wallM'))
    return F,zi,zo
COL={'roofW':np.array([0.62,0.55,0.48]),'wallW':np.array([0.86,0.80,0.70]),'roofM':np.array([0.55,0.55,0.55]),'wallM':np.array([0.85,0.82,0.76]),'glassM':np.array([0.65,0.75,0.82])}
LIGHT=unit(np.array([-0.4,-0.6,0.7])) if False else None
def render(ax,F,eye,target,title,focal=1.2):
    E=np.array(eye,float); T=np.array(target,float); f=(T-E)/np.linalg.norm(T-E); r=np.cross(f,[0,0,1]); r/=np.linalg.norm(r); up=np.cross(r,f)
    L=np.array([-0.5,-0.4,0.75]); L/=np.linalg.norm(L)
    items=[]
    for poly,typ in F:
        P=np.array(poly,float); V=P-E; d=V@f
        if (d<500).any(): continue
        x=(V@r)/d*focal; y=(V@up)/d*focal
        n=np.cross(P[1]-P[0],P[2]-P[0]); nn=np.linalg.norm(n)
        if nn<1e-9: continue
        n/=nn
        if n@(E-P.mean(0))<0: n=-n
        sh=0.55+0.45*max(0,n@L)
        items.append((d.mean(),np.c_[x,y],np.clip(COL[typ]*sh,0,1)))
    items.sort(key=lambda t:-t[0])
    from matplotlib.patches import Polygon as MPo
    for _,xy,c in items: ax.add_patch(MPo(xy,closed=True,fc=c,ec=(0.3,0.3,0.3),lw=0.15))
    hy=(np.array([0,0,0])@up)  # 地平線：視線方向の無限遠
    fh=f.copy(); fh[2]=0; fh/=np.linalg.norm(fh); hy=(fh@up)/(fh@f)*focal
    ax.add_patch(plt.Rectangle((-3,-3),6,3+hy,fc='#e9e6df',zorder=-5)); ax.add_patch(plt.Rectangle((-3,hy),6,3,fc='#eef3f7',zorder=-6))
    ax.set_xlim(-0.95,0.95); ax.set_ylim(-0.45,0.65); ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title,fontsize=9)
