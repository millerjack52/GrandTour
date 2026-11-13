"""Create an isolated playable map from the existing shared mud/water prototype."""
import sys,json,time,traceback,hashlib,shutil
from pathlib import Path
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from benmore_river_life_materials import props
BASE='/Game/GrandTour/ArtTests/MudLab';LEVEL=BASE+'/L_MudLab'
SOURCE='/Game/GrandTour/ArtTests/MudWater/L_MudWater'
OUT=ROOT/'Art/Export/MudLab';OUT.mkdir(parents=True,exist_ok=True)
les=u.get_editor_subsystem(u.LevelEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
report=dict(ok=False,level=LEVEL)
baseline=[p for folder in ['MudWater','MudProvingGround'] for p in (ROOT/'Content/GrandTour/ArtTests'/folder).glob('*') if p.is_file()]
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline}
try:
    target=ROOT/'Content/GrandTour/ArtTests/MudLab'
    if target.exists():shutil.copytree(target,ROOT/'Saved/MudLabBackups'/str(time.time_ns()))
    if not assets.does_asset_exist(LEVEL):
        assert les.load_level(SOURCE)
        assert u.EditorLoadingAndSavingUtils.save_map(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world(),LEVEL)
    assert les.load_level(LEVEL)
    def texture(filename,name):
        task=props(u.AssetImportTask(),filename=str(OUT/filename),destination_path=BASE,destination_name=name,automated=True,replace_existing=True,save=True)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);return assets.load_asset(BASE+'/'+name)
    paint=texture('soil-paint.png','T_LabPaint');rest=texture('world-rest.png','T_LabRest')
    s=next(a for a in actors.get_all_level_actors() if isinstance(a,u.GTLandscapeSurface))
    s.paint_origin_cm=u.Vector2D(-1575,-1575);s.paint_size_cm=3150
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(s,paint)
    assert u.GTLandscapeSurfaceSetupLibrary.import_world_rest_heights(s,rest)
    s.set_actor_label('MudLab_Surface');s.enable_wheel_support=True;s.observe_player_wheels=True;s.follow_player=True
    s.use_soil_shear_response=True;s.use_rut_interaction=True
    s.use_native_mud_shader_updates=True
    s.set_editor_property('bearing_strength',1.);s.set_editor_property('layer_depth_scale',1.)
    s.mud_regions=[props(u.GTLandscapeMudRegion(),name=n,centre=u.Vector2D(200,y),half_size=u.Vector2D(1375,380),wetness=w,cohesion=c,relief=1.,fragment_scale=1.)
        for n,y,w,c in [('Firm soil',-850,.25,.85),('Soft mud',0,.88,.42),('Standing water',850,1.,.4)]]
    def material(source,name):
        m=assets.load_asset(BASE+'/'+name) or assets.duplicate_asset(source,BASE+'/'+name)
        assert m
        for e in mel.get_material_expressions(m):
            if isinstance(e,u.MaterialExpressionTextureObjectParameter):
                key=str(e.get_editor_property('parameter_name'))
                if key=='GTLS_Paint':e.set_editor_property('texture',paint)
                if key=='GTLS_Rest':e.set_editor_property('texture',rest)
            if isinstance(e,u.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name')) in ['GTLS_WaterLevel','FieldLevelCm']:
                e.set_editor_property('default_value',-26*50/255)
            if isinstance(e,u.MaterialExpressionCustom):
                code=e.get_editor_property('code')
                code=code.replace('float wet=mud*lerp(.62,1.,1-smoothstep(WaterLevel,WaterLevel+5,height));',
                    'float wet=mud*saturate(paint.a*.7+.3*(1-smoothstep(WaterLevel,WaterLevel+5,height)));')
                e.set_editor_property('code',code)
        if name!='M_LabWater':mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE)
        errors=mel.recompile_material(m);assert not errors,str(errors)
        assert assets.save_loaded_asset(m);return m
    from mudrunner_lab_materials import make
    ground,water=make(paint,rest)
    for old in list(actors.get_all_level_actors()):
        if isinstance(old,u.GTMudRunnerVisual):actors.destroy_actor(old)
    visual=actors.spawn_actor_from_class(u.GTMudRunnerVisual,u.Vector())
    visual.set_actor_label('MudLab_NativeVisualGrid');visual.surface=s;visual.material=ground
    s.landscape.landscape_material=ground
    for c in s.landscape.get_components_by_class(u.MeshComponent):
        for i in range(c.get_num_materials()):c.set_material(i,ground)
    sheet=s.simulated_water;assert sheet
    sheet.set_actor_label('MudLab_Pond');sheet.set_editor_property('mud_surface',s)
    sheet.set_editor_property('base_level_cm',-26*50/255)
    sheet.set_editor_property('surface_material_path',BASE+'/M_LabWater')
    sheet.set_editor_property('mud_cell_cm',25.)
    visual.water_sheet=sheet
    visual.water_simulation_material=assets.load_asset(BASE+'/M_LabWaterSim')
    visual.sediment_simulation_material=assets.load_asset(BASE+'/M_LabWaterSediment')
    visual.wave_material=assets.load_asset(BASE+'/M_LabWaves')
    # Clear dressing and any serialized vehicles only in this copy. The lab supplies its own pawn.
    for a in list(actors.get_all_level_actors()):
        label=a.get_actor_label()
        if isinstance(a,(u.PlayerStart,u.GTCarPawn,u.GTMudDetailStudy)) or label.startswith('MudLab_Sign'):
            actors.destroy_actor(a)
        elif label.startswith('MudScene_Detail_'):
            for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
                c.set_cast_shadow(False)
                for i in reversed(range(c.get_instance_count())):
                    p=c.get_instance_transform(i,True).translation
                    # Include the chase camera's run-up and overhanging tree crowns.
                    if abs(p.x)<3000 and abs(p.y)<2100:c.remove_instance(i)
    start=actors.spawn_actor_from_class(u.PlayerStart,u.Vector(-1200,-850,120),u.Rotator())
    start.set_actor_label('MudLab_Start')
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',u.GTMudLabGameMode)
    grass=None
    for a in actors.get_all_level_actors():
        for c in a.get_components_by_class(u.MeshComponent):
            for slot in range(c.get_num_materials()):
                original=c.get_material(slot)
                if original and original.get_name()=='M_VergeGrass':
                    grass=grass or material(original.get_path_name(),'M_LabGrass')
                    c.set_material(slot,grass)
    for i,(name,y) in enumerate([('1  FIRM SOIL',-850),('2  SOFT MUD',0),('3  STANDING WATER',850)]):
        sign=actors.spawn_actor_from_class(u.TextRenderActor,u.Vector(-650,y+325,125),u.Rotator())
        sign.set_actor_label('MudLab_Sign_'+str(i+1));text=sign.get_component_by_class(u.TextRenderComponent)
        sign.set_actor_rotation(u.Rotator(pitch=0,yaw=180,roll=0),False)
        text.set_text(name);text.set_world_size(42);text.set_text_render_color(u.Color(235,226,182,255))
        text.set_horizontal_alignment(u.HorizTextAligment.EHTA_CENTER)
        for x in [-780,1200]:
            for side in [-1,1]:
                post=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(x,y+side*350,45))
                post.set_actor_label('MudLab_SignPost_%d_%d_%d'%(i,x,side))
                post.static_mesh_component.set_static_mesh(assets.load_asset('/Engine/BasicShapes/Cube'))
                post.set_actor_scale3d(u.Vector(.12,.12,.9))
    u.EditorLevelLibrary.set_level_viewport_camera_info(u.Vector(-2450,-2350,1900),u.Rotator(pitch=-31,yaw=40,roll=0))
    for t in [paint,rest]:assert assets.save_loaded_asset(t)
    assert les.save_current_level()
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in hashes.items()),'Source asset changed'
    report.update(ok=True,source_assets_unchanged=True,game_mode='GTMudLabGameMode',
        landscape=s.landscape.get_path_name(),surface=s.get_surface_report(),actors=len(actors.get_all_level_actors()),
        signs=[dict(label=a.get_actor_label(),rotation=a.get_actor_rotation().to_tuple()) for a in actors.get_all_level_actors() if isinstance(a,u.TextRenderActor)])
except Exception:
    report['error']=traceback.format_exc();u.log_error(report['error'])
(OUT/'setup-report.json').write_text(json.dumps(report,indent=2))
s=sheet=world=ground=water=paint=rest=None
les.load_level('/Engine/Maps/Entry');u.SystemLibrary.collect_garbage()
quit_at=time.monotonic()+3
def finish(dt):
    if time.monotonic()>=quit_at:u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(finish)
