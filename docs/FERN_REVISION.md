# Fern form and shading revision

The owner subsequently endorsed the variation direction and requested a broader dense-NZ-forest pass. The combined ground, moss, rock, roots and tree-context study is documented in [Dense forest visual revision](DENSE_FOREST_VISUAL_REVISION.md). This endorsement does not mark the candidate meshes as installed or their in-game checks as passed.

## Latest variation pass

The owner requested substantial variation and continued visual improvement. `Art/Blender/build_fern_variation.py` now builds **16 candidates across four growth forms**, each with three LODs, into `Art/Export/LidarStudy/FirstSection/FernRevision/Variation`. This extends the three-Cascade study below and preserves those earlier files.

The four forms are outward-hanging Cascade sprays, Fine fronds with actual secondary divisions, compact Crevice plants, and upright Crown plants. Within each form, crown size, frond count, length, elevation, droop, twist, attachment, maturity and small gaps differ deterministically. Young and mature pigments remain restrained; selected old fronds have muted brown areas. One shared preview foliage graph varies roughness with the authored pigment from 0.65 to 0.84. Root wind weights retain the existing convention.

The library has 16 distinct frond-skeleton hashes, with unchanged skeletons across each asset's LODs. There are zero dropped degenerate faces, decreasing triangle counts by LOD, and each candidate's LOD0 is below its original growth form's LOD0 count. Cascade ranges from 3,725 to 4,303 triangles; Fine from 10,188 to 12,662; Crevice from 2,395 to 3,077; Crown from 3,445 to 4,584. Fine foliage still needs careful screen-coverage and temporal review despite being lighter than the original Fine meshes. Sixteen meshes also have memory and batching costs; lower per-mesh triangle counts alone do not establish a performance improvement.

`variation-library.png` is a labelled CPU render of all 16 candidates at a common scale. `variation-patch.png` groups 11 of them on a constructed sloping surface, with uneven colonies, overlapping growth forms and exposed ground. The supporting surface is for preview only, not surveyed terrain or proof of in-game root/frond clearance. The patch proportions are an example, not a mandated equal-species planting recipe. Its transforms are saved in `patch-layout.json`.

The `.blend` library and patch, 48 FBX files, 48 GLB files and manifest are saved beside the renders. Rebuild with Blender using `--background --factory-startup --threads 4 --python Art/Blender/build_fern_variation.py`. These remain isolated candidates: no live map, plant package or current material was replaced. Unreal installation, material translation, contact-bake refresh, actual placement/wind/LOD checks and GPU timings remain outstanding. Visual review of the preview is not acceptance of a game build.

## Earlier three-Cascade study

8 November 2026: the owner rejected the fern appearance in the riverbank captures and confirmed that both shape and shading need correction. The existing fern treatment is not visually accepted. The earlier material-only pass did not resolve the angular, repetitive silhouettes.

The first replacement study is isolated in `Art/Export/LidarStudy/FirstSection/FernRevision`, with source `Art/Blender/build_fern_revision.py`. It uses the owner's Waimeamea photographs 04 and 08 as growth-form references. It does not replace live meshes, material packages, planting or the shared generator.

## Candidate

- Three deterministic Cascade fern variants, each with three detail levels.
- Curved, tapered, cupped leaflets with smooth normals, offset attachment and modest differences in length and twist.
- Uneven outward sprays and raised younger fronds, preserving the bank-facing orientation and root origin convention.
- Cooler mature greens, restrained younger greens, variation along blades and a softer ridge. The Blender preview uses modest thin-leaf transmission and roughness 0.7; this shader has not yet been translated to Unreal.
- Opaque mesh silhouettes without new opacity cards. Each highest-detail candidate has 4,801 triangles compared with 5,199 in its original Cascade counterpart. This is a geometry count, not evidence of faster rendering.

The first preview was too sparse; the second retained overlapping fronds but exposed overly broad tip leaflets. The current candidate caps leaflet width relative to length to maintain the narrow taper. It still needs review as a fern in the actual bank, including its outline at gameplay distances.

## Evidence and checks

`before.png` and `candidate.png` are CPU Cycles asset previews with the same camera, lighting, exposure and background. They are not game screenshots. The before preview reconstructs the original Cascade_0 mesh and its generic Blender material, not the latest Unreal material polish.

`manifest.json` records the three variants, triangle counts, identical frond-skeleton hashes across their LODs and zero dropped degenerate faces. The saved `.blend`, GLB and FBX files are available for further iteration. Every LOD retains all fronds; reduced levels thin leaflet detail. Their visual transitions remain untested.

Rebuild from the project root:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --threads 4 --python Art/Blender/build_fern_revision.py
```

## Remaining work

Review the candidate's shape and pigment direction, then integrate into a protected bounded Unreal trial with an appropriate foliage shader. Changed frond envelopes require fresh supporting-surface and uphill-clearance checks; the previous placement checks cannot certify the replacement. Recheck wind, LOD transitions and apparent density in matched game views. FernFloor contact depends on geometry and will need rebaking if replacement meshes are installed. Fine, Crevice and Crown forms have not been revised by this Cascade study.

Performance testing remains pending at the owner's direction while Skate shares the GPU. Owner acceptance and in-game visual validation remain pending for this new candidate. Existing game assets remain installed solely as the current state, not an accepted result.
