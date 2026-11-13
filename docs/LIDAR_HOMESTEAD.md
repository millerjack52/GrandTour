# HS4 - longer L-shaped wing and connected veranda steps

Owner correction (2026-10-21): the wing behind the garage is longer and the stairs must lead onto the veranda. The Blender source now extends that wing from 7.4 m to 10.3 m, with its front at local Y=-6.5 m. It projects 4.5 m beyond the main front wall, making a clear L-shaped footprint. Floor, roof, wall openings, foundation and simple collision extend together. The registered house anchor/yaw and detached garage placement remain those of HS3.

The stairs move to local X=1.45 m inside the L. A 1.8 m opening in the balustrade leads onto the same continuous deck slab, facing the glazed entrance. The veranda slab and planks terminate before the wing wall. A saved-map character-movement check now walks up the steps, through the opening, along the deck and back down without teleporting between waypoints.

The model is authored and saved in Blender: `Art/Export/LidarStudy/Homestead/RiversideHomestead.blend`, rebuilt by `Art/Blender/build_lidar_homestead.py`. House: 8,367 triangles and 17 simple hulls; garage: 2,702 and 9; graded court: 3,382 triangles. This adds 317 house triangles over HS3 with no new materials or actors. House datum is 5502.183 cm, set from the updated footprint survey. Garage datum remains 5234.119 cm. Guarded installation and the saved-map gameplay check both exited 0. All twelve garage swaps passed. The new walking check traversed seven waypoints up the stairs, along the deck and back down, with a 99.29 cm rise onto the deck and no falling/obstruction. Evidence: `Saved/LidarAuthoringQA/HS4/`; final views: `Art/Export/LidarStudy/Place/HS4_house_front.png` and `HS4_house_overview.png`. Underlying terrain digest and source DEM checksum are unchanged. No new FPS measurement was required for this geometry-only correction; HS3 timing remains evidence for that earlier revision. Owner visual/walking review remains the gate.

The owner reports inadequate steering at speed and explicitly reserves driving work for the next task. This house pass does not change driving code or tuning.

# HS3 - registered house placement and model cleanup

The owner's 2026-10-21 satellite screenshots correct the house footprint. The previous anchor lay near the garage, almost on the access-road endpoint. Placement now comes from `Art/References/Homestead/site-layout.json`, tied to the existing NZTM-aligned aerial: house anchor **(-51137.5, -26131.25) cm**, yaw **-65 degrees**, garage authored offset **(540, -1100) cm**. This moves the house 11.34 m, mostly east, and aligns the veranda northwest toward the court and river. The satellite registration and building dimensions remain image estimates.

The same transform drives the house, garage, graded lawn/court, interaction door, vehicle collection bay, recovery checkpoint and benchmark camera positions. Use the existing inspect -> Blender -> install -> check workflow below. The firm-road checker now derives its protected house/apron samples from this same placement instead of the old hard-coded coordinates. The new lawn/court replaces the previous mesh; this pass does not rebuild native terrain. The underlying ground digest remains `6AE1F9489CE5EC408044BFEC06A9FE25`, and the source DEM checksum is unchanged.

Roof surfaces now meet at trimmed intersections instead of overlapping complete roof slabs. The visible outer gables remain, with no internal gable through the junction. Weatherboard walls have recessed framed openings, clean lap edges and subtle colour variation; the exposed side undercroft is closed. Solar panels sit on the unobstructed wing roof. Vertex alpha controls surface roughness within the existing single opaque building material. No extra material slots, ticking actors or texture allocations were added.

House: **8,050 triangles / 17 simple hulls** (HS2: 8,108 / 15). Garage: **2,702 / 9**, unchanged. Graded lawn/court: **3,382 triangles** (HS2: 3,482), complex static collision. The new house datum is 5494.447 cm; garage floor 5234.119 cm. Both retain the existing reduced distance LODs. The focused installer removed 261 intersecting vegetation instances in the new footprint.

Saved-map visual checks passed and exited normally. The first gameplay run passed its assertions but returned an access violation after its shutdown log closed. The checker now releases its remaining editor/PIE object wrappers before teardown; the full repeat passed all assertions and exited 0. All twelve garage replacements preserved inventory, maintained one vehicle and settled on the new apron. Door interaction, occupied-bay refusal, boot-capacity refusal, duplicate selection refusal, entry, refusal while driving, and walk-away closure passed. A brief normal-input departure check travelled 14.18 m; this is not a road-driving acceptance test. Evidence: `Saved/LidarAuthoringQA/HS3/`, with final views `Art/Export/LidarStudy/Place/HS3_house_front.png`, `HS3_house_overview.png`, and `HS3_garage_menu.png`.

Original sources/exports are preserved in `Saved/LidarAuthoringBackups/HS3-source/`; the pre-install level is in `Saved/LidarAuthoringBackups/HS1-1792611552074800600/`. The owner's new references are archived unchanged in `Art/References/Homestead/Placement-*-2026-10-21.png`. No commits were made. Owner visual review and driving remain the final acceptance gate.

The relocated standalone performance capture (`hs3-relocated`) exited 0 and held 60.0 FPS at both house-arrival and garage-door views using the saved 1600x900 / TSR 75% capped preset. Frame p95: 16.680 / 16.671 ms; GPU mean: 8.637 / 7.705 ms, 840 measured frames per view. This covers these two stationary views, excludes loading/teleports/screenshots and is not whole-route or display-presentation timing. Metrics: `Art/Export/LidarStudy/Place/playperf-hs3-relocated-summary.json`.

## Historical HS2 implementation and evidence

### HS2 - riverside house and garage

The owner's four house/garage photos supplied on 2026-10-20 lead this reconstruction. Two ground views establish timber weatherboards, a raised covered veranda, front steps, intersecting iron roofs, flue, solar array and a lower charcoal corrugated garage. Two aerials establish the relationship to the clearing. Dimensions and unseen faces are inferred; this is an exterior reconstruction, not a surveyed architectural model.

## Placement and assets

- Existing surveyed anchor: (-52264.44549, -26256.74983) cm. Authored front is -Y; placement yaw 0 degrees with authored X reflected for Unreal's handedness. Owner correction: the veranda faces the river (-world Y), a 90-degree rotation from the first saved west-facing layout.
- Garage offset: (1060, -880) cm in the authored frame, on the right when viewed from the river. The front-right roller door is the interaction point; the other bay is open. Its slab is 6.56 x 6.48 m, with a roughly 2.84 m high roof. Door, player standing point and collection bay come from the exported layout so resizing does not leave the interaction behind.
- House: 8,108 triangles and 15 authored box hulls. Garage: 2,702 triangles and 9 hulls. Both have reduced distance LODs, opaque vertex-colour materials, modeled weatherboard laps and roof seams. HS2 separates the lower lean-to veranda from the silver main gable, uses a green roof on the perpendicular wing, adds timber foundation skirts and a partly solid deck balustrade, and uses lighter weathered timber.
- A 3,482-triangle static graded lawn/court uses a 1 m survey of the final LiDAR relief. The floor is set above the actual building footprint; the datum is 95.41 cm lower than HS1. A broader lawn slope replaces the raised yard shelf, and a gravel veneer follows the arrival court. Positive fill supports the house stairs, lower garage and level parking bay. This changes neither the landscape nor the native terrain digest. Overlapping canopy/understory is cleared within the foundations and arrival court. The House recovery checkpoint moves onto the new parking bay.
- Assets: `/Game/GrandTour/ArtTests/LidarStudy/Homestead`; placed directly in `L_LidarStudy`, folder `LiDAR/Homestead`.

## Garage

On foot, look at the closed garage roller door and hold E briefly. Scroll selects a vehicle; T collects it. Tab, E on the door, or walking away closes the menu. F still enters/exits cars. The walking HUD displays interaction prompts independently of the F1 driving-info toggle.

The editable garage roster contains the twelve existing drivable models: Range Rover Classic, BMW E39 Touring, Opel Kadett A, Suzuki SJ413, Ferrari 288, Graphic Adventure, Fiat Panda 1990, Toyota Prado, Toyota Land Cruiser 80, Nissan Pathfinder 2002, Subaru Impreza 2003 and Crafted Utility. Duplicate review/unfinished variants are not separate choices. Add future vehicles to the garage's `Vehicles` property and the installer's canonical roster.

Selection leaves the player on foot. The controller checks a conservative parking envelope, creates the replacement, verifies boot capacity, copies the exact inventory stacks and only then retires its former vehicle. Another car or the player in the bay blocks collection. A moving car, active winch or insufficient boot capacity refuses replacement. Failed selection retains the current car and inventory. The replacement starts parked with handbrake on and inherits the prior car's audio mute state. This is a fresh vehicle, not a transfer of damage, fitted parts or tuning.

The garage is a reusable, non-ticking station actor with an editable world-space vehicle spawn transform. It uses the existing station row/selection system. The LiDAR HUD renders that system on foot without adding the full convoy HUD.

## Rebuild

One Unreal at a time. Every runner calls `Art/wait_unreal_free.ps1` and holds the existing build/profiling mutex. Never kill an editor.

1. `Art/run_lidar_homestead.ps1 -Mode inspect` refreshes the final-relief ground survey.
2. Blender background: `Art/Blender/build_lidar_homestead.py` produces FBX, GLB, editable blend, manifest and layout. Optional `-- --preview` renders the combined architecture.
3. `Art/run_lidar_homestead.ps1 -Mode install` backs up the map, imports assets, places the buildings and door, clears intersecting vegetation and saves.
4. `Art/run_lidar_homestead.ps1 -Mode check` reloads the saved map and exercises the garage in PIE, including every vehicle and a blocked bay. Evidence: `Saved/LidarAuthoringQA/HS1/check.json` and `Art/Export/LidarStudy/Place/HS1_*.png`.

The main Place installer also calls the shared placement function once the homestead layout exists. After changing terrain under the homestead, refresh the survey and rebuild the graded mesh before reinstalling. The installer refuses a layout baked for another orientation, anchor or garage offset. Use the full `install` workflow for updates; the experimental asset-only import mode was removed after an editor shutdown fault, despite successfully saved assets. Ground-material version changes are applied independently of the FBX digest.

`Art/open_lidar_study.ps1 -Play -ShowFPS -House` starts a drive at the garage. The mesh manifest records expected imported vertex positions to catch FBX handedness regressions. The checker also verifies the vertex-colour material connection: Unreal's VertexColor RGB output is the unnamed output, not `RGB`.

## Original HS1 validation (before the visual correction)

Guarded C++ build succeeded. The final saved-map check passed all twelve roster replacements through the real station selection path, preserved three Wire items through every swap, kept exactly one car, refused occupied parking and an overloaded boot, rejected collection while driving, and verified entry and walking away to close the menu. Normal throttle input reached 0.6 and the replacement accelerated to 194.80 cm/s during the short PIE response check (41.09 cm travel); this is a functional response check, not a route drive or a performance measurement. Chaos's reported gear in that diagnostic is separate from the project's custom drivetrain gear.

The final terrain digest remains `DB443C52AD8AD4F3A1E2CD57E8E4716F`. House ground datum is 5354.7009 cm; garage/parking floor 5181.2742 cm. The apron has a vertex-painted lawn/gravel blend and its outer seam is buried to absorb sub-grid terrain curvature. Screenshots were inspected from the river-facing front and above, and at the garage menu. Installation and the final check exited cleanly. Owner visual/drive review remains the final gate. No commits were made.

The first standalone performance capture (`hs1-final`) is **contended, not acceptance evidence**: Skate.exe was running concurrently, accounting for about 72% of the GPU engine versus Unreal's 15% in a Windows counter sample. NVIDIA reported 99% total utilization, 88 C and active software thermal slowdown. No other application was closed. Do not compare that run to the prior FS1 clean captures or treat its label as a passed final benchmark. Any subsequent clean results are recorded separately in the Place stage log.

## HS2 visual correction and validation (2026-10-21 UTC)

The owner rejected the initial resemblance. This revision changes the building forms and their relationship to the slope, rather than relying on added texture detail. The separate low veranda roof leaves the main gable visible, the perpendicular wing has green roofing and a solar array, and timber skirts close the raised undercroft. The narrower garage moves 1.4 m inward and 1.2 m back. The building floor sits 18 cm above the highest sampled ground within its footprint; the datum is 5259.2928 cm and garage floor is 5186.0743 cm. The lawn slopes into a conforming gravel court. River-facing yaw remains 0 degrees, and the native ground digest is unchanged.

Final installation and the fresh saved-map check exited 0. All twelve garage replacements passed, including inventory preservation, blocked parking, overloaded-boot refusal, duplicate selection, refusal while driving, entry and walk-away closure. The normal throttle response check travelled 21.55 m and reached 1028.34 cm/s. Evidence is archived in `Saved/LidarAuthoringQA/HS2/`; the routine runner still writes to `HS1/`. Reviewed final map images are `Art/Export/LidarStudy/Place/HS2_house_front.png`, `HS2_house_overview.png` and `HS2_garage_menu.png`.

The initial survey and first install produced their reports but ended with an editor shutdown access violation. The inspection path now unloads to Entry before exit, and installation releases its editor-world reference before unloading. The subsequent inspection, final installation and functional check exited cleanly. Source and the former views were preserved in `Saved/LidarAuthoringBackups/HS2-source/`. No C++ changes or commits were made. Dimensions and hidden faces remain inferred from the owner's photos; owner visual and drive review remain the acceptance gate.

Clean standalone capture `hs2-clean` exited 0 with Skate closed: both house-arrival and garage-door views held 60.0 FPS at 1600x900, TSR 75%, using the saved capped preset. Frame p95 was 16.681 / 16.679 ms; GPU mean 8.281 / 7.702 ms, with 840 measured frames per view. The sampled GPU temperature was 68 C without software thermal slowdown. The result applies to these two stationary on-foot views, excludes loading/teleports/screenshots, and is not display-presentation or whole-route timing. Full metrics and CSV path are in `Art/Export/LidarStudy/Place/playperf-hs2-clean-summary.json` and the Place stage log.
