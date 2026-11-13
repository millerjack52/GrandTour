"""Playable, isolated shallow gravel test; preserves all shared mud/snow settings.
Deformable gravel DG1 (docs/DEFORMABLE_GRAVEL_PLAN.md): the field wears M_GT_Gravel (Art/Unreal/gravel_dg1_material.py, the DG1 bakes
with PBR and parallax), the landscape copy the same arrays; each section's profile carries its loose stones (12 per m^2 Firm, 30 Loose)
and the windrow heaps (LumpShare 0.3, dome cap 2.5 cm, radius 1-2 cells, LM2c's clustered and absent sites); clods stay off.
DG1b: the texture slides with the field at 0.25 of mud's (TextureSlideScale: the windrow walls' streaks)."""
import unreal as u, json, sys, traceback, random
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
from deformable_gravel_material import build,props,DEST
from gravel_dg1_material import build_all
import ground_detail   # GR2 phase B: the soil detail and the ground scatter (docs/GROUND_RELIEF_PLAN.md GR2)
import ground_relief   # GR1: the strips' relief numbers (docs/GROUND_RELIEF_PLAN.md GR1)
OUT=ROOT/'Art/Export/DeformableGravel';OUT.mkdir(parents=True,exist_ok=True)
eal=u.EditorAssetLibrary;assets=u.AssetToolsHelpers.get_asset_tools();les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
report={'ok':False}
def spawn(cls,label,pos,rot=None):
    a=act.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label(label);return a
try:
    report['ground_detail_stripped']=ground_detail.strip_landscape(DEST+'/M_GravelLandscape')   # GR2: the switches read nodes the builders remake
    report['materials']=[build(True),build(False)]   # the study's M_GravelField (kept for comparison) and its landscape copy
    report['dg1_materials']=build_all()               # DG1: M_GT_Gravel, the landscape on the arrays, M_GT_GravelStone, MPC
    level=DEST+'/L_GravelDeform'
    assert les.load_level(level) if eal.does_asset_exist(level) else les.new_level(level)
    for a in act.get_all_level_actors():
        if not isinstance(a,(u.WorldSettings,u.Brush)):act.destroy_actor(a)
    for name in ['Tarmac','Dirt','Mud','Bog','Snow']:
        path=DEST+'/Surfaces/PM_'+name
        pm=eal.load_asset(path) or eal.duplicate_asset('/Game/GrandTour/Terrain/Surfaces/PM_'+name,path)
        assert pm,path
        if name=='Dirt':props(pm,friction=.68,rolling_resistance=.035,sinkage_rate=.003,max_sinkage=.025,wet_sinkage_scale=1.15,wet_rolling_resistance_scale=1.15,sinkage_drag_scale=.35,plough_drag=.012,sinkage_grip_loss=.04)
        eal.save_loaded_asset(pm)
    spec=props(u.GTTerrainSpec(),components_per_side=3,subsections_per_component=1,quads_per_subsection=63,quad_size_cm=100.,origin_x_cm=-2000.,origin_y_cm=-9400.,base_amplitude_m=.40,base_wavelength_m=100.,octaves=2,slope_m_per_km=0.,road_half_width_m=3.5,shoulder_m=8.,route_m=[u.Vector2D(0,0),u.Vector2D(140,0)],alt_routes=[],planes=[],stations=[],features=[],biomes=[])
    # Ground relief GR1 items 1-3 and 5 ("the gravel strip the same"): rolling land, three relief octaves, the hummocks, the grass variation.
    ground_relief.apply_relief(spec)
    sections=[]
    for start,end,cap,rate,stones in [(30.,55.,.025,.004,12.),(80.,110.,.05,.009,30.)]:
        profile=props(u.GTDeformProfile(),mode=u.GTDeformProfileMode.ON,medium=u.GTDeformMedium.GRAVEL,surface_material_path=DEST+'/M_GT_Gravel.M_GT_Gravel',gravel_stones_per_m2=stones,texture_slide_scale=.25,max_sinkage_m=cap,sinkage_rate=rate,cell_cm=12.5,ridge_width_cm=45.,max_ridge_cm=3.,ridge_blend=1.,ridge_smooth=0.,ridge_foot_cm=18.,ridge_noise=.35,floor_noise_cm=.15,ridge_return=.85,rut_shoulder_cm=14.,rut_shoulder_min_cells=1.,rut_depth_variation=.12,ridge_slump=.08,ridge_slump_floor=.12,ridge_slump_rise_max_cm=.15,ridge_fill_share=.12,repose_deg=37.,slump_rate=3.,ooze_rate=0.,recover_share=0.,creep_cm_per_cm=.15,smear_cm_per_cm=0.,set_seconds=.7,lump_share=.3,lump_max_cm=2.5,lump_radius_cells=1.5,lump_variety_radius_jitter=.33,lump_absent_share=.5,lump_cluster_cm=150.,throw_max=0.,clod_chance=0.,clod_bank_per_cm=0.,clod_throw_chance=0.)
        sections.append(props(u.GTRouteSection(),start_m=start,end_m=end,kind=u.GTRouteSectionKind.ROAD,water_table_cm=-200.,deform=profile))
    spec.sections=sections;spec.spans=[props(u.GTSurfaceSpan(),start_m=0.,end_m=140.,layer=1)]
    asset=eal.load_asset(DEST+'/DA_GravelDeform') or assets.create_asset('DA_GravelDeform',DEST,u.GTTerrainSpecAsset,u.DataAssetFactory())
    props(asset,display_name='Shallow gravel - firm then loose',spec=spec);eal.save_loaded_asset(asset)
    builder=spawn(u.GTTerrainBuilder,'TerrainBuilder',(0,-2500,500))
    props(builder,spec_asset=asset,landscape_material_path=DEST+'/M_GravelLandscape',layer_info_folder=DEST+'/Layers',surface_folder=DEST+'/Surfaces')
    assert builder.rebuild_landscape(),builder.last_message
    for a in act.get_all_level_actors():
        if isinstance(a,u.GTTerrainDressing):act.destroy_actor(a)
    def height(x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x*100,y*100)
    spawn(u.PlayerStart,'PlayerStart',(500,0,height(5,0)+150))
    spawn(u.DirectionalLight,'Sun',(0,0,1000));sky=spawn(u.SkyLight,'SkyLight',(0,0,1000));sky.light_component.set_editor_property('real_time_capture',True)
    spawn(u.SkyAtmosphere,'SkyAtmosphere',(0,0,0));spawn(u.ExponentialHeightFog,'HeightFog',(0,0,0))
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    from tussock_style_lighting import configure
    configure(world)
    group=spawn(u.Actor,'TS_ApprovedTussock',(0,0,0));group.root_component.set_mobility(u.ComponentMobility.STATIC)
    rng=random.Random(71008);transforms=[]
    for i in range(360):
        x=rng.uniform(0,140);y=rng.choice([-1,1])*rng.uniform(6.0,19.);s=rng.uniform(.65,1.1)
        transforms.append(u.Transform(u.Vector(x*100,y*100,height(x,y)),u.Rotator(yaw=rng.uniform(0,360)),u.Vector(s,s,s)))
    transforms,report['grass_variation']=ground_relief.vary(spec,transforms,True)   # GR1 item 5
    c=u.GTVegetationSubsystem.add_tagged_instances(group,u.load_asset('/Game/GrandTour/ArtTests/TussockStyle/SM_TS_Straw'),transforms,'GravelTestGrass','NoCollision',True)
    c.set_cull_distances(8500,13500)
    # GR2 phase B (docs/GROUND_RELIEF_PLAN.md GR2): the soil detail (MI_GT_Landscape_Strips) on the grass verge and the ground scatter.
    report['ground_detail']=ground_detail.apply_strip('GravelDeform',DEST,DEST+'/M_GravelLandscape','gravel',asset,ground_detail.grass_rows(transforms,0),transforms,[r[2] for r in ground_detail.grass_rows(transforms,0)])
    camera=spawn(u.CameraActor,'Gravel_Review',(3200,-500,180),u.Rotator(pitch=-16,yaw=20));camera.camera_component.set_field_of_view(65.)
    world.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    report['relief']=ground_relief.report(spec);report['relief_numbers']=ground_relief.numbers()   # GR1
    assert les.save_current_level()
    report.update(ok=True,level=level,sections=[{'span_m':[s.start_m,s.end_m],'sink_cap_cm':s.deform.max_sinkage_m*100,'sink_rate_cm_s':s.deform.sinkage_rate*100} for s in sections],cell_cm=12.5,physical_surface='Dirt tag with test-owned gravel coefficients',limitations=['heightfield-driven wheel sinkage/rut forces; base landscape collision is not recooked','session lifetime only','not installed across Benmore yet'])
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
finally:
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()

