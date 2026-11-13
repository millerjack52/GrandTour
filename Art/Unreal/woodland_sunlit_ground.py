"""UE daylight adapter: recovered clay noise, clay detail normals and patchy wet film.

This lighting model is authored, not recovered MudRunner shader arithmetic.
Native pigments, clod WPO, terrain updates and water shaders remain upstream.
"""
import unreal as u
from benmore_river_life_materials import Graph, props
import benmore_woodland_materials as mat
mel=u.MaterialEditingLibrary
TAG='WoodlandSunlitGround'

CODE=r'''
float4 s=Texture2DSampleLevel(Style,StyleSampler,saturate((P.xy+125000)/250000),0);
float2 fieldUV=(P.xy-Window.xy)/max(Window.z,1);
float valid=Ready*(all(fieldUV>=0)&&all(fieldUV<=1));
float4 live=Texture2DSampleLevel(Field,FieldSampler,saturate(fieldUV),0)*valid;
float2 uv=(P.xy-live.gb)*.0024;
float2 e=float2(.0024*1.5,0);
// Green is source vertical displacement, not brightness-derived albedo height.
float l=Texture2DSample(Clay,ClaySampler,uv-e).g;
float r=Texture2DSample(Clay,ClaySampler,uv+e).g;
float d=Texture2DSample(Clay,ClaySampler,uv-e.yx).g;
float t=Texture2DSample(Clay,ClaySampler,uv+e.yx).g;
float h=Texture2DSample(Clay,ClaySampler,uv).g;
float broad=Texture2DSample(Clay,ClaySampler,P.xy/190.).g;
float region=min(length(P.xy-float2(-76250,-43375)),min(length(P.xy-float2(-68000,22000)),length(P.xy-float2(-59550,-59475))));
float enabled=Strength*lerp(1,1-smoothstep(2500,3500,region),ReviewOnly);
float soil=(1-s.r)*(1-s.a);
float nearDetail=1-smoothstep(1400,3000,length(Camera-P));
// Analytic texture filtering plus distance fade avoids unresolved glints.
float2 slope=float2(r-l,t-d)*(.9/3.)*soil*(1-.45*s.g)*nearDetail;
// Absorbed moisture stays rough. Free surface film is confined to low patches.
float cavity=1-smoothstep(.35,.65,h);
float depression=smoothstep(1,12,max(0,-live.r));
float film=smoothstep(.58,.86,s.b)*smoothstep(.52,.72,broad)*cavity*soil*(1-s.g)*lerp(.35,1,depression);
// Only the scan's normal/roughness are used. Native pigments stay untouched.
float2 claySlope=Detail.xy/max(Detail.z,.3)*.70*soil*(1-.5*s.g)*nearDetail;
claySlope*=lerp(1,.45,saturate(live.a))*lerp(1,.35,film);
float3 detailed=normalize(float3(N.xy+(claySlope-slope)*N.z,N.z));
float dryRough=clamp(.76+.18*DetailRough+.06*(h-.5)+.06*s.g,.76,.98);
Rough=lerp(.78,lerp(dryRough,.47,film),enabled);
AO=lerp(1,1-.10*cavity*soil*nearDetail,enabled);
return normalize(lerp(N,detailed,enabled));
'''

def patch(m,style):
    # The saved passthroughs are intact baseline inputs, never our own output.
    nodes=list(mel.get_material_expressions(m))
    for n in nodes:
        if str(n.get_editor_property('desc'))==TAG:mel.delete_material_expression(m,n)
    for n in mel.get_material_expressions(m):
        if isinstance(n,u.MaterialExpressionCustom):
            code=str(n.get_editor_property('code'))
            # Match the opt-in CPU grass/soil split, including the tread ribbon.
            code=code.replace('saturate(1-sandCover-grassCover)','saturate(1-sandCover)')
            code=code.replace('(1-style.r)*(1-style.g)*(1-style.a)','(1-style.r)*(1-style.a)')
            n.set_editor_property('code',code)
        if isinstance(n,(u.MaterialExpressionTextureObject,u.MaterialExpressionTextureObjectParameter)):
            tex=n.get_editor_property('texture')
            if tex and tex.get_name() in ['T_style','T_style_groundstudy']:n.set_editor_property('texture',style)
    if m.get_name()=='M_Tread':return mat.save(m)
    nodes=list(mel.get_material_expressions(m))
    source=next((n for n in nodes if str(n.get_editor_property('desc'))=='WoodlandSoilDetailSource:Normal'),None)
    if not source:
        original=mel.get_material_property_input_node(m,u.MaterialProperty.MP_NORMAL)
        output=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_NORMAL)
        saved=Graph(m,'WoodlandSoilDetailSource:Normal')
        source=saved.custom(['Value'],'return Value;');saved.wire(original,source,'Value',output)
    noise=next(n.texture for n in nodes if isinstance(n,u.MaterialExpressionTextureObject) and n.texture and 'env_mud_noise' in n.texture.get_name())
    # Owned copy with mip filtering; original geometry source texture is unchanged.
    clay=u.load_asset(mat.BASE+'/T_ClayLighting') or u.EditorAssetLibrary.duplicate_asset(noise.get_path_name().split('.')[0],mat.BASE+'/T_ClayLighting')
    props(clay,srgb=False,mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,filter=u.TextureFilter.TF_TRILINEAR,address_x=u.TextureAddress.TA_WRAP,address_y=u.TextureAddress.TA_WRAP)
    assert u.EditorAssetLibrary.save_loaded_asset(clay)
    g=Graph(m,TAG)
    n=g.custom(['P','N','Camera','Style','Clay','Strength','ReviewOnly','Field','Window','Ready','Detail','DetailRough'],CODE,outputs=[('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    inputs={'P':g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS),
            'N':source,'Camera':g.node(u.MaterialExpressionCameraPositionWS),
            'Style':g.node(u.MaterialExpressionTextureObject,texture=style,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
            'Clay':g.node(u.MaterialExpressionTextureObject,texture=clay,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
            'Strength':g.node(u.MaterialExpressionScalarParameter,parameter_name='WoodlandSurfaceDetail',default_value=1),
            'ReviewOnly':g.node(u.MaterialExpressionScalarParameter,parameter_name='WoodlandGroundReviewOnly',default_value=1)}
    for key in ['Field','Window','Ready']:
        inputs[key]=next(e for e in nodes if isinstance(e,(u.MaterialExpressionTextureObjectParameter,u.MaterialExpressionVectorParameter,u.MaterialExpressionScalarParameter)) and str(e.get_editor_property('parameter_name'))=='GTLS_'+key)
    uv=g.custom(['P','Field','Window','Ready'],'''float2 q=(P.xy-Window.xy)/max(Window.z,1);float inside=Ready*(all(q>=0)&&all(q<=1));float2 shift=Texture2DSampleLevel(Field,FieldSampler,saturate(q),0).gb*inside;return (P.xy-shift)/125.;''',u.CustomMaterialOutputType.CMOT_FLOAT2)
    for pin in ['P','Field','Window','Ready']:g.wire(inputs[pin],uv,pin)
    normal=u.load_asset('/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/T_brown_mud_02_nor_dx')
    rough=u.load_asset('/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/T_brown_mud_02_Rough')
    assert normal and rough
    inputs['Detail']=g.tex(normal,uv,True)
    inputs['DetailRough']=g.tex(rough,uv)
    inputs['DetailRough'].set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    for pin,node in inputs.items():g.wire(node,n,pin,'R' if pin=='DetailRough' else '')
    for prop,pin in [(u.MaterialProperty.MP_NORMAL,''),(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_AMBIENT_OCCLUSION,'AO')]:g.output(n,prop,pin)
    return mat.save(m)

def install(style):
    return [patch(u.load_asset(mat.BASE+'/M_'+name),style).get_path_name() for name in ['Terrain','Detail','Tread']]
