"""Create derived centimetre FBXs with car-origin pivots, UVs and deterministic material mapping."""
import bpy,sys,json,math,hashlib
from pathlib import Path
from mathutils import Matrix
SOURCE=Path(sys.argv[sys.argv.index('--')+1]).resolve();OUT=Path(sys.argv[sys.argv.index('--')+2]).resolve();OUT.mkdir(parents=True,exist_ok=False)
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest();bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.01
names={'EQUIPMENT | Roof Rack':'SM_RR_RoofRack','EQUIPMENT | Bull Bar':'SM_RR_BullBar','EQUIPMENT | Snorkel':'SM_RR_Snorkel'};report=dict(source=str(SOURCE),source_sha256=before,assets=[])
for c in [c for c in bpy.data.collections if c.get('kind')=='equipment']:
 sc.collection.children.link(c);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();obs=[]
 for o in c.objects:
  if o.type!='MESH':continue
  me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),depsgraph=dg);me.transform(o.matrix_world)
  ob=bpy.data.objects.new('Export '+o.name,me);sc.collection.objects.link(ob);obs.append(ob)
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();o=bpy.context.object;o.name=names[c.name]
 bpy.ops.object.material_slot_remove_unused();bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
 o.data.transform(Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z'));o.data.calc_loop_triangles()
 v=[(v.co.x,-v.co.y,v.co.z) for v in o.data.vertices];bounds=[[fn(p[i] for p in v) for i in range(3)] for fn in [min,max]]
 report['assets'].append(dict(name=o.name,materials=[m.name for m in o.data.materials],triangles=len(o.data.loop_triangles),uv_layers=len(o.data.uv_layers),unreal_bounds_cm=bounds))
 bpy.ops.export_scene.fbx(filepath=str(OUT/(o.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False)
 bpy.data.objects.remove(o,do_unlink=True);sc.collection.children.unlink(c)
assert before==hashlib.sha256(SOURCE.read_bytes()).hexdigest();(OUT/'manifest.json').write_text(json.dumps(report,indent=2));print('EQUIPMENT_EXPORT_OK')
