"""Check the saved Prado static assembly and capture four actual PIE views.

Run inside the full Unreal editor after import_prado.py has saved the level.
This script changes only the active review view/PIE session, not saved assets.
"""
import json
import struct
import time
import traceback
from pathlib import Path

import unreal as u


OUT = Path('C:/GrandTour/Art/Export/VehicleTools/prado-unreal-v01')
MANIFEST = OUT / 'Prado' / 'manifest.json'
MAP = '/Game/GrandTour/ArtTests/Prado/L_PradoReview'
SHOTS = [
    ('NC_Camera_Prado_Front', 'UE_Prado_Front.png'),
    ('NC_Camera_Prado_Rear', 'UE_Prado_Rear.png'),
    ('NC_Camera_Prado_FrontClose', 'UE_Prado_FrontClose.png'),
    ('NC_Camera_Prado_Cockpit', 'UE_Prado_Cockpit.png'),
    ('NC_Camera_Prado_CabinForward', 'UE_Prado_CabinForward.png'),
]
REAR_LENSES = {
    'M_Prado_Prado_rear_amber_lens',
    'M_Prado_Prado_rear_red_lens',
    'M_Prado_Prado_reverse_lens',
}

OUT.mkdir(parents=True, exist_ok=True)
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase = 'load'
index = 0
last = time.monotonic()
started = last
finished = False
report = {
    'ok': False,
    'map': MAP,
    'manifest': str(MANIFEST),
    'images': [],
    'captures': [],
    'scope': 'Saved static assembly and actual PIE renders; no Prado driving rig.',
    'visual_review': 'Pending human/agent inspection of the completed images.',
}


def finish(error=None):
    global finished
    if finished:
        return
    finished = True
    report['elapsed_seconds'] = round(time.monotonic() - started, 2)
    if error:
        report['error'] = error
        report['failed_phase'] = phase
    (OUT / 'render-check.json').write_text(json.dumps(report, indent=2))
    u.unregister_slate_post_tick_callback(handle)
    try:
        u.EditorLevelLibrary.editor_end_play()
    finally:
        u.SystemLibrary.quit_editor()


def verify_assembly():
    manifest = json.loads(MANIFEST.read_text())
    parts = manifest['parts']
    expected = {part['name']: part for part in parts}
    assert len(expected) == len(parts), 'Duplicate manifest part names'
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    car = next(a for a in actors if a.get_actor_label() == 'NC_Prado')
    components = car.get_components_by_class(u.StaticMeshComponent)
    names = [c.static_mesh.get_name() if c.static_mesh else None for c in components]
    assert len(components) == len(parts), (len(components), len(parts))
    assert sorted(names) == sorted(expected), (names, list(expected))
    report['components'] = len(components)
    report['expected_components'] = len(parts)
    report['source_sha256'] = manifest.get('source_sha256')
    by_name = {c.static_mesh.get_name(): c for c in components}

    glass_parts = [p for p in parts if p['group'] == 'Glass']
    assert {p['name'] for p in glass_parts} == {'SM_Prado_Glass'}
    glazing = []
    for part in glass_parts:
        component = by_name[part['name']]
        assert not component.get_editor_property('cast_shadow'), 'Glass casts shadows'
        slots = component.get_num_materials()
        assert slots == len(part['materials']), (part['name'], slots)
        for slot, expected_name in enumerate(part['materials']):
            material = component.get_material(slot)
            assert material and material.get_name() == expected_name
            blend = material.get_editor_property('blend_mode')
            assert blend == u.BlendMode.BLEND_TRANSLUCENT, (expected_name, blend)
            glazing.append({
                'mesh': part['name'], 'slot': slot,
                'material': material.get_path_name(), 'blend_mode': str(blend),
                'cast_shadow': False,
                'lighting': str(material.get_editor_property('translucency_lighting_mode')),
            })
    report['glazing'] = glazing

    # A Blender lens transmission value of .08 does not classify it as glazing.
    # Inspect the material assigned to each actual imported rear-light slot.
    rear_parts = [p for p in parts if p['group'] == 'RearLighting']
    assert rear_parts, 'Manifest has no RearLighting part'
    seen = set()
    rear_materials = []
    for part in rear_parts:
        component = by_name[part['name']]
        assert component.get_num_materials() == len(part['materials'])
        for slot, expected_name in enumerate(part['materials']):
            material = component.get_material(slot)
            assert material and material.get_name() == expected_name
            if expected_name not in REAR_LENSES:
                continue
            blend = material.get_editor_property('blend_mode')
            assert blend == u.BlendMode.BLEND_OPAQUE, (expected_name, blend)
            seen.add(expected_name)
            source = manifest['materials'][expected_name]
            rear_materials.append({
                'mesh': part['name'], 'slot': slot,
                'material': material.get_path_name(), 'blend_mode': str(blend),
                'source_base_color': source.get('base_color'),
                'source_transmission': source.get('transmission'),
            })
    assert seen == REAR_LENSES, ('Missing rear lens materials', sorted(REAR_LENSES - seen))
    report['rear_lenses'] = rear_materials
    available = {a.get_actor_label() for a in actors if isinstance(a, u.CameraActor)}
    assert all(label in available for label, _ in SHOTS), ('Missing review cameras', available)


def fresh_png(path, requested_at):
    if not path.exists():
        return None
    stat = path.stat()
    if stat.st_mtime < requested_at or stat.st_size < 24:
        return None
    with path.open('rb') as stream:
        header = stream.read(24)
    if header[:8] != b'\x89PNG\r\n\x1a\n' or header[12:16] != b'IHDR':
        return None
    width, height = struct.unpack('>II', header[16:24])
    assert (width, height) == (1440, 900), ('Unexpected screenshot dimensions', width, height)
    # IEND is written after the complete image stream, avoiding a partial-file pass.
    with path.open('rb') as stream:
        stream.seek(-12, 2)
        end = stream.read(12)
    if end[4:8] != b'IEND':
        return None
    return {'width': width, 'height': height, 'bytes': stat.st_size}


def tick(dt):
    global phase, last, index, world, pc, shot_started
    if finished:
        return
    now = time.monotonic()
    try:
        if now - started > 420:
            finish('Overall capture timeout (420 seconds)')
            return
        if phase == 'load':
            phase = 'loading'
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(MAP)
            verify_assembly()
            phase = 'loaded'
            last = time.monotonic()
        elif phase == 'loaded' and now - last > 8:
            phase = 'playing'
            last = now
            u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play()
        elif phase == 'playing' and now - last > 18:
            world = u.EditorLevelLibrary.get_game_world()
            if not world:
                if now - last > 90:
                    finish('PIE game world unavailable after 90 seconds')
                return
            pc = u.GameplayStatics.get_player_controller(world, 0)
            assert pc, 'PIE player controller unavailable'
            phase = 'camera_setup'
        elif phase == 'camera_setup':
            cameras = u.GameplayStatics.get_all_actors_of_class(world, u.CameraActor)
            label, filename = SHOTS[index]
            camera = next(a for a in cameras if a.get_actor_label() == label)
            pc.set_view_target_with_blend(camera, 0)
            location, rotation = camera.get_actor_location(), camera.get_actor_rotation()
            report['captures'].append({
                'camera': label, 'file': str(OUT / filename),
                'location_cm': [location.x, location.y, location.z],
                'rotation_degrees': [rotation.pitch, rotation.yaw, rotation.roll],
                'status': 'pending',
            })
            phase = 'camera_ready'
            last = time.monotonic()
        elif phase == 'camera_ready' and now - last > 4:
            filename = OUT / SHOTS[index][1]
            shot_started = time.time()
            u.SystemLibrary.execute_console_command(
                world, 'HighResShot 1440x900 filename="' + filename.as_posix() + '"', pc
            )
            phase = 'shot'
            last = time.monotonic()
        elif phase == 'shot' and now - last > 8:
            output = OUT / SHOTS[index][1]
            metadata = fresh_png(output, shot_started)
            if metadata is None:
                if now - last > 75:
                    finish('Screenshot was not completed within 75 seconds: ' + str(output))
                return
            report['images'].append(str(output))
            report['captures'][-1].update(metadata, status='captured')
            index += 1
            if index == len(SHOTS):
                report['ok'] = True
                finish()
                return
            phase = 'camera_setup'
            last = now
    except Exception:
        finish(traceback.format_exc())


handle = u.register_slate_post_tick_callback(tick)
