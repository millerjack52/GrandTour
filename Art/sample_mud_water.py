"""Mud and water MW1 (docs/MUD_WATER_SURFACE_PLAN.md items 1 and 4): the numbers from Art/Unreal/check_mud_water.py's pictures.

- water masks: a frame with the rut water against the same frame with it hidden; a pixel is water where any channel differs by
  more than 8/255, kept where at least 5 of its 3 x 3 neighbours are (no lone specks);
- diagnosis (item 1): in the owner's frame, the old track's region (the world strip 4 m before to 3.5 m past the puddle, +-60 cm
  across, projected with the camera) outside the water: each debug picture against the base - the mean absolute difference
  (0-255, RGB), the detail (the mean absolute Laplacian of the luminance, 0-255), the highlight share (luminance over 0.8);
- glare: the owner's frame's water pixels at luminance over 0.95 (display values), before and after (<= 5 %);
- motion: the fixed water camera's frames 0.5 s apart (30 fixed steps), in its water mask: the mean absolute luminance change
  (>= 2/255) and the share of water pixels changing by more than 4/255 (>= 15 %); gt.Mud.WaterMotion 0 against 1 (after);
- PBR: the close bank's buffer dumps (uncompressed EXR; the encoding checked on the strip's gravel, 0.9 by construction, as
  Art/sample_mud_pbr.py): roughness p5/50/95 of the mud outside the water (the frame's middle, the water mask from the pair),
  dry and at test wetness 1; the gate is the wet p5 >= 0.5 (one 8-bit GBuffer step under it, 0.496, is reported as the floor);
  the base colour's luminance inside the soil band (0.0325-0.25).
Writes <report dir>/mw-numbers-<tag>.json and the roughness and normal views (<dump>_Roughness_view.png, _WorldNormal_view.png).
numpy and Pillow (system Python).   python Art/sample_mud_water.py Art/Export/MudWater/check-after.json
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sample_mud_pbr import load_buffer, srgb_encode, pct, lum, save_view, project  # noqa: E402

SOIL_LO, SOIL_HI = 0.0325, 0.25


def img(path):
    """The picture without HighResShot's letterbox (the 16:9 view inside the 1440 x 900 shot: black bands top and bottom), so it
    lines up with the buffer dumps (the view only)."""
    p = Path(path)
    if not p.exists():
        return None
    a = np.asarray(Image.open(p).convert('RGB'), np.float32)
    rows = a.max(axis=(1, 2)) > 0.0
    top = int(np.argmax(rows))
    bottom = len(rows) - int(np.argmax(rows[::-1]))
    band = min(top, len(rows) - bottom)
    return a[band:len(rows) - band] if band > 0 else a


def luma(a):
    return (a[..., 0] * 0.2126 + a[..., 1] * 0.7152 + a[..., 2] * 0.0722) / 255.0


def water_mask(with_w, without):
    if with_w is None or without is None:
        return None
    d = np.abs(with_w - without).max(-1) > 8.0
    m = np.zeros(d.shape, np.int32)
    p = np.pad(d.astype(np.int32), 1)
    for dy in range(3):
        for dx in range(3):
            m += p[dy:dy + d.shape[0], dx:dx + d.shape[1]]
    return m >= 5


def poly_mask(shape, pts):
    from PIL import ImageDraw
    im = Image.new('L', (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon([(float(x), float(y)) for x, y in pts], fill=1)
    return np.asarray(im, bool)


def laplace(l):
    out = np.zeros_like(l)
    out[1:-1, 1:-1] = np.abs(4 * l[1:-1, 1:-1] - l[:-2, 1:-1] - l[2:, 1:-1] - l[1:-1, :-2] - l[1:-1, 2:])
    return out


def cam_of(c):
    return dict(location=c['eye'], target=c['look'], fov=c['fov'])


def cell_mask(rep, key, cam, shape):
    """The rut water's cells the check listed for a frame (rep['water_cells'][key], [x, y, water z]), each square projected with the
    frame's camera and filled; None when the check listed none. (The picture-difference mask caught the grass and the capture
    noise.)"""
    cells = (rep.get('water_cells') or {}).get(key)
    if cells is None:
        return None
    from PIL import ImageDraw
    h, w = shape
    half = 0.5 * float(rep.get('water_cell_cm') or 12.5)
    im = Image.new('L', (w, h), 0)
    dr = ImageDraw.Draw(im)
    c = np.array(cam['location'], float)
    f = np.array(cam['target'], float) - c
    f /= np.linalg.norm(f)
    for x, y, z in cells:
        if (np.array([x, y, z]) - c) @ f <= 10.0:
            continue
        pts = [project(cam, (x + dx, y + dy, z), w, h) for dx, dy in ((-half, -half), (half, -half), (half, half), (-half, half))]
        dr.polygon([(float(a), float(b)) for a, b in pts], fill=1)
    return np.asarray(im, bool)


def main():
    rp = Path(sys.argv[1])
    rep = json.loads(rp.read_text())
    out = rp.parent
    tag = rep.get('tag', 'after')
    pre = {'before': 'MW_Before_', 'mw1': 'MW1_'}.get(tag, 'MW_')
    base_name = {'before': 'MW_Before_OnFoot', 'mw1': 'MW1_OnFoot'}.get(tag, 'MW_After_OnFoot')
    P = rep.get('puddle') or {}
    res = dict(report=str(rp), tag=tag)

    def path(n):
        return out / (n + '.png')

    # ---- the owner's frame: the diagnosis and the glare ----
    base = img(path(base_name))
    if base is not None:
        h, w = base.shape[:2]
        O = rep['frames']['owner']
        wz = O['look'][2]
        corners = [(P['x'] - 400.0, P['y'] - 60.0, wz), (P['x'] + 350.0, P['y'] - 60.0, wz), (P['x'] + 350.0, P['y'] + 60.0, wz), (P['x'] - 400.0, P['y'] + 60.0, wz)]
        pts = [project(cam_of(O), c, w, h) for c in corners]
        track = poly_mask((h, w), pts)
        wm = cell_mask(rep, 'owner', cam_of(O), (h, w))
        if wm is None:
            wm = water_mask(base, img(path(pre + 'Dbg_NoWater')))
        mud = track & ~wm if wm is not None else track
        res['owner'] = dict(track_pixels=int(track.sum()), water_pixels=int(wm.sum()) if wm is not None else None, mud_pixels=int(mud.sum()),
                            track_box_px=[[round(x, 1), round(y, 1)] for x, y in pts])
        lb = luma(base)
        lap_b = laplace(lb) * 255.0

        def measures(a):
            la = luma(a)
            return dict(mean_lum=round(float(la[mud].mean()), 4), highlight_share=round(float((la[mud] > 0.8).mean()), 4),
                        detail=round(float((laplace(la) * 255.0)[mud].mean()), 3))
        rows = dict(base=measures(base))
        for n in ['Repeat', 'PomRef', 'POM0', 'DeformDetail0', 'WaterMotion0', 'NoWater', 'EndRef', 'SlideUV0', 'Repeat2', 'FreshWet0', 'AllOff']:
            a = img(path(pre + 'Dbg_' + n))
            if a is None:
                continue
            r = measures(a)
            r['mean_abs_diff'] = round(float(np.abs(a - base)[mud].mean()), 3)
            er = img(path(pre + 'Dbg_EndRef'))
            if n in ('SlideUV0', 'Repeat2', 'FreshWet0', 'AllOff') and er is not None:
                r['vs_endref'] = round(float(np.abs(a - er)[mud].mean()), 3)
            r['diff_over_8_share'] = round(float((np.abs(a - base).max(-1) > 8.0)[mud].mean()), 4)
            rows[n] = r
        res['diagnosis'] = rows
        # MW1b: the mud's own pixels (the MudDiagnostic picture against the base: the mud turns to its diagnostic ramp) outside
        # the water; the mud glare gate (luminance over 0.9 <= 3 %), whole frame and its right half; the walls (cells over 22 deg,
        # projected) and the parallax's change on them (POM 0 against the picture right before it, <= 3/255).
        mm = img(path(pre + 'Dbg_MudMask'))
        if mm is not None:
            mudm = (np.abs(mm - base).max(-1) > 30.0) & ~(wm if wm is not None else np.zeros_like(track))
            lm = lb[mudm]
            right = mudm.copy(); right[:, :w // 2] = False
            res['mud_glare'] = dict(mud_pixels=int(mudm.sum()), over_09_share=round(float((lm > 0.9).mean()), 4),
                                    right_half_over_09_share=round(float((lb[right] > 0.9).mean()), 4) if right.any() else None,
                                    over_08_share=round(float((lm > 0.8).mean()), 4), mean_lum=round(float(lm.mean()), 4), gate='<= 0.03 over 0.9')
            res['mud_glare']['pass'] = bool(res['mud_glare']['over_09_share'] <= 0.03)
            Image.fromarray((mudm * 255).astype(np.uint8)).save(out / (base_name + '_mudmask.png'))
            walls = cell_mask(rep, 'owner_walls', cam_of(O), (h, w))
            ref, pom0 = img(path(pre + 'Dbg_PomRef')), img(path(pre + 'Dbg_POM0'))
            if walls is not None and ref is not None and pom0 is not None:
                wl = walls & mudm
                flat = mudm & ~walls
                dd = np.abs(pom0 - ref)
                res['walls_pom'] = dict(wall_pixels=int(wl.sum()), wall_mean_abs_diff=round(float(dd[wl].mean()), 3) if wl.any() else None,
                                        wall_over_8_share=round(float((dd.max(-1) > 8)[wl].mean()), 4) if wl.any() else None,
                                        flat_mean_abs_diff=round(float(dd[flat].mean()), 3) if flat.any() else None, gate='walls <= 3/255')
                res['walls_pom']['pass'] = bool(wl.any() and res['walls_pom']['wall_mean_abs_diff'] <= 3.0)
                Image.fromarray((wl * 255).astype(np.uint8)).save(out / (base_name + '_walls.png'))
        if wm is not None and wm.any():
            lw = lb[wm]
            res['glare'] = dict(water_pixels=int(wm.sum()), over_095_share=round(float((lw > 0.95).mean()), 4), over_090_share=round(float((lw > 0.90).mean()), 4),
                                mean_lum=round(float(lw.mean()), 4), gate='share of water pixels over 0.95 <= 0.05')
            res['glare']['pass'] = bool(res['glare']['over_095_share'] <= 0.05)
            a = img(path(pre + 'Dbg_WaterMotion0'))
            if a is not None:
                la = luma(a)[wm]
                res['glare_water_motion0'] = dict(over_095_share=round(float((la > 0.95).mean()), 4), mean_lum=round(float(la.mean()), 4))
        Image.fromarray((np.stack([track, wm if wm is not None else track, mud], -1) * 255).astype(np.uint8)).save(out / (base_name + '_masks.png'))

    # ---- the moving water ----
    t0 = img(path(pre + 'Water_t0'))
    mw = cell_mask(rep, 'water', cam_of(rep['frames']['water']), t0.shape[:2]) if t0 is not None else None
    if mw is None:
        mw = water_mask(t0, img(path(pre + 'Water_NoWater')))
    if mw is not None and mw.any():
        res['motion'] = dict(water_pixels=int(mw.sum()), gate='mean |dL| >= 2/255 and >= 15 % of the water over 4/255')
        for label, names in [('motion1', [pre + 'Water_t0', pre + 'Water_t05', pre + 'Water_t10']), ('motion0', ['MW_Water_Motion0_t0', 'MW_Water_Motion0_t05'])]:
            frames = [img(path(n)) for n in names]
            if any(f is None for f in frames):
                continue
            pairs = []
            for a, b in zip(frames, frames[1:]):
                d = np.abs(luma(b) - luma(a))[mw] * 255.0
                pairs.append(dict(mean_abs_dl=round(float(d.mean()), 3), share_over_4=round(float((d > 4.0).mean()), 4)))
            ok = all(p['mean_abs_dl'] >= 2.0 and p['share_over_4'] >= 0.15 for p in pairs)
            res['motion'][label] = dict(pairs=pairs, pass_=ok)
        Image.fromarray((mw * 255).astype(np.uint8)).save(out / (pre + 'Water_mask.png'))

    # ---- PBR: the close bank, dry and wet ----
    fix = None
    calib = out / (pre + 'PBR_Calib')
    r, how = load_buffer(calib, 'Roughness')
    if r is not None:
        hh, ww = r.shape[:2]
        med = float(np.median(r[int(hh * 0.55):int(hh * 0.95), int(ww * 0.3):int(ww * 0.7), 0]))
        fix = 'linear' if abs(med - 0.9) < 0.03 else ('srgb-decoded' if abs(med - 0.787) < 0.03 else 'unknown')
        res['encoding'] = dict(file_type=how, gravel_roughness_median=round(med, 3), verdict=fix)
    res['pbr'] = []
    for label, dump, pair in [('dry', pre + 'PBR_Close_Dry', (pre + 'Mud_Close', pre + 'Mud_Close_NoWater')),
                              ('wet', pre + 'PBR_Close_Wet', (pre + 'Mud_Close_Wet', pre + 'Mud_Close_Wet_NoWater'))]:
        rough, how = load_buffer(out / dump, 'Roughness')
        colour, _ = load_buffer(out / dump, 'BaseColor')
        normal, _ = load_buffer(out / dump, 'WorldNormal')
        if rough is None or colour is None:
            res['pbr'].append(dict(name=dump, missing=True))
            continue
        if fix == 'srgb-decoded':
            rough, colour = srgb_encode(rough), srgb_encode(colour)
        hh, ww = rough.shape[:2]
        sel = np.zeros((hh, ww), bool)
        sel[int(hh * 0.25):int(hh * 0.95), int(ww * 0.15):int(ww * 0.85)] = True
        cc = (rep.get('close') or {}).get('camera')
        wmask = cell_mask(rep, 'close' if label == 'dry' else 'close_wet', cam_of(cc), rough.shape[:2]) if cc else None
        if wmask is None:
            wmask = water_mask(img(path(pair[0])), img(path(pair[1])))
        outside = sel & ~wmask if wmask is not None and wmask.shape == sel.shape else sel
        rr = rough[..., 0][outside]
        c = colour[outside]
        row = dict(name=dump, condition=label, pixels=int(outside.sum()), water_pixels_in_box=int((sel & wmask).sum()) if wmask is not None else None,
                   rough_p5_50_95=pct(rr, [5, 50, 95]), rough_under_050=round(float((rr < 0.5).mean()), 4),
                   rough_box_p5_all=pct(rough[..., 0][sel], [5]),
                   base_luminance_mean=round(float(lum(c).mean()), 4))
        row['in_soil_band'] = bool(SOIL_LO <= row['base_luminance_mean'] <= SOIL_HI)
        if label == 'wet':
            row['pass_rough_p5'] = bool(row['rough_p5_50_95'][0] >= 0.5)
            row['pass_rough_p5_8bit'] = bool(row['rough_p5_50_95'][0] >= 0.496)
        res['pbr'].append(row)
        save_view(rough[..., 0], out / (dump + '_Roughness_view.png'))
        if normal is not None:
            Image.fromarray((np.clip(normal * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)).save(out / (dump + '_WorldNormal_view.png'))
    # The owner frame's buffers: views only.
    for dname in [pre + 'Dbg_Buffers']:
        rough, _ = load_buffer(out / dname, 'Roughness')
        normal, _ = load_buffer(out / dname, 'WorldNormal')
        if rough is not None:
            if fix == 'srgb-decoded':
                rough = srgb_encode(rough)
            save_view(rough[..., 0], out / (dname + '_Roughness_view.png'))
            if base is not None and rough.shape[:2] == base.shape[:2]:
                rr = rough[..., 0][mud]
                res.setdefault('owner_buffers', {})['track_mud_rough_p5_50_95'] = pct(rr, [5, 50, 95])
        if normal is not None:
            Image.fromarray((np.clip(normal * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8)).save(out / (dname + '_WorldNormal_view.png'))
            if base is not None and normal.shape[:2] == base.shape[:2]:
                nz = normal[..., 2][mud]
                # How smooth the normals are: the mean angle between neighbours (deg), over the track's mud.
                n = normal / np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-6)
                dot = np.clip((n[1:, :-1] * n[:-1, :-1]).sum(-1), -1, 1)
                ang = np.degrees(np.arccos(dot))
                res.setdefault('owner_buffers', {}).update(normal_z_mean=round(float(nz.mean()), 4),
                                                           neighbour_angle_deg_mean=round(float(ang[mud[:-1, :-1]].mean()), 3))
    # The test rings on settled water: the pixels the rings change (on against off, the same frame), in and out of the water.
    on, off = img(path('MW_Rings_Test')), img(path('MW_Rings_Test_Off'))
    if on is not None and off is not None and mw is not None and mw.shape == on.shape[:2]:
        dd = np.abs(on - off).max(-1)
        res['rings_test'] = dict(water_pixels=int(mw.sum()), changed_over_8_in_water=int((dd > 8)[mw].sum()), changed_over_8_outside=int((dd > 8)[~mw].sum()),
                                 mean_abs_dl_in_water=round(float(np.abs(luma(on) - luma(off))[mw].mean() * 255.0), 3))
    # The fresh rut's pool (after): WaterMotion 1 and 0.
    t0 = img(path('MW_Water2_t0'))
    if t0 is not None and (rep.get('frames') or {}).get('water2'):
        m2 = cell_mask(rep, 'water2', cam_of(rep['frames']['water2']), t0.shape[:2])
        if m2 is not None and m2.any():
            res['motion2'] = dict(water_pixels=int(m2.sum()))
            for label, names in [('motion1', ['MW_Water2_t0', 'MW_Water2_t05', 'MW_Water2_t10']), ('motion0', ['MW_Water2_Motion0_t0', 'MW_Water2_Motion0_t05'])]:
                frames = [img(path(n)) for n in names]
                if any(f is None for f in frames):
                    continue
                pairs = []
                for a2, b2 in zip(frames, frames[1:]):
                    d = np.abs(luma(b2) - luma(a2))[m2] * 255.0
                    pairs.append(dict(mean_abs_dl=round(float(d.mean()), 3), share_over_4=round(float((d > 4.0).mean()), 4)))
                res['motion2'][label] = dict(pairs=pairs, pass_=all(q['mean_abs_dl'] >= 2.0 and q['share_over_4'] >= 0.15 for q in pairs))
    # The debug set on the fresh rut's bank: the frame's middle (15-85 % across, 25-95 % down) outside the water.
    cb = img(path(pre + 'Mud_Close_NoWater'))   # the debug set is taken with the water hidden
    cc = (rep.get('close') or {}).get('camera')
    if cb is not None and cc:
        hh, ww = cb.shape[:2]
        box = np.zeros((hh, ww), bool)
        box[int(hh * 0.25):int(hh * 0.95), int(ww * 0.15):int(ww * 0.85)] = True
        cm = cell_mask(rep, 'close', cam_of(cc), (hh, ww))
        sel = box & ~cm if cm is not None else box
        lb = luma(cb)
        rows = dict(base=dict(pixels=int(sel.sum()), mean_lum=round(float(lb[sel].mean()), 4), highlight_share=round(float((lb[sel] > 0.8).mean()), 4),
                              detail=round(float((laplace(lb) * 255.0)[sel].mean()), 3)))
        for n in ['Repeat', 'SlideUV0', 'FreshWet0', 'POM0', 'DeformDetail0', 'Repeat2']:
            a2 = img(path(pre + 'Dbg_Close_' + n))
            if a2 is None:
                continue
            la = luma(a2)
            rows[n] = dict(mean_lum=round(float(la[sel].mean()), 4), highlight_share=round(float((la[sel] > 0.8).mean()), 4),
                           detail=round(float((laplace(la) * 255.0)[sel].mean()), 3), mean_abs_diff=round(float(np.abs(a2 - cb)[sel].mean()), 3),
                           diff_over_8_share=round(float((np.abs(a2 - cb).max(-1) > 8.0)[sel].mean()), 4))
        res['diagnosis_close'] = rows
    # MW1b item 6: the rings frame on Standard / Firm.
    rr = rep.get('rings') or {}
    res['rings_frame'] = dict(puddle=rr.get('puddle'), shot_kmh=rr.get('shot_kmh'), counts_at_shot=rr.get('counts_at_shot'), reached=rr.get('reached_shot'),
                              describe=rr.get('rings_describe'))
    # MW1b item 4 (the diag run): each pool layer off against the reference right before it, the frame's middle.
    if tag == 'diag':
        rows = {}
        for k, n in enumerate(['Mottle0', 'Ruffle0', 'Froth0', 'Flecks0', 'Drift0', 'Ripple0', 'Motion0']):
            a2, r2 = img(path('MW1b_Pool_' + n)), img(path('MW1b_Pool_Ref%d' % k))
            if a2 is None or r2 is None:
                continue
            hh, ww = a2.shape[:2]
            sl = (slice(int(hh * 0.15), int(hh * 0.85)), slice(int(ww * 0.1), int(ww * 0.9)))
            la, lr = luma(a2)[sl], luma(r2)[sl]
            rows[n] = dict(mean_abs_diff=round(float(np.abs(a2 - r2)[sl].mean()), 3), detail_ref=round(float((laplace(lr) * 255).mean()), 3),
                           detail_off=round(float((laplace(la) * 255).mean()), 3), lum_sd_ref=round(float(lr.std() * 255), 3), lum_sd_off=round(float(la.std() * 255), 3))
        res['pool_layers'] = rows
    res['rings'] = dict(drive=(rep.get('drive') or {}).get('counts_at_shot'), drive_end=(rep.get('drive') or {}).get('counts_end'),
                        drive_start=(rep.get('drive') or {}).get('counts_start'), shot_kmh=(rep.get('drive') or {}).get('shot_kmh'),
                        walk_start=(rep.get('walk') or {}).get('counts_start'), walk_end=(rep.get('walk') or {}).get('counts_end'),
                        walk_skipped=(rep.get('walk') or {}).get('skipped'),
                        drive_describe=(rep.get('drive') or {}).get('rings_describe'), walk_describe=(rep.get('walk') or {}).get('rings_describe'))
    (out / ('mw-numbers-%s.json' % tag)).write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1)[:6000])
    print('MUD_WATER_NUMBERS_OK')


if __name__ == '__main__':
    main()
