# 架構の正確なモデル（GH スクリプトの 2D 断面 → rhino3dm の押し出し・回転面）
import math, numpy as np, rhino3dm as r3
from scipy.interpolate import make_interp_spline
def _dedup(pts,eps=1e-6):
    out=[pts[0]]
    for p in pts[1:]:
        if math.hypot(p[0]-out[-1][0],p[1]-out[-1][1])>eps: out.append(p)
    return out
def nurbs_interp(pts):
    pts=_dedup([tuple(p) for p in pts])
    if len(pts)<4:
        return r3.PolylineCurve([r3.Point3d(p[0],p[1],0) for p in pts])
    P=np.array(pts); s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(P,axis=0),axis=1))]
    sp=make_interp_spline(s,P,k=3)
    t=sp.t; c=sp.c; n=len(c)
    crv=r3.NurbsCurve(3,False,4,n)
    for i in range(n): crv.Points[i]=r3.Point4d(c[i][0],c[i][1],0,1)
    kn=t[1:-1]
    for i in range(len(kn)): crv.Knots[i]=float(kn[i])
    return crv
def nurbs_bezier(ctrl):
    n=len(ctrl); crv=r3.NurbsCurve(3,False,n,n)
    for i,p in enumerate(ctrl): crv.Points[i]=r3.Point4d(p[0],p[1],0,1)
    kn=[0.0]*(n-1)+[1.0]*(n-1)
    for i,v in enumerate(kn): crv.Knots[i]=v
    return crv
def seg_curve(segs):
    pc=r3.PolyCurve()
    for kind,pts in segs:
        if kind=='L':
            if math.hypot(pts[1][0]-pts[0][0],pts[1][1]-pts[0][1])<1e-6: continue
            c=r3.LineCurve(r3.Point3d(pts[0][0],pts[0][1],0),r3.Point3d(pts[1][0],pts[1][1],0))
        elif kind=='P': c=nurbs_interp(pts)
        else: c=nurbs_bezier(pts)
        pc.Append(c)
    return pc
def seg_poly(segs,n=16):
    """プレビュー用の折れ線"""
    from_=[]
    for kind,pts in segs:
        if kind=='L': q=list(pts)
        elif kind=='P': q=list(pts)
        else:
            m=len(pts)-1
            q=[]
            for i in range(n+1):
                t=i/n; x=y=0
                for j,p in enumerate(pts):
                    cf=math.comb(m,j)*(1-t)**(m-j)*t**j; x+=cf*p[0]; y+=cf*p[1]
                q.append((x,y))
        from_+= q if not from_ else q[1:]
    return from_
def ellipse_nurbs(o,ex,ey,a,b):
    """有理 2 次の楕円（9 点）。o 中心、ex/ey 軸方向（単位）、a/b 半径"""
    w=math.sqrt(0.5); cs=[(1,0),(1,1),(0,1),(-1,1),(-1,0),(-1,-1),(0,-1),(1,-1),(1,0)]
    crv=r3.NurbsCurve(3,True,3,9)
    for i,(x,y) in enumerate(cs):
        wt=1.0 if i%2==0 else w
        p=[o[j]+ex[j]*a*x+ey[j]*b*y for j in range(3)]
        crv.Points[i]=r3.Point4d(p[0]*wt,p[1]*wt,p[2]*wt,wt)
    for i,v in enumerate([0,0,1,1,2,2,3,3,4,4]): crv.Knots[i]=float(v)
    return crv
def ellipse_curve(u,z,w,h):
    return ellipse_nurbs((u,z,0),(1,0,0),(0,1,0),w/2.0,h/2.0)
def frame_plane(world,Bd,th):
    o=world(Bd,th,0,0,0); x=world(Bd,th,1000,0,0)
    ux=r3.Vector3d((x[0]-o[0])/1000,(x[1]-o[1])/1000,0)
    return r3.Plane(r3.Point3d(*o),ux,r3.Vector3d(0,0,1))   # 法線 = ux × Z = −（弧の方向）
def plate(world,Bd,th,segs,holes,t0,thick,hw,hh):
    ext=r3.Extrusion()
    ext.SetPathAndUp(r3.Point3d(0,0,-t0-thick),r3.Point3d(0,0,-t0),r3.Vector3d(0,1,0))
    ok=ext.SetOuterProfile(seg_curve(segs),True)
    for (hu,hz) in holes: ext.AddInnerProfile(ellipse_curve(hu,hz,hw,hh))
    ext.Transform(r3.Transform.PlaneToPlane(r3.Plane.WorldXY(),frame_plane(world,Bd,th)))
    return ext,ok
def girder_arc(center,r,z,th_a,th_b,w,h):
    """弧に沿う楕円断面の桁：楕円を中心の鉛直軸まわりに回転"""
    cx,cy=center
    o=r3.Point3d(cx+r*math.cos(th_a),cy+r*math.sin(th_a),z)
    ux=r3.Vector3d(math.cos(th_a),math.sin(th_a),0)
    prof=ellipse_nurbs((o.X,o.Y,o.Z),(ux.X,ux.Y,0),(0,0,1),w/2.0,h/2.0)
    axis=r3.Line(r3.Point3d(cx,cy,0),r3.Point3d(cx,cy,1000))
    lo,hi=(th_a,th_b) if th_b>th_a else (th_b,th_a)
    rev=r3.RevSurface.Create(prof,axis,0.0,hi-lo)
    if th_b<th_a: rev=r3.RevSurface.Create(prof,axis,-(th_a-th_b),0.0)
    return r3.Brep.CreateFromRevSurface(rev,True,True)
def girder_line(p0,p1,w,h):
    """2 点の間をまっすぐ通る楕円断面の桁（押し出し）"""
    p0=np.array(p0,float); p1=np.array(p1,float); d=p1-p0; L=np.linalg.norm(d)
    ext=r3.Extrusion()
    ext.SetPathAndUp(r3.Point3d(0,0,0),r3.Point3d(0,0,L),r3.Vector3d(0,1,0))
    ext.SetOuterProfile(ellipse_nurbs((0,0,0),(1,0,0),(0,1,0),w/2.0,h/2.0),True)
    zax=d/L; up=np.array([0,0,1.0]); xax=np.cross(up,zax); xax/=np.linalg.norm(xax); yax=np.cross(zax,xax)
    tgt=r3.Plane(r3.Point3d(*p0),r3.Vector3d(*xax),r3.Vector3d(*yax))
    ext.Transform(r3.Transform.PlaneToPlane(r3.Plane.WorldXY(),tgt))
    return ext
def floor2_big(G,Bk,zsplit,margin=280.0):
    """2 階床梁（せい 800）でも楕円（肉球）が下に出るよう、床の桁を包む木を厚くする。
    屋根の頭は今までどおり（JOINT_MARGIN）"""
    old_jh=G['joint_heads']; old_g2=G['GIRDER_FROM_TOP2']
    gw,gh,jm=G['GIRDER_W'],G['GIRDER_H'],G['JOINT_MARGIN']
    def jh(heads):
        return [(u,z,gw/2.0+(margin if z<zsplit else jm),gh/2.0+(margin if z<zsplit else jm)) for u,z in heads]
    G['joint_heads']=jh; G['GIRDER_FROM_TOP2']=gh/2.0+margin
    try:
        F=G['floor2_profile_tamedia'](Bk)
    finally:
        G['joint_heads']=old_jh; G['GIRDER_FROM_TOP2']=old_g2
    return F
