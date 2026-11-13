"""Bounded saved-asset checks and three views of the river; no driving retune."""
import unreal as u,json,time,traceback,math,array,sys
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/BenmoreRivers';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive'
data=json.loads((OUT/'assets.json').read_text());phase='load';last=time.monotonic();started=last;index=0;report={'ok':False,'views':[]}
les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
u.EditorPythonScripting.set_keep_python_script_alive(True)
views=[('River_Close','Benmore_River_Camera_Close'),('River_Reach','Benmore_River_Camera_Reach'),('River_Overlook',''),('River_Mouth','@Mouth')]
def console(cmd):u.SystemLibrary.execute_console_command(world,cmd,pc)
def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    (OUT/'validation-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()
def tick(dt):
    global phase,last,world,pc,camera,index,frames
    now=time.monotonic()
    try:
        if now-started>460:raise RuntimeError('Bounded river review timed out; saved assets retained')
        if phase=='load':
            phase='loading';assert les.load_level(LEVEL);phase='asset_warm';last=now
        elif phase=='asset_warm' and now-last>8:
            phase='check';actors=act.get_all_level_actors()
            surfaces=[a for a in actors if a.get_actor_label().startswith('Benmore_River_Surface_')]
            assert len(surfaces)==len(data['parts'])
            for a in surfaces:
                assert str(a.static_mesh_component.get_collision_profile_name())=='NoCollision'
                assert a.static_mesh_component.get_material(0).get_name()=='M_Benmore_BakedRiver'
            banks=[a for a in actors if a.get_actor_label().startswith('Benmore_River_Bank_')];assert len(banks)==6
            editorworld=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            ignore=[a for a in actors if not isinstance(a,u.LandscapeProxy) and a not in banks];bank_errors=[];coordinates=[]
            for part in data['parts']+data['bank_parts']:
                mesh=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/Rivers/'+part['name']);desc=mesh.get_static_mesh_description(0)
                raw=json.loads((OUT/(part['name']+'.json')).read_text())['vertices']
                for i in range(0,desc.get_vertex_count(),max(1,desc.get_vertex_count()//12)):
                    p=desc.get_vertex_position(u.VertexID(i));error=min(max(abs(p.x-v[0]*100),abs(p.y-v[1]*100),abs(p.z-v[2]*100)) for v in raw)
                    assert error<.05,('Coordinate mismatch',part['name'],error)
                    if 'RiverBank' not in part['name']:continue
                    actor=next(a for a in banks if a.get_actor_label().endswith(part['name'][-2:]));assert str(actor.static_mesh_component.get_collision_profile_name())=='BlockAll'
                    pos=p+actor.get_actor_location()
                    hit=u.SystemLibrary.line_trace_single(editorworld,u.Vector(pos.x,pos.y,pos.z+400),u.Vector(pos.x,pos.y,pos.z-400),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True)
                    assert hit is not None
                    z=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z;bank_errors.append(abs(z-pos.z)/100)
                coordinates.append(part['name'])
            assert max(bank_errors)<.05,(max(bank_errors),bank_errors)
            report['bank_collision']={'samples':len(bank_errors),'max_surface_error_m':max(bank_errors)};report['mesh_coordinates_checked']=coordinates
            for label,count in [('Benmore_ReferenceRoadAggregate',5704),('Benmore_RoadVergeDetail',52104)]:
                actor=next(a for a in actors if a.get_actor_label()==label);total=sum(c.get_instance_count() for c in actor.get_components_by_class(u.InstancedStaticMeshComponent));assert total==count,(label,total)
            assert sum(a.get_actor_label().startswith('Benmore_Composition_SchistExposure_') for a in actors)==18
            report.update(saved_map_reloaded=True,surface_meshes=len(surfaces),roads_and_verges_preserved=True,water_collision='NoCollision',runtime_solver=False)
            if (OUT/'bank-art-install.json').exists():
                art_report=json.loads((OUT/'bank-art-install.json').read_text())
                for category,count in art_report['counts'].items():
                    a=next(a for a in actors if a.get_actor_label()=='Benmore_River_Art_'+category)
                    assert sum(c.get_instance_count() for c in a.get_components_by_class(u.InstancedStaticMeshComponent))==count
                sys.path.insert(0,str(ROOT/'Art/Unreal'))
                from benmore_river_bank_art import check_support
                report['bank_art']=check_support(editorworld,art_report)
            phase='begin';last=now
        elif phase=='begin' and now-last>5:
            phase='starting';assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,1000);phase='warm';last=now
        elif phase=='warm' and now-last>20:
            world=u.EditorLevelLibrary.get_game_world()
            if not world:return
            pc=u.GameplayStatics.get_player_controller(world,0)
            if not pc:return
            car=u.GameplayStatics.get_player_pawn(world,0);car.disable_input(pc)
            if isinstance(car,u.GTCarPawn):car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
            camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'RiverReviewCamera')
            camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
            for cmd in ['gt.Look.Post 2','gt.Look.Kuwahara 0','gt.Look.Weather Clear','showhud','t.MaxFPS 30','grass.MaxCreatePerFrame 8','grass.MaxAsyncTasks 16','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:console(cmd)
            phase='view';last=now
        elif phase=='view':
            name,label=views[index]
            if label=='@Mouth':
                camera.set_actor_location(u.Vector(-127500,-3000,2400),False,True);camera.set_actor_rotation(u.Rotator(pitch=-9,yaw=130),False);camera.camera_component.set_field_of_view(70)
            elif label:
                bookmark=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()==label)
                camera.set_actor_transform(bookmark.get_actor_transform(),False,True);camera.camera_component.set_field_of_view(70)
            else:
                grid=array.array('f');grid.frombytes((ROOT/'Art/Export/BenmoreRoads/height_local_south_up.f32').read_bytes());i=round((750+1250)/2500*2016);j=round((500+1250)/2500*2016)
                camera.set_actor_location(u.Vector(75000,50000,grid[j*2017+i]*100+190),False,True);camera.set_actor_rotation(u.Rotator(pitch=-7,yaw=215),False);camera.camera_component.set_field_of_view(82)
            pc.set_view_target_with_blend(camera,0);phase='grow';last=now;frames=0
        elif phase=='grow':
            frames+=1
            if now-last<45 or frames<45:return
            name=views[index][0];console('HighResShot 1600x1000 filename="'+(OUT/(name+'.png')).as_posix()+'"')
            report['views'].append(dict(name=name,frames=frames,wait_seconds=now-last,image=str(OUT/(name+'.png')),visually_reviewed=False))
            phase='shot';last=now
        elif phase=='shot' and now-last>4:
            assert (OUT/(views[index][0]+'.png')).exists()
            if index==0:
                console('HighResShot 1600x1000 filename="'+(OUT/'River_Close_Motion.png').as_posix()+'"')
                phase='motion_wait';last=now;return
            index+=1
            if index>=len(views):finish();return
            phase='view';last=now
        elif phase=='motion_wait' and now-last>4:
            assert (OUT/'River_Close_Motion.png').exists();index+=1
            if index>=len(views):finish();return
            phase='view';last=now
    except Exception:finish(traceback.format_exc())
handle=u.register_slate_post_tick_callback(tick)
