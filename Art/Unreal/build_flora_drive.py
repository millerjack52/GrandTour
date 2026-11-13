"""Isolated playable demo: existing deformable mud/water, new Flora Paint/Cloud Paint art."""
import unreal as u,json,math,random,traceback,hashlib,time,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();O=ROOT/'Art/Export/FloraDrive';DEST='/Game/GrandTour/ArtTests/FloraDrive';LEVEL=DEST+'/L_FloraDrive';SOURCE='/Game/GrandTour/ArtTests/MudRoad/L_MudRoad';FLORA='/Game/GrandTour/ArtTests/FloraPath'
sys.path[:0]=[str(ROOT/'Art/Unreal'),str(ROOT/'Art/tools')]
from benmore_river_life_materials import props,Graph
from make_mud_road import centre,heading
from flora_drive_ground import ground_height,floor_z,pond_delta,surround_height
import flora_drive_ground_materials as floor_detail
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary;at=u.AssetToolsHelpers.get_asset_tools();mel=u.MaterialEditingLibrary
r={'ok':False,'level':LEVEL,'source_level':SOURCE,'counts':{},'performance_verified':False}
def spawn(cls,name,p=(0,0,0),rot=None):
 a=act.spawn_actor_from_class(cls,u.Vector(*p),rot or u.Rotator());a.set_actor_label('FloraDrive_'+name);return a
def mat(name):
 m=u.load_asset(DEST+'/'+name) or at.create_asset(name,DEST,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(m);return m,Graph(m,'FloraDrive')
def save_mat(m):mel.recompile_material(m);eal.save_loaded_asset(m)
def texture(file,name):
 t=props(u.AssetImportTask(),filename=str(file),destination_path=DEST,destination_name=name,automated=True,replace_existing=True,save=True);at.import_asset_tasks([t]);tex=u.load_asset(DEST+'/'+name);assert tex;return tex
try:
 cfg=json.loads((O/'look-settings.json').read_text());rng=random.Random(20261112)
 # The source and the approved path study are read-only inputs for this build.
 protected=[ROOT/'Content/GrandTour/ArtTests'/p for p in ['MudRoad/L_MudRoad.umap','MudLab/L_MudLab.umap','LidarStudy/L_LidarStudy.umap','FloraPath/L_FloraPath.umap']]
 hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
 (O/'protected-before.json').write_text(json.dumps(hashes,indent=2))
 if eal.does_asset_exist(LEVEL):assert les.load_level(LEVEL)
 else:
  assert les.load_level(SOURCE);assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL);assert les.load_level(LEVEL)
 for a in list(act.get_all_level_actors()):
  label=a.get_actor_label()
  if label.startswith(('MudScene_Detail_','MudRoad_Dressing','MixedRoute_','FloraDrive_')) or isinstance(a,(u.DirectionalLight,u.SkyLight,u.SkyAtmosphere,u.ExponentialHeightFog,u.PostProcessVolume,u.VolumetricCloud,u.TextRenderActor)):
   act.destroy_actor(a)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();world.get_world_settings().set_editor_property('default_game_mode',u.GTMudLabGameMode)
 route=next(a for a in act.get_all_level_actors() if isinstance(a,u.GTMudRoute));props(route,title='FLORA DRIVE / painted forest + live mud',checkpoint_labels='1 Forest start   2 Puddle trail   3 Wet clearing',start_low_range=True,start_diff_locked=True)
 for start in act.get_all_level_actors():
  if isinstance(start,u.PlayerStart):
   p=start.get_actor_location();start.set_actor_location(u.Vector(p.x,p.y,120),False,True)
 surface=next(a for a in act.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface));visual=next(a for a in act.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual));assert surface.simulated_water and visual.water_sheet
 if visual.hide_whole_landscape:surface.separate_visual_mesh=True
 # Extend this demo's existing numerical field with the woodland pond.
 paint=texture(O/'soil-paint.png','T_FloraDrivePaint');rest=texture(O/'world-rest.png','T_FloraDriveRest')
 for t in [paint,rest]:
  props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True);eal.save_loaded_asset(t)
 assert u.GTLandscapeSurfaceSetupLibrary.import_paint(surface,paint)
 assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(surface,rest)
 def bind_rest(m):
  for e in mel.get_material_expressions(m):
   if isinstance(e,u.MaterialExpressionTextureObjectParameter):
    key=str(e.get_editor_property('parameter_name'))
    if key=='GTLS_Paint':e.set_editor_property('texture',paint)
    if key=='GTLS_Rest':e.set_editor_property('texture',rest)
  save_mat(m)
 for field,name in [('surface_material_path','M_FloraWater')]:
  source=u.load_asset(surface.simulated_water.get_editor_property(field));path=DEST+'/'+name
  water_mat=u.load_asset(path) or eal.duplicate_asset(source.get_path_name().split('.')[0],path);assert water_mat;bind_rest(water_mat)
  surface.simulated_water.set_editor_property(field,path)
 for field,name in [('water_simulation_material','M_FloraWaterSim'),('sediment_simulation_material','M_FloraWaterSediment')]:
  source=visual.get_editor_property(field);path=DEST+'/'+name;m=u.load_asset(path) or eal.duplicate_asset(source.get_path_name().split('.')[0],path);bind_rest(m);visual.set_editor_property(field,m)
 r['pond']=json.loads((O/'pond-authoring.json').read_text())
 r['mud_system']={'native_updates':surface.use_native_mud_shader_updates,'wheel_support':surface.enable_wheel_support,'water_sheet':surface.simulated_water.get_actor_label()}
 # Map-local lighting bridge: recovered pigment/geometry remain, Unreal owns sunlight and shadows.
 def lit_soil(source,name):
  path=DEST+'/'+name;m=u.load_asset(path) or eal.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
  if m.get_editor_property('shading_model')==u.MaterialShadingModel.MSM_UNLIT:
   native=mel.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR);assert isinstance(native,u.MaterialExpressionCustom)
   code=str(native.get_editor_property('code'));assert 'mrNormal' in code
   pos=code.rfind('return ');assert pos>0
   native.set_editor_property('code',code[:pos]+'FloraNormal=mrNormal;\n'+code[pos:])
   native.set_editor_property('additional_outputs',list(native.get_editor_property('additional_outputs'))+[props(u.CustomOutput(),output_name='FloraNormal',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)])
   g=Graph(m,'FloraDriveLighting');props(m,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT)
   g.output(native,u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(0),u.MaterialProperty.MP_EMISSIVE_COLOR)
   signed=g.node(u.MaterialExpressionMultiply);g.wire(native,signed,'A','FloraNormal');g.wire(g.node(u.MaterialExpressionTwoSidedSign),signed,'B');g.output(signed,u.MaterialProperty.MP_NORMAL)
   g.output(g.scalar(.85),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.12),u.MaterialProperty.MP_SPECULAR)
   if m.get_editor_property('blend_mode')==u.BlendMode.BLEND_TRANSLUCENT:props(m,translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
   save_mat(m)
  parameters=[e for e in mel.get_material_expressions(m) if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='SoilPigmentScale']
  if parameters:parameters[0].set_editor_property('default_value',cfg['soil_pigment_scale'])
  else:
   g=Graph(m,'FloraDriveSoilPalette');old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
   scale=g.node(u.MaterialExpressionScalarParameter,parameter_name='SoilPigmentScale',default_value=cfg['soil_pigment_scale']);tint=g.node(u.MaterialExpressionVectorParameter,parameter_name='SoilTint',default_value=u.LinearColor(.9,.66,.4,1))
   c=g.custom(['Pigment','Scale','Tint'],'return saturate(Pigment*Scale*Tint);');g.wire(old,c,'Pigment');g.wire(scale,c,'Scale');g.wire(tint,c,'Tint');g.output(c,u.MaterialProperty.MP_BASE_COLOR)
  save_mat(m)
  bind_rest(m)
  return m
 floor_detail.controls();floor_textures=floor_detail.textures()
 visual.material=lit_soil(visual.material,'M_FloraSoil');floor_detail.apply(visual.material,floor_textures)
 if visual.track_material:
  visual.track_material=lit_soil(visual.track_material,'M_FloraTread');floor_detail.apply(visual.track_material,floor_textures)
 from flora_lidar_mud import install as match_lidar_mud
 r['lidar_mud']=match_lidar_mud(surface,visual,texture)
 old=surface.landscape.landscape_material
 if old.get_editor_property('shading_model')==u.MaterialShadingModel.MSM_UNLIT or old.get_path_name().startswith(DEST+'/M_FloraLandscape'):
  surface.landscape.landscape_material=lit_soil(old,'M_FloraLandscape')
  floor_detail.apply(surface.landscape.landscape_material,floor_textures)
  for c in surface.landscape.get_components_by_class(u.MeshComponent):
   for i in range(c.get_num_materials()):c.set_material(i,surface.landscape.landscape_material)
 # A simple firm apron carries the surrounding forest and keeps the test plot out of a sky void.
 apron=spawn(u.StaticMeshActor,'ForestApron',(0,0,-35));apron.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Plane'));apron.static_mesh_component.set_material(0,visual.material);apron.set_actor_scale3d(u.Vector(120,120,1));apron.static_mesh_component.set_collision_profile_name('BlockAll')
 # Shallow, low-poly shoulder forms: no displacement cost and no obstruction to the route.
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 for ground_mesh_name in ['SM_FloraFloorForms','SM_ForestSurround']:
  task=props(u.AssetImportTask(),filename=str(O/(ground_mesh_name+'.fbx')),destination_path=DEST,destination_name=ground_mesh_name,replace_existing=True,automated=True,save=True)
  opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False);task.options=opt;at.import_asset_tasks([task])
 m,g=mat('M_ForestFloorForms');props(m,tangent_space_normal=False)
 floor_colour=g.vector((.15,.10,.055));floor_normal=g.node(u.MaterialExpressionVertexNormalWS)
 g.output(floor_colour,u.MaterialProperty.MP_BASE_COLOR);g.output(floor_normal,u.MaterialProperty.MP_NORMAL);g.output(g.scalar(.9),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.12),u.MaterialProperty.MP_SPECULAR)
 floor_detail.apply(m,floor_textures,floor_colour,floor_normal)
 forms=spawn(u.StaticMeshActor,'ForestFloorForms');forms.static_mesh_component.set_static_mesh(u.load_asset(DEST+'/SM_FloraFloorForms'));forms.static_mesh_component.set_material(0,m);forms.static_mesh_component.set_collision_profile_name('NoCollision');forms.set_actor_enable_collision(False)
 surround_mat,g=mat('M_ForestSurround');props(surround_mat,tangent_space_normal=False)
 # Broad shaded forest-floor colours carry distant stands without more POM reads.
 p=g.node(u.MaterialExpressionWorldPosition);shade=g.custom(['P'],'float n=.5+.25*sin(P.x*.002+sin(P.y*.001))+.25*sin(P.y*.0017-P.x*.0011);return lerp(float3(.035,.042,.022),float3(.075,.083,.040),n);');g.wire(p,shade,'P');g.output(shade,u.MaterialProperty.MP_BASE_COLOR);g.output(g.scalar(.95),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.1),u.MaterialProperty.MP_SPECULAR);save_mat(surround_mat)
 surround=spawn(u.StaticMeshActor,'WoodedSurround');surround_mesh=u.load_asset(DEST+'/SM_ForestSurround');props(surround_mesh.get_editor_property('body_setup'),collision_trace_flag=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE);eal.save_loaded_asset(surround_mesh);surround.static_mesh_component.set_static_mesh(surround_mesh);surround.static_mesh_component.set_material(0,surround_mat);surround.static_mesh_component.set_collision_profile_name('BlockAll')
 r['ground_detail']=json.loads((O/'ground-geometry.json').read_text());r['ground_detail'].update(source=str(floor_detail.SRC),texture_max_size=2048,texture_samples_added=6,normal_fade_cm=[1800,6500])

 owner=spawn(u.Actor,'FloraPaint_Instances');buckets={};far_buckets={};treepoints=[]
 manifest=json.loads((ROOT/'Art/Export/LidarStudy/FloraPath/scene-manifest.json').read_text());models={row['name']:u.load_asset(FLORA+'/'+row['name']) for row in manifest['meshes']};assert all(models.values())
 def place(name,x,y,height,yaw=None):
  if pond_delta(x,y)<-4:return False
  mesh=models[name];b=mesh.get_bounds();scale=height/(b.box_extent.z*2);z=floor_z(x,y)-(b.origin.z-b.box_extent.z)*scale
  buckets.setdefault(name,[]).append(u.Transform(location=u.Vector(x,y,z),rotation=u.Rotator(yaw=rng.uniform(0,360) if yaw is None else yaw),scale=u.Vector(scale,scale,scale)))
  return True
 trees=[n for n in models if 'Tree' in n]
 for x in range(-2850,2851,570):
  for side in [-1,1]:
   for depth in [1050,2250]:
    xx=x+rng.uniform(-190,190);yy=centre(x)+side*(depth+rng.uniform(-170,170))
    if abs(yy)>3000 or (x>250 and side==1 and depth==1050):continue
    if any(math.hypot(xx-a,yy-b)<480 for a,b in treepoints):continue
    treepoints.append((xx,yy));place(rng.choice(trees),xx,yy,rng.uniform(1350,2050))
 # Instanced outer stands close the views without adding another simulated terrain/water domain.
 for ring,count in [(3850,28),(5050,36)]:
  for i in range(count):
   angle=2*math.pi*i/count+rng.uniform(-.035,.035);x=math.cos(angle)*ring;y=math.sin(angle)*ring
   treepoints.append((x,y));place(rng.choice(trees),x,y,rng.uniform(1400,2200))
 # Groups vary by habitat, with low planting near the road and sparse ferns.
 grass=[n for n in models if '_Grass_' in n and 'Dry' not in n and 'Blooming' not in n]
 bloom=[n for n in models if 'Blooming_Grass' in n];ferns=[n for n in models if 'Ferns' in n];small=[n for n in models if 'Small_Plants' in n];flowers=[n for n in models if 'Flower_B' in n];shrubs=[n for n in models if 'Shrubbery' in n];rocks=[n for n in models if '_Rock_' in n]
 for k in range(240):
  x=rng.uniform(-2900,2900);side=rng.choice([-1,1]);off=rng.uniform(340,2700);y=centre(x)+side*off
  if abs(y)>2900:continue
  for j in range(rng.randint(11,20)):
   xx=x+rng.gauss(0,130);yy=y+rng.gauss(0,125)
   if abs(xx)>3050 or abs(yy)>3050 or abs(yy-centre(xx))<280:continue
   group=grass if j%4 else bloom
   if j%9==0:group=small
   if j%17==0 and side<0:group=ferns
   place(rng.choice(group),xx,yy,rng.uniform(30,82) if group!=ferns else rng.uniform(45,80))
  if k%3==0:
   for j in range(5):place(rng.choice(flowers),x+rng.gauss(0,80),y+rng.gauss(0,75),rng.uniform(20,40))
  if k%7==0:place(rng.choice(shrubs),x,y,rng.uniform(60,105))
 for x,y in treepoints:
  if rng.random()<.7:place(rng.choice(rocks),x+100,y+90,rng.uniform(25,70))
 # Small stone clusters bridge exposed soil and planted shoulders; avoid a repeated road-edge line.
 for k in range(95):
  x=rng.uniform(-2750,2750);y=centre(x)+rng.choice([-1,1])*rng.uniform(365,1600)
  if abs(y)>2850:continue
  for j in range(rng.randint(3,7)):
   xx=x+rng.gauss(0,80);yy=y+rng.gauss(0,70)
   if abs(yy-centre(xx))<335:continue
   name=rng.choice(rocks)
   if place(name,xx,yy,rng.uniform(4,16)):
    t=buckets[name][-1];p=t.translation;t.translation=u.Vector(p.x,p.y,p.z-2)
 # Habitat-specific groups and a layered backdrop complete the small driving scene.
 from finish_flora_drive_scene import dress_scene
 r['dressing']=dress_scene(models,buckets,far_buckets,treepoints,place,spawn)
 from flora_road_relief import dress as dress_road
 r['road_relief']=json.loads((O/'road-relief-authoring.json').read_text());r['road_relief']['scatter']=dress_road(models,buckets,spawn,act)
 from flora_rock_master import install as install_rocks
 r['rock_master']=install_rocks(world,spawn)
 # Existing plants must not emerge through the solid cores of the new outcrops.
 cores=[(p['x'],p['y'],p['width_cm']*.34) for p in r['rock_master']['placements'] if p['hero']]
 clear=lambda p:not any((p.x-x)**2+(p.y-y)**2<radius**2 for x,y,radius in cores)
 before=sum(map(len,buckets.values()))
 buckets={name:[t for t in ts if clear(t.translation)] for name,ts in buckets.items()}
 treepoints[:]=[(x,y) for x,y in treepoints if clear(u.Vector(x,y,0))]
 r['rock_master']['covered_plants_removed']=before-sum(map(len,buckets.values()))
 # Preserve the source pack materials; fix empty-mask coverage on local copies.
 foliage_materials={};r['foliage_materials']=[]
 def foliage_material(source):
  key=source.get_path_name()
  if key in foliage_materials:return foliage_materials[key]
  if isinstance(source,u.MaterialInstanceConstant):
   parent=source.get_editor_property('parent');local_parent=foliage_material(parent)
   if local_parent==parent:foliage_materials[key]=source;return source
   path=DEST+'/Foliage/'+source.get_name();mi=u.load_asset(path) or eal.duplicate_asset(key.split('.')[0],path);assert mi
   mel.set_material_instance_parent(mi,local_parent);eal.save_loaded_asset(mi);foliage_materials[key]=mi;return mi
  if not isinstance(source,u.Material):return source
  nodes=[e for e in mel.get_material_expressions(source) if isinstance(e,u.MaterialExpressionCustom) and 'ViewScalarBlueNoise' in str(e.get_editor_property('code'))]
  if not nodes:foliage_materials[key]=source;return source
  path=DEST+'/Foliage/'+source.get_name();m=u.load_asset(path) or eal.duplicate_asset(key.split('.')[0],path);assert m
  for e in mel.get_material_expressions(m):
   if isinstance(e,u.MaterialExpressionCustom) and 'ViewScalarBlueNoise' in str(e.get_editor_property('code')):
    e.set_editor_property('code','float c=smoothstep(0.015,max(0.05,Softness),saturate(Coverage));if(c<=0.0)return 0.0;if(c>=1.0)return 1.0;uint leaf=(uint)(Seed*255.);uint2 p=(uint2)Parameters.SvPosition.xy+uint2(leaf*37u,leaf*91u);return ViewScalarBlueNoise(p,View.StateFrameIndex)<c ? 1.0 : 0.0;')
  for e in list(mel.get_material_expressions(m)):
   if str(e.get_editor_property('desc'))=='FloraDriveBreeze':mel.delete_material_expression(m,e)
  g=Graph(m,'FloraDriveBreeze');wp=g.node(u.MaterialExpressionWorldPosition);tm=g.node(u.MaterialExpressionTime);cp=g.node(u.MaterialExpressionCameraPositionWS)
  breeze=0. if any(s in key.lower() for s in ['fallen_leaves','branch_0']) else cfg.get('breeze_cm',1.25)
  amplitude=g.node(u.MaterialExpressionScalarParameter,parameter_name='BreezeCm',default_value=breeze)
  wind=g.custom(['P','Time','Camera','Amount'],'float fade=1-smoothstep(2500.,5500.,distance(P,Camera));float gust=sin(Time*1.1+P.x*.004+P.y*.003)*.65+sin(Time*1.8+P.y*.013)*.35;return float3(.8,.35,.08)*gust*Amount*fade;')
  for pin,n in [('P',wp),('Time',tm),('Camera',cp),('Amount',amplitude)]:g.wire(n,wind,pin)
  g.output(wind,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
  props(m,has_pixel_animation=True)
  save_mat(m);foliage_materials[key]=m;r['foliage_materials'].append({'source':key,'local':path,'empty_mask_coverage':0,'breeze_cm':breeze});return m
 for name,transforms,is_far in [(n,t,False) for n,t in buckets.items()]+[(n,t,True) for n,t in far_buckets.items()]:
  shadow=not is_far and ('Tree' in name or '_Rock_' in name or 'Ferns' in name or 'Shrubbery' in name)
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,models[name],transforms,'FloraDrive','NoCollision',shadow);c.set_cull_distances(0,0) if 'Tree' in name else c.set_cull_distances(5000,9000)
  props(c,visible_in_ray_tracing=False,affect_distance_field_lighting='Tree' in name,shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
  if is_far:c.set_forced_lod_model(3);c.set_cull_distances(15000,20000)
  for slot,entry in enumerate(models[name].static_materials):
   if entry.material_interface:c.set_material(slot,foliage_material(entry.material_interface))
  r['counts'][name]=r['counts'].get(name,0)+len(transforms)
 assert len(r['foliage_materials'])>0,'Foliage repairs must reach the material parents used by the instances'
 # Simple hidden trunk colliders, independent of the source mesh assets.
 cylinder=u.load_asset('/Engine/BasicShapes/Cylinder')
 for i,(x,y) in enumerate(treepoints):
  a=spawn(u.StaticMeshActor,'TrunkCollision_'+str(i),(x,y,floor_z(x,y)+300));a.static_mesh_component.set_static_mesh(cylinder);a.set_actor_scale3d(u.Vector(.5,.5,6));a.set_actor_hidden_in_game(True);a.static_mesh_component.set_collision_profile_name('BlockAll');a.static_mesh_component.set_cast_shadow(False)
 # Sky colour is adjustable and does not rely on the old test map's backdrop.
 m,g=mat('M_PaintedSky');props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT,two_sided=True,is_sky=True)
 v=g.node(u.MaterialExpressionCameraVectorWS);h=g.node(u.MaterialExpressionVectorParameter,parameter_name='HorizonColour',default_value=u.LinearColor(*cfg['sky_horizon'],1));z=g.node(u.MaterialExpressionVectorParameter,parameter_name='ZenithColour',default_value=u.LinearColor(*cfg['sky_zenith'],1));b=g.node(u.MaterialExpressionScalarParameter,parameter_name='SkyLuminance',default_value=cfg['sky_luminance']);e=g.custom(['V','H','Z','B'],'return lerp(H,Z,pow(saturate(-V.z),.55))*B;')
 for key,n in [('V',v),('H',h),('Z',z),('B',b)]:g.wire(n,e,key)
 g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR);save_mat(m)
 a=spawn(u.StaticMeshActor,'PaintedSky');a.tags=[u.Name('GTLook.LocalSky')];a.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));a.static_mesh_component.set_material(0,m);a.set_actor_scale3d(u.Vector(4000,4000,4000));a.static_mesh_component.set_collision_profile_name('NoCollision');a.set_actor_enable_collision(False);a.static_mesh_component.set_cast_shadow(False)
 # Creator-rendered cloud masks/colours: fixed daylight appearance, cheap distant cards.
 clouddata=json.loads((O/'cloud-render-report.json').read_text());assert clouddata['ok']
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
 if not eal.does_asset_exist(DEST+'/SM_DriveCloudCard'):
  task=props(u.AssetImportTask(),filename=str(O/'SM_DriveCloudCard.fbx'),destination_path=DEST,automated=True,save=True);opt=props(u.FbxImportUI(),import_mesh=True,import_as_skeletal=False,import_materials=False,import_textures=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH);props(opt.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,generate_lightmap_u_vs=False);task.options=opt;at.import_asset_tasks([task])
 card=u.load_asset(DEST+'/SM_DriveCloudCard');assert card
 cloudmats=[]
 for row in clouddata['clouds']:
  tex=texture(O/row['file'],'T_'+row['name']);props(tex,srgb=True,max_texture_size=2048,compression_settings=u.TextureCompressionSettings.TC_DEFAULT);eal.save_loaded_asset(tex)
  m,g=mat('M_'+row['name']);props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,two_sided=True,use_translucency_vertex_fog=False)
  t=g.node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='CloudPaintRGBA',texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR);b=g.node(u.MaterialExpressionScalarParameter,parameter_name='CloudLuminance',default_value=cfg['cloud_luminance']);mul=g.node(u.MaterialExpressionMultiply);g.wire(t,mul,'A');g.wire(b,mul,'B');g.output(mul,u.MaterialProperty.MP_EMISSIVE_COLOR);g.output(t,u.MaterialProperty.MP_OPACITY,'A');save_mat(m);cloudmats.append(m)
 for i,az in enumerate([-145,-95,-45,0,38,85,135,180]):
  angle=math.radians(az);distance=65000+(i%3)*13000;width=41000+(i%3)*5000;height=width*2/3
  a=spawn(u.StaticMeshActor,'CloudPaint_'+str(i),(math.cos(angle)*distance,math.sin(angle)*distance,24500+(i%3)*6500),u.Rotator(yaw=az));a.static_mesh_component.set_static_mesh(card);a.static_mesh_component.set_material(0,cloudmats[i%3]);a.set_actor_scale3d(u.Vector(1,width/200,height/200));a.static_mesh_component.set_collision_profile_name('NoCollision');a.set_actor_enable_collision(False);a.static_mesh_component.set_cast_shadow(False)
 # Match the cloud source's light direction and use map-local exposure/fog.
 sun=spawn(u.DirectionalLight,'Sun',(0,0,2000),u.Rotator(pitch=-35.3,yaw=-169.));sun.tags=[u.Name('GTWeatherUnmanaged')];sun.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sun.light_component,intensity=cfg['sun_lux'],light_color=u.Color(r=cfg['sun_rgb8'][0],g=cfg['sun_rgb8'][1],b=cfg['sun_rgb8'][2],a=255),light_source_angle=3.,volumetric_scattering_intensity=.6)
 sky=spawn(u.SkyLight,'Sky');sky.tags=[u.Name('GTWeatherUnmanaged')];sky.light_component.set_mobility(u.ComponentMobility.MOVABLE);props(sky.light_component,source_type=u.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP,cubemap=u.load_asset('/Game/GrandTour/ArtTests/FloraMatch/T_SourceWorld'),real_time_capture=False,lower_hemisphere_is_black=False,occlusion_max_distance=100.,intensity=cfg['sky_intensity']);sky.light_component.recapture_sky()
 fog=spawn(u.ExponentialHeightFog,'ForestMist',(0,0,150));fog.tags=[u.Name('GTWeatherUnmanaged')];props(fog.component,fog_density=cfg['fog_density'],fog_height_falloff=.12,start_distance=250.,fog_max_opacity=.94,fog_inscattering_luminance=u.LinearColor(*cfg['fog_colour'],1),enable_volumetric_fog=True,volumetric_fog_scattering_distribution=.5,volumetric_fog_albedo=u.Color(r=170,g=194,b=230,a=255),volumetric_fog_distance=9000.)
 pp=spawn(u.PostProcessVolume,'Exposure');props(pp,unbound=True,priority=600.,blend_weight=1.);ps=pp.settings
 for k,val in {'auto_exposure_min_brightness':cfg['exposure_ev'],'auto_exposure_max_brightness':cfg['exposure_ev'],'auto_exposure_bias':0.,'bloom_intensity':.1,'lens_flare_intensity':0.,'vignette_intensity':.1,'local_exposure_highlight_contrast_scale':1.,'local_exposure_shadow_contrast_scale':1.,'dynamic_global_illumination_method':u.DynamicGlobalIlluminationMethod.NONE}.items():props(ps,**{'override_'+k:True,k:val})
 pp.settings=ps
 from flora_drive_ground_shadows import apply as apply_ground_shadows
 r['ground_shadows']=apply_ground_shadows()
 u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-2850,-150,220),u.Rotator(pitch=4,yaw=8))
 assert les.save_current_level();assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items())
 r['colour_constructor_probe']=str(u.Color(255,225,172,255));r['sun_actual_colour']=str(sun.light_component.get_editor_property('light_color'));r.update(ok=True,source_maps_unchanged=True,tree_colliders=len(treepoints),tree_instances=sum(v for n,v in r['counts'].items() if 'Tree' in n),plant_instances=sum(v for n,v in r['counts'].items() if 'Tree' not in n),cloud_cards=8,cloud_source=clouddata['source'],route_length_m=52.3,attribution='Flora Paint and Cloud Paint: Casey Sheep / MeiU',settings=cfg)
except Exception:r['error']=traceback.format_exc();u.log_error(r['error'])
(O/'build-report.json').write_text(json.dumps(r,indent=2))
# Release editor references before unloading; captures run in a fresh process.
for name in ['a','owner','surface','visual','route','world','sun','sky','fog','pp','c','mesh','models','card','m','g','cloudmats']:globals()[name]=None
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
# Release nested transforms and expression containers before UObject shutdown too.
for key,value in list(globals().items()):
 if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
value=None
import gc
gc.collect();u.SystemLibrary.collect_garbage();end=time.monotonic()+3
def quit(dt):
 if time.monotonic()>end:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(quit)

