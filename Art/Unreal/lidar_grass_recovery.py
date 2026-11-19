"""Compare earlier fine LiDAR grass against the broad Flora replacements."""
from pathlib import Path
import os,json
R=Path('C:/GrandTour')
_h=(R/'Art/Unreal/lidar_flora_transfer.py').read_text()
exec(compile(_h.split('steps=run()')[0],'<lidar-review-helpers>','exec'))
O=R/'Art/Export/LidarGrassRecovery';O.mkdir(parents=True,exist_ok=True)
stage=os.environ.get('GT_LIDAR_GRASS_STAGE','audit')
report={'ok':False,'stage':stage,'images':[],'settings':json.loads((R/'Art/lidar_grass_recovery_settings.json').read_text())}
GRASS_FIELDS=['generate_around_player','grass_material','rank_material','card_grass_material','distant_grass_material','pasture_clump_mesh','pasture_clump_mesh_b','pasture_clump_mesh_c','rank_clump_mesh','distant_pasture_mesh','distant_pasture_material','clump_spacing_cm','clump_scale_min','clump_scale_max','clump_stream_radius_cm','grass_cull_start_cm','grass_cull_end_cm','clump_lod1_distance_cm','clump_lod2_distance_cm','distant_pasture_spacing_cm','distant_pasture_end_cm','independent_grass_lod_scale','blade_scale','rank_band_scale']

def grass_fields(a):
 return {k:path(a.get_editor_property(k)) if isinstance(a.get_editor_property(k),u.Object) else value(a.get_editor_property(k)) for k in GRASS_FIELDS}

def inspect_grass():
 report['grass']=[{'actor':a.get_actor_label(),**grass_fields(a)} for a in actors() if isinstance(a,u.GTMixedGroundDetails)]
 report['ground']=[{'actor':a.get_actor_label(),'material':path(a.relief_material),'digest':str(a.output_digest)} for a in actors() if isinstance(a,u.GTProceduralGround)]
 mats=set();refs=[]
 for a in actors():
  for c in a.get_components_by_class(u.PrimitiveComponent):
   try:ms=list(c.get_materials())
   except Exception:continue
   for i,m in enumerate(ms):
    if m and any(t in path(m) for t in ('Terrain','Detail','Ground','Grass')):
     refs.append({'actor':a.get_actor_label(),'component':c.get_name(),'slot':i,'material':path(m)});mats.add(m)
 for a in actors():
  if isinstance(a,u.GTProceduralGround):mats.add(a.relief_material)
  if isinstance(a,u.GTMixedGroundDetails):
   mats.update(a.get_editor_property(k) for k in GRASS_FIELDS if k.endswith('material') and a.get_editor_property(k))
 for name in ('Near','Far','Verge'):mats.add(u.load_asset(BASE+'/GrassGS3/M_GS3_'+name))
 report['material_refs']=refs;report['materials']={};pending=list(mats)
 while pending:
  m=pending.pop()
  if not m or path(m) in report['materials']:continue
  report['materials'][path(m)]=material(m)
  if isinstance(m,u.MaterialInstanceConstant):pending.append(m.get_editor_property('parent'))
 report['fine_meshes']={}
 for name in ('Near_A','Near_B','Near_C','Far','Verge'):
  m=u.load_asset(BASE+'/GrassGS3/SM_GS3_'+name);assert m
  report['fine_meshes'][path(m)]={'triangles':[m.get_num_triangles(i) for i in range(u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_lod_count(m))],'dimensions':value(m.get_bounds().box_extent*2)}

def review_views():
 from lidar_grounding import GroundSampler
 g=GroundSampler(next(a for a in actors() if isinstance(a,u.GTProceduralGround)))
 fixture=json.loads((R/'Art/Unreal/lidar_grass_check_views.json').read_text())
 p=fixture['lp3_captures']['Paddock_middle'];c=fixture['gp2c_chase']
 views=[]
 for name,xy,aim,height in [('paddock_low',p['camera_cm'],p['target_cm'],145),('paddock_wide',c['camera_cm'],p['target_cm'],550)]:
  views.append({'name':name,'position':[xy[0],xy[1],g.height(xy[0],xy[1])+height],'target':[aim[0],aim[1],g.height(aim[0],aim[1])+100]})
 bank=next(v for v in json.loads((R/'Art/Export/LidarFloraTransfer/views.json').read_text()) if v['name']=='bank');views.append(bank)
 return views

def capture_grass(label):
 global world,pc,car,camera
 views=json.loads((O/'views.json').read_text());L.editor_set_viewport_realtime(False)
 assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);end=time.monotonic()+240
 while not car:
  world=u.EditorLevelLibrary.get_game_world()
  if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
  assert time.monotonic()<end;yield 1
 car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True);car.set_actor_hidden_in_game(True)
 for c in json.loads((R/'Art/lidar_performance.json').read_text())['commands']:cmd(c)
 for c in ('DisableAllScreenMessages','ShowHUD','r.MotionBlurQuality 0','r.Streaming.FullyLoadUsedTextures 1'):cmd(c)
 camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'GrassRecoveryCamera');camera.camera_component.set_field_of_view(68);camera.camera_component.set_editor_property('constrain_aspect_ratio',False);pc.set_view_target_with_blend(camera,0)
 pc.set_tickable_when_paused(True);pc.set_editor_property('should_perform_full_tick_when_paused',True);camera.set_tickable_when_paused(True)
 grass=next(a for a in actors() if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
 report.setdefault('runtime',{})[label]={'properties':grass_fields(grass),'quality':{k:u.SystemLibrary.get_console_variable_float_value(k) for k in ['r.ScreenPercentage','r.StaticMeshLODDistanceScale','r.AntiAliasingMethod']}}
 yield 20
 for v in views:
  u.GameplayStatics.set_game_paused(world,False);look(v);car.set_actor_location(u.Vector(*v['position'])-u.Vector(0,0,90),False,True)
  mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield 12
  end=time.monotonic()+120
  while grass.streaming_consistency(False)=='busy':assert time.monotonic()<end,'Grass streaming timed out';yield .5
  consistent=grass.streaming_consistency(True);assert consistent.startswith('ok '),consistent
  report['runtime'][label][v['name']]={'consistency':consistent,'near_count':grass.near_grass_count(),'report':grass.grass_report()};save()
  u.GameplayStatics.set_game_paused(world,True);yield from shot(label+'_'+v['name'])
  if v['name']=='paddock_low' and label in ('fine_muted','candidate','verify'):
   assert grass.near_grass_count()>1000
   before=grass.grass_report()
   for comp in (grass.grass,grass.grass_b,grass.grass_c):
    if comp.get_instance_count():
     for i in range(min(4,comp.get_instance_count())):
      pos=comp.get_instance_transform(i,True).translation;grass.apply_review_grass_contact(u.Vector2D(pos.x,pos.y),i%2==1)
   u.GameplayStatics.set_game_paused(world,False);yield 2
   after=grass.grass_report()
   import re
   counters=lambda s:{k:int(v) for k,v in re.findall(r'((?:bent|removed)_[abc])=(\d+)',s)}
   bc,ac=counters(before),counters(after);assert len(ac)==6
   assert sum(ac[k]-bc[k] for k in ac if k.startswith('bent'))>0 and sum(ac[k]-bc[k] for k in ac if k.startswith('removed'))>0,'Contact probe did not bend and remove grass'
   report['runtime'][label]['contact']={'before':bc,'after':ac,'method':'native API probe; not a physical driving test'};save()
 u.GameplayStatics.set_game_paused(world,False);pc.set_view_target_with_blend(car,0);u.EditorLevelLibrary.editor_end_play();yield 5
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();pc=car=camera=None

def normalized_invariants():
 import lidar_grass_recovery_materials as recovery
 mapping={path(u.load_asset(recovery.D+'/M_Fine_'+k)):path(u.load_asset(recovery.SOURCES[k])) for k in ('Terrain','Detail')}
 def normalize(v):
  if isinstance(v,dict):return {k:normalize(x) for k,x in v.items()}
  if isinstance(v,list):return [normalize(x) for x in v]
  return mapping.get(v,v) if isinstance(v,str) else v
 return normalize(protected())

def run():
 global world
 report['original_map_sha256']=sha(MAPFILE);verify(True)
 if stage=='prepare':
  import lidar_grass_recovery_materials as recovery
  report['materials']=recovery.prepare();report['ok']=True;save();yield 3;return
 assert L.load_level(MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();yield 3
 if stage=='audit':inspect_grass();save()
 elif stage=='compare':
  import lidar_grass_recovery_materials as recovery
  before=normalized_invariants();report['grass_before']=[grass_fields(a) for a in actors() if isinstance(a,u.GTMixedGroundDetails)]
  (O/'invariants.json').write_text(json.dumps(before));(O/'views.json').write_text(json.dumps(review_views(),indent=2))
  yield from capture_grass('current')
  report['restored_bindings']=recovery.apply(world,False);assert normalized_invariants()==before;save()
  yield from capture_grass('fine_original')
  report['muted_bindings']=recovery.apply(world,True);assert normalized_invariants()==before;save()
  yield from capture_grass('fine_muted')
  assert normalized_invariants()==before
  report['grass_after']=[grass_fields(a) for a in actors() if isinstance(a,u.GTMixedGroundDetails)]
  for a,b in zip(report['grass_before'],report['grass_after']):
   for key in GRASS_FIELDS:
    if not key.endswith(('mesh','mesh_b','mesh_c','material')):assert a[key]==b[key],key
  report['protected_geometry_and_systems']=True
 elif stage=='candidate':
  import lidar_grass_recovery_materials as recovery
  before=normalized_invariants();assert before==json.loads((O/'invariants.json').read_text())
  report['grass_before']=[grass_fields(a) for a in actors() if isinstance(a,u.GTMixedGroundDetails)]
  report['bindings']=recovery.apply(world,True);assert normalized_invariants()==before
  report['grass_after']=[grass_fields(a) for a in actors() if isinstance(a,u.GTMixedGroundDetails)];save()
  yield from capture_grass('candidate');assert normalized_invariants()==before
  report['protected_geometry_and_systems']=True
 elif stage=='install':
  import lidar_grass_recovery_materials as recovery
  from lidar_grass_recovery_baseline import verify as verify_recovery
  report['recovery_packages']=verify_recovery(False)
  comparison=json.loads((O/'candidate-report.json').read_text());assert comparison['ok'] and comparison['settings']==report['settings']
  before=normalized_invariants();assert before==json.loads((O/'invariants.json').read_text())
  assert [grass_fields(a) for a in actors() if isinstance(a,u.GTMixedGroundDetails)]==comparison['grass_before']
  report['bindings']=recovery.apply(world,True);assert normalized_invariants()==before
  expected=[grass_fields(a) for a in actors() if isinstance(a,u.GTMixedGroundDetails)];assert expected==comparison['grass_after']
  assert L.save_current_level();report['saved_map_sha256']=sha(MAPFILE);save()
  assert L.load_level('/Engine/Maps/Entry');world=None;yield 3
  assert L.load_level(MAP);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();yield 3
  assert normalized_invariants()==before
  assert [grass_fields(a) for a in actors() if isinstance(a,u.GTMixedGroundDetails)]==expected
  report['saved_bindings_verified']=True;report['protected_geometry_and_systems']=True;save()
  yield from capture_grass('verify');report['recovery_packages']=verify_recovery(True)
 else:raise ValueError(stage)
 assert sha(MAPFILE)==report.get('saved_map_sha256',report['original_map_sha256']);report['ok']=True;save()
 assert L.load_level('/Engine/Maps/Entry');world=None;yield 3

exec(compile('steps=run()'+_h.split('steps=run()',1)[1],'<lidar-review-loop>','exec'))
