"""Stationary contact regression: drop into mud, sample suspension; never drive."""
import unreal as u
import json,time,math,traceback,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudRoad/NativeStage4'
sys.path.insert(0,str(ROOT/'Art/tools'));from make_mud_road import centre,heading
report=dict(ok=False,cases=[]);world=pc=car=None
def save():(OUT/'suspension-report.json').write_text(json.dumps(report,indent=2))
def run():
 global world,pc,car
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/MudRoad/L_MudRoad')
 u.GTPlayWindowLibrary.request_play_in_new_window(960,540);yield 10
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
 u.SystemLibrary.execute_console_command(world,'t.MaxFPS 60',pc)
 car.disable_input(pc);move=car.get_chaos_movement();move.set_handbrake_input(True)
 for label,x in [('entry',-2200),('dip',650),('dip_edge',850),('churned_dip',650)]:
  if label=='churned_dip':
   # Pre-deform the physical field without moving the car: regression for a
   # rut floor more than 50 cm below the underlying landscape collision.
   surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
   for xx in range(300,1001,50):
    for yy in range(-250,251,50):
     for _ in range(80):surface.apply_review_native_contact(u.Vector2D(xx,centre(xx)+yy),1.)
   surface=None
  car.set_actor_location_and_rotation(u.Vector(x,centre(x),100),u.Rotator(yaw=heading(x)),False,True)
  case=dict(name=label,frames=[]);report['cases'].append(case)
  began=u.GameplayStatics.get_time_seconds(world)
  while u.GameplayStatics.get_time_seconds(world)-began<12:
   frame=dict(t=u.GameplayStatics.get_time_seconds(world)-began,z=car.get_actor_location().z,vz=car.get_velocity().z,wheels=[])
   for i,w in enumerate(move.wheels):
    traction=car.get_traction().wheels[i]
    frame['wheels'].append(dict(contact=not w.is_in_air(),offset=w.get_suspension_offset(),z=traction.contact_point.z,water_cm=traction.water_depth_m*100))
   case['frames'].append(frame);yield 0
  settled=[f for f in case['frames'] if f['t']>6]
  case['offset_range_cm']=[max(f['wheels'][i]['offset'] for f in settled)-min(f['wheels'][i]['offset'] for f in settled) for i in range(4)]
  case['contact_changes']=[sum(a['wheels'][i]['contact']!=b['wheels'][i]['contact'] for a,b in zip(settled,settled[1:])) for i in range(4)]
  case['contact_fraction']=[sum(f['wheels'][i]['contact'] for f in settled)/len(settled) for i in range(4)]
  case['peak_vz_cm_s']=max(abs(f['vz']) for f in settled)
  case['native']=move.native_substance_report();save()
 move=None;report['ok']=True;save();yield from finish()
def finish():
 global world,pc,car
 u.EditorLevelLibrary.editor_end_play();yield 4
 world=pc=car=None
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
steps=run();deadline=0;busy=False;began=time.monotonic()
def tick(dt):
 global deadline,busy,steps
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<240
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error']);steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
