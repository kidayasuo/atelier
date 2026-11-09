exec(open('/tmp/claude-0/t/ideas/check_vars.py').read().split("titles=")[0])
def load2(path):
    f=r3.File3dm.Read(path); names={i:l.Name for i,l in enumerate(f.Layers)}
    cols={'10_本館_屋根':(0.85,0.82,0.76),'11_本館_骨組み':(0.55,0.40,0.25),'20_西館_屋根':(0.62,0.58,0.52),'21_西館_外壁':(0.88,0.82,0.72),'22_西館_骨組み':(0.55,0.40,0.25),
          '23_西館_2階床':(0.70,0.66,0.60),'24_西館_間仕切り':(0.92,0.90,0.86),'25_西館_階段':(0.47,0.43,0.39),'35_機械室（本館の北）':(0.70,0.68,0.64),'26_室外機置場（屋根の上）':(0.45,0.45,0.45)}
    F=[]
    for o in f.Objects:
        g=o.Geometry; n=names[o.Attributes.LayerIndex]
        if isinstance(g,r3.Mesh) and (n in cols or n[:2] in ('31','32','33','34','35','36','41','42','43','44','45')):
            col=cols.get(n,(0.8,0.8,0.8)); 
            if n[:2] in ('31','32','33','34','35','36','41','42','43','44','45'):
                L=f.Layers[o.Attributes.LayerIndex]; col=tuple(np.array(L.Color[:3])/255)
            V=[(g.Vertices[i].X,g.Vertices[i].Y,g.Vertices[i].Z) for i in range(len(g.Vertices))]
            for j in range(len(g.Faces)):
                a,b,c,d=g.Faces[j]; idx=[a,b,c] if c==d else [a,b,c,d]
                F.append((np.array([V[i] for i in idx]),col,n))
    return F
allF=load2('/home/claude/plans/rhino/sodachiya_west_case3.3dm')
fig,axs=plt.subplots(2,2,figsize=(16,10))
globals()['faces']=[(p,c) for p,c,n in allF]
view(axs[0,0],np.r_[W-bis*40000+np.array([0,-10000]),30000],np.r_[c+np.array([3000,-6000]),0],1.4,'北西の上空から')
view(axs[0,1],np.r_[np.array([-32000,-48000]),1500],np.r_[np.array([-15000,-40000]),2500],0.7,'西の道路から')
globals()['faces']=[(p,c) for p,c,n in allF if n not in ('20_西館_屋根','10_本館_屋根','21_西館_外壁')]
view(axs[1,0],np.r_[W-bis*40000+np.array([0,-10000]),30000],np.r_[c+np.array([3000,-6000]),0],1.4,'屋根と外壁を外して（骨組み・部屋・階段）')
view(axs[1,1],np.r_[np.array([25000,-25000]),22000],np.r_[c+np.array([0,-8000]),2000],1.2,'屋根と外壁を外して（園庭の上空から）')
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_case3_views.png',dpi=68)
