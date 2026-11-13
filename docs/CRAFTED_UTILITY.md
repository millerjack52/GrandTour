# Crafted Utility reference-led model

## Current floor repair — October 1, 2026

Latest model: `C:/GrandTour/Art/Export/VehicleTools/crafted-character-detailed-v06/Crafted_Utility_Detailed.blend`. The user found exposed seat bottoms beside the 1.2 m-wide floor. The two small floor rectangles are replaced with a continuous passenger/cargo pan reaching the sills, inset around rear wheelhouses, with formed sill returns and a front footwell upstand. The sloping rear boundary follows the existing tail return. All 765 other meshes and their transforms remain exactly as in the current saved v05.

`floor-before.json` records 1,030 uncovered samples in v05. The repaired pan covers all 4,205 compartment samples and all 1,120 seat-base projections, with no floor/tyre surface intersections. `saved-assembly-contracts.json` now checks six fit groups, including the previous five repairs. `saved-floor-preservation.json` checks the reopened result against the immediate source. Review `underside.png`, `underside-quarter.png`, `quarter.png` and `side.png` in the output folder.

Source tools: `fit_character_floor.py`, `floor_contracts.py`, `verify_floor_preservation.py`, plus the extended `assembly_contracts.py`. These are static, model-specific checks. An older verifier comparing against the original shape study also detects a 13.204 mm bonnet difference already present in the source v05; the same failure occurs before the floor repair. The current source and all its non-floor geometry are preserved rather than reverting existing work.

## Current assembly tidy pass — October 1, 2026

Latest model: `C:/GrandTour/Art/Export/VehicleTools/crafted-character-detailed-v05/Crafted_Utility_Detailed.blend`. The user liked the model but identified five assembly defects in detailed v03: rear pillar overhang, floating mudflaps, arch/body gaps, rear seats entering the wheelhouses and tyres narrower than the rims. All five are repaired in this separate revision. The original source is unchanged.

The lower rear cabin now follows the body taper; the full arch seating edge follows the actual panel and continues into the liner. Mudflaps have clamps and body hangers. The rear bench has 35 mm lateral wheelhouse clearance. Tyres are 270 mm wide around approximately 240 mm rim hardware, with at least 13 mm rubber margin on each side. Main panel shapes, bonnet, roof, wheel centres and tread diameter remain unchanged.

`assembly-before.json` detects all five failures in the source; `saved-assembly-contracts.json` passes all five groups after reopening the repaired model. `saved-assembly-checks.json` also passes 13 selected apertures and the static tyre/body and cockpit/glass scopes. `repair-preservation-checks.json` verifies 600 unaffected meshes and their world transforms unchanged. Of the initial 39 protected study meshes, 19 remain untouched; the arch/cabin repairs are explicit exceptions listed in `repair-manifest.json`.

Repair source: `Art/VehicleTools/tidy_character_assembly.py`, run against detailed v03 with a fresh output folder. Checks: `assembly_contracts.py`, `check_assembly_contracts.py`, `verify_dressed_character.py` and `verify_tidy_preservation.py`. Current copies and feedback screenshots are saved with the blend. Ten review images include low rear, pillar, arch, wheel and wheel-off views in addition to the normal overall views. Detailed v04 is a preserved intermediate attempt whose arch seating check failed.

Process lesson: separately authored components need tests for their shared boundaries, support paths, occupied volumes and axial/radial fit. Surface collision checks alone missed these defects. The car-modelling skill records this in `references/assembly-qa.md`. Checks remain static and scoped; another vehicle is still needed to test reproducibility.

## Initial accepted form and detail pass — October 1, 2026

The user liked the displayed side profile of `shape-character-v03` and requested details on that body before testing reproducibility on another car. Initial detailed static model: `Art/Export/VehicleTools/crafted-character-detailed-v03/Crafted_Utility_Detailed.blend`. It superseded the rejected model described in the historical sections below and is the source of the current tidy pass above.

The detail pass keeps 39 evaluated primary meshes unchanged: bonnet, roof, cabin/window geometry, arch lips and bumpers. It derives eight side skins from the actual accepted surface with 3 mm reveals, rather than reusing the rejected body's panels. Lamps, grille, rear lights, recessed handles, mirrors, glazing seals, wipers, cream stripe, low mouldings, twelve-vent steel wheels, tan cockpit and restrained underbody parts are fitted to that envelope. The rear lamps and fixtures follow the lower tail's inward taper.

Source: `Art/VehicleTools/dress_shape_character.py`; saved-file verifier: `Art/VehicleTools/verify_dressed_character.py`. Both are copied into the output folder. The builder opens the approved body and requires a new empty output folder. The original accepted source file remains unchanged. The historical form-control sliders are not linked to the detailed assembly; edit in a new revision and refit dependencies if changing its body.

`preservation-checks.json` records zero displacement on the 39 retained primary meshes and less than 0.001 mm distance from derived raw panel vertices to the accepted surface. `saved-assembly-checks.json` reopens the saved model and verifies that preservation, 13 selected real apertures, tyre/body surface intersections and cockpit/glass surface intersections. No intersections were found in those scopes. Seven native renders include side, front/rear quarters, front/rear, top and a rear-profile close-up. Initial review corrected the protruding headliner, hidden fog lamps and insufficient rear-lens housing depth without reshaping the body.

This is a static detailed authoring assembly. Operating rigs, UVs, LODs and engine export remain separate work. Reproducibility on another model has not been tested. The next vehicle must start with its own shape map and bare-body review.

## Historical rejected v05 assembly

Selected direction: A, Crafted Utility, from the user's three-style concept board. **The user has now rejected v05's overall shape.** Its technical checks do not establish shape quality. Preserve it as a component source. Continue with `docs/REFERENCE_SHAPE_FITTING.md` and the reference-fit workbench; do not add detail or treat v05 as the approved body.

## Files

- Model: `C:/GrandTour/Art/Export/VehicleTools/crafted-utility-v05/Crafted_Utility.blend`
- Native renders, comparison sheet, shape specification and check reports: the same folder.
- Build source: `C:/GrandTour/Art/VehicleTools/build_crafted_utility.py`
- Saved-file verifier: `C:/GrandTour/Art/VehicleTools/verify_crafted_utility.py`
- Review compositor: `C:/GrandTour/Art/VehicleTools/crafted_utility_review_board.py`
- Selected reference: `C:/GrandTour/Art/References/Vehicles/BoardDerived_2026-09-30/01-crafted-utility-views.png`, also packed in the blend.

The builder requires a new empty output directory and never opens or overwrites earlier vehicle files. Source helpers are copied with the delivery. Reference pixels are not measured orthographics; rear and top reference views are inferred designs.

## Construction

One envelope defines the side width, bonnet/scuttle heights, cabin taper, wheel centres and arch profiles. Four body panel regions per side are closed sheet meshes, separated by 4 mm nominal gaps with recessed dark jamb backing. Narrow painted arch lips and inner tubs share the aperture profile. Bonnet, roof, windows, tailgate, bumpers, mirrors, wheels and lights are separate collections. Door handles use real apertures and recessed pockets. The bonnet has a broad central plane, shoulder folds and a turned front edge. Glazing uses nested frame, gasket and pane profiles.

The prior wheel construction was reused at its supported dimensions, then uniformly scaled about new mounts. The wheel web was reauthored with twelve smaller through-vents. Existing detailed optics and cabin construction were adapted to new mounts. Adapted components use a new owner ID; old protected rebuild operators are not appropriate for these changed interfaces. The source and editable mesh collections are the authoring route for this revision. No general-purpose auto-fit guarantee is implied.

The first saved-file checks found wheel tub and mudflap intersections, and then a cargo-floor intersection. The final source moves the tubs inboard, moves mudflaps rearward, clips rear door-card edges above the shared arch, and divides the floor around the rear tyre envelope. The verifier checks those actual evaluated surfaces after reopening the saved file.

## Review and limits

`geometry-review.json` audits evaluated closed meshes. `saved-assembly-check.json` records the four wheel mounts, packed reference and static tyre surface checks against skins, lips, liners, mudflaps, floor and door cards. These checks do not certify all component contacts, solid containment, suspension or steering motion. Nominal radial clearance is 57 mm; it is not a minimum moving clearance measurement.

The final check reports 730 evaluated vehicle mesh objects, 133,364 evaluated vertices, no non-manifold objects, and no detected tyre/obstacle surface intersections in the stated scope. The four mounts and packed reference also passed the saved-file check. These counts describe the authoring assembly, not a runtime budget.

Review the side reference comparison, front/rear/top orthographic renders, colour three-quarter views, clay views and front detail. Silhouette, construction and game readiness are separate assessments. The roof/bonnet highlights and broad side surfaces remain artistic choices to review against the supplied board.

This delivery has no opening rig, UV/LOD pipeline, engine collision, Unreal import or gameplay validation. Earlier articulated prototypes and the user's original `Art/rangerover.blend` remain untouched.

## Rebuild

Run Blender 5.1 in background with `--python-exit-code 1 --python C:/GrandTour/Art/VehicleTools/build_crafted_utility.py -- --output NEW_EMPTY_FOLDER`. Omit `--draft` for the complete render set. Run `verify_crafted_utility.py -- --folder OUTPUT_FOLDER` in Blender after the build, then run the review compositor with ordinary Python and `--folder OUTPUT_FOLDER`.
