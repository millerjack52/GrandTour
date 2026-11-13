"""Stage C step 4 task (docs/LandscapeMigrationManifest.md 9.C.4): the ticking-editor pass on L_OWToolkitTest.

Run by tick_harness.ps1 only: its bootstrap Content/Python/init_unreal.py execs this file inside the full editor when
env GT_TOOLKIT_HARNESS names it. PCG generation and landscape edit-layer merges do nothing in a commandlet, hence the
real editor. Driven from a slate post-tick callback, one step at a time:
  1. waits for the editor world L_OWToolkitTest, then lets >= 6 s (and >= 30 ticks) of real ticks pass;
  2. measures, per road, the landscape height and OW_RoadVerge weight at the middle spline point (index n//2) and at
     half the spline length;
  3. calls OWRoadBedComponent.apply_bed_and_verge() on each BP_OWRoad*, lets >= 8 s of ticks pass, measures again;
  4. calls generate(True) on each OWBiome.* PCGVolume (never a cleanup first);
  5. polls every 2 s until every volume is generated and owns ISM instances and the counts hold for 3 polls, or
     10 minutes pass;
  6. saves dirty packages (maps + content), measures the roads a last time;
  7. writes tick_apply_and_generate_report.json (per-step ok, "finished": true) and calls quit_editor().
Heights: SystemLibrary.line_trace_single straight down (Visibility, complex) with every non-landscape actor ignored,
so the hit is the landscape collision. Verge weight: LandscapeComponent.editor_get_paint_layer_weight_at_location on
the component under the point (0..1).
The report is rewritten after every step, so a killed run still leaves its progress.
"""
import json
import time
import traceback
from pathlib import Path

import unreal

MAP_NAME = "L_OWToolkitTest"
VERGE_INFO = "/Game/OWGame/Dev/L_OWWorldCanvas_sharedassets/OW_RoadVerge_LayerInfo"
BIOMES = ["Forest", "Meadow", "Scree", "Road", "Cliff", "Alpine"]
WORLD_TIMEOUT_S = 20 * 60.0      # the harness kills the editor at 25 min
SETTLE_S, SETTLE_TICKS = 6.0, 30
AFTER_APPLY_S, AFTER_APPLY_TICKS = 8.0, 30
GEN_TIMEOUT_S = 600.0
POLL_S = 2.0
STABLE_POLLS = 3
COMPONENT_CM = 6300.0            # 63 quads x 100 cm (layout 9.C.1)
REPORT = Path(__file__).with_name("tick_apply_and_generate_report.json")

T0 = time.time()
result = {"ok": True, "finished": False, "method": {
    "height": "SystemLibrary.line_trace_single down, TRACE_TYPE_QUERY1 (Visibility), complex, all non-landscape "
              "actors ignored",
    "verge": "LandscapeComponent.editor_get_paint_layer_weight_at_location (0..1)"},
    "timeline_s": {}, "steps": {}}


def log(msg):
    unreal.log("GT_TICK_TASK " + str(msg))


def write_report():
    try:
        REPORT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    except Exception as exc:
        unreal.log_error("GT_TICK_TASK report write failed: %r" % exc)


def mark(name):
    result["timeline_s"][name] = round(time.time() - T0, 1)


def run_step(name, func):
    try:
        value = func()
        result["steps"][name] = {"ok": True, "value": value}
        log("%s ok: %s" % (name, json.dumps(value, default=str)[:600]))
    except Exception as exc:
        result["ok"] = False
        result["steps"][name] = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()}
        unreal.log_error("GT_TICK_TASK %s FAILED: %r" % (name, exc))
        value = None
    mark(name)
    write_report()
    return value


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def level_actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def landscape():
    found = [a for a in level_actors() if isinstance(a, unreal.LandscapeProxy)]
    if len(found) != 1:
        raise RuntimeError("expected 1 landscape, found %d" % len(found))
    return found[0]


def roads():
    found = sorted((a for a in level_actors() if a.get_class().get_name().startswith("BP_OWRoad")),
                   key=lambda a: a.get_class().get_name())
    if len(found) != 3:
        raise RuntimeError("expected 3 BP_OWRoad* actors, found %d" % len(found))
    return found


def biome_volumes():
    out = {}
    for biome in BIOMES:
        tag = unreal.Name("OWBiome." + biome)
        hits = [a for a in level_actors()
                if isinstance(a, unreal.PCGVolume) and tag in a.get_editor_property("tags")]
        if len(hits) != 1:
            raise RuntimeError("expected 1 volume tagged OWBiome.%s, found %d" % (biome, len(hits)))
        out[biome] = hits[0]
    return out


def ism_instances(actor):
    comps = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    return len(comps), sum(c.get_instance_count() for c in comps)


def ground_z(world, land, ignore, x, y):
    hit = unreal.SystemLibrary.line_trace_single(
        world, unreal.Vector(x, y, 20000.0), unreal.Vector(x, y, -20000.0),
        unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore, unreal.DrawDebugTrace.NONE, True)
    if hit is None:
        return None, None
    # HitResult's fields are not Python-visible; to_tuple() runs its native break (GameplayStatics.BreakHitResult,
    # which Python does not expose by name): blocking, overlap, time, distance, location, impact point, ...
    vals = hit.to_tuple()
    vecs = [v for v in vals if isinstance(v, unreal.Vector)]
    actors = [v for v in vals if isinstance(v, unreal.Actor)]
    hit_actor = actors[0].get_name() if actors else None
    return (round(vecs[0].z, 1) if vecs else None), hit_actor


def verge_weight(land, info, x, y):
    for comp in land.get_components_by_class(unreal.LandscapeComponent):
        o = comp.get_world_location()
        if o.x <= x < o.x + COMPONENT_CM and o.y <= y < o.y + COMPONENT_CM:
            return round(comp.editor_get_paint_layer_weight_at_location(unreal.Vector(x, y, 0.0), info), 3)
    return None


def measure_roads():
    world = editor_world()
    land = landscape()
    info = unreal.load_asset(VERGE_INFO)
    if info is None:
        raise RuntimeError("missing " + VERGE_INFO)
    ignore = [a for a in level_actors() if not isinstance(a, unreal.LandscapeProxy)]
    out = {}
    for road in roads():
        spline = road.get_component_by_class(unreal.SplineComponent)
        n = spline.get_number_of_spline_points()
        points = {
            "mid_point_%d" % (n // 2): spline.get_location_at_spline_point(n // 2, unreal.SplineCoordinateSpace.WORLD),
            "half_length": spline.get_location_at_distance_along_spline(spline.get_spline_length() / 2.0,
                                                                        unreal.SplineCoordinateSpace.WORLD),
        }
        entry = {}
        for key, p in points.items():
            z, hit_actor = ground_z(world, land, ignore, p.x, p.y)
            entry[key] = {"xy": [round(p.x), round(p.y)], "spline_z": round(p.z, 1), "ground_z": z,
                          "hit": hit_actor, "verge": verge_weight(land, info, p.x, p.y),
                          "layout_z": round(unreal.OWToolkitSetupLibrary.sample_toolkit_test_height_cm(p.x, p.y), 1)}
        out[road.get_class().get_name()] = entry
    return out


def apply_beds():
    out = {}
    for road in roads():
        bed = road.get_component_by_class(unreal.OWRoadBedComponent)
        if bed is None:
            raise RuntimeError(road.get_name() + " has no OWRoadBedComponent")
        bed.apply_bed_and_verge()
        out[road.get_class().get_name()] = "applied"
    return out


def generate_all():
    out = {}
    for biome, vol in biome_volumes().items():
        comp = vol.get_component_by_class(unreal.PCGComponent)
        comp.generate(True)
        out[biome] = comp.get_graph().get_name() if comp.get_graph() else None
    return out


def count_biomes():
    out = {}
    for biome, vol in biome_volumes().items():
        comp = vol.get_component_by_class(unreal.PCGComponent)
        comps, inst = ism_instances(vol)
        out[biome] = {"ism_components": comps, "instances": inst,
                      "generated": bool(comp.get_editor_property("generated"))}
    return out


def dirty_packages():
    utils = unreal.EditorLoadingAndSavingUtils
    return ([p.get_name() for p in utils.get_dirty_map_packages()],
            [p.get_name() for p in utils.get_dirty_content_packages()])


def save_all():
    maps_before, content_before = dirty_packages()
    ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    maps, content = dirty_packages()
    if not ok:
        raise RuntimeError("save_dirty_packages returned False; still dirty: %s %s" % (maps, content))
    return {"saved": ok, "dirty_maps_before": maps_before, "dirty_content_before": content_before[:40],
            "dirty_content_before_count": len(content_before), "still_dirty_maps": maps,
            "still_dirty_content": content[:20]}


def wait(seconds, ticks):
    end, n = time.time() + seconds, 0
    while time.time() < end or n < ticks:
        n += 1
        yield


def task():
    log("bootstrapped; waiting for " + MAP_NAME)
    while True:
        w = editor_world()
        if w is not None and w.get_name() == MAP_NAME:
            break
        if time.time() - T0 > WORLD_TIMEOUT_S:
            break
        yield
    if w is None or w.get_name() != MAP_NAME:
        def world_timeout():
            raise RuntimeError("the editor world never became %s (it is %s)" % (MAP_NAME, w and w.get_name()))
        run_step("world", world_timeout)
        yield from finish()
        return
    mark("world_loaded")
    yield from wait(SETTLE_S, SETTLE_TICKS)
    run_step("measure_before", measure_roads)
    run_step("apply_bed_and_verge", apply_beds)
    yield from wait(AFTER_APPLY_S, AFTER_APPLY_TICKS)
    run_step("measure_after", measure_roads)
    if run_step("generate", generate_all) is not None:
        start, last, stable, counts = time.time(), None, 0, None
        while time.time() - start < GEN_TIMEOUT_S:
            yield from wait(POLL_S, 1)
            counts = count_biomes()
            snap = {b: c["instances"] for b, c in counts.items()}
            done = all(c["instances"] > 0 and c["generated"] for c in counts.values())
            stable = stable + 1 if (done and snap == last) else 0
            last = snap
            if stable >= STABLE_POLLS:
                break
        final = counts

        def poll_result():
            if stable < STABLE_POLLS:
                raise RuntimeError("generation did not settle in %d s: %s" % (GEN_TIMEOUT_S, final))
            return {"biomes": final, "seconds": round(time.time() - start, 1)}
        run_step("generation_poll", poll_result)
    run_step("save", save_all)
    run_step("measure_final", measure_roads)
    run_step("biomes_final", count_biomes)
    yield from finish()


def finish():
    result["finished"] = True
    mark("finished")
    write_report()
    log("REPORT ok=%s -> %s; quitting the editor" % (result["ok"], REPORT))
    yield
    unreal.SystemLibrary.quit_editor()


_gen = task()
_handle = None
_busy = False


def _on_tick(delta_seconds):
    # A save (or any progress dialog) pumps Slate from inside a step, which fires this callback again while the
    # generator is still running: "generator already executing" (paid 2026-09-27, run 1). Skip re-entrant ticks.
    global _handle, _busy
    if _busy:
        return
    _busy = True
    try:
        next(_gen)
    except StopIteration:
        if _handle is not None:
            unreal.unregister_slate_post_tick_callback(_handle)
            _handle = None
    except Exception as exc:
        result["ok"] = False
        result["steps"]["task"] = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()}
        result["finished"] = True
        write_report()
        unreal.log_error("GT_TICK_TASK crashed: %r" % exc)
        if _handle is not None:
            unreal.unregister_slate_post_tick_callback(_handle)
            _handle = None
        unreal.SystemLibrary.quit_editor()
    finally:
        _busy = False


write_report()
_handle = unreal.register_slate_post_tick_callback(_on_tick)
