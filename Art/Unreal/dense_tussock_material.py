"""Shared opaque foliage material for all dense-tussock renderer variants."""
import unreal as u

def configure(mat):
    mel=u.MaterialEditingLibrary
    mel.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',True)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
    for usage in [u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,u.MaterialUsage.MATUSAGE_NANITE]:
        mel.set_base_material_usage(mat,usage,True)
    vc=mel.create_material_expression(mat,u.MaterialExpressionVertexColor)
    assert mel.connect_material_property(vc,'',u.MaterialProperty.MP_BASE_COLOR)
    assert mel.connect_material_property(vc,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
    for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.9),(u.MaterialProperty.MP_SPECULAR,.1)]:
        c=mel.create_material_expression(mat,u.MaterialExpressionConstant)
        c.set_editor_property('r',value); mel.connect_material_property(c,'',prop)
    mel.recompile_material(mat)
    u.EditorAssetLibrary.save_loaded_asset(mat)
