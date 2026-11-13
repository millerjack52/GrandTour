# Painterly mud study

Current art pass: `Art/Export/MudStyleStudy/03/MudStyleStudy.blend` with `Driver.png`
and `SurfaceDetail.png`. Generator: `Art/Blender/build_mud_style_study.py`.
Uses the approved gravel-04 source and tussock shapes/palette. Revision 03 is
now transferred into the Unreal art-test levels; see `MUD_STYLE_IMPORT.md`.
The runtime mud simulation is unchanged.

The visual target separates matte raised earth, darker worked rut floors and
localized shallow water. Broad umber/clay patches and directional paint strokes
replace photographic noise. Dampness lowers roughness only in the low worked
regions; raised areas stay matte. Three flat, irregular pools are clipped against
the preview ground. They are static art geometry, not simulated water.

The study adds a static pair of wandering ruts, low displaced shoulders and buried
soft clod instances (141 in revision 02) from three reusable shapes. Source road collision and vehicle
behaviour are not changed. Smooth analytic ground normals conceal the mesh grid.
The approved gravel blends through an irregular mud-coverage mask, with loose
stones removed from the heavily muddy area. Grass, lighting and review cameras
come from the approved road scene.

The material is driven by separate mud-coverage, wetness and worked-floor masks.
These correspond to information already available in the live system: MudField
height/track coverage and weather wetness. Actual implementation must retain the
live field displacement, its world-space normal derivation, the patch/landscape
boundary matching, and weather controls. The static art ruts and pool surfaces
must not be mistaken for a runtime deformation implementation.

Relevant engine sources: `Art/Unreal/setup_m6_mud.py`, `GTMudPatch` and `GTMudField`.
Existing material history explicitly reduced all-over gloss and disabled regular
tread stripes. This art pass respects that direction: wet highlights are local,
with no repeated ladder-like tread pattern. Any later runtime integration needs
engine captures and appropriate mud/terrain regression checks.

Blender renders use Cycles CPU / four threads. This is an art review, not a GPU
benchmark, physics change or Unreal import.

Revision 01 was visually reviewed and retained for comparison. Its clods looked
too separate and a pool edge appeared raised. Revision 02 subdivides the preview
road before evaluating the surface, reducing the discrepancy between the ground
triangles and pool clipping; reduces clod count, flattens/elongates them and sinks
their bases; and adds a secondary scale of broken clay paint shapes. This preview
subdivision does not change the runtime mud-field resolution.
Pool review also caught a clipped water edge above the basin rim. Local preview
basins now contain the water, with each level limited below its sampled rim; the
pre-fix renders are retained in `02/BeforePoolFix`.

Revision 03 follows the supplied ochre clay sphere reference: warmer restrained
earth tones, broad irregular plate faces, interrupted shallow ledges and sparse
embedded gravel. Warped 2D cells provide the face variation and edge normals;
small noise only chips the boundaries. Plate relief fades by 93% in the worked
rut floors. Clods have angular faces rather than smooth pebble-like shading.
The pool basins, rut geometry, cameras and lighting remain those of revision 02
for direct comparison. This is a material/art preview, not an Unreal import.
Each version retains a generator snapshot under its `source` directory.

The first revision-03 render made the plate network too continuous and the
retained gravel too pale. The final pass gates the edges with a separate mask,
softens their relief and coats the retained stone palette with earth tones.
The initial images and generator are retained in `03/BeforeEdgeRefinement`.
