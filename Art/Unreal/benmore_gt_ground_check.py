"""Benmore integration B1 item 6 (docs/BENMORE_INTEGRATION_PLAN.md B1): the checks on the saved review level, in a -RenderOffScreen editor
(Art/benmore_b1.ps1 -Step check). Saves nothing.
- The review material's static shader counts (MaterialEditingLibrary.get_statistics; not timing) and its collections.
- The surface table: line traces against the landscape's collision (its physical material output, rendered per collision sample) along
  the two roads at fixed offsets from the centreline and on a 64 x 64 grid over the site.
- At three review locations (the Gaea review cameras Creek_Close, Creek_Reach, Long_Vista): an open-ground spot found by traces (firm
  ground, under 10 deg, 20 m or more from a road centreline), the nearest road verge, the sun behind every camera:
  BI_OnFoot_<loc>.png (1.7 m, 30 deg down), BI_OnFoot_<loc>_Off.png (the same with MPC_GT_GroundDetail GroundDetail 0 and ScatterScale 0),
  BI_Verge_<loc>.png, BI_Far_<loc>.png (1.7 m, 40-60 m of ground). The scatter's instance counts near the camera from the engine's own
  grass build log (LogGrass Verbose 'ASYNC GRASS INSTANCES COMPLETE', the last build per component, subsection and mesh).
Writes Art/Export/BenmoreB1/check.json and the pictures there."""
import json
import math
import os
import re
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = ROOT / 'Art/Export/BenmoreB1'
LOG = ROOT / 'Saved/Logs/benmore_b1_check.log'
LEVEL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
MATERIAL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement/M_GC_Terrain'
MPC = '/Game/GrandTour/Terrain/MPC_GT_GroundDetail'
ROADS = json.loads((ROOT / 'Art/Export/BenmoreRoads/road-manifest.json').read_text())['routes']
LOCATIONS = [('CreekClose', 'Benmore_Gaea_Camera_Creek_Close'), ('CreekReach', 'Benmore_Gaea_Camera_Creek_Reach'),
             ('LongVista', 'Benmore_Gaea_Camera_Long_Vista')]
SCATTER_MESHES = re.compile(r'^SM_GD_(Clod|Pebble|Twig|Litter)')
GROW_S = 32
GROUND = {'PM_Benmore_FirmGround'}
ONLY = os.environ.get('GT_B1_ONLY', '')   # e.g. '_Off': only those shots, their rows replaced in the previous check.json
GRASS_TYPES = ['/Game/GrandTour/Terrain/GroundDetail/LGT_GT_SoilScatter', '/Game/GrandTour/Terrain/GroundDetail/LGT_GT_GrassLitter']


def scatter_density(scale, authored):
    """As UGTTrackPaintSubsystem does for gt.Ground.Scatter: the scatter grass types' densities times scale (in memory, not saved)."""
    i = 0
    for path in GRASS_TYPES:
        t = eal.load_asset(path)
        vs = list(t.get_editor_property('grass_varieties'))
        for v in vs:
            if len(authored) <= i:
                authored.append(v.get_editor_property('grass_density').get_editor_property('default'))
            v.set_editor_property('grass_density', u.PerPlatformFloat(default=authored[i] * scale))
            i += 1
        t.set_editor_property('grass_varieties', vs)
mel = u.MaterialEditingLibrary
eal = u.EditorAssetLibrary
act = u.get_editor_subsystem(u.EditorActorSubsystem)
ues = u.get_editor_subsystem(u.UnrealEditorSubsystem)
report = dict(ok=False, level=LEVEL, timings_collected=False, images=[])


def stats(path):
    m = eal.load_asset(path)
    s = mel.get_statistics(m)
    cols = sorted({e.get_editor_property('collection').get_path_name() for e in mel.get_material_expressions(m)
                   if isinstance(e, u.MaterialExpressionCollectionParameter) and e.get_editor_property('collection')})
    return dict(pixel=s.num_pixel_shader_instructions, vertex=s.num_vertex_shader_instructions, samplers=s.num_samplers,
                pixel_texture_samples=s.num_pixel_texture_samples, collections=cols)


def trace(world, ignore, x, y):
    """The landscape under (x, y): its point, normal and physical material (UGTSurfaceQueryLibrary: the Kismet traces return none)."""
    res = u.GTSurfaceQueryLibrary.trace_landscape_surface(world, u.Vector(x, y, 60000.0), u.Vector(x, y, -60000.0))
    pm, point, normal = res if isinstance(res, tuple) else (res, None, None)
    if point is None or (point.x == 0.0 and point.y == 0.0 and point.z == 0.0 and pm is None):
        return None
    return dict(point=point, normal=normal, pm=pm.get_name() if pm else None, landscape=True)


def surface_table(world, ignore):
    table = dict(roads={}, grid={}, misses=0)
    for r in ROADS:
        hw = r['width_m'] * 0.5
        for label, off in [('centre', 0.0), ('quarter', hw * 0.5), ('edge-0.3m', hw - 0.3), ('verge+1.5m', hw + 1.5), ('grass+8m', hw + 8.0)]:
            counts = {}
            for pt in r['points'][::12]:
                yaw = math.radians(pt['yaw'])
                for side in (1.0, -1.0):
                    x = (pt['x_m'] - math.sin(yaw) * off * side) * 100.0
                    y = (pt['y_m'] + math.cos(yaw) * off * side) * 100.0
                    h = trace(world, ignore, x, y)
                    if not h or not h['landscape']:
                        table['misses'] += 1
                        continue
                    counts[h['pm']] = counts.get(h['pm'], 0) + 1
            table['roads'].setdefault(r['name'], {})[label] = counts
    for i in range(64):
        for j in range(64):
            x = -123000 + 246000 * (i + 0.5) / 64
            y = -123000 + 246000 * (j + 0.5) / 64
            h = trace(world, ignore, x, y)
            if not h or not h['landscape']:
                table['misses'] += 1
                continue
            table['grid'][h['pm']] = table['grid'].get(h['pm'], 0) + 1
    return table


def nearest_road(x, y):
    best = None
    for r in ROADS:
        for pt in r['points']:
            d = math.hypot(pt['x_m'] * 100 - x, pt['y_m'] * 100 - y)
            if best is None or d < best[0]:
                best = (d, r, pt)
    return best


def find_open(world, ignore, cx, cy, yaw):
    """The first spot on rings of 10-200 m round (cx, cy) that is firm ground under 10 deg, 20 m from a road centreline, with firm
    ground 6 and 12 m along the view."""
    for radius in range(1000, 20001, 1000):
        for k in range(16):
            a = 2 * math.pi * k / 16
            x, y = cx + radius * math.cos(a), cy + radius * math.sin(a)
            h = trace(world, ignore, x, y)
            if not h or not h['landscape'] or h['pm'] not in GROUND or h['normal'].z < 0.985:
                continue
            if nearest_road(x, y)[0] < 2000:
                continue
            ok = True
            for d in (600, 1200, 2400):
                g = trace(world, ignore, x + d * math.cos(yaw), y + d * math.sin(yaw))
                if not g or g['pm'] not in GROUND:
                    ok = False
                    break
            if ok:
                return x, y, h['point'].z, radius
    return None


def grass_counts(marker):
    text = LOG.read_text(errors='ignore') if LOG.exists() else ''
    at = text.rfind(marker)
    text = text[at:] if at >= 0 else ''
    last = {}
    for m in re.finditer(r'ASYNC GRASS INSTANCES COMPLETE (\S+) (\S+) (\d+) (\d+) \((\d+)\)', text):
        last[(m.group(1), m.group(2), m.group(3), m.group(4))] = int(m.group(5))
    per = {}
    for (comp, mesh, sx, sy), n in last.items():
        per[mesh] = per.get(mesh, 0) + n
    ours = {k: v for k, v in per.items() if SCATTER_MESHES.match(k)}
    fam = {}
    for k, v in ours.items():
        f = SCATTER_MESHES.match(k).group(1)
        fam[f] = fam.get(f, 0) + v
    return dict(scatter_per_mesh=ours, scatter_per_family=fam, scatter_total=sum(ours.values()),
                others_total=sum(v for k, v in per.items() if not SCATTER_MESHES.match(k)), builds=len(last))


def run():
    u.EditorPythonScripting.set_keep_python_script_alive(True)
    state = dict(phase='load', t=time.monotonic(), shots=[], i=0, marker='')

    def finish(error=None):
        report['ok'] = error is None
        if error:
            report['error'] = error
            u.log_error(error)
        try:
            for c in state.get('cams', []):
                act.destroy_actor(c)
        except Exception:  # noqa: BLE001
            pass
        (OUT / 'check.json').write_text(json.dumps(report, indent=1, default=str))
        u.unregister_slate_post_tick_callback(handle)
        u.SystemLibrary.quit_editor()

    def cam(loc, yaw, pitch, fov):
        c = act.spawn_actor_from_class(u.CameraActor, loc, u.Rotator(roll=0.0, pitch=pitch, yaw=yaw))
        c.camera_component.set_field_of_view(fov)
        c.camera_component.set_editor_property('constrain_aspect_ratio', False)
        state.setdefault('cams', []).append(c)
        return c

    def tick(dt):
        try:
            now = time.monotonic()
            ph = state['phase']
            if ph == 'load':
                state['phase'] = 'loading'
                world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
                assert world
                state['world'] = world
                actors = list(u.GameplayStatics.get_all_actors_of_class(world, u.Actor))
                ignore = [a for a in actors if not isinstance(a, u.LandscapeProxy)]
                state['ignore'] = ignore
                report['material'] = stats(MATERIAL)
                diag = []
                for r in ROADS:
                    n = len(r['points'])
                    for i in (n // 7, 3 * n // 7, 5 * n // 7):
                        pt = r['points'][i]
                        diag.append(u.GTSurfaceQueryLibrary.describe_landscape_surface_at(world, u.Vector(pt['x_m'] * 100.0, pt['y_m'] * 100.0, 0.0)))
                report['surface_diagnosis'] = diag
                report['surfaces'] = surface_table(world, ignore)
                if not any(k not in (None, 'null') for k in report['surfaces']['grid']):
                    GROUND.add(None)   # no physical material anywhere: the open-ground search goes by slope and road distance alone
                sun = next(a for a in actors if isinstance(a, u.DirectionalLight))
                f = sun.get_actor_forward_vector()
                syaw = math.degrees(math.atan2(f.y, f.x))   # the light travels this way: looking along it puts the sun behind
                report['sun'] = dict(forward=[f.x, f.y, f.z], view_yaw=syaw)
                cams = {a.get_actor_label(): a for a in actors if isinstance(a, u.CameraActor)}
                shots = []
                for loc, label in LOCATIONS:
                    c = cams[label].get_actor_location()
                    spot = find_open(world, ignore, c.x, c.y, math.radians(syaw))
                    assert spot, 'no open ground near ' + label
                    x, y, z, r = spot
                    d, road, pt = nearest_road(c.x, c.y)
                    hw = road['width_m'] * 0.5
                    ryaw = pt['yaw'] if math.cos(math.radians(pt['yaw'] - syaw)) >= 0 else pt['yaw'] + 180.0
                    nx, ny = -math.sin(math.radians(ryaw)), math.cos(math.radians(ryaw))   # the verge on the left of the view along the road
                    vx, vy = pt['x_m'] * 100 + nx * (hw + 2.5) * 100, pt['y_m'] * 100 + ny * (hw + 2.5) * 100
                    vh = trace(world, ignore, vx, vy)
                    report.setdefault('locations', {})[loc] = dict(camera=label, open_ground=[x, y, z], ring_m=r / 100.0, road=road['name'],
                                                                   road_point=[pt['x_m'], pt['y_m']], road_distance_m=d / 100.0,
                                                                   verge=[vx, vy, vh['point'].z if vh else None], verge_pm=vh['pm'] if vh else None)
                    eye = u.Vector(x, y, z + 170.0)
                    shots.append((loc, 'BI_OnFoot_%s' % loc, eye, syaw, -30.0, 70.0, True))
                    shots.append((loc, 'BI_OnFoot_%s_Off' % loc, eye, syaw, -30.0, 70.0, False))
                    # The verge: 1.7 m over it, looking along the road, turned 12 deg toward the running surface, 10 deg down.
                    toward = -12.0   # the road is on the right of a camera on the left verge: turn clockwise toward it
                    shots.append((loc, 'BI_Verge_%s' % loc, u.Vector(vx, vy, (vh['point'].z if vh else z) + 170.0), ryaw + toward, -10.0, 70.0, True))
                    shots.append((loc, 'BI_Far_%s' % loc, eye, syaw, -4.0, 60.0, True))
                state['shots'] = [s for s in shots if ONLY in s[1]] if ONLY else shots
                state['authored'] = []
                u.SystemLibrary.execute_console_command(world, 'log LogGrass Verbose')
                state.update(phase='view', t=now)
            elif ph == 'view':
                loc, name, eye, yaw, pitch, fov, on = state['shots'][state['i']]
                world = state['world']
                mpc = eal.load_asset(MPC)
                u.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'GroundDetail', 1.0 if on else 0.0)
                scatter_density(1.0 if on else 0.0, state['authored'])   # gt.Ground.Scatter's path (the collection's ScatterScale does not reach the grass maps)
                c = cam(eye, yaw, pitch, fov)
                state['cam'] = c
                ues.set_level_viewport_camera_info(c.get_actor_location(), c.get_actor_rotation())
                state.update(phase='flush', t=now)
            elif ph == 'flush' and now - state['t'] > 4:
                # The collection reaches the scene at the end of a frame; a flush in the same tick re-renders the nearest grass maps
                # with the old scale.
                loc, name, eye, yaw, pitch, fov, on = state['shots'][state['i']]
                state['marker'] = 'B1_GRASS_MARK_%d_%s' % (state['i'], name)
                u.log(state['marker'])   # the counts read the log after this line (in order with the grass build lines)
                u.SystemLibrary.execute_console_command(state['world'], 'grass.FlushCache')
                state.update(phase='grow', t=now)
            elif ph == 'grow' and now - state['t'] > GROW_S:
                state.update(phase='shot', t=now)   # first: the screenshot call can tick the editor (and this callback) again
                loc, name, eye, yaw, pitch, fov, on = state['shots'][state['i']]
                path = OUT / (name + '.png')
                if path.exists():
                    path.unlink()
                u.AutomationLibrary.take_high_res_screenshot(1440, 900, str(path), state['cam'])
                row = dict(location=loc, image=str(path), eye=[eye.x, eye.y, eye.z], yaw=yaw, pitch=pitch, fov=fov,
                           ground_detail=1 if on else 0, scatter_scale=1 if on else 0)
                row['grass'] = grass_counts(state['marker'])
                report['images'].append(row)
            elif ph == 'shot' and now - state['t'] > 6:
                path = Path(report['images'][-1]['image'])
                if not path.exists() or path.stat().st_size < 1000:
                    if now - state['t'] < 40:
                        return
                    raise RuntimeError('no screenshot written: ' + str(path))
                state['i'] += 1
                if state['i'] >= len(state['shots']):
                    world = state['world']
                    mpc = eal.load_asset(MPC)
                    u.MaterialLibrary.set_scalar_parameter_value(world, mpc, 'GroundDetail', 1.0)
                    scatter_density(1.0, state['authored'])
                    if ONLY and (OUT / 'check.json').exists():
                        prev = json.loads((OUT / 'check.json').read_text())
                        keep = [r for r in prev.get('images', []) if ONLY not in Path(r['image']).name]
                        report['images'] = keep + report['images']
                        report['rerun_only'] = ONLY
                    state['phase'] = 'done'
                    finish()
                else:
                    state['phase'] = 'view'
        except Exception:  # noqa: BLE001
            state['phase'] = 'done'
            finish(traceback.format_exc())

    handle = u.register_slate_post_tick_callback(tick)


run()
