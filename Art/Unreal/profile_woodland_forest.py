"""Repeatable fixed-camera rendering measurements; no driving or saved edits."""
import unreal as u
from pathlib import Path
import sys,json,time,traceback,shutil
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/tools'))
from benmore_profile_metrics import analyse
OUT=ROOT/'Art/Export/BenmoreWoodland';CSV=ROOT/'Saved/Profiling/CSV'
report={'ok':False,'driving_tested':False,'runs':[]};world=pc=None;busy=False
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def run():
 global world,pc
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/ArtTests/BenmoreWoodland/L_Benmore_Woodland')
 actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 report['stage']='dense' if any(a.get_actor_label().startswith('Woodland_DenseForest') for a in actors) else 'baseline'
 if any(isinstance(a,u.GTMixedGroundDetails) and a.grass_material and 'M_GrassRecovered' in a.grass_material.get_path_name() for a in actors):report['stage']+='-grass'
 if any(isinstance(a,u.GTLandscapeSurface) and a.grass_is_visual_cover for a in actors):report['stage']+='-groundstudy'
 if any(a.get_actor_label()=='Woodland_ShadowBalance' for a in actors):report['stage']+='-shadowbalanced'
 if any(isinstance(a,u.GTMixedGroundDetails) and a.distant_grass_material for a in actors):report['stage']+='-distancegrass'
 les.editor_set_viewport_realtime(False)
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 25
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0)
 sys.path.insert(0,str(ROOT/'Art/Unreal'))
 from woodland_lighting_audit import snapshot
 report['runtime_lighting']=snapshot(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
 car=u.GameplayStatics.get_player_pawn(world,0);car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
 for s in ['t.MaxFPS 0','r.VSync 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','r.MotionBlurQuality 0','DisableAllScreenMessages']:cmd(s)
 report['viewport']=list(pc.get_viewport_size());yield 20
 sites=json.loads((OUT/'authoring.json').read_text())['sites']
 for index in [1,2]:
  site=sites[index-1];x,y=site['center'];z=site['center_height_cm']
  pc.select_lane(index);car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
  p=u.Vector(x-1300,y+1450,z+280);target=u.Vector(x+150,y-150,z+90)
  cam=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,target)),'ForestProfile')
  cam.camera_component.set_field_of_view(65);pc.set_view_target_with_blend(cam,0);yield 12
  for repeat in range(3):
   distance_cover=repeat!=0;grass.distant_grass.set_visibility(distance_cover);yield 3
   before=set(CSV.glob('*.csv'));cmd('csvprofile start');yield 10;cmd('csvprofile stop');yield 4
   new=set(CSV.glob('*.csv'))-before;assert len(new)==1
   f=new.pop();dest=OUT/(report['stage']+'_'+site['name']+'_'+str(repeat)+'.csv');shutil.copy2(f,dest)
   report['runs'].append(dict(site=site['name'],repeat=repeat,distance_cover=distance_cover,near_grass=grass.grass.get_instance_count(),distant_grass=grass.distant_grass.get_instance_count(),csv=str(dest),analysis=analyse(dest)))
  cmd('HighResShot 1440x900 filename="'+(OUT/(report['stage']+'_'+site['name']+'.png')).as_posix()+'"');yield 3
  cam.destroy_actor()
 report['ok']=True
 (OUT/('forestprofile-'+report['stage']+'.json')).write_text(json.dumps(report,indent=2))
 u.EditorLevelLibrary.editor_end_play();yield 4
 les.load_level('/Engine/Maps/Entry');les.editor_set_viewport_realtime(True);yield 3
def finish():
 global world,pc,steps
 (OUT/'forestprofile.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle)
 world=pc=steps=None
 import gc
 gc.collect();u.SystemLibrary.collect_garbage();u.EditorPythonScripting.set_keep_python_script_alive(False)
steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global busy,deadline
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<800
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:finish()
 except Exception:report['error']=traceback.format_exc();u.log_error(report['error']);finish()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
