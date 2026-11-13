# Power and ride consistency follow-up

Owner feedback rejected the previous Ferrari pass: power still felt muted/traction-controlled and suspension bounced. Focused checks and a supplementary lap had not established satisfactory driving feel.

## Confirmed causes and evidence

UE 5.8 `ChaosVehiclesCore/Private/WheelSystem.cpp`, `FSimpleWheelSim::Simulate`, sets a grounded wheel's omega to ground omega plus **one step** of excess-torque spin. It does not retain that spin between steps. The custom independent engine then reads this wheel speed back through its clutch. Native traction control is disabled on all four Ferrari and Range Rover wheels.

The unchanged rendered low-friction fixture confirmed frame dependence. Six seconds of full throttle from idle on friction 0.08 gave Ferrari peak engine RPM 3,863 at 30 fps versus 2,711 at 120; Range Rover 2,866 versus 1,892. Road speeds were almost identical (Ferrari 6.6 km/h, RR 12.4 km/h). Reports are `Saved/FerrariDrivingQA/consistency-before.json` and `.log`. All six scenarios recorded, but the baseline process exited -1073741819 during shutdown; it is not a clean process pass.

The Ferrari also had authored soft springs plus another 20% speed-dependent softening and rollbar reduction. Removing the dynamic softening alone did **not** improve the repeated-bump result: vertical velocity RMS rose from 14.40 to 18.12 cm/s. Stiffer damping alone was also harsher in the first candidate run. Candidate suspension selection therefore uses measured repeated impacts, rather than assuming that more damping is automatically better.

## Implementation under validation

`GTPersistentWheelSpin.h` retains rotational momentum and solves a bounded rolling-contact impulse, with drive torque, braking and equal tyre reaction. Longitudinal/lateral forces share the existing grip limit. `GTSoilVehicleMovement.cpp` replaces the native wheel force with the resulting force at the same contact position, and updates the actual wheel omega and angular position; this is not cosmetic RPM or a torque boost. Native suspension contacts and lateral slip curves remain in use.

The initial momentum-only candidate let both cars reach their rev limits, but light wheels overshot shaft RPM too much at 30 fps. The engaged engine's ratio-squared rotational inertia is now reflected onto the driven wheels. The existing clutch remains a simplified hybrid model, not a full multi-body driveline simulation. The helper has native checks for torque reaction, friction bounds, spin accumulation, lift-off, brake lock, airborne spin and 30/60/120 Hz behavior.

The inertia candidate completed with native tests and process exit 0 (`consistency-candidate-inertia.json/.log`). At 30/120 **frame caps**, Ferrari peak shaft RPM was 7,940/7,731 and RR 5,138/5,070; both reached their engine limit under idle-launch throttle. Rendered frame caps are not a claim that the GPU presented every frame at 120 Hz. The separate native solver tests cover actual 30/60/120 Hz time steps.

Under the same new wheel physics, repeated-bump vertical velocity RMS was 20.45 cm/s on the authored fixed springs, 16.09 on 260/280 springs with 0.72/0.76 damping, and 16.57 with stronger 0.85/0.88 damping. Mean speeds were within 0.2 km/h. The moderate-damping tune was selected: roughly 21% less vertical motion than the fixed authored-spring candidate, with peak pitch reduced from 3.00° to 2.54°. This is **not** a 21% improvement over the owner's prior adaptive tune: its coast behavior differs and its earlier RMS was 14.40. Owner ride acceptance still requires driving under power over the real course.

Selected Ferrari assets retain 8/12 cm travel and 35° lock, with fixed 260/280 rates and 0.72/0.76 damping. Its original 3.4 first gear is restored from the previous pass's 2.9 workaround, giving approximately 17% more first-gear torque multiplication without increasing engine output. Final consistency checks add a powered 40 km/h repeated-bump run alongside the 80 km/h-entry coast run.

The rollout is to Ferrari and Range Rover high-range firm-ground driving. Low range, yielding mud and water retain the established solver; other vehicle powertrains are unchanged. `gt.Vehicle.PersistentSpin 0` provides a diagnostic A/B. The Ferrari uses a fixed spring/damper tune, bypassing speed-dependent suspension softening. No graphics reductions are part of this work.

Rendered probe: run `Art/wait_unreal_free.ps1` as its own command, then `Art/ferrari_drivetrain.ps1 -Mode Consistency -Label <label>`. The probe opens the existing rally map, uses transient fixtures, and compares two frame caps and six repeated crests. Candidate wheel CDO edits are in memory only; the selected tune is saved separately after comparison. Maps and player saves are protected.

Pre-change source and Ferrari wheel assets are backed up under `Saved/WorkshopBackups/20261027-power-consistency/`. Original failed/intermediate reports are retained. Complete corners, focused drivetrain checks, Range Rover regression and the owner's keyboard drive remain required gates.

## Final verification

- Final consistency probe: native tests and all six rendered scenarios passed; process exit 0. Ferrari shaft peaks at the 30/120 frame caps were 7,908/7,649 RPM; RR 5,138/5,072. Both reached their engine rev ranges from idle on low grip. Protected maps, vehicle/wheel assets and saves were unchanged by this probe. `Saved/FerrariDrivingQA/consistency-final.json` and `.log`.
- Repeated crests: held-40-km/h run crossed all six with 10.04 cm/s vertical-velocity RMS, 2.47° maximum pitch and 0.03° maximum roll. The 80-km/h-entry coast run recorded 15.39 cm/s RMS, 2.64° pitch and 0.08° roll; final vertical speed was -0.15 cm/s. These fixtures do not establish jump-landing or owner feel acceptance.
- Ferrari focused suite: **44 checks passed, process exit 0**, including the saved fixed suspension configuration, independent handbrake revs, launch, shifting, torque conservation, rear-wheel RPM, steering reversal/return, small crest, low-grip revs from idle, low range, reverse, fuel cutoff and protected saves/maps. `Saved/FerrariDrivingQA/check.json`, `Saved/Logs/Ferrari-Check.log`.

The original version-2 full-course driver still failed: 815.86 m, 98.53 km/h peak, 12.02 m maximum offset and 78.79° maximum slip; process exit 0. The new solver was active for the entire trace. It ran wide before applying full throttle while recovering its line. This remains a failed cornering test, not a pass; `Saved/RallyHandlingQA/corners-ferrari-power-consistency.json` retains it.

The first Range Rover regression stopped after 86 checks because the handbraked hill fixture crept. Diagnosis: the new contact impulse still included free wheel rotation when a strong brake could hold it locked. The locked case now reacts the supported body mass directly and includes a native regression assertion. `power-regression-hill-failure.json/.log` preserve that run. The full suite must pass again after this correction.

After correcting locked contact, **all 146 Range Rover checks passed with process exit 0**, including parked slopes, Expedition hill starts in both ranges, all three packages, traction loss, airborne/recontact behavior, reverse, fuel cutoff, BMW exclusion and protected player saves/maps. Native tests also passed. Evidence: `Saved/FerrariDrivingQA/power-range-rover-regression.json` and `.log`.

Over the final two seconds of full throttle on the slippery fixture, mean engine RPM was Ferrari 7,592/7,546 and RR 5,040/5,020 for the 30/120 frame caps: under 1% difference. Actual sampled callback rates were approximately 30 and 97 Hz; this is not a 120 fps rendering claim.

The existing version-3 recovery-aware driver completed 1,518.81 m on the final build: 98.55 km/h peak, 2.93 m maximum path offset, 34.16° maximum body slip recovered, and 2.25° maximum roll. Callback wall times: mean 12.69 ms, p95 14.68 ms, p99 16.38 ms, maximum 179.81 ms. Graphics remained unchanged. This demonstrates complete corners and recovery with lifting, not an unchanged-controller baseline win or 120 fps. The process then exited **-1073741819 during shutdown**; the completed lap is captured evidence, not a clean process pass. Report/log/process files are `Saved/RallyHandlingQA/corners-ferrari-power-recovery.json`, its `-process.json`, and `Saved/Logs/RallyHandling-Corners-ferrari-power-recovery.log`. The existing intermittent shutdown fault remains unresolved.

The Ferrari focused suite was repeated after the locked-contact correction: **44 checks passed again, process exit 0**. The final source also passed the guarded Development Editor build and Python syntax checks. No source changes followed these tests.

Owner test: use `Art/ferrari_drivetrain.ps1 -Mode Play`. Test full-throttle wheelspin and lift-off on gravel, powered exits in sections 2–4, and the crest in section 6. W + Space still permits free revs; F1 shows RPM/gear. The tune is ready for a fresh owner assessment, with the original automated corner failure, frame hitch and intermittent editor shutdown error explicitly outstanding. The other fleet cars have not received this new wheel model.

Interactive handoff: guarded Ferrari Play is running as PID **19124**. The rally map loaded successfully, the game window responds, `-GTFerrariTest` is active and the saved graphics profile is retained. Log: `Saved/Logs/Ferrari-Play.log`. Do not build or start another Unreal process while this game is open.
