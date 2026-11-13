import bpy,json,hashlib
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/porsche-authored-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Porsche_Safari_Complete.blend'))
def records():
 out={}
 for o in bpy.context.scene.objects:
  if o.type!='MESH' or o.name.startswith('STUDIO_'):continue
  pts=[o.matrix_world@v.co for v in o.data.vertices]
  if not pts:continue
  out[o.name]={'lo':[min(p[k] for p in pts) for k in range(3)],'hi':[max(p[k] for p in pts) for k in range(3)]}
 return out
before=records();bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(P/'Porsche_Safari_Complete.glb'));after=records()
missing=sorted(set(before)-set(after));extra=sorted(set(after)-set(before))
errors={n:max(abs(before[n][t][k]-after[n][t][k]) for t in ['lo','hi'] for k in range(3)) for n in set(before)&set(after)}
report={'source_mesh_count':len(before),'reimported_mesh_count':len(after),'missing':missing,'extra':extra,'max_world_bounds_error_m':max(errors.values(),default=0),'glb_sha256':hashlib.sha256((P/'Porsche_Safari_Complete.glb').read_bytes()).hexdigest()}
report['status']='PASS' if not missing and not extra and report['max_world_bounds_error_m']<1e-5 else 'FAIL'
(P/'export-roundtrip.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2),flush=True)
