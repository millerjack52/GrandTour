# Benmore landscape character pass

Level: `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive`.

The user's panorama exposed a gap between detailed nearby tussocks and a smooth, largely uniform middle distance. This pass adds terrain cover variation, sheltered scrub, short stock fences and a softer sky. It preserves the dry natural palette in the supplied location photographs.

## Ground and dressing

- The shared local landscape/backdrop shader blends pale mineral soil, straw cover and muted olive gullies using the existing DEM concavity mask. Warped 80–190 m colour patches carry through the middle distance. The blend starts at 35 m and reaches full strength at 220 m. Fine 1.45 / 4.3 / 11 m variation is filtered using its screen footprint to reduce distant aliasing. The existing bank/schist and road masks remain.
- Twenty sheltered groups contain 923 scrub plants, using map-owned copies of the existing Open and Dense RoadFordStyle meshes. Muted leaf materials, heights of 0.8–1.85 m and three LODs provide variation. Centres stay at least 9.04 m from road centrelines. Scrub is terrain-seated and culls over 380–650 m.
- Two roadside fence runs contain 90 silvered timber posts and 258 wire spans, with access gaps. Posts are terrain-seated and buried 12 cm; wires connect three heights between neighbouring posts. Fences cull over 650–950 m. These are decorative, non-colliding fences.

The canonical terrain heights, road geometry, road POM, existing rocks, 57,808 road/verge instances, willows and approved L_TussockStyle meshes are retained.

## Sky integration

`Character/M_Benmore_SoftSky` uses a blue-grey gradient and soft stretched procedural clouds. Its 100 km dome excludes shadows, lighting captures, ray tracing and scene captures and has no collision.

The actor carries `GTLook.LocalSky`. A small opt-in in `GTLookSubsystem::EnsureSky` adopts a tagged level-owned dome instead of spawning the prototype sky over it. Levels without that tag retain the existing path. The adopted material still receives the shared CloudCover and SkyScale values, and responds to `gt.Look.Sky`. No shared sky material is modified. Wind direction and sun highlights are not modelled by this first sky material.

## Rebuild and restore

1. `Art/tools/prepare_benmore_character.py`: deterministic placements from road data, final heightfield and landform mask.
2. `Art/Unreal/setup_benmore_character.py`: material and dressing setup.
3. `Art/Unreal/refine_benmore_character.py`: rebuild terrain materials and the sky without replacing dressing.
4. `Art/Unreal/check_benmore_character.py`: saved-state checks, PIE road traces, vegetation streaming and three visual captures.

Outputs: `Art/Export/BenmoreCharacter`. `refinement-report.json` and the latest `final-visual-report.json` supersede initial setup imagery. A pre-pass map is saved as `L_Benmore_BeforeCharacter`; original terrain materials are copied into `Character/M_BeforeCharacter_*`, and the pre-pass shader source is `before_benmore_bank_surface.py`. Restoring the map alone does not restore shared material edits: restore those copied materials/source as well.

## Validation

Validated 2026-10-07:

- `GrandTourEditor Win64 Development` builds successfully. Existing engine deprecation/compiler-version warnings remain.
- Terrain and sky materials compile; the saved level adopts the tagged sky as a dynamic material instance at runtime. The prototype white-cloud overlap is absent in the final captures.
- All 923 scrub instances and 348 fence parts are saved without collision. The existing 5,704 road aggregate and 52,104 verge instances remain.
- The terrain heightfield SHA-256 matches the preceding environment pass exactly: `0eee9713accd1244a67cb4bd3976fd9bbbdb4bfdffb270a860d1439fee37a985`.
- The settled car has four wheel contacts. Twenty-one road-centre collision traces hit the expected terrain within the 10 cm tolerance, with no new dressing blocking them.
- All four approved TussockStyle variants produce populated grass clusters around the review cameras. Large camera jumps require additional warm-up for visible grass; cluster bounds alone can become available before the final cover is drawn. A 100-second roadside warm-up restored full visible cover; `road-visual-report.json` passes and its `Terrace_Fence.png` supersedes the earlier roadside capture. Both review scripts now use that longer warm-up.
- Final captures use the normal `gt.Look.Post 2` rendering mode with Clear weather and HUD hidden. The initial neutral-render captures are superseded. The strongly mottled first shader was reduced to broader, lower-contrast patches during visual review.

The editor's unattended frame timings are diagnostics, not a performance benchmark. The six driving scenarios documented in the preceding environment pass have not been rerun for this visual-only terrain/dressing pass. Open rocky areas and the outer background still need future composition/landmark work; this pass is an incremental environment treatment, not a finished level.
