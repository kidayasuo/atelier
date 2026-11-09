import sys, ezdxf
sys.path.insert(0,'/tmp/claude-0/mock2')
import Rhino.Geometry as rg
d=ezdxf.readfile('/home/claude/plans/rhino/sodachiya_site.dxf')
C={}
for e in d.modelspace().query('LWPOLYLINE'):
    pts=[rg.Point3d(p[0],p[1],0) for p in e.get_points()]; pts.append(pts[0]); C[e.dxf.layer]=rg.PolylineCurve(pts)
code=open('/home/claude/plans/rhino/sodachiya_frames_gh.py').read()
def run(**kw):
    g={'__name__':'gh','Site':C['SITE'],'Setback':C['SITE_setback_1m']}; g.update(kw)
    exec(compile(code,'gh','exec'),g); return g
