"""setup_m5_legs.py - the tour's leg and tour assets and the greybox maps of legs 2 to 5, headless.

Run with Art\\setup_m5_legs.bat (close the editor first; run setup_m1_track, setup_m3_weather and
setup_m3_leg before it). Creates:
- /Game/GrandTour/Legs/DA_Leg_01..05 from the C++ defaults (UGTLegDefinition::ApplyDefault; DA_Leg_01
  is rewritten unchanged) and /Game/GrandTour/Race/DA_Tour_01 (UGTTourDefinition::ApplyDefaultTour01:
  the five legs, four rivals, points and prizes by placing, the ending lines);
- /Game/GrandTour/Legs/L_Leg02..L_Leg05, greybox legs along +X on a tarmac floor, from the table
  below: surface lanes, a zigzag route marked by posts, checkpoints, the extraction zone, radiation
  pockets with alloy caches, cable bundles, wrecks and winch posts, weather fronts, and on the
  photograph leg the subject in a hide of posts. The car spawns at the start; each AGTLegStart names
  its DA_Leg_0N. L_Leg01 stays with setup_m3_leg.py.
Safe to re-run: the props are rebuilt from the table; each floor and its lighting are kept.
"""
import math

import unreal

LEG_FOLDER = "/Game/GrandTour/Legs"
RACE_FOLDER = "/Game/GrandTour/Race"
HARVEST_FOLDER = "/Game/GrandTour/Harvest"
WEATHER_FOLDER = "/Game/GrandTour/Weather"
SURF_PATH = "/Game/GrandTour/Terrain/Surfaces"
MAT_PATH = "/Game/GrandTour/Materials"
PROP_PREFIXES = ("Lane_", "Marker_", "Road_", "Roof_", "Post_", "Node_", "Wreck_", "Zone_", "Front_", "Checkpoint_", "Extraction_", "LegStart_", "Subject_", "Hide_")

# Distances in metres along +X; lateral offsets in metres (+Y is the passenger side when facing +X).
LEGS = [
    dict(number=2, length=1600, weather="Rain",
         lanes=[("Dirt", 200, 500), ("Mud", 520, 560), ("Dirt", 560, 900), ("Mud", 900, 940), ("Mud", 1300, 1340)],
         checkpoints=[(600, 60), (1200, -60)], extraction=1600, roof=None,
         radiation=None, subject=None,
         cables=[(300, 15), (1000, -14)], wrecks=[(700, 18, 20.0), (1450, -16, -30.0)],
         posts=[(545, 18), (925, -18), (1325, 18)],
         front=dict(start=-200, speed=500.0, influence=150)),
    dict(number=3, length=1400, weather="Clear",
         lanes=[("Dirt", 400, 1000)],
         checkpoints=[(500, 0), (1100, 40)], extraction=1400, roof=None,
         radiation=dict(x=700, y=120, half=25, caches=[(690, 125)]),
         subject=dict(x=735, y=150, name="spectacled bear"),
         cables=[(250, -14), (1250, 16)], wrecks=[(900, -17, 15.0)],
         posts=[], front=None),
    dict(number=4, length=2000, weather="Snow",
         lanes=[("Snow", 300, 900), ("Snow", 1200, 1800)],
         checkpoints=[(700, -50), (1400, 50)], extraction=2000, roof=1000,
         radiation=None, subject=None,
         cables=[(200, 14), (1050, -15), (1900, 15)], wrecks=[(600, -18, 25.0), (1600, 17, -20.0)],
         posts=[(850, 18)], front=None),
    dict(number=5, length=2400, weather="Clear",
         lanes=[("Dirt", 200, 1200), ("Mud", 1300, 1340), ("Dirt", 1400, 2200), ("Mud", 1900, 1940)],
         checkpoints=[(800, 0), (1600, -80)], extraction=2400, roof=None,
         radiation=dict(x=1200, y=-150, half=25, caches=[(1195, -150), (1212, -138)]),
         subject=None,
         cables=[(400, 15), (1500, -16), (2100, 14)], wrecks=[(1000, -17, 10.0), (1750, 18, -40.0), (2250, -15, 30.0)],
         posts=[(1325, 18), (1925, -18)],
         front=dict(start=-300, speed=350.0, influence=150)),
]

lib = unreal.GTVehicleSetupLibrary
eal = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cube = unreal.load_asset("/Engine/BasicShapes/Cube")


def log(msg):
    unreal.log("SETUP_M5_LEGS " + msg)


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
saved_legs = lib.create_leg_assets(LEG_FOLDER, WEATHER_FOLDER)
log("leg assets saved: %d (expected 5)" % saved_legs)
saved_tour = lib.create_tour_assets(RACE_FOLDER, LEG_FOLDER)
log("tour assets saved: %d (expected 1)" % saved_tour)
if saved_legs < 5 or saved_tour < 1:
    raise SystemExit("asset writing fell short")
tour = eal.load_asset(RACE_FOLDER + "/DA_Tour_01")
log("DA_Tour_01: %d legs, %d rivals, credits %d" % (len(tour.get_editor_property("leg_paths")), len(tour.get_editor_property("rivals")), tour.get_editor_property("starting_credits")))


# ---- one leg's props --------------------------------------------------------------------------
def route_points(spec):
    pts = [(0.0, 0.0)] + [(float(x), float(y)) for x, y in spec["checkpoints"]] + [(float(spec["extraction"]), 0.0)]
    return pts


def build_props(world, spec):
    n = spec["number"]
    surf = {name: load_or_none(SURF_PATH + "/PM_" + name) for name in ("Tarmac", "Dirt", "Mud", "Snow")}
    mi = {name: load_or_none(MAT_PATH + "/MI_Env_" + name) for name in ("Tarmac", "Dirt", "Mud", "Snow", "Marker", "Greybox")}
    if surf["Dirt"] is None or surf["Mud"] is None or surf["Snow"] is None:
        unreal.log_warning("SETUP_M5_LEGS surface materials missing (run setup_m1_track.bat first); lanes will be plain")

    # Surface lanes: 30 m wide, 1 cm proud of the floor, with a marker post either side at the start.
    for index, (kind, a, b) in enumerate(spec["lanes"]):
        box(world, "Lane_%d_%s" % (index, kind), (a + b) * 50.0, 0, -9, float(b - a), 30, 0.2, surface=surf[kind], material=mi[kind])
        for side in (-1, 1):
            box(world, "Marker_%d_%d" % (index, side), a * 100.0, side * 1600, 40, 0.4, 0.4, 0.8, material=mi["Marker"])

    # The route as posts every 100 m, 15 m either side of the line start -> checkpoints -> extraction.
    pts = route_points(spec)
    count = 0
    for (x0, y0), (x1, y1) in zip(pts[:-1], pts[1:]):
        dx, dy = x1 - x0, y1 - y0
        length = (dx * dx + dy * dy) ** 0.5
        if length < 1.0:
            continue
        nx, ny = -dy / length, dx / length
        d = 0.0
        while d < length:
            px, py = x0 + dx * d / length, y0 + dy * d / length
            for side in (-1, 1):
                box(world, "Road_%d" % count, (px + side * 15.0 * nx) * 100.0, (py + side * 15.0 * ny) * 100.0, 30, 0.3, 0.3, 0.6, material=mi["Greybox"])
                count += 1
            d += 100.0

    # A shelter roof: a 12 x 12 m slab 5 m up on two posts, straddling the road.
    if spec["roof"] is not None:
        rx = spec["roof"] * 100.0
        box(world, "Roof_A", rx, 0, 500, 12, 12, 0.2, material=mi["Greybox"])
        for side in (-1, 1):
            box(world, "Roof_A_Post_%d" % side, rx, side * 550, 250, 0.4, 0.4, 5, material=mi["Greybox"])

    # Checkpoints, the extraction zone, the leg start.
    for index, (x, y) in enumerate(spec["checkpoints"], start=1):
        checkpoint = spawn(world, unreal.GTCheckpoint, "Checkpoint_%d" % index, x * 100.0, y * 100.0, 250)
        checkpoint.set_editor_property("index", index)
        checkpoint.set_editor_property("extent", unreal.Vector(150, 1500, 500))
    extraction = spawn(world, unreal.GTExtractionZone, "Extraction_A", spec["extraction"] * 100.0, 0, 250)
    extraction.set_editor_property("extent", unreal.Vector(1000, 1000, 500))
    start = spawn(world, unreal.GTLegStart, "LegStart_A", 0, 0, 0)
    start.set_editor_property("leg_asset_path", "%s/DA_Leg_%02d" % (LEG_FOLDER, n))

    # A radiation pocket with alloy caches.
    rad = spec["radiation"]
    if rad is not None:
        zone = spawn(world, unreal.GTRadiationZone, "Zone_Radiation_A", rad["x"] * 100.0, rad["y"] * 100.0, 600)
        zone.set_editor_property("extent", unreal.Vector(rad["half"] * 100.0, rad["half"] * 100.0, 600))
        for index, (x, y) in enumerate(rad["caches"]):
            cache = spawn(world, unreal.GTHarvestNode, "Node_Cache_%d" % index, x * 100.0, y * 100.0, 30)
            cache.set_editor_property("node_name", "alloy cache")
            cache.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_RadiationCache")
            cache.set_editor_property("uses", 2)
            cache.set_editor_property("colour", unreal.LinearColor(0.3, 0.9, 0.35, 1.0))

    # The photograph leg's subject, in a hide of six posts (a thicket) 6 m out, with a way in.
    subject = spec["subject"]
    if subject is not None:
        bear = spawn(world, unreal.GTPhotoSubject, "Subject_A", subject["x"] * 100.0, subject["y"] * 100.0, 100, yaw=180.0)
        bear.set_editor_property("subject_name", subject["name"])
        for index in range(6):
            angle = math.radians(index * 60.0 + 30.0)
            box(world, "Hide_%d" % index, subject["x"] * 100.0 + math.cos(angle) * 600.0, subject["y"] * 100.0 + math.sin(angle) * 600.0, 150, 0.5, 0.5, 3.0, material=mi["Greybox"])

    # Nodes, wrecks and winch posts along the route.
    for index, (x, y) in enumerate(spec["cables"]):
        node = spawn(world, unreal.GTHarvestNode, "Node_Cable_%d" % index, x * 100.0, y * 100.0, 30)
        node.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_CableBundle")
    for index, (x, y, yaw) in enumerate(spec["wrecks"]):
        wreck = spawn(world, unreal.GTWreck, "Wreck_%d" % index, x * 100.0, y * 100.0, 55, yaw=yaw)
        wreck.set_editor_property("loot_table_path", HARVEST_FOLDER + "/DA_Loot_Wreck")
    for index, (x, y) in enumerate(spec["posts"]):
        post = spawn(world, unreal.GTWinchAnchor, "Post_%d" % index, x * 100.0, y * 100.0, 0)
        post.get_anchor().set_editor_property("strength_n", 200000.0)
        post.get_anchor().set_editor_property("display_name", "steel post")

    # The weather front behind the start, sweeping +X.
    front = spec["front"]
    if front is not None:
        actor = spawn(world, unreal.GTWeatherFront, "Front_A", front["start"] * 100.0, 0, 1500)
        actor.set_editor_property("speed_cm_per_sec", front["speed"])
        actor.set_editor_property("influence_cm", front["influence"] * 100.0)


def build_level(spec):
    n = spec["number"]
    level_path = "%s/L_Leg%02d" % (LEG_FOLDER, n)
    if eal.does_asset_exist(level_path):
        log("level exists: rebuilding the props in " + level_path)
        if not les.load_level(level_path):
            raise SystemExit("could not load level " + level_path)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        removed = sum(lib.destroy_actors_with_label_prefix(world, prefix) for prefix in PROP_PREFIXES)
        log("removed %d old props" % removed)
        build_props(world, spec)
    else:
        if not les.new_level(level_path):
            raise SystemExit("could not create level " + level_path)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        tarmac = load_or_none(SURF_PATH + "/PM_Tarmac")
        mi_tarmac = load_or_none(MAT_PATH + "/MI_Env_Tarmac")
        length = spec["length"]
        box(world, "Floor", length * 50.0, 0, -50, float(length + 300), 400, 1, surface=tarmac, material=mi_tarmac)
        sun = spawn(world, unreal.DirectionalLight, "Sun", 0, 0, 1000)
        sun.set_actor_rotation(rot(pitch=-40, yaw=20), False)
        sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.0)
        sky = spawn(world, unreal.SkyLight, "SkyLight", 0, 0, 1000)
        sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
        spawn(world, unreal.SkyAtmosphere, "SkyAtmosphere", 0, 0, 0)
        spawn(world, unreal.ExponentialHeightFog, "HeightFog", 0, 0, 0)
        spawn(world, unreal.PlayerStart, "PlayerStart", 0, 0, 120)
        build_props(world, spec)
        log("created level " + level_path)
    if not les.save_current_level():
        raise SystemExit("could not save level " + level_path)
    log("saved %s (%d m, %s, %d checkpoints)" % (level_path, spec["length"], spec["weather"], len(spec["checkpoints"])))


for leg_spec in LEGS:
    build_level(leg_spec)
log("DONE")
