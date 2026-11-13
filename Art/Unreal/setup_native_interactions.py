"""Update the current mixed route in place. Full map/content backup before editing."""
import unreal as u
import sys,json,time,traceback,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import native_interaction_materials as mat
BASE='/Game/GrandTour/ArtTests/MudRoad';OUT=ROOT/'Art/Export/MudRoad/NativeInteractions'
assets=u.EditorAssetLibrary;actors=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
report=dict(ok=False)
try:
 backup=ROOT/'Saved/NativeInteractionBackups'/str(time.time_ns());shutil.copytree(ROOT/'Content/GrandTour/ArtTests/MudRoad',backup);report['backup']=str(backup)
 assert les.load_level(BASE+'/L_MudRoad')
 textures,materials=mat.make();soil,track=mat.shore_materials();mat.terrain_oracle()
 allactors=actors.get_all_level_actors()
 for a in allactors:
  if isinstance(a,u.GTLandscapeSurface):
   a.use_native_water_response=True
   if a.get_actor_label()=='MixedRoute_Surface':
    regions=list(a.mud_regions)
    for r in regions:
     if r.granular:r.wetness=.65;r.name='Wet riverbank sand'
    a.mud_regions=regions;a.landscape.landscape_material=soil
  if isinstance(a,u.GTMudRunnerVisual) and a.get_actor_label().startswith('MixedRoute_'):a.material=soil;a.track_material=track
 fx=next((a for a in allactors if isinstance(a,u.GTMudRunnerWheelEffects)),None) or actors.spawn_actor_from_class(u.GTMudRunnerWheelEffects,u.Vector())
 fx.set_actor_label('NativeWheelInteractions');fx.materials=materials
 se=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);count=0;hulls=[]
 for a in allactors:
  if not a.get_actor_label().startswith('NativeMudClods_'):continue
  for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
   if not c.component_has_tag('NativeMudClod'):continue
   source=c.static_mesh;name=source.get_name();path=mat.BASE+'/'+name
   mesh=assets.load_asset(path) or assets.duplicate_asset(source.get_path_name().split('.')[0],path)
   se.remove_collisions(mesh);assert se.set_convex_decomposition_collisions(mesh,1,32,100000)
   assert se.get_convex_collision_count(mesh)>0;assets.save_loaded_asset(mesh)
   hulls.append(dict(mesh=mesh.get_path_name(),hulls=se.get_convex_collision_count(mesh)))
   for i in range(c.get_instance_count()):
    t=c.get_instance_transform(i,True)
    clod=actors.spawn_actor_from_class(u.GTMudRunnerClod,t.translation,t.rotation.rotator())
    clod.set_actor_label('NativePhysicalClod_'+str(count));clod.large=name.endswith('_b')
    clod.body.set_static_mesh(mesh);clod.body.set_collision_profile_name('BlockAllDynamic');clod.set_actor_scale3d(t.scale3d)
    count+=1
  actors.destroy_actor(a)
 report['converted_clods']=count;report['hulls']=hulls
 # Rocks left in the verge are solid too. Preserve their existing placements.
 report['verge_rock_components']=0
 for a in actors.get_all_level_actors():
  if a.get_actor_label().startswith('MudScene_Detail_') and 'rock' in a.get_actor_label().lower():
   for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
    if c.static_mesh:
     source=c.static_mesh;path=mat.BASE+'/'+source.get_name()+'_Solid'
     mesh=assets.load_asset(path) or assets.duplicate_asset(source.get_path_name().split('.')[0],path)
     if se.get_convex_collision_count(mesh)==0:assert se.set_convex_decomposition_collisions(mesh,1,32,100000)
     assets.save_loaded_asset(mesh);c.set_static_mesh(mesh);c.set_collision_profile_name('BlockAll');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
     report['verge_rock_components']+=1
 assert les.save_current_level();report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
fx=soil=track=a=c=clod=mesh=None;allactors=[]
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();until=time.monotonic()+3
def tick(dt):
 if time.monotonic()>=until:u.unregister_slate_post_tick_callback(handle);u.EditorPythonScripting.set_keep_python_script_alive(False)
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
