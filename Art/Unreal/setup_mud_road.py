"""Create a separate winding road using the accepted MudLab terrain/shader system."""
import sys,json,time,traceback,hashlib,shutil,math,random
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path[:0]=[str(ROOT/'Art/Unreal'),str(ROOT/'Art/tools')]
from benmore_river_life_materials import props
from make_mud_road import centre,heading
BASE='/Game/GrandTour/ArtTests/MudRoad';LEVEL=BASE+'/L_MudRoad'
SOURCE='/Game/GrandTour/ArtTests/MudLab/L_MudLab';LAB='/Game/GrandTour/ArtTests/MudLab'
OUT=ROOT/'Art/Export/MudRoad';OUT.mkdir(parents=True,exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
report=dict(ok=False,level=LEVEL)
baseline=list((ROOT/'Content/GrandTour/ArtTests/MudLab').rglob('*'))
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline if p.is_file()}
try:
    target=ROOT/'Content/GrandTour/ArtTests/MudRoad'
    if target.exists():shutil.copytree(target,ROOT/'Saved/MudRoadBackups'/str(time.time_ns()))
    # Regenerate the dedicated map from the immutable lab; backups preserve any previous version.
    assert les.load_level(SOURCE)
    assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
    assert les.load_level(LEVEL)
    def texture(filename,name):
        task=props(u.AssetImportTask(),filename=str(OUT/filename),destination_path=BASE,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);t=assets.load_asset(BASE+'/'+name)
        props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True)
        assert assets.save_loaded_asset(t);return t
    paint=texture('soil-paint.png','T_RoadPaint');rest=texture('world-rest.png','T_RoadRest')
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    s.paint_origin_cm=u.Vector2D(-3150,-3150);s.paint_size_cm=6300
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,paint)
    assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(s,rest)
    s.set_actor_label('MudRoad_Surface');s.enable_wheel_support=True;s.observe_player_wheels=True;s.follow_player=True
    s.use_soil_shear_response=True;s.use_rut_interaction=True;s.use_native_mud_shader_updates=True
    s.mud_regions=[props(u.GTLandscapeMudRegion(),name='Winding forest road',centre=u.Vector2D(),half_size=u.Vector2D(3150,3150),wetness=.88,cohesion=.52,relief=1.,fragment_scale=1.)]
    def material(name):
        m=assets.load_asset(BASE+'/'+name) or assets.duplicate_asset(LAB+'/'+name,BASE+'/'+name);assert m
        for e in mel.get_material_expressions(m):
            if isinstance(e,u.MaterialExpressionTextureObjectParameter):
                key=str(e.get_editor_property('parameter_name'))
                if key=='GTLS_Paint':e.set_editor_property('texture',paint)
                if key=='GTLS_Rest':e.set_editor_property('texture',rest)
            if isinstance(e,u.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='GTLS_PaintWindow':
                e.set_editor_property('default_value',u.LinearColor(-3150,-3150,6300,0))
        assert not mel.recompile_material(m)
        assert assets.save_loaded_asset(m);return m
    ground=material('M_LabSoil');water=material('M_LabWater')
    sim=material('M_LabWaterSim');sediment=material('M_LabWaterSediment')
    visual=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTMudRunnerVisual))
    visual.set_actor_label('MudRoad_NativeVisualGrid');visual.surface=s;visual.material=ground
    s.landscape.landscape_material=ground
    for c in s.landscape.get_components_by_class(u.MeshComponent):
        for i in range(c.get_num_materials()):c.set_material(i,ground)
    sheet=s.simulated_water;assert sheet
    sheet.set_actor_label('MudRoad_Puddles');sheet.set_editor_property('mud_surface',s)
    sheet.set_actor_location(u.Vector(),False,False)
    props(sheet,base_level_cm=-26*50/255,surface_material_path=BASE+'/M_LabWater',mud_half_size_cm=3150.,mud_cell_cm=50.)
    visual.water_sheet=sheet;visual.water_simulation_material=sim;visual.sediment_simulation_material=sediment
    visual.wave_material=assets.load_asset(LAB+'/M_LabWaves')
    for a in list(actors.get_all_level_actors()):
        if isinstance(a,(u.PlayerStart,u.GTCarPawn,u.GTMudDetailStudy,u.GTMudRoute,u.TextRenderActor)) or a.get_actor_label().startswith(('MudLab_Sign','MudRoad_Dressing')):
            actors.destroy_actor(a)
    # Re-use the established forest assets. Move existing trees clear of the winding road.
    rng=random.Random(9017);counts={}
    for a in actors.get_all_level_actors():
        label=a.get_actor_label()
        if not label.startswith('MudScene_Detail_'):continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            for i in reversed(range(c.get_instance_count())):
                t=c.get_instance_transform(i,True);p=t.translation
                margin=760 if 'trees' in label else 430
                if abs(p.y-centre(p.x))<margin:c.remove_instance(i)
            counts[label]=counts.get(label,0)+c.get_instance_count()
    # Add a continuous verge using existing grass meshes, with open sight lines at the bends.
    a=actors.spawn_actor_from_class(u.Actor,u.Vector());a.set_actor_label('MudRoad_Dressing_Verge')
    grass=material('M_LabGrass')
    for kind in ['Straw','Rust','Fine']:
        mesh=assets.load_asset('/Game/GrandTour/ArtTests/TussockStyle/SM_TS_'+kind);b=mesh.get_bounds();ts=[]
        for _ in range(470):
            x=rng.uniform(-2850,2850);y=centre(x)+rng.choice([-1,1])*rng.uniform(340,1100)
            sc=rng.uniform(25,55)/(2*b.box_extent.z)
            ts.append(u.Transform(location=u.Vector(x,y,-(b.origin.z-b.box_extent.z)*sc-3),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)))
        c=u.GTVegetationSubsystem.add_tagged_instances(a,mesh,ts,'MudRoad','NoCollision',False)
        if grass:c.set_material(0,grass)
        c.set_cast_shadow(False);c.set_cull_distances(10000,18000)
    # Forest frame beyond the shoulders; existing tree meshes and materials, no new detail assets.
    trees=[a for a in actors.get_all_level_actors() if a.get_actor_label()=='MudScene_Detail_trees']
    if trees:
        comps=trees[0].get_components_by_class(u.InstancedStaticMeshComponent)
        for k,x in enumerate(range(-2750,2800,360)):
            for side in [-1,1]:
                c=comps[k%len(comps)];mesh=c.static_mesh;b=mesh.get_bounds();sc=rng.uniform(800,1150)/(2*b.box_extent.z)
                y=centre(x)+side*rng.uniform(850,1550)
                c.add_instance(u.Transform(location=u.Vector(x,y,-(b.origin.z-b.box_extent.z)*sc-10),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)),True)
    data=json.loads((OUT/'authoring.json').read_text());points=data['recovery']
    route=actors.spawn_actor_from_class(u.GTMudRoute,u.Vector());route.set_actor_label('MudRoad_RecoveryPoints')
    route.set_editor_property('title','MUD ROAD / winding forest track')
    route.set_editor_property('checkpoint_labels','1 Start   2 Broken puddles   3 Flooded dip')
    route.set_editor_property('recovery_points',[u.Transform(location=u.Vector(p['x'],p['y'],p['z']),rotation=u.Rotator(yaw=p['yaw'])) for p in points])
    p=points[0];start=actors.spawn_actor_from_class(u.PlayerStart,u.Vector(p['x'],p['y'],120),u.Rotator(yaw=p['yaw']));start.set_actor_label('MudRoad_Start')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',u.GTMudLabGameMode)
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-3200,-3400,3300),u.MathLibrary.find_look_at_rotation(u.Vector(-3200,-3400,3300),u.Vector()))
    assert les.save_current_level()
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items()),'MudLab changed'
    report.update(ok=True,source_assets_unchanged=True,route_length_m=data['route_length_m'],wet_area_m2=data['wet_area_m2'],surface=s.get_surface_report(),dressing=counts)
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
s=sheet=world=ground=water=paint=rest=visual=sim=sediment=route=None
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage()
quit_at=time.monotonic()+3
def finish(dt):
    if time.monotonic()>=quit_at:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
