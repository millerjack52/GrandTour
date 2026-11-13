"""Validate the imported art scene and capture it with the actual runtime look."""
import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/MudStyleUE'
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase='load';index=0;last=time.monotonic();start=last;report={'ok':False,'images':[]}
def finish(error=None):
    if error:report['error']=error
    (OUT/'capture-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,index,shot,shot_started
    now=time.monotonic()
    try:
        if now-start>360:finish('Capture timed out');return
        if phase=='load':
            phase='loaded';last=now;assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle')
        elif phase=='loaded' and now-last>8:
            meshes=[u.load_asset('/Game/GrandTour/ArtTests/MudStyle/'+r['name']) for r in json.loads((OUT/'manifest.json').read_text())['terrain']]
            report['uv_channels']={mesh.get_name():u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_num_uv_channels(mesh,0) for mesh in meshes}
            assert all(v>=4 for v in report['uv_channels'].values())
            phase='playing';last=now;u.EditorLevelLibrary.editor_play_simulate()
        elif phase=='playing' and now-last>20:
            world=u.EditorLevelLibrary.get_game_world()
            if not world:return
            if index==0:
                report['post_mode']=u.SystemLibrary.get_console_variable_int_value('gt.Look.Post');report['warp_scale']=u.SystemLibrary.get_console_variable_float_value('gt.Look.WarpScale');report['kuwahara']=u.SystemLibrary.get_console_variable_int_value('gt.Look.Kuwahara')
                assert report['post_mode']==2 and report['warp_scale']==0 and report['kuwahara']==0
                group=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='MS_ApprovedMud');components=group.get_components_by_class(u.InstancedStaticMeshComponent)
                report['instances']=sum(c.get_instance_count() for c in components);report['components']=len(components)
                assert report['instances']==len(json.loads((OUT/'manifest.json').read_text())['placements'])
                terrain=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_path_name().startswith('/Game/GrandTour/ArtTests/MudStyle/SM_MS_')]
                report['terrain_materials']=[a.static_mesh_component.get_material(0).get_path_name() for a in terrain];assert len(terrain)==8 and all('/M_MS_Ground.' in m for m in report['terrain_materials'])
            label=['TS_Driver','MS_SurfaceDetail','TS_Overview'][index];camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()==label)
            filename=OUT/('UE_'+label+'.png');phase='capturing';shot_started=time.time();report['images'].append(str(filename));shot=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(filename),camera=camera,delay=2);phase='shot';last=time.monotonic()
        elif phase=='shot' and now-last>8:
            output=Path(report['images'][-1])
            if not output.exists() or output.stat().st_mtime<shot_started:return
            index+=1
            if index==3:report['ok']=True;finish();return
            phase='playing';last=now-12
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
