"""Isolated first slice. Previous scenes are unapproved comparisons, never source assets to modify."""
import sys,json,time,traceback,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import mud_proving_materials as materials
BASE=materials.BASE;LEVEL=BASE+'/L_MudProvingGround';OUT=ROOT/'Art/Export/MudProvingGround'
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem);assets=u.EditorAssetLibrary
report={'ok':False,'level':LEVEL,'acceptance':'unapproved prototype; rendered review and handling revision required'}
try:
    target=ROOT/'Content/GrandTour/ArtTests/MudProvingGround'
    if target.exists():
        backup=ROOT/'Saved/MudProvingGround'/str(time.time_ns());shutil.copytree(target,backup);report['backup']=str(backup)
    if assets.does_asset_exist(LEVEL):assert les.load_level(LEVEL)
    else:
        assert les.load_level('/Game/GrandTour/ArtTests/MudResponse/L_MudResponse')
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
    def texture(filename,name):
        task=props(u.AssetImportTask(),filename=str(OUT/filename),destination_path=BASE,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);return assets.load_asset(BASE+'/'+name)
    paint=texture('soil-paint.png','T_ProvingPaint');rest=texture('world-rest.png','T_ProvingRest')
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface));land=s.landscape
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,paint)
    assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(s,rest)
    mat,watermat=materials.make(paint,rest)
    s.tyre_coating_material=materials.tyre()
    land.landscape_material=mat
    s.enable_wheel_support=True;s.follow_player=True;s.observe_player_wheels=True
    s.use_soil_shear_response=True
    s.set_editor_property('layer_depth_scale',1.)
    s.set_editor_property('bearing_strength',1.)
    s.set_editor_property('settlement_speed_scale',1.)
    s.set_actor_label('ProvingGround_Surface')
    s.mud_regions=[props(u.GTLandscapeMudRegion(),name='Saturated_prototype',centre=u.Vector2D(),half_size=u.Vector2D(1575,1575),wetness=.9,cohesion=.68,relief=1.,fragment_scale=1.2)]
    for a in list(actors.get_all_level_actors()):
        if isinstance(a,u.GTMudDetailStudy):actors.destroy_actor(a)
        if a.get_actor_label()=='ProvingGround_ConnectedWater':actors.destroy_actor(a)
        # Clear dressing from the broader contact patch, retaining the surroundings.
        if a.get_actor_label().startswith('MudScene_Detail_'):
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                # Dense non-Nanite grass can overflow VSM marking queues.
                # Keep tree/shrub/vehicle shadows; this low cover uses ambient contact shading.
                if a.get_actor_label()=='MudScene_Detail_grass':c.set_cast_shadow(False)
                for i in reversed(range(c.get_instance_count())):
                    p=c.get_instance_transform(i,True).translation
                    if abs(p.x)<1450 and abs(p.y)<600:c.remove_instance(i)
    pool=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,-4.509804))
    pool.set_actor_label('ProvingGround_ConnectedWater');pool.set_actor_scale3d(u.Vector(31.5,31.5,1))
    c=pool.static_mesh_component;c.set_static_mesh(assets.load_asset('/Engine/BasicShapes/Plane'))
    c.set_material(0,watermat);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);c.set_cast_shadow(False)
    s.puddle_surface=pool
    for a in actors.get_all_level_actors():
        if isinstance(a,u.DirectionalLight):a.light_component.set_editor_property('forward_shading_priority',1 if a.get_actor_label()=='MudScene_Sun' else 0)
    for asset in [paint,rest,mat,watermat]:assert assets.save_loaded_asset(asset)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-1000,-800,550),u.Rotator(-22,30,0))
    assert les.save_current_level()
    # Standalone comparisons preserve the owner's liked baseline and its geometry.
    # Thickness and strength are independent controls, not terrain amplitude or speed multipliers.
    report['soil_presets']=[]
    for name,depth,strength in [('Firm',.65,1.6),('DeepSoft',1.28,.6)]:
        variant=BASE+'/L_MudProvingGround_'+name
        if assets.does_asset_exist(variant):assert les.load_level(variant)
        else:
            assert les.load_level(LEVEL)
            world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            assert u.EditorLoadingAndSavingUtils.save_map(world,variant)
        v=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
        v.set_editor_property('layer_depth_scale',depth)
        v.set_editor_property('bearing_strength',strength)
        v.set_editor_property('settlement_speed_scale',1.)
        assert les.save_current_level()
        report['soil_presets'].append(dict(level=variant,layer_depth_scale=depth,bearing_strength=strength))
    report.update(ok=True,material=mat.get_path_name(),water=watermat.get_path_name(),world_height_import_succeeded=True)
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
# Release references to the duplicated worlds before engine shutdown.
s=land=pool=c=a=v=world=mat=watermat=paint=rest=None
les.load_level('/Engine/Maps/Entry')
u.SystemLibrary.collect_garbage()
quit_at=time.monotonic()+5
def finish_tick(dt):
    if time.monotonic()>=quit_at:
        u.unregister_slate_post_tick_callback(quit_handle)
        u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True)
quit_handle=u.register_slate_post_tick_callback(finish_tick)
