# Dense varied meadow: meadow-variety-04

The user rejected the repeated clump shape and requested greater density and
variation. The coverage library now has four different forms, each in five slope
variants. They share one opaque material and the restrained dry straw palette.

| Form | Shape | Source height | Triangles per patch |
| --- | --- | --- | --- |
| Mat | Low, fine blades spread across a wide footprint | 12-27 cm | 88 |
| Tuft | Upright fine blades with a few folded leaves | 22-48 cm | 90 |
| Swept | Lower blades leaning together | 16-36 cm | 100 |
| Seed | Taller narrow stems with six small seed ears | 34-68 cm | 98 |

The heights precede instance scaling and root burial. Spacing changes from
0.66 m to 0.56 m, with greater placement jitter. Low grass occurs throughout;
taller and leaning forms are selected using a mixture of broad spatial noise and
random choice. Taller seed patches are a minority. Heights, spreads and warm
brown/straw values vary by form, rather than just rescaling one plant shape.
The shoulder and river masks still feather coverage away from the route/water.

The grass keeps one material, no alpha cards, no collision or shadow casting,
and 25-42 m fade/cull. There are more mesh batches and instances, so timings
must be measured rather than inferred from triangle counts. Non-grass geometry
and dressing remain unchanged. Previous sources/previews are retained under
`GrassIterations/variety-before/`.

Blender driver-height and close verge views were inspected. Source validation
passed for all 20 meshes, per-form triangle counts, linear FBX colour transfer,
non-grass placements and smooth terrain continuity.

The meadow now contains 15,181 grass patches (39.1% more than fine-03): 6,842 Mat,
2,962 Tuft, 4,283 Swept and 1,094 Seed. Total unculled grass triangles are
1,404,188 (28.7% more). The full assembly has 46 source meshes, 17,862 dressing
instances and 152,786 source triangles. The meadow-variety-04 import passed.

The benchmark maps were regenerated with all 15,181 grass instances. Four cooled
ABBA runs at 1440 x 900 / 100% screen percentage, standalone offscreen DX12,
completed without material errors or observed thermal-throttle flags. Each run
uses 550 warm samples. Grass adds 0.4320 ms to the GPU base pass and 41 draw calls
in this driver-height view. This is higher than fine-03's historical 0.2369 ms
base-pass result, consistent with denser coverage and more mesh batches; the runs
are not a direct old/new paired benchmark. Total GPU/frame-time variability means
the negative total GPU delta is not a speedup claim or a precise overall cost.
Kuwahara was disabled in both variants. No Unreal screenshots were captured.

Final Blender images, import report, source checks and performance analysis are
archived in `GrassIterations/variety-04/`. Raw CSVs are in
`GrassIterations/performance/meadow_variety04_*`.
