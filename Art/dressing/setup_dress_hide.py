"""Leg dressing LD6 (docs/LEG_DRESSING_PLAN.md LD6): dress The Hide (/Game/GrandTour/Legs/L_Leg03), headless.

Run through setup_dress_hide.bat (the manifest 9.0 pattern). Rerunnable: it replaces its own RVT volume, exclusion and
five PCG volumes by label (GTHIDE_*) and touches nothing else of the map beyond what the terrain builder's
RebuildLandscape does (the landscape, the regrounded actors, the builder's stones / posts / ford rocks; no L3 cards
when the spec has biomes). Steps, each with an ok in the report:
  0. spec: with env GT_PUSH_SPEC=1 (the .bat's "pushspec" argument; -Script= drops script arguments) DA_Terrain_Hide is
     rewritten from the C++ default (GTVehicleSetupLibrary.create_terrain_spec_assets(folder, True): GTTerrain::HideSpec,
     which carries the D2 biome palette since LD6; the owner's edits to the asset are lost). Without it the asset is kept
     and must already carry biome rules;
  1. level: load L_Leg03;
  2. rebuild: the map's AGTTerrainBuilder (spec DA_Terrain_Hide) RebuildLandscape - the biome layers painted, the actors
     regrounded, the builder's dressing rebuilt;
  3. rvt: RVT_AM_01_Material on the landscape's RuntimeVirtualTextures, and one RuntimeVirtualTextureVolume over the
     landscape bounds (the ported ClaudeSetupRVTVolumes.py "full" settings: the actor at the bounds' min corner, scale =
     the full size, 25 m of z margin each way, bounds aligned to the landscape);
  4. exclusion: an AGTDressingExclusion (GTHIDE_Exclusion) RebuildFromSpec(DA_Terrain_Hide);
  5. volumes: five PCGVolumes (GTHIDE_PCG_<Biome>) over the landscape bounds, tagged GTBiome.<Forest|Meadow|Scree|Alpine|
     Brush>, graph /Game/GrandTour/Dressing/PCG/PCG_GT_<Biome>, GenerateOnDemand, not partitioned (no generation here: a
     commandlet never ticks); their brushes NoCollision (a WorldStatic object query in the game must not hit them);
  6. save;
  7. gate: one of each, the landscape carrying the RVT.
Report: docs/landscape_migration/ld6_hide_setup.json. Then generate:
  powershell -NoProfile -ExecutionPolicy Bypass -File Art\\dressing\\tick_harness.ps1
    -Task C:\\GrandTour\\Art\\dressing\\tick_generate_only.py -Map /Game/GrandTour/Legs/L_Leg03   (env GT_TICK_MAP=L_Leg03)
"""
import json
import os
import traceback
from pathlib import Path

import unreal

LEVEL = "/Game/GrandTour/Legs/L_Leg03"
LEVEL_NAME = LEVEL.rsplit("/", 1)[-1]
TERRAIN_DIR = "/Game/GrandTour/Terrain"
SPEC_PATH = TERRAIN_DIR + "/DA_Terrain_Hide"
PUSH_SPEC = os.environ.get("GT_PUSH_SPEC", "") == "1"
PCG_DIR = "/Game/GrandTour/Dressing/PCG"
BIOMES = ["Forest", "Meadow", "Scree", "Alpine", "Brush"]
RVT = "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material"
RVT_Z_MARGIN = 2500.0                      # ClaudeSetupRVTVolumes.py
LABEL_PREFIX = "GTHIDE_"
RVT_LABEL = LABEL_PREFIX + "RVT_Material"
EXCLUSION_LABEL = LABEL_PREFIX + "Exclusion"
VOLUME_MARGIN_CM = 200.0
VOLUME_Z_MARGIN_CM = 5000.0
REPORT = Path(r"C:\GrandTour\docs\landscape_migration\ld6_hide_setup.json")
LAST_LINE = "rerun the tick harness after any RebuildLandscape"

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary
gtlib = unreal.GTVehicleSetupLibrary
result = {"ok": True, "level": LEVEL, "push_spec": PUSH_SPEC, "steps": {}}
state = {}


def log(msg):
    unreal.log("SETUP_DRESS_HIDE " + str(msg))


def step(name):
    def decorate(func):
        if not result["ok"]:
            result["steps"][name] = {"ok": False, "error": "skipped: an earlier step failed"}
            return None
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            log("%s ok: %s" % (name, json.dumps(value, default=str)[:600]))
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()}
            unreal.log_error("SETUP_DRESS_HIDE %s FAILED: %r" % (name, exc))
            return None
    return decorate


def all_actors():
    return actors_sub.get_all_level_actors()


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def destroy_labelled(label):
    n = 0
    for a in list(all_actors()):
        if a.get_actor_label() == label:
            actors_sub.destroy_actor(a)
            n += 1
    return n


def spawn(cls, label, loc, rot=None):
    actor = actors_sub.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0.0, 0.0, 0.0))
    if actor is None:
        raise RuntimeError("spawn failed: %s" % label)
    actor.set_actor_label(label)
    return actor


def landscape_actor():
    lands = [a for a in all_actors() if isinstance(a, unreal.LandscapeProxy)]
    if len(lands) != 1:
        raise RuntimeError("%d landscapes in %s (want 1)" % (len(lands), LEVEL))
    return lands[0]


def rules_of(spec):
    return [(str(r.get_editor_property("layer")), round(r.get_editor_property("noise_min"), 2),
             round(r.get_editor_property("noise_max"), 2), r.get_editor_property("max_section_dist_m"))
            for r in spec.get_editor_property("biomes")]


@step("spec")
def spec_step():
    default = gtlib.make_hide_terrain_spec()
    if PUSH_SPEC:
        if gtlib.create_terrain_spec_assets(TERRAIN_DIR, True) < 1:
            raise RuntimeError("create_terrain_spec_assets(%s, True) failed" % TERRAIN_DIR)
    asset = eal.load_asset(SPEC_PATH)
    if asset is None:
        raise RuntimeError("missing " + SPEC_PATH)
    spec = asset.get_editor_property("spec")
    rules = rules_of(spec)
    if not rules:
        raise RuntimeError("DA_Terrain_Hide carries no biome rules: run setup_dress_hide.bat pushspec (or add them)")
    state["spec_asset"] = asset
    return {"pushed": PUSH_SPEC, "rules": rules, "fallback": str(spec.get_editor_property("fallback_biome")),
            "cpp_default_rules": len(default.get_editor_property("biomes")),
            "same_rule_layers_as_cpp": [r[0] for r in rules] == [r[0] for r in rules_of(default)]}


@step("level")
def level_step():
    if not les.load_level(LEVEL):
        raise RuntimeError("could not load " + LEVEL)
    world = editor_world()
    if world is None or world.get_name() != LEVEL_NAME:
        raise RuntimeError("the editor world is %s, not %s" % (world and world.get_name(), LEVEL_NAME))
    return {"world": world.get_name(), "actors": len(all_actors())}


@step("rebuild")
def rebuild_step():
    builders = [a for a in all_actors() if isinstance(a, unreal.GTTerrainBuilder)]
    if len(builders) != 1:
        raise RuntimeError("%d terrain builders in %s (want 1)" % (len(builders), LEVEL))
    builder = builders[0]
    spec_asset = builder.get_editor_property("spec_asset")
    if spec_asset is None or spec_asset.get_path_name().split(".")[0] != SPEC_PATH:
        raise RuntimeError("the builder's spec is %s, not %s" % (spec_asset and spec_asset.get_path_name(), SPEC_PATH))
    # The witness (LD6, paid 2026-09-27: a dressed map's PCG volumes once caught the builder's ground trace and sank every
    # actor 140 m): the gameplay actors' height over the spec's ground before and after; the heights do not change with
    # biome rules, so none may move a metre (the builder measures against whatever static is under an actor and puts it
    # back on the spec's ground: a bog post, Post_Bog_1_1, came back 25 cm higher on every rebuild; put back and logged).
    spec = spec_asset.get_editor_property("spec")
    witness_classes = (unreal.GTLegStart, unreal.GTCheckpoint, unreal.GTExtractionZone, unreal.GTHarvestNode,
                       unreal.GTWinchAnchor, unreal.PlayerStart)

    witnesses = {}

    def heights():
        out_h = {}
        for a in all_actors():
            if isinstance(a, witness_classes):
                loc = a.get_actor_location()
                out_h[a.get_name()] = loc.z - gtlib.sample_terrain_height_cm(spec, loc.x, loc.y)
                witnesses[a.get_name()] = a
        return out_h
    before = heights()
    land = builder.rebuild_landscape()
    if land is None:
        raise RuntimeError("RebuildLandscape failed: %s" % builder.get_editor_property("last_message"))
    after = heights()
    moved = {k: round(after[k] - before[k], 1) for k in before if k in after and abs(after[k] - before[k]) > 1.0}
    sunk = {k: v for k, v in moved.items() if abs(v) > 100.0}
    lowest = min(after.values()) if after else 0.0
    if sunk:
        raise RuntimeError("the rebuild moved gameplay actors over 1 m off their ground: %s; the lowest now %.0f cm over it" % (sunk, lowest))
    # A small move is put back (so a rerun does not ratchet it: the bog post came back +25.3 cm on every rebuild).
    for name in moved:
        a = witnesses[name]
        loc = a.get_actor_location()
        a.set_actor_location(unreal.Vector(loc.x, loc.y, gtlib.sample_terrain_height_cm(spec, loc.x, loc.y) + before[name]), False, False)
    out = {"message": str(builder.get_editor_property("last_message")),
           "witness": "%d gameplay actors, none moved over 1 m against the spec's ground; moved over 1 cm (cm, put back): %s; the lowest %.0f cm over it"
                      % (len(after), moved or "none", lowest),
           "regrounded": builder.get_editor_property("last_regrounded"),
           "rebuilds": builder.get_editor_property("rebuilds"), "landscape": land.get_actor_label()}
    dressing = builder.get_editor_property("dressing")
    if dressing is not None:
        for prop in ("stone_count", "post_count", "ford_rock_count", "foliage_count"):
            try:
                out[prop] = dressing.get_editor_property(prop)
            except Exception as exc:
                out[prop] = "unreadable: %r" % exc
    layers = set()
    for comp in land.get_components_by_class(unreal.LandscapeComponent):
        try:
            for alloc in comp.get_editor_property("weightmap_layer_allocations"):
                info = alloc.get_editor_property("layer_info")
                if info:
                    layers.add(str(info.get_editor_property("layer_name")))
        except Exception:
            break
    out["weight_layers"] = sorted(layers)
    return out


@step("rvt")
def rvt_step():
    land = landscape_actor()
    rvt = unreal.load_asset(RVT)
    if rvt is None:
        raise RuntimeError("missing " + RVT)
    land.set_editor_property("runtime_virtual_textures", [rvt])
    land_rvts = [t.get_path_name().split(".")[0] for t in land.get_editor_property("runtime_virtual_textures") if t]
    if RVT not in land_rvts:
        raise RuntimeError("the landscape's RuntimeVirtualTextures read back as %s" % land_rvts)
    removed = destroy_labelled(RVT_LABEL)
    origin, extent = land.get_actor_bounds(False)
    min_corner = unreal.Vector(origin.x - extent.x, origin.y - extent.y, origin.z - extent.z - RVT_Z_MARGIN)
    scale = unreal.Vector(extent.x * 2.0, extent.y * 2.0, extent.z * 2.0 + RVT_Z_MARGIN * 2.0)
    vol = spawn(unreal.RuntimeVirtualTextureVolume, RVT_LABEL, min_corner)
    comp = vol.get_component_by_class(unreal.RuntimeVirtualTextureComponent)
    comp.set_editor_property("virtual_texture", rvt)
    comp.set_editor_property("bounds_align_actor", land)
    vol.set_actor_scale3d(scale)
    vol.modify()
    got = comp.get_editor_property("virtual_texture")
    if got is None or got.get_path_name().split(".")[0] != RVT:
        raise RuntimeError("RVT volume texture read-back: %s" % got)
    return {"replaced": removed, "landscape_rvts": land_rvts,
            "landscape_origin": [round(origin.x), round(origin.y), round(origin.z)],
            "landscape_extent": [round(extent.x), round(extent.y), round(extent.z)],
            "min_corner": [round(min_corner.x), round(min_corner.y), round(min_corner.z)],
            "size": [round(scale.x), round(scale.y), round(scale.z)]}


@step("exclusion")
def exclusion_step():
    removed = destroy_labelled(EXCLUSION_LABEL)
    excl = spawn(unreal.GTDressingExclusion, EXCLUSION_LABEL, unreal.Vector(0.0, 0.0, 0.0))
    boxes = excl.rebuild_from_spec(state["spec_asset"])
    tags = [str(t) for t in excl.get_editor_property("tags")]
    if boxes <= 0:
        raise RuntimeError("the exclusion built no boxes: %s" % excl.get_editor_property("last_message"))
    if "OWDressing.Exclude" not in tags:
        raise RuntimeError("the exclusion is not tagged OWDressing.Exclude: %s" % tags)
    return {"replaced": removed, "boxes": boxes, "message": str(excl.get_editor_property("last_message")),
            "route": excl.get_editor_property("route_box_count"), "alt": excl.get_editor_property("alt_box_count"),
            "sections": excl.get_editor_property("section_box_count"), "patches": excl.get_editor_property("patch_box_count"),
            "gameplay": excl.get_editor_property("gameplay_box_count"), "tags": tags}


@step("volumes")
def volumes_step():
    land = landscape_actor()
    origin, extent = land.get_actor_bounds(False)
    size = (extent.x * 2.0 + VOLUME_MARGIN_CM, extent.y * 2.0 + VOLUME_MARGIN_CM, extent.z * 2.0 + VOLUME_Z_MARGIN_CM * 2.0)
    center = unreal.Vector(origin.x, origin.y, origin.z)
    out = []
    for biome in BIOMES:
        label = LABEL_PREFIX + "PCG_" + biome
        removed = destroy_labelled(label)
        graph = unreal.load_asset("%s/PCG_GT_%s" % (PCG_DIR, biome))
        if graph is None:
            raise RuntimeError("graph missing: PCG_GT_" + biome + " (run create_biome_pcg.bat GT)")
        vol = spawn(unreal.PCGVolume, label, center)
        vol.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        _, unit = vol.get_actor_bounds(False)
        if unit.x < 1.0 or unit.y < 1.0 or unit.z < 1.0:
            raise RuntimeError("%s spawned with no brush (extent %s)" % (label, unit))
        vol.set_actor_scale3d(unreal.Vector(size[0] / (2.0 * unit.x), size[1] / (2.0 * unit.y), size[2] / (2.0 * unit.z)))
        vol.set_actor_location(center, False, False)
        vol.set_editor_property("tags", [unreal.Name("GTBiome." + biome)])
        comp = vol.get_component_by_class(unreal.PCGComponent)
        if comp is None:
            raise RuntimeError(label + " has no PCGComponent")
        comp.set_graph(graph)
        comp.set_editor_property("generation_trigger", unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
        comp.set_editor_property("is_component_partitioned", False)
        # LD7 (paid 2026-09-27): the brush answers WorldStatic object queries in the game - the water field's bed trace,
        # the leg volumes' marker trace and the tests' ground traces all landed on the volume's top face, 140 m up. PCG
        # samples the volume through its own sceneless body in the editor, so the brush needs no collision.
        brush = vol.get_component_by_class(unreal.BrushComponent)
        if brush is None:
            raise RuntimeError(label + " has no BrushComponent")
        brush.set_collision_profile_name("NoCollision")
        brush.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        vol.modify()
        o, e = vol.get_actor_bounds(False)
        out.append({"label": label, "replaced": removed, "tag": "GTBiome." + biome, "graph": comp.get_graph().get_name(),
                    "center": [round(o.x), round(o.y), round(o.z)], "size": [round(e.x * 2), round(e.y * 2), round(e.z * 2)],
                    "partitioned": comp.get_editor_property("is_component_partitioned"),
                    "brush_collision": [str(brush.get_collision_profile_name()), str(brush.get_collision_enabled())],
                    "trigger": str(comp.get_editor_property("generation_trigger"))})
    return out


@step("save")
def save_step():
    if not les.save_current_level():
        raise RuntimeError("save_current_level failed")
    return "saved"


@step("gate")
def gate_step():
    actors = all_actors()
    tagged = {b: len([a for a in actors if isinstance(a, unreal.PCGVolume)
                      and unreal.Name("GTBiome." + b) in a.get_editor_property("tags")]) for b in BIOMES}
    land = landscape_actor()
    excl = [a for a in actors if isinstance(a, unreal.GTDressingExclusion)]
    rvts = [a for a in actors if isinstance(a, unreal.RuntimeVirtualTextureVolume)]
    land_rvts = [t.get_path_name().split(".")[0] for t in land.get_editor_property("runtime_virtual_textures") if t]
    problems = []
    if any(v != 1 for v in tagged.values()):
        problems.append("tagged volumes %s" % tagged)
    if len(excl) != 1:
        problems.append("exclusions %d" % len(excl))
    if len(rvts) != 1:
        problems.append("rvt volumes %d" % len(rvts))
    if RVT not in land_rvts:
        problems.append("the landscape lacks the RVT")
    if problems:
        raise RuntimeError("gate: " + "; ".join(problems))
    return {"tagged_volumes": tagged, "exclusions": len(excl), "rvt_volumes": len(rvts), "landscape_rvts": land_rvts,
            "actors_total": len(actors)}


REPORT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
log("REPORT ok=%s -> %s" % (result["ok"], REPORT))
log(LAST_LINE)
