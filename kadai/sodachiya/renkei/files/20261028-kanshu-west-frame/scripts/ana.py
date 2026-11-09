import pickle, sys, numpy as np, math, trimesh, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0,'/home/claude/atelier/sodachiya/model/build/south')
import uv as U
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
RW=U.RW; C=np.array([U.CX,U.CY,0.])
def frame_axes(f):
    th0=U.TH_S-f*1000/RW
    rad=np.array([math.cos(th0),math.sin(th0),0.]); n=np.array([-math.sin(th0),math.cos(th0),0.])
    # t = r sin(th0-th): positive when th<th0 i.e. larger u. n points to increasing th -> t = -dot(P-C,n)
    return rad,n
def section(tm,f,t):
    rad,n=frame_axes(f)
    o=C-n*t
    s=tm.section(plane_origin=o,plane_normal=n)
    if s is None: return None
    polys=[]
    for e in s.discrete:
        q=np.c_[(RW-(e-C)@rad)/1000.0, e[:,2]]
        if len(q)>=3: polys.append(q)
    # even-odd assemble
    res=None
    for q in polys:
        pg=Polygon(np.c_[q[:,0]*1000,q[:,1]]).buffer(0)   # v in mm
        res=pg if res is None else res.symmetric_difference(pg)
    return res
def holes(pg):
    out=[]
    for g in getattr(pg,'geoms',[pg]):
        for r in g.interiors:
            P=Polygon(r); out.append((P.centroid.x,P.centroid.y,P.area))
    return out
def blobs(pg):
    return [ (g.centroid.x,g.centroid.y,g.area,g.bounds) for g in getattr(pg,'geoms',[pg]) if g.area>1]
