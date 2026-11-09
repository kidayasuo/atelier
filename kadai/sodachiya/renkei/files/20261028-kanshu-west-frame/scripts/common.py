import sys, numpy as np, re, pickle, math
sys.path.insert(0,'/home/claude/atelier/sodachiya/model/build/south')
import solids, uv as U
RW=U.RW
FU=[21.33,24,27,30,33,36,39,42,45,48]
def to_local(V):
    th=np.arctan2(V[:,1]-U.CY,V[:,0]-U.CX)%(2*np.pi)
    u=(U.TH_S-th)*RW/1000; r=np.hypot(V[:,0]-U.CX,V[:,1]-U.CY); v=(RW-r)/1000
    return u,v,r
def west_parts(path,pat=r'^22[abcd]_'):
    import rhino3dm as r3, trimesh
    m=r3.File3dm.Read(path); LN={i:l.FullPath for i,l in enumerate(m.Layers)}
    out=[]
    for i,o in enumerate(m.Objects):
        ln=LN[o.Attributes.LayerIndex].split('::')[-1]
        if not re.match(pat,ln): continue
        vf=solids.geom_vf(o.Geometry)
        if vf is None: print('novf',ln,type(o.Geometry).__name__); continue
        t=solids.to_trimesh(*vf)
        p=dict(i=i,layer=ln,name=o.Attributes.Name or '',tm=t,M=solids.to_manifold(t),typ=type(o.Geometry).__name__)
        V=np.asarray(p['tm'].vertices); u,v,r=to_local(V)
        if np.median(v)>-0.35: continue
        p['ln']=ln[:3]; p['uvz']=np.c_[u,v,V[:,2]]
        uc=np.median(u); f=min(FU,key=lambda x:abs(x-uc))
        # local t (mm) from the radial plane of frame f
        th0=U.TH_S-f*1000/RW; th=U.TH_S-u*1000/RW
        p['f']=f; p['t']=r*np.sin(th0-th); p['tc']=float(np.median(p['t']))
        p['guid']=str(m.Objects[p['i']].Attributes.Id)
        out.append(p)
    return m,out
