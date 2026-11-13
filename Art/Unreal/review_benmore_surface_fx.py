"""Exercise the saved Benmore integration, using existing road tracing/path following.
No map saves or physics tuning. Review-only rendering reductions; no performance measurements.
"""
import json,math,sys,time,traceback,types
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/DustLab'
source=ROOT/'Art/Unreal/capture_benmore_b1b.py'
q=types.ModuleType('benmore_fx_road_helpers');q.__file__=str(source)
# Definitions only: do not register or run the original capture task.
exec(compile(source.read_text().split('\ngen = run()')[0],str(source),'exec'),q.__dict__)
q.OUT=OUT
report={'ok':False,'checks':{},'pictures':[],'profiled':False,'review_rendering':'960x600 viewport, 60% screen percentage, Lumen disabled, reduced shadows/clouds; process only; fixed step 1/30 s'}
state={'phase':'run','started':time.monotonic()}
dust=mud=manager=None

def wait_game(seconds,view=None):
    start=q.gs()
    while q.gs()-start<seconds:
        if view:view()
        yield

def bind_effects():
    global dust,mud
    dust=next(a for a in u.GameplayStatics.get_all_actors_of_class(q.world,u.GTDustLab) if a.target_car==q.car and a.get_owner()==manager)
    mud=next(a for a in u.GameplayStatics.get_all_actors_of_class(q.world,u.GTMudFlickLab) if a.target_car==q.car and a.get_owner()==manager)

def fx_state():
    return dict(dust_rate=dust.total_rate,dust_live=dust.get_live_particles(),mud_rate=mud.total_rate,mud_live=mud.get_live_particles(),
                legacy_dust_rate=sum(q.spray.get_fine_rate(i,2) for i in range(len(q.car.get_traction().wheels))),
                legacy_mud_rate=sum(q.spray.get_fine_rate(i,0) for i in range(len(q.car.get_traction().wheels))),
                grit_rate=sum(q.spray.get_fine_rate(i,1) for i in range(len(q.car.get_traction().wheels))),
                external_dust=q.spray.get_editor_property('bExternalDustEffects'),external_mud=q.spray.get_editor_property('bExternalMudEffects'))

def wide_view():
    p=q.car.get_actor_location();f=q.car.get_actor_forward_vector();r=q.car.get_actor_right_vector()
    side=-1. if r.x*q.L[0]+r.y*q.L[1]>0 else 1.
    eye=(p.x-f.x*1250+r.x*side*1400,p.y-f.y*1250+r.y*side*1400,p.z+650)
    return q.aim(eye,(p.x-f.x*450,p.y-f.y*450,p.z),65.)

def close_view():
    p=q.car.get_actor_location();f=q.car.get_actor_forward_vector();r=q.car.get_actor_right_vector()
    side=-1. if r.x*q.L[0]+r.y*q.L[1]>0 else 1.
    return q.aim((p.x-f.x*550+r.x*side*750,p.y-f.y*550+r.y*side*750,p.z+260),(p.x,p.y,p.z-10),60.)

def capture(name,view,extra=None):
    name=state.get('capture_prefix','Benmore_Dry_')+name.replace('B1b_','')
    u.GameplayStatics.set_game_paused(q.world,True)
    row={'name':name,'state':q.state(view),'effects':fx_state(),'extra':extra or {}}
    path=OUT/(name+'.png');start=time.time()
    q.console('HighResShot 1440x900 filename="%s"'%path.as_posix())
    real=time.monotonic()
    while not(path.exists() and path.stat().st_mtime>=start-.5 and time.monotonic()-real>1.5):
        if time.monotonic()-real>60:raise RuntimeError('Capture not written '+name)
        yield
    row['image']=str(path);report['pictures'].append(row)
    u.GameplayStatics.set_game_paused(q.world,False)
    q.car.reset_driving_inputs();q.move.set_handbrake_input(True)

q.capture=capture
q.chase_view=wide_view

def run():
    global manager
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(q.LEVEL)
    start=time.monotonic()
    while time.monotonic()-start<6:yield
    assert u.GTPlayWindowLibrary.request_play_in_new_window(960,600)
    start=time.monotonic()
    while time.monotonic()-start<18:yield
    q.world=u.EditorLevelLibrary.get_game_world();assert q.world
    q.pc=u.GameplayStatics.get_player_controller(q.world,0)
    cars=u.GameplayStatics.get_all_actors_of_class(q.world,u.GTCarPawn)
    pawn=u.GameplayStatics.get_player_pawn(q.world,0)
    q.car=pawn if isinstance(pawn,u.GTCarPawn) else sorted(cars,key=lambda a:a.get_path_name())[0]
    q.pc.possess(q.car);q.car.disable_input(q.pc)
    q.move=q.car.get_chaos_movement();q.spray=q.car.get_spray()
    q.weather=next(o for o in u.ObjectIterator(u.GTWeatherSubsystem) if o.get_outer()==q.world)
    clear=q.weather.find_state('Clear')
    if clear:q.weather.set_state(clear,True)
    q.weather.set_wetness_for_test(0.)
    q.camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(q.world,u.CameraActor,u.Transform(),'BenmoreSurfaceFXReview')
    q.camera.camera_component.set_constraint_aspect_ratio(False);q.pc.set_view_target_with_blend(q.camera,0.)
    q.console('showhud')
    suns=u.GameplayStatics.get_all_actors_of_class(q.world,u.DirectionalLight)
    sun=max(suns,key=lambda a:a.light_component.get_editor_property('intensity'))
    f=sun.light_component.get_forward_vector();q.L=q.unit((f.x,f.y,f.z));q.Lh=q.unit((f.x,f.y))
    manager=u.GameplayStatics.get_all_actors_of_class(q.world,u.GTVehicleSurfaceEffects)[0]
    yield from wait_game(1.)
    report['car_count']=len(cars)
    report['checks']['all_cars_managed']=manager.get_managed_car_count()==len(cars)
    pairs=[]
    for car in cars:
        pairs.append((sum(a.target_car==car for a in u.GameplayStatics.get_all_actors_of_class(q.world,u.GTDustLab)),
                      sum(a.target_car==car for a in u.GameplayStatics.get_all_actors_of_class(q.world,u.GTMudFlickLab))))
    report['checks']['one_effect_pair_per_car']=all(p==(1,1) for p in pairs)
    q.console('gt.SurfaceEffects 0');yield from wait_game(.7)
    report['checks']['disable_restores_legacy']=all(not c.get_spray().get_editor_property('bExternalDustEffects') and
        not c.get_spray().get_editor_property('bExternalMudEffects') for c in cars) and manager.get_managed_car_count()==0
    q.console('gt.SurfaceEffects 1');yield from wait_game(.7);bind_effects()
    report['checks']['reenable_rebinds']=manager.get_managed_car_count()==len(cars) and fx_state()['external_dust'] and fx_state()['external_mud']
    yield from q.scenario_chase()
    dry=report['pictures'][-1]['effects']
    report['checks']['dry_gravel_dust']=dry['dust_rate']>1 and dry['dust_live']>0
    report['checks']['no_duplicate_dust']=dry['legacy_dust_rate']==0
    report['checks']['grit_preserved']=dry['grit_rate']>0
    q.weather.set_wetness_for_test(1.);state['capture_prefix']='Benmore_Wet_'
    q.release(True,False)
    start=q.gs()
    while q.gs()-start<1.5:
        q.move.set_throttle_input(.4);q.move.set_brake_input(0.);q.car.set_raw_steer(0.)
        view=wide_view();yield
    yield from capture('Gravel',view)
    wet=report['pictures'][-1]['effects']
    report['checks']['wet_suppresses_dust']=wet['dust_rate']==0 and wet['legacy_dust_rate']==0
    q.weather.set_wetness_for_test(0.)
    # Use an existing deformable riverbed, never author or modify a patch here.
    patches=u.GameplayStatics.get_all_actors_of_class(q.world,u.GTMudPatch)
    report['mud_patches']=[]
    found=False
    for patch in patches:
        centre,extent=patch.get_actor_bounds(False)
        report['mud_patches'].append({'name':patch.get_name(),'centre':list(centre.to_tuple()),'extent':list(extent.to_tuple())})
        if extent.x<150 or extent.y<150:continue
        # Stay near the centre of the existing patch; choose its long direction.
        heading=(1.,0.) if extent.x>=extent.y else (0.,1.)
        q.place(centre.x,centre.y,heading)
        yield from q.settle(close_view,2.)
        q.release(False,True)
        start=q.gs()
        while q.gs()-start<4.:
            q.move.set_throttle_input(.9);q.move.set_brake_input(0.);q.car.set_raw_steer(0.)
            view=close_view()
            if q.gs()-start>1. and mud.total_rate>1 and mud.get_live_particles()>0:
                state['capture_prefix']='Benmore_'
                yield from capture('MudFlick',view,{'patch':patch.get_name()})
                found=True;break
            yield
        if found:break
    report['checks']['existing_mud_ground_emits']=found
    if found:
        fx=report['pictures'][-1]['effects'];report['checks']['no_duplicate_mud']=fx['legacy_mud_rate']==0
    assert all(report['checks'].values()),'Integration checks failed'

gen=run();busy=False

def finish(error=None):
    global dust,mud,manager,gen
    report['ok']=not error and all(report['checks'].values())
    if error:report['error']=error;u.log_error(error)
    (OUT/'benmore-review-report.json').write_text(json.dumps(report,indent=2))
    gen=None;dust=mud=manager=None
    for name in ('world','pc','car','move','spray','weather','camera'):setattr(q,name,None)
    u.EditorLevelLibrary.editor_end_play();state.update(phase='stopping',last=time.monotonic())

def tick(dt):
    global busy
    if busy:return
    busy=True
    try:
        now=time.monotonic()
        if state['phase']=='stopping':
            if now-state['last']>4 and u.EditorLevelLibrary.get_game_world() is None:
                u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry');state.update(phase='quitting',last=now)
        elif state['phase']=='quitting':
            if now-state['last']>4:
                u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        elif state['phase']=='run':
            if now-state['started']>900:raise RuntimeError('Benmore FX review timed out')
            next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False

handle=u.register_slate_post_tick_callback(tick)
