"""Set up the sculpting world-preview PCG rig: graph + materials + level actor.

REFERENCE ONLY in GrandTour (sized for the source's world canvas).

RUN IN-EDITOR (py "C:/GrandTour/Art/dressing/ported/ClaudeSetupPCGWorldPreview.py") with your sculpt map
open — the map must contain a Landscape. PCG generation needs a ticking
editor; the in-editor path is the supported one
(docs/landscape_migration/pitfalls_from_source.md, PCG).

Creates (get-or-create, never deletes):
  /Game/OWGame/Dev/WorldPreview/M_OWPreviewConifer   flat dark-green preview material
  /Game/OWGame/Dev/WorldPreview/PCG_OWWorldPreview   graph: landscape -> trees + scree
  Level actor "OW_PCGWorldPreview" (StaticMeshActor, no mesh) carrying the
  PCGComponent, GenerateOnDemand, first generation triggered at the end.

Loop while sculpting: sculpt -> select OW_PCGWorldPreview -> Generate button
on the PCG component (or rerun this script; it regenerates too).

To retune: edit node settings in the PCG graph editor (they're live), or
delete the two assets in-editor and rerun after changing values below.
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


ASSET_DIR = "/Game/OWGame/Dev/WorldPreview"
MAT_PATH = f"{ASSET_DIR}/M_OWPreviewConifer"
GRAPH_PATH = f"{ASSET_DIR}/PCG_OWWorldPreview"
ACTOR_LABEL = "OW_PCGWorldPreview"
CONE_PATH = "/Engine/BasicShapes/Cone.Cone"
STONE_PATHS = [
    "/Game/MWLandscapeAutoMaterial/Meshes/Cover/SM_MWAM_StoneA.SM_MWAM_StoneA",
    "/Game/MWLandscapeAutoMaterial/Meshes/Cover/SM_MWAM_StoneB.SM_MWAM_StoneB",
    "/Game/MWLandscapeAutoMaterial/Meshes/Cover/SM_MWAM_StoneC.SM_MWAM_StoneC",
    "/Game/MWLandscapeAutoMaterial/Meshes/Cover/SM_MWAM_StoneD.SM_MWAM_StoneD",
]
REPORT_PATH = Path(__file__).with_name("ClaudeSetupPCGWorldPreviewReport.json")

# Tunables (also live-editable on the graph nodes afterwards).
# Sized for the FULL 8128m x 8128m world canvas (~66 km^2, laptop under
# memory pressure): forest massing, not per-tree fidelity. Expect roughly
# 20-30k trees + 10-20k stones per Generate. If you later bound the preview
# to one 2016m region, these can go ~10x denser.
TREE_DENSITY = 0.0008     # points per m^2 (~1 tree / 1250 m^2, ~35m spacing)
TREE_MIN_FLATNESS = 0.86  # cos(slope): 0.86 ~ keeps slopes < ~30 deg
SCREE_DENSITY = 0.003
SCREE_FLATNESS = (0.42, 0.78)  # cos(slope) band ~ 39..65 deg = steep faces

result = {"ok": True, "steps": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": str(value)}
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"PCG_PREVIEW {name}: {exc!r}")
            return None

    return decorate


@step("preview_material")
def preview_material():
    if unreal.EditorAssetLibrary.does_asset_exist(MAT_PATH):
        return MAT_PATH
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset("M_OWPreviewConifer", ASSET_DIR, unreal.Material,
                             unreal.MaterialFactoryNew())
    if mat is None:
        raise RuntimeError("create_asset returned None for preview material")
    mel = unreal.MaterialEditingLibrary
    color = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -350, 0)
    color.set_editor_property("constant", unreal.LinearColor(0.05, 0.16, 0.07, 1.0))
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 220)
    rough.set_editor_property("r", 0.9)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mat):
        raise RuntimeError("save failed for preview material")
    return MAT_PATH


def _add_node(graph, settings_class):
    out = graph.add_node_of_type(settings_class)
    # BlueprintCallable with an out-param returns (node, settings) in python
    if isinstance(out, tuple):
        return out
    raise RuntimeError(f"add_node_of_type returned {out!r}, expected (node, settings)")


def _weighted_entry(mesh_path: str, weight: int, material_override=None,
                    cull_distance: int = 0):
    """Preview-prop descriptor: no shadows, no collision (the VRAM budget on
    this laptop cannot afford VSM pages + physics for 30k+ instances)."""
    mesh = unreal.load_asset(mesh_path)
    if mesh is None:
        raise RuntimeError(f"missing mesh {mesh_path}")
    entry = unreal.PCGMeshSelectorWeightedEntry()
    desc = entry.get_editor_property("descriptor")
    desc.set_editor_property("static_mesh", mesh)
    if material_override is not None:
        desc.set_editor_property("override_materials", [material_override])
    desc.set_editor_property("cast_shadow", False)
    body = desc.get_editor_property("body_instance")
    body.set_editor_property("collision_profile_name", "NoCollision")
    desc.set_editor_property("body_instance", body)
    if cull_distance > 0:
        desc.set_editor_property("instance_start_cull_distance", int(cull_distance * 0.7))
        desc.set_editor_property("instance_end_cull_distance", cull_distance)
    entry.set_editor_property("descriptor", desc)
    entry.set_editor_property("weight", weight)
    return entry


@step("build_graph")
def build_graph():
    # Always rebuild: the script is the source of truth for graph structure.
    # (In-editor delete_asset is safe; the headless-with-editor-open pitfall
    # does not apply to the editor's own python.) Node tweaks made in the
    # graph editor are lost on rerun - tune via this script's constants.
    if unreal.EditorAssetLibrary.does_asset_exist(GRAPH_PATH):
        if not unreal.EditorAssetLibrary.delete_asset(GRAPH_PATH):
            raise RuntimeError(f"could not delete existing {GRAPH_PATH} - close its editor tab and rerun")

    tools = unreal.AssetToolsHelpers.get_asset_tools()
    graph = tools.create_asset("PCG_OWWorldPreview", ASSET_DIR, unreal.PCGGraph,
                               unreal.PCGGraphFactory())
    if graph is None:
        raise RuntimeError("create_asset returned None for PCG graph")

    # --- shared landscape source
    land_node, land = _add_node(graph, unreal.PCGGetLandscapeSettings)
    sel = land.get_editor_property("actor_selector")
    sel.set_editor_property("must_overlap_self", False)
    land.set_editor_property("actor_selector", sel)

    # --- tree branch: sparse sample -> keep flat ground -> randomize -> cones
    tree_samp_node, tree_samp = _add_node(graph, unreal.PCGSurfaceSamplerSettings)
    tree_samp.set_editor_property("points_per_squared_meter", TREE_DENSITY)
    tree_samp.set_editor_property("unbounded", True)

    tree_n2d_node, _ = _add_node(graph, unreal.PCGNormalToDensitySettings)

    tree_filt_node, tree_filt = _add_node(graph, unreal.PCGDensityFilterSettings)
    tree_filt.set_editor_property("lower_bound", TREE_MIN_FLATNESS)
    tree_filt.set_editor_property("upper_bound", 1.0)

    tree_xf_node, tree_xf = _add_node(graph, unreal.PCGTransformPointsSettings)
    tree_xf.set_editor_property("uniform_scale", False)
    # Cone is 1m; oversized 12-28m trees so forest masses read from canvas
    # fly-over altitude on the 66 km^2 world.
    tree_xf.set_editor_property("scale_min", unreal.Vector(6.0, 6.0, 12.0))
    tree_xf.set_editor_property("scale_max", unreal.Vector(11.0, 11.0, 28.0))
    tree_xf.set_editor_property("rotation_max", unreal.Rotator(roll=0.0, pitch=0.0, yaw=360.0))

    tree_spawn_node, tree_spawn = _add_node(graph, unreal.PCGStaticMeshSpawnerSettings)
    tree_spawn.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted)
    conifer_mat = unreal.load_asset(MAT_PATH)
    tree_sel = tree_spawn.get_editor_property("mesh_selector_parameters")
    tree_sel.set_editor_property("mesh_entries", [
        _weighted_entry(CONE_PATH, 1, conifer_mat),
    ])

    # --- scree branch: denser sample -> keep steep faces -> tumble -> MW stones
    scree_samp_node, scree_samp = _add_node(graph, unreal.PCGSurfaceSamplerSettings)
    scree_samp.set_editor_property("points_per_squared_meter", SCREE_DENSITY)
    scree_samp.set_editor_property("unbounded", True)

    scree_n2d_node, _ = _add_node(graph, unreal.PCGNormalToDensitySettings)

    scree_filt_node, scree_filt = _add_node(graph, unreal.PCGDensityFilterSettings)
    scree_filt.set_editor_property("lower_bound", SCREE_FLATNESS[0])
    scree_filt.set_editor_property("upper_bound", SCREE_FLATNESS[1])

    scree_xf_node, scree_xf = _add_node(graph, unreal.PCGTransformPointsSettings)
    scree_xf.set_editor_property("uniform_scale", True)
    scree_xf.set_editor_property("scale_min", unreal.Vector(0.6, 0.6, 0.6))
    scree_xf.set_editor_property("scale_max", unreal.Vector(2.2, 2.2, 2.2))
    scree_xf.set_editor_property("rotation_min", unreal.Rotator(roll=-180.0, pitch=-180.0, yaw=0.0))
    scree_xf.set_editor_property("rotation_max", unreal.Rotator(roll=180.0, pitch=180.0, yaw=360.0))

    scree_spawn_node, scree_spawn = _add_node(graph, unreal.PCGStaticMeshSpawnerSettings)
    scree_spawn.set_mesh_selector_type(unreal.PCGMeshSelectorWeighted)
    scree_sel = scree_spawn.get_editor_property("mesh_selector_parameters")
    # Stones are near-field detail: cull at 2km so they never cost at
    # fly-over altitude. Trees keep no cull - forest massing must read far.
    scree_sel.set_editor_property("mesh_entries",
                                  [_weighted_entry(p, 1, cull_distance=200000)
                                   for p in STONE_PATHS])

    # --- wiring (pin labels verified against 5.8 PCG source)
    for samp, n2d, filt, xf, spawn in (
        (tree_samp_node, tree_n2d_node, tree_filt_node, tree_xf_node, tree_spawn_node),
        (scree_samp_node, scree_n2d_node, scree_filt_node, scree_xf_node, scree_spawn_node),
    ):
        graph.add_edge(land_node, "Out", samp, "Surface")
        graph.add_edge(samp, "Out", n2d, "In")
        graph.add_edge(n2d, "Out", filt, "In")
        graph.add_edge(filt, "Out", xf, "In")
        graph.add_edge(xf, "Out", spawn, "In")

    if not unreal.EditorAssetLibrary.save_loaded_asset(graph):
        raise RuntimeError("save failed for PCG graph")
    return GRAPH_PATH


@step("find_landscape")
def find_landscape():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    landscapes = [a for a in actors if isinstance(a, unreal.LandscapeProxy)]
    if not landscapes:
        raise RuntimeError("no Landscape in the open map - open your sculpt map first")
    origin, _extent = landscapes[0].get_actor_bounds(False)
    return origin


@step("preview_actor")
def preview_actor():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    existing = [a for a in actors if a.get_actor_label() == ACTOR_LABEL]
    if existing:
        actor = existing[0]
    else:
        origin = unreal.Vector(0, 0, 0)
        actor = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).spawn_actor_from_class(
            unreal.StaticMeshActor, origin)
        actor.set_actor_label(ACTOR_LABEL)

    comp = actor.get_component_by_class(unreal.PCGComponent)
    if comp is None:
        sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = sub.k2_gather_subobject_data_for_instance(actor)
        params = unreal.AddNewSubobjectParams(
            parent_handle=handles[0], new_class=unreal.PCGComponent)
        handle, fail_reason = sub.add_new_subobject(params)
        if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
            raise RuntimeError(f"add_new_subobject failed: {fail_reason}")
        comp = actor.get_component_by_class(unreal.PCGComponent)
        if comp is None:
            raise RuntimeError("PCGComponent not found after add_new_subobject")

    graph = unreal.load_asset(GRAPH_PATH)
    comp.set_graph(graph)
    try:
        comp.set_editor_property(
            "generation_trigger",
            unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
    except Exception as exc:  # cosmetic - GenerateOnLoad default also works
        unreal.log_warning(f"PCG_PREVIEW generation_trigger not set: {exc!r}")
    comp.generate(True)
    actor.modify()
    return f"{ACTOR_LABEL} generating"


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("PCG_PREVIEW setup complete - sculpt, then hit Generate on OW_PCGWorldPreview")
