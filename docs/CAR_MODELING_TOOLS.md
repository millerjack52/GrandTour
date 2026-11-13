# Car construction tools: first working module

## Bonnet and bumper workshop — third component milestone

`Art/VehicleTools/bonnet_bumper_workshop.py` adds an editable bonnet crown within fixed boundaries, a stepped bumper with fitted returns and real openings, and independently swappable vent/blank inserts. See `docs/BONNET_BUMPER_WORKSHOP.md` and `Art/Export/VehicleTools/bonnet-bumper-workshop-v04/`. The prior wheel, fender and lighting collections remain intact. These are static exterior authoring components, not articulated or game-ready vehicle parts.

## Lamp and grille workshop — second component milestone

The lighting module `Art/VehicleTools/lamp_grille_workshop.py` adds separate housings, reflectors, curved fluted lenses, retaining bezels, indicators and a grille with actual openings and shaped slats. It reuses protected construction helpers and preserves the wheel/fender collections. See `docs/LAMP_GRILLE_WORKSHOP.md` and `Art/Export/VehicleTools/lamp-grille-workshop-v02/` for the review, component library and add-on. This remains an unlit component study, not optical or game-readiness validation.

## Wheel and fender workshop — implemented September 30

The first reusable component workshop is now implemented. See `docs/WHEEL_FENDER_WORKSHOP.md`, the module `Art/VehicleTools/wheel_fender_workshop.py`, and the actual Blender review in `Art/Export/VehicleTools/wheel-fender-workshop-v03/`. It supplies editable tyre profiles, tread, dished wheels with through-openings, fitted front fenders, selective protected rebuilding and static fit checks. The modelling skill now records these demonstrated methods. This is a component study; the rest of the vehicle remains the older simplified model and user style approval is pending.

## Latest direction — richer style and separately authored parts

The user's latest feedback is that the simple wagon, Land Cruiser and Range Rover studies lack detail and visual interest. Their earlier provisional acceptance is not approval of the final art direction. See `docs/VEHICLE_STYLE_AND_MODULAR_PARTS_PLAN.md` and `Art/References/Vehicles/StyleReset_2026-09-30/` for the new concept boards and proposed fitted-component authoring workflow. Direction B is recommended, not yet selected. This pass produced concepts and a plan, not a new tool or vehicle mesh. Preserve previous studies as iteration history.

## Fresh reference-led wagon — September 30, 2026

The user rejected the overall style and silhouette of `coachwork-v02`, then accepted the proposed direction of a compact, sturdy angular family wagon. After viewing `reference-wagon-v03`, the user accepted it as good enough and requested a Land Cruiser in the same style. The generated concept remains a visual target, not a calibrated blueprint.

New independent source: `Art/VehicleTools/build_reference_wagon.py`. Current study: `Art/Export/VehicleTools/reference-wagon-v03/Reference_Wagon.blend`. This starts from an empty scene and does not import or deform the rejected coachwork. Each build requires a new empty output directory and saves its source snapshot, artistic dimensions, packed concept and five actual Blender renders. Earlier work is preserved.

The study uses broad planar panels, a folded bonnet, an upright cabin, fitted window openings, connected arch lips and wraparound bumpers. Simple seat and dashboard masses support exterior glazing review; they are not a functional cockpit. Initial render review caught roof-end gaps, warped side shading and excess arch clearance; subsequent revisions corrected these. This is a silhouette review candidate, not an exact reproduction, finished vehicle or validated game asset. No rig, UV, collision, motion-clearance or Unreal checks have been performed.

## Sculpted coachwork — rejected style study

Latest: `Art/Export/VehicleTools/coachwork-v02/Estate_Shape_Study.blend`, generated with `specs/estate_coachwork_v1.json`. The user rejected the previous revision's rectangular overall shape. The earlier longitudinal taper retained too much of the constant-width construction; `coachwork.py` now supplies independent longitudinal roof/body profiles and a vertical section profile. These create wider axle shoulders, tucked lower doors and sills, a narrower crowned roof, a crowned bonnet and cut-back end corners. Wheels retain their dimensions and positions. The optional coachwork profile replaces the earlier simple plan taper.

Body, extracted skins, glazing and fittings follow the same subdivided envelope. Bumpers retain their vertical section while following the plan profile. A first render exposed faceted glazing and a distorted bumper; v02 corrects both. Seven actual Blender views were inspected, plus matched front/top comparisons against shape-v07 with common cameras, scale and lighting. Comparisons live in `coachwork-v02/comparison/`, with BEFORE on the left and AFTER on the right.

All 38 regression assertions passed, including measured roof taper/crown and lower-body tuck, as well as the targeted indicator and sill/arch checks. Source and test snapshots accompany the saved model. This remains a shape study pending user style review: opaque glass, simplified wheels, no interior, rig, UV/export or Unreal validation. Static checks are not a universal intersection guarantee.

## Earlier taper and fitting corrections

Latest: `Art/Export/VehicleTools/shape-v07/Estate_Shape_Study.blend`, generated with `specs/estate_shape_v2.json`. The accepted wheelbase, roof height and cabin proportions are retained. Body width now narrows to 88% at the nose and 94% at the tail, with explicit angled front corners. Body, glazing and fittings are split at shared taper stations before shaping; wheels retain their dimensions and placement.

Sill trim ends derive from the wheel openings with 35 mm nominal clearance at the arch feet, and the flare fades into those feet. The indicators sit inside the front recess and behind the nose plane. The front bumper and side returns form one connected mesh. Seven Blender views include dedicated sill/arch and indicator close-ups.

34 regression assertions passed. The fit report additionally checks both indicators against the recess, both trim ends against the arch feet, and ray samples for bodywork occluding the trim. Deliberately displaced indicators and trim fail the relevant checks. These are targeted static checks, not general certification of every fitting or vehicle articulation.

## Current shape revision

The user accepted the construction approach but rejected the front prototype's overall shape. The latest review is `Art/Export/VehicleTools/shape-v04/`, using `specs/estate_shape_v1.json`. Its complete estate silhouette is a shape study, not a finished game asset. The bonnet span changed from 1.32 m to 1.07 m, roof width from 1.33 m to 1.43 m, and sill height from 0.265 m to 0.36 m. Rear roof, axle and pillar landmarks make cabin/body balance visible. The lamp/grille recess was enlarged to read as one front-face band.

The original front-module tests remain. Additional checks cover four wheels, four extracted door skins, rear-axle edits and unobstructed lamp recesses. Final review evidence and source snapshots are stored beside the blend. Glass remains opaque and wheels simplified; no rig, interior or Unreal validation is claimed. Style approval remains with the user.

2026-09-30. Version one establishes a repeatable construction and review workflow for the newly approved stylized estate. It does not replace the existing game vehicles.

## Start here

- Installed skill: `C:/Users/mille/.codex/skills/grandtour-car-modeling/SKILL.md`; invoke as `$grandtour-car-modeling`.
- Repository copy: `Art/VehicleTools/skill/`. Keep it and the installed copy synchronized when updating the skill.
- Source tools and specifications: `Art/VehicleTools/`.
- Current reviewed prototype: `Art/Export/VehicleTools/front-v04/Estate_Front_Construction.blend`.
- Five actual Blender renders, specification, fit report and regression report live beside that blend.
- Usage, approved reference locations, edit protection and limitations: the skill's `references/workflow.md`.

## What this proves

The bonnet and adjoining door skins are extracted from a shared body surface. Wheel dimensions drive both tyres and wheel openings. Window frames derive from their glazing boundaries; headlamps sit in cut openings. Components rebuild selectively, with a preflight check for manual edits and staging before existing objects are replaced.

21 regression assertions passed in Blender 5.1.2. They include increased tyre radius and matching arch changes, width changes, unchanged unrelated components, preservation/refusal of manual edits, invalid inputs, rollback after an injected builder failure, save/reopen consistency, deliberate collision detection and shared window/body corner positions.

The saved v04 file was also reopened through the CLI and widened from 1.82 m to 1.88 m. It rebuilt body, cabin and fittings, retained wheels and passed the limited static fit checks. That geometry-only variant is `Art/Export/VehicleTools/front-width-test/`.

Visual review caught a raised window base despite clean initial topology results. The second shape iteration joined that boundary, refined the arch lip, reduced the hub size and raised the bumper. The final pass centred the lamp pairs and corrected the top-view framing. This is why render inspection remains separate from geometry checks.

## Deliberately unfinished

The module ends at a cut through the front door/roof. It is a construction example, not a finished vehicle. The broad forms follow the approved direction but still need a whole-body proportion review. Glass, wheels and fittings remain simplified. No rear body, cabin interior, UVs, moving-part rig, steering travel or Unreal checks are included. The automated intersection report covers specified body/panel/wheel pairs, not every part of the assembly.

Next development step: extend the shared shell through the rear quarter, derive the remaining openings and doors, then test door hinges and wheel travel. Keep shape review separate from mechanical and export readiness.
