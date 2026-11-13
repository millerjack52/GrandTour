"""Fix biome generation: ensure the PCGWorldActor exists, then force-generate.

The Get Landscape Data node reads the landscape through a cache hosted on
APCGWorldActor. The editor spawns that actor silently when a PCG component
is added through the UI — a scripted component add bypasses it, and
generation then fails with "Landscape data is unable to access the
landscape cache". Rerunnable.

PIPELINE (regeneration chain). Acts on the OPEN level; generation needs a
ticking editor, so run it IN-EDITOR with the map open:
    py "C:/GrandTour/Art/dressing/ported/ClaudeFixBiomeGenerate.py"

GrandTour port: the source generated one "PCG_BiomeHost" actor on its slice
map; this port generates every actor whose label matches HOST_LABELS (the
source host plus the DRESSLAB_PCG_* / CANVAS_PCG_* biome volumes), and writes
the per-step report the GrandTour gates read.
"""
import json
import traceback
from pathlib import Path

import unreal

# Exact label or label prefix of the PCG host actors to generate.
HOST_LABELS = ("PCG_BiomeHost", "DRESSLAB_PCG_", "CANVAS_PCG_")

REPORT_PATH = Path(__file__).with_name("ClaudeFixBiomeGenerateReport.json")
report = {"ok": True, "steps": {}}


def step(name):
    def decorate(func):
        try:
            value = func()
            report["steps"][name] = {"ok": True, "value": value}
            return value
        except Exception as exc:
            report["ok"] = False
            report["steps"][name] = {"ok": False, "error": repr(exc),
                                     "traceback": traceback.format_exc()}
            unreal.log_error(f"BIOME FIX {name}: {exc!r}")
            return None

    return decorate


def actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


@step("pcg_world_actor")
def pcg_world_actor():
    """1. Ensure the PCG world actor exists."""
    if any(isinstance(a, unreal.PCGWorldActor) for a in actors().get_all_level_actors()):
        return "already present"
    spawned = actors().spawn_actor_from_class(
        unreal.PCGWorldActor, unreal.Vector(0.0, 0.0, 0.0), unreal.Rotator(0.0, 0.0, 0.0))
    if not spawned:
        raise RuntimeError("failed to spawn PCGWorldActor")
    return "spawned"


@step("generate")
def generate():
    """2. Force-generate the biome hosts so the scatter appears immediately."""
    generated = []
    for actor in actors().get_all_level_actors():
        label = actor.get_actor_label()
        if not label.startswith(HOST_LABELS):
            continue
        pcg = actor.get_component_by_class(unreal.PCGComponent)
        if not pcg:
            raise RuntimeError(f"{label} has no PCGComponent")
        pcg.generate_local(True)
        generated.append(label)
    if not generated:
        raise RuntimeError(f"no PCG host actor matching {HOST_LABELS} found")
    return {"requested": generated}


@step("save")
def save():
    """3. Save (the world actor is new level content). Skipped if a step failed."""
    if not report["ok"]:
        raise RuntimeError("not saving - an earlier step failed")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    return True


REPORT_PATH.write_text(json.dumps(report, indent=2, default=str))
unreal.log_warning("BIOME FIX: %s" % report)
if not report["ok"]:
    raise RuntimeError(f"biome fix FAILED - see {REPORT_PATH}")
