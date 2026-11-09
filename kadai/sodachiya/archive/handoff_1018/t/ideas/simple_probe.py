exec(open('/tmp/claude-0/t/ideas/hill3_core.py').read())
setbI=setb
for k in np.arange(1.0,6.01,0.25):
    ok=setb.contains(SPt(*at(k,12700))) and setb.contains(SPt(*at(k,700)))
    print(k, ok, round(segs[min(kk,key=lambda x:abs(x-k))][2]) if min(abs(np.array(kk)-k))<0.2 else '')
