import unreal as u
from pathlib import Path
import json,traceback
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreWoodland';report={'ok':False}
try:
 assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/BenmoreWoodland/L_Benmore_Woodland')
 sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem);report['meshes']=[]
 for i in range(3):
  m=u.load_asset('/Game/GrandTour/ArtTests/SiberianShowcase/SM_Fir_'+str(i));n=sm.get_lod_count(m)
  report['meshes'].append(dict(path=m.get_path_name(),lods=n,verts=[sm.get_number_verts(m,j) for j in range(n)],screens=list(sm.get_lod_screen_sizes(m)),nanite=m.get_editor_property('nanite_settings').enabled,materials=[x.material_interface.get_path_name() for x in m.static_materials]))
 report['api']={n:str(getattr(sm,n).__doc__) for n in ['set_lods','set_lod_screen_sizes','set_lod_from_static_mesh']}
 report['ok']=True
except Exception:report['error']=traceback.format_exc()
(OUT/'forestaudit.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
