"""Owned channel pilot: sourced aggregate plus geographic deposition/wetness data.

The existing deformation WPO, physical profiles and water simulation stay intact.
"""
import unreal as u
from benmore_river_life_materials import Graph, props

DEST='/Game/GrandTour/Demo/BenmoreRoads/Gaea/ChannelPilot'
SOURCE='/Game/GrandTour/Demo/BenmoreRoads/Gaea/'
mel=u.MaterialEditingLibrary;eal=u.EditorAssetLibrary
UV='(P.xy*.01-float2(-725,105)+.125)/float2(175.25,205.25)'

def clone(source,name):
    m=u.load_asset(DEST+'/'+name) or eal.duplicate_asset(source,DEST+'/'+name)
    assert m
    return m

def bed(source,name,zone_texture=None,rock_root=None,mask_uv=None):
    m=clone(source,name)
    # Idempotent rebuild: retained source nodes are marked before adding our wrapper.
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='ChannelPilot':mel.delete_material_expression(m,n)
    old={}
    for label,prop in [('Color',u.MaterialProperty.MP_BASE_COLOR),('Normal',u.MaterialProperty.MP_NORMAL),('Rough',u.MaterialProperty.MP_ROUGHNESS)]:
        marker='CP_Source'+label+'|'
        n=next((n for n in mel.get_material_expressions(m) if str(n.get_editor_property('desc')).startswith(marker)),None)
        if n:out=str(n.get_editor_property('desc')).split('|')[1]
        else:
            source=mel.get_material_property_input_node(m,prop);sourceout=mel.get_material_property_input_node_output_name(m,prop)
            assert source
            keep=Graph(m,marker)
            n=keep.custom(['Value'],'return Value;',u.CustomMaterialOutputType.CMOT_FLOAT1 if label=='Rough' else u.CustomMaterialOutputType.CMOT_FLOAT3)
            keep.wire(source,n,'Value',sourceout);out=''
        old[label]=(n,out)
    g=Graph(m,'ChannelPilot')
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    node=g.custom(['P','Camera','Base','OldN','OldR','Zones','Rock','RockN','RockR'],'''
Normal=OldN;Rough=OldR;
float2 maskUV='''+(mask_uv or UV)+''';
float2 uv=P.xy/290,dx=ddx(uv),dy=ddy(uv);
float2 fine=uv*2.35+float2(.173,.681);
[branch] if(any(maskUV<0)||any(maskUV>1)) return Base;
float4 zones=Texture2DSampleLevel(Zones,ZonesSampler,maskUV,0);
[branch] if(zones.a<.005) return Base;
float3 rock=Texture2DSampleGrad(Rock,View.SharedBilinearWrappedSampler,uv,dx,dy).rgb;
float near=1-smoothstep(35,100,length(Camera-P)*.01);
float3 aggregate=rock;
[branch] if(near>.01){
 float3 small=Texture2DSampleGrad(Rock,View.SharedBilinearWrappedSampler,fine,dx*2.35,dy*2.35).rgb;
 aggregate=lerp(rock,lerp(small,rock,smoothstep(.25,.85,zones.r)),near);
}
// Retain real mineral colours and grain contrast, with a restrained dry-soil tint.
aggregate*=float3(1.35,1.31,1.22);
float grey=dot(aggregate,float3(.2126,.7152,.0722));
aggregate=lerp(aggregate,grey*float3(1.10,1.035,.90),.18);
float3 silt=float3(.135,.112,.078)*lerp(.78,1.18,saturate(grey*4));
float3 bed=lerp(aggregate,silt,zones.g*.75)*lerp(1,.72,zones.b);
float rr=.85;
[branch] if(near>.01){
 float2 n=Texture2DSampleGrad(RockN,View.SharedBilinearWrappedSampler,uv,dx,dy).rg*2-1;
 rr=Texture2DSampleGrad(RockR,View.SharedBilinearWrappedSampler,uv,dx,dy).r;
 Normal=normalize(OldN+float3(n*.46*zones.a*(1-zones.g)*near,0));
}
Rough=lerp(OldR,clamp(rr*.82+.10-zones.b*.16,.48,.94),zones.a);
return lerp(Base,bed,zones.a*.94);
''',outputs=[('Normal',u.CustomMaterialOutputType.CMOT_FLOAT3),('Rough',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for pin,(n,out) in zip(['Base','OldN','OldR'],[old['Color'],old['Normal'],old['Rough']]):g.wire(n,node,pin,out)
    g.wire(p,node,'P');g.wire(g.node(u.MaterialExpressionCameraPositionWS),node,'Camera')
    for pin,name,kind in [('Zones','T_CP_BedZones',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),('Rock','T_CP_RiverColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('RockN','T_CP_RiverNormal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('RockR','T_CP_RiverRough',u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)]:
        t=zone_texture if pin=='Zones' and zone_texture else u.load_asset((rock_root if pin!='Zones' and rock_root else DEST)+'/'+name);assert t
        g.wire(g.node(u.MaterialExpressionTextureObject,texture=t,sampler_type=kind),node,pin)
    for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'Normal'),(u.MaterialProperty.MP_ROUGHNESS,'Rough')]:g.output(node,prop,out)
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assert eal.save_loaded_asset(m)
    return m

def water():
    m=clone(SOURCE+'RiverScale/M_RS_DomainRiver','M_CP_DomainRiver')
    for n in list(mel.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='ChannelPilot':mel.delete_material_expression(m,n)
    marker='CP_SourceMask|'
    old=next((n for n in mel.get_material_expressions(m) if str(n.get_editor_property('desc')).startswith(marker)),None)
    if old:out=str(old.get_editor_property('desc')).split('|')[1]
    else:
        old=mel.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY_MASK)
        out=mel.get_material_property_input_node_output_name(m,u.MaterialProperty.MP_OPACITY_MASK)
        old.set_editor_property('desc',marker+out)
    g=Graph(m,'ChannelPilot')
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    n=g.custom(['Old','P','Shore'],'''
float2 uv='''+UV+''';
[branch] if(any(uv<0)||any(uv>1))return Old;
float4 shore=Texture2DSampleLevel(Shore,ShoreSampler,uv,0);
return Old*(shore.a>.999 ? step(.5001,shore.r) : 1);
''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    g.wire(old,n,'Old',out);g.wire(p,n,'P')
    g.wire(g.node(u.MaterialExpressionTextureObject,texture=u.load_asset(DEST+'/T_CP_Shore'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR),n,'Shore')
    g.output(n,u.MaterialProperty.MP_OPACITY_MASK)
    errors=mel.recompile_material(m);assert not errors,list(errors)
    assert eal.save_loaded_asset(m)
    return m

def make():
    return (bed(SOURCE+'RiverScale/M_RS_Terrain','M_CP_Terrain'),
            bed(SOURCE+'RiverLife/M_RL_DeformField','M_CP_DeformField'),water())
