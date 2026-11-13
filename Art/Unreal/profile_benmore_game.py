"""Uncooked standalone game capture, without a retained editor scene.

Launch only through profile_benmore_game.ps1. CSV records every frame; no
screenshots or pauses occur within measurement windows. This is not Shipping.
"""
import unreal as u
import json, os, sys, time, traceback, shutil, subprocess, re
from pathlib import Path

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path[:0] = [str(ROOT/'Art/tools'), str(ROOT/'Art/Unreal')]
from benmore_profile_metrics import analyse,compare_isolation
import benmore_render_controls as render_controls
OUT = Path(os.environ['GT_BENMORE_PROFILE_OUT'])
OPTIONS = json.loads(os.environ['GT_BENMORE_PROFILE_OPTIONS'])
assert OUT.is_dir() and not (OUT/'profile-report.json').exists()
CSV = ROOT/'Saved/Profiling/CSV'
world = pc = driver = None
restore_cvars = {}
shadow_components = []
DRIVING=OPTIONS['mode'] in ('Driving','CompareDriving')
COMPARING=OPTIONS['mode'] in ('Compare','CompareDriving')
TRIALS = {
    'willow_visibility': ('Diagnostic.WillowsVisible',0),
    'raytracing_instances_lod': ('r.RayTracing.Geometry.InstancedStaticMeshes.MinLOD',2),
    'motion_blur': ('r.MotionBlurQuality',0),
    'tsr_16bit': ('r.TSR.16BitVALU.Nvidia',1),
    'lumen_cache_updates': ('Diagnostic.LumenCacheUpdates',1),
    'lumen_diffuse_off': ('r.Lumen.DiffuseIndirect.Allow',0),
    'fleet_far_lod': ('Diagnostic.FleetFarLOD',1),
    'temporal_aa': ('r.AntiAliasingMethod',2),
    'tsr_history': ('r.TSR.History.ScreenPercentage',100),
    'screen_percentage': ('r.ScreenPercentage',75),
    'screen_percentage_60': ('r.ScreenPercentage',60),
    'lumen_atlas': ('r.LumenScene.SurfaceCache.AtlasSize',2048),
    'nanite_pool': ('r.Nanite.Streaming.StreamingPoolSize',128),
    'grass_tick': ('grass.TickInterval',4),
    'shadow_coarse': ('r.Shadow.Virtual.NonNanite.IncludeInCoarsePages',0),
    'shadow_resolution': ('r.Shadow.Virtual.ResolutionLodBiasDirectional',0),
    'lumen_gather': ('r.Lumen.ScreenProbeGather.DownsampleFactor',32),
    'tsr_update': ('r.TSR.History.UpdateQuality',2),
    'grass_shadows': ('grass.DisableDynamicShadows',1),
    'nanite_lod': ('r.Nanite.MaxPixelsPerEdge',2),
    'raytracing_vehicle_lod': ('r.RayTracing.Geometry.SkeletalMeshes.LODBias',1),
    'raytracing_landscape_lod': ('r.RayTracing.Geometry.Landscape.LODBias',1),
    'receiver_mask': ('r.Shadow.Virtual.UseReceiverMaskDirectional',0),
    'gravel_pom': ('MPC_Benmore_GravelPOM.Enabled',0),
    'fine_spray': ('gt.Spray.Fine',0),
    'grass_density': ('grass.DensityScale',.35),
    'high_opaque_gi': ('Diagnostic.HighOpaqueGI',1),
    'lumen_irradiance': ('r.Lumen.FinalGatherMethod',0),
    'lumen_async': ('r.Lumen.AsyncCompute',0),
    'contrast_vrs': ('r.VRS.ContrastAdaptiveShading',0),
    'parked_fleet': ('Diagnostic.ParkedFleetVisible',0),
    'authored_tussocks': ('Diagnostic.AuthoredTussocksVisible',0),
}
report = dict(ok=False, target_fps=80, target_frame_ms=12.5, target_verified=False,
              runtime=('Normal game in PIE' if OPTIONS.get('pie') else 'Uncooked standalone game')+', audio enabled', runs=[], options=OPTIONS,
              stationary_only=not DRIVING, driving_tested=False)


def console(command):
    u.SystemLibrary.execute_console_command(world, command, pc)


def pom_collection():
    # Codex's gravel parallax switch (back on MPC_Benmore_GravelPOM after the Benmore triage).
    value=u.load_asset('/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface/MPC_Benmore_GravelPOM')
    assert value,'Gravel POM collection missing'
    return value


def setting(flag):
    if flag.startswith('Diagnostic.'):return render_controls.get(flag,world)
    if flag=='MPC_Benmore_GravelPOM.Enabled':
        return u.MaterialLibrary.get_scalar_parameter_value(world,pom_collection(),'Enabled')
    return u.SystemLibrary.get_console_variable_float_value(flag)


def apply_setting(flag,value):
    if flag.startswith('Diagnostic.'):
        render_controls.set_value(flag,value,world,pc)
    elif flag=='MPC_Benmore_GravelPOM.Enabled':
        u.MaterialLibrary.set_scalar_parameter_value(world,pom_collection(),'Enabled',value)
    else:console(flag+' '+str(value))
    assert abs(setting(flag)-value)<1.e-5,'Setting rejected: '+flag


def apply_landscape_shadow_cache(active):
    for component,original in shadow_components:
        mode=u.ShadowCacheInvalidationBehavior.RIGID if active else original
        component.set_editor_property('shadow_cache_invalidation_behavior',mode)
        # Refresh the render proxy outside the timed window. Collision and
        # landscape geometry remain untouched. Restoring uses the same path.
        component.set_cast_shadow(False)
        component.set_cast_shadow(True)
        assert component.get_editor_property('shadow_cache_invalidation_behavior')==mode


def shader_cpu():
    p = subprocess.run(['powershell', '-NoProfile', '-Command',
        '(Get-Process ShaderCompileWorker -ErrorAction SilentlyContinue | Measure-Object CPU -Sum).Sum'],
        capture_output=True, text=True, timeout=20)
    assert p.returncode == 0
    return float(p.stdout.strip() or 0)


def grass_state():
    result={}
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.LandscapeProxy):
        for component in actor.get_components_by_class(u.GrassInstancedStaticMeshComponent):
            if not component.static_mesh or not component.is_visible():continue
            row=result.setdefault(component.static_mesh.get_path_name(),dict(components=0,shadow_casters=0))
            row['components']+=1
            row['shadow_casters']+=int(component.get_editor_property('cast_shadow'))
    assert result, 'Generated grass has not populated'
    return result


def capture():
    global world, pc, driver
    # -ExecCmds is processed after loading the explicitly supplied game map.
    world = (u.EditorLevelLibrary.get_game_world() if OPTIONS.get('pie') else
             u.find_object(None, '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.L_Benmore_GaeaReview'))
    assert isinstance(world, u.World), 'Standalone game world not found'
    yield 10
    pc = u.GameplayStatics.get_player_controller(world, 0)
    assert pc
    if not DRIVING:
        pawn=u.GameplayStatics.get_player_pawn(world,0)
        if isinstance(pawn,u.GTCarPawn):
            # Use the ordinary brakes to keep the detached-camera reference
            # from drifting downhill; do not change simulation or handling.
            pawn.reset_driving_inputs()
            pawn.get_chaos_movement().set_throttle_input(0)
            pawn.get_chaos_movement().set_brake_input(1)
            pawn.get_chaos_movement().set_handbrake_input(True)
    report['resolution'] = list(pc.get_viewport_size())
    assert report['resolution'] == [OPTIONS.get('output_width',1600),OPTIONS.get('output_height',900)], 'Unexpected standalone output size'
    shot_size='x'.join(str(v) for v in report['resolution'])
    for command in ('t.MaxFPS '+str(OPTIONS.get('frame_limit',0)), 'r.VSync 0', 'r.ScreenPercentage '+str(OPTIONS.get('screen_percentage',100)), 'r.DynamicRes.OperationMode 0',
                    'gt.Look.Weather Clear'):
        console(command)
    if OPTIONS.get('adaptive'):
        for command in ('r.DynamicRes.MinScreenPercentage 50',
                        'r.DynamicRes.MaxScreenPercentage '+str(OPTIONS['screen_percentage']),
                        'r.DynamicRes.FrameTimeBudget 11.5','r.DynamicRes.AllowInPIE 1','r.DynamicRes.OperationMode 2'):
            console(command)
    report['settings'] = {flag:u.SystemLibrary.get_console_variable_float_value(flag) for flag in (
        'r.ScreenPercentage','r.TSR.History.ScreenPercentage','r.Lumen.HardwareRayTracing','r.VRS.ContrastAdaptiveShading','r.VRS.EnableSoftware',
        'r.Lumen.Reflections.Allow','r.Shadow.Virtual.MaxPhysicalPages','r.Nanite.Streaming.StreamingPoolSize',
        'r.VolumetricCloud','grass.DensityScale','grass.CullDistanceScale','gt.Spray.SparseUpdates',
        'r.LumenScene.SurfaceCache.AtlasSize','r.Lumen.ScreenProbeGather.DownsampleFactor',
        'r.Shadow.Virtual.ResolutionLodBiasDirectional','r.TSR.History.UpdateQuality','grass.TickInterval',
        't.MaxFPS','r.DynamicRes.OperationMode','r.DynamicRes.MinScreenPercentage',
        'r.DynamicRes.MaxScreenPercentage','r.DynamicRes.FrameTimeBudget')}
    console('csvcategory NaniteStreamingDetail enable')
    console('csvcategory VSM enable')
    if not report.get('shadow_inventory'):
        inventory=[]
        for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
            for c in actor.get_components_by_class(u.PrimitiveComponent):
                if not c.get_editor_property('cast_shadow'):continue
                origin,extent,radius=u.SystemLibrary.get_component_bounds(c)
                if radius<1000:continue
                inventory.append(dict(component=c.get_path_name(),actor=actor.get_actor_label(),
                    radius_m=radius*.01,extent_m=[v*.01 for v in extent.to_tuple()],
                    cache=str(c.get_editor_property('shadow_cache_invalidation_behavior')),
                    materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())]))
        report['shadow_inventory']=sorted(inventory,key=lambda r:-r['radius_m'])
    cameras = {a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor)}
    parked_driver = None
    if not DRIVING and 'Vegetation' in OPTIONS['views']:
        from benmore_profile_drive import Driver
        parked_driver = Driver(world,pc,ROOT)
    if DRIVING:
        from benmore_profile_drive import Driver
        driver = Driver(world,pc,ROOT)
    trial = None
    if COMPARING:
        if OPTIONS['stage']=='landscape_shadow_cache':
            for actor in u.GameplayStatics.get_all_actors_of_class(world,u.LandscapeProxy):
                for component in actor.get_components_by_class(u.LandscapeComponent):
                    original_mode=component.get_editor_property('shadow_cache_invalidation_behavior')
                    if component.get_editor_property('cast_shadow') and original_mode==u.ShadowCacheInvalidationBehavior.AUTO:
                        shadow_components.append((component,original_mode))
            assert shadow_components,'No automatic landscape shadow components'
            flag,original,candidate='Landscape.ShadowCacheInvalidationBehavior',0,1
            report['diagnostic_only']='Suppressing landscape material invalidations is attribution only; changing deformation shadows requires a separate correctness-preserving implementation.'
            report['shadow_components']=[c.get_path_name() for c,_ in shadow_components]
        else:
            flag,candidate=TRIALS[OPTIONS['stage']]
            original=setting(flag)
            assert original!=candidate, 'This candidate is already loaded'
            restore_cvars[flag]=original
        trial=(flag,original,candidate)
        report['trial']=dict(stage=OPTIONS['stage'],cvar=flag,reference=original,candidate=candidate)
        report.setdefault('trials',[]).append(dict(report['trial']))
        if OPTIONS['stage']=='nanite_pool':
            assert u.SystemLibrary.get_console_variable_int_value('r.Nanite.Streaming.Debug.StreamingPoolResize')==1
            console('csvcategory NaniteStreamingDetail enable')
    for view in OPTIONS['views']:
        reference_grass=None
        for repeat in range(4 if trial else OPTIONS['repeats']):
            active=bool(trial and repeat in (1,2))
            if trial:
                flag,original,candidate=trial
                if shadow_components:apply_landscape_shadow_cache(active)
                else:apply_setting(flag,candidate if active else original)
                if OPTIONS['stage'] in ('grass_shadows','grass_density'):console('grass.FlushCachePIE')
            if driver:
                placement = driver.place(view)
            elif view == 'Vegetation':
                # Match the real road/fleet approach, with the ordinary brakes
                # held throughout stationary A/B trials. No authored camera is
                # present here in the saved map.
                placement = parked_driver.place(view)
            else:
                camera = cameras['Benmore_RL_Camera_'+view]
                pc.set_view_target_with_blend(camera,0)
                placement = dict(camera=camera.get_path_name(), position_cm=list(camera.get_actor_location().to_tuple()))
            # Warm to sustained clocks and let the observed startup DDC scan
            # finish (it ran into the previous 120-second warmup's first window).
            yield 240 if not report['runs'] else 20
            if driver or (parked_driver and view == 'Vegetation'):
                # A braked car can creep on a slope during the long warmup.
                # Re-place only outside measurement, then allow ordinary
                # suspension/contact settling plus shader/screenshot waits.
                placement = (driver or parked_driver).place(view)
                yield 5
            previous = shader_cpu()
            idle = 0
            for _ in range(100):
                yield 3
                current = shader_cpu()
                idle = idle+3 if abs(current-previous)<.1 else 0
                previous = current
                if idle>=9:break
            assert idle>=9, 'Shaders did not settle'
            # Read outside timed windows. Imported LODs alone don't establish
            # which geometry the live fleet is actually drawing.
            if repeat==0:
                report.setdefault('runtime_vehicle_lods',{})[view]=render_controls.vehicle_lods(world)
            grass=None
            if trial and OPTIONS['stage']=='grass_shadows':
                grass=grass_state()
                if reference_grass is None:
                    reference_grass=grass
                    assert any(r['shadow_casters'] for r in grass.values()), 'Grass shadows already disabled'
                assert set(grass)==set(reference_grass), 'Grass mesh coverage changed'
                for mesh,state in reference_grass.items():
                    if not DRIVING:
                        assert .95*state['components']<=grass[mesh]['components']<=1.05*state['components'], 'Grass regeneration incomplete'
                    if active:assert grass[mesh]['shadow_casters']==0, 'Grass shadows remained enabled'
                    elif not DRIVING:assert grass[mesh]['shadow_casters']>=state['shadow_casters']*.95
                    else:assert grass[mesh]['shadow_casters']>0,'Reference grass shadows absent'
            atlas_stats = None
            if repeat==0 or (trial and OPTIONS['stage']=='lumen_atlas'):
                log_path=OUT/'editor.log'
                log_start=log_path.stat().st_size
                console('r.LumenScene.DumpStats 1')
                yield 3
                with log_path.open('rb') as log:
                    log.seek(log_start)
                    dump=log.read().decode('utf-8',errors='replace')
                match=re.search(r'Allocated (\d+) physical pages out of (\d+)',dump)
                assert match, 'Missing Lumen surface-cache occupancy telemetry'
                used,total=map(int,match.groups())
                expected=u.SystemLibrary.get_console_variable_int_value('r.LumenScene.SurfaceCache.AtlasSize')
                assert total==(expected//128)**2, 'Atlas capacity did not change as requested'
                assert used<total*.8, 'Lumen atlas lacks working-set headroom'
                atlas_stats=dict(allocated_pages=used,capacity_pages=total,raw=dump)
            if repeat == 0 or (trial and repeat == 1):
                # One-frame queue event attribution outside measurement.
                # Separate graphics/compute durations are not additive costs.
                old_ui=u.SystemLibrary.get_console_variable_int_value('r.ProfileGPU.ShowUI')
                console('r.ProfileGPU.ShowUI 0')
                console('profilegpu')
                yield 3
                console('r.ProfileGPU.ShowUI '+str(old_ui))
                suffix='_candidate' if active else '_reference' if trial else '_start'
                prefix=OPTIONS['stage']+'_' if OPTIONS.get('stages') else ''
                console('HighResShot '+shot_size+' filename="'+(OUT/(prefix+view+suffix+'.png')).as_posix()+'"')
                yield 10
            assert list(pc.get_viewport_size()) == report['resolution']
            before = set(CSV.glob('*.csv'))
            cpu_before = shader_cpu()
            yield 2
            if driver:driver.begin()
            console('csvprofile start')
            start = time.monotonic()
            while time.monotonic()-start < OPTIONS['seconds']:
                if driver:driver.step()
                yield .1 if driver else 1
            console('csvprofile stop')
            if driver:driver.stop()
            yield 4
            assert abs(shader_cpu()-cpu_before)<.1, 'Shader compilation inside capture'
            new = set(CSV.glob('*.csv'))-before
            assert len(new)==1
            source = new.pop()
            destination = OUT/source.name
            shutil.copy2(source,destination)
            metrics = analyse(source)
            if OPTIONS.get('adaptive'):
                scale=metrics['metrics']['DynamicResolutionPercentage']
                assert scale['min']>=49.9 and scale['max']<=OPTIONS['screen_percentage']+.1, 'Adaptive resolution inactive or outside bounds'
            row = dict(view=view,repeat=repeat,csv=str(destination),analysis=metrics,placement=placement)
            if OPTIONS['stage']=='fleet_far_lod':row['vehicle_lods']=render_controls.vehicle_lods(world)
            if atlas_stats:row['lumen_atlas']=atlas_stats
            if grass:
                row['grass']=grass
                end_grass=grass_state()
                if DRIVING:
                    # Moving through generated grass legitimately loads and
                    # retires components. Verify the shadow treatment on the
                    # newly generated components, not identical component counts.
                    row['grass_end']=end_grass
                    assert set(end_grass)==set(grass),'Grass mesh families changed during drive'
                    if active:assert all(s['shadow_casters']==0 for s in end_grass.values()),'New grass retained shadows'
                    else:assert all(s['shadow_casters']>0 for s in end_grass.values()),'Reference lost all grass shadows'
                else:assert end_grass==grass, 'Grass component/shadow state changed during capture'
            if trial:
                if shadow_components:
                    assert all(c.get_editor_property('shadow_cache_invalidation_behavior')==(u.ShadowCacheInvalidationBehavior.RIGID if active else old) for c,old in shadow_components)
                else:assert abs(setting(flag)-(candidate if active else original))<1.e-5
                row.update(feature=OPTIONS['stage'],disabled=active,candidate_active=active,iteration=repeat)
            size=metrics['metrics']['NaniteStreamingDetail/StreamingPoolSizeMB']
            visible=metrics['metrics']['NaniteStreamingDetail/VisibleStreamingDataSizeMB']
            assert size['min']==size['max']==u.SystemLibrary.get_console_variable_int_value('r.Nanite.Streaming.StreamingPoolSize')
            assert visible['max']<size['min']*.8, 'Nanite visible working set lacks headroom'
            if driver:
                row['drive_samples'] = driver.samples
                row['distance_m'] = driver.distance
                assert driver.distance >= OPTIONS['seconds'], 'Insufficient real vehicle movement'
                if view == 'Ford':
                    assert any(s['water_particles']>0 for s in driver.samples), 'Ford route never exercised water spray'
                console('HighResShot '+shot_size+' filename="'+(OUT/(OPTIONS['stage']+'_'+view+'_'+str(repeat)+'_end.png')).as_posix()+'"')
                yield 10
            report['runs'].append(row)
            (OUT/'profile-progress.json').write_text(json.dumps(report,indent=2))
            memory = metrics['local_memory']
            assert memory, 'Missing local memory telemetry'
            # Preserve unknown samples as failures, but finish the other routes
            # so a missing counter sample cannot hide their performance costs.
            row['memory_telemetry_complete'] = memory['unavailable_frames']==0
            assert memory['over_budget_frames']==0, 'Local VRAM budget exceeded'
    report['driving_tested'] = bool(driver)
    if trial:report['comparisons']=compare_isolation(report['runs'])
    report['frame_time_gate_passed'] = all(r['analysis']['metrics']['FrameTime']['p99']<=12.5 for r in report['runs'])
    report['headroom_gate_passed'] = all(r['analysis']['local_memory']['unavailable_frames']==0 and r['analysis']['local_memory']['below_proposed_headroom_frames']==0 for r in report['runs'])
    # A short scripted route cannot certify sustained interactive play by itself.
    report['ok'] = True


def main():
    # Separate ABBA experiments share the initial warmup, not settings. Restore
    # and verify every candidate before beginning the next experiment.
    for stage in OPTIONS.get('stages') or [OPTIONS['stage']]:
        OPTIONS['stage']=stage
        yield from capture()
        if shadow_components:
            apply_landscape_shadow_cache(False)
            shadow_components.clear()
        for flag,value in restore_cvars.items():
            apply_setting(flag,value)
        if 'grass.DensityScale' in restore_cvars:console('grass.FlushCachePIE')
        report['ok']=False
    report['ok']=True


def finish(error=None):
    global gen, world
    gen = None
    # An external build can invalidate startup before capture() first assigns
    # world. Still quit our game instead of leaving an unmeasured process alive.
    if world is None and not OPTIONS.get('pie'):
        world=u.find_object(None, '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.L_Benmore_GaeaReview')
    if error:
        report.update(ok=False,error=error)
        u.log_error(error)
    if driver:driver.stop()
    if world:
        if shadow_components:apply_landscape_shadow_cache(False)
        for flag,value in restore_cvars.items():apply_setting(flag,value)
        if any(f in restore_cvars for f in ('grass.DisableDynamicShadows','grass.DensityScale')):console('grass.FlushCachePIE')
        report['restored_settings']={f:setting(f) for f in restore_cvars}
    report['render_diagnostics']=render_controls.metadata()
    (OUT/'profile-report.json').write_text(json.dumps(report,indent=2))
    u.unregister_slate_post_tick_callback(handle)
    if world:
        console('csvprofile stop')
        if OPTIONS.get('pie'):
            u.EditorLevelLibrary.editor_end_play()
            u.SystemLibrary.quit_editor()
        else:console('quit')


gen = main()
next_at = started = time.monotonic()
busy = False


def tick(dt):
    global busy,next_at
    if busy or gen is None:return
    busy = True
    try:
        if (OUT/'external-load-invalid.json').exists():raise RuntimeError('External workload detected')
        if time.monotonic()-started>2400:raise RuntimeError('Bounded game profiler timeout')
        if time.monotonic()>=next_at:next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False


handle = u.register_slate_post_tick_callback(tick)
