import unreal as u
from benmore_river_life_materials import Graph,props
import mud_proving_materials as shared
BASE='/Game/GrandTour/ArtTests/SandTerrain'
def make(paint,rest):
    assets=u.EditorAssetLibrary;mel=u.MaterialEditingLibrary
    m=assets.load_asset(BASE+'/M_Sand') or assets.duplicate_asset(shared.BASE+'/M_ProvingSoil',BASE+'/M_Sand')
    for n in list(mel.get_material_expressions(m)):mel.delete_material_expression(m,n)
    g=Graph(m,'SandTerrain');d=shared.inputs(g,paint,rest)
    shared.output(g,d,r'''
float2 q=P.xy-field.gb;
float loose=smoothstep(.3,.8,paint.a);
float broad=grain.noise(q/340.)*.65+grain.noise(q/103.+17)*.35;
float grains=grain.noise(q/1.8);
float resolve=1-smoothstep(.4,1.8,length(fwidth(q)));
float quartz=lerp(.5,grains,resolve);
float3 sand=lerp(float3(.39,.30,.19),float3(.58,.47,.31),broad);
sand*=lerp(.91,1.08,quartz);
sand*=lerp(.85,1,loose);
sand*=1-smoothstep(.3,.95,field.a)*.055;
float3 verge=float3(.12,.145,.069)*(.85+grain.noise(q/32.)*.25);
return lerp(verge,sand,mud);
''',u.MaterialProperty.MP_BASE_COLOR,u.CustomMaterialOutputType.CMOT_FLOAT3)
    shared.output(g,d,r'''
float e=6.25;
float dx=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy+float2(e,0),PaintWindow,Window,Ready)-ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy-float2(e,0),PaintWindow,Window,Ready);
float dy=ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy+float2(0,e),PaintWindow,Window,Ready)-ground.height(Rest,RestSampler,Field,FieldSampler,Paint,PaintSampler,DepthScale,P.xy-float2(0,e),PaintWindow,Window,Ready);
float2 q=P.xy-field.gb;
float resolve=1-smoothstep(.5,2,length(fwidth(q)));
float2 granular=float2(grain.noise(q/1.6+float2(.2,0))-grain.noise(q/1.6-float2(.2,0)),grain.noise(q/1.6+float2(0,.2))-grain.noise(q/1.6-float2(0,.2)))*.23*resolve;
float flow=length(field.gb);float2 axis=float2(-field.b,field.g)/max(.01,flow);
float phase=6.283185*dot(q,axis)/15.;
float tread=smoothstep(.78,.98,field.a)*smoothstep(.2,1,flow)*(1-smoothstep(.6,2,fwidth(phase)));
return normalize(float3(-float2(dx,dy)/(2*e)+granular*(1-field.a*.5)+axis*sin(phase)*tread*.13,1));
''',u.MaterialProperty.MP_NORMAL,u.CustomMaterialOutputType.CMOT_FLOAT3)
    shared.output(g,d,'return lerp(.86,.78,smoothstep(.2,.95,field.a));',u.MaterialProperty.MP_ROUGHNESS)
    shared.output(g,d,'return .18;',u.MaterialProperty.MP_SPECULAR)
    displacement=shared.output(g,d,'return saturate((height+50)/65);',None)
    assert u.GTLandscapeSurfaceSetupLibrary.connect_displacement(m,displacement,0,100.)
    assert not mel.recompile_material(m);assert assets.save_loaded_asset(m)
    return m
