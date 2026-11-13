# MudRunner lessons: the world reacts to mud (plan for implementing agents)

Written 2026-10-07 from the owner's ask: "I would like to improve on it with some lessons from mudrunner", with a link
to the Spintires/MudRunner developer's article "Mud and water of Spintires: MudRunner" (gamedeveloper.com, 2017).
The owner's choices the same day: build all six lessons below, **the world-reacting ones first**.

## 0. Rules for the agent

Everything in `docs/LIVING_MUD_PLAN.md` section 0 and `docs/MUD_ONE_SURFACE_PLAN.md` section 0 holds. On top of that,
the owner's standing rules (from the 2026-10-05/06 sessions):

- **Performance is the owner's to test.** Run no cost, timing or profiling measurements. Every feature gets a console
  switch (default on), and its stage note lists them, so the owner can A/B. Functional runs are fine: drive checks for
  completion and pictures, tests, builds.
- **Games.** Check `Get-Process GoWR,GoW,FarCry6` before each run. If a game is running, builds, headless Blender,
  setups, imports and CPU tests may run: use a wrapper's command line directly if its guard refuses, and say so. Drive
  checks and `suite.sh` are cancelled, without asking or waiting, and listed as owed. Never close a game.
- **Foreign Unreal.** The OpenAI Codex app runs Unreal in this project. Before every Unreal or UBT run, check for
  UnrealEditor/UnrealEditor-Cmd you didn't start, and wait for it with a background PowerShell wait loop and its
  notification, never sleep-polling. Give up after 20 min and report. Never run two Unreal processes yourself.
- **The owner's look rejections** (memory: terrain look rejections): regular lines or stripes, too smooth, very
  uniform (evenly spaced, same size), blocky, tall walls, flat planes, swirls or marbling, pebble or cobble mosaics.
  Every new look is checked against that list. The target is clustered, irregular and lumpy, in the painterly style
  of the approved bakes. Never say how something looks from code; describe what the pictures contain.
- **Assets.** Painterly bakes come from headless Blender scripts in the style-study workflow (no downloads, nothing
  hand-painted). Procedural meshes are fine. Never model car bodies or characters.
- **Tests.** Every GrandTour.Mud and GrandTour.Snow test keeps passing, and the mud field CRC stays 8e0aad06 unless a
  stage changes the field on purpose (then report it).
- **Docs per stage.** VEHICLE_BUILD_SYSTEM (the next free section), the devlog, the BACKLOG line, and an italic Done
  note under the stage's heading here. Commit only the stage's files (never `git add -A`), ending with the attribution
  line. Don't push.
- **Read list for a fresh agent**: this file; `docs/LIVING_MUD_PLAN.md` section 0; `docs/MUD_VARIANTS.md`; and the
  sources each stage names, read by `grep -n` and `sed -n` ranges.

## 1. What MudRunner does that we don't (from the article)

The article's mud grid is 128x128 per 16 m block: **12.5 cm, exactly our cell**. Its "mud slides away from the
wheels" offset is our `OffsetCm`. The differences that matter:

1. **Mud replaces base terrain dynamically.** A channel marks where base terrain is substituted by mud, and "it's the
   only channel that is dynamically updated as vehicles deform terrain". Mud decals (oriented boxes, z-projected) go
   on roads and rocks, plus wet decals. Ours stops dead at the patch box, and thrown mud landing outside it vanishes.
2. **Mud particles stick to things.** "Those objects float on top of the mud and are affected by vehicle wheels (can
   stick to them even)", and they "affect per-vertex mud data of most of the environmental assets": plants and rocks
   get muddy.
3. **The tint channel telegraphs softness.** "'tinted' terrain is softer": the player reads the ground.
4. **Mud chunks** are "full-fledged rigid bodies", and "they even break into smaller chunks, when vehicles drive over".
5. **Water carries mud.** The water simulation propagates "foam, water, height and mud parameters" each frame from
   wheel and chassis primitives.

## 2. What exists to build on

- **Track paint** (`UGTTrackPaintSubsystem`): a 2048 world-aligned render target over 128 m round the car, 6.25 cm
  texels, R = rut depth, scrolled by whole texels and decayed every 0.5 s (`FadeSeconds` 120), mirrored on a 256 CPU
  grid for gameplay and tests. `MPC_TrackPaint` carries TrackOrigin. `MF_TrackPaint` reads it in the environment and
  landscape masters.
- **Car dirt** (`UGTBodyStateComponent`): per-region `Dirt` (`MudDirtRate` 0.15/s, `DustDirtRate`), and the Grime node
  in `M_GT_Vehicle` (Dirt, DirtColour, DirtBottomZ, DirtHeight: a flat colour fading up from the sills in car space,
  through MF_Weather; clear coat reduced under dirt; the painted path behind UsePaint). `M_GT_Glass` has Dirt.
  `UGTBodyComponent` pushes Dirt per panel.
- **Water**: fords run `FGTWaterField`, a virtual-pipe shallow-water solver with face fluxes (velocity), wheel and hull
  lids, and sources and sinks at the flow-wise ends, drawn by `AGTWaterSheet` / `M_GT_Water`. Rut water is per-cell
  in the mud field (`WaterTableCm`), drawn by the patch's water mesh with `M_GT_MudWater`.
- **Spray** (`UGTSprayComponent`): CPU blobs; LM2a's throw blobs carry volume and land into patches via
  `DepositThrown`. Blobs landing outside every patch currently lose their volume.
- **Variants** (LM5b): `TA_MS_Bog{Color,Normal,Rough,Height}` texture arrays, slice = variant; `MPC_TrackPaint`
  `PatchVariant0..3`.
- **Clods** (LM2b/LM2c): HISM per patch, 10 variants in four families, per-instance freshness.

## 3. Stages, in the owner's order (the world reacts first)

### MR1: mud leaves the bog (carried mud, splats, muddy grass)

*Done 2026-10-08 (VEHICLE_BUILD_SYSTEM 79, docs/MUD_VARIANTS.md "Carried mud, splats, muddy grass"; no cost or timing measured). All eight items built. RT_TrackPaint stays RGBA16f (R the ruts bit for bit; a rut stamp no longer copies into G and B). Switches gt.Mud.Carry, gt.Mud.Splats, gt.Mud.GrassMud (and the static switch GrassMud). GrandTour.Mud.Carry: rise 0.600/0.600, shed 0.498 at 15 m, wash 0.500 at 2 m, a 50 m exit falling 0.567 / 0.179 / 0.086 / 0.045 / 0.028 by 10 m with 45.0 % gaps, a splat only inside its reach, G 598 s and B 90 s to 1/e; 11 of 11 Mud and Snow tests, CRC 8e0aad06. Departures: a blob is traced inside a patch's box too, for meshes only (the box reaches 2 m past the mud, so every post beside a section is in one); the grass reads G at the blade's XY (the tussocks are 1-2.5 m clumps) and mud reaches an absolute 18-30 cm; the load sheds by the chassis's ground speed. Found and fixed: LM5b's LiveApronRoughness read the weather's BaseColor as roughness (mirror-shiny strip ground). Found: at Deep's 60 cm sinkage LM2a's blobs leave from the sunk contact and land within about half a metre, so a spin-up reaches a post only a little way behind the tyre (2 decals from 484 blobs). Pictures: Carry_Exit and Splat_Post seen in a clean run; the bigger blots (1.8-2.8 widths) and muddy grass owed a clean picture (GoWR was running for the last drives, which timed out at 98.96 and 97.35 m). The terrain rerun alone (GoWR running, no foreign Unreal): PASS, escape forward 9.0 m in 12 s, the held 30-degree exit slower than down the ruts.*

1. **Mud load per wheel.** `FGTWheelTraction::MudLoad` (0..1):
   - In a mud patch it rises at `MudLoadRate` 0.6 /s x (0.5 + sinkage fraction) x (1 + slip share).
   - On firm ground it falls by distance, half-life `MudShedHalfM` 15 m.
   - In water deeper than 5 cm it washes, half-life 2 m.
   - In snow patches it stays 0 (snow carries nothing in this stage).
2. **Carried tracks.** A wheel outside every patch with `MudLoad` over 0.02 paints into track paint:
   - **G = mud coverage**, at MudLoad x 0.8, across its width.
   - **B = wetness**, 1.
   - Each stamp is a clumpy brush (an atlas of irregular painterly blots from the splat bake below), rotated randomly
     and jittered across the tyre, so the trail breaks up and thins, with no regular stripes.
   - The format: if the target is single-channel today, it becomes RGBA (8- or 16-bit, your choice; say which) and
     scrolls and decays per channel. **Coverage fades over `MudFadeSeconds` 600; wetness over `MudDrySeconds` 90.**
   - The CPU grid mirrors G and B for the tests.
3. **Splats.** A throw blob (LM2a) whose path leaves every patch is traced against the world: one short line trace per
   blob per frame, only for volume-carrying blobs, capped at 64 traces a frame.
   - **On landscape**, it paints a splat into G and B: radius 2-3x the blob's, a random blot from the atlas.
   - **On a static mesh** (rock, post, dressing, road mesh), it spawns a pooled deferred decal: at most 96 alive,
     oldest first out. It's a mud-splat decal material using the atlas, with colour from the Standard bog slice, wet
     to dry over 90 s, faded out over 600 s.
   - Blobs hitting the car are MR2's.
4. **The splat atlas.** `Art/Blender/build_mud_splats.py`, headless, in the style-study language: 16 irregular blots,
   splatters with flung droplets, and drag smears, as a 2048 atlas (4x4) of mask, height and normal. Painterly
   shapes. No lines, no repeats within the atlas, no swirls.
5. **Materials.**
   - **Ground** (landscape masters, M_GT_Environment and the strips' landscape materials, through MF_TrackPaint or a
     sibling MF_MudCover): where G > 0, the ground goes toward the Standard bog slice. The coverage edge is ragged (G x
     the bog's height map, then a threshold with a soft step). B gives wet (dark, glossy) versus dried (lighter,
     matte). The ruts' R depth stays as it is.
   - **Grass** (the GT tussock and grass copies in use on the strips and The Hide; find them): the lower 30-50 % of
     the blades darken toward dried mud by G at the instance's world position, plus a speckle. Behind a material
     switch.
6. **Switches**: `gt.Mud.Carry`, `gt.Mud.Splats`, `gt.Mud.GrassMud`.
7. **Tests** (`GrandTour.Mud.Carry`, CPU):
   - MudLoad's rise in a patch, its shed over distance (half at 15 m within 10 %), and its wash in water;
   - the grid's G along a 50 m exit: decreasing, with at least 20 % gaps (broken, not a solid band);
   - decay and drying times within 10 %;
   - a splat on landscape adds G only in its radius;
   - every Mud and Snow test passes, and the field CRC is unchanged.
8. **Pictures** (an `MR1` phase in the L_MudVariants check):
   - `Carry_Exit.png`: the car parked 30 m past the Stony section's exit, looking back at the carried tracks;
   - `Carry_Grass.png`: a wheel driven over a grass verge;
   - `Splat_Post.png`: a post or rock beside the Deep section after a spin-up.
   Describe them; no timing.

### MR2: a muddy vehicle

**MR1 housekeeping first (main session, 2026-10-08, from MR1's report):**

1. **Carried tracks must not read as dotted lines.** The only clean `Carry_Exit` showed "two thin dotted tracks of
   small dark specks", which is the regular-pattern rejection. Stamp by distance, not by frame:
   - blots overlap, with spacing at most 0.6x the blot radius;
   - each blot's size, rotation and offset are jittered;
   - strength is modulated along the track by a 1-3 m noise, so the trail breaks into smears and gaps, not beads.
   Add a `GrandTour.Mud.Carry` row: along a 30 m exit, G's autocorrelation at lags of 1-10 blot spacings shows no peak
   over 0.3. Then retake `Carry_Exit`.
2. **Muddy grass must be seen.** Take `Carry_Grass` at 1-2 m from a verge a muddy wheel has crossed, and describe the
   blades' feet. If nothing shows, find why (the coverage at the blades, the switch, the material path) and fix it.
3. **The black square decal.** In the GoWR rerun the post's decal drew as one black, hard-edged square. Find the cause
   (a missing texture or slice, a decal size or projection fault, the material domain or blend, a cast in the decal
   pool) and fix it. Retake `Splat_Post`.
4. **The trace budget.** 77,370 traces were refused in one run at 64 a frame. Trace only volume-carrying blobs that are
   descending and within an estimated 1 m of a surface (patch surface or landscape height below them). Give the
   landscape path a cheap height test without a trace. Raise the cap to 128 if needed. Report refusals per second
   after the change.

*Housekeeping done 2026-10-08 (VEHICLE_BUILD_SYSTEM 80). 1: carried blots stamped by distance at 0.3-0.6 x the smallest blot's reach at the load, the strength along the track from a two-octave hashed noise (230 / 110 cm) through a gap threshold that rises as the load runs out; a second cause in the ground: MF_MudCover's edge G x (0.25 + 1.5 h) let a track's moderate G through only on the bog's lumps (the specks), now G x (0.5 + h three mips down + 0.3 (h - 0.5)). GrandTour.Mud.Carry: a 30 m exit, lags 1-4 cells (25 cm; blot spacing 7.5 cm): r 0.92 / 0.90 / 0.87 / 0.83, no peak (MR1's stamping peaked 0.40 at 75 cm in a Python model of the grid); the 50 m row now asks the track to thin (no 10 m bin over the first, the last 20 m under a third of the first 20 m, the last bin under half the first; "monotone" reported: yes). Clean run: the exit's G per 5 m 0.43 / 0.33 / 0.22 / 0.15 / 0.12 left, gaps 4.1 % (MR1 0.30 / 0.16 / 0.05 / 0.02 / 0.02, 59.8 %). 2: the grass measured its mud line from the ISM component's origin (a pixel shader's ObjectPositionWS; on the strips the ground is 34 cm above it), and its mud was the straw's own brown: the origin now comes through a vertex interpolator, the mud is the bog's mean colour; a diagnosis (line raised to 4 m, mud blue) turned the blades over carried mud blue and only them; Carry_Grass / Carry_Grass_Off: the clump's feet darker (mean 78.5 vs 86.9 of 255 at the feet, unchanged above). 3: the black square was the engine's fallback decal material (DefaultDeferredDecalMaterial, unlit and opaque over the decal's box) drawn while M_GT_MudSplatDecal's shaders compiled; a decal now waits hidden until the shader map is complete, and the editor is asked for the jobs (a hidden decal never draws, so nothing else asks: the first fix alone left 24 decals waiting a whole run); no black square since. 4: traced only while descending within 1 m of the surface under it (a patch's field, or the landscape's height from a heightfield lookup, no trace); a blob under the landscape's height splats there without a trace; cap kept at 64. Refused: MR1's clean run 77,370 of 208,959 traces (about 480 a second over a run of this length); MR2's clean run 17,674 of 134,097 in 157.7 s of play, 112 a second (2.3 a frame at 48 frames a second), 63,744 blob-frames skipped by the band, 12 splats by the height test.*

The drive check runs even with a game open (the owner's rule since 2026-10-08). Under GoWR the drive stalled at about
98 m in Standard twice, so if that happens again, report it, and take the MR1 and MR2 pictures from a scripted pass
that teleports the car between sections instead of driving the whole strip.

1. **The state** (on `UGTBodyStateComponent`, extending the per-region Dirt):
   - per-region **MudCoat** (0..1; the existing Dirt can carry it if that's cleaner, say which);
   - a per-car **MudLineCm** (how high the mud reaches above the wheel bottoms: the max over the last 10 s of
     sinkage + water depth + 20 cm, plus 30 cm while spinning);
   - **MudWet** (1 when fresh, drying to 0 over 90 s; rain keeps it at least the rain's wetness);
   - per wheel **TyreCoat**.
2. **Sources:**
   - a wheel in a mud patch: TyreCoat up fast (full within about 2 s);
   - the sills and bumper regions up by speed x sinkage;
   - spinning flings mud: the front wheels feed the front bumper and front sides, the rears feed the rear and back
     sides, by slip;
   - a throw blob hitting the body: a line trace against the car's own body (capped, as MR1), adding to that region
     and setting MudWet 1;
   - belly drag (deep mud): the underside and sills to MudLineCm;
   - MR1's MudLoad also keeps the tyres coated.
3. **Removal:**
   - water: regions below the water level wash at 0.3 /s while moving, 0.1 /s still; tyres at 0.5 /s;
   - rain: 0.01 /s x rain;
   - dried mud stays until washed.
4. **The material** (`setup_m1_body.py` / `M_GT_Vehicle`, `M_GT_Glass`, and the tyre material; find which one the
   wheels wear):
   - The Grime node's flat DirtColour becomes the Standard bog slice (colour, normal, roughness), sampled tri-planar
     in car space at about 1 m.
   - Its height gradient becomes a mud line at MudLineCm (car space Z above the wheel bottoms), broken by a car-space
     **splatter mask**: a tileable painterly splatter, droplets and drips baked by `build_mud_splats.py` as a second
     output. So the edge is splattered, never a smooth gradient.
   - MudCoat scales coverage up to and above the line (thrown splats reach higher at lower density).
   - MudWet: wet means darker and glossy (roughness about 0.3), dry means lighter and matte (about 0.9).
   - The clear coat reduced under mud as now. The painted path (UsePaint 1) and the plain path both get it.
   - **Tyres**: caked in mud by TyreCoat in the treads first (darker, matte when dry).
   - **Glass**: the existing Dirt on the windscreen from throw hits only, as splats.
5. **Switch**: `gt.Mud.CarMud`.
6. **Tests** (`GrandTour.Mud.CarMud`, CPU, on the state component):
   - 3 s in mud brings the tyres to at least 0.9 and the sills to at least 0.5, with the roof at 0;
   - spin feeds the arches by axle;
   - water washes below the waterline only;
   - drying takes 90 s within 10 %;
   - rain washes.
7. **Pictures**:
   - `Car_Muddy_Side.png` and `Car_Muddy_Rear.png` after L_MudVariants' drive;
   - `Car_Washed.png` after L_MudDrive's ford, with only below the waterline clean.

*Done 2026-10-08 (VEHICLE_BUILD_SYSTEM 80, docs/MUD_VARIANTS.md "The muddy car"; no cost or timing measured). All seven items built. State: the per-region Dirt carries MudCoat (dust still adds to it); TyreCoat per wheel; MudLineCm the most over 10 s of the deeper of the sinkage and the water at a wheel (the water is measured over the sunk contact, so it holds the sinkage: their sum put the coat at 156 cm in Deep's rut water) + 20, + 30 while spinning; departure: the material draws CoatLineCm, MudLineCm's high mark while mud is laid, lowered only by a wash (as asked the line falls back 10 s after the mud, which would wipe dried mud off); MudWet; WashCm / WashAmount. Sources as asked, mud being the Mud/Bog surface (a ford's riverbed, a profiled patch on Dirt the traction flags too, re-coated the car leaving the water); blob hits traced against the car's own collision, rising blobs inside its bounds only, 32 a frame: a face hit sticks, an underside hit coats and drops back (consumed, 56 % of a spin-up's throw never reached the bog). Removal as asked; a bog's rut water does not wash (FGTWheelTraction::bRutWater, new), and MR1's load now washes in a ford's water over its riverbed patch. Material: the Grime node behind CarMud (0 = before MR2 exactly): the Standard slice tri-planar in car space at 100 cm, its colour, roughness and normal 3 mips down (sharp, the bake's lumps read as glued pebbles), the coat blended across the body from the regions (no panel seams), the line broken by the bog's height, the splatter, a 7 m-tile wave (22 cm) and lifted 18 cm round the wheels, droplets above over 80 cm, the washed band, wet/dry, the clear coat thinned, both paths; M_GT_Tyre on the wheels' M_Wheel slot (it drew WorldGridMaterial), caked treads first in the wheel's rest pose; M_GT_Glass splats (no windscreen is built on the driven car). Switch gt.Mud.CarMud. GrandTour.Mud.CarMud: tyres 0.976, sills 0.585, roof 0 after 3 s; spin feeds front or rear arches only; 50 cm of water: clean at 30 cm, untouched at 80 cm; dry at 90.0 s; rain 0.100 in 10 s; 12 of 12 Mud and Snow tests, CRC 8e0aad06. Pictures: Car_Muddy_Side / Rear - a mottled coat below a line rising and falling in tongues, droplets and drips above, caked tyres: splattered, not a band (the droplets above are dense and even over the doors); Car_Washed (L_MudDrive's ford, GoWR open) - a clean band to about 55 cm, tyres clean, the coat above; its top edge a nearly level waterline. Suite 7 PASS, terrain FAIL twice at step 11's held exit (also with gt.Mud.CarMud 0). With GoWR open the drives stalled; the scripted pass took the pictures.*

### MR2b: splatter with structure (main session, 2026-10-08, after looking at MR2's `Car_Muddy_Side.png`)

**What the picture shows:**
- The coat's top edge is a row of rounded tongues with **vertical sides**, like a city skyline: blocky.
- Above it, dark round droplets with drips are spread **evenly over both doors and the pillars**: polka dots, which is
  "very uniform".
- The caked tyres and the mottled coat below read well and stay.

**On a MudRunner truck**, mud is structured by the wheels: fans of spray thrown up and back from each arch, densest
just behind and above it, thinning with distance; a mud line that rises over the arches and dips between them, its
edge jagged and sloped, never vertical-walled.

1. **Wheel fans.** Per wheel, a `FanCoat` (0..1) fed by that wheel's spin and its speed through mud, washed like the
   rest.
   - The material builds a fan mask per arch in car space: an annular sector from the arch centre, opening up and
     back (back = away from the direction of the wheel's last spin: forward spin throws backward). Its density falls
     with distance from the arch (about 1.2 m reach) and its edges are broken by noise.
   - `T_MudSplat_Splatter`'s droplets and drips show only by that density times FanCoat, plus a sparse baseline
     (0.1x) elsewhere.
   - Four fan parameters go to the panels the way Dirt does today.
2. **The mud line's edge.**
   - The coat line's height along car X becomes a two-octave noise at 25 and 80 cm, plus a rise of about 15 cm over
     each arch, joined by slopes (the line's slope capped at about 1.5, so no vertical walls).
   - The edge is broken at two scales by the splatter mask and a fine noise, so it's jagged rather than rounded
     tongues.
   - The coat below stays as it is.
3. **No uniform spots.** In `Car_Muddy_Side`, droplet density in the arch fans must be at least 3x the density
   mid-door, measured from the picture's dark-spot count in boxes behind the rear arch and mid-door.
4. **The clean picture set.** Retake every MR1/MR2 picture in one run with no game open, if possible:
   - Carry_Exit, Carry_Grass, Carry_Grass_Off, Splat_Post;
   - Car_Muddy_Side, Car_Muddy_Rear, Car_Washed.
   If a game is open, run anyway (the owner's rule), but put the grass camera on a verge the car crossed and didn't
   park on, and say which pictures came from a game run.

Switch: `gt.Mud.CarMud` covers it. Tests: CarMud rows for FanCoat (spin feeds only the spinning wheel's fan; washes
like the coat).

*Done 2026-10-08 (VEHICLE_BUILD_SYSTEM 82, docs/MUD_VARIANTS.md "The muddy car"; no cost or timing measured; no game open at any run). 1: per wheel FanCoat (in mud: 0.8/s x the tread's spin over the car's speed, 0.3/s x MR2's speed x sinkage; washed like the coat: its arch wholly under a ford's water, rain, Wash) and FanDir, the sign of FanSide, a memory of which way the tread threw (new FGTWheelTraction::TreadCmPerS, Chaos's omega x radius; a full spin turns it over in about 1.25 s); the material's fan per arch is an annular sector in the side plane from the arch centre, -20 to 105 degrees from straight back, density (1 - t)^1.5 over 120 cm past the wheel's radius, radius and angle broken by a 25 cm noise, x FanCoat, plus 0.1 x the coat elsewhere; T_MudSplat_Splatter gained a G channel ranking every droplet (the bake's coverage byte-identical), so the density shows that share of whole droplets. Departure: the line's base is the coat line x 0.65 (LineDropShare 0.35; at 0.75 the coat reached the belt behind the rear arch and left no paint above it for the fan). 2: the line a curve along s = x - y: 80 / 25 cm value-noise octaves (12 / 4 cm) and 15 cm over each arch on 40 cm ramps, slope at most 1.49; its edge broken by a 9 cm two-octave noise (3 cm) and the splatter's droplets (8 cm); MR2's 7 m top-down sample (constant up a side: the vertical walls) gone, from the coat's thinning too. 3: Car_Muddy_Side, 92-114 cm above the wheel bottoms: behind the right rear arch 26 dark spots (2.63 per 100 cm2), mid-door 2 (0.18): 14.6x (Art/count_car_droplets.py, Car_Muddy_Side_Boxes.png). Found on the way: the check parked with the brake pedal held, which is reverse at a stop, so after the spin-up the wheels spun backward in Deep for 4 s and turned every fan forward (the fans were right); the checks now let the pedal go once parked (the runs with the fans forward measured 1.5-3.7x). 4: one clean set: Car_Muddy_Side - the line a slope low mid-door rising over both arches, jagged at small scale, no skyline; the droplets in two patches behind and above each arch, the mid-door nearly clean; spray from the wheels, but round spots without streaks; the coat a smooth blurred brown (MR2's); Car_Muddy_Rear - the rear less coated than MR2's (the line about 50-55 cm there), droplets scattered on the tailgate, densest near the right rear wheel; Car_Washed (completed: tyres clean, a 50 cm band at 0.98) - only a thin ragged strip of coat above the waterline, which may read as a stripe; Carry_Exit faint (two short marks at the exit, thin broken trails for a few metres); Carry_Grass / Off from a verge point the car crossed 16.5 m before it parked (the feet darker, 90.0 against 97.1 of 255; subtle); Splat_Post irregular lumpy splats on the shaded side, no black square. GrandTour.Mud.CarMud: spin feeds only the spinning wheel's fan (RR 1.000, the others 0), it turns in front after 1.5 s of reverse spin (not 0.5 s), braking forward keeps it behind; it washes like the coat (0.400 with the arch through 120 cm, kept through 50 cm, 0.900 after 10 s of rain, 0 with Wash); 12 of 12 Mud and Snow, CRC 8e0aad06. Suite `terrain drivetrain grip mud surface track body bodystate`: 7 PASS, terrain FAIL at step 11's held exit (6 m in 5.9 s, equal to down the ruts), PASS on the one rerun (5.9 against 5.6 s).*

### MR3: muddy water

**Scope, 2026-10-08 (the owner): "just rut pools for now, we are looking at improving water simulation."** MR3 does
item 1 (rut water) only. Item 2 (ford water) is deferred: GTWaterField and GTWaterSheet are being reworked separately,
with uncommitted edits in the tree. MR3 must not touch GTWaterField, GTWaterSheet, M_GT_Water or the river. Its
"Ford_Muddy" picture and the plume test are dropped; `Rut_Muddy.png` stays.

1. **Rut water.**
   - The mud field gains **Turbidity** per cell. A stamp or a throw deposit in a cell with water over 1 cm sets it to
     1. It mixes lightly with its neighbours and settles, half-life `RutSettleS` 45 s.
   - It's uploaded in TreadTexture A (free since LM5b dropped the churn channel).
   - `M_GT_MudWater` lerps from today's water to opaque muddy brown, the Standard slice's colour lightened, by
     turbidity. Where Fresh is set there are foam specks: light brown froth, painterly, irregular.
2. **Ford water.**
   - `FGTWaterField` gains **Turbidity** per cell. Wheel and hull lids stamping in water add turbidity by speed and
     slip.
   - It's advected by the solver's velocity (semi-Lagrangian, using the same face fluxes), diffuses lightly, settles
     with half-life `FordSettleS` 60 s, and leaves through the downstream sink columns.
   - It's uploaded as a grid texture to `M_GT_Water`: colour and opacity toward muddy brown, with foam at fresh
     churn.
   - River sections (WATER_PLAN R1), if they use a different solver: report and leave them.
3. **Switch**: `gt.Mud.MuddyWater`.
4. **Tests** (CPU):
   - rut turbidity settles at its half-life within 10 %;
   - a ford plume's centroid moves downstream at the local flow speed within 20 % and is gone past the sink;
   - no turbidity without water.
5. **Pictures**: `Ford_Muddy.png` (L_MudDrive's ford just after the crossing, looking downstream) and `Rut_Muddy.png`
   (a rut pool in Deep).

*Done 2026-10-08 (VEHICLE_BUILD_SYSTEM 84, docs/MUD_VARIANTS.md "Muddy rut water"; rut pools only, item 2 and the ford untouched; no cost or timing measured; GoWR open at every Unreal run, so the pictures are from a game run). Item 1: FGTMudField::Turbidity per cell (mud only) with its own tile flags; ChurnWater sets 1 where over 1 cm of water stands (RutWaterTableCm, the patch's table pushed every tick, over the lower of the surface before and after) from TouchCell where it sets Fresh (a stamp that moved the cell: a still wheel does not churn) and from DepositLump (a throw's landing); SettleTurbidity, its own 0.1 s sub-step whatever gt.Mud.Settle says: a wet cell exchanges K = 0.15/s x dt with each wet neighbour in a turbid tile (a weighted mean of old values: never above 1, conserving, never into a dry cell; a sleeping tile joins when a wet edge at 0.02 or more faces it), then x 0.5^(dt / RutSettleS 45); a dry cell holds 0; a tile under 0.02 everywhere sleeps and its remainder goes to 0. Heights and the settle's tiles untouched. TreadTexture A was free on mud (only snow writes it, LM3c; no mud material read it; LM5b dropped the churn channel): A = turbidity. M_GT_MudWater: a wrapper node from live_mud_style.py (setup_m6_water.py untouched) between the rut water's own node and its outputs: by turbidity toward the Standard slice top-down 5 mips down, toward its mean by 0.55, x 1.9, opaque past 3 cm (0.96), roughness 0.32; froth where Fresh x turbid: the splatter bake's droplets at two turned tilings (140 cm), whole droplets by rank, clustered by a two-octave value noise, the mean x 3.6. Switch gt.Mud.MuddyWater (0: nothing set, the field cleared, the wrapper returns its input). GrandTour.Mud.MuddyWater: set only where water (403 deep cells, 403 set, none dry after a sub-step; none without a table or above it; a throw in the pool 1, beside it 0); half-life 45.00 s over the pool, 42.70 s at its middle; the mix never above 1 or in a dry cell, the sum never rising, across a tile edge; the switch 0: the LM0 CRC 8e0aad06 on and off under water, the state CRC and awake tiles equal after 30 s, A all 0; asleep at 251.8 s (asked 254.0); 13 of 13 Mud and Snow tests, CRC 8e0aad06. Pictures (the scripted pass; the car spun 4.2 s in Deep's rut pools, moved 0.66 m): Rut_Muddy - the pool opaque mid-brown, smooth and evenly mottled, with pale tan froth specks in two loose bands of irregular clusters of many sizes (no grid, rings or swirls), but crisp and flat with some drip streaks, more spilt paint than foam (readout: 63 of 74 wet cells over 0.5, 60 froth cells); Rut_Settled (60.2 s of game time later) - the froth gone, the pool still brown, a little more see-through (the spot 0.287, the wet mean 0.265): a small change, since the clear rut water was already brown. Suite terrain drivetrain grip mud surface track: 5 PASS, terrain FAIL at step 11's held exit, FAIL again on the one rerun (the standing failure).*

*MR3b 2026-10-08 (VEHICLE_BUILD_SYSTEM 86; material only, live_mud_style.py; GoWR open): settled water darker, glossy (0.07), see-through at the rim (0.3 to 0.6) and churned an opaque lighter brown (0.95, rough 0.35), lerped by turbidity; the froth procedural soft bubbles (1.6 / 0.72 cm jittered cells) in 25 cm clumps, no splat atlas; Rut_Muddy / Rut_Settled retaken plus Rut_Muddy_Low / Rut_Settled_Low (the checks' shots now wait 10 ticks: at 2 frames a second the first grazing run caught the moved camera); the bubbles read as scattered pale bubbles in clumps, not paint, but sparse and fine; settled reads as murky see-through water (still brown at 60 s, turbidity about 0.28), no sky reflection seen; 13 of 13 Mud and Snow, CRC 8e0aad06.*

### MRP: physically based mud, parallax occlusion, optimised (named by the owner 2026-10-08 at the world-reacts gate)

*Done 2026-10-08 (VEHICLE_BUILD_SYSTEM 91, docs/MUD_VARIANTS.md "Physically based mud, parallax occlusion"; no cost or timing measured; no game open at any run). All five items built. 1: every mud surface behind gt.Mud.PBR (1; 0 = the look before MRP, to within the textures' quantisation: the roughness and the blend height now come from the BC7 ORH array) - the bakes' roughness remapped r' = 0.45 + (r - 0.14) x 0.5 / 0.77 clamped 0.45-0.95 (slurry 0.15-0.38 -> 0.46-0.61, lump tops 0.83-0.90 -> 0.89-0.95; the PBR 0 paths invert it), wet (the weather, the fresh sheen) toward the same surface saturated, MudWetRoughLo..Hi 0.45-0.65, floor 0.4, darkening unchanged; carried mud and splats dried 0.85-0.95, wet 0.45-0.65 (were 0.30-0.32); car and tyre mud wet 0.5 / dry 0.9 held in the bands, the clear coat 0 under full mud (MR2's), and a floor of 0.45 after MF_Weather (its wet path took porous mud toward 0.15); glass splats take the mud's roughness (compiled out of the glass's default translucency lighting); rut water Specular 0.25 (F0 0.02), settled 0.15 with a faint drifting ripple normal, churned 0.5, froth 0.6; removed: the water's grazing gloss (0.07 -> 0.03) and Fresnel opacity (0.45), the froth's glint, the slurry's sub-0.4 roughness, the wet / fresh falls to 0.48 / 0.5, MR1/MR2's 0.30-0.32 wet mud, the glass splats' 0.05; no mud emissive existed (M_GT_Mud's is its diagnostic); the clods were already in the bands. The far gloss fade's static switch FarGlossFade is now off: no crosswise bands in the far ruts of Mud_PBR_OnFoot. 2: Art/bake_mud_orh.py - horizon AO (16 directions to 6 cm) from each variant's height, T_MS_Bog<V>AO.png beside the bakes, packed with the remapped roughness and the height into T_MS_Bog<V>ORH.png; TA_MS_BogORH (linear BC7) by import_mud_variants.py; the ground, the landscapes' aprons, MF_MudCover, the splat decal, the car and the tyres read Color + Normal + ORH; the AO on the Ambient Occlusion pins (M_GT_Mud through its Occl output, so M_GT_Snow's copy keeps AO 1; MF_MudCover's new AmbientOcclusion output on all four ground materials; the car and tyre) plus a cavity tint of MudCavityTint 0.15. 3: POM on M_GT_Mud in the field normal's frame, MudPomDepthCm 3, SampleGrad with the un-slid derivatives, a linear refine, the hit's slide on both tilings and the walls, MudPomNearM 6 / MudPomFarM 14 behind a dynamic branch, 8 (POM 1) or 8-16 by the view angle (POM 2), skipped under rut water (AGTMudPatch pushes MudWaterTableCm), a 4-step sun self-shadow within 4 m (gt.Mud.POMShadow); the switches are MPC_TrackPaint scalars written by UGTTrackPaintSubsystem. 4: shader stats (pixel instructions, samplers, before -> after): M_GT_Mud 503 -> 742, 7 -> 6; M_GT_MudWater 2515 -> 2602, 8; M_GT_Vehicle 731 -> 750, 11 -> 10; M_GT_Tyre 321 -> 341, 5; M_GT_Glass 443, 3; M_GT_Landscape 305 -> 319, 7 -> 6; M_GT_Environment 357 -> 371, 8 -> 7; M_LiveLandscape / M_VariantsLandscape 477 -> 493, 10 -> 8; M_GT_MudSplatDecal 405 -> 415, 5 -> 6. PBR rows from HighResShot's GBuffer dumps (uncompressed EXR, linear: the gravel 0.898 of 0.9): ground roughness p5 Firm 0.741, Standard 0.502, Deep 0.455, Stony 0.502, L_MudDrive 0.502 (none under 0.40); the rut water (translucent, so a model of its formula over the pool's turbidity) median 0.272; car mud wet (MudWet 0.89) 0.451, dry 0.898; base colour luminance Firm 0.063, Standard 0.045, Deep 0.0322 (at the wet-soil floor's dark edge), Stony 0.048. Pictures: nothing reads as glossy; Mud_PBR_Close with POM 2 has the lumps standing up and occluding the mud behind them with dark shadowed fronts, fine stair-stepping on the steepest flanks and near-black undersides (Standard's lumps closer to stones set in mud); from standing height the parallax shows only in the near metres; Rut_Settled_PBR a murky see-through film without a mirror; the car's coat matte wet and dry. Departures: the close-up camera moved to sunlit untouched mud 3.2 m right of the line (the first run's spot looked into the +Y rut's shadow); the landscapes' carried mud and apron under rain still go through MF_Weather's shared wet path (no floor there). 5: 13 of 13 Mud and Snow, CRC 8e0aad06; Suite `terrain drivetrain grip mud surface track body bodystate`: 7 PASS, terrain FAIL at step 11's held exit (6 m in 6.3 s against 4.7 s unheld: "slower than down the ruts 0"), FAIL again on the one rerun (5.9 against 3.9 s) - the standing failure since MR2 (MRP changes no physics). gt.Mud.PBR 0 (the old look) was not pictured.*

*MRP follow-up 2026-10-08 (the main session's look at Mud_PBR_Close; no game open, a foreign Unreal waited out three times): the march's step search reads the height one mip up (SampleGrad with doubled derivatives), then MudPomRefine 5 binary halvings at full resolution and a secant between the bracket's ends; the steps' floor MudPomGrazingMinSteps 12 at a grazing angle (8 looking down, the maximum 16); the fade, the branch and the water skip kept. MudPomSteepCap (the depth shrunk where the relief is steep) built, tried at 0.6 and left at 0: the band pattern on the steepest lump flanks stayed in Mud_PBR_Close_Steep (about 20 degrees) with and without it and with gt.Mud.POMShadow 0 (0.27 of 255 apart), and Mud_PBR_Close is 0.62 of 255 from MRP's; the bands look like the packed height's own BC7 steps (a 4 x 4 block keeps at most 16 levels of its range), untested. M_GT_Mud 742 -> 917 pixel instructions (the landscapes +3 / +4 for the floor). Rain on carried mud: MF_MudCover's new FloorMask (its cover with gt.Mud.PBR) x (1 - MF_Weather's Puddle) holds the roughness at 0.45 after the weather on the four ground materials (MF_Weather unchanged); Carry_Wet_PBR (fresh tracks at 200 m, test wetness 1): the carried mud's median 0.451 (p5 0.259 at the tracks' feathered edges) against the wet gravel's 0.129, puddles 0.03. 13 of 13 Mud and Snow, CRC 8e0aad06. One check run ended in a GPU out-of-memory crash during MR3 (no other GPU user found); the one rerun passed.*

*MRP follow-up 2, 2026-10-09 (the main session's test of the BC7 theory; no game open, no foreign Unreal at these runs): the parallax's height has its own array, TA_MS_BogHeightPOM, BC4 (TC_Alpha) from the 16-bit height bakes (the old TA_MS_BogHeight, BC1, is kept: M_GravelLandscape reads it), and the AO and roughness a two-channel BC5 array, TA_MS_BogOR (TC_Normalmap, read raw); the ground, the landscapes' aprons, MF_MudCover, the decal, the car and the tyres read OR (+ HeightPOM where they need a height); TA_MS_BogORH is no longer built or read. M_GT_Mud 917 -> 919 pixel instructions, 6 -> 7 samplers. Texture memory (4 slices x 2048, every mip): ORH (BC7) 22.4 MB; OR (BC5) 22.4 MB + HeightPOM (BC4) 11.2 MB = 33.6 MB (+50 %); the G8 test array 22.4 MB. Mud_PBR_Close_Steep: the bands on the steepest flank are the same with BC7, BC4 and uncompressed G8 (0.48 and 0.74 of 255 from BC7's picture), so the compression is not the cause: the height bakes themselves have near-vertical lump rims (up to about 8 % of the height range, 0.36 cm, per 0.146 cm texel), and the parallax stretches those few texels of colour, normal and AO across the whole visible flank. Stopped there, as asked: BC4 kept (the cheapest of the split, not a fix); a softer rim in the bakes or a pre-blurred parallax height would be the next thing to try. Mud_PBR_Close POM 0 / 2 retaken (0.38 of 255 from the BC7 picture). 13 of 13 Mud and Snow, CRC 8e0aad06. One check run ended out of video memory (6 GB) after its pictures; the 32-bit post-process format is now only on while a buffer dump is taken.*

*MRP follow-up 3, 2026-10-09 (the main session: soften what the parallax reads, back to one ORH pack; no game open, no foreign Unreal at these runs): ORH's B is now a soft-rimmed parallax height (bake_mud_orh.py soft_rims: the slope capped at 1.5 % of the range per texel by the mean of the height's two cone envelopes, tops and floors kept, then a 1.5 texel Gaussian; the AO and the shading normal keep the sharp bake). Max slope per texel, before -> after: Standard 23.6 -> 1.5 %; Firm 23.1 -> 1.5 %; Deep 22.1 -> 1.5 %; Stony 17.7 -> 1.5 % (the real rims were steeper than the 8 % one row showed). Every reader is back on ORH (M_GT_Mud 917 pixel instructions, 6 samplers: MRP's), OR / HeightPOM / HeightPOM8 no longer built, the G8 hooks gone. Mud_PBR_Close_Steep: the flank bands are gone (the flank a smooth slope); a dotted dark line remains along some lumps' feet and the left lumps' shadowed edges are serrated; Mud_PBR_Close (POM 0 / 2, 14.0 of 255 apart; 4.2 from the sharp-height POM 2): the lumps still stand up and hide the mud behind them, lower and softer-edged than with the sharp height, not flattened. Texture memory from the built platform data (every mip, every slice; UGTMudArtLibrary::TextureAllMipsBytes): the bog arrays 53.4 MiB (Color 10.7, Normal 21.4, ORH 21.4), everything the mud materials read 135.9 MiB (RT_TrackPaint 32.0 of it), the snow's 62.2 MiB (sharing RT_TrackPaint and the legacy mud and clay maps). Both check runs ended out of video memory after their pictures, the second with r.Streaming.PoolSize 1500: textures are not the cause - at the crash D3D12 held 26.7 GB of UAV buffers (textures 253 MB, render targets 769 MB, the texture pool needed 42 MB), after about 25 HighResShots and 6 buffer dumps; the cause is unchecked. 13 of 13 Mud and Snow, CRC 8e0aad06.*

*VRAM soak, 2026-10-09: the "out of video memory" endings are not a leak but D3D12 residency-set slots used up under -RenderOffScreen (no swap chain, so nothing waits for the GPU); check_mud_variants.py now waits for the GPU each tick (GT_CHECK_PACE=0 off). Evidence, soak results and the switch: docs/VRAM_SOAK.md.*

**The owner, after the world-reacts set: "That is far too glossy, we need pbr and occlusion mapping for detail. ensure
it is optimised."** Their answers:
- too glossy: **all of it** (the mud ground, the rut water, the car mud, carried mud and splats);
- "occlusion mapping" means **parallax occlusion mapping on the mud ground**, plus a proper ambient occlusion map.

Performance stays the owner's to measure (no timing runs). Static shader stats (instruction and sampler counts) are
not timing and are reported.

1. **Physically based values everywhere mud is drawn.** No glossy hacks:
   - **Dry mud and soil**: base colour within the physical soil range (linear albedo about 0.05-0.25; report each
     variant's mean), roughness 0.85-0.95, specular default (F0 0.04).
   - **Wet mud** (saturated, not standing water): base colour darkened about 0.65-0.8x, **roughness 0.45-0.65, never
     under 0.4**. That covers the bogs' slurry, FreshWet's sheen, the weather's wetness on mud, wet carried mud, wet
     splats and wet car mud. The bakes' roughness is relative: the bog's slurry at 0.2-0.4 is remapped into the wet-mud
     band (for example 0.2-0.9 to 0.45-0.95; state the remap).
   - **Rut water**: water's F0 is about 0.02 (UE Specular about 0.25).
     - Settled: roughness 0.12-0.2 with a faint ripple normal, so it reads as murky water, not a mirror.
     - Churned: roughness 0.45-0.55 and opaque.
     - Remove any Fresnel or opacity boost that makes it glassier than that.
   - **Car mud**: wet 0.45-0.55, dry 0.85-0.95, the clear coat 0 under mud, tyres' mud the same.
   - **Remove** every mud-surface specular boost, glint, emissive or Fresnel trick (list what you removed).
   - **The far gloss fade** becomes unnecessary at these values. Keep its switch, default off, if the bands don't come
     back in the far views; say which.
2. **Packed maps (optimisation).** One linear **ORH array** per variant slice: R ambient occlusion, G roughness (the
   remapped value), B height (for parallax), A spare.
   - The ambient occlusion is baked from each variant's height map: horizon-based AO over about a 6 cm radius, computed
     by a script (numpy or Blender) and written beside the bakes.
   - The mud ground then samples Color + Normal + ORH per tiling, three arrays instead of four.
   - The AO drives the material's **Ambient Occlusion** output (indirect light) plus a light cavity darkening on the
     base colour (at most 15 %).
   - The carried-mud cover, the splat decals and the car mud use the same ORH (Standard slice) for AO and roughness.
3. **Parallax occlusion mapping on the mud patch surface.** The `M_GT_Mud` live block reuses LM4b's snow parallax
   approach:
   - It marches in a frame built from the **field's normal** (not the flat grid's tangent space, which is wrong on rut
     walls), over the ORH height. Depth about 3 cm (the bakes' -2 to +2.2 cm).
   - A linear refine after the march. **Mip-correct sampling**: SampleGrad with the original derivatives, so there's no
     shimmer at mip seams.
   - The hit's offset moves every lookup: colour, normal and ORH, on both tilings, with tiling 2 offset by the tiling
     ratio and rotation.
   - **Optimised**:
     - full steps within `MudPomNearM` 6 m, fading to off by `MudPomFarM` 14 m (a dynamic branch, so nothing is marched
       beyond it);
     - steps 8-16, by the view angle against the field normal (fewer when looking straight down);
     - no march where the pixel is under rut water;
     - a cheap self-shadow (4 steps toward the sun) only within 4 m, behind its own switch, default on if it reads
       right.
   - Switch `gt.Mud.POM` (0 off, 1 = 8 steps, 2 = adaptive 8-16, the default 2).
4. **Stats and pictures** (no timing):
   - Per material, before and after: pixel instruction count and sampler count (`M_GT_Mud`, `M_GT_MudWater`,
     `M_GT_Vehicle`, the tyre material, `MF_MudCover`'s users, `M_GT_MudSplatDecal`).
   - **PBR validation captures** on L_MudVariants and L_MudDrive with buffer visualisation (Roughness, BaseColor, and
     the AO if the view exists), by the check script. A sampler reports per surface: mud ground roughness has its 5th
     percentile at 0.40 or more (outside water); rut water roughness has its median at 0.12 or more; car mud wet is
     0.45 or more. Base colour means sit inside the soil range.
   - **Look pictures**: `Mud_PBR_OnFoot.png` (eye level along Standard's ruts), `Mud_PBR_Close.png` (60 cm, low,
     across lumps: the POM depth), each with POM 0 and 2, plus `Rut_Settled_PBR.png` and `Car_Muddy_PBR.png`. Describe
     what they contain: whether the lumps read as raised with self-occlusion, any shimmer, swimming or stair-stepping,
     and whether anything still reads as glossy.
5. **Tests**: every Mud and Snow test passes, and the CRC is unchanged (heights untouched). The switches at their old
   settings (POM 0 and the old roughness path behind a `gt.Mud.PBR 0` switch) give the previous look, so the owner can
   A/B.

### MR4: readable soft spots

1. **The field.** A static per-cell **Softness** S (0..1) per patch, from a hashed smooth noise at 3-8 m (two
   octaves), shaped so 20-30 % of the area is soft (S over 0.6) in irregular blobs of 2-6 m. The amplitude is per
   variant: Firm 0.5, Standard 1, Deep 1, Stony 0.6.
2. **The feel.** Inside the patch, the sinkage cap and rate scale by lerp(0.75, 1.5, S), normalised so the patch's mean
   scale stays 1, which leaves the tuned bog's averages alone. Friction scales by lerp(1.05, 0.9, S). The traction
   reads S at the contact.
3. **The look.** Soft spots blend toward the **Deep** slice, wetter and glossier, by S with a ragged edge (S x the bog
   height, then a soft threshold), so a soft spot in a Standard or Stony bog reads as the deep stuff. It's uploaded
   once, in the patch's static layer texture (G channel) or a sibling.
4. **Switch**: `gt.Mud.SoftSpots` (0 = S treated as 0.5: today's numbers exactly).
5. **Tests**:
   - the soft-area share and the blob sizes;
   - the mean scale is 1 within 2 %;
   - a CPU stroke across a soft and a firm spot sinks proportionally;
   - every Mud and Snow test passes with SoftSpots 0, and reports what moves with 1.
   Report the terrain test's bog escape: it sits at its gate.
6. **Pictures**: `Soft_Spots.png`, looking across a Standard section before driving, then after.

#### MR4 execution block (main session, 2026-10-09; supersedes 1-6 where they differ)

**Principle: what you see is what you feel.** The look and the feel read the same S, so a spot that looks deep sinks
deeper, and a firm-looking patch holds. Soft spots change no field height: the mud field CRC stays 8e0aad06.

**Scope.** Only Mud-medium bog patches (an unprofiled bog, or an LM5b variant's patch). Not fords or riverbeds
(their profiles), not Snow (snow feel is frozen), and not the `Gravel` medium. Gravel belongs to the Codex app: its
uncommitted hunks in GTMudPatch.cpp/.h and GTTerrainGenerator.h are not ours. Never edit or stage them, and they must
keep compiling. Report the exact predicate used.

1. **S, per cell, computed at Init, deterministic** (seed from the section index):
   - Raw n: two octaves of hashed smooth noise at 7 m and 3 m wavelengths (weights 0.65 / 0.35), domain-warped by a
     9 m noise of amplitude 1.5 m. The warp is what makes the blobs ragged instead of round.
   - S0: n remapped by the percentiles of the patch's interior cells only (d >= 2.0 m from the nearest edge),
     piecewise-linear: p5 -> 0.15, p75 -> 0.6, p95 -> 0.9: exactly 25 % of the interior over 0.6 at amplitude 1. The
     20-30 % share gate (item 5) is on the interior cells, pooled over the four patches at amplitude 1; the per-patch
     interior and whole-patch shares are reported beside it. (Main session, 2026-10-09.)
   - Variant amplitude a (a new field on FGTDeformProfile, `SoftSpotAmplitude`, set in MudVariantDefaults; Standard
     uses 1 with no profile): S = 0.5 + (S0 - 0.5) x a. **Proposed: Standard 1, Firm 0.5, Deep 0.6, Stony 0.6.**
     Deep drops from the outline's 1 because Deep already crawls at 1.8 km/h on sinkage x1.5; at a = 1 its soft
     spots would sink about 1.36x more again.
   - Rim: S = lerp(0.4, S, smoothstep(0.5 m, 2.0 m, d)), d the distance to the nearest patch edge: the outer 0.5 m is
     exactly 0.4 (so item 5's outer-0.5 m gate holds), under the look threshold even in the hollows (0.4 + 0.125 <
     0.55), so the edge never blends, and its feel is about 1. (Main session, 2026-10-09.)
   - Store S as a float array on the patch (or the field), outside the CRC.
2. **The feel**, in UGTTractionComponent where the LM5b variant scales are applied (the bVariantScaled branch, about
   line 204-215). Read S bilinearly at the contact point through a new `AGTMudPatch::SoftScalesAt(FVector2D)`. It
   returns:
   - SinkScale = lerp(0.75, 1.5, S) / M_s, multiplied into both the sinkage cap and the rate;
   - FrictionScale = lerp(1.05, 0.9, S) / M_f, multiplied into VariantFriction;
   where M_s and M_f are the patch means of those lerps over all its cells, computed at Init. Both scales sit on top
   of the variant's own scales, and every existing hard cap on sinkage still applies after them. Factor the cap/rate
   arithmetic into a static helper, so the CPU test calls the same code the traction does.
3. **The look**, in M_GT_Mud via Art/Unreal/live_mud_style.py:
   - LayerTexture goes from PF_G8 to PF_R8G8: R is the bog layer as today, G is S x 255. It is uploaded at Init as
     today.
   - Weight w = smoothstep(0.55, 0.68, S - 0.25 x (h - 0.5)), where h is the base slice's ORH.B (the parallax height).
     Lump tops therefore stay the base mud, and the hollows between lumps fill with the soft stuff first: a ragged edge
     that follows the lumps, never a smooth outline.
   - Inside a dynamic branch on w > 0.01, for variants other than Deep:
     - sample the **Deep** slice's Color, Normal and ORH at the same POM-offset UV (no second parallax march);
     - colour = lerp(base, deep, w);
     - normal and AO lerp by w;
     - roughness = lerp(base, max(0.45, deep), w), which keeps the MRP floor.
   - For every variant, Deep included: colour x lerp(1, 0.85, w) (wetter) and roughness pulled toward 0.45 by 0.5 x w.
     A Deep patch skips the slice samples and gets only this wet pull.
   - Report the instruction and sampler counts against MRP follow-up 3's 917 / 6. Counts are fine; no timing.
4. **Switch** `gt.Mud.SoftSpots` (default 1). At 0, SinkScale and FrictionScale are exactly 1 and G is re-uploaded as
   0 (so w = 0). The patch notices a flip on its tick, as it does for bSettleOn, and re-uploads the layer.
5. **Tests**: new `GrandTour.Mud.SoftSpots`, built on patches the size of L_MudVariants' sections.
   - Soft share (S > 0.6) is 20-30 % at amplitude 1; report it per variant.
   - Blobs are the 8-connected components over 0.6 with area of at least 1 m². Their median equivalent diameter is
     2-6 m, and their median shape factor P²/(4πA) is at least 1.6 (cell-edge perimeter; a cell-grid circle is about
     1.27).
   - Report the CV of blob-centroid nearest-neighbour distances (clustering), with no gate.
   - The mean SinkScale and FrictionScale are each 1 within 2 %.
   - In the outer 0.5 m, S is at most 0.45.
   - The same seed gives the same S, byte for byte.
   - Stroke: two CPU strokes with depths from the traction's helper, one over a cell with S 0.8 and one over S 0.2.
     The ratio of their rut depths equals the ratio of their SinkScales within 5 %.
   - With switch 0: both scales are exactly 1 and G is all 0.
   - Every GrandTour.Mud and GrandTour.Snow test passes at SoftSpots 1, and again at 0 (CRC 8e0aad06 both times). List
     any number that moves at 1.
   - Terrain test at 1: report step 11's escape distance; if step 11's result differs from today's, run it at 0 too.
6. **Check and pictures** (extend Art/Unreal/check_mud_variants.py; its per-tick GPU wait from VRAM_SOAK stays on):
   - CPU maps `Art/Export/MudVariants/soft-<Variant>.png`: S as grey, 1 px per cell, with a 1-px line along the route
     line.
   - Before driving:
     - `Soft_Standard_Before.png`, looking across a Standard section from 1.7 m eye height, 8-15 m from a soft blob;
     - `Soft_Firm_Before.png`, the same for Firm;
     - `Soft_Top.png`, a high oblique view (about 20 m up, 45 deg) over the Standard and Firm sections.
   - After the drive: `Soft_Standard_After.png`, from the same camera as Standard_Before.
   - Per section, from the drive: the mean speed, compared with the committed drive-report (which predates soft
     spots), and the share of wheel-path cells (route line ±1 m) that are soft.
   - The four existing variant pictures are retaken as usual.
7. **Docs**:
   - VEHICLE_BUILD_SYSTEM: take the next free section **at commit time**, because the Codex app adds sections there
     too.
   - The devlog, the BACKLOG line, MUD_VARIANTS.md (an amplitude column, and gt.Mud.SoftSpots in the switch table) and
     the italic Done note here.
   - The owner's test list: gt.Mud.SoftSpots 0/1 on L_MudVariants, and the amplitudes to name.
8. **Commit only MR4's hunks.** Several files carry other work's uncommitted hunks (GTMudPatch.cpp/.h,
   GTTerrainGenerator.h, VEHICLE_BUILD_SYSTEM.md, BACKLOG.md, the devlog). Stage them with a filtered patch and
   `git apply --cached`, using `git add -N` first for an untracked file, and check `git diff --cached` before
   committing.

*Done 2026-10-09 (VEHICLE_BUILD_SYSTEM 96, docs/MUD_VARIANTS.md "Readable soft spots"; no cost or timing measured). Built as the
execution block with the main session's revisions of the same day: scope `!bHasProfile && Medium == EGTDeformMedium::Mud`; S at
Init (7 m / 3 m octaves, a 9 m warp of 1.5 m, the remap over the interior 2 m in, amplitude Firm 0.5 / Standard 1 / Deep 0.6 /
Stony 0.6, the rim lerp(0.4, S, smoothstep(0.5 m, 2.0 m, d))); SoftScalesAt into the traction's variant branch through
UGTTractionComponent::PatchSinkage; MudLayer R8G8 with S in G; M_GT_Mud toward the Deep slice (991 pixel instructions, 7 samplers,
accepted: MudLayer had been compiled out); gt.Mud.SoftSpots; the terrain test's bog escape at gt.Mud.SoftSpots 0 with a mean-S
line. GrandTour.Mud.SoftSpots: the interior's share at amplitude 1 pooled 25.0 % (whole 19.4 %), median blob 4.82 m, shape 2.04,
the outer 0.5 m 0.400, the scales' means 1.0000, the stroke ratio 1.5000 = the SinkScale ratio, switch 0 exact; 14 of 14 Mud and
Snow at 1 and at 0, CRC 8e0aad06, nothing else moved (GoWR open). Terrain with the step at 0: escape forward 6.1 m (8 asked; GoWR
open; mean S 0.559 under its wheels, 49 % soft); 7.0 m at 1 and 9.6 m at 0 before, without a game: the owner's feel call. The check
at 1.13 frames a second (GoWR): drive timed out at 76.28 m, speeds not comparable; wheel-path soft share Firm 29.1, Standard 18.6,
Deep 18.0, Stony 14.3 %; the pictures and soft maps for the main session's look.*

*Follow-up 2026-10-09 (the main session): Deep keeps its colour under soft spots (the x0.85 darkening only off Deep, for its soil
band); the terrain test runs steps 8-9 (the bog run and the escape) at gt.Mud.SoftSpots 0, restoring it after. 14 of 14 Mud and Snow
at 1 and at 0, CRC 8e0aad06 (GoWR open). Owed without a game: the terrain test and the check (Deep's luminance, PBR_CarryWet).*

### MR5: breakable mud chunks

1. **Meshes.** `Art/Blender/build_mud_chunks.py`: 6 larger clods (20-50 cm, 600-1,000 triangles) in LM2c's families
   (rounded, slab, broken, smear), each with one simple convex collision hull. Import as `SM_GT_MudChunk_0..5`.
   Material: the variant slice via the clod material's path.
2. **Placement.** At patch build, scattered on the untouched mud and banks of each mud patch, clustered (cluster
   noise), about 1 per 25 m² near the route line (within 6 m of it), none within 30 cm of each other. Per variant:
   Firm 0.5x, Deep 1.5x, Stony 1x with stony chunks.
3. **Physics.**
   - Simulated rigid bodies, 10-40 kg by size, asleep until touched; at most 64 awake at once.
   - **They rest on the landscape collision.** This matches the visual surface where the field is 0: untouched mud.
     So none spawn in ruts, and a chunk whose cell is cut by a wheel breaks (it was run over). The car bumps them
     and pushes them.
4. **Breaking.** A chunk breaks into 3-5 LM2c clods (the visual HISM) plus a lump deposit of its volume into
   `LumpCm` (exact) where it lies:
   - when a wheel's stamp capsule overlaps its footprint (driven over);
   - when the chassis hits it with an impulse over `ChunkBreakImpulse` (500 N s proposed);
   - or when it lands from a throw at over 4 m/s.
   Chunks under 25 cm break on any wheel contact.
5. **Switch**: `gt.Mud.Chunks`.
6. **Tests** (CPU where possible): break on a capsule overlap, with the volume moved into LumpCm exactly; the spawn
   counts and spacing per variant; the awake cap.
7. **Pictures**: `Chunks_Before.png` and `Chunks_After.png` (the same camera before and after a pass through
   Standard).

#### MR5 execution block (main session, 2026-10-09; supersedes 1-7 where they differ)

**Principle: chunks are the firm crust, and soft spots are the soup.** Chunks sit only where MR4's S is low, so they
also signal firm ground. Wheels never ride up on a chunk: a chunk a wheel reaches breaks. The chassis bumps and
pushes chunks. Scope is the same as MR4: `!bHasProfile && Medium == Mud` (no Snow, ford, riverbed or Gravel). Codex's
uncommitted hunks stay untouched and unstaged, as in MR4.

1. **Meshes.** `Art/Blender/build_mud_chunks.py` follows `build_mud_clods.py`'s recipe and export conventions:
   - Six chunks: 2 rounded, 2 slab (one with a broken side), 1 broken (planar cuts) and 1 smear. Each is authored
     30 cm across, 600-1,000 triangles, with stronger surface noise than the clods and a few crack grooves, so it reads
     as torn crust, not a stone.
   - Each has one convex collision hull (UCX_) covering the mesh above an **embed line at 18 % of its height**. The
     render mesh goes on below that line, the hull doesn't, and the pivot sits at the hull's bottom centre. Resting on
     the ground, the lowest 18 % is buried, so the chunk reads as set in the mud. This is a render-only trick; the
     physics is unaffected.
   - `Art/Export/MudChunks/manifest.json` lists per mesh: family, closed-mesh volume (cm³ at 30 cm), hull volume, and
     embed height.
   - Import as `SM_GT_MudChunk_0..5`. The material is a new instance of M_GT_Clod's path: the variant slice through
     PatchVariant, freshness fixed at 0 (dry crust). Stony chunks therefore wear the Stony slice.
2. **Placement**, at patch Init after S; deterministic, with the seed from the section index:
   - **Candidate cells:** within 6 m of the section's route line (the line MR4's wheel-path share used), at least 1.5 m
     from the patch rim, and S ≤ 0.55.
   - **Density:** 1 per 25 m² of candidate area, times the variant multiplier: Firm 0.5, Standard 1, Deep 1.5,
     Stony 1.
   - **Clustering:** a hashed 4 m noise marks about 35 % of the candidate area as cluster ground, with density ×2.5
     there and ×0.2 elsewhere, renormalised so the mean density is the target.
   - **Sizes:** power-law, size = 20 + 30 × u^2.2 cm, so most are small. Random yaw, tilt ±12°. Families picked with
     weights rounded 0.3, slab 0.35, broken 0.2, smear 0.15.
   - **Spacing:** no overlaps, an edge gap of at least 5 cm (centres at least r1 + r2 + 5 cm apart), so clusters can
     sit close like broken crust.
   - **Cap:** 48 per patch.
   - **Resting height:** spawn with the hull's bottom on the landscape, found by a trace at spawn, so nothing drops.
3. **Physics:**
   - One pooled UStaticMeshComponent per chunk, owned by the patch, simulating.
   - Mass = clamp(1.6 kg/L × volume, 10, 40) kg. Each chunk is put to sleep right after spawn.
   - Object type `ECC_Destructible`. First confirm nothing else in the project uses it; if something does, report it
     and use the next unused engine channel.
   - The vehicle's wheel suspension traces ignore that channel (the wheel trace collision responses), so wheels never
     ride up on a chunk.
   - Chunks block WorldStatic, WorldDynamic, the vehicle body, Pawn and each other.
   - **Awake cap:** at most 64 awake world-wide (counted in the mud subsystem). Beyond that, the longest-awake chunk is
     put to sleep.
   - **Lost chunks:** a chunk more than 1 m below the landscape at its XY is removed, and its volume is logged as lost.
4. **Breaking.** The chunk is removed and, at its XY:
   - its exact volume (from the manifest, × scale³) goes into LumpCm as a dome of radius 0.5 × size: DepositThrown's
     dome without its clod roll, factored out as a shared helper;
   - 3-5 LM2c clods spawn through SpawnClod with a new Source 5 (chunk break), at 0.25-0.45 × the chunk's size,
     scattered within 0.6 × size.

   It breaks:
   - **a)** when a wheel in contact inside the patch has a stamp footprint that overlaps the chunk's footprint circle
     (0.4 × size). Any size breaks, since wheels pass through chunks physically. Check this on the same per-wheel path
     that stamps the field, against a coarse grid of the patch's chunks.
   - **b)** when the chassis hits it with a normal impulse over `ChunkBreakImpulse` = 500 N·s (50,000 kg·cm/s in UE
     units). Below that, it is pushed.
   - **c)** when an awake chunk hits the ground at over 4 m/s.

   Readouts: breaks by trigger, the volume deposited, the volume lost, the awake peak.
5. **Switch** `gt.Mud.Chunks` (default 1). At 0, no chunks spawn and existing ones are removed; there are no
   deposits, so the mud field CRC is unaffected. The terrain test forces `gt.Mud.Chunks 0` across steps 8-9 together
   with SoftSpots (the tuned bog) and reports how many chunks L_Leg03's bog line has at 1.
6. **Tests:** `GrandTour.Mud.Chunks` (NullRHI; Chaos runs headless), on L_MudVariants' patches:
   - **Spawn:**
     - deterministic;
     - count per variant within ±25 % of the target;
     - none on cells with S > 0.55, none within 1.5 m of the rim, no overlaps (edge gap at least 5 cm);
     - size CV at least 0.25, with the largest at least 2× the smallest;
     - nearest-neighbour distance CV at least 0.4, so the spacing is not even.
   - **Wheel break:** a footprint overlap removes the chunk. The LumpCm volume added equals the chunk's volume within
     0.5 %, and it spawns 3-5 clods.
   - **Impulse break:** call the hit handler at 0.9× and at 1.1× the threshold; only the second breaks.
   - **Awake cap:** wake 100 chunks, and at most 64 stay awake.
   - **Physics:** a chunk dropped 5 cm onto flat ground rests and sleeps within 3 s, with its hull bottom within 1 cm of
     the ground.
   - **Switch 0:** no chunks.
   - **Regression:** every Mud and Snow test passes at Chunks 1 and at 0, CRC 8e0aad06 both times.
   - **Suite:** run the full `bash Art/suite.sh -q` once, because chunks are new things the cars can hit.
7. **Check and pictures**, extending check_mud_variants.py:
   - `Chunks_Before.png` and `Chunks_After.png`: the same camera across Standard's start, before and after the scripted
     pass;
   - `Chunks_Close.png`: on foot, eye height 1.7 m, 3-4 m from the biggest cluster in Standard;
   - `Chunks_Firm.png`: across Firm's sparser chunks;
   - per section: chunk count, breaks by trigger, the awake peak, and the volume deposited.
   Under a game the drive may time out. Report how far it got.
8. **Docs and commit** as MR4. VEHICLE_BUILD_SYSTEM takes the next free section at commit time. Stage hunk by hunk
   and never stage Codex's hunks (DefaultEngine.ini included: MR5 uses no new channel, so it needs no ini change).
   The owner's test list: gt.Mud.Chunks 0/1 on L_MudVariants, ChunkBreakImpulse, the density multipliers, the size
   range, and the cost (component count per patch).

*Done 2026-10-09 (VEHICLE_BUILD_SYSTEM 97, docs/MUD_VARIANTS.md "Breakable mud chunks"; no cost or timing measured; no game or foreign
Unreal at any run). Built as the execution block: channel ECC_Destructible (unused elsewhere: no source, config or script names it, no
package serialises it, a scan of the three maps naming it found no such component), the car's wheel traces ignore it; six meshes
(806-996 triangles, 30 cm, UCX_ hulls of 59-64 vertices over the 18 % embed line, volumes 1538-5586 cm^3 on the mesh as
UGTMudChunkData); M_GT_MudChunk on M_GT_Clod's path (freshness 0, the tint from custom primitive data); placement as item 2 with u
stratified per patch; the variant multipliers in FGTDeformProfile::ChunkDensityScale; breaks through DepositLumpDome (DepositThrown's
dome, recorded as EventChunk) with 3-5 Source 5 clods; the awake cap in UGTMudSubsystem; gt.Mud.Chunks; the terrain test's steps 8-9 at
0. GrandTour.Mud.Chunks: counts 6 / 10 / 16 / 11 = the targets, no violations, size CV 0.28-0.32 (largest at least 2x smallest), NN CV
0.41-1.41, the wheel break's field volume exact (half of it over LumpMaxCm into HeightCm, DepositLump's rule), 0.9x / 1.1x impulse,
the cap 64 of 140, the drop asleep at 0.37 s on its hull; 15/15 Mud and Snow at 1 and 0, CRC 8e0aad06; suite 28 PASS; L_Leg03's bog 17
chunks, escape 8.4 m. The check drove through (39 fps): breaks wheel 6, landing 1, impulse 0; Deep's luminance 0.0323 (0.0324 at
gt.Mud.Chunks 0: the churn). The Chunks_* pictures for the main session's look.*

## 4. Order and gates

MR1 -> MR2 -> MR3, chained, with the main session looking at each stage's pictures. Then the owner drives and looks.
Then MR4 -> MR5, and the owner drives. One Opus agent per stage; never two touching the same files or running Unreal
at once.
