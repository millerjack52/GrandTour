"""Baked Blender road layers blended over the unchanged meadow/wet surface."""
import unreal as u
from ground_surface_material import build as build_old

def build(mat,textures):
    mel=u.MaterialEditingLibrary
    old='/Game/GrandTour/ArtTests/RoadFordStyle/'
    mel.delete_all_material_expressions(mat)
    build_old(mat,u.load_asset(old+'T_RF_GravelPainted'),u.load_asset(old+'T_RF_MeadowPainted'),u.load_asset(old+'T_RB_Normal'))
    old_color=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_BASE_COLOR)
    old_normal=mel.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)
    def expr(cls):return mel.create_material_expression(mat,cls)
    def custom(code,inputs):
        n=expr(u.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
        slots=[]
        for name in inputs:
            slot=u.CustomInput();slot.set_editor_property('input_name',name);slots.append(slot)
        n.set_editor_property('inputs',slots);return n
    uv=expr(u.MaterialExpressionTextureCoordinate)
    masks=expr(u.MaterialExpressionTextureCoordinate);masks.set_editor_property('coordinate_index',1)
    vc=expr(u.MaterialExpressionVertexColor)
    prefix='''float2 f=frac(float2(UV.x,1-UV.y)*0.25);
float2 m=1-abs(f*2-1);float2 coord=float2(m.x,1-m.y);
float wear=saturate((1-Loose)/0.68);
float blend=(1-saturate(Masks.x))*(1-saturate(1-Masks.y));
'''
    color=custom(prefix+'''float3 a=Texture2DSample(A,ASampler,coord).rgb;
float3 b=Texture2DSample(B,BSampler,coord).rgb;
return lerp(Old,lerp(a,b,wear),blend);''',['A','B','UV','Masks','Loose','Old'])
    normal=custom(prefix+'''float3 a=UnpackNormalMap(Texture2DSample(A,ASampler,coord)).xyz;
float3 b=UnpackNormalMap(Texture2DSample(B,BSampler,coord)).xyz;
float3 n=normalize(lerp(a,b,wear));n.xy*=float2(f.x<0.5?1:-1,f.y<0.5?1:-1);
return normalize(lerp(Old,n,blend));''',['A','B','UV','Masks','Loose','Old'])
    for n,channel,old_input in [(color,'Color',old_color),(normal,'Normal',old_normal)]:
        for key,kind in [('A','Loose'),('B','Compact')]:
            tex=expr(u.MaterialExpressionTextureObjectParameter);tex.set_editor_property('parameter_name',kind+channel);tex.set_editor_property('texture',textures['T_GR_'+kind+channel])
            if channel=='Normal':tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
            assert mel.connect_material_expressions(tex,'',n,key)
        for src,output,key in [(uv,'','UV'),(masks,'','Masks'),(vc,'A','Loose'),(old_input,'','Old')]:assert mel.connect_material_expressions(src,output,n,key)
    assert mel.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(normal,'',u.MaterialProperty.MP_NORMAL)
    mel.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    mel.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_NANITE,True)
    mel.recompile_material(mat);u.EditorAssetLibrary.save_loaded_asset(mat)
    return mat
