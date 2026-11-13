# Benmore full site

The first separate road/driving pass is documented in [BENMORE_ROADS.md](BENMORE_ROADS.md), map `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive`. This document describes the terrain-only reference and source package.

The user's selected level footprint is the **whole area below candidate C**, including the northern ridge, central terrace and southern hills beside the lake. It supersedes the earlier 1 km candidate D proposal.

## Extent and source data

- Selected footprint: **2240 x 2404 m**, approximately **5.385 km²**. Bounds were matched to the user's overview screenshot and rounded outward to metres.
- NZTM bounds: 1382180–1384420 E, 5079947–5082351 N.
- Gaea/Unreal terrain tile: **2500 x 2500 m**, centred at 1383300 E, 5081149 N. The small extra border accommodates a square heightmap without stretching the selection.
- Selected terrain elevations: approximately **360.5–642.1 m NZVD2016**. The square's border reaches approximately 679.2 m.
- Source: LINZ one-metre DEM. No erosion, vertical exaggeration or road grading has been applied.

Files are in `Art/Export/MackenzieRealTerrain/BenmoreFullSite`.

`Selected_Area_1m_NZTM.tif` is the native-resolution rectangular selection. `Gaea_Border_1m_NZTM.tif` includes the square border. `Surroundings_4km_1m_NZTM.tif` provides nearby context for later scenery; it is not a change to the selected playable footprint.

## Gaea

Load **H_Benmore_FullSite_2048.png** through a File node, using **Raw** scale. Set Terrain Definition to **Width 2500 m**, **Height 512 m**, and start at **2048** resolution. Keep the transform and value range unchanged; do not apply Autolevel to this input.

Height encoding: `NZVD2016 metres = PNG / 65535 * 512 + 256`. North is at the top of the image. First and last sample centres span exactly 2500 m. The float GeoTIFF `Gaea_Grid_2048_NZTM.tif` preserves the same samples in metre elevations, with their geographic transform.

`M_Selected_Footprint_2048.png` marks the user's selected rectangle inside the square border. The lake/land masks are approximate elevation-threshold guides, not surveyed shorelines. `M_Slope_0to45deg_2048.png` maps 0–45 degrees to black–white. These are data maps, not painted ground materials.

Keep an untouched source branch when developing the terrain. Begin by inspecting the real landforms; additional erosion may not be necessary. Save the `.terrain` graph under `Art/Gaea` and retain export metadata, especially if an output node changes height normalization.

## Unreal terrain review

Target map: `/Game/GrandTour/Demo/BenmoreFullSite/L_Benmore_TerrainReview`.

Open it in Unreal using `Art/open_benmore_terrain.ps1`, or select the map in the Content Browser. The editor viewport is positioned for a full-site overview. Play uses a free-flying default pawn for terrain inspection, not the driving prototype.

`Art/Unreal/setup_benmore_full_site.py` creates a separate terrain review map. It imports the real heightfield into a 2017 x 2017 Landscape using the existing grid builder and Unreal's render-target height import. It removes the temporary procedural builder afterwards. It does not modify shared C++ terrain/vehicle code or other environment assets.

The Unreal heightmap is **H_Benmore_UE_2017.png** (also `.r16`). It has a different encoding and row direction from the Gaea input: `local metres = (pixel - 32768) / 64`. Lake-level elevation 360.531005859375 m is local Z=0. Landscape XY scale is 124.0079365 cm; Z scale 200; location (−125000, −125000, 0) cm. UE X points east and Y north. The Unreal image is flipped vertically so row zero is the southern edge.

`T_Benmore_HeightRG_2017.png` is an internal lossless RG-channel transfer image, not a conventional grayscale heightmap. The import script disables its colour-space conversion, compression and mipmaps before transfer, and checks transfer values against known samples.

This map is for terrain review. It has no authored driving route or game-ready water. The lake-coloured ground is a visual elevation cue. The source DEM does not establish underwater bathymetry. Deterministic gameplay height queries must be integrated with the imported terrain before using the Grand Tour driving systems here.

The script writes `unreal-review-report.json`; only `ok: true` confirms successful import and checks. It compares 49 asymmetric height samples, including corners, with the supplied grid and checks interior collision samples. `Unreal_Terrain_Review.png` is the captured engine overview after successful validation.

Validated import: all 49 height samples matched the encoded input exactly; all 25 interior collision probes hit, with a maximum height difference of about 1.1 mm. `Art/Unreal/capture_benmore_review.py` separately reloads the saved map, checks height persistence and captures the complete site. See the report's `saved_map_verified` field for that result. Encoding and resampling precede these checks; they do not establish original survey accuracy or route driveability.

## Next design pass

Use the central terrace to establish the main route, then follow contours into selected hillside sections. Keep steep faces as scenery or deliberate optional challenges. Inspect gullies before assigning crossings; the DEM alone does not identify dependable water flow or safe fords. Adapt the earlier blockout's route rhythm to the geography rather than transferring its road masks directly.

Source attribution: Sourced from the LINZ Data Service and licensed by Toitū Te Whenua Land Information New Zealand for re-use under CC BY 4.0. The original source/license text accompanies the terrain files.
