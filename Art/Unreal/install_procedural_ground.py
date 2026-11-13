"""Install editable tools on a separate copy of Big Mountain. No STG imports."""
import unreal as u
from pathlib import Path
import json,time,traceback,hashlib,math
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/ProceduralGround';OUT.mkdir(parents=True,exist_ok=True)
BASE='/Game/GrandTour/ArtTests/ProceduralGround';OLD='/Game/GrandTour/ArtTests/BigMountain';LEVEL=BASE+'/L_BigMountain_Authoring'
assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem);mel=u.MaterialEditingLibrary
report=dict(ok=False,driving_tested=False);busy=False
def save():(OUT/'install.json').write_text(json.dumps(report,indent=2))
def props(o,**kw):
 for k,v in kw.items():o.set_editor_property(k,v)
 return o
def spawn(cls,label,pos=(0,0,0)):
 a=actors.spawn_actor_from_class(cls,u.Vector(*pos));a.set_actor_label(label);return a
def copy(path,name):
 if assets.does_asset_exist(BASE+'/'+name):return u.load_asset(BASE+'/'+name)
 a=assets.duplicate_asset(path,BASE+'/'+name);assert a;return a
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run():
 previous=OUT/'install.json'
 assert not(previous.exists() and json.loads(previous.read_text()).get('ok')),'Existing completed authoring map retained; use its Rebuild button'
 paths=[]
 for folder in ['BigMountain','BenmoreWoodland','NativeRoad']:
  paths+=list((ROOT/'Content/GrandTour/ArtTests'/folder).rglob('*.uasset'))+list((ROOT/'Content/GrandTour/ArtTests'/folder).rglob('*.umap'))
 report['protected']={str(p.relative_to(ROOT)):digest(p) for p in paths};save()
 assert les.load_level(OLD+'/L_BigMountain');world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
 assets.make_directory(BASE)
 if not assets.does_asset_exist(LEVEL):assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
 assert les.load_level(LEVEL);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();assert BASE in world.get_path_name(),world.get_path_name()
 refs=list(actors.get_all_level_actors());land=next(a for a in refs if isinstance(a,u.Landscape));surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface));visual=next(a for a in refs if isinstance(a,u.GTMudRunnerVisual))
 tex={n:copy(OLD+'/T_'+n,'T_'+n) for n in ['paint','style','macro']}
 mats={n:copy(OLD+'/M_'+n,'M_'+n) for n in ['Terrain','Detail','Tread']}
 for mat in mats.values():
  for e in mel.get_material_expressions(mat):
   if isinstance(e,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSample)):
    t=e.get_editor_property('texture')
    if t and t.get_name()[2:] in tex:e.set_editor_property('texture',tex[t.get_name()[2:]])
  assert not mel.recompile_material(mat);assert assets.save_loaded_asset(mat)
 land.set_editor_property('landscape_material',mats['Terrain']);visual.material=mats['Detail'];visual.track_material=mats['Tread'];surface.paint_texture=tex['paint']
 route=json.loads((ROOT/'Art/Export/BigMountain/route.json').read_text());length=0;points=[];last=route[0];next_sample=0
 for point in route:
  length+=math.dist(last,point);last=point
  if length>=next_sample:points.append(point);next_sample+=5000
  if length>=50000:break
 assert len(points)>=8
 xs=[p[0] for p in points];ys=[p[1] for p in points];cx=(max(xs)+min(xs))/2;cy=(max(ys)+min(ys))/2
 ex=(max(xs)-min(xs))/2+6500;ey=(max(ys)-min(ys))/2+6500
 author=spawn(u.GTProceduralGround,'Ground Authoring - select for Capture Rebuild Clear',(cx,cy,0))
 props(author,landscape=land,surface=surface,seed=962,output_asset_root=BASE+'/',paint_texture=tex['paint'],style_texture=tex['style'],macro_texture=tex['macro'])
 author.generation_bounds.set_box_extent(u.Vector(ex,ey,20000),False)
 # Clear old one-off scatter inside this study's baseline only. All output from
 # this point on belongs to the new tools. Original map assets remain untouched.
 removed=0
 for a in refs:
  if a.get_actor_label() not in ['BigMountain_Forest','BigMountain_Ecology','BigMountain_Understory']:continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   ids=[]
   for i in range(c.get_instance_count()):
    p=c.get_instance_transform(i,True).translation
    if abs(p.x-cx)<ex and abs(p.y-cy)<ey:ids.append(i)
   if ids:assert c.remove_instances(sorted(ids,reverse=True));removed+=len(ids)
 report['previous_scatter_removed_in_study']=removed
 rules=[]
 specs=[('Fir', ['/Game/GrandTour/ArtTests/BenmoreWoodland/Forest/SM_Fir_'+str(i) for i in range(3)],4,.32,.7,1.2,250,False,False,35000),
 ('Understory',['/Game/GrandTour/ArtTests/BenmoreWoodland/Understory/SM_BirchBush'],26,.42,.65,1.5,30,False,False,22000),
 ('MudClods',['/Game/GrandTour/ArtTests/MudRoad/NativeInteractions/SM_plants_mud_chunk_'+s for s in ['a','b']],12,.15,.6,1.3,0,True,True,15000)]
 for name,paths,budget,density,lo,hi,clearance,solid,road,cull in specs:
  meshes=[u.load_asset(p) for p in paths];assert all(meshes),paths
  rules.append(props(u.GTGroundScatterRule(),name=name,meshes=meshes,candidate_budget=budget,density=density,minimum_scale=lo,maximum_scale=hi,road_clearance_cm=clearance,solid=solid,road_debris=road,cull_distance_cm=cull))
 author.scatter_rules=rules
 forest=next(a for a in refs if a.get_actor_label()=='BigMountain_Forest')
 fir=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.static_mesh and c.static_mesh.get_name()=='SM_Fir_0')
 rules[0].material_overrides=list(fir.get_materials())
 rules[1].mesh_height_cm=145.;bush=rules[1].meshes[0]
 rules[1].material_overrides=[u.load_asset('/Game/GrandTour/ArtTests/BenmoreWoodland/Understory/MI_BirchBush') if any(s in bush.get_material(i).get_name().lower() for s in ['leaf','leave','foliage']) else bush.get_material(i) for i in range(bush.get_num_sections(0))]
 rules[2].material_overrides=[u.load_asset('/Game/GrandTour/ArtTests/MudRoad/NativeStage4/M_NativeClod')]
 author.scatter_rules=rules
 assert author.capture_base(),author.last_message
 road=spawn(u.GTProceduralRoad,'Road 01 - edit control points then Rebuild',(cx,cy,0))
 road.author=author;road.control_points.clear_spline_points(False)
 for i,(x,y) in enumerate(points):
  z=author.base_height_at(u.Vector2D(x,y));road.control_points.add_spline_point(u.Vector(x,y,z),u.SplineCoordinateSpace.WORLD,False)
  road.control_points.set_scale_at_spline_point(i,u.Vector(1,1+.12*math.sin(i*1.7),1),False)
 road.control_points.update_spline()
 props(road,width_cm=850.,bed_depth_cm=18.,mud_depth_cm=28.,wetness=.46)
 wet=points[len(points)//2];region=spawn(u.GTProceduralGroundRegion,'Wet ground - editable regional mask',(*wet,author.base_height_at(u.Vector2D(*wet))))
 props(region,author=author,kind=u.GTGroundRegionKind.WET_GROUND,grass_cover=.25,mud_depth_cm=36.,wetness=.88)
 region.bounds.set_box_extent(u.Vector(4800,3200,500),False);region.set_actor_rotation(u.Rotator(yaw=25),False)
 woodland=spawn(u.GTProceduralGroundRegion,'Woodland - editable density mask',(cx,cy+3500,author.base_height_at(u.Vector2D(cx,cy+3500))))
 props(woodland,author=author,kind=u.GTGroundRegionKind.WOODLAND,grass_cover=.85);woodland.bounds.set_box_extent(u.Vector(ex*.65,ey*.7,500),False)
 assert author.rebuild(),author.last_message;report['first_digest']=author.output_digest;report['first_cells']=author.generated_cell_count();report['instances']=author.instance_count;save();yield 8
 start=points[1];z=author.base_height_at(u.Vector2D(*start));yaw=math.degrees(math.atan2(points[2][1]-start[1],points[2][0]-start[0]))
 route_actor=next(a for a in refs if isinstance(a,u.GTMudRoute));recovery=[]
 for index in [1,len(points)//2,len(points)-2]:
  x,y=points[index];p=land.get_height_at_location(u.Vector(x,y,0)) if hasattr(land,'get_height_at_location') else None
  zz=author.base_height_at(u.Vector2D(x,y))
  recovery.append(u.Transform(location=u.Vector(x,y,zz+100),rotation=u.Rotator(yaw=yaw)))
 props(route_actor,title='BIG MOUNTAIN / procedural authoring study',recovery_points=recovery)
 for a in refs:
  if isinstance(a,u.PlayerStart):a.set_actor_location(u.Vector(*start,z+100),False,True);a.set_actor_rotation(u.Rotator(yaw=yaw),False)
  if isinstance(a,u.GTVehicleSurfaceEffects):assert a.dust_intensity==0
 for t in tex.values():assert assets.save_loaded_asset(t)
 assert les.save_current_level();yield 3
 assert les.load_level('/Engine/Maps/Entry');assert les.load_level(LEVEL)
 author=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));assert author.b_has_base if hasattr(author,'b_has_base') else author.get_editor_property('has_base')
 for path,sha in report['protected'].items():assert digest(ROOT/path)==sha,path
 report.update(ok=True,level=LEVEL,road_points=points,bounds=[cx,cy,ex,ey],protected_unchanged=True,saved_and_reloaded=True);save()
 les.load_level('/Engine/Maps/Entry');yield 5
steps=run();deadline=0;began=time.monotonic()
def tick(dt):
 global deadline,busy
 if busy:return
 busy=True
 try:
  assert time.monotonic()-began<1000
  if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
 except StopIteration:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
