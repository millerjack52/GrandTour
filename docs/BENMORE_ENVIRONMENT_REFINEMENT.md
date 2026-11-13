# Benmore environment refinement

Implemented in `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive`. The pre-pass map is `L_Benmore_BeforeEnvironment`; its landscape material is also copied to `ReferenceSurface/M_Benmore_BeforeEnvironment`. The terrain-only survey map is untouched.

## Ground and hills

`benmore_bank_surface.py` adds slope-driven dry taupe soil and layered grey rock over the existing ground. Three-axis texture projection prevents the rock detail stretching vertically on steep faces. Broken world-space masks interrupt the soil/rock transition. This is an art-directed schist-like treatment using existing licensed Meadow textures, not a scan of local schist.

Broad 57–190 m variation supplies colour structure across distant landforms. A numeric DEM mask adds 40 m and 140 m concavity measurements: gullies receive darker muted olive/brown vegetation, while exposed ridges become lighter and stonier. Small detail fades over 80–350 m; the grass macro colour takes over gradually from 120–600 m. Road masks preserve the road treatment. The backdrop uses the same landform mask and bank/hill palette.

The map now contains a height-fog actor with a 280 m start distance and restrained blue-grey colour. Runtime density remains controlled by the existing weather system (Clear's default is 0.010); the editor value is 0.007. Skylight intensity is 0.9. Shared weather and sky assets are unchanged.

## Supported rocks

Large rocks retain their authored XY locations and variation. A local terrain plane supplies their tilt while preserving their original heading. Vertical terrain traces under each mesh's lower 32% establish its supporting footprint; the most restrictive contact embeds that base by 6.5 cm. Higher natural overhangs are excluded from base contacts. This avoids burying the whole cluster merely because its upper silhouette overhangs the base.

Small aggregate uses the same triangle split as landscape collision, confirmed by terrain traces. Five footprint samples support each stone, with 1.2 cm embedding. Stone width increases 35%; height increases 45%. Roadside stone groups cast shadows, retaining their existing short culling distances. The tiny road aggregate remains without shadows. A component tag prevents repeated enlargement when re-running setup. Grass is re-seated separately and keeps its approved TussockStyle meshes.

## Real surrounding terrain

Four Nanite scenery patches extend to the downloaded LINZ region: 1371837–1385525 E, 5072648–5085427 N (NZTM), with a 20 m outer inset. Relative to the level centre, coverage reaches about 11.44 km west, 8.48 km south, 4.26 km north and 2.21 km east. Coverage is asymmetric because it follows the user's download.

Source elevations are averaged onto a 10 m sampling grid, then sampled onto progressively spaced mesh rings. An overlapping inner strip blends into the playable landscape boundary; no fictional mountain ring or vertical exaggeration is added. The four patches contain 403,200 source triangles combined and have no gameplay collision. The playable footprint is unchanged. Lake colour remains a visual elevation cue, not a water simulation.

Source attribution: LINZ Data Service; licensed by Toitu Te Whenua Land Information New Zealand for reuse under CC BY 4.0. The original downloaded data and attribution remain in the existing terrain package.

## Road detail

Loose gravel repeats every 12.5 m instead of 8 m, enlarging it 1.5625 times. Packed fine gravel retains its 4 m repeat. Colour, normals, explicit mip derivatives and POM height all use the matching scale. Close-range loose POM depth is 5.5 cm, fading over 15–30 m; no pixel-depth offset is introduced.

Physical road undulations use 8.5 m and 15.7 m wavelengths with irregular amplitude, shallow wheel depressions, and faded junction/end transitions. These scales are resolvable by the 1.24 m landscape grid. Maximum quantized height change is +6.25 / -7.8125 cm. Existing verge banks and drainage hollows remain. New heights are committed to the canonical float grid only after the map saves and exported height samples match.

## Rebuild and validation

1. `Art/tools/prepare_benmore_environment.py`: numeric height data, supporting footprint samples, backdrop vertex data.
   Run `Art/tools/prepare_benmore_landform.py` for the numeric hill-shading mask.
2. Blender: `Art/Blender/export_benmore_backdrop.py`.
3. Unreal: `Art/Unreal/setup_benmore_environment.py`.
4. `Art/Unreal/check_benmore_environment.py`: saved geometry, support, collision, grass and images.
5. `Art/Unreal/check_benmore_environment_drive.py`: six representative vehicle cases.

Reports and captures are under `Art/Export/BenmoreEnvironment`. The support refinement report supersedes the initial setup report's earlier all-underside seating result. The saved-map validation report checks the final basal-footprint placements. The editor's background frame timing is not a performance benchmark.

Validated 2026-10-07:

- All 201 large rock clusters retained. All 13,342 sampled base contacts lie at or below terrain; the highest is embedded 6.5 cm.
- All 57,808 ordinary verge/road instances retained and re-seated, including 41,115 stones. The four TussockStyle grass variants streamed around the review cameras.
- Height import/export anchors match exactly. 1,085 road/verge collision probes hit; maximum wheel-path difference from the authoring grid is 2.23 cm. A separate driving check used 1,116 probes, with zero misses and maximum difference 1.42 cm.
- All four backdrop source meshes match their numeric geographic coordinates; 824 checked vertices had maximum Z error below 0.004 cm. Actors retain identity world transforms.
- All six driving cases completed: start, main climb, branch entry, hill climb, hill descent, branch rejoin. Tested peak speeds were approximately 18–26.5 km/h. Each case started with four wheel contacts; no tested run left its road or rolled. This is a representative drivability check, not a high-speed handling benchmark.
- Final close-bank review caught and removed overly regular bedding stripes. Irregular layered colour and weaker normal detail are saved in the final shader. `bank-final-report.json` and the updated `Steep_Bank.png` / `Distant_Landscape.png` supersede those two captures from the preceding visual pass.
