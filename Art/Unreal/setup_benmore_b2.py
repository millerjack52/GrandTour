"""Benmore integration B2 / B2c (docs/BENMORE_INTEGRATION_PLAN.md B2, its addendum and B2c), the editor step (Art/benmore_b2.ps1
-Step setup). Writes Art/Export/BenmoreB2/setup-c.json (and setup.json, the launcher's check). B2a's and B2b's stages (a, b) are in git
history (49b7013, 46fba10); this is the whole setup as of B2c, in one run:

1. Art/Export/BenmoreB2/plan.json (Art/benmore_b2_plan.py) into L_Benmore_GaeaReview as AGTDeformZone actors (folder GT_DeformZones;
   earlier ones replaced; a bog with meshes in its outline left out):
   - gravel stretches: DA_GravelDeform's profile (Loose or Firm) on M_GC_Terrain_Zone (Codex's road material with the deformation on
     top), no loose stones (Codex's verge stones are there already), the road's width;
   - MudRoad stretches: DA_MudVariants' MudRoad section (MRD1c) on M_GT_Mud_Zone, the zone 4 m wider than the road (the mud spills onto
     the verges and thins out there), its tracks on the road's own width;
   - bogs: the variant's bog section on M_GT_Mud_Zone.
2. Each mud zone's colour: the landscape's base colour sampled round it (a top-down base-colour capture of 1.5 m squares 7-9 m off a
   road's edge, 6-8 m off a bog's outline; the median), made wetter (value x0.62, saturation x1.15): the zone's MudColour (the far maps)
   and, over the bog bake's mean for its variant, its SurfaceTint (M_GT_Mud_Zone's MudTint).
3. The far maps (AGTDeformZone::BakeMudMaps: the mud's opacity and the apron at 50 cm, the colours at 2 m) baked and imported.
4. The bogs' vegetation copy; M_GT_Mud_Zone; M_GC_Terrain's coverage dither, apron and far mud (benmore_deform_zones.attach_deform),
   then M_GC_Terrain_Zone copied from it. Instruction and sampler counts.
The map is saved only if its file is unchanged since this run loaded it.
"""
import colorsys
import json
import math
import os
import statistics
import sys
import time
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
sys.path.insert(0, str(ROOT / 'Art/Unreal'))
import benmore_deform_zones as dz   # noqa: E402

STAGE = 'c'
OUT = ROOT / 'Art/Export/BenmoreB2'
LEVEL = '/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview'
UMAP = ROOT / 'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap'
TERRAIN = dz.TERRAIN
GRAVEL_SPEC = '/Game/GrandTour/ArtTests/DeformableGravel/DA_GravelDeform'
MUD_SPEC = '/Game/GrandTour/ArtTests/MudVariants/DA_MudVariants'
ROAD_MAT = dz.ROAD_ZONE + '.' + dz.ROAD_ZONE.rsplit('/', 1)[1]
MUD_MAT = dz.MUD_ZONE + '.' + dz.MUD_ZONE.rsplit('/', 1)[1]
MUD_SPILL_CM = 400.0
eal = u.EditorAssetLibrary
mel = u.MaterialEditingLibrary
report = dict(ok=False, stage=STAGE, level=LEVEL, timings_collected=False)


def stats(m):
    s = mel.get_statistics(m)
    return dict(pixel=s.num_pixel_shader_instructions, vertex=s.num_vertex_shader_instructions, samplers=s.num_samplers,
                pixel_texture_samples=s.num_pixel_texture_samples)


def sections():
    gsec = list(eal.load_asset(GRAVEL_SPEC).get_editor_property('spec').get_editor_property('sections'))
    msec = list(eal.load_asset(MUD_SPEC).get_editor_property('spec').get_editor_property('sections'))
    variants = dict(STANDARD=u.GTMudVariant.STANDARD, FIRM=u.GTMudVariant.FIRM, DEEP=u.GTMudVariant.DEEP, STONY=u.GTMudVariant.STONY)
    braided = [s for s in msec if s.get_editor_property('deform').get_editor_property('pre_churn_style') == u.GTPreChurnStyle.BRAIDED]
    by_variant = {k: s for k, e in variants.items() for s in msec if s.get_editor_property('mud_variant') == e and s not in braided}
    road = braided[0]
    # DA_GravelDeform: Firm (2.5 cm, 12 stones a m^2) then Loose (5 cm, 30).
    firm, loose = sorted(gsec, key=lambda s: s.get_editor_property('deform').get_editor_property('max_sinkage_m'))
    return dict(firm=firm, loose=loose, road=road, by_variant=by_variant)


def lin2srgb(c):
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def srgb2lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def wetter(rgb):
    h, s, v = colorsys.rgb_to_hsv(*[lin2srgb(max(0.0, min(1.0, c))) for c in rgb])
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, s * 1.15), v * 0.62)
    return [srgb2lin(c) for c in (r, g, b)]


def run_c():
    plan = json.loads((OUT / 'plan.json').read_text())
    world = u.EditorLoadingAndSavingUtils.load_map(LEVEL)
    assert world
    loaded_mtime = UMAP.stat().st_mtime
    report['umap_mtime_at_load'] = loaded_mtime
    act = u.get_editor_subsystem(u.EditorActorSubsystem)
    removed = 0
    for a in act.get_all_level_actors():
        if isinstance(a, u.GTDeformZone):
            act.destroy_actor(a)
            removed += 1
    report['zones_removed'] = removed
    sec = sections()

    def ground_z(x, y):
        hit = u.SystemLibrary.line_trace_single(world, u.Vector(x, y, 60000.), u.Vector(x, y, -60000.), u.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                u.DrawDebugTrace.NONE, True)
        if not hit:
            return None, None
        t = hit.to_tuple()
        actor = next((v for v in t if isinstance(v, u.Actor)), None)
        point = next((v for v in t if isinstance(v, u.Vector)), None)
        return (point.z if point else None), actor

    def spawn(label, x, y, yaw):
        z, _ = ground_z(x, y)
        a = act.spawn_actor_from_class(u.GTDeformZone, u.Vector(x, y, (z or 0.0) + 50.0), u.Rotator(yaw=yaw))   # Rotator's positional order is roll, pitch, yaw
        a.set_actor_label(label)
        a.set_folder_path('GT_DeformZones')
        return a

    # 2's sampler: a top-down base-colour capture of a 1.5 m square, the landscape alone.
    cap = act.spawn_actor_from_class(u.SceneCapture2D, u.Vector(0.0, 0.0, 100000.0), u.Rotator(pitch=-90.0))
    comp = cap.get_component_by_class(u.SceneCaptureComponent2D)
    rt = u.RenderingLibrary.create_render_target2d(world, 8, 8, u.TextureRenderTargetFormat.RTF_RGBA16F)
    props = dz.props
    props(comp, projection_type=u.CameraProjectionMode.ORTHOGRAPHIC, ortho_width=150.0, capture_source=u.SceneCaptureSource.SCS_BASE_COLOR,
          capture_every_frame=False, capture_on_movement=False, texture_target=rt)
    comp.set_editor_property('show_flag_settings', [props(u.EngineShowFlagsSetting(), show_flag_name=n, enabled=False)
                                                    for n in ('InstancedGrass', 'InstancedFoliage', 'InstancedStaticMeshes', 'StaticMeshes', 'Particles',
                                                              'Fog', 'Decals', 'SkeletalMeshes', 'Translucency')])

    def capture(x, y):
        z, _ = ground_z(x, y)
        if z is None:
            return None
        cap.set_actor_location(u.Vector(x, y, z + 2000.0), False, False)
        comp.capture_scene()
        px = u.RenderingLibrary.read_render_target_raw(world, rt, False)
        if not px:
            return None
        return [sum(getattr(p, k) for p in px) / len(px) for k in ('r', 'g', 'b')]

    def soil(points):
        got = [c for c in (capture(x, y) for x, y in points) if c and sum(c) > 0.01]
        if not got:
            return None, 0
        return [statistics.median(c[i] for c in got) for i in range(3)], len(got)

    def road_points(z_):
        line = z_['line_cm']
        arcs = [0.0]
        for i in range(1, len(line)):
            arcs.append(arcs[-1] + math.hypot(line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]))
        hw = z_['width_cm'] * 0.5
        pts = []
        for f in (0.1, 0.3, 0.5, 0.7, 0.9):
            s = z_['start_cm'] + f * (z_['end_cm'] - z_['start_cm'])
            i = next((k for k in range(1, len(line)) if arcs[k] >= s), len(line) - 1)
            t = (s - arcs[i - 1]) / max(1e-6, arcs[i] - arcs[i - 1])
            x = line[i - 1][0] + (line[i][0] - line[i - 1][0]) * t
            y = line[i - 1][1] + (line[i][1] - line[i - 1][1]) * t
            dx, dy = line[i][0] - line[i - 1][0], line[i][1] - line[i - 1][1]
            n = math.hypot(dx, dy) or 1.0
            nx, ny = -dy / n, dx / n
            for off in (hw + 700.0, hw + 900.0):
                for sd in (1.0, -1.0):
                    pts.append((x + nx * off * sd, y + ny * off * sd))
        return pts

    # The landscape's shaders compile after the map loads (the capture draws the default grey until they have): wait until a probe of
    # open ground reads coloured, up to 25 minutes.
    probe = road_points(next(z for z in plan['zones'] if z['kind'] == 'mud'))[0]
    t0 = time.monotonic()
    while True:
        c = capture(*probe)
        if c and (abs(c[0] - c[1]) > 0.003 or abs(c[1] - c[2]) > 0.003):
            break
        if time.monotonic() - t0 > 1500.0:
            raise RuntimeError('the landscape still captures grey after 25 minutes: %s' % c)
        for _ in range(30):
            yield
    report['shader_wait_s'] = round(time.monotonic() - t0)
    report['probe_linear'] = [round(v, 4) for v in c]

    rows = []
    for z_ in plan['zones']:
        cx, cy = z_['centre_m'][0] * 100.0, z_['centre_m'][1] * 100.0
        a = spawn(z_['label'], cx, cy, 0.0)
        mud = z_['kind'] == 'mud'
        if mud:
            s = sec['road']
        else:
            s = sec[z_['profile']]
            d = s.get_editor_property('deform')
            d.set_editor_property('surface_material_path', ROAD_MAT)
            d.set_editor_property('gravel_stones_per_m2', 0.0)   # Codex's verge stones are there already
            s.set_editor_property('deform', d)
        p = dict(zone_id=z_['id'], label=z_['label'], shape=u.GTDeformZoneShape.ROAD, line_cm=[u.Vector2D(q[0], q[1]) for q in z_['line_cm']],
                 width_cm=z_['width_cm'] + (MUD_SPILL_CM if mud else 0.0), track_width_cm=z_['width_cm'] if mud else 0.0,
                 start_cm=z_['start_cm'], end_cm=z_['end_cm'], cut_wave_cm=60.0, start_cut_key=z_['start_key'], end_cut_key=z_['end_key'],
                 section=s, tiled=not mud, edge_fade_cm=150.0, surface_tint=u.LinearColor(1.0, 1.0, 1.0, 1.0),
                 patch_material_path=MUD_MAT if mud else '')
        row = dict(id=z_['id'], label=z_['label'], kind=z_['kind'], profile=z_['profile'], length_m=z_['length_m'], actor=a.get_actor_label())
        if mud:
            c, n = soil(road_points(z_))
            row.update(soil_samples=n, soil_linear=[round(v, 4) for v in c] if c else None)
            c = c or [0.20, 0.16, 0.11]
            w = wetter(c)
            mean = dz.BOG_MEAN['STANDARD']
            tint = [round(w[i] / mean[i], 3) for i in range(3)]
            p.update(mud_colour=u.LinearColor(w[0], w[1], w[2], 1.0), surface_tint=u.LinearColor(tint[0], tint[1], tint[2], 1.0))
            row.update(mud_colour_linear=[round(v, 4) for v in w], mud_tint=tint)
        for k, v in p.items():
            a.set_editor_property(k, v)
        rows.append(row)
    bogs = []
    for b in plan['bogs']:
        cx, cy = b['centre_m'][0] * 100.0, b['centre_m'][1] * 100.0
        rx, ry = b['half_m'][0] * 100.0, b['half_m'][1] * 100.0
        ca, sa = math.cos(math.radians(b['yaw_deg'])), math.sin(math.radians(b['yaw_deg']))
        hits, samples, zs = {}, 0, []
        for i in range(-12, 13):
            for j in range(-12, 13):
                lx, ly = i / 12.0 * rx * 1.16, j / 12.0 * ry * 1.16
                if (lx / (rx * 1.16)) ** 2 + (ly / (ry * 1.16)) ** 2 > 1.0:
                    continue
                x, y = cx + lx * ca - ly * sa, cy + lx * sa + ly * ca
                z, actor = ground_z(x, y)
                samples += 1
                if actor is not None and not isinstance(actor, u.LandscapeProxy):
                    hits[actor.get_actor_label()] = hits.get(actor.get_actor_label(), 0) + 1
                elif z is not None:
                    zs.append(z)
        row = dict(b, samples=samples, mesh_hits=hits, ground_z_range_cm=[round(min(zs)), round(max(zs))] if zs else None)
        if sum(hits.values()) > 0.02 * samples:
            row.update(placed=False, why_not='meshes in the outline')
            bogs.append(row)
            continue
        a = spawn(b['label'], cx, cy, b['yaw_deg'])
        s = sec['by_variant'].get(b['variant'].upper()) or sec['by_variant'].get('FIRM')
        if b['variant'].upper() == 'STANDARD':
            s = sections()['by_variant']['FIRM']   # a fresh copy (the strips' Standard section is the mud road)
            s.set_editor_property('mud_variant', u.GTMudVariant.STANDARD)
            d = s.get_editor_property('deform')
            d.set_editor_property('pre_churn_style', u.GTPreChurnStyle.PAIRS)
            s.set_editor_property('deform', d)
        ring = []
        r0 = max(rx, ry) * 1.16 + 260.0
        for k in range(12):
            ang = 2.0 * math.pi * k / 12.0
            for extra in (600.0, 800.0):
                rr = r0 + extra
                ring.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
        c, n = soil(ring)
        row.update(soil_samples=n, soil_linear=[round(v, 4) for v in c] if c else None)
        c = c or [0.20, 0.16, 0.11]
        w = wetter(c)
        mean = dz.BOG_MEAN[b['variant'].upper()]
        tint = [round(w[i] / mean[i], 3) for i in range(3)]
        p = dict(zone_id=b['id'], label=b['label'], shape=u.GTDeformZoneShape.BLOB, blob_half_cm=u.Vector2D(rx, ry), blob_edge_noise=0.16,
                 section=s, tiled=False, edge_fade_cm=150.0, patch_material_path=MUD_MAT,
                 mud_colour=u.LinearColor(w[0], w[1], w[2], 1.0), surface_tint=u.LinearColor(tint[0], tint[1], tint[2], 1.0))
        for k, v in p.items():
            a.set_editor_property(k, v)
        row.update(placed=True, actor=a.get_actor_label(), section_variant=str(s.get_editor_property('mud_variant')),
                   water_table_cm=s.get_editor_property('water_table_cm'), pre_churn=s.get_editor_property('deform').get_editor_property('pre_churn_scale'),
                   mud_colour_linear=[round(v, 4) for v in w], mud_tint=tint)
        bogs.append(row)
    act.destroy_actor(cap)
    report['zones'] = rows
    report['bogs'] = bogs
    # 3. The far maps.
    mask_png, colour_png = OUT / 'T_GT_MudZoneMask.png', OUT / 'T_GT_MudZoneColour.png'
    baked = u.GTDeformZone.bake_mud_maps(world, u.Vector2D(*dz.FAR_ORIGIN), dz.FAR_SIZE, dz.FAR_MASK_SIZE, dz.FAR_COLOUR_SIZE, dz.FAR_APRON_CM,
                                        str(mask_png), str(colour_png))
    report['far_maps'] = json.loads(baked)
    assert report['far_maps'].get('ok'), baked
    report['far_textures'] = dz.import_far_maps(mask_png, colour_png)
    # 4. The materials.
    report['coverage_default'] = dz.ensure_coverage_default()
    report['vegetation_copy'] = dz.ensure_vegetation_copy()
    m = eal.load_asset(TERRAIN)
    report['terrain_before'] = stats(m)
    rep = dz.attach_deform(m)
    errors = [str(e) for e in mel.recompile_material(m)]
    if (errors and any('StateFrameIndexMod8' in e for e in errors)) or str(rep.get('road_zone_material', '')).startswith('failed: frame'):
        report['dither_frame_term'] = 'off: %s' % (errors[:1] or rep.get('road_zone_material'))
        dz.FRAME = '0'
        rep = dz.attach_deform(m)
        errors = [str(e) for e in mel.recompile_material(m)]
    assert not errors, errors[:3]
    assert eal.save_loaded_asset(m)
    report['attach'] = rep
    assert isinstance(rep.get('road_zone_material'), dict), rep.get('road_zone_material')
    report['terrain_after'] = stats(m)
    report['mud_zone_material'] = dz.build_mud_zone_material()
    report['blend_mode'] = str(m.get_editor_property('blend_mode'))
    u.SystemLibrary.execute_console_command(world, 'grass.FlushCache')
    now_mtime = UMAP.stat().st_mtime
    report['umap_mtime_before_save'] = now_mtime
    if now_mtime != loaded_mtime:
        raise RuntimeError('L_Benmore_GaeaReview changed on disk since this run loaded it: not saved')
    assert u.EditorLoadingAndSavingUtils.save_map(world, LEVEL)
    report['saved'] = True
    report['surface_effects_actors'] = [a.get_actor_label() for a in act.get_all_level_actors() if a.get_class().get_name().startswith('GTVehicleSurfaceEffects')]


def finish(error=None):
    report['ok'] = error is None
    if error:
        report['error'] = error
    text = json.dumps(report, indent=1, default=str)
    (OUT / ('setup-%s.json' % STAGE)).write_text(text)
    (OUT / 'setup.json').write_text(text)
    u.unregister_slate_post_tick_callback(handle)
    u.SystemLibrary.quit_editor()


u.EditorPythonScripting.set_keep_python_script_alive(True)
gen = run_c()
busy = False


def tick(dt):
    global busy
    if busy:
        return
    busy = True
    try:
        next(gen)
    except StopIteration:
        finish()
    except Exception:  # noqa: BLE001
        finish(traceback.format_exc())
    finally:
        busy = False


handle = u.register_slate_post_tick_callback(tick)
