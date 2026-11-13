"""GS3 saved-map inspection, distance coverage, streaming/contact regression and owner views."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
# Stable camera fixture: later map checks overwrite check.json.
reference=json.loads((ROOT/'Art/Unreal/lidar_grass_check_views.json').read_text())
report=dict(ok=False,images=[])
def save():(OUT/'grasscheck.json').write_text(json.dumps(report,indent=2))

def run():
 global world,pc,car
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
 until=time.monotonic()+180
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:
   pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 for command in json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']:
  u.SystemLibrary.execute_console_command(world,command,pc)
 u.SystemLibrary.execute_console_command(world,'EnableCheats',pc)
 car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
 chase=reference['gp2c_chase'];xyz=chase['car_cm']
 car.set_actor_location_and_rotation(u.Vector(xyz[0],xyz[1],xyz[2]+100),u.Rotator(yaw=chase['car_yaw_deg']),False,True)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
 yield from settle(18)
 # Streaming is time-sliced. Slow/contended frames must not turn a fixed delay
 # into a false missing-grass failure; keep a bounded completion check.
 until=time.monotonic()+180
 while grass.streaming_consistency(False)=='busy':
  assert time.monotonic()<until,'Grass streaming did not finish within 180 seconds'
  yield from settle(1)
 report['wind_scale']=grass.grass.get_material(0).get_scalar_parameter_value('NativeGrassWindScale')
 assert report['wind_scale']>0,report
 audio=car.get_audio()
 report['vehicle_audio']=dict(muted=audio.muted,playing=audio.playing,rms=audio.render_test_block(4096))
 assert audio.muted and not audio.playing and report['vehicle_audio']['rms']==0,report['vehicle_audio']
 report['grass_report']=grass.grass_report()
 assert grass.near_grass_count()>1000 and grass.distant_grass.get_instance_count()>1000,report
 bins={str(n):0 for n in (40,80,125,150,180)}
 focus=car.get_actor_location()
 for i in range(grass.distant_grass.get_instance_count()):
  p=grass.distant_grass.get_instance_transform(i,True).translation
  dist=math.hypot(p.x-focus.x,p.y-focus.y)*.01
  for end in (40,80,125,150,180):
   if dist<=end:bins[str(end)]+=1;break
 report['far_radial_bins_m']=bins;assert bins['125']>100 and bins['150']>100,bins
 report['far_collision']=str(grass.distant_grass.get_collision_enabled())
 assert grass.distant_grass.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION
 assert not grass.distant_grass.get_editor_property('cast_shadow')
 until=time.monotonic()+120
 while grass.streaming_consistency(False)=='busy':
  assert time.monotonic()<until;yield from settle(1)
 report['near_consistency']=grass.streaming_consistency(True)
 assert report['near_consistency'].startswith('ok '),report['near_consistency']
 save()
 yield from capture('GS3_paddock_chase',chase['camera_cm'],chase['aim_cm'])
 middle=reference['lp3_captures']['Paddock_middle']
 yield from capture('GS3_paddock_ground',middle['camera_cm'],middle['target_cm'])
 yield from settle(1.3)
 yield from capture('GS3_sway_later',middle['camera_cm'],middle['target_cm'])
 assert pc.show_drive_info
 # Validate the handler/rendering here; physical F1 is checked in the foreground
 # standalone window, since hidden PIE input injection is not a keyboard test.
 pc.toggle_drive_info()
 assert not pc.show_drive_info
 yield from capture('GS3_info_hidden',middle['camera_cm'],middle['target_cm'])
 pc.toggle_drive_info()
 assert pc.show_drive_info
 report['info_toggle']=True
 report['info_toggle_method']='controller handler; physical F1 checked separately in standalone'
 # Exact-view distance-layer A/B, with the near grass and ground unchanged.
 u.SystemLibrary.execute_console_command(world,'gt.Grass.Distance 0',pc)
 yield from capture('GS3_paddock_ground_far_off',middle['camera_cm'],middle['target_cm'])
 u.SystemLibrary.execute_console_command(world,'gt.Grass.Distance 1',pc)
 yaw=math.radians(chase['car_yaw_deg']);fx,fy=math.cos(yaw),math.sin(yaw)
 yield from capture('GS3_paddock_overview',(focus.x-fx*1600,focus.y-fy*1600,focus.z+1000),(focus.x+fx*12000,focus.y+fy*12000,focus.z-100))
 before=nums(grass.grass_report())
 for i in range(13):grass.apply_review_grass_contact(u.Vector2D(focus.x+fx*500-fy*(i-6)*55,focus.y+fy*500+fx*(i-6)*55),i%2==1)
 yield from settle(2)
 after=nums(grass.grass_report());keys=['bent_a','bent_b','bent_c','removed_a','removed_b','removed_c']
 report['contact']=dict(before={k:before[k] for k in keys},after={k:after[k] for k in keys})
 assert all(after[k]>0 for k in keys),report['contact']
 yield from capture('GS3_paddock_contact',(focus.x+fx*950,focus.y+fy*950,focus.z+160),(focus.x+fx*500,focus.y+fy*500,focus.z-20))
 report['ok']=True;save();grass=mesh=audio=None;yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<900,'Grass check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
