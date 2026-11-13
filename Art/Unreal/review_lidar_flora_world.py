"""Actual saved-map Unreal views, near/mid/far, with native runtime grass active."""
from pathlib import Path
R=Path('C:/GrandTour')
exec(compile((R/'Art/Unreal/check_lidar_flora.py').read_text().split('\nsteps=run();')[0],'<flora-review-helpers>','exec'))
OUT=R/'Art/Export/LidarStudy/FloraWorld';PHASE='review';report=dict(ok=False,images=[],timings={},views=[])

def runtime_capture(name,pos,target,is_long=False):
 """Capture the settled game viewport: HighResShot silently forces LOD0."""
 global camera
 if camera:camera.destroy_actor()
 p=u.Vector(*pos);t=u.Vector(*target)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=p,rotation=u.MathLibrary.find_look_at_rotation(p,t)),'FloraRuntimeReview')
 camera.camera_component.set_field_of_view(68)
 camera.camera_component.set_editor_property('aspect_ratio',16./9 if is_long else 1.6)
 camera.camera_component.set_editor_property('constrain_aspect_ratio',True)
 pc.set_view_target_with_blend(camera,0);yield from settle(5)
 path=OUT/(name+'.png');stamp=time.time()
 u.SystemLibrary.execute_console_command(world,'Shot -nosuffix filename="'+path.as_posix()+'"',pc)
 until=time.monotonic()+45
 while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until,'Viewport capture timeout';yield .3
 report['images'].append(str(path));save()

capture=lambda name,pos,target:runtime_capture(name,pos,target,False)
long_capture=lambda name,pos,target:runtime_capture(name,pos,target,True)
def run():
 global world,pc,car,camera
 les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
 rows=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
 import install_lidar_flora_world as integrity
 integrity.verify(rows);report['saved_map_integrity']=dict(integrity.report)
 report['polish_shader_checks']=[]
 for material_path in u.EditorAssetLibrary.list_assets('/Game/GrandTour/ArtTests/LidarStudy/FloraWorld/Foliage',True,False):
  m=u.load_asset(material_path)
  if isinstance(m,u.Material):
   for n in u.MaterialEditingLibrary.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='PathPainterlyCoverage':
     assert 'StateFrameIndex' not in str(n.get_editor_property('code'));report['polish_shader_checks'].append(m.get_name())
 assert len(report['polish_shader_checks'])>=3,'Expected painted foliage shader checks'
 cfg=json.loads((OUT/'profile.json').read_text())
 if cfg.get('art_direction',{}).get('enabled',False):
  report['art_direction_checks']=[]
  for folder in ['Foliage','InteractiveGrass']:
   for material_path in u.EditorAssetLibrary.list_assets(integrity.D+'/'+folder,True,False):
    mat=u.load_asset(material_path)
    if not isinstance(mat,u.Material):continue
    nodes=[n for n in u.MaterialEditingLibrary.get_material_expressions(mat) if str(n.get_editor_property('desc'))=='FloraReferenceVolumes']
    if not nodes:continue
    assert not any(isinstance(n,u.MaterialExpressionTextureSample) for n in nodes),'Art pass unexpectedly added texture fetches'
    base=u.MaterialEditingLibrary.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
    assert str(base.get_editor_property('desc'))=='FloraReferenceVolumes'
    report['art_direction_checks'].append(dict(material=mat.get_name(),parameters={str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value') for n in nodes if isinstance(n,u.MaterialExpressionScalarParameter)}))
  assert len(report['art_direction_checks'])>=15,'Expected map-wide volume pigment treatment'
 author=next(a for a in rows if isinstance(a,u.GTProceduralGround));g=GroundSampler(author)
 route=trial.route(json.loads((ROOT/'Art/Export/LidarStudy/Place/roads.json').read_text()))
 controller=next(a for a in rows if isinstance(a,u.GTDistanceStyleController));controller.finish_review_shaders()
 report['profile']=controller.profile.get_path_name();report['ground_digest']=str(author.output_digest)
 report['map_sha256']=hashlib.sha256((R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap').read_bytes()).hexdigest()
 views=[]
 for name,s,off,height,look in [('approach',185.,-.8,170.,200.),('mud',211.,-.7,125.,221.),('bank',229.,-2.,180.,239.),('woodland',355.,9.,170.,370.),('upper_road',560.,-.8,170.,575.)]:
  x,y,yaw=trial.at(route,s,off);tx,ty,_=trial.at(route,look,5. if name=='bank' else off)
  views.append(dict(name=name,station=s,position=[x,y,g.height(x,y)+height],target=[tx,ty,g.height(tx,ty)+100],long=False))
 prior=json.loads((R/'Art/Export/LidarStudy/FloraIntegration/longrange-report.json').read_text())
 for v in prior['views']:views.append(dict(v,long=True))
 report['views']=views;save();les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1920,1080)
 until=time.monotonic()+180
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<until;yield .5
 pc.possess(car);car.disable_input(pc);car.reset_driving_inputs();mv=car.get_chaos_movement();mv.set_handbrake_input(True)
 report['runtime_settings']={k:u.SystemLibrary.get_console_variable_float_value(k) for k in ['r.ScreenPercentage','r.StaticMeshLODDistanceScale','r.ForceLOD','r.AntiAliasingMethod','r.Shadow.Virtual.NonNanite.IncludeInCoarsePages','r.Shadow.Virtual.SMRT.RayCountDirectional','r.Shadow.Virtual.ResolutionLodBiasDirectional']}
 report['runtime_fog']=[dict(label=a.get_name(),height=a.get_actor_location().z,tags=[str(t) for t in a.tags],density=a.component.fog_density,falloff=a.component.fog_height_falloff,start=a.component.start_distance,volumetric=a.component.enable_volumetric_fog) for a in u.GameplayStatics.get_all_actors_of_class(world,u.ExponentialHeightFog)]
 cfg=json.loads((OUT/'profile.json').read_text())
 assert all(abs(f['density']-cfg['fog_density'])<.0001 and f['volumetric']==cfg.get('volumetric_fog',True) for f in report['runtime_fog']), 'Runtime weather replaced the authored map atmosphere'
 report['runtime_lights']=[dict(rotation=[a.get_actor_rotation().pitch,a.get_actor_rotation().yaw,a.get_actor_rotation().roll],intensity=a.light_component.intensity) for a in u.GameplayStatics.get_all_actors_of_class(world,u.DirectionalLight)]
 for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','t.MaxFPS 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0','gt.Perf.LogSpikes 1','showhud']:u.SystemLibrary.execute_console_command(world,cmd,pc)
 mesh=car.get_component_by_class(u.SkeletalMeshComponent)
 for v in views:
  x,y,yaw=trial.at(route,v['station']-7);car.set_actor_location_and_rotation(u.Vector(x,y,g.height(x,y)+80),u.Rotator(yaw=yaw),False,True)
  mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield from settle(7)
  yield from (long_capture if v['long'] else capture)('review_'+v['name'],v['position'],v['target'])
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Reset',pc);report['timings'][v['name']]=yield from frame_window(4)
  u.SystemLibrary.execute_console_command(world,'gt.Perf.Dump FLORA_WORLD_'+v['name'],pc);save()
 # Exercise the unchanged host's contact path against the new material contract.
 grass=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTMixedGroundDetails))
 component=grass.grass;assert component.get_instance_count()>0
 p=component.get_instance_transform(0,True).translation;before=grass.grass_report()
 contact_pos=[p.x-120,p.y-150,p.z+220];contact_target=[p.x,p.y,p.z+15]
 yield from capture('contact_before',contact_pos,contact_target)
 grass.apply_review_grass_contact(u.Vector2D(p.x,p.y),True);yield from settle(.3)
 yield from capture('contact_after',contact_pos,contact_target)
 after=grass.grass_report();assert int(re.search(r'removed=(\d+)',after).group(1))>int(re.search(r'removed=(\d+)',before).group(1))
 report['grass_contact_probe']=dict(before=before,after=after,scope='Native contact API and material input contract; not a full driving test')
 report['ok']=True;report['timing_scope']='Hidden editor tick intervals, not a standalone GPU benchmark';report['capture_method']='Normal game viewport Shot; gameplay LODs and temporal rendering retained. Earlier HighResShot images forced LOD0.';save()
 rows=author=g=mesh=mv=controller=grass=component=None;gc.collect();yield from finish()
steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
 global deadline,busy,steps,failed
 if measure_frames and dt>0:frame_samples.append(dt)
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1800,'Whole-map review timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error'])
  if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
