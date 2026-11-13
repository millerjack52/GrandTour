"""Export baked water surfaces with the established Unreal axis convention."""
from pathlib import Path
import bpy,json
OUT=Path('C:/GrandTour/Art/Export/BenmoreRivers')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
data=json.loads((OUT/'assets.json').read_text())
for part in data['parts']+data['bank_parts']:
    d=json.loads((OUT/(part['name']+'.json')).read_text())
    mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata([(x,-y,z) for x,y,z in d['vertices']],[],[list(reversed(f)) for f in d['faces']]);mesh.update()
    obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj)
    for poly in mesh.polygons:poly.use_smooth=True
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    bpy.ops.export_scene.fbx(filepath=str(OUT/(part['name']+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
    obj.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Benmore_Baked_River.blend'))
print('BENMORE_RIVER_EXPORT_OK')
