"""Open the dedicated map; use the fitted cockpit for the finished revision."""
import unreal as u

MAP = '/Game/GrandTour/Test/GraphicAdventure/L_GraphicAdventure_Test'
u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
u.EditorPythonScripting.set_keep_python_script_alive(True)
seen = None

def tick(dt):
    global seen
    worlds = u.EditorLevelLibrary.get_pie_worlds(False)
    if not worlds:
        seen = None
        return
    world = worlds[0]
    car = u.GameplayStatics.get_player_pawn(world, 0)
    if car and car != seen and car.get_class().get_name() == 'BP_GraphicAdventure_C':
        mesh = car.get_component_by_class(u.SkeletalMeshComponent).get_editor_property('skeletal_mesh_asset')
        car.set_chase_camera('/Finished/' not in mesh.get_path_name())
        seen = car

handle = u.register_slate_post_tick_callback(tick)
u.log('GRAPHIC_ADVENTURE_TEST_READY: press Play; W/S pedals, A/D steering, Space handbrake, C camera.')
