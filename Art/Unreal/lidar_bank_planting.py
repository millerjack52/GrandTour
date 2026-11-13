"""RS5: rooted, slope-aware plants in the river reach; no flat rosettes on cliff faces."""
from pathlib import Path
import unreal as u
import sys,json,math,random,time,traceback,gc,shutil,hashlib
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_river_plant_variety as plants
from lidar_grounding import GroundSampler
from benmore_river_life_materials import props
BASE=plants.BASE;KIT=plants.KIT;OUT=plants.OUT;QA=ROOT/'Saved/LidarAuthoringQA/RS5'
VERSION='rs5-1';TAG='RS5BankFit1';PREFIX='LidarStudy_RS5_'
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
KINDS=('CrownFern','Kiokio','VergeTussock','Rush','Harakeke','Coprosma','TreeFern','MossHummock','RootTangle')
def gradient(g,x,y,r):return ((g.height(x+r,y)-g.height(x-r,y))/(2*r),(g.height(x,y+r)-g.height(x,y-r))/(2*r))
def frame(g,x,y):
 gx,gy=gradient(g,x,y,30);bx,by=gradient(g,x,y,140)
 return gx,gy,math.degrees(math.atan(math.hypot(gx,gy))),math.degrees(math.atan(math.hypot(bx,by)))
def selected(a):return a.get_actor_label()=='LidarStudy_Understory' or a.get_actor_label().startswith(('LidarStudy_RiverDetail_',plants.PREFIX,PREFIX))
def snapshot():
 rows=[];rs3=[]
 for a in actors.get_all_level_actors():
  if not selected(a):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh:continue
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);p=t.translation
    if a.get_actor_label().startswith(plants.PREFIX):rs3.append(plants.tfkey(t))
    if plants.inside(p.x,p.y):rows.append((a.get_actor_label(),c.static_mesh.get_name(),plants.tfkey(t)))
 return dict(signature=hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest(),instances=len(rows),rs3_signature=plants.digest(rs3),rs3_instances=len(rs3))
def fit(g,mesh,t,gx,gy,tilt_fraction,shrink=1.,fern=False):
 p=t.translation;length=max(.001,math.hypot(gx,gy));down=u.Vector(-gx/length,-gy/length,0)
 normal=u.Vector(-gx,-gy,1);normal=normal/normal.length()
 axis=u.Vector(normal.x*tilt_fraction,normal.y*tilt_fraction,1-tilt_fraction+normal.z*tilt_fraction)
 rot=u.MathLibrary.make_rot_from_xz(down,axis)
 sc=t.scale3d
 scale=u.Vector(sc.x*shrink*(1.12 if fern else 1),sc.y*shrink*(.75 if fern else 1),sc.z*shrink*(.82 if fern else 1))
 # Seat the actual small root crown, not the frond bounding box. All basal ring
 # points must be in the bank; frond tips are intentionally free to overhang.
 root_radius=max(6,min(22,mesh.get_bounds().box_extent.z*scale.z*.13))
 basis=u.Transform(location=u.Vector(p.x,p.y,0),rotation=rot,scale=u.Vector(1,1,1))
 candidates=[]
 for j in range(8):
  a=j*math.tau/8;q=u.MathLibrary.transform_location(basis,u.Vector(math.cos(a)*root_radius,math.sin(a)*root_radius,0))
  candidates.append(g.height(q.x,q.y)-q.z)
 z=min(g.height(p.x,p.y),min(candidates))-5
 return u.Transform(location=u.Vector(p.x,p.y,z),rotation=rot,scale=scale)
def apply():
 refs=list(actors.get_all_level_actors());author=next(a for a in refs if isinstance(a,u.GTProceduralGround));g=GroundSampler(author);terrain=str(author.output_digest)
 counts={'removed':{},'fitted':{},'fern_replacements':0,'flat_preserved':0};protected=[];after=[]
 for a in refs:
  if not selected(a) or a.get_actor_label().startswith(PREFIX) or TAG in [str(t) for t in a.tags]:continue
  label=a.get_actor_label();source='RS5Source_'+hashlib.sha256(label.encode()).hexdigest()[:12]
  for old in list(actors.get_all_level_actors()):
   if old.get_actor_label().startswith(PREFIX) and source in [str(t) for t in old.tags]:actors.destroy_actor(old)
  replacements={}
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   mesh=c.static_mesh
   if not mesh:continue
   name=mesh.get_name().removeprefix('SM_NZ_')
   if not name.startswith(KINDS):continue
   removals=[];updates=[];keep=[]
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);p=t.translation
    if not plants.inside(p.x,p.y):keep.append(plants.tfkey(t));continue
    gx,gy,angle,broad=frame(g,p.x,p.y)
    if angle<18:keep.append(plants.tfkey(t));counts['flat_preserved']+=1;continue
    seed=int(hashlib.sha256(('%s:%.2f:%.2f'%(name,p.x,p.y)).encode()).hexdigest()[:12],16);rng=random.Random(seed)
    bench=angle<28 and broad>angle+9
    remove=False;new=None
    if name.startswith('TreeFern'):
     # A vertical trunk needs a genuine support patch; don't rotate whole trees
     # sideways to conceal unsuitable placement on a bare cut face.
     remove=angle>36 or (broad>48 and not bench)
     if not remove:new=fit(g,mesh,t,gx,gy,.03)
    elif name.startswith(('Coprosma','Harakeke')):
     remove=angle>34 or (broad>45 and not bench)
     if not remove:new=fit(g,mesh,t,gx,gy,.08,.9)
    elif name.startswith(('MossHummock','RootTangle')):
     remove=angle>72
     if not remove:
      s=t.scale3d;flat=u.Transform(location=p,rotation=t.rotation.rotator(),scale=u.Vector(s.x*.75,s.y*.75,s.z*.32))
      new=g.seat(mesh,flat,False)
      if abs(new.translation.z-g.height(p.x,p.y))>65:remove=True;new=None
    elif name.startswith(('Rush','VergeTussock')):
     remove=angle>42 or (angle>32 and rng.random()<.40)
     if not remove:new=fit(g,mesh,t,gx,gy,.27,.82)
    else:
     remove=angle>58 or (angle>42 and rng.random()<.46)
     if not remove:
      # Kiokio already has arched outer fronds and hanging tips. Narrow the
      # cross-bank footprint, turn its long axis downhill, and tuck its crown in.
      target='SM_NZ_Kiokio_'+('A' if rng.random()<.65 else 'B');fern=u.load_asset(KIT+'/'+target);assert fern
      height=rng.uniform(45,80) if angle>35 else rng.uniform(60,95)
      sc=height/max(1,fern.get_bounds().box_extent.z*2)
      ft=u.Transform(location=p,rotation=u.Rotator(),scale=u.Vector(sc,sc,sc))
      placed=fit(g,fern,ft,gx,gy,.50 if angle>30 else .35,fern=True)
      replacements.setdefault(target,[]).append(placed);counts['fern_replacements']+=1;remove=True
    if remove:
     removals.append(i);counts['removed'][name]=counts['removed'].get(name,0)+1
    elif new:
     updates.append((i,new));counts['fitted'][name]=counts['fitted'].get(name,0)+1
   protected.append((label,c.get_name(),plants.digest(keep)))
   for j,(i,t) in enumerate(updates):assert c.update_instance_transform(i,t,True,j==len(updates)-1,True)
   if removals:assert c.remove_instances(sorted(removals,reverse=True))
   remaining=[]
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);p=t.translation
    if not plants.inside(p.x,p.y) or frame(g,p.x,p.y)[2]<18:remaining.append(plants.tfkey(t))
   after.append((label,c.get_name(),plants.digest(remaining)))
  for name,ts in replacements.items():
   obj=actors.spawn_actor_from_class(u.Actor,u.Vector());obj.set_actor_label(PREFIX+source+'_'+name);obj.tags=[TAG,source,'LidarBankPlants']
   mesh=u.load_asset(KIT+'/'+name);c=u.GTVegetationSubsystem.add_tagged_instances(obj,mesh,ts,'LidarBankPlants','NoCollision',False)
   c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cull_distances(10000,16000)
   props(c,cast_shadow=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),cast_shadow_as_two_sided=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),visible_in_ray_tracing=False,affect_distance_field_lighting=False)
   for i,slot in enumerate(mesh.get_editor_property('static_materials')):
    m=slot.get_editor_property('material_interface')
    if m and m.get_name()=='M_NZ_Foliage':c.set_material(i,u.load_asset(BASE+'/MI_NZ_Foliage_Bush'))
  a.tags=list(a.tags)+[TAG]
 assert protected==after,'Flat or outside plants changed'
 assert str(author.output_digest)==terrain
 counts.update(ground_digest=terrain,flat_and_outside_preserved=True,version=VERSION)
 return counts
def inventories():
 # Report the actual remaining old river-detail batches, keeping later checks valid.
 f=OUT/'riverdetail.json'
 if f.exists():
  d=json.loads(f.read_text());counts={};n=0
  for a in actors.get_all_level_actors():
   if not a.get_actor_label().startswith('LidarStudy_RiverDetail_'):continue
   n+=1
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if c.static_mesh:counts[c.static_mesh.get_name()]=counts.get(c.static_mesh.get_name(),0)+c.get_instance_count()
  d.update(instances=sum(counts.values()),components=n,by_mesh=counts,rs5_bank_fit=True);f.write_text(json.dumps(d,indent=2))
def validate_roots():
 refs=actors.get_all_level_actors();author=next(a for a in refs if isinstance(a,u.GTProceduralGround));g=GroundSampler(author)
 rows=0;maximum=-1e9;ferns=0;trees=0
 for a in refs:
  if not selected(a) or TAG not in [str(t) for t in a.tags]:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   mesh=c.static_mesh
   if not mesh:continue
   name=mesh.get_name().removeprefix('SM_NZ_')
   if not name.startswith(KINDS) or name.startswith(('MossHummock','RootTangle')):continue
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);p=t.translation
    if not plants.inside(p.x,p.y):continue
    gx,gy,angle,broad=frame(g,p.x,p.y)
    if angle<18:continue
    if name.startswith('TreeFern'):assert angle<=36.01;trees+=1
    if a.get_actor_label().startswith(PREFIX):assert angle<=58.01;ferns+=1
    radius=max(6,min(22,mesh.get_bounds().box_extent.z*t.scale3d.z*.13))
    basis=u.Transform(location=p,rotation=t.rotation.rotator(),scale=u.Vector(1,1,1))
    gap=max((lambda q:q.z-g.height(q.x,q.y))(u.MathLibrary.transform_location(basis,u.Vector(math.cos(j*math.tau/8)*radius,math.sin(j*math.tau/8)*radius,0))) for j in range(8))
    maximum=max(maximum,gap);assert gap<.1,(name,'Root rim above bank',gap);rows+=1
 return dict(root_crowns_checked=rows,max_root_rim_above_ground_cm=maximum,bank_ferns=ferns,supported_tree_ferns=trees)
if __name__=='__main__':
 QA.mkdir(parents=True,exist_ok=True);report={'ok':False};busy=False;deadline=0
 def save():(QA/'install.json').write_text(json.dumps(report,indent=2))
 def run():
  les=u.get_editor_subsystem(u.LevelEditorSubsystem);backup=ROOT/'Saved/LidarAuthoringBackups'/('RS5-'+str(time.time_ns()));backup.mkdir(parents=True)
  mapfile=ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap';shutil.copy2(mapfile,backup/'L_LidarStudy.umap');report['backup']=str(backup);save()
  assert les.load_level(BASE+'/L_LidarStudy');yield 2
  report['placement']=apply();inventories();report['snapshot']=snapshot();save()
  apply();assert snapshot()==report['snapshot'];report['idempotent']=True
  assert les.save_current_level();yield 2
  gc.collect();assert les.load_level('/Engine/Maps/Entry');yield 3
  assert les.load_level(BASE+'/L_LidarStudy');yield 2
  assert snapshot()==report['snapshot'];report.update(ok=True,reloaded=True)
  import lidar_road_style
  report['map_sha256']=lidar_road_style.digest(mapfile);save()
  (OUT/'bank-planting.json').write_text(json.dumps(dict(version=VERSION,report=str(QA/'install.json'))))
  gc.collect();les.load_level('/Engine/Maps/Entry');yield 3
 steps=run();began=time.monotonic()
 def tick(dt):
  global busy,deadline,steps
  if busy:return
  busy=True
  try:
   assert time.monotonic()-began<750
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
  except Exception:
   report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
