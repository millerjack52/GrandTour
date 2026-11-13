# Benmore rivers: simulate once, render from the bake

The first reach uses the gully north of the road loop. This is an authored flowing
stream, not a claim that the LINZ DEM proves a perennial river. Its source discharge
is an art parameter. The existing DEM supplies the bed; separate terrain-fitted
gravel banks contain the channel across the shallow fan. The lake sets the outlet.

## Implementation plan

1. Survey the DEM and select a drainage line clear of both roads.
2. Author terrain-fitted banks and run a conservative 2D Saint-Venant shallow-water
   model over the combined DEM and bank surface.
   Validate resting water, wet/dry transport, water balance, discharge and outlet.
3. Bake the mean surface, XY velocity, depth and a foam potential into mesh/data
   assets. Keep full-precision arrays and the authoring controls for another bake.
4. Use Single Layer Water with flow-advection of procedural ripples and foam.
   Clear only channel foliage, reuse the gravel assets on banks, preserve roads.
5. Reload and inspect the saved reach close up and in the long vista.
6. Break the dry banks into mineral and planted patches, with grounded rock
   groups and a few sheltered willow clusters. Preserve the settled flow bake.
7. Resolve the coarse background terrain/lake-mask junction at the outlet,
   then check the saved close, reach, overlook and mouth views.

## Scope

The delivered authoring model resolves gravity, water level differences, rough-bed
resistance, wetting/drying, momentum advection and conservative intercell flow.
It uses Rusanov finite-volume fluxes with hydrostatic reconstruction, a CFL time
step and semi-implicit Manning friction. It does not solve 3D overturning or
sediment transport. Foam is a procedural
rendering mask derived from flow/depth/strain, not a simulated bubble field.

The runtime surface is static geometry with animated shading. It has no ticking
fluid grid. This first environmental pass does not register the bake with the
vehicle water subsystem: no baked-current buoyancy, flooding or wheel wakes are
claimed. Existing live ford simulations remain available for a future crossing.
Changing discharge, bed geometry or the outlet level requires a new bake.

## Files and rebuild

- `Art/tools/survey_benmore_rivers.py`: drainage inspection.
- `Art/tools/bake_benmore_river.py`: simulation, numerical checks, data export.
- `Art/tools/benmore_shallow_water.py`: finite-volume solver and validation cases.
- `Art/tools/prepare_benmore_river_assets.py`: surface clipping, vegetation mask,
  bank placement data.
- `Art/Blender/export_benmore_rivers.py`: FBX surface export.
- `Art/tools/validate_benmore_river_geometry.py`: triangle orientation, finite
  coordinates, conservative road clearance and source-height hash checks.
- `Art/Unreal/benmore_river_material.py`: flow-advection and river-local ground.
- `Art/Unreal/setup_benmore_rivers.py`: map-owned asset installation.
- `Art/Unreal/check_benmore_rivers.py`: reload, preservation and view checks.
- `Art/tools/prepare_benmore_riverbank_art.py`: numeric bank-cover weights and
  deterministic dry-bank placements, separate from the hydraulic bake.
- `Art/Unreal/benmore_river_bank_art.py`: river-owned materials, placement and
  native ground-contact checks.
- `Art/Unreal/refine_benmore_riverbanks.py`: apply just the bank art without
  rerunning the flow solver; Unreal must be closed before launching it.
- `Art/tools/prepare_benmore_river_mouth.py` and
  `Art/Blender/export_benmore_river_mouth.py`: high-resolution source DEM apron
  and local lake coverage at the outlet beyond the gameplay landscape edge.
- `Art/Unreal/benmore_river_mouth.py`: apron, backdrop cutout and shared river/lake
  water shading, plus native coordinate and collision checks.
- `Art/Export/BenmoreRivers`: full precision data, reports and review images.

Run `Art/build_benmore_rivers.ps1` with Unreal closed for the complete rebuild.
Use `-Prepared` to import and review already exported FBXs without repeating the
simulation or mesh export. The wrapper guards both UnrealEditor and
UnrealEditor-Cmd and disables background throttling for the review.
Use `Art/build_benmore_rivers.ps1 -ArtOnly` to regenerate just the dry-bank
materials and placements from the existing bake, then save and capture views.
Use `Saved/Tools/TerrainPython/Scripts/python.exe` for the individual data scripts.
The authoring environment uses numpy, scipy, rasterio, Pillow, matplotlib and
numba. Export with Blender 5.1, then run the Unreal setup with one editor process.
The original composition map is backed up as `L_Benmore_BeforeRivers` before edits.
Runtime destination: `/Game/GrandTour/Demo/BenmoreRoads/Rivers`. The six bank meshes
have collision matching their visible surface; the original landscape heightfield
is unchanged. For a major route/discharge redesign, start from the map backup so
previously cleared authored foliage is restored before applying the new footprint.

## Technical references

- [Audusse et al.: A Fast and Stable Well-Balanced Scheme with Hydrostatic Reconstruction for Shallow Water Flows](https://publications.imp.fu-berlin.de/478/1/file_2004_siam.pdf),
  the hydrostatic reconstruction used with the bake's finite-volume fluxes.
- [Valve: Water Flow in Portal 2](https://cdn.akamai.steamstatic.com/apps/valve/2010/siggraph2010_vlachos_waterflow.pdf),
  staggered flow-advection phases to limit cumulative distortion.
- [Epic: Single Layer Water](https://dev.epicgames.com/documentation/unreal-engine/single-layer-water-shading-model-in-unreal-engine),
  reflection, scattering and absorption on an opaque or masked water surface.

The source elevation remains LINZ CC-BY 4.0, as documented in `BENMORE_FULL_SITE.md`.
Numerical flow maps, bank masks and procedural waves are not sourced photography.

## Validation status

The bake follows a 1,502 m path with a 1 m simulation grid and 170,535 active cells.
It ran for 2,480 simulated seconds (63,429 steps) at an authored inflow of 6 m3/s.
The final measured outflow after the lower-bank rebake is 5.997 m3/s (0.05%
difference); the maximum change in depth over the final 40 s is 1.58 mm.
Water balance error is 1.39e-8 m3. Still-water
and closed wet/dry dam-release checks passed, with no positivity correction.
No wet river cells reached an artificial corridor wall. The connected wet area
is 18,360 m2 including the mouth; sampled road-edge clearance is at least 170 m.

The 10th/50th/90th/99th depth percentiles are 0.065/0.336/0.810/1.212 m. Speed
percentiles are 0.236/1.253/2.542/3.049 m/s. Those are authoring-model outputs,
not surveyed measurements. World XY velocities fit the texture's +/-6 m/s range
without clipping. The water has 41,222 triangles; six bank meshes add 64,824.
There are 1,700 existing gravel-mesh instances on the banks. These are asset counts,
not a frame-time benchmark.

Saved in `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive`. All twelve imported
mesh coordinate checks passed. Seventy-six native bank collision traces differ
from the visible surface by at most 1.80 cm, at the bank's buried outer seam.
All mesh vertices have a conservative road-edge clearance of at least 157 m.
The saved map retains 5,704 road gravel and 52,104 verge instances. Sixty-six
existing scrub instances were removed from the new bank/channel footprint.

The 1,700 bank stones use the exported mesh triangles instead of bilinear
interpolation. All basal points are seated at least 4.5 cm into the combined
ground in the current setup's numeric check. In the original grounding pass,
132 native traces confirmed a maximum gap of -4.45 cm and the largest placement
correction was 12.4 cm. Those historical trace results are in
`stone-grounding-validation.json` and `geometry-validation.json`.

The initial close-up, reach and established overlook were captured and inspected.
Bank gravel was then enlarged to a 12.5 m texture repeat, and the final close view
was refreshed after the stone correction. The reach is north of the driving loop;
`Benmore_River_Camera_Close` and `Benmore_River_Camera_Reach` are saved review cameras.

The second bank pass replaced the continuous pale gravel strip with coherent
gravel, silt, damp-edge and warmer soil patches. The same numeric cover weights
originally placed 4,900 approved L_TussockStyle tussocks, 360 low shrubs, 76 low rock
exposures with a local schist material, and ten existing young willows in five
downstream groups. Open gravel remains between the planted patches. The trees
and larger rocks have collision; the small foliage does not. New detail is owned
by the `Benmore_River_Art_` actor groups and can be rebuilt independently.

Those were dry-bank additions without a hydraulic rebake. The subsequent
lower-bank pass below changes the authored bed and reruns the simulation.
Future changes to channel shape, erosion or in-stream obstructions must likewise
modify the authoring bed and rerun the simulation.

The bank art is checked against the exact exported triangle heights, not a
smoothed interpolation. Native traces verify the deliberately buried roots and
rock bases; exact counts and maximum gaps are in `bank-art-validation.json`.
The original bank-art pass's 173 samples were embedded by 6.9–7.6 cm; its minimum tested rock
bounding-box clearance from wet cells is 1.47 m. The mouth apron adds 33 native
collision samples with zero measured height error and a maximum imported
coordinate error of 0.002 cm.
Review images are regenerated from the
saved level, including a dedicated lake-mouth view. Before-images use the
`Before_BankArt_` prefix. The additional assets have not been frame-time profiled.

The mouth review exposed a mismatch between the 1 m river DEM and the coarse
background terrain/lake mask. A 79,754-triangle bed apron now uses the same source
DEM below the outlet, with a 1.2 cm seam burial. A river-owned copy of the backdrop
material masks the covered portion. The lake uses the shared Single Layer Water
optical treatment and a finer local shoreline mask, while complementary coverage
keeps the two water surfaces from overlapping. No bathymetric survey, erosion or
new hydraulic solve is implied by this rendering correction.

Runtime frame time, vehicle interaction and weather-dependent rebakes are not
validated by this pass. No C++ physics code or driving constants were changed.

## Lower banks and deformable-gravel study, 2026-10-08

The owner requested less prominent banks and reminded us that the eventual
terrain must deform. The accepted pre-edit exports are retained in
`Art/Export/BenmoreRivers_BeforeLowBanks`.

`Art/tools/trim_benmore_bank_crowns.py` builds a conservative minimum crown from
that accepted solve: the local maximum wet-surface head within 12 m, plus
30 cm freeboard, while preserving every previously wet bed cell. The bake uses
this envelope to trim the dry raised crowns, then performs a fresh solve.
Uniformly lowering the banks spilled across the artificial simulation boundary;
those exploratory results were discarded and never installed in the map.

The accepted revision removes 1,946.59 m3 of the original 22,041.71 m3 of authored
bank fill (8.8%). Across the 6,734 m2 lowered by more than 1 cm, the median
reduction is 26.2 cm and the maximum 79.9 cm. This is a selective reduction:
the largest hydraulically necessary fill remains 2.715 m. The source DEM is
unchanged. The fresh solve has no wet corridor-edge cells and remains connected
to the lake; discharge and conservation results are recorded above.

The bank dressing is reduced to 2,300 approved tussocks, 150 shrubs, 45 low rock
exposures and ten young willows. The 1,700 small gravel stones remain. Placements
are regenerated against the revised mesh triangles; this is not a vertical
offset applied to the old plants. Numeric minimum rock clearance from wet cells
is 1.29 m and placement-center road clearance is 153 m.

The revised saved map passed all twelve mesh-coordinate checks and 76 bank
collision traces (maximum error 1.80 cm at the buried seam). Ninety-six native
bank-art samples are embedded by 6.95–7.50 cm; the imported rock bounding boxes
remain at least 1.55 m clear of wet cells. The road/verge counts and eighteen
existing schist groups are preserved. All four saved views were inspected.
The remaining tall banks still read as continuous raised edges in places;
the lake-mouth material transition also remains visibly patchy. Neither is
claimed as final art approval. Fresh reports and image hashes are recorded in
`visual-review-low-banks.json` alongside the numerical reports.

The banks remain authored collision meshes. The separate playable gravel study
in `docs/DEFORMABLE_GRAVEL.md` reuses the existing wheel-driven field for shallow
ruts. It is not yet a whole-level deformation implementation or an erosion
model coupled to this baked river.
