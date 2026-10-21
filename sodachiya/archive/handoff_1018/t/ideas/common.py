import math, numpy as np
from shapely.geometry import Polygon as SP, LineString as SL, Point as SPt, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['font.family']='IPAGothic'
V=dict(N=(0,0),E=(34860,-43830),S=(-14440,-83040),SW=(-21910,-73650),W=(-25830,-20540))
site=SP([V['N'],V['E'],V['S'],V['SW'],V['W']])
setb=SP([(-160,-1405),(33455,-43670),(-14280,-81635),(-20935,-73269),(-24794,-20994)])
tip=np.array(V['S']); e1=np.array(V['SW'])-tip; e2=np.array(V['E'])-tip
e1=e1/np.linalg.norm(e1); e2=e2/np.linalg.norm(e2)
park=SP([tuple(tip),tuple(tip+e1*12000),tuple(tip+e1*12000+e2*12000),tuple(tip+e2*12000)])
def unit(v): v=np.array(v,float); return v/np.linalg.norm(v)
def annulus(c,r0,r1,a0,a1,n=60):
    a=np.linspace(a0,a1,n)
    pts=[(c[0]+r1*math.cos(t),c[1]+r1*math.sin(t)) for t in a]+[(c[0]+r0*math.cos(t),c[1]+r0*math.sin(t)) for t in a[::-1]]
    return SP(pts)
def frame(ax,title):
    def f(p,fc,ec='k',lw=.6,ls='-',alpha=1):
        for q in getattr(p,'geoms',[p]):
            x,y=q.exterior.xy; ax.fill(x,y,fc=fc,ec=ec,lw=lw,ls=ls,alpha=alpha)
    f(site,'#eef5e6')
    x,y=setb.exterior.xy; ax.plot(list(x)+[x[0]],list(y)+[y[0]],color='#bbb',lw=.5,ls='--')
    f(park,'#9CC58A'); c=park.centroid; ax.text(c.x,c.y,'公園',ha='center',va='center',fontsize=7)
    for tt,(x,y),r in [('北の道路（大学）',(-15500,-7500),38),('西の道路',(-28500,-48000),86),('高野川',(15000,-66000),38),('隣家',(21500,-19000),-51)]:
        ax.text(x,y,tt,fontsize=7,ha='center',va='center',rotation=r,color='#555')
    ax.annotate('比叡',xy=(36000,6000),xytext=(30000,-1000),fontsize=7,arrowprops=dict(arrowstyle='->',color='#888'),color='#888')
    ax.set_aspect('equal'); ax.axis('off'); ax.set_title(title,fontsize=10)
    ax.set_xlim(-30000,38000); ax.set_ylim(-86000,4000)
    return f
def lab(ax,p,t,fs=7,**kw):
    c=p.representative_point() if not isinstance(p,tuple) else SPt(*p); ax.text(c.x,c.y,t,ha='center',va='center',fontsize=fs,**kw)
def garden_area(blds,extra=[]):
    g=site.difference(unary_union(blds+extra+[park]))
    return g.area/1e6
