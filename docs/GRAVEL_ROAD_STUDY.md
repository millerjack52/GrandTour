# Gravel road shape and scale study

The Blender studies below were reviewed before import. Revision 04 was then
approved for Unreal integration; see `docs/GRAVEL_ROAD_IMPORT.md` for maps,
rebuild steps, engine checks and limitations. The earlier study renders remain
available for comparison.

Source: `Art/Blender/build_gravel_road_study.py` and
`Art/Blender/gravel_road_material.py`. Output:
`Art/Export/GravelRoadStudy/04/GravelRoadStudy.blend`, `Driver.png`, and
`SurfaceDetail.png`. Earlier versions and their scripts are preserved under `01`
through `03`.

The 26 m review section uses the existing road and verge geometry, the accepted
tussock models, and the existing continuous meadow/wetness masks. Camera positions,
lighting and grass stay the same between revisions so the road change is visible.
Renders use Cycles CPU with four threads; these are not Unreal performance checks.

## Revision 02: coarser gravel with actual relief

The owner found revision 01 too flat and its detail too fine. The coarse texture
tile now spans 5.4 m instead of 1.8 m, making individual aggregate features three
times larger. The fine layer spans 2.4 m instead of 1.35 m. Colour and normal maps
share coordinates at each scale. Normal relief and stone/joint colour contrast
are increased; compacted wheel paths retain a blend of both layers.

Four reusable angular pebble meshes have 33/38/33/38 triangles. Most placement
width parameters are 3.2–8.7 cm, with occasional 9–13 cm shoulder stones and varied
aspect ratios. These are nominal scale parameters; actual widths depend on the
prototype bounds. Their raised crowns produce real silhouettes and shadows.
Placement concentrates stones along the centre and shoulders with broken patches,
and removes most stones from wheel paths. These are intended for instancing with
no individual physics bodies, not separate engine actors.

Shallow centre and shoulder gravel ridges add up to approximately 3.6 cm of broad
relief in the Blender review. Analytic smooth normals conceal the terrain grid.
The modified review ground is saved in the blend; only the four pebble prototypes
are currently exported as FBX. Any subsequent engine integration must transfer
the material, placement data and chosen ground treatment together and benchmark
their cost. No engine performance or driving-behaviour claim is made.

Texture inputs reuse the existing CC0 Poly Haven Gravel Floor 02/04 assets.
Provenance: `Art/Textures/RoadBenchmark/SOURCE.txt`. Source image files are
unmodified; the Blender material remaps their values to a restrained grey palette.

## Revision 03: stylized surface

The owner accepted the larger aggregate and relief but requested more stylization.
The road now uses procedural stone faces instead of photographic gravel colour
and normal maps. Five related slate, warm-grey and limestone colours cover broad
angular stone centres, with shallow bevelled edges and restrained directional
paint marks. The first revision-03 render used round crowns; close-up review
showed a bead-like pattern, so the final surface uses irregular polygon boundaries
and reduced bump depth. Coverage gaps and varied chip sizes then break up the
continuous cells so they do not read as paving. Rejected images are preserved
under `03/RoundedDraft` and `03/PolygonDraft`.
Wheel paths, raised ridges, stone placement and camera/lighting are retained from
revision 02. The loose-stone mesh palette matches the surface more closely and
its face-to-face colour variation is reduced.

The meadow and moisture transitions remain in place. Existing bank textures
still use their original materials. This Blender procedural road shader needs
texture baking or a deliberate Unreal material port before integration; FBX alone
does not transfer the surface. No full-screen painterly filter is involved.

## Revision 04: fuller painted base

The owner found revision 03 closer stylistically, but the base lacked some detail.
A secondary layer of smaller embedded chips now fills the spaces between larger
stones. It uses 34 cells per metre versus 13 for the broad faces, four restrained
colours, and shallow 2 mm / 0.3-strength bump. The broad stone coverage suppresses
this smaller relief so large faces remain quiet. Directional paint marks are
slightly stronger. Geometry, stone placements, palette of the larger stones,
lighting and cameras are unchanged. No photographic texture noise or screen-space
filter has been reintroduced. The same Blender-only/import limitations apply.
