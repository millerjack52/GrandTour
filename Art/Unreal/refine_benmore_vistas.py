"""Sharpen distant material separation and add the lake's visual surface."""
import unreal as u,sys,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreVistas';sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build
from benmore_bank_surface import backdrop_material
from benmore_character_sky import build as skybuild
from benmore_vista_lake import build as lakebuild
les=u.get_editor_subsystem(u.LevelEditorSubsystem);phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(err=None):
    global phase
    phase='done';report['ok']=err is None
    if err:report['error']=err;u.log_error(err)
    (OUT/'refinement-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='building';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover');report['surface']=build(m);assert not u.MaterialEditingLibrary.recompile_material(m);u.EditorAssetLibrary.save_loaded_asset(m);backdrop_material();skybuild();report['lake']=lakebuild()
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>35:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
