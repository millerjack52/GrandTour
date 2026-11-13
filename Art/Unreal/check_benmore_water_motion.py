"""Fresh-process saved-asset and runtime-clock check for the motion art pass."""
import unreal as u
import sys,json,time,traceback,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
VARIANT=os.environ.get('GT_WATER_ART_VARIANT','Motion')
if VARIANT=='Detail':
    from benmore_water_detail import DEST
elif VARIANT=='Rapids':
    from benmore_water_rapids import DEST
else:
    from benmore_water_motion import DEST
OUT=ROOT/('Art/Export/BenmoreGaea/Water'+VARIANT+'_20261011')
report={'ok':False};busy=False;started=time.monotonic();next_at=started

def run():
    assert shared.les.load_level(shared.LEVEL)
    shared.DEST=DEST;shared.verify_saved_water()
    sheet=shared.refs()['Benmore_RS_WaterDomain']
    assert sheet.get_editor_property('ambient_wave_material').get_path_name()==DEST+'/M_FW_Precombine.M_FW_Precombine'
    assert sheet.get_editor_property('surface_material_path')==DEST+'/M_GC_DomainRiver.M_GC_DomainRiver'
    if VARIANT=='Detail':
        report['refraction']={}
        for kind in ['River','Lake']:
            material=u.load_asset(DEST+'/M_GC_Domain'+kind)
            assert material.get_editor_property('refraction_method')==u.RefractionMode.RM_2D_OFFSET
            assert u.MaterialEditingLibrary.get_material_property_input_node(material,u.MaterialProperty.MP_REFRACTION)
            errors=u.MaterialEditingLibrary.recompile_material(material);assert not errors,list(errors)
            report['refraction'][kind]='bounded normal-driven screen offset'
        spray=shared.refs()['Benmore_RiffleSpray'];comp=spray.static_mesh_component
        assert comp.get_collision_enabled()==u.CollisionEnabled.NO_COLLISION
        mesh=comp.static_mesh;bounds=mesh.get_bounds()
        report['spray']={'material':comp.get_material(0).get_path_name(),'origin_cm':list(bounds.origin.to_tuple()),'extent_cm':list(bounds.box_extent.to_tuple()),'collision':'disabled'}
        # Catch FBX axis/unit mistakes: the accepted course is west/north of origin.
        assert bounds.origin.x< -20000 and bounds.origin.y>0 and bounds.box_extent.x<100000
        errors=u.MaterialEditingLibrary.recompile_material(comp.get_material(0));assert not errors,list(errors)
    yield 8
    shared.les.editor_request_begin_play();yield 8
    world=u.EditorLevelLibrary.get_game_world();assert world
    pc=u.GameplayStatics.get_player_controller(world,0)
    u.SystemLibrary.execute_console_command(world,'ShowFlag.Rendering 0',pc)
    sheet=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_editor_property('water_domain'))
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
    mats=[c.get_material(0) for c in components]
    u.GameplayStatics.set_game_paused(world,False)
    a=[m.get_scalar_parameter_value('AmbientClock') for m in mats]
    game_start=u.GameplayStatics.get_time_seconds(world)
    report.update(game_time_before=game_start,clock_before=a)
    # Shader/PIE startup can consume the entire wall wait before another game
    # tick occurs. Judge an animation clock over simulated time, not wall time.
    while u.GameplayStatics.get_time_seconds(world)-game_start<1:
        yield .05
    b=[m.get_scalar_parameter_value('AmbientClock') for m in mats]
    report['game_time_after']=u.GameplayStatics.get_time_seconds(world)
    report['clock_after']=b
    assert all(y>x for x,y in zip(a,b)),(a,b)
    assert all(m.get_scalar_parameter_value('AmbientReady')==1 for m in mats)
    if VARIANT in ('Rapids','Detail'):assert all(m.get_scalar_parameter_value('RapidsIntensity')==1 for m in mats)
    report.update(ok=True,clock_before=a,clock_after=b,saved_parents=shared.report['reloaded_water_asset_parents'])
    # Drop Python references before tearing down PIE and its material instances.
    mats=[];components=[];sheet=None;world=None;pc=None
    u.EditorLevelLibrary.editor_end_play();yield 3

def tick(dt):
    global busy,next_at,gen
    if busy or time.monotonic()<next_at:return
    busy=True
    try:
        if time.monotonic()-started>180:raise RuntimeError('Fresh runtime check timed out')
        delay=next(gen);next_at=time.monotonic()+delay
    except (StopIteration,Exception) as e:
        if not isinstance(e,StopIteration):report.update(ok=False,error=traceback.format_exc());u.log_error(report['error'])
        (OUT/'runtime-report.json').write_text(json.dumps(report,indent=2))
        gen=None;u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False

gen=run();handle=u.register_slate_post_tick_callback(tick)
