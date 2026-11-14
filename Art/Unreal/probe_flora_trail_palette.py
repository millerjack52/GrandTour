"""Reversible PIE diagnosis. Never save the scene or overwrite calibrated materials.

Each case starts from the saved baseline. All probes retain Standard display,
exposure, fog, source texture bindings, source coverage and native shadows.
"""
import json
import sys
import time
import traceback
from pathlib import Path
import unreal as u

R = Path('C:/GrandTour')
sys.path[:0] = [str(R / 'Art/Unreal'), str(R / 'Art')]
from benmore_river_life_materials import Graph, props
from flora_trail_asset_audit import verify, await_bark_textures
from flora_trail_palette_baseline import verify as verify_protected
from flora_trail_source34 import configure, settings

D = '/Game/GrandTour/ArtTests/FloraTrail'
O = R / 'Art/Export/FloraTrail/PaletteCandidate'
CFG = json.loads((R / 'Art/flora_trail_palette_probe_settings.json').read_text())
M = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
report = {'ok': False, 'stage': 'diagnose', 'cases': [], 'images': [],
          'requested_size': CFG['requested_size'], 'views': CFG['views'],
          'view_status': CFG['view_status'], 'performance_verified': False,
          'candidate_installed': False, 'motion_checked': False}
state = {'busy': False, 'due': 0, 'frame': 0}
world = pc = car = camera = None


def save():
    (O / 'diagnose-report.json').write_text(json.dumps(report, indent=2) + '\n')


def cmd(command):
    u.SystemLibrary.execute_console_command(world, command, pc)


def frames(count):
    end = state['frame'] + count
    while state['frame'] < end:
        yield 0


def shot(name):
    yield from frames(CFG['settle_frames'])
    path = O / (name + '.png')
    stamp = time.time()
    cmd('Shot filename="' + path.as_posix() + '" -nosuffix')
    deadline = time.monotonic() + 45
    while not path.exists() or path.stat().st_mtime < stamp:
        assert time.monotonic() < deadline, name
        yield .2
    # PNG IHDR records native backbuffer dimensions; requested window size is not evidence.
    header = path.read_bytes()[:24]
    assert header[:8] == b'\x89PNG\r\n\x1a\n'
    report['images'].append({'name': name, 'native_size': [int.from_bytes(header[16:20], 'big'),
                                                          int.from_bytes(header[20:24], 'big')]})
    save()


def probe_material(key):
    source = D + '/Materials/Source34/M_Source34_' + key
    path = D + '/Materials/PaletteDiagnostic/M_NormalPigment_' + key
    material = u.load_asset(path) or E.duplicate_asset(source, path)
    assert material
    # Only local probe nodes are rebuilt. Coverage, texture UVs and all source nodes survive.
    for node in list(M.get_material_expressions(material)):
        if str(node.get_editor_property('desc')) == 'PaletteDiagnostic':
            M.delete_material_expression(material, node)
    nodes = M.get_material_expressions(material)
    pigment = next(n for n in nodes if isinstance(n, u.MaterialExpressionTextureSampleParameter2D)
                   and str(n.get_editor_property('parameter_name')) == 'SourcePigment')
    g = Graph(material, 'PaletteDiagnostic')
    tint = g.node(u.MaterialExpressionVectorParameter, parameter_name='ProbePigment',
                  default_value=u.LinearColor(1, 1, 1, 1))
    colour = g.custom(['C', 'Tint'], 'return C*Tint;')
    g.wire(pigment, colour, 'C', 'RGB'); g.wire(tint, colour, 'Tint')
    g.output(colour, u.MaterialProperty.MP_BASE_COLOR)
    blend = g.node(u.MaterialExpressionScalarParameter, parameter_name='ProbeNormalBlend', default_value=0.)
    normal = g.node(u.MaterialExpressionVertexNormalWS)
    shaped = g.custom(['N', 'Blend'],
        'float3 upN=normalize(float3(N.xy,abs(N.z)+.001));return normalize(lerp(float3(0,0,1),upN,saturate(Blend)));')
    g.wire(normal, shaped, 'N'); g.wire(blend, shaped, 'Blend')
    g.output(shaped, u.MaterialProperty.MP_NORMAL)
    assert not M.recompile_material(material)
    assert E.save_loaded_asset(material, False)
    return material


def run():
    global world, pc, car, camera
    protected = verify_protected()
    report['protected_file_count'] = len(protected['protected_hashes'])
    report['baseline_backup'] = protected['backup']
    L = u.get_editor_subsystem(u.LevelEditorSubsystem)
    assert L.load_level(D + '/L_FloraTrail')
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    for command in json.loads((R / 'Art/flora_trail_settings.json').read_text())['console']:
        cmd(command)
    yield 8
    yield from await_bark_textures()
    report['source_assets'] = verify(world)
    # Editor graph inspection belongs before PIE; it is not a runtime material API.
    for key in ('tree', 'pine'):
        source = u.load_asset(D + '/Materials/Source34/M_Source34_' + key)
        assert M.get_material_property_input_node(source, u.MaterialProperty.MP_WORLD_POSITION_OFFSET) is None
    report['wind'] = 'Frozen source tree foliage; no connected world-position-offset output.'
    probes = {key: probe_material(key) for key in ('tree', 'pine')}
    # Audit new graphs in editor context, before PIE (including 4K bark and 3 LODs).
    report['probe_textures'] = {}
    for key, material in probes.items():
        report['probe_textures'][key] = {str(n.get_editor_property('parameter_name')):
            n.get_editor_property('texture').get_path_name() for n in M.get_material_expressions(material)
            if isinstance(n, u.MaterialExpressionTextureSampleParameter2D)}
    # Existing calibrated card; do not mutate or recompile shared diagnostic assets.
    grey = u.load_asset('/Game/GrandTour/ArtTests/FloraTrailReview/M_DisplayCheck')
    assert grey, 'Run the established saved-source verification to create the display card first'
    yield 8
    u.GTPlayWindowLibrary.request_play_in_new_window(*CFG['requested_size'])
    yield 12
    world = u.EditorLevelLibrary.get_game_world()
    pc = u.GameplayStatics.get_player_controller(world, 0)
    car = pc.get_car(); assert car
    car.disable_input(pc); car.get_chaos_movement().set_handbrake_input(True)
    for command in ['DisableAllScreenMessages', 'r.MotionBlurQuality 0', 'r.ScreenPercentage 100',
                    'r.DynamicRes.OperationMode 0', 'r.VSync 0', 't.MaxFPS 0',
                    'r.Streaming.FullyLoadUsedTextures 1']:
        cmd(command)
    slots = []
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Actor):
        for component in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            mesh = component.static_mesh
            if not component.get_instance_count() or not mesh or mesh.get_name() not in ('SM_Exact_tree', 'SM_Exact_pine'):
                continue
            if not mesh.get_path_name().startswith(D + '/Meshes/'):
                continue
            key = mesh.get_name().removeprefix('SM_Exact_')
            for index, material in enumerate(component.get_materials()):
                if material.blend_mode == u.BlendMode.BLEND_MASKED:
                    assert material.get_path_name().startswith(D + '/Materials/Source34/')
                    slots.append((component, index, material, key))
    assert len(slots) == 4
    camera = u.GTVehicleSetupLibrary.spawn_actor_of_class(world, u.CameraActor,
        u.Transform(location=u.Vector()), 'FloraTrail_PaletteDiagnosticCamera')
    camera.camera_component.set_field_of_view(CFG['fov'])
    camera.camera_component.set_editor_property('constrain_aspect_ratio', False)
    pc.set_view_target_with_blend(camera, 0); cmd('ShowHUD')
    yield 12  # Fully-load-used-textures request + temporal settling before first comparison.
    original_light = settings()
    for case in CFG['cases']:
        for component, index, material, key in slots:
            component.set_material(index, material)
        light = dict(original_light)
        for key in ('sun_colour', 'sky_colour'):
            if key in case: light[key] = case[key]
        if case.get('reverse_azimuth'):
            x, y, z = light['sun_ray']; light['sun_ray'] = [-x, -y, z]
        lighting = configure(world, light)
        if 'pigment' in case or 'normal_blend' in case:
            for component, index, material, key in slots:
                mid = component.create_dynamic_material_instance(index, probes[key])
                mid.set_vector_parameter_value('ProbePigment', u.LinearColor(*case.get('pigment', [1, 1, 1]), 1))
                mid.set_scalar_parameter_value('ProbeNormalBlend', case.get('normal_blend', 0.))
        report['cases'].append({'case': case, 'lighting': lighting})
        for view in CFG['views']:
            if view['name'] not in case['views']: continue
            pos, target = u.Vector(*view['position']), u.Vector(*view['target'])
            camera.set_actor_location(pos, False, True)
            camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos, target), False)
            yield from shot(case['name'] + '_' + view['name'])
    # Test actual display transfer separately from material/light probes. No tonemapper
    # toggle is used to disguise uniform normals; the neutral card is actual game output.
    configure(world, original_light)
    for component, index, material, key in slots: component.set_material(index, material)
    view = CFG['views'][0]; pos = u.Vector(*view['position'])
    camera.set_actor_location(pos, False, True)
    camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pos, u.Vector(*view['target'])), False)
    cube = u.GTVehicleSetupLibrary.spawn_actor_of_class(world, u.StaticMeshActor,
        u.Transform(location=pos + camera.get_actor_forward_vector()*300), 'PaletteDisplayCheck')
    cube.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
    assert cube.static_mesh_component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube'))
    cube.set_actor_scale3d(u.Vector(.5, .5, .5)); cube.static_mesh_component.set_material(0, grey)
    yield from shot('display_check'); cube.destroy_actor()
    verify_protected()
    report.update(ok=True, protected_unchanged=True, saved_scene_unchanged=True)
    save()
    pc.set_view_target_with_blend(car, 0)
    yield 2
    u.EditorLevelLibrary.editor_end_play(); yield 4
    world = pc = car = camera = None
    L.load_level('/Engine/Maps/Entry'); yield 3


def close():
    # Match the established FloraTrail shutdown workaround: release Python UObject
    # proxies before requesting exit, then release keepalive before QuitEditor.
    for key, value in list(globals().items()):
        if not key.startswith('__') and key not in ('u', 'time'):
            globals()[key] = None
    value = None
    import gc
    gc.collect(); u.SystemLibrary.collect_garbage()
    globals()['quit_at'] = time.monotonic() + 3
    def shutdown(dt):
        if time.monotonic() > quit_at:
            u.unregister_slate_post_tick_callback(quit_handle)
            u.EditorPythonScripting.set_keep_python_script_alive(False)
            u.SystemLibrary.quit_editor()
    globals()['quit_handle'] = u.register_slate_post_tick_callback(shutdown)


steps = run()


def tick(dt):
    global steps
    if state['busy']: return
    state['busy'] = True; state['frame'] += 1
    try:
        if time.monotonic() >= state['due']:
            state['due'] = time.monotonic() + next(steps)
    except StopIteration:
        steps = None; u.unregister_slate_post_tick_callback(handle); close()
    except Exception:
        report['error'] = traceback.format_exc(); save(); u.log_error(report['error'])
        u.unregister_slate_post_tick_callback(handle); close()
    finally:
        if state is not None: state['busy'] = False


u.EditorPythonScripting.set_keep_python_script_alive(True)
handle = u.register_slate_post_tick_callback(tick)
