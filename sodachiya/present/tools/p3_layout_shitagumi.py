# 3枚目（平面図）の下組み：高野川を下辺に敷地全体1/100、2階は西の道路の外に同じ向きで（10-25、プレゼンの準備）。更新係への見本
import sys,os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0,'.')
src=open('mock.py').read(); src=src[:src.index('# ================================================================ 2　景観')]
g={'__file__':os.path.abspath('mock.py'),'__name__':'m'}
exec(compile(src,'mock.py','exec'),g)
import numpy as np, matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from shapely.geometry import Polygon, LineString
from shapely import affinity
rot=g['rot']; R3=g['R3']; W,H=g['W'],g['H']
# 回した形にすりかえる
g['plan_items'][:]=[(ln,k,rot(gg)) for ln,k,gg in g['plan_items']]
for k in list(g['GD']):
    v=g['GD'][k]
    g['GD'][k]=[rot(x) for x in v] if isinstance(v,list) else rot(v)
g['roofs_plan']=rot(g['roofs_plan'])
_rp=g['roofs_plan'].buffer(0.3)
g['plan_items'][:]=[it for it in g['plan_items'] if g['room_color'](it[0]) or it[0].startswith(('17_','21_','24_','11a','22a','35_','16_','19_','27_','48_')) or it[0].startswith(('6','7')) or it[2].within(_rp)]
SC=g['SITE_C']; site=np.vstack([R3(v) for v in SC.values()]); o0=site.min(0)
fig,ax=g['page']()
MG=6
ox,oy=MG+64, MG+3                      # 敷地の南の角（左下）
xf=g['xform'](ox,oy,100,o0[0],o0[1])
ax.add_patch(Rectangle((MG,MG),W-2*MG,H-2*MG,fc='none',ec='#333',lw=0.4))
rp=g['clip_rect'](ax,MG,MG,W-2*MG,H-2*MG); st=len(ax.patches); sl=len(ax.lines)
A_=R3(SC['SW'])[0];B_=R3(SC['NW'])[0];t_=(B_-A_)/np.linalg.norm(B_-A_);n_=np.array([-t_[1],t_[0]])
if n_@(R3(SC['E'])[0]-A_)>0: n_=-n_
for ln in g['KMAP']['lines']:
    Q=R3(np.array(ln))
    if ((Q-A_)@n_).mean()>7.0: continue      # 2階を置く所（道の向かい）は消す
    q=xf(Q); ax.plot(q[:,0],q[:,1],color='#505050',lw=0.35)
g['draw_garden'](ax,xf)
g['draw_plan'](ax,ox,oy,100,o0[0],o0[1],640,575)
# 2階：西の道路の外へ、同じ向きで
A=R3(SC['SW'])[0];B=R3(SC['NW'])[0];t=(B-A)/np.linalg.norm(B-A);n=np.array([-t[1],t[0]])
if n@(R3(SC['E'])[0]-A)>0: n=-n
sh=n*22.0-t*11.0
C2={'41_':'#E9DFCF','42_':'#D9D3EC','43_':'#D9D3EC','43b':'#D5EBEE','44_':'#D9D3EC','45_':'#D9D3EC','36_':'#D9D3EC'}
_far=A+n*7.0
_hp=Polygon([_far-t*200,_far+t*200,_far+t*200+n*200,_far-t*200+n*200])
def put(gg,**kw):
    gg=affinity.translate(gg,*sh).intersection(_hp)
    if not gg.is_empty: g['draw_shape'](ax,gg,xf,**kw)
put(g['roofs_plan'],fc='#ECEAE6',ec='#8A847A',lw=0.25,z=0.9)
for o in g['objs']:
    ln=o['layer']
    if ln.startswith(('23_',)+tuple(C2)):
        sg=g['shape'](o,'plan')
        if sg is None: continue
        sg=rot(sg)
        put(sg,fc='#F4F1EA' if ln.startswith('23_') else C2[ln[:3]],ec='#333333' if ln.startswith('23_') else '#9A9A9A',lw=0.5 if ln.startswith('23_') else 0.12,z=1 if ln.startswith('23_') else 2)
q=xf(np.array([_far-t*40,_far+t*60])); ax.plot(q[:,0],q[:,1],color='#999999',lw=0.3,ls=(0,(3,2)))
for a in ax.patches[st:]: a.set_clip_path(rp)
for a in ax.lines[sl:]: a.set_clip_path(rp)
# 敷地の線（一点鎖線）
q=xf(site[[2,1,0,4,3,2]]) if False else None
P=np.vstack([R3(SC[k]) for k in ['S','E','N','NW','SW','S']]); q=xf(P)
ax.plot(q[:,0],q[:,1],color='#C03030',lw=0.4,ls=(0,(8,2,1,2)))
sx_=ox+630+8
g['T'](ax,sx_,H-MG-14,'こどもたちの育ち舎　3/5',4.5,bold=True)
g['T'](ax,sx_,H-MG-22,'平面図　1階・2階　1/100',4.0,bold=True)
g['T'](ax,sx_,H-MG-30,'2階は西の道路の外に同じ向きで',2.6)
fig.savefig('out/p3_layout_shitagumi.pdf')
print('2F shift',sh.round(1),'strip',W-MG-sx_)
