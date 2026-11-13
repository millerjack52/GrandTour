# Ported landscape-toolkit scripts (stage D)

These are Python scripts ported from the source project's `Scripts/` folder under stage D of `docs/LandscapeMigrationManifest.md` (sections 7 and 9.D). File names are unchanged. Pitfalls are in `docs/landscape_migration/pitfalls_from_source.md`.

Two scripts are not here:
- `ClaudeTuneMeadowLook` belongs to stage B.
- The Region01 heightmap tools are skipped.

## Rules applied to every port

- **Source-only code removed.**
  - Source-only layers, biomes, classes and corridors are gone. Nothing references the removed actor classes or plugin classes.
  - `_RETIRED_*` functions are dropped, along with helpers that only they used.
  - `unreal.OWRoadBedComponent` keeps its name. It now lives in the GrandTour runtime module, and a CoreRedirect covers the old path.
- **Paths.**
  - Source absolute paths are replaced. Scripts live in `C:/GrandTour/Art/dressing/ported/`, and each report JSON is written next to its script (`<Name>Report.json`).
  - Grass-card PNGs go to `GrassCards/` in this folder.
- **Maps.**
  - A script that names a map has one `MAP` constant at the top, defaulting to `/Game/GrandTour/Test/L_OWToolkitTest`.
  - The first argv entry starting with `/Game/` overrides it. This is checked for `py "<script>" /Game/...`. Passing it through `-Script="..."` headless is **unverified**, but the default needs no override.
- **Unchanged.**
  - Asset paths under `/Game/OWGame`, `/Game/ANGRY_MESH`, `/Game/MWLandscapeAutoMaterial` and `/Game/Materials` (see "Vendor use").
  - The report JSON with a per-step `ok`.
- **Checks.**
  - Every port passes `python -W error -m py_compile`.
  - The manifest 9.D gate grep over this folder returns nothing.
- **Leftover text.** Comments still cite source plan docs as `Docs/<Plan>.md`; those are in the source project's `Docs/` folder. Some knowledge comments still name the source's lab and canvas maps.

## How to run

- **Headless** is the manifest 9.0 pattern, run from PowerShell (never Git Bash):
  `& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' C:\GrandTour\GrandTour.uproject -run=PythonScript "-Script=C:/GrandTour/Art/dressing/ported/<Name>.py" -NullRHI -Unattended -NoSplash -NoSound "-abslog=<abs log>"`
  - Close the editor first.
  - Gate on the report JSON, not the exit code.
- **In-editor** means typing this in the editor console: `py "C:/GrandTour/Art/dressing/ported/<Name>.py" [/Game/Map/Path]`.
- **Tick** marks scripts that need a **ticking editor**. PCG generate and landscape edit-layer merges silently no-op in a commandlet (source `Scripts/CLAUDE.md`:60). Run them in-editor, or through the stage C tick harness (manifest 9.C.4).

## Scripts

| script | role | changes made | run |
|---|---|---|---|
| ClaudeSetupBiomePCG | pipeline (regen chain, after `-run=OWCreateBiomePCG`) | Biomes are now the 6 commandlet graphs (source-only biome dropped). Dropped the 3 `_RETIRED_graph_*` builders, the whole python graph kit they used (`_add`, `_sampler`, `_set_target_attribute`, ...) and the `wood_material` step, which only served them and would recreate the unmigrated M_OWPreviewWood. Header rewritten. Added the `MAP` constant, which it loads if not open. Keeps the M_OWPreviewConifer rebuild (deletes and recreates it). | in-editor, **tick** (`comp.generate`) |
| ClaudeDiagnoseBiomePCG | pipeline (regen chain) | Docstring run path only. Still checks Forest/Meadow/Scree. | in-editor, **tick** for its regenerate step |
| ClaudeFixBiomeGenerate | pipeline (regen chain) | Converted to the per-step report pattern (the source wrote a flat report and raised before writing it). Generates every actor matching `PCG_BiomeHost`, `DRESSLAB_PCG_*` or `CANVAS_PCG_*`; the source generated only the `PCG_BiomeHost` slice host, which the test map will not have. Saves only if all steps passed. Acts on the open level. | in-editor, **tick** |
| ClaudeAddRoadBedComponent | pipeline (roads) | Docstring: GrandTour headless command, and a note that the class now lives in the GrandTour module. | headless (after stage A build) |
| ClaudePaintRoadVerge | pipeline (roads) | Docstring run path only. Acts on the open level. | in-editor, **tick** (`editor_apply_spline` + edit-layer merge) |
| ClaudeVerifyRoadTypes | pipeline (roads, fresh-session verify) | None (no paths in it). | headless, separate session from ClaudeAuthorRoadTypes |
| ClaudeVerifyRoadExclusion | pipeline (roads) | Removed the fourth corridor class, its bounds constant and every "3 + 1" count. It now asserts 3 road getters, 3 samplers, 3 Set bounds modifiers at +/-(200,200,500), and every Difference fed by tag + 3 roads. Docstring: GrandTour headless command. | headless |
| ClaudeSetupRVTVolumes | pipeline (roads, map parameter) | `MAP` constant plus argv override. `find_landscape` loads `MAP` when another map is open (the source loaded its lab only when no landscape was found) and reports `{map, landscape}`. Docstring rewritten. | in-editor, or headless |
| ClaudeSetupDressingLab | regen-only | Removed the 4 bed/wet layers from `LAYERS`, `LAYER_TINTS` and `layer_ground`; the 3 extra ground-texture samples; `BED_LAYERS`/`WET_LAYER`; the wet-resolve node chain and its "must come after the bed layers" ordering rule. The grass kill mask is back to `(1 - OW_RoadVerge)`, still gated by `conn()`. Assertions now expect 13 layer samples. `MAP` replaces the source's map-dir/name/path trio; the script creates `MAP` if it is missing. The landscape-import text points at `OWToolkitSetupLibrary.BuildToolkitTestLandscape`. **Deletes and rebuilds M_OWDressingLab and respawns the lighting rig.** | in-editor |
| ClaudeHookupMeadowPack | regen-only | Docstring: GrandTour headless command. Notes that the fresh-session verify was not ported and that ClaudeTuneMeadowLook is stage B's. | headless |
| ClaudeAuthorOWFoliageMaster | regen-only | GrandTour headless command in the header. `REPORT_PATH` is next to the script. Still names the source's `ClaudeVerifyOWFoliageMaster.py`, which was not ported. | headless |
| ClaudeAuthorFoliageVariants | regen-only | Docstring run path. | in-editor |
| ClaudeSetupFoliageMIs | regen-only | Docstring run path. | in-editor |
| ClaudeSetupMeadowFlowers | regen-only | GrandTour headless command. `REPORT_PATH` is next to the script. | headless |
| ClaudeAuthorRoadTypes | regen-only | Docstring: GrandTour headless command; the verify script is in the same folder. | headless |
| ClaudeCreateOWRoadBP | regen-only | Docstring run path. | in-editor |
| ClaudeCleanupTreeOrphans | regen-only | Replaced the source lab map name with `MAP`; the map must be open. **Deletes** lineup actors and orphan tree meshes. | in-editor |
| DevGeneratePainterlyGrassCards | regen-only | `OUT_DIR` is `GrassCards/` next to the script. Docstring updated. | plain `python` (numpy + Pillow), no Unreal |
| ClaudeImportGrassCards | regen-only | `SRC_DIR` is `GrassCards/` next to the script. `REPORT_PATH` is next to the script. GrandTour headless command. | headless |
| ClaudeSetupLabRoads | reference | Docstring run path and a reference-only note. Acts on the open level. | in-editor |
| ClaudeRegenerateLabDressing | reference | The source's nearest-instance-to-spline self-check was source-only and is gone. It now fingerprints the per-volume ISM count and position sum before and after `generate_local(True)`, and saves only if that changed. `MAP` constant. | in-editor, **tick** |
| ClaudeSetupPCGWorldPreview | reference | Docstring run path. Adds a reference-only note (sized for the source's 8 km canvas). | in-editor, **tick** |
| ClaudeSetupCanvasDressing | reference | Source-only biome volume dropped (6 `CANVAS_PCG_*` volumes now). Replaced the source canvas map name with `MAP`; the map must be open. Docstring. | in-editor |

## Notes for later stages

- **Order.**
  1. Run the regen chain after `-run=OWCreateBiomePCG` (stage A commandlet, editor closed): `ClaudeSetupBiomePCG` (in-editor), then `ClaudeFixBiomeGenerate` if Get Landscape Data complains about the landscape cache, then `ClaudeDiagnoseBiomePCG` if a biome spawns nothing.
  2. Then stage B's `ClaudeTuneMeadowLook`.
- **These overwrite migrated assets:**
  - `ClaudeSetupBiomePCG` rebuilds `M_OWPreviewConifer` on every run.
  - Every regen-only script stomps migrated assets, so none runs by default.
- **Test map.**
  - `ClaudeSetupBiomePCG` spawns `DRESSLAB_PCG_<Biome>` StaticMeshActors with a PCGComponent and a BoxComponent.
  - The stage C test map uses tagged `PCGVolume`s instead (9.C.2). Running both on one map gives two sets of biome actors.
- **ClaudeRegenerateLabDressing** measures in the same frame as `generate_local`, as the source did, so it normally reports "NOT SAVED" even in-editor. The stage C tick harness, which polls on post-tick, is the working route.
- **Vendor use.**
  - `/Game/Materials` (MM_Foliage, MM_Trunk, MaterialInstances, MPC_GlobalWind) is used by `ClaudeAuthorOWFoliageMaster` and `ClaudeSetupFoliageMIs`. It is not one of the three packs, but it is in the manifest closure (section 3).
  - No port references ToonFantasyNature or Fantastic_Village_Pack.
