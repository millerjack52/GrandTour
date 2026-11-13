"""Temporary PIE A/B switches; never saves the map or quality settings."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
report=dict(ok=False,tests={});wall_samples=[];sampling=False;last_wall=None
def save():(OUT/'riverperf.json').write_text(json.dumps(report,indent=2))
def wall_wait(seconds):
 end=time.monotonic()+seconds
 while time.monotonic()<end:yield .01
def measure():
 global sampling,last_wall
 wall_samples.clear();last_wall=None;sampling=True;yield from wall_wait(8);sampling=False
 s=sorted(wall_samples);return dict(frames=len(s),mean_ms=1000*sum(s)/max(1,len(s)),p95_ms=1000*s[min(len(s)-1,int(.95*len(s)))] if s else None)
def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy');les.editor_set_viewport_realtime(False)
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 until=time.monotonic()+180
 while not world or not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 r=json.loads((OUT/'authoring-reference.json').read_text())['river_points_cm'];p=r[3352];t=r[3330]
 car.set_actor_location_and_rotation(u.Vector(p[0],p[1],p[2]+85),u.Rotator(),False,True)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector(p[0],p[1],p[2]+190),rotation=u.MathLibrary.find_look_at_rotation(u.Vector(p[0],p[1],p[2]+190),u.Vector(t[0],t[1],t[2]+40))),'RiverPerf')
 pc.set_view_target_with_blend(camera,0);car.set_actor_hidden_in_game(True);yield from wall_wait(8)
 actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor);detail=[a for a in actors if a.get_actor_label().startswith('LidarStudy_RiverDetail_')]
 sheet=next(a for a in actors if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'));surfaces=list(sheet.get_editor_property('domain_surfaces'))
 report['tests']['baseline_car_hidden']=yield from measure();save()
 car.set_actor_hidden_in_game(False);yield from wall_wait(3);report['tests']['car_visible']=yield from measure();save()
 car.set_actor_hidden_in_game(True)
 for a in detail:a.set_actor_hidden_in_game(True)
 yield from wall_wait(3);report['tests']['new_dressing_hidden']=yield from measure();save()
 for a in detail:a.set_actor_hidden_in_game(False)
 for a in surfaces:a.set_actor_hidden_in_game(True)
 yield from wall_wait(3);report['tests']['water_hidden']=yield from measure();save()
 for a in surfaces:a.set_actor_hidden_in_game(False)
 quality=u.SystemLibrary.get_console_variable_int_value('r.ShadowQuality');report['original_shadow_quality']=quality
 u.SystemLibrary.execute_console_command(world,'r.ShadowQuality 0',pc);yield from wall_wait(3);report['tests']['shadows_off']=yield from measure();save()
 u.SystemLibrary.execute_console_command(world,'r.ShadowQuality '+str(quality),pc)
 # The new material mask is a parameter on the live visual grid's MID.
 black=u.load_asset('/Engine/EngineResources/Black');changed=[]
 for a in actors:
  for c in a.get_components_by_class(u.MeshComponent):
   for i in range(c.get_num_materials()):
    m=c.get_material(i)
    if isinstance(m,u.MaterialInstanceDynamic):
     getter=getattr(m,'get_texture_parameter_value',None) or getattr(m,'k2_get_texture_parameter_value',None)
     texture=getter('RR1Mask') if getter else None
     if texture:changed.append((m,texture));m.set_texture_parameter_value('RR1Mask',black)
 yield from wall_wait(3);report['tests']['live_gravel_mask_off']=yield from measure();report['changed_mids']=len(changed);save()
 for m,t in changed:m.set_texture_parameter_value('RR1Mask',t)
 car.set_actor_hidden_in_game(False);report['ok']=True;save();actors=detail=surfaces=sheet=changed=m=t=None
 yield from finish()
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed,last_wall
 now=time.monotonic()
 if sampling:
  if last_wall is not None:wall_samples.append(now-last_wall)
  last_wall=now
 if busy:return
 busy=True
 try:
  assert now-began<900
  if now>=deadline:deadline=now+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
