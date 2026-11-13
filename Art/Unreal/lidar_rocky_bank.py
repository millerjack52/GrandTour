"""RS6: embedded angular outcrops and sparse rooted ledge plants in the river bend."""
import unreal as u
from pathlib import Path
import sys,json,math,random,hashlib
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_river_plant_variety as plants
from lidar_grounding import GroundSampler
from benmore_river_life_materials import props,Graph
BASE=plants.BASE;KIT=plants.KIT;OUT=plants.OUT
QA=ROOT/'Saved/LidarAuthoringQA/RS6';DEST=BASE+'/RockyBank'
PREFIX='LidarStudy_RS6_';VERSION='rs6-1'
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
# A broken arc following the outside of the horseshoe, deliberately off the roads.
ANCHORS=[(-49100,-30600),(-48000,-30060),(-46950,-30250),(-46050,-30900),(-45150,-31850),(-44780,-32950),(-44700,-34000)]
def context():
 refs=actors.get_all_level_actors();a=next(a for a in refs if isinstance(a,u.GTProceduralGround))
 return refs,a,GroundSampler(a)
def gradient(g,x,y):return ((g.height(x+100,y)-g.height(x-100,y))/200,(g.height(x,y+100)-g.height(x,y-100))/200)
def road_distance(x,y):
 if not hasattr(road_distance,'segments'):
  roads=json.loads((OUT/'roads.json').read_text());road_distance.segments=[]
  for r in roads:
   p=r.get('authoring',{}).get('points_cm',r['points']);road_distance.segments.extend(zip(p,p[1:]))
 dist=1e12
 for a,b in road_distance.segments:
  dx=b[0]-a[0];dy=b[1]-a[1];t=max(0,min(1,((x-a[0])*dx+(y-a[1])*dy)/max(1,dx*dx+dy*dy)))
  dist=min(dist,math.hypot(x-a[0]-t*dx,y-a[1]-t*dy))
 return dist
def assets():
 e=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;result={}
 # Share the bank's world-space texture, pigment and scale across the new geometry.
 # This avoids the imported pack's unrelated pale stone and bright moss caps.
 import lidar_slope_style as slope
 path=DEST+'/M_BankStone'
 stone=u.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset('M_BankStone',DEST,u.Material,u.MaterialFactoryNew())
 for n in list(mel.get_material_expressions(stone)):mel.delete_material_expression(stone,n)
 graph=Graph(stone,'RS6BankStone');p=graph.node(u.MaterialExpressionWorldPosition)
 texture=graph.node(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/T_tiles_rock_slope__d_a'))
 code=slope.CODE.replace('float4 s=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+185000)/370000),0);','').replace('[branch] if(s.a<.001)return Native;','')
 code=code[:code.index('float3 r=lerp(old,stone,steep);')]+'return saturate(stone);'
 pigment=graph.custom(['P','Rock'],code);graph.wire(p,pigment,'P');graph.wire(texture,pigment,'Rock')
 graph.output(pigment,u.MaterialProperty.MP_BASE_COLOR);graph.output(graph.scalar(.91),u.MaterialProperty.MP_ROUGHNESS);graph.output(graph.scalar(.18),u.MaterialProperty.MP_SPECULAR)
 assert not mel.recompile_material(stone);assert e.save_loaded_asset(stone)
 for k in [1,2,3]:
  path=DEST+'/SM_RiverOutcrop_'+str(k)
  m=u.load_asset(path) if e.does_asset_exist(path) else e.duplicate_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Benmore_Rock'+str(k),path)
  m.set_material(0,stone);e.save_loaded_asset(m);result[k]=m
 return result
def build_rocks():
 refs,author,g=context();rng=random.Random(6126);meshes=assets();rows=[]
 for a in refs:
  if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a)
 samples=json.loads((ROOT/'Art/Export/BenmoreEnvironment/rock-undersides.json').read_text())
 for group,(ax,ay) in enumerate(ANCHORS):
  gx,gy=gradient(g,ax,ay);ll=max(.01,math.hypot(gx,gy));cx,cy=gy/ll,-gx/ll;ux,uy=gx/ll,gy/ll
  stagger=[-100,260,-120,200,-180,140,-150][group]
  for part,(along,up,width,depth,height) in enumerate([(0,stagger,1100,1150,950),(410,stagger+250,760,760,620),(-250,stagger-550,720,650,450)]):
   x=ax+cx*along+ux*up;y=ay+cy*along+uy*up;k=1+(group+part)%3;m=meshes[k];b=m.get_bounding_box()
   width*=rng.uniform(.85,1.16);depth*=rng.uniform(.88,1.12);height*=rng.uniform(.78,1.12)
   sx=width/(b.max.x-b.min.x);sy=depth/(b.max.y-b.min.y);sz=height/(b.max.z-b.min.z)
   # Moderate bedding tilt leaves actual upward-facing shelves on the rock mesh.
   gx,gy=gradient(g,x,y);axis=u.Vector(-gx*.20,-gy*.20,1)
   rot=u.MathLibrary.make_rot_from_xz(u.Vector(cx,cy,0),axis)
   local=u.Transform(location=u.Vector(x,y,0),rotation=rot,scale=u.Vector(sx,sy,sz))
   cutoff=b.min.z+(b.max.z-b.min.z)*.32
   back=[u.MathLibrary.transform_location(local,u.Vector(*(v*100 for v in p))) for p in samples[str(k)] if p[2]*100<cutoff]
   assert back
   z=min(g.height(p.x,p.y)-p.z for p in back)-55
   tf=u.Transform(location=u.Vector(x,y,z),rotation=rot,scale=u.Vector(sx,sy,sz))
   corners=[u.MathLibrary.transform_location(tf,u.Vector(xx,yy,zz)) for xx in [b.min.x,b.max.x] for yy in [b.min.y,b.max.y] for zz in [b.min.z,b.max.z]]
   radius=max(math.hypot(p.x-x,p.y-y) for p in corners);clear=road_distance(x,y)-radius
   if clear<400:continue
   a=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(PREFIX+'Rock_%02d_%d'%(group,part))
   c=a.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(m);c.set_collision_profile_name('BlockAll');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
   a.set_actor_transform(tf,False,True);a.tags=['RS6RockOutcrop']
   gap=max(p.z+z-g.height(p.x,p.y) for p in back);assert gap<=-11
   rows.append(dict(label=a.get_actor_label(),kind=k,tf=plants.tfkey(a.get_actor_transform()),center=[x,y],radius=radius,road_clearance_cm=clear,buried_support_gap_cm=gap))
 assert len(rows)>=12,len(rows)
 return dict(version=VERSION,rocks=rows,ground_digest=str(author.output_digest))
def rock_trace(x,y,ignore):
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,10000),u.Vector(x,y,3500),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
 if not hit:return None
 r=hit.to_tuple()
 if not r[0] or not r[9] or not r[9].get_actor_label().startswith(PREFIX+'Rock_'):return None
 return r[5],r[7],r[9]
def plant_ledges(report):
 refs,author,g=context();rockactors=[a for a in refs if a.get_actor_label().startswith(PREFIX+'Rock_')];ignore=[a for a in refs if a not in rockactors]
 # Clear the continuous steep face inside this arc, not just tiny holes at each rock.
 def footprint(x,y,pad=0):return any(math.hypot(x-r['center'][0],y-r['center'][1])<r['radius']+pad for r in report['rocks'])
 removed={};protected=[];after=[]
 for a in refs:
  label=a.get_actor_label()
  isforest=label=='LidarStudy_Forest'
  if not (isforest or label=='LidarStudy_Understory' or label.startswith(('LidarStudy_RiverDetail_',plants.PREFIX,'LidarStudy_RS5_'))):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh:continue
   rm=[];keep=[]
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);p=t.translation
    clear=footprint(p.x,p.y,60 if isforest else 230)
    if clear:rm.append(i)
    else:keep.append(plants.tfkey(t))
   protected.append((label,c.get_name(),plants.digest(keep)))
   if rm:c.remove_instances(sorted(rm,reverse=True));removed[c.static_mesh.get_name()]=removed.get(c.static_mesh.get_name(),0)+len(rm)
   after.append((label,c.get_name(),plants.digest([plants.tfkey(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())])))
 assert protected==after,'Instances outside rock clearing changed'
 # Upright rushes and compact shrubs have volume; no flat fern rosettes on the faces.
 rng=random.Random(619);placed=[];batches={}
 for rock in report['rocks']:
  x,y=rock['center'];radius=rock['radius'];found=0
  for attempt in range(75):
   xx=x+rng.uniform(-.65,.65)*radius;yy=y+rng.uniform(-.65,.65)*radius;hit=rock_trace(xx,yy,ignore)
   if not hit:continue
   p,n,a=hit
   if n.z<.82 or p.z<g.height(xx,yy)+15:continue
   if any(math.hypot(p.x-q['root'][0],p.y-q['root'][1])<95 for q in placed):continue
   # Four root probes must all be supported by actual rock within 8 cm.
   support=[rock_trace(xx+dx,yy+dy,ignore) for dx,dy in [(8,0),(-8,0),(0,8),(0,-8)]]
   if any(h is None or abs(h[0].z-p.z)>8 for h in support):continue
   # Avoid the middle of broad bare slabs: seek a nearby edge or intersecting seam.
   edge=[rock_trace(xx+dx,yy+dy,ignore) for dx,dy in [(70,0),(-70,0),(0,70),(0,-70)]]
   if all(h and abs(h[0].z-p.z)<25 and h[2]==a for h in edge):continue
   name='SM_NZ_'+rng.choices(['Rush_A','Rush_B','VergeTussock_A','Coprosma_A','Harakeke_B'],[3,2,2,2,1])[0]
   mesh=u.load_asset(KIT+'/'+name)
   if not mesh:name='SM_NZ_VergeTussock_A';mesh=u.load_asset(KIT+'/'+name)
   assert mesh
   height=rng.uniform(50,100);sc=height/max(1,mesh.get_bounds().box_extent.z*2)
   z=min(h[0].z for h in support)-4
   tf=u.Transform(location=u.Vector(xx,yy,z),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc*.82,sc*.82,sc))
   batches.setdefault(name,[]).append(tf);placed.append(dict(root=[xx,yy,z],mesh=name,support=a.get_actor_label(),normal_z=n.z,max_root_gap_cm=z-min(h[0].z for h in support)))
   found+=1
   if found>=4:break
 for name,tfs in batches.items():
  a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(PREFIX+'Ledge_'+name);a.tags=['RS6LedgePlants']
  mesh=u.load_asset(KIT+'/'+name);c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,tfs,'RS6LedgePlants','NoCollision',False)
  c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cull_distances(15000,22000)
  props(c,cast_shadow=True,visible_in_ray_tracing=False)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   material=slot.get_editor_property('material_interface')
   if material and material.get_name()=='M_NZ_Foliage':c.set_material(i,u.load_asset(BASE+'/MI_NZ_Foliage_Bush'))
 report.update(removed=removed,ledge_plants=placed,outside_instances_preserved=True)
 assert str(author.output_digest)==report['ground_digest']
 return report
def snapshot():
 rows=[]
 for a in actors.get_all_level_actors():
  if not a.get_actor_label().startswith(PREFIX):continue
  c=a.get_component_by_class(u.StaticMeshComponent)
  if c and c.static_mesh:rows.append((a.get_actor_label(),c.static_mesh.get_path_name(),plants.tfkey(a.get_actor_transform())))
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   for i in range(c.get_instance_count()):rows.append((a.get_actor_label(),c.static_mesh.get_path_name(),plants.tfkey(c.get_instance_transform(i,True))))
 return plants.digest(rows)
def apply():return plant_ledges(build_rocks())

def owner_inventory():
 rows={}
 for a in actors.get_all_level_actors():
  if a.get_actor_label() not in ('LidarStudy_Forest','LidarStudy_Understory'):continue
  counts={}
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if c.static_mesh:
    name=c.static_mesh.get_name();counts[name]=counts.get(name,0)+c.get_instance_count()
  rows[a.get_actor_label()]=counts
 return rows

def validate(report):
 refs,author,g=context();byname={a.get_actor_label():a for a in refs}
 rocks=[byname[r['label']] for r in report['rocks']];ignore=[a for a in refs if a not in rocks]
 assert str(author.output_digest)==report['ground_digest']
 for r in report['rocks']:
  a=byname[r['label']];c=a.get_component_by_class(u.StaticMeshComponent)
  assert plants.tfkey(a.get_actor_transform())==tuple(r['tf'])
  assert c.get_collision_enabled()==u.CollisionEnabled.QUERY_AND_PHYSICS
  assert 'USE_COMPLEX_AS_SIMPLE' in str(c.static_mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag'))
  assert c.static_mesh.get_material(0).get_name()=='M_BankStone'
  assert road_distance(*r['center'])-r['radius']>=400
 planted=0;maxgap=-1e9
 for a in refs:
  if not a.get_actor_label().startswith(PREFIX+'Ledge_'):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   for i in range(c.get_instance_count()):
    tf=c.get_instance_transform(i,True);p=tf.translation;rot=tf.rotation.rotator()
    assert abs(rot.pitch)<.01 and abs(rot.roll)<.01,'Ledge plants must grow upward'
    for dx,dy in [(8,0),(-8,0),(0,8),(0,-8)]:
     h=rock_trace(p.x+dx,p.y+dy,ignore);assert h
     gap=p.z-h[0].z;maxgap=max(maxgap,gap);assert gap<=.1 and gap>-22
    planted+=1
 assert planted==len(report['ledge_plants']) and planted>=20
 forest=byname['LidarStudy_Forest'];trunks=[];canopy=[]
 for c in forest.get_components_by_class(u.InstancedStaticMeshComponent):
  if not c.static_mesh:continue
  name=c.static_mesh.get_name()
  for i in range(c.get_instance_count()):
   p=c.get_instance_transform(i,True).translation;key=(round(p.x,1),round(p.y,1))
   if name=='Cylinder':trunks.append(key)
   elif name.startswith('SM_Canopy_'):canopy.append(key)
 assert sorted(trunks)==sorted(canopy),'Tree visuals and collision roots differ'
 return dict(rocks=len(rocks),ledge_plants=planted,max_root_gap_cm=maxgap,tree_collision_pairs=len(trunks),minimum_road_clearance_cm=min(r['road_clearance_cm'] for r in report['rocks']),ground_unchanged=True)
