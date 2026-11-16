"""Map-local, bounded foliage wind and shader-animated falling leaf instances."""
import unreal as u,json,hashlib,random,math
from pathlib import Path
from benmore_river_life_materials import Graph,props
import flora_ground_patches as ground
import flora_woodland_materials as wood
R=Path('C:/GrandTour');O=Path('D:/GrandTourAssets/ReviewEvidence/FloraTrail/Motion')
CFG=json.loads((R/'Art/flora_motion_settings.json').read_text())
D='/Game/GrandTour/ArtTests/FloraTrail/Woodland/Motion/'+CFG['revision']
BASE=ground.MAP;MAP=D+'/L_FloraTrail_Motion'
E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
PLANTS={'SM_Exact_tree':3.,'SM_Exact_pine_f002':3.,'SM_Exact_fern':1.7,'SM_Exact_shrub':1.5,'SM_Exact_grass':2.,'SM_Exact_drygrass':1.7}

def slots(world):
    result=[]
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        for c in a.get_components_by_class(u.StaticMeshComponent):
            if not c.static_mesh or c.static_mesh.get_name() not in PLANTS:continue
            for i,m in enumerate(c.get_materials()):
                if isinstance(m,u.Material) and m.get_editor_property('blend_mode')==u.BlendMode.BLEND_MASKED:result.append((a.get_actor_label(),c,i,m))
    return result

def time_node(g):
    real=g.node(u.MaterialExpressionTime)
    override=g.node(u.MaterialExpressionScalarParameter,parameter_name='FloraTimeOverride',default_value=-1.)
    node=g.custom(['T','Override'],'return Override>=0.?Override:T;',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(real,node,'T');g.wire(override,node,'Override');return node

def signature(m):
    names=('MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_SPECULAR','MP_OPACITY_MASK','MP_SUBSURFACE_COLOR','MP_AMBIENT_OCCLUSION','MP_EMISSIVE_COLOR')
    outputs={}
    for name in names:
        p=getattr(u.MaterialProperty,name);n=M.get_material_property_input_node(m,p)
        outputs[name]=[n.get_name() if n else None,str(M.get_material_property_input_node_output_name(m,p))]
    textures=[(n.get_name(),n.get_editor_property('texture').get_path_name() if n.get_editor_property('texture') else None) for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSample)]
    return {'outputs':outputs,'textures':textures}

def wind(source,amount):
    path=D+'/M_Wind_'+hashlib.sha1(source.get_path_name().encode()).hexdigest()[:8]
    m=u.load_asset(path)
    if not m:
        m=E.duplicate_asset(source.get_path_name().split('.')[0],path);assert m
        g=Graph(m,'FloraMotion')
        pos=g.node(u.MaterialExpressionPreSkinnedPosition);bounds=g.node(u.MaterialExpressionBounds)
        q=g.custom(['P','Lo','Hi'],'return saturate((P-Lo)/max(Hi-Lo,float3(1,1,1)));')
        g.wire(pos,q,'P');g.wire(bounds,q,'Lo','Min');g.wire(bounds,q,'Hi','Max')
        amp=g.node(u.MaterialExpressionScalarParameter,parameter_name='FloraWindCm',default_value=amount)
        enabled=g.node(u.MaterialExpressionScalarParameter,parameter_name='FloraWindEnabled',default_value=1.)
        node=g.custom(['P','Local','Q','Camera','T','Amount','Enabled','Seed'],'''#if SHADOW_DEPTH_SHADER
// Keep cached canopy shadows stable; leaf flutter is a small visual offset.
return float3(0,0,0);
#else
float fade=1.-smoothstep('''+str(CFG['wind_fade_start_cm'])+''','''+str(CFG['wind_fade_end_cm'])+''',distance(P,Camera));
float root=smoothstep(.02,.60,Q.z);
float phase=Seed*6.283185+dot(P.xy,float2(.0011,.0007));
float gust=sin(T*.83+phase)*.65+sin(T*1.31+phase*.73)*.35;
float flutter=sin(T*3.8+dot(Local,float3(.027,.019,.013))+Seed*11.);
float3 offset=float3(.88,.38,.04)*gust*Amount*root;
offset+=float3(.18,-.32,.32)*flutter*Amount*root;
return offset*fade*saturate(Enabled);
#endif''')
        for n,pin,out in [(g.node(u.MaterialExpressionWorldPosition),'P',''),(pos,'Local',''),(q,'Q',''),(g.node(u.MaterialExpressionCameraPositionWS),'Camera',''),(time_node(g),'T',''),(amp,'Amount',''),(enabled,'Enabled',''),(g.node(u.MaterialExpressionPerInstanceRandom),'Seed','')]:g.wire(n,node,pin,out)
        g.output(node,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
        props(m,max_world_position_offset_displacement=8.)
        E.set_metadata_tag(m,'FloraMotionSource',source.get_path_name())
    assert signature(m)==signature(source)
    assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
    return m

def leaf_material():
    path=D+'/M_FallingLeaves';m=u.load_asset(path)
    if m:return m
    m=u.AssetToolsHelpers.get_asset_tools().create_asset('M_FallingLeaves',D,u.Material,u.MaterialFactoryNew());assert m
    props(m,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.4,two_sided=True,shading_model=u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE,tangent_space_normal=False,max_world_position_offset_displacement=1250.)
    g=Graph(m,'FallingLeaves');uv=g.node(u.MaterialExpressionTextureCoordinate)
    atlas=g.custom(['UV'],'return float2(.326,.019)+UV*float2(.072,.087);',u.CustomMaterialOutputType.CMOT_FLOAT2)
    g.wire(uv,atlas,'UV')
    mask=g.node(u.MaterialExpressionTextureSample,texture=u.load_asset('/Game/GrandTour/ArtTests/FloraTrail/PineTrial/SourceMatch/T_SourceMask4K'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    g.wire(atlas,mask,'UVs')
    seed=g.node(u.MaterialExpressionPerInstanceRandom);t=time_node(g)
    age=g.custom(['T','Seed'],'return frac(T/lerp(13.,19.,Seed)+Seed);',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(t,age,'T');g.wire(seed,age,'Seed')
    colour=g.custom(['Seed','UV'],'''float3 olive=float3(.18,.23,.055),ochre=float3(.38,.19,.045),coral=float3(.34,.10,.055);
float3 c=Seed<.68?lerp(olive,ochre,Seed/.68):lerp(ochre,coral,(Seed-.68)/.32);
return c*lerp(.78,1.1,saturate(UV.y));''')
    g.wire(seed,colour,'Seed');g.wire(uv,colour,'UV');g.output(colour,u.MaterialProperty.MP_BASE_COLOR)
    sub=g.custom(['C'],'return C*.12;');g.wire(colour,sub,'C');g.output(sub,u.MaterialProperty.MP_SUBSURFACE_COLOR)
    g.output(g.scalar(.88),u.MaterialProperty.MP_ROUGHNESS);g.output(g.scalar(.03),u.MaterialProperty.MP_SPECULAR)
    origin=g.node(u.MaterialExpressionObjectPositionWS);camera=g.node(u.MaterialExpressionCameraPositionWS)
    pixel_origin=g.node(u.MaterialExpressionVertexInterpolator)
    pins=M.get_material_expression_input_names(pixel_origin)
    g.wire(origin,pixel_origin,str(pins[0]) if pins else '')
    opacity=g.custom(['A','Age','P','Camera'],'''float fade=1.-smoothstep('''+str(CFG['leaf_fade_start_cm'])+''','''+str(CFG['leaf_fade_end_cm'])+''',distance(P.xy,Camera.xy));
return A*smoothstep(0.,.045,Age)*(1.-smoothstep(.90,1.,Age))*fade;''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    for n,pin,out in [(mask,'A','R'),(age,'Age',''),(pixel_origin,'P',''),(camera,'Camera','')]:g.wire(n,opacity,pin,out)
    g.output(opacity,u.MaterialProperty.MP_OPACITY_MASK)
    # Plane instances have zero rotation and uniform scale. World vertex minus
    # instance origin therefore gives the card-local vector in centimetres.
    motion=g.custom(['P','Origin','Age','T','Seed'],'''float3 v=P-Origin;
float spin=T*(.65+Seed*.6)+Seed*6.283185;
float c=cos(spin),s=sin(spin),tilt=.9+sin(T*1.8+Seed*9.)*.9;
float3 card=float3(v.x*c-v.y*s,(v.x*s+v.y*c)*cos(tilt),(v.x*s+v.y*c)*sin(tilt));
float phase=Seed*6.283185;
float3 drift=float3(sin(T*.63+phase)*65.+Age*110.,cos(T*.49+phase)*50.+Age*45.,-Age*900.);
return card-v+drift;''')
    for n,pin in [(g.node(u.MaterialExpressionWorldPosition),'P'),(origin,'Origin'),(age,'Age'),(t,'T'),(seed,'Seed')]:g.wire(n,motion,pin)
    g.output(motion,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    normal=g.custom(['T','Seed'],'''float b=.9+sin(T*1.8+Seed*9.)*.9;
return float3(0,-sin(b),cos(b));''')
    g.wire(t,normal,'T');g.wire(seed,normal,'Seed');g.output(normal,u.MaterialProperty.MP_NORMAL)
    M.set_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES)
    assert not M.recompile_material(m);assert E.save_loaded_asset(m,False)
    return m

def install(world):
    for a,c,i,m in slots(world):
        c.set_material(i,wind(m,PLANTS[c.static_mesh.get_name()]))
        props(c,world_position_offset_disable_distance=CFG['wind_disable_cm'],shadow_cache_invalidation_behavior=u.ShadowCacheInvalidationBehavior.RIGID)
    actor=u.GTVehicleSetupLibrary.spawn_actor_of_class(world,u.Actor,u.Transform(),'FloraMotion_FallingLeaves')
    surface=u.GameplayStatics.get_all_actors_of_class(world,u.GTLandscapeSurface)[0]
    rng=random.Random(419);transforms=[]
    # Six local clusters along the drivable route, rather than a world-wide emitter.
    for i in range(CFG['leaf_count']):
        x=(-1700,-1000,-300,400,1100,1800)[i%6]+rng.uniform(-220,220)
        centre=530*math.sin((x+2200)/1050)-150
        y=centre+rng.choice((-1,1))*rng.uniform(130,480)
        floor=surface.contact_height_cm(u.Vector2D(x,y),False)
        transforms.append(u.Transform(location=u.Vector(x,y,floor+930.),scale=u.Vector(*([rng.uniform(.10,.17)]*3))))
    mesh=u.load_asset('/Engine/BasicShapes/Plane')
    c=u.GTVegetationSubsystem.add_tagged_instances(actor,mesh,transforms,'FloraFallingLeaves','NoCollision',False)
    c.set_material(0,leaf_material());c.set_cull_distances(CFG['leaf_cull_cm']-500,CFG['leaf_cull_cm'])
    props(c,visible_in_ray_tracing=False,affect_distance_field_lighting=False,cast_shadow=False)
    actor.set_actor_tick_enabled(False)

def leaf_components(world):
    return [c for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_actor_label()=='FloraMotion_FallingLeaves' for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]

def geometry(world):
    rows=[r for r in ground.geometry(world) if r['actor']!='FloraMotion_FallingLeaves']
    data=json.dumps(rows)
    for root in (BASE,MAP):data=data.replace(root+'.'+root.rsplit('/',1)[-1],'<ReviewWorld>').replace(root,'<ReviewMap>')
    return json.loads(data)
