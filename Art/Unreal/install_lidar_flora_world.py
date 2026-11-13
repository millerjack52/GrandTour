"""Whole-map, reversible Flora Paint treatment of LiDARStudy.

Native terrain, water, soil, roads, collision and interactive grass remain owned
by their original systems. Generated art has a separate owner and map profile.
"""
import unreal as u,sys,json,os,math,random,traceback,shutil,hashlib,gc,time
from pathlib import Path
R=Path('C:/GrandTour');sys.path.insert(0,str(R/'Art/Unreal'))
from benmore_river_life_materials import Graph,props
from lidar_grounding import GroundSampler
import lidar_flora_materials as F
BASE='/Game/GrandTour/ArtTests/LidarStudy';D=BASE+'/FloraWorld';O=R/'Art/Export/LidarStudy/FloraWorld';O.mkdir(parents=True,exist_ok=True)
A=u.get_editor_subsystem(u.EditorActorSubsystem);E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;L=u.get_editor_subsystem(u.LevelEditorSubsystem)
STAGE=os.environ.get('GT_FLORA_WORLD_STAGE','audit');PREFIX='LidarStudy_FloraWorld_';F.DEST=D
report={'ok':False,'stage':STAGE}
CFG=O/'profile.json'
DEFAULT=dict(seed=184911,tree_min_height_cm=1450,tree_max_height_cm=2950,tree_min_lod=1,
 plant_cull_start_cm=6500,plant_cull_end_cm=10000,plant_anchor_stride=4,plant_group_size=4,
 palette=dict(strength=.22,palette_strength=.24,normal_simplification=.35,forest_colour=[.045,.105,.065],shadow_colour=[.017,.043,.043],sunlit_colour=[.19,.225,.085],clearing_colour=[.20,.23,.10],clearing_shadow_colour=[.055,.09,.07],ground_tint=[1.04,1.02,.94],patch_variation=.10,finish_strength=.50,finish_saturation=.96,green_restraint=.28,highlight_compression=.12,midtone_gain=1.02,sunlight_warmth=.24,sunlight_lift=.06,sky_palette_strength=.50,sky_horizon_colour=[.64,.78,.80],sky_zenith_colour=[.24,.46,.62],haze_colour=[.47,.64,.69],haze_intensity=.68,haze_start_metres=400.,haze_full_metres=2200.,canopy_depth_strength=.55),
 sun_lux=42000.,sun_temperature=5600.,sky_intensity=2.6,exposure_ev100=12.8,exposure_min_ev100=10.5,exposure_max_ev100=13.1,exposure_bias=.1,fog_density=.025,fog_start_cm=800.,
 foliage_tint=[.77,.91,.83],bark_tint=[1.03,.96,.90],native_fern_tint=[.76,.96,.91],
 ground=dict(GroundTileCm=240.,GroundNormalStrength=1.1,GrainStrength=.55,ReliefDepthCm=2.8,POMEnabled=1.,POMNearCm=700.,POMFarCm=1800.,DetailWidthCm=2400.))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def path(a):return a.get_path_name().split('.')[0] if a else None
def protected(rows):
 a=next(a for a in rows if isinstance(a,u.GTProceduralGround));s=next(a for a in rows if isinstance(a,u.GTLandscapeSurface));v=next(a for a in rows if isinstance(a,u.GTMudRunnerVisual))
 return dict(ground=str(a.output_digest),soil={k:s.get_editor_property(k) for k in ['layer_depth_scale','maximum_layer_depth_cm','bearing_strength','settlement_speed_scale','grass_is_visual_cover','use_native_mud_shader_updates']},water=sorted([[a.get_actor_label(),list(a.get_actor_location().to_tuple())] for a in rows if isinstance(a,u.GTWaterSheet)]),native_grid=dict(follow=v.follow_player_grid,half=v.half_size_cm,tread=path(v.track_material)))
def backup():
 b=Path('D:/GrandTourBackups/FloraWorld_2026-11-13');b.mkdir(parents=True,exist_ok=True)
 p=R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap';dest=b/p.name
 if not dest.exists():shutil.copy2(p,dest)
 assert dest.stat().st_size>1000000000
 report['backup']=str(b)
 return b
def audit(rows):
 out={'protected':protected(rows),'lights':[],'postprocess':[],'fog':[],'components':[]}
 for a in rows:
  if isinstance(a,(u.DirectionalLight,u.SkyLight)):
   c=a.light_component;out['lights'].append(dict(label=a.get_actor_label(),type=a.get_class().get_name(),intensity=c.intensity,colour=str(c.light_color)))
  if isinstance(a,u.PostProcessVolume):
   s=a.settings;out['postprocess'].append(dict(label=a.get_actor_label(),priority=a.priority,settings={k:str(s.get_editor_property(k)) for k in ['auto_exposure_min_brightness','auto_exposure_max_brightness','auto_exposure_bias','color_saturation','color_gain','ambient_occlusion_intensity','ambient_occlusion_radius']}))
  if isinstance(a,u.ExponentialHeightFog):
   c=a.component;out['fog'].append(dict(label=a.get_actor_label(),settings={k:str(c.get_editor_property(k)) for k in ['fog_density','fog_height_falloff','start_distance','enable_volumetric_fog','fog_inscattering_luminance']}))
  if a.get_actor_label() in ['LidarStudy_Forest','LidarStudy_Understory']:
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if c.static_mesh:out['components'].append(dict(actor=a.get_actor_label(),component=c.get_name(),mesh=path(c.static_mesh),count=c.get_instance_count(),materials=[path(m) for m in c.get_materials()]))
 return out
def spawn(label):
 a=A.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label(PREFIX+label);a.set_folder_path('LiDAR/FloraWorld');return a
def tint_material(src,cache,tint):
 local=F.clone_material(src,cache)
 # The purchased graph and its normals remain intact; local finish is editable.
 if isinstance(local,u.MaterialInstanceConstant):
  parent=local.get_editor_property('parent')
  if parent:M.set_material_instance_parent(local,tint_material(parent,cache,tint));E.save_loaded_asset(local,False)
  return local
 nodes=list(M.get_material_expressions(local))
 if not any(str(n.get_editor_property('desc'))=='FloraWorldColour' for n in nodes):
  n=M.get_material_property_input_node(local,u.MaterialProperty.MP_BASE_COLOR)
  if not n:return local
  output=str(M.get_material_property_input_node_output_name(local,u.MaterialProperty.MP_BASE_COLOR));g=Graph(local,'FloraWorldColour')
  p=g.node(u.MaterialExpressionVectorParameter,parameter_name='MapFoliageTint',default_value=u.LinearColor(*tint,1))
  v=g.node(u.MaterialExpressionPerInstanceRandom)
  c=g.custom(['Base','Tint','Variation'],'float t=saturate(Variation);float3 family=lerp(float3(.88,.98,1.06),float3(1.08,1.02,.84),t);return Base*Tint*family*lerp(.91,1.06,t);')
  g.wire(n,c,'Base',output);g.wire(p,c,'Tint');g.wire(v,c,'Variation');g.output(c,u.MaterialProperty.MP_BASE_COLOR)
 for n in M.get_material_expressions(local):
  if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='MapFoliageTint':n.set_editor_property('default_value',u.LinearColor(*tint,1))
 props(local,dithered_lod_transition=True);M.set_material_usage(local,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not M.recompile_material(local);assert E.save_loaded_asset(local,False)
 return local

def style(rows,cfg):
 controller=next(a for a in rows if isinstance(a,u.GTDistanceStyleController))
 p=u.load_asset(D+'/DA_Lidar_FloraWoodland') or E.duplicate_asset(BASE+'/CohesiveStyle/DA_Lidar_Evergreen',D+'/DA_Lidar_FloraWoodland')
 for key,value in cfg['palette'].items():p.set_editor_property(key,u.LinearColor(*value,1) if isinstance(value,list) else value)
 assert E.save_loaded_asset(p,False);controller.profile=p;controller.cohesive=p;controller.apply_profile()
 for a in rows:
  if isinstance(a,u.DirectionalLight):
   c=a.light_component;props(c,intensity=cfg['sun_lux'],use_temperature=True,temperature=cfg['sun_temperature'])
  if isinstance(a,u.SkyLight):a.light_component.set_editor_property('intensity',cfg['sky_intensity'])
  if isinstance(a,u.ExponentialHeightFog):
   # This map owns its authored atmosphere, as FloraPath already does. Global
   # weather otherwise replaces the chosen density with its absolute .01 value.
   if 'GTWeatherUnmanaged' not in [str(t) for t in a.tags]:a.tags=list(a.tags)+[u.Name('GTWeatherUnmanaged')]
   props(a.component,fog_density=cfg.get('fog_density',.025),start_distance=cfg.get('fog_start_cm',800.),fog_inscattering_luminance=u.LinearColor(650,1050,1450,1),enable_volumetric_fog=cfg.get('volumetric_fog',True),volumetric_fog_distance=cfg.get('volumetric_distance_cm',15000.),volumetric_fog_extinction_scale=cfg.get('volumetric_extinction',.65),volumetric_fog_scattering_distribution=.4)
 pp=next((a for a in rows if a.get_actor_label()==PREFIX+'Grade'),None)
 if not pp:
  pp=A.spawn_actor_from_class(u.PostProcessVolume,u.Vector());pp.set_actor_label(PREFIX+'Grade');pp.set_folder_path('LiDAR/FloraWorld')
 props(pp,unbound=True,priority=650.,blend_weight=1.)
 s=pp.settings
 for k,v in dict(auto_exposure_method=u.AutoExposureMethod.AEM_HISTOGRAM,auto_exposure_min_brightness=cfg.get('exposure_min_ev100',10.5),auto_exposure_max_brightness=cfg.get('exposure_max_ev100',13.4),auto_exposure_bias=cfg.get('exposure_bias',.05),auto_exposure_low_percent=80.,auto_exposure_high_percent=98.,auto_exposure_speed_up=3.,auto_exposure_speed_down=2.,color_saturation=u.Vector4(1,1,1,1),color_contrast=u.Vector4(1,1,1,1.02),local_exposure_highlight_contrast_scale=.85,local_exposure_shadow_contrast_scale=.82,bloom_intensity=.08,film_grain_intensity=0.,vignette_intensity=.08).items():
  s.set_editor_property('override_'+k,True);s.set_editor_property(k,v)
 pp.settings=s
 report['profile']=path(p)

def refine_shapes(rows,cfg):
 for label,kind in [(PREFIX+'Canopy','canopy'),('LidarStudy_Understory','fern')]:
  owner=next(a for a in rows if a.get_actor_label()==label)
  key='FloraWorldScale_'+kind+'='
  tags=[str(t) for t in owner.tags];prior=next((t[len(key):] for t in tags if t.startswith(key)),'1,1')
  oldxy,oldz=map(float,prior.split(','));xy=cfg.get('canopy_width_scale',.86) if kind=='canopy' else cfg.get('fern_width_scale',.88);z=1. if kind=='canopy' else cfg.get('fern_height_scale',.62)
  if abs(xy-oldxy)+abs(z-oldz)<1e-6:continue
  for c in owner.get_components_by_class(u.InstancedStaticMeshComponent):
   if kind=='fern' and (not c.static_mesh or not any(s in c.static_mesh.get_name() for s in ['CrownFern','Kiokio'])):continue
   ts=[]
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);s=t.scale3d;t.scale3d=u.Vector(s.x*xy/oldxy,s.y*xy/oldxy,s.z*z/oldz);ts.append(t)
   assert c.batch_update_instances_transforms(0,ts,True,True,True)
  owner.tags=[u.Name(t) for t in tags if not t.startswith(key)]+[u.Name(key+str(xy)+','+str(z))]
 report['shape_controls']=dict(canopy_width=cfg.get('canopy_width_scale',.86),fern_width=cfg.get('fern_width_scale',.88),fern_height=cfg.get('fern_height_scale',.62))

def far_finish(mat):
 if not mat.get_name().startswith('M_FirFar_'):return
 if not any(str(n.get_editor_property('desc'))=='FloraFarCrownDepth' for n in M.get_material_expressions(mat)):
  g=Graph(mat,'FloraFarCrownDepth');src=M.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR);out=str(M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR))
  uv=g.node(u.MaterialExpressionTextureCoordinate)
  n=g.custom(['Base','UV'],'float top=step(.6666,UV.x);float crown=lerp(lerp(.48,1.06,smoothstep(.40,.95,UV.y)),.90,top);return Base*crown;')
  g.wire(src,n,'Base',out);g.wire(uv,n,'UV');g.output(n,u.MaterialProperty.MP_BASE_COLOR)
 for node in M.get_material_expressions(mat):
  if isinstance(node,u.MaterialExpressionCustom) and str(node.get_editor_property('desc'))=='FloraFarCrownDepth':node.set_editor_property('code','float top=step(.75,UV.x);float crown=lerp(lerp(.48,1.06,smoothstep(.40,.95,1-UV.y)),.90,top);return Base*crown;')
 # Avoid a stippled far canopy in the cheap six-triangle tier.
 props(mat,dithered_lod_transition=False)

def fern_cover(rows,cfg):
 """Keep every established low-fern position, using the painted pack fronds."""
 existing=next((a for a in rows if a.get_actor_label()==PREFIX+'FernCover'),None)
 if existing and STAGE in ('refine','polish'):
  report['painted_ferns']=sum(c.get_instance_count() for c in existing.get_components_by_class(u.InstancedStaticMeshComponent));return
 for a in list(rows):
  if a.get_actor_label()==PREFIX+'FernCover':A.destroy_actor(a)
 owner=spawn('FernCover');old=next(a for a in rows if a.get_actor_label()=='LidarStudy_Understory')
 g=GroundSampler(next(a for a in rows if isinstance(a,u.GTProceduralGround)));rng=random.Random(cfg['seed']+93);cache={};buckets={0:[],1:[],2:[]}
 meshes=[u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_'+n) for n in ['Ferns_021','Ferns_025','Ferns_033']];assert all(meshes)
 for c in old.get_components_by_class(u.InstancedStaticMeshComponent):
  if not c.static_mesh or not any(s in c.static_mesh.get_name() for s in ['CrownFern','Kiokio']):continue
  bounds=c.static_mesh.get_bounds()
  for i in range(c.get_instance_count()):
   t=c.get_instance_transform(i,True);p=t.translation;k=rng.randrange(3);b=meshes[k].get_bounds()
   width=max(95,min(185,2*max(bounds.box_extent.x*t.scale3d.x,bounds.box_extent.y*t.scale3d.y)))
   sc=width/(2*max(b.box_extent.x,b.box_extent.y));z=g.height(p.x,p.y)-3
   buckets[k].append(u.Transform(location=u.Vector(p.x,p.y,z),rotation=t.rotation.rotator(),scale=u.Vector(sc,sc,sc)))
  c.set_visibility(False);c.set_hidden_in_game(True);c.set_cast_shadow(False)
 for k,ts in buckets.items():
  mesh=meshes[k];c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'FloraWorldFerns','NoCollision',True)
  c.set_cull_distances(6500,11000);props(c,visible_in_ray_tracing=False,cast_contact_shadow=True,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  for i,slot in enumerate(mesh.static_materials):
   if slot.material_interface:c.set_material(i,tint_material(slot.material_interface,cache,[.92,1.,.87]))
 report['painted_ferns']=sum(map(len,buckets.values()));assert report['painted_ferns']>139000

def accent_finish(mat):
 if 'Shrubbery' not in mat.get_name():return
 tag='FloraWorldWarmAccent';nodes=[n for n in M.get_material_expressions(mat) if str(n.get_editor_property('desc'))==tag]
 if not nodes:
  src=M.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR);out=str(M.get_material_property_input_node_output_name(mat,u.MaterialProperty.MP_BASE_COLOR));g=Graph(mat,tag)
  n=g.custom(['Base','Colour','Strength'],'float lum=dot(Base,float3(.2126,.7152,.0722));float3 warm=Colour*lum/max(.01,dot(Colour,float3(.2126,.7152,.0722)));return lerp(Base,warm,saturate(Strength));')
  g.wire(src,n,'Base',out);g.wire(g.node(u.MaterialExpressionVectorParameter,parameter_name='MapAccentColour',default_value=u.LinearColor(.45,.16,.07,1)),n,'Colour');g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='MapAccentStrength',default_value=.65),n,'Strength');g.output(n,u.MaterialProperty.MP_BASE_COLOR)

def interactive_grass(rows,cfg):
 """Keep the native streaming/contact host; replace only clump art/materials.

Custom floats 0/1/2 are the host's root-height/bent/removed contract, also used
by woodland_native_grass.WIND. Rank grass remains unindexed, as before.
"""
 cache={}
 def material(src):
  key=path(src)
  if key in cache:return cache[key]
  dst=D+'/InteractiveGrass/'+src.get_name();m=u.load_asset(dst) or E.duplicate_asset(key,dst);cache[key]=m
  if isinstance(m,u.MaterialInstanceConstant):M.set_material_instance_parent(m,material(src.get_editor_property('parent')))
  else:
   tag='FloraNativeGrassContact'
   if not any(str(n.get_editor_property('desc'))==tag for n in M.get_material_expressions(m)):
    g=Graph(m,tag);old=M.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);out=str(M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET));old=old or g.vector((0,0,0))
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    n=g.custom(['Old','P','Root','Bend','Removed'],'''float h=max(0,(P.z+Old.z-Root)*.01);
float strength=saturate((h-.1)*2.5)*saturate(Bend)*saturate(h);
float3 contact=float3(.7,.3,-.8)*strength*100;
return Removed>.5 ? float3(0,0,-100000) : Old+contact;''')
    g.wire(old,n,'Old',out);g.wire(p,n,'P')
    for key,index in [('Root',0),('Bend',1),('Removed',2)]:g.wire(g.node(u.MaterialExpressionPerInstanceCustomData,data_index=index),n,key)
    g.output(n,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
   for node in M.get_material_expressions(m):
    if isinstance(node,u.MaterialExpressionVectorParameter) and str(node.get_editor_property('parameter_name'))=='MapFoliageTint':node.set_editor_property('default_value',u.LinearColor(.98,.94,.78,1))
   grass_cores(m);M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not M.recompile_material(m)
  assert E.save_loaded_asset(m,False);return m
 models=[u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_'+n) for n in ['Grass_005','Grass_013','Grass_016']];rank=u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_Dry_Grass_014');assert all(models) and rank
 shared=material(u.load_asset(D+'/Foliage/MI_Path_Grass_003'))
 ranksource=F.clone_material(rank.static_materials[0].material_interface,{})
 rankmat=material(ranksource)
 report['interactive_grass']=[]
 for a in rows:
  if isinstance(a,u.GTMixedGroundDetails):
   a.pasture_clump_mesh=models[0];a.pasture_clump_mesh_b=models[1];a.pasture_clump_mesh_c=models[2];a.rank_clump_mesh=rank;a.grass_material=shared;a.rank_material=rankmat
   # Same 65cm planting lattice and native contact host; source clumps are 38–42 triangles.
   report['interactive_grass'].append(dict(actor=a.get_actor_label(),material=path(shared),models=[path(m) for m in models],rank=path(rank),spacing=a.clump_spacing_cm))

def grass_cores(m):
 tag='FloraGrassRockCores'
 if any(str(n.get_editor_property('desc'))==tag for n in M.get_material_expressions(m)):return
 import lidar_logging_trial as T
 route=T.route(json.loads((R/'Art/Export/LidarStudy/Place/roads.json').read_text()));pilot=json.loads((R/'Art/Export/LidarStudy/FloraIntegration/profile.json').read_text())
 code='float cover=1.;\n'
 for rock in pilot['outcrops']:
  x,y,_=T.at(route,rock['station'],rock['across']);radius=rock['width_cm']*.42
  code+='cover*=smoothstep({:.3f},{:.3f},distance(P.xy,float2({:.5f},{:.5f})));\n'.format(radius-35,radius,x,y)
 code+='return Mask*cover;'
 g=Graph(m,tag);old=M.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK);port=str(M.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK));assert old
 node=g.custom(['P','Mask'],code,u.CustomMaterialOutputType.CMOT_FLOAT1);g.wire(g.node(u.MaterialExpressionWorldPosition),node,'P');g.wire(old,node,'Mask',port);g.output(node,u.MaterialProperty.MP_OPACITY_MASK)

def woodland_midstory(rows,cfg):
 """Source-pack saplings replace the remaining sharp legacy tree-fern tier.
 Low fern coverage and every original midstory planting position are retained.
 """
 old=next(a for a in rows if a.get_actor_label()=='LidarStudy_Understory')
 from flora_world_finish import debris_material
 wood=debris_material()
 for c in old.get_components_by_class(u.InstancedStaticMeshComponent):
  if c.static_mesh and any(s in c.static_mesh.get_name() for s in ['Log_','Stump_','RootTangle_']):
   for i in range(c.get_num_materials()):c.set_material(i,wood)
 existing=next((a for a in rows if a.get_actor_label()==PREFIX+'Midstory'),None)
 if existing:
  report['sapling_count']=sum(c.get_instance_count() for c in existing.get_components_by_class(u.InstancedStaticMeshComponent));return
 owner=spawn('Midstory');rng=random.Random(cfg['seed']+49);groups={0:[],1:[],2:[]}
 canopy=next(a for a in rows if a.get_actor_label()==PREFIX+'Canopy');prototypes={int(c.static_mesh.get_name().rsplit('_',1)[1]):c for c in canopy.get_components_by_class(u.InstancedStaticMeshComponent)}
 originals=[u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_'+n) for n in ['Tree_B_001','Tree_D_003','Tree_B_002']]
 for c in old.get_components_by_class(u.InstancedStaticMeshComponent):
  if not c.static_mesh or 'TreeFern' not in c.static_mesh.get_name():continue
  b=c.static_mesh.get_bounds()
  for i in range(c.get_instance_count()):
   t=c.get_instance_transform(i,True);k=rng.randrange(3);s=max(350.,min(800.,b.box_extent.z*2*t.scale3d.z))/(originals[k].get_bounds().box_extent.z*2)
   t.scale3d=u.Vector(s*.85,s*.85,s);groups[k].append(t)
  c.set_visibility(False);c.set_hidden_in_game(True);c.set_cast_shadow(False)
 for k,ts in groups.items():
  proto=prototypes[k];c=u.GTVegetationSubsystem.add_tagged_instances(owner,proto.static_mesh,ts,'FloraWorldSaplings','NoCollision',True)
  props(c,override_min_lod=True,min_lod=2,visible_in_ray_tracing=False,affect_distance_field_lighting=False,cast_contact_shadow=True,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID);c.set_cull_distances(20000,35000)
  for i,mat in enumerate(proto.get_materials()):c.set_material(i,mat)
 report['sapling_count']=sum(map(len,groups.values()))

def install(rows,cfg):
 before=protected(rows);report['protected_before']=before
 # Old generated components stay recoverable but do not render alongside replacements.
 old=next(a for a in rows if a.get_actor_label()=='LidarStudy_Forest');source=[]
 for c in old.get_components_by_class(u.InstancedStaticMeshComponent):
  if c.static_mesh and c.static_mesh.get_name().startswith('SM_CD_Canopy'):
   b=c.static_mesh.get_bounds()
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True);source.append((t,b.box_extent.z*2*t.scale3d.z))
   c.set_visibility(False);c.set_hidden_in_game(True);c.set_cast_shadow(False)
 # Existing pilot trees join the same global treatment; preserve its plants/rocks/collision.
 for a in rows:
  if a.get_actor_label()=='LidarStudy_FloraIntegration_Vegetation':
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if c.static_mesh and '_Tree_' in c.static_mesh.get_name():
     b=c.static_mesh.get_bounds()
     for i in range(c.get_instance_count()):
      t=c.get_instance_transform(i,True);source.append((t,b.box_extent.z*2*t.scale3d.z))
     c.set_visibility(False);c.set_hidden_in_game(True);c.set_cast_shadow(False)
 for a in list(rows):
  if a.get_actor_label().startswith(PREFIX):A.destroy_actor(a)
 owner=spawn('Canopy');rng=random.Random(cfg['seed']);buckets={0:[],1:[],2:[]};cache={}
 meshes=[u.load_asset(D+'/Canopy/SM_Canopy_'+str(k)) for k in range(3)];assert all(meshes)
 # Use source geometry bounds, not enlarged billboard bounds, to preserve tree stature.
 originals=[u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_'+n) for n in ['Tree_B_001','Tree_D_003','Tree_B_002']]
 for t,h in source:
  p=t.translation;patch=math.sin(p.x/11500)+math.cos(p.y/13000)
  k=(0 if patch>.15 else 1) if rng.random()<.82 else 2
  b=originals[k].get_bounds();height=max(cfg['tree_min_height_cm'],min(cfg['tree_max_height_cm'],h))
  s=height/(b.box_extent.z*2);z=p.z-min(0,b.origin.z-b.box_extent.z)*s
  buckets[k].append(u.Transform(location=u.Vector(p.x,p.y,z),rotation=t.rotation.rotator(),scale=u.Vector(s,s,s)))
 counts={}
 for k,ts in buckets.items():
  mesh=meshes[k]
  assert u.get_editor_subsystem(u.StaticMeshEditorSubsystem).set_lod_screen_sizes(mesh,[1.,.65,.28,.14]);E.save_loaded_asset(mesh,False)
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'FloraWorldCanopy','NoCollision',True)
  props(c,override_min_lod=True,min_lod=cfg['tree_min_lod'],visible_in_ray_tracing=False,affect_distance_field_lighting=False,cast_contact_shadow=True,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  c.set_cull_distances(0,0)
  for i,slot in enumerate(mesh.static_materials):
   if slot.material_interface:
    mat=slot.material_interface
    # Far material is already map-owned; all other source materials get a local clone.
    local=tint_material(mat,cache,cfg['bark_tint'] if any(s in mat.get_name() for s in ['Bark','Wood']) else cfg['foliage_tint']);c.set_material(i,local)
  counts[str(k)]=len(ts)
 report['tree_counts']=counts;report['total_trees']=sum(counts.values());assert report['total_trees']>140000
 # Keep low native ferns/grass; plant source-pack grasses and low shrubs between them.
 author=next(a for a in rows if isinstance(a,u.GTProceduralGround));g=GroundSampler(author)
 under=next(a for a in rows if a.get_actor_label()=='LidarStudy_Understory');plants={};anchors=[]
 for c in under.get_components_by_class(u.InstancedStaticMeshComponent):
  if not c.static_mesh:continue
  n=c.static_mesh.get_name()
  if any(s in n for s in ['CrownFern','Kiokio']):
   for i in range(0,c.get_instance_count(),cfg['plant_anchor_stride']):anchors.append(c.get_instance_transform(i,True).translation)
   c.set_cast_shadow(True);props(c,cast_contact_shadow=True)
   for i,mat in enumerate(c.get_materials()):
    if mat:c.set_material(i,tint_material(mat,cache,cfg['native_fern_tint']))
 # Long grass, fine grass, broad leaves and coral flowering accents, in coherent clumps.
 names=['Grass_003','Grass_005','Grass_013','Grass_016','Grass_020','Blooming_Grass_008','Blooming_Grass_012','Small_Plants_006','Small_Plants_013','Blooming_Shrubbery_006','Blooming_Shrubbery_009']
 models={n:u.load_asset('/Game/GrandTour/ArtTests/FloraPath/SM_Path_FP_'+n) for n in names};assert all(models.values())
 for i,p in enumerate(anchors):
  for j in range(cfg['plant_group_size']):
   n=names[(i//7+j)%7] if j<3 else names[7+(i//11)%4]
   mesh=models[n];b=mesh.get_bounds();x=p.x+rng.uniform(-110,110);y=p.y+rng.uniform(-110,110)
   z=g.height(x,y);slope=math.hypot(g.height(x+45,y)-g.height(x-45,y),g.height(x,y+45)-g.height(x,y-45))/90
   if slope>.9:continue
   s=rng.uniform(35,70)/(2*b.box_extent.z)
   if 'Small_Plants' in n:s=rng.uniform(45,85)/(2*max(b.box_extent.x,b.box_extent.y))
   plants.setdefault(n,[]).append(u.Transform(location=u.Vector(x,y,z-max(0,b.origin.z-b.box_extent.z)*s-3),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(s,s,s)))
 plantowner=spawn('Understory');report['plant_counts']={}
 for n,ts in plants.items():
  mesh=models[n];shadow=any(s in n for s in ['Small_Plants','Shrubbery'])
  c=u.GTVegetationSubsystem.add_tagged_instances(plantowner,mesh,ts,'FloraWorldUnderstory','NoCollision',shadow)
  c.set_cull_distances(cfg['plant_cull_start_cm'],cfg['plant_cull_end_cm']);props(c,visible_in_ray_tracing=False,cast_contact_shadow=True,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  for i,slot in enumerate(mesh.static_materials):
   if slot.material_interface:c.set_material(i,tint_material(slot.material_interface,cache,cfg['foliage_tint']))
  report['plant_counts'][n]=len(ts)
 report['retained_native_ferns']=sum(c.get_instance_count() for c in under.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and any(s in c.static_mesh.get_name() for s in ['CrownFern','Kiokio']))
 # Replace the old rounded hummock appearance across the forest with the purchased
 # sculpted rock kit. Original collision components are retained independently.
 rockdata=json.loads((R/'Art/Export/FloraDrive/RockMaster/export-report.json').read_text())['meshes']
 rockowner=spawn('Rocks');rockbuckets={};rockmodels={}
 for c in under.get_components_by_class(u.InstancedStaticMeshComponent):
  if not c.static_mesh or 'MossHummock' not in c.static_mesh.get_name():continue
  oldbounds=c.static_mesh.get_bounds()
  for i in range(c.get_instance_count()):
   t=c.get_instance_transform(i,True);k=(i//5)%len(rockdata)
   if k not in rockmodels:rockmodels[k]=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/RockMaster/'+rockdata[k]['mesh'])
   mesh=rockmodels[k];b=mesh.get_bounds();width=2*max(oldbounds.box_extent.x*t.scale3d.x,oldbounds.box_extent.y*t.scale3d.y)
   sc=width/(2*max(b.box_extent.x,b.box_extent.y));p=t.translation
   tf=g.seat(mesh,u.Transform(location=u.Vector(p.x,p.y,p.z),rotation=t.rotation.rotator(),scale=u.Vector(sc,sc,sc)),False)
   q=tf.translation;tf.translation=u.Vector(q.x,q.y,q.z-b.box_extent.z*sc*.35)
   rockbuckets.setdefault(k,[]).append(tf)
  c.set_visibility(False);c.set_hidden_in_game(True);c.set_cast_shadow(False)
 report['rock_counts']={}
 for k,ts in rockbuckets.items():
  mesh=rockmodels[k];c=u.GTVegetationSubsystem.add_tagged_instances(rockowner,mesh,ts,'FloraWorldRocks','NoCollision',True)
  c.set_cull_distances(20000,35000);props(c,visible_in_ray_tracing=False,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  for i,slot in enumerate(mesh.static_materials):
   if slot.material_interface:c.set_material(i,tint_material(slot.material_interface,cache,[.90,.98,.93]))
  report['rock_counts'][mesh.get_name()]=len(ts)
 # Ground grain/POM everywhere, with a close-range early-out. Native WPO unchanged.
 import lidar_logging_trial as T
 route=T.route(json.loads((R/'Art/Export/LidarStudy/Place/roads.json').read_text()));mapping={}
 import re
 for role in ['Terrain','Detail']:
  src=u.load_asset(BASE+'/FloraIntegration/M_Flora'+role)
  m=u.load_asset(D+'/M_Flora'+role) or E.duplicate_asset(path(src),D+'/M_Flora'+role)
  for n in M.get_material_expressions(m):
   if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='LidarFloraDetail':
    code=str(n.get_editor_property('code'));code=re.sub(r'float distanceRoad=1e12;.*?(?=float cover=)','float distanceRoad=1000.;\n',code,flags=re.S)
    code=code.replace('float cover=1-smoothstep(DetailWidthCm-350,DetailWidthCm,distanceRoad);','float cover=1.;')
    n.set_editor_property('code',code)
   if isinstance(n,u.MaterialExpressionScalarParameter):
    key=str(n.get_editor_property('parameter_name'))
    if key in cfg['ground']:n.set_editor_property('default_value',cfg['ground'][key])
  for pin in [u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK]:
   a=M.get_material_property_input_node(src,pin);b=M.get_material_property_input_node(m,pin);assert (a.get_name() if a else None)==(b.get_name() if b else None)
  assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
  mapping[src]=m;mapping[u.load_asset(BASE+'/CohesiveStyle/M_Evergreen'+role)]=m
 for a in A.get_all_level_actors():
  if isinstance(a,u.LandscapeProxy) and a.landscape_material in mapping:a.landscape_material=mapping[a.landscape_material]
  if isinstance(a,u.GTProceduralGround) and a.relief_material in mapping:a.relief_material=mapping[a.relief_material]
  if isinstance(a,u.GTMudRunnerVisual) and a.material in mapping:a.material=mapping[a.material]
  for c in a.get_components_by_class(u.MeshComponent):
   for i,mat in enumerate(c.get_materials()):
    if mat in mapping:c.set_material(i,mapping[mat])
 refine_shapes(A.get_all_level_actors(),cfg);fern_cover(A.get_all_level_actors(),cfg);style(A.get_all_level_actors(),cfg);interactive_grass(A.get_all_level_actors(),cfg);woodland_midstory(A.get_all_level_actors(),cfg)
 report['protected_after']=protected(A.get_all_level_actors());assert before==report['protected_after']
 assert L.save_current_level();report['saved_map_sha256']=sha(R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap')

def verify(rows):
 expected=json.loads((O/'install-report.json').read_text());assert expected['ok'];report['protected']=protected(rows);assert report['protected']==expected['protected_before'],(report['protected'],expected['protected_before'])
 owner=next(a for a in rows if a.get_actor_label()==PREFIX+'Canopy');assert sum(c.get_instance_count() for c in owner.get_components_by_class(u.InstancedStaticMeshComponent))==expected['total_trees']
 report['tree_count_verified']=expected['total_trees']
 under=next(a for a in rows if a.get_actor_label()=='LidarStudy_Understory')
 count=sum(c.get_instance_count() for c in under.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and any(s in c.static_mesh.get_name() for s in ['CrownFern','Kiokio']))
 assert count==expected['retained_native_ferns'];report['retained_native_ferns']=count
 fernowner=next(a for a in rows if a.get_actor_label()==PREFIX+'FernCover');painted=sum(c.get_instance_count() for c in fernowner.get_components_by_class(u.InstancedStaticMeshComponent));assert painted==count;report['painted_fern_positions_preserved']=painted
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);report['canopy_lods']=[]
 for k in range(3):
   mesh=u.load_asset(D+'/Canopy/SM_Canopy_'+str(k));assert sm.get_lod_count(mesh)==4 and mesh.get_static_mesh_description(3).get_triangle_count()==8
   report['canopy_lods'].append(dict(mesh=path(mesh),far_triangles=8,screens=list(sm.get_lod_screen_sizes(mesh))))
 v=next(a for a in rows if isinstance(a,u.GTMudRunnerVisual));assert path(v.material)==D+'/M_FloraDetail'
 for role in ['Terrain','Detail']:
  mat=u.load_asset(D+'/M_Flora'+role);src=u.load_asset(BASE+'/FloraIntegration/M_Flora'+role)
  for pin in [u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.MaterialProperty.MP_OPACITY_MASK]:
   a=M.get_material_property_input_node(src,pin);b=M.get_material_property_input_node(mat,pin);assert (a.get_name() if a else None)==(b.get_name() if b else None)
 report['native_displacement_connections_unchanged']=True
 mid=next(a for a in rows if a.get_actor_label()==PREFIX+'Midstory');report['sapling_count']=sum(c.get_instance_count() for c in mid.get_components_by_class(u.InstancedStaticMeshComponent));assert report['sapling_count']==13030
 for k in range(3):
  for prefix in ['T_FirAtlas_','T_FirNormal_']:
   tex=u.load_asset(D+'/Canopy/'+prefix+str(k));assert tex.power_of_two_mode==u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO and tex.mip_gen_settings==u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE
 report['distant_atlas_filtering_verified']=True
 for a in rows:
  if isinstance(a,u.GTMixedGroundDetails):
   assert path(a.grass_material).startswith(D+'/InteractiveGrass/')
   mat=a.grass_material.get_editor_property('parent');node=M.get_material_property_input_node(mat,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
   assert str(node.get_editor_property('desc'))=='FloraNativeGrassContact'
   indices=sorted(n.get_editor_property('data_index') for n in M.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionPerInstanceCustomData))
   assert all(i in indices for i in [0,1,2]);report['native_grass_contact_inputs_verified']=indices
 report['ok']=True

def main():
 if not CFG.exists():CFG.write_text(json.dumps(DEFAULT,indent=2))
 if STAGE=='grassmaterials':
  report['canopy_texture_mips']=[]
  for k in range(3):
   for prefix in ['T_FirAtlas_','T_FirNormal_']:
    tex=u.load_asset(D+'/Canopy/'+prefix+str(k));assert tex
    props(tex,power_of_two_mode=u.TexturePowerOfTwoSetting.STRETCH_TO_POWER_OF_TWO,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,filter=u.TextureFilter.TF_TRILINEAR)
    if prefix=='T_FirAtlas_':props(tex,do_scale_mips_for_alpha_coverage=True,alpha_coverage_thresholds=u.Vector4(0,0,0,.35))
    assert E.save_loaded_asset(tex,False);report['canopy_texture_mips'].append(path(tex))
  for assetpath in E.list_assets(D+'/InteractiveGrass',True,False):
   mat=u.load_asset(assetpath)
   if isinstance(mat,u.Material):grass_cores(mat);assert not M.recompile_material(mat);assert E.save_loaded_asset(mat,False)
  report['ok']=True;return
 cfg=json.loads(CFG.read_text());assert L.load_level(BASE+'/L_LidarStudy');rows=A.get_all_level_actors()
 if STAGE=='audit':report.update(audit(rows));backup()
 elif STAGE=='install':backup();install(rows,cfg)
 elif STAGE in ('refine','polish'):
  before=protected(rows);style(rows,cfg);refine_shapes(rows,cfg);fern_cover(rows,cfg);interactive_grass(rows,cfg);woodland_midstory(rows,cfg)
  report['instancing_materials_saved']=[]
  for assetpath in E.list_assets(D+'/Foliage',True,False):
   mat=u.load_asset(assetpath)
   if isinstance(mat,u.Material):
    name=mat.get_name();colour=cfg['bark_tint'] if any(s in name for s in ['Bark','Wood']) else cfg['native_fern_tint'] if name=='M_LP6_Foliage' else [.92,1.,.87] if 'Fern_1' in name else [1.,1.,1.] if 'Flower' in name else [.90,.98,.93] if 'SM_RM' in name else cfg['foliage_tint']
    for node in M.get_material_expressions(mat):
     if isinstance(node,u.MaterialExpressionVectorParameter) and str(node.get_editor_property('parameter_name'))=='MapFoliageTint':node.set_editor_property('default_value',u.LinearColor(*colour,1))
    far_finish(mat);accent_finish(mat)
    if name.startswith(('M_FirFar_','M_Path_Leaf_')):
     import canopy_surface_shadows as shadows
     shadows.wrap(mat)
     for node in M.get_material_expressions(mat):
      if isinstance(node,u.MaterialExpressionCustom) and str(node.get_editor_property('desc'))=='CanopySurfaceShadow':node.set_editor_property('code',str(node.get_editor_property('code')).replace('light,fade);','light,fade*.55);'))
    M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);assert not M.recompile_material(mat);assert E.save_loaded_asset(mat,False);report['instancing_materials_saved'].append(path(mat))
  if STAGE=='polish':
   from flora_world_finish import shape_material,plant_pigment,coherent_transmission,crown_volume
   import flora_world_art_direction as art_direction
   report['reference_polish_materials']=[]
   report['art_direction_materials']=[]
   for folder in ['Foliage','InteractiveGrass']:
    for assetpath in E.list_assets(D+'/'+folder,True,False):
     mat=u.load_asset(assetpath)
     if isinstance(mat,u.Material):
      shape_material(mat);plant_pigment(mat);coherent_transmission(mat);crown_volume(mat)
      if cfg.get('art_direction',{}).get('enabled',False):
       treatment=art_direction.install(mat,cfg['art_direction'])
       if treatment:report['art_direction_materials'].append(dict(material=path(mat),treatment=treatment))
      assert not M.recompile_material(mat);assert E.save_loaded_asset(mat,False)
      report['reference_polish_materials'].append(path(mat))
     elif isinstance(mat,u.MaterialInstanceConstant):
      for key,value in [('NormalUpBlend',.28 if 'Leaf' in mat.get_name() else .18),('Transmission',.32 if 'Leaf' in mat.get_name() else .42)]:M.set_material_instance_scalar_parameter_value(mat,key,value)
      assert E.save_loaded_asset(mat,False)
  assert before==protected(rows);assert L.save_current_level();report['saved_map_sha256']=sha(R/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap')
 else:verify(rows)
 report['ok']=True
if __name__=='__main__':
 try:main()
 except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
 (O/(STAGE+'-report.json')).write_text(json.dumps(report,indent=2));gc.collect();L.load_level('/Engine/Maps/Entry');gc.collect()
 state={'end':time.monotonic()+3}
 def finish(dt):
  if time.monotonic()>state['end']:u.unregister_slate_post_tick_callback(state['handle']);u.SystemLibrary.quit_editor()
 u.EditorPythonScripting.set_keep_python_script_alive(True);state['handle']=u.register_slate_post_tick_callback(finish)
