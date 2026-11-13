"""Read-only survey of the existing native bed and mean water shape.

Writes diagnostics only; never modifies heights, flow bakes or Unreal assets.
Cross sections sample the Landscape's actual triangle convention. The water
line is the saved mean field, not a measurement of runtime wave displacement.
"""
from pathlib import Path
import json
import hashlib

import numpy as np
from scipy.ndimage import map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Art/Export/BenmoreGaea'
OUT = BASE / 'RiverScale/ChannelAudit'


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    path = BASE / 'RiverLife/height_local_south_up.f32'
    raw = path.read_bytes()
    height = np.frombuffer(raw, dtype='<f4').reshape(2017, 2017)
    with np.load(BASE / 'RiverScale/water-domain.npz') as src:
        data = {key: src[key] for key in src.files}
    x, y = data['x'], data['y']
    cell = float(x[1] - x[0])

    def sample(key, xy):
        coords = [(xy[..., 1] - y[0]) / cell, (xy[..., 0] - x[0]) / cell]
        return map_coordinates(data[key].astype(float), coords, order=1, mode='constant')

    def bed(xy):
        uv = (xy + 1250) * 2016 / 2500
        assert np.all((uv >= 0) & (uv < 2016)), 'Outside native Landscape'
        ij = uv.astype(int)
        i, j = ij[..., 0], ij[..., 1]
        s, t = uv[..., 0] - i, uv[..., 1] - j
        q, r, v, w = height[j, i], height[j, i+1], height[j+1, i], height[j+1, i+1]
        return np.where(s >= t, q+(r-q)*s+(w-r)*t, q+(w-v)*s+(v-q)*t)

    crossings = json.loads((BASE / 'RiverLife/assets.json').read_text())['crossings']
    yy, xx = np.meshgrid(y, x, indexing='ij')
    eligible = data['wet'] & (xx > -1250)
    indices = np.argwhere(eligible)
    points = np.c_[xx[eligible], yy[eligible]]
    sections = []
    targets = [(crossings[0]['name'], crossings[0]['center_m'][:2]),
               ('Bend upstream of ford', [-610, 240]),
               (crossings[1]['name'], crossings[1]['center_m'][:2])]
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout='constrained')
    fig.suptitle('Existing river: bed and mean-surface audit', fontsize=18)
    fig.supxlabel('Cross-section heights are exaggerated; vertical scales differ. Saved data, not a runtime capture.', fontsize=10)
    for ax, (name, target) in zip(axes.flat, targets):
        k = np.argmin(np.linalg.norm(points - target, axis=1))
        j, i = indices[k]
        centre = points[k]
        flow = np.array([data['vx'][j, i], data['vy'][j, i]])
        assert np.linalg.norm(flow) > .02, 'Cross section needs a meaningful flow direction'
        along = flow / np.linalg.norm(flow)
        across = np.array([-along[1], along[0]])
        distance = np.linspace(-12, 12, 481)
        xy = centre + distance[:, None] * across
        ground = bed(xy)
        mean = sample('mean', xy)
        wet = (sample('wet', xy) > .5) & (mean > ground + .015)
        # Use only the connected wet interval containing the selected centre.
        middle = len(distance) // 2
        assert wet[middle], 'Chosen cross-section centre is not wet'
        lo = hi = middle
        while lo > 0 and wet[lo-1]:
            lo -= 1
        while hi+1 < len(wet) and wet[hi+1]:
            hi += 1
        active = np.zeros_like(wet)
        active[lo:hi+1] = True
        baseline = mean[middle]
        depth = mean[active] - ground[active]
        row = dict(name=name, centre_m=centre.tolist(), cross_axis=across.tolist(),
                   wet_width_m=float(distance[hi]-distance[lo]),
                   water_transverse_range_cm=float(np.ptp(mean[active])*100),
                   depth_p10_p50_p90_cm=(np.percentile(depth, [10, 50, 90])*100).tolist(),
                   min_max_depth_cm=[float(depth.min()*100), float(depth.max()*100)])
        sections.append(row)
        ax.plot(distance, ground-baseline, color='#897450', lw=2, label='Native bed / banks')
        ax.plot(distance, np.where(active, mean-baseline, np.nan), color='#277b98', lw=2,
                label='Baked mean water surface')
        ax.fill_between(distance, ground-baseline, mean-baseline, where=active,
                        color='#8ccbd8', alpha=.55)
        ax.set(title=f'{name} | wetted width {row["wet_width_m"]:.1f} m',
               xlabel='Across the channel (m)', ylabel='Height relative to centre water level (m)')
        ax.grid(alpha=.2)
        ax.legend(fontsize=8, loc='upper left')
    ax = axes.flat[3]
    local = eligible & (xx > -735) & (xx < -560) & (yy > 110) & (yy < 305)
    # Crop before plotting to make the source sample spacing legible.
    js, ii = np.where(local)
    crop = np.s_[js.min()-5:js.max()+6, ii.min()-5:ii.max()+6]
    im = ax.pcolormesh(xx[crop], yy[crop], np.where(data['wet'][crop], data['depth'][crop], np.nan),
                       shading='nearest', cmap='Blues', vmin=0, vmax=.6)
    for row in sections[:2]:
        c, a = np.array(row['centre_m']), np.array(row['cross_axis'])
        ends = c + np.array([-12, 12])[:, None]*a
        ax.plot(ends[:, 0], ends[:, 1], color='#b45134', lw=1)
    ax.set(title='Ford reach: current baked wet footprint', xlabel='World X (m)', ylabel='World Y (m)')
    ax.set_aspect('equal')
    fig.colorbar(im, ax=ax, label='Baked water depth (m)', shrink=.8)
    fig.savefig(OUT / 'Channel_Audit.png', dpi=145)
    plt.close(fig)
    depth = data['depth'][eligible]
    report = dict(ok=True, source_height_sha256=hashlib.sha256(raw).hexdigest(),
                  basis='Saved mean domain and native bed; not a runtime or surveyed-hydrology result',
                  mean_grid_spacing_m=cell, native_grid_spacing_m=2500/2016,
                  native_wet_cell_count=int(eligible.sum()),
                  native_water_depth_p10_p50_p90_cm=(np.percentile(depth, [10, 50, 90])*100).tolist(),
                  fraction_native_wet_area_shallower_than_20cm=float(np.mean(depth < .2)),
                  sections=sections, assets_modified=False,
                  caution='Cross-section wet extent is a sampled mask, not a legal or surveyed bank boundary.')
    assert path.read_bytes() == raw
    (OUT / 'channel-audit.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    run()
