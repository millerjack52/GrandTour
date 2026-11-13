"""Trace the user-identified northern valley from the original LiDAR drainage.
The sketch chooses a branch only; none of its pixels become channel geometry.
Run inspect_lidar_channels.py first. This changes reference data, never the DEM.
"""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw
from shapely.geometry import LineString,mapping
D=Path('Art/Export/LidarStudy');R=D/'Reference'
z=np.load(R/'drainage-2m.npz');h=z['h'];filled=z['filled'];receiver=z['receiver'];acc=z['acc'];order=z['order'];ny,nx=h.shape
xx,yy=np.meshgrid(-1817.5+np.arange(nx)*2,-1849.5+np.arange(ny)*2)
# Broad valley gate north of the tributary junction. The DEM chooses the cell.
# Previously choosing the largest contributor upstream from the house selected
# the eastern tributary. A valley identifier is necessary at that junction.
gate=(xx>-500)&(xx<-150)&(yy>-1650)&(yy<-1500)
seed=int(np.where(gate,acc,0).argmax())
children={}
for k in order:
 p=int(receiver[k])
 if p>=0 and (p not in children or acc.ravel()[k]>acc.ravel()[children[p]]):children[p]=int(k)
up=[];k=seed
while k in children:
 k=children[k];up.append(k)
 # Stop at an inferred headwater instead of drawing tiny hillslope drainage.
 if acc.ravel()[k]<20000:break
path=[];k=seed
while k>=0:path.append(k);k=int(receiver[k])
path=np.array(list(reversed(up))+path,dtype=int)
pts=np.stack([xx.ravel()[path],yy.ravel()[path]],-1)
# Sub-cell simplification only. No Gaussian smoothing across channel bends.
g=LineString(pts).simplify(.65,preserve_topology=True)
assert g.is_simple and g.bounds[2]<0, 'Wrong eastern branch selected'
house=np.array([-522.6444549,-262.5674983]);house_distance=float(np.linalg.norm(pts-house,axis=1).min());assert house_distance<100
fill=filled.ravel()[path]-h.ravel()[path]
# Conditioning resolves local pits; it is a diagnostic, NEVER applied to the map.
# More than 1m of filling means the channel/structure needs local review.
uncertain=[];start=None
for i,v in enumerate(np.r_[fill>1.,False]):
 if v and start is None:start=i
 if not v and start is not None:
  if i-start>=3:uncertain.append(dict(start_index=start,end_index=i-1,max_conditioning_m=float(fill[start:i].max()),coordinates=pts[start:i].tolist()))
  start=None
props=dict(kind='river',name='Waimeamea northern valley',source='LiDAR drainage',accuracy='2m D8 drainage from original 1m LiDAR; northern branch selected from user valley identification. Not surveyed bathymetry.',method='Steepest descent with priority-flood flat routing; no sketch geometry; maximum 0.65m simplification',uncertain_reaches=len(uncertain))
f=R/'aligned-features.json';data=json.loads(f.read_text());data['features']=[v for v in data['features'] if v['properties'].get('source')!='LiDAR drainage'];data['features'].append(dict(type='Feature',properties=props,geometry=mapping(g)));f.write_text(json.dumps(data))
report=dict(ok=True,seed=[float(xx.ravel()[seed]),float(yy.ravel()[seed])],seed_catchment_m2=float(acc.ravel()[seed]),length_m=g.length,bounds=g.bounds,house_distance_m=house_distance,points=len(g.coords),dem_analysis_spacing_m=2,source_spacing_m=1,sketch_used_for='branch identification only',terrain_modified=False,conditioning_max_m=float(fill.max()),conditioning_p90_m=float(np.percentile(fill,90)),uncertain_reaches=uncertain)
(R/'drainage-report.json').write_text(json.dumps(report,indent=2))
im=Image.open(R/'registered-aerial.jpg');dr=ImageDraw.Draw(im)
def px(x,y):return ((x+1818.533589)/3637.067178*2048,(y+1850.5)/3701*2084)
dr.line([px(x,y) for x,y in g.coords],fill='#51d6ed',width=3)
for reach in uncertain:dr.line([px(x,y) for x,y in reach['coordinates']],fill='#ff964f',width=4)
for feature in data['features']:
 if feature['properties'].get('source')=='priority aerial' and feature['properties']['kind']=='road':dr.line([px(x,y) for x,y in feature['geometry']['coordinates']],fill='#f5c672',width=3)
a=px(*house);dr.ellipse((a[0]-7,a[1]-7,a[0]+7,a[1]+7),fill='red')
im.save(R/'priority-alignment.png')
# Legible hillshade review around the valley and priority access road.
gy,gx=np.gradient(h,2);shade=np.clip(.58-.30*gx+.38*gy,0,1);im=Image.fromarray(np.uint8(np.stack([shade*.90,shade*.95,shade],-1)*255));dr=ImageDraw.Draw(im)
def p2(x,y):return ((x+1817.5)/2,(y+1849.5)/2)
dr.line([p2(x,y) for x,y in g.coords],fill='#30d4f0',width=3)
for reach in uncertain:dr.line([p2(x,y) for x,y in reach['coordinates']],fill='#ff964f',width=3)
for feature in data['features']:
 if feature['properties'].get('source')=='priority aerial' and feature['properties']['kind']=='road':dr.line([p2(x,y) for x,y in feature['geometry']['coordinates']],fill='#f5c672',width=2)
a=p2(*house);dr.ellipse((a[0]-5,a[1]-5,a[0]+5,a[1]+5),fill='red');dr.text((a[0]+8,a[1]),'House',fill='white')
im.crop((480,0,1000,1300)).save(R/'terrain-course-review.png')
print(json.dumps({k:v for k,v in report.items() if k!='uncertain_reaches'},indent=2));print('Review reaches:',len(uncertain))
