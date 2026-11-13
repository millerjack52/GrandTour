"""Shape the road BED and paint OW_RoadVerge along every BP_OWRoad*
spline using the engine's own spline-apply
(LandscapeProxy.editor_apply_spline) - the same machinery landscape
splines use, running IN-EDITOR where the edit-layer merge is alive.

Two passes per road (user 2026-07-30, deformation DEFAULT ON):
  1. HEIGHTS: raise+lower the terrain to the spline at road width with
     a blend falloff - the worn-bed look; roads hug slopes. Set
     DEFORM_BED = False to skip (paint-only, the pre-2026-07-30
     behavior). One-way like the paint: re-routing a road does not
     auto-revert the old bed.
  2. PAINT: the verge kill-switch layer at exactly road width, zero
     falloff (grass to the edge).

RUN IN-EDITOR (console, map open):  py "C:/GrandTour/Art/dressing/ported/ClaudePaintRoadVerge.py"
Rerunnable - run again after drawing new roads. Deforming terrain moves
the ground under existing PCG dressing: fire Generate on the biome +
road PCG actors afterwards (or rerun the tune script).

Route history (2026-07-30): the headless commandlet route
(-run=OWPaintRoadVerge) writes correct layer data but the edit-layer
COMPOSITE merge is dormant in commandlets (engine guards; runs 1-5 in
the handoff record) - its read-back gate now fails honestly. This
in-editor script is the WORKING route.
"""

from __future__ import annotations

import json
from pathlib import Path
import traceback

import unreal


ROAD_CLASSES = ("BP_OWRoad_C", "BP_OWRoad_Dusty_C", "BP_OWRoad_Gravel_C")
LAYER_INFO_NAME = "OW_RoadVerge_LayerInfo"   # asset name (per-map copies exist)
VERGE_LAYER_NAME = "OW_RoadVerge"            # TARGET LAYER name on the landscape
EDIT_LAYER_NAME = "Layer"                    # preferred; validated per map
# editor_apply_spline widths are in spline-component local space (road
# actors are unscaled). ROAD-WIDTH-ONLY as of 2026-07-30 (user: grass
# should grow right up to the road edge, no cleared band): core = the
# road half-width 200, zero falloff. NOTE: repainting at a narrower
# width does NOT erase a previously painted wider band - roads painted
# under the old 240+80 values keep their clearing until the excess is
# brush-erased in the Paint panel (the interactive brush normalizes
# siblings; scripts cannot - kill-switch doctrine).
HALF_WIDTH = 200.0
SIDE_FALLOFF = 0.0
# Bed deformation (pass 1): same core width, wide blend so the bed
# melts into the surroundings instead of leaving a vertical seam.
DEFORM_BED = True
DEFORM_SIDE_FALLOFF = 250.0

REPORT_PATH = Path(__file__).with_name("ClaudePaintRoadVergeReport.json")

result = {"ok": True, "steps": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"ROADVERGE {name}: {exc!r}")
            return None

    return decorate


def _landscape():
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    landscapes = [a for a in actors_sub.get_all_level_actors()
                  if isinstance(a, unreal.LandscapeProxy)]
    if not landscapes:
        raise RuntimeError("no landscape in the open level")
    return landscapes[0]


@step("find_layer_info")
def find_layer_info():
    """Resolve OW_RoadVerge's layer info FROM THE OPEN MAP'S LANDSCAPE.

    PAID 2026-07-30 (canvas round: roads stayed grassy, report said ok):
    every map owns its OWN *_LayerInfo assets (L_OWDressingLab_sharedassets
    vs L_OWWorldCanvas_sharedassets), and EditorApplySpline's PaintLayer
    contract is exact - "The landscape must be configured with the SAME
    layer info in one of its layers or this will do nothing!"
    (LandscapeProxy.h:1036). The old registry name-search returned
    whichever asset sorted first (the lab's) and painted NOTHING on the
    canvas, silently. Ask the landscape instead: target_layers is a
    Map(FName -> FLandscapeTargetLayerSettings.LayerInfoObj).
    """
    landscape = _landscape()
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    target_layers = landscape.get_editor_property("target_layers")
    found = None
    available = []
    for key in target_layers.keys():
        available.append(str(key))
        if str(key) == VERGE_LAYER_NAME:
            found = target_layers[key].get_editor_property("layer_info_obj")
    if found is None:
        raise RuntimeError(
            f"{VERGE_LAYER_NAME} has NO layer info on this map's landscape "
            f"({world.get_name() if world else '?'}). Create it in the Paint "
            f"panel (Target Layers -> {VERGE_LAYER_NAME} -> Create Layer Info, "
            f"Weight-Blended), then rerun. Target layers present: {available}")
    return {"map": world.get_name() if world else None,
            "layer_info": found.get_path_name()}


@step("find_edit_layer")
def find_edit_layer():
    """Pick a VALID edit layer name (ALandscape.GetEditLayers, Landscape.h
    :394). Passing a name the landscape does not have makes the spline
    apply a no-op; "" is the engine's own default (apply without
    targeting a specific edit layer)."""
    landscape = _landscape()
    names = []
    try:
        for lay in landscape.get_edit_layers():
            try:
                names.append(str(lay.get_editor_property("name")))
            except Exception:
                names.append(str(lay.get_name()))
    except Exception as exc:
        return {"edit_layers": f"unavailable ({type(exc).__name__})",
                "using": EDIT_LAYER_NAME}
    if not names:
        return {"edit_layers": [], "using": ""}   # no edit layers on this map
    using = EDIT_LAYER_NAME if EDIT_LAYER_NAME in names else names[0]
    return {"edit_layers": names, "using": using}


@step("paint_roads")
def paint_roads():
    info_step = result["steps"]["find_layer_info"]
    if not info_step["ok"]:
        raise RuntimeError("layer info unresolved - see find_layer_info")
    layer_info = unreal.load_asset(
        info_step["value"]["layer_info"].split(".")[0])
    el_step = result["steps"].get("find_edit_layer", {})
    edit_layer = (el_step.get("value") or {}).get("using", EDIT_LAYER_NAME)
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    landscape = _landscape()
    painted = []
    for actor in actors_sub.get_all_level_actors():
        if actor.get_class().get_name() not in ROAD_CLASSES:
            continue
        spline = actor.get_component_by_class(unreal.SplineComponent)
        if spline is None:
            continue
        if DEFORM_BED:
            landscape.editor_apply_spline(
                spline,
                start_width=HALF_WIDTH, end_width=HALF_WIDTH,
                start_side_falloff=DEFORM_SIDE_FALLOFF,
                end_side_falloff=DEFORM_SIDE_FALLOFF,
                start_roll=0.0, end_roll=0.0,
                num_subdivisions=40,
                raise_heights=True, lower_heights=True,
                paint_layer=None,
                edit_layer_name=edit_layer)
        landscape.editor_apply_spline(
            spline,
            start_width=HALF_WIDTH, end_width=HALF_WIDTH,
            start_side_falloff=SIDE_FALLOFF, end_side_falloff=SIDE_FALLOFF,
            start_roll=0.0, end_roll=0.0,
            num_subdivisions=40,
            raise_heights=False, lower_heights=False,
            paint_layer=layer_info,
            edit_layer_name=edit_layer)
        painted.append(f"{actor.get_actor_label()} "
                       f"({actor.get_class().get_name()})"
                       f"{' +bed' if DEFORM_BED else ''}")
    if not painted:
        raise RuntimeError(
            "no BP_OWRoad* actors found in the OPEN level. On World "
            "Partition maps only LOADED cells enumerate - load the region "
            "containing the roads, or check you are in the right map.")
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    return {"map": world.get_name() if world else None,
            "edit_layer": edit_layer,
            "layer_info": layer_info.get_path_name(),
            "roads": painted}


@step("flush_grass_and_save")
def flush_grass_and_save():
    unreal.SystemLibrary.execute_console_command(None, "grass.FlushCache")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return "grass flushed, dirty packages saved"


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("ROADVERGE paint complete - grass should clear off the roads "
           "within a few seconds")
