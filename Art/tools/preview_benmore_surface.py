"""Package unretouched Unreal captures and the preservation/vehicle check results."""
from pathlib import Path
import json
from PIL import Image
root=Path(__file__).resolve().parents[2]
out=root/'Art/Export/BenmoreGaea/WaterSurface_20261011'
r=json.loads((out/'install-report.json').read_text());assert r['ok'] and r['before']==r['after']
fresh=json.loads((out/'verify-report.json').read_text());assert fresh['ok']
crop=(0,330,960,600) # Water only; exclude asynchronously generated background grass.
frames=[Image.open(out/('Verified_%02d.png'%i)).convert('RGB').crop(crop) for i in range(12)]
# GIF units are 10 ms; alternate 120/130 ms to preserve the 0.125 s sampling.
frames[0].save(out/'SurfaceMotion.gif',save_all=True,append_images=frames[1:],duration=[120,130]*6,loop=0)
before=Image.open(out/'Before_00.png').convert('RGB').crop(crop)
before.save(out/'SurfaceComparison.gif',save_all=True,append_images=[frames[0]],duration=[1500,1500],loop=0)
v=json.loads((out/'vehicle-review.json').read_text());assert v['ok'] and v['fixed_dt']['ok'] and v['surface_detail_saved_assets']
rows=[x for x in v['samples'] if x['case']=='AlongRiver']
drive=[Image.open(out/('AlongRiver_%02d.png'%(i+1))).convert('RGB') for i in range(len(rows))]
durations=[round((b['t']-a['t'])*100)*10 for a,b in zip(rows,rows[1:])];durations.append(durations[-1])
drive[0].save(out/'VehicleMotion.gif',save_all=True,append_images=drive[1:],duration=durations,loop=0)
summary={'ok':True,'layout_and_physics_preserved':True,'vehicle':v['car_actor'],
    'fixed_dt':v['fixed_dt'],'cases':sorted(set(x['case'] for x in v['samples'])),
    'surface_frames':12,'surface_seconds':1.5,'surface_crop_xyxy':crop,'vehicle_frames':len(drive),'vehicle_preview_sparse':True,
    'performance_measured':False,'mesh_triangles':sum(x['faces_after'] for x in r['meshes'])}
(out/'preview-report.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
