"""Runtime overrides for reproducing the original and revised LiDAR tree shadows."""

import sys

import unreal as u


def apply_shadow_override(stock=False):
    world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
    if not world or not u.GameplayStatics.get_player_pawn(world, 0):
        raise RuntimeError("The live LiDAR study and player pickup are required")
    distance, bias = (0, 3) if stock else (11000, -3)
    count = 0
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for component in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            tags = {str(tag) for tag in component.component_tags}
            if tags & {"FloraWorldCanopy", "FloraWorldSaplings"}:
                component.set_world_position_offset_disable_distance(distance)
                count += 1
    if not count:
        raise RuntimeError("No FloraWorld canopy or sapling groups found")
    u.SystemLibrary.execute_console_command(
        world, f"r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias {bias}"
    )
    marker = "GT_TREE_SHADOW_STOCK" if stock else "GT_TREE_SHADOW_TRIAL"
    u.log(f"{marker} {count} canopy and sapling groups, {distance} cm, shadow clipmap bias {bias}")


apply_shadow_override(sys.argv[1:] == ["stock"])
