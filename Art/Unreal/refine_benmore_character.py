"""Rebuild only the character pass materials/sky, retaining placed dressing."""
import unreal as u, sys, json, time, traceback
from pathlib import Path
root=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(root/'Art/Unreal'))
from benmore_reference_surface import build
from benmore_bank_surface import backdrop_material
from benmore_character_sky import build as skybuild
out=root/'Art/Export/BenmoreCharacter';les=u.get_editor_subsystem(u.LevelEditorSubsystem)
phase='load';last=time.monotonic();report={'ok':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (out/'refinement-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='working';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            mat=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            report['surface']=build(mat);assert not u.MaterialEditingLibrary.recompile_material(mat)
            u.EditorAssetLibrary.save_loaded_asset(mat);backdrop_material();report['sky']=skybuild()
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>25:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
