import sys
s=open('build_2story.py').read()
old=s[s.index("SINK=0.0\nZOUT=6300.0"):s.index("# --- areas")]
new='''SINK=0.0
import os
VAR=os.environ.get('VAR','B3')
ZE={'A':6500.0,'B2':6500.0,'B3':8000.0}[VAR]; ZW=4500.0
def zprof(k,d,L):
    return ZE+(ZW-ZE)*d/max(L,1)
'''
s=s.replace(old,new)
i=s.index("print('playroom %.0f m2, avg ceiling(参考)"); j=s.index("\n",i)
s=s[:i]+"print(VAR,'playroom %.0f m2 (avg ceiling %.2f), kitchen block %.0f m2'%(play.area/1e6,h.mean(),kit.area/1e6))"+s[j:]
a=s.index("slab=band_poly(KH+0.02,kk[-1],1500,60000).intersection(W)"); b=s.index("for k in np.arange(2.0,12.01,1.0):")
s=s[:a]+'''def zone_area(poly,zmin,zmax=1e9):
    pts=[(x,y) for x in np.arange(poly.bounds[0],poly.bounds[2],250) for y in np.arange(poly.bounds[1],poly.bounds[3],250) if poly.contains(SPt(x,y))]
    return sum(1 for p in pts if zmin<=zat2(p)-300-3250<zmax)*0.0625
def slab2(poly,label):
    m=MB(); poly_fill(poly,3250.0,m); m.add('23_西館_2階')
    curve([(x,y,3260) for x,y in poly.exterior.coords],'23_西館_2階')
    c=poly.representative_point(); model.Objects.AddTextDot(label,r3.Point3d(c.x,c.y,4300),attrs('23_西館_2階'))
if VAR=='B3':
    sl=band_poly(KH-1.0,kk[-1],0,9000).intersection(W)
    slab2(sl,'2階：会議室＋休憩室（高い側）／ぐったり休憩（低い側）')
    print('2F total %.0f, clear>=2.4: %.0f, 1.4-2.4: %.0f'%(sl.area/1e6,zone_area(sl,2400),zone_area(sl,1400,2400)))
if VAR=='B2':
    sl=band_poly(KH,kk[-1],0,6000).intersection(W)
    slab2(sl,'2階：屋根裏の休憩（ぐったり）')
    print('2F total %.0f, clear>=2.4: %.0f, 1.4-2.4: %.0f'%(sl.area/1e6,zone_area(sl,2400),zone_area(sl,1400,2400)))
if VAR=='A':
    mb2=MB()
    def mwz(k,u,z): p=world(bm,thf(k),u,0); return (p[0],p[1],z)
    k0,k1=19-8,20-6; u0,u1=3000,12200; zf,zr=4300,7300
    ks=np.linspace(k0,k1,13)
    for a_,b_ in zip(ks,ks[1:]):
        mb2.quad([mwz(a_,u0,zr),mwz(b_,u0,zr),mwz(b_,u1,zr),mwz(a_,u1,zr)])
        for u in (u0,u1): mb2.quad([mwz(a_,u,zf),mwz(b_,u,zf),mwz(b_,u,zr),mwz(a_,u,zr)])
    for k in (k0,k1): mb2.quad([mwz(k,u0,zf),mwz(k,u1,zf),mwz(k,u1,zr),mwz(k,u0,zr)])
    mb2.add('12_本館_2階')
    c=world(bm,thf((k0+k1)/2),7600,0); model.Objects.AddTextDot('本館の上の2階：休憩室60＋会議室30',r3.Point3d(c[0],c[1],5800),attrs('12_本館_2階'))
    area=(thf(k1)-thf(k0))*(bm['R']+(u0+u1)/2)*(u1-u0)/1e6
    print('main 2F %.0f m2'%area)
for txt,pt in [('遊戯室',play.representative_point()),('キッチン',kit.representative_point())]:
    model.Objects.AddTextDot(txt,r3.Point3d(pt.x,pt.y,2000),attrs('22_西館_床'))
'''+s[b:]
a=s.index("# キャットウォーク（2 階の高さ、道路側の壁に沿って幅 1.2m）"); b=s.index("model.Write(",a)
s=s[:a]+'''cw=[]
for k in [x for x in kk if 3.0<=x<=KH-1.0]:
    a,b,L=segs[k]; cw.append((a+(b-a)*1200/L).tolist()+[3250])
curve(cw,'23_西館_2階')
'''+s[b:]
s=s.replace("    if k>=KH: curve([P(1500,3250),P(L,3250)],'30_架構の線')","")
s=s.replace("('30_架構の線',(60,60,160))","('30_架構の線',(60,60,160)),('12_本館_2階',(190,150,110))")
# main labels for B2
s=s.replace("mrooms=[(1,3,'0・1歳'),(4,5,'2歳'),(6,7,'事務・医務'),(8,10,'ホール'),","mrooms=[(1,3,'0・1歳'),(4,5,'2歳'),(6,7,'事務・医務')]+([(8,9,'ホール'),(10,10,'会議室＋休憩の半分')] if VAR=='B2' else [(8,10,'ホール')])+[")
s=s.replace("model.Write('/home/claude/plans/rhino/sodachiya_west_2story.3dm',8)","model.Write('/home/claude/plans/rhino/sodachiya_west_var%s.3dm'%VAR,8)")
open('build_var.py','w').write(s)
