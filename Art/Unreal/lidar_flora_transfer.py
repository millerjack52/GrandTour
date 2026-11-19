"""Audit and transfer the reviewed FloraTrail foliage treatment to LiDAR."""
import unreal as u,json,sys,os,time,traceback,hashlib,gc,struct,math
from pathlib import Path
R=Path('C:/GrandTour');sys.path[:0]=[str(R/'Art/Unreal'),str(R/'Art')]
from lidar_flora_transfer_baseline import verify,sha,MAP as MAPFILE
from benmore_river_life_materials import props,Graph
BASE='/Game/GrandTour/ArtTests/LidarStudy';MAP=BASE+'/L_LidarStudy';D=BASE+'/FloraTrailStyle/v1'
O=R/'Art/Export/LidarFloraTransfer';O.mkdir(parents=True,exist_ok=True)
stage=os.environ.get('GT_LIDAR_TRANSFER_STAGE','audit');L=u.get_editor_subsystem(u.LevelEditorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
report={'ok':False,'stage':stage,'images':[]};state={'busy':False,'due':0,'frame':0};world=pc=car=camera=None
def save():(O/(stage+'-report.json')).write_text(json.dumps(report,indent=2))
def path(x):return x.get_path_name() if x else None
def value(v):
 if hasattr(v,'to_tuple'):return list(v.to_tuple())
 if isinstance(v,(str,int,float,bool)):return v
 return str(v)
def fields(x,names):
 d={}
 for name in names:
  try:d[name]=value(x.get_editor_property(name))
  except Exception:pass
 return d
def actors():return u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
def original_path(m):return E.get_metadata_tag(m,'LidarTransferSource') or path(m) if m else None
def protected():
 rows=[];systems={};roads=[]
 for a in actors():
  label=a.get_actor_label()
  if isinstance(a,(u.DirectionalLight,u.SkyLight)):systems[label]={'rotation':value(a.get_actor_rotation()),**fields(a.light_component,['intensity','light_color','temperature','use_temperature'])}
  if isinstance(a,u.ExponentialHeightFog):systems[label]=fields(a.component,['fog_density','fog_height_falloff','start_distance','enable_volumetric_fog','fog_inscattering_luminance'])
  if isinstance(a,u.PostProcessVolume):systems[label]={'priority':a.priority,'weight':a.blend_weight,'blendables':[[b.weight,original_path(b.object)] for b in a.settings.weighted_blendables.array],**fields(a.settings,['auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','color_gamma_shadows','color_gain_shadows','tone_curve_amount'])}
  if isinstance(a,u.GTProceduralGround):systems['ground']={'digest':str(a.output_digest),'material':path(a.relief_material)}
  if isinstance(a,u.GTLandscapeSurface):systems['soil']=fields(a,['layer_depth_scale','maximum_layer_depth_cm','bearing_strength','settlement_speed_scale','grass_is_visual_cover','use_native_mud_shader_updates'])
  if isinstance(a,u.GTMudRunnerVisual):systems['mud']={'material':path(a.material),'tread':path(a.track_material),**fields(a,['follow_player_grid','half_size_cm'])}
  if isinstance(a,u.GTWaterSheet):systems[label]={'position':value(a.get_actor_location()),**fields(a,['water_material','depth_cm','flow_speed'])}
  if isinstance(a,u.GTProceduralRoad):roads.append([label,[list(a.control_points.get_location_at_spline_point(i,u.SplineCoordinateSpace.WORLD).to_tuple()) for i in range(a.control_points.get_number_of_spline_points())]])
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh:continue
   count=c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1;h=hashlib.sha256()
   for i in range(count):
    t=c.get_instance_transform(i,True) if isinstance(c,u.InstancedStaticMeshComponent) else c.get_world_transform()
    h.update(struct.pack('10d',*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()))
   rows.append({'actor':label,'component':c.get_name(),'mesh':path(c.static_mesh),'count':count,'transforms':h.hexdigest(),'materials':[original_path(m) for m in c.get_materials()],'collision':str(c.get_collision_enabled()),**fields(c,['visible','hidden_in_game','instance_start_cull_distance','instance_end_cull_distance','forced_lod_model','min_lod'])})
 return {'systems':systems,'roads':sorted(roads),'components':sorted(rows,key=lambda v:(v['actor'],v['component']))}
def make_views():
 from lidar_grounding import GroundSampler
 g=GroundSampler(next(a for a in actors() if isinstance(a,u.GTProceduralGround)))
 road=next(a for a in actors() if isinstance(a,u.GTProceduralRoad) and 'Logging mud' in a.get_actor_label());s=road.control_points
 views=[]
 for name,station,off,height in [('road',185,-80,170),('bank',229,-200,180),('canopy',355,900,170)]:
  p=s.get_location_at_distance_along_spline(station*100,u.SplineCoordinateSpace.WORLD);d=s.get_direction_at_distance_along_spline(station*100,u.SplineCoordinateSpace.WORLD);p+=u.Vector(-d.y*off,d.x*off,0)
  t=s.get_location_at_distance_along_spline((station+15)*100,u.SplineCoordinateSpace.WORLD)
  views.append({'name':name,'position':[p.x,p.y,g.height(p.x,p.y)+height],'target':[t.x,t.y,g.height(t.x,t.y)+100]})
 for v in json.loads((R/'Saved/LidarAuthoringQA/ValleyGround/cameras.json').read_text()):
  if v['view'] in ('V02','V03'):views.append({'name':'valley' if v['view']=='V02' else 'long_valley','position':v['position'],'target':v['target']})
 return views
def cmd(s):u.SystemLibrary.execute_console_command(world,s,pc)
def frames(n):
 end=state['frame']+n
 while state['frame']<end:yield 0
def look(v):
 p=u.Vector(*v['position']);t=u.Vector(*v['target']);camera.set_actor_location(p,False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(p,t),False)
def shot(name,settle=80):
 yield from frames(settle);p=O/(name+'.png');stamp=time.time();cmd('Shot filename="'+p.as_posix()+'" -nosuffix');end=time.monotonic()+60
 while not p.exists() or p.stat().st_mtime<stamp:assert time.monotonic()<end,name;yield .25
 data=p.read_bytes()[:24];report['images'].append({'name':name,'size':[int.from_bytes(data[16:20],'big'),int.from_bytes(data[20:24],'big')]});save()
def capture():
 global world,pc,car,camera
 views=json.loads((O/'views.json').read_text());report['views']=views
 L.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
 end=time.monotonic()+240
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<end;yield 1
 car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True);car.set_actor_hidden_in_game(True)
 for c in json.loads((R/'Art/lidar_performance.json').read_text())['commands']:cmd(c)
 for c in ('DisableAllScreenMessages','ShowHUD','r.MotionBlurQuality 0','r.Streaming.FullyLoadUsedTextures 1'):cmd(c)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'LidarTransferCamera');camera.camera_component.set_field_of_view(68);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0)
 pc.set_tickable_when_paused(True);pc.set_editor_property('should_perform_full_tick_when_paused',True);camera.set_tickable_when_paused(True)
 yield 20
 report['runtime_quality']={k:u.SystemLibrary.get_console_variable_float_value(k) for k in ['r.ScreenPercentage','r.StaticMeshLODDistanceScale','r.AntiAliasingMethod']}
 for v in views:
  u.GameplayStatics.set_game_paused(world,False);look(v);car.set_actor_location(u.Vector(*v['position'])-u.Vector(0,0,90),False,True);yield 10
  u.GameplayStatics.set_game_paused(world,True);yield from shot(stage+'_'+v['name'])
  if v['name']=='canopy':
   for i in range(12):
    look({**v,'position':[v['position'][0]+i*12,*v['position'][1:]]});yield from shot(stage+'_move_%02d'%i,8)
 u.GameplayStatics.set_game_paused(world,False);pc.set_view_target_with_blend(car,0);u.EditorLevelLibrary.editor_end_play();yield 5
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();pc=car=camera=None
def material(m):
 data={'path':path(m),'type':m.get_class().get_name()}
 if isinstance(m,u.MaterialInstanceConstant):data.update(parent=path(m.get_editor_property('parent')),scalars=str(m.get_editor_property('scalar_parameter_values')),vectors=str(m.get_editor_property('vector_parameter_values')));return data
 if not isinstance(m,u.Material):return data
 data.update(fields(m,['shading_model','tangent_space_normal','two_sided','blend_mode']))
 data['nodes']=[]
 for n in M.get_material_expressions(m):
  d={'name':n.get_name(),'type':n.get_class().get_name(),'desc':str(n.get_editor_property('desc'))}
  d.update(fields(n,['parameter_name','default_value','code','coordinate_index']))
  if isinstance(n,(u.MaterialExpressionTextureSample,u.MaterialExpressionTextureObject)):
   t=n.get_editor_property('texture');d['texture']=path(t)
  data['nodes'].append(d)
 data['outputs']={p.name:path(M.get_material_property_input_node(m,p)) for p in (u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_SUBSURFACE_COLOR,u.MaterialProperty.MP_AMBIENT_OCCLUSION,u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK)}
 return data
def audit():
 rows=actors();report.update(map_sha256=sha(MAPFILE),components=[],lights=[],fog=[],postprocess=[],actors=[],materials={})
 mats=set()
 for a in rows:
  label=a.get_actor_label();report['actors'].append({'label':label,'type':a.get_class().get_name(),'position':value(a.get_actor_location())})
  if isinstance(a,(u.DirectionalLight,u.SkyLight)):report['lights'].append({'label':label,'rotation':value(a.get_actor_rotation()),**fields(a.light_component,['intensity','light_color','temperature','use_temperature'])})
  if isinstance(a,u.ExponentialHeightFog):report['fog'].append({'label':label,**fields(a.component,['fog_density','fog_height_falloff','start_distance','enable_volumetric_fog','fog_inscattering_luminance'])})
  if isinstance(a,u.PostProcessVolume):
   s=a.settings;report['postprocess'].append({'label':label,'priority':a.priority,'weight':a.blend_weight,**fields(s,['auto_exposure_method','auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','color_gamma_shadows','color_gain_shadows','tone_curve_amount']),'blendables':[{'weight':b.weight,'path':path(b.object)} for b in s.weighted_blendables.array]})
   mats.update(b.object for b in s.weighted_blendables.array if b.object)
  if isinstance(a,u.GTDistanceStyleController):report['style']={'profile':path(a.profile),**fields(a.profile,['strength','palette_strength','normal_simplification','finish_strength','canopy_depth_strength','haze_intensity','haze_start_metres','haze_full_metres'])}
  if isinstance(a,u.GTProceduralGround):report['ground']={'digest':str(a.output_digest),'material':path(a.relief_material)}
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh:continue
   ms=list(c.get_materials());n=c.get_instance_count() if isinstance(c,u.InstancedStaticMeshComponent) else 1
   report['components'].append({'actor':label,'component':c.get_name(),'mesh':path(c.static_mesh),'count':n,'materials':[path(m) for m in ms],**fields(c,['visible','hidden_in_game','instance_start_cull_distance','instance_end_cull_distance','forced_lod_model','min_lod'])})
   if 'FloraWorld' in label or 'FloraIntegration' in label:mats.update(m for m in ms if m)
 pending=list(mats)
 while pending:
  m=pending.pop()
  if path(m) in report['materials']:continue
  report['materials'][path(m)]=material(m)
  if isinstance(m,u.MaterialInstanceConstant):pending.append(m.get_editor_property('parent'))
 save()
def run():
 global world
 report['protected_packages']=verify(stage not in ('audit','before'))
 if stage=='prepare':
  import lidar_flora_transfer_materials as transfer
  report['materials']=transfer.prepare(json.loads((O/'audit-report.json').read_text()));report['ok']=True;save();yield 3;return
 assert L.load_level(MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();yield 4
 if stage=='audit':audit()
 elif stage=='before':
  p=protected();(O/'invariants.json').write_text(json.dumps(p));(O/'views.json').write_text(json.dumps(make_views(),indent=2));report['invariants_captured']=True
  yield from capture();assert sha(MAPFILE)==json.loads((O/'baseline.json').read_text())['hashes']['Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap']
 else:
  expected=json.loads((O/'invariants.json').read_text());before=protected()
  # The initial baseline records geometry and systems; lighting is also compared
  # immediately around installation and held in the saved verification manifest.
  assert before['components']==expected['components'] and before['roads']==expected['roads']
  for k,v in expected['systems'].items():assert before['systems'][k]==v,k
  if stage=='install':
   import lidar_flora_transfer_materials as transfer
   report['transfer']=transfer.install(world);save()
   assert protected()==before,'Transfer altered geometry, lighting or driving systems'
   assert L.save_current_level();report['saved_map_sha256']=sha(MAPFILE);save()
   (O/'installed-invariants.json').write_text(json.dumps(before))
   assert L.load_level('/Engine/Maps/Entry');assert L.load_level(MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
  else:
   installation=json.loads((O/'install-report.json').read_text());assert installation['ok'];assert sha(MAPFILE)==installation['saved_map_sha256']
   report['transfer']=installation['transfer'];report['saved_map_sha256']=sha(MAPFILE)
  assert protected()==json.loads((O/'installed-invariants.json').read_text())
  report['invariants_preserved']=True
  report['bindings_verified']=0
  rows={a.get_actor_label():a for a in actors()}
  for b in report['transfer']['bindings']:
   c=next(c for c in rows[b['actor']].get_components_by_class(u.StaticMeshComponent) if c.get_name()==b['component'])
   assert path(c.get_material(b['slot']))==b['copy'];report['bindings_verified']+=1
   if 'Path_Leaf_0' in b['copy']:
    mid=u.MaterialLibrary.create_dynamic_material_instance(world,c.get_material(b['slot']))
    values={key:mid.get_scalar_parameter_value(key) for key in ('LeafTransmission','CrownOcclusion','CrownVolume','CrownCard')}
    for key,v in values.items():assert abs(v-report['transfer']['settings'][key])<1e-6,(key,v)
    report.setdefault('leaf_defaults_verified',{})[b['copy']]=values
  pp=next(a for a in actors() if a.get_actor_label()==report['transfer']['grade_volumes'][0]);assert any(b.object and '/FloraTrailStyle/' in path(b.object) for b in pp.settings.weighted_blendables.array)
  grade=next(b.object for b in pp.settings.weighted_blendables.array if b.object and '/FloraTrailStyle/' in path(b.object));grade_mid=u.MaterialLibrary.create_dynamic_material_instance(world,grade);assert abs(grade_mid.get_scalar_parameter_value('FloraTrailGrade')-1.)<1e-6
  report['grade_verified']=True;save();yield from capture()
  assert sha(MAPFILE)==report['saved_map_sha256'];verify(True)
 report['ok']=True;save()
 assert L.load_level('/Engine/Maps/Entry');world=None;yield 3
steps=run()
def close():
 globals()['world']=None;gc.collect();u.SystemLibrary.collect_garbage();globals()['quit_at']=time.monotonic()+3
 def quit(dt):
  if time.monotonic()>quit_at:u.unregister_slate_post_tick_callback(quit_handle);u.EditorPythonScripting.set_keep_python_script_alive(False);u.SystemLibrary.quit_editor()
 globals()['quit_handle']=u.register_slate_post_tick_callback(quit)
def tick(dt):
 state['frame']+=1
 if state['busy']:return
 state['busy']=True
 try:
  if time.monotonic()>=state['due']:state['due']=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);close()
 except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);close()
 finally:state['busy']=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
