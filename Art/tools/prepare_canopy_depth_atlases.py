"""Dilate each captured view independently, including depth, before mip filtering."""
from pathlib import Path
import sys,json
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
folder=Path(sys.argv[1])
c=np.asarray(Image.open(folder/'T_PD_TreeColour.tga').convert('RGBA')).copy()
n=np.asarray(Image.open(folder/'T_PD_TreeNormalDepth.tga').convert('RGBA')).copy()
stats=[]
for row in range(3):
 for col in range(8):
  ys=slice(row*256,(row+1)*256);xs=slice(col*256,(col+1)*256)
  cc=c[ys,xs];nn=n[ys,xs];mask=cc[:,:,3]>.35*255
  _,idx=distance_transform_edt(~mask,return_indices=True)
  cc[:,:,:3]=cc[idx[0],idx[1],:3];nn[:,:,:]=nn[idx[0],idx[1],:]
  stats.append(float(mask.mean()))
Image.fromarray(c).save(folder/'T_PD_TreeColour.tga')
Image.fromarray(n).save(folder/'T_PD_TreeNormalDepth.tga')
(folder/'dilation.json').write_text(json.dumps(dict(coverage=stats,dimensions=[2048,1024])))
