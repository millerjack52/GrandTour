# Correcting the vehicle shape

The user rejected the Crafted Utility v05 silhouette. This supersedes its passing technical checks. The new workbench diagnoses the rejected model; it is not another claimed finished car.

## What failed

The previous workflow checked broad dimensions and component construction, but did not register and overlay the actual mesh against traced contours. Its long straight bonnet, almost flat roof, low arch openings and simplified side sections drifted from the reference. Clean topology and tyre clearance did not address that failure.

A source audit also found nine settings in `build_crafted_utility.py` that were not read by geometry: `arch_lip_width`, `belt`, `door_split`, `lower_half_width`, `rear_door_end`, `roof`, `roof_front`, `roof_half_width`, `roof_rear`. Many corresponding positions were hardcoded later. The earlier description of a fully shared shape specification was therefore overstated. Do not try to fix this model by changing those dictionary fields alone.

## Working diagnostic

Folder: `C:/GrandTour/Art/Export/VehicleTools/reference-fit-v01/`.

- `Crafted_Utility_Reference_Fit.blend`: 47 editable primary-form meshes in a separate collection, preserved v05 locked/hidden, packed source images, traced curves and three fixed reference cameras.
- `shape-diagnosis.png`: source pixels with native Blender contour overlays and enlarged bonnet/roof comparisons.
- `reference-observations.json`: explicit manual pixel annotations, camera registration, uncertainty and reference priority.
- `baseline-contour-errors.json`: measurements from evaluated mesh triangles, not from configuration values.
- `workbench-checks.json` and `saved-workbench-checks.json`: camera projection, actual-edit sensitivity, saved-file persistence and sidebar checks.
- Source tools are copied alongside the file. Install `reference_fit_workbench.py` as an add-on, or run the embedded `RUN ME - Reference Fit tools.py` text explicitly. Nothing autoruns.

In Blender, use the **GT Shape** sidebar. Choose a view and adjust Reference opacity. Edit only `FIT | Editable forms`; yellow target curves are editable observations, not automatic mesh drivers. **Measure edited bonnet and roof** writes a new numbered JSON report and a Text Editor report. Save manual work as a new blend revision. The builder refuses to overwrite an existing workbench; `--output NEW_FOLDER` creates a fresh diagnostic copy.

The original A image supplied by the user is the primary artistic target. The generated side/front sheets are secondary. Their apparent projections and proportions disagree, so they cannot all be treated as measured orthographic views. Do not repeatedly generate new references to justify geometry drift.

## Evidence and uncertainty

The side camera uses the two wheel hubs and one uniform scale; it does not stretch the image to hide errors. Native Blender projection reproduces those anchor coordinates within 0.001 px numerically. This is a registration implementation check, not evidence that the hand-picked anchors are exact. Manual tracing uncertainty is estimated at about 3 px.

Against the annotated side view, the existing bonnet's leading contour is approximately **21.5 px too high**, while its rear portion is around **2-6 px low**. Its local contour RMS is 8.7 px. The roof's middle is approximately **5.7 px low** and its front transition is about **9 px high**, with 5.4 px local RMS. The overlay also exposes the rear roof overrun and arch/aperture differences. These are local image-space observations, not a percentage accuracy score or real-vehicle dimensions.

The measurement test moved the actual roof vertices up by 0.10 authoring metres and observed the expected 18.79 px contour displacement, then restored them. The original model file hash remained unchanged. Saved-file tests exercise camera switching, packed reference persistence, opacity and report export.

The original-perspective camera is **provisional**. A wheel-based fit with fixed 60 mm focal length gives about 6.4 px weighted RMS and reaches its 8-degree elevation lower bound. The far wheel is partly hidden; that view is underconstrained. Do not optimize body shape automatically against this camera or interpret its mismatches as certain body errors. The front camera is also provisional. Resolve these views through manual camera matching and shared landmarks before using them quantitatively.

## The modelling method from here

### User correction: character is in the changes of plane

On 2026-09-30 the user emphasized that the lower rear body and bumper slope inward toward the bottom. The goal is to identify comparable nuances across different models, not only match a car's bounding silhouette. Before the next build, create a per-car shape map: evidence region -> directional observation -> confidence -> actual geometry control -> fixed-view comparison. Include shoulder turns, cross-sectional taper, roof/bonnet crown, opening shapes and bumper/panel relationships. Keep implementation and aesthetic approval separate. Reuse the observation method across cars, not this car's exact proportions.

First application starts in `Art/Export/VehicleTools/shape-character-v01/` with 11 evidence records. Latest reviewable bare-body revision is `Art/Export/VehicleTools/shape-character-v03/Crafted_Utility_Character_Study.blend`; v02/v03 fix visible roof/bonnet/scuttle joins. Original models and diagnostic cameras remain preserved. The general procedure is recorded in the grandtour-car-modeling skill's `references/shape-observation.md`.

The new study includes annotated original-A and side-reference shape maps, an actual-render side overlay, seven fixed review views, six coordinated shape probes on the FORM CONTROLS object, and saved-file driver tests. 1 is the proposed shape, 0 removes the named feature. These are comparison controls; their alternatives do not promise every dependent joint stays fitted. The side fit is materially closer by direct contour construction, but width/hidden geometry and agreement with the original perspective are still provisional. No details or game integration should be restored on the strength of the side overlay alone.

1. Fix reference choice and camera registration first. Hold those cameras fixed during a geometry comparison. Keep wheel centres and ground as anchors; add reliable body landmarks only after separating camera ambiguity from shape differences.
2. Author a small, editable master body with deliberate cross-sections at the nose, front axle, scuttle, cabin middle, rear axle and tail. Use a Mirror modifier and controlled surface topology. Define crown, shoulder roll, cabin taper, lower-body tuck and arch profiles as actual curves/vertices. A bounding box or a single side outline cannot specify volume.
3. Correct the bonnet drop/crown and roof crown/end first, then the shoulder sections and window apertures. Evaluate shaded curvature as well as silhouette. Use the original three-quarter image for the overall impression and inspect the opposite quarter to catch a shape that only works from one camera.
4. Compare source/mesh overlays and local contour errors after each meaningful form change. Check held-out profile samples and all relevant views; a lower error on the same few traced points is not enough to declare the car right. Stay with the plain body and wheel proxies until the shape is convincing.
5. Cut fitted panels and reintroduce existing detail from that established master body. Components follow the body; their old mounts must not force the body back into the rejected shape.

This changes the construction and review loop. It is not a promise that a camera solver or another skill file can judge the entire design automatically.

## Technical basis

Blender supports reference backgrounds in cameras and distinguishes perspective from orthographic projection: [Blender camera manual](https://docs.blender.org/manual/en/2.90/render/cameras.html). Camera pose estimation requires corresponding image/3D observations and camera assumptions: [OpenCV PnP documentation](https://docs.opencv.org/4.13.0/d5/d1f/calib3d_solvePnP.html). Bounded residual minimization and robust losses can help numerical fitting, but do not remove ambiguity: [SciPy least-squares documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html). The current camera proposal uses a small NumPy implementation, not OpenCV or SciPy; a synthetic recovery test accompanies it.
