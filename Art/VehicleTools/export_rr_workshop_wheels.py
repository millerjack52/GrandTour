"""Export derived runtime meshes; preserve reviewed Blender library."""
import bpy,bmesh,sys,json,math,hashlib
from pathlib import Path
from mathutils import Matrix
SOURCE=Path('C:/GrandTour/Art/Export/VehicleTools/rr-wheels-tyres-v04/GT_RangeRover_Wheel_Components.blend')
OUT=Path(sys.argv[sys.argv.index('--')+1]);OUT.mkdir(parents=True,exist_ok=False)
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));sc=bpy.context.scene;sc.unit_settings.system='METRIC';sc.unit_settings.scale_length=.01
parts=[c for c in bpy.data.collections if c.get('kind') in ['rim','tyre']]
names={'RIM | Pressed Steel':'SM_Rim_Pressed','RIM | Classic Alloy':'SM_Rim_Alloy','RIM | Heavy Duty Steel':'SM_Rim_Heavy','TYRE | Road':'SM_Tyre_Road','TYRE | All Terrain':'SM_Tyre_AllTerrain','TYRE | Mud':'SM_Tyre_Mud'}
report={'source_sha256':before,'assets':[]}
for c in parts:
    sc.collection.children.link(c)
    for o in c.objects:
        for mod in o.modifiers:
            if mod.type=='BEVEL':mod.segments=1
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();obs=[]
    for o in c.objects:
        if o.type!='MESH':continue
        me=bpy.data.meshes.new_from_object(o.evaluated_get(dg),depsgraph=dg)
        ob=bpy.data.objects.new('Export '+o.name,me);sc.collection.objects.link(ob);obs.append(ob)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();ob=bpy.context.object;ob.name=names[c.name]
    # Remove unused slots and retain native material names as deterministic import mapping.
    bpy.ops.object.material_slot_remove_unused()
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.008);bpy.ops.object.mode_set(mode='OBJECT')
    me=ob.data;me.transform(Matrix.Scale(100,4)@Matrix.Rotation(math.pi/2,4,'Z'))
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Z',axis_up='Y',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',bake_space_transform=False,use_mesh_modifiers=True,mesh_smooth_type='FACE',add_leaf_bones=False,bake_anim=False,path_mode='AUTO')
    me.calc_loop_triangles();report['assets'].append({'name':ob.name,'triangles':len(me.loop_triangles),'materials':[m.name for m in me.materials],'uv_layers':len(me.uv_layers)})
    bpy.data.objects.remove(ob,do_unlink=True);sc.collection.children.unlink(c)
assert before==hashlib.sha256(SOURCE.read_bytes()).hexdigest()
(OUT/'manifest.json').write_text(json.dumps(report,indent=2));print('EXPORT_OK')
