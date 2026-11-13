# Riverbeds: sinking that shows, water that fills its basin, a winch that lets go (plan for implementing agents)

Written 2026-09-22 after the owner walked and drove L_Proving (two screenshots). Five stages, S0 to S4, one Opus 5.5
session each, in that order, each gated where its gate says so. Section 2 is the orchestrator's mechanism claims as
verified against the code on 2026-09-22 (read only; no build, no test ran: FarCry6.exe was up). Written so an agent can
start from this file and the read list without the conversation that produced it.

**All five stages built 2026-09-22/23: VEHICLE_BUILD_SYSTEM sections 50-54.**

## 0. Rules for the agent (the owner's, all of them hold)

- **Never model car bodies or characters.** Textures are sourced (CC0), never painted or generated.
- **Never say how something looks or feels from code.** Numbers come from tests and pictures (a pixel sampler,
  `Art/tools/*.ps1`, on boxes the runner logs), or the thing is "unchecked". A dark patch is not a hole until the
  histogram says so. Compare like with like: a ford run with a ford run, a bog run with a bog run.
- **Movement is the owner's.** No tuned number is touched: the rows in `Art/Unreal/setup_m1_track.py`, the traction's
  constants, the mud's shape numbers, the water's (WaterDragPerMetre 2.4, DragCd 1.0, HeadDropCm 30), the intake 0.85 m,
  the camera. The numbers this plan marks "proposed" are starting points the stage agent sets, measures and reports;
  the owner names them after driving. A stage that moves a movement number it did not set reports it before/after.
- **Harvesting is a placeholder**: never build on its nodes, tools or yields.
- **The machine rule.** Before any build or run: `tasklist | grep -i -E "UnrealEditor|GrandTour|FarCry"`. A game on the
  GPU voids every timing number (frame, `GTWATERSTATS`, crossing times on rendered runs): say so next to the number. A
  game on the CPU is the owner's and is left alone: no run until it is gone. One Unreal process at a time.
- **Tools, one call each**: `bash Art/build.sh` (check its stdout line `== build exit 0`, not the log; close the
  editor first); `bash Art/suite.sh [names]` (24 tests; `terrain` about 260 s, `water` about 290 s; the whole suite
  about 20 min, in the background); the setups only when their assets change, in this order: `Art/setup_m6_textures.bat`,
  `Art/setup_m6_water.bat`, `Art/setup_m6_mud.bat`, `Art/setup_m6_hide.bat`, then `Art/setup_m6_proving.bat` (section
  49 rebuilt hide then proving); pictures: `Art/ford_shots.bat` (L_Leg03, `-GTShotsFrom=22`, hide_22-31) and
  `Art/bog_shots.bat` (`-GTShotsFrom=12`), both into `Saved/Logs/hide_shots.log`; samplers `sample_ford.ps1`,
  `sample_border.ps1`, `sample_rut_low.ps1`. **The ford diag** (section 49): `-GTFordDiag` (`FGTFordDiagRunner`,
  `Source/GrandTour/Core/GTFordDiagRunner.cpp`, with `-GTNoLoad`) opens L_Proving headless, surveys forda/fordb
  (`GTFORDPROF` profiles, surface changes, rows, rocks) and drives a dry pad and each ford at full throttle (base,
  `gt.Water.Hull 0`, `gt.Water.Buoyancy 0`, forda repeat); `Art/ford_diag.bat` runs it (2 min 20 s) into
  `Saved/Logs/ford_diag.log`; `python Art/tools/ford_diag.py [log] [--rows DIR]` prints crossing, minimum speed, force
  budget, slip, exit-bank dynamics, sinkage and radius; the logger is the cvar **`gt.Water.Diag`** (1: a `GTWATERDIAG`
  line every 0.1 s, 2: every tick; the runner sets 2 within 6 m of a waterline). It gates nothing and is not in the
  suite. **L_Proving's picture mode** (since S2, section 52): `Art/proving_shots.bat [step]` into
  `Saved/Logs/proving_shots.log` and `Saved/Screenshots/Proving`, sampler `sample_wheels.ps1`; a picture there is a new
  step after step 1 (S3 and S4 say which). Never chain per-test
  Bash calls; run `/Game/` map arguments from a script file. Write every file before the first build. Keep heredocs tiny.
- **Test policy ("cut 1")**: per stage `bash Art/suite.sh terrain` plus the touched modules' tests (the traction:
  `drivetrain grip mud surface track`; the winch: `winch`; the water: `water`; L_Proving: `proving`; the runner only:
  nothing more). The full suite once at the end of a session, in the background, by its last agent.
- **Known flakes**: body and winch (rerun once); terrain step 11's ruts gate (marginal on a chaotic crawl; stays a
  flake, never tuned); the water test's bow settle gate until S0.
- **Docs per stage**: a new section at the end of `docs/VEHICLE_BUILD_SYSTEM.md` (S0 50, S1 51, S2 52, S3 53, S4 54),
  the devlog `docs/devlog/<date>.md`, a RIVERBED line in `docs/BACKLOG.md`, and this file's stage note (italic under
  the stage heading). Numbers before and after, what was seen (a look is a look), what is unchecked.
- **Report format** (under 250 words): tests run and their result lines; gate numbers asked/read; pictures and their
  sampler numbers; the stage's own numbers as set; unchecked; files touched.
- **Read list for a fresh agent** (by `grep -n` and sed ranges only): this file; `docs/VEHICLE_BUILD_SYSTEM.md`
  section 49 (the ford bed fix and the diag, about 160 lines) and the sections the stage lists; the file:line
  references in section 2 for the stage's mechanism. Nothing else until a change needs it. Git is not initialised.

## 1. The owner's four reports and the look (2026-09-22)

1. "The wheels clip into the ground in riverbeds. We need to find a better way of blending deformable surfaces and
   non-deformable surfaces."
2. "The water only covers a square of the pond."
3. "Once the player hooks the winch to a pole, there isn't a way to detach it."
4. "Deformable river beds could be cool, is that possible?"

The orchestrator's look at the two pictures (a look, not a measurement). Picture 1, on foot beside the estate car on
flat pale ground next to a water body: every visible wheel sits deep in undeformed ground, the front-left to about the
hub, the rears past the tyre's lower third, no rut or bank around them. Picture 2: a rectangular pale-blue water sheet
with a straight far edge and a foam line on the near edge, inside a larger pale depression whose floor continues past
the sheet's straight edges at what looks like the same level; brown bands and green scrub around, a green ramp wedge
in the distance (L_Proving).

## 2. The mechanisms, verified in the code (2026-09-22)

**M1, visible sinking: confirmed, one difference.** The shrink is `UGTVehicleTuningComponent::Apply`
(`Vehicle/GTVehicleTuningComponent.cpp:112-119`): Chaos radius = base - min(SinkageCm, `MaxVisibleSinkFraction` 0.6 x
base) (`.h:44`), `SetWheelRadius`; the drawn wheel keeps its size. Base 38 cm (`GTVehicleWheel.cpp:8`), so the cap is
22.8 cm. SinkageCm is the traction's `Sinkage` x 100 (`Vehicle/GTTractionComponent.cpp:450`), grown from the row's
`SinkageRate`/`MaxSinkage` x WetSinkageScale (`:141-143`, `:225-247`). **Differs:** the field does not carry the wheel
down inside a patch. The shrink lowers the wheel everywhere; inside a patch the field read only raises Sinkage to
RutDepth x MaxSink x 0.8 when a rut lies ahead (`:232`), and `StampMud` digs the field to the wheel's sinkage (`:411`),
so the ground follows the wheel. The mud mesh has no collision (`Terrain/GTMudPatch.cpp:22`); the wheels sweep the
landscape. Patch reads and stamps need the Surface.Mud/Bog tag (`GTTractionComponent.cpp:183-184`, `:404-405`).
Patches: only `EGTRouteSectionKind::Mud` sections (`Terrain/GTMudSubsystem.cpp:103`). Sinking without a patch: the
channel paint (Mud wherever a channel is dug past 0.5 x `MudChannelDepthM` 1.5 m, kept off a firm ford's paving only,
`Terrain/GTTerrainGenerator.cpp:651-665`); Dirt and Scrub (Scrub is PM_Dirt, `:359`) at 5 cm dry, **15 cm wet**
(WetSinkageScale 3.0); L_TestTrack's Mud (22 cm) and Snow (25 cm) lanes (`Art/Unreal/setup_m1_track.py:48-52`).
F2 (`GTTractionComponent.cpp:233-239`): above the new row's MaxSink the sinkage falls at `SinkageRecoveryRate` 0.08 m/s
(`.h:159`); Mud -> Dirt measured 0.219 -> 0.052 m in 2.08 s (section 49). **Also found:** the Chaos radius is the
lever. `GTDrivetrainComponent.cpp:79-84` scales each wheel's grip torque cap by `GetWheelRadius`, so a shrink cap is a
movement change, not only a look. **Tests:** none gates the radius. The `mud` test runs on L_TestTrack's patchless Mud
lane and gates only pull-away (>= 400 cm/s and 8 m, not bogged, `Core/GTDriveTestGameMode.cpp:536-543`); `surface`,
`track` and `spray` drive the same lanes; the ford diag logs the radius (`GTFordDiagRunner.cpp:418,499`); terrain's bog
sink (body 7 cm lower, `GTM6TestRunner.cpp:517-530`) is inside the patch.

**M2, the sheet's box: confirmed, with the geometry.** `place_ford_sheet` (`Art/Unreal/setup_m6_hide.py:615-622`,
shared by `setup_m6_proving.py:232`) scales the sheet to (section length + 24 m) x 30 m at the route's mid heading. The
flow runs at route yaw + `FlowYawOffsetDeg` 90, so the field's X (along the flow) is the 30 m and its Y the route
length + 24 m (`GTWaterSheet.cpp:587-620`). `FieldCellCm` 25 (`GTWaterSheet.h:106`). Built on the first tick
(`GTWaterSheet.cpp:508-512`, `BuildField` `:239`); the bed is the landscape height plus a static trace (`BedZAt`
`:128-150`), sampled once. `UGTWaterSubsystem` does not size sheets. Measured: forda 120 x 216 = 25,920 cells (30 x
54 m, 41.8 % wet), fordb 120 x 240 = 28,800 (30 x 60 m, 35.7 %), the Hide 120 x 296 = 35,520 (30 x 74 m, 38.7 %).
Step cost: WS1 0.570 ms per stepping frame with no sources, WS2 0.910 with all; `ford_diag.log` (19:25, before
FarCry6) 0.49 ms mean per sheet; both L_Proving sheets step every frame (no sleep by distance). **Dry cells: handled**
(depth 0 falls out of the solver, a face between two dry cells is a wall, `GTWaterField.h:5-29`). **Found:** Init fills
every cell under the level, `max(0, level - bed)` (`GTWaterField.cpp:64-72`), not a flood fill, so a bigger box floods
disconnected hollows. **Found:** the flow-wise ends are the current's source and sink (open Flather ends at level +-
HeadDropCm/2, `:572-588`, `:773-810`); an end on dry ground passes no water. The channels run along the flow: forda a
capsule (70,-30)-(70,20) m, radius 30, 2.0 m deep; fordb (100,45)-(160,45), radius 20, 3.4 m
(`GTTerrainGenerator.cpp:1165-1166`); the Hide (950,-220)-(1050,260), about 490 m (`:1061`). So the straight edges in
picture 2 are probably the flow-wise ends, 15 m either side of the road (unchecked).

**M3, winch release: confirmed, one difference.** `Release()` (`Vehicle/GTWinchComponent.h:55-57`, `.cpp:138-155`)
sets Stowed, clears anchor and reel, detaches the cable's end and hides the cable (no rewind, no drop). Callers:
`DropHook` only while HookCarried (`:100-106`); the tether when the carrier is gone or seated (`:180`); a lost or failed
anchor (`:210`, `:254`); tests directly (`Core/GTM2TestRunner.cpp:529` then `AttachTo` a weak anchor `:547`;
`GTM6TestRunner.cpp:2156`). No input reaches it once Attached. **Differs:** there is no hook tool; the hook is carried
state (`AGTPlayerCharacter::SetCarriedHook`/`IsCarryingHook`). Take: E hold 0.3 s at the front (`GTCarPawn.cpp:351-353`,
only while `CanTakeHook` = Stowed or Snapped). Attach: E hold 0.5 s on an anchor (`Vehicle/GTWinchAnchor.cpp:42-70`,
"bring the winch hook" when empty-handed). G drops a carried hook (`GTPlayerCharacter.cpp:446-455`, `:537-538`);
getting in drops it (`GTPlayerController.cpp:155`). `AttachCount`: winch `GTWinchComponent.h:149`, anchor
`GTWinchAnchor.h:33`, both counted in `AttachTo` (`.cpp:126-127`). **Keys on foot** (`GTPlayerCharacter.cpp:519-545`):
W A S D, mouse, LShift sprint, E interact, wheel tools, Tab inventory, G drop hook, H head bob, T transfer, Space jump;
pad sticks, L3, A, DPad left/right, View, X drop hook, Y transfer, B jump. **In the car** (`GTCarPawn.cpp:587-619`):
W/Up, S/Down, A/Left, D/Right, Space handbrake, mouse, F exit, R reel (hold), C camera, X diff lock, V low range; pad
RT, LT, left stick X, B, right stick, Y exit, X reel, R3 camera, DPad right diff lock, DPad down low range. Also Enter /
pad Menu, continue (`GTPlayerController.cpp:68-69`). `docs/ARCHITECTURE.md` 7's list is stale (names Recentre,
Headlights, Pause; not mapped).

**M4, a deformable riverbed is the bog's system: confirmed, with the gaps.** A patch reads nothing from the row
directly: its depth is the wheel's Sinkage (the row's numbers through the traction); its look bakes the generator's
layer per vertex, Bog or not (`GTMudPatch.cpp:145`). The ridge numbers are already per patch (UPROPERTYs on
`AGTMudPatch`, `GTMudPatch.h:155-231`, copied into the field); `BuildPatches` sets only `WaterTableCm` per section
(`GTMudSubsystem.cpp:123-124`), so per-section ridge numbers are the same small pattern. A per-patch
SinkageRate/MaxSinkage is looking the patch up before `:141-143`, widening the tag gates (`:183`, `:404-405`) and letting
`BuildPatches` take a section with a profile (`:103`): tens of lines. The landscape hole has 4 slots (Patch0..3 in
MPC_TrackPaint, `GTMudSubsystem.cpp:152-160`); L_Proving would use 3 (bog, forda, fordb), the Hide 2. The solver's
bed is the landscape plus static geometry read at the first tick (M2); a patch never reaches it. The one water query
takes the deeper of sheet and rut water (`GTWaterSubsystem.cpp:101-133`). Backlog line 60 (MUD DEFORMATION TUNABLES)
holds the profile ("a deformation profile per route section ... patches over any section that names one, the stamp on
the profile's surface tags"); its ridge numbers are pre-stage-I (40/25, today 90/12). `MUD_ONE_SURFACE_PLAN.md` has no
deformation profile (only rut profiles).

**M5, R3 is the river: confirmed.** `WATER_PLAN.md` section 6: "R2. Fallen trees: fixed lids" (not started); "R3a. A
river: the spec, the carve, one sloping patch with an inflow and an outflow" (`Rivers`: a polyline, WidthM 14, DepthM
0.7, FlowSpeedMps 1.5); "R3b. The chain: patches end to end, woken by distance, rising by discharge" (about 60 x 24 m
patches, 2 m overlap). S3 fills a ford's basin at its rest level; it does not slope, chain or source a river.

## 3. Stages

Doc sections 50-54. `WATER_PLAN.md` section 6 numbers R2/R3a/R3b as 50/51/52: those move up by five (55/56/57) when
these land. That file is edited by the stage that lands them, not now.

### S0. Housekeeping (when the machine is quiet; section 50)

*BUILT 2026-09-22 (VEHICLE_BUILD_SYSTEM 50). The water test's crossing is held at 3 km/h over the ford's middle 20 m
by a PI on the throttle; the gate stays 1.5 cm and read +1.22 (a first bang-bang try read +1.45); `PASS water (294s)`.
Terrain failed only step 11's ruts flake. The owner decided item 1 (section 4): fords are driven slowly, the intake
stays 0.85 m. Full suite this session, in foreground batches: 23 PASS, 1 FAIL (terrain, the ruts flake).* **Reads:** section 49's test block; `GTM6TestRunner.cpp` the bow step `:3784-3808`, its gate `:3967`,
the speed-hold pattern `:2374` (bang-bang around 1100 cm/s) and `:479`. **Changes:** the settle gate ("the middle back
within 1.5 cm 20 s after") read +1.54 / +1.97 cm after section 49 because the test car passes mid-ford at 6 km/h, not
3 (bow 11.05-12.56 / -13.03 to -15.74 cm against 20.60 / -6.70; +1.19 at 3 km/h before). The runner can hold a speed,
so pin mid-ford to about 83 cm/s (3 km/h) after the 20 km/h entry; re-gate only if the pinned run still fails, with the
measured number and the reason in the gate's text. Terrain step 11 stays a flake. **Record the open decision:** forda
at full throttle floods the intake (front 0.846-0.877 m over `IntakeHeightM` 0.85, `GTConditionComponent.h:208`, from
the bow wave): section 4 item 1. **Tests:** `water`, `terrain`, then the full suite in the background. **Gate:** water
10/10.

### S1. Winch release (section 51)

*BUILT 2026-09-22 (VEHICLE_BUILD_SYSTEM 51), with the plan's keys: on foot, E on the held anchor ("Detach winch hook",
0.5 s) or at the nose ("Release winch", 0.3 s); in the seat, IA_ReleaseWinch on G and DPad Up. Every path calls
`Release()`: the hook is stowed and the pull ends at once. The drawn cable then rewinds at `RewindSpeed` 500 cm/s
(proposed, unmeasured by eye) and hides (item 4 decided). `PASS winch (27s)`: released under 2133 N, 0 N after,
1275 cm in 2.55 s, attaches 2 / 2. Waiting on the owner's try at fordb's posts.* **Reads:** M3's references; `ARCHITECTURE.md` 6e and 7. **Changes:** on foot, E on the anchor the winch
holds offers "Detach winch hook" (`AnchorOffer`, today Unavailable when empty-handed) and E at the front while Attached
offers "Release winch" (`ResolveInteraction` `GTCarPawn.cpp:351`, today it falls through to Enter); both call
`Release()`. In the car, a new action (IA_ReleaseWinch) proposed on **G** (free in the car; G drops the hook on foot)
and **DPad Up** (free), added to `EnsureMapped` (`GTCarPawn.cpp:679-681`) so old mapping contexts get it. On release
the cable does what `Release()` does (hidden, end detached, Stowed); a visible drop or rewind is section 4 item 4.
`ARCHITECTURE.md` 7's key lists brought to the code. **Tests:** `winch` (rerun once on the weak-anchor flake) with a
new step: attach, release through the new action (the key path, not a direct `Release()`), re-attach; it reads winch
and anchor `AttachCount` (+2 each) and the state (Attached -> Stowed -> Attached). **Gates:** winch PASS with the new
step; the owner tries it at fordb's posts.

### S2. No sinking without deformation (section 52)

*BUILT 2026-09-23 (VEHICLE_BUILD_SYSTEM 52). The box is `GTTerrain::MudPatchBoxCm`, shared by the generator and
`BuildPatches`; Mud/Bog outside every box goes to Dirt: survey L_Proving 2,511 -> 0 (forda's channel 1,166, fordb's
1,296, the bog's fringe 49), the Hide 2,750 -> 0 (the terrain test gates it at 0). The shrink is capped outside a box at
`OutsidePatchSinkCapM` 0.05 m and comes back at `VisibleSinkRiseRate` 0.3 m per m of ground (both proposed): out of the
Proving bog's side at 22 cm the shrink reaches the cap 0.31 m past the edge, chassis one-tick rise 0.42 cm; without the
ramp the wheel grew 17.3 cm and its load 12.4 kN in one tick. forda 6.97 -> 6.95 s. L_TestTrack's patchless Mud lane
is 9-10 % slower (mud 593 -> 538 cm/s, surface's Mud exit 1299 -> 1164), all gates pass. `Art/proving_shots.bat` is
L_Proving's picture mode (step 1: the car on forda's channel bank; the tyre ends 6.5-7.8 px above the ground line, and
9.1-9.7 px on a flat control: unchecked, the owner looks). Terrain failed only step 11's ruts flake; full suite 23/24.*
**Reads:** M1's references; VEHICLE_BUILD_SYSTEM 23 (stage 3's sinkage) and 31 (the box, the hole);
`GTMudSubsystem.cpp:80-130`. **(a) The generator paints no Mud/Bog outside a patch box.** The box `BuildPatches`
computes (`:106-116`: route points +- `HalfWidthAt` + `MarginCm` 200) moves into `GTTerrain` so generator and
subsystem share it; `LayerWeights` gives the channel's Mud (`GTTerrainGenerator.cpp:651-665`) and any Mud/Bog weight
outside every box to Dirt, so the ford channel banks become Dirt. Measure first: Mud- and Bog-dominant landscape
samples outside every box, per map (a survey line in the ford diag for L_Proving, the terrain test for the Hide);
expected 0 after. Rebuild both maps, hide then proving. **(b) The visible shrink only inside a patch box.** At the
hand-off (`GTTractionComponent.cpp:450`), outside `PatchAt(contact)` (the box, not `bInMudPatch`, which also needs the
tag), SinkageCm = min(Sinkage, cap), cap **proposed 5 cm** (Dirt's MaxSinkage, unmeasured). Drag, grip, belly and the
F2 decay keep the raw Sinkage. Wet Dirt (15 cm) gets capped. It is a movement change (M1's lever): report it. Bog
physics unchanged (the bog is a patch). **Tests:** `terrain` (bog escape in 13.0-15.0 m, clear-off 0.95, middle sink
>= 7 cm); `drivetrain grip mud surface track spray` (L_TestTrack's Mud and Snow lanes are patchless: any change is
reported before/after as a movement change for the owner, never silently re-gated); `proving`; `Art/ford_diag.bat`
(forda's radius and exit numbers before/after: the diag's radius is the one measure of the shrink outside a patch).
**Picture:** a new L_Proving shot step (the bog_shots pattern, `-RenderOffScreen`) parks the car on forda's channel
bank; the runner logs each wheel's projected lowest point and the ground line under it as boxes, PowerShell reads the
tyre's lowest visible pixel against the ground line (the `sample_border.ps1` pattern). **Gates:** those numbers; the
owner's look.

### S3. The water fills its basin (section 53)

*BUILT 2026-09-23 (VEHICLE_BUILD_SYSTEM 53). GTFORDFILL: forda's basin 76.25 x 28.75 m, fordb's 79.00 x 23.25 m (the
placed boxes 30 x 54 and 30 x 60), no disconnected hollows; the Hide's reaches the 200 m search edge (its stream). The
field is the basin + `BasinMarginM` 2 m (proposed): forda 25,920 -> 42,051 cells, 0.501 -> 0.867 ms; fordb 28,800 ->
36,188, 0.517 -> 0.743 ms; a current keeps its 30 m along the flow, so the Hide is 120 x 475 = 57,000 cells, capped by
`MaxSimCells` 57,000 (proposed), 0.707 -> 1.129 ms, and stops at its ends (+15/-15 cm against a flat sheet). Water only
in the basin; the footprint past the placed box only near it. L_Proving's ponds still (proving asserts under 20 cm/s:
+0.3 and -2.8); seam 0.00 cm (static part checked under a 20,000 cap). Picture step 2 (forda station, eye 5 m): the old
edge's water share 33.8 -> -0.2 points, the car reads 64/0 -> 47/47 cm. water PASS (river 50.57/50.57), proving PASS,
terrain fails only the step 11 flake; the Hide's carried 5.75 -> 7.28 m (movement, reported); forda crossing 6.96 ->
5.72 s. The owner's look next.* **Reads:** M2's references; VEHICLE_BUILD_SYSTEM 41 (WS1), 44 (W5), 46 (R1: `GTWATERSTATS`, the
slow-frame clamp). **Measure first (R1 style):** for each ford on both maps, a flood fill from the lowest bed cell at
`GetLevelCm()` (wetness 0) over `BedZAt`'s heights at 25 cm, in a search box capped at 200 x 200 m; log `GTFORDFILL`
per ford (the wet region's bounds along and across the flow, area and cells, against today's box) and the disconnected
hollows under the level inside today's box. L_Proving from the ford diag's survey, the Hide from a water-test survey
step. **Change:** the sheet's box = the wet region's bounds plus a margin (**proposed 2 m**), simulated up to a cap
(**proposed** so a sheet costs no more than 2 x 0.57 = 1.14 ms/step: at about 18 ns a cell, 0.49 ms / 25,920, that is
about 60,000 cells or 3,750 m2 at 25 cm, extrapolated, unmeasured). Beyond the cap a static flat sheet at `GetLevelCm()`
(so W5's rise follows) in the same material, no solver; waves and current die at the simulated box's edge. Init fills
only the flood-filled region. **Traps (M2):** along the flow the box's ends are the current's source and sink: on a
basin's dry rim they pass nothing and forda's current goes (the current gates decide; section 4 item 5). The ends
stand at level +- 15 cm, so a static sheet at the level meeting one leaves a step up to 15 cm. M_GT_Water samples the
field texture (`GTWaterSheet.cpp:333,416-419`): the static sheet needs a flat one or a switch. The Hide's 490 m stream is
R3a's river: S3 stops at the cap there; R2/R3 untouched. **Tests:** `water`, `terrain` (ford through, flooded, held
0.07 m in 6 s, carried 5.89 m in 10 s, floats, winched), `proving`, the ford diag. **Gates:** water 10/10 (W5 50.57 of
50.6); the current gates as before; `GTWATERSTATS` step cost before/after on a quiet machine; a picture from the forda
station with no straight water edge inside the basin, sampled along the old edge line (a new L_Proving shot, or
hide_22-31 on the Hide if S2's shot step is not there); the owner's look.

### S4. Deformable riverbeds (section 54)

*BUILT 2026-09-23 (VEHICLE_BUILD_SYSTEM 54). `FGTDeformProfile` on `FGTRouteSection::Deform` (mode ByKind: every Ford's
bed, a bog keeps its rows); `BuildPatches` builds the bogs first as before, then the profiled sections, a later box cut
25 cm short of an earlier one (the Hide's ford box overlapped its bog's by 15.8 m: 68.0 -> 51.8 m long). L_Proving 3
patches (bog, forda, fordb), the Hide 2 (bog, ford), every one with a hole. The traction looks the patch up first; the
profile (10 cm, 0.02 m/s, the bog's ridge numbers: proposed) on ground that sinks at all. forda 5.72 -> 5.57 s, exit bank
step 0.0 cm, the wheel at 10.0 cm raw and visible in the water (radius 28.0 cm); ruts under the water 776 cells past 1 cm,
mean -9.76 cm, deepest -11.27; the depth the car reads 57.8/58.1/60.2 cm before and after; the rut picture 33.1 % of the
rut pixels changed against 0.0 % beside them; the box edge mud minus land +30.8 (the mesh draws the Mud row on Dirt).
Found: a 4.0 cm one-tick radius step at the far edge of forda's box at 9 m/s (S2's rise rate). terrain fails only the
step 11 flake (bog unchanged); the water test's bow settle read +1.54 (FAIL) and +1.47 cm (asked 1.5; +1.40 with
-GTNoBedPatch). Full suite 23/24, terrain's flake the one FAIL.*
**Reads:** M4's references; VEHICLE_BUILD_SYSTEM 27-29 (field, mesh, physics read), 31 (the hole), 36
(the rut water). **Changes:** the profile (backlog line 60) as a struct on `FGTRouteSection`: SinkageRate, MaxSinkage
and the ridge numbers, overriding the row's for wheels inside its box; `BuildPatches` builds a patch for any section
with a profile and copies its ridge numbers (the `WaterTableCm` pattern); the traction looks the patch up first, the
tag gates widened to "a patch with a profile". A patch per ford bed on the bog's box rule (ford half width 6 x 1.2 =
7.2 m + 2 m), starting profile **proposed** MaxSinkage 10 cm, SinkageRate 0.02 m/s (Dirt's x 2), the bog's ridge
numbers, unmeasured; the owner names the rest after feeling it. The patch's rut-water mesh off where a sheet covers;
the landscape hole = the box, as the bog. The solver's bed stays the landscape, static: ruts do not deepen the ford
water (the car's depth is the sheet surface minus the landscape contact). **Traps:** section 49's F3 on a Mud bed made
forda 27.12 s (the diag gates it); the mesh wears M_GT_Mud (muddy_tracks, Mud/Bog tints) on a Dirt bed, so the look at
the box edge is unchecked (`sample_border.ps1`); a fifth patch gets no hole. **Tests:** `terrain proving water`,
`drivetrain grip mud surface track`, the ford diag. **Gates:** forda crossing under 8 s (6.92 now) and the exit
one-tick sinkage step under 2 cm; terrain, proving and water pass; ruts under the ford water pictured from the ford
steps (hide_22-31) and sampled on the `sample_rut_low.ps1` pattern; the owner drives forda.

## 4. Open decisions for the owner

1. **Decided 2026-09-22** (the owner: "Keep it as 'drive fords slowly'"): forda's intake flooding at full throttle
   stays; `IntakeHeightM` stays 0.85 (front water 0.846-0.877 m at full throttle). Recorded in section 50, nothing changed.
2. **Decided 2026-09-23** (the owner: "go ahead with S2"): the 5 cm cap (`OutsidePatchSinkCapM`) is the starting
   number, with the 0.3 m per m rise rate beside it; the owner names both after feeling. The change on L_TestTrack's
   patchless lanes is reported in section 52 (Mud lane pull-away 593 -> 538 cm/s, all gates pass).
3. **Decided 2026-09-23** (the owner said go ahead with S2 as written): yes, channel floors go from Mud to Dirt. The
   survey (section 52) counted 1,166 Mud-dominant 1 m samples in forda's channel outside any patch, 0 after; picture 1's
   pale ground fits it, which is as far as a count goes.
4. **Decided 2026-09-22** (the owner: "stow the hook, rewind visibly"): detaching stows the hook (today's
   `Release()`), and the cable rewinds visibly to the drum. Built in section 51 at `RewindSpeed` 500 cm/s (proposed,
   unmeasured); the owner names the speed and the look.
5. **Decided 2026-09-22** (the owner: "let the ponds stand still"): the Proving Ground's fords are closed basins and
   their ponds stand still. No current through them; the sheet's ends go onto the dry rim. This is for S3 to build.
6. **Decided 2026-09-23** (the orchestrator, after the owner's "go ahead with S4"): both maps' fords get a bed patch.
   The profile is the Ford kind's default (`FGTRouteSection::Deform`, mode ByKind), so DA_Terrain_Hide's ford took it
   with no asset edit; the Hide's ford holds hole slot 1 of its 2 patches, L_Proving's forda and fordb slots 1 and 2 of
   3, no bog lost its hole. The numbers (MaxSinkage 10 cm, SinkageRate 0.02 m/s, the bog's ridge numbers) stay the
   owner's to name after driving. Built in section 54.
7. **Decided 2026-09-23:** a picture mode for L_Proving, built in section 52: `Art/proving_shots.bat`
   (`-GTProvingShots`, `-RenderOffScreen`, one runner step per stage, `-GTShotsFrom=N` through the .bat's first
   argument; S3 and S4 add their steps after step 1).

## 5. Costs and unknowns

- **Water fields** at 25 cm (M2): forda 25,920 cells, fordb 28,800, the Hide 35,520; the surface mesh is one vertex a
  cell (35,520 on the Hide). 0.49 ms per sheet on L_Proving, both every frame (about 0.99 ms together). The water
  test's 0.86-0.93 and the proving test's 0.60-0.65 ms ran with FarCry6 up: void.
- **Mud patches** at `CellCm` 12.5 (`GTMudSubsystem.h:39`) and `MeshCellCm` 12.5 (`GTMudPatch.h:112`): the Hide's bog
  mesh **158,730** vertices (555 x 286) and its rut-water grid the same **158,730** (315,780 triangles); L_Proving's
  bog water grid 663 x 211 = 139,893. A ford-bed patch (forda, about 48 x 18 m): about 55,000 cells and vertices,
  unmeasured. Each patch is a field, a mesh and a water mesh; S4 turns the last off under a sheet.
- **Landscape**: **21** texture samples a pixel since the painterly rows (section 48), the hole mask on top; frame
  cost unmeasured, as are the bicubic field sampling (34) and the second grid (36).
- **Unknowns:** rendered runs are bimodal (real time or about a quarter speed on one build); the flood fill's extent
  on the Hide (a stream, not a pond); section 49's unexplained force (-820 to +1390 N along the table); whether the
  22.8 cm shrink cap agrees with picture 1's "to about the hub" (unchecked).
