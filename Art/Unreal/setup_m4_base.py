"""setup_m4_base.py - items, recipes, crew upgrades and the greybox convoy base, headless.

Run with Art\\setup_m4_base.bat (close the editor first; run setup_m1_track and setup_m3_leg
before it). Creates:
- /Game/GrandTour/Items/DA_Item_* (resources, parts, consumables), /Game/GrandTour/Crafting/
  DA_Recipe_* and /Game/GrandTour/Economy/DA_Upgrade_* from the C++ defaults (UGTItemRegistry
  builds the same set at runtime when they are missing);
- /Game/GrandTour/Base/L_Base: a 120 x 80 m tarmac yard with the car lift (the PlayerStart is on
  it, so the car spawns parked there), the workbench, the trader, the crew tent, the briefing
  board and the departure gate at the far end of a short road. The base game mode puts you on
  foot beside the car; drive out through the gate to start the next leg.
Safe to re-run: the props are rebuilt from the table below; the floor and lighting are kept.
"""
import unreal

LEVEL_PATH = "/Game/GrandTour/Base/L_Base"
ITEM_FOLDER = "/Game/GrandTour/Items"
RECIPE_FOLDER = "/Game/GrandTour/Crafting"
UPGRADE_FOLDER = "/Game/GrandTour/Economy"
SURF_PATH = "/Game/GrandTour/Terrain/Surfaces"
MAT_PATH = "/Game/GrandTour/Materials"
PROP_PREFIXES = ("Station_", "Gate_", "Marker_", "Wall_", "Road_")

lib = unreal.GTVehicleSetupLibrary
eal = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cube = unreal.load_asset("/Engine/BasicShapes/Cube")


def log(msg):
    unreal.log("SETUP_M4_BASE " + msg)


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
saved_items = lib.create_item_assets(ITEM_FOLDER)
saved_recipes = lib.create_recipe_assets(RECIPE_FOLDER)
saved_upgrades = lib.create_upgrade_assets(UPGRADE_FOLDER)
log("items saved: %d (expected 24), recipes: %d (expected 7), upgrades: %d (expected 7)" % (saved_items, saved_recipes, saved_upgrades))
if saved_items < 24 or saved_recipes < 7 or saved_upgrades < 7:
    raise SystemExit("asset writing fell short")
heater = eal.load_asset(ITEM_FOLDER + "/DA_Item_Part_Heater")
log("DA_Item_Part_Heater: slot %s price %d resistances %d" % (heater.get_editor_property("slot"), heater.get_editor_property("base_price"), len(heater.get_editor_property("resistances"))))


# ---- level ------------------------------------------------------------------------------------
def build_props(world):
    mi = {name: load_or_none(MAT_PATH + "/MI_Env_" + name) for name in ("Tarmac", "Marker", "Greybox")}
    tarmac = load_or_none(SURF_PATH + "/PM_Tarmac")
    # The lift under the PlayerStart; the car spawns parked on it facing +X with the gate road ahead.
    # Stations stand clear of the road (|y| < 4 m): workbench, trader and briefing board on the
    # driver's side (-Y, where you get out), the crew tent across the yard.
    spawn(world, unreal.GTCarLift, "Station_Lift", 0, 0, 10)
    spawn(world, unreal.GTWorkbench, "Station_Workbench", 300, -800, 45)
    spawn(world, unreal.GTTrader, "Station_Trader", -500, -800, 50)
    spawn(world, unreal.GTBriefingBoard, "Station_Briefing", 1100, -650, 55, yaw=90.0)
    spawn(world, unreal.GTCrewTent, "Station_Crew", -1200, 1000, 110)
    # A short road out to the gate, 40 m ahead, and the gate itself.
    box(world, "Road_Out", 2000, 0, -9, 40, 8, 0.2, surface=tarmac, material=mi["Greybox"])
    spawn(world, unreal.GTDepartGate, "Gate_Depart", 4000, 0, 200)
    for side in (-1, 1):
        box(world, "Gate_Post_%d" % side, 4000, side * 650, 200, 0.5, 0.5, 4, material=mi["Marker"])
    # Yard walls with the opening at the gate.
    box(world, "Wall_Back", -2000, 0, 150, 0.4, 60, 3, material=mi["Greybox"])
    for side in (-1, 1):
        box(world, "Wall_Side_%d" % side, 1000, side * 3000, 150, 60, 0.4, 3, material=mi["Greybox"])
        box(world, "Wall_Front_%d" % side, 4000, side * 1900, 150, 0.4, 24, 3, material=mi["Greybox"])


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
    box(world, "Floor", 1000, 0, -50, 120, 80, 1, surface=tarmac, material=mi_tarmac)
    sun = spawn(world, unreal.DirectionalLight, "Sun", 0, 0, 1000)
    sun.set_actor_rotation(rot(pitch=-50, yaw=40), False)
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.0)
    sky = spawn(world, unreal.SkyLight, "SkyLight", 0, 0, 1000)
    sky.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)
    spawn(world, unreal.SkyAtmosphere, "SkyAtmosphere", 0, 0, 0)
    spawn(world, unreal.ExponentialHeightFog, "HeightFog", 0, 0, 0)
    spawn(world, unreal.PlayerStart, "PlayerStart", 0, 0, 140)
    build_props(world)
    log("created level " + LEVEL_PATH)

# The base runs AGTBaseGameMode; every other map uses the global default (AGTRunGameMode).
settings = world.get_world_settings()
settings.set_editor_property("default_game_mode", unreal.GTBaseGameMode.static_class())
override = settings.get_editor_property("default_game_mode")
log("game mode override: %s" % (override.get_name() if override else None))
if override is None or override.get_name() != "GTBaseGameMode":
    raise SystemExit("could not set the base game mode on " + LEVEL_PATH)

if not les.save_current_level():
    raise SystemExit("could not save level")
log("DONE")
