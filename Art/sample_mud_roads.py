"""Mud roads MRD1 (docs/MUD_ROADS_PLAN.md): reads Art/Export/MudRoads/check-mrd.json (Art/Unreal/check_mud_water.py, GT_MW_TAG mrd) and
prints the gates - item 1's per MudRoad section (the patches' DescribeMudRoad: tracks, the depth histograms, crossings and heading
spread per 20 m window, the puddle share of the road), item 2's mud glare in the MW owner frame (mud pixels over 0.9 luminance
<= 3 %, sample_mud_water.py's mask: the MudDiagnostic picture against the base, outside the projected water cells) and the water's
motion (mean |dL| >= 2/255 and >= 15 % of the water over 4/255, frames 0.5 s apart) - and every picture. No timing, no cost.
    python Art/sample_mud_roads.py Art/Export/MudRoads/check-mrd.json
Writes check-mrd-numbers.json beside the report."""
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sample_mud_water import img, luma, cell_mask, cam_of  # noqa: E402


def main():
    rp = Path(sys.argv[1])
    rep = json.loads(rp.read_text())
    out = rp.parent
    res = dict(report=str(rp), error=rep.get('error'))

    def path(n):
        return out / (n + '.png')
    # Item 1: the gates per MudRoad section.
    roads = []
    for key, level in [('mud_roads', 'L_MudVariants'), ('mud_roads2', 'L_MudDrive')]:
        for r in rep.get(key, []):
            a = r.get('depth_asked', {})
            s = r.get('depth_settled', {})
            roads.append(dict(level=level, section=r.get('section'), tracks=r.get('tracks'), visible_m=r.get('visible_m'), layout_try=r.get('layout_try'),
                              crossings_per_20m=r.get('crossings_per_20m'), crossings_min_window=r.get('crossings_min_window_per_20m'),
                              crossings_pass=(r.get('crossings_min_window_per_20m') or 0) >= 2.0,   # MRD1b: relaxed from 3
                              heading_sd_min_window_deg=r.get('heading_sd_min_window_deg'), heading_pass=(r.get('heading_sd_min_window_deg') or 0) >= 4.0,
                              depth_asked=a, depth_settled=s, puddle_share=r.get('puddle_share'), puddle_target=r.get('puddle_target'),
                              puddle_pass=0.08 <= (r.get('puddle_share') or 0) <= 0.15, puddle_basins=r.get('puddle_basins'),
                              churn_zones=r.get('churn_zones'), clods=r.get('clods'), chunks=r.get('chunks'), debris=r.get('debris'),
                              debris_per_m2=r.get('debris_per_m2'), tread_tracks=r.get('tread_tracks'), tread_share=r.get('tread_share_of_present'),
                              wall_cells=r.get('wall_cells'), lip_block_cells=r.get('lip_block_cells'), lip_lean_cells=r.get('lip_lean_cells'),
                              pools_per_5m_max=r.get('pools_per_5m_max'), pools_pass=(r.get('pools_per_5m_max') or 0) <= 2, pool_runs=r.get('pool_runs'),
                              pool_run_mean_m=r.get('pool_run_mean_m'), cells_lifted_to_table=r.get('cells_lifted_to_table'), width_over_tyre=r.get('width_over_tyre'),
                              width_cm=r.get('width_cm'), stretches=r.get('stretches'), stretch_ends_in_view=r.get('stretch_ends_in_view'),
                              stretch_ends_largest_gap=r.get('stretch_ends_largest_gap'),
                              pool_run_m=r.get('pool_run_m'), pool_run_cv=r.get('pool_run_cv'), pool_gap_m=r.get('pool_gap_m'), pool_gap_cv=r.get('pool_gap_cv'),
                              cv_pass=(r.get('pool_run_cv') or 0) >= 0.4 and (r.get('pool_gap_cv') or 0) >= 0.4, pools_per_5m_line_max=r.get('pools_per_5m_line_max'),
                              runs_meeting_a_track=r.get('runs_meeting_a_track'), runs_joined_across=r.get('runs_joined_across')))
    res['roads'] = roads
    # Item 2: the mud glare in the MW owner frame.
    base = img(path('MW_After_OnFoot'))
    mm = img(path('MW_Dbg_MudMask'))
    O = rep.get('frames', {}).get('owner')
    if base is not None and mm is not None and O:
        h, w = base.shape[:2]
        wm = cell_mask(rep, 'owner', cam_of(O), (h, w))
        mudm = (np.abs(mm - base).max(-1) > 30.0) & ~(wm if wm is not None else np.zeros((h, w), bool))
        lb = luma(base)
        lm = lb[mudm]
        res['mud_glare'] = dict(mud_pixels=int(mudm.sum()), over_09_share=round(float((lm > 0.9).mean()), 4) if lm.size else None,
                                over_08_share=round(float((lm > 0.8).mean()), 4) if lm.size else None, mean_lum=round(float(lm.mean()), 4) if lm.size else None,
                                gate='<= 0.03 over 0.9')
        res['mud_glare']['pass'] = bool(lm.size and res['mud_glare']['over_09_share'] <= 0.03)
        if wm is not None and wm.any():
            lw = lb[wm]
            res['water_glare'] = dict(water_pixels=int(wm.sum()), over_095_share=round(float((lw > 0.95).mean()), 4), mean_lum=round(float(lw.mean()), 4))
    # Item 2: the water's motion.
    t0 = img(path('MW_Water_t0'))
    Wc = rep.get('frames', {}).get('water')
    if t0 is not None and Wc:
        mw = cell_mask(rep, 'water', cam_of(Wc), t0.shape[:2])
        if mw is not None and mw.any():
            frames = [img(path(n)) for n in ['MW_Water_t0', 'MW_Water_t05', 'MW_Water_t10']]
            pairs = []
            for a, b in zip(frames, frames[1:]):
                if a is None or b is None:
                    continue
                d = np.abs(luma(b) - luma(a))[mw] * 255.0
                pairs.append(dict(mean_abs_dl=round(float(d.mean()), 3), share_over_4=round(float((d > 4.0).mean()), 4)))
            res['motion'] = dict(water_pixels=int(mw.sum()), pairs=pairs, gate='mean |dL| >= 2/255 and >= 15 % of the water over 4/255',
                                 pass_=bool(pairs) and all(p['mean_abs_dl'] >= 2.0 and p['share_over_4'] >= 0.15 for p in pairs))
    # MRD1b item 1: the puddle look in MRD_Ref4 - the water pixels (its projected water cells) against the wet mud (a ring 4-15 px
    # round the water, under the horizon) and the sky (over the horizon row, bluer than red): the water's median luminance between
    # the wet mud's and the sky's, and its median colour R > G > B.
    r4 = img(path('MRD_Ref4'))
    C4 = rep.get('frames', {}).get('ref4')
    if r4 is not None and C4:
        h, w = r4.shape[:2]
        wm = cell_mask(rep, 'ref4', cam_of(C4), (h, w))
        if wm is not None and wm.any():
            lum = luma(r4)
            e, l = np.array(C4['eye'], float), np.array(C4['look'], float)
            d = l - e
            pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
            f = (w / 2) / math.tan(math.radians(C4['fov']) / 2)
            hr = int(h / 2 - f * math.tan(-pitch))
            above = np.arange(h)[:, None] < hr - 4
            sky = np.broadcast_to(above, (h, w)) & (r4[..., 2] > r4[..., 0])
            m = Image.fromarray((wm * 255).astype(np.uint8))
            outer = np.asarray(m.filter(ImageFilter.MaxFilter(31))) > 0
            inner = np.asarray(m.filter(ImageFilter.MaxFilter(9))) > 0
            mud = outer & ~inner & ~np.broadcast_to(above, (h, w))
            med = lambda a, k: round(float(np.median(a[k])), 4) if k.any() else None
            rgb = [round(float(np.median(r4[..., c][wm])), 1) for c in range(3)]
            res['puddle_look'] = dict(water_pixels=int(wm.sum()), wet_mud_pixels=int(mud.sum()), sky_pixels=int(sky.sum()), horizon_row=hr,
                                      water_median_lum=med(lum, wm), wet_mud_median_lum=med(lum, mud), sky_median_lum=med(lum, sky), water_median_rgb=rgb,
                                      gate='wet mud < water < sky (median luminance), water R > G > B')
            ok = None not in (res['puddle_look']['wet_mud_median_lum'], res['puddle_look']['sky_median_lum'])
            res['puddle_look']['pass'] = bool(ok and res['puddle_look']['wet_mud_median_lum'] < res['puddle_look']['water_median_lum'] < res['puddle_look']['sky_median_lum']
                                              and rgb[0] > rgb[1] > rgb[2])
            Image.fromarray((np.stack([wm, mud, sky], -1) * 255).astype(np.uint8)).save(out / 'MRD_Ref4_masks.png')
    res['camera_fixes'] = rep.get('camera_fixes')
    res['chase'] = {k: v for k, v in (rep.get('chase') or {}).items() if k != 'samples'}
    res['pictures'] = [p for p in rep.get('images', []) if Path(p).name.startswith('MRD_')]
    (out / 'check-mrd-numbers.json').write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1))
    print('MUD_ROADS_NUMBERS_OK')


if __name__ == '__main__':
    main()
