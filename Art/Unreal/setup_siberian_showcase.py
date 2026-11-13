"""Build an isolated, playable showcase from the accepted MudRoad lighting/effects."""
import unreal as u
import sys,json,time,traceback,math,random,hashlib,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path[:0]=[str(ROOT/'Art/Unreal'),str(ROOT/'Art/tools')]
from benmore_river_life_materials import props,Graph
from make_siberian_showcase import ground,masks,road_distance,river_y,pond_q,ROAD,SHORT
import siberian_surface_repairs as repairs
BASE='/Game/GrandTour/ArtTests/SiberianShowcase';OLD='/Game/GrandTour/ArtTests/MudRoad';OUT=ROOT/'Art/Export/SiberianShowcase';LEVEL=BASE+'/L_SiberianShowcase'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
report=dict(ok=False,level=LEVEL);data=json.loads((OUT/'authoring.json').read_text())
def spawn(cls,label,pos=(0,0,0),rot=None):
 a=actors.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label('Taiga_'+label);return a
def texture(tile,name):
 path=BASE+'/'+tile;task=props(u.AssetImportTask(),filename=str(OUT/tile/(name+'.png')),destination_path=path,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=assets.load_asset(path+'/T_'+name);assert t
 props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True);assets.save_loaded_asset(t);return t
def material(source,tile,name,textures,origin):
 path=BASE+'/'+tile+'/'+name;m=assets.load_asset(path) or assets.duplicate_asset(source,path);assert m
 for e in mel.get_material_expressions(m):
  if isinstance(e,u.MaterialExpressionTextureObjectParameter):
   key=str(e.get_editor_property('parameter_name'))
   if key in ['GTLS_Paint','GTLS_Rest']:e.set_editor_property('texture',textures[key.split('_')[1].lower()])
  elif isinstance(e,u.MaterialExpressionTextureObject):
   t=e.get_editor_property('texture')
   if t and t.get_name() in ['T_style','T_macro']:e.set_editor_property('texture',textures[t.get_name()[2:]])
  if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(*origin,6300,0))
 return repairs.repair(m,name)
def region(label,x,y,hx,hy,grass=0,sand=False,wet=.85,ellipse=False):
 return props(u.GTLandscapeMudRegion(),name=label,centre=u.Vector2D(x,y),half_size=u.Vector2D(hx,hy),grass_cover=grass,granular=sand,wetness=wet,cohesion=.12 if sand else .52,relief=.15 if sand or grass else 1.,fragment_scale=1.,elliptical=ellipse)
try:
 source=ROOT/'Content/GrandTour/ArtTests/MudRoad/L_MudRoad.umap';before=hashlib.sha256(source.read_bytes()).hexdigest()
 target=ROOT/'Content/GrandTour/ArtTests/SiberianShowcase'
 if target.exists():shutil.copytree(target,ROOT/'Saved/SiberianShowcaseBackups'/str(time.time_ns()))
 if assets.does_asset_exist(LEVEL):assert les.load_level(LEVEL)
 else:
  assert les.load_level(OLD+'/L_MudRoad')
  world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL);assert les.load_level(LEVEL)
 # Retain the accepted native particle actor and scene lighting/grade only.
 keep=(u.WorldSettings,u.DirectionalLight,u.SkyLight,u.SkyAtmosphere,u.ExponentialHeightFog,u.PostProcessVolume,u.GTMudRunnerWheelEffects)
 report['retained']=[]
 for a in list(actors.get_all_level_actors()):
  if isinstance(a,keep) or 'SkySphere' in a.get_class().get_name():report['retained'].append(a.get_actor_label())
  elif a.get_class().get_name() not in ['LevelScriptActor','Brush']:actors.destroy_actor(a)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',u.GTMudLabGameMode)
 rng=random.Random(9640861);report['tiles']=[];surfaces={};visuals={}
 native_soil=OLD+'/MixedSurfaces/M_RoadNativeSoil';native_track=OLD+'/MixedSurfaces/M_NativeTread'
 grassmesh=assets.load_asset(OLD+'/MixedSurfaces/SM_NativeShortGrass');grassmat=repairs.grass(OLD+'/MixedSurfaces/M_NativeGrassRich',BASE+'/M_Grass');assert grassmesh and grassmat
 for tile in data['tiles']:
  name=tile['name'];ox,oy=tile['origin'];cx,cy=ox+3150,oy+3150;textures={n:texture(name,n) for n in ['paint','rest','style','macro']}
  soil=material(native_soil,name,'M_Soil',textures,[ox,oy]);track=material(native_track,name,'M_Tread',textures,[ox,oy])
  land=u.GTLandscapeSurfaceSetupLibrary.create_study_landscape(world,soil,u.Vector(ox,oy,0),tile['heights_cm']);assert land;land.set_actor_label('Taiga_'+name+'_Landscape')
  s=spawn(u.GTLandscapeSurface,name+'_Surface',(cx,cy,0));s.landscape=land
  props(s,paint_origin_cm=u.Vector2D(ox,oy),paint_size_cm=6300.,enable_wheel_support=True,observe_player_wheels=True,follow_player=True,use_soil_shear_response=True,use_rut_interaction=True,use_native_mud_shader_updates=tile['native'],use_native_substance_response=tile['native'],use_native_water_response=True)
  s.set_editor_property('layer_depth_scale',2.48);s.maximum_layer_depth_cm=124.
  assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,textures['paint']);assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(s,textures['rest'])
  regions=[]
  if oy==0:
   for x in range(ox+200,ox+6300,350):regions.append(region('Wet river sand',x,float(river_y(x)),210,920,sand=True,wet=.65))
   regions.append(region('Upper pond shore',3900,4500,1450,1150,sand=True,wet=.65,ellipse=True))
  regions.extend([region('Deep bog',2300,-2070,1500,1050,wet=.96,ellipse=True),region('Forest pond mud',-2500,-900,1500,1100,wet=.94,ellipse=True)])
  for x,y in ROAD+SHORT:regions.append(region('Forest track',x,y,310,310,wet=.7,ellipse=True))
  regions.append(region('Forest sod',cx,cy,3150,3150,grass=1,wet=.32));s.mud_regions=regions
  v=spawn(u.GTMudRunnerVisual,name+'_Visual',(cx,cy,0));props(v,surface=s,material=soil,track_material=track)
  if tile['water_level'] is not None:
   wm=material(OLD+'/M_LabWater',name,'M_Water',textures,[ox,oy]);sim=material(OLD+'/M_LabWaterSim',name,'M_WaterSim',textures,[ox,oy]);sed=material(OLD+'/M_LabWaterSediment',name,'M_Sediment',textures,[ox,oy])
   px,py,half=(3900,4500,1500.) if name=='NE' else (cx,cy,3150.)
   w=spawn(u.GTWaterSheet,name+'_PondAndPools',(px,py,tile['water_level']));w.get_component_by_class(u.StaticMeshComponent).set_static_mesh(assets.load_asset('/Engine/BasicShapes/Cube'));w.set_actor_scale3d(u.Vector(half/50,half/50,.1))
   props(w,mud_surface=s,mud_half_size_cm=half,mud_cell_cm=50.,base_level_cm=tile['water_level'],build_sleeping_mud_basin=True,continuous_shore_rendering=True,surface_material_path=BASE+'/'+name+'/M_Water');s.set_editor_property('simulated_water',w)
   props(v,water_sheet=w,water_simulation_material=sim,sediment_simulation_material=sed,wave_material=assets.load_asset('/Game/GrandTour/ArtTests/MudLab/M_LabWaves'))
  details=spawn(u.GTMixedGroundDetails,name+'_Grass');details.surface=s;details.grass_material=grassmat;details.grass.set_static_mesh(grassmesh);details.grass.set_material(0,grassmat)
  ts=[]
  for yy in range(oy+30,oy+6270,32):
   for xx in range(ox+30,ox+6270,32):
    x,y=xx+rng.uniform(-15,15),yy+rng.uniform(-15,15);sand,g,_,_,_=masks(x,y);z=float(ground(x,y))
    if g<.20 or rng.random()>min(1.,g*1.7) or z<40 or (name=='NE' and z<162 and pond_q(x,y,3900,4500,1000,760)<2.0):continue
    sc=rng.uniform(1.0,1.55);ts.append(u.Transform(location=u.Vector(x,y,z-2),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,rng.uniform(.65,1.2))))
  details.grass.add_instances(ts,False,True);details.grass.set_cull_distances(2500,5500)
  details.grass.set_editor_property('visible_in_ray_tracing',False)
  surfaces[name]=s;visuals[name]=v;report['tiles'].append(dict(name=name,grass=len(ts),native_mud=tile['native'],height_range=tile['height_range_cm']))
 # One continuous river field crosses tile boundaries; the ford is shaped into its bed.
 river=spawn(u.GTWaterSheet,'River',(0,1450,.1));river.get_component_by_class(u.StaticMeshComponent).set_static_mesh(assets.load_asset('/Engine/BasicShapes/Cube'));river.set_actor_scale3d(u.Vector(200,40,.1))
 rm=assets.load_asset(BASE+'/M_River') or assets.duplicate_asset(OLD+'/MixedSurfaces/M_NativeRiver',BASE+'/M_River');repairs.repair(rm,'M_River')
 props(river,base_level_cm=.1,flow_direction=u.Vector2D(1,0),flow_speed_cm_per_s=45.,head_drop_cm=4.,field_cell_cm=50.,wind_ripple_cm=2.,use_authored_basin_seed=True,authored_basin_seed_cm=u.Vector2D(0,float(river_y(0))),continuous_shore_rendering=True,surface_material_path=BASE+'/M_River')
 # Dense, irregular fir stands with open banks and clear route sight lines.
 tree_actor=spawn(u.Actor,'Forest');report['trees']=0;trunks=[]
 treepaths=['/Game/OWGame/Dev/DressingLab/Trees/SM_OWFirTree','/Game/OWGame/Dev/DressingLab/Trees/SM_OWFir_TallSparse_A','/Game/OWGame/Dev/DressingLab/Trees/SM_OWFir_TallSparse_B']
 se=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
 for k,path in enumerate(treepaths):
  src=assets.load_asset(path);assert src
  mesh=assets.load_asset(BASE+'/SM_Fir_'+str(k)) or assets.duplicate_asset(path,BASE+'/SM_Fir_'+str(k));b=mesh.get_bounds();ts=[]
  # Trunk-only collision is built separately below; foliage remains visual.
  se.remove_collisions(mesh);assets.save_loaded_asset(mesh)
  for j in range(420):
   x,y=rng.uniform(-9800,9800),rng.uniform(-9800,9800);z=float(ground(x,y))
   if rng.random()>(.68+.32*math.sin(x/1600)*math.cos(y/1100)):continue
   if road_distance(x,y)<590 or z<55 or abs(y-float(river_y(x)))<950 or pond_q(x,y,-2500,-900,1350,1000)<1 or pond_q(x,y,3900,4500,1450,1100)<1 or pond_q(x,y,2300,-2070,1700,1250)<1:continue
   sc=rng.uniform(850,1550)/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*sc-8),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)))
   trunks.append(u.Transform(location=u.Vector(x,y,z+200),scale=u.Vector(.28,.28,4)))
  c=u.GTVegetationSubsystem.add_tagged_instances(tree_actor,mesh,ts,'TaigaForest','NoCollision',True);c.set_cull_distances(18000,24000);report['trees']+=len(ts)
 c=u.GTVegetationSubsystem.add_tagged_instances(tree_actor,assets.load_asset('/Engine/BasicShapes/Cylinder'),trunks,'TaigaTrunk','BlockAll',False);c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 # Low-cost surrounding hills conceal the edge of the deformable study.
 opts=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opts.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS)
 task=props(u.AssetImportTask(),filename=str(OUT/'surroundings.obj'),destination_path=BASE,destination_name='SM_Surroundings',automated=True,replace_existing=True,save=True,options=opts);u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=assets.load_asset(BASE+'/SM_Surroundings');assert mesh
 body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
 terrainmat=assets.load_asset(BASE+'/M_ForestFloor') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_ForestFloor',BASE,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(terrainmat);g=Graph(terrainmat)
 p=g.node(u.MaterialExpressionWorldPosition);uv=g.custom(['P'],'return P.xy/700;',u.CustomMaterialOutputType.CMOT_FLOAT2);g.wire(p,uv,'P')
 tex=g.node(u.MaterialExpressionTextureSample,texture=assets.load_asset('/Game/GrandTour/ArtTests/MudLab/NativeReference/T_tiles_grass__d_a'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);g.wire(uv,tex,'UVs')
 props(terrainmat,shading_model=u.MaterialShadingModel.MSM_UNLIT)
 col=g.custom(['C'],'return pow(max(C.rgb*float3(.48,.68,.24),0),2.2);');g.wire(tex,col,'C');g.output(col,u.MaterialProperty.MP_EMISSIVE_COLOR);mel.recompile_material(terrainmat);assets.save_loaded_asset(terrainmat);mesh.set_material(0,terrainmat);assets.save_loaded_asset(mesh)
 skirt=spawn(u.StaticMeshActor,'SurroundingHills');c=skirt.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll')
 # Solid rocks frame shorelines; physically breakable source mud chunks sit on wet shoulders.
 rockactor=spawn(u.Actor,'BankRocks');report['rocks']=0
 for k in range(1,4):
  mesh=assets.load_asset(OLD+'/NativeInteractions/SM_Benmore_Rock'+str(k)+'_Solid');assert mesh;b=mesh.get_bounds();ts=[]
  for _ in range(55):
   x=rng.uniform(-5950,5950);y=float(river_y(x))+rng.choice([-1,1])*rng.uniform(500,900);z=float(ground(x,y))
   if road_distance(x,y)<360:continue
   sc=rng.uniform(20,65)/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*sc-5),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)))
  c=u.GTVegetationSubsystem.add_tagged_instances(rockactor,mesh,ts,'TaigaRock','BlockAll',True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS);report['rocks']+=len(ts)
 report['clods']=0
 for i in range(115):
  k=rng.randrange(len(SHORT)-1);ax,ay=SHORT[k];bx,by=SHORT[k+1];t=rng.random();x=ax+(bx-ax)*t;y=ay+(by-ay)*t+rng.choice([-1,1])*rng.uniform(130,240)
  _,_,dep,_,rest=masks(x,y)
  if dep<12:continue
  kind='b' if i%5==0 else 'a';mesh=assets.load_asset(OLD+'/NativeInteractions/SM_plants_mud_chunk_'+kind);assert mesh
  clod=spawn(u.GTMudRunnerClod,'PhysicalClod_'+str(i),(x,y,float(ground(x,y)+rest)+2),u.Rotator(yaw=rng.uniform(0,360)));clod.large=kind=='b';clod.body.set_static_mesh(mesh);clod.body.set_collision_profile_name('BlockAllDynamic');report['clods']+=1
 route=spawn(u.GTMudRoute,'Route');route.set_editor_property('title','SIBERIAN SHOWCASE / forest, river and bog');route.set_editor_property('checkpoint_labels','1 Start  2 Pools  3 Bog  4 West ford  5 Grass  6 East ford')
 route.set_editor_property('recovery_points',[u.Transform(location=u.Vector(p['x'],p['y'],p['z']),rotation=u.Rotator(yaw=p['yaw'])) for p in data['checkpoints']])
 p=data['checkpoints'][0];spawn(u.PlayerStart,'Start',(p['x'],p['y'],p['z']),u.Rotator(yaw=p['yaw']))
 # Navigation markers are small physical posts on dry approaches, outside wheel lines.
 marker=assets.load_asset(BASE+'/M_Waymarker') or u.AssetToolsHelpers.get_asset_tools().create_asset('M_Waymarker',BASE,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(marker);g=Graph(marker);g.output(g.vector([.35,.19,.055]),u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);mel.recompile_material(marker);assets.save_loaded_asset(marker)
 for idx,p in enumerate(data['checkpoints'],1):
  a=math.radians(p['yaw']);x,y=p['x']-math.sin(a)*350,p['y']+math.cos(a)*350;z=float(ground(x,y))
  post=spawn(u.StaticMeshActor,'WaypointPost_'+str(idx),(x,y,z+50));c=post.get_component_by_class(u.StaticMeshComponent);c.set_static_mesh(assets.load_asset('/Engine/BasicShapes/Cube'));c.set_material(0,marker);c.set_collision_profile_name('BlockAll');post.set_actor_scale3d(u.Vector(.15,.15,1.))
  sign=spawn(u.TextRenderActor,'Waypoint_'+str(idx),(x,y,z+120),u.Rotator(yaw=p['yaw']-90));c=sign.get_component_by_class(u.TextRenderComponent);c.set_text(str(idx)+' / '+p['name']);c.set_world_size(23);c.set_text_render_color(u.Color(239,224,183,255))
 view=u.Vector(-9700,-10200,7400);u.EditorLevelLibrary.set_level_viewport_camera_info(view,u.MathLibrary.find_look_at_rotation(view,u.Vector(0,300,0)))
 from siberian_wave_materials import precombine
 wave_material=precombine()
 for sheet in actors.get_all_level_actors():
  if isinstance(sheet,u.GTWaterSheet):sheet.set_editor_property('ambient_wave_material',wave_material)
 assert les.save_current_level();assert hashlib.sha256(source.read_bytes()).hexdigest()==before,'Original road changed'
 report.update(ok=True,loop_length_m=data['loop_length_m'],source_level_unchanged=True)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
world=land=s=v=w=details=route=river=tree_actor=rockactor=post=sign=c=clod=None;surfaces={};visuals={}
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();until=time.monotonic()+3
def finish(dt):
 if time.monotonic()>=until:u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
