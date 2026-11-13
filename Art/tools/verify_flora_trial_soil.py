"""Compare saved Unreal soil queries with independently decoded authored maps."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path('C:/GrandTour');O=ROOT/'Art/Export/FloraDrive'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from flora_trial_evidence import audited_fingerprint
from make_mud_road import centre
r=json.loads((O/'audit-report.json').read_text());assert r['ok']
maps={k:np.asarray(Image.open(O/'LidarMud'/(k+'.png')).convert('RGBA'),dtype=float)/255 for k in ['paint','style','clay']}

def read(im,x,y):
    q=(np.array([x,y])+3150)/6300*im.shape[0]-.5
    lo=np.floor(q).astype(int);t=q-lo;hi=np.minimum(lo+1,im.shape[0]-1);lo=np.maximum(lo,0)
    return (im[lo[1],lo[0]]*(1-t[0])+im[lo[1],hi[0]]*t[0])*(1-t[1])+(im[hi[1],lo[0]]*(1-t[0])+im[hi[1],hi[0]]*t[0])*t[1]

errors={k:0. for k in ['sinkage_cap_cm','softness','wetness','grass_cover','clay_weight','cohesion']}
for row in r['soil_samples']:
    x=row['x'];y=centre(x)+row['across'];p=read(maps['paint'],x,y);s=read(maps['style'],x,y);clay=read(maps['clay'],x,y)
    expected=dict(sinkage_cap_cm=min(124,p[0]*50*r['settings']['layer_depth_scale']),softness=p[3] if p[0]>0 else 0,wetness=s[2],grass_cover=s[1],clay_weight=clay[0],cohesion=.5)
    for key,value in expected.items():errors[key]=max(errors[key],abs(row[key]-value))
assert errors['sinkage_cap_cm']<.001,errors
assert all(v<.0001 for k,v in errors.items() if k!='sinkage_cap_cm'),errors
out=dict(ok=True,sample_count=len(r['soil_samples']),max_absolute_errors=errors,trial_packages_sha256=audited_fingerprint(),scope='Saved CPU soil fields only; no wheel motion, live deformation, water dynamics or rendering tested')
(O/'soil-verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
