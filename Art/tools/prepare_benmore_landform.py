"""A numeric landform mask: broad concavity and local relief from the source DEM."""
from pathlib import Path
import numpy as np,json,rasterio as rio
from rasterio.warp import reproject,Resampling
from rasterio.transform import from_origin
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreEnvironment'
with rio.open(ROOT/'Art/Export/MackenzieRealTerrain/region-01/Region_DEM_1m_NZTM.tif') as src:
    l,b,r,t=src.bounds;res=10;w=int((r-l)/res);h=int((t-b)/res);a=np.zeros((h,w),np.float32)
    reproject(rio.band(src,1),a,src_transform=src.transform,src_crs=src.crs,dst_transform=from_origin(l,t,res,res),dst_crs=src.crs,resampling=Resampling.average)
def blur(a,r):
    # Separable box filter, metres remain float; edge padding prevents wraparound.
    p=np.pad(a,((0,0),(r,r)),mode='edge');s=np.pad(np.cumsum(p,axis=1,dtype=np.float64),((0,0),(1,0)));a=(s[:,2*r+1:]-s[:,:-2*r-1])/(2*r+1)
    p=np.pad(a,((r,r),(0,0)),mode='edge');s=np.pad(np.cumsum(p,axis=0,dtype=np.float64),((1,0),(0,0)));return (s[2*r+1:]-s[:-2*r-1])/(2*r+1)
concavity=np.clip(.5+(blur(a,7)-a)/20,0,1);detail=np.clip(.5+(blur(a,2)-a)/5,0,1)
gy,gx=np.gradient(a,10);slope=np.clip(np.hypot(gx,gy)/.8,0,1)
rgba=np.stack([concavity,detail,slope,np.ones_like(a)],axis=2);Image.fromarray(np.uint8(np.round(rgba*255))).save(OUT/'T_Benmore_Landform.png')
(OUT/'landform.json').write_text(json.dumps({'bounds_nztm':[l,b,r,t],'width':w,'height':h,'spacing_m':10,'channels':{'R':'140 m neighbourhood concavity','G':'40 m neighbourhood concavity','B':'slope','A':'unused'}},indent=2))
