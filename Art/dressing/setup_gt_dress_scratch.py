"""Leg dressing LD4 step 6 (docs/LEG_DRESSING_PLAN.md, LD4 "Tests"): build the scratch map L_GTDressScratch.

Headless, through setup_gt_dress_scratch.bat (the manifest 9.0 pattern); the ticking pass generates it afterwards
(tick_harness.ps1 -Task tick_generate_only.py -Map /Game/GrandTour/Test/L_GTDressScratch). Never touches
L_OWToolkitTest. It:
  - creates /Game/GrandTour/Test/L_GTDressScratch (not partitioned); refuses if it exists unless env
    GT_DRESS_OVERWRITE=1 (the .bat's "overwrite" argument: -Script= drops script arguments), which opens the map,
    destroys every actor and rebuilds;
  - writes /Game/GrandTour/Test/DA_Terrain_GTDressScratch: the Proving spec (UGTVehicleSetupLibrary
    .make_proving_terrain_spec) plus a TEST palette holding every GT graph's layers - one 90 m noise (seed 31) cut into
    bands, so each layer gets ground on the Proving's gentle relief (it has no 32 deg slopes or 75 m heights):
      OW_Scree 0-0.10, OW_Alpine 0.10-0.22, Thicket 0.22-0.38, OW_ForestFir 0.38-0.52, OW_Forest 0.52-0.74,
      OW_MeadowLush 0.74-0.87, fallback OW_Meadow;
  - adds a sun, sky light, sky atmosphere and height fog (so the ticking editor's window shows something);
  - imports the ground with UGTVehicleSetupLibrary.build_leg_landscape (M_GT_Landscape, LI_<layer> in
    /Game/GrandTour/Terrain/Layers, the off-road PhysMaterial on the biome layers);
  - adds an AGTDressingExclusion rebuilt from that spec asset (tag OWDressing.Exclude);
  - adds five PCGVolumes over the landscape, tagged GTBiome.<Forest|Meadow|Scree|Alpine|Brush>, graph
    /Game/GrandTour/Dressing/PCG/PCG_GT_<X>, GenerateOnDemand, not partitioned. No generation here (a commandlet never
    ticks);
  - saves, and writes docs/landscape_migration/ld4_scratch_setup.json with a per-step ok and a gate.
"""
import json
import os
import traceback
from pathlib import Path

import unreal

LEVEL = "/Game/GrandTour/Test/L_GTDressScratch"
LEVEL_NAME = LEVEL.rsplit("/", 1)[-1]
SPEC_DIR = "/Game/GrandTour/Test"
SPEC_NAME = "DA_Terrain_GTDressScratch"
OVERWRITE = os.environ.get("GT_DRESS_OVERWRITE", "") == "1"
MATERIAL = "/Game/GrandTour/Materials/M_GT_Landscape"
LAYER_FOLDER = "/Game/GrandTour/Terrain/Layers"
SURFACE_FOLDER = "/Game/GrandTour/Terrain/Surfaces"
PCG_DIR = "/Game/GrandTour/Dressing/PCG"
BIOMES = ["Forest", "Meadow", "Scree", "Alpine", "Brush"]
# The test palette: (layer, noise min, noise max) on one noise, in priority order; the rest goes to the fallback.
NOISE_WAVELENGTH_M, NOISE_SEED, NOISE_FADE = 90.0, 31, 0.03
PALETTE = [("OW_Scree", 0.0, 0.10), ("OW_Alpine", 0.10, 0.22), ("Thicket", 0.22, 0.38),
           ("OW_ForestFir", 0.38, 0.52), ("OW_Forest", 0.52, 0.74), ("OW_MeadowLush", 0.74, 0.87)]
FALLBACK = "OW_Meadow"
EXPECTED_LAYERS = ["OW_Scree", "OW_Alpine", "Thicket", "OW_ForestFir", "OW_Forest", "OW_MeadowLush", "OW_Meadow"]
VOLUME_MARGIN_CM = 200.0
VOLUME_Z = (0.0, 10000.0)                  # centre, height (cm): the Proving relief is a few metres
REPORT = Path(r"C:\GrandTour\docs\landscape_migration\ld4_scratch_setup.json")

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary
gtlib = unreal.GTVehicleSetupLibrary
result = {"ok": True, "level": LEVEL, "overwrite": OVERWRITE, "steps": {}}
state = {}


def log(msg):
    unreal.log("SETUP_GT_DRESS_SCRATCH " + str(msg))


def step(name):
    def decorate(func):
        if not result["ok"]:
            result["steps"][name] = {"ok": False, "error": "skipped: an earlier step failed"}
            return None
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            log("%s ok: %s" % (name, json.dumps(value, default=str)[:500]))
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()}
            unreal.log_error("SETUP_GT_DRESS_SCRATCH %s FAILED: %r" % (name, exc))
            return None
    return decorate


def spawn(cls, label, loc, rot=None):
    actor = actors_sub.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0.0, 0.0, 0.0))
    if actor is None:
        raise RuntimeError("spawn failed: %s" % label)
    actor.set_actor_label(label)
    return actor


def all_actors():
    return actors_sub.get_all_level_actors()


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


@step("level")
def make_level():
    exists = eal.does_asset_exist(LEVEL)
    if exists and not OVERWRITE:
        raise RuntimeError(LEVEL + " exists; rerun with the 'overwrite' argument (env GT_DRESS_OVERWRITE=1)")
    removed = 0
    if exists:
        # delete_asset + new_level fails headless (the .umap stays; paid 2026-09-27 on L_OWToolkitTest): open and empty.
        if not les.load_level(LEVEL):
            raise RuntimeError("could not load the existing " + LEVEL)
        for a in list(all_actors()):
            if isinstance(a, (unreal.WorldSettings, unreal.Brush)) and not isinstance(a, unreal.Volume):
                continue
            actors_sub.destroy_actor(a)
            removed += 1
    elif not les.new_level(LEVEL, False):
        raise RuntimeError("new_level failed for " + LEVEL)
    world = editor_world()
    if world is None or world.get_name() != LEVEL_NAME:
        raise RuntimeError("the editor world is %s, not %s" % (world and world.get_name(), LEVEL_NAME))
    return {"replaced_existing": exists, "actors_removed": removed, "world": world.get_name()}


@step("spec")
def spec_asset():
    spec = gtlib.make_proving_terrain_spec()
    rules = []
    for layer, lo, hi in PALETTE:
        r = unreal.GTBiomeRule()
        r.set_editor_property("layer", layer)
        r.set_editor_property("noise_wavelength_m", NOISE_WAVELENGTH_M)
        r.set_editor_property("seed", NOISE_SEED)
        r.set_editor_property("noise_min", lo)
        r.set_editor_property("noise_max", hi)
        r.set_editor_property("noise_fade", NOISE_FADE)
        rules.append(r)
    spec.set_editor_property("biomes", rules)
    spec.set_editor_property("fallback_biome", FALLBACK)
    path = "%s/%s" % (SPEC_DIR, SPEC_NAME)
    asset = unreal.load_asset(path) if eal.does_asset_exist(path) else None
    created = asset is None
    if created:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", unreal.GTTerrainSpecAsset)
        asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(SPEC_NAME, SPEC_DIR, unreal.GTTerrainSpecAsset,
                                                                        factory)
        if asset is None:
            raise RuntimeError("could not create " + path)
    asset.set_editor_property("display_name", "GT dress scratch (Proving + test palette)")
    asset.set_editor_property("spec", spec)
    if not eal.save_loaded_asset(asset, False):
        raise RuntimeError("could not save " + path)
    state["spec_asset"] = asset
    state["spec"] = asset.get_editor_property("spec")
    got = state["spec"].get_editor_property("biomes")
    return {"asset": path, "created": created, "rules": [(str(r.get_editor_property("layer")),
                                                          round(r.get_editor_property("noise_min"), 2),
                                                          round(r.get_editor_property("noise_max"), 2)) for r in got],
            "fallback": str(state["spec"].get_editor_property("fallback_biome")),
            "components_per_side": state["spec"].get_editor_property("components_per_side")}


@step("lighting")
def lighting():
    sun = spawn(unreal.DirectionalLight, "Sun", unreal.Vector(0.0, 0.0, 20000.0), unreal.Rotator(0.0, -50.0, 40.0))
    sun_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_comp.set_editor_property("atmosphere_sun_light", True)
    sun_comp.set_intensity(8.0)
    sky = spawn(unreal.SkyLight, "SkyLight", unreal.Vector(0.0, 0.0, 20000.0))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    spawn(unreal.SkyAtmosphere, "SkyAtmosphere", unreal.Vector(0.0, 0.0, 0.0))
    spawn(unreal.ExponentialHeightFog, "HeightFog", unreal.Vector(0.0, 0.0, 0.0))
    return "sun, sky light, sky atmosphere, height fog"


@step("landscape")
def landscape():
    material = unreal.load_asset(MATERIAL)
    if material is None:
        raise RuntimeError("missing " + MATERIAL)
    land = gtlib.build_leg_landscape(editor_world(), state["spec"], material, LAYER_FOLDER, SURFACE_FOLDER,
                                     "GTDRESS_Landscape")
    if land is None:
        raise RuntimeError("build_leg_landscape returned None (see the log)")
    state["landscape"] = land
    origin, extent = land.get_actor_bounds(False)
    state["land_bounds"] = (origin, extent)
    infos = [str(i.get_editor_property("layer_name")) for i in
             (unreal.load_asset("%s/LI_%s" % (LAYER_FOLDER, n)) for n in EXPECTED_LAYERS) if i]
    missing = [n for n in EXPECTED_LAYERS if n not in infos]
    if missing:
        raise RuntimeError("layer infos missing for %s" % missing)
    return {"label": land.get_actor_label(), "bounds_origin": [round(origin.x), round(origin.y), round(origin.z)],
            "bounds_size": [round(extent.x * 2), round(extent.y * 2), round(extent.z * 2)], "layer_infos": infos}


@step("exclusion")
def exclusion():
    excl = spawn(unreal.GTDressingExclusion, "GTDRESS_Exclusion", unreal.Vector(0.0, 0.0, 0.0))
    boxes = excl.rebuild_from_spec(state["spec_asset"])
    tags = [str(t) for t in excl.get_editor_property("tags")]
    if boxes <= 0:
        raise RuntimeError("the exclusion built no boxes")
    if "OWDressing.Exclude" not in tags:
        raise RuntimeError("the exclusion is not tagged OWDressing.Exclude: %s" % tags)
    comps = excl.get_components_by_class(unreal.BoxComponent)
    return {"boxes": boxes, "box_components": len(comps), "tags": tags}


@step("volumes")
def volumes():
    origin, extent = state["land_bounds"]
    size = (extent.x * 2.0 + VOLUME_MARGIN_CM, extent.y * 2.0 + VOLUME_MARGIN_CM, VOLUME_Z[1])
    center = unreal.Vector(origin.x, origin.y, VOLUME_Z[0])
    out = []
    for biome in BIOMES:
        label = "GTDRESS_PCG_" + biome
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
        graph = unreal.load_asset("%s/PCG_GT_%s" % (PCG_DIR, biome))
        if graph is None:
            raise RuntimeError("graph missing: PCG_GT_" + biome + " (run create_biome_pcg.bat GT)")
        comp.set_graph(graph)
        comp.set_editor_property("generation_trigger", unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
        comp.set_editor_property("is_component_partitioned", False)
        vol.modify()
        o, e = vol.get_actor_bounds(False)
        out.append({"label": label, "tag": "GTBiome." + biome, "graph": comp.get_graph().get_name(),
                    "center": [round(o.x), round(o.y), round(o.z)], "size": [round(e.x * 2), round(e.y * 2), round(e.z * 2)],
                    "partitioned": comp.get_editor_property("is_component_partitioned"),
                    "trigger": str(comp.get_editor_property("generation_trigger"))})
    return out


@step("save")
def save():
    if not les.save_current_level():
        raise RuntimeError("save_current_level failed")
    return "saved"


@step("gate")
def gate():
    actors = all_actors()
    tagged = {b: len([a for a in actors if isinstance(a, unreal.PCGVolume)
                      and unreal.Name("GTBiome." + b) in a.get_editor_property("tags")]) for b in BIOMES}
    lands = [a for a in actors if isinstance(a, unreal.LandscapeProxy)]
    excl = [a for a in actors if isinstance(a, unreal.GTDressingExclusion)]
    problems = []
    if any(v != 1 for v in tagged.values()):
        problems.append("tagged volumes %s" % tagged)
    if len(lands) != 1:
        problems.append("landscapes %d" % len(lands))
    if len(excl) != 1:
        problems.append("exclusions %d" % len(excl))
    if problems:
        raise RuntimeError("gate: " + "; ".join(problems))
    return {"tagged_volumes": tagged, "landscapes": len(lands), "exclusions": len(excl), "actors_total": len(actors)}


REPORT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
log("REPORT ok=%s -> %s" % (result["ok"], REPORT))
