"""Export the high-resolution mouth bed using the established axis convention."""
from pathlib import Path
import bpy,json
OUT=Path('C:/GrandTour/Art/Export/BenmoreRivers');part=json.loads((OUT/'mouth-assets.json').read_text());name=part['name']
d=json.loads((OUT/(name+'.json')).read_text());bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-y,z) for x,y,z in d['vertices']],[],[list(reversed(f)) for f in d['faces']]);mesh.update()
obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
for p in mesh.polygons:p.use_smooth=True
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
print('BENMORE_RIVER_MOUTH_EXPORT_OK')
