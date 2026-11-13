"""Approved Mackenzie shingle on Benmore's authored deposition masks."""
import re
import unreal as u
from benmore_river_life_materials import Graph
TAG='BenmoreMackenzieShingle'
mel=u.MaterialEditingLibrary

def attach(m, refresh_sources=False):
    nodes=list(mel.get_material_expressions(m));sources={};keep=Graph(m,TAG+'Source')
    slots=[('Base',u.MaterialProperty.MP_BASE_COLOR,3,0),('OldN',u.MaterialProperty.MP_NORMAL,3,0),
           ('OldR',u.MaterialProperty.MP_ROUGHNESS,1,.9),('OldAO',u.MaterialProperty.MP_AMBIENT_OCCLUSION,1,1)]
    for key,prop,size,default in slots:
        marker=TAG+'Source:'+key
        n=next((n for n in nodes if str(n.get_editor_property('desc'))==marker),None)
        if n is None:
            old=mel.get_material_property_input_node(m,prop);out=mel.get_material_property_input_node_output_name(m,prop)
            n=keep.custom(['Value'],'return Value;',u.CustomMaterialOutputType.CMOT_FLOAT3 if size==3 else u.CustomMaterialOutputType.CMOT_FLOAT1)
            n.set_editor_property('desc',marker);keep.wire(old or keep.scalar(default),n,'Value',out)
        elif refresh_sources:
            old=mel.get_material_property_input_node(m,prop);out=mel.get_material_property_input_node_output_name(m,prop)
            assert old and str(old.get_editor_property('desc'))!=TAG,'Refresh sources only after rebuilding the underlying mud'
            keep.wire(old,n,'Value',out)
        sources[key]=n
    for n in nodes:
        if str(n.get_editor_property('desc'))==TAG:mel.delete_material_expression(m,n)
    nodes=list(mel.get_material_expressions(m));g=Graph(m,TAG)
    cp=next(n for n in nodes if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('desc'))=='ChannelPilot' and 'float2 maskUV=' in n.get_editor_property('code'))
    beduv=next(line.split('=',1)[1].strip().rstrip(';') for line in cp.get_editor_property('code').splitlines() if line.strip().startswith('float2 maskUV='))
    bed=next(n for n in nodes if isinstance(n,u.MaterialExpressionTextureObject) and n.texture and n.texture.get_name()=='T_GC_ExtendedBedZones')
    road=next((n for n in nodes if isinstance(n,u.MaterialExpressionTextureSample) and n.texture and n.texture.get_name()=='T_Benmore_RoadMask'),None)
    p=g.node(u.MaterialExpressionWorldPosition,world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    n=g.node(u.MaterialExpressionVertexNormalWS)
    mask=g.custom(['P','N','Bed','Road'],'''
float2 uv='''+beduv+''';
float4 zones=Texture2DSampleLevel(Bed,View.SharedBilinearClampedSampler,saturate(uv),0);
zones*=all(uv>=0)&&all(uv<=1);
Wetness=saturate(zones.b);
// Keep sheltered mud and the authored road surface; river gravel blends at edges.
return zones.a*(1-smoothstep(.30,.65,zones.g))*(1-saturate(Road.r))*smoothstep(.65,.90,N.z);
''',u.CustomMaterialOutputType.CMOT_FLOAT1,[('Wetness',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for key,value in [('P',p),('N',n),('Bed',bed),('Road',road or g.vector((0,0,0)))]:g.wire(value,mask,key,'RGB' if key=='Road' and road else '')
    study=u.load_asset('/Game/GrandTour/ArtTests/MackenzieRiverStudy/M_MRS_Shingle');assert study
    original=next(v for v in mel.get_material_expressions(study) if isinstance(v,u.MaterialExpressionCustom) and 'float2 base=P.xy/135.' in v.get_editor_property('code'))
    code=str(original.get_editor_property('code'))
    code=re.sub(r'\bView\b','Eye',code)
    code=re.sub(r'float pocket=.*?float fines=[^;]+;', 'float fines=0;',code,flags=re.S)
    code=re.sub(r'float wet=1-smoothstep\(1.5,17\.,[^;]+;', 'float wet=saturate(Wetness);',code)
    assert 'float wet=saturate(Wetness);' in code
    for key in ['Color','Normal','Height','Rough','AO']:code=code.replace(key+'Sampler','View.SharedBilinearWrappedSampler')
    code=code.replace('return c;','OutN=normalize(lerp(OldN,OutN,Coverage));OutR=lerp(OldR,OutR,Coverage);OutAO=lerp(OldAO,OutAO,Coverage);return lerp(Base,c,Coverage);')
    code='OutN=OldN;OutR=OldR;OutAO=OldAO;[branch]if(Coverage<.001)return Base;\n'+code
    inputs=dict(sources,P=p,N=n,Eye=g.node(u.MaterialExpressionCameraVectorWS),Camera=g.node(u.MaterialExpressionCameraPositionWS))
    tangent=m.get_editor_property('tangent_space_normal')
    if tangent:
        transform=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_TANGENT,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
        g.wire(sources['OldN'],transform,'');inputs['OldN']=transform
    for key in ['Color','Normal','Height','Rough','AO']:
        tex=u.load_asset('/Game/GrandTour/ArtTests/MackenzieRiverStudy/T_MRS_Pebble_'+key);assert tex
        inputs[key]=g.node(u.MaterialExpressionTextureObject,texture=tex,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if key=='Color' else u.MaterialSamplerType.SAMPLERTYPE_NORMAL if key=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    shader=g.custom(list(inputs)+['Coverage','Wetness'],code,outputs=[('OutN',u.CustomMaterialOutputType.CMOT_FLOAT3),('OutR',u.CustomMaterialOutputType.CMOT_FLOAT1),('OutAO',u.CustomMaterialOutputType.CMOT_FLOAT1)])
    for key,value in inputs.items():g.wire(value,shader,key)
    g.wire(mask,shader,'Coverage');g.wire(mask,shader,'Wetness','Wetness')
    for prop,out in [(u.MaterialProperty.MP_BASE_COLOR,''),(u.MaterialProperty.MP_NORMAL,'OutN'),(u.MaterialProperty.MP_ROUGHNESS,'OutR'),(u.MaterialProperty.MP_AMBIENT_OCCLUSION,'OutAO')]:
        if prop==u.MaterialProperty.MP_NORMAL and tangent:
            transform=g.node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
            g.wire(shader,transform,'',out);g.output(transform,prop)
        else:g.output(shader,prop,out)
    assert not mel.recompile_material(m)
    return dict(material=m.get_path_name(),repeat_cm=135,pom_cm=3,coverage='Existing river deposition, excluding silt and road',distance_blend_m=[12,28])
