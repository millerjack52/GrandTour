# Benmore water: balanced pass, 2026-10-11

The owner accepts the Gaea river's shape and requested a balanced improvement to
flow, appearance and car interaction. This pass retains the channel and depth
baseline in `/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`.

The subsequent [visible-motion art pass](BENMORE_WATER_MOTION.md) supersedes these
surface materials after the owner found this pass too visually subdued.

## Changes

- Flowing water now applies a signed force at each grounded wheel. The former
  absolute longitudinal coefficient went through rolling resistance, which
  always opposes the car's travel and cannot accelerate it with a following
  current. The new vector opposes velocity relative to the water, including at
  rest, and shares the existing resistance cap with ground resistance. The
  established zero-current/rut-water path is retained. `WaterForceN` exposes
  the actual world-XY force for diagnostics.
- Hull displacement is registered with sheets touched by wet hull corners as
  well as the centre. This removes the dry-centre delay on entry. Sheets are
  deduplicated; lift coefficients, hull dimensions and the field grid are unchanged.
- The previously prepared 2.5 cm visual-wake threshold fix in `GTSprayWater.cpp`
  is included in the verified build; the higher spray threshold remains separate.
- New `Gaea/WaterBalanced` materials use bounded, overlapping flow phases with
  continuous current speed instead of interpolated speed bins. Height and normals
  use the same sampler and clock. The four ambient texture reads, geometric wave
  amplitude bound and existing field size are retained.
- Foam breakup follows the local current, including live disturbances near the
  car, instead of a fixed diagonal drift. Smaller, less opaque flecks leave water
  visible between them. Distant unresolved flecks fade to their mean coverage.
  The shared spray material, including the separate muddy-splash work, is preserved.

The short advection/crossfade approach follows
[Alex Vlachos, Water Flow in Portal 2 / Left 4 Dead 2](https://cdn.cloudflare.steamstatic.com/apps/valve/2010/siggraph2010_vlachos_waterflow.pdf).
Our flow comes from the existing hydraulic bake and local field. This remains a
baked mean plus local disturbances and cosmetic waves; it does not add erosion,
free-surface overturning, resolved spray breakup, or a larger simulation.

## Preservation and evidence

`Art/Export/BenmoreGaea/WaterBalanced_20261011/` contains the build log, four CPU
water tests, separate gameplay regression logs, installation report, runtime
captures, and `verification-summary.json`. Before/after installation snapshots
match for all 90,872 authored instances, crossing deformation settings, physical
water queries, serialized domain bytes, grid controls, the original Drive map,
and the shared spray material. The review map saved and reloaded successfully.

The install process returned an access-violation exit status after its successful
report and normal log shutdown. The early post-reload captures also show terrain
streaming artifacts; later captures recover. The separate fresh-process driving
review completed successfully and exited cleanly; it supersedes the initial
install's process exit as the runtime verification.

The first driving review was deliberately stopped: the inherited harness picked
an arbitrary fleet car and selected Chaos gears instead of this project's custom
transmission. The corrected harness uses the driver's car, selects direction
through the proper pedals, and runs at fixed 1/60 s. It records signed wheel forces
and hull forces alongside spray and displacement. A second continuously rendered
run became impractically slow alongside Ace Combat and was stopped. The final
harness uses the existing capture gate and GPU pacing: simulation continues with
scene rendering off between pictures, then warms six rendered frames before each
paused screenshot. Capture sequences show game
states, not runtime FPS. Another game was running during this work; no performance
improvement is claimed. Final regression outcomes are in the verification summary.

The accepted run is `Review_20261011T143956`: all six cases pass (crawl, crossing,
reverse, dry ground, driver-view crossing and along-river driving), with 47 samples
and captures. All 300 measured unpaused steps are 1/60 s. Wet cases emit water;
all four dry samples have zero water emission, wheel-water force and displacement.
The along-river case holds approximately 3 m/s and is assembled into `Driving.gif`.
The optional wake on/off capture did not trigger because its bow-rate threshold
was not reached in that case; no paired comparison is claimed.

The full water gameplay regression passes. The terrain run fails forward bog
escape (7.4 m in 12 s), the faster-in-existing-ruts comparison (6 m in 9.3 s versus
8.7 s on the first pass), and the held-exit comparison (8.5 s versus 9.3 s down the
ruts). Its built/raised ford, held-current, drifting, buoyancy and winch gates pass.
These failures are reported without retuning the bog or rerunning to chase a pass.
The spray/audio regression also fails its dry-tarmac particle gate; particle caps
and audio checks pass. The car centre is at x=59.39 m just before the 60 m dirt
boundary at the relevant sample, so front-wheel entry is a possible explanation,
not an established diagnosis. This gate checks mud/dust/snow, not water particles.
The shared dry-spray system and its test thresholds were not changed by this pass.

Visual review is a first pass: flow direction and foam breakup are improved, but
the water still has broad reflections and visible procedural foam patterns.
Spray breakup and shoreline presentation remain candidates for the next art pass.
The driving checks establish functional response, not that the handling has been
accepted by the owner or that the river is now a complete fluid simulation.

## Reproduction and rollback

Build with `Art/build_guarded.ps1`; CPU water checks use
`Art/benmore_water_interaction.ps1 -Mode Tests`. Install with
`Art/benmore_water_balanced.ps1 -Mode Install`; fresh driving review uses `-Mode Review`
or `-Mode Reported`. Separate gameplay logs are generated by
`Art/tools/test_benmore_water_balanced.ps1`.

For appearance rollback, restore the prior `Gaea/WaterInteraction` material parents
and sheet surface path; the prior review map is also saved as
`Gaea/L_Benmore_BeforeWaterBalanced`. Source snapshots from before this pass are in
the evidence folder's `Before` directory. Do not reset the shared working tree:
it contains extensive independent work.
