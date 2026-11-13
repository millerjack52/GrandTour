"""Geographic material-control data from the existing DEM; no height edits.

Outputs are numeric shader inputs, not painted terrain imagery. D8 drainage is
a visual proxy: depressions are not filled and this is not a hydrology survey.
"""
from pathlib import Path
import json, hashlib, time
import numpy as np
import rasterio as rio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreVistaStudy'; OUT.mkdir(exist_ok=True)
W,H=2736,2554; CELL=5.0
canonical=ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32'
sha=hashlib.sha256(canonical.read_bytes()).hexdigest()
start=time.monotonic()
with rio.open(ROOT/'Art/Export/MackenzieRealTerrain/region-01/Region_DEM_1m_NZTM.tif') as src:
    z=np.zeros((H,W),np.float32)
    reproject(rio.band(src,1),z,src_transform=src.transform,src_crs=src.crs,
              dst_transform=from_origin(src.bounds.left,src.bounds.top,CELL,CELL),
              dst_crs=src.crs,resampling=Resampling.average)
    bounds=list(src.bounds)
assert np.isfinite(z).all() and z.min()>0

def blur(a,r):
    p=np.pad(a,((0,0),(r,r)),mode='edge')
    s=np.pad(np.cumsum(p,axis=1,dtype=np.float64),((0,0),(1,0)))
    a=(s[:,2*r+1:]-s[:,:-2*r-1])/(2*r+1)
    p=np.pad(a,((r,r),(0,0)),mode='edge')
    s=np.pad(np.cumsum(p,axis=0,dtype=np.float64),((1,0),(0,0)))
    return ((s[2*r+1:]-s[:-2*r-1])/(2*r+1)).astype(np.float32)

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

# Route every cell only to a strictly lower neighbour. Descending elevation is
# therefore a valid accumulation order without cycles or recursive traversal.
gy,gx=np.gradient(z,CELL);slope=np.hypot(gx,gy)
receiver=np.full((H,W),-1,np.int32);drop=np.zeros_like(z)
ids=np.arange(W*H,dtype=np.int32).reshape(H,W)
pad=np.pad(z,1,mode='edge');ip=np.pad(ids,1,constant_values=-1)
for dy,dx in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
    neighbour=pad[1+dy:H+1+dy,1+dx:W+1+dx]
    candidate=ip[1+dy:H+1+dy,1+dx:W+1+dx]
    gradient=(z-neighbour)/(CELL*np.hypot(dx,dy))
    take=(gradient>drop)&(candidate>=0)
    receiver[take]=candidate[take];drop[take]=gradient[take]
area=np.ones(W*H,np.float32);dest=receiver.ravel()
for i in np.argsort(z.ravel())[::-1]:
    j=dest[i]
    if j>=0:area[j]+=area[i]
flow=np.log1p(area.reshape(H,W))
# Small channels sit inside broader hollows. Avoid painting all D8 paths as
# high-contrast parallel stripes; only concentrated flow has much influence.
hollow=blur(z,13)-z
fold=z-blur(z,4)
flow_core=smooth(4.2,8.2,flow)
drain=np.clip(blur(flow_core,2)*.65+smooth(1.0,8.5,hollow)*.60,0,1)
exposure=smooth(.25,.70,slope)*(.60+.40*smooth(-1.5,3.2,fold))
soil=(1-smooth(.28,.65,slope))*smooth(-1.0,5.0,hollow)
# Local relief is encoded around neutral .5, independent of sun direction.
relief=np.clip(.5+fold/7.5,0,1)
mask=np.stack([drain,exposure,soil,relief],-1)
assert np.isfinite(mask).all() and mask.min()>=0 and mask.max()<=1
Image.fromarray(np.uint8(np.round(mask*255))).save(OUT/'T_Benmore_GeographicZones.png')
assert hashlib.sha256(canonical.read_bytes()).hexdigest()==sha
report={'ok':True,'source':'LINZ DEM, numeric terrain-derived material controls',
        'generator':'Python / rasterio / NumPy; no Gaea export used',
        'height_changed':False,'height_sha256':sha,'spacing_m':CELL,'size':[W,H],
        'bounds_nztm':bounds,'channels':{'R':'drainage and sheltered hollows','G':'steep exposed rock','B':'soil settlement proxy','A':'local terrain relief, neutral .5'},
        'channel_percentiles':{n:np.percentile(mask[...,i],[0,10,50,90,100]).tolist() for i,n in enumerate('RGBA')},
        'elapsed_seconds':time.monotonic()-start}
(OUT/'geography-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
