"""Read-only export of the accepted Landscape, with checks against its terrain spec."""
import unreal as u
import json, struct, time, traceback
from pathlib import Path

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/MackenzieGaea/first-pass'
OUT.mkdir(parents=True, exist_ok=True)
LEVEL = '/Game/GrandTour/Demo/MackenzieBlockout/L_Mackenzie_Blockout'
report = {'ok': False, 'source_level': LEVEL, 'width': 1009, 'height': 1009}
u.EditorPythonScripting.set_keep_python_script_alive(True)
phase = 'load'
started = time.monotonic()

def finish(error=None):
    report['ok'] = error is None
    if error: report['error'] = error
    (OUT / 'landscape-export.json').write_text(json.dumps(report, indent=2))
    u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.quit_editor()

def tick(dt):
    global phase, loaded, world, landscape, rt
    try:
        if time.monotonic() - started > 180:
            raise RuntimeError('Landscape export timed out')
        if phase == 'load':
            assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level(LEVEL)
            world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
            actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
            landscapes = [a for a in actors if isinstance(a, u.Landscape)]
            assert len(landscapes) == 1
            landscape = landscapes[0]
            report['location_cm'] = list(landscape.get_actor_location().to_tuple())
            report['scale'] = list(landscape.get_actor_scale3d().to_tuple())
            loaded = time.monotonic()
            phase = 'warm'
        elif phase == 'warm' and time.monotonic() - loaded > 12:
            rt = u.RenderingLibrary.create_render_target2d(world, 1009, 1009, u.TextureRenderTargetFormat.RTF_RGBA8)
            assert landscape.landscape_export_heightmap_to_render_target(rt, True, True)
            loaded = time.monotonic()
            phase = 'read'
        elif phase == 'read' and time.monotonic() - loaded > 12:
            # The first use may compile the export material asynchronously.
            assert landscape.landscape_export_heightmap_to_render_target(rt, True, True)
            colors = u.RenderingLibrary.read_render_target(world, rt, False)
            assert len(colors) == 1009 * 1009, str(type(colors))
            values = [(int(c.r) << 8) | int(c.g) for c in colors]
            report['encoded_range'] = [min(values), max(values)]
            report['pixel_samples'] = [list(colors[i].to_tuple()) for i in [0, 504*1009+504, len(colors)-1]]
            assert max(values) > min(values) > 0
            spec = u.load_asset('/Game/GrandTour/Demo/MackenzieBlockout/DA_Mackenzie_Blockout').spec
            errors = []
            anchors = []
            # Asymmetric points and outer corners catch flipping, transposition,
            # missing border pixels and incorrect gamma/channel decoding.
            for iy in [0, 1, 126, 251, 504, 731, 882, 1007, 1008]:
                for ix in [0, 1, 126, 257, 504, 743, 882, 1007, 1008]:
                    x = -50000 + ix * 100000 / 1008
                    y = -50000 + iy * 100000 / 1008
                    expected = u.GTVehicleSetupLibrary.sample_terrain_height_cm(spec, x, y) / 100
                    actual = (values[iy * 1009 + ix] - 32768) / 128
                    errors.append(abs(actual - expected))
                    anchors.append({'pixel': [ix, iy], 'xyz_m': [x/100, y/100, actual], 'spec_z_m': expected})
            report['max_error_m'] = max(errors)
            report['anchors'] = anchors
            assert max(errors) < .025, 'Export differs from accepted terrain: ' + str(max(errors))
            (OUT / 'H_Mackenzie_UE_original.r16').write_bytes(struct.pack('<' + 'H' * len(values), *values))
            report['min_height_m'] = (min(values) - 32768) / 128
            report['max_height_m'] = (max(values) - 32768) / 128
            report['sample_spacing_m'] = 1000 / 1008
            report['row_order'] = 'Row 0: UE Y=-500m; column 0: UE X=-500m. No flip.'
            finish()
    except Exception:
        finish(traceback.format_exc())

handle = u.register_slate_post_tick_callback(tick)
