"""Install/check the bounded road-condition pilot; never drive the vehicle."""
import unreal as u
from pathlib import Path
import json,hashlib,traceback,time,gc,re,math,sys
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround';BASE='/Game/GrandTour/ArtTests/ProceduralGround';LEVEL=BASE+'/L_BigMountain_Authoring'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
living='-GTLivingRoads' in u.SystemLibrary.get_command_line()
STEM='livingroads' if living else 'roadconditions'
MODE='LivingRoads' if living else 'RoadConditions'
mud_push='-GTMudPush' in u.SystemLibrary.get_command_line()
if mud_push:STEM='mudpush';MODE='MudPush'
headless='-GTDensityNoVisual' in u.SystemLibrary.get_command_line()
report=dict(ok=False,visual_checked=False,driving_tested=False);busy=False;play_world=None
def save():(OUT/(STEM+('-functional.json' if headless else '.json'))).write_text(json.dumps(report,indent=2))
def rebuild(a):
 t=time.monotonic();assert a.rebuild(),a.last_message
 r=dict(seconds=time.monotonic()-t,digest=a.output_digest,wet_samples=a.road_pool_wet_samples,tiles=len(a.get_editor_property('relief_tiles')),triangles=a.relief_triangles)
 u.log('ROAD CONDITIONS '+str(r));return r
def water_material():
 path=BASE+'/M_RoadPools';mat=u.load_asset(path)
 if not mat:mat=assets.duplicate_asset('/Game/GrandTour/ArtTests/BigMountain/M_Water',path)
 assert mat
 color=next((e for e in mel.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionVertexColor) and e.get_editor_property('desc')=='RoadPoolDepth'),None)
 if not color:color=mel.create_material_expression(mat,u.MaterialExpressionVertexColor);color.set_editor_property('desc','RoadPoolDepth')
 changed=0
 for e in list(mel.get_material_expressions(mat)):
  if not isinstance(e,u.MaterialExpressionCustom):continue
  code=str(e.get_editor_property('code'));original=code
  code=re.sub(r'float4 flow=Texture2DSampleLevel\(Baked,BakedSampler,saturate\(buv\),0\);','float4 flow=float4(.5,.5,RoadDepth*.5,0);',code)
  code=re.sub(r'float bankDistance=\(Texture2DSampleLevel\(BankEdge,BankEdgeSampler,saturate\(shapeBankUV\),0\).g-.5\)\*4;','float bankDistance=max(0,RoadDepth*4);',code)
  code=code.replace('return Old*step(.5001,shore.r);','return Old; // Road pool triangles already clip to the final bed.')
  if code!=original:
   e.set_editor_property('code',code);changed+=1
   if 'RoadDepth' in code:
    inputs=list(e.get_editor_property('inputs'));ci=u.CustomInput();ci.set_editor_property('input_name','RoadDepth');inputs.append(ci);e.set_editor_property('inputs',inputs)
    assert mel.connect_material_expressions(color,'R',e,'RoadDepth')
 assert changed>=3 or any('RoadDepth' in str(e.get_editor_property('code')) for e in mel.get_material_expressions(mat) if isinstance(e,u.MaterialExpressionCustom)),changed
 assert not mel.recompile_material(mat);assert assets.save_loaded_asset(mat);return mat
def checks(author):
 tiles=list(author.get_editor_property('relief_tiles').values());pairs={(round(t.get_actor_location().x,2),round(t.get_actor_location().y,2)):t for t in tiles};seam=0;n=0
 for t in tiles:
  o=t.get_actor_location();span=t.get_editor_property('span_cm')
  for dx,dy in [(1,0),(0,1)]:
   other=pairs.get((round(o.x+dx*span,2),round(o.y+dy*span,2)))
   if not other:continue
   for j in range(9):
    p=u.Vector2D(o.x+span*(1 if dx else j/8),o.y+span*(1 if dy else j/8));seam=max(seam,abs(t.height_at(p)-other.height_at(p)));n+=1
 assert n>100 and seam<.05;report.update(seam_samples=n,seam_max_cm=seam)
 soil=[c for t in tiles for c in t.get_editor_property('soil') if c.r>=0]
 report['soil_depth_range_cm']=[min(c.r for c in soil),max(c.r for c in soil)];report['firmness_range']=[min(c.b for c in soil),max(c.b for c in soil)]
 assert report['soil_depth_range_cm'][1]>35 and report['soil_depth_range_cm'][0]<5
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();ignored=[a for a in actors.get_all_level_actors() if a!=author.landscape and not isinstance(a,u.GTRoadReliefTile)];errors=[]
 for t in tiles[::max(1,len(tiles)//12)]:
  o=t.get_actor_location();span=t.get_editor_property('span_cm')
  for x,y in [(.33,.41),(.67,.58),(.5,.5)]:
   p=u.Vector2D(o.x+span*x,o.y+span*y);z=t.height_at(p)
   hit=u.SystemLibrary.line_trace_single(world,u.Vector(p.x,p.y,z+1000),u.Vector(p.x,p.y,z-1000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignored,u.DrawDebugTrace.NONE,True).to_tuple()
   assert hit[0];owner=next((v for v in hit if isinstance(v,u.Actor)),None);assert isinstance(owner,u.GTRoadReliefTile),(owner,t)
   errors.append(abs(hit[4].z-z))
 assert max(errors)<.1;report.update(collision_max_error_cm=max(errors),collision_samples=len(errors))
 domain=author.get_editor_property('generated_water_domain');assert domain
 patches=domain.get_editor_property('road_patches');wet=[]
 for p in patches:
  s=p.get_editor_property('samples');w=p.get_editor_property('size_x');o=p.get_editor_property('origin_cm');cell=p.get_editor_property('cell_cm')
  for i in range(len(s)//4):
   if s[i*4+1]>.005:wet.append(dict(x=o.x+(i%w+.5)*cell,y=o.y+(i//w+.5)*cell,z=s[i*4],depth_cm=s[i*4+1]*100))
 assert len(wet)==author.road_pool_wet_samples and wet, 'No natural pools in the pilot; adjust wet section location, not basin shape'
 report['pool_depth_range_cm']=[min(p['depth_cm'] for p in wet),max(p['depth_cm'] for p in wet)];assert max(p['depth_cm'] for p in wet)<=18.01
 report['pool_examples']=wet[::max(1,len(wet)//6)][:6]
 # Compare serialized depths with the actual final collision mesh, not old landscape.
 deltas=[]
 for p in wet[::max(1,len(wet)//100)]:
  for t in tiles:
   o=t.get_actor_location();span=t.get_editor_property('span_cm')
   if o.x<=p['x']<o.x+span and o.y<=p['y']<o.y+span:
    deltas.append(abs(p['z']-t.height_at(u.Vector2D(p['x'],p['y']))-p['depth_cm']));break
 assert deltas and max(deltas)<.1;report['water_bed_max_error_cm']=max(deltas)
def run():
 if not headless:
  if living:
   import living_roads
   yield from living_roads.review(report,save)
  else:yield from review()
  return
 assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(world,'Automation RunTests GrandTour.Authoring.');until=time.monotonic()+150
 while True:
  log=(ROOT/('Saved/Logs/ProceduralGround-'+MODE+'.log')).read_text(errors='replace')
  if 'Test Completed. Result={Success} Name={RoadBasins}' in log and 'Test Completed. Result={Success} Name={NativeOracle}' in log and (not living or 'Test Completed. Result={Success} Name={RoadSoilOwnership}' in log):break
  assert 'Test Completed. Result={Fail}' not in log,log[-5000:];assert time.monotonic()<until;yield .5
 report['native_oracle_and_basin_tests']=True
 if living:
  u.SystemLibrary.execute_console_command(world,'Automation RunTests GrandTour.MudRunner.');until=time.monotonic()+150
  while True:
   log=(ROOT/('Saved/Logs/ProceduralGround-'+MODE+'.log')).read_text(errors='replace')
   assert 'Test Completed. Result={Fail}' not in log,log[-5000:]
   if all('Test Completed. Result={Success} Name={'+n+'}' in log for n in ['ShaderOracle','SubstanceOracle']+(['LivePush'] if mud_push else [])):break
   assert time.monotonic()<until;yield .5
  report['native_shader_and_substance_oracles']=True
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));road=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralRoad) and a.get_actor_label().startswith('Road 01'))
 author.road_water_material=water_material();road.add_example_conditions();assert len(road.conditions)==4
 if living:
  import living_roads
  living_roads.configure(author,road,report)
 road.set_actor_label('Road 01 - Conditions: firm grass shallow deep');report['first']=rebuild(author);save();yield 2
 checks(author);baseline=author.output_digest;terrain=author.current_terrain_digest();wet=author.road_pool_wet_samples
 report['repeat']=rebuild(author);assert author.output_digest==baseline and author.changed_relief_tiles==0
 # Changing only physical depth must not reshape the authored bed or puddles.
 conditions=list(road.conditions);old=conditions[2].mud_depth_cm;conditions[2].mud_depth_cm=old+8;road.conditions=conditions
 rebuild(author);assert author.current_terrain_digest()==terrain and author.road_pool_wet_samples==wet
 conditions[2].mud_depth_cm=old;road.conditions=conditions;rebuild(author);assert author.output_digest==baseline
 report['independent_depth_verified']=True
 if living:
  # Catch later roads accidentally overwriting an earlier condition's softness.
  def fine_softness():return [c.a for _,t in sorted(author.get_editor_property('relief_tiles').items(),key=lambda pair:str(pair[0])) for c in t.get_editor_property('soil')]
  before=fine_softness();old_firm=conditions[2].firmness;conditions[2].firmness=.85;road.conditions=conditions
  rebuild(author);after=fine_softness()
  assert len(before)==len(after) and max(a-b for a,b in zip(before,after))>.3
  assert author.current_terrain_digest()==terrain and author.road_pool_wet_samples==wet
  conditions[2].firmness=old_firm;road.conditions=conditions;rebuild(author);assert author.output_digest==baseline
  report['independent_firmness_verified']=True
 # Invalid input must leave completed output intact.
 old_end=conditions[0].end_metres;conditions[0].end_metres=-1;road.conditions=conditions;assert not author.rebuild();assert author.output_digest==baseline
 conditions[0].end_metres=old_end;road.conditions=conditions
 for tex in [author.paint_texture,author.style_texture,author.macro_texture]:assert assets.save_loaded_asset(tex)
 assert les.save_current_level();yield 2
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL);author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
 assert author.output_digest==baseline and author.current_terrain_digest()==terrain;checks(author);report['save_reload_verified']=True
 for path,digest in json.loads((OUT/'install.json').read_text())['protected'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
 report.update(ok=True,protected_unchanged=True);save();les.load_level('/Engine/Maps/Entry');yield 3

def review():
 global play_world
 functional=json.loads((OUT/'roadconditions-functional.json').read_text());assert functional['ok']
 assert les.load_level(LEVEL)
 road=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralRoad) and a.get_actor_label().startswith('Road 01'))
 targets=[]
 for distance,name in [(2200,'RoadConditions_firm'),(7000,'RoadConditions_grass')]:
  p=road.control_points.get_location_at_distance_along_spline(distance,u.SplineCoordinateSpace.WORLD);targets.append((name,p))
 pool=max(functional['pool_examples'],key=lambda p:p['depth_cm']);targets.append(('RoadConditions_rut_pool',u.Vector(pool['x'],pool['y'],pool['z'])))
 tiles=[a for a in actors.get_all_level_actors() if isinstance(a,u.GTRoadReliefTile)]
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
 def bed(p):
  for t in tiles:
   o=t.get_actor_location();span=t.get_editor_property('span_cm')
   if o.x<=p.x<o.x+span and o.y<=p.y<o.y+span:return t.height_at(u.Vector2D(p.x,p.y))
  return author.base_height_at(u.Vector2D(p.x,p.y))
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);until=time.monotonic()+180;car=None
 while car is None:
  yield .5;play_world=u.EditorLevelLibrary.get_game_world()
  if play_world:pc=u.GameplayStatics.get_player_controller(play_world,0);car=u.GameplayStatics.get_player_pawn(play_world,0)
  assert time.monotonic()<until
 car.disable_input(pc);move=car.get_chaos_movement();move.set_throttle_input(0);move.set_brake_input(1);move.set_handbrake_input(True)
 # The water window follows the possessed pawn, otherwise the camera. Unpossess
 # the parked car so these stationary views exercise the water actually in view.
 pc.un_possess()
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(play_world,cmd,pc)
 sheet=next(s for s in u.GameplayStatics.get_all_actors_of_class(play_world,u.GTWaterSheet) if s.get_editor_property('water_domain'))
 report['images']=[];report['water_stats']=[];report['camera_positions']=[]
 camera=None
 for name,p in targets:
  if camera:camera.destroy_actor()
  p=u.Vector(p.x,p.y,bed(p)+40)
  pos=p+u.Vector(-150,-200,1200)
  pos.z=max(pos.z,bed(pos)+500)
  report['camera_positions'].append(dict(name=name,target=[p.x,p.y,p.z],camera=[pos.x,pos.y,pos.z]))
  camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(play_world,u.CameraActor,u.Transform(location=pos,rotation=u.MathLibrary.find_look_at_rotation(pos,p)),'RoadConditionReview')
  camera.get_component_by_class(u.CameraComponent).set_field_of_view(65);pc.set_view_target_with_blend(camera,0)
  # Stationary camera only; leave the unpossessed vehicle at its normal spawn.
  yield 12
  # PIE's initial camera handoff can replace the first view target after spawn.
  pc.set_view_target_with_blend(camera,0);yield 1
  actual=u.GameplayStatics.get_player_camera_manager(play_world,0).get_camera_location()
  report['camera_positions'][-1]['actual']=[actual.x,actual.y,actual.z]
  assert (actual-pos).length()<1,(actual,pos)
  sheet.water_diagnostics(True);yield 4
  stats=sheet.water_diagnostics(False);report['water_stats'].append(stats)
  if name=='RoadConditions_rut_pool':
   frames=re.search(r': (\d+) frames',stats);steps=re.search(r'/ (\d+) run',stats)
   assert frames and int(frames[1])>0 and steps and int(steps[1])>0,stats
   report['water_stepping_verified']=True
   probes=[u.Vector2D(q['x'],q['y']) for q in functional['pool_examples']]
   q=max(probes,key=lambda xy:sheet.review_water_column(xy).g)
   before=sheet.review_water_column(q);volume=sheet.add_impulse(q,60,1)
   samples=[]
   for _ in range(8):
    yield .1;c=sheet.review_water_column(q);samples.append([c.r,c.g,c.b,c.a])
   assert volume>0 and all(math.isfinite(v) for sample in samples for v in sample),(volume,samples)
   report['stationary_water_impulse']=dict(volume_m3=volume,before=[before.r,before.g,before.b,before.a],samples=samples)
  path=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(play_world,True);yield .3
  u.SystemLibrary.execute_console_command(play_world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
  until=time.monotonic()+45
  while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
  u.GameplayStatics.set_game_paused(play_world,False);report['images'].append(str(path));save()
 camera.destroy_actor();car=pc=sheet=camera=None;u.EditorLevelLibrary.editor_end_play();yield 3
 until=time.monotonic()+60
 while u.EditorLevelLibrary.get_game_world():assert time.monotonic()<until;yield .5
 play_world=None;report.update(ok=True,captures_complete=True);save();les.load_level('/Engine/Maps/Entry');yield 3
steps=run();deadline=0
def tick(dt):
 global busy,deadline,steps
 if busy:return
 busy=True
 try:
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle)
  if play_world:u.GameplayStatics.set_game_paused(play_world,False);u.EditorLevelLibrary.editor_end_play()
  u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
