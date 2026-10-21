exec(open('/tmp/claude-0/t/ideas/check_c3.py').read().split("fig,axs=")[0])
fig,axs=plt.subplots(1,2,figsize=(14,6))
globals()['faces']=[(p,c) for p,c,n in allF]
T=np.array([-1500,-6000])
view(axs[0],np.r_[T+np.array([-14000,9000]),9000],np.r_[T,1500],1.0,'北の道路の上から')
view(axs[1],np.r_[T+np.array([16000,-8000]),6000],np.r_[T,2000],1.0,'園庭の北の端から')
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/machine_onigiri_3d.png',dpi=72)
