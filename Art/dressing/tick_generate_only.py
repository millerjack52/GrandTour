"""Leg dressing LD4 step 6 task: generate every GTBiome.* PCG volume of the open map, wait, save, report.

Run by tick_harness.ps1 only (its bootstrap Content/Python/init_unreal.py execs this file inside the full editor when
env GT_TOOLKIT_HARNESS names it); PCG generation does nothing in a commandlet, hence the real editor:
  powershell -NoProfile -ExecutionPolicy Bypass -File Art\dressing\tick_harness.ps1
    -Task C:\GrandTour\Art\dressing\tick_generate_only.py -Map /Game/GrandTour/Test/L_GTDressScratch
Driven from a slate post-tick callback, one step at a time:
  1. waits for the editor world (env GT_TICK_MAP, default L_GTDressScratch; LD6: L_Leg03), then >= 6 s and >= 30 ticks;
  2. LD7: cleanup(True) on every PCGVolume tagged GTBiome.* and waits for 0 instances (a map generated before reads
     "generated" at once otherwise); then generate(True) on each;
  3. polls every 0.5 s until every volume is generated and owns instances and the counts hold for 4 polls, or 10 min;
     the generation time is from the generate calls to the first poll that already had the final counts;
  4. reads every ISM on the volumes: its class from its GTVeg.* component tag (Solid, Soft.Brush, Soft.Sapling,
     Soft.Young; no tag = None), mesh, instances and collision profile, and checks each ISM carries at most one GTVeg
     tag and the profile its class wants (Solid: BlockAll, unless docs/landscape_migration/ld4_gt_graphs.json lists
     the mesh as having no simple collision; every other class: NoCollision); LD5: counts each class's component
     classes and fails a soft class (Soft.*) on anything but a plain InstancedStaticMeshComponent;
  5. the tree scale histogram: every tree-mesh instance (the painterly tree variants except stumps and bushes, and
     the pack oaks) by size class - Sapling / Young from their tags, Mature = Solid - standing only (a lying deadfall
     log is Solid with the same meshes: an instance whose up axis is below 60 deg from vertical is left out); bins of
     0.1 on the instance's Z scale, min / max of X and Z, and the span of Z scale x the variant's baked Z prescale;
  6. saves the dirty MAP packages only (content is listed, never saved);
  7. writes tick_generate_only_report.json next to this file and docs/landscape_migration/ld4_scratch_generation.json
     (L_Leg03: ld6_hide_generation.json; env GT_TICK_DOCS_REPORT overrides)
     (per-step ok, "finished": true) and calls quit_editor().
The report is rewritten after every step, so a killed run still leaves its progress.
"""
import json
import math
import os
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

import unreal

MAP_NAME = os.environ.get("GT_TICK_MAP", "L_GTDressScratch")
TAG_PREFIX = "GTBiome."
WORLD_TIMEOUT_S = 20 * 60.0      # the harness kills the editor at 25 min
SETTLE_S, SETTLE_TICKS = 6.0, 30
GEN_TIMEOUT_S = 600.0
POLL_S = 0.5
# LD7 cut step 1 A/B only (env GT_TICK_SOFT_HISM=1, graphs built with -GTSoftHISM): soft classes on HISM are not flagged.
SOFT_HISM_AB = os.environ.get("GT_TICK_SOFT_HISM", "") == "1"
STABLE_POLLS = 4
REPORT = Path(__file__).with_name("tick_generate_only_report.json")
# LD6: The Hide's run writes its own docs report (env GT_TICK_DOCS_REPORT overrides either).
DOCS_REPORT = Path(os.environ.get("GT_TICK_DOCS_REPORT") or (r"C:\GrandTour\docs\landscape_migration\ld6_hide_generation.json"
                   if MAP_NAME == "L_Leg03" else r"C:\GrandTour\docs\landscape_migration\ld4_scratch_generation.json"))
GT_GRAPHS_REPORT = Path(r"C:\GrandTour\docs\landscape_migration\ld4_gt_graphs.json")
CLASS_TAGS = {"GTVeg.Solid": "Solid", "GTVeg.Soft.Brush": "Soft.Brush", "GTVeg.Soft.Sapling": "Soft.Sapling",
              "GTVeg.Soft.Young": "Soft.Young"}
CLASSES = ["Solid", "Soft.Brush", "Soft.Sapling", "Soft.Young", "None"]
WANT_PROFILE = {"Solid": "BlockAll", "Soft.Brush": "NoCollision", "Soft.Sapling": "NoCollision",
                "Soft.Young": "NoCollision", "None": "NoCollision"}
SIZE_OF_CLASS = {"Soft.Sapling": "Sapling", "Soft.Young": "Young", "Solid": "Mature"}
# OWCreateTreeVariantsCommandlet's baked Z scale per variant family (FVariantSpec.Scale.Z); pack oaks 1.
PRESCALE_Z = [("SM_OWFir_BareGiant", 2.45), ("SM_OWFir_AncientSparse", 2.20), ("SM_OWFir_BareTall", 1.95),
              ("SM_OWFir_TallSparse", 1.80), ("SM_OWFir_Dead", 1.40), ("SM_OWBirch_Sparse", 1.20),
              ("SM_OWBeech", 1.0), ("SM_OWBirch", 1.0), ("SM_OWFirTree", 1.0), ("SM_OakTree_", 1.0)]

T0 = time.time()
result = {"ok": True, "finished": False, "map": MAP_NAME, "timeline_s": {}, "steps": {}}


def log(msg):
    unreal.log("GT_TICK_GEN " + str(msg))


def write_report():
    text = json.dumps(result, indent=2, default=str)
    for path in (REPORT, DOCS_REPORT):
        try:
            path.write_text(text, encoding="utf-8")
        except Exception as exc:
            unreal.log_error("GT_TICK_GEN report write failed (%s): %r" % (path, exc))


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
        unreal.log_error("GT_TICK_GEN %s FAILED: %r" % (name, exc))
        value = None
    mark(name)
    write_report()
    return value


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def level_actors():
    return unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()


def volumes():
    out = {}
    for a in level_actors():
        if not isinstance(a, unreal.PCGVolume):
            continue
        for t in a.get_editor_property("tags"):
            if str(t).startswith(TAG_PREFIX):
                out[str(t)[len(TAG_PREFIX):]] = a
    if not out:
        raise RuntimeError("no PCGVolume tagged %s*" % TAG_PREFIX)
    return dict(sorted(out.items()))


def isms(actor):
    return list(actor.get_components_by_class(unreal.InstancedStaticMeshComponent))


def counts():
    out = {}
    for biome, vol in volumes().items():
        comp = vol.get_component_by_class(unreal.PCGComponent)
        comps = isms(vol)
        out[biome] = {"ism_components": len(comps), "instances": sum(c.get_instance_count() for c in comps),
                      "generated": bool(comp.get_editor_property("generated"))}
    return out


def generate_all():
    out = {}
    for biome, vol in volumes().items():
        comp = vol.get_component_by_class(unreal.PCGComponent)
        comp.generate(True)
        out[biome] = comp.get_graph().get_name() if comp.get_graph() else None
    return out


def no_simple_collision():
    try:
        data = json.loads(GT_GRAPHS_REPORT.read_text(encoding="utf-8"))
        return {p.rsplit("/", 1)[-1].split(".")[0] for p in data.get("solid_without_simple_collision", [])}
    except Exception:
        return set()


def is_tree_mesh(name):
    if name.startswith("SM_OakTree_"):
        return True
    return (name.startswith("SM_OWBeech") or name.startswith("SM_OWBirch") or name.startswith("SM_OWFir")) \
        and "Stump" not in name and "Bush" not in name


def prescale_z(name):
    for prefix, z in PRESCALE_Z:
        if name.startswith(prefix):
            return z
    return 1.0


def analyse():
    exempt = no_simple_collision()
    per_graph = {}
    profile_problems, tag_problems, class_problems = [], [], []
    scales = defaultdict(list)          # size class -> [(x, z, z * prescale)]
    lying = 0
    for biome, vol in volumes().items():
        graph = {c: {"instances": 0, "isms": 0} for c in CLASSES}
        meshes = defaultdict(Counter)
        for comp in isms(vol):
            n = comp.get_instance_count()
            tags = [str(t) for t in comp.get_editor_property("component_tags")]
            veg = [t for t in tags if t.startswith("GTVeg.")]
            if len(veg) > 1:
                tag_problems.append("%s/%s: %s" % (biome, comp.get_name(), veg))
            cls = CLASS_TAGS.get(veg[0], "Unknown:" + veg[0]) if veg else "None"
            mesh = comp.get_editor_property("static_mesh")
            mesh_name = mesh.get_name() if mesh else "None"
            profile = str(comp.get_collision_profile_name())
            want = WANT_PROFILE.get(cls, "?")
            if cls == "Solid" and mesh_name in exempt:
                want = "NoCollision"
            if profile != want:
                profile_problems.append("%s/%s %s %s: profile %s, want %s" % (biome, comp.get_name(), mesh_name, cls,
                                                                              profile, want))
            g = graph.setdefault(cls, {"instances": 0, "isms": 0})
            g["instances"] += n
            g["isms"] += 1
            comp_class = comp.get_class().get_name()
            g.setdefault("component_classes", Counter())[comp_class] += 1
            if cls.startswith("Soft.") and comp_class != "InstancedStaticMeshComponent" and not SOFT_HISM_AB:
                class_problems.append("%s/%s %s %s: %s, want a plain InstancedStaticMeshComponent (LD5)" % (
                    biome, comp.get_name(), mesh_name, cls, comp_class))
            meshes[cls][mesh_name] += n
            size = SIZE_OF_CLASS.get(cls)
            if size and is_tree_mesh(mesh_name):
                pz = prescale_z(mesh_name)
                for i in range(n):
                    t = comp.get_instance_transform(i, True)
                    if isinstance(t, tuple):     # (found, transform) on some Python bindings
                        t = next(v for v in t if isinstance(v, unreal.Transform))
                    up = unreal.MathLibrary.get_up_vector(t.rotation.rotator())
                    if up.z < 0.5:
                        lying += 1
                        continue
                    s = t.scale3d
                    scales[size].append((s.x, s.z, s.z * pz))
        per_graph[biome] = {"graph": vol.get_component_by_class(unreal.PCGComponent).get_graph().get_name(),
                            "classes": {c: v for c, v in graph.items() if v["instances"] or v["isms"]},
                            "meshes": {c: dict(m) for c, m in meshes.items()}}
    totals = Counter()
    for g in per_graph.values():
        for c, v in g["classes"].items():
            totals[c] += v["instances"]
    histogram = {}
    for size in ("Sapling", "Young", "Mature"):
        vals = scales.get(size, [])
        if not vals:
            histogram[size] = {"instances": 0}
            continue
        bins = Counter("%.1f" % (math.floor(z * 10.0 + 1e-6) / 10.0) for _, z, _ in vals)
        histogram[size] = {"instances": len(vals),
                           "z_scale_bins_0.1": dict(sorted(bins.items(), key=lambda kv: float(kv[0]))),
                           "x_min": round(min(v[0] for v in vals), 3), "x_max": round(max(v[0] for v in vals), 3),
                           "z_min": round(min(v[1] for v in vals), 3), "z_max": round(max(v[1] for v in vals), 3),
                           "z_times_prescale_min": round(min(v[2] for v in vals), 3),
                           "z_times_prescale_max": round(max(v[2] for v in vals), 3)}
    everything = [v for vals in scales.values() for v in vals]
    span = {}
    if everything:
        span = {"instance_z_scale": [round(min(v[1] for v in everything), 3), round(max(v[1] for v in everything), 3)],
                "z_times_prescale": [round(min(v[2] for v in everything), 3), round(max(v[2] for v in everything), 3)]}
    out = {"per_graph": per_graph, "totals_by_class": dict(totals), "tree_scale_histogram": histogram,
           "tree_scale_span": span, "lying_tree_instances_left_out": lying,
           "collision_check": {"problems": profile_problems, "exempt_no_simple_collision": sorted(exempt)},
           "tag_check": {"problems": tag_problems}, "component_class_check": {"problems": class_problems}}
    if profile_problems or tag_problems or class_problems:
        raise RuntimeError("collision/tag/class check: %d profile, %d tag, %d component class problem(s): %s" % (
            len(profile_problems), len(tag_problems), len(class_problems),
            (profile_problems + tag_problems + class_problems)[:6]))
    return out


def dirty_packages():
    utils = unreal.EditorLoadingAndSavingUtils
    return ([p.get_name() for p in utils.get_dirty_map_packages()],
            [p.get_name() for p in utils.get_dirty_content_packages()])


def save_maps():
    maps_before, content_before = dirty_packages()
    ok = unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False)
    maps, content = dirty_packages()
    if not ok or maps:
        raise RuntimeError("map save failed; still dirty: %s" % maps)
    return {"saved_maps": maps_before, "dirty_content_not_saved": content_before[:40],
            "dirty_content_count": len(content_before)}


def wait(seconds, ticks):
    end, n = time.time() + seconds, 0
    while time.time() < end or n < ticks:
        n += 1
        yield


def task():
    log("bootstrapped; waiting for " + MAP_NAME)
    w = None
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
    run_step("before", counts)
    # LD7 (paid 2026-09-27): on a map generated before, every volume already reads "generated" with instances, so the
    # settle poll below passed at once and the save caught the old output mid-regeneration (Scree 1006 -> 2012). Clean
    # every volume first and wait until each reads 0 instances and not generated.
    def cleanup_all():
        out = {}
        for biome, vol in volumes().items():
            comp = vol.get_component_by_class(unreal.PCGComponent)
            comp.cleanup(True)
            out[biome] = "cleanup(True)"
        return out
    if run_step("cleanup", cleanup_all) is not None:
        start_clean, cleaned = time.time(), None
        while time.time() - start_clean < 120.0:
            yield from wait(POLL_S, 1)
            cleaned = counts()
            if all(c["instances"] == 0 and not c["generated"] for c in cleaned.values()):
                break
        final_clean = cleaned

        def clean_result():
            if not all(c["instances"] == 0 and not c["generated"] for c in final_clean.values()):
                raise RuntimeError("cleanup left instances or a generated flag: %s" % final_clean)
            return {"volumes": final_clean, "seconds": round(time.time() - start_clean, 1)}
        run_step("cleaned", clean_result)
    start = time.time()
    if run_step("generate", generate_all) is not None:
        polls, last, stable, snap_counts = [], None, 0, None
        while time.time() - start < GEN_TIMEOUT_S:
            yield from wait(POLL_S, 1)
            snap_counts = counts()
            snap = {b: c["instances"] for b, c in snap_counts.items()}
            polls.append((round(time.time() - start, 2), snap))
            done = all(c["instances"] > 0 and c["generated"] for c in snap_counts.values())
            stable = stable + 1 if (done and snap == last) else 0
            last = snap
            if stable >= STABLE_POLLS:
                break
        final = snap_counts

        def poll_result():
            if stable < STABLE_POLLS:
                raise RuntimeError("generation did not settle in %d s: %s" % (GEN_TIMEOUT_S, final))
            final_snap = polls[-1][1]
            first = next(t for t, s in polls if s == final_snap)
            return {"volumes": final, "generation_seconds": first, "poll_s": POLL_S,
                    "settled_at_s": polls[-1][0], "polls": len(polls)}
        run_step("generation", poll_result)
    run_step("analysis", analyse)
    run_step("save", save_maps)
    run_step("after_save", counts)
    yield from finish()


def finish():
    result["finished"] = True
    mark("finished")
    write_report()
    log("REPORT ok=%s -> %s" % (result["ok"], REPORT))
    yield
    unreal.SystemLibrary.quit_editor()


_gen = task()
_handle = None
_busy = False


def _on_tick(delta_seconds):
    # A save (or any progress dialog) pumps Slate from inside a step, which fires this callback again while the
    # generator is still running (paid 2026-09-27 in tick_apply_and_generate.py): skip re-entrant ticks.
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
        unreal.log_error("GT_TICK_GEN crashed: %r" % exc)
        if _handle is not None:
            unreal.unregister_slate_post_tick_callback(_handle)
            _handle = None
        unreal.SystemLibrary.quit_editor()
    finally:
        _busy = False


write_report()
_handle = unreal.register_slate_post_tick_callback(_on_tick)
