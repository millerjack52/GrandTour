"""Ground relief GR1 (docs/GROUND_RELIEF_PLAN.md GR1): the test strips' relief numbers in one place, for setup_mud_variants.py,
setup_deformable_gravel.py and setup_live_mud_drive.py. The owner's numbers (proposals, named after the drive):
- the land: base_amplitude_m 3.5 at base_wavelength_m 60, 4 octaves, persistence 0.5 (item 1);
- the relief: 3 octaves (RoughnessOctaves) at 6, 3 and 2 m (RoughnessWavelengthM 6), scrub 0.45 m, bog 0.22 m (item 2);
- the hummocks: 8 per 100 m^2 on a 12 m cluster noise x0.1-2.2, radius 1.0-2.8 m, height 0.15-0.5 m, rim +-25 %, crest 30 % (item 3);
- each bog section's PreChurnScale 1 (item 4, bog_deform());
- the grass: height x0.55-1.45 (3 m and 0.8 m), bare gaps 10-25 % (2 m), lean +-12 deg, tussocks x2 on hummock crests (item 5).
Every number 0 (or the struct's default) gives the strips' ground before GR1.
Route drivability (item 1, the amplitude lowered only where a gate fails): L_MudDrive's route grade p95 away from its ford was
11.02 % at 3.5 m (asked at most 10); GrandTour.Relief.Strips' sweep put it at 10.02 at 3.0 m and 9.76 at 2.75 m, so L_MudDrive takes
2.75 m (MUD_DRIVE_AMPLITUDE_M). L_MudVariants (7.32 %) and L_GravelDeform (5.25 %) keep 3.5 m."""

import json
import unreal as u

LAND = dict(base_amplitude_m=3.5, base_wavelength_m=60., octaves=4, persistence=.5)
RELIEF = dict(roughness_octaves=3, roughness_wavelength_m=6., scrub_roughness_m=.45, mud_roughness_m=.22)
HUMMOCKS = dict(density=8., cluster_wavelength_m=12., cluster_min=.1, cluster_max=2.2, radius_min_m=1., radius_max_m=2.8, radius_power=2.,
                height_min_m=.15, height_max_m=.5, rim_warp=.25, crest_offset=.3, seed=0)
GRASS = dict(height_jitter=.45, height_wavelength_m=3., height_fine_wavelength_m=.8, bare_share_min=.10, bare_share_max=.25, bare_wavelength_m=2.,
             bare_share_wavelength_m=12., tilt_degrees=12., slope_follow=.5, crest_tussock_weight=2., seed=0)
PRE_CHURN_SCALE = 1.
MUD_DRIVE_AMPLITUDE_M = 2.75


def _props(obj, values):
    for key, value in values.items():
        obj.set_editor_property(key, value)
    return obj


def apply_relief(spec, **land):
    """The land, the relief octaves, the hummocks and the grass variation onto a strip's GTTerrainSpec (in place); land= overrides
    LAND's numbers for one strip (L_MudDrive's base_amplitude_m 2.75: the route-drivability rule, below)."""
    _props(spec, dict(LAND, **land))
    _props(spec, RELIEF)
    spec.set_editor_property('hummocks', _props(u.GTHummockField(), HUMMOCKS))
    spec.set_editor_property('grass', _props(u.GTGrassVariation(), GRASS))
    return spec


def bog_deform():
    """A bog section's Deform: Mode ByKind as before (the variant's feel), PreChurnScale 1."""
    return _props(u.GTDeformProfile(), dict(pre_churn_scale=PRE_CHURN_SCALE))


def vary(spec, transforms, tussock):
    """A placement through spec.grass (GTTerrain::VaryGrass); returns (transforms, stats dict)."""
    result = u.GTReliefLibrary.vary_grass_transforms(spec, transforms, bool(tussock))
    if isinstance(result, tuple):
        out, stats = result[0], result[1]
    else:
        out, stats = result, '{}'
    return list(out), json.loads(stats)


def report(spec):
    """The strip's relief statistics (UGTReliefLibrary::ReliefReportJson) as a dict."""
    return json.loads(u.GTReliefLibrary.relief_report_json(spec))


def numbers():
    return dict(land=LAND, relief=RELIEF, hummocks=HUMMOCKS, grass=GRASS, pre_churn_scale=PRE_CHURN_SCALE)
