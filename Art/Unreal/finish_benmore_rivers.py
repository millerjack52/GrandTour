"""Increase bank aggregate scale after the first in-engine review."""
import unreal as u,time,json,traceback,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRivers';DEST='/Game/GrandTour/Demo/BenmoreRoads/Rivers'
u.EditorPythonScripting.set_keep_python_script_alive(True);phase='load';last=time.monotonic()
def tick(dt):
    global phase,last
    try:
        if phase=='load':
            phase='edit';assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            if not (OUT/'Before_GravelRefinement.png').exists():shutil.copy2(OUT/'River_Close.png',OUT/'Before_GravelRefinement.png')
            for name in ['M_Benmore_RiverBank','M_Benmore_RiverTerrain']:
                m=u.load_asset(DEST+'/'+name);changed=0
                for n in u.MaterialEditingLibrary.get_material_expressions(m):
                    if not isinstance(n,u.MaterialExpressionCustom):continue
                    code=n.get_editor_property('code')
                    if code=='return P.xy/420;':n.set_editor_property('code','return P.xy/1250;');changed+=1
                    if name=='M_Benmore_RiverBank' and 'Detail.xy*.38' in code:n.set_editor_property('code',code.replace('Detail.xy*.38','Detail.xy*.52'));changed+=1
                assert not u.MaterialEditingLibrary.recompile_material(m);assert u.EditorAssetLibrary.save_loaded_asset(m)
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>20:
            phase='done';u.unregister_slate_post_tick_callback(handle)
            p=ROOT/'Art/Unreal/check_benmore_rivers.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
    except Exception:
        (OUT/'refinement-error.txt').write_text(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
