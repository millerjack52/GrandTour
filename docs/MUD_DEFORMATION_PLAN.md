# Mud deformation plan, MudRunner-style (2026-09-15)

The user asked for something like the mud of Spintires / MudRunner after the second bog retune, pointing at
Pavel Zagrebelnyy's breakdown (gamedeveloper.com "Mud and water of Spintires: MudRunner", mirrored on 80.lv).
This is what that technique is, what the project already has of it, and the stages to build the rest, each with
a headless check and a look before the feel test.

## What MudRunner does (from the article)

- The level (up to 1 x 1 km) is a grid of 16 m blocks. Only the blocks near the truck are "active": mud, water and
  plant simulation run there only.
- Mud is a heightfield. Per block, a 25 x 25 texture holds the base terrain (packed height, a two-material mix, a
  tint that also marks softer ground, and an alpha that "marks portions of base terrain that are substituted by the
  mud", the one channel updated as vehicles deform it). Mud blocks add a 128 x 128 texture (12.5 cm a texel): R is
  the mud height relative to the base terrain, GB a horizontal "mud offset" so "the mud slides away from vehicles
  wheels as they move", A the "mud tracks" factor that blends the terrain shader into the mud shader.
- The CPU knows the wheels' and chassis' positions, sizes, velocities and penetration depths and "forms various
  'primitives' and draws them" into that texture. The author calls the primitives "pure empirics" with "very vague
  connection to real world physics".
- Rendering and physics "operate on completely different sets of data": the vertex shader takes "a simple 2d grid
  of vertices" and fetches the two textures; the pixel shader "simply blends few diffuse textures based on the normal
  which it derives from the heightfield data". Most of the terrain renders at lower resolution; the deformed mud at
  full.
- Water is another heightfield mesh from rivers drawn as curves, a flow texture per block, five scrolled wave layers,
  and a GPU propagation pass over two ping-ponged textures into which the CPU draws the wheels' primitives (foam,
  height, mud in the water). Mud particles float on the mud, decorative only, simulated on a thread.

## What GrandTour already has of it

- `UGTTrackPaintSubsystem` is the CPU-draws-primitives half: each wheel stamps a capsule of its width and a strength
  into a 2048 x 2048 render target over a 128 m window that follows the car (6.25 cm a texel), and into a CPU cell
  grid the physics reads (`SampleDepth`). The window recentres by shifting its content; what leaves it is gone.
- `MF_TrackPaint` is the render half in miniature: it samples the target at the pixel's world XY and outputs RutDepth,
  a finite-difference normal and a Displacement that `setup_m1_trackpaint.py` wires to world position offset on
  M_GT_Environment (the greybox master); M_GT_Landscape takes the ruts as colour and normal.
- The physics is already separate from the rendering, as in MudRunner: sinkage per wheel from the surface's numbers
  (`UGTTractionComponent`), the wheel radius shrunk by it so the body drops (`UGTVehicleTuningComponent`), drag, grip
  loss and the rut ease from the CPU grid, the belly as drag. Nothing in the physics reads the render target.
- The bog itself: a Mud route section, the Bog layer down its middle, hummocks and a fixed rut pair in the landscape.

## What is missing

1. A mud surface with volume: the stamp only darkens and dips; nothing rises beside the wheel and nothing slides
   away, so a rut is a groove in paint, not mud pushed aside.
2. A render mesh fine enough to show it: the landscape is 1 m quads, and a 75 cm rut on 1 m vertices is a broad
   dip. MudRunner draws its mud on 12.5 cm texels over a fine grid.
3. Persistence: the paint window forgets ruts 64 m behind the car; MudRunner keeps every block's mud for the session.
4. The base terrain hidden where the mud is: a rut that dips below the landscape's surface is cut off by it.
5. The physics reading the mud surface inside a bog (ruts that hold the car, a belly that flattens mud) instead of
   the paint window.

## The design

The MudRunner split kept: a CPU mud field per bog that the wheels and the belly draw into and the physics reads, a
texture built from it, and a fine flat grid mesh per bog whose vertex shader reads the texture. No collision
changes, no mesh recooking: the wheels keep sweeping the landscape and the sinkage model keeps dropping the car. (The
earlier idea of a dynamic mesh with recooked collision is dropped: it is the expensive path and the reference did not
take it.)

### Stage A: the mud field (about a day)
*Built and headless-verified 2026-09-15 (VEHICLE_BUILD_SYSTEM.md section 27): `FGTMudField`, `AGTMudPatch`,
`UGTMudSubsystem`, the stamps from `UGTTractionComponent::StampMud`, the terrain test's step 10. One patch over The
Hide's bog; ruts to the sinkage (-34.5 cm mean of 40), ridges 7.9 cm, tracks, a second pass down a line lowers nothing.
Two things the plan did not say: the belly stamps a box inset 40 cm from the contacts, and on a curving line the rears
cut their own ruts beside the fronts'. Nothing visible yet.*
- `FGTMudField` owned by a new `AGTMudPatch` actor, one per Mud section, spawned by `AGTTerrainBuilder` at rebuild
  over the section's painted footprint plus a 2 m margin (the trough is read from the layer weights, not the section
  half width, since the bog layer widens with its pockets). A CPU grid at 12.5 cm: mud height in cm relative to the
  landscape (negative in a rut, positive on a ridge), a 2D offset in cm, a tracks factor 0..1. The Hide's bog, 50 m by
  about 20 m, is 400 x 160 cells.
- Primitives, drawn each physics tick from the traction's numbers: per wheel a capsule from the last contact to this
  one, the tyre's width, lowered to the wheel's sinkage (the field never goes below the surface's max sinkage); the
  volume lowered is pushed into two ridges beside it (a raised cosine 40 cm wide, its height set so about 60 % of the
  volume returns: mud compacts) and the offset channel is pushed outward from the wheel by a fraction of its lateral
  and forward travel, decaying over 60 cm; the belly, when the sinkage is past `AxleClearanceM`, a box of the track
  width between the axles flattened to the axle depth (a smear, no ridges). The tracks factor rises to 1 under any
  primitive and stays.
- Persistence: the field lives with the patch actor for the leg. No drying in this stage (MudRunner has none).
- Upload: dirty 16 m blocks are copied into an `R16G16B16A16F` `UTexture2D` per patch with `UpdateTextureRegions`
  each frame there is a change (no render-target readback anywhere).
- Test (`Art/mud_field_test.bat` or a step in the terrain test): drive the bog's middle; sample the field under the
  track: rut depth at least 60 % of the wheel's max sinkage, a ridge on both sides at least 5 cm above the surface,
  the tracks factor 1 under the wheels and 0 five metres off; a second drive along the same line lowers the field
  by less than the first (compacted).

### Stage B: the mud mesh and its material (one to two days)
*Built and headless-verified 2026-09-15 (VEHICLE_BUILD_SYSTEM.md section 28): the grid mesh on `AGTMudPatch`,
`M_GT_Mud` from `Art/setup_m6_mud.bat`, the landscape's hole under the mesh in `setup_m6_hide.py` (a pixel depth offset until
section 30's addendum: pushed back 100 cm, the sheet floated in front of the dirt from eye height), the picture
`hide_12_mud_diag` from `Art/hide_shots.bat` sampled by `Art/tools/sample_mud_diag.ps1`. Three things the plan did not
say: the mesh is masked where the field is untouched (an opaque rectangle over the bog would show its edges against
the layer blend), the patch boxes ride in `MPC_TrackPaint` (a material may reference two collections and the landscape
has weather and track paint), and the picture's crawl is its own (the sunk car of the earlier picture hides its ruts
from above). The look is the layer colours until the texture pass; not looked at by the user.*
- A flat grid mesh per patch at 25 cm (`UProceduralMeshComponent`, no collision), its vertices at the landscape's
  height at rebuild so it coincides with the ground at rest, 2 cm up. Its material `M_GT_Mud` reads the patch's
  texture in the vertex shader: Z from the mud height, XY from the offset; the pixel shader derives the normal from the
  height by finite difference (as `MF_TrackPaint` does), blends the mud look over the ground look by the tracks
  factor, and reads the weather's wetness for the sheen. The landscape is masked out (a hole) exactly where the mesh
  draws, from the patches' field textures through its dynamic material instances, so the mesh is the ground there
  (the base terrain "substituted by the mud"; a pixel depth offset under the patch until 2026-09-15, which let the
  sheet float in front of the dirt from eye height).
- `Art/hide_shots.bat` gains a picture of the bog from 40 m above after the test's drive, with a diagnostic
  colour on the mud material (height as a colour ramp) switchable by a material parameter, so the ruts and ridges are
  judged by pixel sampling: the rut band darker than the surface, the ridges lighter, the fixed rut pair and the
  hummocks visible as shape in the same picture.
- Test: the picture's samples as above; the mesh's vertex count and bounds; the material compiles off-screen
  (`-RenderOffScreen` with the probe).

### Stage C: the physics reads the field (about a day)
- Inside a patch the traction reads the field instead of the paint window: the rut depth ahead (the rut ease and
  the drop-in as now), and a new cross-slope of the rut under each wheel (the field's gradient across the heading),
  which adds a lateral drag when the wheel is steered out of its rut: ruts hold the car, and following your own line
  is the easy way through. The belly's flattening lowers the belly drag on a second pass (a channel already cut).
- The paint window keeps doing dirt and snow tracks; bogs no longer stamp it (the field is the record).
- Test: the terrain test's escape step gains a second forward pass down the first pass's ruts, faster than the first;
  a sideways exit at 30 degrees to the ruts is slower than straight on.
- BUILT 2026-09-15 (VEHICLE_BUILD_SYSTEM 29). As planned, with two readings made concrete: the rut ahead is read where
  the tyre is heading (the chassis heading turned by the wheel's steer), the deepest of three probes across the tyre,
  and the "cross-slope" is the field's gradient at that point split into a climb along the heading (extra drag,
  `RutHoldDrag`) and a slope across it (a push at the contact back into the rut, `RutHoldLateral`), both weighted by
  the tracks factor so untouched mud never holds, both clamped (`RutHoldMaxSlope`: a stamp's wall is a step). The
  belly reads its channel just ahead of its box (`BellyChannelEase`). The passes live in their own terrain test step
  after the field check so the stage A checks cannot be eroded by them. Headless-verified, not felt.

### Later, not in this plan
- Water like MudRunner's: a propagation pass over the ford's sheet with the wheels' primitives (foam, waves, mud in
  the water) and a flow texture from the generator. The sheet stays a level for now.
- Mud particles and spray from the field's motion (the spray system exists; it does not read the field).
- Drying: the field relaxing toward zero over a leg's weather; weather fronts writing mud height into a patch.
- Deformation outside bogs (dirt and snow stay paint), and the landscape carrying the field on Nanite displacement
  when the art pass decides on Nanite landscape.

## Numbers and limits
- Field 12.5 cm, mesh 25 cm, texture per patch 400 x 160 texels for The Hide's bog (about 0.5 MB), one draw call.
- Primitives are empirics, as MudRunner's: no volume solver. The chassis never physically rests on a ridge; the
  belly stays a number in the traction, which is also how the reference's physics sat beside its rendering.
- The wheel radius trick stays the physics of sinking. The drawn wheel and the mesh's rut agree because both follow
  the same sinkage.
- Cost: A one day, B one to two, C one; each stage headless-checked and looked at before the user feels it.

*Continued by docs/MUD_ONE_SURFACE_PLAN.md (2026-09-15, stages D-H: one surface, the mud texture, tread, water in the ruts, smoothness), written for implementing agents after the user judged the hole "better, but not MudRunner/Spintires".*
