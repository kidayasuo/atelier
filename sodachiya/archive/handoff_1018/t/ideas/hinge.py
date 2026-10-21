exec(open('/tmp/claude-0/t/ideas/common.py').read())
def inset_line(a,b,d):
    a=np.array(a,float); b=np.array(b,float); t=unit(b-a); n=np.array([-t[1],t[0]])
    m=(a+b)/2
    if not site.contains(SPt(*(m+n*1000))): n=-n
    return a+n*d, b+n*d, t, n
def intersect(p1,d1,p2,d2):
    A=np.array([d1,-d2]).T; s=np.linalg.solve(A,p2-p1); return p1+d1*s[0]
def make_spine(rf, inset=1500, n=400):
    nA,nB,tN,nN=inset_line(V['W'],V['N'],inset)      # 北の道路（W→N）
    wA,wB,tW,nW=inset_line(V['W'],V['SW'],inset)     # 西の道路（W→SW）
    Wi=intersect(nA,tN,wA,tW)
    phi=math.pi-math.acos(np.dot(tN,tW))              # 振れ角
    tl=rf*math.tan(phi/2)
    T1=Wi+tN*tl; T2=Wi+tW*tl
    bis=unit(tN+tW); C=Wi+bis*(rf/math.cos(phi/2))
    return dict(Wi=Wi,tN=tN,tW=tW,T1=T1,T2=T2,C=C,rf=rf,phi=phi)
def spine_pts(S, Lw, Ln, ds=250):
    """南端（西の翼）→ 角の円弧 → 北の翼。返り値: [(p, normal_to_garden)]"""
    pts=[]
    # west wing: from T2 + tW*Lw back to T2
    for s in np.arange(0,Lw,ds):
        p=S['T2']+S['tW']*(Lw-s); n=unit(S['C']-S['T2'])
        pts.append((p,n))
    a2=math.atan2(*(S['T2']-S['C'])[::-1]); a1=math.atan2(*(S['T1']-S['C'])[::-1])
    da=(a1-a2+math.pi)%(2*math.pi)-math.pi
    L_arc=abs(da)*S['rf']
    for s in np.arange(0,L_arc,ds):
        a=a2+da*s/L_arc; p=S['C']+S['rf']*np.array([math.cos(a),math.sin(a)]); pts.append((p,unit(S['C']-p)))
    for s in np.arange(0,Ln+1e-6,ds):
        p=S['T1']+S['tN']*s; pts.append((p,unit(S['C']-S['T1'])))
    return pts, L_arc
def band_from(pts,s0,s1,u0,u1,ds=250):
    i0,i1=int(round(s0/ds)),int(round(s1/ds))
    seg=pts[i0:i1+1]
    a=[tuple(p+n*u0) for p,n in seg]; b=[tuple(p+n*u1) for p,n in seg[::-1]]
    return SP(a+b).buffer(0)
