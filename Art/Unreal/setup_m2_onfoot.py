"""setup_m2_onfoot.py - the on-foot test map, headless.

Run with Art\\setup_m2_onfoot.bat (close the editor first; run setup_m1_track.bat before it for
the surface materials). Creates /Game/GrandTour/Test/L_OnFootTest, the map the possession swap
lives on for the life of the project (ARCHITECTURE 5, Enter / exit):
- a 300 x 300 m tarmac floor, sun, sky, fog, the PlayerStart (the car spawns there, F gets out);
- a 40 m mud lane ahead of the car so the winch has a job (drive in, bog, get out, rig a post);
- two cable bundles (cutter), a wreck (pry bar, also an anchor), a strong post and a rotten post
  (winch anchors), a hazard volume marked by a red slab (exposure drains inside it), and a wall.
Safe to re-run: the props are rebuilt from the table below; the floor and lighting are kept.
"""
import unreal

LEVEL_PATH = "/Game/GrandTour/Test/L_OnFootTest"
SURF_PATH = "/Game/GrandTour/Terrain/Surfaces"
MAT_PATH = "/Game/GrandTour/Materials"
PROP_PREFIXES = ("Node_", "Wreck_", "Post_", "Hazard_", "Wall_", "Lane_", "Marker_")

lib = unreal.GTVehicleSetupLibrary
eal = unreal.EditorAssetLibrary
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cube = unreal.load_asset("/Engine/BasicShapes/Cube")


def log(msg):
    unreal.log("SETUP_M2_ONFOOT " + msg)


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


def build_props(world):
    mud = load_or_none(SURF_PATH + "/PM_Mud")
    mi_mud = load_or_none(MAT_PATH + "/MI_Env_Mud")
    mi_marker = load_or_none(MAT_PATH + "/MI_Env_Marker")
    mi_grey = load_or_none(MAT_PATH + "/MI_Env_Greybox")
    if mud is None:
        unreal.log_warning("SETUP_M2_ONFOOT no PM_Mud (run setup_m1_track.bat first); the lane will be plain")
    # Mud lane 20 m ahead of the start, 40 m long, 12 m wide, 1 cm proud of the floor.
    box(world, "Lane_Mud", 4000, 0, -9, 40, 12, 0.2, surface=mud, material=mi_mud)
    for side in (-1, 1):
        box(world, "Marker_Mud_%d" % side, 2000, side * 660, 40, 0.4, 0.4, 0.8, material=mi_marker)
    # Cable bundles and the wreck to the right of the start.
    spawn(world, unreal.GTHarvestNode, "Node_Cable_A", 800, 900, 30)
    spawn(world, unreal.GTHarvestNode, "Node_Cable_B", 1400, 1100, 30)
    spawn(world, unreal.GTWreck, "Wreck_A", 1200, -1200, 55, yaw=25.0)
    # Anchors: a strong post past the mud, a rotten one by the wreck.
    strong = spawn(world, unreal.GTWinchAnchor, "Post_Strong", 6800, 0, 0)
    strong.get_anchor().set_editor_property("strength_n", 200000.0)
    strong.get_anchor().set_editor_property("display_name", "steel post")
    rotten = spawn(world, unreal.GTWinchAnchor, "Post_Rotten", 2200, -1800, 0)
    rotten.get_anchor().set_editor_property("strength_n", 3000.0)
    rotten.get_anchor().set_editor_property("display_name", "rotten post")
    # Hazard volume 15 m to the left, marked by a red slab on the floor.
    hazard = spawn(world, unreal.GTHazardVolume, "Hazard_A", 0, 2500, 200)
    hazard.set_editor_property("extent", unreal.Vector(800, 800, 400))
    hazard.set_editor_property("exposure_drain_per_second", 8.0)
    box(world, "Hazard_A_Marker", 0, 2500, -9, 16, 16, 0.2, material=mi_marker)
    # A wall to winch against (cable snap) beyond the strong post.
    box(world, "Wall_A", 8200, 0, 150, 1, 14, 3, material=mi_grey)


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
    box(world, "Floor", 3000, 0, -50, 300, 300, 1, surface=tarmac, material=mi_tarmac)
    sun = spawn(world, unreal.DirectionalLight, "Sun", 0, 0, 1000)
    sun.set_actor_rotation(rot(pitch=-45, yaw=30), False)
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
