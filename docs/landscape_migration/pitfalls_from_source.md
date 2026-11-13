# Landscape toolkit pitfalls carried over from the source project

Stage D of `docs/LandscapeMigrationManifest.md`. Source files (read-only): `CLAUDE.md` = `D:\Dev\OWGameUE\Scripts\CLAUDE.md`; every other file is in `D:\Dev\OWGameUE\Docs\`. Only toolkit-relevant items; the sections the manifest excludes (section 4) are left out. Script names refer to the ports in `Art/dressing/ported/`.

## Headless Python and commandlets

- Run pattern: every step is an `@step` with a per-step `ok` in a report JSON, and the script raises at the end if any step failed. Read the report, not the exit code: 255 with a good report is normal. (CLAUDE.md:11)
- The exit code of `UnrealEditor-Cmd` is not a success signal: a run with an all-`ok` report returned 1. Chained drivers gate on the report's `ok`. (CLAUDE.md:225)
- `unreal.log()` output from `-run=PythonScript` never reaches redirected stdout. The artifacts are the report JSON and `Saved/Logs/<Project>.log`, which is overwritten per launch; earlier runs are in `*-backup-*.log`. (CLAUDE.md:207, 211)
- Git Bash rewrites `/Game/...` arguments to `C:/Program Files/Git/Game/...`. Symptom: "Failed to find object ... Git/Game". Run anything that takes a `/Game/` argument through PowerShell. (CLAUDE.md:209)
- In PowerShell 5.1, a variable named `$script` reaches UE unexpanded. Use `$py` and pass `"-Script=$py"`. (CLAUDE.md:7)
- Piping `UnrealEditor-Cmd` into `Select-Object -First N` kills UE when the pipe closes, leaving stale reports. Redirect to a file instead. (CLAUDE.md:135)
- Python that reads a JSON file written by PowerShell must use `read_text(encoding="utf-8-sig")`: PowerShell 5.1 `Set-Content -Encoding utf8` writes a BOM. (CLAUDE.md:223)
- Asset delete/recreate fails while any `UnrealEditor*` process is open: `delete_asset` returns False and later creates return None. Check processes before launching. (CLAUDE.md:18)
- `delete_asset` can return True and still leave a loadable zombie `.uasset`. `Test-Path` afterwards and remove leftovers with the editor closed. (CLAUDE.md:19)
- Kill any `-game` process before a headless rebuild; it holds `.uasset` locks (Error Code 32). (CLAUDE.md:106)
- `-run=PythonScript` always runs NullRHI, even without the flag, so `recompile_material` reporting 0 errors is a blind pass. Only a real-RHI run shows "Failed to compile Material". (CLAUDE.md:58, 122)
- Unity-build ODR: identical anonymous-namespace helper names in two .cpp files of one module compile until the unity chunks change, then fail with C2084. Grep for the name before pasting helpers. (CLAUDE.md:201)

## Python API limits (5.8)

- Use `EditorLoadingAndSavingUtils.load_map`. `LevelEditorSubsystem.load_level` access-violates on World Partition maps under NullRHI. (CLAUDE.md:22)
- A headless `load_map` enumerates no WP external actors, so edits to level actors on WP maps run in-editor. (CLAUDE.md:25)
- `add_component_by_class` is not exposed. Use `SubobjectDataSubsystem.add_new_subobject` and check the handle with `SubobjectDataBlueprintFunctionLibrary.is_handle_valid` (the handle has no `.is_valid()`). (CLAUDE.md:26, 44)
- Deleting BP components that the event graph references compiles to `BS_ERROR`. Scripts only add components. (CLAUDE.md:32)
- Python cannot rerun `OnConstruction`. Give the actor a UFUNCTION with both `BlueprintCallable` and `CallInEditor`: `CallInEditor` alone makes a Details button that Python cannot press. (CLAUDE.md:30, 39-42)
- BP-declared variables don't show in `dir()` on a headless CDO. Read them from a T3D export or from an in-editor instance. (RoadDressingRoundPlan.md:45-46)
- `EditorActorSubsystem.duplicate_actor` crashes headless. (RoadLookRoundPlan.md:36)
- Python names drop the `b` on bools (`bUnbounded` → `unbounded`, `bSRGB` → `srgb`); `b_xxx` raises. Other struct fields keep their member name. (CLAUDE.md:68)
- `get_components_by_class` returns a TSet, not creation order. Sort by an intrinsic property, or write order-independent asserts. (CLAUDE.md:66)
- SkyLight derives from `ULightComponentBase`, so a `LightComponent` probe misses it; query `SkyLightComponent`. A STATIONARY skylight with real-time capture silently no-ops; it needs MOVABLE. (CLAUDE.md:62, 101-103)

## Materials and material instances (script-authored)

- Material connections can't be read from Python (`FExpressionInput` is protected). `connect_material_expressions` does return truthfully, so gate on it. To inspect wiring, export a T3D. (CLAUDE.md:29)
- Connecting to an empty or mismatched input name silently wires input 0. Some pins use UI names (Power wants `Exp`). Wire helpers must raise on a miss. (CLAUDE.md:213)
- The MI parameter setters always return False, so verify by read-back, never by the setter's result. (CLAUDE.md:70)
- `set_material_instance_parent` doesn't dirty the package. Save with `only_if_is_dirty=False` and verify in a fresh session. (CLAUDE.md:71; RoadDressingRoundPlan.md:27-29)
- MI overrides match by name and survive a changed master default. A rerun that changes a default has to re-set every parameter on the MI. (CLAUDE.md:221)
- One `delete_all_material_expressions` call removes only the leaf layer. Loop until empty. (CLAUDE.md:219)
- Never duplicate an Opaque material and flip it to Masked: the private `bCanMaskedBeAssumedOpaque` survives. Create a fresh material instead. (CLAUDE.md:86; OWPainterlyGrassPlan.md:63)

## Landscape layers and edit layers

- `LandscapeLayerInfoObject.LayerName` is read-only from Python. Create layer infos in the Paint panel (Create Layer Info, Weight-Blended); scripts author only the material's LayerSample nodes. (CLAUDE.md:50)
- `EditorApplySpline`'s `PaintLayer` silently no-ops unless it is the exact layer info this landscape uses, and every map owns its own `*_LayerInfo`. Resolve it from `landscape.target_layers[...].layer_info_obj`, and validate the edit-layer name against `get_edit_layers()`. (CLAUDE.md:52; RoadLookRoundPlan.md:189-198)
- The edit-layer composite merge runs only on the editor tick. In a commandlet, layer writes land but render nothing. (CLAUDE.md:60; see PCG below for the harness)
- Edit layers are only resolved, never created headlessly. Create patch layers in-editor. (WorldToolsRoundPlan.md:80-82)
- LandscapePatch: `AssignToLandscape(landscape, name)` makes a "Patches" layer and leaves the patch unbound on a name miss. Call `set_landscape`, then assign by the real name from `get_edit_layers_bp()`. Test the guid with `!= unreal.Guid()`. (CLAUDE.md:51)
- Patch components are editor-only and stripped at cook. (WorldToolsRoundPlan.md:57-61)
- `M_OWDressingLab` sums weighted layers, so unpainted ground renders black and gets no PCG dressing. Paint first. (CLAUDE.md:64)

## PCG

- PCG generation needs a ticking editor. `generate_local(True)` under a commandlet returns cleanly and changes nothing. The working harness:
  - write `Content/Python/init_unreal.py`;
  - launch the full `UnrealEditor.exe` with the map;
  - let about 6 s of ticks pass, work, then poll on a slate post-tick callback;
  - save, then `quit_editor()`;
  - delete the bootstrap in a `finally`.
  (CLAUDE.md:60)
- Two launch routes that failed: `-ExecCmds=py ...` passed through a `Start-Process` array (the quoting gets mangled), and `-ExecutePythonScript` (not an engine flag). (CLAUDE.md:60)
- Never `cleanup_local()` before generating: if generation never runs, the level is left empty. Measure before and after, and save only on change. (CLAUDE.md:60)
- `FPCGAttributePropertySelector` fields are protected. Author the biome graphs in the C++ commandlet. From Python, assign a plain string or a base `PCGAttributePropertySelector` built with the helper, then read it back. (CLAUDE.md:54; WorldDressingPlan.md:11)
- ByClass getters need `ActorSelectionClass` set explicitly. Left null, they save null and silently match nothing. `ClaudeDiagnoseBiomePCG.py` finds and patches this. (CLAUDE.md:201; RoadLookRoundPlan.md:120)
- `UPCGEdge` naming is inverted: `InputPin` is the upstream end. Default pins keep multiple connections, and `Differences` unions its inputs. (CLAUDE.md:201)
- `GetNodes` is not exposed. Enumerate edges → pins → nodes, and read settings with `settings_interface`. (CLAUDE.md:201)
- ByClass matching is IsA, so typed roads are sibling duplicates with the MI baked into the CDO, not child classes (children would double-match). (RoadLookRoundPlan.md:127-129)
- A Distance-band filter with an empty Target pin passes everything through (PCGDistance.cpp:195). Generate points from the spline so that every failure yields nothing. (RoadLookRoundPlan.md:131-137)
- Spline point scale is baked into sampled points. TransformPoints multiplies it by default, and point bounds scale with it; a scaled corridor once erased dressing map-wide. Insert a unit-scale TransformPoints (`bAbsoluteScale`, 1..1) right after the sampler. The commandlet's `MakeUnitScale` does this. (CLAUDE.md:203)
- When the graph roster changes, update every expected-summary check (the "N graphs ... 0 failed" count) in the same change. (RoadLookRoundPlan.md:121-122)
- Commandlet reruns stomp in-editor node tweaks. The tunables live in the script or commandlet constants. (WorldDressingPlan.md:11, 188-189)
- The game never runs PCG: generate at edit time and save the instances. (WorldDressingPlan.md:19-20)
- A scripted PCG component add bypasses the editor's silent `PCGWorldActor` spawn, and Get Landscape Data then fails. `ClaudeFixBiomeGenerate.py` spawns the actor.

## Grass types

- Grass pins read raw layer weights. Only the interactive brush normalises siblings; `SetAlphaData` and `EditorApplySpline` leave meadow at 255 under a 255 verge. So every pin is multiplied by (1 - OW_RoadVerge) in the material. (RoadLookRoundPlan.md:181-185)
- A narrower verge repaint doesn't erase an older, wider band. Brush-erase the excess. (RoadLookRoundPlan.md:181-185)
- Grass never casts shadows and is not Nanite. It has a hard end cull per type, and density is the knob. (OWPainterlyGrassPlan.md:18-19; WorldDressingPlan.md:149)
- The LGT varieties are owned by `ClaudeHookupMeadowPack.py`. The tune knobs, hookup constants and commandlet values are one set of numbers: change all three together. (MeadowForestLookPerfPlan.md:28-31)
- Grass cards import sRGB ON. Distance colour merge sits inside each type's end cull (MergeStart 2500 / MergeEnd 4500). (OWPainterlyGrassPlan.md:42, 74)

## Trees, WPO and foliage masters

- Vendor WPO can be structural: MM_Foliage builds canopy volume in WPO, so disabling WPO deleted Beech and Birch canopies. Before touching vendor WPO, export a T3D. (CLAUDE.md:180-187)
- Bake time-invariant puff into geometry after any ScaleMesh. Baked meshes double-puff where WPO is still on. Check the `isFluffy` static switch per species: Fir is false, and baking it shatters needles. (CLAUDE.md:187-197)
- Never edit vendor assets (`/Game/ANGRY_MESH`, `/Game/Materials`). Duplicate into `/Game/OWGame` and tune there. (MeadowForestLookPerfPlan.md:20-21; MeadowPackIntegrationPlan.md:16-18)
- The Shadow Map Method stays VSM; that is a flagged decision. (MeadowForestLookPerfPlan.md:22-23)

## RVT

- Enable VT support (`r.VirtualTextures=1`) with a 256 MB pool, Auto Grow off, then restart. On starvation, raise the pool to 512 once. (RVTGroundRoundPlan.md:42-47, 128-130)
- An RVT volume's actor location is the bounds MIN CORNER, and its scale is the full size. Centre-placed volumes cover the wrong quadrant. (RoadLookRoundPlan.md:31)
- The volume component's `virtual_texture`, `bounds_align_actor` and `snap_bounds_to_landscape` can be set from Python; the "Set Bounds" button cannot. Size the volume from `get_actor_bounds()`. (RVTGroundRoundPlan.md:55-63)
- The display sample needs `bEnableFeedback=False` plus an explicit `MaterialType=BASE_COLOR_NORMAL_SPECULAR`. With feedback on while also writing the RVT, the landscape renders black. (RoadLookRoundPlan.md:32-33)
- Ground outside the RVT volume samples black ("working" mode). Keep full-landscape volumes. (RoadLookRoundPlan.md:82-84)
- RVT volumes and the landscape's RVT assignment are per level. (RVTGroundRoundPlan.md:136-138)
- Pack grass tints its bases from the RVT; without an RVT they are black. When the ground displays the same composite, the blades camouflage themselves, so "Disable RVT Grass" is baked TRUE on the AG settings actor. (RVTGroundRoundPlan.md:18-23)

## Roads, verge and bed

- The vendor road BP ships with empty mesh slots that can't be edited per instance. `ClaudeCreateOWRoadBP.py` duplicates it and bakes the recipe into the copy's CDO. (RoadDressingRoundPlan.md:39-46)
- Roads draw only into the RVT, so the landscape surface is the road surface. Project road dressing onto the landscape with no lift; spline height chords above terrain on slopes. (RoadLookRoundPlan.md:138-150)
- Scripted spline reshaping is a dead end. Author landscape splines and road shapes in-editor. (RoadLookRoundPlan.md:100-101)
- Bed and verge paint are one-way: re-routing a road doesn't revert the old bed. Regenerate PCG after deforming. (RoadLookRoundPlan.md:96-110)

## Perf numbers worth keeping

- D4 budget: grass has no shadows and culls at 5000-8000; meadow props and scree cull at 20000 with no shadow; bushes at 30000; trees cast shadows near and use HLOD far; deadfall culls at 15000. (WorldDressingPlan.md:147-154)
- Gate: GPU ≤ 20 ms at Medium shadows on the RTX 4050 laptop, with no VRAM banner. (WorldDressingPlan.md:159-160)
- On a VRAM banner, check the D4 descriptors first (a missing CastShadow=false is the usual cause), then Shadows Medium, then densities. The banner is screen-only and never logged. (WorldDressingPlan.md:185-187)
- Two density cuts didn't fix oak frame time: density was not the dominant cost. (MeadowForestLookPerfPlan.md:36-42)
- The fix was HISM for non-Nanite pack meshes plus per-instance culls: oaks 20000/25000, bushes 10000/13000, stumps and logs 7000/9000, rocks 8000/10000. (MeadowForestLookPerfPlan.md:84-102)
- The forest-floor carpet culls at 3500/4500. On a regression, halve the carpet delta first, then drop culls to 3000/4000. Tune knobs are the first lever; never delete machinery. (MeadowForestLookPerfPlan.md:183-190, 235-236)
