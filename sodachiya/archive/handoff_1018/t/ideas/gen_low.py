s=open('build_2story.py').read()
old=s[s.index("SINK=0.0\nZOUT=6300.0"):s.index("# --- areas")]
new='''SINK=0.0
K2=4.0                      # これより北（北西の角）が 2 階の職員の部屋
ZW=4500.0                   # 西の道沿いの軒
ZE=7000.0                   # 本館側の高い縁
Z2I,Z2O=7000.0,6600.0       # 北西の角の 2 階の屋根（本館側→道路側）
def zprof(k,d,L):
    if k<K2: return Z2I+(Z2O-Z2I)*d/max(L,1)
    return ZE+(ZW-ZE)*d/max(L,1)
'''
s=s.replace(old,new)
s=s.replace("play=W.intersection(SP([tuple(at(1.0,0))]+[tuple(at(k,0)) for k in np.linspace(1,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,1,20)]))",
"play=W.intersection(SP([tuple(at(K2,0))]+[tuple(at(k,0)) for k in np.linspace(K2,KH,20)]+[tuple(at(KH,60000))]+[tuple(at(k,60000)) for k in np.linspace(KH,K2,20)]))\nblk=W.intersection(SP([tuple(at(0.5,0))]+[tuple(at(k,0)) for k in np.linspace(0.5,K2,20)]+[tuple(at(K2,60000))]+[tuple(at(k,60000)) for k in np.linspace(K2,0.5,20)]))")
s=s.replace("kit=W.difference(play)","kit=W.difference(play).difference(blk)")
i=s.index("print('playroom %.0f m2, avg ceiling(参考)"); j=s.index("\n",i)
s=s[:i]+"print('playroom %.0f m2 (avg ceiling %.2f), kitchen %.0f m2, NW block %.0f m2 (1F nest + 2F)'%(play.area/1e6,h.mean(),kit.area/1e6,blk.area/1e6))"+s[j:]
s=s.replace("mf=MB(); poly_fill(play,-SINK,mf); poly_fill(kit,0.0,mf); mf.add('22_西館_床')","mf=MB(); poly_fill(play,0.0,mf); poly_fill(kit,0.0,mf); poly_fill(blk,0.0,mf); mf.add('22_西館_床')")
a=s.index("# 2F slab + rooms outline + void"); b=s.index("for k in np.arange(2.0,12.01,1.0):")
s=s[:a]+'''# 北西の角の 2 階
m2=MB(); poly_fill(blk,3250.0,m2); m2.add('23_西館_2階')
curve([(x,y,3260) for x,y in blk.exterior.coords],'23_西館_2階')
for txt,pt,z in [('遊戯室（本館側が高い吹抜け）',play.representative_point(),2000),('キッチン（平屋・高天井）',kit.representative_point(),2000),('1階：低い巣（遊戯室の一部）',blk.representative_point(),1500),('2階：休憩室・会議室・機械室',blk.representative_point(),4500)]:
    model.Objects.AddTextDot(txt,r3.Point3d(pt.x,pt.y,z),attrs('22_西館_床' if z<3000 else '23_西館_2階'))
mw2=MB()
a_,b_,L_=segs[min(kk,key=lambda x:abs(x-K2))]
for d0,d1 in zip(np.linspace(0,L_,13),np.linspace(0,L_,13)[1:]):
    p0=a_+(b_-a_)*d0/L_; p1=a_+(b_-a_)*d1/L_
    za0,za1=zprof(K2-1e-3,d0,L_),zprof(K2-1e-3,d1,L_); zb0,zb1=zprof(K2+1e-3,d0,L_),zprof(K2+1e-3,d1,L_)
    mw2.quad([(p0[0],p0[1],min(za0,zb0)),(p1[0],p1[1],min(za1,zb1)),(p1[0],p1[1],max(za1,zb1)),(p0[0],p0[1],max(za0,zb0))])
mw2.add('21_西館_外壁')
cw=[]
for k in [x for x in kk if K2<=x<=KH]:
    a,b,L=segs[k]; cw.append((a+(b-a)*1200/L).tolist()+[3250])
curve(cw,'23_西館_2階')
st=[]
for k in [x for x in kk if K2<=x<=KH]:
    a,b,L=segs[k]; t=(KH-k)/(KH-K2); st.append((a+(b-a)*2600/L).tolist()+[3250*t])
curve(st,'23_西館_2階')
'''+s[b:]
a=s.index("# walls\nmw_=MB()"); b=s.index("mw_.add('21_西館_外壁')")
s=s[:a]+'''# walls
mw_=MB(); mg=MB(); lat=[]
cs=list(W.exterior.coords)
def is_outer(p):
    k,u=ku(p); k=np.clip(k,kk[0],kk[-1]); return abs(u-np.interp(k,kk,uout))<150 and k>=K2
for a,b in zip(cs,cs[1:]):
    za,zb=zat2(a),zat2(b)
    m=((a[0]+b[0])/2,(a[1]+b[1])/2)
    if is_outer(m):
        mw_.quad([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zb-450),(a[0],a[1],za-450)])
        mg.quad([(a[0],a[1],za-450),(b[0],b[1],zb-450),(b[0],b[1],zb),(a[0],a[1],za)])
        seg=np.linalg.norm(np.array(b)-np.array(a))
        for t in np.arange(0,1,300/max(seg,1)):
            p=np.array(a)+(np.array(b)-np.array(a))*t; lat.append((p,zat2(p)-450))
    else:
        mw_.quad([(a[0],a[1],0),(b[0],b[1],0),(b[0],b[1],zb),(a[0],a[1],za)])
mg.add('25_西館_ハイサイド')
for p,z in lat:
    curve([(p[0],p[1],0),(p[0],p[1],z)],'24_縦格子')
'''+s[b:]
s=s.replace("('30_架構の線',(60,60,160))","('30_架構の線',(60,60,160)),('24_縦格子',(120,90,60)),('25_西館_ハイサイド',(170,210,230))")
s=s.replace("    if k>=KH: curve([P(1500,3250),P(L,3250)],'30_架構の線')","    if k<K2: curve([P(0,3250),P(L,3250)],'30_架構の線')")
a=s.index("# キャットウォーク（2 階の高さ、道路側の壁に沿って幅 1.2m）"); b=s.index("model.Write(",a)
s=s[:a]+s[b:]
s=s.replace("/home/claude/plans/rhino/sodachiya_west_2story.3dm","/home/claude/plans/rhino/sodachiya_west_lowstreet.3dm")
open('build_lowstreet.py','w').write(s)
