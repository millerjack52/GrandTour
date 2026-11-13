import bpy,json
from pathlib import Path
out=Path('C:/GrandTour/Art/Export/BenmoreGaea/RiverScale')
d=json.loads((out/'SM_RS_StreamLive.json').read_text())
bpy.ops.object.select_all(action='DESELECT')
mesh=bpy.data.meshes.new('SM_RS_StreamLive')
mesh.from_pydata([(x,-y,z) for x,y,z in d['vertices']],[],[list(reversed(f)) for f in d['faces']]);mesh.update()
obj=bpy.data.objects.new('SM_RS_StreamLive',mesh);bpy.context.collection.objects.link(obj)
for p in mesh.polygons:p.use_smooth=True
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(out/'SM_RS_StreamLive.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
