import matplotlib; matplotlib.use('Agg'); matplotlib.rcParams['pdf.fonttype']=42; import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
plt.rcParams['font.family']='IPAGothic'
rows=[('0・1歳','芽吹き（淡い黄緑）','#E6EFC2'),('2歳','若葉（やわらかい緑）','#C5DE9A'),('3歳','青葉','#9FCB84'),('4歳','青葉（少し深く）','#86BC78'),('5歳','常磐（いちばん深い）','#6FA96E'),
      ('医務','乳白＋小さな赤十字','#F7F3EA'),('医務の赤十字','赤','#D33A3A'),('事務','生成り・砂色','#E9DCC4'),('ホール','木の床（はちみつ色）','#E3C08D'),
      ('遊戯室','陽だまり（淡い山吹）','#F6E3A4'),('キッチン','柿','#F0B98A'),('食べる場所','杏','#F7D3B0'),('2階の職員の部屋','藤（薄紫）','#E3DAF0'),('便所・水まわり','水色','#D5EBEE'),('廊下・縁側','白木（塗らない）','#F4EBDD')]
fig,ax=plt.subplots(figsize=(8,7.7)); ax.axis('off'); ax.set_xlim(0,10); ax.set_ylim(0,len(rows)+0.5)
for i,(n,d,c) in enumerate(rows):
    y=len(rows)-i-0.5
    ax.add_patch(Rectangle((0.2,y-0.38),1.6,0.76,fc=c,ec='#999',lw=.5))
    if n=='医務':
        pass
    if n=='医務':
        ax.add_patch(Rectangle((0.92,y-0.24),0.16,0.48,fc='#D33A3A',ec='none')); ax.add_patch(Rectangle((0.76,y-0.08),0.48,0.16,fc='#D33A3A',ec='none'))
    ax.text(2.1,y,n,va='center',fontsize=12); ax.text(4.6,y,d,va='center',fontsize=10,color='#444'); ax.text(8.2,y,c[1:],va='center',fontsize=11,color='#333',family='monospace')
    if i==4 or i==8: ax.plot([0.2,9.8],[y-0.5,y-0.5],color='#ccc',lw=.6)
plt.tight_layout(); plt.savefig('/home/claude/plans/rhino/room_colors.pdf')
