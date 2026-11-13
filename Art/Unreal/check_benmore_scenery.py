"""Verify grass streaming at separated sites and capture the saved level."""
import unreal as u,json,time,math,array,traceback,statistics
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreScenery'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive';les=u.get_editor_subsystem(u.LevelEditorSubsystem)
grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
def height(x,y):
    f=(x+1250)/2500*2016;g=(y+1250)/2500*2016;i=int(f);j=int(g);a=f-i;b=g-j;k=j*2017+i
    return (grid[k]*(1-a)+grid[k+1]*a)*(1-b)+(grid[k+2017]*(1-a)+grid[k+2018]*a)*b
views=[('Roadside_Willows',-849,-210,150),('Shoreline_Willows',-1090,-682,137),('Hillside_Rocks',-204,85,65)]
report={'ok':False,'views':[],'level':LEVEL};phase='load';last=time.monotonic();started=last;index=0;frame_times=[]
u.EditorPythonScripting.set_keep_python_script_alive(True)
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def finish(error=None):
    global phase
    phase='finished';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'validation-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,pc,car,camera,index,frame_times,row
    now=time.monotonic()
    try:
        if now-started>600:raise RuntimeError('Vegetation check timeout')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL)
            sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
            report['saved_mesh_checks']=[]
            for variant in ['Young','Broad','Windswept','Weathered']:
                mesh=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Scenery/SM_Willow_'+variant)
                lods=sm.get_lod_count(mesh);hulls=len(mesh.get_editor_property('body_setup').get_editor_property('agg_geom').get_editor_property('convex_elems'))
                assert lods==4 and hulls==3,(variant,lods,hulls)
                report['saved_mesh_checks'].append({'variant':variant,'lods':lods,'trunk_hulls':hulls})
            phase='begin';last=now
        elif phase=='begin' and now-last>10:
            phase='starting'
            lib=getattr(u,'GTPlayWindowLibrary',None)
            if lib:assert lib.request_play_in_new_window(1600,1000)
            else:les.editor_request_begin_play()
            phase='warm';last=now
        elif phase=='warm' and now-last>25:
            phase='initializing';world=u.EditorLevelLibrary.get_game_world();pc=u.GameplayStatics.get_player_controller(world,0);car=u.GameplayStatics.get_player_pawn(world,0);assert isinstance(car,u.GTCarPawn)
            car.disable_input(pc);car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'VegetationReview')
            camera.camera_component.set_editor_property('constrain_aspect_ratio',False);camera.camera_component.set_field_of_view(72)
            for cmd in ['gt.Look.Post 0','gt.Look.Kuwahara 0','gt.Look.Weather Clear','showhud','t.MaxFPS 30']:console(cmd)
            actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
            scenery=[a for a in actors if a.get_actor_label().startswith('Benmore_Scenery_')]
            treeactors=[a for a in scenery if '_trees_' in a.get_actor_label()]
            rockactors=[a for a in scenery if '_rocks_' in a.get_actor_label()]
            assert len(treeactors)==27 and len(rockactors)==201,(len(treeactors),len(rockactors))
            report['saved_actor_counts']={'trees':len(treeactors),'rocks':len(rockactors)}
            placement_rows=json.loads((OUT/'placements.json').read_text())['trees']
            for a in treeactors:
                index_in_plan=int(a.get_actor_label().split('_')[-1]);expected=placement_rows[index_in_plan]['scale']
                assert abs(a.get_actor_scale3d().x-expected)<.001
            report['saved_tree_scales_verified']=True
            ignore=[a for a in actors if a not in scenery];hits=[];probes=0
            routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
            for route in routes:
                pts=route['points']
                for i in range(0,len(pts)-10,10):
                    p,q=pts[i],pts[i+10]
                    for side in [-1.5,0,1.5]:
                        yaw=math.radians(p['yaw']);ox=-math.sin(yaw)*side;oy=math.cos(yaw)*side
                        start=u.Vector((p['x_m']+ox)*100,(p['y_m']+oy)*100,(p['z_m']+.7)*100)
                        end=u.Vector((q['x_m']+ox)*100,(q['y_m']+oy)*100,(q['z_m']+.7)*100)
                        hit=u.SystemLibrary.line_trace_single(world,start,end,u.TraceTypeQuery.TRACE_TYPE_QUERY1,False,ignore,u.DrawDebugTrace.NONE,True)
                        probes+=1
                        if hit is not None:hits.append([route['name'],i,side])
            report['road_obstruction_check']={'probes':probes,'hits':hits};assert not hits,hits
            report['viewport']=list(pc.get_viewport_size());phase='view';last=now
        elif phase=='view':
            phase='moving';name,x,y,yaw=views[index]
            camera.set_actor_location(u.Vector(x*100,y*100,height(x,y)*100+230),False,False);camera.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw),False);pc.set_view_target_with_blend(camera,0)
            phase='grow';last=now
        elif phase=='grow' and now-last>32:
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
            assert set(by_mesh)=={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'},('Unexpected grass meshes',by_mesh)
            assert len(components)>5,('No terrain grass streamed',views[index],len(components))
            assert near>5,('Grass did not follow camera',views[index],near)
            row={'name':views[index][0],'camera_xy_m':list(views[index][1:3]),'populated_clusters_within_100m':near,'grass_components':len(components),'clusters_by_mesh':by_mesh}
            report['views'].append(row);console('t.MaxFPS 0');frame_times=[];phase='profile_warm';last=now
        elif phase=='profile_warm' and now-last>4:
            frame_times=[];phase='profile';last=now
        elif phase=='profile':
            if 0<dt<1:frame_times.append(dt*1000)
            if now-last>6:
                phase='capturing';times=sorted(frame_times);assert times
                row['editor_frame_interval_ms']={'mean':statistics.mean(times),'p95':times[min(len(times)-1,int(.95*len(times)))],'samples':len(times)}
                console('t.MaxFPS 30');file=OUT/(views[index][0]+'.png');row['image']=str(file);console('HighResShot 1600x1000 filename="'+file.as_posix()+'"');phase='next';last=now
        elif phase=='next' and now-last>4:
            index+=1
            if index==len(views):finish();return
            phase='view'
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
