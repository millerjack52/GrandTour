"""Scoped update of the owned Big Mountain map, with backup and height readback."""
import unreal as u
from pathlib import Path
import sys,json,time,traceback,hashlib,shutil,array
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
OUT=ROOT/'Art/Export/BigMountain';BASE='/Game/GrandTour/ArtTests/BigMountain';OLD='/Game/GrandTour/ArtTests/BenmoreWoodland'
data=json.loads((OUT/'authoring.json').read_text());auth=json.loads((OUT/'enrichment-authoring.json').read_text());assert auth['ok']
report=dict(ok=False,driving_tested=False);busy=False
assets=u.EditorAssetLibrary;at=u.AssetToolsHelpers.get_asset_tools();mel=u.MaterialEditingLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
def save():(OUT/'enrich.json').write_text(json.dumps(report,indent=2))
def spawn(cls,label):
 a=actors.spawn_actor_from_class(cls,u.Vector());a.set_actor_label('BigMountain_'+label);return a
def texture(name):
 t=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True);at.import_asset_tasks([t]);v=u.load_asset(BASE+'/T_'+name);assert v
 props(v,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_NEAREST if name=='HeightRG' else u.TextureFilter.TF_BILINEAR,never_stream=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP);assert assets.save_loaded_asset(v);return v
def run():
 backup=ROOT/'Saved/BigMountainBackups'/('pre-enrichment-'+str(time.time_ns()));shutil.copytree(ROOT/'Content/GrandTour/ArtTests/BigMountain',backup/'Content');report['backup']=str(backup)
 for name in ['install.json','check.json','watercheck.json']:shutil.copy2(OUT/name,backup/name)
 protected=json.loads((OUT/'install.json').read_text())['protected_before']
 for path,digest in protected.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
 assert les.load_level(BASE+'/L_BigMountain');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();refs=actors.get_all_level_actors()
 land=next(a for a in refs if isinstance(a,u.Landscape));s=next(a for a in refs if isinstance(a,u.GTLandscapeSurface));sheet=next(a for a in refs if isinstance(a,u.GTWaterSheet));grass=next(a for a in refs if isinstance(a,u.GTMixedGroundDetails) and a.generate_around_player)
 textures={n:texture(n) for n in ['HeightRG','paint','style','rest','macro','waterflow','waterShore']}
 transfer=u.load_asset(BASE+'/M_HeightTransfer');assert transfer
 for e in mel.get_material_expressions(transfer):
  if isinstance(e,u.MaterialExpressionTextureSample):e.set_editor_property('texture',textures['HeightRG'])
 assert not mel.recompile_material(transfer);assert assets.save_loaded_asset(transfer)
 rt=u.RenderingLibrary.create_render_target2d(world,1009,1009,u.TextureRenderTargetFormat.RTF_RGBA8);yield 20
 u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);yield 10
 u.RenderingLibrary.draw_material_to_render_target(world,rt,transfer);assert land.landscape_import_heightmap_from_render_target(rt,True,0);yield 15
 assert land.landscape_export_heightmap_to_render_target(rt,True,True);yield 6
 assert land.landscape_export_heightmap_to_render_target(rt,True,True)
 pixels=u.RenderingLibrary.read_render_target(world,rt,False);raw=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
 digest=hashlib.sha256(raw.tobytes()).hexdigest();assert digest==data['terrain_sha256'],digest;report['height_verified']=True;report['height_sha256']=digest;save()
 for fn,key in [(u.GTLandscapeSurfaceSetupLibrary.import_paint,'paint'),(u.GTLandscapeSurfaceSetupLibrary.import_material_atlas,'style'),(u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights,'rest')]:assert fn(s,textures[key]),key
 grass.grass.clear_instances();grass.distant_grass.clear_instances()
 domain=u.load_asset(BASE+'/DA_WaterDomain');assert domain.import_bake(str(OUT/'water-domain.bin'));assert assets.save_loaded_asset(domain)
 for a in list(refs):
  if a.get_actor_label() in ['BigMountain_Understory','BigMountain_Ecology','BigMountain_Puddles']:actors.destroy_actor(a)
 u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.OBJ 0')
 ui=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(ui.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,generate_lightmap_u_vs=False)
 task=props(u.AssetImportTask(),filename=str(OUT/'Puddles.obj'),destination_path=BASE,destination_name='SM_Puddles',automated=True,replace_existing=True,save=True,options=ui);at.import_asset_tasks([task]);mesh=u.load_asset(BASE+'/SM_Puddles');assert mesh
 wm=u.load_asset(BASE+'/M_Water');mesh.set_material(0,wm);assets.save_loaded_asset(mesh)
 water=spawn(u.StaticMeshActor,'Puddles');water.static_mesh_component.set_static_mesh(mesh);water.static_mesh_component.set_material(0,wm);water.static_mesh_component.set_collision_profile_name('NoCollision');props(water.static_mesh_component,cast_shadow=False,affect_distance_field_lighting=False,receives_decals=False)
 lakes=next(a for a in refs if a.get_actor_label()=='BigMountain_GaeaLakes');sheet.set_editor_property('domain_surfaces',[lakes,water])
 forest=next(a for a in refs if a.get_actor_label()=='BigMountain_Forest');cs=forest.get_components_by_class(u.InstancedStaticMeshComponent);trees=json.loads((OUT/'trees.json').read_text());trunks=[];bindings={}
 for k in range(3):
  c=next(c for c in cs if c.static_mesh and c.static_mesh.get_name()=='SM_Fir_'+str(k));bindings[k]=list(c.get_materials());b=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(k)).get_bounds();ts=[]
  for x,y,z,kind,h,yaw in trees:
   if kind!=k:continue
   scale=h/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*scale-8),rotation=u.Rotator(yaw=yaw),scale=u.Vector(scale,scale,scale)));trunks.append(u.Transform(location=u.Vector(x,y,z+220),scale=u.Vector(.35,.35,4.4)))
  c.clear_instances();c.add_instances(ts,False,True);yield 1
 c=next(c for c in cs if c.static_mesh and c.static_mesh.get_name()=='Cylinder');c.clear_instances();c.add_instances(trunks,False,True)
 owner=spawn(u.Actor,'Ecology');entries=json.loads((OUT/'ecology.json').read_text());treebase='/Game/OWGame/Dev/DressingLab/Trees/'
 paths=[OLD+'/Understory/SM_BirchBush',treebase+'SM_OWBush_Beech_B',OLD+'/Forest/SM_Fir_0','/Game/OWGame/Dev/DressingLab/SM_OWFlowerClump_White','/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/SM_NativeShortGrass',OLD+'/Understory/SM_Branch',treebase+'SM_OWFir_Stump_A']+['/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/SM_Benmore_Rock'+str(k)+'_Solid' for k in range(1,4)]
 report['ecology']=[]
 for kind,path in enumerate(paths):
  mesh=u.load_asset(path);assert mesh,path
  if kind>=7:
   owned=BASE+'/SM_EcologyRock'+str(kind-6);mesh=u.load_asset(owned) or assets.duplicate_asset(path,owned);se=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
   if se.get_convex_collision_count(mesh)==0:assert se.set_convex_decomposition_collisions(mesh,1,24,50000)
   assert se.get_convex_collision_count(mesh)>0;assert assets.save_loaded_asset(mesh)
  b=(u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_0') if kind==2 else mesh).get_bounds();ts=[]
  for item in entries:
   if item['kind']!=kind:continue
   x,y,z=item['p'];scale=item['height_cm']/max(1,2*b.box_extent.z);bury=8 if kind>=6 else 3
   ts.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*scale-bury),rotation=u.Rotator(yaw=item['yaw']),scale=u.Vector(scale,scale,scale)))
  collision=kind>=7
  if collision:assert u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_convex_collision_count(mesh)>0,path
  c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'BigMountainEcology','BlockAll' if collision else 'NoCollision',kind>=7)
  c.set_cull_distances(12000 if kind not in [3,4,5] else 7000,19000 if kind not in [3,4,5] else 12000);props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False)
  if collision:c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
  if kind==4:c.set_material(0,grass.grass_material)
  if kind==2:
   for slot,m in enumerate(bindings[0]):c.set_material(slot,m)
  if kind in [0,1]:
   for slot in range(c.get_num_materials()):
    mat=c.get_material(slot)
    if mat and any(v in mat.get_name().lower() for v in ['leaf','leave','foliage']):c.set_material(slot,u.load_asset(OLD+'/Understory/MI_BirchBush'))
  report['ecology'].append(dict(kind=kind,mesh=path,count=len(ts),collision=collision));yield 1
 route=next(a for a in refs if isinstance(a,u.GTMudRoute));route.set_editor_property('title','BIG MOUNTAIN / woodland, wet hollows and shore trail');route.set_editor_property('recovery_points',[u.Transform(location=u.Vector(*a['center'],a['center_height_cm']+80),rotation=u.Rotator(yaw=a['yaw'])) for a in data['sites']])
 start=next(a for a in refs if isinstance(a,u.PlayerStart));a=data['sites'][0];start.set_actor_location(u.Vector(*a['center'],a['center_height_cm']+80),False,True)
 for a in refs:
  if isinstance(a,u.GTVehicleSurfaceEffects):assert a.dust_intensity==0
 assert les.save_current_level();yield 3
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(BASE+'/L_BigMountain')
 for path,d in protected.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==d
 report.update(ok=True,saved_and_reloaded=True,trees=len(trees),instances=len(entries),puddles=len(auth['puddles']),original_benmore_unchanged=True);save()
steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1100,'Update timeout'
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
