"""Build the isolated 1 km Mackenzie driving blockout using existing GT terrain APIs."""
import unreal as u
import json, math, os, sys, traceback
from pathlib import Path

ROOT=Path(u.Paths.project_dir()).resolve()
OUT=ROOT/'Art/Export/MackenzieBlockout'; OUT.mkdir(parents=True,exist_ok=True)
DEST='/Game/GrandTour/Demo/MackenzieBlockout'
LEVEL=DEST+'/L_Mackenzie_Blockout'
eal=u.EditorAssetLibrary; mel=u.MaterialEditingLibrary
assets=u.AssetToolsHelpers.get_asset_tools()
act=u.get_editor_subsystem(u.EditorActorSubsystem); les=u.get_editor_subsystem(u.LevelEditorSubsystem)
lib=u.GTVehicleSetupLibrary
report={'ok':False,'level':LEVEL,'revision':'blockout-01'}

def props(obj,**kw):
    for k,v in kw.items(): obj.set_editor_property(k,v)
    return obj

def spawn(cls,label,pos,rot=None):
    ob=act.spawn_actor_from_class(cls,u.Vector(*pos),rot or u.Rotator())
    ob.set_actor_label(label); return ob

def load(path):
    return eal.load_asset(path) if eal.does_asset_exist(path) else None

def smooth(points,closed=False,steps=8):
    result=[]; n=len(points)
    for i in range(n if closed else n-1):
        a,b,c,d=[points[k%n] if closed else points[max(0,min(n-1,k))] for k in [i-1,i,i+1,i+2]]
        for j in range(steps):
            t=j/steps
            result.append(tuple(.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in [0,1]))
    result.append(result[0] if closed else points[-1]); return result

def flat_material(name,color):
    m=load(DEST+'/'+name) or assets.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    c=mel.create_material_expression(m,u.MaterialExpressionConstant3Vector)
    c.set_editor_property('constant',u.LinearColor(*color,1)); mel.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
    r=mel.create_material_expression(m,u.MaterialExpressionConstant); r.set_editor_property('r',.9); mel.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(m); eal.save_loaded_asset(m); return m

def landscape_material():
    m=load(DEST+'/M_BlockoutLandscape') or assets.create_asset('M_BlockoutLandscape',DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    custom=mel.create_material_expression(m,u.MaterialExpressionCustom)
    keys=['WorldPos','Tarmac','Dirt','Mud','Snow','Scrub','Bog']; inputs=[]
    for key in keys: inp=u.CustomInput(); inp.set_editor_property('input_name',key); inputs.append(inp)
    props(custom,inputs=inputs,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,code='''
float broad=0.5+0.5*sin(WorldPos.x/4100.0)*sin(WorldPos.y/5700.0);
float fine=0.5+0.5*sin(WorldPos.x/37.0)*sin(WorldPos.y/53.0);
float3 grass=lerp(float3(.24,.205,.105),float3(.42,.315,.15),broad);
float3 gravel=float3(.285,.27,.235)*(0.88+0.24*fine);
return grass*Scrub+gravel*Dirt+float3(.14,.085,.045)*Mud+float3(.09,.045,.022)*Bog+float3(.08,.085,.09)*Tarmac+float3(.7,.74,.77)*Snow;
''')
    world=mel.create_material_expression(m,u.MaterialExpressionWorldPosition)
    mel.connect_material_expressions(world,'',custom,'WorldPos')
    for key in keys[1:]:
        s=mel.create_material_expression(m,u.MaterialExpressionLandscapeLayerSample)
        s.set_editor_property('parameter_name',key); mel.connect_material_expressions(s,'',custom,key)
    mel.connect_material_property(custom,'',u.MaterialProperty.MP_BASE_COLOR)
    r=mel.create_material_expression(m,u.MaterialExpressionConstant); r.set_editor_property('r',.88)
    mel.connect_material_property(r,'',u.MaterialProperty.MP_ROUGHNESS)
    errors=mel.recompile_material(m); assert not errors,str(errors)
    eal.save_loaded_asset(m); return m

try:
    assert les.load_level(LEVEL) if eal.does_asset_exist(LEVEL) else les.new_level(LEVEL)
    for ob in act.get_all_level_actors():
        if not isinstance(ob,(u.WorldSettings,u.Brush)): act.destroy_actor(ob)
    route=smooth([(-60,-360),(200,-320),(340,-180),(340,20),(260,240),(60,350),(-160,320),(-340,160),(-370,-80),(-280,-330)],True)
    spec=props(u.GTTerrainSpec(),components_per_side=8,subsections_per_component=2,quads_per_subsection=63,
        quad_size_cm=100000/1008,origin_x_cm=-50000.,origin_y_cm=-50000.,z_scale=100.,seed=106,
        base_amplitude_m=3.,base_wavelength_m=260.,octaves=2,persistence=.35,slope_m_per_km=0.,
        road_half_width_m=3.2,shoulder_m=12.,max_grade_percent=10.,route_smooth_m=45.,
        route_m=[u.Vector2D(*p) for p in route],spans=[],sections=[],alt_routes=[],planes=[],stations=[],biomes=[],
        road_roughness_m=.025,track_roughness_m=.08,scrub_roughness_m=.18,ford_roughness_m=.04,
        rally_width_scale=1.,rally_grade_percent=10.,rally_smooth_m=40.,camber_max_degrees=3.,
        verge_ditch_m=.18,verge_bank_m=.22,rally_post_spacing_m=70.,ford_rock_count=0,
        track_stone_spacing_m=0.,water_bar_height_m=.12,track_rut_depth_m=.06,ford_grade_percent=12.,mud_channel_depth_m=100.)
    feature_data=[('RIDGE',(-380,20),(-200,370),240,42),('HILL',(120,310),(0,0),275,24),
                  ('HILL',(190,-420),(0,0),180,9),('HILL',(-480,-290),(0,0),210,20),
                  ('CHANNEL',(110,-80),(510,-80),17,2.8)]
    spec.features=[props(u.GTTerrainFeature(),kind=getattr(u.GTTerrainFeatureKind,kind),start_m=u.Vector2D(*a),end_m=u.Vector2D(*b),radius_m=float(radius),height_m=float(height)) for kind,a,b,radius,height in feature_data]
    length=lib.terrain_route_length_m(spec)
    _,ford_arc=lib.terrain_route_distance_m(spec,35000.,-8000.)
    _,junction_arc=lib.terrain_route_distance_m(spec,34000.,2000.)
    _,rejoin_arc=lib.terrain_route_distance_m(spec,-34000.,16000.)
    ford=props(u.GTRouteSection(),start_m=ford_arc-17,end_m=ford_arc+17,kind=u.GTRouteSectionKind.FORD,depth_m=.28,flow_speed_mps=.35,ford_rock_count_override=0)
    # First blockout tests the firm crossing, with no deformation mesh layered on top.
    deform=u.GTDeformProfile(); deform.mode=u.GTDeformProfileMode.OFF; ford.deform=deform
    spec.sections=[ford]
    spec.spans=[props(u.GTSurfaceSpan(),start_m=0.,end_m=length,layer=1)]
    a,_=lib.terrain_route_point_cm(spec,junction_arc); b,_=lib.terrain_route_point_cm(spec,rejoin_arc)
    shortcut=smooth([(a.x/100,a.y/100),(215,62),(65,65),(-100,95),(-235,135),(b.x/100,b.y/100)],False,5)
    spec.alt_routes=[props(u.GTAltRoute(),points_m=[u.Vector2D(*p) for p in shortcut],half_width_m=2.,layer=1)]
    # The existing generator grades alternative routes independently. Bind the exit to the
    # main road with a long, smooth authored ramp, instead of leaving a cliff at the join.
    altlength=lib.terrain_alt_route_length_m(spec,0)
    ramp_length=350.; ramp_start=altlength-ramp_length
    ramp_a,_=lib.terrain_alt_route_point_cm(spec,0,ramp_start)
    ramp_b,_=lib.terrain_route_point_cm(spec,rejoin_arc)
    distance=math.hypot(ramp_b.x-ramp_a.x,ramp_b.y-ramp_a.y)/100
    grade=(ramp_b.z-ramp_a.z)/(distance*100)
    dx=(ramp_b.x-ramp_a.x)/(distance*100);dy=(ramp_b.y-ramp_a.y)/(distance*100)
    heading=math.degrees(math.atan2(dy,dx));extension=18.
    # A broad graded earthwork carries the slightly wandering track. Level end pads
    # feather its slope into both joins without seams between short ramp segments.
    planes=[props(u.GTTerrainPlane(),start_m=u.Vector2D(ramp_a.x/100-dx*extension,ramp_a.y/100-dy*extension),
        yaw_degrees=heading,length_m=distance+2*extension,half_width_m=18.,base_zm=ramp_a.z/100-grade*extension,
        grade_percent=grade*100,blend_m=18.,roughness_m=.06,layer=-1)]
    for end in [ramp_a,ramp_b]:
        planes.append(props(u.GTTerrainPlane(),start_m=u.Vector2D(end.x/100-dx*8,end.y/100-dy*8),
            yaw_degrees=heading,length_m=16.,half_width_m=8.,base_zm=end.z/100,grade_percent=0.,
            blend_m=25.,roughness_m=.04,layer=-1))
    spec.planes=planes
    sa=load(DEST+'/DA_Mackenzie_Blockout') or assets.create_asset('DA_Mackenzie_Blockout',DEST,u.GTTerrainSpecAsset,u.DataAssetFactory())
    stations=[]
    station_arcs=[('Start',20.),('Ford',ford_arc-35.),('Shortcut',junction_arc-20.),('Ridge',rejoin_arc-270.)]
    for name,arc in station_arcs:
        p,yaw=lib.terrain_route_point_cm(spec,arc)
        stations.append(props(u.GTTerrainStation(),name=name,point_m=u.Vector2D(p.x/100,p.y/100),yaw_degrees=yaw,arc_m=arc,start_ahead_m=0.,note='Mackenzie demo blockout - '+name))
    spec.stations=stations
    props(sa,display_name='Mackenzie Blockout',spec=spec); eal.save_loaded_asset(sa)
    landscape_material()
    dressing=spawn(u.GTTerrainDressing,'TerrainDressing',(0,0,0)); dressing.foliage_density=0.
    builder=spawn(u.GTTerrainBuilder,'TerrainBuilder',(0,0,0))
    props(builder,spec_asset=sa,landscape_material_path=DEST+'/M_BlockoutLandscape',layer_info_folder=DEST+'/Layers',reground_actors=False)
    land=builder.rebuild_landscape(); assert land,builder.last_message
    report['builder']=builder.last_message
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    world.get_world_settings().set_editor_property('default_game_mode',u.GTRunGameMode)
    def height(x,y): return lib.sample_terrain_height_cm(spec,x*100,y*100)
    p,yaw=lib.terrain_route_point_cm(spec,20.)
    spawn(u.PlayerStart,'PlayerStart',(p.x,p.y,p.z+150),u.Rotator(yaw=yaw))
    sun=spawn(u.DirectionalLight,'Sun',(0,0,10000),u.Rotator(pitch=-35,yaw=-55)); sun.light_component.set_intensity(10.5)
    sun.light_component.set_editor_property('light_source_angle',1.5)
    sky=spawn(u.SkyLight,'SkyLight',(0,0,10000)); sky.light_component.set_editor_property('real_time_capture',True); sky.light_component.set_intensity(.65)
    spawn(u.SkyAtmosphere,'SkyAtmosphere',(0,0,0))
    fog=spawn(u.ExponentialHeightFog,'DistanceHaze',(0,0,0)); fog.component.set_editor_property('fog_density',.006)
    pp=spawn(u.PostProcessVolume,'BlockoutExposure',(0,0,0)); pp.unbound=True; pp.priority=200.
    settings=pp.settings
    props(settings,override_auto_exposure_min_brightness=True,auto_exposure_min_brightness=.25,override_auto_exposure_max_brightness=True,auto_exposure_max_brightness=.25,override_auto_exposure_bias=True,auto_exposure_bias=0.)
    pp.settings=settings
    sys.path.insert(0,str(ROOT/'Art/Unreal')); os.environ['GT_M6_AS_MODULE']='1'
    import setup_m6_hide
    water=setup_m6_hide.place_ford_sheet(world,spec,0,ford,eal.load_asset('/Game/GrandTour/Materials/M_GT_Water'))
    wood=flat_material('M_BlockoutPost',(.22,.17,.105)); pale=flat_material('M_BlockoutMarker',(.7,.65,.47)); roof=flat_material('M_BlockoutRoof',(.18,.215,.23))
    cube=u.load_asset('/Engine/BasicShapes/Cube'); cyl=u.load_asset('/Engine/BasicShapes/Cylinder')
    def box(label,x,y,z,size,mat,heading=0,mesh=cube):
        ob=spawn(u.StaticMeshActor,label,(x*100,y*100,z),u.Rotator(yaw=heading)); ob.static_mesh_component.set_static_mesh(mesh); ob.static_mesh_component.set_material(0,mat); ob.set_actor_scale3d(u.Vector(*size)); return ob
    # Guide posts make the route readable at driving speed; all stay outside the 6.4 m road.
    for arc in range(50,int(length),65):
        p,yaw=lib.terrain_route_point_cm(spec,float(arc)); rad=math.radians(yaw)
        for side in [-1,1]:
            x=p.x/100-math.sin(rad)*5.8*side; y=p.y/100+math.cos(rad)*5.8*side
            box('Marker_Route_%s_%s'%(arc,side),x,y,height(x,y)+55,(.13,.13,1.1),pale,mesh=cyl)
    # Small open-front shed is a recognisable start/return landmark.
    sx,sy=-45,-388; z=height(sx,sy)
    box('Start_Shed_Roof',sx,sy,z+320,(8,5,.3),roof)
    box('Start_Shed_Back',sx,sy-2.3,z+150,(8,.2,3),wood)
    for dx in [-3.7,3.7]:
        for dy in [-2.2,2.2]:box('Start_Shed_Post',sx+dx,sy+dy,z+150,(.2,.2,3),wood)
    for name,arc,text in [('Ford',ford_arc-32,'SHALLOW FORD'),('Fork',junction_arc-30,'MAIN LOOP / SHORTCUT'),('Ridge',rejoin_arc-270,'RIDGE LOOKOUT'),('Start',25,'MACKENZIE LOOP')]:
        p,yaw=lib.terrain_route_point_cm(spec,arc); rad=math.radians(yaw)
        x=p.x/100-math.sin(rad)*8.; y=p.y/100+math.cos(rad)*8.; z=height(x,y)
        box('Sign_'+name,x,y,z+140,(.18,.18,2.8),wood)
        sign=spawn(u.TextRenderActor,'Label_'+name,(x*100,y*100,z+230),u.Rotator(yaw=yaw+180))
        sign.text_render.set_text(text); sign.text_render.set_world_size(30.)
    # Tree silhouettes only: art placement will follow the route review.
    tree=u.load_asset('/Game/GrandTour/ArtTests/RoadFordStyle/SM_RF_Willow_Mature')
    if tree:
        p,yaw=lib.terrain_route_point_cm(spec,ford_arc)
        for i,(dx,dy,scale) in enumerate([(-13,-24,.9),(15,-25,.8),(-15,26,1.),(19,28,.85)]):
            x,y=p.x/100+dx,p.y/100+dy
            ob=spawn(u.StaticMeshActor,'Placeholder_Willow_'+str(i),(x*100,y*100,height(x,y)),u.Rotator(yaw=i*71)); ob.static_mesh_component.set_static_mesh(tree); ob.set_actor_scale3d(u.Vector(scale,scale,scale))
    camera=spawn(u.CameraActor,'Overview',(85000,-100000,95000))
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(camera.get_actor_location(),u.Vector(0,0,1200)),False); camera.camera_component.set_field_of_view(55)
    u.get_editor_subsystem(u.UnrealEditorSubsystem).set_level_viewport_camera_info(camera.get_actor_location(),camera.get_actor_rotation())
    samples=[]
    for arc in range(0,int(length)+1,5):
        p,yaw=lib.terrain_route_point_cm(spec,float(arc)); samples.append({'arc_m':arc,'x_m':p.x/100,'y_m':p.y/100,'z_m':p.z/100,'yaw':yaw})
    grades=[abs(b['z_m']-a['z_m'])/5*100 for a,b in zip(samples,samples[1:])]
    shortcut_samples=[]
    altlength=lib.terrain_alt_route_length_m(spec,0)
    for arc in range(0,int(altlength)+1,5):
        p,yaw=lib.terrain_alt_route_point_cm(spec,0,float(arc)); shortcut_samples.append({'arc_m':arc,'x_m':p.x/100,'y_m':p.y/100,'z_m':p.z/100,'yaw':yaw})
    p,yaw=lib.terrain_alt_route_point_cm(spec,0,altlength)
    shortcut_samples.append({'arc_m':altlength,'x_m':p.x/100,'y_m':p.y/100,'z_m':p.z/100,'yaw':yaw})
    assert all(math.isfinite(row[k]) for row in samples+shortcut_samples for k in ['x_m','y_m','z_m'])
    assert max(abs(row[k]) for row in samples+shortcut_samples for k in ['x_m','y_m'])<480
    assert max(grades)<18.,'Unexpected route grade: '+str(max(grades))
    assert les.save_current_level()
    report.update(ok=True,side_m=1000,height_samples=1009,route_length_m=length,shortcut_length_m=altlength,
        road_width_m=6.4,shortcut_width_m=4.,ford_arc_m=ford_arc,ford_depth_m=.28,max_sampled_grade_percent=max(grades),
        route_elevation_range_m=[min(p['z_m'] for p in samples),max(p['z_m'] for p in samples)],
        stations=[{'name':name,'arc_m':arc} for name,arc in station_arcs],route=samples,shortcut=shortcut_samples,
        ford_water_level_cm=water.base_level_cm,actors=len(act.get_all_level_actors()),notes=['No Gaea terrain yet','Firm ford bed, deformation disabled for this blockout','Legacy willow silhouettes are placeholders'])
except Exception:
    report['error']=traceback.format_exc(); u.log_error(report['error'])
finally:
    (OUT/'setup-report.json').write_text(json.dumps(report,indent=2)); u.log('MACKENZIE_SETUP '+json.dumps({k:v for k,v in report.items() if k not in ['route','shortcut']})); u.SystemLibrary.quit_editor()
