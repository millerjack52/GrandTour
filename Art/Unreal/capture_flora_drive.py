"""Rendered continuous road drive, recovery points, deformation, water and reset."""
import json,time,traceback,math,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/FloraDrive'
LEVEL='/Game/GrandTour/ArtTests/FloraDrive/L_FloraDrive'
import sys
sys.path[:0]=[str(ROOT/'Art/tools'),str(ROOT/'Art/Unreal')]
from make_mud_road import centre,heading
DATA=json.loads((ROOT/'Art/Export/MudRoad/authoring.json').read_text())
report=dict(ok=False,level=LEVEL,images=[])
from flora_trial_evidence import audited_fingerprint
report['trial_packages_sha256']=audited_fingerprint()
world=pc=car=surface=sheet=camera=None
driving=False
# Keep reset probes beyond the occupied entry: the parked tyres immediately work that soil again.
PROBES=[(x,centre(x)+offset) for x in range(-2000,2350,100) for offset in [-85,85]]

def save():(OUT/'capture-report.json').write_text(json.dumps(report,indent=2))
def console(s):u.SystemLibrary.execute_console_command(world,s,pc)
def terrain_snapshot():
    return [dict(x=x,y=y,height_cm=surface.sample_surface(u.Vector2D(x,y)).surface_delta_cm,
        compression_cm=surface.sample_surface(u.Vector2D(x,y)).compression_cm) for x,y in PROBES]
def sample():
    wheels=car.get_traction().wheels
    tuning=car.get_component_by_class(u.GTVehicleTuningComponent).get_current()
    return dict(time=u.GameplayStatics.get_time_seconds(world),position=car.get_actor_location().to_tuple(),
        speed_cm_s=car.get_velocity().length(),sink_cm=[w.sinkage_cm for w in tuning.wheels],
        water_cm=[w.water_depth_m*100 for w in wheels],
        compression_cm=[surface.sample_surface(u.Vector2D(w.contact_point.x,w.contact_point.y)).compression_cm for w in wheels],
        contacts=[w.get_editor_property('bInContact') for w in wheels])

frame_counter=0

def wait_frames(count):
    target=frame_counter+count
    while frame_counter<target:yield 0

def settle_car():
    # Wall-clock delays do not guarantee physics advanced on a busy GPU.
    started=u.GameplayStatics.get_time_seconds(world);deadline=time.monotonic()+180
    while True:
        elapsed=u.GameplayStatics.get_time_seconds(world)-started
        state=sample()
        if elapsed>=2 and sum(state['contacts'])>=3 and abs(car.get_velocity().z)<4:break
        assert time.monotonic()<deadline,'Vehicle did not settle on the road'
        yield .1
    report.setdefault('settled_checkpoints',[]).append(state)

def capture(name):
    # Accumulate temporal mask coverage before pausing the simulation.
    yield from wait_frames(48)
    u.GameplayStatics.set_game_paused(world,True);yield from wait_frames(16)
    path=OUT/(name+'.png');stamp=time.time()
    console('Shot filename="'+path.as_posix()+'" -nosuffix')
    end=time.monotonic()+60
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end,'Screenshot timeout';yield .2
    report['images'].append(str(path));save()
    u.GameplayStatics.set_game_paused(world,False)

def bind():
    global world,pc,car,surface,sheet
    world=u.EditorLevelLibrary.get_game_world();assert world
    pc=u.GameplayStatics.get_player_controller(world,0);assert isinstance(pc,u.GTMudLabController)
    car=pc.get_car();assert car and u.GameplayStatics.get_player_pawn(world,0)==car,'Car must be possessed without test intervention'
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    sheet=u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet)[0]

def run():
    global world,pc,car,surface,sheet,camera
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    yield 3
    u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12
    bind()
    while u.GameplayStatics.get_time_seconds(world)<6:yield .2
    for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','r.AntiAliasingMethod 4','sg.AntiAliasingQuality 3','t.IdleWhenNotForeground 0','t.MaxFPS 60']:console(cmd)
    car.disable_input(pc);car.get_chaos_movement().set_handbrake_input(True)
    yield from settle_car();yield from capture('01_start')
    for checkpoint,name in [(2,'02_broken_puddles'),(3,'03_flooded_dip')]:
        pc.select_lane(checkpoint);yield .2;car.get_chaos_movement().set_handbrake_input(True);yield from settle_car();yield from capture(name)
        if checkpoint==2:
            controls=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/MPC_ForestGround')
            u.MaterialLibrary.set_scalar_parameter_value(world,controls,'POMEnabled',0)
            yield from capture('18_chase_without_parallax')
            u.MaterialLibrary.set_scalar_parameter_value(world,controls,'POMEnabled',1)
    authored=json.loads((OUT/'road-relief-authoring.json').read_text())
    report['road_cross_sections']=[]
    for row in authored['profiles']:
        actual=[]
        for probe in row:
            h=surface.sample_surface(u.Vector2D(probe['x'],probe['y'])).surface_delta_cm
            actual.append(dict(lateral_cm=probe['lateral_cm'],runtime_height_cm=h,authored_height_cm=probe['after_cm']))
        report['road_cross_sections'].append(dict(station_cm=row[0]['x'],samples=actual))
    report['minimum_runtime_crown_to_trough_cm']=min(row['samples'][2]['runtime_height_cm']-min(row['samples'][i]['runtime_height_cm'] for i in [1,3]) for row in report['road_cross_sections'])
    assert report['minimum_runtime_crown_to_trough_cm']>8,'Authored road relief did not reach the runtime surface'
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector(-3850,-4400,4200)),'FloraDrive_ReviewCamera')
    camera.camera_component.set_editor_property('field_of_view',65);camera.camera_component.set_editor_property('constrain_aspect_ratio',False)
    pc.set_view_target_with_blend(camera,0);console('ShowHUD')
    for name,pos,target in [('05_overview',(-3850,-4400,4200),(100,0,0)),('06_forest_path',(-2350,-470,210),(900,150,640)),('07_wet_clearing',(-250,-850,190),(1000,450,470)),('08_clouds_canopy',(1500,-2000,350),(1700,1500,1900)),('09_ground_detail',(-1850,-480,110),(-650,200,15)),('15_pond',(250,300,155),(1100,1200,70)),('16_woodland_edge',(-2100,-1100,165),(-400,-2200,420)),('17_exit',(2450,-1650,190),(900,300,350))]:
        camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False);yield 3
        yield from capture(name)
    # Isolate the normal and POM contributions with a fixed, close camera.
    for name,pos,target in [('19_rock_bank',(-2345,1541,230),(-1150,1646,100)),('20_rock_outcrop',(-9,-1936,230),(1150,-1626,100))]:
        camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False);yield 3
        yield from capture(name)
    ground_controls=u.load_asset('/Game/GrandTour/ArtTests/FloraDrive/MPC_ForestGround');assert ground_controls
    camera.set_actor_location(u.Vector(-1700,-650,100),False,True)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(-1700,-650,100),u.Vector(-1400,-400,0)),False)
    camera.camera_component.set_field_of_view(55.)
    for name,normal_enabled,pom_enabled in [('10_flat_control',0,0),('11_normal_only',1,0),('12_parallax',1,1)]:
        u.MaterialLibrary.set_scalar_parameter_value(world,ground_controls,'NormalEnabled',normal_enabled)
        u.MaterialLibrary.set_scalar_parameter_value(world,ground_controls,'POMEnabled',pom_enabled)
        yield from capture(name)
    console('ShowFlag.VisualizeBuffer 1');console('r.BufferVisualizationTarget WorldNormal')
    yield from capture('13_world_normals');console('ShowFlag.VisualizeBuffer 0')
    camera.set_actor_location(u.Vector(-1630,-650,100),False,True)
    yield from capture('14_parallax_moved')
    report['ground_checks']={'flat_normal_pom_same_camera':True,'world_normal_buffer':True,'lateral_camera_move_cm':70,'pom_steps':[10,24],'pom_fade_m':[7,18]}
    pond_bed=surface.sample_surface(u.Vector2D(900,1050)).surface_delta_cm
    report['pond_bed_cm']=pond_bed;assert pond_bed<-20,'Authored pond did not reach the runtime terrain'
    # Bounded, stationary PIE spot checks. No screenshots or pauses during capture.
    from benmore_profile_metrics import analyse
    csv_dir=ROOT/'Saved/Profiling/CSV';report['render_spot_checks']=[]
    console('t.MaxFPS 0');console('r.VSync 0');console('r.DynamicRes.OperationMode 0')
    for label,pos,target in [('road',(-2350,-470,210),(900,150,640)),('pond',(250,300,155),(1100,1200,70))]:
        camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False);camera.camera_component.set_field_of_view(65.)
        yield from wait_frames(90)
        previous=set(csv_dir.glob('*.csv'));console('CsvProfile START');yield from wait_frames(300);console('CsvProfile STOP')
        deadline_csv=time.monotonic()+30;files=[]
        while not files:
            yield 1;files=[p for p in csv_dir.glob('*.csv') if p not in previous]
            assert time.monotonic()<deadline_csv,'CSV capture did not finish'
        yield 2
        output=OUT/('render_'+label+'.csv');shutil.copy2(max(files,key=lambda p:p.stat().st_mtime),output)
        analysis=analyse(output)
        report['render_spot_checks'].append({'view':label,'resolution':list(pc.get_viewport_size()),'csv':str(output),'metrics':{k:analysis['metrics'][k] for k in ['FrameTime','GPUTime','GameThreadTime','RenderThreadTime'] if k in analysis['metrics']},'scope':'stationary uncapped PIE; not a packaged-game benchmark'})
    console('t.MaxFPS 60')
    report['ok']=True;report['note']='Final visual pass. Vehicle checkpoint views are stationary; continuous-drive evidence is in functional-report.json.';save()
    yield from finish()

def finish():
    global world,pc,car,surface,sheet,camera,driving
    driving=False
    u.EditorLevelLibrary.editor_end_play();yield 4
    world=pc=car=surface=sheet=camera=None
    u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Engine/Maps/Entry')
    u.SystemLibrary.collect_garbage();yield 3
    # Return all the way out of run() before quitting. A suspended generator
    # otherwise retains reflected Unreal values until Python's late shutdown.

steps=run();deadline=0;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,driving,steps,frame_counter
    if busy:return
    busy=True;frame_counter+=1
    try:
        assert time.monotonic()-began<900,'Lab test deadline'
        if driving:
            move=car.get_chaos_movement();move.set_handbrake_input(False);move.set_throttle_input(.52);move.set_brake_input(0)
            p=car.get_actor_location();tx=min(p.x+220,2700);ty=centre(tx)
            target=math.degrees(math.atan2(ty-p.y,tx-p.x))
            delta=(target-car.get_actor_rotation().yaw+180)%360-180
            car.set_raw_steer(max(-.75,min(.75,delta/32)))
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        steps=None
        u.unregister_slate_post_tick_callback(handle)
        # Release every nested Python-held engine object before editor shutdown.
        for key,value in list(globals().items()):
            if not key.startswith('__') and key not in ('u','time'):globals()[key]=None
        value=None
        import gc
        gc.collect();u.SystemLibrary.collect_garbage()
        globals()['quit_at']=time.monotonic()+3
        def close_editor(dt):
            if time.monotonic()>quit_at:
                u.unregister_slate_post_tick_callback(quit_handle);u.SystemLibrary.quit_editor()
        globals()['quit_handle']=u.register_slate_post_tick_callback(close_editor)
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error']);driving=False
        if world:u.GameplayStatics.set_game_paused(world,False)
        steps=finish();deadline=time.monotonic()+next(steps)
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)

