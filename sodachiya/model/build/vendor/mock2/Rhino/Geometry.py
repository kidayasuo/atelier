import math
from shapely.geometry import Polygon, Point
CNT={}
def c(k): CNT[k]=CNT.get(k,0)+1
class Point3d:
    def __init__(s,x,y,z): s.X,s.Y,s.Z=x,y,z
class Vector3d(Point3d): pass
class Plane:
    def __init__(s,o,x,y): pass
Plane.WorldXY=Plane(None,None,None)
class _Crv:
    def __init__(s,a=None,b=None,closed=False): s.a,s.b,s.closed=a,b,closed
    @property
    def IsClosed(s): return s.closed
class LineCurve(_Crv):
    def __init__(s,a,b): c('line'); _Crv.__init__(s,a,b)
class NurbsCurve(_Crv):
    @staticmethod
    def Create(per,deg,pts): assert deg==5 and len(pts)==6; c('nurbs'); return NurbsCurve(pts[0],pts[-1])
class Curve:
    @staticmethod
    def JoinCurves(cs,tol):
        for x,y in zip(cs,cs[1:]): assert math.dist((x.b.X,x.b.Y,x.b.Z),(y.a.X,y.a.Y,y.a.Z))<1e-6
        assert math.dist((cs[-1].b.X,cs[-1].b.Y,cs[-1].b.Z),(cs[0].a.X,cs[0].a.Y,cs[0].a.Z))<1e-6
        return [_Crv(closed=True)]
class PolylineCurve(_Crv):
    def __init__(s,pts): c('pl'); s.pts=pts
    def Contains(s,q,pl,tol):
        poly=Polygon([(p.X,p.Y) for p in s.pts]); return PointContainment.Inside if poly.contains(Point(q.X,q.Y)) else PointContainment.Outside
class PointContainment: Inside=1; Outside=2
class Ellipse:
    def __init__(s,pl,a,b): pass
    def ToNurbsCurve(s): return _Crv(closed=True)
class _Face:
    def CreateExtrusion(s,path,cap): c('extr'); return object()
class _Brep:
    Faces=[_Face()]
    def CapPlanarHoles(s,tol): return s
class Brep:
    @staticmethod
    def CreatePlanarBreps(cs,tol): c('planar'); return [_Brep()]
    @staticmethod
    def CreateFromSweep(r,s,cl,tol): c('sweep'); return [_Brep()]
class Arc:
    def __init__(s,a,m,b): pass
class ArcCurve(_Crv):
    def __init__(s,a): pass
class _H(_Crv):
    def __init__(s,pts): s.pts=pts; s.PointAtStart=pts[0]; s.PointAtEnd=pts[-1]
    def DuplicateSegments(s):
        return [ _Seg(a,b) for a,b in zip(s.pts,s.pts[1:]) ]
class _Seg:
    def __init__(s,a,b): s.PointAtStart=a; s.PointAtEnd=b
def _cic(pts,deg): c('interp'); return NurbsCurve(pts[0],pts[len(pts)-1])
Curve.CreateInterpolatedCurve=staticmethod(_cic)
class Circle:
    def __init__(s,c,r): s.c=c
    def ToNurbsCurve(s): return _Crv(closed=True)
def _dupseg(s): return [_Seg(a,b) for a,b in zip(s.pts,s.pts[1:])]
PolylineCurve.DuplicateSegments=_dupseg
