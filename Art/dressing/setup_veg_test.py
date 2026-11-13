"""Leg dressing LD5 (docs/LEG_DRESSING_PLAN.md): build the vegetation physics test map /Game/GrandTour/Test/L_VegTest.

Headless, through setup_veg_test.bat (the manifest 9.0 pattern). Refuses if the map exists unless env GT_VEG_OVERWRITE=1
(the .bat's "overwrite" argument: -Script= drops script arguments), which opens the map, destroys every actor and
rebuilds. It places:
  - a sun, sky light, sky atmosphere and height fog (the gpu frame-time case draws something real);
  - a flat floor: the engine cube scaled to 200 x 160 x 1 m, its top at z = 0, x -30..170 m, y -30..130 m;
  - a PlayerStart at (9, -15) m facing +x (where Art/veg_test.bat's runner parks the car between cases);
  - one actor VEG_TestDressing tagged GTBiome.Test (so gt.Look.Dressing switches it) owning plain ISMs of the real
    meshes with the real LD4 component tags (UGTVegetationSubsystem.add_tagged_instances), every lane along +x from
    x = 0 (a 60 m clear run-up) with lanes 30-40 m apart:
      brush   y 0 m:   LD5 v2: a 30 x 20 m patch (x 60..90, y -10..10) at the thicket-core composition (PCG_GT_Brush's
                       densest streams) - bushes at 0.08/m2 (SM_OWBush_* and SM_BirchBush_0x_Summer, scale 0.7-1.4) plus
                       cover plants at 0.10/m2 (SM_CoverPlant_0x_Summer, scale 0.75-1.2), uniform random places and yaw
                       (seeded) - GTVeg.Soft.Brush, NoCollision;
      saplings y 40 m: the 8 small-tree variants at scale 0.35 in a row ACROSS the lane at x 60 m, 2 m apart and centred
                       on the car's path (y 33..47 m; LD5 v2 result), GTVeg.Soft.Sapling, NoCollision;
      young   y 70 m:  4 variants at scale 0.65, 4 m apart from x 60 m, GTVeg.Soft.Young, NoCollision;
      mature  y 100 m: SM_OWBirch at scale 1.0, x 60 m, GTVeg.Solid, BlockAll (its trunk capsule is the mesh's own);
  - saves and writes docs/landscape_migration/ld5_veg_test_setup.json with a per-step ok and a gate.
"""
import json
import os
import random
import traceback
from pathlib import Path

import unreal

LEVEL = "/Game/GrandTour/Test/L_VegTest"
LEVEL_NAME = LEVEL.rsplit("/", 1)[-1]
OVERWRITE = os.environ.get("GT_VEG_OVERWRITE", "") == "1"
REPORT = Path(r"C:\GrandTour\docs\landscape_migration\ld5_veg_test_setup.json")
TREES = "/Game/OWGame/Dev/DressingLab/Trees"
PACK_TREES = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/Trees/Trees_Summer"
CUBE = "/Engine/BasicShapes/Cube"
TAG_ACTOR = "GTBiome.Test"
M = 100.0   # cm per m

# LD7 cut step 1: the pack bushes and cover plants are the Nanite passthrough copies the GT graphs use
# (/Game/GrandTour/Dressing/Nanite/SM_GTN_<vendor name>, OWCreateTreeVariants -GTNanitePack); the vendor originals are
# PACK_TREES/SM_BirchBush_0x_Summer and PACK_COVER/SM_CoverPlant_0x_Summer.
NANITE = "/Game/GrandTour/Dressing/Nanite"
BUSHES = ["%s/SM_OWBush_%s" % (TREES, n) for n in ("Beech_A", "Beech_B", "Birch_A", "Birch_B")] + \
         ["%s/SM_GTN_SM_BirchBush_%02d_Summer" % (NANITE, i) for i in range(1, 6)]
PACK_COVER = "/Game/ANGRY_MESH/StylizedPack_MeadowEnvironment/Meshes/CoverPlants/CoverPlants_Summer"
COVER = ["%s/SM_GTN_SM_CoverPlant_%02d_Summer" % (NANITE, i) for i in range(1, 5)]
SMALL_TREES = ["SM_OWBeech", "SM_OWBirch", "SM_OWFirTree", "SM_OWFir_TallSparse_A", "SM_OWFir_TallSparse_B",
               "SM_OWFir_BareTall_A", "SM_OWFir_BareTall_B", "SM_OWFir_BareTall_C"]
YOUNG_TREES = SMALL_TREES[:4]
MATURE_TREE = "SM_OWBirch"
LANES = {"brush_y": 0.0, "sapling_y": 40.0, "young_y": 70.0, "mature_y": 100.0, "start_x": 60.0}
PATCH = {"x": (60.0, 90.0), "y": (-10.0, 10.0), "seed": 5,
         "streams": [(BUSHES, 0.08, (0.7, 1.4)), (COVER, 0.10, (0.75, 1.2))]}   # (meshes, per m2, scale)
SAPLING = {"scale": 0.35, "spacing": 2.0}
YOUNG = {"scale": 0.65, "spacing": 4.0}
FLOOR = {"x": (-30.0, 170.0), "y": (-30.0, 130.0)}
PLAYER_START = (9.0, -15.0)

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary
veg = unreal.GTVegetationSubsystem
result = {"ok": True, "level": LEVEL, "overwrite": OVERWRITE, "steps": {}}
state = {}


def log(msg):
    unreal.log("SETUP_VEG_TEST " + str(msg))


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
            unreal.log_error("SETUP_VEG_TEST %s FAILED: %r" % (name, exc))
            return None
    return decorate


def spawn(cls, label, loc, rot=None):
    actor = actors_sub.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0.0, 0.0, 0.0))
    if actor is None:
        raise RuntimeError("spawn failed: %s" % label)
    actor.set_actor_label(label)
    return actor


def editor_world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def mesh(path):
    asset = unreal.load_asset(path)
    if asset is None or not isinstance(asset, unreal.StaticMesh):
        raise RuntimeError("missing static mesh " + path)
    return asset


def xf(x_m, y_m, yaw=0.0, scale=1.0):
    return unreal.Transform(unreal.Vector(x_m * M, y_m * M, 0.0), unreal.Rotator(0.0, 0.0, yaw),
                            unreal.Vector(scale, scale, scale))


@step("level")
def make_level():
    exists = eal.does_asset_exist(LEVEL)
    if exists and not OVERWRITE:
        raise RuntimeError(LEVEL + " exists; rerun with the 'overwrite' argument (env GT_VEG_OVERWRITE=1)")
    removed = 0
    if exists:
        # delete_asset + new_level fails headless (the .umap stays): open and empty (setup_gt_dress_scratch.py).
        if not les.load_level(LEVEL):
            raise RuntimeError("could not load the existing " + LEVEL)
        for a in list(actors_sub.get_all_level_actors()):
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


@step("floor")
def floor():
    cx = (FLOOR["x"][0] + FLOOR["x"][1]) * 0.5
    cy = (FLOOR["y"][0] + FLOOR["y"][1]) * 0.5
    sx = FLOOR["x"][1] - FLOOR["x"][0]
    sy = FLOOR["y"][1] - FLOOR["y"][0]
    actor = spawn(unreal.StaticMeshActor, "VEG_Floor", unreal.Vector(cx * M, cy * M, -50.0))
    comp = actor.static_mesh_component
    comp.set_static_mesh(mesh(CUBE))
    actor.set_actor_scale3d(unreal.Vector(sx, sy, 1.0))
    comp.set_collision_profile_name("BlockAll")
    origin, extent = actor.get_actor_bounds(False)
    top = origin.z + extent.z
    if abs(top) > 1.0:
        raise RuntimeError("the floor's top is at %.1f cm, not 0" % top)
    return {"centre_m": [cx, cy], "size_m": [sx, sy], "top_cm": round(top, 2)}


@step("player_start")
def player_start():
    spawn(unreal.PlayerStart, "VEG_PlayerStart", unreal.Vector(PLAYER_START[0] * M, PLAYER_START[1] * M, 120.0))
    return {"at_m": PLAYER_START}


@step("dressing")
def dressing():
    actor = spawn(unreal.Actor, "VEG_TestDressing", unreal.Vector(0.0, 0.0, 0.0))
    actor.set_editor_property("tags", [unreal.Name(TAG_ACTOR)])
    rng = random.Random(PATCH["seed"])
    out = {"components": []}

    def add(mesh_path, transforms, tag, profile, shadow):
        comp = veg.add_tagged_instances(actor, mesh(mesh_path), transforms, tag, profile, shadow)
        if comp is None:
            raise RuntimeError("add_tagged_instances returned None for " + mesh_path)
        if comp.get_instance_count() != len(transforms):
            raise RuntimeError("%s: %d instances, asked %d" % (mesh_path, comp.get_instance_count(), len(transforms)))
        out["components"].append({"mesh": mesh_path.rsplit("/", 1)[-1], "tag": tag, "profile": profile,
                                  "instances": len(transforms), "class": comp.get_class().get_name()})

    # brush: the thicket-core composition over the 30 x 20 m patch, uniform random places (the PCG sampler's density)
    x0, x1 = PATCH["x"]
    y0, y1 = PATCH["y"]
    area = (x1 - x0) * (y1 - y0)
    per_mesh = {}
    out["brush_streams"] = []
    for meshes, density, (lo, hi) in PATCH["streams"]:
        count = int(round(density * area))
        out["brush_streams"].append({"meshes": len(meshes), "per_m2": density, "count": count, "scale": [lo, hi]})
        for _ in range(count):
            per_mesh.setdefault(rng.choice(meshes), []).append(
                xf(rng.uniform(x0, x1), rng.uniform(y0, y1), rng.uniform(0.0, 360.0), rng.uniform(lo, hi)))
    for path, transforms in per_mesh.items():
        add(path, transforms, "GTVeg.Soft.Brush", "NoCollision", False)
    # saplings: the 8 small-tree variants in a row across the lane, centred on the car's path
    for i, name in enumerate(SMALL_TREES):
        across = (i - (len(SMALL_TREES) - 1) * 0.5) * SAPLING["spacing"]
        add("%s/%s" % (TREES, name), [xf(LANES["start_x"], LANES["sapling_y"] + across, 0.0, SAPLING["scale"])],
            "GTVeg.Soft.Sapling", "NoCollision", True)
    # young trees: 4 variants, 4 m apart
    for i, name in enumerate(YOUNG_TREES):
        add("%s/%s" % (TREES, name), [xf(LANES["start_x"] + i * YOUNG["spacing"], LANES["young_y"], 0.0, YOUNG["scale"])],
            "GTVeg.Soft.Young", "NoCollision", True)
    # the mature tree: solid, blocking, its trunk capsule from the mesh
    add("%s/%s" % (TREES, MATURE_TREE), [xf(LANES["start_x"], LANES["mature_y"], 0.0, 1.0)], "GTVeg.Solid", "BlockAll", True)
    out["brush_instances"] = sum(len(t) for t in per_mesh.values())
    out["tags"] = [str(t) for t in actor.get_editor_property("tags")]
    state["actor"] = actor
    return out


@step("save")
def save():
    if not les.save_current_level():
        raise RuntimeError("save_current_level failed")
    return "saved"


@step("gate")
def gate():
    actor = state["actor"]
    isms = actor.get_components_by_class(unreal.InstancedStaticMeshComponent)
    by_tag = {}
    hism = 0
    for comp in isms:
        tags = [str(t) for t in comp.get_editor_property("component_tags")]
        for t in tags:
            by_tag[t] = by_tag.get(t, 0) + comp.get_instance_count()
        hism += 1 if isinstance(comp, unreal.HierarchicalInstancedStaticMeshComponent) else 0
    problems = []
    want_brush = sum(int(round(d * (PATCH["x"][1] - PATCH["x"][0]) * (PATCH["y"][1] - PATCH["y"][0]))) for _, d, _ in PATCH["streams"])
    if by_tag.get("GTVeg.Soft.Brush", 0) != want_brush:
        problems.append("brush instances %d" % by_tag.get("GTVeg.Soft.Brush", 0))
    if by_tag.get("GTVeg.Soft.Sapling", 0) != len(SMALL_TREES):
        problems.append("saplings %d" % by_tag.get("GTVeg.Soft.Sapling", 0))
    if by_tag.get("GTVeg.Soft.Young", 0) != len(YOUNG_TREES):
        problems.append("young %d" % by_tag.get("GTVeg.Soft.Young", 0))
    if by_tag.get("GTVeg.Solid", 0) != 1:
        problems.append("solid %d" % by_tag.get("GTVeg.Solid", 0))
    if hism:
        problems.append("%d HISM component(s); every one must be a plain ISM" % hism)
    if TAG_ACTOR not in [str(t) for t in actor.get_editor_property("tags")]:
        problems.append("the actor is not tagged " + TAG_ACTOR)
    if problems:
        raise RuntimeError("gate: " + "; ".join(problems))
    return {"instances_by_tag": by_tag, "ism_components": len(isms), "hism_components": hism,
            "actors_total": len(actors_sub.get_all_level_actors())}


REPORT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
log("REPORT ok=%s -> %s" % (result["ok"], REPORT))
