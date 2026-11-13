"""A repeatable playable gravel/mud/ford strip using existing vehicle and terrain physics.

LM5b (docs/MUD_VARIANTS.md): the mud section is a Standard bog (FGTRouteSection::MudVariant's default), so it wears the
Standard bog slice everywhere in its patch; the landscape material comes from live_mud_style.live_landscape.
"""
import unreal as u,json,sys,traceback,random,math,os
from pathlib import Path
ROOT=Path(u.Paths.project_dir()).resolve();OUT=ROOT/'Art/Export/LiveMudDrive';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Art/Unreal'));os.environ['GT_M6_AS_MODULE']='1'
from live_mud_style import apply_existing,live_landscape
import setup_m6_hide as terrain
import ground_detail   # GR2 phase B: the soil detail and the ground scatter (docs/GROUND_RELIEF_PLAN.md GR2)
import ground_relief   # GR1: the strips' relief numbers (docs/GROUND_RELIEF_PLAN.md GR1)
import mud_roads   # Mud roads MRD1 (docs/MUD_ROADS_PLAN.md item 5): a 60 m MudRoad section at 115-175 m
eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;assets=u.AssetToolsHelpers.get_asset_tools();les=u.get_editor_subsystem(u.LevelEditorSubsystem);act=u.get_editor_subsystem(u.EditorActorSubsystem)
DEST='/Game/GrandTour/ArtTests/LiveMudDrive';LEVEL=DEST+'/L_MudDrive';report={'ok':False}
ROUTE_M=200.;ROAD_M=(115.,175.)   # MRD1 item 5: the MudRoad section (its box 108.2-181.8 m, clear of the ford's)
def setprops(obj,**values):
    for key,value in values.items():obj.set_editor_property(key,value)
    return obj
def spawn(cls,label,pos,rot=None):
    a=act.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator());a.set_actor_label(label);return a
try:
    report['materials']=apply_existing()
    report['mud_road_branches']=mud_roads.import_branches()   # MRD1 item 3
    if eal.does_asset_exist(LEVEL):assert les.load_level(LEVEL)
    else:assert les.new_level(LEVEL)
    for a in act.get_all_level_actors():
        if not isinstance(a,(u.WorldSettings,u.Brush)):act.destroy_actor(a)
    spec=u.GTTerrainSpec()
    # MRD1 item 5: the route on to 200 m and 4 components (x -20..232 m, y -126..126 m, as L_MudVariants) for a 60 m MudRoad at 115-175 m.
    setprops(spec,components_per_side=4,subsections_per_component=1,quads_per_subsection=63,quad_size_cm=100.,origin_x_cm=-2000.,origin_y_cm=-12600.,base_amplitude_m=1.2,base_wavelength_m=90.,octaves=2,slope_m_per_km=0.,road_half_width_m=3.,shoulder_m=8.,route_m=[u.Vector2D(0,0),u.Vector2D(ROUTE_M,0)],alt_routes=[],planes=[],stations=[])
    # Ground relief GR1 items 1-3 and 5: rolling land (at 60 m, 4 octaves), three relief octaves, the hummocks, the grass variation.
    ground_relief.apply_relief(spec,base_amplitude_m=ground_relief.MUD_DRIVE_AMPLITUDE_M)   # 2.75 m: the route-drivability rule (ground_relief.py)
    mud=setprops(u.GTRouteSection(),start_m=32.,end_m=60.,kind=u.GTRouteSectionKind.MUD,deform=ground_relief.bog_deform())   # GR1 item 4: pre-churned
    ford=setprops(u.GTRouteSection(),start_m=88.,end_m=100.,kind=u.GTRouteSectionKind.FORD,depth_m=.35)
    road=setprops(u.GTRouteSection(),start_m=ROAD_M[0],end_m=ROAD_M[1],kind=u.GTRouteSectionKind.MUD,deform=mud_roads.road_deform(),water_table_cm=mud_roads.ROAD_WATER_TABLE_CM)   # MRD1 item 5
    spec.sections=[mud,ford,road]
    spec.spans=[setprops(u.GTSurfaceSpan(),start_m=0.,end_m=ROUTE_M,layer=1)]
    spec.features=[setprops(u.GTTerrainFeature(),kind=u.GTTerrainFeatureKind.CHANNEL,start_m=u.Vector2D(94,-35),end_m=u.Vector2D(94,35),radius_m=12.,height_m=1.4),setprops(u.GTTerrainFeature(),kind=u.GTTerrainFeatureKind.HILL,start_m=u.Vector2D(60,30),radius_m=35.,height_m=8.),setprops(u.GTTerrainFeature(),kind=u.GTTerrainFeatureKind.HILL,start_m=u.Vector2D(125,-35),radius_m=38.,height_m=9.)]
    spec_asset=eal.load_asset(DEST+'/DA_MudDrive') or assets.create_asset('DA_MudDrive',DEST,u.GTTerrainSpecAsset,u.DataAssetFactory())
    setprops(spec_asset,display_name='Gravel - live clay - ford',spec=spec);eal.save_loaded_asset(spec_asset)
    # This map has its own landscape material so its gravel can match the approved art road. LM5b: built by live_mud_style's
    # live_landscape (shared with L_MudVariants): its apron round each live patch takes the patch's variant slice from
    # MPC_TrackPaint's boxes, in place of the clay inside the two boxes measured here before.
    report['landscape_material']=live_landscape(DEST+'/M_LiveLandscape')
    builder=spawn(u.GTTerrainBuilder,'TerrainBuilder',(0,-2500,500));builder.spec_asset=spec_asset;builder.landscape_material_path=DEST+'/M_LiveLandscape';assert builder.rebuild_landscape(),builder.last_message
    # The builder includes legacy prototype foliage. This strip uses the approved tussocks below.
    for dressing in act.get_all_level_actors():
        if isinstance(dressing,u.GTTerrainDressing):
            for component in dressing.get_components_by_class(u.InstancedStaticMeshComponent):
                if component.get_name()=='Foliage':component.clear_instances()
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    def height(x,y):return u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec,x*100,y*100)
    spawn(u.PlayerStart,'PlayerStart',(500,0,height(5,0)+150))
    sun=spawn(u.DirectionalLight,'Sun',(0,0,1000));sky=spawn(u.SkyLight,'SkyLight',(0,0,1000));sky.light_component.set_editor_property('real_time_capture',True)
    spawn(u.SkyAtmosphere,'SkyAtmosphere',(0,0,0));spawn(u.ExponentialHeightFog,'HeightFog',(0,0,0))
    from tussock_style_lighting import configure
    configure(world)
    terrain.place_ford_sheet(world,spec,1,ford,eal.load_asset('/Game/GrandTour/Materials/M_GT_Water'))
    for x in [28,65,83,105,178]:
        a=spawn(u.GTWinchAnchor,'WinchPost_'+str(x),(x*100,650,height(x,6.5)));a.get_anchor().set_editor_property('strength_n',200000.)
    data=json.loads((ROOT/'Art/Export/TussockStyle/manifest.json').read_text());group=spawn(u.Actor,'TS_ApprovedTussock',(0,0,0));group.root_component.set_mobility(u.ComponentMobility.STATIC);count=0
    gd_grass,gd_tussocks=[],[]   # GR2 phase B: every grass instance (the grass map) and the tussocks (the scatter's mounds and litter)
    for kind in range(4):
        name=next(r['name'].replace('_LOD0','') for r in data['models'] if r['kind']==kind and r['lod']==0);mesh=eal.load_asset('/Game/GrandTour/ArtTests/TussockStyle/'+name);transforms=[]
        for offset in [0,72,144]:
            for i,p in enumerate(data['placements']):
                if p['kind']!=kind:continue
                x,y,_=p['location_m'];x+=offset;y=-y
                if not(0<x<ROUTE_M and 5.5<abs(y)<22) or 81<x<107 or (abs(y)>12 and i%3):continue
                z=height(x,y);rx,ry,rz=p['rotation_deg'];scale=p['scale'];transforms.append(u.Transform(u.Vector(x*100,y*100,z),u.Rotator(roll=rx,pitch=-ry,yaw=-rz),u.Vector(scale,scale,scale)))
        transforms,stats=ground_relief.vary(spec,transforms,kind!=3);report.setdefault('grass_variation',{})[name]=stats   # GR1 item 5
        gd_grass+=ground_detail.grass_rows(transforms,kind);gd_tussocks+=transforms if kind!=3 else []
        c=u.GTVegetationSubsystem.add_tagged_instances(group,mesh,transforms,'LiveMudGrass','NoCollision',kind!=3);c.set_cull_distances(6500,10500);c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('visible_in_ray_tracing',False);count+=len(transforms)
    # GR2 phase B (docs/GROUND_RELIEF_PLAN.md GR2): the soil detail (MI_GT_Landscape_Strips) and the ground scatter, strips only.
    report['ground_detail']=ground_detail.apply_strip('LiveMudDrive',DEST,DEST+'/M_LiveLandscape','live',spec_asset,gd_grass,gd_tussocks,[r[2] for r in ground_detail.grass_rows(gd_tussocks,0)])
    overview=spawn(u.CameraActor,'Live_Overview',(4000,1800,1600),u.Rotator(pitch=-22,yaw=-20));overview.camera_component.set_field_of_view(65)
    world.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    report['relief']=ground_relief.report(spec);report['relief_numbers']=ground_relief.numbers()   # GR1
    assert les.save_current_level();report.update(ok=True,level=LEVEL,grass_instances=count,route_m=ROUTE_M,mud_m=[32,60],ford_m=[88,100],water_depth_m=.35,
                                                  mud_road_m=list(ROAD_M),mud_road=dict(pre_churn_style='Braided',water_table_cm=mud_roads.ROAD_WATER_TABLE_CM,mud_road_spray_scale=mud_roads.SPRAY_SCALE,debris_per_m2=mud_roads.DEBRIS_PER_M2),physics='Soft variable rut shoulders in the shared field; vehicle coefficients and maximum sinkage unchanged')
except Exception:report['error']=traceback.format_exc();u.log_error(report['error'])
finally:(OUT/'setup-report.json').write_text(json.dumps(report,indent=2));u.SystemLibrary.quit_editor()
