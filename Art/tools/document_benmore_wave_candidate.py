"""Record the uninstalled candidate and the actual blocker, without claiming a pass."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[2]
# Historical recorder only. Never overwrite newer installed-candidate status.
assert '## 94.' not in (ROOT/'docs/VEHICLE_BUILD_SYSTEM.md').read_text(encoding='utf-8'), 'Stage 94 already recorded; update the current record instead.'
OUT=ROOT/'Art/Export/BenmoreGaea/FlowWaves'
status=json.loads((OUT/'candidate-status.json').read_text())
status.update(installed=False,full_build_passed=False,gpu_material_validated=False,
    after_motion_captured=False,background_jobs_running=False,
    blocker='Repeated shared Unreal soak runs started during both build attempts. Own builds stopped; shared tests untouched.',
    resume=['Reserve an editor-free interval, then complete the editor build with MaxParallelActions=2.',
            'Run Art/benmore_waves.ps1 -Mode Install, inspect GPU data/material compile and preservation report.',
            'Run Art/benmore_waves.ps1 -Mode After; inspect ambient, impulse, window-join and lake captures.',
            'Run the focused CPU water automation tests after the build; no driving/timing while GoWR is active.',
            'Only then mark the candidate installed and update the pending documentation.'])
(OUT/'candidate-status.json').write_text(json.dumps(status,indent=2))
detail='''

## 94. Benmore ambient wave candidate — NOT INSTALLED (2026-10-09)

The owner rejected the water simulation after stage 93. The code still rendered
an amplified rain-ring normal with 4.7 s reset/crossfade advection and no distant
ambient height. A controlled, fixed-step editor baseline now exists in
`Art/Export/BenmoreGaea/FlowWaves/motion-before.json`: the current at the inspected
ford is (-0.792, -0.472) m/s; undisturbed sample heights stay unchanged. A 4 cm,
1.4 m radius added-volume impulse starts at 4 cm and falls to a 0.319 cm sampled
peak after 5.75 s. This is a diagnostic impulse, not a vehicle crossing, an
artistic acceptance gate, a conservation test or a performance measurement.
The before sequence visibly retains broad reflections and circular ambient
ripples. No driven or timed test was run; GoWR remains active.

**Prepared source, unvalidated replacement:** `GTWaterAmbient.cpp` and small
`GTWaterSheet.h` / `GTWaterDomainSheet.cpp` additions provide a single optional
256x256 RGBA16F numerical precombine per domain owner, capped at 30 Hz. Benmore
has one owner. Four domain surfaces share its texture and absolute clock. No
runtime map-size simulation, solver, depth, placement or vehicle tuning changes.
The optional material reference defaults null, so existing maps do not enable
it merely by rebuilding. `gt.Water.Domain.Ambient` disables only the candidate
rendering; `gt.Water.Domain.AmbientHz` selects 15–60 Hz for future measurement.

`Art/Unreal/benmore_flow_waves.py` prepares six long height bands and eight
normal-only bands, matching analytical slopes and crest breakup. Integer
spatial frequencies make the numerical 12 m field tile; four fixed neighbouring
direction/speed samples follow the authored mean without UV reset. RG encode
slopes, B long-wave height, A remaining foam transmittance. Geometry wavelength
is at least 5.37 m; the maximum river displacement bound is 1.215 cm before
shore/distance fades. The background lake is a coarse engine plane, so ambient
geometric relief is gated to flowing baked river data; calm lake ripples are
normal-only. The raw GPU channels and alpha convention still require the
provided real-RHI test. This is numerical wave data, not a new painted texture.

**Blocker and current state:** Python parsing passed and the existing editor
captured 46 before frames. The full C++ build did NOT finish. Two attempts were
stopped when another shared Unreal soak run began; the first also encountered
UBA memory-pressure retries. The original DLL remains dated 2026-10-09 00:33:56.
No new material assets, backup map or level change were installed. No after
images, real-RHI material compilation, GPU readback pass, wave-regression pass
or visual acceptance exists for the candidate. All own wait/build processes
were stopped; no automatic background installation is armed. The user was
asked to pause Claude's queue after its current test, as back-to-back runs
repeatedly prevent the editor-free build required by their shared-work rule.

**Resume:** finish the editor build in a reserved quiet interval, then
`Art/benmore_waves.ps1 -Mode Install` and `-Mode After`. The installer backs up the
stage 93 level, compares actual GPU channel values at two clocks, checks one
shared target, effect-off physical queries, asset parents, save/reload, all
authored instance transforms, road transforms, physical domain, profiles and
original driving-map hash. The motion review advances the real disturbance
field separately from the ambient clock; after includes 12 fps sampled ambient
motion, the same impulse, 10 m recenter and visible join checks, bar/long-reach
and lake views. Inspect them before accepting or reporting a completed fix.
Then run focused `GrandTour.Water.RiverReference`, `MovingDomain` and
`PassiveDetail` CPU regressions. Driving, wheelspin/wakes, runtime cadence and
FPS still need separate validation; existing CPU fixtures use the older pilot
and do not by themselves establish current-course visual quality.

Evidence and status: `Art/Export/BenmoreGaea/FlowWaves/candidate-status.json`,
`motion-before.json`, `Ambient_Before.gif`, `Saved/Logs/BenmoreWavesBefore.log`,
`build_last.txt`, `build_benmore_waves.txt`. The physical binary, native float
height source and original driving map still match stage 93 source hashes.
'''
target=ROOT/'docs/VEHICLE_BUILD_SYSTEM.md'
assert '## 94. Benmore ambient wave candidate' not in target.read_text(encoding='utf-8')
with target.open('a',encoding='utf-8') as f:f.write(detail)
brief='''

### 2026-10-09 — ambient wave candidate pending shared editor access

Stage 94 in `docs/VEHICLE_BUILD_SYSTEM.md` records the response to the owner's
water-simulation rejection. Controlled before motion is captured; a numerical
height/slope/foam precombine and current-directed surface replacement are
prepared, **not installed or GPU/visually validated**. Full builds were stopped
when shared soak tests started again; no physics or saved-map change belongs to
this candidate. GoWR remains active: no driving or performance results. No own
background job remains armed. Resume from
`Art/Export/BenmoreGaea/FlowWaves/candidate-status.json` once a build/editor slot
is available, and pass install/readback/preservation plus actual motion review
before claiming the water is fixed.
'''
for name in ['BENMORE_RIVER_LIFE.md','WATER_PLAN.md','BACKLOG.md','devlog/2026-10-09.md']:
    with (ROOT/'docs'/name).open('a',encoding='utf-8') as f:f.write(brief)
print('Recorded stage 94 as uninstalled, unvalidated, blocked by shared editor queue.')
