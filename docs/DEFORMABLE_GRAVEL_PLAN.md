# Deformable gravel: taking over the study and bringing it to the mud's standard

Main session, 2026-10-09. The owner asked for a deformable gravel material and chose to take over the OpenAI Codex
app's uncommitted study (`docs/DEFORMABLE_GRAVEL.md`, `L_GravelDeform`). It gets built and judged on that test strip
first, then applied to the test level once the owner approves.

## 0. Rules for the agent

`docs/MUDRUNNER_LESSONS_PLAN.md` section 0 holds in full: no timing; the foreign-Unreal wait; run with a game open,
never close it; the owner's look rejections; headless Blender for assets; docs per stage; commit only the stage's
files; never push. On top of that:

- **What Codex still owns:** the water simulation (GTWaterField/GTWaterSheet/M_GT_Water/river), Benmore
  (terrain, roads, reference roads, Gaea, verges, gravel POM for Benmore) and everything not listed in DG0. Never edit
  or stage those.
- **The approved look is the Blender gravel study revision 04**
  (`Art/Export/GravelRoadStudy/04/`, `docs/GRAVEL_ROAD_STUDY.md`). Keep its palette, its painted angular stone faces,
  its secondary chips and its scattered loose stones. What the game version lacks is the study's depth: the loose 3D
  stones on top, relief, and physically based values. In the study's first in-game picture
  (`Art/Export/DeformableGravel/Gravel_RepeatedPass.png`) the ground reads as a flat cobble mosaic, the ruts as smooth
  dark stripes with a thin pale line along one edge, and no displaced stones show at the rut edges. Those are three of
  the owner's rejections (cobble mosaic, regular lines, too smooth), and this plan exists to remove them.
- **The feel numbers stay the study's** (firm cap 2.5 cm and rate 0.4 cm/s, loose 5 cm and 0.9 cm/s, friction 0.68,
  rolling 0.035, plough 0.012, sinkage drag 0.35). The owner names any change after driving.

## DG0: take over the study (no look or feel change)

*Done 2026-10-09 (commit 30b4703): the inventory and the dependency list (Art/Export/DeformableGravel/dg0-dependencies.json: 33 study
packages, 42 shared, none Benmore); build, 15/15 Mud and Snow (CRC 8e0aad06) and the ten checks passed on MR5's code.*

1. **Inventory.** List every file and asset the study needs:
   - the C++ hunks: `EGTDeformMedium::Gravel`, `FGTDeformProfile::SurfaceMaterialPath`, and
     `AGTMudPatch::ProfileSurfaceMaterialPath` plus its use in Init;
   - `Art/Unreal/{deformable_gravel_material,setup_deformable_gravel,check_deformable_gravel}.py`,
     `Art/deformable_gravel.ps1`, `docs/DEFORMABLE_GRAVEL.md`;
   - `Content/GrandTour/ArtTests/DeformableGravel/*`, `Art/Export/DeformableGravel/*` (reports and pictures);
   - every asset those reference (resolved with the asset registry's dependency query in a commandlet, not by
     guessing). That includes `/Game/GrandTour/ArtTests/GravelRoad/T_GR_*` and the scripts and sources that made them:
     `Art/Blender/build_gravel_road_study.py`, `gravel_road_material.py`, `export_gravel_road.py`,
     `Art/Unreal/import_gravel_road.py`, `gravel_road_material.py`, `Art/import_gravel_road.ps1`,
     `Art/Export/GravelRoadStudy/`, `Art/Export/GravelRoadUE/`, `docs/GRAVEL_ROAD_STUDY.md`, `docs/GRAVEL_ROAD_IMPORT.md`,
     and the Poly Haven CC0 sources the study names, with their SOURCE.txt.
   - Anything Benmore-named stays out even if it shares a texture. Report shared assets, and don't move them.
2. **Verify** the study still works on today's code: MR4 and MR5 exclude the Gravel medium from soft spots and chunks.
   Run the build, mud_shape_test (CRC 8e0aad06) and `Art/deformable_gravel.ps1 -Mode Check`, whose ten functional
   checks must still pass.
3. **Commit** the inventory only, hunk by hunk for the shared C++ files:
   "Deformable gravel DG0: take over the Codex study (Gravel medium, per-section field material, L_GravelDeform)".
   Report the file list and the asset dependency list.

## DG1: the look and the loose stones

*Done 2026-10-09 (VEHICLE_BUILD_SYSTEM 98, docs/DEFORMABLE_GRAVEL.md): the bakes and arrays, M_GT_Gravel and the landscape on them, the
loose stones, the windrow heaps, GrandTour.Gravel.Stones (16/16 with Mud and Snow, CRC 8e0aad06). Open: the study's check
small_positive_ridges fails (the loose windrow 5.5 cm against under 4: the heaps' 2.5 cm domes on the 3 cm ridge cap) - the main
session decides the check's limit or the heaps' cap. The pale line was the field normal's sun-lit rut wall (now varied and tilt-capped).*

*DG1b done 2026-10-09 (the main session's look): the stones in the ground's palette (a Loose-bake stone face per instance x0.82; the
material lacked the instanced-mesh usage, so DG1 drew the default material), median base-colour luminance 0.216 against the ground's
0.197, the least 0.147; clustering on two octaves sharpened, x0.1-2.5, quadrat cv 0.73 / 0.78 (DG1 0.44 / 0.37), densities renormalised
per section; the texture slide 0.25 for gravel (the windrow streaks); small_positive_ridges re-based for Loose to under 6 cm; ten of ten.*

1. **Bakes** (headless Blender, from the revision-04 study's own shader and stone meshes), with the tileable-bake
   workflow LM5 used (seams clean, no dominant direction). 2 m tiles at 2048:
   - **Loose**: the study's off-path surface, broad stones and chips, as approved.
   - **Packed**: the study's wheel-path surface. Fine matrix with sparse, flattened stones pressed in; flatter and a
     little lighter (dusty), never smooth: the chips stay.
   - Each set: Color, Normal, ORH, packed as `Art/bake_mud_orh.py` does for mud. R is horizon AO from height. G is
     roughness in the dry-stone band, 0.55-0.9. B is a parallax height with soft rims, using MRP follow-up 3's slope
     cap of 1.5 %/texel and its 1.5-texel Gaussian, so steep stone edges don't terrace.
   - As `TA_GV_{Color,Normal,ORH}` Texture2DArrays: slice 0 Loose, slice 1 Packed (the mud's array builder).
   - Before any import, look at a Blender render of each set's tile repeated 3×3 at 1.7 m eye height. Report seams,
     repetition and a mosaic read.
   - **Decisions after the phase A bakes** (main session, 2026-10-09; they override the lines above where they
     differ):
     - **Packed** is the study's own wheel path: the shader at vertex-alpha 0.32. It is 3 % darker, not lighter, and
       its chips are 19 % fainter. Both are accepted, because this is the approved revision 04.
     - **Roughness** has no structure in the study (a constant 0.9), so the bake adds some. On Loose:
       ORH.G = 0.9 − 0.16 × smoothstep(0.45, 0.9, h), where h is the sharp height, so stone tops sit near 0.74 and the
       matrix at 0.9. Packed takes 0.05 off everything (tyre-polished), with a floor of 0.55.
     - **The slope cap is scaled for gravel.** 1.5 %/texel is a mud number: with 0.098 cm texels and 7.7 cm stones it
       turned the stones into domes (stone-top median B 0.64). Use 6 %/texel and a 1.0-texel Gaussian. Gates:
       Loose's stone-top median B ≥ 0.85 and its maximum ≥ 0.97. Terracing is judged in game on `Gravel_Low`.
     - **Parallax depth** (the study's relief is a 2.5 mm bump): B maps to 1.0 cm on Loose and 0.5 cm on Packed. The
       rest of the depth comes from the 3D stones and the field's windrow and heaps.
     - **Paint dabs:** random orientation (the bake's default), no road alignment.
     - **After the phase A2 Close.png** (main session): with displacement, the level-topped stones read as rounded
       pillows packed in mortar, i.e. cobble paving (a rejection). The parallax height therefore gets the following,
       and it overrides the 1.0 cm above:
       - a per-stone top height of 0.35-1.0, with about 30 % half buried;
       - a per-stone tilted top, rising 15-45 % of the range across the stone;
       - chips raised 0.05-0.3, and a noisy 0-0.1 matrix;
       - Loose depth 0.8 cm. Packed stones are tilted and sunk too, at 0.25-0.7.
       - Gate: stone-top median B ≥ 0.6. The look gate adds an on-foot render (1.7 m, 90° FOV).
2. **M_GT_Gravel** replaces `M_GravelField` on the gravel field (through the profile's `SurfaceMaterialPath`). It
   keeps the study's field displacement and bicubic normals and adds:
   - **The track blend.** p = smoothstep(0.35, 0.7, T - 0.3 × (hL - mean(hL))), where T is the worked/track mask the
     study already reads and hL is the Loose slice's height, and mean(hL) is its bake mean from the manifest. Stone tops hold out longest, so a rut's edge breaks up
     around the stones instead of drawing a line. Packed is Color/Normal/ORH lerped by p.
   - **The windrow.** Where the field height is positive (the displaced windrow), stone density goes up: Loose's AO
     contrast ×1.15 and its height ×1.2 over 0-2 cm of windrow. No new texture.
   - **Parallax occlusion.** On Loose's height, M_GT_Mud's POM code (field-normal frame, 6-14 m fade, adaptive
     8-16 steps, the 4-step self-shadow within 4 m), behind `gt.Gravel.POM` 0/1/2 like gt.Mud.POM. Packed uses the
     same POM UV.
   - **PBR.** Dry roughness from ORH.G. Weather wetness (MPC_Weather Wetness) darkens the base colour ×0.75 and lowers
     roughness to no less than 0.4. Specular is default (stone, F0 0.04).
   - **The pale edge line.** Find what draws the pale line along one rut edge in the study's picture (a pre-existing
     mask or normal edge). Remove it, and report the cause.
   - The landscape side (`M_GravelLandscape`) moves to the same arrays and world-space UV (no POM there), so the patch
     edge matches.
3. **Loose stones** (the study's 3D stones, which the game lacks):
   - **Instances.** One HISM per gravel patch with the study's `SM_GR_Stone1..4` (imported already; add a few more
     sizes by scale), in the study's palette material.
   - **Placement:**
     - Per m², the study's own rule: about 30 on Loose sections (the approved render's density) and 12 on Firm,
       with a `gt.Gravel.StoneDensity` scale (0-1, default 1) for the owner's cost tests.
     - Modulated by a hashed 1.5 m cluster noise (×0.3 to ×1.8, renormalised), and by 1.6× within 1 m of the road
       edges and on the crown between the wheel paths, as in the study.
     - Sizes 1.5-5 cm, power-law (most small). Random yaw, tilted to the field normal plus ±15°, sunk 20-35 % of their
       height.
     - Deterministic per section. Cull and fade at 25-35 m.
   - **Wheels push them.** On the same per-wheel path that stamps the field, each stone whose centre falls inside a
     stamp capsule is resolved:
     - **Pushed:** moved sideways out of the capsule, perpendicular to the wheel's heading, to 0.5-1.0 × the capsule's
       half-width past its edge, with ±30 % jitter along the heading and a new random yaw. They pile into the windrow
       irregularly, never in a row.
     - **Pressed in:** 12 % stay where they are, sunk to 70 % of their height.
     - **Flicked:** with wheel slip over 0.3, a share equal to the slip (capped at 0.6) is thrown back 0.5-3 m along
       the heading, with ±25° spread, and lands at the field surface.
     - Stones are visual only. The field's windrow already carries the volume.
   - `gt.Gravel.Stones` 0/1.
4. **Windrows into accumulations** (the study's own next step 1). Enable the field's lumps on the gravel profiles at
   gravel scale: LumpShare 0.3, dome cap 2.5 cm, radius 1-2 cells, the LM2c clustered and absent-site rules
   (spacing CV ≥ 0.4). The windrow then breaks into heaps instead of a continuous rail. Clods stay off.
5. **Tests**: `GrandTour.Gravel.Stones` (NullRHI CPU):
   - placement is deterministic, with density per section within ±15 % of target;
   - after a CPU stroke, stones whose centres lie in the capsule are ≤ 15 % of what was there before;
   - the band 0.5-1.0 half-widths outside the capsule gains the moved count exactly;
   - the moved stones' along-heading spacing has CV ≥ 0.4 (no row);
   - with slip 0.5, the flicked share is 0.5 ± 0.05 and the landing distances fall in 0.5-3 m;
   - with gt.Gravel.Stones 0, there are no instances.
   Then all GrandTour.Mud and GrandTour.Snow tests, with the CRC unchanged (gravel's lumps are profile-scoped; a mud
   CRC change means a leak, so stop). Then the study's ten functional checks.
6. **Pictures**, extending `check_deformable_gravel.py`:
   - the study's four (Before, FirstPass, RepeatedPass, ShoulderPass);
   - `Gravel_Close.png`: on foot, 1.7 m eye height, 3 m from a first-pass rut edge on the Loose section;
   - `Gravel_Low.png`: 0.5 m above the ground, looking along a rut;
   - `Gravel_Close_POM0.png`;
   - `Gravel_Wet.png`: Wetness 1.
   - PBR sampler rows: dry stone base-colour luminance in 0.05-0.35, and roughness p5 ≥ 0.5 dry and ≥ 0.4 wet.
   - Shader instruction and sampler counts against M_GravelField's.
7. **Docs**:
   - `docs/DEFORMABLE_GRAVEL.md` rewritten for the new state, with a switch table (gt.Gravel.POM, gt.Gravel.Stones,
     gt.Mud.Settle).
   - VEHICLE_BUILD_SYSTEM: the next free section, picked at commit time.
   - The devlog and BACKLOG line.
   - An italic Done note here.
   - The owner's test list:
     - drive L_GravelDeform: first pass, repeat and shoulder;
     - gt.Gravel.POM 0/1, gt.Gravel.Stones 0/1;
     - the stone densities;
     - the feel numbers.
8. **Commit**: "Deformable gravel DG1: revision-04 bakes with PBR and parallax, loose stones wheels push aside,
   windrow heaps".

## DG2 (after the owner approves DG1): apply to the test level

Written when DG1 is approved, once the owner says which level ("the test level") and which of its sections get gravel.
