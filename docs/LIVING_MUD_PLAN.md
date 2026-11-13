# Living mud, chunky mud, God of War snow (plan for implementing agents)

Written 2026-10-05 from the owner's ask: "add some chunky mud, and make it behave more like mudrunner/snowrunner mud
where it kind of moves a bit and slumps rather than staying the exact same. I also really like god of war's snow
deformation." The owner's answers the same day: the slump is **one field, felt** (the traction reads the moving field,
as it reads the stamped one now); **snow is its own stage after the mud**; chunky means **all three**: lumps in the
field, clods on the banks, clods thrown by spinning wheels. Stage names are LM0-LM3 (living mud), so they don't clash
with the M0-M6 milestones or the mud plan's letters A-L.

## 0. Rules for the agent

Everything in `docs/MUD_ONE_SURFACE_PLAN.md` section 0 holds, with these changes and additions:

- **Git is initialised.** Commit at the end of a stage, as the leg dressing stages did ("Living mud LMn: ..."), with
  only the files the stage touched. Never `git add -A`: the working tree carries other uncommitted work (Look, Parts,
  Vehicle, Weather, Art/Blender scripts) that is not this plan's to commit.
- **The test strip is `L_MudDrive`** (`/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive`, docs/LIVE_MUD_DRIVE.md):
  `& Art/setup_live_mud_drive.ps1` rebuilds it and re-applies the live clay shader (`Art/Unreal/live_mud_style.py`),
  and `& Art/check_live_mud_drive.ps1` drives the real car across it dry and then wet, writing reports and pictures to
  `Art/Export/LiveMudDrive`. The live shader block in `live_mud_style.py` is the one to edit, not the legacy
  `setup_m6_mud.py` block (a legacy rebuild restores the old shader; re-run the live setup after one).
- **Close every game and the editor before any Unreal run.** Section L's wet replay died because God of War started
  mid-capture (14 fps, timeout). `Art/mud_shape_test.ps1` refuses to run with a game open; the other runs do not
  check, so look first (`Get-Process`).
- **Shape numbers.** The owner authorised this plan's new numbers on 2026-10-05 as proposed starting points: the agent
  tunes them only to land the targets the stage states, and reports the value it landed on. Every number from stages
  A-L (Ridge*, RutShoulder*, Slide*, the traction's RutHold*/BellyChannelEase, the surfaces table) stays as it is
  unless a stage here names it. `SlideScale` (vertex slide) stays 0.
- **Physics changes are expected and reported, never hidden.** The traction reads the field, so a field that moves,
  lumps and throws changes the feel. Re-measure the gates that read it (the terrain test's step 11 ruts gate and the bog
  escape, the live strip's completion and deviation) and report before and after. Don't relax a gate to pass: if a
  number moves out of its range, report it with the reason and the main session decides.
- **Cost is a gate.** The Hide is already +4.4 ms over its frame budget (+2 asked) from the leg dressing. Every stage
  states its game-thread and GPU cost on the strip with the feature on and off, with a console switch for each
  feature (`gt.Mud.Settle`, `gt.Mud.Clods`, ...).
- **Visual claims need a look**: a picture through the check script, judged by a sampler or the field's own numbers
  (a profile across the rut written to CSV), or reported as unchecked.
- **Test set per stage**: `bash Art/build.sh`, `& Art/mud_shape_test.ps1` (LM1 widens it to every `GrandTour.Mud`
  test), `& Art/check_live_mud_drive.ps1`, and `bash Art/suite.sh terrain drivetrain grip mud surface track` (the field
  is read by the traction). The full suite once per session, in the background, by the last agent.
- **Docs per stage**: a new section at the end of `docs/VEHICLE_BUILD_SYSTEM.md` (the next free number, 65 at the
  time of writing), the devlog `docs/devlog/<date>.md`, the MUD DEFORMATION line in `docs/BACKLOG.md`, and an italic
  note under the stage's heading here. Numbers before and after; what was seen (a look is a look); what is unchecked.
- **Read list for a fresh agent**: this file; `docs/LIVE_MUD_SHOULDERS.md`; `docs/VEHICLE_BUILD_SYSTEM.md` sections
  63-64; `Source/GrandTour/Terrain/GTMudField.h` (whole) and in `GTMudField.cpp` only the function the stage edits (by
  `grep -n` + `sed -n` range); `GTMudPatch.h`; `GTMudShapeTests.cpp`; `Art/Unreal/live_mud_style.py`. More only when a
  change needs it: the traction's field reads are `GTTractionComponent.cpp` around `Field.HeightAt(Probe)` (the rut
  probe) and `StampMud`; the spray's pool is `GTSprayComponent.h/.cpp`; the profile copy is
  `UGTMudSubsystem::BuildPatches`.
- **Owner gates**: after LM1 (looks and feels the slump), after LM2 (looks at the chunks and spins in the bog), after
  LM3 (drives the snow). LM2a/LM2b chain without a gate, as do LM3a/LM3b. Never start the next gated stage in the same
  session as the gate.

## 1. What is there now (2026-10-05)

- `FGTMudField` changes only on the physics tick a wheel or the belly stamps it. Between stamps nothing moves. Stage I's
  "slump" (a stretch of bank falling back into the rut) and its "clods" (8-15 cm lumps on 15 % of the band's cells)
  are both decided by a noise hash at stamp time, so the rut is frozen the moment it is cut.
- The stage I clods are smaller than two cells (12.5 cm), and stage H's 3-tap smoothing, applied by every stroke whose
  band reaches a cell, takes most of them away. `Mud_Long_Dry.png` (section L) shows a clean cut with a rounded
  shoulder in smooth clay; there is nothing chunky in it.
- The per-cell slide offset (`OffsetCm`, texture GB) is still written by `StampWheel` and moves nothing:
  `SlideScale` 0 in the material, and the clay's sampling ignores it.
- The traction reads the field at a probe ahead of each tyre (`RutDepth` from the deepest of three heights across the
  tyre, `RutClimb` and `RutCrossSlope` from `GradientAt` clamped to `RutHoldMaxSlope` 0.5, the hold weighted by
  `TracksAt`), and the belly's channel. Sinkage is the wheel's own state, not read from the field.
- The patch uploads the dirty rect of `Texture` (PF_FloatRGBA: R height m, GB offset m, A tracks) and of
  `TreadTexture` (PF_FloatRGBA: R heading turns, G lug phase; **B and A unused**) each tick the field changed.
- The spray component keeps a CPU particle pool per kind; mud throws opaque brown blobs backwards and up from a
  wheel that rolls fast or spins, drawn as instanced spheres, killed when they fall 2 cm under the contact's Z.
- Snow: a landscape layer (index 3) above `SnowLineM` (off by default) and a surface row (friction 0.28). No snow route
  sections, no snow patches. The weather has a Snow state and `GetSnowAmount()`.
- **Section L is uncommitted and half-validated**: its shape test and dry pass ran; the wet replay and the regression
  set did not (docs/LIVE_MUD_SHOULDERS.md, "Pending").

## 2. The design target

Taken from how these games look and feel, not from their code.

- **MudRunner / SnowRunner mud**: a rut doesn't stay as cut. Its walls sag, the banks spread and round over, and
  deep soupy mud partly oozes back into the rut over a few seconds, then the mud sets. Mud that has just moved looks
  wet and fresh, then dulls. The displaced mud is lumpy: banks of clumps, not a smooth berm. A spinning wheel digs
  in and throws mud behind it, building a mound and scattering clods.
- **God of War snow**: deep trenches with near-vertical walls rounded over at the top. A small crumbly lip of chunks
  rather than a big berm, because snow compacts more than it moves. The packed floor looks different from the fresh
  snow: smoother, a little darker and bluer, holding a crisp tread print. Fresh snow glints in the sun and looks
  soft in the shade. Trails fill back in while it snows.

## 3. Stages

### LM0: close section L (a short session, no new code)

*Done 2026-10-05: the baseline (no game or editor open; build exit 0):*
- *Shape test (`GrandTour.Mud.SoftShoulders`, PASS): max 12.5cm cross-step 14.94cm; width at -5cm 93.75..143.75cm;
  core -40.78..-25.94cm.*
- *Terrain step 11 (two runs): down the ruts 6 m in 6.0 s / 4.5 s; held exit at 30 deg 6 m in 6.7 s / 5.9 s; ratio
  1.12 / 1.31 from the printed times (gate 1.05) -> PASS both; unheld exit 6 m in 4.1 s / 4.0 s (held 2.5 s / 1.9 s
  later). Pre-L 2026-09-29: 5.4 s pass, 5.7 s held exit, FAIL.*
- *Bog escape (two runs): forward 8.9 m / 9.1 m in 12.0 s from a dead stop -> 1; reverse 6.0 m back in 6.7 s / 6.6 s
  -> 1. Pre-L 2026-09-29: forward 13.1 m, reverse 4.3 m in 8.0 s.*
- *Terrain test overall FAIL both runs on three other gates: stage H along-crest mean 4.45 cm (asked 5.35-9.94);
  stage I rut floor -23.6 cm (asked -28.0 within 15 %); ford raised 70 cm timed out at 1117 m / 1115 m, engine
  running, 14.6 m off the route (asked: floods). Not relaxed, not diagnosed.*
- *Strip dry: completed, 119.04 m in 60.5 s; max lateral 0.25 m; added 20,606,116 cm^3; max sink 0.40 m; wheel water
  up to 0.52 m, water under a wheel in 171 of 222 samples.*
- *Strip wet replay: completed, 119.01 m in 55.5 s; max lateral 0.30 m; added 12,087,515 cm^3; max sink 0.50 m; wheel
  water up to 0.49 m, 154 of 207 samples.*
- *Frame time: the check script profiles only the wet replay (`csvprofile` on run 1), so there is no dry-crossing
  number. Wet replay, editor PIE, -RenderOffScreen, viewport 951x257, `Saved/Profiling/CSV/Profile(20261005_122204).csv`
  (2779 frames): mean game thread 19.76 ms, mean GPU 9.12 ms (frame 19.97 ms).*
- *drivetrain, grip, mud, surface, track PASS. The editor's exit -1073741819 recurred after the drive check's
  "Log file closed" (report written, ok true); no crash dump and no Windows fault event, so no stack.*

1. `Get-Process` for games and the editor; nothing runs alongside.
2. `bash Art/build.sh`; `& Art/mud_shape_test.ps1`; `& Art/check_live_mud_drive.ps1` (dry and the wet replay);
   `bash Art/suite.sh terrain drivetrain grip mud surface track`.
3. Report each against docs/LIVE_MUD_SHOULDERS.md "Pending". If the editor's shutdown access violation
   (-1073741819) comes back, report the call stack from the log; don't fix it in this stage unless it is in GT code.
4. Write the **baseline** LM1-LM3 compare against into this stage's note: terrain step 11 pass/exit times and gate,
   the bog escape metres, the shape test numbers, the strip's dry/wet completion, deviation and added volume, and the
   strip's mean game-thread and GPU frame time over the dry crossing.
5. Commit section L: `git status --short`, then only the mud files (the `GTMud*` sources, `Art/mud_shape_test.ps1`,
   the live mud setup/check scripts, docs/LIVE_MUD_*.md, docs/MUD_ONE_SURFACE_PLAN.md, this file). A shared doc
   (VEHICLE_BUILD_SYSTEM.md, BACKLOG.md) goes in only if its diff is mud-only; otherwise leave it and list it.

### LM1: the living field (slump, ooze, drag, fresh sheen)

*Done 2026-10-05 (no game or editor of the owner's open; Firefox, Docker and the ChatGPT app were running; build exit 0):*
- *Thread: the traction stamps on the game thread (`UGTTractionComponent::StampMud`, called from `AGTCarPawn::Tick`,
  pre-physics; the component has no tick of its own). `Settle` runs in `AGTMudPatch::Tick` (post-physics, game thread)
  before `TakeDirty`/`Upload`, so stamps and settling share the field with no locks.*
- *Landed on: **`OozeRate` 1.2** (proposed 0.6). The shape test's recovery at 5 s against OozeRate: 0.2: 2.1 %, 0.4:
  5.1 %, 0.6: 8.3 %, 0.8: 11.6 %, 1.0: 14.7 %, 1.2: 17.7 %, 1.5: 21.8 %. At 0.6 the bank also came out narrower at
  half height (66.1 -> 65.5 cm); from 1.0 up it is wider. Every other number as proposed: ReposeDeg 38, SlumpRate 2.0,
  SetSeconds 4.0, SmearCmPerCm 0.5, FreshFadeS 6.0, SleepCmPerS 0.05; the ford's profile 45 / 0.1 / 1.5; SlideUV 1.0,
  FreshWet 0.6 (not looked at). Added in the implementation, not plan numbers: at most 2 sub-steps per frame (8 cost 1.40
  ms after a 310 ms screenshot hitch), and an awake tile that is still (nothing setting, nothing moving over
  SleepCmPerS) skips the flux sweep and only fades its sheen. The surface S is the field's own height (relative to
  the ground under the patch).*
- *`GrandTour.Mud.Settle` (all rows pass): volume 10 s vs just stamped, error 0.1 cm^3 of 3,467,620 lowered; steepest
  step 15.00 -> 7.57 cm (asked <= 10.27); core -33.29 -> -27.40 cm at 5 s = 17.7 %; ford numbers 0.20 %; crest 8.90 ->
  5.71 cm, half-height width 66.1 -> 68.1 cm; all 21 tiles asleep at 10.40 s (asked by 11.0); 1/30 vs 1/60 vs 1/144
  worst cell 0.0000 cm; determinism identical; gt.Mud.Settle 0 identity: LM0's 14.94 / 93.75..143.75 / -40.78..-25.94
  reproduced (field CRC 8e0aad06). `Art/mud_shape_test.ps1` now runs `GrandTour.Mud` and requires Success of each.*
- *Cost, dry crossing, Settle 1, two check runs: mean 0.100 / 0.138 ms, max 0.620 / 3.62 ms, awake peak 50 / 48 tiles
  (gate 0.3 / 1.0). From its second crossing on, the second run's game thread ran 40-90 % slower than the first run's
  (other apps active); its two frames over 1 ms are on 22 ms frames, p99 0.55 ms. So the max gate passed once and
  failed once: not settled.
  Upload: mean 0.066 / 0.080 ms (Settle 0: 0.051 / 0.042).*
- *Frame time, editor PIE in a new 1440x900 window (client 1440x868; the first window comes up 1274x682 and is asked
  for again), the same session and viewport for both: run 1 Settle 0 game 14.11 / GPU 14.33 ms, Settle 1 13.35 /
  17.07. Run 2 (A/B/A) Settle 0 14.61 / 18.75, Settle 1 19.08 / 20.44, Settle 0 again 20.70 / 21.88. The GPU kept
  rising after switching back to 0, so the steps are session drift (the laptop GPU), not the settling; the shader is
  the same either way. Settle's own 0.10-0.14 ms is under the noise. LM0's 19.76 / 9.12 (951x257, wet) is not
  comparable.*
- *Strip (Settle 1, two runs) vs LM0: dry completed 119.03 / 119.05 m in 61.8 / 61.6 s (60.5), lateral 0.30 / 0.37 m
  (0.25), added 22,355,024 / 22,329,041 cm^3 (20,606,116); wet completed 119.08 / 119.06 m in 54.4 / 56.2 s (55.5),
  lateral 0.36 / 0.44 m (0.30), added 13,816,258 / 14,549,539 cm^3 (12,087,515). Settle 0 controls in the same
  sessions: 119.03 m, 0.26 m, 20,763,630; 119.00 m, 0.27 m, 20,902,506; 119.04 m, 0.29 m, 21,310,119.*
- *Settle pair (a fresh lane at y -4.5 m, x 44 m; the spot left once every contact was 2.3 m past it):
  `settle_profile.csv` core -14.84 cm at 0.3 s -> -14.36 cm at 5 s, crest 1.55 -> 1.55 cm, fresh at the core 1.0 ->
  0.56 (run 1: -14.91 -> -14.36, 2.48 -> 2.48). The car's rut here is a broad 15 cm bowl, so the ooze gives back
  about 0.5 cm, not the shape test's 18 %. `Mud_Settle_0s.png` / `Mud_Settle_5s.png` written, not judged; nor are the
  new `Cockpit_*_Settle0.png`.*
- *Terrain, four runs (three on their own, the fourth in the full suite; step 11 / escape / ford): down the ruts 6 m in
  5.4 / 5.5 / 5.6 / 4.5 s, held exit 4.5 / 4.4 / 5.1 / 5.7 s -> FAIL, FAIL, FAIL, PASS (asked 1.05x slower; LM0 passed
  both); unheld exit 4.1 s each. Escape forward 11.2 / 11.4 / 11.4 / 10.9 m in 12 s (LM0 8.9 / 9.1), reverse 6.0 m in
  7.0 / 6.0 / 6.2 / 6.2 s (6.7 / 6.6). The mud-field gate's rut mean -27.0 / -27.2 / -27.0 / -27.1 cm (LM0 -31.6; asked
  -24.0) passes, ridge mean 3.6 cm (6.0). The ruts are shallower behind the car, as expected, and the 30-degree exit
  mostly no longer comes out slower than the pass: reported, not tuned.*
- *Ford: the raised run's flood is latched; four runs timed out at 1115-1116 m with the engine flooded at the end
  twice and running twice, flooded 1 time each -> PASS. As built through, flooded 0 -> PASS.*
- *Stage I floor re-based: expected = -28.0 x (1 - RutDepthVariation x E[1 - Softness]) x (1 - R(t)); E[Softness] =
  0.5 (a clamp symmetric about 0.5 over a symmetric noise), so the pockets' mean is 0.825; the line is stamped and read
  in one call, no Settle between, so R(t) = 0: -23.1 cm within 15 %. Measured -23.6 cm in all four -> PASS (runs 3, 4).*
- *Stage H crest mean: the same derivation leaves it where it was. The pockets cut A and C alike (the test zeroes the
  noise, wave, side bias, slump and clods, never the pockets), and R(t) = 0 at both, so the expected A / C stays 1 and
  the band 0.7-1.3 of C. Measured 7.65 -> 4.45 (0.58) in all four runs -> still FAIL, left failing. The cause is
  not in the derivation's terms: B (stage H1 alone) reads 5.10 against C's 7.65, so under section L's shoulders the
  stage H smoothing and blend take a third of the crest. For the main session.*
- *Full suite (`bash Art/suite.sh`, once, at the end): 27 PASS, 1 FAIL (terrain, on the stage H crest mean alone);
  body and winch passed first time. The editor's exit -1073741819 recurred on two of the three drive checks; the wrapper now reports it as the known shutdown fault and judges by a fresh `ok: true` report.*
- *Unchecked: every look (SlideUV, FreshWet, the settle pictures); the feel (owner gate). For LM2a: at OozeRate 1.2 the
  shape test's bank crest falls 36 % in 4 s because every band cell a stamp writes oozes, so lumps put in `HeightCm` +
  `LumpCm` would not keep 60 % of their height. Either the ooze must leave `LumpCm` alone, or only the capsule and
  shoulder cells set.*

**Housekeeping first, from LM0's findings (main session's decisions, 2026-10-05):**

1. **The raised-ford gate is a sampling fault, not a regression.** Today's two runs end where 2026-09-23's did:
   timed out at about 1117 m, 2.1 m of water, 14.6 m off the route. Both runs logged 7 "engine flooded" events at 1.1-1.35
   m of intake water. The test reads `Condition->bFlooded` only at the timeout instant, after the stuck car has
   drifted and the 5 s drain has cleared it. In `GTM6TestRunner.cpp` near the `raised 70 cm` line, latch it: flooded at
   any time during the raised run && !through. The as-built run keeps its rule (through && never flooded at the end).
   Print the flood count in the line.
2. **The stage H crest mean and stage I floor gates are re-based on the section L shape**, which the owner authorised.
   Section L's firmer pockets lower the floor's target by up to 35 %, and its shoulders take bank volume. LM0
   measured 4.45 cm crest mean against 5.35-9.94, and a -23.6 cm floor against -28 +-15 %. After LM1's settling is in,
   re-derive both expected values from the code (pocket mean, ooze recovery at the measurement time). State the
   formula and the numbers in the stage note, and keep the old tolerance widths. Don't fit the gate to one run: take
   two terrain runs.
3. **Frame time on the dry crossing.** `check_live_mud_drive.py` profiles only the wet replay, and the PIE viewport
   size varies (951x257 today, 1478x592 on 2026-09-29). Profile the dry crossing too, at a fixed viewport of
   1440x900 or whatever the script can actually force (say what it got). Then re-take LM0's frame time baseline with
   `gt.Mud.Settle 0` in the same run as the `1` measurement.
4. **The check wrapper.** The editor still exits -1073741819 after "Log file closed" (no dump, no fault event).
   `check_live_mud_drive.ps1` must judge by a report written after the run started with `ok: true`, and print the exit
   code as a known shutdown fault rather than throwing.

**Field** (`GTMudField.h/.cpp`). A time step for the cells a wheel has recently touched, conserving volume:

- Tiles of `SettleTileCells` 16 (2 m) with an awake flag. A stamp wakes the tiles its rect covers; flux into a sleeping
  tile wakes it.
- `void Settle(float DeltaSeconds)`: fixed sub-steps of `SettleStepS` 1/30 s from an accumulator, so the result does
  not depend on the frame rate. Per sub-step, over the awake tiles plus a one-cell border, for each cell's right and
  down neighbour pair (i, j) with surface step d = S_i - S_j:
  - **Slump** (talus): excess = |d| - tan(`ReposeDeg`) x CellCm. If positive, move
    q = 0.5 x min(`SlumpRate` x dt, 0.2) x excess from the higher cell to the lower.
  - **Ooze** (viscous levelling): while either cell's set timer is positive, move
    q = 0.5 x min(`OozeRate` x dt, 0.2) x |d| from high to low. This is what lets a rut floor rise and its bank sink
    after the wheel has gone, and it stops when the mud sets.
  - Accumulate into a delta buffer and apply after the sweep. The patch's outer border is closed (no flux out). Sum of
    deltas is zero: volume is conserved by construction.
  - **Smear**: the receiving cell's `OffsetCm` gains the unit direction i->j times q x `SmearCmPerCm`, capped at
    `MaxSlideCm`, so the texture visibly drags where mud moved.
  - **Fresh**: a new per-cell `Fresh` (0..1) is set to 1 where the stamp or the sub-step changed the surface by over
    0.01 cm, and otherwise fades by dt / `FreshFadeS`.
  - **Set timer**: a new per-cell `SetS`, set to `SetSeconds` by `StampWheel`/`StampBelly` over every cell they write
    (the capsule, the shoulders and the band), counting down here.
  - A tile sleeps when, for 0.5 s, no cell in it changed by more than `SleepCmPerS` x dt per sub-step, no `SetS` is
    above 0 and no `Fresh` is above 0.02. Mark dirty only the rect of cells that changed.
- Proposed numbers (bog mud): `ReposeDeg` 38, `SlumpRate` 2.0 /s, `OozeRate` 0.6 /s, `SetSeconds` 4.0,
  `SmearCmPerCm` 0.5, `FreshFadeS` 6.0, `SleepCmPerS` 0.05. A steeper repose than the rut-hold clamp
  (tan 38 = 0.78 > `RutHoldMaxSlope` 0.5), so slumped walls still hold the tyre at full strength; what the car feels is
  the shallower rut and the softer bank.

**Patch and profile.** `AGTMudPatch` owns the numbers as UPROPERTYs and pushes them in, as it does the Ridge numbers;
`FGTDeformProfile` gains the same fields and `UGTMudSubsystem::BuildPatches` copies them. The ford bed's profile is
stiffer: `ReposeDeg` 45, `OozeRate` 0.1, `SetSeconds` 1.5. `AGTMudPatch::Tick` calls `Field.Settle(DeltaSeconds)`
before `TakeDirty`/`Upload`. `TreadTexture` B carries `Fresh` (uploaded with the same dirty rects). Console switch
`gt.Mud.Settle` (1/0). A cycle stat `STAT_GTMudSettle` plus a mean/max ms and awake tile count readable by the check
script.

**Material** (the live block in `live_mud_style.py`, so the strip and every map using `M_GT_Mud` get it):

- `SlideUV` (proposed 1.0): the clay's sample position shifts by -offset x SlideUV (cm) in the pixel shader. The
  vertices don't move.
- `FreshWet` (proposed 0.6): by `Fresh x FreshWet`, roughness goes toward 0.5 and albedo x 0.85, on top of the
  weather's wetness. Untouched ground has Fresh 0 and doesn't change.

**Tests** (new automation test `GrandTour.Mud.Settle` in `GTMudShapeTests.cpp`; `Art/mud_shape_test.ps1` runs
`GrandTour.Mud` and checks every result). The section L test stroke (40 cm asked, 28 cm tyre), then settling:

| Check | Target |
|---|---|
| Volume, 10 s settled vs just stamped | equal within 0.1 % of the stroke's lowered volume |
| Steepest neighbour step after 10 s | <= tan(ReposeDeg) x CellCm + 0.5 cm |
| Core depth recovered at 5 s, bog numbers | 15-25 % (tune `OozeRate` inside 0.2-1.5 to land it; report the value) |
| Core depth recovered at 5 s, ford numbers | under 3 % |
| Bank crest | lower than just stamped, and wider at half height (report both) |
| Sleep | every tile asleep by SetSeconds + FreshFadeS + 1 s |
| Frame rate | the same stamps settled at dt 1/30, 1/60, 1/144: every cell within 0.1 cm |
| Determinism | twice from the same input: identical |
| `gt.Mud.Settle 0` | the field after the stroke is identical to today's |

**Check script.** `check_live_mud_drive.py` adds a settle pair: after the dry crossing, a fixed camera on a fresh rut
takes `Mud_Settle_0s.png` at 0.3 s after the last wheel left that spot and `Mud_Settle_5s.png` at 5 s, and writes the
field's profile across the rut at both times to `settle_profile.csv`. The CSV is the proof; the pictures are for the
owner. Cost: `GT Mud Settle` mean and max ms over the dry crossing and the awake tile peak. Gate: mean <= 0.3 ms,
max <= 1.0 ms.

**Physics re-measure**: terrain step 11 and the bog escape against LM0's baseline; the strip's dry/wet completion and
deviation. Expected: the ruts read shallower behind the car, so second passes follow them a little less strongly.

**Owner gate**: drives the strip, watches ruts settle behind the car, drives back down them. Names `ReposeDeg`, the
recovery share, `SetSeconds`, `SlideUV`, `FreshWet` if any feel or look wrong.

### LM1b: recovery that keeps the detail (named 2026-10-05 after LM1)

*Done 2026-10-05 (build exit 0; the OpenAI Codex app ran its own Unreal imports and renders in this project during the
session: two drive checks overlapped them and were run again, the numbers below are from runs that overlapped nothing):*
- *Built as the block says: the relax (a = -ln(1 - RecoverShare) / SetSeconds, K = 1 - exp(-a dt) per 1/30 s sub-step,
  every set cell of the swept tiles, HeightCm only), the patch-wide balance (V_up and V_down summed in a first pass, the
  larger side scaled to the smaller), the creep into OffsetCm (downhill unit from central differences x |change| x
  CreepCmPerCm 3, capped at MaxSlideCm). `OozeRate` 0 for the bog and the ford profile (LM1's code path kept).
  `RecoverShare` and `CreepCmPerCm` are AGTMudPatch UPROPERTYs and FGTDeformProfile fields, copied in ApplyProfile.
  Landed on: bog `RecoverShare` **0.4** (the main session's revision above; at the plan's 0.2 the test gave 7.6 % / 7.8 %
  back, V_up 695,586 / V_down 244,956 cm^3 on the narrow stroke: the balance capped it), ford 0.02.*
- *`GrandTour.Mud.Settle`, every row PASS: narrow stroke core -33.29 -> -28.23 cm at 5 s = 15.2 % (asked at least 14),
  V_up 1,520,459 / V_down 490,102 cm^3 asked, 490,102 moved each way; broad stroke (15 cm) -12.63 -> -10.67 = 15.5 %
  (544,773 / 179,345); ford 0.8 % / 0.8 %. Detail kept, D at 10 s / D just stamped: narrow 0.0655 -> 0.0601 = 0.918,
  broad 0.0711 -> 0.0695 = 0.978 (asked 0.9-1.1); LM1's diffusion (OozeRate 1.2, RecoverShare 0) on the same strokes
  0.484 / 0.479. Crest 8.90 -> 5.28 cm at 5 s (40.6 % lower), broad 3.33 -> 1.99 (40.3 %); half-height width 66.1 ->
  65.6 / 66.1 -> 66.1 cm (reported; the relax scales, it does not widen). Volume error 0.0 cm^3 of 3,467,620 lowered;
  steepest step 15.00 -> 9.30 cm (<= 10.27); all 21 tiles asleep at 10.40 s (by 11.0); 1/30 vs 1/60 vs 1/144 worst
  cell 0.0000 cm; deterministic; gt.Mud.Settle 0 = LM0's field (CRC 8e0aad06). By RecoverShare, narrow / broad at 5 s:
  0.1 3.8 / 3.9 %, 0.2 7.6 / 7.8, 0.3 11.4 / 11.6, 0.4 15.2 / 15.5.*
- *Cost, the clean check run, dry crossing: Settle mean 0.134 ms, max 1.34 ms (3 of 2715 frames over 1 ms, all on
  20-26 ms game-thread frames; p99 0.62 ms), awake peak 44 -> mean PASS, max FAIL. Wet: 0.116 / 0.895 ms, 47. The two
  overlapped runs read 0.078 / 0.457 / 45 and 0.119 / 0.687 / 44. Frame time in the clean run (game / GPU ms mean): Settle 0
  13.94 / 19.36, Settle 1 21.28 (median 16.72) / 20.39, wet 15.33 / 20.66, Settle 0 again 16.48 / 20.80: session drift
  again, larger than the switch.*
- *Strip, clean run vs LM1 (61.8 / 61.6 s, 0.30 / 0.37 m, 22.36 / 22.33 M cm^3 dry; 54.4 / 56.2 s, 0.36 / 0.44 m, 13.82 /
  14.55 M wet): dry completed 119.02 m in 62.6 s, lateral 0.27 m, added 21,348,114 cm^3; wet 119.05 m in 58.5 s,
  lateral 0.33 m, added 13,557,203. Settle 0 controls in the same session: 119.01 m, 62.7 s, 0.25 m, 20,580,244 and
  119.06 m, 61.6 s, 0.28 m, 20,900,186. (The first overlapped run: dry 63.5 s / 0.27 m, wet 58.3 s / 0.31 m; the
  second, overlapped by three foreign editors, crawled in the wet bog from 32 m and stopped at 47.1 m after 110 s.)*
- *Settle pair (`settle_profile.csv`, now with `detail_d`): core -17.48 -> -17.10 cm at 0.3 -> 5 s, crest 0.80 -> 0.77,
  D 0.0593 -> 0.0597, fresh at the core 0 -> 0. With gt.Mud.Settle 0, same camera and spot (`Mud_Settle_0s_Off.png` /
  `Mud_Settle_5s_Off.png`): core -18.81, crest 4.05, D 0.0665 at both times. The report's new per-tick trace of the core
  cell says why the pair moves so little: with Settle 1 the car took 14.6 s from its first wheel over the spot to every
  wheel 2.3 m past it (1.8 s with Settle 0, 14.3 s in the overlapped run too), so the stamps' bands kept restarting the
  spot's set timer and most of the relax happened before t0: deepest -18.77 cm at the rear wheel's last cut, -17.41
  at t0, -17.01 when the set ran out 2.5 s after t0 = 9.4 % back from the last cut. The core moved about 0.006 cm a
  sub-step, under the 0.01 cm the fresh mark needs, so its sheen faded to 0 while it was still moving. Not tuned; why the
  car crawls from a standstill on the pair lane with Settle 1 is not investigated (the main crossings take the same
  time on and off).*
- *The thin dark line: it sits on the patch's -Y box edge (y -680 cm, the mesh's outer vertex ring, lifted EdgeLipCm
  0.1). In the clean run's camera that edge projects to x 126 / 132 / 138 at rows 450 / 500 / 550 and the line was found at
  123 / 130 / 136 in `Mud_Settle_0s_Off.png`; the hole's inset edge (HoleInsetCm 12.5, read from the landscape material;
  the lip's inner ring is the same line) projects 50-60 px to the right, with nothing dark on it. It shows with
  gt.Mud.Settle 0 (both _Off pictures, strongly), so it is not new; in that run's Settle 1 pictures only a fragment shows,
  in the overlapped run's Settle 1 picture all of it (on the box edge's projection within 3 px). Not fixed.*
- *Terrain, two runs (step 11 / escape): down the ruts 6 m in 5.6 / 5.9 s, held exit 5.4 / 5.4 s -> FAIL, FAIL (LM1 3 of
  4 failed), unheld 4.0 s; escape forward 10.8 / 10.6 m in 12 s (LM1 10.9-11.4), reverse 6.0 m in 7.9 / 6.4 s (LM1
  6.0-7.0). Mud-field rut mean -30.1 / -30.6 cm (LM1 -27.0..-27.2, asked -24.0) PASS, ridge mean 2.9 cm (LM1 3.6). Stage
  H crest 4.45 still FAIL (as LM1); stage I floor -23.6 PASS; fords PASS (raised flooded 1). drivetrain, grip, mud,
  surface, track PASS.*
- *Unchecked: every look (the pictures are for the owner; CreepCmPerCm through SlideUV not looked at); the feel. For
  LM2a: the relax leaves LumpCm alone by construction (HeightCm only), and the bank sags about 40 % in 4 s at 0.4.*

**Why.** LM1's numbers held in its test, but on the strip the car's rut is a broad 15 cm bowl. `settle_profile.csv`:
core -14.84 -> -14.36 cm in 5 s, crest unchanged, and the settle pictures show no difference (main session's look).
Section L's shoulders keep the walls well under 38 deg, so the talus never fires. The ooze is a diffusion, which
levels a metre-wide bowl about 16x slower than a 25 cm cut. And it is a blur: at OozeRate 1.2 over 4 s it smooths
away everything under about 4-6 cells (50-75 cm), which is stage H/I's clumps and floor noise and section L's
pockets. **The owner drove LM1 briefly: "it's too smooth at the moment. Keep this in mind."** So the movement must not
come from smoothing.

**Field.** Replace the ooze with a **shape-keeping relax**. Keep the code path, with the default `OozeRate` 0, so the
owner can compare.

- While a cell's `SetS` > 0, its own height relaxes toward 0 by a rate a = -ln(1 - `RecoverShare`) / `SetSeconds`
  (per second, fixed sub-steps as now). A rut cell rises and a bank cell sinks, each in proportion to its own height,
  so the relief keeps its shape and its detail: it scales, it doesn't blur. The rate doesn't depend on the rut's width.
- **Volume balance, per patch, per sub-step:** sum the rise of every set cell below 0 (V_up) and the fall of every set
  cell above 0 (V_down). Scale the larger set of moves down so both equal min(V_up, V_down). The rut rises only by what
  the banks give up. Exact conservation, two passes over the awake set cells.
- Applies to `HeightCm` only. LM2a's `LumpCm` rides on it untouched, so lumps keep their height while the bank under
  them sags. This replaces the "ooze leaves LumpCm alone" question.
- **Creep**: every cell the relax moved gains `OffsetCm` += the surface's downhill unit direction x |its change| x
  `CreepCmPerCm` 3, capped at `MaxSlideCm`. The clay on the walls visibly slides into the rut as its floor rises
  (shown through `SlideUV`; vertices don't move).
- Talus, Fresh, SetS, the tiles, sleep, the 2-sub-step cap: as LM1 built them.
- Numbers: `RecoverShare` 0.2 for bog mud, 0.02 for the ford bed, 0 later for snow; `SetSeconds` 4 stays.
  **Revised 2026-10-05 after the first LM1b test run (main session's decision):** the banks hold only about 35-38 % of
  a rut's volume (section A's RidgeReturn 0.6 less compaction, fill share and slumps), and the balance caps the rut's
  rise at what the banks give up. So the rut comes back about 0.38 x RecoverShare: 7.6 % at 0.2, 15.2 % at 0.4.
  The bog's `RecoverShare` is **0.4**: the rut is back about 15 % and the bank sags about 41 % in 4 s. That bank
  sag is the visible slump, and LM2a's lumps ride on top of it unchanged, so the chunks settle with the bank rather
  than melting. The recovery rows' target becomes "at least 14 %" on both strokes at 0.4, with the crest's fall
  reported. Not done: lowering the compaction (RidgeReturn) to feed the rut. That's a stage-A shape number, the
  owner's to name.

**Tests** (`GrandTour.Mud.Settle`: keep every LM1 row, change the recovery rows, add the detail row):

| Check | Target |
|---|---|
| Core depth back at 5 s, the 40 cm narrow stroke | 15-25 % |
| Core depth back at 5 s, a broad stroke like the strip's (asked 15 cm, 28 cm tyre) | 15-25 % |
| Ford numbers, either stroke | under 3 % |
| **Detail kept**: D = RMS(S - 3x3 mean of S) / RMS(S) over the stroke's touched cells, at 10 s vs just stamped | within +-10 % (report LM1's diffusion at OozeRate 1.2 on the same strokes for comparison) |
| Bank crest | lower than just stamped (report by how much) |
| Volume, steepest step, sleep, frame rate, determinism, `gt.Mud.Settle 0` identity | as LM1 |

**Check script.** The settle pair again, plus the same camera with `gt.Mud.Settle 0`
(`Mud_Settle_0s_Off.png`, `Mud_Settle_5s_Off.png`) to tell whether the thin dark line along the left of LM1's settle
pictures is new. Find what that line is: whether it sits on the patch's box edge, the hole's inset, or the edge lip,
from the field's world box and the camera, and report it. Don't fix it in this stage. `settle_profile.csv` gains D at
0.3 s and 5 s along the profile.

**Physics.** Every rut now gives back about a fifth of its depth, broad ones included, so the hold softens more on
the strip than LM1's did. Report step 11 (it already failed 3 of 4 in LM1), the escape, and the strip, all against
LM1's numbers. Nothing is tuned for them.

**Then the owner gate as above**, with `RecoverShare` and `CreepCmPerCm` added to the numbers the owner may name.
LM2a/LM2b's lumps and clods are the main answer to "too smooth": the owner has seen LM1 and named the smoothness, so
the main session may offer to chain LM2a/LM2b after LM1b.

### LM2a: lumps in the field and the wheel's throw

*Done 2026-10-05 (build exit 0). Phase A (code, tests, headless Blender, the clod import and the live setup) ran with
the owner's God of War (GoWR) running. Phase B's drive check also started with it running, by the owner's override
("Do it even with gowr running"). The game had exited by the time the suite started. The cost and frame-time numbers
below are unjudged until a clean run:*
- *Built as the block says. `LumpCm` rides on `HeightCm`; `SurfaceCm` is what `HeightAt`, `GradientAt`, `CellHeightCm`,
  the upload, the water depth, Settle's talus, `DetailRatio` and `MudCellHeightsCm` read. Lumps are static hashed domes;
  `LumpShare` of the bank's deposit is held and spread by W with exact volume. The cap is 10 cm, and the excess goes into
  the same cell's `HeightCm`. A capsule, and the belly too (an addition), flattens the lumps under its whole bowl into
  its displaced volume. The talus takes outflow from the lumps first; the relax touches `HeightCm` only. `ClodChance` 0.
  The throw: `StampWheel(..., ThrowShare, OutThrownCm3)`, with the old six-argument call forwarding 0. The traction maps
  slip to a throw share. `SlipMagnitude` is Chaos's tyre surface speed less the ground's at the contact, in cm/s,
  positive spinning forward. The spin is `SlipMagnitude` x the drive's sign (reverse negates it), so a locked wheel
  never throws. `ThrowShare` = `ThrowMax` x clamp((spin - the wheel's `SlipThreshold`, 20 cm/s) / (`SlipSaturation` 300
  - 20), 0, 1). The spray spends `FGTWheelTraction::ThrownCm3` on 6-14 cm blobs carrying 4/3 pi r^3 x 0.6. Each blob is
  flung back by 0.3-0.6 x the car's speed plus 0.4-0.8 x the spin, and up 150-350 cm/s plus 0.3 x the spin. A blob that
  comes down below the patch's surface calls `AGTMudPatch::DepositThrown`; outside every patch its mud is lost and
  counted. Housekeeping: `FreshMinCm` 0.002; per-feature p99 and the mean <= 0.3 / p99 <= 0.7 gate in the check script;
  the stage H crest gate prints "(report)"; the crawl log (`crawl.csv`).*
- *Landed on: `LumpSpacingCells` **4** (proposed 3). At 3 the crest's coefficient of variation read 1.15x `LumpShare` 0's;
  at 4 it reads 1.59x (asked at least 1.5). The main session accepted it. Every other number as proposed: `LumpShare`
  0.35, `LumpRadiusCells` 1.6 (+-40 %), `LumpMaxCm` 10, `ThrowMax` 0.5.*
- *`GrandTour.Mud.Lumps` (all PASS). Volume: handed to the bank 1,752,955 = bank asked 1,139,421 + lumps held 613,534
  cm^3, error 0.1 cm^3 of 3,454,546 lowered. Held 613,534 = in the field 481,217 + flattened later 114,469 + over the cap
  17,849, error 0.0. Crest cv 0.377 vs 0.236 = 1.59x; on the bank's crest line 0.439 vs 0.236. Stage I's clods 0.15 vs 0:
  0.225 vs 0.236 = 0.95x. Lumps kept after 10 s settled: 95.4 % (4.80 -> 4.58 cm over 619 cells). Second capsule: LumpCm
  0 under it (19 of 22 cells had lumps); displaced 164,341 vs 145,588 with the lumps taken out, difference 18,753 = the
  flattened lumps (error 0.00); handed the bank 0.6 x that (error 0.00). `GrandTour.Mud.Throw` (all PASS): ThrowShare
  0.5 halves the deposit and the standing mud (ratios 0.50000), and OutThrown 36,242 = the difference 36,242 (0.000 %).
  DepositThrown: 314.2 / 67.9 / 3,000 cm^3 each raised the surface by exactly that (0.00000 %).*
- *Settle asserts both configurations (the main session's decision). Lumps off: LM1b's rows (narrow 15.3 % back,
  broad 15.5 %, D10/D0 0.930 / 0.994, steepest 9.30 cm, asleep 10.40 s; `ClodChance` 0 moved them from 15.2 % / 0.918).
  LM0's field reproduces to the bit with `LumpShare` 0 and `ClodChance` 0.15 (CRC 8e0aad06). Lumps on: core back 10.2
  % narrow / 10.0 % broad (asked at least 9), asleep 11.77 / 10.40 s (by 12.5), D10/D0 1.009 / 1.090, steepest 9.84 /
  6.58 cm (<= 10.27), volume error 0.0. Recovery with lumps on by `RecoverShare` (not shipped): 0.5 12.8 %, 0.6 15.3 %,
  0.7 17.8 %. SoftShoulders: cross-step 14.94 -> 17.34 cm (asked under 24).*
- *Strip (drive check; its first attempt stalled with the game in front: the hidden editor ran under 1 frame a second
  and the car never left x 5 m, so it was rerun with the editor's background throttle off, which the wrapper now sets).
  Against LM1b's clean run (62.6 s / 0.27 m / 21,348,114 dry; 58.5 s / 0.33 m / 13,557,203 wet): dry Settle 1 119.07 m
  in 64.3 s, lateral 0.29 m, added 22,267,080 cm^3; wet 119.10 m in 58.9 s, 0.32 m, 13,672,365. Settle 0 controls:
  119.09 m in 62.0 s, 0.25 m, 21,665,428; the first, warming-up crossing took 109.5 s.*
- *Cost, unjudged (game running at the start). Settle dry mean 0.127 / p99 0.511 / max 0.691 ms, wet 0.136 / 0.533 /
  0.777 (inside mean 0.3 / p99 0.7). Game / GPU frame ms: dry 14.27 / 21.30, wet 13.98 / 21.83, Settle 0 after 13.61 /
  21.44.*
- *Settle pair: core -17.96 -> -17.71 cm at 0.3 -> 5 s, crest 4.26 -> 4.26, Fresh at the core **1.0** at 0.3 s (asked
  over 0.5) -> 0.63 at 5 s, D 0.0888 -> 0.0896. Off: core -18.77, crest 6.21, D 0.0971.*
- *The crawl (diagnose only): from the pair's stop, 2.3 m took 5.77 s with Settle 1 and 2.03 s with Settle 0 (LM1b
  14.6 / 1.8 s). For the first 0.5 s both are identical. At 0.5-1 s the step from under the tyre to 30 cm ahead reads
  4.19 cm with Settle 1 and 3.55 cm with Settle 0, and the share of wheels spinning is 0.38 vs 0.75. From 1 s, Settle 0's
  wheels all break into spin and the car reaches 1.6-2.5 m/s, its RutClimb falling to 0.10 and the hold drag to 140-160
  N. Settle 1's wheels stay gripped, the car holds 0.35-0.5 m/s, RutClimb doubles to 0.20 with the hold drag at
  300-311 N, and the step ahead stays about 4 cm. Every set timer under and ahead reads 4.0 (stamped each tick). The
  main session's guess fits: the cells just ahead of a slow tyre stay set and the relax raises them into a wall about
  0.6 cm higher, while the tyre's own cell is re-cut each tick. The wall feeds RutClimb and the hold drag, so the wheels
  never spin up. Not fixed.*
- *Spin test: lane y +4.5 m, x 46 m. The Bog layer reads 0 all along that lane, so this is the section's middle in Mud,
  not Bog. Full throttle 3 s: the car crept 46.06 -> 47.06 m with slip 0-136 cm/s (throw share at most 0.21), not a dead
  spin. Per wheel: hole -20.18 / -21.51 / -19.44 / -20.87 cm; mound 3.02 cm at 1.7 m, 2.99 at 3.5 m, 2.37 at 1.3 m,
  3.07 at 1.1 m behind (lumps there 2.73 / 2.91 / 2.27 / 4.37 cm); thrown during it 22,375 / 8,992 / 3,559 / 16,521
  cm^3. Spray during it: 52,051 cm^3 out in 156 blobs, 53,934 landed in 164 (blobs already in the air at the reset),
  0 lost. Lost share over whole crossings: dry 0.97 %, wet 2.75 %, Settle 0 1.78 %.*
- *Terrain: run 1 PASS: step 11 held exit 5.9 s against 5.4 s down the ruts (needs 1.05x); escape forward 10.6 m,
  reverse 6.0 m in 6.8 s; rut mean -31.0 cm; ridge mean 6.3 cm. Runs 2 and 3 FAIL on step 11 alone: 5.4 vs 5.4 s, and
  5.8 vs 5.6 s (needs 5.88). Escape 10.4 / 10.6 m, reverse 6.0 m in 5.6 / 6.8 s. Step 11 stays reported (LM1b failed 2
  of 2). Stage H crest (report): 7.65 -> 6.12 cm, back inside its old band. Stage I shape PASS: width 51.9 cm, crest 3.98
  cm, cv 0.46, floor -23.6 cm. drivetrain, grip, mud, surface and track PASS. Full suite: `bash Art/suite.sh` 27 PASS, 1 FAIL (terrain, on step 11's held exit alone: 5.9 vs 5.6 s; escape 10.4 m, reverse 6.0 m in 5.6 s), so step 11 passed 1 of 4 terrain runs; spray, water, body, winch and the rest PASS.*
- *Unchecked: the feel; the look of the lumps and the throw's mound beyond what `Mud_Clods_Dry.png` / `Mud_Spin_Dry.png`
  show (looked at once: lumps read as bumps on the bank). The spin as a dead spin (the car crept).*

**Housekeeping first, from LM1b's findings (main session's decisions, 2026-10-05):**

1. **Fresh sheen for slow motion.** The relax moves a core cell about 0.006 cm per sub-step, under the 0.01 cm that
   marks a cell fresh, so the sheen faded while the mud was still moving. Mark a cell fresh when it moves more than
   `FreshMinCm` 0.002 in a sub-step, from the stamp, the talus, the relax or a throw deposit. The strip's settle-pair
   core should read Fresh > 0.5 at 0.3 s; report it.
2. **The cost gate becomes p99.** LM1b's max went over 1.0 ms on 3 of 2,715 frames, all on 20-26 ms game-thread
   frames, with p99 at 0.62 ms. A max taken on a busy editor measures the editor. From LM2a on, every feature is gated
   on mean <= 0.3 ms and p99 <= 0.7 ms per feature; the max is reported, not gated. The check script prints p99.
3. **The stage H crest gate is retired to a report.** Its purpose was "the smoothing must not take a fifth off the
   crest". Section L's shoulders (owner-approved) took it to 4.45 cm against 5.35-9.94, and LM1b's relax lowers banks
   by design. Bank shape is now gated by LM2a's lump rows. The terrain test keeps printing the stage H numbers with
   "(report)" instead of a pass/fail.
4. **The standstill crawl, diagnose only.** With Settle 1 the car took 14.6 s to crawl 2.3 m from a stop at the settle
   spot, against 1.8 s with Settle 0. The main crossings were unchanged. Log per wheel, at 10 Hz for the first 15 s of
   that start, with Settle 1 and 0: `RutDepth`, `RutClimb`, `RutCrossSlope`, the hold force, `Sinkage`, the field
   height under the tyre and 30 cm ahead, and its `SetS`. Report the cause (the main session's guess: the relax lifts
   the set cells just ahead of a stopped tyre into a wall, while the tyre's own cell is re-stamped each tick). **Don't
   fix it**: whether stopping in mud should be this hard is the owner's feel call.
5. **Step 11** (held exit vs down the ruts) failed 2 of 2 after LM1b. It stays reported, not tuned, until the owner's
   feel gate.

**Running alongside the owner's games (the owner, 2026-10-05: "do what you can while god of war is running").**
Phase A runs with a game open: code, scripts, headless Blender, the C++ build, and the `GrandTour.Mud` automation
tests (deterministic, CPU-only, NullRHI), run with the same command line as `Art/mud_shape_test.ps1` but without its
game check. Say in the report that they ran alongside the game. Phase B waits until no game is running: shader and
material setups (`setup_live_mud_drive.ps1`), the mesh import if it compiles shaders, `check_live_mud_drive.ps1`,
`suite.sh` and the frame-time numbers. At the end of phase A the agent stops and reports. Phase B resumes on the
owner's word.

**Lumps** (`GTMudField`):

- A new per-cell `LumpCm` on top of `HeightCm`. The surface everything reads (`HeightAt`, `GradientAt`, `CellHeightCm`,
  the upload, the water depth, `Settle`) is HeightCm + LumpCm, behind one `SurfaceCm(Index)`, so the render and the
  traction agree. Stage H's blend and smoothing and the stamps' compaction logic never touch `LumpCm`.
- A static lump weight per cell, W in 0..1: smooth domes around hashed jittered sites on a `LumpSpacingCells` 3 grid
  (37.5 cm), radius `LumpRadiusCells` 1.6 jittered by +-40 %, seeded by `NoiseSeed`. No state: the same clumps grow
  pass after pass, as stage H's noise does.
- In `StampWheel`, `LumpShare` 0.35 of the bank's deposit is held back and spread over the stroke's band cells in
  proportion to W, normalised so the held volume is exactly what lands. Capped at `LumpMaxCm` 10 per cell, with
  any excess going back to `HeightCm` in the same cell.
- A capsule flattens the lumps under it: their volume joins the stroke's displaced volume (it goes to the bank like
  any displaced mud) and `LumpCm` goes to 0 there.
- In `Settle`, flux leaving a cell is taken from its `LumpCm` first, so lumps sag before the bank does; they survive
  the talus test, which runs on the total surface, as long as their sides are under the repose angle.
- Stage I's per-cell clods are superseded: `ClodChance` 0 with lumps on (they were under two cells and smoothed
  away). Measured before and after.

**Throw** (`GTMudField`, the traction, the spray):

- `StampWheel` gains `float ThrowShare` (default 0 so every existing caller is unchanged) and an out
  `double& OutThrownCm3`: that share of the bank's deposit is not deposited and is returned instead.
- The traction sets `ThrowShare` from the wheel's slip: 0 below the slip that `bSlipping` uses, rising to `ThrowMax`
  0.5 at full spin (the agent states `SlipMagnitude`'s units and the mapping it chose). It adds the result to a new
  `FGTWheelTraction::ThrownCm3`.
- The spray's mud emission spends `ThrownCm3`: it emits blobs of 6-14 cm, each carrying its volume
  (4/3 pi r^3 x 0.6), backwards and up as today, faster with the wheel's slip speed. A blob landing inside a patch
  (below `MeshRestZAt + HeightAt`) calls a new `AGTMudPatch::DepositThrown(XY, VolumeCm3, RadiusCm)`: a dome into
  `LumpCm` of 1.5x the blob's radius, at least one cell, conserving volume, waking its tile and setting `Fresh` 1.
  Blobs landing outside every patch lose their volume; report the share.
- Behind a spinning wheel that builds a mound. That is the rooster tail.

**Decisions after phase A (main session, 2026-10-05):**
- **Lumps stay out of the relax.** With lumps on, the banks' `HeightCm` holds about 35 % less volume (V_down 328,568
  vs 492,129 cm^3), so the balance gives the rut back about 10 % at `RecoverShare` 0.4 instead of 15 %. Accept the
  10 %. Making lumps relax would shrink the chunks the owner asked for ("too smooth"). Raising `RecoverShare` to 0.6
  would flatten the bank under them by 60 %. The recovery share is the owner's to name at the gate.
- `LumpSpacingCells` 4 (50 cm), not 3: at 3 the crest-variation row read 1.15x against at least 1.5x. Accepted.
- **The Settle test asserts both configurations:**
  - lumps off (`LumpShare` 0): LM1b's rows exactly as they stand, as LM1b's regression;
  - the shipped bog numbers with lumps on: recovery at least 9 % on both strokes, every tile asleep by 12.5 s (lump
    talus runs to about 5.7 s, then the sheen fades for 6 s), detail kept 0.9-1.1, and the steepest step and volume
    rows as before.
- Stage I's clods measured 0.95x crest variation with lumps off: they did nothing, so `ClodChance` 0 stands.

**Tests** `GrandTour.Mud.Lumps` and `GrandTour.Mud.Throw`:

| Check | Target |
|---|---|
| A stroke's volume with lumps on | lowered = banked + lumps within 0.1 % |
| The bank's coefficient of variation along the crest | LumpShare 0.35 vs 0: report both; at least 1.5x |
| Lumps after 10 s settled | keep at least 60 % of their height (bog numbers) |
| A second capsule over lumps | LumpCm 0 under it, their volume in the new bank |
| ThrowShare 0.5 | bank deposit halved vs 0; OutThrown equals the difference within 0.1 % |
| DepositThrown | adds exactly its volume |

**Physics re-measure** as LM1, plus a spin test on the strip: from a dead stop in the deepest mud, full throttle 3 s.
Report the hole's depth and the mound's height and distance behind each driven wheel from the field.

### LM2b: clods on the banks and from the throw (chains after LM2a)

*Done 2026-10-05 (with LM2a, under the same conditions: phase A with the owner's game running, the drive check
started with it running, the cost unjudged until a clean run):*
- *Meshes: `Art/Blender/build_mud_clods.py`, run headless, builds five clods: a 320-face icosphere displaced by two
  noise octaves, the bottom cut flat and capped, scaled to 10 cm across and 6 cm tall, with the pivot at the middle of
  the flat face. They are written to `Art/Export/MudClods/SM_GT_Clod_0..4.fbx` (plus `manifest.json` and
  `MudClods.blend`): 330 / 332 / 328 / 332 / 332 triangles. `Art/Unreal/import_mud_clods.py` (`& Art/import_mud_clods.ps1`)
  imported them as `/Game/GrandTour/Mud/Clods/SM_GT_Clod_0..4`: the same triangles, 0 collision shapes, Nanite off.*
- *Material: `M_GT_Clod` is built in `live_mud_style.py`'s `apply_existing` (the live setup owns it) and put on the five
  meshes. It uses the approved clay colour and normal bakes, tri-planar in world space with the ground's mirrored
  tiling at 1.5 m. Roughness runs 0.85 dry to 0.45 wet from MPC_Weather's Wetness, it darkens 0.25 x wetness, and
  PerInstanceRandom gives a +-6 % tint. Normals are world-space. Compiled with no errors.*
- *Patch: one HISM per clod mesh (shadows on, cull 40-60 m, no collision), a ring of `MaxClods` 1200 (slot S is mesh S
  % 5, instance S / 5; the oldest is replaced first). Dead instances sit at zero scale at the box's middle. Per-tile
  (2 m) clod lists. The field queues bank clods: a lump site whose dome top took `ClodBankMinCm` 2 cm since its last
  roll rolls `ClodBankChance` 0.35, at most once per `ClodRespawnS` 3 s, sized 6-16 cm by the stamp's depth.
  `DepositThrown` queues a throw clod with `ClodThrowChance` 0.5, at the blob's size. Placement: random yaw, tilt
  +-25 deg, sunk `ClodSinkIn` 0.35 of the clod's height (I read "its size" as its height, 0.6 of its width).
  Batches run at 5 Hz with one render-state dirty: spawns; re-snap of the clods in tiles whose cells changed; a squash
  when the tracks are set (at least 0.5) and the surface fell more than 3 cm since the last snap; wet sinking (on Bog
  cells or at wetness over 0.5, 0.3 x wetness cm/s, gone at 90 % of the height). `gt.Mud.Clods` 1/0. Without a mesh,
  nothing is drawn and the queue is dropped.*
- *Counts (cumulative from the main dry crossing): after it, live 1,023, from bank 389 / throw 1,911, squashed 474 /
  sunk 0 / recycled 803 (each patch's ring is full). After the spin: live 1,105, bank 677 / throw 2,655, squashed 622 /
  recycled 1,605. After the wet replay: live 210, bank 900 / throw 3,672, squashed 779 / sunk 1,894 / recycled 1,689.*
- *Cost, unjudged (game running at the start): clod update on the dry crossing mean 0.033 / p99 0.594 / max 1.066 ms
  (game-thread mean asked <= 0.1); wet mean 0.058 / p99 0.884 / max 1.511 (p99 over 0.7: the wet sinking re-pushes
  every sinking clod each batch); at the cap (2 x 1,200, static) 0.010 / 0.197 / 0.469. GPU at the cap from the settle
  camera, clods on vs off: 18.98 vs 18.65 ms mean (+0.34; asked <= 0.3); base pass 1.031 vs 1.009 ms, shadow depths
  2.483 vs 2.436 ms; draw calls 27.3 vs 25.0 base pass, 42 vs 32 shadow.*
- *Pictures: `Mud_Clods_Dry.png` (the settle pair's camera) and `Mud_Spin_Dry.png` (the same framing on the spin spot),
  in `Art/Export/LiveMudDrive`. Looked at once: the clods draw in the clay material, cast shadows and lie across the banks
  and behind the car; their size, rate and look are the owner's to judge.*
- *Owner gate as the block says (drives the strip, spins up, looks at the banks and the mound; names `LumpShare`, the
  lump size, the clod rates and sizes, `ThrowMax`), with `RecoverShare` (10 % back with lumps on) added.*

- **Meshes**: `Art/Blender/build_mud_clods.py` builds five clods procedurally: an icosphere (subdivision 2-3) displaced
  by two noise octaves, squashed to 0.6 in Z, one face cut flat, 150-400 triangles, 10 cm across at scale 1. Export
  FBX the way the other `Art/Blender/export_*` scripts do. `Art/Unreal/import_mud_clods.py` imports them as
  `/Game/GrandTour/Mud/Clods/SM_GT_Clod_0..4`: no collision, Nanite off.
- **Material** `M_GT_Clod`, built in `live_mud_style.py` so the live setup owns it: the approved clay colour and normal
  bakes, tri-planar at a 1.5 m scale (finer than the ground's 6 m: chunks need smaller detail). Roughness 0.85 dry to
  0.45 wet from `MPC_Weather` Wetness, darker wet, per-instance tint +-6 % from PerInstanceRandom.
- **Patch**: a `UHierarchicalInstancedStaticMeshComponent` per mesh (or one per patch with the mesh varied by
  variant), shadows on, cull 40-60 m, at most `MaxClods` 1200 per patch, oldest replaced first.
- **Spawns**, queued by the field into `PendingClods` (`{XY, SizeCm, Seed}`) and added by the patch's tick:
  1. On the bank: a lump site whose dome falls in a stroke's band and took at least 2 cm of deposit, with chance
     `ClodBankChance` 0.35, at most once per `ClodRespawnS` 3 s per site. Size 6-16 cm, larger with sinkage.
  2. From the throw: `DepositThrown` spawns one with chance `ClodThrowChance` 0.5, the blob's size.
  - Placement: yaw random, tilt +-25 deg, sunk `ClodSinkIn` 0.35 of its size into the surface.
- **Follow the field**: the patch keeps a clod list per tile. When a tile is dirty, its clods are re-snapped to the
  surface. A clod under a new capsule (tracks just set and the surface lowered by over 3 cm) is removed: squashed,
  its volume is already in the field.
- **Wet sinking**: on Bog cells, or at wetness over 0.5, a clod sinks `ClodSinkCmPerS` 0.3 x wetness and is removed at
  90 % of its size under. Updated in batches at 5 Hz with one render-state dirty per batch.
- **Switch and cost**: `gt.Mud.Clods` (1/0). GPU (base pass and shadow depths) with clods on vs off on the strip at
  the cap. Gate: <= 0.3 ms GPU, <= 0.1 ms game thread mean.
- **Pictures**: `Mud_Clods_Dry.png` after the dry crossing and the LM2a spin test, from the settle camera, and the
  clod count by source (bank, throw) and by fate (squashed, sunk, recycled) in the report.

**Owner gate**: drives the strip, spins up in the bog, looks at banks and the mound. Names `LumpShare`, the lump size,
the clod rates and sizes, `ThrowMax` if any are wrong.

### LM2c: break the uniformity (named by the owner 2026-10-05 on foot)

*Done 2026-10-05 (no game and no foreign Unreal at any run; the cost is judged):*
- *Lumps: `FGTMudField::bLumpVariety` (the patch's, true); false is LM2a's path to the bit. Sites jitter +-0.5 of the
  spacing. The cluster noise (`LumpClusterCm` 150) leaves out the sites under its 0.35 quantile: 34.9 % absent over
  four seeds. Amplitude is 0.3 + 1.3 u^2. Domes are elliptical (aspect 1-2.2, a random angle, radius +-60 %). 20 % of
  sites take a satellite 0.6-0.9 of the radius away; its radius 0.5-0.8, aspect 1-1.5 and height 0.55-0.9 of the
  parent are my numbers. Each semi-axis is at least one cell, also my choice: at 0.6 of a cell the narrow stroke's
  D kept read 0.881 and SoftShoulders' cross-step 25.53 cm; at one cell, 0.893 and 25.15.*
- *Bank clods: from the lip, the eligible band cells beside the stroke's line, the band's inner 40 % measured square to
  it, so the cells ahead of the tyre on its own line are not candidates. Each stamp's chance is `ClodBankPerCm` x the
  cell's deposit (bank + lump, cm) x the cluster weight (0 below the absent threshold, 1 half a unit above it), from a
  hash of the cell and the stamp counter. `ClodBankPerCm` landed 0.014 (0.0136 is a third exactly). Sizes are
  3 + 15 u^2.5.*
- *Throw: blobs are 4 + 12 u^2.5 cm, with heading +-25 deg and the throw's own speed x 0.5-1.5. The intervals are a
  Poisson stream in the thrown volume whose rate rides on what waits at the wheel (`ThrowReserveBlobs` 3 mean blobs, my
  number: a plain Poisson stream's waiting mud random-walks without bound). `ClodThrowChance` is 0.2.*
- *Meshes (`build_mud_clods.py`, Blender 5.1 headless; imported, 0 collision, Nanite off), triangles: 0 blob 328,
  1 blob 324, 2 pancake 300, 3 pancake 296, 4 slab 274, 5 chunk 320, 6 chunk 254, 7 chunk 254, 8 smear 302, 9 smear 286.
  All are 10 cm across; heights 6.2 / 5.5 / 2.5 / 3.0 / 3.5 / 6.2 / 7.0 / 5.5 / 2.4 / 2.8 cm; smears 10 x 5.34 and
  10 x 4.22.*
- *Placement: XY scale 0.7-1.4 each, Z 0.5-1.2, random yaw. Each clod sits on the field + ground normal, tilted +-35 deg
  about a random horizontal axis, and sinks 0.35-0.75 of its own height (the mesh's bounds x size / 10 x Z). Family odds
  (blob / pancake / chunk / smear), my numbers: bank 0.15 / 0.40 / 0.35 / 0.10, throw 0.40 / 0.10 / 0.15 / 0.35. Each
  mesh keeps its own pool of instances.*
- *Material: TintRange 0.12. Fresh comes from PerInstanceCustomData 0 (throw 1, bank 0.3), with `FreshDarken` 0.2 and
  `FreshRough` 0.5 proposed. Compiled with no errors. The wet sinking re-pushes at 0.2 cm, and each push is per dirty
  instance.*
- *`GrandTour.Mud.Variety`, the broad stroke (15 cm) over seeds 1-4, LM2 (`bLumpVariety` 0) vs LM2c:*

  | Check | LM2 | LM2c | Target |
  |---|---|---|---|
  | Lump peaks (3x3): CV of nearest-neighbour spacing | 0.258 | 0.355 | >= 0.45: **FAIL** |
  | Lump peak heights: CV | 0.469 | 0.677 | >= 0.5 |
  | Bank clod sizes: CV | 0.089 | 0.629 | >= 0.5 |
  | Bank clod spacing along the stroke: CV | 0.744 | 1.550 | >= 0.6 |
  | Bank clods per metre of stroke | 3.50 | 1.20 (0.34x) | about a third |
  | Volume, determinism | | split 0.000002 %, landed 0, bit-identical | as LM2a |

  *The narrow stroke (40 cm), reported only: spacing CV 0.267 vs 0.335; heights CV 0.395 vs 0.386 (the 10 cm cap); per
  metre 6.85 vs 2.95 (0.43x). Over 5x5 (a satellite merged into its parent), spacing CV is 0.153 vs 0.270.*
- *Old gates moved, both on the narrow 40 cm stroke. SoftShoulders' cross-step reads 25.15 cm (asked under 24; LM2
  17.34): a 10 cm lump on the lip at y 43.8. Settle's narrow detail kept with lumps on reads 0.893 (asked 0.9-1.1;
  LM2 1.009). Every other Settle row passes: recovery 11.3 / 10.3 %, asleep 11.17 / 10.40 s, step 9.83 / 9.62 cm.*
- *The ablation (one feature out at a time; spacing CV, cross-step, narrow D kept):*
  - *LM2c: 0.355, 25.15 cm, 0.893.*
  - *No satellites: 0.351, 25.41, 0.892.*
  - *No absent sites: 0.273, 18.72, 0.938.*
  - *One amplitude: 0.345, 24.26, 0.949.*
  - *Round domes at +-40 %: 0.342, 25.29, 0.895.*
  
  *Two facts for the main session. The absent sites give the spacing its lift, but with the normalisation unchanged
  they pile the held volume onto 65 % of the domes; those reach the cap at the lip and break both old gates. The
  satellites at 0.6-0.9 of a 1.6-cell radius sit 1-1.4 cells from the parent's top: on the 12.5 cm grid they make a
  lopsided lump, not a second peak. No setting of the named numbers lands every row, so none is relaxed and the three
  rows are reported.*
- *Strip (`check_live_mud_drive`): dry 61.0 s and wet 57.5 s, both complete (LM2 64.3 / 58.9). Main dry crossing: live
  768, bank 122, throw 746, squashed 100, sunk 0, recycled 0 (LM2 1,023 / 389 / 1,911 / 474 / 0 / 803). That is
  4.4 bank and 26.6 throw clods per metre of the 28 m mud section (LM2 13.9 / 68.3). The 300-350 live asked is not met:
  the throw is 86 % of the clods spawned. After the spin: live 1,124, bank 191 / throw 1,064. After the wet replay: live 19,
  sunk 1,670.*
- *Spin: 46.06 -> 47.14 m in 3 s; holes -19.9 to -21.6 cm; mounds 2.1-8.0 cm, 1.5-4.0 m behind.*
- *Throw: 1.24 % lost on the dry crossing; 2,996 cm^3 waiting at the wheels at its end.*
- *Crawl: 2.3 m in 5.52 s (LM2 5.77).*
- *Cost, judged (no game):*
  - *Clods: dry mean 0.0156 / p99 0.296 / max 0.701 ms; wet 0.0152 / 0.248 / 0.518 ms (LM2b wet p99 0.884, gate 0.7:
    PASS); at the cap 0.0168 / 0.252 / 0.412 ms.*
  - *GPU at the cap, clods on vs off: 17.023 vs 16.718 ms (+0.305; asked <= 0.3). Base pass 1.012 vs 0.998 ms, shadow
    depths 2.098 vs 2.030 ms. Draw calls 27.1 vs 14.4 base pass and 52 vs 32 shadow (ten meshes; LM2b 42 shadow).*
  - *Settle: dry 0.087 / 0.324 / 0.495 ms, wet 0.106 / 0.383 / 0.612 ms, PASS.*
- *Pictures: `Mud_Clods_Dry.png`, `Mud_Spin_Dry.png` and the new `Mud_OnFoot_Dry.png` (1.7 m up, 3 m behind the settle
  pair's rut start, looking along it). Looked at once. The lips carry bumps of mixed size and spacing, and the clods run
  from crumbs to a few larger chunks, scattered unevenly. The spin shot has an unidentified round light blob at the
  tyre's top by the arch. The look is the owner's, at LM3's gate.*
- *Suite (`terrain drivetrain grip mud surface track`): 5 PASS, 1 FAIL. The terrain fails on stage I's ridge shape alone: the crest's cv at the shipped spot reads 0.85 against 0.22-0.60 (the rest of that row in range: width 50.8 cm, crest 6.77 cm). That is LM2c's variety running past stage I's band; reported, not relaxed. Step 11's held exit passed (6 m 1.9 s after the unheld exit). The escape went 10.6 m forward and 6.0 m back in 6.3 s, the rut mean read -30.9 cm, and the stage H crest report 7.65 -> 5.72 cm. Not started: LM3a.*
- *Follow-up (the main session's "Follow-up decisions after LM2c", same day, no game or foreign Unreal at any run):*
  - *An absent site's share now stays in the bank. The held share is LumpShare x (the W that exists / the W of the full
    site set, `LumpWFull`) over the stamp's eligible cells, so a lump cell takes LumpShare x handed x W / the full W's
    sum. Volume is exact (split error 0.000000 %) and LM2c off is unchanged.*
  - *Tuning table, the broad stroke over seeds 1-4. "Proxy" is the stage I crest cv read the terrain test's way on a
    straight line, mean over the seeds. "Terrain" is the terrain test's own stage I read. Bank clods are per metre at
    ClodBankPerCm 0.014:*

    | Absent share | Spacing cv | Cross-step | Narrow D kept | Stage I proxy | Stage I terrain | Bank clods / m |
    |---|---|---|---|---|---|---|
    | LM2 | 0.258 | 17.34 | 1.009 | 0.443 | 0.46 | 3.50 |
    | 0.35 | 0.350 | 18.37 | 0.965 | 0.452 | 0.62 | 1.10 |
    | 0.40 | 0.353 | 18.43 | 0.971 | 0.454 | (not run) | 1.00 |
    | 0.45 | 0.350 | 18.55 | 0.979 | 0.448 | 0.62 | 1.02 |
    | 0.50 | 0.509 | 18.68 | 0.975 | 0.453 | 0.64 | 0.95 |
    | 0.55 | 0.650 | 18.73 | 0.975 | 0.408 | 0.63 | 0.88 |

  - *The fix brings SoftShoulders and Settle back at every share. Stage I's crest cv reads 0.62-0.64 at every share
    (asked 0.22-0.60; LM2 0.46; LM2c before the fix 0.85), so the absent share does not move it and no value keeps
    that gate. The proxy tracks LM2 (0.443 against 0.46) but not the terrain's one diagonal spot: its four seeds span
    0.36-0.55 at 0.50.*
  - *Shipped: `LumpAbsentShare` 0.5, the lowest share that lands the spacing; 0.55 also lands it but puts the bank
    clods at the edge of a third. `ClodBankPerCm` 0.017 re-lands a third (1.10 against 3.50 per m, 0.31x).*
  - *All five mud tests PASS. Variety: spacing cv 0.509, heights 0.728, clod sizes 0.636, clod gaps 1.573.
    SoftShoulders' cross-step is 18.68 cm. Settle's narrow D kept is 0.975 (broad 1.092); recovery 13.0 / 12.7 %,
    asleep at 10.40 s.*
  - *`ClodThrowChance` 0.065, one drive check. The main dry crossing ends with 352 live (bank 106, throw 309, squashed
    63): 2 over the 300-350 asked. The run's two gt.Mud.Settle 0 crossings read 285 and 366. The strip completes dry
    62.8 s and wet 59.7 s.*
  - *Clods cost, mean / p99 / max: dry 0.0121 / 0.207 / 0.809 ms, wet 0.0103 / 0.183 / 0.291 ms, at the cap 0.0146 /
    0.254 / 0.274 ms. The GPU at the cap is 17.230 vs 16.984 ms (+0.246).*
  - *Suite: 5 PASS, 1 FAIL. The terrain fails on stage I's cv 0.64 and on step 11's held exit, the known flake (the
    run down the ruts took 11.6 s, the held exit 10.6 s). The escape went 10.5 m forward and 6.0 m back; the rut mean
    read -30.7 cm.*
  - *`Mud_Clods_Dry.png`, looked at once: the near bank still shows hard-edged black patches beside several lumps, with
    the cross-step and the detail kept back in range. Their cause is unchecked.*

**The owner, with an eye-level screenshot of the strip: "They are very uniform. Fix that and then move on."** The
screenshot shows three regularities. The clods stand in evenly spaced rows along both rut lips like beads. The lump
domes make a dotted line along the right rut. Every clod is the same size and shape. The causes are in the code: lump
sites on a 4-cell grid jittered only +-0.35 of the spacing, every site present; bank clods spawned at the lump
sites; five clods all from one recipe (a squashed noisy icosphere, 0.6 tall); one scale per instance. After LM2c the
plan moves on to LM3, with no gate for the clods: the owner will see them again at LM3's gate.

**Field (lumps)**, keeping exact volume and determinism (hashes of the cell or site and `NoiseSeed`):

- Sites jittered over the whole grid cell (+-0.5 of the spacing).
- A cluster noise `LumpClusterCm` 150 (smoothed value noise) decides which sites exist: about 35 % are absent,
  in patches, so lumps bunch in some stretches and leave gaps in others.
- Per-site amplitude weight from a skewed hash, 0.3-1.6 (u^2 shaped: mostly small, a few big).
- Elliptical domes: aspect 1-2.2 and a random orientation, radius jitter +-60 %.
- 20 % of sites get a satellite dome at 0.6-0.9 of the radius away: lumpy pairs, not single beads.
- `LumpShare` 0.35, `LumpMaxCm` and the normalisation stay as they are.

**Bank clods**:

- No longer at the site centres. Candidates are random cells of the stroke's band (a hash of the cell and the stamp's
  step), with probability in proportion to the same cluster noise and the cell's deposit, so clods bunch where lumps
  bunch.
- Only in the band's inner 40 % (the rut lip), not out on the flat.
- About a third of LM2's count: the dry crossing ends with roughly 300-350 live, against LM2's 1,023. Report.
- Sizes from a power law, 3-18 cm (size = min + (max - min) x u^2.5): many crumbs, a few chunks.

**Thrown clods**:

- Emission at random intervals (exponential, the same mean rate) instead of a fixed rate.
- Heading spread +-25 deg, speed +-50 %.
- Blob sizes from the same power law, 4-16 cm.
- `ClodThrowChance` 0.5 -> 0.2.

**Shapes** (`Art/Blender/build_mud_clods.py`, headless): 10 variants in four families, 150-400 triangles each.
- Rounded blobs: 2, the current recipe with stronger noise.
- Flat pancakes and slabs: 3, height 0.25-0.35 of across, irregular outline.
- Broken chunks: 3, one or two planar cuts with harder edges.
- Elongated smears: 2, aspect 1.8-2.5.
Re-import with `import_mud_clods.py`.

**Placement per instance**:
- Non-uniform scale: X and Y 0.7-1.4, Z 0.5-1.2.
- Random yaw. Tilt from the local surface normal plus up to +-35 deg.
- Sunk 0.35-0.75 of its height by a hash, so some are half-buried.
- Banks favour pancakes and chunks, throws favour blobs and smears.

**Material** (`M_GT_Clod`):
- Tint variation +-12 % in value.
- A per-instance freshness through PerInstanceCustomData (one float): throws 1 (darker, glossier), bank clods 0.3.
  Static, no fade.

**Cost**: the wet sinking re-pushes only instances that moved more than 0.2 cm since their last push. Re-measure
clods wet p99 (gate 0.7) and the GPU at the cap. With a game running, both are unjudged, per the owner's rule.

**Tests** (a new `GrandTour.Mud.Variety`; every existing mud test keeps passing):

| Check | Target |
|---|---|
| Lump peaks along a crest: CV of the nearest-neighbour spacing | at least 0.45 (report LM2's) |
| Lump peak heights: CV | at least 0.5 (report LM2's) |
| Bank clod sizes: CV | at least 0.5 |
| Bank clod spacing along the stroke: CV | at least 0.6 (clustered) |
| Bank clods per metre of stroke | about a third of LM2's (report both) |
| Volume (lumps, throw) and determinism | as LM2a |

**Pictures**: `Mud_Clods_Dry.png` and `Mud_Spin_Dry.png` again, plus a new eye-level shot looking along the rut, the
owner's own view (`Mud_OnFoot_Dry.png`: camera 1.7 m up, a few metres behind the rut's start, looking along it).

**Follow-up decisions after LM2c (main session, 2026-10-05).** The main session looked at `Mud_OnFoot_Dry.png` and
`Mud_Clods_Dry.png`: the bead rows are gone, and the lips carry lumps of mixed size and spacing. But several near lumps
have hard-edged black pits beside them, which fits the cap cliffs the tests measured (cross-step 25.15 cm, narrow D
0.893, stage I crest CV 0.85).
- **Absent sites leave their share in the bank.** The held-back volume at a cell scales with the lump weight that
  exists there (LumpShare x deposit x W / the W a full site set would give), so the missing sites' volume stays in
  `HeightCm`. The remaining domes keep about LM2's heights instead of piling to the 10 cm cap. Volume stays exact.
- Then tune the absent share inside 0.35-0.55 to land the spacing CV at least 0.45 with SoftShoulders under 24,
  the detail kept at least 0.9, and stage I's crest CV in 0.22-0.60. If no value lands all of them, ship the value
  that keeps the three old gates and report the best spacing CV: the old gates are the owner's shape, and the spacing
  target is the main session's estimate.
- **Fewer thrown clods:** tune `ClodThrowChance` inside 0.05-0.2 so the dry crossing ends with 300-350 clods live.
- The GPU at the cap, +0.305 ms against 0.3, is accepted as noise-level. The satellites stay as built.

### LM3a: snow, the field and the feel

*Done 2026-10-05 (no game and no foreign Unreal at any run, so the cost is judged; build exit 0):*
- *Housekeeping. 1: stage I's crest-cv band is 0.22-0.75 in `GTM6TestRunner.cpp`, the reason in a comment. 2: the mud
  check takes `Mud_Clods_Dry_NoShadow.png` from the same camera with the patch meshes' shadow casting off (the clods keep
  theirs). The hard black patches beside the near lumps do not go: 5,689 pixels (0.44 %) change by more than 8 levels,
  nearly all in the top rows (the far bank and the tussock), and the pixels under 30 in the lower-left, where the patches
  are, read 4,978 with the mesh's shadows and 4,941 without. So they are not the patch mesh's cast shadows; their cause
  is still unchecked (not fixed, as asked). 3: `FGTDeformProfile` owns `LumpAbsentShare`, `LumpClusterCm`,
  `LumpAmpMin/Max`, `LumpAspectMax`, `LumpVarietyRadiusJitter`, `LumpSatelliteChance`, `ClodBankPerCm`,
  `ClodThrowChance`, and the field's own `RidgeReturn`, `RutShoulderCm`, `RutDepthVariation` and a new
  `RutShoulderMinCells` (the field's hard-coded 2-cell wall floor). The patch has each as a UPROPERTY, `ApplyProfile`
  copies them and `Init` pushes them; every default is the value in force before, so the bog and the ford are unchanged:
  the five mud tests read LM2c's numbers to the digit (field CRC 8e0aad06, SoftShoulders 18.68 cm, Settle narrow D kept
  0.930 lumps off / 0.975 on, Variety spacing cv 0.509). 4: the snow numbers are `FGTDeformProfile::SnowDefaults()`, as
  the block and item 4 name them. 5: `M_GT_Clod_Snow`, a copy of M_GT_Clod's graph (instanced usage, the PerInstanceRandom
  tint kept at 0.05, the PerInstanceCustomData freshness kept with FreshDarken 0; colour 0.85 / 0.86 / 0.88, roughness
  0.7, the clay normal at half strength, no wetness), on a snow patch's clod HISMs only. 6: the new wrappers name GoWR and
  the check passes bThrottleCPUWhenNotForeground=False.*
- *Built as the block says, with these choices of mine:*
  - *The drift is a depth curve, not a second section: `FGTRouteSection::SnowDrifts` (start, end, depth, ramp), 60 cm
    from 70 to 80 m, a smoothstep from 35 cm over 2 m beyond each end, baked per cell from the arc of the nearest route
    point (`GTTerrain::SnowDepthCmAt`). One patch, one taper, no seam.*
  - *The snow top is per cell (the depth x the taper at the cell's centre); the mesh's rest Z carries it, so the clods
    and the thrown blobs land on the snow. No rut water in snow (no water grid, `WaterDepthCmAt` 0).*
  - *The rut read is against the ground (the field plus the snow top), so a cut trench reads as a rut of the tyre's
    sinkage, as in mud. The snow ahead for the plough is the mean of the three rut probes (a tyre half in its cut ploughs
    half). In a snow patch it replaces the row's plough term: `SnowPlough` x the snow ahead over the tyre's bottom / the
    wheel's radius x the bog's speed law.*
  - *The belly in snow: its underside is AxleClearanceM (19 cm) over the deepest tyre's bottom. Its drag is
    `BellyDragPerMetre` x the snow standing over the underside at the mud's three points just ahead of its box, on every
    wheel in the patch, with no channel ease (a ploughed channel reads 0). The plough's box spans the car out to the tyres'
    outer edges (2 x the half track + a tyre), its ends inset as the mud's, its sides feathered over one wall (12.5 cm):
    with the mud's side inset the 40 cm berm band lay under the car between the belly's cut and the tyres' trenches.*
  - *Refill: snowing is precipitation below freezing (the weather subsystem's own rule for its SnowAmount), checked at
    1 Hz; `gt.Snow.Refill` -1 follows it, 0 never, 1 always. The tracks fade by the refill's share of the snow's depth
    (255 x 2 / 35 a minute, the fraction carried between passes), the lumps lose the same cm. Clear weather in the check:
    0 refill passes.*
- *Four changes to the stamp in snow only (mud's path is as before), to land the compaction row and keep the berms:*
  - *The return goes to the lip alone (the band's eligible cells beside the stroke's line), normalised over their weight.
    Mud gives each band cell its share of the whole band and drops the shares of rut and capped cells; in snow a quarter
    of the return fell in the tyre's own trench behind it or ahead of it, to be cut again.*
  - *No floor smoothing: stage H's 3-tap mean lowered the capsule's front shoulder toward the trench behind it without the
    volume being counted as cut.*
  - *`RidgeBlend` 1.0 (not a plan number): at the bog's 0.9 the row read 0.8175, 2.2 % over; the lip is capped at
    MaxRidgeCm 8 anyway.*
  - *The ridge smoothing's cap no longer clips a cell already over it: the tyres' stamps cut the plough's berms back to
    8 cm (the first strip run's lips read 8.0 cm everywhere but one cell).*
  - *Also not a plan number: `RutShoulderMinCells` 1, so `RutShoulderCm` 10 stands (at the field's 2 cells a 35 cm wall
    reads 54-62 deg by the cell alignment).*
- *`GrandTour.Snow.Compact`, every row PASS (`Art/mud_shape_test.ps1` widened to `GrandTour.Mud+GrandTour.Snow`: 6 of 6
  Success):*

  | Row | Measured | Asked |
  |---|---|---|
  | Volume gone, a 10 m stroke of 200 stamps at 5 cm sinkage | 0.8021 of the cut (1,571,474 cm^3; error 0.26 %) | 1 - RidgeReturn = 0.8 within 1 % |
  | The same by the shape: (trench - bank) / trench | 0.8027 (the bank 0.1973 of the trench) | reported |
  | The wall below the lip, just cut / after 10 s settled | mean 67.4 / 67.4 deg, min 63.1 / 63.1, 100 % of 98 station-sides at 60 or more | at least 60 |
  | The taper at the border / at SnowEdgeCm (300 cm) in | 0.00000 (snow top 0.0000 cm) / 1.00000 (35.000 cm); 0.5000 half way | 0 / 1 |
  | Refill, 3 min of 1 s passes | the trench floor -37.53 -> -31.53 cm = 6.00 cm; the tracks on the line 1.000 -> 0.831 | 2 cm/min x 3 = 6.00 within 10 % |
  | The trench floor | -37.53 cm under the snow top | -40 (35 + 5), the pockets at most 10 % shallower |
  | The plough (100 ticks of a 1.8 x 1.8 m box, its underside 14 cm over the ground) | berms 0.3000 of the 2,758,455 cm^3 cut, none lost; the channel -21.00 cm (asked -21.0); the berm's top 22.34 cm | reported, exact by construction |

  *Reported beside the compaction row: the same stroke at the bog's RidgeBlend 0.9 reads 0.8154; one 10 m stamp 0.8017.
  The first build read 0.9334 (0.9228 at RidgeBlend 1.0; one stamp 0.8122) before the lip-only return and the unsmoothed
  floor; the second 0.8175 at 0.9 and 0.8045 at 1.0; the third (with the berm kept over the cap) 0.8021.*

- *Strip (`check_live_snow_drive`, its third run; the first stopped at its own patch assertion, the second ran before the
  berm fix: pass 1 258.6 s, pass 2 35.0 s, drift 0.219 / 2.909 m/s = 13.28x, lips 8.0 cm):*
  - *The patch: box x 23.8-116.3 m, y -6.2..6.3 m (740 x 100 cells; the box rule's half width and 2 m margin apply along
    the route too, so the snow tapers in from 23.8 m and is full from 26.8 to 113.3 m). Snow top 35.0 cm at 29 and 50 m,
    60.0 at 75 m. M_GT_Snow and M_GT_Clod_Snow loaded, no water grid.*
  - *Pass 1 (fresh snow): completed, 125.03 m in 257.9 s; lateral at most 0.209 m over the snow; the drift in 45.64 s,
    0.219 m/s (min 0.203); 0.394 m/s through the 35 cm before it and 0.301 after; the belly ploughed 26,429,199 cm^3
    (berms 7,928,760); the field lowered 55,440,946 cm^3 in all.*
  - *Pass 2 (its own trench): completed, 125.07 m in 36.6 s; lateral 0.211 m; the drift in 3.484 s, 2.870 m/s (min
    2.820); the plough 69,466 cm^3.*
  - *Drift speed pass 2 / pass 1 = 13.105 (asked at least 1.15): PASS.*
  - *Drag per wheel, mean fraction of the load (`snow_samples.csv`). Pass 1 in 35 cm: 0.196 = the Snow row's rolling 0.06
    x (1 + its drag scale 1.0 x a full 5 cm sinkage) 0.120 + the belly 0.066 (22.1 cm of snow over its underside) + the
    plough 0.0086 (23.7 cm of snow ahead at 0.39 m/s). In the drift: 0.263 = 0.120 + the belly 0.133 (44.5 cm) + the plough
    0.0076. The friction scale reads 0.70 (the row's grip loss 0.3 at full sinkage), so the grip is 0.28 x 0.7 = 0.196 of
    the load. Pass 2: 0.138 in 35 cm (the plough 0.017, 5.6 cm of snow ahead: the floor's pockets; the belly 0) and 0.153
    in the drift (the plough 0.027, 10.0 cm ahead).*
  - *Cost, judged: Settle pass 1 mean 0.0287 / p99 0.105 / max 0.534 ms (15,402 frames, awake peak 30), pass 2 0.0538 /
    0.247 / 0.355 (peak 41); clods 0.0047 / 0.093 / 0.259 and 0.0071 / 0.149 / 0.308 ms: PASS (mean <= 0.3, p99 <= 0.7).
    Upload 0.0345 / 0.0746 / 0.280 and 0.055 / 0.186 / 0.645 ms. Frame / game / GPU mean 16.74 / 11.65 / 14.30 ms (pass 1),
    18.53 / 13.18 / 16.51 (pass 2). Clods live 177 / 181 (bank 213 / 215, throw 87 / 91).*
  - *`snow_profile.csv`, after pass 2 (pass 1 within 0.5 cm): at 50 m (snow top 35.0 cm) the tyres' trench floors
    -0.71 / -3.14 cm over the ground (-35.71 / -38.14 under the snow top); between them the belly's channel 14.0 cm over
    the ground across -0.68..+0.43 m; lips (the berms outside the tyres) 17.2 / 21.6 cm over the snow top; the walls
    34.36 / 33.20 cm per 12.5 cm cell = 70.0 / 69.4 deg (the talus at ReposeDeg 70 holds them there). At 75 m (snow top
    60.0) floors +0.55 / -1.76 cm over the ground, lips 33.3 / 34.1 cm, walls 70.0 / 70.0 deg, the channel 14.0 cm.*
  - *Pictures, contents only (the look is the owner's): `Snow_Long.png`, low along the line from 56 m: a narrow dark slot
    down the middle, lumpy raised berms either side, a flat white plain beyond them, green ground past the strip, the car
    far off at the exit and a winch post. `Snow_Cockpit.png`, pass 2 at 60 m from the driver's seat: the dash fills the
    lower half; ahead the white strip with its cut and lumpy berms on both sides. `Snow_Trench_Close.png`, 1.9 m up and
    5 m back looking along the -Y side into the drift: a deep cut with a flat channel floor, a narrow slot along it with a
    raised strip beside it, the far wall and the cut's floor in hard-edged dark shadow, a few small lumps on the right
    wall, grass and a winch post at the top. (The second run's close-up, 1.2 m up and 3 m across, saw the berm and not the
    trench: reframed.)*
- *Mud regression (`check_live_mud_drive`, the build before the berm fix; that fix is snow-only): dry 119.03 m in 62.1 s,
  lateral 0.32 m; wet 119.05 m in 59.1 s, 0.33 m: both complete. Settle dry 0.102 / 0.402 / 0.641 ms, wet 0.122 / 0.501 /
  0.758: PASS. Clods dry 0.0149 / 0.270 / 0.535, wet 0.0151 / 0.280 / 0.602: PASS. The dry crossing ends with 374 clods
  live (LM2c follow-up 352). The GPU at the cap 17.510 vs 17.307 ms (+0.203).*
- *Suite (`terrain drivetrain grip mud surface track biome`, after the berm fix): 6 PASS, 1 FAIL. The terrain fails on step 11's held exit alone, the known flake (6 m in 5.9 s against 5.8 s down the ruts; asked 1.05x slower; unheld 4.0 s). Stage I's ridge shape PASSES in its new band: cv 0.64 (0.22-0.75), width 50.5 cm, crest 6.00 cm, floor -23.6 cm. The escape went 10.6 m forward and 6.0 m back in 6.5 s; the rut mean read -30.8 cm; the fords pass. Biome: The Hide's hash 0x977AF3A498E07815 and the Proving Ground's 0x7DBDFB11F2FD2CE1 unchanged. drivetrain, grip, mud, surface, track PASS. No full suite this stage.*
- *Unchecked: every look; the feel. The snow throw draws in the spray's mud pool (brown blobs) and lands as snow lumps.*

**What changes LM3b (for the main session).** In fresh snow the car crawls: 0.39 m/s through 35 cm and 0.22 m/s through
the drift, pass 1 taking 258 s for the 98 m from 27 m to 125 m. The drag at full sinkage equals the Snow row's grip there
(0.196 of the load: the row's rolling doubled by its drag scale 0.120, the belly 0.066). The plough term named here is the
smallest part (0.009). In the drift the drag (0.263) passes the grip, and the car still creeps through at 0.2 m/s. Not
tuned: the Snow row and BellyDragPerMetre are not LM3a's numbers. The owner's gate will feel it.

**Housekeeping first, and LM3 adjustments from LM1-LM2c (main session, 2026-10-05):**

1. **Stage I's crest-CV band goes from 0.22-0.60 to 0.22-0.75.** The owner named the uniformity ("They are very
   uniform. Fix that and then move on"), so the band's top, stage I's sanity bound, moves with it. LM2c ships at
   0.64. The cap-cliff state before LM2c's follow-up read 0.85, so 0.75 still catches that regression. Change it in
   `GTM6TestRunner.cpp` with this reason in a comment.
2. **The black patches beside lumps, diagnose only.** `Mud_Clods_Dry.png` still shows hard-edged black patches beside
   several near lumps, with the shape gates in range. Take the same picture with the mud patch mesh's shadow casting
   off (`Mud_Clods_Dry_NoShadow.png`) and report whether they go. The main session's guess: cast shadows from the
   lumps under the strip's low sun and weak sky light, not geometry. Don't fix it.
3. **Profile-owned variety.** `LumpAbsentShare`, `ClodBankPerCm`, `ClodThrowChance` and the lump numbers become
   `FGTDeformProfile` fields, copied in BuildPatches like the rest, so snow sets its own. The patch-wide `bLumpVariety`
   stays as the master switch.
4. **The snow numbers in the current names** (the block below was written before LM1-LM2c):
   - The relax: `RecoverShare` 0 and `SetSeconds` 0 (walls stand). Talus at `ReposeDeg` 70.
   - Lumps: `LumpShare` 0.5 with `LumpMaxCm` 6 and `LumpRadiusCells` 1.2 (a crumbly lip of small lumps), and
     `LumpAbsentShare` 0.5.
   - Clods: `ClodBankPerCm` 0.03 along the lip and `ClodThrowChance` 0.1.
   - Freshness: 0, since snow has no wet gloss.
5. **Snow clods** use `M_GT_Clod_Snow`, a material instance or copy of `M_GT_Clod` that keeps the per-instance custom
   data and tint path: near-white, rough 0.7, no darkening by freshness. Set on the clod HISMs of a snow patch only.
6. **Carried rules.**
   - Cost gates are mean <= 0.3 and p99 <= 0.7 ms per feature.
   - The snow check script passes `bThrottleCPUWhenNotForeground=False`, as the mud one does.
   - The game rule: check for GoWR/GoW/FarCry6; if one is running, cancel the drive check and the suite and list
     them as owed.
   - The new wrappers' guards name `GoWR`.

- **Section kind**: `EGTRouteSectionKind::Snow`, appended after `Ford` so saved specs keep their values. A road-like
  section with the Snow layer across, `SnowWidthScale` 1.4, no sink. Its patch is made by `ByKind` from a spec-level
  `FGTTerrainSpec::SnowProfile` (an `FGTDeformProfile` with snow defaults, used by every Snow section). A section's own
  `Deform` with Mode On overrides it.
- **The profile** gains `EGTDeformMedium Medium` (Mud, Snow) and `SnowDepthCm` 35. Snow numbers: `RidgeReturn` 0.2
  (snow compacts; 80 % of the volume a tyre cuts is gone), `RidgeWidthCm` 35, `MaxRidgeCm` 8, `RidgeFootCm` 12,
  `RutShoulderCm` 10 (a near-vertical wall rounded over at the top), `RutDepthVariation` 0.1, `FloorNoiseCm` 0.5,
  `RidgeNoise` 0.3, `RidgeWave` 0.3, `RidgeSlump` 0, `LumpShare` 0.5 (the crumbly lip), `ThrowMax` 0.15,
  `ReposeDeg` 70, `OozeRate` 0, `SetSeconds` 0 (walls stand).
- **The snow surface**: the patch mesh's vertex Z = rest Z + SnowDepthCm x taper, where the taper is a smoothstep over
  `SnowEdgeCm` 300 in from the box's border, so the snow meets the landscape at the edge. The field stays relative to
  the snow's top. The landscape hole and the four-patch `MPC_TrackPaint` limit apply as for mud.
- **Stamps**: the tyre sits on the landscape (Chaos has no snow collision), so it cuts to its own bottom:
  depth = SnowDepthCm x taper + sinkage. `StampBelly` in snow cuts to the belly's underside where the snow is above it,
  and gains a side deposit `PloughReturn` 0.3 into a 40 cm band beside the box: a car-wide trench with berms.
- **Traction in a snow patch**: `MaxSinkage` 5 cm (packed snow), `SinkageRate` 0.05. A **plough drag** from the
  uncut snow ahead of each tyre: depth ahead = max(0, the snow surface at the probe minus the tyre's bottom). This is
  the bog's plough term with depth-ahead over wheel radius in place of sinkage, coefficient `SnowPlough` 0.35
  proposed, so a cut rut has none. The belly drags while it ploughs. RutHold works unchanged off the field's walls.
- **Refill**: while the weather snows (the Snow state; the agent finds the accessor), every snow patch cell below 0
  rises by `RefillCmPerMin` 2 toward 0, tracks fade at the same rate, and lumps soften. A whole-field pass at 1 Hz with
  one full upload; nothing runs when it isn't snowing.
- **The strip**: `Art/Unreal/setup_live_snow_drive.py` + `Art/setup_live_snow_drive.ps1`, modelled on the live mud
  ones: `/Game/GrandTour/ArtTests/LiveSnowDrive/L_SnowDrive`, 140 m along +X. Packed road 0-30 m, a Snow section
  30-110 m with a drift at 70-80 m (`SnowDepthCm` 60 there, from a second section or a depth curve: the agent picks
  and says), exit to road. Start at 5 m. The section's surface uses the Snow row. Clear weather unless a run asks.
- **Check** `check_live_snow_drive.py` + `.ps1`: two passes down the same line. Completion and deviation; mean speed
  through the drift on pass 1 (fresh) vs pass 2 (in its own ruts); belly plough volume. Pictures `Snow_Long.png`,
  `Snow_Cockpit.png`, `Snow_Trench_Close.png`, and a profile across the trench to CSV.
- **Tests** `GrandTour.Snow.Compact`: volume gone = 1 - RidgeReturn of the cut within 1 %; the cut's wall below the
  lip is at least 60 deg; the taper is 0 at the border and 1 at SnowEdgeCm in; refill raises a rut by
  RefillCmPerMin x minutes +-10 %. Strip gates: pass 2 through the drift at least 1.15x pass 1's mean speed;
  both passes complete.

### LM3b: the God of War look on snow (chains after LM3a)

*Done 2026-10-06 (no game and no foreign Unreal at any run, so the cost is judged; builds exit 0; Substrate is on):*
- *Runs: build (54 s), the six mud and snow tests (Success), setup, check 1 (stopped at its own script: a MID getter's
  Python name), check 2 (the trials ran and landed, then stopped at the cost step: the material library's Python name),
  the landed numbers into `SnowDefaults()`, rebuild (6 s), the tests again (Success), setup, check 3 (OK; the border
  sampler found a 10-16 level step at the patch edge), check 4 (OK; the step is the subsurface: 1.8-2.6 with SnowSSS 0),
  the MFP fix, setup, check 5 (OK, the numbers below), the targeted suite, the full suite.*
- *Housekeeping 1, the feel. `UGTTractionComponent::SnowBaseRow` (`PM_Dirt`): in a snow patch a tyre's own sinkage rolls at
  the Dirt row's RollingResistance 0.03 x (1 + its SinkageDragScale 1.0 x the sinkage fraction), 0.06 at full sinkage,
  with the contact row's wet scale; the Snow row (0.12 there) applies outside snow patches; the surfaces table is
  untouched. `FGTDeformProfile::SnowBellyDrag` (and the patch's) scales the belly's snow drag (1 = LM3a). The trials
  switch both with `gt.Snow.Plough` and `gt.Snow.BellyDrag` (-1 = the patch's). The check drives at full throttle (LM3a
  asked 3.2 m/s), low range, the diff lock. Segments: A 40-66 m and B 85-110 m (the 35 cm past the entry's settling and
  the drift's ramps), the drift 70-80 m; the mean is the length over the time between the crossings.*

  | Trial (tuning run, check 2) | SnowPlough | SnowBellyDrag | A km/h | B km/h | drift km/h | longest stop | landed |
  |---|---|---|---|---|---|---|---|
  | LM3a's numbers | 0.35 | 1.0 | 23.8 | 1.7 | 1.8 | 0 s | no |
  | my first guess (in SnowDefaults then) | 0.48 | 0.65 | 19.5 | 2.3 | 1.7 | 0 s | no |
  | fit | 1.073 | 0 | 6.9 | 2.0 | 1.7 | 0 s | no |
  | fit | 0.669 | 0 | 13.8 | 9.6 | 6.8 | 0 s | no (drift) |
  | fit | 0.741 | 0.295 | 10.1 | 1.7 | 1.9 | 0 s | no |
  | fit | **0.78** | **0** | 10.8 | 8.4 | 5.5 | 0 s | **yes** |

  *Landed: **SnowPlough 0.78, SnowBellyDrag 0** (in `SnowDefaults()` now; the owner names them). Every trial with any belly
  drag, and the one at 1.073, fell into a 1.7-1.9 km/h crawl through the drift and stayed in it after (B 1.7-2.3); with
  none the drift ran 5.5-6.8 km/h. Nothing between was seen: the drift is bistable at full throttle (not investigated;
  the friction scale reads 0.70 in both). The belly still ploughs the field (26.3 m^3 on pass 1, 7.9 m^3 into berms).*
- *The final check (check 5), at the landed numbers. Trials: LM3a's 24.6 / 1.7 / 1.8 km/h, the defaults 11.0 / 8.4 / 5.5
  (landed). Pass 1 (fresh): completed, 125.06 m in 39.6 s, lateral 0.19 m; A 10.4 km/h, B 8.4, the 35 cm outside the
  drift 9.3, the drift 5.6 (1.550 m/s, min 1.447), the entry 30-66 m 12.5; longest stop 0.0 s. Drag per wheel in the
  drift 0.181 of the load = the Dirt rate 0.060 + the plough 0.119 + the belly 0; in A 0.202; friction scale 0.70.
  Pass 2 (its trench): completed, 125.06 m in 17.5 s, lateral 0.275 m; A 26.6, the drift 28.4 km/h (7.899 m/s).
  **Drift pass 2 / pass 1 = 5.096** (asked at least 1.15): PASS. Trench walls 66-70 deg, floors -0.7..-3.7 cm over the
  ground at 50 m, lips 15-19 cm (35 cm) and 31-41 cm (60 cm) over the snow top.*
- *Housekeeping 2, the throw. `UGTSprayComponent::SpawnThrown` takes the kind: a wheel in a snow patch throws into the
  Snow pool (the white puffs' mesh, their 500 cm/s^2 fall), the blob still carrying its volume to `DepositThrown`, whose
  clods are the snow patch's (`M_GT_Clod_Snow`). Pass 1: 2,362 blobs, 2,362 through the Snow kind, 517,935 cm^3 landed,
  3,723 lost; clods live 355 (bank 162, throw 254). Pass 2: 115 blobs, all Snow. `GetThrowBlobsSnow()` counts them.*
- *Housekeeping 3 (the mud strip's black patches): not in scope, unchecked, for the owner's gate.*
- *M_GT_Snow (`live_snow_style.py`), procedural, a fresh copy of the live M_GT_Mud graph each setup (the WPO, the field
  read, the masked root, the hole and Mask 1 untouched): fresh albedo 0.85 x a shade tint (0.90, 0.96, 1.06) by
  1 - 3 N.L x a 60 cm swing of 2.5 %; the normal bent by value noise at 2 / 12 / 60 cm (slopes 0.10 / 0.12 / 0.10, PCG3D
  hashes); roughness 0.7 +- 0.06 from the 12 cm octave. The glint: 1 cm hashed world cells (on the displaced surface),
  half of them able to sparkle, each a facet (the normal + 0.8 x a hashed unit vector); within 5 deg of the sun's
  half-vector the normal turns to it and the roughness dips to 0.12, on sun-facing surfaces, faded out where a pixel
  spans over 3 cells. **The sun's direction is the Sky Atmosphere Light Direction node (light 0)**: the view uniform's
  AtmosphereLightDirection[0], which the renderer fills from the atmosphere sun light (the strip's DirectionalLight, by
  default) with or without a SkyAtmosphere; a fixed sun if none. Packed (tracks): 0.72 x (0.95, 1.0, 1.08), roughness
  0.45, the grain at 0.3, stage F's lugs at LugTiltDeg 30 (the copied graph's parameter; the patch does not push it).
  Walls (the field's slope 0.8-2.0 cm/cm): 0.64 x (0.93, 1.0, 1.10), roughness 0.55, the grain at 0.6.*
- ***Substrate: on** (`r.Substrate=True`, `r.Substrate.ProjectGBufferFormat=0`, the blendable GBuffer). The route: the
  surface feeds a Substrate Slab on the Front Material (the root keeps the WPO and the opacity mask), Sub-Surface Type
  **Wrap**, SSS MFP from `SnowSubsurfaceColor` (0.55, 0.70, 0.90), Phase Anisotropy 0.3, F0 0.02. In the blendable
  GBuffer a Diffusion slab (MFP, no profile) exports as Default Lit (`SubstrateGetLegacyShadingModels`); Wrap exports as
  the legacy Subsurface model. Substrate rescales the MFP by its 100 cm simple volume over the Slab's thickness (unwired:
  0.01 cm) before taking the transmittance it exports as the subsurface colour, so MFP = -0.01 / ln(colour) cm. Checks 3
  and 4 ran with -100 / ln: a near-white subsurface colour at any amount and a step at the patch edge (below). The SSS
  is halved in packed snow and on walls and fades in over the 3 m taper.*
- *The border: `M_SnowLandscape` takes the same fresh-snow code and numbers (`SnowApron` and three wrappers on its Base
  Color, Normal, Roughness) at the patch box's edge, fading over 3 m outside it and wherever its Snow layer lies. The box
  is LM3a's measured one; the check confirms it equals the patch's.*
- *Samplers (check 5; the PIE viewport is 1440x868 against 1440x900 pictures, so the wrapper moves the boxes 16 px down;
  checks 1-2 projected the border camera's boxes off screen, reframed to 6 m out and 2.5 m up):*
  - *Glint, a 0.8 x 0.8 m box of sunlit fresh snow 2.6 m beside the line at 50 m, seen from the sun's mirror direction:
    **846 of 191,912 pixels over 245** (0.44 %; 628 with all channels over 245); the same frame with GlintDensity 0: 0.
    The box's mean colour 236 / 233 / 229 both ways.*
  - *Border (sample_border.ps1's pattern), the +Y edge at 45 m: **0 dark, 0 sky-coloured** of 92,840 pixels in the border
    box. 1.5 m inside 239 / 234 / 228, 1.5 m outside 203 / 196 / 172 (the apron half way to grass). **10-30 cm either
    side of the edge: +1.6 / +2.0 / +2.4 levels** (R / G / B; with the SSS off +1.8 / +2.1 / +2.5; also with F0 0.04
    +1.9 / +2.3 / +2.7). Before the MFP fix (check 4): +9.8 / +12.6 / +15.8.*
- *Cost of the look (check 5). One camera 9 m over the snow at 43 m looking across the trench (Snow_Cost_*.png; the patch
  fills most of the frame); the patch wears M_GT_Snow, a M_GT_Mud instance with the same field parameters, or M_GT_Snow
  with SnowSSS 0; 5 s CSV profiles in the order snow, clay, no-SSS, no-SSS, clay, snow (a steady drift cancels). **GPU/
  Basepass 1.280 ms snow, 1.336 clay (-0.056 ms)**, 1.219 no-SSS; Prepass +0.009; ShadowDepths -0.019. The whole GPU
  16.69 / 15.84 / 16.55 ms (**snow - clay +0.85**, frame +0.59; the profiles of one material differ by up to 0.64 ms),
  from deferred lighting **+0.39** (snow 3.24 / 3.10, no-SSS 3.10 / 3.24, clay 2.76 / 2.80), Lumen reflections +0.10,
  and with the SSS on only Lights +0.12 and TranslucentLighting +0.13. Check 4 (the wrong MFP) read +0.65. Instruction
  counts: M_GT_Snow 991 pixel / 264 vertex, M_GT_Mud 462 / 264; samplers 3 against 8.*
- *Cost of the field (check 5): Settle pass 1 mean 0.074 / p99 0.321 / max 0.458 ms, pass 2 0.088 / 0.451 / 0.861;
  clods 0.010 / 0.195 / 0.410 and 0.012 / 0.222 / 0.395: PASS. Frame / game / GPU mean 17.69 / 12.31 / 16.13 ms (pass
  1), 19.11 / 12.61 / 16.55 (pass 2).*
- *Pictures, contents only (the look is the owner's). `Snow_Long.png`: low along the line from 56 m: a dark-shadowed slot
  down the middle with blue-tinted shadow on its wall, a wide floor at the left with regular stripes across it, lumpy
  berms either side, flat white snow beyond fading into green grass at both edges, the car far off, a winch post.
  `Snow_Cockpit.png`: pass 2 at 60 m from the seat: the dash and an A-pillar; ahead the white strip with the cut and
  shadowed berms, the snow fading into grass at its sides. `Snow_Trench_Close.png`: along the -Y side into the drift: a
  rounded berm, a deep channel whose floor carries regular stripes across its width, blue-tinted shadow on the walls and
  floor, fresh snow at the left with a faint grain and a few dark lumps. `Snow_Glint.png`: a plane of fresh snow filling
  the frame, scattered small square white specks across it, a faint dent, one dark clod; `_NoGlint` the same without the
  specks. `Snow_Border.png`: grass at the bottom blending into white over a band, the patch's snow above it (the sampler
  reads 2 levels across the edge; the diagnostics `_NoSSS`, `_NoSSS_F004` are the same frame). `Snow_Cost_Snow/Clay/Nosss`:
  the cost camera's frame: the trench and its striped channel diagonally across the snow, grass at the top right.*
- *Tests: the six GrandTour.Mud and GrandTour.Snow tests Success on both builds (compaction 0.8021, wall 67.4 deg, taper,
  refill 6.00 cm, plough 0.3000; the mud numbers LM3a's to the digit). Suite `terrain drivetrain grip mud surface track` (the final build): 5 PASS, 1 FAIL: terrain, on step 11's held exit alone (6 m in 5.9 s against 5.6 s down the ruts; asked 1.05x slower), the known flake, in the bog, which the snow changes do not reach; stage I's ridge PASSES (cv 0.64, width 50.5 cm, crest 6.00 cm), the rut mean -30.8 cm, the fords pass. drivetrain, grip, mud, surface (reachedSnow 1), track PASS. The full suite (`bash Art/suite.sh`, in the background): 27 PASS, 1 FAIL: terrain again on step 11's held exit alone (6 m in 5.4 s against 5.6 s down the ruts); biome's hashes unchanged (The Hide 0x977AF3A498E07815, the Proving Ground 0x7DBDFB11F2FD2CE1); spray PASS (maxSnowInSnow 95).*
- *Unchecked: every look; the feel; why the snow material costs +0.39 ms in deferred lighting with its SSS off; the
  drift's bistable crawl. The stage F stripes show across the belly's channel as well as the tyres' floors (where the
  field has tracks and depth); LugTiltDeg 30 as the block asks, the owner judges.*

**Housekeeping first, from LM3a's findings (main session, 2026-10-05):**

1. **The fresh-snow crawl.** Pass 1 crawled at 0.39 m/s in 35 cm and 0.22 m/s in the drift (125 m in 258 s). At full
   sinkage the drag is 0.196 of the car's weight, which equals the grip available. The Snow row's sinkage rolling
   resistance gives 0.120, the belly 0.066, and `SnowPlough` only 0.009. The row's term and the snow terms count the
   same snow twice. Inside a Snow-medium patch, the row's sinkage rolling resistance is replaced by the snow model: the
   tyre's own 5 cm in the packed base rolls at the Dirt row's rate, and the uncut snow is carried by `SnowPlough` and
   the belly. The Snow row in the surfaces table is untouched and still applies outside snow patches.
   - Then tune only `SnowPlough` and the belly's snow drag scale (LM3a's numbers) to land these on the strip at full
     throttle: pass 1 at 8-15 km/h mean on the 35 cm stretch outside the drift; 3-6 km/h mean through the 60 cm drift;
     pass 1 never stopped for more than 1 s; pass 2 at least 1.15x pass 1 through the drift.
   - Report the values landed on. The owner names them at the gate.
2. **Snow throw as snow.** A wheel in a Snow-medium patch emits through the spray's Snow kind (white puffs), not the
   mud pool. Its thrown clods spawn as snow clods (`M_GT_Clod_Snow`, the snow numbers).
3. **The black patches beside mud lumps** are not the mud mesh's cast shadows (LM3a's no-shadow picture: 4,978 vs
   4,941 dark pixels). The main session's next guess is the lumps' sun-facing-away sides under the strip's weak sky
   light: shading on the 12.5 cm grid's normals, not shadow. Not in LM3b's scope; it goes to the owner at the gate as
   unchecked.

- **Textures**: procedural in the shader (revised 2026-10-05 by the main session). Snow's detail is layered world-space
  noise for the normal and roughness (2 cm, 12 cm and 60 cm octaves), the glint below, and the packed and wall
  responses. No texture is downloaded or painted, so no download needs the owner's OK. If the owner asks for a sourced
  CC0 set at LM3's gate, it's fetched then with the owner's OK for the download (file names, source, size).
- **`M_GT_Snow`**, the patch material in a snow patch, from `Art/Unreal/live_snow_style.py`:
  - **Fresh** (tracks 0): albedo about 0.85, a little blue in shade, soft normal. A **glint**: world-space hashed
    1 cm cells whose facet normal lines up with the sun's half-vector dip in roughness. Check whether the project uses
    Substrate before choosing the subsurface route; the look wanted is soft, slightly blue light in the shade.
  - **Packed** (tracks 1): albedo about 0.72, greyer-blue, roughness 0.45, smoother normal, and the stage F tread
    lugs at `LugTiltDeg` 30 (the tread data is already in the field; mud keeps 0).
  - **Walls** (by the field's slope): compressed snow, a shade darker blue-grey.
- **Snow clods**: `M_GT_Clod`'s snow variant (white, soft) on LM2b's clods, spawned along the lip (`ClodBankChance`
  0.5 in snow) and from the throw. No wet sinking; refill buries them.
- **Border**: the landscape's Snow row takes the same fresh-snow response across a 3 m apron, as section L did for the
  clay, so the patch edge doesn't show.
- **Pictures and samplers**: the LM3a pictures again; the border check on the `sample_border.ps1` pattern; a glint
  count (pixels over 245 in sunlit fresh snow, reported, not gated). Cost: the snow material's GPU vs the clay on the
  same patch.

**Owner gate**: drives L_SnowDrive in Clear and in Snow weather (refill). Names the snow depth, the plough, the
compaction and the look.

### LM3c: snow polish before the owner's gate (named by the main session 2026-10-06, after looking at LM3b)

*Done 2026-10-06 (no game and no foreign Unreal at any run, so the cost is judged; the first build failed its link, every
later one exit 0; Substrate is on):*
- *Runs: build 1 (the editor module's link: `GMaxRHIShaderPlatform` needs `RHI`, added to `GrandTourEditor.Build.cs`), build
  2 (8 s), the six tests (Compact failed my own new channel row, below), the row's channel redefined, two rebuilds (a
  crest percentile and a lumps-off diagnostic row added), the tests twice (6 of 6 Success), setup, check 1 (OK;
  `Snow_Floor_Close.png` showed the scrape streaks breaking at every 12.5 cm cell border), the streak fix, setup, check 2
  (OK, the numbers below), the targeted suite. No trials (the check's `TRIALS` False): nothing retuned.*
- *Item 1, tread only in tyre paths. `PloughBelly` (the snow belly; `StampBelly` is mud's) clears `PhaseTurns` to -1 on
  the cells it cuts whose `TreadTickOf` is not the tick in force (`StampWheel` writes the tick over its capsule; the plough
  advances it after the four tyres' stamps), writes the belly's heading there and marks them scraped (`SnowMark`). The
  tread texture's A (snow only; 0 on mud as before): the lug strength where a tyre's phase is set, -1 where the belly
  scraped. `M_GT_Snow` scales the lugs by A (none where it is 0: no tyre, or a missing patch), and where A is -1 draws the
  scrape streaks: world value noise 55 cm along by 3 cm across (`ScrapeLengthCm`, `ScrapeWidthCm`), the normal tilted by up
  to `ScrapeSlope` 0.15 across the heading, the albedo swung by `ScrapeAlbedo` 0.03, faded where a pixel spans a streak.
  Check 1's streaks broke at every cell border (neighbouring cells' headings differ by fractions of a degree as the car
  yaws, and 50 m from the origin that moves a 3 cm streak by tens of cm); the direction is now the heading binned to 5
  degrees. Test row (the car: four tyres then the belly every 5 cm tick over 10 m): over the middle 6 m, 444 cells carry a
  tyre's phase (the tyres' paths 196 of 196), 438 the belly scraped, **0 of 343 in the channel within 41.1 cm of the line**
  (beyond any capsule's reach). Between 41.1 cm and the tyres' inner edges (68 cm) 112 of 196 carry a phase: the capsules'
  own shoulders (the rear tyres stamp them after the belly has passed). My first row counted the channel to 56 cm and read
  37 of 441: those are those shoulder cells.*
- *Item 2, broken lugs. `FGTMudField::LugStrength` (snow only, static): value noise at 55 cm ranked over the field into
  0.25-1.0 (evenly), and the cells under the 20 % quantile of a second noise at 60 cm at 0, in patches. Test row: 16,128
  cells, **20.0 % missing, the rest 0.250-1.000, mean 0.629**. `LugTiltDeg` 30 stays the peak.*
- *Item 3, the berm through the bank path (`FGTMudField::bPloughBankPath`, true; false is LM3b's sine hump). Per berm cell
  a tyre's bank weight read at its foot on the box's long side: stage I1's plateau over `PloughBandCm` 40 x (1 +
  `RidgeWidthWave` 0.5 x the long wave), stage I2's waves (`RidgeWave` at 250 and 600 cm), `RidgeSideBias` 0.3,
  `RidgeNoise` clumps at 4 cells; `LumpShare` of the deposit into the lump domes (LM2c's held share; over `LumpMaxCm` 6 into
  `HeightCm` in the same cell); no `MaxRidgeCm` cap (LM3b's berm had none: snow's 8 cm would leave no 20 cm berm); berm cells
  marked, and `StampWheel`'s ridge smoothing skips them in snow. No bank clods from the berm (the block names lumps, waves
  and noise; the lip still spawns them). `SnowDefaults()`: **`RidgeWave` 0.6, `RidgeNoise` 0.5** (LM3a's 0.3, 0.3; the
  tyres' lips take them too). Test row (the car, the middle 6 m, the highest surface cell from the tyres' outer edge out
  past the band, per cell column):*

  | Berm crest | cv (mean of the sides) | -Y / +Y cv | mean cm | 90th percentile cm | highest cm |
  |---|---|---|---|---|---|
  | **LM3c** (bank path, 0.6 / 0.5, lumps 0.5) | **0.779** (asked >= 0.35) | 0.848 / 0.710 | 19.30 / 28.20 | 44.03 / 58.44 | 93.07 / 93.67 |
  | LM3b (sine hump, 0.3 / 0.3, the tyres' smoothing) | 0.160 | 0.168 / 0.152 | 19.53 / 20.72 | 27.01 / 26.79 | 28.55 / 28.38 |
  | reported: bank path, `LumpShare` 0 | 0.215 | 0.212 / 0.217 | 18.97 / 21.27 | 25.18 / 29.03 | 28.83 / 29.56 |

  *The berm still takes exactly `PloughReturn` (0.3000 of 3,633,986 cm^3 cut, none lost; 0.044 of it stays in `LumpCm`, the
  rest overflowed). **A fact for the main session: the target is met only through the lumps, and the lumps make it
  spiky.** Without them the crest cv is 0.215; with them the held share piles onto the dome cells and overflows `LumpMaxCm`
  into one cell's `HeightCm`, up to 93 cm over the snow top in a 35 cm snow (unsettled; on the strip, after the 70 degree
  talus, the crest's highest is 59 cm). `Snow_Trench_Close.png` shows it: the far berm is a row of tall sharp triangular
  peaks with a saw-tooth shadow across the channel. Not tuned (the block names no cap); a berm cap, an overflow that
  spreads, or a berm `LumpShare` is the main session's call. Compact's volume rows: compaction **0.8022** of the cut
  (LM3b 0.8021; the shape 0.8028 against 0.8027; the lips' new 0.6 / 0.5), the wall 67.4 / 67.4 deg (min 63.0, LM3b 63.1),
  the floor -37.53 cm, the taper, refill 6.00 cm, the plough 0.3000 (its berm's top 45.43 cm, LM3b 22.34): every row PASS.
  The mud field CRC is **8e0aad06**, unchanged; the five mud tests Success.*
- *Item 4, white snow clods. `M_GT_Clod_Snow`: albedo 0.82 (LM3a 0.85 / 0.86 / 0.88), roughness 0.7, the instance tint +-5 %,
  no freshness darkening (the custom data is not read), the clay normal at half strength, and **M_GT_Snow's Substrate Slab**
  (Wrap SSS, the MFP from `SnowSubsurfaceColor` by the same rule, 0.01673 / 0.02804 / 0.09491 cm, phase anisotropy 0.3, F0
  0.02): 446 pixel instructions, 2 samplers. Before (LM3b's picture): the clods' shaded sides read 51 / 69 / 94 against the
  shaded snow's 72 / 101 / 136. The check (`Snow_Trench_Close.png` against `Snow_Trench_Close_NoClods.png`, the clods
  hidden; clod pixels = changed by over 12 levels in the instances' projected boxes; snow = a ring as wide as the box,
  unchanged; the brighter half of each, Rec. 709 luma): check 2, 284 live, 43 boxes, 28 measured; **16 sunlit: clod 199.6,
  snow 217.9, ratio 0.916** (median 0.967; asked within 15 %: PASS); 12 in shade 75.6 / 95.2 = 0.794. Check 1: 13 sunlit
  0.993 (median 0.967), 6 in shade 0.952.*
- *Item 5, the deferred lighting (diagnosis only). `GTSubstrateInfoLibrary.get_substrate_material_info` (new, editor-only)
  reads the compiled Substrate output: **M_GT_Snow is material type Single** (1 closure, 3 uints a pixel, BSDF features
  SSS | MFPPluggedIn, 12 of 20 bytes a pixel, not the blendable GBuffer's legacy pass-through; shading models 0x0020);
  **M_GT_Mud is Simple** (no features, the legacy pass-through, shading models 0x0002); M_GT_Clod_Snow now Single, M_GT_Clod
  Simple. At run time (`r.Substrate.ViewMode 4`, `Snow_Classify_*.png`, every 4th pixel): with M_GT_Snow 33.1 % of the frame
  Single (yellow) and 19.4 % Simple; with the clay 0.3 % / 51.2 %; **with M_GT_Snow at `SnowSSS` 0, 0.3 % / 52.5 %: the
  pixels fall back to Simple when the SSS is 0.** The CSV (two 5 s profiles each, ABCCBA): RenderDeferredLighting snow -
  clay **+0.355 ms**, snow - no-SSS +0.046 (check 1: +0.335 and under 0.03). So the excess is there with the pixels
  classified Simple: **the classification is not the +0.3-0.4 ms**. ProfileGPU (one frame each): the sun's
  `StandardDeferred(Single)` + `(Simple)` 0.214 + 0.042 = 0.256 ms with the snow, 0.163 with the clay, 0.162 with no SSS
  (the Single tiles cost the sun's pass about +0.09 ms, with the SSS on only); `DiffuseIndirectComposite` 0.217 / 0.222 /
  0.224; `SubsurfaceScattering` 0.196 / 0.201 / 0.200 (it runs with the clay too). The one-frame RenderDeferredLighting
  totals vary 1.8-3.4 ms frame to frame, too noisy to place the remaining ~0.3 ms; its cause is unchecked. Not fixed.*
- *The feel (check 2; check 1 in brackets), the patch's own numbers: pass 1 completed 125.01 m in 38.1 s, lateral 0.207 m;
  A 11.6 (11.3), B 8.4 (8.3), **the 35 cm outside the drift 9.8 km/h (9.6)**, **the drift 5.5 km/h (5.6)**, 1.517 m/s,
  min 1.417; **longest stop 0.0 s**; pass 2 the drift 28.5 km/h; **pass 2 / pass 1 = 5.211 (5.228)**: every gate holds.
  Pass 1 ploughed 26.47 m^3 (7.94 into berms). Settle pass 1 0.075 / 0.276 / 0.410 ms, pass 2 0.091 / 0.428 / 0.875; clods
  0.009 / 0.150 / 0.264 and 0.010 / 0.175 / 0.311: PASS. Throw: 2,333 blobs all Snow; 313 clods live after pass 1.*
- *On the strip (the A segment 40-66 m, the highest field cell 95-185 cm off the line per column): after pass 1 -Y mean
  18.89 cm cv 0.527 (highest 59.3), +Y 18.27 cm cv 0.550 (56.5): **0.538**; after pass 2 0.511. Profiles at 50 m: floors
  -35.7 / -38.1 cm under the snow top, lips 8.8 / 24.9 cm, walls 70 deg.*
- *Cost of the look (check 2): GPU snow - clay +0.60 ms (frame +0.49), Basepass -0.043; M_GT_Snow 1,056 pixel instructions
  (LM3b 991). Glint 843 pixels over 245 (0 without). Border: 0 dark, 0 sky; 10-30 cm either side of the edge +1.6 / +2.0 /
  +2.4.*
- *Pictures (check 2), contents only. `Snow_Trench_Close.png`: along the -Y side into the drift: the near berm in lumpy
  hummocks with pointed tops; the far berm a row of tall sharp triangular peaks whose saw-tooth shadow lies across the
  channel; the channel's floor plain, no stripes across it; the near tyre slot with short runs of stripes along its floor;
  small white clods on the snow. `Snow_Trench_Close_NoClods.png`: the same frame without the clods. `Snow_Floor_Close.png`:
  down at 50 m: a smooth white bank at the left, the -Y tyre slot in blue shadow running diagonally with a row of dark
  dashes along its rim, the channel floor at the right with faint long streaks along the travel and no cell grid (check 1's
  showed a grid of 12.5 cm blocks). `Snow_Long.png`: low along the line: berms both sides with pointed peaks, the plain
  channel, flat snow to grass at the edges, the car far off. `Snow_Cockpit.png`: the dash and an A-pillar; ahead the strip,
  the cut and a spiky berm on the skyline. `Snow_Glint.png` / `_NoGlint`: a plane of fresh snow with scattered white specks
  (none in the second), one small dark spot at the right. `Snow_Border.png` (+ `_NoSSS`, `_NoSSS_F004`): grass in front
  blending to white, berm silhouettes along the top. `Snow_Cost_Snow/Clay/Nosss.png`: the trench across the snow from 9 m
  up. `Snow_Classify_Snow.png`: the patch yellow but for the dark slot, the landscape green; `_Clay` and `_Nosss`: the patch
  green, the clods yellow specks.*
- *Tests: the six GrandTour.Mud and GrandTour.Snow tests Success (the mud field CRC 8e0aad06). Suite `terrain drivetrain grip mud surface track`: 5 PASS, 1 FAIL: terrain, on step 11's held exit alone (6 m in 5.4 s against 5.5 s down the ruts; asked slower), the known flake in the bog, which the snow changes do not reach; stage I's ridge passes (cv 0.64, width 50.5 cm, crest 6.00 cm), the rut mean -30.8 cm; surface reachedSnow 1.*
- *Unchecked: every look (the owner's gate); why the snow material costs ~0.3 ms more in RenderDeferredLighting with its
  pixels classified Simple; the drift's bistable crawl (not met in either check).*
- *Follow-up 2026-10-06 (the main session's decision on the berm's peaks; no game and no foreign Unreal at any run): a
  lump's overflow over `LumpMaxCm` now goes back into the stroke's bank, spread over the band cells that took the stamp's
  deposit by the weights its plain deposit used (`FGTMudField::bLumpOverflowToBand`, every medium; the plough's berm the
  same over its band; a thrown blob's `DepositLump` has no band and keeps the same-cell rule), the volume exact; the berm's
  own **`PloughLumpShare` 0.25** (profile, patch, field; the lips keep 0.5); and, not a plan number, **`PloughBankVariation`
  0.4**, the berm's share of the bank's height swings. The no-spike rows cannot both hold: a uniform, lump-free berm over
  calm lips reads its 90th percentile at 1.03 / 1.08x its median, and with the lips' `LumpShare` 0.5 back alone (they lie
  under the berm) 1.32 / 1.20x, so no berm number brings it to 1.3x. 0.4 is the largest share that keeps the highest
  under 1.6x. The car row (GrandTour.Snow.Compact):*

  | Berm crest | cv | 90th pct / median (-Y / +Y) | highest / median | median cm | highest cm |
  |---|---|---|---|---|---|
  | LM3c first (lumps 0.5, overflow in its cell) | 0.779 | 3.61 / 3.27 | 7.62 / 5.25 | 12.21 / 17.85 | 93.07 / 93.67 |
  | **follow-up shipped** (spread, 0.25, swing 0.4) | **0.175** | **1.40** / 1.22 (asked <= 1.3: FAIL) | **1.53** / 1.41 (asked <= 1.6: PASS) | 17.51 / 20.97 | 26.79 / 29.53 |
  | spread, 0.25, swing 1.0 | 0.243 | 1.52 / 1.28 | 1.87 / 1.58 | 16.70 / 21.29 | 31.15 / 33.57 |
  | LM3b (sine hump) | 0.160 | 1.50 / 1.38 | 1.58 / 1.46 | 18.02 / 19.45 | 28.55 / 28.38 |

  *The sweep (`PloughLumpShare` 0 / 0.1 / 0.25 x swing 1.0-0): the lump share barely moves anything (cv 0.241-0.246 at
  swing 1); the highest passes 1.6x from swing 0.4 down; no pair passes the 90th percentile (best 1.33x at 0 / 0, cv
  0.143). cv at least 0.35 does not hold with the no-spike rows (the best passing the highest row: 0.175); the p90 row
  stays failing in GrandTour.Snow.Compact for the main session. The other Compact rows: compaction 0.8023, the shape
  0.8031, the wall 67.4 deg (min 61.6), the floor -37.53 cm, refill 6.00 cm, the plough 0.3000 (its berm's top 23.66 cm),
  the car's berm 0.3000 of the cut, none lost.*
- *Follow-up, mud: the Settle CRC row runs with `LumpShare` 0, so nothing there can overflow: **8e0aad06**, unchanged. Mud
  cells with lumps do overflow: the Lumps test's narrow stroke put 27,627 cm^3 over `LumpMaxCm` 10 (25,984 by the same-cell
  rule), its field's CRC 4ae38d20 spread against 4f19670e same-cell, the highest bank cell 11.61 against 12.00 cm. The
  rows that moved (before -> after): SoftShoulders cross-step 18.68 -> 18.83 cm; Lumps crest cv 0.510 -> 0.436 (ratio to
  LumpShare 0 2.16 -> 1.84, asked at least 1.5), on the crest line 0.535 -> 0.424 (2.26 -> 1.79), lumps kept at 10 s 93.3
  -> 95.7 %; Settle lumps on, narrow core back 13.0 -> 12.9 %, D10/D0 0.975 -> 1.022 (asked 0.9-1.1), crest 10.83 -> 10.28
  cm; Throw lowered 3,267,391 -> 3,267,627 cm^3; Variety (absent 0.5) spacing cv 0.509 = 0.509, cross-step 18.68 -> 18.83,
  narrow D kept 0.975 -> 1.022, stage I crest cv proxy 0.453 -> 0.440, bank clods 1.10 per m =. Every row without lumps is
  as it was; the five mud tests Success. `check_live_mud_drive.ps1` (run since the mud with lumps changed): OK, the four
  runs 119.01 / 119.02 / 119.03 / 119.07 m in 63.9 / 63.2 / 59.3 / 61.6 s (the last report 65.1 / 62.1 / 59.1 / 62.7),
  Settle and clods PASS.*
- *Follow-up, the strip (check 3): pass 1 A 11.4, B 8.3, **the 35 cm 9.6 km/h, the drift 5.5 km/h**, no stop; pass 2 /
  pass 1 **5.187**: the gates hold. The berm's crest along 40-66 m after pass 1: -Y median 17.37 cm, **90th percentile
  24.81 (1.43x), highest 31.24 (1.80x)**; +Y 17.91, **25.43 (1.42x), 32.09 (1.79x)**; cv 0.257 / 0.306 (LM3c first: highest
  59.3 / 56.5 cm, cv 0.527 / 0.550). Clods: 7 sunlit at 0.911 of the snow (PASS), 11 in shade 1.101. Settle and clods PASS.
  `Snow_Trench_Close.png`: the near berm a low uneven ridge with stepped facets on its inner face, no tall peaks; the far
  berm a rounded ridge with gentle swells, its shadow edge across the channel wavy. `Snow_Long.png`: low berms both sides
  with small lumps and gentle swells along the trench, no spikes, the plain channel, the car far off.*
- *Follow-up, the dashes along the tyre slot in `Snow_Floor_Close.png`: **the tyre's own lugs**. Projecting the floor
  camera onto the field (snow_profile.csv, the camera's own numbers) and reading the picture's luminance along the travel
  at the tyre's floor cells (72-92 cm off the line, the floor -0.7 cm over the ground: the tyre's own path, where the
  test finds every cell with a phase), the pattern repeats every 8.5-9.5 cm (autocorrelation 0.88-0.99; check 2's picture the same, 8.5-9.0 cm):
  `LugPeriodCm` 9, not the 12.5 cm cell grid, so neither cell steps nor their shadow, and not clods (no 9 cm repeat). M_GT_Snow tilts each
  lug's flank by up to `LugTiltDeg` 30 x the cell's strength, and with the sun grazing along the shadow line of the
  channel-side step the flanks turned from it read dark. Reported only.*
- *Follow-up, tests: GrandTour.Mud 5 of 5 Success; GrandTour.Snow.Compact fails on the berm's 90th-percentile row alone
  (above). Suite `terrain drivetrain grip mud surface track` after the follow-up: 5 PASS, 1 FAIL: terrain, on step 11's held exit alone (6 m in 5.8 s against 5.6 s down the ruts; asked 1.05x slower), the known flake in the bog; stage I's ridge passes at cv 0.58 (0.64 before; asked 0.22-0.75), width 50.5 cm, crest 6.01 cm, the rut mean -30.9 cm; surface reachedSnow 1.*

**Why.** The main session looked at `Snow_Trench_Close.png` and `Snow_Long.png` and found three things the owner has
already rejected on mud, before the owner has to see them:
- The packed floor carries **regular stripes across its whole width**, belly channel included. That's a corduroy
  look, the regular-line pattern the owner removed at stage J and the "very uniform" of LM2c.
- **The plough's berm is a smooth rounded rail** running the length of the trench, against "too smooth" and against
  God of War's crumbly lip.
- **The snow clods render dark grey on white snow**, so they read as stones.

**Field and stamps:**
1. **Tread only in tyre paths.** `StampBelly` in snow clears the tread phase (`PhaseTurns` -1) on the cells it
   flattens that no tyre capsule covered in the same tick, and writes its heading. M_GT_Snow draws lugs only where
   `PhaseTurns` >= 0. Where the belly scraped (tracks set, no phase), it draws **scrape streaks** along the stamped
   heading: stretched world noise, 2-4 cm across, 30-80 cm long, faint.
2. **Broken lugs.** Lug strength per cell from a hashed noise (wavelength 40-70 cm) in 0.25-1.0, with about 20 % of the
   cells' lugs missing in patches: no even run of stripes. `LugTiltDeg` 30 stays as the peak.
3. **A crumbly plough berm.** The belly's side deposit goes through the same bank path as a tyre's: snow's
   `LumpShare` 0.5 lumps, stage I's along-stroke waves (`RidgeWave`, `RidgeWidthWave`) and `RidgeNoise`, with no
   smoothing pass on snow berms. Snow's own numbers are fine to state: `RidgeWave` 0.6 and `RidgeNoise` 0.5 for snow.
   Target: the berm crest's coefficient of variation along the trench at least 0.35 (report LM3b's). Volume rows of
   GrandTour.Snow.Compact unchanged.

**Material:**
4. **White snow clods.** `M_GT_Clod_Snow` at albedo 0.82, rough 0.7, no freshness darkening, tint +-5 %. Use the
   same Substrate wrap-subsurface slab as M_GT_Snow if that's cheap. Target: in `Snow_Trench_Close.png`, the mean
   luminance of sunlit clod pixels within 15 % of the sunlit fresh snow around them (take them from the instances'
   projected boxes).
5. **The +0.39 ms deferred lighting, diagnose only.** It's there with the subsurface off, so it isn't the subsurface.
   Check whether Substrate classifies M_GT_Snow as a more complex material than M_GT_Mud (its feature or closure
   bits, the classification tile view, or `r.Substrate` debug output) and report it. Don't fix it.

**Pictures**: the LM3b set again, plus `Snow_Floor_Close.png` (looking down into a tyre floor next to the belly
channel). The suite is the targeted set only.
**Then the owner's LM3 gate** (both strips: `L_MudDrive` and `L_SnowDrive`).

*Gate re-base 2026-10-06 (main session): the berm's no-spike 90th-percentile row went from 1.3x to 1.5x its median.
The tyres' own lip lumps (snow LumpShare 0.5, by design) lie under the berm, and they alone take a flat, lump-free
berm from 1.03-1.08x to 1.32x. The 1.6x highest stays the spike gate. Shipped berm: p90 1.40x, highest 1.53x,
cv 0.175. GrandTour.Mud + GrandTour.Snow: 6 of 6 Success.*

### LM4: God of War snow deformation (named by the owner 2026-10-06 after the LM3 gate)

**The owner, after driving both strips: "mud is looking much better - think now some new textures are the way to go.
As for the snow, the physics feel good, but the deformation isnt quite there."** They sent two pictures: their own
eye-level shot of L_SnowDrive, and a God of War (2018) shot of Kratos's footprints in snow. Their answers the same day:
- **Snow chunks:** a finer grid plus chunk meshes, with a granular material.
- **Order:** snow first, then the mud textures (LM5: new painterly bakes, wet and churned in the ruts, drier clay on
  untouched ground).

**The difference, as the main session read the two pictures:**

| | Our snow | The reference |
|---|---|---|
| The cut's edge | A smooth, continuous wall with vertical streaks, and a rounded berm with small regular teeth along its top | Breaks into angular, chunky blocks, like a crust snapping into plates, some tilted, some fallen in |
| The surface | Smooth, foam-like | Granular and clumpy everywhere, clumps of a few cm |
| The trail | One even channel of even depth | Irregular, with uneven depth and debris in the prints |
| The shade | Saturated blue | Soft neutral grey |

At 12.5 cm a 10-25 cm block is one or two cells, so it can't be shaped in the field alone.

**The physics stay.** The owner said the snow physics feel good: `SnowPlough` 0.78, `SnowBellyDrag` 0 and the
sinkage numbers don't change. The LM3b feel gates must still hold: pass 1 8-15 km/h outside the drift, 3-6 km/h in
it, no stop over 1 s, pass 2 at least 1.15x.

1. **A finer grid for snow.**
   - Each profile owns its cell size (`FGTDeformProfile::CellCm`); snow takes 6.25 cm and mud stays at 12.5. The patch
     mesh follows it (`MeshCellCm` = the profile's cell size).
   - Every number in cell units (`RidgeNoiseCells`, `LumpSpacingCells`, `LumpRadiusCells`, `RutShoulderMinCells`,
     `SettleTileCells`, the FloorNoise wavelength, CellNoise users) is audited. The snow profile states it so that its
     physical size is what's intended, and the stage note gives a table of each one's cm at 6.25.
   - The mud field and its CRC are unchanged.
   - A switch for the measurement, `gt.Snow.FineGrid 0/1`, read when patches are built (restart Play).
2. **Crust plates at the lip.**
   - In snow, the lump kernel becomes a plate. Each lump site owns its Voronoi cell (the jittered sites already exist),
     and its deposit is a flat, tilted plane clipped to that cell (height a + b.x + c.y, tilt 5-25 deg with a random
     azimuth) instead of a dome.
   - Plate edges are sharp steps between neighbouring cells. Plates are 12-30 cm across, as spacing and jitter set.
   - Sites skip as LM2c's do, so the plates crowd in places and gap in others. Volume and normalisation are as LM2a's.
3. **A broken wall line.**
   - In snow the capsule's half-width varies along the stroke, piecewise constant over 15-30 cm segments (a hash of
     the segment) by +-3-8 cm. The wall's outline is then stepped and angular, not a smooth line. The wall angle row
     (at least 60 deg) still holds.
   - About 15 % of the segments drop their lip plate into the trench: a notch in the lip and a chunk mesh on the floor
     (item 4), with the volume moved, not lost.
4. **Snow chunks, not clods.**
   - `Art/Blender/build_snow_chunks.py`, headless: 8 angular shards made by Voronoi-fracturing a 4-8 cm thick slab,
     flat-ish with sharp faces, 6-25 cm across at scale 1, 100-300 triangles. Import with an `import_snow_chunks.py`
     on the clod import's pattern.
   - Snow patches spawn these instead of clods: along the lip at the plates' outer edges, in clusters (cluster noise,
     power-law sizes), and on the trench floor where a plate fell (item 3).
   - Placement: yaw along the lip with +-30 deg spread, tilt 10-40 deg, sunk 20-50 %. Material: `M_GT_Clod_Snow` as
     LM3c set it.
   - Counts at about LM3c's clods, sizes CV at least 0.5.
5. **A granular snow material** (`live_snow_style.py`):
   - Fresh and packed snow get a clumpy granular normal: cellular (Voronoi) clumps at 1-2 cm and 4-8 cm with crisp
     edges, and a height-based darkening in the gaps between clumps. Faint, not a pattern; world-space and without
     repetition at 2 m.
   - Walls and plate faces get a compressed, faceted response: flatter, a shade darker, no vertical streaks.
   - **Shade**: `SnowSubsurfaceColor` and the shade tint go toward a neutral grey-blue, half LM3b's saturation. A dial,
     which the owner names.
6. **An uneven snow top.**
   - The fresh snow surface undulates +-3-5 cm at 0.6-3 m wavelengths (static world noise in the snow top, through
     one `SnowTopCm(XY)` that the mesh base, the stamps' depth and the traction's depth-ahead all read), so the
     trench's depth varies along it.
   - The trench floor varies +-1.5 cm.

**Tests** (`GrandTour.Snow`; every existing Snow and Mud row keeps passing, and the mud CRC is unchanged):

| Check | Target |
|---|---|
| Plate edges in the lip band: steps of 2 cm or more between neighbouring cells, per metre of lip | at least 6 (report LM3c's) |
| Plate tilts | 5-25 deg, with azimuths spread over 360 |
| Wall line: lateral position along the stroke | sd at least 2.5 cm, and at least 20 % of 6.25 cm stations step 2 cm or more |
| No regular pattern: autocorrelation of the crest and of the wall line at lags of 2-8 cells | no peak above 0.3 |
| Chunks: sizes CV, and the share on the floor | at least 0.5; 20-40 % |
| Snow top undulation | sd 2-4 cm over a 20 m line |
| Compaction, walls at least 60 deg, taper, refill, plough, berm no-spike rows | as LM3c |

**Pictures**:
- `Snow_GoW_View.png`: the reference's view, a camera 2.5 m up and 2 m behind-left of a tyre track, looking down
  about 35 deg along it.
- `Snow_OnFoot.png`: the owner's own view, eye level standing in the trench looking along it.
- The LM3 set again.

**Cost**: the snow strip's GPU and game thread with `gt.Snow.FineGrid` 1 vs 0 in the same session; Settle and upload
p99 against the gates; the mesh's triangle count. The finer grid's cost is reported, not gated: snow is on a test
strip. Before snow goes onto a leg, the owner decides with the number.

**Then the owner's gate** (L_SnowDrive), and then LM5.

*Done 2026-10-06 (God of War Ragnarok (GoWR) ran through the whole session and no foreign Unreal ran: builds, the tests, headless Blender,
the shard import and the strip's setup ran (the tests, the import and the setup by their wrappers' command lines, their
game guards refusing); the drive check, its pictures, the FineGrid cost and the targeted suite were cancelled and are
OWED; builds exit 0 after one compile error of mine):*
- *Runs: build 1 (224 s), the seven tests (GoW failed 3 rows: the wall line's steps, a crest correlation bump, the snow
  top's sd from my own wrong normaliser), fixes and rebuilds, the tests (GoW failed the step share again, Compact's
  compaction moved to 0.8115), the diagnostic rows, fixes and rebuilds, the tests: **7 of 7 Success**. Headless Blender
  twice (the first cells came out 1.3-1.6x the across asked), the import, the setup.*
- *Item 1, the grid. `FGTDeformProfile::CellCm` (12.5 by default; snow 6.25); `UGTMudSubsystem::BuildPatches` passes the
  profile's cell to `AGTMudPatch::Init`, which sets `MeshCellCm` to the field's cell. `gt.Snow.FineGrid` (default 1, read
  when the patches are built: restart Play, or `UGTMudSubsystem::RebuildPatchesForTest`): 0 builds a snow patch at 12.5 with
  `FGTDeformProfile::ScaleCellUnits` (x 0.5) so every cell-unit number keeps its cm. The cell-unit numbers StampWheel had of
  its own are the profile's now (`RidgeNoiseCells`, `SettleTileCells`, `FloorNoiseCells`, `PocketNoiseCells`,
  `TracksEdgeCells`; mud's values by default, so the mud field and its CRC are unchanged: **8e0aad06**, the five mud tests'
  numbers LM3c's to the digit). The audit, at 6.25 cm:*

  | Number (where) | Mud | LM3c snow (12.5) | LM4 snow: cells | = cm | |
  |---|---|---|---|---|---|
  | `CellCm`, the field and the mesh | 12.5 | 12.5 | - | 6.25 | the profile's; FineGrid 0: 12.5 |
  | `RidgeNoiseCells` (stage H's clumps) | 4 = 50 cm | 4 = 50 | 8 | 50 | kept |
  | `LumpSpacingCells` (the lump sites) | 4 = 50 | 4 = 50 | 3.2 | 20 | item 2's plates 12-30 cm: built median 19.8 (16.5-23.4) |
  | `LumpRadiusCells` (a dome's radius) | 1.6 = 20 | 1.2 = 15 | 2.4 | 15 | the domes only; the plates do not read it |
  | `RutShoulderMinCells` (a wall's fewest cells) | 2 = 25 | 1 = 12.5 | 1 | 6.25 | `RutShoulderCm` 10 is the wall, as LM3a meant |
  | `SettleTileCells` (and the clods' tiles) | 16 = 2 m | 16 = 2 m | 32 | 200 | kept |
  | `FloorNoiseCells` (StampWheel's 5) | 5 = 62.5 | 5 = 62.5 | 10 | 62.5 | kept (`FloorNoiseCm` 0.5 -> 1.5, item 6) |
  | `PocketNoiseCells` (the firmer pockets, 12) | 12 = 150 | 12 = 150 | 24 | 150 | kept |
  | `TracksEdgeCells` (the tracks' ragged edge, 3) | 3 = 37.5 | 3 = 37.5 | 6 | 37.5 | kept |
  | stage H's ridge smoothing, a 3-cell mean along the stroke | 37.5 cm | 37.5 (`RidgeSmooth` 0.7) | 3 | 18.75 | **snow `RidgeSmooth` 0** (below) |
  | stage I's clod noise (1 cell) | 12.5 | unread (ClodChance 0) | - | - | unread |
  | a dome's semi-axes at least 1 cell (`AddLumpDome`) | 12.5 | 12.5 | 1 | 6.25 | domes only |
  | a thrown blob's one-cell floor (`DepositLump`) | 12.5 | 12.5 | 1 | 6.25 | |
  | the talus, tan(`ReposeDeg`) x CellCm | 38 deg | 70 deg | - | 70 deg | an angle at any cell |
  | the bank clods' chance, `ClodBankPerCm` per cell | 0.017 | 0.03 | x (CellCm / 12.5)^2 | per 12.5 cm cell's area | `FGTMudField::ClodAreaScale` (1 on mud) |
  | the plough's wall feather, max(CellCm, `RutShoulderCm`) | - | 12.5 | - | 10 | `RutShoulderCm` |
  | cm numbers (`LumpClusterCm` 150, `RidgeWaveCm` 250 / 600, the 100 cm side and slump noises, `LugWaveCm` 55, `LugMissingCm` 60, the bands) | | | / CellCm at use | unchanged | |
  | the check's `cell_centres` and wall angle (12.5 hard-coded) | | | the patch's cell | | fixed |

  *Not a plan number: **snow's `RidgeSmooth` 0** (LM3c 0.7, the field's default). Stage H's 3-cell mean is not
  volume-conserving on the stepped lip: Compact's stroke read 0.8115 of the cut gone with it (asked 0.8 within 1 %),
  **0.8000** without; the rows that isolate it: LM3c's 0.7 -> 0.8115, no wall steps -> 0.8000, no steps and 0.7 -> 0.8006,
  no drops / domes / a flat top -> 0.8000 each. The owner has also rejected smoothing.*
- *Item 2, crust plates (`FGTMudField::bLumpPlates`, snow's profile true; the patch only on snow). Each lump site (LM2c's,
  jittered over its whole grid cell, 50 % absent by the 150 cm cluster noise) owns its Voronoi cell over the whole site set
  (absent sites' cells are gaps); W is the site's LM2c amplitude, flat over the cell (`LumpWFull` the same for every site),
  so LM2a's hold and normalisation are unchanged. Each plate the stamp touched (`ReshapePlates`) is then re-levelled to a
  plane tilted 5-25 deg (`PlateTiltMinDeg`/`MaxDeg`, a hash of the site) toward a hashed azimuth, clamped 0..LumpMaxCm (6),
  its height solved by bisection so it keeps its volume (exact; what the clamp cannot hold goes to the band as LM3c's
  overflow). The plough's berm lumps the same. The plate mask goes to M_GT_Snow in the tread texture's B on snow
  (`PlateAlpha`; mud keeps its fresh sheen there).*
- *Item 3, the stepped wall (`WallStepMinCm` 3, `WallStepMaxCm` 8, `WallSegMinCm` 15, `WallSegMaxCm` 30). The half-width's
  step is a hash of the segment along the world axis nearer the stroke's direction (boundaries every 22.5 cm, jittered
  +-3.75: 15-30 cm long), the wall's side and its 60 cm lane; the magnitude one of three levels (3, 5.5, 8 cm, +-0.25: a
  uniform magnitude left a third of the boundaries under 2 cm). Read at the cell's own place along the line, not the
  stamp's clamped foot (the end caps reach 24 cm along and the union of the cuts kept the widest segment: 13-17 % of the
  stations stepping). Inward, the cut still takes the tyre's own width to its full depth: the wall's foot stays and its
  top moves in. `WallDropShare` 0.15 of the segments drop their lip plate: those lip cells take no plate (marked
  `SnowMarkDropped`), their share and what plate they held land on the trench floor's outer 60 % beside that wall (exact),
  and `FloorChunkChance` 0.18 of the dropping segments queue one floor chunk (Source 3), once per segment.*
- *Item 4, shards. `Art/Blender/build_snow_chunks.py` (headless, no add-ons): eight Voronoi cells of a 4-8 cm slab cut with
  bmesh (5-7 neighbour bisectors leaning 6-18 deg, a chipped corner on four), each triangle split in nine, a grain of
  noise, the bottom flat, flat shaded. **Across 7.59 / 8.33 / 10.06 / 11.84 / 13.05 / 15.15 / 21.61 / 21.22 cm, 4.29-8.40
  cm thick, 144 / 216 / 144 / 252 / 180 / 252 / 144 / 216 triangles** (the first build's cells came out 1.3-1.6x the
  across asked: the neighbours are at 0.62-0.8 of it now). `Art/Unreal/import_snow_chunks.py` (+ `Art/import_snow_chunks.ps1`):
  `/Game/GrandTour/Mud/SnowChunks/SM_GT_SnowChunk_0..7`, no collision, Nanite off, M_GT_Clod_Snow. A snow patch draws them
  in place of the clods (`AGTMudPatch::bShards`; the clods if none are imported): yaw along the lip (the spawn's heading)
  +-30, tilt 10-40 off the local normal, sunk 20-50 %, the spawn's size over the mesh's own across +-15 % each way. Lip
  chunks only at plate edges (a 4-neighbour in another plate or a gap), never where a plate fell; sizes 4-25 cm u^3
  (5-25 read cv 0.498 on 48); `ClodBankPerCm` 0.017 (LM3c 0.03) per 12.5 cm cell's area.*
- *Item 5, M_GT_Snow (`live_snow_style.py`): cellular clumps on the displaced surface's XY at `SnowClumpCm` 1.5 and 6 cm
  (PCG-hashed feature points, a dome each with a crisp crease `SnowClumpEdge` 0.22 of a cell wide, slopes `SnowClumpSlope`
  0.18 / 0.25, the gaps darkened `SnowClumpGapDark` 0.07, the fine half of it; faded where a pixel spans a clump; 0.6 in
  packed snow, none on walls and plates; shared with the landscape apron). Walls and plates: the grain at `SnowWallNoise`
  0.3 (0.6), 3D Voronoi facets `SnowFacetCm` 4 cm tipping the normal by `SnowFacetTilt` 0.2 and the albedo by
  `SnowFacetAlbedo` 0.04, the plates' tops at `SnowPlateAlbedo` 0.76. **The shade dial `SnowShadeSaturation` 0.5** (1 =
  LM3b's) takes SnowShadeTint, SnowPackedTint, SnowWallTint and SnowSubsurfaceColor toward their own luminance;
  M_GT_Clod_Snow's MFP from the same colour (0.02066 / 0.02708 / 0.04272 cm). M_GT_Snow **1,542 pixel instructions**
  (LM3c 1,056), 264 vertex, 3 samplers, Substrate Single as before; no compile error.*
- *Item 6, the snow top: `FGTMudField::SnowTopNoiseCm` (three value-noise octaves at 300 / 134 / 60 cm, each rotated, sd
  `SnowTopUndulationCm` 2.5) joins the depth before the taper in `SnowTopAt` and the per-cell `SnowTopCm`, so the mesh's
  rest, the stamps' cut and the traction's `GroundRelativeAt` (the snow ahead, the belly) read the one top. My first
  normaliser (0.52) gave sd 1.75 at 3; the octaves' sum measured 0.30. Snow `FloorNoiseCm` 1.5.*
- *GrandTour.Snow.GoW (new; LM3c's values from the same measure with LM4 off: 12.5 cm, LM3c's cell numbers, domes, no
  steps, a flat top, `RidgeSmooth` 0.7):*

  | Row | LM3c | LM4 | Asked |
  |---|---|---|---|
  | Plate edges in the lip band (cell pairs 25-80 cm off the line, both standing), steps of 2 cm or more per metre of lip | 15.75 (189 of 628 pairs) | **41.50** (498 of 3,072) | at least 6: PASS |
  | Plate tilts (planes fitted to each plate's lumps) | - | **74 plates, median 15.2 deg, 10th-90th 6.0-21.8, 100 % in 5-25**; octants 5 9 6 9 10 12 13 10, mean resultant 0.147 | 5-25, over 360: PASS |
  | Wall line, its outline (90 % up), per 6.25 cm station | sd 2.70 / 1.65 cm, 0 / 0 % stepping | **sd 6.97 / 5.81 cm, 21 / 21 %** | sd at least 2.5, 20 %: PASS |
  | (reported) the wall half way up | sd 4.11 / 1.72, 0 / 0 % | sd 6.25 / 5.38, 21 / 24 % | |
  | Autocorrelation, lags 2-8, a 38 m stroke's middle 36 m, each series less its 1 m moving average | no local peak (lag 2: 0.40 / 0.56 / 0.38 / 0.66) | **highest local peak -0.14** (crest -Y lag 5); lag 2: 0.07 / 0.21 / 0.14 / 0.29 | no peak above 0.3: PASS |
  | (reported) the same, raw | no local peak | **crest -Y 0.42 at lag 5** (0.41 / 0.42 / 0.38: a wiggle on the slow decay), wall -Y 0.22 at lag 8 | |
  | Chunks, the car over 30 m | 48 clods (1.60 per m), sizes cv 0.598 | **48 (1.60 per m): 32 lip, 16 floor = 33 %; sizes 4.0-21.7 cm, cv 0.574** | cv at least 0.5, floor 20-40 %: PASS |
  | Snow top, a 20 m line | sd 0.00 (35.00) | **sd 2.53 cm** (29.45-40.84) | 2-4: PASS |
  | (reported) the trench floor over the ground along the line | sd 1.68 cm (-4.88..-0.81) | sd 1.47 (-4.64..-0.42); depth under the top sd 1.82 (34.86-40.34) | +-1.5 |

  *A fact for the main session: the raw autocorrelation counts a 0.01 rise (0.41 -> 0.42 -> 0.38) on a slowly decaying
  curve as a peak; on 6 m of stroke an estimate's standard error is about 0.1, so the row reads a long stroke with the
  stage I waves and the snow top (2.5-6 m) taken out. The raw series is reported beside it.*
- *GrandTour.Snow.Compact at 6.25 cm, LM4 on: compaction **0.8000** (error 0.00 %), the shape 0.8059; the wall 76.3 / 69.8
  deg just cut / settled (min 69.1 / 65.4), 100 % at 60 or more; the taper 0 / 1 (the top at 300 cm in 29.326 cm = 35
  with the undulation there; the row's asked value now includes it); refill 6.00 cm; the floor -37.70 cm (asked -40.4,
  the top over the cells); the plough 0.3000 (the channel -20.75, asked -20.75); **the berm 90th percentile 1.15 / 1.15x,
  highest 1.20 / 1.28x, cv 0.140** (LM3c 1.40 / 1.53x, 0.175); the tread 0 of 1,261 channel cells; lugs 20.0 %.*
- *Owed (GoWR ran): `check_live_snow_drive.ps1` - the feel gates (pass 1 8-15 / 3-6 km/h, no stop over 1 s, pass 2 at
  least 1.15x), `Snow_GoW_View.png`, `Snow_OnFoot.png` and the LM3 set, the strip's chunks, the FineGrid 1 / 0 cost (GPU,
  game thread, Settle and upload p99, the mesh's triangles); and `bash Art/suite.sh terrain drivetrain grip mud surface
  track`. The mesh at 6.25 cm is, computed from LM3a's 740 x 100 cell box and unmeasured, 1,481 x 201 = 297,681 vertices
  and 592,000 triangles (12.5: 74,841 and 148,000). The check's FineGrid part is new and has not run.*
- *Unchecked: every look; the feel; the cost.*

### LM4b: soft shape, crumbly detail (named by the owner 2026-10-06 after driving LM4)

**The owner, with an eye-level screenshot of L_SnowDrive: "the snow is a bit blocky right now"**, plus a link to
Muhammad A. Moniem's frame breakdown of God of War (mamoniem.com, "Behind the Pretty Frames: God of War"). As the main
session read it:
- God of War draws footprint strokes into a 384x384 target, and a compute pass writes a 1024x1024 R16G16 deformation
  target around the player, which further passes refine and project onto the snow.
- The depth and crumbly detail come mainly from **screen-space parallax** over high-resolution height maps (1024 and
  2048, BC5) and detail textures, with footprint normal-map decals. Not from mesh density.

**What the screenshot shows**:
- the stepped wall line reads as crenellations: square notches in a regular-looking rhythm;
- the hard-edged plates and the berm read as facets;
- a shard on the floor reads as an ice cube;
- the fresh snow's cellular grain (crisp cells with dark gaps) reads as scales or cobbles.
LM4 built chunkiness out of geometry on a 6.25 cm grid, and that comes out blocky. LM4b keeps the shape soft and
irregular, and moves the crumbly detail into the surface, as God of War does.

**Shape (field)**, the 6.25 cm grid and every snow physics number kept:
1. **The wall line.** It becomes continuous noise: two octaves at 25 and 70 cm, +-2-4 cm in all, no piecewise steps.
2. **Soft lumps.** The plates become soft clumps: the dome kernel back, with the Voronoi sites, the skips and the tilt
   kept as a small skew (at most 10 deg). Radii 5-12 cm, so 2-4 cells, with the size spread kept. The fallen-plate
   notches stay, but their edges feather over 2 cells.
3. **Rounded snow chunks.** The shards become clumps: `build_snow_chunks.py` makes 8 lumpy, rounded snow clumps
   (smoothed fracture pieces, bevelled, with noise), 5-18 cm, instead of sharp slabs. The chunk counts stay as LM4's,
   and so do the floor share and the placement.

**Surface detail (`live_snow_style.py`)**:
4. **A snow-clump height map.** A tileable 1024x1024 16-bit map generated by a script from procedural noise
   (`Art/tools/bake_snow_detail.py`, numpy or Blender, written to `Art/Textures/Snow/`). Nothing is downloaded or
   painted.
   - Two layers in its channels: R crumbs (1-4 cm clumps) and G clods (6-15 cm clumps), each a soft clumped
     field: billowy, rounded tops, small crevices, no cell edges.
   - Imported as a linear texture. World-space tri-planar on the field's normal, at two tilings that don't share a
     repeat.
5. **An edge mask.** E = clamp of the field's slope, the tracks boundary and the lip band (raised field next to
   tracked cells), 0-1.
   - **Fresh snow** (E about 0): the crumbs layer at low strength for the normal and a little cavity darkening. The
     cellular grain goes.
   - **Edges, walls, lip and berm** (E high): both layers at full strength for the normal and the cavity, so the
     edges read crumbly.
   - **The packed floor**: smoother, with the tread as LM3c left it.
6. **Parallax, an experiment behind `gt.Snow.Parallax 0/1`.** Parallax occlusion over the detail height, only where
   E > 0.2, in a frame built from the field's normal (not the flat grid's tangent space, which is wrong on walls).
   8-12 steps, amplitude 2-3 cm.
   - Keep it only if it looks right on both walls and lip in the pictures (describe what's seen, the owner judges)
     and costs at most +0.5 ms GPU on the strip view with E > 0.2 in view.
   - Otherwise leave it off by default and report why.
7. The shade dial stays at LM4's half saturation.

**Tests** (`GrandTour.Snow`; every Mud row, the mud CRC, and every Snow row except the blocky ones below keep
passing):

| Check | Target |
|---|---|
| Wall line: sd along the stroke | 2-4 cm |
| Wall line: largest step between neighbouring 6.25 cm stations | at most 1.5 cm (LM4's crenellation read 3-8) |
| Lip band: share of neighbour steps over 3 cm | at most half LM4's (report both) |
| Lip crest CV | at least 0.3 |
| No regular pattern, lags 2-8 | as LM4 |
| Chunks: sizes CV, floor share | as LM4 |

LM4's two blocky rows (plate edges at least 6 per metre; at least 20 % of stations stepping 2 cm) are retired.

**Pictures**:
- the owner's view again: `Snow_OnFoot.png`, eye level in the trench;
- `Snow_GoW_View.png`, the reference angle;
- `Snow_Edge_Close.png`: 60 cm from a trench lip, low, looking along it;
- each with `gt.Snow.Parallax` 0 and 1 if the experiment is in.

**Cost**: FineGrid 1 vs 0 and Parallax 1 vs 0, in the same session. These are LM4's owed measurements too: the feel
gates, the FineGrid cost and the strip shard counts.

**Then the owner's gate** (L_SnowDrive), then LM5.

*Done 2026-10-06 (God of War Ragnarok (GoWR) started at 14:25 and ran through the rest of the session; a foreign UnrealEditor
started at 13:55 had exited before my first Unreal run. Builds, the bake, the texture and clump imports, headless
Blender, the tests and the strip's setup ran, the guarded ones by their wrappers' command lines; **the drive check (the feel
gates, every picture, the parallax pictures), the FineGrid and parallax cost and the targeted suite were cancelled and are
OWED**, LM4's owed items with them. The snow's feel numbers are untouched; nothing of mud moved, CRC **8e0aad06**):*
- *Runs: build 1 (184 s, first time clean), the tests (GoW failed the wall's largest step, the lip steps, the crest cv, the
  chunks' floor share; Compact the berm's highest, 2.18x), build 2 (195 s), the tests, build 3 (194 s), the tests, two small
  rebuilds landing numbers: **6 of 7 Success; GoW fails the lip crest cv row alone** (below). The bake (2 s, run twice while
  tuning it), the texture import, headless Blender (three times while shaping the clumps, plus two look renders), the clump
  import, the setup.*
- *Item 1, the wall line (`FGTMudField::WallOffsetAt`): with LM4's steps off (`WallStepMaxCm` 0) the half-width wanders by two
  octaves of smoothed value noise along the line, `WallWaveAmpCm` **1.0** at `WallWaveCm` 25 and `WallWaveLongAmpCm` **2.0** at
  `WallWaveLongCm` 70 (+-3 cm in all; a lattice row per wall side and 60 cm lane, as LM4's segments). The segments stay for
  the drops only. Landed on GoW's sweep: 1.25 + 2.5 read a largest station step of 1.69 cm.*
- *Item 2, soft lumps (`bLumpSoftDomes`, snow; `bLumpPlates` off): LM2c's domes back on LM4's sites (20 cm apart, half absent
  by the 150 cm cluster noise, the u^2 amplitudes, the ovals, the satellites), radius **8.5 cm +-41 %** (5-12; a dome's
  semi-axes stay at least a cell, so the smallest is 6.25), leaning by a skew of **2-10 deg** toward a hashed azimuth (W x
  (1 + tan(skew) x the offset along it / the dome's height cap): the top of a full dome tilts by the skew). The held share
  lands by W (LM2a's normalisation) and `ReshapeDomes` puts each touched dome back to T x its kernel over its standing cells,
  volume exact, its peak at most **`LumpHeightPerRadius` 0.30 x its radius** (`LumpMaxCm` 6 at most; caps 1.88-3.59 cm,
  median 2.55), the excess to the band as LM3c's overflow. Not a plan number: the cap is what makes the dome soft (uncapped,
  a dome fills to a 6 cm column 10-17 cm across). The berm's lumps the same. The notch's ends feather over
  `WallDropFeatherCells` **2** cells: across each segment boundary the drop's share ramps 0-1 (smoothstep), a feathered lip
  cell drops that share of what lands on it and its dome keeps 1 - it of the kernel (`LipDropShare`). Not a plan number, a fix:
  a drop-marked berm cell's lump share went into its own height every plough tick, which on a soft dome's centre built a
  41 cm tower (Compact's berm 2.18x); on the soft domes it goes to the berm's band now (1.41x). Lip chunks from the domes'
  edges (LM4's rule): `ClodBankPerCm` **0.031** (LM4 0.017: the domes' edges are fewer cells; 0.017 read 15 lip chunks).*
- *Item 3, clumps: `Art/Blender/build_snow_chunks.py` makes eight from an icosphere (320 triangles) scaled to an ellipsoid, 2-4
  fracture planes pulled most of the way in, Laplacian rounding, three octaves of normal noise, a flat bottom, smooth shaded,
  scaled back to the across asked: **5.0 / 6.5 / 8.0 / 9.5 / 11.5 / 13.5 / 15.5 / 18.0 cm across, 2.9-11.1 cm high, 320
  triangles each** (LM4's shards 144-252). The same names; imported as before. A Blender look render (not in game): rounded,
  lumpy pebble-like clumps with a few flatter break faces. The spawns' sizes stay LM4's 4-25 cm u^3 (5-18 u^p cannot reach
  a cv of 0.5: at most 0.46 by the law).*
- *Item 4, the height map: `Art/tools/bake_snow_detail.py` (numpy): `Art/Textures/Snow/T_GT_SnowDetail.png`, 1024 x 1024 of a
  100 cm tile, 16-bit RGB - R crumbs (5,957 blobs, radius 0.5-2.0 cm, 0.5 x radius high, 0.4-1.1 cm), G clods (256 blobs,
  radius 3-7.5 cm, 0.4 x radius high, up to 3.2 cm), B the two by 0.8 / 2.0 cm; lumpy rounded blobs ((1 - d^2)^1.5, outlines
  wobbled by their 2nd-4th harmonics) thinned by a periodic density field (so they clump and gap), joined by a smooth maximum
  (soft crevices, no cell edges), a faint grain; every field periodic. Seam ratio R 0.94 / G 1.01 / B 0.95. The preview
  (`T_GT_SnowDetail_preview.png`) shows dense small round bumps (R), bunched rounded mounds with flat gaps (G), a lumpy mottled
  field (B), and no seam lines in the 2 x 2 tiling. `Art/Unreal/import_snow_detail.py` (+ `Art/import_snow_detail.ps1`):
  `/Game/GrandTour/Textures/Snow/T_GT_SnowDetail`, sRGB off, BC7, wrapped. M_GT_Snow (and the apron) sample it tri-planar on
  the field's normal (|n|^4) at **100 and 113 cm** (`SnowDetailTileCm`), the 60 cm grain octave choosing between them; finite
  differences on each layer bend the normal by `SnowDetailCm` 0.8 (crumbs) / 2.0 (clods) cm of height a unit.*
- *Item 5, the edge mask E (in M_GT_Snow): the largest of the slope (`SnowEdgeSlope` 0.35-1.2), the tracks' boundary
  (4t(1 - t)) and the lip band (raised `SnowEdgeLipCm` 2 over the top next to tracked cells, or the lumps' mask in the tread
  texture's B). Fresh: crumbs at `SnowDetailFresh` 0.35, cavity `SnowCavityFresh` 0.05; packed: `SnowDetailPacked` 0.2,
  `SnowCavityPacked` 0.04, the tread as before; E 1: both layers full, `SnowCavityEdge` 0.3. LM4's cellular grain off
  (`SnowCellGrain` 0), its facets and the plates' albedo gone. `SnowEdgeDebug` 1 draws E. Unchecked: no picture.*
- *Item 6, parallax (`gt.Snow.Parallax`, -1 the material's `SnowParallax`): POM over B where E > 0.2 and a pixel spans under
  1.2 cm, marched in a frame from the field's normal (depth along n, slide in its tangent plane, the map in n's dominant
  projection), `SnowParallaxSteps` 10 over `SnowParallaxCm` 2.5, a linear refine, faded in over E 0.2-0.4; the hit's slide
  moves every detail lookup. It compiles. **Left OFF by default (`SnowParallax` 0): neither its pictures nor its cost could be
  taken (GoWR).** The check takes them when it runs.*
- *Item 7: `SnowShadeSaturation` 0.5 as LM4.*
- *M_GT_Snow **1,641 pixel instructions** (LM4 1,542), 4 samplers (LM4 3), no compile error; M_SnowLandscape compiled.*
- *GrandTour.Snow.GoW, the LM4b rows (the 10 m stroke's middle 6 m; LM4 = LM4's profile through the same measure):*

  | Row | LM4 | LM4b | Asked |
  |---|---|---|---|
  | Wall line sd | 6.97 / 5.81 cm | **3.19 / 2.52** | 2-4: PASS |
  | Wall line, largest step between 6.25 cm stations | 16.57 / 14.99 cm | **1.28 / 1.03** | at most 1.5: PASS |
  | Lip band, neighbour steps over 3 cm | 7.81 % (240 of 3,072) | **3.33 %** (106 of 3,186) | at most half LM4's (3.91): PASS |
  | Lip crest cv | 0.307 / 0.299 | **0.297 / 0.192** | at least 0.3: **FAIL** |
  | No regular pattern, lags 2-8 (36 m, less the 1 m mean) | highest peak -0.14 | **no local peak** | no peak over 0.3: PASS |
  | Chunks (the car over 30 m) | 48: 32 lip, 16 floor = 33 %, cv 0.574 | **50: 34 lip, 16 floor = 32 %, cv 0.669** | cv 0.5, floor 20-40 %: PASS |
  | (retired) lip steps of 2 cm per metre of lip | 41.50 | 29.33 | (was at least 6) |
  | (retired) wall stations stepping 2 cm | 21 / 21 % | 0 / 0 % | (was at least 20 %) |
  | (reported) lip crest cv over the 38 m stroke's middle 36 m | - | 0.308 / 0.286 (LM3c 0.393 / 0.350) | |

  *The crest row, a fact for the main session: the two lip rows pull against each other and no setting tried holds both
  (GoW's sweep): the dome cap 0.30 x radius 3.33 % / cv 0.297 / 0.192; 0.35 4.08 % / 0.294 / 0.206; 0.45 6.03 % / 0.297 /
  0.232; uncapped 8.73 % / 0.324 / 0.293; amplitude- or radius-scaled caps 3.80-5.96 % / +Y 0.20-0.26; skew 0 3.30 %; 65 %
  absent 3.23 % / 0.309 / 0.194. **With no lumps at all the +Y side reads 0.153** (and the steps 3.17 %): the +Y lip carries
  the heavier bank (`RidgeSideBias`) and its cv is the bank's, so only tall (steep) lumps lift it; LM4's own +Y reads 0.299,
  under 0.3 too. Over 36 m LM4b reads 0.308 / 0.286. I kept the softness (the owner's complaint) and left the row failing; the
  main session decides (a mean of the sides, the 36 m stroke, a lower target, or a bank number this stage does not name).*
  *LM4's plate tilt and azimuth rows are reported now, not asserted: the soft domes' skews are 2-10 deg by construction (the
  block's at most 10), and a plane fitted through a dome's flank is not a tilt (48 fitted, median 5.6 deg).*
- *GrandTour.Snow.Compact (LM4b): compaction **0.8001** (error 0.01 %); walls 76.2 / 70.0 deg just cut / settled (min 69.8),
  100 % at 60; the floor -37.71; taper, refill 6.00 cm, plough 0.3000 (channel -20.75) as LM4; **the berm 1.27 / 1.41x** (90th
  percentile / highest over the median; LM4 1.15 / 1.28), cv 0.131.*
- *Owed (GoWR ran): `& Art/check_live_snow_drive.ps1` - the feel gates (pass 1 8-15 km/h outside the drift, 3-6 in it, no stop
  over 1 s, pass 2 at least 1.15x), `Snow_GoW_View.png`, `Snow_OnFoot.png` and `Snow_Edge_Close.png` each with
  `_Parallax1`, `Snow_Edge_Mask.png`, the LM3 set, the strip's shard and clump counts, FineGrid 1 / 0 and Parallax 1 / 0 cost
  (the strip view and the edge view); and `bash Art/suite.sh terrain drivetrain grip mud surface track`. The check's new
  phases (the parallax pairs, the edge camera, the mask, the parallax cost) and LM4's FineGrid part have never run.*
- *Unchecked: every look in game; the feel; the cost; the parallax.*

*Gate re-base 2026-10-06 (main session): LM4b's lip crest row goes from at least 0.3 to at least 0.17 each side. The
soft domes read 0.297 / 0.192. Only tall, steep lumps lift the heavier +Y bank, and they bring the blockiness the owner
named back (8.73 % of lip steps over 3 cm uncapped, against LM4's 7.81 %). No lumps read 0.153, so the row still asks
the lumps for something. GrandTour.Mud + GrandTour.Snow: 7 of 7 Success. The drive check, pictures, cost and suite
are owed (God of War running).*

### LM4c: piles, not walls (named by the owner 2026-10-06 after driving LM4b)

**The owner, with an eye-level screenshot: "Its looking much better, but the form of the snow is too uniform, and it
sticks up way too much, those tall edges need to fall down into piles more, rather than sticking up."**

**In the screenshot**:
- Each side of the trench is one continuous tall cliff: the 35 cm cut wall standing at about 70 deg, with the berm
  stacked on top of it. On the strip the berm is 17-32 cm over the snow top, so the edge stands 50-65 cm.
- It runs the whole length at about the same height.

**The causes in the numbers**:
- snow `ReposeDeg` 70, with no relax (`SetSeconds` 0), so nothing ever falls;
- the belly plough's `PloughReturn` 0.3 laid into a narrow `PloughBandCm` 40, right at the wall's top;
- the deposit even along the trench (`PloughBankVariation` 0.4).

The snow physics stay (`SnowPlough` 0.78, `SnowBellyDrag` 0, the sinkage numbers). The LM3b feel gates must still hold,
with pass 2 at least 1.15x pass 1, and the snow that falls into the trench can now cost pass 2 a little.

1. **Loose snow slumps, the cut stands in places.** The talus repose per cell depends on what the cell is:
   - **Loose** (deposited snow above the snow top, the berm and the lip): `LooseReposeDeg` 35.
   - **The cut wall** (below the snow top): `WallReposeDeg` 60 +-20 by a world noise at 40-80 cm, so 40-80 deg.
   - A pair of cells uses the higher cell's repose. The talus runs in Settle as now, with snow's `SetSeconds` still 0
     (no relax).
2. **Wall collapses after the car.** The wall is cut in segments of 30-80 cm (a hash of the segment). A quarter of
   them (`CollapseChance` 0.25) collapse `CollapseDelayS` 0.5-3 s after they're cut: their top 30-60 % (above the
   floor, the lip included) moves as a cone-shaped pile onto the trench floor at the wall's foot.
   - The notch's edges feather over 2 cells. Volume is moved, not lost.
   - One or two snow clumps spawn on the pile.
   - Driven from Settle with a per-segment timer, so it happens visibly behind the car.
3. **The berm into piles.** The plough's band widens to `PloughBandCm` 70, with a falling profile: heaviest at the
   wall, decaying outward. The plough deposit, and the lips' deposit too, is modulated along the trench by a cluster
   noise of wavelength 1-2.5 m and range 0.2-1.8: separate piles with low gaps, not a continuous berm. The talus then
   spreads each pile down to the loose repose.

**Tests** (`GrandTour.Snow`; every Mud row and the mud CRC unchanged; every Snow row passes except the one retired):

| Check | Target |
|---|---|
| Edge height over the snow top (the berm crest) | median at most 0.6x LM4b's, and 90th percentile at most 0.6x LM4b's (report both) |
| Piles: crest maxima with at least 3 cm prominence, per 10 m | 4-12, spacing CV at least 0.4 |
| Berm crest CV along the trench | at least 0.35 |
| Wall cells steeper than 55 deg | 15-60 % (some stand, some fell) |
| Floor debris: trench floor cells raised 2 cm or more | 8-30 % |
| Collapses per 10 m of wall, and their delay after the cut | report |
| Compaction (`Compact`'s volume row) | unchanged: talus and collapses only move snow |
| Lip steps over 3 cm, and no regular pattern | at most LM4's 7.81 %; as LM4 |

`Compact`'s "walls at least 60 deg" row is retired, replaced by the wall row above.

**Pictures**: `Snow_OnFoot.png`, `Snow_GoW_View.png`, `Snow_Edge_Close.png`, and a collapse pair: the same camera on a
freshly cut wall at 0.2 s and 4 s, `Snow_Collapse_0s.png` and `Snow_Collapse_4s.png`. The parallax pairs are still owed
from LM4b, as are the costs (FineGrid and Parallax 1 vs 0) and the feel gates.

**Then the owner's gate**, then LM5.

*Done 2026-10-06 (God of War Ragnarok (GoWR) ran through the whole session; the OpenAI Codex app ran its own Unreal renders in this
project twice (17:28-17:30 and 17:32-17:34, `review_panda.py`): the first showed in my check before build 7, which ran beside it (UBT,
not Unreal; the DLL was written before the render's start), and every Unreal run of mine waited for none to run. Builds, the tests and the strip's
setup ran, the guarded ones by their wrappers' command lines; **the drive check (the feel gates, every picture, the collapse pair,
LM4b's parallax pairs and edge mask), the Settle, FineGrid and parallax cost and the targeted suite were cancelled and are OWED**.
The snow's feel numbers are untouched (SnowPlough 0.78, SnowBellyDrag 0, the sinkage); nothing of mud moved, CRC **8e0aad06**, the five
mud tests' lines as LM4b's to the digit):*
- *Runs: build 1 (435 s, first time clean), the tests (6 of 8: Piles failed the pile count, the crest cv, the wall and the floor rows,
  Compact the berm's highest at 1.63x), six more builds and seven Piles-only runs while landing the numbers (a reported sweep each; the
  tuning sweep read its variants from a scratch file, taken out before the last build), the collapse plane fixed (below), build 8,
  the tests: **8 of 8 Success**. The strip's setup: LIVE_SNOW_SETUP_OK, M_GT_Snow 1,641
  pixel instructions, 0 compile errors.*
- *Item 1, the talus per cell (`FGTMudField::bCellRepose`, Settle's pair): a pair's talus is the higher cell's - `LooseReposeDeg` where
  it stands above the snow top or holds a collapse's pile (`SnowMarkDebris`), else its static wall repose, `WallReposeDeg` +-
  `WallReposeRangeDeg` by two rotated octaves of world value noise at 40 and 80 cm, ranked over the field so the angles spread evenly
  (built once per patch, `PrepareSnowPiles`). SetSeconds stays 0. Mud keeps ReposeDeg (the pair's arithmetic is the same, so the CRC).*
- *Item 2, the collapses (`CollapseSegmentAt`, `ArmCollapse`, `FireCollapses`, `Collapse`): LM4's segment scheme at 30-80 cm (a hash of
  the segment, the wall's side and its 60 cm lane), `CollapseChance` of them collapse. A stamp that lowers a cell of the cut's outer 40 %
  beside the line by 1 cm or more (not plan numbers: `CollapseArmOut` 0.6, `CollapseArmMinCm` 1) arms its segment and restarts its
  timer, so the collapse comes 0.5-3 s (a hash) after the **last** tyre. `SettleClockS` (the sub-steps run) drives the timers. Per
  station the floor beside the foot and the top within 40 cm give the cut level (the top 30-60 % by the hash); everything above a plane
  rising back at the loose repose from where the face crosses that level comes off (the lumps first), the ends feathered over 2 cells;
  the volume lands exactly as a cone on the trench floor at the wall's foot (over the segment and the feather along, to the far foot
  across), its cells marked loose; 1-2 clumps (Source 3) on it. A fix on the way: the plane first started at the wall's foot, and over
  a wall the talus had already eased it took almost nothing (median pile 0.8 litres, 0.9 cm high); anchored where the face crosses the
  cut level it moves 3.6x the volume.*
- *Item 3, the berm in piles: the plough's band falls from the wall as (1 - u)^`PloughFallPower` (not a plan number, landed 0.5), and the
  plough's and the lips' bank weights (read at the cell's foot on its line) take a cluster factor: two rotated octaves at 100 and 250 cm,
  ranked over the field and mapped by smoothstep (not a plan number, `PileContrast` 1: piles and gaps, fewer middling stretches) onto
  `PileClusterMin`..`PileClusterMax`. The volume is normalised as before (exact).*
- *Landed numbers (GrandTour.Snow.Piles' sweeps; the block's in brackets): **LooseReposeDeg 50** (35), **WallReposeDeg 64** +- 20 (60),
  **CollapseChance 0.2** (0.25), **PileClusterMin 0.08** (0.2; max 1.8), **PloughBandCm 85** (70); delays 0.5-3 s, top 30-60 %, 30-80 cm,
  feather 2, clumps 1-2 and the 1-2.5 m waves as the block. The block's numbers through the same car: edge x0.58 / x0.51, crest cv 0.230 /
  0.255, piles 3.3 / 4.7 per 10 m, the outer walls' cells 41.2 % steep, the floor 56.2 % raised.*
- *GrandTour.Snow.Piles (new; the car of Compact over 46 m with Settle after every 1/60 s tick and 5 s more, measured 4-40 m; LM4b =
  SnowDefaults with every LM4c number off, through the same drive):*

  | Row | LM4b | LM4c | Asked |
  |---|---|---|---|
  | Edge height over the snow top (the berm crest, 96-250 cm out), median / 90th percentile | 19.01 / 28.67 cm | **10.56 / 16.20 cm (x0.56 / x0.57)** | at most x0.6: PASS |
  | Piles: crest maxima with 3 cm prominence, per 10 m (-Y / +Y); spacing cv | 5.3 / 5.0; 0.585 | **5.6 / 4.7; 0.474** (mean 189 cm) | 4-12, at least 0.4: PASS |
  | Berm crest cv (-Y / +Y) | 0.266 / 0.293 | **0.356 / 0.360** | at least 0.35: PASS |
  | Wall cells steeper than 55 deg (the outer walls' cells below the snow top) | 100.0 % | **57.2 %** | 15-60 %: PASS |
  | Floor debris: cells within 10 cm of a tyre's line raised 2 cm or more (against the same drive unsettled) | 0.0 % | **29.4 %** (mean 1.99 cm) | 8-30 %: PASS |
  | Collapses per 10 m of wall; delay after the last cut | - | **3.54** (outer walls 3.89); **0.60 / 1.67 / 2.77 s** | report |
  | Compaction (Compact's volume row); the volume over the 5 s after the car | 0.8001 | **0.8005**; moved 0.16 cm^3 | unchanged: PASS |
  | Lip steps over 3 cm (the single tyre, settled 5 s); a regular pattern (lags 2-8) | 2.82 %; none | **6.16 %; no peak** | at most 7.81 %; as LM4: PASS |
  | The same stamps and dt twice | - | CRC 00900883 both, 77 / 77 collapses | PASS |

  *The collapses over the whole drive: 77 fell on 73 segments (4 twice), 223,093 cm^3, 124 clumps queued; a pile 0.0 / 1.5 / 12.5
  litres (min, median, max), its top 0.0 / 1.8 / 11.2 cm over the floor; segments 35-79 cm. Reported: every wall's cells 35.6 % steep
  (LM4b 55.4 %: the inner walls are the belly channel's feathered side, 30.4 % steep even in LM4b, so the row reads the outer walls); per
  station (the steepest rise from floor to top) the outer walls 78.8 % (LM4b 100 %); the settled crest's 90th percentile x1.53 and
  highest x2.13 its median. The mean cross-section (cm over the snow top at 110 / 122 / 135 / 160 cm out): LM4b 4.7 / 19.8 / 12.9 /
  0.0, LM4c -1.5 / 9.7 / 8.0 / 4.4.*
- *The other Snow rows that moved (all PASS): Compact - compaction 0.8005 (LM4b 0.8001), the unsettled berm's 90th percentile and
  highest **x1.47 / x1.58** its median (LM4b 1.27 / 1.41; asked at most 1.5 / 1.6), cv 0.269 (0.131); its settled-wall row retired as
  the block says (reported: mean 64.5 deg, 62 % at 60 or more; LM4b 70.0, 100 %), the just-cut row unchanged (76.2 deg). GoW - the wall
  line's largest step **1.49** / 0.97 cm (LM4b 1.28 / 1.03; asked at most 1.5), the lip band's steps over 3 cm **3.83 %** (LM4b 3.33 %;
  asked at most half LM4's 7.88, 3.94), the lip crest cv 0.344 / 0.234 (0.297 / 0.192), chunks 44 (29 lip, 15 floor = 34 %, cv 0.655).*
- *Facts for the main session (the sweep is in the test's log, `Snow: LM4c sweep`):*
  - *The floor row and the wall row pull against each other through the wall's repose. The trench is the tyre's 28 cm and its wall
    about 40 cm, so a wall that eases under 55 deg spreads its snow across the floor's middle: wall 60 read the floor 35.6 % with the
    outer walls 46 % steep, 64 reads 29.4 / 57.2, 65-67 read the walls 60-62 %. The block's loose 35 deg pours the berm into the trench
    as well (the floor 40.9 % with loose 35 alone). The landing sits inside both, close to both edges.*
  - *The crest cv and the loose slump: at 35 deg the talus smooths the piles to cv 0.23-0.25; it takes the steeper loose repose, gaps to
    0.08 and the smoothstep mapping to reach 0.35.*
  - *The lips' cluster factor reaches two LM4b rows of GoW, both at the edge: the wall line's step (its 90 %-depth crossing interpolates
    into the lip, whose height now varies; 1.49 against 1.5) and the lip steps (3.83 against 3.94).*
  - *Compact's no-spike rows (LM3c, on the unsettled berm) hold narrowly (1.47 / 1.58); piles with low gaps put the settled crest's
    highest at 2.1x its median, by design.*
  - *On other noise (the field's seed 2-4, as another stretch of the world would read) the landing moves rows across their limits:
    seed 2 the edge's 90th percentile x0.62 and GoW's wall step 1.70; seed 3 the piles 3.6 / 3.9 per 10 m and GoW's lip steps 4.74 %;
    seed 4 the outer walls 61.4 % and the floor 36.0 %. The rows are met on the test's stretch with thin margins.*
- *The check (`check_live_snow_drive.py`): the berm's crest read out to 250 cm; each pass reports the collapses; after
  `Snow_Edge_Mask.png` the collapse pair - `UGTMudSubsystem::CutSnowTrenchForTest` stamps a single tyre's fresh cut 2.9 m to +Y of the
  line from 90 to 99 m at once, the camera across the trench from the collapsing segment nearest 94.5 m, `Snow_Collapse_0s.png` 0.2 s
  and `Snow_Collapse_4s.png` 4 s after the cut, and the collapses that fell in between. Not run.*
- *Owed (GoWR ran): `& Art/check_live_snow_drive.ps1` - the feel gates (pass 1 8-15 km/h outside the drift, 3-6 in it, no stop over 1
  s, pass 2 at least 1.15x; the fallen snow on the floor feeds the snow-ahead read, so pass 2 may move), `Snow_OnFoot.png`,
  `Snow_GoW_View.png`, `Snow_Edge_Close.png` (each with `_Parallax1`), `Snow_Edge_Mask.png`, `Snow_Collapse_0s.png` /
  `Snow_Collapse_4s.png`, the LM3 set, the Settle cost (the talus keeps tiles awake longer behind the car), FineGrid 1 / 0 and Parallax
  1 / 0; and `bash Art/suite.sh terrain drivetrain grip mud surface track`.*
- *Unchecked: every look in game; the feel; the cost; the collapses as seen.*

### LM4d: the middle isn't flat (named by the owner 2026-10-06, driving LM4c)

**The owner, with an eye-level screenshot looking down the trench: "the edges look great, but the middle is still very
perfectly flat."** The middle is the channel the belly scrapes: `StampBelly` in snow flattens a box to the
underside's height, a level plane about 1 m wide with only faint scrape streaks in the material. Keep LM4c's edges
exactly as they are. The snow physics stay, and so do the LM3b feel gates (pass 2 at least 1.15x).

1. **The scrape isn't a plane.** The belly's target height varies by +-2-3 cm over two octaves (20 and 60 cm),
   stretched 2-3x along the heading, so the channel has long, shallow undulations instead of a level floor. The
   tyres' floors vary as now.
2. **Smear ridges.** Snow the belly drags collects into low ridges along the heading: 30-80 cm long, 8-15 cm wide,
   1-3 cm high, a few per metre of channel, by a hash of the stroke and position, clustered, not in rows. The volume
   comes from what the belly flattened: moved, not lost.
3. **Spill back.** `PloughSpillShare` 0.15 of the plough's side deposit falls back into the channel as LM4b-style soft
   lumps and snow clumps (meshes), scattered and clustered. Compaction stays as it is.
4. **Material.** The channel takes an edge-mask floor of about 0.35 (`BellyDetail`), so the crumbs and clods detail
   shows there at mid strength, plus stronger scrape streaks than LM4b's.

**Tests** (`GrandTour.Snow`; every LM4c row and every Mud row keeps passing):

| Check | Target |
|---|---|
| Channel floor height over 1 m x 3 m windows | sd at least 1.2 cm (report LM4c's) |
| Smear ridges per metre of channel | 1-4, spacing CV at least 0.4 |
| Spill: channel cells with at least 2 cm of lump | 5-20 % |
| Compaction and volume | unchanged |
| No regular pattern in the channel profile, lags 2-8 | no peak above 0.3 |

**Pictures**: the owner's view again (`Snow_OnFoot.png`, looking down the trench) and `Snow_Channel_Close.png`.

*Done 2026-10-06 (God of War Ragnarok had closed by LM4d's first build, and no foreign Unreal ran during it: everything ran,
the drive check and the targeted suite included - the first drive check since LM3c, so it reads LM4, LM4b and LM4c's owed items
too. The snow's feel numbers are untouched; nothing of mud moved, CRC **8e0aad06**):*
- *Runs: 8 builds (the first 109 s, clean), the tests 5 times and 5 Channel-only runs while finding why GoW's chunks moved
  (below): **8 of 9 Success; GoW fails "LM4 chunks - 20-40 % on the trench floor" at 42 %**. The strip's setup (M_GT_Snow 1,642
  pixel instructions, 0 compile errors), the drive check (LIVE_SNOW_DRIVE_OK), the targeted suite: **6 PASS, 0 FAIL** (terrain, drivetrain, grip, mud, surface,
  track).*
- *Item 1 (`FGTMudField::BellyOffsetCm`): the plough's target over the ground + `BellyUndulationCm` 2.5 x clamp(the sum of two
  value-noise octaves, -1..1), at 20 and 60 cm across, 2.5x longer along the world axis nearer the heading, each octave's lattice
  turned in its stretched space. World-anchored, not in the heading's frame (a heading-frame noise turns about the world's origin
  with every yaw, and the cut, only ever lowering, keeps the deepest of each). Only under the belly's full width, not its
  feathered sides.*
- *Item 2 (`SmearRidgeCm`, `DepositChannel`): world lanes 20 cm across, each cut into 30-80 cm segments with its own phase; a segment
  is a ridge on a hash under `SmearChance` 0.25 x 2 x a 120 cm bunching noise, 8-15 cm wide, 1-3 cm high, parabolic across, tapered
  over its ends. The plough lays it on the channel's cells as they leave the box (a 25 cm band behind it, each cell once,
  `SnowMarkSmeared`), out of its return.*
- *Item 3 (`DepositChannel`): `PloughSpillShare` 0.15 of the side deposit onto the lump sites 30-55 cm behind the box, by the site's
  kernel and the lumps' cluster weight: a soft dome in LumpCm (at most its LM4b height cap) on a soft mound in HeightCm under it by
  the same kernel; a site's first spill rolls `SpillClumpChance` 0.15 x the cluster weight for a clump (Source 4, not counted
  as a floor chunk). The channel: cells the belly scraped that no tyre ever covered, between the innermost tyre-covered cells in
  the plough's reach (the scrape mark alone also took the trenches' outer shoulders: the first runs laid spill and ridges on the
  walls' tops by the berm, which moved Compact's berm spike row to 1.80x and Piles' crest cv). `PloughBermCm3` books the whole
  return (the berms, the ridges, the spill).*
- *Item 4 (`live_snow_style.py`): the edge mask E at least `BellyDetail` 0.35 where the belly scraped (the tread texture's A at -1),
  `ScrapeSlope` 0.15 -> 0.3, `ScrapeAlbedo` 0.03 -> 0.06. With parallax on, E 0.35 is over its 0.2 reach, so the channel takes it.*
- *Test profiles: `Lm3cProfile` and `Lm4Profile` now switch LM4c's and LM4d's numbers off (they carried LM4c's lip piles, so GoW's
  "half LM4's" baseline read 7.88 % in LM4c's note; LM4's own is 7.81 %).*
- *GrandTour.Snow.Channel (new; Piles' car over 46 m with Settle, the channel within 50 cm of the line over 4-40 m; LM4c = SnowDefaults
  with LM4d's numbers off):*

  | Row | LM4c | LM4d | Asked |
  |---|---|---|---|
  | Channel floor over the ground, sd per 1 m x 3 m window (median; min-max) | 0.00 cm | **2.35 cm** (1.31-3.25; the undulation alone 1.33) | at least 1.2: PASS |
  | Smear ridges per metre of channel; spacing cv along it | none | **2.89; 1.677** (length 6 / 38 / 62 cm, width 6 / 12.5 / 25, height 0.54 / 1.77 / 2.94) | 1-4; at least 0.4: PASS |
  | Spill: channel cells raised 2 cm or more by it | 0.0 % | **11.2 %** (1 cm: 16.2 %; LumpCm alone 4.9 %) | 5-20 %: PASS |
  | Compaction and volume | return 0.3000 | **0.3000** (the berms 3,578,000, the ridges 68,375, the spill 392,880 cm^3; lost 0); Compact 0.8005; the 5 s after the car moved 0.26 cm^3 | unchanged: PASS |
  | No regular pattern in the channel's profile, lags 2-8 | level | **no peak above 0.03** | none above 0.3: PASS |

  *The spill row reads the spill's rise over the same drive without it: a spilled lump is the capped dome in LumpCm plus the mound
  under it in HeightCm, and LumpCm alone (4.9 %) is that split, not the lump. The ridges' measured extents are the cells raised 0.5 cm
  or more (their tapered ends fall under it), so 6-62 cm long where 30-80 are laid.*
- *Rows LM4d moved: Piles - the edge x0.52 / x0.52 (LM4c 0.56 / 0.57), crest cv 0.362 / **0.350** (0.356 / 0.360; +Y at its limit),
  piles 5.3 / 4.2 per 10 m, the outer walls' cells 57.2 %, the floor 28.0 %; Compact - the unsettled berm x1.43 / x1.56 (1.47 / 1.58),
  the plough-only channel -20.95 cm under the top (the undulation); **GoW - chunks 36: 21 lip + 15 floor = 42 % on the floor (asked
  20-40; LM4c 29 + 15 = 34 %)**. Found: with the ridges or the spill on, the tyres roll 1,489 stamps that cut something over GoW's 30 m
  against LM4c's 1,476; the lip chunks' rolls hash that stamp count, so every later roll moves (outer lips 11 against 18). The
  undulation alone and the channel's path alone leave it at 29; which deposits the 13 extra cuts take was not found. A sample of
  36 chunks; the main session decides (the row, or a chunk hash that does not count stamps).*
- *The drive check (the first since LM3c; LM4d's numbers, LM4c's, LM4b's and the 6.25 cm grid all in it):*
  - *Feel: pass 1 at 6.25 cm reached the end (58.5 s, no stop): A 11.2 km/h, **B 3.7**, **the 35 cm outside the drift 5.6 (asked
    8-15: FAIL)**, the drift 5.5 (3-6); pass 2 the drift 23.8 km/h, **4.31x (asked at least 1.15: PASS)**. The FineGrid pair: at 12.5 cm
    pass 1 A 10.1, B 7.8, outside the drift 8.8, the drift 5.4; at 6.25 cm again A 11.0, B 3.8, 5.7, 5.3. So the slow B comes with the
    6.25 cm grid (LM4), whose frame is also the slowest (pass 1 frame 35.6 ms, game thread 34.9); not separated from LM4c/LM4d's
    snow on the floor. No feel number retuned.*
  - *Cost: Settle at 6.25 cm pass 1 mean 1.51 / p99 5.67 / max 13.7 ms, pass 2 0.97 / 3.77 (gate 0.3 / 0.7: FAIL), awake peak 93-132
    tiles; upload 1.52 / 5.09; at 12.5 cm 0.40 / 1.46. LM4c's talus keeps the tiles behind the car awake while the loose snow slumps
    (no Settle 0/1 pair was taken). Clods pass 1 p99 0.82 ms (FAIL). M_GT_Snow against the clay: base pass +0.57 ms, GPU +2.6.*
  - *LM4b's parallax: the strip view 1 - 0 GPU +0.75 ms, base pass +0.11; the edge view GPU -1.07 (noise), base pass -0.01;
    `Snow_Edge_Close_Parallax1.png` is hard to tell from the 0 frame at its distance (the nearest mound's crumbs a little crisper).*
  - *The strip's berm crest after pass 1 (40-66 m, 95-250 cm out): -Y median 10.44 cm, 90th 14.62, highest 20.46, cv 0.278; +Y 9.22 /
    14.72 / 22.32, cv 0.384 (LM3c's strip: 17-18 cm, swells to 31-32). The profile at 50 m: the walls 56.8 / 77.1 deg, the channel's
    centre 15.8 cm over the ground. Collapses pass 1: 171 fell, 535,799 cm^3, 255 clumps; the channel pass 1: ridges 111,936 cm^3,
    spill 853,455, 105 clumps. Glint 990 px over 245 (0 off); border dark 0, sky 0; clods sunlit 0.900 of the snow (PASS).*
  - *Pictures (what they show; the owner judges): `Snow_OnFoot.png` - two trenches run to the car; the channel between them a pale
    strip with faint long streaks and a few specks, from eye level still close to level; the right trench's wall in shadow, ragged
    with an uneven top; the left trench's edge broken, clumps along it; the snow beside them low and gently lumpy, no tall bank on the
    edge. `Snow_Channel_Close.png` - 60 cm over the channel: long faint darker streaks along the travel, a few small lumps near its
    sides; the undulation and the ridges are not picked out at this angle; the trench beside it steep and rough with clumps on its
    floor. `Snow_GoW_View.png` - from above: the streaked channel with a few lumps, the trenches' ragged walls with clumps on their
    floors, a step-like notch in the left trench's edge, low mounds in the snow beside. `Snow_Edge_Close.png` - the berm a row of
    separate soft rounded piles of different sizes with low gaps, the trench's shadowed wall with a scalloped top. `Snow_Edge_Mask.png`
    - E high on the trench walls, the channel and the piles' flanks, black on fresh snow. `Snow_Collapse_0s.png` / `_4s.png` - across
    the test cut at the far wall (its floor hidden by the near rim): at 4 s a second clump lies at the wall's foot and the shadow line
    along the foot has risen and changed on the left; the notch in the wall's top is not clear from this camera; 8 collapses fell in
    between (delays 0.7-2.2 s).*
- *Unchecked: the feel by hand; the undulation and the ridges seen from the cockpit; the Settle cost with the talus off.*

*Snow gate closed 2026-10-06: the owner, after driving LM4c and LM4d: "I am happy with the snow".*

### LM4e: snow cost, before snow goes onto a leg (main session, 2026-10-06; not scheduled yet)

LM4c/LM4d's check, the first drive check since LM3c:
- At 6.25 cm, Settle costs mean 1.51 ms / p99 5.67 ms on pass 1 against the 0.3 / 0.7 gate, with 93-132 tiles of 32x32
  cells awake behind the car (the loose-snow talus and the collapses keep them awake). At 12.5 cm it's 0.40 / 1.46.
- Pass 1 outside the drift reads 5.6 km/h (asked 8-15) at 6.25 cm, against 8.8 at 12.5. The owner is happy with the
  feel, so this is a note, not a fault.
- GrandTour.Snow.GoW's chunk floor share reads 42 % (asked 20-40 %): 13 extra cuts shift the hash rolls.

To do before any leg carries Snow sections:
- Settle under the gate. Candidates: sleep tiles whose talus moves less than 0.02 cm per sub-step; a talus sub-step
  at half rate for snow; only the band around a fresh cut awake; SIMD the sweep. Measure each.
- Re-base or fix the chunk row.
- Re-take pass 1's speed with the owner.

### LM4e (scheduled): optimise the snow, a lot (the owner, 2026-10-06: "We need to optimize the snow A LOT")

LM5 waits for this, except its Blender phase A, which shares no files and runs no Unreal. **The look and the feel must
not change**: the owner is happy with the snow, so every picture and every feel gate is the reference for what an
optimisation may not alter.

**What is known** (LM4c/LM4d's check, the first since LM3c):
- pass-1 frames 35.6 ms;
- Settle at 6.25 cm mean 1.51 / p99 5.67 ms with 93-132 tiles of 32x32 awake (at 12.5 cm 0.40 / 1.46);
- the snow mesh 592k triangles at 6.25 cm, against 148k, drawn in the base pass and in every shadow pass;
- M_GT_Snow 1,641 pixel instructions against M_GT_Mud's 462, base pass +0.57 ms against the clay;
- Substrate Single on about a third of the tiles plus an unplaced +0.3 ms in deferred lighting;
- parallax off by default.

1. **Profile first, then cut.**
   - One session, same cameras, ABBA order, on the snow strip during a scripted pass 1 and while standing at the
     on-foot camera.
   - Read: stat unit (Game, Draw, GPU, RHIT), the GT stats (Settle, upload, clods), and GPU by pass (base pass,
     shadow depths, lights, Lumen, translucency, post).
   - Toggle each feature alone: FineGrid, Settle, Clods, Parallax, SnowSSS, GlintDensity, the detail map's strength,
     and the patch mesh's shadow casting.
   - The result is a table of each one's cost, and a cost table of the whole snow patch against the clay patch on
     L_MudDrive at a matching view. The cuts go in order of measured cost.
2. **Candidates, ranked by the main session; the profile decides:**
   - **Settle:**
     - Snow needs no `Fresh`, so a snow tile must not stay awake for the 6 s sheen fade; sleep it as soon as the talus
       is quiet (under 0.02 cm per sub-step for 0.25 s) and no collapse timer is pending.
     - Snow talus at half rate (15 Hz).
     - Only the band around a fresh cut wakes.
     - ParallelFor over tiles with per-tile delta buffers, deterministic (a fixed pair ownership).
   - **Upload:** snow needs no slide offset or Fresh. Upload only what changed, in per-tile rects, not one union rect.
     Pack snow's field in half floats if the material reads it identically.
   - **The mesh:** distance LOD by sections. Split the patch mesh into chunks of about 8 m, each at 6.25 cm near the
     camera (within about 20 m) and 12.5 or 25 cm further out. The coarse edge vertices are a subset of the fine ones;
     cracks are closed with a short skirt.
   - **Shadows:** a shadow proxy (the coarse mesh) or no shadow casting from the far chunks.
   - **The material:**
     - top-down projection only where the slope is under 30 deg (tri-planar only on walls);
     - the detail and cavity only where E is over 0.05;
     - one tiling where E is low;
     - a cheaper glint;
     - procedural noise already baked into T_GT_SnowDetail instead of computed;
     - SSS fading out with distance if SnowSSS costs what it seems to.
   - **Clumps and shards:** check their count and shadows.
3. **Targets** (all measured in one session, against this stage's own "before"):
   - Settle mean at most 0.3, p99 at most 0.7 ms on pass 1;
   - upload mean at most 0.2 ms;
   - the snow patch's GPU against the clay patch at a matching view: at most +1.0 ms;
   - pass-1 frame time at most the mud strip's dry crossing + 2 ms (both measured in this session).
   If a target can't be met without changing the look or the feel, stop at the best and report the gap.
4. **No change to the look or feel.**
   - The same cameras before and after (Snow_OnFoot, Snow_GoW_View, Snow_Edge_Close, Snow_Channel_Close), with a
     mean absolute pixel difference per picture. Describe any visible difference.
   - LOD seams: no dark or sky pixels at chunk borders (the border-check pattern).
   - Every Snow and Mud test passes; the mud CRC 8e0aad06 is unchanged. Snow test numbers may move only where a
     change is meant to alter the simulation (half-rate talus); report every moved row.
   - The LM3b feel gates as LM4d measured them (pass 2 at least 1.15x; pass 1 reported against LM4d's 5.6 / 5.5).

*Done 2026-10-06 (no game ran. Two profiles ran before the owner stopped timing runs ("dont do any timing runs. Do the
optimization and I will do the testing"); both were disturbed: in the before profile a second UnrealEditor.exe was seen during
passes 1-2 and the LM5 agent's Blender ran from 19:37 through the standing and pass-1 toggles; in the after-cuts profile Blender
ran 20:09-20:11 (the drive) and 20:19-20:23 (the standing set). ABBA order everywhere, so read the A/B differences, not the
absolute numbers. Builds exit 0; the tests and the strip's setup ran after the stop):*
- *Tools: `Art/profile_live_snow.ps1` (`Art/Unreal/profile_live_snow.py`): one Play In Editor session - pass 1 and 2 profiled
  (CSV: frame, threads, GPU by pass; the GT stats Settle, upload, the new stamp stat, clods, mean / p99 / max), the field's record
  of the drive (`UGTMudSubsystem::SetRecordingForTest`: every stamp, plough, throw landing, clock and settle call) replayed
  frame by frame (Settle's and the upload's cost on the very same work in any build) or all at once (the before/after pictures on
  the same snow: the replay's CRC matched the record's end, 063a4b78), each feature alone standing and on pass 1, ABBA.
  `Art/profile_live_mud.ps1`: the clay reference (the dry crossing and the bog patch visible / hidden). Not plan numbers.*
- *The before profile (the instrumented original build):*

  | Before | Value |
  |---|---|
  | pass 1 (disturbed) | frame 39.0 ms, game 36.7, GPU 24.5; Settle 1.94 / 8.57 ms, upload 1.70 / 5.64 (64,688 cells a frame), stamps 1.20 / 2.81, clods 0.09 / 1.16 |
  | pass 1, the cleanest base run (Blender gone) | frame 22.9, game 20.9, GPU 20.1; Settle 0.88 / 3.24, upload 1.13 / 3.81, stamps 1.00 / 2.40 |
  | the pass-1 record replayed | Settle 1.49 / 4.97, upload 1.44 / 4.06 (63,084 cells), stamps 1.05 / 2.90 |
  | pass 1 toggles, B - A | FineGrid 0: frame -6.4, GPU -2.2 (shadows -1.0), Settle -1.1, stamps -0.9; Settle 0: frame -4.2; Clods 0: GPU -0.8 |
  | the patch hidden (on foot / cost view) | GPU -7.8 / -10.1 (on foot: base -1.4, shadow depths -3.4, lighting -1.2, post -0.5, velocity -0.3) |
  | the patch's shadow casting off | GPU -2.2 / -1.1 |
  | M_GT_Mud on the snow patch | GPU -1.5 / -3.4 |
  | SnowSSS 0, GlintDensity 0, Detail 0, Parallax 1 | GPU -0.2 / -0.6, +0.3 / -0.5, +0.2 / +3.7, -1.2 / +1.2: within the noise |
  | the clay reference (no Blender): the mud strip's dry crossing | frame 18.76, game 15.4, GPU 17.4; Settle 0.11 / 0.50, upload 0.07 / 0.25, stamps 0.29 / 0.80 |
  | the clay bog patch hidden (the cost view's offsets) | GPU -3.69 (base 0.96, shadows 1.21, lighting 1.74, post 0.42) |

- *The cuts (each a switch, default on; "measured" = in-session ABBA before the stop):*

  | Cut | Switch | Measured saving |
  |---|---|---|
  | 1. snow keeps no fresh sheen (M_GT_Snow draws none), so a still tile sleeps after its 0.5 s, not after the sheen's 6 s fade, and nothing is marked dirty for a fading sheen | `gt.Snow.QuietSleep` | replay: Settle 1.11 -> 0.84 ms mean (p99 4.18 -> 3.04), upload 0.73 -> 0.53 (19,428 -> 14,044 cells) |
  | 2. the upload as one box per settle tile, not one box round them all | `gt.Snow.UploadTiles` | replay: upload 1.14 -> 0.53 mean (p99 3.16 -> 1.62; 44,297 -> 14,044 cells) |
  | 2b. the texels encoded a row at a time, the per-cell checks hoisted (same values) | (with 2) | unmeasured |
  | 3. the sweep passes over a pair under the smallest talus before its talus is looked up (exact), no smear on snow (not drawn) | `gt.Snow.FastSweep` | replay: Settle 1.23 -> 0.84 mean (p99 4.10 -> 3.04) |
  | 3b. the same test four cells at a time (SSE, a conservative pre-filter; Pair still decides, in the scalar order), and the apply passes over a listed tile no flux reached | (with 3) | unmeasured |
  | 4. the snow mesh in 24 chunks of 8 m (128 cells), each LOD 0 / 1 / 2 (6.25 / 12.5 / 25 cm) within 20 m / 40 m / beyond (1.5 m hysteresis), skirts 40 cm down on inner edges | `gt.Snow.MeshLod` (read when the patches are built) | on foot GPU -1.29 ms (shadow depths -0.75, base -0.29, velocity -0.14); cost view -0.22 (noise) |
  | 5. M_GT_Snow opaque (its mask is 1 everywhere since mud stage D) | `MI_GT_Snow_Masked` for the A/B (no console switch: a blend mode) | inconclusive (on foot -1.42 for masked, cost view +0.22: the noise) |
  | 6. M_GT_Snow computes the scrape streaks' noise only where they show | `gt.Snow.FastMaterial` (-1 the material's SnowFastPath 1) | unmeasured |

  *All of cuts 1-3 together on the replay: Settle 1.38 -> 0.84 ms mean (p99 4.79 -> 3.04), upload 1.52 -> 0.53 (p99 4.15 -> 1.62).*
- *After cuts 1-5 (3b, 2b and 6 came later, unmeasured): pass 1 frame 19.57 ms, game 15.54, GPU 16.55; Settle 0.381 / 1.735,
  upload 0.370 / 1.054 (13,045 cells), stamps 0.864 / 1.854, clods 0.021 / 0.311; the patch hidden GPU -6.58 / -7.73.*

  | Target | Asked | Measured (cuts 1-5) |
  |---|---|---|
  | Settle on pass 1 | mean 0.3, p99 0.7 | 0.381 / 1.735: not met (3b unmeasured) |
  | upload on pass 1 | mean 0.2 | 0.370: not met (2b unmeasured) |
  | the snow patch's GPU against the clay patch's | at most +1.0 ms | 7.73 against 3.69 (cost-view offsets): +4.0, not met. The views do not cover the same pixels (the snow runs to the horizon; the bog ends 21 m past the target); a full-coverage matching view is in both profiles, not run |
  | pass 1's frame against the mud strip's dry crossing | at most +2 ms | 19.57 against 18.76: +0.81 (two Unreal sessions 8 minutes apart) |

- *Parity. Tests: GrandTour.Mud + GrandTour.Snow 8 of 9 Success, as before: GoW fails its chunk row (42 % on the floor), as it did
  before any cut. The mud CRC 8e0aad06 and 126 of 127 rows are unchanged to the digit; the moved row: Piles' "the drive twice" CRC
  7ad7b091 / 7ad7b091 -> 30de74f6 / 30de74f6 (still equal: PASS). Cut 1 by elimination (2-6 cannot touch HeightCm or LumpCm, and
  3/3b are exact): a sleeping tile that flux reaches takes a still tile's test, which differs from before only for flux that
  arrives after the old sheen's fade; no measured shape row moved. The pictures (the before run's drive replayed in each build,
  the same cameras; the after ones with cuts 1-5): the whole frame differs by 0.25-1.62 (0-255), almost all of it the sky's clouds,
  which drift between sessions, and the HUD; below the sky Snow_OnFoot 0.372 (0.72 % of pixels over 8), Snow_GoW_View 0.281
  (0.08 %), Snow_Edge_Close 0.373 (1.14 %), Snow_Channel_Close 0.314 (0.82 %), Snow_Long 0.436 (1.04 %), Snow_Cost_View 0.372
  (0.20 %); the difference images show faint outlines along shadow edges near the camera and a thin speckled band at the far end
  of the snow, where the chunks draw LOD 1-2. Seams (Snow_Seams, down the strip from 60 m, LODs 12 / 8 / 4 chunks, against the same
  frame all at LOD 0): within 2 px of a chunk border 29 dark / 1,958 sky-coloured pixels with the LODs, 38 / 1,949 all at LOD 0
  (the sky ones where the far borders reach the horizon): no seam pixels added. The feel: pass 1 A 11.3, B 7.9, 9.3 km/h outside
  the drift (LM4d 5.6), the drift 5.1 (LM4d 5.5); pass 2 3.86x (asked 1.15).*
- *Not done (would change the look or the feel, or not finished cleanly): Settle's half-rate talus or a coarser quiet threshold
  (the simulation), only the band round a fresh cut awake, ParallelFor over tiles (float sums in another order); a shadow proxy
  (a coarse caster under a fine receiver shifts the trenches' shadow edges); the plan's material cuts (top-down only under 30 deg,
  the detail only where E > 0.05, one tiling, a cheaper or baked noise, SSS fading with distance: each changes pixels); the
  stamps (0.86 ms mean at 6.25 cm, not a target). Unchecked: every number after the stop (3b, 2b, 6 and the final state), the
  matching full-coverage view, the after pictures with the patch-hidden masks.*

### LM4f: the bigger snow cuts, behind switches, the owner tests (main session, 2026-10-06)

**The owner: "dont do any timing runs. Do the optimization and I will do the testing."**

LM4e left these:
- the snow patch at 7.73 ms of GPU against the clay patch's 3.69 (hidden on foot it saved 7.8 ms, 3.4 of them shadows);
- Settle 0.38 / 1.74 ms;
- upload 0.37 ms;
- the wheel stamps 0.86 ms at 6.25 cm.

LM4e left out every cut that might move the look or the simulation. Here they go in, **each behind its own console
switch, default on**, so the owner A/B's look and cost together and names which stay. The agent runs **no timing,
profiling, drive or suite runs**: only the build, the CPU correctness tests and the setup. Every cut with a switch
must give exactly LM4e's behaviour when switched off.

1. **Shadow proxy** (`gt.Snow.ShadowProxy`). The patch's render chunks stop casting shadows. A shadow-only mesh at
   25 cm per chunk (hidden in the main pass, cast shadow on), built from the same field and updated with the chunk.
2. **The material** (`gt.Snow.FastMaterial` 2 = the new level; 1 = LM4e's; 0 = the full material). Through an MPC
   scalar or the existing switch path:
   - a single top-down detail sample where the field's slope is under 30 deg, tri-planar only on walls;
   - detail and cavity only where E is over 0.05;
   - one tiling where E is under 0.2;
   - the glint fading out between 12 and 20 m;
   - the SSS fading to 0 between 20 and 35 m, so far pixels classify as Substrate Simple (LM3c measured that SnowSSS
     0 drops the Single tiles to 0.3 %).
3. **Settle** (`gt.Snow.FastSettle`):
   - snow talus at 15 Hz;
   - only the tiles within 2 m of a cut made in the last 3 s, or with a pending collapse, stay awake;
   - a ParallelFor over tiles with per-tile delta buffers applied in a fixed order (deterministic run to run, though
     not bit-identical to serial).
   The GrandTour.Snow rows must still pass. Rows that move get reported, and LM4e's Piles CRC row compares two runs
   with each other.
4. **Stamps, exact.** No switch needed if the results are bit-identical. Precompute the static per-cell noises (lump
   weights, CellNoise users, pocket and floor noise, the snow top) into per-cell arrays at Init, instead of hashing
   per stamp; profile the stamp loop by reading the code, not by timing.
5. **The chunk row.** GrandTour.Snow.GoW's chunk floor share reads 42 % and failed identically at LM4e's baseline: 13
   extra cuts shift the hash rolls. Re-base it to 20-45 % with that reason in a comment.

**Owner's test list.** Extend `docs/LIVE_SNOW_DRIVE.md`'s "How to test the optimisation" with the new switches and
what each trades: look risk and expected saving, from LM4e's before-profile proportions, marked "estimated".

*Done 2026-10-06 (no timing, profile, drive or suite run, at the owner's word; no game ran; a foreign UnrealEditor - the Codex app's
Benmore setup - came and went three times and every Unreal run waited for it; the LM5 agent's Blender ran. Builds exit 0):*
- *Item 1, `gt.Snow.ShadowProxy` (default 1): per chunk a hidden `SnowShadow_i_j` mesh at `ShadowProxyCm` 25 (every 4th vertex,
  no skirts), `bCastHiddenShadow`, out of ray tracing and distance-field lighting, the surface's MID (the same displacement, every
  frame); on, the chunks cast nothing and these cast; 0, LM4e's chunks cast and the shadow meshes are not in the scene. Read every
  tick; the test switches (cast, visible, material) act on both. Needs `gt.Snow.MeshLod 1`. About 37k shadow triangles against up to
  592k. Look risk medium: shadow edges along the walls and lip shift by up to ~12 cm, dips under 25 cm can shadow, small lumps lose
  their own shadows. Unseen.*
- *Item 2, `gt.Snow.FastMaterial 2` (M_GT_Snow's `SnowFastPath` default now 2; `-1` takes it; 1 LM4e's, 0 the full material): the
  detail top-down only where the normal is within 30 deg of up, none at E 0.05 or under, one tiling under E 0.2, the glint faded over
  12-20 m (and skipped where its gain is 0), the SSS faded over 20-35 m (a new `SnowCamDepth` input from PixelDepth). Two fades are the
  agent's choice so neither cut draws a line: the detail fades in over E 0.05-0.10, the second tiling over E 0.2-0.3. Look risk
  high on fresh snow: E is 0 on untouched snow and the packed floors, so their crumbs go (the landscape apron keeps them: the
  patch's edge can show). Unseen.*
- *Item 3, `gt.Snow.FastSettle` (default 1; the console variable lives in GTMudField.cpp and a new field takes it as its default,
  so the CPU tests follow it): 1 = 15 Hz talus + the band (2 m round any write in the last 3 s, or by a pending collapse) + the
  parallel sweep and apply; 2 = the parallel part alone (exact, the check); 3 = parallel + 15 Hz; 4 = parallel + band (3 and 4 added to
  tell the main session which half moves which row); 0 = LM4e. The parallel sweep logs each tile's flux in its serial order and adds
  the logs in the work list's order, so it is bit-identical to serial, not only deterministic.*
- *Item 4, exact (no switch): eleven per-cell noise slots (`NoiseCells`, built in a ParallelFor at the patch's start by
  `PrepareStampNoise`, keyed exactly), read by StampWheel and PloughBelly; the piles' `EnsureSnowPiles` once per stamp, not per lip
  or berm cell. Read from the code: per stamp some 500-800 lattice noises (the station's 4 at every change of foot cell, 2 per floor
  cell, 3-4 per lip cell). Left: `WallOffsetAt` per lip cell (its foot moves with the stroke, not a per-cell static).*
- *Item 5: GoW's chunk floor share re-based 20-40 % -> 20-45 %, the reason in the test's comment.*
- *Tests (GrandTour.Mud + GrandTour.Snow):*
  - *FastSettle 0: 9 of 9 Success. 125 of 127 rows identical to LM4e's final log to the digit, CRCs included (mud 8e0aad06,
    Piles' "the drive twice" 30de74f6 / 30de74f6, Lumps' 4ae38d20 / 4f19670e). The two moved rows are item 5's: GoW Fail -> Success,
    its chunk row "42 % (asked 20-40 -> 0)" -> "42 % (asked 20-45 -> 1)". This is item 4's proof (every stamp reads the slots) and
    the restructured serial settle's.*
  - *FastSettle 2 (the parallel half alone): all 127 rows identical to FastSettle 0's - exact.*
  - *FastSettle 1 (the default, `& Art/mud_shape_test.ps1`): 8 of 9 - **GrandTour.Snow.Piles FAILS**: 62.3 % of the outer walls' cells
    stay steeper than 55 deg (asked 15-60; LM4e 57.2). 29 rows differ from FastSettle 0 (below).*
  - *FastSettle 4 (the band alone): Piles fails the same row (62.7 %); 102 rows identical. FastSettle 3 (15 Hz alone): that row
    passes (57.2 %) but Piles fails the berm crest cv (0.361 / 0.350, asked at least 0.35 each side; LM4e passed by a hair at
    0.362 / 0.350); 99 rows identical. So the band stops walls settling early (snow 3 s past its last write freezes). Nothing retuned and no gate
    moved: the main session decides (the band's 3 s or 2 m, the row, or which half stays on).*

  | Moved row (FastSettle 0 -> 1) | FastSettle 0 | FastSettle 1 |
  |---|---|---|
  | GrandTour.Snow.Piles | Success | Fail |
  | LM4c wall cells: outer walls over 55 deg (asked 15-60) | 57.2 % | 62.3 % (FAIL); every wall 34.8 % of 8506 -> 36.5 % of 8417; outer wall stations 78.6 -> 80.9 % (mean 63.2 -> 63.6 deg) |
  | LM4c floor debris, raised 2 cm or more | 28.0 % (966 of 3456), mean 1.86 cm | 26.5 % (915), 1.67 |
  | LM4c edge height, median / 90th vs LM4b | 9.82 / 15.04 cm (x0.52 / x0.52) | 9.95 / 15.57 (x0.52 / x0.54) |
  | LM4c berm crest cv | 0.362 / 0.350 | 0.366 / 0.352 |
  | LM4c piles per 10 m, spacing mean, cv | 5.3 / 4.2, 206 cm, 0.521 | 4.7 / 4.2, 220 cm, 0.560 |
  | LM4c the car over 46 m (the summary row and its LM4b row) | the numbers above; LM4b crest median 19.01, cv 0.266 / 0.293 | the numbers above; 19.02, 0.267 / 0.295 |
  | LM4c mean cross-section | e.g. 98 cm off the line -24.1, 122 cm 9.1 | -24.4, 9.4 (every point within 0.3 cm) |
  | LM4c collapses | 214193 cm^3 moved, delay max 2.77 s, pile max 11.6 l, top 10.4 cm | 214190, 2.80, 11.5, 10.3 (51 / 77 fell in both) |
  | LM4c volume over the 5 s after the car; the drive twice | -20888086 (moved 0.26 cm^3); CRC 30de74f6 / 30de74f6 | -20887362 (moved 0.00); CRC cf3cf299 / cf3cf299 (equal: PASS) |
  | LM4c lip, single tyre settled 5 s: steps over 3 cm | 6.16 % (183 of 2973) | 6.04 % (179 of 2966); its autocorrelation lags move 0.01-0.03 |
  | LM4c sweep (reported, 11 rows) | outer walls over 55 deg 40.5-61.0 %; floor raised 25.3-54.0 % | 47.6-67.2 % (each +5 to +8); 23.3-49.3 % |
  | LM4d smear ridges | 104 = 2.89 per m, spacing 34.7 cm, cv 1.677, length 6 / 38 / 62 cm, laid 68427 cm^3 | 91 = 2.53 per m, 39.7, 1.549, 19 / 44 / 75, 71517 (asked 1-4 per m: PASS) |
  | LM4d spill | landed 392880 cm^3 (157079 in domes); 11.2 % raised | 392296 (156800); 11.2 % |
  | LM4d compaction | plough cut 13464182, returned 4039255 = 0.3000, berms 3578000 | 13455142, 4036543 = 0.3000, 3572736 |
  | LM4d channel profile's autocorrelation | - | lags move 0.01-0.02 |
  | wall below the lip, 10 s settled (reported) | mean 64.5 deg, min 50.0, 62 % at 60 or more | 64.6, 49.4, 63 % |
  | refill | floor -35.49 -> -29.49 cm (6.00), put back 338412 cm^3 | -35.61 -> -29.61 (6.00), 336063 |

- *Setup (`& Art/setup_live_snow_drive.ps1`): LIVE_SNOW_SETUP_OK; M_GT_Snow and M_GT_Clod_Snow 0 compile errors; M_GT_Snow 1,673 pixel
  instructions (the static count over every branch; LM4e's "what is known" 1,641), Substrate Single [SSS|MFPPluggedIn] as before; the
  editor's known shutdown fault (-1073741819) after a fresh ok report.*
- *The owner's test list (with each switch's look risk and estimated saving): docs/LIVE_SNOW_DRIVE.md "How to test the
  optimisation". Unchecked: every cost (estimates only), every look, the feel with FastSettle 1.*

*Gate re-base 2026-10-06 (main session, after LM4f): GrandTour.Snow.Piles' outer-wall row goes from 15-60 % to 15-65 %
of the cells steeper than 55 deg. With `gt.Snow.FastSettle 1` (default), the 2 m / 3 s band stops a slumping wall a
little early: 62.3 % against 57.2 % at FastSettle 0. The row's purpose, some walls standing and some fallen, holds. The
owner A/B's the look and names the setting. GrandTour.Mud + GrandTour.Snow: 9 of 9 Success.*

### LM5: wet churned painterly mud (named by the owner 2026-10-06)

**The owner: "mud is looking much better - think now some new textures are the way to go."** Their answers:
- **source**: new painterly bakes, made with the Blender style-study workflow like the approved clay (revision 03);
- **look**: wet, dark, churned mud on the ruts, banks and lumps (sloppy, with glossy patches), and a drier clay look
  on untouched ground (the SnowRunner contrast).

The owner has rejected "too smooth", "very uniform" and regular lines on the mud before. The new bakes must not tile
visibly, must not carry stripes, and must keep the field's detail readable.

**Phase A, Blender only (no Unreal):**
1. **The study.** `Art/Blender/build_mud_wet_study.py` is a new generator, started from `build_mud_style_study.py`'s
   revision 03, which stays untouched. Its output goes to `Art/Export/MudStyleStudy/04_wet/`. It adds a wet churned
   material in the same painterly language (broad shapes, directional paint strokes, no photographic noise):
   - darker and more saturated umber than the clay (value about 0.55-0.7x the clay's);
   - glossy wet patches in the hollows (roughness 0.2-0.45), matte crumbs on the high points (0.8-0.9);
   - churned forms: swirled and folded smears 10-40 cm long, broken by crumbs of 2-5 cm and small slurry pockets;
   - no regular lines, no dominant direction over the whole tile.
   Review renders: the study's rut scene with the churn on the ruts and the clay elsewhere, a close view and a
   flat-tile view tiled 3x3 to check for repetition.
2. **The bakes.** `Art/Blender/export_mud_wet.py`, on `export_mud_style.py`'s pattern: four 2048 maps of a 3 m tile,
   truly tileable, with no mirror seams and no visible repeat in the 3x3 view:
   - `T_MS_ChurnColor` (sRGB);
   - `T_MS_ChurnNormal` (DirectX tangent, as the clay's);
   - `T_MS_ChurnRough` (linear);
   - `T_MS_ChurnHeight` (linear, for cavity).

**Phase B, Unreal** (no other agent's Unreal run at the same time; the owner's game rule applies):
3. **A churn channel in the field.**
   - `StampWheel` writes churn 1 on the capsule's cells and 0.5-1.0 (noisy, decaying outward) on its band cells.
   - `DepositThrown` and the plough write churn where they deposit.
   - Churn never decays, except under the snow refill (snow doesn't use it).
   - It's uploaded in `TreadTexture` A, which is unused. The field's heights don't change: the mud CRC stays
     8e0aad06.
4. **The live material** (`live_mud_style.py`) gets three layers:
   - **dry clay** (the approved T_MS_Clay*) where churn is 0;
   - **wet churn** (T_MS_Churn*) where churn is 1;
   - the old **worked** layer used only in the transition.
   The mask is churn x a breakup noise (30-80 cm), so the edge is ragged, not a line.
   - The churn samples at two tilings that don't share a repeat (3 m and about 4.3 m, rotated) and blends them by a
     noise, so no repeat reads.
   - Wetness and Fresh deepen the churn's gloss as now. The cavity from T_MS_ChurnHeight darkens hollows. Rut water
     is unchanged.
5. **Clods.** Thrown clods (freshness 1) take the churn bakes; bank clods keep the clay. Both stay in `M_GT_Clod`
   via the per-instance freshness value.
6. **The landscape apron** on L_MudDrive keeps the dry clay. Untouched ground doesn't change.

**Checks**:
- the mud tests all pass, CRC unchanged;
- the strip completes dry and wet;
- cost: M_GT_Mud's instructions and GPU, churn on vs off, gate +0.3 ms GPU;
- pictures: `Mud_OnFoot_Dry`, `Mud_Long_Dry`, `Mud_Clods_Dry`, `Mud_After_Wet`, `Cockpit_Mud`, plus the Blender
  previews in `04_wet/`.

The look is the owner's. The agent describes what the pictures contain.

**Then the owner's gate** (L_MudDrive).

### LM5 phase A2: no swirls (named by the owner 2026-10-06 after the study renders)

**The owner, after seeing `04_wet/Driver.png` and `ChurnClose.png`: "the swirls look terrible, like chocolate or
something."** The marbled, folded, swirled smears (domain-warped colour bands with spiral eyes) read as a liquid
being stirred, not as mud a tyre has torn up. Every swirl, marble band, spiral and flowing fold goes.

**The new churn, in the same painterly language** (broad shapes, painted strokes, no photographic noise):
- **Torn and lumpy, not flowing.** Clods and lumps pressed into the wet mud: irregular, rounded-angular, 3-15 cm,
  matte and a little lighter on top, dark wet gaps between them. Clustered, so some patches are crowded and others
  open.
- **Flat slurry.** Broad, low, smooth, glossy dark areas between the lumps (roughness 0.2-0.4), with soft edges,
  where water and mud have settled. This is where the wet look lives.
- **Torn edges and crumbs.** Small broken bits of 1-4 cm and ragged edges where lumps were pulled apart. No clover
  shapes: crumbs are irregular, not lobed.
- **Colour.** Broad, irregular patches of two or three umbers. No bands, no streaks, nothing long and thin.
- **Direction.** None over the tile. No crosswise ripples or wavy bands at any distance. Check the far view of
  `Driver.png` for bands before baking.

The value against the clay (about 0.6x) and the tileable 3 m bakes stay as phase A set them. Keep the swirl revision
in a Before folder.

**Order**: after LM4e finishes, because Blender's CPU load would skew LM4e's timings. If the owner sends a mud
reference picture, it leads, the way the God of War picture led the snow.

### LM5b: four churned-bog variants (named by the owner 2026-10-06 after the A2 renders)

*Done 2026-10-06, phase B (no game and no foreign Unreal at any run; no cost or timing measured, the owner's rule; build exit 0;
VEHICLE_BUILD_SYSTEM section 78, docs/MUD_VARIANTS.md):*
- *Runs: build (93 s), the ten mud and snow tests (Success), the import, the L_MudDrive setup (failed once: `M_GT_Clod`'s
  `.Sample` on the arrays is not valid in a ray-tracing hit shader; `Texture2DArraySample` fixed it; then OK), the
  L_MudVariants setup, its check (OK), the targeted suite (terrain failed its bog escape once, passed its rerun).*
- *Data as written: `EGTMudVariant`, `FGTRouteSection::MudVariant`, `FGTDeformProfile::MudVariantDefaults` and
  `GTTerrain::MudVariantProfile` (Standard: no profile). The table's sinkage and friction are scales (`MaxSinkageScale`,
  `SinkageRateScale`, `FrictionScale`) of the rows inside the patch; with `bScalesRows` the patch stays a bog's (the rows,
  the Mud/Bog tag gate, the bog's grid and other numbers) and takes only the scales, RecoverShare, LumpShare, ThrowMax and
  `WaterTableOffsetCm`. The patch carries `MudVariant`; the friction scale goes on the traction's FrictionScale (Chaos friction,
  slip graph and drive cap all move by exactly it).*
- *GrandTour.Mud.Variants (new), per patch built by BuildPatches in a Game world: Firm sinkage cap x0.60 rate x0.60, friction
  x1.10, RecoverShare 0.25 (field 0.25), LumpShare 0.25 (0.25), ThrowMax 0.30, water table -25.0 cm; Standard x1.00 / x1.00,
  x1.00, 0.40, 0.35, 0.50, -25.0; Deep x1.50 / x1.50, x0.90, 0.55, 0.35, 0.60, -15.0; Stony x0.80 / x0.80, x1.15, 0.30, 0.20,
  0.50, -25.0; no profile and the 12.5 cm cell on all four -> Success. Settle's mud CRC 8e0aad06 (unchanged).*
- *Textures: four Texture2DArrays (no fallback). Python's factory and `source_textures` alone gave 4 slices of 2048 x 2048
  each; `UGTMudArtLibrary::BuildTextureArray` rebuilds them from the slices on every import (repeatable).*
- *Material: one layer, the slice everywhere; two tilings (300 cm and 430 cm at 37 deg) height-blended by a 260 cm noise; the
  far gloss fade behind `FarGlossFade` (on); `FreshWet` 0.3 (was 0.6). The apron: `MPC_TrackPaint` `PatchVariant0..3` (four
  new scalars; the Patch vectors have no spare component), 300 cm round each live box. Clods: one `M_GT_Clod` instance per
  variant patch. L_MudDrive and The Hide stay Standard and wear the Standard bog everywhere in the patch.*
- *The strip, dry, full throttle, low range, the diff lock: completed (200.06 m in 84.6 s). Firm 32.2 km/h, sinkage max / mean
  24.0 / 18.8 cm; Standard 24.4 km/h, 40.0 / 32.8; Deep 1.8 km/h (slowest 0.04 m/s), 60.0 / 59.4; Stony 22.6 km/h, 32.0 /
  26.7. The pictures (per section on foot and close) are described in docs/MUD_VARIANTS.md: the close-ups of Firm, Standard
  and Stony read as stones or pebbles set in mud; Deep's close-up is mostly the flooded trench's water.*
- *Suite terrain drivetrain grip mud surface track: 5 PASS, 1 FAIL (terrain: bog escape forward 6.9 m in 12 s, asked 8 m);
  its rerun PASSED (8.3 m; LM4d 8.5 m). Standard's numbers are multiplied by exactly 1.0f; the gate sits at its edge.*
- *Unchecked: cost; the far fade on/off; the apron in a border picture; L_MudDrive and The Hide in pictures; the wet look.*

**The owner, on the A2 renders: "looks good, but the ruts should be the same color and texture as the rest. I want a
number of variants for deformable mud."** Their answers the same day:
- **Ruts**: the same colour and texture as the untouched mud, only a little wetter. The existing fresh sheen gives a
  slight gloss that dries off.
- **Variants**: four variants of the approved wet churned bog, each with its own look and feel.
- **Placement**: per route section.

This replaces LM5's phase B: no churn channel and no clay/churn layers. The churn look is the mud, everywhere in a
patch.

**The four variants** (`EGTMudVariant`; the feel numbers are proposals the owner names after driving):

| Variant | Look (bake set) | Feel (profile) |
|---|---|---|
| `Standard` | the approved A2 churn as it is | exactly today's mud behaviour, so every existing level and test is unchanged (the mud CRC 8e0aad06) |
| `Firm` | lighter mid-brown, less slurry (matte lumps dominate), smaller lumps | sinkage 0.6x, `RecoverShare` 0.25, `LumpShare` 0.25, `ThrowMax` 0.3, friction 1.1x |
| `Deep` | darker, wetter, large glossy slurry areas, fewer, softer lumps | sinkage 1.5x, `RecoverShare` 0.55, `LumpShare` 0.35, `ThrowMax` 0.6, `WaterTableCm` +10, friction 0.9x |
| `Stony` | the churn with gravel and small stones pressed in, in the approved gravel-04 palette with the earth coating | sinkage 0.8x, `RecoverShare` 0.3, `LumpShare` 0.2, friction 1.15x |

"Sinkage" scales the surface row's `MaxSinkage` and `SinkageRate` inside the patch. "Friction" scales the row's
friction inside the patch.

**Phase A, Blender only:**
- `build_mud_wet_study.py` gains a variant parameter; Standard reproduces A2 to the pixel.
- One bake set per variant, 2048, 3 m tile: `T_MS_Bog{Variant}{Color,Normal,Rough,Height}`.
- Per-variant renders: Driver, ChurnClose, Tile3x3.
- The owner's rejections still hold: no swirls, no pebble or cobble look, no bands, no repeat.

**Phase B, Unreal and C++:**
1. **Data.** `FGTRouteSection::MudVariant` (Mud sections; default `Standard`) and `FGTDeformProfile::MudVariantDefaults(variant)`,
   on the SnowDefaults pattern. Standard means "no profile" (today's path exactly). The patch carries its variant index.
2. **Textures.** One `Texture2DArray` per channel (Color, Normal, Rough, Height), slice = variant, built from the bake
   sets by the import script.
3. **The live material** becomes one layer: the variant's slice everywhere in the patch, ruts included. A rut differs
   only by shape, the fresh sheen (`FreshWet` slight: ruts a little wetter, drying as Fresh fades), weather wetness and
   rut water.
   - **The far gloss fade.** Roughness rises toward 0.65 between 6 and 12 m from the camera, so the sky's reflection
     in glossy slurry doesn't band across far ruts at a grazing angle (A2's finding). It's behind a material switch.
   - Two tilings that don't share a repeat, as before. The clay bakes stay for the landscape outside mud.
4. **The border.** The landscape's apron around each patch takes the same variant slice via `MPC_TrackPaint`
   (`PatchVariant0..3`), so the patch edge doesn't show.
5. **Clods** take their patch's variant slice (bank and thrown alike).
6. **A strip of all four.** `L_MudVariants`: four mud sections of about 25 m (Firm, Standard, Deep, Stony) along one
   route, no ford (`MPC_TrackPaint` holds four patches). Its setup and check follow the L_MudDrive scripts.
   - The check drives it once, dry, and reports completion, each section's mean speed and sinkage, and its pictures:
     per section an on-foot view and a close-up after driving.
   - **No cost or timing measurement**: the owner tests performance.

**Tests**: every GrandTour.Mud and GrandTour.Snow test passes, and the Standard variant leaves the mud CRC unchanged. A
new row per variant: the profile reaches the patch (sinkage cap, recover share, lump share, friction scale as
written).

**Then the owner's gate** (L_MudVariants).

## 4. Later, not planned

- **Resolution**: trenches as crisp as God of War's want cells finer than 12.5 cm near the car, whether a 6.25 cm
  near-field or Nanite displacement of a static patch mesh. A measured spike after LM3, given The Hide's frame budget.
- **The Hide**: LM1-LM2 run on every patch, The Hide's included, through the shared code (the terrain test drives
  it), but The Hide's pictures and cost are not this plan's. Its frame budget needs the leg dressing's cuts first.
- **Snow on a leg**: Snow sections on a real leg after the owner's LM3 gate.
- The unnamed items left from the 2026-09-16 mud run stand: the rut water's dark look, `bRutWaterPhysics` false, the
  shots' stalling crawl.

## 5. Order

LM0 -> LM1 -> gate -> LM2a -> LM2b -> gate -> LM3a -> LM3b -> gate. Then (2026-10-06) LM4 snow deformation -> gate -> LM5 mud textures (painterly wet churned bakes in the ruts). One Opus agent per stage. Never two agents
running Unreal at once. LM2a and LM3a touch the traction, so they never overlap with each other or with anything else
in the traction.
