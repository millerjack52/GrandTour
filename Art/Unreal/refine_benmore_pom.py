"""Rebuild existing Benmore POM shading without reimporting textures."""
import unreal as u,json,sys,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build
report={'ok':False}
try:
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
    m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover');report.update(build(m))
    errors=u.MaterialEditingLibrary.recompile_material(m);assert not errors,str(errors)
    assert u.EditorAssetLibrary.save_loaded_asset(m);assert les.save_current_level();report['ok']=True
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(ROOT/'Art/Export/BenmorePOM/setup-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
