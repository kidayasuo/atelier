import sys, re, numpy as np, rhino3dm as r
from shapely.geometry import Polygon, LinearRing
from shapely.validation import explain_validity
sys.path.insert(0,'/home/claude/atelier/sodachiya/model/build/south')
import solids
from common import to_local, FU
m=r.File3dm.Read(sys.argv[1]); LN={i:l.FullPath.split('::')[-1] for i,l in enumerate(m.Layers)}
for i,o in enumerate(m.Objects):
    ln=LN[o.Attributes.LayerIndex]
    if not re.match(r'^22[abcd]_',ln): continue
    g=o.Geometry
    pl=g.GetProfilePlane(0.0); O=np.array([pl.Origin.X,pl.Origin.Y,pl.Origin.Z]); X=np.array([pl.XAxis.X,pl.XAxis.Y,pl.XAxis.Z]); Y=np.array([pl.YAxis.X,pl.YAxis.Y,pl.YAxis.Z])
    rings=[]
    for k in range(g.ProfileCount):
        P=solids.A3(solids.curve_pts(g.Profile3d(k,0.0)))
        q=np.c_[(P-O)@X,(P-O)@Y]; rings.append(q)
    issues=[]
    if not g.IsValid: issues.append('INVALID')
    try:
        po=Polygon(rings[0])
        if not po.is_valid: issues.append('outer:'+explain_validity(po)[:40])
        for k,q in enumerate(rings[1:],1):
            ph=Polygon(q)
            if not ph.is_valid: issues.append(f'hole{k}:'+explain_validity(ph)[:30])
            if not po.buffer(0).contains(ph.buffer(0)):
                inter=po.buffer(0).intersection(ph.buffer(0)).area/ max(ph.area,1)
                issues.append(f'hole{k} outside outer ({inter:.0%} inside)')
            # min wall between hole and outer
            d=po.exterior.distance(ph)
            if d<30: issues.append(f'hole{k} wall {d:.0f}mm')
        # thin slivers: parts of outer polygon thinner than 20mm
        pb=po.buffer(0); er=pb.buffer(-10).buffer(10)
        thin=pb.difference(er).area
        if thin>2000: issues.append(f'thin parts {thin/1e3:.0f}k mm2')
    except Exception as e: issues.append('ERR '+str(e)[:40])
    if issues:
        bb=g.GetBoundingBox(); V=np.array([[bb.Min.X,bb.Min.Y,bb.Min.Z],[bb.Max.X,bb.Max.Y,bb.Max.Z]])
        u,v,_=to_local(V.mean(0)[None])
        if v[0]>-0.35: continue
        print(ln[:3], f'u{u[0]:.2f} v{v[0]:.2f} z{bb.Min.Z:.0f}-{bb.Max.Z:.0f}', o.Attributes.Name[:20], str(o.Attributes.Id)[:8], 'np=%d'%g.ProfileCount, '; '.join(issues))
