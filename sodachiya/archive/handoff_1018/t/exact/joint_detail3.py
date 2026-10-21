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
from exact import floor2_big
F2=floor2_big(G,Bk,Z2+1500)
uc=uW0+400                                   # 西館の東の柱芯
wood='#f3e3c8'; steel='#8e979d'; glass='#cfe8f3'
topM=lambda u: 3000+u/12.0                     # 本館の梁の天端
topW=lambda u: te+(tw-te)*(u-uc)/Dk            # 西館の梁の天端
RT=230                                         # 屋根の厚み（CLT90＋断熱100＋通気・金属板）
cf=uc-200                                      # 西館の柱の東の面
# 本館の越屋根（添付の断面に倣う）：東の束 10750–10900、内法 1100、西は本館の西の柱の列
MP1,MP0=10900,10750; MW=12200
capM=lambda u: 5150-(13080-u)/20.0             # キャップの天端（1/20 で東へ）
# 西館の越屋根：東の面 = 西館の東の縁（高窓の面）、内法 1100、西の束 14200–14350
WP0,WP1=14200,14350
capW=lambda u: 8750-(u-12000)/20.0             # キャップの天端（1/20 で西へ）
def sec(AX,detail=False):
    def poly(pts,fc='none',ec='k',lw=0.35,hatch=None,z=2):
        AX.add_patch(MP(list(pts),closed=True,fc=fc,ec=ec,lw=lw,hatch=hatch,zorder=z))
    def rect(u0,u1,z0,z1,**kw): poly([(u0,z0),(u1,z0),(u1,z1),(u0,z1)],**kw)
    # --- 本館の架構（実形）
    poly(seg_poly(P['beam']),fc=wood,hatch='////',z=4)
    poly(seg_poly(P['cols'][1]['segs']),fc=wood,hatch='\\\\\\\\',z=3)
    for hu,hz in P['holes']: AX.add_patch(EL((hu,hz),G['GIRDER_W'],G['GIRDER_H'],fc='#d8bf98',ec='k',lw=0.35,zorder=5))
    # 本館の屋根（越屋根の東の束まで）
    for (z0,z1,fc,h) in ((0,90,wood,'....'),(90,190,'#fff6c8','xxx'),(190,RT,'#dfe6ea',None)):
        poly([(8000,topM(8000)+z0),(MP0,topM(MP0)+z0),(MP0,topM(MP0)+z1),(8000,topM(8000)+z1)],fc=fc,hatch=h,lw=0.25,z=4)
    zr=topM(MP0)+RT
    rect(MP0,MP1,zr-RT,4600,fc=wood,hatch='////',lw=0.3,z=4)                       # 立ち上がり（防水 250 以上）
    rect(MP0-25,MP0,zr,4620,fc=steel,lw=0.2,z=5)                                    # 立ち上がりの水切り
    rect(MP0+40,MP0+110,4600,capM(MP0)-50,fc=wood,lw=0.3,z=4)                       # 束
    for zz in np.arange(4630,5050,75): AX.plot([MP0-10,MP1+10],[zz+40,zz],color='k',lw=0.5,zorder=6)   # 横ガラリ
    rect(MP1+15,MP1+30,4600,5050,fc=glass,lw=0.2,z=5)                               # ガラリの内側の開閉窓
    # 西の束（架構ごと、キャップを受ける）：本館の西の柱の上
    rect(12000-50,12000+50,topM(12000)-60,capM(12000)-50,fc=wood,hatch='////',lw=0.3,z=4)
    # キャップ：東の先端 9850 → 本館の西の壁の線 12200 は鋼板、そこから西館の壁まではガラス
    poly([(9850,capM(9850)-50),(MW,capM(MW)-50),(MW,capM(MW)),(9850,capM(9850))],fc=steel,lw=0.3,z=6)
    poly([(9850,capM(9850)-50),(9850,capM(9850)-160),(9870,capM(9850)-160),(9870,capM(9850)-50)],fc=steel,lw=0.2,z=6)  # 東の垂れ
    poly([(MW,capM(MW)-40),(cf-110,capM(cf-110)-40),(cf-110,capM(cf-110)),(MW,capM(MW))],fc=glass,lw=0.3,z=6)          # すき間の上はガラス
    # LED（キャップの下、東の束の頭）
    rect(MP0+60,MP0+110,capM(MP0)-95,capM(MP0)-55,fc='#f0b400',ec='none',z=7)
    for t in (0.35,0.6,0.85): AX.plot([MP0+85,MP0+85-t*900],[capM(MP0)-95,capM(MP0)-95-t*500],color='#f0b400',lw=0.5,alpha=0.6,zorder=1)
    # --- 西館の架構（実形）
    W2M=lambda pts:[(uc+u,z) for u,z in pts]
    poly(W2M(seg_poly(Pk['beam'])),fc=wood,hatch='////',z=4)
    poly(W2M(seg_poly(F2['beam'])),fc=wood,hatch='////',z=4)
    poly(W2M(seg_poly(F2['cols'][0]['segs'])),fc=wood,hatch='\\\\\\\\',z=3)
    for hu,hz in list(Pk['holes'])+list(F2['holes']):
        if hu<3000: AX.add_patch(EL((uc+hu,hz),G['GIRDER_W'],G['GIRDER_H'],fc='#d8bf98',ec='k',lw=0.35,zorder=5))
    # 西館の屋根（越屋根の西の束から西へ）
    for (z0,z1,fc,h) in ((0,90,wood,'....'),(90,190,'#fff6c8','xxx'),(190,RT,'#dfe6ea',None)):
        poly([(WP1,topW(WP1)+z0),(17500,topW(17500)+z0),(17500,topW(17500)+z1),(WP1,topW(WP1)+z1)],fc=fc,hatch=h,lw=0.25,z=4)
    zw=topW(WP1)+RT
    rect(WP0,WP1,zw-RT,zw+250,fc=wood,hatch='////',lw=0.3,z=4)                      # 立ち上がり
    rect(WP1,WP1+25,zw,zw+270,fc=steel,lw=0.2,z=5)
    zl0=zw+250; zl1=zl0+450
    rect(WP0+40,WP0+110,zl0,capW(WP0)-50,fc=wood,lw=0.3,z=4)                         # 西の束
    for zz in np.arange(zl0+30,zl1,75): AX.plot([WP0-10,WP1+10],[zz,zz+40],color='k',lw=0.5,zorder=6)
    # 東の面：受け材 → 高窓 → ガラリ（同じ面）
    rect(cf-140,cf,capM(cf)+40,capM(cf)+280,fc=wood,hatch='////',lw=0.3,z=4)          # 受け材（柱に留める）
    zg0=capM(cf)+300
    rect(cf-70,cf,capM(cf)+280,zg0,fc=steel,lw=0.2,z=5)                               # 下枠
    rect(cf-52,cf-28,zg0,zl0,fc=glass,lw=0.3,z=4)                                     # 高窓
    rect(cf-70,cf,zl0-40,zl0,fc=steel,lw=0.2,z=5)
    for zz in np.arange(zl0+30,zl1,75): AX.plot([cf-80,cf+10],[zz,zz+40],color='k',lw=0.5,zorder=6)
    rect(cf-60,cf+10,zl1,capW(cf)-50,fc=wood,lw=0.3,z=4)                             # 東の束
    # 雨押え（西館に固定、本館のキャップのガラスの上を滑る）
    poly([(cf-152,capM(cf)+260),(cf-140,capM(cf)+260),(cf-140,capM(cf)+70),(cf-330,capM(cf-330)+30),(cf-330,capM(cf-330)+18),(cf-152,capM(cf)+56)],fc='#555',lw=0.2,z=7)
    # 西館のキャップ：東の先端 12000 → 西の先端 15250、1/20 で西へ
    poly([(12000,capW(12000)-50),(15250,capW(15250)-50),(15250,capW(15250)),(12000,capW(12000))],fc=steel,lw=0.3,z=6)
    for uu in (12000,15250): rect(uu-10 if uu>13000 else uu,uu+10 if uu>13000 else uu+20,capW(uu)-160,capW(uu)-50,fc=steel,lw=0.2,z=6)
    rect(WP0+60,WP0+110,capW(WP0)-95,capW(WP0)-55,fc='#f0b400',ec='none',z=7)
    rect(cf-40,cf+10,capW(cf)-95,capW(cf)-55,fc='#f0b400',ec='none',z=7)
    for t in (0.35,0.6,0.85):
        AX.plot([WP0+85,WP0+85+t*700],[capW(WP0)-95,capW(WP0)-95-t*500],color='#f0b400',lw=0.5,alpha=0.6,zorder=1)
        AX.plot([cf-15,cf-15-t*700],[capW(cf)-95,capW(cf)-95-t*500],color='#f0b400',lw=0.5,alpha=0.6,zorder=1)
    # 2 階の床（吹抜は d 0–1000）と手すり
    rect(uW0+1000,17500,Z2-80,Z2,fc=wood,hatch='....',lw=0.3,z=4)
    rect(uW0+1000,uW0+1050,Z2,Z2+1100,fc=steel,lw=0.2,z=4)
    # 床・基礎
    for (u0,u1) in ((8000,12650),(12750,17500)): rect(u0,u1,-150,0,fc='#e6e6e6',hatch='..',lw=0.3,z=2)
    for (u0,u1) in ((11600,12450),(12950,13700)): rect(u0,u1,-850,-150,fc='#e6e6e6',hatch='..',lw=0.3,z=2)
    rect(12500,12900,0,12,fc=steel,lw=0.25,z=6)
    AX.plot([8000,17500],[0,0],color='k',lw=0.5,zorder=1)
    return dict(zr=zr,zw=zw,zl0=zl0,zl1=zl1,zg0=zg0)
# ================= ページ 1：断面 1/40 と拡大 1/10 =================
SC=40.0; X0,X1=9300,16900; Y0,Y1=-900,9200
ax=axes_mm(15,18,(X1-X0)/SC,(Y1-Y0)/SC,(X0,X1),(Y0,Y1))
H=sec(ax)
def lab(x,y,t,tx,ty,ha='left',fs=6.0,AX=None):
    (AX or ax).annotate(t,xy=(x,y),xytext=(tx,ty),fontsize=fs,ha=ha,va='center',arrowprops=dict(arrowstyle='-',lw=0.25,shrinkA=0,shrinkB=0),zorder=10,annotation_clip=False)
for u in (12000,uc): ax.plot([u,u],[-850,9150],color='#aaa',lw=0.15,ls=(0,(8,3,1,3)),zorder=0)
ax.text(12000,9150,'本館 西の柱芯',ha='center',fontsize=5.5,color='#666'); ax.text(uc,9150,'西館 東の柱芯',ha='center',fontsize=5.5,color='#666')
lab(12400,capW(12400)-30,'西館の越屋根のキャップ（鋼板、1/20 で西へ）\n東へ 900 出て、本館の越屋根の上にかかる',9400,8500)
lab(WP0+80,H['zl0']+200,'西館の越屋根のガラリ（両面）',15200,7700)
lab(WP0+85,capW(WP0)-75,'LED（キャップの下）',15900,8950)
lab(cf-40,(H['zg0']+H['zl0'])/2,'高窓（東向き）',13950,6900)
lab(10500,capM(10500)-25,'本館の越屋根もどきのキャップ\n（鋼板、1/20 で東へ）',9400,6300)
lab(12650,capM(12650)-20,'すき間の上はガラス',9400,5800)
lab(MP0+10,4800,'東のガラリ＋内側の開閉窓\n（冬は閉める）',9400,5200)
lab(12000,4400,'束（架構ごと、キャップを受ける）',9400,2750)
lab(cf-150,capM(cf)+150,'雨押え（西館に固定、滑らせる）',14100,5600)
lab(10000,topM(10000)+150,'本館の屋根（東へ 1/12）',9400,2350)
lab(uW0+1025,Z2+800,'2階ホールの手すり（d 0–1.0 m は換気の吹抜）',14000,4200)
lab(uc+300,Z2-550,'2階の床梁（Tamedia 型、桁を包む楕円＝肉球）',14400,2300)
lab(12000,1500,'本館の柱・梁（Tamedia 型）',9400,1700)
lab(12700,6,'床のエキスパンションカバー',10300,-550,ha='center')
lab(13300,-500,'基礎は別々',14600,-500)
ax.text(10600,600,'西廊下',fontsize=7,ha='center'); ax.text(14600,600,'土間（はだし）',fontsize=7,ha='center')
def hdim(u0,u1,z,t):
    ax.annotate('',xy=(u0,z),xytext=(u1,z),arrowprops=dict(arrowstyle='<->',lw=0.25,shrinkA=0,shrinkB=0)); ax.text((u0+u1)/2,z+60,t,ha='center',fontsize=5.3)
hdim(12200,cf,1100,'柱のあき %d'%int(round(cf-12200,-1)))
hdim(MP1,12000,capM(12000)+250,'1,100'); hdim(13100,WP0,capW(WP0)+250,'1,100')
for zz,t in ((capM(13080),'%.2f'%(capM(13080)/1000)),(capW(12000),'%.2f'%(capW(12000)/1000)),(Z2,'2階床 %.2f'%(Z2/1000))):
    ax.plot([16500,16800],[zz,zz],color='k',lw=0.25); ax.text(16820,zz,t,fontsize=5.5,va='center')
fig.text(15/FW,(18+(Y1-Y0)/SC+5)/FH,'A　本館と西館の取り合い（越屋根を含む）　断面詳細（架構 9 の面）　1/40',fontsize=10)
# --- 拡大 1/10：二つの越屋根のキャップと、すき間
ZX0,ZX1,ZY0,ZY1=11700,13500,4350,6150
ax2=axes_mm(232,95,(ZX1-ZX0)/10,(ZY1-ZY0)/10,(ZX0,ZX1),(ZY0,ZY1))
sec(ax2); ax2.add_patch(RC((ZX0,ZY0),ZX1-ZX0,ZY1-ZY0,fc='none',ec='k',lw=0.4,clip_on=False))
lab(12100,capM(12100)-25,'キャップ（鋼板 t2.3、見付 50）',11750,6050,AX=ax2,fs=6.8)
lab(12500,capM(12500)-20,'すき間の上はガラス（キャップと一体の枠）',11750,5900,AX=ax2,fs=6.8)
lab(cf-200,capM(cf-200)+40,'雨押え：西館に固定、キャップの上を滑らせる\n（地震・温度の動きを逃がす）',12350,5700,AX=ax2,fs=6.8)
lab(cf-70,capM(cf)+150,'受け材（西館の柱に留める）',12750,5450,AX=ax2,fs=6.8)
lab(cf-40,H['zg0']+150,'高窓の下枠',12950,6000,AX=ax2,fs=6.8)
lab(12000,4700,'束（本館の西の柱の上）',11750,4500,AX=ax2,fs=6.8)
ax2.annotate('',xy=(12200,4420),xytext=(cf,4420),arrowprops=dict(arrowstyle='<->',lw=0.3,shrinkA=0,shrinkB=0)); ax2.text((12200+cf)/2,4450,'柱のあき %d'%int(round(cf-12200,-1)),ha='center',fontsize=6.5)
fig.text(232/FW,(95+(ZY1-ZY0)/10+5)/FH,"A'　キャップがすき間をまたぐところ　1/10",fontsize=10)
fig.text(232/FW,20/FH,'・本館の越屋根は、西館と接する区間では西のガラリをやめ、キャップを西館の壁まで延ばして\n　すき間の屋根を兼ねる（すき間の上はガラス）。外から見る越屋根の形は端から端まで続く。\n・西館の越屋根は屋根の頂点（東の縁）、換気の吹抜の真上。キャップは東へ 900 出て本館の越屋根に重なる。\n・水はどちらのキャップも外へ流れ（本館は東、西館は西）、すき間には落ちない。\n・LED はキャップの下。夜は低く長い線（本館）と高く短い線（西館）の二段の光になる。\n・西館の 2 階床梁（せい 800）は、桁を包む木を厚く（280）して、楕円が梁の下に出るようにした。',fontsize=6.3,va='bottom')
from matplotlib.backends.backend_pdf import PdfPages
PDF=PdfPages('/home/claude/plans/rhino/joint_detail.pdf'); PDF.savefig(fig); fig.savefig('/tmp/claude-0/t/exact/j3_p1.png',dpi=110)
fig=plt.figure(figsize=(FW*MM,FH*MM))
# ---------------- 平面（南端） ----------------
# 直線で近似した局所座標：x = u（本館の東の柱芯から放射方向）、y = 架構 12 の線からの弧の方向（南が負）
pitch=lambda u: 3000*(bm['R']+u)/(bm['R']+12000)
ks_=lambda kk_,u: -(kk_-12)*pitch(u)        # 北（k が小さい）を +y
SC2=50.0; PX0,PX1=7600,18600; PY0,PY1=-5200,4600
ax=axes_mm(40,40,(PX1-PX0)/SC2,(PY1-PY0)/SC2,(PX0,PX1),(PY0,PY1))
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
poly2([(10400-60,120),(10400+60,120),(10400+60,ks_(11,10400)-180),(10400-60,ks_(11,10400)-180)],fc='#bbb',ec='k',lw=0.3,zorder=3)   # 事務と西廊下の境
ax.text(9800,-1350,'海峡の床は室内より 150 低い（上がり框）',fontsize=6,ha='center',color='#555')
# 部屋の名前
ax.text(9300,2400,'事務',fontsize=8,ha='center'); ax.text(10400,-3300,'医務',fontsize=8,ha='center')
ax.text(11200,4000,'西廊下',fontsize=6.5,ha='center',rotation=0); ax.text(15400,2800,'食べる場所（はだし）',fontsize=7,ha='center')
ax.text(15400,-750,'海峡（土足、幅 1.5 m）→ 駐車場へ',fontsize=7,ha='center',va='center')
ax.text(10000,-750,'← 園庭へ',fontsize=6.5,ha='center',va='center')
def lab2(x,y,t,tx,ty,ha='left'):
    ax.annotate(t,xy=(x,y),xytext=(tx,ty),fontsize=6.2,ha=ha,va='center',arrowprops=dict(arrowstyle='-',lw=0.25,shrinkA=0,shrinkB=0),zorder=10)
lab2(12560,100,'すき間のふさぎ\n（西館の南の壁の延長）',13700,-3000)
lab2(12215,100,'エキスパンションのシール',11000,-4300,ha='center')
lab2(12700,3200,'床のカバー（はだしで渡る）',14600,4100)
lab2(12600,2000,'上は越屋根のキャップ（ガラス、断面 A）',14600,1300)
lab2(10300,60,'事務の窓（海峡を見守る）',9000,1200,ha='center')
lab2(uW+400,190,'西館の角は直角\n（丸めない）',16800,-3000,ha='center')
for kk_ in (11,12,13):
    y=ks_(kk_,PX0+300); ax.plot([PX0,PX1],[ks_(kk_,PX0),ks_(kk_,PX1)],color='#aaa',lw=0.15,ls=(0,(8,3,1,3)),zorder=0)
    ax.text(PX0-150,ks_(kk_,PX0),'架構 %d'%kk_,fontsize=5.5,ha='right',va='center',color='#666')
ax.plot([12000,12000],[PY0,PY1],color='#aaa',lw=0.15,ls=(0,(8,3,1,3)))
fig.text(40/FW,(40+(PY1-PY0)/SC2+6)/FH,'B　南端の取り合い　平面詳細　1/50',fontsize=10)
fig.text(40/FW,22/FH,'・円弧は短い区間なので直線で近似して描いている（3 m で 5 mm のずれ）。\n・海峡の 1.5 m を医務と事務のどちらから取るかは未定。図では医務の側から取っている。\n・北端の取り合いも同じ考え方（西館の北の妻の壁を架構 2 の線にそろえ、すき間をふさぐ）。',fontsize=6.5,va='bottom')
PDF.savefig(fig); PDF.close(); fig.savefig('/tmp/claude-0/t/exact/joint_p2.png',dpi=110)
print('uW0',uW0,'L',L)
