"""Verify grass streaming at separated sites and capture the saved level."""
import unreal as u,json,time,math,array,traceback,statistics
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreCharacter'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive';les=u.get_editor_subsystem(u.LevelEditorSubsystem)
grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
def height(x,y):
    f=(x+1250)/2500*2016;g=(y+1250)/2500*2016;i=int(f);j=int(g);a=f-i;b=g-j;k=j*2017+i
    return (grid[k]*(1-a)+grid[k+1]*a)*(1-b)+(grid[k+2017]*(1-a)+grid[k+2018]*a)*b
routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
views=[]

for name,ri,i in [('Hillside_Vista',1,400),('Terrace_Fence',0,40),('Sheltered_Scrub',1,150)]:
    p=routes[ri]['points'][i];views.append((name,p['x_m'],p['y_m'],p['yaw']))

report={'ok':False,'views':[],'level':LEVEL};phase='load';last=time.monotonic();started=last;index=0;frame_times=[]
u.EditorPythonScripting.set_keep_python_script_alive(True)
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'final-visual-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,pc,car,camera,index,frame_times,row
    now=time.monotonic()
    try:
        if now-started>1100:raise RuntimeError('Vegetation check timeout')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL)
            actors=u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            groups=[a for a in actors if a.get_actor_label()=='Benmore_ReferenceRoadAggregate'];assert len(groups)==1
            count=0
            for c in groups[0].get_components_by_class(u.InstancedStaticMeshComponent):
                count+=c.get_instance_count();assert str(c.get_collision_profile_name())=='NoCollision'
            assert count==5704,count
            report['saved_gravel_instances']=count;report['gravel_collision']='NoCollision'
            verge=next(a for a in actors if a.get_actor_label()=='Benmore_RoadVergeDetail')
            counts={}
            for c in verge.get_components_by_class(u.InstancedStaticMeshComponent):
                assert str(c.get_collision_profile_name())=='NoCollision'
                counts[c.get_editor_property('static_mesh').get_name()]=c.get_instance_count()
            expected=json.loads((ROOT/'Art/Export/BenmoreVerges/setup-report.json').read_text())['instance_total']
            assert sum(counts.values())==expected
            report['saved_verge_instances']=sum(counts.values());report['verge_meshes']=counts
            report['character_actors']={}
            for a in actors:
                if a.get_actor_label().startswith('Benmore_Character_'):
                    row={'position':str(a.get_actor_location()),'instances':sum(c.get_instance_count() for c in a.get_components_by_class(u.InstancedStaticMeshComponent))}
                    for c in a.get_components_by_class(u.StaticMeshComponent):assert str(c.get_collision_profile_name())=='NoCollision'
                    report['character_actors'][a.get_actor_label()]=row
            assert report['character_actors']['Benmore_Character_ShelteredScrub']['instances']==923
            assert report['character_actors']['Benmore_Character_StockFences']['instances']>300
            sky=next(a for a in actors if a.get_actor_label()=='Benmore_Character_SoftSky');assert not sky.get_actor_enable_collision()
            report['height_sha256']=__import__('hashlib').sha256((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes()).hexdigest()
            previous=json.loads((ROOT/'Art/Export/BenmoreEnvironment/completion-report.json').read_text());assert report['height_sha256']==previous['height_sha256']
            phase='begin';last=now
        elif phase=='begin' and now-last>10:
            phase='starting'
            lib=getattr(u,'GTPlayWindowLibrary',None)
            if lib:assert lib.request_play_in_new_window(1600,1000)
            else:les.editor_request_begin_play()
            phase='warm';last=now
        elif phase=='warm' and now-last>25:
            world=u.EditorLevelLibrary.get_game_world()
            if u.GameplayStatics.get_time_seconds(world)<8:return
            phase='initializing';world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0);assert isinstance(car,u.GTCarPawn)
            car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'VegetationReview')
            camera.camera_component.set_editor_property('constrain_aspect_ratio',False);camera.camera_component.set_field_of_view(72)
            for cmd in ['gt.Look.Post 2','gt.Look.Kuwahara 0','gt.Look.Weather Clear','showhud','t.MaxFPS 30']:console(cmd)
            report['look_post']=2;report['simulation_seconds_before_contacts']=u.GameplayStatics.get_time_seconds(world)
            report['viewport']=list(pc.get_viewport_size())
            skies=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.actor_has_tag('GTLook.LocalSky')]
            assert len(skies)==1
            sky_mat=skies[0].static_mesh_component.get_material(0)
            assert isinstance(sky_mat,u.MaterialInstanceDynamic), 'Runtime did not adopt the level sky'
            report['level_sky_adopted']=True
            ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if not isinstance(a,u.LandscapeProxy)]
            # No new visual-only sky/fence/scrub components may block the vehicle.
            report['wheel_contacts']=[bool(u.ChaosWheeledVehicleMovementComponent.break_wheel_status(car.get_chaos_movement().get_wheel_state(i))[0]) for i in range(4)]
            assert sum(report['wheel_contacts'])>=3,report['wheel_contacts']
            for p in routes[0]['points'][::60]:
                hit=u.SystemLibrary.line_trace_single(world,u.Vector(p['x_m']*100,p['y_m']*100,height(p['x_m'],p['y_m'])*100+1000),u.Vector(p['x_m']*100,p['y_m']*100,-10000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,[car,camera],u.DrawDebugTrace.NONE,True)
                assert hit is not None
                pos=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0];assert abs(pos.z-height(p['x_m'],p['y_m'])*100)<10
            report['road_clearance_traces']=len(routes[0]['points'][::60])
            phase='view';last=time.monotonic()
        elif phase=='view':
            phase='moving';name,x,y,yaw=views[index]
            if name=='Road_Surface_Detail':
                a=math.radians(yaw);x-=math.sin(a)*1.2;y+=math.cos(a)*1.2;yaw+=30
            if name=='Bank_And_Rocks':x=-719;y=-64;yaw=75
            if name=='Distant_Landscape':yaw=180
            if name=='Hillside_Vista':x=285;y=-100;yaw=180
            if name=='Sheltered_Scrub':x=278;y=115;yaw=90
            if name=='Steep_Bank':yaw+=90
            camera.set_actor_location(u.Vector(x*100,y*100,height(x,y)*100+(130 if name=='Road_Surface_Detail' else 190)),False,False);camera.set_actor_rotation(u.Rotator(pitch=-7 if name=='Hillside_Vista' else -4,yaw=yaw),False);pc.set_view_target_with_blend(camera,0)
            phase='grow';last=now
        elif phase=='grow' and now-last>100:
            phase='counting';components=[];near=0;by_mesh={}
            for land in u.GameplayStatics.get_all_actors_of_class(world,u.LandscapeProxy):
                for c in land.get_components_by_class(u.GrassInstancedStaticMeshComponent):
                    # GPU-backed grass instance totals are not exposed by this
                    # Python build. Validate populated cluster bounds instead.
                    origin,extent,radius=u.SystemLibrary.get_component_bounds(c)
                    if radius>10 and c.get_editor_property('static_mesh'):
                        components.append(c);mesh=c.get_editor_property('static_mesh').get_name();by_mesh[mesh]=by_mesh.get(mesh,0)+1
                        cam=camera.get_actor_location()
                        if math.hypot(max(0,abs(origin.x-cam.x)-extent.x),max(0,abs(origin.y-cam.y)-extent.y))<10000:near+=1
            if set(by_mesh)!={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'} and now-last<150:
                phase='grow';return
            assert set(by_mesh)=={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'},('Unexpected grass meshes',by_mesh)
            assert len(components)>5,('No terrain grass streamed',views[index],len(components))
            if near<=5 and now-last<150:
                phase='grow';return
            assert near>5,('Grass did not follow camera',views[index],near)
            cam=camera.get_actor_location()
            row={'name':views[index][0],'camera_xy_m':[cam.x/100,cam.y/100],'populated_clusters_within_100m':near,'grass_components':len(components),'clusters_by_mesh':by_mesh}
            report['views'].append(row);console('t.MaxFPS 30');frame_times=[];phase='profile';last=now
        elif phase=='profile_warm' and now-last>4:
            frame_times=[];phase='profile';last=now
        elif phase=='profile':
            if 0<dt<1:frame_times.append(dt*1000)
            if now-last>2:
                phase='capturing';times=sorted(frame_times);assert times
                row['editor_tick_diagnostic_not_a_benchmark']={'mean':statistics.mean(times),'p95':times[min(len(times)-1,int(.95*len(times)))],'samples':len(times)}
                console('t.MaxFPS 30');file=OUT/(views[index][0]+'.png');row['image']=str(file);console('HighResShot 1600x1000 filename="'+file.as_posix()+'"');phase='next';last=now
        elif phase=='next' and now-last>4:
            index+=1
            if index==len(views):finish();return
            phase='view'
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
