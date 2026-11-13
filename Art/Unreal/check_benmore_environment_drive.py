"""Reload the saved DEM road map, survey collision, and drive selected sections."""
import unreal as u
import json,math,time,array,traceback,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreEnvironment/Drive';OUT.mkdir(exist_ok=True);ROAD=ROOT/'Art/Export/BenmoreRoads'
data=json.loads((ROAD/'road-manifest.json').read_text());routes=data['routes']
grid=array.array('f');grid.frombytes((ROAD/'height_local_south_up.f32').read_bytes())
report={'ok':False,'level':data['level'],'runs':[],'images':[]}
phase='load';last=time.monotonic();started=last;index=0
les=u.get_editor_subsystem(u.LevelEditorSubsystem);lib=u.GTVehicleSetupLibrary
def maxgrade(ri,sign=1):
    pts=routes[ri]['points'];i=max(range(1,len(pts)-1),key=lambda j:(pts[j+1]['z_m']-pts[j]['z_m'])*sign)
    return pts[i]['arc_m']
mainclimb=maxgrade(0);hillclimb=maxgrade(1);hilldescent=maxgrade(1,-1)
cases=[('Start',0,40.,150.),('Main_Climb',0,max(10,mainclimb-45),min(routes[0]['length_m']-5,mainclimb+55)),
       ('Branch_Entry',1,10.,115.),('Hill_Climb',1,max(10,hillclimb-45),min(routes[1]['length_m']-5,hillclimb+55)),
       ('Hill_Descent',1,max(10,hilldescent-45),min(routes[1]['length_m']-5,hilldescent+55)),('Branch_Rejoin',1,routes[1]['length_m']-120,routes[1]['length_m']-3)]
if False:
    previous=json.loads((OUT/'drive-report.json').read_text())
    report['runs']=[r for r in previous['runs'] if r.get('completed')]
    report['retained_passes']='Earlier successful cases on identical heightfield; remaining branch cases retested with low range and differential lock'
    completed={r['name'] for r in report['runs']};cases=[c for c in cases if c[0] not in completed]
u.EditorPythonScripting.set_keep_python_script_alive(True)
def height(x,y):
    fx=max(0,min(2015.999999,(x+1250)/2500*2016));fy=max(0,min(2015.999999,(y+1250)/2500*2016));ix=int(fx);iy=int(fy);a=fx-ix;b=fy-iy
    i=iy*2017+ix;return (grid[i]*(1-a)+grid[i+1]*a)*(1-b)+(grid[i+2017]*(1-a)+grid[i+2018]*a)*b
def point(ri,s):
    rows=routes[ri]['points'];f=max(0,min(len(rows)-1.000001,s/routes[ri]['length_m']*(len(rows)-1)));i=int(f);t=f-i
    a,b=rows[i],rows[i+1];x=a['x_m']*(1-t)+b['x_m']*t;y=a['y_m']*(1-t)+b['y_m']*t
    return u.Vector(x*100,y*100,height(x,y)*100),math.degrees(math.atan2(b['y_m']-a['y_m'],b['x_m']-a['x_m']))
def nearest(p,ri):
    row=min(routes[ri]['points'],key=lambda a:(a['x_m']*100-p.x)**2+(a['y_m']*100-p.y)**2)
    return row['arc_m'],math.hypot(row['x_m']*100-p.x,row['y_m']*100-p.y)/100
def save(): (OUT/'drive-report.json').write_text(json.dumps(report,indent=2))
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    save();u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def shot(name):
    file=OUT/(name+'.png');report['images'].append(str(file));console('HighResShot 1600x1000 filename="'+file.as_posix()+'"')
def tick(dt):
    global phase,last,index,world,pc,car,move,body,camera,row,drive_started,max_lateral,peak_speed,reference_land,reference_rt
    now=time.monotonic()
    try:
        if now-started>850:raise RuntimeError('Drive validation timeout')
        if phase=='load':
            phase='loading';assert les.load_level('/Game/GrandTour/Demo/BenmoreFullSite/L_Benmore_TerrainReview')
            ref_world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            assert not any(a.get_actor_label()=='Benmore_Roadside_ArtSample' for a in actors)
            assert ref_world.get_world_settings().get_editor_property('default_game_mode').get_name()=='GameModeBase'
            reference_land=next(a for a in actors if isinstance(a,u.Landscape))
            assert reference_land.get_editor_property('landscape_material').get_name()=='M_Benmore_TerrainReview'
            reference_rt=u.RenderingLibrary.create_render_target2d(ref_world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8)
            phase='reference_warm';last=now
        elif phase=='reference_warm' and now-last>12:
            phase='exporting_reference';assert reference_land.landscape_export_heightmap_to_render_target(reference_rt,True,True);phase='reference_check';last=now
        elif phase=='reference_check' and now-last>10:
            phase='checking_reference';assert reference_land.landscape_export_heightmap_to_render_target(reference_rt,True,True)
            ref_world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            source=array.array('H');source.frombytes((ROOT/'Art/Export/MackenzieRealTerrain/BenmoreFullSite/H_Benmore_UE_2017.r16').read_bytes())
            errors=[]
            for route in routes:
                for p in route['points'][::12]:
                    x=round((p['x_m']+1250)/2500*2016);y=round((p['y_m']+1250)/2500*2016)
                    c=u.RenderingLibrary.read_render_target_pixel(ref_world,reference_rt,x,y)
                    errors.append(abs(((int(c.r)<<8)|int(c.g))-source[y*2017+x])/64)
            report['original_reference']={'samples_in_road_corridors':len(errors),'max_error_m':max(errors),'terrain_only':True};assert max(errors)==0
            assert les.load_level(data['level']);phase='loaded';last=now
        elif phase=='loaded' and now-last>5:
            phase='begin';les.editor_request_begin_play();phase='warm';last=now
        elif phase=='warm' and now-last>18:
            phase='checking';world=u.EditorLevelLibrary.get_game_world();assert world
            pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0);assert isinstance(car,u.GTCarPawn)
            car.disable_input(pc);car.reset_driving_inputs();move=car.get_chaos_movement();body=car.get_component_by_class(u.SkeletalMeshComponent)
            console('gt.Look.Post 0');console('gt.Look.Kuwahara 0');console('gt.Look.Weather Clear');console('t.MaxFPS 30')
            ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if not isinstance(a,u.LandscapeProxy)]
            misses=[];errors=[];samples=0
            for route in routes:
                for p in route['points'][::5]:
                    a=math.radians(p['yaw'])
                    for offset in [-1.4,0,1.4]:
                        x=p['x_m']-math.sin(a)*offset;y=p['y_m']+math.cos(a)*offset;samples+=1
                        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,100000),u.Vector(x*100,y*100,-10000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
                        if hit is None:misses.append([x,y]);continue
                        vecs=[v for v in hit.to_tuple() if isinstance(v,u.Vector)];errors.append(abs(vecs[0].z-height(x,y)*100))
            report['collision']={'samples':samples,'misses':misses,'max_error_cm':max(errors)}
            assert not misses and max(errors)<25,report['collision']
            report['pawn']=car.get_class().get_name();report['saved_map_reloaded']=True
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='Benmore_RouteOverview')
            pc.set_view_target_with_blend(camera,0);move.set_handbrake_input(True);phase='overview';last=now;save()
        elif phase=='overview' and now-last>5:
            phase='capturing';shot('Unreal_Road_Overview');phase='case';last=now
        elif phase=='case' and now-last>3:
            phase='positioning';name,ri,a,b=cases[index];p,yaw=point(ri,a)
            car.set_actor_location_and_rotation(u.Vector(p.x,p.y,p.z+150),u.Rotator(yaw=yaw),False,True)
            body.set_physics_linear_velocity(u.Vector());body.set_physics_angular_velocity_in_degrees(u.Vector())
            car.reset_driving_inputs();move.set_handbrake_input(True);move.set_target_gear(1,True)
            # The steep optional branch is an off-road low-range section.
            car.get_drivetrain().set_low_range(ri==1);car.get_drivetrain().set_diff_lock(ri==1)
            pc.set_view_target_with_blend(car,0);car.set_chase_camera(True)
            row={'name':name,'route':routes[ri]['name'],'start_arc_m':a,'target_arc_m':b,'low_range':ri==1,'diff_lock':ri==1};report['runs'].append(row)
            max_lateral=0.;peak_speed=0.;phase='settle';last=now
        elif phase=='settle' and now-last>4:
            phase='settling';row['ground_contacts']=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(move.get_wheel_state(i))[0]) for i in range(4)]
            assert sum(row['ground_contacts'])>=3,('Car did not settle',row)
            shot(cases[index][0]+'_Driver');car.reset_driving_inputs();move.set_handbrake_input(False)
            phase='drive';drive_started=u.GameplayStatics.get_time_seconds(world);last=now
        elif phase=='drive':
            name,ri,a,b=cases[index];p=car.get_actor_location();arc,dist=nearest(p,ri)
            speed=car.get_velocity().length()/100;peak_speed=max(peak_speed,speed);max_lateral=max(max_lateral,dist)
            target,_=point(ri,min(routes[ri]['length_m'],arc+max(8.,speed*1.2)))
            wanted=math.atan2(target.y-p.y,target.x-p.x);yaw=math.radians(car.get_actor_rotation().yaw);delta=(wanted-yaw+math.pi)%(2*math.pi)-math.pi
            steering=math.atan2(2*2.6*math.sin(delta),max(8.,speed*1.2))/math.radians(33)
            car.set_raw_steer(max(-.8,min(.8,steering)));desired=7 if ri==0 else 5
            move.set_throttle_input(max(0,min(.75,(desired-speed)*.25+.20)));move.set_brake_input(max(0,min(.65,(speed-desired-.6)*.25)))
            elapsed=u.GameplayStatics.get_time_seconds(world)-drive_started
            assert abs(car.get_actor_rotation().roll)<45,('Vehicle rolled',name)
            assert p.z>height(p.x/100,p.y/100)*100-150,('Vehicle fell through',name)
            if arc>=b:
                row.update(completed=True,end_arc_m=arc,elapsed_sim_s=elapsed,peak_kmh=peak_speed*3.6,max_nearest_sample_distance_m=max_lateral)
                assert max_lateral<routes[ri]['width_m']/2,('Vehicle left road',row)
                move.set_throttle_input(0);move.set_brake_input(1);save();index+=1
                if index==len(cases):finish();return
                phase='case';last=now
            elif elapsed>90:raise RuntimeError('Drive section stalled: '+str((name,arc,b,speed,elapsed)))
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
