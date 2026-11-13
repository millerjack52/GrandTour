"""Saved-map POM on/off comparison, low camera and moving-camera checks."""
import unreal as u,json,time,math,array,traceback,statistics
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmorePOM'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive';les=u.get_editor_subsystem(u.LevelEditorSubsystem)
grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
def height(x,y):
    f=(x+1250)/2500*2016;g=(y+1250)/2500*2016;i=int(f);j=int(g);a=f-i;b=g-j;k=j*2017+i
    return (grid[k]*(1-a)+grid[k+1]*a)*(1-b)+(grid[k+2017]*(1-a)+grid[k+2018]*a)*b
routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
views=[]
for name,ri,i,h,pitch in [('Driver',0,40,130,-4),('Detail',0,40,90,-32),('Hillside',1,400,130,-6)]:
    p=routes[ri]['points'][i]
    for enabled in [0,1]:views.append(dict(name=name+('_POM' if enabled else '_NormalOnly'),x=p['x_m'],y=p['y_m'],yaw=p['yaw'],height=h,pitch=pitch,enabled=enabled))
report={'ok':False,'views':[],'level':LEVEL};phase='load';started=last=time.monotonic();index=0;frame_times=[];motion_index=0
u.EditorPythonScripting.set_keep_python_script_alive(True)
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def enable(value):
    u.MaterialLibrary.set_scalar_parameter_value(world,collection,'Enabled',value)
    assert abs(u.MaterialLibrary.get_scalar_parameter_value(world,collection,'Enabled')-value)<.001
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    capped=any(abs(v.get('editor_frame_interval_ms',{}).get('median',0)-125)<.001 for v in report['views'])
    report['performance_comparison_valid']=bool(report['views']) and not capped and error is None
    if capped:report['timing_note']='Editor tick inputs stayed capped at 125 ms; these samples cannot establish POM performance overhead or full-speed temporal stability.'
    if error:report['error']=error;u.log_error(error)
    if 'world' in globals():
        try:enable(1)
        except Exception:report['restore_error']=traceback.format_exc()
    if globals().get('throttle_property'):
        try:performance_settings.set_editor_property(throttle_property,original_throttle)
        except Exception:report['settings_restore_error']=traceback.format_exc()
    (OUT/'validation-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,pc,car,camera,index,frame_times,row,collection,motion_distance,motion_index,performance_settings,original_throttle,throttle_property
    now=time.monotonic()
    try:
        if now-started>650:raise RuntimeError('POM check timeout')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL)
            # This editor settings class is not exported as a named Python type.
            performance_settings=u.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings')
            throttle_property=None
            if performance_settings:
                try:
                    original_throttle=performance_settings.get_editor_property('bThrottleCPUWhenNotForeground')
                    performance_settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
                    throttle_property='bThrottleCPUWhenNotForeground'
                except Exception:report['background_setting_unavailable']=traceback.format_exc()
            report['background_throttling_disabled_for_check']=bool(throttle_property)
            collection=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/MPC_Benmore_GravelPOM');assert collection
            assert collection.get_editor_property('scalar_parameters')[0].get_editor_property('default_value')==1
            m=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            expressions=u.MaterialEditingLibrary.get_material_expressions(m)
            pom=[e for e in expressions if isinstance(e,u.MaterialExpressionCustom) and 'distanceFade' in e.get_editor_property('code')]
            assert len(pom)==1
            report['saved_pom_nodes']=1
            groups=[a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if a.get_actor_label()=='Benmore_ReferenceRoadAggregate']
            assert len(groups)==1
            components=groups[0].get_components_by_class(u.InstancedStaticMeshComponent)
            assert sum(c.get_instance_count() for c in components)==5704
            assert all(str(c.get_collision_profile_name())=='NoCollision' for c in components)
            phase='begin';last=now
        elif phase=='begin' and now-last>10:
            phase='starting';assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,1000)
            phase='warm';last=now
        elif phase=='warm' and now-last>25:
            phase='initializing';world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0)
            car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'POMReview')
            camera.camera_component.set_editor_property('constrain_aspect_ratio',False);camera.camera_component.set_field_of_view(72)
            for cmd in ['gt.Look.Post 0','gt.Look.Kuwahara 0','gt.Look.Weather Clear','showhud','t.MaxFPS 0','r.VSync 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:console(cmd)
            report['viewport']=list(pc.get_viewport_size());phase='view'
        elif phase=='view':
            phase='moving';v=views[index];enable(v['enabled'])
            camera.set_actor_location(u.Vector(v['x']*100,v['y']*100,height(v['x'],v['y'])*100+v['height']),False,False)
            camera.set_actor_rotation(u.Rotator(pitch=v['pitch'],yaw=v['yaw']),False);pc.set_view_target_with_blend(camera,0)
            phase='grow';last=now
        elif phase=='grow' and now-last>(32 if index in [0,4] else 8):
            phase='counting';by_mesh={}
            for land in u.GameplayStatics.get_all_actors_of_class(world,u.LandscapeProxy):
                for c in land.get_components_by_class(u.GrassInstancedStaticMeshComponent):
                    origin,extent,radius=u.SystemLibrary.get_component_bounds(c)
                    if radius>10 and c.get_editor_property('static_mesh'):
                        mesh=c.get_editor_property('static_mesh').get_name();by_mesh[mesh]=by_mesh.get(mesh,0)+1
            assert set(by_mesh)=={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'}
            row=dict(views[index],grass_clusters=by_mesh);report['views'].append(row);frame_times=[];phase='profile';last=now
        elif phase=='profile':
            if dt>0:frame_times.append(dt*1000)
            if now-last>8:
                phase='capturing';times=sorted(frame_times);assert times
                row['editor_frame_interval_ms']={'median':statistics.median(times),'mean':statistics.mean(times),'p95':times[min(len(times)-1,int(.95*len(times)))],'samples':len(times)}
                file=OUT/(row['name']+'.png');row['image']=str(file);console('HighResShot 1600x1000 filename="'+file.as_posix()+'"');phase='next';last=now
        elif phase=='next' and now-last>3:
            index+=1
            if index<len(views):phase='view'
            else:
                phase='motion_setup';enable(1);motion_index=0
                p=routes[0]['points'][40]
                camera.set_actor_location(u.Vector(p['x_m']*100,p['y_m']*100,height(p['x_m'],p['y_m'])*100+130),False,False)
                camera.set_actor_rotation(u.Rotator(pitch=-8,yaw=p['yaw']),False);last=now;phase='motion_warm'
        elif phase=='motion_warm' and now-last>25:
            motion_distance=0;phase='motion';report['motion']={'nominal_speed_m_s':5,'captures':[]}
        elif phase=='motion':
            # Avoid camera jumps across screenshot readback or editor stalls.
            motion_distance+=min(max(dt,0),.05)*5
            p=routes[0]['points'][40];distance=motion_distance;yaw=math.radians(p['yaw'])
            x=p['x_m']+math.cos(yaw)*distance;y=p['y_m']+math.sin(yaw)*distance
            camera.set_actor_location(u.Vector(x*100,y*100,height(x,y)*100+130),False,False)
            if distance>=(motion_index+1)*8:
                phase='motion_capturing';file=OUT/('Motion_'+str(motion_index)+'.png')
                report['motion']['captures'].append(dict(image=str(file),travel_m=distance))
                console('HighResShot 1600x1000 filename="'+file.as_posix()+'"');motion_index+=1;phase='motion'
                if motion_index==5:phase='motion_done';last=now
        elif phase=='motion_done' and now-last>4:finish()
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
