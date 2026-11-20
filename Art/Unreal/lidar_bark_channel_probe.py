"""Isolate the painted bark layer on transient materials in a paused LiDAR drive."""

import builtins
import sys

import unreal as u


world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
assert world and u.GameplayStatics.is_game_paused(world)
mode = sys.argv[1]
if mode == "setup":
    for command in (
        "r.BufferVisualizationOverviewTargets BaseColor,WorldNormal,Roughness,SceneDepth,"
        "AmbientOcclusion,SubsurfaceColor,Specular,MaterialAO,Metallic,ShadingModel",
        "r.BufferVisualizationDumpFramesAsHDR 0",
        "r.BufferVisualizationDumpFrames 1",
    ):
        u.SystemLibrary.execute_console_command(world, command)
    builtins.gt_bark_originals = []
    builtins.gt_saved_shadow_quality = u.SystemLibrary.get_console_variable_int_value(
        "r.ShadowQuality"
    )
elif mode in ("shadows_off", "shadows_restore"):
    assert builtins.gt_saved_shadow_quality > 0
    value = 0 if mode == "shadows_off" else builtins.gt_saved_shadow_quality
    u.SystemLibrary.execute_console_command(world, f"r.ShadowQuality {value}")
    assert u.SystemLibrary.get_console_variable_int_value("r.ShadowQuality") == value
    u.log(f"GT_ACCESS_SHADOW_QUALITY value={value}")
elif mode == "restore":
    assert len(builtins.gt_bark_originals) == 3
    for component, slot, original in builtins.gt_bark_originals:
        component.set_material(slot, original)
    builtins.gt_bark_originals = []
elif mode == "off":
    assert not builtins.gt_bark_originals
    trees = [
        comp
        for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent)
        if comp.is_visible() and "FloraWorldCanopy" in {str(tag) for tag in comp.component_tags}
    ]
    near = [c for c in trees if "TrialNearCanopy" in {str(tag) for tag in c.component_tags}]
    active = near or trees
    assert len(active) == 3
    for component in active:
        ((slot, original),) = [
            (i, material)
            for i, material in enumerate(component.get_materials())
            if material and "Path_Wood" in material.get_name()
        ]
        instance = component.create_dynamic_material_instance(slot, original)
        value = instance.get_scalar_parameter_value("BarkMossStrength")
        instance.set_scalar_parameter_value("BarkMossStrength", 0.0)
        assert instance.get_scalar_parameter_value("BarkMossStrength") == 0
        builtins.gt_bark_originals.append((component, slot, original))
        u.log(f"GT_BARK_LAYER mesh={component.static_mesh.get_name()} source_strength={value}")
else:
    raise ValueError(mode)
