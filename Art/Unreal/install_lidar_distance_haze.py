"""Save and reload the distance fog revision without regenerating the level."""
import unreal as u,json,sys,time,traceback,gc
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
import lidar_first_section as S
import lidar_forest_atmosphere as A
QA=ROOT/'Saved/LidarAuthoringQA/DistanceHaze';QA.mkdir(exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);report=dict(ok=False);busy=False;deadline=0

def state():
 actors=C.actors.get_all_level_actors()
 forest=next(a for a in actors if a.get_actor_label()=='LidarStudy_Forest')
 return dict(local=S.snapshot(),outside=S.outside_snapshot(),
  forest={c.get_name():C.fingerprint(c) for c in forest.get_components_by_class(u.InstancedStaticMeshComponent)},
  ground=[str(a.output_digest) for a in actors if isinstance(a,u.GTProceduralGround)],
  sun=[dict(rotation=[a.get_actor_rotation().pitch,a.get_actor_rotation().yaw,a.get_actor_rotation().roll],intensity=a.light_component.intensity) for a in actors if isinstance(a,u.DirectionalLight)])

def fog_values():
 a=next(a for a in C.actors.get_all_level_actors() if isinstance(a,u.ExponentialHeightFog));c=a.component
 return dict(height=a.get_actor_location().z,**{k:c.get_editor_property(k) for k in ['fog_density','fog_height_falloff','start_distance','fog_max_opacity','enable_volumetric_fog']},luminance=[c.fog_inscattering_luminance.r,c.fog_inscattering_luminance.g,c.fog_inscattering_luminance.b])

def run():
 assert les.load_level(C.BASE+'/L_LidarStudy');yield 2
 before=state();report['before']=fog_values();report['settings']=A.apply_global_fog();report['after']=fog_values()
 assert state()==before
 report['protected_packages']=C.validate_protected()
 assert les.save_current_level();report['saved']=True
 assert les.load_level('/Engine/Maps/Entry');gc.collect();yield 3
 assert les.load_level(C.BASE+'/L_LidarStudy');yield 2
 assert fog_values()==report['after'];assert state()==before
 report.update(ok=True,saved_reload=True,planting_ground_and_sun_unchanged=True)
 yield 1

steps=run()
def tick(dt):
 global busy,deadline
 if busy or time.monotonic()<deadline:return
 busy=True
 try:deadline=time.monotonic()+float(next(steps))
 except StopIteration:
  (QA/'install.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());(QA/'install.json').write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
