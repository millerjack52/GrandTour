# Deformable gravel

Open `/Game/GrandTour/ArtTests/DeformableGravel/L_GravelDeform` and Play. Drive straight ahead along the 140 m strip. The firm
section is at 30-55 m and the loose section at 80-110 m. Turn around and reuse the tracks, then move onto untouched gravel alongside
them. The field exists during Play; restarting Play resets it. The strip is a test bed: the material and the stones are not yet on
any game level (DG2, after the owner's approval).

The OpenAI Codex app built the first playable study (2026-10-08). The main session took it over in DG0 (commit 30b4703) and brought it
to the mud's standard in DG1 (`docs/DEFORMABLE_GRAVEL_PLAN.md`): the approved Blender revision 04 baked tileable, physically based
values, parallax, loose 3D stones the wheels push aside, and windrow heaps.

## What is on the strip

- **The field**: `EGTDeformMedium::Gravel` on the existing `FGTMudField` / `AGTMudPatch` / `UGTMudSubsystem` and wheel stamps. Each
  section's `FGTDeformProfile` gives the response, the field material (`SurfaceMaterialPath`), the stones' density
  (`GravelStonesPerM2`) and the windrow lumps. MR4's soft spots and MR5's chunks stay mud-only (`!bHasProfile && Medium == Mud`).
- **The bakes** (`Art/Blender/bake_gravel_dg1.py`, `Art/bake_gravel_orh.py`, `Art/Export/GravelDG1/manifest.json`): revision 04's own
  shader on a 2 m tile at 2048, seamless (periodic Voronoi and noise fields fed to a node-for-node copy of the study's graph). Loose is
  the off-path surface, Packed the study's own wheel path (vertex alpha 0.32: 3 % darker, chips 19 % fainter, as approved). ORH: R
  horizon AO, G roughness (0.9 - 0.16 x smoothstep(0.45, 0.9, h); Packed 0.05 lower), B a per-stone parallax height (tilted tops,
  centres 0.35-1.0 Loose / 0.25-0.7 Packed, soft rims at 6 %/texel). Imported as `TA_GV_{Color,Normal,ORH}` (slice 0 Loose, 1 Packed;
  `Art/import_gravel_dg1.ps1`).
- **M_GT_Gravel** on the field (`Art/Unreal/gravel_dg1_material.py`): the study's displacement and bicubic field normal, the arrays on a
  2 m world tile, the track blend p = smoothstep(0.35, 0.7, T - 0.3 (hL - 0.2959)) with T the worked mask, the windrow's denser look
  (AO contrast x1.15 and parallax x1.2 over 0-2 cm of windrow), parallax occlusion (0.8 cm Loose, 0.5 cm Packed; M_GT_Mud's march, 6-14 m
  fade, 4-step sun self-shadow within 4 m), PBR (roughness from ORH, wet: base colour x0.75 and roughness to 0.4, default specular), the
  AO and a 0.15 cavity tint. **M_GravelLandscape** wears slice 0 of the same arrays on the same world uv (no parallax), so the patch
  edge matches. The study's `M_GravelField` stays in the folder for comparison.
- **The loose stones** (`UGTGravelStones`, `Source/GrandTour/Terrain/GTGravelStones.*`): the study's `SM_GR_Stone1..4`, one hierarchical
  instance component per mesh per patch, in `M_GT_GravelStone` (DG1b: the ground's own stone palette - each instance takes a stone
  face of the Loose bake through the ground's x0.82 colour path with a small tint; roughness 0.75-0.85 per instance, 0.4 wet; faded out
  25-35 m; the material carries the instanced-mesh usage, without which DG1 drew the engine's default material: the near-black specks).
  The study's density: 12 per m^2 Firm, 30 Loose, renormalised over the section's span and over the patch's margins separately; DG1b's
  clustering: two octaves of value noise (1.5 m and 4 m, the second weighted 0.45), sharpened (smoothstep over 0.4-0.6), x0.1-2.5 (1 m^2
  quadrat count cv 0.73 Firm / 0.78 Loose, DG1's 0.44 / 0.37); 1.6x within 1 m of the road's edges and on the crown; tapered over the
  patch's last 3 m; sizes 1.5-5 cm (a power law: 77 % under 3 cm), random yaw,
  tilted to the field plus up to 15 deg, sunk 20-35 %. On the wheels' stamp path each stone whose centre is in the stroke is pushed out
  sideways 0.5-1.0 half-widths past its edge (jittered along it), or pressed in (12 %, sunk to 70 %, and it stays pressed), or with
  wheel slip over 0.3 flicked back 0.5-3 m within +-25 deg (a share equal to the slip, at most 0.6). Visual only.
- **Windrow heaps**: the field's lumps on the gravel profiles (LumpShare 0.3, dome cap 2.5 cm, radius 1-2 cells, LM2c's clustered and
  absent sites); clods stay off. The study's check `small_positive_ridges` is re-based for them (DG1b): Loose under 6 cm (the 3 cm ridge
  cap plus the 2.5 cm heaps, by design; the passes read 5.2-5.6 cm), Firm keeps under 4 cm (3.3-3.9 cm).
- **The texture slide** (DG1b): the field material's texture follows the field's offset at 0.25 of the mud's (`FGTDeformProfile::
  TextureSlideScale`, M_GT_Gravel's GravelSlideUV; the mud materials do not read it). At the mud's 1 the windrow walls showed streaked,
  smeared stones (Gravel_Close; gt.Gravel.Debug 2, no slide, removes them).

| Setting | Firm | Loose |
|---|---:|---:|
| Wheel sinkage cap | 2.5 cm | 5 cm |
| Rolling sinkage rate | 0.4 cm/s | 0.9 cm/s |
| Field cell size | 12.5 cm | 12.5 cm |
| Positive ridge cap (without the heaps) | 3 cm | 3 cm |
| Heaps (lumps) | 0.3 of the deposit, cap 2.5 cm | same |
| Loose stones | 12 per m^2 | 30 per m^2 |

Dry friction 0.68, rolling resistance 0.035, plough drag 0.012, sinkage drag scale 0.35 (the test's own `PM_Dirt` copy). These are the
study's feel numbers; the owner names any change after driving.

## Switches

| Switch | Default | What it does |
|---|---|---|
| `gt.Gravel.POM` | 2 | the gravel ground's parallax: 0 off, 1 8 steps, 2 adaptive 8-16 |
| `gt.Gravel.Stones` | 1 | 0 removes every loose stone (no instances); 1 brings the same stones back |
| `gt.Gravel.StoneDensity` | 1 | the stones' density scale, 0-1, for the cost tests |
| `gt.Mud.Settle` | 1 | the field's settling step (shared with the mud) |
| `gt.Gravel.Debug` | 0 | the pale-line diagnosis: 1 flat normal, 2 no texture slide, 3 no detail normal, 4 flat lighting normal, 5 no specular, 6 fully rough |

`stat unit`, `stat gpu` and `stat game` keep the existing `GT Mud` counters. No timing was measured: performance is the owner's.

## The pale line along the rut edges

The study's RepeatedPass picture had a thin pale line along one edge of each rut. It is the field normal's sun-lit rut wall: the cut
is even all along a rut, so its sun-facing wall (about 25 cm, ~15 deg) catches the low sun as one strip, and the grazing view squeezes
it into a thin line (the shadowed wall into the dark stripe). gt.Gravel.Debug showed it: the flat normal removes it; no texture slide,
no detail normal, no specular, full roughness and a B-spline slope in place of the Catmull-Rom one all draw it unchanged. M_GT_Gravel
now varies the wall's lighting slope along the rut (a 45 cm two-octave noise, x0.25-1.25) and by stone (x0.8-1.2), and soft-caps its
tilt at about 8 deg (`GravelWallTiltCap` 0.14); the relief is drawn by the parallax, the track blend, the stones and the AO.

## Rebuild and checks

- `python Art/bake_gravel_orh.py` (repack only) or the Blender bake: see `Art/Blender/bake_gravel_dg1.py`'s header.
- `& Art/import_gravel_dg1.ps1`: the arrays.
- `& Art/deformable_gravel.ps1 -Mode Setup`: the materials and the strip (M_GT_Gravel, the landscape, the stone material, the MPC).
- `& Art/deformable_gravel.ps1 -Mode Check`: the three passes, the study's ten checks, the pictures and the PBR captures;
  `python Art/sample_gravel_pbr.py` reads the captures into `pbr-rows.json`.
- `& Art/mud_shape_test.ps1`: every GrandTour.Mud, GrandTour.Snow and GrandTour.Gravel test.
- `& Art/gravel_shader_stats.ps1`: the shader counts against M_GravelField.

## The owner's tests

1. Drive L_GravelDeform: the first pass, the repeat on the same line, and the fresh shoulder lane.
2. `gt.Gravel.POM 0/1/2` and `gt.Gravel.Stones 0/1`.
3. The stone densities (`gt.Gravel.StoneDensity`, and the profiles' 12 / 30 per m^2).
4. The feel numbers above.
5. The heaps' height (the loose windrow stands up to 5.6 cm) and the stones' clustering.
