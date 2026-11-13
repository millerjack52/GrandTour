# Riverbank vegetation kit

Built for the RoadFordStyle assembly after the road and colour reviews. Visual
reference: the owner's supplied New Zealand ford and stream photographs, with
open deciduous branching, pale weathered trunks, autumn colour and low scrub.
These are stylised willow-inspired forms, not botanical reconstructions.

| Mesh | Feature to review | Triangles | Collision |
| --- | --- | ---: | --- |
| SM_RF_Willow_Mature | Bent continuous trunk, spreading limbs and pendant foliage | 50,072 | Four convex lower-trunk hulls |
| SM_RF_Willow_Young | Smaller sparse tree with irregular bare twig tips | 9,878 | Four convex lower-trunk hulls |
| SM_RF_Scrub_Open | Exposed twigs with smaller connected leaves | 2,272 | None |
| SM_RF_Scrub_Dense | Shorter, fuller silhouette with smaller leaves | 8,688 | None |

Leaves are small, bent lance-shaped geometry with two-sided materials in Unreal;
no alpha-cutout foliage texture is needed. Major forks use a merged scaffold;
fine branches taper through faceted rings. Four UCX convex prisms follow each
tree's lower trunk. The canopy and upper
branches do not add blocking collision. Trees are not functional winch anchors.

## Files

- `Art/Blender/riverbank_vegetation_v2.py`: active mesh construction module.
- `Art/Blender/riverbank_vegetation.py`: retained previous implementation.
- `Art/Export/RoadFordStyle/RiverbankVegetation.blend`: reusable original objects
  plus a separate asset-review scene. The original export objects are hidden;
  the review scene uses visible display copies of their meshes.
- `Art/Export/RoadFordStyle/Riverbank_asset_review.png`: individual-model review.
- `Art/Export/RoadFordStyle/RoadFordStyle.blend`: the complete assembled scene.
- Four matching `SM_RF_Willow_*.fbx` / `SM_RF_Scrub_*.fbx` files in that folder.
- Unreal destination: `/Game/GrandTour/ArtTests/RoadFordStyle`.

The assembly adds six trees and 62 scrub instances. Existing road geometry,
surface colours and 2,613 placements retain their deterministic values; the new
vegetation is generated after those assets. New tree shadows can change the
appearance of the ground in scene views. The approved earlier scene and its
manifest are preserved under `ReviewBeforeVegetation`.

Rebuild through `Art/road_ford_blender_preview.sh`, then import through
`Art/import_road_ford_style.sh` with Unreal closed. The importer checks the number
of trunk collision hulls. Final driving collision, wind animation, PCG setup,
Nanite foliage voxelisation and performance remain unverified/not configured.
The existing art-preview limitations for mud and water still apply.

Current validation: four saved model-review passes and a Blender scene check;
Unreal import completed with 26 meshes and 2,681 instances. Both trees imported
all four UCX hulls. Imported tree heights are about 8.82 m and 6.61 m. A manifest
comparison confirmed all 2,681 placements match the pre-iteration assembly.
Source meshes total 150,906 triangles before instancing, up from 97,760. This is
not a frame-time test. See [TREE_ITERATION_REVIEW.md](TREE_ITERATION_REVIEW.md).
