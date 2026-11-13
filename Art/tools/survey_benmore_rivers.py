"""Authoring survey: DEM drainage, not evidence of a perennial watercourse."""
from pathlib import Path
import sys, json, heapq
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource
sys.path.insert(0,str(Path(__file__).parent))
from prepare_benmore_composition import height, ROUTES
OUT=Path('C:/GrandTour/Art/Export/BenmoreRivers');OUT.mkdir(exist_ok=True)
axis=np.linspace(-1250,1250,501);xx,yy=np.meshgrid(axis,axis);bed=height(xx,yy)
filled=bed.copy();seen=np.zeros(bed.shape,bool);receiver=np.full(bed.size,-1,int);queue=[];order=[]
for j in range(501):
    for i in range(501):
        if j in (0,500) or i in (0,500) or bed[j,i]<.7:
            seen[j,i]=True;heapq.heappush(queue,(float(bed[j,i]),j,i))
while queue:
    z,j,i=heapq.heappop(queue);order.append(j*501+i)
    for dj,di in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
        v,w=j+dj,i+di
        if not(0<=v<501 and 0<=w<501) or seen[v,w]:continue
        seen[v,w]=True;filled[v,w]=max(bed[v,w],z+.0001);receiver[v*501+w]=j*501+i
        heapq.heappush(queue,(float(filled[v,w]),v,w))
acc=np.ones(bed.size)
for k in reversed(order):
    if receiver[k]>=0:acc[receiver[k]]+=acc[k]
acc=acc.reshape(bed.shape)*25
np.savez_compressed(OUT/'survey.npz',axis=axis,bed=bed,filled=filled,receiver=receiver,catchment_m2=acc)
fig,ax=plt.subplots(figsize=(12,11))
rgb=LightSource(315,35).shade(bed,cmap=plt.get_cmap('gist_earth'),vert_exag=1,dx=5,dy=5)
ax.imshow(rgb,origin='lower',extent=(-1250,1250,-1250,1250))
ax.contour(xx,yy,bed,levels=np.arange(0,310,10),colors='k',alpha=.25,linewidths=.5)
ax.scatter(xx[acc>25000],yy[acc>25000],s=np.clip(acc[acc>25000]/40000,1,14),c='#28cbea',alpha=.7)
for route in ROUTES:ax.plot([p['x_m'] for p in route['points']],[p['y_m'] for p in route['points']],color='#f4764e',lw=2)
ax.plot(750,500,'w*',markersize=13);ax.text(750,550,'Existing overlook',color='w')
ax.set(xlabel='East (m)',ylabel='North (m)',title='Benmore DEM drainage survey — blue = accumulated terrain runoff, orange = roads')
ax.grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'Drainage_Survey.png',dpi=130)
print(str(OUT/'Drainage_Survey.png'))
