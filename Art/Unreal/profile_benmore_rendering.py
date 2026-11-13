"""Stationary rendering isolation. Run ONLY with other games closed.

No driving/physics conclusions; no screenshots inside CSV capture windows.
Every test brackets one disabled feature with baseline samples (ABBA).
"""
import unreal as u
import json,os,time,traceback,subprocess,sys,shutil
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/tools'))
from benmore_profile_metrics import analyse,compare_isolation
assert os.environ.get('GT_BENMORE_PROFILE_OUT'), 'Launch through the guarded PowerShell runner'
OUT=Path(os.environ['GT_BENMORE_PROFILE_OUT']).resolve()
assert OUT.is_dir() and not (OUT/'profile-report.json').exists(), 'Fresh run directory required'
OPTIONS=json.loads(os.environ.get('GT_BENMORE_PROFILE_OPTIONS','{}'))
CAPTURE_SECONDS=int(OPTIONS.get('seconds',60))
MODE=OPTIONS.get('mode','Baseline')
REPEATS=int(OPTIONS.get('repeats',3))
VIEWS=OPTIONS.get('views',['Ford','Long_Vista','Lake_Mouth'])
CSV=ROOT/'Saved/Profiling/CSV';LEVEL='/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
world=pc=None;report={'ok':False,'resolution':[1440,900],'stationary_only':True,
    'driving_tested':False,'full_baseline_complete':False,'runs':[],
    'target_fps':80,'target_frame_ms':1000/80,'target_verified':False,
    'scope':'Stationary renderer isolation only; continuous driving and full CPU/streaming validation remain required.'}
editor_mesh_metadata={}
restore_cvars={}
candidate_stage=None
u.EditorPythonScripting.set_keep_python_script_alive(True)

def console(text):u.SystemLibrary.execute_console_command(world,text,pc)
def files():return set(CSV.glob('*.csv'))
def shader_cpu():
    result=subprocess.run(['powershell','-NoProfile','-Command','(Get-Process ShaderCompileWorker -ErrorAction SilentlyContinue | Measure-Object CPU -Sum).Sum'],capture_output=True,text=True,timeout=20)
    assert result.returncode==0, 'Cannot verify shader worker inactivity'
    return float(result.stdout.strip() or 0)

def foliage_inventory(components):
    """Read actual runtime bindings; setup scripts alone are not asset evidence."""
    rows=[];meshes={};materials={}
    sm=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    for c in components:
        mesh=c.static_mesh
        if not mesh:continue
        path=mesh.get_path_name()
        if path not in meshes:
            if u.EditorLevelLibrary.get_game_world():
                # These editor APIs return -1/empty during PIE, not real LOD data.
                metadata=editor_mesh_metadata.get(path,{
                    'lod_count':None,'lod_screen_sizes':None,'vertices_by_lod':None,
                    'lod_metadata_status':'Not collected before PIE'})
            else:
                lods=sm.get_lod_count(mesh)
                assert lods>0, 'Unavailable authored mesh LOD metadata: '+path
                metadata={'lod_count':lods,'lod_screen_sizes':list(sm.get_lod_screen_sizes(mesh)),
                    'vertices_by_lod':[sm.get_number_verts(mesh,i) for i in range(lods)],
                    'lod_metadata_status':'Editor read before PIE'}
                editor_mesh_metadata[path]=metadata
            meshes[path]={**metadata,'nanite_enabled':mesh.get_editor_property('nanite_settings').enabled}
        bindings=[]
        for material in c.get_materials():
            if not material:bindings.append(None);continue
            name=material.get_path_name();bindings.append(name)
            base=material
            while isinstance(base,u.MaterialInstance):base=base.get_editor_property('parent')
            if base and isinstance(base,u.Material) and name not in materials:
                materials[name]={'base':base.get_path_name(),
                    'base_blend_mode':str(base.get_editor_property('blend_mode')),
                    'base_two_sided':base.get_editor_property('two_sided'),
                    'note':'Base properties; instance overrides and compiled shader cost require separate inspection.'}
        rows.append({'component':c.get_path_name(),'actor':c.get_owner().get_actor_label(),
            'class':c.get_class().get_name(),'mesh':path,'instances':c.get_instance_count(),
            'materials':bindings,'visible':c.is_visible(),
            **{key:c.get_editor_property(key) for key in
               ['instance_start_cull_distance','instance_end_cull_distance','cast_shadow',
                'affect_distance_field_lighting','visible_in_ray_tracing']}})
    return {'components':rows,'meshes':meshes,'materials':materials,
        'note':'Authored LOD metadata, not the LOD selected for every rendered instance.'}
def main():
    global world,pc,candidate_stage
    assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
    ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if MODE=='Candidate':
        sys.path.insert(0,str(ROOT/'Art/Unreal'))
        from benmore_performance_stages import Candidate
        candidate_stage=Candidate(OPTIONS['stage'],ROOT,OUT.name,OPTIONS.get('far_lod_screen',.008))
        report['candidate']=candidate_stage.metadata
    # Collect authored foliage LODs while the editor-only APIs are available.
    editor_foliage=[c for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent)
        if c.static_mesh and any(token in c.static_mesh.get_path_name().lower()
            for token in ('tussock','willow','shrub','scrub','grass'))]
    try:report['editor_foliage_inventory']=foliage_inventory(editor_foliage)
    except Exception:report['editor_foliage_inventory_error']=traceback.format_exc()
    if OPTIONS.get('disable_editor_viewport_realtime',False):
        u.get_editor_subsystem(u.LevelEditorSubsystem).editor_set_viewport_realtime(False)
        report['editor_viewport_realtime_override_requested']=True
        # This affects the editor viewport, not PIE. It may retain allocated
        # resources; any memory/performance benefit must still be measured.
    # Offscreen Slate starts with r.SetRes's 1280x720 virtual desktop, which
    # clips the requested PIE client area. Enlarge that virtual desktop first;
    # retain the exact 1440x900 viewport assertion below.
    u.SystemLibrary.execute_console_command(ew,'r.SetRes 1920x1080w')
    yield 2
    # Keep all gameplay subsystems, but use a stationary camera with no pawn.
    ew.get_world_settings().set_editor_property('default_game_mode',u.GameModeBase)
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
    yield 20
    world=u.EditorLevelLibrary.get_game_world();assert world
    pc=u.GameplayStatics.get_player_controller(world,0);assert pc
    report['actual_viewport']=list(pc.get_viewport_size())
    report['requested_resolution']=[1440,900]
    # Offscreen Slate adds two client pixels on this host. Record the rendered
    # size explicitly and require it to remain identical in every comparison.
    assert report['actual_viewport'] in ([1440,900],[1440,902]), 'Unexpected viewport size'
    report['resolution']=report['actual_viewport']
    for command in ['t.MaxFPS 0','r.VSync 0','r.ScreenPercentage 100','r.DynamicRes.OperationMode 0']:console(command)
    console('gt.Look.Weather Clear')
    previous=shader_cpu();idle=0
    for attempt in range(100):
        yield 3
        current=shader_cpu();idle=idle+3 if abs(current-previous)<.1 else 0;previous=current
        if idle>=9:break
    assert idle>=9, 'Shaders did not settle; no profile is valid'
    report['shader_workers_idle_checked']=True
    report['options']=OPTIONS
    report['settings']={name:u.SystemLibrary.get_console_variable_float_value(name) for name in
        ['r.ScreenPercentage','r.DynamicRes.OperationMode','r.VSync','t.MaxFPS',
         'r.Lumen.HardwareRayTracing','sg.GlobalIlluminationQuality','sg.ReflectionQuality',
         'sg.ShadowQuality','grass.DensityScale','grass.CullDistanceScale',
         'r.Shadow.Virtual.MaxPhysicalPages','r.TSR.History.ScreenPercentage',
         'r.VolumetricCloud','r.LumenScene.SurfaceCache.CardCaptureFactor',
         'gt.Spray.SparseUpdates']}
    cameras={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor)}
    sheets=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTWaterSheet) if a.get_editor_property('water_domain')]
    assert len(sheets)==1, 'Expected one moving water domain'
    # Domain references survive MID creation and material renames. Hiding the sheet
    # includes its local procedural mesh but leaves the simulation ticking.
    water=[sheets[0],*sheets[0].get_editor_property('domain_surfaces')]
    assert len(water)==4 and all(water), 'Expected local mesh plus three authored water surfaces'
    water_visibility=[(a,a.get_editor_property('hidden')) for a in water]
    report['water_actors']=[a.get_actor_label() for a in water]
    # Custom composition ISM/HISMs are not reliably isolated by InstancedFoliage.
    vegetation=[]
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for component in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh=component.static_mesh
            if mesh and not isinstance(component,u.GrassInstancedStaticMeshComponent) and any(
                token in mesh.get_path_name().lower() for token in ('tussock','willow','shrub','scrub','grass')):
                vegetation.append((component,component.is_visible()))
    assert vegetation, 'No authored vegetation components identified'
    report['vegetation_components']=[c.get_path_name() for c,_ in vegetation]
    try:report['foliage_inventory']=foliage_inventory([c for c,_ in vegetation])
    except Exception:report['foliage_inventory_error']=traceback.format_exc()
    groups={category:[(c,visible) for c,visible in vegetation
        if c.get_owner().get_actor_label().startswith('Benmore_Composition_'+category+'_')]
        for category in ['tussocks','shrubs']}
    shrub_shadows=[(c,c.get_editor_property('cast_shadow')) for c,_ in groups['shrubs']]
    available={'water':None,'landscape_grass':'ShowFlag.InstancedGrass',
        'vegetation_meshes':None,'shadows':'ShowFlag.DynamicShadows',
        'composition_tussocks':None,'composition_shrubs':None,'shrub_shadows':None,
        'lumen_gi':'r.Lumen.DiffuseIndirect.Allow',
        'lumen_reflections':'r.Lumen.Reflections.Allow','clouds':'r.VolumetricCloud'}
    selected=OPTIONS.get('features',['water','landscape_grass','vegetation_meshes','shadows'])
    features={name:available[name] for name in selected} if MODE=='Isolation' else {'baseline':None}
    original_flags={flag:u.SystemLibrary.get_console_variable_int_value(flag)
        for flag in features.values() if flag}
    report['original_cvar_overrides']=original_flags
    restore_cvars.update(original_flags)
    report['diagnostic_only']=('One reversible candidate per ABBA block; stationary results require driving and visual validation. Deltas are not additive.'
        if MODE=='Candidate' else 'Disabling a feature measures a dependency-inclusive delta; it is not a proposed visual preset. Deltas are not additive.')
    report['cameras']={}
    for view in VIEWS:
        assert 'Benmore_RL_Camera_'+view in cameras, 'Missing required camera: '+view
        camera=cameras['Benmore_RL_Camera_'+view]
        report['cameras'][view]={'position_cm':list(camera.get_actor_location().to_tuple()),
            'rotation':list(camera.get_actor_rotation().to_tuple()),'fov':camera.camera_component.field_of_view}
        pawn=u.GameplayStatics.get_player_pawn(world,0)
        if pawn:pawn.set_actor_location(camera.get_actor_location(),False,True)
        # Sustained laptop clocks, not a cold boost peak, are the reference.
        pc.set_view_target_with_blend(cameras['Benmore_RL_Camera_'+view],0);yield 240 if not report['runs'] else 20
        if MODE=='Baseline':
            console('HighResShot 1440x902 filename="'+(OUT/('baseline_'+view+'.png')).as_posix()+'"')
            yield 10
        if MODE=='Candidate':
            report['cameras'][view]['candidate_bindings']=candidate_stage.bind(world,pc)
            for iteration,active in enumerate([False,True,True,False]):
                candidate_stage.apply(active)
                yield 20
                # Material/LOD changes can trigger PSO work after binding. Wait
                # outside timings and reject compilation during the sample.
                previous=shader_cpu();idle=0
                for attempt in range(100):
                    yield 3
                    current=shader_cpu();idle=idle+3 if abs(current-previous)<.1 else 0;previous=current
                    if idle>=9:break
                assert idle>=9, 'Candidate shaders did not settle'
                if iteration in (0,1):
                    name=OPTIONS['stage']+'_'+view+('_candidate' if active else '_reference')
                    console('HighResShot 960x600 filename="'+(OUT/(name+'.png')).as_posix()+'"')
                    yield 10
                readiness=candidate_stage.verify_ready()
                assert list(pc.get_viewport_size())==report['resolution'], 'Viewport changed during capture'
                shader_before=shader_cpu()
                # Process inspection blocks this Slate frame. Let it finish
                # before starting CSV; retain every frame inside the capture.
                yield 2
                before=files();console('csvprofile start');yield CAPTURE_SECONDS;console('csvprofile stop');yield 4
                assert abs(shader_cpu()-shader_before)<.1, 'Shader compilation during candidate capture'
                candidate_stage.verify_ready()
                new=files()-before;assert len(new)==1, 'CSV capture ambiguous'
                path=new.pop();archived=OUT/path.name;shutil.copy2(path,archived)
                metrics=analyse(path)
                report['runs'].append({'view':view,'feature':OPTIONS['stage'],
                    'disabled':active,'candidate_active':active,'iteration':iteration,
                    'csv':str(archived),'analysis':metrics,'readiness':readiness})
                (OUT/'profile-progress.json').write_text(json.dumps(report,indent=2))
                memory=metrics['local_memory']
                assert memory is not None, 'Missing GPU memory telemetry'
                report['runs'][-1]['memory_telemetry_complete']=memory['unavailable_frames']==0
                assert memory['over_budget_frames']==0, 'GPU over budget; candidate timing invalid'
            candidate_stage.restore()
            continue
        if MODE=='Memory':
            # Allocation diagnostics only; commands can stall and are never
            # issued inside timed windows. Residency is measured by CSV/DXGI.
            console('rhi.DumpMemory')
            console('rhi.DumpResourceMemory 80')
            console('ListTextures')
            yield 5
            report['memory_dump_log']=str(OUT/'editor.log')
            probe=OPTIONS.get('memory_probe','shadow_pool')
            flag,candidate={'shadow_pool':('r.Shadow.Virtual.MaxPhysicalPages',2048),
                'nanite_pool':('r.Nanite.Streaming.StreamingPoolSize',128),
                'tsr_history':('r.TSR.History.ScreenPercentage',100),
                'lumen_hardware_raytracing':('r.Lumen.HardwareRayTracing',0)}[probe]
            original=u.SystemLibrary.get_console_variable_int_value(flag)
            # A config trial may already load the candidate. An explicit reference
            # allows comparison with the recorded pre-trial setting; always restore
            # the actually loaded value rather than the comparison reference.
            reference=int(OPTIONS.get('memory_reference',0)) or original
            assert reference>candidate, 'Reference is already at or below this candidate; no reduction to test'
            restore_cvars[flag]=original
            report['memory_probe']={'feature':probe,'cvar':flag,'loaded_value':original,
                'baseline':reference,'candidate':candidate}
            report['memory_probe_note']='ABBA memory diagnostic; budget pressure is retained as evidence, not a clean performance certification.'
            # UE 5.8 emits VSM/FreePages through this CSV category. Keep the
            # instrumentation identical in all four samples; no overlay in timings.
            if probe=='shadow_pool':console('csvcategory VSM enable')
            if probe=='nanite_pool':
                assert u.SystemLibrary.get_console_variable_int_value('r.Nanite.Streaming.Debug.StreamingPoolResize')==1, 'Runtime Nanite pool resize is disabled'
                console('csvcategory NaniteStreamingDetail enable')
            for iteration,value in enumerate([reference,candidate,candidate,reference]):
                console(flag+' '+str(value));yield 20
                assert u.SystemLibrary.get_console_variable_int_value(flag)==value
                if iteration in (0,1):
                    u.log('BENMORE_MEMORY_STATE '+probe+' '+str(value))
                    console('rhi.DumpResourceMemory 80')
                    console('HighResShot 960x600 filename="'+(OUT/(probe+'_'+str(value)+'.png')).as_posix()+'"')
                    yield 10
                assert list(pc.get_viewport_size())==report['resolution'], 'Viewport changed during capture'
                before=files();console('csvprofile start');yield CAPTURE_SECONDS;console('csvprofile stop');yield 4
                new=files()-before;assert len(new)==1, 'CSV capture ambiguous'
                path=new.pop();archived=OUT/path.name;shutil.copy2(path,archived)
                metrics=analyse(path)
                assert metrics['local_memory'] is not None, 'Missing GPU memory budget telemetry'
                report['runs'].append({'view':view,'feature':probe,'disabled':value==candidate,
                    'candidate_active':value==candidate,'cvar_value':value,
                    'iteration':iteration,'csv':str(archived),'analysis':metrics})
                (OUT/'profile-progress.json').write_text(json.dumps(report,indent=2))
                if probe=='shadow_pool':
                    pages=metrics['metrics'].get('VSM/FreePages')
                    assert pages is not None, 'Missing VSM occupancy counters; cannot validate pool capacity'
                    assert pages['min']>=0, 'VSM page pool overflow; candidate rejected'
                if probe=='nanite_pool':
                    size=metrics['metrics'].get('NaniteStreamingDetail/StreamingPoolSizeMB')
                    visible=metrics['metrics'].get('NaniteStreamingDetail/VisibleStreamingDataSizeMB')
                    assert size and visible, 'Missing Nanite pool telemetry'
                    assert size['min']==value and size['max']==value, 'Nanite pool did not resize'
                    assert visible['max']<value*.8, 'Insufficient visible Nanite streaming headroom'
            report.setdefault('memory_candidate_gates',[]).append({'view':view,
                'feature':probe,'headroom_passed':all(row['analysis']['local_memory']['below_proposed_headroom_frames']==0
                    and row['analysis']['local_memory']['unavailable_frames']==0
                    for row in report['runs'] if row['view']==view and row['feature']==probe and row['candidate_active']),
                'visual_review_required':True,'promotion_ready':False})
            continue
        grass=[c for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
            for c in a.get_components_by_class(u.GrassInstancedStaticMeshComponent)]
        try:report['cameras'][view]['landscape_grass_inventory']=foliage_inventory(grass)
        except Exception:report['cameras'][view]['landscape_grass_inventory_error']=traceback.format_exc()
        for feature,flag in features.items():
            if flag and original_flags[flag]==0:
                report.setdefault('skipped_features',[]).append({'view':view,'feature':feature,'reason':'Already disabled in baseline'})
                continue
            for iteration,off in enumerate([False]*REPEATS if MODE=='Baseline' else [False,True,True,False]):
                if flag:console(flag+' '+('0' if off else str(original_flags[flag])))
                elif feature=='water':
                    for a,was_hidden in water_visibility:a.set_actor_hidden_in_game(off or was_hidden)
                    assert all(a.get_editor_property('hidden')==(off or was_hidden) for a,was_hidden in water_visibility)
                elif feature=='vegetation_meshes':
                    for component,was_visible in vegetation:component.set_visibility(was_visible and not off)
                    assert all(c.is_visible()==(visible and not off) for c,visible in vegetation)
                elif feature.startswith('composition_'):
                    group=groups[feature.removeprefix('composition_')]
                    assert group, 'Missing composition group: '+feature
                    for c,visible in group:c.set_visibility(visible and not off)
                    assert all(c.is_visible()==(visible and not off) for c,visible in group)
                elif feature=='shrub_shadows':
                    assert any(cast for _,cast in shrub_shadows), 'No shrub shadows to isolate'
                    for c,cast in shrub_shadows:c.set_cast_shadow(cast and not off)
                    assert all(c.get_editor_property('cast_shadow')==(cast and not off) for c,cast in shrub_shadows)
                yield 10
                assert list(pc.get_viewport_size())==report['resolution'], 'Viewport changed during capture'
                if flag:assert u.SystemLibrary.get_console_variable_int_value(flag)==(0 if off else original_flags[flag])
                before=files();console('csvprofile start');yield CAPTURE_SECONDS;console('csvprofile stop');yield 4
                new=files()-before;assert len(new)==1, 'CSV capture ambiguous'
                path=new.pop();metrics=analyse(path)
                archived=OUT/path.name;shutil.copy2(path,archived)
                report['runs'].append({'view':view,'feature':feature,'disabled':off,'iteration':iteration,'csv':str(archived),'analysis':metrics})
                (OUT/'profile-progress.json').write_text(json.dumps(report,indent=2))
                memory=metrics['local_memory']
                assert memory is not None, 'Missing GPU memory budget telemetry'
                assert memory['unavailable_frames']==0, 'Incomplete GPU memory budget telemetry; baseline not certified'
                assert memory['over_budget_frames']==0, 'Local GPU memory budget exceeded; run invalid'
    report['isolation_comparisons']=compare_isolation(report['runs'])
    report['memory_telemetry_complete']=all(row['analysis']['local_memory']['unavailable_frames']==0 for row in report['runs'])
    report['ok']=True

def finish(error=None):
    global gen
    gen=None
    if error:report['error']=error;report['ok']=False;u.log_error(error)
    if (OUT/'external-load-invalid.json').exists():report['ok']=False;report['error']='Another game/process started during profiling; results invalid.'
    if candidate_stage and candidate_stage.world is not None:
        try:
            candidate_stage.restore()
            report['candidate_restored']=True
        except Exception:
            report['ok']=False;report['candidate_restore_error']=traceback.format_exc()
    if world:
        try:
            for flag,value in restore_cvars.items():console(flag+' '+str(value))
            report['restored_cvars']={flag:u.SystemLibrary.get_console_variable_int_value(flag) for flag in restore_cvars}
            assert report['restored_cvars']==restore_cvars, 'Runtime CVar restoration failed'
        except Exception:
            report['ok']=False;report['restore_error']=traceback.format_exc()
    if report.get('editor_viewport_realtime_override_requested'):
        try:
            # UE removes only this subsystem's override, preserving the user's
            # underlying realtime preference (LevelEditorSubsystem.cpp).
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_set_viewport_realtime(True)
            report['editor_viewport_realtime_override_removed']=True
        except Exception:
            report['ok']=False;report['viewport_restore_error']=traceback.format_exc()
    (OUT/'profile-report.json').write_text(json.dumps(report,indent=2))
    if world:console('csvprofile stop')
    u.unregister_slate_post_tick_callback(handle);u.EditorLevelLibrary.editor_end_play();u.SystemLibrary.quit_editor()

gen=main();next_at=time.monotonic();started=next_at;busy=False
def tick(dt):
    global next_at,busy
    # Level loading and reflected editor calls can pump Slate recursively.
    if busy or gen is None:return
    busy=True
    try:
        if (OUT/'external-load-invalid.json').exists():raise RuntimeError('External GPU workload detected; profile invalid')
        if time.monotonic()-started>4500:raise RuntimeError('Bounded profiler timeout')
        if time.monotonic()<next_at:return
        next_at=time.monotonic()+next(gen)
    except StopIteration:finish()
    except Exception:finish(traceback.format_exc())
    finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
