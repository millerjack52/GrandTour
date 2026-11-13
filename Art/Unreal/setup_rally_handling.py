"""Build and check an isolated circuit using the production firm-gravel pipeline."""
from pathlib import Path
import unreal as u
import sys, os, json, math, time, traceback, hashlib, shutil, gc, random

ROOT=Path(u.Paths.project_dir()).resolve();sys.path.insert(0,str(ROOT/'Art/Unreal'))
BASE='/Game/GrandTour/ArtTests/RallyHandling';LEVEL=BASE+'/L_RallyHandling'
SOURCE='/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy'
OUT=ROOT/'Art/Export/RallyHandling';QA=ROOT/'Saved/RallyHandlingQA';QA.mkdir(parents=True,exist_ok=True)
DATA=json.loads((OUT/'course.json').read_text());MODE=os.environ.get('GT_RALLY_HANDLING_MODE','Install')
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
A=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.get_editor_subsystem(u.LevelEditorSubsystem)
report=dict(ok=False,mode=MODE,level=LEVEL,length_m=DATA['length_m'],images=[])
protected=ROOT/'Content/GrandTour/ArtTests/LidarStudy/L_LidarStudy.umap'
before=hashlib.sha256(protected.read_bytes()).hexdigest()
def save(): (QA/(MODE.lower()+'.json')).write_text(json.dumps(report,indent=2))
def props(o,**kw):
    for k,v in kw.items():o.set_editor_property(k,v)
    return o
def spawn(cls,label,p=(0,0,0),yaw=0):
    a=A.spawn_actor_from_class(cls,u.Vector(*p),u.Rotator(yaw=yaw));a.set_actor_label('Rally_'+label);return a
def texture(name):
    task=props(u.AssetImportTask(),filename=str(OUT/(name+'.png')),destination_path=BASE,destination_name='T_'+name,automated=True,replace_existing=True,save=True)
    AT.import_asset_tasks([task]);t=u.load_asset(BASE+'/T_'+name);assert t
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,never_stream=True,address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP)
    E.save_loaded_asset(t);return t
def flat_material(name,color):
    m=u.load_asset(BASE+'/'+name) or AT.create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(m)
    M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    c=props(M.create_material_expression(m,u.MaterialExpressionConstant3Vector),constant=u.LinearColor(*color))
    M.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
    r=props(M.create_material_expression(m,u.MaterialExpressionConstant),r=.85)
    M.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS);M.recompile_material(m);E.save_loaded_asset(m);return m
def cube(label,p,scale,mat,yaw=0,solid=False):
    a=spawn(u.StaticMeshActor,label,p,yaw);a.set_actor_scale3d(u.Vector(*scale))
    a.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    a.static_mesh_component.set_material(0,mat);a.static_mesh_component.set_collision_profile_name('BlockAll' if solid else 'NoCollision');return a
def text(label,p,caption,yaw=180,size=65):
    a=spawn(u.TextRenderActor,label,p,yaw);c=a.get_component_by_class(u.TextRenderComponent)
    c.set_text(caption);c.set_world_size(size);c.set_text_render_color(u.Color(245,232,198,255));return a
def heading(i):
    p=DATA['points_m'][i];q=DATA['points_m'][min(i+1,len(DATA['points_m'])-1)]
    return math.degrees(math.atan2(q[1]-p[1],q[0]-p[0]))
def fix_gravel_material(mat):
    # The LiDAR RD1 mask is survey-specific. Here the generated style mask owns
    # the road width; alpha still supplies real lateral tyre-wear coordinates.
    for ex in M.get_material_expressions(mat):
        if isinstance(ex,u.MaterialExpressionCustom):
            code=str(ex.get_editor_property('code'))
            if '// RD1 gravel' in code:
                code=code.replace(')*6.4);',')*12.8);')
                code=code.replace('float gw=1-smoothstep(2.0,2.6,ad);','float gw=1-smoothstep(.04,.60,style.g);')
                ex.set_editor_property('code',code)
    # This whole test surface is fixed gravel. Do not inherit live-grid offsets,
    # opacity cutouts on its overlay tiles.
    zero=next((e for e in M.get_material_expressions(mat) if str(e.get_editor_property('desc'))=='RallyFixedZero'),None)
    if not zero:zero=props(M.create_material_expression(mat,u.MaterialExpressionConstant),r=0.,desc='RallyFixedZero')
    M.connect_material_property(zero,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    assert not M.recompile_material(mat);assert E.save_loaded_asset(mat)
def ground(x,y,tiles,fallback=0):
    for t in tiles:
        p=t.get_actor_location()
        if p.x<=x<p.x+t.span_cm and p.y<=y<p.y+t.span_cm:return t.height_at(u.Vector2D(x,y))
    return fallback
def check(world):
    refs=u.GameplayStatics.get_all_actors_of_class(world,u.GTMudRoute);assert len(refs)==1
    route=refs[0];assert not route.start_low_range and not route.start_diff_locked
    assert len(route.get_editor_property('recovery_points'))==7
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    # Avoid the spline's overlapping closure endpoints, where the start fade blends.
    samples=[surface.sample_surface(u.Vector2D(p[0]*100,p[1]*100)) for p in DATA['samples_m'][15:-15:5]]
    assert all(str(s.surface_tag)=='Gravel' and s.sinkage_cap_cm<.01 and s.water_depth_cm<.01 for s in samples),'Non-firm carriageway sample'
    garage=u.GameplayStatics.get_all_actors_of_class(world,u.GTGarage)[0];assert len(garage.vehicles)==12
    import lidar_gravel_dust
    lidar_gravel_dust.validate(world)
    return dict(firm_samples=len(samples),cars=len(garage.vehicles),checkpoints=7,high_range=True,open_diffs=True)

def install():
    # Read production bindings, then create the new level before any mutation.
    assert L.load_level(SOURCE);refs=list(A.get_all_level_actors())
    source_author=next(a for a in refs if isinstance(a,u.GTProceduralGround))
    ground_source=source_author.relief_material.get_path_name()
    relief=next(a.relief_texture for a in refs if isinstance(a,u.GTProceduralRoad) and a.relief_texture)
    manager=next(a for a in refs if isinstance(a,u.GTVehicleSurfaceEffects))
    fx=(manager.dust_system,manager.mud_system,manager.mud_intensity)
    canopy=[];grass=None
    for a in refs:
        if isinstance(a,u.GTMixedGroundDetails) and a.grass_material:
            grass=(a.grass.static_mesh,a.grass_material)
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if c.static_mesh and c.static_mesh.get_name().startswith('SM_Canopy_') and len(canopy)<4:
                canopy.append((c.static_mesh,list(c.get_materials())))
    E.make_directory(BASE)
    if E.does_asset_exist(LEVEL):
        backup=ROOT/'Saved/RallyHandlingBackups'/str(time.time_ns());backup.mkdir(parents=True)
        shutil.copy2(ROOT/'Content/GrandTour/ArtTests/RallyHandling/L_RallyHandling.umap',backup/'L_RallyHandling.umap')
        assert L.load_level(LEVEL)
        for a in list(A.get_all_level_actors()):
            if a.get_class().get_name() not in ['WorldSettings','LevelScriptActor','Brush']:A.destroy_actor(a)
    else:assert L.new_level(LEVEL,False)
    refs=source_author=manager=None;gc.collect()
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world();assert '/RallyHandling/' in world.get_path_name()
    tex={n:texture(n) for n in ['paint','style','macro','clay']}
    mat=u.load_asset(BASE+'/M_Terrain') or E.duplicate_asset(ground_source,BASE+'/M_Terrain');assert mat
    codes=[]
    for ex in M.get_material_expressions(mat):
        if isinstance(ex,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionTextureSample)):
            t=ex.get_editor_property('texture')
            if t:
                for key in tex:
                    if t.get_name().lower() in ['t_'+key,'t_'+key+'_groundstudy']:ex.set_editor_property('texture',tex[key])
        if isinstance(ex,u.MaterialExpressionVectorParameter) and str(ex.get_editor_property('parameter_name'))=='GTLS_PaintWindow':ex.set_editor_property('default_value',u.LinearColor(-25200,-25200,50400,0))
        if isinstance(ex,u.MaterialExpressionCustom):
            code=str(ex.get_editor_property('code')).replace('185000','25200').replace('370000','50400')
            ex.set_editor_property('code',code);codes.append(code)
    (QA/'terrain-code.txt').write_text('\n\n'.join(codes))
    fix_gravel_material(mat)
    seed=u.load_asset('/Game/GrandTour/Demo/MackenzieBlockout/DA_Mackenzie_Blockout').spec
    props(seed,components_per_side=2,subsections_per_component=2,quads_per_subsection=63,quad_size_cm=200.,origin_x_cm=-25200.,origin_y_cm=-25200.,z_scale=100.,base_amplitude_m=0.,slope_m_per_km=0.,route_m=[],features=[],planes=[],alt_routes=[],stations=[],sections=[],spans=[],biomes=[],scrub_roughness_m=0.,road_roughness_m=0.,track_roughness_m=0.)
    asset=u.load_asset(BASE+'/DA_Grid') or AT.create_asset('DA_Grid',BASE,u.GTTerrainSpecAsset,u.DataAssetFactory())
    props(asset,spec=seed,display_name='Rally handling');E.save_loaded_asset(asset)
    dress=spawn(u.GTTerrainDressing,'TemporaryDressing');dress.foliage_density=0
    builder=spawn(u.GTTerrainBuilder,'TemporaryBuilder')
    props(builder,spec_asset=asset,landscape_material_path=BASE+'/M_Terrain',layer_info_folder=BASE+'/Layers',reground_actors=False)
    land=builder.rebuild_landscape();assert land,builder.last_message
    A.destroy_actor(builder);A.destroy_actor(dress);land.set_actor_label('Rally_504m terrain')
    surface=spawn(u.GTLandscapeSurface,'FirmSurface')
    props(surface,landscape=land,paint_origin_cm=u.Vector2D(-25200,-25200),paint_size_cm=50400.,grass_is_visual_cover=True,use_native_substance_response=True,use_soil_shear_response=True,enable_wheel_support=True,mud_regions=[])
    assert u.GTLandscapeSurfaceSetupLibrary.import_paint(surface,tex['paint'])
    assert u.GTLandscapeSurfaceSetupLibrary.import_material_atlas(surface,tex['style'])
    author=spawn(u.GTProceduralGround,'Road author - select road points and Rebuild')
    props(author,landscape=land,surface=surface,seed=221026,output_asset_root=BASE+'/',paint_texture=tex['paint'],style_texture=tex['style'],macro_texture=tex['macro'],relief_material=mat,relief_spacing_cm=50.,landscape_recess_depth_cm=5.,scatter_rules=[])
    author.generation_bounds.set_box_extent(u.Vector(24000,24000,5000),False)
    assert author.capture_base(),author.last_message
    road=spawn(u.GTProceduralRoad,'Circuit - editable control points')
    props(road,author=author,width_cm=900.,firm_gravel=True,firm_roughness_cm=4.,profile_smoothing_metres=6.,firm_maximum_cut_fill_cm=400.,bed_depth_cm=0.,mud_depth_cm=0.,wetness=.12,centre_grass_cover=0.,verge_grass_cover=.85,relief_texture=relief)
    road.control_points.clear_spline_points(False)
    for i,p in enumerate(DATA['points_m']):
        road.control_points.add_spline_point(u.Vector(*(v*100 for v in p)),u.SplineCoordinateSpace.WORLD,False)
        road.control_points.set_scale_at_spline_point(i,u.Vector(1,1.18 if i in [0,1,2,3,19,20,21,22,29,30,31] else 1.,1),False)
    road.control_points.update_spline()
    # Apron connects to the main straight, providing a safe fleet change area.
    pit=spawn(u.GTProceduralRoad,'Service apron')
    props(pit,author=author,width_cm=1800.,firm_gravel=True,bed_depth_cm=0.,mud_depth_cm=0.,wetness=.12,relief_texture=relief)
    pit.control_points.clear_spline_points(False)
    for p in [(-10000,-18000,0),(-10000,-20500,0),(-6000,-20500,0)]:pit.control_points.add_spline_point(u.Vector(*p),u.SplineCoordinateSpace.WORLD,False)
    pit.control_points.update_spline();assert author.rebuild(),author.last_message
    report['generation']=dict(digest=str(author.output_digest),tiles=len(author.relief_tiles),message=str(author.last_message));save();yield 4
    tiles=list(author.relief_tiles.values())
    recover=[]
    for cp in DATA['checkpoints']:
        i=cp['index'];x,y,z=[v*100 for v in DATA['points_m'][i]]
        recover.append(u.Transform(location=u.Vector(x,y,ground(x,y,tiles)+100),rotation=u.Rotator(yaw=heading(i))))
    recover[-1]=u.Transform(location=u.Vector(-8000,-20500,100),rotation=u.Rotator(yaw=0))
    route=spawn(u.GTMudRoute,'Numbered resets')
    props(route,title='RALLY HANDLING / 1.54 km gravel circuit',checkpoint_labels='1 Start  2 Fast right  3 Linked bends  4 Sweeper  5 Hairpin  6 Crest  7 Service',recovery_points=recover,start_low_range=False,start_diff_locked=False)
    start=spawn(u.PlayerStart,'Start',(-10000,-18000,110));world.get_world_settings().set_editor_property('default_game_mode',u.GTMudLabGameMode)
    from lidar_homestead import roster
    garage=spawn(u.GTGarage,'Service - walk up and press E',(-8000,-21900,105),90)
    props(garage,vehicles=roster(),vehicle_spawn_transform=recover[-1],display_name='Rally service - choose a car')
    cream=flat_material('M_Marker',(.8,.73,.52));orange=flat_material('M_Orange',(.75,.16,.035));dark=flat_material('M_Service',(.035,.055,.06))
    # Small open service shelter: no building asset changes and no driving obstacles.
    cube('ServiceRoof',(-8000,-22600,360),(14,12,.22),dark,solid=True)
    for x in [-8600,-7400]:cube('ServicePost',(x,-23000,175),(.18,.18,3.5),cream,solid=True)
    cube('ServiceBack',(-8000,-23150,160),(14,.18,3.2),dark,solid=True)
    text('ServiceSign',(-8600,-21870,270),'RALLY SERVICE',90,75)
    text('Help',(-8600,-21870,175),'F exit | E menu | scroll + T select\n1-6 repeat sections | 7 service\nF1 info | C camera | Backspace restart',90,30)
    for k,cp in enumerate(DATA['checkpoints'][:-1],1):
        i=cp['index'];p=DATA['points_m'][i];yaw=heading(i);rad=math.radians(yaw)
        x=p[0]*100+math.sin(rad)*800;y=p[1]*100-math.cos(rad)*800;z=ground(x,y,tiles)
        cube('SectionPost',(x,y,z+90),(.13,.13,1.8),cream)
        text('Section'+str(k),(x,y,z+190),str(k)+' / '+cp['name'],yaw+180,42)
    # Repeated edge posts are instanced, non-colliding, and well outside tyre paths.
    owner=spawn(u.Actor,'Course edge markers');transforms=[]
    samples=DATA['samples_m']
    for i in range(0,len(samples)-2,18):
        p=samples[i];q=samples[i+2];yaw=math.atan2(q[1]-p[1],q[0]-p[0])
        for sign in [-1,1]:
            x=p[0]*100+sign*math.sin(yaw)*720;y=p[1]*100-sign*math.cos(yaw)*720
            transforms.append(u.Transform(location=u.Vector(x,y,ground(x,y,tiles)+45),scale=u.Vector(.13,.13,.9)))
    c=u.GTVegetationSubsystem.add_tagged_instances(owner,u.load_asset('/Engine/BasicShapes/Cube'),transforms,'RallyMarkers','NoCollision',False);c.set_material(0,cream)
    for n,x in [(150,1000),(100,6000),(50,11000)]:
        cube('BrakeBoard',(x,-18900,110),(.15,2,1.5),orange)
        text('Brake'+str(n),(x-10,-18900,145),str(n),180,60)
    # A visible start gantry, clear above the road and outside its edges.
    for y in [-18700,-17300]:cube('StartPost',(-10000,y,300),(.22,.22,6),dark)
    cube('StartBeam',(-10000,-18000,600),(.25,14,.3),orange)
    text('StartBanner',(-10025,-18300,550),'START',180,100)
    # Reuse production tree meshes around the outside; keep all sight lines/runoff clear.
    rng=random.Random(221026);report['tree_variants']=len(canopy)
    for index,(mesh,mats) in enumerate(canopy):
        ts=[];bounds=mesh.get_bounds()
        for j in range(65):
            angle=rng.uniform(0,math.tau);radius=rng.uniform(22000,24700)
            x,y=math.cos(angle)*radius,math.sin(angle)*radius
            if y < -21000 and -11000<x<-5000:continue
            sc=rng.uniform(900,1600)/max(1,bounds.box_extent.z*2)
            ts.append(u.Transform(location=u.Vector(x,y,-(bounds.origin.z-bounds.box_extent.z)*sc),rotation=u.Rotator(yaw=rng.uniform(0,360)),scale=u.Vector(sc,sc,sc)))
        c=u.GTVegetationSubsystem.add_tagged_instances(owner,mesh,ts,'RallyTrees','NoCollision',True)
        for slot,m in enumerate(mats):c.set_material(slot,m)
        c.set_cull_distances(45000,55000)
    sun=spawn(u.DirectionalLight,'Sun');sun.set_actor_rotation(u.Rotator(pitch=-38,yaw=-32),False)
    props(sun.light_component,intensity=8.,atmosphere_sun_light=True)
    sky=spawn(u.SkyLight,'Sky');props(sky.light_component,intensity=1.2,real_time_capture=True)
    spawn(u.SkyAtmosphere,'Atmosphere')
    pp=spawn(u.PostProcessVolume,'Exposure');pp.set_editor_property('unbound',True)
    settings=pp.settings
    props(settings,override_auto_exposure_min_brightness=True,override_auto_exposure_max_brightness=True,auto_exposure_min_brightness=.25,auto_exposure_max_brightness=.25,override_auto_exposure_bias=True,auto_exposure_bias=0.)
    pp.settings=settings
    manager=spawn(u.GTVehicleSurfaceEffects,'Dust and surface effects')
    props(manager,dust_system=fx[0],mud_system=fx[1],mud_intensity=fx[2],dust_intensity=1.2)
    manager.set_editor_property('bEnabled',True)
    for t in tex.values():assert E.save_loaded_asset(t)
    assert L.save_current_level();report['saved']=True;save()
    world=land=surface=author=road=pit=tiles=route=start=garage=manager=None;gc.collect()
    assert L.load_level('/Engine/Maps/Entry');yield 3
    assert L.load_level(LEVEL);yield 3
    report['validation']=check(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world());report['saved_and_reloaded']=True

def polish():
    assert L.load_level(LEVEL);yield 3
    texture('clay');fix_gravel_material(u.load_asset(BASE+'/M_Terrain'))
    marker=u.load_asset(BASE+'/M_Marker')
    M.set_material_usage(marker,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert E.save_loaded_asset(marker)
    report['validation']=check(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world())
    yield 3

def recess():
    # Back up every owned authored asset, not only the map, before regeneration.
    backup=ROOT/'Saved/RallyHandlingBackups'/('recess-'+str(time.time_ns()))
    shutil.copytree(ROOT/'Content/GrandTour/ArtTests/RallyHandling',backup)
    report['backup']=str(backup);save()
    assert L.load_level(LEVEL);yield 3
    author=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
    report['previous_recess_cm']=author.landscape_recess_depth_cm
    assert author.has_base,'Do not recapture the already recessed terrain as the base'
    author.landscape_recess_depth_cm=5.
    assert author.rebuild(),author.last_message
    for t in (author.paint_texture,author.style_texture,author.macro_texture):assert E.save_loaded_asset(t)
    assert L.save_current_level()
    author=None;gc.collect();assert L.load_level('/Engine/Maps/Entry');yield 3
    assert L.load_level(LEVEL);yield 3
    author=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
    assert author.landscape_recess_depth_cm==5
    report['recess_cm']=author.landscape_recess_depth_cm
    report['validation']=check(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world())
    report['saved_and_reloaded']=True

def surface_feedback():
    backup=ROOT/'Saved/RallyHandlingBackups'/('surface-'+str(time.time_ns()))
    shutil.copytree(ROOT/'Content/GrandTour/ArtTests/RallyHandling',backup)
    report['backup']=str(backup);save()
    assert L.load_level(LEVEL);yield 3
    author=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
    assert author.has_base and author.landscape_recess_depth_cm==5
    roads=[a for a in A.get_all_level_actors() if isinstance(a,u.GTProceduralRoad)]
    circuit=next(a for a in roads if a.get_actor_label()=='Rally_Circuit - editable control points')
    previous_roughness=float(circuit.firm_roughness_cm)
    # Independent left/right tracks through the existing straight, before/after.
    samples=[(x,-18000+y) for x in range(-9000,4000,50) for y in (-75,75)]
    tiles=list(author.relief_tiles.values());before=[ground(x,y,tiles) for x,y in samples]
    circuit.firm_roughness_cm=4.
    assert author.rebuild(),author.last_message
    for t in (author.paint_texture,author.style_texture,author.macro_texture):assert E.save_loaded_asset(t)
    assert L.save_current_level()
    author=circuit=roads=tiles=None;gc.collect();assert L.load_level('/Engine/Maps/Entry');yield 3
    assert L.load_level(LEVEL);yield 3
    author=next(a for a in A.get_all_level_actors() if isinstance(a,u.GTProceduralGround))
    tiles=list(author.relief_tiles.values());after=[ground(x,y,tiles) for x,y in samples]
    delta=[b-a for a,b in zip(before,after)]
    report['surface_feedback']=dict(previous_roughness_cm=previous_roughness,roughness_cm=4.,samples=len(samples),min_added_cm=min(delta),max_added_cm=max(delta),height_variation_cm=max(delta)-min(delta))
    if abs(previous_roughness-4.)<.001:
        assert max(abs(d) for d in delta)<.1,'Repeated Surface changed the existing relief'
    else:
        assert max(abs(d) for d in delta)<abs(4.-previous_roughness)+.1 and max(delta)-min(delta)>abs(4.-previous_roughness)*.25,report['surface_feedback']
    report['validation']=check(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world())
    report['saved_and_reloaded']=True

def review():
    assert L.load_level(LEVEL);yield 3
    L.editor_set_viewport_realtime(False)
    assert u.GTPlayWindowLibrary.request_play_in_new_window(1440,900)
    world=None;until=time.monotonic()+180
    while not world:
        world=u.EditorLevelLibrary.get_game_world();assert time.monotonic()<until;yield .2
    pc=u.GameplayStatics.get_player_controller(world,0);car=pc.get_car();move=car.get_chaos_movement()
    report['validation']=check(world)
    assert not car.get_drivetrain().is_low_range() and not car.get_drivetrain().is_diff_locked()
    for n in range(1,8):
        pc.select_lane(n);assert not car.get_drivetrain().is_low_range() and not car.get_drivetrain().is_diff_locked()
    pc.select_lane(1);car.disable_input(pc);move.set_handbrake_input(True)
    for cmd in ['DisableAllScreenMessages','t.IdleWhenNotForeground 0','Slate.bAllowThrottling 0']:
        u.SystemLibrary.execute_console_command(world,cmd,pc)
    yield 8
    camera=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.CameraActor,u.Transform(),'RallyReview')
    camera.camera_component.set_constraint_aspect_ratio(False);camera.camera_component.set_field_of_view(65)
    camera.set_actor_location_and_rotation(u.Vector(-34000,-39000,39000),u.Rotator(pitch=-40,yaw=48),False,True)
    pc.set_view_target_with_blend(camera,0);yield 4
    yield from capture(world,'Overview')
    pc.set_view_target_with_blend(car,0);move.set_handbrake_input(False)
    began=u.GameplayStatics.get_time_seconds(world);samples=[];shot=False
    # Functional smoke drive on the acceleration straight, not a handling-quality verdict.
    while u.GameplayStatics.get_time_seconds(world)-began<9:
        move.set_throttle_input(1.);move.set_brake_input(0.);car.set_raw_steer(0.)
        p=car.get_actor_location();samples.append(dict(speed_kmh=car.get_velocity().length()*.036,x=p.x,y=p.y,z=p.z))
        if not shot and u.GameplayStatics.get_time_seconds(world)-began>6:
            yield from capture(world,'Driving');shot=True
        yield .1
    move.set_throttle_input(0);move.set_brake_input(1);report['drive']=dict(peak_kmh=max(s['speed_kmh'] for s in samples),distance_m=(samples[-1]['x']-samples[0]['x'])/100,samples=samples)
    assert report['drive']['peak_kmh']>40 and report['drive']['distance_m']>50
    assert max(abs(s['y']+18000) for s in samples)<350,'Straight-line instability'
    labs=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.GTDustLab) if a.target_car==car and a.intensity>0]
    report['live_dust']=sum(a.get_live_particles() for a in labs);assert report['live_dust']>0
    pc.select_lane(7);car.reset_driving_inputs();move.set_handbrake_input(True);yield 4
    assert pc.exit_car()
    ch=pc.get_player_character();ch.set_actor_location(u.Vector(-8000,-21600,100),False,True)
    pc.set_control_rotation(u.Rotator(pitch=-12,yaw=-90));pc.set_view_target_with_blend(ch,0);yield 3
    garage=u.GameplayStatics.get_all_actors_of_class(world,u.GTGarage)[0]
    inter=ch.get_interaction();assert inter.get_current_target()==garage,'Service interaction target missing'
    inter.set_hold_input(True);yield .5;inter.set_hold_input(False)
    assert ch.is_station_open();ch.move_station_selection(1);assert ch.act_on_station(),garage.last_message
    car=pc.get_car();assert car.get_class()==garage.vehicles[1].vehicle_class
    assert len(u.GameplayStatics.get_all_actors_of_class(world,u.GTCarPawn))==1
    report['garage_swap']=str(garage.vehicles[1].name)
    yield from capture(world,'ServiceMenu')
    assert pc.enter_vehicle(car);pc.select_lane(1)
    assert not car.get_drivetrain().is_low_range() and not car.get_drivetrain().is_diff_locked()
    world=pc=car=move=camera=labs=ch=garage=inter=None;gc.collect();u.EditorLevelLibrary.editor_end_play();yield 5

def capture(world,name):
    path=QA/(name+'.png');stamp=time.time()
    u.GameplayStatics.set_game_paused(world,True);yield .3
    u.SystemLibrary.execute_console_command(world,'HighResShot 1440x900 filename="'+path.as_posix()+'"',u.GameplayStatics.get_player_controller(world,0))
    until=time.monotonic()+60
    while not path.exists() or path.stat().st_mtime<stamp:assert time.monotonic()<until;yield .2
    report['images'].append(str(path));save();u.GameplayStatics.set_game_paused(world,False);yield .5

def run():
    if MODE=='Install':yield from install()
    elif MODE=='Polish':yield from polish()
    elif MODE=='Recess':yield from recess()
    elif MODE=='Surface':yield from surface_feedback()
    else:yield from review()
    assert hashlib.sha256(protected.read_bytes()).hexdigest()==before
    report['lidar_map_unchanged']=True
    assert L.load_level('/Engine/Maps/Entry');gc.collect();yield 4
    report['ok']=True;save()

save();steps=run();deadline=0.;busy=False;began=time.monotonic()
def tick(dt):
    global deadline,busy,steps
    if busy:return
    busy=True
    try:
        assert time.monotonic()-began<1500,'Rally setup timeout'
        if time.monotonic()>=deadline:deadline=time.monotonic()+next(steps)
    except StopIteration:
        u.unregister_slate_post_tick_callback(handle);steps=None;gc.collect();u.SystemLibrary.quit_editor()
    except Exception:
        report['error']=traceback.format_exc();save();u.log_error(report['error']);u.unregister_slate_post_tick_callback(handle);u.SystemLibrary.quit_editor()
    finally:busy=False
u.EditorPythonScripting.set_keep_python_script_alive(True);handle=u.register_slate_post_tick_callback(tick)
