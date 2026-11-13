# Benmore foam, spray and refraction

Scope: `L_Benmore_GaeaReview`, with isolated assets in `Gaea/WaterDetail`.
The previous `WaterRapids` assets and `L_Benmore_BeforeWaterDetail` map remain available.

The former whitewater threshold converted low-frequency noise into large white
regions. The replacement retains open water between small cellular bubble rims,
stretched strands and irregular gaps. Two overlapping short advection phases
follow the baked downstream velocity without accumulating distortion at bends.
Bubble-scale normal variation accompanies the colour. Fine detail fades when it
cannot be resolved instead of turning into a distant white sheet.

Refraction was disabled (`RM_None`, disconnected input). The new Single Layer
Water graph uses a bounded explicit screen offset from the difference between
the surface normal and the animated normal. Refraction, reflection strength and
water optical coverage fade at the signed bank distance and in very shallow
water. The engine additionally rejects depth discontinuities. `RefractionStrength`
defaults to 1 and can be set to 0 for comparison. This is screen-space refraction;
it cannot reveal geometry missing from the scene buffers.

`Benmore_RiffleSpray` is a collision-free, shadow-free batched mesh. Its 454 launch
sites come from the accepted depth/current bake, with wet neighbours required.
3,632 small droplet cards follow intermittent ballistic arcs 5–17 cm high and
drift downstream. They fade beyond 22–60 m. The animation runs in the material;
there is no actor tick or CPU particle simulation. It is ambient riffle spray,
not a new vehicle splash solver. Existing car wake/spray behavior is retained.
Spray colour is compensated for the scene's physical daylight exposure so the
small backlit cards remain pale. `spray_material(rebuild=True)` rebuilds their
animation graph; normal installation can reuse it when only colour is tuned.

Rebuild spray seeds with `Art/Blender/build_benmore_riffle_spray.py` in Blender.
Install/capture with `Art/benmore_water_motion.ps1 -Variant Detail`, then validate
in a fresh editor process with `-Variant Detail -Mode Verify`. Both commands
require the interactive editor to be closed. Captures use matched camera and
water clocks, including refraction off/on and spray off controls.

Reports and captures are in `Art/Export/BenmoreGaea/WaterDetail_20261011`.
Validation checks saved parents, compilation, runtime clocks, spray collision and
coordinate bounds, and preservation of the physical domain, queries, placements,
crossing profiles, drive map and existing vehicle spray material. This art pass
does not claim a measured frame-rate improvement or a hydraulic simulation change.

Final verification (2026-10-11): install and fresh-process runtime reports pass.
All four water surfaces advance together from 0.400 to 1.494 seconds. Saved river
and lake materials retain the refraction connection; spray collision is disabled.
The fixed-clock spray on/off image check finds 101 bright affected pixels and
zero dark ones in the close water crop. The comparison animation contains 24
engine frames over three seconds. An intermediate backup-map load hit Unreal's
world-GC assertion; final captures reuse the preserved original baseline and the
completed install exits cleanly.

## Contact foam on the accepted WaterSurface waves (2026-10-11)

`benmore_water_surface.py` now makes the existing transported vehicle aeration
read as white foam. It uses a lower concentration threshold, moving cellular
lace and broken flecks, with extra coverage on steep wake crests. Neutral pale
foam colour responds to vehicle and bank contact as well as ambient rapids;
previously only ambient whitewater brightened the grey-green foam colour.

A narrow band from the signed bank field adds broken foam in wet, shallow,
moving water. Depth, current, distance and pixel footprint suppress it in dry,
still or unresolved areas. It shares the short overlapping advection phases
with the wake texture, retaining gaps instead of drawing a solid bank outline.
The wave displacement, river meshes, precombined wave field and physics are
unchanged. This adds no textures, meshes or particle pools.

Install with `Art/benmore_contact_foam.ps1 -Mode Install`; validate saved assets
in a fresh process with `-Mode Verify`. The material-only installer backs up
both materials under `WaterSurface/BeforeContactFoam`, checks vertex shader
text, and hashes the meshes, precombine material and maps before/after. It
also compares scenery, crossing profiles, water queries and solver settings.

The vehicle review uses `Art/benmore_vehicle_waves.ps1 -Mode Review
-OutputFolder WaterSurface_Foam_20261011 -Car RangeRoverClassic`. It captures
foam off/on while the same car pose and simulation time remain paused, plus
the existing six entry/crossing/reverse/dry/driver/along-river cases. These are
functional and visual checks, not performance or handling benchmarks.
Evidence and previews: `Art/Export/BenmoreGaea/WaterSurface_Foam_20261011`.

The first rendered comparison had too much filled coverage in the wake. The
final material narrows the transported concentration envelope, favours the
fine lace over broad flecks, and perforates clumps at roughly 4.4 cm spacing.
Subpixel perforations fade to partial coverage rather than solid white. The
first full six-case run is preserved in `Iteration1`; `-FoamFocus` repeats the
along-river and dry checks after this material-only refinement.

Final result: material-only install and fresh-process verification passed, with
no shader/Python errors in the fresh verification log. The final focused drive
passed both cases with 300 sampled steps at 1/60 s, dry spray suppressed, and
identical car position/simulation time in the foam off/on pair. The accepted
vertex displacement and protected asset hashes stayed identical. View
`CarFoamComparison.gif` for that toggle and `EdgeFoamMotion.gif` for the final
fixed-clock surface captures. Car motion captures are sparse; no FPS claim.

## Focused vehicle whitewater (2026-10-11)

The next reference pass separates fresh contact foam from transported wake
history. `VehicleContactFoam` reconstructs a curved bow band, narrow shoulder
bands and a short rear wake in relative-travel coordinates. Speed, wet tyre/hull
immersion, reference water depth and source decay gate it. It follows reverse
motion too. The unused alpha channel of the existing detail texture carries
this mask; it initializes to zero and does not alter wave height, sediment,
fluid volume, buoyancy or drag.

The material uses that mask for connected white crest coverage with ragged
edges and small holes. Old transported flecks are reduced substantially, so
the whitewater reads around the car instead of filling the disturbed footprint.
Bank foam and accepted wave displacement are retained. No new textures, meshes
or particle pools are allocated.

Evidence: `Art/Export/BenmoreGaea/WaterSurface_Foam_Focused_20261011`. Use
`-OutputFolder WaterSurface_Foam_Focused_20261011` with the contact-foam installer
and vehicle review. The review drives `LandCruiser80` and includes a front-quarter
BowView in the existing 0.39 m reach at (-805, 32.5) m, in addition to the ford
cases. Test fixtures never save the map. `InitialCheck` retains the first run:
its functional assertions passed but the editor exited with an access violation
during teardown. The harness now releases its render target and world references
and allows EndPlay to complete before quitting.

Final validation: guarded native build and all four water automation groups
passed. The Land Cruiser completed seven cases including reverse, dry ground,
along-river and the deeper bow view, with 300 sampled physics steps at 1/60 s.
The paired foam capture preserved position/time. Fresh-load verification exited
cleanly with zero material/Python errors after the capture helper was changed
to unload the heavy scene before renderer shutdown. Protected geometry/map
hashes and displacement shader text remained identical. The contact mask uses
the existing 96 x 96 detail upload; its bounded coverage is recorded in
`preview-report.json`. `BowView_01.png` shows the front-quarter result.

## Softer foam and motion-aligned bow (2026-10-11)

The contact material replaces the regularly perforated pattern with warped
gradient noise, wispy fringe streaks, softer crest coverage and small normal
variation. Two overlapping downstream advection phases animate the froth.
It reuses the contact alpha channel and allocates no new textures or meshes.
The saved displacement shader, river layout and protected asset hashes are
unchanged. The pre-install materials are under `WaterSurface/BeforeMotionFoam`.

The cosmetic bow reads the rigid body's actual linear velocity relative to
the domain's undisturbed mean current. Previously its direction sampled the
car's own disturbed tyre/hull current; there was no direct steering-angle
input. A 0.14-second vector filter suppresses abrupt direction changes and
handles reverse through zero. The attached wake is shorter, leaving the older
wave packets in world space instead of swinging the whole tail with the car.
Tyre spray, buoyancy, drag and physical fluid sampling retain their live flow.

Evidence is in `Art/Export/BenmoreGaea/WaterSurface_Foam_Focused_Motion_20261011`.
The guarded build and all four native water automation groups passed. Eight
rendered vehicle scenarios passed their assertions, with 300 sampled steps at
1/60 s and a matched-pose foam toggle. The steering-isolation fixture holds
the car's translational motion while alternating full left/right steering and
offsetting its body heading. Across 121 samples the bow's maximum direction
error was 2.87 degrees, while body heading differed from motion by at least
23.67 degrees. This isolates visual orientation, not vehicle handling quality.

Install and fresh-load verification both confirmed saved materials and
preservation checks. However, the Install, Review and Verify editor processes
all returned access violation `0xC0000005` after normal shutdown logging. Their
successful assertion reports do not constitute clean end-to-end process
passes. `validation-status.json` records this unresolved teardown limitation.
`BowView_01.png` shows the resulting foam; motion GIFs use sparse captures and
are not frame-rate measurements.
