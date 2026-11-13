"""Matched rendered driving benchmark, with old-world garbage collected before warmup."""
import csv,json,math,statistics,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/RutInteraction';CSV=ROOT/'Saved/Profiling/CSV'
report=dict(ok=False,cases=[],scope='Two fresh PIE worlds. Explicit garbage collection before 8-second warmup, then 8-second real-time rendered driving. Raw review profile is preserved separately.')
world=pc=car=surface=sheet=mesh=move=camera=None
def save():(OUT/'benchmark-report.json').write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def numbers(s):return {k:float(v) for k,v in (x.split('=') for x in s.split())}
def sample():
    return dict(position=car.get_actor_location().to_tuple(),bank=numbers(move.rut_interaction_report()),soil=numbers(surface.get_surface_report()),water=numbers(sheet.mud_water_diagnostics()),
        support=[w.get_editor_property('bLandscapeSupport') for w in car.get_tuning().get_current().wheels])
def metrics(path):
    with path.open(newline='') as f:rows=list(csv.reader(f))
    result={}
    for i,key in enumerate(rows[0]):
        if key not in ['FrameTime','GameThreadTime','GPUTime']:continue
        values=[]
        for row in rows[1:]:
            if not row or row[0].startswith('[') or row[0]=='EVENTS':break
            try:values.append(float(row[i]))
            except (ValueError,IndexError):pass
        values.sort();assert values
        result[key]=dict(frames=len(values),mean_ms=statistics.fmean(values),p99_ms=values[min(len(values)-1,math.ceil(len(values)*.99)-1)])
    return result
def run():
    global world,pc,car,surface,sheet,mesh,move,camera
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    for name,enabled in [('control',False),('worked',True)]:
        assert les.load_level('/Game/GrandTour/ArtTests/RutInteraction/L_RutInteraction');yield 2
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 8
        world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car()
        old=u.GameplayStatics.get_player_pawn(world,0)
        if old and old!=car:old.set_actor_hidden_in_game(True)
        old=None;pc.possess(car);car.disable_input(pc)
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
        sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]
        surface.use_rut_interaction=enabled;surface.follow_player=False
        car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(-550,100,150),u.Rotator(),False,True)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        move=car.get_chaos_movement();move.set_handbrake_input(True);car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
        camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'RutBenchmarkCamera')
        camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(60)
        eye=u.Vector(190,-630,390);target=u.Vector(200,110,-3)
        camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,target),False,False);pc.set_view_target_with_blend(camera,0)
        for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60','ShowFlag.Rendering 1']:console(cmd)
        u.SystemLibrary.collect_garbage();yield 8
        case=dict(name=name,before=sample(),samples=[]);report['cases'].append(case);save()
        stamp=time.time();console('csvprofile start');wall=time.monotonic()
        move.set_handbrake_input(False);move.set_throttle_input(.35);car.set_raw_steer(.15)
        while time.monotonic()-wall<8:case['samples'].append(sample());yield .1
        case['after']=sample();console('csvprofile stop');car.reset_driving_inputs();move.set_handbrake_input(True);yield 3
        paths=[p for p in CSV.glob('*.csv') if p.stat().st_mtime>=stamp];assert paths
        path=max(paths,key=lambda p:p.stat().st_mtime);case['csv']=str(path);case['frames']=metrics(path)
        case['mud_contact_fraction']=statistics.fmean(v for s in case['samples'] for v in s['support']);save()
        console('ShowFlag.Rendering 0');yield 2
        u.EditorLevelLibrary.editor_end_play();yield 5
        world=pc=car=surface=sheet=mesh=move=camera=None;assert les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 5
    a,b=report['cases']
    report['checks']=dict(both_driving_in_mud=min(a['mud_contact_fraction'],b['mud_contact_fraction'])>.8,
        bounded_bank_cost=b['after']['bank']['mean_ms']<.02,
        bounded_terrain_cost=b['after']['soil']['observe_mean_ms']<3,
        no_major_frame_regression=b['frames']['FrameTime']['mean_ms']<a['frames']['FrameTime']['mean_ms']*1.2,
        no_water_clamps=all(c['after']['water']['clamps']==0 for c in report['cases']))
    report['ok']=all(report['checks'].values());save()
    les=None;u.SystemLibrary.collect_garbage();yield 5
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
steps=run();deadline=0;busy=False;started=time.monotonic()
def tick(dt):
    global deadline,busy
    if busy:return
    busy=True
    try:
        assert time.monotonic()-started<300,'Benchmark deadline'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
