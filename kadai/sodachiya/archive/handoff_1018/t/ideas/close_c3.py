src=open('/tmp/claude-0/t/ideas/check_c3.py').read()
exec(src.split("fig,axs=")[0])
fig,axs=plt.subplots(1,2,figsize=(16,7))
keep=lambda n: n not in ('20_西館_屋根','10_本館_屋根','21_西館_外壁','11_本館_骨組み','35_機械室（本館の北）','26_室外機置場')
globals()['faces']=[(p,c) for p,c,n in allF if keep(n)]
T=np.array([-17500,-41000])
view(axs[0],np.r_[T+np.array([-17000,-17000]),14000],np.r_[T,3000],1.1,'南西の上空から（屋根・外壁・本館を外して）')
view(axs[1],np.r_[T+np.array([14000,-16000]),11000],np.r_[T+np.array([-2000,3000]),3500],1.1,'南東から（同）')
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_case3_south.png',dpi=72)
