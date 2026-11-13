# Physical Benmore verge relief

This pass changes the landscape heightfield around the existing roads. It creates interrupted gravel/earth banks up to 56.25 cm above the former ground and shallow drainage hollows up to 34.375 cm below it. Shapes vary along each side of the road, with eroded gaps and a gradual return to the surrounding terrain. Their dimensions suit the landscape's 1.24 m vertex spacing.

The running surface is protected. Across 5,568 sampled centre/wheel-path points, the generated height change is below 0.01 mm (floating-point roundoff). Both roads participate in the exclusion calculation, protecting intersections. The source LINZ terrain package remains untouched.

`prepare_benmore_relief.py` produces the derived heightfield and a reversible baseline under `Art/Export/BenmoreRelief`. `setup_benmore_relief.py` backs up the map as `L_Benmore_BeforeVergeRelief`, imports and verifies the new landscape heights, re-seats affected dressing, saves the driving map, then updates the canonical `BenmoreRoads/height_local_south_up.f32` authoring grid. Re-running the setup uses the current canonical grid for the placement delta, avoiding cumulative offsets.

The earlier `BenmoreRoads` height PNG/R16 and transfer texture are retained as the original graded-road baseline; running the original road setup again would restore that baseline. Subsequent vegetation, scenery and verge-placement preparation reads the current canonical F32 grid. The terrain import uses the new `ReferenceSurface/T_Benmore_VergeHeightRG` texture.

`check_benmore_relief.py` reloads the saved map, probes collision across wheel paths, banks and hollows, checks the existing verge/aggregate instances and grass streaming, and captures the terrace, hillside and shoulder views. Automated editor tick timings are not a performance benchmark.

The 2026-10-07 import passed all height-transfer probes exactly and re-seated 42,687 instances. Saved-map validation passed 1,085 collision probes with no misses; the maximum wheel-path difference from the reference grid was 0.76 cm. Across sculpted shoulders the maximum difference from bilinear grid interpolation was 16.07 cm, within the 25 cm check tolerance for the triangulated 1.24 m landscape. All 52,104 verge instances and 5,704 original gravel instances remained present; all four landscape grass variants streamed. Terrace, hillside and close shoulder captures were visually reviewed, and the reload logged no material compilation errors.
