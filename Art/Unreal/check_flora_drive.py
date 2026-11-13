"""Rendered continuous road drive, recovery points, deformation, water and reset."""
import json,time,traceback,math
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

def save():(OUT/'check-report.json').write_text(json.dumps(report,indent=2))
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

def capture(name):
    u.GameplayStatics.set_game_paused(world,True);yield 2
    path=OUT/(name+'.png');stamp=time.time()
    console('Shot filename="'+path.as_posix()+'" -nosuffix')
    end=time.monotonic()+45
    while not path.exists() or path.stat().st_mtime<stamp:
        assert time.monotonic()<end,'Screenshot timeout';yield .2
    yield 1
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
    global driving,world,pc,car,surface,sheet,camera
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    # ShaderOracle passed in the separate preflight; it owns and closes its PIE world.
    yield 3
    u.GTPlayWindowLibrary.request_play_in_new_window(1600,900);yield 12
    bind()
    # Shader compilation can consume wall-clock waits without advancing physics.
    while u.GameplayStatics.get_time_seconds(world)<8:yield .2
    reference=json.loads((OUT/'LidarMud/reference.json').read_text())
    report['lidar_settings']={k:surface.get_editor_property(k) for k in reference['settings']}
    assert report['lidar_settings']==reference['settings'],'Mud response settings differ from LiDAR'
    report['lidar_soil_samples']=[]
    for x in [-2100,-1200,-500,100,900,2100]:
        q=surface.sample_surface(u.Vector2D(x,centre(x)))
        report['lidar_soil_samples'].append(dict(x=x,depth=q.sinkage_cap_cm,softness=q.softness,wetness=q.wetness,cohesion=q.cohesion))
    # Render the translated native Waves shader independently of lighting and
    # compare it with the CPU interpreter of the original SM3 disassembly.
    oracle=json.loads((ROOT/'Art/Export/MudLab/NativeReference/wave-oracle.json').read_text())
    rt=u.RenderingLibrary.create_render_target2d(world,8,8,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/M_WaveOracle')
    u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
    yield 2
    actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
    report['wave_shader_max_error']=max(abs(v-e) for c,p in zip(actual,oracle['pixels']) for v,e in zip([c.r,c.g,c.b],p[:3]))
    assert report['wave_shader_max_error']<.005,'GPU wave shader differs from original SM3 oracle'
    mud_oracle=json.loads((ROOT/'Art/Export/MudLab/NativeReference/mud-oracle.json').read_text())
    oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/M_MudBlendOracle')
    u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
    yield 1
    actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
    error=max(abs(v-e) for c,p in zip(actual,mud_oracle['pixels']) for v,e in zip([c.r,c.g,c.b],p))
    report['mud_blend_shader_max_error']=error
    assert error<.005,'GPU mud blend differs from original SM3 oracle: '+str(error)
    normal_oracle=json.loads((ROOT/'Art/Export/MudLab/NativeReference/mud-normal-oracle.json').read_text())
    oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/M_MudNormalOracle')
    u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
    yield 1
    actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
    error=max(abs(v-e) for c,p in zip(actual,normal_oracle['pixels']) for v,e in zip([c.r,c.g,c.b],p))
    report['mud_normal_shader_max_error']=error
    assert error<.005,'GPU mud normal differs from original VS oracle: '+str(error)
    water_oracle=json.loads((ROOT/'Art/Export/MudLab/NativeReference/water-oracle.json').read_text())
    for name,key in [('M_WaterStateOracle','state'),('M_WaterSedimentOracle','sediment')]:
        oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/'+name)
        u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
        yield 1
        actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
        error=max(abs(v-e) for c,p in zip(actual,water_oracle[key]) for v,e in zip([c.r,c.g,c.b],p))
        report['water_'+key+'_shader_max_error']=error
        assert error<.005,'GPU water '+key+' differs from original SM3 oracle: '+str(error)
    rt=actual=oracle_material=None
    console('CsvProfile START');report['native_spawn']=sample();report['chase_camera']=car.is_chase_camera()
    report['initial_terrain']=terrain_snapshot()
    assert car.is_chase_camera()
    for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.ScreenPercentage 100','r.VSync 0','t.MaxFPS 60']:console(cmd)
    car.disable_input(pc)
    from flora_rendered_deformation import RenderedDeformation
    rendered_ground=RenderedDeformation(world)
    yield from rendered_ground.baseline()
    review_camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector(-600,centre(0)-500,160)),'FloraDrive_RutReview')
    review_camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(review_camera.get_actor_location(),u.Vector(0,centre(0),0)),False)
    review_camera.camera_component.set_editor_property('field_of_view',60)
    pc.set_view_target_with_blend(review_camera,0);console('ShowHUD');yield 2
    yield from capture('21_ruts_before_drive')
    pc.set_view_target_with_blend(car,0);console('ShowHUD')
    yield from capture('01_start')
    report['initial_water']=sheet.mud_water_diagnostics()
    # Exercise each recovery point, then drive the entire route continuously.
    for checkpoint in [2,3,1]:
        pc.select_lane(checkpoint);yield 3
        p=car.get_actor_location();expected=DATA['recovery'][checkpoint-1]
        assert math.hypot(p.x-expected['x'],p.y-expected['y'])<120,'Recovery missed checkpoint'
    row=dict(samples=[],start=car.get_actor_location().to_tuple())
    report['route']=row
    started=u.GameplayStatics.get_time_seconds(world);wall=time.monotonic();driving=True
    captured=set()
    while car.get_actor_location().x<2370:
        p=car.get_actor_location();row['samples'].append(sample())
        assert abs(p.y-centre(p.x))<260,'Car left the running surface'
        assert u.GameplayStatics.get_time_seconds(world)-started<75,'Route traversal timed out'
        assert time.monotonic()-wall<300,'Drive simulation stalled'
        for tag,x in [('02_broken_puddles',-1000),('03_flooded_dip',710),('04_exit',2200)]:
            if p.x>x and tag not in captured:
                captured.add(tag);yield from capture(tag)
        yield .15
    driving=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
    row['end']=sample();row['travel_cm']=sum(math.dist(a['position'][:2],b['position'][:2]) for a,b in zip(row['samples'],row['samples'][1:]))
    row['max_sink_cm']=max(max(s['sink_cm'],default=0) for s in row['samples'])
    row['max_water_cm']=max(max(s['water_cm'],default=0) for s in row['samples'])
    row['max_compression_cm']=max(max(s['compression_cm'],default=0) for s in row['samples'])
    assert row['travel_cm']>4800,'Incomplete traversal'
    assert row['max_water_cm']>8,'No substantive puddle contact'
    assert row['max_compression_cm']>.2,'No soil deformation'
    yield from rendered_ground.measure('after_drive')
    report['rendered_deformation']=rendered_ground.result()
    pc.set_view_target_with_blend(review_camera,0);console('ShowHUD');yield 2
    yield from capture('22_ruts_after_drive')
    pc.set_view_target_with_blend(car,0);console('ShowHUD')
    save()
    report['water_after']=sheet.mud_water_diagnostics()
    assert 'bed_updates=0 ' not in report['water_after'],'Water did not receive changed terrain heights'
    report['surface_after']=surface.get_surface_report()
    native_visual=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRunnerVisual)[0]
    report['native_visual']=native_visual.get_research_report()
    assert 'water_shader_steps=0' not in report['native_visual'],'Native water simulation did not execute'
    report['native_water_samples']={}
    for name,target in [('state_targets',native_visual.get_research_water_state()),('sediment_targets',native_visual.get_research_water_sediment())]:
        assert target,'Missing native water render target'
        colours=[u.RenderingLibrary.read_render_target_raw_pixel(world,target,x,y,False) for y in [31,63,94] for x in [31,63,94]]
        values=[[c.r,c.g,c.b] for c in colours]
        assert all(math.isfinite(v) and -.001<=v<=1.001 for row in values for v in row),'Non-finite/out-of-range native water state'
        report['native_water_samples'][name]=values
    assert max(row[0] for row in report['native_water_samples']['sediment_targets'])>.01,'Native suspension did not reach its render target'
    target=colours=None
    native_visual=None
    assert 'native_shader=1' in report['surface_after'],'Recovered mud update path was not enabled'
    assert 'native_cells=0' not in report['surface_after'],'Recovered mud update path did no work'
    report['worked_terrain']=terrain_snapshot()
    report['max_worked_height_change_cm']=max(abs(a['height_cm']-b['height_cm']) for a,b in zip(report['initial_terrain'],report['worked_terrain']))
    assert report['max_worked_height_change_cm']>.2,'Driven tracks did not change the sampled terrain'
    # An overview is supplemental: the other images use the actual playable chase camera and HUD.
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector(-3850,-4400,4200)),'MudLab_ReviewCamera')
    eye=camera.get_actor_location();camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,u.Vector(100,0,0)),False)
    camera.get_component_by_class(u.CameraComponent).set_editor_property('field_of_view',65)
    camera.get_component_by_class(u.CameraComponent).set_editor_property('constrain_aspect_ratio',False)
    pc.set_view_target_with_blend(camera,0);yield 2
    console('ShowHUD');yield from capture('05_overview')
    for name,pos,target in [('06_forest_path',(-2350,-470,210),(900,150,640)),('07_wet_clearing',(-250,-850,190),(1000,450,470)),('08_clouds_canopy',(1500,-2000,350),(1700,1500,1900))]:
        camera.set_actor_location(u.Vector(*pos),False,True);camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False);yield 3
        yield from capture(name)
    report['water_solver_diagnostics']=sheet.water_diagnostics(False)
    console('CsvProfile STOP')


    pc.reset_lab();world=pc=car=surface=sheet=camera=None;yield 12
    bind()
    # Match simulated soil-working time, not a shorter wall-clock reload delay.
    while u.GameplayStatics.get_time_seconds(world)<report['native_spawn']['time']:yield .05
    report['reset']=sample()
    assert abs(car.get_actor_location().x+2450)<120 and abs(car.get_actor_location().y-centre(-2450))<80
    assert car.is_chase_camera() and pc.selected_lane==1
    # Chaos settles a few centimetres differently between cold start and reload.
    # Tyre sinkage at those different positions is not a terrain-reset invariant.
    report['reset_wheel_sink_difference_cm']=max(abs(a-b) for a,b in zip(report['reset']['sink_cm'],report['native_spawn']['sink_cm']))
    report['reset_position_difference_cm']=math.dist(report['reset']['position'],report['native_spawn']['position'])
    assert all(report['reset']['contacts']),'Reset vehicle is not supported on all four wheels'
    assert report['reset']['speed_cm_s']<2,'Reset vehicle did not settle'
    # RestHeight samples the authoring texture directly; the live field is bilinearly
    # filtered at a different resolution. Fresh compression therefore need not be zero.
    # Compare the same world points with their measured fresh baseline instead.
    report['reset_terrain']=terrain_snapshot()
    report['max_reset_height_error_cm']=max(abs(a['height_cm']-b['height_cm']) for a,b in zip(report['initial_terrain'],report['reset_terrain']))
    report['reset_surface']=surface.get_surface_report()
    assert report['max_reset_height_error_cm']<.01,'Reload did not restore the fresh height field'
    # The occupied muddy entry immediately accumulates new soil work after reload.
    # Exact restoration of the route probes above is the reset invariant.
    report['performance_verified']=False;report['performance_note']='Functional run includes pauses, screenshots and recovery; see separate render spot checks for timing.';report['ok']=True;save()
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
    global deadline,busy,driving,steps
    if busy:return
    busy=True
    try:
        assert time.monotonic()-began<550,'Lab test deadline'
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

