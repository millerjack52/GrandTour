"""Benmore optimisation BO1 (docs/BENMORE_OPTIMISATION_PLAN.md section 3 BO1).

Inside the editor (launched by Art/benmore_bo1.ps1):
  apply mode (default):
  - copies L_Benmore_GaeaReview.umap to Art/Export/BenmoreGaea/BO1 (plain file copy, SHA-256 recorded),
  - sets visible_in_ray_tracing False and affect_dynamic_indirect_lighting False on the authored
    SM_TS_* / SM_Composition_Scrub_* ISM components that still had ray-tracing visibility,
  - measures (below), saves the map, reloads and verifies.
  measure mode (env GT_BO1_MODE=measure, launcher -Measure): the map already carries the BO1 flags;
  verifies them and the instance signature, measures, and does NOT save.
  Measurement: a transient SceneCapture2D at the camera is rendered every tick (the off-screen editor
  viewport never draws: UEditorEngine::Tick skips drawing while all windows are hidden). Lumen
  r.LumenScene.DumpStats at MeshCardsMinSize 150 / 10 / 150, a settled capture picture
  (<Camera>_BO1_settled.png) and the high-res editor screenshot (<Camera>_BO1.png, a single viewport
  render) at Ford and Creek_Close.
Outside Unreal (`python apply_benmore_bo1.py --parse-log`, run by the launcher after the editor exits):
  - parses the three DumpStats blocks from Saved/Logs/BenmoreBO1.log into the report.
No timings are collected here. Rollback: copy the backup umap back over the map.
"""
import json, os, sys, time, traceback, array, hashlib, shutil, re, datetime
from pathlib import Path

try:
    import unreal as u
    IN_UNREAL = True
except ImportError:
    IN_UNREAL = False

LEVEL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
PREFIXES = ('SM_TS_', 'SM_Composition_Scrub_')
EXPECTED = {  # 2026-10-10 runtime inventory: mesh -> (instances, end cull cm)
    'SM_TS_Rust': (1200, 33000), 'SM_TS_Straw': (1200, 33000),
    'SM_Composition_Scrub_Dense': (120, 33000), 'SM_Composition_Scrub_Open': (120, 33000)}
CVAR = 'r.LumenScene.SurfaceCache.MeshCardsMinSize'
SETTLE = 40.0
AFTER_DUMP = 5.0
DUMPS = ['first_150', 'at_10', 'at_150_again']
CAMERAS = [('Ford', 'Benmore_RL_Camera_Ford'), ('Creek_Close', 'Benmore_Gaea_Camera_Creek_Close')]
RES = (1440, 900)


def project_root():
    if IN_UNREAL:
        return Path(u.Paths.project_dir()).resolve()
    return Path(__file__).resolve().parents[2]


ROOT = project_root()
OUT = ROOT / 'Art/Export/BenmoreGaea/BO1'
REPORT = OUT / 'bo1-report.json'
LOG = ROOT / 'Saved/Logs/BenmoreBO1.log'
MAP_FILE = ROOT / 'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- log parse (outside Unreal)
def parse_dump(lines, start, stop):
    """Parse the first '*** LumenScene Stats ***' block in lines[start:stop] (stop = next marker)."""
    begin = next((i for i in range(start, stop) if '*** LumenScene Stats ***' in lines[i]), None)
    if begin is None:
        return None
    sections = {}
    section = 'scene'
    raw = []
    for line in lines[begin + 1:begin + 80]:
        m = re.search(r'LogRenderer:\s+(.*)$', line)
        if not m:
            continue
        text = m.group(1).strip()
        if text.startswith('***'):
            name = text.strip('* ').lower()
            if 'bin allocator' in name or 'cpu memory' in name or 'gpu memory' in name or 'primitiveculling' in name:
                break
            section = {'surface cache': 'surface_cache', 'far field': 'far_field'}.get(name, name)
            continue
        raw.append(text)
        if ': ' in text:
            key, value = text.split(': ', 1)
            sections.setdefault(section, {})[key.strip()] = value.strip()
        else:
            sections.setdefault(section, {})[text.split(' ')[0]] = text

    def num(sec, key):
        v = sections.get(sec, {}).get(key)
        if v is None:
            return None
        m = re.match(r'[-0-9.]+', v)
        return float(m.group(0)) if m and '.' in m.group(0) else (int(m.group(0)) if m else v)

    alloc = sections.get('surface_cache', {}).get('Allocated', '')
    m = re.match(r'Allocated (\d+) physical pages out of (\d+)', alloc)
    return {
        'log_line': begin + 1,
        'primitive_groups': num('scene', 'Primitive groups'),
        'mesh_cards': num('scene', 'Mesh cards'),
        'cards': num('scene', 'Cards'),
        'mesh_sdf_objects': num('scene', 'Mesh SDF Objects'),
        'allocated_physical_pages': int(m.group(1)) if m else None,
        'physical_pages_total': int(m.group(2)) if m else None,
        'bin_pages_line': sections.get('surface_cache', {}).get('Bin pages'),
        'virtual_texels': sections.get('surface_cache', {}).get('Virtual texels'),
        'physical_texels': sections.get('surface_cache', {}).get('Physical texels'),
        'mesh_cards_to_add': num('surface_cache', 'Mesh cards to add'),
        'locked_cards_to_update': num('surface_cache', 'Locked cards to update'),
        'far_field': {k: sections.get('far_field', {}).get(k) for k in ('Primitive groups', 'Mesh cards', 'Cards')} if 'far_field' in sections else None,
        'raw': raw,
    }


def opaque_png(path):
    """Set alpha to 255 in an 8-bit RGBA, non-interlaced PNG (scene-capture exports carry alpha 0). Stdlib only."""
    import struct, zlib
    data = Path(path).read_bytes()
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        return 'not a png'
    pos, chunks, idat = 8, [], b''
    while pos < len(data):
        n, kind = struct.unpack('>I4s', data[pos:pos + 8]); body = data[pos + 8:pos + 8 + n]; pos += 12 + n
        if kind == b'IDAT': idat += body
        else: chunks.append((kind, body))
    w, h, depth, ctype, _, _, interlace = struct.unpack('>IIBBBBB', chunks[0][1])
    if (depth, ctype, interlace) != (8, 6, 0):
        return 'skipped (depth %d, colour type %d, interlace %d)' % (depth, ctype, interlace)
    raw = zlib.decompress(idat); stride = w * 4; out = bytearray(); prev = bytearray(stride); alpha0 = 0
    for y in range(h):
        f = raw[y * (stride + 1)]; row = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if f == 1:
            for i in range(4, stride): row[i] = (row[i] + row[i - 4]) & 255
        elif f == 2:
            for i in range(stride): row[i] = (row[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride): row[i] = (row[i] + (((row[i - 4] if i >= 4 else 0) + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = row[i - 4] if i >= 4 else 0; b = prev[i]; c = prev[i - 4] if i >= 4 else 0
                p = a + b - c; pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                row[i] = (row[i] + (a if pa <= pb and pa <= pc else (b if pb <= pc else c))) & 255
        prev = row
        alpha0 += row[3::4].count(0)
        fixed = bytearray(row); fixed[3::4] = b'\xff' * w
        out += b'\x00' + fixed
    def chunk(kind, body):
        return struct.pack('>I', len(body)) + kind + body + struct.pack('>I', zlib.crc32(kind + body) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', chunks[0][1])
    png += b''.join(chunk(k, b) for k, b in chunks[1:] if k not in (b'IEND',))
    png += chunk(b'IDAT', zlib.compress(bytes(out), 6)) + chunk(b'IEND', b'')
    Path(path).write_bytes(png)
    return 'alpha set opaque (%d of %d pixels had alpha 0)' % (alpha0, w * h)


def parse_log():
    report = json.loads(REPORT.read_text())
    for img in report.get('images', []):
        if img.get('path') and img['path'].endswith('_settled.png') and Path(img['path']).exists() and not img.get('alpha_fix'):
            img['alpha_fix'] = opaque_png(img['path'])
    lines = LOG.read_text(encoding='utf-8', errors='replace').splitlines()
    markers = [i for i, l in enumerate(lines) if 'BO1_DUMP_BEGIN ' in l]
    stats, missing = {}, []
    for name in DUMPS:
        marker = next((i for i in markers if lines[i].rstrip().endswith('BO1_DUMP_BEGIN ' + name)), None)
        block = None
        if marker is not None:
            stop = next((i for i in markers if i > marker), len(lines))
            block = parse_dump(lines, marker, stop)
        if block is None:
            missing.append(name)
        stats[name] = block
    report['lumen_stats'] = stats
    report['lumen_stats_source'] = str(LOG)
    if missing:
        report['ok'] = False
        report['error'] = (report.get('error') or '') + ' Lumen DumpStats block missing in log for: ' + ', '.join(missing)
    REPORT.write_text(json.dumps(report, indent=2))
    print('lumen_stats parsed; missing=%s' % missing)
    return 0 if not missing else 2


if not IN_UNREAL:
    if '--parse-log' in sys.argv:
        sys.exit(parse_log())
    sys.exit('Run inside Unreal via Art/benmore_bo1.ps1, or with --parse-log after the run.')


# ---------------------------------------------------------------- editor run
MODE = os.environ.get('GT_BO1_MODE', 'apply').strip().lower()
OUT.mkdir(parents=True, exist_ok=True)
act = u.get_editor_subsystem(u.EditorActorSubsystem)
les = u.get_editor_subsystem(u.LevelEditorSubsystem)
ues = u.get_editor_subsystem(u.UnrealEditorSubsystem)
phase = 'start'
started = time.monotonic()
last = started
report = {'ok': False, 'stage': 'BO1', 'timings_collected': False, 'level': LEVEL, 'map_file': str(MAP_FILE),
          'changes': [], 'unexpected': [], 'images': [], 'cameras': {}, 'cvar_readback': {}, 'log': str(LOG)}
cameras = {}
capture = None
render_target = None
pending_shot = None
cam_index = 0
u.EditorPythonScripting.set_keep_python_script_alive(True)


def world():
    return ues.get_editor_world()


def console(cmd):
    u.SystemLibrary.execute_console_command(world(), cmd)
    u.log('BO1 console: ' + cmd)


def cvar():
    return u.SystemLibrary.get_console_variable_float_value(CVAR)


def ism_components():
    for a in sorted(act.get_all_level_actors(), key=lambda a: a.get_actor_label()):
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c, u.GrassInstancedStaticMeshComponent):
                continue
            yield a, c


def signature():
    # Identical to apply_benmore_render_budget.py: every non-grass ISM instance transform, hashed.
    h = hashlib.sha256(); count = 0
    for a in sorted(act.get_all_level_actors(), key=lambda a: a.get_actor_label()):
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            if isinstance(c, u.GrassInstancedStaticMeshComponent): continue
            for i in range(c.get_instance_count()):
                t = c.get_instance_transform(i, True); h.update(array.array('d', [*t.translation.to_tuple(), *t.rotation.to_tuple(), *t.scale3d.to_tuple()]).tobytes()); count += 1
    return {'instances': count, 'sha256': h.hexdigest()}


def mesh_of(c):
    m = c.get_editor_property('static_mesh')
    return (m.get_name(), m.get_path_name()) if m else (None, None)


def flags(c):
    return {'visible_in_ray_tracing': c.get_editor_property('visible_in_ray_tracing'),
            'affect_dynamic_indirect_lighting': c.get_editor_property('affect_dynamic_indirect_lighting')}


def rt_census():
    out = {}
    for a, c in ism_components():
        name, _ = mesh_of(c)
        row = out.setdefault(str(name), {'rt_false_components': 0, 'rt_true_components': 0, 'rt_false_instances': 0, 'rt_true_instances': 0})
        key = 'rt_true' if c.get_editor_property('visible_in_ray_tracing') else 'rt_false'
        row[key + '_components'] += 1; row[key + '_instances'] += c.get_instance_count()
    return out


def apply_changes():
    found = {}
    for a, c in ism_components():
        name, path = mesh_of(c)
        if not name or not name.startswith(PREFIXES) or not c.get_editor_property('visible_in_ray_tracing'):
            continue
        before = flags(c)
        c.set_editor_property('visible_in_ray_tracing', False)
        c.set_editor_property('affect_dynamic_indirect_lighting', False)
        row = {'actor': a.get_actor_label(), 'component': c.get_name(), 'class': c.get_class().get_name(), 'mesh': path,
               'instances': c.get_instance_count(),
               'cull_start_cm': c.get_editor_property('instance_start_cull_distance'),
               'cull_end_cm': c.get_editor_property('instance_end_cull_distance'),
               'flags_before': before, 'flags_after': flags(c)}
        report['changes'].append(row)
        found.setdefault(name, []).append(row)
    for mesh, (count, cull) in EXPECTED.items():
        rows = found.get(mesh, [])
        if len(rows) != 1:
            report['unexpected'].append('%s: expected 1 RT-visible component, found %d' % (mesh, len(rows)))
        for r in rows:
            if r['instances'] != count or r['cull_end_cm'] != cull:
                report['unexpected'].append('%s on %s: %d instances, end cull %s cm (expected %d, %d)' % (mesh, r['actor'], r['instances'], r['cull_end_cm'], count, cull))
    for mesh in found:
        if mesh not in EXPECTED:
            report['unexpected'].append('%s: %d RT-visible component(s) not in the expected set, changed anyway' % (mesh, len(found[mesh])))
    for r in report['changes']:
        if any(r['flags_after'].values()):
            raise RuntimeError('Flags did not change on %s.%s' % (r['actor'], r['component']))


def verify_flags(key):
    labels = {(r['actor'], r['component']) for r in report['changes']}
    seen = []
    for a, c in ism_components():
        if (a.get_actor_label(), c.get_name()) in labels:
            f = flags(c); seen.append({'actor': a.get_actor_label(), 'component': c.get_name(), **f})
            if any(f.values()):
                raise RuntimeError('%s: %s.%s still reads %s' % (key, a.get_actor_label(), c.get_name(), f))
    if len(seen) != len(labels) or not labels:
        raise RuntimeError('%s: found %d of %d changed components' % (key, len(seen), len(labels)))
    report[key] = seen


def find_cameras():
    labels = {a.get_actor_label(): a for a in act.get_all_level_actors()}
    for key, label in CAMERAS:
        cam = labels.get(label)
        report['cameras'][key] = {'label': label, 'found': cam is not None}
        if cam is not None:
            cameras[key] = cam
        else:
            report['unexpected'].append('Camera actor missing: ' + label)


def make_capture():
    """Transient SceneCapture2D (RF_Transient, never saved; destroyed before any save)."""
    global capture, render_target
    render_target = u.RenderingLibrary.create_render_target2d(world(), RES[0], RES[1], u.TextureRenderTargetFormat.RTF_RGBA8)
    first = next(iter(cameras.values()), None)
    loc = first.get_actor_location() if first else u.Vector(0, 0, 0)
    rot = first.get_actor_rotation() if first else u.Rotator(0, 0, 0)
    capture = act.spawn_actor_from_class(u.SceneCapture2D, loc, rot, True)
    if capture is None:
        raise RuntimeError('SceneCapture2D spawn failed')
    capture.set_actor_label('BO1_TransientCapture')
    comp = capture.get_editor_property('capture_component2d')
    comp.set_editor_property('texture_target', render_target)
    comp.set_editor_property('capture_source', u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property('capture_every_frame', False)
    comp.set_editor_property('capture_on_movement', False)
    comp.set_editor_property('always_persist_rendering_state', True)
    try:
        comp.set_editor_property('use_ray_tracing_if_enabled', True)
        report['capture_use_ray_tracing_if_enabled'] = True
    except Exception as e:
        report['unexpected'].append('capture use_ray_tracing_if_enabled: %s' % e)
    report['capture'] = {'actor': capture.get_actor_label(), 'transient': True, 'resolution': list(RES),
                         'source': 'SCS_FINAL_COLOR_LDR', 'note': 'rendered with capture_scene() every editor tick (~15 fps)'}


def place(key):
    cam = cameras.get(key)
    if cam is None:
        return False
    ues.set_level_viewport_camera_info(cam.get_actor_location(), cam.get_actor_rotation())
    if capture is not None:
        capture.set_actor_location_and_rotation(cam.get_actor_location(), cam.get_actor_rotation(), False, True)
        try:
            fov = cam.get_editor_property('camera_component').get_editor_property('field_of_view')
            capture.get_editor_property('capture_component2d').set_editor_property('fov_angle', fov)
            report['cameras'][key]['fov'] = fov
        except Exception as e:
            report['unexpected'].append('capture fov for %s: %s' % (key, e))
    return True


def render():
    if capture is not None:
        capture.get_editor_property('capture_component2d').capture_scene()


def export_settled(key):
    if capture is None or key not in cameras:
        return
    name = '%s_BO1_settled.png' % key
    path = OUT / name
    if path.exists(): path.unlink()
    u.RenderingLibrary.export_render_target(world(), render_target, str(OUT), name)
    report['images'].append({'camera': key, 'kind': 'scene capture after settle (40 s of capture renders)', 'path': str(path),
                             'exists': path.exists(), 'cvar': cvar()})
    if not path.exists():
        report['unexpected'].append('Settled capture not written: ' + str(path))


def shoot(key):
    global pending_shot
    cam = cameras.get(key)
    if cam is None:
        report['images'].append({'camera': key, 'path': None, 'note': 'camera actor missing'}); pending_shot = None; return
    path = OUT / ('%s_BO1.png' % key)
    if path.exists(): path.unlink()
    u.AutomationLibrary.take_high_res_screenshot(RES[0], RES[1], str(path), cam)
    pending_shot = {'camera': key, 'kind': 'take_high_res_screenshot (single editor viewport render)', 'path': str(path), 'cvar': cvar()}


def shot_done(now):
    """True once the pending screenshot exists (or 30 s passed; then recorded as missing)."""
    global pending_shot
    if pending_shot is None:
        return True
    p = Path(pending_shot['path'])
    if p.exists() and now - last > 5:
        pending_shot['exists'] = True; report['images'].append(pending_shot); pending_shot = None; return True
    if now - last > 30:
        pending_shot['exists'] = False; report['images'].append(pending_shot)
        report['unexpected'].append('Screenshot not written: ' + pending_shot['path']); pending_shot = None; return True
    return False


def dump(name):
    u.log('BO1_DUMP_BEGIN ' + name)
    report['cvar_readback'][name] = cvar()
    console('r.LumenScene.DumpStats 1')


def destroy_capture():
    global capture
    if capture is not None:
        act.destroy_actor(capture); capture = None
        report['capture_destroyed'] = True


def finish(error=None):
    global phase
    phase = 'done'
    report['ok'] = error is None
    report['editor_ok'] = error is None
    report['elapsed_s'] = round(time.monotonic() - started, 1)
    if error:
        report['error'] = error; u.log_error(error)
    try:
        REPORT.write_text(json.dumps(report, indent=2, default=str))
    finally:
        u.unregister_slate_post_tick_callback(handle)
        u.SystemLibrary.quit_editor()


def start_apply():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = OUT / ('L_Benmore_GaeaReview_before_bo1_%s.umap' % stamp)
    src_hash = sha256(MAP_FILE)
    shutil.copy2(MAP_FILE, backup)
    b_hash = sha256(backup)
    if b_hash != src_hash:
        raise RuntimeError('Backup hash differs from the source map')
    report['backup'] = {'path': str(backup), 'sha256': b_hash, 'bytes': backup.stat().st_size,
                        'earlier_backups': sorted(str(p) for p in OUT.glob('L_Benmore_GaeaReview_before_bo1_*.umap') if p != backup)}
    if not les.load_level(LEVEL):
        raise RuntimeError('load_level failed')
    try:
        u.AutomationLibrary.finish_loading_before_screenshot()
    except Exception as e:
        report['unexpected'].append('finish_loading_before_screenshot: %s' % e)
    report['cvar_at_start'] = cvar()
    report['instance_signature_before'] = signature()
    report['rt_census_before'] = rt_census()
    apply_changes()
    sig = signature()
    if sig != report['instance_signature_before']:
        raise RuntimeError('Instance signature changed by the flag edits')
    report['instance_signature_after_change'] = sig
    report['measurement_note'] = 'Dumps taken after the flag edits were applied in memory, before the save.'


def start_measure():
    global report
    prev = json.loads((OUT / 'bo1-report-run1.json').read_text())
    if not (prev.get('saved') and prev.get('signatures_equal') and prev.get('changes')):
        raise RuntimeError('measure mode needs the saved run-1 report bo1-report-run1.json')
    keep = {k: v for k, v in prev.items() if k not in ('lumen_stats', 'lumen_stats_source', 'images', 'cvar_readback', 'measurement_note', 'error', 'elapsed_s', 'ok', 'editor_ok', 'viewport_realtime_set')}
    report = {**report, **keep}
    report['images'] = []; report['cvar_readback'] = {}; report['unexpected'] = list(prev.get('unexpected', []))
    report['run1'] = {'report': str(OUT / 'bo1-report-run1.json'), 'log': str(OUT / 'BenmoreBO1-run1.log'),
                      'note': 'Run 1 applied and saved the flags; its Lumen dumps were invalid (the off-screen editor viewport never draws, '
                              'only the screenshot render dumped once and the parser attached that block to all three markers).'}
    map_hash = sha256(MAP_FILE)
    report['measure_run'] = {'map_sha256_at_start': map_hash, 'matches_run1_saved_map': map_hash == prev.get('map_sha256_after_save')}
    if map_hash != prev.get('map_sha256_after_save'):
        report['unexpected'].append('Map file changed since run 1 save (sha %s)' % map_hash)
    b = prev.get('backup', {})
    if b.get('path') and Path(b['path']).exists():
        report['measure_run']['backup_sha256_recheck'] = sha256(b['path'])
        report['measure_run']['backup_intact'] = report['measure_run']['backup_sha256_recheck'] == b.get('sha256')
    if not les.load_level(LEVEL):
        raise RuntimeError('load_level failed')
    try:
        u.AutomationLibrary.finish_loading_before_screenshot()
    except Exception as e:
        report['unexpected'].append('finish_loading_before_screenshot: %s' % e)
    report['cvar_at_start'] = cvar()
    sig = signature()
    report['measure_run']['instance_signature'] = sig
    if sig != prev['instance_signature_before']:
        raise RuntimeError('Instance signature differs from run 1')
    verify_flags('measure_run_flags')
    report['measure_run']['rt_census'] = rt_census()
    report['measurement_note'] = ('Measure run (no save): map already carries the BO1 flags; dumps and pictures from a transient '
                                  'SceneCapture2D rendered every tick at the camera.')


def tick(dt):
    global phase, last, cam_index
    if phase == 'done':
        return
    try:
        now = time.monotonic()
        if now - started > 1200:
            raise RuntimeError('Bounded BO1 run timeout (1200 s) in phase ' + phase)
        if phase not in ('start', 'loading', 'saving'):
            render()
        if phase == 'start':
            phase = 'loading'
            report['mode'] = MODE
            start_measure() if MODE == 'measure' else start_apply()
            find_cameras()
            make_capture()
            place('Ford')
            phase = 'settle_150'; last = time.monotonic()
        elif phase == 'settle_150' and now - last > SETTLE:
            dump('first_150'); phase = 'dumped_150'; last = now
        elif phase == 'dumped_150' and now - last > AFTER_DUMP:
            console(CVAR + ' 10'); console('r.LumenScene.SurfaceCache.Reset 1'); phase = 'settle_10'; last = now
        elif phase == 'settle_10' and now - last > SETTLE:
            dump('at_10'); phase = 'dumped_10'; last = now
        elif phase == 'dumped_10' and now - last > AFTER_DUMP:
            console(CVAR + ' 150'); console('r.LumenScene.SurfaceCache.Reset 1'); phase = 'settle_150b'; last = now
        elif phase == 'settle_150b' and now - last > SETTLE:
            dump('at_150_again'); phase = 'dumped_150b'; last = now
        elif phase == 'dumped_150b' and now - last > AFTER_DUMP:
            cam_index = 0; phase = 'picture'
        elif phase == 'picture':
            key = CAMERAS[cam_index][0]
            export_settled(key); shoot(key); phase = 'shot'; last = now
        elif phase == 'shot' and shot_done(now):
            cam_index += 1
            if cam_index < len(CAMERAS):
                place(CAMERAS[cam_index][0]); phase = 'settle_next'; last = now
            else:
                phase = 'closing'
        elif phase == 'settle_next' and now - last > SETTLE:
            phase = 'picture'
        elif phase == 'closing':
            destroy_capture()
            if MODE == 'measure':
                after = sha256(MAP_FILE)
                report['measure_run']['map_sha256_at_end'] = after
                report['measure_run']['map_unchanged'] = after == report['measure_run']['map_sha256_at_start']
                if not report['measure_run']['map_unchanged']:
                    raise RuntimeError('Map file changed during the measure run')
                finish(); return
            phase = 'saving'
            if not u.EditorLoadingAndSavingUtils.save_map(world(), LEVEL):
                raise RuntimeError('save_map failed')
            report['saved'] = True
            report['map_sha256_after_save'] = sha256(MAP_FILE)
            if not les.load_level(LEVEL):
                raise RuntimeError('reload failed')
            sig = signature()
            report['instance_signature_reloaded'] = sig
            if sig != report['instance_signature_before']:
                raise RuntimeError('Instance signature changed after save and reload')
            verify_flags('reloaded_flags')
            if any(a.get_actor_label() == 'BO1_TransientCapture' for a in act.get_all_level_actors()):
                raise RuntimeError('Transient capture actor present after reload')
            report['rt_census_reloaded'] = rt_census()
            report['signatures_equal'] = True
            finish()
    except Exception:
        finish(traceback.format_exc())


handle = u.register_slate_post_tick_callback(tick)
