import unreal as u,sys,json,time,os,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
import lidar_first_section as S
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
STAGE=os.environ.get('GT_CD_STAGE','install');busy=False;deadline=0;report=dict(ok=False)
def run():
 if STAGE=='install':C.protect();C.finalize_bounds();yield 2
 assert les.load_level(C.BASE+'/L_LidarStudy');yield 3
 if STAGE=='install':
  before=dict(local=S.snapshot(),outside=S.outside_snapshot())
  ground=next(a for a in C.actors.get_all_level_actors() if isinstance(a,u.GTProceduralGround));digest=str(ground.output_digest)
  report['forest']=C.apply()
  assert before==dict(local=S.snapshot(),outside=S.outside_snapshot())
  assert str(ground.output_digest)==digest
  report.update(**before,ground_digest=digest,protected_packages=C.validate_protected())
  assert les.save_current_level()
  recipe=json.loads((C.OUT/'recipe.json').read_text()) if (C.OUT/'recipe.json').exists() else {}
  recipe.update(enabled=True,version=1,coverage='Broader connected crowns at unchanged tree bases',representation='24 elevation-aware depth-reprojected views; 2 triangles per far tree',scope='LidarStudy_Forest, living species only')
  (C.OUT/'recipe.json').write_text(json.dumps(recipe,indent=2))
 else:
  saved=json.loads((C.QA/'install-result.json').read_text());assert saved['ok']
  assert S.snapshot()==saved['local'];assert S.outside_snapshot()==saved['outside']
  forest=next(a for a in C.actors.get_all_level_actors() if a.get_actor_label()=='LidarStudy_Forest')
  rows=[]
  for row in saved['forest']:
   c=next(c for c in forest.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name()==row['component'])
   assert C.fingerprint(c)==dict(count=row['count'],transforms=row['transforms'])
   assert c.static_mesh.get_path_name()==row['mesh']
   assert c.get_editor_property('world_position_offset_disable_distance')==0
   assert C.sm.get_lod_count(c.static_mesh)==4
   assert C.sm.get_number_verts(c.static_mesh,3)==4
   rows.append(row)
  report.update(forest=rows,protected_packages=C.validate_protected(),saved_reload=True,motion=C.motion_sequence(),lighting=C.export_lighting())
 report['ok']=True;yield 1
steps=run()
def tick(dt):
 global busy,deadline
 if busy or time.monotonic()<deadline:return
 busy=True
 try:deadline=time.monotonic()+float(next(steps))
 except StopIteration:
  (C.QA/(STAGE+'-result.json')).write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 except Exception:
  report.update(ok=False,error=traceback.format_exc());(C.QA/(STAGE+'-result.json')).write_text(json.dumps(report,indent=2));u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
 finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
