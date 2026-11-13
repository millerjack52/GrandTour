"""Bake the height a visible surface must reach to see the saved sun.

Unlike one visibility value per tree, this field can shadow lower foliage while
leaving its upper crown lit. It approximates an opaque canopy envelope, using
the saved planting and terrain. Rebuild with either or the sun direction.
"""
from pathlib import Path
import runpy,json
import numpy as np
from PIL import Image
ROOT=Path('C:/GrandTour')
d=runpy.run_path(str(ROOT/'Art/tools/build_canopy_lighting.py'))
canopy=d['canopy'];step=d['step'];sun=d['sun'];OUT=d['OUT'];N=canopy.shape[0]
direction=sun[:2]/np.linalg.norm(sun[:2]);slope=sun[2]/np.linalg.norm(sun[:2])
ceiling=np.full_like(canopy,-10000)
for distance in np.arange(step*.75,1200,step*1.5):
 dx,dy=np.rint(direction*distance/step).astype(int)
 x0=max(0,-dx);x1=min(N,N-dx);y0=max(0,-dy);y1=min(N,N-dy)
 if x0>=x1 or y0>=y1:continue
 blocker=canopy[y0+dy:y1+dy,x0+dx:x1+dx]-distance*slope
 np.maximum(ceiling[y0:y1,x0:x1],blocker,out=ceiling[y0:y1,x0:x1])
lo=-20.;hi=float(np.ceil(canopy.max()+20))
packed=np.uint16(np.clip((ceiling-lo)/(hi-lo),0,1)*65535+.5)
rgba=np.zeros((N,N,4),np.uint8);rgba[:,:,0]=packed>>8;rgba[:,:,1]=packed&255;rgba[:,:,3]=255
Image.fromarray(rgba).save(OUT/'T_CD_ShadowHeight.png')
report=dict(height_min_m=lo,height_max_m=hi,world_min_m=[-1850,-1850],world_span_m=3700,size=[N,N],sun=sun.tolist(),trace_m=1200,method=__doc__)
(OUT/'shadow-height.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
