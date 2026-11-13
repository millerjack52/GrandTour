# Landscape surface prototype (architecture A)

Owner handoff, 2026-10-12. Terrain/surface ownership is Codex; driving physics remains Claude's.
Benmore triage landed as `1ff26f7`. This prototype never loads or saves Benmore and does not
change its gravel POM, physical materials, dust, vegetation, river, creek or lake.

## Review location and status

Map: `/Game/GrandTour/ArtTests/LandscapeSurface/L_LandscapeSurfacePrototype`.
One 31.5 m landscape component, Nanite with skirts, one material. No patch meshes, holes or scatter.
The paint has a mud lane that blends into gravel and then firm ground. The editor camera is 1.6 m high.

This is the small-area prototype gate, **not a rollout to Benmore**. Visual acceptance and performance
remain pending. Broad tests and automated drives are skipped at the owner's request; the owner's report
of spikes/holes prompted a targeted rendered reproduction and repair capture.
The editor C++ build succeeded and setup created/saved the map, material and paint texture. Its log
confirms the Nanite mesh build completed and contains no material compilation errors. These are setup
checks, not evidence of runtime correctness or visual quality.
The lab's wet soil treatment is provisional; gravel reuses the existing Benmore Fine/LooseGravel assets.
The old `L_MudVariants`, `L_GravelDeform` and `L_MudDrive` strips remain unchanged on the legacy patch path.

Build with the shared guard, each command separately:

```powershell
powershell -NoProfile -File Art/wait_unreal_free.ps1
powershell -NoProfile -File Art/build_guarded.ps1
powershell -NoProfile -File Art/wait_unreal_free.ps1
powershell -NoProfile -File Art/setup_landscape_surface_prototype.ps1
```

Setup refuses to overwrite an existing prototype map/material. It writes only prototype assets and
`Art/Export/LandscapeSurface/setup-report.json`; the project's content binaries are deliberately not in Git.
Launch the prototype with these CVars (setup uses them for its process; it does not modify shared config):

```text
r.Nanite.Tessellation 1
r.Nanite.ProgrammableRaster 1
r.Nanite.ComputeRasterization 1
landscape.Nanite.LiveRebuildOnModification 0
```

Keep live rebuilding off. The new landscape is registered before its first save builds Nanite data.
Epic documents that Nanite landscape displacement needs current Nanite data and that Nanite keeps both
landscape representations resident: [Using Nanite with Landscapes](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-nanite-with-landscapes-in-unreal-engine).
Do not increase the global streaming pool to hide the previous always-resident memory warning.

## Data and material

`FGTLandscapeSurfaceField` is a separate bounded prototype field. It does not alter the legacy
`FGTMudField`, whose wide shoulder/relaxation defaults must remain compatible with the old strips and snow.

- 6.25 cm cells, 256 x 256 per 16 m world tile; nine active tiles in a 48 m window.
- Sparse LRU CPU cache, conservatively bounded to 128 MiB including an overhead allowance. Evicted tracks
  are lost; this is not save-game persistence. Cells have signed height delta, XY slide, track blend,
  freshness and turbidity. Cached inactive cells freeze until reactivated.
- Painted mud initializes with deterministic fragments and slabs, approximately 24–180 cm across, plus
  broader unevenness. Rest heights are bounded to -12..+12 cm and fade with painted thickness. The
  initial relief is authored terrain mass; excavation/deposition counters measure subsequent wheel
  changes only. Regenerated tiles restore the same relief, rather than changing random shape.
- Two 768 x 768 bilinear RGBA16f textures, approximately 9 MiB combined, uploaded at up to 20 Hz.
  Full-window upload is intentionally the prototype baseline; owner measurement determines whether it
  needs dirty rectangles or a GPU field. There is a one-metre displacement fade at the moving window rim.
- The ordinary landscape's collision represents the original surface. At a painted cell, firm base is
  `original surface - painted mud thickness`; current mud height above that base is `thickness + delta`.
  Thus existing landscape heights need no destructive rebake. The normalized displacement output is
  `(delta + 50) / 65`, with **local-space magnitude `65 / uniform landscape scale`** and centre `50/65`.
  The prototype uses uniform scale 50, so its material magnitude is 1.3 local units, giving -50..+15
  world cm bounds. Do not put 65 in the material magnitude: Nanite applies object scale afterward.
- Cuts stay inside the tyre footprint; there is no shoulder digging or lateral diffusion. Removed volume
  is allocated to adjacent painted mud lips. If their bounded capacity is exhausted, further excavation
  stops instead of destroying material or spreading a moat. Repeated stamps use an absolute target depth.
- Water requires a negative hollow below the authored water table, capped at 6 cm fill. Five wave layers
  supply sub-centimetre geometric motion and normals. Bilinear samples, muddy foam/turbidity, water
  specular 0.055 and roughness 0.56 restrain the bright grazing highlight.
- Rut water is an opaque turbid surface within the same landscape material; this prototype does not
  implement transparent water, refraction, flow transport or a second water simulation.
- Gravel geometry is unchanged. Existing `UGTTrackPaintSubsystem` R supplies swept/compacted line and
  neighbouring loose aggregate shading. The fine and coarse gravel texture remains visible on the line;
  no sand-coloured replacement trench, geometric berm, or scatter is created.
- Runtime textures bind to both ordinary landscape MIDs and Nanite component MIDs. UE 5.8's
  `SetLandscapeMaterialTextureParameterValue` only updates ordinary landscape components.
- The deforming landscape uses `ShadowCacheInvalidationBehavior=Always`. Texture uploads do not
  change its transform or advertise WPO, so automatic virtual-shadow invalidation otherwise retains
  the original flat-ground shadow inside freshly cut ruts. This is local to the prototype's components;
  global shadow caching and hardware Lumen remain enabled. The cost of this necessary invalidation
  must be included in the owner's prototype measurements before any larger rollout.

`GTLandscapeSurfaceSetupLibrary::ConnectDisplacement` connects the hidden displacement property from C++.
It accepts the uniform landscape scale and converts the desired world range to local units. Runtime
checks each Nanite component's transform and material magnitude; it disables displacement with an error
if the product is not 65 world cm or the transform is nonuniform. Transient field textures start with
explicitly zeroed pixels, and displacement exits at the neutral value until its field is ready.
`ImportPaint` reads the same source texels used by the material into serialized CPU paint, so gameplay
does not attempt a GPU readback. The import accepts square BGRA8 source images up to 2048 pixels:

| Channel | Meaning |
| --- | --- |
| R | thickness / 50 cm; 0 = firm; authored interiors normally 10–50 cm, feather to 0 at joins |
| G | water table depth below original surface / 50 cm; material and CPU decode negative cm |
| B | gravel coverage, 0–1 |
| A | mud softness, 0–1 |

Texture requirements: linear, uncompressed vector-displacement setting, no mipmaps, bilinear filtering,
clamp addressing. The perimeter must have zero R/B. `PaintOriginCm` is the minimum world XY corner;
`PaintSizeCm` is square extent. The importer enables Gaea exports or manually painted textures, but this
prototype **does not yet import Benmore's Gaea masks or live Landscape paint layers**. Reimport the texture
and call `ImportPaint` again after authoring; CPU paint must never lag the GPU image.

## Physics handoff (additive; no traction code changed)

`AGTLandscapeSurface::QuerySurface(WorldContext, WorldXY)` returns `FGTLandscapeSurfaceSample`:

| Member | Units / contract |
| --- | --- |
| bAuthored | false means retain the existing physical-material/legacy query |
| SinkageCapCm | finite painted thickness, zero for gravel/firm |
| SinkageRateCmPerS | prototype rate from softness; Claude can calibrate the consumer |
| FrictionScale | multiplier; mud 0.70–0.95, gravel swept line 0.90–1.00 |
| Softness | 0–1 |
| WaterDepthCm | standing rut water above mud, max 6 cm |
| MudHeightAboveBaseCm | nonnegative mud remaining above firm base, including lips |
| SurfaceDeltaCm | total signed height from collision/original surface, including initial clods and hollows |
| SurfaceTag | FName: `Mud`, `Gravel`, `FirmGround`; these are not registered GameplayTags |

Write seam: `StampWheel(StartXY, EndXY, TyreHeading, WidthCm, AbsoluteDepthCm)`.
Coordinates and widths are centimetres; heading is normalized internally. Stamps outside active tiles
are ignored. The actor focuses on the player by default before observing contacts.

Until Claude integrates this seam, `bObservePlayerWheels=true` reads the player's existing contact points,
tyre widths and slip after physics and produces a **visual-only** sink target. It does not change forces,
wheel radii, grip, suspension or legacy patch queries. Visual ruts therefore do not yet give correct
wheel sinkage. Disable this observer when the physics owner starts sending `StampWheel`, to avoid double
stamping. The gravel query reads the existing track paint for grip, but that multiplier is not applied
to traction until the seam is consumed. Only one non-overlapping prototype actor per painted area.

## Owner review gate

Drive a pass, get stuck and spin, then repeat the same pass. Inspect on foot at 1.6 m, toward the sun,
across the mud/gravel/firm blends and across x=0/y=0 tile boundaries. `ApplyReviewTracks()` is an explicit
optional fixture for two tyre-width passes and a stationary spin; setup does not run it automatically.
`GetSurfaceReport()` exposes cached tile count, evictions, volume counters and bound Nanite materials.
The material scalar `GTLS_DisplacementEnabled` allows geometry on/off comparison.

Owner measurements needed before Benmore integration: frame cost of tessellation and uploads, memory
residency, stable Nanite rendering, repeat-pass width/depth and lip volume, water glare toward the sun,
and continuous joins. No claim of visual approval or performance improvement is made by setup.

After that gate: connect Claude's consumer, choose/paint Benmore masks, tune against the owner's angles,
then install the material on Benmore with the timestamp-before-save check. Legacy strips can be retired
only after the replacement has been reviewed.

## Repair of the initial spike/hole failure

The initial setup in `77e6ead` was incorrect: magnitude 65 was authored as though Nanite displaced in world
centimetres. The landscape had scale (50,50,100), so its vertical displacement could be amplified 100x.
The owner observed towering walls and holes. Compilation and a saved Nanite mesh were insufficient
validation; the first runtime render should have been inspected before handoff.

Epic documents local-space displacement before object scale in
[Working with Nanite-enabled content](https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content).
The prototype also avoids the nonuniform landscape scaling problem documented in
[UE-367789](https://issues.unrealengine.com/issue/UE-367789) by using uniform scale 50. Its flat base remains
at the same height and its XY extent is unchanged.

After the editor build, run the shared wait command on its own, then
`powershell -NoProfile -File Art/setup_landscape_surface_prototype.ps1 -RepairAndCapture`.
This repairs only the existing prototype material/landscape, keeps a binary backup under Saved, checks
timestamps before saves, and captures a baseline plus repeat-pass/spin fixture from 1.6 m at the track,
surface join and toward the sun. It writes `Art/Export/LandscapeSurface/repair-report.json` and images.
This checks the reported rendering failure, not driving integration or performance.

The first scale-corrected capture still had black cuts. Unlit/triangle captures showed continuous terrain.
Switching hardware Lumen off initially appeared to cure them, but individual ray-tracing passes and
component exclusions did not. That switch also rebuilds rendering state. A fresh virtual-shadow cache
removed the cuts while hardware Lumen stayed on: the old flat-ground shadow was covering the new ruts.
The repair marks the deforming landscape's shadow cache for continuous invalidation; no ray-tracing
exclusion, global lighting downgrade, budget increase or warning suppression is used.

`-DiagnoseCuts` adds temporary cache/viewmode comparisons to the capture process. Those diagnostic
images must not be substituted for the default captures when judging the shipped settings. Two earlier
diagnostic processes exited with an access violation after completing captures and normal log shutdown;
the capture script now lets EndPIE finish before requesting editor exit.

Final repair validation: editor C++ build succeeded; the default four-capture run completed with exit
code 0. Its runtime report confirms uniform scale 50, local magnitude 1.3, displacement scale valid,
hardware Lumen 1, global virtual-shadow cache 1, and the Nanite component's invalidation set to Always.
The foot, join and sun captures no longer show the towering geometry/sky holes or the previous cached
black bands. The smooth soil, straight fixture ruts and lip shape still need visual development; this
repair is not owner approval of the material or a performance result.

## MudRunner reference surface pass

The owner's three screenshots establish the art target: irregular clumps and compressed hollows in
photos 1/3, and shallow water between raised mud banks in photo 2. They are visual references, not
evidence of how the reference game's renderer implements each shape.

The prototype now starts with seeded, world-aligned clods, broad hollows and areas of lower relief.
Wheels compress this existing height field into a slightly uneven floor; lip capacity varies along
the bank, creating separate raised lumps while retaining the volume allocation and finite-depth limit.
Initial relief fades out with the mud paint. Gravel still has no geometric displacement.

The material adds subdued grey/olive/brown variation, darker hollows, fractured grain and brighter
exposed clods. Small shader relief stays below a centimetre and fades on compressed tracks and under
water. This cosmetic microrelief is not part of the CPU physics query. Water normals use the combined
mud-plus-fill height gradient and layered waves, and sparse foam appears only after disturbance.

The physics interface signatures are unchanged. `SurfaceDeltaCm` and `MudHeightAboveBaseCm` now report
the initial uneven surface as well as wheel changes; they are no longer flat before the first wheel
stamp. Driving forces and the physics consumer remain outside this change. Initial clods are authored
mass, so the conservation counters intentionally start at zero before wheel excavation.

The first rendered iteration was too uniformly clumpy. The second introduces 2–3 m variations in
churn strength and reduces the water highlight. The same straight repeat-pass/spin fixture and camera
positions are retained for comparison; this fixture deliberately does not conceal straight rut edges
with a more flattering drive path. Before-pass images are retained as `before_art_*.png` in the export
folder. Performance and owner visual acceptance remain pending.

Validation: the editor C++ build and Python syntax checks passed. Both art iterations were inspected
in actual runtime captures, including the mud/gravel blend and grazing sun. The final fresh launch
completed all four captures and exited 0 with hardware Lumen and global shadow caching enabled.
Copies are `reference_pass_baseline.png`, `reference_pass_foot.png`, `reference_pass_join.png` and
`reference_pass_sun.png` under `Art/Export/LandscapeSurface`, with `reference-pass-report.json`.
The preceding run saved every capture but again exited with -1073741819 during teardown after the
normal shutdown log. Delaying EndPIE did not eliminate that intermittent editor-exit issue; its log is
retained at `Saved/Logs/LandscapeSurfaceArt-shutdown-error.log`. No broad tests or benchmark were run.

## Clump revision after owner feedback

The owner found the reference pass too uniform, reading as waves of dirt instead of clumps. Rest relief
now uses sparse rotated blocks with broad tilted crowns, clipped corners and short bevels. Two size
groups and density variation leave areas of compacted ground between clumps. Density is evaluated at
each clump centre, so occupancy cannot change partway across a shape. Clumps combine by maximum height
rather than adding overlapping dome tails. Lip capacity has actual gaps along the rut, while retaining
the same 31.25 cm minimum bank width, +15 cm height cap and excavation/deposition allocation.

Continuous ridged microrelief has been replaced with scattered small chips. Its normal strength is
reduced so surface grain does not hide the larger shapes. The first capture of this revision still
rounded the clumps into mounds on the 12.5 cm field. The field is now 6.25 cm, preserving the 16 m tiles
and 48 m active window, with broader crowns and a shorter normal sampling distance.

This resolution change quadruples active cell count, per-tile payload and full-window texture upload
bytes. The two textures grow from 2.25 to 9 MiB; their maximum raw upload rate grows from 45 to 180 MiB/s
at 20 Hz, before overhead. The 128 MiB CPU cache cap is unchanged, so fewer historical tiles fit.
These are calculated data sizes, not measured frame times. Owner performance measurement and visual
acceptance remain pending; no global memory pool or rendering budget is increased.

Validation: editor C++ build succeeded. The fresh runtime run completed all four captures and exited 0.
Baseline, foot, gravel join and grazing-sun images were inspected; broad crowns and separated clods
are visible, with no towering displacement or sky holes. The soil texture still reads softer than the
reference. Hardware Lumen and global shadow caching remain enabled, with local Always invalidation.
The report confirms the displacement scale guard is valid; excavation and deposit counters agree,
which is not an independent volume measurement. No benchmark or broad test suite was run.
Review images are `clump_revision_baseline.png`, `clump_revision_foot.png`, `clump_revision_join.png`
and `clump_revision_sun.png`, with `clump-revision-report.json`, in `Art/Export/LandscapeSurface`.
The previous surface is retained in `before_clump_revision_*.png` for comparison.

## Rut and clump variation revision

The owner judged both the clumps and ruts too uniform in `2ddee08`. The three supplied MudRunner images
remain the comparison target: mixed fragment sizes and torn masses in photos 1/3, and broken muddy
ridges with intermittent water pockets in photo 2. The previous flat crowns repeated too visibly.

Rest relief now varies fragment aspect, size, height, crown slope and bevel independently. Larger
slabs mix with small fragments; some split across a fracture. World-space warping distorts outlines,
and stronger density variation forms clusters and open patches. Lower fragments no longer all rise
to the same prominent cap: a smooth compression bounds high crowns without clipping them flat. The
world-space pattern remains deterministic across tile reloads. A first rendered revision was too
sparse and left pointed bank deposits; broader overlapping fragments and wider deposit crowns replace it.

Rut target depth now varies substantially with world-stable soil patches and smaller floor detail.
Their edges vary inward within the wheel footprint, and edge cells blend towards the authored soil
height. This leaves shallow sections between deep pockets without moving the wheel path. Deposition
has sparse gaps and a varying cross-section with broad crowns instead of a repeated sine profile. The original
straight repeated-pass fixture is unchanged, so camera comparisons expose the actual surface change.
Excavation still stops at the finite base or available deposition capacity, with every removed volume
allocated to the lips. Query signatures and driving forces are unchanged; sampled terrain heights
reflect this revised relief and rut response. Grid size and memory budgets are unchanged this pass.

Validation: both C++ iterations built successfully. The first captured run exited 0. The final run
wrote all four images and a successful capture report, with valid displacement scale, hardware Lumen
and global shadow caching enabled. It then exited -1073741819 after the normal shutdown/log-close
sequence, as seen on earlier revisions. This is not a clean runtime-run pass. Its log is preserved at
`Saved/Logs/LandscapeSurfaceVariation-shutdown-error.log`. No broad tests or performance benchmark ran.

Baseline, foot, join and sun images were inspected directly against the three supplied references.
The final shapes have more size/aspect variation and broader torn masses; rut banks vary in height
and continuity. The straight test paths remain apparent and fine material definition still falls
short of the reference. Owner visual acceptance remains pending. Review captures are `variation_*.png`
and `variation-report.json` in `Art/Export/LandscapeSurface`; `before_variation_*.png` retains the previous
committed appearance. The report's matching excavation/deposition counters are not an independent
volume check, and its `ok` field describes capture completion rather than editor process exit.

## Mud type, depth and moisture comparison

The separate `/Game/GrandTour/ArtTests/LandscapeMudVariants/L_LandscapeMudVariants` map contains six
labelled regions on one landscape. Open that map and Play for fresh, driveable surfaces; the capture
fixture's tracks are runtime changes and are not baked into the saved map.

| Surface | Available layer | Character |
|---|---:|---|
| Dry compacted loam | 10 cm | Low relief, small impressions, low softness |
| Damp loam | 10 cm | Softer response, small broken clods |
| Dry clay crust | 30 cm | Connected flatter plates, narrow irregular fissures, shallow cuts |
| Wet sticky clay | 30 cm | Larger cohesive forms, broad banks, deeper cuts, local water pockets |
| Dry churned soil | 20 cm | Mixed fragments, interrupted edges, moderate sinkage |
| Deep saturated mud | 50 cm | Lower initial relief, deep channels, shallow standing water |

Layer depth is a finite thickness, not a promised wheel penetration. Paint retains depth, water-table
depth and softness. `MudRegions` adds independent wetness, cohesion, relief and fragment scale;
wetness no longer follows paint softness in the variant material. Cohesion changes fragment size,
fracture continuity, floor variation and bank continuity. Dry cohesive soil uses nearest-feature
boundaries to produce plates with fissures. This is heightfield relief, not detached moving chunks
or a simulated fracture system. Region rectangles sit outside each fading mud pad; overlapping
regions use the first match. Edit character before Play; rest heights initialize when tiles load.

The saved presets and fixture are in `Art/Unreal/review_landscape_mud_variants.py`. Run the Unreal
availability guard as its own command, then `Art/setup_landscape_surface_prototype.ps1 -MudVariants`.
On first use this creates the map/material/paint; later runs load the existing assets without
overwriting manual edits. Changing script preset values alone does not update an already saved map.
The fixture applies matching 28 cm wheel sweeps, two nominal pressure stages scaled by each preset's
softness, and one repeated stationary stamp. It is an art comparison, not a vehicle force benchmark.

Review: `Art/Export/LandscapeSurface/mud-variants.html`, thirteen `mud_*.png` images and
`variants-report.json`. The final C++ build passed, Python syntax was checked, and the final capture
run produced all thirteen fresh images and exited 0. The displacement scale guard remained valid.
The final report has matching excavation/deposition counters (1,134,114.157 cm3 each); this is not
an independent volume measurement. Sample offsets include initial relief. Water stays capped at
6 cm; queried dry regions contain no water. No performance benchmark or broad test suite ran.

All six after images, the revised dry-clay before image and overview were inspected. The presets
are visibly distinct, but wet banks remain too continuous and the surface still lacks the authored
slumped masses and separate chunk detail identified in `TERRAIN_SURFACES_RESEARCH.md`. These variants
are a reviewable character study, not a claim that the MudRunner shape target has been reached.
Driving-force code and Benmore assets were not edited. Generated Unreal assets remain local under
the repository's existing Content ignore policy; the setup script is the reproducible source.

## Slumped-bank construction revision (2026-10-13)

The variant delivery stopped with a known shape defect. This continuation replaces the actual bank
construction, rather than treating that defect as a completed result. The owner's three MudRunner
references are included in the local gallery alongside previous/revised images from the same cameras.

The previous 31.25 cm deposit strip tended to normalize each short slice into a continuous ridge.
Three explicitly shaped profiles now provide low sheared sheets, folded slabs and torn wedges. Their
crowns have asymmetric slopes, bevels, folds and notches. Independent placements on opposite banks
vary length, breadth, height and gaps. Cohesive rest relief also uses these profiles, while crumbly
soil retains the fragmented construction and dry clay retains its plate fissures.

The plain clay view also exposed an incorrect aspect ratio in the old fragments: the largest wet
forms could exceed a metre in radius but had only a few centimetres of crown relief. Base fragment
radii are now 8-19 cm and 18-38 cm before each preset's scale/cohesion adjustment, with denser placement
at 32/75 cm spacing. Crown compression uses a smooth exponential approaching 12 cm, preserving taller
individual clumps without flattening them against one common cap. Broader deposited sheets remain
separate from this smaller rest-fragment scale.
The first smaller-fragment render exposed pointed bumps in the dry soil where too few cells covered
a crown. Height now fades for under-resolved fragments (8-24 cm radius), dry bevels retain broader
tops, and fracture splitting is limited to fragments above 30 cm radius. Smaller pieces read as
embedded crumbs instead of full-height, single-vertex peaks. The simulation grid is unchanged.

Displaced soil can occupy a 55-90 cm shoulder (depending on cohesion), extending 45 cm behind and
95 cm ahead of the contact for allocation. The longitudinal weighting allows volume to accumulate
in neighbouring slabs instead of depositing the same amount into each short slice. A bounded forward
push profile can accept material ahead of the tyre. All of this is deposition: cuts remain inside
the tyre footprint, with a curved cross-section and varied target floor depth. Existing track cells
do not receive side-bank deposits. Every deposited amount still comes from excavation; finite base,
15 cm lip cap, 6 cm water fill limit and allocation limited by available capacity remain in force.
This is a heightfield approximation of shearing and piling, not rigid clods or a physical soil solver.

The variant material reduces unrelated colour blotches and wet microchips so the folds remain legible.
Large colour variation follows height more strongly. Wet soil roughness is lower; the existing muted
water specular/roughness settings are unchanged. The review script refreshes only its variant material
from the source shader, with a timestamp check and backup under `Saved/LandscapeMudVariants`. It does
not overwrite the saved map/paint. This supersedes the earlier statement that every existing asset
is loaded without modification. Other maps and materials are not saved by this review script.

There are now nineteen captures: the six matching before/after pairs and overview, plus plain clay
geometry views for wet clay and saturated mud, curved/crossed tracks in colour and clay, the opposite
viewing direction, and the mud/firm-ground join. `GTLS_ClayReview` defaults to zero and is set only on
runtime material instances for the diagnostic views. Geometry, lighting and camera height stay the
same when switching to clay. The curved pass is an additional art fixture, not the straight control.
Previous bank images are kept under `Art/Export/LandscapeSurface/before_slumped_banks`.
The larger deposition neighbourhood increases stamp work; performance remains for the owner to
measure. No simulation textures, global rendering budgets or driving-force interfaces were added.

Validation: the final C++ build succeeded; both Python files pass syntax parsing. All nineteen final
captures were written, the report is successful, and the final editor process exited 0. Wet and dry
before/after surfaces, clay geometry, curved/crossed tracks, opposite lighting and the firm join were
inspected. Tall continuous deposit ridges are replaced by lower interrupted sheets; smaller clumps
have a more appropriate height/footprint ratio, and the wet highlight reveals the folds. The report
confirms valid displacement scaling, zero queried water on dry presets, at most 6 cm water on wet
presets, and matching cumulative excavation/deposition counters (697,493.663 cm3 for the straight
fixture; 978,459.945 cm3 after crossing passes). Those counters are not an independent volume check.
An earlier iteration saved its captures but exited -1073741819 during shutdown after log close;
its log remains `Saved/Logs/LandscapeMudVariants-shutdown-error.log`. The final clean exit does not
establish that intermittent engine-exit fault is fixed. No broad tests or performance benchmark ran.
The gallery is a direct visual review, not a claim of feature parity with MudRunner's separate chunk,
tread and particle systems. The current 6.25 cm heightfield still limits fine fracture silhouettes.


## Scanned rest shapes and parallax revision (2026-10-13)

The owner rejected the previous procedural shapes again. This revision changes their source,
rather than adding noise to the same slab/mesa construction. In the isolated six-variant map,
real scanned height data now initializes the CPU mud surface. Other surface actors retain the
previous construction unless the optional rest-height data is explicitly imported.

Sources are Poly Haven's CC0 [Brown Mud 02](https://polyhaven.com/a/brown_mud_02) and
[Mud Cracked Dry 03](https://polyhaven.com/a/mud_cracked_dry_03). Ten unchanged 2K maps supply
colour, displacement, DirectX normals, roughness and ambient occlusion. URLs and published
checksums are in `Art/Textures/LandscapeMudPBR/provenance.json`; run
`python Art/tools/fetch_landscape_mud_pbr.py` to recover the ignored source binaries.
These are coherent scanned map sets, not independently generated albedo/height approximations.

`ImportRestHeights` box-filters source heights into two serialized 32x32 linear arrays, supporting
G8, G16 and BGRA8 sources. The first 256x256 import aliased fine grit into spiky CPU terrain;
32 samples across the 260 cm wet tile filters below the 6.25 cm field's useful detail scale.
Dry clay uses a 180 cm tile. Bilinear periodic sampling also handles negative world coordinates.
The arrays occupy 8 KiB of float payload per actor. No editor texture-source access is required
at runtime. This is not a change to the field's resolution, streaming window or memory budget.

Rest heights use the existing region relief strength: compact loam .2, damp loam .65, dry clay .5,
wet clay 1.0, crumbly soil .85, saturated bog .4. The wet scan is centred at .62 and scaled by
45 cm before region strength and the existing -12/+12 cm rest bounds; dry crust is centred at
.55 and scaled by 8 cm. Depth/softness/wetness select the dry crust blend. These are art calibration
values, not measured soil constants. The rest surface participates in tile initialization and
bank capacity, so cutting these clumps uses the existing conserved-volume allocation. The query
interface, finite painted thickness, tyre width, 15 cm lip limit and 6 cm water limit are unchanged.
No driving-force code is edited.

The material installer is `Art/Unreal/landscape_mud_pbr.py`. Its shared parallax coordinate node
uses the matching height maps, 12-24 ray steps with interpolation, a 2.5 cm visual range, distance
fade from 10 to 22 m and a grazing-angle fade. Colour, normal, roughness and occlusion use those
same coordinates. POM fades out in pools and is reduced in compressed tracks. It does not write
pixel depth offset or change physical terrain height. A separate bounded 2 cm full-range scan
layer supplies fine Nanite relief; the larger shape is already in the CPU field. Thus terrain
queries can differ from the visible microrelief by up to 1.24 cm, before parallax's visual illusion.
Normals combine the field gradient with scanned surface normals and the existing water waves.
Clay review strips scanned colour, detail normals and AO while retaining geometry. Wet roughness
and specular were adjusted using the toward-sun view to avoid the first iteration's excessive glare.

The review installer backs up and refreshes only its own material and map. It explicitly updates
region relief and imports the serialized heights even when the study map already exists. This
supersedes earlier statements that existing region values are never updated. Source textures and
Unreal assets remain local under the existing binary ignore policy. No Benmore map is saved.

The gallery includes the owner's three references, pre-PBR comparisons, all six before/after
pairs, clay views, the join, opposite light, curved passes, a shallower 10 cm pass, a worked lane,
close POM off/on and overcast views. The worked lane adds four wandering 48 cm truck-width paths;
observed vehicle tyre dimensions are unchanged. The original 28 cm deep control remains a stress
fixture. These captures compare art and deformation; they are not a vehicle performance benchmark.

Validation: both targeted C++ builds succeeded (the final log is
`Saved/Logs/build_landscape_scan_filtered.txt`). Three Python sources parse; all ten downloaded
maps pass their manifest checksums. The final run saved 26 fresh captures, returned `ok: true`
and exited 0 (`Saved/Logs/mud_pbr_pass7.txt`). Its log has no material compile or Python errors.
Dry, damp, wet and saturated views, geometry-only views, opposite light, close parallax, overcast
and the finite study boundary were visually inspected across the iterations. The filtered scan
removed the first import's spiky sampling; before-PBR and before-CPU-scan images remain available.
The final report retains valid displacement scaling and matching cumulative excavation/deposition
counters: 927,152.582 cm3 after straight passes, 1,297,076.960 cm3 after curved passes and
1,841,353.691 cm3 after the worked lane. These counters are not independent volume measurements.
Queried dry areas have zero water; queried wet clay/bog water stays at or below 6 cm. No broad
tests or performance benchmark ran. Early material iterations again hit the existing
-1073741819 editor-exit issue (wrapper logs `mud_pbr_pass1.txt` and `mud_pbr_pass2.txt`); subsequent
clean exits do not establish that unrelated intermittent shutdown problem is fixed.

The current result combines scanned continuous terrain and material relief. It does not implement
MudRunner's separate rigid chunks, undercuts or tread/particle systems. Exact microrelief collision
is still outside the landscape displacement architecture; the shared terrain query remains the
source for sinkage. The saved review is for judging the shape/material against the supplied photos.

## Dressed forest-track study (2026-10-13)

The next review is `/Game/GrandTour/ArtTests/LandscapeMudScene/L_LandscapeMudScene`.
It puts the approved scanned mud into a short worn forest track with a wetter basin, firm grass
shoulders, embedded stones, loose pebbles, twigs, branches, leaf litter and three fallen logs.
The 63 m landscape is still one surface, with uniform scale 100 and corrected material displacement
scale. Its central 31.5 m paint window contains a roughly 22 m worked lane; this is a composition
study, not a complete route. Existing project meshes supply the dressing. Scene-local material
copies mute the trees, shrubs and logs without changing their shared source assets.

`AGTMudDetailStudy` is an opt-in art fixture. It seeds three varying-depth passes through the
existing wheel-stamp interface at Play, then updates small debris every half second from
`SampleSurface`. Leaves use the water surface when submerged; larger pieces sample additional
supports along local X to bridge small hollows. This changes their vertical placement only:
there is no rigid-body motion, tyre pushing, physical floating or rotation to match the ground.
Small debris has no collision. Trees and logs use their existing mesh collision. The saved map
keeps player-wheel observation enabled for further deformation; screenshot-only changes happen
in PIE. No traction, drivetrain, suspension or terrain-query interfaces were changed.

Run `powershell -NoProfile -File Art/wait_unreal_free.ps1 -MaxMinutes 0` as its own command,
then `powershell -NoProfile -File Art/setup_landscape_mud_scene.ps1`. The installer refreshes
only its dedicated generated actors, scene paint and materials, backing up the existing map
under `Saved/LandscapeMudScene`. It requires the earlier scanned mud variants and referenced
project dressing assets. Unreal binaries and images remain local under the repository ignore
policy. No Benmore map is saved.

Review `Art/Export/LandscapeMudScene/mud-scene.html`: approach, debris, puddle, reverse,
low detail and overview. The first canopy pass remains in `first_canopy` for comparison.
The first render exposed excessive canopy shadow and orange grass; subsequent passes opened
the trees, muted the verge and forest palette, and strengthened branch visibility.

The targeted C++ build passed (`Saved/Logs/build_mud_detail_study.txt`). Visual capture and
surface-report results are recorded in `Art/Export/LandscapeMudScene/scene-report.json`.
Performance is not measured. The capture log reports a non-Nanite virtual-shadow-map marking
queue overflow, so shadow cost remains an owner profiling item before production integration.
All six final images were saved and the report returned `ok: true`, valid displacement scaling
and matching excavation/deposition counters of 1,408,903.135 cm3. These are cumulative counters,
not an independent volume measurement. The final run (`Saved/Logs/mud_scene_pass4.txt`) encountered
the existing -1073741819 editor shutdown error after the captures and log close. Pass 3 exited
cleanly; that does not establish that the intermittent engine-exit issue is fixed.

## Benmore material integration (2026-10-13)

The approved wet mud and dry crust scans are integrated into the material already assigned to
`/Game/GrandTour/Demo/BenmoreRoads/Gaea/L_Benmore_GaeaReview`:
`/Game/GrandTour/Demo/BenmoreRoads/Gaea/ShoreRefinement/M_GC_Terrain`.
`Art/Unreal/benmore_mud_materials.py` wraps its existing colour, normal, roughness, specular and
occlusion outputs. Existing ecology, bed-zone and road masks select exposed silt and dry verges.
The road running-surface mask excludes the new mud layer, and steep banks and submerged bed
areas fade it out. The scanned layers share 260/180 cm wet/dry repeats, matching POM coordinates,
2.5 cm visual depth, 12–24 steps, and the study's distance and grazing-angle fades. Samples use
shared samplers and skip the scan work outside the layer's coverage. `BM_ScannedMudEnabled`
provides a material override switch. The normal blend respects the landscape's tangent space.

This is a material integration. Benmore's landscape scale is 124.0079/124.0079/200, unlike the
uniformly scaled displacement studies. No terrain rescale, geometric mud displacement, live mud
actor or seeded rut fixture is installed by this pass. Existing physical-material and grass
outputs, vehicle interfaces, river/lake water and actor placement are retained. Separate new
debris scatter is not part of this material installation.

Run `powershell -NoProfile -File Art/wait_unreal_free.ps1 -MaxMinutes 0` as its own command,
then `powershell -NoProfile -File Art/install_benmore_mud_materials.ps1`. `-Inspect` runs the
read-only inventory instead. The installer backs up both the map and terrain material under
`Saved/BenmoreMudMaterials/<timestamp>`, checks their modification times before saving, then
saves only the terrain material. The map already references it and does not need a save.
Preview water/camera changes are discarded by reloading. The current shoreline rebuild script
also reapplies this adapter so a shoreline material refresh retains the new layers.

The four matched before/after views and report are in `Art/Export/BenmoreMudMaterials`;
open `benmore-mud.html` to compare WetBank, SiltBank, DryVerge and Ford. Source scan binaries
remain the approved Poly Haven files documented above. Assets and screenshots follow the
existing local binary policy. No broad tests or performance benchmark are run (owner preference).

Validation: the four Python files parse, both installation/capture runs exited 0, and the final
report returned `ok: true` (`Saved/Logs/benmore_mud_pass2.txt`). All four final views were saved;
bank, silt, roadside and ford transitions were visually checked. The final log has no Python
or material compilation errors. Physical-material and grass output connections match their
pre-install signatures, actor placement survives reload, and the map file's SHA-256 is unchanged.
The first integration looked too dry on the silt banks; the final remap selects the wet scan
more strongly where the existing silt mask is dense. This material pass does not resolve the
pre-existing dark scatter stones or water glare visible in the baseline images. The original
material/map backup is `Saved/BenmoreMudMaterials/1791899057883787100`.
