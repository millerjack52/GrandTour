# Soft rut shoulders and patch boundary

2026-09-29. User requested less sharp/uniform deformation and removal of the visible boundary between live mud and landscape.

## Changes

`FGTMudField::StampWheel` cuts a smoothstep shoulder outside the tyre contact area instead of jumping straight from full depth to the raised bank. Nominal shoulder run is 45 cm, grows with deep sinkage (1.2 times depth), and varies along the stroke and between sides with deterministic noise. Firmer pockets reduce the requested depth by up to 35%, in addition to the existing small floor noise, so the rut no longer has a constant-depth floor. The raised bank starts outside that shoulder. Belly cuts have a 35 cm rounded feather. These shapes are in the CPU field used by traction as well as the rendered field; this is an authorized shape change, not just shading.

The wider stamp exposed old deposition/smoothing assumptions: subsequent banks and the trailing feather could refill an earlier compacted rut. Compacted bank cells are now preserved; shoulder cells do not receive core-floor slump, and a shallower trailing feather cannot smooth a deeper previous cut upward. Existing maximum sinkage and traction coefficients are unchanged, but the sampled field shape and therefore the forces it produces do change. The material retains more clay detail on steep walls and a little on worked floors.

The test landscape's clay apron previously blended only color. It now blends the same clay normal and roughness across the boundary, preserving the original ground shading beyond the apron. The live mesh's outer overlap lip is 0.1 cm instead of 1 cm; overlap and the landscape hole remain in place.

## Reproduce

Open `/Game/GrandTour/ArtTests/LiveMudDrive/L_MudDrive` and Play. Restart Play to clear old ruts.

```powershell
& 'C:/Program Files/Git/bin/bash.exe' Art/build.sh
& Art/mud_shape_test.ps1
& Art/setup_live_mud_drive.ps1
& Art/check_live_mud_drive.ps1
```

Before images/reports are preserved under `Art/Export/LiveMudDrive/BeforeSoftShoulders`. The driving check adds `Boundary_Dry.png` and `Mud_Long_Dry.png` to the existing cockpit and transverse rut views.

## Verification

Build and `GrandTour.Mud.SoftShoulders` passed. A requested 40 cm deep, 28 cm tyre test stroke measured a worst 12.5 cm transverse step of 14.94 cm, width at -5 cm varying 93.75–143.75 cm and core depths 25.94–40.78 cm (including the existing small floor noise). The test checks sloped walls, depth variation/bounds, deterministic results, finite/bounded repeated and crossing passes, untouched distant ground and the belly feather.

Rendered inspection: `Boundary_Dry.png` shows continuous clay detail across the tested approach boundary, without the earlier straight dark edge. `Mud_Long_Dry.png` shows rounded shoulders, varying width/depth and interrupted water pockets rather than a constant-depth trench. The dry route completed. On 2026-09-29 the wet replay timed out near 61.8 m because God of War started during the capture (about 14 fps); validation was then deferred at the user's request ("Save changes and previews; test later").

### Validation run, 2026-10-05 (no game or editor open; living mud plan stage LM0)

- Build exit 0; `GrandTour.Mud.SoftShoulders` PASS with the numbers above, unchanged.
- `Art/check_live_mud_drive.ps1`: report `ok: true`. Dry: 119.04 m in 60.5 s, max lateral 0.25 m, added 20,606,116 cm^3, wheel water up to 0.52 m. Wet replay: 119.01 m in 55.5 s, max lateral 0.30 m, added 12,087,515 cm^3, wheel water up to 0.49 m. Nine pictures rewritten in `Art/Export/LiveMudDrive` (not judged in this run). The wrapper still throws, because the editor exits -1073741819 after "Log file closed"; no crash dump or Windows fault event, so no stack.
- `Art/suite.sh terrain drivetrain grip mud surface track`: drivetrain, grip, mud, surface, track PASS. Terrain FAIL, twice, on the same three gates: stage H along-crest mean 4.45 cm (asked 5.35-9.94), stage I rut floor -23.6 cm (asked -28.0 within 15 %), and the ford raised 70 cm timed out with the engine running (asked: floods). The first two are old shape-specific expectations that this shape change moves; the ford one is not diagnosed. None was relaxed. The step 11 rut-exit gate passed both runs (held exit 1.12x / 1.31x the pass, gate 1.05x).
- Bog escape moved from forward 13.1 m / reverse 4.3 m (pre-L) to forward 8.9-9.1 m / reverse 6.0 m.
- Performance: the check profiles only the wet replay (editor PIE, viewport 951x257): mean game thread 19.76 ms, GPU 9.12 ms. Not a packaged benchmark; not comparable with the 2026-09-29 report (different viewport).
