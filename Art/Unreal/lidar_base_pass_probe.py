"""Temporarily remove one visible material family from the main pass for GPU profiling."""

import builtins
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import unreal as u

mode, group, directory = sys.argv[1:]
out = Path(directory)
world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
assert world and u.GameplayStatics.get_player_pawn(world, 0)


def family(actor, component):
    owner = actor.get_class().get_name()
    tags = {str(tag) for tag in component.component_tags}
    if owner == "GTMixedGroundDetails" and isinstance(component, u.InstancedStaticMeshComponent):
        return "far_grass" if component.get_name() == "DistantGrassCover" else "near_grass"
    if tags & {"FloraWorldCanopy", "FloraWorldSaplings", "LidarTreeSectionTrial"}:
        return "trees"
    if tags & {"FloraWorldUnderstory", "FloraWorldFerns", "FloraWorldRocks"}:
        return "dressing"
    if isinstance(component, u.LandscapeComponent) or owner in {
        "GTRoadReliefTile",
        "GTMudRunnerVisual",
        "GTProceduralGround",
        "GTLandscapeSurface",
    }:
        return "terrain"
    if owner == "GTCarPawn":
        return "pickup"
    return None


if mode == "inventory":
    groups = defaultdict(list)
    counts = Counter()
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        if actor.get_editor_property("hidden"):
            continue
        for component in actor.get_components_by_class(u.PrimitiveComponent):
            if not component.is_visible() or not component.get_editor_property(
                "render_in_main_pass"
            ):
                continue
            category = family(actor, component)
            if not category:
                continue
            groups[category].append(component)
            if isinstance(component, u.InstancedStaticMeshComponent):
                mesh = component.static_mesh
                counts[category, mesh.get_name() if mesh else "(none)"] += (
                    component.get_instance_count()
                )
    rain_views = [
        c
        for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)
        if a.get_class().get_name() == "GTRainEmitter"
        for c in a.get_components_by_class(u.SceneCaptureComponent2D)
        if c.is_visible()
    ]
    groups["rain_capture"] = rain_views
    groups["tree_wind"] = [c for c in groups["trees"] if c.evaluate_world_position_offset]
    groups["tree_visibility"] = groups["trees"]
    groups["tree_min2"] = [
        c
        for c in groups["trees"]
        if c.get_editor_property("override_min_lod") and c.get_editor_property("min_lod") == 1
    ]
    leaf_slots = {}
    for component in groups["trees"]:
        for slot, mat in enumerate(component.get_materials()):
            if mat and "MI_Path_Leaf_" in mat.get_name():
                leaf_slots[component] = (slot, mat)
    groups["tree_leaf_opaque"] = list(leaf_slots)
    groups["tree_mask_threshold"] = list(leaf_slots)
    groups["tree_leaf_constant"] = [
        c for c in leaf_slots if c.static_mesh.get_name() == "SM_Canopy_1"
    ]
    groups["tree_nanite"] = groups["trees"]
    groups["mature_tree_nanite"] = [
        c for c in groups["trees"] if "FloraWorldCanopy" in {str(tag) for tag in c.component_tags}
    ]
    groups["mature_d003_nanite"] = [
        c for c in groups["mature_tree_nanite"] if c.static_mesh.get_name() == "SM_Canopy_1"
    ]
    for label in ("tree", "mature_tree", "mature_d003"):
        groups[label + "_paint"] = groups[label + "_nanite"]
    for c in groups["dressing"]:
        if not isinstance(c, u.InstancedStaticMeshComponent):
            continue
        materials = [m for m in c.get_materials() if m]
        graphs = []
        for material in materials:
            while isinstance(material, u.MaterialInstance):
                material = material.get_editor_property("parent")
            wind = u.MaterialEditingLibrary.get_material_property_input_node(
                material, u.MaterialProperty.MP_WORLD_POSITION_OFFSET
            )
            if wind:
                graphs.append(
                    str(wind.get_editor_property("code"))
                    if isinstance(wind, u.MaterialExpressionCustom)
                    else wind.get_name()
                )
        # Existing FloraDriveBreeze has zero displacement beyond 55 m. Restrict the
        # trial to those exact graphs; exclude interactive and unfamiliar shaders.
        if graphs and all(
            "1-smoothstep(2500.,5500.,distance(P,Camera))" in code for code in graphs
        ):
            groups["dress_windlimit"].append(c)
    builtins.gt_base_dressing_limits = {
        c: c.world_position_offset_disable_distance for c in groups["dress_windlimit"]
    }
    builtins.gt_base_tree_meshes = {c: c.static_mesh for c in groups["trees"]}
    builtins.gt_base_tree_materials = {c: list(c.get_materials()) for c in groups["trees"]}
    builtins.gt_base_leaf_slots = leaf_slots
    groups["canopy_1"] = [c for c in groups["trees"] if c.static_mesh.get_name() == "SM_Canopy_1"]
    groups["all_grass"] = groups["near_grass"] + groups["far_grass"]
    for category in ("terrain", "dressing", "all_grass", "pickup"):
        groups["hide_trees_and_" + category] = groups["trees"] + groups[category]
    builtins.gt_base_families = groups
    builtins.gt_base_active = ("control", [])
    (out / f"base-inventory-{group}.json").write_text(
        json.dumps(
            {
                "eligible_components": {key: len(value) for key, value in groups.items()},
                "instances": [[*key, count] for key, count in counts.items()],
            },
            indent=2,
        )
    )
elif mode == "measure":

    def enable(setting, components, enabled):
        for component in components:
            if u.SystemLibrary.is_valid(component):
                if setting in ("rain_capture", "tree_visibility") or setting.startswith(
                    "hide_trees_and_"
                ):
                    component.set_visibility(enabled, False)
                elif setting == "tree_wind":
                    component.set_evaluate_world_position_offset(enabled)
                elif setting == "dress_windlimit":
                    distance = builtins.gt_base_dressing_limits[component] if enabled else 11000
                    component.set_world_position_offset_disable_distance(distance)
                elif setting == "tree_min2":
                    component.set_editor_property("min_lod", 1 if enabled else 2)
                elif setting == "tree_mask_threshold":
                    slot, original = builtins.gt_base_leaf_slots[component]
                    kind = component.static_mesh.get_name().rsplit("_", 1)[1]
                    material = (
                        original
                        if enabled
                        else u.load_asset(
                            f"/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy/MI_FilteredLeafMask_{kind}"
                        )
                    )
                    assert material
                    component.set_material(slot, material)
                elif setting in ("tree_leaf_opaque", "tree_leaf_constant"):
                    slot, original = builtins.gt_base_leaf_slots[component]
                    diagnostic = (
                        "/Engine/BasicShapes/BasicShapeMaterial"
                        if setting == "tree_leaf_opaque"
                        else "/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy/MI_LeafColourCost"
                    )
                    material = original if enabled else u.load_asset(diagnostic)
                    assert material
                    component.set_material(slot, material)
                elif setting.endswith(("_nanite", "_paint")):
                    original = builtins.gt_base_tree_meshes[component]
                    kind = original.get_name().rsplit("_", 1)[1]
                    painted = setting.endswith("_paint")
                    study_mesh = "SM_NanitePainted" if painted else "SM_NaniteTrial"
                    mesh = (
                        original
                        if enabled
                        else u.load_asset(
                            f"/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy/{study_mesh}_{kind}"
                        )
                    )
                    assert mesh
                    # This is a static authored world. Allow replacing the test mesh, then
                    # restore static mobility before the warm-up and measurement windows.
                    mobility = component.mobility
                    component.set_mobility(u.ComponentMobility.MOVABLE)
                    if painted:
                        materials = (
                            builtins.gt_base_tree_materials[component]
                            if enabled
                            else [slot.material_interface for slot in mesh.static_materials]
                        )
                        assert enabled or all(
                            "/NanitePaint/" in m.get_path_name() for m in materials
                        )
                        for slot, material in enumerate(materials):
                            component.set_material(slot, material)
                    assert component.set_static_mesh(mesh)
                    component.set_mobility(mobility)
                else:
                    component.set_render_in_main_pass(enabled)

    previous_group, previous_components = builtins.gt_base_active
    enable(previous_group, previous_components, True)
    selected = [] if group == "control" else builtins.gt_base_families[group]
    if group != "control" and not selected:
        raise RuntimeError(f"No components in {group}")
    enable(group, selected, False)
    builtins.gt_base_active = (group, selected)
    u.log(f"GT_BASE_PROBE {group} components={len(selected)}")
else:
    raise ValueError(mode)
