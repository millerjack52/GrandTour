"""A numeric lake-coverage mask from the existing regional terrain data."""
from pathlib import Path
import numpy as np,rasterio as rio
from rasterio.warp import reproject,Resampling
from rasterio.transform import from_origin
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreVistas'
with rio.open(ROOT/'Art/Export/MackenzieRealTerrain/region-01/Region_DEM_1m_NZTM.tif') as src:
    l,b,r,t=src.bounds;w=int((r-l)/10);h=int((t-b)/10);z=np.zeros((h,w),np.float32)
    reproject(rio.band(src,1),z,src_transform=src.transform,src_crs=src.crs,dst_transform=from_origin(l,t,10,10),dst_crs=src.crs,resampling=Resampling.average)
water=(z<361.011005859375).astype(float)
def blur(a,r):
    p=np.pad(a,((0,0),(r,r)),mode='edge');s=np.pad(np.cumsum(p,axis=1),((0,0),(1,0)));a=(s[:,2*r+1:]-s[:,:-2*r-1])/(2*r+1)
    p=np.pad(a,((r,r),(0,0)),mode='edge');s=np.pad(np.cumsum(p,axis=0),((1,0),(0,0)));return (s[2*r+1:]-s[:-2*r-1])/(2*r+1)
shore=np.clip((1-blur(water,5))*2,0,1)
Image.fromarray(np.uint8(np.round(np.stack([water,shore,np.zeros_like(water),np.ones_like(water)],-1)*255))).save(OUT/'T_Benmore_LakeCoverage.png')
print({'water_cells':int(water.sum()),'cell_m':10,'lake_is_visual_only':True})
