# Tussock art study

The dense rendering benchmark achieved coverage but was rejected for shape and
colour. This separate Blender study works on those issues before another map
conversion. It does not change the existing Unreal levels or benchmark assets.

Source: `Art/Blender/build_tussock_style_study.py`.
Build: `bash Art/build_tussock_style_study.sh 07`.
Outputs: `Art/Export/TussockStyleStudy/07/`.

## Direction

- Arching straw: an uneven crown with a drooping skirt, fewer rigid upright tips.
- Wind-combed rust: lower and wider, with an asymmetric sweep and weathered brown.
- Tall weathered: a narrower, taller crown, bent tips and subdued grey-brown.
- Fine undergrass: short mixed stems to connect the larger plants to the ground.

Colour families are separated between plant forms instead of assigning all
colours randomly to every clump. Roots are restrained umber; leaves retain body
colour rather than acquiring luminous pale outlines. Clusters of similar plants
break up the uniform mixture. The material uses vertex colours, diffuse and thin
leaf transmission; foliage does not cast shadows, matching the shadowless
benchmark scope. Artist normals soften ribbon-face lighting.

## Review history

03: fine arching leaves, but the render exposed incorrect face winding and very
dark self-shadowing. Rejected.

04: corrected facing and removed grass shadows. Softer, but the palette still
averaged to beige and the forms were too similar. Rejected.

05: distinct straw, rust and grey-olive families with stronger form separation.
The tall form read like stiff reeds. A lineup bug originally repeated one source
mesh; the corrected lineup now displays the actual four meshes at equal scale.

06: lowered and bent the tall form's tips, softened the rust colour, shifted the
grey-olive toward grey-brown and grouped the planting into loose colour patches.

07: spread the roots and curve outward earlier to reduce tight stem bundles;
increased two-sided transmission to soften dark leaf backs; warmed the pale
weathered form to taupe. This is the current art-review candidate.

`Roadside.png` is a small planting study; its simple road is supporting context,
not a proposed replacement for the existing detailed road. `Shapes.png` shows
the four meshes at equal scale with palette samples. Both are actual Blender
renders. Editable scenes are `TussockStyleStudy.blend` and `TussockShapes.blend`.

## Production status

This is a near-detail art study, not an optimized replacement. Each large crown
has 2,660 triangles; the fine patch has 600. No production LODs, FBX import or
Unreal material validation have been done for these new forms. Earlier benchmark
timings do not apply. Rendered on CPU with four threads while the user's game
remained running; no GPU performance measurements were attempted.

The user subsequently approved study 07 for import. Its Unreal assets, authored
LODs and complete test map are documented in `docs/TUSSOCK_STYLE_IMPORT.md`.
