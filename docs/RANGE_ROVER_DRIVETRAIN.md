# Range Rover drivetrain prototype

Open the workshop with **U** while parked, then choose **Drivetrain** (or cycle categories with Tab). Select Standard, Rally or Expedition and press Enter to fit. Preview and compare describe the choice without changing the running drivetrain. Return to driving to feel it. Tyres, suspension and equipment remain separate choices.

**V** selects high/low range while stopped (below 30 cm/s); **X** toggles the existing centre and axle locks. Rally has limited-slip behavior with the full locks off. Expedition starts with whichever range/lock state the route or driver selected; fitting does not silently engage them. F1 exposes range, diff mode, package, gear and RPM in the driving lab HUD.

| Package | Engine behavior | Gearing | Differentials |
|---|---|---|---|
| Standard | Authored torque curve and pedal response | Authored four-speed, 3.54 final, 2.50 low on the current RR | Authored open/selectable locks |
| Rally | Sharper pedal, 6% less idle torque, 15% more at 2500 RPM, 32% more at 4500 RPM | 3.05 / 2.15 / 1.58 / 1.18; 3.90 final; 4500/2300 RPM shifts; 0.22 s shift cut | Partial centre/front/rear coupling; strongest at the rear; reduced on lift-off |
| Expedition | Progressive pedal, 20% more idle torque, 12% more at 2500 RPM, 20% less at 4500 RPM | Original forward ratios; 4.11 final; 3.30 low; 3400/1500 RPM shifts; 0.45 s shift cut | Open until the driver selects full locks |

Multipliers are relative to the authored torque curve, after the existing fuel, damage, flooding and environment tuning. They are gameplay tuning values, not specifications for a real Range Rover engine. The 5000 RPM limiter and the approved hybrid V8 audio stay in use; the audio reads the actual engine RPM and shaped throttle. No new exhaust recording, cooling upgrade or separate thermal penalty is included in this pass.

The installed engine-slot part identifies the package: `Part.Engine`, `Part.RREngineRally`, `Part.RREngineExpedition`. These are complete drivetrain packages for this prototype, not three separate purchasable engine/gearbox/diff items. The two new packages are Range Rover-only in the normal install path. The runtime also checks the exact approved Range Rover mesh, so a foreign loadout cannot enable the new behavior on another car. Other cars continue to read their authored engine and transmission configuration.

The workshop uses the existing mechanical installation transaction and run/loadout persistence. Outside the driving lab the replacement must be in the boot, with room to return the old unit. In the lab, fitting changes only the current pawn's loadout: it does not spend or grant inventory, repair damage or write a separate cosmetic save. Campaign persistence occurs through the existing run save lifecycle. Existing saves without the new part IDs use their original settings.

Implementation: `GTRangeRoverDrivetrain.h` owns the package tables. `GTDrivetrainComponent` resolves the current car's loadout and applies ratios, pedal shaping, curve multipliers and LSD coupling to its existing wheel-torque simulation. It does not modify movement configuration assets or shared wheel classes. Package changes reset shift state. Full locks use the existing drivetrain model; this is not a new clutch, gearbox-inertia or transfer-case simulation.

Validation commands (each launch/build must be preceded by the standalone Unreal-free guard):

```powershell
powershell -NoProfile -File Art/wait_unreal_free.ps1
powershell -NoProfile -File Art/build_guarded.ps1
powershell -NoProfile -File Art/wait_unreal_free.ps1
powershell -NoProfile -File Art/workshop.ps1 -Mode DrivetrainCheck
```

`check_rr_drivetrain.py` runs native differential/pedal checks, rendered workshop checks, equal-duration gravel acceleration runs, a transient hill-start fixture, reverse and fuel-cutoff checks, disk loadout round trips, independent-pawn checks and non-Range Rover exclusion. It uses isolated QA saves and verifies the player's existing save files and map assets are unchanged. `Art/workshop.ps1 -Mode Check` remains the full pre-existing wheel/suspension/equipment regression.

## Validated 26 October 2026

Editor build succeeded. The final drivetrain suite passed all **78 checks**, including the native automation case, with editor exit 0. The native case exercises the production differential splitter with unequal traction and reverse/coast inputs, pedal/torque invariants and both new part IDs through the real save class on disk. Live PIE checks cover preview/cancel/compare, fitting without lab repairs or inventory changes, captured-loadout restoration, independent vehicles, acceleration/shifting, steering, transfer-shift gating, reverse, empty-fuel cutoff and light-throttle behavior. A BMW rejects the new packages and ignores their special configuration even if a loadout is imported directly.

The full existing workshop regression subsequently passed **205 live checks with editor exit 0**, covering paint, wheels/tyres, suspension, equipment, preview restoration, loadout/cosmetic recovery and driving. Its current report is `Saved/WorkshopQA/check.json`; the previous equipment-only baseline was preserved as `check-before-drivetrain.json`.

Measured examples from the final run (illustrative comparisons, not certified vehicle specifications):

| Same gravel start, eight seconds at full throttle | Maximum speed | Highest gear |
|---|---:|---:|
| Standard | 81.4 km/h | 3 |
| Rally | 94.3 km/h | 3 |
| Expedition | 79.4 km/h | 3 |

On a transient 15-degree ramp, five seconds at 40% throttle with Expedition and locked diffs moved **8.1 m backwards in high range** and **8.6 m uphill in low range**, from the same standing start. Both new packages also completed a four-second steering sweep from the gravel start, changing heading by about 51–53 degrees with peak chassis roll below 2 degrees. These are bounded scenarios, not an exhaustive terrain, endurance or player-feel test.

The progressive throttle map initially exposed an engine-braking edge case. Lift-off detection now reads the original pedal position, so a light Expedition throttle request still produces positive torque while rolling. That behavior is covered by the final live checks. The standard and other-car pedal path remains unchanged.

Evidence: `Saved/WorkshopQA/drivetraincheck.json`, `drivetrain-final.json`, `Saved/Logs/Workshop-DrivetrainCheck.log`, and the reviewed in-game screens `11-rally-drivetrain.png` / `12-expedition-drivetrain.png`. Initial harness failures and the earlier successful 72-check run are retained separately. Player saves and the rally/LiDAR map assets were unchanged; QA save slots were cleaned up. The first two aborted harness attempts encountered the previously observed editor shutdown error; the two complete drivetrain runs exited cleanly. This does not claim to fix that pre-existing intermittent editor issue.

## Traction-loss response, 27 October 2026

Driver feedback identified a loss-of-power feeling when grip broke away. Two code paths could contribute: the original differential splitter discarded input torque against estimated opposite-wheel grip limits, and the automatic gearbox used spinning-wheel RPM on surfaces outside the yielding-soil path. The latter could command an unnecessary shift and its associated torque cut.

For the exact Range Rover mesh, across Standard/Rally/Expedition, the centre and axle splits now conserve input torque. Open diffs divide shaft torque equally; the existing limited-slip and full-lock couplings redistribute it between sides. The Chaos tyre solver already caps ground force against available grip and applies excess torque to wheelspin (`ChaosVehiclesCore/Private/WheelSystem.cpp`); the drivetrain no longer applies a second grip-based torque cap. Other fleet cars retain the legacy splitter.

Range Rover shift decisions now consider road speed on every surface. Excess shaft RPM relative to road speed, or zero grounded wheels, holds upshifts. Downshifts are inhibited during wheelspin unless engine RPM is genuinely below the downshift threshold. The normal rev limiter, tyre grip, engine damage, fuel/flooding behavior and deep-bog penalty remain active. This is not a traction increase or a blanket removal of all power limits.

The live regression adds a transient 0.08-friction platform, checks all three packages for torque conservation and wheelspin-triggered shift cuts, and exercises airborne spinning wheels followed by ground contact in the same car. Native checks preserve the old fleet splitter and test the new split and shift decisions independently. Diagnostic `SetupReport()` fields now include contact count, road/shaft RPM, wheelspin shift hold, remaining shift cut, tuning torque scale, requested wheel torque and delivered wheel torque. The earlier 26 October report is preserved at `Saved/WorkshopQA/drivetrain-before-slip-fix.json`.

Validation: the editor build succeeded and the expanded **105-check drivetrain suite passed with editor exit 0**. All three packages exceeded available grip on the 0.08-friction fixture while preserving requested wheel torque within 0.1 Nm, with no wheelspin-induced shift cuts. The same airborne Rally vehicle resumed powered ground contact after landing. Normal acceleration/shifts, steering, hill starts, reverse, light throttle, empty-fuel cutoff, saved package IDs and BMW exclusion also passed. Player saves and map assets were unchanged. Evidence is retained in `Saved/WorkshopQA/drivetrain-slip-final.json` and `drivetrain-slip-integration.json`.

The first slip-check run failed an overly high airborne RPM expectation, not torque delivery or shift hold: Chaos already has an unloaded-wheel spin ceiling. The assertion was corrected to validate spinning above idle, continued shaft torque and actual recontact. That existing wheel-spin ceiling was not changed.

## Handbrake revving and automatic clutch, 27 October 2026

Further driver feedback exposed the separate RPM problem: the custom engine was set directly to `max(idle, wheel RPM)`. Locked wheels therefore pinned it to idle, regardless of throttle. The torque-conserving differential changes above could not fix that coupling.

Range Rover Standard, Rally and Expedition now integrate engine RPM independently, using the existing torque curve and package throttle/torque maps, a 0.65 kg m² engine/flywheel inertia and rotational drag. A simplified automatic clutch transfers engine output plus a bounded speed-synchronisation torque and applies the equal opposite load to the engine. This is an arcade automatic-clutch model, not a detailed simulation of the original vehicle's hydraulic torque converter. The existing idle floor is retained; stalling and restarting are outside this change.

Holding Space opens the clutch immediately. W can raise engine RPM while the handbraked wheels remain still; lifting W lets revs fall. Releasing Space reconnects the clutch progressively over 0.4 seconds, so stored flywheel energy contributes to launch instead of RPM snapping to wheel speed. An anti-stall capacity limit permits low-speed launch, while rolling wheels can back-drive the engine on overrun. Shifts open the clutch and retain their existing combustion cut. Free revving cannot upshift; stopping with the handbrake selects first gear for the next launch. Reverse uses the same engine/clutch model with the existing drive-direction convention.

Engine RPM continues to feed the existing hybrid V8 audio and driving display. `SetupReport` adds `clutch_engagement` and `clutch_nm`; `engine_nm` reports combustion output for the Range Rover, while requested/delivered wheel torque measures actual transmitted drive after the clutch. Fuel, damage, flooding and bog tuning still scale combustion output. Residual flywheel energy can briefly drive the shaft even after combustion ceases. Other fleet cars retain their previous RPM/torque path. No audio recordings, graphics, tyres, brakes or saved map assets are changed.

The regression now reproduces held-handbrake revving, lift-off and release for every package, plus a rolling handbrake/recovery/stop sequence, empty-fuel free revving and BMW wheel-coupled RPM. Native tests exercise free revs, rundown, progressive take-up, equal engine reaction and rolling back-drive. Previous evidence is preserved as `Saved/WorkshopQA/drivetrain-before-clutch.json`; source backups are under `Saved/WorkshopBackups/20261027-handbrake-clutch/`.

The first live pass passed the new handbrake checks but failed the existing hill-start comparison. Its clutch used absolute shaft speed, incorrectly treating backward roll as forward rotation and applying torque downhill. The final model uses signed shaft speed relative to the selected direction, with a native rollback regression. It also treats the authored positive torque curve as net crankshaft output instead of subtracting engine losses twice; modeled rundown drag applies when that output is zero. The failed report/log are retained as `drivetrain-clutch-first.json` and `.log`.

The second pass exposed a further low-range instability: a stiff speed-only clutch alternated large positive and negative torque against wheel speed sampled once per game frame. Synchronisation now contributes at most 30% of rated engine torque and softens with the square of the total gear ratio, alongside the existing engine output and clutch capacity. The second failed report/log are retained as `drivetrain-clutch-second.json` and `.log`.

Although the third pass passed its 145 checks, telemetry showed the softened clutch could leave engine RPM below forward shaft RPM in low range. The final implementation adds a kinematic back-drive speed floor blended with clutch engagement, preserving the existing wheel solver's speed constraint once engaged and passing overrun drag back to the shaft. The engine can still rev independently with the clutch open or slip above shaft speed while taking up drive. This hybrid coupling deliberately retains a simplified game model rather than solving engine, clutch, tyre and chassis inertias together inside Chaos. An additional live low-range RPM check now guards the observed lag. The third report/log are retained as `drivetrain-clutch-third.json` and `.log`.

Final validation: the editor build succeeded and **146 drivetrain checks passed with editor exit 0**, including the native regression case. All three packages free-rev past 4,500 RPM with the handbrake held, remain below 1 km/h, drop revs on lift, and progressively reconnect drive on release. Rolling handbrake/recovery, first-gear selection at a stop, ordinary acceleration/shifts, steering, low-friction and airborne recovery, reverse, light throttle, empty fuel, saved loadouts and BMW isolation passed. The low-range hill start climbed 12.6 m in five seconds at 40% pedal; high range rolled back 7.3 m. Player saves and the rally/LiDAR map assets were unchanged. Evidence: `Saved/WorkshopQA/drivetrain-clutch-final.json`, `.log`, and `drivetrain-clutch-integration.json` (source hashes and compact results). The previously recorded 205-check cosmetic/equipment suite was not rerun for this drivetrain-only change. Keyboard driving remains the feel acceptance test.
