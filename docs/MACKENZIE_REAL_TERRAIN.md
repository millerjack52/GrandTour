# Real terrain: Lake Benmore region

**Current selection:** the user chose the whole shoreline/terrace/hill area below C, not one of the 1 km squares. See [Benmore full site](BENMORE_FULL_SITE.md). The candidate studies below remain as exploration history.

Prepared from the supplied LINZ download. This is a separate source-data and site-selection package; the accepted Unreal blockout and other environment asset work are untouched.

## Download inspection

- Four 1 m GeoTIFF tiles, NZTM2000 / EPSG:2193; metre elevations in NZVD2016.
- Combined footprint: 13.688 x 12.779 km; 174,918,952 valid source pixels, no missing cells.
- Elevation range: 360.488–1571.505 m. The large central flat area is Lake Benmore; it must not be treated as driveable ground or surveyed lake-bed bathymetry.
- `Region_DEM_1m_NZTM.tif` joins the tiles without resampling. Complete missing-value scan passed; 36 checks at tile corners, centres and edges matched source elevations exactly.
- `Region_Overview_5m_NZTM.tif` is for browsing. Use the full-resolution mosaic for production crops.
- `LINZ_source_and_license.txt` preserves the supplied attribution and metadata.

## Candidate sites

See `Region_With_Candidates.png` for positions and `Candidate_Comparison.png` for equally scaled close-ups. A is the suggested starting point: gentle western foothill terrain with sufficient elevation change for a route. B is a northern alternative. C has more local undulation. Ranking uses slope and relief, excluding lake-level areas; it is a design suggestion, not proof of driveability. Roads, land cover and possible stream crossings still need review. The blue lake preview mask is inferred from elevations below 361 m, not an authoritative shoreline dataset.

Each candidate spans exactly 1000 x 1000 m between the outer pixel centres, with a 1024 x 1024 16-bit PNG for Gaea and a matching float GeoTIFF for geographic reference. Native one-metre elevations were sampled bilinearly. The GeoTIFF footprint extends half a sample beyond the study bounds because GIS pixels have area; its first/last pixel centres coincide with the study edges.

## Open a candidate in Gaea

Create a new graph, add a File node, choose that candidate's `H_Candidate_*_1024.png`, and use Raw scale with no Autolevel. Set Width 1000 m and Height from this table. Start at 1024 resolution.

| Candidate | Terrain Height | Add to Gaea elevation to recover NZVD2016 | Observed elevations |
| --- | --- | --- | --- |
| A | 128 m | 352 m | 374.62–460.77 m |
| B | 128 m | 352 m | 376.53–461.51 m |
| C | 256 m | 368 m | 384.72–495.60 m |

These files are north-up; row zero is the northern edge. The earlier synthetic blockout package used a different row orientation and encoding. Use each candidate's `heightmap.json`, not the earlier blockout settings, for integration. No height exaggeration or erosion has been applied.

Choose a site before adapting the route. The synthetic road-protection masks do not align to these geographic locations. Keep the accepted road rhythm as a design reference, then fit roads to the selected landforms. An Unreal import must also reconcile deterministic gameplay height queries and recheck collision and driving.

Rebuild tools: `Art/tools/inspect_linz_terrain.py` and `Art/tools/package_linz_candidates.py`. Python runtime: `Saved/Tools/TerrainPython/Scripts/python.exe` (rasterio, pyproj, numpy, Pillow). The `--preview-only` inspector option reuses the native mosaic and verifies it before rebuilding previews.

Attribution: Sourced from the LINZ Data Service and licensed by Toitū Te Whenua Land Information New Zealand for re-use under CC BY 4.0. Source: https://data.linz.govt.nz/layer/121859-new-zealand-lidar-1m-dem/
