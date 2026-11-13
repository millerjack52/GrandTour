# LiDAR rally handling

## RH1: recoverable slides, 2026-10-21 UTC

Owner direction: the same cars drive fast gravel / DIY dirt sections and slow
off-road sections. Preserve their different capabilities and the existing
off-road response. The high-speed slide currently loses too much grip; move
slightly toward arcade handling.

This first pass retains lateral force after the tyre's peak rather than adding
engine power, peak grip, automatic steering or a corrective chassis yaw torque.
Each car keeps its mass, driven axles, engine, ratios, brakes, suspension and
tyre curve. The existing muddy road, forest, house and river assets are not saved
or rebuilt by this pass.

### Behaviour and controls

- `HighSpeedSlideRecovery` on `UGTSoilVehicleMovement` defaults to 0.75: recover
  75% of the lateral curve's lost force after its peak. The existing 0.68 tail
  therefore becomes 0.92 at full effect. This is a curve fraction, not a promise
  of 0.92 g: surface friction, load and the friction circle still apply.
- Smooth speed blend from 30 to 65 km/h. Below 30 km/h, no change.
- Low range always bypasses the adjustment, including at higher speed.
- Fades out over softness 0.25-0.45, soil penetration 6-12 cm and water immersion
  1-5 cm. Deep/soft mud and water retain the previous response.
- Pre-peak and peak response remain unchanged. Grip still breaks away; throttle
  and braking still share the available tyre force.
- `gt.Vehicle.SlideRecovery 0` restores the old response for an A/B drive.
  `gt.Vehicle.SlideRecovery 1` re-enables the per-car strength. Default is 1.
  No level rebuild is required; reopen Unreal after the compiled code change.

The physics thread uses an immutable game-thread snapshot of range and strength.
It temporarily adjusts each wheel's runtime lateral-curve multiplier and restores
it after the standard Chaos force calculation. Shared wheel class data is never
modified. Curve peaks are sampled once per simulation; no added actors, physics
bodies, streaming, textures or per-frame terrain searches.

### Implementation

- `Source/GrandTour/Vehicle/GTSlideRecovery.h`: bounded blend and curve adjustment.
- `Source/GrandTour/Vehicle/GTSoilVehicleMovement.cpp/.h`: snapshot and tyre solver
  integration, per-car property and A/B console variable.
- `Source/GrandTour/Vehicle/GTSlideRecoveryTests.cpp`: original-force invariants
  plus actual Chaos wheel force comparisons.
- `Source/GrandTour/GrandTour.Build.cs`: explicit ChaosVehiclesCore dependency.
- `Art/Unreal/check_lidar_dual_driving.py` and
  `Art/check_lidar_dual_driving.ps1`: transient checks in the actual saved LiDAR
  map using the Range Rover, BMW E39 Touring and Suzuki SJ413.

### Evidence

Build passed. All five selected automation tests passed, with exit 0:
SlideRecovery, MudRunner.SubstanceOracle, MudRunner.LivePush,
LandscapeMud.RutWallWork and LandscapeMud.DirectionalSoilFlow.

At 79.2 km/h and a 40-degree tyre slip angle, the Chaos wheel fixture's lateral
force rose from 151280.1 to 204673.0 engine force units (+35.3%). Low range,
low speed and peak force compare identically. Deep mud/water exclusions pass.
See `Saved/Logs/rally-tests.log` and `Saved/Logs/rally-build.txt`.

Controlled on-map comparison: identical initial 65 km/h velocity disturbance,
20-degree sideways angle, zero steering/throttle, 3 seconds. This is an injected
disturbance to isolate response, not evidence that each car accelerated to that
speed. Cars run sequentially on the same live road; terrain is not reset between
passes and timing is not deterministic. Small differences need a player drive
and repeat trials before drawing strong conclusions.

| Car | Integrated absolute slip, deg s, old/new | Time below 5 degrees, s, old/new | Max lateral displacement, m, old/new |
|---|---:|---:|---:|
| Range Rover | 13.135 / 12.556 | 1.152 / 1.055 | 4.520 / 4.447 |
| BMW estate | 6.444 / 6.036 | 0.539 / 0.545 | 1.328 / 1.264 |
| Suzuki | 4.440 / 4.206 | 0.436 / 0.336 | 1.192 / 1.394 |

All six runs completed with normal editor exit. Reduced slip integral is common
to all three, but the Suzuki travelled farther sideways and BMW recovery time
did not improve. This is not universal handling acceptance. Owner drive is the
gate. Full evidence: `Saved/LidarAuthoringQA/Rally/slides.json`.

The unmodified normal-route baseline is `Saved/LidarAuthoringQA/Rally/baseline.json`.
It uses 40 seconds on Waimeamea Road from station 200 m, then 15 seconds on
Riverside access from 1290 m, with fresh cars, low range and locks on the latter.
The public-road peaks were only 32.914 / 11.422 / 2.258 km/h respectively. That
sample exposes an unresolved acceleration/surface/route limitation; it does not
qualify as a successful fast rally section. Do not compensate blindly with power
or transfer the slow-offroad calibration to every car. The BMW has a 1:1 low
range multiplier, so its low-range test is not evidence of 4WD capability.

Further diagnosis in the post-change route run: the start of Waimeamea Road
samples `bNativeSubstanceResponse=True`, `bGranularResponse=False`, softness 0.1
and sinkage cap 2.409 cm. The next 100 m rises 9.58%. The visible gravel road is
therefore still using native mud resistance at this point. The editor road
rebuild currently writes style R toward zero for every road, and `NativeMudAt`
uses that channel to distinguish native mud from granular soil. This needs an
explicit authored road surface type propagated through rebuild and fine contact
sampling; changing global mud resistance would also alter the working mud route.
RH1 deliberately does not change those existing surface classifications. This
is an outstanding part of the broader fast-road work, not a handling success.

These PIE checks do not establish sustained standalone 60 fps, player feel,
slide recovery on every surface, or a finished rally route. No new FPS claim.

Post-change normal routes also completed with exit 0. Low-range travel changed
by +0.74% (Range Rover), -3.09% (BMW), -2.60% (Suzuki), within the 5% tolerance
for non-deterministic live-map runs. Engine torque, mass, drive split, wheel
radii and range/lock settings matched baseline exactly. Peak public-road speeds
remained 32.690 / 11.260 / 2.271 km/h, so the fast-speed target is still unmet.
See `Saved/LidarAuthoringQA/Rally/recovery-routes.json` and `regression.json`.

### Reproduce

```
powershell -NoProfile -File Art/check_lidar_dual_driving.ps1 -Label owner-routes
powershell -NoProfile -File Art/check_lidar_dual_driving.ps1 -Label owner-slides -Mode slides
```

The wrapper waits for Unreal to be free, holds the shared profiling reservation,
never kills an editor, requires a fresh report and checks the process exit.
The report's `ok` means basic execution/control checks passed; individual
`reached_60_kmh` fields report whether the fast-speed target was actually met.

## FR1: firm gravel roads, 2026-10-21 UTC

Owner direction: established gravel roads, including Riverside access, are
high-speed rally sections and need not deform. Logging mud, bogs and the river
gravel bank retain their yielding surfaces. This supersedes RD1b's shallow ruts
and damp hollow on the access roads.

`AGTProceduralRoad.bFirmGravel` is opt-in. It writes exactly zero yielding depth
and softness through the carriageway plus a 50 cm interpolation guard, fading
into the soil over the shoulder. Conditions and relief textures cannot add ruts
or bogs to the rally portion. The final 35 m at the Riverside house retains its
existing geometric profile, with a 16 m approach blend; it is still rigid.
The fine collision mesh meets its mineral support mesh
at the same height. Existing zero-depth terrain handling bypasses native mud
support/resistance and keeps cosmetic gravel wheel marks. No vehicle, tyre,
transmission, water-force or mud-solver parameters change.

`ProfileSmoothingMetres=16` filters short elevation bumps using a symmetric
distance-weighted window. It preserves straight grades, fades at route ends,
and leaves XY bends and widths intact. Cut/fill is bounded to 120 cm. Smoothing
runs during editor generation, with no added runtime simulation or mesh density.

`Art/Unreal/lidar_firm_roads.py` supplies the shared policy for Riverside access,
Pond field spur, Waimeamea Road and Waterhouse Road. Full Install reapplies it;
`Art/firm_lidar_roads.ps1` performs a backed-up, targeted rebuild of the current
saved map. It checks sampled soil depths, profile roughness, protected ground,
geometry budget and persistence before reporting success.

`Art/check_lidar_dual_driving.ps1 -Mode firm -Label firm-roads` checks the same
three cars on both gravel routes in high range and the logging route in low
range. Soil strokes additionally test rigid roads versus yielding logging mud
and river gravel. This is a control/regression check, not owner acceptance or
a standalone performance measurement.

FR1 map validation: saved and reloaded with normal editor exit. All 8,565
sampled lane positions have zero yielding depth. Two-metre midpoint residual
RMS decreased by 34.0% (Riverside), 35.9% (Pond spur), 34.9% (Waimeamea) and
71.1% (Waterhouse). Geometry remains 1,004,400 triangles. Second rebuild changed
zero tiles and retained digest `6AE1F9489CE5EC408044BFEC06A9FE25`.
The complete homestead apron survey, protected bank/logging elevations and
sampled yielding depths compare unchanged. Evidence: `Saved/LidarAuthoringQA/FR1/apply.json`.

First driving run: Waimeamea peaks were 76.942 / 73.753 / 74.786 km/h for the
Range Rover / BMW / Suzuki, versus 32.690 / 11.260 / 2.271 in RH1. These are
finite automated runs with changing grades, not top-speed ratings. The original
driver missed Riverside's tight bend and stopped outside the road; its broad
9 m departure threshold incorrectly allowed those rows to report `ok`. Do not
treat them as route-completion evidence. The driver now samples bends at 5 m,
brakes more conservatively, and rejects a five-second stall.

Logging trial at 220 m, 15 seconds, low range: Range Rover travelled 52.494 m,
Suzuki 10.412 m; BMW moved -1.893 m and failed. No pre-change comparison exists
for this exact muddy segment, so this is a capability observation, not evidence
of an off-road regression or improvement. Off-road coefficients are unchanged.
The full run consequently reports `ok=false`; raw results remain in
`Saved/LidarAuthoringQA/Rally/firm-roads.json`.

All four pressure-stroke checks passed: Waimeamea/Riverside remain at zero
deformation; logging mud and river gravel yield approximately 1 cm. Their
sampled layer depths are 5.700 cm and 4.613 cm respectively. The river gravel's
existing legacy `SurfaceTag=Mud` is unchanged by FR1; do not confuse it with
the established roads, which report `Gravel` with zero depth.


Final Riverside repeat: BMW and Suzuki completed the 35-second segment (274.9 m / 273.2 m, peaks 42.0 / 41.7 km/h). The Range Rover automated driver went wide and the run failed after 89.1 m. Overall access check remains false; owner drive is required for handling acceptance. All four soil-stroke checks passed again. See `Saved/LidarAuthoringQA/FR1/validation-summary.json`.

Road rebuilds also preserve the hidden static pool mesh used beneath the four live rut-water basins. The existing and regenerated seed arrays/extents match exactly. The saved visibility correction passed reload with normal exit; terrain digest stayed unchanged (`Saved/LidarAuthoringQA/FR1/water.json`).

## RH2 - responsive high-range steering (2026-10-21)

Owner reports very weak steering at speed and names Forza Horizon 4 as the feel
reference. This is a first response pass, not a reconstruction of Forza physics.
The existing speed-dependent steering lock is compounded by Chaos's squared
input curve and 2.5/s rise rate. At 80 km/h a 180 ms tap only produced about
1.7 degrees at the front wheels; half stick only used a quarter of available
lock. The earlier automated driver also forgot to invert that squared response.

`FGTResponsiveSteering` captures each car's authored input configuration and
blends toward linear response, rise rate 6/s and return rate 8/s from 30 to
60 km/h in high range. Already faster authored rates remain faster. Strength
is per car (`HighSpeedSteeringResponse`, default 1); no shared wheel defaults
are mutated. Transition curves reuse 17 linear keys, and steady full/bypass
states skip rebuilding. External authored input curves remain referenced and
are restored with the original configuration when bypassed.

Low range at any speed, speeds at/below 30 km/h, and contacted mud/bog/snow
bypass RH2. Sinkage fades it out over 6-12 cm and water depth over 1-5 cm.
Maximum steering lock, speed/lock curve, tyre forces, slide recovery,
suspension, engine power, terrain and water physics are unchanged. There is
no yaw force, auto-countersteer or hidden vehicle velocity correction.

Console comparison: `gt.Vehicle.ResponsiveSteering 0` restores the original
input response; `gt.Vehicle.ResponsiveSteering 1` enables RH2 (default).

Build succeeded (`Saved/Logs/responsive-steering-build.txt`). Six automation
tests passed with exit 0: ResponsiveSteering, SlideRecovery, SubstanceOracle,
LivePush, RutWallWork, DirectionalSoilFlow. The new test exercises the actual
Chaos filter for tap response at different tick rates, signed input, reversal,
recentering, monotonic blends, bypasses and restoration of car-specific rates.
Report: `Saved/Automation/ResponsiveSteering`.

Saved LiDAR-map open-loop trials, without map saves: 36 runs / 18 paired checks
passed, editor and wrapper exit 0 (`Rally/responsive-steering.json`). These
compare the installed C++ via the console switch, not replacement Python
tuning. The 80 km/h half-stick results are:

| Car | Peak wheel angle, before -> after | Heading change at 0.7 s, before -> after |
| --- | --- | --- |
| Range Rover | 2.02 -> 4.07 degrees | 4.65 -> 9.40 degrees |
| BMW | 2.01 -> 4.05 degrees | 3.91 -> 8.00 degrees |
| Suzuki | 2.02 -> 4.08 degrees | 4.96 -> 9.09 degrees |

The 180 ms tap at 80 km/h gives 4.44-4.51 times the peak wheel angle; 90 km/h
direction reversals give about twice the wheel angle. At 20 km/h (both ranges)
and 90 km/h low range, response weight is exactly zero and wheel angles match
within the 3% test tolerance. Small whole-vehicle differences remain between
separately spawned physics runs. This establishes response and bypass behavior,
not subjective acceptance, sustained full-throttle cornering or a lap-time claim.
The fixture injects initial velocity, then coasts for 1.4 seconds.

Reproduce: `Art/check_lidar_dual_driving.ps1 -Mode steering -Label responsive-steering`.
The route driver now inverts the blended squared/linear response to obtain
the requested wheel angle; comparisons with old FR1 route runs include this
driver correction and cannot isolate the RH2 handling change.


RH2 riverside route validation: three 35-second high-range runs passed, with
normal editor/wrapper exit. Results include the corrected automated driver.

| Car | Distance | Peak speed | Maximum centreline offset |
| --- | --- | --- | --- |
| RangeRover | 305.686 m | 46.260 km/h | 0.516 m |
| BMW | 281.930 m | 42.718 km/h | 0.411 m |
| Suzuki | 271.311 m | 41.799 km/h | 0.521 m |

All four pressure-stroke checks passed again: Waimeamea and Riverside stay
undeformed; logging mud and the river gravel bank still yield. Evidence:
`Saved/LidarAuthoringQA/Rally/responsive-steering-access.json`. No map or
asset saves were made. No new FPS claim: this pass changes input processing,
and the route runs are functional checks. Owner driving remains the acceptance
gate, especially sustained throttle, braking into corners and controller feel.


## RH3 - consistent keyboard response and normal-Play performance (2026-10-21)

Owner feedback: RH2 still felt delayed/uneven on keyboard and performance had
regressed. RH3 removes speed-dependent blending of the input filter on firm
high-range surfaces. The existing speed-dependent maximum steering lock remains.
Linear response rises at 6/s and returns at 8/s throughout firm high range;
authored faster rates survive. Low range, contacted mud/bog/snow, sinkage and
water bypass/fades remain as RH2. Tyre force curves, power, suspension and slide
recovery are not retuned by this pass. This supersedes RH2's <=30 km/h bypass.

The ordinary editor launch log had no performance commands: directional shadow
bias was -1.5 rather than the saved preset's +0.5. PIE also defaults to overriding
game screen percentage. A new GTLidarPerformanceSubsystem applies the canonical
Art/lidar_performance.json when L_LidarStudy begins Game/PIE, respects explicit
higher-priority overrides and restores prior settings on the last play world's
shutdown. The JSON is staged as a runtime dependency (packaged build untested).
OriginalQuality launcher uses -GTLidarPerformance=0; gt.Lidar.PerformanceAuto 0
before Play is another opt-out. Version 2 keeps TSR at 75%, uses mesh LOD scale
4 instead of 3 and shadow bias 1 instead of 0.5. Density is unchanged; the
tradeoff is earlier mesh simplification and lower shadow resolution. Output
resolution remains whatever the player/editor chooses; measurements below are
1600x900. The preset caps normal play to 60 fps; captures are uncapped.

Water profiling exposed two avoidable costs. RefreshDomainBed now samples only
supported cells and preserves the live field without copying/rebuilding it if
reference depths did not change. TickWaterDomain alone owns player-centred
streaming: remote parked-car lids/impulses are clipped instead of repeatedly
moving the simulation away from the player. Whole-course coverage/immersion
queries remain independent of this local surface-wave window.

Validation:
- Editor builds succeeded: Saved/Logs/rh3-build.txt and rh3-water-build.txt.
- Nine automation tests passed, exit 0, Saved/Automation/RH3: ResponsiveSteering,
  SlideRecovery, DirectionalSoilFlow, RutWallWork, LivePush, SubstanceOracle,
  MovingDomain, RiverReference and ShoreEnvelope.
- 24 actual A/D keyboard sequences, 12 paired comparisons, all handling checks
  passed in the saved LiDAR map. Three cars (Range Rover/BMW/Suzuki), 20/40/80
  km/h high range, 20 km/h low range. Each sequence presses A for 160 ms,
  releases, presses D for 160 ms, then releases; input trace reaches both signs
  and returns to zero. Initial velocity is injected and the car coasts for
  1.4 seconds: this is not a sustained throttle/cornering or owner-feel verdict.
  High-range peak wheel-angle ratios on/off were 5.13-5.73 for these short taps;
  low-range ratios were 0.97-1.00 with response weight exactly zero.
  Evidence: Saved/LidarAuthoringQA/Rally/rh3-keyboard.json. Its subsequent water
  setup failed because the car was still moving too fast to exit, so the whole
  report must NOT be treated as a fully successful run despite its old ok=true
  field. The runner now sets ok=false on exceptions and waits for braking before
  the water test. All keyboard comparisons completed before this setup failure.
- Separate water-mode rerun passed with normal editor/wrapper exit:
  Saved/LidarAuthoringQA/Rally/rh3-water.json. All 14 preset values applied without
  test-side profile commands and restored exactly after PIE. A remote contact
  left local water height exactly 4488.623535 cm and returned zero remote impulse.
  At (-47938.658044,-37813.658044), a soil stroke lowered terrain delta from
  -1.168833 to -3.417597 cm; the formerly dry shore became wet, depth 1.556757 cm.
  Reproduce with Art/check_lidar_dual_driving.ps1 -Mode water -Label <new-label>.

Performance on RTX 4050 Laptop 6 GB, Development offscreen standalone, 1600x900,
uncapped; 440 measured frames per scene, excludes loading/teleports/screenshots:

| Scene | Stock mean FPS / p95 ms | Prior saved preset, steering off | RH3 final mean FPS / p95 ms |
| --- | --- | --- | --- |
| River | 51.4 / 29.844 | 77.4 / 16.302 | 89.9 / 12.944 |
| Bog 214 | 31.3 / 42.458 | 55.8 / 23.447 | 69.7 / 17.920 |
| Bog 552 | 30.9 / 47.408 | 63.3 / 20.201 | 71.9 / 17.657 |
| Access stress | 36.1 / 37.846 | 60.8 / 22.183 | 64.6 / 19.052 |

These are short fixed-heading LOW-range throttle stress scenes, NOT completed
rally routes. In particular, the old access fixture drives into trees/off-road;
its screenshot must not be used to claim successful road following. Stock used
100% screen percentage and stock quality; the prior and final saved presets use
75%. The improvement combines configuration and code changes, not steering
alone. Final GPU p95: 11.290, 13.658, 16.081, 15.488 ms in table order. Full-frame
p95 still exceeds 16.667 ms in three scenes: NO locked-60 or full-route claim.
SteeringResponse CSV scope mean 0.000822 ms / p95 0.0013 ms across warmed final
capture frames (mostly low-range bypass; not a high-range A/B cost comparison).
Water.LiveRiverBed mean per-call cost old -> final, table order:
3.2520 -> 1.2447, 3.7703 -> 0.3160, 3.6776 -> 0.2993, 3.3781 -> 0.0443 ms.
Final window log has seven moves for initial placement, four teleports and two
local focus movements, without repeated far-contact recentering. Final bog view
was inspected: full foliage, ground detail and mud remain visible.

Evidence: Art/Export/LidarStudy/Place/playperf-rh3-{stock,saved-off,tuned,final}
metadata/summary JSON, Saved/Profiling/gt_perf_PF60-rh3-final-*.json and final CSV
Saved/Profiling/CSV/Profile(20261021_154828).csv. Reproduce final capture:
Art/profile_lidar_play.ps1 -Label <new-label> -UseSavedProfile -Uncapped -Drive -Probes.
No map/assets were saved, no commits made, Unreal closed normally. Owner driving
remains the acceptance gate; remaining streaming/rendering spikes are documented
rather than hidden by average FPS.


## PF120 - 2026-10-21 UTC: 120 fps target, first optimization pass

STATUS: TARGET NOT MET. User asked for smoother driving and a 120 fps target.
The retained preset caps at 120; this is NOT a claim of sustained 120. The budget
is 8.333 ms. Saved normal-Play preset is Art/lidar_performance.json version 5.
No map or art assets saved; steering/traction tuning and physics rates unchanged.

Implemented:
- Height-only wheel contact queries in GTLandscapeSurface and GTVehicleTuningComponent.
  Preserve the 9x9 support grid and native height sentinel; skip the legacy grid
  that native support immediately overwrote. Four footprint probes now read only
  the thickness, rest height and bed delta they actually need. Vehicle tick scope
  at the two bogs fell from 4.325/4.580 ms in the pre-change render trial to
  1.196/1.200 ms in the first optimized trial (different graphics configuration;
  CPU scope comparison only, not a controlled whole-frame code-only A/B).
- GTWaterDomainSheet no longer samples the domain twice per window cell, and
  queries ground only inside the authored shore envelope. Live depth and shore
  deformation still use the same physical field.
- GTMixedGroundDetails/Streaming use UE5.8 MarkRenderInstancesDirty for instance
  changes. Engine SendRenderInstanceData_Concurrent flushes tracked changes and
  updates bounds without rebuilding the complete scene proxy. Mud clumps skip
  unchanged transforms and reuse their existing full surface sample. Grass
  density, wind, bend/removal, near/far ranges and simulation are retained.
- GTItemRegistry's four reflected raw-pointer arrays converted to TObjectPtr.
  ObjectPtrDecay preserves the existing const raw-array getter API. Build and
  runtime registry snapshots succeeded. No raw reflected object-pointer array
  declarations remain in project headers under the checked source scan.
- Preset: TSR 66.667%, fixed resolution scale; mesh LOD scale 6; VSM directional
  static/moving bias 2, two SMRT rays; coarse non-Nanite pages off; clipmap last
  level 17; HZB on; ForceAllRayTracingEffects=0 and Lumen.Reflections.Allow=0;
  terrain visual upload budget 0.5 ms; VSync off; 120 cap. Normal PIE/game applies
  it and restores prior values on leaving Play. This lowers image resolution,
  shadow detail and mesh detail; it does not thin vegetation or simplify soil.
  Original preset copy: Saved/PerformancePresets/lidar_performance-before-pf120.json.

RTX4050 Laptop 6 GB, Development offscreen standalone, 1600x900, uncapped.
Below: mean FPS / p95 full-frame milliseconds. Every scene has 440 measured
frames from the existing fixed-heading LOW-range stress fixture. Loading,
teleports and screenshots are excluded. Travel length differs with frame rate;
these are short scene comparisons, NOT full rally-route or presentation timing.
The access fixture heads into trees/off-road and must not be called a rally run.

| Trial | River | Bog214 | Bog552 | Access stress |
| --- | --- | --- | --- | --- |
| pf120-render | 101.4 / 11.940 | 80.8 / 14.854 | 91.4 / 13.829 | 77.7 / 16.204 |
| pf120-contact-csm | 105.7 / 12.218 | 73.3 / 15.617 | 83.3 / 14.334 | 71.8 / 17.956 |
| pf120-lod | 104.6 / 11.154 | 84.8 / 14.211 | 94.9 / 12.461 | 76.7 / 16.354 |
| pf120-raster | 114.1 / 10.529 | 87.0 / 13.282 | 92.4 / 13.005 | 73.7 / 16.413 |
| pf120-budget | 106.2 / 10.776 | 87.5 / 13.677 | 103.6 / 11.503 | 80.0 / 15.573 |
| pf120-instances | 99.0 / 11.556 | 85.2 / 14.482 | 100.0 / 12.063 | 82.3 / 15.705 |
| pf120-adaptive | 106.3 / 10.702 | 84.5 / 14.963 | 99.4 / 12.151 | 79.4 / 15.652 |

RH3 previous comparable final: 89.9/12.944, 69.7/17.920, 71.9/17.657,
64.6/19.052, respectively. Retained PF120 graphics/code capture is
pf120-instances: 99.0, 85.2, 100.0, 82.3 fps; p99 12.693, 15.656, 13.180,
21.709 ms; maxima 25.969, 27.975, 27.582, 41.834 ms. These still exceed
8.333 ms. No whole-map locked-60 or locked-120 claim. GC pointer storage changes
came after this short capture; none of the rejected GC settings are retained.

Experiment settings and outcomes (full commands in each playperf metadata JSON):
- render: 66.667%, LOD4, VSM bias2, rays2, expensive RT effects/reflections off.
- contact-csm: height optimization, conventional shadows 1024/two cascades/0.6
  distance and RT disabled. Rejected: dense forest was slower.
- lod: 66.667%, LOD6, VSM bias2/rays2, RT effects/reflections off, uploads0.5ms.
- raster: 60%, LOD6, RT disabled, VRS enabled. Rejected: distance-field fallback
  increased GPU cost and the dense/access scenes did not improve enough.
- budget: 60%, LOD8, shadow bias3. Rejected additional visual compromises.
- instances: retained lod settings plus incremental grass/clump updates and
  redundant water-query removal. No large isolated FPS gain claimed for grass.
- adaptive: 50-75% dynamic resolution, 8.333ms budget, otherwise retained settings.
  It bottomed out at 50% in the heavy view and did not solve the bottleneck;
  rejected in favor of sharper fixed 66.667%.

Actual road-following instrumentation added via -Mode performance to
Art/check_lidar_dual_driving.ps1 and Art/Unreal/check_lidar_dual_driving.py.
It records CSV only during a 40s Waimeamea Road drive and 35s Riverside access
run, then checks water/terrain, ends PIE and checks preset restoration.
Art/tools/analyze_lidar_play_perf.py --routes <label> reports all captured
frames, including GC and streaming spikes. These are hidden PIE plus Python
controller overhead, not standalone. Requested window 1600x900; physical
viewport was not recorded in these initial captures (future runs now record it).

Retained-settings route evidence: Saved/LidarAuthoringQA/Rally/pf120-roads.json
and pf120-roads-perf.json. Range Rover: Waimeamea 532.183 m, 77.578 km/h peak,
max offset 0.33 m; Riverside 302.08 m, 46.38 km/h, max offset 0.51 m. Both passed.
All 17 profile values applied automatically and restored. Whole-capture mean FPS
66.0 / 60.2; p95 18.179 / 18.030 ms; p99 20.852 / 30.911 ms; worst frame
1290.920 / 1401.998 ms. CSV events correlate those worst frames with GC; first
route GC scope was 1258.023 ms. Do NOT hide these in the short stress results.

Rejected incremental-GC investigation:
- Tested gc.AllowIncrementalReachability=1, time limit0.001s and
  gc.AllowIncrementalGather=1 (UE labels these experimental). The normal
  pf120-gc-roads-final run averaged 69.3/66.5 fps, p95 17.635/17.308 ms,
  max32.064/32.105ms, with registry snapshots and profile restoration passing.
  However, its captures had no GC timing columns/cycle events, so those clean
  maxima do NOT prove garbage collection was fixed.
- Forced continuous incremental collection with gc.VerifyNoUnreachableObjects=1
  in pf120-gc-verify exposed a first reachability iteration around774ms, despite
  later iterations near1-2ms. The time limit is soft and the first traversal is
  not sufficiently sliced. REJECTED: all gc.* settings removed from saved v5.
  Pointer-storage cleanup retained. This diagnostic is artificial GC stress,
  not a representative FPS measurement. Do not use its FPS as normal gameplay.
- Next performance work must address the expensive first GC traversal/object
  ownership graph, plus forest/shadow render passes and moving terrain/water
  windows. Merely lowering resolution further did not meet 120.

Validation:
- Guarded builds succeeded; latest pointer cleanup build log pf120-gc-build.txt.
- Saved/Automation/PF120/index.json: nine tests passed (eight clean, RiverReference
  with unrelated HTTP connectivity timeout warning): ResponsiveSteering,
  SlideRecovery, DirectionalSoilFlow, RutWallWork, LivePush, SubstanceOracle,
  MovingDomain, RiverReference, ShoreEnvelope. These ran after contact/water/
  instance edits, before the later registry-pointer-only change.
- Actual map height oracle: 3528 native/legacy comparisons, max error
  0.000001430511 cm. Deforming the tested dry shore opened water; remote contact
  did not recenter the local water. Reports pf120-height-check and pf120-roads.
- GrassCheck initially failed because check.json had been overwritten and no
  longer held gp2c_chase camera coordinates. Fixed the test to use the dedicated
  Art/Unreal/lidar_grass_check_views.json fixture, retained from before_GS1.
  Rerun passed normally (grasscheck-process.json exit0, report_ok true).
  21982 near instances, 11736 distant; distant bins 40/80/125/150/180m:
  1260/3760/5293/1291/121. Three-layer rebuild had zero missing/extra instances.
  Bend counts after contact33/23/21, removal11/6/6; wind scale2; no far collision
  or shadows; audio mute and info-toggle checks passed. Ground/distance/contact
  images inspected in the actual LiDAR map.
- Registry runtime snapshot:24 items,15 parts,7 recipes,7 upgrades, unchanged
  across the normal incremental-GC experiment. Public getters work after storage
  conversion. Additional forced verification outcomes are recorded below.

Reproduce retained standalone capture:
  Art/profile_lidar_play.ps1 -Label <new> -UseSavedProfile -Uncapped -Drive -Probes
  Saved/Tools/TerrainPython/Scripts/python.exe Art/tools/analyze_lidar_play_perf.py <new>
Reproduce normal editor road measurement:
  Art/check_lidar_dual_driving.ps1 -Mode performance -Label <new>
  Saved/Tools/TerrainPython/Scripts/python.exe Art/tools/analyze_lidar_play_perf.py --routes <new>
Every build/editor launch used Art/wait_unreal_free.ps1 and the shared mutex.
No user editor killed, no commits, no map saves. Owner drive remains the feel gate.

PF120 final diagnostic outcome (2026-10-21 UTC): pf120-gc-verify completed and
Unreal exited normally. 248 incremental cycles completed;251 no-unreachable-
reference verification passes;900 reachability iterations, worst998.01ms.
No GC reference errors/assertions. Registry24/15/7/7 and preset restoration passed.
Forced continuous-GC routes covered77.122m /67.054m, peak42.00/40.38km/h;
7.4/7.5fps means, p95 802.110/799.815ms, max1025.699/855.089ms. These artificial
stress timings demonstrate WHY the experimental collector settings were rejected;
they are NOT normal-game performance. Retained v5 contains17 commands and NO gc.*
overrides. Normal gameplay corresponds to pf120-roads, with the documented
60.2-66.0fps editor averages and periodic collection hitches still unresolved.
Do not attribute pf120-gc-roads-final's clean maxima to a proven GC fix.
The explicit test-only GT_DUAL_DRIVE_GC_STRESS=1 flag now supplies its own three
experimental collector commands, continuous collection and reference checking;
these are never written to the gameplay preset. The object iterator used by the
registry test is explicitly destroyed before driving, so it cannot retain a GC
pause. No Unreal process left running at completion. 120fps remains an open target.


## RH4: deliberate steering reversal and rally runoff, 2026-10-23 UTC

### Diagnosis and scope

The existing RH3 response made initial keyboard turn-in faster, but its 6/s rise
and 8/s fall still require about 292 ms to move from full steering one way to
full steering the other way. The vehicle must first unwind the existing angle;
a fast first tap therefore did not establish fast countersteer. Frame hitches
can add a separate delay. Existing RH1 post-peak recovery is already 0.75;
adding another grip or yaw correction without isolating the problem was not
justified.

Audited keyboard input, Chaos's actual filter, speed steering curve, wheel
geometry, tyre force/load/friction circle, chassis slip and braking. The native
steering curve uses MPH correctly. With 35-degree lock and AngleRatio geometry,
mean front angle is approximately 8 degrees at 80 km/h and 6 at 100 km/h. This is
a real limit, but no full-input saturation above 70 km/h occurred on the complete
controlled laps. That does not prove every faster bend has enough authority.
Full braking/throttle still compete with lateral force; the recovery curve is
not unlimited grip.

The first path driver failed the final return bend with both baseline steering
and an experimental 35% full-input steering reserve. It countersteered late and
used opposite-key taps to trim overshoots, producing large slip while braking.
The extra-lock experiment did not fix it and was removed completely. Rejected
source and raw traces remain under Saved/RallyHandlingQA/rh4-rejected-lock-reserve
and corners-rh4-{control2,reserve}.json. Do not attribute those failures entirely
to the car, or present the rejected experiment as a retained assist.

### Retained changes

- GTResponsiveSteering.h and GTCarPawn.cpp accelerate only a deliberate full
  opposite-direction input: rise/fall up to 12/s during that reversal. Strength
  blends from zero at 30 to full at 60 km/h and uses the existing surface/range
  gate. Ordinary initial turn-in stays 6/s and release stays 8/s. Partial analogue
  input is unchanged. Releasing the key, reaching the requested angle (including
  damaged steering bias), disabling the option or entering low range cancels it.
  Faster authored rates remain faster. No yaw or slip signal chooses steering.
- gt.Vehicle.CountersteerResponse 0 restores RH3 reversal response; 1 is the new
  default. GTCarPawn.h exposes reversal state for diagnostic checks. Final bias
  cancellation was compiled/tested after the full laps; all fresh lap/probe cars
  had zero bias, so that guard does not change their measured behaviour.
- GTSoilVehicleMovement.cpp/.h adds a read-only, physics-locked solver report:
  applied filtered input, actual wheel angles, slip, friction forces and loads.
  The original Chaos ProcessSteering receives the original input unchanged.
  Engine DebugLatForce and stored network VehicleInputs were not valid telemetry
  on this path; the corrected report captures the ProcessSteering argument.
  The earliest all-zero filtered-input traces are explicitly marked invalid for
  saturation analysis, while their actual wheel/force samples remain usable.
- GTProceduralGround.h/.cpp adds LandscapeRecessDepthCm, retaining 400 cm as the
  default for existing maps. The existing rally author uses 5 cm. The Recess
  workflow backs up assets, uses the already captured base (never recaptures the
  recessed terrain), rebuilds, saves and reloads. Backup:
  Saved/RallyHandlingBackups/recess-1792789691069757900. Recess exited 0; 297 dry,
  nondeforming Gravel samples, 12 service cars and seven checkpoints passed.
  The LiDAR map hash was unchanged. No replacement test level was created.
- Art/rally_handling.ps1 adds guarded Recess/Corners/Tests modes, labeled evidence,
  fleet selection and a CountersteerResponse switch. check_rally_corners.py and
  analyze_rally_corners.py capture and summarize complete corners. The existing
  dual-driving tool adds explicit reversal and offroad regression modes.

Mass, suspension, drivetrain, tyre curves, available steering lock, RH1 grip
recovery and saved v6 graphics settings are unchanged. GTSlideRecovery.h and
Art/lidar_performance.json match the pre-tuning SHA-256 snapshot. Audio stays
muted. All editor/build work uses the shared reservation; no Unreal was killed.

### Response and complete-corner evidence

Controlled live reversal probes used real A/D keys, with initial speed injected
only to isolate input response. At 80 km/h, time from the scheduled opposite key
to 90% opposite filtered input was:

| Car | RH3, ms | RH4, ms |
| --- | ---: | ---: |
| Range Rover | 332 | 185 |
| BMW E39 Touring | 297 | 194 |
| Suzuki SJ413 | 296 | 200 |

Peak available wheel angle remained about 8.1 degrees. All 12 high/low probes and
six comparisons passed in-world. Low-range response/reversal gates stayed zero;
short-run peak angle variation was within 10%. This timing test is not a corner
or acceleration test. rh4-reversal.json reports the in-world result separately
from rh4-reversal-process.json: Unreal returned -1073741819 after normal shutdown
logging, so the strict wrapper correctly failed. The shutdown issue remains.

Controller version 2 uses 80 ms minimum A/D pulses, releases overshoot rather
than tapping opposite steering, and accounts for body sideslip in its requested
angle. This is an automated test driver, not a gameplay assist. From rest it
uses throttle/brake, plans corners for 3.4 m/s2 and brakes at 3.0 m/s2, with a
100 km/h ceiling. No speed injection, yaw torque or path teleporting occurs
within the lap. Start/finish exclude approximately 20 m of the 1.54 km circuit.
Baseline and final both completed all sections and exited 0.

| Car | Peak km/h, final | Max offset m, RH3 / RH4 | Max body slip deg, RH3 / RH4 |
| --- | ---: | ---: | ---: |
| Range Rover | 95.57 | 2.47 / 3.41 | 4.22 / 4.30 |
| BMW E39 Touring | 88.38 | 1.75 / 1.71 | 4.23 / 4.45 |
| Suzuki SJ413 | 79.85 | 1.85 / 1.91 | 3.72 / 4.02 |

These are single nondeterministic laps. They establish complete-corner execution
and fleet differences, not uniformly better tracking, large-slide recovery or
owner acceptance. The Range Rover offset worsened. Its effect on keyboard feel
must be evaluated by the owner before further tuning. Evidence:
Saved/RallyHandlingQA/analysis-rh4-final.json combines corners-rh4-driver2-control
and corners-rh4-final, with per-section entry/exit, slip, wheel/load/force traces.

### Frame-time evidence and limitations

Final native engine frame samples cover the whole driving interval, including
hitches, on the RTX 4050. Offscreen PIE requested 1600x900 but the reported actual
viewport was 1274x682. Python control and telemetry are included. These are not
standalone 1600x900 presentation benchmarks or proof of a locked frame rate.
Saved v6 remains TSR 75%, LOD4, VSM bias1/rays4, cap120; no quality reduction.

| Car | Mean ms | p95 ms | p99 ms | Worst ms |
| --- | ---: | ---: | ---: | ---: |
| Range Rover | 11.925 | 13.142 | 13.895 | 162.300 |
| BMW E39 Touring | 11.837 | 13.299 | 14.072 | 180.557 |
| Suzuki SJ413 | 12.011 | 13.672 | 14.815 | 178.782 |

The 8.333 ms target is not met. Saved/RallyHandlingQA/rh4-final-csv.json includes
CPU/GPU columns and raw CSV filenames. GPU means were 7.78/9.65/10.06 ms. The
current hitches are not attributed to GC: these captures have no collector-cycle
columns, and the Python driver may contribute. Earlier LiDAR GC findings remain
unresolved. No experimental collector setting or graphics reduction was retained.

An instrumentation defect polluted the first BMW/Suzuki baseline capture frame
with prior-car JSON serialization (759/1591 ms). Raw data is retained, but those
are not game GC hitches. Final capture starts after parked serialization drains
and stops before output formatting. The remaining 162-181 ms final hitches are
inside the captured driving intervals and are included above.

Startup preset application is retained to avoid mid-PIE graphics mutation, but
corners-rh4-control still hit an engine SparseArray assertion before driving.
The earlier recorded render-thread crash and later shutdown failures are not
resolved by this handling work. Keep process status separate from in-world QA.


### Final validation and owner drive

Final Development Editor build succeeded (rh4-release-build.txt). All ten tests
in Saved/Automation/RallyHandling-rh4-release/index.json passed without warnings,
process exit 0: ResponsiveSteering, CountersteerResponse, SlideRecovery,
DirectionalSoilFlow, RutWallWork, LivePush, SubstanceOracle, MovingDomain,
RiverReference, ShoreEnvelope. Reversal tests exercise the real Chaos filter at
30/60/120 Hz in both directions, exact low-range bypass, release/partial-input
cancellation, blended strength, faster authored rates and damaged steering bias.
Python source compilation also passed.

Live low-range logging regression, rh4-offroad.json: Range Rover travelled
43.414 m (pass), BMW -1.886 m (five-second stall, fail), Suzuki 6.701 m (below the
10 m threshold, fail). The overall route result is false; do not relax the
threshold or flatten fleet capabilities to hide it. Prior documented results
were 52.494/-1.893/10.412 m, with no deterministic paired baseline. All sampled
response weights and reversal directions were exactly zero, and native tests
prove the original filter is restored. This supports bypass preservation, not a
claim that every off-road performance metric is unchanged. No soil, suspension,
power, low-range gearing or wheel-force coefficient was retuned.

Live river/terrain checks passed: remote contact left radius 4488.791 cm
unchanged with zero remote impulse; shore deformation changed -1.169 to -3.418 cm
and opened 1.523 cm of water. All 3528 native/legacy contact-height comparisons
agreed within 0.000002385 cm. The run then returned -1073741819 during shutdown;
rh4-offroad-process.json records that failure separately. No map was saved.

Reproduce from C:\GrandTour (each launcher waits and reserves the Unreal slot):

    powershell -NoProfile -File Art/rally_handling.ps1 -Mode Play
    powershell -NoProfile -File Art/rally_handling.ps1 -Mode Play -CountersteerResponse 0
    powershell -NoProfile -File Art/rally_handling.ps1 -Mode Corners -Label owner-baseline -Fleet -CountersteerResponse 0
    powershell -NoProfile -File Art/rally_handling.ps1 -Mode Corners -Label owner-candidate -Fleet
    powershell -NoProfile -File Art/rally_handling.ps1 -Mode Tests -Label owner-check
    powershell -NoProfile -File Art/check_lidar_dual_driving.ps1 -Mode reversal -Label owner-reversal
    powershell -NoProfile -File Art/check_lidar_dual_driving.ps1 -Mode offroad -Label owner-offroad

Close a running game normally before requesting another launch/build. For a
build, run Art/wait_unreal_free.ps1 as its own command, then Art/build_guarded.ps1.
Review uses the retained startup graphics preset; never apply it mid-PIE.

Owner drive in /Game/GrandTour/ArtTests/RallyHandling/L_RallyHandling:
1. Start with Range Rover. W accelerates, S brakes, A/D steer, Space handbrake.
   F1 toggles driving information. Use 1 (acceleration), 2 (fast right),
   3 (linked bends), 4 (sweeper), 5 (hairpin approach), 6 (crest). Each reset
   starts in high range with open diffs. Drive whole corners and their exits.
2. Compare ordinary taps against deliberate left-to-right/right-to-left changes
   at 60-90 km/h. Lift/brake into a slide, unwind, then countersteer and exit.
   Assess delay, overshoot, predictability and whether lifting/braking is useful.
   Do not judge only maximum wheel angle or straight-line acceleration.
3. Use the console command gt.Vehicle.CountersteerResponse 0, repeat the same
   section, then set it to 1. Keep the other assists/settings unchanged for A/B.
4. Press 7 for service, F to exit, E to open the menu, scroll to BMW E39 Touring
   or Suzuki SJ413, and T to collect. Compare rear-drive and short-wheelbase
   behaviour on the same corners. V toggles low range; its original input
   response should remain intact. Re-enter the LiDAR map for actual mud/river use.
5. The broad 4 m runoff trench is replaced with a 5 cm recess. Evaluate brief
   gravel-edge excursions and recovery. Avoid treating the terrain repair as
   evidence of more tyre grip. Use stat unit if evaluating frame pacing in the
   interactive game; hidden-editor measurements include extra test overhead.

The owner keyboard drive remains the final feel gate. This is a bounded,
measured reversal-response candidate, not a declaration of FH4-quality handling,
large-slide mastery, universal off-road route success or 120 fps.


Final visual/functional review (2026-10-23 UTC): Review report and process both
passed, exit 0. Rechecked 297 firm dry samples, seven resets, high range/open
diffs, 12 service cars, 98.18 km/h straight smoke, live dust and BMW service swap.
Overview/Driving/ServiceMenu PNGs were visually inspected; the old broad runoff
trench is absent in the matching driving view. Prior images remain in
Saved/RallyHandlingQA/pre-rh4-review. Current evidence is also frozen in
Saved/RallyHandlingQA/rh4-final-review to protect it from future Review runs.
LiDAR map unchanged. This clean run does not erase earlier engine failures.

Interactive handoff: guarded Play launched L_RallyHandling with response1,
-NoSound, saved v6 and requested1600x900; map load completed, PID24644 left
running for the owner. Log: Saved/Logs/RallyHandling-Play-rh4-owner.log. Startup
still reports missing Nanite materials / landscape displacement disabled;
this same diagnostic is present in the pre-task2026-10-22 Review log. The fixed,
nondeforming circuit checks pass, but this is not a new displacement-quality
validation. No further editor/build is permitted while this game is open.


## RH5: physical gravel texture, thrown chips and steering body roll (2026-10-23/24 UTC)

Owner feedback after RH4: improved steering, but too smooth, no flying gravel,
and too little sway under steering. Audit found that firm-road generation
removed all fine relief; GTSprayArt recognised legacy gravel patches/materials
but missed authored Gravel over the generic collision material. Existing dust
was working. The external dust coordinator suppresses dust only, not grit.

Retained changes:
- GTProceduralRoad.FirmRoughnessCm defaults to zero for existing roads. This
  circuit uses 4 cm bounded, positive, nondeforming relief with three wavelengths
  and different left/right phases. Road edges taper out; the 5 cm backing recess,
  firmness, wetness and apron remain as before. Saved/reloaded measurements at
  520 straight samples added 0.103-3.950 cm (range 3.848 cm); all 297 carriageway
  samples remain dry, firm Gravel. No new level or LiDAR map edit.
- GTSprayArt uses authored contact classification before legacy fallback. Gravel
  throws 2.5-6 cm chips, with steering-aware backward/upward velocity. An initial
  1.5-4 cm capture was too subtle; the final visual-only adjustment also raised
  launch speed from 230 to 300 cm/s plus the existing bounded spin contribution.
  Emission rate is unchanged by that adjustment; legacy gravel keeps its sizes.
  Braking slip no longer reverses the authored-gravel throw. Airborne, mud/snow
  patches and water deeper than 2.5 cm reject gravel; wetness suppresses dust.
  Existing dust ownership, particle budgets and assets remain in use.
- GTSoilVehicleMovement has per-instance RallySuspensionCompliance=0.2. Above
  30-60 km/h on firm ground it blends to 80% of each car's original spring rate
  and 35% of its original anti-roll coupling. Damping coefficients follow sqrt
  of spring scale. Original masses, travel, preload, steering, tyres and power
  are retained. Low range, soft ground/water gate, or speed <=30 restores the
  authored suspension. This is actual suspension response, not camera shake or
  cosmetic body rotation. Console gt.Vehicle.RallyRide 0/1 compares old/new ride.
- Solver suspension configs are copied into simulation-owned storage, never
  shared wheel-class defaults; original values are restored rather than stacked.
  Existing constraints are updated, not recreated. The Chaos module dependency
  supplies the native constraint setters.

The initial transient spring85 probe used UE5.8 SetSuspensionParams and exposed
inconsistent rate units between its simple simulation and constraint paths.
Its near-zero lateral acceleration/roll is INVALID tuning evidence despite
the diagnostic report's execution-ok flag. Raw feedback-rh5-audit.json is retained.
The shipped path uses the original solver units consistently; the public setter
was not retained. Failed compile/link attempts are retained separately from the
successful rh5-feedback-build-linked.txt build. The final chip-only visibility
adjustment was then compiled in rh5-gravel-visibility-build.txt; the physics
and corner measurements above refer to the same suspension/road implementation.

Paired controlled probes on the rough circuit (60 km/h injected entry velocity,
fixed steering doublet; not acceleration or whole-corner acceptance):

| Car | Original peak roll (deg) | Candidate peak roll (deg) |
| --- | ---: | ---: |
| RangeRover | 1.808 | 2.577 |
| BMW | 1.222 | 1.488 |
| Suzuki | 2.191 | 2.799 |

Candidate lateral acceleration stayed close to baseline: RR 0.613/0.610 g,
BMW 0.635/0.637 g, Suzuki 0.704/0.697 g (original/candidate).
Candidate live gravel counts peaked at 167/150/147. All shared wheel defaults
were unchanged. All three high-speed low-range probes kept ride weight zero and
scale one; switching each candidate into low range also restored scale one.
Feedback process exited 0. The closer gravel image is a visual check only.
The first visual-only capture did not update the paused camera and returned
-1073741819 during shutdown; its raw image/report are retained. The corrected
capture lets the camera update before pausing. See its separate process result.

Complete circuit, same controller version 2 and startup graphics profile:

| Car | Completed | Peak km/h | Mean offset m | Max offset m | Max roll deg |
| --- | --- | ---: | ---: | ---: | ---: |
| RangeRover | True | 91.34 | 1.263 | 4.237 | 3.54 |
| BMW | True | 78.82 | 1.130 | 2.735 | 1.84 |
| Suzuki | True | 73.70 | 1.560 | 4.275 | 3.43 |

See analysis-rh5-final.json for per-section slip/steering and the prior RH4 run.
The road itself changed and the controller is frame-driven, so this is not a
deterministic isolated suspension benchmark. Native frame distributions and all
driving hitches are preserved in rh5-validation-summary.json. Actual hidden
viewport: [1274, 682]; requested 1600x900. No 120 fps claim.
Compared with RH4, mean path offsets increased from 1.025/0.776/0.479 m to
1.263/1.130/1.560 m for RR/BMW/Suzuki. Maximum body slip increased from
4.30/4.45/4.02 deg to 7.82/10.30/13.06 deg. This pass adds terrain and suspension
movement; it is not a uniformly improved line-tracking result. Native mean frame
times were 12.182/12.089/12.542 ms, p95 13.642/13.553/14.666 ms and maxima
167.488/223.611/229.301 ms, including the hitches.

Low-range logging route: RangeRover 45.411 m, route pass=True, suspension bypass=True; BMW -1.852 m, route pass=False, suspension bypass=True; Suzuki 3.719 m, route pass=False, suspension bypass=True.
Overall off-road route ok=False; preserve the existing failure thresholds.
All sampled suspension states bypassed the candidate. River remote-contact,
shore-opening and 3528 contact-height checks are recorded in the summary. These
support exclusion/restoration, not identical fleet route performance.

Regression suite: 13 passed, 0 warnings,
0 failed; process exit 0. Covers spray, dust/mud flick, actual Chaos
steering reversal, slide recovery, soil forces and river/shore behaviour. Python
syntax passed. Graphics profile hash unchanged and vehicle audio stays muted.

Process failures remain explicit: Surface initially failed a label lookup before
editing (raw report retained), then saved/reloaded successfully but returned
-1073741819 during shutdown. Surface process is not a clean pass. Final corner
exit=0; off-road exit=-1073741819.
The earlier render/SparseArray/shutdown issues are not declared solved.
The first RH5 off-road launch was interrupted across a client-session gap before
writing a result. Its log is preserved as DualDriving-rh5-offroad-interrupted.log;
cause and exit code are unknown. It is not counted as a pass. Results above are
from the rerun on 2026-10-24 UTC.

Recovery: pre-RH5 source/map snapshots in Saved/RallyHandlingQA/rh5-source-baseline;
complete pre-surface assets in Saved/RallyHandlingBackups/surface-1792798044392105500.
LidarAuthoringBackups is historical recovery data (26.16 GiB at inspection), not
a runtime dependency; deleting it loses earlier map/material/source rollback
copies. Nothing in that folder was deleted by this work.

Owner drive: use Art/rally_handling.ps1 -Mode Play; drive sections 2/3/4 and crest
6, then 7/F/E/scroll/T to compare BMW and Suzuki. Look for small road impacts,
gravel fans and outward body lean followed by settling after steering release.
Use gt.Vehicle.RallyRide 0 then 1 on the same corner for the suspension A/B;
leave steering assists and graphics fixed. Low range V retains the original
suspension. Owner keyboard feel remains the final acceptance gate.

Interactive handoff (2026-10-24 UTC): guarded Play rh5-owner loaded the rally
circuit, PID 40392 left running, audio muted and saved graphics profile retained.
Final chip visual probe exited 0; larger chips remain small details in the chase
view, so owner judgement of readability is still required. No further Unreal
run/build while this game is open. Log: Saved/Logs/RallyHandling-Play-rh5-owner.log.
