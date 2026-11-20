"""Transient caster isolation in the game world. No editor asset or map saves."""

import builtins
import collections
import json
from pathlib import Path
import sys
import unreal as u

mode, directory = sys.argv[1:]


def game_world():
    world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
    assert world and u.GameplayStatics.get_player_pawn(world, 0), "Missing live LiDAR pickup"
    return world


out = Path(directory)


def inspect_materials(trees):
    graphs = {}
    for c in trees:
        for m in c.get_materials():
            if not m:
                continue
            instance = m
            while isinstance(m, u.MaterialInstance):
                m = m.get_editor_property("parent")
            if not m:
                continue
            key = m.get_path_name()
            if key in graphs:
                record = graphs[key]
                if "breeze_cm_by_instance" in record and isinstance(instance, u.MaterialInstance):
                    record["breeze_cm_by_instance"][instance.get_path_name()] = (
                        instance.get_scalar_parameter_value("BreezeCm")
                    )
                continue
            try:
                n = u.MaterialEditingLibrary.get_material_property_input_node(
                    m, u.MaterialProperty.MP_WORLD_POSITION_OFFSET
                )
                graphs[m.get_path_name()] = {
                    "wpo": n.get_name() if n else None,
                    "wpo_code": str(n.get_editor_property("code"))
                    if isinstance(n, u.MaterialExpressionCustom)
                    else None,
                    "custom": [
                        [
                            str(e.get_editor_property("desc")),
                            str(e.get_editor_property("code"))[:1800],
                        ]
                        for e in u.MaterialEditingLibrary.get_material_expressions(m)
                        if isinstance(e, u.MaterialExpressionCustom)
                        and (
                            "wind" in str(e.get_editor_property("desc")).lower()
                            or "wind" in str(e.get_editor_property("code")).lower()
                        )
                    ],
                }
                if isinstance(instance, u.MaterialInstance) and (
                    "distance(P,Camera)" in (graphs[key]["wpo_code"] or "")
                    and "gust*Amount*fade" in graphs[key]["wpo_code"]
                ):
                    graphs[key]["breeze_cm_by_instance"] = {
                        instance.get_path_name(): instance.get_scalar_parameter_value("BreezeCm")
                    }
            except Exception as exc:
                graphs.setdefault(key, {})["error"] = str(exc)
    (out / "tree-programs.json").write_text(json.dumps(graphs, indent=1))


if mode == "init":
    world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
    assert world and u.GameplayStatics.get_player_pawn(world, 0), (
        "Could not resolve live LiDAR vehicle"
    )
    groups = collections.defaultdict(list)
    inventory = collections.Counter()
    samples = []
    settings = []
    visible_trees = []
    fast_ranges = []
    other_distances = collections.Counter()
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for c in actor.get_components_by_class(u.PrimitiveComponent):
            tags = {str(t) for t in c.component_tags}
            if isinstance(c, u.InstancedStaticMeshComponent) and c.is_visible() and tags & {"FloraWorldCanopy", "FloraWorldSaplings"}:
                visible_trees.append(c)
            if "LidarFastCrownShadow" in tags:
                assert all(c.get_editor_property(p) for p in ("cast_shadow", "cast_hidden_shadow", "hidden_in_game"))
                assert not any(c.get_editor_property(p) for p in ("render_in_main_pass", "render_in_depth_pass", "evaluate_world_position_offset"))
                fast_ranges.append([c.static_mesh.get_name(), c.instance_end_cull_distance, c.get_instance_count()])
            if not c.get_editor_property("cast_shadow"):
                continue
            mesh = c.static_mesh if isinstance(c, u.StaticMeshComponent) else None
            asset = mesh.get_name() if mesh else ""
            owner = actor.get_class().get_name()
            tags = " ".join(map(str, c.component_tags))
            desc = (asset + " " + owner + " " + tags + " " + actor.get_name()).lower()
            if any(
                s in desc for s in ("tree", "canopy", "conifer", "trunk", "pine", "woodlandforest", "lidarfastcrownshadow")
            ):
                group = "trees"
            elif (
                "landscapecomponent" in c.get_class().get_name().lower()
                or "landscapemesh" in desc
                or "landscape" in owner.lower()
            ):
                group = "landscape"
            elif any(
                s in desc
                for s in (
                    "mixedground",
                    "grass",
                    "understory",
                    "small_plant",
                    "shrub",
                    "fern",
                    "forestground",
                    "foliage",
                )
            ):
                group = "groundflora"
            elif any(
                s in desc for s in ("mud", "relieftile", "proceduralground", "roadrelief", "gravel")
            ):
                group = "groundmesh"
            elif any(s in desc for s in ("vehicle", "pickup", "wheel", "bodycomponent", "truck")):
                group = "vehicle"
            else:
                group = "other"
            groups[group].append(c)
            inventory[(group, owner, c.get_class().get_name(), asset, tags)] += 1
            if (
                isinstance(c, u.StaticMeshComponent)
                and c.world_position_offset_disable_distance > 0
            ):
                other_distances[(tags, asset, c.world_position_offset_disable_distance)] += 1
            if isinstance(c, u.InstancedStaticMeshComponent):
                if "FloraWorld" in tags:
                    settings.append(
                        dict(
                            tags=tags,
                            mesh=asset,
                            mobility=str(c.mobility),
                            eval_wpo=c.evaluate_world_position_offset,
                            disable_cm=c.world_position_offset_disable_distance,
                            cache=str(c.shadow_cache_invalidation_behavior),
                            materials=[m.get_path_name() if m else None for m in c.get_materials()],
                        )
                    )
                samples.append(
                    [
                        group,
                        actor.get_name(),
                        asset,
                        tags,
                        c.get_instance_count(),
                        str(c.shadow_cache_invalidation_behavior),
                    ]
                )
    trees = visible_trees
    builtins.gt_shadow_tree_settings = [
        (c, c.world_position_offset_disable_distance, c.evaluate_world_position_offset)
        for c in trees
    ]
    inspect_materials(trees)
    builtins.gt_shadow_groups = groups
    builtins.gt_shadow_disabled = []
    (out / "casters.json").write_text(
        json.dumps(
            {
                "groups": {g: len(cs) for g, cs in groups.items()},
                "classes": [[*k, v] for k, v in inventory.most_common()],
                "instanced": samples,
                "flora_settings": settings,
                "fast_crown_ranges": sorted(fast_ranges),
                "explicit_wpo_limits": [[*k, count] for k, count in other_distances.items()],
            },
            indent=1,
        )
    )
elif mode == "restore_shadow_wind":
    casters = [
        c for actor in u.GameplayStatics.get_all_actors_of_class(game_world(), u.Actor)
        for c in actor.get_components_by_class(u.InstancedStaticMeshComponent)
        if "LidarFullNaniteShadow" in {str(tag) for tag in c.component_tags} and c.cast_shadow
    ]
    instances = sum(c.get_instance_count() for c in casters)
    assert instances == 146197 and {c.static_mesh.get_name() for c in casters} == {
        f"SM_NaniteRenderLod1_{i}" for i in range(3)
    }
    assert all(c.cast_hidden_shadow and not c.evaluate_world_position_offset for c in casters)
    for c in casters:
        c.set_evaluate_world_position_offset(True)
    assert all(c.evaluate_world_position_offset and c.world_position_offset_disable_distance == 11000 for c in casters)
    u.log(f"GT_RESTORED_CASTER_WIND instances={instances} groups={len(casters)}")
elif mode == "verify_launch":
    trees = builtins.gt_shadow_tree_settings
    assert trees and all(c.world_position_offset_disable_distance == 11000 for c, _, _ in trees)
    assert (
        u.SystemLibrary.get_console_variable_int_value(
            "r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias"
        )
        == -3
    )
    u.log(f"GT_TREE_SHADOW_VERIFIED components={len(trees)}")
elif mode == "verify_stock":
    trees = builtins.gt_shadow_tree_settings
    assert trees and all(c.world_position_offset_disable_distance == 0 for c, _, _ in trees)
    assert (
        u.SystemLibrary.get_console_variable_int_value(
            "r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias"
        )
        == 3
    )
    u.log(f"GT_TREE_STOCK_VERIFIED components={len(trees)}")
elif mode in ("approach", "bog_entry"):
    world = game_world()
    # Surveyed centreline about 18 m before the baseline point on Logging mud track fce5.
    x, y = -44506.0, -39484.0
    yaw = -73
    if mode == "bog_entry":
        # Start the drive 24 metres before the deep-bog checkpoint on its heading.
        x, y, yaw = -27247.0, -62212.0, -19.6745
    xy = u.Vector2D(x, y)
    height = None
    for tile in u.GameplayStatics.get_all_actors_of_class(world, u.GTRoadReliefTile):
        v = tile.get_actor_location()
        span = tile.get_editor_property("span_cm")
        if v.x <= x < v.x + span and v.y <= y < v.y + span:
            height = tile.height_at(xy)
            break
    if height is None:
        ignored = {
            c.get_owner()
            for name in ("trees", "groundflora", "vehicle")
            for c in builtins.gt_shadow_groups[name]
            if u.SystemLibrary.is_valid(c)
        }
        hit = u.SystemLibrary.line_trace_single(
            world,
            u.Vector(x, y, 8000),
            u.Vector(x, y, 2500),
            u.TraceTypeQuery.TRACE_TYPE_QUERY1,
            True,
            list(ignored),
            u.DrawDebugTrace.NONE,
            True,
        )
        assert hit is not None, "No ground under the surveyed approach"
        height = next(v.z for v in hit.to_tuple() if isinstance(v, u.Vector))
    assert 2500 < height < 8000, "Implausible road height"
    u.log(f"GT_SHADOW_APPROACH surface_z={height:.2f}")
    pc = u.GameplayStatics.get_player_controller(world, 0)
    u.SystemLibrary.execute_console_command(
        world, f"BugItGo {x} {y} {height + 110.0} 0 {yaw} 0", pc
    )
elif mode.startswith("record_"):
    w = game_world()
    pawn = u.GameplayStatics.get_player_pawn(w, 0)
    camera = u.GameplayStatics.get_player_camera_manager(w, 0)
    (out / (mode + ".json")).write_text(
        json.dumps(
            dict(
                game_time=u.GameplayStatics.get_time_seconds(w),
                pawn=pawn.get_actor_location().to_tuple(),
                camera=camera.get_camera_location().to_tuple(),
                rotation=camera.get_camera_rotation().to_tuple(),
            )
        )
    )
elif mode in ("pause", "resume"):
    assert u.GameplayStatics.set_game_paused(game_world(), mode == "pause")
elif mode in ("hold_trial", "hold_stock"):
    world = game_world()
    trial = mode == "hold_trial"
    for component, _, _ in builtins.gt_shadow_tree_settings:
        component.set_world_position_offset_disable_distance(11000 if trial else 0)
    bias = -3 if trial else 3
    u.SystemLibrary.execute_console_command(
        world, f"r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias {bias}"
    )
    u.SystemLibrary.execute_console_command(world, "r.Shadow.Virtual.Cache 0")
elif mode.startswith("wind_"):
    if not (out / "tree-programs.json").exists():
        inspect_materials([x[0] for x in builtins.gt_shadow_tree_settings])
    arg = mode.removeprefix("wind_")
    for c, dist, enabled in builtins.gt_shadow_tree_settings:
        c.set_world_position_offset_disable_distance(
            0 if arg == "stock" else dist if arg in ("restore", "off") else int(arg)
        )
        c.set_evaluate_world_position_offset(enabled if arg != "off" else False)
elif mode.startswith("isolate_"):
    for c in builtins.gt_shadow_disabled:
        if u.SystemLibrary.is_valid(c):
            c.set_cast_shadow(True)
    group = mode.removeprefix("isolate_")
    components = builtins.gt_shadow_groups.get(group, [])
    for c in components:
        if u.SystemLibrary.is_valid(c):
            c.set_cast_shadow(False)
    builtins.gt_shadow_disabled = components
u.log("GT_SHADOW_STUDY " + mode)
