"""Install editable native road-relief profiles; regression and stationary checks."""
import unreal as u
from pathlib import Path
import json,time,traceback,hashlib,gc,re,math
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround';BASE='/Game/GrandTour/ArtTests/ProceduralGround';LEVEL=BASE+'/L_BigMountain_Authoring'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
data=json.loads((OUT/'install.json').read_text());report=dict(ok=False,driving_tested=False,images=[]);busy=False;world=pc=car=camera=None
def save():(OUT/'roadrelief.json').write_text(json.dumps(report,indent=2))
def rebuild(a):
 start=time.monotonic();assert a.rebuild(),a.last_message
 r=dict(seconds=time.monotonic()-start,digest=a.output_digest,tiles=len(a.get_editor_property('relief_tiles')),triangles=a.relief_triangles,changed=a.changed_relief_tiles,retained=a.retained_relief_tiles)
 u.log('ROAD RELIEF '+str(r));return r
def alltiles(a):return list(a.get_editor_property('relief_tiles').values())
def height(tiles,p):
 for t in tiles:
  o=t.get_actor_location();s=t.get_editor_property('span_cm')
  if o.x<=p.x<o.x+s and o.y<=p.y<o.y+s:return t.height_at(u.Vector2D(p.x,p.y))
 return None
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:yield 0
def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector(*pos),rotation=u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target))),'ReliefReview')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65);pc.set_view_target_with_blend(camera,0);yield from settle(3)
 path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
 end=time.monotonic()+30
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<end;yield .3
 u.GameplayStatics.set_game_paused(world,False);report['images'].append(str(path));save()
def normals(mat):
 if any(e.get_editor_property('desc')=='AuthoredRoadGeometryNormal' for e in mel.get_material_expressions(mat)):return
 for e in mel.get_material_expressions(mat):
  if isinstance(e,u.MaterialExpressionCustom):
   code=e.get_editor_property('code').replace('mrNormal=normalize(float3(mrNormal.xy-macroSlope,mrNormal.z));','// Geometric grade is supplied by the mesh normal below.')
   e.set_editor_property('code',code)
 old=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL);pin=mel.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_NORMAL);assert old
 geo=mel.create_material_expression(mat,u.MaterialExpressionVertexNormalWS)
 n=mel.create_material_expression(mat,u.MaterialExpressionCustom);n.set_editor_property('desc','AuthoredRoadGeometryNormal');n.set_editor_property('code','return normalize(float3(N.xy/max(N.z,.15)+G.xy/max(G.z,.15),1));');n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
 inputs=[]
 for name in ['N','G']:
  i=u.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
 n.set_editor_property('inputs',inputs);assert mel.connect_material_expressions(old,pin,n,'N');assert mel.connect_material_expressions(geo,'',n,'G');assert mel.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
 assert not mel.recompile_material(mat);assert assets.save_loaded_asset(mat)
def run():
 global world,pc,car
 assert les.load_level(LEVEL);ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(ew,'Automation RunTests GrandTour.Authoring.NativeOracle');until=time.monotonic()+150
 while True:
  log=(ROOT/'Saved/Logs/ProceduralGround-RoadRelief.log').read_text(errors='replace')
  if re.search(r'Test Completed\. Result=\{\w+\} Name=\{NativeOracle\}',log):break
  assert time.monotonic()<until;yield .5
 assert 'Result={Success} Name={NativeOracle}' in log;report['native_oracle']=True;save()
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));road=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralRoad))
 assets.make_directory(BASE+'/RoadProfiles')
 for name in ['dirt_road','grass_road','dirt_path']:
  path=BASE+'/RoadProfiles/T_'+name
  if not assets.does_asset_exist(path):
   task=u.AssetImportTask();task.filename=str(ROOT/f'Art/Export/MudRunnerEditorResearch/RoadRelief/{name}.png');task.destination_path=BASE+'/RoadProfiles';task.destination_name='T_'+name;task.automated=True;task.save=True;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
  tex=u.load_asset(path);assert tex;tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);assert assets.save_loaded_asset(tex)
 for name in ['M_Terrain','M_Detail']:normals(u.load_asset(BASE+'/'+name))
 road.relief_texture=u.load_asset(BASE+'/RoadProfiles/T_dirt_road');road.relief_default_width_cm=700;road.relief_diffuse_aspect=2;road.relief_strength=1;road.apply_relief=True
 author.relief_material=u.load_asset(BASE+'/M_Terrain');author.relief_spacing_cm=25
 report['first']=rebuild(author);save();yield 3
 assert author.relief_triangles>10000;baseline=author.output_digest;terrain=author.current_terrain_digest()
 tiles=alltiles(author);report['repeat']=rebuild(author);assert author.output_digest==baseline and author.changed_relief_tiles==0;save();yield 1
 # Actual geometry difference with the relief amplitude disabled, same road bed.
 points=[]
 for t in tiles[::max(1,len(tiles)//8)]:
  o=t.get_actor_location();span=t.get_editor_property('span_cm')
  for j in range(1,12):
   for i in range(1,12):points.append(o+u.Vector(span*i/12,span*j/12,0))
 enabled=[height(tiles,p) for p in points];road.relief_strength=0;report['zero_strength']=rebuild(author)
 disabled=[height(alltiles(author),p) for p in points];diff=[a-b for a,b in zip(enabled,disabled)]
 report['relief_range_cm']=[min(diff),max(diff)];assert min(diff)<-5 and max(diff)>1 and min(diff)>-25 and max(diff)<10,diff
 road.relief_strength=1;rebuild(author);assert author.output_digest==baseline
 # Move a control point, then restore it; unchanged distant tiles must survive.
 index=road.control_points.get_number_of_spline_points()//2;original=road.control_points.get_location_at_spline_point(index,u.SplineCoordinateSpace.WORLD)
 road.control_points.set_location_at_spline_point(index,original+u.Vector(0,1200,0),u.SplineCoordinateSpace.WORLD,True)
 report['moved']=rebuild(author);assert author.output_digest!=baseline and author.changed_relief_tiles>0 and author.retained_relief_tiles>0
 road.control_points.set_location_at_spline_point(index,original,u.SplineCoordinateSpace.WORLD,True);rebuild(author);assert author.output_digest==baseline
 assert author.clear_generated();assert len(alltiles(author))==0 and author.current_terrain_digest()==author.base_terrain_digest();report['clear_restores_base']=True
 rebuild(author);assert author.output_digest==baseline and author.current_terrain_digest()==terrain
 # Reject malformed relief before mutating terrain/output.
 old_width=road.relief_default_width_cm;road.relief_default_width_cm=0;assert not author.rebuild();assert author.output_digest==baseline;road.relief_default_width_cm=old_width;report['invalid_input_retains_output']=True
 tiles=alltiles(author);report['seam_max_cm']=0;seams=0
 by={tuple((round(t.get_actor_location().x,2),round(t.get_actor_location().y,2))):t for t in tiles}
 for t in tiles:
  o=t.get_actor_location();span=t.get_editor_property('span_cm')
  for dx,dy in [(1,0),(0,1)]:
   other=by.get((round(o.x+dx*span,2),round(o.y+dy*span,2)))
   if not other:continue
   for i in range(11):
    p=u.Vector2D(o.x+span*(1 if dx else i/10),o.y+span*(1 if dy else i/10))
    report['seam_max_cm']=max(report['seam_max_cm'],abs(t.height_at(p)-other.height_at(p)));seams+=1
 assert seams>100 and report['seam_max_cm']<.05;report['seam_samples']=seams
 for tex in [author.paint_texture,author.style_texture,author.macro_texture]:assert assets.save_loaded_asset(tex)
 assert les.save_current_level();yield 3
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL);author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));assert author.output_digest==baseline and author.current_terrain_digest()==terrain;report['save_reload']=True
 # Collision probes after reload, against both coarse ground and detailed tiles.
 ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();tiles=alltiles(author);ignored=[a for a in actors.get_all_level_actors() if a!=author.landscape and not isinstance(a,u.GTRoadReliefTile)];errors=[]
 for t in tiles[::max(1,len(tiles)//12)]:
  o=t.get_actor_location();s=t.get_editor_property('span_cm')
  for x,y in [(.33,.41),(.67,.58),(.5,.5)]:
   p=u.Vector2D(o.x+s*x,o.y+s*y);z=t.height_at(p)
   hit=u.SystemLibrary.line_trace_single(ew,u.Vector(p.x,p.y,z+1000),u.Vector(p.x,p.y,z-1000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignored,u.DrawDebugTrace.NONE,True)
   parts=hit.to_tuple();assert parts[0];owner=next((v for v in parts if isinstance(v,u.Actor)),None);assert isinstance(owner,u.GTRoadReliefTile),(owner,t)
   errors.append(abs(parts[4].z-z))
 assert max(errors)<.1;report['collision_samples']=len(errors);report['collision_max_error_cm']=max(errors);save()
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 20
 world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0);car.disable_input(pc);move=car.get_chaos_movement();move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 report['sites']=[];report['mud_support_probes']=[]
 for lane,name in enumerate(['Relief_entry','Relief_wet','Relief_end'],1):
  pc.select_lane(lane);car.disable_input(pc);move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True);yield from settle(8)
  poses=[]
  for _ in range(4):
   yield from settle(.5);p=car.get_actor_location();r=car.get_actor_rotation();poses.append(dict(z=p.z,pitch=r.pitch,roll=r.roll,contacts=sum(bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(k))[0]) for k in range(4))))
  assert all(s['contacts']>=3 and abs(s['pitch'])<30 and abs(s['roll'])<30 for s in poses[-2:]);assert abs(poses[-1]['z']-poses[-2]['z'])<8,poses
  runtime_tiles=u.GameplayStatics.get_all_actors_of_class(world,u.GTRoadReliefTile)
  supported=0
  for dx,dy in [(0,0),(60,0),(-60,0),(0,60),(0,-60)]:
   point=p+u.Vector(dx,dy,0);h=height(runtime_tiles,point)
   if h is None:continue
   q=u.GTLandscapeSurface.query_wheel_surface(car,u.Vector(point.x,point.y,h),u.Vector2D(1,0),25)
   supported+=int(q.wheel_support)
  report['mud_support_probes'].append(supported);assert supported>0,(lane,supported)
  report['sites'].append(dict(name=name,poses=poses));yield from capture(name,(p.x-700,p.y+600,p.z+500),(p.x+400,p.y,p.z))
  if lane==1:yield from capture('Relief_low_sun',(p.x+700,p.y-200,p.z+160),(p.x+2200,p.y+50,p.z-100))
 assert all(a.dust_intensity==0 for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTVehicleSurfaceEffects))
 for path,sha in data['protected'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==sha,path
 report.update(ok=True,protected_unchanged=True);save();yield from finish()
def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 if camera:camera.destroy_actor()
 camera=pc=car=None;u.EditorLevelLibrary.editor_end_play();yield 4;world=None;les.load_level('/Engine/Maps/Entry');yield 4
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
