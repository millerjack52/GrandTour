# Doors, window surrounds and mirrors

Current assembly: `Art/Export/VehicleTools/door-window-workshop-v02/RangeRover_Doors_Windows_Workshop.blend`.
Reusable collections: `Door_Window_Components.blend` in the same directory. The original `Art/rangerover.blend` remains untouched.

This milestone replaces the simple side-panel regions and accessories in the bonnet/bumper assembly with twelve independent collections: four door assemblies, six side-window cassettes and two mirrors. The previous fifteen wheel, fender, lighting and bonnet/bumper collections remain in the assembly.

## What changed

- Door skins have broad upper planes, a shallow lower pressing, real thickness, inner edge returns and separate rubbing mouldings. The rear door follows the retained faceted wheel arch. The old source skin is removed from the door region, so the new panels are not overlays.
- Handles sit in actual apertures. Each has an eight-sided recessed cup, a bridge grip and end returns. Front handles include a lock barrel and key slot.
- Window cassettes contain a folded frame, fine metal reveal, extruded rubber gasket, 3 mm solid glass pane and a lower drip lip. All nested profiles come from the same opening.
- Mirror assemblies contain a sail mount, pivot foot, support, chamfered housing, fitted casing seam, perimeter gasket and recessed reflective glass.

## Editing in Blender

Install `GrandTour_Doors_Windows_Addon.zip`, or run the saved `START HERE - doors windows workshop.py` text once. Open the **GT Parts** sidebar.

Select a door mesh to change **Door pressing relief** (0.5–1.5). Select a window mesh to change **Window seal width** (7–14 mm). **Rebuild selected side component** replaces only that collection. Mirror parts can be edited directly; no unsupported size/position fitting controls are exposed.

The fixed interface is `rr-side-v1`: metres, +X left, -Y front, +Z up, original assembly origin. The front/rear door gap is 8 mm. The supported relief parameter changes the interior pressing while preserving the perimeter. Window seals and glass resize together inside the unchanged frame. The top of each window frame sits about 3 mm below the inherited gutter's lower face.

Direct geometry, transform and relevant material edits cause rebuild to refuse. Preserve those edits as a manual variant or deliberately migrate them into the source. Do not clear fingerprints to bypass the refusal. Each collection carries its spec, owner and mounting root, and is marked as an asset.

## Source and verification

`Art/VehicleTools/door_window_workshop.py` supplies builders and sidebar registration. `build_door_window_workshop.py` opens the previous milestone and requires an empty output directory. `test_door_window_workshop.py` exercises actual aperture geometry, rear-arch fit, relief changes, fixed boundaries, deliberately broken boundaries, seal/glass resizing, mirrored skins, edit preservation, invalid inputs and save/reopen behavior.

`verify_door_window_assembly.py` reopens the saved assembly, checks component fingerprints, selected closed meshes, glass seats and intersections against the earlier fifteen collections plus the retained rear body, roof and gutters. It also imports and registers the packaged ZIP independently. Pass `--render-orthos` to save front/top fit images. Blender can exit with code zero after a Python assertion; inspect the log and generated report rather than trusting the exit code alone.

Review images include matched before/after whole and side views, close-ups of the door/handle/window/mirror, a clay view and separated components. `fit-report.json`, `tests.json` and `assembly-reopen-check.json` record the actual checks.

The assembly remains a static exterior study. Its original interior is a placeholder. Window frames are separate authoring modules; door skin and window roots are not yet linked into an operating door rig. Opening sweeps, hinges/latches, weatherproofing, collision, UVs, LODs and game export remain future work. Aesthetic acceptance is separate from technical checks.

Next exterior milestone: rear quarters, split tailgate, rear lamp assemblies and rear bumper, using the established detail density and boundary protections.
