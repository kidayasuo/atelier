exec(open('/tmp/claude-0/t/ideas/case3.py').read().split('# ---------- rooms')[0].replace("print(","(lambda *a:None)("))
import sys; sys.path.insert(0,'/tmp/claude-0/t/exact'); from exact import seg_poly
import pickle; WN=pickle.load(open('/tmp/claude-0/t/exact/wnew.pkl','rb'))['WN']
import matplotlib; matplotlib.use('Agg'); matplotlib.rcParams['pdf.fonttype']=42
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP, Rectangle as RC, Ellipse as EL
plt.rcParams['font.family']='IPAGothic'; plt.rcParams['hatch.linewidth']=0.25
MM=1/25.4; FW,FH=420,297
fig=plt.figure(figsize=(FW*MM,FH*MM))
def axes_mm(x,y,w,h,xlim,ylim):
    ax=fig.add_axes([x/FW,y/FH,w/FW,h/FH]); ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.set_aspect('equal'); ax.axis('off'); return ax
Cc_=np.array(G['CENTER'])
# ---------------- 断面 ----------------
k=9
Lx=SL([tuple(at(k,-5000)),tuple(at(k,60000))]).intersection(WN); a=np.array(Lx.coords[0]); b=np.array(Lx.coords[-1])
if np.linalg.norm(a-Cc_)>np.linalg.norm(b-Cc_): a,b=b,a
L=np.linalg.norm(b-a); uW0=np.linalg.norm(a-Cc_)-bm['R']     # 西館の東の縁（本館の u）
B=G['buildings']()[0]; P=B['prof']
Dk=L-800; te=zroof(k,400,L); tw=zroof(k,L-400,L)
Bk=dict(R=1,D=Dk,EAVE=0.0); Pk=G['frame_profiles'](Bk,te,tw,700.0,0.0,250.0); Bk.update(prof=Pk,TOP_E=te,TOP_W=tw,FLOOR2_TOP=Z2-50,FLOOR2_DEPTH=HB2)
F2=G['floor2_profile_tamedia'](Bk)
uc=uW0+400                                   # 西館の東の柱芯
SC=40.0; X0,X1=9300,16700; Y0,Y1=-900,9000
ax=axes_mm(18,22,(X1-X0)/SC,(Y1-Y0)/SC,(X0,X1),(Y0,Y1))
LW=0.35; TH=0.18
def poly(pts,fc='none',ec='k',lw=LW,hatch=None,z=2,alpha=1):
    ax.add_patch(MP(list(pts),closed=True,fc=fc,ec=ec,lw=lw,hatch=hatch,zorder=z,alpha=alpha))
def line(p,q,lw=TH,c='k',ls='-',z=3): ax.plot([p[0],q[0]],[p[1],q[1]],color=c,lw=lw,ls=ls,zorder=z,solid_capstyle='butt')
def lab(x,y,t,tx,ty,ha='left',fs=6.2):
    ax.annotate(t,xy=(x,y),xytext=(tx,ty),fontsize=fs,ha=ha,va='center',arrowprops=dict(arrowstyle='-',lw=0.25,color='k',shrinkA=0,shrinkB=0),zorder=10)
# 本館：梁・柱（切断、実形）
wood='#f3e3c8'
poly([(u,z) for u,z in seg_poly(P['beam'])],fc=wood,hatch='////',z=4)
poly([(u,z) for u,z in seg_poly(P['cols'][1]['segs'])],fc=wood,hatch='\\\\\\\\',z=3)
for hu,hz in P['holes']: ax.add_patch(EL((hu,hz),G['GIRDER_W'],G['GIRDER_H'],fc='#d8bf98',ec='k',lw=LW,zorder=5))
topM=lambda u: 3000+u/12.0
# 本館の屋根：CLT 90 ＋ 断熱 100 ＋ 通気・金属板 40
uE=12330
for (z0,z1,fc,h) in ((0,90,wood,'....'),(90,190,'#fff6c8','xxx'),(190,230,'#dfe6ea',None)):
    poly([(X0,topM(X0)+z0),(uE,topM(uE)+z0),(uE,topM(uE)+z1),(X0,topM(X0)+z1)],fc=fc,hatch=h,lw=0.25,z=4)
# 立ち上がり＋笠木（本館側）
zr=topM(uE)+230
poly([(uE-120,topM(uE-120)+230),(uE,zr),(uE,zr+260),(uE-120,zr+260)],fc=wood,hatch='////',lw=0.3,z=4)
poly([(uE-150,zr+260),(uE+40,zr+260),(uE+40,zr+200),(uE+20,zr+200),(uE+20,zr+275),(uE-150,zr+275)],fc='#9aa4ab',lw=0.25,z=5)
# 西館：梁・柱・2 階床梁（切断、実形）
W2M=lambda pts:[(uc+u,z) for u,z in pts]
poly(W2M(seg_poly(Pk['beam'])),fc=wood,hatch='////',z=4)
poly(W2M(seg_poly(F2['beam'])),fc=wood,hatch='////',z=4)
poly(W2M(seg_poly(F2['cols'][0]['segs'])),fc=wood,hatch='\\\\\\\\',z=3)
for hu,hz in list(Pk['holes'])+list(F2['holes']):
    if hu<3000: ax.add_patch(EL((uc+hu,hz),G['GIRDER_W'],G['GIRDER_H'],fc='#d8bf98',ec='k',lw=LW,zorder=5))
topW=lambda u: te+(tw-te)*(u-uc)/Dk
wE=uW0-250
for (z0,z1,fc,h) in ((0,90,wood,'....'),(90,190,'#fff6c8','xxx'),(190,230,'#dfe6ea',None)):
    poly([(wE,topW(wE)+z0),(X1,topW(X1)+z0),(X1,topW(X1)+z1),(wE,topW(wE)+z1)],fc=fc,hatch=h,lw=0.25,z=4)
poly([(wE-40,topW(wE)-60),(wE,topW(wE)-60),(wE,topW(wE)+250),(wE-40,topW(wE)+250)],fc='#9aa4ab',lw=0.25,z=5)   # 鼻隠し
# 西館の東の面：高窓（ガラス）と下の壁
gx=uW0+80
zg0=zr+520; zg1=topW(gx)-120
poly([(gx-60,zr+330),(gx+60,zr+330),(gx+60,zg0),(gx-60,zg0)],fc=wood,hatch='////',lw=0.3,z=4)        # 腰（天窓の受け）
poly([(gx-15,zg0),(gx+15,zg0),(gx+15,zg1),(gx-15,zg1)],fc='#cfe8f3',lw=0.3,z=4)                         # 高窓
for zz in (zg0,(zg0+zg1)/2,zg1): poly([(gx-45,zz-30),(gx+45,zz-30),(gx+45,zz+30),(gx-45,zz+30)],fc='#9aa4ab',lw=0.2,z=5)
# 天窓（すき間の上）：本館の立ち上がり → 西館の腰、本館側に固定、西館側は雨押えで滑らせる
s0=(uE+20,zr+275); s1=(gx-60,zr+330+40)
poly([(s0[0],s0[1]),(s1[0],s1[1]),(s1[0],s1[1]+30),(s0[0],s0[1]+30)],fc='#cfe8f3',lw=0.3,z=6)
poly([(gx-60,zr+330+40+30),(gx+60,zr+330+40+30),(gx+60,zr+500),(gx-210,zr+430),(gx-210,zr+410),(gx-60,zr+470)],fc='#9aa4ab',lw=0.25,z=6)  # 雨押え
# 床・基礎（別々の基礎、床にエキスパンションのカバー）
for (u0,u1) in ((X0,12650),(12750,X1)):
    poly([(u0,-150),(u1,-150),(u1,0),(u0,0)],fc='#e6e6e6',hatch='..',lw=0.3,z=2)
for (u0,u1) in ((11600,12450),(12950,13700)):
    poly([(u0,-850),(u1,-850),(u1,-150),(u0,-150)],fc='#e6e6e6',hatch='..',lw=0.3,z=2)
poly([(12500,0),(12900,0),(12900,12),(12500,12)],fc='#9aa4ab',lw=0.25,z=6)       # 床のカバー
line((X0,-850),(X1,-850),lw=0.15,c='#888',ls='--')
ax.plot([X0,X1],[0,0],color='k',lw=0.5,zorder=1)
# 2 階の床（吹抜は d 0–1000）
poly([(uW0+1000,Z2-80),(X1,Z2-80),(X1,Z2),(uW0+1000,Z2)],fc=wood,hatch='....',lw=0.3,z=4)
poly([(uW0+1000,Z2),(uW0+1050,Z2),(uW0+1050,Z2+1100),(uW0+1000,Z2+1100)],fc='#9aa4ab',lw=0.2,z=4)     # 手すり
# 寸法
def dim_h(u0,u1,z,txt):
    ax.annotate('',xy=(u0,z),xytext=(u1,z),arrowprops=dict(arrowstyle='<->',lw=0.25,shrinkA=0,shrinkB=0)); ax.text((u0+u1)/2,z+60,txt,ha='center',fontsize=5.5)
def dim_v(u,z0,z1,txt,side=1):
    ax.annotate('',xy=(u,z0),xytext=(u,z1),arrowprops=dict(arrowstyle='<->',lw=0.25,shrinkA=0,shrinkB=0)); ax.text(u+side*80,(z0+z1)/2,txt,ha='left' if side>0 else 'right',va='center',fontsize=5.5,rotation=90)
dim_h(12000,uc,-500,'%d'%(uc-12000)); dim_h(12200,uc-200,1100,'柱のあき %d'%(uc-200-12200))
dim_v(X0+250,0,topM(X0+250)+230,'%.2f m'%((topM(X0+250)+230)/1000),side=1)
dim_v(X1-250,0,topW(X1-250)+230,'%.2f m'%((topW(X1-250)+230)/1000),side=-1)
dim_v(uW0+1600,0,Z2,'2階床 %.2f m'%(Z2/1000),side=1)
for u in (12000,uc): line((u,-800),(u,9000),lw=0.15,c='#aaa',ls=(0,(8,3,1,3)),z=0)
ax.text(12000,8850,'本館 西の柱芯',ha='center',fontsize=5.5,color='#666'); ax.text(uc,8850,'西館 東の柱芯',ha='center',fontsize=5.5,color='#666')
# 注記
lab(uE-60,zr+130,'立ち上がり＋笠木（本館の屋根の西の縁）',10300,6200,ha='center')
lab((s0[0]+s1[0])/2,(s0[1]+s1[1])/2+15,'天窓（本館側に固定）\n水は本館の屋根へ流す',11000,7000,ha='center')
lab(gx-120,zr+460,'雨押え（西館側に固定、\n天窓の上を滑る＝エキスパンション）',13900,6650)
lab(gx,(zg0+zg1)/2,'高窓（東向き）\n上部は換気用の開き窓',14600,5600)
lab(wE-20,topW(wE)+100,'鼻隠し（西館の屋根の東の縁、\n水は西へ流れるので樋なし）',13900,8550)
lab(10400,topM(10400)+150,'本館の屋根\nCLT 90＋断熱 100＋通気・金属板\n（東へ 1/12 で下がる）',9900,5000,ha='left')
lab(12700,6,'床のエキスパンションカバー',11800,-420,ha='center')
lab(13300,-500,'基礎は別々',14600,-420)
lab(uW0+1025,Z2+800,'2階ホールの手すり\n（d 0–1.0 m は換気の吹抜）',15200,4500)
lab(12000,1800,'本館の柱・梁（Tamedia 型の実形）',10200,2600,ha='center')
lab(uc+200,2000,'西館の柱・2階床梁（実形）',14800,1700)
ax.text(10600,700,'西廊下',fontsize=7,ha='center'); ax.text(14300,700,'土間（はだし）',fontsize=7,ha='center')
fig.text(18/FW,(22+(Y1-Y0)/SC+6)/FH,'A　本館と西館の取り合い　断面詳細（架構 9 の面）　1/40',fontsize=10)
# ---------------- 平面（南端） ----------------
# 直線で近似した局所座標：x = u（本館の東の柱芯から放射方向）、y = 架構 12 の線からの弧の方向（南が負）
pitch=lambda u: 3000*(bm['R']+u)/(bm['R']+12000)
ks_=lambda kk_,u: -(kk_-12)*pitch(u)        # 北（k が小さい）を +y
SC2=50.0; PX0,PX1=7600,18600; PY0,PY1=-5200,4600
ax=axes_mm(232,40,(PX1-PX0)/SC2,(PY1-PY0)/SC2,(PX0,PX1),(PY0,PY1))
def poly2(pts,**kw): ax.add_patch(MP(list(pts),closed=True,**kw))
SH=1500.0
# 海峡（土足）：架構 12 の線から南へ 1.5 m、本館を横切って駐車場へ
poly2([(PX0,0),(PX1,0),(PX1,-SH),(PX0,-SH)],fc='#ece5d6',ec='none',zorder=0)
for x in np.arange(PX0,PX1,450): ax.plot([x,x+300],[-SH+100,-100],color='#c9bda5',lw=0.2,zorder=0)
# 本館の柱（架構 11,12,13 の西の柱と、教室側の柱）
for kk_ in (11,12,13):
    y=ks_(kk_,12000); poly2([(11800,y-90),(12200,y-90),(12200,y+90),(11800,y+90)],fc=wood,ec='k',lw=0.4,hatch='\\\\\\\\',zorder=3)
    for s in (-1,1): poly2([(9000,y+s*90),(12280,y+s*90),(12280,y+s*180),(9000,y+s*180)],fc='none',ec='#999',lw=0.2,ls='--',zorder=2)
# 本館の壁：事務の南の壁（海峡の北）、医務の北の壁（海峡の南）、本館の西の外壁（架構 12 より南）
poly2([(PX0,0),(12000-200,0),(12000-200,120),(PX0,120)],fc='#bbb',ec='k',lw=0.3,zorder=3)
poly2([(PX0,-SH),(12000-200,-SH),(12000-200,-SH-120),(PX0,-SH-120)],fc='#bbb',ec='k',lw=0.3,zorder=3)
y13=ks_(13,12000)
poly2([(12080,-SH-120),(12200,-SH-120),(12200,y13-90),(12080,y13-90)],fc='#bbb',ec='k',lw=0.3,zorder=3)
ax.plot([12200,12200],[0,-SH],color='k',lw=0.3,ls=(0,(1,1.5)),zorder=3)   # 海峡の西の口（開口）
# 事務の窓（海峡を見る）
poly2([(9300,30),(11300,30),(11300,90),(9300,90)],fc='#cfe8f3',ec='k',lw=0.2,zorder=4)
# 西館：東の縁 uW0=12900、南の壁＝架構 12 の線（直角の角）
uW=12200+700
poly2([(uW,0),(PX1,0),(PX1,200),(uW,200)],fc='#bbb',ec='k',lw=0.3,zorder=3)                 # 西館の南の壁
# 西館の東の柱（d=400）と南の妻の柱
for yy in (0+100,):
    poly2([(uW+200,yy),(uW+600,yy),(uW+600,yy+180),(uW+200,yy+180)],fc=wood,ec='k',lw=0.4,hatch='\\\\\\\\',zorder=4)
y11=ks_(11,uW+400)
poly2([(uW+200,y11-90),(uW+600,y11-90),(uW+600,y11+90),(uW+200,y11+90)],fc=wood,ec='k',lw=0.4,hatch='\\\\\\\\',zorder=4)
# すき間のふさぎ：西館の南の壁を本館の柱まで延ばす（本館側はエキスパンションのシール）
poly2([(12230,0),(uW,0),(uW,200),(12230,200)],fc='#d9d9d9',ec='k',lw=0.3,hatch='xx',zorder=3)
poly2([(12200,20),(12230,20),(12230,180),(12200,180)],fc='#333',ec='none',zorder=5)
# 床のエキスパンションカバー（北側、すき間の上）
poly2([(12500,200),(12900,200),(12900,4600),(12500,4600)],fc='#dfe3e6',ec='#777',lw=0.2,zorder=1)
# 天窓の範囲（すき間の上、破線）
poly2([(12330,200),(uW,200),(uW,4600),(12330,4600)],fc='none',ec='#4a90b8',lw=0.4,ls='--',zorder=2)
# 部屋の名前
ax.text(10400,2400,'事務',fontsize=8,ha='center'); ax.text(10400,-3300,'医務',fontsize=8,ha='center')
ax.text(11200,4000,'西廊下',fontsize=6.5,ha='center',rotation=0); ax.text(15400,2800,'食べる場所（はだし）',fontsize=7,ha='center')
ax.text(15400,-750,'海峡（土足、幅 1.5 m）→ 駐車場へ',fontsize=7,ha='center',va='center')
ax.text(10000,-750,'← 園庭へ',fontsize=6.5,ha='center',va='center')
def lab2(x,y,t,tx,ty,ha='left'):
    ax.annotate(t,xy=(x,y),xytext=(tx,ty),fontsize=6.2,ha=ha,va='center',arrowprops=dict(arrowstyle='-',lw=0.25,shrinkA=0,shrinkB=0),zorder=10)
lab2(12560,100,'すき間のふさぎ\n（西館の南の壁の延長）',13700,-3000)
lab2(12215,100,'エキスパンションのシール',11000,-4300,ha='center')
lab2(12700,3200,'床のカバー（はだしで渡る）',14600,4100)
lab2(12600,2000,'上は天窓（断面 A）',14600,1300)
lab2(10300,60,'事務の窓（海峡を見守る）',9000,1200,ha='center')
lab2(uW+400,190,'西館の角は直角\n（丸めない）',16800,-3000,ha='center')
for kk_ in (11,12,13):
    y=ks_(kk_,PX0+300); ax.plot([PX0,PX1],[ks_(kk_,PX0),ks_(kk_,PX1)],color='#aaa',lw=0.15,ls=(0,(8,3,1,3)),zorder=0)
    ax.text(PX0-150,ks_(kk_,PX0),'架構 %d'%kk_,fontsize=5.5,ha='right',va='center',color='#666')
ax.plot([12000,12000],[PY0,PY1],color='#aaa',lw=0.15,ls=(0,(8,3,1,3)))
fig.text(232/FW,(40+(PY1-PY0)/SC2+6)/FH,'B　南端の取り合い　平面詳細　1/50',fontsize=10)
fig.text(232/FW,22/FH,'・円弧は短い区間なので直線で近似して描いている（3 m で 5 mm のずれ）。\n・海峡の 1.5 m を医務と事務のどちらから取るかは未定。図では医務の側から取っている。\n・北端の取り合いも同じ考え方（西館の北の妻の壁を架構 2 の線にそろえ、すき間をふさぐ）。',fontsize=6.5,va='bottom')
fig.savefig('/home/claude/plans/rhino/joint_detail.pdf'); fig.savefig('/tmp/claude-0/t/exact/joint_detail.png',dpi=110)
print('uW0',uW0,'L',L)
