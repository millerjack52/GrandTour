# Rear quarters, split tailgate, lamps and bumper

Latest assembly: `Art/Export/VehicleTools/rear-body-workshop-v05/RangeRover_Rear_Body_Workshop.blend`.
Reusable library: `Rear_Body_Components.blend` in the same folder.

This milestone adds seven independent component collections: left/right rear quarters, left/right lamp cassettes, lower tailgate, glazed upper tailgate and rear step bumper. The assembly retains all 27 earlier workshop collections. The original user-authored `Art/rangerover.blend` is not modified.

## Construction

The quarter panels replace the original rear side skins and arch surfaces. Their front boundary stays 8 mm behind the rear-door edge. The complete returned wheel arch follows the existing faceted interface, so the completed rear doors remain unchanged. Upper quarter shaping uses restrained planar bands; the lower arch area stays calm. The right quarter includes a separate fuel flap, opening and seal. Formed corner posts close the joints between the cargo windows and the rear glazed frame.

The lower tailgate has a planar centre, four folded shoulders and actual sheet thickness. Both its registration recess and release-handle opening pass through the skin. The plate sits inside a cup; the handle has a bezel, pocket and grip returns. Hinge leaves follow the lower folded surface. The upper tailgate has a frame with mitred returns, metal reveal, rubber gasket, solid glass, wiper assembly, shaped roof hinges and a header seal.

Rear lights are removable cassettes inside real openings in the quarter-panel columns. Each includes a back shell, bezel, reflectors, three separate closed lenses, dividers and mounting screws. Optical ribs are geometry. A plain-lens variant uses the same cassette interface.

The bumper has a stepped carrier, wraparound ends, fitted tread pad and ribs, rubbing strip, reflectors, mounting arms and lower finisher. The tread pad seats on the carrier rather than floating above a sloped surface.

## Editing

Install `GrandTour_Rear_Body_Addon.zip`, or run the saved `START HERE - rear body workshop.py` text. The **GT Parts** sidebar exposes:

- **Tailgate crown:** 10–24 mm, selected lower-tailgate collection only. The perimeter remains fixed and the handle, lettering and hinge leaves follow the changed surface.
- **Rear lens:** ribbed or smooth, selected lamp collection only. The quarter-panel opening remains unchanged.

Use **Rebuild selected rear component** after setting a supported parameter. Regular source imports do not rebuild or clear scenes. Manual geometry, transform and relevant material edits cause regeneration to refuse. Preserve such edits as variants or migrate them into the generator deliberately; do not clear fingerprints to force replacement.

The `rr-rear-v1` interface is specific to this Range Rover study: metres, +X left, +Y rear, +Z up and the original assembly origin. It is not a universal vehicle fitter.

## Verification and review

Source is under `Art/VehicleTools/`:

- `rear_body_workshop.py`: builders and optional Blender sidebar.
- `build_rear_body_workshop.py`: opens the door/window assembly and writes an empty revision directory.
- `test_rear_body_workshop.py`: actual cutouts, planar tailgate faces, boundary preservation under crown changes, seated hinges/tread/header, real lens variants, deliberate gap/collision faults, manual-edit refusal, invalid input, staged-failure rollback and persistence.
- `verify_rear_body_assembly.py`: reopens the delivered assembly, verifies all 34 workshop collection fingerprints, checks the prior parts/body/roof for unintended surface intersections and registers the ZIP independently. Intended roof hinge/header contacts are listed separately.

The revision includes matched before/after rear and rear-face images, tailgate/lamp/quarter/fuel close-ups, clay, side/top/front views, a whole-car view and separated parts. Results are saved in `fit-report.json`, `tests.json` and `assembly-reopen-check.json`. Inspect Blender's output and reports: Python assertions can occur even when the Blender process exits with code zero.

## Limits

This remains a static exterior study. Hinge geometry is fitted, but there is no operating tailgate rig, checked opening sweep, gas strut, latch mechanism, defroster or complete cargo interior. Fixed roof mounts and seals must be separated from moving leaves when articulation is developed. Internal attachment contacts and retained wheelhouse-liner joins are outside the external-neighbour clearance claim. These checks do not establish weatherproofing, bumper load capacity, UVs, LODs, collision or game readiness.

The next useful milestone is the cockpit and visible interior: dashboard, controls, seats and door cards, reviewed from the driver's position as well as through the exterior glazing.
