"""Apply denser approved tussocks and textured dry-meadow ground."""
import unreal as u,json,time,traceback,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreVegetation'
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_ground_detail import build,DENSITIES
DEST='/Game/GrandTour/Demo/BenmoreRoads/Vegetation';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);eal=u.EditorAssetLibrary
phase='load';started=time.monotonic();last=started;report={'ok':False}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'ground-refinement-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last
    try:
        if time.monotonic()-started>600:raise RuntimeError('Cover refinement timeout')
        if phase=='load':
            phase='building';assert les.load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();assert world.get_path_name().startswith(LEVEL+'.')
            mat=u.load_asset(DEST+'/M_Benmore_FullCover');assert mat
            backup=DEST+'/M_Benmore_BeforeGroundDetail'
            if not eal.does_asset_exist(backup):assert eal.duplicate_asset(mat.get_path_name(),backup)
            report.update(build(mat));assert not u.MaterialEditingLibrary.recompile_material(mat);assert eal.save_loaded_asset(mat)
            for name,density in DENSITIES.items():
                grass=u.load_asset(DEST+'/LGT_Benmore_'+name);vs=list(grass.get_editor_property('grass_varieties'));assert len(vs)==1
                assert vs[0].get_editor_property('grass_mesh').get_name().startswith('SM_TS_')
                vs[0].set_editor_property('grass_density',u.PerPlatformFloat(default=density));grass.set_editor_property('grass_varieties',vs);assert eal.save_loaded_asset(grass)
            setup=json.loads((OUT/'setup-report.json').read_text())
            for row in setup['types']:row['density_per_100m2']=DENSITIES[row['name']]
            setup['ground_detail']={k:v for k,v in report.items() if k!='ok'};(OUT/'setup-report.json').write_text(json.dumps(setup,indent=2))
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>45:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
