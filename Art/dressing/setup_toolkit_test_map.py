"""Stage C step 2 (docs/LandscapeMigrationManifest.md 9.C.2): build the toolkit test map L_OWToolkitTest.

Headless, through setup_toolkit_test_map.bat (manifest 9.0 pattern). It:
  - creates /Game/GrandTour/Test/L_OWToolkitTest (not partitioned). It refuses if the map exists, unless env
    GT_TOOLKIT_OVERWRITE=1 (the .bat's "overwrite" argument: -Script= drops script arguments), which opens the map,
    destroys every actor and rebuilds;
  - adds a sun (atmosphere sun), SkyAtmosphere, a real-time-capture SkyLight and ExponentialHeightFog;
  - calls OWToolkitSetupLibrary.build_toolkit_test_landscape (layout 9.C.1) with MI_OWDressingLab_Style, the 13
    WorldCanvas layer infos and RVT_AM_01_Material;
  - places one RVT volume over the landscape bounds (the ported ClaudeSetupRVTVolumes.py "full" settings);
  - places 6 PCGVolumes over the whole landscape, graph PCG_OW<Biome>, tag OWBiome.<Biome>, generate on demand,
    NOT partitioned (the smoke test counts ISM instances on the volumes themselves). No generation here: a
    commandlet never ticks, the tick harness generates;
  - places BP_OWRoad, BP_OWRoad_Dusty, BP_OWRoad_Gravel and BP_OWCliffWall, default spline points cleared, the
    new points in world XY with Z from sample_toolkit_test_height_cm, marked "Override Construction Script";
  - places a PlayerStart at (8400, 8400, ground + 300) facing +Y. The world settings keep NO game mode override
    (GTRunGameMode, the global default, dispatches -GTDressingTest);
  - saves, and writes setup_toolkit_test_map_report.json next to this file with a per-step ok and a gate.
"""
import json
import math
import os
import traceback
from pathlib import Path

import unreal

LEVEL = "/Game/GrandTour/Test/L_OWToolkitTest"
LEVEL_NAME = LEVEL.rsplit("/", 1)[-1]
OVERWRITE = os.environ.get("GT_TOOLKIT_OVERWRITE", "") == "1"
LAYER_DIR = "/Game/OWGame/Dev/L_OWWorldCanvas_sharedassets"
LAYERS = ["OW_Meadow", "OW_MeadowLush", "OW_MeadowDry", "OW_Bare", "OW_Alpine", "OW_Snow", "OW_Forest",
          "OW_ForestBeech", "OW_ForestBirch", "OW_ForestFir", "OW_ForestOak", "OW_Scree", "OW_RoadVerge"]
VERGE = "OW_RoadVerge"
MATERIAL = "/Game/OWGame/Dev/DressingLab/MI_OWDressingLab_Style"
RVT = "/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material"
RVT_LABEL = "OWTEST_RVT_Material"
RVT_Z_MARGIN = 2500.0                      # ClaudeSetupRVTVolumes.py
PCG_DIR = "/Game/OWGame/Dev/DressingLab"
BIOMES = ["Forest", "Meadow", "Scree", "Road", "Cliff", "Alpine"]
VOLUME_CENTER = (25200.0, 25200.0, 3000.0)
VOLUME_SIZE = (50400.0, 50400.0, 10000.0)
ROAD_DIR = "/Game/OWGame/Dev/DressingLab/Roads"
ROADS = [
    ("BP_OWRoad", [(3000, 2000), (6000, 12000), (9000, 22000), (7000, 31000)]),
    ("BP_OWRoad_Dusty", [(22000, 2000), (26000, 12000), (24000, 22000), (27000, 31000)]),
    ("BP_OWRoad_Gravel", [(39000, 2000), (43000, 12000), (41000, 22000), (44000, 31000)]),
]
CLIFF_BP = "/Game/OWGame/Dev/DressingLab/Cliffs/BP_OWCliffWall"
SCREE_HILL = (25200.0, 42000.0)
CLIFF_R = 5200.0
CLIFF_ANGLES_DEG = [200.0, 235.0, 270.0, 305.0, 340.0]
PLAYER_START_XY = (8400.0, 8400.0)
REPORT = Path(__file__).with_name("setup_toolkit_test_map_report.json")

les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
eal = unreal.EditorAssetLibrary
lib = unreal.OWToolkitSetupLibrary
result = {"ok": True, "level": LEVEL, "overwrite": OVERWRITE, "steps": {}}
state = {}


def log(msg):
    unreal.log("SETUP_TOOLKIT_TEST_MAP " + str(msg))


def step(name):
    def decorate(func):
        if not result["ok"]:
            result["steps"][name] = {"ok": False, "error": "skipped: an earlier step failed"}
            return None
        try:
            value = func()
            result["steps"][name] = {"ok": True, "value": value}
            log("%s ok: %s" % (name, json.dumps(value, default=str)[:400]))
            return value
        except Exception as exc:
            result["ok"] = False
            result["steps"][name] = {"ok": False, "error": repr(exc), "traceback": traceback.format_exc()}
            unreal.log_error("SETUP_TOOLKIT_TEST_MAP %s FAILED: %r" % (name, exc))
            return None
    return decorate


def height(x, y):
    return float(lib.sample_toolkit_test_height_cm(float(x), float(y)))


def spawn(cls, label, loc, rot=None):
    actor = actors_sub.spawn_actor_from_class(cls, loc, rot or unreal.Rotator(0.0, 0.0, 0.0))
    if actor is None:
        raise RuntimeError("spawn failed: %s" % label)
    actor.set_actor_label(label)
    return actor


def all_actors():
    return actors_sub.get_all_level_actors()


def landscape_actor():
    found = [a for a in all_actors() if isinstance(a, unreal.LandscapeProxy)]
    if len(found) != 1:
        raise RuntimeError("expected 1 landscape, found %d" % len(found))
    return found[0]


def place_spline_actor(bp_path, label, xy_points):
    cls = eal.load_blueprint_class(bp_path)
    if cls is None:
        raise RuntimeError("blueprint class failed to load: " + bp_path)
    pts = [unreal.Vector(float(x), float(y), height(x, y)) for x, y in xy_points]
    actor = spawn(cls, label, pts[0])
    spline = actor.get_component_by_class(unreal.SplineComponent)
    if spline is None:
        raise RuntimeError(label + " has no SplineComponent")
    default_points = spline.get_number_of_spline_points()
    spline.clear_spline_points(True)
    for p in pts:
        spline.add_spline_point(p, unreal.SplineCoordinateSpace.WORLD, True)
    # Keep these points when the construction script reruns (the component's instance data). No change notify: a
    # notify reruns the construction script at once, which replaces the component (the old handle reads 0 points).
    spline.set_editor_property("spline_has_been_edited", True, unreal.PropertyAccessChangeNotifyMode.NEVER)
    spline.update_spline()
    spline = actor.get_component_by_class(unreal.SplineComponent)
    got = [spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD)
           for i in range(spline.get_number_of_spline_points())]
    if len(got) != len(pts):
        raise RuntimeError("%s: %d spline points after the rebuild, want %d" % (label, len(got), len(pts)))
    for a, b in zip(got, pts):
        if abs(a.x - b.x) > 1.0 or abs(a.y - b.y) > 1.0 or abs(a.z - b.z) > 1.0:
            raise RuntimeError("%s: spline point read-back %s != %s" % (label, a, b))
    actor.modify()
    return actor, {"label": label, "class": actor.get_class().get_name(), "default_points_cleared": default_points,
                   "override_construction_script": spline.get_editor_property("spline_has_been_edited"),
                   "points": [[round(p.x), round(p.y), round(p.z, 1)] for p in pts],
                   "length_cm": round(spline.get_spline_length())}


@step("level")
def make_level():
    exists = eal.does_asset_exist(LEVEL)
    if exists and not OVERWRITE:
        raise RuntimeError(LEVEL + " exists; rerun with the 'overwrite' argument (env GT_TOOLKIT_OVERWRITE=1)")
    removed = 0
    if exists:
        # Overwrite = open the map and destroy every actor. delete_asset + new_level fails headless: the .umap stays
        # on disk and new_level refuses the path ("An asset already exists at this location"), paid 2026-09-27.
        if not les.load_level(LEVEL):
            raise RuntimeError("could not load the existing " + LEVEL)
        for a in list(all_actors()):
            if isinstance(a, (unreal.WorldSettings, unreal.Brush)) and not isinstance(a, unreal.Volume):
                continue
            actors_sub.destroy_actor(a)
            removed += 1
    elif not les.new_level(LEVEL, False):
        raise RuntimeError("new_level failed for " + LEVEL)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if world is None or world.get_name() != LEVEL_NAME:
        raise RuntimeError("the editor world is %s, not %s" % (world and world.get_name(), LEVEL_NAME))
    left = [a.get_class().get_name() for a in all_actors()]
    return {"replaced_existing": exists, "actors_removed": removed, "world": world.get_name(),
            "actors_at_start": left}


@step("lighting")
def lighting():
    sun = spawn(unreal.DirectionalLight, "Sun", unreal.Vector(25200.0, 25200.0, 20000.0),
                unreal.Rotator(0.0, -50.0, 40.0))   # Rotator(roll, pitch, yaw)
    sun_comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    sun_comp.set_editor_property("atmosphere_sun_light", True)
    sun_comp.set_intensity(8.0)
    sky = spawn(unreal.SkyLight, "SkyLight", unreal.Vector(25200.0, 25200.0, 20000.0))
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    spawn(unreal.SkyAtmosphere, "SkyAtmosphere", unreal.Vector(0.0, 0.0, 0.0))
    spawn(unreal.ExponentialHeightFog, "HeightFog", unreal.Vector(25200.0, 25200.0, 0.0))
    return {"sun_atmosphere": sun_comp.get_editor_property("atmosphere_sun_light"),
            "sky_real_time_capture": sky.get_component_by_class(unreal.SkyLightComponent)
            .get_editor_property("real_time_capture")}


@step("landscape")
def landscape():
    material = unreal.load_asset(MATERIAL)
    rvt = unreal.load_asset(RVT)
    if material is None or rvt is None:
        raise RuntimeError("material %s / rvt %s failed to load" % (material, rvt))
    infos = []
    for name in LAYERS:
        info = unreal.load_asset("%s/%s_LayerInfo" % (LAYER_DIR, name))
        if info is None:
            raise RuntimeError("layer info missing: %s_LayerInfo" % name)
        infos.append(info)
    report_json = lib.build_toolkit_test_landscape(material, infos, rvt)
    if not report_json:
        raise RuntimeError("build_toolkit_test_landscape returned None (see LogOWToolkitSetup in the log)")
    report = json.loads(report_json)
    if not report.get("ok"):
        raise RuntimeError("build report not ok: " + report_json)
    painted = report.get("painted", {})
    unpainted = [n for n in LAYERS if n != VERGE and painted.get(n, 0) <= 0]
    if unpainted:
        raise RuntimeError("layers with no painted vertices: %s" % unpainted)
    state["build_report"] = report
    return report


@step("rvt_volume")
def rvt_volume():
    land = landscape_actor()
    rvt = unreal.load_asset(RVT)
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
    land_rvts = [t.get_path_name().split(".")[0] for t in land.get_editor_property("runtime_virtual_textures") if t]
    if RVT not in land_rvts:
        raise RuntimeError("the landscape's RuntimeVirtualTextures lacks the RVT: %s" % land_rvts)
    return {"landscape_origin": [round(origin.x), round(origin.y), round(origin.z)],
            "landscape_extent": [round(extent.x), round(extent.y), round(extent.z)],
            "min_corner": [round(min_corner.x), round(min_corner.y), round(min_corner.z)],
            "size": [round(scale.x), round(scale.y), round(scale.z)], "landscape_rvts": land_rvts}


@step("biome_volumes")
def biome_volumes():
    center = unreal.Vector(*VOLUME_CENTER)
    out = []
    for biome in BIOMES:
        label = "OWTEST_PCG_" + biome
        vol = spawn(unreal.PCGVolume, label, center)
        vol.set_actor_scale3d(unreal.Vector(1.0, 1.0, 1.0))
        _, unit_extent = vol.get_actor_bounds(False)
        if unit_extent.x < 1.0 or unit_extent.y < 1.0 or unit_extent.z < 1.0:
            raise RuntimeError("%s spawned with no brush (extent %s)" % (label, unit_extent))
        vol.set_actor_scale3d(unreal.Vector(VOLUME_SIZE[0] / (2.0 * unit_extent.x),
                                            VOLUME_SIZE[1] / (2.0 * unit_extent.y),
                                            VOLUME_SIZE[2] / (2.0 * unit_extent.z)))
        vol.set_actor_location(center, False, False)
        vol.set_editor_property("tags", [unreal.Name("OWBiome." + biome)])
        comp = vol.get_component_by_class(unreal.PCGComponent)
        if comp is None:
            raise RuntimeError(label + " has no PCGComponent")
        graph = unreal.load_asset("%s/PCG_OW%s" % (PCG_DIR, biome))
        if graph is None:
            raise RuntimeError("graph missing: PCG_OW" + biome)
        comp.set_graph(graph)
        comp.set_editor_property("generation_trigger", unreal.PCGComponentGenerationTrigger.GENERATE_ON_DEMAND)
        comp.set_editor_property("is_component_partitioned", False)
        vol.modify()
        origin, extent = vol.get_actor_bounds(False)
        if (abs(extent.x * 2.0 - VOLUME_SIZE[0]) > 10.0 or abs(extent.y * 2.0 - VOLUME_SIZE[1]) > 10.0
                or abs(extent.z * 2.0 - VOLUME_SIZE[2]) > 10.0):
            raise RuntimeError("%s bounds %s x2 != %s" % (label, extent, VOLUME_SIZE))
        out.append({"label": label, "tag": "OWBiome." + biome, "graph": comp.get_graph().get_name(),
                    "unit_brush_extent": round(unit_extent.x, 1),
                    "center": [round(origin.x), round(origin.y), round(origin.z)],
                    "size": [round(extent.x * 2), round(extent.y * 2), round(extent.z * 2)],
                    "partitioned": comp.get_editor_property("is_component_partitioned"),
                    "trigger": str(comp.get_editor_property("generation_trigger"))})
    return out


@step("roads")
def roads():
    out = []
    for name, pts in ROADS:
        actor, info = place_spline_actor("%s/%s" % (ROAD_DIR, name), "OWTEST_" + name, pts)
        bed = actor.get_component_by_class(unreal.OWRoadBedComponent)
        if bed is None:
            raise RuntimeError(name + " has no OWRoadBedComponent")
        info["road_bed"] = bed.get_class().get_path_name()
        out.append(info)
    return out


@step("cliff")
def cliff():
    cx, cy = SCREE_HILL
    pts = [(cx + CLIFF_R * math.cos(math.radians(a)), cy + CLIFF_R * math.sin(math.radians(a)))
           for a in CLIFF_ANGLES_DEG]
    _, info = place_spline_actor(CLIFF_BP, "OWTEST_BP_OWCliffWall", pts)
    return info


@step("player_start")
def player_start():
    x, y = PLAYER_START_XY
    z = height(x, y) + 300.0
    spawn(unreal.PlayerStart, "PlayerStart", unreal.Vector(x, y, z), unreal.Rotator(0.0, 0.0, 90.0))
    return [x, y, round(z, 1)]


@step("game_mode")
def game_mode():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    override = world.get_world_settings().get_editor_property("default_game_mode")
    if override is not None:
        raise RuntimeError("the level overrides the game mode (%s); it must not" % override.get_name())
    return "no override (GTRunGameMode, the global default)"


@step("save")
def save():
    if not les.save_current_level():
        raise RuntimeError("save_current_level failed")
    return "saved"


@step("gate")
def gate():
    actors = all_actors()
    road_classes = sorted(a.get_class().get_name() for a in actors
                          if a.get_class().get_name().startswith("BP_OWRoad"))
    cliffs = [a for a in actors if a.get_class().get_name() == "BP_OWCliffWall_C"]
    tagged = {}
    for biome in BIOMES:
        tag = unreal.Name("OWBiome." + biome)
        tagged[biome] = len([a for a in actors if isinstance(a, unreal.PCGVolume)
                              and tag in a.get_editor_property("tags")])
    rvt_volumes = [a for a in actors if isinstance(a, unreal.RuntimeVirtualTextureVolume)]
    land = landscape_actor()
    land_rvts = [t.get_path_name().split(".")[0] for t in land.get_editor_property("runtime_virtual_textures") if t]
    painted = state["build_report"]["painted"]
    counts = {"roads": len(road_classes), "road_classes": road_classes, "cliff_walls": len(cliffs),
              "tagged_volumes": tagged, "rvt_volumes": len(rvt_volumes), "landscape_rvt_set": RVT in land_rvts,
              "painted_non_verge_min": min(painted[n] for n in LAYERS if n != VERGE),
              "painted_verge": painted.get(VERGE, 0), "actors_total": len(actors)}
    problems = []
    if counts["roads"] != 3:
        problems.append("roads %d" % counts["roads"])
    if counts["cliff_walls"] != 1:
        problems.append("cliff walls %d" % counts["cliff_walls"])
    if any(v != 1 for v in tagged.values()):
        problems.append("tagged volumes %s" % tagged)
    if counts["rvt_volumes"] != 1:
        problems.append("rvt volumes %d" % counts["rvt_volumes"])
    if not counts["landscape_rvt_set"]:
        problems.append("landscape RVT not set")
    if counts["painted_non_verge_min"] <= 0:
        problems.append("a non-verge layer is unpainted")
    if problems:
        raise RuntimeError("gate: " + "; ".join(problems))
    return counts


REPORT.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
log("REPORT ok=%s -> %s" % (result["ok"], REPORT))
