"""Export only render surfaces; leave the accepted bed and crossings untouched."""
import bpy,json
from pathlib import Path
OUT=Path(__file__).resolve().parents[2]/'Art/Export/BenmoreGaea/ShoreRefinement'
for name in ['SM_GC_RiverSurface','SM_GC_OutletSurface']:
    data=json.loads((OUT/(name+'.json')).read_text())
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(x,-y,z) for x,y,z in data['vertices']],[],[list(reversed(t)) for t in data['faces']]);mesh.update()
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    for p in mesh.polygons:p.use_smooth=True
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False)
print('BENMORE_SHORE_MESHES_OK')
