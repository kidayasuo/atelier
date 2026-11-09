exec(open('/tmp/claude-0/t/exact/exact_model.py').read())
PREVL=PREV
_W=W
exec(open('/tmp/claude-0/t/ideas/check_c3.py').read().split("allF=load2")[0])
allF=load2(OUT)
wood={'11a_本館_柱':(0.52,0.37,0.22),'11b_本館_梁':(0.60,0.44,0.27),'11c_本館_桁':(0.45,0.32,0.19),'22a_西館_柱':(0.52,0.37,0.22),'22b_西館_梁':(0.60,0.44,0.27),'22c_西館_2階床梁':(0.66,0.50,0.32),'22d_西館_桁':(0.45,0.32,0.19)}
FR_=[(p,wood[l],l) for p,l in PREVL]
fig,axs=plt.subplots(2,2,figsize=(16,10))
hide={'20_西館_屋根','10_本館_屋根','21_西館_外壁','24_西館_間仕切り','23_西館_2階床','35_機械室（本館の北）','26_室外機置場'}
rooms=lambda n: n[:2] in ('31','32','33','34','36')
globals()['faces']=[(p,c) for p,c,n in allF if rooms(n) or n=='25_西館_階段']+[(p,c) for p,c,n in FR_]
Wc=np.array(_W.centroid.coords[0])
view(axs[0,0],np.r_[Wc+np.array([-30000,-26000]),24000],np.r_[Wc+np.array([4000,-4000]),2000],1.3,'骨組み（南西の上空から）')
view(axs[0,1],np.r_[Wc+np.array([30000,-30000]),16000],np.r_[Wc+np.array([2000,-6000]),3000],1.2,'骨組み（園庭の上空から）')
# close-ups
mainth=G['buildings']()[0]
def wp(k,u,z): return np.r_[at(k,u),z]
view(axs[1,0],wp(10.5,-9000,2500)+np.r_[0,0,0],wp(10.0,5000,4200),0.8,'本館と西館のあいだ（西館の柱・梁・桁、2階床梁）')
mb=G['buildings']()[0]
e=np.array(G['world'](mb,mb['thetas'][6],-9000,1600)); tg=np.array(G['world'](mb,mb['thetas'][8],4000,2600))
view(axs[1,1],e,tg,0.8,'本館の架構（庇の側から）')
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/exact_views.png',dpi=68)
print('done')
