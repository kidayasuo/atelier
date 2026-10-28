from ana import *
import collections
st=sys.argv[1]; P=pickle.load(open(f'st/{st}.3dm.pk','rb'))
for p in P: p['tc']=float((p['t'].min()+p['t'].max())/2)
G=[p for p in P if p['ln']=='22d']
def secs(p):
    return section(p['tm'],p['f'],p['tc'])
print('== ply outlines (pairs on same frame, same name, t<0 vs t>0)')
grp=collections.defaultdict(list)
for p in P:
    if p['ln'] in ('22b','22c'): grp[(p['f'],p['ln'],p['name'])].append(p)
for k,L in sorted(grp.items()):
    if len(L)!=2: print('  unpaired',k[0],k[1],k[2][:25],[round(x['tc']) for x in L]); continue
    a,b=sorted(L,key=lambda x:x['tc'])
    sa=section(a['tm'],a['f'],a['tc']); sb=section(b['tm'],b['f'],b['tc'])
    if sa is None or sb is None: print('  nosec',k); continue
    xa=sa.symmetric_difference(sb); 
    hd=sa.exterior.hausdorff_distance(sb.exterior) if sa.geom_type=='Polygon' and sb.geom_type=='Polygon' else -1
    ba,bb_=sa.bounds,sb.bounds
    dend=[round(bb_[i]-ba[i]) for i in range(4)]
    flag='' if xa.area<2e4 and hd<5 else '  <<'
    print(f'  u{k[0]} {k[1]} {k[2][:18]:18s} t={a["tc"]:.0f}/{b["tc"]:.0f} xor={xa.area/1e6:.3f}m2 haus={hd:.0f}mm dbounds(vmin,zmin,vmax,zmax)={dend}{flag}')
print('== holes vs girders')
for p in P:
    if p['ln'] not in ('22a','22b','22c'): continue
    s=section(p['tm'],p['f'],p['tc'])
    if s is None: continue
    hs=holes(s)
    gb=[]
    for g in G:
        bb=g['tm'].bounds
        sg=section(g['tm'],p['f'],p['tc'])
        if sg is None or sg.is_empty: continue
        gb+=blobs(sg)
    for hv,hz,ha in hs:
        if ha<5e4: continue
        if gb:
            d=min(gb,key=lambda b:math.hypot(b[0]-hv,b[1]-hz)); dist=math.hypot(d[0]-hv,d[1]-hz)
        else: dist=1e9; d=None
        if dist>3:
            print(f'  {p["ln"]} u{p["f"]} t{p["tc"]:.0f} {p["name"][:16]} hole v{hv/1000:.2f} z{hz:.0f} ({ha/1e3:.0f}k): girder off {"none" if d is None or dist>800 else f"dv={d[0]-hv:.0f} dz={d[1]-hz:.0f}"}')
    # girders through solid wood
    for b in gb:
        pass
    for g in G:
        sg=section(g['tm'],p['f'],p['tc'])
        if sg is None or sg.is_empty: continue
        ov=sg.intersection(s).area
        if ov>500: print(f'  {p["ln"]} u{p["f"]} t{p["tc"]:.0f} girder {g["name"][:12]} cuts wood {ov/1e3:.1f}k mm2 at v{sg.centroid.x/1000:.2f} z{sg.centroid.y:.0f}')
