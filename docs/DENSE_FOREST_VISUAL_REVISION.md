# Dense NZ forest visual revision

## Material detail revision — unchanged geometry

8 November 2026: the owner requested implementation of the no-added-geometry rock research. `Art/tools/bake_rock_surface_detail.py` now authors coherent periodic height, normal, pigment and roughness maps: irregular worn fracture faces, shallow erosion, interrupted mineral seams and restrained inclusions. The source is a procedural height-field bake, not a scan or a high-poly sculpt. The initial trial had overly regular depressions and bright flecks; those were replaced with torn, sloping features, finer relief and quieter pigment.

`Art/Blender/rock_detail_material.py` uses five 1024px texture samples across the existing 2m UV tile. Rock colour, normal and packed data share weathering features. Moss has separate colour and packed coverage/roughness/tuft-height maps. Its texture-scale coverage breaks up the existing basal vertex mask and responds modestly to cavities. A small bump layer adds tuft relief around the structural rock normal. Rock structure is baked into one normal field, avoiding naive averaging of encoded normal maps. A separate moss normal is also baked for later Unreal translation but is not sampled in this Blender material. There is no displacement, tessellation or POM.

`Art/Blender/preview_rock_material_detail.py` updates only the outcrop material in the saved study. It compares every scene mesh's vertex positions, topology, UVs, colour attributes, world transform and triangle count before and after. `material-detail-validation.json` records equality; the six outcrops remain **2,112 triangles**. The camera, lighting, exposure and rendering settings match the prior previews. `before-material-detail-close.png` and `before-material-detail-wide.png` preserve the old renders; `rock-weathering.png` and `forest-bank.png` contain the new close and wide views.

Rebuild this material revision with:

```powershell
python Art/tools/bake_rock_surface_detail.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 4 --python Art/Blender/preview_rock_material_detail.py
```

These are CPU Blender previews. The material has not been installed in Unreal; existing FBX/GLB files remain geometry candidates, not portable versions of this shader. Runtime performance and memory testing remain pending at the owner's request. Five texture lookups replace the prior two-image/procedural graph, so unchanged polygons are not a claim of unchanged GPU cost. The original UV projection still compresses detail on steep side faces and requires review in the final game material. Collision/contact checks from the prior geometry revision also remain pending.

## Current weathered-rock pass

The owner requested less angular, more natural weathered rock, moss around the bases, and normal-map or tessellation detail while retaining separation from the ground.

The six outcrop meshes now use connected, smoothly shaded shoulders with irregular outlines and mild geometric weathering. Their buried feet and exposed upper silhouettes remain distinct. The geometry totals 2,112 triangles, replacing the 330-triangle faceted study below, and shares one rock material. No runtime tessellation has been enabled. Actual runtime cost remains unmeasured.

`Art/tools/bake_rock_weathering.py` generates two deterministic, seamless 1024px data maps over a 2m tile: `Textures/T_RockWeather_Normal.png` and `Textures/T_RockWeather_RAH.png`. Their physical height field contains grain, shallow pits and low-amplitude erosion rather than long drawn cracks. The normal map is tangent-space, non-colour, +Y/OpenGL; Unreal import must account for its green-channel convention. The second map packs roughness, cavity occlusion and normalized height. The current Blender material uses its roughness channel; the other channels are available for later material translation. The bake checks finite, normalized vectors and records height units in `Textures/bake.json`.

The rock material uses the normal map, varied roughness and a vertex mask for irregular basal moss. Moss reduces mineral normal strength and raises roughness locally; upper faces retain their stone colour. The broad grey terrain halo remains suppressed. Geometry-dependent contact and collision checks are still pending before game installation.

The first close review showed cloudy pigment and overly faint fine detail. The latest maps add centimetre-scale shallow erosion alongside the finer grain/pits, with approximately 1.76 cm total source height range across the 2m tile. The pigment range is narrower and finer mineral grain breaks up the colour. `Color.R` on the rock mesh is the moss mask, not red albedo; preserve it during import and wire it into the new material. The close camera targets the left outcrop to avoid tree-trunk occlusion.

`before-rock-weathering.png` preserves the faceted wide preview. `forest-bank.png` and `rock-weathering.png` show the current wide and close views. These remain unedited CPU Blender previews, not game screenshots. `forest-floor.png` is older evidence. To rebuild the weathering maps and review:

```powershell
python Art/tools/bake_rock_weathering.py
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 4 --python Art/Blender/build_forest_floor_revision.py -- --views forest-bank,rock-weathering
```

## Earlier rock-shape correction

The owner repeated that the rocks were too blended into the ground after the material changes. The latest wide preview therefore adds actual outcrop geometry over the three existing exposure regions: six uneven, partly embedded rock masses with bevelled shoulders, faceted upper surfaces and darker side faces. An initial continuous-rim version looked like slabs and was revised. Each lower rim is buried 14 cm into the source support; shoulders stand approximately 3–23 cm above it, with up to 62 cm of added crown height. The six pieces total 330 triangles. They add visible geometry; `unchanged_bank_geometry` in the manifest refers only to the underlying source bank, not to the entire rendered surface.

The broad mineral tint on the underlying terrain is reduced to 12% of its previous mask weight. The separate rock geometry now carries the exposed mineral faces; soil and moss around its foot no longer form a large grey halo that visually merges with the boulder. This replaces the previous material-only approach for the current preview.

`SM_ForestStudy_Outcrops` is a separate candidate export. It has not been installed in Unreal and has no verified game collision. Collision parity and plant/frond contacts must be checked against the raised surfaces before installation. The original terrain and live packages remain untouched.

`before-rock-shape.png` preserves the preceding material-only wide view. `forest-bank.png` is the current geometry revision. The close `forest-floor.png` predates the geometry revision and is not current evidence for the raised outcrops. The latest run uses `-- --views forest-bank` to render the same wide camera and lighting for this comparison; the default command still renders both views.

8 November 2026: the owner endorsed the direction of the more varied ferns and asked for the rest of the dense NZ forest environment to improve too: mud, ground, moss, rocks and the surrounding vegetation. The target is a coherent forest habitat based on the owner's Waimeamea photographs, not a display of separate plant assets.

## Current bounded study

`Art/Blender/build_forest_floor_revision.py` builds a combined study in `Art/Export/LidarStudy/FirstSection/ForestFloorRevision`. It uses the existing RS7 bank mesh, the 152 recorded fern positions, the fitted FernFloor litter/root layer, and the 12 recorded local tree transforms with their source beech meshes. The fern forms come from the new 16-variant library. This is a CPU Blender study; nothing from this pass has replaced live Unreal packages.

The bank's vertex positions remain exactly unchanged in the saved study. A separate copy is used for export so FBX unit conversion cannot round the source positions. Existing terrain collision, mud simulation and driving behaviour remain untouched.

Implemented in the study:

- Damp soil and mud colour/roughness follow bank elevation and small geometric hollows. These are visual moisture masks, not the runtime mud simulation state.
- Moss coverage varies across soil and the existing rock distribution, with its own pigment and fine surface variation. Low moss cushions provide limited close-range silhouette detail.
- Mineral faces are darker and less uniformly pale, with masked fissure shading. The existing physical rock relief remains intact.
- Existing fitted roots, twigs and leaf litter use distinct woody and leaf materials. Nine additional fallen branches and 47 small partly embedded stones provide local detail; 142 small moss cushions are concentrated in the review area rather than spread across the entire map.
- The varied ferns share meshes across 152 instances. Their source X/Y positions, scale and yaw are reused; preview root heights are fitted to the bank. This changes their frond envelopes, so prior game clearance checks do not validate them.
- The recorded local trees provide context. A bark study adds darker bark and irregular lower-trunk moss, using the existing tree geometry and transforms.

The manifest records source hashes, bank geometry hash, instance counts, preview transforms and added triangle counts. `habitat-masks.json` and the saved blend retain the explicit rock/moss/moisture channels. Procedural Blender materials are not portable Unreal shaders: the exported GLB/FBX files are geometry/mask candidates, not finished game materials. Translate or bake the material graphs and verify mask import before installation.

## Visual review

`forest-bank.png` and `forest-floor.png` are unedited CPU renders of the actual bank geometry with the candidate treatment. They use approximate studio lighting, not the game's canopy lighting, exposure or camera capture pipeline. The scene omits the surrounding full forest, river and the original grass layer; it is not a whole-environment acceptance image.

The first preview exposed overly pale rock and weak forest context. The next revision darkens the mineral palette, breaks up moss colour, adds fissure shading and includes the recorded trees. Owner visual acceptance is still pending; improvements must be checked in the complete game scene.

The owner then said the overall direction was better but the rocks blended into the ground too much. The current revision gives exposed rock cooler mineral tones and a slightly different dry roughness, tightens the rock/soil transition, limits broad-face moss coverage and reduces brown wet tint on stone. Moss remains concentrated around margins and hollows. An intermediate cellular crack experiment read like paving and was replaced with the existing authored rock-height texture. The soil study also reuses existing soil colour and relief textures. `before-rock-contrast.png` preserves the earlier wide preview for comparison with the final `forest-bank.png`; camera and lighting are unchanged for that pair.

## Next implementation gates

1. Check ground material and foliage cohesion at walking height in Unreal, with matched exposure. Soil must retain mineral detail; moss must read as vegetation rather than green paint. Mud should be damp in believable hollows, without uniformly glossy terrain.
2. Import candidate assets into a separate bounded review set and verify vertex masks and shader compilation. Recheck roots, frond clearance, small-rock contacts, wind and LOD changes; rebake geometry-dependent contact data. Do not reuse the old fern checks as evidence for new geometry.
3. Review the rest of the dense-forest structure: beech branching and canopy enclosure, pole-tree layers, shrubs and fine grasses, fallen timber, gaps, ground-to-river transitions and bark/moss continuity. Preserve photographed growth forms rather than forcing equal species proportions.
4. Run clean matched runtime comparisons when the shared GPU is available. Measure added material/geometry cost, overdraw, draw calls, memory and temporal stability. Candidate triangle counts are not a measured speed improvement. GPU testing remains pending at the owner's direction.

Rebuild from `C:\GrandTour`:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 4 --python Art/Blender/build_forest_floor_revision.py
```

No rollback is required for the live game: this pass only creates isolated source assets and review evidence. Earlier material changes and fern candidates retain their own records in `RIVERBANK_MATERIAL_POLISH.md` and `FERN_REVISION.md`.
