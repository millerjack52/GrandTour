"""Append the completed visual pass to the shared project records."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Art/Export/BenmoreGaea/ShoreRefinement'
def main():
    read=lambda n:json.loads((OUT/n).read_text())
    install=read('install-report.json');prep=read('prepare-report.json');pixel=read('pixel-report.json');test=read('terrain-regression.json')
    assert install['ok'] and install['before']==install['after'] and prep['ok']
    visual=(OUT/'visual-review.txt').read_text().strip();assert visual
    path=ROOT/'docs/VEHICLE_BUILD_SYSTEM.md';text=path.read_text(encoding='utf-8')
    title='Benmore shoreline and sediment refinement'
    assert title not in text,'Already documented; update the existing entry instead'
    stage=max(map(int,re.findall(r'^## (\d+)\.',text,re.M)))+1
    shore=prep['shore']
    entry=f'''## {stage}. {title} (2026-10-09)

Owner said stage 92 was looking better and authorized continuing. Preserve that
accepted native morphology; this stage changes shoreline rendering and material
transitions in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`.
Owned outputs/assets: `Art/Export/BenmoreGaea/ShoreRefinement`, `Gaea/ShoreRefinement`.
Backup: `Gaea/L_Benmore_BeforeShoreRefinement`.

- A 0.625 m signed coverage atlas and matching clipped render meshes reconstruct
  the existing hydraulic occupancy against the native triangle floor. The
  smoothed coverage is bounded to preserve narrow channels. At the validation
  sample spacing the offline mask removes {shore['changed_fraction']*100:.2f}% of old coverage,
  maximum retreat {shore['removed_max_distance_m']:.3f} m; added coverage is zero.
  It does not deepen the river or alter the native heights. Surface vertex means
  still use the accepted wet-weighted baked height, with no height offset.
- The local surface uses the same shore atlas, with a bounded visual rim to avoid
  reproducing its 0.625 m occupancy-cell edges. Interior live wet/dry clipping,
  wakes and field WPO remain. This is render reconstruction, not higher-resolution
  physical wetness: vehicle depth/current queries and the serialized domain asset
  are unchanged. The rim is not a new shoreline flooding/erosion simulation.
- Sediment data separates low wet gravel, dry bar cores and higher soil margins
  using height above water, current speed and the existing bar/rock masks. The
  uniform 78% grey mix/gain is replaced with a 42–76% mineral-neutral tint,
  lighter clean gravel and stronger wet darkening. Existing sourced CC0 mineral
  albedo/normal/roughness remain;
  no generated art textures. Ecology path/vegetation channels remain identical.
- Native Landscape R16 SHA after save/reload:
  `{install['reloaded_native_height_sha256']}`.
  All authored instance transforms/counts, road transforms, tracked deformation
  settings, water-domain asset bytes, fixed-point queries, local solver settings
  and original Drive map SHA compare equal before/after. Deformation WPO stays
  connected. No C++ or tuned physics edits; no new native static bed overlay.
- Runtime simulation remains 9216 cells / 60 m / 0.625 m. Static native surface is
  {prep['meshes'][0]['triangles']} triangles (stage 92: 59923); outlet
  {prep['meshes'][1]['triangles']} (unchanged). This visual pass is not a measured
  performance improvement. No FPS or Benmore driven acceptance claim.

**Actual visual inspection:** {visual}

**Validation:** source hashes and reconstruction bounds, Python compilation,
Unreal material compilation/import/save/reload, native/apron collision support,
unchanged native R16, unchanged placement/query/domain/physics checks passed.
Fixed-camera Before/After images use the same water clock. Pixel differences:
Bars {pixel['Bars']['mean_absolute_rgb_change']*255:.2f}/255; BarGround
{pixel['BarGround']['mean_absolute_rgb_change']*255:.2f}/255. These quantify changes,
not artistic acceptance; sky/cloud animation was not frozen and can affect pixel
comparisons away from the river. `bash Art/suite.sh terrain` ran once ({test['elapsed_s']} s),
**FAIL** at the documented step 11 held rut-exit gate (5.7 s vs 5.5 s down-ruts;
"slower than down the ruts 0"). The run preceded importing this visual-only pass.
No physics adjustment or repeated run to chase that standing failure.

**Reproduction:** `Art/tools/prepare_benmore_shore.py`, Blender background
`Art/Blender/export_benmore_shore.py`, `Art/benmore_shore.ps1`, then
`Art/tools/sample_benmore_shore.py`. The installer reuses guarded library helpers
from `install_benmore_gaea_creek.py`, whose direct-run entry point is now guarded.
After installation, use `-ReviewOnly` for a material/capture retry. Never rerun the
stage 92 normal terrain installer on this revision. Evidence: prepare/install/
pixel/terrain-regression reports, nine paired engine renders, visual-review.txt.

**Remaining:** ambient flow-normal choice and specular/riffle response, visually
reviewed moving-water sequences, Benmore driving and actual frame-time profiling.
Current owner acknowledgement applies to stage 92; this pass awaits their review.
'''
    for relative in ['docs/VEHICLE_BUILD_SYSTEM.md','docs/BENMORE_RIVER_LIFE.md','docs/devlog/2026-10-09.md']:
        p=ROOT/relative;p.write_text(p.read_text(encoding='utf-8')+'\n\n'+entry,encoding='utf-8')
    short=f'''\n\n### Benmore shore refinement, stage {stage} (2026-10-09)

Installed in GaeaReview with stage 92 native bed and hydraulic data preserved.
Bounded subcell shoreline reconstruction, matched static/live coverage, geographic
wet-gravel/dry-bar/soil transitions using sourced mineral textures. Actual paired
engine images and preservation/collision checks are in
`Art/Export/BenmoreGaea/ShoreRefinement`. Terrain suite still fails its known rut-exit
gate. Ambient water shading/motion, driven acceptance and FPS profiling remain
open. See `BENMORE_RIVER_LIFE.md` stage {stage} for exact scope and limitations.
'''
    p=ROOT/'docs/WATER_PLAN.md';p.write_text(p.read_text(encoding='utf-8')+short,encoding='utf-8')
    p=ROOT/'docs/BACKLOG.md';p.write_text(p.read_text(encoding='utf-8')+f'\n- [ ] (M6, T1) BENMORE SHORE {stage}: Visual shore/sediment refinement installed and engine-checked; accepted stage 92 terrain/flow, placements and physics preserved. Owner look review, ambient water rendering, Benmore driving and FPS remain open. Known terrain rut-exit failure retained. Evidence: `Art/Export/BenmoreGaea/ShoreRefinement`.\n',encoding='utf-8')
    (OUT/'documentation-stage.json').write_text(json.dumps(dict(stage=stage,documents_updated=True),indent=2))
    print('Documented shore refinement stage',stage)

if __name__=='__main__':main()
