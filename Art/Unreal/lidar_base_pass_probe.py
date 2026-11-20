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
    if tags & {"FloraWorldCanopy", "FloraWorldSaplings"}:
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
    groups["tree_leaf_constant"] = [
        c for c in leaf_slots if c.static_mesh.get_name() == "SM_Canopy_1"
    ]
    groups["tree_nanite"] = groups["trees"]
    builtins.gt_base_tree_meshes = {c: c.static_mesh for c in groups["trees"]}
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
                elif setting == "tree_min2":
                    component.set_editor_property("min_lod", 1 if enabled else 2)
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
                elif setting == "tree_nanite":
                    original = builtins.gt_base_tree_meshes[component]
                    kind = original.get_name().rsplit("_", 1)[1]
                    mesh = (
                        original
                        if enabled
                        else u.load_asset(
                            f"/Game/GrandTour/ArtTests/LidarStudy/PerformanceStudy/SM_NaniteTrial_{kind}"
                        )
                    )
                    assert mesh
                    # This is a static authored world. Allow replacing the test mesh, then
                    # restore static mobility before the warm-up and measurement windows.
                    mobility = component.mobility
                    component.set_mobility(u.ComponentMobility.MOVABLE)
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
