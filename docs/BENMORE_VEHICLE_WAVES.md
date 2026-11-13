# More pronounced car/water response

The car now creates a surface pressure wave when its tyres enter the river,
including before the hull or actor centre reaches the wet area. Effective visual
immersion combines wetted tyre depth/contact fraction with actual hull immersion.
Relative speed uses the current at the wet wheels; deeper hull immersion takes
over as the body enters. Dry wheels and a stationary car in still water produce
no reconstructed wake. Airborne bow spray still requires a wet hull.

The curved bow crest is narrower and taller. Three spreading wake arms and a
stern crest make the disturbed surface more readable. Speed/immersion changes
are smoothed over 0.20 seconds. On exit, the last wake drifts with the sampled
current and decays over 2.4 seconds. Raised relief is capped at 30 cm and 85% of
local reference depth; troughs retain the previous shallower bound. The existing
62.5 cm mesh and local detail texture carry both height and crest aeration.

Wheel splash sheets are slightly wider and last longer, within the existing
particle pool. This is a stronger visual response to the existing water physics;
buoyancy, tyre drag and fluid mass are not retuned. Solver wakes still run normally.

Validation: `Art/build_guarded.ps1`, then
`Art/benmore_vehicle_waves.ps1 -Mode Tests` and `-Mode Review`.
The four water automation tests include early tyre entry, relative-flow force
direction, dry/stationary suppression, bounded displacement, moving-window
continuity, and unchanged solver state under cosmetic reconstruction.
The rendered review possesses `Benmore_Fleet_Ferrari288` in crawl, crossing, reverse,
dry-ground, driving-camera and along-river cases, plus a paused-state wave toggle.
It does not save vehicle placements or the review map, and is not a handling or
frame-rate benchmark. Evidence: `Art/Export/BenmoreGaea/VehicleWaves_20261011`.

2026-10-11 result: guarded build succeeded; all four automation groups passed;
the rendered Ferrari review completed all six cases and exited successfully.
The paused relief toggle preserved car position and simulation time. The run
uploaded a maximum positive cosmetic relief of 22.75 cm, and the dry case emitted
zero wheel or bow spray. `VehicleWake.gif` contains seven captures at recorded
simulation intervals (a sparse functional preview, not a frame-rate recording).
`WaveComparison.png` compares relief disabled/enabled at the same physics state,
not the previous implementation against the new one.
