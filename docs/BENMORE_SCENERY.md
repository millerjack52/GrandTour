# Benmore scenery pass

The playable `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_Drive` map gains four small willow groups and scattered rock clusters. Placements are art-directed, not a survey of existing vegetation or geology. The original terrain, driving routes and TussockStyle ground cover remain in place.

The 27 willows use the accepted Blender family from `Art/Export/WillowFamily/willow-family-01`: Young, Broad, Windswept and Weathered. These are imported into the map-owned `Scenery` folder, with the painted bark, two branch UV charts, fork blend colours, original leaf palette, four generated distance LODs and three lower-trunk collision hulls per tree. Leaves have no collision. This first integration has static foliage; wind and a dedicated distance-canopy optimization remain future work.

Three groups follow the low western lakeside ground; another marks the western terrace-loop bend. The existing lake-height shading is still only a cue, not a finished water surface.

The mature willow instances have been enlarged to approximately 12–17 m, while young trees remain about 6–7 m tall. The underlying approved library meshes retain their original dimensions; instance scale establishes the mature landscape proportions. Canopy bounds are checked again against road margins.

The 201 rocks use copies of three Meadow Environment rock meshes. They sit in clusters around terrace edges and hillside breaks, with collision and terrain burial. Map-owned material instances remove the bright green top layer and use a neutral grey stone tint. Their source assets are preserved. Scenery placement rejects the road corridors and checks asset bounds against road clearance. Trees and rocks are individually labelled `Benmore_Scenery_*` for inspection and selective editing.

The pre-pass level is preserved as `/Game/GrandTour/Demo/BenmoreRoads/L_Benmore_BeforeScenery`. Re-running setup replaces only this pass's labelled scenery actors and its owned assets; edits to those actors should be captured in the placement source first.

## Build and verification

1. `Art/Blender/export_benmore_willows.py` exports the approved family to FBX without changing the source Blender scenes.
2. `Art/tools/prepare_benmore_scenery.py` writes seeded placement data using the current driving height grid and road manifest.
3. `Art/Unreal/setup_benmore_scenery.py` imports, validates scale and collision, places scenery and saves the driving map.
4. `Art/Unreal/check_benmore_scenery.py` reloads the saved map, verifies tree and rock counts, checks tree LODs and trunk hulls, traces the road corridors for new obstructions and captures roadside, shoreline and hillside views.

Outputs live in `Art/Export/BenmoreScenery`. Require `ok: true` in both setup and validation reports. Runtime frame intervals are local editor observations, not shipping performance certification. Terrain source attribution remains in `BENMORE_FULL_SITE.md`.

`refine_benmore_scenery.py` applies the latest instance scales and dry rock materials without reimporting meshes. The shared rock-material setup is in `benmore_rock_materials.py`.

Final saved-map checks passed with 27 trees and 201 rocks, verified updated tree scales, four LODs and three trunk hulls for each variant, and 552 road-corridor traces with no scenery hits. Roadside, shoreline and hillside captures were visually inspected after the scale and rock-colour refinement.
