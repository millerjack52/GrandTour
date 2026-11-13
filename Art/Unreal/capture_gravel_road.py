"""Check the transferred material and LOD appearance under the game's runtime look."""
import unreal as u,json,time,traceback
from pathlib import Path
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/GravelRoadUE'
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase='load'; index=0; last=time.monotonic(); start=last
report={'ok':False,'images':[]}
def finish(error=None):
    if error:report['error']=error
    (OUT/'capture-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle)
    u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,index,shot,shot_started
    now=time.monotonic()
    try:
        if now-start>360:finish('Capture timed out');return
        if phase=='load':
            phase='loaded';last=now
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/TussockStyle/L_TussockStyle')
        elif phase=='loaded' and now-last>8:
            phase='playing';last=now;u.EditorLevelLibrary.editor_play_simulate()
        elif phase=='playing' and now-last>20:
            world=u.EditorLevelLibrary.get_game_world()
            if not world:return
            if index==0:
                report['post_mode']=u.SystemLibrary.get_console_variable_int_value('gt.Look.Post')
                report['warp_scale']=u.SystemLibrary.get_console_variable_float_value('gt.Look.WarpScale')
                report['kuwahara']=u.SystemLibrary.get_console_variable_int_value('gt.Look.Kuwahara')
                report['post_volumes']=[dict(name=a.get_actor_label(),blendables=len(a.get_editor_property('settings').weighted_blendables.array)) for a in u.GameplayStatics.get_all_actors_of_class(world,u.PostProcessVolume)]
                assert report['post_mode']==2 and report['warp_scale']==0 and report['kuwahara']==0
                assert all(v['blendables']==0 for v in report['post_volumes'])
                gravel=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='GR_ApprovedGravel')
                components=gravel.get_components_by_class(u.InstancedStaticMeshComponent)
                report['gravel_instances']=sum(c.get_instance_count() for c in components)
                report['gravel_components']=len(components)
                assert report['gravel_instances']==9523 and report['gravel_components']==4
                terrain=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_path_name().startswith('/Game/GrandTour/ArtTests/GravelRoad/SM_GR_')]
                report['terrain_materials']=[a.static_mesh_component.get_material(0).get_path_name() for a in terrain]
                assert len(terrain)==8 and all('/M_GR_Road.' in m for m in report['terrain_materials'])
            view=['Driver','Overview'][index]
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='TS_'+view)
            filename=OUT/('UE_'+view+'.png')
            phase='capturing';shot_started=time.time();report['images'].append(str(filename))
            shot=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(filename),camera=camera,delay=2)
            phase='shot';last=time.monotonic()
        elif phase=='shot' and now-last>8:
            output=Path(report['images'][-1])
            if not output.exists() or output.stat().st_mtime<shot_started:return
            index+=1
            if index==2:report['ok']=True;finish();return
            phase='playing';last=now-12
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
