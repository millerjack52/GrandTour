"""RS2 saved-material, firm-gravel and live-mud smoke check in L_LidarStudy."""
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
exec(compile((ROOT/'Art/Unreal/check_lidar_place.py').read_text().split('steps=run();')[0],'<lidar-check-helpers>','exec'))
import sys
sys.path.insert(0,str(ROOT/'Art/Unreal'))
import lidar_road_style as style
import lidar_logging_trial as trial
from lidar_grounding import GroundSampler
QA=ROOT/'Saved/LidarAuthoringQA/RS2'
report=dict(ok=False,images=[],scope='Saved shader invariants, authored surface probes and one short low-range mud drive; not handling acceptance')
RD1_THROTTLE=.65;RD1_LOOK_CM=300.

def save():(QA/'check.json').write_text(json.dumps(report,indent=2))

def sample(surface,x,y):
    q=surface.sample_surface(u.Vector2D(x,y))
    return dict(sinkage_cap_cm=q.sinkage_cap_cm,friction=q.friction_scale,wetness=q.wetness,
                softness=q.softness,water_depth_cm=q.water_depth_cm,delta_cm=q.surface_delta_cm,
                compression_cm=q.compression_cm,surface_tag=str(q.surface_tag))

def run():
    global world,pc,car,drive_on,drive_cmd
    installed=json.loads((QA/'install.json').read_text());assert installed['ok']
    report['materials']=style.validate()
    for current,expected in zip(report['materials'],installed['materials']):
        preserved=json.loads(json.dumps(expected['preserved']))
        if (OUT/'slope-style.json').exists():
            import lidar_slope_style as slopes
            slope_install=json.loads((slopes.QA/'install.json').read_text());assert slope_install['ok']
            assert slopes.validate()==slope_install['materials']
            m=u.load_asset(BASE+'/M_'+current['material']);rock=slopes.rocknode(m)
            preserved['other_shader_programs'][rock.get_name()]=hashlib.sha256(slopes.CODE.encode()).hexdigest()
            report['later_slope_pass_verified']=True
        assert current['preserved']==preserved
    mapfile=ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
    assert style.digest(mapfile)==installed['map_sha256']
    les=u.get_editor_subsystem(u.LevelEditorSubsystem);assert les.load_level(BASE+'/L_LidarStudy')
    les.editor_set_viewport_realtime(False);assert u.GTPlayWindowLibrary.request_play_in_new_window(1600,900)
    until=time.monotonic()+180
    while not car:
        world=u.EditorLevelLibrary.get_game_world()
        if world:pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car() if pc else None
        assert time.monotonic()<until;yield .5
    pc.possess(car);car.disable_input(pc);car.reset_driving_inputs()
    for command in json.loads((ROOT/'Art/lidar_performance.json').read_text())['commands']:
        u.SystemLibrary.execute_console_command(world,command,pc)
    for command in ('DisableAllScreenMessages','r.MotionBlurQuality 0','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0'):
        u.SystemLibrary.execute_console_command(world,command,pc)
    refs=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    author=next(a for a in refs if isinstance(a,u.GTProceduralGround));ground=GroundSampler(author)
    surface=next(a for a in refs if isinstance(a,u.GTLandscapeSurface))
    mv=car.get_chaos_movement();mesh=car.get_component_by_class(u.SkeletalMeshComponent)
    roads=json.loads((OUT/'roads.json').read_text());path=trial.route(roads)
    # The established gravel road must retain its firm authored surface.
    site=json.loads((OUT/'sites.json').read_text())[0];x,y=site['center'];yaw=site['yaw']
    car.set_actor_location_and_rotation(u.Vector(x,y,ground.height(x,y)+100),u.Rotator(yaw=yaw),False,True)
    mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector());mv.set_handbrake_input(True)
    yield from settle(7)
    report['gravel_probes']=[sample(surface,x,y-d) for d in (0,300,600)]
    assert all(q['sinkage_cap_cm']<.5 for q in report['gravel_probes']),report['gravel_probes']
    yield from capture('RS2_gravel',(x-50,y+100,ground.height(x,y)+180),(x,y-1400,ground.height(x,y-1400)+35))
    report['mud_probes']=[]
    for label,station in [('solid',170.),('hollow',214.),('crest',430.),('wet_shelf',552.),('deep_gully',667.)]:
        px,py,_=trial.at(path,station,.85);report['mud_probes'].append(dict(name=label,**sample(surface,px,py)))
    assert report['mud_probes'][-1]['sinkage_cap_cm']>report['mud_probes'][2]['sinkage_cap_cm']
    assert report['mud_probes'][-1]['softness']>report['mud_probes'][2]['softness']
    x,y,yaw=trial.at(path,165.)
    car.set_actor_location_and_rotation(u.Vector(x,y,ground.height(x,y)+100),u.Rotator(yaw=yaw),False,True)
    mesh.set_physics_linear_velocity(u.Vector());mesh.set_physics_angular_velocity_in_degrees(u.Vector())
    car.reset_driving_inputs();mv.set_handbrake_input(True);car.get_drivetrain().set_low_range(True);car.get_drivetrain().set_diff_lock(True)
    yield from settle(8)
    probes=[trial.at(path,s,off)[:2] for s in range(165,197) for off in (-1.2,-.9,-.6,-.3,0,.3,.6,.9,1.2)]
    before=[sample(surface,*p) for p in probes]
    pts=[p[:2] for p in path['points_cm']];cum=[0.]
    for a,b in zip(pts,pts[1:]):cum.append(cum[-1]+math.dist(a,b))
    p=car.get_actor_location();s0,_=rd1_project(pts,cum,p.x,p.y);now=u.GameplayStatics.get_time_seconds(world)
    drive_cmd=dict(pts=pts,cum=cum,s=s0,max_off=0.,t0=now,t_last=-1.,trace=[])
    mv.set_handbrake_input(False);drive_on=True
    yield from settle(8)
    drive_on=False;mv.set_throttle_input(0);mv.set_handbrake_input(True);car.set_raw_steer(0)
    yield from settle(2)
    after=[sample(surface,*p) for p in probes]
    change=max(abs(a['delta_cm']-b['delta_cm']) for a,b in zip(after,before))
    progress=(drive_cmd['s']-s0)/100.
    report['mud_drive']=dict(progress_m=progress,max_lateral_offset_m=drive_cmd['max_off']/100.,max_surface_change_cm=change,trace=drive_cmd['trace'],samples=len(probes))
    save();assert progress>1.,report['mud_drive'];assert change>.05,report['mud_drive']
    cx,cy,_=trial.at(path,165.);tx,ty,_=trial.at(path,180.)
    yield from capture('RS2_mud_ruts',(cx,cy,ground.height(cx,cy)+220),(tx,ty,ground.height(tx,ty)+20))
    assert not report.get('drive_errors'),report.get('drive_errors')
    assert style.digest(mapfile)==installed['map_sha256']
    report.update(ok=True,map_unchanged=True,owner_accepted=False);save()
    refs=author=ground=surface=mv=mesh=None
    yield from finish()

steps=run();deadline=0;began=time.monotonic();failed=False
def tick(dt):
    global busy,deadline,steps,failed,drive_on
    if drive_on and car:
        try:drive_ctrl()
        except Exception:report.setdefault('drive_errors',[]).append(traceback.format_exc());drive_on=False
    if busy:return
    busy=True
    try:
        assert time.monotonic()-began<700,'RS2 check timed out'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
    except Exception:
        report.update(ok=False,error=traceback.format_exc());save();u.log_error(report['error']);drive_on=False
        if failed:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
        else:failed=True;steps=finish();deadline=time.monotonic()+next(steps)
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
