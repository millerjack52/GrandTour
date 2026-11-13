"""Pad empty UV atlas gutters; preserve every occupied source colour texel."""
from pathlib import Path
from PIL import Image
import numpy as np,json
root=Path(__file__).resolve().parents[2]/'Art/Export/LidarStudy/FloraMatch'
report=[]
for p in root.glob('FP_*_Colour.png'):
 im=Image.open(p).convert('RGB');a=np.asarray(im).copy();original=a.copy()
 occupied=np.any(a>0,axis=-1);valid=occupied.copy()
 for _ in range(16):
  sums=np.zeros(a.shape,dtype=np.uint32);counts=np.zeros(valid.shape,dtype=np.uint8)
  for dy,dx in [(0,1),(0,-1),(1,0),(-1,0),(1,1),(-1,-1),(1,-1),(-1,1)]:
   shifted=np.roll(a,(dy,dx),(0,1));mask=np.roll(valid,(dy,dx),(0,1))
   if dy>0:mask[:dy]=False
   elif dy<0:mask[dy:]=False
   if dx>0:mask[:,:dx]=False
   elif dx<0:mask[:,dx:]=False
   sums+=shifted*mask[...,None];counts+=mask
  fill=(~valid)&(counts>0)
  if not fill.any():break
  a[fill]=(sums[fill]/counts[fill,None]).round().astype(np.uint8);valid|=fill
 assert np.array_equal(a[occupied],original[occupied])
 Image.fromarray(a).save(p)
 report.append({'file':p.name,'occupied_texels_unchanged':True,'padded_texels':int((valid&~occupied).sum())})
(root/'atlas-padding.json').write_text(json.dumps(report,indent=2))
print(report)
