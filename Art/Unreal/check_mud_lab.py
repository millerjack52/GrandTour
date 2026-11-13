"""Rendered PIE acceptance: possession, three driven lanes, deformation, water and reset."""
import json,time,traceback,math
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/MudLab'
LEVEL='/Game/GrandTour/ArtTests/MudLab/L_MudLab'
report=dict(ok=False,level=LEVEL,lanes=[],images=[])
world=pc=car=surface=sheet=camera=None
driving=False
PROBES=[(x,y+offset) for x in range(-600,650,100) for y in [-850,0,850] for offset in [-85,85]]

def save():(OUT/'playtest-report.json').write_text(json.dumps(report,indent=2))
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
    console('HighResShot 1440x900 filename="'+path.as_posix()+'"')
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
    editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    u.SystemLibrary.execute_console_command(editor_world,'Automation RunTests GrandTour.MudRunner.ShaderOracle')
    editor_world=None
    yield 14
    while u.AutomationLibrary.are_automated_tests_running():yield .25
    u.GTPlayWindowLibrary.request_play_in_new_window(1440,900);yield 12
    bind()
    # Render the translated native Waves shader independently of lighting and
    # compare it with the CPU interpreter of the original SM3 disassembly.
    oracle=json.loads((OUT/'NativeReference/wave-oracle.json').read_text())
    rt=u.RenderingLibrary.create_render_target2d(world,8,8,u.TextureRenderTargetFormat.RTF_RGBA16F,u.LinearColor(0,0,0,1),False,False)
    oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/M_WaveOracle')
    u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
    yield 2
    actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
    report['wave_shader_max_error']=max(abs(v-e) for c,p in zip(actual,oracle['pixels']) for v,e in zip([c.r,c.g,c.b],p[:3]))
    assert report['wave_shader_max_error']<.005,'GPU wave shader differs from original SM3 oracle'
    mud_oracle=json.loads((OUT/'NativeReference/mud-oracle.json').read_text())
    oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/M_MudBlendOracle')
    u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
    yield 1
    actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
    error=max(abs(v-e) for c,p in zip(actual,mud_oracle['pixels']) for v,e in zip([c.r,c.g,c.b],p))
    report['mud_blend_shader_max_error']=error
    assert error<.005,'GPU mud blend differs from original SM3 oracle: '+str(error)
    normal_oracle=json.loads((OUT/'NativeReference/mud-normal-oracle.json').read_text())
    oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/M_MudNormalOracle')
    u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
    yield 1
    actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
    error=max(abs(v-e) for c,p in zip(actual,normal_oracle['pixels']) for v,e in zip([c.r,c.g,c.b],p))
    report['mud_normal_shader_max_error']=error
    assert error<.005,'GPU mud normal differs from original VS oracle: '+str(error)
    water_oracle=json.loads((OUT/'NativeReference/water-oracle.json').read_text())
    for name,key in [('M_WaterStateOracle','state'),('M_WaterSedimentOracle','sediment')]:
        oracle_material=u.load_asset('/Game/GrandTour/ArtTests/MudLab/'+name)
        u.RenderingLibrary.draw_material_to_render_target(world,rt,oracle_material)
        yield 1
        actual=[u.RenderingLibrary.read_render_target_raw_pixel(world,rt,x,y,False) for y in range(8) for x in range(8)]
        error=max(abs(v-e) for c,p in zip(actual,water_oracle[key]) for v,e in zip([c.r,c.g,c.b],p))
        report['water_'+key+'_shader_max_error']=error
        assert error<.005,'GPU water '+key+' differs from original SM3 oracle: '+str(error)
    rt=actual=oracle_material=None
    report['native_spawn']=sample();report['chase_camera']=car.is_chase_camera()
    report['initial_terrain']=terrain_snapshot()
    assert car.is_chase_camera()
    for cmd in ['DisableAllScreenMessages','r.MotionBlurQuality 0','r.VSync 0','t.MaxFPS 60']:console(cmd)
    car.disable_input(pc)
    yield from capture('01_start')
    report['initial_water']=sheet.mud_water_diagnostics()
    for lane in [1,2,3]:
        pc.select_lane(lane);yield 3
        p=car.get_actor_location()
        assert abs(p.x+1200)<120 and abs(p.y-(lane-2)*850)<80,'Lane reset missed its start'
        row=dict(lane=lane,samples=[],start=p.to_tuple())
        report['lanes'].append(row)
        started=u.GameplayStatics.get_time_seconds(world);wall=time.monotonic();driving=True
        while u.GameplayStatics.get_time_seconds(world)-started<12 and car.get_actor_location().x<650:
            row['samples'].append(sample());yield .15
            assert time.monotonic()-wall<150,'Drive simulation stalled'
        driving=False;car.reset_driving_inputs();car.get_chaos_movement().set_handbrake_input(True)
        row['end']=sample();row['travel_cm']=row['end']['position'][0]-row['start'][0]
        row['max_sink_cm']=max((max(s['sink_cm'],default=0) for s in row['samples']),default=0)
        row['max_water_cm']=max((max(s['water_cm'],default=0) for s in row['samples']),default=0)
        row['max_compression_cm']=max((max(s['compression_cm'],default=0) for s in row['samples']),default=0)
        assert row['travel_cm']>600,'Car did not reach the test surface'
        assert all(math.isfinite(v) for s in row['samples'] for v in s['position']),'Non-finite physics'
        save();yield from capture('0%d_lane_%d'%(lane+1,lane))
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
    assert report['lanes'][1]['max_sink_cm']>report['lanes'][0]['max_sink_cm']+1,'No measurable firm/soft distinction'
    assert report['lanes'][1]['max_compression_cm']>.2,'No lasting soil deformation'
    assert report['lanes'][2]['max_water_cm']>5,'No water interaction'
    # An overview is supplemental: the other images use the actual playable chase camera and HUD.
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(location=u.Vector(-2050,-2350,1900)),'MudLab_ReviewCamera')
    eye=camera.get_actor_location();camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(eye,u.Vector(100,0,0)),False)
    camera.get_component_by_class(u.CameraComponent).set_editor_property('field_of_view',65)
    camera.get_component_by_class(u.CameraComponent).set_editor_property('constrain_aspect_ratio',False)
    pc.set_view_target_with_blend(camera,0);yield 2
    yield from capture('05_overview')
    console('viewmode unlit');yield 2
    yield from capture('06_diffuse_diagnostic')
    console('viewmode lit')
    pc.reset_lab();world=pc=car=surface=sheet=camera=None;yield 12
    bind();report['reset']=sample()
    assert abs(car.get_actor_location().x+1200)<120 and abs(car.get_actor_location().y+850)<80
    assert car.is_chase_camera() and pc.selected_lane==1
    assert max(report['reset']['sink_cm'],default=0)<1
    # RestHeight samples the authoring texture directly; the live field is bilinearly
    # filtered at a different resolution. Fresh compression therefore need not be zero.
    # Compare the same world points with their measured fresh baseline instead.
    report['reset_terrain']=terrain_snapshot()
    report['max_reset_height_error_cm']=max(abs(a['height_cm']-b['height_cm']) for a,b in zip(report['initial_terrain'],report['reset_terrain']))
    report['reset_surface']=surface.get_surface_report()
    assert report['max_reset_height_error_cm']<.01,'Reload did not restore the fresh height field'
    assert 'excavated_cm3=0.000 ' in report['reset_surface'],'Reload retained accumulated soil work'
    report['ok']=True;save()
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
            move=car.get_chaos_movement();move.set_handbrake_input(False);move.set_throttle_input(.6);move.set_brake_input(0);move.set_steering_input(0)
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        steps=None
        import gc
        gc.collect();u.SystemLibrary.collect_garbage()
        u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error']);driving=False
        if world:u.GameplayStatics.set_game_paused(world,False)
        steps=finish();deadline=time.monotonic()+next(steps)
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
