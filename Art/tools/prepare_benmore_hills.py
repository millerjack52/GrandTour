"""Geographic hill masks, world normals and evenly sampled scenery from LINZ DEM."""
from pathlib import Path
import json, shutil
import numpy as np
import rasterio as rio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreHills';OUT.mkdir(exist_ok=True)
shader=ROOT/'Art/Unreal/benmore_bank_surface.py'
if not (OUT/'before_benmore_bank_surface.py').exists():shutil.copyfile(shader,OUT/'before_benmore_bank_surface.py')
for name in ['Terrace_Fence','Sheltered_Scrub','Hillside_Vista']:
    target=OUT/('Before_'+name+'.png')
    if not target.exists():shutil.copyfile(ROOT/'Art/Export/BenmoreCharacter'/(name+'.png'),target)
with rio.open(ROOT/'Art/Export/MackenzieRealTerrain/region-01/Region_DEM_1m_NZTM.tif') as src:
    bounds=list(src.bounds);res=10.;w=int((bounds[2]-bounds[0])/res);h=int((bounds[3]-bounds[1])/res)
    dem=np.full((h,w),-9999,np.float32)
    reproject(rio.band(src,1),dem,src_transform=src.transform,src_crs=src.crs,dst_transform=from_origin(bounds[0],bounds[3],res,res),dst_crs=src.crs,resampling=Resampling.average)
assert np.min(dem)>0
def blur(a,r):
    p=np.pad(a,((0,0),(r,r)),mode='edge');s=np.pad(np.cumsum(p,axis=1,dtype=np.float64),((0,0),(1,0)));a=(s[:,2*r+1:]-s[:,:-2*r-1])/(2*r+1)
    p=np.pad(a,((r,r),(0,0)),mode='edge');s=np.pad(np.cumsum(p,axis=0,dtype=np.float64),((1,0),(0,0)));return (s[2*r+1:]-s[:-2*r-1])/(2*r+1)
def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
# Descending D8 accumulation; strict downhill links cannot form cycles.
# This is an art mask, not a hydrologic simulation: local pits remain sinks.
z=blur(dem,1);yy,xx=np.indices(z.shape);dest=np.full(z.shape,-1,np.int32);best=np.zeros_like(z)
for dy,dx in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
    ny=np.clip(yy+dy,0,h-1);nx=np.clip(xx+dx,0,w-1);drop=(z-z[ny,nx])/np.hypot(dx,dy)
    take=drop>best;dest[take]=(ny*w+nx)[take];best[take]=drop[take]
acc=np.ones(z.size,np.float64);links=dest.ravel()
for i in np.argsort(z.ravel())[::-1]:
    j=links[i]
    if j>=0:acc[j]+=acc[i]
flow=smooth(1.25,3.2,np.log10(acc.reshape(h,w)))
drain=np.clip(blur(flow,1)*1.7,0,1)
gy,gx=np.gradient(z,res);slope=np.hypot(gx,gy)
ridge=np.clip(.5+(z-blur(z,16))/35,0,1)
fold=np.clip(.5+(z-blur(z,4))/8,0,1)
rgba=np.stack([drain,ridge,np.clip(slope,0,1),fold],-1)
Image.fromarray(np.uint8(np.round(rgba*255))).save(OUT/'T_Benmore_HillStructure.png')
# Raster Y runs south, world Y north: normal Y is +dH/dRasterY.
normal=np.stack([-gx,gy,np.ones_like(z)],-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
Image.fromarray(np.uint8(np.round((normal*.5+.5)*255))).save(OUT/'T_Benmore_HillNormal.png')
cx,cy=1383300,5081149;datum=360.531005859375
def sample(a,f,g):
    f=np.clip(f,0,a.shape[1]-1.000001);g=np.clip(g,0,a.shape[0]-1.000001);i=f.astype(int);j=g.astype(int);x=f-i;y=g-j
    return (a[j,i]*(1-x)+a[j,i+1]*x)*(1-y)+(a[j+1,i]*(1-x)+a[j+1,i+1]*x)*y
grid=np.fromfile(ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
def height(x,y):
    real=sample(dem,(x+cx-bounds[0])/res-.5,(bounds[3]-y-cy)/res-.5)-datum
    edge=sample(grid,(np.clip(x,-1250,1250)+1250)/2500*2016,(np.clip(y,-1250,1250)+1250)/2500*2016)
    blend=smooth(-5,35,np.maximum(abs(x),abs(y))-1250)
    return edge*(1-blend)+real*blend-.2*(1-blend)
local=[bounds[0]-cx+20,bounds[1]-cy+20,bounds[2]-cx-20,bounds[3]-cy-20]
def axis(lo,hi):return np.unique(np.r_[lo,np.arange(np.ceil(lo/20)*20,hi,20),hi,[-1245,1245]])
xs=axis(local[0],local[2]);ys=axis(local[1],local[3]);parts=[]
for name,x,y in [('West',xs[xs<=-1245],ys),('East',xs[xs>=1245],ys),('South',xs[(xs>=-1245)&(xs<=1245)],ys[ys<=-1245]),('North',xs[(xs>=-1245)&(xs<=1245)],ys[ys>=1245])]:
    xx,yy=np.meshgrid(x,y);verts=np.stack([xx,yy,height(xx,yy)],-1).astype('<f4');mesh='SM_Benmore_Hills_'+name;verts.tofile(OUT/(mesh+'.f32'))
    parts.append({'name':mesh,'rows':len(y),'columns':len(x),'vertices':len(x)*len(y),'triangles':2*(len(x)-1)*(len(y)-1)})
manifest={'bounds_nztm':bounds,'texture_size':[w,h],'texel_m':10,'mesh_spacing_m':20,'parts':parts,'triangles':sum(p['triangles'] for p in parts),'source':'LINZ Data Service, CC BY 4.0','height_exaggeration':1,'structure_channels':{'R':'smoothed downhill runoff accumulation','G':'320 m relative ridge height','B':'slope rise/run','A':'80 m local fold convexity'},'normal_space':'world XYZ, RGB UNORM, north-up raster','heightfield_changed':False}
(OUT/'hills.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
