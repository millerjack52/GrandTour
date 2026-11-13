# Benmore road-edge detail

This pass adds irregular roadside detail to `L_Benmore_Drive`: 31,736 gravel chips, 3,675 larger stones, 13,034 fine-grass clumps, 2,581 straw tussocks and 1,078 weathered tussocks. These are seven instanced mesh groups spread along both existing roads, with deliberate gaps and density variation rather than continuous hedges.

The small stone meshes are the existing GravelRoad assets, with a map-owned matte grey material override and per-instance colour variation; grass uses the approved TussockStyle meshes and original materials. Chips are roughly 5–12 cm across and the larger stones 13–30 cm, partly buried. The stones retain their authored flattened shape, with enough height above the soil to read from the road. Dense centreline samples exclude placements from all road running surfaces, including intersections. Plants are set farther back according to size; a few outer blades can overhang the loose shoulder. Wet ground and steep slopes are excluded.

The map-owned landscape shader adds broken patches of dry exposed soil, gravel spill and grass litter across the shoulder. Surface normals extend into the loose verge, while the enlarged 8 m gravel repeat and existing road POM are retained. Terrain heights and road collision remain unchanged.

All added instances are non-colliding, without dynamic shadows, and use distance culling ranges of 65–110 m for stones and 100–180 m for grass. The actor `Benmore_RoadVergeDetail` contains only this pass's additions. Rebuilding it preserves existing trees, rocks, grass streaming, road aggregate and other actors.

Rebuild with `Art/tools/prepare_benmore_verges.py`, then `Art/Unreal/setup_benmore_verges.py`. Inspect the saved result with `Art/Unreal/check_benmore_verges.py`. Outputs are under `Art/Export/BenmoreVerges`. `ReferenceSurface/M_Benmore_BeforeVergeDetail` retains the previous ground material.

This pass is surface dressing. The subsequent [physical verge relief pass](BENMORE_VERGE_RELIEF.md) adds banks and drainage hollows and re-seats this dressing. Editor tick diagnostics from the automated capture session are not a performance benchmark.

Saved-map validation on 2026-10-07 passed: all 52,104 added verge instances reloaded across seven mesh groups with NoCollision, the existing 5,704 road-gravel instances remained, and all four landscape tussock variants streamed near the terrace, hillside and shoulder cameras. The final reload logged no material compilation errors. Those three captures were visually reviewed; the small stone meshes retain their faceted source geometry.
