"""Export sharp, terrain-fitted schist formations in the existing FBX convention."""
from pathlib import Path
import bpy,json
OUT=Path('C:/GrandTour/Art/Export/BenmoreComposition')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for part in json.loads((OUT/'outcrops.json').read_text())['parts']:
    d=json.loads((OUT/(part['name']+'.json')).read_text())
    verts=[(x,-y,z) for x,y,z in d['vertices']]
    mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(verts,[],[list(reversed(p)) for p in d['faces']]);mesh.update()
    attr=mesh.color_attributes.new(name='Formation',type='FLOAT_COLOR',domain='POINT')
    for c,v in zip(attr.data,d['colors']):c.color=v
    obj=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    for p in mesh.polygons:p.use_smooth=False
    bpy.ops.export_scene.fbx(filepath=str(OUT/(part['name']+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,colors_type='LINEAR')
    obj.select_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Benmore_Composition_Schist.blend'))
print('BENMORE_COMPOSITION_EXPORT_OK')
