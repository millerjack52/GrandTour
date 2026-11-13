"""RS3: a bounded riverbank planting pass with mixed silhouettes and open gaps."""
from pathlib import Path
import unreal as u
import sys,json,math,random,hashlib,shutil,time,traceback,gc
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from lidar_grounding import GroundSampler
from benmore_river_life_materials import props
BASE='/Game/GrandTour/ArtTests/LidarStudy';KIT='/Game/GrandTour/Environment/NativePlants/v01'
OUT=ROOT/'Art/Export/LidarStudy/Place';QA=ROOT/'Saved/LidarAuthoringQA/RS3'
PREFIX='LidarStudy_RS3_';VERSION='rs3-2'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary
REPLACE=('CrownFern','Kiokio','VergeTussock','Rush','Harakeke','Coprosma')
def inside(x,y):return ((x+48000)/6500)**2+((y+34600)/7500)**2<1
def tfkey(t):return tuple(round(v,4) for v in (*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()))
def digest(rows):return hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest()
def apply():
 refs=actors.get_all_level_actors();author=next(a for a in refs if isinstance(a,u.GTProceduralGround));ground=GroundSampler(author)
 terrain=str(author.output_digest);rng=random.Random(20261106);removed={};seeds=[];outside_before=[];outside_after=[]
 # Replace only low living foliage in this reach. Trees, rock, debris and collision remain.
 for a in refs:
  if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a);continue
  if a.get_actor_label()!='LidarStudy_Understory' and not a.get_actor_label().startswith('LidarStudy_RiverDetail_'):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   mesh=c.static_mesh
   if not mesh or not mesh.get_name().removeprefix('SM_NZ_').startswith(REPLACE):continue
   assert c.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION,(a.get_actor_label(),mesh.get_name())
   indices=[];keep=[]
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);p=t.translation
    if inside(p.x,p.y):indices.append(i);seeds.append([p.x,p.y])
    else:keep.append(tfkey(t))
   outside_before.append((a.get_actor_label(),c.get_name(),digest(keep)))
   if indices:
    assert c.remove_instances(sorted(indices,reverse=True))
    removed[mesh.get_name()]=removed.get(mesh.get_name(),0)+len(indices)
   outside_after.append((a.get_actor_label(),c.get_name(),digest([tfkey(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())])))
 assert outside_before==outside_after,'Plant instances outside the study changed'
 # Store original candidates so repeat application generates exactly the same planting.
 seedfile=OUT/'river-plant-seeds.json'
 if seedfile.exists():seeds=json.loads(seedfile.read_text())
 else:
  assert seeds;seedfile.write_text(json.dumps(sorted(seeds)))
 seeds=sorted(seeds);rng.shuffle(seeds)
 roads=json.loads((OUT/'roads.json').read_text());segments=[]
 for road in roads:
  pts=road.get('authoring',{}).get('points_cm',road['points'])
  segments.extend((a,b) for a,b in zip(pts,pts[1:]) if inside(a[0],a[1]) or inside(b[0],b[1]))
 def roadclear(x,y):
  for a,b in segments:
   dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
   if math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)<270:return False
  return True
 sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet) and not a.get_editor_property('mud_initial_domain'))
 species={'VergeTussock_A':(45,85),'VergeTussock_B':(40,90),'Rush_A':(50,95),'Rush_B':(40,85),'CrownFern_A':(50,100),'Kiokio_B':(40,85),'Coprosma_A':(85,145),'Coprosma_B':(65,125),'Harakeke_B':(90,155)}
 meshes={n:u.load_asset(KIT+'/SM_NZ_'+n) for n in species};assert all(meshes.values())
 palette={}
 for name,tint in [('Sage',(.83,.98,.81)),('Olive',(.91,.94,.65)),('Deep',(.64,.86,.76)),('Gold',(.98,.90,.59))]:
  path=BASE+'/RS3/MI_'+name;m=u.load_asset(path) or assets.duplicate_asset(BASE+'/MI_NZ_Foliage_Bush',path);assert m
  u.MaterialEditingLibrary.set_material_instance_vector_parameter_value(m,'Tint',u.LinearColor(*tint,1));u.MaterialEditingLibrary.update_material_instance(m);assert assets.save_loaded_asset(m,False);palette[name]=m
 # Select unevenly sized islands with generous gaps instead of a blanket scatter.
 centres=[(x,y,340) for x,y in [(-49050,-35050),(-48350,-34550),(-48000,-33900),(-48900,-33800),(-47550,-34400)] if roadclear(x,y)]
 for x,y in seeds:
  if any(math.hypot(x-cx,y-cy)<spacing for cx,cy,spacing in centres):continue
  if not roadclear(x,y):continue
  centres.append((x,y,rng.uniform(270,490)))
  if len(centres)>=270:break
 groups={};positions=[];rejected=0
 # Each bed has a dominant shape with contrasting companions, not a random species per point.
 mixes=[['VergeTussock_A','VergeTussock_B','Coprosma_B'],['Rush_A','Rush_B','Kiokio_B'],['Coprosma_A','CrownFern_A','VergeTussock_B'],['Harakeke_B','VergeTussock_A','Kiokio_B']]
 for k,(cx,cy,spacing) in enumerate(centres):
  mix=mixes[k%4] if k<5 else mixes[rng.randrange(len(mixes))];colour=rng.choice(['Sage','Olive','Deep']);radius=rng.uniform(170,330)
  for j in range(rng.randint(10,20)):
   angle=rng.random()*math.tau;rad=math.sqrt(rng.random())*radius
   x=cx+math.cos(angle)*rad;y=cy+math.sin(angle)*rad*rng.uniform(.55,1.15)
   z=ground.height(x,y);xy=u.Vector2D(x,y)
   if not inside(x,y) or not roadclear(x,y) or (sheet.covers(xy) and z<sheet.surface_cm_at(xy)+18):rejected+=1;continue
   slope=max(abs(ground.height(x+45,y)-ground.height(x-45,y)),abs(ground.height(x,y+45)-ground.height(x,y-45)))/90
   if slope>1.15 or any(math.hypot(x-px,y-py)<65 for px,py in positions):rejected+=1;continue
   name=mix[0] if j<3 else rng.choice(mix[1:]);lo,hi=species[name];height=rng.uniform(lo,hi)
   mesh=meshes[name];scale=height/max(1,mesh.get_bounds().box_extent.z*2);width=scale*rng.uniform(.75,1.2)
   tf=u.Transform(location=u.Vector(x,y,z-3),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(width,width,scale))
   tint='Gold' if name.startswith('VergeTussock') and rng.random()<.28 else colour
   groups.setdefault((name,tint),[]).append(tf);positions.append((x,y))
 assert 1200<=len(positions)<=4000,(len(positions),len(centres))
 for (name,tint),ts in groups.items():
  a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(PREFIX+name+'_'+tint);a.tags=['LidarRiverPlantVariety',VERSION]
  c=u.GTVegetationSubsystem.add_tagged_instances(a,meshes[name],ts,'LidarRiverPlantVariety','NoCollision',False)
  c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cull_distances(10000,16000)
  props(c,cast_shadow=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),cast_shadow_as_two_sided=any(k in name for k in ('Coprosma','Gorse','Broom','Matagouri','Shrub')),visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  for i,slot in enumerate(meshes[name].get_editor_property('static_materials')):
   m=slot.get_editor_property('material_interface')
   if m and m.get_name()=='M_NZ_Foliage':c.set_material(i,palette[tint])
 assert str(author.output_digest)==terrain
 bank_fit=None
 if (OUT/'bank-planting.json').exists():
  import lidar_bank_planting
  bank_fit=lidar_bank_planting.apply()
 if (OUT/'rocky-bank.json').exists():
  import lidar_rocky_bank
  lidar_rocky_bank.apply()
 # Keep the pre-existing river-detail inventory accurate after selective removal.
 detailfile=OUT/'riverdetail.json'
 if detailfile.exists():
  d=json.loads(detailfile.read_text());counts={};components=0
  for a in actors.get_all_level_actors():
   if not a.get_actor_label().startswith('LidarStudy_RiverDetail_'):continue
   components+=1
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):counts[c.static_mesh.get_name()]=counts.get(c.static_mesh.get_name(),0)+c.get_instance_count()
  d.update(instances=sum(counts.values()),components=components,by_mesh=counts,rs3_selective_plant_removal=True);detailfile.write_text(json.dumps(d,indent=2))
 # ISM stores single-precision instance matrices; validate their actual readback,
 # rather than comparing against the double-precision construction inputs.
 stored=[tfkey(c.get_instance_transform(i,True)) for a in actors.get_all_level_actors() if a.get_actor_label().startswith(PREFIX) for c in a.get_components_by_class(u.InstancedStaticMeshComponent) for i in range(c.get_instance_count())]
 actual_groups={a.get_actor_label()[len(PREFIX):]:sum(c.get_instance_count() for c in a.get_components_by_class(u.InstancedStaticMeshComponent)) for a in actors.get_all_level_actors() if a.get_actor_label().startswith(PREFIX)}
 return dict(version=VERSION,removed=removed,total=len(stored),generated_total=len(positions),clusters=len(centres),groups=actual_groups,bank_fit=bank_fit,rejected=rejected,ground_digest=terrain,outside_preserved=True,minimum_road_clearance_cm=270,signature=digest(stored))

if __name__=='__main__':
 QA.mkdir(parents=True,exist_ok=True);report=dict(ok=False);busy=False;deadline=0
 def save():(QA/'install.json').write_text(json.dumps(report,indent=2))
 def run():
  les=u.get_editor_subsystem(u.LevelEditorSubsystem)
  backup=ROOT/'Saved/LidarAuthoringBackups'/('RS3-'+str(time.time_ns()));backup.mkdir(parents=True)
  shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
  report['backup']=str(backup);save()
  assert les.load_level(BASE+'/L_LidarStudy');yield 2
  report['planting']=apply();save()
  repeat=apply();assert repeat['signature']==report['planting']['signature'];report['idempotent']=True
  assert les.save_current_level();yield 2
  gc.collect();assert les.load_level('/Engine/Maps/Entry');yield 3
  assert les.load_level(BASE+'/L_LidarStudy');yield 2
  rows=[tfkey(c.get_instance_transform(i,True)) for a in actors.get_all_level_actors() if a.get_actor_label().startswith(PREFIX) for c in a.get_components_by_class(u.InstancedStaticMeshComponent) for i in range(c.get_instance_count())]
  assert len(rows)==report['planting']['total'];assert digest(rows)==report['planting']['signature']
  report.update(ok=True,reloaded=True);save();(OUT/'river-plant-variety.json').write_text(json.dumps(dict(version=VERSION,report=str(QA/'install.json'))))
  gc.collect();les.load_level('/Engine/Maps/Entry');yield 3
 steps=run();began=time.monotonic()
 def tick(dt):
  global busy,deadline,steps
  if busy:return
  busy=True
  try:
   assert time.monotonic()-began<700
   if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
  except StopIteration:u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
  except Exception:
   report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
  finally:busy=False
 u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
