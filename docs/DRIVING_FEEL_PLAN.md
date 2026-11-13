# Driving feel plan (2026-09-14)

The user drove The Hide's sections and called the driving generic: the rally stretch easy with no
sense of risk, the bog and the 4WD roughness absent. This is the plan to fix that, in stages, each
with a headless check and a feel test by the user before the next. Reference: MudRunner / SnowRunner
for the heavy ground, rally stages for the fast stretches (PROJECT_PLAN 6).

## Why it feels generic (read from the code, not guessed)

- **Twice the grip of a real car.** Chaos grip per wheel = load x surface Friction x the wheel's
  FrictionForceMultiplier. The project never sets the multiplier, so it is the Chaos default 2.0
  (ChaosVehicleWheel.cpp). Tarmac 0.70 becomes 1.4 g, dirt 0.62 becomes 1.24 g, mud 0.45 x 0.7 at full
  sinkage still 0.63 g. A Range Rover on gravel has about 0.6 g. Nothing on the map can make the car
  slide, so every bend is flat out and the rally stretch cannot be risky.
- **No progressive breakaway.** No LateralSlipGraph is set, so lateral force is slip angle x
  CorneringStiffness (a stiff linear spring) clipped by the friction circle: the tyre is on rails until
  it saturates, then slides with the same force (SideSlipModifier 1.0). No "letting go", nothing to
  catch. The steering has no speed falloff of its own beyond the Chaos default curve, and 35 deg of lock.
- **A billiard-table road.** The landscape has 2 m quads, so nothing under ~4 m wavelength exists. The
  road is a smoothed profile (80 m road / 30 m rally) with a flat cross-section; off-road noise is four
  octaves down to ~40 m. There are no ruts, stones, water bars, roots, potholes or ditches. The rally
  stretch is 1.3 x width = 15.6 m wide, with a smooth shoulder either side: leaving it costs nothing.
- **Mud is a number.** Sinkage grows to 0.30 m over 6 s at rolling speed and only scales drag and
  grip; the wheels never visibly sink, the chassis never touches the mud, the drag at full sinkage
  (0.14 of load + plough) is under what first gear pushes, and the bog is 50 m: the car is through before
  it has sunk.
- **Locked differentials everywhere.** Chaos gives every powered wheel TransmissionTorque x its fixed
  ratio, whatever the other wheel is doing (ChaosWheeledVehicleMovementComponent.cpp ~line 900). A wheel
  in the air or in slime never starves its partner. There is no diff lock to engage, no low range, so
  there is nothing to operate in the mud.

## Stages

### 1. Grip that can be lost (about a day)
*Built and headless-verified 2026-09-14 (VEHICLE_BUILD_SYSTEM.md section 20): grip test tarmac 0.84 g, dirt
0.47 g; the rally bend at 90 km/h flat out is left by 25 m, at 43 km/h held. Also found and fixed: Chaos 5.8's
constraint suspension left the tyres 70-85 % of their real load. Awaiting the feel test.*
- FrictionForceMultiplier 2.0 -> 1.0 on both wheel classes and the surface Friction table rewritten
  as real coefficients (tarmac ~0.95, dirt ~0.62, mud ~0.38, snow ~0.28; scrub reads as dirt).
- A LateralSlipGraph on the wheels: rising to a peak around 6-8 deg, easing to ~75 % by 25 deg, and
  SideSlipModifier ~0.85 so a sliding tyre gives less than a gripping one (a slide that has to be caught).
- Steering angle by speed (full lock at rest, ~12 deg at 60 km/h, ~6 deg at 120) and the steering
  input rise rate, so keyboard lock at speed is not an instant spin.
- Numbers live in one place: the surface table in Art/Unreal/setup_m1_track.py and a tyre block on the
  wheel classes (EditAnywhere), no constants in the traction code.
- Check: a skid-pad number in the drive test (peak lateral g on dirt ~0.6, tarmac ~0.9); a flat-out run
  into the rally stretch's sharp bend at 695 m leaves the road, the same run 25 km/h slower stays on.
  Rerun the whole suite: the timings in drive / mud / rough / leg / terrain tests will move.
- Feel test gate: the user drives the valley road and the rally stretch.

### 2. Ground with texture (two to three days)
*First part built 2026-09-14 (VEHICLE_BUILD_SYSTEM.md section 24): 1 m quads and bumps per surface (road 2 cm,
rally 6, track 15, mud 12, ford 8, scrub 25 at 4 m and 2 m). The rest built the same night (section 25): stones in the
tracks and posts along the rally edges with collision (`AGTTerrainDressing`), water bars every ~100 m across a track,
a wandering rut pair down tracks and bogs, crests and compressions listed on the rally section (The Hide: 0.9 m at 810,
-0.5 at 862, 0.8 at 960), RallyWidthScale 0.75 with a 3 m verge (ditch on fill, bank in cut). Terrain test: the crest at
87 km/h lifts all four wheels for 0.44 s, the track at 40 km/h shakes at 0.45 g RMS, the car dropped on the verge rolls
11.5 deg into the ditch. Awaiting the feel test.*
- Landscape quads 2 m -> 1 m (4x the data, fine for a 2 km map) so the generator can carry detail.
- Roughness per section kind in the spec: road ~2 cm, rally ~6 cm, track ~15 cm, mud ~10 cm, scrub
  ~25 cm, at 2-6 m wavelengths, faded out on the paved centre of a road and kept on a track.
- Track features: water bars (a 20-30 cm ridge across the track every 80-150 m), stones in the track
  (instanced low rocks with collision, 15-40 cm, from the generator), rut pairs on mud and track.
- Rally features: explicit crests and compressions listed on the section (arc, height, length) so the
  car goes light or airborne at 90+ km/h; RallyWidthScale 1.3 -> ~0.75 (9 m road); a verge profile at
  the paved edge (a ditch on the fill side, a bank on the cut side) so a wheel off the road is pulled in;
  posts or greybox trees along the rally edge at 20-40 m spacing, with collision, so leaving the road
  dents the car through the existing body and condition systems.
- Check: the rough test's RMS g at 40 km/h over a track section above a floor; a crest at 90 km/h puts
  all four wheels off the ground for >= 0.3 s; a car placed 1 m off the rally edge sits >= 30 cm lower
  and rolled; the terrain test still passes every section.
- Feel test gate: the track under the hillside and the rally stretch again.

### 3. Mud and water that take the car (two to three days)
*Built and headless-verified 2026-09-14 (VEHICLE_BUILD_SYSTEM.md section 23): the bog's middle stops a 30 km/h
entry 25 m in with the car 19 cm lower; the mud edge crawls through in low range with the lock; the ford is driven
in 0.6 m and floods the engine at 1.3 m. The belly is drag and grip loss in the traction rather than a collision box
(Chaos has no unsprung axles). Felt 2026-09-14: "Looking pretty good", but the car got completely stuck with no way
to move (deep mud retuned so a locked low-range crawl creeps at walking pace) and the ground should have shape
(stage 2 started). Felt again 2026-09-15: "brings the car to a stop, and you cannot drive out": the retune's creep was
13 cm/s by the test's own measure under a squared plough law, and the relief had since shaped the bog. Plough drag is
linear under 10 m/s now, the rut is read along the heading at rest (reverse into your own ruts), BellyGripLoss 0.15 and
the Bog row 0.040 / 0.8 / 0.25: a dead stop in the deep band pulls away at 0.095 of the load and crawls at 2.1 m/s; the
terrain test's new escape step drives 15 m out forward and 6 m back (VEHICLE_BUILD_SYSTEM.md section 26). Not felt.*
- Visible sinking: the Chaos wheel radius is reduced by the sinkage (SetWheelRadius) while the drawn
  wheel keeps its size, so the tyre buries itself and the body drops onto the mud; the physics asset
  needs a floor-pan body so the belly drags (high-centred is then real Chaos contact, not a number).
- Mud numbers reworked for real grip: sinkage to 0.3 m in 2-3 s under wheelspin, slow recovery, grip
  loss ~0.5 at full sinkage, rolling and plough drag that stop a 30 km/h entry inside 40 m.
- A sixth layer, deep mud, painted by the generator in the trough's centre and in pockets, with firm
  edges to read: line choice is the MudRunner skill.
- Water (the backlog item, same stage): depth by wheel from the sheet's level, drag rising with depth,
  the engine floods past a bonnet-height level, the weather can raise the level.
- Check: the mud test as above; wheels visibly below ground in a screenshot (pixel-sampled); the
  crawl gets through the shallow line and bogs in the deep one; the ford stalls the engine at depth.
- Feel test gate: the bog and the ford.

### 4. A drivetrain you operate (two to three days)
*Built and headless-verified 2026-09-14, before stages 2 and 3 at the user's call (VEHICLE_BUILD_SYSTEM.md
section 22): open diffs on ice 194 cm in 4 s, locked 1359 cm; a 35 % standing start fails in high range and
climbs 10.6 m in low; reverse from the pedals. Two Chaos hill hacks (the suspension's straight-up normal at low
speed, sleep on slopes) are off. No clutch model yet, so the engine does not bog down audibly. Felt: "Solid". Found
after stage 3: Chaos's island sleep took the chassis when it stopped on the ramp under throttle and the wheels' torque
did nothing (the test had failed unseen, left out of the suite script); the chassis body now never sleeps (section 25).*
- Per-wheel torque through SetTorqueCombineMethod(Override) + SetDriveTorque / SetBrakeTorque, computed
  from the Chaos engine's RPM, gear and throttle so the dash and audio keep reading Chaos.
- Open centre and axle differentials (a pair's torque limited by its weaker wheel: a spinning wheel
  starves its partner), a diff lock toggle (equal torque plus brake bias on the runaway wheel), low
  range (torque up, shift points and speed down), dash lamps LOCK and LOW; gamepad and keyboard binds.
- Check: one wheel of an axle on a 0.05-friction slab: the car cannot move open, moves locked; low range
  climbs a 35 % ramp that high range stalls on.
- Feel test gate: the bog with the levers.

### 5. Feedback, after the user has felt 1-4 (one to two days)
- The first-person camera's vertical lag (12 / 8 cm) filters the bumps stage 2 adds; body roll on
  camber; spring 340 / damping 0.62 was tuned on the flat rough patch and may need to move for real
  ground; engine load in the audio. Only what the user names.

## Not in this plan
Real-time terrain deformation (ruts that deepen, Tier 2), a Pacejka tyre, a manual gearbox (cheap to
add as a toggle on stage 4 if wanted), textures and vegetation (the M6 art items follow).
