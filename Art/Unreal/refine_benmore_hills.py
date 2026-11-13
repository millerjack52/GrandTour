"""Retune hill materials only; keep the verified new scenery meshes."""
import unreal as u,sys,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_reference_surface import build
from benmore_bank_surface import backdrop_material
OUT=ROOT/'Art/Export/BenmoreHills';les=u.get_editor_subsystem(u.LevelEditorSubsystem)
phase='load';last=time.monotonic();report={'ok':False};u.EditorPythonScripting.set_keep_python_script_alive(True)
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
            mat=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            report['surface']=build(mat);assert not u.MaterialEditingLibrary.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat);backdrop_material()
            # Record numeric texture settings to catch unexpected import/downsampling.
            report['textures']={}
            for name in ['T_Benmore_HillNormal','T_Benmore_HillStructure']:
                t=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Hills/'+name)
                report['textures'][name]={'width':t.blueprint_get_size_x(),'height':t.blueprint_get_size_y(),'srgb':t.get_editor_property('srgb'),'compression':str(t.get_editor_property('compression_settings'))}
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>40:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
