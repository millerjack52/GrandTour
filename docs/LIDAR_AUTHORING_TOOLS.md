# LiDAR track and river-bed tools

Open `Open-LidarStudy.bat`. Use **Tools → LiDAR Place**. This tool authors the new
mud track to the logging site and local river-bed/ford edits. The river course
and water levels stay fixed. No route or ford location has been chosen for you.

## Draw the mud track

1. Move the editor camera over the intended start. Choose **New mud track here**.
2. Select its `DesignPoints` spline. Move points; Alt-drag an end point to extend
   the control polygon. Keep point type **Linear**. The road generator uses the
   existing recovered natural-cubic implementation, rather than Unreal Hermite
   tangents. The coloured preview shows the design polygon, not the finished mesh.
3. Use **Snap selected track to ground** after moving the route across slopes.
   Then adjust individual point heights where you want a bench or graded approach.
   Select the track under **LiDAR Designs** in the Outliner, or its linked built
   mud-track actor. Selecting terrain, foliage or a gravel road shows an explanation.
   Snap uses the selected spline's current XY, including moved or extended built
   roads, and supports Undo. When a built road is selected, it snaps that road
   and copies its control polygon to the linked design in the same transaction.
   The built spline displays Linear segments to match the exported polygon;
   the generator still uses its recovered natural-cubic algorithm. Select either
   the design or its built road, not both. Terrain remains unchanged until ApplyDesign.
   The viewport
   and Output Log report how many points moved and the largest height change.
   If Unreal was already open when the Python tools were updated, switch the
   Output Log command dropdown to **Python** and run:
   `import importlib, lidar_authoring_editor; importlib.reload(lidar_authoring_editor).register_menu()`
   This reloads the menu code without reloading the level or its design actors.
4. In Details, set **Width Metres** and **Maximum Cut Fill Metres**. The initial
   width is a provisional 2.4 m, adjustable from 2 m; it is not a photo measurement.
   A spline point's **Scale Y** multiplies Width Metres locally. Export retains
   these widths, and both terrain generation and vegetation clearance follow them.
5. Use **Preview selected width and depth** for a temporary 60-second outline.
   **Inspect selected profile** reports length and maximum control-point grade in
   the Output Log. The final road uses 50 cm relief tiles and the existing budget.

## Use the MudRunner study controls

The owner's correction on 19 October: **mud does not imply pronounced ruts along
the whole track**. Photo 1 establishes a narrow bush trail, grey-brown mud, close
ferns and tree-fern skirts; the rutted spot in that photo is not a uniform template.

The tool feeds the existing `GTProceduralRoad` / `FGTRoadCondition` path:

| Control | Meaning |
|---|---|
| Mud Depth Cm | Available yielding soil; not an initial rut and not predicted wheel sinkage |
| Firmness | Existing soil-response control; softness is derived independently of appearance |
| Wetness | Wetness input, separate from firmness |
| Rut Depth Cm | Pre-existing geometric grooves; **zero by default** |
| Relief Strength | Recovered dirt-path solid relief; **zero by default**, independent of live mud |
| Basin Depth Cm | Broad local bog hollow, independent of old ruts and soil depth (0–100 cm) |
| Water Fill Cm | Maximum standing-water depth above a depression floor (0–40 cm), limited by its spill point |
| Conditions | Local stretches with their own soil, rut, basin, water, churn, spread, breakup and grass controls |

Start with no extra Conditions. **Add local mud condition** creates an entry with
zero old-rut depth (the generic study struct's defaults are different). Add a
condition only where you want a local worn
stretch, shallow wet hollow, churned patch or deeper old rut. Start/End Metres use
the three-dimensional control-polygon knot distance, as the study does. Blend
Metres softens transitions. Later conditions override soil values and add relief;
start with non-overlapping ranges. For a bog, set **Basin Depth Cm** to shape a
broad hollow and **Water Fill Cm** to allow standing water. Water fills the final
collision bed up to its spill point; a sloping or open hollow may drain. Neither
control requires pre-existing ruts. The pool builder preserves the existing river
and pond child domains and replaces its own generated pool on each rebuild.
Keep river-bed/ford edits in their separate design actor.

The starting mud depth 18 cm, firmness .45 and wetness .65 are editable setup
values, not a claim about the site. Your drive determines the feel. Existing gravel
roads retain their settings and material mask. The new track uses the existing mud
surface and live wheel deformation; this tool does not replace the runtime solver.

Read the distinction between recovered algorithms and host authoring rules in
`docs/ProceduralGroundPlan.txt`, `docs/ProceduralGroundGuide.txt` (Road conditions
and Fine road relief), and
`Art/Export/MudRunnerEditorResearch/RoadRelief/FINDINGS.txt`. The layered response
background is in `docs/MUDRUNNER_LESSONS_PLAN.md`. Historical deeply churned example
presets in `docs/MUD_ROADS_PLAN.md` are not applied to the whole logging track.

## Shape the bed and ford

1. Move the camera near the desired crossing and choose **New river bed near camera**.
   This creates a roughly 40 m reach on the existing course, with control points at
   the bed. It does not move the river or edit terrain immediately.
2. Set **Target Depth Metres**, then choose **Fit selected bed to target depth**.
   This places the controls below the unchanged reference water surface. Afterwards
   individual point **Z** values are the authored bed heights: raise for a shallower
   ford, lower for a deeper channel. Changing Target Depth alone does not move them.
3. Adjust **Width Metres** for the flat-bottom footprint and **Bank Blend Metres**
   for the transition back to the existing bed. Bed edits taper over up to 5 m at
   their ends and at the existing wet shoreline. Dry banks and the course remain.
4. Preview shows the bed width and vertical depth lines. Inspector/export check
   control depths; preparation checks the full sampled shape and cut/fill limit.

Supported target depths are 0.10–1.50 m, matching this study's water-domain cap.
Overlapping bed-edit footprints are rejected; use one longer path with more points.
The source DEM is not bathymetry. The derived collision landscape is still 1.835 m
per vertex, so make broad, blended changes; this is not a centimetre-scale cobble
sculptor. Road generation preserves the wet bed at the ford instead of building a
road embankment through it.

## Save, rebuild, drive

**Save all designs** writes `Art/LidarAuthoring/edits.json`, backing up the previous
file under `Saved/LidarAuthoringBackups`. Only this export makes viewport edits
pipeline inputs. Saving the Unreal map alone is not an export. **Load saved designs**
recreates the controls; it refuses when controls already exist to avoid overwriting
unsaved work. Use **Enabled = false** and export to remove a design from the build
while retaining its controls. Unreal Undo handles viewport changes, not exported files.

Close Unreal normally, then from `C:\GrandTour` run:

```powershell
powershell -NoProfile -File Art/lidar_place.ps1 -Mode ApplyDesign
```

That runs **prepare → Install → Polish → Water → Check**, checking the Unreal slot
before every editor launch. It never kills Unreal. Preparation is staged and only
successful outputs replace the previous prepared files. Install backs up the level
content, imports the derived terrain, restores design controls from JSON, and rebuilds
the roads, water depth/shore data and vegetation. Source DEM and reference vectors
remain untouched. River files and the derived terrain participate in the install digest.

Use `-Mode ValidateDesign` for a fast saved-input check and `-Mode Prepare` to bake
without changing the saved level. After a first install, the design controls are in
the **LiDAR Designs** Outliner folder. For a fresh editor session before that, use
**Load saved designs** if no controls are present.

Drive the descent, both ford approaches and the exit to the logging site. No tool
check approves route choice, mud feel or ford safety for you. Review the generated
cross-slope report and bed-height readbacks alongside your drive. A new track's
cross-slope over 20 degrees fails Check; that is a coarse error guard, not a target.

## Verification and limits

`Art/tools/test_lidar_authoring.py` checks unchanged/disabled designs, local bed
shaping and restoration, overlap/depth rejection, independent mud/rut inputs, and
water/terrain digest coverage. `Art/lidar_place.ps1 -Mode AuthoringCheck` exercises
the menu and editor control serialization in Entry, without opening L_LidarStudy.
Reports are under `Art/Export/LidarStudy/Place/authoringcheck.json` and the temporary
preparation fixtures under `Saved/LidarAuthoringQA`.

LT3 uses the owner's saved 96-point, 713.721 m route. Dirt extends through both
crossings, followed by solid mud, worn climbs, a firmer crest and four different
wet hollows near 214, 290, 552 and 667 m. Local width ranges from 2.215 to 4.334 m.
Ruts vary by section; the whole route is not uniformly churned. Soil depth,
basin depth and standing-water fill are independent. These are provisional
driving-test settings, not measured site depths. Conditions remain editable.
Six fallen logs and thirty mud chunks have simple collision, individual masses
and physics simulation. They can move; this pass does not implement log damage
or mud-chunk fragmentation. The placed rigid bodies use existing study meshes.
The car's trial engine is 480 Nm peak (previously 320), with more low-rev torque;
the 2.5:1 transfer-case reduction is unchanged. This changes the default car in
other maps too. Owner driving remains the acceptance gate.

Run `Art/lidar_place.ps1 -Mode LoggingCheck` after the normal pipeline for saved
pool/collision and river-preservation checks, both-range pulling tests, movable
body checks, a log-contact drive and captures of each hollow.

For this trial, launch `Play-LidarStudy.bat`: you start at the house end of the
saved route. **1** returns there, **V** switches range, **X** switches diff locks,
and **Backspace** reloads a fresh level/vehicle. **2–5** place you before the first
hollow, rutted saddle, wet shelf and deep gully. **6–9** retain the original map
recovery locations. See the LT3 stage log for actual water measurements and test
results. The owner's drive remains the acceptance gate.
