# Bonnet and bumper workshop

September 30, 2026. Third component milestone, continuing from the lamp/grille and wheel/fender workshops.

## Result and use

Review folder: `Art/Export/VehicleTools/bonnet-bumper-workshop-v04/`. Earlier folders are iteration history; v03 is an interrupted intermediate render, not a delivery.

- `RangeRover_Bonnet_Bumper_Workshop.blend`: assembled exterior study.
- `Bonnet_Bumper_Components.blend`: appendable bonnet, bumper carrier and left/right insert collections.
- `GrandTour_Bonnet_Bumper_Addon.zip`: self-contained add-on with its construction helper.
- `01-before-front.png` / `03-after-front.png` and `02-before-whole.png` / `04-after-whole.png`: matched comparisons.
- Top, side, bumper closeup, clay and separated-component renders provide additional inspection views.

Install and enable the ZIP, or run `START HERE - bonnet bumper workshop.py` in the blend to load the local project module. This adds a **Bonnet and Bumper Workshop** section to **GT Parts**. No code autoruns when the blend opens.

Select a bonnet mesh and use crown/plateau controls to change the broad forms. The fixed perimeter stays at the original fender/scuttle interface. Select a left or right bumper insert and choose vent or blank to replace that insert alone. Manual mesh/material/transform changes block procedural regeneration; keep those edits as a manual variant.

## Geometry and interfaces

The bonnet is a closed 4 mm authoring skin with a raised central plateau, broad side folds, a level leading edge, underside edge returns and a latch mounting pad fitted to its local slope. It uses the original width-taper station at Y=-1.84 rather than interpolating across that change. The nominal side reveal is 4 mm and rear reveal is 6 mm. The skin sits 6 mm above the fender guide at its side boundary.

The bumper uses a stepped carrier, a top return fitted near the existing nose, separate moulded corner caps, a rubbing strip, recessed registration mount, lower inlets, mounting arms and a folded lower guard with actual slots. Two short mounting tabs join that guard to the carrier underside. Left and right insert frames fit real carrier apertures. Vented and blank variants share that interface.

The geometry uses the current Range Rover study's origin and dimensions: metres, front -Y, up Z. Bonnet crown supports .030–.070 m and plateau .55–.70 of half width. This is a prototype range for this interface, not an automatic fitter for unrelated vehicles. The bumper is a visual assembly, not a certified crash or recovery structure.

## Review and checks

The first render exposed a horizontal underside pad poking through the sloped bonnet. The revised pad follows the underside at each corner. The bonnet's leading edge now stays level across its width; changes to the crown are concentrated inside that boundary. The bumper's top return was also extended toward the nose to reduce an excessive recess behind its upper edge.

Independent checks cover closed bonnet topology, a level leading edge, the fitted underside pad, guard-tab contact with both adjoining pieces, actual crown changes without boundary movement, unchanged neighbouring parts, a real blank insert swap, insert/carrier fit, deliberately introduced collision and seam errors, preserved manual edits, unsupported parameter refusal, sidebar registration and save/reopen. See `Art/Export/VehicleTools/bonnet-bumper-tests-v03/tests.json`.

The build compares all eleven earlier wheel/fender/light component fingerprints to the source assembly. Static neighbouring-surface checks and packaged add-on verification are recorded separately in `assembly-reopen-check.json`. Chassis mounting arms are deliberate interfaces. Bonnet hinges, latch operation, wiper sweep, deformation, UVs, LODs and engine export remain outside this study.

Sources live in `Art/VehicleTools/`: `bonnet_bumper_workshop.py`, `build_bonnet_bumper_workshop.py`, `test_bonnet_bumper_workshop.py` and `verify_bonnet_bumper_assembly.py`. The original user model and prior review revisions are preserved.
