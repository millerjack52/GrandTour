"""Isolated first-pass Big Mountain level. Existing Benmore assets remain read-only."""
import unreal as u
import json,sys,time,traceback,hashlib,array,re,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props,Graph
OUT=ROOT/'Art/Export/NativeRoad';BASE='/Game/GrandTour/ArtTests/NativeRoad';LEVEL=BASE+'/L_NativeRoad'
OLD='/Game/GrandTour/ArtTests/BenmoreWoodland'
data=json.loads((OUT/'authoring.json').read_text());report=dict(ok=False,driving_tested=False,stages=[])
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
busy=False
def protected():
 paths=[p for folder in ['BenmoreWoodland','BigMountain'] for p in (ROOT/'Content/GrandTour/ArtTests'/folder).rglob('*') if p.suffix in ['.uasset','.umap']]
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def spawn(cls,label,pos=(0,0,0)):
 a=actors.spawn_actor_from_class(cls,u.Vector(*pos));a.set_actor_label('NativeRoad_'+label);return a
def tex(name):
 t=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
 at.import_asset_tasks([t]);v=u.load_asset(BASE+'/T_'+name);assert v
 props(v,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST if name=='HeightRG' else u.TextureFilter.TF_BILINEAR,never_stream=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
 assert assets.save_loaded_asset(v);return v
def clone(source,name):
 path=BASE+'/'+name
 if assets.does_asset_exist(path):return u.load_asset(path)
 a=assets.duplicate_asset(source,path);assert a;return a
def ground(kind,textures):
 m=clone(OLD+'/M_'+kind,'M_'+kind)
 for e in mel.get_material_expressions(m):
  if isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSample)):
   t=e.get_editor_property('texture')
   if t:
    key=t.get_name()[2:]
    if key in ['style','style_groundstudy']:key='style'
    if key in textures:e.set_editor_property('texture',textures[key])
  if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(-6400,-6400,12800,0))
  if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='WoodlandGroundReviewOnly':e.set_editor_property('default_value',0)
  if isinstance(e,u.MaterialExpressionCustom):
   code=str(e.get_editor_property('code')).replace('+125000','+6400').replace('/250000','/12800')
   e.set_editor_property('code',code)
 if kind!='Tread' and not any(str(e.get_editor_property('desc'))=='NativeReferenceAuthoredTracks' for e in mel.get_material_expressions(m)):
  g=Graph(m,'NativeReferenceAuthoredTracks')
  source=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR);pin=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_BASE_COLOR)
  n=g.custom(['C','P','Tracks'],'float a=Texture2DSample(Tracks,TracksSampler,saturate((P.xy+6400.)/12800.)).r;return C*lerp(1.,.82,a);')
  g.wire(source,n,'C',pin);g.wire(g.node(u.MaterialExpressionWorldPosition),n,'P');g.wire(g.node(u.MaterialExpressionTextureObject,texture=textures['authoredTracks'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,'Tracks');g.output(n,u.MaterialProperty.MP_BASE_COLOR)
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return m
def water(flow,shore):
 m=clone('/Game/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces/M_NativeDomainRiver','M_Water')
 changed=0;codes=[]
 for e in mel.get_material_expressions(m):
  if isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter)):
   t=e.get_editor_property('texture')
   if t and ('DomainFlow' in t.get_name() or t.get_name()=='T_waterflow'):e.set_editor_property('texture',flow)
   if t and 'Shore' in t.get_name():e.set_editor_property('texture',shore)
  if isinstance(e,u.MaterialExpressionCustom):
   c=str(e.get_editor_property('code'))
   c=re.sub(r'\(P.xy\*\.01-float2\(-1480(?:\.0+)?,-300(?:\.0+)?\)\+\.(?:625|3125)\)/float2\(126[01]\.\d+,107[56]\.\d+\)', '(P.xy+6400.)/12800.',c)
   c,n=re.subn(r'float2 buv\s*=.*?;', 'float2 buv=(P.xy+6400.)/12800.;',c);changed+=n;e.set_editor_property('code',c);codes.append(c)
 assert changed>0,'Water atlas mapping not found'
 (OUT/'water-material-code.txt').write_text('\n\n'.join(codes))
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return m
def run():
 global world,land,sheet,surface,visual,grass
 before=protected();report['protected_before']=before
 prior=OUT/'install.json'
 assert not (prior.exists() and json.loads(prior.read_text()).get('ok')), 'Completed map retained; use check'
 if assets.does_asset_exist(LEVEL):
  backup=ROOT/'Saved/NativeRoadBackups'/str(time.time_ns());backup.mkdir(parents=True);shutil.copy2(ROOT/'Content/GrandTour/ArtTests/NativeRoad/L_NativeRoad.umap',backup/'L_NativeRoad.umap')
 assets.make_directory(BASE)
 if not assets.does_asset_exist(LEVEL):
  assert les.load_level(OLD+'/L_Benmore_Woodland')
  assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
 assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 refs=list(actors.get_all_level_actors());surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface));visual=next(a for a in refs if isinstance(a,u.GTMudRunnerVisual));sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet));grass=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
 forest=next(a for a in refs if a.get_actor_label()=='Woodland_DenseForest')
 forestbindings={c.static_mesh.get_name():list(c.get_materials()) for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith('SM_Fir_')}
 keep=(u.WorldSettings,u.DirectionalLight,u.SkyLight,u.SkyAtmosphere,u.ExponentialHeightFog,u.PostProcessVolume,u.GTVehicleSurfaceEffects,u.GTDustLab,u.GTMudRunnerWheelEffects)
 for a in refs:
  if a in [surface,visual,sheet,grass] or isinstance(a,keep) or 'SkySphere' in a.get_class().get_name() or a.get_actor_label()=='Benmore_Character_SoftSky':continue
  if a.get_class().get_name() not in ['LevelScriptActor','Brush']:actors.destroy_actor(a)
 for a in actors.get_all_level_actors():
  if isinstance(a,u.GTVehicleSurfaceEffects):a.dust_intensity=0
  if isinstance(a,u.GTDustLab):a.intensity=0
 textures={n:tex(n) for n in ['paint','rest','style','macro','HeightRG','waterflow','waterShore','relief','ReliefLighting','authoredTracks']}
 mats={n:ground(n,textures) for n in ['Terrain','Detail','Tread']};wm=water(textures['waterflow'],textures['waterShore'])
 spec=u.load_asset('/Game/GrandTour/Demo/MackenzieBlockout/DA_Mackenzie_Blockout').spec
 props(spec,components_per_side=8,subsections_per_component=2,quads_per_subsection=63,quad_size_cm=12800/1008,origin_x_cm=-6400.,origin_y_cm=-6400.,z_scale=data['z_scale'],base_amplitude_m=0.,slope_m_per_km=0.,route_m=[],features=[],planes=[],alt_routes=[],stations=[],sections=[],spans=[],biomes=[],scrub_roughness_m=0.,road_roughness_m=0.,track_roughness_m=0.)
 sa=u.load_asset(BASE+'/DA_GridSeed') or at.create_asset('DA_GridSeed',BASE,u.GTTerrainSpecAsset,u.DataAssetFactory());props(sa,spec=spec,display_name='Build-only blank grid; do not regenerate imported Gaea terrain');assets.save_loaded_asset(sa)
 dressing=spawn(u.GTTerrainDressing,'TemporaryDressing');dressing.foliage_density=0
 builder=spawn(u.GTTerrainBuilder,'TemporaryBuilder');props(builder,spec_asset=sa,landscape_material_path=mats['Terrain'].get_path_name(),layer_info_folder=BASE+'/Layers',reground_actors=False)
 land=builder.rebuild_landscape();assert land,builder.last_message
 land.set_actor_label('NativeRoad_NativeReference_128m');p=land.get_actor_location();land.set_actor_location(u.Vector(p.x,p.y,data['landscape_z_cm']),False,True);land.set_editor_property('use_dynamic_material_instance',True)
 actors.destroy_actor(builder);actors.destroy_actor(dressing)
 transfer=u.load_asset(BASE+'/M_HeightTransfer') or at.create_asset('M_HeightTransfer',BASE,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(transfer);transfer.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 n=props(mel.create_material_expression(transfer,u.MaterialExpressionTextureSample),texture=textures['HeightRG'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);mel.connect_material_property(n,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(transfer);assets.save_loaded_asset(transfer)
 rt=u.RenderingLibrary.create_render_target2d(world,1009,1009,u.TextureRenderTargetFormat.RTF_RGBA8);yield 20
 u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);yield 10
 u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer)
 c=u.RenderingLibrary.read_render_target_pixel(world,rt,504,504);report['transfer_center']=[c.r,c.g,c.b,c.a];report['landscape_transform']=str(land.get_actor_transform());(OUT/'progress.json').write_text(json.dumps(report,indent=2))
 assert c.r>0 or c.g>0, 'Height transfer is black'
 assert land.landscape_import_heightmap_from_render_target(rt,True,0);yield 15
 assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 6
 assert land.landscape_export_heightmap_to_render_target(rt,True,True)
 pixels=u.RenderingLibrary.read_render_target(world,rt,False);raw=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
 (OUT/'readback.r16').write_bytes(raw.tobytes())
 digest=hashlib.sha256(raw.tobytes()).hexdigest();assert digest==data['terrain_sha256'],digest
 report['height_verified']=True;report['stages'].append('Decoded native height + authored mud imported exactly')
 start=data['sites'][0];x,y=start['center']
 surface.landscape=land;surface.set_actor_location(u.Vector(x,y,0),False,True)
 props(surface,paint_origin_cm=u.Vector2D(-6400,-6400),paint_size_cm=12800.,grass_is_visual_cover=True,simulated_water=sheet,extend_water_response_to_domain=True,mud_regions=[])
 for fn,key in [(u.GTLandscapeSurfaceSetupLibrary.import_paint,'paint'),(u.GTLandscapeSurfaceSetupLibrary.import_material_atlas,'style'),(u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights,'rest')]:assert fn(surface,textures[key]),key
 props(visual,surface=surface,material=mats['Detail'],track_material=mats['Tread'],follow_player_grid=True);visual.set_actor_location(u.Vector(x,y,0),False,True)
 assert u.GTLandscapeSurfaceSetupLibrary.import_mud_relief(surface,textures['relief'],12800.)
 grass.surface=surface;grass.set_editor_property('grass_spacing_cm',45.);grass.grass.clear_instances();grass.distant_grass.clear_instances()
 domain=clone('/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain','DA_WaterDomain');assert domain.import_bake(str(OUT/'water-domain.bin'));assets.save_loaded_asset(domain)
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.OBJ 0')
 ui=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(ui.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,generate_lightmap_u_vs=False)
 task=props(u.AssetImportTask(),filename=str(OUT/'Water.obj'),destination_path=BASE,destination_name='SM_Water',automated=True,replace_existing=True,save=True,options=ui);at.import_asset_tasks([task]);mesh=u.load_asset(BASE+'/SM_Water');assert mesh
 mesh.set_material(0,wm);assets.save_loaded_asset(mesh)
 wateractor=spawn(u.StaticMeshActor,'GaeaLakes');wateractor.static_mesh_component.set_static_mesh(mesh);wateractor.static_mesh_component.set_material(0,wm);wateractor.static_mesh_component.set_collision_profile_name('NoCollision');props(wateractor.static_mesh_component,cast_shadow=False,affect_distance_field_lighting=False,receives_decals=False)
 props(sheet,water_domain=domain,domain_surfaces=[wateractor],surface_material_path=wm.get_path_name());sheet.get_component_by_class(u.ProceduralMeshComponent).clear_all_mesh_sections()
 trees=json.loads((OUT/'trees.json').read_text());forest=spawn(u.Actor,'Forest');trunks=[]
 for k in range(3):
  mesh=u.load_asset(OLD+'/Forest/SM_Fir_'+str(k));source=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(k));b=source.get_bounds();ts=[]
  for tx,ty,tz,kind,h,yaw in trees:
   if kind!=k:continue
   sc=h/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(tx,ty,tz-(b.origin.z-b.box_extent.z)*sc-8),rotation=u.Rotator(yaw=yaw),scale=u.Vector(sc,sc,sc)));trunks.append(u.Transform(location=u.Vector(tx,ty,tz+220),scale=u.Vector(.35,.35,4.4)))
  c=u.GTVegetationSubsystem.add_tagged_instances(forest,mesh,ts,'NativeRoadForest','NoCollision',True);c.set_cull_distances(18000,22000);props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  for i,m in enumerate(forestbindings[mesh.get_name()]):c.set_material(i,m)
  yield 1
 c=u.GTVegetationSubsystem.add_tagged_instances(forest,u.load_asset('/Engine/BasicShapes/Cylinder'),trunks,'NativeRoadTrunks','BlockAll',False);c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 owner=spawn(u.Actor,'Understory');entries=json.loads((OUT/'understory.json').read_text())
 paths=[OLD+'/Understory/SM_BirchBush','/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/SM_NativeShortGrass',OLD+'/Understory/SM_Branch']
 for kind,path in enumerate(paths):
  mesh=u.load_asset(path);assert mesh,path;b=mesh.get_bounds();ts=[]
  for item in entries:
   if item['kind']!=kind:continue
   px,py,pz=item['p'];sc=item['height_cm']/max(1,2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(px,py,pz-(b.origin.z-b.box_extent.z)*sc-3),rotation=u.Rotator(yaw=item['yaw']),scale=u.Vector(sc,sc,sc)))
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'NativeRoadUnderstory','NoCollision',False);c.set_cull_distances(7000,11000);props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  if kind==1:c.set_material(0,grass.grass_material)
  if kind==0:
   for slot in range(c.get_num_materials()):
    m=c.get_material(slot)
    if m and any(v in m.get_name().lower() for v in ['leaf','leave','foliage']):c.set_material(slot,u.load_asset(OLD+'/Understory/MI_BirchBush'))
 debris=json.loads((OUT/'debris.json').read_text());owner=spawn(u.Actor,'NativeDebris')
 for kind in ['mud_chunk_a','mud_chunk_b','lying_spruce_a']:
  source='/Game/GrandTour/ArtTests/GroundDetail/SM_GD_Clod'+('0' if kind=='mud_chunk_a' else '3') if kind!='lying_spruce_a' else OLD+'/Understory/SM_Branch'
  mesh=u.load_asset(source);assert mesh,source;b=mesh.get_bounds();ts=[]
  for d in debris:
   if d['brand']!=kind:continue
   x,y,z=d['p'];sc=d['scale'];target=35*sc if kind!='lying_spruce_a' else 320*sc
   factor=target/max(1,2*max(b.box_extent.x,b.box_extent.y));z-=5
   ts.append(u.Transform(location=u.Vector(x,y,z-b.origin.z*factor+b.box_extent.z*factor*.65),rotation=u.Rotator(yaw=d['yaw']),scale=u.Vector(factor,factor,factor)))
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'NativeReferenceDebris','NoCollision',False);c.set_cull_distances(10000,14000)
  # Small mud clods retain terrain support; logs use existing mesh collision if available.
  if kind=='lying_spruce_a':c.set_collision_profile_name('BlockAll');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 route=spawn(u.GTMudRoute,'Route');route.set_editor_property('title','NATIVE EDITOR / muddy road reference');route.set_editor_property('checkpoint_labels','1 Road entry   2 Muddy bend   3 Pool edge')
 route.set_editor_property('recovery_points',[u.Transform(location=u.Vector(*s['center'],s['center_height_cm']+80),rotation=u.Rotator(yaw=s['yaw'])) for s in data['sites']])
 spawn(u.PlayerStart,'Start',(*start['center'],start['center_height_cm']+80)).set_actor_rotation(u.Rotator(yaw=start['yaw']),False)
 for s in data['sites']:
  cx,cy=s['center'];z=s['center_height_cm'];cam=spawn(u.CameraActor,s['name']+'_Camera',(cx-900,cy-1000,z+600));cam.set_actor_rotation(u.MathLibrary.find_look_at_rotation(cam.get_actor_location(),u.Vector(cx,cy,z+80)),False)
  if s==start:u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(cam.get_actor_location(),cam.get_actor_rotation())
 assert les.save_current_level();yield 2
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 loaded=actors.get_all_level_actors();assert len([a for a in loaded if isinstance(a,u.Landscape)])==1;assert len([a for a in loaded if isinstance(a,u.GTLandscapeSurface)])==1
 assert protected()==before
 report.update(ok=True,saved_and_reloaded=True,level=LEVEL,trees=len(trees),understory=len(entries),height_sha256=digest,original_benmore_unchanged=True)
 (OUT/'install.json').write_text(json.dumps(report,indent=2));yield 1
steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1100,'Install timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();(OUT/'install.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
