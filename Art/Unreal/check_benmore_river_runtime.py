"""Focused retry of live-patch imagery after saved-map and collision checks passed."""
import unreal as u,json,time,traceback,hashlib
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreGaea/RiverLife';act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'runtime-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,gameworld,capture,rt,camera,gm,task
    try:
        now=time.monotonic()
        if phase=='load':
            phase='loading';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            lake=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverLife/M_RL_Lake')
            for n in u.MaterialEditingLibrary.get_material_expressions(lake):
                if isinstance(n,u.MaterialExpressionCustom):
                    code=n.get_editor_property('code')
                    if 'grad*.045,1' in code:n.set_editor_property('code',code.replace('grad*.045,1','grad*.045*(1-smoothstep(40,250,length(Camera-P)*.01)),1'))
            assert not u.MaterialEditingLibrary.recompile_material(lake);assert u.EditorAssetLibrary.save_loaded_asset(lake)
            vista=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Camera_Long_Vista');u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(vista.get_actor_location(),vista.get_actor_rotation());camera=vista;phase='start' if (OUT/'Ford_LivePatches.png').exists() else 'vista';last=now
        elif phase=='vista' and now-last>25:
            task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(OUT/'Long_Vista.png'),camera);phase='start';last=now
        elif phase=='start' and now-last>5:
            camera=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Camera_Ford');a=act.spawn_actor_from_class(u.SceneCapture2D,camera.get_actor_location(),camera.get_actor_rotation());a.set_actor_label('RL_RuntimeCapture');gm=world.get_world_settings().get_editor_property('default_game_mode');world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase);u.EditorLevelLibrary.editor_play_simulate();phase='warm';last=now
        elif phase=='warm' and now-last>15:
            gameworld=u.EditorLevelLibrary.get_game_world();assert gameworld
            rows=[]
            for p in u.GameplayStatics.get_all_actors_of_class(gameworld,u.GTMudPatch):
                row={'cap_cm':p.profile_max_sinkage_m*100,'hole_slot':p.hole_slot,'ground_misses':p.mesh_ground_misses,'material_loaded':bool(p.get_editor_property('bMaterialLoaded')),'vertices':p.mesh_vertex_count};assert row['material_loaded'] and row['ground_misses']==0 and row['vertices']>100;rows.append(row)
            assert len(rows)==2 and sorted(r['hole_slot'] for r in rows)==[0,1];report['patches']=rows
            capture=next(a for a in u.GameplayStatics.get_all_actors_of_class(gameworld,u.SceneCapture2D) if a.get_actor_label()=='RL_RuntimeCapture');rt=u.RenderingLibrary.create_render_target2d(gameworld,1440,900,u.TextureRenderTargetFormat.RTF_RGBA8);c=capture.get_components_by_class(u.SceneCaptureComponent2D)[0]
            for k,v in dict(texture_target=rt,capture_source=u.SceneCaptureSource.SCS_FINAL_COLOR_LDR,fov_angle=70.,capture_every_frame=True,always_persist_rendering_state=True).items():c.set_editor_property(k,v)
            c.capture_scene();phase='photo';last=now
        elif phase=='photo' and now-last>8:
            capture.get_components_by_class(u.SceneCaptureComponent2D)[0].capture_scene();report['first_game_time']=u.GameplayStatics.get_time_seconds(gameworld);phase='export_first';last=now
        elif phase=='export_first' and now-last>.5:
            u.RenderingLibrary.export_render_target(gameworld,rt,str(OUT),'Ford_LivePatches.png');phase='later';last=now
        elif phase=='later' and now-last>1.7:
            capture.get_components_by_class(u.SceneCaptureComponent2D)[0].capture_scene();report['second_game_time']=u.GameplayStatics.get_time_seconds(gameworld);phase='export_second';last=now
        elif phase=='export_second' and now-last>.5:
            u.RenderingLibrary.export_render_target(gameworld,rt,str(OUT),'Ford_LivePatches_Later.png');report['images']=['Ford_LivePatches.png','Ford_LivePatches_Later.png'];report['motion_interval_s']=report['second_game_time']-report['first_game_time']
            for name in report['images']:assert (OUT/name).exists() and (OUT/name).stat().st_size>1000
            report['distinct_frames']=hashlib.sha256((OUT/report['images'][0]).read_bytes()).digest()!=hashlib.sha256((OUT/report['images'][1]).read_bytes()).digest();assert report['distinct_frames'] and report['motion_interval_s']>.01
            u.EditorLevelLibrary.editor_end_play();phase='restore';last=now
        elif phase=='restore' and now-last>5:
            world.get_world_settings().set_editor_property('default_game_mode',gm);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview');finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
