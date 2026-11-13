import unreal as u,json,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import canopy_depth as C
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(C.BASE+'/L_LidarStudy')
rows=[]
for a in C.actors.get_all_level_actors():
 for c in a.get_components_by_class(u.StaticMeshComponent):
  m=c.static_mesh
  if not m or not any(x in m.get_name().lower() for x in ['canopy','beech','fir','tree']):continue
  r=dict(actor=a.get_actor_label(),component=c.get_name(),mesh=m.get_path_name(),materials=[str(c.get_material(i)) for i in range(c.get_num_materials())],forced_lod=c.get_editor_property('forced_lod_model'))
  for key in ['use_gpu_lod_selection','instance_lod_distance_scale','override_min_lod','min_lod_model','visible','hidden_in_game']:
   try:r[key]=str(c.get_editor_property(key))
   except Exception:pass
  if isinstance(c,u.InstancedStaticMeshComponent):r['count']=c.get_instance_count();r['sample']=str(c.get_instance_transform(0,True))
  try:r['auto_lod']=str(m.get_editor_property('auto_compute_lod_screen_size'))
  except Exception:pass
  rows.append(r)
(C.QA/'world-probe.json').write_text(json.dumps(rows,indent=2));u.SystemLibrary.quit_editor()
