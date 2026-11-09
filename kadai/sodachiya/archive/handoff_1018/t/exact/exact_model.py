import sys, json, math; sys.path.insert(0,'/tmp/claude-0/t/exact')
OUT=globals().get('OUT','/home/claude/plans/rhino/sodachiya_exact.3dm')
src=open('/tmp/claude-0/t/ideas/case3.py').read()
src=src.replace("model.Write('/home/claude/plans/rhino/sodachiya_west_case3.3dm',8)","pass").replace("print('written')","")
src=src.replace("    def add(s,n):\n        if s.n:","    def add(s,n):\n        if n in SKIP: return\n        if s.n:")
SKIP={'11_本館_骨組み','22_西館_骨組み'}
exec(src)
from exact import *
world_=G['world']
C=[c for c in json.load(open('/tmp/claude-0/t/ideas/conform.json')) if c[0]=='tri' and c[1]==205000][0]
place(C[1],(C[2][0],C[2][1]),C[2][2],700)
CT,BT=G['COL_T'],G['BEAM_T']; GW,GH_=G['GIRDER_W'],G['GIRDER_H']; HC=G['HOLE_CLEAR']
for n,c in [('11a_本館_柱',(150,105,60)),('11b_本館_梁',(170,125,75)),('11c_本館_桁',(120,85,50)),
            ('22a_西館_柱',(150,105,60)),('22b_西館_梁',(170,125,75)),('22c_西館_2階床梁',(185,140,90)),('22d_西館_桁',(120,85,50))]:
    layer(n,c)
PREV=[]      # プレビュー用 (polygon, layer)
def prev_plate(Bd,th,segs,t0,thick,lay):
    q=seg_poly(segs)
    if len(q)>160: q=q[::max(1,len(q)//160)]+[q[-1]]
    A=[world_(Bd,th,u,z,t0) for u,z in q]; Bq=[world_(Bd,th,u,z,t0+thick) for u,z in q]
    PREV.append((np.array(A),lay)); PREV.append((np.array(Bq),lay))
    for i in range(len(q)-1): PREV.append((np.array([A[i],A[i+1],Bq[i+1],Bq[i]]),lay))
def add_plate(Bd,th,segs,holes,t0,thick,lay):
    e,ok=plate(world_,Bd,th,segs,holes,t0,thick,GW+2*HC,GH_+2*HC)
    if not (ok and e.IsValid): print('invalid plate',lay)
    model.Objects.AddExtrusion(e,at_(lay)); prev_plate(Bd,th,segs,t0,thick,lay)
def prev_tube(pts,lay,n=10):
    """楕円の桁のプレビュー：点列（中心）に沿う 8 角の筒"""
    pts=[np.array(p,float) for p in pts]
    ring=[]
    for i,p in enumerate(pts):
        d=(pts[min(i+1,len(pts)-1)]-pts[max(i-1,0)]); d[2]=0; d/=np.linalg.norm(d)
        s=np.array([-d[1],d[0],0])
        ring.append([p+s*GW/2*math.cos(a)+np.array([0,0,GH_/2*math.sin(a)]) for a in np.linspace(0,2*math.pi,9)[:-1]])
    for i in range(len(pts)-1):
        for j in range(8): PREV.append((np.array([ring[i][j],ring[i][(j+1)%8],ring[i+1][(j+1)%8],ring[i+1][j]]),lay))
# ---------------- 本館 ----------------
B=G['buildings']()[0]; P=B['prof']
for th in B['thetas']:
    for c in P['cols']:
        add_plate(B,th,c['segs'],[h for h in P['holes'] if abs(h[0]-c['u'])<1],-CT/2,CT,'11a_本館_柱')
    for t0 in (-CT/2-BT,CT/2): add_plate(B,th,P['beam'],P['holes'],t0,BT,'11b_本館_梁')
OV=G['GIRDER_OVERHANG']
for hu,hz in P['holes']:
    r=B['R']+hu; tha=B['thetas'][0]-OV/r; thb=B['thetas'][-1]+OV/r
    model.Objects.AddBrep(girder_arc(G['CENTER'],r,hz,tha,thb,GW,GH_),at_('11c_本館_桁'))
    prev_tube([world_(B,tha+(thb-tha)*i/40,hu,hz) for i in range(41)],'11c_本館_桁')
# ---------------- 西館 ----------------
Cc_=np.array(G['CENTER']); INS=400.0
heads_in=[]; heads_out=[]; f2_in=[]; f2_out=[]
REPORT=[]
for k,a,b,L in FR:
    if L<2500: continue
    th=thf(k); Rk=np.linalg.norm(np.array(a)-Cc_)+INS; Dk=L-2*INS
    Bk=dict(R=Rk,D=Dk,EAVE=0.0)
    off=(np.linalg.norm(np.array(a)-Cc_)-bm['R']-12000)-np.interp(k,kk,uin); Lr=np.interp(k,kk,uout-uin)
    te=zroof(k,INS+off,Lr); tw=zroof(k,L-INS+off,Lr)
    Pk=G['frame_profiles'](Bk,te,tw,700.0,0.0,250.0)
    Bk['prof']=Pk; Bk['TOP_E']=te; Bk['TOP_W']=tw
    cols=Pk['cols']; holes_all=list(Pk['holes'])
    endf=(k==KE)
    if k>=K2-0.01:
        Bk['FLOOR2_TOP']=Z2-50.0; Bk['FLOOR2_DEPTH']=450.0 if endf else HB2
        F=floor2_big(G,Bk,Z2+1500)
        cols=F['cols']; holes_all+=F['holes']
        for t0 in (-CT/2-BT,CT/2): add_plate(Bk,th,F['beam'],F['holes'],t0,BT,'22c_西館_2階床梁')
        f2_in.append(world_(Bk,th,0,F['holes'][0][1])); f2_out.append(world_(Bk,th,Dk,F['holes'][1][1]))
    for c in cols:
        add_plate(Bk,th,c['segs'],[h for h in holes_all if abs(h[0]-c['u'])<1],-CT/2,CT,'22a_西館_柱')
    for t0 in (-CT/2-BT,CT/2): add_plate(Bk,th,Pk['beam'],Pk['holes'],t0,BT,'22b_西館_梁')
    heads_in.append(world_(Bk,th,0,Pk['holes'][0][1])); heads_out.append(world_(Bk,th,Dk,Pk['holes'][1][1]))
    REPORT.append((round(float(k),2),round(Dk),round(te),round(tw)))
for line in (heads_in,heads_out,f2_in,f2_out):
    for p0,p1 in zip(line,line[1:]):
        model.Objects.AddExtrusion(girder_line(p0,p1,GW,GH_),at_('22d_西館_桁'))
    if len(line)>1: prev_tube(line,'22d_西館_桁')
print('west frames (k, span, top_e, top_w):',REPORT)
model.Write(OUT,8); print('written',OUT)
