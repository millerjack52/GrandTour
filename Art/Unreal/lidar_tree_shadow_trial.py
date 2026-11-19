"""Opt-in tree shadow settings for the installed LiDAR standalone study."""

import unreal as u


def enable_trial():
    world = u.find_object(None, "/Game/GrandTour/ArtTests/LidarStudy/L_LidarStudy.L_LidarStudy")
    if not world or not u.GameplayStatics.get_player_pawn(world, 0):
        raise RuntimeError("The live LiDAR study and player pickup are required")
    count = 0
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for component in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            tags = {str(tag) for tag in component.component_tags}
            if tags & {"FloraWorldCanopy", "FloraWorldSaplings"}:
                component.set_world_position_offset_disable_distance(11000)
                count += 1
    if not count:
        raise RuntimeError("No FloraWorld canopy or sapling groups found")
    u.SystemLibrary.execute_console_command(
        world, "r.Shadow.Virtual.Clipmap.WPODisableDistance.LodBias -3"
    )
    u.log(f"GT_TREE_SHADOW_TRIAL {count} canopy and sapling groups, 11000 cm, shadow clipmap bias -3")


enable_trial()
