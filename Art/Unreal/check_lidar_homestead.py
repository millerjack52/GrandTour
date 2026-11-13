"""Saved-map garage integration: real interaction trace, menu, all cars, rollback and entry."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
import sys
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_homestead as HS
QA=ROOT/'Saved/LidarAuthoringQA/HS1';report=dict(ok=False,images=[],swaps=[])
MODE=os.environ.get('GT_HS1_MODE','check')
walk_target=None
layout=json.loads((HS.OUT/'layout.json').read_text())
def save():(QA/(MODE+'.json')).write_text(json.dumps(report,indent=2))
def result_ok(r):return r[0] if isinstance(r,tuple) else r
def local(x,y,z):return u.Vector(*HS.xy(x,y),z)
def coords(v):return (v.x,v.y,v.z)
def run():
 global world,pc,car,walk_target
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 names=[a.get_actor_label() for a in refs if a.get_actor_label().startswith('LidarStudy_Homestead_')]
 assert len(names)==4,names
 assert layout['anchor_cm']==HS.SITE['anchor_cm'] and layout['placement_yaw']==HS.YAW
 for suffix,point,z in [('SM_RiversideHouse',(0,0),layout['house_datum_cm']),('SM_RiversideGarage',HS.GARAGE,layout['garage_floor_cm']),('GarageDoor',layout['door_local_cm'],layout['garage_floor_cm']+105)]:
  actor=next(a for a in refs if a.get_actor_label()=='LidarStudy_Homestead_'+suffix)
  assert (actor.get_actor_location()-local(*point,z)).length()<.1,(suffix,actor.get_actor_location())
  assert abs((actor.get_actor_rotation().yaw-HS.YAW+180)%360-180)<.01
 report['placement']=dict(anchor=HS.ANCHOR,yaw=HS.YAW,garage=HS.GARAGE)
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));assert str(author.output_digest)==layout['ground_digest']
 report['saved_actors']=names;report['ground_digest']=str(author.output_digest)
 expected_bay=local(*layout['bay_local_cm'],layout['bay_height_cm']+100)
 for route in refs:
  if not isinstance(route,u.GTMudRoute):continue
  match=re.search(r'(\d+)\s+(?:Riverside\s+)?[Hh]ouse',str(route.get_editor_property('checkpoint_labels')))
  if match:
   recovery=route.get_editor_property('recovery_points')[int(match.group(1))-1]
   assert (recovery.translation-expected_bay).length()<.1,'House recovery point inside the new buildings'
   report['house_checkpoint']=coords(recovery.translation)
 report['mesh_probe']={}
 for name in ['SM_RiversideHouse','SM_RiversideGarage','SM_HomesteadGrade']:
  mesh=u.load_asset(HS.DEST+'/'+name)
  report['mesh_probe'][name]=dict(first_vertex=coords(mesh.get_static_mesh_description(0).get_vertex_position(u.VertexID(0))),bounds=str(mesh.get_bounding_box()),collision=str(mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')))
 save()
 manifest=json.loads((HS.OUT/'manifest.json').read_text())
 for entry in manifest['models']:
  actual=report['mesh_probe'][entry['name']]['first_vertex']
  assert all(abs(a-b)<.1 for a,b in zip(actual,entry['expected_first_vertex_cm'])),(entry['name'],actual)
 assert isinstance(u.MaterialEditingLibrary.get_material_property_input_node(u.load_asset(HS.DEST+'/M_Homestead'),u.MaterialProperty.MP_BASE_COLOR),u.MaterialExpressionVertexColor),'Building colour input disconnected'
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
 until=time.monotonic()+180
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 for cmd in json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 if MODE=='views':
  pc.set_editor_property('show_drive_info',False)
  yield from capture('HS1_house_front',coords(local(*layout['front_camera_cm'])),coords(local(350,-100,layout['house_datum_cm']+200)))
  yield from capture('HS1_house_overview',coords(local(600,-2200,layout['house_datum_cm']+1400)),coords(local(400,-200,layout['house_datum_cm']+100)))
  u.SystemLibrary.execute_console_command(world,'viewmode unlit',pc)
  yield from capture('HS1_house_unlit',coords(local(600,-2200,layout['house_datum_cm']+1400)),coords(local(400,-200,layout['house_datum_cm']+100)))
  u.SystemLibrary.execute_console_command(world,'viewmode lit',pc)
  u.SystemLibrary.execute_console_command(world,'showflag.DynamicShadows 0',pc)
  u.SystemLibrary.execute_console_command(world,'r.DistanceFieldAO 0',pc)
  yield from capture('HS1_house_no_shadows',coords(local(600,-2200,layout['house_datum_cm']+1400)),coords(local(400,-200,layout['house_datum_cm']+100)))
  report['ok']=True;save();actor=route=author=refs=mesh=None;gc.collect();yield from finish();return
 garage=u.GameplayStatics.get_all_actors_of_class(world,u.GTGarage)[0]
 assert len(garage.vehicles)==12
 tf=garage.vehicle_spawn_transform
 car.set_actor_location_and_rotation(tf.translation,tf.rotation.rotator(),False,True)
 car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True);yield from settle(6)
 pc.set_editor_property('show_drive_info',False)
 yield from capture('HS1_house_front',coords(local(*layout['front_camera_cm'])),coords(local(350,-100,layout['house_datum_cm']+200)))
 yield from capture('HS1_house_overview',coords(local(600,-2200,layout['house_datum_cm']+1400)),coords(local(400,-200,layout['house_datum_cm']+100)))
 assert pc.exit_car(),'Cannot exit initial car'
 ch=pc.get_player_character();stand=local(*layout['stand_local_cm'],layout['garage_floor_cm']+100)
 ch.set_actor_location(stand,False,True);pc.set_control_rotation(u.Rotator(yaw=HS.YAW+90));pc.set_view_target_with_blend(ch,0)
 yield from settle(3)
 inter=ch.get_interaction();report['door_prompt']=inter.get_prompt();report['door_target']=inter.get_current_target().get_name() if inter.get_current_target() else None
 assert inter.get_current_target()==garage,report
 inter.set_hold_input(True);yield from settle(.5);inter.set_hold_input(False)
 assert ch.is_station_open(),'Door did not open the menu'
 report['door_interaction']=True
 car.get_boot().add('Wire',3);wire=car.get_boot().count_of('Wire')
 # Occupied bay must fail before removing or moving the outgoing car.
 blocker=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.StaticMeshActor,u.Transform(location=tf.translation+u.Vector(0,0,100)),'GarageCheckBlocker')
 bc=blocker.static_mesh_component;bc.set_mobility(u.ComponentMobility.MOVABLE);bc.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'));bc.set_collision_profile_name('BlockAll');bc.set_world_scale3d(u.Vector(2,2,2))
 ch.move_station_selection(1)
 assert not ch.act_on_station() and pc.get_car()==car and car.get_boot().count_of('Wire')==wire
 assert 'Clear the parking bay' in garage.last_message,garage.last_message
 report['occupied_bay_refusal']=garage.last_message;ch.move_station_selection(-1);blocker.destroy_actor();yield from settle(.3)
 boot=car.get_boot();capacity=boot.max_weight_kg;boot.max_weight_kg=100000
 assert boot.add('Scrap',1000)==1000
 ch.move_station_selection(1)
 assert not ch.act_on_station() and pc.get_car()==car and 'Unload the boot' in garage.last_message,garage.last_message
 report['capacity_refusal']=garage.last_message;assert boot.remove('Scrap',1000)==1000;boot.max_weight_kg=capacity;ch.move_station_selection(-1)
 # Use the same selection/act path as scroll + T, covering every fleet entry.
 for index,entry in enumerate(list(garage.vehicles)[1:]+[garage.vehicles[0]]):
  if index==11:
   for _ in range(11):ch.move_station_selection(-1)
  else:ch.move_station_selection(1)
  assert ch.act_on_station(),garage.last_message
  car=pc.get_car();assert car.get_class()==entry.vehicle_class,(car.get_class(),entry.name)
  assert not ch.act_on_station() and pc.get_car()==car,'Current vehicle row allowed duplicate collection'
  assert not pc.is_driving() and ch.get_controller()==pc and car.get_boot().count_of('Wire')==wire
  yield from settle(2.5)
  stopped_by=u.GameplayStatics.get_time_seconds(world)+12
  while car.get_velocity().length()>30:
   assert u.GameplayStatics.get_time_seconds(world)<stopped_by,('Replacement did not settle on apron',str(entry.name),car.get_velocity())
   yield from settle(.5)
  assert len(u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn))==1,'Replacement leaked a car'
  p=car.get_actor_location();assert -60<p.z-layout['garage_floor_cm']<160,(entry.name,p)
  report['swaps'].append(dict(name=str(entry.name),class_path=car.get_class().get_path_name(),height_cm=p.z,speed_cm_s=car.get_velocity().length(),wire=wire));save()
 assert pc.enter_vehicle(car),'Cannot enter replacement'
 assert pc.is_driving() and car.get_controller()==pc
 refused=pc.replace_garage_vehicle(garage.vehicles[1].vehicle_class,tf);assert not result_ok(refused)
 report['driving_swap_refused']=True
 yield from settle(.5)
 car.get_chaos_movement().set_handbrake_input(False)
 u.SystemLibrary.execute_console_command(world,'Input.+action IA_Throttle 0.6',pc)
 before=car.get_actor_location();report['drive_trace']=[]
 for _ in range(15):
  yield from settle(.2)
  mv=car.get_chaos_movement()
  report['drive_trace'].append(dict(throttle=mv.get_throttle_input(),gear=mv.get_current_gear(),speed=car.get_velocity().length(),position=coords(car.get_actor_location())))
 after=car.get_actor_location()
 u.SystemLibrary.execute_console_command(world,'Input.-action IA_Throttle',pc)
 car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
 assert max(row['throttle'] for row in report['drive_trace'])>.4,'Drive test did not reach the normal throttle input'
 report['drive_distance_cm']=(after-before).length();assert report['drive_distance_cm']>40,report
 yield from settle(4)
 # Park clear, then restore the door view with the menu open for visual review.
 car.set_actor_location_and_rotation(tf.translation,tf.rotation.rotator(),False,True)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(2)
 assert pc.exit_car();ch=pc.get_player_character();ch.set_actor_location(stand,False,True);pc.set_control_rotation(u.Rotator(yaw=HS.YAW+90));pc.set_view_target_with_blend(ch,0);yield from settle(2)
 ch.get_interaction().set_hold_input(True);yield from settle(.5);ch.get_interaction().set_hold_input(False)
 assert ch.is_station_open()
 yield from capture('HS1_garage_menu',coords(stand+u.Vector(0,0,65)),coords(garage.get_actor_location()+u.Vector(0,0,55)))
 # Walking away must close the menu; these are the actual saved map buildings.
 ch.set_actor_location(local(-500,-2400,layout['house_datum_cm']+150),False,True);yield from settle(2);assert not ch.is_station_open()
 report['walk_away_closes']=True
 # Exercise real character movement up the steps, through the railing opening,
 # along the deck, and back down. Teleport only to the starting ground landing.
 if layout.get('veranda_path_local_cm'):
  path=layout['veranda_path_local_cm'];movement=ch.get_component_by_class(u.CharacterMovementComponent)
  old_speed=movement.max_walk_speed;movement.max_walk_speed=160
  ch.set_actor_location(local(*path[0],layout['house_datum_cm']+180),False,True)
  yield from settle(2)
  samples=[dict(point=path[0],position=coords(ch.get_actor_location()))]
  for point in path[1:]+list(reversed(path[:-1])):
   walk_target=local(*point,0);until=time.monotonic()+15
   while math.hypot(ch.get_actor_location().x-walk_target.x,ch.get_actor_location().y-walk_target.y)>22:
    assert time.monotonic()<until,('Veranda walking path obstructed',point,coords(ch.get_actor_location()))
    yield .1
   walk_target=None;yield from settle(.3)
   assert not movement.is_falling(),('Unsupported veranda path',point)
   samples.append(dict(point=point,position=coords(ch.get_actor_location())))
  movement.max_walk_speed=old_speed;movement=None
  assert max(s['position'][2] for s in samples)-samples[0]['position'][2]>75,'Stairs did not lift the walking character onto the deck'
  report['veranda_walk']=samples;save()
 report['ok']=True;save()
 # Drop editor and PIE wrappers before ending play / unloading the large map.
 garage=ch=inter=author=refs=actor=route=mesh=mv=boot=bc=blocker=entry=None
 gc.collect();yield from finish()
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if walk_target is not None and pc:
  walker=pc.get_player_character()
  if walker:
   delta=walk_target-walker.get_actor_location();delta.z=0
   if delta.length()>5:walker.add_movement_input(delta/delta.length(),1.,False)
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<900,'Homestead check timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  globals()['walk_target']=None
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
