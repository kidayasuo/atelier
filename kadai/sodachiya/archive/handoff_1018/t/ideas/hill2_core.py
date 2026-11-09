exec(open('/tmp/claude-0/t/ideas/hill.py').read().split("COL['roofW']")[0])
KH=9.0              # 丘（遊戯室）と台所棟の境
def lines(k):
    t=np.clip((k-1.6)/(KH-1.6),0,1)
    zr=400+4100*ss(t)                 # 尾根：北の先端 0.4m → 4.5m
    zo=400+2000*t                     # 道路側の軒：0.4m → 2.4m
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
    return 4500.0+(3000.0-4500.0)*(d-7000)/max(L-7000,1)
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
        F.append(([Q(k0,4500-0),Q(k1,4500),Q(k1,6600),Q(k0,6600)],'wallK'))
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
