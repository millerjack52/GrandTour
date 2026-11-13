"""Stationary saved-lighting review; no driving or asset changes."""
import unreal as u
from pathlib import Path
import json,time,traceback
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreWoodland'
report={'ok':False,'images':[],'saved_edits':False};world=None;busy=False
def run():
 global world
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/ArtTests/BenmoreWoodland/L_Benmore_Woodland')
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 25
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0)
 car=u.GameplayStatics.get_player_pawn(world,0);car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
 def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
 for s in ['t.MaxFPS 0','r.VSync 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','r.MotionBlurQuality 0','showhud']:cmd(s)
 sky=u.GameplayStatics.get_all_actors_of_class(world,u.SkyLight)[0].get_component_by_class(u.SkyLightComponent)
 pp=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.PostProcessVolume) if a.get_actor_label()=='Woodland_ShadowBalance')
 p=u.Vector(-77550,-41925,1480.1875);target=u.Vector(-76100,-43525,1290.1875)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,target)),'ShadowStudy')
 camera.camera_component.set_field_of_view(65);pc.set_view_target_with_blend(camera,0);yield 12
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
 report['grass']={'near':grass.grass.get_instance_count(),'distant':grass.distant_grass.get_instance_count()}
 assert report['grass']['distant']>5000
 # Lighting must settle while unpaused. Pause only to capture the saved look;
 # changing the sky here did not update indirect lighting as a fresh PIE did.
 u.GameplayStatics.set_game_paused(world,True)
 report['sky_flags']={k:str(sky.get_editor_property(k)) for k in ['affects_world','visible','hidden_in_game','mobility','intensity','real_time_capture','affect_global_illumination','indirect_lighting_intensity']}
 f=OUT/'Woodland_SavedLighting.png';stamp=time.time();cmd('HighResShot 1440x900 filename="'+f.as_posix()+'"')
 limit=time.monotonic()+30
 while not f.exists() or f.stat().st_mtime<stamp:assert time.monotonic()<limit;yield .3
 report['images'].append(str(f))
 for buffer in ['BaseColor','WorldNormal','AmbientOcclusion']:
  cmd('viewmode VisualizeBuffer');cmd('r.BufferVisualizationTarget '+buffer);yield 3
  f=OUT/('ShadowFixed_'+buffer+'.png');cmd('HighResShot 1440x900 filename="'+f.as_posix()+'"');yield 2
  report['images'].append(str(f))
 cmd('viewmode lit');cmd('ShowFlag.DynamicShadows 0');yield 5
 f=OUT/'ShadowFixed_no_direct_shadows.png';cmd('HighResShot 1440x900 filename="'+f.as_posix()+'"');yield 2
 report['images'].append(str(f))
 report['ok']=True
 u.GameplayStatics.set_game_paused(world,False);u.EditorLevelLibrary.editor_end_play();yield 4
 les.load_level('/Engine/Maps/Entry');les.editor_set_viewport_realtime(True);yield 3
def finish():
 (OUT/'shadowreview.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
steps=run();deadline=0
def tick(dt):
 global busy,deadline
 if busy:return
 busy=True
 try:
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:finish()
 except Exception:
  report['error']=traceback.format_exc();u.log_error(report['error']);finish()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)




