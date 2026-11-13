# Benmore: Gaea 2 handoff

Prepared 8 October 2026 and built with the installed Gaea **2.3.0.1**.

The technical setup is ready. Your part is to judge and adjust the landform in Gaea, then build it. Keep the first pass focused on the northern gully. We will bring the result into a separate Unreal review level and update the assets around the new channel.

## Start here

1. In Gaea, choose **File → Open** and open:

   `C:\GrandTour\Art\Export\BenmoreGaea\Benmore_01_RiverStudy.terrain`

2. Save a working copy alongside it as `Benmore_02_MyRiver.terrain`.
3. Select **06_ProtectedTerrain** to see the final terrain. Compare it with **01_CurrentTerrain**. The final node is deliberately blended at **0.5** to keep the first pass restrained.
4. Select **02_GentleErosion** to adjust erosion, or **04_ChannelStudy** to adjust the river. Change one control at a time. Return to **06_ProtectedTerrain** to judge the result that will actually come back.
5. When the shape is worth testing in Unreal, use Gaea's **Build** command at **2048** resolution. The export nodes already have their paths configured. Save your `.terrain` file too.
6. Tell me the build is ready. The files should be in:

   `C:\GrandTour\Art\Export\BenmoreGaea\return`

You do not need to export meshes, move the existing Unreal assets, or import the heightmap yourself.

## What to aim for

Use the actual Otago/Mackenzie references for the landform. Look for a shallow, irregular channel sitting naturally in a wider valley, occasional exposed gravel bars, and banks that blend into the surrounding ground. Keep the distant ridge silhouettes recognisable.

- **Erosion:** add smaller gullies and slope breakup without turning the whole catchment into sharp badlands. Start with the supplied low settings. Increase Duration modestly if the terrain still feels too smooth.
- **Rivers / Width:** adjust the channel's lateral footprint. Look for changes in width along its route, rather than one broad trench.
- **Rivers / Depth:** increase gradually if the bed is too shallow. Judge the bank profile from a low view as well as from above.
- **Rivers / Downcutting:** starts at zero. Leave it low for this first pass; a large value can over-carve an existing DEM.
- **Rivers / Water:** affects river generation, not the final Unreal water material.
- **Final Combine / Ratio:** starts at 0.5. Raising it allows more of the processed terrain through; lowering it brings the terrain closer to the original.

These are a starting study, not a finished river design. Gaea's river controls are relative values, not direct metre measurements. [Gaea Rivers reference](https://docs.gaea.app/reference/nodes/simulate/rivers.html).

The supplied headwater mask allows starts in an area uphill of the northern gully. It is connected to the **Headwaters** input. The Headwaters count is high because generation is confined to that small area; it does not produce 1,000 visible rivers. If the route needs to move, send the saved graph and a description of the desired start/end points; we can revise this mask. Changing the Seed also changes the generated route.

## Settings to retain

| Setting | Value |
|---|---|
| Terrain width | **2500 m** |
| Terrain height range | **512 m** |
| Preview resolution | **1024** is fine |
| Build resolution | **2048 × 2048** |
| File nodes: Enforce Linear Gamma | **Off** — verified on this Gaea installation |
| Build: Flip Y | **Off** |
| Export format | **TIFF32**, already configured |
| Final Combine | **Blend**, original in Input 1, processed terrain in Input 2 |
| Final Combine mask | **05_FirstCatchmentMask** |
| Rivers: Render Surface | **Off** in this terrain study |

Keep the original input, its export, and the mask connections intact. Avoid AutoLevel, automatic normalization, changing the terrain extent, or rotating/cropping the heightmap. We need the heights to stay in the same coordinate system as the roads and placed assets.

Use the supplied generic **Export** nodes. Gaea's **Unreal** export node automatically stretches the height range, so it is unsuitable for this particular fixed-datum round trip. [Gaea Unreal node reference](https://docs.gaea.app/reference/nodes/output/unreal), [Export reference](https://docs.gaea.app/reference/nodes/output/export.html).

The **512 m range is an encoding range**, not the terrain's highest point. The original datum is already accounted for in the input and return converter. Do not move the terrain up or down to make its lowest point zero.

## What the masks protect

See `C:\GrandTour\Art\Export\BenmoreGaea\review\FirstPass_Map.png`.

The cyan outline marks a broad first-study area. It is an art boundary, not a calculated watershed. The orange lines are the road routes.

- The full road cut/fill shoulders are preserved, with a feather outside them.
- The low lake margin stays at its original elevation.
- The outside edge of the 2.5 km tile stays fixed so it can continue matching the surroundings.
- Everything outside the first-study area remains original in the starter graph.

For `M_Protect…` files, **white means preserve**. For `M_FirstPass_Edit…` and the final Combine mask, **white means allow edits**. Do not swap those two kinds of masks.

Protecting roads can interrupt a generated channel where it reaches a road. That is intentional for this first pass: a culvert, bridge or ford needs a deliberate decision. Likewise, the protected lake margin still needs a designed river mouth. A visually pleasing Gaea route is not yet proof of an uninterrupted final watercourse.

## Files to return

Build the whole graph, so these files all come from the same version:

| File | Purpose |
|---|---|
| `H_Eroded.tif` | Final protected terrain |
| `H_InputCheck.tif` | Untouched original, used to verify scale, orientation and encoding |
| `M_Rivers.tif` | Channel footprint for rebuilding water and dressing |
| `M_Depth.tif` | Gaea depth data for interpretation during integration |
| `H_WaterSurface.tif` | Unblended river-node surface reference; **not the ground heightmap** |
| `M_Wear.tif`, `M_Deposits.tif` | Erosion masks for surface/material work |
| Your saved `.terrain` | Editable source of the result |

The river, surface and erosion masks are from the processing nodes before the final protective blend. They are guides: we must clip them to the edited area and reconcile the water elevation against the final terrain. Do not use the surface export as a direct landscape replacement or assume the depth map is a world-space water simulation.

If the Gaea preview looks different from the full build, judge the **2048 build**. Avoid resizing exports in an image editor.

## What happens back in Unreal

1. Validate the unchanged input export. The converter rejects flipped, gamma-shifted, normalized, 8-bit or incorrectly sized data.
2. Apply the Gaea **height difference** to the exact original 2017 × 2017 Unreal grid. This avoids resampling the original terrain twice. Reapply protection on the return path and check all protected samples are unchanged.
3. Import into a **copy** of `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive`, keeping the existing Landscape, transform and material setup.
4. Rebuild the river water surface and remove or rebuild the old raised bank meshes in the changed area. Those meshes were not included in the height export.
5. Re-seat affected rocks, shrubs and placed instances against the revised terrain, keeping their horizontal positions where sensible. Rebuild terrain-driven grass and update exclusions along the new watercourse. Review hero rocks, trees and crossings individually.
6. Check collision, grounding, water continuity, material transitions and long vistas before replacing the working level.

The placement snapshot contains **306 actors and 90,418 mesh instances**. It records labels, meshes, materials and transforms; it is an inventory and recovery reference, not a complete Unreal level backup. Most assets remain reusable. Dense generated dressing can be updated in batches; some deliberate compositions will need attention.

Gaea edits the base terrain. Runtime deformable gravel remains a separate system layered onto that base, with its existing wheel/physics field. New riverbeds do not require replacing that system.

## What has been verified

- Read the **saved current Unreal Landscape**, including its graded roads.
- Verified it matches the canonical road height data exactly and that exporting did not change the source map.
- Built both supplied `.terrain` files in Gaea 2.3.0.1.
- The unchanged import/export returns a **byte-identical Unreal R16 heightmap** after conversion.
- Verified the river study exports a nonempty river/depth mask in the editable area and preserves terrain outside the mask.
- Passed ten CPU data checks, including road/shore/edge protection and rejection of bad return formats.

The Gaea study has now been approved for integration and imported into the separate Unreal map **L_Benmore_GaeaReview**. See [the integration notes](C:/GrandTour/docs/BENMORE_GAEA_INTEGRATION.md) for placement changes, validation and the current water-preview scope. The original driving level is unchanged.

## Technical commands for the return step

These are for the integration work; you can simply tell me the Gaea build is ready.

```powershell
Set-Location C:\GrandTour
& .\Saved\Tools\TerrainPython\Scripts\python.exe .\Art\tools\convert_benmore_gaea.py
```

The converter writes only to `Art\Export\BenmoreGaea\candidate`. It never edits a map. It stops for terrain changes beyond a 12 m first-pass review limit; review the shape before deliberately raising that limit.

The untouched pipeline proof is `Benmore_00_RoundTrip.terrain`; its exports go to `roundtrip`, separate from your study. The detailed check report is `review\validation-report.json`.

Do not rerun the older `prepare_benmore_roads.py` or `setup_benmore_roads.py` as the import step: those rebuild from the earlier road workflow and are not the Gaea return procedure. Also avoid rerunning `prepare_benmore_gaea.py` over your edited starter; it regenerates the supplied graphs.
