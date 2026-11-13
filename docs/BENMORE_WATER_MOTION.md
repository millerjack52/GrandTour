# Benmore: stronger visible river motion, 2026-10-11

The owner clarified that the main problem was appearance and insufficient motion.
This art pass follows the balanced water work, targeting readable movement from a
stationary camera at driving distance.

The subsequent [shallow-rapids pass](BENMORE_WATER_RAPIDS.md) adds depth-directed
turbulence and whitewater over these materials, at the owner's request.

`Gaea/WaterMotion` contains new river/lake material variants and a dedicated wave
precombine. Fine ripple slopes are stronger, reflection response is less muted,
and sparse elongated foam traces travel with the authored current even without a
car. Coarse waves are taller in deeper water; their existing 22%-of-depth geometry
limit, shoreline fade, and distance fade remain. Fine waves affect shading rather
than displacing the coarse mesh. Short overlapping advection phases prevent
unbounded stretching around bends.

The source is `Art/Unreal/benmore_water_motion.py`; installation and matched
captures use `Art/benmore_water_motion.ps1`. The capture script uses identical
camera positions and water clocks before and after, with 24 frames at 0.125 s
intervals and an additional wider view. `Art/tools/preview_benmore_water_motion.py`
assembles the engine frames into `Comparison.gif` and `Motion.gif`, without
retouching the water. These are controlled three-second animation samples, not
measurements of game frame rate.

Evidence is in `Art/Export/BenmoreGaea/WaterMotion_20261011/`. The installer compares
authored placements, depth queries, domain bytes, deformation profiles, runtime
grid settings, the original Drive map, and the shared spray asset. It saves and
reloads the review map, then checks that the new precombine animates on the normal
PIE game clock. Shader compilation, those preservation checks and the actual
captured appearance are the relevant checks for this material-only change.

Validation completed: all three new materials compiled, the saved map reloaded,
and all preservation snapshots matched. Fifty images cover matched motion and
wider views. The fresh-process check passes: all four runtime surface clocks
advance together from 1.0448 to 2.1055 seconds, and that process exits cleanly.
The initial install returned an access-violation status after writing its
successful report and closing its log. An initial fresh-clock check also sampled
too soon during startup; its report/log are retained. The corrected check waits
for one full second of game time instead of assuming a two-second wall wait
contains game ticks. Run it with `Art/benmore_water_motion.ps1 -Mode Verify`.

The water-region frame differences increase from 1.76 to 6.27 mean RGB levels
per 0.125 s; the fixed-ground control remains approximately 0.49 in both sequences.
This confirms increased visible motion, not aesthetic quality or performance.
The full camera sequences are in `Comparison.gif` and `Motion.gif`; `Detail.gif`
shows a labelled, unretouched crop of the same river frames.

The earlier car/current fixes remain in place. The broader bog/rut and dry-spray
test failures recorded in `BENMORE_WATER_BALANCED.md` are not resolved by this art
pass. Motion remains cosmetic shading over the existing hydraulic current and
bounded local water simulation.

For rollback, restore the `Gaea/WaterBalanced` surface parents and the
`Gaea/FlowWaves/M_FW_Precombine` ambient material, or use the saved
`Gaea/L_Benmore_BeforeWaterMotion` map. No shared asset reset is necessary.
