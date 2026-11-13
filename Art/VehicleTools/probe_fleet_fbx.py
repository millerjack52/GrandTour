import bpy,json
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
p=Path('C:/GrandTour/Art/Export/VehicleTools/new-cars-unreal-v01/CraftedUtility/manifest.json');d=json.loads(p.read_text());part=d['parts'][3]
bpy.ops.import_scene.fbx(filepath=part['file'])
for o in bpy.context.selected_objects:
 if o.type=='MESH':
  v=[o.matrix_world@v.co for v in o.data.vertices];print('PROBE',o.name,'matrix',list(o.matrix_world),'bounds',[[min(vv[i] for vv in v) for i in range(3)],[max(vv[i] for vv in v) for i in range(3)]],'expected',part['bounds_local_cm'])
