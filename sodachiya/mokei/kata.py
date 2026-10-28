"""本館の架構を平らに組む型（2 段）。切った部品 02_架構の試作1本_桁穴D.svg の形から作る（10-28、模型の相談のチャット）。
  python3 sodachiya/mokei/kata.py  →  mokei/cut/12a_・12b_
"""
import os
HERE = os.path.dirname(os.path.abspath(__file__)); CUT = os.path.join(HERE, "cut")
os.chdir(CUT)
import sys; sys.argv = ["", "02_架構の試作1本_桁穴D.svg"]
import re, sys
from shapely.geometry import Polygon, LineString
from shapely.ops import linemerge, polygonize, unary_union, snap
src=open(sys.argv[1]).read()
red=src.split('id="切る（赤）"')[1].split('</g>')[0]
lines=[]
for d in re.findall(r'd="([^"]+)"',red):
    pts=[tuple(map(float,p.split(','))) for p in re.findall(r'[-\d.]+,[-\d.]+',d)]
    closed=d.strip().endswith('Z')
    if closed: pts.append(pts[0])
    lines.append((pts,closed))
# join open polylines: connect each end to nearest other end within 1mm
rings=[Polygon(p) for p,c in lines if c]
opn=[p for p,c in lines if not c]
import math
while opn:
    cur=opn.pop(0)
    while True:
        e=cur[-1]
        if math.dist(e,cur[0])<1.0 and len(cur)>3: break
        best=min(range(len(opn)),key=lambda i:min(math.dist(e,opn[i][0]),math.dist(e,opn[i][-1])))
        nxt=opn.pop(best)
        if math.dist(e,nxt[-1])<math.dist(e,nxt[0]): nxt=nxt[::-1]
        cur=cur+nxt
    rings.append(Polygon(cur).buffer(0))
rings.sort(key=lambda p:-p.area)
# build parts: big rings minus contained small rings
parts=[]
used=set()
for i,p in enumerate(rings):
    if i in used: continue
    if any(q.contains(p) for j,q in enumerate(rings) if j!=i and q.area>p.area): continue
    holes=[j for j,q in enumerate(rings) if j!=i and p.contains(q)]
    g=p
    for j in holes: g=g.difference(rings[j]); used.add(j)
    parts.append(g)
if 0: print(round(g.area,2),[round(v,2) for v in g.bounds], len(g.interiors) if g.geom_type=='Polygon' else g.geom_type)
import pickle; PARTS=parts
parts=PARTS
import pickle
from shapely.geometry import Polygon
from shapely import affinity
P=PARTS
beam=P[0]; cw=P[2]; ce=P[4]
def hc(g): return [Polygon(i).centroid for i in g.interiors]
bh=sorted(hc(beam),key=lambda p:p.x)
for name,c,h in []:# [('E',ce,bh[0]),('W',cw,bh[1])]:
    ch=hc(c)[0]
    print(name,'beam hole',round(h.x,3),round(h.y,3),'col hole',round(ch.x,3),round(ch.y,3))
from shapely.ops import unary_union
ce2=affinity.translate(ce,bh[0].x-hc(ce)[0].x,bh[0].y-hc(ce)[0].y)
cw2=affinity.translate(cw,bh[1].x-hc(cw)[0].x,bh[1].y-hc(cw)[0].y)
if 0: print('feet bottom E/W',round(ce2.bounds[3],3),round(cw2.bounds[3],3))
fill=lambda g: Polygon(g.exterior)
frame=unary_union([fill(beam),fill(ce2),fill(cw2)])
if 0: print(frame.geom_type,[round(v,2) for v in frame.bounds])
# concave corners
import numpy as np
C=np.array(frame.exterior.coords)[:-1]
ccw=frame.exterior.is_ccw
cc=[]
for i in range(len(C)):
    a,b,c=C[i-1],C[i],C[(i+1)%len(C)]
    cr=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
    v1=b-a; v2=c-b
    ang=abs(np.degrees(np.arctan2(cr, v1@v2)))
    if (cr<0 if ccw else cr>0) and ang>30: cc.append((round(b[0],2),round(b[1],2),round(ang)))
if 0: print('concave',cc)
F=dict(beam=fill(beam),ce=fill(ce2),cw=fill(cw2),frame=frame,cc=cc)
import pickle
from shapely.geometry import Point, box, Polygon
from shapely.ops import unary_union
from shapely import affinity
frame,beam,ce,cw=F['frame'],F['beam'],F['ce'],F['cw']
M=8.0; GAP=3.0; O=3.0
x0,y0,x1,y1=frame.bounds
outer=box(x0-M,y0-M,x1+M,y1+M)
corners=[Point(x,y).buffer(0.8,32) for x,y,a in F['cc'] if y<50]
# finger notches on beam top edge
def top_y(x):
    from shapely.geometry import LineString
    l=LineString([(x,0),(x,100)]).intersection(beam); return l.bounds[1]
notches=[Point(x,top_y(x)).buffer(3,32) for x in (60,110)]
upper_pocket=unary_union([frame.buffer(-0.1,join_style=2)]+corners+notches)
upper=outer.difference(upper_pocket)
lower_pocket=unary_union([beam.buffer(0.2), unary_union([ce,cw]).intersection(beam.buffer(1.0)).buffer(0.2)])
lower=outer.difference(lower_pocket)
W=outer.bounds[2]-outer.bounds[0]; H=outer.bounds[3]-outer.bounds[1]
def sheet(name,geom,note,label):
    gs=[affinity.translate(geom,O-outer.bounds[0],O-outer.bounds[1]+k*(H+GAP)) for k in (0,1)]
    sw=O*2+W; sh=O*2+2*H+GAP
    def rings(g):
        for p in getattr(g,'geoms',[g]):
            yield p.exterior
            yield from p.interiors
    paths=''.join('<path d="M'+' L'.join(f'{x:.3f},{y:.3f}' for x,y in r.coords)+' Z"/>\n' for g in gs for r in rings(g))
    t=''.join(f'<text x="{O+M:.2f}" y="{O+k*(H+GAP)+H-2:.2f}" font-size="2.5">{label} {k+1}</text>\n' for k in (0,1))
    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{sw:.1f}mm" height="{sh:.1f}mm" viewBox="0 0 {sw:.1f} {sh:.1f}">
<!-- {note} -->
<g id="参考（切らない・送る前に消す）" fill="none" stroke="#000000" stroke-width="0.01">
<path d="M0,0 L{sw:.1f},0 L{sw:.1f},{sh:.1f} L0,{sh:.1f} Z"/>
</g>
<g id="切る（赤）" fill="none" stroke="#FF0000" stroke-width="0.01">
{paths}</g>
<g id="参考の文字（送る前に消す）" fill="#000000" stroke="none" font-family="sans-serif">
{t}</g></svg>'''
    open(name,'w').write(svg); print(name, round(sw,1),'x',round(sh,1))
sheet('12a_架構の型_上の段_シナ1.7.svg',upper,'シナ 1.7：本館の架構を平らに組む型の上の段 ×2（架構の形の抜き、入隅の逃げ、指を入れる切り欠き）','型 上の段')
sheet('12b_架構の型_下の段_航空ベニヤ0.8.svg',lower,'航空ベニヤ 0.8：型の下の段 ×2（下の梁の抜き、梁の縁から 1 mm の逃げ）','型 下の段')
