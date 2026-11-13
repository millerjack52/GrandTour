# Benmore long-vista pass

Focus: the user's long views across the basin and lake. No new roadside props, terrain grading or vegetation scatter.

## Treatment

- Rotate the map's sun from pitch -40 / yaw -50 to pitch -27 / yaw -125. This lights the visible east-facing slopes across the lake and gives their folds more directional definition. Sun intensity changes from 8 to 10, with 6000 K temperature and a 1.2-degree source angle. Skylight intensity increases from 0.9 to 1.1 for restrained shadow fill.
- Move the existing height-fog start from 280 m to 800 m and reduce its maximum opacity from 0.52 to 0.30. Weather still drives density. This is a clearer daytime vista treatment; it also reduces the maximum opacity available to other weather states on this demo map.
- Increase broad mineral-pattern wavelengths from 43–110 m to 90–310 m. Add pale wash channels on steeper faces, reserve the darker vegetation treatment for gentler drainage bottoms, and add irregular, subdued bed variation. All masks remain tied to the real DEM and existing road exclusions.
- Strengthen the separation between straw-brown upland cover and pale grey scree. The broad geology blend reaches 86% beyond 350 m, preserving the existing close road and bank treatment.
- Replace the sky's stretched planar noise with multi-scale directional 3D noise. More defined cloud masses, brighter cloud tops and open blue areas replace the old streaks. Existing CloudCover/SkyScale controls remain. This remains an inexpensive procedural sky dome, not volumetric clouds; it does not cast cloud shadows.
- Add a masked lake sheet at 0.6 m above the terrain datum. Coverage comes from the real DEM, with a narrow turquoise shoreline transition, subtle moving ripple normals and a reflective surface. Shore colour is a visual approximation, not bathymetry. The surface has no collision or water physics.

The previous pass's 20 m background geometry and 10 m regional normals remain. Terrain/road heights and collisions, trees, tussocks, rocks, scrub and fences are retained.

## Rebuild and review

- `Art/Unreal/setup_benmore_vistas.py` rebuilds local materials/sky and applies scene lighting/fog.
- `Art/tools/prepare_benmore_lake.py` prepares the numerical lake-coverage mask. `Art/Unreal/refine_benmore_vistas.py` applies the final material refinement and builds the lake surface; run it after setup.
- `Art/Unreal/check_benmore_vistas.py` verifies saved settings, existing instance counts, canonical height hash, car wheel contact and road clearance. It captures the existing lake view plus a new high overlook at local (750, 500) m, 1.9 m above the ground, facing southwest with an 82-degree field of view. Grass warm-up is 100 seconds per viewpoint.
- Results are under `Art/Export/BenmoreVistas`. `Before_Lake.png` is the prior lake view; there is no earlier high-overlook capture.

Restore the map `L_Benmore_BeforeVistas` together with material copies under `Vistas/M_BeforeVistas_*` and the two `before_*.py` source files. The map backup alone cannot restore edits to shared local material assets. Setup records prior scene values in its report.

## Validation

Final setup, refinement and play-mode reports passed. Both 1600 × 1000 views were inspected after 100-second grass warm-ups. The saved sun/fog settings, all four background actors and collision-free lake were checked. The lake texture reports a temporary 32 × 32 resource immediately on load; the source coverage image is 1368 × 1277 and the warmed render was checked visually.

- Canonical terrain SHA remains `0eee9713accd1244a67cb4bd3976fd9bbbdb4bfdffb270a860d1439fee37a985`.
- All four vehicle wheels have ground contact; all 21 sampled road-clearance traces pass.
- Existing 5,704 road aggregate instances, 52,104 verge instances, 923 scrub plants and 348 fence parts are preserved.
- All four approved TussockStyle meshes streamed at both viewpoints, with 24 and 20 populated clusters within 100 m respectively.
- The local sky is adopted by the runtime weather system.

No C++ or shared project settings are changed in this vista pass. Unattended editor timings are not a performance benchmark. The distant hills still use broad material and terrain detail; this is a visual improvement pass rather than a photorealistic environment finish.

## Reference-led surface and middle-distance pass

The user's eight references are preserved unchanged under `Art/References/BenmoreVistas`. NZ images 2–4 guide landform and colour; game images 6–7 guide continuity from the foreground through the basin to distant ridges. Image 5 is a useful reminder that strong surface and light treatment can make an open landscape feel complete without uniform prop density.

- Replace smoothed 10 m background normals with normals derived from 5 m DEM samples, preserving drainage detail. The playable terrain adds only the difference between fine and coarse normals beyond 90–300 m; its close shading and road exclusions remain.
- Add a 2736 × 2554 regional cover mask: grass coverage, rock exposure, fine curvature and sheltered scrub. Slope and curvature come from the DEM; vegetation coverage is an art treatment rather than surveyed land cover.
- Replace the dominant smooth hill colour blend with broken grey rock, dry soil, golden grass and restrained dark scrub patches. Ground clump patterns retain 2.3 m, 8.5 m and 27 m scales with pixel-footprint fades to reduce distant aliasing.
- Add 3,771 shrubs in 42 irregular patches, using the existing three-LOD map-owned scrub meshes. Heights are 0.95–2.1 m. These patches render out to 1.75 km, have no collision or dynamic shadow cost, and are seated by landscape traces. The nearest placement is 10.77 m from a road edge. Existing foreground dressing is retained.
- Keep the existing daylight, sky and lake for the first visual comparison, so the effect of the new land surface can be assessed directly.
- After the initial comparison, reduce the excessive mottling on gentle slopes while retaining sharper rock and erosion treatment. Thin the fog to a 0.20 maximum opacity starting at 1.1 km, preserving weather-controlled density and the existing sun/skylight. This maximum also applies to other weather states on this map.
- Refine the procedural clouds with finer edge variation and light-facing density shading. This is still a sky material, not volumetric cloud lighting. Reduce lake roughness from 0.24 to 0.12, halve the fine ripple strength and reduce its emissive contribution; the existing masked visual-only water remains.

Rebuild: run `Art/tools/prepare_benmore_reference_vistas.py`, then `Art/Unreal/setup_benmore_reference_vistas.py` and `Art/Unreal/refine_benmore_reference_vistas.py`. Review with `Art/Unreal/check_benmore_reference_vistas.py`. Outputs and before captures are under `Art/Export/BenmoreReferenceVistas`. The `Initial_*.png` captures show the first surface comparison before the final balance and sky/water adjustments.

Restore using `L_Benmore_BeforeReferenceVistas` plus the four `ReferenceVistas/M_BeforeReference_*` materials (Ground, Backdrop, Sky, Lake) and the saved `before_*.py` builders. A map copy alone does not restore shared material edits.

Reference-pass validation passed after the final cloud adjustment. Both saved viewpoints were inspected at 1600 × 1000 after full vegetation warm-ups. All four approved TussockStyle meshes stream at both viewpoints, with 24 and 20 populated clusters within 100 m. The 3,771 added shrubs persist with NoCollision, all four vehicle wheels have ground contact, and all 21 road-clearance traces pass. Existing gravel, verge, scrub and fence counts and the canonical terrain SHA remain unchanged. The final fog settings and runtime adoption of the local sky are verified in `final-visual-report.json`.

The finer cloud-edge noise was reduced after visual review to avoid hard fragmented outlines. `finish_benmore_reference_sky.py` applies that sky builder and runs both captures in the same editor session. No C++, shared weather assets or project rendering settings were changed. Performance was not benchmarked; the new regional data textures and extended scrub visibility add rendering cost. Water remains the existing visual sheet with revised shading, without a dedicated planar-reflection system.

## Atmospheric daylight pass

The later lighting pass replaces the visible painted dome with the map's SkyAtmosphere and native volumetric clouds. A transparent, collision-free `GTLook.LocalSky` anchor retains compatibility with the shared look subsystem. The old sky material is preserved. Native atmosphere scattering coefficients are 0.028 km^-1 for Rayleigh and 0.002 km^-1 for Mie, with a 0.75 aerial-perspective distance scale. These are coefficients, not multipliers of one.

Sun: movable, 60,000 lux, pitch -24 / yaw -80, 5900 K, 0.75-degree source angle. The realtime skylight captures the atmospheric sky and clouds at intensity 1.0. Native cloud shadows use a 12 km extent and 0.45 surface strength. No artificial terrain shadow pattern is baked into the ground.

Cloud material: a map-owned copy of the engine's simple volumetric cloud material and its original instance. The instance supplies the cloud-pattern, height-profile and volume-noise textures; a blank instance would inherit black placeholder textures and produce an empty sky. Two MPC_Weather RainIntensity inputs increase coverage and density as rain develops. Other weather states continue to scale sun/skylight intensity and height-fog density. The cloud layer begins at 2.8 km and is 3 km thick. Coverage -0.14 and density 0.008 are the clear-weather values. Cloud coverage is driven by rain here, not the old painted-sky CloudCover parameter, so overcast without rain retains the clear coverage pattern under dimmer light.

The map-owned priority-400 post-process volume uses fixed EV100 13.6, 0.12 bloom, restrained saturation/contrast, and mild local exposure. The old priority-300 ReviewExposure volume is disabled; it otherwise forces EV 0.3 and clips physical daylight to white. The new volume takes precedence over the shared look subsystem's prototype exposure without changing C++. Ambient fog luminance is (1200, 1700, 2400), while directional fog is only (0.030, 0.028, 0.025): the renderer multiplies that directional coefficient by sun luminance. Treating both fields as absolute luminance produces a large white glow toward the sun. The previous fog start and opacity remain.

Rebuild with `Art/Unreal/setup_benmore_daylight.py`; review with `Art/Unreal/check_benmore_daylight.py`. The checker includes both clear viewpoints and a rain overlook. Outputs are under `Art/Export/BenmoreDaylight`. `L_Benmore_BeforeDaylight` restores this pass: all changed scene settings and assignments are in the map, and earlier material assets are not modified. Re-running older sky/setup builders can replace the compatibility anchor and should be followed by the daylight setup.

Daylight validation passed on 2026-10-07. The saved map was reloaded and both clear views were inspected at 1600 x 1000 after 100-second vegetation warm-ups. The final side light separates the large gullies and ridges without the former directional-fog glare. The rainy overlook was inspected after a 45-second transition warm-up; RainIntensity reads 0.70 and the native cloud layer becomes denser and darker. Exposure remains fixed, so rain has a deliberately dark storm appearance rather than automatic camera brightening.

All four TussockStyle meshes streamed at both clear viewpoints, with 24 and 20 populated clusters within 100 m. Four wheel contacts and all 21 road-clearance traces passed. The canonical height SHA, 5,704 gravel instances, 52,104 verge instances, 923 original scrub instances, 3,771 reference scrub instances and 348 fence parts are retained. The cloud texture overrides, weather inputs, exposure, disabled old review volume, realtime skylight and runtime sky-anchor adoption are checked in `Art/Export/BenmoreDaylight/final-visual-report.json`. The final editor run completed without Python or material-compilation errors.

`finish_benmore_daylight.py` applies the final exposure, cross-light and fog coefficient before running the review. Native volumetric clouds add rendering cost; the unattended editor tick samples are not a performance benchmark. A normal gameplay frame-rate benchmark remains separate. No C++ or shared project rendering settings were changed in this pass.
