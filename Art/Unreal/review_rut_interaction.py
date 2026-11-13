"""Matched live vehicle passes, opt-in bank-work telemetry and rendered soil/water review."""
import csv,json,math,time,traceback,statistics
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/RutInteraction'
BASE='/Game/GrandTour/ArtTests/RutInteraction/L_RutInteraction'
report=dict(ok=False,cases=[],images=[],scope='Actual vehicle passes. CPU bank timings exclude rendering. Handling remains subject to owner driving review.')
world=pc=car=surface=sheet=camera=mesh=move=None
def save():(OUT/'review-report.json').write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def numbers(s):return {k:float(v) for k,v in (x.split('=') for x in s.split())}
def frame_metrics(path):
    with path.open(newline='') as f:rows=list(csv.reader(f))
    result={}
    for i,key in enumerate(rows[0]):
        if key not in ['FrameTime','GameThreadTime','RenderThreadTime','RHIThreadTime','GPUTime']:continue
        values=[]
        for row in rows[1:]:
            if not row or row[0].startswith('[') or row[0]=='EVENTS':break
            try:values.append(float(row[i]))
            except (ValueError,IndexError):pass
        if values:
            values.sort();result[key]=dict(frames=len(values),mean_ms=statistics.fmean(values),p99_ms=values[min(len(values)-1,math.ceil(len(values)*.99)-1)])
    return result
def sample():
    supports=[]
    for w,t in zip(car.get_traction().wheels,car.get_tuning().get_current().wheels):
        s=u.GTLandscapeSurface.query_wheel_surface(car,w.contact_point,w.tyre_heading,25)
        supports.append(dict(authored=s.get_editor_property('bWheelSupport'),sink=t.sinkage_cm,ground=t.ground_support_cm,settlement=max(0,s.rest_wheel_support_cm-t.ground_support_cm)+t.sinkage_cm))
    return dict(time=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),rotation=car.get_actor_rotation().to_tuple(),
        speed=car.get_velocity().length(),steer_degrees=[w.get_steer_angle() for w in move.wheels],bank=numbers(move.rut_interaction_report()),water=numbers(sheet.mud_water_diagnostics()),
        soil=numbers(surface.get_surface_report()),
        wheels=[dict(contact=w.get_editor_property('bInContact'),slip=w.slip_magnitude,tread=w.tread_cm_per_s) for w in car.get_traction().wheels],
        support=supports)
def aim(eye,target):
    camera.set_actor_location_and_rotation(u.Vector(*eye),u.MathLibrary.find_look_at_rotation(u.Vector(*eye),u.Vector(*target)),False,False)
    pc.set_view_target_with_blend(camera,0)
def capture(name,eye,target):
    aim(eye,target);yield .04
    u.GameplayStatics.set_game_paused(world,True);console('ShowFlag.Rendering 1');yield 4
    path=OUT/(name+'.png');stamp=time.time();console('HighResShot 1440x900 filename="'+path.as_posix()+'"')
    end=time.monotonic()+90
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end,'Screenshot timeout';yield .25
    last=path.stat().st_mtime;stable=time.monotonic()
    while time.monotonic()-stable<5:
        yield .25
        if path.stat().st_mtime!=last:last=path.stat().st_mtime;stable=time.monotonic()
    assert path.stat().st_size>40000,'Empty render'
    report['images'].append(dict(file=name+'.png',time=u.GameplayStatics.get_time_seconds(world)));save()
    console('ShowFlag.Rendering 0');u.GameplayStatics.set_game_paused(world,False);yield .05
def run():
    global world,pc,car,surface,sheet,camera,mesh,move
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    for name,suffix,enabled in [('control','',False),('worked','',True),('firm','_Firm',True),('deep','_Deep',True)]:
        assert les.load_level(BASE+suffix);yield 2
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 8
        world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
        old=u.GameplayStatics.get_player_pawn(world,0)
        if old and old!=car:old.set_actor_hidden_in_game(True)
        old=None;pc.possess(car);car.disable_input(pc)
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
        sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
        surface.use_rut_interaction=enabled;surface.follow_player=False;surface.observe_player_wheels=True
        car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(-150,100,150),u.Rotator(),False,True)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        move=car.get_chaos_movement();move.set_handbrake_input(True)
        car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
        camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'RutInteractionReviewCamera')
        camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(60)
        settings=camera.camera_component.get_editor_property('post_process_settings');settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',.6)
        camera.camera_component.set_editor_property('post_process_settings',settings)
        for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60']:console(cmd)
        start=u.GameplayStatics.get_time_seconds(world)
        while u.GameplayStatics.get_time_seconds(world)-start<5:yield .1
        case=dict(name=name,enabled=enabled,level=BASE+suffix,before=sample(),samples=[]);report['cases'].append(case);save()
        if name=='worked':yield from capture('worked_before',(190,-630,390),(500,110,-3))
        start=u.GameplayStatics.get_time_seconds(world);move.set_handbrake_input(False)
        while u.GameplayStatics.get_time_seconds(world)-start<9:
            elapsed=u.GameplayStatics.get_time_seconds(world)-start
            move.set_throttle_input(.6);move.set_brake_input(0);car.set_raw_steer(.6 if elapsed>5 else 0)
            case['samples'].append(sample());yield .1
        car.reset_driving_inputs();move.set_handbrake_input(True);case['after']=sample()
        case['travel_cm']=math.dist(case['before']['position'][:2],case['after']['position'][:2])
        case['bank_work_j']=case['after']['bank']['work_j']-case['before']['bank']['work_j'];save()
        yield from capture(name+'_after',(190,-630,390),(500,110,-3))
        if name in ['control','worked']:
            car.set_actor_hidden_in_game(True)
            yield from capture(name+'_tracks',(340,-210,180),(200,110,-8))
            car.set_actor_hidden_in_game(False)
        if name=='worked':
            # An unpaused segment measures the new force cost during real rendering.
            car.set_actor_location_and_rotation(u.Vector(-550,100,150),u.Rotator(),False,True)
            mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());yield 5
            aim((190,-630,390),(200,110,-3));console('ShowFlag.Rendering 1');yield 2
            csv_start=time.time();console('csvprofile start')
            case['rendered_start']=sample();wall=time.monotonic();case['rendered_samples']=[]
            move.set_handbrake_input(False);move.set_throttle_input(.35);car.set_raw_steer(.15)
            while time.monotonic()-wall<8:case['rendered_samples'].append(sample());yield .1
            case['rendered_end']=sample();console('csvprofile stop');car.reset_driving_inputs();move.set_handbrake_input(True);yield 3
            files=[p for p in (ROOT/'Saved/Profiling/CSV').glob('*.csv') if p.stat().st_mtime>=csv_start]
            if files:
                latest=max(files,key=lambda p:p.stat().st_mtime);case['frame_profile']=frame_metrics(latest);case['frame_profile_source']=str(latest)
            console('ShowFlag.Rendering 0');save()
        u.EditorLevelLibrary.editor_end_play();yield 4
        world=pc=car=surface=sheet=camera=mesh=move=None
        assert les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 4
    all_samples=[s for c in report['cases'] for s in [c['before']]+c['samples']+[c['after']]]
    control,worked,firm,deep=report['cases']
    settlement=lambda c:statistics.fmean(w['settlement'] for w in c['before']['support'])
    report['checks']=dict(control_has_no_bank_work=abs(control['bank_work_j'])<.001,
        worked_bank_work=worked['bank_work_j']>10,
        lateral_bank_work=worked['after']['bank']['lateral_j']-worked['before']['bank']['lateral_j']>5,
        steering_reaches_front_tyres=all(max(abs(a) for s in c['samples'] for a in s['steer_degrees'])>8 for c in [control,worked]),
        all_variants_contact=all(sum(w['contact'] for w in c['after']['wheels'])>=3 for c in report['cases']),
        conserves_soil=all(abs(s['soil']['balance_cm3'])<.1 for s in all_samples),
        conserves_water=all(abs(s['water']['delta_m3'])<.001 for s in all_samples),
        no_water_clamps=all(s['water']['clamps']==0 for s in all_samples),
        baseline_still_drives=worked['travel_cm']>max(200,control['travel_cm']*.5),
        profile_drives_in_mud=statistics.fmean(w['authored'] for s in worked['rendered_samples'] for w in s['support'])>.8,
        deep_settles_more_than_firm=settlement(deep)>settlement(firm)+5,
        finite_vehicle=all(math.isfinite(v) for s in all_samples for v in s['position']))
    report['settlement_cm']={c['name']:settlement(c) for c in report['cases']}
    report['ok']=all(report['checks'].values());save()
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
steps=run();deadline=0;busy=False;started=time.monotonic()
def tick(dt):
    global deadline,busy
    if busy:return
    busy=True
    try:
        assert time.monotonic()-started<840,'Review deadline exceeded'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error'])
        u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
