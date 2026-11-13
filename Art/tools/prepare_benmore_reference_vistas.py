"""DEM-derived fine relief and art-directed vegetation/rock masks for long views."""
from pathlib import Path
import json,math
import numpy as np
import rasterio as rio
from rasterio.warp import reproject,Resampling
from rasterio.transform import from_origin
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreReferenceVistas';OUT.mkdir(exist_ok=True)
W,H=2736,2554
with rio.open(ROOT/'Art/Export/MackenzieRealTerrain/region-01/Region_DEM_1m_NZTM.tif') as src:
    z=np.zeros((H,W),np.float32)
    reproject(rio.band(src,1),z,src_transform=src.transform,src_crs=src.crs,dst_transform=from_origin(src.bounds.left,src.bounds.top,5,5),dst_crs=src.crs,resampling=Resampling.average)
assert np.min(z)>0
def blur(a,r):
    p=np.pad(a,((0,0),(r,r)),mode='edge');s=np.pad(np.cumsum(p,axis=1,dtype=np.float64),((0,0),(1,0)));a=(s[:,2*r+1:]-s[:,:-2*r-1])/(2*r+1)
    p=np.pad(a,((r,r),(0,0)),mode='edge');s=np.pad(np.cumsum(p,axis=0,dtype=np.float64),((1,0),(0,0)));return ((s[2*r+1:]-s[:-2*r-1])/(2*r+1)).astype(np.float32)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
def noise(scale,seed):
    rng=np.random.default_rng(seed);a=rng.random((int(np.ceil(H/scale))+2,int(np.ceil(W/scale))+2),dtype=np.float32)
    x=np.arange(W)/scale;y=np.arange(H)/scale;ix=x.astype(int);iy=y.astype(int);fx=(x-ix);fy=(y-iy);fx=fx*fx*(3-2*fx);fy=fy*fy*(3-2*fy)
    return ((a[iy[:,None],ix]*(1-fx)+a[iy[:,None],ix+1]*fx)*(1-fy[:,None])+(a[iy[:,None]+1,ix]*(1-fx)+a[iy[:,None]+1,ix+1]*fx)*fy[:,None]).astype(np.float32)
# Five metre normals preserve the original drainage relief instead of smoothing it away.
gy,gx=np.gradient(z*.85+blur(z,1)*.15,5)
slope=np.hypot(gx,gy);normal=np.stack([-gx,gy,np.ones_like(z)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8(np.round((normal*.5+.5)*255))).save(OUT/'T_Benmore_FineHillNormal.png')
fold=z-blur(z,3);bowl=blur(z,12)-z
patch=.50*noise(21,91)+.30*noise(8,17)+.20*noise(3,11)
rock=smooth(.27,.66,slope)*smooth(.31,.61,patch+fold*.12)
cover=smooth(.31,.63,patch+bowl*.012)*(1-smooth(.35,.75,slope))
scrub=smooth(.49,.70,patch+bowl*.028)*(1-smooth(.18,.48,slope))
relief=np.clip(.5+fold/2,0,1)
rgba=np.stack([cover,rock,relief,scrub],-1)
Image.fromarray(np.uint8(np.round(rgba*255))).save(OUT/'T_Benmore_CoverStructure.png')
# Visual shrub islands bridge the 650 m cut-off of the original close scrub.
grid=np.fromfile(ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes'];pts=np.array([[p['x_m'],p['y_m'],r['width_m']/2] for r in routes for p in r['points']])
def ground(x,y):
    fx=(x+1250)/2500*2016;fy=(y+1250)/2500*2016;i=int(fx);j=int(fy);a=fx-i;b=fy-j;q,r,s,t=grid[j,i],grid[j,i+1],grid[j+1,i],grid[j+1,i+1]
    return float(q+(r-q)*a+(t-r)*b if a>=b else q+(t-s)*a+(s-q)*b)
def sample(a,x,y):return float(a[int((4278-y)/5),int((x+11463)/5)])
def clearance(x,y):return float(np.min(np.hypot(pts[:,0]-x,pts[:,1]-y)-pts[:,2]))
rng=np.random.default_rng(71026);centres=[]
for _ in range(15000):
    x,y=rng.uniform(-1130,1130,2)
    if ground(x,y)<4 or sample(slope,x,y)>.42 or sample(scrub,x,y)<.18 or clearance(x,y)<20:continue
    if all(math.hypot(x-a,y-b)>115 for a,b in centres):centres.append((float(x),float(y)))
    if len(centres)==42:break
rows=[];used=set()
for ci,(cx,cy) in enumerate(centres):
    ang=rng.uniform(0,2*np.pi)
    for _ in range(95):
        a,b=rng.normal(0,[37,17]);x=cx+a*math.cos(ang)-b*math.sin(ang);y=cy+a*math.sin(ang)+b*math.cos(ang)
        if not(-1200<x<1200 and -1200<y<1200):continue
        cell=(round(x/3),round(y/3))
        if cell in used or ground(x,y)<3 or sample(slope,x,y)>.50 or clearance(x,y)<10:continue
        used.add(cell);rows.append(dict(x=float(x),y=float(y),z=ground(x,y),height_m=float(rng.uniform(.95,2.1)),yaw=float(rng.uniform(-180,180)),kind=int(rng.integers(0,2)),cluster=ci))
data={'shrubs':rows,'clusters':centres,'min_road_edge_clearance_m':min(clearance(r['x'],r['y']) for r in rows),'source_texel_m':5,'texture_size':[W,H],'source':'LINZ DEM; art-directed cover is not a land-cover survey','height_changed':False}
(OUT/'placements.json').write_text(json.dumps(data,indent=2));print({'scrub':len(rows),'clusters':len(centres),'min_road_edge_clearance_m':data['min_road_edge_clearance_m'],'texture_size':[W,H]})
