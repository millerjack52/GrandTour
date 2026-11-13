"""Reversible bounded Flora Paint / Rock Master migration in the actual LiDAR map."""
import unreal as u,json,math,random,sys,traceback,hashlib
from pathlib import Path
R=Path('C:/GrandTour');O=R/'Art/Export/LidarStudy/FloraIntegration';sys.path.insert(0,str(R/'Art/Unreal'))
import lidar_logging_trial as T
from lidar_grounding import GroundSampler
from benmore_river_life_materials import props
import lidar_flora_materials as F
BASE='/Game/GrandTour/ArtTests/LidarStudy';D=BASE+'/FloraIntegration';PREFIX='LidarStudy_FloraIntegration_'
A=u.get_editor_subsystem(u.EditorActorSubsystem);E=u.EditorAssetLibrary
report=dict(ok=False,counts={},removals={},rocks=[],materials=[])
defaults=dict(start_m=170,end_m=260,half_width_m=20,seed=184911,tree_min_lod=1,tree_limit=160,plant_groups=480,retain_native_grass=True,retain_ground_ferns=True,
 trees=['Tree_B_001','Tree_D_003','Tree_B_002'],tree_min_height_cm=1350,tree_max_height_cm=2300,
 grass=['Grass_003','Grass_005','Grass_013','Grass_016','Grass_020','Blooming_Grass_008','Blooming_Grass_012','Dry_Grass_014'],
 small=['Small_Plants_006','Small_Plants_013','Small_Plants_015'],ferns=['Ferns_021','Ferns_025','Ferns_033'],shrubs=['Blooming_Shrubbery_006','Blooming_Shrubbery_009'],
 plant_cull_start_cm=6000,plant_cull_end_cm=9500,
 ground=dict(GroundTileCm=280.,GroundNormalStrength=1.1,GrainStrength=.55,ReliefDepthCm=2.8,POMEnabled=1.,POMNearCm=700.,POMFarCm=1800.,DetailWidthCm=2400.),
 outcrops=[dict(station=195.,across=9.,width_cm=680,variant=0),dict(station=224.,across=-10.,width_cm=750,variant=1),dict(station=242.,across=10.,width_cm=640,variant=2)])

def tfkey(t):
 p=t.translation;q=t.rotation;s=t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def protected():
 rows=A.get_all_level_actors();author=next(a for a in rows if isinstance(a,u.GTProceduralGround));s=next(a for a in rows if isinstance(a,u.GTLandscapeSurface))
 return dict(ground=str(author.output_digest),soil={k:s.get_editor_property(k) for k in ['layer_depth_scale','maximum_layer_depth_cm','bearing_strength','settlement_speed_scale','grass_is_visual_cover','use_native_mud_shader_updates']},
 water=sorted([(a.get_actor_label(),a.get_actor_location().to_tuple()) for a in rows if isinstance(a,u.GTWaterSheet)]),
 lights=sorted([(a.get_actor_label(),a.light_component.intensity,[a.light_component.light_color.r,a.light_component.light_color.g,a.light_component.light_color.b],a.get_actor_rotation().to_tuple()) for a in rows if isinstance(a,u.DirectionalLight)]))

try:
 cfgpath=O/'profile.json'
 if not cfgpath.exists():cfgpath.write_text(json.dumps(defaults,indent=2))
 cfg=json.loads(cfgpath.read_text());rng=random.Random(cfg['seed'])
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(BASE+'/L_LidarStudy')
 rows=A.get_all_level_actors();author=next(a for a in rows if isinstance(a,u.GTProceduralGround));g=GroundSampler(author)
 route=T.route(json.loads((R/'Art/Export/LidarStudy/Place/roads.json').read_text()));pts=[T.at(route,s) for s in range(cfg['start_m'],cfg['end_m']+1,5)]
 def road_distance(x,y):
  best=1e20
  for a,b in zip(pts,pts[1:]):
   dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
   best=min(best,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
  return best
 def inside(x,y):return road_distance(x,y)<cfg['half_width_m']*100
 invariant=protected();report['protected_before']=invariant
 original_hashes={str(p.relative_to(R)):sha(p) for folder in ['Content/GrandTour/ArtTests/FloraPath','Content/GrandTour/ArtTests/FloraDrive','Content/GrandTour/ArtTests/LidarStudy/CohesiveStyle','Content/GrandTour/ArtTests/LidarStudy/Place'] for p in (R/folder).rglob('*.uasset')}
 prior=O/'source-removals.json';marker=next((a for a in rows if a.get_actor_label()==PREFIX+'SourceState'),None)
 removed=json.loads(prior.read_text()) if marker else []
 if marker:
  # Restore exactly the source instances we own before reselecting the edited
  # corridor. This lets bounds change without orphaning cleared forest patches.
  grouped={}
  for r in removed:grouped.setdefault((r['actor'],r['component']),[]).append(r)
  for (label,name),records in grouped.items():
   a=next(a for a in rows if a.get_actor_label()==label)
   c=next(c for c in a.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==name)
   assert c.static_mesh.get_path_name()==records[0]['mesh'],'Original forest component was replaced externally'
   transforms=[]
   for r in records:
    v=r['transform'];transforms.append(u.Transform(location=u.Vector(*v[:3]),rotation=u.Quat(*v[3:7]).rotator(),scale=u.Vector(*v[7:])))
   c.modify();c.add_instances(transforms,False,True)
  removed=[];marker=None
 # Replace only source-generated forest cohorts. Hand-built banks, obstacles,
 # nearby RS7 artwork and all water/physics actors remain untouched.
 if not marker:
  living_positions=set()
  forest=next(a for a in rows if a.get_actor_label()=='LidarStudy_Forest')
  cx,cy=pts[len(pts)//2][:2]
  for c in forest.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.static_mesh and c.static_mesh.get_name().startswith('SM_CD_Canopy'):
    for i in c.get_instances_overlapping_sphere(u.Vector(cx,cy,g.height(cx,cy)+1500),10000,True):
     p=c.get_instance_transform(i,True).translation;living_positions.add((round(p.x,1),round(p.y,1)))
  for a in rows:
   if a.get_actor_label() not in ['LidarStudy_Forest','LidarStudy_Understory','LidarStudy_DistanceStyle']:continue
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    mesh=c.static_mesh
    if not mesh:continue
    n=mesh.get_name();forest=a.get_actor_label()=='LidarStudy_Forest'
    if forest and not (n.startswith('SM_CD_Canopy') or n=='Cylinder'):continue
    if not forest and not any(k in n for k in ['Fern','Kiokio','Coprosma','VergeTussock','Harakeke','ForestInterior']):continue
    ids=[]
    # The 100m search bounds are deliberately conservative; precise corridor test follows.
    cx,cy=pts[len(pts)//2][:2];near=c.get_instances_overlapping_sphere(u.Vector(cx,cy,g.height(cx,cy)+1500),10000,True)
    for i in near:
     t=c.get_instance_transform(i,True);p=t.translation
     if n=='Cylinder' and (round(p.x,1),round(p.y,1)) not in living_positions:continue
     if cfg.get('retain_ground_ferns',False) and any(k in n for k in ['CrownFern','Kiokio']):
      blocked=False
      for rock in cfg['outcrops']:
       rx,ry,_=T.at(route,rock['station'],rock['across'])
       if math.hypot(p.x-rx,p.y-ry)<rock['width_cm']*.5+100:blocked=True;break
      if not blocked:continue
     if inside(p.x,p.y):
      ids.append(i);removed.append(dict(actor=a.get_actor_label(),component=c.get_name(),mesh=mesh.get_path_name(),transform=tfkey(t),height=mesh.get_bounds().box_extent.z*2*t.scale3d.z))
    if ids:c.modify();assert c.remove_instances(sorted(ids,reverse=True))
  prior.write_text(json.dumps(removed,indent=2))
 for a in list(rows):
  if a.get_actor_label().startswith(PREFIX):A.destroy_actor(a)
 def spawn(cls,label,pos=(0,0,0),rotation=None):
  a=A.spawn_actor_from_class(cls,u.Vector(*pos),rotation or u.Rotator());a.set_actor_label(PREFIX+label);a.set_folder_path('LiDAR/FloraIntegration');return a
 spawn(u.Actor,'SourceState');owner=spawn(u.Actor,'Vegetation');cache={};models={};buckets={};treepoints=[]
 def model(name):
  if name not in models:models[name]=u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_'+name);assert models[name],name
  return models[name]
 # Rock groups are grounded into the actual bank and kept clear of the driving corridor.
 rockrows=json.loads((R/'Art/Export/FloraDrive/RockMaster/export-report.json').read_text())['meshes'];cores=[]
 for group in cfg['outcrops']:
  for j in range(4):
   hero=j==0;row=rockrows[group['variant'] if hero else 3+j%2];mesh=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/RockMaster/'+row['mesh']);assert mesh
   s=group['station']+(0 if hero else rng.uniform(-3.5,3.5));off=group['across']+(0 if hero else rng.uniform(-2.2,2.2));x,y,yaw=T.at(route,s,off)
   width=group['width_cm'] if hero else rng.uniform(120,300)
   if road_distance(x,y)-width*.5<430:continue
   b=mesh.get_bounds();scale=width/(2*max(b.box_extent.x,b.box_extent.y));yaw+=rng.uniform(-30,30)
   t=u.Transform(location=u.Vector(x,y,0),rotation=u.Rotator(yaw=yaw),scale=u.Vector(scale,scale,scale));t=g.seat(mesh,t,False)
   p=t.translation;t.translation=u.Vector(p.x,p.y,p.z-2*b.box_extent.z*scale*(.20 if hero else .30))
   a=spawn(u.StaticMeshActor,'Rock_'+str(len(report['rocks'])));a.set_actor_transform(t,False,True);c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll');c.set_cast_shadow(True)
   for i,slot in enumerate(mesh.static_materials):
    if slot.material_interface:c.set_material(i,F.clone_material(slot.material_interface,cache))
   props(c,visible_in_ray_tracing=False,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
   cores.append((x,y,width*.33));report['rocks'].append(dict(mesh=mesh.get_name(),transform=tfkey(t),width_cm=width))
 def clear_rock(x,y):return not any(math.hypot(x-a,y-b)<r for a,b,r in cores)
 def place(name,x,y,height,tree=False,width=None,yaw=None):
  if not clear_rock(x,y):return
  mesh=model(name);b=mesh.get_bounds();scale=width/(2*max(b.box_extent.x,b.box_extent.y)) if width else height/(2*b.box_extent.z)
  # Source assets with buried root cards retain their source origin; avoid scaling thin leaves by height.
  z=g.height(x,y)-max(0,b.origin.z-b.box_extent.z)*scale-3
  t=u.Transform(location=u.Vector(x,y,z),rotation=u.Rotator(yaw=rng.uniform(0,360) if yaw is None else yaw),scale=u.Vector(scale,scale,scale))
  buckets.setdefault(name,[]).append(t)
  if tree:treepoints.append((x,y,z,height))
 originals=[r for r in removed if r['actor']=='LidarStudy_Forest' and 'SM_CD_Canopy' in r['mesh']]
 originals.sort(key=lambda r:tuple(r['transform'][:3]))
 assert 0<len(originals)<=cfg['tree_limit'],('Tree budget requires explicit review',len(originals),cfg['tree_limit'])
 for row in originals:
  x,y,z=row['transform'][:3]
  # Preserve stand locations and large-scale canopy height rather than flattening it to demo scale.
  h=max(cfg['tree_min_height_cm'],min(cfg['tree_max_height_cm'],row['height']))
  place(rng.choice(cfg['trees']),x,y,h,True)
 for k in range(cfg['plant_groups']):
  s=rng.uniform(cfg['start_m'],cfg['end_m']);off=rng.choice([-1,1])*rng.uniform(3.1,cfg['half_width_m']-.8)
  cx,cy,_=T.at(route,s,off)
  for j in range(rng.randint(10,18)):
   x,y=cx+rng.gauss(0,125),cy+rng.gauss(0,125)
   if not inside(x,y) or road_distance(x,y)<230:continue
   slope=math.hypot(g.height(x+50,y)-g.height(x-50,y),g.height(x,y+50)-g.height(x,y-50))/100
   if slope>.85:continue
   if j==0 and k%5==0:place(rng.choice(cfg['ferns']),x,y,rng.uniform(38,65))
   elif j%6==0:place(rng.choice(cfg['small']),x,y,0,width=rng.uniform(35,90))
   else:place(rng.choice(cfg['grass']),x,y,rng.uniform(28,72))
  if k%8==0:place(rng.choice(cfg['shrubs']),cx,cy,rng.uniform(65,130))
 for name,ts in buckets.items():
  mesh=model(name);tree='Tree' in name;shadow=tree or any(s in name for s in ['Small_Plants','Ferns','Shrubbery'])
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'LidarFlora','NoCollision',shadow)
  # Trees retain distant visibility. Detail LOD1/2 limits the expensive source geometry.
  if tree:props(c,override_min_lod=True,min_lod=cfg['tree_min_lod']);c.set_cull_distances(0,0)
  else:c.set_cull_distances(cfg['plant_cull_start_cm'],cfg['plant_cull_end_cm'])
  props(c,visible_in_ray_tracing=False,cast_contact_shadow=True,cast_shadow_as_two_sided=shadow,affect_distance_field_lighting=tree,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  for i,slot in enumerate(mesh.static_materials):
   if slot.material_interface:c.set_material(i,F.clone_material(slot.material_interface,cache))
  report['counts'][name]=len(ts)
 cylinder=u.load_asset('/Engine/BasicShapes/Cylinder');colliders=[]
 for x,y,z,h in treepoints:colliders.append(u.Transform(location=u.Vector(x,y,z+h*.30),scale=u.Vector(.38,.38,h*.60/100)))
 c=u.GTVegetationSubsystem.add_tagged_instances(owner,cylinder,colliders,'LidarFloraTrunks','BlockAll',False);c.set_visibility(False);c.set_hidden_in_game(True)
 # Map-local wrappers, assigned wherever the actual approved terrain/detail parents were used.
 mapping={}
 for role in ['Terrain','Detail']:
  source=u.load_asset(BASE+'/CohesiveStyle/M_Evergreen'+role);assert source
  local=F.ground(source,role,route,cfg);mapping[source]=local;report['materials'].append(local.get_path_name())
 for a in A.get_all_level_actors():
  if isinstance(a,u.GTMixedGroundDetails):
   grasscache={}
   for field in ['grass_material','rank_material','card_grass_material','distant_grass_material','distant_pasture_material']:
    source=a.get_editor_property(field)
    if source:a.set_editor_property(field,F.grass_exclusion(source,route,cfg,grasscache))
   report['legacy_grass_excluded_within_section']=not cfg.get('retain_native_grass',False)
  if isinstance(a,u.LandscapeProxy) and a.landscape_material in mapping:a.landscape_material=mapping[a.landscape_material]
  if isinstance(a,u.GTProceduralGround) and a.relief_material in mapping:a.relief_material=mapping[a.relief_material]
  if isinstance(a,u.GTMudRunnerVisual):
   assert a.follow_player_grid,'LiDAR requires runtime MR_VisualWindow binding'
   if a.material in mapping:a.material=mapping[a.material]
  for c in a.get_components_by_class(u.MeshComponent):
   for i in range(c.get_num_materials()):
    if c.get_material(i) in mapping:c.set_material(i,mapping[c.get_material(i)])
 report['protected_after']=protected();assert protected()==invariant,'Native terrain/soil/water/light changed'
 assert all(sha(R/p)==v for p,v in original_hashes.items()),'Shared source package changed'
 for row in removed:report['removals'][row['actor']]=report['removals'].get(row['actor'],0)+1
 assert len(treepoints)>0 and sum(report['counts'].values())<10000
 report.update(tree_instances=len(treepoints),plant_instances=sum(report['counts'].values())-len(treepoints),local_materials=len(cache),source_package_hashes_unchanged=True,profile=cfg)
 x,y,_=T.at(route,211,-.7);tx,ty,_=T.at(route,221);p=u.Vector(x,y,g.height(x,y)+170);target=u.Vector(tx,ty,g.height(tx,ty)+100)
 u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(p,u.MathLibrary.find_look_at_rotation(p,target))
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level()
 report['ok']=True;report['saved_map_sha256']=sha(R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap')
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(O/'install-report.json').write_text(json.dumps(report,indent=2))
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');u.SystemLibrary.quit_editor()
