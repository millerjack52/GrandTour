"""Record verified installation; leave visual acceptance and performance explicit."""
from pathlib import Path
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Art/Export/BenmoreGaea/FlowWaves'
install=json.loads((OUT/'install-report.json').read_text())
motion=json.loads((OUT/'motion-comparison.json').read_text())
assert install['ok'] and motion['ok']
cpu=(ROOT/'Saved/Logs/water_domain_test.log').read_text(errors='replace')
assert len(re.findall(r'Test Completed\. Result=\{Success\}.*Path=\{GrandTour.Water.',cpu))==3
status=json.loads((OUT/'candidate-status.json').read_text())
for path,expected in status['files'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==expected,path
status.update(installed=True,full_build_passed=True,gpu_material_validated=True,after_motion_captured=True,
    background_jobs_running=False,blocked_by=None,blocker=None,cpu_regressions_passed=3,
    planned='Installed current-aligned ambient waves with shallow geometric relief; physical solver unchanged',
    geometry_check='geometry-check-report.json',motion_comparison='motion-comparison.json',
    lake_geometric_relief=False,performance_measured=False,driving_tested=False,
    resume=['Owner review of river surface relief/motion in the Gaea review level.',
            'Lake geometry needs a bounded render-grid solution; its coarse plane still uses normal-only ambient waves.',
            'Actual vehicle wakes, runtime cadence and quiet-machine GPU measurements remain separate checks.'])
(OUT/'candidate-status.json').write_text(json.dumps(status,indent=2))
detail='''## 94. Benmore current-aligned waves and river surface relief (2026-10-09)

Installed in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`.
The owner rejected the old circular ripple motion and perfectly flat surface.
This pass replaces the rain-ring/reset animation with current-aligned numerical
waves and actual vertex displacement. It is a render change, not a new fluid
solver or a deeper river. Owner artistic acceptance is still pending.

`GTWaterAmbient.cpp` and hooks in `GTWaterSheet.h` / `GTWaterDomainSheet.cpp`
produce one shared 256-square RGBA16F height/slope/foam target at 30 Hz for the
Benmore domain. Four surfaces share its texture and absolute clock. Six geometry
bands and eight finer normal-only bands are sampled in four fixed neighbouring
direction/speed bases without periodic UV reset. Procedural numerical data is
the wave plan's approved exception; no new painted texture was made.

The shortest geometry wavelength is 2.91 m on a 0.625 m grid. Amplitude follows
current and depth, stays below 22% of optical depth, fades over the final 10–75 cm
to shore and between 55–180 m viewing distance. Numerical sampled maxima are
5.16 cm on the river and 4.49 cm on the outlet (before distance fade); these are
sampled values, not a physical wave-height guarantee. The absolute bound is
8.235 cm before the depth/shore fades. Fine ripples stay in the lighting.

The outlet render mesh was subdivided on its original triangle planes: 21,893
to 87,572 triangles, with original vertices, footprint and mean surface
preserved. The native river remains 68,183 triangles. Interaction displacement
now samples the existing live field on that continuous river mesh, fading in
through the existing 6 m edge region. It no longer swaps to the offset local
grid in the river; the lake retains its local replacement. This removes the
river grid seam exposed by the first boundary captures. This adds rendering work;
it is not a measured speedup. The background lake remains a coarse engine plane
with normal-only ambient waves. A bounded lake render grid is still needed for
lake geometric relief; this pass does not claim all water is now displaced.

**Validation:** full editor C++ build passed. SM6 material creation and actual
GPU readback passed at two clocks (worst channel error <0.000475), including the
foam alpha convention. One shared target, disable/enable physics independence,
asset parents and save/reload checks passed. All 90,872 authored instances,
57,808 road instances, deformation profiles, physical water-domain asset,
fixed-point water queries, runtime solver settings and original Drive map hash
remain equal. Physical source binary and native height source hashes also match.
The interaction field remains 9,216 cells / 60 m / 0.625 m.

Three CPU regressions passed: `GrandTour.Water.RiverReference`, `MovingDomain`,
`PassiveDetail`. The fixed-step 24-frame impulse comparison is numerically
unchanged. The effect does not alter buoyancy/depth queries. No driven crossing,
runtime frame cadence, FPS or GPU-cost result is claimed. Previous stage 93's
terrain suite had the existing step-11 held-rut-exit failure; tuned traction was
not changed or retuned. The user requested work without timing claims.

Actual engine captures include 60 ambient frames at 12 sampled frames/second,
the impulse, window recenter/join pairs, shallow-angle relief off/on, reach,
bar and lake. The GIF's five-second wrap is a preview loop, not a runtime wave
reset. Clouds and vegetation were not frozen. See `visual-review.txt` for the
image inspection and remaining appearance limits; pixels do not establish
artistic acceptance or vehicle feel.

**Reproduction:** `Art/tools/prepare_benmore_flow_mesh.py`, Blender
`Art/Blender/export_benmore_flow_mesh.py`, `Art/tools/check_benmore_wave_geometry.py`,
`Art/benmore_waves.ps1 -Mode Install`, `-Mode After`,
`Art/water_domain_test.ps1`, `Art/tools/sample_benmore_wave_motion.py`.
Shared Unreal runs must finish before builds or another editor is launched.
The previous blocked attempts made no level change; a later free interval
allowed this build and installation. Backup: `L_Benmore_BeforeFlowWaves`.

Owner comparisons: `gt.Water.Domain.Ambient 0` / `1` toggle only this rendering;
`gt.Water.Domain.AmbientHz` defaults 30, clamped 15–60. Use `stat unit`, `stat gpu`
and `gt.Water.Stats 1` for a future owner profiling pass. Solver statistics alone
do not include the new render-target/material/mesh cost.

Evidence: `Art/Export/BenmoreGaea/FlowWaves/` contains install, geometry, motion,
comparison and current status reports, captures and `Ambient_After.gif`.
Build/test logs are `Saved/Logs/build_benmore_waves.txt`,
`BenmoreWavesInstall.log`, `BenmoreWavesAfter.log`, `water_domain_test.log`.
'''
p=ROOT/'docs/VEHICLE_BUILD_SYSTEM.md';text=p.read_text(encoding='utf-8')
start=text.index('## 94. Benmore');end=text.find('\n## ',start+1)
p.write_text(text[:start]+detail+(text[end:] if end>=0 else ''),encoding='utf-8')
brief='''### 2026-10-09 — river wave geometry installed (stage 94)

`docs/VEHICLE_BUILD_SYSTEM.md` stage 94 now records installed current-aligned
height/slope/foam waves, real shallow river relief and a finer outlet render
mesh. Build, GPU readback, preservation, save/reload, fixed-step impulse and
three CPU water regressions passed. Terrain, tuned physics and placements are
unchanged. Actual motion and shallow-angle captures are in
`Art/Export/BenmoreGaea/FlowWaves/`. Owner visual acceptance, driven wakes and
performance measurement remain open. The coarse lake still has normal-only
ambient waves; geometric lake relief needs a bounded render grid. No FPS claim.
'''
for name in ['BENMORE_RIVER_LIFE.md','WATER_PLAN.md','BACKLOG.md','devlog/2026-10-09.md']:
    p=ROOT/'docs'/name;text=p.read_text(encoding='utf-8')
    old_heading='### 2026-10-09 — ambient wave candidate pending shared editor access'
    start=text.index(old_heading if old_heading in text else '### 2026-10-09 — river wave geometry installed (stage 94)')
    following=re.search(r'\n#{1,6} ',text[start+1:])
    end=start+1+following.start() if following else -1
    p.write_text(text[:start]+brief+(text[end:] if end>=0 else ''),encoding='utf-8')
print('Recorded installed river wave geometry; lake geometry, driving and timings remain open.')
