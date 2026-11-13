"""Install DEM hill structure and replace only the scenery backdrop geometry."""
import unreal as u,sys,json,time,traceback,array,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreHills';DEST='/Game/GrandTour/Demo/BenmoreRoads/Hills'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build
from benmore_bank_surface import backdrop_material
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
eal=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools();mel=u.MaterialEditingLibrary
data=json.loads((OUT/'hills.json').read_text());report={'ok':False};phase='load';last=time.monotonic()
u.EditorPythonScripting.set_keep_python_script_alive(True)
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def finish(err=None):
    global phase
    phase='done';report['ok']=err is None
    if err:report['error']=err;u.log_error(err)
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='building';assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();eal.make_directory(DEST)
            if not eal.does_asset_exist('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeHills'):assert u.EditorLoadingAndSavingUtils.save_map(world,'/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeHills')
            ground=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            for mat,name in [(ground,'M_BeforeHills_Ground'),(u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Environment/M_Benmore_Backdrop'),'M_BeforeHills_Backdrop')]:
                if not eal.does_asset_exist(DEST+'/'+name):assert eal.duplicate_asset(mat.get_path_name(),DEST+'/'+name)
            for name in ['T_Benmore_HillStructure','T_Benmore_HillNormal']:
                task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
                assets.import_asset_tasks([task]);t=u.load_asset(DEST+'/'+name);assert t
                props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP,never_stream=True)
                eal.save_loaded_asset(t)
            report['surface']=build(ground);assert not mel.recompile_material(ground);eal.save_loaded_asset(ground);material=backdrop_material()
            u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0');report['meshes']=[]
            # Import and validate all new meshes before replacing saved actors.
            meshes=[]
            for part in data['parts']:
                name=part['name'];task=props(u.AssetImportTask(),filename=str(OUT/(name+'.fbx')),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True)
                opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
                props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
                task.options=opt;assets.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
                mesh.set_material(0,material);ns=mesh.get_editor_property('nanite_settings');ns.enabled=True;sm.set_nanite_settings(mesh,ns,True);eal.save_loaded_asset(mesh)
                raw=array.array('f');raw.frombytes((OUT/(name+'.f32')).read_bytes());desc=mesh.get_static_mesh_description(0);assert desc.get_vertex_count()==part['vertices']
                errors=[]
                for i in range(0,part['vertices'],max(1,part['vertices']//160)):
                    p=desc.get_vertex_position(u.VertexID(i));errors.append(max(abs(p.x-raw[3*i]*100),abs(p.y-raw[3*i+1]*100),abs(p.z-raw[3*i+2]*100)))
                assert max(errors)<.2,(name,max(errors));meshes.append(mesh)
                report['meshes'].append({'name':name,'vertices':part['vertices'],'source_checks':len(errors),'max_coordinate_error_cm':max(errors),'nanite':True})
            for a in act.get_all_level_actors():
                if a.get_actor_label().startswith('Benmore_Backdrop_') or a.get_actor_label().startswith('Benmore_Hills_'):act.destroy_actor(a)
            for mesh in meshes:
                a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(mesh.get_name().replace('SM_',''));c=a.static_mesh_component;c.set_static_mesh(mesh)
                c.set_collision_profile_name('NoCollision');a.set_actor_enable_collision(False);props(c,cast_shadow=True,receives_decals=False)
                a.set_actor_location(u.Vector(0,0,0),False,True);a.set_actor_rotation(u.Rotator(0,0,0),False);a.set_actor_scale3d(u.Vector(1,1,1))
            fog=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_DistanceHaze')
            report['previous_max_fog_opacity']=fog.component.get_editor_property('fog_max_opacity');fog.component.set_editor_property('fog_max_opacity',.52)
            report.update(triangles=data['triangles'],mesh_spacing_m=20,height_changed=False,max_fog_opacity=.52)
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>45:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
