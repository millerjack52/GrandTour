"""Regenerate a map's biome PCG volumes and SAVE, so the level's instances
actually match the current graphs.

REFERENCE ONLY in GrandTour: written for the source project's dressing lab.

WHY THIS EXISTS: after a graph fix, a saved level keeps the instances it was
generated with. Telling the user to press Generate is not a fix; this does it.

SELF-VERIFYING AND CONSERVATIVE: it fingerprints every PCG volume's instances
(per-volume ISM instance count plus a coarse position sum) before and after,
and SAVES ONLY IF the fingerprint actually changed. If PCG generation does not
run in this session (it is normally an editor-tick-driven async job, which a
commandlet does not pump), the fingerprint is unchanged and nothing is
written - a no-op, not a wrecked level.

Deliberately does NOT cleanup-then-generate: if generation silently never runs,
cleanup alone would delete the existing dressing and leave the map empty.

Generation needs a ticking editor, so the useful route is IN-EDITOR:
  py "C:/GrandTour/Art/dressing/ported/ClaudeRegenerateLabDressing.py" [/Game/Map/Path]
(map defaults to MAP below; the first argv entry starting with /Game/ overrides it)
Headless it loads and measures but normally saves nothing:
  UnrealEditor-Cmd.exe C:\\GrandTour\\GrandTour.uproject -run=PythonScript
    "-Script=C:/GrandTour/Art/dressing/ported/ClaudeRegenerateLabDressing.py"
    -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import traceback

import unreal

# Map to regenerate. Override: the first argv entry that starts with /Game/.
MAP = "/Game/GrandTour/Test/L_OWToolkitTest"
for _arg in getattr(sys, "argv", [])[1:]:
    if _arg.startswith("/Game/"):
        MAP = _arg
        break
VOLUME_PREFIXES = ("DRESSLAB_PCG_", "CANVAS_PCG_")
MAX_SAMPLES = 3000

REPORT_PATH = Path(__file__).with_name("ClaudeRegenerateLabDressingReport.json")
result = {"ok": True, "map": MAP, "steps": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {"ok": False, "error": repr(exc),
                                     "traceback": traceback.format_exc()}
            unreal.log_error(f"LABREGEN {name}: {exc!r}")
            return None

    return decorate


def _actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


unreal.EditorLoadingAndSavingUtils.load_map(MAP)


def _fingerprint():
    """Per-volume (instance count, rounded position sum over a strided sample)."""
    prints = {}
    for actor in _actors():
        label = actor.get_actor_label()
        if not label.startswith(VOLUME_PREFIXES):
            continue
        count_total = 0
        pos_sum = 0.0
        for comp in actor.get_components_by_class(unreal.InstancedStaticMeshComponent):
            count = comp.get_instance_count()
            count_total += count
            stride = max(1, count // MAX_SAMPLES)
            for i in range(0, count, stride):
                loc = comp.get_instance_transform(i, world_space=True).translation
                pos_sum += loc.x + loc.y + loc.z
        prints[label] = [count_total, round(pos_sum, 0)]
    return prints


@step("regenerate_and_verify")
def regenerate():
    before = _fingerprint()
    if not before:
        raise RuntimeError(f"no {VOLUME_PREFIXES} PCG volumes in {MAP}")

    volumes = []
    for actor in _actors():
        label = actor.get_actor_label()
        if not label.startswith(VOLUME_PREFIXES):
            continue
        for comp in actor.get_components_by_class(unreal.PCGComponent):
            # bForce=True ignores cached/serialized data.
            comp.generate_local(True)
            volumes.append(label)

    after = _fingerprint()
    changed = sorted(label for label in after if after[label] != before.get(label))

    saved = False
    if changed:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        saved = True

    return {
        "volumes_generated": volumes,
        "fingerprint_before": before,
        "fingerprint_after": after,
        "changed_volumes": changed,
        "saved": saved,
        "note": ("SAVED - the level now matches the graphs" if saved else
                 "NOT SAVED - generation did not change any instance in this "
                 "session (PCG generation is editor-tick driven and a "
                 "commandlet may not pump it, or the graphs already matched). "
                 "Nothing was destroyed; escalate to an editor-mode run or the "
                 "PCG world-partition builder."),
    }


REPORT_PATH.write_text(json.dumps(result, indent=2, default=str))
unreal.log(f"LABREGEN report -> {REPORT_PATH}")
if not result["ok"]:
    raise RuntimeError("lab regen FAILED - see report")
