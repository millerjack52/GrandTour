"""Isolated source-facing coverage experiment. Never modifies a production asset."""
import json
from pathlib import Path
import unreal as u
from benmore_river_life_materials import Graph, props

E=u.EditorAssetLibrary;M=u.MaterialEditingLibrary
D='/Game/GrandTour/ArtTests/FloraParity/Coverage'
CONTRACT=json.loads(Path('C:/GrandTour/Art/Export/LidarStudy/FloraParity/source-contract.json').read_text())

def make_candidate(source):
    root=source
    while isinstance(root,u.MaterialInstanceConstant):root=root.get_editor_property('parent')
    if root.blend_mode!=u.BlendMode.BLEND_MASKED:return source,None
    family=root.get_name().removeprefix('M_Path_').split('_T_Colour_')[0]
    group=next(n for n in CONTRACT['groups']['Material:'+family]['nodes'] if n['type']=='ShaderNodeGroup' and 'Flora' in n['name'])
    soft=next(i['default'] for i in group['inputs'] if i['identifier']=='Input_17')
    parent_path=D+'/'+root.get_name();m=u.load_asset(parent_path) or E.duplicate_asset(root.get_path_name().split('.')[0],parent_path)
    for n in list(M.get_material_expressions(m)):
        if str(n.get_editor_property('desc'))=='SourceFacingCoverage':M.delete_material_expression(m,n)
    alpha=next(n for n in M.get_material_expressions(m) if isinstance(n,u.MaterialExpressionCustom) and 'return saturate(a*Gain)' in str(n.get_editor_property('code')))
    g=Graph(m,'SourceFacingCoverage');normal=g.node(u.MaterialExpressionVertexNormalWS);view=g.node(u.MaterialExpressionCameraVectorWS)
    # Mathematical translation of Blender 5.1.2 Layer Weight Facing + Mix.002.
    # https://github.com/blender/blender/blob/v5.1.2/source/blender/gpu/shaders/material/gpu_shader_material_layer_weight.glsl
    coverage=g.custom(['Alpha','N','V','Soft'],'''
float b=clamp(Soft,0.0,0.99999);
float exponent=(b<0.5)?(2.0*b):(0.5/(1.0-b));
float alignment=saturate(abs(dot(normalize(N),normalize(V))));
float facing=1.0-pow(alignment,exponent);
return saturate(Alpha*(1.0-0.9*facing));
''',u.CustomMaterialOutputType.CMOT_FLOAT1)
    p=g.node(u.MaterialExpressionScalarParameter,parameter_name='SourceFacingSoftness',default_value=soft)
    for a,pin in [(alpha,'Alpha'),(normal,'N'),(view,'V'),(p,'Soft')]:g.wire(a,coverage,pin)
    g.output(coverage,u.MaterialProperty.MP_OPACITY_MASK)
    props(m,dither_opacity_mask=True,opacity_mask_clip_value=.5)
    assert not M.recompile_material(m);E.save_loaded_asset(m,False)
    path=D+'/'+source.get_name();mi=u.load_asset(path) or E.duplicate_asset(source.get_path_name().split('.')[0],path)
    M.set_material_instance_parent(mi,m);M.set_material_instance_scalar_parameter_value(mi,'BreezeCm',0.)
    M.set_material_instance_scalar_parameter_value(mi,'SourceFacingSoftness',soft);E.save_loaded_asset(mi,False)
    return mi,dict(family=family,baseline_root=root.get_path_name(),candidate_root=m.get_path_name(),source_soft_socket='Input_17',source_soft=soft,extra_texture_samples=0,scope='Facing coverage only; source mask blur and BSDF translation remain pending',temporal_validation='pending')
