"""Install the dry-bank art pass and review the saved river at several scales."""
import unreal as u,sys,time,json,traceback,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRivers'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_bank_art import apply_art,check_support
les=u.get_editor_subsystem(u.LevelEditorSubsystem);phase='load';last=time.monotonic();started=last
u.EditorPythonScripting.set_keep_python_script_alive(True)
def tick(dt):
    global phase,last,report
    try:
        if time.monotonic()-started>480:raise RuntimeError('River bank installation timed out')
        if phase=='load':
            phase='loading';assert les.load_level('/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            for name in ['River_Close','River_Reach','River_Overlook']:
                src=OUT/(name+'.png');dst=OUT/('Before_BankArt_'+name+'.png')
                if src.exists() and not dst.exists():shutil.copy2(src,dst)
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>8:
            phase='install';world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            backup='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeRiverBankArt'
            if not u.EditorAssetLibrary.does_asset_exist(backup):assert u.EditorLoadingAndSavingUtils.save_map(world,backup)
            report=apply_art(world);phase='validate';last=time.monotonic()
        elif phase=='validate' and time.monotonic()-last>12:
            # Saving pumps Slate; guard before calling it to avoid recursively
            # entering this callback and attempting a second save.
            phase='saving'
            check_support(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),report)
            assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),'/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive')
            if (OUT/'bank-art-error.txt').exists():(OUT/'bank-art-error.txt').unlink()
            phase='done';u.unregister_slate_post_tick_callback(handle)
            p=ROOT/'Art/Unreal/check_benmore_rivers.py';exec(compile(p.read_text(),str(p),'exec'),{'__file__':str(p)})
    except Exception:
        (OUT/'bank-art-error.txt').write_text(traceback.format_exc());u.log_error(traceback.format_exc());u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
handle=u.register_slate_post_tick_callback(tick)
