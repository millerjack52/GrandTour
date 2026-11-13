"""Actual possessed car, normal hull/tyre updates, untimed functional visual review.

Initial teleports/velocities put the real vehicle in repeatable cases. Thereafter normal
throttle/gear/brake inputs drive it. Capture pauses preserve each requested image state.
This is not a handling benchmark or a frame-time measurement; the map is never saved.
"""
import unreal as u
import sys,json,time,traceback,math,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
import install_benmore_gaea_creek as shared
from check_render import Gate
GATE=Gate(warm=6);pace_rt=None;fixed_dts=[]
CAPTURE_ONLY=bool(os.environ.get('GT_WATER_REVIEW_OUT'))
SURFACE_DETAIL='WaterSurface_' in os.environ.get('GT_WATER_REVIEW_OUT','')
CONTACT_FOAM='WaterSurface_Foam_' in os.environ.get('GT_WATER_REVIEW_OUT','')
FOCUSED_FRONT='WaterSurface_Foam_Focused_' in os.environ.get('GT_WATER_REVIEW_OUT','')
MOTION_REVIEW='Focused_Motion_' in os.environ.get('GT_WATER_REVIEW_OUT','')
if CONTACT_FOAM:GATE=Gate(warm=30)
OUT=ROOT/'Art/Export/BenmoreGaea/WaterInteraction/RealismFinal';OUT.mkdir(exist_ok=True)
report=dict(ok=False,timings_collected=False,actual_vehicle=True,images=[],samples=[])
phase='load';last=time.monotonic();started=last;case_index=-1;pending=None;frame=0
CASES=[('Crawl',-3,1.8,6),('Crossing',-5,5.0,4),('Reverse',3,-2.5,5),('Dry',-15,0,2),('DriverCrossing',-5,5,4),('AlongRiver',-2,3,6)]
PRONOUNCED='-GTPronouncedWaves' in u.SystemLibrary.get_command_line()
if PRONOUNCED:
    CASES=[('Crawl',-3,1.8,3),('Crossing',-5,5.0,3),('Reverse',3,-2.5,3),
        ('Dry',-15,0,1),('DriverCrossing',-5,5,3),('AlongRiver',-2,3,3.5)]
if '-GTFoamFocus' in u.SystemLibrary.get_command_line():
    assert CONTACT_FOAM and PRONOUNCED
    CASES=[('AlongRiver',-2,3,3.5),('Dry',-15,0,1)]
    report['review_scope']='Focused material review: along-river foam and dry-ground checks, plus BowView when testing the focused contact front.'
if FOCUSED_FRONT:
    CASES.append(('BowView',-2,3,2.5))
if MOTION_REVIEW:
    CASES.append(('SteeringIsolation',-2,2,2.5))
if '-GTWaveFinish' in u.SystemLibrary.get_command_line():
    OUT=ROOT/'Art/Export/BenmoreGaea/WaterInteraction/WakeFinish';OUT.mkdir(exist_ok=True)
    CASES=[('AlongRiver',-2,3,4)]
p=shared.crossings[0]['center_m'];n=shared.crossings[0]['cross_direction'];f=shared.crossings[0]['flow_direction']
centre=u.Vector(p[0]*100,p[1]*100,p[2]*100);direction=u.Vector(n[0],n[1],0)
REPORTED='-GTReportedCrossing' in u.SystemLibrary.get_command_line()
if REPORTED:
    # Reproduce the approach in the owner's 2026-10-10 Play log, separately
    # from the previously reviewed ford. No authored placement is changed.
    OUT=Path(os.environ['GT_WATER_REVIEW_OUT']);OUT.mkdir(parents=True,exist_ok=False)
    p=(-805,22,0);n=(0,1);f=(1,0)
    centre=u.Vector(p[0]*100,p[1]*100,0);direction=u.Vector(0,1,0)
    CASES=[('ReportedCrossing',-14,3.5,14)]
    report['scope']='Approximate reported route from moving-window log; functional diagnosis, not FPS or handling validation.'
elif os.environ.get('GT_WATER_REVIEW_OUT'):
    OUT=Path(os.environ['GT_WATER_REVIEW_OUT']);OUT.mkdir(parents=True,exist_ok=True)
u.EditorPythonScripting.set_keep_python_script_alive(True)

def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def capture(path):
    size='960x600' if REPORTED or os.environ.get('GT_WATER_REVIEW_OUT') or '-GTWaveFinish' in u.SystemLibrary.get_command_line() else '1280x800'
    console('HighResShot '+size+' filename="'+path.as_posix()+'"')
def wake_materials(enabled,parameter='WakeDetailReady'):
    components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
    for c in components:c.get_material(0).set_scalar_parameter_value(parameter,1 if enabled else 0)
def save():(OUT/'vehicle-review.json').write_text(json.dumps(report,indent=2))
def finish(error=None):
    global phase,last,pace_rt
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    if fixed_dts:report['fixed_dt']={'min':min(fixed_dts),'max':max(fixed_dts),'frames':len(fixed_dts),'ok':all(abs(d-1/60)<1e-4 for d in fixed_dts)}
    report['capture_rendering']=GATE.report()['render']
    save()
    if 'world' in globals():u.GameplayStatics.set_game_paused(world,False)
    if pace_rt:u.RenderingLibrary.release_render_target2d(pace_rt)
    pace_rt=None
    for name in ['world','pc','car','move','body','camera','sheet','ignore']:globals()[name]=None
    u.EditorLevelLibrary.editor_end_play();phase='shutdown';last=time.monotonic()

def ground(x,y):
    hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,100000),u.Vector(x,y,-10000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
    if hit:
        vectors=[v for v in hit.to_tuple() if isinstance(v,u.Vector)]
        return vectors[0].z
    raise RuntimeError('Ground trace missed')

def aim():
    at=car.get_actor_location();target=at+u.Vector(0,0,35)
    pos=at+u.Vector(f[0]*680-n[0]*460,f[1]*680-n[1]*460,320)
    if case_index>=0 and CASES[case_index][0]=='DriverCrossing':
        pos=at-car.get_actor_forward_vector()*650+u.Vector(0,0,240)
        target=at+car.get_actor_forward_vector()*120
    if case_index>=0 and CASES[case_index][0]=='AlongRiver':
        pos=at-car.get_actor_forward_vector()*620+car.get_actor_right_vector()*660+u.Vector(0,0,480)
        target=at+car.get_actor_forward_vector()*130
    if case_index>=0 and CASES[case_index][0] in ('BowView','SteeringIsolation'):
        pos=at+car.get_actor_forward_vector()*680+car.get_actor_right_vector()*430+u.Vector(0,0,250)
        target=at+car.get_actor_forward_vector()*130
    camera.set_actor_location(pos,False,False);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos,target),False)
    camera.camera_component.set_field_of_view(58);pc.set_view_target_with_blend(camera,0)

def sample():
    spray=car.get_spray();hull=car.get_hull();pos=car.get_actor_location()
    wheels=car.get_traction().get_editor_property('wheels')
    return dict(case=CASES[case_index][0],t=round(u.GameplayStatics.get_time_seconds(world)-case_start,3),
        position_cm=pos.to_tuple(),yaw=car.get_actor_rotation().yaw,speed_mps=car.get_velocity().length()*.01,
        splash_rate=spray.get_splash_rate_now(),bow_rate=spray.get_bow_rate_now(),live=spray.get_live_count(u.GTSprayKind.WATER),
        wheel_depth_m=spray.get_splash_deepest_m(),bow_submerged_m=spray.get_bow_submerged_m(),
        lid_m3=hull.get_editor_property('lid_volume_m3'),lift_n=hull.get_editor_property('lift_n'),
        hull_force_n=hull.get_editor_property('last_water_force').to_tuple(),
        wheel_water_forces_n=[w.get_editor_property('water_force_n').to_tuple() for w in wheels],
        wheel_flows_cmps=[w.get_editor_property('flow_cm_per_s').to_tuple() for w in wheels])

def tick(dt):
    global phase,last,world,pc,car,move,body,camera,sheet,ignore,case_index,case_start,next_shot,pending,frame,direction,pace_rt
    now=time.monotonic();frame+=1
    if phase=='shutdown':
        if now-last>3:
            u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        return
    try:
        if CAPTURE_ONLY and 'world' in globals():
            GATE.tick(world)
            if GATE.on:
                if pace_rt is None:pace_rt=u.RenderingLibrary.create_render_target2d(world,1,1,u.TextureRenderTargetFormat.RTF_RGBA8)
                u.RenderingLibrary.read_render_target_pixel(world,pace_rt,0,0)
            if not pending and phase in ('settle','drive') and len(fixed_dts)<300:
                fixed_dts.append(float(u.GameplayStatics.get_world_delta_seconds(world)))
        if now-started>1100:raise RuntimeError('Vehicle review timeout')
        if pending:
            path,requested,issued=pending
            if path.exists() and path.stat().st_mtime>=requested and frame-issued>3:
                report['images'].append(str(path));pending=None;save()
                comparison=None
                if (path.name.startswith('AlongRiver_') or REPORTED) and (report['samples'][-1]['bow_rate']>25 or PRONOUNCED and report['samples'][-1]['splash_rate']>0) and report['samples'][-1]['t']>1 and not report.get('paired_wakes'):
                    report['paired_wakes']={'position_cm':car.get_actor_location().to_tuple(),'game_time':u.GameplayStatics.get_time_seconds(world)}
                    wake_materials(False);comparison=OUT/'Driver_WakesOff.png'
                elif path.name=='Driver_WakesOff.png':
                    wake_materials(True);comparison=OUT/'Driver_WakesOn.png'
                elif path.name=='Driver_WakesOn.png':
                    assert car.get_actor_location().to_tuple()==tuple(report['paired_wakes']['position_cm'])
                    assert u.GameplayStatics.get_time_seconds(world)==report['paired_wakes']['game_time']
                    report['paired_wakes']['same_physics_state']=True;save()
                    if CONTACT_FOAM:
                        wake_materials(False,'FoamVisibility');comparison=OUT/'Driver_FoamOff.png'
                elif path.name=='Driver_FoamOff.png':
                    wake_materials(True,'FoamVisibility');comparison=OUT/'Driver_FoamOn.png'
                elif path.name=='Driver_FoamOn.png':
                    assert car.get_actor_location().to_tuple()==tuple(report['paired_wakes']['position_cm'])
                    assert u.GameplayStatics.get_time_seconds(world)==report['paired_wakes']['game_time']
                    report['paired_foam_same_physics_state']=True;save()
                if comparison:
                    pending=(comparison,time.time(),frame);capture(comparison);return
                if CAPTURE_ONLY:GATE.set(world,pc,False)
                u.GameplayStatics.set_game_paused(world,False)
            elif time.time()-requested>50:raise RuntimeError('Capture timeout '+str(path))
            return
        if phase=='load':
            phase='loading';assert shared.les.load_level(shared.LEVEL);phase='begin';last=now
        elif phase=='begin' and now-last>12:
            shared.les.editor_request_begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>15:
            world=u.EditorLevelLibrary.get_game_world();assert world
            pc=u.GameplayStatics.get_player_controller(world,0)
            cars=u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn);assert cars,'No actual car in the review map'
            # Fleet enumeration order changes as cars are added to the level.
            # Exercise the driver's actual car, not an arbitrary parked vehicle.
            car=next(a for a in cars if a.get_actor_label()==os.environ.get('GT_WATER_REVIEW_CAR','Benmore_Fleet_Ferrari288')) if PRONOUNCED else pc.get_car() or cars[0]
            if PRONOUNCED and pc.get_car()!=car:
                pc.get_car().reset_driving_inputs()
                assert pc.exit_car();assert pc.enter_vehicle(car)
            pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
            move=car.get_chaos_movement();body=car.get_component_by_class(u.SkeletalMeshComponent)
            car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Benmore_RL_Camera_Ford')
            sheet=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_editor_property('water_domain'))
            ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if not isinstance(a,u.LandscapeProxy)]
            report['car']=car.get_class().get_name();report['car_actor']=car.get_actor_label();report['pool_per_kind']=car.get_spray().get_editor_property('pool_per_kind')
            components=[sheet.get_component_by_class(u.ProceduralMeshComponent)]+[a.static_mesh_component for a in sheet.get_editor_property('domain_surfaces')]
            report['water_bindings']=[{'component':c.get_path_name(),'material':c.get_material(0).get_path_name(),
                'parameters':{k:c.get_material(0).get_scalar_parameter_value(k) for k in ['WakeDetailReady','FieldActive','LocalSurface','DetailEnabled','FoamVisibility','AmbientClock']}}
                for c in components]
            if SURFACE_DETAIL:
                assert '/WaterSurface/' in sheet.get_editor_property('surface_material_path')
                assert all(c.get_material(0).get_scalar_parameter_value('FoamVisibility')==1 for c in components)
                report['surface_detail_saved_assets']=True
            report['initial_cvars']={k:u.SystemLibrary.get_console_variable_float_value(k) for k in ['gt.Water.VehicleWaves','gt.Water.WakeRelief','gt.Water.Domain.Detail','gt.Water.InteractionSpray']}
            report['water_defaults']={k:car.get_spray().get_editor_property(k) for k in ['splash_speed_mps','splash_depth_m','splash_rate','bow_spray_mps','bow_spray_rate']}
            water_mesh=next(c for c in car.get_components_by_class(u.InstancedStaticMeshComponent) if c.get_name().startswith('Spray_water'))
            report['spray_mesh']=water_mesh.get_editor_property('static_mesh').get_path_name()
            report['spray_material']=water_mesh.get_material(0).get_path_name()
            assert report['spray_mesh']=='/Engine/BasicShapes/Plane.Plane','Water must use the new spray cards'
            console('t.MaxFPS 30');console('gt.Water.VisualWakeDebug 1');phase='next'
            if CAPTURE_ONLY:GATE.set(world,pc,False)
        elif phase=='next':
            case_index+=1
            if case_index>=len(CASES):
                if MOTION_REVIEW:
                    rows=report['steering_isolation']
                    assert len(rows)>30 and min(x['steer'] for x in rows)<0 and max(x['steer'] for x in rows)>0
                    assert max(x['direction_error_deg'] for x in rows)<10, 'Bow failed to follow controlled body velocity'
                    assert min(x['body_heading_difference_deg'] for x in rows)>15, 'Test did not separate heading from travel'
                    report['steering_isolation_passed']=True
                if SURFACE_DETAIL:
                    clock=sheet.get_component_by_class(u.ProceduralMeshComponent).get_material(0).get_scalar_parameter_value('AmbientClock')
                    assert clock>report['water_bindings'][0]['parameters']['AmbientClock']
                    report['surface_clock_end']=clock
                for name in [c[0] for c in CASES if c[0]!='Dry']:
                    rows=[r for r in report['samples'] if r['case']==name]
                    assert max(r['splash_rate'] for r in rows)>0,name+' never splashed'
                dry=[r for r in report['samples'] if r['case']=='Dry']
                if dry:assert max(r['splash_rate']+r['bow_rate'] for r in dry)==0,'Dry ground emitted water'
                finish();return
            name,offset,speed,duration=CASES[case_index]
            axis=f if name in ('AlongRiver','BowView','SteeringIsolation') else n
            # Existing 0.39 m reach sampled from the accepted Morphology domain.
            # Gives an unobstructed wet-bow view; no authored level edit.
            origin=centre
            if name in ('BowView','SteeringIsolation'):
                origin=u.Vector(-80500,3250,0);axis=(-.89578987,-.44447779)
                report['bow_view_reference']={'position_m':[-805,32.5],'depth_m':.385689,'flow_mps':[-.509059,-.252588]}
            direction=u.Vector(axis[0],axis[1],0)
            enabled=0 if name.endswith('Off') else 1
            console('gt.Water.InteractionSpray %d'%enabled);console('gt.Water.InteractionTrails %d'%enabled);console('gt.Water.WakeRelief %s'%('1.5' if enabled else '0'))
            at=origin+direction*(offset*100);at.z=ground(at.x,at.y)+150
            car.reset_driving_inputs();move.reset_vehicle();move.set_brake_input(0);move.set_handbrake_input(True)
            yaw=math.degrees(math.atan2(axis[1],axis[0]))+(30 if name=='SteeringIsolation' else 0)
            car.set_actor_location_and_rotation(at,u.Rotator(pitch=0,yaw=yaw,roll=0),False,True)
            body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector())
            report.setdefault('placements',[]).append(dict(case=name,requested=at.to_tuple(),actual=car.get_actor_location().to_tuple(),yaw=car.get_actor_rotation().yaw))
            sheet.preview_water_at(u.Vector2D(at.x,at.y),0,True);aim();phase='settle';last=u.GameplayStatics.get_time_seconds(world)
        elif phase=='settle' and u.GameplayStatics.get_time_seconds(world)-last>2:
            speed=CASES[case_index][2]
            # GrandTour's own transmission chooses reverse from pedals at rest;
            # Chaos SetTargetGear alone does not select its drive direction.
            if speed and car.get_drivetrain().is_reversing()!=(speed<0):
                move.set_throttle_input(.3 if speed>0 else 0)
                move.set_brake_input(.3 if speed<0 else 0)
                return
            move.set_throttle_input(0);move.set_brake_input(0);move.set_handbrake_input(speed==0)
            if speed:body.set_physics_linear_velocity(direction*(speed*100))
            case_start=u.GameplayStatics.get_time_seconds(world);next_shot=0;phase='drive'
        elif phase=='drive':
            name,offset,target,duration=CASES[case_index];elapsed=u.GameplayStatics.get_time_seconds(world)-case_start
            speed=car.get_velocity().length()*.01
            drive=.65 if target and speed<abs(target) else 0
            brake=.25 if target and speed>abs(target)+.7 else 0
            move.set_throttle_input(brake if target<0 else drive)
            move.set_brake_input(drive if target<0 else brake)
            car.set_raw_steer(.22 if SURFACE_DETAIL and name=='AlongRiver' and elapsed>1 else 0);aim()
            if name=='SteeringIsolation':
                # Diagnostic fixture: hold COM travel while alternating wheel
                # steering, with chassis yaw deliberately 30 degrees off travel.
                steer=1 if int(elapsed/.4)%2 else -1
                car.set_raw_steer(steer)
                v=body.get_physics_linear_velocity();v.x=direction.x*target*100;v.y=direction.y*target*100
                body.set_physics_linear_velocity(v);body.set_physics_angular_velocity_in_degrees(u.Vector())
                if elapsed>.5:
                    m=sheet.get_visual_wake_motion(car)
                    expected=math.atan2(v.y*.01+.252588,v.x*.01+.509059)
                    actual=math.atan2(m.y,m.x)
                    angle=lambda a,b:abs(math.degrees(math.atan2(math.sin(a-b),math.cos(a-b))))
                    report.setdefault('steering_isolation',[]).append(dict(t=elapsed,steer=steer,motion_mps=m.to_tuple(),
                        direction_error_deg=angle(actual,expected),body_heading_difference_deg=angle(actual,math.radians(car.get_actor_rotation().yaw))))
            if elapsed>=duration:move.set_throttle_input(0);move.set_handbrake_input(True);phase='next';return
            if elapsed>=next_shot:
                if CAPTURE_ONLY and not GATE.ready(world,pc):return
                row=sample();report['samples'].append(row)
                path=OUT/('%s_%02d.png'%(name,len([r for r in report['samples'] if r['case']==name])))
                # Keep this actual physics state through the asynchronous screenshot.
                u.GameplayStatics.set_game_paused(world,True)
                pending=(path,time.time(),frame);capture(path)
                next_shot=elapsed+(.4 if PRONOUNCED and name=='AlongRiver' else 1.4 if PRONOUNCED else 1 if REPORTED else .5 if os.environ.get('GT_WATER_REVIEW_OUT') else .4 if '-GTWaveFinish' in u.SystemLibrary.get_command_line() else .2)
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
