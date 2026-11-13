"""Private proving-ground materials. Soil and single-layer water share a world height map."""
import unreal as u
from benmore_river_life_materials import Graph,props
from landscape_surface_material import NOISE
BASE='/Game/GrandTour/ArtTests/MudProvingGround'
mel=u.MaterialEditingLibrary;assets=u.EditorAssetLibrary

COMMON=NOISE+r'''
struct Ground {
 float height(Texture2D Rest,SamplerState RS,Texture2D Field,SamplerState FS,Texture2D Paint,SamplerState PS,float DepthScale,float2 xy,float3 PW,float3 W,float Ready) {
  float2 q=(xy-PW.xy)/PW.z;
  float2 packed=Texture2DSampleLevel(Rest,RS,saturate(q),0).rg;
  float h=dot(packed,float2(65280,255))*(65./65535.)-50;
  float thickness=min(50,Texture2DSampleLevel(Paint,PS,saturate(q),0).r*50*DepthScale);
  h=clamp(h,-thickness,15);
  h*=all(q>=0)&&all(q<=1);
  float2 uv=(xy-W.xy)/max(W.z,1);
  float edge=min(min(uv.x,uv.y),min(1-uv.x,1-uv.y));
  float a=Ready*smoothstep(0,100/max(W.z,1),edge);
  float live=Texture2DSampleLevel(Field,FS,saturate(uv),0).r;
  return clamp(lerp(h,live,a),-thickness,15);
 }
};Ground ground;
float2 puv=(P.xy-PaintWindow.xy)/PaintWindow.z;
float4 paint=Texture2DSampleLevel(Paint,PaintSampler,saturate(puv),0)*(all(puv>=0)&&all(puv<=1));
paint.r=saturate(paint.r*DepthScale);
float2 uv=(P.xy-Window.xy)/max(Window.z,1);
float valid=Ready*(all(uv>=0)&&all(uv<=1));
float4 field=Texture2DSampleLevel(Field,FieldSampler,saturate(uv),0)*valid;
float4 water=Texture2DSampleLevel(Water,WaterSampler,saturate(uv),0)*valid;
float height=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy,PaintWindow,Window,Ready);
float mud=smoothstep(0,3,paint.r*50);
float depth=max(0,WaterLevel-height)*mud;
float wet=mud*lerp(.62,1.,1-smoothstep(WaterLevel,WaterLevel+5,height));
'''

def fresh(name):
    path=BASE+'/'+name
    m=assets.load_asset(path) or u.AssetToolsHelpers.get_asset_tools().create_asset(name,BASE,u.Material,u.MaterialFactoryNew())
    for e in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,e)
    props(m,tangent_space_normal=False)
    return m

def inputs(g,paint,rest):
    d={'P':g.node(u.MaterialExpressionWorldPosition),'Time':g.node(u.MaterialExpressionTime)}
    zero=u.load_asset('/Engine/EngineResources/Black') or u.load_asset('/Engine/EngineResources/WhiteSquareTexture')
    for name,tex in [('Paint',paint),('Rest',rest),('Field',zero),('Water',zero)]:
        d[name]=g.node(u.MaterialExpressionTextureObjectParameter,parameter_name='GTLS_'+name,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    for name,val in [('Window',(-1600,-1600,4800,1)),('PaintWindow',(-1575,-1575,3150,1))]:
        d[name]=g.node(u.MaterialExpressionVectorParameter,parameter_name='GTLS_'+name,default_value=u.LinearColor(*val))
    for name,val in [('Ready',0),('WaterLevel',-4.509804),('Enabled',1),('DepthScale',1)]:
        d[name]=g.node(u.MaterialExpressionScalarParameter,parameter_name='GTLS_'+name,default_value=val)
    return d

def output(g,d,body,prop,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    e=g.custom(list(d),COMMON+body,kind)
    for k,v in d.items():g.wire(v,e,k)
    if prop is not None:g.output(e,prop)
    return e

def make(paint,rest):
    m=fresh('M_ProvingSoil');g=Graph(m,'MudProvingSoil');d=inputs(g,paint,rest)
    tex=u.load_asset('/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/T_brown_mud_02_Diffuse');assert tex
    colour=dict(d,Grain=g.node(u.MaterialExpressionTextureObject,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR))
    output(g,colour,r'''
float2 q=P.xy-field.gb;
float2 a=q/87.,b=float2(q.x*.61-q.y*.792,q.x*.792+q.y*.61)/143.+float2(17.3,5.7);
float3 c0=Texture2DSample(Grain,GrainSampler,a).rgb,c1=Texture2DSample(Grain,GrainSampler,b).rgb;
float grainL=dot(lerp(c0,c1,grain.noise(q/113.)),float3(.2126,.7152,.0722));
float macro=grain.noise(q/360.);
float pressed=smoothstep(.15,.9,field.a);
float3 scanned=lerp(c0,c1,grain.noise(q/113.));
float3 soil=lerp(scanned,grainL.xxx,.25)*float3(1.04,1.,.94)*1.9;
soil*=lerp(.84,1.18,macro*.35+smoothstep(-15,12,height)*.65);
soil*=lerp(1.,.82,wet);soil*=lerp(1.,.8,pressed);
float3 verge=float3(.145,.155,.10)*( .85+grain.noise(q/24.)*.25);
return lerp(verge,soil,mud);
''',u.MaterialProperty.MP_BASE_COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3)
    displacement=output(g,d,'return saturate((clamp(height,-paint.r*50,15)*Enabled+50)/65);',None)
    normaltex=u.load_asset('/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/T_brown_mud_02_nor_dx');assert normaltex
    normals=dict(d,Detail=g.node(u.MaterialExpressionTextureObject,texture=normaltex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL))
    output(g,normals,r'''
float e=6.25;
float dx=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy+float2(e,0),PaintWindow,Window,Ready)-ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy-float2(e,0),PaintWindow,Window,Ready);
float dy=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy+float2(0,e),PaintWindow,Window,Ready)-ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy-float2(0,e),PaintWindow,Window,Ready);
float2 q=(P.xy-field.gb)/3.;
float2 micro=float2(grain.noise(q+float2(.1,0))-grain.noise(q-float2(.1,0)),grain.noise(q+float2(0,.1))-grain.noise(q-float2(0,.1)));
float2 a=(P.xy-field.gb)/87.;
float2 b=float2(a.x*.61-a.y*.792,a.x*.792+a.y*.61)*87./143.+float2(17.3,5.7);
float3 n0=UnpackNormalMap(float4(Texture2DSample(Detail,DetailSampler,a).xyz,1));
float3 n1=UnpackNormalMap(float4(Texture2DSample(Detail,DetailSampler,b).xyz,1));
float2 s0=n0.xy/max(n0.z,.3),s1=n1.xy/max(n1.z,.3);
s1=float2(s1.x*.61+s1.y*.792,-s1.x*.792+s1.y*.61);
float2 detail=lerp(s0,s1,grain.noise(P.xy/113.));
float flowLength=length(field.gb);float2 axis=float2(-field.b,field.g)/max(.01,flowLength);
float phase=6.283185*dot(P.xy,axis)/20.;
float tread=smoothstep(.75,.98,field.a)*smoothstep(.1,.6,flowLength)*(1-smoothstep(.6,2.2,fwidth(phase)));
float2 treadN=axis*sin(phase)*pow(saturate(.5+.5*cos(phase)),2)*tread*.28;
return normalize(float3(-float2(dx,dy)/(2*e)+(detail*.85+micro*.35)*(1-field.a*.72)+treadN,1));
''',u.MaterialProperty.MP_NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(g,d,'return lerp(.88,lerp(.69,.46,wet)*(1-field.a*.24),mud);',u.MaterialProperty.MP_ROUGHNESS)
    output(g,d,'return .22;',u.MaterialProperty.MP_SPECULAR)
    assert u.GTLandscapeSurfaceSetupLibrary.connect_displacement(m,displacement,0,100.)
    assert not mel.recompile_material(m);assets.save_loaded_asset(m)
    w=fresh('M_ProvingPool');g=Graph(w,'MudProvingWater')
    slw=g.node(u.MaterialExpressionSingleLayerWaterMaterialOutput)
    props(w,shading_model=u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER,blend_mode=u.BlendMode.BLEND_MASKED,opacity_mask_clip_value=.2)
    clean=lambda s:''.join(c.lower() for c in s if c.isalnum())
    for pin,value in [('Scattering Coefficients',(.008,.006,.0038)),('Absorption Coefficients',(.018,.024,.035)),('Color Scale Behind Water',(.82,.78,.65))]:
        actual=next(n for n in mel.get_material_expression_input_names(slw) if clean(n)==clean(pin));g.wire(g.vector(value),slw,actual)
    actual=next(n for n in mel.get_material_expression_input_names(slw) if clean(n)=='phaseg');g.wire(g.scalar(.1),slw,actual)
    d=inputs(g,paint,rest)
    output(g,d,'return smoothstep(.02,.7,depth);',u.MaterialProperty.MP_OPACITY_MASK)
    output(g,d,'return float3(.025,.024,.018);',u.MaterialProperty.MP_BASE_COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(g,d,'return .16;',u.MaterialProperty.MP_OPACITY)
    output(g,d,'return .085+water.b*.055;',u.MaterialProperty.MP_ROUGHNESS)
    output(g,d,'return .25;',u.MaterialProperty.MP_SPECULAR)
    output(g,d,r'''
float2 n=0;
for(int i=0;i<4;i++) {
 float a=.7+i*2.39996;float2 direction=float2(cos(a),sin(a));
 float phase=dot(P.xy,direction)*6.283185/(19+i*23)+Time*(.7+i*.34);
 n+=cos(phase)*direction*(.006+water.b*.022)/(1+i*.7);
}
return normalize(float3(n*smoothstep(0,2,depth),1));
''',u.MaterialProperty.MP_NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3)
    assert not mel.recompile_material(w);assets.save_loaded_asset(w)
    return m,w

def tyre():
    m=fresh('M_ProvingTyre');props(m,tangent_space_normal=True)
    mel.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    g=Graph(m,'MudProvingTyre');d={'UV':g.node(u.MaterialExpressionTextureCoordinate)}
    position=g.node(u.MaterialExpressionPreSkinnedPosition);interp=g.node(u.MaterialExpressionVertexInterpolator)
    g.wire(position,interp,'');d['Pos']=interp
    normal=g.node(u.MaterialExpressionPreSkinnedNormal);normal_interp=g.node(u.MaterialExpressionVertexInterpolator)
    g.wire(normal,normal_interp,'');d['RestNormal']=normal_interp
    for name,value in [('TyreCoat',(0,0,0,0)),('WheelGeom',(135,-135,30,30))]:
        v=g.node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value))
        joined=g.node(u.MaterialExpressionAppendVector);g.wire(v,joined,'A');g.wire(v,joined,'B','A');d[name]=joined
    d['MudWet']=g.node(u.MaterialExpressionScalarParameter,parameter_name='MudWet',default_value=0)
    for name,suffix,sampler in [('CakeColor','Diffuse',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('CakeHeight','Displacement',u.MaterialSamplerType.SAMPLERTYPE_MASKS),('CakeNormal','nor_dx',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)]:
        t=u.load_asset('/Game/GrandTour/ArtTests/LandscapeMudVariants/PBR/T_brown_mud_02_'+suffix);assert t
        d[name]=g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=sampler)
    common=r'''
bool front=Pos.x>(WheelGeom.x+WheelGeom.y)*.5;
float coat=front ? (Pos.y<0?TyreCoat.x:TyreCoat.y) : (Pos.y<0?TyreCoat.z:TyreCoat.w);
float radius=length(float2(Pos.x-(front?WheelGeom.x:WheelGeom.y),Pos.z-WheelGeom.z))/max(WheelGeom.w,1);
float rim=1-smoothstep(.59,.66,radius);
// Triplanar rest-space detail avoids radial UV spokes and edge-on tread stretching.
float3 q=float3(Pos.x-(front?WheelGeom.x:WheelGeom.y),Pos.y,Pos.z-WheelGeom.z)/52.;
float3 w=pow(abs(RestNormal),4);w/=max(w.x+w.y+w.z,.001);
float h=Texture2DSample(CakeHeight,CakeHeightSampler,q.yz).r*w.x+Texture2DSample(CakeHeight,CakeHeightSampler,q.xz).r*w.y+Texture2DSample(CakeHeight,CakeHeightSampler,q.xy).r*w.z;
float need=(1-saturate(radius))*.95+.1;
float mask=smoothstep(-.07,.07,coat-need+(h-.5)*.23)*smoothstep(0,.08,coat);
'''
    for body,prop,kind in [
        ('float3 mud=(Texture2DSample(CakeColor,CakeColorSampler,q.yz).rgb*w.x+Texture2DSample(CakeColor,CakeColorSampler,q.xz).rgb*w.y+Texture2DSample(CakeColor,CakeColorSampler,q.xy).rgb*w.z)*lerp(2.4,1.7,saturate(MudWet));return lerp(lerp(float3(.022,.021,.02),float3(.24,.24,.25),rim),mud,mask);',u.MaterialProperty.MP_BASE_COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3),
        ('return lerp(lerp(.85,.45,rim),lerp(.78,.48,saturate(MudWet)),mask);',u.MaterialProperty.MP_ROUGHNESS,u.CustomMaterialOutputType.CMOT_FLOAT1),
        ('return rim*.6*(1-mask);',u.MaterialProperty.MP_METALLIC,u.CustomMaterialOutputType.CMOT_FLOAT1),
        ('float3 n=UnpackNormalMap(float4(Texture2DSample(CakeNormal,CakeNormalSampler,q.yz).xyz,1))*w.x+UnpackNormalMap(float4(Texture2DSample(CakeNormal,CakeNormalSampler,q.xz).xyz,1))*w.y+UnpackNormalMap(float4(Texture2DSample(CakeNormal,CakeNormalSampler,q.xy).xyz,1))*w.z;return normalize(lerp(float3(0,0,1),n,mask*.8));',u.MaterialProperty.MP_NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3)]:
        e=g.custom(list(d),common+body,kind)
        for name,node in d.items():g.wire(node,e,name)
        g.output(e,prop)
    assert not mel.recompile_material(m);assets.save_loaded_asset(m);return m
