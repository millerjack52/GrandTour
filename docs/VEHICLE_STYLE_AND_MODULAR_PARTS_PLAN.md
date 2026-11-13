# Vehicle style reset and fitted-parts tool proposal

## Impreza reproduction case — October 1, 2026

Latest review: after rejecting the v11 Blender model as "an ugly mess", the user approved the four-view sheet and enlarged side profile in `Art/References/Vehicles/Impreza2003/orthographic-reset-v01/` with "Good. Go". A new static assembly is saved at `Art/Export/VehicleTools/impreza-ortho-full-v08/Impreza_Orthographic_Rebuild.blend`. It uses traced image controls for the body, glazing, arches and curved door seams; the old body is not reused. The final presentation preserves the verified v07 geometry. Twelve scoped static checks pass, including 900 floor rays, tyre/rim fit, wheelhouse clearance, fitted mudflap and wing mounts, graphics and guards. The new checks detect the graphic and skid-plate failures in full-v01. Packed references, source scripts, an aligned side comparison and all review views accompany the model. Mesh approval remains pending; previous animation tests do not carry over to this static rebuild.

The user chose the 2003 blobeye sedan and approved `Art/References/Vehicles/Impreza2003/concepts-v03/02-gravel-club-refined.png`. Earlier Impreza concepts were rejected first as too realistic, then too faceted. The accepted direction uses coherent broad surfaces, selective rounded transitions, simplified materials and chunky rally equipment.

Rejected historical delivery: `Art/Export/VehicleTools/impreza-gravel-full-v11/Impreza_Gravel.blend`. It contains independently editable body, cabin, wheels, rally equipment and fitted interior, plus four opening doors, Ackermann steering, rolling wheels and linked cabin steering. The approved image is packed into the blend. Its shape specification explicitly uses artistic, perspective-inferred dimensions. Saved-file validation passes 14 assembly/kinematic checks, 900 seat-base floor rays and 166 sampled movement poses with zero unexpected contacts. Review views include underside and cockpit cutaway. User approval of the concept does not establish approval of this mesh. No game export, suspension or physics certification is implied.

The user requested two user-facing stages for future vehicles: reference approval, then build and internally repair/review before delivery. The car modelling skill's Impreza reference records the current builders, corrections and limits; retained earlier output revisions preserve failing evidence.

## Pathfinder reproduction case — October 1, 2026

Latest authorized stage is articulation: `Art/Export/VehicleTools/pathfinder-articulation-v08/Pathfinder_Articulation.blend`, with a separate `Pathfinder_Movement_Demo.blend`. Four door groups, Ackermann steering, wheel roll and linked cabin steering are controlled by `GT | Pathfinder controls`. The continuous source panels required explicit separation and fitted edge/liner/footwell repairs; source cockpit v03 remains untouched. The final reopened sweep passes 192 sampled poses with zero unexpected contacts, including quarter-degree door increments near closure. Earlier failures and the exact migrated meshes are retained in reports. Hidden hinge fixtures are inspection aids, not Pathfinder exterior styling. No suspension, physics or engine-export certification is included. The modelling skill's Pathfinder reference records the current builders, checks and lessons.

Current cockpit continuation: `Art/Export/VehicleTools/pathfinder-cockpit-v03/Pathfinder_Cockpit.blend`. The user authorized moving on from bonnet/wheel v05. New components include fitted seats and mounts, instruments/controls, console, door cards, lining, cargo deck and roof crossbars; transmissive glazing exposes the interior. Existing raw exterior geometry is preserved. The independent saved-file checker covers occupied wheelhouse volumes as well as collisions, floor coverage under seats and real mount contact. Cutaway review prompted closing the instrument housing back and replacing round belt placeholders with flat webbing. The interior is an artistic interpretation, with static fit checks; articulation and game export remain pending. See the car-modelling skill's Pathfinder reference for current scripts and limits.

Latest continuation: the user disliked the bonnet in exterior v04. `Art/Export/VehicleTools/pathfinder-bonnet-wheels-v05/Pathfinder_Bonnet_Wheels.blend` refines the crown, shoulder folds and fitted wing seams, and adds dished alloys, hardware and attached tyre tread. It retains the cabin, stance and unrelated raw meshes. Whole-edge bonnet checks supplement previous static assembly tests. The close-up review exposed overlapping Solidify edge caps despite sub-millimetre interface fit; the revised sheet rim settings and normals remove that artifact. Builder and saved-file verifier are `refine_pathfinder_bonnet_wheels.py` and `verify_pathfinder_bonnet_wheels.py`. The original blend is preserved. This is a new visual review candidate, not user-approved final geometry or game-ready output. Continue with cockpit/fittings after review.

The user subsequently called the corrected target-led shape "Much better" and authorized continuing while following the process and fixing mistakes. The exterior continuation is `Art/Export/VehicleTools/pathfinder-exterior-v04/Pathfinder_Exterior.blend`, built by `dress_pathfinder_exterior.py`. It preserves the corrected bonnet, cabin, window and wheel geometry while adding fitted optics, grille, inserts, wipers and trim. Interface checks prompted repairs to folded fascia rows, tyre-intersecting bumper returns, flare seating and the floor-to-sill slit. The scoped validator is `verify_pathfinder_exterior.py`; older failing reports remain in v01/v02. Wheels/tyres, cockpit, rig and export are still pending. Preserve manual edits if refining this exterior file rather than regenerating blindly from its earlier seed.

After seeing the orthographics, the user rejected the shape explicitly: "it is way off. I thought we had sorted this". Audit found that the shape map made photographs primary, and the constructor hard-coded photo registration plus factory overhang correction rather than following the approved artistic target. Correction candidate: `Art/Export/VehicleTools/pathfinder-approved-target-v03/Pathfinder_2002_Shape.blend`, with matched review in `pathfinder-target-review-v03/`. `approved-target-shape-spec.json` records the approved image, traced regions and one uniform registration; `build_pathfinder_target_shape.py` consumes those controls. Primary forms and window negative spaces were revised; detail and whole-assembly certification remain deferred. This candidate has no user shape approval. The car-modelling skill now records the authority mismatch and the need to check actual control provenance, not just written intent.

Latest user review: the Pathfinder shape is **not there yet**. They requested orthographic pictures for refinement. `Art/Export/VehicleTools/pathfinder-2002-orthographic-v01/` contains native Blender side/front/rear/top renders at 300 pixels per metre, neutral materials, 0.5 m grids and axle/centreline guides. `side-comparison.jpg` aligns the approved generated style image by estimated wheel centres using uniform scale only; the target retains perspective and is not a measured blueprint. Original v03 file SHA-256 and mesh/curve geometry were verified unchanged. `Pathfinder_Orthographic_Review.blend` is a presentation copy, not a shape correction. Initial review priorities are bonnet/nose transition, cargo-window and rear-pillar rake, side section shaping and bumper wrap. Keep detail work deferred until form refinement.

The user accepted Crafted Utility v06 and requested a 2002 Nissan Pathfinder to test the method on a different car. They approved two generated style sheets before authorizing geometry. First native form study: `Art/Export/VehicleTools/pathfinder-2002-shape-v03/Pathfinder_2002_Shape.blend`. Real 2002 SE photos and generated style targets are saved under `Art/References/Vehicles/Pathfinder2002/`, with an observation map and explicit uncertainty notes.

The independent R50 body has its own bonnet roll, windscreen rake, cargo glazing, high rear handles, broad flares and wrapped tail. It reuses the observation and fitting method rather than the Range Rover mesh or its fixed dimensions. Its saved-file report passes static floor coverage, wheel envelope/rim fit, tyre clearance, flare seating and screen/roof joins. v02's eight uncovered floor samples were corrected by deriving exact wheelhouse transition rows.

This is a shape review, not a finished vehicle: lamps, wheels and cabin materials are proxies. Cockpit, detailed optics/tyres, rig and export are pending. The 3D shape has not yet been accepted by the user, and a completed second detailed vehicle is still needed to assess reproducibility. Continue with the car-modelling skill's `references/pathfinder-shape.md`.

## Latest accepted direction — October 1, 2026

Latest follow-up: `Art/Export/VehicleTools/crafted-character-detailed-v06/Crafted_Utility_Detailed.blend` replaces the undersized floor in v05. Floor coverage and underside review are now a sixth assembly check; see `docs/CRAFTED_UTILITY.md`. This change preserves all other current source geometry.

After seeing `shape-character-v03/side.png`, the user said the shape looked great and requested the detail pass on that body. Latest static detailed assembly: `Art/Export/VehicleTools/crafted-character-detailed-v05/Crafted_Utility_Detailed.blend`. This repairs five user-reported fitting defects in detailed v03: rear pillar/body join, mudflap attachment, arch joins, rear bench/wheelhouse clearance and tyre/rim width. The same five added checks fail the previous file and pass the saved repair. Preserve the accepted main form, keep detail mounts specific to it, and follow `docs/CRAFTED_UTILITY.md` for current delivery/checks. The prior `crafted-utility-v05` body rejection below concerns a different, older model. The user wants to test reproducibility on a different vehicle after this detail pass; that test has not yet occurred.

## Current user feedback after cockpit work

The user says the current model's shape is off, while its details are a big improvement. Continue with it as a learning prototype for eventual import. This does not approve its silhouette or proportions. Reuse demonstrated component construction and validation methods; establish a fresh shape target before using the prototype to generate future cars. The movement derivative and its measured fit corrections are documented in `docs/ARTICULATION_WORKSHOP.md`.

## Latest reference direction: user board

**Latest feedback:** the user rejected Crafted Utility v05's overall shape too and asked for a better way to get it right. The corrective method and diagnostic workbench are in `docs/REFERENCE_SHAPE_FITTING.md` and `Art/Export/VehicleTools/reference-fit-v01/`. Original A remains the primary target; generated orthographic-style views are secondary guides. No prior mesh/clearance pass overrides this shape rejection.

The user explicitly rejected the shape-reset-v03 Blender A/B studies and supplied the A Crafted Utility / B Graphic Adventure / C Chunky Expedition concept board, asking for references derived from it. Do not continue those rejected shape studies or substitute the red short off-roader. The user then selected **A, Crafted Utility**, and asked to build it. This selects the style; it does not automatically approve the resulting 3D model.

The new static assembly is `Art/Export/VehicleTools/crafted-utility-v05/Crafted_Utility.blend`. It uses a new shared envelope traced proportionally from the selected Crafted Utility sheet: long four-door body, 2.64 m artistic wheelbase, 0.81 m tyres, narrow rolled arches, slim bumpers, formed clamshell bonnet and tapered cabin. These numbers are authoring choices, not factory measurements. Separate panel and detail collections remain editable. See `docs/CRAFTED_UTILITY.md` for source, review images, construction checks and limits. Preserve the older detailed articulated prototype for its learning/import purpose; do not apply its rebuild operators or rig directly to these new interfaces.

`Art/References/Vehicles/BoardDerived_2026-09-30/` preserves the supplied board and three generated reference sheets, one per style. Each shows the plain base vehicle in side, front, rear, top and front three-quarter views, so equipment does not obscure the silhouette. `prompts.json` records the exact built-in image-generation prompts and review limitations. Rear/top views are inferred and cross-view discrepancies must be resolved into a single coherent Blender envelope. These are visual modelling references, not measured blueprints or approved geometry.

## Rejected shape correction studies (preserved for comparison)

The user subsequently asked to bring the overall shape closer to the references. Shape work now takes priority over the next import step. `Art/Export/VehicleTools/shape-reset-v03/` contains two separate, unapproved Blender proposals and matched clay comparisons against the cockpit prototype:

- **A, compact four-door:** retains the four-door/cargo-window arrangement, with a higher bonnet and body, stronger arch shoulders, less glazing rake and larger wheels relative to length. Wheelbase 2.47 m, tyre diameter 0.90 m, roof datum 1.98 m.
- **B, short expedition:** explores the more compact character of the red off-roader reference using a two-door side layout. Wheelbase 2.18 m, tyre diameter 0.94 m, roof datum 2.02 m.

The source prototype has a 2.63 m wheelbase, 0.76 m tyre diameter and 1.79 m roof datum. These proposed dimensions are artistic choices, not dimensions measured from the perspective references. Both studies were subsequently rejected; the supplied three-style board above now takes precedence.

`Shape_Study_A.blend` and `Shape_Study_B.blend` contain editable new meshes with the selected study visible and the old comparison geometry hidden. `shape-comparison.png` lays out native Blender three-quarter, side and front renders at matched camera/scale/material settings within each row. Colour images are supplementary. The new body is a connected folded shell with actual arch apertures, formed arch shoulders, tapered cabin and recessed glazing; wheel meshes are uniformly resized from the demonstrated component.

These studies establish proportions only. They do not carry the detailed fitted cockpit, production panel separations, functional rig or prior clearance certification. The detailed learning prototype remains preserved. Resolve the primary silhouette before transferring and refitting its detailed components; do not simply stretch the complete articulated car to match a new outline.

September 30, 2026. The user's latest feedback supersedes the earlier provisional acceptance of the simple wagon, Land Cruiser and Range Rover studies: those cars lack detail and visual interest, and a stronger shared style is needed. The requested next step is concept imagery and a plan for separately modelled parts that fit together. No new model or tool implementation is delivered in this pass. Existing work remains preserved.

## New art references and proposals

Workspace: `Art/References/Vehicles/StyleReset_2026-09-30/`.

- `user-reference-01-rally.png`: authored fender volumes, layered lamp housings, tyre/rim depth, confident graphic design and visible component layering. Its race aero and sponsor graphics are not default requirements for every Grand Tour car.
- `user-reference-02-expedition.png`: exaggerated but coherent cabin/wheel proportions, legible silhouettes, stance and practical accessory groupings that read against a painterly landscape.
- `user-reference-03-collection.png`: model-specific body shapes, deliberate chamfers, distinct accessory silhouettes and clear material separation. Detail is concentrated where it explains a component.
- `01-style-directions.png`: A crafted utility, B graphic adventure, C chunky expedition, compared on a common SUV with base and equipped versions.
- `02-detail-target.png`: proposed B direction, with a plain base vehicle and closeups of wheel/arch, lamp/grille/bonnet, and door/glass/mirror.
- `03-modular-parts-concept.png`: illustrative assembled/separated front corner and clay/colour junction comparison.

All three new boards were produced with the built-in image generator. Exact prompts, input roles and caption correction are in `final-prompt-set.json`. The second board's draft was corrected to remove an unsupported game-readiness phrase. These images are art proposals, not measured orthographics, exact mechanical designs or proof of geometry fit. Small inconsistencies between views and invented mounting details must be resolved in Blender.

Recommendation: B, graphic adventure. Keep broad calm panels, but author the bonnet crown, shoulder, arch transition, lower door return and bumper profile. Give lamps, grille, wheels, windows and handles real depth. Add selective colour blocking after the plain and clay versions already read well. Do not substitute roof cargo, decals, dirt or fine bolts for the missing medium-scale forms. A trends more conventional; C deliberately exaggerates stance and bulk further. The user has not selected a direction yet.

## Why the current workflow plateaued

The recent `build_reference_wagon.py`, `build_stylized_landcruiser.py` and `build_stylized_rangerover.py` scripts create complete fresh scenes with simplified parts. Their proportions and output folders are reproducible, but they are not an independent component-authoring workflow. Decorative seam strips, simple lamps, large uninterrupted panels and placeholder interior masses are acceptable for a shape study, not the new art target.

Earlier `car_tools.py` already has shared surfaces, extracted panels, dependency tracking, geometry fingerprints, selective regeneration and staged rebuilds. It is a useful technical starting point, but its estate-specific dimensions, four coarse part groups and limited fit tests are not a general car editor. The new tool should reuse these protections without locking art direction to its procedural body shape. Passing its checks never established good art direction.

## Proposed Blender tool: fitted-part authoring

The central rule is: author parts independently inside a shared assembly specification. Arbitrary objects do not become well-fitting simply because they have named sockets.

### Shared assembly definition

Store the approved body envelope, wheel centres and maximum motion envelopes, shoulder/scuttle/roof landmarks, named panel boundaries and attachment frames. Keep one authoritative coordinate convention: metres, front -Y, left +X, up +Z. The body guide is an editable artistic surface; it must not be rebuilt into a generic box at every operation.

Each adjacent pair references the same boundary definition. The definition includes a seam curve or surface patch, offset/gap policy, orientation, thickness/return space and an interface version. At lighting-sensitive seams it also includes the intended surface normal or tangent relationship. A shared location alone cannot guarantee continuous highlights or a good panel transition.

### Part definition

Each component owns its detailed mesh, materials and optional pivots in its own collection, with a stable ID. It records its assembly frame, required interface versions, mating boundaries, permitted shape envelope, intended mounting contacts, allowed fit parameters, dependencies and locked/manual status.

| Part | Shared fit definition | Independently authored detail |
| --- | --- | --- |
| Bonnet and fender | Shared perimeter, seam clearance, edge returns and surface transition | Crown, shoulder planes, lips and selected creases |
| Lamp cassette | Opening perimeter, insertion depth, mounting frame and rear clearance | Lens, reflector, seal, rim, rear shell and tabs |
| Wheel and arch | Hub frame, tyre envelope and steering/suspension swept clearance | Tyre profile/tread, rim dish, spokes, hub and hardware |
| Door and glazing | Door aperture, glazing recess, gasket path and hinge envelope | Skin shape, handle pocket, inner return, seal and door card |
| Bumper and body | Mount frames, upper contour, return length and service clearance | Layered face, real recesses, recovery points and insert variants |
| Roof equipment | Roof/load interface, bracket positions and protected roof space | Rack, feet, straps, cases, lights and antenna |

Boundary loops or dedicated guide meshes should be driven by the shared definition. Protect a narrow transition region around those boundaries; allow free manual modelling over the rest of the part. Do not shrinkwrap or stretch the entire detailed component to conceal an incompatible interface.

### Artist workflow

1. Select a part and enter an isolation workspace with neighbouring surfaces ghosted and the full-car silhouette available.
2. Model the part normally, using editable meshes and appropriate modifiers. Fit guides and clearance volumes remain visible.
3. Preview it in the assembled car and in standard closeups. Switch between clay and final materials.
4. Run fit validation, inspect specific highlighted failures and resolve them.
5. Save a versioned component and assembly snapshot. Rebuild only selected generated regions and their declared dependencies.

Initial controls: Isolate Part, Show Neighbours, Show Interfaces, Check Fit, Preview Variant, Rebuild Selected and Save Revision. A small Blender panel plus Python operators is sufficient for the first implementation; a large general-purpose vehicle system is not needed first.

Automatic fitting applies only to parameters a component explicitly supports. A rigid bolt-on part can move with its mount frame. If a changed opening exceeds a hand-authored housing's supported size, preserve that housing and flag incompatibility. Do not silently deform it. Protect manual geometry, transforms and material changes, including relevant shader edits; the old fingerprints do not cover all of this. Save before mutation and replace generated parts only after staged validation succeeds.

## Detail and quality plan

### 1. Choose the style on a whole car

Use the new A/B/C board and detail target to select proportions, edge treatment and detail density. Then resolve one consistent side/front/top envelope in Blender. The generated views are references rather than independent things to trace. Review the clean base vehicle in clay at normal gameplay distance before committing to fine detail.

### 2. Prove one detailed front corner within the complete silhouette

Keep the entire approved body visible as context. Author bonnet, fender, leading door edge, lamp cassette, grille, bumper and wheel as separate fitted components. This junction proves body-to-body seams, an inset assembly, a bolt-on assembly and moving clearance in one small area. Deliver the assembled blend, independent collections, interface records, source and identical-camera clay/material renders.

Prioritize: fender shoulders and returns; bonnet thickness; lamp cavity/lens/rim; grille depth; bumper layers; tyre shoulders and rim dish; handle and window recesses. These changes should improve the car before accessories are added.

### 3. Prove that separate authoring survives edits

- Modify lamp internals, refit and verify the bonnet, wheel and manually edited door remain unchanged.
- Swap two bumper variants using the same mounts and interface version, without repositioning the body.
- Make a supported guide change and verify the declared generated boundaries update together.
- Make an unsupported opening change and verify the tool reports incompatibility and preserves the detailed part.
- Deliberately introduce a bad gap or collision and confirm the report highlights it.
- Save and reopen the assembly; confirm part identity, references, fit settings and manual edits persist.

### 4. Extend detail in complete assemblies

After the front corner looks right and fits, finish doors/glazing, rear/tailgate and roof. Develop a small compatible accessory family with visible brackets and sensible clearances. Then bring the other vehicle types into the same style using their own silhouettes and interfaces; sharing wheel/lamp construction patterns should not make every car the same body.

### 5. Treat the first-person cockpit as its own review milestone

Allocate detail to the driver's actual eye position: dash forms, wheel, gauges, controls, door cards, seals, pillars and visible bonnet edges. Verify sightlines and scale from inside. A few seats seen through exterior glass do not establish a functional cockpit.

## Review criteria

Keep style, fit and runtime preparation as separate results.

- Style: the base car is interesting without equipment; clay renders carry its form; detail clusters explain components; no noisy all-over bevels or arbitrary facets. Compare close interaction distance, normal exterior gameplay framing and a small distant thumbnail.
- Static fit: measure gaps and boundary mismatch along whole seams, opening containment, depth, surface transition, mesh defects and unintended intersections. Report intended bracket/fastener contacts separately instead of hiding all intersections.
- Moving fit: check bonnet and door opening sweeps, steering lock and suspension extremes against the relevant envelopes. These are future prototype checks, not claims about the existing studies.
- Edit safety: unchanged-part fingerprints, staged rollback, manual edit protection, interface incompatibility and save/reopen behaviour.
- Runtime preparation later: real UV/material requirements, texture versus geometry choices, LODs, pivots/rig, collision and in-engine performance. Choose budgets from the needed views and measured cost rather than an arbitrary low polygon target.

The tool can make fit reliable and edits safe. It cannot decide whether the style is appealing; consistent visual comparison and user direction remain necessary.


