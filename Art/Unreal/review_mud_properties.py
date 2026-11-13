"""Same car, route and inputs in three soil profiles; capture actual PIE settlement and ruts."""
import json,math,statistics,time,traceback
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudProvingGround'
BASE='/Game/GrandTour/ArtTests/MudProvingGround/L_MudProvingGround'
report=dict(ok=False,profiles=[],scope='Same estate, standing load then 60 percent throttle / low range / diff lock. Not a GPU benchmark.')
world=pc=car=surface=camera=None
def save():(OUT/'propertiesreview-report.json').write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def sample():
    tuning=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
    wheels=car.get_traction().wheels
    data=[]
    physics_wheels=car.get_chaos_movement().get_editor_property('wheels')
    for i,(w,t) in enumerate(zip(wheels,tuning.wheels)):
        width=physics_wheels[i].get_editor_property('wheel_width')
        s=u.GTLandscapeSurface.query_wheel_surface(car,w.contact_point,w.tyre_heading,width)
        data.append(dict(contact=w.get_editor_property('bInContact'),penetration_cm=t.sinkage_cm,
            ground_cm=t.ground_support_cm,compression_cm=s.compression_cm,
            total_settlement_cm=max(0,s.rest_wheel_support_cm-t.ground_support_cm)+t.sinkage_cm,
            available_depth_cm=s.sinkage_cap_cm,water_depth_cm=s.water_depth_cm,tread_cm_s=w.tread_cm_per_s))
    return dict(time=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),speed_cm_s=car.get_velocity().length(),wheels=data)
def capture(name,eye,target):
    camera.set_actor_location_and_rotation(u.Vector(*eye),u.MathLibrary.find_look_at_rotation(u.Vector(*eye),u.Vector(*target)),False,False)
    pc.set_view_target_with_blend(camera,0);console('ShowFlag.Rendering 1');yield 2
    u.GameplayStatics.set_game_paused(world,True);yield 3
    path=OUT/(name+'.png');stamp=time.time()
    console('HighResShot 1440x900 filename="'+path.as_posix()+'"')
    end=time.monotonic()+60
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end,'Screenshot timeout';yield .25
    # HighResShot can publish again after the first file write. Keep rendering
    # enabled until that request drains, otherwise the second write is black.
    last=path.stat().st_mtime;stable=time.monotonic()
    while time.monotonic()-stable<5:
        yield .25
        if path.stat().st_mtime!=last:last=path.stat().st_mtime;stable=time.monotonic()
    assert path.stat().st_size>40000,'Empty/black render: '+name
    u.GameplayStatics.set_game_paused(world,False);console('ShowFlag.Rendering 0');yield .1
def run():
    global world,pc,car,surface,camera
    les=u.get_editor_subsystem(u.LevelEditorSubsystem)
    for label,suffix in [('baseline',''),('firm','_Firm'),('deep_soft','_DeepSoft')]:
        assert les.load_level(BASE+suffix);yield 3
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 10
        world=u.EditorLevelLibrary.get_game_world();assert world
        pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();assert car
        old=u.GameplayStatics.get_player_pawn(world,0)
        if old and old!=car:old.set_actor_hidden_in_game(True)
        old=None;pc.possess(car);car.disable_input(pc)
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
        surface.follow_player=False;surface.observe_player_wheels=True
        car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(-950,0,150),u.Rotator(),False,True)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
        move=car.get_chaos_movement();move.set_handbrake_input(True)
        car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
        camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'SoilPropertiesCamera')
        camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(65)
        settings=camera.camera_component.get_editor_property('post_process_settings')
        settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',.6)
        camera.camera_component.set_editor_property('post_process_settings',settings)
        for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60']:console(cmd)
        start=u.GameplayStatics.get_time_seconds(world)
        while u.GameplayStatics.get_time_seconds(world)-start<6:yield .1
        record=dict(name=label,level=BASE+suffix,depth_scale=surface.layer_depth_scale,bearing_strength=surface.bearing_strength,standing=sample(),drive=[])
        report['profiles'].append(record);save()
        # Fixed world camera makes chassis lowering and immersion directly comparable.
        yield from capture('properties_'+label+'_loaded',(-665,-340,160),(-950,0,5))
        start=u.GameplayStatics.get_time_seconds(world);move.set_handbrake_input(False)
        while u.GameplayStatics.get_time_seconds(world)-start<8:
            move.set_throttle_input(.6);move.set_brake_input(0)
            record['drive'].append(sample());yield .2
        car.reset_driving_inputs();move.set_handbrake_input(True);record['end']=sample();save()
        car.set_actor_hidden_in_game(True);surface.observe_player_wheels=False
        yield from capture('properties_'+label+'_tracks',(-1180,-240,100),(-600,0,-6))
        record['surface_report']=surface.get_surface_report();save()
        u.EditorLevelLibrary.editor_end_play();yield 5
        mesh=move=world=pc=car=surface=camera=None
        assert les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();yield 3
    for p in report['profiles']:
        p['standing_mean_settlement_cm']=statistics.fmean(w['total_settlement_cm'] for w in p['standing']['wheels'])
        p['travel_cm']=math.dist(p['drive'][0]['position'][:2],p['end']['position'][:2])
        p['contact_fraction']=statistics.fmean(w['contact'] for s in p['drive'] for w in s['wheels'])
    b,f,d=report['profiles']
    report['checks']={'deeper_than_baseline':d['standing_mean_settlement_cm']>b['standing_mean_settlement_cm']+3,
        'firm_less_than_baseline':f['standing_mean_settlement_cm']<b['standing_mean_settlement_cm']-3,
        'deep_chassis_lower':d['standing']['position'][2]<b['standing']['position'][2]-3,
        'contact_retained':all(p['contact_fraction']>.95 for p in report['profiles'])}
    log=(ROOT/'Saved/Logs/MudProvingGround-PropertiesReview.log').read_text(errors='replace')
    assert not any('Failed to compile Material' in line and 'MudProvingGround' in line for line in log.splitlines()),'Soil shader compilation failed'
    report['ok']=all(report['checks'].values());save()
    u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
steps=run();deadline=0;busy=False;started=time.monotonic()
def tick(dt):
    global deadline,busy
    if busy:return
    busy=True
    try:
        assert time.monotonic()-started<600,'Properties review deadline exceeded'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:pass
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error'])
        u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
