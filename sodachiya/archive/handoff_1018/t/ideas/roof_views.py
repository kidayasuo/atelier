exec(open('/tmp/claude-0/t/ideas/roof_render.py').read())
V=dict(N=(0,0),E=(34860,-43830),S=(-14440,-83040),SW=(-21910,-73650),W=(-25830,-20540))
Wc=np.array(W.centroid.coords[0])
Vw=np.array(V['W']); bis=unit(unit(np.array(V['N'])-Vw)+unit(np.array(V['SW'])-Vw))
eye1=np.r_[Vw-bis*9000,1500]; tgt1=np.r_[np.array(segs[5.0][1]),1500]
eye2=np.r_[Vw-bis*30000+np.array([0,-12000]),26000]; tgt2=np.r_[Wc+np.array([3000,-2000]),2000]
pn=segs[3.0][1]; eye3=np.r_[np.array(V['N'])*0.5+np.array(V['W'])*0.5+np.array([-3000,9000]),1500]; tgt3=np.r_[Wc,1500]
opts=[('A','A：勾配一定・外側の軒が一定'),('B','B：勾配一定・本館側の棟を保つ'),('C','C：両端の高さ一定・勾配が変化'),('D','D：外側の軒が交差点へ向かって上がる')]
fig,axs=plt.subplots(4,3,figsize=(18,17))
for row,(o,t) in enumerate(opts):
    F,zi,zo=faces_for(o)
    render(axs[row,0],F,eye1,tgt1,t+'　｜　交差点の歩道から（目の高さ 1.5m）',focal=0.62)
    render(axs[row,1],F,eye2,tgt2,'北西の上空から（屋根の面）',focal=1.5)
    ax=axs[row,2]
    # 展開した外側の立面（北の先端→南）と本館側の棟
    sL=np.r_[0,np.cumsum(np.linalg.norm(np.diff(np.array([segs[k][1] for k in kk]),axis=0),axis=1))]/1000
    ax.fill_between(sL,0,zo/1000,color='#dccdb0',label='外側の壁（道路側）')
    ax.plot(sL,zi/1000,color='#8a5a3a',lw=1.5,label='本館側の棟')
    ax.plot(sL,zo/1000,color='#5a4630',lw=1.2)
    ax.axhline(4.0,color='#888',lw=.6,ls='--'); ax.text(sL[-1],4.05,'本館の西の屋根 4.0m',fontsize=7,ha='right',color='#666')
    slope=(zi-zo)/Larr
    ax2=ax.twinx(); ax2.plot(sL,1/np.maximum(slope,1e-6),color='#3c78b4',lw=.8,ls=':'); ax2.set_ylim(0,30); ax2.set_ylabel('勾配 1/N の N（点線）',fontsize=7,color='#3c78b4')
    ax.set_ylim(0,9.5); ax.set_xlabel('北の先端からの長さ（m、道路側の外壁に沿って）',fontsize=7); ax.set_ylabel('高さ m',fontsize=7)
    ax.set_title('道路側の外壁の展開立面',fontsize=9); ax.legend(fontsize=7,loc='lower right')
    print(o,'outer %.2f-%.2f ridge %.2f-%.2f'%(zo.min()/1000,zo.max()/1000,zi.min()/1000,zi.max()/1000))
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/west_roof_options.png',dpi=65)
