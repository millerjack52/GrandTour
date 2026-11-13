"""Lab-only reconstruction from ShaderCache.sdc; see NativeReference/provenance.json.
Recovered arithmetic is distinguished from the Unreal/state/lighting adapters.
"""
from pathlib import Path
import unreal as u
from benmore_river_life_materials import Graph,props
import mud_proving_materials as shared
BASE='/Game/GrandTour/ArtTests/MudLab'
DATA=Path(u.Paths.project_dir())/'Art/Export/MudLab/NativeReference'
MUD_BLEND=(Path(__file__).parent/'mudrunner_mud_blend.hlsl').read_text()
MUD_NORMAL=(Path(__file__).parent/'mudrunner_mud_normal.hlsl').read_text()
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary

def texture(name,numeric=False):
    task=props(u.AssetImportTask(),filename=str(DATA/(name+'.png')),destination_path=BASE+'/NativeReference',destination_name='T_'+name,automated=True,replace_existing=True,save=True)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    t=assets.load_asset(BASE+'/NativeReference/T_'+name);assert t
    # Original RGBA channels are used directly by the SM3 equations. Convert the
    # resulting diffuse colour to UE linear space after blending, not each input.
    props(t,srgb=False,compression_settings=u.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP,never_stream=True)
    if numeric:props(t,mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,filter=u.TextureFilter.TF_BILINEAR)
    assert assets.save_loaded_asset(t)
    return t

def fresh(name):
    m=assets.load_asset(BASE+'/'+name) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
    for e in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,e)
    props(m,tangent_space_normal=False)
    return m

def texinput(g,t):return g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)

# Mud_001 VS: normal from +/- 1/128 of the 16 m mud block; this is separate
# from the 22 cm XYZ noise displacement, which is deliberately absent from N.
STATE=MUD_NORMAL+r'''
float e=12.5;
float hx=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy+float2(e,0),PaintWindow,Window,Ready)-ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy-float2(e,0),PaintWindow,Window,Ready);
float hy=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy+float2(0,e),PaintWindow,Window,Ready)-ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy-float2(0,e),PaintWindow,Window,Ready);
NativeMudNormal nativeNormal;
float3 mrNormal=nativeNormal.eval(hx,hy);
float packedR=(height*.01+1.24)/2.04;
// Lab adapter: paint softness authors initial mud alpha; live A records disturbance.
// Base-map vegetation/dirt are authored here, not inferred native STG channels.
float baseA=mud, mudA=max(paint.a,field.a), presence=baseA*mudA;
float flat=.5*(saturate((mrNormal.z-.84)*6.25)+saturate((packedR-.45)*2.85714293));
float nearWeight=1-saturate((length(Camera.xy-P.xy)*.01-32)*.125);
flat=lerp(flat,1,min(2*(1-nearWeight),1));
float below=-height*.01;
float shade=min(2-.7*saturate(below*.765625)-saturate(presence*3.33333325),1)+.2*saturate(below*2.5);
float decalWeight=saturate((.75-mrNormal.z+.6*(1-shade))*2.5);
// Field GB is centimetres of displacement. Native GB encodes +/-11.25 cm.
float2 materialXY=P.xy-clamp(field.gb,-11.25,11.25);
// The fixture's native base-map vegetation channel is authored neutral zero.
// Absence of mud does not imply the native maximum vegetation tint.
float vegetation=0;
float3 dirtTint=1+vegetation*float3(-.639215708,-.607843161,-.874509811);
float3 grassTint=1+vegetation*float3(-.356862754,-.56078434,-.819607854);
'''

def make(paint,rest):
    native={k:texture(n,k in ['Noise','WaveSource']) for k,n in {
        'Mud':'tiles_mud__d_a','Flat':'tiles_mud_flat__d_a','Dirt':'tiles_dirt__d_a',
        'Grass':'tiles_grass__d_a','Noise':'env_mud_noise__uncmp','WaveSource':'env_water_waves__d_a_uncmp',
        'Foam':'env_water_foam__s_d_a'}.items()}
    m=fresh('M_LabSoil');props(m,two_sided=True)
    g=Graph(m,'MudRunnerRecovered');d=shared.inputs(g,paint,rest)
    d['P'].set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    d['Camera']=g.node(u.MaterialExpressionCameraPositionWS)
    d['VisualGrid']=g.node(u.MaterialExpressionScalarParameter,parameter_name='MR_VisualGrid',default_value=0)
    d.update({k:texinput(g,native[k]) for k in ['Mud','Flat','Dirt','Grass','Noise']})
    def out(body,prop,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
        e=g.custom(list(d),shared.COMMON+STATE+body,kind)
        for k,v in d.items():g.wire(v,e,k)
        if prop is not None:g.output(e,prop)
        return e
    out(MUD_BLEND+r'''
// Mud_000 PS, through the first material blend (before scene lighting).
float2 q=materialXY*.01;
float4 churn=Texture2DSample(Mud,MudSampler,q*.24);
float4 flatTex=Texture2DSample(Flat,FlatSampler,q*.24);
float4 dirt=Texture2DSample(Dirt,DirtSampler,q*.12);
float4 grass=Texture2DSample(Grass,GrassSampler,q*.12);
// No projected vehicle/road decal atlas in this fixture: use the same mud
// pigment as its neutral input, retaining the native blend attenuation.
NativeMudBlend nativeBlend;
float3 encoded=nativeBlend.eval(churn,flatTex,dirt,grass,churn.rgb,presence,flat,decalWeight,mud,dirtTint,grassTint)*shade;
// D3D9 colour-space bridge; UE handles lights/shadows rather than the native MRT.
return pow(max(encoded,0),2.2);
''',u.MaterialProperty.MP_BASE_COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3)
    normal=out('return mrNormal;',None,u.CustomMaterialOutputType.CMOT_FLOAT3)
    # UE flips back-face normals on two-sided surfaces. Native VS normals are
    # independent of face winding; cancel that host flip on displaced folds.
    signed=g.node(u.MaterialExpressionMultiply)
    g.wire(normal,signed,'A');g.wire(g.node(u.MaterialExpressionTwoSidedSign),signed,'B')
    g.output(signed,u.MaterialProperty.MP_NORMAL)
    disp=out(r'''
float3 noise=Texture2DSampleLevel(Noise,NoiseSampler,P.xy*.0024,0).rgb-.5;
float visible=height+noise.g*22*presence;
return saturate((visible*Enabled+50)/65);
''',None)
    assert u.GTLandscapeSurfaceSetupLibrary.connect_displacement(m,disp,0,100.)
    out(r'''
// Mud_001: XYZ noise is added after height displacement. Native Y-up -> UE Z-up.
float3 noise=Texture2DSampleLevel(Noise,NoiseSampler,P.xy*.0024,0).rgb-.5;
return (float3(0,0,height)+noise.rbg*22*presence)*VisualGrid;
''',u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.CustomMaterialOutputType.CMOT_FLOAT3)
    # Original mud pass outputs diffuse/MRT attributes, no PBR normal/roughness
    # texture. These are explicitly the UE lighting adapter, not recovered values.
    out('return .9;',u.MaterialProperty.MP_ROUGHNESS)
    out('return 0;',u.MaterialProperty.MP_SPECULAR)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)

    w=fresh('M_LabWater');g=Graph(w,'MudRunnerRecoveredWater')
    props(w,shading_model=u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.2)
    slw=g.node(u.MaterialExpressionSingleLayerWaterMaterialOutput)
    clean=lambda s:''.join(c.lower() for c in s if c.isalnum())
    # SLW is the rendering bridge: the original is a deferred refraction/reflectance
    # composite. Coefficients below reproduce brown.xml's depth tint slope in cm.
    refr=[(x/255.)**2.2*.9 for x in [128,118,101]]
    import math
    absorption=[-math.log(max(x,.001))/(.8*100) for x in refr]
    for pin,v in [('Scattering Coefficients',(.00145,.00115,.00075)),('Absorption Coefficients',tuple(absorption)),('Color Scale Behind Water',tuple(refr))]:
        actual=next(n for n in mel.get_material_expression_input_names(slw) if clean(n)==clean(pin));g.wire(g.vector(v),slw,actual)
    actual=next(n for n in mel.get_material_expression_input_names(slw) if clean(n)=='phaseg');g.wire(g.scalar(0),slw,actual)
    d=shared.inputs(g,paint,rest);d['Camera']=g.node(u.MaterialExpressionCameraPositionWS)
    for k in ['WaveSource','Foam']:d[k]=texinput(g,native[k])
    for key,param in [('Wave','FieldTex'),('BaseBed','MudBaseTex')]:
        d[key]=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name=param,texture=u.load_asset('/Engine/EngineResources/Black'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    for key in ['MRWaterState','MRWaterSediment','MRWaves']:
        d[key]=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name=key,texture=u.load_asset('/Engine/EngineResources/Black'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    d['NativeWaterReady']=g.node(u.MaterialExpressionScalarParameter,parameter_name='MR_WaterReady',default_value=0)
    for name,val in [('FieldMin',(-1575,-1575,0,0)),('FieldSize',(3150,3150,0,0)),('FieldTexels',(126,126,0,0))]:
        d[name]=g.node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*val))
    d['Level']=g.node(u.MaterialExpressionScalarParameter,parameter_name='FieldLevelCm',default_value=-26*50/255)
    WATER=r'''
float2 wu=(P.xy-FieldMin.xy)/max(FieldSize.xy,1);
float4 wave=Texture2DSampleLevel(Wave,WaveSampler,saturate(wu),0);
float baseBed=Texture2DSampleLevel(BaseBed,BaseBedSampler,saturate(wu),0).r;
float waterDepth=min(wave.g,max(0,Level+wave.r-baseBed-height));
float depthM=waterDepth*.01;
// WaterCompute_008 SimulationWithMud: local mud-alpha injection, before the
// original 3x3 transport. Persistent transport comes from the lab state adapter.
float h=height*.01, wl=(Level-baseBed)*.01;
float mudA=max(paint.a,field.a);
float speed=length(wave.ba)*.01;
float suspended=(1-saturate(abs(wl+.5-h)*.5))*mudA*max(1-4*speed,0);
float turbidity=saturate(max(water.a,suspended));
float4 nativeState=Texture2DSampleLevel(MRWaterState,MRWaterStateSampler,saturate(wu),0);
float4 nativeSediment=Texture2DSampleLevel(MRWaterSediment,MRWaterSedimentSampler,saturate(wu),0);
// Water_001 VS: max(-waterDepth,(sim.r-.50195998)*.8) metres.
// Other atlas-wave vertex terms remain separate from this recovered ripple term.
float nativeRippleCm=max(-waterDepth,(nativeState.r-.50195998)*80)*NativeWaterReady;
waterDepth=max(0,waterDepth+nativeRippleCm);depthM=waterDepth*.01;
turbidity=lerp(turbidity,nativeSediment.r,NativeWaterReady);
float nativeFoam=nativeSediment.g*NativeWaterReady;
'''
    def wout(body,prop,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
        e=g.custom(list(d),shared.COMMON+WATER+body,kind)
        for k,v in d.items():g.wire(v,e,k)
        g.output(e,prop);return e
    wout('return smoothstep(.05,.65,waterDepth)*(all(wu>=0)&&all(wu<=1));',u.MaterialProperty.MP_OPACITY_MASK)
    # Brown.xml values; preserve dark silt foam rather than generic white foam.
    brown=tuple((x/255.)**2.2*.5 for x in [129,115,91])
    foam=tuple((x/255.)**2.2 for x in [62,55,46])
    wout('return lerp(float3%s,float3%s,saturate(nativeFoam));'%(brown,foam),u.MaterialProperty.MP_BASE_COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3)
    # Binding 0x1408e3fa9: coefficient=-1/OpacityDepth, multiplier=1-OpacityBias.
    # Original Water_000 transmittance: saturate((1-bias)*exp(-depth/depthScale)).
    # It is not a linear opacity-depth ramp; map its complement to SLW opacity.
    # Use the native brown medium for this fixture; suspended material increases
    # the visible density through an explicit SLW adapter, not a new erosion law.
    wout('float transmission=saturate(.6*exp(-depthM/.4)); return 1-transmission*(1-turbidity);',u.MaterialProperty.MP_OPACITY)
    wout('return .10;',u.MaterialProperty.MP_ROUGHNESS)
    wout('return .25;',u.MaterialProperty.MP_SPECULAR)
    wout('return float3(0,0,wave.r+nativeRippleCm);',u.MaterialProperty.MP_WORLD_POSITION_OFFSET,u.CustomMaterialOutputType.CMOT_FLOAT3)
    # Execute the 94 native Waves instructions in a function. Sampling its output
    # at world*.14 follows Water_000; atlas direction selection is still an adapter.
    body=(DATA/'waves.hlsl').read_text()
    functions='struct NativeWaves { float4 eval(Texture2D WaveSource,SamplerState WaveSourceSampler,float2 UV,float Time) {\n'+body+'\n} }; NativeWaves nativeWaves;\n'
    wout(functions+r'''
float2 movingFlow=lerp(wave.ba*.01,(nativeState.gb-.50195998)*2,NativeWaterReady);
float2 direction=movingFlow/max(length(movingFlow),.0001);
if(length(movingFlow)<.0001)direction=float2(1,0);
float2 q=float2(dot(P.xy*.01,direction),dot(P.xy*.01,float2(-direction.y,direction.x)))*.14;
float4 optical=Texture2DSampleLevel(MRWaves,MRWavesSampler,frac(q),0);
float2 n=(optical.xy-.50195998)*2;
float fade=1-saturate((length(Camera-P)*.01-16)/24);
n*=lerp(.2,1,fade)*saturate(depthM/.2);
float2 cell=max(FieldSize.xy/FieldTexels.xy,1),du=1/FieldTexels.xy;
float dx=Texture2DSampleLevel(Wave,WaveSampler,saturate(wu+float2(du.x,0)),0).r-Texture2DSampleLevel(Wave,WaveSampler,saturate(wu-float2(du.x,0)),0).r;
float dy=Texture2DSampleLevel(Wave,WaveSampler,saturate(wu+float2(0,du.y)),0).r-Texture2DSampleLevel(Wave,WaveSampler,saturate(wu-float2(0,du.y)),0).r;
dx+=(Texture2DSampleLevel(MRWaterState,MRWaterStateSampler,saturate(wu+float2(du.x,0)),0).r-Texture2DSampleLevel(MRWaterState,MRWaterStateSampler,saturate(wu-float2(du.x,0)),0).r)*80*NativeWaterReady;
dy+=(Texture2DSampleLevel(MRWaterState,MRWaterStateSampler,saturate(wu+float2(0,du.y)),0).r-Texture2DSampleLevel(MRWaterState,MRWaterStateSampler,saturate(wu-float2(0,du.y)),0).r)*80*NativeWaterReady;
float2 slopes=direction*n.x+float2(-direction.y,direction.x)*n.y-float2(dx,dy)/(2*cell);
return normalize(float3(slopes,1));
''',u.MaterialProperty.MP_NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3)
    assert not mel.recompile_material(w);assert assets.save_loaded_asset(w)
    test=fresh('M_WaveOracle');props(test,shading_model=u.MaterialShadingModel.MSM_UNLIT)
    tg=Graph(test,'NativeWaveOracle')
    td={'WaveSource':texinput(tg,native['WaveSource']),'UV':tg.node(u.MaterialExpressionTextureCoordinate),'Time':tg.scalar(1.25)}
    te=tg.custom(list(td),body,u.CustomMaterialOutputType.CMOT_FLOAT4)
    for k,v in td.items():tg.wire(v,te,k)
    tg.output(te,u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not mel.recompile_material(test);assert assets.save_loaded_asset(test)
    precombined=fresh('M_LabWaves');props(precombined,shading_model=u.MaterialShadingModel.MSM_UNLIT)
    pg=Graph(precombined,'NativeWavesPrecombine')
    pd={'WaveSource':texinput(pg,native['WaveSource']),'UV':pg.node(u.MaterialExpressionTextureCoordinate),'Time':pg.node(u.MaterialExpressionTime)}
    pe=pg.custom(list(pd),body,u.CustomMaterialOutputType.CMOT_FLOAT4)
    for k,v in pd.items():pg.wire(v,pe,k)
    pg.output(pe,u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not mel.recompile_material(precombined);assert assets.save_loaded_asset(precombined)
    make_simulation(paint,rest)
    make_water_oracle()
    make_mud_oracle()
    return m,w

def make_mud_oracle():
    m=fresh('M_MudBlendOracle');props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT)
    g=Graph(m,'NativeMudBlendOracle');uv=g.node(u.MaterialExpressionTextureCoordinate)
    e=g.custom(['UV'],MUD_BLEND+(DATA/'mud-oracle-inputs.hlsl').read_text(),u.CustomMaterialOutputType.CMOT_FLOAT3)
    g.wire(uv,e,'UV');g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
    m=fresh('M_MudNormalOracle');props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT)
    g=Graph(m,'NativeMudNormalOracle');uv=g.node(u.MaterialExpressionTextureCoordinate)
    code=MUD_NORMAL+'NativeMudNormal n; return n.eval((UV.x-.5)*2,(UV.y-.5)*2)*.5+.5;'
    e=g.custom(['UV'],code,u.CustomMaterialOutputType.CMOT_FLOAT3)
    g.wire(uv,e,'UV');g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)

def make_water_oracle():
    program=(DATA/'water-simulation.hlsl').read_text()
    bridge=(DATA/'water-oracle-inputs.hlsl').read_text()
    for name,tail in [('M_WaterStateOracle','return saturate(oC0.rgb);'),('M_WaterSedimentOracle','return saturate(float3(oC1.r,oC0.a,0));')]:
        m=fresh(name);props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT)
        g=Graph(m,'NativeWaterOracle')
        d={'UV':g.node(u.MaterialExpressionTextureCoordinate),'FieldTexels':g.vector((8,8,0)),'Level':g.scalar(15)}
        e=g.custom(list(d),bridge+program+'\n'+tail,u.CustomMaterialOutputType.CMOT_FLOAT3)
        for k,v in d.items():g.wire(v,e,k)
        g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR)
        assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)

def make_simulation(paint,rest):
    """Native SimulationWithMud MRTs packed into two UE RGB render targets.
    S1.rgb stays native. S1.a (foam) lives in S2.g; suspended mud remains S2.r.
    Native atlas addressing is remapped to this fixture's single rectangular pond.
    """
    program=(DATA/'water-simulation.hlsl').read_text()
    for name,tail in [('M_LabWaterSim','return saturate(oC0.rgb);'),('M_LabWaterSediment','return saturate(float3(oC1.r,oC0.a,0));')]:
        m=fresh(name);props(m,shading_model=u.MaterialShadingModel.MSM_UNLIT)
        g=Graph(m,'NativeSimulationWithMud');d=shared.inputs(g,paint,rest)
        d['UV']=g.node(u.MaterialExpressionTextureCoordinate)
        for key,param in [('Wave','FieldTex'),('BaseBed','MudBaseTex'),('Previous','MRWaterState'),('Sediment','MRWaterSediment')]:
            d[key]=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name=param,texture=u.load_asset('/Engine/EngineResources/Black'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        for key,val in [('FieldMin',(-1575,-1575,0,0)),('FieldSize',(3150,3150,0,0)),('FieldTexels',(126,126,0,0))]:
            d[key]=g.node(u.MaterialExpressionVectorParameter,parameter_name=key,default_value=u.LinearColor(*val))
        d['Level']=g.node(u.MaterialExpressionScalarParameter,parameter_name='FieldLevelCm',default_value=-26*50/255)
        # Source texture adapters. They explicitly undo each native atlas border.
        # Ground.height uses the field and authored rest data; no texture guesses.
        pre=shared.COMMON+r'''
struct InputBridge {
 float4 waterMap(Texture2D W,SamplerState WS,float2 uv) {
  float4 w=Texture2DSampleLevel(W,WS,saturate(uv-.015625),0);
  return float4(clamp(w.ba*.01,-1,1)*.5+.50195998,0,w.g*.01);
 }
 float4 state(Texture2D Prev,SamplerState PS,Texture2D Sed,SamplerState SS,Texture2D Wave,SamplerState WS,float2 uv) {
  float3 prior=Texture2DSampleLevel(Prev,PS,saturate(uv),0).rgb;
  float2 flow=Texture2DSampleLevel(Wave,WS,saturate(uv),0).ba*.01;
  // Wheel/body rasterization bridge: host flow excites the native state when
  // stronger than its retained disturbance. The subsequent transport is native.
  float2 old=(prior.gb-.50195998)*2;
  float2 disturbance=dot(flow,flow)>dot(old,old)?clamp(flow,-1,1):old;
  return float4(prior.r,disturbance*.5+.50195998,Texture2DSampleLevel(Sed,SS,saturate(uv),0).g);
 }
};InputBridge bridge;
#define MRP(uv) (FieldMin.xy+((uv)-.0078125)*FieldSize.xy)
#define MRH(uv) ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,MRP(uv),PaintWindow,Window,Ready)
#define MRA(uv) max(Texture2DSampleLevel(Paint,PaintSampler,saturate((MRP(uv)-PaintWindow.xy)/PaintWindow.z),0).a,Texture2DSampleLevel(Field,FieldSampler,saturate((MRP(uv)-Window.xy)/Window.z),0).a*Ready)
#define SAMPLE0(uv) float4(Texture2DSampleLevel(BaseBed,BaseBedSampler,saturate(((uv)-.015625)/.75),0).r/1600,0,0,0)
#define SAMPLE1(uv) float4((MRH(uv)+124)/204,.50195998,.50195998,MRA(uv))
#define SAMPLE2(uv) bridge.waterMap(Wave,WaveSampler,uv)
#define SAMPLE3(uv) bridge.state(Previous,PreviousSampler,Sediment,SedimentSampler,Wave,WaveSampler,uv)
#define SAMPLE4(uv) Texture2DSampleLevel(Sediment,SedimentSampler,saturate(uv),0)
'''
        post='\n#undef SAMPLE0\n#undef SAMPLE1\n#undef SAMPLE2\n#undef SAMPLE3\n#undef SAMPLE4\n#undef MRP\n#undef MRH\n#undef MRA\n'
        e=g.custom(list(d),pre+program+post+tail,u.CustomMaterialOutputType.CMOT_FLOAT3)
        for k,v in d.items():g.wire(v,e,k)
        g.output(e,u.MaterialProperty.MP_EMISSIVE_COLOR)
        assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
