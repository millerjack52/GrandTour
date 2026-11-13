import bpy,json
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v01')
if (P/'delivery-manifest.json').exists():raise RuntimeError('Protected delivery')
bpy.ops.wm.open_mainfile(filepath=str(P/'Panda_Assembly.blend'));s=bpy.context.scene
assert not s.get('panda_steering_view_refined')
changed=[]
for o in s.objects:
 if o.get('panda_cabin') and any(o.name.startswith('CAB | '+k) for k in ['Steering','Column stalk','Stalk grip','Ignition']):o.location.z-=.012*3.6;changed.append(o.name)
s['panda_steering_view_refined']=True
bpy.ops.object.select_all(action='DESELECT')
for o in s.objects:
 if o.type in ['MESH','EMPTY'] and not o.name.startswith('SOURCE'):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/'Panda_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(P/'Panda_Assembly.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(P/'Panda_Assembly.blend'))
r=json.loads((P/'interior-manifest.json').read_text());r['driver_view_refinement']={'steering_lowered_m':.0432,'parts':changed,'reason':'Clear view of instrument dial above steering rim'};(P/'interior-manifest.json').write_text(json.dumps(r,indent=2))
