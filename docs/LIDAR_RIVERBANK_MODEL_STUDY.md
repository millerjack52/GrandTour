# Fitted earth banks on the LiDAR ford

The 220 m study covers stations 3130–3350 m on the saved LiDAR river. The preview adds eroded soil faces with shallow, partly buried cobbles. At the closest driving position the earth lip breaks the plane between two trunks. The pale, smooth-looking cobbles draw too much attention. At 48 m the overall bank still reads as one slope. Keep this as an authoring study. The normal driving map still uses the existing landscape and bank dressing.

The existing fitted bank skin follows one surveyed 22 × 15.6 m patch. The three existing river outcrops provide individual rock shapes. General-purpose modules need a buried toe, tapered ends and an uphill edge that meets the ground throughout each bend. The next art pass should pair a darker, root-bound cut on eroding bends with low gravel shelves on depositing bends. The shape of the landscape at the water’s edge must carry the larger silhouette through the gaps.

## Evidence

- Three geometry iterations used the same river approach. Narrow mossy shapes resembled isolated logs. Wider soil faces read more clearly but had a conspicuously smooth rim. The last pass interrupted that rim and combined deposited stones and exposed earth in each mesh.
- The final bake generated five sections across the 220 m reach. Widths were 5.7–14.8 m, with 6,468 triangles and one shared opaque material across five occupied 32 m tiles. All 86 stones are part of those meshes. Tile count describes submitted scene objects, not measured draw calls.
- The three fixed driving cameras came from a recorded 34.1 m pickup approach. Matched shots used the same vehicle transform, camera, fixed exposure and Fast crown shadows with the models hidden and shown. The play world used the original landscape digest df671e4dafe8cc06d9e08b82258f68f0. The final native images and local timing samples are in Saved/FordGroundReview/BankModelStudy-20261122/LowerBank.
- Vertex, triangle-centre and edge-midpoint probes remained outside wet and protected quads. Every rim vertex of the soil strips finished at least 20 cm below the original surface. Vertical traces hit 105 sampled upper faces in Unreal across all five sections. Driving wheels against the banks, other routes and other maps still need testing.
- The final bake repeated byte-for-byte. Whole-reach placement happens during authoring. Bake the managed reach in one invocation before dividing it into mesh tiles. On a different map, supply its terrain transform, wetted area, road exclusions, river levels and nearby trunk positions. Its grain texture can be supplied to the preview function.

## Frame times

Play in Editor replayed 38 recorded vehicle and camera positions, holding each for seven frames. The test measured elapsed time between editor frame callbacks with screenshots disabled during timing, after one warm-up pass. This measures editor frame pacing with vehicle physics disabled. It does not measure GPU time or a live standalone drive. The window captured 1274 × 682 pixels with the normal LiDAR profile at 75% internal resolution.

| In run order | Median frame, ms | 95th percentile, ms |
| --- | ---: | ---: |
| Existing | 31.40 | 36.18 |
| Models | 32.13 | 37.86 |
| Models | 33.13 | 37.96 |
| Existing | 33.48 | 38.38 |

Pooling the two runs per condition gives 32.49 ms existing and 32.67 ms with models. The 0.18 ms difference is smaller than the 2.08 ms drift between existing-only medians. A standalone drive at the target resolution is necessary to establish cost against the 16.67 ms frame budget.

## Reproduce the geometry

Use the inputs from the LiDAR riverbank relief survey documented in LIDAR_RIVERBANK_PHYSICAL_RELIEF.md. The trunk file contains XY pairs in world metres. A bare terrain can omit it. The terrain Python environment includes NumPy, SciPy and Pillow.

```powershell
$f = 'Saved/FordGroundReview/physical'
$p = 'Saved/FordGroundReview/BankModelStudy-20261122'
& Saved/Tools/TerrainPython/Scripts/python.exe Art/tools/bake_erosion_bank_meshes.py "$f/live.r16" "$f/live-hash.json" "$f/river-wet.png" "$f/protected.png" "$f/course.json" "$p/LowerBank/sections.json" --trunks "$p/trunks.json" --reach 3130 3350
```

With the surveyed level open and a Play in Editor session running, execute the following in the Unreal Python console. The function returns the preview actors for visibility and collision comparisons. End Play to remove them. The mesh and material packages are temporary and should be discarded on editor exit.

```python
from pathlib import Path
import sys, unreal
root = Path(unreal.Paths.project_dir()).resolve()
sys.path.insert(0, str(root / "Art/Unreal"))
from preview_erosion_bank_meshes import preview
banks = preview(root / "Saved/FordGroundReview/BankModelStudy-20261122/LowerBank/sections.json")
```
