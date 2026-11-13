# Range Rover learning prototype: movement inspection

Latest revision: `C:/GrandTour/Art/Export/VehicleTools/articulation-workshop-v03/`.

The user explicitly finds the overall shape off, while considering the details a substantial improvement. This model is retained for learning and eventual import. Neither its proportions nor its silhouette should become the approved template for later vehicles.

## Open and use

- `RangeRover_Articulation_Workshop.blend`: neutral assembly with manual controls and no active animation.
- `RangeRover_Movement_Demo.blend`: separate 180-frame playback demonstration at 24 fps. Doors open and close over frames 1–80; steering and wheel rotation run over 80–160; the final segment holds neutral steering with one wheel revolution completed. Motion is in place.
- `GrandTour_Articulation_Addon.zip`: optional **GT Parts → Prototype Movement** sidebar. Alternatively run the saved Blender text `START HERE - movement controls.py`.

The rig's normal Blender drivers work without the add-on. Select **GT | inspection controls** and edit its Object Custom Properties directly, or use the sidebar. Use the manual assembly for live adjustments: the demo's keyed properties are controlled by its timeline.

| Control | Meaning |
| --- | --- |
| Left/right front door | 0–70 degrees, each independently |
| Left/right rear door | 0–65 degrees, each independently |
| Steer | −30 to +30 degrees of equivalent centre steering; positive turns toward vehicle left |
| Roll | Degrees of wheel rotation, positive for forward rolling; UI range ±720 |

The sidebar also provides neutral, all-doors-open and left/right steering poses. Driver expressions clamp door/steering inputs at their limits. The steering-wheel ratio is fixed at 15:1. Front steering uses an Ackermann relationship based on 2.63 m wheelbase and 1.56 m track; the inner front wheel turns more sharply. All road wheels roll about their own axle after the front steering transform. The steering column shroud, stalks and pedals remain stationary.

Each door moves its exterior pressing, glazing cassette and interior card together. Each front door also carries its mirror. Hinge axes are located on the front edge of each door, at X ±0.930 m and Y −0.770/0.230 m. These are inspection pivots; detailed hinges, latches and physical constraints are not built.

## Corrections revealed by movement

The first sweep found contacts that earlier static tests did not cover. The final derivative records these migrations in `build-report.json` and the object's `articulation_fit_change` property:

- Inset the dashboard end zones and their vents to X ±0.750 m to clear front door trim.
- Move fixed jamb backing inward 55 mm to clear door returns.
- Shorten front window drip lips by 45 mm at the windscreen end.
- Add 6 mm at the rear door window's trailing clearance, keeping its glazing layers fitted together. The first degree of opening had clipped the cargo-window surround.
- Move the inner front wheelhouse plane from X ±0.570 to ±0.400 m, with its liner following it. The visible fender arch is unchanged.
- Narrow the retained placeholder underbody from 1.2 to 0.8 m for steering clearance.

Seven workshop collections receive geometry corrections; 39 preserve their original mesh/material/modifier/local-transform fingerprints. The underbody and six jamb backings are retained base-scene objects outside those collections. Rig attachment itself preserves all corrected component content and neutral world transforms. The original cockpit-v04 and `Art/rangerover.blend` remain separate.

## Authoring versus articulation

Author geometry in the static component workflow. The movement file is a derived assembly. Added `RIG GUARD` manifest objects make older static component rebuilders refuse replacement even at the neutral pose, because those rebuilders would otherwise discard the motion hierarchy. Do not delete guards or reset fingerprints to force a rebuild. Migrate an intentional geometry change through the builder and rerun the movement checks.

The builder verifies the original 46 source fingerprints before applying the explicit fit migration. Running it into a nonempty output directory or attempting to create a second rig in the same scene is refused. Existing variants are preserved.

## Verification

`kinematic-tests.json` contains 18 passing checks, including real vertex movement, reflected left/right wheels, fixed centres, linked steering, grouped door movement, neutral restoration, driver clamps, old-builder guards, duplicate-rig refusal and registration from the packaged ZIP. `demo-reopen-check.json` verifies a 60-degree door pose and 90-degree wheel roll after reopening the saved animated copy.

`sweep-report.json` records 249 sampled pose checks:

- 94 individual door poses: 0.5-degree steps over the first five degrees, then five-degree steps to the stated limit.
- 72 adjacent-door combinations: 36 front/rear angle pairs per side, including maximum opening.
- 52 road-wheel poses: 13 steering inputs from −30 to +30 degrees, with four tread phases at each input.
- 31 cabin steering-wheel poses over −450 to +450 degrees of wheel rotation.

No unexpected surface intersections were detected in those samples. The steering hub's designed contact with its column shaft is listed separately at all 31 cabin-wheel poses. This is triangle surface testing, not a proof of continuous clearance, containment, a minimum air gap or every simultaneous door/steering configuration. No suspension travel is included.

Native review renders show the neutral assembly, open doors from front/rear/top, a turned front wheel, steering from above and the linked cabin steering wheel. The source scripts alongside this guide's revision are `articulation_workshop.py`, `fit_articulation_interfaces.py`, `build_articulation_workshop.py`, `check_articulation_workshop.py` and `review_articulation_workshop.py`.

## Import boundary

This is a Blender inspection rig using parented objects and drivers. It is not yet an Unreal skeletal vehicle, physics asset or validated export. Suspension, drivetrain, deforming tyres, differential wheel speeds, UV/LOD work and simplified collision remain separate. The next import experiment should establish scale, axes, pivots, material/glass transfer and part grouping before adding more detail or adopting the shape for a new vehicle.
