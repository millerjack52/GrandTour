"""Temporarily preview a baked riverbank reach in a running Play in Editor world."""

import json
import math
from collections import defaultdict
from pathlib import Path
from uuid import uuid4

import unreal as u

from benmore_river_life_materials import Graph


def bank_material(package, grain_texture):
    texture = u.load_asset(grain_texture)
    if not texture:
        raise ValueError(f"Missing bank grain texture {grain_texture}")
    material = u.AssetToolsHelpers.get_asset_tools().create_asset(
        "M_BankEarth", package, u.Material, u.MaterialFactoryNew()
    )
    graph = Graph(material, "Riverbank")
    pigment = graph.node(u.MaterialExpressionVertexColor)
    grain = graph.node(u.MaterialExpressionTextureSample, texture=texture)
    mix = graph.custom(
        ["Pigment", "Grain"],
        "float v=dot(Grain,float3(.22,.70,.08));return Pigment*clamp(.74+3.1*v,.78,1.42);",
    )
    graph.wire(pigment, mix, "Pigment")
    graph.wire(grain, mix, "Grain")
    graph.output(mix, u.MaterialProperty.MP_BASE_COLOR)
    graph.output(graph.scalar(.89), u.MaterialProperty.MP_ROUGHNESS)
    graph.output(graph.scalar(.18), u.MaterialProperty.MP_SPECULAR)
    if u.MaterialEditingLibrary.recompile_material(material):
        raise RuntimeError("Riverbank preview material failed to compile")
    return material


def build_tile(parts, asset_path, material):
    origin = parts[0]["origin"]
    vertices, triangles, colours, uvs = [], [], [], []
    for part in parts:
        start = len(vertices)
        shift = [x - base for x, base in zip(part["origin"], origin)]
        for vertex in part["v"]:
            vertices.append(u.Vector(*[100 * (a + b) for a, b in zip(vertex, shift)]))
        triangles.extend(u.IntVector(*[start + index for index in face]) for face in part["t"])
        colours.extend(u.LinearColor(*value, 1.) for value in part["c"])
        uvs.extend(u.Vector2D(*value) for value in part["uv"])

    buffers = u.GeometryScriptSimpleMeshBuffers()
    buffers.set_editor_property("vertices", vertices)
    buffers.set_editor_property("triangles", triangles)
    buffers.set_editor_property("vertex_colors", colours)
    buffers.set_editor_property("uv0", uvs)
    dynamic = u.DynamicMesh()
    dynamic.append_buffers_to_mesh(buffers)
    options = u.GeometryScriptCreateNewStaticMeshAssetOptions()
    options.set_editor_property("enable_recompute_normals", True)
    options.set_editor_property("enable_recompute_tangents", True)
    options.set_editor_property("enable_collision", True)
    options.set_editor_property("collision_mode", u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    mesh, outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(
        dynamic, asset_path, options
    )
    if not mesh or "SUCCESS" not in str(outcome):
        raise RuntimeError(f"Building {asset_path} failed with {outcome}")
    mesh.set_material(0, material)
    return mesh, u.Vector(*[100 * value for value in origin])


def preview(bake_path, grain_texture="/Game/GrandTour/ArtTests/LidarStudy/FirstSection/PeatMoss/T_PM_PeatColour"):
    """Return preview actors for toggling. End Play to remove them. Does not save packages."""
    world = u.EditorLevelLibrary.get_game_world()
    if not world:
        raise RuntimeError("Start Play in Editor on the surveyed map first")
    tiles = defaultdict(list)
    for part in json.loads(Path(bake_path).read_text())["sections"]:
        tile = tuple(math.floor(value / 32.) for value in part["origin"][:2])
        tiles[tile].append(part)
    if not tiles:
        return []
    package = f"/Game/__GrandTourPreviewOnly/BankModels_{uuid4().hex}"
    material = bank_material(package, grain_texture)
    actors = []
    try:
        for (x, y), parts in sorted(tiles.items()):
            mesh, location = build_tile(parts, f"{package}/SM_Bank_{x+32768}_{y+32768}", material)
            actor = u.GTVehicleSetupLibrary.spawn_actor_of_class(
                world, u.StaticMeshActor, u.Transform(location=location), "RiverbankPreview"
            )
            actors.append(actor)
            component = actor.static_mesh_component
            component.set_mobility(u.ComponentMobility.MOVABLE)
            component.set_static_mesh(mesh)
            component.set_material(0, material)
            component.set_collision_profile_name("BlockAll")
            component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
    except Exception:
        for actor in actors:
            actor.destroy_actor()
        raise
    return actors
