"""Extend the accepted road in place; never recreate the original mud tile."""
import unreal as u
import sys,json,time,traceback,shutil,random,math
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path[:0]=[str(ROOT/'Art/Unreal'),str(ROOT/'Art/tools')]
from benmore_river_life_materials import props
from make_mixed_route import ground,kind,route_y
import mixed_route_materials as mat
BASE=mat.BASE;OUT=mat.DATA;LEVEL='/Game/GrandTour/ArtTests/MudRoad/L_MudRoad'
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report=dict(ok=False)
try:
 backup=ROOT/'Saved/MixedRouteBackups'/str(time.time_ns());shutil.copytree(ROOT/'Content/GrandTour/ArtTests/MudRoad',backup);report['backup']=str(backup)
 assert les.load_level(LEVEL)
 original=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface) and not a.get_actor_label().startswith('MixedRoute_'))
 def signature(s):
  return dict(native=s.use_native_substance_response,shader=s.use_native_mud_shader_updates,shear=s.use_soil_shear_response,rut=s.use_rut_interaction,paint=s.paint_texture.get_path_name(),water=s.simulated_water.get_path_name(),level=s.simulated_water.base_level_cm)
 before=signature(original)
 old_land=None
 for a in list(actors.get_all_level_actors()):
  if a.get_actor_label().startswith('MixedRoute_'):
   if isinstance(a,u.Landscape):old_land=a
   else:actors.destroy_actor(a)
 def spawn(cls,label,pos=(0,0,0)):
  a=actors.spawn_actor_from_class(cls,u.Vector(*pos));a.set_actor_label('MixedRoute_'+label);return a
 textures={n:mat.texture(n) for n in ['paint','rest','style','macro','tiles_beach__d_a','tiles_beach_dark__d_a','overlays_wet_sand__d_a','overlays_wet_sand__s_d','grass_grass_short__d_a']}
 soil,track=mat.soil(textures['paint'],textures['rest'],textures['style'],textures['macro']);grass=mat.grass();grade=mat.grade()
 data=json.loads((OUT/'authoring.json').read_text());world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 land=old_land or u.GTLandscapeSurfaceSetupLibrary.create_study_landscape(world,soil,u.Vector(3150,-3150,0),data['heights_cm']);assert land
 land.landscape_material=soil
 surface=spawn(u.GTLandscapeSurface,'Surface');surface.landscape=land
 props(surface,paint_origin_cm=u.Vector2D(3150,-3150),paint_size_cm=6300.,enable_wheel_support=True,observe_player_wheels=True,follow_player=True,use_soil_shear_response=True,use_rut_interaction=True,use_native_mud_shader_updates=False,use_native_substance_response=False,use_native_water_response=True)
 assert u.GTLandscapeSurfaceSetupLibrary.import_paint(surface,textures['paint'])
 assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(surface,textures['rest'])
 def region(name,x,y,hx,hy,sand,wet,ellipse=False):
  return props(u.GTLandscapeMudRegion(),name=name,centre=u.Vector2D(x,y),half_size=u.Vector2D(hx,hy),granular=sand,elliptical=ellipse,grass_cover=0. if sand else 1.,wetness=wet,cohesion=.12 if sand else .7,relief=.15,fragment_scale=1.)
 surface.mud_regions=[region('Wet riverbank sand',4250,-450,1000,1450,True,.65,True),region('River sand',7325,0,575,3150,True,.65),region('Pond shore',5550,1550,1150,880,True,.65,True),region('Intact grass sod',6300,0,3150,3150,False,.3)]
 # Every water copy keeps the accepted equations and receives only this tile's input maps.
 def watermat(name):
  m=assets.load_asset(BASE+'/'+name) or assets.duplicate_asset('/Game/GrandTour/ArtTests/MudRoad/'+name,BASE+'/'+name);assert m
  for e in mel.get_material_expressions(m):
   if isinstance(e,u.MaterialExpressionTextureObjectParameter):
    key=str(e.get_editor_property('parameter_name'))
    if key=='GTLS_Paint':e.set_editor_property('texture',textures['paint'])
    if key=='GTLS_Rest':e.set_editor_property('texture',textures['rest'])
   if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':e.set_editor_property('default_value',u.LinearColor(3150,-3150,6300,0))
  assert not mel.recompile_material(m);assets.save_loaded_asset(m);return m
 water=watermat('M_LabWater');sim=watermat('M_LabWaterSim');sediment=watermat('M_LabWaterSediment')
 pond=spawn(u.GTWaterSheet,'Pond',(5550,1550,-5))
 props(pond,mud_surface=surface,mud_half_size_cm=1200.,mud_cell_cm=25.,base_level_cm=-5.,build_sleeping_mud_basin=True,surface_material_path=BASE+'/M_LabWater')
 pond.get_component_by_class(u.StaticMeshComponent).set_static_mesh(assets.load_asset('/Engine/BasicShapes/Cube'))
 pond.set_actor_scale3d(u.Vector(24,24,.1))
 surface.set_editor_property('simulated_water',pond)
 river=spawn(u.GTWaterSheet,'River',(7300,0,.1));river.get_component_by_class(u.StaticMeshComponent).set_static_mesh(assets.load_asset('/Engine/BasicShapes/Cube'))
 river.set_actor_scale3d(u.Vector(13,62,.1))
 river_material=mat.river(water)
 props(river,base_level_cm=.1,flow_direction=u.Vector2D(0,-1),flow_speed_cm_per_s=50.,head_drop_cm=12.,field_cell_cm=50.,wind_ripple_cm=8.,surface_material_path=BASE+'/M_NativeRiver')
 visual=spawn(u.GTMudRunnerVisual,'VisualGrid',(6300,0,0))
 props(visual,surface=surface,material=soil,track_material=track,water_sheet=pond,water_simulation_material=sim,sediment_simulation_material=sediment,wave_material=assets.load_asset('/Game/GrandTour/ArtTests/MudLab/M_LabWaves'))
 # Original source short-grass mesh, decoded from MeshCache polar vertices.
 opts=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
 props(opts.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,convert_scene=False,convert_scene_unit=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_COMPUTE_NORMALS)
 task=props(u.AssetImportTask(),filename=str(OUT/'grass_grass_short.obj'),destination_path=BASE,destination_name='SM_NativeShortGrass',automated=True,replace_existing=True,save=True,options=opts)
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=assets.load_asset(BASE+'/SM_NativeShortGrass');assert mesh
 mesh.set_material(0,grass);assets.save_loaded_asset(mesh);grass_bounds=(mesh.get_bounds().box_extent*2).to_tuple()
 details=spawn(u.GTMixedGroundDetails,'Grass');details.surface=surface;details.grass_material=grass;details.grass.set_static_mesh(mesh);details.grass.set_material(0,grass)
 rng=random.Random(9640861);transforms=[]
 for y0 in range(-3000,3001,36):
  for x0 in range(3250,9351,36):
   x=x0+rng.uniform(-14,14);y=y0+rng.uniform(-14,14)
   if kind(x,y)!=2 or ground(x,y)<6:continue
   # Two faint existing wheel lines make the intended grass crossing readable;
   # remaining plants still receive the same persistent contact state in play.
   road=abs(y-route_y(x));lane=min(abs(road-82),abs(road+82))
   if lane<35 and rng.random()<.68:continue
   sc=rng.uniform(.85,1.35)
   transforms.append(u.Transform(location=u.Vector(x,y,ground(x,y)+2),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)))
 details.grass.add_instances(transforms,False,True);details.grass.set_cull_distances(7000,12000)
 dust=spawn(u.GTDustLab,'SandDust');dust.granular_only=True;dust.intensity=.6
 dust.dust_system=assets.load_asset('/Game/GrandTour/ArtTests/DustLab/Build_20261012_155349/NS_DustLab');assert dust.dust_system
 # Sparse forest framing; no collision decor on the route or in water.
 trees=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='MudScene_Detail_trees'),None)
 if trees:
  dressing=spawn(u.Actor,'Trees')
  for c in trees.get_components_by_class(u.InstancedStaticMeshComponent):
   mesh=c.static_mesh;b=mesh.get_bounds();ts=[]
   for _ in range(26):
    x=rng.uniform(3350,9250);y=rng.uniform(-2950,2950)
    if abs(y-route_y(x))<900 or ground(x,y)<10 or 6750<x<7900:continue
    sc=rng.uniform(700,1100)/(2*b.box_extent.z)
    ts.append(u.Transform(location=u.Vector(x,y,ground(x,y)-(b.origin.z-b.box_extent.z)*sc-8),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)))
   if ts:u.GTVegetationSubsystem.add_tagged_instances(dressing,mesh,ts,'MixedRoute','NoCollision',True)
 # Open the last original-road shoulder into the extension.
 for a in actors.get_all_level_actors():
  if not a.get_actor_label().startswith(('MudScene_Detail_','MudRoad_Dressing')):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   for i in reversed(range(c.get_instance_count())):
    p=c.get_instance_transform(i,True).translation
    if p.x>2400 and abs(p.y-route_y(p.x))<450:c.remove_instance(i)
 pp=next(a for a in actors.get_all_level_actors() if a.get_actor_label()=='NativeDayGrade')
 settings=pp.settings;settings.set_editor_property('weighted_blendables',u.WeightedBlendables(array=[u.WeightedBlendable(weight=1.,object=grade)]));pp.settings=settings
 route=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMudRoute))
 points=list(route.get_editor_property('recovery_points'))[:3]
 for key in ['sand','grass','river']:
  x,y=data['probes'][key];yaw=math.degrees(math.atan(440/1300*math.cos((x-3150)/1300)))
  points.append(u.Transform(location=u.Vector(x,y,ground(x,y)+110),rotation=u.Rotator(yaw=yaw)))
 route.set_editor_property('recovery_points',points);route.set_editor_property('title','MIXED SURFACE ROAD / mud - sand - grass - water')
 route.set_editor_property('checkpoint_labels','1 Start  2 Puddles  3 Dip  4 Sand  5 Grass  6 River')
 assert signature(original)==before,'Original mud/water configuration changed'
 assert les.save_current_level()
 report.update(ok=True,level=LEVEL,original=before,grass_instances=len(transforms),height_range_cm=data['height_range_cm'],checkpoints=6,source_mesh_size_cm=grass_bounds)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
world=original=surface=land=visual=pond=river=details=route=trees=pp=None
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();quit_at=time.monotonic()+3
def finish(dt):
 if time.monotonic()>=quit_at:u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
