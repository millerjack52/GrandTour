# Dry fine grass: meadow-fine-03

The user found meadow-palette-02 too green and requested finer grass. The grass
palette now uses warm brown roots, muted straw, dry ochre and sparse beige tips.
The olive-green blade group is removed. Large tussocks, willow leaves and the
meadow underlayer receive related warm, restrained adjustments. Lighting and
exposure are unchanged.

Each shared patch combines 12 folded blades (60 triangles) with 20 slender pointed
blades (40 triangles). The fine blades are authored 17-34 cm high and 1.6-3.6 cm
wide before instance scaling, clustered between the two remaining broad fans.
They share the same opaque material and instance as the broad grass. There is
no extra material pass, alpha masking, shadow caster, collision or texture sample.

All 10,914 grass placements are retained. Total grass triangles remain 1,091,400;
the patch vertex count rises from 120 to 152. Equal triangle counts do not imply
identical GPU cost, especially for narrow blades. The existing 25-42 m fade/cull
and no-shadow policy remain.

Source validation compares all placements to palette-02, checks 100 triangles
and 152 vertices per patch, confirms linear FBX colours, and preserves the smooth
terrain checks. `Art/validate_meadow.sh` also updates `GrassCoverage.blend`.

Review images and measurements are recorded under `GrassIterations/fine-03/`.
Blender driver-height, ford and verge views were reviewed. Source validation and
the meadow-fine-03 Unreal import passed. Four cooled ABBA runs at 1440 x 900,
100% screen percentage, offscreen DX12 completed without material errors or
observed thermal throttling. Each run contributes 550 warm frames. The grass
base-pass delta is 0.2369 ms; game-thread delta is 0.1215 ms. Overall frame/GPU
timing varies and its negative delta is not evidence of a speedup. Kuwahara is
disabled in both variants; no Unreal screenshots were captured. These results
cover the stationary driver-height view, not all production driving conditions.
The existing benchmark maps were reused because all instance placements and
shared asset paths are unchanged, verified against the preceding manifest.
