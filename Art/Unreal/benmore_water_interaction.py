"""Stage 95: amplify local physical wakes and transported aeration, without changing the solver."""
import unreal as u
from benmore_river_life_materials import Graph,props
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
SRC='/Game/GrandTour/Demo/BenmoreRoads/Gaea/FlowWaves'
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/WaterInteraction'

def make_spray():
    folder='/Game/GrandTour/Materials';name='M_GT_WaterSpray'
    m=u.load_asset(folder+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.Material,u.MaterialFactoryNew())
    for n in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,n)
    props(m,blend_mode=u.BlendMode.BLEND_TRANSLUCENT,shading_model=u.MaterialShadingModel.MSM_DEFAULT_LIT,
        two_sided=False,translucency_lighting_mode=u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    g=Graph(m,'WaterSpray')
    colour=g.node(u.MaterialExpressionVectorParameter,parameter_name='BaseColor',default_value=u.LinearColor(.72,.80,.77,1))
    alpha=g.node(u.MaterialExpressionScalarParameter,parameter_name='Opacity',default_value=.82)
    rough=g.scalar(.7)
    edge=g.custom(['UV','Alpha','Density','Family','Seed'],'''
struct SprayMask {
 float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
};SprayMask mask;
float2 q=UV*2-1;
float grain=mask.n(UV*9+Seed*31);
float fine=mask.n(UV*23+Seed*17);
float radial=saturate(1-dot(q,q));
float coverage=pow(radial,1.2);
if(Family>.5 && Family<1.5){
 float fanWidth=.18+.82*UV.x;
 float flank=1-smoothstep(.55,1,abs(q.y)/fanWidth);
 float lengthMask=smoothstep(0,.14,UV.x)*(1-smoothstep(.55+.22*grain,1,UV.x));
 coverage=flank*lengthMask*smoothstep(.23,.64,grain*.75+fine*.25);
}else if(Family>1.5){
 coverage=pow(radial,2.2)*lerp(.35,1,grain);
}else{
 coverage*=lerp(.7,1,fine);
}
return coverage*Alpha*Density;
''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(g.node(u.MaterialExpressionTextureCoordinate),edge,'UV');g.wire(alpha,edge,'Alpha')
    g.wire(g.node(u.MaterialExpressionPerInstanceRandom),edge,'Seed')
    g.wire(g.node(u.MaterialExpressionPerInstanceCustomData,data_index=0,const_default_value=1),edge,'Density')
    g.wire(g.node(u.MaterialExpressionPerInstanceCustomData,data_index=1,const_default_value=0),edge,'Family')
    fade=g.node(u.MaterialExpressionDepthFade,fade_distance_default=12);g.wire(edge,fade,next(pin for pin in mel.get_material_expression_input_names(fade) if 'opacity' in pin.lower()))
    g.output(colour,u.MaterialProperty.MP_BASE_COLOR);g.output(rough,u.MaterialProperty.MP_ROUGHNESS)
    g.output(g.scalar(.05),u.MaterialProperty.MP_SPECULAR);g.output(fade,u.MaterialProperty.MP_OPACITY)
    mel.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

def make(kind):
    name='M_GC_Domain'+kind
    source=u.load_asset(SRC+'/'+name);assert source
    m=u.load_asset(DEST+'/'+name) or eal.duplicate_asset(SRC+'/'+name,DEST+'/'+name)
    g=Graph(m,'WaterInteraction')
    wpo=mel.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    original_wpo=mel.get_material_property_input_node(source,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    original_pixel=mel.get_material_property_input_node(source,u.MaterialProperty.MP_BASE_COLOR)
    pixel=mel.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
    for n in [wpo,pixel]:
        inputs=list(n.get_editor_property('inputs'))
        if 'WakeReady' not in {str(i.get_editor_property('input_name')) for i in inputs}:
            inputs.append(props(u.CustomInput(),input_name='WakeReady'));n.set_editor_property('inputs',inputs)
            g.wire(g.node(u.MaterialExpressionScalarParameter,parameter_name='WakeDetailReady',default_value=0),n,'WakeReady')
    code=str(original_wpo.get_editor_property('code'))
    assert 'return offset;' in code
    code=code.replace('return offset;', '''
// B is signed EXTRA height, quarter-centimetre units with exactly neutral byte 128.
// Native continuous river mesh and the lake's local mesh read the same field.
[branch]if(WakeReady>.5 && inside>.5 && (Local>.5 || inBake>.5)) {
 float extra=(Texture2DSampleLevel(Detail,DetailSampler,uv,0).b*255-128)*.25;
 offset.z+=extra*smoothstep(0,600,min(edge.x,edge.y));
}
return offset;''')
    wpo.set_editor_property('code',code)
    code=str(original_pixel.get_editor_property('code'))
    assert 'DetailEnabled>.5 && (Local>.5 || inBake>.5)' in code
    old='Normal=normalize(float3(-slope+detail,1));';assert old in code
    code=code.replace(old, '''
[branch]if(WakeReady>.5 && physicalWeight>.001) {
 float2 du=float2(1/FieldTexels.x,0),dv=float2(0,1/FieldTexels.y);
 float hl=Texture2DSampleLevel(Detail,DetailSampler,uv-du,0).b;
 float hr=Texture2DSampleLevel(Detail,DetailSampler,uv+du,0).b;
 float hd=Texture2DSampleLevel(Detail,DetailSampler,uv-dv,0).b;
 float ht=Texture2DSampleLevel(Detail,DetailSampler,uv+dv,0).b;
 slope+=float2(hr-hl,ht-hd)*(255*.25)/(2*cell)*physicalWeight;
}
Normal=normalize(float3(-slope+detail,1));''')
    old='foam=saturate(foam+trail.x*FoamGain*(.25+.75*bubble)*nearFade);';assert old in code
    code=code.replace(old,'''struct WakeAeration {
 float h(float2 p){return frac(sin(dot(p,float2(127.1,311.7)))*43758.5453);}
 float n(float2 p){float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);return lerp(lerp(h(i),h(i+float2(1,0)),f.x),lerp(h(i+float2(0,1)),h(i+1),f.x),f.y);}
};WakeAeration aeration;
// Transport comes from the persistent detail field. Multiplying varying local
// velocity by absolute time stretches a procedural mask into contour stripes.
float2 foamUV=(q-float2(.11,-.08)*Time)*3.2;
float flecks=aeration.n(foamUV)*.7+aeration.n(foamUV*2.3+13)*.3;
float interactionFoam=smoothstep(.04,.55,trail.x*FoamGain)*smoothstep(.27,.68,flecks)*nearFade;
foam=saturate(foam+interactionFoam);''')
    code=code.replace('+foam*.3','+foam*.70').replace('+foam*.16','+foam*.34')
    old='return lerp(colour,float3(.35,.39,.36),foam);';assert old in code
    code=code.replace(old,'return lerp(colour,lerp(float3(.35,.39,.36),float3(.62,.69,.65),saturate(interactionFoam*2)),foam);')
    pixel.set_editor_property('code',code)
    for prop,out in [(u.MaterialProperty.MP_NORMAL,'Normal'),(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_OPACITY,'Opacity')]:g.output(pixel,prop,out)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m)
    return m
