# Wheel and fender workshop — first implementation

September 30, 2026. Built to improve the modelling process through reusable component construction and actual visual comparisons. This is not a complete vehicle rebuild.

## Open the result

- `Art/Export/VehicleTools/wheel-fender-workshop-v03/RangeRover_Wheel_Fender_Workshop.blend`: assembled Range Rover context with new front fenders and all four wheels.
- `Art/Export/VehicleTools/wheel-fender-workshop-v03/Wheel_Fender_Components.blend`: appendable left front wheel and fender collections, marked as assets.
- `01-before-detail.png` / `04-after-detail.png`: identical-camera detail comparison.
- `02-before-whole.png` / `05-after-whole.png`: identical-camera whole-car comparison.
- `03-before-clay.png` / `06-after-clay.png`: material-independent comparison.
- `07-after-side.png` and `08-components.png`: side inspection and separated parts.

The old Range Rover source and the user's `Art/rangerover.blend` are preserved. The new revision retains the old body colour, lighting, rear arches, cabin and other fittings so the component change can be assessed directly.

## What is implemented

`Art/VehicleTools/wheel_fender_workshop.py` is an importable Blender module and optional add-on. It has an editable cross-section tyre builder, staggered tread generator, an open rim barrel, a dished web with eight real vents, hub hardware, and a front-fender builder with common aperture/skin boundaries. Each wheel and fender has its own collection and mount.

In the review blend, run the embedded `START HERE - workshop.py` text once to enable **GT Parts** in the viewport sidebar. Alternatively install the supplied add-on ZIP through Blender's Install from Disk action and enable it. The blend does not autorun code or modify Blender preferences.

Select a wheel mesh, click **Toggle tyre profile guide**, select the visible guide and edit its vertices. Select a wheel mesh again, set the radius/width deliberately in the sidebar and choose **Rebuild selected part**. Edit the mesh directly when the procedural template is insufficient; direct mesh edits deliberately block later automatic rebuilding. Save that component as a separate manual variant.

**Check selected corner fit** reports static tyre/tread intersections and skin-to-arch boundary disagreement to a Blender Text. Use it after supported edits. Unsupported dimensions are rejected. Rebuild stages a replacement before removing the generated original and preserves unrelated components. Manual mesh, transform, common modifier settings and material-node changes trigger refusal.

Supported prototype dimensions: tyre radius .36–.39 m, width .24–.29 m, fixed rim radius .225 m, arch allowance .05–.075 m. The fender interface is specific to the original Range Rover study. The wheel is reusable; other vehicles need appropriate mount frames and authored fender interfaces.

## Visual refinement and validation

Revision 1 exposed unwanted diagonal facets on the fender despite passing fit checks. Revision 2 replaces the warped broad panels with planar strips and uses consistently scaled arch rings. Revision 3 closes the back of the wheelhouse and includes the bonnet's taper breakpoint in the shared edge. These are concrete lessons recorded in the modelling skill: valid fit tests alone do not establish good surfaces, and matching endpoints is insufficient for a multi-segment boundary.

The independent test script exercises actual profile-driven geometry changes, neighbour preservation, deliberate collisions and boundary mismatches, planar broad panels, intermediate bonnet-edge fit, hand-edit refusal, unsupported-size refusal, failed-stage recovery, supported range endpoints, sidebar registration, and save/reopen. Reports are saved in `Art/Export/VehicleTools/wheel-fender-tests-v04/`.

Fit measurements cover static surface intersections and shared skin/lip vertices. The distance field is sampled, not an exact minimum. Steering, suspension, containment, full neighbour fit, UVs, LODs, collision and engine performance are not certified. The whole car still needs body, lighting-component and cabin work; its overall style remains subject to review.

The final assembly was reopened in a separate Blender process. All six saved component fingerprints matched. Evaluated carcass/tread surfaces for all four wheels had no intersections with the checked side body, sill trim, wheelhouses, underbody mass or new fenders. See `assembly-reopen-check.json` in the review revision. This remains a static, explicitly scoped check.

Sources: `wheel_fender_workshop.py`, `build_wheel_fender_workshop.py`, `test_wheel_fender_workshop.py` under `Art/VehicleTools/`. The build writes to an empty revision directory; module import itself does not reset a scene. Construction guidance is now in the existing `grandtour-car-modeling` skill's `references/wheel-fender-workshop.md`.
