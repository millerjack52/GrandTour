"""Start the normal Benmore game in one PIE window, then run the shared profiler."""
import unreal as u
import os,sys,time,json,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['GT_BENMORE_PROFILE_OUT'])
u.EditorPythonScripting.set_keep_python_script_alive(True)


def start():
    assert not u.EditorLevelLibrary.get_game_world(), 'Another play session exists'
    world=u.EditorLoadingAndSavingUtils.load_map('/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview')
    assert world
    # Leave the authored game mode, pawn, HUD and audio intact. The offscreen
    # virtual desktop must be large enough for the requested PIE client area.
    u.SystemLibrary.execute_console_command(world,'r.SetRes 1920x1080w')
    yield 2
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,898)
    yield 20
    assert u.EditorLevelLibrary.get_game_world()


gen=start()
next_at=time.monotonic()
busy=False


def tick(dt):
    global busy,next_at
    if busy:return
    busy=True
    try:
        if time.monotonic()>=next_at:next_at=time.monotonic()+next(gen)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle)
        sys.path.insert(0,str(ROOT/'Art/Unreal'))
        import profile_benmore_game
    except Exception:
        error=traceback.format_exc()
        (OUT/'profile-report.json').write_text(json.dumps(dict(ok=False,error=error,target_verified=False),indent=2))
        u.log_error(error)
        u.unregister_slate_post_tick_callback(handle)
        if u.EditorLevelLibrary.get_game_world():u.EditorLevelLibrary.editor_end_play()
        u.SystemLibrary.quit_editor()
    finally:busy=False


handle=u.register_slate_post_tick_callback(tick)
