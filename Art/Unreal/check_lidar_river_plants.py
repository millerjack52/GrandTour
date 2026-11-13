from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-capture-helpers>','exec'))
report=dict(ok=False,images=[])
def save():(OUT/'rs3-river-view.json').write_text(json.dumps(report,indent=2))
def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 import sys
 sys.path.insert(0,str(ROOT/'Art/Unreal'))
 import lidar_river_plant_variety as plants
 saved=[plants.tfkey(c.get_instance_transform(i,True)) for a in plants.actors.get_all_level_actors() if a.get_actor_label().startswith(plants.PREFIX) for c in a.get_components_by_class(u.InstancedStaticMeshComponent) for i in range(c.get_instance_count())]
 installed=json.loads((plants.QA/'install.json').read_text())
 assert installed['ok'] and installed['planting']['version']==plants.VERSION
 expected_count=installed['planting']['total'];expected_signature=installed['planting']['signature']
 if (OUT/'bank-planting.json').exists():
  import lidar_bank_planting as bank
  fitted=json.loads((bank.QA/'install.json').read_text());assert fitted['ok']
  expected_count=fitted['snapshot']['rs3_instances'];expected_signature=fitted['snapshot']['rs3_signature']
 if (OUT/'rocky-bank.json').exists():
  import lidar_rocky_bank as rocky
  latest=json.loads((rocky.QA/'install.json').read_text());assert latest['ok']
  expected_count=latest['bank_snapshot']['rs3_instances'];expected_signature=latest['bank_snapshot']['rs3_signature']
 assert len(saved)==expected_count and plants.digest(saved)==expected_signature,'Saved planting readback mismatch'
 report['saved_planting_verified']=True
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
 until=time.monotonic()+180
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 for cmd in json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']+['DisableAllScreenMessages','r.MotionBlurQuality 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:
  u.SystemLibrary.execute_console_command(world,cmd,pc)
 car.set_actor_location_and_rotation(u.Vector(-49200,-36100,5000),u.Rotator(),False,True)
 car.set_actor_hidden_in_game(True)
 yield from settle(10)
 yield from capture('RS3_river_overview',(-49000,-35300,5700),(-47700,-33800,4470))
 yield from capture('RS3_river_water_view',(-49800,-35200,4900),(-47600,-34000,4480))
 report['ok']=True;save();yield from finish()
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global busy,deadline,steps,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<450,'Capture timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
