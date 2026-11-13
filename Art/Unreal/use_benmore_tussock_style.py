"""Switch Benmore grass to the actual approved L_TussockStyle assets."""
import unreal as u,json,time,traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreVegetation'
SOURCE='/Game/GrandTour/ArtTests/TussockStyle';DEST='/Game/GrandTour/Demo/BenmoreRoads/Vegetation'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem);eal=u.EditorAssetLibrary
phase='inspect';last=time.monotonic();started=last
report={'ok':False,'source_level':SOURCE+'/L_TussockStyle','level':LEVEL,'sources':[],'types':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'tussock-style-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world
    try:
        if time.monotonic()-started>480:raise RuntimeError('Tussock style swap timeout')
        if phase=='inspect':
            phase='working';assert les.load_level(SOURCE+'/L_TussockStyle')
            found={}
            for actor in act.get_all_level_actors():
                for c in actor.get_components_by_class(u.InstancedStaticMeshComponent):
                    mesh=c.get_editor_property('static_mesh')
                    if mesh and mesh.get_name().startswith('SM_TS_'):
                        mats=list(c.get_editor_property('override_materials'))
                        # Source study normally inherits mesh materials directly.
                        assert not any(mats),('Unexpected source overrides',mesh.get_name())
                        found[mesh.get_name()]=mesh
            assert set(found)=={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'},list(found)
            for name,mesh in found.items():
                report['sources'].append({'mesh':mesh.get_path_name(),'material':mesh.get_material(0).get_path_name()})
            assert les.load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            assert world.get_path_name().startswith(LEVEL+'.')
            mapping={'LowGrass':'Fine','CrownTussock':'Straw','ShaggyTussock':'Rust','TallClumps':'Weathered','DistantTussock':'Straw'}
            for name,variant in mapping.items():
                grass=u.load_asset(DEST+'/LGT_Benmore_'+name);assert grass
                varieties=list(grass.get_editor_property('grass_varieties'));assert len(varieties)==1
                mesh=found['SM_TS_'+variant]
                varieties[0].set_editor_property('grass_mesh',mesh)
                varieties[0].set_editor_property('override_materials',[])
                grass.set_editor_property('grass_varieties',varieties)
                assert eal.save_loaded_asset(grass)
                report['types'].append({'name':name,'mesh':mesh.get_path_name(),'material':mesh.get_material(0).get_path_name()})
            setup=json.loads((OUT/'setup-report.json').read_text())
            setup['source_level']=report['source_level']
            for row in setup['types']:
                row.update(next(r for r in report['types'] if r['name']==row['name']))
            (OUT/'setup-report.json').write_text(json.dumps(setup,indent=2))
            u.SystemLibrary.execute_console_command(world,'grass.FlushCache')
            phase='warm';last=time.monotonic()
        elif phase=='warm' and time.monotonic()-last>35:
            phase='saving';assert les.save_current_level();finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
