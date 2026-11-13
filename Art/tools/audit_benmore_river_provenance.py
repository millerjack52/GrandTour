"""Read-only Gaea/channel provenance audit. Writes diagnostics, never terrain/assets."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.ndimage import map_coordinates, distance_transform_edt, gaussian_filter
from convert_benmore_gaea import read_height
from prepare_benmore_gaea import resample
import reshape_benmore_channel as channel

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Art/Export/BenmoreGaea'
OUT = BASE / 'review/RiverProvenance'
N = 2017
DX = 2500 / (N - 1)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summary(v):
    v = np.asarray(v)
    return {'count': int(v.size), 'p0_p10_p50_p90_p100': np.percentile(v, [0, 10, 50, 90, 100]).tolist()}


def sample(a, xy):
    return map_coordinates(a, [(xy[:, 1] + 1250) / DX, (xy[:, 0] + 1250) / DX], order=1, mode='nearest')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source_paths = [BASE / 'candidate/H_Benmore_Gaea_2017.r16',
                    BASE / 'ChannelShape/H_ChannelShape_2017.r16',
                    ROOT / 'Content/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview.umap',
                    ROOT / 'Content/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive.umap']
    hashes = {str(p): sha(p) for p in source_paths}
    gaea = np.fromfile(BASE / 'candidate/height_local_south_up.f32', '<f4').reshape(N, N)
    installed = np.fromfile(BASE / 'ChannelShape/height_local_south_up.f32', '<f4').reshape(N, N)
    masks = {name: resample(read_height(BASE / ('return/' + name + '.tif'))[::-1], N)
             for name in ['M_Rivers', 'M_Depth', 'H_WaterSurface']}
    edit = resample(read_height(BASE / 'input/M_FirstPass_Edit_2048.png')[::-1], N)
    protect = np.load(BASE / 'source/protect_2017.npy')
    selected = (edit > .3) & (protect < .5)
    river = (masks['M_Rivers'] > .5) & selected
    assert river.any()
    surface = masks['H_WaterSurface'] * 512 + 256 - 360.531005859375
    carve = (gaea - installed > .1) & selected
    distance = distance_transform_edt(~river) * DX
    paths = np.load(BASE / 'ChannelShape/original-paths.npz')
    station_reports = []
    for k in paths.files:
        p = paths[k]
        arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(p[:, :2], axis=0), axis=1))]
        in_native = (p[:, 0] >= -1250) & (p[:, 0] <= 1250)
        sections = []
        for title, lo, hi in [('upper', 0, 500), ('crossing_reach', 500, 800), ('lower', 800, 1320)]:
            q = p[(arc >= lo) & (arc <= hi)]
            length = float(np.linalg.norm(np.diff(q[:, :2], axis=0), axis=1).sum())
            direct = float(np.linalg.norm(q[-1, :2] - q[0, :2]))
            sections.append({'reach': title, 'length_m': length, 'fall_m': float(q[0, 2] - q[-1, 2]),
                             'mean_profile_grade': float((q[0, 2] - q[-1, 2]) / length),
                             'sinuosity_length_over_endpoint_distance': length / direct})
        station_reports.append({'path': k, 'length_m': float(arc[-1]),
                                'distance_from_current_centerline_to_gaea_mask_m': summary(sample(distance, p[in_native, :2])),
                                'sections': sections})
    inspect = BASE / 'review/native-inspection'
    inspection = {}
    if (inspect / 'H_ChannelBed.tif').exists():
        pairs = ['H_InputCheck', 'H_Eroded', 'H_WaterSurface', 'M_Rivers', 'M_Depth']
        matching = {name: sha(inspect / (name + '.tif')) == sha(BASE / 'return' / (name + '.tif')) for name in pairs}
        raw = resample(read_height(inspect / 'H_ChannelBed.tif')[::-1], N) * 512 + 256 - 360.531005859375
        inspection = {'same_build_data_as_return': matching,
                      'raw_surface_minus_raw_channelbed_m': summary((surface - raw)[river]),
                      'final_imported_bed_minus_raw_channelbed_m': summary((gaea - raw)[river])}
    graph = json.loads((BASE / 'Benmore_01_RiverStudy.terrain').read_text())
    nodes = graph['Assets']['$values'][0]['Terrain']['Nodes']
    river_node = next(n for n in nodes.values() if n['Name'] == '04_ChannelStudy')
    blend = next(n for n in nodes.values() if n['Name'] == '06_ProtectedTerrain')
    report = {'ok': True, 'scope': 'Read-only provenance/geometry diagnosis; no candidate or map change',
              'gaea_graph': str(BASE / 'Benmore_01_RiverStudy.terrain'),
              'gaea_river_controls': {k: river_node[k] for k in ['Water', 'Width', 'Depth', 'Downcutting', 'Headwaters', 'RiverValleyWidth', 'RenderSurface', 'Seed']},
              'final_blend_ratio': blend['Ratio'], 'final_blend_mask': 'M_FirstPass_Edit_2048.png',
              'additional_import_protection': 'delta multiplied by (1-protect_2017)',
              'gaea_mask_area_m2': float(river.sum() * DX ** 2),
              'new_native_carve_area_above_10cm_m2': float(carve.sum() * DX ** 2),
              'fraction_new_carve_inside_gaea_mask': float(river[carve].mean()),
              'gaea_surface_minus_final_imported_bed_m': summary((surface - gaea)[river]),
              'gaea_depth_data_times_512_m': summary(masks['M_Depth'][river] * 512),
              'current_paths': station_reports, 'raw_inspection': inspection,
              'current_carve_origin': 'Priority-flood parent paths on a 3.75 m grid, then authored floor/width cuts; independent from Gaea M_Rivers topology',
              'current_water_bake_scope': 'Hydraulics over fixed authored bed; no sediment transport or bank migration',
              'hashes_before': hashes,
              'source_files_unchanged': all(sha(Path(p)) == value for p, value in hashes.items()),
              'limitations': ['Gaea saved starter and returned exports are provenance inputs; no later edited user graph was found in the project.',
                             'Sinuosity and mask overlap do not establish an accepted natural channel form.',
                             'Gaea depth/surface data are not a calibrated catchment discharge or Unreal gameplay simulation.']}
    assert report['source_files_unchanged']
    (OUT / 'provenance-report.json').write_text(json.dumps(report, indent=2))
    plot(gaea, installed, masks['M_Rivers'], selected, paths)
    print(json.dumps(report, indent=2))


def plot(gaea, installed, river, selected, paths):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    ys, xs = np.linspace(-1250, 1250, N), np.linspace(-1250, 1250, N)
    xlim, ylim = (-850, -250), (30, 780)
    i0, i1 = np.searchsorted(xs, xlim)
    j0, j1 = np.searchsorted(ys, ylim)
    crop = np.s_[j0:j1+1, i0:i1+1]
    x, y = xs[i0:i1+1], ys[j0:j1+1]
    ext = [x[0], x[-1], y[0], y[-1]]
    light = LightSource(315, 42)
    fig, axes = plt.subplots(1, 3, figsize=(15, 8), layout='constrained', sharex=True, sharey=True)
    for ax, h, title in zip(axes, [gaea, gaea, installed],
                           ['Returned Gaea terrain + Gaea river mask', 'Later drainage paths over Gaea terrain', 'Current native incision below Gaea terrain']):
        shade = light.hillshade(gaussian_filter(h[crop], .6), vert_exag=1, dx=DX, dy=DX)
        ax.imshow(shade, origin='lower', extent=ext, cmap='gray', vmin=0, vmax=1)
        ax.set(title=title, xlabel='East / X (m)', xlim=xlim, ylim=ylim, aspect='equal')
    axes[0].contour(x, y, river[crop] * selected[crop], [.5], colors=['#29c7ff'], linewidths=1)
    axes[1].contour(x, y, river[crop] * selected[crop], [.5], colors=['#29c7ff'], linewidths=.7, alpha=.65)
    for k in paths.files:
        p = paths[k]
        axes[1].plot(p[:, 0], p[:, 1], color='#ffb35b', lw=1.4)
    incision = gaea - installed
    masked = np.ma.masked_where(incision[crop] < .10, incision[crop])
    im = axes[2].imshow(masked, origin='lower', extent=ext, cmap='YlOrRd', vmin=.1, vmax=1.1, alpha=.85)
    crossings = json.loads((BASE / 'RiverLife/assets.json').read_text())['crossings']
    for ax in axes:
        for c in crossings:
            p = c['center_m']
            ax.plot(p[0], p[1], '+', color='white', ms=8)
            ax.text(p[0]+5, p[1], c['name'], color='white', fontsize=8)
    axes[0].set_ylabel('North / Y (m)')
    fig.colorbar(im, ax=axes[2], label='Later native cut (m)', shrink=.65)
    fig.suptitle('River provenance diagnosis — data visualization, not an Unreal render or proposed replacement')
    fig.savefig(OUT / 'Gaea_vs_Current_Channel.png', dpi=145)
    plt.close(fig)


if __name__ == '__main__':
    main()
