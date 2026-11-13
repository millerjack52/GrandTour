"""Isolated drivable sand comparison; original mud maps/assets are protected."""
import sys,json,time,shutil,traceback,hashlib,gc
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
import sand_terrain_material as materials
BASE=materials.BASE;LEVEL=BASE+'/L_SandTerrain';OUT=ROOT/'Art/Export/SandTerrain'
e=u.EditorAssetLibrary;les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
report=dict(ok=False,level=LEVEL)
report['rotator_api']=u.Rotator.__doc__
try:
    originals=[ROOT/'Content/GrandTour/ArtTests/RutInteraction/L_RutInteraction.umap',ROOT/'Content/GrandTour/ArtTests/MudProvingGround/M_ProvingSoil.uasset']
    before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
    folder=ROOT/'Content/GrandTour/ArtTests/SandTerrain'
    if folder.exists():shutil.copytree(folder,ROOT/'Saved/SandTerrain'/str(time.time_ns()))
    if not e.does_asset_exist(LEVEL):
        assert les.load_level('/Game/GrandTour/ArtTests/RutInteraction/L_RutInteraction')
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        assert u.EditorLoadingAndSavingUtils.save_map(world,LEVEL)
    world=None;assert les.load_level(LEVEL)
    def texture(file,name):
        t=props(u.AssetImportTask(),filename=str(OUT/file),destination_path=BASE,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);return e.load_asset(BASE+'/'+name)
    paint=texture('sand-paint.png','T_SandPaint');rest=texture('sand-rest.png','T_SandRest')
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface));land=s.landscape
    report['mesh_inventory']=[dict(label=a.get_actor_label(),type=a.get_class().get_name(),materials=[str(c.get_material(i).get_path_name()) for c in a.get_components_by_class(u.MeshComponent) for i in range(c.get_num_materials()) if c.get_material(i)]) for a in actors.get_all_level_actors()]
    s.set_editor_property('simulated_water',None);s.puddle_surface=None
    for a in list(actors.get_all_level_actors()):
        water_mesh=isinstance(a,u.StaticMeshActor) and any('water' in c.get_material(i).get_path_name().lower() or 'puddle' in c.get_material(i).get_path_name().lower() for c in a.get_components_by_class(u.MeshComponent) for i in range(c.get_num_materials()) if c.get_material(i))
        if water_mesh or a.get_actor_label()=='MudScene_Detail_trees' or isinstance(a,(u.GTWaterSheet,u.GTVehicleSurfaceEffects,u.GTDustLab)):actors.destroy_actor(a)
        elif a.get_actor_label().startswith('MudScene_Detail_'):
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                for i in reversed(range(c.get_instance_count())):
                    p=c.get_instance_transform(i,True).translation
                    if abs(p.x)<1500 and abs(p.y)<870:c.remove_instance(i)
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,paint)
    assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(s,rest)
    # Import helpers change numeric texture formats after AssetImportTask saves.
    # Persist those settings so a fresh editor reads the same field as the CPU.
    assert e.save_loaded_asset(paint);assert e.save_loaded_asset(rest)
    s.use_soil_shear_response=True;s.use_rut_interaction=True;s.use_granular_response=True
    s.set_editor_property('layer_depth_scale',1.);s.set_editor_property('bearing_strength',1.05);s.set_editor_property('settlement_speed_scale',1.1)
    s.enable_wheel_support=True;s.observe_player_wheels=True;s.follow_player=True;s.tyre_coating_material=None
    s.mud_regions=[props(u.GTLandscapeMudRegion(),name='Dry_granular_sand',centre=u.Vector2D(),half_size=u.Vector2D(1575,1575),wetness=.02,cohesion=.04,relief=1.,fragment_scale=1.)]
    s.set_actor_label('Sand_LooseAndCompacted')
    mat=materials.make(paint,rest)
    pm=e.load_asset(BASE+'/PM_Sand') or e.duplicate_asset('/Game/GrandTour/Terrain/Surfaces/PM_Dirt',BASE+'/PM_Sand')
    tag=u.GameplayTag();assert tag.import_text('(TagName="Surface.Sand")');pm.set_editor_property('surface_tag',tag)
    pm.set_editor_property('sinkage_rate',0.);assert e.save_loaded_asset(pm)
    mat.set_editor_property('phys_material',pm);assert e.save_loaded_asset(mat)
    land.landscape_material=mat;land.set_editor_property('default_phys_material',pm)
    for c in land.get_components_by_class(u.LandscapeNaniteComponent):
        for i in range(c.get_num_materials()):c.set_material(i,mat)
    land.set_editor_property('collision_mip_level',land.get_editor_property('collision_mip_level'))
    manager=actors.spawn_actor_from_class(u.GTVehicleSurfaceEffects,u.Vector())
    manager.set_actor_label('Sand_DryDust');manager.dust_system=e.load_asset('/Game/GrandTour/FX/VehicleSurface/Benmore_20261012_162504/NS_DryDust');assert manager.dust_system
    manager.mud_system=None;manager.dust_intensity=1.2
    # Start aligned with the loose lane; the packed lane lies to its left (+Y).
    for a in actors.get_all_level_actors():
        if isinstance(a,u.GTCarPawn):a.set_actor_location_and_rotation(u.Vector(-1050,-280,135),u.Rotator(),False,True)
        if isinstance(a,u.PlayerStart):a.set_actor_location_and_rotation(u.Vector(-1050,-280,160),u.Rotator(),False,True)
        if a.get_actor_label()=='MudScene_Sun':
            a.set_actor_rotation(u.Rotator(pitch=-38,yaw=130,roll=0),False);a.light_component.set_editor_property('intensity',3.5)
            a.light_component.set_editor_property('light_source_angle',1.2)
        if isinstance(a,u.SkyLight):a.light_component.set_editor_property('intensity',3.)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-1450,-1400,780),u.Rotator(-24,38,0))
    assert les.save_current_level()
    assert before=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in originals}
    report.update(ok=True,baseline_unchanged=True,loose_lane_y=-280,packed_lane_y=350,material=mat.get_path_name(),surface=pm.surface_tag.export_text())
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
s=land=world=a=c=manager=mat=pm=paint=rest=tag=p=None;les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage();end=time.monotonic()+5
def finish(dt):
    global actors,les,e,handle
    if time.monotonic()>=end:
        u.unregister_slate_post_tick_callback(handle);handle=None
        actors=les=e=None;gc.collect();u.SystemLibrary.collect_garbage()
        # Let ExecutePythonScript finish its notification and defer shutdown itself.
        u.EditorPythonScripting.set_keep_python_script_alive(False)
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
