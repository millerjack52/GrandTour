"""Isolated first-pass Big Mountain level. Existing Benmore assets remain read-only."""
import unreal as u
import json,sys,time,traceback,hashlib,array,re,shutil,math,gc
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props,Graph
OUT=ROOT/'Art/Export/LidarStudy';BASE='/Game/GrandTour/ArtTests/LidarStudy';LEVEL=BASE+'/L_LidarStudy'
OLD='/Game/GrandTour/ArtTests/BenmoreWoodland'
TEMPLATE='/Game/GrandTour/ArtTests/ProceduralGround'
data=json.loads((OUT/'authoring.json').read_text());report=dict(ok=False,driving_tested=False,stages=[])
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
busy=False
def protected():
 paths=[]
 for folder in ['BenmoreWoodland','BigMountain','ProceduralGround']:
  paths+=list((ROOT/'Content/GrandTour/ArtTests'/folder).rglob('*.uasset'))+list((ROOT/'Content/GrandTour/ArtTests'/folder).rglob('*.umap'))
 return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
def spawn(cls,label,pos=(0,0,0)):
 a=actors.spawn_actor_from_class(cls,u.Vector(*pos));a.set_actor_label('LidarStudy_'+label);return a
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
 m=clone(TEMPLATE+'/M_'+kind,'M_'+kind)
 for e in mel.get_material_expressions(m):
  if isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSample)):
   t=e.get_editor_property('texture')
   if t:
    key=t.get_name()[2:]
    if key in ['style','style_groundstudy']:key='style'
    if key in textures:e.set_editor_property('texture',textures[key])
  if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(-185000,-185000,370000,0))
  if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))=='WoodlandGroundReviewOnly':e.set_editor_property('default_value',0)
  if isinstance(e,u.MaterialExpressionCustom):
   code=str(e.get_editor_property('code')).replace('+250000','+185000').replace('/500000','/370000')
   e.set_editor_property('code',code)
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
   c=re.sub(r'\(P.xy\*\.01-float2\(-1480(?:\.0+)?,-300(?:\.0+)?\)\+\.(?:625|3125)\)/float2\(126[01]\.\d+,107[56]\.\d+\)', '(P.xy+185000.)/370000.',c)
   c,n=re.subn(r'float2 buv\s*=.*?;', 'float2 buv=(P.xy+185000.)/370000.;',c);changed+=n;e.set_editor_property('code',c);codes.append(c)
 assert changed>0,'Water atlas mapping not found'
 (OUT/'water-material-code.txt').write_text('\n\n'.join(codes))
 assert not mel.recompile_material(m);assert assets.save_loaded_asset(m);return m
def run():
 global world,land,sheet,surface,visual,grass,report
 before=protected();report['protected_before']=before
 prior=OUT/'install.json'
 if prior.exists() and json.loads(prior.read_text()).get('ok'):
  report=json.loads(prior.read_text());assert protected()==report['protected_before']
  assert les.load_level(LEVEL)
  refs=actors.get_all_level_actors();a=next(a for a in refs if isinstance(a,u.GTProceduralGround))
  assert a.output_digest==report['road_generation']['digest'] and len(a.relief_tiles)==report['road_generation']['tiles']
  import lidar_gravel_dust
  report['gravel_dust']=lidar_gravel_dust.configure()
  assert les.save_current_level()
  report['post_save_reload_verified']=True
  assert les.load_level('/Engine/Maps/Entry');refs=a=None;gc.collect();yield 4
  prior.write_text(json.dumps(report,indent=2));return
 if assets.does_asset_exist(LEVEL):
  backup=ROOT/'Saved/LidarStudyBackups'/str(time.time_ns());backup.mkdir(parents=True);shutil.copy2(ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap',backup/'L_LidarStudy.umap')
 assets.make_directory(BASE)
 if not assets.does_asset_exist(LEVEL):
  assert les.load_level(TEMPLATE+'/L_BigMountain_Authoring')
  assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
 assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 refs=list(actors.get_all_level_actors());surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface));visual=next(a for a in refs if isinstance(a,u.GTMudRunnerVisual));sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet));grass=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
 forest=next(a for a in refs if a.get_actor_label()=='BigMountain_Forest')
 template_author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
 template_road=next(a for a in refs if isinstance(a,u.GTProceduralRoad) and a.relief_texture)
 relief_texture=template_road.relief_texture
 forestbindings={c.static_mesh.get_name():list(c.get_materials()) for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name().startswith('SM_Fir_')}
 keep=(u.WorldSettings,u.DirectionalLight,u.SkyLight,u.SkyAtmosphere,u.ExponentialHeightFog,u.PostProcessVolume,u.GTVehicleSurfaceEffects,u.GTDustLab,u.GTMudRunnerWheelEffects)
 for a in refs:
  if a in [surface,visual,sheet,grass] or isinstance(a,keep) or 'SkySphere' in a.get_class().get_name() or a.get_actor_label()=='Benmore_Character_SoftSky':continue
  if a.get_class().get_name() not in ['LevelScriptActor','Brush']:actors.destroy_actor(a)
 for a in actors.get_all_level_actors():
  if isinstance(a,u.GTDustLab):a.intensity=0
 import lidar_gravel_dust
 report['gravel_dust']=lidar_gravel_dust.configure()
 textures={n:tex(n) for n in ['paint','rest','style','macro','HeightRG','waterflow','waterShore']}
 mats={n:ground(n,textures) for n in ['Terrain','Detail','Tread']};wm=clone(TEMPLATE+'/M_RoadPools','M_Water')
 spec=u.load_asset('/Game/GrandTour/Demo/MackenzieBlockout/DA_Mackenzie_Blockout').spec
 props(spec,components_per_side=16,subsections_per_component=2,quads_per_subsection=63,quad_size_cm=370000/2016,origin_x_cm=-185000.,origin_y_cm=-185000.,z_scale=data['z_scale'],base_amplitude_m=0.,slope_m_per_km=0.,route_m=[],features=[],planes=[],alt_routes=[],stations=[],sections=[],spans=[],biomes=[],scrub_roughness_m=0.,road_roughness_m=0.,track_roughness_m=0.)
 sa=u.load_asset(BASE+'/DA_GridSeed') or at.create_asset('DA_GridSeed',BASE,u.GTTerrainSpecAsset,u.DataAssetFactory());props(sa,spec=spec,display_name='Build-only blank grid; do not regenerate imported Gaea terrain');assets.save_loaded_asset(sa)
 dressing=spawn(u.GTTerrainDressing,'TemporaryDressing');dressing.foliage_density=0
 builder=spawn(u.GTTerrainBuilder,'TemporaryBuilder');props(builder,spec_asset=sa,landscape_material_path=mats['Terrain'].get_path_name(),layer_info_folder=BASE+'/Layers',reground_actors=False)
 land=builder.rebuild_landscape();assert land,builder.last_message
 land.set_actor_label('LINZ LiDAR - full coverage - 1.835m landscape grid');p=land.get_actor_location();land.set_actor_location(u.Vector(p.x,p.y,data['landscape_z_cm']),False,True);land.set_editor_property('use_dynamic_material_instance',True)
 actors.destroy_actor(builder);actors.destroy_actor(dressing)
 transfer=u.load_asset(BASE+'/M_HeightTransfer') or at.create_asset('M_HeightTransfer',BASE,u.Material,u.MaterialFactoryNew());mel.delete_all_material_expressions(transfer);transfer.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
 n=props(mel.create_material_expression(transfer,u.MaterialExpressionTextureSample),texture=textures['HeightRG'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR);mel.connect_material_property(n,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR);assert not mel.recompile_material(transfer);assets.save_loaded_asset(transfer)
 rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);yield 20
 u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);yield 10
 u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer)
 c=u.RenderingLibrary.read_render_target_pixel(world,rt,1008,1008);report['transfer_center']=[c.r,c.g,c.b,c.a];report['landscape_transform']=str(land.get_actor_transform());(OUT/'progress.json').write_text(json.dumps(report,indent=2))
 assert c.r>0 or c.g>0, 'Height transfer is black'
 assert land.landscape_import_heightmap_from_render_target(rt,True,0);yield 15
 assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 6
 assert land.landscape_export_heightmap_to_render_target(rt,True,True)
 pixels=u.RenderingLibrary.read_render_target(world,rt,False);raw=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
 (OUT/'readback.r16').write_bytes(raw.tobytes())
 digest=hashlib.sha256(raw.tobytes()).hexdigest();assert digest==data['terrain_sha256'],digest
 report['height_verified']=True;report['stages'].append('Quantized LiDAR resample imported exactly')
 start=data['sites'][0];x,y=start['center']
 surface.landscape=land;surface.set_actor_location(u.Vector(x,y,0),False,True)
 props(surface,paint_origin_cm=u.Vector2D(-185000,-185000),paint_size_cm=370000.,grass_is_visual_cover=True,simulated_water=sheet,extend_water_response_to_domain=True,mud_regions=[])
 for fn,key in [(u.GTLandscapeSurfaceSetupLibrary.import_paint,'paint'),(u.GTLandscapeSurfaceSetupLibrary.import_material_atlas,'style'),(u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights,'rest')]:assert fn(surface,textures[key]),key
 props(visual,surface=surface,material=mats['Detail'],track_material=mats['Tread'],follow_player_grid=True);visual.set_actor_location(u.Vector(x,y,0),False,True)
 grass.surface=surface;grass.set_editor_property('grass_spacing_cm',45.);grass.grass.clear_instances();grass.distant_grass.clear_instances()
 domain=clone('/Game/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain','DA_WaterDomain');assert domain.import_bake(str(OUT/'water-domain.bin'));assets.save_loaded_asset(domain)
 props(sheet,water_domain=domain,domain_surfaces=[],surface_material_path=wm.get_path_name());sheet.get_component_by_class(u.ProceduralMeshComponent).clear_all_mesh_sections()
 trees=json.loads((OUT/'trees.json').read_text());forest=spawn(u.Actor,'Forest');trunks=[]
 for k in range(3):
  mesh=u.load_asset(OLD+'/Forest/SM_Fir_'+str(k));source=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(k));b=source.get_bounds();ts=[]
  for tx,ty,tz,kind,h,yaw in trees:
   if kind!=k:continue
   sc=h/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(tx,ty,tz-(b.origin.z-b.box_extent.z)*sc-8),rotation=u.Rotator(yaw=yaw),scale=u.Vector(sc,sc,sc)));trunks.append(u.Transform(location=u.Vector(tx,ty,tz+220),scale=u.Vector(.35,.35,4.4)))
  c=u.GTVegetationSubsystem.add_tagged_instances(forest,mesh,ts,'LidarStudyForest','NoCollision',True);c.set_cull_distances(60000,75000);props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  for i,m in enumerate(forestbindings[mesh.get_name()]):c.set_material(i,m)
  yield 1
 c=u.GTVegetationSubsystem.add_tagged_instances(forest,u.load_asset('/Engine/BasicShapes/Cylinder'),trunks,'LidarStudyTrunks','BlockAll',False);c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 owner=spawn(u.Actor,'Understory');entries=json.loads((OUT/'understory.json').read_text())
 paths=[OLD+'/Understory/SM_BirchBush','/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/SM_NativeShortGrass',OLD+'/Understory/SM_Branch']
 for kind,path in enumerate(paths):
  mesh=u.load_asset(path);assert mesh,path;b=mesh.get_bounds();ts=[]
  for item in entries:
   if item['kind']!=kind:continue
   px,py,pz=item['p'];sc=item['height_cm']/max(1,2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(px,py,pz-(b.origin.z-b.box_extent.z)*sc-3),rotation=u.Rotator(yaw=item['yaw']),scale=u.Vector(sc,sc,sc)))
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'LidarStudyUnderstory','NoCollision',False);c.set_cull_distances(16000,24000);props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  if kind==1:c.set_material(0,grass.grass_material)
  if kind==0:
   for slot in range(c.get_num_materials()):
    m=c.get_material(slot)
    if m and any(v in m.get_name().lower() for v in ['leaf','leave','foliage']):c.set_material(slot,u.load_asset(OLD+'/Understory/MI_BirchBush'))
 # Fine-road authoring remains bounded; the complete landscape and ecological
 # scatter cover the original dataset. Editable loop sits inside a 1km study.
 points=json.loads((OUT/'route.json').read_text());selected=[];distance=0.;last=points[0]
 for point in points:
  distance+=math.dist(last,point);last=point
  if not selected or distance>=2500:selected.append(point);distance=0
 if math.dist(selected[-1],points[-1])>1:selected.append(points[-1])
 xs=[p[0] for p in selected];ys=[p[1] for p in selected];cx=(max(xs)+min(xs))/2;cy=(max(ys)+min(ys))/2
 author=spawn(u.GTProceduralGround,'Editable woodland loop',(cx,cy,0))
 props(author,landscape=land,surface=surface,seed=161026,output_asset_root=BASE+'/',paint_texture=textures['paint'],style_texture=textures['style'],macro_texture=textures['macro'],relief_material=mats['Detail'],road_water_material=wm,relief_spacing_cm=50.,scatter_rules=[])
 author.generation_bounds.set_box_extent(u.Vector((max(xs)-min(xs))/2+4000,(max(ys)-min(ys))/2+4000,30000),False)
 assert author.capture_base(),author.last_message
 road=spawn(u.GTProceduralRoad,'Woodland loop - editable road',(cx,cy,0));props(road,author=author,relief_texture=relief_texture,width_cm=750.,bed_depth_cm=10.,mud_depth_cm=20.,wetness=.5,centre_grass_cover=.3,verge_grass_cover=.9,maximum_cut_fill_cm=70.,detail_seed=161026,relief_strength=.65)
 road.control_points.clear_spline_points(False)
 for i,(x,y) in enumerate(selected):
  road.control_points.add_spline_point(u.Vector(x,y,author.base_height_at(u.Vector2D(x,y))),u.SplineCoordinateSpace.WORLD,False)
  road.control_points.set_scale_at_spline_point(i,u.Vector(1,.95+.22*math.sin(i*.77)+.1*math.sin(i*2.1),1),False)
 road.control_points.update_spline()
 conditions=[]
 for name,a,b,depth,rut,firm,wet,cover,fill,churn in [
  ('Firm approach',0,160,3,3,.88,.25,.2,0,.05),
  ('Worked verge',190,440,35,15,.28,.65,.4,0,.5),
  ('Soft hollow',480,740,90,32,.02,.95,.12,16,.95),
  ('Grassy ridge',780,1120,18,6,.65,.4,.8,0,.12),
  ('Broken wet track',1170,1500,65,26,.12,.86,.2,0,.8),
  ('Firm return',1540,1930,6,4,.8,.3,.5,0,.08),
  ('Boggy return',1980,2220,100,36,0,1,.3,0,1)]:
  conditions.append(props(u.GTRoadCondition(),name=name,start_metres=a,end_metres=b,blend_metres=15.,mud_depth_cm=float(depth),rut_depth_cm=float(rut),firmness=float(firm),wetness=float(wet),grass_cover=float(cover),water_fill_cm=float(fill),track_spread_cm=160.*churn,churn=float(churn),crossing_tracks=.5*churn,breakup_cm=2.+10*churn))
 road.conditions=conditions
 assert author.rebuild(),author.last_message
 report['road_generation']=dict(digest=author.output_digest,tiles=len(author.relief_tiles),triangles=author.relief_triangles,wet_pool_samples=author.road_pool_wet_samples,conditions=len(conditions));yield 12
 for t in [textures['paint'],textures['style'],textures['macro']]:assert assets.save_loaded_asset(t)
 for site in data['sites']:
  xy=u.Vector2D(*site['center']);h=author.base_height_at(xy)
  for tile in author.relief_tiles.values():
   o=tile.get_actor_location()
   if o.x<=xy.x<o.x+tile.span_cm and o.y<=xy.y<o.y+tile.span_cm:h=tile.height_at(xy);break
  site['center_height_cm']=h
 (OUT/'installed-sites.json').write_text(json.dumps(data['sites'],indent=2))
 route=spawn(u.GTMudRoute,'Route');route.set_editor_property('title','LIDAR WOODLAND / full coverage');route.set_editor_property('checkpoint_labels','1 Trailhead   2 Woodland   3 Wet hollow   4 Ridge return')
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
 (OUT/'install.json').write_text(json.dumps(report,indent=2));les.load_level('/Engine/Maps/Entry');yield 4
steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1100,'Install timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:
  u.unregister_slate_post_tick_callback(handle)
  for key in ['world','land','sheet','surface','visual','grass']:globals()[key]=None
  gc.collect();u.SystemLibrary.quit_editor()
 except Exception:
  report['error']=traceback.format_exc();(OUT/'install.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)



