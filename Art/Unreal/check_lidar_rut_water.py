"""Live-bed regression and real wheel inputs in L_LidarStudy, PIE only."""
from pathlib import Path
import os
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
import lidar_logging_trial as trial
report=dict(ok=False,images=[],basins=[],deformation={})

def save():
 (OUT/'rutwatercheck.json').write_text(json.dumps(report,indent=2))
 if os.environ.get('GT_RUT_SPRAY_REVIEW')=='1':(OUT/'rutwater-spray-review.json').write_text(json.dumps(report,indent=2))
def numbers(s):return {k:float(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+)',s)}

def capture(name,pos,target,delay=.1):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'RutWaterReview')
 camera.camera_component.set_field_of_view(68);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
 pc.set_view_target_with_blend(camera,0);yield from settle(delay)
 u.GameplayStatics.set_game_paused(world,True);yield .3
 f=OUT/(name+'.png');stamp=time.time()
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+f.as_posix()+'"',pc)
 until=time.monotonic()+30
 while not f.exists() or f.stat().st_mtime<stamp:assert time.monotonic()<until;yield .2
 report['images'].append(str(f));u.GameplayStatics.set_game_paused(world,False);save()

def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 refs=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 author=next(a for a in refs if isinstance(a,u.GTProceduralGround));tiles=list(author.relief_tiles.values())
 assert str(author.output_digest)==json.loads((OUT/'rutwater.json').read_text())['ground_digest']
 domain=next(a for a in refs if isinstance(a,u.GTWaterSheet) and a.get_editor_property('water_domain'))
 seed=list(domain.get_editor_property('water_domain').road_patches)[-1]
 raw=list(seed.samples);origin=seed.origin_cm;cell=seed.cell_cm;w=seed.size_x
 wet=[(origin.x+(i%w+.5)*cell,origin.y+(i//w+.5)*cell,raw[4*i],raw[4*i+1]) for i in range(len(raw)//4) if raw[4*i+1]>.005]
 def ground(x,y):
  for t in tiles:
   o=t.get_actor_location()
   if o.x<=x<o.x+t.span_cm and o.y<=y<o.y+t.span_cm:return t.height_at(u.Vector2D(x,y))
  return author.base_height_at(u.Vector2D(x,y))
 path=trial.route(json.loads((OUT/'roads.json').read_text()))
 ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 if os.environ.get('GT_RUT_SKIP_AUTOMATION')!='1':
  u.SystemLibrary.execute_console_command(ew,'Automation RunTests GrandTour.Water+GrandTour.MudRunner.EmitterLuaOracle+GrandTour.LandscapeMud.MovingWaterBed')
  yield 30
  while u.AutomationLibrary.are_automated_tests_running():yield .25
 ew=None
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
 until=time.monotonic()+180
 while not world or not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:
   pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
 mv=car.get_chaos_movement();body=car.get_component_by_class(u.SkeletalMeshComponent)
 surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
 sheets=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)
 pools=[s for s in sheets if s.get_editor_property('mud_initial_domain')]
 assert len(pools)==4
 runtime_domain=next(s for s in sheets if s.get_editor_property('water_domain'))
 assert len(runtime_domain.get_editor_property('water_domain').road_patches)==3,'Baked duplicate still active'
 fx=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerWheelEffects);assert len(fx)==1;fx=fx[0]
 assert len(fx.materials)==9 and all(fx.materials)
 report['spray_materials']=[m.get_path_name() for m in fx.materials]
 assert all('/LidarStudy/RutWater/M_Spray_' in p for p in report['spray_materials'])
 for m in fx.materials:
  n=u.MaterialEditingLibrary.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)
  assert 'View.OneOverPreExposure' in n.get_editor_property('code')
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','gt.Perf.LogSpikes 1','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 if os.environ.get('GT_RUT_SPRAY_REVIEW')=='1':
  report['scope']='Close visual/readback review; deformation regression is archived separately'
  x,y,yaw=trial.at(path,214)
  car.set_actor_location_and_rotation(u.Vector(x,y,ground(x,y)+85),u.Rotator(yaw=yaw),False,True)
  body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());mv.set_handbrake_input(True)
  yield from settle(3)
  pool=min(pools,key=lambda s:(s.get_actor_location().x-x)**2+(s.get_actor_location().y-y)**2)
  mats=[c.get_material(0) for c in pool.get_components_by_class(u.ProceduralMeshComponent)]
  material=next(m for m in mats if isinstance(m,u.MaterialInstanceDynamic))
  state=material.get_texture_parameter_value('MRWaterState');sediment=material.get_texture_parameter_value('MRWaterSediment')
  assert isinstance(state,u.TextureRenderTarget2D) and isinstance(sediment,u.TextureRenderTarget2D)
  def pixels():
   # Small sparse GPU readback, outside the performance window.
   return [[v.r,v.g,v.b] for rt in [state,sediment] for yy in range(10,50,8) for xx in range(10,50,8)
           for v in [u.RenderingLibrary.read_render_target_raw_pixel(world,rt,xx,yy,False)]]
  report['native_before']=pixels();initial=numbers(fx.effect_report())
  # Diagnostic views only: hide fern instances in PIE to expose the wheel contact.
  # This never changes or saves the authored LiDAR vegetation.
  hidden_vegetation=[]
  for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if c.is_visible():c.set_visibility(False);hidden_vegetation.append(c)
  report['diagnostic_vegetation_hidden']=True
  report['placements']=[]
  fxmesh=fx.get_component_by_class(u.ProceduralMeshComponent)
  report['emitter_render']=dict(transform=str(fx.get_actor_transform()),relative_location=str(fxmesh.get_editor_property('relative_location')),
     visible=fxmesh.is_visible(),hidden=fx.get_editor_property('hidden'),owner_no_see=fxmesh.get_editor_property('owner_no_see'),only_owner_see=fxmesh.get_editor_property('only_owner_see'))
  mv.set_handbrake_input(False);mv.set_target_gear(1,True);mv.set_throttle_input(.85)
  for index in range(3):
   yield from settle(.6)
   report['placements'].append(fx.placement_report())
   report['emitter_render']['bounds']=str(u.SystemLibrary.get_component_bounds(fxmesh));report['emitter_render']['sections']=fxmesh.get_num_sections();save()
   p=car.get_actor_location();fxv,fyv=math.cos(math.radians(yaw)),math.sin(math.radians(yaw));rx,ry=-fyv,fxv
   yield from capture('RutWater_spray_'+str(index),(p.x-fxv*180+rx*400,p.y-fyv*180+ry*400,p.z+100),(p.x-fxv*100,p.y-fyv*100,p.z-30))
  report['native_after']=pixels();report['native_changed']=max(abs(a-b) for va,vb in zip(report['native_before'],report['native_after']) for a,b in zip(va,vb))
  report['emissions']={k:v-initial.get(k,0) for k,v in numbers(fx.effect_report()).items() if k!='alive'}
  assert report['native_changed']>.001 and report['emissions']['water_small']>0
  for c in hidden_vegetation:c.set_visibility(True)
  hidden_vegetation=[]
  p=car.get_actor_location()
  yield from capture('RutWater_spray_in_map',(p.x-fxv*450,p.y-fyv*450,p.z+230),(p.x-fxv*100,p.y-fyv*100,p.z-25))
  mv.set_throttle_input(0);mv.set_handbrake_input(True);report['ok']=True;save()
  refs=author=tiles=ground=seed=surface=pool=pools=sheets=runtime_domain=body=mv=fx=state=sediment=material=mats=pixels=None
  yield from finish();return
 for station in [214,290,552,667]:
  x,y,yaw=trial.at(path,station)
  car.set_actor_location_and_rotation(u.Vector(x,y,ground(x,y)+85),u.Rotator(yaw=yaw),False,True)
  body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector());mv.set_handbrake_input(True)
  yield from settle(4)
  pool=min(pools,key=lambda s:(s.get_actor_location().x-x)**2+(s.get_actor_location().y-y)**2)
  before=numbers(pool.mud_water_diagnostics());assert before['native_steps']>0 and before['awake']==1,before
  report['basins'].append(dict(station=station,before=before))
  assert sum(numbers(s.mud_water_diagnostics())['awake'] for s in pools)==1
  # Real car inputs, not ReviewWheel's synthetic particle emission.
  initial=numbers(fx.effect_report());mv.set_handbrake_input(False);mv.set_target_gear(1,True);mv.set_throttle_input(.85)
  yield from settle(4)
  mv.set_throttle_input(0);mv.set_handbrake_input(True)
  after=numbers(fx.effect_report());report['basins'][-1]['wheel_emissions']={k:after[k]-initial.get(k,0) for k in after if k!='alive'}
  report['basins'][-1]['after']=numbers(pool.mud_water_diagnostics());save()
  p=car.get_actor_location();cx,cy,_=trial.at(path,station-4)
  yield from capture('RutWater_drive_'+str(station),(cx,cy,ground(cx,cy)+260),(p.x,p.y,p.z-35),.1)
 # Open a short connection from existing water into an initially dry shore.
 # This changes only the transient PIE soil; the saved route stays untouched.
 station=214;x,y,yaw=trial.at(path,station)
 cx,cy,cyaw=trial.at(path,station-12)
 car.set_actor_location_and_rotation(u.Vector(cx,cy,ground(cx,cy)+85),u.Rotator(yaw=cyaw),False,True)
 body.set_physics_linear_velocity(u.Vector());mv.set_handbrake_input(True);yield from settle(3)
 pool=min(pools,key=lambda s:(s.get_actor_location().x-x)**2+(s.get_actor_location().y-y)**2)
 candidates=[]
 for wx,wy,z,d in wet:
  if (wx-x)**2+(wy-y)**2>1000**2:continue
  if not pool.covers(u.Vector2D(wx,wy)) or surface.sample_surface(u.Vector2D(wx,wy)).water_depth_cm<3:continue
  z=pool.surface_cm_at(u.Vector2D(wx,wy))
  for dx,dy in [(25,0),(-25,0),(0,25),(0,-25)]:
   px,py=wx+dx,wy+dy;q=u.Vector2D(px,py)
   if pool.covers(q):continue
   soil=surface.sample_surface(q)
   if soil.sinkage_cap_cm<25:continue
   gap=ground(px,py)+soil.surface_delta_cm-z
   if 0<gap<15:candidates.append((gap,wx,wy,px,py))
 assert candidates,'No suitable dry shoreline for live deformation regression'
 gap,wx,wy,px,py=min(candidates)
 initial=numbers(pool.mud_water_diagnostics());before_depth=surface.sample_surface(u.Vector2D(px,py)).water_depth_cm
 soil_before=surface.sample_surface(u.Vector2D(px,py)).surface_delta_cm
 surface.apply_review_soil_stroke(u.Vector2D(wx,wy),u.Vector2D(px+(px-wx)*3,py+(py-wy)*3),70.,35.,.8)
 yield from settle(6)
 final=numbers(pool.mud_water_diagnostics());after_depth=surface.sample_surface(u.Vector2D(px,py)).water_depth_cm
 report['deformation']=dict(point=[px,py],source=[wx,wy],gap_cm=gap,soil_before_cm=soil_before,soil_after_cm=surface.sample_surface(u.Vector2D(px,py)).surface_delta_cm,before_depth_cm=before_depth,after_depth_cm=after_depth,before=initial,after=final,covers=pool.covers(u.Vector2D(px,py)))
 save()
 assert report['deformation']['covers'] and after_depth>before_depth+.5,report['deformation']
 assert final['bed_updates']>initial['bed_updates']
 assert abs(final['volume_m3']-initial['volume_m3'])<max(.001,initial['volume_m3']*.001)
 assert sum(b['wheel_emissions'].get('water_small',0) for b in report['basins'])>0,'No recovered water spray from actual driving'
 yield from capture('RutWater_opened_rut',(px+280,py+180,ground(px,py)+190),(px,py,ground(px,py)-10))
 u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc)
 report['timing']=yield from frame_window(5)
 u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump RutWater',pc)
 report['ok']=True;save()
 refs=author=tiles=ground=seed=surface=pool=pools=sheets=runtime_domain=body=mv=fx=None
 yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if measure_frames and dt>0:frame_samples.append(dt)
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1200
  if time.monotonic()>=deadline:
   delay=next(steps);deadline=time.monotonic()+delay
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
