# Landscape toolkit migration manifest (OWGameUE -> GrandTour)

Phase 0 survey, 2026-09-26. Read-only on the source. Nothing has been ported yet. Water is excluded throughout.

- Source: `D:\Dev\OWGameUE` (UE 5.8). Target: `C:\GrandTour` (UE 5.8, same launcher engine).
- Raw survey output is in `docs/landscape_migration/`:
  - `closure_summary.md`: all tables and chains.
  - `closure_packages.txt`: one line per package with its size.
  - `ar_walk.py`: the Asset Registry walk, rerunnable headless and read-only.
- The walk ran headless on the source with no saves. It finished in 63 s, all 10 steps ok, and the source's own log was left untouched.

---

## 1. Target facts

| item | finding |
|---|---|
| Engine | `EngineAssociation 5.8`. OK: 5.8 assets open. |
| Modules | One runtime module, `GrandTour`, with the macro `GRANDTOUR_API`. There is no editor module, although `GrandTourEditor.Target.cs` exists. |
| GrandTour.Build.cs | Public: Core, CoreUObject, Engine, InputCore, EnhancedInput, ChaosVehicles, GameplayTags, PhysicsCore, AssetRegistry, AudioExtensions, CableComponent, **Landscape**, **Foliage**, RHI, RenderCore, ProceduralMeshComponent. Private: MeshDescription, StaticMeshDescription. Editor only: MaterialEditor. |
| Plugins (.uproject) | ModelingToolsEditorMode (editor) and ChaosVehiclesPlugin. PCG, GeometryScripting and LandscapePatch are **not** enabled. Water is not enabled. GrandTour's own water is plain materials (M_GT_Water, M_GT_MudWater), unrelated to this migration. |
| /Game collisions | None. The target top level has Characters, Collections, Developers and GrandTour. Incoming folders: OWGame, ANGRY_MESH, MWLandscapeAutoMaterial, 3DAssets, Materials, Textures. |
| CLAUDE.md / AGENTS.md | None in the target. GrandTour's pipeline rules apply: headless `.bat` + Python in `Art/`, and tests are `*_test.bat` `-game -NullRHI` runs graded by `Art/suite.sh`, not `Automation RunTests`. |
| Version control | **None. GrandTour is not a git repo.** A 1.1 GB migration has no undo (see Q9). |
| Editor running | None at survey time. |

### Renderer: source block vs target

| setting | source | target | plan |
|---|---|---|---|
| `r.Nanite.AllowVoxels` | 1 | absent | **add** (Nanite tree foliage) |
| `r.GenerateMeshDistanceFields` | True | True | already set |
| `r.DynamicGlobalIlluminationMethod` / `r.ReflectionMethod` (Lumen) | 1 / 1 | 1 / 1 | already set |
| `r.Shadow.Virtual.Enable` | 1 | 1 | already set |
| `r.Lumen.TraceMeshSDFs` | 1 | absent | leave (a lighting change; only if the trees need it) |
| `r.Nanite.ProjectEnabled` | True | absent (engine default on) | leave |
| `[VirtualTexturePoolConfig] DefaultSizeInMegabyte` | 256 | absent | **add** |
| AA=TSR, MSAA 8, MotionBlur off, SkinCache, GPUSkin | set | differs | **do not port**: look and character settings, not landscape |
| `r.Substrate` | absent (off) | **True** | see Q8: every migrated material goes through Substrate conversion |
| `r.RayTracing` | absent | True | no change |

---

## 2. Dependency closure

The closure has 332 packages totalling 1117 MB. Of those, 90 are roots, 196 were reached through hard references and 46 through soft ones. Every package is in the Asset Registry and on disk. The Engine content it touches (40 packages) is not migrated.

| group | pkgs | MB | what |
|---|---|---|---|
| OWGame/Dev/DressingLab (flat) | 29 | 9.2 | M_OWDressingLab, MI_OWDressingLab_Style, 5 layer infos, 10 LGT_OW*, 3 flower clumps + 3 MIs, 6 biome PCG graphs |
| OWGame/Dev/DressingLab/Trees | 25 | 12.7 | generated tree variants |
| OWGame/Dev/DressingLab/TreeMIs | 22 | 0.3 | generated tree MIs |
| OWGame/Dev/DressingLab/Masters | 2 | 0.1 | M_OWFoliageMaster, M_OWTrunkMaster |
| OWGame/Dev/DressingLab/Roads | 7 | 1.2 | BP_OWRoad, _Dusty, _Gravel + 4 MI_OWRoad_* |
| OWGame/Dev/DressingLab/Cliffs | 1 | 0.0 | BP_OWCliffWall |
| OWGame/Dev/WorldPreview | 2 | 0.2 | PCG_OWWorldPreview, M_OWPreviewConifer |
| 3DAssets | 3 | 1.7 | SM_Beech / SM_Birch / SM_FirTree (licence txt present) |
| Materials | 12 | 0.2 | out of scope, needed by the tree meshes and masters (section 3) |
| Textures | 9 | 14.4 | out of scope, needed by the tree meshes and masters (section 3) |
| ANGRY_MESH/StylizedPack_MeadowEnvironment | 161 | 1042.1 | of 875 pkgs / 1801 MB in the pack; mostly textures (Rocks 431 MB) |
| ANGRY_MESH/StylizedPack_Common | 41 | 3.0 | of 53 / 12 MB; includes RVT_AM_01_Material |
| MWLandscapeAutoMaterial | 18 | 32.3 | of 100 / 701 MB |
| ToonFantasyNature | **0** | 0 | not needed. No root or in-scope script references it. |
| Fantastic_Village_Pack | **0** | 0 | not needed |

**Layer infos.** The five "sharedassets" rules matched nothing because the assets are named `OW_<Layer>_LayerInfo`. There are 24 layer infos across the two folders.

The material samples 17 layers:
- 13 non-water: OW_Meadow, OW_MeadowLush, OW_MeadowDry, OW_Bare, OW_Alpine, OW_Snow, OW_Forest, OW_ForestBeech, OW_ForestBirch, OW_ForestFir, OW_ForestOak, OW_Scree, OW_RoadVerge.
- 4 water: OW_BedGravel, OW_BedSand, OW_BedRock, OW_RiverWet.

`L_OWWorldCanvas_sharedassets` holds **exactly the 13 non-water layer infos**. `L_OWDressingLab_sharedassets` holds 7 of them (duplicate names) plus 4 water ones. Layer infos are leaves, so these 13 are extra to the 332 and tiny. See Q6.

**Material nodes.** M_OWDressingLab has:
- 17 LandscapeLayerSample nodes and no LayerBlend.
- One LandscapeGrassOutput with 12 grass entries, all pointing at the 10 LGT_OW* assets.
- One RVT output and one RVT sample (`/Game/ANGRY_MESH/StylizedPack_Common/Textures/RVT_AM_01_Material`).

MI_OWDressingLab_Style's parent is M_OWDressingLab directly.

**/Script modules the closure uses:**

| module | packages |
|---|---|
| NavigationSystem | 95 |
| StaticMeshDescription | 25 |
| Landscape | 23 |
| Interchange* | 9 each |
| StructUtilsEditor | 7 |
| PCG | 7 |
| OWGameUE | 7 |

The only plugin module is PCG. Nothing uses Water, MeshPartition, MeshTerrain or LandscapePatch. That is a lower bound, because Engine and CoreUObject are not listed.

---

## 3. Dependencies outside the listed scope (22 packages, 14.6 MB)

**/Game/Materials (12):**
- MM_Foliage and MM_Trunk.
- 6 MIs: MI_Foliage_* and MI_Trunk_* for Beech, Birch and FirTree.
- Wind functions F_BendWind, F_RealTimeWindIntensity, F_WindDirection.
- MPC_GlobalWind.

Why they come along: the vendor tree meshes `3DAssets/SM_*` carry the MIs, which pull MM_Foliage / MM_Trunk. The OW masters `M_OWFoliageMaster` / `M_OWTrunkMaster` pull the wind functions and MPC_GlobalWind.

**/Game/Textures (9):** TXT_Leaves_* and TXT_Trunk_* (13.6 MB). They are pulled by the TreeMIs and the OW masters.

**`OWGame/Dev/WorldPreview/M_OWPreviewConifer`:** a soft reference from PCG_OWWorldPreview.

**Verdict:** all 22 are small, have no water, and are required. Bring them along with the closure. MPC_GlobalWind is a second wind system beside GrandTour's own MPC_Weather. Unifying them is a later look decision, not part of the port.

**C++ hardcoded paths:**
- `OWCreateBiomePCGCommandlet.cpp:376` builds `/Game/OWGame/Dev/WorldPreview/M_OWPreviewWood` into a local variable that is never used. It is dead code: drop the line, and don't migrate the material.
- Every other hardcoded path points inside the closure: DressingLab/{Trees,TreeMIs,Roads,Cliffs}, ANGRY_MESH Meadow meshes, 3DAssets and /Engine/BasicShapes. Those paths stay valid because assets keep their `/Game/...` paths.

---

## 4. Water leaks and fix plan

No package in the closure is a water asset. River/ (7 assets), PCG_OWRiver, M_OWWaterVillage and MI_OWWaterVillage are all left behind, and nothing references a Water plugin mount or class. The leaks are inside assets and code:

| # | leak | evidence | fix |
|---|---|---|---|
| W1 | **PCG_OWForest / Meadow / Scree / Alpine reference `/Script/OWGameUE`** | These are exactly the four graphs whose builders call `MakeRiverExclusions`, which adds a By-Class spline getter on `AOWRiverMesh::StaticClass()`. Road and Cliff graphs have no such reference. So the class is `OWRiverMesh`. This is inferred from the code; I'll confirm it by loading once in Phase 3. | Add **no** redirect for OWRiverMesh. Don't migrate these graphs; generate them fresh in the target with the stripped commandlet (Q4). Then no river node can survive. |
| W2 | M_OWDressingLab samples OW_BedGravel / OW_BedSand / OW_BedRock / OW_RiverWet | 4 of its 17 LayerSample nodes. `ClaudeSetupDressingLab.py:23-103` authored them (bed grades, and the wet layer ordered last, apparently for the grass kill mask). | Unpainted layers weigh 0, so they're harmless. They'll show as 4 extra target layers in the Paint panel. Create no layer infos for them. The graph is **not** edited unless you say so (Q5). |
| W3 | Water layer infos (`OW_RiverWet`, `OW_Bed*`) | They live in `L_OWDressingLab_sharedassets`. | Migrate only the 13 non-water layer infos from `L_OWWorldCanvas_sharedassets` (Q6). |
| W4 | River code in `OWCreateBiomePCGCommandlet.cpp` | Section 5. | Strip it cleanly; keep the road and cliff exclusions. |
| W5 | River references in scripts | `ClaudeSetupDressingLab` (21), `ClaudeSetupBiomePCG` (5: PCG_OWRiver expected, River in the biome loop), `ClaudeRegenerateLabDressing` (21), `ClaudeVerifyRoadExclusion` (21), `ClaudeSetupCanvasDressing` (3), `GenerateRegion01ProductionInputs` (16), `ValidateRegion01TerrainExports` (2). | Strip them when porting (section 7). |
| W6 | `OWBedStampComponent` was written "for river channels, pools, steps and hillside benches" | No asset references it (no `/Script/OWGameUEEditor` references in the closure). | Port it as a generic sculpt stamp, or drop it (Q7). |
| W7 | Docs | `WorldToolsRoundPlan` (19 river mentions) and `OWWorldBuildingGuide` (4). The other 7 docs have none. | Skip those sections when carrying the knowledge over. |

Vendor-internal water functions, such as `MF_MWAM_WaterMask`, are **not** in the closure. They only arrive if a whole pack is added (Q3), and then they stay inside it unused.

---

## 5. C++ plan

### Classes that assets reference, and their redirects

| asset | class | redirect |
|---|---|---|
| BP_OWRoad, BP_OWRoad_Dusty, BP_OWRoad_Gravel | component `OWRoadBed` : `/Script/OWGameUE.OWRoadBedComponent` (plus Spline and 2 Billboards) | `+ClassRedirects=(OldName="/Script/OWGameUE.OWRoadBedComponent",NewName="/Script/GrandTour.OWRoadBedComponent")` |
| PCG_OWForest / Meadow / Scree / Alpine | `/Script/OWGameUE.OWRiverMesh` (W1) | **none, on purpose** |

That single redirect is all the assets need. No asset references an `OWGameUEEditor` class. The redirect goes in `[CoreRedirects]` in `Config/DefaultEngine.ini` **before** any road BP is opened in the target.

### Where the files go

A new editor module, `GrandTourEditor`, is the recommended layout (Q1). Class names stay `OW*` (Q2), so only the module in the path changes.

| source file (lines) | target | API macro | notes |
|---|---|---|---|
| `OWGameUE/World/OWRoadBedComponent.h/.cpp` (80/166) | `Source/GrandTour/Dressing/` | `OWGAMEUE_API` -> `GRANDTOUR_API` | Runtime component, because it ships inside the road BPs. The editor part is under `WITH_EDITOR` and resolves edit layers via `GetEditLayers()`. Needs **Slate, SlateCore** (it uses `FNotificationInfo`) added to GrandTour's `bBuildEditor` block. Landscape is already a dependency. |
| `OWGameUEEditor/Private/OWCreateBiomePCGCommandlet.h/.cpp` (23/1810) | `Source/GrandTourEditor/Private/Dressing/` | none | Water strip below. |
| `OWCreateTreeVariantsCommandlet.h/.cpp` (22/839) | same | none | Unchanged. Needs GeometryCore, **GeometryFramework** (`UDynamicMesh.h`; missing from the brief's list), GeometryScriptingCore and GeometryScriptingEditor. |
| `OWPaintRoadVergeCommandlet.h/.cpp` (28/313) | same | none | Replace the hardcoded map (`:20` `/Game/OWGame/Dev/L_OWDressingLab`) with a required `-Map=` argument, with no default. Keep `VergeLayerName OW_RoadVerge` and the road class-name match. It needs RHI (a GPU composite), so no `-NullRHI`. |
| `OWBedStampComponent.h/.cpp` + `OWBedStampActor.h/.cpp` (115/331, 26/16) | same (if Q7 = keep) | none | Subclass of `ULandscapeTexturePatch`, so it needs the **LandscapePatch** plugin and module. |

**`GrandTourEditor.Build.cs`:**
- Public: Core, CoreUObject, Engine, GrandTour.
- Private: AssetRegistry, UnrealEd, Landscape, LandscapePatch (only if Q7 = keep), PCG, GeometryCore, GeometryFramework, GeometryScriptingCore, GeometryScriptingEditor, RenderCore, Foliage (`LandscapeEdit.h` needs it, a GrandTour trap), Slate, SlateCore.
- Also: add the `.uproject` module entry (Type Editor) and `ExtraModuleNames.Add("GrandTourEditor")` in the Editor target.

Commandlet command names stay the same (`-run=OWCreateBiomePCG`, `OWCreateTreeVariants`, `OWPaintRoadVerge`).

### Water strip in `OWCreateBiomePCGCommandlet.cpp`

Line numbers are from the source file.

- L28 `#include "World/OWRiverMesh.h"`.
- L56-67: the A2 river palette comment and `PackAutumnRock`. It is used only by BuildRiverGraph (L1665-1674).
- L362-366: the `MakeRiverExclusions` declaration. Remove the calls at L375 (Forest), L695 (Meadow), L797 (Scree) and L1455 (Alpine).
- L1024-1093: `MakePresetGate` and its comment. River only (used at L1650 and L1685).
- L1094-1107: `MakeZOffset`. River only (L1760).
- L1108-1160: the river corridor constants (`RiverExclusionSampleCm`, `RiverHalfWidthCm`, `RiverExclusionHalfExtents`) and the `MakeRiverExclusions` definition.
- L1524-~1778: the R2 bank-dressing comment and `BuildRiverGraph`.
- L1787: the `{ "PCG_OWRiver", &BuildRiverGraph }` builder entry.
- L376: the dead `Wood` variable (section 3).
- **Keep** `MakeUnitScale` (L990-1022) even though only river code calls it today. It is the generic guard against the spline scale leaking into point scale, one of the pitfalls you listed. Rewrite its comment to drop the river narrative but keep the lesson. Wiring it into the road chains (road splines are unit scale today) is a possible hardening step, not part of this port.
- Keep the road and cliff exclusions, `MakeRoadSplineGetter`, `MakeSplineCenterSampler` and the three road BP class paths (L870-874), all unchanged.

**Build:** check for a running editor with `Get-Process UnrealEditor*`, then build once with the editor closed and fix errors from the log.

---

## 6. Config and plugins (Phase 1)

- `DefaultEngine.ini`: add `r.Nanite.AllowVoxels=1` under RendererSettings, and `[/Script/Engine.VirtualTexturePoolConfig] DefaultSizeInMegabyte=256`. Add the one CoreRedirect from section 5. Nothing else from the source renderer block. GrandTour's lighting, exposure and post-processing stay untouched.
- `.uproject` plugins:
  - Enable PCG, GeometryScripting, and LandscapePatch (only if Q7 = keep).
  - ModelingToolsEditorMode is already on.
  - **Do not enable** MeshPartition, MeshTerrainMode or PCGMeshPartitionInterop: no asset or file needs them. Water and MeshPartitionWater stay off.

---

## 7. Assets (Phase 3) and scripts

**Migrate set:**
- The closure minus the 6 biome graphs (Q4). That is 326 packages plus the 13 WorldCanvas layer infos, each keeping its `/Game/...` path.
- Vendor packs follow Q3.
- **Not migrated:** L_OWDressingLab, L_OWWorldSlice, the `*_sharedassets` duplicates and water layer infos, River/, PCG_OWRiver, M/MI_OWWaterVillage, M_OWPreviewWood, ToonFantasyNature, Fantastic_Village_Pack.
- After the migrate, re-audit the target: rerun the walk on GrandTour and require zero `/Script/OWGameUE` references and zero water names.

**Scripts:** ported into `Art/dressing/`, with a `.bat` per headless step (the GrandTour pattern). Paths are adapted and river references stripped.

| role | scripts |
|---|---|
| Regeneration chain (run in Phase 4) | `ClaudeSetupBiomePCG` (graph post-steps after the commandlet), `ClaudeTuneMeadowLook` (holds the absolute live knob values, so rerunning it after regeneration restores the source's tuning), `ClaudeDiagnoseBiomePCG`, `ClaudeFixBiomeGenerate` |
| Roads | `ClaudeAddRoadBedComponent`, `ClaudePaintRoadVerge`, `ClaudeVerifyRoadTypes`, `ClaudeVerifyRoadExclusion` (strip river), `ClaudeSetupRVTVolumes` (map parameter) |
| Authoring and baselines | Ported for regeneration only, **not run by default**: they would stomp the migrated state. `ClaudeSetupDressingLab` (strip the 4 bed layers before any run), `ClaudeHookupMeadowPack`, `ClaudeAuthorOWFoliageMaster`, `ClaudeAuthorFoliageVariants`, `ClaudeSetupFoliageMIs`, `ClaudeSetupMeadowFlowers`, `ClaudeAuthorRoadTypes`, `ClaudeCreateOWRoadBP`, `ClaudeCleanupTreeOrphans`, `DevGeneratePainterlyGrassCards`, `ClaudeImportGrassCards` |
| Bound to the source's maps | Reference only: `ClaudeSetupLabRoads`, `ClaudeRegenerateLabDressing`, `ClaudeSetupPCGWorldPreview`, `ClaudeSetupCanvasDressing` |
| Region01 heightmap tools | Skip: `DevPrepFMGHeightmap`, `GenerateRegion01ProductionInputs`, `ValidateRegion01TerrainExports` |

**Knowledge carried over** into `docs/LandscapeToolkit.md` (Phase 4). From `Scripts/CLAUDE.md`, the traps that apply here:
- PCG generation and landscape edit-layer merges no-op in a commandlet: they need a ticking editor.
- Git Bash mangles `/Game/` arguments.
- `unreal.log` output never reaches stdout.
- Gate on the report JSON, not the exit code.
- Never pipe UnrealEditor-Cmd into `Select-Object`.

The river sections of the docs are skipped.

**Phase 4 test map:** `/Game/GrandTour/Test/L_OWToolkitTest`. It gets:
- A landscape with MI_OWDressingLab_Style, with layer infos assigned in the Paint panel by you or me in a ticking editor.
- Every biome layer painted, one PCG volume per biome, and one road of each type.
- The road-bed and verge tools run on it.

The smoke test follows the GrandTour pattern (`dressing_toolkit_test.bat`). It checks that:
- The 3 road BPs load with an `OWRoadBedComponent`.
- The 6 biome graphs load with no `OWRiverMesh` reference and a non-empty node count.
- The material has the 13 non-water layers.

---

## 8. Open questions (my recommendation first)

1. **Editor module.** Create `GrandTourEditor` (recommended), or put the commandlets in `GrandTour` under `WITH_EDITOR`? The latter drags PCG and GeometryScriptingEditor into the game module.
2. **Class names.** Keep `OW*` (recommended: one module redirect, toolkit stays recognisable), or rename to the `GT*` prefix from ARCHITECTURE.md? Renaming means one redirect per class plus renamed commandlet switches.
3. **Vendor packs.** Your brief prefers Fab "Add to Project" of whole packs: ~2.5 GB (MeadowEnvironment 1.8 GB, Common 12 MB, MWLandscapeAutoMaterial 701 MB), and each pack's version must be checked against the source. The alternative lets Migrate carry the 220 vendor packages the closure uses: ~1.08 GB at exactly the versions the source uses, with no version check. **I recommend Migrate**, then Add to Project later if you want the rest of a pack for hand dressing. Either way, skip ToonFantasyNature and Fantastic_Village_Pack; nothing needs them.
4. **Biome graphs.** Generate the 6 fresh in the target (commandlet, then `ClaudeSetupBiomePCG`, then `ClaudeTuneMeadowLook` knobs) instead of migrating them (recommended). No map in the target references them yet, so nothing is lost, and the river nodes can't come along. **Did you ever hand-edit a biome graph in the editor** beyond those scripts? Such edits would be lost.
5. **River layers in M_OWDressingLab.** Leave the 4 unpainted bed/wet samples for now (recommended; harmless). Or strip them from the graph: I'd first check the grass kill mask that orders OW_RiverWet last. Nothing is edited without your yes.
6. **Layer infos.** Bring the 13 from `L_OWWorldCanvas_sharedassets` only (recommended: complete, no water, one asset per name). Or also the DressingLab root 5 (`OW_Meadow`, `OW_Forest`, `OW_Scree`, `OW_Bare`, `LI_OW_Meadow`)? Those duplicate names and would show twice in the Paint panel's asset picker.
7. **Bed stamp.** Port `OWBedStampComponent`/`Actor` as a generic sculpt stamp (steps, benches), as your brief lists it, and enable LandscapePatch. Or drop it, since it was built for river channels and nothing references it.
8. **Substrate.** GrandTour runs `r.Substrate=True`; OWGameUE doesn't. Every migrated material, including the vendor masters and the RVT output, is converted on load. Accept that and judge it in your look checklist (recommended). Turning Substrate off would change all of GrandTour.
9. **Backup.** GrandTour has no git. Before Phase 2, `git init` with an LFS or ignore setup for Content, or at least a zip of `Source`, `Config`, `Content` and the `.uproject`? Tell me which.
10. **GrandTour integration (not a blocker).** This material doesn't read GrandTour's MF_Weather/MPC_Weather or the painterly look layers. The port stops at the test map. Wiring it into legs is a later decision.

---

## 9. Build plan (approved 2026-09-26: "go with your recommendations, no need for zip")

Answers: Q1-Q8 and Q10 as recommended above. Q9: git baseline `eedf146` (code, config, docs, Art scripts; Content and art binaries ignored by `.gitignore`), no zip.

Stages:
- **A** (C++ and config) and **D** (script ports) run in parallel.
- Then **B** (assets and biome graphs).
- Then **C** (test map, tools, smoke test, docs).

One Opus agent per stage.

### 9.0 Rules for every stage

- The source `D:\Dev\OWGameUE` is READ-ONLY. Only read files and do read-only headless runs there. Never save, build or write anything in it.
- **Running Unreal:**
  - Go through the PowerShell tool; Git Bash rewrites `/Game/...` arguments.
  - Never name a PowerShell variable `$script`; pass `"-Script=$py"`.
  - Never pipe UnrealEditor-Cmd into `Select-Object`; redirect to a file.
  - `unreal.log` does not reach stdout. Every Python step writes a report JSON with a per-step `ok`, and the stage gates on that report, not on the exit code.
- **Before a build or a target Unreal run:** no process may be running whose command line contains `GrandTour.uproject`. Check with `Get-CimInstance Win32_Process -Filter "Name like 'UnrealEditor%'"`.
- **Builds:** only `bash Art/build.sh`.
- **Headless Python in GrandTour:** `UnrealEditor-Cmd.exe C:\GrandTour\GrandTour.uproject -run=PythonScript "-Script=<abs .py>" -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"`. Each Unreal step gets a `.bat` under `Art/dressing/` (the GrandTour pattern), so it can be rerun.
- **Git:** `git add` only your own paths (`2>/dev/null` silences the CRLF warnings). Commit messages end with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- If you find a fact that changes the design, stop and report it. Do not redesign.

### 9.A C++, config, plugins (Phases 1+2)

No target Unreal launch in this stage.

1. **`Config/DefaultEngine.ini`.** Nothing else changes.
   - Under `[/Script/Engine.RendererSettings]`, add `r.Nanite.AllowVoxels=1` with a `;` comment naming this manifest.
   - Add a new `[/Script/Engine.VirtualTexturePoolConfig]` section with `DefaultSizeInMegabyte=256`.
   - Add a new `[CoreRedirects]` section with `+ClassRedirects=(OldName="/Script/OWGameUE.OWRoadBedComponent",NewName="/Script/GrandTour.OWRoadBedComponent")`.
2. **Project and target files.**
   - `GrandTour.uproject`: enable the PCG, GeometryScripting and LandscapePatch plugins. Add the module `{ "Name": "GrandTourEditor", "Type": "Editor", "LoadingPhase": "Default" }`.
   - `GrandTourEditor.Target.cs`: `ExtraModuleNames.Add("GrandTourEditor")`. Leave the game target untouched.
3. **Runtime component.** Copy `OWRoadBedComponent.h/.cpp` from the source to `Source/GrandTour/Dressing/`.
   - Change `OWGAMEUE_API` to `GRANDTOUR_API`.
   - The .cpp includes `"Dressing/OWRoadBedComponent.h"`.
   - In `GrandTour.Build.cs`, add `"Slate", "SlateCore"` to the `bBuildEditor` block.
4. **Editor module** in `Source/GrandTourEditor/`:
   - `GrandTourEditor.Build.cs`: the section 5 dependencies, LandscapePatch included, `PCHUsage = UseExplicitOrSharedPCHs`, `PublicIncludePaths.Add(ModuleDirectory)`.
   - `GrandTourEditor.h/.cpp` with `IMPLEMENT_MODULE(FDefaultModuleImpl, GrandTourEditor)`.
   - `Private/Dressing/` holding the four commandlets and the bed stamp files.
5. **Strips and edits.**
   - Strip `OWCreateBiomePCGCommandlet.cpp` exactly as section 5 lists. Keep `MakeUnitScale`; reword its comment to drop the river story but keep the lesson. Drop the dead `Wood` line.
   - `OWPaintRoadVergeCommandlet`: make `-Map=` required (`FParse::Value`). Log an error and return 1 when it is missing. Update the `Run:` comment.
   - Reword the bed stamp header to "sculpt stamps: channels, steps, hillside benches".
   - **Gate:** `grep -i -E "river|water|OWGameUE"` over every ported file returns nothing.
6. **Test-map helper library.** New `Source/GrandTourEditor/Private/Dressing/OWToolkitSetupLibrary.h/.cpp`: a `UBlueprintFunctionLibrary` in the editor module, callable from Python, for the Phase 4 test map.
   - Reuse the technique in `Source/GrandTour/Terrain/GTTerrainBuilder.cpp`. GrandTour's landscape traps:
     - 5.8 always has edit layers, and the GPU merge never runs under NullRHI.
     - So write the FINAL weightmaps on the CPU with `FLandscapeEditDataInterface(Info, FGuid(), false)`, then `SetAlphaData(..., false, false)`, then `Flush()`.
     - Then call `PostEditChange()` on every weightmap texture, then `UpdateAllComponentMaterialInstances(true)`.
     - Call `UpdateLayerInfoMap` and `AddTargetLayer` for each layer info.
   - Functions:
     - `static float SampleToolkitTestHeightCm(float X, float Y)` (BlueprintPure), implementing the layout in 9.C.1.
     - `static FString ToolkitTestLayerAt(float X, float Y)`, for debugging the layout.
     - `static bool BuildToolkitTestLandscape(UMaterialInterface* Material, const TArray<ULandscapeLayerInfoObject*>& LayerInfos, URuntimeVirtualTexture* RVT, FString& OutReport)`. It spawns the landscape in the current editor world per 9.C.1, with heights, 13 target layers and CPU-written weights. It sets the landscape's `RuntimeVirtualTextures = [RVT]`. OutReport is JSON: vertex count, components, painted-vertex count per layer.
7. **Smoke-test runner** in the runtime module.
   - Dispatched by `-GTDressingTest`, the same way the existing `-GT...Test` switches are (see `Run/GTRunGameMode.cpp` for `GTEnvTest`).
   - It runs the checks in 9.C.5, prints GrandTour's `GTDRIVETEST` lines and `GTDRIVETEST_RESULT PASS|FAIL <reason>`, then quits.
   - No PCG module dependency. Count `UInstancedStaticMeshComponent` instances on actors tagged `OWBiome.*`. Get the layer infos from the landscape components' weightmap allocations and identify them by asset name.
8. **Build and commit.** Build once, fix errors from the log, and rebuild until `Result: Succeeded`. Commit `Source Config GrandTour.uproject` as "Port OW landscape toolkit C++ (no water) + config".

**Report:** the build result, the file list with line counts, the strip grep output, and anything that deviated from this plan.

### 9.D Script ports

Runs in parallel with A. No Unreal runs, and no writes to Source, Config or Content.

- **Scope.** Port into `Art/dressing/ported/` every script in section 7 **except** `ClaudeTuneMeadowLook` (stage B owns it) and the three Region01 tools.
- **Per script:**
  - Strip the river/water code and names (W5).
  - Replace source absolute paths (`C:/Dev/OWGameUE`, `D:\Dev\OWGameUE`, `Scripts/`) with GrandTour ones.
  - Make any map path a single `MAP = ...` constant at the top, or an argv override.
  - Drop the `_RETIRED_*` functions.
  - Keep the report-JSON pattern.
- **`ClaudeSetupDressingLab`:** remove the four bed/wet layers and their grades from its layer list, so a regeneration can never re-add them.
- **Checks:** run `python -m py_compile` on each port (syntax only). **Gate:** `grep -i -E "river|water|OWGameUE"` over the ports returns nothing.
- **`Art/dressing/ported/README.md`:** a table with one row per script: its role (pipeline, regen-only or reference), the changes made, and its run command.
- **`docs/landscape_migration/pitfalls_from_source.md`:** the entries from `D:\Dev\OWGameUE\Scripts\CLAUDE.md` and the nine docs of brief item 11 that apply to this toolkit, one or two lines each, each with its source file:line. Relevant topics: PCG, landscape, grass, trees/WPO, RVT, roads, headless Python, commandlets. No river items.
- No commit; stage C commits this work.

### 9.B Assets and biome graphs (Phase 3; after A)

1. **Copy set.** Write it to `docs/landscape_migration/copy_set.txt`. It is `landscape_migration/closure_packages.txt`:
   - minus the 6 biome graphs (`DressingLab/PCG_OW{Forest,Meadow,Scree,Alpine,Cliff,Road}`),
   - minus the 5 DressingLab root layer infos (`OW_{Meadow,Forest,Scree,Bare}_LayerInfo`, `LI_OW_Meadow`),
   - plus the 13 `L_OWWorldCanvas_sharedassets/OW_*_LayerInfo` (all 13 there are non-water).

   That is 334 packages, plus the file `Content/3DAssets/STYLIZED_COZY_TREES_LICENSE.txt`.
2. **Copy by file, not with the editor's Migrate.** Source and target package paths are identical, so Migrate's only extra work (path remapping) would do nothing. A byte copy of exactly the audited closure is equivalent. It needs no editor on the source, so there is no chance of a source save, and it can be verified by hash. Write `Art/dressing/copy_closure.ps1`:
   - Copy every file of each package (`.uasset/.umap/.uexp/.ubulk/.uptnl`).
   - Refuse if any destination file already exists.
   - Compare SHA-1 of source and destination.
   - Log to `docs/landscape_migration/copied_files.txt`.
3. **Re-audit and redirect proof.** `Art/dressing/audit_toolkit.py` + `.bat`, headless on the target:
   - Every `/Game` dependency of the copied packages resolves (0 missing).
   - 0 water-named packages.
   - `/Script/OWGameUE*` dependencies appear only on the 3 road BPs.
   - Load the 3 road BPs. Their components must include `OWRoadBed : /Script/GrandTour.OWRoadBedComponent`. If not, the redirect is broken: STOP and do not resave.
   - Then resave the 3 road BPs and query again: 0 `/Script/OWGameUE*` dependencies anywhere.
4. **Regenerate the graphs.** `Art/dressing/create_biome_pcg.bat` runs `-run=OWCreateBiomePCG -Unattended -NullRHI -NoSplash -NoSound`. Expect 6 graphs created.
5. **Restore the tuning.** Port `ClaudeTuneMeadowLook.py` to `Art/dressing/tune_meadow_look.py`:
   - The KNOBS values stay byte-identical to the source.
   - Keep only the LGT and PCG knob steps.
   - The step that fires Generate must do nothing when no biome actors exist.

   Run it headless and gate on its report.
6. **Structural check.** Count node classes per biome graph in the source (a read-only headless run on OWGameUE) and in the target. The only expected difference is the river-exclusion node sets in Forest, Meadow, Scree and Alpine. Any other difference means a hand edit or drift: report it, don't fix it.
7. **Final audit and commit.** Rerun the audit with the graphs included: every graph dependency resolves, 0 `/Script/OWGameUE*`, 0 water. Content is not versioned, so commit only `Art/dressing` and `docs/landscape_migration`.

### 9.C Test map, tools, smoke test, docs (Phase 4; after B and D)

1. **Layout** (implemented in `OWToolkitSetupLibrary`).
   - **Grid:** the landscape is 505 x 505 vertices: 8 x 8 components, 63 quads, 1 section, scale 100, origin (0,0,0). That covers 0..50400 cm. It is split into 3 x 3 cells of C = 16800 cm; column i = floor(X/C), row j = floor(Y/C).
   - **Heights (cm):**
     - Base: `100*sin(X/7000)*cos(Y/9000) + 50*sin((X+Y)/3100)`.
     - Scree hill at (25200, 42000): add `7000*pow(saturate(1 - r/6000), 1.6)`. Its normal.z runs about 0.5-1, covering the scree slope bands 0.42-0.78 and 0.2-0.5.
     - Alpine hill at (42000, 42000): add `4000*smoothstep(saturate(1 - r/7500))`.
   - **Dominant layer per vertex:**

     | row | column 0 | column 1 | column 2 |
     |---|---|---|---|
     | 0 | OW_Meadow | OW_MeadowLush | OW_MeadowDry |
     | 1 | OW_Forest | OW_ForestBeech (lower half), OW_ForestBirch (upper half) | OW_ForestFir (lower half), OW_ForestOak (upper half) |
     | 2 | OW_Bare | OW_Scree where the scree hill's r < 6200, else OW_Bare | OW_Snow where the alpine hill's r < 3000, OW_Alpine where r < 7800, else OW_Bare |

     OW_RoadVerge starts at 0; the road tools paint it.
   - **Blending:** start from one-hot weights, apply a separable box blur of radius 4 vertices per layer, then normalise to 255.
   - Register all 13 non-water layers as target layers. The 4 water layers are not registered.
2. **Setup script.** `Art/dressing/setup_toolkit_test_map.py` + `.bat`, headless. It:
   - Creates a new level `/Game/GrandTour/Test/L_OWToolkitTest`, refusing to overwrite unless given `--overwrite`.
   - Adds lighting: a DirectionalLight as the atmosphere sun, SkyAtmosphere, a SkyLight with real-time capture, ExponentialHeightFog.
   - Calls `BuildToolkitTestLandscape(MI_OWDressingLab_Style, the 13 WorldCanvas layer infos, RVT_AM_01_Material)`.
   - Places an RVT volume over the landscape bounds, with the settings from the source `ClaudeSetupRVTVolumes.py`.
   - Places 6 `PCGVolume`s following the pattern in the source `ClaudeSetupBiomePCG.py:370-443`. Each covers the whole landscape (center (25200,25200,3000), box 50400 x 50400 x 10000 cm), uses graph `PCG_OW<Biome>` and is tagged `OWBiome.<Biome>`.
   - Places the roads and cliff wall. Spline points are world XY, with Z from `SampleToolkitTestHeightCm`. Clear each BP's default points first.

     | actor | spline points |
     |---|---|
     | `BP_OWRoad` | (3000,2000)→(6000,12000)→(9000,22000)→(7000,31000) |
     | `BP_OWRoad_Dusty` | (22000,2000)→(26000,12000)→(24000,22000)→(27000,31000) |
     | `BP_OWRoad_Gravel` | (39000,2000)→(43000,12000)→(41000,22000)→(44000,31000) |
     | `BP_OWCliffWall` | 5 points on r = 5200 around the scree hill, at 200°..340° |
   - Places a PlayerStart at (8400, 8400, ground + 300) facing +Y.
   - Saves, and writes a report JSON: painted count per layer (all > 0 except RoadVerge) and actor counts.
3. **Verge commandlet.** `Art/dressing/paint_road_verge.bat` runs `-run=OWPaintRoadVerge -Map=/Game/GrandTour/Test/L_OWToolkitTest -Unattended -NoSplash -NoSound -AllowCommandletRendering`. **As built:** a commandlet runs NullRHI even without `-NullRHI`, so the merge never happened until `-AllowCommandletRendering` was added (stage C, 2026-09-26).
4. **Ticking-editor pass.** PCG generation and edit-layer merges do nothing in a commandlet, so they need a real editor.
   - `Art/dressing/tick_harness.ps1`:
     - Writes `Content/Python/init_unreal.py`, which acts ONLY when the env var `GT_TOOLKIT_HARNESS` names a task script.
     - Launches the full `UnrealEditor.exe` with the map. It waits up to 25 minutes, then kills the editor.
     - In a `finally`, whatever happens, deletes the bootstrap (and `Content/Python` if it created that folder).
   - Task script `Art/dressing/tick_apply_and_generate.py`:
     1. Lets about 6 s of real ticks pass.
     2. Calls `OWRoadBedComponent.apply_bed_and_verge()` on each road, then lets a few seconds of ticks pass.
     3. Calls `generate(True)` on each tagged volume. Never clean up first.
     4. Polls on the slate post-tick until no component is generating and every volume owns ISM instances, or 10 minutes pass.
     5. Saves dirty packages.
     6. Writes a report: instances per biome; landscape height and verge weight at each road's middle point, before and after; per-step `ok`.
     7. Calls `quit_editor()`.
   - The editor window appears on screen while this runs.
5. **Smoke test.** `Art/dressing_toolkit_test.bat`, following the `env_test.bat` pattern: map `/Game/GrandTour/Test/L_OWToolkitTest`, `-GTDressingTest`, `-game -NullRHI`, and a `gpu` argument that switches to `-RenderOffScreen`. Add it to `Art/suite.sh` if the suite keeps a list.
   - PASS requires all of:
     - 3 road actors `BP_OWRoad*`, each with a `UOWRoadBedComponent`.
     - The landscape material is `MI_OWDressingLab_Style`.
     - Exactly the 13 non-water layer infos are present, none named Bed or RiverWet.
     - Each of the 6 `OWBiome.*` volumes owns more than 0 ISM instances (saved from the ticking pass).
   - Run it, then `bash Art/suite.sh terrain` as a GrandTour regression check on the terrain path.
6. **Docs.** Write `docs/LandscapeToolkit.md` covering:
   - What's here: folders, classes, commandlets, scripts.
   - The regeneration order: tree variants → biome graphs → tune → test map → verge → ticking pass.
   - Every command.
   - The pitfalls: the brief's list, `landscape_migration/pitfalls_from_source.md`, and anything paid for in stages A-C.
   - The water exclusions.
   - The test map and smoke test.
   - The checklist below, verbatim.

   Add a short VEHICLE_BUILD_SYSTEM section that points at it and gives the numbers. Commit `Art docs Source` (Source only if stage C touched code).

### 9.E Editor / PIE checklist (for the owner; Claude judges no look)

Open `L_OWToolkitTest`. The first open compiles many shaders, because Substrate converts every migrated material; let it finish.

1. **Layers.** The Paint panel lists the 13 OW layers with their layer infos. It also lists the 4 unpainted river layers from the material; that is expected and harmless.
2. **Biomes.** Each cell reads as its biome:
   - meadow, lush and dry differ in colour and grass;
   - the forest cells show generic, beech, birch, fir and oak;
   - rocks sit on the scree hill's steep faces;
   - firs and rocks cover the alpine hill, with a snow cap on top;
   - the bare cell is bare.
3. **Borders.** The 4 m cross-fades between cells read soft, with no hard seams or tiling stripes.
4. **Grass density.**
   - Compare the meadow grass and flowers per cell against your memory of the OWGameUE lab.
   - Check the grass pop-in ring distance.
   - There is no grass on road beds or verges.
5. **Trees.**
   - No double "puff". The variants are baked, so a leaf that swells or sways twice means WPO is still on their material.
   - The painterly trunk normals are intact.
   - Nanite foliage looks fine up close and far away.
   - No giant or tiny outliers.
6. **Roads.** Each of the three types has:
   - its bed carved along the spline;
   - a painted verge;
   - no trees or rocks on it;
   - its own dressing.

   Then move one spline point and click **Apply Bed & Verge** in Details: the carve follows. The verge stamp is additive, so the old strip stays painted.
7. **Cliff.** Cliff rocks line the scree hill's south base.
8. **RVT blend.** Ground cover and prop bases pick up the landscape colour. There is no black, white or smeared RVT (which would point to the volume bounds).
9. **Substrate.** Open `D:\Dev\OWGameUE` `L_OWDressingLab` side by side (read-only; don't save it). Compare the landscape, leaves and road MIs for colour or roughness shifts.
10. **Perf** (PIE, `stat unit`, `stat gpu`). Note the frame and GPU time standing in the oak forest cell, standing in the meadow cell, and driving across. Write the numbers down next to L_Proving's.
