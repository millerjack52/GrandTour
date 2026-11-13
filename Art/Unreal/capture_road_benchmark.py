"""Rendered review in a task-owned offscreen editor. Starts SIE for the existing runtime look subsystem."""
import json,time,traceback
from pathlib import Path
import unreal as u
u.EditorPythonScripting.set_keep_python_script_alive(True)
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/RoadBenchmark'
start=time.monotonic(); phase=0; last=start
report={'ok':False,'screenshots':[],'method':'SIE with runtime GTLookSubsystem'}
def finish(error=None):
    if error: report['error']=error
    report['finished']=True
    (OUT/'capture-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle)
    u.EditorLevelLibrary.editor_end_play()
    u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,shot_task
    now=time.monotonic()
    try:
        if now-start>240: finish('Capture timed out'); return
        if phase==0 and now-start>10:
            u.EditorLevelLibrary.editor_play_simulate(); phase=1; last=now
        elif phase in [1,3] and now-last>35:
            world=u.EditorLevelLibrary.get_game_world()
            if not world: return
            name='RB_DriverReview' if phase==1 else 'RB_Overview'
            cameras=u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor)
            camera=next(a for a in cameras if a.get_actor_label()==name)
            filename=OUT/('Unreal_'+name+'.png')
            # Screenshot setup pumps Slate while it waits for shaders: advance before that re-entry.
            report['screenshots'].append(str(filename)); phase+=1; last=now
            shot_task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(filename),camera=camera,delay=2.0)
        elif phase in [2,4] and now-last>10:
            if not Path(report['screenshots'][-1]).exists(): return
            if phase==4:
                report['ok']=True; finish(); return
            phase=3; last=now
    except Exception:
        finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
u.log('ROAD_BENCHMARK_CAPTURE registered')
