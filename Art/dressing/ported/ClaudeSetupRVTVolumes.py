"""RV0 of Docs/RVTGroundRoundPlan.md: spawn/refresh the two
RuntimeVirtualTextureVolume actors in MAP, pointed at the pack's RVT
assets (vendor, referenced only), bounds-matched to the map's landscape.

RUN IN-EDITOR (AFTER VT support is enabled in Project Settings + editor
restart; loads MAP if another map is open):
  py "C:/GrandTour/Art/dressing/ported/ClaudeSetupRVTVolumes.py" [/Game/Map/Path]
(map defaults to MAP below; the first argv entry starting with /Game/ overrides it)
or headless (PowerShell; the argv map override is unverified headless, MAP default needs none):
  & 'C:\\Program Files\\Epic Games\\UE_5.8\\Engine\\Binaries\\Win64\\UnrealEditor-Cmd.exe'
    C:\\GrandTour\\GrandTour.uproject -run=PythonScript
    "-Script=C:/GrandTour/Art/dressing/ported/ClaudeSetupRVTVolumes.py"
    -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"

Rerunnable: deletes + respawns its own two actors each run. NOTE: the
ClaudeSetupDressingLab.py lighting_rig purge deletes any DRESSLAB_-
prefixed actor that is not DRESSLAB_PCG_ - so RERUN THIS SCRIPT after
every lab-setup rerun.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback

import unreal

# Map this script works on. Override: the first argv entry that starts with
# /Game/ (py "<script>" /Game/Some/L_Map).
MAP = "/Game/GrandTour/Test/L_OWToolkitTest"
for _arg in getattr(sys, "argv", [])[1:]:
    if _arg.startswith("/Game/"):
        MAP = _arg
        break
MAP_NAME = MAP.rsplit("/", 1)[-1]

RVT_MATERIAL = "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material"
RVT_HEIGHT = "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Height"
VOLUMES = [("DRESSLAB_RVT_Material", RVT_MATERIAL),
           ("DRESSLAB_RVT_Height", RVT_HEIGHT)]

# RL0 (Docs/RoadLookRoundPlan.md) volume density knob:
#   "full"    - whole 2016m lab landscape (RVT texel density ~2.7x
#               blurrier per axis than the demo's 756m volume).
#   "working" - demo texel parity over the road test area ONLY. Ground
#               OUTSIDE the box samples the RVT out of bounds = BLACK.
# DECISION RECORDED 2026-07-29 (plan RL0.3, either/or): the planned
# coverage-lerp fallback is NOT implementable - the engine's
# MaterialExpressionRuntimeVirtualTextureReplace (header verified) is a
# render-PASS switch (inputs: Default / VirtualTextureOutput), not a
# spatial validity signal; in the display pass it always returns its
# Default input, so out-of-volume ground stays black with or without it.
# The pack's own landscape master does not use it either (T3D check).
# Per the plan's else-branch: DEFAULT "full", skip the lerp. "working"
# stays available for a user-accepted black-horizon tradeoff run in the
# lab; the production texel-density decision (own higher-res RVT asset =
# own-grass-master round) is the user's, recorded in the handoff.
VOLUME_MODE = "full"
WORKING_CENTER = (-74000.0, 19600.0)   # user road test area (RL plan)
WORKING_SIZE = 75600.0                 # 756m = demo volume footprint

REPORT_PATH = Path(__file__).with_name("ClaudeSetupRVTVolumesReport.json")

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
            unreal.log_error(f"RVTVOL {name}: {exc!r}")
            return None

    return decorate


@step("find_landscape")
def find_landscape():
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_name() != MAP_NAME:
        # Headless session (or another map open): load MAP.
        unreal.EditorLoadingAndSavingUtils.load_map(MAP)
    landscapes = [a for a in actors_sub.get_all_level_actors()
                  if isinstance(a, unreal.LandscapeProxy)]
    if not landscapes:
        raise RuntimeError(f"no landscape found in {MAP}")
    return {"map": MAP, "landscape": landscapes[0].get_actor_label()}


@step("spawn_volumes")
def spawn_volumes():
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    landscape = [a for a in actors_sub.get_all_level_actors()
                 if isinstance(a, unreal.LandscapeProxy)][0]
    origin, extent = landscape.get_actor_bounds(False)
    made = []
    for label, rvt_path in VOLUMES:
        rvt = unreal.load_asset(rvt_path)
        if rvt is None:
            raise RuntimeError(f"RVT asset failed to load: {rvt_path}")
        for a in list(actors_sub.get_all_level_actors()):
            if a.get_actor_label() == label:
                actors_sub.destroy_actor(a)
        # VERIFIED CONVENTION (diffed against the pack demo map's working
        # volumes, 2026-07-29): the volume's local box spans 0..1 from the
        # actor origin - ACTOR LOCATION = BOUNDS MIN CORNER, actor scale =
        # full size. Placing the actor at the landscape CENTER shifted
        # coverage half a map off (black-landscape incident, quadrant
        # mismatch).
        z_margin = 2500.0
        z_size = extent.z * 2.0 + z_margin * 2.0
        if VOLUME_MODE == "working":
            half = WORKING_SIZE / 2.0
            min_corner = unreal.Vector(WORKING_CENTER[0] - half,
                                       WORKING_CENTER[1] - half,
                                       origin.z - extent.z - z_margin)
            scale = unreal.Vector(WORKING_SIZE, WORKING_SIZE, z_size)
        else:
            min_corner = unreal.Vector(origin.x - extent.x, origin.y - extent.y,
                                       origin.z - extent.z - z_margin)
            scale = unreal.Vector(extent.x * 2.0, extent.y * 2.0, z_size)
        vol = actors_sub.spawn_actor_from_class(
            unreal.RuntimeVirtualTextureVolume, min_corner)
        vol.set_actor_label(label)
        comp = vol.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
        comp.set_editor_property("virtual_texture", rvt)
        if VOLUME_MODE != "working":
            # "working" must NOT re-align to the landscape - alignment
            # would snap the box back out to full landscape coverage.
            comp.set_editor_property("bounds_align_actor", landscape)
        vol.set_actor_scale3d(scale)
        vol.modify()
        made.append(f"{label} -> {rvt.get_name()} MODE={VOLUME_MODE} "
                    f"min-corner {min_corner} size {scale.x:.0f}x{scale.y:.0f}")
    return made


@step("verify_and_report")
def verify_and_report():
    """Read back both volumes; report bounds vs landscape so the user can
    judge whether a manual 'Set Bounds' click is needed."""
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    landscape = [a for a in actors_sub.get_all_level_actors()
                 if isinstance(a, unreal.LandscapeProxy)][0]
    l_origin, l_extent = landscape.get_actor_bounds(False)
    out = {"landscape": f"origin {l_origin} extent {l_extent}"}
    for label, rvt_path in VOLUMES:
        hits = [a for a in actors_sub.get_all_level_actors()
                if a.get_actor_label() == label]
        if len(hits) != 1:
            raise RuntimeError(f"{label}: expected 1 actor, found {len(hits)}")
        comp = hits[0].get_component_by_class(unreal.RuntimeVirtualTextureComponent)
        got = comp.get_editor_property("virtual_texture")
        if got is None or got.get_path_name().split(".")[0] != rvt_path:
            raise RuntimeError(f"{label}: virtual_texture read-back mismatch: {got}")
        v_origin, v_extent = hits[0].get_actor_bounds(False)
        out[label] = f"origin {v_origin} extent {v_extent}"
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return out


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
if not result["ok"]:
    raise RuntimeError(f"one or more steps failed - see {REPORT_PATH}")
unreal.log("RVTVOL volumes ready - if volume extents mismatch the landscape, "
           "click 'Set Bounds' on each volume's component once")
