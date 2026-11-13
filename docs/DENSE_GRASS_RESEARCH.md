# Dense tussock and grass: research recommendation

Research performed by a delegated GPT-6 Luna agent, then checked against the installed engine, project scripts and Epic documentation. Research only: no game assets, materials or levels changed.

## What is causing the gap

The supplied photo has overlapping rounded tussock crowns, fine grass and low woody scrub. The current meshes emphasize thin pointed blades, exposing a bright ground surface between them. Increasing blade count alone does not supply that plant volume.

The project's coverage importer explicitly disables Nanite for GrassCarpet meshes and fades them from 25 m to a complete cutoff at 42 m. No cheaper replacement grass layer takes over. This helps explain the broad bare hills in the screenshot. The grass shader sinks vertices with -125 * authored height * (1 - fade); this is a height-dependent displacement, not a fixed 125 cm movement.

Confirmed locally:
- Engine 5.8.0, changelist 55116800.
- Config/DefaultEngine.ini enables r.Nanite.AllowVoxels=1.
- EngineTypes.h exposes ShapePreservation None, PreserveArea and Voxelize.
- setup_road_ford_style.py disables Nanite on coverage meshes.
- GTVegetationSubsystem::AddTaggedInstances creates ordinary ISM components, not HISM.
- Current vegetation: 15,181 coverage patches; 1,404,188 unculled grass triangles; approximately 73% of patches are the low Mat or Swept forms.

## Recommended rendering approach

Build fuller, rounded, arching tussock crowns and a fine underlayer first. Use overlapping clusters with different crown widths and heights, plus some low woody scrub. Retain dry straw colours; any greener growth belongs locally around moist stream margins, not across all tussocks.

Compare three rendering paths using the SAME authored vegetation and visible coverage:

| Path | Purpose |
| --- | --- |
| Conventional instanced meshes with authored LODs | Predictable control over nearby detail, cheaper middle-distance clumps and distant coverage. |
| Nanite with Preserve Area | Control experiment for retaining thin/disconnected foliage during simplification. |
| Nanite with Voxelize | Candidate for preserving dense tussock volume as it recedes into the distance. |

Epic describes voxel foliage as an Experimental feature which converts suitable distant aggregate geometry to a voxel representation. It is promising here, but the project's global switch does not activate it on our non-Nanite grass. A prototype is required before choosing it for the laptop. [Nanite Foliage](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage)

**Material compatibility:** Epic documents that voxel normal-distribution data currently overwrites vertex-colour alpha. Our grass stores blade height there. Start the Nanite experiment with a separate static material and no sinking/WPO logic; relocate that mask before reusing it for animation. [Nanite Foliage](https://dev.epicgames.com/documentation/unreal-engine/nanite-foliage)

Opaque clump geometry remains the preferred first candidate. Epic warns that foliage's disconnected geometry and many holes can defeat ordinary Nanite simplification/occlusion, and that masked pixels/overdraw are costly. Cards are a comparison candidate, not an automatic optimization. Preserve Area preserves area during simplification; it does not invent a missing tussock crown. [Working with Nanite-Enabled Content](https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content)

For the conventional path, use separate near, middle and distant representations with overlapping transitions. A ground material can carry distant colour and texture, but cannot replace nearby silhouette or parallax. Epic documents foliage culling/fade, and warns that Nanite-enabled foliage does not use the same instance distance-cull/fade behaviour; do not copy the existing fade strategy blindly. [Foliage Mode](https://dev.epicgames.com/documentation/unreal-engine/foliage-mode-in-unreal-engine)

PCG hierarchical generation can organize different scales of vegetation into grids. It helps distribution and streaming; it does not make visible grass free to render. [PCG Generation Modes](https://dev.epicgames.com/documentation/unreal-engine/using-pcg-generation-modes-in-unreal-engine)

## Small benchmark before another full-map density pass

Use a representative road-and-hillside strip that includes vegetation beyond the current 42 m cutoff. Review at driver height, beside the verge and from an overview. The target is overlapping vegetation mass and continuity into the distance, with the road, rock and water masks preserved.

Hold visible coverage, camera, resolution, lighting, scalability and Lumen settings constant across the three paths. Begin static and shadowless, then test localized shadows/wind separately. Measure median and p95 full GPU/frame time, CPU time, VRAM, draw calls, Lumen/shadow work and Nanite raster/material passes where applicable. Converting to Nanite shifts work between passes: legacy BasePass alone cannot choose a winner.

Use Blender for asset-shape reviews as requested. Inspect the actual in-engine result for distance thinning, transition bands and shimmer while driving; use Unreal captures only if needed to evaluate those engine-specific effects.

The previous 0.432 ms result was ONLY the grass BasePass delta for a stationary view, with grass disappearing at 42 m. Full GPU time was around 9-10 ms and variable, not noisy BY 9 ms. That result cannot establish the cost of full distant hillsides.

Earlier project work in docs/LEG_DRESSING_PLAN.md recorded Lumen and shadows as major vegetation costs; some runs were thermally throttled or affected by checker-material fallbacks. Treat those as diagnostic history, not clean evidence that Nanite or voxels are faster/slower here.

**Decision:** prioritize substantial tussock crowns and continuous near-to-far coverage. Run Voxelize as a serious candidate alongside the conventional LOD control, then choose from equal-coverage image quality and full-frame measurements on the RTX 4050.
