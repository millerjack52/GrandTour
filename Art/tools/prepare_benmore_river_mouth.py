"""Resolve the DEM at the river/lake join beyond the gameplay landscape edge."""
from pathlib import Path
import numpy as np,json,hashlib
from scipy.ndimage import distance_transform_edt,maximum_filter,minimum_filter
from PIL import Image
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreRivers'
d=np.load(OUT/'river_bake.npz');x=d['x'];y=d['y'];base=d['base'];xx,yy=np.meshgrid(x,y)
# Replace only a strip of the coarse distant terrain. Heights are the same
# source DEM as the simulation, not a new sculpt or a change in discharge.
inside=(xx>-1565)&(xx<-1250)&(yy>-15)&(yy<205)&((d['shore']<32)|(base<.65))
cells=minimum_filter(inside,size=2,origin=-1)[:-1,:-1]
vertices=[];faces=[];lookup={};origin=np.array([-1500.,0.,0.])
footprint=np.zeros_like(inside)
for j,i in np.argwhere(cells):
    ids=[]
    for a,b in [(j,i),(j,i+1),(j+1,i+1),(j+1,i)]:
        key=(a,b);footprint[a,b]=True
        if key not in lookup:
            lookup[key]=len(vertices);vertices.append((np.array([x[b],y[a],base[a,b]-.012])-origin).tolist())
        ids.append(lookup[key])
    faces.extend([[ids[0],ids[1],ids[2]],[ids[0],ids[2],ids[3]]])
water=(base<.60)&footprint
shore=distance_transform_edt(~(water|d['wet']))
rgba=np.stack([footprint.astype(float),water.astype(float),np.clip(shore/16,0,1),footprint.astype(float)],-1)
Image.fromarray(np.uint8(np.round(rgba*255))).save(OUT/'T_Benmore_RiverMouth.png')
name='SM_Benmore_RiverMouthBed'
(OUT/(name+'.json')).write_text(json.dumps(dict(vertices=vertices,faces=faces)))
report=dict(ok=True,name=name,origin_m=origin.tolist(),triangles=len(faces),vertices=len(vertices),
    source='river_bake.npz:base (the simulation source DEM)',height_offset_m=-.012,
    bake_sha256=hashlib.sha256((OUT/'river_bake.npz').read_bytes()).hexdigest(),flow_changed=False)
(OUT/'mouth-assets.json').write_text(json.dumps(report,indent=2));print(report)
