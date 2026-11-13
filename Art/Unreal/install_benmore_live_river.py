"""Install one bounded live ford, save, reload, then inspect a fixed-time editor preview.
No driving or timing test. Backs up the map and uses review-owned assets.
"""
import unreal as u
import sys,json,time,traceback,array,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverScale'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_live_water_material import make,DEST
from benmore_river_life_materials import props
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
BACKUP='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_BeforeLiveRiver'
eal=u.EditorAssetLibrary;act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report={'ok':False,'timings_collected':False,'driving_tested':False,'model':'One fixed-bank 8192-cell river disturbance pilot','images':[]}
phase='load';last=time.monotonic();started=last;shot_index=0;sheet=None
u.EditorPythonScripting.set_keep_python_script_alive(True)

def signature():
    h=hashlib.sha256();count=0
    for a in sorted(act.get_all_level_actors(),key=lambda a:a.get_actor_label()):
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c,u.GrassInstancedStaticMeshComponent):continue
            for i in range(c.get_instance_count()):
                t=c.get_instance_transform(i,True);h.update(array.array('d',[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]).tobytes());count+=1
    return {'count':count,'sha256':h.hexdigest()}

def install():
    global sheet,camera
    assert les.load_level(LEVEL)
    if not eal.does_asset_exist(BACKUP):assert eal.duplicate_asset(LEVEL,BACKUP)
    report['backup']=BACKUP;report['instances_before']=signature()
    data=json.loads((OUT/'live-reference.json').read_text())
    path=DEST+'/DA_RS_FordReference';ref=u.load_asset(path)
    if not ref:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.GTRiverReference)
        ref=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_RS_FordReference',DEST,u.GTRiverReference,factory)
    assert ref
    for name,value in data.items():ref.set_editor_property(name,u.Vector2D(*value) if name in ['origin_cm','axis_x'] else value)
    assert eal.save_loaded_asset(ref)
    material=make()
    streams=[a for a in act.get_all_level_actors() if isinstance(a,u.StaticMeshActor) and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name() in ['SM_RL_Stream','SM_RS_StreamLive']]
    assert len(streams)==1,[a.get_actor_label() for a in streams]
    stream=streams[0]
    task=props(u.AssetImportTask(),filename=str(OUT/'SM_RS_StreamLive.fbx'),destination_path=DEST,destination_name='SM_RS_StreamLive',automated=True,replace_existing=True,save=True)
    opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,import_animations=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
    props(opt.static_mesh_import_data,combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(DEST+'/SM_RS_StreamLive');assert mesh;mesh.set_material(0,material);assert eal.save_loaded_asset(mesh)
    stream.static_mesh_component.set_static_mesh(mesh)
    report['local_mesh_refinement']=json.loads((OUT/'live-mesh-report.json').read_text())
    # Static/editor default is the baked appearance; only the live actor supplies FieldActive=1.
    stream.static_mesh_component.set_material(0,material)
    sheet=next((a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RS_LiveFord'),None)
    if not sheet:sheet=act.spawn_actor_from_class(u.GTWaterSheet,u.Vector(-66125,17750,1585.3853));sheet.set_actor_label('Benmore_RS_LiveFord')
    for key,value in dict(river_reference=ref,river_surface=stream,base_level_cm=1585.3853,field_cell_cm=37.5,max_sim_cells=8192,wind_ripple_cm=6,rain_drop_cm=.2,river_active_distance_m=100,surface_material_path=material.get_path_name(),dry_cut_cm=1).items():sheet.set_editor_property(key,value)
    sheet.set_folder_path('Benmore/RiverScale')
    assert signature()==report['instances_before']
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
    assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
    sheet=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RS_LiveFord')
    assert sheet.get_editor_property('river_reference').get_editor_property('size_x')==128
    assert sheet.get_editor_property('river_surface')
    assert signature()==report['instances_before'];report['saved_and_reloaded']=True
    camera=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Camera_Ford')
    # Low crossing camera makes actual surface displacement legible.
    camera.set_actor_location(u.Vector(-65550,17800,1780),False,False)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(-66125,17750,1585)),False)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
    sheet.preview_river(0,True)
    report['surface_before_cm']=sheet.surface_cm_at(u.Vector2D(-66125,17750))
    report['current_before_cmps']=sheet.flow_cm_per_s_at(u.Vector2D(-66125,17750)).to_tuple()

def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'live-install-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()

def tick(dt):
    global phase,last,shot_index,task
    try:
        now=time.monotonic()
        if now-started>1200:raise RuntimeError('Bounded live river setup timeout')
        if phase=='load':
            phase='installing';install();phase='warm';last=now
        elif phase=='warm' and now-last>40:
            phase='capturing';path=OUT/'LiveFord_Rest.png';task=u.AutomationLibrary.take_high_res_screenshot(1280,800,str(path),camera);report['images'].append(str(path));phase='shot';last=now
        elif phase=='shot' and now-last>4:
            assert Path(report['images'][-1]).exists()
            if shot_index==0:
                report['impulse_added_m3']=sheet.add_impulse(u.Vector2D(-66125,17750),65,4)
                sheet.preview_river(.5,False);report['surface_after_cm']=sheet.surface_cm_at(u.Vector2D(-66125,17750))
                assert abs(report['surface_after_cm']-report['surface_before_cm'])>.01
                path=OUT/'LiveFord_Disturbance.png';shot_index=1
            elif shot_index==1:
                sheet.preview_river(1,False);path=OUT/'LiveFord_Propagation.png';shot_index=2
            else:finish();return
            phase='capturing';task=u.AutomationLibrary.take_high_res_screenshot(1280,800,str(path),camera);report['images'].append(str(path));phase='shot';last=now
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
