"""Bake inexpensive, world-aligned forest-floor variation from existing trees.

The canopy field approximates enclosure, not directional shadows or 3D AO.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image
ROOT=Path('C:/GrandTour');OUT=ROOT/'Art/Export/LidarStudy/Place/ValleyGround'
seeds=np.asarray(json.loads((OUT/'canopy-seeds.json').read_text()),np.float64)
N=4096;metres_per_pixel=3700/N
xy=(seeds[:,:2]+185000)/370000*N-.5
ix=np.rint(xy[:,0]).astype(int);iy=np.rint(xy[:,1]).astype(int)
valid=(ix>=0)&(ix<N)&(iy>=0)&(iy<N)
# Far-card bounds are larger than leaf crowns. Use restrained influence radii
# and retain the sparse/gapped distribution from the actual map instances.
radius=np.clip(seeds[:,2]*.006,2,8)
buckets=np.clip(np.rint(radius).astype(int),2,8);density=np.zeros((N,N),np.float32)
for r in range(2,9):
    hits=valid&(buckets==r);layer=np.zeros_like(density)
    np.add.at(layer,(iy[hits],ix[hits]),1.)
    sigma=r*.65/metres_per_pixel
    density+=gaussian_filter(layer,sigma,mode='constant')*(2*np.pi*sigma*sigma)
enclosure=1-np.exp(-density*.78)
rng=np.random.default_rng(20261109)
def field(scale):
    a=gaussian_filter(rng.random((N,N),dtype=np.float32),scale/metres_per_pixel,mode='reflect')
    lo,hi=np.percentile(a,[2,98]);return np.clip((a-lo)/(hi-lo),0,1)
small=.55*field(.9)+.45*field(3.2);broad=field(18);large=field(65)
cover=np.clip(.08+.63*small+.24*broad+.18*enclosure,0,1)
variation=.55*broad+.45*large
fine=field(.65)
rgba=np.stack([enclosure,cover,variation,fine],-1)
Image.fromarray(np.uint8(np.clip(rgba,0,1)*255+.5)).save(OUT/'T_VG_Floor.png')
report=dict(source_sha256=hashlib.sha256((OUT/'canopy-seeds.json').read_bytes()).hexdigest(),instances=len(seeds),size=[N,N],world_span_m=3700,metres_per_pixel=metres_per_pixel,method='Approximate enclosure from existing canopy bases; layered 0.9/3.2/18/65 metre ground-cover variation',enclosure_mean=float(enclosure.mean()),canopy_bounds_radius_scale=.6)
(OUT/'map.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
