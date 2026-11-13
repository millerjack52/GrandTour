# Benmore first driving routes

**Current road surface:** [BENMORE_REFERENCE_ROADS.md](BENMORE_REFERENCE_ROADS.md) applies the user�s actual-area photo references to gravel, wheel paths and hill colours.

**Current scenery pass:** [BENMORE_SCENERY.md](BENMORE_SCENERY.md) adds the approved willow family and clustered rocks to the same driving map.

**Current vegetation pass:** [BENMORE_VEGETATION.md](BENMORE_VEGETATION.md) extends streamed tussock and low grass across the whole terrain. Its unified cover replaces the roadside-only grass described in the original road pass below. The map and launcher are unchanged.

Map: `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive`.
Launch: `Art/play_benmore_roads.ps1`.

Controls: WASD/arrows to drive, Space handbrake, C camera, **V low range**, **X differential lock**. Use low range and the differential lock for the hillside branch. The steep climb is intended as a crawl; the first test stalled in high range, then completed with these existing drivetrain controls enabled. No vehicle power/grip tuning was changed to make the test pass.

This is the first road and dressing blockout on the user's full selected Benmore site. The original terrain review map and LINZ exports remain the reference. Roads are fictional and have not been matched to surveyed or legal road alignments.

## Layout

- Terrace loop: 2517 m long, 6.4 m road width; sampled peak centreline grade 14.1%, 95th percentile 9.1%.
- Hillside branch: 1189 m long, 4.4 m road width; sampled peak grade 22.9%. This is the more demanding optional route.
- The full 2240 x 2404 m selection remains within the 2500 m terrain square. The initial routes occupy the open terrace and lower hills; the northern ridge and southern hills remain available for expansion.
- Cuts/fills blend into the DEM over 8–10 m shoulders. Maximum grid cut is 3.36 m and fill is 2.24 m. About 36,258 square metres change by more than 10 cm. Terrain outside the corridors is unchanged from the encoded source.

The first 220 m has the densest roadside art sample. Existing dense tussock LOD meshes and approved gravel textures/stones are reused by reference. Shared meshes and materials are not edited. There are 3584 tussock instances, 539 small stones, and 55 guide posts. Tussock fades by 220 m; small stones by 100 m. These are an initial scale/composition sample, not a fully dressed landscape.

## Technical scope

Driving uses the existing GT car and the imported Landscape's physical collision. There is deliberately no procedural `GTTerrainBuilder` spec actor in this map: the old analytic height generator does not describe this DEM. This avoids building mud, snow or route actors at incorrect procedural heights. Procedural route stations, route-dependent gameplay, deformable mud, water and the willow library are not integrated in this road pass.

The map has a firm-ground physical-material fallback. Separate road/off-road surface tuning and deformation remain later integration work. The blue lake-height cue is still terrain shading, not game-ready water.

Source coordinate convention: Unreal X east, Y north; local Z is elevation minus 360.531005859375 m NZVD2016. Landscape scale/extent matches the terrain review. Road images have southern edge at row zero. Height encoding is `(value - 32768) / 64` local metres.

## Rebuild and verification

1. Run `Art/tools/prepare_benmore_roads.py` with `Saved/Tools/TerrainPython/Scripts/python.exe`. Outputs go to `Art/Export/BenmoreRoads`.
2. Run `Art/Unreal/setup_benmore_roads.py` in a rendered Unreal editor. On first creation it copies the reference map, then explicitly loads the separate driving map before edits. It imports the road heightfield, adds materials/dressing and verifies imported heights. Running it again replaces this blockout's terrain, materials and generated roadside group; hand edits to those are not preserved.
3. Run `Art/Unreal/check_benmore_roads.py` in a rendered editor. It reloads the saved map, surveys road collision at centre and wheel offsets, captures views, and drives representative sections. `setup-report.json` and `drive-report.json` each require `ok: true` for a successful run. Grade estimates alone do not establish driveability.

The JSON route points and height grid are authoritative for this blockout's offline placement and validation. No shared C++ code was changed or rebuilt for this pass.

The visual-only update (`GT_BENMORE_ART_ONLY=1` when running setup) leaves the imported heightfield unchanged and writes `art-report.json`. `capture_benmore_roads.py` reloads that saved update and captures the overview, driver and roadside views without saving changes. Terrain reference recovery is independently checked at 155 points inside the authored road corridors against the original R16, with zero difference. The saved driving terrain passed 1116 collision probes, no misses, maximum difference 1.11 cm against the encoded heightfield.

All six representative driving cases passed: start, main climb, branch entry, hill climb, hill descent and branch rejoin. The first three passes were retained across the visual-only update; the remaining three were validated on the final saved map with low range and differential lock. The high-range hill failure is retained separately in `drive-report-high-range.json`. These are representative-section tests, not a complete lap or a performance certification.

Source: LINZ Data Service, Toitū Te Whenua Land Information New Zealand, CC BY 4.0. See `Art/Export/MackenzieRealTerrain/BenmoreFullSite/LINZ_source_and_license.txt`.
