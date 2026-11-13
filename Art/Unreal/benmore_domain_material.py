"""Continuous water shading and a single exact cutout for the moving simulation mesh."""
import unreal as u
from benmore_river_life_materials import Graph,props
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/RiverScale'
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary

REGION='''
float2 uv=(P.xy-FieldMin.xy)/FieldSize.xy;
float2 cell=FieldSize.xy/FieldTexels.xy;
float2 edge=min(P.xy-FieldMin.xy-cell*.5,FieldMin.xy+FieldSize.xy-cell*.5-P.xy);
float inside=Active*step(0,min(edge.x,edge.y));
float4 live=float4(0,0,0,0);
[branch]if(inside>.5)live=Texture2DSampleLevel(Field,FieldSampler,uv,0);
'''

def make(kind):
    name='M_RS_Domain'+kind
    path=DEST+'/'+name
    # Preserve the refined lake-mouth coverage graph on the static lake.
    source=DEST+('/M_RS_Lake' if kind=='Lake' else '/M_RS_Stream')
    m=u.load_asset(path) or eal.duplicate_asset(source,path)
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='WaterDomain':mel.delete_material_expression(m,n)
    old=next((n for n in mel.get_material_expressions(m) if str(n.get_editor_property('desc')).startswith('DomainOriginalMask|')),None)
    if old:oldout=str(old.get_editor_property('desc')).split('|',1)[1]
    else:
        old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK);oldout=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK)
        old.set_editor_property('desc','DomainOriginalMask|'+oldout)
    g=Graph(m,'WaterDomain');props(m,tangent_space_normal=False,opacity_mask_clip_value=.5)
    # The static lake and the moving river mesh must use identical underwater optics;
    # otherwise the moving window and the outlet read as separate coloured sheets.
    water=next(n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionSingleLayerWaterMaterialOutput))
    clean=lambda s:''.join(c.lower() for c in s if c.isalnum())
    for pin,value in [('Scattering Coefficients',(.00025,.00060,.00045)),('Absorption Coefficients',(.003,.0015,.001)),('Color Scale Behind Water',(.95,.98,.96))]:
        actual=next(n for n in mel.get_material_expression_input_names(water) if clean(n)==clean(pin));g.wire(g.vector(value),water,actual)
    actual=next(n for n in mel.get_material_expression_input_names(water) if clean(n)=='phaseg');g.wire(g.scalar(.08),water,actual)
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    inputs={'P':p,'Time':g.node(u.MaterialExpressionTime),'Camera':g.node(u.MaterialExpressionCameraPositionWS)}
    for key,val in [('FieldMin',(0,0,0,0)),('FieldSize',(6000,6000,0,0)),('FieldTexels',(96,96,0,0))]:
        inputs[key]=g.node(u.MaterialExpressionVectorParameter,parameter_name=key,default_value=u.LinearColor(*val))
    for key,param,val in [('Active','FieldActive',0),('Local','LocalSurface',0),('Level','FieldLevelCm',0),('DetailEnabled','DetailEnabled',1),('FoamGain','FoamGain',4),('SedimentGain','SedimentGain',2),('Turbidity','WaterTurbidity',1),('Motion','SurfaceMotion',1),('TimeOverride','WaterTimeOverride',-1)]:
        inputs[key]=g.node(u.MaterialExpressionScalarParameter,parameter_name=param,default_value=val)
    for key,path in [('Field','/Engine/EngineResources/WhiteSquareTexture'),('Detail','/Engine/EngineResources/WhiteSquareTexture'),('Ripple','/Game/GrandTour/Textures/Water/T_GT_Water_N'),('Baked',DEST+'/T_RS_DomainFlow')]:
        inputs[key]=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name=key+'Tex' if key!='Field' else 'FieldTex',texture=u.load_asset(path),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Ripple' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    args=list(inputs)
    wpo=g.custom(args,REGION+'return Local>.5 && inside>.5 ? float3(0,0,live.r+Level-P.z) : float3(0,0,0);')
    for key,n in inputs.items():g.wire(n,wpo,key)
    g.output(wpo,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    code=REGION+'''
// Review-only time override permits repeatable motion captures; normal play uses Time.
Time=TimeOverride>=0 ? TimeOverride : Time;
Turbidity=saturate(Turbidity);Motion=saturate(Motion);
float2 buv=(P.xy*.01-float2(-1480,-300)+.625)/float2(1261.25,1076.25);
float inBake=step(0,min(buv.x,buv.y))*step(max(buv.x,buv.y),1);
float4 flow=Texture2DSampleLevel(Baked,BakedSampler,saturate(buv),0);
flow=lerp(float4(.5,.5,.75,0),flow,inBake);
float2 velocity=(flow.rg-.5)*4;
float depth=flow.b*2;
if(Local>.5){velocity=live.ba*.01;depth=live.g*.01;}
float dist=length(Camera-P)*.01;
float speed=length(velocity),nearFade=1-smoothstep(65,260,dist);
float2 q=P.xy*.01;
float t0=frac(Time/4.7),t1=frac(Time/4.7+.5),blend=abs(t0*2-1);
float2 drift=velocity+lerp(float2(.025,.009),float2(.12,.055),Motion);
float2 a=q-drift*t0*4.7,b=q-drift*t1*4.7;
float2 footprint=max(abs(ddx(q)),abs(ddy(q)));
float tile=lerp(3.8,2.6,Motion);
float mip=max(0,log2(max(max(footprint.x,footprint.y)*2048/tile,1)));
float2 detail=0;
float bubble=0;
float rippleShade=0;
[branch]if(nearFade>.001){
float2 n0=lerp(Texture2DSampleLevel(Ripple,RippleSampler,a/tile,mip).rg,Texture2DSampleLevel(Ripple,RippleSampler,b/tile,mip).rg,blend)*2-1;
float2 n1=Texture2DSampleLevel(Ripple,RippleSampler,(q.yx+lerp(float2(.023,-.017),-drift.yx*.63,Motion)*Time)/9.1,max(0,mip-log2(9.1/tile))).rg*2-1;
// This sourced rain-ripple normal is unusually soft (RG sigma ~0.019 before mips).
// Preserve it, but supply enough gain for its current-driven motion to survive filtering.
float strength=lerp(lerp(.025,.065,saturate(speed)),lerp(2.0,5.0,saturate(speed)),Motion);
detail=clamp((n0+lerp(.27,.48,Motion)*n1.yx)*strength,-.32,.32)*nearFade;
bubble=smoothstep(lerp(.08,.025,Motion),lerp(.45,.10,Motion),abs(n0.x)+abs(n0.y));
// Restrained painterly facing variation, derived from the same moving samples. Normal
// tilt alone under the broad sky failed to make a readable current in the first captures.
rippleShade=clamp(dot(n0,float2(.65,.75))*9+(n1.x-n1.y)*2,-.35,.35)*Motion*nearFade;
}
float2 slope=0;
[branch]if(Local>.5 && inside>.5){
float2 du=float2(1/FieldTexels.x,0),dv=float2(0,1/FieldTexels.y);
float4 l=Texture2DSampleLevel(Field,FieldSampler,uv-du,0),r=Texture2DSampleLevel(Field,FieldSampler,uv+du,0);
float4 d=Texture2DSampleLevel(Field,FieldSampler,uv-dv,0),t=Texture2DSampleLevel(Field,FieldSampler,uv+dv,0);
slope=float2((r.g>1?r.r:live.r)-(l.g>1?l.r:live.r),(t.g>1?t.r:live.r)-(d.g>1?d.r:live.r))/(2*cell);
slope=clamp(slope,-.18,.18)*smoothstep(0,600,min(edge.x,edge.y));
}
Normal=normalize(float3(-slope+detail,1));
// Small broken highlights, with stronger roughness in fast, shallow reaches.
float riffle=smoothstep(.40,1.25,speed)*(1-smoothstep(.20,.75,depth));
float foam=flow.a*lerp(smoothstep(.95,1.45,speed)*.16,smoothstep(.22,.95,speed)*(.02+.09*bubble),Motion)*nearFade;
float2 trail=0;
[branch]if(DetailEnabled>.5 && Local>.5 && inside>.5 && nearFade>.001)trail=Texture2DSampleLevel(Detail,DetailSampler,uv,0).rg;
foam=saturate(foam+trail.x*FoamGain*(.25+.75*bubble)*nearFade);
float silt=saturate(trail.y*SedimentGain)*nearFade;
Rough=clamp(lerp(lerp(.23,.32,riffle),lerp(.19,.29,riffle),Motion)+foam*.18-rippleShade*.15,.08,.65);
Opacity=saturate(lerp(.085,.14,Turbidity)+smoothstep(.08,1.1,depth)*lerp(.09,.14,Turbidity)+foam*.3+silt*.06+rippleShade*.14);
Mask=Local>.5 ? inside*step(1,live.g) : OldMask*(1-inside);
float3 colour=lerp(float3(.019,.031,.028),float3(.009,.024,.026),smoothstep(.12,.8,depth));
colour*=1+rippleShade*.65;
// A mineral-bearing base remains present without a passing vehicle. Shared on the
// static and local surfaces, with depth attenuation retaining readable shallow edges.
Scatter=lerp(lerp(float3(.00025,.00060,.00045),float3(.0052,.0065,.0055),Turbidity),float3(.012,.008,.004),silt);
Scatter*=1+rippleShade*.20;
Absorb=lerp(lerp(float3(.003,.0015,.001),float3(.016,.010,.006),Turbidity),float3(.010,.013,.018),silt);
return lerp(colour,float3(.35,.39,.36),foam);
'''
    node=g.custom(args+['OldMask'],code,outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1),('Opacity',u.CustomMaterialOutputType.CMOT_FLOAT1),('Mask',u.CustomMaterialOutputType.CMOT_FLOAT1),('Scatter',u.CustomMaterialOutputType.CMOT_FLOAT3),('Absorb',u.CustomMaterialOutputType.CMOT_FLOAT3)])
    for key,n in inputs.items():g.wire(n,node,key)
    if kind=='Lake':g.wire(old,node,'OldMask',oldout)
    else:g.wire(g.scalar(1),node,'OldMask') # Static geometry is already clipped to the same wet domain.
    for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'Normal'),(u.MaterialProperty.MP_ROUGHNESS,'Rough'),(u.MaterialProperty.MP_OPACITY,'Opacity'),(u.MaterialProperty.MP_OPACITY_MASK,'Mask')]:g.output(node,prop,out)
    for pin,out in [('Scattering Coefficients','Scatter'),('Absorption Coefficients','Absorb')]:
        actual=next(n for n in mel.get_material_expression_input_names(water) if clean(n)==clean(pin));g.wire(node,water,actual,out)
    g.output(g.scalar(.28),u.MaterialProperty.MP_SPECULAR)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m
