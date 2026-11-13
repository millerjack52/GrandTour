"""Material for the isolated architecture-A prototype. Never edits Benmore assets."""
import unreal as u

DEST = '/Game/GrandTour/ArtTests/LandscapeSurface'
REFERENCE = '/Game/GrandTour/Demo/BenmoreRoads/ReferenceSurface'

NOISE = r'''
struct GTMudDetail {
    float hash(float2 p) {
        uint2 q=uint2(int2(p));
        uint h=q.x*374761393u+q.y*668265263u;
        h=(h^(h>>13))*1274126177u;
        return float((h^(h>>16))&0x00ffffffu)/16777215.0;
    }
    float noise(float2 p) {
        float2 i=floor(p),f=frac(p);f=f*f*(3-2*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);
    }
    float relief(float2 p) {
        // Separate small chips, without the connected ridges of ridged noise.
        float2 i=floor(p/11),f=frac(p/11);
        float2 centre=.28+.44*float2(hash(i+19),hash(i-37));
        float2 q=abs(f-centre);
        float edge=max(q.x,q.y*1.3);
        float chip=(1-smoothstep(.08,.22,edge))*step(hash(i+71),.38);
        return chip*(.18+.42*hash(i+93))+(noise(p/2.3)-.5)*.08;
    }
};
GTMudDetail grain;
'''

COMMON = NOISE + r'''
float2 puv=(P.xy-PaintWindow.xy)/max(PaintWindow.z,1);
float inPaint=all(puv>=0)&&all(puv<=1);
float4 paint=Texture2DSampleLevel(Paint,PaintSampler,saturate(puv),0)*inPaint;
float2 uv=(P.xy-Window.xy)/max(Window.z,1);
float edge=min(min(uv.x,uv.y),min(1-uv.x,1-uv.y));
float active=smoothstep(0,100/max(Window.z,1),edge)*Ready;
float4 field=Texture2DSampleLevel(Field,FieldSampler,saturate(uv),0)*active;
float4 water=Texture2DSampleLevel(Water,WaterSampler,saturate(uv),0)*active;
float thickness=paint.r*50;
float mud=smoothstep(0,3,thickness);
float delta=(isfinite(field.r)?clamp(field.r,-thickness,15):0)*mud;
float depth=min(min(water.r,6),max(0,-paint.g*50-delta))*mud;
float pool=smoothstep(.05,.6,depth);
float wet=saturate(water.g)*mud;
float2 mudUV=P.xy-field.gb*mud;
float microMask=active*mud*(1-pool)*(1-field.a*.7)*lerp(1,.3,wet);
float micro=grain.relief(mudUV)*microMask;
'''

WAVES = r'''
// Five directional layers, in world cm; millimetre geometry, centimetre wavelengths.
float2 waveN=0; float waveH=0;
for(int i=0;i<5;i++) {
    float a=.71+i*2.39996; float2 d=float2(cos(a),sin(a));
    float k=6.283185/(28+i*23); float phase=dot(P.xy,d)*k+Time*(.8+i*.31);
    float amp=.045/(1+i*.45);
    waveH+=sin(phase)*amp; waveN+=cos(phase)*amp*k*d;
}
waveH*=pool; waveN*=pool;
'''

DISPLACEMENT = 'if(Ready<.5 || Enabled<.5) return 50.0/65.0;\n' + COMMON + WAVES + r'''
// One landscape carries both dry mud and the top of opaque, turbid rut water.
// Gravel contributes no geometric displacement. Signed bounds: -50 to +15 cm.
float h=clamp(delta+depth+micro+waveH*min(1,depth/.3),-thickness,15);
if(!isfinite(h)) h=0;
return saturate((h*Enabled+50)/65);
'''

COLOR = COMMON + r'''
float2 texUV=(P.xy-field.gb*mud)/400;
float3 fine=Texture2DSample(Fine,FineSampler,texUV).rgb;
float3 loose=Texture2DSample(Loose,LooseSampler,texUV*.32).rgb;
float2 trackUV=(P.xy-TrackWindow.xy)/max(TrackWindow.z,1)+.5;
float trackValid=all(trackUV>=0)&&all(trackUV<=1);
float sweep=saturate(Texture2DSampleLevel(Tracks,TracksSampler,saturate(trackUV),0).r)*trackValid;
float2 t=12.5/max(TrackWindow.z,1);
float nearby=0;
nearby=max(nearby,Texture2DSampleLevel(Tracks,TracksSampler,saturate(trackUV+float2(t.x,0)),0).r);
nearby=max(nearby,Texture2DSampleLevel(Tracks,TracksSampler,saturate(trackUV-float2(t.x,0)),0).r);
nearby=max(nearby,Texture2DSampleLevel(Tracks,TracksSampler,saturate(trackUV+float2(0,t.y)),0).r);
nearby=max(nearby,Texture2DSampleLevel(Tracks,TracksSampler,saturate(trackUV-float2(0,t.y)),0).r);
float berm=saturate(nearby-sweep)*trackValid;
float fineL=dot(fine,float3(.2126,.7152,.0722));
float coarseL=dot(loose,float3(.2126,.7152,.0722));
float3 packed=float3(1,.98,.92)*clamp(.25+(fineL-.20)*.75,.13,.46);
float3 aggregate=float3(1,.985,.94)*clamp(.29+(coarseL-.4)*1.25,.075,.62);
// Keep the approved aggregate visible even on the swept line. Berms add loose texture only.
float3 gravel=lerp(packed*.8,aggregate*.72,clamp(.6-sweep*.28+berm*.35,.28,.85));
float broad=grain.noise(mudUV/190.0);
float chips=grain.noise(mudUV/8.0);
float grit=grain.noise(mudUV/1.7);
float fracture=smoothstep(.25,.7,grain.noise(mudUV/4.0));
float raised=smoothstep(-8,9,delta);
// Large colour changes follow the displaced forms; fine grain must not camouflage their silhouette.
float3 soil=lerp(float3(.102,.108,.092),float3(.245,.235,.205),broad*.2+raised*.8);
soil*=lerp(.9,1.08,chips)*lerp(.94,1.04,grit)*lerp(.94,1,fracture);
float3 colour=lerp(soil,gravel,paint.b*(1-mud));
float3 mudColour=soil*lerp(.88,.7,wet)*(1-field.a*.13);
colour=lerp(colour,mudColour,mud);
float3 slurry=lerp(float3(.045,.052,.042),float3(.105,.092,.064),saturate(water.a*.65+.15));
float foam=water.b*pool*.07*smoothstep(.64,.85,grain.noise(P.xy/5.0));
return lerp(colour,lerp(slurry,float3(.16,.155,.125),foam),pool);
'''

NORMAL = COMMON + WAVES + r'''
float2 texel=3.125/max(Window.z,1);
float l=Texture2DSampleLevel(Field,FieldSampler,saturate(uv-float2(texel.x,0)),0).r;
float r=Texture2DSampleLevel(Field,FieldSampler,saturate(uv+float2(texel.x,0)),0).r;
float b=Texture2DSampleLevel(Field,FieldSampler,saturate(uv-float2(0,texel.y)),0).r;
float t=Texture2DSampleLevel(Field,FieldSampler,saturate(uv+float2(0,texel.y)),0).r;
l+=Texture2DSampleLevel(Water,WaterSampler,saturate(uv-float2(texel.x,0)),0).r;
r+=Texture2DSampleLevel(Water,WaterSampler,saturate(uv+float2(texel.x,0)),0).r;
b+=Texture2DSampleLevel(Water,WaterSampler,saturate(uv-float2(0,texel.y)),0).r;
t+=Texture2DSampleLevel(Water,WaterSampler,saturate(uv+float2(0,texel.y)),0).r;
float2 slope=float2(r-l,t-b)/6.25*active*mud*Enabled;
float3 detail=Texture2DSample(DetailN,DetailNSampler,(P.xy-field.gb*mud)/400).xyz;
detail=UnpackNormalMap(float4(detail,1)).xyz;
float2 microSlope=float2(grain.relief(mudUV+float2(1,0))-grain.relief(mudUV-float2(1,0)),
                        grain.relief(mudUV+float2(0,1))-grain.relief(mudUV-float2(0,1)))*.5;
float2 tilt=slope+microSlope*microMask*1.3+detail.xy*.22*(1-mud)+waveN*pool*3;
return normalize(float3(BaseN.xy-tilt,BaseN.z));
'''

ROUGHNESS = COMMON + r'''// GTLS_ROUGHNESS
return clamp(lerp(.91,lerp(.88,.46,wet)+.08*(grain.noise(mudUV/9)-.5),mud)*(1-pool)+pool*.56,.38,.96);
'''
SPECULAR = COMMON + r'''// GTLS_SPECULAR
return lerp(.16,.055,pool);
'''


def build(paint, destination=DEST):
    mel = u.MaterialEditingLibrary
    assets = u.EditorAssetLibrary
    path = destination + '/M_LandscapeSurface'
    if assets.does_asset_exist(path):
        raise RuntimeError('Prototype material already exists; preserve it or explicitly remove the prototype before rebuilding.')
    m = u.AssetToolsHelpers.get_asset_tools().create_asset('M_LandscapeSurface', destination, u.Material, u.MaterialFactoryNew())
    def props(o, **kw):
        for k, v in kw.items(): o.set_editor_property(k, v)
        return o
    def expr(cls, **kw): return props(mel.create_material_expression(m, cls), **kw)
    def tex(name, texture, normal=False):
        assert texture, name
        return expr(u.MaterialExpressionTextureObjectParameter, parameter_name=name, texture=texture,
                    sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if normal else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    p = expr(u.MaterialExpressionWorldPosition, world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    # All dynamic samples are multiplied by Ready=0 until upload. A known linear texture
    # avoids a default engine texture's sRGB sampler mismatch during shader compilation.
    zero = paint
    shared = dict(P=p, Paint=tex('GTLS_Paint',paint), Field=tex('GTLS_Field',zero), Water=tex('GTLS_Water',zero),
                  Window=expr(u.MaterialExpressionVectorParameter,parameter_name='GTLS_Window',default_value=u.LinearColor(-1600,-1600,4800,1)),
                  PaintWindow=expr(u.MaterialExpressionVectorParameter,parameter_name='GTLS_PaintWindow',default_value=u.LinearColor(-1575,-1575,3150,1)),
                  Ready=expr(u.MaterialExpressionScalarParameter,parameter_name='GTLS_Ready',default_value=0),
                  Enabled=expr(u.MaterialExpressionScalarParameter,parameter_name='GTLS_DisplacementEnabled',default_value=1),
                  Time=expr(u.MaterialExpressionTime))
    def custom(code, inputs, typ):
        c=expr(u.MaterialExpressionCustom,code=code,output_type=typ,inputs=[props(u.CustomInput(),input_name=k) for k in inputs])
        for k,v in inputs.items(): assert mel.connect_material_expressions(v,'',c,k),k
        return c
    d=custom(DISPLACEMENT,shared,u.CustomMaterialOutputType.CMOT_FLOAT1)
    assert u.GTLandscapeSurfaceSetupLibrary.connect_displacement(m,d,0,50.)
    fine=tex('FineGravel',u.load_asset(REFERENCE+'/T_Benmore_FineGravel'))
    loose=tex('LooseGravel',u.load_asset(REFERENCE+'/T_Benmore_LooseGravel'))
    for node in (fine,loose): node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    tracks=tex('TrackPaint',u.load_asset('/Game/GrandTour/Terrain/RT_TrackPaint'))
    collection=u.load_asset('/Game/GrandTour/Terrain/MPC_TrackPaint');assert collection
    tw=expr(u.MaterialExpressionCollectionParameter,collection=collection,parameter_name='TrackOrigin')
    c=custom(COLOR,dict(shared,Fine=fine,Loose=loose,Tracks=tracks,TrackWindow=tw),u.CustomMaterialOutputType.CMOT_FLOAT3)
    assert mel.connect_material_property(c,'',u.MaterialProperty.MP_BASE_COLOR)
    dn=tex('FineGravelNormal',u.load_asset(REFERENCE+'/T_Benmore_FineGravelN'),True)
    n=custom(NORMAL,dict(shared,DetailN=dn,BaseN=expr(u.MaterialExpressionVertexNormalWS)),u.CustomMaterialOutputType.CMOT_FLOAT3)
    m.set_editor_property('tangent_space_normal',False)
    assert mel.connect_material_property(n,'',u.MaterialProperty.MP_NORMAL)
    for prop,code in [(u.MaterialProperty.MP_ROUGHNESS,ROUGHNESS),
                      (u.MaterialProperty.MP_SPECULAR,SPECULAR)]:
        node=custom(code,shared,u.CustomMaterialOutputType.CMOT_FLOAT1)
        assert mel.connect_material_property(node,'',prop)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_NANITE)
    mel.recompile_material(m)
    assets.save_loaded_asset(m)
    return m
