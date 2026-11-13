"""D2 of the source's WorldDressingPlan: biome PCG post-steps.

PIPELINE (regeneration chain): run AFTER the OWCreateBiomePCG commandlet has
authored the six biome graphs (PCG_OWForest / Meadow / Scree / Road / Cliff /
Alpine) under /Game/OWGame/Dev/DressingLab/. This script owns the preview tree
material, the DRESSLAB_PCG_* biome actors (PCGComponent + BoxComponent sized to
the landscape) and their first generate.

RUN IN-EDITOR with the map open (PCG generate needs a ticking editor):
  py "C:/GrandTour/Art/dressing/ported/ClaudeSetupBiomePCG.py" [/Game/Map/Path]
(map defaults to MAP below; the first argv entry starting with /Game/ overrides it)

All descriptors follow the D4 budget table: CastShadow OFF, collision OFF.
Lab graphs are UNPARTITIONED (partitioned components need a WP level; that
switch happens on production region maps, verified 5.8 source line
PCGComponent.h:657). Rerunnable: the preview material is rebuilt; actors reused.
Loop: paint layers -> select DRESSLAB_PCG_* actor(s) -> Generate.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback

import unreal


# Map the biome actors live in. Override: the first argv entry that starts
# with /Game/.
MAP = "/Game/GrandTour/Test/L_OWToolkitTest"
for _arg in getattr(sys, "argv", [])[1:]:
    if _arg.startswith("/Game/"):
        MAP = _arg
        break
MAP_NAME = MAP.rsplit("/", 1)[-1]
ASSET_DIR = "/Game/OWGame/Dev/DressingLab"
PREVIEW_DIR = "/Game/OWGame/Dev/WorldPreview"
BIOMES = ("Forest", "Meadow", "Scree", "Road", "Cliff", "Alpine")

result = {"ok": True, "map": MAP, "steps": {}}


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
            unreal.log_error(f"BIOME_PCG {name}: {exc!r}")
            return None

    return decorate


# ---------------------------------------------------------------- materials

@step("tree_material_variation")
def tree_material_variation():
    """Rebuild M_OWPreviewConifer: PerInstanceRandom lerps two greens so no
    two trees read identical (D2 variation checklist)."""
    path = f"{PREVIEW_DIR}/M_OWPreviewConifer"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        if not unreal.EditorAssetLibrary.delete_asset(path):
            raise RuntimeError("close the M_OWPreviewConifer tab and rerun")
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    mat = tools.create_asset("M_OWPreviewConifer", PREVIEW_DIR, unreal.Material,
                             unreal.MaterialFactoryNew())
    mel = unreal.MaterialEditingLibrary
    dark = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -600, -100)
    dark.set_editor_property("constant", unreal.LinearColor(0.04, 0.14, 0.06, 1.0))
    light = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -600, 100)
    light.set_editor_property("constant", unreal.LinearColor(0.10, 0.20, 0.05, 1.0))
    rand = mel.create_material_expression(mat, unreal.MaterialExpressionPerInstanceRandom, -600, 300)
    lerp = mel.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -350, 0)
    mel.connect_material_expressions(dark, "", lerp, "A")
    mel.connect_material_expressions(light, "", lerp, "B")
    mel.connect_material_expressions(rand, "", lerp, "Alpha")
    mel.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -350, 250)
    rough.set_editor_property("r", 0.9)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    unreal.EditorAssetLibrary.save_loaded_asset(mat)
    return path


# ---------------------------------------------------------------- graphs

# OWNERSHIP (2026-07-27): the biome graphs are authored by the C++ commandlet
# (-run=OWCreateBiomePCG, editor closed) because the PCG attribute selector is
# unreachable from python (docs/landscape_migration/pitfalls_from_source.md).
# The old python graph builders were retired and are not ported. This script
# only verifies the graphs exist.
@step("graphs_exist_check")
def graphs_exist_check():
    # Keep this list and the commandlet's "N graphs ... 0 failed" summary
    # moving together (the check went stale twice in the source project).
    expected = tuple(f"PCG_OW{b}" for b in BIOMES)
    missing = [n for n in expected
               if not unreal.EditorAssetLibrary.does_asset_exist(f"{ASSET_DIR}/{n}")]
    if missing:
        raise RuntimeError(f"graphs missing: {missing} - run the OWCreateBiomePCG "
                           "commandlet first (editor closed)")
    return f"all {len(expected)} graphs present (commandlet-authored)"


# ---------------------------------------------------------------- level rig

@step("biome_actors")
def biome_actors():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_name() != MAP_NAME:
        # Headless session: load the map, same route the RVT-volume
        # script uses.
        unreal.EditorLoadingAndSavingUtils.load_map(MAP)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if not world or world.get_name() != MAP_NAME:
            raise RuntimeError(f"open {MAP_NAME} first (current: {world and world.get_name()})")
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing = {a.get_actor_label(): a for a in actors_sub.get_all_level_actors()}
    # Bounded-sampler graduation (2026-07-30, canvas port): the graphs'
    # surface samplers are now bUnbounded=False and clip to the owning
    # actor's bounds. A bare StaticMeshActor has ~no bounds, so every
    # biome actor gets a BoxComponent sized to the LAB landscape (canvas
    # work volumes reuse this pattern at user-chosen sizes).
    landscapes = [a for a in actors_sub.get_all_level_actors()
                  if isinstance(a, unreal.LandscapeProxy)]
    if not landscapes:
        raise RuntimeError("no landscape found for PCG bounds sizing")
    l_origin, l_extent = landscapes[0].get_actor_bounds(False)
    out = []
    # RL2 added the Road graph actor; RC added Cliff (BP_OWCliffWall splines);
    # RC-A added Alpine.
    for biome in BIOMES:
        label = f"DRESSLAB_PCG_{biome}"
        actor = existing.get(label)
        if actor is None:
            actor = actors_sub.spawn_actor_from_class(
                unreal.StaticMeshActor, unreal.Vector(100800, 100800, 0))
            actor.set_actor_label(label)
        comp = actor.get_component_by_class(unreal.PCGComponent)
        if comp is None:
            sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
            handles = sub.k2_gather_subobject_data_for_instance(actor)
            params = unreal.AddNewSubobjectParams(
                parent_handle=handles[0], new_class=unreal.PCGComponent)
            handle, fail = sub.add_new_subobject(params)
            if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
                raise RuntimeError(f"add PCGComponent failed on {label}: {fail}")
            comp = actor.get_component_by_class(unreal.PCGComponent)
        box = actor.get_component_by_class(unreal.BoxComponent)
        if box is None:
            sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
            handles = sub.k2_gather_subobject_data_for_instance(actor)
            params = unreal.AddNewSubobjectParams(
                parent_handle=handles[0], new_class=unreal.BoxComponent)
            handle, fail = sub.add_new_subobject(params)
            if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
                raise RuntimeError(f"add BoxComponent failed on {label}: {fail}")
            box = actor.get_component_by_class(unreal.BoxComponent)
        actor.set_actor_location(
            unreal.Vector(l_origin.x, l_origin.y, l_origin.z), False, False)
        box.set_box_extent(unreal.Vector(
            l_extent.x, l_extent.y, l_extent.z + 5000.0), False)
        box.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        got = box.get_editor_property("box_extent")
        if abs(got.x - l_extent.x) > 1.0:
            raise RuntimeError(f"{label}: box extent read-back {got} != {l_extent}")
        comp.set_graph(unreal.load_asset(f"{ASSET_DIR}/PCG_OW{biome}"))
        try:
            comp.set_editor_property(
                "generation_trigger",
                unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
        except Exception as exc:
            unreal.log_warning(f"BIOME_PCG trigger not set on {label}: {exc!r}")
        comp.generate(True)
        actor.modify()
        out.append(label)
    return out


@step("save_all")
def save_all():
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return "saved"


REPORT = Path(__file__).with_name("ClaudeSetupBiomePCGReport.json")
REPORT.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT}")
unreal.log("BIOME_PCG setup complete - paint layers, then Generate on DRESSLAB_PCG_* actors")
