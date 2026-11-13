"""Private copies of the accepted shared-water scene; no baseline asset edits."""
import hashlib,json,shutil,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/RutInteraction';OUT.mkdir(parents=True,exist_ok=True)
SOURCE='/Game/GrandTour/ArtTests/MudWater/L_MudWater';BASE='/Game/GrandTour/ArtTests/RutInteraction'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
report=dict(ok=False,levels=[])
try:
    originals=[ROOT/'Content/GrandTour/ArtTests/MudWater/L_MudWater.umap',ROOT/'Content/GrandTour/ArtTests/MudProvingGround/L_MudProvingGround.umap']
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
    folder=ROOT/'Content/GrandTour/ArtTests/RutInteraction'
    if folder.exists():shutil.copytree(folder,ROOT/'Saved/RutInteraction'/str(time.time_ns()))
    for name,depth,bearing in [('L_RutInteraction',1.,1.),('L_RutInteraction_Firm',.65,1.6),('L_RutInteraction_Deep',1.28,.6)]:
        assert les.load_level(SOURCE)
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        target=BASE+'/'+name
        assert u.EditorLoadingAndSavingUtils.save_map(world,target)
        world=None;assert les.load_level(target)
        s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
        s.set_editor_property('use_rut_interaction',True)
        s.set_editor_property('layer_depth_scale',depth);s.set_editor_property('bearing_strength',bearing)
        assert s.simulated_water and s.simulated_water.mud_surface==s,'Copied pond references must stay inside this map'
        assert les.save_current_level()
        report['levels'].append(dict(level=target,depth=depth,bearing=bearing))
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals},'Accepted maps changed'
    report.update(ok=True,baseline_hashes=before,baseline_unchanged=True)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
s=world=None;les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();quit_at=time.monotonic()+5
def finish(dt):
    if time.monotonic()>=quit_at:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
