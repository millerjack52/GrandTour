import bpy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreGaea/ChannelPilot'
name='SM_CP_RiverSurface';data=json.loads((OUT/(name+'.json')).read_text())
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-y,z) for x,y,z in data['vertices']],[],[list(reversed(t)) for t in data['faces']]);mesh.update()
obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
for p in mesh.polygons:p.use_smooth=True
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False)
print('CHANNEL_PILOT_MESH_EXPORTED')
