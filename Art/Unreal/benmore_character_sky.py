"""A map-owned soft cloud layer, ordered after the prototype painted sky."""
import unreal as u
DEST='/Game/GrandTour/Demo/BenmoreRoads/Character'
def build():
    eal=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary;eal.make_directory(DEST);path=DEST+'/M_Benmore_SoftSky'
    m=u.load_asset(path) if eal.does_asset_exist(path) else u.AssetToolsHelpers.get_asset_tools().create_asset('M_Benmore_SoftSky',DEST,u.Material,u.MaterialFactoryNew())
    mel.delete_all_material_expressions(m)
    for k,v in dict(shading_model=u.MaterialShadingModel.MSM_UNLIT,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,two_sided=True,use_translucency_vertex_fog=False,apply_cloud_fogging=False,translucency_pass=u.MaterialTranslucencyPass.MTP_BEFORE_DOF).items():m.set_editor_property(k,v)
    def expr(cls,**kw):
        e=mel.create_material_expression(m,cls)
        for k,v in kw.items():e.set_editor_property(k,v)
        return e
    inputs=[]
    for name in ['P','Camera','Time','CloudCover','SkyScale']:
        i=u.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    code='''struct SkyNoise {
float hash(float3 p) { return frac(sin(dot(p,float3(127.1,311.7,74.7)))*43758.5453); }
float n(float3 p) { float3 i=floor(p),f=frac(p);f=f*f*(3-2*f);
float a=lerp(lerp(hash(i),hash(i+float3(1,0,0)),f.x),lerp(hash(i+float3(0,1,0)),hash(i+float3(1,1,0)),f.x),f.y);
float b=lerp(lerp(hash(i+float3(0,0,1)),hash(i+float3(1,0,1)),f.x),lerp(hash(i+float3(0,1,1)),hash(i+1),f.x),f.y);
return lerp(a,b,f.z); }
float fbm(float3 q) { return .50*n(q)+.26*n(q*2.03)+.14*n(q*4.11)+.07*n(q*8.2)+.03*n(q*16.4); } };SkyNoise f;
float3 d=normalize(P-Camera);float h=saturate(d.z);
float3 sky=lerp(float3(.47,.61,.76),float3(.055,.20,.48),pow(h,.44));
float3 sun=normalize(float3(.511,.730,.454));
float3 q=d*7.5+float3(Time*.0003,Time*.00012,3.7);
float density=f.fbm(q);
float edge=.6*f.n(q*17.1)+.3*f.n(q*34.2)+.1*f.n(q*68.4);
float a=density+(edge-.5)*.045;
float threshold=lerp(.535,.32,saturate(CloudCover));
float clouds=smoothstep(threshold,threshold+.055,a)*smoothstep(.02,.10,h);
// Light-facing density difference supplies body shading rather than a flat white fill.
float light=saturate(.56+(density-f.fbm(q+sun*.60))*5.0);
float rim=(1-smoothstep(threshold+.01,threshold+.10,a))*.08;
float3 cloud=lerp(float3(.24,.31,.41),float3(1.45,1.40,1.29),saturate(light+rim));
float highVeil=smoothstep(.62,.78,f.n(d*float3(14,14,40)+7))*smoothstep(.10,.45,h);
sky=lerp(sky,float3(.64,.72,.82),highVeil*.12);
float3 clear=lerp(sky,cloud,clouds);
return lerp(clear,float3(.37,.41,.46),CloudCover*.3)*lerp(.35,1,saturate(SkyScale))*1.3;'''
    c=expr(u.MaterialExpressionCustom,inputs=inputs,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    for name,cls in [('P',u.MaterialExpressionWorldPosition),('Camera',u.MaterialExpressionCameraPositionWS),('Time',u.MaterialExpressionTime)]:assert mel.connect_material_expressions(expr(cls),'',c,name)
    for name,value in [('CloudCover',.1),('SkyScale',1.)]:assert mel.connect_material_expressions(expr(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value),'',c,name)
    mel.connect_material_property(c,'',u.MaterialProperty.MP_EMISSIVE_COLOR);mel.connect_material_property(expr(u.MaterialExpressionConstant,r=1.),'',u.MaterialProperty.MP_OPACITY)
    assert not mel.recompile_material(m);eal.save_loaded_asset(m)
    act=u.get_editor_subsystem(u.EditorActorSubsystem)
    for a in act.get_all_level_actors():
        if a.get_actor_label()=='Benmore_Character_SoftSky':act.destroy_actor(a)
    a=act.spawn_actor_from_class(u.StaticMeshActor,u.Vector(0,0,0));a.set_actor_label('Benmore_Character_SoftSky');c=a.static_mesh_component
    a.set_editor_property('tags',['GTLook.LocalSky'])
    c.set_collision_profile_name('NoCollision');c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);a.set_actor_enable_collision(False)
    c.set_static_mesh(u.load_asset('/Engine/BasicShapes/Sphere'));c.set_material(0,m)
    for k,v in dict(cast_shadow=False,cast_dynamic_shadow=False,cast_static_shadow=False,affect_dynamic_indirect_lighting=False,affect_distance_field_lighting=False,visible_in_ray_tracing=False,visible_in_reflection_captures=False,visible_in_real_time_sky_captures=False,hidden_in_scene_capture=True,receives_decals=False,translucency_sort_priority=-999).items():c.set_editor_property(k,v)
    a.set_actor_location(u.Vector(0,0,0),False,True);a.set_actor_scale3d(u.Vector(200000,200000,200000));c.set_collision_profile_name('NoCollision');c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);a.set_actor_enable_collision(False)
    return {'radius_km':100,'sort_priority':-999,'collision':'NoCollision','shared_sky_assets_modified':False}
