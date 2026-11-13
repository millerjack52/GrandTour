# Grass reference correction

The user rejected `grass-coverage-02` because it did not resemble the generated
environment references. The GPU result did not establish visual success.

## Reference recovered

`Art/References/Environment/approved-gravel-road.png` and `approved-ford.png`
are copies of the original concepts from this conversation, not new concepts
generated to justify the models. Their modelling cues are coherent golden fan
silhouettes, broad warm ground patches, small olive groups and readable daylight.
The scene's existing trees, route, physical surface assignments and vehicle
settings are not redesigned in this correction.

## Blender iterations

- `grass-reference-03`: replaced miniature scattered ribbons with folded fans,
  warmed the ground and opened the lighting. Rejected internally: too many
  equally tall clumps, pale highlights and a continuous wheat-like silhouette.
- `grass-reference-04`: darker saturated gold, one fan per patch, wider height
  variation. Rejected internally: the small clumps exposed too much smooth
  underlayer and some read as evenly scattered dots.
- `grass-reference-05`: standing and low companion fans per patch, broad tapered
  blade faces and a narrower height range; broad colour planes baked into the
  meadow mesh. The ground remains continuous through distance culling.

Before/iteration renders and source snapshots are under
`Art/Export/RoadFordStyle/GrassIterations`. Current review images are real Blender
renders. They are not image-generated approximations of the implemented models.

## Scope and performance controls

Five shared slope meshes remain, now 120 triangles / 24 folded blades each,
versus 198 triangles / 66 small ribbons previously. Each mesh uses one opaque
vertex-colour material. No new textures, masked cards, wind or runtime updates.
Instancing, no collision/shadows, and 25–42 m fade/cull are retained. Blender's
grass shadow visibility now matches the imported no-shadow policy.

The meadow colour planes use existing terrain triangles and vertex colours,
without an extra texture lookup. Terrain vertex positions are unchanged.
Existing tall tussock materials shift toward ochre/gold. Tree models and their
material definitions are unchanged.

Blender review lighting uses sun 2.5, cool fill strength 0.5, and a lighter blue
camera sky; AgX and exposure remain unchanged. In the isolated Unreal map,
sun intensity changes 8 to 9.5 and skylight intensity 1 to 1.25. These are local
review-map settings, not edits to global look/weather values. Blender and Unreal
lighting units are not interchangeable; final engine appearance is not certified
by the Blender render.

## Validation

Imported successfully as `grass-reference-05`, with 31 source meshes and 11,930
instances, including 9,249 grass patches. All 2,681 previous dressing placements
compare identical to the baseline. All five grass meshes pass the reusable
library check: 120 triangles, one material slot, vertex alpha storing blade
height for the existing distance fade. This is a 39.4% source-triangle reduction
per grass mesh. Import settings retain the five no-shadow instanced components
and the 25–42 m cull range. Tree trunk collision hull verification still passes.

Source/library: `Art/Export/RoadFordStyle/RoadFordStyle.blend` and
`GrassCoverage.blend`. Current image: `Dry_road_driver_view.png` in that folder.
Evidence: `unreal-import-report.json`, `grass-library-validation.json` and
`GrassIterations/reference-05/validation.json`.

The prior 0.293 ms opaque-pass result belongs to the rejected coverage-02 build.
Fresh profiling for this revision completed in four cooled Off/On/On/Off runs,
900 frames each, analysing frames 300–849. CSV metadata verifies DX12 at
1440 × 900, 100% screen percentage. No thermal slowdown was observed.

| Metric | Grass off | Grass on | Difference |
|---|---:|---:|---:|
| GPU time, average of run medians | 9.280 ms | 9.323 ms | +0.044 ms |
| Opaque base pass, average of run medians | 0.012 ms | 0.238 ms | +0.226 ms |
| Game thread, average of run medians | 1.918 ms | 2.056 ms | +0.138 ms |
| Mean frame time | 11.169 ms | 10.591 ms | -0.578 ms |

The total GPU delta is small and within observed run variation. The opaque
pass shows the grass's measurable cost; it is not zero-cost rendering. Lower
mean frame time is not evidence that grass improves performance. As before,
these are stationary driver-height tests with Kuwahara disabled equally in both
variants, not a complete driving/region-scale performance guarantee.

Evidence is preserved in `GrassIterations/reference-05/grass-performance.json`
and `grass-profile-runs.json`; raw CSV files are in
`GrassIterations/performance/grass_ref05_*.csv`. The current build is a revised
visual candidate, not user-approved art. The saved concepts remain the target.
