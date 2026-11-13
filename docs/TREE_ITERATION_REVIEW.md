# Willow modelling iteration review

Request: iterate the actual models against the new tree references until the
quality improves visibly. All review images are Blender renders of real mesh
assets, with a fixed studio camera/light setup for each view. No concept image
is substituted for a model render.

References: `Art/References/Trees/willow-silhouettes-v1.png` and
`willow-modelling-details-v1.png`. Priority features: asymmetric bent trunk,
continuous forks, clear major-branch hierarchy, connected hanging leaves, open
canopy silhouette, and painterly warm/cool bark colour. The sparse variant is
intentionally less leafy than the mature tree.

## Saved passes

Every pass is under `Art/Export/RoadFordStyle/Iterations` and contains renders,
a source snapshot, a Blender scene and triangle counts.

| Pass | Observed problem | Change for the next pass |
| --- | --- | --- |
| baseline | Straight trunks, regularly distributed branches, detached-looking leaf clouds | Author the major limbs; merge the scaffold into one trunk; attach leaves to actual shoots |
| pass-01 | Improved forks but an under-filled crown and repetitive paired hanging fans | Add supporting branchlets and irregular pendant distribution; strengthen bark palette |
| pass-02 | Better canopy, but diamond-shaped leaves and clay-like bark in the close-up | Add a longer tapered leaf outline and broad warm/cool bark patches |
| pass-03 | Dark bark patches too broad; bare shoots too regular; scrub leaves oversized | Reduce dark coverage, break up bare twig tips, reduce scrub leaf size and simplify fine stems |
| pass-04 | Final model review, followed by a scene check | See final validation below |

## Reproduce the review

Run `bash Art/review_riverbank.sh <new-pass-name>` from the repository root.
The script renders the mature front, three-quarter and fork detail views, then
the sparse tree and scrub views. It saves a source snapshot of
`Art/Blender/riverbank_vegetation_v2.py`, the active model generator. The original
`riverbank_vegetation.py` is retained as the previous implementation.

The revised trunk uses a merged, reduced polygon scaffold. The leaves and fine
branches remain explicitly modelled, with no opacity-mask texture. Bark colour
is stored in vertex colours and exported to Unreal. Fine stems use fewer sides
than structural branches. Simplified convex collision follows the lower trunk,
not the canopy.

## Final validation

Visual acceptance is a modelling judgment, not a claim of a perfect match to
the concept. The final scene, collision import and mesh counts are recorded
below. Wind animation, PCG authoring, foliage voxelisation,
runtime performance and driven collision feel remain outside this pass.

Final revision: `riverbank-refined-04`, imported successfully into
`/Game/GrandTour/ArtTests/RoadFordStyle/L_RoadFordStyle`. Both trees have four
verified lower-trunk collision hulls. All 2,681 instance transforms are unchanged
from the saved baseline; model geometry and bark/leaf materials changed.

Final source triangles: mature 50,072; sparse 9,878; open scrub 2,272; dense scrub
8,688. The mature tree peaked at 71,132 in pass 03 before the fine stems were
simplified. Total assembly source triangles are 150,906, compared with 97,760
before this iteration. More detail has a cost; no runtime performance claim is
made from these counts.

The final studio and ford renders were inspected. The major forks are continuous,
leaf sprays visibly connect to supporting shoots, the sparse tips have irregular
branching, and the open/dense scrub remain distinct. The scene view retains the
open driving line. The final library display also corrects scrub floor contact;
this display adjustment does not move the in-level instances.

## Mature canopy study, 2026-10-06

The owner rejected the existing trees as unfinished. A separate mature-willow
study now lives in `Art/Blender/riverbank_vegetation_v3.py`. The active level
generator still uses v2; this study does not replace the imported level assets.
The younger tree and both scrub models remain the v2 versions.

`Art/Export/RoadFordStyle/Iterations/canopy-v3-02/TreeReview.blend` contains the
latest actual mesh, with front, three-quarter and branch-detail PNG renders in
the same folder. `canopy-v3-01` preserves the first pass and its source snapshot;
`canopy-v2-comparison` preserves a fresh v2 render under the study lighting
(the old tree's highest tip extends outside that comparison frame).

The new mature tree uses curved structural limbs with merged forks, alternating
secondary branches, two additional upper limbs, overlapping pendant foliage,
four-triangle folded leaves, stronger gold/olive colours, and sculpted and
vertex-coloured bark grain. Fine branch tips are restored after the scaffold
remesh so they are not lost below its voxel size. The lower trunk follows the
previous path and retains its four collision hulls.

The second pass has 118,626 source triangles and measures approximately
9.58 x 7.77 x 7.71 m. It contains no zero-area faces under the review's 1e-10
area threshold. This is substantially heavier than the old 50,072-triangle
mature tree: density, LODs, wind, engine materials, collision fit and runtime
performance still need game-side validation. Visual review covered all three
saved views; user acceptance of this new direction is pending.

Reproduce in background Blender with `Art/Blender/review_willow_canopy.py --
<new-label>`. An optional second argument selects `riverbank_vegetation_v2`
for comparison. Labels containing an existing saved review are refused, to
preserve past iterations. The v3 builder depends on the retained v2 module.

## Wood revision, 2026-10-06

The owner rejected the canopy study's wood. Latest review:
`Art/Export/RoadFordStyle/Iterations/wood-v4-04/TreeReview.blend`.
The branch-detail, three-quarter and front renders are actual Blender renders.
The previous colour bands and crosswise surface displacement have been removed
from the visible bark treatment. Wood now uses smoother surface shading, shallow
branch-aligned relief, and a generated painted bark texture. Two limb coordinate
charts are sampled separately and blended at forks to avoid stretched UV bands.

`Art/Blender/willow_bark.py` is the bark helper, called by the v3 builder. Earlier
wood studies preserve the failed procedural tests and the first textured pass.
The final texture is packed into the saved blend and also stored at
`Art/Textures/WillowBark/willow_bark_painted_v1.png`. The complete prompt and
built-in image-generation provenance are in that folder's `generation.txt`.
Texture edge continuity is not pixel-verified; blending may soften fine grain
at the forks. This version remains a visual study awaiting owner feedback.

`Art/Blender/check_willow_wood.py -- wood-v4-04` compares the saved file with
`canopy-v3-02`. Foliage geometry and the four collision meshes match; all vertex
coordinates are finite, and no zero-area faces were found. Source geometry stays
at 118,626 triangles. The younger tree and scrub have not been revised. The
two-UV bark material and blend attribute need baking or equivalent material
support for Unreal; no level import or runtime-performance claim is made.

## Owner reference rebuild, 2026-10-06

Three newly supplied images are preserved in `Art/References/Trees/UserWillows`:
the lakeside tree, a dense weeping-willow image, and a weeping-willow model view.
These supersede the earlier generated concepts as the modelling direction for
this study. The lake image informs the low fork and multiple rising limbs; the
other two inform long pendant shoots, fine green leaves and a rounded canopy.

New standalone generator: `Art/Blender/willow_reference_v5.py`. Latest model:
`Art/Export/RoadFordStyle/Iterations/reference-v5-02/TreeReview.blend`.
The previous pass is preserved in `reference-v5-01`. The second pass increases
crown coverage with leafy upper branchlets and longer, denser green curtains.
Leaves use two triangles each. The bark texture from the wood study is retained,
darkened and packed into the model. No old collision shapes are reused: three
new hulls follow the new lower trunk, with no canopy collision.

The second pass has 49,217 leaves, 818 pendant shoots and 190,524 triangles,
approximately 8.76 x 7.78 x 8.10 m. `check_reference_willow.py -- reference-v5-02`
reopened the saved blend and verified finite coordinates, zero degenerate faces,
three hulls and packed file textures. Front, three-quarter and trunk detail
renders were inspected. This is a substantial change in tree form, not an
approval claim or a one-to-one botanical reconstruction of the photographs.

Reproduce with `review_willow_canopy.py -- <new-label> willow_reference_v5` in
background Blender. The active Unreal level remains on the original assets.
Wind, LODs, the game-side bark material and runtime cost still require work.

## Willow family variations, 2026-10-06

The owner accepted `reference-v5-02` and requested variations. The saved accepted
model remains available. `willow_reference_v5.py` now also accepts named presets;
`build_willow_variations.py -- willow-family-01` builds the four new models into
`Art/Export/WillowFamily/willow-family-01`.

| Variant | Form | Height | Source triangles |
| --- | --- | ---: | ---: |
| Young | Narrower trunk and crown, fewer primary limbs | 6.02 m | 102,472 |
| Broad | Wider crown, thicker wood and fuller curtains | 8.52 m | 231,828 |
| Windswept | Leaning scaffold and foliage trailing to one side | 7.48 m | 136,190 |
| Weathered | Open crown, omitted limbs, one blunt broken limb | 7.97 m | 73,436 |

The variants use different seeds, structural parameters, limb selections and
foliage densities. They retain the accepted narrow leaves and packed bark
texture, with restrained green/olive colour changes. Each has three lower-trunk
collision hulls built for its own shape. No canopy collision is added.

Each variant has its own PNG review and standalone `.blend` scene (`young`,
`broad`, `windswept`, `weathered`). `WillowFamily.blend` includes a labelled
lineup and the four reusable source objects at the origin in a hidden source
collection. Display copies share their source meshes. The lineup shows actual
relative sizes; individual review images are framed separately.

The generation checks found no zero-area faces or non-finite coordinates.
`check_willow_family.py -- willow-family-01` verifies saved individual files,
packed textures, origin placement, review cameras and source objects in the
library. These are Blender assets; Unreal materials, LODs, wind and performance
remain unverified. No imported level assets have been replaced.

After building, `finish_willow_family.py -- willow-family-01` finalizes the
standalone files' startup scenes and renders the library with reduced studio
light energy and darker labels. Run `check_willow_family.py` after this step;
it also checks that each file opens with an active review camera.
