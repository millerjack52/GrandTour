"""Canvas dressing graduation (user 2026-07-30): point the dressing kit
at a map (the source used L_OWWorldCanvas). Assigns M_OWDressingLab + the two
pack RVTs to the map's landscape and spawns BOUNDED work-volume PCG actors
(CANVAS_PCG_Forest/Meadow/Scree/Road/Cliff/Alpine, 500m boxes) that the user moves /
resizes / duplicates over areas being dressed - Generate fires per
volume, never the whole canvas (samplers are bounded as of the port).
Touches NO heights and NO layer infos (Paint panel, one-time, user).

REFERENCE ONLY in GrandTour (bound to the source's canvas map).

RUN IN-EDITOR with the map OPEN:
  py "C:/GrandTour/Art/dressing/ported/ClaudeSetupCanvasDressing.py" [/Game/Map/Path]
(map defaults to MAP below; the first argv entry starting with /Game/ overrides it)
Then run ClaudeSetupRVTVolumes.py (it sizes to the OPEN map's landscape)
and create the paint layers in the Paint panel (reuse the existing
*_LayerInfo assets). Rerunnable (get-or-create; existing work volumes
keep their user-set positions/sizes).
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback

import unreal

# Map that must be open. Override: the first argv entry that starts with /Game/.
MAP = "/Game/GrandTour/Test/L_OWToolkitTest"
for _arg in getattr(sys, "argv", [])[1:]:
    if _arg.startswith("/Game/"):
        MAP = _arg
        break
MAP_NAME = MAP.rsplit("/", 1)[-1]
ASSET_DIR = "/Game/OWGame/Dev/DressingLab"
RVTS = ["/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material",
        "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Height"]
WORK_EXTENT = unreal.Vector(25000.0, 25000.0, 30000.0)  # 500m x 500m box

REPORT_PATH = Path(__file__).with_name("ClaudeSetupCanvasDressingReport.json")
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
                "ok": False, "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
            unreal.log_error(f"CANVASDRESS {name}: {exc!r}")
            return None
    return decorate


@step("check_map")
def check_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_name() != MAP_NAME:
        raise RuntimeError(f"open {MAP_NAME} first (current: "
                           f"{world.get_name() if world else None})")
    return MAP_NAME


@step("landscape_material_rvt")
def landscape_material_rvt():
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    landscapes = [a for a in actors_sub.get_all_level_actors()
                  if isinstance(a, unreal.LandscapeProxy)]
    if not landscapes:
        raise RuntimeError(f"no landscape in {MAP_NAME}")
    mat = unreal.load_asset(f"{ASSET_DIR}/M_OWDressingLab")
    rvts = [unreal.load_asset(p) for p in RVTS]
    if mat is None or any(r is None for r in rvts):
        raise RuntimeError("material or RVT assets failed to load")
    out = []
    for ls in landscapes:
        ls.set_editor_property("landscape_material", mat)
        ls.set_editor_property("runtime_virtual_textures", rvts)
        got_m = ls.get_editor_property("landscape_material")
        got_r = ls.get_editor_property("runtime_virtual_textures")
        if got_m is None or got_m.get_name() != "M_OWDressingLab" or len(got_r) != 2:
            raise RuntimeError(f"{ls.get_actor_label()}: assignment read-back failed")
        ls.modify()
        out.append(f"{ls.get_actor_label()}: material + 2 RVTs")
    return out


@step("work_volumes")
def work_volumes():
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    existing = {a.get_actor_label(): a for a in actors_sub.get_all_level_actors()}
    sub = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    out = []
    for i, biome in enumerate(("Forest", "Meadow", "Scree", "Road", "Cliff",
                               "Alpine")):
        label = f"CANVAS_PCG_{biome}"
        actor = existing.get(label)
        created = actor is None
        if created:
            # Spawn at the canvas center; the user repositions per work area.
            actor = actors_sub.spawn_actor_from_class(
                unreal.StaticMeshActor, unreal.Vector(100800 + i * 2000, 100800, 0))
            actor.set_actor_label(label)
        for cls, tag in ((unreal.PCGComponent, "PCG"), (unreal.BoxComponent, "Box")):
            if actor.get_component_by_class(cls) is None:
                handles = sub.k2_gather_subobject_data_for_instance(actor)
                params = unreal.AddNewSubobjectParams(
                    parent_handle=handles[0], new_class=cls)
                handle, fail = sub.add_new_subobject(params)
                if not unreal.SubobjectDataBlueprintFunctionLibrary.is_handle_valid(handle):
                    raise RuntimeError(f"add {tag} failed on {label}: {fail}")
        box = actor.get_component_by_class(unreal.BoxComponent)
        if created:  # keep user-resized boxes on rerun
            box.set_box_extent(WORK_EXTENT, False)
        box.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        comp = actor.get_component_by_class(unreal.PCGComponent)
        graph = unreal.load_asset(f"{ASSET_DIR}/PCG_OW{biome}")
        if graph is None:
            raise RuntimeError(f"graph missing: PCG_OW{biome}")
        comp.set_graph(graph)
        try:
            comp.set_editor_property(
                "generation_trigger",
                unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
        except Exception as exc:
            unreal.log_warning(f"CANVASDRESS trigger not set on {label}: {exc!r}")
        # NO generate here - the user places the volume first, then hits
        # Generate on the actor (bounded = only the box gets dressed).
        actor.modify()
        out.append(f"{label}{' (new)' if created else ' (kept)'}")
    return out


@step("save_all")
def save_all():
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return "dirty packages saved (WP external actors incl.)"


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
unreal.log(f"CANVASDRESS report -> {REPORT_PATH}")
if not result["ok"]:
    raise RuntimeError("canvas dressing setup FAILED - see report")
unreal.log("CANVASDRESS ready: run ClaudeSetupRVTVolumes.py, create paint "
           "layers in the Paint panel, place the CANVAS_PCG_* volumes, "
           "paint, Generate.")
