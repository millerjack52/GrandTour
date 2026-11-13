"""setup_m0.py - one-off M0 setup, headless: physics asset for SK_RangeRover and a flat test level.

Run with:
  UnrealEditor-Cmd.exe GrandTour.uproject -run=pythonscript -script=Art/Unreal/setup_m0.py
      -EnablePlugins=PythonScriptPlugin -unattended -nopause -nosplash -NullRHI

- Creates SK_RangeRover_PhysicsAsset from the skeletal mesh (default generator), then removes
  the four Wheel_* bodies and their constraints so only the Root body remains. Chaos wheels are
  swept from the suspension and must not have bodies of their own.
- Creates /Game/GrandTour/Test/L_DriveTest: a 400 m floor, sun, sky, player start.
Safe to re-run: existing assets are reused or overwritten.
"""
import unreal

SK_PATH = "/Game/GrandTour/Vehicles/Bodies/RangeRover/SK_RangeRover"
LEVEL_PATH = "/Game/GrandTour/Test/L_DriveTest"


def log(msg):
    unreal.log("SETUP_M0 " + msg)


# ---- physics asset ---------------------------------------------------------------------------
sk = unreal.load_asset(SK_PATH)
if sk is None:
    raise SystemExit("missing " + SK_PATH + " (run Art/import_rangerover.bat first)")

pa = sk.get_editor_property("physics_asset")
if pa is None:
    pa = unreal.SkeletalMeshEditorSubsystem.create_physics_asset(sk, True, 0)
    log("created physics asset %s" % (pa.get_path_name() if pa else None))
else:
    log("physics asset already set: " + pa.get_path_name())
if pa is None:
    raise SystemExit("physics asset creation failed")

# Body setups are not reachable from Python; the game module exposes a helper (GTVehicleSetupLibrary).
removed = unreal.GTVehicleSetupLibrary.remove_bodies_by_bone_prefix(pa, "Wheel_")
log("removed %d wheel bodies" % removed)
lines = [str(line) for line in unreal.GTVehicleSetupLibrary.describe_bodies(pa)]
for line in lines:
    log("body " + line)
if not any(line.startswith("Root ") for line in lines):
    unreal.log_warning("SETUP_M0 no body on Root; the vehicle will have no collision")
unreal.EditorAssetLibrary.save_loaded_asset(pa)
unreal.EditorAssetLibrary.save_loaded_asset(sk)

# ---- test level ------------------------------------------------------------------------------
# The chassis body: replace the generated capsule with a box round the body (Unreal cm, from the
# import verification: X -229..232, Y +-93, Z 39..179). Wheels hang below and are swept by Chaos.
unreal.GTVehicleSetupLibrary.set_box_body(pa, sk, "Root", unreal.Vector(1.5, 0.0, 109.0),
                                          unreal.Vector(461.0, 186.0, 140.0))
for line in [str(l) for l in unreal.GTVehicleSetupLibrary.describe_bodies(pa)]:
    log("body after box " + line)
log("hit events enabled on %d bodies" % unreal.GTVehicleSetupLibrary.enable_hit_events(pa))
unreal.EditorAssetLibrary.save_loaded_asset(pa)

# ---- test level ------------------------------------------------------------------------------
# EditorActorSubsystem spawning crashes in a commandlet (no level-editor mode tools), so actors
# are spawned through plain UWorld spawning exposed by GTVehicleSetupLibrary.
les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
lib = unreal.GTVehicleSetupLibrary


def spawn(world, cls, location, rotation=unreal.Rotator(0, 0, 0), scale=unreal.Vector(1, 1, 1), label="", setup=None):
    transform = unreal.Transform(location, rotation, scale)
    actor = lib.spawn_actor_of_class(world, cls, transform, label)
    if actor is None:
        raise SystemExit("could not spawn " + str(cls))
    if setup:
        setup(actor)
    return actor


if unreal.EditorAssetLibrary.does_asset_exist(LEVEL_PATH):
    log("level exists, leaving it alone: " + LEVEL_PATH)
else:
    if not les.new_level(LEVEL_PATH):
        raise SystemExit("could not create level " + LEVEL_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cube = unreal.load_asset("/Engine/BasicShapes/Cube")
    # 400 m x 400 m, 1 m thick, top face at z = 0
    floor = lib.spawn_static_mesh_actor(
        world, cube, unreal.Transform(unreal.Vector(0, 0, -50), unreal.Rotator(0, 0, 0), unreal.Vector(400, 400, 1)),
        "Floor")
    if floor is None:
        raise SystemExit("could not spawn the floor")
    spawn(world, unreal.DirectionalLight, unreal.Vector(0, 0, 1000), unreal.Rotator(-45, 30, 0), label="Sun",
          setup=lambda a: a.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(8.0))
    spawn(world, unreal.SkyLight, unreal.Vector(0, 0, 1000), label="SkyLight",
          setup=lambda a: a.get_component_by_class(unreal.SkyLightComponent).set_editor_property("real_time_capture", True))
    spawn(world, unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), label="SkyAtmosphere")
    spawn(world, unreal.ExponentialHeightFog, unreal.Vector(0, 0, 0), label="HeightFog")
    spawn(world, unreal.PlayerStart, unreal.Vector(0, 0, 120), label="PlayerStart")
    if not les.save_current_level():
        raise SystemExit("could not save level")
    log("created level " + LEVEL_PATH)

log("DONE")
