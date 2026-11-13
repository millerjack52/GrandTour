"""Quantitative gates before importing the river life art into Unreal."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy.spatial import cKDTree
from prepare_benmore_river_life import OUT,BASE,ROOT,ground

report=json.loads((OUT/'flow-report.json').read_text());assert report['ok']
data=json.loads((OUT/'assets.json').read_text());old=np.fromfile(BASE/'candidate/H_Benmore_Gaea_2017.r16',dtype='<u2');new=np.fromfile(OUT/'H_RiverLife_2017.r16',dtype='<u2')
protect=np.load(BASE/'source/protect_2017.npy').ravel();assert np.array_equal(new[protect>=.999],old[protect>=.999]);assert np.all(new<=old)
checks={}
for row in data['meshes']:
    raw=json.loads((OUT/(row['name']+'.json')).read_text());v=np.array(raw['vertices']);f=np.array(raw['faces']);assert np.isfinite(v).all()
    area=np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]])[:,2]/2
    assert area.min()>0
    if row['name']=='SM_RL_Stream':
        points=np.concatenate([v,v[f].mean(axis=1)]);d=points[:,2]-ground(points[:,0],points[:,1]);assert d.min()>=-.003,float(d.min())
        checks[row['name']]={'vertices':len(v),'triangles':len(f),'minimum_clearance_m':float(d.min()),'max_clearance_m':float(d.max())}
    else:checks[row['name']]={'vertices':len(v),'triangles':len(f)}
    if row['name']=='SM_RL_Outlet':assert v[:,0].max()<=-1250+1e-6
ford=next(c for c in data['crossings'] if c['name']=='Ford');bridge=next(c for c in data['crossings'] if c['name']=='Footbridge')
assert ford['water_depth_m']<.34 and ford['sampled_bank_grade_p95']<.27
assert bridge['span_m']<=9
for p in data['paths']:
    assert p['grade_p95']<.28,p
    assert p['grade_max']<(.20 if p['name'].startswith('Ford') else .28),p
result={'ok':True,'flow_validation':report['validation'],'geometry':checks,'protected_height_samples_unchanged':True,'raised_terrain_samples':int(np.count_nonzero(new>old)),'cut_samples':int(np.count_nonzero(new<old)),'maximum_cut_m':float(np.max((old.astype(float)-new)/64)),'ford':ford,'footbridge':bridge,'approach_grades':[{k:p[k] for k in ['name','grade_p95','grade_max']} for p in data['paths']]}
(OUT/'geometry-report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
