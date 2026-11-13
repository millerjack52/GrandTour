"""Terrain-only drainage diagnostic; does not install or alter terrain."""
from pathlib import Path
import heapq,json
import numpy as np,rasterio
from rasterio.enums import Resampling
from PIL import Image,ImageDraw
from scipy.ndimage import map_coordinates

D=Path('Art/Export/LidarStudy/Reference');SRC=Path('C:/Users/mille/Downloads/lds-new-zealand-2layers-GTiff-SHP/new-zealand-lidar-1m-dem')
cache=D/'drainage-2m.npz';step=2.
if not cache.exists():
    raw=np.concatenate([rasterio.open(SRC/f).read(1) for f in ['CF08.tif','CG08.tif']])
    # Pixel-centre mapping, no padded landscape or quantised export involved.
    h=map_coordinates(raw,np.mgrid[.5:3701:2,.5:3637:2],order=1,mode='nearest').astype('float32')
    ny,nx=h.shape;seen=np.zeros(h.shape,bool);parent=np.full(h.size,-1,np.int32);filled=h.copy();heap=[];order=[]
    for j in range(ny):
        for i in ([0,nx-1] if 0<j<ny-1 else range(nx)):
            seen[j,i]=True;heapq.heappush(heap,(float(h[j,i]),j*nx+i))
    offsets=[(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]
    while heap:
        z,k=heapq.heappop(heap);order.append(k);j,i=divmod(k,nx)
        for dy,dx in offsets:
            y,x=j+dy,i+dx
            if y<0 or x<0 or y>=ny or x>=nx or seen[y,x]:continue
            seen[y,x]=True;q=y*nx+x;parent[q]=k;v=max(z,float(h[y,x]));filled[y,x]=v;heapq.heappush(heap,(v,q))
    print('Priority flood finished',flush=True)
    # Use steepest downhill D8, not the priority-flood tree on slopes.
    receiver=parent.copy().reshape(h.shape);best=np.zeros(h.shape,np.float32);ids=np.arange(h.size).reshape(h.shape)
    for dy,dx in offsets:
        a=(slice(max(0,-dy),min(ny,ny-dy)),slice(max(0,-dx),min(nx,nx-dx)))
        b=(slice(max(0,dy),min(ny,ny+dy)),slice(max(0,dx),min(nx,nx+dx)))
        slope=(filled[a]-filled[b])/(step*np.hypot(dx,dy));better=slope>best[a]
        best[a][better]=slope[better];receiver[a][better]=ids[b][better]
    # Flood order increases elevation and resolves flat parent order; downstream
    # receivers therefore always precede their donors (checked explicitly).
    order=np.asarray(order,np.int32);rank=np.empty(h.size,np.int32);rank[order]=np.arange(h.size)
    receiver=receiver.ravel();v=receiver>=0;assert np.all(rank[receiver[v]]<rank[v])
    acc=np.full(h.size,step*step,np.float64)
    for k in order[::-1]:
        if receiver[k]>=0:acc[receiver[k]]+=acc[k]
    np.savez_compressed(cache,h=h,filled=filled,receiver=receiver,acc=acc.reshape(h.shape),order=order)
else:
    z=np.load(cache);h=z['h'];filled=z['filled'];receiver=z['receiver'];acc=z['acc'];order=z['order'];ny,nx=h.shape

acc=acc.reshape(h.shape)
gy,gx=np.gradient(h,step);shade=np.clip(.55-.32*gx+.40*gy,0,1)
im=Image.fromarray(np.uint8(np.stack([shade*.88,shade*.94,shade],-1)*255))
arr=np.array(im);arr[acc>100000]=[35,160,220];arr[acc>1000000]=[10,90,200];im=Image.fromarray(arr);d=ImageDraw.Draw(im)
house=(-522.6444549,-262.5674983)
def pix(x,y):return ((x+1817.5)/2,(y+1849.5)/2)
a=pix(*house);d.ellipse((a[0]-5,a[1]-5,a[0]+5,a[1]+5),fill='red');d.text((a[0]+8,a[1]),'House',fill='white')
im.save(D/'terrain-channel-network.png');im.crop((450,150,1000,1000)).resize((1100,1700)).save(D/'terrain-channel-house.png')
yy,xx=np.mgrid[:ny,:nx];x=-1817.5+xx*2;y=-1849.5+yy*2
zone=(x>-550)&(x<-440)&(y>-380)&(y<-260)
ids=np.flatnonzero(zone);ids=ids[np.argsort(acc.ravel()[ids])[-12:]]
print(json.dumps([dict(x=float(x.ravel()[k]),y=float(y.ravel()[k]),z=float(h.ravel()[k]),area=float(acc.ravel()[k])) for k in ids],indent=2))
