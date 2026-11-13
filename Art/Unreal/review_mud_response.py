"""Real vehicle passes, transverse old-rut crossing and shallow-sod studies."""
import sys,json,time,traceback,re
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from check_render import Gate
OUT=ROOT/'Art/Export/MudResponse';BASE='/Game/GrandTour/ArtTests/MudResponse'
PHYSICS_ONLY='-GTMudResponsePhysicsOnly' in u.SystemLibrary.get_command_line()
CAPTURE_LITE='-GTMudResponseCaptureLite' in u.SystemLibrary.get_command_line()
DRIVING_ONLY='-GTMudResponseDrivingOnly' in u.SystemLibrary.get_command_line()
report=dict(ok=False,images=[],samples=[],crossing=[],settling=[],soil_yield=[],checks={},handling_changed=True,performance_measured=False)
report['capture_shadows']='raster review override' if CAPTURE_LITE else 'project settings'
state='load';started=last=time.monotonic();world=pc=car=surface=fx=camera=rt=None;busy=False;gate=Gate(24 if DRIVING_ONLY else 80);tyres=[]

def stats(text):return {k:float(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+)',text)}
def sample():
    wheels=car.get_traction().wheels;body=car.get_component_by_class(u.GTBodyStateComponent)
    tuning=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
    ground=[surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y)) for w in wheels]
    return dict(t=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),speed=car.get_velocity().length(),
        rotation=[car.get_actor_rotation().pitch,car.get_actor_rotation().yaw,car.get_actor_rotation().roll],support=[w.ground_support_cm for w in tuning.wheels],support_active=[w.get_editor_property('bLandscapeSupport') for w in tuning.wheels],
        sinkage=[w.sinkage_cm for w in tuning.wheels],load=[w.load for w in wheels],soil_depth=[s.sinkage_cap_cm for s in ground],
        compression=[s.compression_cm for s in ground],ground_height=[s.surface_delta_cm for s in ground],
        rest_support=[u.GTLandscapeSurface.query_wheel_surface(car,w.contact_point,w.tyre_heading,25).rest_wheel_support_cm for w in wheels],
        coat=[body.get_tyre_coat(i) for i in range(4)],tread=[w.tread_cm_per_s for w in wheels],contacts=[w.get_editor_property('bInContact') for w in wheels],
        effects=stats(fx.get_effect_report()),field=stats(surface.get_surface_report()))
def finish(error=None):
    global state,last,world,pc,car,surface,fx,camera,rt
    if error:report['error']=error;u.log_error(error)
    report['ok']=not error and all(report['checks'].values())
    (OUT/('contact-report.json' if PHYSICS_ONLY else 'review-report.json')).write_text(json.dumps(report,indent=2))
    cards=''.join('<figure><img src="'+Path(p).name+'"><figcaption>'+Path(p).stem.replace('_',' ')+'</figcaption></figure>' for p in report['images'])
    if CAPTURE_LITE:cards='<p>Screenshots use raster shadows and software Lumen to avoid a GPU stall in the review process. Saved scene lighting is unchanged.</p>'+cards
    if not PHYSICS_ONLY:(OUT/'mud-response.html').write_text('<!doctype html><meta charset="utf-8"><title>Mud driving response</title><style>body{background:#20241f;color:#ede6d5;font:17px system-ui;margin:32px}main{display:grid;grid-template-columns:1fr 1fr;gap:20px}figure{margin:0}img{width:100%}</style><h1>Mud driving response</h1><p>Loaded tyres gradually sink into soft soil while permanent compression preserves the existing bog relief. Compacted tracks and grass yield less; the firm base limits penetration. Includes a transverse crossing of old tracks. Tyres retain their physical radius; local soil contacts follow loaded settlement and deformed terrain. Grip weakens with wheelspin, and resistance rises with speed and immersion. Chassis collision still uses the original landscape. Grass panels are prescribed 2 / 5 / 8 cm soil studies.</p><main>'+cards+'</main>',encoding='utf-8')
    if world:u.GameplayStatics.set_game_paused(world,False)
    if rt:u.RenderingLibrary.release_render_target2d(rt)
    tyres.clear();world=pc=car=surface=fx=camera=rt=None
    u.EditorLevelLibrary.editor_end_play();state='ending';last=time.monotonic()
def aim(eye,target):
    camera.set_actor_location_and_rotation(eye,u.MathLibrary.find_look_at_rotation(eye,target),False,False);pc.set_view_target_with_blend(camera,0)
def capture(name,next_state,eye=None,target=None):
    global state,shot,next_phase,shot_time,prime_frame
    if PHYSICS_ONLY or (DRIVING_ONLY and name not in ['03_driven_ruts','07_crossing_existing_ruts']):state=next_state;return
    if eye is not None:aim(eye,target)
    gate.set(world,pc,True)
    shot=name;next_phase=next_state;state='camera_prime';shot_time=0;prime_frame=gate.frame
def position(x=-850,y=0,yaw=0):
    car.reset_driving_inputs();car.set_actor_location_and_rotation(u.Vector(x,y,140),u.Rotator(pitch=0,yaw=yaw,roll=0),False,True)
    assert abs(car.get_actor_rotation().yaw-yaw)<.1, 'Review vehicle heading was not applied'
    mesh=car.get_component_by_class(u.SkeletalMeshComponent);mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
def body():
    global state,last,world,pc,car,surface,fx,camera,rt,move,sim0,next_sample,shot_time,grass_index
    now=time.monotonic()
    if state=='ending':
        if now-last>5 and u.EditorLevelLibrary.get_game_world() is None:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        return
    if now-started>600:raise RuntimeError('Mud response review timed out: '+state)
    if state=='load':
        assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(BASE+'/L_MudResponse');state='play';last=now
    elif state=='play' and now-last>8:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);state='warm';last=now
    elif state=='warm' and now-last>12:
        world=u.EditorLevelLibrary.get_game_world()
        if not world:return
        pc=u.GameplayStatics.get_player_controller(world,0);old=u.GameplayStatics.get_player_pawn(world,0)
        if old:old.set_actor_hidden_in_game(True)
        car=pc.get_car() or u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.GTCarPawn,u.Transform(u.Vector(-850,0,140)),'MudResponseCar')
        pc.possess(car);car.disable_input(pc);car.set_actor_hidden_in_game(False);position()
        move=car.get_chaos_movement();move.set_handbrake_input(True);car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
        surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
        surface.observe_player_wheels=True;surface.follow_player=False
        fx=surface.get_component_by_class(u.GTLandscapeWheelEffects);assert fx
        camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'MudResponseCamera');camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(65)
        settings=camera.camera_component.get_editor_property('post_process_settings')
        settings.set_editor_property('override_auto_exposure_bias',True);settings.set_editor_property('auto_exposure_bias',.8)
        camera.camera_component.set_editor_property('post_process_settings',settings)
        mesh=car.get_component_by_class(u.SkeletalMeshComponent)
        for i in range(mesh.get_num_materials()):
            old=mesh.get_material(i)
            if old and 'Tyre' in old.get_base_material().get_name():
                new=mesh.create_dynamic_material_instance(i,u.load_asset(BASE+'/M_ResponseTyre'))
                tyres.append((old,new));report.setdefault('tyre_slots',[]).append(i)
        for cmd in ['showhud','DisableAllScreenMessages','r.MotionBlurQuality 0']:u.SystemLibrary.execute_console_command(world,cmd,pc)
        gate.start_dt();gate.set(world,pc,False);sim0=u.GameplayStatics.get_time_seconds(world);state='settle'
    if not world:return
    gate.tick(world)
    # HighResShot performs its own readback. An unrelated synchronous pixel read
    # every frame stalls this callback under GPU contention and prevents timeouts.
    for old,new in tyres:
        for key in ['TyreCoat','WheelGeom']:new.set_vector_parameter_value(key,old.get_vector_parameter_value(key))
        for key in ['MudWet','MudSlice','Wetness','CarMud']:new.set_scalar_parameter_value(key,old.get_scalar_parameter_value(key))
    t=u.GameplayStatics.get_time_seconds(world)-sim0
    if state=='settle' and t>3:
        report['idle']=sample();report['checks']['idle_no_spray']=report['idle']['effects']['rate']==0
        u.log('MudResponse: idle complete '+json.dumps(report['idle']))
        sim0=u.GameplayStatics.get_time_seconds(world);t=0;next_sample=0;move.set_handbrake_input(False);state='drive'
    elif state=='support_prepare':
        state='cross_prepare'
    elif state=='support_off' and t>3:
        report['support_off']=sample();surface.enable_wheel_support=True
        sim0=u.GameplayStatics.get_time_seconds(world);state='support_on'
    elif state=='support_on' and t>3:
        report['support_on']=sample()
        lift=report['support_on']['position'][2]-report['support_off']['position'][2]
        expected=sum(h-d for h,d in zip(report['support_on']['support'],report['support_on']['sinkage']))/4
        report['support_body_shift_cm']=lift
        u.log('MudResponse: support chassis shift='+str(lift)+' expected='+str(expected))
        report['checks']['support_moves_chassis']=abs(lift)>.25 and lift*expected>0 and abs(lift-expected)<2
        report['checks']['loaded_tyres_sink']=sum(report['support_on']['sinkage'])/4>2
        early=report['settling'][0];late=report['support_on']
        report['checks']['settles_progressively']=sum(late['sinkage'])>sum(early['sinkage'])+4
        move.set_handbrake_input(False);sim0=u.GameplayStatics.get_time_seconds(world);t=0;next_sample=0;state='cross_drive'
    if state=='support_on':report['settling'].append(sample())
    if state=='drive':
        move.set_throttle_input(.65);move.set_brake_input(0);car.set_raw_steer(0)
        if t>=next_sample:
            report['samples'].append(sample());next_sample=t+.2
        if t>7:
            report['first_pass_end']=sample()
            p=car.get_actor_location();capture('01_vehicle_mud_spray','repeat',p+u.Vector(-620,650,230),p+u.Vector(-60,0,0))
    elif state=='repeat':
        position();move.set_handbrake_input(False);sim0=u.GameplayStatics.get_time_seconds(world);state='drive_repeat'
    elif state=='drive_repeat':
        move.set_throttle_input(.6);move.set_brake_input(0)
        if t>7:
            report['repeat']=sample();p=car.get_actor_location();capture('02_coated_tyres','support_prepare',p+u.Vector(310,220,100),p+u.Vector(140,65,32))
    elif state=='cross_prepare':
        surface.observe_player_wheels=False
        report['cross_x']=(-850+report['first_pass_end']['position'][0])*.5
        position(report['cross_x'],-210,90);move.set_handbrake_input(True)
        surface.enable_wheel_support=False;sim0=u.GameplayStatics.get_time_seconds(world);state='support_off'
    elif state=='cross_drive':
        move.set_throttle_input(.55);move.set_brake_input(0)
        if t>=next_sample:report['crossing'].append(sample());next_sample=t+.05
        if t>8 or car.get_actor_location().y>230:
            active=[v for s in report['crossing'] for v,a in zip(s['support'],s['support_active']) if a]
            report['checks']['wheel_support_reads_bog']=len(active)>20 and max(active)-min(active)>1
            report['checks']['support_bounded']=all(-20.01<=v<=12.01 for s in report['crossing'] for v in s['support'])
            report['checks']['crossing_keeps_contact']=sum(sum(s['contacts']) for s in report['crossing'])>=len(report['crossing'])*3
            report['checks']['crosses_old_tracks']=car.get_actor_location().y>180
            # Clumps can crush further than the average footprint. Limit the actual
            # rut below its original footprint, rather than counting a crushed crest.
            report['checks']['rolling_compression_bounded']=max(r-h for s in report['samples'] for r,h in zip(s['rest_support'],s['support']))<16
            loaded=report['samples']+report['crossing']+report['settling']+[report['idle']]
            report['checks']['yield_above_firm_base']=all(h-d>=-depth-.01 and 0<=d<=19.01 for s in loaded for h,d,depth,a in zip(s['support'],s['sinkage'],s['soil_depth'],s['support_active']) if a)
            settled=report['support_on']
            report['loaded_settlement_cm']=[r-h+d for r,h,d in zip(settled['rest_support'],settled['support'],settled['sinkage'])]
            report['checks']['bog_has_substantial_loaded_settlement']=sum(report['loaded_settlement_cm'])/4>8
            p=car.get_actor_location();capture('07_crossing_existing_ruts','yield_prepare',p+u.Vector(460,-450,190),p+u.Vector(0,0,-20))
    elif state=='yield_prepare':
        surface.observe_player_wheels=False;position(580,0,0);move.set_handbrake_input(True)
        sim0=u.GameplayStatics.get_time_seconds(world);state='yield_settle'
    elif state=='yield_settle' and t>3:
        probes=[]
        for w in car.get_traction().wheels:
            for dx in [-6.25,0,6.25]:
                for dy in [-6.25,0,6.25]:probes.append([w.contact_point.x+dx,w.contact_point.y+dy])
        report['yield_probes']=probes
        report['yield_before']=[surface.sample_surface(u.Vector2D(*p)).surface_delta_cm for p in probes]
        report['yield_before_body_z']=car.get_actor_location().z
        surface.observe_player_wheels=True;sim0=u.GameplayStatics.get_time_seconds(world);next_sample=0;state='yield_load'
    elif state=='yield_load':
        if t>=next_sample:
            report['soil_yield'].append(dict(t=t,height=[surface.sample_surface(u.Vector2D(*p)).surface_delta_cm for p in report['yield_probes']]))
            next_sample=t+.2
        if t>2:
            drops=[a-b for a,b in zip(report['yield_before'],report['soil_yield'][-1]['height'])]
            report['yield_ground_drop_cm']=max(drops)
            report['yield_body_drop_cm']=report['yield_before_body_z']-car.get_actor_location().z
            report['checks']['loaded_ground_itself_yields']=max(drops)>1 and sum(d>0.5 for d in drops)>=4
            state='ground'
    elif state=='ground':
        move.set_throttle_input(0);move.set_brake_input(0);move.set_handbrake_input(True);car.set_actor_hidden_in_game(True)
        surface.observe_player_wheels=False
        report['checks']['car_spray_emitted']=report['repeat']['effects']['emitted']>0
        report['checks']['tyres_pick_up_mud']=max(report['repeat']['coat'])>.25
        report['checks']['soil_volume_balanced']=abs(report['repeat']['field']['balance_cm3'])<.01
        cx=report['cross_x']
        capture('03_driven_ruts','grass_prepare',u.Vector(cx+350,-330,165),u.Vector(cx-70,0,-5))
    elif state=='grass_prepare':
        # Prescribed equal wheel work exposes the contrasting depth and intact-sod response.
        for cx,depth in [(-1000,2),(0,5),(1000,8)]:
            for x in range(cx-340,cx+340,12):
                for y in [730,910]:surface.stamp_wheel(u.Vector2D(x,y),u.Vector2D(x+12,y),u.Vector2D(1,0),28,depth)
        grass_index=0;state='grass_warm';sim0=u.GameplayStatics.get_time_seconds(world)
    elif state=='grass_warm' and t>.2:
        cx=[-1000,0,1000][grass_index];name=['04_firm_turf_2cm','05_damp_grass_5cm','06_wet_grass_8cm'][grass_index]
        depth=surface.sample_surface(u.Vector2D(cx,730)).surface_delta_cm
        report['checks'][name+'_finite_depth']=depth>=-[2,5,8][grass_index]-.2
        capture(name,'grass_next',u.Vector(cx-180,580,340),u.Vector(cx+70,825,0))
    elif state=='grass_next':
        grass_index+=1
        if grass_index==3:finish();return
        state='grass_warm';sim0=u.GameplayStatics.get_time_seconds(world)
    if state=='camera_prime' and gate.frame-prime_frame>2:
        u.GameplayStatics.set_game_paused(world,True);state='capture'
    if state=='capture' and gate.ready(world,pc):
        path=OUT/(shot+'.png');shot_time=time.time();u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc);state='capture_wait'
    elif state=='capture_wait':
        path=OUT/(shot+'.png')
        if path.exists() and path.stat().st_mtime>=shot_time:
            report['images'].append(str(path));u.GameplayStatics.set_game_paused(world,False);gate.set(world,pc,False);state=next_phase
def tick(dt):
    global busy
    if busy:return
    busy=True
    try:body()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
