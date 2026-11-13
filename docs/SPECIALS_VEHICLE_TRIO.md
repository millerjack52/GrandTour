# Specials vehicle trio — Blender and Unreal handoff

Three independent stylized vehicle models: Opel Kadett A (Oliver/Botswana inspiration), BMW E39 528i Touring (Africa inspiration), and Suzuki SJ413 (James May/Bolivia inspiration). These are intact, simplified game interpretations before episode-specific damage or improvised modifications, not factory-accurate restorations. Dimensions are modelling targets and measured export values; small trim and cabin details are interpreted.

## Files

- Generated multi-view reference sheets and exact prompts: `Art/References/Vehicles/SpecialsTrio/`. Built-in image generation was used; references are style guides rather than engineering drawings.
- Editable sources: `Art/Vehicles/SpecialsTrio/<car>/<car>.blend`.
- Rigged textured sources: `Art/Vehicles/SpecialsTrio/<car>/<car>_Game.blend`.
- Portable archives: `Art/Vehicles/SpecialsTrio/<car>/<car>_BlenderPackage.zip`.
- Export evidence: `Art/Export/SpecialsTrio/<car>/Package_v01/`, with three FBXs, textures, reports and actual Blender renders.
- Source revisions R1–R6 are preserved under `Art/Export/SpecialsTrio/<car>/`.

Car identifiers are `KadettA`, `E39Touring` and `SJ413`. `summary.json` beside the canonical vehicle folders records final counts and validation status.

## Iteration and review

R1 exposed flat nose construction, overly thick frames, shared-looking wheel details and cockpit floor gaps. R2 corrected front mesh winding, reduced frames, introduced actual steel-wheel apertures, separated the BMW arch section that belongs to its rear door, and added its bumper/quarter-window treatment. R3 corrected lamps extending above the bonnet and removed floor/sill geometry crossing wheel space. R4 added continuous wrapped bumpers and a fully modelled Suzuki spare. Broader intersection checks then caught rear seats reaching into the wheel space on the Kadett and BMW; R5 corrected that fit.

Open-panel review caught the Kadett plate following the boot lid and hatch badges staying behind when their panels opened. R6 fixes those assignments and the Kadett speedometer ordering. The Suzuki rear-door review also corrected the test pose to open outward. The distance-mesh render rejected collapsing wheel dishes/spokes: current LODs preserve all exterior geometry and reduce the interior only. These are conservative distance variants, not a final performance optimization.

Actual source and baked-asset front, rear, side, cockpit and opened-panel renders are kept for inspection. No generated image is presented as a model render.

## Export and material contract

Blender uses metres, front -Y and left +X. FBX geometry is centimetres with +X front and +Y left before Unreal's handedness conversion. One Root bone with rigid child groups for wheels, doors, bonnet, boot/hatch, steering and instrument needles. Every vertex has exactly one full-weight influence.

Four material sections: Exterior, Interior, Glass, Markings. Exterior and Interior each have a 2048-square BaseColor and ORM texture. BaseColor is sRGB; ORM is linear, R=1 (neutral AO), G=roughness, B=metallic. No light is baked into albedo. Glass requires a translucent engine material. Small instrument and text graphics use the `GT_Colour` vertex attribute; connect Vertex Color to their base colour. Textures are packed in the .blend files and also supplied as PNGs.

## What the checks establish

- Explicit BVH intersection tests for straight tyres/treads against outer body skins, bonnet, floor, sill and seats; seats against glass/roof; body skin panels against one another. All checked pairs must pass before packaging. Intentional assembly contact, every possible part pair, suspension travel and full steering sweeps are outside this test's scope.
- Evaluated mesh triangles cleaned of zero-area faces, finite positions, UVs and single rigid influences.
- Every articulated group is rotated and its evaluated vertices compared with the expected rigid transform.
- Three FBXs per car re-imported into a fresh Blender scene, checking bone names, material sections, UVs, vertex colours, exact triangle counts, axes, wheelbase, track, hub height and bounds against source geometry. FBX hashes are recorded.
- Final texture/LOD and open-panel renders inspected separately from the numerical checks.

The approved packages are now imported into Unreal with dedicated vehicle Blueprints, three mesh LODs, materials, wheel classes and two-box chassis/cabin PhysicsAssets. Working instrument needles, steering-wheel animation, opening body panels and model-specific damage still require bindings. The wheels use the existing native Chaos animation. Handling values are initial test tuning, not a simulation of each production car's exact specification. They are not yet offered in the campaign car selector, and performance has not been benchmarked.

## Unreal testing

Under `/Game/GrandTour/Test/SpecialsTrio/`:

| Car | Normal test track | Mud/gravel/ford strip |
| --- | --- | --- |
| Opel Kadett A | `L_KadettA_Test` | `L_KadettA_Mud` |
| BMW E39 Touring | `L_E39Touring_Test` | `L_E39Touring_Mud` |
| Suzuki SJ413 | `L_SJ413_Test` | `L_SJ413_Mud` |

These are independent map copies of `L_TestTrack` and `L_MudDrive`; open one and press Play to spawn as that car. The original map assets and startup-map settings are unchanged. Meshes, physics and Blueprints live under `/Game/GrandTour/Vehicles/Bodies/<car>/`. Existing keyboard/gamepad driving controls apply; C switches cockpit/chase camera, F gets out, and on-foot interaction gets back in. Doors stay visually closed in this first driving integration.

The new vehicle defaults disable Range Rover panel replacement, its extra windscreen/dashboard, and the parts system's placeholder cubes. The parts remain installed and functional. `bShowGreyboxVisuals` defaults to true so existing prototypes retain their old presentation. A drivetrain fix respects a front torque share of zero (Kadett/BMW rear drive) or one (front drive); the existing default 50/50 AWD path is unchanged. The Suzuki uses that AWD test setup. Suspension, camera eye, tyre dimensions and chassis collision are configured independently per model.

`Art/Export/SpecialsTrio/unreal_import_report.json` records imported assets. `unreal_asset_check.json` checks their persisted defaults after restarting Unreal, including all six maps, bones, dimensions, wheel radii, disabled legacy additions and collision. `UnrealReview/runtime_check.json` records the Play-in-Editor smoke tests and actual rendered previews. Only an `ok: true` report confirms completion of its check. Driving checks cover four grounded wheels at rest, forward travel, rotating wheels, braking, turning, driven axle torque, and getting out/back in. They do not establish full suspension/steering clearance over every obstacle or a complete mud/ford traversal.

Completed 2026-09-30: editor build succeeded; fresh-process asset checks passed; all six PIE runs passed; twelve exterior/cockpit captures saved. The original Range Rover's `GTDriveTest` regression also passed (76.6 m, peak 70 km/h, input mappings and both cameras valid), recorded in `Saved/Logs/specials_original_car_regression.log`.

## Reproduction

From `C:/GrandTour`, build a source with Blender 5.1:

```powershell
& 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --factory-startup --python-exit-code 1 --python Art/Blender/build_specials_trio.py -- --car KadettA --version R6 --views front,rear,side,cockpit
./Art/package_specials_trio.ps1 -Car KadettA -Source R6
```

Repeat with `E39Touring` and `SJ413`. Preserve manual edits before regenerating a named revision. The packaging and validation adapters reuse the checked Land Cruiser export implementation without reading or modifying its assets. A failed check stops the pipeline. Run the finalizer only after reviewing the rendered evidence.

After building the editor module, run `./Art/import_specials_trio.ps1` to import and check saved assets. It stops if another editor/game is running. Runtime checks use `Art/Unreal/check_specials_trio_drive.py` in a regular Unreal Editor process with `-ExecCmds="py C:/GrandTour/Art/Unreal/check_specials_trio_drive.py"`; they run PIE, save screenshots and close that editor. Importing again refreshes these generated vehicle assets but preserves existing test-map geometry and assigns only each map's vehicle game mode.

## Research references

- [Top Gear: Oliver's Kadett A and Botswana history](https://www.topgear.com/car-news/top-gear-tv/meet-olivers-african-racing-cousin).
- [Opel: Kadett A history and period photographs](https://www.media.stellantis.com/em-en/opel/press/opel-kadett-and-astra-85-years-as-defining-force-of-compact-class).
- [BMW Group Classic: 528i Touring E39](https://www.bmwgroup-classic.com/en/models/bmw-classics/product-description-page.ad-932-1.bmw-528i-touring-e39.html).
- [Suzuki: official 4x4 model history](https://www.globalsuzuki.com/automobile/history/).
- Episode vehicle cross-checks: [Africa special](https://topgear.fandom.com/wiki/Africa_Special), [Bolivia special](https://topgear.fandom.com/wiki/Bolivia_Special).

Photography informed the research only; it is not included in the vehicle textures. Generated reference sheets are included with their prompts and must not override the actual exported geometry measurements.

## E39 refinement: first body-shape checkpoint, 2026-09-30

The user identified panel gaps and misplaced or incorrectly sized parts after driving integration. Refinement now starts with a continuous shell and a proportion review before separating panels. The approved R6 source, package and Unreal assets are preserved.

Current study: `Art/Export/E39Refinement/03/E39_ShellStudy.blend`. Five actual Blender renders beside it show front, rear, side and both three-quarter angles. Revisions 01 and 02 are retained. Revision 02 adjusted window/pillar angles and neutral presentation; revision 03 corrected a bonnet-corner fold exposed by the renders. The packed BMW dimension drawing and an internal readme travel with the blend file.

Reference: BMW's 1999 owner manual, printed page 200, [sport wagon dimensions](https://www.ge39.com/files/2000Manual-5Sedan-SportWagon.pdf), locally archived under `Art/References/Vehicles/E39Refinement`. Published length 4805 mm, width 1800 mm, height 1440 mm, wheelbase 2830 mm and tracks 1512/1526 mm anchor the study. Intermediate surface shapes are authored estimates from the drawing, not measured scan data.

`shape_check.json` records measured shell length 4805 mm, width 1798.045 mm, roof height 1440 mm, and exact target axle spacing/tracks. The shell has 4616 triangles before bevel, zero loose vertices, zero boundary edges and zero nonmanifold edges. These checks establish a closed surface, not full production quality or absence of all possible intersections. Wheel placeholders and painted window guides remain; bumper/lamp shaping, final panel topology, glazing, interior, UVs, rigging and export remain future work. No Unreal validation applies to this study.

Reproduce using `Art/Blender/refine_e39_shell.py` with `--revision <new-id> --views three_quarter,side,front,rear,rear_quarter --samples 32` through Blender's background Python runner. A copy of the builder is saved with revision 03. CPU rendering uses six threads. Review the bonnet/cabin/rear proportions before cutting doors and other moving panels from the shared shell.

## E39 exterior refinement: revision 11

The next review asset is `Art/Export/E39Refinement/11/E39_ExteriorStudy.blend`, built by `Art/Blender/refine_e39_details.py`. It adds recessed twin headlamps, kidney grilles and slats, lower intake and fog lamps, shaped bumper returns, rear lamps and plate pocket, handles, fitted mirror mounts and rubbing strips. The front corners were widened within the existing body width to give the headlight housings adequate surrounding metal. The stepped rear quarter-window guide was simplified.

Bonnet, four door skins and tailgate are extracted from the shared surface, with a nominal 3 mm inset perimeter. Door cuts follow the pillar slopes above the belt; the tailgate perimeter widens below its glass. Skin thickness runs inward. The study retains window material guides, placeholder wheels and the packed dimension drawing; it has no completed cabin, hinge rig, UVs or game export. Final panel returns, weather seals, opening travel and full assembly clearance remain to be built and checked.

Actual Blender render iterations 04 through 11 exposed and corrected cuts through glass, detached mirror mounts, lamp-recess artifacts and shading changes caused by panel separation. Revision 11 uses deliberate flat shading on the tailgate sections to remove the false denting caused by smoothing across its recesses, and contains five neutral views. `saved_file_fit_check.json` is produced by independently reopening the saved blend with `Art/Blender/check_e39_exterior.py`. All six evaluated panel skins passed: zero open/nonmanifold edges or loose vertices, positive enclosed volumes, and zero mutual panel intersections across all fifteen pairs. This is deliberately narrower than a complete vehicle fit or game-readiness claim. The report does not test every decorative fitting against the fixed shell or full hinge travel.

Reproduce with the detail builder's `--revision <new-id> --views three_quarter,side,front,rear,rear_quarter --samples 48`; use the same Blender background invocation as the shape study. Then run `check_e39_exterior.py -- <absolute-path-to-E39_ExteriorStudy.blend>`. The existing R6 source, Unreal vehicles and maps are not replaced by this review asset.
