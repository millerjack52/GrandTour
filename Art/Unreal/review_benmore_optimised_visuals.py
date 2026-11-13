"""Untimed visual regression of normal Benmore driving after optimisation.

Uses real controls; placement only before the drive. Paused screenshots are
explicitly NOT performance evidence. No water, simulation or handling overrides.
Launch in the exclusive standalone game slot with GT_BENMORE_VISUAL_OUT set.
"""
import unreal as u
import os,sys,json,time,traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_profile_drive import Driver
OUT=Path(os.environ['GT_BENMORE_VISUAL_OUT']).resolve()
assert OUT.parent==ROOT/'Art/Export/BenmoreGaea' and not OUT.exists()
OUT.mkdir()
world=pc=driver=None
report=dict(ok=False,timings_collected=False,paused_screenshots=True,samples=[])


def console(s):u.SystemLibrary.execute_console_command(world,s,pc)


def main():
    global world,pc,driver
    world=u.find_object(None,'/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.L_Benmore_GaeaReview')
    assert isinstance(world,u.World)
    yield 15
    pc=u.GameplayStatics.get_player_controller(world,0)
    # Camera-manager updates otherwise stop with the paused world, leaving the
    # requested side view stuck on the previous chase POV.
    pc.set_editor_property('bShouldPerformFullTickWhenPaused',True)
    driver=Driver(world,pc,ROOT)
    console('r.ScreenPercentage 100')
    console('r.DynamicRes.OperationMode 0')
    report['settings']={k:u.SystemLibrary.get_console_variable_float_value(k) for k in (
        'gt.Spray.SparseUpdates','gt.Spray.LazyFineActivation',
        'gt.Water.VehicleWaves','gt.Water.WakeRelief','gt.Water.Domain.Detail','gt.Water.InteractionSpray',
        'r.ScreenPercentage','r.TSR.History.ScreenPercentage','r.Nanite.MaxPixelsPerEdge')}
    sheet=next(s for s in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)
               if s.get_editor_property('WaterDomain'))
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[
        a.static_mesh_component for a in sheet.get_editor_property('DomainSurfaces')]
    def bindings():return [dict(component=c.get_path_name(),material=c.get_material(0).get_path_name(),
        values={k:c.get_material(0).get_scalar_parameter_value(k)
            for k in ['WakeDetailReady','FieldActive','LocalSurface','DetailEnabled']}) for c in components]
    report['water_materials']=bindings()
    camera=u.GameplayStatics.get_actor_of_class(world,u.CameraActor)
    assert camera
    console('t.MaxFPS 60')
    console('gt.Look.Weather Clear')
    yield 30
    driver.place('Ford')
    yield 8
    driver.begin()
    began=u.GameplayStatics.get_time_seconds(world)
    next_photo=0.
    while u.GameplayStatics.get_time_seconds(world)-began<18:
        driver.step()
        elapsed=u.GameplayStatics.get_time_seconds(world)-began
        spray=driver.car.get_spray()
        if elapsed>=next_photo:
            row=dict(elapsed_s=elapsed,position_cm=list(driver.car.get_actor_location().to_tuple()),
                water_bindings=bindings(),
                speed_mps=driver.car.get_velocity().length()*.01,water_particles=spray.get_live_count(u.GTSprayKind.WATER),
                bow_rate=spray.get_bow_rate_now(),splash_rate=spray.get_splash_rate_now(),
                fine_live=[spray.get_fine_live_count(i) for i in range(3)],
                fine_rates=[[spray.get_fine_rate(w,e) for e in range(3)] for w in range(4)])
            report['samples'].append(row)
            u.GameplayStatics.set_game_paused(world,True)
            for view in ('chase','side'):
                if view=='chase':pc.set_view_target_with_blend(driver.car,0)
                else:
                    at=driver.car.get_actor_location()
                    f=driver.car.get_actor_forward_vector();r=driver.car.get_actor_right_vector()
                    eye=at-f*580+r*660+u.Vector(0,0,360)
                    camera.set_actor_location(eye,False,False)
                    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,at+f*100),False)
                    camera.camera_component.set_field_of_view(58)
                    pc.set_view_target_with_blend(camera,0)
                yield .2
                if view=='side':
                    actual=pc.player_camera_manager.get_camera_location()
                    assert (actual-eye).length()<2,'Paused side camera did not update'
                photo=OUT/(f'{len(report["samples"]):02d}_{view}.png')
                console('HighResShot 1600x900 filename="'+photo.as_posix()+'"')
                for _ in range(60):
                    yield .1
                    if photo.exists():break
                assert photo.exists(),'Screenshot failed'
            pc.set_view_target_with_blend(driver.car,0)
            u.GameplayStatics.set_game_paused(world,False)
            next_photo=elapsed+2
        yield .1
    driver.stop()
    assert any(s['water_particles']>0 for s in report['samples']),'No water spray exercised'
    assert any(s['bow_rate']>0 for s in report['samples']),'No bow emission exercised'
    report['ok']=True


def finish(error=None):
    global gen
    gen=None
    if error:report.update(ok=False,error=error);u.log_error(error)
    if driver:driver.stop()
    if world:u.GameplayStatics.set_game_paused(world,False)
    (OUT/'visual-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle)
    if world:console('quit')


gen=main();next_at=started=time.monotonic();busy=False
def tick(dt):
    global next_at,busy
    if gen is None or busy:return
    busy=True
    try:
        if time.monotonic()-started>600:raise RuntimeError('Visual review timeout')
        if time.monotonic()>=next_at:next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
