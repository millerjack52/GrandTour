"""Bounded RS7 first section. Separate assets; shared terrain and plant kit untouched."""
import unreal as u
import json,math,random,hashlib,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_section_surface as S
from lidar_grounding import GroundSampler
from benmore_river_life_materials import Graph,props
BASE='/Game/GrandTour/ArtTests/LidarStudy';DEST=BASE+'/FirstSection'
OUT=ROOT/'Art/Export/LidarStudy/FirstSection';QA=ROOT/'Saved/LidarAuthoringQA/RS7'
actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
PREFIX='LidarStudy_RS7_'

def material(name,leaf=False):
 if not leaf:
  from lidar_bank_ground_material import build
  return build(name)
 m=u.load_asset(DEST+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);g=Graph(m,'RS7')
 props(m,two_sided=leaf,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE if leaf else u.MaterialShadingModel.MSM_DEFAULT_LIT,dithered_lod_transition=True)
 vc=g.node(u.MaterialExpressionVertexColor)
 wp=g.node(u.MaterialExpressionWorldPosition)
 if leaf:
  colour=g.custom(['C','P'],'float broad=.94+.06*sin(P.x*.021+P.y*.016+P.z*.023);return C*float3(1.19,.98,.57)*broad;')
  g.wire(vc,colour,'C');g.wire(wp,colour,'P')
 g.output(colour,u.MaterialProperty.MP_BASE_COLOR)
 if leaf:
  sub=g.node(u.MaterialExpressionMultiply);g.wire(colour,sub,'A');g.wire(g.scalar(.32),sub,'B');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
  wind=g.custom(['P','T','A'],'return float3(sin(T*1.1+P.x*.004+P.y*.006)*A*1.8,cos(T*.9+P.x*.003)*A*.8,0);')
  g.wire(g.node(u.MaterialExpressionWorldPosition),wind,'P');g.wire(g.node(u.MaterialExpressionTime),wind,'T');g.wire(vc,wind,'A','A');g.output(wind,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
 g.output(g.scalar(.84 if leaf else .92),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.12),u.MaterialProperty.MP_SPECULAR)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
 assert not mel.recompile_material(m);assets.save_loaded_asset(m)
 import lidar_bank_material_polish as polish
 if polish.enabled():polish.leaf(name)
 return m

def import_assets():
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 assets.make_directory(DEST);leaf=material('M_BankLeaf',True);earth=material('M_BankEarth');surface=material('M_BankSurface')
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);rows=json.loads((OUT/'plants.json').read_text())+[dict(asset='SM_RS7_BankSkin')]
 report=[]
 for row in rows:
  name=row['asset'];task=u.AssetImportTask();task.filename=str(OUT/(name+'_LOD0.fbx'));task.destination_path=DEST;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=True
  opt=u.FbxImportUI();opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name);assert mesh
  if 'lods' in row:
   screens=[1.,.025,.007];options=u.StaticMeshReductionOptions();options.auto_compute_lod_screen_size=False;settings=[]
   for screen in screens:
    r=u.StaticMeshReductionSettings();r.percent_triangles=1.;r.screen_size=screen;settings.append(r)
   options.reduction_settings=settings;assert sm.set_lods(mesh,options)==3
   for lod in (1,2):assert sm.import_lod(mesh,lod,str(OUT/(name+'_LOD'+str(lod)+'.fbx')))==lod
   assert sm.set_lod_screen_sizes(mesh,screens)
   assert 60<mesh.get_bounds().box_extent.z*2<400,(name,str(mesh.get_bounds()))
   sm.remove_collisions(mesh)
  else:
   assert 1500<mesh.get_bounds().box_extent.x*2<3500
   mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
  for i,slot in enumerate(mesh.get_editor_property('static_materials')):
   isleaf='foliage' in str(slot.get_editor_property('material_slot_name')).lower();mesh.set_material(i,surface if name=='SM_RS7_BankSkin' else leaf if isleaf else earth)
  ns=mesh.get_editor_property('nanite_settings');ns.enabled=False;sm.set_nanite_settings(mesh,ns,True)
  assets.save_loaded_asset(mesh);report.append(dict(asset=name,lods=sm.get_lod_count(mesh),size=str(mesh.get_bounds().box_extent*2)))
 (QA/'imports.json').write_text(json.dumps(report,indent=2));return report

def tfkey(t):
 p=t.translation;q=t.rotation;s=t.scale3d
 return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def selected(a):
 return a.get_actor_label()=='LidarStudy_Understory' or a.get_actor_label().startswith(('LidarStudy_RS3_','LidarStudy_RS5_','LidarStudy_RiverDetail_'))
def outside_snapshot():
 h=hashlib.sha256();n=0
 for a in actors.get_all_level_actors():
  if not selected(a):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.static_mesh:continue
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True)
    if not S.inside(t.translation.x,t.translation.y):h.update(json.dumps([a.get_name(),c.get_name(),tfkey(t)]).encode());n+=1
 return {'hash':h.hexdigest(),'instances':n}

def apply():
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));g=GroundSampler(author);digest=str(author.output_digest)
 before=outside_snapshot();removed=[]
 prior=QA/'source-removals.json'
 if not any(a.get_actor_label()==PREFIX+'SourceState' for a in actors.get_all_level_actors()):
  for a in actors.get_all_level_actors():
   if not selected(a):continue
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if not c.static_mesh or not any(k in c.static_mesh.get_name() for k in ['CrownFern','Kiokio','MossHummock','RootTangle','Coprosma','VergeTussock','Rush','Harakeke']):continue
    ids=[]
    for i in range(c.get_instance_count()):
     t=c.get_instance_transform(i,True);p=t.translation
     if S.inside(p.x,p.y):ids.append(i);removed.append(dict(actor=a.get_name(),component=c.get_name(),mesh=c.static_mesh.get_path_name(),transform=tfkey(t)))
    if ids:assert c.remove_instances(sorted(ids,reverse=True))
  prior.write_text(json.dumps(removed,indent=2))
 for a in list(actors.get_all_level_actors()):
  if a.get_actor_label().startswith(PREFIX):actors.destroy_actor(a)
 marker=actors.spawn_actor_from_class(u.Actor,u.Vector());marker.set_actor_label(PREFIX+'SourceState')
 skin=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(S.CX,S.CY,4800));skin.set_actor_label(PREFIX+'BankSkin')
 sc=skin.static_mesh_component;sc.set_static_mesh(u.load_asset(DEST+'/SM_RS7_BankSkin'));sc.set_collision_profile_name('BlockAll')
 rows=json.loads((OUT/'plants.json').read_text());rng=random.Random(731119);groups={};placed=[];rejected=0
 # The approved layout is also the basis for geometric relief contact guards.
 # Rebuild it exactly instead of rerolling slope-dependent species or yaw.
 layout_path=OUT/'plant-layout.json'
 if layout_path.exists():
  placed=json.loads(layout_path.read_text())
  for p in placed:
   t=u.Transform(location=u.Vector(p['x'],p['y'],p['z']),rotation=u.Rotator(yaw=p['yaw']),scale=u.Vector(p['scale'],p['scale'],p['scale']))
   groups.setdefault(p['mesh'],[]).append(t)
 def support(x,y):return g.height(x,y)+max(0,S.relief(x,y))
 # Uneven connected communities, with readable exposed-rock gaps.
 for i in range(0 if layout_path.exists() else 320):
  a=rng.uniform(-1020,1020);b=rng.uniform(-700,700);x,y=S.xy(a,b)
  patch=.5+.5*math.sin(a*.006+math.sin(b*.005))
  if rng.random()>.52+.42*patch:continue
  r=S.rock(a,b)
  if r>.6 and rng.random()<.8:continue
  if any((x-p['x'])**2+(y-p['y'])**2<62**2 for p in placed):continue
  gx=(support(x+25,y)-support(x-25,y))/50;gy=(support(x,y+25)-support(x,y-25))/50
  angle=math.degrees(math.atan(math.hypot(gx,gy)))
  kind='Crevice' if r>.5 else rng.choices(['Cascade','Fine','Crown'],[.48,.30,.22])[0]
  row=rng.choice([v for v in rows if v['kind']==kind]);scale=rng.uniform(.68,1.14)
  if kind=='Crevice':scale=rng.uniform(.65,.95)
  yaw=math.degrees(math.atan2(-gy,-gx))+rng.uniform(-14,14)
  if math.hypot(gx,gy)<.15:yaw=-145+rng.uniform(-35,35)
  # Crown envelope seats below the actual support, while the growth frame stays upright.
  z=min(support(x+math.cos(k*math.tau/8)*7*scale,y+math.sin(k*math.tau/8)*7*scale) for k in range(8))-1
  tf=u.Transform(location=u.Vector(x,y,z),rotation=u.Rotator(yaw=yaw),scale=u.Vector(scale,scale,scale))
  clear=[]
  for probe in row['probes']:
   p=u.MathLibrary.transform_location(tf,u.Vector(probe[0]*100,-probe[1]*100,probe[2]*100));clear.append(p.z-support(p.x,p.y))
  if sum(v<-12 for v in clear)>len(clear)*.12:rejected+=1;continue
  groups.setdefault(row['asset'],[]).append(tf);placed.append(dict(x=x,y=y,z=z,mesh=row['asset'],scale=scale,yaw=yaw,slope=angle,clipping_fraction=sum(v<-12 for v in clear)/len(clear),min_frond_clearance=min(clear)))
 for name,tfs in groups.items():
  a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(PREFIX+name);a.root_component.set_mobility(u.ComponentMobility.STATIC)
  c=u.GTVegetationSubsystem.add_tagged_instances(a,u.load_asset(DEST+'/'+name),tfs,'RS7BankPlants','NoCollision',False)
  c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cull_distances(14000,20000);c.set_lod_distance_scale(1.)
  # Leaf silhouettes must self-shadow and anchor the plants to the bank.
  props(c,cast_shadow=True,cast_shadow_as_two_sided=True,affect_distance_field_lighting=False,visible_in_ray_tracing=False)
 assert str(author.output_digest)==digest
 after=outside_snapshot();assert before==after,'Outside planting changed'
 report=dict(version='RS7-1',ground_digest=digest,outside=after,removed=len(json.loads(prior.read_text())),plants=len(placed),rejected_frond_support=rejected,placement=placed,groups={k:len(v) for k,v in groups.items()},shared_materials_unchanged=True,trees_unchanged=True)
 (QA/'placement.json').write_text(json.dumps(report,indent=2));return report

def snapshot():
 rows=[]
 for a in actors.get_all_level_actors():
  if not a.get_actor_label().startswith(PREFIX):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   for i in range(c.get_instance_count()):rows.append([a.get_actor_label(),c.static_mesh.get_path_name(),tfkey(c.get_instance_transform(i,True))])
 return {'count':len(rows),'hash':hashlib.sha256(json.dumps(sorted(rows)).encode()).hexdigest()}

def local_exposure():
 pp=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==PREFIX+'LocalExposure'),None)
 if not pp:pp=actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector(-46500,-32200,4900));pp.set_actor_label(PREFIX+'LocalExposure')
 pp.set_actor_scale3d(u.Vector(35,35,25));props(pp,unbound=False,priority=500.,blend_radius=800.)
 settings=dict(auto_exposure_min_brightness=11.0,auto_exposure_max_brightness=11.0,auto_exposure_bias=0.,local_exposure_highlight_contrast_scale=.6,local_exposure_shadow_contrast_scale=.6,white_temp=7200.)
 s=pp.get_editor_property('settings')
 for k,v in settings.items():s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
 pp.set_editor_property('settings',s)
 (QA/'local-exposure.json').write_text(json.dumps(dict(bounds=str(pp.get_actor_bounds(False)),settings=settings,unbound=False),indent=2))
 return pp

def ground_communities():
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));g=GroundSampler(author);rng=random.Random(73188)
 for a in list(actors.get_all_level_actors()):
  if a.get_actor_label().startswith(PREFIX+'Floor_'):actors.destroy_actor(a)
 path=DEST+'/M_BankGroundLeaf';m=u.load_asset(path) or assets.duplicate_asset(DEST+'/M_BankLeaf',path)
 graph=Graph(m,'RS7StableRoot');zero=next((n for n in mel.get_material_expressions(m) if str(n.get_editor_property('desc'))=='RS7StableRoot'),None)
 if not zero:zero=graph.vector((0,0,0))
 graph.output(zero,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);mel.recompile_material(m);assets.save_loaded_asset(m)
 groups={};kit='/Game/GrandTour/Environment/NativePlants/v01/'
 patches=[(-830,340),(-540,-460),(-220,490),(280,420),(620,-490),(850,100)]
 for aa,bb in patches:
  for i in range(rng.randint(5,10)):
   a=aa+rng.uniform(-100,100);b=bb+rng.uniform(-85,85);x,y=S.xy(a,b)
   if not S.inside(x,y,70):continue
   name=rng.choice(['SM_NZ_VergeTussock_A','SM_NZ_VergeTussock_B']);mesh=u.load_asset(kit+name);sc=rng.uniform(28,58)/(mesh.get_bounds().box_extent.z*2)
   z=g.height(x,y)+max(0,S.relief(x,y))-6
   groups.setdefault(name,[]).append(u.Transform(location=u.Vector(x,y,z),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)))
 for i in range(14):
  a=rng.uniform(-1000,1000);b=rng.uniform(675,810);x,y=S.xy(a,b);name=rng.choice(['SM_NZ_Cobble_Cluster_S','SM_NZ_Cobble_Cluster_M'])
  sc=rng.uniform(.6,1.0);tf=u.Transform(location=u.Vector(x,y,g.height(x,y)+max(0,S.relief(x,y))-4),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc));groups.setdefault(name,[]).append(tf)
 for name,ts in groups.items():
  a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(PREFIX+'Floor_'+name);a.root_component.set_mobility(u.ComponentMobility.STATIC)
  c=u.GTVegetationSubsystem.add_tagged_instances(a,u.load_asset(kit+name),ts,'RS7Floor','NoCollision',False)
  c.set_cull_distances(10000,15000);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_lod_distance_scale(1.)
  for i in range(c.get_num_materials()):c.set_material(i,m if 'Tussock' in name else u.load_asset(DEST+'/M_BankEarth'))
  props(c,cast_shadow=False,affect_distance_field_lighting=False)
 (QA/'floor-communities.json').write_text(json.dumps({name:len(ts) for name,ts in groups.items()},indent=2))

def tree_palette():
 """Rebatch only trees rooted inside the section, preserving transforms/colliders."""
 forest=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_Forest')
 datafile=QA/'forest-sources.json';saved=json.loads(datafile.read_text()) if datafile.exists() else None
 rows=[];outside=[];after=[];colliders=[]
 for c in forest.get_components_by_class(u.InstancedStaticMeshComponent):
  if not c.static_mesh:continue
  if c.static_mesh.get_name()=='Cylinder':
   colliders=[tfkey(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())];continue
  ids=[];keep=[]
  for i in range(c.get_instance_count()):
   tf=c.get_instance_transform(i,True);p=tf.translation
   if S.inside(p.x,p.y):
    ids.append(i);rows.append(dict(mesh=c.static_mesh.get_path_name(),transform=tfkey(tf),materials=[c.get_material(k).get_path_name() for k in range(c.get_num_materials())]))
   else:keep.append(tfkey(tf))
  outside.append(hashlib.sha256(json.dumps(keep).encode()).hexdigest())
  if ids:assert c.remove_instances(sorted(ids,reverse=True))
  after.append(hashlib.sha256(json.dumps([tfkey(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())]).encode()).hexdigest())
 assert outside==after
 if saved is None:datafile.write_text(json.dumps(rows,indent=2));saved=rows
 elif rows:assert rows==saved,'Source trees differ from the recorded baseline'
 name='M_BankBark';m=u.load_asset(DEST+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
 mel.delete_all_material_expressions(m);g=Graph(m,'RS7Bark');p=g.node(u.MaterialExpressionWorldPosition)
 pigment=g.custom(['P','Tex'],'''float grain=Texture2DSample(Tex,TexSampler,P.xz*float2(.011,.002)).g;
float moss=smoothstep(.25,.8,sin(P.z*.008+sin(P.x*.02))*sin(P.y*.014));
return lerp(float3(.13,.105,.073),float3(.10,.15,.05),moss*.65)*(.72+grain*.55);''')
 g.wire(p,pigment,'P');g.wire(g.node(u.MaterialExpressionTextureObject,texture=u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/T_tiles_forest__d_a')),pigment,'Tex');g.output(pigment,u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(.93),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.08),u.MaterialProperty.MP_SPECULAR)
 mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not mel.recompile_material(m);assets.save_loaded_asset(m)
 for a in list(actors.get_all_level_actors()):
  if a.get_actor_label().startswith(PREFIX+'Trees_'):actors.destroy_actor(a)
 groups={}
 for r in saved:groups.setdefault(r['mesh'],[]).append(r)
 for meshpath,rs in groups.items():
  a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(PREFIX+'Trees_'+meshpath.split('.')[-1]);a.root_component.set_mobility(u.ComponentMobility.STATIC)
  tfs=[]
  for r in rs:
   t=r['transform'];tfs.append(u.Transform(location=u.Vector(*t[:3]),rotation=u.Quat(*t[3:7]).rotator(),scale=u.Vector(*t[7:10])))
  c=u.GTVegetationSubsystem.add_tagged_instances(a,u.load_asset(meshpath),tfs,'RS7LocalTrees','NoCollision',False);c.set_lod_distance_scale(2.)
  for i,mat in enumerate(rs[0]['materials']):c.set_material(i,m if 'Bark' in mat else u.load_asset(mat))
  c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
 result=dict(trees=len(saved),transforms_preserved=True,collider_count=len(colliders),collider_hash=hashlib.sha256(json.dumps(colliders).encode()).hexdigest(),outside_tree_hashes=after)
 (QA/'tree-palette.json').write_text(json.dumps(result,indent=2));return result

def validate():
 report=json.loads((QA/'placement.json').read_text());assert outside_snapshot()==report['outside']
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));g=GroundSampler(author);assert str(author.output_digest)==report['ground_digest']
 skin=next(a for a in actors.get_all_level_actors() if a.get_actor_label()==PREFIX+'BankSkin')
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 ignore=[a for a in actors.get_all_level_actors() if a!=skin]
 def skin_z(x,y):
  hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,9000),u.Vector(x,y,3500),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True).to_tuple()
  assert hit[0] and hit[9]==skin,(x,y,'No bank support')
  return hit[5].z
 samples=[]
 for aa,bb in [(-600,0),(600,0),(0,-500),(0,500),(0,0)]:
  x,y=S.xy(aa,bb);actual=skin_z(x,y);expected=g.height(x,y)+S.relief(x,y);samples.append(abs(actual-expected))
 assert max(samples)<4.,samples
 roots=[]
 for p in report['placement']:
  for k in range(4):
   x=p['x']+math.cos(k*math.tau/4)*6*p['scale'];y=p['y']+math.sin(k*math.tau/4)*6*p['scale']
   roots.append(p['z']-max(g.height(x,y),skin_z(x,y)))
 assert max(roots)<3.,max(roots)
 assert max(p['clipping_fraction'] for p in report['placement'])<=.12
 result=dict(ground_digest=report['ground_digest'],outside=report['outside'],snapshot=snapshot(),skin_max_error_cm=max(samples),root_probes=len(roots),max_root_gap_cm=max(roots),minimum_root_offset_cm=min(roots),frond_probes='every frond, sampled longitudinally, authored LOD0 skeleton',no_shared_asset_edits=True)
 (QA/'validation.json').write_text(json.dumps(result,indent=2));return result
