"""Authored starting churn, not recovered map data. 12.5 cm texels shared by CPU/GPU."""
from pathlib import Path
import numpy as np,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreWoodland'
N=1024;SIZE=12800.;rng=np.random.default_rng(361905)
y,x=np.mgrid[:N,:N].astype(np.float32);x=(x+.5)*SIZE/N;y=(y+.5)*SIZE/N
h=np.zeros_like(x)
wrap=lambda p:(p+SIZE/2)%SIZE-SIZE/2
# Smooth, periodic 0.8-4 m folds; no per-vertex jitter or isolated pyramids.
for k in range(32):
 nx,ny=rng.integers(-90,91,2)
 if nx==0 and ny==0:continue
 h+=rng.uniform(.35,1.3)*np.sin((x*nx+y*ny)*2*np.pi/SIZE+rng.uniform(0,2*np.pi))
# Broad, irregular depressions and displaced shoulders, about 1-4 m wide.
for k in range(90):
 cx,cy=rng.uniform(0,SIZE,2);a=rng.uniform(0,np.pi);dx=wrap(x-cx);dy=wrap(y-cy)
 along=dx*np.cos(a)+dy*np.sin(a);across=-dx*np.sin(a)+dy*np.cos(a)
 q=(along/rng.uniform(110,340))**2+(across/rng.uniform(65,160))**2
 h+=rng.uniform(5,10)*(1.5*np.exp(-q*.45)-2.4*np.exp(-q*1.7))
# Several older, meandering paired wheel passages, feathering into undisturbed soil.
for k in range(27):
 cx,cy=rng.uniform(0,SIZE,2);a=rng.uniform(0,np.pi);dx=wrap(x-cx);dy=wrap(y-cy)
 s=dx*np.cos(a)+dy*np.sin(a);t=-dx*np.sin(a)+dy*np.cos(a)
 length=rng.uniform(800,2000);envelope=np.exp(-(s/length)**6)
 t=t-30*np.sin(s/330+rng.uniform(0,6.28))-12*np.sin(s/110)
 width=rng.uniform(22,36);separation=rng.uniform(65,80);depth=rng.uniform(12,25)
 for side in [-1,1]:
  d=t-side*separation
  h+=envelope*(-depth*np.exp(-(d/width)**2)+5*np.exp(-((np.abs(d)-width*1.8)/(width*.8))**2))
# Keep the existing -50..15 cm encoding and avoid clipped flat ridges.
h=12*np.tanh(np.maximum(h,0)/12)+35*np.tanh(np.minimum(h,0)/35)
packed=np.uint16(np.clip((h+50)/65,0,1)*65535+.5)
Image.fromarray(np.stack([packed>>8,packed&255,np.zeros_like(packed),np.full_like(packed,255)],-1).astype('uint8')).save(OUT/'relief.png')
report=dict(tile_cm=SIZE,resolution=N,texel_cm=SIZE/N,min_cm=float(h.min()),max_cm=float(h.max()),std_cm=float(h.std()),authored=True)
(OUT/'relief.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
