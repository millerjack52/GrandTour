"""Load, collision-survey, render and drive representative parts of the Mackenzie blockout."""
import unreal as u
import json, math, time, traceback
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve(); OUT=ROOT/'Art/Export/MackenzieBlockout'
setup=json.loads((OUT/'setup-report.json').read_text()); assert setup['ok']
LEVEL=setup['level']; lib=u.GTVehicleSetupLibrary
report={'ok':False,'level':LEVEL,'runs':[],'images':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase='load'; last=time.monotonic(); started=last; index=0
cases=[('Start',20.,110.,False),('Ford',setup['ford_arc_m']-38,setup['ford_arc_m']+40,False),('Ridge',1338.,1428.,False),('Shortcut',45.,130.,True),('Shortcut_Climb',430.,530.,True),('Shortcut_Exit',620.,setup['shortcut_length_m']-1.,True)]

def save(): (OUT/'drive-report.json').write_text(json.dumps(report,indent=2))
def finish(error=None):
    global phase
    phase='done'; report['ok']=not error
    if error: report['error']=error
    save(); u.unregister_slate_post_tick_callback(handle)
    u.EditorLevelLibrary.editor_end_play(); u.SystemLibrary.quit_editor()

def console(command): u.SystemLibrary.execute_console_command(world,command,pc)
def shot(name):
    path=OUT/(name+'.png'); report['images'].append(str(path))
    console('HighResShot 1440x900 filename="'+path.as_posix()+'"')

def point(arc,alt=False):
    return lib.terrain_alt_route_point_cm(spec,0,arc) if alt else lib.terrain_route_point_cm(spec,arc)

def nearest(p,alt):
    rows=setup['shortcut'] if alt else setup['route']
    row=min(rows,key=lambda r:(r['x_m']*100-p.x)**2+(r['y_m']*100-p.y)**2)
    return row['arc_m'],math.hypot(row['x_m']*100-p.x,row['y_m']*100-p.y)/100

def tick(dt):
    global phase,last,index,world,pc,car,move,body,camera,spec,row,drive_started,max_lateral,peak_speed
    now=time.monotonic()
    try:
        if now-started>600: finish('Check timed out'); return
        if phase=='load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
            spec=u.load_asset('/Game/GrandTour/Demo/MackenzieBlockout/DA_Mackenzie_Blockout').spec
            phase='loaded'; last=now
        elif phase=='loaded' and now-last>3:
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play(); phase='warm'; last=now
        elif phase=='warm' and now-last>15:
            world=u.EditorLevelLibrary.get_game_world(); assert world
            pc=u.GameplayStatics.get_player_controller(world,0); car=u.GameplayStatics.get_player_pawn(world,0)
            assert isinstance(car,u.GTCarPawn),'No drivable GT car spawned'
            car.disable_input(pc); car.reset_driving_inputs(); move=car.get_chaos_movement(); body=car.get_component_by_class(u.SkeletalMeshComponent)
            console('gt.Look.Post 0'); console('gt.Look.Kuwahara 0'); console('gt.Look.Weather Clear'); console('t.MaxFPS 30')
            report['pawn']=car.get_class().get_name()
            # Saved terrain collision, including both shortcut junctions and the loop seam.
            errors=[]; misses=[]; worst=0.; count=0
            actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
            ignore=[a for a in actors if not isinstance(a,u.LandscapeProxy)]
            for route in [setup['route'],setup['shortcut']]:
                for entry in route[::2]:
                    x,y=entry['x_m']*100,entry['y_m']*100
                    for offset in [-1.4,0,1.4]:
                        rad=math.radians(entry['yaw']); px=x-math.sin(rad)*offset*100; py=y+math.cos(rad)*offset*100
                        hit=u.SystemLibrary.line_trace_single(world,u.Vector(px,py,15000),u.Vector(px,py,-15000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
                        count+=1
                        if hit is None: misses.append([px,py]); continue
                        vecs=[v for v in hit.to_tuple() if isinstance(v,u.Vector)]
                        error=abs(vecs[0].z-lib.sample_terrain_height_cm(spec,px,py)); worst=max(worst,error)
                        if error>35: errors.append({'x':px,'y':py,'delta_cm':error})
            report['collision']={'samples':count,'misses':len(misses),'max_height_error_cm':worst,'errors':errors[:8]}
            assert not misses and not errors,report['collision']
            camera=lib.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'BlockoutReviewCamera')
            camera.set_actor_location(u.Vector(85000,-100000,95000),False,False)
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(0,0,1200)),False); camera.camera_component.set_field_of_view(55)
            pc.set_view_target_with_blend(camera,0.); move.set_handbrake_input(True)
            phase='overview'; last=now; save()
        elif phase=='overview' and now-last>4:
            shot('Overview'); phase='case'; last=now
        elif phase=='case' and now-last>2:
            name,a,b,alt=cases[index]; p,yaw=point(a,alt)
            ground=lib.sample_terrain_height_cm(spec,p.x,p.y)
            car.set_actor_location_and_rotation(u.Vector(p.x,p.y,ground+150),u.Rotator(yaw=yaw),False,True)
            body.set_physics_linear_velocity(u.Vector()); body.set_physics_angular_velocity_in_degrees(u.Vector())
            car.reset_driving_inputs(); move.set_handbrake_input(True); move.set_target_gear(1,True)
            pc.set_view_target_with_blend(car,0.); car.set_chase_camera(True)
            row={'name':name,'start_arc_m':a,'target_arc_m':b}; report['runs'].append(row)
            max_lateral=0.; peak_speed=0.; phase='settle'; last=now
        elif phase=='settle' and now-last>4:
            row['ground_contacts']=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)]
            assert sum(row['ground_contacts'])>=3,('Car did not settle',row)
            shot(cases[index][0]+'_Driver'); car.reset_driving_inputs(); move.set_handbrake_input(False)
            phase='drive'; drive_started=u.GameplayStatics.get_time_seconds(world); last=now
        elif phase=='drive':
            name,a,b,alt=cases[index]; p=car.get_actor_location(); arc,dist=nearest(p,alt)
            speed=car.get_velocity().length()/100; peak_speed=max(peak_speed,speed); max_lateral=max(max_lateral,dist)
            target,_=point(min(b+10,arc+max(9.,speed*1.2)),alt)
            wanted=math.atan2(target.y-p.y,target.x-p.x); yaw=math.radians(car.get_actor_rotation().yaw)
            delta=(wanted-yaw+math.pi)%(2*math.pi)-math.pi
            steering=math.atan2(2*2.6*math.sin(delta),max(9.,speed*1.2))/math.radians(33)
            car.set_raw_steer(max(-.8,min(.8,steering)))
            desired=4.5 if name=='Ford' else 8.
            move.set_throttle_input(max(0.,min(.65,(desired-speed)*.25+.16)))
            move.set_brake_input(max(0.,min(.6,(speed-desired-1)*.2)))
            elapsed=u.GameplayStatics.get_time_seconds(world)-drive_started
            assert abs(car.get_actor_rotation().roll)<50,('Vehicle rolled',name)
            assert p.z>-1000,('Vehicle fell below terrain',name)
            if arc>=b:
                row.update(completed=True,end_arc_m=arc,elapsed_sim_s=elapsed,peak_kmh=peak_speed*3.6,max_nearest_sample_distance_m=max_lateral)
                assert max_lateral<5.0,('Vehicle left route',row)
                move.set_throttle_input(0.); move.set_brake_input(1.); save(); index+=1
                if index==len(cases): finish(); return
                phase='case'; last=now
            elif elapsed>65: raise RuntimeError('Drive section stalled: '+str((name,arc,b,speed,elapsed)))
    except Exception: finish(traceback.format_exc())

handle=u.register_slate_post_tick_callback(tick)
