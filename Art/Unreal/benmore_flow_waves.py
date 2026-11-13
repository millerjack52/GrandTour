"""Numerical wave data and bounded, continuous current sampling. No painted textures.

One 256-square precombine for the domain: RG slopes, B long-wave height,
A foam transmittance. Integer spatial frequencies make the 12m field seamless.
Sub-metre bands contribute normals/foam only, never grid displacement.
"""
import unreal as u
from benmore_river_life_materials import Graph, props
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/FlowWaves'
SRC='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement'

# nx, ny, amplitude metres, intrinsic radians/sec, phase radians.
COARSE=[(3,1,.014,.31,.4),(4,0,.011,.43,1.7),(3,-2,.012,.37,4.2),(2,2,.009,.29,2.9),(4,1,.008,.41,5.6),(2,-3,.007,.23,3.5)]
FINE=[(13,3,.0020,.71,.2),(21,-5,.0014,.83,2.2),(32,7,.0009,.67,5.2),(41,-8,.0006,.91,1.4),(17,11,.0013,.57,3.3),(8,-15,.0012,.77,4.1),(29,16,.00065,.97,2.7),(11,-7,.0014,.63,5.8)]
HEIGHT_RANGE=.18
HEIGHT_BOUND=sum(w[2] for w in COARSE)

# Common envelope: displacement and its lighting use the same depth/current gain.
# The absolute bound is <=22% of mean optical depth, then shore/distance fades.
ENVELOPE='''
float currentShape=smoothstep(.12,.85,length(ambientVelocity))*inBake;
float strength=min(1.35,.22*ambientDepth/HEIGHT_BOUND)*currentShape;
float shore=smoothstep(.025,.18,ambientDepth);
float2 shapeBankUV=(P.xy*.01-float2(-1480,-300)+.3125)/float2(1260.625,1075.625);
float bankDistance=(Texture2DSampleLevel(BankEdge,BankEdgeSampler,saturate(shapeBankUV),0).g-.5)*4;
shore*=lerp(1,smoothstep(.10,.75,bankDistance),inBake);
float geometryFade=1-smoothstep(55,180,length(Camera-P)*.01);
'''.replace('HEIGHT_BOUND',format(HEIGHT_BOUND,'.8f'))

def make_precombine():
    name='M_FW_Precombine'
    m=u.load_asset(DEST+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    for n in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,n)
    props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT,blend_mode=u.BlendMode.BLEND_ALPHA_COMPOSITE)
    g=Graph(m,'FlowWaves');uv=g.node(u.MaterialExpressionTextureCoordinate)
    tm=g.node(u.MaterialExpressionScalarParameter,parameter_name='WaveClock',default_value=0)
    code='float h=0,small=0;float2 slope=0;\n'
    for group,waves in [('h',COARSE),('small',FINE)]:
        for x,y,a,w,p in waves:
            code+=f'{{float2 k=float2({x},{y})*6.28318530718;float phase=dot(UV,k)-Clock*{w:.8f}+{p:.8f};float s,c;sincos(phase,s,c);{group}+={a:.8f}*s;slope+={a:.8f}*c*k/12;}}\n'
    code+='Foam=smoothstep(.0020,.0055,small+h*.025)*smoothstep(.025,.085,length(slope));\nreturn float3(.5+slope*.5,.5+h/%.8f);'%HEIGHT_RANGE
    n=g.custom(['UV','Clock'],code,outputs=[('Foam',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    g.wire(uv,n,'UV');g.wire(tm,n,'Clock');g.output(n,u.MaterialProperty.MP_EMISSIVE_COLOR);g.output(n,u.MaterialProperty.MP_OPACITY,'Foam')
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m

FLOW='''
float2 buv=(P.xy*.01-float2(-1480,-300)+.625)/float2(1261.25,1076.25);
float inBake=step(0,min(buv.x,buv.y))*step(max(buv.x,buv.y),1);
float4 flow=Texture2DSampleLevel(Baked,BakedSampler,saturate(buv),0);
flow=lerp(float4(.5,.5,.75,0),flow,inBake);
float2 ambientVelocity=(flow.rg-.5)*4;
float ambientDepth=flow.b*2;
'''

# Four fixed direction/speed bases; no rotating coordinate warp and no periodic
# reset/crossfade. Decode each slope in its own basis BEFORE combining them.
SAMPLE='''
struct CurrentWaves {
 float4 evaluate(Texture2D tex,SamplerState ss,float2 q,float2 v,float clock,float mip) {
  float speed=length(v);
  // Direction/speed interpolation uses fixed world bases, including calm water.
  float2 direction=speed>.001 ? v/speed : float2(1,0);
  float turn=atan2(direction.y,direction.x)/6.28318530718*16;
  float lo=floor(turn),d=smoothstep(0,1,frac(turn));
  float sb=speed/.25,s0=floor(sb)*.25,s=smoothstep(0,1,frac(sb));
  float4 result=0;
  [unroll]for(int j=0;j<2;j++) {
   float a=(lo+j)*6.28318530718/16;
   float sn,cs;sincos(a,sn,cs);float2 x=float2(cs,sn),y=float2(-sn,cs);
   float2 p=float2(dot(q,x),dot(q,y));
   float4 f0=Texture2DSampleLevel(tex,ss,(p-float2(s0*clock,0))/12,mip);
   float4 f1=Texture2DSampleLevel(tex,ss,(p-float2((s0+.25)*clock,0))/12,mip);
   float4 f=lerp(f0,f1,s);float2 grad=(f.rg-.5)*2;
   f=float4(x*grad.x+y*grad.y,(f.b-.5)*HEIGHT_RANGE,1-f.a);
   result+=f*(j==0 ? 1-d : d);
  }
  return result;
 }
};CurrentWaves waves;
'''.replace('HEIGHT_RANGE',format(HEIGHT_RANGE,'.8f'))

def extra_inputs(g,n):
    old=list(n.get_editor_property('inputs'));oldnames={str(i.get_editor_property('input_name')) for i in old}
    if 'SurfaceNormal' not in oldnames:
        old.append(props(u.CustomInput(),input_name='SurfaceNormal'))
        n.set_editor_property('inputs',old)
        g.wire(g.node(u.MaterialExpressionVertexNormalWS),n,'SurfaceNormal')
        old=list(n.get_editor_property('inputs'));oldnames.add('SurfaceNormal')
    if 'BankEdge' not in oldnames:
        old.append(props(u.CustomInput(),input_name='BankEdge'))
        n.set_editor_property('inputs',old)
        edge=g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(SRC+'/T_SR_Shore'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        g.wire(edge,n,'BankEdge')
        oldnames.add('BankEdge')
        # CustomInput structs are copied by the Python API. Re-read after wiring
        # or a later array assignment drops the newly connected texture pin.
        old=list(n.get_editor_property('inputs'))
    if {'Ambient','Ready','Clock','WaveGain'}<=oldnames:return
    params={
        'Ambient':g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='AmbientTex',texture=u.load_asset('/Engine/EngineResources/WhiteSquareTexture'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),
        'Ready':g.node(u.MaterialExpressionScalarParameter,parameter_name='AmbientReady',default_value=0),
        'Clock':g.node(u.MaterialExpressionScalarParameter,parameter_name='AmbientClock',default_value=0),
        'WaveGain':g.node(u.MaterialExpressionScalarParameter,parameter_name='AmbientGain',default_value=1)}
    for key in params:
        assert key not in oldnames
        old.append(props(u.CustomInput(),input_name=key))
    n.set_editor_property('inputs',old)
    for key,p in params.items():g.wire(p,n,key)

def make_surface(kind):
    name='M_GC_Domain'+kind
    # Rebuild from the installed shoreline master so reruns never stack graphs.
    path=DEST+'/'+name
    m=u.load_asset(path) or eal.duplicate_asset(SRC+'/'+name,path)
    assert m
    g=Graph(m,'FlowWaves')
    nodes=[n for n in mel.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom)]
    source_nodes=[n for n in mel.get_material_expressions(u.load_asset(SRC+'/'+name)) if isinstance(n,u.MaterialExpressionCustom)]
    original_wpo=next(n for n in source_nodes if 'return Local>.5 && inside>.5' in str(n.get_editor_property('code')))
    wpo=mel.get_material_property_input_node(m,u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    assert isinstance(wpo,u.MaterialExpressionCustom)
    code=str(original_wpo.get_editor_property('code'));region=code.split('return Local>.5')[0]
    extra_inputs(g,wpo)
    code=region+FLOW+SAMPLE+ENVELOPE+'''
float3 offset=Local>.5 && inside>.5 ? float3(0,0,live.r+Level-P.z) : float3(0,0,0);
// The river already has a continuous fine mesh. Deform it with the existing
// interaction field instead of replacing it with a half-cell-offset grid.
// The solver's boundary sponge and this blend leave the outside surface joined.
if(Local<.5 && inBake>.5 && inside>.5)
 offset.z=(live.r+Level-P.z)*smoothstep(0,600,min(edge.x,edge.y));
// The background lake is a coarse plane: keep ambient relief on the tessellated
// flowing river, while the lake receives normal-only ripples on both sides of
// the replacement window. Never displace just the local half of a flat lake.
// Height bands have wavelength >=2.91m, carried by 62.5cm-or-finer render grids.
[branch]if(Ready>.5 && geometryFade>.001){
 float4 wave=waves.evaluate(Ambient,AmbientSampler,P.xy*.01,ambientVelocity,Clock,0);
 offset.z+=wave.b*100*strength*shore*geometryFade*WaveGain;
}
return offset;
'''
    wpo.set_editor_property('code',code)
    n=next(n for n in nodes if 'Mask=Local>.5' in str(n.get_editor_property('code')) and 'Rough=' in str(n.get_editor_property('code')))
    original=next(n for n in source_nodes if 'float2 drift=velocity' in str(n.get_editor_property('code')))
    extra_inputs(g,n);code=str(original.get_editor_property('code'))
    # Keep live depth, occupancy, shore refinement and transported trails intact.
    start=code.index('float t0=frac(Time/4.7)');end=code.index('float2 slope=0;',start)
    new=SAMPLE+'''
float2 detail=0;float bubble=0;float rippleShade=0;
float2 footprint=max(abs(ddx(q)),abs(ddy(q)));
float mip=max(0,log2(max(max(footprint.x,footprint.y)*256/12,1)));
// Always use the authored mean for ambient phase. Local wakes add their slopes
// separately; moving the interaction window cannot restart the ambient current.
float2 ambientVelocity=(flow.rg-.5)*4;
float ambientDepth=flow.b*2;
'''+ENVELOPE+'''
[branch]if(Ready>.5 && nearFade>.001){
 float4 wave=waves.evaluate(Ambient,AmbientSampler,q,ambientVelocity,Clock,mip);
 // Calm lake/pool detail remains normal-only. Flowing close water uses exactly
 // the geometric gain; unresolved/distant detail gradually returns to normals.
 float normalGain=max(.15*(1-currentShape),strength)*nearFade;
 detail=-wave.rg*normalGain*shore*WaveGain;
 bubble=saturate(wave.a);
}
'''
    code=code[:start]+new+code[end:]
    old_window='float windowBlend=Local>.5 ? smoothstep(0,600,min(edge.x,edge.y)) : 0;'
    assert old_window in code
    code=code.replace(old_window, '''
float physicalWeight=inside*((Local>.5 || inBake>.5) ? smoothstep(0,600,min(edge.x,edge.y)) : 0);
float windowBlend=physicalWeight;''')
    code=code.replace('if(Local>.5 && inside>.5){','if(inside>.5 && (Local>.5 || inBake>.5)){')
    code=code.replace('DetailEnabled>.5 && Local>.5 && inside>.5','DetailEnabled>.5 && (Local>.5 || inBake>.5) && inside>.5')
    code=code.replace('slope=clamp(slope,-.18,.18)*smoothstep(0,600,min(edge.x,edge.y));','slope=clamp(slope,-.18,.18);')
    code=code.replace('Normal=normalize(float3(-slope+detail,1));','''
float3 baseNormal=normalize(SurfaceNormal);
baseNormal*=baseNormal.z<0 ? -1 : 1;
float2 baseSlope=-baseNormal.xy/max(.1,baseNormal.z);
slope=lerp(baseSlope,slope,physicalWeight);
Normal=normalize(float3(-slope+detail,1));''')
    # Only the lake still needs a local replacement mesh. River coverage is
    # carried by its native mesh throughout, including inside the live window.
    code=code.replace('Mask=Local>.5 ? inside*max(step(1,live.g),shoreRim) : OldMask*(1-inside);',
        'Mask=Local>.5 ? (1-inBake)*inside*max(step(1,live.g),shoreRim) : OldMask*(1-inside*(1-inBake));')
    code=code.replace('Mask=Local>.5 ? inside*step(1,live.g) : OldMask*(1-inside);',
        'Mask=Local>.5 ? (1-inBake)*inside*step(1,live.g) : OldMask*(1-inside*(1-inBake));')
    old='float foam=flow.a*lerp(smoothstep(.95,1.45,speed)*.16,smoothstep(.22,.95,speed)*(.02+.09*bubble),Motion)*nearFade;'
    assert old in code
    code=code.replace(old,'float foam=flow.a*smoothstep(.18,.95,speed)*bubble*.28*nearFade;')
    code=code.replace('Rough=clamp(lerp(lerp(.23,.32,riffle),lerp(.19,.29,riffle),Motion)+foam*.18-rippleShade*.15,.08,.65);','Rough=clamp(lerp(.23,.36,riffle)+foam*.16,.18,.65);')
    n.set_editor_property('code',code)
    assert not mel.recompile_material(m);assert eal.save_loaded_asset(m);return m
