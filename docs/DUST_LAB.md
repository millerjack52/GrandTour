# Isolated vehicle dust prototype

Started 2026-10-12. User approved the dust/mud plan and asked that Claude's work
in Gaea Benmore Review not be disturbed. This first milestone concerns dry dust.

## Isolation

- New `AGTDustLab` actor; no existing vehicle, spray, terrain, weather or water
  implementation is edited. No actor is added to Benmore.
- C++ was staged under `Art/DustLab/PendingSource` while the editor was occupied,
  then installed as five new Source files. Build mode promotes only those files under the shared mutex,
  after checking that any existing destination is byte-identical. This keeps
  Claude's builds from picking up unvalidated code during preparation.
- All new assets belong to `/Game/GrandTour/ArtTests/DustLab`.
- Setup copies `L_GravelDeform` into `L_DustLab`. Its existing terrain/spec
  references are read-only. Setup saves only the copied level and new assets.
- Each setup builds a new versioned Niagara package, avoiding the existing
  spray builder's known same-package rebuild issue. No shared asset is deleted.
- `Art/run_dust_lab.ps1` holds the existing GrandTour-BenmoreProfiling mutex,
  refuses to start alongside another Unreal/build process, and never terminates
  another session. Start with the Entry map, not the project's default map.
- The review suppresses original spray only in its own transient PIE session;
  it never saves those runtime overrides.
- A normal manual Play session still includes the car's existing spray. Use the
  Review command for the isolated comparison shown in the captures; integrating
  or replacing the production spray is a later step.

## Prototype behaviour

The actor reads existing per-wheel contact, surface tag, slip, tyre direction,
vehicle velocity and weather. Dirt and sand tags emit outside gravel patches;
gravel patches select a separate tint. It writes no physics or deformation data.

Three CPU Niagara emitters per emitting wheel, with dynamic bounds and world-space
particles:

| Layer | Lifetime | Purpose |
| --- | --- | --- |
| ContactDust | 0.6–1.3 s | Short, small tyre puffs |
| NearWake | 3.5–6 s | Growing clouds close behind the car |
| LingeringTrail | 7–12 s | Sparse expanding trail left along the driven path |

Velocity loses its initial throw through drag and approaches the weather wind
(default wind scale 0.35), with a gentle upward drift. These are starting values
for the prototype, subject to further art direction. The existing painterly
dust flipbook is copied, with private material lighting values and depth fading.
Particle tint is set at birth so a surface transition doesn't recolour old dust.

`gt.DustLab 0` or the actor's `bEnabled=false` stops emission; existing dust fades.
`Intensity` is clamped to 0–3. `WetnessOverride=-1` uses weather wetness; 0–1 is
available for this isolated test. Moisture suppresses dust completely at 0.6.
An idle or airborne wheel emits nothing. Rolling, wheelspin and braking slip
can disturb loose ground. Rates and lifetimes bound the population; this is not
a measured performance guarantee. Fully drained systems deactivate.

## Validation commands

Only after the shared Unreal/build slot is free:

1. `powershell -NoProfile -File Art/wait_unreal_free.ps1 -MaxMinutes 20`
2. `powershell -NoProfile -File Art/run_dust_lab.ps1 -Mode Build` (promote new files
   and build under the same shared reservation; no existing source is overwritten)
3. Repeat the free-slot check, then `powershell -NoProfile -File Art/run_dust_lab.ps1 -Mode Tests`
4. Repeat the free-slot check, then `powershell -NoProfile -File Art/run_dust_lab.ps1 -Mode Setup`
5. Repeat the free-slot check, then `powershell -NoProfile -File Art/run_dust_lab.ps1 -Mode Review`
6. `powershell -NoProfile -File Art/run_dust_lab.ps1 -Mode Verify` checks the saved
   private map, system assignment, and source-map actor inventory.

The review drives the real car on the copied test strip, captures chase, roadside
and elevated views, then suppresses emission with wetness and captures the trail
before and after expiry. It records contacts, gravel-patch flags, actual speed,
emission rate and live counts. Its fixed-step launch is for repeatability, not
performance measurement. No timings or FPS claims should be inferred from it.

`GrandTour.DustLab.Emission` covers idle, dry rolling, wheelspin, braking slip,
reverse symmetry, tarmac, wetness, airborne contact and extreme speed bounds.
Review gates additionally require actual particles on dirt and gravel, no wet
emission, survival of old particles after transition, and eventual expiry.

## Remaining scope

- Local terrain wetness beyond the weather value is not yet wired; do not infer
  puddle-level dryness from this first prototype.
- Mud, grit refinements, retained tyre mud, curved-route and surface-normal
  treatment, distance quality tiers and Benmore integration are later milestones.
- New C++ classes are opt-in but still require the project's shared DLL build;
  no build is allowed while Claude's editor is active.

## Current status

The editor build and `GrandTour.DustLab.Emission` automation test passed.
The private map is `/Game/GrandTour/ArtTests/DustLab/L_DustLab`. New Niagara,
material and atlas assets are authored in timestamped folders beneath DustLab.
The active version is recorded by `Art/Export/DustLab/setup-report.json` and
independently checked by `verify-report.json`. Actual rendered images and the
seven functional gates are recorded by `review-report.json`.
Content binaries are excluded by this repository's existing `.gitignore`; the
saved map/assets are local artifacts and can be rebuilt with Setup.

The launcher refusal was exercised while another Unreal editor was active.
No foreign editor or build process was terminated.

## Setup issue and recovery

Unreal's SaveMap wrote the initial copied level but left the source world open.
The first setup accidentally saved a DustLab actor into `L_GravelDeform`.
That actor was removed in a dedicated repair; the source map was reserialized,
so its binary hash differs from the baseline. Independent verification checks
zero DustLab actors in the source, one in the private map, and matching original
actor classes, transforms, meshes and materials (12 actors). This is a semantic
comparison against the copy made before installation, not a byte restoration.
Benmore was never edited. Setup now opens the private map in a fresh process
after creating a copy and checks the exact world path before changing actors.

Some early editor runs faulted during shutdown after producing reports; the
launcher treated those nonzero exits as failures. NullRHI authoring was also
rejected because Niagara reported not ready to run. Setup therefore requires
the rendering editor and a valid, runtime-ready Niagara compile. Final status
must use successful process exits as well as report contents.
The review now waits for PIE to end, releases its Python world/actor references,
then unloads the test map before requesting editor exit on a later frame.

## Final validation, 2026-10-12

- Build passed; emission automation: one test passed, zero failed.
- Setup passed with valid=1, ready=1, compile errors=0, warnings=0 and exit 0.
- Review passed all seven gates and exited 0 after the staged shutdown change.
  The elevated shot contained 649 live particles. Two seconds after stopping
  emission, 378 remained; by the final shot, zero remained. These are functional
  observations at this review speed, not a particle budget or performance result.
- Verify passed with exit 0: source has zero prototype actors, private has one,
  and all 12 baseline actor inventory entries match.
- Active system: `Build_20261012_155349/NS_DustLab`, inside the DustLab asset root.
- Final protected hashes match Benmore, shared spray assets, existing spray and
  traction source, and DefaultEngine.ini. The repaired gravel source-map binary
  is the exception described above.
- Visual review: continuous, softly expanding trail on dirt/gravel at roughly
  30–35 km/h. Mud and production integration remain outside this first milestone.

## Mud flick extension

`AGTMudFlickLab` is a second opt-in actor in the private `L_MudFlickLab` map,
copied from the existing LiveMudDrive strip. It does not change the dust map.
The three new runtime files join the five DustLab files in the guarded Build
list. The existing private authoring library gains `BuildMudFlick`.

The existing spray continues to own the large physical clumps, carried volume,
terrain deposits and vehicle splats. The new actor adds two cosmetic CPU Niagara
layers: irregular 3.5–12 cm flecks and 1.5–4.5 cm fine spatter. Both follow gravity,
have modest drag, finite 0.65–1.6 s lifetimes, and die on their first scene collision.
Their collision uses the scene mesh; it does not query the deformation field's
exact displaced height. Physical clumps retain their existing field collision.

Emission reads each wheel's actual mud-patch contact, tread speed, signed slip,
and the positive delta in accumulated thrown volume. It never spends or modifies
that volume. Airborne wheels, snow/gravel patches, idle tyres and locked wheels
cannot create new flicks. Reverse follows tread direction; braking slip cannot
create a reverse rooster tail. Colour is sampled from the patch variant at birth.
Rates are bounded and drained emitters deactivate. No performance budget has
been measured. Retained mud shedding outside a patch is still future work.

Run `Art/run_dust_lab.ps1` with `-Mode MudSetup`, `MudReview`, and `MudVerify`.
`-Mode Tests` now includes both dust and mud emission tests. MudReview suppresses
the original cosmetic mud/dust rates and original fine Niagara only in PIE,
while leaving volume-carrying clumps active. Normal manual Play still contains
the original cosmetic spray as well, pending production integration.

Mud setup compiled valid and runtime-ready with zero errors/warnings and exited
cleanly. Both `GrandTour.DustLab.Emission` and `GrandTour.DustLab.MudFlick` passed
(two succeeded, zero failed). Reports use the `mud-` prefix in `Art/Export/DustLab`.

The initial reverse review failed because setting Chaos's gear does not select
reverse in the custom drivetrain; the review now holds the brake input as a
driver would. A subsequent rendered review passed all six functional gates and
exited cleanly. Another capture passed those gates but hit an access violation
during editor shutdown. Staging EndPIE and editor exit reduced but did not
eliminate this intermittent problem; its cause is unresolved. The launcher still
rejects nonzero exits. The failed run is preserved in `mud-review-shutdown-failure.json`
and `MudReview-shutdown-failure.log`; successful particle checks alone must not
be interpreted as proof of a reliable editor shutdown.

Final mud drive review (16:10 local) passed all six gates and exited 0. The final
camera observes the sunlit side from inside the patch, on the -4.5 m test lane,
without changing lighting or obscuring the car with foreground grass. During
reverse the new system had 601 live particles; after cutoff there were 530, then
zero in the cleared shot. The existing system emitted 1,064 physical clumps and
recorded 1,061 landed by that last shot. This is a low-speed bog/crawl review,
not validation of a high-speed mud-water wall like the off-road references.
The shutdown issue remains recorded despite the final clean exit.

MudVerify passed with exit 0: zero prototype actors in the source, one in the
private copy, matching baseline actor classes/transforms/meshes/materials and
the saved `Mud_20261012_160314/NS_MudFlick` assignment. All 12 protected files
match their start-of-mud-phase hashes, including Benmore, both source maps,
the completed dust map, terrain settings, shared spray assets and vehicle code.

## Benmore integration (user requested after the isolated reviews)

`AGTVehicleSurfaceEffects` is a placed level coordinator. It discovers every
`AGTCarPawn` at 0.25 s intervals and gives each car a dedicated dust and mud actor,
including later spawns. Switching the possessed car does not change ownership.
Parked cars do not allocate Niagara components until there is something to emit.
Destroyed cars are retired; coordinator-owned effects never find a different
car on their own. `gt.SurfaceEffects 0` removes the replacement actors and restores
legacy cosmetic spray; `1` reinstates them. Other maps have no coordinator and
retain their original spray behaviour.

The dust driver now reads `bGravelSpray` and `DustTint` from wheel-contact physical
materials, as Benmore requires. It excludes muddy/snow patches and standing water
over 2.5 cm. Mud flicks also recognise Mud/Bog surface tags outside a deformation
patch, allowing authored wet ground to use the same cosmetic layer.

Two transient flags on `UGTSprayComponent` prevent duplicate cosmetic dust and
mud. The fine-layer driver suppresses only replaced dust/mud rates; gravel grit
is preserved. The old volumeless mud/dust spawn branch is suppressed on covered
surfaces. Volume-carrying clump creation/deposition, snow, water, steam, traction,
terrain generation and physical-material values are not edited.

BenmoreSetup snapshots all pre-existing actor names, classes, transforms, mesh
and material assignments and asserts they survive installation. It adds one
`Benmore_VehicleSurfaceEffects` actor. Standalone saved-map verification repeats
the comparison. The before-map binary is recorded in
`Art/Export/DustLab/benmore-backup.json`. Versioned production Niagara copies are
saved under `/Game/GrandTour/FX/VehicleSurface/Benmore_*`; their proven material
and atlas dependencies remain at the original DustLab asset paths.

Commands: `Art/run_dust_lab.ps1 -Mode BenmoreSetup`, `BenmoreReview`, and
`BenmoreVerify`; `Tests` covers emission, `SprayTests` checks the original spray
art and rendering-upload tests. Rendered integration review uses the actual
Benmore road/path queries and existing riverbed patches, without saving runtime
weather, vehicle positions, or camera changes. It is not a performance benchmark.

Installed into `L_Benmore_GaeaReview` on 2026-10-12 using
`/Game/GrandTour/FX/VehicleSurface/Benmore_20261012_162504/NS_DryDust` and
`NS_MudFlick`. BenmoreSetup and the final rendered BenmoreReview exited 0.
The review passed all ten gates across 13 runtime cars (12 placed plus the
player spawn), including disable/re-enable, one pair per car, no duplicate
cosmetic emission, retained gravel grit, wet-weather suppression and mud
emission on the existing crossing-profile riverbed.

The dry-road capture recorded 906 live dust particles; setting wetness to 1
stopped new emission while the existing trail continued fading. The riverbed
capture recorded 178 mud particles, with no dust or legacy cosmetic mud.
Screenshots and numeric evidence are in `Art/Export/DustLab/benmore-review-report.json`.
This functional capture used process-only graphics reductions and a fixed
1/30 s simulation step while another game was running. Saved Benmore graphics
settings were not changed; the captures do not establish performance or final
full-quality appearance. The intermittent shutdown issue from earlier lab runs
is not considered resolved by this clean exit.

`benmore-protected-after.json` checks the 12 previously protected files. Only
the authorized main-map save and two shared spray implementation files changed
in that set. The shared spray header also gained the two transient coordination
flags. Shared Niagara/material assets, traction code, engine config and the
earlier prototype/source maps retain their previous hashes. The exact original
main-map backup is `Art/Export/DustLab/BenmoreBackups/20261012_161744/L_Benmore_GaeaReview.umap`.

BenmoreVerify passed with exit 0 after initializing the saved editor world.
The 342-row installation baseline includes one renderer-only Chaos debug actor;
all remaining 341 actor rows match in names, classes, transforms and authored
mesh/material assignments, with exactly one additional effects coordinator.
The verifier excludes only that debug actor and the exact engine camera-icon
mesh/material pair. Camera actors themselves remain checked. Raw differences
are retained in `benmore-editor-helper-differences.json`. A package-only load
had initially returned uninitialized world transforms, so it was not a valid
comparison with the initialized setup baseline. No map edits were needed.

Final integration validation: the editor target built successfully; both
`GrandTour.DustLab` tests and both existing `GrandTour.Spray` tests passed with
zero warnings/failures and clean process exits. The saved-map verifier and all
ten rendered integration gates passed. Open Gaea Benmore and Play to use the
effects automatically. `gt.SurfaceEffects 0` restores legacy spray for comparison;
`gt.SurfaceEffects 1` re-enables the new dust/mud systems.
