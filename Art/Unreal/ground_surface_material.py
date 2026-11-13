"""Matches ground_material_v2.py; three texture fetches total per ground pixel."""
import unreal as u

def build(material,gravel,meadow,normal):
    mel=u.MaterialEditingLibrary
    def expr(cls): return mel.create_material_expression(material,cls)
    def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT3):
        node=expr(u.MaterialExpressionCustom); node.set_editor_property('code',code)
        node.set_editor_property('output_type',kind)
        slots=[]
        for name in inputs:
            slot=u.CustomInput(); slot.set_editor_property('input_name',name); slots.append(slot)
        node.set_editor_property('inputs',slots); return node
    uv=expr(u.MaterialExpressionTextureCoordinate)
    masks=expr(u.MaterialExpressionTextureCoordinate); masks.set_editor_property('coordinate_index',1)
    vc=expr(u.MaterialExpressionVertexColor)
    # FBX converts Blender UV V to 1-V, including the packed moisture channel.
    color=custom('''UV=float2(UV.x,1.0-UV.y);
float2 warped=UV+float2(0.08*sin(UV.y*1.71),0.08*sin(UV.x*1.37));
float2 gravelUV=abs(frac(warped)*2.0-1.0);
float2 meadowUV=abs(frac(warped*0.5)*2.0-1.0);
float3 gravel=Texture2DSample(Gravel,GravelSampler,float2(gravelUV.x,1.0-gravelUV.y)).rgb;
float3 meadow=Texture2DSample(Meadow,MeadowSampler,float2(meadowUV.x,1.0-meadowUV.y)).rgb;
meadow*=float3(0.63,0.56,0.58);
float lum=dot(gravel,float3(0.2126,0.7152,0.0722));
float3 dust=float3(0.42,0.31,0.18)*(0.8+lum*0.5);
gravel=lerp(gravel,dust,(1.0-Loose)*0.85);
float3 base=lerp(gravel,meadow,saturate(Masks.x))*Tint*1.25;
float3 wet=float3(0.06,0.027,0.014)*(0.55+lum*2.0);
return lerp(base,wet,saturate(1.0-Masks.y)*0.82);''',['Gravel','Meadow','UV','Masks','Tint','Loose'])
    for key,texture in [('Gravel',gravel),('Meadow',meadow)]:
        n=expr(u.MaterialExpressionTextureObjectParameter); n.set_editor_property('parameter_name',key); n.set_editor_property('texture',texture)
        assert mel.connect_material_expressions(n,'',color,key)
    for n,output,key in [(uv,'','UV'),(masks,'','Masks'),(vc,'','Tint'),(vc,'A','Loose')]:
        assert mel.connect_material_expressions(n,output,color,key), key
    assert mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=custom('return 0.9-0.30*saturate(1.0-Masks.y);',['Masks'],u.CustomMaterialOutputType.CMOT_FLOAT1)
    assert mel.connect_material_expressions(masks,'',rough,'Masks')
    assert mel.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    fine_uv=expr(u.MaterialExpressionTextureCoordinate); fine_uv.set_editor_property('u_tiling',3.0); fine_uv.set_editor_property('v_tiling',3.0)
    ns=expr(u.MaterialExpressionTextureSample); ns.set_editor_property('texture',normal); ns.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    assert mel.connect_material_expressions(fine_uv,'',ns,'UVs')
    norm=custom('return normalize(lerp(float3(0,0,1),N,0.28-0.12*saturate(Masks.x)));',['N','Masks'])
    assert mel.connect_material_expressions(ns,'RGB',norm,'N')
    assert mel.connect_material_expressions(masks,'',norm,'Masks')
    assert mel.connect_material_property(norm,'',u.MaterialProperty.MP_NORMAL)
    spec=expr(u.MaterialExpressionConstant); spec.set_editor_property('r',.15)
    mel.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
    mel.recompile_material(material); u.EditorAssetLibrary.save_loaded_asset(material)
    return material
