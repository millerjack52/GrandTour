"""Export the returned Gaea channel preview using the established Unreal axes."""
from pathlib import Path
import bpy,json
OUT=Path('C:/GrandTour/Art/Export/BenmoreGaea/integration')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
name='SM_Benmore_GaeaCreeks';d=json.loads((OUT/(name+'.json')).read_text())
mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-y,z) for x,y,z in d['vertices']],[],[list(reversed(f)) for f in d['faces']]);mesh.update()
obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
for poly in mesh.polygons:poly.use_smooth=True
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Benmore_GaeaCreeks.blend'))
print('BENMORE_GAEA_CREEKS_EXPORTED')
