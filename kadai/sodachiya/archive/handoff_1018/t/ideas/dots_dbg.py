exec(open('/tmp/claude-0/t/ideas/dots_opt.py').read().split("import itertools")[0])
import json
for name,Rs,v,pen,ga in json.load(open('/tmp/claude-0/t/ideas/dots_opt.json')):
    _,_,d=evalp(Rs,*v,name,detail=True)
    blds=unary_union([d['main'],d['west']])
    print(name,Rs//1000,'outset %.1f'%(blds.difference(setb).area/1e6),'ne %.0f'%NE.distance(blds),'park %.1f'%(park.intersection(blds.buffer(1000)).area/1e6),'parking', not d['pk'].is_empty,
          'west outset %.1f'%(d['west'].difference(setb).area/1e6),'main outset %.1f'%(d['main'].difference(setb).area/1e6))
