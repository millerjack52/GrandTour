"""Authoring regressions and stationary checks. No test driving."""
import unreal as u
from pathlib import Path
import json,time,traceback,hashlib,math,gc,re
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround';BASE='/Game/GrandTour/ArtTests/ProceduralGround';LEVEL=BASE+'/L_BigMountain_Authoring'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.EditorAssetLibrary
data=json.loads((OUT/'install.json').read_text());report=dict(ok=False,driving_tested=False,images=[]);busy=False;world=pc=car=camera=None
def save():(OUT/'check.json').write_text(json.dumps(report,indent=2))
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:yield 0
def timed_rebuild(author):
 start=time.monotonic();assert author.rebuild(),author.last_message
 return dict(seconds=time.monotonic()-start,digest=author.output_digest,changed=author.changed_cells,retained=author.retained_cells,instances=author.instance_count)
def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,u.Vector(*target))),'AuthoringReview')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65);pc.set_view_target_with_blend(camera,0);yield from settle(3)
 path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 end=time.monotonic()+30
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<end;yield .3
 u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));save()
def run():
 global world,pc,car
 assert les.load_level(LEVEL);ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(ew,'Automation RunTests GrandTour.Authoring.NativeOracle')
 until=time.monotonic()+150
 while True:
  log=(ROOT/'Saved/Logs/ProceduralGround-Check.log').read_text(errors='replace')
  if re.search(r'Test Completed\. Result=\{\w+\} Name=\{NativeOracle\}',log):break
  assert time.monotonic()<until,'Native oracle timed out before a completion event'
  yield .5
 assert re.search(r'Test Completed\. Result=\{Success\} Name=\{NativeOracle\} Path=\{GrandTour.Authoring.NativeOracle\}',log),'Native arithmetic oracle did not pass; inspect automation log'
 report['native_oracle']=True
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));road=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralRoad))
 # Persist the calibrated study preset; generation itself uses editable rules.
 rules=list(author.scatter_rules);forest=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='BigMountain_Forest')
 fir=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Fir_0')
 rules[0].material_overrides=list(fir.get_materials());rules[1].mesh_height_cm=145.
 bush=rules[1].meshes[0];rules[1].material_overrides=[u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/Understory/MI_BirchBush') if any(s in bush.get_material(i).get_name().lower() for s in ['leaf','leave','foliage']) else bush.get_material(i) for i in range(bush.get_num_sections(0))]
 rules[2].material_overrides=[u.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeStage4/M_NativeClod')];author.scatter_rules=rules
 report['preset_materials']=[[m.get_path_name() if m else None for m in rule.material_overrides] for rule in rules];save()
 # Keep the road's actor pivot within the authored section for viewport editing.
 controls=[road.control_points.get_location_at_spline_point(i,u.SplineCoordinateSpace.WORLD) for i in range(road.control_points.get_number_of_spline_points())]
 road.set_actor_location(u.Vector(data['bounds'][0],data['bounds'][1],0),False,True)
 for i,p in enumerate(controls):road.control_points.set_location_at_spline_point(i,p,u.SplineCoordinateSpace.WORLD,False)
 road.control_points.update_spline()
 assert author.rebuild(),author.last_message;yield 3
 baseline=author.output_digest;terrain=author.current_terrain_digest();assert terrain!=author.base_terrain_digest(),'Road bed made no terrain changes'
 ignored=[a for a in actors.get_all_level_actors() if a!=author.landscape and not isinstance(a,u.GTRoadReliefTile)];deltas=[]
 for p in controls[1:-1]:
  hit=u.SystemLibrary.line_trace_single(ew,p+u.Vector(0,0,3000),p-u.Vector(0,0,3000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,u.DrawDebugTrace.NONE,True)
  assert hit;parts=hit.to_tuple();assert parts[0]
  # HitResult location follows blocking_hit, initial_overlap, time, distance.
  location=parts[4];assert isinstance(location,u.Vector),str(parts)
  deltas.append(location.z-author.base_height_at(u.Vector2D(p.x,p.y)))
 assert any(abs(d)>3 for d in deltas),'Persistent layer changed but collision did not'
 report['collision_height_changes_cm']=deltas
 report['repeat']=timed_rebuild(author);assert report['repeat']['digest']==baseline and author.changed_cells==0 and author.retained_cells>0
 # A moved spline point must update output, retain distant cells, and restore
 # exactly when moved back. No accumulation of old road beds or placement.
 index=road.control_points.get_number_of_spline_points()//2;p=road.control_points.get_location_at_spline_point(index,u.SplineCoordinateSpace.WORLD)
 road.control_points.set_location_at_spline_point(index,p+u.Vector(0,1800,0),u.SplineCoordinateSpace.WORLD,True)
 report['moved_road']=timed_rebuild(author);assert author.output_digest!=baseline and author.changed_cells>0 and author.retained_cells>0
 road.control_points.set_location_at_spline_point(index,p,u.SplineCoordinateSpace.WORLD,True)
 report['restored_road']=timed_rebuild(author);assert author.output_digest==baseline and author.current_terrain_digest()==terrain
 original_seed=author.seed;author.seed=original_seed+1
 report['changed_seed']=timed_rebuild(author);assert author.output_digest!=baseline
 author.seed=original_seed;assert author.rebuild();assert author.output_digest==baseline
 assert author.clear_generated();assert author.current_terrain_digest()==author.base_terrain_digest();assert author.instance_count==0 and author.generated_cell_count()==0;report['clear_restores_base']=True
 report['after_clear']=timed_rebuild(author);assert author.output_digest==baseline and author.current_terrain_digest()==terrain
 # Invalid road edits must fail before changing the terrain/output.
 q=road.control_points.get_location_at_spline_point(1,u.SplineCoordinateSpace.WORLD)
 road.control_points.set_location_at_spline_point(1,road.control_points.get_location_at_spline_point(0,u.SplineCoordinateSpace.WORLD),u.SplineCoordinateSpace.WORLD,True)
 assert not author.rebuild();assert author.current_terrain_digest()==terrain and author.output_digest==baseline;report['invalid_input_retains_output']=True
 road.control_points.set_location_at_spline_point(1,q,u.SplineCoordinateSpace.WORLD,True)
 assert author.rebuild();report['message']=author.last_message
 for texture in [author.paint_texture,author.style_texture,author.macro_texture]:assert assets.save_loaded_asset(texture)
 assert les.save_current_level();yield 3
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));assert author.output_digest==baseline and author.current_terrain_digest()==terrain;report['save_reload']=True;save()
 # All probes are stationary. Do not send throttle or steering input.
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 20
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0);assert isinstance(car,u.GTCarPawn)
 car.disable_input(pc);move=car.get_chaos_movement();move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0];grass=u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails)[0]
 report['sites']=[]
 for lane,name in enumerate(['Road_entry','Wet_ground','Road_end'],1):
  pc.select_lane(lane);car.disable_input(pc);move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);yield from settle(8)
  poses=[]
  for _ in range(4):
   yield from settle(.5);r=car.get_actor_rotation();p=car.get_actor_location();poses.append(dict(x=p.x,y=p.y,z=p.z,speed_cm_s=car.get_velocity().length(),pitch=r.pitch,roll=r.roll,contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(k))[0]) for k in range(4))))
  assert all(s['contacts']>=3 and abs(s['roll'])<30 and abs(s['pitch'])<30 for s in poses[-2:]),poses
  assert abs(poses[-1]['z']-poses[-2]['z'])<8,poses
  sample=surface.sample_surface(u.Vector2D(p.x,p.y));report['sites'].append(dict(name=name,poses=poses,mud_depth=sample.sinkage_cap_cm,grass=grass.grass.get_instance_count()))
  yield from capture(name,(p.x-700,p.y+600,p.z+500),(p.x+400,p.y,p.z))
 cx,cy,ex,ey=data['bounds'];z=car.get_actor_location().z
 yield from capture('Generated_corridor',(cx-20000,cy-20000,z+20000),(cx,cy,z))
 assert all(a.dust_intensity==0 for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTVehicleSurfaceEffects))
 report['grass_report']=grass.grass_report();report['surface_report']=surface.get_surface_report()
 outputs=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.actor_has_tag('GT.ProceduralGround.Output')]
 clods=[(a,c) for a in outputs for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith('SM_plants_mud_chunk') and c.get_instance_count()>0]
 assert clods;report['clod_collision_probes']=0
 for owner,c in clods[:3]:
  t=c.get_instance_transform(0,True);point=u.MathLibrary.transform_location(t,c.static_mesh.get_bounds().origin)
  ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a!=owner]
  hit=u.SystemLibrary.line_trace_single(world,point+u.Vector(0,0,100),point-u.Vector(0,0,100),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,u.DrawDebugTrace.NONE,True)
  assert hit;parts=hit.to_tuple();assert parts[0] and next((v for v in parts if isinstance(v,u.Actor)),None)==owner
  report['clod_collision_probes']+=1
 for path,sha in data['protected'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
 report.update(ok=True,protected_unchanged=True);save();yield from finish()
def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 if camera:camera.destroy_actor()
 camera=pc=car=None;u.EditorLevelLibrary.editor_end_play();yield 4;world=None
 les.load_level('/Engine/Maps/Entry');yield 4
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1100
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
