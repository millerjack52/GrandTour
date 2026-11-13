"""Separate full-heightmap woodland level; original Benmore and water assets protected."""
import unreal as u
import json,sys,time,traceback,hashlib,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import benmore_woodland_materials as mat
OUT=ROOT/'Art/Export/BenmoreWoodland';BASE=mat.BASE;LEVEL=BASE+'/L_Benmore_Woodland'
SOURCE='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
data=json.loads((OUT/'authoring.json').read_text());report=dict(ok=False,level=LEVEL,driving_tested=False)
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def protected():
 paths=[ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap',ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/Morphology/DA_GC_WaterDomain.uasset']
 paths+=list((ROOT/'Content/GrandTour/Demo/BenmoreRoads/Gaea/NativeSurfaces').glob('M_NativeDomain*.uasset'))
 return {str(p.relative_to(ROOT)):digest(p) for p in paths}
def spawn(cls,label,p=(0,0,0)):
 a=actors.spawn_actor_from_class(cls,u.Vector(*p));a.set_actor_label('Woodland_'+label);return a
try:
 report['protected_before']=protected()
 target=ROOT/'Content/GrandTour/ArtTests/BenmoreWoodland'
 if target.exists():
  backup=ROOT/'Saved/BenmoreWoodlandBackups'/str(time.time_ns());shutil.copytree(target,backup);report['backup']=str(backup)
 if assets.does_asset_exist(LEVEL):assert les.load_level(LEVEL)
 else:
  assert les.load_level(SOURCE)
  assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
  assert les.load_level(LEVEL)
 world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 refs={a.get_actor_label():a for a in actors.get_all_level_actors()};land=next(a for a in refs.values() if isinstance(a,u.Landscape));sheet=next(a for a in refs.values() if isinstance(a,u.GTWaterSheet))
 keep=(u.Landscape,u.WorldSettings,u.GTWaterSheet,u.DirectionalLight,u.SkyLight,u.SkyAtmosphere,u.ExponentialHeightFog,u.PostProcessVolume,u.GTVehicleSurfaceEffects)
 report['removed_actors']=0
 for a in list(refs.values()):
  label=a.get_actor_label()
  if isinstance(a,keep) or label in ['Benmore_RL_Stream','Benmore_RL_Outlet','Benmore_Vista_Lake','Benmore_RL_MouthBed','Benmore_RL_Footbridge','Benmore_Character_SoftSky'] or label.startswith('Benmore_Hills_') or 'SkySphere' in a.get_class().get_name():continue
  if a.get_class().get_name() not in ['LevelScriptActor','Brush']:actors.destroy_actor(a);report['removed_actors']+=1
 world.get_world_settings().set_editor_property('default_game_mode',u.GTMudLabGameMode)
 for a in actors.get_all_level_actors():
  if isinstance(a,u.GTVehicleSurfaceEffects):a.set_editor_property('dust_intensity',0.)
 textures={n:mat.texture(n) for n in ['paint','rest','style','macro']}
 textures.update({n:mat.texture(n,True) for n in ['tiles_forest__d_a','tiles_rock_slope__d_a','tiles_dirt_dark__d_a']})
 mats={k:mat.soil(textures,k) for k in ['Terrain','Detail','Tread']}
 props(land,landscape_material=mats['Terrain'],use_dynamic_material_instance=True)
 for a in actors.get_all_level_actors():
  if a.get_actor_label().startswith('Benmore_Hills_'):a.static_mesh_component.set_material(0,mats['Terrain'])
 start=data['sites'][0];cx,cy=start['center']
 s=spawn(u.GTLandscapeSurface,'Ground',(cx,cy,0));s.landscape=land
 props(s,paint_origin_cm=u.Vector2D(*data['origin']),paint_size_cm=data['size'],enable_wheel_support=True,observe_player_wheels=True,follow_player=True,separate_visual_mesh=True,use_soil_shear_response=True,use_rut_interaction=True,use_native_mud_shader_updates=True,use_native_substance_response=True,use_native_water_response=True,extend_water_response_to_domain=True,maximum_layer_depth_cm=124.)
 s.set_editor_property('simulated_water',sheet);s.set_editor_property('layer_depth_scale',2.48)
 assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,textures['paint'])
 assert u.GTLandscapeSurfaceSetupLibrary.import_material_atlas(s,textures['style'])
 assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(s,textures['rest'])
 import benmore_mud_relief
 benmore_mud_relief.install(s)
 import benmore_woodland_detail
 report['soil_detail']=benmore_woodland_detail.install()
 import woodland_mud_clods
 report['native_clods']=woodland_mud_clods.install()
 v=spawn(u.GTMudRunnerVisual,'Detail',(cx,cy,0));props(v,surface=s,material=mats['Detail'],track_material=mats['Tread'],half_size_cm=2400.,hide_whole_landscape=False,follow_player_grid=True)
 d=spawn(u.GTMixedGroundDetails,'ShortGrass');props(d,surface=s,generate_around_player=True,grass_material=mat.grass())
 d.grass.set_static_mesh(assets.load_asset('/Game/GrandTour/ArtTests/MudRoad/MixedSurfaces/SM_NativeShortGrass'));d.grass.set_material(0,d.grass_material)
 d.grass.set_cull_distances(1800,2700);d.grass.set_editor_property('visible_in_ray_tracing',False)
 trees=json.loads((OUT/'trees.json').read_text());report['trees']=len(trees)
 forest=spawn(u.Actor,'Forest');trunks=[];fir_materials={}
 summer={line.split()[1]:line.split()[2] for line in (ROOT/'Art/dressing/retint_summer_map.txt').read_text().splitlines() if line.strip() and not line.startswith('#') and len(line.split())==3}
 for k in range(3):
  mesh=assets.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(k));assert mesh;b=mesh.get_bounds();ts=[]
  for x,y,z,kind,h,yaw in trees:
   if kind!=k:continue
   sc=h/(2*b.box_extent.z);ts.append(u.Transform(location=u.Vector(x,y,z-(b.origin.z-b.box_extent.z)*sc-8),rotation=u.Rotator(yaw=yaw),scale=u.Vector(sc,sc,sc)))
   trunks.append(u.Transform(location=u.Vector(x,y,z+220),scale=u.Vector(.35,.35,4.4)))
  c=u.GTVegetationSubsystem.add_tagged_instances(forest,mesh,ts,'WoodlandForest','NoCollision',True);c.set_cull_distances(45000,70000);c.set_editor_property('visible_in_ray_tracing',False)
  for slot in range(c.get_num_materials()):
   old=c.get_material(slot)
   if old and old.get_path_name() in summer:
    source_path=summer[old.get_path_name()]
    if source_path not in fir_materials:
     evergreen=assets.load_asset(source_path);assert evergreen;fir_materials[source_path]=mat.fir(evergreen)
    c.set_material(slot,fir_materials[source_path])
 c=u.GTVegetationSubsystem.add_tagged_instances(forest,assets.load_asset('/Engine/BasicShapes/Cylinder'),trunks,'WoodlandTrunks','BlockAll',False)
 c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
 fx=spawn(u.GTMudRunnerWheelEffects,'WheelEffects');fx.materials=[assets.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/M_'+n) for n in ['mud_small','mud_large','water_small','water_medium','water_large','water_fluid','mud_bits','water_drops','water_bits']];assert all(fx.materials)
 route=spawn(u.GTMudRoute,'Route');route.set_editor_property('title','BENMORE WOODLAND / forest tracks and wetlands');route.set_editor_property('checkpoint_labels','1 Forest road   2 River ford   3 Deep bog')
 route.set_editor_property('recovery_points',[u.Transform(location=u.Vector(*p['center'],p['center_height_cm']+80),rotation=u.Rotator(yaw=130 if p['name']=='Road' else 0)) for p in data['sites']])
 spawn(u.PlayerStart,'Start',(*start['center'],start['center_height_cm']+80)).set_actor_rotation(u.Rotator(yaw=130),False)
 for p in data['sites']:
  x,y=p['center'];z=p['center_height_cm'];camera=spawn(u.CameraActor,p['name']+'_Camera',(x+750,y-1050,z+520));camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(x,y,z+80)),False)
 assert les.save_current_level();assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 loaded=actors.get_all_level_actors();assert len([a for a in loaded if isinstance(a,u.GTLandscapeSurface)])==1
 report['protected_after']=protected();assert report['protected_before']==report['protected_after']
 report.update(ok=True,saved_and_reloaded=True,ground_area_km2=6.25,high_detail_area_m2=48*48)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'install.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
