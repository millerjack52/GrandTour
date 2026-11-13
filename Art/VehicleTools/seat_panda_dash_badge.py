import bpy
from pathlib import Path
P=Path('C:/GrandTour/Art/Export/VehicleTools/panda-interior-v01')
bpy.ops.wm.open_mainfile(filepath=str(P/'Panda_Assembly.blend'));s=bpy.context.scene
o=bpy.data.objects['CAB | Passenger dash badge'];o.scale*=4/7;o.location.y=-.1130*3.6;o.location.z=.309*3.6
bpy.ops.object.select_all(action='DESELECT')
for o in s.objects:
 if o.type in ['MESH','EMPTY'] and not o.name.startswith('SOURCE'):o.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/'Panda_Assembly.glb'),export_format='GLB',use_selection=True,export_apply=True,export_extras=True)
bpy.ops.export_scene.fbx(filepath=str(P/'Panda_Assembly.fbx'),use_selection=True,object_types={'MESH','EMPTY'},apply_unit_scale=True,axis_forward='-Y',axis_up='Z',add_leaf_bones=False)
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(P/'Panda_Assembly.blend'))
