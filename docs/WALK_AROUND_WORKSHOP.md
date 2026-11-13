# Walk-around workshop prototype

The Range Rover now has a native runtime workshop overlay using the approved orange/black title blocks and studio-board labels. The vehicle remains in the existing rally world. This is the interactive layout and customization slice; the illustrated hangar and equipment assets from the concept have not been built.

Launch `Play-Workshop.bat`, stop the Range Rover, and press **U**. Click Paint, Wheels, Tyres, Suspension or Equipment on the vehicle. Drag empty space to orbit, scroll to zoom, or use Tab to cycle parts and arrows to change options. Hold Space or the Compare button to see the fitted choice. Enter/Fit commits; Cancel/Escape discards a pending preview. Escape from the walk-around view, U, or Back to drive closes the workshop.

- Body and roof paint: original plus Highland green, Sandstone, Oxblood, Charcoal and Limestone. The roof follows the selected body colour. Original trim, interior, baked detail, damage and dirt are retained.
- Wheels: the Blender Pressed steel, Classic alloy and Heavy-duty steel models replace the drawn wheels on all four corners. Each rim and tyre remains independently selectable and follows its animated wheel bone, including steering, rotation and suspension travel.
- Tyres: Road, All-terrain and Mud use the three Blender tread meshes. Road retains Part.Tyre; Mud retains Part.TyreKnobbly and its existing handling. The new Part.TyreAllTerrain uses intermediate prototype tuning (1.05 grip, 1.10 rolling resistance). Preview changes geometry only; fitting changes the actual tyre slot.
- The rally lab permits test fitting without inventory changes or repairing tyre condition. Outside the lab, replacement tyres must be in the boot and the old set must fit back in it. The standard part-install path handles a real installation.
- Committed paint and rim model are saved to `Saved/SaveGames/GT_Workshop_RangeRover.sav`. Older finish-only saves map original/Limestone to Pressed steel, Graphite to Heavy-duty steel and Bright silver to Classic alloy. Mechanical parts use the existing loadout/run save, not this cosmetic profile. A lab tyre test fit lasts for that car instance.
- Preview changes materials and visible geometry only. Closing, cancelling, switching categories, losing compare focus, changing possession or destroying the vehicle restores/discards pending work. The session pauses physics and restores the previous camera, pause, HUD and input state when it closes.
- This first slice is enabled only for the Range Rover. Other vehicles keep their existing materials and cannot enter this workshop.

Implementation: `Source/GrandTour/UI/GTWorkshopComponent.*` owns the session and transactions. `SGTWorkshop.*` draws the responsive overlay and handles input. `GTBodyComponent` applies the isolated workshop materials and committed appearance. `GTPlayerController` owns entry and cleanup.

`Art/workshop.ps1 -Mode Setup` generates only `/Game/GrandTour/UI/Workshop` material variants, preserving the actual course tyre-coating graph. It backs up existing variants before editing. Source master materials and maps are not regenerated.

`Art/workshop.ps1 -Mode WheelSetup` imports the derived Blender FBXs from `Art/Export/WorkshopWheels-v01` into the isolated `UI/Workshop/Wheels` folder. Each mesh has UVs and four LODs. Runtime wheels have no collision and leave Chaos wheel size, mass and suspension unchanged. Separate rim/rubber materials receive each wheel's mud coat and vehicle wetness. The original skeletal wheel material section is hidden only after all six meshes load; wheel bones remain active. The source Blender library and car are preserved.

The initial Blender fit review found arch intersections at maximum compression with both the original and replacement tyre envelopes. The subsequent suspension pass below limits physical and drawn travel together to address those intersections.

The workshop inspection camera disables its own motion blur to avoid persistent temporal smearing when orbiting a paused world. The driving camera and graphics profile are unchanged.

`Art/workshop.ps1 -Mode Check` runs rendered PIE checks in the existing rally map. Evidence goes to `Saved/WorkshopQA`. It uses a separate QA cosmetic save slot and restores any pre-existing QA save. `-Mode Play` launches the normal driving window with the established graphics profile and Range Rover audio. All modes share the existing Unreal reservation.

Validation: editor build succeeded; 37 live PIE checks passed with a normal exit. Reviewed the rendered paint, comparison and tyre screens. The standalone 1600x900 window also passed direct mouse/keyboard checks for U entry/exit/re-entry, hotspot and option clicks, arrow navigation, cancel, orbit and wheel zoom. The test left the original fitted appearance unchanged. Evidence: Saved/WorkshopQA/check.json, manual-input.json and the PNGs. The automated screenshot window was desktop-clamped to 1280x720; standalone was also inspected at 1600x900.

2026-10-25: body paint now includes Roof panels. Updated the workshop description, rebuilt successfully, reran the 37 live checks, and visually verified the roof recolour in Saved/WorkshopQA/02-paint-preview.png. Existing fitted colours also apply to the roof when loaded.
The roof verification completed all 37 checks and produced the reviewed screenshots, but the editor process returned -1073741819 after logging shutdown and closing its log. No new Saved/Crashes report was produced. Treat this run as functional checks passed with an editor shutdown error, not a clean process exit.

2026-10-25 wheel integration: all six meshes imported with four LODs and expected centimetre bounds. Editor builds succeeded. The expanded live PIE suite passed 90 checks covering nine visual combinations, real Road/All-terrain/Mud fitting, compare/cancel, cosmetic reload, bone attachment and rotation relative to the chassis, collision disabled on cosmetic wheels, nonzero per-wheel mud/wetness, driving/steering on all three tyres, and exclusion of the BMW. The rally and LiDAR maps remain unchanged; tests use and restore the QA save slot. Reviewed the in-game alloy/mud views and corrected paused-camera blur. Final menu wording/swatches were corrected and rebuilt after that functional run.

Evidence: `Saved/WorkshopQA/wheelsetup.json`, `check.json`, and screenshots `04-wheel-preview.png`, `05-tyres-preview.png`, `06-orbit-other-side.png`, `07-mud-tyres.png`. The menu screenshot predates the final WHEEL DESIGN wording/swatch correction. Both asset setup and functional-check processes returned -1073741819 after logging normal editor shutdown; this remains an explicit process-exit limitation, despite successful asset and functional reports. The full-compression arch clipping identified in Blender is also retained and remains future suspension work.

## Suspension prototype

The fourth workshop category selects Standard (`Part.Suspension`), Touring (`Part.SuspensionHD`) or Trail (`Part.SuspensionTrail`). These affect the Range Rover's real spring rate, damping, droop and rollbar response. Other cars retain their authored behavior. Selection and comparison do not change physics; Fit changes the mechanical loadout. Return to driving for the suspension to settle. This version does not show a temporary stance preview while physics is paused.

| Kit | Spring rate (Chaos authoring units) | Damping ratio | Droop from reference hub | Rollbar factor |
|---|---:|---:|---:|---:|
| Standard | 340 | 0.62 | 16 cm | 1.00 |
| Touring | 410 | 0.72 | 18 cm | 1.10 |
| Trail | 360 | 0.68 | 21 cm | 0.85 |

Physical bump limits relative to the authored hub are 0 cm front and +2.5 cm rear. These are not travel measured from the settled ride height: Standard settles about 9 cm below its reference hubs. The existing speed-dependent firm-road compliance multiplies the selected kit's settings. Each vehicle owns its solver configuration; wheel class defaults and constraint allocation are unchanged. Animation uses the same per-kit limits, with the previous visual smoothing amount, so Trail can actually draw its full 21 cm droop.

`GTRangeRoverSuspension.h` holds the shared kit specifications. `GTSoilVehicleMovement` applies them to the existing suspension and constraints under the physics write lock. `GTWorkshopComponent` routes both tyres and suspension through the existing install/loadout transaction. The lab does not spend inventory or repair the car; outside the lab a replacement kit and room for the removed kit are required. Mechanical persistence remains in the existing loadout/run save.

The Blender hardware is a separate editable component study at `Art/Export/VehicleTools/rr-suspension-v05/GT_RangeRover_Suspension_Components.blend`, with a review scene and native renders alongside it. It contains three collections with separate coils, seats, mounting studs/nuts/washers, isolators, damper tubes, rods, gaiters, eye bushes and sleeves. UVs are present. **These meshes are not installed on the vehicle yet:** fitted mounts, underfloor integration and suspension hardware animation remain a subsequent art pass. The original car and wheel libraries are unchanged.

`scan_rr_suspension.py` encloses all three actual tyre models in a convex hull and checks it against the evaluated source body. The saved report in `Saved/WorkshopQA/suspension-clearance-scan.json` covers 10 mm vertical increments and 5-degree steering increments to +/-35 degrees, including the rear 25 mm bump limit. All revised-limit sampled poses clear; the old +120 mm bump control collides. This is discrete geometry evidence, not continuous collision certification or a full rough-terrain handling qualification.

`verify_rr_suspension.py` reopens the saved hardware library and checks topology/UVs, stud/seat and washer contact, and open sleeve bores. The earlier v03 assembly deliberately remains as a failing control for the stud gap and floating washers. `check_workshop.py` additionally tests live kit fitting, cancel/compare, actual ride height, acceleration/steering, per-vehicle isolation, loadout restore and full-droop animation.

Final suspension validation: build succeeded; all 126 rendered PIE checks passed and the final editor process exited 0. Touring measured about 3.30 cm above Standard and Trail 5.43 cm above Standard at the same reset location. The airborne Trail hubs reached 21 cm droop. Another Range Rover remained on Standard throughout fitting; the BMW retained its original suspension. All 706 revised-travel clearance samples passed; all 32 old full-bump control poses collided. The saved v05 component library passed 103 topology/attachment/UV checks. The original Range Rover source hash remains `d34a0c7797773c2e1d39b37454e8b3c9671b1a8424c0e0fa9233df044551158f`.

Evidence: `Saved/WorkshopQA/check.json`, `suspension-clearance-scan.json`, `08-suspension-menu.png`, `09-suspension-0.png` through `09-suspension-2.png`, and the v05 library's `verification.json` and `saved-assembly-check.json`. The first expanded run stopped on a QA fixture spawning on top of another vehicle; its report is preserved as `check-suspension-first.json`. The fixture was moved clear before the successful rerun. That earlier run again returned the previously observed shutdown error; the final clean exit does not establish its general cause or resolution. No broad rough-terrain endurance test or manual handling-feel approval is claimed.

## Bolt-on equipment

Equipment adds three independent visual accessories to the Range Rover: Roof rack, Bull bar and Snorkel. Selecting a row previews adding or removing that accessory; Enter/Apply commits. Hold Compare restores the fitted set temporarily. Cancel, changing category and closing discard an uncommitted toggle. All eight combinations are supported. The existing cosmetic save now stores an equipment bitmask; missing fields in old saves default to no accessories. Saving paint or rims preserves the equipment selection.

This is cosmetic customization. There is no cargo expansion, impact protection, functional recovery eye or increased wading depth, and the UI states that. Accessories follow the chassis and receive region dirt and vehicle wetness. They add no physics collision, change no mechanical loadout or inventory, and have no independent damage/detachment simulation. Other cars receive no equipment components. Existing suspension-hardware mounting work remains separate.

The approved visual basis is `Art/References/Vehicles/RangeRoverCustomization_2026-10-25_v01/03-bolt-on-equipment.png`. The editable Blender library and fitted review scene are in `Art/Export/VehicleTools/rr-equipment-v02`. Six rack feet follow sampled roof surfaces; the bull bar has bumper interfaces and recovery-eye detail; the snorkel has wing and pillar interfaces and an open louvred intake head. v02 repairs twisting found in v01's tube-frame close-ups. Source vehicle and wheel assets are preserved.

The native build report passes 139 topology/static-body checks. The reopened saved model passes 139 checks covering topology, 11 mounting contacts, pairwise accessory clearance, intake opening probes, 24 door poses and a 194-pose conservative tyre-envelope sweep. Intentional mounting overlap is distinguished from an air gap. These are sampled fit checks; they do not certify continuous motion or crash deformation.

`Art/VehicleTools/export_rr_equipment.py` writes UV-mapped, centimetre-scale FBXs with the car origin as pivot into `Art/Export/WorkshopEquipment-v01`. `Art/workshop.ps1 -Mode EquipmentSetup` imports only `/Game/GrandTour/UI/Workshop/Equipment`, backing up any existing owned assets, and creates four LODs and dirt/wetness materials. Source/imported bounds match within 1 mm. LOD0 triangle counts: rack 6,048; bar 3,936; snorkel 1,716. The existing workshop cook-directory rule includes these assets.

The equipment category uses a wider camera distance to keep the bull bar and basket in frame. The roof label sits above the selection ring. `check_workshop.py` exercises every subset, add/remove, compare/cancel, category switching, close/cancel, cosmetic reload, driving attachment, wetness response and exclusion of the BMW, alongside the existing tyre/suspension regression suite. The separate QA save is restored after the run; the user's cosmetic save is unchanged.

Final equipment validation: editor build succeeded, asset import succeeded with exit 0, and all **205 live PIE checks passed with final editor exit 0**. Reviewed the final equipment screen at `Saved/WorkshopQA/10-equipment-fitted.png`, including full bar/rack framing and the corrected roof-label spacing. The first 203-check run passed functionally but returned the intermittent -1073741819 shutdown error; its evidence is retained in `check-equipment-first.json`. The final clean exit does not claim to resolve that intermittent editor issue. Final reports: `equipmentsetup.json`, `check.json`, `equipment-integration.json`. The user's cosmetic save, source Blender car, rally map and LiDAR map were preserved.

## Drivetrain packages

The sixth workshop category adds Standard, Rally and Expedition drivetrain packages for the Range Rover. These use the existing engine slot and mechanical loadout save. Preview remains descriptive; fitting changes the actual torque curve response, gearing, shift timing and differential coupling when driving resumes. Tyres, suspension and equipment are separate choices. See [Range Rover drivetrain prototype](RANGE_ROVER_DRIVETRAIN.md) for controls, tuning values, persistence and validation.
