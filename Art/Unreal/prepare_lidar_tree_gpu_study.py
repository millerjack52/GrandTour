"""Build disposable GPU-study copies. No authored project asset is modified or checked out."""

import unreal as u


root = "/Game/GrandTour/ArtTests/LidarStudy"
scratch = root + "/PerformanceStudy"
assets = u.EditorAssetLibrary
materials = u.MaterialEditingLibrary
assets.make_directory(scratch)
for kind in range(3):
    source = f"{root}/FloraWorld/Canopy/SM_Canopy_{kind}"
    dest = f"{scratch}/SM_NaniteTrial_{kind}"
    original = u.load_asset(source)
    mesh = (
        u.load_asset(dest)
        if assets.does_asset_exist(dest)
        else assets.duplicate_asset(source, dest)
    )
    assert mesh and mesh.get_path_name() != original.get_path_name()
    settings = mesh.get_editor_property("nanite_settings")
    if not settings.enabled:
        settings.enabled = True
        settings.shape_preservation = u.NaniteShapePreservation.PRESERVE_AREA
        mesh.set_editor_property("nanite_settings", settings)
    assert mesh.get_editor_property("nanite_settings").enabled and assets.save_loaded_asset(
        mesh, False
    )
    assert not original.get_editor_property("nanite_settings").enabled
    for part in ("Rigid", "Leaves"):
        path = f"{scratch}/SM_Section{part}_{kind}"
        copy = (
            u.load_asset(path)
            if assets.does_asset_exist(path)
            else assets.duplicate_asset(source, path)
        )
        assert copy and copy.get_path_name() != original.get_path_name()
        assert not copy.get_editor_property("nanite_settings").enabled
        # The source components have ray tracing disabled. Do not build an unused
        # acceleration structure for the deliberately empty far leaf section.
        copy.set_editor_property("support_ray_tracing", False)
        assert assets.save_loaded_asset(copy, False)

# Preserve the cost of the actual coverage and wind programs while removing the colour,
# normal and transmission graph. The constant colour is a diagnostic material only.
source = root + "/FloraTrailStyle/v1/MI_Path_Leaf_0_T_Colour_5_ca124a94"
original = u.load_asset(source)
parent = original.get_editor_property("parent")
while isinstance(parent, u.MaterialInstance):
    parent = parent.get_editor_property("parent")
dest = scratch + "/M_LeafColourCost"
mat = (
    u.load_asset(dest)
    if assets.does_asset_exist(dest)
    else assets.duplicate_asset(parent.get_path_name().split(".")[0], dest)
)
if assets.get_metadata_tag(mat, "LidarConstantSurface") != "1":
    constant = materials.create_material_expression(mat, u.MaterialExpressionConstant3Vector)
    constant.constant = u.LinearColor(0.13, 0.26, 0.09, 1.0)
    normal = materials.create_material_expression(mat, u.MaterialExpressionConstant3Vector)
    normal.constant = u.LinearColor(0.0, 0.0, 1.0, 1.0)
    value = materials.create_material_expression(mat, u.MaterialExpressionConstant)
    value.r = 0.75
    for prop in ("BASE_COLOR", "SUBSURFACE_COLOR"):
        assert materials.connect_material_property(
            constant, "", getattr(u.MaterialProperty, "MP_" + prop)
        )
    assert materials.connect_material_property(normal, "", u.MaterialProperty.MP_NORMAL)
    for prop in ("ROUGHNESS", "AMBIENT_OCCLUSION"):
        assert materials.connect_material_property(
            value, "", getattr(u.MaterialProperty, "MP_" + prop)
        )
    for prop in (u.MaterialProperty.MP_OPACITY_MASK, u.MaterialProperty.MP_WORLD_POSITION_OFFSET):
        assert (
            materials.get_material_property_input_node(mat, prop).get_name()
            == materials.get_material_property_input_node(parent, prop).get_name()
        )
    assert not materials.recompile_material(mat)
    assets.set_metadata_tag(mat, "LidarConstantSurface", "1")
    assert assets.save_loaded_asset(mat, False)

# Carry parameter overrides from every instance in the source inheritance chain to the experiment.
chain = []
ancestor = original
while isinstance(ancestor, u.MaterialInstance):
    chain.append(ancestor)
    ancestor = ancestor.get_editor_property("parent")
for index, ancestor in enumerate(reversed(chain)):
    dest = scratch + (
        "/MI_LeafColourCost" if ancestor == original else f"/MI_LeafColourCostParent_{index}"
    )
    child = (
        u.load_asset(dest)
        if assets.does_asset_exist(dest)
        else assets.duplicate_asset(ancestor.get_path_name().split(".")[0], dest)
    )
    materials.set_material_instance_parent(child, mat)
    assert assets.save_loaded_asset(child, False)
    mat = child
u.log("GT_TREE_GPU_STUDY_READY verified disposable canopy and material copies")
