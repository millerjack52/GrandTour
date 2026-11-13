"""Verify grass streaming at separated sites and capture the saved level."""
import unreal as u,json,time,math,array,traceback,statistics
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreEnvironment'
LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive';les=u.get_editor_subsystem(u.LevelEditorSubsystem)
grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes())
def height(x,y):
    f=(x+1250)/2500*2016;g=(y+1250)/2500*2016;i=int(f);j=int(g);a=f-i;b=g-j;k=j*2017+i
    return (grid[k]*(1-a)+grid[k+1]*a)*(1-b)+(grid[k+2017]*(1-a)+grid[k+2018]*a)*b
routes=json.loads((ROOT/'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
views=[]

for name,ri,i in [('Terrace_Gravel',0,40),('Hillside_Gravel',1,400),('Road_Surface_Detail',0,40),('Bank_And_Rocks',0,200),('Distant_Landscape',1,400)]:
    p=routes[ri]['points'][i];views.append((name,p['x_m'],p['y_m'],p['yaw']))

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
            # Verify the imported scenery retained the source coordinate system.
            backdrop_checks=[]
            for part in json.loads((OUT/'backdrop.json').read_text())['parts']:
                mesh=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Environment/'+part['name'])
                raw=array.array('f');raw.frombytes((OUT/(part['name']+'.f32')).read_bytes())
                expected={(round(raw[i]*100,0),round(raw[i+1]*100,0)):raw[i+2]*100 for i in range(0,len(raw),3)}
                desc=mesh.get_static_mesh_description(0)
                v=[desc.get_vertex_position(u.VertexID(i)) for i in range(0,desc.get_vertex_count(),251)]
                actor=next(a for a in actors if a.get_actor_label()==part['name'].replace('SM_',''));assert actor.get_actor_location().length()<.1
                mismatch=[];errors=[]
                for p in v:
                    k=(round(p.x,0),round(p.y,0))
                    candidates=[expected.get((k[0]+dx,k[1]+dy)) for dx in [-1,0,1] for dy in [-1,0,1]];candidates=[z for z in candidates if z is not None]
                    if not candidates:mismatch.append([p.x,p.y,p.z])
                    else:errors.append(min(abs(p.z-z) for z in candidates))
                assert not mismatch,('Backdrop coordinate mismatch',part['name'],mismatch[:5])
                assert max(errors)<.25
                backdrop_checks.append({'mesh':part['name'],'sampled_vertices':len(errors),'max_error_cm':max(errors)})
            report['backdrop_geographic_alignment']=backdrop_checks
            material=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Vegetation/M_Benmore_FullCover')
            assert not u.MaterialEditingLibrary.recompile_material(material)
            bm=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Environment/M_Benmore_Backdrop');u.MaterialEditingLibrary.set_material_usage(bm,u.MaterialUsage.MATUSAGE_NANITE);u.EditorAssetLibrary.save_loaded_asset(bm)
            assert len([a for a in actors if a.get_actor_label().startswith('Benmore_Scenery_rocks_')])==201
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
            report['viewport']=list(pc.get_viewport_size())
            ignore=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if not isinstance(a,u.LandscapeProxy)]
            errors=[];misses=[];road_errors=[]
            for route in routes:
                for p in route['points'][::12]:
                    a=math.radians(p['yaw'])
                    for offset in [-route['width_m']/2-3.7,-route['width_m']/2-2.1,-1.4,0,1.4,route['width_m']/2+2.1,route['width_m']/2+3.7]:
                        x=p['x_m']-math.sin(a)*offset;y=p['y_m']+math.cos(a)*offset
                        hit=u.SystemLibrary.line_trace_single(world,u.Vector(x*100,y*100,100000),u.Vector(x*100,y*100,-10000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
                        if hit is None:misses.append([x,y]);continue
                        vectors=[v for v in hit.to_tuple() if isinstance(v,u.Vector)]
                        error=abs(vectors[0].z-height(x,y)*100);errors.append(error)
                        if abs(offset)<=1.4:road_errors.append(error)
            report['collision']={'samples':len(errors),'misses':len(misses),'max_surface_error_cm':max(errors),'max_wheel_path_error_cm':max(road_errors)}
            assert not misses and max(errors)<25 and max(road_errors)<8,report['collision']
            # Re-test saved large-rock support against PIE landscape collision.
            samples=json.loads((OUT/'rock-undersides.json').read_text());gaps=[]
            for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor):
                if not a.get_actor_label().startswith('Benmore_Scenery_rocks_'):continue
                mesh=a.static_mesh_component.get_editor_property('static_mesh');kind=mesh.get_name()[-1];bounds=mesh.get_bounds();cut=(bounds.origin.z-bounds.box_extent.z)/100+bounds.box_extent.z*2/100*.32
                samples_used=[v for v in samples[kind] if v[2]<=cut]
                for x,y,z in samples_used:
                    point=u.MathLibrary.transform_location(a.get_actor_transform(),u.Vector(x*100,y*100,z*100))
                    hit=u.SystemLibrary.line_trace_single(world,u.Vector(point.x,point.y,100000),u.Vector(point.x,point.y,-10000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
                    assert hit is not None
                    ground=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z;gaps.append(point.z-ground)
            report['saved_rock_support']={'samples':len(gaps),'maximum_gap_cm':max(gaps)};assert max(gaps)<.1
            phase='view';last=time.monotonic()
        elif phase=='view':
            phase='moving';name,x,y,yaw=views[index]
            if name=='Road_Surface_Detail':
                a=math.radians(yaw);x-=math.sin(a)*1.2;y+=math.cos(a)*1.2;yaw+=30
            if name=='Bank_And_Rocks':x=-719;y=-64;yaw=75
            if name=='Distant_Landscape':yaw=180
            camera.set_actor_location(u.Vector(x*100,y*100,height(x,y)*100+(130 if name=='Road_Surface_Detail' else 190)),False,False);camera.set_actor_rotation(u.Rotator(pitch=-28 if name=='Road_Surface_Detail' else (-2 if name=='Distant_Landscape' else -4),yaw=yaw),False);pc.set_view_target_with_blend(camera,0)
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
            if set(by_mesh)!={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'} and now-last<150:
                phase='grow';return
            assert set(by_mesh)=={'SM_TS_Straw','SM_TS_Rust','SM_TS_Weathered','SM_TS_Fine'},('Unexpected grass meshes',by_mesh)
            assert len(components)>5,('No terrain grass streamed',views[index],len(components))
            if near<=5 and now-last<150:
                phase='grow';return
            assert near>5,('Grass did not follow camera',views[index],near)
            row={'name':views[index][0],'camera_xy_m':list(views[index][1:3]),'populated_clusters_within_100m':near,'grass_components':len(components),'clusters_by_mesh':by_mesh}
            report['views'].append(row);console('t.MaxFPS 0');frame_times=[];phase='profile_warm';last=now
        elif phase=='profile_warm' and now-last>4:
            frame_times=[];phase='profile';last=now
        elif phase=='profile':
            if 0<dt<1:frame_times.append(dt*1000)
            if now-last>6:
                phase='capturing';times=sorted(frame_times);assert times
                row['editor_tick_diagnostic_not_a_benchmark']={'mean':statistics.mean(times),'p95':times[min(len(times)-1,int(.95*len(times)))],'samples':len(times)}
                console('t.MaxFPS 30');file=OUT/(views[index][0]+'.png');row['image']=str(file);console('HighResShot 1600x1000 filename="'+file.as_posix()+'"');phase='next';last=now
        elif phase=='next' and now-last>4:
            index+=1
            if index==len(views):finish();return
            phase='view'
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
