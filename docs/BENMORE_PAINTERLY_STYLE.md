# Benmore: grounded painterly direction

The user selected **grounded and painterly** after finding the daylight pass
bland. The real terrain, roads and approved TussockStyle meshes remain the
starting point. Style comes from coordinated shape, colour and detail choices.

## Visual rules

- Gold and pale straw dominate the tussock. Exposed earth is quieter and less
  yellow; sheltered vegetation introduces small areas of sage.
- Schist and shadowed gullies carry blue-grey and restrained mauve relationships.
  The lake provides a distinct blue accent.
- Broad connected areas of grass, earth and rock must read before fine texture.
  Keep the established terrain-wide plant coverage and road exclusions.
- Keep close detail selective. Distant material marks simplify without removing
  the real ridges, gullies or silhouettes.
- Pigment patterns stay attached to the terrain and respond to light. No screen
  blur, posterisation, painted-in sunlight or outlines are added.

## Reference and first implementation

`Art/References/BenmoreStyle/Grounded_Painterly_Target.png` is a concept paint-over
made with the built-in image generation tool from the actual daylight overlook.
It is not an Unreal render. The exact prompt is preserved in the same folder as
`generation-prompt.txt`. Generated foliage details and painted clouds are visual
suggestions, not a representation of implemented assets.

The first Unreal pass uses independent material copies in
`/Game/GrandTour/Demo/BenmoreRoads/Painterly`:

- Terrain colour has broader gold, soil, sage and schist areas. Large pigment
  patches use warped horizontal coordinates, avoiding elevation stripes across
  whole mountains. Finer geological marks fade with distance and pixel size.
- Background normal detail uses a footprint-dependent mip and blends in a
  softer level to reduce survey artefacts; playable terrain retains half of
  the additional fine-normal correction outside the close detail range.
- Five copied landscape grass types use a map-owned foliage material with the
  original four approved meshes, scales, LODs and cull distances. Root-to-tip
  vertex colour variation is retained and remapped into the new palette.
- The original grass-mask channels and local densities are retained. Grass
  output pins are explicitly reconnected on every rebuild and the saved graph
  is checked before capture.
- Existing rock components receive a lit, matte schist material. Geometry,
  transforms and collision are untouched. Roadside tussock components use the
  same foliage treatment as landscape grass.
- A copied lake material raises the blue body colour. Lake geometry, mask,
  normals, reflection settings and lack of collision remain as before.
- The existing map grade uses EV100 13.3, mild cool shadow colour and a 1.3
  realtime skylight intensity. The native sky, cloud material and sun angle are
  retained from the daylight pass.

This is a first material implementation of the selected direction. The concept's
individual grass shapes and painted cloud edges are not reproduced by a filter.

## Rebuild and recovery

Run `Art/Unreal/setup_benmore_painterly.py`; it saves the map and runs
`check_benmore_painterly.py`. Shader source is in
`Art/Unreal/benmore_painterly_surface.py`. `refine_benmore_painterly.py` updates
the saved terrain/hill shaders without rebuilding other materials.

The map copy `L_Benmore_BeforePainterly` restores prior assignments and lighting.
Original materials, grass-type assets and meshes are not modified. Outputs and
before screenshots are under `Art/Export/BenmorePainterly`.

Validation passed on 2026-10-07. The saved map was captured at the clear hillside,
high overlook and rain overlook, and all three images were inspected. The
hillside has 24 populated grass clusters within 100 m; both overlook states
have 20. All four approved source meshes are present. All four wheels contact
the driving surface, all 21 road-clearance traces pass, and the canonical
terrain-height SHA256 is unchanged. Existing 5,704 road aggregate instances,
52,104 verge instances, scrub and fence counts are preserved. The final review
log has no material compilation failures or Python exceptions.

Reports: `Art/Export/BenmorePainterly/final-visual-report.json` and
`grass-connections-report.json`. The final saved material uses the original
grass masks directly; the experimental density multiplier is not connected.

The unattended review temporarily accelerates grass cluster creation. The
final capture also uses the engine's `-BENCHMARK` launch flag to bypass hidden
window throttling; this is not a performance benchmark. Neither setting is
saved as a gameplay default. Visual captures remain necessary: cluster bounds
alone do not prove that the visible foreground is fully populated. All five
grass outputs are checked for direct connections to the established mask.

## Long-vista material and lighting study

The next approved pass targets the overlook's smooth middle distance. It uses
numeric masks derived directly from the existing LINZ DEM in the repository's
Python/rasterio pipeline. Gaea was researched as an authoring option; these
particular masks are not Gaea exports.

`Art/tools/prepare_benmore_vista_study.py` creates a 5 m material-control map:
drainage/sheltered hollows, steep exposed rock, a soil-settlement proxy, and
local terrain relief. Drainage uses downhill D8 accumulation with no depression
filling; this is visual material guidance, not a land-cover or hydrology survey.
The canonical gameplay heights remain unchanged.

`Art/Unreal/benmore_vista_study_surface.py` uses this data to connect darker
sage-brown gullies, mineral exposures and lighter soil tongues. Surface cover
has approximately 1.7 m, 4.8 m and 17 m pattern scales. They fade with pixel
footprint, filling the previous detail gap after the close texture disappears.
The original grass-output channels, meshes and density settings are retained.

`setup_benmore_vista_study.py` creates separate terrain, hill and cloud-instance
assets under `/Game/GrandTour/Demo/BenmoreRoads/VistaStudy`. The study changes
the skylight intensity to 1.15, cloud pattern scale to
320, clear coverage to -0.09 and cloud surface-shadow strength to 0.70. Exposure
stays at EV100 13.3. The -24 degree pitch / -80 degree yaw sun direction is
retained because it gives the ridge faces clearer shading. Cloud rain control
retains the existing weather material. Noise contrast is limited so geological
features and lighting remain stronger than the surface pattern.

The map `L_Benmore_BeforeVistaStudy` retains the previous materials and lighting.
Before/after captures and numeric reports live in `Art/Export/BenmoreVistaStudy`.
Validation passed on 2026-10-07. The clear overlook, clear hillside and rain
overlook were captured at 1600 x 1000 and visually inspected. The final pass
keeps the ridge shading readable, adds surface variation through the middle
distance, and reduces the mottling seen in the first trial. Foreground rock
surfaces and additional scenery remain separate art work.

All four approved tussock meshes are present, with 20 populated clusters within
100 m of the overlook and 24 at the hillside. All four wheels contact the
driving surface and all 21 road-clearance checks pass. The canonical height
hash, 5,704 aggregate instances, 52,104 verge instances and existing scrub/fence
counts are preserved. Rain control reaches 0.70. The final review log has no
material compilation failures or Python exceptions.

Reports are `Art/Export/BenmoreVistaStudy/setup-report.json`,
`geography-report.json` and `final-visual-report.json`. The final engine log is
`Saved/Logs/BenmoreVistaStudyFinal.log`. The same unattended capture settings
described above apply; tick timings are diagnostics, not a performance result.

## Overlook vegetation and outcrop composition

This pass adds nine connected scrub/tussock bands and 18 schist exposures
selected for visibility from the established overlook. Planting follows real
terrain hollows, with variable widths, lengths and gaps. A numeric coverage
map carries the planted patches into the ground material at distance. Existing
landscape grass outputs and their approved L_TussockStyle assets are preserved.

`prepare_benmore_composition.py` creates the placements and coverage map.
`build_benmore_schist_exposures.py` builds terrain-fitted wedges with broken
strata and small downslope fragments. `export_benmore_composition.py` exports
their sharp face normals and vertex masks from Blender. `setup_benmore_composition.py`
imports the assets, checks geometry coordinates and basal support, and saves
the level. `check_benmore_composition.py` checks both road routes and captures
the matched overlook, a branch-road view and the hillside.

The study assets live under `/Game/GrandTour/Demo/BenmoreRoads/Composition`.
Only the study's prefixed actors are replaced on a rebuild. The original
shared meshes/materials remain intact; `L_Benmore_BeforeComposition` preserves
the previous map. `Art/Export/BenmoreComposition` contains source geometry,
placements, the editable Blender file, before/after captures and reports.
No buildings or shelterbelt have been added in this pass.

The pass is saved and the final overlook and branch-road captures were
visually inspected on 2026-10-07. It adds 5,557 scrub instances and 17,278
approved tussock instances in nine irregular bands. Eighteen terrain-fitted
formations use 58,471 polygon faces, with closed geometry checked before
import. The final shapes use short, tapered wedges and broken clusters.

All 449 sampled basal points are embedded; the maximum measured gap is
-0.119 m and numeric/landscape height disagreement is below 0.001 m. The
nearest outcrop footprint is 23.1 m from a road edge; scrub centres are at
least 10 m clear. All 62 clearance traces across both road routes pass and
all four wheels contact the driving surface in the main review. Existing
terrain heights, grass outputs, road/verge instance counts, shared assets,
lighting and weather settings are preserved.

The main review's play session ended before the third image. The recovered
hillside still is visually inconclusive: its background-throttled capture
has incomplete foreground grass streaming. Do not use that image as a final
coverage comparison. The reliable final comparisons are `High_Overlook.png`
and `Composition_Road.png`. `final-visual-report.json` retains `ok: false` for
the incomplete overall three-view review, alongside the successful primary
checks. `interrupted-review.json` and `hillside-validation.json` preserve the
separate evidence. No performance conclusion is drawn from these captures.
