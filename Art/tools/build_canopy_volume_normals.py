"""Recover smooth crown-group normals from the captured surface depth.

Small leaf-plane normals average upward at distance. A filtered depth surface
keeps the captured bough relief without adding geometry or texture samples.
Original captures are retained; derived maps are reproducible.
"""
from pathlib import Path
import json,math,sys
import numpy as np
from scipy.ndimage import gaussian_filter,distance_transform_edt
from PIL import Image
OUT=Path('C:/GrandTour/Art/Export/LidarStudy/CanopyDepth');stats=[]
for kind in ([sys.argv[1]] if len(sys.argv)>1 else ['Mature','Pole','Edge']):
 folder=OUT/kind;data=json.loads((folder/'tree-bake.json').read_text());size=data['size_cm']
 colour=np.array(Image.open(folder/'T_PD_TreeColour.tga').convert('RGBA'))
 raw=np.array(Image.open(folder/'T_PD_TreeNormalDepth.tga').convert('RGBA'));normal=raw.copy()
 for row in range(3):
  el=math.radians(row*35)
  for col in range(8):
   az=col*math.tau/8;V=np.array([math.cos(el)*math.cos(az),math.cos(el)*math.sin(az),math.sin(el)])
   R=np.array([math.sin(az),-math.cos(az),0]);U=np.cross(R,V)
   ys=slice(row*256,(row+1)*256);xs=slice(col*256,(col+1)*256)
   c=colour[ys,xs];n=raw[ys,xs];mask=c[:,:,3]/255.
   z=(n[:,:,3]/255.-.5)*2*size
   z=gaussian_filter(z*mask,2.2)/np.maximum(.001,gaussian_filter(mask,2.2))
   dy,dx=np.gradient(z,size/256)
   surface=V[None,None,:]-dx[:,:,None]*R[None,None,:]+dy[:,:,None]*U[None,None,:]
   surface/=np.maximum(np.linalg.norm(surface,axis=2,keepdims=True),.001)
   old=n[:,:,:3]/127.5-1
   bent=surface*.78+old*.22;bent/=np.maximum(np.linalg.norm(bent,axis=2,keepdims=True),.001)
   leaf=(c[:,:,1]/np.maximum(1.,c[:,:,0])>1.15)&(mask>.35)
   result=n.copy();result[leaf,:3]=np.uint8(np.clip(bent[leaf]*.5+.5,0,1)*255+.5)
   _,idx=distance_transform_edt(mask<=.35,return_indices=True);result[:,:,:3]=result[idx[0],idx[1],:3]
   normal[ys,xs]=result
 Image.fromarray(normal).save(folder/'T_CD_VolumeNormalDepth.tga')
 stats.append(dict(kind=kind,filter_pixels=2.2,depth_surface_weight=.78,original_normal_weight=.22))
(OUT/'volume-normals.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats))
