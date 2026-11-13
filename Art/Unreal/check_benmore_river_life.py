"""Saved-map, grounding, bridge collision and stationary deformation checks.

No driving, performance profiling or timing measurements. Simulation uses a
temporary GameModeBase, and never saves that temporary game-mode override.
"""
import unreal as u
from pathlib import Path
import array,hashlib,json,time,traceback
ROOT=Path(u.Paths.project_dir()).resolve();BASE=ROOT/'Art/Export/BenmoreGaea';OUT=BASE/'RiverLife'
data=json.loads((OUT/'assets.json').read_text());setup=json.loads((OUT/'setup-report.json').read_text());assert setup['ok']
data['cameras'].append({'name':'Lake_Mouth','position_m':[-1220,-65,13],'target_m':[-1270,-15,1.2],'fov':72})
act=u.get_editor_subsystem(u.EditorActorSubsystem);les=u.get_editor_subsystem(u.LevelEditorSubsystem)
phase='load';started=time.monotonic();last=started;index=0;report={'ok':False,'mode':'Saved-map/static images and stationary patch initialization; no driving or profiling','images':[]}
u.EditorPythonScripting.set_keep_python_script_alive(True)

def digest(a):
    h=hashlib.sha256();count=0
    for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
        for i in range(c.get_instance_count()):
            t=c.get_instance_transform(i,True);h.update(array.array('d',[*t.translation.to_tuple(),*t.rotation.to_tuple(),*t.scale3d.to_tuple()]).tobytes());count+=1
    return [count,h.hexdigest()]

def finish(error=None):
    global phase
    phase='done';report['ok']=error is None
    if error:report['error']=error;u.log_error(error)
    report['source_drive_map_unchanged']=hashlib.sha256((ROOT/'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap').read_bytes()).hexdigest()==json.loads((BASE/'integration/assets.json').read_text())['source_map_sha256']
    (OUT/'review-report.json').write_text(json.dumps(report,indent=2));u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()

def tick(dt):
    global phase,last,index,world,land,rt,cameras,task,photo_started,gm,gameworld,capture,capture_rt
    now=time.monotonic()
    try:
        if now-started>1100:raise RuntimeError('Bounded river review timed out')
        if phase=='load':
            phase='loading';assert les.load_level(setup['level']);world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();actors=act.get_all_level_actors();land=next(a for a in actors if isinstance(a,u.Landscape))
            assert not any(a.get_actor_label()=='Benmore_Gaea_CreekSurface' for a in actors)
            for label,expected in setup['road_hashes'].items():assert digest(next(a for a in actors if a.get_actor_label()==label))==expected
            report['road_transforms_unchanged']=True
            cameras=[]
            for c in data['cameras']:
                camera=next((a for a in actors if a.get_actor_label()=='Benmore_RL_Camera_'+c['name']),None)
                if camera is None:
                    camera=act.spawn_actor_from_class(u.CameraActor,u.Vector(*(v*100 for v in c['position_m'])));camera.set_actor_label('Benmore_RL_Camera_'+c['name']);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(*(v*100 for v in c['target_m']))),False);camera.camera_component.set_field_of_view(c['fov']);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
                cameras.append(camera)
            rt=u.RenderingLibrary.create_render_target2d(world,2017,2017,u.TextureRenderTargetFormat.RTF_RGBA8);phase='warm';last=now
        elif phase=='warm' and now-last>15:
            phase='export';assert land.landscape_export_heightmap_to_render_target(rt,True,True);phase='verify';last=now
        elif phase=='verify' and now-last>10:
            phase='verifying';assert land.landscape_export_heightmap_to_render_target(rt,True,True);pixels=u.RenderingLibrary.read_render_target(world,rt,False);values=array.array('H',((int(c.r)<<8)|int(c.g) for c in pixels));del pixels
            checksum=hashlib.sha256(values.tobytes()).hexdigest();assert checksum==data['height_sha256'];report['saved_height_sha256']=checksum;report['all_height_samples_exact']=True
            ignore=[a for a in act.get_all_level_actors() if not isinstance(a,u.LandscapeProxy)];errors=[]
            for x,y,z,gap in json.loads((OUT/'support-samples.json').read_text())[::2]:
                hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,z+20000),u.Vector(x,y,z-20000),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit
                actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z;errors.append(abs(actual-z)/100)
            assert errors and max(errors)<.05;report['grounding']={'samples':len(errors),'max_error_m':max(errors)}
            bridge=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Footbridge');c=next(c for c in data['crossings'] if c['name']=='Footbridge');build=json.loads((OUT/'bridge-build.json').read_text());ends=c['ends_m'];x=(ends[0][0]+ends[1][0])*50+c['cross_direction'][0]*8;y=(ends[0][1]+ends[1][1])*50+c['cross_direction'][1]*8;z=build['deck_z_m']*100
            ignore=[a for a in act.get_all_level_actors() if a!=bridge];hit=u.SystemLibrary.line_trace_single(world,u.Vector(x,y,z+300),u.Vector(x,y,z-300),u.TraceTypeQuery.TRACE_TYPE_QUERY1,True,ignore,u.DrawDebugTrace.NONE,True);assert hit,'Bridge deck collision missing'
            actual=[v for v in hit.to_tuple() if isinstance(v,u.Vector)][0].z;assert abs(actual-(z+5.25))<3,(actual,z)
            report['bridge_collision']={'deck_trace_ok':True,'height_error_cm':abs(actual-(z+5.25))}
            phase='view'
        elif phase=='view':
            phase='moving';camera=cameras[index];u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation());u.SystemLibrary.execute_console_command(world,'grass.FlushCache');phase='grow';last=now
        elif phase=='grow' and now-last>35:
            phase='capturing';path=OUT/(data['cameras'][index]['name']+'.png');photo_started=time.time();task=u.AutomationLibrary.take_high_res_screenshot(1440,900,str(path),cameras[index]);report['images'].append({'name':data['cameras'][index]['name'],'path':str(path),'visually_reviewed':False});phase='shot';last=now
        elif phase=='shot' and now-last>5:
            path=Path(report['images'][-1]['path'])
            assert path.exists() and path.stat().st_size>1000 and path.stat().st_mtime>=photo_started-1
            index+=1
            if index==len(cameras):phase='runtime'
            else:phase='view'
        elif phase=='runtime':
            phase='starting_runtime';gm=world.get_world_settings().get_editor_property('default_game_mode');world.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
            camera=next(a for a in act.get_all_level_actors() if a.get_actor_label()=='Benmore_RL_Camera_Ford');temporary=act.spawn_actor_from_class(u.SceneCapture2D,camera.get_actor_location(),camera.get_actor_rotation());temporary.set_actor_label('RL_RuntimeCapture')
            u.EditorLevelLibrary.editor_play_simulate();phase='runtime_warm';last=now
        elif phase=='runtime_warm' and now-last>15:
            gameworld=u.EditorLevelLibrary.get_game_world()
            if gameworld is None:
                if now-last<40:return
                raise RuntimeError('Stationary simulation did not start')
            phase='runtime_check';patches=u.GameplayStatics.get_all_actors_of_class(gameworld,u.GTMudPatch);assert len(patches)==2,len(patches)
            rows=[]
            for p in patches:
                row=dict(section=p.section_index,hole_slot=p.hole_slot,material=p.material_path,material_loaded=bool(p.get_editor_property('bMaterialLoaded')),profile=bool(p.get_editor_property('bHasProfile')),cap_cm=p.profile_max_sinkage_m*100,ground_misses=p.mesh_ground_misses,vertices=p.mesh_vertex_count,cells=[p.cells_x,p.cells_y],bounds_min=list(p.bounds_min.to_tuple()),bounds_max=list(p.bounds_max.to_tuple()))
                assert row['profile'] and row['material_loaded'] and row['ground_misses']==0 and row['vertices']>100 and 'M_RL_DeformField' in row['material'];rows.append(row)
            assert sorted(r['hole_slot'] for r in rows)==[0,1]
            assert all(abs(a-b)<.01 for a,b in zip(sorted(r['cap_cm'] for r in rows),[3.5,7.5]))
            report['stationary_runtime_patches']=rows;report['driving_checked']=False;report['vehicle_water_coupling']=False
            camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(gameworld,u.CameraActor) if a.get_actor_label()=='Benmore_RL_Camera_Ford')
            pc=u.GameplayStatics.get_player_controller(gameworld,0)
            if pc:pc.set_view_target_with_blend(camera,0.)
            capture=next(a for a in u.GameplayStatics.get_all_actors_of_class(gameworld,u.SceneCapture2D) if a.get_actor_label()=='RL_RuntimeCapture')
            capture_rt=u.RenderingLibrary.create_render_target2d(gameworld,1440,900,u.TextureRenderTargetFormat.RTF_RGBA8)
            component=capture.get_components_by_class(u.SceneCaptureComponent2D)[0];component.set_editor_property('texture_target',capture_rt);component.set_editor_property('capture_source',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR);component.set_editor_property('fov_angle',camera.camera_component.field_of_view);component.set_editor_property('capture_every_frame',True);component.set_editor_property('always_persist_rendering_state',True);component.capture_scene()
            phase='runtime_photo';last=now
        elif phase=='runtime_photo' and now-last>10:
            capture.get_components_by_class(u.SceneCaptureComponent2D)[0].capture_scene();report['first_game_time']=u.GameplayStatics.get_time_seconds(gameworld);phase='runtime_export';last=now
        elif phase=='runtime_export' and now-last>.5:
            phase='runtime_capture';path=OUT/'Ford_LivePatches.png';photo_started=time.time();u.RenderingLibrary.export_render_target(gameworld,capture_rt,str(OUT),path.name);report['images'].append({'name':'Ford_LivePatches','path':str(path),'visually_reviewed':False});phase='runtime_end';last=now
        elif phase=='runtime_end' and now-last>1.7:
            path=Path(report['images'][-1]['path']);assert path.exists() and path.stat().st_mtime>=photo_started-1
            capture.get_components_by_class(u.SceneCaptureComponent2D)[0].capture_scene();report['second_game_time']=u.GameplayStatics.get_time_seconds(gameworld);phase='motion_export';last=now
        elif phase=='motion_export' and now-last>.5:
            phase='motion_capture';path=OUT/'Ford_LivePatches_Later.png';photo_started=time.time();u.RenderingLibrary.export_render_target(gameworld,capture_rt,str(OUT),path.name);report['images'].append({'name':'Ford_LivePatches_Later','path':str(path),'visually_reviewed':False});phase='motion_end';last=now
        elif phase=='motion_end' and now-last>5:
            path=Path(report['images'][-1]['path']);assert path.exists() and path.stat().st_mtime>=photo_started-1
            report['motion_interval_s']=report['second_game_time']-report['first_game_time'];report['distinct_frames']=hashlib.sha256((OUT/'Ford_LivePatches.png').read_bytes()).digest()!=hashlib.sha256(path.read_bytes()).digest();assert report['distinct_frames'] and report['motion_interval_s']>.01
            phase='ending';u.EditorLevelLibrary.editor_end_play();phase='restore';last=now
        elif phase=='restore' and now-last>5:
            phase='restoring';world.get_world_settings().set_editor_property('default_game_mode',gm);assert les.load_level(setup['level']);finish()
    except Exception:finish(traceback.format_exc())

handle=u.register_slate_post_tick_callback(tick)
