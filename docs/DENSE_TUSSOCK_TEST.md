# Dense tussock rendering comparison

This is an isolated prototype under `/Game/GrandTour/ArtTests/DenseTussock`.
The reviewed `L_RoadFordStyle` remains unchanged. Source assets and reports are
under `Art/Export/DenseTussock`.

## Source and visual iterations

`dense-tussock-01` introduced three substantial tussock crowns and a fine
underlayer. The first Blender review exposed upright, palm-like bases; revision
02 lowers the arching leaf tips and warms the roots. The resulting rounded masses
are a density/rendering test, not an approved final vegetation style.

The source has three crown variants with 160 curved ribbons each, plus a 48-blade
underlayer. Crown LOD triangle counts are 1,280 / 432 / 128. Underlayer LOD counts
are 192 / 64 / 20. Lower LODs retain distributed blades with wider ribbons to
reduce loss of apparent coverage. Root positions follow the continuous terrain;
full rotations align each instance to its local slope rather than multiplying
the mesh library into separate slope variants.

All versions use 15,796 identical placements (2,095 crowns, 1,413 shaggy crowns,
616 tall crowns and 11,672 underlayer patches), opaque two-sided vertex-colour materials,
no WPO, no collision, no grass shadows and no component distance cutoff. Vertex
alpha is unused, avoiding the voxel normal-distribution/height-mask conflict.
Road and river masks are maintained. The test field extends to about 95 metres
along the road, including vegetation beyond the former 42-metre cutoff.

The initial Unreal captures exposed very dark undersides with Default Lit shading.
The shared material was changed to Two Sided Foliage with vertex colour feeding
both base and subsurface colour. Initial engine views are archived under
`iterations/02-default-lit`. No global lighting or exposure was changed.

## Rendering variants

- `L_DT_LOD_Driver` and `L_DT_LOD_Overview`: non-Nanite instancing, three imported
  LODs with screen-size thresholds 1 / 0.08 / 0.025.
- `L_DT_Voxel_Driver` and `L_DT_Voxel_Overview`: same LOD0 source with Nanite
  Shape Preservation = Voxelize.
- `L_DT_Preserve_Driver` and `L_DT_Preserve_Overview`: Nanite Preserve Area control.

The initial NullRHI editor attempt crashed in the static-mesh LOD-copy path. The
setup now imports authored LOD FBXs directly in an offscreen DX12 editor. The
setup report verifies every mesh's Nanite mode, LOD count and screen thresholds.

## Verification workflow

`Art/build_dense_tussock.sh` builds the separate Blender scene and FBXs.
`Art/setup_dense_tussock.ps1` imports and saves the six comparison maps.
`Art/capture_dense_tussock.ps1` produces matched engine captures: Blender is used
for art iteration, but engine-specific LOD/voxel behaviour requires Unreal review.
`Art/profile_dense_tussock.ps1` benchmarks the three modes in forward/reverse
order in two stationary views. `Art/analyse_dense_tussock.py` records full GPU,
frame, CPU, VRAM and available Nanite/Lumen pass statistics from warm samples.

Resolution is 1440 x 900, DX12, 100% screen percentage, fixed scene lighting and
exposure, with shader warm-up and GPU cooldown. Kuwahara is disabled equally in
all variants because of its previously recorded unrelated compile issue. These
are matched static-view comparisons, not complete vehicle-driving benchmarks.
Do not infer overall performance from the legacy BasePass when comparing Nanite.
The camera-constrained review PNGs are 1440 x 810; benchmark render resolution is
verified separately from the CSV metadata.

## Image review

The authored LOD path retains the most continuous distant cover in the matched
overview. The Voxelize path exposes more brown ground between clumps as they
recede. Identical instance counts do not guarantee identical apparent coverage:
the widened authored LOD ribbons deliberately compensate for lost geometry.
The current tussock crowns also remain too repetitive for final art approval.
These are renderer experiments, not a claim that the reference style is finished.

## Performance status

The first benchmark launch was held by the cooldown gate. On 2026-09-29 at about
09:54 local time, with Unreal closed, Windows GPU Engine counters attributed
81.6% 3D usage to PID 2080 (`GoW.exe`, God of War). NVIDIA reported 84 C and 90%
overall GPU utilization. No performance result from that state is acceptable.
The user closed the game and three clean driver-view runs completed. No user
process was terminated. The harness explicitly guards against `GoW` before and
during each benchmark now.

| Mode | GPU median (ms) | GPU p95 (ms) | Frame median (ms) | Frame p95 (ms) |
| --- | ---: | ---: | ---: | ---: |
| Authored LOD | 10.654 | 12.026 | 11.722 | 22.355 |
| Nanite Voxelize | 10.097 | 11.380 | 11.376 | 21.775 |
| Nanite Preserve Area | 10.169 | 11.410 | 11.458 | 21.206 |

These are **one run per mode**, 550 warm samples per run, full-scene GPU time at
1440 x 900. They are not incremental grass costs and do not establish locked
60 fps gameplay. None of the three recorded thermal-throttling flags. CSV
metadata confirms DX12 and resolution; logs confirm 100% screen percentage and
uncapped rendering. Lumen remained enabled. No overview timings are available.

God of War restarted as PID 3580 at 10:02:52 local during run 4, which ended at
10:03:05. That run is retained for audit with `valid: false` in `runs.json` and is
excluded from `analysis.json`. The user explicitly chose to save the prototype
and partial results rather than continue. No benchmark or editor remains running.

**Provisional choice:** authored LODs retain the strongest distant coverage for
about 0.5 ms more GPU time in this single driver-view comparison. The Nanite
variants are not equivalent in apparent density, so their lower timing is not
evidence of an equal-quality optimization. Do not promote a final renderer winner
until repeated overview and motion checks are complete.

Resume with `Art/profile_dense_tussock.ps1 -StartIndex 4`, with other games closed,
then run `Art/analyse_dense_tussock.py`. The clean first three runs are preserved.
Raw CSVs, telemetry, invalidation reason and analysis are in
`Art/Export/DenseTussock/performance`. Engine captures for all six maps are in
`Art/Export/DenseTussock/UE_*.png`; Blender previews and the editable `.blend`
are in the same output folder.

Pending: repeated full-GPU measurements, in-motion transition/shimmer review,
and a voxel visualization check confirming where voxel clusters actually render.
The import report verifies the Voxelize setting; that alone does not prove its
runtime voxel coverage. Wind, grass shadows, PCG streaming and a complete driving
leg remain outside this static prototype.

`Art/capture_dense_tussock.ps1 -VoxelDebug` is prepared for the outstanding voxel
visualization check; it has not been run. This uses a separate output and report
so it will not replace the six normal review captures.
