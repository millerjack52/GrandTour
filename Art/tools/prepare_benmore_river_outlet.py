"""Replace the coarse scenery under the new outlet with the same surveyed bed."""
import json,numpy as np
from scipy.ndimage import map_coordinates,distance_transform_edt
from scipy.interpolate import LinearNDInterpolator
from PIL import Image
from bake_benmore_river_life import OUT,ROOT,terrain
from prepare_benmore_river_life import exportmesh
DX=1.25;bounds=(-1580.,-330.,-1250.,800.)
x=np.arange(bounds[0],bounds[2]+.1,DX);y=np.arange(bounds[1],bounds[3]+.1,DX);xx,yy=np.meshgrid(x,y)
b=np.load(OUT/'flow-bake.npz');wet=map_coordinates(b['wet'].astype(float),[(yy-b['y'][0])/DX,(xx-b['x'][0])/DX],order=1,mode='constant')>.4
old=np.asarray(Image.open(ROOT/'Art/Export/BenmoreRivers/T_Benmore_RiverMouth.png'))[:,:,0]/255
prior=map_coordinates(old,[(yy+20),(xx+1570)],order=1,mode='constant')>.8
distance=distance_transform_edt(~wet)*DX
footprint=(distance<32)|prior
bed=terrain(xx,yy)
v=np.fromfile(ROOT/'Art/Export/BenmoreHills/SM_Benmore_Hills_West.f32',dtype='<f4').reshape(-1,3)
coarse=LinearNDInterpolator(v[:,:2],v[:,2])(xx,yy);coarse=np.where(np.isfinite(coarse),coarse,bed)
edge=distance_transform_edt(np.pad(footprint,1))[1:-1,1:-1]*DX
blend=np.clip((edge-1.25)/12,0,1);blend=blend*blend*(3-2*blend)
# Keep the native border and every wet cell exact; blend only the dry apron edge.
blend=np.maximum(blend,(xx>-1253.75).astype(float));blend=np.maximum(blend,wet.astype(float))
z=coarse*(1-blend)+(bed-.012)*blend
row=exportmesh('SM_RL_MouthBed',xx,yy,z,footprint.astype(float),.5)
lake=(bed<.60).astype(float)
rgba=np.stack([footprint,lake,wet,np.ones_like(lake)],axis=-1)
Image.fromarray(np.uint8(np.rint(rgba*255))).save(OUT/'T_RL_Mouth.png')
(OUT/'outlet-assets.json').write_text(json.dumps({'ok':True,**row,'bounds_m':bounds,'step_m':DX,'shape':list(xx.shape),'origin_m':[0,0,0],'bed_source':'Same LINZ/Gaea DEM as the flow solve','max_wet_bed_error_m':float(abs(z[wet]-bed[wet]+.012).max()),'scenery_only':True},indent=2))
print(row)
