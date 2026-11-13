"""Matched live vehicle passes, granular soil telemetry and native rendered review."""
import csv,json,math,time,traceback,statistics,gc
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/SandTerrain'
BASE='/Game/GrandTour/ArtTests/SandTerrain/L_SandTerrain'
report=dict(ok=False,cases=[],images=[],scope='Matched loose/compacted sand driving, shared finite soil field. Owner driving review still required.')
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
        supports.append(dict(authored=s.get_editor_property('bWheelSupport'),granular=s.get_editor_property('bGranularResponse'),sink=t.sinkage_cm,grip=t.soil_grip,drag_n=t.soil_drag_n,
            settlement=max(0,s.rest_wheel_support_cm-t.ground_support_cm)+t.sinkage_cm,water=s.water_depth_cm))
    dust=u.GameplayStatics.get_all_actors_of_class(world,u.GTDustLab)
    return dict(time=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),speed=car.get_velocity().length(),support=supports,
        tyre_mud=[car.get_body_state().get_tyre_coat(i) for i in range(4)],mud_wet=car.get_body_state().mud_wet,
        soil=numbers(surface.get_surface_report()),dust_rate=sum(a.total_rate for a in dust),dust_particles=sum(a.get_live_particles() for a in dust),
        wheels=[dict(contact=w.get_editor_property('bInContact'),slip=w.slip_magnitude,tag=w.surface_tag.export_text()) for w in car.get_traction().wheels])
def aim(eye,target):
    camera.set_actor_location_and_rotation(u.Vector(*eye),u.MathLibrary.find_look_at_rotation(u.Vector(*eye),u.Vector(*target)),False,False)
    pc.set_view_target_with_blend(camera,0)
def capture(name,eye,target):
    aim(eye,target);yield .05
    u.GameplayStatics.set_game_paused(world,True);console('ShowFlag.Rendering 1');yield 4
    path=OUT/(name+'.png');stamp=time.time();console('HighResShot 1440x900 filename="'+path.as_posix()+'"')
    end=time.monotonic()+90
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end;yield .25
    last=path.stat().st_mtime;stable=time.monotonic()
    while time.monotonic()-stable<5:
        yield .25
        if path.stat().st_mtime!=last:last=path.stat().st_mtime;stable=time.monotonic()
    assert path.stat().st_size>40000
    report['images'].append(name+'.png');save()
    console('ShowFlag.Rendering 0');u.GameplayStatics.set_game_paused(world,False);yield .05
def run():
    global world,pc,car,surface,camera,mesh,move
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    for name in ['T_SandPaint','T_SandRest']:
        texture=u.load_asset('/Game/GrandTour/ArtTests/SandTerrain/'+name)
        assert not texture.get_editor_property('srgb')
        assert texture.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP
        assert texture.get_editor_property('mip_gen_settings')==u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    texture=None
    for name,lane in [('loose',-280),('compacted',350)]:
        assert les.load_level(BASE);yield 2
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 8
        world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
        old=u.GameplayStatics.get_player_pawn(world,0)
        if old and old!=car:old.set_actor_hidden_in_game(True)
        old=None;pc.possess(car);car.disable_input(pc)
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0];surface.follow_player=False
        car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(-1050,lane,135),u.Rotator(),False,True)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        move=car.get_chaos_movement();move.set_handbrake_input(True)
        car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
        camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'SandReviewCamera')
        camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(60)
        settings=camera.camera_component.get_editor_property('post_process_settings');settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',0.)
        camera.camera_component.set_editor_property('post_process_settings',settings)
        for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60']:console(cmd)
        yield 5
        case=dict(name=name,before=sample(),samples=[]);report['cases'].append(case);save()
        if name=='loose':yield from capture('overview',(900,-400,700),(-300,0,-3))
        yield from capture(name+'_settled',(-600,lane-520,280),(-980,lane,5))
        aim((-300,-1300,800),(0,0,0));console('ShowFlag.Rendering 1');yield 2
        csv_start=time.time();console('csvprofile start');start=u.GameplayStatics.get_time_seconds(world)
        move.set_handbrake_input(False);move.set_throttle_input(.5)
        while u.GameplayStatics.get_time_seconds(world)-start<6 and car.get_actor_location().x<950:
            case['samples'].append(sample());yield .1
        console('csvprofile stop');case['after']=sample();case['drive_seconds']=case['after']['time']-start;save()
        p=car.get_actor_location();yield from capture(name+'_driving',(p.x+320,p.y-560,p.z+250),(p.x,p.y,p.z-20))
        car.reset_driving_inputs();move.set_handbrake_input(True);yield 3
        files=[p for p in (ROOT/'Saved/Profiling/CSV').glob('*.csv') if p.stat().st_mtime>=csv_start]
        if files:case['frame_profile']=frame_metrics(max(files,key=lambda p:p.stat().st_mtime))
        car.set_actor_hidden_in_game(True)
        yield from capture(name+'_tracks',(-100,lane-320,235),(-350,lane,-8))
        case['travel_cm']=case['after']['position'][0]-case['before']['position'][0];save()
        console('ShowFlag.Rendering 0');yield 2;u.EditorLevelLibrary.editor_end_play();yield 5
        world=pc=car=surface=camera=mesh=move=None
        assert les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 5
    loose,packed=report['cases'];settlement=lambda c:statistics.fmean(s['settlement'] for s in c['before']['support'])
    all_samples=[s for c in report['cases'] for s in [c['before'],c['after']]+c['samples']]
    report['settlement_cm']={c['name']:settlement(c) for c in report['cases']}
    report['checks']=dict(loose_sinks_more=settlement(loose)>settlement(packed)+5,
        both_drive=all(c['travel_cm']>200 for c in report['cases']),
        granular_contact=all(sum(s['granular'] for s in c['before']['support'])>=3 for c in report['cases']),
        dry_sand=all(s['water']<.01 for a in all_samples for s in a['support']),
        volume_conserved=all(abs(s['soil']['balance_cm3'])<.1 for s in all_samples),
        dry_dust=max(s['dust_rate'] for s in all_samples)>5,
        no_wet_mud_coating=all(max(s['tyre_mud'])<.001 and s['mud_wet']<.001 for s in all_samples),
        finite_car=all(math.isfinite(v) for s in all_samples for v in s['position']))
    report['ok']=all(report['checks'].values());save()
    les=None;u.SystemLibrary.collect_garbage();yield 5
steps=run();deadline=0;busy=False;started=time.monotonic()
def tick(dt):
    global deadline,busy,steps,handle
    if busy:return
    busy=True
    try:
        assert time.monotonic()-started<840
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle);handle=None;steps.close();steps=None;gc.collect();u.SystemLibrary.collect_garbage();u.EditorPythonScripting.set_keep_python_script_alive(False)
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)

