# FS1 - LiDAR forest silhouettes

Owner direction, 2026-10-20: revise the trees in L_LidarStudy itself. Waimeamea
photos lead species, colour and habitat; Danny Weinbaum's *Art Tips for Building
Forests* supplies composition guidance, not a different biome or a performance
recipe. No separate demonstration level.

Reference: https://www.gamedeveloper.com/art/art-tips-for-building-forests

## Diagnosis

NP5 explicitly snaps beech foliage to a small number of shallow horizontal
tiers. Repeating those shelves and symmetrical forks across the forest remains
visible after the LP6 shading corrections. The distant representation must be
rebaked from a changed tree rather than disguising the old shape with tint.

The reference distinguishes tall, clear-boled interior stands from fuller bush
edges. It also calls out relatively little shrub growth inside mature stands;
generic dense shrub placement everywhere would contradict the photos.

## Implementation

- `Art/Blender/build_lidar_forest.py`: map-owned deterministic beech forms. Branch
  attachments vary in height and direction; unequal side branches carry radial,
  overlapping leaf groups. Every group survives all three geometry LODs, with
  fewer broader folded sprays. No shared horizontal tier planes.
- `Art/Unreal/lidar_forest_shapes.py`: imports only the FS1 forms, rebuilds their
  canopy representations and applies them to existing instanced components in
  the saved map. Records mesh budgets, instance counts, ground digest and backup.
- `Art/Unreal/lidar_canopy_assets.py`: consults `Place/forest-shapes.json` for
  map-owned sources on future Install/Polish runs. Updates authored LODs in place
  instead of deleting meshes referenced by the level. Source bounds determine
  placement scale and trunk collision scale, independent of far-card bounds.
- `Art/Unreal/install_lidar_place.py`: uses the same tint helper as the canopy
  builder. It finds the tint below the LP6 shading node, so repeat installs cannot
  stack another darkening multiplier. `run_lidar_forest.ps1 -Check` checks that
  applying the tint twice leaves the graph unchanged.
- `Art/run_lidar_forest.ps1`: waits for the Unreal slot, launches one hidden
  editor, waits for natural exit, checks fresh evidence and material errors.

Shared NativePlants source assets remain available. The existing placement mask,
roads, water, paddock exclusions, terrain and trunk collision instances are
preserved during the shape comparison. Near foliage stays opaque and instanced;
the three-view far card remains six triangles. No new per-tree tick or physics.

## Validation sequence

1. Capture the current saved map at the paddock, gate, river and access views.
2. Replace the mature form first and compare those exact views in the actual map.
3. Carry the successful crown treatment into pole and forest-edge forms, with
   habitat-appropriate proportions. Re-bake far cards from each actual source.
4. Check saved mesh LODs, roots, unchanged ground digest and instance counts.
5. Compare matched standalone performance at the saved 1600x900 TSR75 profile,
   and check moving river views. Owner visual/drive approval is the final gate.

Baseline `fs1-before`: 59.8-60.0 FPS across the four views, p95 frame time
16.676-16.685 ms, GPU means 7.235-9.036 ms. Isolated 42.179 and 55.521 ms frames
occurred. These are capped offscreen measurements, not a whole-route guarantee.

An initial import crashed before any level save: calling Unreal `set_lods` on an
existing authored mesh replaces its LOD descriptions with empty reduction slots;
the subsequent `SetLodFromStaticMesh` dereferences the empty destination. The
pipeline now retains the authored destination slots and validates descriptions
before copying. The previous canopy assets and map were backed up before import.

## Shape review and final mesh budgets

The mature-only in-map capture (`fs1-mature`) showed deeper irregular crowns at
the paddock and river; the unchanged pole and edge trees still displayed the
original horizontal shelves. That comparison led to the pole and edge revision.
Mature stands keep tall clear boles; pole crowns are narrower and taller, while
edge crowns begin lower and spread unevenly. The existing 20-40 m species cohorts,
tree positions and dead spars remain, without adding a uniform shrub layer.

| Form | LOD0 | LOD1 | LOD2 | Far card |
| --- | ---: | ---: | ---: | ---: |
| Mature | 18,897 | 6,419 | 1,466 | 6 |
| Pole | 5,945 | 1,945 | 501 | 6 |
| Edge | 18,897 | 6,419 | 1,466 | 6 |

All 32 bough groups on mature/edge and 21 on pole persist at every geometry LOD.
Far-card baking uses the source geometry bounds, not a previous card's square
bounds, preventing repeated bake growth. Alpha-coverage-preserving mipmaps use
the material's 0.35 clip threshold. Cards remain a three-view atlas per species.

The importer performs root sampling against final relief tiles and checks the
forest counts against the authored tree list. Shared native kit models, the
terrain output, water and track generation are not rebuilt by this pass.

## Saved-map checks, 2026-10-20

The final import saved 69,855 mature trees, 70,886 pole trees, 5,554 edge trees and
2,125 dead spars: 148,420 instances, unchanged. All four canopy meshes have four
LODs. Sampling 2,116 root pivots against the final ground found 0.0 cm maximum
error. Ground digest remains `DB443C52AD8AD4F3A1E2CD57E8E4716F`.

The full import exited normally but the strict runner rejected transient shader
warnings during replacement of the previous material graphs. The graph builder
now neutralises old custom nodes before removal. A subsequent clean editor check
loaded the saved materials without compilation errors, verified the source cache
and alpha-coverage mip settings, and applied each tint twice without adding nodes.
Evidence: `Saved/LidarAuthoringQA/FS1/install.json` and `check.json`.

Matched final stationary measurements (`fs1-final`, 840 measured frames/view):

| View | FPS mean | Frame p95 ms | Frame max ms | GPU mean ms | Baseline GPU mean ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| Paddock middle | 60.0 | 16.674 | 16.966 | 7.245 | 7.708 |
| Paddock gate | 60.0 | 16.674 | 16.734 | 6.863 | 7.235 |
| River | 59.9 | 16.681 | 44.520 | 8.484 | 8.447 |
| Access | 60.0 | 16.673 | 16.866 | 8.832 | 9.036 |

These are the existing 1600x900 TSR75 capped offscreen preset; loading, teleports
and screenshots are excluded. The isolated river frame remains, so this is not
a hitch-free or whole-route 60 FPS guarantee. Actual forest screenshots are
`Place/PF60-fs1-final-*.png`, with the matched old trees in `PF60-fs1-before-*.png`.
Owner visual and drive approval remains outstanding. All changes are uncommitted.

Moving checks (`fs1-walk`, 440 measured frames/site, 48.97-49.32 m travelled):

| View | FPS mean | Frame p95 ms | Frame max ms | GPU mean ms |
| --- | ---: | ---: | ---: | ---: |
| Ford | 59.5 | 16.686 | 56.840 | 10.276 |
| Gravel bar | 59.9 | 16.690 | 20.048 | 11.283 |
| Shallows | 59.9 | 16.685 | 27.041 | 10.969 |
| Across forest | 60.0 | 16.681 | 17.778 | 10.641 |

The ford contains an isolated 64.779 ms GPU sample (GPU timing and logical frame
timing do not necessarily line up on the same frame). Sustained GPU means are
close to the previous LP6 moving run: 10.222, 11.183, 10.942 and 11.711 ms. A
single-site repeat is recorded separately, rather than discarding the first run.

The identical ford repeat (`fs1-ford-repeat`) averaged 60.0 FPS over 440 measured
frames, p95 16.676 ms, p99 16.724 ms, maximum 17.140 ms. GPU mean/p95/max was
10.125/11.456/13.044 ms. The larger spike did not recur; its cause is not
conclusively attributed. Complete source reports, including both runs, are in
`Saved/LidarAuthoringQA/FS1/result.json`; every measurement is in the stage log.
