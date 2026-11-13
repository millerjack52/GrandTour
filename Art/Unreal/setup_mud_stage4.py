"""Apply isolated stage-4 assets to the road; retain a complete pre-change backup."""
import sys,json,time,traceback,shutil,random,math
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path[:0]=[str(ROOT/'Art/Unreal'),str(ROOT/'Art/tools')]
from benmore_river_life_materials import props
from make_mud_road import centre
from mudrunner_stage4_materials import make
OUT=ROOT/'Art/Export/MudRoad/NativeStage4';BASE='/Game/GrandTour/ArtTests/MudRoad';LEVEL=BASE+'/L_MudRoad'
assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report=dict(ok=False)
try:
 backup=ROOT/'Saved/MudRoadStage4Backups'/str(time.time_ns());shutil.copytree(ROOT/'Content/GrandTour/ArtTests/MudRoad',backup);report['backup']=str(backup)
 assert les.load_level(LEVEL)
 surface=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
 visual=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
 ground,clod,track,grade=make(assets.load_asset(BASE+'/T_RoadPaint'),assets.load_asset(BASE+'/T_RoadRest'))
 visual.track_material=track
 pp=next((a for a in actors.get_all_level_actors() if a.get_actor_label()=='NativeDayGrade'),None) or actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
 pp.set_actor_label('NativeDayGrade');pp.set_editor_property('unbound',True);pp.set_editor_property('priority',100.)
 settings=pp.get_editor_property('settings');settings.set_editor_property('weighted_blendables',u.WeightedBlendables(array=[u.WeightedBlendable(weight=1.,object=grade)]));pp.set_editor_property('settings',settings)
 visual.material=ground;surface.landscape.landscape_material=ground;surface.use_native_substance_response=True
 for c in surface.landscape.get_components_by_class(u.MeshComponent):
  for i in range(c.get_num_materials()):c.set_material(i,ground)
 for a in list(actors.get_all_level_actors()):
  if a.get_actor_label().startswith('NativeMudClods_'):actors.destroy_actor(a)
 rng=random.Random(9640861);report['meshes']=[]
 for kind in ['a','b']:
  name='plants_mud_chunk_'+kind
  opts=props(u.FbxImportUI(),import_mesh=True,import_materials=False,import_textures=False,import_as_skeletal=False,mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH)
  props(opts.static_mesh_import_data,combine_meshes=True,auto_generate_collision=False,import_uniform_scale=1.,convert_scene=False,convert_scene_unit=False,normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
  task=props(u.AssetImportTask(),filename=str(OUT/(name+'.obj')),destination_path=BASE+'/NativeStage4',destination_name='SM_'+name,automated=True,replace_existing=True,save=True,options=opts)
  u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=assets.load_asset(BASE+'/NativeStage4/SM_'+name);assert mesh,name
  mesh.set_material(0,clod);assets.save_loaded_asset(mesh)
  b=mesh.get_bounds();report['meshes'].append(dict(name=name,size_cm=(b.box_extent*2).to_tuple()))
  actor=actors.spawn_actor_from_class(u.Actor,u.Vector());actor.set_actor_label('NativeMudClods_'+kind)
  ts=[]
  for _ in range(210 if kind=='a' else 65):
   x=rng.uniform(-2100,2100);offset=rng.choice([-1,1])*rng.uniform(125,260);y=centre(x)+offset
   # Imported source clods keep native scale; placement alone is road-authored.
   h=surface.sample_surface(u.Vector2D(x,y)).surface_delta_cm
   ts.append(u.Transform(location=u.Vector(x,y,h+(2.4 if kind=='a' else 1.8)),rotation=u.Rotator(yaw=rng.uniform(0,360))))
  c=u.GTVegetationSubsystem.add_tagged_instances(actor,mesh,ts,'NativeMudClod','NoCollision',True)
  c.set_material(0,clod)
 # Fog now belongs to the native scene compose, not a second UE height-fog pass.
 for fog in actors.get_all_level_actors():
  if isinstance(fog,u.ExponentialHeightFog):fog.set_actor_hidden_in_game(True)
 route=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMudRoute));route.set_editor_property('title','MUD ROAD / recovered mud colour and tire response')
 assert les.save_current_level()
 report.update(ok=True,level=LEVEL,native_substance=True,native_colour=True,scope='Mud Color PS, day LUT/fog, source clod meshes, source tread textures with a world-ribbon projector, physical byte field and recovered wheel impulses through Chaos; see IMPLEMENTATION.txt for remaining native seams')
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
surface=visual=ground=clod=route=None
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();quit_at=time.monotonic()+3
def tick(dt):
 if time.monotonic()>=quit_at:
  u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
  # The command-line Python executor releases its notification and defers exit.
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
