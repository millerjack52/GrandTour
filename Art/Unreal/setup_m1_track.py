"""setup_m1_track.py - M1 greybox track and surface assets, headless.

Run with Art\\setup_m1_track.bat (close the editor first). Creates:
- /Game/GrandTour/Terrain/Surfaces/PM_{Tarmac,Dirt,Mud,Snow}: UGTSurfacePhysMaterial assets
  (dry grip in the inherited Friction, wet grip, rolling drag, sinkage, track depth, surface tag).
- /Game/GrandTour/Materials/M_GT_Environment: the environment master (BaseColor and Roughness
  parameters; MF_Weather goes in here later so every instance picks it up) and one instance per
  surface plus a grey one for greybox props.
- /Game/GrandTour/Test/L_TestTrack: a 600 x 200 m tarmac floor; a straight of four 60 m lanes
  (tarmac, dirt, mud, snow) along +X from x = 0 ending in a wall at 245 m (the headless surface
  test drives this); and off to the side (y = +40 m) a 12 degree climb to a plateau, a jump ramp,
  a rough patch and a slalom for driving by hand.
Safe to re-run: surface values and materials are re-applied from the tables below; an existing
map is left alone except the rough patch, which is rebuilt from the current design.
"""
import random

import unreal

SURF_PATH = "/Game/GrandTour/Terrain/Surfaces"
MAT_PATH = "/Game/GrandTour/Materials"
LEVEL_PATH = "/Game/GrandTour/Test/L_TestTrack"
LANE_LEN = 6000.0     # cm
LANE_W = 1200.0
WALL_X = 24500.0

# name: (friction, wet_scale, rolling, sink_rate, max_sink, drag_scale, plough, grip_loss, track_depth, colour,
#        wet_rolling, wet_sink)
# This table is the source of truth for surface numbers and is applied on every run.
# friction is the real tyre-to-ground coefficient (the wheel's FrictionForceMultiplier is 1.0 since driving feel
# stage 1, docs/DRIVING_FEEL_PLAN.md): a car on it corners and brakes at about that many g. Before stage 1 the
# multiplier was the Chaos default 2.0 and dirt at 0.62 meant 1.24 g, a car that could not slide. grip_loss takes
# its share off at full sinkage, which dirt reaches after a few seconds at speed: 0.1 leaves dirt at 0.56 (gravel),
# 0.3 leaves mud at 0.27 and snow at 0.20. Stage 3: Mud is the shallow line of a bog (sinks to 22 cm, just past the
# 19 cm axle clearance, so a locked low-range crawl still has more grip than drag); Bog is the deep mud down its
# middle (sinks to 40 cm: the axles ride on it; at full sinkage grip 0.23 against drag 0.135 of the load at rest, so
# a crawl pulls away from a dead stop on the flat and climbs about 5 degrees, and the plough drag holds it to about
# 7 km/h with the wheels churning; the user's first bog had drag 0.66 against 0.30 and the car could not move at all,
# the second 0.18 against 0.16 with a squared plough law and it stopped on any hummock and could not drive out).
# sink_rate is metres per second while rolling through the surface; sitting still grows at 30 %
# of it, wheelspin adds up to 150 % (UGTTractionComponent). Drag as a fraction of wheel load:
# rolling x (1 + drag_scale x sinkage) + plough x sinkage x (speed / 10 m/s) (squared past 10 m/s). First gear can
# push about 0.26 g, so keep rolling x (1 + drag_scale) under ~0.15 for anything a car should
# pull away in; plough is what makes deep mud punish speed. wet_rolling multiplies rolling and
# wet_sink multiplies sink_rate and max_sink when the weather subsystem's wetness is 1 (M3): wet
# dirt drives like shallow mud, wet tarmac only loses grip (wet_scale).
SURFACES = {
    "Tarmac": (0.95, 0.75, 0.012, 0.00, 0.00, 0.0, 0.00, 0.0, 0.0, (0.16, 0.16, 0.17), 1.0, 1.0),
    "Dirt":   (0.62, 0.80, 0.030, 0.01, 0.05, 1.0, 0.02, 0.1, 0.3, (0.45, 0.33, 0.20), 1.6, 3.0),
    "Mud":    (0.42, 0.95, 0.060, 0.08, 0.22, 1.0, 0.25, 0.3, 1.0, (0.28, 0.20, 0.12), 1.2, 1.3),
    "Bog":    (0.36, 0.95, 0.040, 0.14, 0.40, 0.8, 0.45, 0.25, 1.0, (0.18, 0.13, 0.08), 1.2, 1.3),
    "Snow":   (0.28, 1.00, 0.060, 0.04, 0.25, 1.0, 0.08, 0.3, 0.8, (0.90, 0.92, 0.96), 1.0, 1.0),
}

tools = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
lib = unreal.GTVehicleSetupLibrary
mel = unreal.MaterialEditingLibrary


def log(msg):
    unreal.log("SETUP_M1 " + msg)


def get_or_create(name, path, cls, factory):
    full = path + "/" + name
    asset = eal.load_asset(full) if eal.does_asset_exist(full) else None
    if asset is None:
        asset = tools.create_asset(name, path, cls, factory)
        if asset is None:
            raise SystemExit("could not create " + full)
        log("created " + full)
    return asset


# ---- surface physical materials ---------------------------------------------------------
phys = {}
for name, (fric, wet, roll, rate, mx, drag, plough, loss, depth, _, wet_roll, wet_sink) in SURFACES.items():
    factory = unreal.PhysicalMaterialFactoryNew()
    factory.set_editor_property("physical_material_class", unreal.GTSurfacePhysMaterial)
    pm = get_or_create("PM_" + name, SURF_PATH, unreal.GTSurfacePhysMaterial, factory)
    if not lib.set_surface_tag(pm, "Surface." + name):
        unreal.log_warning("SETUP_M1 unknown gameplay tag Surface." + name)
    pm.set_editor_property("friction", fric)
    pm.set_editor_property("wet_friction_scale", wet)
    pm.set_editor_property("rolling_resistance", roll)
    pm.set_editor_property("sinkage_rate", rate)
    pm.set_editor_property("max_sinkage", mx)
    pm.set_editor_property("sinkage_drag_scale", drag)
    pm.set_editor_property("plough_drag", plough)
    pm.set_editor_property("sinkage_grip_loss", loss)
    pm.set_editor_property("track_depth", depth)
    pm.set_editor_property("wet_rolling_resistance_scale", wet_roll)
    pm.set_editor_property("wet_sinkage_scale", wet_sink)
    eal.save_loaded_asset(pm)
    phys[name] = pm
log("surface physical materials: " + ", ".join(phys))

# ---- environment master material + instances --------------------------------------------
materials = {}
try:
    master_full = MAT_PATH + "/M_GT_Environment"
    if eal.does_asset_exist(master_full):
        master = eal.load_asset(master_full)
    else:
        master = tools.create_asset("M_GT_Environment", MAT_PATH, unreal.Material, unreal.MaterialFactoryNew())
        colour = mel.create_material_expression(master, unreal.MaterialExpressionVectorParameter, -400, 0)
        colour.set_editor_property("parameter_name", "BaseColor")
        colour.set_editor_property("default_value", unreal.LinearColor(0.5, 0.5, 0.5, 1.0))
        rough = mel.create_material_expression(master, unreal.MaterialExpressionScalarParameter, -400, 250)
        rough.set_editor_property("parameter_name", "Roughness")
        rough.set_editor_property("default_value", 0.85)
        mel.connect_material_property(colour, "", unreal.MaterialProperty.MP_BASE_COLOR)
        mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
        mel.recompile_material(master)
        eal.save_loaded_asset(master)
        log("created " + master_full)

    def make_instance(name, colour, roughness=0.85):
        inst = get_or_create(name, MAT_PATH, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        mel.set_material_instance_parent(inst, master)
        mel.set_material_instance_vector_parameter_value(inst, "BaseColor", unreal.LinearColor(colour[0], colour[1], colour[2], 1.0))
        mel.set_material_instance_scalar_parameter_value(inst, "Roughness", roughness)
        mel.update_material_instance(inst)
        eal.save_loaded_asset(inst)
        return inst

    for name, spec in SURFACES.items():
        materials[name] = make_instance("MI_Env_" + name, spec[9], 0.6 if name == "Snow" else 0.85)
    materials["Greybox"] = make_instance("MI_Env_Greybox", (0.55, 0.55, 0.55))
    materials["Marker"] = make_instance("MI_Env_Marker", (0.9, 0.35, 0.1))
    log("materials: " + ", ".join(materials))
except Exception as e:  # materials are cosmetic; the track must still build
    unreal.log_warning("SETUP_M1 material creation failed, using defaults: %s" % e)

# ---- level ----------------------------------------------------------------------------------
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
cube = unreal.load_asset("/Engine/BasicShapes/Cube")
cylinder = unreal.load_asset("/Engine/BasicShapes/Cylinder")


def rot(pitch=0.0, yaw=0.0, roll=0.0):
    # unreal.Rotator's positional order is (roll, pitch, yaw); always use keywords.
    return unreal.Rotator(roll=roll, pitch=pitch, yaw=yaw)


def box(world, label, x, y, z, sx, sy, sz, pitch=0.0, yaw=0.0, surface=None, material=None, mesh=None, roll=0.0):
    transform = unreal.Transform(unreal.Vector(x, y, z), rot(pitch, yaw, roll), unreal.Vector(sx, sy, sz))
    actor = lib.spawn_static_mesh_actor(world, mesh or cube, transform, label)
    if actor is None:
        raise SystemExit("could not spawn " + label)
    comp = actor.get_editor_property("static_mesh_component")
    if surface is not None:
        comp.set_phys_material_override(surface)
    if material is not None:
        comp.set_material(0, material)
    return actor


FEATURE_PREFIXES = ("Climb", "Plateau", "Descent", "JumpRamp", "Rough_", "Cone_", "Sun")


def build_features(world):
    """Hand-driving features on a parallel strip at y = +40 m, and the sun."""
    fy = 4000
    m = materials.get
    box(world, "Climb", 1956, fy, 416, 40, 12, 0.2, pitch=12.0, surface=phys["Dirt"], material=m("Dirt"))
    box(world, "Plateau", 5900, fy, 822, 40, 12, 0.2, surface=phys["Dirt"], material=m("Dirt"))
    box(world, "Descent", 9844, fy, 416, 40, 12, 0.2, pitch=-12.0, surface=phys["Dirt"], material=m("Dirt"))
    box(world, "JumpRamp", 13400, fy, 70, 8, 12, 0.2, pitch=10.0, surface=phys["Tarmac"], material=m("Greybox"))
    # Smooth ridges across the lane instead of hard-edged boxes: cylinders lying across the
    # driving direction (roll 90), radius 25 cm, buried so the crests stand 8..15 cm proud, every 3 m.
    rng = random.Random(7)
    for i in range(10):
        crest = 8 + 7 * rng.random()          # cm above the floor
        box(world, "Rough_Ridge_%d" % i, 15500 + i * 300, fy, crest - 25, 0.5, 0.5, 12,
            surface=phys["Dirt"], material=m("Dirt"), mesh=cylinder, roll=90.0)
    for i in range(7):
        box(world, "Cone_%d" % i, 19000 + i * 1000, fy + (300 if i % 2 else -300), 60, 0.6, 0.6, 1.2,
            material=m("Marker"), mesh=cylinder)
    sun = lib.spawn_actor_of_class(world, unreal.DirectionalLight,
                                   unreal.Transform(unreal.Vector(0, 0, 1000), rot(pitch=-45, yaw=30), unreal.Vector(1, 1, 1)), "Sun")
    if sun is None:
        raise SystemExit("could not spawn the sun")
    sun.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.0)


if eal.does_asset_exist(LEVEL_PATH):
    log("level exists: rebuilding the feature strip and sun in " + LEVEL_PATH)
    if not les.load_level(LEVEL_PATH):
        raise SystemExit("could not load level " + LEVEL_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    removed = sum(lib.destroy_actors_with_label_prefix(world, prefix) for prefix in FEATURE_PREFIXES)
    log("removed %d old feature actors" % removed)
    build_features(world)
    if not les.save_current_level():
        raise SystemExit("could not save level")
else:
    if not les.new_level(LEVEL_PATH):
        raise SystemExit("could not create level " + LEVEL_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    m = materials.get

    # Floor: 600 m x 200 m tarmac, top at z = 0, x from -200 m to 400 m.
    box(world, "Floor", 10000, 0, -50, 600, 200, 1, surface=phys["Tarmac"], material=m("Tarmac"))

    # Surface straight: four lanes, 20 cm slabs whose top sits 1 cm proud of the floor.
    for index, name in enumerate(["Tarmac", "Dirt", "Mud", "Snow"]):
        cx = index * LANE_LEN + LANE_LEN / 2
        box(world, "Lane_" + name, cx, 0, -9, LANE_LEN / 100, LANE_W / 100, 0.2, surface=phys[name], material=m(name))
        # kerb markers either side at the lane start
        for side in (-1, 1):
            box(world, "Marker_%s_%d" % (name, side), index * LANE_LEN, side * (LANE_W / 2 + 60), 40, 0.4, 0.4, 0.8,
                material=m("Marker"))
    box(world, "Wall", WALL_X, 0, 150, 1, 14, 3, surface=phys["Tarmac"], material=m("Greybox"))

    build_features(world)

    for cls, loc, label in (
        (unreal.SkyLight, (0, 0, 1000), "SkyLight"),
        (unreal.SkyAtmosphere, (0, 0, 0), "SkyAtmosphere"),
        (unreal.ExponentialHeightFog, (0, 0, 0), "HeightFog"),
        (unreal.PlayerStart, (-2500, 0, 120), "PlayerStart"),
    ):
        actor = lib.spawn_actor_of_class(world, cls, unreal.Transform(unreal.Vector(*loc), rot(), unreal.Vector(1, 1, 1)), label)
        if actor is None:
            raise SystemExit("could not spawn " + label)
        if cls is unreal.SkyLight:
            actor.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True)

    if not les.save_current_level():
        raise SystemExit("could not save level")
    log("created level " + LEVEL_PATH)

log("DONE")
