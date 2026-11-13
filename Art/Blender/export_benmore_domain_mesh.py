import bpy,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'
for name in ['SM_RS_RiverSurface','SM_RS_OutletSurface']:
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    d=json.loads((OUT/(name+'.json')).read_text())
    mesh=bpy.data.meshes.new(name);mesh.from_pydata([(x,-y,z) for x,y,z in d['vertices']],[],[list(reversed(t)) for t in d['faces']]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
    for poly in mesh.polygons:poly.use_smooth=True
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False)
print('WATER_DOMAIN_MESHES_EXPORTED')
