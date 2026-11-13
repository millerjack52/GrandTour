"""Add approved clay/compacted bakes to a copy of the approved gravel material."""
import unreal as u
def build(mat,textures):
    mel=u.MaterialEditingLibrary
    old={prop:mel.get_material_property_input_node(mat,prop) for prop in [u.MaterialProperty.MP_BASE_COLOR,u.MaterialProperty.MP_NORMAL,u.MaterialProperty.MP_ROUGHNESS]}
    def expr(cls):return mel.create_material_expression(mat,cls)
    def custom(code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT3):
        n=expr(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',kind);slots=[]
        for name in inputs:
            slot=u.CustomInput();slot.set_editor_property('input_name',name);slots.append(slot)
        n.set_editor_property('inputs',slots);return n
    coords=[]
    for index in [0,2,3]:
        n=expr(u.MaterialExpressionTextureCoordinate);n.set_editor_property('coordinate_index',index);coords.append(n)
    uv,masks,rut=coords
    prefix='''float2 f=frac(float2(UV.x,1-UV.y)*0.25);
float2 m=1-abs(f*2-1);float2 coord=float2(m.x,1-m.y);
float coverage=saturate(Masks.x);float worked=saturate(Rut.x);
'''
    for channel,prop,body in [
        ('Color',u.MaterialProperty.MP_BASE_COLOR,'return lerp(Old,lerp(Texture2DSample(A,ASampler,coord).rgb,Texture2DSample(B,BSampler,coord).rgb,worked),coverage);'),
        ('Normal',u.MaterialProperty.MP_NORMAL,'''float3 a=UnpackNormalMap(Texture2DSample(A,ASampler,coord));
float3 b=UnpackNormalMap(Texture2DSample(B,BSampler,coord));
float3 n=normalize(lerp(a,b,worked));n.xy*=float2(f.x<0.5?1:-1,f.y<0.5?1:-1);
return normalize(lerp(Old,n,coverage));''')]:
        n=custom(prefix+body,['UV','Masks','Rut','Old','A','B'])
        for source,key in [(uv,'UV'),(masks,'Masks'),(rut,'Rut'),(old[prop],'Old')]:assert mel.connect_material_expressions(source,'',n,key)
        for kind,key in [('Clay','A'),('Worked','B')]:
            tex=expr(u.MaterialExpressionTextureObjectParameter);tex.set_editor_property('parameter_name',kind+channel);tex.set_editor_property('texture',textures['T_MS_'+kind+channel])
            if channel=='Normal':tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            assert mel.connect_material_expressions(tex,'',n,key)
        assert mel.connect_material_property(n,'',prop)
    rough=custom('return lerp(Old,0.88-0.40*saturate(1-Masks.y),saturate(Masks.x));',['Old','Masks'],u.CustomMaterialOutputType.CMOT_FLOAT1)
    mel.connect_material_expressions(old[u.MaterialProperty.MP_ROUGHNESS],'',rough,'Old');mel.connect_material_expressions(masks,'',rough,'Masks');mel.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    spec=custom('return lerp(0.15,0.27,saturate(Masks.x));',['Masks'],u.CustomMaterialOutputType.CMOT_FLOAT1);mel.connect_material_expressions(masks,'',spec,'Masks');mel.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR)
    mel.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_NANITE,True);mel.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
