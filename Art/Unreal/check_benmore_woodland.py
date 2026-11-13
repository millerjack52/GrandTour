"""Saved heightmap, moving detail, stationary support and visual checks. No driving."""
import unreal as u
from pathlib import Path
import json,time,traceback,array,hashlib,re,math
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreWoodland'
LEVEL='/Game/GrandTour/ArtTests/BenmoreWoodland/L_Benmore_Woodland'
data=json.loads((OUT/'authoring.json').read_text());report=dict(ok=False,images=[],driving_tested=False,sites={})
world=pc=car=camera=None;busy=False
def save():(OUT/'check.json').write_text(json.dumps(report,indent=2))
def settle(seconds):
 start=u.GameplayStatics.get_time_seconds(world)
 while u.GameplayStatics.get_time_seconds(world)-start<seconds:yield 0
def capture(name,pos,target):
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'WoodlandReview')
 camera.get_component_by_class(u.CameraComponent).set_field_of_view(65);pc.set_view_target_with_blend(camera,0);yield from settle(3)
 f=OUT/(name+'.png');stamp=time.time();u.GameplayStatics.set_game_paused(world,True);yield .3
 u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+f.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not f.exists() or f.stat().st_mtime<stamp:assert time.monotonic()<until;yield .3
 report['images'].append(str(f));u.GameplayStatics.set_game_paused(world,False);save()
def run():
 global world,pc,car
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(LEVEL)
 report['scanned_soil_override']=False
 for name in ['Terrain','Detail']:
  material=u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/M_'+name)
  nodes=list(u.MaterialEditingLibrary.get_material_expressions(material))
  assert not any(str(n.get_editor_property('desc'))=='WoodlandSoilDetail' for n in nodes)
  for key,prop in [('Color',u.MaterialProperty.MP_BASE_COLOR),('Normal',u.MaterialProperty.MP_NORMAL)]:
   marker=next((n for n in nodes if str(n.get_editor_property('desc'))=='WoodlandSoilDetailSource:'+key),None)
   active=u.MaterialEditingLibrary.get_material_property_input_node(material,prop)
   if marker:assert active==marker or (key=='Normal' and str(active.get_editor_property('desc'))=='WoodlandSunlitGround')
 material=nodes=marker=None
 for name in ['Terrain','Detail','Tread']:
  material=u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/M_'+name)
  nodes=list(u.MaterialEditingLibrary.get_material_expressions(material))
  codes=[str(n.get_editor_property('code')) for n in nodes if isinstance(n,u.MaterialExpressionCustom)]
  assert any('woodlandNoise.offset' in c and 'struct WoodlandGridNoise' in c for c in codes),name
 material=nodes=codes=None
 report['native_clod_displacement']=True
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 land=next(a for a in actors if isinstance(a,u.Landscape))
 rt=u.RenderingLibrary.create_render_target2d(editor,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);yield 10
 assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 6
 assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 4
 pixels=u.RenderingLibrary.read_render_target(editor,rt,False);heights=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
 report['terrain_sha256']=hashlib.sha256(heights.tobytes()).hexdigest();assert report['terrain_sha256']==data['terrain_sha256']
 editor=land=rt=None;actors=[]
 les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 22
 world=u.EditorLevelLibrary.get_game_world();assert world;pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0)
 assert isinstance(pc,u.GTMudLabController) and isinstance(car,u.GTCarPawn)
 car.disable_input(pc);move=car.get_chaos_movement()
 effects=u.GameplayStatics.get_all_actors_of_class(world,u.GTVehicleSurfaceEffects);assert effects and all(a.dust_intensity==0 for a in effects)
 dust=u.GameplayStatics.get_all_actors_of_class(world,u.GTDustLab);assert dust and all(a.intensity==0 and a.total_rate==0 and a.get_live_particles()==0 for a in dust)
 report['dust']=dict(coordinators=len(effects),emitters=len(dust),rate=0,live_particles=0)
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 60','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 surfaces=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface);visuals=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)
 assert len(surfaces)==len(visuals)==1;s=surfaces[0];v=visuals[0];assert v.follow_player_grid
 assert not u.GameplayStatics.get_all_actors_of_class(world,u.GTMudPatch)
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails) if a.generate_around_player)
 report['grass_material']=grass.grass_material.get_path_name()
 assert 'M_GrassRecovered' in report['grass_material']
 forests=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='Woodland_DenseForest']
 assert len(forests)==1
 report['forest_trees']=sum(c.get_instance_count() for c in forests[0].get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith('SM_Fir_'))
 assert report['forest_trees']>50000
 sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
 for idx,site in enumerate(data['sites'],1):
  name=site['name'];x,y=site['center'];z=site['center_height_cm'];pc.select_lane(idx);car.disable_input(pc);move.set_handbrake_input(True)
  poses=[]
  for _ in range(12):
   yield from settle(.5);p=car.get_actor_location();r=car.get_actor_rotation()
   poses.append(dict(z=p.z,pitch=r.pitch,roll=r.roll,speed_cm_s=car.get_velocity().length(),contacts=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)]))
  tail=poses[-4:];assert all(sum(p['contacts'])>=3 and abs(p['roll'])<20 and abs(p['pitch'])<20 and p['speed_cm_s']<40 for p in tail),(name,tail)
  assert max(p['z'] for p in tail)-min(p['z'] for p in tail)<4,(name,tail)
  at=v.get_actor_location();assert math.hypot(at.x-x,at.y-y)<1200
  sample=s.sample_surface(u.Vector2D(x,y));assert sample.granular_response==(name=='Ford') and sample.native_substance_response==(name!='Ford')
  candidates=[]
  for dx in range(-900,901,150):
   for dy in range(-900,901,150):
    if math.hypot(dx,dy)<350:continue
    q=s.sample_surface(u.Vector2D(x+dx,y+dy))
    if q.sinkage_cap_cm>5 and q.granular_response==(name=='Ford') and q.native_substance_response==(name!='Ford'):candidates.append((dx*dx+dy*dy,x+dx,y+dy))
  _,tx,ty=min(candidates);before=s.sample_surface(u.Vector2D(tx,ty))
  for _ in range(12):s.apply_review_soil_stroke(u.Vector2D(tx-100,ty),u.Vector2D(tx+100,ty),30,7 if name!='Bog' else 65,.35);yield from settle(.05)
  after=s.sample_surface(u.Vector2D(tx,ty));assert after.surface_delta_cm<before.surface_delta_cm-.3
  v.add_review_tread(u.Vector(tx-100,ty,0),u.Vector(tx+100,ty,0),30,.35,0)
  report['sites'][name]=dict(parked=poses,grid_center=[at.x,at.y],depth_cm=sample.sinkage_cap_cm,granular=sample.granular_response,native_mud=sample.native_substance_response,before_cm=before.surface_delta_cm,after_cm=after.surface_delta_cm,grass_instances=grass.grass.get_instance_count())
  assert 0<grass.grass.get_instance_count()<18000
  far=grass.distant_grass;coords=[];beyond_80=0
  assert grass.distant_grass_material and far.get_instance_count()>1000
  for i in range(far.get_instance_count()):
   p=far.get_instance_transform(i,True).translation;coords.append((round(p.x,2),round(p.y,2)))
   beyond_80+=math.hypot(p.x-x,p.y-y)>8000
  assert len(coords)==len(set(coords)),'Distance grass streaming duplicated cells'
  assert beyond_80>500,'Distance grass did not populate beyond the near ring'
  report['sites'][name]['distant_grass']={'count':len(coords),'beyond_80m':beyond_80,'unique':True}
  yield from capture(name+'_surface',(x+850,y-1100,z+550),(x,y,z+90))
  if name=='Road':
   yield from capture('Forest_track',(x-1300,y+1450,z+280),(x+150,y-150,z+90))
   # The distant landscape once wrote black/invalid normals while albedo was
   # present, creating an apparent shadow-distance wall. Keep both buffers.
   for buffer in ['BaseColor','WorldNormal']:
    u.SystemLibrary.execute_console_command(world,'viewmode VisualizeBuffer',pc)
    u.SystemLibrary.execute_console_command(world,'r.BufferVisualizationTarget '+buffer,pc)
    yield from capture('Forest_'+buffer,(x-1300,y+1450,z+280),(x+150,y-150,z+90))
   u.SystemLibrary.execute_console_command(world,'viewmode lit',pc)
  if name=='Bog':
   heights=[s.sample_surface(u.Vector2D(x+dx,y+dy)).surface_delta_cm for dx in range(-1200,1201,50) for dy in range(-1200,1201,50) if math.hypot(dx,dy)>400]
   report['bog_rest_relief_range_cm']=[min(heights),max(heights)];assert max(heights)-min(heights)>12
   yield from capture('Bog_relief_low',(x+650,y-950,z+150),(x-900,y+650,z-5))
   yield from capture('Bog_clods_close',(x+450,y-700,z+65),(x+200,y-200,z-8))
   if s.grass_is_visual_cover:
    dynamic=next(c for c in v.get_components_by_class(u.ProceduralMeshComponent) if c.get_name()=='NativeVisualGrid').get_material(0)
    assert isinstance(dynamic,u.MaterialInstanceDynamic)
    pos=(x+450,y-700,z+65);target=(x+200,y-200,z-8)
    dynamic.set_scalar_parameter_value('WoodlandSurfaceDetail',0)
    yield from capture('GroundStudy_baseline',pos,target)
    dynamic.set_scalar_parameter_value('WoodlandSurfaceDetail',1)
    yield from capture('GroundStudy_daylight',pos,target)
    for buffer in ['Roughness','WorldNormal','BaseColor']:
     u.SystemLibrary.execute_console_command(world,'viewmode VisualizeBuffer',pc)
     u.SystemLibrary.execute_console_command(world,'r.BufferVisualizationTarget '+buffer,pc)
     yield from capture('GroundStudy_'+buffer,pos,target)
    u.SystemLibrary.execute_console_command(world,'viewmode lit',pc)
    # Locate genuinely grass-covered deep mud: coverage must no longer select
    # a different physical law or erase the yielding layer.
    turf=[]
    for dx in range(-2400,2401,150):
     for dy in range(-2400,2401,150):
      q=s.sample_surface(u.Vector2D(x+dx,y+dy))
      if q.grass_cover>.5 and q.sinkage_cap_cm>30 and q.native_substance_response:turf.append((dx*dx+dy*dy,x+dx,y+dy,q))
    assert turf,'No grass-covered deep mud in review area'
    _,gx,gy,q=min(turf,key=lambda a:a[0]);before=q.surface_delta_cm
    for _ in range(12):s.apply_review_soil_stroke(u.Vector2D(gx-80,gy),u.Vector2D(gx+80,gy),32,20,.4);yield from settle(.05)
    after=s.sample_surface(u.Vector2D(gx,gy));assert after.surface_delta_cm<before-.3
    grass.apply_review_grass_contact(u.Vector2D(gx,gy),True)
    report['covered_mud']=dict(point=[gx,gy],grass=q.grass_cover,depth=q.sinkage_cap_cm,native=q.native_substance_response,before=before,after=after.surface_delta_cm)
    yield from capture('GroundStudy_covered_mud',(gx+350,gy-500,z+220),(gx,gy,z))
  if name=='Ford':
   near=[]
   for i in range(0,grass.grass.get_instance_count(),7):
    gt=grass.grass.get_instance_transform(i,True);gp=gt.translation;d=math.hypot(gp.x-x,gp.y-y)
    if 350<d<1800:near.append((d,gp))
   assert near
   gp=min(near,key=lambda a:a[0])[1]
   yield from capture('Grass_recovered',(gp.x+140,gp.y-210,gp.z+75),(gp.x,gp.y,gp.z+15))
   yield from capture('Grass_recovered_later',(gp.x+140,gp.y-210,gp.z+75),(gp.x,gp.y,gp.z+15))
   # The denser grass stream extends beyond the live deformation window. Use
   # the nearby instance just inspected, not an arbitrary array midpoint that
   # can lie outside the active soil field after edge-slot recycling.
   p=gp
   before=s.sample_surface(u.Vector2D(p.x,p.y));assert before.grass_cover>.1
   grass.apply_review_grass_contact(u.Vector2D(p.x,p.y),True)
   for _ in range(8):s.apply_review_soil_stroke(u.Vector2D(p.x-50,p.y),u.Vector2D(p.x+50,p.y),30,4,.3)
   yield from settle(.2);report['grass']=grass.grass_report();assert re.search(r'bent=[1-9]',report['grass'])
   report['grass_point']=[p.x,p.y];report['grass_deformed_cm']=s.sample_surface(u.Vector2D(p.x,p.y)).surface_delta_cm-before.surface_delta_cm
   assert report['grass_deformed_cm']<-.2
 # Returning to the ford proves detail and short grass move back, with contacts retained.
 pc.select_lane(2);car.disable_input(pc);move.set_handbrake_input(True);yield from settle(3)
 report['grass_return']=grass.grass_report();assert re.search(r'removed=[1-9]',report['grass_return'])
 x,y=data['sites'][1]['center'];z=data['sites'][1]['center_height_cm']
 yield from capture('River_woodland',(x+2200,y-3600,z+1600),(x,y,z))
 mats=[sheet.get_component_by_class(u.ProceduralMeshComponent).get_material(0)]+[a.static_mesh_component.get_material(0) for a in sheet.get_editor_property('domain_surfaces')]
 assert all(isinstance(m,u.MaterialInstanceDynamic) and m.get_scalar_parameter_value('AmbientReady')==1 for m in mats)
 tex=mats[0].get_texture_parameter_value('AmbientTex');assert all(m.get_texture_parameter_value('AmbientTex')==tex for m in mats)
 a=u.RenderingLibrary.read_render_target_raw_pixel(world,tex,100,150,False);yield from settle(.7);b=u.RenderingLibrary.read_render_target_raw_pixel(world,tex,100,150,False)
 report['wave_delta']=max(abs(a.r-b.r),abs(a.g-b.g),abs(a.b-b.b));assert report['wave_delta']>.0001
 fx=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerWheelEffects)[0]
 fx.review_wheel(u.Vector(x,y,z+30),3,12,.12,.22,.4);yield from settle(.2);report['water_fx']=fx.effect_report();fx.clear_review()
 report['surface']=s.get_surface_report();report['native_response']=move.native_substance_report();report['ok']=True;save();yield from finish()
def finish():
 global world,pc,car,camera
 if world:u.GameplayStatics.set_game_paused(world,False)
 u.EditorLevelLibrary.editor_end_play();yield 4;world=pc=car=camera=None
 u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_set_viewport_realtime(True)
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global steps,deadline,busy,failed
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<840,'Deadline'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  steps=None;import gc;gc.collect();u.SystemLibrary.collect_garbage();u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
 except Exception:
  report['ok']=False;report['error']=traceback.format_exc();save();u.log_error(report['error'])
  if failed:u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
