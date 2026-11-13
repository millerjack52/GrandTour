"""Repair the user's metre-high displacement failure; inspect the actual runtime at eye height.
Only the isolated prototype map/material are saved. No benchmark, Benmore edits or broad test suite.
"""
import json
import shutil
import sys
import time
import traceback
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir()).resolve()
sys.path.insert(0,str(ROOT/'Art/Unreal'))
from landscape_surface_material import COLOR,NORMAL,DISPLACEMENT,ROUGHNESS,SPECULAR,DEST
OUT=ROOT/'Art/Export/LandscapeSurface';OUT.mkdir(parents=True,exist_ok=True)
LEVEL=DEST+'/L_LandscapeSurfacePrototype'
MAPFILE=ROOT/'Content/GrandTour/ArtTests/LandscapeSurface/L_LandscapeSurfacePrototype.umap'
MATFILE=MAPFILE.parent/'M_LandscapeSurface.uasset'
report={'ok':False,'images':[],'performance_measured':False}
les=u.get_editor_subsystem(u.LevelEditorSubsystem)
mel=u.MaterialEditingLibrary
phase='load';last=time.monotonic();start=last;busy=False;index=0
world=pc=camera=surface=None
CAMERAS=[('foot',(-400,-400,160),(0,0,-5)),
         ('join',(250,-400,160),(250,100,0)),
         ('sun',(600,-350,160),(-350,200,5))]
CAPTURES=[('baseline','foot',[]),('foot','foot',[]),('join','join',[]),('sun','sun',[])]
if '-GTLSRenderDiagnostics' in u.SystemLibrary.get_command_line():
    CAPTURES += [('fresh_shadow_cache','foot',['r.Shadow.Virtual.Cache 0']),
                 ('no_dynamic_shadows','foot',['ShowFlag.DynamicShadows 0']),
                 ('restored_shadows','foot',['ShowFlag.DynamicShadows 1','r.Shadow.Virtual.Cache 1']),
                 ('unlit','foot',['viewmode unlit']),
                 ('software_lumen','foot',['viewmode lit','r.Lumen.HardwareRayTracing 0']),
                 ('nanite_triangles','foot',['r.Nanite.Visualize Triangles'])]


def finish(error=None):
    global phase,last,world,pc,camera,surface
    phase='ending';last=time.monotonic()
    if error:report['error']=error;u.log_error(error)
    (OUT/'repair-report.json').write_text(json.dumps(report,indent=2))
    world=pc=camera=surface=None
    u.EditorLevelLibrary.editor_end_play()


def repair():
    global map_stamp,material_stamp
    map_stamp=MAPFILE.stat().st_mtime_ns;material_stamp=MATFILE.stat().st_mtime_ns
    backup=ROOT/'Saved/LandscapeSurfaceRepair'/str(time.time_ns());backup.mkdir(parents=True)
    for path in (MAPFILE,MATFILE):shutil.copy2(path,backup/path.name)
    report['backup']=str(backup)
    assert les.load_level(LEVEL)
    ew=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    landscape=next(iter(u.GameplayStatics.get_all_actors_of_class(ew,u.Landscape)))
    oldscale=landscape.get_actor_scale3d()
    report['old_scale']=[oldscale.x,oldscale.y,oldscale.z]
    material=u.load_asset(DEST+'/M_LandscapeSurface');assert material
    ds=material.get_editor_property('displacement_scaling')
    report['old_magnitude_local']=ds.magnitude
    expressions=list(mel.get_material_expressions(material));displacement=None
    for e in expressions:
        if not isinstance(e,u.MaterialExpressionCustom):continue
        code=e.get_editor_property('code')
        if 'return saturate((h*Enabled+50)/65)' in code:e.set_editor_property('code',DISPLACEMENT);displacement=e
        elif 'float3 fine=' in code:e.set_editor_property('code',COLOR)
        elif 'float2 slope=' in code:e.set_editor_property('code',NORMAL)
        elif 'return clamp(lerp(.92' in code or 'GTLS_ROUGHNESS' in code:e.set_editor_property('code',ROUGHNESS)
        elif 'return lerp(.12,.08,pool)' in code or 'GTLS_SPECULAR' in code:e.set_editor_property('code',SPECULAR)
    assert displacement
    assert u.GTLandscapeSurfaceSetupLibrary.connect_displacement(material,displacement,0,50.)
    landscape.set_actor_scale3d(u.Vector(50,50,50))
    landscape.set_editor_property('shadow_cache_invalidation_behavior',u.ShadowCacheInvalidationBehavior.ALWAYS)
    report['new_scale']=[50,50,50]
    report['magnitude_local']=material.get_editor_property('displacement_scaling').magnitude
    report['intended_world_bounds_cm']=[-50,15]
    mel.recompile_material(material)
    assert MATFILE.stat().st_mtime_ns==material_stamp,'Material changed on disk since load'
    u.EditorAssetLibrary.save_loaded_asset(material)
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    for name,pos,target in CAMERAS:
        label='SurfaceReview_'+name
        c=next((a for a in actors.get_all_level_actors() if a.get_actor_label()==label),None)
        if c is None:c=actors.spawn_actor_from_class(u.CameraActor,u.Vector(*pos))
        c.set_actor_label(label)
        c.set_actor_location(u.Vector(*pos),False,False)
        c.set_actor_rotation(u.MathLibrary.find_look_at_rotation(u.Vector(*pos),u.Vector(*target)),False)
        c.camera_component.set_field_of_view(75.)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(*CAMERAS[0][1]),u.MathLibrary.find_look_at_rotation(u.Vector(*CAMERAS[0][1]),u.Vector(*CAMERAS[0][2])))


def tick_body(dt):
    global phase,last,index,world,pc,camera,surface,shot_time
    now=time.monotonic()
    if phase=='ending':
        # EndPIE is queued. Let its teardown finish before requesting editor shutdown.
        if now-last>3 and u.EditorLevelLibrary.get_game_world() is None:
            phase='done'
            u.unregister_slate_post_tick_callback(handle)
            u.SystemLibrary.quit_editor()
        return
    if now-start>420:finish('Repair/capture timed out');return
    if phase=='load':
        phase='repairing'
        repair();phase='save';last=time.monotonic()
    elif phase=='save' and now-last>8:
        assert MAPFILE.stat().st_mtime_ns==map_stamp,'Map changed on disk since load'
        assert les.save_current_level()
        phase='play';last=time.monotonic()
    elif phase=='play' and now-last>3:
        assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
        phase='warm';last=now
    elif phase=='warm' and now-last>12:
        world=u.EditorLevelLibrary.get_game_world()
        if world is None:return
        pc=u.GameplayStatics.get_player_controller(world,0)
        surface=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)))
        surface.set_editor_property('observe_player_wheels',False)
        surface.set_editor_property('follow_player',False)
        report['before']=surface.get_surface_report()
        assert 'displacement_scale_valid=1' in report['before'],report['before']
        landscape=next(iter(u.GameplayStatics.get_all_actors_of_class(world,u.Landscape)))
        report['nanite_components']=[dict(scale=[c.get_world_scale().x,c.get_world_scale().y,c.get_world_scale().z],materials=c.get_num_materials()) for c in landscape.get_components_by_class(u.LandscapeNaniteComponent)]
        report['hardware_lumen']=u.SystemLibrary.get_console_variable_int_value('r.Lumen.HardwareRayTracing')
        report['hardware_ao']=u.SystemLibrary.get_console_variable_int_value('r.Lumen.ScreenProbeGather.ShortRangeAO.HardwareRayTracing')
        report['virtual_shadow_cache']=u.SystemLibrary.get_console_variable_int_value('r.Shadow.Virtual.Cache')
        report['nanite_shadow_invalidation']=[str(c.get_editor_property('shadow_cache_invalidation_behavior')) for c in landscape.get_components_by_class(u.LandscapeNaniteComponent)]
        report['landscape_ray_geometry_visible']=[c.get_editor_property('visible_in_ray_tracing') for c in landscape.get_components_by_class(u.LandscapeComponent)]
        report['nanite_ray_geometry_visible']=[c.get_editor_property('visible_in_ray_tracing') for c in landscape.get_components_by_class(u.LandscapeNaniteComponent)]
        phase='aim';last=now
    elif phase=='aim':
        # Baseline first, then explicit repeat-pass/spin fixture on the same field.
        if index==1:surface.apply_review_tracks();report['after']=surface.get_surface_report()
        label,name,commands=CAPTURES[index]
        for command in commands:u.SystemLibrary.execute_console_command(world,command,pc)
        camera=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.CameraActor) if a.get_actor_label()=='SurfaceReview_'+name)
        pc.set_view_target_with_blend(camera,0.)
        phase='capture';last=now
    elif phase=='capture' and now-last>3:
        label=CAPTURES[index][0]
        path=OUT/('repair_'+label+'.png')
        report['images'].append(str(path));shot_time=time.time()
        u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',pc)
        phase='image_wait';last=now
    elif phase=='image_wait' and now-last>3:
        path=Path(report['images'][-1])
        if not path.exists() or path.stat().st_mtime<shot_time:return
        index+=1
        if index>=len(CAPTURES):report['ok']=True;finish();return
        phase='aim';last=now


def tick(dt):
    global busy
    if busy:return
    busy=True
    try:tick_body(dt)
    except Exception:finish(traceback.format_exc())
    finally:busy=False


u.EditorPythonScripting.set_keep_python_script_alive(True)
handle=u.register_slate_post_tick_callback(tick)
