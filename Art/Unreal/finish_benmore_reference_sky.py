"""Soften excessive cloud edge fragmentation and recapture both saved viewpoints."""
import unreal as u,sys,time,json,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreReferenceVistas';sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_character_sky import build
les=u.get_editor_subsystem(u.LevelEditorSubsystem);phase='load';last=time.monotonic();u.EditorPythonScripting.set_keep_python_script_alive(True)
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='building';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive');build();phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>20:
            phase='saving';assert les.save_current_level();u.unregister_slate_post_tick_callback(handle)
            # The gameplay checks run on the saved result in this same editor session.
            s=(ROOT/'Art/Unreal/check_benmore_reference_vistas.py').read_text();exec(compile(s,str(ROOT/'Art/Unreal/check_benmore_reference_vistas.py'),'exec'),{'__file__':str(ROOT/'Art/Unreal/check_benmore_reference_vistas.py')})
    except Exception:
        phase='error';u.log_error(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
