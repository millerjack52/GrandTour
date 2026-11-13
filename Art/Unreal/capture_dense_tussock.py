"""Engine-only comparison: distance simplification cannot be checked in Blender."""
import unreal as u, json, time, traceback, sys
from pathlib import Path
OUT=Path(u.Paths.project_dir()).resolve()/'Art/Export/DenseTussock'
debug='-DTDenseDebug' in u.SystemLibrary.get_command_line()
sys.path.insert(0,str(Path(u.Paths.project_dir()).resolve()/'Art/Unreal'))
from dense_tussock_material import configure
if not debug: configure(u.EditorAssetLibrary.load_asset('/Game/GrandTour/ArtTests/DenseTussock/M_DT_Foliage'))
u.EditorPythonScripting.set_keep_python_script_alive(True)
jobs=[(mode,view) for view in ['Driver','Overview'] for mode in ['LOD','Voxel','Preserve']]
if debug: jobs=[('Voxel','Overview')]
index=0; phase='load'; last=time.monotonic(); start=last
report={'ok':False,'images':[]}
def finish(error=None):
    if error: report['error']=error
    (OUT/('voxel-debug-report.json' if debug else 'capture-report.json')).write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle)
    u.EditorLevelLibrary.editor_end_play(); u.SystemLibrary.quit_editor()
def tick(dt):
    global index,phase,last,shot,shot_started
    now=time.monotonic()
    try:
        if now-start>600: finish('Timed out'); return
        if phase=='load':
            phase='loaded'; last=now
            mode,view=jobs[index]
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GrandTour/ArtTests/DenseTussock/L_DT_'+mode+'_'+view)
        elif phase=='loaded' and now-last>8:
            phase='playing'; last=now; u.EditorLevelLibrary.editor_play_simulate()
        elif phase=='playing' and now-last>20:
            world=u.EditorLevelLibrary.get_game_world()
            if not world: return
            mode,view=jobs[index]
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='DT_'+view)
            filename=OUT/('UE_'+mode+'_'+view+'.png')
            if debug:
                filename=OUT/'UE_Voxel_Debug.png'
                u.SystemLibrary.execute_console_command(world,'r.Nanite.Visualize Voxels')
            phase='capturing'; last=now
            shot_started=time.time()
            report['images'].append(str(filename))
            shot=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(filename),camera=camera,delay=2)
            phase='shot'; last=time.monotonic()
        elif phase=='shot' and now-last>8:
            output=Path(report['images'][-1])
            if not output.exists() or output.stat().st_mtime<shot_started: return
            phase='ended'; last=now; u.EditorLevelLibrary.editor_end_play()
        elif phase=='ended' and now-last>4:
            index+=1
            if index==len(jobs): report['ok']=True; finish(); return
            phase='load'
    except Exception: finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
