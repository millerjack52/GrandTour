"""Validate the generated creek mesh against the exact returned landscape."""
import json
import numpy as np
from scipy.spatial import cKDTree
from convert_benmore_gaea import OUT,sha

data=OUT/'integration';meta=json.loads((data/'assets.json').read_text())
raw=json.loads((data/'SM_Benmore_GaeaCreeks.json').read_text());v=np.array(raw['vertices']);f=np.array(raw['faces'])
h=np.fromfile(OUT/'candidate/height_local_south_up.f32',dtype='<f4').reshape(2017,2017)
def height(p):
    x=(p[:,0]+1250)/2500*2016;y=(p[:,1]+1250)/2500*2016;i=x.astype(int);j=y.astype(int);a=x-i;b=y-j
    q,r,s,t=h[j,i],h[j,i+1],h[j+1,i],h[j+1,i+1]
    return np.where(a>=b,q+(r-q)*a+(t-r)*b,q+(t-s)*a+(s-q)*b)
centres=v[f].mean(axis=1);check=np.concatenate([v,centres]);clearance=check[:,2]-height(check)
assert np.isfinite(v).all() and np.min(clearance)>.04 and np.max(clearance)<.21
area=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2]/2
assert np.all(area>0)
routes=json.loads((OUT.parent/'BenmoreRoads/road-manifest.json').read_text())['routes'];road=[]
for route in routes:
    points=np.array([[p['x_m'],p['y_m']] for p in route['points']]);d=cKDTree(points).query(v[:,:2])[0]-route['width_m']/2-1.1
    road.append(float(d.min()))
assert min(road)>10
report={'ok':True,'vertices':len(v),'triangles':len(f),'support_samples':len(check),
        'water_clearance_min_m':float(clearance.min()),'water_clearance_max_m':float(clearance.max()),
        'water_footprint_area_m2':float(area.sum()),'minimum_road_edge_clearance_m':min(road),
        'candidate_sha256':sha(OUT/'candidate/H_Benmore_Gaea_2017.r16'),
        'scope':'Shallow terrain-fitted water preview, no hydraulic/vehicle simulation',
        'no_raised_bank_meshes':True}
assert report['candidate_sha256']==meta['height_sha256']
(data/'geometry-validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
