"""Distance forest lighting from authored terrain and the actual saved crowns.

RG: world-space canopy-envelope normal XY. B: soft visibility to the saved sun.
A: approximate local enclosure. This is a fixed-sun distant shading field, not
dynamic per-leaf shadows. Rebuild when terrain, planting or the sun changes.
"""
from pathlib import Path
import numpy as np,json,hashlib,math
from scipy.ndimage import gaussian_filter,zoom
from PIL import Image
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/LidarStudy/CanopyDepth'
data=json.loads((OUT/'lighting-seeds.json').read_text());N=2048;step=3700/N
meta=json.loads((OUT.parent/'authoring.json').read_text())
heightfile=OUT.parent/'Place/authoring-height.r16'
height=np.fromfile(heightfile,'<u2').reshape(2017,2017).astype(np.float32)*meta['height_span_cm']/65535/100
height=zoom(height,N/2017,order=1);canopy=height.copy()
for x,y,top,radius,depth in data['trees']:
 ix=(x+1850)/step-.5;iy=(y+1850)/step-.5;r=max(1,radius/step)
 x0=max(0,int(ix-r));x1=min(N,int(ix+r)+2);y0=max(0,int(iy-r));y1=min(N,int(iy+r)+2)
 if x0>=x1 or y0>=y1:continue
 yy,xx=np.ogrid[y0:y1,x0:x1];d=((xx-ix)**2+(yy-iy)**2)/(r*r)
 crown=np.where(d<1,top-depth*(1-np.sqrt(np.maximum(0,1-d))),-10000)
 np.maximum(canopy[y0:y1,x0:x1],crown,out=canopy[y0:y1,x0:x1])
smooth=gaussian_filter(canopy,5/step)
gy,gx=np.gradient(smooth,step);length=np.sqrt(gx*gx+gy*gy+1)
nx=-gx/length;ny=-gy/length
# Trace the canopy/terrain height envelope towards the actual fixed sunlight.
# Coarser shadow field is sufficient at valley range; soften before upsampling.
small=zoom(canopy,.5,order=1);M=small.shape[0];mstep=3700/M
sun=np.array(data['sun']);horizontal=np.linalg.norm(sun[:2]);direction=sun[:2]/horizontal;slope=sun[2]/horizontal
excess=np.full_like(small,-20)
for distance in np.arange(mstep,1200,mstep*1.5):
 dx,dy=np.rint(direction*distance/mstep).astype(int)
 tx0=max(0,-dx);tx1=min(M,M-dx);ty0=max(0,-dy);ty1=min(M,M-dy)
 if tx0>=tx1 or ty0>=ty1:continue
 delta=small[ty0+dy:ty1+dy,tx0+dx:tx1+dx]-small[ty0:ty1,tx0:tx1]-distance*slope
 np.maximum(excess[ty0:ty1,tx0:tx1],delta,out=excess[ty0:ty1,tx0:tx1])
visibility=np.clip((1.4-excess)/2.8,0,1);visibility=visibility*visibility*(3-2*visibility)
visibility=zoom(gaussian_filter(visibility,.75),2,order=1)
enclosure=np.clip(1-np.maximum(0,gaussian_filter(canopy,24/step)-canopy)*.035,.55,1)
rgba=np.stack([nx*.5+.5,ny*.5+.5,visibility,enclosure],-1)
Image.fromarray(np.uint8(np.clip(rgba,0,1)*255+.5)).save(OUT/'T_CD_Lighting.png')
report=dict(size=[N,N],sun=data['sun'],seed_sha256=hashlib.sha256((OUT/'lighting-seeds.json').read_bytes()).hexdigest(),terrain_sha256=hashlib.sha256(heightfile.read_bytes()).hexdigest(),trees=len(data['trees']),metres_per_pixel=step,normal_smoothing_m=5,shadow_trace_m=1200,shadow_visibility_mean=float(visibility.mean()),method=__doc__)
(OUT/'lighting-field.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
