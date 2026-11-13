"""Editable layered composition; native budgets/ranges, host habitat masks.
Only the dedicated authoring study is saved. Stationary checks, no driving.
"""
import unreal as u
from pathlib import Path
import json,time,traceback,hashlib,gc,shutil,re,math
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround';BASE='/Game/GrandTour/ArtTests/ProceduralGround';LEVEL=BASE+'/L_BigMountain_Authoring'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.EditorAssetLibrary
NO_VISUAL='-gtdensitynovisual' in u.SystemLibrary.get_command_line().lower()
report=dict(ok=False,driving_tested=False,visual_checked=False,headless=NO_VISUAL,images=[]);busy=False;world=pc=car=camera=None
data=json.loads((OUT/'install.json').read_text())
def save():(OUT/('density-functional.json' if NO_VISUAL else 'density.json')).write_text(json.dumps(report,indent=2))
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def rebuild(a):
 t=time.monotonic();assert a.rebuild(),a.last_message
 return dict(seconds=time.monotonic()-t,digest=a.output_digest,instances=a.instance_count,changed=a.changed_cells,retained=a.retained_cells,tiles=len(a.get_editor_property('relief_tiles')),triangles=a.relief_triangles)
def inventory():
 rows={}
 for a in actors.get_all_level_actors():
  if 'GT.ProceduralGround.Output' not in [str(t) for t in a.tags]:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   tags=list(c.component_tags);name=str(tags[0]) if tags else c.static_mesh.get_name()
   rows[name]=rows.get(name,0)+c.get_instance_count()
 return rows
def settle(seconds):
 t=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-t<seconds:yield 0
def capture(name,p):
 global camera
 if camera:camera.destroy_actor()
 pos=p+u.Vector(-700,600,500);target=p+u.Vector(400,0,0)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=pos,rotation=u.MathLibrary.find_look_at_rotation(pos,target)),'DensityReview')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65);pc.set_view_target_with_blend(camera,0);yield from settle(3)
 path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 end=time.monotonic()+30
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<end;yield .3
 u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));save()
def run():
 global world,pc,car
 backup=OUT/'BeforeDensityLayers'
 if not backup.exists():shutil.copytree(ROOT/'Content/GrandTour/ArtTests/ProceduralGround',backup)
 assert les.load_level(LEVEL)
 refs=list(actors.get_all_level_actors());author=next(a for a in refs if isinstance(a,u.GTProceduralGround));road=next(a for a in refs if isinstance(a,u.GTProceduralRoad) and a.get_actor_label().startswith('Road 01'))
 report['before']=dict(instances=author.instance_count,layers=inventory(),digest=author.output_digest)
 ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();u.SystemLibrary.execute_console_command(ew,'Automation RunTests GrandTour.Authoring.NativeOracle');until=time.monotonic()+150
 while True:
  log=(ROOT/'Saved/Logs/ProceduralGround-Density.log').read_text(errors='replace')
  if re.search(r'Test Completed\. Result=\{\w+\} Name=\{NativeOracle\}',log):break
  assert time.monotonic()<until;yield .5
 assert 'Result={Success} Name={NativeOracle}' in log;report['native_oracle']=True
 fir_mats=list(author.scatter_rules[0].material_overrides)
 bush=u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/Understory/SM_BirchBush')
 bush_mats=[u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/Understory/MI_BirchBush') if any(s in bush.get_material(i).get_name().lower() for s in ['leaf','leave','foliage']) else bush.get_material(i) for i in range(bush.get_num_sections(0))]
 def variant(lo,hi,a,b):return props(u.GTGroundPlantVariant(),min_map_scale=lo,max_map_scale=hi,min_size=a,max_size=b,scale_random=.3)
 def rule(name,meshes,**kw):
  loaded=[u.load_asset(m) for m in meshes];assert all(loaded),meshes
  return props(u.GTGroundScatterRule(),name=name,meshes=loaded,**kw)
 firs=['/Game/GrandTour/ArtTests/BenmoreWoodland/Forest/SM_Fir_'+str(i) for i in range(3)]
 branch=['/Game/GrandTour/ArtTests/BenmoreWoodland/Understory/SM_Branch'];bushes=[bush.get_path_name()]
 habitat=u.GTScatterHabitat
 # Native Firs, Bushes, SmallTwigs and MudChunks budgets. Species are the same
 # Unreal substitutes as the direct reference export, not imported placements.
 rules=[
  rule('Canopy',firs,candidate_budget=26,density=.38,seed_offset=962,cluster_strength=.65,cluster_scale_cm=2200,scale_map_contrast=2.5,road_clearance_cm=280,cull_distance_cm=35000,material_overrides=fir_mats,variants=[variant(0,.55,.6,1.4),variant(.25,1,.8,1.4),variant(.4,1,.8,1.4)]),
  rule('YoungFirs',firs,candidate_budget=26,density=.15,seed_offset=415,cluster_strength=.85,cluster_scale_cm=1100,scale_map_contrast=2.5,road_clearance_cm=180,mesh_height_cm=450,cull_distance_cm=24000,material_overrides=fir_mats,minimum_scale=.6,maximum_scale=1.6),
  rule('LowBushes',bushes,candidate_budget=64,density=.34,habitat=habitat.OPEN_GROUND,seed_offset=705,cluster_strength=.9,cluster_scale_cm=900,mesh_height_cm=85,minimum_scale=.7,maximum_scale=1.2,road_clearance_cm=20,cull_distance_cm=22000,cast_shadow=False,material_overrides=bush_mats),
  rule('TallBushes',bushes,candidate_budget=64,density=.15,seed_offset=331,cluster_strength=.85,cluster_scale_cm=1600,mesh_height_cm=165,minimum_scale=.6,maximum_scale=1.4,road_clearance_cm=130,cull_distance_cm=24000,cast_shadow=False,material_overrides=bush_mats),
  rule('VergeShrubs',bushes,candidate_budget=64,density=.6,habitat=habitat.VERGE,seed_offset=127,cluster_strength=.95,cluster_scale_cm=650,verge_width_cm=1000,mesh_height_cm=70,minimum_scale=.65,maximum_scale=1.35,road_clearance_cm=0,cull_distance_cm=18000,cast_shadow=False,material_overrides=bush_mats),
  rule('Twigs',branch,candidate_budget=320,density=.065,habitat=habitat.OPEN_GROUND,seed_offset=628,cluster_strength=.75,cluster_scale_cm=1200,mesh_footprint_cm=160,minimum_scale=.6,maximum_scale=1.7,road_clearance_cm=0,cull_distance_cm=12000,align_to_ground=True,cast_shadow=False),
  rule('FallenWood',branch,candidate_budget=32,density=.03,seed_offset=219,cluster_strength=.65,cluster_scale_cm=2800,mesh_footprint_cm=450,minimum_scale=.6,maximum_scale=.8,road_clearance_cm=250,cull_distance_cm=18000,align_to_ground=True,cast_shadow=False),
  rule('MudClods',['/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/SM_plants_mud_chunk_'+s for s in ['a','b']],candidate_budget=64,density=.3,habitat=habitat.VERGE,road_debris=False,road_clearance_cm=30,verge_width_cm=350,seed_offset=958,cluster_strength=.95,cluster_scale_cm=700,scale_map_contrast=2.4,cull_distance_cm=12000,solid=True,align_to_ground=True,cast_shadow=False,material_overrides=[u.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeStage4/M_NativeClod')],variants=[variant(0,.8,.55,1.1),variant(.2,1,.5,.9)])]
 author.scatter_rules=rules;road.centre_grass_cover=.65;road.verge_grass_cover=.9
 widths=[.8,.72,1.05,1.5,.95,1.35,.85,.64,1.12,1.45,.9]
 for i,w in enumerate(widths):road.control_points.set_scale_at_spline_point(i,u.Vector(1,w,1),False)
 road.control_points.update_spline()
 # The reference overlaps road ribbons. A narrow grass track here is authored
 # as a second editable spline using the recovered native grass-road profile.
 side=next((a for a in refs if isinstance(a,u.GTProceduralRoad) and a.get_actor_label()=='Road 02 - grass passing track'),None)
 if not side:side=actors.spawn_actor_from_class(u.GTProceduralRoad,u.Vector());side.set_actor_label('Road 02 - grass passing track')
 props(side,author=author,width_cm=400,bed_depth_cm=5,mud_depth_cm=15,wetness=.35,centre_grass_cover=.9,verge_grass_cover=.95,relief_texture=u.load_asset(BASE+'/RoadProfiles/T_grass_road'),relief_default_width_cm=400,relief_diffuse_aspect=2)
 side.control_points.clear_spline_points(False)
 for idx,offset in [(3,0),(4,800),(5,1100),(6,600),(7,0)]:
  p=road.control_points.get_location_at_spline_point(idx,u.SplineCoordinateSpace.WORLD);p.y+=offset;p.z=author.base_height_at(u.Vector2D(p.x,p.y));side.control_points.add_spline_point(p,u.SplineCoordinateSpace.WORLD,False)
 side.control_points.update_spline()
 grass=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails));report['grass_before']=dict(spacing=grass.grass_spacing_cm,streamed=grass.generate_around_player)
 grass.grass_spacing_cm=45;assert grass.generate_around_player
 report['first']=rebuild(author);yield 3;report['layers']=inventory();baseline=author.output_digest
 assert len(report['layers'])==8 and author.instance_count>data['instances']*2,report
 report['repeat']=rebuild(author);assert author.output_digest==baseline and author.changed_cells==0
 # Invalid eligibility cannot partially mutate output. Restore the field after.
 valid=list(author.scatter_rules);invalid=list(author.scatter_rules);bad=invalid[0];bad.variants=[variant(0,1,1,1)];invalid[0]=bad;author.scatter_rules=invalid
 assert not author.rebuild() and author.output_digest==baseline
 author.scatter_rules=rules;assert author.rebuild() and author.output_digest==baseline
 assert author.clear_generated() and author.current_terrain_digest()==author.base_terrain_digest();rebuild(author);assert author.output_digest==baseline
 report['clear_and_restore']=True;report['invalid_input_retained_output']=True
 for t in [author.paint_texture,author.style_texture,author.macro_texture]:assert assets.save_loaded_asset(t)
 assert les.save_current_level();yield 3;assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));assert author.output_digest==baseline;assert inventory()==report['layers'];report['saved_and_reloaded']=True
 # Verify generated clods really block queries after size/ground alignment.
 ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();clods=[]
 for a in actors.get_all_level_actors():
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if 'MudClods' in [str(t) for t in c.component_tags] and c.get_instance_count():clods.append((a,c))
 assert clods;blocking=[]
 for a,c in clods[::max(1,len(clods)//5)]:
  t=c.get_instance_transform(0,True);p=t.translation;b=c.static_mesh.get_bounds();span=max(200,b.box_extent.z*t.scale3d.z*3)
  ignored=[o for o in actors.get_all_level_actors() if o!=a]
  hit=u.SystemLibrary.line_trace_single(ew,p+u.Vector(0,0,span),p-u.Vector(0,0,span),u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignored,u.DrawDebugTrace.NONE,True)
  parts=hit.to_tuple();blocking.append(bool(parts[0]));assert parts[0]
 report['solid_clod_traces']=len(blocking);save()
 if NO_VISUAL:
  for path,sha in data['protected'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
  report.update(ok=True,protected_unchanged=True);save();les.load_level('/Engine/Maps/Entry');yield 4;return
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);until=time.monotonic()+180
 while car is None:
  yield .5;world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0)
  assert time.monotonic()<until,'Play world/pawn did not become ready within 180 seconds'
 move=car.get_chaos_movement()
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 report['sites']=[]
 for lane,name in enumerate(['Density_entry','Density_wet','Density_end'],1):
  pc.select_lane(lane);car.disable_input(pc);move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);yield from settle(10)
  p=car.get_actor_location();contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(k))[0]) for k in range(4));assert contacts>=3
  g=u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails)[0]
  report['sites'].append(dict(name=name,contacts=contacts,near_grass=g.grass.get_instance_count(),distant_grass=g.distant_grass.get_instance_count()))
  assert g.grass.get_instance_count()>2000;yield from capture(name,p)
 assert all(a.dust_intensity==0 for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTVehicleSurfaceEffects))
 for path,sha in data['protected'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
 report.update(ok=True,protected_unchanged=True,visual_checked=True);save();yield from finish()
def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 if camera:camera.destroy_actor()
 camera=pc=car=None;u.EditorLevelLibrary.editor_end_play();yield 4
 until=time.monotonic()+60
 while u.EditorLevelLibrary.get_game_world():
  assert time.monotonic()<until,'Play world did not close';yield .5
 world=None;les.load_level('/Engine/Maps/Entry');yield 4
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
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
