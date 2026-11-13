"""Bake coherent normal/height/occlusion data from deterministic surface fields.
Data textures, not painted lighting. All height values are in centimetres.
"""
from pathlib import Path
import numpy as np,json
from PIL import Image
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/FirstSection/PerceivedDetail');OUT.mkdir(exist_ok=True)
rng=np.random.default_rng(87132)
def smoothnoise(n,cells):
 a=rng.random((cells,cells)).astype(np.float32)
 # Periodic, bilinear interpolation of a deterministic source lattice.
 v=np.arange(n,dtype=np.float32)*cells/n;i=v.astype(int);f=v-i;f=f*f*(3-2*f)
 return ((a[i[:,None]%cells,i[None,:]%cells]*(1-f[None,:])+a[i[:,None]%cells,(i[None,:]+1)%cells]*f[None,:])*(1-f[:,None])+(a[(i[:,None]+1)%cells,i[None,:]%cells]*(1-f[None,:])+a[(i[:,None]+1)%cells,(i[None,:]+1)%cells]*f[None,:])*f[:,None])
def bake(name,h,span_cm,depth_cm):
 assert np.isfinite(h).all(),name
 pixel=span_cm/h.shape[0];gx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*pixel);gy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*pixel)
 normal=np.stack([-gx,gy,np.ones_like(h)],-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
 horizon=np.zeros_like(h)
 for dy,dx in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,1),(1,-1),(-1,-1)]:
  occ=np.zeros_like(h)
  for radius in [2,5,11,23,47]:
   slope=(np.roll(np.roll(h,dy*radius,0),dx*radius,1)-h)/(radius*pixel*np.hypot(dx,dy))
   occ=np.maximum(occ,slope)
  horizon+=np.arctan(occ)/(np.pi/2)
 ao=np.clip(1-horizon/8*.62,.48,1)
 height=(h-h.min())/depth_cm
 packed=np.stack([normal[...,0]*.5+.5,normal[...,1]*.5+.5,np.clip(height,0,1),ao],-1)
 Image.fromarray(np.uint8(np.clip(packed,0,1)*255)).save(OUT/(name+'.png'))
 # Source height and full normals are retained for inspection/rebaking.
 Image.fromarray(np.uint16(np.clip(height,0,1)*65535)).save(OUT/(name+'_Height16.png'))
 Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(OUT/(name+'_Normal.png'))
 return dict(name=name,resolution=h.shape[0],span_cm=span_cm,depth_cm=depth_cm,height_min_cm=float(h.min()),height_max_cm=float(h.max()),packed='R tangent normal X; G tangent normal Y; B height; A horizon occlusion')
n=1024;y,x=np.mgrid[:n,:n].astype(np.float32);x*=200/n;y*=200/n
soil=.65*smoothnoise(n,13)+.18*smoothnoise(n,57)+.055*smoothnoise(n,173)
for _ in range(135):
 cx,cy=rng.uniform(0,200,2);rx=rng.uniform(1,4.2);ry=rx*rng.uniform(.6,1.3)
 dx=(x-cx+100)%200-100;dy=(y-cy+100)%200-100;q=(dx/rx)**2+(dy/ry)**2
 soil=np.maximum(soil,.50+rng.uniform(.65,2.4)*np.clip(1-q,0,1)**.55)
for _ in range(10):
 offset=rng.uniform(0,200);wave=offset+3*np.sin(x*.025+rng.uniform(0,6));d=np.abs((y-wave+100)%200-100)
 soil+=rng.uniform(.3,.75)*np.exp(-(d/rng.uniform(.3,.65))**2)
rock=1.0+1.8*smoothnoise(n,5)+.24*smoothnoise(n,39)+.08*smoothnoise(n,119)
for _ in range(23):
 angle=rng.uniform(0,np.pi);offset=rng.uniform(-170,170);width=rng.uniform(.45,1.5)
 d=np.abs(x*np.cos(angle)+y*np.sin(angle)-offset+2.2*np.sin(x*.04+y*.035))
 rock-=rng.uniform(.35,1.5)*np.exp(-(d/width)**2)
rock-=rock.min()
rows=[bake('T_PD_SoilNH',soil,200,4),bake('T_PD_RockNH',rock,200,5)]
n=512;v,u=np.mgrid[:n,:n].astype(np.float32)/(n-1);side=(v-.5)*2
leaf=.055*np.exp(-(side/.16)**2)*(np.clip(np.sin(np.pi*u),0,1)**.4)
vein=np.abs(((u*13-np.abs(side)*1.8+.5)%1)-.5)
leaf+=.018*np.exp(-(vein/.075)**2)*np.sin(np.pi*u)*np.clip(1-np.abs(side),0,1)
leaf+=.004*np.sin(u*125+side*5)*np.sin(side*48)
rows.append(bake('T_PD_LeafNH',leaf,12,.12))
(OUT/'bakes.json').write_text(json.dumps(dict(source='Deterministic authored height fields; gradients and 8-direction sampled horizon occlusion',textures=rows),indent=2))
print(json.dumps(rows,indent=2))
