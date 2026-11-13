"""Add grouped habitat detail without regenerating terrain or existing planting."""
import unreal as u,json,math,sys,os,time,traceback,hashlib,collections,shutil,gc
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
import lidar_first_section as S
from lidar_grounding import GroundSampler
from benmore_river_life_materials import props
OUT=ROOT/'Art/Export/LidarStudy/LevelDetail';QA=ROOT/'Saved/LidarAuthoringQA/LevelDetail';QA.mkdir(exist_ok=True)
DEST=C.BASE+'/LevelDetail';PREFIX='LidarStudy_LevelDetail_';actors=C.actors;assets=u.EditorAssetLibrary;sm=C.sm;les=u.get_editor_subsystem(u.LevelEditorSubsystem)
STAGE=os.environ.get('GT_DETAIL_STAGE','prepare');report=dict(ok=False,stage=STAGE);busy=False;deadline=0

def protected_state():
 refs=actors.get_all_level_actors();forest=next(a for a in refs if a.get_actor_label()=='LidarStudy_Forest')
 return dict(bank=S.snapshot(),understory=S.outside_snapshot(),forest={c.get_name():C.fingerprint(c) for c in forest.get_components_by_class(u.InstancedStaticMeshComponent)},ground=[str(a.output_digest) for a in refs if isinstance(a,u.GTProceduralGround)])

def mesh_for(row):
 source=u.load_asset(row['mesh']);assert source,row['mesh']
 if not (row['anchor'] and row['role'] in ['stone','log','stump']):return source,False
 path=DEST+'/'+source.get_name();mesh=u.load_asset(path)
 if not mesh:
  mesh=assets.duplicate_asset(row['mesh'],path);sm.remove_collisions(mesh);assert sm.add_simple_collisions(mesh,u.ScriptingCollisionShapeType.BOX)>=0
  assert assets.save_loaded_asset(mesh,False)
 return mesh,True

def prepare(plan,g):
 views=[]
 for row in plan['review']:
  x,y=row['position_xy_cm'];tx,ty=row['target_xy_cm'];pos=u.Vector(x,y,g.height(x,y)+row['eye_cm']);target=u.Vector(tx,ty,g.height(tx,ty)+row['target_height_cm'])
  label='LevelDetail_'+row['view'];cam=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None) or actors.spawn_actor_from_class(u.CameraActor,pos)
  cam.set_actor_label(label);cam.set_actor_location(pos,False,True);cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False);cam.camera_component.set_field_of_view(row['fov'])
  views.append(dict(view=row['view'],actor=cam.get_name(),position=[pos.x,pos.y,pos.z],target=[target.x,target.y,target.z],fov=row['fov'],description=row['biome'],patch=row['patch']))
 views += [v for v in json.loads((ROOT/'Saved/LidarAuthoringQA/ValleyGround/cameras.json').read_text()) if v['view'] in ['V02','G01']]
 (QA/'cameras.json').write_text(json.dumps(views,indent=2));return views

def install(plan,g):
 # Reruns replace only this pass's actors, never the approved population.
 for a in actors.get_all_level_actors():
  if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a)
 meshcache={};groups={};placed=[];rejected=collections.Counter();roles=collections.Counter();biomes=collections.Counter()
 probes={r['asset']:r['probes'] for r in json.loads((S.OUT/'plants.json').read_text())}
 limits={'log':20,'stump':28,'twig':25,'root':28,'shrub':40,'grass':42,'rush':28,'flax':28,'fern':34,'crevice':48,'moss':45,'stone':54}
 for i,row in enumerate(plan['items']):
  key=(row['mesh'],row['anchor']);mesh,solid=meshcache.setdefault(key,mesh_for(row)) if key not in meshcache else meshcache[key]
  x,y=row['xy_cm'];role=row['role'];scale=row['scale'];yaw=row['yaw']
  gx=(g.height(x+35,y)-g.height(x-35,y))/70;gy=(g.height(x,y+35)-g.height(x,y-35))/70;slope=math.degrees(math.atan(math.hypot(gx,gy)))
  if slope>limits[role]:rejected['final_slope']+=1;continue
  plant=role in ['shrub','grass','rush','flax','fern','crevice']
  if role in ['fern','crevice']:yaw=math.degrees(math.atan2(-gy,-gx))+(row['yaw']%31-15)
  tf=u.Transform(location=u.Vector(x,y,0),rotation=u.Rotator(yaw=yaw),scale=u.Vector(scale,scale,scale));tf=g.seat(mesh,tf,plant)
  if role in ['fern','crevice']:
   samples=probes[mesh.get_name()];bad=0
   for px,py,pz in samples:
    p=u.MathLibrary.transform_location(tf,u.Vector(px*100,-py*100,pz*100));bad+=p.z-g.height(p.x,p.y)<-12
   if bad>len(samples)*.12:rejected['frond_ground_intersection']+=1;continue
  if role in ['twig','root','moss','log','stump']:
   # Reject a sharply curved support that would bury most of this small object.
   h=(mesh.get_bounding_box().max.z-mesh.get_bounding_box().min.z)*scale
   nominal=g.height(x,y)-mesh.get_bounding_box().min.z*scale-4
   if nominal-tf.translation.z>max(9,h*.42):rejected['support_curvature']+=1;continue
  cell=(math.floor(x/102400),math.floor(y/102400));group=(*cell,mesh.get_path_name(),solid,role)
  groups.setdefault(group,[]).append(tf);roles[role]+=1;biomes[row['biome']]+=1
  placed.append(dict(mesh=mesh.get_path_name(),role=role,biome=row['biome'],patch=row['patch'],transform=S.tfkey(tf),solid=solid))
  if i%1500==0:
   (QA/'progress.json').write_text(json.dumps(dict(stage='grounding',examined=i,total=len(plan['items']),accepted=len(placed))));yield .01
 owners={};components=[]
 for j,((cx,cy,path,solid,role),transforms) in enumerate(groups.items()):
  if (cx,cy) not in owners:
   a=actors.spawn_actor_from_class(u.Actor,u.Vector(cx*102400,cy*102400,0));a.set_actor_label(PREFIX+str(cx)+'_'+str(cy));a.tags=['LevelDetail','LD1'];a.root_component.set_mobility(u.ComponentMobility.STATIC);owners[(cx,cy)]=a
  a=owners[(cx,cy)];mesh=u.load_asset(path);c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,transforms,'LevelDetail','BlockAll' if solid else 'NoCollision',solid)
  c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if solid else u.CollisionEnabled.NO_COLLISION)
  cull=(28000,42000) if role=='stone' and solid else (14000,22000) if role in ['log','stump'] else (8500,14000) if role=='shrub' else (4500,7000) if role in ['moss','twig','root'] else (5500,9500)
  c.set_cull_distances(*cull);c.set_lod_distance_scale(1.5)
  props(c,cast_shadow=True,cast_shadow_as_two_sided=role in ['shrub','grass','rush','flax','fern','crevice'],affect_distance_field_lighting=False,visible_in_ray_tracing=False)
  for slot,material in enumerate(mesh.get_editor_property('static_materials')):
   if material.material_interface and material.material_interface.get_path_name().split('.')[0].endswith('/M_NZ_Foliage'):c.set_material(slot,u.load_asset(C.BASE+'/MI_NZ_Foliage_Bush'))
  components.append(dict(actor=a.get_actor_label(),component=c.get_name(),mesh=path,role=role,count=len(transforms),solid=solid,cull_cm=cull,fingerprint=C.fingerprint(c)))
  if j%30==0:yield .01
 (OUT/'placed.json').write_text(json.dumps(placed,separators=(',',':')))
 report.update(instances=len(placed),roles=dict(roles),biomes=dict(biomes),rejected=dict(rejected),actors=len(owners),components=components,layout_sha256=hashlib.sha256((OUT/'layout.json').read_bytes()).hexdigest())

def verify():
 previous=json.loads((QA/'install.json').read_text());assert previous['ok']
 rows={}
 for a in actors.get_all_level_actors():
  if a.get_actor_label().startswith(PREFIX):
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):rows[(a.get_actor_label(),c.get_name())]=c
 assert sum(c.get_instance_count() for c in rows.values())==previous['instances']
 for r in previous['components']:
  c=rows[(r['actor'],r['component'])];assert c.get_instance_count()==r['count'];assert c.static_mesh.get_path_name()==r['mesh']
  assert C.fingerprint(c)==r['fingerprint']
 assert protected_state()==json.loads((QA/'protected.json').read_text())
 return dict(instances=previous['instances'],saved_reload=True,protected_packages=C.validate_protected())

def run():
 if STAGE=='prepare':
  backup=QA/'before-detail.umap'
  if not backup.exists():shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup)
 assert les.load_level(C.BASE+'/L_LidarStudy');yield 2
 if STAGE=='verify':
  report.update(verify());report['ok']=True;yield 1;return
 before=protected_state();author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));g=GroundSampler(author)
 plan=json.loads((OUT/'layout.json').read_text())
 if STAGE=='prepare':
  (QA/'protected.json').write_text(json.dumps(before,indent=2));report['views']=prepare(plan,g)
 elif STAGE=='install':
  assert before==json.loads((QA/'protected.json').read_text());yield from install(plan,g)
 assert protected_state()==before;report['protected_packages']=C.validate_protected()
 assert les.save_current_level();report.update(ok=True,saved=True)
 if STAGE=='install':(OUT/'recipe.json').write_text(json.dumps(dict(enabled=True,version=1,source='Art/Unreal/lidar_level_detail.py',layout='layout.json',instances=report['instances']),indent=2))
 yield 1
steps=run()
def tick(dt):
 global busy,deadline
 if busy or time.monotonic()<deadline:return
 busy=True
 try:deadline=time.monotonic()+float(next(steps))
 except StopIteration:
  (QA/(STAGE+'.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());(QA/(STAGE+'.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
