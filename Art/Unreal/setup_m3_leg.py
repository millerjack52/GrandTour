"""setup_m3_leg.py - loot tables, the first leg definition and the greybox leg map, headless.

Run with Art\\setup_m3_leg.bat (close the editor first; run setup_m1_track and setup_m3_weather
before it). Creates:
- /Game/GrandTour/Harvest/DA_Loot_CableBundle, DA_Loot_Wreck, DA_Loot_RadiationCache from the
  C++ defaults (UGTLootTable::DefaultTables);
- /Game/GrandTour/Legs/DA_Leg_01: par 300 s, limit 600 s, starts overcast, cold rising over the
  second half, dust through the dirt section, heat on the last stretch, four rival times;
- /Game/GrandTour/Legs/L_Leg01, a 1.2 km greybox leg along +X on a 1.5 km tarmac floor: a
  shelter roof at 250 m (dry under cover), a dirt section 300-600 m, a mud crossing at 700 m
  with a steel post beside it, checkpoints at 400 m and 800 m, the extraction zone at 1200 m, a
  radiation pocket 80 m off the road at 600 m with two alloy caches inside, cable bundles and
  wrecks along the way (all paying from their loot tables), and a weather front that starts
  300 m behind the start and sweeps the leg at 4 m/s. The car spawns at the start; the
  AGTLegStart there names DA_Leg_01.
Safe to re-run: the props are rebuilt from the table below; the floor and lighting are kept.
"""
import unreal

LEVEL_PATH = "/Game/GrandTour/Legs/L_Leg01"
LEG_FOLDER = "/Game/GrandTour/Legs"
HARVEST_FOLDER = "/Game/GrandTour/Harvest"
WEATHER_FOLDER = "/Game/GrandTour/Weather"
SURF_PATH = "/Game/GrandTour/Terrain/Surfaces"
MAT_PATH = "/Game/GrandTour/Materials"
PROP_PREFIXES = ("Lane_", "Marker_", "Roof_", "Post_", "Node_", "Wreck_", "Zone_", "Front_", "Checkpoint_", "Extraction_", "LegStart_")

lib = unreal.GTVehicleSetupLibrary
eal = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cube = unreal.load_asset("/Engine/BasicShapes/Cube")


def log(msg):
    unreal.log("SETUP_M3_LEG " + msg)


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    # unreal.Rotator's positional order is (roll, pitch, yaw); always use keywords.
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def load_or_none(path):
    return eal.load_asset(path) if eal.does_asset_exist(path) else None


def box(world, label, x, y, z, sx, sy, sz, surface=None, material=None):
    transform = unreal.Transform(unreal.Vector(x, y, z), rot(), unreal.Vector(sx, sy, sz))
    actor = lib.spawn_static_mesh_actor(world, cube, transform, label)
    if actor is None:
        raise SystemExit("could not spawn " + label)
    comp = actor.get_editor_property("static_mesh_component")
    if surface is not None:
        comp.set_phys_material_override(surface)
    if material is not None:
        comp.set_material(0, material)
    return actor


def spawn(world, cls, label, x, y, z, yaw=0.0):
    actor = lib.spawn_actor_of_class(world, cls, unreal.Transform(unreal.Vector(x, y, z), rot(yaw=yaw), unreal.Vector(1, 1, 1)), label)
    if actor is None:
        raise SystemExit("could not spawn " + label)
    return actor


# ---- data assets ------------------------------------------------------------------------------
saved_loot = lib.create_loot_table_assets(HARVEST_FOLDER)
log("loot tables saved: %d (expected 3)" % saved_loot)
saved_leg = lib.create_leg_assets(LEG_FOLDER, WEATHER_FOLDER)
log("leg assets saved: %d (expected 5: the tour's legs; setup_m5_legs.py builds the maps of 2 to 5)" % saved_leg)
if saved_loot < 3 or saved_leg < 5:
    raise SystemExit("asset writing fell short")
leg = eal.load_asset(LEG_FOLDER + "/DA_Leg_01")
log("DA_Leg_01: par %.0f limit %.0f weather %s conditions %d rivals %d" % (
    leg.get_editor_property("par_time_seconds"), leg.get_editor_property("time_limit_seconds"),
    leg.get_editor_property("start_weather"), len(leg.get_editor_property("conditions")), len(leg.get_editor_property("rival_times_seconds"))))


# ---- level ------------------------------------------------------------------------------------
def build_props(world):
    surf = {name: load_or_none(SURF_PATH + "/PM_" + name) for name in ("Tarmac", "Dirt", "Mud")}
    mi = {name: load_or_none(MAT_PATH + "/MI_Env_" + name) for name in ("Tarmac", "Dirt", "Mud", "Marker", "Greybox")}
    if surf["Dirt"] is None or surf["Mud"] is None:
        unreal.log_warning("SETUP_M3_LEG surface materials missing (run setup_m1_track.bat first); lanes will be plain")

    # Route surfaces: dirt 300-600 m, mud crossing 700-740 m, 30 m wide, 1 cm proud of the floor.
    box(world, "Lane_Dirt", 45000, 0, -9, 300, 30, 0.2, surface=surf["Dirt"], material=mi["Dirt"])
    box(world, "Lane_Mud", 72000, 0, -9, 40, 30, 0.2, surface=surf["Mud"], material=mi["Mud"])
    for side in (-1, 1):
        box(world, "Marker_Mud_%d" % side, 70000, side * 1600, 40, 0.4, 0.4, 0.8, material=mi["Marker"])
        box(world, "Marker_Dirt_%d" % side, 30000, side * 1600, 40, 0.4, 0.4, 0.8, material=mi["Marker"])

    # Shelter roof at 250 m: a 12 x 12 m slab 5 m up on two posts, straddling the road.
    box(world, "Roof_A", 25000, 0, 500, 12, 12, 0.2, material=mi["Greybox"])
    for side in (-1, 1):
        box(world, "Roof_A_Post_%d" % side, 25000, side * 550, 250, 0.4, 0.4, 5, material=mi["Greybox"])

    # Checkpoints and the extraction zone.
    for index, x in ((1, 40000), (2, 80000)):
        checkpoint = spawn(world, unreal.GTCheckpoint, "Checkpoint_%d" % index, x, 0, 250)
        checkpoint.set_editor_property("index", index)
        checkpoint.set_editor_property("extent", unreal.Vector(150, 1500, 500))
    extraction = spawn(world, unreal.GTExtractionZone, "Extraction_A", 120000, 0, 250)
    extraction.set_editor_property("extent", unreal.Vector(1000, 1000, 500))

    # The leg start names the leg.
    start = spawn(world, unreal.GTLegStart, "LegStart_A", 0, 0, 0)
    start.set_editor_property("leg_asset_path", LEG_FOLDER + "/DA_Leg_01")

    # Radiation pocket 80 m off the road at 600 m with two alloy caches.
    zone = spawn(world, unreal.GTRadiationZone, "Zone_Radiation_A", 60000, 8000, 600)
    zone.set_editor_property("extent", unreal.Vector(2500, 2500, 600))
    for index, (x, y) in enumerate(((60000, 8000), (61500, 6800))):
        cache = spawn(world, unreal.GTHarvestNode, "Node_Cache_%d" % index, x, y, 30)
        cache.set_editor_property("node_name", "alloy cache")
        cache.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_RadiationCache")
        cache.set_editor_property("uses", 2)
        cache.set_editor_property("colour", unreal.LinearColor(0.3, 0.9, 0.35, 1.0))

    # Nodes and wrecks along the route.
    for index, (x, y) in enumerate(((15000, 1200), (50000, -1400), (95000, 1300))):
        node = spawn(world, unreal.GTHarvestNode, "Node_Cable_%d" % index, x, y, 30)
        node.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_CableBundle")
    for index, (x, y, yaw) in enumerate(((30000, -1500, 20.0), (85000, 1600, -35.0))):
        wreck = spawn(world, unreal.GTWreck, "Wreck_%d" % index, x, y, 55, yaw=yaw)
        wreck.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_Wreck")
    post = spawn(world, unreal.GTWinchAnchor, "Post_Mud", 74500, 1600, 0)
    post.get_anchor().set_editor_property("strength_n", 200000.0)
    post.get_anchor().set_editor_property("display_name", "steel post")

    # The weather front: 300 m behind the start, sweeping +X at 4 m/s (it reaches the extraction in about six minutes).
    front = spawn(world, unreal.GTWeatherFront, "Front_A", -30000, 0, 1500)
    front.set_editor_property("speed_cm_per_sec", 400.0)
    front.set_editor_property("influence_cm", 15000.0)


if eal.does_asset_exist(LEVEL_PATH):
    log("level exists: rebuilding the props in " + LEVEL_PATH)
    if not les.load_level(LEVEL_PATH):
        raise SystemExit("could not load level " + LEVEL_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    removed = sum(lib.destroy_actors_with_label_prefix(world, prefix) for prefix in PROP_PREFIXES)
    log("removed %d old props" % removed)
    build_props(world)
else:
    if not les.new_level(LEVEL_PATH):
        raise SystemExit("could not create level " + LEVEL_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    tarmac = load_or_none(SURF_PATH + "/PM_Tarmac")
    mi_tarmac = load_or_none(MAT_PATH + "/MI_Env_Tarmac")
    box(world, "Floor", 60000, 0, -50, 1500, 300, 1, surface=tarmac, material=mi_tarmac)
    sun = spawn(world, unreal.DirectionalLight, "Sun", 0, 0, 1000)
    sun.set_actor_rotation(rot(pitch=-40, yaw=20), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.0)
    sky = spawn(world, unreal.SkyLight, "SkyLight", 0, 0, 1000)
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    spawn(world, unreal.SkyAtmosphere, "SkyAtmosphere", 0, 0, 0)
    spawn(world, unreal.ExponentialHeightFog, "HeightFog", 0, 0, 0)
    spawn(world, unreal.PlayerStart, "PlayerStart", 0, 0, 120)
    build_props(world)
    log("created level " + LEVEL_PATH)

if not les.save_current_level():
    raise SystemExit("could not save level")
log("DONE")
