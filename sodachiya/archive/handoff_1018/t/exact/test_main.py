import sys; sys.path.insert(0,'/tmp/claude-0/t/exact')
exec(open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- model')[0].replace("print(","(lambda *a:None)("))
from exact import *
import json
C=[c for c in json.load(open('/tmp/claude-0/t/ideas/conform.json')) if c[0]=='tri' and c[1]==205000][0]
bm2,bw2=place(C[1],(C[2][0],C[2][1]),C[2][2],700)
print('thetas match',np.allclose(bm2['thetas'],bm['thetas']), 'R',bm2['R'])
B=G['buildings']()[0]
print(B['R'],len(B['thetas']),np.allclose(B['thetas'],bm['thetas']))
P=B['prof']
e,ok=plate(G['world'],B,B['thetas'][0],P['beam'],P['holes'],G['COL_T']/2,G['BEAM_T'],G['GIRDER_W']+20,G['GIRDER_H']+20)
print('beam ok',ok,e.IsValid)
c=P['cols'][0]; e2,ok2=plate(G['world'],B,B['thetas'][0],c['segs'],[h for h in P['holes'] if abs(h[0]-c['u'])<1],-90,180,220,420)
print('col',ok2,e2.IsValid)
g=girder_arc(G['CENTER'],B['R']+P['holes'][0][0],P['holes'][0][1],B['thetas'][0]-0.003,B['thetas'][-1]+0.003,200,400)
print('girder',g is not None and g.IsValid)
m=r3.File3dm(); m.Settings.ModelUnitSystem=r3.UnitSystem.Millimeters
m.Objects.AddExtrusion(e); m.Objects.AddExtrusion(e2); m.Objects.AddBrep(g)
m.Write('/tmp/claude-0/t/exact/t.3dm',8); print('ok')
bb=e.GetBoundingBox(); print('beam bbox',bb.Min,bb.Max)
print('expected east col', G['world'](B,B['thetas'][0],0,0,0), 'west', G['world'](B,B['thetas'][0],12000,0,0), 'eave tip', G['world'](B,B['thetas'][0],-3000,0,0))
gb=g.GetBoundingBox(); print('girder bbox',gb.Min,gb.Max)
print('girder ends',G['world'](B,B['thetas'][0],0,0,0)[:2],G['world'](B,B['thetas'][-1],0,0,0)[:2])
