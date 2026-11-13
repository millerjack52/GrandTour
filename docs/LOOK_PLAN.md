# The painted look: plan (2026-09-23)

**Current visual default (2026-09-29):** At the owner's request, gameplay now uses
`gt.Look.Post=2`, `gt.Look.WarpScale=0`, and `gt.Look.Kuwahara=0`. Fixed exposure is
retained, but full-screen banding and stroke displacement are disabled. Mode 2
preserves authored sun softness. The original stages below describe the earlier
look; their filter defaults are superseded. See `docs/TUSSOCK_STYLE_IMPORT.md`
for the current tussock-map lighting and validation.

*Written 2026-09-23 from the owner's ask ("I am ready to start on the visuals. I have a very distinct style I am going
for. What do you think the best method to approach creating this look procedurally? I will create the models.", then
"What about a Blender addon?", then "write docs") and the orchestrator's decisions. Five stages, L1-L5, take
docs/VEHICLE_BUILD_SYSTEM.md sections 55-59. Nothing here is measured: every number is proposed. Gate to start: the
owner reads this and starts L1 in a new chat with docs/prompts/LOOK_L1_blender_addon.md.*

## 0. Rules for the agent (the owner's, all of them hold)

Rules 1-6 are docs/RIVERBED_PLAN.md section 0's (lines 10-53), adapted where the look needs it.

1. **Never model cars or characters.** The owner makes every model. A sourced texture is CC0 only, with its licence in
   a SOURCE.txt beside it. The GT Paint addon never sources a texture: it bakes the owner's model in the owner's preset
   and hand paint. (RIVERBED 0 says textures are "never painted or generated"; the bake of the owner's model is the one
   exception.)
2. **Never say how something looks or feels from code.** Numbers come from bakes, tests and pictures (a pixel sampler,
   `Art/tools/*.ps1`, on boxes the runner logs), or the thing is "unchecked". A look at a picture is reported as a look.
   Compare like with like: a full hide_shots run with a full run, a bog run with a bog run, a ford run with a ford run.
3. **Movement is the owner's, and so is every tuned number.** Not touched: the rows in `Art/Unreal/setup_m1_track.py`,
   the traction's constants, the mud's shape numbers, the water's (WaterDragPerMetre 2.4, DragCd 1.0, HeadDropCm 30),
   the intake 0.85 m, the camera, the terrain specs, the weather states' values, the landscape material's tile sizes and
   tints (section 48). The look adds; it does not tune. "Proposed" numbers are starting points the stage agent sets,
   measures and reports; the owner names them.
4. **Harvesting is a placeholder**: never build on its nodes, tools or yields.
5. **The machine rule.** Before any build or .bat: `tasklist | grep -i -E "UnrealEditor|GrandTour|FarCry"`. An editor or
   GrandTour process is the owner's: never kill it; stop and say so. FarCry6.exe running: finish the current run, wait
   at most 15 minutes, then write the docs for what is done and report PARTIAL. A game on the GPU voids every timing
   number (frame ms, `GTWATERSTATS`): say so beside the number. One Unreal process at a time.
6. **Tools, one call each.** `bash Art/build.sh` (check its stdout line `== build exit 0`, not the log; editor closed).
   A .bat: `cmd //c "$(cygpath -w /c/GrandTour/Art/<name>.bat)" < /dev/null`, then check its log's timestamp.
   `bash Art/suite.sh <names>` in the foreground (timeout 900000 ms), waited on inside the turn, never on a
   notification; 24 tests: base body bodystate door drive drivetrain env grip hazard leg loop loot mud onfoot proving
   rough spray surface terrain tour track water weather winch. Setups only when their assets change, in the order
   setup_m6_textures, setup_m6_water, setup_m6_mud, setup_m6_hide, setup_m6_proving. MF_Weather and MPC_Weather belong
   to `Art/Unreal/setup_m1_weather.py`; rebuilding MF_Weather severs the masters: re-run setup_m1_body.py then
   setup_m1_masters.py (as `setup_m3_weather.py` does). `setup_m6_hide.py` builds the landscape material
   (`build_landscape_material`, :258), the water material (`build_water_material`, :557) and the level (`build_level`,
   :825). Pictures, all `-RenderOffScreen`: `Art/hide_shots.bat` (L_Leg03, every step, `Saved/Screenshots/M6`),
   `Art/bog_shots.bat` (`-GTShotsFrom=12`) and `Art/ford_shots.bat` (`-GTShotsFrom=22`), all three into
   `Saved/Logs/hide_shots.log`; `Art/base_shots.bat` (L_Base, `-GTBaseShots`: the car on the lift, the doors,
   `Saved/Screenshots/M4`); `Art/proving_shots.bat [step]` (L_Proving, `-GTProvingShots`, `Saved/Screenshots/Proving`,
   `Saved/Logs/proving_shots.log`). Samplers: `sample_rut_low`, `sample_border`, `sample_ford`, `sample_wheels`. Never
   chain per-test Bash calls; `/Game/` map arguments from a script file. Inline heredocs over ~10 lines fail: use the
   Write tool. The repo is CRLF throughout; keep it. Git is not initialised.

**Blender rules.**
- Blender 5.1 at `C:\Program Files\Blender Foundation\Blender 5.1`. Reproducible work runs headless:
  `"/c/Program Files/Blender Foundation/Blender 5.1/blender.exe" -b --python <script>` from a bash script file
  (`Art/blender_test.sh`, new in L1), never typed inline.
- The MCP: the blender-mcp addon, port 9876, one client at a time. It reaches the owner's live Blender only when they
  click Start MCP Server. Never touch the owner's open file without saying so. **Scratch-instance recipe** (the owner's
  Blender holds the port): stop the owner's server through a `bpy.app.timers` callback (say so in the report); launch
  `cmd //c start "" "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" --python <script>`, where the script
  registers a timer that enables the addon and starts the server, retrying until it runs; verify with
  `netstat -ano | grep 9876`.
- Node lookups by type (`n.type == "BSDF_PRINCIPLED"`), never by name (names localise). Enum values read from RNA
  (`bl_rna.properties[...].enum_items`), never hardcoded; the render engine is the exception (a dynamic enum): read it,
  assign inside `try/except TypeError`. Baking is a Cycles call.
- `Art/rangerover.blend` is the owner's blockout and the source of truth: copy it for tests, never edit or save it
  (`Art/Blender/export_rangerover.py` never saves it either).

**Test policy.** L1: `bash Art/blender_test.sh` + `bash Art/suite.sh base body`. L2: `bash Art/suite.sh terrain` + the
full suite once. L3: `terrain proving`. L4: `water mud terrain`, their lines unchanged. The full suite once at the end
of a session, by its last agent. **Known flakes**: body (Chaos hit events) and winch (its anchor), rerun once; terrain
step 11's ruts gate. Report them; never tune them.

**Docs per stage.** A new section at the end of `docs/VEHICLE_BUILD_SYSTEM.md` (L1 55, L2 56, L6 57, L3 58, L4 60, L5 61; the
last today is 54); `docs/devlog/<date>.md`; a LOOK line in `docs/BACKLOG.md` ending with the stage's gate; the stage
note here (italic under its heading). `docs/WATER_PLAN.md` section 6 (line 515) lists R2/R3a/R3b as 55/56/57: each agent
that takes a look section moves them up by one, in one line there. Numbers before and after, what was seen, unchecked.

**Report format** (under 250 words, numbers first): tests and results; bake and gate numbers asked/read; pictures and
sampler numbers before/after; the stage's numbers as set; unchecked; files touched (paths only).

**Read list for a fresh agent** (grep -n and sed ranges only): this file, sections 0-2 and the stage
(`grep -n '^### L'`); the five references (Read tool); `Art/Unreal/setup_m6_textures.py` lines 1-90;
`Art/Unreal/import_rangerover.py` (80 lines); `docs/VEHICLE_BUILD_SYSTEM.md` section 48 (line 4100, the painterly
ground) and section 54's first 20 lines for the voice; the files the stage names. Nothing else until a change needs it.

## 1. The references and the look (2026-09-23)

Five frames, `docs/references/look/ref_01.webp` .. `ref_05.webp`, stills from one video (a player's icons and progress
bar sit on top: not part of the look). A hillside town, a figure with a boombox on a skateboard, high clear sun.

**The plan writer's look** (2026-09-23; a look, not a measurement):
- ref_01: close-up. An orange wall in one flat orange with horizontal brush drags; branch shadows on it hard-edged and
  darker rust, the wall's own hue, not grey. Foliage behind as flat dark-green blade shapes in 2-3 values. The jacket
  near-flat charcoal with a few fold shapes; the boombox in three greys. A pale wall below in blocky tan-grey planes.
- ref_02: low, wide. A yellow wall, its tree shadow a hard ochre-brown; a cobalt wall with deeper blue-violet branch
  shadows and chipped white plaster patches. A pale grey road; the skateboard's shadow a hard cool blue-grey shape.
- ref_03: back-lit street. The road splits into a cool blue-grey shadow half and a warm pale lit half, long hard cast
  shadows of the cyclists across it. Sky a flat cobalt lightening to the horizon; houses as orange, yellow and blue
  blocks, two tones each; mid-ground people as simple shapes; power lines as thin dark strokes; a pale distant peak.
- ref_04: the deep frame. The distant town as hundreds of small pale blocks, lighter and bluer with distance; clouds as
  white painted blobs with a blue-grey shadow side; a blue wall with loose dark wire strokes and scraped pale patches;
  the foreground road broken into flat blue shadow shapes; rubble in pale lavender planes. Ragged edges everywhere.
- ref_05: a yellow wall with ochre scuffs and drips, pale grey trim as flat bands, dark windows in blue frames; a cool
  blue-violet shadow band across the road; the dog in two oranges; the distant houses and people pale, low contrast.
- Across all five: shadows on saturated walls keep the wall's hue, darker and a little more saturated; shadows on the
  pale road go blue-violet. One multiplied cool tint gives both: orange (1.0, 0.5, 0.2) x (0.55, 0.62, 0.80) =
  (0.55, 0.31, 0.16), a rust; pale grey 0.8 x the tint = a blue-grey (arithmetic, not a reading of the frames). Almost
  no ambient-occlusion darkening in corners. Most detail on the figure (face, hair, boombox), least on the background.

**The orchestrator's look** (2026-09-23, quoted; also a look): "flat, saturated local colour on big surfaces with
almost no texture detail; two tones per surface, lit and shadow, a hard terminator, the shadow shifted cool rather than
merely darkened; crisp cast shadows that carry colour (palm shadows on walls); no outlines; no specular noise, bloom or
reflections; foliage as flat leaf silhouettes in two or three values; painted scuffs and brush grain on walls; ragged
painterly edges; detail concentrated on the focal subject, backgrounds simplified into blocks; a slight cool haze on the
distant town; clouds as painted blobs. It is painted concept art: nothing in it comes from a photographic texture
pipeline."

**Where the game is today** (grep, 2026-09-23): the landscape's Scrub and Dirt rows wear two painterly CC0 sets (section
48); the Mud and Bog rows and `M_GT_Mud` wear the photoreal muddy_tracks set; `M_GT_Water` a CC0 ripple normal (W4).
`Config/DefaultEngine.ini`: Lumen GI and reflections (`r.DynamicGlobalIlluminationMethod=1`, `r.ReflectionMethod=1`),
Substrate (`r.Substrate=True`, GBuffer format 0), virtual shadow maps, ray tracing; no `r.CustomDepth` line. No
post-process material and no custom-stencil use exist in `Art/Unreal/*.py` or `Source/`. The car wears `M_GT_Vehicle`
(`Art/Unreal/setup_m1_body.py:13-19`: runtime Dirt, MF_Weather wetness, MF_Dents, clear coat). Sun and sky are spawned
per level by the setup scripts (`setup_m0.py:88`, `setup_m1_track.py:181`, ...).

## 2. The split (decided 2026-09-23)

| | Runtime, in Unreal | Author time, in Blender |
|---|---|---|
| What | everything that depends on the sun, weather, camera or deformation: the two-tone lighting bands, the coloured shadow, haze, the brush-edge post, the sky, the water and mud looks, the landscape (already painterly on Scrub/Dirt, section 48) | the painted surface of every model the owner makes: posterised colour blocks, edge wear, grime, brush grain |
| How | one post-process lighting layer (L2) over deferred lighting; own materials for the sky, water and mud (L3, L4) | baked once per asset into an albedo and a packed mask, art-directable by hand in Blender's texture paint |
| Cost | a full-screen pass per frame (measured in L2) | free at runtime: two textures per asset |
| Tool | the post material + `M_GT_Painted` (L1), which receives the bakes and hands lighting to the post layer | the GT Paint addon (L1) automates it |

The flow: the owner's model -> Apply Style -> hand paint -> Bake -> `T_GT_<Asset>_D` (unlit albedo) + `T_GT_<Asset>_M`
(R wear, G grime, B roughness) + FBX -> Unreal import -> `M_GT_Painted` (colour and roughness, no lighting) -> deferred
lighting + hard shadows -> the L2 band pass, tints, warp, Kuwahara, grade -> the frame. The contract: a bake carries
paint, never light. Grime is dark paint in the albedo; the band pass leaves it as paint.

## 3. Stages

One Opus 5.5 agent per stage (L1 in a new chat), each gated by the owner's look and a frame or bake number. L1 and L2
may run in parallel: one is in Blender, one in Unreal, and they never share a process. L1's Unreal half
(`setup_look_l1.bat`, `suite.sh base body`) and every L2 run still take turns under rule 5 (one Unreal process;
`build.sh` wants the editor closed).

### L1. The GT Paint Blender addon and M_GT_Painted (section 55)

*BUILT 2026-09-23 (VEHICLE_BUILD_SYSTEM 55): `Art/Blender/gt_paint/` (Apply Style, Bake, Export; the GT_Paint group
posterised to the preset's tones, the addon's own nearest-copy margin), `Art/Blender/gt_paint_preset.json` (every number
PROPOSED, UNMEASURED), `bash Art/blender_test.sh` PASS (TestCube 3 tones of 4, TestBox 2 of 4, TestCar 10 of 16; under
a second a 1K bake), `Art/setup_look_l1.bat` (props into /Game/GrandTour/Props/Painted, `M_GT_Painted`,
`MI_GT_Painted_<Asset>`), `Art/proving_shots.bat 4` + `Art/tools/sample_tones.ps1` (TestCar box before 205 200 192,
after 244 190 97; the parked car's control box +0.2 +0.4 +0.4), `suite.sh base body proving` 3 PASS. The driven car
keeps M_GT_Vehicle (closed 2026-09-24, L1 follow-up 3: the car keeps M_GT_Vehicle and takes the bake as textures, a
painted path behind UsePaint; follow-up 4, 2026-09-25: GT Paint's Bake unwraps a single source with no UV and the panel has Unwrap for Paint, so frontDoors, passengerDoors and rearPanel now carry a UV into Unreal and the driven car wears their bakes, VEHICLE_BUILD_SYSTEM 55). Gate open: the owner installs the addon, styles a model of their own, bakes,
exports, sees it in Unreal beside the landscape, and names the preset's numbers.*

*Follow-up 2, 2026-09-24 (section 55): the strokes are normal-map dabs from the owner's OW Painterly Normal Baker (Bake's third output T_GT_<Asset>_N), not albedo; scuffs and albedo strokes default to 0.*

- **The addon**: `Art/Blender/gt_paint/` (a package, `__init__.py`, `bl_info` for 5.1, an N-sidebar panel "GT Paint").
- **Apply Style**: creates or refreshes the shared `GT_Paint` shader node group and a material per object from the
  preset: base colours from vertex colour or an ID mask, posterised to the preset's tone count, world-aligned brush
  grain, edge wear from bevel + pointiness, grime from ambient occlusion, an optional single paint highlight.
  *Follow-up 2026-09-23 (section 55): wear = the bevel edge term (pointiness 0 by default) + sparse ragged scuffs
  low and on edges; grain = light/dark strokes on walls after the tone rounding; the owner re-looks.*
- **Bake**: smart-project UV if none; unlit albedo -> `T_GT_<Asset>_D`, packed mask -> `T_GT_<Asset>_M` (R wear, G
  grime, B roughness); 1K or 2K PNG into `Art/Export/<Asset>/`.
- **Export**: FBX named for `Art/Unreal/import_rangerover.py`'s pattern. Flag (repo, 2026-09-23): that script is the
  Range Rover's only. It reads `Art/Export/SK_RangeRover.fbx` (skeletal) and `Art/Export/Static/*.fbx` (`SM_RR_<Part>`)
  into `/Game/GrandTour/Vehicles/Bodies/RangeRover` and `.../Panels`, with `make_task`'s FbxImportUI settings (:23-52:
  no materials, no textures, scene and unit conversion, combined meshes, auto collision). It never reads
  `Art/Export/<Asset>/`. So: `SK_<Asset>.fbx` / `SM_<Asset>_<Part>.fbx` in `Art/Export/<Asset>/`, imported by
  `setup_look_l1.py` with a copy of `make_task`'s settings; the car's meshes are already imported and only take the
  textures and the material.
- **The preset**: `Art/Blender/gt_paint_preset.json`, every number the owner's. Proposed (all unmeasured): tones 4,
  grain scale 0.35 m, grain strength 0.15, wear width 2 cm, wear lighten 0.25, grime strength 0.3, highlight off.
- **Headless test**: `Art/Blender/tests/test_gt_paint.py` via `bash Art/blender_test.sh` on a cube, a bevelled box and a
  copy of `Art/rangerover.blend`'s car (copy, never edit): bake time, files, distinct-tone count vs the preset, mean
  albedo, mask means; fails on a missing file.
- **The Unreal side**: `Art/setup_look_l1.bat` + `Art/Unreal/setup_look_l1.py` import the car's bake into
  `/Game/GrandTour/Textures/Painted` on the `setup_m6_textures.py` conventions (AssetImportTask; `_D` TC_Default sRGB on,
  `_M` TC_Masks sRGB off; a `SETUP_LOOK_L1` log prefix); build `M_GT_Painted` (albedo from `_D`, roughness from `_M.B`,
  wear lightening and grime darkening behind scalar parameters, no lighting tricks) and assign it to the imported car.
- **Numbers**: an existing picture mode with the car in view (`Art/base_shots.bat` or `Art/proving_shots.bat`): mean
  colour and distinct-tone count in a box on the car, before and after. No sampler counts tones today (grep
  "distinct|unique|histogram" over `Art/tools/*.ps1`: nothing): L1 writes `Art/tools/sample_tones.ps1` (proposed: a box,
  colours quantised to 5 bits a channel, the count holding over 0.5 % of the box, mean colour, a 16-bin luminance
  histogram); L2 reuses it. `bash Art/suite.sh base body` PASS.
- **Gate**: the owner installs the addon, styles a model of their own, bakes, exports, sees it in Unreal beside the
  landscape, names the preset numbers.

### L2. The Unreal post-process lighting layer (section 56)

*BUILT 2026-09-24 (VEHICLE_BUILD_SYSTEM 56): `UGTLookSubsystem` (Source/GrandTour/Look/) puts one transient unbound
post-process volume on every game world with `M_GT_PostLook` (Before DOF; `Art/setup_look_l2.bat`) and, behind
`gt.Look.Kuwahara` (off), `M_GT_PostKuwahara`; `gt.Look.Post` 0/1/2 flips it, `gt.Look.Debug` 1-5 are the probe views.
BaseColor exists under Substrate (GBuffer format 0). X = scene / PreExposure / base / (sun lux / pi), measured on the
Hide (lit 0.5+, cast shadow < 0.1) -> Clear 3 bands at 0.20 / 0.45, soft 0.08, shadow tint 0.55 0.62 0.80, lit 1.00 0.96
0.88, InBand 0.25, warp 1.5 px, lift ~0.012-0.020, exposure fixed at EV100 0.25 (the car copy's red 252 -> 236), the
sun's source angle 0.05 deg; soft two-band sets for Overcast/Rain/Storm and a Snow set, unrendered. r.CustomDepth=3 is
on (this stage); the water stays out of the pass as After-DOF translucency (it writes no stencil). Ford frame ms off /
on / Kuwahara 17.15 / 18.05 / 21.18 and 18.63 / 18.76 / 21.47. Every number PROPOSED, UNMEASURED; found: the mud
patch reads darker than the landscape's Mud row under the pass (base colours, L4's). Gate: the owner drives The Hide
and L_Proving with gt.Look.Post on and off and names the band count, tints, terminator, warp, exposure and Kuwahara.*

- Keep deferred lighting and hard virtual shadow maps (the sun's light source angle near 0; the sun is spawned per
  level, `setup_m0.py:88`, `setup_m1_track.py:181`: the agent finds every one).
- **The post material**: per-pixel light amount = SceneColor / BaseColor (guarded, proposed max(BaseColor, 0.02)),
  quantised into 2-3 bands with a short soft terminator (proposed 0.08), recomposed as BaseColor x a warm lit tint or a
  cool shadow tint (proposed shadow tint 0.55, 0.62, 0.80 linear, unmeasured; the lit tint proposed by the agent). A
  low-amplitude stroke-noise UV warp of the image (proposed 1.5 px at 1080p). An anisotropic Kuwahara filter behind a
  cvar (proposed `gt.Look.Kuwahara`, the `gt.*` family of `gt.Water.Diag`; radius proposed 4 px). A grade with lifted
  blacks; no bloom, no lens flare, no film grain.
- **Exclusions**: custom stencil masks so translucent water and the emissive dashboard skip the band pass (custom
  depth-stencil is not enabled in `Config/`: the stage sets it and says so).
- **Weather**: the states are Clear, Overcast, Rain, Storm, Snow (`Source/GrandTour/Weather/GTWeatherStateDefinition.h:90`,
  defaults from `GTWeatherStateDefinition.cpp:49`). Overcast and Rain (and Storm) get their own band settings, a soft,
  low-contrast set, or they read as mud; Snow's set unchecked.
- **Frame cost**: Kuwahara's ms measured on The Hide's ford steps (`Art/ford_shots.bat`, the `GTWATERSTATS` lines,
  `Source/GrandTour/Terrain/GTWaterSheet.cpp:228`) because the water solver slows under 15 fps (WATER_PLAN section 6).
- **Gates**: the pictures `hide_1_valley`, `hide_6_bog`, `hide_10_rally`, `hide_13_rut_low`, `hide_22_ford_bank`
  (`Saved/Screenshots/M6`, a full `Art/hide_shots.bat` run each side) before/after with the samplers (distinct-tone
  counts in the sky, a panel of the car, the ground; the band histogram); frame ms per step before/after on a quiet
  machine, Kuwahara on and off; the full suite once; the owner's look on The Hide and L_Proving.

### L3. Sky, foliage and atmosphere (section 58)

*PLANNED 2026-09-26 from `docs/prompts/LOOK_L3_sky_foliage_haze.md`, before any build; drafted by the Opus agent, reviewed
and amended by Fable the same day (the dome static, the frame budget and cut order, the far water, the sun disc): the
reasoning is the main session's, the agent executes. Every number PROPOSED, UNMEASURED
unless marked as an existing one reused (L2's LitX 0.75, L6's tone step 0.183, jitter and dab, M_GT_Foliage's wind).*

*BUILT 2026-09-26 (VEHICLE_BUILD_SYSTEM 58) as planned, the numbers above; L3 took section 58, so L4/L5 moved up one to
60/61 (and WATER_PLAN's R2-R3b to 59-61). The dome route held: ground box Sky 1 / 0 0.42 against 0.34 for a repeat, the
Debug 6 flags identical. Found and fixed: the first build's dome collided (a car near the origin launched; the NoCollision
profile). Ridge saturation 0.541 -> 0.054, blue - red -13.6 -> +8.6, one histogram peak either way; 3000 clumps (6000
cards) on The Hide; DabNormal ships 0 (under the noise); the stage +0.1 to +0.3 ms on the ford, under the 1.0 ms budget:
nothing cut; full suite 23 PASS + the ruts flake. My look: the sky flat and painted but pale, not cobalt (HorizonPow the
first dial); the haze strong. Gate: the owner drives The Hide in Clear and Overcast with the three switches.*
*Dials applied 2026-09-26 (VEHICLE_BUILD_SYSTEM 58, 'Dials applied'), the owner's first named set over the numbers above
(which were the first build's): HazeMix 0.35 -> 0.15, HazeEndCm 600 -> 1200 m, HorizonPow 1.5 -> 3.0, zenith 0.10 0.22 0.55
-> 0.04 0.10 0.45, the Scrub card tint 0.18 0.32 0.12 -> 0.08 0.20 0.06. Sky top 170 196 222 -> 99 141 211; ridge
saturation 0.054 -> 0.208 with the haze; blades / grass luma 1.40 -> 1.06. Still the owner's to move.*

The BACKDROP (the sky, not lit) and the DISTANCE (a colour operation on what is lit and banded): no band added, none
moved on the ground. Today: SkyAtmosphere, Sun 8.0, SkyLight real-time capture, height fog; no cloud although every
state carries a CloudCover (Clear 0.1, Overcast 0.9, Rain/Storm/Snow 1.0); no foliage anywhere.
- (a) **The sky.** `UGTLookSubsystem` spawns at BeginPlay, beside its volume, one transient actor: the engine's Sphere
  at a **10 km** radius (the far plane is infinite, reversed Z; 10 km is past every leg's 2 km grid), spawned at the
  world origin once (every leg's grid is 2 km, so a 10 km sphere at the origin surrounds every camera; the gradient and the
  clouds are on the view direction, so the dome's offset never shows), wearing a dynamic instance of `M_GT_Sky` (/Game/GrandTour/Materials): unlit, TRANSLUCENT in the
  Before-DOF pass (standard translucency renders into scene colour before the post chain), two-sided, Apply Fogging
  off. Per pixel, on the view direction d: horizon weight h = (1 - max(d.z, 0))^**1.5**; sky = lerp(zenith **0.10
  0.22 0.55**, horizon **0.62 0.72 0.86**, h), linear. Clouds: a 3D value noise on d at a cell of **0.333** (a sixth
  of the sky's 2-unit width) plus **0.12** x a second at a fifth of that (the ragged edge), at d + CloudOffset; cloud
  where it passes a cut from the noise's own quantiles (simulated, as L6's 0.366), so the covered share of the upper
  sky is the state's CloudCover. Two flat tones: light **0.92 0.92 0.90**, underside **0.70 0.74 0.84** where the
  point **0.08** below is clear (each blob's lower rim). Value: x LitX 0.75 x SunRef (the band pass's own: a cloud as
  bright as a 0.92 paint in sun) x SkyScale. CloudOffset advances **0.002** a second along the state's WindYaw,
  accumulated on the CPU (a wind change turns the drift, no jump). No sun disc (the hard sun is L2's; the atmosphere's own disc is covered by the dome, as in the references).
  **The weather reaches it** as instance parameters from `UGTWeatherSubsystem::GetCurrent()` (the blended state, storm
  pressure on top) every tick; not a collection (MPC_Weather has no CloudCover; setup_m1_weather.py stays as it is).
  **Exclusions**: bVisibleInRealTimeSkyCaptures, bVisibleInReflectionCaptures, bVisibleInRayTracing, CastShadow,
  bAffectDynamicIndirectLighting, bAffectDistanceFieldLighting false; bHiddenInSceneCapture true (the rain's top-down
  occlusion capture must not see a lid); no collision; TranslucencySortPriority **-1000** (under the rain and spray).
  Translucent writes no depth and no GBuffer, so Lumen's screen traces, reflections, the fog, the aerial perspective
  and the band pass see today's far-depth sky under it (depth > SkyDepthCm: the sky branch, warp and lift, unbanded;
  BaseGuard never meets it). Rejected by the engine source: IsSky (with one in the scene the real-time capture renders
  only IsSky meshes, ReflectionEnvironmentRealTimeCapture.cpp:745: the painted sky lights the world, or the sky light
  goes black); an opaque dome (fogged at 10 km, and a surface Lumen's screen traces can hit). **Measured**: Sky 1 / 0
  with the camera held, the ground box and car box means against the same picture taken twice (the noise);
  gt.Look.Debug 6 with the dome on (sky box green, 0 % red). **The alternative**, the sky drawn in M_GT_PostLook at
  depth > SkyDepthCm, cannot move the lighting at all; taken only if the pair fails, because the dome keeps the sky
  its own material (a painted sky, a sun disc later) and the post material to the light and the distance.
- (b) **The haze**, in M_GT_PostLook behind `Haze` (gt.Look.Haze): a = saturate((depth - **60 m**) / (**600 m** -
  60 m)); on the displayed colour c AFTER the recomposition (banded, or a base-less pass-through), before the lift:
  c = lerp(luma(c), c, 1 - a x (1 - **0.5**)), then lerp(c, tint **0.70 0.78 0.90** x LitX x SunRef, **0.35** x a).
  After, because before the tints the shadow tint would multiply the haze tint again and the haze would scale with the
  band; mixed toward one lit pale colour, the far ground loses contrast and gains value (ref_04's town). Not the sky,
  not stencilled pixels (so the far water stays unhazed: L4's, named there); the height fog is in SceneColor under it. Haze 0 skips the block. Measured on the ridge box:
  mean saturation (max - min) / max and mean blue - red off / on, the band count (histogram peaks) unchanged; the car
  box (< 60 m) unchanged. **Build**: the haze lines go into setup_look_l2.py's M_GT_PostLook (the one change to it,
  master default Haze 0) and setup_look_l3.py runs setup_look_l2.py first: a re-run of either builds the same material.
- (c) **The card material** `M_GT_FoliageCard`: a fresh copy of M_GT_Foliage each run (two-sided, the wind WPO on
  MPC_Weather and its MF_Weather call as they are), Masked (clip **0.5**), InstancedStaticMeshes usage (L6's lesson),
  one Custom node in front of MF_Weather. Mask: UseCardMask 0, a PLACEHOLDER fan of **5** blades from the card's foot,
  each an ellipse tapered to the top (lengths **0.7-1.0** of the card, half-width **0.09**, leaning **+-30 deg**), from
  the instance-local position (no UV needed); UseCardMask 1, the texture CardMask (R mask, G tone: the owner's card).
  Colour: the tint (**0.18 0.32 0.12**, `MI_GT_FoliageCard_Scrub`), L6's jitter (+-0.04, +-3 deg), per blade one of
  three tones tint x (1 + k x 0.183), k = -1/0/+1 at 25/50/25 %. Normal: world space, normalize(lerp(vertex normal,
  up, **0.7**)), so a clump lights as one mass; roughness **0.9**, specular 0, default lit (no subsurface, no
  translucency). `DabNormal` 0/1: L6's procedural dab on the card's plane at NormalStrength 0.5, fading at 40 m;
  shipped on or off by the clump picture pair.
- (d) **The placement**: a `Foliage` HISM in AGTTerrainDressing beside Stones/Posts/Rocks, no collision, casting
  shadows; FoliageMeshPath `/Engine/BasicShapes/Plane.Plane` (the PLACEHOLDER, the stones' convention),
  FoliageMaterialPath `MI_GT_FoliageCard_Scrub`. Rebuild(Spec): a jittered grid at FoliageDensity **0.025** a m2 (one
  clump per 40 m2); a point is kept on the Scrub layer (LayerAt 4) with no channel dig, at least **6 m** outside the
  road's edge (route distance minus half width) and the alt routes'; nearest the route first up to **3000** clumps;
  each **2** cards crossed (FoliageCardsPerClump; an owner's clump mesh takes 1), random yaw, scale **0.8-1.3** of a
  **1.2 x 1.5 m** card. FoliageCount in LastMessage and the terrain test's dressing line; density 0 places none.
- (e) **Switches**: gt.Look.Sky (the dome hidden), gt.Look.Haze, gt.Look.Foliage (every dressing's Foliage hidden: no
  draw, no shadow, out of Lumen), 1 by default, -GTLookSky= / -GTLookHaze= / -GTLookFoliage=. 0 = today pixel for
  pixel: a full run with all three 0 against the pre-L3 run, mean |difference| per channel.
- (f) **Weather**: Clear and Overcast rendered. Nothing forces a state from outside today (the run mode sets the leg's
  start state; the M3 tests call SetState in code): gt.Look.Weather <Id> (-GTWeather=) is added, the subsystem calling
  SetState(FindState(Id), instant) while the target differs; the states' numbers untouched; pictures log the values.

**Applied**: every level gets the sky and the haze through the subsystem; The Hide the foliage through
`setup_look_l3.py` calling RebuildDressing (as L6) and saving L_Leg03; L_Proving not re-dressed unless the owner asks.
**Later, not built**: the owner's cards by path, a sun disc, snow on the cards, other layers' tints. **Pictures**:
`Art/sky_shots.bat` (-GTShotsFrom=50): 50 the rally posts at 640 m behind the parked car, pitched up **15 deg**; 51
hide_10's spot, the far ridge; 52 a clump within 20 m of the route from 7 m; each all on, Sky 0, Haze 0, Foliage 0,
Clear then Overcast (L2, L6 on), plus a repeat, Debug 6, DabNormal 1; hide_10 and hide_22 from full runs before and
after. **Frame cost**: ford_shots' GTWATERSTATS ms per step all on / Sky 0 / Haze 0 / Foliage 0, each twice, clumps in
frame logged; the full hide run's seconds. **Budget**: the whole stage a proposed **1.0 ms** on the ford step at 720p;
over it, cut in this order and say what was cut: the card shadows (CastShadow off), the sky's second noise octave, the
clump cap to 1500. **Tests**: terrain after each change, the full suite once. **Unknowns**:
Lumen at the terrain's silhouette against a translucent dome; the noise's share against CloudCover; the masked cards'
shadow cost (the wind invalidates cached shadow pages); LayerAt over 100k candidates; how far 3000 clumps reach; snow
on the up-blended normal; TSR on the drifting clouds.

### L4. Water and mud in the style (section 60)

- `M_GT_Water` (`Art/Unreal/setup_m6_water.py:417` FORD_MATERIAL; `setup_m6_hide.py:45`, `build_water_material` :557),
  `M_GT_Mud` and the landscape's Mud and Bog rows (`build_landscape_material` :258) get the same band treatment: fewer
  ripple details, flat colour bands, foam and spray as flat shapes, the photoreal muddy_tracks set replaced or
  posterised (the owner's decision then). The water is translucent and skips L2's pass (stencil), so its bands live in
  its own material. The mud plan's unnamed list in the BACKLOG stays.
- **Gates**: the water and mud test lines unchanged (look only, no physics; `bash Art/suite.sh water mud terrain`), bog
  and ford pictures before/after (`bog_shots`, `ford_shots`, like with like), the owner's look.

### L5. The owner's tuning pass (section 61)

- The owner drives and names numbers across L1-L4. Consistency checks: one style preset
  (`Art/Blender/gt_paint_preset.json`, every bake from it), one shadow tint, one haze. A material takes at most two MPCs
  (the landscape holds Weather + TrackPaint): opaque surfaces get the tint from the post layer; the translucent water
  copies the same constant at build time.

### L6. The runtime painterly surface material (section 57)

*PLANNED 2026-09-25 from `docs/prompts/LOOK_L6_runtime_paint.md`, before any build. Every number PROPOSED, UNMEASURED
unless marked the bake's. L6 takes section 57: L3/L4/L5 move to 58/59/60, WATER_PLAN's R2/R3a/R3b to 58/59/60.*

*BUILT 2026-09-25 (VEHICLE_BUILD_SYSTEM 57) as planned, the numbers above. Found: the dressing drew the engine's default
checker in the game until now (M_GT_Environment has no InstancedStaticMeshes usage flag; not given one here). A HISM's
Local space is the component's: the edge term runs in Instance & Particle Space. The dab tile's seam 4.31 x / 3.47 x: the
procedural dab ships (DabTile 0). Surface 0 = the plain graph (twin cube 0.30 a channel, 0.00 % over 8); ford frame ms
off / on 16.54 / 16.64 and 16.69 / 16.77; compose 1 / 1 band on the stone, post and rock; full suite 24 PASS. Gate: the
owner drives The Hide with gt.Look.Surface on and off and names the numbers.*
*Owner's look 2026-09-25 (the gate): "can't really tell any difference between the two. However, I am happy to move on, it will do for now." Stands as built, switch on, no number named; the dials to raise later stay proposed (tone step 0.183, grain 0.08 / 0.1, wear lighten, NormalStrength 0.5, the 40 m fade). L_Proving not re-dressed (VEHICLE_BUILD_SYSTEM 57).*

The engine-side twin of the GT Paint bake: `M_GT_Painterly` gives any unbaked mesh the painted surface from the mesh
alone, and L2's band pass then lights it. It shapes the SURFACE only (local colour, grain, edge wear, the dab normal);
it never quantises the light, so a stone shows L2's bands once, not twice. What the dressing wears today (grep):
`AGTTerrainDressing` puts the engine's cube (stones, and the 12 ford rocks in the SAME `Stones` component) in
`MI_Env_Greybox` (0.55 grey, roughness 0.85) and the cylinder (rally posts) in `MI_Env_Marker` (0.9 0.35 0.1), both
children of `M_GT_Environment` (BaseColor/Roughness through MF_Weather, porosity, CanPool; the track-paint normal and
WPO behind TrackStrength, 0 on both), paths as C++ defaults in `GTTerrainDressing.h` (DA_Terrain_Hide holds none). The
water bars are landscape ridges (`WaterBarArcs`, found by trace): they wear the landscape material, tuned, not mine.

**The material.** `M_GT_Painterly` = a copy of `M_GT_Environment` (so the weather still wets it and 0 is that graph)
with one Custom node before MF_Weather and the Normal pin. Per pixel, in this order:
- (a) **Local colour**: the tint is the instance's `BaseColor` (the plain instance's own colour), posterised to **3
  tones of value** k = -1/0/+1: tint x (1 + k x **0.183**), the bake's level spacing reused ((1 + wear_lighten 0.25 -
  (1 - grime 0.3)) / (tones 4 - 1)); k from a 3D world value noise at **35 cm** (the bake's grain_scale 0.35 m) cut at
  shares **25/50/25 %**. World space, so no UV is needed. The lighting is never posterised.
- (b) **Brush grain**: stroke-shaped value noise on the dominant world plane (hard tri-planar pick by the vertex normal,
  so a flat face keeps one plane), **60 cm** along the stroke x 12 cm across (the preset's grain_stretch 5), horizontal
  on walls; the top and bottom **15 %** of the noise are light and dark strokes: albedo x (1 +- **0.08**), roughness
  -+ **0.1**. Binary strokes, so the tone count stays small. World-scaled: a mesh's scale does not stretch it.
- (c) **Edge wear**: no curvature bake exists. Chosen: an edge term from the mesh's own local bounds - per instance-
  local axis the face is not facing, the distance to that bounds plane x the instance's scale on the axis, in cm (a
  box: the cube's 12 edges; `EdgeRound` 1 on the post instance: the cylinder's rims, the cap by its radius). Width
  **2 cm** (the bake's wear_width) or **1.5 px** at the pixel's depth, whichever is wider, broken by the bake's
  wear_breakup **0.5**; the wear tone is the bake's: 0.35 (wear_tint) of the way to wear_colour #F2EDE4. Rejected: the
  screen-space change of the world normal - the cube's faces carry split normals, constant per triangle, and pixel-quad
  derivatives never cross a triangle, so it gives nothing on a hard edge and a uniform tint on the cylinder's smooth
  side (reasoned, not measured). Its cost is inside the whole material's frame ms (step 4), not separated.
- (d) **The dab normal**: `T_GT_DabTile_N` baked once from a 2 x 2 m plane by the owner's OW Painterly Normal Baker
  through GT Paint headless (the preset's 55 cm, aspect 2, jitter 8, untouched), sampled on the dominant plane at a
  **200 cm** tile; its seam measured (mean |difference| across the wrapped edge / the mean between neighbouring
  texels inside). If it does not tile, the procedural dab ships: an oriented ellipse per cell of a **55 x 27.5 cm**
  jittered brick grid (3 x 3 cells searched), each dab a flat facet tilted up to **8 deg**, direction +- 20 deg (the
  preset's rot_jitter). Both are in the material behind `DabTile` 0/1 so the owner can choose. Strength: the
  existing **NormalStrength 0.5**, as `M_GT_Painted`: normalize(lerp(n, dab, 0.5)).
- (e) **No specular**: roughness floored at **0.75**; metallic 0 and no clear coat as the plain graph already has.
- (f) **Per instance**: PerInstanceRandom -> value **+- 0.04**, hue **+- 3 deg**, before the posterisation.
- (g) **Distance**: the dab normal's strength fades linearly to 0 at **40 m**; haze and desaturation are L3's.
- (h) **The switch** `gt.Look.Surface` 0/1 (and `-GTLookSurface=N`): the plain graph and the painted one meet in lerps
  on a `Surface` scalar, so 0 returns the copied graph's own values. Not a parameter collection: the copy already
  holds two (MPC_Weather, MPC_TrackPaint) and a material takes two, so `UGTLookSubsystem` wraps every mesh slot whose
  base material is `M_GT_Painterly` in a dynamic instance (once a second, as it stencils) and sets `Surface` on each.
  Checked by a same-run picture with the plain `MI_Env_*` put back beside the Surface 0 one.

**Applied in this stage**: `MI_GT_Painterly_Stone` and `_Rock` (from MI_Env_Greybox) and `_Post` (from MI_Env_Marker,
EdgeRound 1), each copying its plain instance's parameters; the ford rocks move into their own `Rocks` component so
they can wear their own instance; the dressing's C++ defaults point at the instances and The Hide's dressing is
rebuilt by `AGTTerrainBuilder::RebuildDressing` from `setup_look_l6.py` and saved (the builder button's path; L_Proving
waits for setup_m6_proving). Later, not built: L3's foliage cards, the tests' engine cubes, what the owner drops in.
The landscape is tuned and stays.

**Pictures and gates.** `Art/dressing_shots.bat` (-GTShotsFrom=40, the bog run's pattern): the car parked away, then
the track stones at 1322 m, the rally posts at 640 m and the proudest ford rock, 7 m off at a 25 deg field of view,
each shot with Surface 0, 1, both again under gt.Look.Debug 1 (BaseColor) and with the plain instance; L2 on.
`sample_bands.ps1 -Dressing`: tones, the 16-bin histogram and the grain (5-bit tone changes per 100 px along three
lines through the box), off vs on; the compose check (clusters of look / BaseColor per pixel on the object, off vs on:
the same count = one set of bands); plain vs off (the switch's 0). hide_10_rally and hide_22_ford_bank from a full run
before and after. The dab tile's seam number. Looks, said as looks. **Frame cost**: `ford_shots.bat` GTWATERSTATS
ms per step, Surface 0 and 1, each twice; the full hide run's seconds, 0 and 1. **Tests**: `suite.sh terrain` after
each change (88 stones, 30 posts, 12 rocks, solid=1), the full suite once.

**Unknowns**: whether instance-local space is what the Local transform gives on a HISM (the edge term needs it; a
picture shows it); the Custom node in the ray-tracing hit shaders (no ddx/ddy used: the pixel footprint comes from
the depth and the field of view); whether a posterised noise reads as paint or as camouflage at 35 cm; the dab tile's
seam; Lumen's surface cache keeping the old albedo for a while after a flip; the cost of the 3 x 3 dab search.

## 4. Open decisions for the owner

1. The preset numbers (L1): tones 4, grain scale 0.35 m, grain strength 0.15, wear width 2 cm, wear lighten 0.25, grime
   strength 0.3, highlight off.
2. The post numbers (L2): 2 or 3 bands, terminator 0.08, shadow tint (0.55, 0.62, 0.80) linear, the lit tint, warp
   1.5 px at 1080p, Kuwahara radius 4 px, the black lift, the soft weather set; the haze and cloud numbers (L3).
3. Whether the mud's photoreal muddy_tracks set goes (L4): posterised in the material or replaced.
4. The Kuwahara filter on or off, after its cost on the ford steps is known (L2).
5. Whether foliage cards are the owner's models or a sourced CC0 set (L3).

## 5. Costs and unknowns

- **Kuwahara at 1080p vs the water solver's cliff**: the solver slows under 15 fps (WATER_PLAN section 6). An
  anisotropic Kuwahara at radius 4 reads tens of taps a pixel (unchecked); rendered runs have been bimodal before (real
  time vs about a quarter speed on one build, 2026-09-18): take repeat runs.
- **The post layer misreads translucency and emissive**: SceneColor / BaseColor means nothing where the GBuffer holds no
  BaseColor (the water, spray, rain, the emissive dashboard, the sky): stencil and depth masks; custom depth-stencil off
  today.
- **The renderer**: Lumen's bounce enters the light ratio (as light); Lumen reflections enter it too, and the look wants
  none; SceneTexture BaseColor under Substrate (GBuffer format 0) and auto exposure's pre-exposed SceneColor both change
  the ratio. All unchecked.
- **The car loses features**: `M_GT_Painted` as decided has none of `M_GT_Vehicle`'s runtime Dirt, MF_Weather wetness,
  MF_Dents or clear coat; L1 reports what the car loses (keeping MF_Weather ties it to rule 6's re-link). Closed
  2026-09-24 (L1 follow-up 3): the car keeps M_GT_Vehicle and takes the bake as textures (PaintAlbedo / PaintMask /
  PaintNormal behind UsePaint), so it loses nothing. The UV (follow-up 4, 2026-09-25): Bake gives a single source
  with no UV map a smart-project GT_UV on the object itself (the bake copy's parameters; modifiers not applied, so
  a Mirror's halves share the islands) and keeps it on later Bakes; Unwrap for Paint does the same from the panel.
  frontDoors, passengerDoors and rearPanel carry it (UV0 area 0.5988 / 0.5007 / 0.6461 in Blender and Unreal).
- **Bake memory per asset**: 1K albedo + 1K mask, about 4 MB each as RGBA8 PNG, about 0.7 MB each in Unreal as BC1
  with mips; 2K is 4x (arithmetic, unchecked). A multi-object asset (the car: SK_RangeRover + the SM_RR_ panels) bakes
  into one atlas only if its UVs do not overlap (unchecked). Pointiness follows vertex density: coarse on a low-poly
  blockout (dents already failed to render right there, 2026-09-12), so bevel carries the wear.
- **Blender 5.1 API drift**: the bake API (Cycles; bake types from RNA), node group interfaces and versioning of the
  shared `GT_Paint` group (stamp a version; Apply Style rebuilds an old one). Unchecked on 5.1.
- **The MCP single-client constraint**: the owner's live Blender and a scratch instance cannot both hold 9876;
  headless tests need no MCP.
- **The landscape's cost**: 21 texture samples a pixel today (section 48: 12 painterly + 9 mud), plus a post pass on top.
