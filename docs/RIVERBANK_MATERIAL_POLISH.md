# Riverbank material and plant shading pass

Owner feedback, 8 November 2026: the fern appearance is unsatisfactory in both shape and shading. The material pass does not resolve that concern. A separate geometry and shading candidate is documented in [Fern revision](FERN_REVISION.md); it has not replaced the live plants.

Status, 8 November 2026: the first bounded candidate is installed in `L_LidarStudy`. Material installation and integrity checks passed. Final in-game visual acceptance and performance acceptance remain pending. This is not a completed rollout of the wider visual/performance plan.

## Changes

- Bank surface and earth now share a consolidated soil/rock/moss calculation using the existing textures. Roughness, dampness and surface relief follow the same material blend. Rock fissure relief is retained; fine normal detail fades with distance and pixel footprint.
- Leaf shading uses existing vertex colour and tip coverage to vary roughness, specular response and light transmission. Leaf colour, wind and geometry remain intact.
- Cascade fern normal strength and occlusion are softened. Ground contact uses the existing FernFloor bake with less compounded darkening.
- Existing authoring entry points preserve this candidate through an enabled recipe, rather than silently rebuilding the earlier material graphs.

The five saved assets under `/Game/GrandTour/ArtTests/LidarStudy/FirstSection` are `M_BankSurface`, `M_BankEarth`, `M_BankLeaf`, `M_BankGroundLeaf`, and `PerceivedDetail/M_PD_Fern`. No new texture assets, geometry, plant instances or render passes were introduced. Lighting, renderer settings, physics and collision are unchanged.

The consolidated ground shader reduces duplicated texture work in the source graph. That is an implementation choice, not a measured GPU improvement. Custom HLSL texture reads are not fully represented by Unreal's graph-level sample count.

## Evidence and outstanding review

`Saved/LidarAuthoringQA/VP2Materials/final-install.json` records successful Unreal installation, graph statistics, asset hashes and unchanged plant snapshots. `file-validation.json` verifies the five installed asset hashes, protected files and Python syntax. The local 229 instances and outside 207,399 low-plant instances retain their original placement hashes.

Baseline and an initial ground-only trial were captured. Reviewing that trial exposed overly smooth rock; the final material restores fissure relief. Those trial images and timings therefore do not validate the final combined candidate.

The final standalone capture loaded without a logged material fallback, but Skate was sharing the GPU and capture progress became unusably slow. The owned offscreen Unreal process was stopped; Skate was left running. At the owner's request, performance testing remains pending. The final candidate has no completed screenshot or motion comparison yet, and no FPS improvement is claimed.

Pending review: compare rock relief, soil/moss transitions, wetness, plant translucency, contact darkness and distant foliage stability using matched views and motion. Then run clean repeated timing comparisons at the saved 1600x900 / TSR75 profile, inspect GPU telemetry and assess the wider plan's frame-time and memory gates. Owner visual acceptance is separate from these technical checks.

The review status page is `Art/Export/LidarStudy/FirstSection/Review/MaterialPolish/index.html`.

## Rebuild and resume

Run from `C:\GrandTour`, with Unreal and competing games closed:

```powershell
powershell -NoProfile -File Art/run_bank_material_polish.ps1 -Mode final
python Art/tools/validate_bank_material_polish.py
python Art/tools/bank_material_review.py select final
python Art/tools/bank_material_review.py capture vp2-b1
python Art/tools/bank_material_review.py series repeated
python Art/tools/bank_material_review.py motion vp2-final-motion
python Art/tools/package_bank_material_review.py
```

The series alternates baseline/candidate comparisons and restores the final variant. Inspect run conditions and telemetry before accepting any timing result. Raw motion output uses `D:\GrandTourReviews\VP2Materials`; stills and timing evidence remain under `Saved/LidarAuthoringQA`. Capture tools do not automatically grant visual acceptance.

The source recipe is `Art/Export/LidarStudy/FirstSection/MaterialPolish/recipe.json`; implementation is `Art/Unreal/lidar_bank_material_polish.py`. The existing FernFloor contact bake must be updated if terrain or planting changes. Full-world regeneration has not been validated by this bounded pass.

## Rollback

With Unreal closed, run `python Art/tools/bank_material_review.py select baseline`. This restores exactly the five materials and refuses to overwrite unrecorded subsequent material edits. Before rebuilding baseline assets through the authoring tools, also set `enabled` to `false` in the recipe so the hooks do not reapply the candidate.

The immutable backup location and original hashes are recorded in `Saved/LidarAuthoringQA/VP2Materials/backup.json`; the current backup is `Saved/LidarAuthoringBackups/VP2Materials-1794167167600687000`. Do not restore the whole backup over later unrelated edits.
