exec(open('/tmp/claude-0/t/ideas/hinge.py').read())
NEl=SL([V['N'],V['E']])
rooms=[(0,9,'0・1歳','#F4D9C6'),(9,15,'2歳','#F4D9C6'),(15,21,'事務・医務','#E3E3E3'),(21,30,'ホール','#F6D27A'),(30,33,'便','#E3E3E3'),
       (33,39,'3歳','#F9E7C9'),(39,42,'便','#E3E3E3'),(42,48,'4歳','#F9E7C9'),(48,51,'便','#E3E3E3'),(51,57,'5歳','#F9E7C9')]
def build(rf,Lw,variant):
    S=make_spine(rf); Ln=57000-Lw-0
    pts,La=spine_pts(S,Lw,57000-Lw,250)
    Ln=57000-Lw-La
    pts,La=spine_pts(S,Lw,Ln,250)
    L=len(pts)*250
    parts=[]
    for a,b,t,c in rooms:
        parts.append((band_from(pts,a*1000,b*1000,0,12000),t,c))
    eave=band_from(pts,0,57000-250,12000,15000)
    # hall garden-face centre & outward direction
    hm=int(25500/250); p,n=pts[hm]
    extra=[]
    if variant=='Y':
        t=n; side=np.array([-t[1],t[0]])
        o=p+n*12700
        def rect(d0,d1,w):
            q=[o+t*d0+side*w/2,o+t*d1+side*w/2,o+t*d1-side*w/2,o+t*d0-side*w/2]; return SP([tuple(x) for x in q])
        extra=[(rect(0,3000,9000),'土間','#FBE9B8'),(rect(3000,12000,9000),'キッチン\n(2階:休憩・会議)','#BFD7EE'),(rect(12000,35000,12000),'遊戯室\n%.0f㎡','#CFE0F2')]
    else:
        o=p+n*12700
        k=SP([tuple(o+np.array([-n[1],n[0]])*4500),tuple(o-np.array([-n[1],n[0]])*4500),tuple(o-np.array([-n[1],n[0]])*4500+n*9000),tuple(o+np.array([-n[1],n[0]])*4500+n*9000)])
        drum=SPt(*(o+n*(9000+9600))).buffer(9300)
        extra=[(k,'キッチン\n(2階:休憩・会議)','#BFD7EE'),(drum,'遊戯室\n%.0f㎡','#CFE0F2')]
    allb=[q for q,_,_ in parts]+[eave]+[q for q,_,_ in extra]
    bl=unary_union(allb)
    bad=bl.difference(setb).area/1e6+max(0,1000-NEl.distance(bl))/100+bl.intersection(park.buffer(1500)).area/1e6
    return S,parts,eave,extra,bad,Lw,Ln
for variant in ('drum','Y'):
    best=None
    for rf in range(16000,40001,2000):
        for Lw in range(8000,40001,1000):
            try: r=build(rf,Lw,variant)
            except Exception as e: continue
            if r[6]<0: continue
            # garden: site minus all
            bl=unary_union([q for q,_,_ in r[1]]+[r[2]]+[q for q,_,_ in r[3]])
            g=garden_area([bl])
            key=(round(r[4],1),-g)
            if best is None or key<best[0]: best=(key,rf,Lw,g)
    print(variant,best)
