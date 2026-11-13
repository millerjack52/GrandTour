import unreal as u,time,json,traceback
from pathlib import Path
O=Path('C:/GrandTour/Art/Export/FloraDrive');world=pc=camera=None;r={}
def console(c):u.SystemLibrary.execute_console_command(world,c,pc)
def run():
 global world,pc,camera
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive');yield 2
 u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0)
 yield 2
 console('ShowHUD');console('r.ScreenPercentage 100');console('DisableAllScreenMessages')
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector(-2350,-470,210)),'Probe')
 camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(900,150,640)),False);pc.set_view_target_with_blend(camera,0)
 for mode in ['WorldNormal','Roughness','Specular']:
  console('ShowFlag.VisualizeBuffer 1');console('r.BufferVisualizationTarget '+mode)
  yield 3;console('Shot filename="'+(O/('probe_'+mode+'.png')).as_posix()+'" -nosuffix');yield 2
 u.EditorLevelLibrary.editor_end_play();world=pc=camera=None;yield 3
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');yield 2
steps=run();deadline=0
def tick(dt):
 global deadline,steps
 try:
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.collect_garbage();u.SystemLibrary.quit_editor()
 except Exception:
  (O/'probe-error.txt').write_text(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
