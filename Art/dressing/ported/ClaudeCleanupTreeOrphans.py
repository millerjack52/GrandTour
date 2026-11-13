"""Lab tree cleanup (queued in handoff 2026-07-28): deletes the placed
tree-lineup StaticMeshActors from MAP (the source used its dressing lab) and the
orphaned tree mesh
assets superseded by the _A/_B/_C siblings (un-suffixed SM_OWFir_* /
SM_OWBirch_Sparse + the manual SM_OWFir_BareGiant2/BareTall2 duplicates).

RUN IN-EDITOR with MAP open:
  py "C:/GrandTour/Art/dressing/ported/ClaudeCleanupTreeOrphans.py" [/Game/Map/Path]
(map defaults to MAP below; the first argv entry starting with /Game/ overrides it)

Actors are deleted BEFORE assets (a placed actor holds a reference that
blocks delete_asset). delete_asset can leave a zombie .uasset on disk even
when it returns True (paid-for pitfall) - the report lists any survivors to
Remove-Item in a later editor-closed session.
"""

import json
import sys
import traceback
from pathlib import Path

import unreal

# Map this script works on. Override: the first argv entry that starts with
# /Game/ (py "<script>" /Game/Some/L_Map).
MAP = "/Game/GrandTour/Test/L_OWToolkitTest"
for _arg in getattr(sys, "argv", [])[1:]:
    if _arg.startswith("/Game/"):
        MAP = _arg
        break
MAP_NAME = MAP.rsplit("/", 1)[-1]
TREES_DIR = "/Game/OWGame/Dev/DressingLab/Trees"
SEARCH_DIRS = ["/Game/OWGame/Dev/DressingLab"]

# Lineup actors: vendor originals placed for comparison + OW variant lineups.
ACTOR_EXACT = {"SM_Beech", "SM_Birch", "SM_FirTree"}
ACTOR_PREFIXES = ("SM_OWFir_", "SM_OWBirch_", "SM_OWBeech")
# NEVER touch (other arcs' props share the map):
ACTOR_PROTECT_PREFIXES = ("SM_HedgeKnight", "SM_OWBLD_", "DRESSLAB_")

# Orphaned assets: superseded un-suffixed variants + manual duplicates.
ORPHAN_ASSET_NAMES = {
    "SM_OWFir_TallSparse", "SM_OWFir_AncientSparse",
    "SM_OWFir_BareTall", "SM_OWFir_BareGiant",
    "SM_OWBirch_Sparse",
    "SM_OWFir_BareGiant2", "SM_OWFir_BareTall2",
}

REPORT_PATH = Path(__file__).with_name("ClaudeCleanupTreeOrphansReport.json")
report = {"ok": True, "steps": {}}


def step(name):
    def deco(fn):
        def wrap(*a, **k):
            try:
                r = fn(*a, **k)
                report["steps"][name] = {"ok": True, "result": r}
                return r
            except Exception as exc:  # noqa: BLE001
                report["steps"][name] = {
                    "ok": False,
                    "error": "{}: {}".format(type(exc).__name__, exc),
                    "trace": traceback.format_exc(),
                }
                report["ok"] = False
                raise
        return wrap
    return deco


@step("delete_lineup_actors")
def delete_lineup_actors():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or world.get_name() != MAP_NAME:
        raise RuntimeError("open {} first (current: {})".format(
            MAP_NAME, world.get_name() if world else "none"))
    actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    deleted, kept = [], []
    for a in list(actors_sub.get_all_level_actors()):
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        label = a.get_actor_label()
        if any(label.startswith(p) for p in ACTOR_PROTECT_PREFIXES):
            kept.append(label)
            continue
        if label in ACTOR_EXACT or any(label.startswith(p) for p in ACTOR_PREFIXES):
            actors_sub.destroy_actor(a)
            deleted.append(label)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return {"deleted": deleted, "protected_seen": kept}


@step("delete_orphan_assets")
def delete_orphan_assets():
    deleted, failed, missing = [], [], []
    seen = set()
    for root in SEARCH_DIRS:
        for ap in unreal.EditorAssetLibrary.list_assets(root, recursive=True, include_folder=False):
            name = ap.split("/")[-1].split(".")[0]
            if name in ORPHAN_ASSET_NAMES and ap not in seen:
                seen.add(ap)
                if unreal.EditorAssetLibrary.delete_asset(ap):
                    deleted.append(ap)
                else:
                    failed.append(ap)
    found_names = {p.split("/")[-1].split(".")[0] for p in seen}
    missing = sorted(ORPHAN_ASSET_NAMES - found_names)
    if failed:
        raise RuntimeError("delete_asset refused: {} (still referenced? "
                           "check the map for remaining lineup actors)".format(failed))
    return {"deleted": deleted, "not_found": missing}


try:
    delete_lineup_actors()
    delete_orphan_assets()
finally:
    REPORT_PATH.write_text(json.dumps(report, indent=2, default=str))

if not report["ok"]:
    raise RuntimeError("cleanup failed; see {}".format(REPORT_PATH))
unreal.log("TREE ORPHAN CLEANUP complete - see report for the deleted list")
